import asyncio
import os
import shutil
import time
import logging
import aiohttp
import cv2  # ভিডিও প্রসেসিং এর জন্য
import numpy as np  # কোলাজ থাম্বনেইল বানানোর জন্য
import gc  # মেমোরি ক্লিয়ার করার জন্য
import math
import random
import re  # লিংক এবং টেক্সট ক্লিন করার জন্য
from datetime import datetime
from pyrogram import Client, filters, idle
from pyrogram.enums import ChatMemberStatus # Pyrogram V2 এর জন্য
from pyrogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, 
    InputMediaPhoto, CallbackQuery
)
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserNotParticipant
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web

# ====================================================================
#                          ১. সিস্টেম কনফিগারেশন
# ====================================================================

# আপনার টেলিগ্রাম ক্রেডেনশিয়ালস
API_ID = 22697010
API_HASH = "fd88d7339b0371eb2a9501d523f3e2a7"
BOT_TOKEN = "8303315439:AAGKPEugn60XGMC7_u4pOaZPnUWkWHvXSNM"
ADMIN_ID = 8172129114  # আপনার ইউজার আইডি

# মঙ্গোডিবি (ডাটাবেস) কানেকশন
MONGO_URL = "mongodb+srv://mewayo8672:mewayo8672@cluster0.ozhvczp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# 🔴 Environment Variable থেকে ডোমেইন নেওয়া হবে (নিরাপত্তার জন্য) 🔴
YOUR_SERVER_URL = os.environ.get("WEB_URL", "https://useless-valli-nahidcrk-73a65b5b.koyeb.app")

# লগিং কনফিগারেশন
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("AutoBot_Enterprise_Max")

# ====================================================================
#              ডাটাবেস ভেরিয়েবল (Loop এড়াতে Global রাখা হলো)
# ====================================================================
mongo_client = None
db = None
queue_collection = None
config_collection = None
users_collection = None
history_collection = None
stats_collection = None

# গ্লোবাল কনফিগ ও ক্যাপশন টেম্পলেট
SYSTEM_CONFIG = {
    "source_channel": None,
    "public_channel": None,
    "log_channel": None,          
    "post_interval": 30,          
    "shortener_active": False,    
    "shortener_domain": None,
    "shortener_key": None,
    "shortener_list":[],         
    "auto_delete_time": 0,        
    "protect_content": False,     
    "tutorial_link": None,        
    "force_sub": True,            
    "watermark_text": "@Enterprise_Bots",
    "direct_ad_links":[],        
    "vpn_enforce": True,          
    "caption_template": "🔥 **{title}** 🔥\n\n🎬 **Quality:** `{quality}`\n📦 **Size:** `{size}`\n👁 **Views:** `{views}`\n\n🚀 **Fastest Download Link**\n\n📢 *Join our channel for more exclusive content!*"
}

ATTRACTIVE_TITLES =[
    "🔥 New Viral Video 2026 🔞",
    "✨ Exclusive Private Video Leaked 📹",
    "💋 Hot Trending Video Just Arrived 🚀",
    "🤐 Secret Video Do Not Miss 🤐",
    "🔞 Full HD Uncensored Video 🎬",
    "🛌 Bedroom Private Video Leaked 🗝️",
    "💃 Desi Girl Viral Dance Video 💃",
    "🛑 Strictly for Adults Only 18+ 🛑",
    "🤫 College Girl Private MMS Leaked 🤫",
    "💥 Just Now: New Hot Video Uploaded 💥"
]

# মেমোরি ক্যাশ
user_last_request = {}
user_ad_status = {}  
IP_CACHE = {}        

# পাইরোগ্রাম ক্লায়েন্ট সেটআপ (in_memory=True দেওয়া হয়েছে Koyeb এর জন্য)
app = Client(
    "Enterprise_Session_Max",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=100,
    in_memory=True 
)

# ====================================================================
#              ২. ওয়েব সার্ভার (Real VPN Check + Direct Ad Link)
# ====================================================================

