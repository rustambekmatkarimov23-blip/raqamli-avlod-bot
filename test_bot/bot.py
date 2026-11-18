import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from questions import TESTS

TOKEN = "8660305995:AAEc2kRUI-N_I04hOwWXPghIXqzTSI-I988"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Foydalanuvchilar holati
user_state = {}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_state and "task" in user_state[user_id]:
        user_state[user_id]["task"].cancel()

    builder = InlineKeyboardBuilder()
    for key, value in TESTS.items():
        builder.button(text=value["title"], callback_data=f"sub_{key}")
    builder.adjust(1)

    await message.answer(
        "🤖 **Raqamli avlod botiga xush kelibsiz!**\n\n"
        "⚡️ Har bir savol uchun **60 soniya** vaqt beriladi va qolgan vaqt ko'rsatib turiladi.\n"
        "🎯 Savollar takrorlanmaydi.\n\n"
        "Bilimingizni sinash uchun fanni tanlang:",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("sub_"))
async def start_test(callback: types.CallbackQuery):
    subject_key = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    if user_id in user_state and "task" in user_state[user_id]:
        user_state[user_id]["task"].cancel()

    subject_data = TESTS[subject_key]
    shuffled_questions = list(subject_data["questions"])
    random.shuffle(shuffled_questions)

    user_state[user_id] = {
        "subject_title": subject_data["title"],
        "questions": shuffled_questions,
        "question_index": 0,
        "score": 0,
        "task": None,
        "message_id": callback.message.message_id,
        "chat_id": callback.message.chat.id
    }
    
    await send_question(user_id)
    await callback.answer()

async def send_question(user_id: int):
    if user_id not in user_state:
        return
    
    state = user_state[user_id]
    q_index = state["question_index"]
    questions = state["questions"]
    
    # Eski taymerni to'xtatamiz
    if state["task"]:
        state["task"].cancel()

    # Agar savollar tugasa
    if q_index >= len(questions):
        score = state["score"]
        total = len(questions)
        try:
            await bot.edit_message_text(
                chat_id=state["chat_id"],
                message_id=state["message_id"],
                text=f"🎉 **Test yakunlandi!**\n\n"
                     f"📚 Fan: {state['subject_title']}\n"
                     f"✅ To'g'ri javoblar: {score} ta / {total} tadan\n\n"
                     f"Qaytadan boshlash uchun /start buyrug'ini bosing.",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        del user_state[user_id]
        return

    # Taymerni 60 soniyadan boshlaymiz
    state["time_left"] = 60
    question_data = questions[q_index]
    
    # Xabarni chiqaramiz
    await update_question_message(user_id)

    # 60 soniyalik ortga hisoblash vaqtini ishga tushiramiz
    state["task"] = asyncio.create_task(run_timer(user_id, q_index))

async def update_question_message(user_id: int):
    if user_id not in user_state:
        return
    
    state = user_state[user_id]
    q_index = state["question_index"]
    questions = state["questions"]
    question_data = questions[q_index]
    time_left = state["time_left"]

    builder = InlineKeyboardBuilder()
    for i, option in enumerate(question_data["options"]):
        builder.button(text=option, callback_data=f"ans_{i}")
    builder.adjust(2)

    text = (
        f"<b>{state['subject_title']}</b> ({q_index + 1}/{len(questions)})\n\n"
        f"⏳ <b>Qolgan vaqt: {time_left} soniya</b>\n\n"
        f"<b>{question_data['question']}</b>"
    )

    try:
        await bot.edit_message_text(
            chat_id=state["chat_id"],
            message_id=state["message_id"],
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML"
        )
    except Exception:
        pass # Agar matn o'zgarmagan bo'lsa xato bermasligi uchun

async def run_timer(user_id: int, q_index: int):
    while user_id in user_state and user_state[user_id]["question_index"] == q_index:
        await asyncio.sleep(5) # Har 5 soniyada vaqtni yangilab boramiz (Telegram limitini buzmaslik uchun)
        if user_id not in user_state:
            break
        
        state = user_state[user_id]
        if state["question_index"] != q_index:
            break

        state["time_left"] -= 5
        if state["time_left"] <= 0:
            # Vaqt tugadi, keyingi savolga o'tamiz
            state["question_index"] += 1
            await send_question(user_id)
            break
        else:
            await update_question_message(user_id)

@dp.callback_query(F.data.startswith("ans_"))
async def check_answer(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in user_state:
        await callback.answer("Test tugagan yoki vaqt o'tgan. /start ni bosing.", show_alert=True)
        return

    state = user_state[user_id]
    
    if state["task"]:
        state["task"].cancel()

    selected_option = int(callback.data.split("_")[1])
    q_index = state["question_index"]
    
    correct_option = state["questions"][q_index]["correct"]
    
    if selected_option == correct_option:
        state["score"] += 1
        
    state["question_index"] += 1
    await send_question(user_id)
    await callback.answer()

async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())