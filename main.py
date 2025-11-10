# -*- coding: utf-8 -*-
import telebot
from telebot import types
import time
import json
import os
import uuid
from collections import defaultdict
import pymongo
import certifi # SSL/TLS certificate-er jonno

# --- Configuration ---
TOKEN = '8426608876:AAEH3RsgifQP9buKAK0uQAs8kBR6MIMygNY'
ADMIN_ID = '8118743556'
ADMIN_USERNAME = 'RAIM_AHMED'
ADMIN_BKASH_NO = '01774049543'
ADMIN_NAGAD_NO = '01774049543'
BOT_USERNAME = "Digital_Easy_Partner_BOT"

# --- NEW: MongoDB Connection (Persistent Data) ---
# Apnar connection string sothik-bhabe deya hoyeche
CONNECTION_STRING = "mongodb+srv://Raimbd:Raimbd09%40%23@cluster0.xigqxgx.mongodb.net/?retryWrites=true&w=majority"

try:
    # certifi.where() bebohar kora khub joruri
    client = pymongo.MongoClient(CONNECTION_STRING, tlsCAFile=certifi.where())
    db = client['digitalPartnerDB'] # Database-er naam
    users_db = db['users']         # User data-r jonno
    orders_db = db['orders']       # Order data-r jonno
    tasks_db = db['gmail_tasks']   # Gmail task-er jonno
    stock_db = db['stock']         # Stock management-er jonno
    
    print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print(f"❌❌❌ MongoDB Connection Error: {e} ❌❌❌")
    print("Doya kore Connection String-ti check korun.")
    exit() # Database chhara bot cholbe na

# Note: The TeleBot instance should be created after defining the token
bot = telebot.TeleBot(TOKEN)

# --- Service Prices ---
USA_GMAIL_PRICE = 15
BD_GMAIL_PRICE = 10
PLAY_POINT_PRICE = 20
VPN_PRICE = 40
YT_1M_PRICE = 25
YT_1Y_PRICE = 150
CRUNCHYROLL_PRICE = 25
VEO_1M_PRICE = 20
VEO_12M_PRICE = 50

# --- Withdrawal Configuration ---
MIN_WITHDRAW = 30
WITHDRAW_FEE = 5
WITHDRAW_FEE_THRESHOLD = 50

# --- Global Data Structures (In-Memory Session Data) ---
# Restart hole eishob data clear hoye jabe (ebong ota e bhalo)
pending_gmails = defaultdict(dict) # Admin approval queue
admin_sessions = {} # Admin-er chola kajer data
active_gmail_tasks = {} # Kon user kon task niyeche tar temporary data

# --- NEW: Stock System Data (Default) ---
# Ekhon database-e save hobe
DEFAULT_STOCK = {
    "_id": "service_stock", # Stock document-er fixed ID
    "gmail_usa": -1,
    "gmail_bd": -1,
    "play_point": -1,
    "vpn_nord": -1,
    "vpn_express": -1,
    "vpn_hma": -1,
    "vpn_pia": -1,
    "vpn_ipvanis": -1,
    "yt_1_month": -1,
    "yt_1_year": -1,
    "crunchyroll_7_day": -1,
    "veo_1_month": -1,
    "veo_12_month": -1
}

# --- ☢️ Data Persistence Functions (load_data/save_data) AR NEI ☢️ ---
# Shob data ekhon database-e direct save hobe


# --- NEW: Database Helper Functions (Data Save/Load) ---

def get_user(user_id):
    """Database theke user-er data ber kore, na thakle notun user toiri kore."""
    user_id_str = str(user_id)
    user_data = users_db.find_one({"_id": user_id_str})
    
    if user_data:
        return user_data
    else:
        # User na thakle, notun user toiri kore database-e save korun
        new_user = {
            "_id": user_id_str,
            "username": "", # /start e update hobe
            "balance": 0,
            "hold": 0,
            "referral_count": 0,
            "referred_users": [],
            "joined_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "is_blocked": False,
            # Session data (jemon order korar shomoy)
            "session": {} 
        }
        try:
            users_db.insert_one(new_user)
            print(f"New user created: {user_id_str}")
            return new_user
        except Exception as e:
            print(f"Error creating new user: {e}")
            return None # Error handle

def update_user(user_id, update_data):
    """User-er data database-e update kore (e.g., $set, $inc, $push)."""
    try:
        users_db.update_one({"_id": str(user_id)}, update_data)
    except Exception as e:
        print(f"Error updating user {user_id}: {e}")

def get_session_data(user_id, key):
    """User-er session theke data ber kore."""
    user = get_user(user_id)
    return user.get("session", {}).get(key)

def set_session_data(user_id, key, value):
    """User-er session-e data save kore."""
    update_user(user_id, {"$set": {f"session.{key}": value}})

def clear_session_data(user_id):
    """User-er shob session data porishkar kore."""
    update_user(user_id, {"$set": {"session": {}}})

def get_stock():
    """Database theke stock-er obostha ber kore."""
    stock_data = stock_db.find_one({"_id": "service_stock"})
    if not stock_data:
        # Stock na thakle, default stock toiri kore
        try:
            stock_db.insert_one(DEFAULT_STOCK)
            return DEFAULT_STOCK
        except pymongo.errors.DuplicateKeyError:
            # Race condition hole, abar find korun
            return stock_db.find_one({"_id": "service_stock"})
    return stock_data

def update_stock(key, value):
    """Ekti nirdishto stock-er value update kore."""
    stock_db.update_one({"_id": "service_stock"}, {"$set": {key: value}})

def get_available_tasks():
    """Database theke shob 'available' task-er list dey."""
    return list(tasks_db.find({"status": "available"}))

def add_new_task(task_data):
    """Database-e notun task jog kore."""
    task_data['status'] = 'available'
    # Check if task already exists
    if tasks_db.find_one({"email": task_data['email']}):
        return False # Task already exists
    tasks_db.insert_one(task_data)
    return True

def assign_task_to_user(user_id, task):
    """Ekti task-ke 'active' hishebe mark kore."""
    tasks_db.update_one({"_id": task['_id']}, {"$set": {"status": "active", "user_id": str(user_id)}})
    active_gmail_tasks[str(user_id)] = {
        "task": task,
        "timestamp": time.time()
    }

def return_task_to_pool(task):
    """Task-ke 'available' hishebe database-e ferot pathay."""
    tasks_db.update_one({"_id": task['_id']}, {"$set": {"status": "available", "user_id": None}})
    # Active task list thekeo remove kore
    user_id = str(task.get('user_id'))
    if user_id in active_gmail_tasks:
        del active_gmail_tasks[user_id]

def remove_task_by_email(email):
    """Email diye 'available' task delete kore."""
    result = tasks_db.delete_one({"email": email, "status": "available"})
    return result.deleted_count > 0

def create_order(order_data):
    """Order-er data database-e save kore."""
    try:
        orders_db.insert_one(order_data)
    except Exception as e:
        print(f"Error creating order: {e}")

def get_order(order_id):
    """Order ID diye order-er data ber kore."""
    return orders_db.find_one({"_id": order_id})

def update_order_status(order_id, status):
    """Order-er status update kore."""
    orders_db.update_one({"_id": order_id}, {"$set": {"status": status}})

def get_user_history(user_id, history_type):
    """User-er nirdishto history database theke ber kore."""
    user_id_str = str(user_id)
    query = {"user_id": user_id_str}
    
    if history_type == "Gmail Sell":
        query["service"] = "Gmail Sell (Task)"
    elif history_type == "Withdrawal":
        query["service"] = "Withdrawal"
    elif history_type == "Service Buy":
        query["service"] = {"$nin": ["Gmail Sell (Task)", "Withdrawal"]}
    
    # Sort by timestamp descending (newest first) and limit to 20
    return list(orders_db.find(query).sort("timestamp", -1).limit(20))

def get_all_users_cursor():
    """Shob user-er data efficient-bhabe ber korar jonno cursor dey (broadcast-er jonno)."""
    return users_db.find({"is_blocked": {"$ne": True}}) # Blocked chara

def get_all_users_list():
    """Shob user-er data list hishebe dey (admin download-er jonno)."""
    return list(users_db.find({}))

def get_bot_stats():
    """Admin panel-er jonno statistics toiri kore."""
    total_users = users_db.count_documents({})
    
    # Aggregation diye total balance ber kora
    pipeline = [
        {"$group": {
            "_id": None,
            "total_balance": {"$sum": "$balance"},
            "total_hold": {"$sum": "$hold"},
            "total_referrals": {"$sum": "$referral_count"}
        }}
    ]
    stats = list(users_db.aggregate(pipeline))
    
    if stats:
        total_balance = stats[0].get('total_balance', 0)
        total_hold = stats[0].get('total_hold', 0)
        total_ref_earnings = stats[0].get('total_referrals', 0) * 2
    else:
        total_balance = 0
        total_hold = 0
        total_ref_earnings = 0

    total_pending_gmails = sum(len(sub["gmails"]) for subs in pending_gmails.values() for sub in subs.values() if subs)
    total_available_tasks = tasks_db.count_documents({"status": "available"})
    total_active_tasks = len(active_gmail_tasks) # In-memory thekei thik ache

    return {
        "total_users": total_users,
        "total_balance": total_balance,
        "total_hold": total_hold,
        "total_ref_earnings": total_ref_earnings,
        "total_pending_gmails": total_pending_gmails,
        "total_available_tasks": total_available_tasks,
        "total_active_tasks": total_active_tasks
    }

def release_stuck_tasks():
    """Bot restart hole, 'active' task-guloke 'available' kore dey."""
    try:
        result = tasks_db.update_many(
            {"status": "active"},
            {"$set": {"status": "available", "user_id": None}}
        )
        if result.modified_count > 0:
            print(f"Released {result.modified_count} stuck tasks back to pool.")
    except Exception as e:
        print(f"Error releasing stuck tasks: {e}")

# --- Bot Initialization ---
# ☢️ load_data() function-ti ekhon ar nei
release_stuck_tasks() # Bot chalur shomoy stuck task release korun
# --- End of Data Persistence Functions ---

LOGO = """
╔═════════════════════════╗
║     🛒 Digital Easy Partner    ║
╚═════════════════════════╝

🌟আপনার ডিজিটাল সার্ভিসের বিশ্বস্ত পার্টনার🌟
"""

# --- Utility Markups ---
def back_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True); markup.add("↩️ মেনুতে ফিরে যান"); return markup

def payment_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💰 Balance (Pay Now)")
    markup.add("📲 Bkash", "📲 Nagad")
    markup.add("↩️ মেনুতে ফিরে যান")
    return markup
    
def withdraw_method_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📲 Bkash", "📲 Nagad", "🪙 Binance", "🅿️ Payer", "↩️ মেনুতে ফিরে যান")
    return markup
    
# --- HOME MENU FUNCTION (MODIFIED) ---
def home_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    row1 = ["📥 Gmail Sell", "💵 Withdraw", "💳 Balance", "👥 Refer"]
    row2 = ["🛒 Buy Services", "📊 History"]
    row3 = ["🆘 Support"]
    markup.add(*row1); markup.add(*row2); markup.add(*row3)
    
    # Database theke user-er data neya hocche
    user = get_user(chat_id)
    user_info = ""
    if user:
        user_info = f"\n👤 User: @{user.get('username', 'NoUsername')}\n💰 Balance: {user.get('balance', 0)} TK"
    
    welcome_msg = f"{LOGO}\n{user_info}\n\n🎯 নিচের মেনু থেকে সেবা নির্বাচন করুন:"
    bot.send_message(chat_id, welcome_msg, reply_markup=markup) 

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    
    # 1. Database theke user-er data ana hocche
    user = get_user(user_id)
    if not user:
        bot.send_message(message.chat.id, "❌ Ekti error hoyeche. Doya kore abar /start korun.")
        return

    if user.get("is_blocked"):
        bot.send_message(message.chat.id, f"❌ আপনাকে এই বট ব্যবহার থেকে ব্লক করা হয়েছে। Admin এর সাথে যোগাযোগ করুন: @{ADMIN_USERNAME}")
        return
        
    bot.send_message(message.chat.id, LOGO)
    time.sleep(0.5)

    is_new_user = user.get("username") == "" # Check korar notun system
    referral_link_used = len(message.text.split()) > 1

    # 2. User-er username update kora hocche
    username = message.from_user.username
    if user.get("username") != username:
        update_user(user_id, {"$set": {"username": username}})
        user["username"] = username # Local copy update

    if is_new_user:
        if referral_link_used:
            referrer_id_str = message.text.split()[1]
            try:
                # 3. Referrer-ke database theke khuje ber kora hocche
                referrer_user = get_user(referrer_id_str)
                if referrer_user and referrer_id_str != user_id:
                    if user_id not in referrer_user.get("referred_users", []):
                        # 4. Referrer-er balance database-e update kora hocche
                        update_user(referrer_id_str, {
                            "$inc": {"balance": 2, "referral_count": 1},
                            "$push": {"referred_users": user_id}
                        })
                        bot.send_message(referrer_id_str, f"🎉 আপনি ২ টাকা পেয়েছেন রেফার বোনাস হিসেবে! নতুন ইউজার: @{username or 'NoUsername'}")
            except Exception as e:
                print(f"Referral processing error: {e}")
        
        # ☢️ save_data() ar nei

    elif not is_new_user and referral_link_used:
        bot.send_message(message.chat.id, "⚠️ আপনি ইতিমধ্যে একজন রেজিস্টার্ড ইউজার। পুনরায় রেফারেল লিঙ্ক ব্যবহার করা যাবে না।")

    welcome_msg = f"""
✨ স্বাগতম {message.from_user.first_name}!

ডিজিটাল Sohoj Buy Sell BD বটে আপনাকে স্বাগতম! 🎉

🔹 Gmail তৈরি করে আয় করুন
🔹 Gmail বিক্রি/ক্রয়
🔹 Premium VPN সার্ভিস
🔹 YouTube Premium অ্যাকাউন্ট
🔹 Crunchyroll Premium
🔹 Google Veo 3
🔹 রেফার প্রোগ্রাম
🔹 Play Point Park On

💼 আপনার একাউন্ট ডিটেইলস:
💰 ব্যালেন্স: {user['balance']} টাকা
👥 রেফার্ড ইউজার: {user['referral_count']} জন

নিচের মেনু থেকে আপনার পছন্দের সেবা নির্বাচন করুন:
"""
    bot.send_message(message.chat.id, welcome_msg)
    time.sleep(1)
    home_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "↩️ মেনুতে ফিরে যান")
def back_to_home(message):
    bot.clear_step_handler(message)
    user_id = str(message.from_user.id)
    clear_session_data(user_id) # 5. Session data porishkar kora hocche
    
    if message.chat.id in admin_sessions:
        del admin_sessions[message.chat.id]
        
    home_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "⬅️ Buy Services Menu")
def back_to_services(message):
    bot.clear_step_handler(message)
    user_id = str(message.from_user.id)
    clear_session_data(user_id) # 5. Session data porishkar kora hocche
    buy_services_menu(message)


# --- Buy Services Submenu Handler ---
@bot.message_handler(func=lambda m: m.text == "🛒 Buy Services")
def buy_services_menu(message):
    user = get_user(message.from_user.id)
    if not user or user.get("is_blocked"): return
    
    options = """
🛒 আমাদের ক্রয় করার সেবাগুলো:

🔹 📥 Gmail Buy
🔹 🌐 Paid VPN Buy
🔹 🎥 YouTube Premium
🔹 🍿 Crunchyroll Premium (New)
🔹 🧠 Google Veo 3 (Gemin) (New)
🔹 🎁 Play Point Park On

💡 আপনার পছন্দের সেবা নির্বাচন করুন:
"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        "📥 Gmail Buy", 
        "🌐 Paid VPN Buy", 
        "🎥 YouTube Premium",
        "🍿 Crunchyroll Premium", # New
        "🧠 Google Veo 3 (Gemin)", # New
        "🎁 Play Point Park On",
        "↩️ মেনুতে ফিরে যান"
    ]

    markup.add(*buttons)
    
    bot.send_message(message.chat.id, options, reply_markup=markup)

# --- History Menu (REPLACES Check Price) ---
@bot.message_handler(func=lambda m: m.text == "📊 History")
def show_history_menu(message):
    bot.clear_step_handler(message)
    user = get_user(message.from_user.id)
    if not user or user.get("is_blocked"): return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add("📥 Gmail Sell History", "💵 Withdraw History", "🛒 Service Buy History")
    markup.add("↩️ মেনুতে ফিরে যান")
    
    bot.send_message(message.chat.id, "📊 অনুগ্রহ করে আপনার কাঙ্ক্ষিত হিস্টোরি নির্বাচন করুন:", reply_markup=markup)

# --- NEW: History Helper and Handlers (MODIFIED) ---
def format_history(history_list, title, max_items=20):
    if not history_list:
        return f"❌ আপনার কোনো {title} হিস্টোরি নেই।"
        
    # Database thekei sorted hoye ashe, tai extra sort dorkar nei
    
    message = f"📜 **{title} History (Last {max_items})**\n\n"
    
    for i, item in enumerate(history_list): # [:max_items] o dorkar nei, DB limit korei pathay
        timestamp = item.get("timestamp", 0)
        date = time.strftime('%d %b %Y, %I:%M %p', time.localtime(timestamp)) if timestamp else "N/A"
        status = item.get("status", "N/A").title()
        
        service = item.get("service")
        if service == "Gmail Sell (Task)":
            email = item.get("details", "N/A").split(':')[0]
            price = item.get("price", 0)
            message += f"{i+1}. **{email}**\n   - Status: {status}, Price: {price} TK\n   - Date: {date}\n\n"
        
        elif service == "Withdrawal":
            amount = item.get("amount", 0)
            method = item.get("method", "N/A")
            message += f"{i+1}. **{amount} TK via {method}**\n   - Status: {status}\n   - Date: {date}\n\n"

        else: # Buy History
            service_name = item.get("service", "N/A")
            type_info = item.get("type", "")
            price = item.get("price", 0)
            message += f"{i+1}. **{service_name} - {type_info}**\n   - Price: {price} TK, Status: {status}\n   - Date: {date}\n\n"
    
    return message

@bot.message_handler(func=lambda m: m.text == "📥 Gmail Sell History")
def show_gmail_sell_history(message):
    user = get_user(message.from_user.id)
    if not user or user.get("is_blocked"): return
    
    # 6. History database theke ana hocche
    user_history = get_user_history(user["_id"], "Gmail Sell")
    response = format_history(user_history, "Gmail Sell")
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💵 Withdraw History")
def show_withdraw_history(message):
    user = get_user(message.from_user.id)
    if not user or user.get("is_blocked"): return
    
    # 6. History database theke ana hocche
    user_history = get_user_history(user["_id"], "Withdrawal")
    response = format_history(user_history, "Withdrawal")
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🛒 Service Buy History")
def show_service_buy_history(message):
    user = get_user(message.from_user.id)
    if not user or user.get("is_blocked"): return
    
    # 6. History database theke ana hocche
    user_history = get_user_history(user["_id"], "Service Buy")
    response = format_history(user_history, "Service Buy")
    bot.send_message(message.chat.id, response, parse_mode="Markdown")
# --- END NEW History Handlers ---


# --- Play Point Park On Flow (MODIFIED for DB) ---
@bot.message_handler(func=lambda m: m.text == "🎁 Play Point Park On")
def play_point_menu(message):
    user = get_user(message.from_user.id)
    if not user or user.get("is_blocked"): return
    
    # Stock Check from DB
    current_stock = get_stock()
    if current_stock.get("play_point", -1) == 0:
        bot.send_message(message.chat.id, "❌ দুঃখিত, Play Point Park On পরিষেবাটি বর্তমানে স্টক আউট আছে।")
        return home_menu(message.chat.id)
        
    options = f"""
