import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from handlers import router
from database import init_db
from scheduler import setup_scheduler

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing")


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

LOCK_FILE = "/tmp/bot.lock"


# =========================
# 🔒 SINGLE INSTANCE LOCK
# =========================

def acquire_lock():
    if os.path.exists(LOCK_FILE):
        print("❌ Bot already running (lock exists)")
        sys.exit(0)

    with open(LOCK_FILE, "w") as f:
        f.write("locked")


def release_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)


# =========================
# STARTUP
# =========================

async def startup():
    logging.info("init db...")
    await init_db()

    logging.info("router...")
    dp.include_router(router)

    logging.info("scheduler...")
    setup_scheduler(bot)


# =========================
# TELEGRAM CLEANUP
# =========================

async def cleanup_telegram():
    logging.info("cleanup webhook + updates...")

    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await bot.get_updates(offset=-1)
    except Exception as e:
        logging.warning(f"cleanup warning: {e}")


# =========================
# POLLING (SAFE WRAPPER)
# =========================

async def start_polling_safe():
    retry = 0

    while True:
        try:
            logging.info("start polling...")
            await dp.start_polling(
                bot,
                allowed_updates=["message"]
            )

        except Exception as e:
            retry += 1
            logging.error(f"polling crashed: {e}")

            wait = min(5 * retry, 30)
            logging.info(f"restart in {wait}s...")
            await asyncio.sleep(wait)


# =========================
# MAIN
# =========================

async def main():
    acquire_lock()

    try:
        await startup()
        await cleanup_telegram()

        await asyncio.sleep(2)

        await start_polling_safe()

    finally:
        release_lock()


# =========================
# ENTRY
# =========================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        release_lock()
        print("stopped")
