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
    waiting_for_bot_token = State()

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

# --- 👥 PROFILLAR (KO'P AKKAUNT ULASH VA O'CHIRISH) ---
@dp.message(F.text == "👥 Profillar")
async def profiles_cmd(message: types.Message):
    accounts = await db.get_accounts(message.from_user.id)
    
    builder = InlineKeyboardMarkup(inline_keyboard=[])
    text = "👥 **Sizning ulangan profillaringiz:**\n\n"
    
    if accounts:
        for acc in accounts:
            acc_id, phone, is_active, interval, msg = acc
            status = "🟢 Faol" if is_active == 1 else "🔴 To'xtatilgan"
            text += f"📱 `{phone}` | Holati: {status}\n"
            builder.inline_keyboard.append([
                InlineKeyboardButton(text=f"❌ O'chirish ({phone})", callback_data=f"del_acc_{acc_id}"),
                InlineKeyboardButton(text="⏯ On/Off", callback_data=f"toggle_acc_{acc_id}_{is_active}")
            ])
    else:
        text += "Hozircha hech qanday profil ulanmagan.\n"

    builder.inline_keyboard.append([InlineKeyboardButton(text="➕ Yangi profil qo'shish", callback_data="add_new_profile")])
    await message.answer(text, reply_markup=builder, parse_mode="Markdown")

@dp.callback_query(F.data == "add_new_profile")
async def add_profile_start(callback: types.CallbackQuery, state: FSMContext):
    builder = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await callback.message.answer(
        "📱 Telegram akkauntingizni ulash uchun raqamingizni yuboring (masalan: `+998901234567`):",
        reply_markup=builder,
        parse_mode="Markdown"
    )
    await state.set_state(AuthState.waiting_for_phone)

@dp.callback_query(F.data.startswith("del_acc_"))
async def del_account_proc(callback: types.CallbackQuery):
    acc_id = int(callback.data.split("_")[2])
    await db.delete_account(acc_id)
    await callback.answer("Profil o'chirildi!", show_alert=True)
    await profiles_cmd(callback.message)

@dp.callback_query(F.data.startswith("toggle_acc_"))
async def toggle_account_proc(callback: types.CallbackQuery):
    _, _, acc_id, curr_status = callback.data.split("_")
    new_status = 0 if int(curr_status) == 1 else 1
    await db.update_account_status(int(acc_id), new_status)
    await callback.answer("Holat o'zgartirildi!", show_alert=True)
    await profiles_cmd(callback.message)

# --- TELEGRAM AKKAUNT SMS/2FA BILAN ULANISH ---
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
        await db.add_account(user_id, data.get("phone", ""), session_string)
        await message.answer("✅ Akkaunt muvaffaqiyatli bog'landi!", reply_markup=main_menu())
        await state.clear()
    else:
        if result == "SessionPasswordNeeded":
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
        await db.add_account(user_id, data.get("phone", ""), session_string)
        await message.answer("✅ Parol tasdiqlandi, akkaunt ulandi!", reply_markup=main_menu())
        await state.clear()
    else:
        await message.answer(f"❌ Parol xato: {result}\nQaytadan kiriting:")

# --- ⏱ INTERVAL ---
@dp.message(F.text == "⏱ Interval")
async def interval_menu(message: types.Message):
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="2 daqiqa", callback_data="set_int_2"), InlineKeyboardButton(text="5 daqiqa", callback_data="set_int_5")],
        [InlineKeyboardButton(text="7 daqiqa", callback_data="set_int_7"), InlineKeyboardButton(text="10 daqiqa", callback_data="set_int_10")],
        [InlineKeyboardButton(text="15 daqiqa", callback_data="set_int_15"), InlineKeyboardButton(text="20 daqiqa", callback_data="set_int_20")],
        [InlineKeyboardButton(text="25 daqiqa", callback_data="set_int_25"), InlineKeyboardButton(text="30 daqiqa", callback_data="set_int_30")],
        [InlineKeyboardButton(text="1 soat", callback_data="set_int_60"), InlineKeyboardButton(text="6 soat", callback_data="set_int_360")],
        [InlineKeyboardButton(text="⌨️ Qo'lda kiritish", callback_data="set_int_custom")]
    ])
    await message.answer("⏱ **Interval sozlamasi**\n\nQuyidan tarqatish oralig'ini tanlang:", reply_markup=builder, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("set_int_"))
