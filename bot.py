import os
import threading
import asyncio
import logging
import uuid
import yt_dlp
from flask import Flask
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, FSInputFile
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.chat_member_status import ChatMemberStatus

# ---------- SOZLAMALAR ----------
BOT_TOKEN = "8481480290:AAE74ULztxB8khVBRMVGIajFrSVe49632fI"
CHANNELS = {
    "@slx_vibee": "EXCITE DOWNLOADER BOT CHANNEL",
}
EXTRA_BUTTONS = [
    {"text": "🌐 BIZNING WEB SITEMIZ ✅", "url": "https://excite-download-bot.netlify.app/"},
    {"text": "📢 BIZNING KANALIMIZ ✅", "url": "https://t.me/slx_vibee"},
]

logging.basicConfig(level=logging.INFO)

# --- Flask app ---
app = Flask(__name__)

# --- Aiogram 3.x ---
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
router = Router()
dp.include_router(router)

# --- Global o‘zgaruvchilar ---
search_results = {}
user_pages = {}
user_queries = {}
user_locks = {}
user_subs = {}

# --------- Yordamchi funksiyalar ---------
async def get_user_lock(user_id: int) -> asyncio.Lock:
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
    return user_locks[user_id]

async def check_subscriptions(user_id: int) -> bool:
    if user_id not in user_subs:
        user_subs[user_id] = list(CHANNELS.keys())

    remaining = user_subs[user_id]
    updated = []
    for channel in remaining:
        try:
            chat = await bot.get_chat(channel)
            member = await bot.get_chat_member(chat.id, user_id)
            if member.status not in (
                ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR
            ):
                updated.append(channel)
        except Exception:
            updated.append(channel)

    user_subs[user_id] = updated
    return len(updated) == 0

async def subscription_keyboard(user_id: int) -> InlineKeyboardMarkup:
    rows = []
    for channel in user_subs.get(user_id, list(CHANNELS.keys())):
        name = CHANNELS.get(channel, channel)
        try:
            chat = await bot.get_chat(channel)
            link = f"https://t.me/{chat.username}" if getattr(chat, "username", None) else f"https://t.me/{channel.lstrip('@')}"
        except Exception:
            link = f"https://t.me/{channel.lstrip('@')}"
        rows.append([InlineKeyboardButton(text=name, url=link)])
    rows.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subs")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def extra_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=btn["text"], url=btn["url"])] for btn in EXTRA_BUTTONS]
    )

# --------- /start ----------
@router.message(CommandStart())
async def cmd_start(message: Message):
    if not await check_subscriptions(message.from_user.id):
        kb = await subscription_keyboard(message.from_user.id)
        await message.answer("❌ Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:", reply_markup=kb)
    else:
        await message.answer(
            "✅ Obunangiz tasdiqlandi!\n\n🔗 Endi video linki yoki musiqa nomini yuboring 🎵",
            reply_markup=extra_keyboard()
        )

# --------- Callback tekshirish ----------
@router.callback_query(F.data == "check_subs")
async def check_subs(callback: CallbackQuery):
    if await check_subscriptions(callback.from_user.id):
        await callback.message.edit_text(
            "✅ Obunangiz tasdiqlandi!\n\n🔗 Endi video linki yoki musiqa nomini yuboring 🎵",
            reply_markup=extra_keyboard()
        )
    else:
        kb = await subscription_keyboard(callback.from_user.id)
        await callback.message.edit_text("❌ Hali barcha kanallarga obuna bo‘lmadingiz!", reply_markup=kb)

# --------- Oddiy xabarlar ----------
@router.message()
async def handle_message(message: Message):
    await message.answer("🔗 Bu Flask versiyasi ishlayapti — sizning botingiz faollashgan!")

# --------- Flask sahifa ----------
@app.route("/", methods=["GET"])
def home():
    return "✅ Bot Flask serverda ishlayapti", 200

# --------- Botni ishga tushirish ----------
def run_bot():
    asyncio.run(dp.start_polling(bot, skip_updates=True))

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
