from flask import Flask
import threading
import telebot

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "salom bot ishlayapti", 200

# ======================================
# BOT
TOKEN = "8481480290:AAE74ULztxB8khVBRMVGIajFrSVe49632fI"

bot = telebot.TeleBot(TOKEN)
# ======================================
# Botni kodlari

import asyncio
import logging
import os
import uuid
import yt_dlp

from fastapi import FastAPI
from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.chat_member_status import ChatMemberStatus

# ---------- SOZLAMALAR ----------
BOT_TOKEN = "8481480290:AAE74ULztxB8khVBRMVGIajFrSVe49632fI"  # Shu yerga tokeningizni qo'ying
CHANNELS = {
    "@slx_vibee": "EXCITE DOWNLOADER BOT CHANNEL",
}
EXTRA_BUTTONS = [
    {"text": "🌐 BIZNING WEB SITEMIZ ✅", "url": "https://excite-download-bot.netlify.app/"},
    {"text": "📢 BIZNING KANALIMIZ ✅", "url": "https://t.me/slx_vibee"},
]

logging.basicConfig(level=logging.INFO)

# --- FastAPI ---
app = FastAPI()

# --- Aiogram 3.x ---
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
router = Router()
dp.include_router(router)

# --- GLOBAL SAQLAGICH ---
search_results = {}   # {user_id: [video_info_list]}
user_pages = {}       # {user_id: current_page}
user_queries = {}     # {user_id: search_text}
user_locks = {}       # {user_id: asyncio.Lock()}
user_subs = {}        # {user_id: [channel_list_remaining]}

# --------- yordamchi funksiyalar ---------
async def get_user_lock(user_id: int) -> asyncio.Lock:
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()
    return user_locks[user_id]

async def check_subscriptions(user_id: int) -> bool:
    """Foydalanuvchi qaysi kanallarga obuna bo'lganini tekshiradi."""
    if user_id not in user_subs:
        user_subs[user_id] = list(CHANNELS.keys())
    remaining = user_subs[user_id]
    updated = []
    for channel in remaining:
        try:
            chat = await bot.get_chat(channel)
            member = await bot.get_chat_member(chat.id, user_id)
            if member.status in (
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.CREATOR,
            ):
                continue
            else:
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

# --------- Obuna tekshirish callback ----------
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

# --------- Foydalanuvchi xabar ----------
@router.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    if not await check_subscriptions(user_id):
        kb = await subscription_keyboard(user_id)
        return await message.answer(
            "❌ Botdan foydalanish uchun majburiy kanallarga obuna bo‘ling!",
            reply_markup=kb
        )

    if not message.text:
        return await message.answer("Iltimos, video link yoki musiqa nomini yuboring.")

    text = message.text.strip()

    # --- VIDEO LINK ---
    if any(x in text for x in ["youtube.com","youtu.be","instagram.com","tiktok.com"]):
        status_msg = await message.answer(f"⏳ Video yuklanmoqda:\n Video havolasi- <b>{text}</b>")
        unique_id = uuid.uuid4().hex
        outtmpl = f"video_{user_id}_{unique_id}.%(ext)s"
        ydl_opts = {"format": "best", "outtmpl": outtmpl, "quiet": True}

        file_path = None
        try:
            lock = await get_user_lock(user_id)
            async with lock:
                loop = asyncio.get_event_loop()
                info = await loop.run_in_executor(
                    None,
                    lambda: yt_dlp.YoutubeDL(ydl_opts).extract_info(text, download=True)
                )
                file_path = yt_dlp.YoutubeDL(ydl_opts).prepare_filename(info)

            caption = (
                "✨ @excite_download_bot — Birinchi raqamli yuklovchi bot ✅\n\n"
                "📢 Rasmiy kanalimizga obuna bo‘ling: @slx_vibee"
                "📩 Murojaat uchun admin: @youtube_excite 👤\n\n"
            )
            kb = extra_keyboard()
            kb.inline_keyboard.insert(0, [InlineKeyboardButton(text="📄 Tavsif", callback_data=f"desc_{unique_id}")])

            search_results[user_id] = [{
                "title": info.get("title"),
                "description": info.get("description", "📄 Tavsif topilmadi"),
                "webpage_url": text,
                "id": unique_id
            }]
            await bot.send_video(
                message.chat.id,
                video=FSInputFile(file_path),
                caption=caption,
                reply_markup=kb
            )
            await status_msg.delete()
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        return

    # --- MUSIQA QIDIRISH ---
    status_msg = await message.answer(f"🎵 Musiqa qidirilmoqda 🔎:  <b>{text}</b>")
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(
            None,
            lambda: yt_dlp.YoutubeDL({"format": "bestaudio/best", "quiet": True}).extract_info(f"ytsearch10:{text}", download=False)
        )
        entries = info.get("entries", [])
        if not entries:
            await status_msg.edit_text(f"❌ Hech narsa topilmadi:  <b>{text}</b>")
            return

        search_results[user_id] = [
            {**entry, "id": str(uuid.uuid4())} for entry in entries
        ]
        user_pages[user_id] = 0
        user_queries[user_id] = text
        await send_music_page(message.chat.id, user_id, 0, text, edit_message=status_msg)
    except Exception as e:
        await status_msg.edit_text(f"❌ Qidirishda xatolik: {e}")
        await message.answer(text, reply_markup=extra_keyboard())

