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
            status TEXT DEFAULT 'active',
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


async def get_active_tasks():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
        SELECT * FROM tasks WHERE status = 'active'
        """)
        return await cursor.fetchall()


async def update_status(task_id, status):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        UPDATE tasks SET status = ? WHERE id = ?
        """, (status, task_id))
        await db.commit()


async def get_all_tasks():
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
    executor_match = re.search(r"@\w+", text)
    date_match = re.search(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", text)

    executor = executor_match.group() if executor_match else "@unknown"
    deadline = date_match.group() if date_match else None

    clean = re.sub(r"@\w+", "", text)
    clean = re.sub(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", "", clean)

    return clean.strip(), executor, deadline


# ---------------- HANDLER ----------------

@dp.message()
async def handler(message: types.Message):
    text = message.text
    if not text:
        return

    # --- список задач ---
    if text.lower().startswith("задачи"):
        tasks = await get_active_tasks()

        if not tasks:
            await message.answer("📭 Нет активных задач")
            return

        msg = "📌 Активные задачи:\n\n"
        for t in tasks:
            msg += f"#{t[0]} {t[2]} — {t[3]} — до {t[4]}\n"

        await message.answer(msg)
        return

    # --- выполнить ---
    if text.startswith("/done"):
        task_id = int(text.split()[1])
        await update_status(task_id, "done")
        await message.answer("✅ Задача выполнена")
        return

    # --- отменить ---
    if text.startswith("/cancel"):
        task_id = int(text.split()[1])
        await update_status(task_id, "cancelled")
        await message.answer("❌ Задача отменена")
        return

    # --- создание задачи ---
    if re.search(r"\d{2}\.\d{2}\.\d{4}", text):
        task_text, executor, deadline = parse_task(text)

        if not deadline:
            await message.answer("❌ Неверный формат даты")
            return

        await add_task(message.chat.id, task_text, executor, deadline)

        await message.answer(
            f"✅ Задача создана\n"
            f"{executor}\n"
            f"Дедлайн: {deadline}"
        )


# ---------------- REMINDERS ----------------

async def check_tasks():
    tasks = await get_all_tasks()
    now = datetime.now()

    for t in tasks:
        task_id = t[0]
        chat_id = t[1]
        task_text = t[2]
        executor = t[3]
        deadline_str = t[4]
        status = t[5]

        if status != "active":
            continue

        try:
            deadline = datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")
        except:
            continue

        diff = deadline - now

        # --- EXPIRED ---
        if now > deadline:
            await update_status(task_id, "expired")
            await bot.send_message(chat_id, f"⚠️ Задача просрочена:\n{task_text}")
            continue

        # --- 24h ---
        if diff <= timedelta(hours=24) and t[6] == 0:
            await bot.send_message(chat_id,
                f"⏰ 24 часа до дедлайна\n{task_text}\n{executor}"
            )
            await mark_notified(task_id, "notified_24h")

        # --- 2h ---
        if diff <= timedelta(hours=2) and t[7] == 0:
            await bot.send_message(chat_id,
                f"🔥 2 часа до дедлайна\n{task_text}\n{executor}"
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