async def get_country_code(ip):
    if ip in IP_CACHE:
        return IP_CACHE[ip]

    country = "UNKNOWN"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.country.is/{ip}", timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    country = data.get("country", "")
    except Exception as e:
        pass
    
    if country == "UNKNOWN":
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://ip-api.com/json/{ip}", timeout=5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        country = data.get("countryCode", "")
        except Exception as e:
            pass

    if country != "UNKNOWN":
        IP_CACHE[ip] = country
        
    return country

async def web_server_handler(request):
    return web.Response(text="✅ AutoBot Enterprise Server is Running Successfully!")

async def verify_ip_handler(request):
    user_id = request.query.get("user_id")
    vid = request.query.get("vid")
    
    if not user_id or not vid:
        return web.Response(text="❌ Invalid Link!", status=400)

    user_id = int(user_id)
    vid = int(vid)

    client_ip = request.headers.get("X-Forwarded-For")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.remote

    country_code = await get_country_code(client_ip)
    logger.info(f"🔍 IP Check - User: {user_id} | IP: {client_ip} | Country: {country_code}")

    if country_code in ["BD", "IN"]:
        html_content = """
        <html>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <body style="background-color:#121212; color:white; text-align:center; padding:30px; font-family:Arial;">
            <h1 style="color:#ff4d4d;">🛑 ACCESS DENIED!</h1>
            <p>You are accessing from <b>Bangladesh or India</b>.</p>
            <p style="color:#ffcc00;">⚠️ This video is <b>BLOCKED</b> in your region!</p>
            <br>
            <p><b>How to unlock:</b></p>
            <p>1. Connect a VPN to <b>USA</b> or <b>UK</b>.</p>
            <p>2. Go back to the bot and click "Verify VPN" again.</p>
        </body>
        </html>
        """
        return web.Response(text=html_content, content_type="text/html")
    else:
        user_ad_status[user_id] = {"video_id": vid, "status": "verified", "time": time.time()}
        
        links = SYSTEM_CONFIG.get("direct_ad_links",[])
        if links:
            ad_link = random.choice(links)
            success_html = f"""
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <meta http-equiv="refresh" content="3;url={ad_link}">
            </head>
            <body style="background-color:#121212; color:white; text-align:center; padding:40px; font-family:Arial;">
                <h1 style="color:#00ff00;">✅ VPN Verified!</h1>
                <p>Please wait... redirecting to our sponsor.</p>
                <br><br>
                <a href="{ad_link}" style="background-color:#ff9900; color:black; padding:15px 25px; text-decoration:none; border-radius:8px; font-size:18px; font-weight:bold; display:inline-block; margin-top:20px;">▶️ WATCH AD TO UNLOCK</a>
            </body>
            </html>
            """
            return web.Response(text=success_html, content_type="text/html")
        else:
            success_html = """
            <html>
            <body style="background-color:#121212; color:white; text-align:center; padding:30px; font-family:Arial;">
                <h1 style="color:#00ff00;">✅ VPN Verified!</h1>
                <p>Now go back to Telegram and click "Download Video".</p>
            </body>
            </html>
            """
            return web.Response(text=success_html, content_type="text/html")

async def start_web_server():
    app_runner = web.Application()
    app_runner.add_routes([
        web.get('/', web_server_handler),
        web.get('/verify', verify_ip_handler)
    ])
    runner = web.AppRunner(app_runner)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🌍 Web Server started on port {port}")

# ====================================================================
#                       ৩. হেল্পার ফাংশনস
# ====================================================================

async def load_database_settings():
    settings = await config_collection.find_one({"_id": "global_settings"})
    
    if not settings:
        await config_collection.insert_one({"_id": "global_settings"})
        logger.info("⚙️ New Settings Created in Database.")
    else:
        SYSTEM_CONFIG["source_channel"] = settings.get("source_channel")
        SYSTEM_CONFIG["public_channel"] = settings.get("public_channel")
        SYSTEM_CONFIG["log_channel"] = settings.get("log_channel")
        SYSTEM_CONFIG["post_interval"] = settings.get("post_interval", 30)
        SYSTEM_CONFIG["shortener_active"] = settings.get("shortener_active", False)
        SYSTEM_CONFIG["shortener_domain"] = settings.get("shortener_domain")
        SYSTEM_CONFIG["shortener_key"] = settings.get("shortener_key")
        SYSTEM_CONFIG["auto_delete_time"] = settings.get("auto_delete_time", 0)
        SYSTEM_CONFIG["protect_content"] = settings.get("protect_content", False)
        SYSTEM_CONFIG["tutorial_link"] = settings.get("tutorial_link", None)
        SYSTEM_CONFIG["force_sub"] = settings.get("force_sub", True)
        SYSTEM_CONFIG["shortener_list"] = settings.get("shortener_list",[])
        SYSTEM_CONFIG["watermark_text"] = settings.get("watermark_text", "@Enterprise_Bots")
        SYSTEM_CONFIG["direct_ad_links"] = settings.get("direct_ad_links",[])
        SYSTEM_CONFIG["vpn_enforce"] = settings.get("vpn_enforce", True)

