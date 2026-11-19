import os
import re
import math
from datetime import datetime, timezone, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY)

# Координаты городов
CITIES = {
    "павлодар": (52.29, 76.96),
    "алматы": (43.23, 76.88),
    "астана": (51.16, 71.47),
    "нур-султан": (51.16, 71.47),
    "караганда": (49.80, 73.10),
    "шымкент": (42.30, 69.60),
    "актобе": (50.28, 57.16),
    "костанай": (53.21, 63.62),
    "семей": (50.41, 80.25),
    "усть-каменогорск": (49.97, 82.60),
    "петропавловск": (54.86, 69.15),
    "москва": (55.75, 37.61),
    "новосибирск": (55.00, 82.95),
}

SIGNS = ["Овен", "Телец", "Близнецы", "Рак", "Лев", "Дева", "Весы", "Скорпион", "Стрелец", "Козерог", "Водолей", "Рыбы"]

def sign_from_lon(lon):
    lon = lon % 360
    idx = int(lon // 30)
    deg = lon % 30
    return f"{SIGNS[idx]} {int(deg)}°{int((deg % 1) * 60):02d}'"

def sign_name(lon):
    return SIGNS[int((lon % 360) // 30)]

def julian_day(dt_utc):
    y = dt_utc.year
    m = dt_utc.month
    d = dt_utc.day + (dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600) / 24
    if m <= 2:
        y -= 1
        m += 12
    a = int(y / 100)
    b = 2 - a + int(a / 4)
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5
    return jd

def sun_longitude(jd):
    t = (jd - 2451545.0) / 36525.0
    l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360
    m = (357.52911 + t * (35999.05029 - t * 0.0001537)) % 360
    m_rad = math.radians(m)
    c = (1.914602 - t * (0.004817 + 0.000014 * t)) * math.sin(m_rad) + (0.019993 - 0.000101 * t) * math.sin(2 * m_rad) + 0.000289 * math.sin(3 * m_rad)
    return (l0 + c) % 360

def moon_longitude(jd):
    t = (jd - 2451545.0) / 36525.0
    l = (218.3165 + 481267.8813 * t) % 360
    m = (357.52911 + 35999.05029 * t) % 360
    mp = (134.963 + 477198.8676 * t) % 360
    f = (93.272 + 483202.0175 * t) % 360
    d = (297.850 + 445267.1115 * t) % 360
    lon = l + 6.289 * math.sin(math.radians(mp)) + 1.274 * math.sin(math.radians(2 * d - mp)) + 0.658 * math.sin(math.radians(2 * d)) + 0.214 * math.sin(math.radians(2 * mp)) - 0.186 * math.sin(math.radians(m)) - 0.114 * math.sin(math.radians(2 * f))
    return lon % 360

def ascendant(jd, lat, lon):
    # GMST
    t = (jd - 2451545.0) / 36525.0
    gmst = (280.46061837 + 360.98564736629 * (jd - 2451545.0) + t * t * (0.000387933 - t / 38710000.0)) % 360
    ramc = (gmst + lon) % 360
    eps = 23.439291 - 0.0130042 * t
    eps_r = math.radians(eps)
    ramc_r = math.radians(ramc)
    lat_r = math.radians(lat)
    asc = math.degrees(math.atan2(math.cos(ramc_r), -(math.sin(ramc_r) * math.cos(eps_r) + math.tan(lat_r) * math.sin(eps_r))))
    return asc % 360

def get_astro_extra(text):
    try:
        m = re.search(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})\D+(\d{1,2})[:.](\d{2})", text)
        if not m:
            m2 = re.search(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})", text)
            if not m2:
                return ""
            day, month, year = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
            hh, mm = 12, 0
        else:
            day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            hh, mm = int(m.group(4)), int(m.group(5))
        # Город - последнее слово после запятой
        parts = text.split(",")
        city = parts[-1].strip().lower() if len(parts) >= 2 else "павлодар"
        lat, lon = CITIES.get(city, (52.29, 76.96))
        # Казахстан UTC+5, если время местное
        dt_local = datetime(year, month, day, hh, mm)
        dt_utc = dt_local - timedelta(hours=5)
        jd = julian_day(dt_utc)
        sun = sun_longitude(jd)
        moon = moon_longitude(jd)
        asc = ascendant(jd, lat, lon)
        return f"Точный расчет: Солнце в {sign_from_lon(sun)}, Луна в {sign_from_lon(moon)}, Асцендент в {sign_from_lon(asc)}. Используй эти данные как основу, не пересчитывай их сама."
    except Exception:
        return ""

KEYBOARD = ReplyKeyboardMarkup(
    [["✨ Разбор", "❤️ Совместимость"], ["🌙 Прогноз на месяц", "🃏 Карта дня"], ["🔮 Гороскоп на сегодня", "💛 Поддержать"]],
    resize_keyboard=True
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет, я твой Астролог ✨\n\nДобро пожаловать в Astro Vibe Ovna\n\nВыбери кнопку внизу или просто напиши дату, время и город. Например:\n15.05.2002, 14:30, Павлодар",
        reply_markup=KEYBOARD
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    rezhim = context.user_data.get("rezhim", "")

    if text == "✨ Разбор":
        context.user_data["rezhim"] = "razbor"
        await update.message.reply_text("Привет, солнышко! ✨\nНапиши свою дату, время и город рождения.\nНапример: 15.05.2002, 14:30, Павлодар", reply_markup=KEYBOARD)
        return

    if text == "❤️ Совместимость":
        context.user_data["rezhim"] = "sovmestimost"
        await update.message.reply_text("Давай проверим вашу совместимость! 💕\nПришли две даты рождения (день/месяц/год). Как только пришлёшь, сразу начнём «чаровать» совместимость! ✨💫\n\nЖду, не стесняйся! 🌺\n— Ovna, ваш астролог-подружка.", reply_markup=KEYBOARD)
        return

    if text == "🌙 Прогноз на месяц":
        context.user_data["rezhim"] = "prognoz"
        await update.message.reply_text("Напиши свою дату рождения, и я сделаю прогноз на месяц! 🌙", reply_markup=KEYBOARD)
        return

    if text == "🃏 Карта дня":
        context.user_data["rezhim"] = "karta"
        await update.message.reply_text("Сегодняшняя карта для тебя... 🃏 Напиши свою дату рождения, и я вытяну карту дня.", reply_markup=KEYBOARD)
        return

    if text == "🔮 Гороскоп на сегодня":
        context.user_data["rezhim"] = "goroskop"
        await update.message.reply_text("Напиши свою дату рождения, и я сделаю гороскоп на сегодня! 🔮", reply_markup=KEYBOARD)
        return

    if text == "💛 Поддержать":
        await update.message.reply_text("Спасибо, солнышко! 💛 Твоя поддержка - это моё топливо для звёзд! ✨", reply_markup=KEYBOARD)
        return

    # Если это дата / текст для разбора
    astro = get_astro_extra(text)

    if rezhim == "razbor":
        prompt = f"Ты астролог. {astro} Сделай тёплый, подробный разбор натальной карты для: {text}. Расскажи про Солнце, Луну, Асцендент, характер, любовь, деньги, предназначение. Стиль - как подружка, с эмодзи."
    elif rezhim == "sovmestimost":
        prompt = f"Ты астролог. {astro} Сделай разбор совместимости для: {text}. Расскажи про сильные стороны пары, конфликты, как помириться, перспективы. Тёпло, с эмодзи."
    elif rezhim == "prognoz":
        prompt = f"Ты астролог. {astro} Сделай прогноз на месяц для: {text}. По неделям, любовь, деньги, здоровье. Тёпло, с эмодзи."
    elif rezhim == "karta":
        prompt = f"Ты астролог. {astro} Вытяни карту дня для: {text}. Название карты, её значение, совет на день. Тёпло, с эмодзи."
    elif rezhim == "goroskop":
        prompt = f"Ты астролог. {astro} Сделай гороскоп на сегодня для: {text}. Любовь, деньги, настроение, совет. Тёпло, с эмодзи."
    else:
        prompt = f"Ты астролог. {astro} Сделай разбор для: {text}. Солнце, Луна, Асцендент, характер, любовь. Тёпло, с эмодзи."

    await update.message.reply_text("Секундочку, звёзды шепчутся... ✨", reply_markup=KEYBOARD)
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        await update.message.reply_text(resp.choices[0].message.content, reply_markup=KEYBOARD)
    except Exception as e:
        await update.message.reply_text(f"Ой, звёзды сегодня капризничают... Попробуй ещё раз через минутку ✨\n({e})", reply_markup=KEYBOARD)

def main():
        app = Application.builder().token(BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        port = int(os.getenv("PORT", 10000))
    def _serve():
        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
            def log_message(self, *a): pass
        HTTPServer(("0.0.0.0", port), H).serve_forever()
    threading.Thread(target=_serve, daemon=True).start()
    app.run_polling()

if __name__ == "__main__":
    main()
