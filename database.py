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
            notified_2h INTEGER DEFAULT 0
        )
        """)

        await db.commit()


async def add_task(chat_id, task_text, executor, deadline):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        INSERT INTO tasks(chat_id, task_text, executor, deadline)
        VALUES (?, ?, ?, ?)
        """, (chat_id, task_text, executor, deadline))
        await db.commit()


async def get_all_tasks():
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("""
        SELECT id, chat_id, task_text, executor, deadline,
               status, notified_24h, notified_2h
        FROM tasks
        WHERE status IN ('active','expired')
        """)
        return await cur.fetchall()


async def get_task(task_id, chat_id):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("""
        SELECT * FROM tasks WHERE id=? AND chat_id=?
        """, (task_id, chat_id))
        return await cur.fetchone()


async def get_last_tasks(chat_id, limit=1):
    async with aiosqlite.connect(DB_NAME) as db:
        cur = await db.execute("""
        SELECT * FROM tasks
        WHERE chat_id=?
        ORDER BY id DESC
        LIMIT ?
        """, (chat_id, limit))
        return await cur.fetchall()


async def update_task_status(task_id, status):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        UPDATE tasks SET status=? WHERE id=?
        """, (status, task_id))
        await db.commit()


async def update_deadline(task_id, deadline):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        UPDATE tasks SET deadline=?, status='active',
        notified_24h=0, notified_2h=0
        WHERE id=?
        """, (deadline, task_id))
        await db.commit()


async def mark_notification(task_id, field):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(f"""
        UPDATE tasks SET {field}=1 WHERE id=?
        """, (task_id,))
        await db.commit()
