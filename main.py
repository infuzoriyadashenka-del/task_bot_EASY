import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from handlers import router
from scheduler import check_tasks, morning_message
from database import init_db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in environment variables")

# ---------------- LOGGING ----------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ---------------- BOT ----------------

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()


# ---------------- STARTUP CLEANUP ----------------

async def on_startup():
    """
    ВАЖНО:
    Убирает webhook и старые pending updates,
    чтобы убрать TelegramConflictError
    """
    logging.info("Cleaning webhook and pending updates...")

    await bot.delete_webhook(drop_pending_updates=True)

    logging.info("Webhook cleared")


# ---------------- SCHEDULER ----------------

def setup_scheduler():
    """
    Планировщик задач:
    - проверка дедлайнов каждую минуту
    - утреннее сообщение в 10:30 UTC+3 (07:30 UTC)
    """

    scheduler.add_job(check_tasks, "interval", minutes=1, args=[bot])
    scheduler.add_job(morning_message, "cron", hour=7, minute=30, args=[bot])

    scheduler.start()
    logging.info("Scheduler started")


# ---------------- MAIN ----------------

async def main():
    logging.info("Initializing database...")
    await init_db()

    logging.info("Starting bot...")

    # cleanup Telegram state (ВАЖНО для Railway)
    await on_startup()

    # register handlers
    dp.include_router(router)

    # scheduler
    setup_scheduler()

    logging.info("🚀 Bot started successfully")

    # start polling
    await dp.start_polling(bot)


# ---------------- ENTRY POINT ----------------

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped manually")
    except Exception as e:
        logging.error(f"Fatal error: {e}")# STARTUP
# =========================

async def on_startup():
    await init_db()

    # проверка задач каждую минуту
    scheduler.add_job(
        check_tasks,
        "interval",
        minutes=1,
        args=[bot]
    )

    # утреннее сообщение (UTC+3 логика внутри scheduler)
    scheduler.add_job(
        morning_message,
        "cron",
        hour=7,
        minute=30,
        args=[bot]
    )

    scheduler.start()

    print("🚀 Bot started successfully")


# =========================
# MAIN
# =========================

async def main():

    await on_startup()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