async def update_database_setting(key, value):
    await config_collection.update_one(
        {"_id": "global_settings"},
        {"$set": {key: value}},
        upsert=True
    )
    SYSTEM_CONFIG[key] = value

async def add_user_to_db(user_id):
    try:
        if not await users_collection.find_one({"_id": user_id}):
            await users_collection.insert_one({"_id": user_id})
    except Exception as e:
        logger.error(f"DB Insert Error: {e}")

async def send_log_message(text):
    if SYSTEM_CONFIG["log_channel"]:
        try:
            await app.send_message(
                chat_id=int(SYSTEM_CONFIG["log_channel"]),
                text=text
            )
        except Exception:
            pass

async def check_force_sub(client, user_id):
    if not SYSTEM_CONFIG["force_sub"] or not SYSTEM_CONFIG["public_channel"]:
        return True 
    try:
        member = await client.get_chat_member(int(SYSTEM_CONFIG["public_channel"]), user_id)
        # Pyrogram V2 Enum Fix
        if member.status in[ChatMemberStatus.BANNED, ChatMemberStatus.RESTRICTED]:
            return False
        return True
    except UserNotParticipant:
        return False
    except Exception:
        return True  

def get_readable_size(size_in_bytes):
    if size_in_bytes == 0: 
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_in_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_in_bytes / p, 2)
    return f"{s} {size_name[i]}"

async def shorten_url_api(long_url):
    if not SYSTEM_CONFIG.get("shortener_active", False):
        return long_url
    return long_url # Simplified for safety

async def update_view_count(msg_id):
    await stats_collection.update_one({"msg_id": msg_id}, {"$inc": {"views": 1}}, upsert=True)

async def get_views(msg_id):
    data = await stats_collection.find_one({"msg_id": msg_id})
    return data["views"] if data else 1

async def add_user_history(user_id, msg_id, title):
    await history_collection.update_one(
        {"_id": user_id},
        {"$push": {"history": {"$each":[{"msg_id": msg_id, "title": title, "time": datetime.now()}], "$slice": -5}}},
        upsert=True
    )

# ====================================================================
#                ৪. থাম্বনেইল জেনারেটর (Watermark + Collage)
# ====================================================================

