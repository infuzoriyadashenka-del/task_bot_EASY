from datetime import datetime, timedelta
import random

from database import (
    get_all_tasks,
    mark_notification,
    update_task_status,
    update_last_overdue_notice,
    add_penalty,
    update_streak
)

UTC_OFFSET = 3


def now():
    return datetime.utcnow() + timedelta(hours=UTC_OFFSET)


# =========================
# TASK CHECKER
# =========================

async def check_tasks(bot):

    tasks = await get_all_tasks()
    current_time = now()

    for task in tasks:

        task_id = task[0]
        chat_id = task[1]
        task_text = task[2]
        executor = task[3]
        deadline_str = task[4]
        status = task[5]
        notified_24h = task[6]
        notified_2h = task[7]
        last_notice = task[8]

        try:
            deadline = datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")
        except:
            continue

        diff = deadline - current_time

        # =========================
        # 24 HOURS WARNING
        # =========================
        if (
            status == "active"
            and diff <= timedelta(hours=24)
            and diff > timedelta(hours=2)
            and notified_24h == 0
        ):
            await bot.send_message(
                chat_id,
                f"⏰ Осталось 24 часа\n\n"
                f"👤 {executor}\n"
                f"📌 {task_text}"
            )

            await mark_notification(task_id, "notified_24h")

        # =========================
        # 2 HOURS WARNING
        # =========================
        if (
            status == "active"
            and diff <= timedelta(hours=2)
            and diff > timedelta(minutes=0)
            and notified_2h == 0
        ):
            await bot.send_message(
                chat_id,
                f"🔥 Осталось 2 часа\n\n"
                f"👤 {executor}\n"
                f"📌 {task_text}"
            )

            await mark_notification(task_id, "notified_2h")

        # =========================
        # EXPIRED TASK LOGIC
        # =========================
        if diff.total_seconds() <= 0:

            # перевести в expired
            if status == "active":
                await update_task_status(task_id, "expired")

                # ❌ ШТРАФ -1
                await add_penalty(chat_id, executor, -1)

                # 🔥 СБРОС streak
                await update_streak(chat_id, executor, 0, reset=True)

            overdue = abs(diff)
            days = overdue.days
            hours = overdue.seconds // 3600

            send_notice = False

            # анти-спам (раз в 30 минут)
            if not last_notice:
                send_notice = True
            else:
                try:
                    last_dt = datetime.strptime(last_notice, "%d.%m.%Y %H:%M")

                    if (current_time - last_dt) >= timedelta(minutes=30):
                        send_notice = True

                except:
                    send_notice = True

            if send_notice:

                await bot.send_message(
                    chat_id,
                    f"⚠️ ПРОСРОЧКА\n\n"
                    f"👤 {executor}\n"
                    f"📌 {task_text}\n\n"
                    f"⏱ Просрочено: {days} дн. {hours} ч."
                )

                await update_last_overdue_notice(
                    task_id,
                    current_time.strftime("%d.%m.%Y %H:%M")
                )


# =========================
# MORNING MESSAGE
# =========================

async def morning_message(bot):

    names = ["Василиса", "Вася", "Даша", "Лизочек"]

    poop = random.choice(names)
    beauty = random.choice(names)

    chats = set()

    tasks = await get_all_tasks()

    for t in tasks:
        chats.add(t[1])

    for chat_id in chats:

        await bot.send_message(
            chat_id,
            "☀️ Доброе утро!\n\n"
            f"💩 Какашка дня — {poop}\n"
            f"💄 Красотка дня — {beauty}"
        )
