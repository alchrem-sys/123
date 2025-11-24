import os
import json
import asyncio
from datetime import datetime, timedelta, timezone
from collections import Counter

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.error import Forbidden, BadRequest, RetryAfter, TimedOut

from upstash_redis import Redis

# -------------------- Налаштування --------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ BOT_TOKEN не встановлений в ENV")
    exit(1)

ADMIN_ID = 868931721  # <- твій Telegram ID (заміни, якщо потрібно)

REDIS_URL = os.getenv("REDIS_URL")
REDIS_TOKEN = os.getenv("REDIS_TOKEN")
if not REDIS_URL or not REDIS_TOKEN:
    print("❌ REDIS_URL або REDIS_TOKEN не встановлені в ENV")
    exit(1)

redis = Redis(url=REDIS_URL, token=REDIS_TOKEN)

# -------------------- Утиліти --------------------
def safe_loads(data):
    """Гарантовано повертає dict або None."""
    if data is None:
        return None
    if isinstance(data, bytes):
        try:
            data = data.decode("utf-8")
        except Exception:
            return None
    if isinstance(data, str):
        try:
            return json.loads(data)
        except Exception:
            return None
    return None

def safe_get_user(user_id: str):
    """Отримує user data з Redis, повертає dict (стандартний формат, якщо пусто)."""
    raw = redis.get(user_id)
    parsed = safe_loads(raw)
    if parsed and isinstance(parsed, dict):
        return parsed
    return {"plus": 0.0, "minus": 0.0, "balance": 0.0, "last_ack": None}

def save_user(user_id: str, user_data: dict):
    """Зберігає user_data і додає user_id у множину 'users' для зручності."""
    redis.set(user_id, json.dumps(user_data))
    # Зберігаємо як string, щоб уникнути байтів/ламаних форматів
    try:
        redis.sadd("users", str(user_id))
    except Exception:
        # Якщо немає множини або Upstash поводиться інакше — ігноруємо помилку
        pass

def scan_all_keys(match="*", count=100):
    """Сканує всі ключі через SCAN і повертає список ключів (synchronous)."""
    keys = []
    try:
        cursor = 0
        while True:
            res = redis.scan(cursor, match=match, count=count)
            # Upstash-Python scan може повертати tuple (next_cursor, [keys...])
            # або dict-like — обробимо обидва випадки
            if isinstance(res, (list, tuple)) and len(res) >= 2:
                cursor = int(res[0])
                batch = res[1] or []
            elif isinstance(res, dict) and "cursor" in res and "keys" in res:
                cursor = int(res["cursor"])
                batch = res["keys"] or []
            else:
                # Несподіваний формат — спробуємо брати все як список
                batch = res or []
                cursor = 0

            # Декодуємо байти, якщо потрібно
            for k in batch:
                if isinstance(k, bytes):
                    try:
                        k = k.decode("utf-8")
                    except Exception:
                        continue
                keys.append(k)

            if cursor == 0:
                break
    except Exception as e:
        print(f"scan_all_keys error: {e}")
    return keys

# -------------------- Команди --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = safe_get_user(user_id)
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
        parse_mode="HTML",
        disable_web_page_preview=True
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = {
        "plus": 0.0,
        "minus": 0.0,
        "balance": 0.0,
        "last_ack": None
    }
    save_user(user_id, user_data)
    await update.message.reply_text("✅ Баланс скинуто!")

