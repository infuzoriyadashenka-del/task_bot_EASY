import random
import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import (
    get_all_active_tasks,
    mark_notification,
    update_last_overdue_notice,
    get_groups
)

UTC_OFFSET = 3

scheduler = AsyncIOScheduler()
BOT = None


# =========================
# TIME
# =========================

def now_msk():
    return datetime.utcnow() + timedelta(hours=UTC_OFFSET)


def parse_dt(dt_str):
    return datetime.strptime(dt_str, "%d.%m.%Y %H:%M")


# =========================
# TASK CHECKER
# =========================

async def check_tasks():

    tasks = await get_all_active_tasks()
    now = now_msk()

    for t in tasks:

        task_id, chat_id, text, executor, deadline, status, n24, n2, last = t

        try:
            dl = parse_dt(deadline)
        except:
            continue

        diff = (dl - now).total_seconds()

        # 24h reminder — теперь с тегом исполнителя
        if 0 < diff <= 86400 and not n24:
            await BOT.send_message(
                chat_id,
                f"⏰ 24ч до дедлайна:\n{text}\n👤 {executor}"
            )
            await mark_notification(task_id, "notified_24h")

        # 2h reminder — теперь с тегом исполнителя
        if 0 < diff <= 7200 and not n2:
            await BOT.send_message(
                chat_id,
                f"⚠️ 2ч осталось:\n{text}\n👤 {executor}"
            )
            await mark_notification(task_id, "notified_2h")

        # overdue spam (каждые 30 минут)
        if now > dl:

            if not last:
                last_time = None
            else:
                try:
                    last_time = datetime.strptime(last, "%Y-%m-%d %H:%M:%S")
                except:
                    last_time = None

            # total_seconds() вместо seconds — чтобы не сбрасывалось каждые сутки
            if (not last_time) or (now - last_time).total_seconds() >= 1800:

                await BOT.send_message(
                    chat_id,
                    f"🚨 ПРОСРОЧКА:\n{text}\n👤 {executor}"
                )

                await update_last_overdue_notice(
                    task_id,
                    now.strftime("%Y-%m-%d %H:%M:%S")
                )


# =========================
# MORNING MESSAGE
# =========================

async def morning_message():

    # ИЗМЕНЕНО: убрали "Лизочек", добавили "Игорь"
    names = ["Даша", "Вася", "Василиса", "Игорь"]

    poop = random.choice(names)
    beauty = random.choice([n for n in names if n != poop])

    groups = await get_groups()

    for g in groups:
        await BOT.send_message(
            g[0],
            f"Всем привет! ☀️\n💩 {poop}\n💅 {beauty}"
        )


# =========================
# START SCHEDULER
# =========================

def setup_scheduler(bot):

    global BOT
    BOT = bot

    scheduler.add_job(check_tasks, "interval", minutes=1)
    scheduler.add_job(morning_message, "cron", hour=10, minute=30, timezone="Europe/Moscow")

    scheduler.start()

    logging.info("Scheduler started cleanly")
