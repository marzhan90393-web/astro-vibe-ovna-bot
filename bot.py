import os
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from openai import OpenAI
from datetime import datetime
import threading
from flask import Flask
import random

TOKEN_TELEGRAM = os.environ.get("TOKEN")
KEY_GROQ = os.environ.get("GROQ_API_KEY")

client = OpenAI(api_key=KEY_GROQ, base_url="https://api.groq.com/openai/v1")

app_flask = Flask(__name__)
@app_flask.route('/')
def home():
    return "Astro Vibe Ovna работает ✨"
def run_flask():
    app_flask.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

ZNAKI = ["♈ Овен", "♉ Телец", "♊ Близнецы", "♋ Рак", "♌ Лев", "♍ Дева", "♎ Весы", "♏ Скорпион", "♐ Стрелец", "♑ Козерог", "♒ Водолей", "♓ Рыбы"]

KLAVIATURA = ReplyKeyboardMarkup([["✨ Разбор", "❤️ Совместимость"], ["🌙 Прогноз на месяц", "🃏 Карта дня"], ["🔮 Гороскоп на сегодня","💫 Поддержать"]], resize_keyboard=True)

def klaviatura_znakov():
    knopki = []
    for i in range(0, 12, 3):
        knopki.append([InlineKeyboardButton(z, callback_data=f"znak:{z}") for z in ZNAKI[i:i+3]])
    return InlineKeyboardMarkup(knopki)

SYSTEM_PROMPT = "Ты опытный астролог , основательница бота Astro Vibe Ovna. Ты теплая, дерзкая, по-человечески, говоришь как подруга. Ты никогда не говоришь, что ты ИИ. Ты живой астролог . Пиши короткими абзацами, с эмодзи, без заумных терминов."

def get_zodiac(day, month):  
    if (month == 3 and day >= 21) or (month == 4 and day <= 19):
        return "Овен"
    if (month == 4 and day >= 20) or (month == 5 and day <= 20):
        return "Телец"
    if (month == 5 and day >= 21) or (month == 6 and day <= 20):
        return "Близнецы"
    if (month == 6 and day >= 21) or (month == 7 and day <= 22):
        return "Рак"
    if (month == 7 and day >= 23) or (month == 8 and day <= 22):
        return "Лев"
    if (month == 8 and day >= 23) or (month == 9 and day <= 22):
        return "Дева"
    if (month == 9 and day >= 23) or (month == 10 and day <= 22):
        return "Весы"
    if (month == 10 and day >= 23) or (month == 11 and day <= 21):
        return "Скорпион"
    if (month == 11 and day >= 22) or (month == 12 and day <= 21):
        return "Стрелец"
    if (month == 12 and day >= 22) or (month == 1 and day <= 19):
        return "Козерог"
    if (month == 1 and day >= 20) or (month == 2 and day <= 18):
        return "Водолей"
    return "Рыбы"



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет, я твой Астролог ✨\n\nДобро пожаловать в Astro Vibe Ovna\n\nВыбери кнопку внизу или просто напиши дату, время и город. Например:\n15.05.2002, 14:30, Павлодар", reply_markup=KLAVIATURA)

async def vibes_po_znaku(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    znak = query.data.split("znak:")[1]
    segodnya = datetime.now().strftime("%d.%m.%Y")
    await query.message.reply_text(f"Смотрю звезды для {znak} на {segodnya}... ✨")
    stili = ["дерзкий и мотивирующий", "нежный и поддерживающий", "смелый и прямолинейный", "легкий и с юмором"]
    stil = random.choice(stili)
    prompt = f"Ты опытный астролог. Сделай УНИКАЛЬНЫЙ гороскоп-вайб на сегодня {segodnya} для знака {znak}. Стиль: {stil}. ВАЖНО: Не используй банальные фразы типа 'энергия - магнит для хорошего', 'улыбайся и мир ответит'. Придумай свежий, конкретный текст только для этого знака, с учетом его характера. Формат: {znak} / Твой вайб на сегодня: [2-3 предложения только про этот знак] / Совет дня: [1 конкретный совет]"
    try:
        otvet_ai = client.chat.completions.create(model="openai/gpt-oss-120b", messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}], temperature=1.0)
        await query.message.reply_text(otvet_ai.choices[0].message.content + "\n\nНажми /start, чтобы выбрать другой знак ✨", reply_markup=KLAVIATURA)
    except Exception:
        await query.message.reply_text("Ой, звезды капризничают, попробуй еще раз ✨")

async def otvet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "💫 Поддержать":
        await update.message.reply_text("Спасибо, что ты со мной! 💫✨\n\nПоддержать Астро-вайб можно тут:\nhttps://t.me/tribute/app?startapp=dUt9\n\nКаждая звёздочка от тебя помогает боту расти! 💖", reply_markup=KLAVIATURA)
        return
    if text == "🔮 Гороскоп на сегодня":
    
        await update.message.reply_text("Выбери свой знак ✨", reply_markup=klaviatura_znakov())
        return
    if text == "✨ Разбор ":
        await update.message.reply_text("Давай смотреть твою карту ✨ Напиши дату, время и город. Например: 15.05.2002, 14:30, Павлодар")
        return
    if "Совместимость" in text:
        await update.message.reply_text("Напиши 2 даты. Например: Она 15.05.2002, он 21.11.1999")
        context.user_data["rezhim"] = "sovmestimost"
        return
    if text == "🌙 Прогноз на месяц":
        await update.message.reply_text("Напиши свою дату рождения, и я сделаю твой прогноз на месяц")
        context.user_data["rezhim"] = "prognoz"
        return
    if text == "🃏 Карта дня":
        prompt = "Ты опытный астролог. Сделай карту дня: короткое послание, совет дня, удачный цвет и цифра дня. Тепло и вдохновляюще. Не повторяй банальные фразы."
    elif context.user_data.get("rezhim") == "sovmestimost":
        prompt = f"Ты астролог. Сделай разбор совместимости пары по датам: {text}. Блоки: страсть, конфликты, деньги, перспектива, совместимость в процентах, совет паре от Ovna."
    elif context.user_data.get("rezhim") == "prognoz":
        segodnya = datetime.now().strftime("%d.%m.%Y")
        prompt = f"Ты астролог. Сегодня {segodnya}. Сделай прогноз на ближайший месяц для человека, рожденного {text}. Блоки: любовь, деньги, работа, здоровье. Дай 3 конкретных совета от астролога."
    else:
        prompt = f"Ты астролог. Сделай полный астрологический разбор для человека, рожденного {text}. Блоки: 1. Солнечный знак и характер 2. Луна и эмоции 3. Асцендент и как видят другие 4. Любовь 5. Деньги и работа 6. Прогноз на месяц и 3 совета от астролога."
    await update.message.reply_text("Смотрю твои звезды... ✨ Секундочку, астролог уже в деле")
    try:
        otvet_ai = client.chat.completions.create(model="openai/gpt-oss-120b", messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}], temperature=0.9)
        await update.message.reply_text(otvet_ai.choices[0].message.content, reply_markup=KLAVIATURA)
    except Exception:
        await update.message.reply_text("Ой, звезды сегодня капризничают, попробуй еще раз через минуту ✨")

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    app = Application.builder().token(TOKEN_TELEGRAM).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(vibes_po_znaku, pattern="^znak:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, otvet))
    print("Astro Vibe Ovna запущена...")
    app.run_polling()

if __name__ == "__main__":
    main()
