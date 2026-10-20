import asyncio
from pyrogram import Client
from database import get_groups, get_active_users

# Telegram'dan olingan universal API ma'lumotlari (bularni o'zgartirmasdan qoldirishingiz mumkin)
API_ID = 6 // masalan o'zingizniki yoki my.telegram.org dan olingan bitta umumiy api_id
API_HASH = "eb06d4abfb49dc3eeb1aeb98ae0f581e"

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
        await client.sign_in(phone_number=phone, phone_code_hash=phone_code_hash, phone_code=code)
    except Exception as e:
        if "SessionPasswordNeeded" in str(e) and password:
            try:
                await client.check_password(password)
            except Exception as ex:
                return False, f"2-bosqichli parol xato: {ex}"
        else:
            return False, f"Xatolik: {e}"
            
    session_string = await client.export_session_string()
    await client.disconnect()
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
