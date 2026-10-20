import asyncio
from pyrogram import Client
from database import get_groups, get_active_users

# --- BU YERGA O'ZINGizning my.telegram.org dan olgan kalitlaringizni yozasiz ---
API_ID = 39992061  # Masalan: 2847592 (faqat raqam)
API_HASH = "22cb23045de6fe3c351d10305b7438f3"  # Masalan: "a1b2c3d4e5f6g7h8..." (qo'shtirnoq ichida)

temp_clients = {}

async def send_code_to_phone(user_id: int, phone_number: str):
    try:
        client = Client(f"session_{user_id}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
        await client.connect()
        sent_code = await client.send_code(phone_number)
        temp_clients[user_id] = {
            "client": client,
            "phone": phone_number,
            "phone_code_hash": sent_code.phone_code_hash
        }
        return True, "Kod yuborildi"
    except Exception as e:
        return False, str(e)

async def sign_in_with_code(user_id: int, code: str, password: str = None):
    if user_id not in temp_clients:
        return False, "Avval raqam yuboring!"
    
    data = temp_clients[user_id]
    client = data["client"]
    phone = data["phone"]
    phone_code_hash = data["phone_code_hash"]
    
    try:
        if code:
            await client.sign_in(phone_number=phone, phone_code_hash=phone_code_hash, phone_code=code)
        elif password:
            await client.check_password(password)
    except Exception as e:
        if "SessionPasswordNeeded" in str(e):
            return False, "SessionPasswordNeeded"
        return False, str(e)
            
    session_string = await client.export_session_string()
    await client.disconnect()
    if user_id in temp_clients:
        del temp_clients[user_id]
    return True, session_string

async def send_user_messages(user_id: int, session_str: str, message: str):
    if not session_str or not message:
        return
    groups = await get_groups(user_id)
    if not groups:
        return

    try:
        async with Client(f"worker_{user_id}", api_id=API_ID, api_hash=API_HASH, session_string=session_str) as app:
            for chat_id in groups:
                try:
                    await app.send_message(chat_id, message)
                    await asyncio.sleep(3)
                except Exception as e:
                    print(f"Xatolik {chat_id}: {e}")
    except Exception as e:
        print(f"UserBot sessiya xatosi {user_id}: {e}")

async def run_auto_sender():
    users = await get_active_users()
    for user in users:
        user_id, session_string, message_text, _ = user
        if session_string and message_text:
            await send_user_messages(user_id, session_string, message_text)
            
