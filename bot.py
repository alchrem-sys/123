import json
import os
from datetime import datetime, timezone
from asyncio import sleep
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("❌ Не знайдено TOKEN у змінних середовища!")

# Директорія для збереження даних
DATA_DIR = "/data"
DATA_FILE = os.path.join(DATA_DIR, "data.json")
os.makedirs(DATA_DIR, exist_ok=True)

# ---------- ЗАВАНТАЖЕННЯ / ЗБЕРЕЖЕННЯ ДАНИХ ----------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

user_data = load_data()
last_reminder_hour = {}  # для відстеження нагадувань по годині

WELCOME_TEXT = (
    "Щоб запустити бота - /start.\n"
    "Писати лише +1;-10;+107;-2.\n"
    "Щоб скинути цифри напиши /reset\n"
    "Цифри повинні бути зі знаком.\n"
    "Кожного дня в 20:00 UTC буде приходити нагадування «прокрути альфу», "
    "пиши «прокрутив», якщо не написав через годину знову прийде таке нагадування.\n"
    "ПИСАТИ ЛИШЕ ЦИФРИ ТА «ПРОКРУТИВ», цей бот більше нічого не розуміє))"
)

# ---------- HANDLERS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"plus": 0.0, "minus": 0.0, "ack": False}
        save_data()
    await update.message.reply_text(WELCOME_TEXT)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data[user_id] = {"plus": 0.0, "minus": 0.0, "ack": False}
    save_data()
    await update.message.reply_text("✅ Дані скинуто. Починай спочатку!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip().lower()

    if user_id not in user_data:
        user_data[user_id] = {"plus": 0.0, "minus": 0.0, "ack": False}
        await update.message.reply_text(WELCOME_TEXT)

    # Якщо користувач відповів "прокрутив"
    if text == "прокрутив":
        user_data[user_id]["ack"] = True
        save_data()
        return

    # Обробка чисел зі знаком
    if text.startswith(("+", "-")):
        try:
            number = float(text)
            if number > 0:
                user_data[user_id]["plus"] += number
            else:
                user_data[user_id]["minus"] += abs(number)

            # округлюємо до 2 знаків
            user_data[user_id]["plus"] = round(user_data[user_id]["plus"], 2)
            user_data[user_id]["minus"] = round(user_data[user_id]["minus"], 2)
            save_data()

            total_plus = user_data[user_id]["plus"]
            total_minus = user_data[user_id]["minus"]
            balance = round(total_plus - total_minus, 2)

            await update.message.reply_text(
                f"✅ Плюс: {total_plus}\n"
                f"❌ Мінус: {total_minus}\n"
                f"💰 Баланс: {balance}"
            )
        except ValueError:
            await update.message.reply_text("Пишіть лише числа зі знаком (+10, -5).")
    else:
        await update.message.reply_text("Пишіть лише числа зі знаком або «прокрутив».")

# ---------- DAILY REMINDER ----------
async def daily_reminder(app):
    last_day = None
    while True:
        now = datetime.now(timezone.utc)
        current_day = now.date()

        # Скидання ack на початку нового дня о 20:00 UTC
        if last_day != current_day and now.hour >= 20:
            for user_id in user_data:
                user_data[user_id]["ack"] = False
            save_data()
            last_day = current_day

        # Надсилання нагадувань о 20:00 та 21:00 UTC
        for user_id, data in user_data.items():
            if now.hour in [20, 21] and not data.get("ack", False):
                last_reminder = last_reminder_hour.get(user_id, None)
                if last_reminder != now.hour:
                    await app.bot.send_message(chat_id=int(user_id), text="🌀 Прокрути альфу!!!!!!!")
                    last_reminder_hour[user_id] = now.hour

        await sleep(60)

# ---------- RUN ----------
async def on_startup(app):
    app.create_task(daily_reminder(app))

app = ApplicationBuilder().token(TOKEN).post_init(on_startup).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("reset", reset))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

print("🤖 Бот працює на Railway Worker!")
app.run_polling()