🌍 দেশ নির্বাচন করুন:
🇺🇸 USA
🇹🇼 Taiwan
🇬🇧 UK
🇰🇷 South Korean
🇯🇵 Japan (New)
💡 প্রতিটি Park On-এর জন্য {PLAY_POINT_PRICE} টাকা খরচ হবে
"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add("🇺🇸 USA", "🇹🇼 Taiwan", "🇬🇧 UK", "🇰🇷 South Korean", "🇯🇵 Japan", "⬅️ Buy Services Menu")
    msg = bot.send_message(message.chat.id, options, reply_markup=markup)
    bot.register_next_step_handler(msg, process_play_point_country)

def process_play_point_country(message):
    if message.text == "⬅️ Buy Services Menu":
        bot.clear_step_handler(message); return buy_services_menu(message)
    
    if message.text not in ["🇺🇸 USA", "🇹🇼 Taiwan", "🇬🇧 UK", "🇰🇷 South Korean", "🇯🇵 Japan"]:
        error_msg = "❌ অবৈধ দেশ। অনুগ্রহ করে বাটন থেকে নির্বাচন করুন:"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        markup.add("🇺🇸 USA", "🇹🇼 Taiwan", "🇬🇧 UK", "🇰🇷 South Korean", "🇯🇵 Japan", "⬅️ Buy Services Menu")
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=markup)
        bot.register_next_step_handler(msg, process_play_point_country); return
        
    country = message.text
    user_id = str(message.from_user.id)
    # 7. Session data database-e save kora hocche
    set_session_data(user_id, "play_point_country", country)
    
    quantity_msg = "🔢 কতগুলো Park On চান?\n💡 পরিমাণ লিখুন (সংখ্যা):"
    msg = bot.send_message(message.chat.id, quantity_msg, reply_markup=back_markup())
    bot.register_next_step_handler(msg, process_play_point_quantity)

def process_play_point_quantity(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    try:
        quantity = int(message.text)
        if quantity <= 0: raise ValueError
        user_id = str(message.from_user.id)
        total_price = quantity * PLAY_POINT_PRICE
        
        # 7. Session data database-e save kora hocche
        set_session_data(user_id, "play_point_quantity", quantity)
        set_session_data(user_id, "play_point_price", total_price)
        
        details_msg = f"💰 মোট মূল্য: {total_price} টাকা\n\nএখন আপনি যে Gmail/Password-গুলোতে Park On করতে চান সেগুলো একসাথে লিখুন:\n(প্রতি লাইনে একটি Gmail/Password)\n\nফরম্যাট:\nexample1@gmail.com/password1\nexample2@gmail.com/password2"
        msg = bot.send_message(message.chat.id, details_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, process_play_point_details)
    except ValueError:
        error_msg = "❌ অবৈধ সংখ্যা! শুধুমাত্র সংখ্যা লিখুন।\nআবার চেষ্টা করুন:"
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, process_play_point_quantity)

def process_play_point_details(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    user_id = str(message.from_user.id)
    
    # 8. Session data database theke ber kora hocche
    price = get_session_data(user_id, "play_point_price")
    country = get_session_data(user_id, "play_point_country")
    quantity = get_session_data(user_id, "play_point_quantity")
    
    if not price or not country or not quantity: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।"); return home_menu(message.chat.id)
    
    # 7. Session data database-e save kora hocche
    set_session_data(user_id, "play_point_details", message.text)
    
    order_summary = f"📝 অর্ডার সারাংশ:\n\n🌍 Country: {country}\n🔢 Quantity: {quantity} টি\n💰 মোট মূল্য: {price} TK\n\n💳 পেমেন্ট মাধ্যম নির্বাচন করুন:"
    bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
    bot.register_next_step_handler(message, process_play_point_payment)

def process_play_point_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    user_id = str(message.from_user.id)
    
    # 8. Session data database theke ber kora hocche
    price = get_session_data(user_id, "play_point_price")
    if not price: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন."); return home_menu(message.chat.id)
    
    user = get_user(user_id) # User-er balance check-er jonno
    
    if message.text == "💰 Balance (Pay Now)":
        balance = user.get("balance", 0)
        if balance < price:
            bot.send_message(message.chat.id, f"❌ আপনার ব্যালেন্স কম আছে।\n💰 আপনার ব্যালেন্স: {balance} TK\n🛒 প্রয়োজন: {price} TK\n📉 ঘাটতি: {price - balance} TK")
            msg = bot.send_message(message.chat.id, "অন্য একটি পেমেন্ট মাধ্যম নির্বাচন করুন:", reply_markup=payment_markup())
            bot.register_next_step_handler(msg, process_play_point_payment)
            return
        else:
            quantity = get_session_data(user_id, "play_point_quantity")
            new_balance = balance - price
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add("✅ Confirm", "❌ Cancel")
            confirm_msg = f"""
🔔 কনফার্মেশন:

🎁 Service: Play Point Park On
🔢 Quantity: {quantity} টি
💰 মূল্য: {price} TK (ব্যালেন্স থেকে)
💸 আপনার বর্তমান ব্যালেন্স: {balance} TK
💳 নতুন ব্যালেন্স হবে: {new_balance} TK

আপনি কি এই অর্ডারটি কনফার্ম করতে চান?
"""
            msg = bot.send_message(message.chat.id, confirm_msg, reply_markup=markup)
            bot.register_next_step_handler(msg, process_play_point_balance_confirm)
            return
    
    if message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"; msg = bot.send_message(message.chat.id, error_msg, reply_markup=payment_markup())
        bot.register_next_step_handler(msg, process_play_point_payment); return
    
    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    
    payment_instructions = f"💳 {method} এ টাকা পাঠান:\n\n📱 Number: {payment_number}\n💰 Amount: {price} TK\n📝 Reference: PPON{user_id}\n\n⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন\n\n📨 এখন আপনার Transaction ID লিখুন:"
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_play_point_order(m, method, price))

def process_play_point_balance_confirm(message):
    user_id = str(message.from_user.id)
    if message.text == "❌ Cancel":
        bot.send_message(user_id, "❌ অর্ডার বাতিল করা হয়েছে।")
        clear_session_data(user_id) # Session clear
        return home_menu(user_id)
        
    # 8. Session data database theke ber kora hocche
    price = get_session_data(user_id, "play_point_price")
    country = get_session_data(user_id, "play_point_country")
    quantity = get_session_data(user_id, "play_point_quantity")
    details = get_session_data(user_id, "play_point_details")

    if not price or not country or not quantity:
        bot.send_message(user_id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।")
        return home_menu(user_id)

    if message.text == "✅ Confirm":
        user = get_user(user_id)
        balance = user.get("balance", 0)

        if balance < price:
            bot.send_message(user_id, "❌ দুঃখিত, আপনার ব্যালেন্স অপর্যাপ্ত। অর্ডার বাতিল করা হয়েছে।")
            clear_session_data(user_id)
            return home_menu(user_id)
            
        # 9. Database-e balance update kora hocche
        update_user(user_id, {"$inc": {"balance": -price}})
        
        order_id = f"PPON{int(time.time())}{user_id}"
        # 10. Order database-e save kora hocche
        order_data = {
            "_id": order_id,
            "user_id": user_id, 
            "service": "Play Point Park On", 
            "country": country, 
            "quantity": quantity, 
            "details": details, 
            "price": price, 
            "method": "Balance",
            "txn_id": "N/A",
            "status": "pending",
            "timestamp": time.time()
        }
        create_order(order_data)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_pp_{order_id}"))
        
        admin_msg = f"🎁 নতুন Play Point Park On অর্ডার (Balance):\n\n📦 Order ID: {order_id}\n👤 User: @{user.get('username', 'N/A')}\n🆔 User ID: {user_id}\n🌍 Country: {country}\n🔢 Quantity: {quantity} টি\n💰 Amount: {price} TK\n💳 Method: Balance\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n📩 Gmail Details:\n{details}"
        bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
        
        user_confirmation = f"✅ আপনার অর্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n🎁 Service: Play Point Park On\n💰 Paid: {price} TK (via Balance)\n\nআপনার অর্ডারটি প্রসেস করা হচ্ছে।\nডেলিভারি সময়: ১-১২ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
        bot.send_message(message.chat.id, user_confirmation)
        
        clear_session_data(user_id) # Session clear
        home_menu(message.chat.id)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("✅ Confirm", "❌ Cancel")
        msg = bot.send_message(message.chat.id, "❌ অবৈধ ইনপুট। দয়া করে '✅ Confirm' অথবা '❌ Cancel' বাটন চাপুন।", reply_markup=markup)
        bot.register_next_step_handler(msg, process_play_point_balance_confirm)

def confirm_play_point_order(message, method, price):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    txn_id = message.text
    user_id = str(message.from_user.id)
    
    # 8. Session data database theke ber kora hocche
    country = get_session_data(user_id, "play_point_country")
    quantity = get_session_data(user_id, "play_point_quantity")
    details = get_session_data(user_id, "play_point_details")

    if not country or not quantity or not details: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন."); return home_menu(message.chat.id)
    
    user = get_user(user_id)
    
    order_id = f"PPON{int(time.time())}{user_id}"
    # 10. Order database-e save kora hocche
    order_data = {
        "_id": order_id,
        "user_id": user_id, 
        "service": "Play Point Park On", 
        "country": country, 
        "quantity": quantity, 
        "details": details, 
        "price": price, 
        "method": method, 
        "txn_id": txn_id, 
        "status": "pending",
        "timestamp": time.time()
    }
    create_order(order_data)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_pp_{order_id}"))
    
    admin_msg = f"🎁 নতুন Play Point Park On অর্ডার:\n\n📦 Order ID: {order_id}\n👤 User: @{user.get('username', 'N/A')}\n🆔 User ID: {user_id}\n🌍 Country: {country}\n🔢 Quantity: {quantity} টি\n💰 Amount: {price} TK\n💳 Method: {method}\n📝 Txn ID: {txn_id}\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n📩 Gmail Details:\n{details}"
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
    
    user_confirmation = f"✅ আপনার অর্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n🎁 Service: Play Point Park On\n💰 Paid: {price} TK\n\nআপনার অর্ডারটি প্রসেস করা হচ্ছে।\nডেলিভারি সময়: ১-১২ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
    bot.send_message(message.chat.id, user_confirmation)
    
    clear_session_data(user_id) # Session clear
    home_menu(message.chat.id)
# --- End of Play Point Flow ---


# --- Gmail Sell Flow (Task-Based) (MODIFIED for DB) ---

def check_task_timeout(user_id):
    """Checks if a user's active task has expired (30 mins)."""
    user_id_str = str(user_id)
    if user_id_str in active_gmail_tasks:
        task_data = active_gmail_tasks[user_id_str]
        if (time.time() - task_data.get('timestamp', 0)) > 1800: # 30 mins
            # 11. Task-ti database-e ferot pathano hocche
            return_task_to_pool(task_data['task'])
            # active_gmail_tasks theke delete return_task_to_pool-ei hoye jay
            bot.send_message(user_id_str, "❌ আপনার আগের Gmail টাস্কটি ৩০ মিনিট নিষ্ক্রিয় থাকার কারণে মেয়াদ শেষ হয়ে গেছে। টাস্কটি পুলে ফেরত পাঠানো হয়েছে।")
            return True
    return False

def check_complete_submission(user_id, submission_id):
    """Check if all gmails in a submission are processed"""
    if user_id not in pending_gmails or submission_id not in pending_gmails[user_id]:
        return
    
    submission = pending_gmails[user_id][submission_id]
    all_processed = all(gmail["status"] != "pending" for gmail in submission["gmails"])
    
    if all_processed:
        user = get_user(user_id) # Database theke user-er data ana hocche
        username = user.get("username", "NoUsername")
        
        approved_count = sum(1 for g in submission["gmails"] if g["status"] == "approved")
        rejected_count = sum(1 for g in submission["gmails"] if g["status"] == "rejected")
        total_amount = approved_count * 7
        
        admin_msg = f"""
✅ Submission {submission_id} প্রসেস সম্পন্ন!

👤 User: @{username}
🆔 User ID: {user_id}
✅ Approved: {approved_count}টি
❌ Rejected: {rejected_count}টি
💰 Total Added: {total_amount} TK
💳 Final Balance: {user['balance']} TK
"""
        bot.send_message(ADMIN_ID, admin_msg)
        
        del pending_gmails[user_id][submission_id]
        if not pending_gmails[user_id]:
            del pending_gmails[user_id]
        
        # ☢️ save_data() ar nei

@bot.message_handler(func=lambda m: m.text == "📥 Gmail Sell")
def gmail_sell(message):
    user_id = str(message.from_user.id)
    user = get_user(user_id)
    if not user or user.get("is_blocked"): return
    
    check_task_timeout(user_id)
    
    if user_id in active_gmail_tasks:
        # ... (ei logic-e kono database change nei, tai eki thakbe)
        task_data = active_gmail_tasks[user_id]
        task = task_data['task']
        remaining_time = 30 - int((time.time() - task_data['timestamp']) / 60)
        
        task_details_msg = f"""
⏳ আপনার একটি টাস্ক ইতিমধ্যে সক্রিয় আছে!
(এই টাস্কটি Done বা Cancel না করে নতুন টাস্ক নিতে পারবেন না।)

💌 প্রতিটি Gmail এর জন্য পাবেন ৭ টাকা

First name: `{task['fname']}`
Last name: `{task['lname']}`
Email: `{task['email']}`
Password: `{task['password']}`

🔐 Gmail সম্পূর্ণ অ্যাক্সেস সহ হতে হবে কোনো 2FA/2-Step Verification থাকা যাবে না !

⏰ সময় বাকি আছে: {remaining_time} মিনিট

কাজ শেষ হলে "✅ Done" চাপুন অথবা বাতিল করতে "❌ Cancel" চাপুন।
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Done", callback_data=f"gmail_task_done_{user_id}"),
            types.InlineKeyboardButton("❌ Cancel", callback_data=f"gmail_task_cancel_{user_id}")
        )
        bot.send_message(message.chat.id, task_details_msg, reply_markup=markup, parse_mode="Markdown")
        return

    # 12. Database theke available task khuja hocche
    available_tasks_list = get_available_tasks()

    if not available_tasks_list:
        bot.send_message(message.chat.id, "😔 Sorry, no tasks available right now. Please try again later.")
        return
        
    try:
        task_to_assign = available_tasks_list[0] # Prothom task-ti neya hocche
        
        # 13. Task-ti database-e 'active' mark kora hocche
        assign_task_to_user(user_id, task_to_assign)
        
        task_details_msg = f"""
💌 প্রতিটি Gmail এর জন্য পাবেন ৭ টাকা

First name: `{task_to_assign['fname']}`
Last name: `{task_to_assign['lname']}`
Email: `{task_to_assign['email']}`
Password: `{task_to_assign['password']}`

🔐 Gmail সম্পূর্ণ অ্যাক্সেস সহ হতে হবে কোনো 2FA/2-Step Verification থাকা যাবে না !

⏰ আপনার কাছে ৩০ মিনিট সময় আছে।

কাজ শেষ হলে "✅ Done" চাপুন অথবা বাতিল করতে "❌ Cancel" চাপুন।
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Done", callback_data=f"gmail_task_done_{user_id}"),
            types.InlineKeyboardButton("❌ Cancel", callback_data=f"gmail_task_cancel_{user_id}")
        )
        bot.send_message(message.chat.id, task_details_msg, reply_markup=markup, parse_mode="Markdown")

    except IndexError:
        bot.send_message(message.chat.id, "😔 Sorry, no tasks available right now. Please try again later.")
    except Exception as e:
        print(f"Error assigning task: {e}")
        bot.send_message(message.chat.id, "❌ টাস্ক দিতে একটি ত্রুটি হয়েছে। অনুগ্রহ করে অ্যাডমিনের সাথে যোগাযোগ করুন।")
# --- End Gmail Sell ---


