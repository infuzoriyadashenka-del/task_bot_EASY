import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from dotenv import load_dotenv

from handlers import router
from database import init_db
from scheduler import setup_scheduler

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing")

if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL is missing")


WEBHOOK_PATH = "/webhook"

logging.basicConfig(level=logging.INFO)


# =========================
# BOT & DISPATCHER
# =========================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# =========================
# WEBHOOK LIFECYCLE
# =========================

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


# =========================
# APP CREATION
# =========================

async def create_app():
    logging.info("Starting bot...")

    await init_db()

    dp.include_router(router)

    setup_scheduler(bot)

    app = web.Application()

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    ).register(app, path=WEBHOOK_PATH)

    return app


# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    app = asyncio.run(create_app())

    web.run_app(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080))
    )

# =========================
# WEBHOOK LIFECYCLE
# =========================

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


# =========================
# APP SETUP
# =========================

async def create_app():
    logging.info("Starting bot...")

    await init_db()

    dp.include_router(router)

    # ⚠️ ВАЖНО: scheduler теперь отдельной функцией
    setup_scheduler(bot)

    app = web.Application()

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    ).register(app, path=WEBHOOK_PATH)

    return app


# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    app = asyncio.run(create_app())

    web.run_app(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080))
    )scheduler = AsyncIOScheduler()


# ---------------- WEBHOOK ----------------

async def on_startup(app: web.Application):
    logging.info("Setting webhook...")

    # всегда очищаем старый webhook
    await bot.delete_webhook(drop_pending_updates=True)

    # ставим новый webhook (ВАЖНО: без двойного /webhook)
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


# ---------------- APP ----------------

async def create_app():
    logging.info("Starting bot...")

    await init_db()

    dp.include_router(router)

    setup_scheduler()

    app = web.Application()

    # webhook lifecycle
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Telegram webhook handler
    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
    ).register(app, path=WEBHOOK_PATH)

    return app


# ---------------- ENTRY POINT ----------------

if __name__ == "__main__":
    app = asyncio.run(create_app())

    web.run_app(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8080))
    )# ---------------- WEBHOOK LIFECYCLE ----------------

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


# ---------------- APP ----------------

async def create_app():

    await init_db()

    dp.include_router(router)

    setup_scheduler()

    app = web.Application()

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

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
    )
