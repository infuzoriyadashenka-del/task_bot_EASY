from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
import re
from datetime import datetime

from database import (
    add_task,
    get_last_tasks,
    get_task,
    get_active_tasks,
    update_task_status
)

router = Router()


def parse_task(text: str):
    executor = re.search(r"@\w+", text)
    date = re.search(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", text)

    executor = executor.group() if executor else "@unknown"
    deadline = date.group() if date else None

    clean = re.sub(r"@\w+", "", text)
    clean = re.sub(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", "", clean)

    return clean.strip(), executor, deadline


@router.message(F.text.startswith("задача:"))
async def create_task(message: Message):

    text = message.text.replace("задача:", "").strip()

    task_text, executor, deadline = parse_task(text)

    if not deadline:
        await message.answer("❌ Укажи дату dd.mm.yyyy hh:mm")
        return

    await add_task(message.chat.id, task_text, executor, deadline)

    last = await get_last_tasks(message.chat.id, 1)

    await message.answer(f"✅ задача #{last[0][0]} добавлена")


@router.message(Command("tasks"))
async def tasks(message: Message):

    rows = await get_active_tasks(message.chat.id)

    if not rows:
        await message.answer("📭 пусто")
        return

    msg = "📌 задачи:\n\n"
    for r in rows:
        msg += f"#{r[0]} {r[2]} {r[3]} {r[4]}\n"

    await message.answer(msg)


@router.message(Command("done"))
async def done(message: Message):

    task_id = int(message.text.split()[1])
    await update_task_status(task_id, "done")

    await message.answer("✅ done")


@router.message(F.text.regexp(r"задача\s+\d+"))
async def info(message: Message):

    task_id = int(re.findall(r"\d+", message.text)[0])
    task = await get_task(task_id, message.chat.id)

    if not task:
        await message.answer("❌ нет")
        return

    await message.answer(f"#{task[0]} {task[2]} {task[3]} {task[4]} {task[5]}")