# --- Gmail Buy Flow (MODIFIED for DB) ---
@bot.message_handler(func=lambda m: m.text == "📥 Gmail Buy")
def gmail_buy(message):
    user = get_user(message.from_user.id)
    if not user or user.get("is_blocked"): return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    options_available = False
    
    # 14. Stock database theke check kora hocche
    current_stock = get_stock()
    
    if current_stock.get("gmail_usa", -1) != 0:
        markup.add(f"🇺🇸 USA Gmail ({USA_GMAIL_PRICE}TK)")
        options_available = True
    if current_stock.get("gmail_bd", -1) != 0:
        markup.add(f"🇧🇩 BD Gmail ({BD_GMAIL_PRICE}TK)")
        options_available = True

    if not options_available:
        bot.send_message(message.chat.id, "❌ দুঃখিত, সকল Gmail বর্তমানে স্টক আউট আছে।")
        return home_menu(message.chat.id)
        
    options = f"""
🎯 Gmail টাইপ নির্বাচন করুন:

🇺🇸 USA Gmail ({USA_GMAIL_PRICE}TK)
- উচ্চ মানের Gmail

🇧🇩 BD Gmail ({BD_GMAIL_PRICE}TK)
- স্থানীয়ভাবে তৈরি

(স্টক আউট থাকলে অপশন দেখাবে না)
"""
    markup.add("⬅️ Buy Services Menu")
    msg = bot.send_message(message.chat.id, options, reply_markup=markup)
    bot.register_next_step_handler(msg, process_gmail_type)

def process_gmail_type(message):
    if message.text == "⬅️ Buy Services Menu":
        bot.clear_step_handler(message); return buy_services_menu(message)
    
    user_id = str(message.from_user.id)
    selected_text = message.text
    
    # 14. Stock database theke check kora hocche
    current_stock = get_stock()
    
    gmail_type = None
    price_per = 0
    
    if selected_text == f"🇺🇸 USA Gmail ({USA_GMAIL_PRICE}TK)" and current_stock.get("gmail_usa", -1) != 0:
        gmail_type = "USA Gmail"
        price_per = USA_GMAIL_PRICE
    elif selected_text == f"🇧🇩 BD Gmail ({BD_GMAIL_PRICE}TK)" and current_stock.get("gmail_bd", -1) != 0:
        gmail_type = "BD Gmail" 
        price_per = BD_GMAIL_PRICE
    else:
        error_msg = "❌ অবৈধ অপশন বা স্টক আউট! দয়া করে আবার চেষ্টা করুন:"
        bot.send_message(message.chat.id, error_msg)
        return gmail_buy(message) # Restart flow

    # 7. Session data database-e save kora hocche
    set_session_data(user_id, "gmail_type", gmail_type)
    set_session_data(user_id, "gmail_price_per", price_per)
        
    quantity_options = f"✅ {gmail_type} সিলেক্ট করেছেন\n💵 প্রতি একাউন্ট: {price_per} TK\n\n🔢 কতটি Gmail অ্যাকাউন্ট কিনতে চান?\n💡 শুধু সংখ্যা লিখুন:"
    msg = bot.send_message(message.chat.id, quantity_options, reply_markup=back_markup())
    bot.register_next_step_handler(msg, process_gmail_quantity)

def process_gmail_quantity(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    user_id = str(message.from_user.id)
    
    # 8. Session data database theke ber kora hocche
    gmail_type = get_session_data(user_id, "gmail_type")
    price_per = get_session_data(user_id, "gmail_price_per")
    
    if not gmail_type or not price_per:
        bot.send_message(message.chat.id, "❌ ডাটা লস্ট হয়েছে! দয়া করে আবার শুরু করুন:"); return gmail_buy(message)
    try:
        quantity = int(message.text)
        if quantity <= 0: raise ValueError
    except ValueError:
        error_msg = "❌ অবৈধ সংখ্যা! শুধুমাত্র সংখ্যা লিখুন:"; msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, process_gmail_quantity); return
    
    price = price_per * quantity
    discount_msg = ""; discount = 0
    
    if quantity >= 10:
        discount = price * 0.10; 
        discount_msg = f"🎉 ১০+ অর্ডারে ১০% ডিসকাউন্ট পেয়েছেন! (-{discount:.0f} TK)"
    elif quantity >= 5:
        discount = price * 0.05; 
        discount_msg = f"🎉 ৫+ অর্ডারে ৫% ডিসকাউন্ট পেয়েছেন! (-{discount:.0f} TK)"
        
    price = int(price - discount)
        
    # 7. Session data database-e save kora hocche
    set_session_data(user_id, "gmail_quantity", quantity)
    set_session_data(user_id, "gmail_price", price)
    
    order_summary = f"📝 অর্ডার সারাংশ:\n\n📧 Type: {gmail_type}\n🔢 Quantity: {quantity} টি\n💵 প্রতি একাউন্ট: {price_per} TK\n{discount_msg}\n💰 মোট মূল্য: {price} TK\n\n💳 পেমেন্ট মাধ্যম নির্বাচন করুন:"
    bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
    bot.register_next_step_handler(message, process_gmail_payment)

def process_gmail_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    user_id = str(message.from_user.id)
    
    # 8. Session data database theke ber kora hocche
    price = get_session_data(user_id, "gmail_price")
    if not price:
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন:"); return gmail_buy(message)
    
    user = get_user(user_id) # Balance check er jonno
    
    if message.text == "💰 Balance (Pay Now)":
        balance = user.get("balance", 0)
        if balance < price:
            bot.send_message(message.chat.id, f"❌ আপনার ব্যালেন্স কম আছে।\n💰 আপনার ব্যালেন্স: {balance} TK\n🛒 প্রয়োজন: {price} TK\n📉 ঘাটতি: {price - balance} TK")
            msg = bot.send_message(message.chat.id, "অন্য একটি পেমেন্ট মাধ্যম নির্বাচন করুন:", reply_markup=payment_markup())
            bot.register_next_step_handler(msg, process_gmail_payment); return
        else:
            # 8. Session data ber kora hocche
            gmail_type = get_session_data(user_id, "gmail_type")
            quantity = get_session_data(user_id, "gmail_quantity")
            new_balance = balance - price
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add("✅ Confirm", "❌ Cancel")
            confirm_msg = f"""
🔔 কনফার্মেশন:

🎁 Service: {gmail_type}
🔢 Quantity: {quantity} টি
💰 মূল্য: {price} TK (ব্যালেন্স থেকে)
💸 আপনার বর্তমান ব্যালেন্স: {balance} TK
💳 নতুন ব্যালেন্স হবে: {new_balance} TK

আপনি কি এই অর্ডারটি কনফার্ম করতে চান?
"""
            msg = bot.send_message(message.chat.id, confirm_msg, reply_markup=markup)
            bot.register_next_step_handler(msg, process_gmail_balance_confirm)
            return
    
    if message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"; 
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=payment_markup())
        bot.register_next_step_handler(msg, process_gmail_payment); return
        
    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    quantity = get_session_data(user_id, "gmail_quantity")

    payment_instructions = f"💳 {method} এ টাকা পাঠান:\n\n📱 Number: {payment_number}\n💰 Amount: {price} TK\n📝 Reference: Gmail{quantity}\n\n⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন\n\n📨 এখন আপনার Transaction ID লিখুন:"
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_gmail_order(m, method, price))

def process_gmail_balance_confirm(message):
    user_id = str(message.from_user.id)
    if message.text == "❌ Cancel":
        bot.send_message(user_id, "❌ অর্ডার বাতিল করা হয়েছে।")
        clear_session_data(user_id) # Session clear
        return home_menu(user_id)
        
    # 8. Session data database theke ber kora hocche
    price = get_session_data(user_id, "gmail_price")
    gmail_type = get_session_data(user_id, "gmail_type")
    quantity = get_session_data(user_id, "gmail_quantity")

    if not price or not gmail_type or not quantity:
        bot.send_message(user_id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।")
        return home_menu(user_id)

    if message.text == "✅ Confirm":
        user = get_user(user_id)
        balance = user.get("balance", 0)

        if balance < price:
            bot.send_message(user_id, "❌ দুঃখিত, আপনার ব্যালেন্স অপর্যাপ্ত। অর্ডার বাতিল করা হয়েছে।")
            clear_session_data(user_id); return home_menu(user_id)
            
        # 9. Database-e balance update kora hocche
        update_user(user_id, {"$inc": {"balance": -price}})
        
        order_id = f"GMAIL{int(time.time())}{user_id}"
        # 10. Order database-e save kora hocche
        order_data = {
            "_id": order_id,
            "user_id": user_id, 
            "service": "Gmail", 
            "type": gmail_type, 
            "quantity": quantity, 
            "price": price, 
            "method": "Balance", 
            "txn_id": "N/A", 
            "status": "pending",
            "timestamp": time.time()
        }
        create_order(order_data)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_gmail_{order_id}"))
        
        admin_msg = f"🛒 নতুন Gmail অর্ডার (Balance):\n\n📦 Order ID: {order_id}\n👤 User: @{user.get('username', 'N/A')}\n🆔 User ID: {user_id}\n📧 Type: {gmail_type}\n🔢 Quantity: {quantity} টি\n💰 Amount: {price} TK\n💳 Method: Balance\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
        
        user_confirmation = f"✅ আপনার অর্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n📧 Service: {gmail_type}\n🔢 Quantity: {quantity} টি\n💰 Paid: {price} TK (via Balance)\n\nআপনার অর্ডারটি প্রসেস করা হচ্ছে। \nডেলিভারি সময়: ১-১২ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
        bot.send_message(message.chat.id, user_confirmation)
        
        clear_session_data(user_id) # Session clear
        home_menu(message.chat.id)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("✅ Confirm", "❌ Cancel")
        msg = bot.send_message(message.chat.id, "❌ অবৈধ ইনপুট। দয়া করে '✅ Confirm' অথবা '❌ Cancel' বাটন চাপুন।", reply_markup=markup)
        bot.register_next_step_handler(msg, process_gmail_balance_confirm)

def confirm_gmail_order(message, method, price):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    txn_id = message.text.strip()

    # 8. Session data database theke ber kora hocche
    user_id = str(message.from_user.id)
    gmail_type = get_session_data(user_id, "gmail_type")
    quantity = get_session_data(user_id, "gmail_quantity")

    if not gmail_type or not quantity:
        bot.send_message(user_id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।"); return gmail_buy(message)
    
    if len(txn_id) < 3:
        error_msg = "❌ অবৈধ Transaction ID! দয়া করে সঠিক Transaction ID লিখুন:"; 
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, lambda m: confirm_gmail_order(m, method, price)); return
        
    user = get_user(user_id)
    order_id = f"GMAIL{int(time.time())}{user_id}"
    
    # 10. Order database-e save kora hocche
    order_data = {
        "_id": order_id,
        "user_id": user_id, "service": "Gmail", "type": gmail_type, 
        "quantity": quantity, "price": price, "method": method, 
        "txn_id": txn_id, "status": "pending", "timestamp": time.time()
    }
    create_order(order_data)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_gmail_{order_id}"))
    
    admin_msg = f"🛒 নতুন Gmail অর্ডার:\n\n📦 Order ID: {order_id}\n👤 User: @{user.get('username', 'N/A')}\n🆔 User ID: {user_id}\n📧 Type: {gmail_type}\n🔢 Quantity: {quantity} টি\n💰 Amount: {price} TK\n💳 Method: {method}\n📝 Txn ID: {txn_id}\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
    
    user_confirmation = f"✅ আপনার অর্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n📧 Service: {gmail_type}\n🔢 Quantity: {quantity} টি\n💰 Paid: {price} TK\n\nআপনার অর্ডারটি প্রসেস করা হচ্ছে। \nডেলিভারি সময়: ১-১২ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
    bot.send_message(message.chat.id, user_confirmation)
    
    clear_session_data(user_id) # Session clear
    home_menu(message.chat.id)
# --- End of Gmail Buy Flow ---


# --- VPN Buy Flow (MODIFIED for DB) ---
@bot.message_handler(func=lambda m: m.text == "🌐 Paid VPN Buy")
def vpn_buy(message):
    user = get_user(message.from_user.id)
    if not user or user.get("is_blocked"): return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    options_available = False
    
    # 14. Stock database theke check kora hocche
    current_stock = get_stock()
    
    vpn_services = {
        "vpn_nord": f"NordVPN 7 Days ({VPN_PRICE}TK)",
        "vpn_express": f"ExpressVPN 7 Days ({VPN_PRICE}TK)",
        "vpn_hma": f"HMA VPN 7 Days ({VPN_PRICE}TK)",
        "vpn_pia": f"PIA VPN 7 Days ({VPN_PRICE}TK)",
        "vpn_ipvanis": f"Ipvanis VPN 7 Days ({VPN_PRICE}TK)"
    }
    
    buttons_to_add = []
    for key, text in vpn_services.items():
        if current_stock.get(key, -1) != 0:
            buttons_to_add.append(text)
            options_available = True
            
    if not options_available:
        bot.send_message(message.chat.id, "❌ দুঃখিত, সকল VPN বর্তমানে স্টক আউট আছে।")
        return home_menu(message.chat.id)
        
    markup.add(*buttons_to_add)
    markup.add("⬅️ Buy Services Menu")
    
    vpn_options = f"""
🔒 VPN প্যাকেজ নির্বাচন করুন:
(মূল্য: {VPN_PRICE} TK প্রতিটি)

(স্টক আউট থাকলে অপশন দেখাবে না)
"""
    msg = bot.send_message(message.chat.id, vpn_options, reply_markup=markup)
    bot.register_next_step_handler(msg, select_vpn_type)

def select_vpn_type(message):
    if message.text == "⬅️ Buy Services Menu":
        bot.clear_step_handler(message); return buy_services_menu(message)
    
    selected_vpn = message.text
    
    vpn_services_texts = [
        f"NordVPN 7 Days ({VPN_PRICE}TK)", f"ExpressVPN 7 Days ({VPN_PRICE}TK)",
        f"HMA VPN 7 Days ({VPN_PRICE}TK)", f"PIA VPN 7 Days ({VPN_PRICE}TK)",
        f"Ipvanis VPN 7 Days ({VPN_PRICE}TK)"
    ]
    if selected_vpn not in vpn_services_texts:
        bot.send_message(message.chat.id, "❌ অবৈধ নির্বাচন বা স্টক আউট। আবার চেষ্টা করুন।"); return vpn_buy(message)
        
    user_id = str(message.from_user.id)
    # 7. Session data database-e save kora hocche
    set_session_data(user_id, "vpn_type", selected_vpn)
    
    order_summary = f"📝 অর্র্ডার সারাংশ:\n\n🔒 Service: {selected_vpn}\n💰 মূল্য: {VPN_PRICE} TK\n\n💳 পেমেন্ট মাধ্যম নির্বাচন করুন:"
    bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
    bot.register_next_step_handler(message, process_vpn_payment)

def process_vpn_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    user_id = str(message.from_user.id)
    
    # 8. Session data database theke ber kora hocche
    vpn_type = get_session_data(user_id, "vpn_type")
    if not vpn_type: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।"); return vpn_buy(message)

    user = get_user(user_id)
    price = VPN_PRICE

    if message.text == "💰 Balance (Pay Now)":
        balance = user.get("balance", 0)
        if balance < price:
            bot.send_message(message.chat.id, f"❌ আপনার ব্যালেন্স কম আছে।\n...")
            msg = bot.send_message(message.chat.id, "অন্য একটি পেমেন্ট মাধ্যম নির্বাচন করুন:", reply_markup=payment_markup())
            bot.register_next_step_handler(msg, process_vpn_payment)
            return
        else:
            new_balance = balance - price
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add("✅ Confirm", "❌ Cancel")
            confirm_msg = f"""
🔔 কনফার্মেশন:

🎁 Service: {vpn_type}
💰 মূল্য: {price} TK (ব্যালেন্স থেকে)
💸 আপনার বর্তমান ব্যালেন্স: {balance} TK
💳 নতুন ব্যালেন্স হবে: {new_balance} TK

আপনি কি এই অর্ডারটি কনফার্ম করতে চান?
"""
            msg = bot.send_message(message.chat.id, confirm_msg, reply_markup=markup)
            bot.register_next_step_handler(msg, process_vpn_balance_confirm)
            return

    if message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"; 
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=payment_markup())
        bot.register_next_step_handler(msg, process_vpn_payment); return
        
    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    
    payment_instructions = f"💳 {method} এ টাকা পাঠান:\n\n📱 Number: {payment_number}\n💰 Amount: {price} TK\n📝 Reference: VPN\n\n⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন\n\n📨 এখন আপনার Transaction ID লিখুন:"
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_vpn_order(m, method, price))

