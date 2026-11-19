import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

TOKEN = os.getenv("BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

KEYBOARD = ReplyKeyboardMarkup(
    [["Разбор", "Совместимость"], ["Прогноз", "Натальная карта"], ["Гороскоп"]],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я твой астролог. Выбери режим:", reply_markup=KEYBOARD)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Разбор":
        prompt = f"Ты астролог. Сделай разбор по данным: {text}, с эмодзи."
    elif text == "Совместимость":
        prompt = f"Ты астролог. Расскажи про совместимость: {text}, с эмодзи."
    elif text == "Прогноз":
        prompt = f"Ты астролог. Сделай прогноз: {text}, с эмодзи."
    elif text == "Натальная карта":
        prompt = f"Ты астролог. Опиши натальную карту: {text}, с эмодзи."
    elif text == "Гороскоп":
        prompt = f"Ты астролог. Сделай гороскоп: {text}, с эмодзи."
    else:
        prompt = f"Ты астролог. Ответь на вопрос: {text}, с эмодзи."
    await update.message.reply_text("Думаю...")
    try:
        resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}])
        await update.message.reply_text(resp.choices[0].message.content, reply_markup=KEYBOARD)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}", reply_markup=KEYBOARD)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
