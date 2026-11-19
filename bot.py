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

def get_astro(text):
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я твой астролог. Выбери режим:",
        reply_markup=KEYBOARD
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Разбор":
        rezhim = "razbor"
    elif text == "Совместимость":
        rezhim = "sovmestimost"
    elif text == "Прогноз":
        rezhim = "prognoz"
    elif text == "Натальная карта":
        rezhim = "karta"
    elif text == "Гороскоп":
        rezhim = "goroskop"
    else:
        rezhim = "razbor"

    astro = get_astro(text)

    if rezhim == "razbor":
        prompt = f"Ты астролог. Сделай разбор по данным: {astro}, с эмодзи."
    elif rezhim == "sovmestimost":
        prompt = f"Ты астролог. Расскажи про совместимость: {astro}, как помириться, перспективы, с эмодзи."
    elif rezhim == "prognoz":
        prompt = f"Ты астролог. Сделай прогноз: {astro}, с эмодзи."
    elif rezhim == "karta":
        prompt = f"Ты астролог. Опиши натальную карту: {astro}, с эмодзи."
    elif rezhim == "goroskop":
        prompt = f"Ты астролог. Сделай гороскоп: {astro}, с эмодзи."
    else:
        prompt = f"Ты астролог. Ответь: {astro}, с эмодзи."

    await update.message.reply_text("Думаю...")

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        await update.message.reply_text(
            resp.choices[0].message.content,
            reply_markup=KEYBOARD
        )
    except Exception as e:
        await update.message.reply_text(
            f"Ошибка: {e}",
            reply_markup=KEYBOARD
        )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
