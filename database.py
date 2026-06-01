import aiosqlite

DB_NAME = "tasks.db"


# =========================
# INIT DB
# =========================

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:

        # TASKS
        await db.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            task_text TEXT NOT NULL,
            executor TEXT NOT NULL,
            deadline TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            notified_24h INTEGER DEFAULT 0,
            notified_2h INTEGER DEFAULT 0,
            last_overdue_notice TEXT
        )
        """)

        # PARTICIPANTS
        await db.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            username TEXT NOT NULL
        )
        """)

        # PENALTIES (штрафы за просрочку)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS penalties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            executor TEXT NOT NULL,
            points INTEGER DEFAULT 0
        )
        """)

        # STREAKS (серии выполнения)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS streaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            executor TEXT NOT NULL,
            streak INTEGER DEFAULT 0,
            max_streak INTEGER DEFAULT 0
        )
        """)

        await db.commit()


# =========================
# PARTICIPANTS
# =========================

async def add_participant(chat_id, username):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
        SELECT id FROM participants
        WHERE chat_id = ? AND username = ?
        """, (chat_id, username))

        if not await cursor.fetchone():
            await db.execute("""
            INSERT INTO participants (chat_id, username)
            VALUES (?, ?)
            """, (chat_id, username))

        await db.commit()


async def get_participants(chat_id):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
        SELECT username
        FROM participants
        WHERE chat_id = ?
        ORDER BY username
        """, (chat_id,))

        return await cursor.fetchall()


# =========================
# TASKS
# =========================

async def add_task(chat_id, task_text, executor, deadline):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
        INSERT INTO tasks (chat_id, task_text, executor, deadline)
        VALUES (?, ?, ?, ?)
        """, (chat_id, task_text, executor, deadline))

        await db.commit()


async def get_task(task_id, chat_id):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
        SELECT *
        FROM tasks
        WHERE id = ? AND chat_id = ?
        """, (task_id, chat_id))

        return await cursor.fetchone()


async def get_active_tasks(chat_id):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
        SELECT *
        FROM tasks
        WHERE chat_id = ?
        AND status IN ('active','expired')
        ORDER BY id DESC
        """, (chat_id,))

        return await cursor.fetchall()


async def get_all_tasks():

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
        SELECT *
        FROM tasks
        WHERE status IN ('active','expired')
        """)

        return await cursor.fetchall()


async def get_last_tasks(chat_id, limit=10):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
        SELECT *
        FROM tasks
        WHERE chat_id = ?
        ORDER BY id DESC
        LIMIT ?
        """, (chat_id, limit))

        return await cursor.fetchall()


async def get_tasks_by_executor(chat_id, executor):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
        SELECT *
        FROM tasks
        WHERE chat_id = ?
        AND executor = ?
        AND status IN ('active','expired')
        ORDER BY id DESC
        """, (chat_id, executor))

        return await cursor.fetchall()


# =========================
# UPDATE TASKS
# =========================

async def update_task_status(task_id, status):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
        UPDATE tasks
        SET status = ?
        WHERE id = ?
        """, (status, task_id))

        await db.commit()


async def update_deadline(task_id, deadline):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
        UPDATE tasks
        SET deadline = ?,
            status = 'active',
            notified_24h = 0,
            notified_2h = 0
        WHERE id = ?
        """, (deadline, task_id))

        await db.commit()


async def mark_notification(task_id, field):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            f"UPDATE tasks SET {field} = 1 WHERE id = ?",
            (task_id,)
        )

        await db.commit()


async def update_last_overdue_notice(task_id, value):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
        UPDATE tasks
        SET last_overdue_notice = ?
        WHERE id = ?
        """, (value, task_id))

        await db.commit()


# =========================
# PENALTIES
# =========================

async def add_penalty(chat_id, executor, value):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
        SELECT points
        FROM penalties
        WHERE chat_id = ? AND executor = ?
        """, (chat_id, executor))

        row = await cursor.fetchone()

        if row:
            await db.execute("""
            UPDATE penalties
            SET points = points + ?
            WHERE chat_id = ? AND executor = ?
            """, (value, chat_id, executor))
        else:
            await db.execute("""
            INSERT INTO penalties (chat_id, executor, points)
            VALUES (?, ?, ?)
            """, (chat_id, executor, value))

        await db.commit()


async def get_penalties(chat_id):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
        SELECT executor, points
        FROM penalties
        WHERE chat_id = ?
        ORDER BY points ASC
        """, (chat_id,))

        return await cursor.fetchall()


# =========================
# STREAKS
# =========================

async def update_streak(chat_id, executor, delta, reset=False):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
        SELECT streak, max_streak
        FROM streaks
        WHERE chat_id = ? AND executor = ?
        """, (chat_id, executor))

        row = await cursor.fetchone()

        if not row:
            streak = 0
            max_streak = 0
        else:
            streak, max_streak = row

        if reset:
            streak = 0
        else:
            streak += delta
            max_streak = max(max_streak, streak)

        await db.execute("""
        INSERT INTO streaks (chat_id, executor, streak, max_streak)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(chat_id, executor)
        DO UPDATE SET streak = ?, max_streak = ?
        """, (chat_id, executor, streak, max_streak, streak, max_streak))

        await db.commit()


async def get_streak(chat_id, executor):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
        SELECT streak, max_streak
        FROM streaks
        WHERE chat_id = ? AND executor = ?
        """, (chat_id, executor))

        return await cursor.fetchone()


# =========================
# STATS / RATING
# =========================

async def get_stats(chat_id):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
        SELECT executor, status, COUNT(*)
        FROM tasks
        WHERE chat_id = ?
        GROUP BY executor, status
        """, (chat_id,))

        return await cursor.fetchall()


async def get_rating(chat_id):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
        SELECT executor, SUM(points) as score
        FROM (
            SELECT executor, 1 as points
            FROM tasks
            WHERE chat_id = ? AND status = 'done'

            UNION ALL

            SELECT executor, -1 as points
            FROM penalties
            WHERE chat_id = ?
        )
        GROUP BY executor
        ORDER BY score DESC
        """, (chat_id, chat_id))

        return await cursor.fetchall()
