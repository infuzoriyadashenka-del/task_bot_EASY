from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

from database import get_all_tasks, mark_notification, update_task_status

scheduler = AsyncIOScheduler()


def now():
    return datetime.utcnow()


async def check_tasks(bot):
    tasks = await get_all_tasks()
    current = now()

    for t in tasks:
        task_id, chat_id, text, executor, deadline, status, n24, n2 = t

        try:
            deadline_dt = datetime.strptime(deadline, "%d.%m.%Y %H:%M")
        except:
            continue

        diff = deadline_dt - current

        if diff.total_seconds() <= 0:
            await update_task_status(task_id, "expired")
            continue

        if diff <= timedelta(hours=24) and n24 == 0:
            await bot.send_message(chat_id, f"⏰ 24h:\n{text}")
            await mark_notification(task_id, "notified_24h")

        if diff <= timedelta(hours=2) and n2 == 0:
            await bot.send_message(chat_id, f"🔥 2h:\n{text}")
            await mark_notification(task_id, "notified_2h")


def setup_scheduler(bot):
    scheduler.add_job(
        check_tasks,
        "interval",
        minutes=1,
        args=[bot],
        max_instances=1,
        coalesce=True
    )
    scheduler.start()
