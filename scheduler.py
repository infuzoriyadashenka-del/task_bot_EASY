from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

from database import get_active_tasks, update_task_status, mark_notification

scheduler = AsyncIOScheduler()


def now():
    return datetime.utcnow()


async def check_tasks(bot):
    tasks = await get_active_tasks(None)

    for task in tasks:
        task_id, chat_id, text, executor, deadline, status, n24, n2 = task

        try:
            deadline_dt = datetime.strptime(deadline, "%d.%m.%Y %H:%M")
        except:
            continue

        diff = deadline_dt - now()

        # expired
        if diff.total_seconds() <= 0:
            await update_task_status(task_id, "expired")
            continue

        # 24h
        if diff <= timedelta(hours=24) and n24 == 0:
            await bot.send_message(chat_id, f"⏰ 24h до дедлайна\n{text}")
            await mark_notification(task_id, "notified_24h")

        # 2h
        if diff <= timedelta(hours=2) and n2 == 0:
            await bot.send_message(chat_id, f"🔥 2h до дедлайна\n{text}")
            await mark_notification(task_id, "notified_2h")


async def morning_message(bot):
    import random

    names = ["Вася", "Даша", "Лиза", "Коля"]

    tasks = await get_active_tasks(None)
    chats = set(t[1] for t in tasks)

    for chat_id in chats:
        await bot.send_message(chat_id, f"☀️ Доброе утро! {random.choice(names)}")


def setup_scheduler(bot):
    scheduler.add_job(check_tasks, "interval", minutes=1, args=[bot], max_instances=1)
    scheduler.add_job(morning_message, "cron", hour=7, minute=30, args=[bot])
    scheduler.start()