def process_vpn_balance_confirm(message):
    user_id = str(message.from_user.id)
    if message.text == "❌ Cancel":
        bot.send_message(user_id, "❌ অর্ডার বাতিল করা হয়েছে।")
        clear_session_data(user_id); return home_menu(user_id)
        
    # 8. Session data database theke ber kora hocche
    vpn_type = get_session_data(user_id, "vpn_type")
    if not vpn_type:
        bot.send_message(user_id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।")
        return home_menu(user_id)

    price = VPN_PRICE
    if message.text == "✅ Confirm":
        user = get_user(user_id)
        balance = user.get("balance", 0)

        if balance < price:
            bot.send_message(user_id, "❌ দুঃখিত, আপনার ব্যালেন্স অপর্যাপ্ত। অর্ডার বাতিল করা হয়েছে।")
            clear_session_data(user_id); return home_menu(user_id)
            
        # 9. Database-e balance update kora hocche
        update_user(user_id, {"$inc": {"balance": -price}})
        
        order_id = f"VPN{int(time.time())}{user_id}"
        # 10. Order database-e save kora hocche
        order_data = {
            "_id": order_id,
            "user_id": user_id, 
            "service": "VPN", 
            "type": vpn_type, 
            "price": price, 
            "method": "Balance", 
            "txn_id": "N/A", 
            "status": "pending",
            "timestamp": time.time()
        }
        create_order(order_data)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_vpn_{order_id}"))
        
        admin_msg = f"🔐 নতুন VPN অর্ডার (Balance):\n\n📦 Order ID: {order_id}\n👤 User: @{user.get('username', 'N/A')}\n🆔 User ID: {user_id}\n🔒 VPN: {vpn_type}\n💰 Amount: {price} TK\n💳 Method: Balance\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
        
        user_confirmation = f"✅ আপনার অর্র্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n🔒 Service: {vpn_type}\n💰 Paid: {price} TK (via Balance)\n\nআপনার অর্র্ডারটি প্রসেস করা হচ্ছে। \nডেলিভারি সময়: ১-৬ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
        bot.send_message(message.chat.id, user_confirmation)
        
        clear_session_data(user_id)
        home_menu(message.chat.id)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("✅ Confirm", "❌ Cancel")
        msg = bot.send_message(message.chat.id, "❌ অবৈধ ইনপুট। দয়া করে '✅ Confirm' অথবা '❌ Cancel' বাটন চাপুন।", reply_markup=markup)
        bot.register_next_step_handler(msg, process_vpn_balance_confirm)

def confirm_vpn_order(message, method, price):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    txn_id = message.text
    user_id = str(message.from_user.id)
    
    # 8. Session data database theke ber kora hocche
    vpn_type = get_session_data(user_id, "vpn_type")
    if not vpn_type: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন."); return home_menu(message.chat.id)
        
    user = get_user(user_id)
    order_id = f"VPN{int(time.time())}{user_id}"
    # 10. Order database-e save kora hocche
    order_data = {
        "_id": order_id,
        "user_id": user_id, "service": "VPN", "type": vpn_type, 
        "price": price, "method": method, "txn_id": txn_id, 
        "status": "pending", "timestamp": time.time()
    }
    create_order(order_data)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_vpn_{order_id}"))
    
    admin_msg = f"🔐 নতুন VPN অর্ডার:\n\n📦 Order ID: {order_id}\n👤 User: @{user.get('username', 'N/A')}\n🆔 User ID: {user_id}\n🔒 VPN: {vpn_type}\n💰 Amount: {price} TK\n💳 Method: {method}\n📝 Txn ID: {txn_id}\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
    
    user_confirmation = f"✅ আপনার অর্র্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n🔒 Service: {vpn_type}\n💰 Paid: {price} TK\n\nআপনার অর্র্ডারটি প্রসেস করা হচ্ছে। \nডেলিভারি সময়: ১-৬ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
    bot.send_message(message.chat.id, user_confirmation)
    
    clear_session_data(user_id)
    home_menu(message.chat.id)
# --- End of VPN Flow ---


# --- YouTube Premium Flow (MODIFIED for DB) ---
@bot.message_handler(func=lambda m: m.text == "🎥 YouTube Premium")
def yt_premium(message):
    user = get_user(message.from_user.id)
    if not user or user.get("is_blocked"): return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    options_available = False
    
    # 14. Stock database theke check kora hocche
    current_stock = get_stock()
    
    if current_stock.get("yt_1_month", -1) != 0:
        markup.add(f"1 Month ({YT_1M_PRICE}TK)")
        options_available = True
    if current_stock.get("yt_1_year", -1) != 0:
        markup.add(f"1 Year ({YT_1Y_PRICE}TK)")
        options_available = True

    if not options_available:
        bot.send_message(message.chat.id, "❌ দুঃখিত, সকল YouTube Premium প্যাকেজ বর্তমানে স্টক আউট আছে।")
        return home_menu(message.chat.id)
        
    yt_options = """
🎬 YouTube Premium প্যাকেজ:
(স্টক আউট থাকলে অপশন দেখাবে না)
"""
    markup.add("⬅️ Buy Services Menu")
    msg = bot.send_message(message.chat.id, yt_options, reply_markup=markup)
    bot.register_next_step_handler(msg, select_yt_plan)

def select_yt_plan(message):
    if message.text == "⬅️ Buy Services Menu":
        bot.clear_step_handler(message); return buy_services_menu(message)
        
    selected_plan = message.text
    price = 0
    
    # 14. Stock database theke check kora hocche
    current_stock = get_stock()
    
    if selected_plan == f"1 Month ({YT_1M_PRICE}TK)" and current_stock.get("yt_1_month", -1) != 0:
        price = YT_1M_PRICE
    elif selected_plan == f"1 Year ({YT_1Y_PRICE}TK)" and current_stock.get("yt_1_year", -1) != 0:
        price = YT_1Y_PRICE
    else:
        bot.send_message(message.chat.id, "❌ অবৈধ নির্বাচন বা স্টক আউট। আবার চেষ্টা করুন।"); return yt_premium(message)
        
    user_id = str(message.from_user.id)
    # 7. Session data database-e save kora hocche
    set_session_data(user_id, "yt_plan", selected_plan)
    set_session_data(user_id, "yt_price", price)
    
    order_summary = f"📝 অর্ডার সারাংশ:\n\n🎬 Service: {selected_plan}\n💰 মূল্য: {price} TK\n\n💳 পেমেন্ট মাধ্যম নির্বাচন করুন:"
    bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
    bot.register_next_step_handler(message, process_yt_payment)

def process_yt_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    user_id = str(message.from_user.id)
    
    # 8. Session data database theke ber kora hocche
    price = get_session_data(user_id, "yt_price")
    yt_plan = get_session_data(user_id, "yt_plan")
    
    if not price or not yt_plan: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।"); return yt_premium(message)

    user = get_user(user_id)
    
    if message.text == "💰 Balance (Pay Now)":
        balance = user.get("balance", 0)
        if balance < price:
            bot.send_message(message.chat.id, f"❌ আপনার ব্যালেন্স কম আছে।\n...")
            msg = bot.send_message(message.chat.id, "অন্য একটি পেমেন্ট মাধ্যম নির্বাচন করুন:", reply_markup=payment_markup())
            bot.register_next_step_handler(msg, process_yt_payment)
            return
        else:
            new_balance = balance - price
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add("✅ Confirm", "❌ Cancel")
            confirm_msg = f"""
🔔 কনফার্মেশন:

🎁 Service: {yt_plan}
💰 মূল্য: {price} TK (ব্যালেন্স থেকে)
💸 আপনার বর্তমান ব্যালেন্স: {balance} TK
💳 নতুন ব্যালেন্স হবে: {new_balance} TK

আপনি কি এই অর্ডারটি কনফার্ম করতে চান?
"""
            msg = bot.send_message(message.chat.id, confirm_msg, reply_markup=markup)
            bot.register_next_step_handler(msg, process_yt_balance_confirm)
            return
    
    if message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"; 
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=payment_markup())
        bot.register_next_step_handler(msg, process_yt_payment); return
        
    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    
    payment_instructions = f"💳 {method} এ টাকা পাঠান:\n\n📱 Number: {payment_number}\n💰 Amount: {price} TK\n📝 Reference: YT\n\n⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন\n\n📨 এখন আপনার Transaction ID লিখুন:"
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_yt_order(m, method, price))

def process_yt_balance_confirm(message):
    user_id = str(message.from_user.id)
    if message.text == "❌ Cancel":
        bot.send_message(user_id, "❌ অর্ডার বাতিল করা হয়েছে।")
        clear_session_data(user_id); return home_menu(user_id)
        
    # 8. Session data database theke ber kora hocche
    price = get_session_data(user_id, "yt_price")
    yt_plan = get_session_data(user_id, "yt_plan")

    if not price or not yt_plan:
        bot.send_message(user_id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।")
        return home_menu(user_id)

    if message.text == "✅ Confirm":
        user = get_user(user_id)
        balance = user.get("balance", 0)

        if balance < price:
            bot.send_message(user_id, "❌ দুঃখিত, আপনার ব্যালেন্স অপর্যাপ্ত। অর্ডার বাতিল করা হয়েছে।")
            clear_session_data(user_id); return home_menu(user_id)
            
        # 9. Database-e balance update kora hocche
        update_user(user_id, {"$inc": {"balance": -price}})
        
        order_id = f"YT{int(time.time())}{user_id}"
        # 10. Order database-e save kora hocche
        order_data = {
            "_id": order_id,
            "user_id": user_id, 
            "service": "YouTube Premium", 
            "type": yt_plan, 
            "price": price, 
            "method": "Balance", 
            "txn_id": "N/A", 
            "status": "pending",
            "timestamp": time.time()
        }
        create_order(order_data)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_yt_{order_id}"))
        
        admin_msg = f"📺 নতুন YouTube Premium অর্ডার (Balance):\n\n📦 Order ID: {order_id}\n👤 User: @{user.get('username', 'N/A')}\n🆔 User ID: {user_id}\n🎬 Plan: {yt_plan}\n💰 Amount: {price} TK\n💳 Method: Balance\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
        
        user_confirmation = f"✅ আপনার অর্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n🎬 Service: {yt_plan}\n💰 Paid: {price} TK (via Balance)\n\nআপনার অর্ডারটি প্রসেস করা হচ্ছে। \nডেলিভারি সময়: ১-৬ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
        bot.send_message(message.chat.id, user_confirmation)
        
        clear_session_data(user_id)
        home_menu(message.chat.id)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("✅ Confirm", "❌ Cancel")
        msg = bot.send_message(message.chat.id, "❌ অবৈধ ইনপুট। দয়া করে '✅ Confirm' অথবা '❌ Cancel' বাটন চাপুন।", reply_markup=markup)
        bot.register_next_step_handler(msg, process_yt_balance_confirm)

def confirm_yt_order(message, method, price):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    txn_id = message.text
    user_id = str(message.from_user.id)
    
    # 8. Session data database theke ber kora hocche
    yt_plan = get_session_data(user_id, "yt_plan")
    if not yt_plan: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন."); return yt_premium(message)
        
    user = get_user(user_id)
    order_id = f"YT{int(time.time())}{user_id}"
    # 10. Order database-e save kora hocche
    order_data = {
        "_id": order_id,
        "user_id": user_id, "service": "YouTube Premium", "type": yt_plan, 
        "price": price, "method": method, "txn_id": txn_id, 
        "status": "pending", "timestamp": time.time()
    }
    create_order(order_data)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_yt_{order_id}"))
    
    admin_msg = f"📺 নতুন YouTube Premium অর্ডার:\n\n📦 Order ID: {order_id}\n👤 User: @{user.get('username', 'N/A')}\n🆔 User ID: {user_id}\n🎬 Plan: {yt_plan}\n💰 Amount: {price} TK\n💳 Method: {method}\n📝 Txn ID: {txn_id}\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
    
    user_confirmation = f"✅ আপনার অর্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n🎬 Service: {yt_plan}\n💰 Paid: {price} TK\n\nআপনার অর্ডারটি প্রসেস করা হচ্ছে। \nডেলিভারি সময়: ১-৬ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
    bot.send_message(message.chat.id, user_confirmation)
    
    clear_session_data(user_id)
    home_menu(message.chat.id)
# --- End of YouTube Premium Flow ---


# --- NEW: Crunchyroll Premium Flow (MODIFIED for DB) ---
@bot.message_handler(func=lambda m: m.text == "🍿 Crunchyroll Premium")
def crunchyroll_buy(message):
    user = get_user(message.from_user.id)
    if not user or user.get("is_blocked"): return
    
    # 14. Stock database theke check kora hocche
    current_stock = get_stock()
    if current_stock.get("crunchyroll_7_day", -1) == 0:
        bot.send_message(message.chat.id, "❌ দুঃখিত, Crunchyroll Premium বর্তমানে স্টক আউট আছে।")
        return home_menu(message.chat.id)
        
    plan_text = f"7 Days ({CRUNCHYROLL_PRICE}TK)"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(plan_text, "⬅️ Buy Services Menu")
    
    options = f"""
🍿 Crunchyroll Premium প্যাকেজ:
{plan_text}
- ৭ দিনের প্রিমিয়াম অ্যাক্সেস
- দ্রুত ডেলিভারি
"""
    msg = bot.send_message(message.chat.id, options, reply_markup=markup)
    bot.register_next_step_handler(msg, select_crunchyroll_plan)

def select_crunchyroll_plan(message):
    if message.text == "⬅️ Buy Services Menu":
        bot.clear_step_handler(message); return buy_services_menu(message)
        
    selected_plan = message.text
    plan_text = f"7 Days ({CRUNCHYROLL_PRICE}TK)"
    
    if selected_plan != plan_text:
        bot.send_message(message.chat.id, "❌ অবৈধ নির্বাচন। আবার চেষ্টা করুন।"); return crunchyroll_buy(message)
        
    price = CRUNCHYROLL_PRICE
    user_id = str(message.from_user.id)
    # 7. Session data database-e save kora hocche
    set_session_data(user_id, "cr_plan", selected_plan)
    
    order_summary = f"📝 অর্ডার সারাংশ:\n\n🍿 Service: {selected_plan}\n💰 মূল্য: {price} TK\n\n💳 পেমেন্ট মাধ্যম নির্বাচন করুন:"
    bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
    bot.register_next_step_handler(message, process_crunchyroll_payment)

def process_crunchyroll_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    user_id = str(message.from_user.id)
    
    # 8. Session data database theke ber kora hocche
    cr_plan = get_session_data(user_id, "cr_plan")
    if not cr_plan: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।"); return crunchyroll_buy(message)

    user = get_user(user_id)
    price = CRUNCHYROLL_PRICE

    if message.text == "💰 Balance (Pay Now)":
        balance = user.get("balance", 0)
        if balance < price:
            bot.send_message(message.chat.id, f"❌ আপনার ব্যালেন্স কম আছে।\n...")
            msg = bot.send_message(message.chat.id, "অন্য একটি পেমেন্ট মাধ্যম নির্বাচন করুন:", reply_markup=payment_markup())
            bot.register_next_step_handler(msg, process_crunchyroll_payment)
            return
        else:
            new_balance = balance - price
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add("✅ Confirm", "❌ Cancel")
            confirm_msg = f"""
🔔 কনফার্মেশন:

🎁 Service: {cr_plan}
💰 মূল্য: {price} TK (ব্যালেন্স থেকে)
💸 আপনার বর্তমান ব্যালেন্স: {balance} TK
💳 নতুন ব্যালেন্স হবে: {new_balance} TK

আপনি কি এই অর্ডারটি কনফার্ম করতে চান?
"""
            msg = bot.send_message(message.chat.id, confirm_msg, reply_markup=markup)
            bot.register_next_step_handler(msg, process_crunchyroll_balance_confirm)
            return
    
    if message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"; 
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=payment_markup())
        bot.register_next_step_handler(msg, process_crunchyroll_payment); return
        
    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    
    payment_instructions = f"💳 {method} এ টাকা পাঠান:\n\n📱 Number: {payment_number}\n💰 Amount: {price} TK\n📝 Reference: CR\n\n⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন\n\n📨 এখন আপনার Transaction ID লিখুন:"
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_crunchyroll_order(m, method, price))

