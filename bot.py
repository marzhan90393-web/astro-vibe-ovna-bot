import os
import threading
from flask import Flask
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

client = OpenAI(
    api_key=GROQ_KEY,
    base_url="https://api.groq.com/openai/v1"
)

KEYBOARD = ReplyKeyboardMarkup(
    [["Разбор", "Совместимость"], ["Прогноз", "Натальная карта", "Гороскоп"]],
    resize_keyboard=True
)

SYSTEM = "Ты астролог Ovna, основательница бота Astro Vibe Ovna. Теплая, дерзкая, как подруга. Никогда не говори, что ты ИИ. Пиши короткими абзацами, с эмодзи, без заумных терминов."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет, я Ovna ✨\n\nДобро пожаловать в Astro Vibe Ovna\n\nВыбери кнопку внизу или просто напиши дату, время и город. Например:\n15.05.2002, 14:30, Павлодар",
        reply_markup=KEYBOARD
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "Разбор":
        prompt = f"Ты Ovna. Сделай полный астрологический разбор для человека: {text}. Но человек еще не дал данные, попроси дату, время и город."
        # Если это просто кнопка, просим данные
        await update.message.reply_text("Давай смотреть твою карту ✨ Напиши дату, время и город. Например: 15.05.2002, 14:30, Павлодар")
        return
    elif text == "Совместимость":
        await update.message.reply_text("Напиши 2 даты. Например: Она 15.05.2002, он 21.11.1999")
        return
    elif text == "Прогноз":
        await update.message.reply_text("Напиши свою дату рождения, и я сделаю твой прогноз на месяц")
        return
    elif text == "Натальная карта":
        await update.message.reply_text("Напиши дату, время и город рождения для натальной карты")
        return
    elif text == "Гороскоп":
        await update.message.reply_text("Напиши свой знак зодиака или дату рождения для гороскопа")
        return
    else:
        prompt = f"Ты Ovna. Сделай астрологический разбор для человека, который написал: {text}. Блоки: характер, Луна и эмоции, любовь, деньги и работа, совет от Ovna."

    await update.message.reply_text("Смотрю твои звезды... ✨ Секундочку, Ovna уже в деле")

    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt}
            ]
        )
        await update.message.reply_text(resp.choices[0].message.content, reply_markup=KEYBOARD)
    except Exception as e:
        await update.message.reply_text(f"Ой, звезды капризничают ✨ Попробуй еще раз через минуту. Ошибка: {e}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Flask чтобы Render не ругался, что нет порта
    flask_app = Flask(__name__)
    @flask_app.route("/")
    def home():
        return "Astro Vibe Ovna работает!"

    threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000))), daemon=True).start()

    print("Astro Vibe Ovna запущена...")
    app.run_polling()

if __name__ == "__main__":
    main()