# --------- Natijalarni sahifa bo'yicha ko'rsatish ----------
async def send_music_page(chat_id, user_id, page, search_text, edit_message: Message = None):
    if not await check_subscriptions(user_id):
        kb = await subscription_keyboard(user_id)
        await bot.send_message(chat_id, "❌ Botdan foydalanish uchun majburiy kanallarga obuna bo‘ling!", reply_markup=kb)
        return

    entries = search_results.get(user_id, [])
    per_page = 10
    start = page*per_page
    end = start+per_page
    subset = entries[start:end]

    header = f"🎵 Natijalar:  <b>{search_text}</b>\n\n"
    lines = [f"{i}. {e.get('title','Noma\'lum')}" for i,e in enumerate(subset,start=start+1)]
    text = header + "\n".join(lines)

    row1 = [InlineKeyboardButton(text=f"{i}", callback_data=f"song_{i}") for i in range(start+1,min(start+6,end+1))]
    row2 = [InlineKeyboardButton(text=f"{i}", callback_data=f"song_{i}") for i in range(start+6,min(end+1,len(entries)+1))]
    buttons = []
    if row1: buttons.append(row1)
    if row2: buttons.append(row2)

    nav = []
    if page>0:
        nav.append(InlineKeyboardButton("⬅️ Ortga", callback_data=f"page_{page-1}"))
    if end<len(entries):
        nav.append(InlineKeyboardButton("➡️ Keyingi", callback_data=f"page_{page+1}"))
    if nav:
        buttons.append(nav)

    buttons.extend([[InlineKeyboardButton(text=btn["text"], url=btn["url"])] for btn in EXTRA_BUTTONS])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    if edit_message:
        await edit_message.edit_text(text, reply_markup=kb)
    else:
        await bot.send_message(chat_id,text,reply_markup=kb)

# --------- Callback handler ----------
@router.callback_query(F.data.startswith(("song_","page_","desc_")))
async def callback_handler(callback: CallbackQuery):
    user_id = callback.from_user.id

    if not await check_subscriptions(user_id):
        kb = await subscription_keyboard(user_id)
        await callback.message.edit_text("❌ Hali barcha majburiy kanallarga obuna bo‘lmadingiz!", reply_markup=kb)
        return

    data = callback.data
    entries = search_results.get(user_id, [])

    if data.startswith("song_"):
        idx = int(data.split("_")[1])-1
        if idx<0 or idx>=len(entries):
            return await callback.message.answer("❌ Noto'g'ri tanlov.")
        video = entries[idx]
        url = video.get("webpage_url")
        title = video.get("title","Noma'lum")
        loading = await callback.message.answer(f"⏳ Yuklanmoqda: <b>{title}</b>")
        unique_id = str(uuid.uuid4())
        outtmpl = f"music_{user_id}_{unique_id}.%(ext)s"
        ydl_opts = {
            "format":"bestaudio/best",
            "outtmpl":outtmpl,
            "postprocessors":[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":"128"}],
            "quiet":True
        }
        try:
            lock = await get_user_lock(user_id)
            async with lock:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))
            file_path = f"music_{user_id}_{unique_id}.mp3"

            caption = (
                "✨ @excite_download_bot — Birinchi raqamli yuklovchi bot ✅\n\n"
                "📢 Rasmiy kanalimizga obuna bo‘ling: @slx_vibee"
                "📩 Murojaat uchun admin: @youtube_excite 👤\n\n"
            )
            kb = extra_keyboard()

            await bot.send_audio(
                chat_id=callback.message.chat.id,
                audio=FSInputFile(file_path),
                title=title,
                performer=video.get("uploader"),
                caption=caption,
                reply_markup=kb
            )
            await loading.delete()
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    elif data.startswith("page_"):
        page = int(data.split("_")[1])
        user_pages[user_id] = page
        search_text = user_queries.get(user_id, "qidiruv")
        await send_music_page(callback.message.chat.id,user_id,page,search_text,edit_message=callback.message)

    elif data.startswith("desc_"):
        unique_id = data.split("_")[1]
        for video in entries:
            if video.get("id") == unique_id:
                await callback.message.answer(f"📄 Tavsif:\n \n{video.get('description','Tavsif topilmadi')}")
                break
        await callback.answer()

# --------- Foydalanuvchi obunalarini fon monitor qilish ----------
async def monitor_subscriptions():
    while True:
        try:
            for user_id in list(user_subs.keys()):
                remaining_before = list(user_subs[user_id])
                await check_subscriptions(user_id)
                remaining_after = user_subs[user_id]

                if len(remaining_after) > 0 and len(remaining_after) != len(remaining_before):
                    try:
                        kb = await subscription_keyboard(user_id)
                        await bot.send_message(
                            chat_id=user_id,
                            text="❌ Siz majburiy kanallardan birini tark etdingiz!\nIltimos, qayta obuna bo‘ling:",
                            reply_markup=kb
                        )
                    except Exception:
                        pass
        except Exception as e:
            logging.error(f"Error in subscription monitor: {e}")
        await asyncio.sleep(60)

# --------- FastAPI health-check ----------
@app.get("/")
async def root():
    return {"status":"Bot ishlayapti ✅"}

# --------- Botni ishga tushirish ----------
async def run_bot():
    await dp.start_polling(bot, skip_updates=True)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(run_bot())
    asyncio.create_task(monitor_subscriptions())

if __name__=="__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)


# ======================================
#  Botni va Serverni ishga tushrsh

def run_bot():
    bot.polling(non_stop=True)

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=5000, debug=True)
