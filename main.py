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
from pyrogram.enums import ChatMemberStatus # 🔴 Pyrogram V2 এর জন্য যোগ করা হয়েছে
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

# 🔴 ডাটাবেস ইনিশিলাইজেশন ভেরিয়েবল (লুপ ফ্রিজ এড়াতে গ্লোবাল করা হলো)
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
    "vpn_enforce": True,          # ভিপিএন সিস্টেম অন
    "caption_template": "🔥 **{title}** 🔥\n\n🎬 **Quality:** `{quality}`\n📦 **Size:** `{size}`\n👁 **Views:** `{views}`\n\n🚀 **Fastest Download Link**\n\n📢 *Join our channel for more exclusive content!*"
}

# কাস্টম আকর্ষণীয় টাইটেল লিস্ট
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
    "💥 Just Now: New Hot Video Uploaded 💥",
    "🚿 Bathroom Hidden Cam Video 🚿",
    "💘 Lovers Private Moments Leaked 💘",
    "🍑 Hot Bhabhi Romance Video 🍑",
    "🌶️ Spicy Video Watch Before Delete 🌶️",
    "🎥 Leaked: Famous Star Private Video 🎥",
    "👅 Wild Romance Full HD Video 👅",
    "👙 Bikini Girl Viral TikTok Video 👙",
    "🍌 Hot & Sexy Video Collection 2026 🍌",
    "🔦 Night Vision Hidden Camera Video 🔦",
    "🛌 Hotel Room Secret Video Viral 🛌",
    "🌧️ Rain Dance Hot Video Leaked 🌧️",
    "🚌 Public Bus Romance Caught on Cam 🚌",
    "👀 Viral Scandal Video 2026 👀",
    "💣 Bomb Shell Hot Video 💣",
    "📱 Girlfriend Private Video Leaked 📱",
    "🔥 Most Wanted Viral Video 🔥",
    "🚧 Warning: 18+ Content Inside 🚧",
    "👅 Tongue Action Viral Video 👅",
    "💃 Stage Dance Hot Performance 💃",
    "🔞 Premium Leaked Content Free 🔞"
]

# মেমোরি ক্যাশ
user_last_request = {}
user_ad_status = {}  
IP_CACHE = {}        

# 🔴 পাইরোগ্রাম ক্লায়েন্ট সেটআপ (in_memory=True দেওয়া হয়েছে যাতে Koyeb এ সেশন লক না হয়)
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
    """ইউজারের আসল দেশ বের করার ফাংশন"""
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
    """সিম্পল ওয়েব পেজ রেসপন্স"""
    return web.Response(text="✅ AutoBot Enterprise Server is Running Successfully!")

async def verify_ip_handler(request):
    """ভিপিএন ভেরিফিকেশন এবং অ্যাড রিডাইরেক্ট রাউট"""
    user_id = request.query.get("user_id")
    vid = request.query.get("vid")
    
    if not user_id or not vid:
        return web.Response(text="❌ Invalid Link!", status=400)

    user_id = int(user_id)
    vid = int(vid)

    # ইউজারের সঠিক আইপি বের করা
    client_ip = request.headers.get("X-Forwarded-For")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.remote

    country_code = await get_country_code(client_ip)
    logger.info(f"🔍 IP Check - User: {user_id} | IP: {client_ip} | Country: {country_code}")

    # বাংলাদেশ বা ইন্ডিয়া হলে ডাইরেক্ট ব্লক
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
        # ভিপিএন সঠিক থাকলে বটের মেমোরিতে ভেরিফাইড মার্ক করা হবে
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
                <br><br>
                <p style="color:#aaaaaa; font-size:14px; margin-top:20px;">After viewing the ad for 3 seconds, go back to Telegram and click <b>Download Video</b>.</p>
                
                <script>
                    setTimeout(function() {{
                        window.location.href = "{ad_link}";
                    }}, 3000);
                </script>
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
    """aiohttp ওয়েব সার্ভার রানার"""
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
        
        logger.info("⚙️ Settings Loaded Successfully from MongoDB.")

