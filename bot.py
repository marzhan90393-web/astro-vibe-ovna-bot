
import os
import re
import asyncio
import random
import threading
import logging

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import swisseph as swe
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

from flask import Flask
from openai import AsyncOpenAI

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)


# =====================================================
# НАСТРОЙКИ
# =====================================================

TOKEN_TELEGRAM = os.environ.get("TOKEN")
KEY_GROQ = os.environ.get("GROQ_API_KEY")

if not TOKEN_TELEGRAM:
    raise RuntimeError("Не задан TOKEN Telegram")

if not KEY_GROQ:
    raise RuntimeError("Не задан GROQ_API_KEY")

client = AsyncOpenAI(
    api_key=KEY_GROQ,
    base_url="https://api.groq.com/openai/v1"
)

MODEL = "openai/gpt-oss-120b"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# =====================================================
# FLASK ДЛЯ RENDER
# =====================================================

app_flask = Flask(__name__)


@app_flask.route("/")
def home():
    return "Astro Vibe Ovna работает ✨"


def run_flask():
    port = int(os.environ.get("PORT", 10000))

    app_flask.run(
        host="0.0.0.0",
        port=port,
        use_reloader=False
    )


# =====================================================
# TELEGRAM КЛАВИАТУРА
# =====================================================

ZNAKI = [
    "♈ Овен", "♉ Телец", "♊ Близнецы",
    "♋ Рак", "♌ Лев", "♍ Дева",
    "♎ Весы", "♏ Скорпион", "♐ Стрелец",
    "♑ Козерог", "♒ Водолей", "♓ Рыбы"
]

KLAVIATURA = ReplyKeyboardMarkup(
    [
        ["✨ Разбор", "❤️ Совместимость"],
        ["🌙 Прогноз на месяц", "🃏 Карта дня"],
        ["🔮 Гороскоп на сегодня", "💫 Поддержать"]
    ],
    resize_keyboard=True
)


def klaviatura_znakov():
    buttons = []

    for i in range(0, 12, 3):
        buttons.append([
            InlineKeyboardButton(
                z,
                callback_data=f"znak:{z}"
            )
            for z in ZNAKI[i:i + 3]
        ])

    return InlineKeyboardMarkup(buttons)


# =====================================================
# СТИЛЬ ASTRO VIBE OVNA
# =====================================================

SYSTEM_PROMPT = """
Ты — астролог проекта Astro Vibe Ovna.

Твой стиль:
- Тёплый, живой, дружеский.
- Общайся как близкая подруга, которая хорошо разбирается в астрологии.
- Пиши простым человеческим языком.
- Не используй заумные формулировки.
- Не пиши длинные вступления.
- Не повторяй одну и ту же мысль.
- Используй эмодзи умеренно.

ВАЖНО:
1. Используй только те астрологические положения,
   которые переданы тебе в запросе.
2. Не придумывай положения планет, знаки и аспекты.
3. Если данных недостаточно, честно скажи об этом.
4. Не выдавай предположения за точные астрологические факты.
5. Не запугивай человека прогнозами.
6. Не обещай конкретные события как гарантированные.

Твоя задача — сделать понятную и содержательную
астрологическую интерпретацию.
"""


# =====================================================
# ЗНАКИ ЗОДИАКА
# =====================================================

SIGNS = [
    "Овен", "Телец", "Близнецы", "Рак",
    "Лев", "Дева", "Весы", "Скорпион",
    "Стрелец", "Козерог", "Водолей", "Рыбы"
]


