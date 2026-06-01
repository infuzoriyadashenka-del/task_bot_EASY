import re
from datetime import datetime, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from database import (
    add_task,
    get_task,
    get_active_tasks,
    get_last_tasks,
    update_task_status,
    update_deadline,
    add_participant,
    get_stats,
    get_rating,
    get_streak
)

router = Router()

UTC_OFFSET = 3


# =========================
# TIME
# =========================

def now():
    return datetime.utcnow() + timedelta(hours=UTC_OFFSET)


# =========================
# USER SAVE
# =========================

async def save_user(message: Message):
    if message.from_user and message.from_user.username:
        await add_participant(
            message.chat.id,
            f"@{message.from_user.username}"
        )


# =========================
# DATE PARSER
# =========================

def parse_human_date(text: str):
    base = now()
    text = text.lower()

    if "завтра" in text:
        return (base + timedelta(days=1)).strftime("%d.%m.%Y %H:%M")

    if "послезавтра" in text:
        return (base + timedelta(days=2)).strftime("%d.%m.%Y %H:%M")

    match = re.search(r"через (\d+) (день|дня|дней)", text)
    if match:
        return (base + timedelta(days=int(match.group(1)))).strftime("%d.%m.%Y %H:%M")

    weekdays = {
        "понедельник": 0,
        "вторник": 1,
        "среду": 2,
        "четверг": 3,
        "пятницу": 4,
        "субботу": 5,
        "воскресенье": 6
    }

    for k, v in weekdays.items():
        if k in text:
            delta = (v - base.weekday() + 7) % 7
            delta = 7 if delta == 0 else delta
            return (base + timedelta(days=delta)).strftime("%d.%m.%Y %H:%M")

    return None


# =========================
# PARSE TASK
# =========================

