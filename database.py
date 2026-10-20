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

async def add_group(user_id: int, chat_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO groups (user_id, chat_id) VALUES (?, ?)", (user_id, chat_id))
        await db.commit()

async def delete_group(group_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM groups WHERE id = ?", (group_id,))
        await db.commit()

async def get_groups(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, chat_id FROM groups WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchall()

async def save_custom_bot(owner_id: int, token: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT INTO custom_bots (owner_id, bot_token) VALUES (?, ?)", (owner_id, token))
        await db.commit()

async def get_active_accounts():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT user_id, session_string, message_text, interval_minutes FROM accounts WHERE is_active = 1") as cursor:
            return await cursor.fetchall()

async def get_stats():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c1:
            total_users = (await c1.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM accounts WHERE is_active = 1") as c2:
            active_accs = (await c2.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM groups") as c3:
            total_groups = (await c3.fetchone())[0]
        return total_users, active_accs, total_groups

async def get_referral_count(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by = ?", (user_id,)) as cursor:
            return (await cursor.fetchone())[0]

async def activate_pro(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET is_pro = 1 WHERE user_id = ?", (user_id,))
        await db.commit()
        