def zodiac_sign(longitude):
    index = int(longitude // 30) % 12
    return SIGNS[index]


# =====================================================
# ГЕОГРАФИЯ И ЧАСОВЫЕ ПОЯСА
# =====================================================

geolocator = Nominatim(
    user_agent="astro_vibe_ovna_bot"
)

tf = TimezoneFinder()

city_cache = {}


async def get_city_data(city):
    """
    Автоматически определяет координаты города
    и его часовой пояс.
    """

    city = city.strip()

    if city in city_cache:
        return city_cache[city]

    try:
        location = await asyncio.to_thread(
            geolocator.geocode,
            city,
            language="ru",
            timeout=15
        )

        if not location:
            location = await asyncio.to_thread(
                geolocator.geocode,
                city,
                timeout=15
            )

        if not location:
            return None

        latitude = location.latitude
        longitude = location.longitude

        tz_name = tf.timezone_at(
            lng=longitude,
            lat=latitude
        )

        if not tz_name:
            return None

        result = {
            "latitude": latitude,
            "longitude": longitude,
            "timezone": tz_name,
            "city": location.address
        }

        city_cache[city] = result

        return result

    except Exception as e:
        logger.exception("Ошибка определения города: %s", e)
        return None


# =====================================================
# ПЕРЕВОД ВРЕМЕНИ В UTC
# =====================================================

def local_to_julian(day, month, year, hour, minute, tz_name):

    local_time = datetime(
        year, month, day,
        hour, minute
    ).replace(
        tzinfo=ZoneInfo(tz_name)
    )

    utc_time = local_time.astimezone(timezone.utc)

    decimal_hour = (
        utc_time.hour +
        utc_time.minute / 60 +
        utc_time.second / 3600
    )

    jd = swe.julday(
        utc_time.year,
        utc_time.month,
        utc_time.day,
        decimal_hour
    )

    return jd


# =====================================================
# РАСЧЁТ НАТАЛЬНОЙ КАРТЫ
# =====================================================

PLANETS = {
    "Солнце": swe.SUN,
    "Луна": swe.MOON,
    "Меркурий": swe.MERCURY,
    "Венера": swe.VENUS,
    "Марс": swe.MARS,
    "Юпитер": swe.JUPITER,
    "Сатурн": swe.SATURN,
    "Уран": swe.URANUS,
    "Нептун": swe.NEPTUNE,
    "Плутон": swe.PLUTO
}


ASPECTS = {
    "соединение": (0, 8),
    "секстиль": (60, 5),
    "квадрат": (90, 7),
    "трин": (120, 7),
    "оппозиция": (180, 8)
}


def calculate_aspects(positions):

    result = []

    names = list(positions.keys())

    for i in range(len(names)):

        for j in range(i + 1, len(names)):

            p1 = names[i]
            p2 = names[j]

            angle = abs(
                positions[p1]["longitude"] -
                positions[p2]["longitude"]
            )

            angle = min(angle, 360 - angle)

            for aspect_name, values in ASPECTS.items():

                exact_angle, orb_limit = values

                orb = abs(angle - exact_angle)

                if orb <= orb_limit:

                    result.append(
                        f"{p1} — {aspect_name} — {p2} "
                        f"(орбис {orb:.1f}°)"
                    )

    return result


def calculate_chart(day, month, year, hour, minute, city_data):

    jd = local_to_julian(
        day, month, year,
        hour, minute,
        city_data["timezone"]
    )

    positions = {}

    for name, planet_id in PLANETS.items():

        position, ret = swe.calc_ut(
            jd,
            planet_id,
            swe.FLG_MOSEPH | swe.FLG_SPEED
        )

        longitude = position[0]
        speed = position[3]

        positions[name] = {
            "longitude": longitude,
            "sign": zodiac_sign(longitude),
            "degree": longitude % 30,
            "retrograde": speed < 0
        }

    # Асцендент и MC

    latitude = city_data["latitude"]
    longitude = city_data["longitude"]

    try:
        cusps, ascmc = swe.houses_ex(
            jd,
            latitude,
            longitude,
            b'P'
        )

    except Exception:

        # Если система Плацидуса не рассчитывается,
        # используем систему целых знаков для углов
        cusps, ascmc = swe.houses_ex(
            jd,
            latitude,
            longitude,
            b'W'
        )

    asc_longitude = ascmc[0]
    mc_longitude = ascmc[1]

    ascendant = zodiac_sign(asc_longitude)
    mc = zodiac_sign(mc_longitude)

    aspects = calculate_aspects(positions)

    return {
        "positions": positions,
        "ascendant": ascendant,
        "mc": mc,
        "aspects": aspects,
        "city": city_data["city"],
        "timezone": city_data["timezone"]
    }


# =====================================================
# ФОРМАТИРОВАНИЕ КАРТЫ
# =====================================================

def format_chart(chart):

    lines = []

    lines.append("НАТАЛЬНАЯ КАРТА")
    lines.append("")
    lines.append(f"Асцендент: {chart['ascendant']}")
    lines.append(f"MC: {chart['mc']}")
    lines.append("")

    for name, data in chart["positions"].items():

        retro = " R (ретроградная)" if data["retrograde"] else ""

        lines.append(
            f"{name}: {data['sign']} "
            f"{data['degree']:.2f}°{retro}"
        )

    lines.append("")
    lines.append("АСПЕКТЫ")

    if chart["aspects"]:

        lines.extend(chart["aspects"])

    else:

        lines.append("Основные аспекты не обнаружены.")

    return "\n".join(lines)


# =====================================================
# РАЗБОР ДАТЫ И ВРЕМЕНИ
# =====================================================

def parse_birth_data(text):

    pattern = (
        r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})"
        r"\s*[,; ]+\s*(\d{1,2}):(\d{2})"
        r"\s*[,; ]+\s*(.+)"
    )

    match = re.search(pattern, text.strip())

    if not match:
        return None

    day, month, year, hour, minute = map(
        int, match.groups()[:5]
    )

    city = match.group(6).strip()

    try:
        datetime(
            year, month, day,
            hour, minute
        )
    except ValueError:
        return None

    if hour > 23 or minute > 59:
        return None

    return {
        "day": day,
        "month": month,
        "year": year,
        "hour": hour,
        "minute": minute,
        "city": city
    }


