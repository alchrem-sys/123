import json
import os
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise ValueError("❌ Не знайдено TOKEN у змінних середовища!")

# ---------- ФАЙЛ ДЛЯ ЗБЕРЕЖЕННЯ ----------
DATA_DIR = "/data"  # постійна директорія в Railway (Volume)
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

# ---------- ДАНІ ----------
user_data = load_data()

# ---------- ЛОГІКА ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"plus": 0.0, "minus": 0.0}
        save_data()
    await update.message.reply_text("Привіт! 👋 Я рахую твій баланс. Дані тепер зберігаються навіть після перезапуску ✅")

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
