import re
from aiogram import Router, F
from aiogram.types import Message

from database import add_task

router = Router()


@router.message()
async def debug_all(message: Message):
    print(f"[MSG] {message.text}")


def parse_task(text: str):
    executor = re.search(r"@\w+", text)
    date = re.search(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", text)

    executor = executor.group() if executor else "@unknown"
    deadline = date.group() if date else None

    clean = re.sub(r"@\w+", "", text)
    clean = re.sub(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", "", clean)

    return clean.strip(), executor, deadline


@router.message(F.text)
async def create_task(message: Message):

    text = message.text or ""

    if not text.lower().startswith("задача:"):
        return

    text = text.replace("задача:", "").strip()

    task_text, executor, deadline = parse_task(text)

    if not deadline:
        await message.answer("❌ нет дедлайна")
        return

    await add_task(message.chat.id, task_text, executor, deadline)

    await message.answer("✅ задача создана")


@router.message(F.text == "/ping")
async def ping(message: Message):
    await message.answer("pong")