def process_crunchyroll_balance_confirm(message):
    user_id = str(message.from_user.id)
    if message.text == "❌ Cancel":
        bot.send_message(user_id, "❌ অর্ডার বাতিল করা হয়েছে।")
        clear_session_data(user_id); return home_menu(user_id)
        
    # 8. Session data database theke ber kora hocche
    cr_plan = get_session_data(user_id, "cr_plan")
    if not cr_plan:
        bot.send_message(user_id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।")
        return home_menu(user_id)
    
    price = CRUNCHYROLL_PRICE
    if message.text == "✅ Confirm":
        user = get_user(user_id)
        balance = user.get("balance", 0)

        if balance < price:
            bot.send_message(user_id, "❌ দুঃখিত, আপনার ব্যালেন্স অপর্যাপ্ত। অর্ডার বাতিল করা হয়েছে।")
            clear_session_data(user_id); return home_menu(user_id)
            
        # 9. Database-e balance update kora hocche
        update_user(user_id, {"$inc": {"balance": -price}})
        
        order_id = f"CR{int(time.time())}{user_id}"
        # 10. Order database-e save kora hocche
        order_data = {
            "_id": order_id,
            "user_id": user_id, 
            "service": "Crunchyroll Premium", 
            "type": cr_plan, 
            "price": price, 
            "method": "Balance", 
            "txn_id": "N/A", 
            "status": "pending",
            "timestamp": time.time()
        }
        create_order(order_data)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_cr_{order_id}"))
        
        admin_msg = f"🍿 নতুন Crunchyroll অর্ডার (Balance):\n\n📦 Order ID: {order_id}\n👤 User: @{user.get('username', 'N/A')}\n🆔 User ID: {user_id}\n🎬 Plan: {cr_plan}\n💰 Amount: {price} TK\n💳 Method: Balance\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
        
        user_confirmation = f"✅ আপনার অর্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n🎬 Service: {cr_plan}\n💰 Paid: {price} TK (via Balance)\n\nআপনার অর্ডারটি প্রসেস করা হচ্ছে। \nডেলিভারি সময়: ১-৬ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
        bot.send_message(message.chat.id, user_confirmation)
        
        clear_session_data(user_id)
        home_menu(message.chat.id)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("✅ Confirm", "❌ Cancel")
        msg = bot.send_message(message.chat.id, "❌ অবৈধ ইনপুট। দয়া করে '✅ Confirm' অথবা '❌ Cancel' বাটন চাপুন।", reply_markup=markup)
        bot.register_next_step_handler(msg, process_crunchyroll_balance_confirm)

def confirm_crunchyroll_order(message, method, price):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    txn_id = message.text
    user_id = str(message.from_user.id)
    
    # 8. Session data database theke ber kora hocche
    cr_plan = get_session_data(user_id, "cr_plan")
    if not cr_plan: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন."); return crunchyroll_buy(message)
        
    user = get_user(user_id)
    order_id = f"CR{int(time.time())}{user_id}"
    # 10. Order database-e save kora hocche
    order_data = {
        "_id": order_id,
        "user_id": user_id, "service": "Crunchyroll Premium", "type": cr_plan, 
        "price": price, "method": method, "txn_id": txn_id, 
        "status": "pending", "timestamp": time.time()
    }
    create_order(order_data)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_cr_{order_id}"))
    
    admin_msg = f"🍿 নতুন Crunchyroll অর্ডার:\n\n📦 Order ID: {order_id}\n👤 User: @{user.get('username', 'N/A')}\n🆔 User ID: {user_id}\n🎬 Plan: {cr_plan}\n💰 Amount: {price} TK\n💳 Method: {method}\n📝 Txn ID: {txn_id}\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
    
    user_confirmation = f"✅ আপনার অর্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n🎬 Service: {cr_plan}\n💰 Paid: {price} TK\n\nআপনার অর্ডারটি প্রসেস করা হচ্ছে। \nডেলিভারি সময়: ১-৬ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
    bot.send_message(message.chat.id, user_confirmation)
    
    clear_session_data(user_id)
    home_menu(message.chat.id)
# --- End of Crunchyroll Premium Flow ---


# --- NEW: Google Veo 3 Flow (MODIFIED for DB) ---
@bot.message_handler(func=lambda m: m.text == "🧠 Google Veo 3 (Gemin)")
def veo_buy(message):
    user = get_user(message.from_user.id)
    if not user or user.get("is_blocked"): return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    options_available = False
    
    # 14. Stock database theke check kora hocche
    current_stock = get_stock()
    
    if current_stock.get("veo_1_month", -1) != 0:
        markup.add(f"1 Month ({VEO_1M_PRICE}TK)")
        options_available = True
    if current_stock.get("veo_12_month", -1) != 0:
        markup.add(f"12 Month ({VEO_12M_PRICE}TK)")
        options_available = True

    if not options_available:
        bot.send_message(message.chat.id, "❌ দুঃখিত, সকল Google Veo 3 প্যাকেজ বর্তমানে স্টক আউট আছে।")
        return home_menu(message.chat.id)
        
    options = """
🧠 Google Veo 3 (Gemin) প্যাকেজ:
(স্টক আউট থাকলে অপশন দেখাবে না)
"""
    markup.add("⬅️ Buy Services Menu")
    msg = bot.send_message(message.chat.id, options, reply_markup=markup)
    bot.register_next_step_handler(msg, select_veo_plan)

def select_veo_plan(message):
    if message.text == "⬅️ Buy Services Menu":
        bot.clear_step_handler(message); return buy_services_menu(message)
        
    selected_plan = message.text
    price = 0
    
    # 14. Stock database theke check kora hocche
    current_stock = get_stock()
    
    if selected_plan == f"1 Month ({VEO_1M_PRICE}TK)" and current_stock.get("veo_1_month", -1) != 0:
        price = VEO_1M_PRICE
    elif selected_plan == f"12 Month ({VEO_12M_PRICE}TK)" and current_stock.get("veo_12_month", -1) != 0:
        price = VEO_12M_PRICE
    else:
        bot.send_message(message.chat.id, "❌ অবৈধ নির্বাচন বা স্টক আউট। আবার চেষ্টা করুন।"); return veo_buy(message)
        
    user_id = str(message.from_user.id)
    # 7. Session data database-e save kora hocche
    set_session_data(user_id, "veo_plan", selected_plan)
    set_session_data(user_id, "veo_price", price)
    
    order_summary = f"📝 অর্ডার সারাংশ:\n\n🧠 Service: {selected_plan}\n💰 মূল্য: {price} TK\n\n💳 পেমেন্ট মাধ্যম নির্বাচন করুন:"
    bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
    bot.register_next_step_handler(message, process_veo_payment)

def process_veo_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    user_id = str(message.from_user.id)
    
    # 8. Session data database theke ber kora hocche
    veo_plan = get_session_data(user_id, "veo_plan")
    price = get_session_data(user_id, "veo_price")
    
    if not veo_plan or not price: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।"); return veo_buy(message)

    user = get_user(user_id)
    
    if message.text == "💰 Balance (Pay Now)":
        balance = user.get("balance", 0)
        if balance < price:
            bot.send_message(message.chat.id, f"❌ আপনার ব্যালেন্স কম আছে।\n...")
            msg = bot.send_message(message.chat.id, "অন্য একটি পেমেন্ট মাধ্যম নির্বাচন করুন:", reply_markup=payment_markup())
            bot.register_next_step_handler(msg, process_veo_payment)
            return
        else:
            new_balance = balance - price
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add("✅ Confirm", "❌ Cancel")
            confirm_msg = f"""
🔔 কনফার্মেশন:

🎁 Service: {veo_plan}
💰 মূল্য: {price} TK (ব্যালেন্স থেকে)
💸 আপনার বর্তমান ব্যালেন্স: {balance} TK
💳 নতুন ব্যালেন্স হবে: {new_balance} TK

আপনি কি এই অর্ডারটি কনফার্ম করতে চান?
"""
            msg = bot.send_message(message.chat.id, confirm_msg, reply_markup=markup)
            bot.register_next_step_handler(msg, process_veo_balance_confirm)
            return
    
    if message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"; 
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=payment_markup())
        bot.register_next_step_handler(msg, process_veo_payment); return
        
    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    
    payment_instructions = f"💳 {method} এ টাকা পাঠান:\n\n📱 Number: {payment_number}\n💰 Amount: {price} TK\n📝 Reference: VEO\n\n⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন\n\n📨 এখন আপনার Transaction ID লিখুন:"
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_veo_order(m, method, price))

def process_veo_balance_confirm(message):
    user_id = str(message.from_user.id)
    if message.text == "❌ Cancel":
        bot.send_message(user_id, "❌ অর্ডার বাতিল করা হয়েছে।")
        clear_session_data(user_id); return home_menu(user_id)
        
    # 8. Session data database theke ber kora hocche
    veo_plan = get_session_data(user_id, "veo_plan")
    price = get_session_data(user_id, "veo_price")

    if not veo_plan or not price:
        bot.send_message(user_id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।")
        return home_menu(user_id)

    if message.text == "✅ Confirm":
        user = get_user(user_id)
        balance = user.get("balance", 0)

        if balance < price:
            bot.send_message(user_id, "❌ দুঃখিত, আপনার ব্যালেন্স অপর্যাপ্ত। অর্ডার বাতিল করা হয়েছে।")
            clear_session_data(user_id); return home_menu(user_id)
            
        # 9. Database-e balance update kora hocche
        update_user(user_id, {"$inc": {"balance": -price}})
        
        order_id = f"VEO{int(time.time())}{user_id}"
        # 10. Order database-e save kora hocche
        order_data = {
            "_id": order_id,
            "user_id": user_id, 
            "service": "Google Veo 3", 
            "type": veo_plan, 
            "price": price, 
            "method": "Balance", 
            "txn_id": "N/A", 
            "status": "pending",
            "timestamp": time.time()
        }
        create_order(order_data)
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_veo_{order_id}"))
        
        admin_msg = f"🧠 নতুন Google Veo 3 অর্ডার (Balance):\n\n📦 Order ID: {order_id}\n👤 User: @{user.get('username', 'N/A')}\n🆔 User ID: {user_id}\n🎬 Plan: {veo_plan}\n💰 Amount: {price} TK\n💳 Method: Balance\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
        
        user_confirmation = f"✅ আপনার অর্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n🎬 Service: {veo_plan}\n💰 Paid: {price} TK (via Balance)\n\nআপনার অর্ডারটি প্রসেস করা হচ্ছে। \nডেলিভারি সময়: ১-৬ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
        bot.send_message(message.chat.id, user_confirmation)
        
        clear_session_data(user_id)
        home_menu(message.chat.id)
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("✅ Confirm", "❌ Cancel")
        msg = bot.send_message(message.chat.id, "❌ অবৈধ ইনপুট। দয়া করে '✅ Confirm' অথবা '❌ Cancel' বাটন চাপুন।", reply_markup=markup)
        bot.register_next_step_handler(msg, process_veo_balance_confirm)

def confirm_veo_order(message, method, price):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    txn_id = message.text
    user_id = str(message.from_user.id)
    
    # 8. Session data database theke ber kora hocche
    veo_plan = get_session_data(user_id, "veo_plan")
    if not veo_plan: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন."); return veo_buy(message)
        
    user = get_user(user_id)
    order_id = f"VEO{int(time.time())}{user_id}"
    # 10. Order database-e save kora hocche
    order_data = {
        "_id": order_id,
        "user_id": user_id, "service": "Google Veo 3", "type": veo_plan, 
        "price": price, "method": method, "txn_id": txn_id, 
        "status": "pending", "timestamp": time.time()
    }
    create_order(order_data)
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_veo_{order_id}"))
    
    admin_msg = f"🧠 নতুন Google Veo 3 অর্ডার:\n\n📦 Order ID: {order_id}\n👤 User: @{user.get('username', 'N/A')}\n🆔 User ID: {user_id}\n🎬 Plan: {veo_plan}\n💰 Amount: {price} TK\n💳 Method: {method}\n📝 Txn ID: {txn_id}\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
    
    user_confirmation = f"✅ আপনার অর্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n🎬 Service: {veo_plan}\n💰 Paid: {price} TK\n\nআপনার অর্ডারটি প্রসেস করা হচ্ছে। \nডেলিভারি সময়: ১-৬ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
    bot.send_message(message.chat.id, user_confirmation)
    
    clear_session_data(user_id)
    home_menu(message.chat.id)
# --- End of Google Veo 3 Flow ---


# --- Balance, Withdraw, Refer, Support (Updated for DB) ---
@bot.message_handler(func=lambda m: m.text == "💳 Balance")
def check_balance(message):
    user_id = str(message.from_user.id)
    
    # 1. Database theke user-er data ana hocche
    user = get_user(user_id)
    if not user:
        bot.send_message(message.chat.id, "❌ একাউন্ট খুঁজে পাওয়া যায়নি!"); return
    if user.get("is_blocked"): return
    
    balance = user.get("balance", 0)
    hold = user.get("hold", 0)
    ref_count = user.get("referral_count", 0)
    join_date = user.get("joined_date", "N/A")
    estimated_earnings = balance + hold + (ref_count * 2)
    
    balance_msg = f"""
💰 আপনার একাউন্ট বিবরণী:

💵 Available Balance: {balance} TK
⏳ Hold Balance: {hold} TK
💰 Total Balance: {balance + hold} TK
👥 Referrals: {ref_count} জন
📈 Estimated Earnings: {estimated_earnings} TK
📅 Join Date: {join_date}

💡 টাকা উত্তোলন করতে '💵 Withdraw' অপশন ব্যবহার করুন
"""
    bot.send_message(message.chat.id, balance_msg)

@bot.message_handler(func=lambda m: m.text == "💵 Withdraw")
def withdraw(message):
    user_id = str(message.from_user.id)
    
    # 1. Database theke user-er data ana hocche
    user = get_user(user_id)
    if not user or user.get("is_blocked"): return
    
    balance = user["balance"]
    if balance < MIN_WITHDRAW:
        error_msg = f"❌ সর্বনিম্ন উত্তোলন {MIN_WITHDRAW} টাকা\n\n💰 আপনার ব্যালেন্স: {balance} TK\n🎯 প্রয়োজন: {MIN_WITHDRAW - balance} TK more\n\n💡 টাকা উপার্জনের উপায়:\n1. Gmail টাস্ক পূরণ করুন (৭ TK/Gmail)\n2. বন্ধুদের রেফার করুন (২ TK/Referral)"
        bot.send_message(message.chat.id, error_msg); return
        
    withdraw_msg = f"💵 উত্তোলনের পরিমাণ লিখুন:\n\n💰 Available: {balance} TK\n🎯 Minimum: {MIN_WITHDRAW} TK\n💸 Maximum: {balance} TK\n\nℹ️ {WITHDRAW_FEE_THRESHOLD} TK এর বেশি উত্তোলনে {WITHDRAW_FEE} TK ফি প্রযোজ্য হবে।\n\nউদাহরণ: {MIN_WITHDRAW}, 100, 200"
    msg = bot.send_message(message.chat.id, withdraw_msg, reply_markup=back_markup()) 
    bot.register_next_step_handler(msg, process_withdraw_amount)

def process_withdraw_amount(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    try:
        amount = int(message.text)
        user_id = str(message.from_user.id)
        
        # 1. Database theke user-er data ana hocche
        user = get_user(user_id)
        balance = user["balance"]
        
        if amount < MIN_WITHDRAW:   
            # --- ERROR THIK KORA ---
            error_msg = f"❌ সর্বনিম্ন {MIN_WITHDRAW} টাকা উত্তোলন করতে পারবেন!\n\nআবার চেষ্টা করুন:"
            msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup()) 
            bot.register_next_step_handler(msg, process_withdraw_amount); return   
        if amount > balance:    
            error_msg = f"❌ আপনার একাউন্টে পর্যাপ্ত টাকা নেই!\n\n💰 আপনার ব্যালেন্স: {balance} TK\n💸 চাহিদাকৃত: {amount} TK\n📉 ঘাটতি: {amount - balance} TK\n\nকম পরিমাণ লিখুন:"
            msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup()) 
            bot.register_next_step_handler(msg, process_withdraw_amount); return 
        
        # 9. Database-e balance update kora hocche (hold e neya)
        update_user(user_id, {
            "$inc": {
                "balance": -amount,
                "hold": amount
            }
        })
        
        method_msg = "📲 উত্তোলনের মাধ্যম নির্বাচন করুন:"
        msg = bot.send_message(message.chat.id, method_msg, reply_markup=withdraw_method_markup()) 
        bot.register_next_step_handler(msg, lambda m: process_withdraw_method(m, amount))
    except Exception as e:
        print(f"Withdraw amount error: {e}")
        error_msg = f"❌ অবৈধ পরিমাণ! শুধুমাত্র সংখ্যা লিখুন:\n\nউদাহরণ: {MIN_WITHDRAW}, 100, 200\n\nআবার চেষ্টা করুন:"
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, process_withdraw_amount)

def process_withdraw_method(message, amount):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        user_id = str(message.from_user.id)
        # 9. Hold theke balance ferot deya hocche
        update_user(user_id, {
            "$inc": {
                "balance": amount,
                "hold": -amount
            }
        })
        return home_menu(message.chat.id)
        
    valid_methods = ["📲 Bkash", "📲 Nagad", "🪙 Binance", "🅿️ Payer"]
    if message.text not in valid_methods:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"; 
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=withdraw_method_markup())
        bot.register_next_step_handler(msg, lambda m: process_withdraw_method(m, amount)); return
        
    method_name = message.text.split(" ")[-1] # Bkash, Nagad, Binance, Payer
    
    if method_name in ["Bkash", "Nagad"]:
        number_msg = f"📱 আপনার {method_name} নম্বর লিখুন (01XXXXXXXXX):"
    elif method_name == "Binance":
        number_msg = "🪙 আপনার Binance ID (Email/Phone/Pay ID) লিখুন:"
    elif method_name == "Payer":
        number_msg = "🅿️ আপনার Payer Wallet ID (e.g., P12345678) লিখুন:"
    else:
        number_msg = "📱 আপনার একাউন্ট নম্বর লিখুন:"

    msg = bot.send_message(message.chat.id, number_msg, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_withdraw_request(m, amount, method_name))

def confirm_withdraw_request(message, amount, method):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        user_id = str(message.from_user.id)
        # 9. Hold theke balance ferot deya hocche
        update_user(user_id, {
            "$inc": {
                "balance": amount,
                "hold": -amount
            }
        })
        return home_menu(message.chat.id)
        
    account_details = message.text.strip()
    user_id = str(message.from_user.id)
    
    # Validation
    if method in ["Bkash", "Nagad"] and (not account_details.isdigit() or len(account_details) != 11 or not account_details.startswith('01')):
        error_msg = "❌ অবৈধ ফোন নম্বর! ১১ ডিজিটের সঠিক নম্বর লিখুন (যেমন: 01XXXXXXXXX):"; 
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, lambda m: confirm_withdraw_request(m, amount, method)); return
    elif method == "Payer" and (not account_details.startswith('P') or not account_details[1:].isdigit() or len(account_details) < 8):
        error_msg = "❌ অবৈধ Payer ID! সঠিক ID লিখুন (e.g., P12345678):";
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, lambda m: confirm_withdraw_request(m, amount, method)); return
    elif len(account_details) < 4:
         error_msg = "❌ একাউন্ট বিবরণী খুবই ছোট। দয়া করে সঠিক তথ্য দিন:";
         msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
         bot.register_next_step_handler(msg, lambda m: confirm_withdraw_request(m, amount, method)); return
         
    # Fee Calculation
    fee = 0
    if amount > WITHDRAW_FEE_THRESHOLD:
        fee = WITHDRAW_FEE
    final_amount_to_pay = amount - fee
    
    markup = types.InlineKeyboardMarkup()
    withdraw_id = f"WD{int(time.time())}{user_id}"
    
    # 10. Order database-e save kora hocche
    order_data = {
        "_id": withdraw_id,
        "user_id": user_id, 
        "service": "Withdrawal", 
        "amount": amount, 
        "fee": fee,
        "final_amount": final_amount_to_pay,
        "method": method, 
        "account": account_details, 
        "status": "pending",
        "timestamp": time.time()
    }
    create_order(order_data)
    
    markup.add(types.InlineKeyboardButton("✅ Pay (Funds are on hold)", callback_data=f"pay_{user_id}_{amount}_{withdraw_id}"))
    
    user = get_user(user_id) # Updated balance paoar jonno
    
    admin_msg = f"""
💸 নতুন উত্তোলনের অনুরোধ:

📋 Withdrawal ID: {withdraw_id}
👤 User: @{user.get('username', 'N/A')}
🆔 User ID: {user_id}
💰 Amount: {amount} TK
💸 Fee: {fee} TK
💵 To Pay: {final_amount_to_pay} TK
💳 Method: {method}
📞 Account: {account_details}
⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}

💡 User Balance (After Hold): {user['balance']} TK
"""
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
    
    user_confirmation = f"""
✅ আপনার উত্তোলনের অনুরোধ পাঠানো হয়েছে!

📋 Withdrawal ID: {withdraw_id}
💰 Amount: {amount} TK
💸 Fee: {fee} TK
💵 Amount to Receive: {final_amount_to_pay} TK
💳 Method: {method}
📞 Account: {account_details}

⏳ Admin অনুমোদন করলে ১-১২ ঘন্টার মধ্যে টাকা পাঠানো হবে।
সেবা নেওয়ার জন্য ধন্যবাদ! 🙏
"""
    bot.send_message(message.chat.id, user_confirmation)
    home_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "👥 Refer")
