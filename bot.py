import os
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

SIGNS = ["Овен ♈","Телец ♉","Близнецы ♊","Рак ♋","Лев ♌","Дева ♍","Весы ♎","Скорпион ♏","Стрелец ♐","Козерог ♑","Водолей ♒","Рыбы ♓"]

PREDICTIONS = [
    "Сегодня звезды на твоей стороне! Жди приятный сюрприз от близкого человека ✨",
    "День для смелых решений. Не бойся сказать то, что давно хотела 💫",
    "Твоя энергия сегодня - магнит для хорошего. Улыбайся, и мир ответит тем же 🌙",
    "Прислушайся к интуиции - она сегодня точнее любого гороскопа 🔮",
    "Идеальный день для отдыха и заботы о себе. Ты заслужила паузу 💖",
    "Вселенная готовит тебе встречу, которая все изменит. Будь открыта! ⭐",
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    row = []
    for sign in SIGNS:
        row.append(InlineKeyboardButton(sign, callback_data=sign))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    await update.message.reply_text(
        "Привет! Я Astro_vibe_ovna_bot ✨🔮\n\nВыбери свой знак зодиака и я расскажу твой вайб на сегодня:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    sign = query.data
    text = random.choice(PREDICTIONS)
    await query.edit_message_text(f"{sign}\n\nТвой вайб на сегодня:\n\n{text}\n\nНажми /start, чтобы выбрать другой знак ✨")

def main():
    token = os.environ.get("BOT_TOKEN")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
