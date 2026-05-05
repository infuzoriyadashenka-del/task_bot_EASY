import asyncio
import re
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

DB_NAME = "tasks.db"


# ---------------- DB ----------------

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            task_text TEXT,
            executor TEXT,
            deadline TEXT,
            notified_24h INTEGER DEFAULT 0,
            notified_2h INTEGER DEFAULT 0
        )
        """)
        await db.commit()


async def add_task(chat_id, task_text, executor, deadline):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        INSERT INTO tasks (chat_id, task_text, executor, deadline)
        VALUES (?, ?, ?, ?)
        """, (chat_id, task_text, executor, deadline))
        await db.commit()


async def get_tasks():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT * FROM tasks")
        return await cursor.fetchall()


async def get_pending_tasks():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
        SELECT * FROM tasks
        """)
        return await cursor.fetchall()


async def mark_notified(task_id, field):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"""
        UPDATE tasks SET {field} = 1 WHERE id = ?
        """, (task_id,))
        await db.commit()


# ---------------- PARSER ----------------

def parse_task(text):
    """
    Формат:
    @user сделать отчёт 20.05.2026 14:00
    """

    executor_match = re.search(r"@\w+", text)
    date_match = re.search(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", text)

    executor = executor_match.group() if executor_match else "@unknown"
    deadline = date_match.group() if date_match else None

    # убираем лишнее
    clean_text = text
    clean_text = re.sub(r"@\w+", "", clean_text)
    clean_text = re.sub(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", "", clean_text)

    task_text = clean_text.strip()

    return task_text, executor, deadline


# ---------------- HANDLER ----------------

@dp.message()
async def handle_message(message: types.Message):
    text = message.text

    if not text:
        return

    # --- список задач ---
    if "задачи" in text.lower():
        tasks = await get_tasks()

        if not tasks:
            await message.answer("📭 Активных задач нет")
            return

        result = "📌 Активные задачи:\n\n"
        for t in tasks:
            result += f"#{t[0]} {t[2]} — {t[3]} — до {t[4]}\n"

        await message.answer(result)
        return

    # --- СОЗДАНИЕ ЗАДАЧИ (ГЛАВНОЕ ИЗМЕНЕНИЕ) ---
    if re.search(r"\d{2}\.\d{2}\.\d{4}", text):
        task_text, executor, deadline = parse_task(text)

        if not deadline:
            await message.answer("❌ Не найден дедлайн (формат: 20.05.2026 14:00)")
            return

        await add_task(
            message.chat.id,
            task_text,
            executor,
            deadline
        )

        await message.answer(
            f"✅ Задача принята\n"
            f"Исполнитель: {executor}\n"
            f"Дедлайн: {deadline}"
        )


# ---------------- REMINDERS ----------------

async def check_tasks():
    tasks = await get_pending_tasks()
    now = datetime.now()

    for t in tasks:
        task_id = t[0]
        chat_id = t[1]
        task_text = t[2]
        executor = t[3]
        deadline_str = t[4]

        try:
            deadline = datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")
        except:
            continue

        diff = deadline - now

        # 24 часа
        if diff <= timedelta(hours=24) and t[5] == 0:
            await bot.send_message(
                chat_id,
                f"⏰ Напоминание (24 часа)\n"
                f"Задача: {task_text}\n"
                f"{executor}"
            )
            await mark_notified(task_id, "notified_24h")

        # 2 часа
        if diff <= timedelta(hours=2) and t[6] == 0:
            await bot.send_message(
                chat_id,
                f"🔥 Срочно!\n"
                f"Задача: {task_text}\n"
                f"Сдавать через 2 часа\n"
                f"{executor}"
            )
            await mark_notified(task_id, "notified_2h")


# ---------------- START ----------------

async def main():
    await init_db()

    scheduler.add_job(check_tasks, "interval", minutes=1)
    scheduler.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