def parse_task(text: str):

    executor = re.search(r"@\w+", text)
    date = re.search(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", text)

    executor = executor.group() if executor else "@unknown"
    deadline = date.group() if date else parse_human_date(text)

    clean = re.sub(r"@\w+", "", text)
    clean = re.sub(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", "", clean)

    return clean.strip(), executor, deadline


# =========================================================
# CREATE TASK (ГЛАВНЫЙ ФИЛЬТР — БОЛЬШЕ НЕ ЛОМАЕТ ВСЁ)
# =========================================================

@router.message()
async def create_task(message: Message):

    if not message.text:
        return

    text = message.text.lower()

    # ❌ команды не трогаем
    if text.startswith("/"):
        return

    # ❌ системные команды
    if text in ["задачи", "рейтинг", "статистика", "аналитика"]:
        return

    if "сколько осталось" in text or "задача" in text:
        return

    # ❌ если нет признаков задачи — выходим
    if not any(x in text for x in ["@", "завтра", "через", "понедельник",
                                  "вторник", "среду", "четверг",
                                  "пятницу", "субботу", "воскресенье"]):
        return

    await save_user(message)

    task_text, executor, deadline = parse_task(message.text)

    if not deadline:
        await message.answer("❌ Не понял дедлайн")
        return

    await add_task(message.chat.id, task_text, executor, deadline)

    last = await get_last_tasks(message.chat.id, 1)
    task_id = last[0][0] if last else "?"

    await message.answer(
        f"✅ Задача #{task_id}\n\n"
        f"👤 {executor}\n"
        f"📌 {task_text}\n"
        f"⏰ {deadline}"
    )


# =========================
# TASK LIST
# =========================

@router.message(Command("tasks"))
@router.message(lambda m: m.text and m.text.lower().startswith("задачи"))
async def list_tasks(message: Message):

    tasks = await get_active_tasks(message.chat.id)

    if not tasks:
        await message.answer("📭 Нет задач")
        return

    msg = "📌 Задачи:\n\n"

    for t in tasks:
        msg += f"#{t[0]} {t[2]} — {t[3]} — {t[4]}\n"

    await message.answer(msg)


# =========================
# TASK INFO
# =========================

@router.message(lambda m: m.text and "задача" in m.text.lower())
async def get_task_info(message: Message):

    nums = re.findall(r"\d+", message.text)
    if not nums:
        return

    task_id = int(nums[0])

    task = await get_task(task_id, message.chat.id)

    if not task:
        await message.answer("❌ Не найдено")
        return

    try:
        deadline = datetime.strptime(task[4], "%d.%m.%Y %H:%M")
        diff = deadline - now()
        hours = int(diff.total_seconds() // 3600)
    except:
        hours = None

    msg = (
        f"📌 Задача #{task[0]}\n\n"
        f"📄 {task[2]}\n"
        f"👤 {task[3]}\n"
        f"⏰ {task[4]}\n"
        f"📊 {task[5]}\n"
    )

    if hours is not None:
        msg += f"\n⏳ Осталось {hours} часов"

    await message.answer(msg)


# =========================
# DONE
# =========================

@router.message(Command("done"))
async def done_task(message: Message):

    try:
        task_id = int(message.text.split()[1])
    except:
        await message.answer("❌ Формат: /done 1")
        return

    await update_task_status(task_id, "done")
    await message.answer("✅ Выполнено")


# =========================
# CANCEL
# =========================

@router.message(Command("cancel"))
async def cancel_task(message: Message):

    try:
        task_id = int(message.text.split()[1])
    except:
        await message.answer("❌ Формат: /cancel 1")
        return

    await update_task_status(task_id, "cancelled")
    await message.answer("❌ Отменено")


# =========================
# DEADLINE CHANGE
# =========================

@router.message(Command("deadline"))
async def change_deadline(message: Message):

    parts = message.text.split(maxsplit=2)

    if len(parts) < 3:
        await message.answer("❌ Формат: /deadline 1 завтра")
        return

    task_id = int(parts[1])
    new_deadline = parts[2]

    if re.search(r"\d{2}\.\d{2}\.\d{4}", new_deadline):
        deadline = new_deadline
    else:
        deadline = parse_human_date(new_deadline)

    if not deadline:
        await message.answer("❌ Не понял дату")
        return

    await update_deadline(task_id, deadline)
    await message.answer(f"⏰ Обновлено #{task_id}")


# =========================
# TIME LEFT
# =========================

@router.message(lambda m: m.text and "сколько осталось" in m.text.lower())
async def time_left(message: Message):

    nums = re.findall(r"\d+", message.text)
    if not nums:
        return

    task_id = int(nums[0])

    task = await get_task(task_id, message.chat.id)

    if not task:
        await message.answer("❌ Нет задачи")
        return

    deadline = datetime.strptime(task[4], "%d.%m.%Y %H:%M")
    diff = deadline - now()

    await message.answer(f"⏳ Осталось {int(diff.total_seconds() // 3600)} часов")


# =========================
# STATS
# =========================

@router.message(lambda m: m.text and m.text.lower() == "статистика")
async def stats(message: Message):

    rows = await get_stats(message.chat.id)

    msg = "📊 Статистика:\n\n"

    for user, status, count in rows:
        msg += f"{user} — {status}: {count}\n"

    await message.answer(msg)


# =========================
# RATING
# =========================

@router.message(lambda m: m.text and m.text.lower() == "рейтинг")
async def rating(message: Message):

    rows = await get_rating(message.chat.id)

    if not rows:
        await message.answer("📭 Нет данных")
        return

    msg = "🏆 Рейтинг:\n\n"

    for i, (user, score) in enumerate(rows, 1):
        msg += f"{i}. {user} — {score}\n"

    await message.answer(msg)


# =========================
# ANALYTICS
# =========================

@router.message(lambda m: m.text and m.text.lower() == "аналитика")
async def analytics(message: Message):

    stats = await get_stats(message.chat.id)

    msg = "📊 Аналитика:\n\n"

    for user, status, count in stats:
        streak = await get_streak(message.chat.id, user)
        s = streak[0] if streak else 0

        msg += (
            f"{user}\n"
            f"✔ {status}: {count}\n"
            f"🔥 streak: {s}\n\n"
        )

    await message.answer(msg)# =========================

async def save_user(message: Message):
    if message.from_user and message.from_user.username:
        await add_participant(
            message.chat.id,
            f"@{message.from_user.username}"
        )


# =========================
# DATE PARSER
# =========================

def parse_human_date(text: str):
    base = now()
    text = text.lower()

    if "завтра" in text:
        return (base + timedelta(days=1)).strftime("%d.%m.%Y %H:%M")

    if "послезавтра" in text:
        return (base + timedelta(days=2)).strftime("%d.%m.%Y %H:%M")

    match = re.search(r"через (\d+) (день|дня|дней)", text)
    if match:
        return (base + timedelta(days=int(match.group(1)))).strftime("%d.%m.%Y %H:%M")

    weekdays = {
        "понедельник": 0,
        "вторник": 1,
        "среду": 2,
        "четверг": 3,
        "пятницу": 4,
        "субботу": 5,
        "воскресенье": 6
    }

    for k, v in weekdays.items():
        if k in text:
            delta = (v - base.weekday() + 7) % 7
            delta = 7 if delta == 0 else delta
            return (base + timedelta(days=delta)).strftime("%d.%m.%Y %H:%M")

    return None


# =========================
# PARSE TASK
# =========================

def parse_task(text: str):

    executor = re.search(r"@\w+", text)
    date = re.search(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", text)

    executor = executor.group() if executor else "@unknown"
    deadline = date.group() if date else parse_human_date(text)

    clean = re.sub(r"@\w+", "", text)
    clean = re.sub(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", "", clean)

    return clean.strip(), executor, deadline


# =========================
# CREATE TASK (ВАЖНО: НЕ ПЕРЕХВАТЫВАЕТ ВСЁ)
# =========================

@router.message()
async def create_task(message: Message):

    if not message.text:
        return

    text = message.text.lower()

    # ❌ игнор команд
    if text.startswith("/"):
        return

    # ❌ НЕ перехватываем другие функции
    if text.startswith("задачи") or text in ["рейтинг", "статистика", "аналитика"]:
        return

    if "сколько осталось" in text or "задача" in text:
        return

    # ❌ если нет признаков задачи — выходим
    if not any(x in text for x in ["@", "завтра", "через", "понедельник",
                                  "вторник", "среду", "четверг",
                                  "пятницу", "субботу", "воскресенье"]):
        return

    await save_user(message)

    task_text, executor, deadline = parse_task(message.text)

    if not deadline:
        await message.answer("❌ Не понял дедлайн")
        return

    await add_task(message.chat.id, task_text, executor, deadline)

    last = await get_last_tasks(message.chat.id, 1)
    task_id = last[0][0] if last else "?"

    await message.answer(
        f"✅ Задача #{task_id}\n\n"
        f"👤 {executor}\n"
        f"📌 {task_text}\n"
        f"⏰ {deadline}"
    )


# =========================
# TASK LIST
# =========================

@router.message(lambda m: m.text and m.text.lower().startswith("задачи"))
async def list_tasks(message: Message):

    tasks = await get_active_tasks(message.chat.id)

    if not tasks:
        await message.answer("📭 Нет задач")
        return

    msg = "📌 Задачи:\n\n"

    for t in tasks:
        msg += f"#{t[0]} {t[2]} — {t[3]} — {t[4]}\n"

    await message.answer(msg)


# =========================
# SINGLE TASK INFO
# =========================

@router.message(lambda m: m.text and "задача" in m.text.lower())
async def get_task_info(message: Message):

    nums = re.findall(r"\d+", message.text)
    if not nums:
        return

    task_id = int(nums[0])

    task = await get_task(task_id, message.chat.id)

    if not task:
        await message.answer("❌ Не найдено")
        return

    try:
        deadline = datetime.strptime(task[4], "%d.%m.%Y %H:%M")
        diff = deadline - now()
        hours = int(diff.total_seconds() // 3600)
    except:
        hours = None

    msg = (
        f"📌 Задача #{task[0]}\n\n"
        f"📄 {task[2]}\n"
        f"👤 {task[3]}\n"
        f"⏰ {task[4]}\n"
        f"📊 {task[5]}\n"
    )

    if hours is not None:
        msg += f"\n⏳ Осталось {hours} часов"

    await message.answer(msg)


# =========================
# DONE
# =========================

@router.message(Command("done"))
async def done_task(message: Message):

    try:
        task_id = int(message.text.split()[1])
    except:
        await message.answer("❌ Формат: /done 1")
        return

    await update_task_status(task_id, "done")
    await message.answer("✅ Выполнено")


# =========================
# CANCEL
# =========================

@router.message(Command("cancel"))
async def cancel_task(message: Message):

    try:
        task_id = int(message.text.split()[1])
    except:
        await message.answer("❌ Формат: /cancel 1")
        return

    await update_task_status(task_id, "cancelled")
    await message.answer("❌ Отменено")


# =========================
# DEADLINE CHANGE
# =========================

@router.message(Command("deadline"))
async def change_deadline(message: Message):

    parts = message.text.split(maxsplit=2)

    if len(parts) < 3:
        await message.answer("❌ Формат: /deadline 1 завтра")
        return

    task_id = int(parts[1])
    new_deadline = parts[2]

    if re.search(r"\d{2}\.\d{2}\.\d{4}", new_deadline):
        deadline = new_deadline
    else:
        deadline = parse_human_date(new_deadline)

    if not deadline:
        await message.answer("❌ Не понял дату")
        return

    await update_deadline(task_id, deadline)
    await message.answer(f"⏰ Обновлено #{task_id}")


# =========================
# TIME LEFT
# =========================

@router.message(lambda m: m.text and "сколько осталось" in m.text.lower())
async def time_left(message: Message):

    nums = re.findall(r"\d+", message.text)
    if not nums:
        return

    task_id = int(nums[0])

    task = await get_task(task_id, message.chat.id)

    if not task:
        await message.answer("❌ Нет задачи")
        return

    deadline = datetime.strptime(task[4], "%d.%m.%Y %H:%M")
    diff = deadline - now()

    await message.answer(f"⏳ Осталось {int(diff.total_seconds() // 3600)} часов")


# =========================
# STATS
# =========================

@router.message(lambda m: m.text and m.text.lower() == "статистика")
async def stats(message: Message):

    rows = await get_stats(message.chat.id)

    msg = "📊 Статистика:\n\n"

    for user, status, count in rows:
        msg += f"{user} — {status}: {count}\n"

    await message.answer(msg)


# =========================
# RATING
# =========================

@router.message(lambda m: m.text and m.text.lower() == "рейтинг")
async def rating(message: Message):

    rows = await get_rating(message.chat.id)

    if not rows:
        await message.answer("📭 Нет данных")
        return

    msg = "🏆 Рейтинг:\n\n"

    for i, (user, score) in enumerate(rows, 1):
        msg += f"{i}. {user} — {score}\n"

    await message.answer(msg)


# =========================
# ANALYTICS
# =========================

@router.message(lambda m: m.text and m.text.lower() == "аналитика")
async def analytics(message: Message):

    stats = await get_stats(message.chat.id)

    msg = "📊 Аналитика:\n\n"

    for user, status, count in stats:

        streak = await get_streak(message.chat.id, user)
        s = streak[0] if streak else 0

        msg += (
            f"{user}\n"
            f"✔ {status}: {count}\n"
            f"🔥 streak: {s}\n\n"
        )

    await message.answer(msg)
