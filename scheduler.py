from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

from database import (
    get_all_tasks,
    update_task_status,
    mark_notification
)

scheduler = AsyncIOScheduler()


def now():
    return datetime.utcnow()


async def check_tasks(bot):

    tasks = await get_all_tasks()
    current = now()

    for t in tasks:
        task_id, chat_id, text, executor, deadline, status, n24, n2 = t

        try:
            dl = datetime.strptime(deadline, "%d.%m.%Y %H:%M")
        except:
            continue

        diff = dl - current

        # expired
        if diff.total_seconds() <= 0:
            if status == "active":
                await update_task_status(task_id, "expired")
            continue

        # 24h
        if diff <= timedelta(hours=24) and not n24:
            await bot.send_message(chat_id, f"⏰ 24h до дедлайна\n{text}")
            await mark_notification(task_id, "notified_24h")

        # 2h
        if diff <= timedelta(hours=2) and not n2:
            await bot.send_message(chat_id, f"🔥 2h до дедлайна\n{text}")
            await mark_notification(task_id, "notified_2h")


async def morning_message(bot):
    tasks = await get_all_tasks()
    chats = set(t[1] for t in tasks)

    for chat in chats:
        await bot.send_message(chat, "☀️ Доброе утро!")


def setup_scheduler(bot):

    scheduler.add_job(check_tasks, "interval", minutes=1, args=[bot])
    scheduler.add_job(morning_message, "cron", hour=9, minute=0, args=[bot])

    scheduler.start()
