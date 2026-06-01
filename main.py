import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from handlers import router
from database import init_db
from scheduler import setup_scheduler

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing")

logging.basicConfig(level=logging.INFO)


# =========================
# BOT
# =========================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================
# STARTUP LOGIC
# =========================

async def on_startup():
    logging.info("Initializing database...")
    await init_db()

    logging.info("Setting up router...")
    dp.include_router(router)

    logging.info("Starting scheduler...")
    setup_scheduler(bot)

    logging.info("🚀 Bot started successfully")


# =========================
# MAIN POLLING LOOP
# =========================

async def main():
    await on_startup()

    await dp.start_polling(bot)


# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    asyncio.run(main())
