import aiosqlite

DB_NAME = "autoxabar.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                phone_number TEXT,
                session_string TEXT,
                message_text TEXT,
                interval_minutes INTEGER DEFAULT 10,
                is_active INTEGER DEFAULT 0,
                is_pro INTEGER DEFAULT 0,
                balance INTEGER DEFAULT 0,
                referred_by INTEGER
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
        async with db.execute("SELECT session_string, message_text, interval_minutes, is_active, phone_number, is_pro, balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def register_user(user_id: int, referrer_id: int = None):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                await db.execute("INSERT INTO users (user_id, referred_by) VALUES (?, ?)", (user_id, referrer_id))
                await db.commit()

async def set_session(user_id: int, session_string: str, phone: str = ""):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            UPDATE users SET session_string = ?, phone_number = ? WHERE user_id = ?
        """, (session_string, phone, user_id))
        await db.commit()

async def set_message(user_id: int, text: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET message_text = ? WHERE user_id = ?", (text, user_id))
        await db.commit()

async def set_interval(user_id: int, minutes: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET interval_minutes = ? WHERE user_id = ?", (minutes, user_id))
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

async def get_stats():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c1:
            total_users = (await c1.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE is_active = 1") as c2:
            active_users = (await c2.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM groups") as c3:
            total_groups = (await c3.fetchone())[0]
        return total_users, active_users, total_groups

async def get_referral_count(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,)) as cursor:
            return (await cursor.fetchone())[0]
            