async def update_database_setting(key, value):
    await config_collection.update_one(
        {"_id": "global_settings"},
        {"$set": {key: value}},
        upsert=True
    )
    SYSTEM_CONFIG[key] = value

async def add_user_to_db(user_id):
    if not await users_collection.find_one({"_id": user_id}):
        await users_collection.insert_one({"_id": user_id})

async def send_log_message(text):
    if SYSTEM_CONFIG["log_channel"]:
        try:
            await app.send_message(
                chat_id=int(SYSTEM_CONFIG["log_channel"]),
                text=text
            )
        except Exception as e:
            logger.error(f"Failed to send log: {e}")

async def check_force_sub(client, user_id):
    if not SYSTEM_CONFIG["force_sub"] or not SYSTEM_CONFIG["public_channel"]:
        return True 
    try:
        member = await client.get_chat_member(int(SYSTEM_CONFIG["public_channel"]), user_id)
        # 🔴 Pyrogram V2 এর জন্য Enum ব্যবহার করা হলো
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
        
    if SYSTEM_CONFIG["shortener_list"]:
        shortener = random.choice(SYSTEM_CONFIG["shortener_list"])
        domain = shortener.get("domain")
        key = shortener.get("api")
    elif SYSTEM_CONFIG["shortener_domain"] and SYSTEM_CONFIG["shortener_key"]:
        domain = SYSTEM_CONFIG["shortener_domain"]
        key = SYSTEM_CONFIG["shortener_key"]
    else:
        return long_url

    try:
        api_url = f"https://{domain}/api?api={key}&url={long_url}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if "shortenedUrl" in data:
                        return data["shortenedUrl"]
    except Exception as e:
        logger.error(f"Shortener API Error: {e}")
    
    return long_url

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
        
        if len(frames) == 4:
            border_v = np.ones((target_h, 10, 3), dtype=np.uint8) * 255 
            top_row = np.hstack((frames[0], border_v, frames[1]))
            bottom_row = np.hstack((frames[2], border_v, frames[3]))
            border_h = np.ones((10, top_row.shape[1], 3), dtype=np.uint8) * 255
            collage = np.vstack((top_row, border_h, bottom_row))
        elif len(frames) >= 2:
            collage = np.hstack((frames[0], frames[1]))
        elif len(frames) == 1:
            collage = frames[0]
        else:
            return None

        cv2.imwrite(thumbnail_path, collage,[int(cv2.IMWRITE_JPEG_QUALITY), 95])
        
        del frames
        del collage
        gc.collect()
        
        return thumbnail_path

    except Exception as e:
        logger.error(f"Collage Generation Error: {e}")
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
                
                buttons = InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Channel to Watch", url=invite.invite_link)],[InlineKeyboardButton("🔄 Refresh / Try Again", url=f"https://t.me/{client.me.username}?start={param}")]
                ])
                return await message.reply(
                    "⚠️ **Access Denied!**\n\n"
                    "You must join our official channel to access this video.",
                    reply_markup=buttons
                )
            except Exception as e:
                logger.error(f"Invite Link Error: {e}")

    if len(message.command) > 1:
        user_id = message.from_user.id
        now = time.time()
        if user_id in user_last_request and now - user_last_request[user_id] < 5:
            return await message.reply("🚫 **Wait!** Please don't spam. Wait 5 seconds between requests.")
        user_last_request[user_id] = now
        
        asyncio.create_task(process_user_delivery(client, message))
        return
    
    if message.from_user.id == ADMIN_ID:
        admin_menu = (
            "👑 **Ultimate Admin Panel (v8.0 - Masterpiece)**\n\n"
            "📡 **Channel Setup:**\n"
            "`/setsource` & `/setpublic` & `/setlog`\n\n"
            "⚙️ **System Config:**\n"
            "`/setinterval 30` - Post Delay\n"
            "`/autodelete 60` - Auto Delete\n"
            "`/settutorial link` - Set Tutorial\n"
            "`/protect on/off` - Content Protection\n\n"
            "🔗 **Shortener Toggle:**\n"
            "`/shortener on` or `off` (Turn URL Shortener ON/OFF)\n"
            "`/setshortener domain.com api_key`\n\n"
            "🛡 **VPN & Multi-Ad Link System:**\n"
            "`/setvpn on` or `off` (Force VPN ON/OFF)\n"
            "`/addadlink link1 link2` (Add Multiple Links)\n"
            "`/adlinks` (View All Links)\n"
            "`/clearadlinks` (Delete All Links)\n\n"
            "🛠 **Smart Controls:**\n"
            "`/admin` - Visual Dashboard\n"
            "`/broadcast` - Send to All\n"
            "`/stats` - Stats / `/clearqueue` - Clear Queue"
        )
        await message.reply(admin_menu)
    else:
        await message.reply(
            "👋 **Hello! Welcome to AutoBot.**\n\n"
            "Search for videos or join our channel to get latest updates.\n"
            "Use `/search movie_name` to find videos."
        )