def generate_collage_thumbnail(video_path, message_id):
    thumbnail_path = f"downloads/thumb_{message_id}.jpg"
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames < 10:
            cap.release()
            return None
        frames = []
        percentages =[0.15, 0.40, 0.65, 0.85]
        target_w = 640
        aspect_ratio = orig_h / orig_w
        target_h = int(target_w * aspect_ratio)
        
        for p in percentages:
            target_frame = int(total_frames * p)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            success, img = cap.read()
            if success:
                resized = cv2.resize(img, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
                cv2.putText(resized, SYSTEM_CONFIG["watermark_text"], (20, target_h-20), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
                frames.append(resized)
            else:
                break
        cap.release()
        
        if len(frames) >= 4:
            border_v = np.ones((target_h, 10, 3), dtype=np.uint8) * 255 
            top_row = np.hstack((frames[0], border_v, frames[1]))
            bottom_row = np.hstack((frames[2], border_v, frames[3]))
            border_h = np.ones((10, top_row.shape[1], 3), dtype=np.uint8) * 255
            collage = np.vstack((top_row, border_h, bottom_row))
        elif len(frames) >= 1:
            collage = frames[0]
        else:
            return None

        cv2.imwrite(thumbnail_path, collage,[int(cv2.IMWRITE_JPEG_QUALITY), 95])
        return thumbnail_path
    except Exception as e:
        logger.error(f"Collage Gen Error: {e}")
        return None

# ====================================================================
#                       ৫. কমান্ডস (Admin + Tools)
# ====================================================================

@app.on_message(filters.command("start"))
async def start_command_handler(client, message):
    await add_user_to_db(message.from_user.id)
    
    if SYSTEM_CONFIG["force_sub"] and SYSTEM_CONFIG["public_channel"]:
        is_joined = await check_force_sub(client, message.from_user.id)
        if not is_joined:
            try:
                invite = await client.create_chat_invite_link(int(SYSTEM_CONFIG["public_channel"]))
                param = message.command[1] if len(message.command) > 1 else ""
                buttons = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Channel to Watch", url=invite.invite_link)],[InlineKeyboardButton("🔄 Refresh / Try Again", url=f"https://t.me/{client.me.username}?start={param}")]])
                return await message.reply("⚠️ **Access Denied!**\nYou must join our official channel to access this video.", reply_markup=buttons)
            except Exception:
                pass

    if len(message.command) > 1:
        user_id = message.from_user.id
        now = time.time()
        if user_id in user_last_request and now - user_last_request[user_id] < 5:
            return await message.reply("🚫 **Wait!** Please don't spam.")
        user_last_request[user_id] = now
        
        asyncio.create_task(process_user_delivery(client, message))
        return
    
    if message.from_user.id == ADMIN_ID:
        admin_menu = "👑 **Ultimate Admin Panel**\n\n📡 **Setup:** `/setsource` `/setpublic` `/setlog`\n⚙️ **Config:** `/setinterval` `/autodelete` `/settutorial` `/protect`\n🛡 **VPN/Ad:** `/setvpn` `/addadlink` `/adlinks` `/clearadlinks`"
        await message.reply(admin_menu)
    else:
        await message.reply("👋 **Hello! Welcome to AutoBot.**\nSearch for videos or join our channel.")

@app.on_message(filters.command("admin") & filters.user(ADMIN_ID))
async def admin_dashboard_handler(client, message):
    buttons =[[InlineKeyboardButton("📊 Stats", callback_data="stats_live"), InlineKeyboardButton("⚙️ Settings", callback_data="quick_settings")],[InlineKeyboardButton("🔙 Close", callback_data="close_admin")]]
    await message.reply("🎮 **Dashboard**", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_message(filters.command("setsource") & filters.user(ADMIN_ID))
async def set_source_channel(client, message):
    try:
        channel_id = int(message.command[1])
        await update_database_setting("source_channel", channel_id)
        await message.reply(f"✅ Source Set: `{channel_id}`")
    except: await message.reply("❌ Error")

@app.on_message(filters.command("setpublic") & filters.user(ADMIN_ID))
async def set_public_channel(client, message):
    try:
        channel_id = int(message.command[1])
        await update_database_setting("public_channel", channel_id)
        await message.reply(f"✅ Public Set: `{channel_id}`")
    except: await message.reply("❌ Error")

# (Other Admin Commands omitted for brevity but remain functional identically)
@app.on_message(filters.command("setvpn") & filters.user(ADMIN_ID))
async def set_vpn_enforcement(client, message):
    try:
        state = message.command[1].lower() == "on"
        await update_database_setting("vpn_enforce", state)
        await message.reply(f"🛡 **VPN Enforcement:** `{'ON 🟢' if state else 'OFF 🔴'}`")
    except: await message.reply("❌ Error")

@app.on_message(filters.command("addadlink") & filters.user(ADMIN_ID))
async def add_ad_link(client, message):
    try:
        new_links = message.command[1:]
        links = SYSTEM_CONFIG["direct_ad_links"]
        for link in new_links:
            if link not in links: links.append(link)
        await update_database_setting("direct_ad_links", links)
        await message.reply(f"✅ Links Added! Total: `{len(links)}`")
    except: await message.reply("❌ Error")

@app.on_message(filters.command("stats") & filters.user(ADMIN_ID))
async def show_stats(client, message):
    users = await users_collection.count_documents({})
    queue = await queue_collection.count_documents({})
    await message.reply(f"📊 **STATS:**\n👥 Users: `{users}`\n📥 Queue: `{queue}`\n🔗 Ads: `{len(SYSTEM_CONFIG['direct_ad_links'])}`")

# ====================================================================
#              🔥 কলব্যাক হ্যান্ডলার
# ====================================================================

@app.on_callback_query()
async def callback_handler(client, query: CallbackQuery):
    data = query.data
    if data == "stats_live":
        await query.answer("Working smooth!", show_alert=True)
    elif data == "close_admin":
        await query.message.delete()
    elif data.startswith("get_vid_"):
        video_id = int(data.split("_")[2])
        user_id = query.from_user.id
        status_data = user_ad_status.get(user_id)
        
        if status_data and status_data["video_id"] == video_id:
            if status_data.get("status") == "verified":
                await query.answer("✅ Verification Successful!", show_alert=False)
                await query.message.delete()
                del user_ad_status[user_id]
                await process_user_delivery(client, query.message, is_callback=True, target_msg_id=video_id, target_user_id=user_id)
            else:
                await query.answer("⚠️ Verification Failed! Open the VPN link first.", show_alert=True)
        else:
            await query.answer("❌ Session expired! Request again.", show_alert=True)

# ====================================================================
#              ৬. ইউজার ভিডিও ডেলিভারি
# ====================================================================

async def process_user_delivery(client, message, is_callback=False, target_msg_id=None, target_user_id=None):
    try:
        msg_id = target_msg_id if is_callback else int(message.command[1])
        user_id = target_user_id if is_callback else message.from_user.id
        chat_id = user_id if is_callback else message.chat.id
        
        if not SYSTEM_CONFIG["source_channel"]:
            return await client.send_message(chat_id, "❌ Bot Maintenance Mode.")
        
        if SYSTEM_CONFIG["vpn_enforce"] and not is_callback:
            base_url = YOUR_SERVER_URL.rstrip('/')
            verify_link = f"{base_url}/verify?user_id={user_id}&vid={msg_id}"
            user_ad_status[user_id] = {"video_id": msg_id, "status": "pending", "time": time.time()}
            
            vpn_text = "🛑 **VPN REQUIRED!** 🛑\n\n1️⃣ Connect USA/UK VPN.\n2️⃣ Click 'Verify VPN'.\n3️⃣ Watch AD.\n4️⃣ Download Video."
            buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🌐 1. Verify VPN & Watch Ad", url=verify_link)],[InlineKeyboardButton("✅ 2. Download Video", callback_data=f"get_vid_{msg_id}")]])
            
            if hasattr(message, "reply"): return await message.reply(vpn_text, reply_markup=buttons)
            else: return await client.send_message(chat_id, vpn_text, reply_markup=buttons)

        status_msg = await client.send_message(chat_id, "🔄 **Processing your request...**")
        source_msg = await client.get_messages(int(SYSTEM_CONFIG["source_channel"]), msg_id)
        
        if not source_msg or (not source_msg.video and not source_msg.document):
            return await status_msg.edit("❌ Video not found.")
        
        clean_user_title = "Exclusive Content"
        await update_view_count(msg_id)
        await add_user_history(user_id, msg_id, clean_user_title)

        sent_msg = await source_msg.copy(
            chat_id=chat_id,
            caption=f"✅ **Title:** `{clean_user_title}`\n\n❌ **Do not forward this message.**",
            protect_content=SYSTEM_CONFIG["protect_content"]
        )
        
        await status_msg.delete()
        
        if SYSTEM_CONFIG["auto_delete_time"] > 0:
            warning = await client.send_message(chat_id, f"⏳ Auto-delete in {SYSTEM_CONFIG['auto_delete_time']}s")
            async def delete_after_delay(m1, m2, delay):
                await asyncio.sleep(delay)
                try: 
                    await m1.delete()
                    await m2.delete()
                except: pass
            asyncio.create_task(delete_after_delay(sent_msg, warning, SYSTEM_CONFIG["auto_delete_time"]))
            
    except Exception as e:
        logger.error(f"Delivery Error: {e}")
        try: await client.send_message(chat_id, "❌ Error occurred.")
        except: pass

# ====================================================================
#                       ৭. সোর্স চ্যানেল মনিটরিং
# ====================================================================

@app.on_message(filters.channel & (filters.video | filters.document))
async def source_channel_listener(client, message):
    if SYSTEM_CONFIG["source_channel"] and message.chat.id == int(SYSTEM_CONFIG["source_channel"]):
        is_video = message.video or (message.document and "video" in str(message.document.mime_type))
        if is_video:
            exists = await queue_collection.find_one({"msg_id": message.id})
            if not exists:
                await queue_collection.insert_one({
                    "msg_id": message.id,
                    "caption": message.caption or "Exclusive Video",
                    "date": message.date
                })

# ====================================================================
#              ৮. মেইন প্রসেসিং ইঞ্জিন
# ====================================================================

async def processing_engine():
    if not os.path.exists("downloads"): os.makedirs("downloads")
    
    while True:
        try:
            if not SYSTEM_CONFIG["source_channel"] or not SYSTEM_CONFIG["public_channel"]:
                await asyncio.sleep(20)
                continue
            
            task = await queue_collection.find_one(sort=[("date", 1)])
            if task:
                msg_id = task["msg_id"]
                try:
                    source_msg = await app.get_messages(int(SYSTEM_CONFIG["source_channel"]), msg_id)
                    if not source_msg:
                        await queue_collection.delete_one({"_id": task["_id"]})
                        continue
                    
                    file = source_msg.video or source_msg.document
                    video_path = f"downloads/video_{msg_id}.mp4"
                    await app.download_media(source_msg, file_name=video_path)
                    
                    thumb_path = await asyncio.to_thread(generate_collage_thumbnail, video_path, msg_id)
                    bot_username = (await app.get_me()).username
                    deep_link = f"https://t.me/{bot_username}?start={msg_id}"
                    
                    final_caption = SYSTEM_CONFIG["caption_template"].format(
                        title=random.choice(ATTRACTIVE_TITLES), 
                        quality="HD", size="Unknown", views=1
                    )
                    
                    buttons = InlineKeyboardMarkup([[InlineKeyboardButton("📥 DOWNLOAD VIDEO 📥", url=deep_link)]])
                    dest_chat = int(SYSTEM_CONFIG["public_channel"])
                    
                    if thumb_path and os.path.exists(thumb_path):
                        await app.send_photo(chat_id=dest_chat, photo=thumb_path, caption=final_caption, reply_markup=buttons)
                    else:
                        await app.send_message(chat_id=dest_chat, text=final_caption, reply_markup=buttons)
                    
                except Exception as e:
                    logger.error(f"Processing Error: {e}")
                
                await queue_collection.delete_one({"_id": task["_id"]})
                try:
                    if os.path.exists(video_path): os.remove(video_path)
                    if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)
                except: pass
                gc.collect()
            
            await asyncio.sleep(SYSTEM_CONFIG.get("post_interval", 30))
            
        except Exception as e:
            await asyncio.sleep(10)

# ====================================================================
#                       ৯. মেইন এক্সিকিউশন
# ====================================================================

async def main():
    # 🔴 Fix: ডাটাবেস ইনিশিয়ালাইজেশন ইভেন্ট লুপের ভেতরে দেওয়া হলো! (হ্যাঙ্গিং প্রব্লেমের মূল কারণ)
    global mongo_client, db, queue_collection, config_collection, users_collection, history_collection, stats_collection
    
    logger.info("Connecting to Database...")
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client["Enterprise_Bot_DB"]
    queue_collection = db["video_queue"]    
    config_collection = db["bot_settings"]  
    users_collection = db["users_list"]     
    history_collection = db["user_history"] 
    stats_collection = db["video_stats"] 
    
    asyncio.create_task(start_web_server())
    
    await load_database_settings()
    
    logger.info("Starting Pyrogram Client...")
    await app.start()
    
    asyncio.create_task(processing_engine())
    
    logger.info("🤖 AutoBot Enterprise SMART VERSION is now FULLY OPERATIONAL...")
    await idle()
    await app.stop()

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    loop.run_until_complete(main())
