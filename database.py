import aiosqlite

DB_NAME = "tasks.db"


async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            text TEXT,
            executor TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'active',
            notified_24h INTEGER DEFAULT 0,
            notified_2h INTEGER DEFAULT 0
        )
        """)
        await db.commit()


async def add_task(chat_id, text, executor, deadline):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        INSERT INTO tasks (chat_id, text, executor, deadline)
        VALUES (?, ?, ?, ?)
        """, (chat_id, text, executor, deadline))
        await db.commit()


async def get_active_tasks():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
        SELECT * FROM tasks WHERE status='active'
        """)
        return await cursor.fetchall()


async def update_status(task_id, status):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        UPDATE tasks SET status=? WHERE id=?
        """, (status, task_id))
        await db.commit()


async def mark(task_id, field):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"""
        UPDATE tasks SET {field}=1 WHERE id=?
        """, (task_id,))
        await db.commit()
