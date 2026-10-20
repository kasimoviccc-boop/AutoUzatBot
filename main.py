import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web

import database as db
from userbot import send_code_to_phone, sign_in_with_code, run_auto_sender

BOT_TOKEN = os.getenv("BOT_TOKEN", "SIZNING_BOT_TOKENINGIZ")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
scheduler = AsyncIOScheduler()

# Render bepul server talabi uchun veb-server
async def handle(request):
    return web.Response(text="Avto Xabar Bot ishlamoqda!")

app = web.Application()
app.add_routes([web.get('/', handle)])

async def start_web_server():
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

class AuthState(StatesGroup):
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_password = State()
    waiting_for_message = State()
    waiting_for_group = State()
    waiting_for_custom_interval = State()

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Profillar"), KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="💬 Xabar"), KeyboardButton(text="📁 Guruhlar")],
            [KeyboardButton(text="▶️ Ishga tushirish"), KeyboardButton(text="⏱ Interval")],
            [KeyboardButton(text="⭐️ Pro"), KeyboardButton(text="🥷 Shaxsiy bot")],
            [KeyboardButton(text="👥 Referal dastur"), KeyboardButton(text="👤 Profil")],
            [KeyboardButton(text="⚙️ Sozlamalar")]
        ],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def start_cmd(message: types.Message, command: CommandObject):
    await db.init_db()
    args = command.args
    referrer_id = int(args) if args and args.isdigit() and int(args) != message.from_user.id else None
    await db.register_user(message.from_user.id, referrer_id)
    
    await message.answer(
        "🤖 **Avto Xabar botiga xush kelibsiz!**\n\nQuyidagi menyu orqali guruhlarga avtomatik xabarlar tarqatishni boshlang:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# --- ⏱ INTERVAL ---
@dp.message(F.text == "⏱ Interval")
async def interval_menu(message: types.Message):
    user = await db.get_user(message.from_user.id)
    current_int = user[2] if user and user[2] else 10

    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="2 daqiqa", callback_data="set_int_2"), InlineKeyboardButton(text="5 daqiqa", callback_data="set_int_5")],
        [InlineKeyboardButton(text="7 daqiqa", callback_data="set_int_7"), InlineKeyboardButton(text="10 daqiqa", callback_data="set_int_10")],
        [InlineKeyboardButton(text="15 daqiqa", callback_data="set_int_15"), InlineKeyboardButton(text="20 daqiqa", callback_data="set_int_20")],
        [InlineKeyboardButton(text="25 daqiqa", callback_data="set_int_25"), InlineKeyboardButton(text="30 daqiqa", callback_data="set_int_30")],
        [InlineKeyboardButton(text="1 soat", callback_data="set_int_60"), InlineKeyboardButton(text="6 soat", callback_data="set_int_360")],
        [InlineKeyboardButton(text="⌨️ Qo'lda kiritish", callback_data="set_int_custom")]
    ])
    await message.answer(
        f"⏱ **Interval sozlamasi**\n\n📌 Hozirgi interval: **{current_int} daqiqa**\n\nQuyidan tanlang:",
        reply_markup=builder,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("set_int_"))