@app.on_message(filters.command("admin") & filters.user(ADMIN_ID))
async def admin_dashboard_handler(client, message):
    buttons =[[
            InlineKeyboardButton("📊 System Stats", callback_data="stats_live"),
            InlineKeyboardButton("⚙️ Quick Settings", callback_data="quick_settings")
        ],[
            InlineKeyboardButton("📡 Channels Info", callback_data="channel_info"),
            InlineKeyboardButton("🗑 Clear All Queue", callback_data="confirm_clear")
        ],[
            InlineKeyboardButton("🔙 Close", callback_data="close_admin")
        ]
    ]
    await message.reply("🎮 **Enterprise Smart Dashboard**", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_message(filters.command("setsource") & filters.user(ADMIN_ID))
async def set_source_channel(client, message):
    try:
        if len(message.command) < 2: return await message.reply("❌ Usage: `/setsource -100xxxx`")
        channel_id = int(message.command[1])
        await update_database_setting("source_channel", channel_id)
        await message.reply(f"✅ **Source Channel Set:** `{channel_id}`")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@app.on_message(filters.command("setpublic") & filters.user(ADMIN_ID))
async def set_public_channel(client, message):
    try:
        if len(message.command) < 2: return await message.reply("❌ Usage: `/setpublic -100xxxx`")
        channel_id = int(message.command[1])
        await update_database_setting("public_channel", channel_id)
        await message.reply(f"✅ **Public Channel Set:** `{channel_id}`")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@app.on_message(filters.command("setlog") & filters.user(ADMIN_ID))
async def set_log_channel(client, message):
    try:
        if len(message.command) < 2: return await message.reply("❌ Usage: `/setlog -100xxxx`")
        channel_id = int(message.command[1])
        await update_database_setting("log_channel", channel_id)
        await message.reply(f"✅ **Log Channel Set:** `{channel_id}`")
        await send_log_message("✅ **Log Channel Connected Successfully!**")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@app.on_message(filters.command("setinterval") & filters.user(ADMIN_ID))
async def set_post_interval(client, message):
    try:
        seconds = int(message.command[1])
        await update_database_setting("post_interval", seconds)
        await message.reply(f"⏱ **Interval Updated:** `{seconds} seconds`")
    except: 
        await message.reply("❌ Use number only.")

@app.on_message(filters.command("autodelete") & filters.user(ADMIN_ID))
async def set_auto_delete(client, message):
    try:
        seconds = int(message.command[1])
        await update_database_setting("auto_delete_time", seconds)
        await message.reply(f"⏳ **Auto Delete:** `{seconds} seconds`")
    except: 
        await message.reply("❌ Use number only.")

@app.on_message(filters.command("settutorial") & filters.user(ADMIN_ID))
async def set_tutorial_link(client, message):
    try:
        if len(message.command) < 2: return await message.reply("❌ Usage: `/settutorial https://link...`")
        link = message.command[1]
        await update_database_setting("tutorial_link", link)
        await message.reply(f"✅ **Tutorial Link Set:**\n`{link}`\n\n(It will now appear as 'ℹ️ How to Download' button on posts)")
    except: 
        await message.reply("❌ Error setting link.")

@app.on_message(filters.command("protect") & filters.user(ADMIN_ID))
async def set_content_protection(client, message):
    try:
        state = message.command[1].lower() == "on"
        await update_database_setting("protect_content", state)
        await message.reply(f"🛡 **Protection:** `{'ON' if state else 'OFF'}`")
    except: 
        await message.reply("❌ Usage: `/protect on` or `off`")

@app.on_message(filters.command("shortener") & filters.user(ADMIN_ID))
async def toggle_shortener(client, message):
    try:
        state = message.command[1].lower() == "on"
        await update_database_setting("shortener_active", state)
        await message.reply(f"🔗 **Shortener System:** `{'ON 🟢' if state else 'OFF 🔴'}`")
    except:
        await message.reply("❌ Usage: `/shortener on` or `/shortener off`")

@app.on_message(filters.command("setshortener") & filters.user(ADMIN_ID))
async def set_shortener_config(client, message):
    try:
        if len(message.command) < 3: 
            return await message.reply("❌ Usage: `/setshortener domain api_key`")
        await update_database_setting("shortener_domain", message.command[1])
        await update_database_setting("shortener_key", message.command[2])
        await message.reply(f"🔗 **Shortener Configured:** `{message.command[1]}`")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@app.on_message(filters.command("setvpn") & filters.user(ADMIN_ID))
async def set_vpn_enforcement(client, message):
    try:
        state = message.command[1].lower() == "on"
        await update_database_setting("vpn_enforce", state)
        await message.reply(f"🛡 **VPN & Ad Link Enforcement:** `{'ON 🟢' if state else 'OFF 🔴'}`")
    except: 
        await message.reply("❌ Usage: `/setvpn on` or `/setvpn off`")

@app.on_message(filters.command("addadlink") & filters.user(ADMIN_ID))
async def add_ad_link(client, message):
    try:
        if len(message.command) < 2: 
            return await message.reply("❌ Usage: `/addadlink https://link1.com https://link2.com ...`")
        
        # স্পেস দিয়ে যতগুলো লিংক দিবে সব একসাথে নিবে
        new_links = message.command[1:]
        links = SYSTEM_CONFIG["direct_ad_links"]
        added_count = 0
        
        for link in new_links:
            if link not in links:
                links.append(link)
                added_count += 1
                
        if added_count > 0:
            await update_database_setting("direct_ad_links", links)
            
        await message.reply(f"✅ **{added_count} Ad Links Added!**\nTotal Links Active: `{len(links)}`")
    except Exception as e:
        await message.reply(f"❌ Error: {e}")

@app.on_message(filters.command("adlinks") & filters.user(ADMIN_ID))
async def view_ad_links(client, message):
    links = SYSTEM_CONFIG["direct_ad_links"]
    if not links: 
        return await message.reply("📭 No ad links added. Use `/addadlink`")
    
    txt = "🔗 **Your Direct Ad Links:**\n\n"
    for i, l in enumerate(links, 1):
        txt += f"{i}. `{l}`\n"
    await message.reply(txt)

@app.on_message(filters.command("clearadlinks") & filters.user(ADMIN_ID))
async def clear_ad_links(client, message):
    await update_database_setting("direct_ad_links",[])
    await message.reply("🗑 **All Ad Links Cleared!**")

@app.on_message(filters.command("stats") & filters.user(ADMIN_ID))
async def show_stats(client, message):
    users = await users_collection.count_documents({})
    queue = await queue_collection.count_documents({})
    msg = (
        f"📊 **SYSTEM STATISTICS**\n\n"
        f"👥 **Total Users:** `{users}`\n"
        f"📥 **Queue Pending:** `{queue}` Videos\n"
        f"⏱ **Interval:** `{SYSTEM_CONFIG['post_interval']}s`\n"
        f"🔗 **Ad Links Active:** `{len(SYSTEM_CONFIG['direct_ad_links'])}`"
    )
    await message.reply(msg)

@app.on_message(filters.command("clearqueue") & filters.user(ADMIN_ID))
async def clear_queue_command(client, message):
    await queue_collection.delete_many({})
    await message.reply("🗑 **Queue Cleared!** All pending videos removed.")

@app.on_message(filters.command("broadcast") & filters.user(ADMIN_ID) & filters.reply)
async def broadcast_message(client, message):
    status_msg = await message.reply("📢 **Broadcast Started...**")
    all_users = users_collection.find({})
    
    total_users = await users_collection.count_documents({})
    success = 0
    blocked = 0
    deleted = 0
    
    async for user in all_users:
        try:
            await message.reply_to_message.copy(chat_id=user["_id"])
            success += 1
        except FloodWait as e:
            await asyncio.sleep(e.value)
            await message.reply_to_message.copy(chat_id=user["_id"])
            success += 1
        except UserIsBlocked:
            blocked += 1
            await users_collection.delete_one({"_id": user["_id"]})
        except InputUserDeactivated:
            deleted += 1
            await users_collection.delete_one({"_id": user["_id"]})
        except: 
            pass
        
        if (success + blocked + deleted) % 20 == 0:
            done = success + blocked + deleted
            percentage = (done / total_users) * 100
            await status_msg.edit(f"📢 **Broadcasting...**\nProgress: {round(percentage, 2)}%\nSent: {success}")
        
    await status_msg.edit(
        f"✅ **Broadcast Completed!**\n\n"
        f"sent: `{success}`\n"
        f"blocked: `{blocked}`\n"
        f"deleted: `{deleted}`"
    )

@app.on_message(filters.command("search"))
async def search_handler(client, message):
    if len(message.command) < 2:
        return await message.reply("🔍 Usage: `/search movie_name`")
    
    query = message.text.split(None, 1)[1]
    results = await queue_collection.find({"caption": {"$regex": query, "$options": "i"}}).limit(5).to_list(None)
    
    if not results:
        return await message.reply("❌ No matches found in recent queue.")
    
    txt = "🔍 **Search Results Found:**\n\n"
    for res in results:
        txt += f"🎬 {res['caption'][:50]}... \n🔗 `/start {res['msg_id']}`\n\n"
    await message.reply(txt)

@app.on_message(filters.command("history"))
async def history_handler(client, message):
    data = await history_collection.find_one({"_id": message.from_user.id})
    if not data or "history" not in data:
        return await message.reply("📭 You haven't requested any videos yet.")
    
    txt = "⏳ **Your Last Requested Videos:**\n\n"
    for item in reversed(data["history"]):
        txt += f"✅ {item['title']}\n"
    await message.reply(txt)

# ====================================================================
#              🔥 কলব্যাক হ্যান্ডলার (অ্যাডমিন + ভিপিএন চেক) 🔥
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
        
        # ইউজারের স্ট্যাটাস চেক করা হচ্ছে
        status_data = user_ad_status.get(user_id)
        
        if status_data and status_data["video_id"] == video_id:
            if status_data.get("status") == "verified":
                await query.answer("✅ Verification Successful! Sending video...", show_alert=False)
                await query.message.delete()
                
                # 🔴 ভিডিও দেওয়ার পর স্ট্যাটাস ডিলিট করে দেওয়া হলো, যাতে পরের ভিডিওর জন্য আবার ভিপিএন ও অ্যাড দেখতে হয়!
                del user_ad_status[user_id]
                
                await process_user_delivery(client, query.message, is_callback=True, target_msg_id=video_id, target_user_id=user_id)
            else:
                await query.answer(
                    "⚠️ Verification Failed!\n\n"
                    "১. আপনি 'Verify VPN' লিংকে ক্লিক করে ব্রাউজারে যাননি।\n"
                    "২. অথবা আপনার ভিপিএন ঠিকমতো কাজ করছে না (লোকেশন বাংলাদেশ দেখাচ্ছে)।\n\n"
                    "অনুগ্রহ করে লিংকে ক্লিক করে ব্রাউজারে অ্যাড পেজটি ওপেন করুন, তারপর এখানে এসে ক্লিক করুন।", 
                    show_alert=True
                )
        else:
            await query.answer("❌ Session expired! Please request the video link again using the bot.", show_alert=True)

# ====================================================================
#              ৬. ইউজার ভিডিও ডেলিভারি (Strict VPN Per Video)
# ====================================================================

async def process_user_delivery(client, message, is_callback=False, target_msg_id=None, target_user_id=None):
    try:
        msg_id = target_msg_id if is_callback else int(message.command[1])
        user_id = target_user_id if is_callback else message.from_user.id
        chat_id = user_id if is_callback else message.chat.id
        
        if not SYSTEM_CONFIG["source_channel"]:
            return await client.send_message(chat_id, "❌ **Bot Maintenance Mode.** (Source not set)")
        
        # ==========================================
        # 🔥 ১০০% রিয়েল ভিপিএন + ডাইরেক্ট অ্যাড লিংক চেকিং 🔥
        # ==========================================
        if SYSTEM_CONFIG["vpn_enforce"] and not is_callback:
            
            # URL এর শেষের অতিরিক্ত স্লাশ (/) রিমুভ করে সঠিক লিংক তৈরি করবে
            base_url = YOUR_SERVER_URL.rstrip('/')
            verify_link = f"{base_url}/verify?user_id={user_id}&vid={msg_id}"
            
            # ইউজারকে Pending স্ট্যাটাসে রাখা হলো
            user_ad_status[user_id] = {"video_id": msg_id, "status": "pending", "time": time.time()}
            
            vpn_text = (
                "🛑 **REGION BLOCKED! VPN REQUIRED!** 🛑\n\n"
                "⚠️ বাংলাদেশ (🇧🇩) এবং ইন্ডিয়া (🇮🇳) থেকে এই ভিডিওটি ওপেন করা সম্পূর্ণ ব্লক করা হয়েছে!\n\n"
                "ভিডিওটি দেখতে চাইলে আপনাকে অবশ্যই নিচের নিয়ম মানতে হবে:\n\n"
                "🇺🇸 **স্টেপ ১:** আপনার ফোনে থাকা যেকোনো ভিপিএন ওপেন করে **USA বা UK** সার্ভার কানেক্ট করুন।\n"
                "🔗 **স্টেপ ২:** ভিপিএন কানেক্ট থাকা অবস্থায় নিচের **'🌐 1. Verify VPN & Watch Ad'** বাটনে ক্লিক করুন।\n"
                "✅ **স্টেপ ৩:** ব্রাউজারে IP ভেরিফাই হলে একটি অ্যাড পেজ আসবে। অ্যাডটি ২-৩ সেকেন্ড দেখে বটে ফিরে আসুন।\n"
                "📥 **স্টেপ ৪:** বটে ফিরে এসে **'✅ 2. Download Video'** বাটনে ক্লিক করুন।\n\n"
                "*(⚠️ ভিপিএন ছাড়া লিংকে ক্লিক করলে Access Denied দেখাবে এবং ভিডিও পাবেনভান না!)*"
            )
            
            buttons = InlineKeyboardMarkup([[InlineKeyboardButton("🌐 1. Verify VPN & Watch Ad", url=verify_link)],[InlineKeyboardButton("✅ 2. Download Video", callback_data=f"get_vid_{msg_id}")],[InlineKeyboardButton("🛡️ Download Free VPN", url="https://play.google.com/store/apps/details?id=com.fast.free.unblock.secure.vpn")]
            ])
            
            if hasattr(message, "reply"): 
                return await message.reply(vpn_text, reply_markup=buttons)
            else: 
                return await client.send_message(chat_id, vpn_text, reply_markup=buttons)

        # ==========================================
        # অরিজিনাল ভিডিও ডেলিভারি লজিক
        # ==========================================
        status_msg = await client.send_message(chat_id, "🔄 **Processing your request...**")
        
        source_msg = await client.get_messages(int(SYSTEM_CONFIG["source_channel"]), msg_id)
        
        if not source_msg or (not source_msg.video and not source_msg.document):
            return await status_msg.edit("❌ **Error:** Video not found or deleted from server.")
        
        raw_title = source_msg.caption or "Exclusive Video"
        clean_user_title = re.sub(r'(https?://\S+|www\.\S+|t\.me/\S+|@\w+)', '', raw_title)
        clean_user_title = re.sub(r'\s+', ' ', clean_user_title).strip()
        
        if len(clean_user_title) < 2: 
            clean_user_title = "Exclusive Video"

        await update_view_count(msg_id)
        await add_user_history(user_id, msg_id, clean_user_title)

        sent_msg = await source_msg.copy(
            chat_id=chat_id,
            caption=f"✅ **Title:** `{clean_user_title}`\n\n❌ **Do not forward this message.**",
            protect_content=SYSTEM_CONFIG["protect_content"]
        )
        
        await status_msg.delete()
        
        if SYSTEM_CONFIG["auto_delete_time"] > 0:
            warning = await client.send_message(chat_id, f"⏳ **This video will be auto-deleted in {SYSTEM_CONFIG['auto_delete_time']} seconds!**")
            
            async def delete_after_delay(m1, m2, delay):
                await asyncio.sleep(delay)
                try: 
                    await m1.delete()
                    await m2.delete()
                except: 
                    pass
            
            asyncio.create_task(delete_after_delay(sent_msg, warning, SYSTEM_CONFIG["auto_delete_time"]))
            
    except Exception as e:
        logger.error(f"Delivery Error: {e}")
        try: 
            await client.send_message(chat_id, "❌ An error occurred. Please contact admin.")
        except: 
            pass
    finally:
        gc.collect() 

# ====================================================================
#                       ৭. সোর্স চ্যানেল মনিটরিং
# ====================================================================

@app.on_message(filters.channel & (filters.video | filters.document))
async def source_channel_listener(client, message):
    if SYSTEM_CONFIG["source_channel"] and message.chat.id == int(SYSTEM_CONFIG["source_channel"]):
        
        is_video = message.video or (message.document and message.document.mime_type and "video" in message.document.mime_type)
        
        if is_video:
            exists = await queue_collection.find_one({"msg_id": message.id})
            if not exists:
                await queue_collection.insert_one({
                    "msg_id": message.id,
                    "caption": message.caption or "Exclusive Video",
                    "date": message.date
                })
                logger.info(f"📥 New Video Added to Queue: ID {message.id}")
                await send_log_message(f"📥 **New Video Queued!**\nID: `{message.id}`")

# ====================================================================
#              ৮. মেইন প্রসেসিং ইঞ্জিন
# ====================================================================

async def processing_engine():
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
        
    logger.info("🚀 Processing Engine Started Successfully...")
    
    while True:
        try:
            if not SYSTEM_CONFIG["source_channel"] or not SYSTEM_CONFIG["public_channel"]:
                await asyncio.sleep(20)
                continue
            
            task = await queue_collection.find_one(sort=[("date", 1)])
            
            if task:
                msg_id = task["msg_id"]
                logger.info(f"🔨 Processing Task ID: {msg_id}")
                
                try:
                    source_msg = await app.get_messages(int(SYSTEM_CONFIG["source_channel"]), msg_id)
                    
                    if not source_msg:
                        logger.error("❌ Message deleted from source channel.")
                        await queue_collection.delete_one({"_id": task["_id"]})
                        continue
                    
                    file = source_msg.video or source_msg.document
                    size_readable = get_readable_size(file.file_size)
                    
                    quality_label = "HD 720p"
                    if source_msg.video:
                        h = source_msg.video.height
                        if h >= 2160: quality_label = "4K Ultra HD"
                        elif h >= 1080: quality_label = "Full HD 1080p"
                        elif h >= 720: quality_label = "HD 720p"
                        else: quality_label = "SD Quality"

                    video_path = f"downloads/video_{msg_id}.mp4"
                    logger.info("⬇️ Downloading video for thumbnail generation...")
                    await app.download_media(source_msg, file_name=video_path)
                    
                    thumb_path = await asyncio.to_thread(generate_collage_thumbnail, video_path, msg_id)
                    
                    bot_username = (await app.get_me()).username
                    deep_link = f"https://t.me/{bot_username}?start={msg_id}"
                    
                    # 🔴 Shortener Switch Logic works here 🔴
                    final_link = await shorten_url_api(deep_link)
                    
                    views_count = await get_views(msg_id)
                    new_spicy_title = random.choice(ATTRACTIVE_TITLES)
                    
                    final_caption = SYSTEM_CONFIG["caption_template"].format(
                        title=new_spicy_title, 
                        quality=quality_label, 
                        size=size_readable, 
                        views=views_count
                    )
                    
                    buttons_list = [[InlineKeyboardButton("📥 DOWNLOAD / WATCH VIDEO 📥", url=final_link)]
                    ]
                    
                    # 🔴 টিউটোরিয়াল বাটন যুক্ত করা হচ্ছে
                    if SYSTEM_CONFIG["tutorial_link"]:
                        buttons_list.append([InlineKeyboardButton("ℹ️ How to Download", url=SYSTEM_CONFIG["tutorial_link"])]
                        )
                    
                    buttons = InlineKeyboardMarkup(buttons_list)
                    dest_chat = int(SYSTEM_CONFIG["public_channel"])
                    
                    if thumb_path and os.path.exists(thumb_path):
                        await app.send_photo(chat_id=dest_chat, photo=thumb_path, caption=final_caption, reply_markup=buttons)
                        log_status = "✅ Posted with Smart Thumbnail"
                    else:
                        await app.send_message(chat_id=dest_chat, text=final_caption, reply_markup=buttons)
                        log_status = "⚠️ Posted without Thumbnail"
                    
                    logger.info(f"✅ Success: {msg_id} | Title: {new_spicy_title}")
                    await send_log_message(f"{log_status}\n🆔 Msg ID: `{msg_id}`\n🏷 Title: `{new_spicy_title}`")
                    
                except Exception as e:
                    logger.error(f"❌ Processing Error: {e}")
                
                # ক্লিনআপ
                await queue_collection.delete_one({"_id": task["_id"]})
                try:
                    if os.path.exists(video_path): 
                        os.remove(video_path)
                    if thumb_path and os.path.exists(thumb_path): 
                        os.remove(thumb_path)
                except: 
                    pass
                gc.collect()
            
            wait_time = SYSTEM_CONFIG.get("post_interval", 30)
            await asyncio.sleep(wait_time)
            
        except Exception as e:
            logger.critical(f"🛑 Critical Loop Error: {e}")
            await asyncio.sleep(10)

# ====================================================================
#                       ৯. মেইন এক্সিকিউশন
# ====================================================================

async def main():
    # 🔴 ডাটাবেসকে লুপের ভেতর ইনিশিয়ালাইজ করা হলো (বট হ্যাং হওয়ার মূল সমাধান)
    global mongo_client, db, queue_collection, config_collection, users_collection, history_collection, stats_collection
    
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    db = mongo_client["Enterprise_Bot_DB"]
    queue_collection = db["video_queue"]    
    config_collection = db["bot_settings"]  
    users_collection = db["users_list"]     
    history_collection = db["user_history"] 
    stats_collection = db["video_stats"] 

    asyncio.create_task(start_web_server())
    await app.start()
    await load_database_settings()
    asyncio.create_task(processing_engine())
    
    logger.info("🤖 AutoBot Enterprise SMART VERSION is now FULLY OPERATIONAL...")
    await idle()
    await app.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
