import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiohttp import web
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from handlers import router
from scheduler import check_tasks, morning_message
from database import init_db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing")

if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL is missing")

WEBHOOK_PATH = "/webhook"

# ---------------- BOT ----------------

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

logging.basicConfig(level=logging.INFO)


# ---------------- WEBHOOK SETUP ----------------

async def on_startup(app: web.Application):
    logging.info("Setting webhook...")

    await bot.delete_webhook(drop_pending_updates=True)

    await bot.set_webhook(
        url=f"{WEBHOOK_URL}{WEBHOOK_PATH}"
    )

    logging.info("Webhook set successfully")


async def on_shutdown(app: web.Application):
    logging.info("Shutting down bot...")
    await bot.delete_webhook()


# ---------------- SCHEDULER ----------------

def setup_scheduler():
    scheduler.add_job(check_tasks, "interval", minutes=1, args=[bot])
    scheduler.add_job(morning_message, "cron", hour=7, minute=30, args=[bot])
    scheduler.start()
    logging.info("Scheduler started")


# ---------------- APP FACTORY ----------------

async def create_app():

    await init_db()

    dp.include_router(router)

    setup_scheduler()

    app = web.Application()

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # aiohttp webhook handler
    from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    return app


# ---------------- ENTRY POINT ----------------

if __name__ == "__main__":
    logging.info("Starting bot...")

    app = asyncio.run(create_app())

    web.run_app(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080))
    )    )

    logging.info("Webhook set successfully")


# ---------------- SCHEDULER ----------------

def setup_scheduler():
    scheduler.add_job(check_tasks, "interval", minutes=1, args=[bot])
    scheduler.add_job(morning_message, "cron", hour=7, minute=30, args=[bot])
    scheduler.start()


# ---------------- APP ----------------

async def main():
    await init_db()

    dp.include_router(router)

    setup_scheduler()

    await on_startup()

    app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    ).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    logging.info("🚀 Webhook bot started")

    return app


# ---------------- RUN ----------------

if __name__ == "__main__":
    web.run_app(
        asyncio.run(main()),
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080))
    )    """
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