async def process_interval(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[2]
    if action == "custom":
        await callback.message.answer("Daqiqalar sonini son ko'rinishida yuboring (masalan: 45):")
        await state.set_state(AuthState.waiting_for_custom_interval)
    else:
        minutes = int(action)
        await db.set_interval(callback.from_user.id, minutes)
        await callback.answer(f"Interval {minutes} daqiqaga o'zgartirildi!", show_alert=True)
        await interval_menu(callback.message)

@dp.message(AuthState.waiting_for_custom_interval)
async def custom_interval_set(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        minutes = int(message.text)
        await db.set_interval(message.from_user.id, minutes)
        await message.answer(f"✅ Interval {minutes} daqiqaga o'rnatildi!", reply_markup=main_menu())
        await state.clear()
    else:
        await message.answer("❌ Faqat raqam kiriting:")

# --- 👥 PROFILLAR (SMS KOD BILAN ULANISH) ---
@dp.message(F.text == "👥 Profillar")
async def profiles_cmd(message: types.Message, state: FSMContext):
    builder = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "📱 Telegram akkauntingizni ulash uchun pastdagi tugmani bosing yoki raqamingizni yuboring (masalan: `+998901234567`):",
        reply_markup=builder,
        parse_mode="Markdown"
    )
    await state.set_state(AuthState.waiting_for_phone)

@dp.message(AuthState.waiting_for_phone, F.contact)
@dp.message(AuthState.waiting_for_phone, F.text)
async def get_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    if not phone.startswith("+"):
        phone = "+" + phone

    success, msg = await send_code_to_phone(message.from_user.id, phone)
    if success:
        await message.answer("📩 Telegram rasmiy ilovangizga SMS kod keldi. Kodni kiriting (masalan: `12345`):", reply_markup=types.ReplyKeyboardRemove())
        await state.update_data(phone=phone)
        await state.set_state(AuthState.waiting_for_code)
    else:
        await message.answer(f"❌ Xatolik: {msg}\nQaytadan urinib ko'ring:")

@dp.message(AuthState.waiting_for_code)
async def get_code(message: types.Message, state: FSMContext):
    code = message.text.strip()
    user_id = message.from_user.id
    
    success, result = await sign_in_with_code(user_id, code)
    if success:
        session_string = result
        data = await state.get_data()
        await db.set_session(user_id, session_string, data.get("phone", ""))
        await message.answer("✅ Akkaunt muvaffaqiyatli bog'landi va saqlandi!", reply_markup=main_menu())
        await state.clear()
    else:
        if "SessionPasswordNeeded" in result:
            await message.answer("🔐 Ikki bosqichli parol yoqilgan ekan. Parolingizni kiriting:")
            await state.set_state(AuthState.waiting_for_password)
        else:
            await message.answer(f"❌ Kod xato: {result}\nQaytadan kiriting:")

@dp.message(AuthState.waiting_for_password)
async def get_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    user_id = message.from_user.id
    
    success, result = await sign_in_with_code(user_id, "", password)
    if success:
        session_string = result
        data = await state.get_data()
        await db.set_session(user_id, session_string, data.get("phone", ""))
        await message.answer("✅ Parol tasdiqlandi, akkaunt ulandi!", reply_markup=main_menu())
        await state.clear()
    else:
        await message.answer(f"❌ Parol xato: {result}\nQaytadan kiriting:")

# --- 💬 XABAR ---
@dp.message(F.text == "💬 Xabar")
async def message_cmd(message: types.Message, state: FSMContext):
    await message.answer("Guruhlarga tarqatiladigan xabar matnini kiriting:")
    await state.set_state(AuthState.waiting_for_message)

@dp.message(AuthState.waiting_for_message)
async def save_message(message: types.Message, state: FSMContext):
    await db.set_message(message.from_user.id, message.text)
    await message.answer("✅ Xabar matni saqlandi!", reply_markup=main_menu())
    await state.clear()

# --- 📁 GURUHLAR ---
@dp.message(F.text == "📁 Guruhlar")
async def groups_cmd(message: types.Message, state: FSMContext):
    groups = await db.get_groups(message.from_user.id)
    groups_list = "\n".join([f"• {g}" for g in groups]) if groups else "Hozircha guruhlar qo'shilmagan."
    
    await message.answer(
        f"📁 **Sizning guruhlaringiz:**\n{groups_list}\n\nYangi guruh ID yoki username'ini kiriting (masalan: `@guruh_nomi`):",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    await state.set_state(AuthState.waiting_for_group)

@dp.message(AuthState.waiting_for_group)
async def save_group(message: types.Message, state: FSMContext):
    await db.add_group(message.from_user.id, message.text)
    await message.answer("✅ Guruh muvaffaqiyatli qo'shildi!", reply_markup=main_menu())
    await state.clear()

# --- ▶️ ISHGA TUSHIRISH ---
@dp.message(F.text == "▶️ Ishga tushirish")
async def start_auto(message: types.Message):
    await db.set_status(message.from_user.id, 1)
    await message.answer("🚀 Avto-xabar yuborish jarayoni muvaffaqiyatli ishga tushirildi! Belgilangan intervalda xabarlar yuboriladi.")

# --- 📊 STATISTIKA ---
@dp.message(F.text == "📊 Statistika")
async def stats_cmd(message: types.Message):
    total, active, groups = await db.get_stats()
    await message.answer(
        f"📊 **Bot Statistikasi:**\n\n"
        f"👥 Jami foydalanuvchilar: {total}\n"
        f"🚀 Faol avto-xabarlar: {active}\n"
        f"📁 Ulangan guruhlar: {groups}",
        parse_mode="Markdown"
    )

# --- ⭐️ PRO ---
@dp.message(F.text == "⭐️ Pro")
async def pro_cmd(message: types.Message):
    await message.answer(
        "⭐️ **Pro Statusi**\n\n"
        "Pro statusini faollashtirish orqali cheksiz guruhlarga xabar yuborish va tezkor interval imkoniyatiga ega bo'lasiz.\n\n"
        "💳 Narxi: 10,000 so'm / oy\n"
        "Bog'lanish uchun: @Admin",
        parse_mode="Markdown"
    )

# --- 🥷 SHAXSIY BOT ---
@dp.message(F.text == "🥷 Shaxsiy bot")
async def personal_bot_cmd(message: types.Message):
    await message.answer(
        "🥷 **Shaxsiy bot yaratish**\n\n"
        "O'zingizning shaxsiy avto-xabar botingizni ochishni xohlaysizmi? @BotFather orqali bot ochib, uning TOKENini bizga yuboring va o'z loyihangiz egasiga aylaning!",
        parse_mode="Markdown"
    )

# --- 👥 REFERAL DASTUR ---
@dp.message(F.text == "👥 Referal dastur")
async def referral_cmd(message: types.Message):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    ref_count = await db.get_referral_count(message.from_user.id)
    
    await message.answer(
        f"👥 **Referal dastur**\n\n"
        f"Do'stlaringizni taklif qiling va mukofotlarga ega bo'ling!\n\n"
        f"🔗 Sizning referal havolangiz:\n`{ref_link}`\n\n"
        f"📊 Taklif qilgan do'stlaringiz soni: **{ref_count} ta**",
        parse_mode="Markdown"
    )

# --- 👤 PROFIL ---
@dp.message(F.text == "👤 Profil")
async def profile_cmd(message: types.Message):
    user = await db.get_user(message.from_user.id)
    if user:
        _, _, interval, active, phone, is_pro, balance = user
        status = "Faol 🟢" if active == 1 else "To'xtatilgan 🔴"
        phone_txt = phone if phone else "Bog'lanmagan ❌"
        daraja = "Pro ⭐️" if is_pro == 1 else "Oddiy 👤"
        
        await message.answer(
            f"👤 **Sizning profilingiz:**\n\n"
            f"📞 Telefon: `{phone_txt}`\n"
            f"⚡️ Holati: {status}\n"
            f"⏱ Interval: {interval} daqiqa\n"
            f"⭐️ Daraja: {daraja}\n"
            f"💰 Balans: {balance} so'm",
            parse_mode="Markdown"
        )
    else:
        await message.answer("Profil ma'lumotlari topilmadi. /start buyrug'ini bosing.")

# --- ⚙️ SOZLAMALAR ---
@dp.message(F.text == "⚙️ Sozlamalar")
async def settings_cmd(message: types.Message):
    await message.answer(
        "⚙️ **Sozlamalar bo'limi**\n\n"
        "Bu yerdan akkauntingizni o'chirishingiz yoki bot tilini o'zgartirishingiz mumkin.",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

async def main():
    logging.basicConfig(level=logging.INFO)
    await db.init_db()
    await start_web_server()
    
    scheduler.add_job(run_auto_sender, 'interval', minutes=1)
    scheduler.start()
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    
