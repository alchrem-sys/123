import os
import json
import asyncio
from datetime import datetime, timedelta, timezone
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from upstash_redis import Redis

# -------------------- Налаштування --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ Токен не встановлений!")
    exit(1)

ADMIN_ID = 868931721  # <- твій Telegram ID

# Upstash Redis (ENV змінні)
REDIS_URL = os.getenv("REDIS_URL")
REDIS_TOKEN = os.getenv("REDIS_TOKEN")

if not REDIS_URL or not REDIS_TOKEN:
    print("❌ REDIS_URL або REDIS_TOKEN не встановлені!")
    exit(1)

# Підключення до Upstash Redis
redis = Redis(url=REDIS_URL, token=REDIS_TOKEN)

# -------------------- Функції для користувачів --------------------
def get_user(user_id: str):
    data = redis.get(user_id)
    if data:
        return json.loads(data)
    return {"plus": 0.0, "minus": 0.0, "balance": 0.0, "last_ack": None}

def save_user(user_id: str, user_data: dict):
    redis.set(user_id, json.dumps(user_data))

# -------------------- Команди --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)
    save_user(user_id, user_data)
    await update.message.reply_text(
        "👋 Привіт, Я бот для фіксації плюсів і мінусів на альфі.\n\n"
        "Пиши типу +5 або -3, +3.5 щоб оновити баланс.\n"
        "Команда /reset — скинути баланс.\n\n"
        "Числа типу 3.5 писати тільки через крапку\n"
        "Щодня о 23:00 за Києвом приходить нагадування 🔔 «прокрути альфу».\n"
        "Напиши «прокрутив», щоб підтвердити.\n\n"
        "Знайшли помилку? - @l1oxsha"
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = {"plus": 0.0, "minus": 0.0, "balance": 0.0, "last_ack": None}
    save_user(user_id, user_data)
    await update.message.reply_text("✅ Баланс скинуто!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)

    text = update.message.text.strip().lower()
    if text.startswith(("+", "-")):
        try:
            value = float(text.replace(" ", ""))
            if value > 0:
                user_data["plus"] += value
            else:
                user_data["minus"] += abs(value)

            user_data["balance"] = round(user_data["plus"] - user_data["minus"], 2)
            save_user(user_id, user_data)

            await update.message.reply_text(
    f"✅ Плюс: {round(user_data['plus'], 2)}\n"
    f"❌ Мінус: {round(user_data['minus'], 2)}\n"
    f"💰 Баланс: {round(user_data['balance'], 2)}\n\n"
    f"<a href='https://t.me/l1xosha'>Канал Автора</a>",
    parse_mode="HTML"
)
        except ValueError:
            await update.message.reply_text("Пиши лише числа зі знаком (типу +5 або -3).")
    elif "прокрутив" in text:
        user_data["last_ack"] = datetime.now(timezone.utc).isoformat()
        save_user(user_id, user_data)
        await update.message.reply_text("🔥 Красава, альфа прокручена")
    else:
        await update.message.reply_text("Пиши лише числа або «прокрутив» 😉")

# -------------------- Адмін-розсилка --------------------
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Тільки адміністратор може використовувати цю команду.")
        return

    if not context.args:
        await update.message.reply_text("❌ Вкажи повідомлення для розсилки: /broadcast Текст")
        return

    message = " ".join(context.args)
    success, fail = 0, 0

    keys = redis.keys("*")
    for uid in keys:
        try:
            await context.bot.send_message(chat_id=int(uid), text=message)
            success += 1
        except Exception as e:
            print(f"⚠️ Не вдалося надіслати {uid}: {e}")
            fail += 1

    await update.message.reply_text(f"✅ Розсилка завершена! Успішно: {success}, Не вдалося: {fail}")

# -------------------- Щоденні нагадування --------------------
async def daily_reminder(app: Application):
    while True:
        now = datetime.now(timezone.utc)
        target = now.replace(hour=21, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)

        await asyncio.sleep((target - now).total_seconds())

        keys = redis.keys("*")
        for uid in keys:
            try:
                await app.bot.send_message(chat_id=int(uid), text="🔔 Прокрути альфу!")
            except Exception as e:
                print(f"⚠️ Не вдалося надіслати {uid}: {e}")

        # Друге нагадування через годину
        await asyncio.sleep(7200)
        for uid in keys:
            try:
                await app.bot.send_message(chat_id=int(uid), text="⏰ Якщо ще не прокрутив — саме час!")
            except Exception as e:
                print(f"⚠️ Не вдалося надіслати (2) {uid}: {e}")

# -------------------- Основна функція --------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    async def start_tasks(app: Application):
        asyncio.create_task(daily_reminder(app))

    app.post_init = start_tasks

    print("🤖 Бот запущено з Upstash Redis (синхронний)!")
    app.run_polling()

if __name__ == "__main__":
    main()