def refer(message):
    user_id = str(message.from_user.id)
    
    # 1. Database theke user-er data ana hocche
    user = get_user(user_id)
    if not user or user.get("is_blocked"): return
    
    ref_count = user["referral_count"]
    ref_earnings = ref_count * 2
    ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    refer_msg = f"""
📢 রেফার প্রোগ্রাম:

🔗 আপনার রেফার লিংক:
`{ref_link}`
(Click to copy)

🎉 প্রতিটি রেফারেলের জন্য পাবেন ২ টাকা
💰 মোট উপার্জন: {ref_earnings} TK
👥 আপনার রেফার্ড ইউজার: {ref_count} জন

⚠️ সতর্কবার্তা:
ফেক/ বট রেফারেল করার চেষ্টা করলে আপনার একাউন্ট ব্লক করা হতে পারে এবং কোনো পেমেন্ট করা হবে না।

💡 রেফার লিংক শেয়ার করার টিপস:
1. Facebook গ্রুপে শেয়ার করুন
2. WhatsApp/Telegram গ্রুপে শেয়ার করুন
3. বন্ধুদের সাথে শেয়ার করুন

বন্ধুদের সাথে শেয়ার করুন এবং টাকা উপার্জন করুন! 🎊
"""
    bot.send_message(message.chat.id, refer_msg, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🆘 Support")
def support(message):
    user = get_user(message.from_user.id)
    if not user or user.get("is_blocked"): return
    support_msg = f"""
🆘 সাপোর্ট সেন্টার:

যেকোনো সমস্যা বা প্রশ্নের জন্য নিচের তথ্য ব্যবহার করে যোগাযোগ করুন:

📞 জরুরী যোগাযোগ:
- Admin: @{ADMIN_USERNAME}
- Phone: {ADMIN_BKASH_NO} (WhatsApp/IMO)

⏰ সাপোর্ট সময়:
- সকাল ১০টা - রাত ১০টা
- ৭ দিন সাপোর্ট

📋 সাধারণ সমস্যার সমাধান:
1. অর্ডার না পেলে - Admin কে মেসেজ করুন
2. টাকা পাঠিয়েছেন কিন্তু ব্যালেন্স আপডেট হয়নি - Txn ID সহ মেসেজ করুন
3. Gmail টাস্ক রিজেক্ট হলে - কারণ দেখুন এবং আবার চেষ্টা করুন

💡 দ্রুত সাপোর্ট পেতে:
- আপনার User ID: {message.from_user.id}
- অর্ডার/ট্রানজেকশন ID দিয়ে মেসেজ করুন

আমরা আপনাকে সাহায্য করতে পেরে আনন্দিত! 🙏
"""
    bot.send_message(message.chat.id, support_msg)
# --- End of Standard Flows ---


# ----------------------------------------------------
# --- Admin Panel (Button System) (MODIFIED for DB) ---
# ----------------------------------------------------

def admin_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📊 স্ট্যাটাস", "💰 ব্যালেন্স ম্যানেজ")
    markup.add("👤 ইউজার/ব্রডকাস্ট", "🚫 ব্লক/আনব্লক")
    markup.add("📧 Gmail টাস্ক ম্যানেজ", "📦 স্টক ম্যানেজ")
    markup.add("↩️ মেনুতে ফিরে যান")
    return markup

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ আপনার অনুমতি নেই!")
        return
    
    bot.clear_step_handler(message)

    # 15. Database theke statistics ana hocche
    stats = get_bot_stats()

    admin_msg = f"""
👑 অ্যাডমিন প্যানেল:

📊 স্ট্যাটিস্টিক্স (সারসংক্ষেপ):
👥 মোট ইউজার: {stats['total_users']}
💰 মোট ব্যালেন্স: {stats['total_balance']} TK
⏳ মোট Hold: {stats['total_hold']} TK
📧 Pending Gmail Submissions: {stats['total_pending_gmails']} টি
📋 Available Gmail Tasks: {stats['total_available_tasks']} টি
🏃 Active Gmail Tasks: {stats['total_active_tasks']} টি

🛠️ নিচের অপশনগুলো থেকে আপনার কাজ নির্বাচন করুন:
"""
    bot.send_message(message.chat.id, admin_msg, reply_markup=admin_markup())
    bot.register_next_step_handler(message, handle_admin_menu)

def handle_admin_menu(message):
    """Routes Admin menu button presses."""
    chat_id = message.chat.id
    if str(chat_id) != ADMIN_ID: return

    text = message.text
    
    if text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(chat_id)
    
    elif text == "📊 স্ট্যাটাস":
        return admin_show_stats(message)

    elif text == "💰 ব্যালেন্স ম্যানেজ":
        return admin_manage_balance_start(message)

    elif text == "👤 ইউজার/ব্রডকাস্ট":
        return admin_user_broadcast_menu(message)

    elif text == "🚫 ব্লক/আনব্লক":
        return admin_block_user_start(message)
        
    elif text == "📧 Gmail টাস্ক ম্যানেজ":
        return admin_gmail_task_menu(message)
        
    elif text == "📦 স্টক ম্যানেজ":
        return admin_stock_menu(message) # New

    else:
        admin_msg = "❌ অবৈধ নির্বাচন। নিচের মেনু থেকে নির্বাচন করুন:"
        bot.send_message(chat_id, admin_msg, reply_markup=admin_markup())
        bot.register_next_step_handler(message, handle_admin_menu)

# --- Admin Sub-Menu Handlers (MODIFIED for DB) ---

def admin_show_stats(message):
    """Handles the '📊 স্ট্যাটাস' button"""
    # 15. Database theke statistics ana hocche
    stats = get_bot_stats()
    
    total_earnings = stats['total_balance'] + stats['total_hold']
    total_ref_earnings = stats['total_ref_earnings']
    total_gmail_earnings = total_earnings - total_ref_earnings
    total_users = stats['total_users']
    
    stats_msg = f"""
📈 বিস্তারিত স্ট্যাটিস্টিক্স:

💰 মোট আয় (All Time): {total_earnings} TK
📧 Gmail, Buy/Sell, Other: {total_gmail_earnings} TK
👥 রেফার থেকে: {total_ref_earnings} TK

📊 ইউজার এক্টিভিটি:
- মোট ইউজার: {total_users}
- গড় ব্যালেন্স: {total_earnings/total_users if total_users > 0 else 0:.2f} TK/User
- গড় রেফার: {stats['total_ref_earnings']/(2*total_users) if total_users > 0 else 0:.2f}/User
"""
    bot.send_message(message.chat.id, stats_msg)
    bot.send_message(message.chat.id, "🛠️ পরবর্তী অপশন নির্বাচন করুন:", reply_markup=admin_markup())
    bot.register_next_step_handler(message, handle_admin_menu)

def admin_user_broadcast_menu(message):
    """Handles the '👤 ইউজার/ব্রডকাস্ট' button"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("👤 ইউজার তালিকা", "📢 ব্রডকাস্ট মেসেজ")
    markup.add("📨 নির্দিষ্ট ইউজারকে মেসেজ", "⬅️ অ্যাডমিন মেনু")
    bot.send_message(message.chat.id, "👤 ইউজার ও মেসেজ ম্যানেজমেন্ট:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_user_broadcast_menu)

def handle_user_broadcast_menu(message):
    """Routes Admin User/Broadcast menu button presses."""
    chat_id = message.chat.id
    if str(chat_id) != ADMIN_ID: return

    text = message.text
    
    if text == "⬅️ অ্যাডমিন মেনু":
        return admin_panel(message) 

    elif text == "👤 ইউজার তালিকা":
        return admin_list_users(message)

    elif text == "📢 ব্রডকাস্ট মেসেজ":
        return admin_broadcast(message)

    elif text == "📨 নির্দিষ্ট ইউজারকে মেসেজ":
        return admin_notify_user(message)

    else:
        admin_msg = "❌ অবৈধ নির্বাচন। নিচের মেনু থেকে নির্বাচন করুন:"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("👤 ইউজার তালিকা", "📢 ব্রডকাস্ট মেসেজ", "📨 নির্দিষ্ট ইউজারকে মেসেজ", "⬅️ অ্যাডমিন মেনু")
        bot.send_message(chat_id, admin_msg, reply_markup=markup)
        bot.register_next_step_handler(message, handle_user_broadcast_menu)

def admin_list_users(message):
    """Lists users and gives option to download all users."""
    
    # 16. Database theke 10 jon user-er list ana hocche
    users_list = ""
    for u in users_db.find().limit(10).sort("joined_date", -1): # Notun 10 jon
        users_list += f"👤 @{u.get('username', 'N/A')} | ID: {u['_id']} | Bal: {u.get('balance', 0)} TK\n"
        
    users_msg = f"👥 সর্বশেষ ১০ ইউজার:\n\n{users_list}\n\n💡 সকল ইউজার ডাউনলোড করতে নিচের বাটনটি ব্যবহার করুন:"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬇️ সকল ইউজার ডাউনলোড (.txt)", callback_data="download_all_users"))
    
    bot.send_message(message.chat.id, users_msg, reply_markup=markup)
    
    # Return to User/Broadcast menu
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("👤 ইউজার তালিকা", "📢 ব্রডকাস্ট মেসেজ", "📨 নির্দিষ্ট ইউজারকে মেসেজ", "⬅️ অ্যাডমিন মেনু")
    bot.send_message(message.chat.id, "👤 ইউজার ম্যানেজমেন্ট:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_user_broadcast_menu)


@bot.callback_query_handler(func=lambda call: call.data == "download_all_users" and str(call.from_user.id) == ADMIN_ID)
def download_all_users_callback(call):
    """Handles the download user list callback."""
    chat_id = call.message.chat.id
    
    try:
        # 17. Database theke shob user-er list ana hocche
        all_users = get_all_users_list()
        
        with open("users.txt", "w", encoding="utf-8") as f:
            for u in all_users:
                status = "BLOCKED" if u.get('is_blocked') else "Active"
                f.write(f"ID: {u['_id']} | User: @{u.get('username', 'N/A')} | Bal: {u.get('balance', 0)} TK | Hold: {u.get('hold', 0)} TK | Ref: {u.get('referral_count', 0)} | Joined: {u.get('joined_date', 'N/A')} | Status: {status}\n")
        
        with open("users.txt", "rb") as f:
            bot.send_document(chat_id, f, caption="📊 সকল ইউজারের তালিকা")
        
        bot.answer_callback_query(call.id, "✅ ফাইল পাঠানো হয়েছে!")
    except Exception as e:
        bot.send_message(chat_id, f"❌ ফাইল পাঠাতে ত্রুটি: {e}")
        bot.answer_callback_query(call.id, "❌ ত্রুটি!")
    
    # File send korar por o menu-te ferot jabe
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("👤 ইউজার তালিকা", "📢 ব্রডকাস্ট মেসেজ", "📨 নির্দিষ্ট ইউজারকে মেসেজ", "⬅️ অ্যাডমিন মেনু")
    bot.send_message(chat_id, "👤 ইউজার ম্যানেজমেন্ট:", reply_markup=markup)
    bot.register_next_step_handler(call.message, handle_user_broadcast_menu)


def admin_broadcast(message):
    """Starts the broadcast flow."""
    msg = bot.send_message(message.chat.id, "📢 ব্রডকাস্ট মেসেজ পাঠাতে চান? একটি ছবিসহ ক্যাপশন লিখে পাঠান। শুধু টেক্সট পাঠাতে চাইলে সরাসরি মেসেজ লিখুন।", reply_markup=back_markup())
    bot.register_next_step_handler(msg, send_broadcast)

def admin_notify_user(message):
    """Starts the notify user flow."""
    msg = bot.send_message(message.chat.id, "👤 ইউজার ID লিখুন যাকে মেসেজ পাঠাতে চান:", reply_markup=back_markup())
    bot.register_next_step_handler(msg, get_notify_message)

def admin_manage_balance_start(message):
    """Handles the '💰 ব্যালেন্স ম্যানেজ' button"""
    msg = bot.send_message(message.chat.id, "👤 ব্যালেন্স পরিবর্তন করতে চান? ইউজার ID লিখুন:", reply_markup=back_markup())
    bot.register_next_step_handler(msg, get_balance_user_id)

def admin_block_user_start(message):
    """Handles the '🚫 ব্লক/আনব্লক' button"""
    msg = bot.send_message(message.chat.id, "🚫 ব্লক/আনব্লক করতে চান? ইউজার ID লিখুন:", reply_markup=back_markup())
    bot.register_next_step_handler(msg, get_block_user_id)


# --- Admin Gmail Task Management Menu (MODIFIED for DB) ---
def admin_gmail_task_menu(message):
    """Handles the '📧 Gmail টাস্ক ম্যানেজ' button"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("➕ নতুন টাস্ক যোগ করুন", "📋 অ্যাভেইলেবল টাস্ক দেখুন")
    markup.add("🗑️ টাস্ক ডিলিট করুন", "⬅️ অ্যাডমিন মেনু")
    bot.send_message(message.chat.id, "📧 Gmail টাস্ক ম্যানেজমেন্ট:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_gmail_task_menu)

def handle_gmail_task_menu(message):
    """Routes Admin Gmail Task menu button presses."""
    chat_id = message.chat.id
    if str(chat_id) != ADMIN_ID: return

    text = message.text
    
    if text == "⬅️ অ্যাডমিন মেনু":
        return admin_panel(message) 

    elif text == "➕ নতুন টাস্ক যোগ করুন":
        return admin_add_gmail_task_start(message)

    elif text == "📋 অ্যাভেইলেবল টাস্ক দেখুন":
        return admin_list_gmail_tasks_action(message)

    elif text == "🗑️ টাস্ক ডিলিট করুন":
        return admin_remove_gmail_task_start(message)

    else:
        admin_msg = "❌ অবৈধ নির্বাচন। নিচের মেনু থেকে নির্বাচন করুন:"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("➕ নতুন টাস্ক যোগ করুন", "📋 অ্যাভেইলেবল টাস্ক দেখুন", "🗑️ টাস্ক ডিলিট করুন", "⬅️ অ্যাডমিন মেনু")
        bot.send_message(chat_id, admin_msg, reply_markup=markup)
        bot.register_next_step_handler(message, handle_gmail_task_menu)

# --- Admin Stock Management Menu (MODIFIED for DB) ---
def admin_stock_menu(message):
    """Handles the '📦 স্টক ম্যানেজ' button"""
    chat_id = message.chat.id
    
    # 14. Stock database theke check kora hocche
    current_stock = get_stock()
    
    def get_status_text(key):
        return "🚫 Out" if current_stock.get(key, -1) == 0 else "✅ In"

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton(f"USA Gmail: {get_status_text('gmail_usa')}", callback_data="stock_toggle_gmail_usa"),
        types.InlineKeyboardButton(f"BD Gmail: {get_status_text('gmail_bd')}", callback_data="stock_toggle_gmail_bd")
    )
    markup.add(
        types.InlineKeyboardButton(f"Play Point: {get_status_text('play_point')}", callback_data="stock_toggle_play_point"),
        types.InlineKeyboardButton(f"Crunchyroll: {get_status_text('crunchyroll_7_day')}", callback_data="stock_toggle_crunchyroll_7_day")
    )
    markup.add(
        types.InlineKeyboardButton(f"YT 1 Month: {get_status_text('yt_1_month')}", callback_data="stock_toggle_yt_1_month"),
        types.InlineKeyboardButton(f"YT 1 Year: {get_status_text('yt_1_year')}", callback_data="stock_toggle_yt_1_year")
    )
    markup.add(
        types.InlineKeyboardButton(f"Veo 1 Month: {get_status_text('veo_1_month')}", callback_data="stock_toggle_veo_1_month"),
        types.InlineKeyboardButton(f"Veo 12 Month: {get_status_text('veo_12_month')}", callback_data="stock_toggle_veo_12_month")
    )
    markup.add(
        types.InlineKeyboardButton(f"NordVPN: {get_status_text('vpn_nord')}", callback_data="stock_toggle_vpn_nord"),
        types.InlineKeyboardButton(f"ExpressVPN: {get_status_text('vpn_express')}", callback_data="stock_toggle_vpn_express")
    )
    markup.add(
        types.InlineKeyboardButton(f"HMA VPN: {get_status_text('vpn_hma')}", callback_data="stock_toggle_vpn_hma"),
        types.InlineKeyboardButton(f"PIA VPN: {get_status_text('vpn_pia')}", callback_data="stock_toggle_vpn_pia")
    )
    markup.add(
        types.InlineKeyboardButton(f"Ipvanis VPN: {get_status_text('vpn_ipvanis')}", callback_data="stock_toggle_vpn_ipvanis")
    )
    
    bot.send_message(chat_id, "📦 সার্ভিস স্টক ম্যানেজমেন্ট:\nবাটন চেপে স্টক টগল করুন (In/Out)।", reply_markup=markup)
    
    # Return to main admin menu
    bot.send_message(chat_id, "🛠️ পরবর্তী অপশন নির্বাচন করুন:", reply_markup=admin_markup())
    bot.register_next_step_handler(message, handle_admin_menu)
    

# ----------------------------------------------------
# --- Admin Step Handlers (MODIFIED for DB) ---
# ----------------------------------------------------

def admin_add_gmail_task_start(message):
    """Starts the flow to add new Gmail tasks."""
    prompt = """
📧 নতুন Gmail টাস্ক যোগ করুন:

নিচের ফরম্যাটে টাস্কগুলো লিখুন (প্রতি লাইনে একটি):
`email:password:firstname:lastname`
`email:password:firstname` (Last name ঐচ্ছিক)

উদাহরণ:
task1@gmail.com:Pass123:John:Doe
task2@gmail.com:Pass456:Jane
"""
    msg = bot.send_message(message.chat.id, prompt, parse_mode="Markdown", reply_markup=back_markup())
    bot.register_next_step_handler(msg, process_new_gmail_task)

def process_new_gmail_task(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return admin_panel(message) 

    tasks_added = 0
    tasks_failed = 0
    failed_lines = []
    
    lines = message.text.strip().split('\n')
    
    for line in lines:
        try:
            parts = line.strip().split(':')
            if len(parts) < 3: # Kompokkhe 3 part (email:pass:fname)
                raise ValueError("Invalid format")
            
            email = parts[0].strip()
            password = parts[1].strip()
            fname = parts[2].strip()
            lname = parts[3].strip() if len(parts) > 3 and parts[3].strip() else "✖️"
            
            if not email or not password or not fname:
                raise ValueError("Missing required fields")

            task_id = str(uuid.uuid4())[:8]
            new_task = {
                # "_id" database nijei toiri korbe
                "id": task_id, "email": email, "password": password,
                "fname": fname, "lname": lname
            }
            
            # 18. Task database-e jog kora hocche
            if add_new_task(new_task):
                tasks_added += 1
            else:
                raise ValueError("Duplicate task")
            
        except Exception as e:
            tasks_failed += 1
            failed_lines.append(f"{line} (Reason: {e})")

    # ☢️ save_data() ar nei
    
    response = f"✅ {tasks_added} টি টাস্ক সফলভাবে যোগ করা হয়েছে।"
    if tasks_failed > 0:
        response += f"\n❌ {tasks_failed} টি টাস্ক যোগ করা যায়নি:\n" + "\n".join(failed_lines)
    
    bot.send_message(message.chat.id, response)
    
    # Return to the task menu
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("➕ নতুন টাস্ক যোগ করুন", "📋 অ্যাভেইলেবল টাস্ক দেখুন", "🗑️ টাস্ক ডিলিট করুন", "⬅️ অ্যাডমিন মেনু")
    bot.send_message(message.chat.id, "📧 টাস্ক ম্যানেজমেন্ট:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_gmail_task_menu)

def admin_list_gmail_tasks_action(message):
    """Action to list gmail tasks."""
    
    # 12. Database theke available task khuja hocche
    available_tasks_list = get_available_tasks()
    
    if not available_tasks_list:
        bot.send_message(message.chat.id, "📋 কোনো অ্যাভেইলেবল Gmail টাস্ক নেই।")
    else:
        response = "📋 অ্যাভেইলেবল Gmail টাস্ক তালিকা:\n\n"
        for i, task in enumerate(available_tasks_list[:50]): # Prothom 50-ti dekhabe
            response += f"{i+1}. {task['email']} | {task['fname']} {task['lname']}\n"
        
        if len(available_tasks_list) > 50:
            response += f"\n...ebong aro {len(available_tasks_list) - 50} টি টাস্ক।"

        if len(response) > 4096:
            bot.send_message(message.chat.id, response[:4090] + "\n...") # Limit handle
        else:
            bot.send_message(message.chat.id, response)
    
    # Return to the task menu
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("➕ নতুন টাস্ক যোগ করুন", "📋 অ্যাভেইলেবল টাস্ক দেখুন", "🗑️ টাস্ক ডিলিট করুন", "⬅️ অ্যাডমিন মেনু")
    bot.send_message(message.chat.id, "📧 টাস্ক ম্যানেজমেন্ট:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_gmail_task_menu)

def admin_remove_gmail_task_start(message):
    """Starts the flow to remove a Gmail task."""
    msg = bot.send_message(message.chat.id, "🗑️ ডিলিট করতে চান? টাস্কটির Email লিখুন:", reply_markup=back_markup())
    bot.register_next_step_handler(msg, process_remove_gmail_task)

def process_remove_gmail_task(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return admin_panel(message) 
        
    email_to_remove = message.text.strip()
    
    # 19. Database theke task delete kora hocche
    if remove_task_by_email(email_to_remove):
        bot.send_message(message.chat.id, f"✅ টাস্ক '{email_to_remove}' সফলভাবে ডিলিট করা হয়েছে।")
    else:
        bot.send_message(message.chat.id, f"❌ টাস্ক '{email_to_remove}' অ্যাভেইলেবল লিস্টে খুঁজে পাওয়া যায়নি।")
    
    # Return to the task menu
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("➕ নতুন টাস্ক যোগ করুন", "📋 অ্যাভেইলেবল টাস্ক দেখুন", "🗑️ টাস্ক ডিলিট করুন", "⬅️ অ্যাডমিন মেনু")
    bot.send_message(message.chat.id, "📧 টাস্ক ম্যানেজমেন্ট:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_gmail_task_menu)


# Balance Management Flow (MODIFIED for DB)
def get_balance_user_id(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return admin_panel(message)
    user_id_to_manage = str(message.text).strip()
    
    # 1. Database theke user-er data ana hocche
    user_data = get_user(user_id_to_manage)
    
    if not user_data or "username" not in user_data: # Check if it's a real user
        msg = bot.send_message(message.chat.id, "❌ এই ইউজার ID খুঁজে পাওয়া যায়নি! আবার চেষ্টা করুন:", reply_markup=back_markup())
        bot.register_next_step_handler(msg, get_balance_user_id); return
        
    refer_earnings = user_data.get("referral_count", 0) * 2
    balance_info = f"""
✅ ইউজার পাওয়া গেছে: @{user_data.get('username', 'N/A')}
🆔 ID: {user_id_to_manage}

💰 বর্তমান ব্যালেন্স:
💵 Main Balance: {user_data.get('balance', 0)} TK
⏳ Hold Balance: {user_data.get('hold', 0)} TK
👥 Referral Count: {user_data.get('referral_count', 0)} জন
📈 Referral Earnings: {refer_earnings} TK

কোন ব্যালেন্স পরিবর্তন করতে চান?
"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3); markup.add("💵 Main Balance", "⏳ Hold Balance", "👥 Referral Count"); markup.add("↩️ মেনুতে ফিরে যান")
    admin_sessions[message.chat.id] = {"manage_user_id": user_id_to_manage}
    msg = bot.send_message(message.chat.id, balance_info, reply_markup=markup)
    bot.register_next_step_handler(msg, select_balance_type)

def select_balance_type(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        if message.chat.id in admin_sessions: del admin_sessions[message.chat.id]
        bot.clear_step_handler(message); return admin_panel(message)
    balance_type = message.text; valid_types = ["💵 Main Balance", "⏳ Hold Balance", "👥 Referral Count"]
    if balance_type not in valid_types:
        msg = bot.send_message(message.chat.id, "❌ অবৈধ নির্বাচন। আবার চেষ্টা করুন:", reply_markup=back_markup())
        bot.register_next_step_handler(msg, select_balance_type); return
    admin_sessions[message.chat.id]["balance_type"] = balance_type
    prompt = f"💡 {balance_type} পরিবর্তন করার জন্য পরিমাণ লিখুন:\n\nপদ্ধতি:\n- যোগ করতে: +10\n- বিয়োগ করতে: -5\n- সরাসরি নতুন মান সেট করতে: 100 (শুধু সংখ্যা)\n\nউদাহরণ: +10 অথবা 50 (যদি আপনি চান নতুন মান 50 হোক)"
    msg = bot.send_message(message.chat.id, prompt, reply_markup=back_markup())
    bot.register_next_step_handler(msg, apply_balance_change)

def apply_balance_change(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        if message.chat.id in admin_sessions: del admin_sessions[message.chat.id]
        bot.clear_step_handler(message); return admin_panel(message)
    chat_id = message.chat.id
    if chat_id not in admin_sessions or "manage_user_id" not in admin_sessions[chat_id]:
        bot.send_message(chat_id, "❌ সেশন এক্সপায়ার্ড! আবার 💰 ব্যালেন্স ম্যানেজ বাটনটি ব্যবহার করুন."); return admin_panel(chat_id)
    
    user_id_to_manage = admin_sessions[chat_id]["manage_user_id"]; balance_type = admin_sessions[chat_id]["balance_type"]
    change_input = message.text.strip()
    try:
        balance_key = ""
        if balance_type == "💵 Main Balance": balance_key = "balance"
        elif balance_type == "⏳ Hold Balance": balance_key = "hold"
        elif balance_type == "👥 Referral Count": balance_key = "referral_count"
        
        # 1. Database theke user-er data ana hocche
        user_data = get_user(user_id_to_manage)
        current_value = user_data.get(balance_key, 0)
        
        update_doc = {}
        change_type = ""
        new_value = 0
        
        if change_input.startswith('+') or change_input.startswith('-'):
            change_amount = int(change_input); 
            # 20. Database-e $inc diye update kora hocche
            update_doc = {"$inc": {balance_key: change_amount}}
            new_value = current_value + change_amount
            change_type = "পরিবর্তন"
        else:
            new_value = int(change_input); 
            # 20. Database-e $set diye update kora hocche
            update_doc = {"$set": {balance_key: new_value}}
            change_type = "সেট"
            
        if new_value < 0:
            new_value = 0
            update_doc = {"$set": {balance_key: 0}} # Negative hote dibe na
            
        update_user(user_id_to_manage, update_doc)
        
        if balance_key in ["balance", "hold"]:
            bot.send_message(user_id_to_manage, f"🎉 Admin আপনার একাউন্টের {balance_type} {change_type} করেছেন।\n\n💰 নতুন ব্যালেন্স: {new_value} TK")
        elif balance_key == "referral_count":
            bot.send_message(user_id_to_manage, f"🎉 Admin আপনার একাউন্টের Referral Count {change_type} করেছেন।\n\n👥 নতুন Referral Count: {new_value} জন")
        
        admin_confirmation = f"✅ সফলভাবে পরিবর্তন করা হয়েছে!\n\n👤 ইউজার: @{user_data.get('username', 'N/A')}\n🔄 টাইপ: {balance_type}\nOld Value: {current_value}\nNew Value: {new_value}"
        bot.send_message(chat_id, admin_confirmation)
        
    except ValueError:
        msg = bot.send_message(chat_id, "❌ অবৈধ পরিমাণ! শুধুমাত্র সংখ্যা, +সংখ্যা অথবা -সংখ্যা লিখুন। আবার চেষ্টা করুন:", reply_markup=back_markup())
        bot.register_next_step_handler(msg, apply_balance_change); return
    except Exception as e:
        bot.send_message(chat_id, f"❌ একটি অজানা ত্রুটি হয়েছে: {e}")
    if chat_id in admin_sessions: del admin_sessions[chat_id]
    
    bot.send_message(chat_id, "🛠️ পরবর্তী অপশন নির্বাচন করুন:", reply_markup=admin_markup())
    bot.register_next_step_handler(message, handle_admin_menu)


# Block/Unblock Flow (MODIFIED for DB)
def get_block_user_id(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return admin_panel(message)
    user_id_to_block = str(message.text).strip()
    
    # 1. Database theke user-er data ana hocche
    user_data = get_user(user_id_to_block)
    
    if not user_data or "username" not in user_data:
        msg = bot.send_message(message.chat.id, "❌ এই ইউজার ID খুঁজে পাওয়া যায়নি! আবার চেষ্টা করুন:", reply_markup=back_markup())
        bot.register_next_step_handler(msg, get_block_user_id); return
        
    current_status = "ব্লকড" if user_data.get("is_blocked") else "আনব্লকড"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2); markup.add("🚫 ব্লক করুন", "✅ আনব্লক করুন"); markup.add("↩️ মেনুতে ফিরে যান")
    prompt = f"✅ ইউজার পাওয়া গেছে: @{user_data.get('username', 'N/A')}\n🆔 ID: {user_id_to_block}\n💡 বর্তমান স্ট্যাটাস: {current_status}\n\nআপনি কি করতে চান?"
    admin_sessions[message.chat.id] = {"block_user_id": user_id_to_block}
    msg = bot.send_message(message.chat.id, prompt, reply_markup=markup)
    bot.register_next_step_handler(msg, block_user_action)

def block_user_action(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        if message.chat.id in admin_sessions: del admin_sessions[message.chat.id]
        bot.clear_step_handler(message); return admin_panel(message)
    chat_id = message.chat.id
    if chat_id not in admin_sessions or "block_user_id" not in admin_sessions[chat_id]:
        bot.send_message(chat_id, "❌ সেশন এক্সপায়ার্ড! আবার 🚫 ব্লক/আনব্লক বাটনটি ব্যবহার করুন."); return admin_panel(chat_id)
    
    user_id_to_block = admin_sessions[chat_id]["block_user_id"]; action = message.text
    user_data = get_user(user_id_to_block)
    
    if action == "🚫 ব্লক করুন":
        # 21. Database-e user-ke block kora hocche
        update_user(user_id_to_block, {"$set": {"is_blocked": True}})
        bot.send_message(user_id_to_block, f"❌ দুঃখিত! Admin কর্তৃক আপনাকে এই বট ব্যবহার থেকে ব্লক করা হয়েছে। Admin এর সাথে যোগাযোগ করুন: @{ADMIN_USERNAME}")
        admin_msg = f"✅ ইউজার @{user_data.get('username', 'N/A')} ({user_id_to_block}) কে সফলভাবে ব্লক করা হয়েছে।"
    elif action == "✅ আনব্লক করুন":
        # 21. Database-e user-ke unblock kora hocche
        update_user(user_id_to_block, {"$set": {"is_blocked": False}})
        bot.send_message(user_id_to_block, "✅ Admin কর্তৃক আপনাকে আনব্লক করা হয়েছে! আপনি এখন বট ব্যবহার করতে পারবেন।")
        admin_msg = f"✅ ইউজার @{user_data.get('username', 'N/A')} ({user_id_to_block}) কে সফলভাবে আনব্লক করা হয়েছে।"
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2); markup.add("🚫 ব্লক করুন", "✅ আনব্লক করুন"); markup.add("↩️ মেনুতে ফিরে যান")
        msg = bot.send_message(chat_id, "❌ অবৈধ নির্বাচন। আবার চেষ্টা করুন:", reply_markup=markup)
        bot.register_next_step_handler(msg, block_user_action); return
        
    bot.send_message(chat_id, admin_msg)
    if chat_id in admin_sessions: del admin_sessions[chat_id]
    
    bot.send_message(chat_id, "🛠️ পরবর্তী অপশন নির্বাচন করুন:", reply_markup=admin_markup())
    bot.register_next_step_handler(message, handle_admin_menu)

# Broadcast Flow (MODIFIED for DB)
def send_broadcast(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return admin_user_broadcast_menu(message)
    success = 0; failed = 0
    broadcast_text = "📢 ব্রডকাস্ট:"
    
    # 22. Database theke efficient-bhabe shob user-er list ana hocche
    users_cursor = get_all_users_cursor()
    
    photo_id = None
    caption = ""
    broadcast_msg = ""
    
    if message.photo:
        photo_id = message.photo[-1].file_id; caption = message.caption or ""
    elif message.text:
        broadcast_msg = message.text
    else:
        bot.send_message(message.chat.id, "❌ শুধুমাত্র টেক্সট অথবা ছবি পাঠানো যাবে।")
        return admin_user_broadcast_menu(message)

    bot.send_message(message.chat.id, f"⏳ ব্রডকাস্ট শুরু হচ্ছে... মোট ইউজার: {users_db.count_documents({'is_blocked': {'$ne': True}})}")
    
    for user in users_cursor:
        try:
            user_id = user["_id"]
            if photo_id:
                bot.send_photo(user_id, photo_id, caption=f"{broadcast_text}\n\n{caption}")
            else:
                bot.send_message(user_id, f"{broadcast_text}\n\n{broadcast_msg}")
            success += 1
        except Exception as e:
            # print(f"Broadcast failed for {user_id}: {e}")
            failed += 1
        time.sleep(0.1) # Flood control
    
    bot.send_message(message.chat.id, f"✅ ব্রডকাস্ট সম্পন্ন!\n\n📊 রেজাল্ট:\n✅ সফল: {success}\n❌ ব্যর্থ: {failed}\n📊 মোট: {success + failed}")
    bot.clear_step_handler(message)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("👤 ইউজার তালিকা", "📢 ব্রডকাস্ট মেসেজ", "📨 নির্দিষ্ট ইউজারকে মেসেজ", "⬅️ অ্যাডমিন মেনু")
    bot.send_message(message.chat.id, "👤 ইউজার ম্যানেজমেন্ট:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_user_broadcast_menu)

# Notify User Flow (MODIFIED for DB)
def get_notify_message(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return admin_user_broadcast_menu(message)
    user_id = str(message.text).strip()
    
    # 1. Database theke user-er data ana hocche
    user = get_user(user_id)
    
    if not user or "username" not in user:
        bot.send_message(message.chat.id, "❌ এই ইউজার ID খুঁজে পাওয়া যায়নি!"); 
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("👤 ইউজার তালিকা", "📢 ব্রডকাস্ট মেসেজ", "📨 নির্দিষ্ট ইউজারকে মেসেজ", "⬅️ অ্যাডমিন মেনু")
        bot.send_message(message.chat.id, "👤 ইউজার ম্যানেজমেন্ট:", reply_markup=markup)
        bot.register_next_step_handler(message, handle_user_broadcast_menu)
        return
        
    msg = bot.send_message(message.chat.id, "💬 মেসেজ পাঠাতে চান? একটি ছবিসহ ক্যাপশন লিখে পাঠান। শুধু টেক্সট পাঠাতে চাইলে সরাসরি মেসেজ লিখুন।", reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: send_notification(m, user_id))

def send_notification(message, user_id):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return admin_user_broadcast_menu(message)
    try:
        if message.photo:
            photo_id = message.photo[-1].file_id; caption = message.caption or ""
            bot.send_photo(user_id, photo_id, caption=f"📨 Admin থেকে মেসেজ:\n\n{caption}")
        elif message.text:
            bot.send_message(user_id, f"📨 Admin থেকে মেসেজ:\n\n{message.text}")
        bot.send_message(message.chat.id, "✅ মেসেজ পাঠানো হয়েছে!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ ইউজারকে মেসেজ পাঠানো যায়নি! Error: {e}")
    bot.clear_step_handler(message)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("👤 ইউজার তালিকা", "📢 ব্রডকাস্ট মেসেজ", "📨 নির্দিষ্ট ইউজারকে মেসেজ", "⬅️ অ্যাডমিন মেনু")
    bot.send_message(message.chat.id, "👤 ইউজার ম্যানেজমেন্ট:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_user_broadcast_menu)


# --- Callback Query Handler (UPDATED for DB) ---

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    # Admin-only actions
    if str(call.from_user.id) == ADMIN_ID:
        # Check for stock toggle first
        if call.data.startswith("stock_toggle_"):
            admin_stock_toggle_callback(call)
            return
        
        # Other admin actions
        if call.data.startswith("approve_") or call.data.startswith("reject_") or call.data.startswith("pay_") or call.data.startswith("deliver_"):
            admin_callback_handler(call)
            return
        
        # Download users
        if call.data == "download_all_users":
            # download_all_users_callback(call) # Already defined with decorator
            return
    
    # User-specific actions
    if call.data.startswith("gmail_task_"):
        user_task_callback_handler(call)

def user_task_callback_handler(call):
    """Handles user-side callbacks like Done/Cancel for tasks."""
    user_id = str(call.from_user.id)
    
    try:
        task_user_id = call.data.split('_')[-1]
        if user_id != task_user_id:
            bot.answer_callback_query(call.id, "❌ এটি আপনার টাস্ক নয়।"); return

        if user_id not in active_gmail_tasks:
            bot.answer_callback_query(call.id, "❌ আপনার টাস্কটি খুঁজে পাওয়া যায়নি বা মেয়াদ শেষ হয়ে গেছে।")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="❌ আপনার টাস্কটি খুঁজে পাওয়া যায়নি বা মেয়াদ শেষ হয়ে গেছে।", reply_markup=None)
            return
            
        task_data = active_gmail_tasks.pop(user_id) # Memory theke remove
        task = task_data['task']
        
        if call.data.startswith("gmail_task_done_"):
            submission_id = str(uuid.uuid4())[:8]
            gmail_str = f"{task['email']}:{task['password']}"
            
            # Pending queue (in-memory)
            pending_gmails[user_id][submission_id] = {
                "gmails": [ { "email": gmail_str, "status": "pending", "task_id": task['_id']} ], # Task ID save
                "timestamp": time.time()
            }
            
            # 23. Task-ke 'pending_approval' hishebe mark kora hocche
            tasks_db.update_one({"_id": task['_id']}, {"$set": {"status": "pending_approval"}})
            
            # 9. Database-e user-er hold balance update kora hocche
            update_user(user_id, {"$inc": {"hold": 7}})
            
            bot.answer_callback_query(call.id, "✅ টাস্ক জমা দেওয়া হয়েছে!")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="✅ টাস্কটি পর্যালোচনার জন্য জমা দেওয়া হয়েছে!\n\nঅ্যাডমিন অ্যাপ্রুভ করলে আপনার অ্যাকাউন্টে ৭ টাকা যোগ হবে।",
                reply_markup=None
            )
            
            # ☢️ save_data() ar nei
            
            username = get_user(user_id).get('username', 'N/A')
            admin_msg = f"📧 নতুন Gmail Submission (Task):\n\n👤 User: @{username}\n🆔 ID: {user_id}\n📅 Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n📋 Submission ID: {submission_id}\n\n👥 মোট Gmail: 1 টি\n💰 সম্ভাব্য Amount: 7 TK"
            bot.send_message(ADMIN_ID, admin_msg)
            
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_gmail_{user_id}_{submission_id}_0"),
                types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_gmail_{user_id}_{submission_id}_0")
            )
            bot.send_message(ADMIN_ID, f"📧 Gmail 1: {gmail_str}", reply_markup=markup)

        elif call.data.startswith("gmail_task_cancel_"):
            # 11. Task-ti database-e ferot pathano hocche
            return_task_to_pool(task)
            # ☢️ save_data() ar nei
            
            bot.answer_callback_query(call.id, "❌ টাস্ক বাতিল করা হয়েছে।")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ টাস্কটি বাতিল করা হয়েছে এবং পুলে ফেরত পাঠানো হয়েছে।",
                reply_markup=None
            )
            
    except Exception as e:
        print(f"Error in user_task_callback_handler: {e}")
        bot.answer_callback_query(call.id, "❌ একটি ত্রুটি হয়েছে।")

def admin_stock_toggle_callback(call):
    """Handles the admin stock toggle inline buttons."""
    try:
        service_key = call.data.replace("stock_toggle_", "")
        
        # 14. Stock database theke check kora hocche
        current_stock = get_stock()
        current_value = current_stock.get(service_key, -1)
        
        # Toggle logic
        new_value = 0 if current_value == -1 else -1
        
        # 24. Database-e stock update kora hocche
        update_stock(service_key, new_value)
            
        bot.answer_callback_query(call.id, f"{service_key} stock updated!")
        
        # Re-draw the stock menu
        new_current_stock = get_stock()
        def get_status_text(key):
            return "🚫 Out" if new_current_stock.get(key, -1) == 0 else "✅ In"

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton(f"USA Gmail: {get_status_text('gmail_usa')}", callback_data="stock_toggle_gmail_usa"),
            types.InlineKeyboardButton(f"BD Gmail: {get_status_text('gmail_bd')}", callback_data="stock_toggle_gmail_bd")
        )
        markup.add(
            types.InlineKeyboardButton(f"Play Point: {get_status_text('play_point')}", callback_data="stock_toggle_play_point"),
            types.InlineKeyboardButton(f"Crunchyroll: {get_status_text('crunchyroll_7_day')}", callback_data="stock_toggle_crunchyroll_7_day")
        )
        markup.add(
            types.InlineKeyboardButton(f"YT 1 Month: {get_status_text('yt_1_month')}", callback_data="stock_toggle_yt_1_month"),
            types.InlineKeyboardButton(f"YT 1 Year: {get_status_text('yt_1_year')}", callback_data="stock_toggle_yt_1_year")
        )
        markup.add(
            types.InlineKeyboardButton(f"Veo 1 Month: {get_status_text('veo_1_month')}", callback_data="stock_toggle_veo_1_month"),
            types.InlineKeyboardButton(f"Veo 12 Month: {get_status_text('veo_12_month')}", callback_data="stock_toggle_veo_12_month")
        )
        markup.add(
            types.InlineKeyboardButton(f"NordVPN: {get_status_text('vpn_nord')}", callback_data="stock_toggle_vpn_nord"),
            types.InlineKeyboardButton(f"ExpressVPN: {get_status_text('vpn_express')}", callback_data="stock_toggle_vpn_express")
        )
        markup.add(
            types.InlineKeyboardButton(f"HMA VPN: {get_status_text('vpn_hma')}", callback_data="stock_toggle_vpn_hma"),
            types.InlineKeyboardButton(f"PIA VPN: {get_status_text('vpn_pia')}", callback_data="stock_toggle_vpn_pia")
        )
        markup.add(
            types.InlineKeyboardButton(f"Ipvanis VPN: {get_status_text('vpn_ipvanis')}", callback_data="stock_toggle_vpn_ipvanis")
        )
        
        bot.edit_message_reply_markup(
            chat_id=call.message.chat.id, 
            message_id=call.message.message_id, 
            reply_markup=markup
        )
    except Exception as e:
        print(f"Error in admin_stock_toggle_callback: {e}")
        bot.answer_callback_query(call.id, "❌ স্টক আপডেট করতে ত্রুটি হয়েছে।")


def admin_callback_handler(call):
    """Handles all other admin-only callbacks."""
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ আপনার অনুমতি নেই!"); return

    data = call.data.split('_')
    action = data[0]
    
    try:
        # 1. Gmail Approval/Rejection
        if action in ["approve", "reject"] and data[1] == "gmail":
            user_id = str(data[2])
            submission_id = str(data[3])
            gmail_index = int(data[4])
            
            if (user_id not in pending_gmails or 
                submission_id not in pending_gmails[user_id] or 
                gmail_index >= len(pending_gmails[user_id][submission_id]["gmails"])):
                bot.answer_callback_query(call.id, "❌ Gmail not found!"); return
            
            submission = pending_gmails[user_id][submission_id]
            gmail_data = submission["gmails"][gmail_index]
            
            if gmail_data["status"] != "pending":
                bot.answer_callback_query(call.id, f"❌ Already {gmail_data['status']}!"); return
            
            gmail = gmail_data["email"]
            task_id = gmail_data.get("task_id") # Task ID ber kora
            
            if action == "approve":
                # 9. Database-e user-er balance/hold update kora hocche
                update_user(user_id, {"$inc": {"hold": -7, "balance": 7}})
                
                pending_gmails[user_id][submission_id]["gmails"][gmail_index]["status"] = "approved"
                
                # 25. Task-ke 'completed' hishebe mark kora
                if task_id:
                    tasks_db.update_one({"_id": task_id}, {"$set": {"status": "completed"}})
                
                current_balance = get_user(user_id)['balance'] # Updated balance
                user_msg = f"✅ আপনার Gmail টাস্কটি অনুমোদিত হয়েছে!\n📧 Gmail: {gmail.split(':')[0]}\n💰 প্রাপ্ত Amount: ৭ টাকা\nআপনার নতুন ব্যালেন্স: {current_balance} TK"
                bot.send_message(user_id, user_msg)
                
                # 10. History database-e save kora hocche
                gsell_order_id = f"GSELL{int(time.time())}{user_id}"
                create_order({
                    "_id": gsell_order_id, "user_id": user_id, "service": "Gmail Sell (Task)",
                    "details": gmail, "price": 7, "status": "approved",
                    "timestamp": time.time()
                })
                
                bot.answer_callback_query(call.id, "✅ Gmail Approved")
                new_text = f"✅ APPROVED: {gmail}"
            
            elif action == "reject":
                # 9. Database-e user-er hold update kora hocche
                update_user(user_id, {"$inc": {"hold": -7}})
                
                pending_gmails[user_id][submission_id]["gmails"][gmail_index]["status"] = "rejected"
                
                # 11. Task-ti database-e ferot pathano hocche
                if task_id:
                    tasks_db.update_one({"_id": task_id}, {"$set": {"status": "available", "user_id": None}})
                
                user_msg = f"❌ আপনার Gmail টাস্কটি রিজেক্ট হয়েছে!\n📧 Gmail: {gmail.split(':')[0]}\nকারণ: অচল Gmail / 2FA / ভুল ফরম্যাট।"
                bot.send_message(user_id, user_msg)

                # 10. History database-e save kora hocche
                gsell_order_id = f"GSELL{int(time.time())}{user_id}"
                create_order({
                    "_id": gsell_order_id, "user_id": user_id, "service": "Gmail Sell (Task)",
                    "details": gmail, "price": 0, "status": "rejected",
                    "timestamp": time.time()
                })
                
                bot.answer_callback_query(call.id, "❌ Gmail Rejected")
                new_text = f"❌ REJECTED: {gmail}"
                
            bot.edit_message_text(
                chat_id=call.message.chat.id, message_id=call.message.message_id,
                text=new_text, reply_markup=None
            )
            # ☢️ save_data() ar nei
            check_complete_submission(user_id, submission_id) 

        # 2. Withdrawal Payment
        elif action == "pay":
            user_id = str(data[1])
            amount = int(data[2]) # Total amount on hold
            withdraw_id = str(data[3])
            
            # 26. Database theke order check kora hocche
            order = get_order(withdraw_id)
            
            if order and order["status"] == "pending":
                # 9. Database-e user-er hold update kora hocche
                update_user(user_id, {"$inc": {"hold": -amount}})
                
                # 27. Database-e order status update kora hocche
                update_order_status(withdraw_id, "completed")
                
                final_amount = order.get("final_amount", amount)
                current_balance = get_user(user_id)['balance'] # Updated balance
                
                user_msg = f"✅ আপনার উত্তোলনের অনুরোধ অনুমোদিত হয়েছে!\n\n💰 Amount Received: {final_amount} TK\n(Total Deducted: {amount} TK)\n📊 নতুন ব্যালেন্স: {current_balance} TK\n\nটাকা ১-২ ঘন্টার মধ্যে আপনার অ্যাকাউন্টে যোগ হবে।"
                bot.send_message(user_id, user_msg)
                bot.answer_callback_query(call.id, "✅ Payment confirmed. Hold released.")
                bot.edit_message_text(
                    chat_id=call.message.chat.id, message_id=call.message.message_id,
                    text=call.message.text + "\n\n✅ PAYMENT SENT AND HOLD RELEASED", reply_markup=None
                )
                # ☢️ save_data() ar nei
            else:
                bot.answer_callback_query(call.id, "❌ Withdrawal not found or already paid.")
                
        # 3. Order Delivery Confirmation
        elif action == "deliver":
            service_type = data[1]
            order_id = "_".join(data[2:])
            
            # 26. Database theke order check kora hocche
            order = get_order(order_id)
            if not order:
                bot.answer_callback_query(call.id, "❌ Order not found!"); return

            user_id = order["user_id"]
            user = get_user(user_id) # User-er username-er jonno
            
            service_name = order.get('service', 'N/A')
            service_details = order.get('type', service_name)
            quantity = order.get('quantity', 1)
            
            details_text = ""
            if service_type == "pp":
                details_text = f"\n\n--- Details ---\n{order.get('details', 'N/A')}"
            
            instructions = f"""
📩 ডেলিভারি নির্দেশনা:

📦 Order ID: {order_id}
👤 User: @{user.get('username', 'N/A')} (ID: {user_id})
🎁 Service: {service_name}
📋 Type: {service_details}
🔢 Quantity: {quantity}
{details_text}

ডেলিভারির পর ম্যানুয়ালি ইউজারকে মেসেজ করুন।
"""
            
            bot.send_message(ADMIN_ID, instructions)
            bot.answer_callback_query(call.id, "✅ Delivery instructions sent")
            bot.edit_message_text(
                chat_id=call.message.chat.id, message_id=call.message.message_id,
                text=call.message.text + "\n\n⏳ DELIVERY IN PROGRESS...", reply_markup=None
            )
            
    except Exception as e:
        print(f"Error in admin_callback_handler: {e}")
        bot.answer_callback_query(call.id, "❌ একটি ত্রুটি হয়েছে।")


# --- Catch-all Handler (MODIFIED) ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    
    user_id = str(message.from_user.id)
    # 1. Database theke user-er data ana hocche
    user = get_user(user_id)
    
    if user and user.get("is_blocked"):
        if str(message.from_user.id) == ADMIN_ID and message.text and message.text.startswith('/'):
            pass # Admin-ke command use korte din
        else:
            bot.send_message(message.chat.id, f"❌ আপনাকে এই বট ব্যবহার থেকে ব্লক করা হয়েছে। Admin এর সাথে যোগাযোগ করুন: @{ADMIN_USERNAME}")
            return
            
    valid_buttons = [
        # User buttons
        "🛒 Buy Services", "📥 Gmail Sell", "💳 Balance", "💵 Withdraw", "👥 Refer", "🆘 Support", "↩️ মেনুতে ফিরে যান",
        "📥 Gmail Buy", "🌐 Paid VPN Buy", "🎥 YouTube Premium", "🎁 Play Point Park On", 
        "📊 History", "📥 Gmail Sell History", "💵 Withdraw History", "🛒 Service Buy History",
        "🍿 Crunchyroll Premium", "🧠 Google Veo 3 (Gemin)",
        "⬅️ Buy Services Menu",
        
        # Payment/Withdraw
        "📲 Bkash", "📲 Nagad", "🪙 Binance", "🅿️ Payer", "💰 Balance (Pay Now)",
        
        # Country
        "🇺🇸 USA", "🇹🇼 Taiwan", "🇬🇧 UK", "🇰🇷 South Korean", "🇯🇵 Japan",
        
        # Confirmation
        "✅ Confirm", "❌ Cancel",
        
        # Specific price buttons
        f"🇺🇸 USA Gmail ({USA_GMAIL_PRICE}TK)", f"🇧🇩 BD Gmail ({BD_GMAIL_PRICE}TK)",
        f"NordVPN 7 Days ({VPN_PRICE}TK)", f"ExpressVPN 7 Days ({VPN_PRICE}TK)",
        f"HMA VPN 7 Days ({VPN_PRICE}TK)", f"PIA VPN 7 Days ({VPN_PRICE}TK)",
        f"Ipvanis VPN 7 Days ({VPN_PRICE}TK)",
        f"1 Month ({YT_1M_PRICE}TK)", f"1 Year ({YT_1Y_PRICE}TK)",
        f"7 Days ({CRUNCHYROLL_PRICE}TK)",
        f"1 Month ({VEO_1M_PRICE}TK)", f"12 Month ({VEO_12M_PRICE}TK)",

        # Admin buttons
        "📊 স্ট্যাটাস", "💰 ব্যালেন্স ম্যানেজ", "👤 ইউজার/ব্রডকাস্ট", "🚫 ব্লক/আনব্লক", "📧 Gmail টাস্ক ম্যানেজ", "📦 স্টক ম্যানেজ",
        "👤 ইউজার তালিকা", "📢 ব্রডকাস্ট মেসেজ", "📨 নির্দিষ্ট ইউজারকে মেসেজ", "⬅️ অ্যাডমিন মেনু",
        "➕ নতুন টাস্ক যোগ করুন", "📋 অ্যাভেইলেবল টাস্ক দেখুন", "🗑️ টাস্ক ডিলিট করুন",
        "💵 Main Balance", "⏳ Hold Balance", "👥 Referral Count", "🚫 ব্লক করুন", "✅ আনব্লক করুন"
    ]
    
    if message.text and not message.text.startswith('/') and message.text not in valid_buttons:
        bot.clear_step_handler(message)
        if message.chat.id in admin_sessions:
            del admin_sessions[message.chat.id]

        unknown_msg = "❌ অজানা কমান্ড!\n\nআপনার মেসেজটি বুঝা যায়নি। অনুগ্রহ করে নিচের মেনু থেকে একটি অপশন নির্বাচন করুন।"
        bot.send_message(message.chat.id, unknown_msg)
        home_menu(message.chat.id)
    
    if message.text and message.text.startswith('/') and message.text not in ['/start', '/admin']:
        bot.send_message(message.chat.id, "❌ অবৈধ কমান্ড! দয়া করে মেনু ব্যবহার করুন।")


if __name__ == "__main__":
    print("🤖 Bot is running with MongoDB persistence...")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Error in polling: {e}. Restarting in 15 seconds...")
            time.sleep(15)
