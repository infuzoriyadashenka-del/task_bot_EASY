import re
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message

from database import add_task, get_active_tasks

router = Router()


def now():
    return datetime.utcnow() + timedelta(hours=3)


def parse_deadline(text: str):
    base = now()
    text = text.lower()

    if "завтра" in text:
        return (base + timedelta(days=1)).strftime("%d.%m.%Y %H:%M")

    if "послезавтра" in text:
        return (base + timedelta(days=2)).strftime("%d.%m.%Y %H:%M")

    match = re.search(r"через (\d+)", text)
    if match:
        return (base + timedelta(days=int(match.group(1)))).strftime("%d.%m.%Y %H:%M")

    return None


def parse_task(text):
    executor = re.search(r"@\w+", text)
    executor = executor.group() if executor else "@unknown"

    deadline = parse_deadline(text)

    clean = re.sub(r"@\w+", "", text).strip()

    return clean, executor, deadline


# CREATE TASK (СУПЕР СТАБИЛЬНО)
@router.message(F.text)
async def create(message: Message):

    if message.text.startswith("/"):
        return

    if "задача" not in message.text.lower():
        return

    text = message.text.lower().replace("задача", "").strip()

    task, executor, deadline = parse_task(text)

    if not deadline:
        await message.answer("❌ не понял дедлайн")
        return

    await add_task(message.chat.id, task, executor, deadline)

    await message.answer(
        f"✅ задача создана\n"
        f"{executor}\n"
        f"{task}\n"
        f"{deadline}"
    )


@router.message(F.text.startswith("/tasks"))
async def tasks(message: Message):

    tasks = await get_active_tasks()

    if not tasks:
        await message.answer("пусто")
        return

    msg = "📌 задачи:\n\n"

    for t in tasks:
        msg += f"#{t[0]} {t[2]} ({t[3]}) — {t[4]}\n"

    await message.answer(msg)
