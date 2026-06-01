from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
import logging

from database import (
get_all_tasks,
mark_notification,
update_task_status
)

scheduler = AsyncIOScheduler()

UTC_OFFSET = 3

def now():
return datetime.utcnow() + timedelta(hours=UTC_OFFSET)

# =========================

# CHECK TASKS

# =========================

async def check_tasks(bot):

```
if getattr(check_tasks, "running", False):
    return

check_tasks.running = True

try:

    tasks = await get_all_tasks()

    logging.info(
        f"Scheduler check started. Tasks found: {len(tasks)}"
    )

    current_time = now()

    for task in tasks:

        task_id = task[0]
        chat_id = task[1]
        text = task[2]
        executor = task[3]
        deadline_str = task[4]
        status = task[5]
        notified_24h = task[6]
        notified_2h = task[7]
        last_overdue_notice = task[8]

        try:
            deadline = datetime.strptime(
                deadline_str,
                "%d.%m.%Y %H:%M"
            )
        except Exception as e:
            logging.error(
                f"Task #{task_id}: invalid deadline format: {e}"
            )
            continue

        diff = deadline - current_time

        logging.info(
            f"Task #{task_id}: {text} | "
            f"remaining={diff}"
        )

        # =====================
        # EXPIRED
        # =====================

        if diff.total_seconds() <= 0:

            if status == "active":

                logging.info(
                    f"Task #{task_id} expired"
                )

                await update_task_status(
                    task_id,
                    "expired"
                )

                try:
                    await bot.send_message(
                        chat_id,
                        (
                            f"❌ Просрочена задача #{task_id}\n\n"
                            f"👤 {executor}\n"
                            f"📌 {text}"
                        )
                    )
                except Exception as e:
                    logging.error(
                        f"Failed send expired notification: {e}"
                    )

            continue

        # =====================
        # 24 HOURS
        # =====================

        if (
            diff <= timedelta(hours=24)
            and notified_24h == 0
        ):

            try:

                await bot.send_message(
                    chat_id,
                    (
                        f"⏰ До дедлайна 24 часа\n\n"
                        f"📌 {text}\n"
                        f"👤 {executor}\n"
                        f"⏰ {deadline_str}"
                    )
                )

                await mark_notification(
                    task_id,
                    "notified_24h"
                )

                logging.info(
                    f"24h reminder sent for task #{task_id}"
                )

            except Exception as e:

                logging.error(
                    f"Failed send 24h reminder: {e}"
                )

        # =====================
        # 2 HOURS
        # =====================

        if (
            diff <= timedelta(hours=2)
            and notified_2h == 0
        ):

            try:

                await bot.send_message(
                    chat_id,
                    (
                        f"🔥 До дедлайна 2 часа\n\n"
                        f"📌 {text}\n"
                        f"👤 {executor}\n"
                        f"⏰ {deadline_str}"
                    )
                )

                await mark_notification(
                    task_id,
                    "notified_2h"
                )

                logging.info(
                    f"2h reminder sent for task #{task_id}"
                )

            except Exception as e:

                logging.error(
                    f"Failed send 2h reminder: {e}"
                )

except Exception as e:

    logging.exception(
        f"Scheduler error: {e}"
    )

finally:

    check_tasks.running = False
```

# =========================

# MORNING MESSAGE

# =========================

async def morning_message(bot):

```
import random

names = [
    "Василиса",
    "Вася",
    "Даша",
    "Лизочек"
]

name = random.choice(names)

try:

    tasks = await get_all_tasks()

    chats = set()

    for task in tasks:
        chats.add(task[1])

    for chat_id in chats:

        try:

            await bot.send_message(
                chat_id,
                (
                    f"☀️ Доброе утро!\n\n"
                    f"💩 Какашка дня — {name}"
                )
            )

        except Exception as e:

            logging.error(
                f"Morning message failed: {e}"
            )

except Exception as e:

    logging.exception(
        f"Morning job error: {e}"
    )
```

# =========================

# SETUP SCHEDULER

# =========================

def setup_scheduler(bot):

```
scheduler.add_job(
    check_tasks,
    trigger="interval",
    minutes=1,
    args=[bot],
    max_instances=1,
    coalesce=True
)

scheduler.add_job(
    morning_message,
    trigger="cron",
    hour=7,
    minute=30,
    args=[bot],
    max_instances=1
)

scheduler.start()

logging.info("Scheduler started")
```
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

    names = ["Василиса", "Вася", "Даша", "Лизочек"]

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
