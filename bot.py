import json
import os
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("❌ Не знайдено TOKEN у змінних середовища!")

DATA_DIR = "/data"
DATA_FILE = os.path.join(DATA_DIR, "data.json")
os.makedirs(DATA_DIR, exist_ok=True)

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

user_data = load_data()
last_ack = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"plus": 0.0, "minus": 0.0}
        save_data()
    await update.message.reply_text(
        "Привіт! 👋 Надішли мені число типу +40 або -20.\nЯ рахую загальний плюс, мінус і баланс 💰"
    )

async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip().replace(",", ".")
    if user_id not in user_data:
        user_data[user_id] = {"plus": 0.0, "minus": 0.0}

    try:
        number = float(text)
        if number > 0:
            user_data[user_id]["plus"] += number
        else:
            user_data[user_id]["minus"] += abs(number)
        save_data()

        total_plus = user_data[user_id]["plus"]
        total_minus = user_data[user_id]["minus"]
        balance = total_plus - total_minus

        await update.message.reply_text(
            f"✅ Плюс: {total_plus}\n❌ Мінус: {total_minus}\n💰 Баланс: {balance}"
        )
    except ValueError:
        await update.message.reply_text("Будь ласка, надішли число типу +50 або -20.")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data[user_id] = {"plus": 0.0, "minus": 0.0}
    save_data()
    await update.message.reply_text("✅ Дані скинуто. Починай спочатку!")

async def pokrutyv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_ack
    last_ack = datetime.now(timezone.utc).hour
    await update.message.reply_text("✅ Добре, не нагадаю ще раз!")

# Фонове нагадування
async def daily_reminder(app):
    global last_ack
    while True:
        from asyncio import sleep
        now = datetime.now(timezone.utc)
        if now.hour in [20, 21]:
            if last_ack != now.hour:
                for user_id in user_data.keys():
                    await app.bot.send_message(chat_id=int(user_id), text="🌀 Покрути альфу!!!!!!!")
                last_ack = now.hour
        await sleep(60)

# Ініціалізація
async def on_startup(app):
    app.create_task(daily_reminder(app))

# ---------- RUN ----------
app = ApplicationBuilder().token(TOKEN).post_init(on_startup).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("reset", reset))
app.add_handler(CommandHandler("pokruviv", pokrutyv))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))

print("🤖 Бот працює на Railway Worker!")
app.run_polling()
