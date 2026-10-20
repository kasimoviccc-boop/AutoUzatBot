import aiosqlite

DB_NAME = "autoxabar.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                session_string TEXT,
                message_text TEXT,
                interval_minutes INTEGER DEFAULT 10,
                is_active INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id TEXT
            )
        """)
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT session_string, message_text, interval_minutes, is_active FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def set_session(user_id: int, session_string: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO users (user_id, session_string) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET session_string = EXCLUDED.session_string
        """, (user_id, session_string))
        await db.commit()

async def set_message(user_id: int, text: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO users (user_id, message_text) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET message_text = EXCLUDED.message_text
        """, (user_id, text))
        await db.commit()

async def set_interval(user_id: int, minutes: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            INSERT INTO users (user_id, interval_minutes) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET interval_minutes = EXCLUDED.interval_minutes
        """, (user_id, minutes))
        await db.commit()

async def set_status(user_id: int, status: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET is_active = ? WHERE user_id = ?", (status, user_id))
        await db.commit()

async def add_group(user_id: int, chat_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO groups (user_id, chat_id) VALUES (?, ?)", (user_id, chat_id))
        await db.commit()

async def get_groups(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT chat_id FROM groups WHERE user_id = ?", (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_active_users():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, session_string, message_text, interval_minutes FROM users WHERE is_active = 1") as cursor:
            return await cursor.fetchall()
          
