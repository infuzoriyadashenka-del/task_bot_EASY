import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from handlers import router
from database import init_db
from scheduler import setup_scheduler

# =========================
# ENV
# =========================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing")


# =========================
# LOGGING
# =========================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# =========================
# BOT INIT
# =========================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================
# STARTUP
# =========================

async def startup():
    logging.info("router...")
    dp.include_router(router)

    logging.info("init db...")
    await init_db()

    logging.info("scheduler...")
    setup_scheduler(bot)


# =========================
# MAIN LOOP
# =========================

async def main():
    await startup()

    # 💥 КРИТИЧНО: убираем webhook полностью
    logging.info("deleting webhook (safety)...")
    await bot.delete_webhook(drop_pending_updates=True)

    logging.info("start polling...")

    await dp.start_polling(
        bot,
        allowed_updates=["message"]
    )


# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("bot stopped")
