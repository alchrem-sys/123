import json
import os
import asyncio
from threading import Thread
from datetime import datetime, timedelta, timezone
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ---------- TOKEN ----------
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("❌ TOKEN не знайдено! Додай змінну середовища у Render (Name: TOKEN, Value: твій токен від BotFather)")

# ---------- DATA ----------
DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

user_data = load_data()

# ---------- TELEGRAM HANDLERS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"plus": 0.0, "minus": 0.0, "last_response": None}
        save_data()
    await update.message.reply_text("Привіт! 👋 Я буду нагадувати тобі покрутити альфу щодня о 20:00 UTC!")

async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip().lower()
    if user_id not in user_data:
        user_data[user_id] = {"plus": 0.0, "minus": 0.0, "last_response": None}

    if text == "покрутив":
        user_data[user_id]["last_response"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        save_data()
        await update.message.reply_text("🔥 Молодець! Побачимось завтра 😉")
        return

    # звичайна логіка чисел
    text = text.replace(",", ".")
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
        await update.message.reply_text("Будь ласка, надішли число типу +50 або -20 або напиши 'покрутив'.")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data[user_id] = {"plus": 0.0, "minus": 0.0, "last_response": None}
    save_data()
    await update.message.reply_text("✅ Дані скинуто. Починай спочатку!")

# ---------- Нагадування ----------
async def send_reminders(app):
    while True:
        now = datetime.now(timezone.utc)
        hour = now.hour

        if hour in [20, 21]:
            for chat_id, data in user_data.items():
                last = data.get("last_response")
                if not last:
                    await app.bot.send_message(chat_id=int(chat_id), text="Покрути альфу!!!!!!! 🔥")
                    continue

                last_dt = datetime.strptime(last, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                # Якщо користувач не відповів сьогодні
                if last_dt.date() < now.date() and hour >= 20:
                    await app.bot.send_message(chat_id=int(chat_id), text="Покрути альфу!!!!!!! 🔥")

        await asyncio.sleep(3600)  # перевіряти щогодини

# ---------- TELEGRAM ----------
async def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))

    asyncio.create_task(send_reminders(app))
    print("🤖 Бот запущено.")
    await app.run_polling()

# ---------- FLASK ----------
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "✅ Telegram бот працює на Render!"

# ---------- MAIN ----------
if __name__ == "__main__":
    # Flask у потоці
    port = int(os.environ.get("PORT", 10000))
    Thread(target=lambda: flask_app.run(host="0.0.0.0", port=port)).start()

    # Бот у головному потоці
    asyncio.run(run_bot())
