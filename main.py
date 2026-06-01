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

print("BOT_TOKEN =", BOT_TOKEN)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def startup():
    logging.info("Initializing database...")
    await init_db()

    logging.info("Connecting router...")
    dp.include_router(router)

    logging.info("Starting scheduler...")
    setup_scheduler(bot)

    logging.info("Bot initialized")


async def main():
    await startup()

    logging.info("Removing webhook...")

    await bot.delete_webhook(drop_pending_updates=True)

    logging.info("Start polling...")

    await dp.start_polling(
        bot,
        allowed_updates=["message"]
    )


if __name__ == "__main__":
    asyncio.run(main())