async def process_interval(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split("_")[2]
    if action == "custom":
        await callback.message.answer("Daqiqalar sonini kiriting:")
        await state.set_state(AuthState.waiting_for_custom_interval)
    else:
        minutes = int(action)
        await db.update_account_interval(callback.from_user.id, minutes)
        await callback.answer(f"Interval {minutes} daqiqaga o'zgartirildi!", show_alert=True)

@dp.message(AuthState.waiting_for_custom_interval)
async def custom_interval_set(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        minutes = int(message.text)
        await db.update_account_interval(message.from_user.id, minutes)
        await message.answer(f"✅ Interval {minutes} daqiqaga o'rnatildi!", reply_markup=main_menu())
        await state.clear()
    else:
        await message.answer("❌ Faqat raqam kiriting:")

# --- 💬 XABAR ---
@dp.message(F.text == "💬 Xabar")
async def message_cmd(message: types.Message, state: FSMContext):
    await message.answer("Guruhlarga tarqatiladigan xabar matnini kiriting:")
    await state.set_state(AuthState.waiting_for_message)

@dp.message(AuthState.waiting_for_message)
async def save_message(message: types.Message, state: FSMContext):
    await db.update_account_message(message.from_user.id, message.text)
    await message.answer("✅ Xabar matni barcha faol profillaringizga saqlandi!", reply_markup=main_menu())
    await state.clear()

# --- 📁 GURUHLAR ---
@dp.message(F.text == "📁 Guruhlar")
async def groups_cmd(message: types.Message, state: FSMContext):
    groups = await db.get_groups(message.from_user.id)
    
    builder = InlineKeyboardMarkup(inline_keyboard=[])
    text = "📁 **Sizning guruhlaringiz:**\n\n"
    
    if groups:
        for g in groups:
            g_id, chat_id = g
            text += f"• `{chat_id}`\n"
            builder.inline_keyboard.append([InlineKeyboardButton(text=f"❌ O'chirish ({chat_id})", callback_data=f"del_group_{g_id}")])
    else:
        text += "Hozircha guruhlar yo'q.\n"
        
    builder.inline_keyboard.append([InlineKeyboardButton(text="➕ Yangi guruh qo'shish", callback_data="add_new_group")])
    await message.answer(text, reply_markup=builder, parse_mode="Markdown")

@dp.callback_query(F.data == "add_new_group")
async def add_group_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Guruh ID yoki username'ini kiriting (masalan: `@guruh_nomi`):")
    await state.set_state(AuthState.waiting_for_group)

@dp.message(AuthState.waiting_for_group)
async def save_group(message: types.Message, state: FSMContext):
    await db.add_group(message.from_user.id, message.text)
    await message.answer("✅ Guruh saqlandi!", reply_markup=main_menu())
    await state.clear()

@dp.callback_query(F.data.startswith("del_group_"))
async def del_group_proc(callback: types.CallbackQuery):
    g_id = int(callback.data.split("_")[2])
    await db.delete_group(g_id)
    await callback.answer("Guruh o'chirildi!", show_alert=True)
    await groups_cmd(callback.message)

# --- ▶️ ISHGA TUSHIRISH ---
@dp.message(F.text == "▶️ Ishga tushirish")
async def start_auto(message: types.Message):
    accounts = await db.get_accounts(message.from_user.id)
    if not accounts:
        await message.answer("❌ Avval `👥 Profillar` bo'limidan Telegram akkauntingizni ulang!")
        return
    for acc in accounts:
        await db.update_account_status(acc[0], 1)
    await message.answer("🚀 Avto-xabar yuborish jarayoni barcha ulangan profillaringiz uchun ishga tushirildi!")

# --- 📊 STATISTIKA ---
@dp.message(F.text == "📊 Statistika")
async def stats_cmd(message: types.Message):
    total, active, groups = await db.get_stats()
    await message.answer(
        f"📊 **Bot Statistikasi:**\n\n"
        f"👥 Jami foydalanuvchilar: {total}\n"
        f"🚀 Faol ulangan profillar: {active}\n"
        f"📁 Saqlangan guruhlar: {groups}",
        parse_mode="Markdown"
    )

# --- ⭐️ PRO STATUS ---
@dp.message(F.text == "⭐️ Pro")
async def pro_cmd(message: types.Message):
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Pro sotib olish (10,000 so'm)", callback_data="buy_pro")]
    ])
    await message.answer(
        "⭐️ **Pro Statusi**\n\n"
        "Pro bilan cheksiz guruh va tezkor interval funksiyalarini olasiz.\n"
        "Balansingiz orqali to'lov qilishingiz mumkin.",
        reply_markup=builder,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "buy_pro")
async def buy_pro_proc(callback: types.CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    balance = user[0] if user else 0
    if balance >= 10000:
        await db.activate_pro(callback.from_user.id)
        await callback.answer("🎉 Pro statusi muvaffaqiyatli faollashtirildi!", show_alert=True)
    else:
        await callback.answer(f"❌ Balans yetarli emas. Sizda: {balance} so'm bor.", show_alert=True)

# --- 🥷 SHAXSIY BOT YARATISH ---
@dp.message(F.text == "🥷 Shaxsiy bot")
async def personal_bot_cmd(message: types.Message, state: FSMContext):
    await message.answer(
        "🥷 **Shaxsiy bot yaratish**\n\n"
        "O'zingizning xuddi shunday avto-xabar botingiz bo'lishini xohlasangiz, @BotFather'dan olingan Bot TOKENini yuboring:",
        parse_mode="Markdown"
    )
    await state.set_state(AuthState.waiting_for_bot_token)

@dp.message(AuthState.waiting_for_bot_token)
async def save_bot_token(message: types.Message, state: FSMContext):
    token = message.text.strip()
    if ":" in token:
        await db.save_custom_bot(message.from_user.id, token)
        await message.answer("✅ Shaxsiy botingiz qabul qilindi! Tezzatda ishga tushiriladi.", reply_markup=main_menu())
        await state.clear()
    else:
        await message.answer("❌ Noto'g'ri TOKEN kiritdingiz. Qaytadan kiriting:")

# --- 👥 REFERAL DASTUR ---
@dp.message(F.text == "👥 Referal dastur")
async def referral_cmd(message: types.Message):
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={message.from_user.id}"
    ref_count = await db.get_referral_count(message.from_user.id)
    
    await message.answer(
        f"👥 **Referal dastur**\n\n"
        f"Har bir taklif qilgan do'stingiz uchun **500 so'm** balans olasiz!\n\n"
        f"🔗 Sizning havolangiz:\n`{ref_link}`\n\n"
        f"📊 Taklif qilinganlar: **{ref_count} ta**",
        parse_mode="Markdown"
    )

# --- 👤 PROFIL ---
@dp.message(F.text == "👤 Profil")
async def profile_cmd(message: types.Message):
    user = await db.get_user(message.from_user.id)
    accounts = await db.get_accounts(message.from_user.id)
    
    if user:
        balance, is_pro, expire, _ = user
        pro_txt = "⭐️ Pro" if is_pro == 1 else "👤 Oddiy"
        
        await message.answer(
            f"👤 **Sizning profilingiz:**\n\n"
            f"🆔 ID: `{message.from_user.id}`\n"
            f"💰 Balans: {balance} so'm\n"
            f"⭐ Daraja: {pro_txt}\n"
            f"📱 Ulangan profillar soni: {len(accounts)} ta",
            parse_mode="Markdown"
        )

# --- ⚙️ SOZLAMALAR ---
@dp.message(F.text == "⚙️ Sozlamalar")
async def settings_cmd(message: types.Message):
    await message.answer(
        "⚙️ **Sozlamalar:**\n\n"
        "Bot tili: O'zbekcha 🇺🇿\n"
        "Xabarnomalar: Yoqilgan 🔔",
        reply_markup=main_menu()
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
            
