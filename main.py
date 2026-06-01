import asyncio
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import init_db
from handlers import router
from scheduler import check_tasks, morning_message


# =========================
# LOAD ENV
# =========================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в .env")


# =========================
# BOT SETUP
# =========================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.include_router(router)

scheduler = AsyncIOScheduler()


# =========================
# STARTUP
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
