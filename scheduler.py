from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

from database import get_all_tasks, mark_notification, update_task_status

scheduler = AsyncIOScheduler()

UTC_OFFSET = 3


# =========================
# TIME
# =========================

def now():
    return datetime.utcnow() + timedelta(hours=UTC_OFFSET)


# =========================
# CHECK TASKS
# =========================

async def check_tasks(bot):

    if getattr(check_tasks, "running", False):
        return

    check_tasks.running = True

    try:
        tasks = await get_all_tasks()
        current_time = now()

        for task in tasks:

            task_id = task[0]
            chat_id = task[1]
            text = task[2]
            executor = task[3]
            deadline_str = task[4]
            status = task[5]
            n24 = task[6]
            n2 = task[7]

            try:
                deadline = datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")
            except:
                continue

            diff = deadline - current_time

            # expired
            if diff.total_seconds() <= 0:
                if status == "active":
                    await update_task_status(task_id, "expired")
                continue

            # 24h notification
            if diff <= timedelta(hours=24) and n24 == 0:
                await bot.send_message(
                    chat_id,
                    f"⏰ 24 часа до дедлайна\n\n{text}"
                )
                await mark_notification(task_id, "notified_24h")

            # 2h notification
            if diff <= timedelta(hours=2) and n2 == 0:
                await bot.send_message(
                    chat_id,
                    f"🔥 2 часа до дедлайна\n\n{text}"
                )
                await mark_notification(task_id, "notified_2h")

    finally:
        check_tasks.running = False


# =========================
# MORNING MESSAGE
# =========================

async def morning_message(bot):

    import random

    names = ["Василиса", "Вася", "Даша", "Лиза"]

    name = random.choice(names)

    tasks = await get_all_tasks()
    chats = set(t[1] for t in tasks)

    for chat_id in chats:
        await bot.send_message(
            chat_id,
            f"☀️ Доброе утро!\n\n💩 Какашка дня — {name}"
        )


# =========================
# SETUP
# =========================

def setup_scheduler(bot):

    scheduler.add_job(
        check_tasks,
        "interval",
        minutes=1,
        args=[bot],
        max_instances=1,
        coalesce=True
    )

    scheduler.add_job(
        morning_message,
        "cron",
        hour=7,
        minute=30,
        args=[bot],
        max_instances=1
    )

    scheduler.start()
