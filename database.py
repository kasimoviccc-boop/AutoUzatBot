import aiosqlite

DB_NAME = "autoxabar.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Foydalanuvchilar
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0,
                is_pro INTEGER DEFAULT 0,
                pro_expire_date TEXT,
                referred_by INTEGER
            )
        """)
        # Akkauntlar (Har bir foydalanuvchi bir nechta profil ulashi uchun)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                phone_number TEXT,
                session_string TEXT,
                message_text TEXT,
                interval_minutes INTEGER DEFAULT 10,
                is_active INTEGER DEFAULT 0
            )
        """)
        # Guruhlar
        await db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                chat_id TEXT
            )
        """)
        # Custom / Shaxsiy botlar
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_bots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER,
                bot_token TEXT
            )
        """)
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT balance, is_pro, pro_expire_date, referred_by FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def register_user(user_id: int, referrer_id: int = None):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                await db.execute("INSERT INTO users (user_id, referred_by) VALUES (?, ?)", (user_id, referrer_id))
                if referrer_id and referrer_id != user_id:
                    # Referal taklif qilganga 500 so'm mukofot berish
                    await db.execute("UPDATE users SET balance = balance + 500 WHERE user_id = ?", (referrer_id,))
                await db.commit()

async def add_account(user_id: int, phone: str, session_str: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO accounts (user_id, phone_number, session_string) VALUES (?, ?, ?)", (user_id, phone, session_str))
        await db.commit()

async def get_accounts(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, phone_number, is_active, interval_minutes, message_text FROM accounts WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchall()

async def update_account_status(acc_id: int, status: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE accounts SET is_active = ? WHERE id = ?", (status, acc_id))
        await db.commit()

async def update_account_message(user_id: int, message_text: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE accounts SET message_text = ? WHERE user_id = ?", (message_text, user_id))
        await db.commit()

async def update_account_interval(user_id: int, minutes: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE accounts SET interval_minutes = ? WHERE user_id = ?", (minutes, user_id))
        await db.commit()

async def delete_account(acc_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM accounts WHERE id = ?", (acc_id,))
        await db.commit()

async def add_
