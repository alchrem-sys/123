import json
import os
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

TOKEN = os.environ.get("TOKEN")
DATA_FILE = "data.json"

# ---------- Дані ----------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

user_data = load_data()

# ---------- Команди ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"plus": 0.0, "minus": 0.0, "reminded": False}
        save_data()

    await update.message.reply_text(
        "Щоб запустити бота - /start.\n"
        "Писати лише +1;-10;+107;-2.\n"
        "Щоб скинути цифри напиши /reset\n"
        "Цифри повинні бути зі знаком.\n"
        "Кожного дня в 23:00 Київ буде приходити нагадування «Прокрути альфу!!!!!!!».\n"
        "Пиши «прокрутив», якщо прокрутив.\n"
        "ПИСАТИ ЛИШЕ ЦИФРИ ТА «ПРОКРУТИВ», цей бот більше нічого не розуміє))"
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data[user_id] = {"plus": 0.0, "minus": 0.0, "reminded": False}
    save_data()
    await update.message.reply_text("✅ Дані скинуто. Починай спочатку!")

async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip().lower().replace(",", ".")

    if text == "прокрутив":
        if user_id in user_data:
            user_data[user_id]["reminded"] = True
            save_data()
        return

    try:
        number = float(text)
        if user_id not in user_data:
            user_data[user_id] = {"plus": 0.0, "minus": 0.0, "reminded": False}

        if number > 0:
            user_data[user_id]["plus"] += number
        else:
            user_data[user_id]["minus"] += abs(number)

        save_data()

        total_plus = round(user_data[user_id]["plus"], 2)
        total_minus = round(user_data[user_id]["minus"], 2)
        balance = round(total_plus - total_minus, 2)

        await update.message.reply_text(
            f"✅ Плюс: {total_plus:.2f}\n"
            f"❌ Мінус: {total_minus:.2f}\n"
            f"💰 Баланс: {balance:.2f}"
        )
    except ValueError:
        pass

# ---------- Нагадування ----------
async def daily_reminder(app):
    while True:
        now = datetime.utcnow()
        # Розрахунок часу до 23:00 Київ (UTC+3)
        target = datetime.utcnow().replace(hour=20, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)
        await asyncio.sleep((target - now).total_seconds())

        for user_id, data in user_data.items():
            if not data.get("reminded", False):
                try:
                    await app.bot.send_message(
                        chat_id=int(user_id),
                        text="Прокрути альфу!!!!!!!"
                    )
                except:
                    pass
            data["reminded"] = False
        save_data()
        # Через годину повтор, якщо не написав
        await asyncio.sleep(3600)

# ---------- Запуск ----------
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))

    # Запускаємо нескінченне щоденне нагадування
    asyncio.create_task(daily_reminder(app))

    print("🤖 Бот запущено на Railway Worker!")
    await app.run_polling()

import asyncio
asyncio.run(main())
