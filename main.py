import asyncio
import re
import random
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

# UTC+3
def now():
    return datetime.utcnow() + timedelta(hours=3)


# ---------------- DB ----------------

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DROP TABLE IF EXISTS tasks")
        await db.execute("""
        CREATE TABLE tasks (
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
        cursor = await db.execute("SELECT * FROM tasks WHERE status='active'")
        return await cursor.fetchall()


async def get_task(task_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT * FROM tasks WHERE id=?", (task_id,))
        return await cursor.fetchone()


async def update_status(task_id, status):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
        await db.commit()


async def mark_notified(task_id, field):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"UPDATE tasks SET {field}=1 WHERE id=?", (task_id,))
        await db.commit()


# ---------------- SMART DATE ----------------

def parse_human_date(text):
    base = now()

    if "завтра" in text:
        return (base + timedelta(days=1)).strftime("%d.%m.%Y 10:00")

    if "послезавтра" in text:
        return (base + timedelta(days=2)).strftime("%d.%m.%Y 10:00")

    if "через" in text:
        days = re.findall(r"через (\d+) дня", text)
        if days:
            return (base + timedelta(days=int(days[0]))).strftime("%d.%m.%Y 10:00")

    weekdays = {
        "понедельник": 0,
        "вторник": 1,
        "среду": 2,
        "четверг": 3,
        "пятницу": 4,
        "субботу": 5,
        "воскресенье": 6
    }

    for word, num in weekdays.items():
        if word in text:
            delta = (num - base.weekday() + 7) % 7
            delta = delta if delta else 7
            return (base + timedelta(days=delta)).strftime("%d.%m.%Y 10:00")

    return None


def parse_task(text):
    executor = re.search(r"@\w+", text)
    date = re.search(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", text)

    executor = executor.group() if executor else "@unknown"
    deadline = date.group() if date else parse_human_date(text)

    clean = re.sub(r"@\w+", "", text)
    clean = re.sub(r"\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}", "", clean)

    return clean.strip(), executor, deadline


# ---------------- HANDLER ----------------

@dp.message()
async def handler(message: types.Message):
    text = message.text.lower()

    if not text:
        return

    # список задач
    if text.startswith("задачи"):
        tasks = await get_active_tasks()
        if not tasks:
            await message.answer("📭 Нет задач")
            return

        msg = "📌 Задачи:\n\n"
        for t in tasks:
            msg += f"#{t[0]} {t[2]} — {t[3]} — до {t[4]}\n"

        await message.answer(msg)
        return

    # сколько осталось
    if "сколько осталось" in text:
        task_id = int(re.findall(r"\d+", text)[0])
        task = await get_task(task_id)

        if not task:
            await message.answer("❌ Задача не найдена")
            return

        deadline = datetime.strptime(task[4], "%d.%m.%Y %H:%M")
        diff = deadline - now()

        hours = int(diff.total_seconds() // 3600)

        await message.answer(f"⏳ Осталось {hours} часов")
        return

    # done
    if text.startswith("/done"):
        task_id = int(text.split()[1])
        await update_status(task_id, "done")
        await message.answer("✅ Готово")
        return

    # cancel
    if text.startswith("/cancel"):
        task_id = int(text.split()[1])
        await update_status(task_id, "cancelled")
        await message.answer("❌ Отменено")
        return

    # создание задачи
    if any(x in text for x in ["завтра", "через", "понедельник"]) or re.search(r"\d{2}\.\d{2}\.\d{4}", text):
        task_text, executor, deadline = parse_task(text)

        if not deadline:
            await message.answer("❌ Не понял дату")
            return

        await add_task(message.chat.id, task_text, executor, deadline)

        await message.answer(f"✅ Задача создана\n{executor}\n{deadline}")


# ---------------- REMINDERS ----------------

async def check_tasks():
    tasks = await get_active_tasks()

    for t in tasks:
        task_id, chat_id, text, executor, deadline_str, status, n24, n2 = t

        deadline = datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")
        diff = deadline - now()

        if diff.total_seconds() <= 0:
            await update_status(task_id, "expired")
            await bot.send_message(chat_id, f"⚠️ Просрочено: {text}")
            continue

        if diff <= timedelta(hours=24) and n24 == 0:
            await bot.send_message(chat_id, f"⏰ 24ч: {text} {executor}")
            await mark_notified(task_id, "notified_24h")

        if diff <= timedelta(hours=2) and n2 == 0:
            await bot.send_message(chat_id, f"🔥 2ч: {text} {executor}")
            await mark_notified(task_id, "notified_2h")


# ---------------- MORNING MESSAGE ----------------

async def morning_message():
    users = ["Василиса", "Вася", "Даша", "Лизочек"]
    name = random.choice(users)

    # ⚠️ отправит в последний активный чат (упрощение)
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT chat_id FROM tasks ORDER BY id DESC LIMIT 1")
        row = await cursor.fetchone()

        if row:
            await bot.send_message(row[0], f"☀️ Всем привет! Какашка дня — {name}")


# ---------------- START ----------------

async def main():
    await init_db()

    scheduler.add_job(check_tasks, "interval", minutes=1)

    # 10:30 UTC+3 = 07:30 UTC
    scheduler.add_job(morning_message, "cron", hour=7, minute=30)

    scheduler.start()

    print("🚀 Bot started")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
