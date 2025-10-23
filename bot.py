import json
import os
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ---------- TOKEN ----------
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("❌ TOKEN не знайдено! Додай змінну середовища у Render (Name: TOKEN, Value: твій токен від BotFather)")

# ---------- ДАНІ ----------
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

# ---------- ОСНОВНА ЛОГІКА ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"plus": 0.0, "minus": 0.0}
        save_data()
    await update.message.reply_text(
        "Привіт! 👋 Надішли мені число типу +40 або -20.\n"
        "Я рахую загальний плюс, мінус і баланс 💰"
    )

async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip().replace(",", ".")  # підтримка ком
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
            f"✅ Плюс: {total_plus}\n"
            f"❌ Мінус: {total_minus}\n"
            f"💰 Баланс: {balance}"
        )

    except ValueError:
        await update.message.reply_text("Будь ласка, надішли число типу +50 або -20.")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data[user_id] = {"plus": 0.0, "minus": 0.0}
    save_data()
    await update.message.reply_text("✅ Дані скинуто. Починай спочатку!")

# ---------- TELEGRAM ----------
def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))
    print("🤖 Бот запущено. Не закривай це вікно.")
    app.run_polling()

# ---------- FLASK ----------
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "✅ Telegram бот працює на Render!"

# ---------- MAIN ----------
if __name__ == "__main__":
    # запускаємо бота у потоці
    Thread(target=run_bot).start()
    # запускаємо Flask для Render
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)
