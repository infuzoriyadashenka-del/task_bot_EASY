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


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def main():

    logging.info("init db...")
    await init_db()

    logging.info("router...")
    dp.include_router(router)

    logging.info("scheduler...")
    setup_scheduler(bot)

    logging.info("start polling...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
