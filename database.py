import aiosqlite

DB_NAME = "tasks.db"


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
            notified_2h INTEGER DEFAULT 0,
            last_overdue_notice TEXT
        )
        """)
        await db.commit()


async def add_task(chat_id, task_text, executor, deadline):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO tasks (chat_id, task_text, executor, deadline) VALUES (?, ?, ?, ?)",
            (chat_id, task_text, executor, deadline)
        )
        await db.commit()


async def get_task(task_id, chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT * FROM tasks WHERE id=? AND chat_id=?",
            (task_id, chat_id)
        )
        return await cur.fetchone()


async def get_active_tasks(chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT * FROM tasks WHERE chat_id=? AND status IN ('active','expired')",
            (chat_id,)
        )
        return await cur.fetchall()


async def get_last_tasks(chat_id, limit=10):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT * FROM tasks WHERE chat_id=? ORDER BY id DESC LIMIT ?",
            (chat_id, limit)
        )
        return await cur.fetchall()


async def update_task_status(task_id, status):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE tasks SET status=? WHERE id=?",
            (status, task_id)
        )
        await db.commit()


async def update_deadline(task_id, deadline):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE tasks SET deadline=?, status='active' WHERE id=?",
            (deadline, task_id)
        )
        await db.commit()


async def get_stats(chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT executor, status, COUNT(*) FROM tasks WHERE chat_id=? GROUP BY executor, status",
            (chat_id,)
        )
        return await cur.fetchall()


async def get_rating(chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT executor, COUNT(*) FROM tasks WHERE chat_id=? AND status='done' GROUP BY executor",
            (chat_id,)
        )
        return await cur.fetchall()


async def get_streak(chat_id, executor):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute(
            "SELECT streak, max_streak FROM streaks WHERE chat_id=? AND executor=?",
            (chat_id, executor)
        )
        return await cur.fetchone()
