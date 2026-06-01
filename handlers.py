import re
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message

from database import add_task

router = Router()


# =========================
# DEBUG (важно!)
# =========================

@router.message()
async def debug_all(message: Message):
    print(f"[DEBUG] chat={message.chat.id} text={message.text}")


# =========================
# PARSER
# =========================

def parse_task(text: str):
    """
    Формат:
    задача: текст @user 12.12.2026 18:00
    """

    executor = re.search(r"@\w+", text)
    date = re.search(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", text)

    executor = executor.group() if executor else "@unknown"
    deadline = date.group() if date else None

    clean = re.sub(r"@\w+", "", text)
    clean = re.sub(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", "", clean)

    return clean.strip(), executor, deadline


# =========================
# CREATE TASK
# =========================

@router.message(F.text)
async def create_task(message: Message):

    text = message.text or ""

    # 🔥 строгое условие
    if not text.lower().startswith("задача:"):
        return

    text = text.replace("задача:", "").strip()

    task_text, executor, deadline = parse_task(text)

    if not deadline:
        await message.answer(
            "❌ Не найден дедлайн\n"
            "Формат: задача: текст @user 12.12.2026 18:00"
        )
        return

    await add_task(
        message.chat.id,
        task_text,
        executor,
        deadline
    )

    await message.answer(
        "✅ Задача создана\n\n"
        f"📌 {task_text}\n"
        f"👤 {executor}\n"
        f"⏰ {deadline}"
    )


# =========================
# PING TEST
# =========================

@router.message(F.text == "/ping")
async def ping(message: Message):
    await message.answer("pong 🟢 бот жив")
