import re
from datetime import datetime, timedelta

from aiogram import Router, F
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


def now():
    return datetime.utcnow() + timedelta(hours=UTC_OFFSET)


# =========================
# SAVE USER
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

    if "послезавтра" in text:
        return (base + timedelta(days=2)).strftime("%d.%m.%Y %H:%M")

    if "завтра" in text:
        return (base + timedelta(days=1)).strftime("%d.%m.%Y %H:%M")

    match = re.search(r"через (\d+) (день|дня|дней)", text)
    if match:
        days = int(match.group(1))
        return (base + timedelta(days=days)).strftime("%d.%m.%Y %H:%M")

    match = re.search(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", text)
    if match:
        return match.group()

    return None


# =========================
# TASK PARSER
# =========================

def parse_task(text: str):
    executor_match = re.search(r"@\w+", text)
    executor = executor_match.group() if executor_match else "@unknown"

    deadline = parse_human_date(text)

    clean = re.sub(r"@\w+", "", text)
    clean = re.sub(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", "", clean)

    clean = clean.replace("завтра", "")
    clean = clean.replace("послезавтра", "")
    clean = re.sub(r"через \d+ (день|дня|дней)", "", clean)

    return clean.strip(), executor, deadline


# =========================
# TASKS LIST
# =========================

async def show_tasks(message: Message):

    tasks = await get_active_tasks(message.chat.id)

    if not tasks:
        await message.answer("📭 Нет активных задач")
        return

    msg = "📌 Задачи:\n\n"

    for t in tasks:
        msg += (
            f"#{t[0]}\n"
            f"👤 {t[3]}\n"
            f"📌 {t[2]}\n"
            f"⏰ {t[4]}\n\n"
        )

    await message.answer(msg)


@router.message(Command("tasks"))
async def tasks_command(message: Message):
    await show_tasks(message)


@router.message(F.text.lower() == "задачи")
async def tasks_text(message: Message):
    await show_tasks(message)


# =========================
# STATS
# =========================

@router.message(Command("stats"))
async def stats_command(message: Message):

    rows = await get_stats(message.chat.id)

    if not rows:
        await message.answer("📭 Нет данных")
        return

    msg = "📊 Статистика\n\n"

    for user, status, count in rows:
        msg += f"{user} — {status}: {count}\n"

    await message.answer(msg)


@router.message(F.text.lower() == "статистика")
async def stats_text(message: Message):
    await stats_command(message)


# =========================
# RATING
# =========================

@router.message(Command("rating"))
async def rating_command(message: Message):

    rows = await get_rating(message.chat.id)

    if not rows:
        await message.answer("📭 Нет данных")
        return

    msg = "🏆 Рейтинг\n\n"

    for i, (user, score) in enumerate(rows, start=1):
        msg += f"{i}. {user} — {score}\n"

    await message.answer(msg)


@router.message(F.text.lower() == "рейтинг")
async def rating_text(message: Message):
    await rating_command(message)


# =========================
# ANALYTICS
# =========================

@router.message(Command("analytics"))
async def analytics_command(message: Message):

    rows = await get_stats(message.chat.id)

    if not rows:
        await message.answer("📭 Нет данных")
        return

    msg = "📊 Аналитика\n\n"

    for user, status, count in rows:

        streak_row = await get_streak(
            message.chat.id,
            user
        )

        streak = streak_row[0] if streak_row else 0

        msg += (
            f"{user}\n"
            f"✔ {status}: {count}\n"
            f"🔥 streak: {streak}\n\n"
        )

    await message.answer(msg)


@router.message(F.text.lower() == "аналитика")
async def analytics_text(message: Message):
    await analytics_command(message)


# =========================
# TASK INFO
# =========================

@router.message(F.text.regexp(r"^задача\s+\d+$"))
async def task_info(message: Message):

    nums = re.findall(r"\d+", message.text)

    if not nums:
        return

    task_id = int(nums[0])

    task = await get_task(
        task_id,
        message.chat.id
    )

    if not task:
        await message.answer("❌ Задача не найдена")
        return

    msg = (
        f"📌 Задача #{task[0]}\n\n"
        f"📄 {task[2]}\n"
        f"👤 {task[3]}\n"
        f"⏰ {task[4]}\n"
        f"📊 {task[5]}"
    )

    await message.answer(msg)


# =========================
# DONE
# =========================

@router.message(Command("done"))
async def done_task(message: Message):

    try:
        task_id = int(message.text.split()[1])
    except Exception:
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
    except Exception:
        await message.answer("❌ Формат: /cancel 1")
        return

    await update_task_status(task_id, "cancelled")

    await message.answer("❌ Отменено")


# =========================
# DEADLINE
# =========================

@router.message(Command("deadline"))
async def deadline_command(message: Message):

    parts = message.text.split(maxsplit=2)

    if len(parts) < 3:
        await message.answer(
            "❌ Формат: /deadline 1 завтра"
        )
        return

    task_id = int(parts[1])

    deadline = parse_human_date(parts[2])

    if not deadline:
        await message.answer("❌ Не понял дату")
        return

    await update_deadline(
        task_id,
        deadline
    )

    await message.answer(
        f"⏰ Дедлайн обновлён для задачи #{task_id}"
    )


# =========================
# CREATE TASK
# =========================

@router.message()
async def create_task(message: Message):

    if not message.text:
        return

    await save_user(message)

    text = message.text.lower()

    if text.startswith("/"):
        return

    if text in [
        "задачи",
        "рейтинг",
        "статистика",
        "аналитика"
    ]:
        return

    if (
        "@" not in text
        and "завтра" not in text
        and "послезавтра" not in text
        and "через" not in text
        and not re.search(r"\d{2}\.\d{2}\.\d{4}", text)
    ):
        return

    task_text, executor, deadline = parse_task(message.text)

    if not deadline:
        await message.answer("❌ Не понял дедлайн")
        return

    await add_task(
        message.chat.id,
        task_text,
        executor,
        deadline
    )

    last = await get_last_tasks(
        message.chat.id,
        1
    )

    task_id = last[0][0] if last else "?"

    await message.answer(
        f"✅ Задача #{task_id}\n\n"
        f"👤 {executor}\n"
        f"📌 {task_text}\n"
        f"⏰ {deadline}"
    )
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

    return None


# =========================
# PARSE TASK (НО БЕЗ ПЕРЕХВАТА ВСЕГО)
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
# CREATE TASK (ТОЛЬКО ПО ЯВНОМУ ТРИГГЕРУ)
# =========================

@router.message(F.text.startswith("задача:"))
async def create_task(message: Message):

    await save_user(message)

    text = message.text.replace("задача:", "").strip()

    task_text, executor, deadline = parse_task(text)

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
# TASKS LIST
# =========================

@router.message(Command("tasks"))
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

@router.message(F.text.regexp(r"задача\s+\d+"))
async def task_info(message: Message):

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
# COMMANDS SAFE
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


@router.message(Command("cancel"))
async def cancel_task(message: Message):

    try:
        task_id = int(message.text.split()[1])
    except:
        await message.answer("❌ Формат: /cancel 1")
        return

    await update_task_status(task_id, "cancelled")
    await message.answer("❌ Отменено")


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
# STATS / RATING / ANALYTICS
# =========================

@router.message(Command("stats"))
async def stats(message: Message):

    rows = await get_stats(message.chat.id)

    msg = "📊 Статистика:\n\n"

    for user, status, count in rows:
        msg += f"{user} — {status}: {count}\n"

    await message.answer(msg)


@router.message(Command("rating"))
async def rating(message: Message):

    rows = await get_rating(message.chat.id)

    if not rows:
        await message.answer("📭 Нет данных")
        return

    msg = "🏆 Рейтинг:\n\n"

    for i, (user, score) in enumerate(rows, 1):
        msg += f"{i}. {user} — {score}\n"

    await message.answer(msg)


@router.message(Command("analytics"))
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