# -------------------- Обробка тексту --------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    # Отримаємо і збережемо користувача одразу (щоб був у базі)
    user_data = safe_get_user(user_id)
    save_user(user_id, user_data)

    text = (update.message.text or "").strip().lower()

    if text.startswith(("+", "-")):
        try:
            value = float(text.replace(" ", ""))
            if value > 0:
                user_data["plus"] = user_data.get("plus", 0.0) + value
            else:
                user_data["minus"] = user_data.get("minus", 0.0) + abs(value)

            user_data["balance"] = round(user_data.get("plus", 0.0) - user_data.get("minus", 0.0), 2)
            save_user(user_id, user_data)

            text_safe = '<a href="https://t.me/+CYIi22BbbV5lZWZi">Канал Автора</a>'
            await update.message.reply_text(
                f"✅ Плюс: {user_data['plus']:.2f}\n"
                f"❌ Мінус: {user_data['minus']:.2f}\n"
                f"💰 Баланс: {user_data['balance']:.2f}\n\n"
                f"{text_safe}",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        except ValueError:
            await update.message.reply_text("Пиши лише числа зі знаком (типу +5 або -3).")
        return

    if "прокрутив" in text:
        user_data["last_ack"] = datetime.now(timezone.utc).isoformat()
        save_user(user_id, user_data)
        await update.message.reply_text("🔥 Красава, альфа прокручена")
        return

    await update.message.reply_text("Пиши лише числа або «прокрутив» 😉")

# -------------------- Діагностика --------------------
async def debug_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Тільки адміністратор.")
        return

    keys = scan_all_keys(match="*")
    # фільтруємо тільки цифрові ключі (user_id)
    user_keys = [k for k in keys if isinstance(k, str) and k.isdigit()]
    sample = user_keys[:20]
    await update.message.reply_text(
        f"🔎 У базі знайдено ключів: {len(keys)}\n"
        f"📥 Користувачів (numeric keys): {len(user_keys)}\n"
        f"Приклади (до 20): {sample}"
    )

# -------------------- Покращена розсилка --------------------
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Тільки адміністратор може використовувати цю команду.")
        return

    if not context.args:
        await update.message.reply_text("❌ Вкажи повідомлення: /broadcast Текст")
        return

    message = " ".join(context.args)
    keys = scan_all_keys(match="*")
    # залишаємо тільки цифрові ключі — решта ігноруємо
    user_keys = []
    for k in keys:
        if isinstance(k, bytes):
            try:
                k = k.decode("utf-8")
            except Exception:
                continue
        if isinstance(k, str) and k.isdigit():
            user_keys.append(k)

    success = 0
    fail = 0
    errors = Counter()

    for uid in user_keys:
        try:
            chat_id = int(uid)
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            success += 1
        except Forbidden:
            errors["Forbidden"] += 1
            fail += 1
        except BadRequest:
            errors["BadRequest"] += 1
            fail += 1
        except RetryAfter as e:
            errors["RetryAfter"] += 1
            await update.message.reply_text(f"⏳ Rate limit від Telegram: retry after {getattr(e, 'retry_after', 'N/A')}s. Припиняю розсилку.")
            break
        except TimedOut:
            errors["TimedOut"] += 1
            fail += 1
        except Exception as e:
            errors[type(e).__name__] += 1
            fail += 1

    summary_lines = [
        f"✅ Успішно: {success}",
        f"❌ Помилок: {fail}",
        f"📦 Всього ключів (SCAN): {len(keys)}",
        f"👥 Numeric user keys: {len(user_keys)}"
    ]
    if errors:
        summary_lines.append("Деталі помилок:")
        for k, v in errors.items():
            summary_lines.append(f"  - {k}: {v}")

    await update.message.reply_text("\n".join(summary_lines))

# -------------------- Щоденні нагадування --------------------
async def daily_reminder(app):
    while True:
        now = datetime.now(timezone.utc)
        # Київ 23:00 -> UTC 21:00 (з урахуванням DST це може змінюватись)
        target = now.replace(hour=21, minute=0, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)

        await asyncio.sleep((target - now).total_seconds())

        keys = scan_all_keys(match="*")
        user_keys = [k for k in keys if isinstance(k, str) and k.isdigit()]

        for uid in user_keys:
            try:
                await app.bot.send_message(
                    chat_id=int(uid),
                    text="🔔 Прокрути альфу!",
                    disable_web_page_preview=True
                )
            except Exception as e:
                print(f"Нагадування — не вдалося надіслати {uid}: {e}")

        # Друге нагадування через 2 години
        await asyncio.sleep(7200)
        for uid in user_keys:
            try:
                await app.bot.send_message(
                    chat_id=int(uid),
                    text="⏰ Якщо ще не прокрутив — саме час!",
                    disable_web_page_preview=True
                )
            except Exception as e:
                print(f"Нагадування2 — не вдалося надіслати {uid}: {e}")

# -------------------- Основна функція --------------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("debug_users", debug_users))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    async def start_tasks(app):
        # стартуємо фонове завдання (нагадування)
        asyncio.create_task(daily_reminder(app))

    app.post_init = start_tasks

    print("🤖 Бот запущено з Upstash Redis!")
    app.run_polling()

if __name__ == "__main__":
    main()
