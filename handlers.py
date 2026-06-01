import re
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from database import (
    add_task,
    get_task,
    get_last_tasks,
    update_task_status,
    update_deadline
)

router = Router()


def parse_task(text: str):
    executor = re.search(r"@\w+", text)
    date = re.search(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", text)

    executor = executor.group() if executor else "@user"
    deadline = date.group() if date else None

    clean = re.sub(r"@\w+", "", text)
    clean = re.sub(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", "", clean)

    return clean.strip(), executor, deadline


@router.message(F.text.startswith("задача:"))
async def create_task(message: Message):

    text = message.text.replace("задача:", "").strip()

    task, executor, deadline = parse_task(text)

    if not deadline:
        await message.answer("❌ Укажи дату: dd.mm.yyyy hh:mm")
        return

    await add_task(message.chat.id, task, executor, deadline)

    last = await get_last_tasks(message.chat.id, 1)
    task_id = last[0][0]

    await message.answer(f"✅ Задача #{task_id} создана")


@router.message(Command("tasks"))
async def tasks(message: Message):

    data = await get_last_tasks(message.chat.id, 20)

    if not data:
        await message.answer("Нет задач")
        return

    msg = "📌 Задачи:\n\n"

    for t in data:
        msg += f"#{t[0]} {t[2]} ({t[3]})\n"

    await message.answer(msg)


@router.message(Command("done"))
async def done(message: Message):
    task_id = int(message.text.split()[1])
    await update_task_status(task_id, "done")
    await message.answer("✅ Done")


@router.message(Command("cancel"))
async def cancel(message: Message):
    task_id = int(message.text.split()[1])
    await update_task_status(task_id, "cancelled")
    await message.answer("❌ Cancelled")


@router.message(Command("deadline"))
async def deadline(message: Message):
    parts = message.text.split(maxsplit=2)

    task_id = int(parts[1])
    new_deadline = parts[2]

    await update_deadline(task_id, new_deadline)
    await message.answer("⏰ updated")
