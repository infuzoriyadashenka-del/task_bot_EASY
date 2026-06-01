import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from handlers import router
from database import init_db
from scheduler import setup_scheduler

# =========================

# CONFIG

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

# BOT

# =========================

bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()

# =========================

# STARTUP

# =========================

async def startup():

```
logging.info("Initializing database...")

await init_db()

logging.info("Connecting router...")

dp.include_router(router)

logging.info("Starting scheduler...")

setup_scheduler(bot)

logging.info("Bot initialized")
```

# =========================

# MAIN

# =========================

async def main():

```
await startup()

logging.info("Removing webhook...")

await bot.delete_webhook(
    drop_pending_updates=True
)

logging.info("Start polling...")

await dp.start_polling(
    bot,
    allowed_updates=["message"]
)
```

# =========================

# ENTRY POINT

# =========================

if **name** == "**main**":

```
try:

    asyncio.run(main())

except (KeyboardInterrupt, SystemExit):

    logging.info("Bot stopped")
```
