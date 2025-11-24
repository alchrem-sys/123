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
    redis.sadd("users", user_id)  # Для розсилки

# -------------------- Команди --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = get_user(user_id)
    save_user(user_id, user_data)
    text_safe = '<a href="https://t.me/l1xosha">Канал Автора</a>'
    await update.message.reply_text(
        "👋 Привіт! Я бот для фіксації плюсів і мінусів на альфі.\n\n"
        "Пиши типу +5 або -3, +3.5 щоб оновити баланс.\n"
        "Команда /reset — скинути баланс.\n\n"
        "Числа типу 3.5 писати тільки через крапку.\n"
        "Щодня о 23:00 за Києвом приходить нагадування 🔔 «прокрути альфу».\n"
        "Напиши «прокрутив», щоб підтвердити.\n\n"
        f"Знайшли помилку? - {text_safe}",
        parse_mode="HTML"
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = {"plus": 0.0, "minus": 0.0, "balance": 
