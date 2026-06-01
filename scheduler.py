from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from database import get_active_tasks, mark

scheduler = AsyncIOScheduler()


def now():
    return datetime.utcnow() + timedelta(hours=3)


async def check_tasks(bot):
    tasks = await get_active_tasks()
    current = now()

    for t in tasks:
        task_id, chat_id, text, executor, deadline, status, n24, n2 = t

        try:
            deadline_dt = datetime.strptime(deadline, "%d.%m.%Y %H:%M")
        except:
            continue

        diff = deadline_dt - current

        if diff.total_seconds() <= 0:
            continue

        # 24h
        if diff <= timedelta(hours=24) and n24 == 0:
            await bot.send_message(chat_id, f"⏰ 24 часа: {text}")
            await mark(task_id, "notified_24h")

        # 2h
        if diff <= timedelta(hours=2) and n2 == 0:
            await bot.send_message(chat_id, f"🔥 2 часа: {text}")
            await mark(task_id, "notified_2h")


def setup_scheduler(bot):
    scheduler.add_job(check_tasks, "interval", minutes=1, args=[bot])
    scheduler.start()
