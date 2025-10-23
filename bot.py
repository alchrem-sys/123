import json
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes


import os
TOKEN = os.getenv("8435130554:AAFlmudax3DgjOaHI5nYNTrr7eBo-zKQNW0")


DATA_FILE = "data.json"

# ---------- ЗАВАНТАЖЕННЯ / ЗБЕРЕЖЕННЯ ДАНИХ ----------

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

# ---------- ОСНОВНА ЛОГІКА ----------

user_data = load_data()

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

# ---------- ЗАПУСК ----------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))

    print("🤖 Бот запущено. Не закривай це вікно.")
    app.run_polling()

if __name__ == "__main__":
    main()



git config --global user.name "Losha"
PS C:\Users\Losha\Desktop\telegram_bot_online> git config --global user.email "al.chrem@gmail.com"