# =====================================================
# GROQ — ГЕНЕРАЦИЯ ОТВЕТОВ
# =====================================================

async def ask_ai(prompt):

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.8,
        max_tokens=3500
    )

    return response.choices[0].message.content


async def send_long_message(message, text, reply_markup=None):

    max_length = 3900

    chunks = [
        text[i:i + max_length]
        for i in range(0, len(text), max_length)
    ]

    for index, chunk in enumerate(chunks):

        markup = (
            reply_markup
            if index == len(chunks) - 1
            else None
        )

        await message.reply_text(
            chunk,
            reply_markup=markup
        )


# =====================================================
# START
# =====================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    context.user_data.clear()

    await update.message.reply_text(
        "Привет! Я твой астролог ✨\n\n"
        "Добро пожаловать в Astro Vibe Ovna 💫\n\n"
        "Здесь мы будем разбирать натальные карты, "
        "совместимость и астрологические прогнозы.\n\n"
        "Выбирай интересующий тебя раздел ниже.\n\n"
        "Для натальной карты отправь:\n"
        "15.05.2002, 14:30, Павлодар",
        reply_markup=KLAVIATURA
    )


# =====================================================
# ГОРоскоп ПО ЗНАКУ
# =====================================================

async def vibes_po_znaku(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    znak = query.data.split("znak:", 1)[1]

    today = datetime.now().strftime("%d.%m.%Y")

    await query.message.reply_text(
        f"Смотрю звезды для {znak}... ✨"
    )

    prompt = f"""
    Сделай уникальный гороскоп на сегодня {today}
    для знака {znak}.

    Стиль: тёплый, живой, интересный.

    Блоки:
    1. Твой вайб сегодня — 2-3 предложения.
    2. Любовь.
    3. Деньги и работа.
    4. Совет дня.

    Не придумывай конкретные транзиты.
    Не используй банальные фразы.
    """

    try:

        answer = await ask_ai(prompt)

        await send_long_message(
            query.message,
            answer,
            KLAVIATURA
        )

    except Exception:

        logger.exception("Ошибка гороскопа")

        await query.message.reply_text(
            "Ой, звезды немного капризничают. "
            "Попробуй ещё раз ✨"
        )


# =====================================================
# ОСНОВНОЙ ОБРАБОТЧИК
# =====================================================

async def otvet(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    mode = context.user_data.get("rezhim")

    # ПОДДЕРЖКА

    if text == "💫 Поддержать":

        await update.message.reply_text(
            "Спасибо, что ты со мной! 💫✨\n\n"
            "Поддержать Astro Vibe Ovna можно здесь:\n"
            "https://t.me/tribute/app?startapp=dUt9\n\n"
            "Каждая звёздочка помогает проекту расти! 💖",
            reply_markup=KLAVIATURA
        )

        return

    # ГОРОСКОП

    if text == "🔮 Гороскоп на сегодня":

        context.user_data.clear()

        await update.message.reply_text(
            "Выбери свой знак ✨",
            reply_markup=klaviatura_znakov()
        )

        return

    # НАТАЛЬНАЯ КАРТА

    if text == "✨ Разбор":

        context.user_data.clear()
        context.user_data["rezhim"] = "razbor"

        await update.message.reply_text(
            "Давай смотреть твою натальную карту ✨\n\n"
            "Напиши дату, время и город рождения.\n\n"
            "Например:\n"
            "15.05.2002, 14:30, Павлодар"
        )

        return

    # СОВМЕСТИМОСТЬ

    if text == "❤️ Совместимость":

        context.user_data.clear()
        context.user_data["rezhim"] = "sovmestimost"

        await update.message.reply_text(
            "Давай посмотрим вашу совместимость ❤️\n\n"
            "Сначала отправь данные первого человека:\n"
            "15.05.2002, 14:30, Павлодар"
        )

        return

    # ПРОГНОЗ

    if text == "🌙 Прогноз на месяц":

        context.user_data.clear()
        context.user_data["rezhim"] = "prognoz"

        await update.message.reply_text(
            "Напиши дату, точное время и город рождения.\n\n"
            "Например:\n"
            "15.05.2002, 14:30, Павлодар"
        )

        return

    # КАРТА ДНЯ

    if text == "🃏 Карта дня":

        context.user_data.clear()

        cards = [
            ("Шут", "Новый этап, спонтанность, открытость."),
            ("Маг", "Инициатива, возможности, сила намерения."),
            ("Императрица", "Изобилие, забота, удовольствие."),
            ("Император", "Порядок, ответственность, контроль."),
            ("Влюблённые", "Выбор, чувства, отношения."),
            ("Колесница", "Движение, решительность, победа."),
            ("Сила", "Внутренняя устойчивость, терпение."),
            ("Отшельник", "Пауза, размышления, поиск ответов."),
            ("Колесо Фортуны", "Перемены, поворот событий."),
            ("Справедливость", "Баланс, честность, последствия."),
            ("Звезда", "Надежда, вдохновение, вера."),
            ("Луна", "Интуиция, эмоции, неопределённость."),
            ("Солнце", "Радость, ясность, успех."),
            ("Мир", "Завершение, результат, целостность.")
        ]

        card, meaning = random.choice(cards)

        prompt = f"""
        Карта Таро дня: {card}.
        Основное значение: {meaning}.

        Сделай тёплое и интересное послание дня.
        Добавь:
        1. Главную тему дня.
        2. Совет.
        3. На что обратить внимание.

        Не обещай гарантированных событий.
        """

        try:

            answer = await ask_ai(prompt)

            await send_long_message(
                update.message,
                f"🃏 Твоя карта дня — {card}\n\n{answer}",
                KLAVIATURA
            )

        except Exception:

            logger.exception("Ошибка карты дня")

            await update.message.reply_text(
                f"Твоя карта дня — {card} ✨\n\n{meaning}",
                reply_markup=KLAVIATURA
            )

        return

    # ЕСЛИ НЕТ РЕЖИМА

    if not mode:

        await update.message.reply_text(
            "Выбери нужный раздел в меню ✨",
            reply_markup=KLAVIATURA
        )

        return

    # ПРОВЕРКА ДАННЫХ

    birth = parse_birth_data(text)

    if not birth:

        await update.message.reply_text(
            "Не совсем поняла данные 🙈\n\n"
            "Напиши в формате:\n"
            "15.05.2002, 14:30, Павлодар"
        )

        return

    await update.message.reply_text(
        "Смотрю твою карту... ✨\n"
        "Определяю координаты и рассчитываю положения планет."
    )

    city_data = await get_city_data(birth["city"])

    if not city_data:

        await update.message.reply_text(
            "Не получилось определить город 😔\n\n"
            "Попробуй указать город вместе со страной.\n"
            "Например: Павлодар, Казахстан"
        )

        return

    try:

        chart = calculate_chart(
            birth["day"],
            birth["month"],
            birth["year"],
            birth["hour"],
            birth["minute"],
            city_data
        )

    except Exception:

        logger.exception("Ошибка расчёта карты")

        await update.message.reply_text(
            "Не удалось рассчитать карту. "
            "Проверь дату, время и город рождения."
        )

        return

    chart_text = format_chart(chart)

    # НАТАЛЬНАЯ КАРТА

    if mode == "razbor":

        prompt = f"""
        Сделай базовый, но содержательный разбор натальной карты.

        Данные:
        {chart_text}

        Город: {chart['city']}.

        Разделы:

        1. Общий портрет личности.
        2. Солнце — характер и самореализация.
        3. Луна — эмоции и внутренние потребности.
        4. Асцендент — первое впечатление и поведение.
        5. Меркурий — мышление и общение.
        6. Венера — любовь и симпатии.
        7. Марс — энергия и действия.
        8. Юпитер и Сатурн — развитие и ответственность.
        9. Уран, Нептун и Плутон — дополнительные особенности.
        10. Сильные стороны и зоны развития.

        Учитывай только переданные положения и аспекты.
        Не выдумывай дома и управителей.
        Сделай красивый синтез карты.
        """

        context.user_data.pop("rezhim", None)

        try:

            answer = await ask_ai(prompt)

            await send_long_message(
                update.message,
                answer,
                KLAVIATURA
            )

        except Exception:

            logger.exception("Ошибка разбора")

            await update.message.reply_text(
                "Не удалось получить интерпретацию. "
                "Попробуй немного позже ✨",
                reply_markup=KLAVIATURA
            )

        return

    # СОВМЕСТИМОСТЬ

    if mode == "sovmestimost":

        if "partner1" not in context.user_data:

            context.user_data["partner1"] = {
                "birth": birth,
                "chart": chart
            }

            await update.message.reply_text(
                "Первую карту рассчитала! ✨\n\n"
                "Теперь отправь данные второго человека:\n"
                "21.11.1999, 12:00, Павлодар"
            )

            return

        partner1 = context.user_data["partner1"]

        chart1 = format_chart(partner1["chart"])
        chart2 = chart_text

        prompt = f"""
        Сделай астрологический разбор совместимости пары.

        ПЕРВЫЙ ЧЕЛОВЕК:
        {chart1}

        ВТОРОЙ ЧЕЛОВЕК:
        {chart2}

        Разбери:

        1. Общее притяжение.
        2. Эмоциональная совместимость — Луна.
        3. Любовь и симпатия — Венера.
        4. Страсть и конфликты — Марс.
        5. Общение — Меркурий.
        6. Сильные стороны пары.
        7. Возможные сложности.
        8. Перспективы отношений.
        9. Практический совет паре.

        Сравни реальные положения планет.
        Не придумывай аспекты между картами.
        Не выдумывай проценты совместимости.
        Пиши тепло и деликатно.
        """

        context.user_data.clear()

        try:

            answer = await ask_ai(prompt)

            await send_long_message(
                update.message,
                answer,
                KLAVIATURA
            )

        except Exception:

            logger.exception("Ошибка совместимости")

            await update.message.reply_text(
                "Не удалось завершить анализ пары. "
                "Попробуй ещё раз ✨",
                reply_markup=KLAVIATURA
            )

        return

    # ПРОГНОЗ НА МЕСЯЦ

    if mode == "prognoz":

        now = datetime.now(
            ZoneInfo(city_data["timezone"])
        )

        transit_chart = calculate_chart(
            now.day,
            now.month,
            now.year,
            now.hour,
            now.minute,
            city_data
        )

        transit_text = format_chart(transit_chart)

        prompt = f"""
        Сделай астрологический прогноз на ближайший месяц.

        НАТАЛЬНЫЕ ПОЛОЖЕНИЯ:
        {chart_text}

        ТЕКУЩИЕ ТРАНЗИТНЫЕ ПОЛОЖЕНИЯ:
        {transit_text}

        Дата расчёта: {now.strftime('%d.%m.%Y')}.

        Разделы:

        1. Главная тема месяца.
        2. Любовь и отношения.
        3. Деньги.
        4. Работа и самореализация.
        5. Эмоциональное состояние.
        6. Три совета астролога.

        Важно:
        Не утверждай, что транзитные аспекты уже рассчитаны.
        Сравни положения натальных и транзитных планет.
        Не придумывай даты точных аспектов.
        Не выдавай прогноз за гарантированное событие.
        """

        context.user_data.clear()

        try:

            answer = await ask_ai(prompt)

            await send_long_message(
                update.message,
                answer,
                KLAVIATURA
            )

        except Exception:

            logger.exception("Ошибка прогноза")

            await update.message.reply_text(
                "Не получилось составить прогноз. "
                "Попробуй немного позже ✨",
                reply_markup=KLAVIATURA
            )

        return


# =====================================================
# ЗАПУСК
# =====================================================

def main():

    threading.Thread(
        target=run_flask,
        daemon=True
    ).start()

    application = (
        Application.builder()
        .token(TOKEN_TELEGRAM)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CallbackQueryHandler(
            vibes_po_znaku,
            pattern="^znak:"
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            otvet
        )
    )

    logger.info("Astro Vibe Ovna запущена!")

    application.run_polling()


if __name__ == "__main__":
    main()
