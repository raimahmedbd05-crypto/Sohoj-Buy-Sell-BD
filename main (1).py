import telebot
from telebot import types
import time
import json
import os
import uuid
from collections import defaultdict

# --- Configuration ---
TOKEN = '8204693585:AAHo3H_NsANMskc9ubQICp2MKP6H-K0dcdg'
ADMIN_ID = '8118743556'
ADMIN_USERNAME = 'RAIM_AHMED' # Added for block message
ADMIN_BKASH_NO = '01774049543'
ADMIN_NAGAD_NO = '01774049543'
BOT_USERNAME = "sohojbuysellbdbot"

# Note: The TeleBot instance should be created after defining the token
bot = telebot.TeleBot(TOKEN)

# --- Service Prices ---
USA_GMAIL_PRICE = 15
BD_GMAIL_PRICE = 10
PLAY_POINT_PRICE = 20
VPN_PRICE = 40
YT_1M_PRICE = 25
YT_1Y_PRICE = 150
CRUNCHYROLL_PRICE = 25 # New
VEO_1M_PRICE = 20      # New
VEO_12M_PRICE = 50     # New

# --- Withdrawal Configuration ---
MIN_WITHDRAW = 30            # Updated
WITHDRAW_FEE = 5             # New
WITHDRAW_FEE_THRESHOLD = 50    # New

# --- Global Data Structures ---
users = {}
pending_gmails = defaultdict(dict) # Nested dict for batch processing
orders = {}
admin_sessions = {} # Global variable for admin session data

# --- NEW Gmail Task System Data ---
available_gmail_tasks = []
active_gmail_tasks = {}

# --- NEW Stock System Data ---
# -1 = In Stock (Unlimited), 0 = Out of Stock
service_stock = {}
DEFAULT_STOCK = {
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

# --- End of Global Data Structures ---


# --- Data Persistence Functions ---
def save_data():
    """Saves all persistent data (users, orders, pending_gmails, gmail tasks, and stock)."""
    try:
        with open('users.json', 'w', encoding='utf-8') as f:
            json.dump({
                "users": users,
                "orders": orders,
                "pending_gmails": dict(pending_gmails),
                "available_gmail_tasks": available_gmail_tasks,
                "active_gmail_tasks": active_gmail_tasks,
                "service_stock": service_stock  # Added stock
            }, f, indent=4)
        # print("All data saved successfully.")
    except Exception as e:
        print(f"Error saving data: {e}")

def load_data():
    """Loads all persistent data from a JSON file."""
    global users, orders, pending_gmails, available_gmail_tasks, active_gmail_tasks, service_stock
    
    default_data = {
        "users": {},
        "orders": {},
        "pending_gmails": defaultdict(dict),
        "available_gmail_tasks": [],
        "active_gmail_tasks": {},
        "service_stock": DEFAULT_STOCK # Use default stock
    }

    if os.path.exists('users.json'):
        try:
            with open('users.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                users = data.get("users", {})
                orders = data.get("orders", {})
                
                loaded_pending_gmails = data.get("pending_gmails", {})
                pending_gmails.clear()
                pending_gmails.update(loaded_pending_gmails)
                
                available_gmail_tasks = data.get("available_gmail_tasks", [])
                
                loaded_active_tasks = data.get("active_gmail_tasks", {})
                for user_id, task_data in loaded_active_tasks.items():
                    if 'task' in task_data:
                        available_gmail_tasks.append(task_data['task'])
                
                active_gmail_tasks.clear()
                
                # Load stock, ensuring all keys from DEFAULT_STOCK exist
                loaded_stock = data.get("service_stock", DEFAULT_STOCK)
                service_stock = DEFAULT_STOCK.copy() # Start with defaults
                service_stock.update(loaded_stock) # Override with saved values
                
            print("All data loaded successfully.")
        except json.JSONDecodeError:
            print("Corrupted users.json file. Starting with empty data.")
            users, orders, available_gmail_tasks, active_gmail_tasks, service_stock = default_data.values()
            pending_gmails.clear()
        except Exception as e:
            print(f"Error loading data: {e}. Starting with empty data.")
            users, orders, available_gmail_tasks, active_gmail_tasks, service_stock = default_data.values()
            pending_gmails.clear()
    else:
        print("users.json not found. Creating new data structures.")
        users, orders, available_gmail_tasks, active_gmail_tasks, service_stock = default_data.values()
        pending_gmails.clear()


# --- Bot Initialization ---
load_data()
# --- End of Data Persistence Functions ---

LOGO = """
╔═════════════════════════╗
║     🛒 Sohoj Buy Sell BD     ║
╚═════════════════════════╝

🌟 আপনার ডিজিটাল সার্ভিসের বিশ্বস্ত পার্টনার 🌟
"""

# --- Utility Markups ---
def back_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True); markup.add("↩️ মেনুতে ফিরে যান"); return markup

def payment_markup():
    """Returns the markup for payment options, now including Balance."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add("📲 Bkash", "📲 Nagad", "💰 Balance") # Added Balance
    markup.add("↩️ মেনুতে ফিরে যান")
    return markup

def withdraw_method_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📲 Bkash", "📲 Nagad", "🪙 Binance", "🅿️ Payer", "↩️ মেনুতে ফিরে যান")
    return markup
    
# --- HOME MENU FUNCTION ---
def home_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # Line 1: Gmail Sell, Withdraw, Balance, Refer (4 buttons)
    row1 = ["📥 Gmail Sell", "💵 Withdraw", "💳 Balance", "👥 Refer"]
    
    # Line 2: Buy Services, Check Price (2 buttons)
    row2 = ["🛒 Buy Services", "🏷️ Check Price"]
    
    # Line 3: Support (1 button)
    row3 = ["🆘 Support"]

    markup.add(*row1)
    markup.add(*row2)
    markup.add(*row3)
    
    user_info = ""
    if str(chat_id) in users:
        user = users[str(chat_id)]
        user_info = f"\n👤 User: @{user.get('username', 'NoUsername')}\n💰 Balance: {user.get('balance', 0)} TK"
    
    welcome_msg = f"""
{LOGO}
{user_info}

🎯 নিচের মেনু থেকে সেবা নির্বাচন করুন:
"""
    bot.send_message(chat_id, welcome_msg, reply_markup=markup) 

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    
    if user_id in users and users[user_id].get("is_blocked"):
        bot.send_message(message.chat.id, f"❌ আপনাকে এই বট ব্যবহার থেকে ব্লক করা হয়েছে। Admin এর সাথে যোগাযোগ করুন: @{ADMIN_USERNAME}")
        return
        
    bot.send_message(message.chat.id, LOGO)
    time.sleep(0.5)

    is_new_user = user_id not in users
    referral_link_used = len(message.text.split()) > 1

    if is_new_user:
        users[user_id] = {
            "username": message.from_user.username,
            "balance": 0,
            "hold": 0,
            "referral_count": 0,
            "referred_users": [],
            "joined_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "is_blocked": False
        }
        
        # Process referral ONLY if it's a new user
        if referral_link_used:
            referrer_id_str = message.text.split()[1]
            try:
                if referrer_id_str in users and referrer_id_str != user_id:
                    if user_id not in users[referrer_id_str]["referred_users"]:
                        users[referrer_id_str]["balance"] += 2
                        users[referrer_id_str]["referral_count"] += 1
                        users[referrer_id_str]["referred_users"].append(user_id)
                        bot.send_message(referrer_id_str, f"🎉 আপনি ২ টাকা পেয়েছেন রেফার বোনাস হিসেবে! নতুন ইউজার: @{message.from_user.username or 'NoUsername'}")
            except:
                pass # Ignore if referrer_id_str is not a valid user ID
        
        save_data()

    elif not is_new_user and referral_link_used:
        # Warn existing user trying to use a referral link
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
💰 ব্যালেন্স: {users[user_id]['balance']} টাকা
👥 রেফার্ড ইউজার: {users[user_id]['referral_count']} জন

নিচের মেনু থেকে আপনার পছন্দের সেবা নির্বাচন করুন:
"""
    bot.send_message(message.chat.id, welcome_msg)
    time.sleep(1)
    home_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "↩️ মেনুতে ফিরে যান")
def back_to_home(message):
    bot.clear_step_handler(message)
    home_menu(message.chat.id)
    if message.chat.id in admin_sessions:
        del admin_sessions[message.chat.id]

# --- Buy Services Submenu Handler ---
@bot.message_handler(func=lambda m: m.text == "🛒 Buy Services")
def buy_services_menu(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return
    
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

# --- Check Price Handler ---
@bot.message_handler(func=lambda m: m.text == "🏷️ Check Price")
def check_price_list(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return
    
    price_list_msg = f"""
🏷️ **সকল সেবার মূল্য তালিকা**

### 💰 Gmail Sell (টাস্ক)
* **প্রতিটি Gmail টাস্ক (Approved):** ৭ টাকা

### 🛒 Buy Services
* **🇺🇸 USA Gmail (Buy):** {USA_GMAIL_PRICE} টাকা
* **🇧🇩 BD Gmail (Buy):** {BD_GMAIL_PRICE} টাকা
    * (৫+ অর্ডারে ৫% ডিসকাউন্ট, ১০+ অর্ডারে ১০% ডিসকাউন্ট)
* **🎁 Play Point Park On:** {PLAY_POINT_PRICE} টাকা (প্রতিটি Park On-এর জন্য)
* **🎥 YouTube Premium:**
    * ১ মাস: {YT_1M_PRICE} টাকা
    * ১ বছর: {YT_1Y_PRICE} টাকা
* **🌐 Paid VPN 7 Days (Nord, Express, HMA, PIA, Ipvanis):** {VPN_PRICE} টাকা
* **🍿 Crunchyroll Premium 7 Days:** {CRUNCHYROLL_PRICE} টাকা
* **🧠 Google Veo 3 (Gemin):**
    * ১ মাস: {VEO_1M_PRICE} টাকা
    * ১২ মাস: {VEO_12M_PRICE} টাকা

### 💸 Withdrawal
* **সর্বনিম্ন উত্তোলন:** {MIN_WITHDRAW} টাকা
* **উত্তোলন ফি (৫০+ TK):** {WITHDRAW_FEE} টাকা

💡 মেনুতে ফিরে যেতে '↩️ মেনুতে ফিরে যান' বাটনটি চাপুন।
"""
    bot.send_message(message.chat.id, price_list_msg, parse_mode="Markdown")


# --- NEW: Balance Payment Helper Functions ---

def handle_balance_payment(message, service_name, price, on_success_callback, on_fail_callback):
    """
    Handles the logic for paying with balance.
    - service_name: String for display (e.g., "Play Point Park On")
    - price: The integer cost of the service.
    - on_success_callback: A function to call if the user confirms. This function MUST create the order.
    - on_fail_callback: A function to call if the user cancels (e.g., home_menu).
    """
    user_id = str(message.from_user.id)
    if user_id not in users:
        bot.send_message(message.chat.id, "❌ User not found. Please /start"); return

    balance = users[user_id].get("balance", 0)

    if balance < price:
        bot.send_message(message.chat.id, f"❌ আপনার পর্যাপ্ত ব্যালেন্স নেই!\n\n💰 আপনার ব্যালেন্স: {balance} TK\n🛒 প্রয়োজন: {price} TK\n\nদয়া করে Bkash/Nagad ব্যবহার করুন অথবা প্রথমে আয় করুন।")
        # Go back to the main menu, as they can't proceed
        return on_fail_callback(message.chat.id) 

    new_balance = balance - price
    
    confirm_msg = f"""
✅ ব্যালেন্স পেমেন্ট কনফার্মেশন:

🎁 সার্ভিস: {service_name}
💰 মূল্য: {price} TK

---
💳 বর্তমান ব্যালেন্স: {balance} TK
💸 নতুন ব্যালেন্স হবে: {new_balance} TK
---

আপনি কি এই পেমেন্টটি কনফার্ম করতে চান?
"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("✅ Confirm", "❌ Cancel")
    
    msg = bot.send_message(message.chat.id, confirm_msg, reply_markup=markup)
    
    # We need to pass all necessary info to the next step
    bot.register_next_step_handler(msg, lambda m: confirm_balance_purchase(m, price, on_success_callback, on_fail_callback))

def confirm_balance_purchase(message, price, on_success_callback, on_fail_callback):
    """
    Handles the "✅ Confirm" or "❌ Cancel" from the user.
    """
    user_id = str(message.from_user.id)

    if message.text == "✅ Confirm":
        # Check balance again just in case (though unlikely to change)
        balance = users[user_id].get("balance", 0)
        if balance < price:
            bot.send_message(message.chat.id, "❌ দুঃখিত, শেষ মুহূর্তে একটি সমস্যা হয়েছে। আপনার ব্যালেন্স অপর্যাপ্ত।")
            return on_fail_callback(message.chat.id)
            
        # Deduct balance
        users[user_id]["balance"] -= price
        save_data() # Save the new balance immediately
        
        # Call the specific service's order creation function
        # This function is responsible for sending user/admin messages and returning to home_menu
        on_success_callback(message)

    elif message.text == "❌ Cancel":
        bot.send_message(message.chat.id, "❌ অর্ডার বাতিল করা হয়েছে।")
        # Use on_fail_callback, which is typically home_menu
        return on_fail_callback(message.chat.id)
    
    else:
        # Invalid input
        bot.send_message(message.chat.id, "❌ অবৈধ অপশন। '✅ Confirm' বা '❌ Cancel' নির্বাচন করুন।")
        # Ask again
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("✅ Confirm", "❌ Cancel")
        msg = bot.send_message(message.chat.id, "দয়া করে নিচের বাটন থেকে নির্বাচন করুন:", reply_markup=markup)
        bot.register_next_step_handler(msg, lambda m: confirm_balance_purchase(m, price, on_success_callback, on_fail_callback))

# --- End of Balance Payment Helper Functions ---


# --- Play Point Park On Flow ---
@bot.message_handler(func=lambda m: m.text == "🎁 Play Point Park On")
def play_point_menu(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return
    
    # Stock Check
    if service_stock.get("play_point", -1) == 0:
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
    markup.add("🇺🇸 USA", "🇹🇼 Taiwan", "🇬🇧 UK", "🇰🇷 South Korean", "🇯🇵 Japan", "↩️ মেনুতে ফিরে যান")
    msg = bot.send_message(message.chat.id, options, reply_markup=markup)
    bot.register_next_step_handler(msg, process_play_point_country)

def process_play_point_country(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    
    # Added Japan
    if message.text not in ["🇺🇸 USA", "🇹🇼 Taiwan", "🇬🇧 UK", "🇰🇷 South Korean", "🇯🇵 Japan"]:
        error_msg = "❌ অবৈধ দেশ। অনুগ্রহ করে বাটন থেকে নির্বাচন করুন:"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        markup.add("🇺🇸 USA", "🇹🇼 Taiwan", "🇬🇧 UK", "🇰🇷 South Korean", "🇯🇵 Japan", "↩️ মেনুতে ফিরে যান")
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=markup)
        bot.register_next_step_handler(msg, process_play_point_country)
        return
        
    country = message.text
    user_id = str(message.from_user.id)
    if user_id not in users: users[user_id] = {}
    users[user_id]["play_point_country"] = country
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
        if user_id not in users: return home_menu(message.chat.id)
        users[user_id]["play_point_quantity"] = quantity
        total_price = quantity * PLAY_POINT_PRICE
        users[user_id]["play_point_price"] = total_price
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
    if user_id not in users or "play_point_price" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।"); return home_menu(message.chat.id)
    users[user_id]["play_point_details"] = message.text
    order_summary = f"📝 অর্ডার সারাংশ:\n\n🌍 Country: {users[user_id]['play_point_country']}\n🔢 Quantity: {users[user_id]['play_point_quantity']} টি\n💰 মোট মূল্য: {users[user_id]['play_point_price']} TK\n\n💳 পেমেন্ট মাধ্যম নির্বাচন করুন:"
    bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
    bot.register_next_step_handler(message, process_play_point_payment)

def process_play_point_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    
    user_id = str(message.from_user.id)
    if user_id not in users or "play_point_price" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন."); return home_menu(message.chat.id)
    
    user_data = users[user_id]
    price = user_data["play_point_price"]
    
    if message.text == "💰 Balance":
        # --- Handle Balance Payment ---
        service_name = f"Play Point Park On ({user_data['play_point_country']} x{user_data['play_point_quantity']})"
        
        def create_ppon_order_from_balance(msg): # 'msg' is the '✅ Confirm' message
            order_id = f"PPON{int(time.time())}{user_id}"
            orders[order_id] = {
                "user_id": user_id, 
                "service": "Play Point Park On", 
                "country": users[user_id]["play_point_country"], 
                "quantity": users[user_id]["play_point_quantity"], 
                "details": users[user_id]["play_point_details"], 
                "price": price, 
                "method": "Balance", # New method
                "txn_id": "N/A", # No Txn ID for balance
                "status": "pending"
            }
            save_data()
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_pp_{order_id}"))
            
            admin_msg = f"""
🎁 নতুন Play Point Park On অর্ডার (Balance):

📦 Order ID: {order_id}
👤 User: @{message.from_user.username or 'N/A'}
🆔 User ID: {user_id}
🌍 Country: {orders[order_id]['country']}
🔢 Quantity: {orders[order_id]['quantity']} টি
💰 Amount: {price} TK
💳 Method: Balance
📝 Txn ID: N/A
⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}

📩 Gmail Details:
{orders[order_id]['details']}
"""
            bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
            
            user_confirmation = f"""
✅ আপনার অর্ডার কনফার্ম হয়েছে! (Paid with Balance)

📦 Order ID: {order_id}
🎁 Service: Play Point Park On
💰 Paid: {price} TK
💳 আপনার নতুন ব্যালেন্স: {users[user_id]['balance']} TK

আপনার অর্ডারটি প্রসেস করা হচ্ছে।
ডেলিভারি সময়: ১-১২ ঘন্টা
সেবা নেওয়ার জন্য ধন্যবাদ! 🙏
"""
            bot.send_message(message.chat.id, user_confirmation)
            home_menu(message.chat.id)

        handle_balance_payment(
            message, 
            service_name, 
            price, 
            on_success_callback=create_ppon_order_from_balance, 
            on_fail_callback=home_menu
        )
        return # Stop execution here
    
    elif message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"; 
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=payment_markup())
        bot.register_next_step_handler(msg, process_play_point_payment); return
    
    # --- Existing Bkash/Nagad logic ---
    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    
    payment_instructions = f"💳 {method} এ টাকা পাঠান:\n\n📱 Number: {payment_number}\n💰 Amount: {price} TK\n📝 Reference: PPON{user_id}\n\n⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন\n\n📨 এখন আপনার Transaction ID লিখুন:"
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_play_point_order(m, method, price))


def confirm_play_point_order(message, method, price):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    txn_id = message.text
    user_id = str(message.from_user.id)
    if user_id not in users or "play_point_details" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন."); return home_menu(message.chat.id)
    order_id = f"PPON{int(time.time())}{user_id}"
    orders[order_id] = {"user_id": user_id, "service": "Play Point Park On", "country": users[user_id]["play_point_country"], "quantity": users[user_id]["play_point_quantity"], "details": users[user_id]["play_point_details"], "price": price, "method": method, "txn_id": txn_id, "status": "pending"}
    save_data()
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_pp_{order_id}"))
    admin_msg = f"🎁 নতুন Play Point Park On অর্ডার:\n\n📦 Order ID: {order_id}\n👤 User: @{message.from_user.username or 'N/A'}\n🆔 User ID: {user_id}\n🌍 Country: {orders[order_id]['country']}\n🔢 Quantity: {orders[order_id]['quantity']} টি\n💰 Amount: {price} TK\n💳 Method: {method}\n📝 Txn ID: {txn_id}\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n📩 Gmail Details:\n{orders[order_id]['details']}"
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
    user_confirmation = f"✅ আপনার অর্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n🎁 Service: Play Point Park On\n💰 Paid: {price} TK\n\nআপনার অর্ডারটি প্রসেস করা হচ্ছে।\nডেলিভারি সময়: ১-১২ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
    bot.send_message(message.chat.id, user_confirmation)
    home_menu(message.chat.id)
# --- End of Play Point Flow ---


# --- Gmail Sell Flow (Task-Based) ---

def check_task_timeout(user_id):
    """Checks if a user's active task has expired (30 mins)."""
    user_id_str = str(user_id)
    if user_id_str in active_gmail_tasks:
        task_data = active_gmail_tasks[user_id_str]
        if (time.time() - task_data.get('timestamp', 0)) > 1800: # 30 mins
            available_gmail_tasks.append(task_data['task'])
            del active_gmail_tasks[user_id_str]
            save_data()
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
        username = users.get(user_id, {}).get("username", "NoUsername")
        
        approved_count = sum(1 for g in submission["gmails"] if g["status"] == "approved")
        rejected_count = sum(1 for g in submission["gmails"] if g["status"] == "rejected")
        total_amount = approved_count * 7 # 7 TK per approval
        
        admin_msg = f"""
✅ Submission {submission_id} প্রসেস সম্পন্ন!

👤 User: @{username}
🆔 User ID: {user_id}
✅ Approved: {approved_count}টি
❌ Rejected: {rejected_count}টি
💰 Total Added: {total_amount} TK
💳 Final Balance: {users[user_id]["balance"]} TK
"""
        bot.send_message(ADMIN_ID, admin_msg)
        
        del pending_gmails[user_id][submission_id]
        if not pending_gmails[user_id]:
            del pending_gmails[user_id]
        
        save_data()

@bot.message_handler(func=lambda m: m.text == "📥 Gmail Sell")
def gmail_sell(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return
    
    check_task_timeout(user_id)
    
    # This logic is correct and handles the user's request:
    # "oita done kinba cancel na kore abar arekta sell dite parbe na"
    if user_id in active_gmail_tasks:
        task_data = active_gmail_tasks[user_id]
        task = task_data['task']
        
        task_details_msg = f"""
⏳ আপনার একটি টাস্ক ইতিমধ্যে সক্রিয় আছে!
(এই টাস্কটি Done বা Cancel না করে নতুন টাস্ক নিতে পারবেন না।)

💌 প্রতিটি Gmail এর জন্য পাবেন ৭ টাকা

First name: `{task['fname']}`
Last name: `{task['lname']}`
Email: `{task['email']}`
Password: `{task['password']}`

🔐 Gmail সম্পূর্ণ অ্যাক্সেস সহ হতে হবে কোনো 2FA/2-Step Verification থাকা যাবে না !

⏰ সময় বাকি আছে: {30 - int((time.time() - task_data['timestamp']) / 60)} মিনিট

কাজ শেষ হলে "✅ Done" চাপুন অথবা বাতিল করতে "❌ Cancel" চাপুন।
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Done", callback_data=f"gmail_task_done_{user_id}"),
            types.InlineKeyboardButton("❌ Cancel", callback_data=f"gmail_task_cancel_{user_id}")
        )
        bot.send_message(message.chat.id, task_details_msg, reply_markup=markup, parse_mode="Markdown")
        return

    if not available_gmail_tasks:
        bot.send_message(message.chat.id, "😔 Sorry, no tasks available right now. Please try again later.")
        return
        
    try:
        task_to_assign = available_gmail_tasks.pop(0) # Get the first task
        
        active_gmail_tasks[user_id] = {
            "task": task_to_assign,
            "timestamp": time.time()
        }
        save_data()
        
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


# --- Gmail Buy Flow (Stock-Aware) ---
@bot.message_handler(func=lambda m: m.text == "📥 Gmail Buy")
def gmail_buy(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    options_available = False
    
    # Stock Check
    if service_stock.get("gmail_usa", -1) != 0:
        markup.add(f"🇺🇸 USA Gmail ({USA_GMAIL_PRICE}TK)")
        options_available = True
    if service_stock.get("gmail_bd", -1) != 0:
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
    markup.add("↩️ মেনুতে ফিরে যান")
    msg = bot.send_message(message.chat.id, options, reply_markup=markup)
    bot.register_next_step_handler(msg, process_gmail_type)

def process_gmail_type(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    user_id = str(message.from_user.id)
    if user_id not in users: users[user_id] = {}
    
    selected_text = message.text
    
    if selected_text == f"🇺🇸 USA Gmail ({USA_GMAIL_PRICE}TK)" and service_stock.get("gmail_usa", -1) != 0:
        users[user_id]["gmail_type"] = "USA Gmail"
        users[user_id]["gmail_price_per"] = USA_GMAIL_PRICE
    elif selected_text == f"🇧🇩 BD Gmail ({BD_GMAIL_PRICE}TK)" and service_stock.get("gmail_bd", -1) != 0:
        users[user_id]["gmail_type"] = "BD Gmail" 
        users[user_id]["gmail_price_per"] = BD_GMAIL_PRICE
    else:
        error_msg = "❌ অবৈধ অপশন বা স্টক আউট! দয়া করে আবার চেষ্টা করুন:"
        bot.send_message(message.chat.id, error_msg)
        return gmail_buy(message) # Restart flow

    selected_type = users[user_id]["gmail_type"]
    price_per = users[user_id]["gmail_price_per"]
        
    quantity_options = f"✅ {selected_type} সিলেক্ট করেছেন\n💵 প্রতি একাউন্ট: {price_per} TK\n\n🔢 কতটি Gmail অ্যাকাউন্ট কিনতে চান?\n💡 শুধু সংখ্যা লিখুন:"
    msg = bot.send_message(message.chat.id, quantity_options, reply_markup=back_markup())
    bot.register_next_step_handler(msg, process_gmail_quantity)

def process_gmail_quantity(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    user_id = str(message.from_user.id)
    if user_id not in users or "gmail_type" not in users[user_id]:
        bot.send_message(message.chat.id, "❌ ডাটা লস্ট হয়েছে! দয়া করে আবার শুরু করুন:"); return gmail_buy(message)
    try:
        quantity = int(message.text)
        if quantity <= 0: raise ValueError
    except ValueError:
        error_msg = "❌ অবৈধ সংখ্যা! শুধুমাত্র সংখ্যা লিখুন:"; msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, process_gmail_quantity); return
    
    gmail_type = users[user_id].get("gmail_type", "N/A"); price_per = users[user_id].get("gmail_price_per", 0)
    price = price_per * quantity
    discount_msg = ""; discount = 0
    
    if quantity >= 10:
        discount = price * 0.10; price -= discount
        discount_msg = f"🎉 ১০+ অর্ডারে ১০% ডিসকাউন্ট পেয়েছেন! (-{discount:.0f} TK)"
    elif quantity >= 5:
        discount = price * 0.05; price -= discount
        discount_msg = f"🎉 ৫+ অর্ডারে ৫% ডিসকাউন্ট পেয়েছেন! (-{discount:.0f} TK)"
        
    users[user_id]["gmail_quantity"] = quantity
    users[user_id]["gmail_price"] = int(price)
    
    order_summary = f"📝 অর্ডার সারাংশ:\n\n📧 Type: {gmail_type}\n🔢 Quantity: {quantity} টি\n💵 প্রতি একাউন্ট: {price_per} TK\n{discount_msg}\n💰 মোট মূল্য: {int(price)} TK\n\n💳 পেমেন্ট মাধ্যম নির্বাচন করুন:"
    bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
    bot.register_next_step_handler(message, process_gmail_payment)

def process_gmail_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    
    user_id = str(message.from_user.id)
    if user_id not in users or "gmail_price" not in users[user_id]:
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন:"); return gmail_buy(message)
    
    user_data = users[user_id]
    price = user_data.get("gmail_price", 0)
    quantity = user_data.get("gmail_quantity", 0)
    gmail_type = user_data.get("gmail_type", "N/A")

    if message.text == "💰 Balance":
        # --- Handle Balance Payment ---
        service_name = f"Gmail Buy ({gmail_type} x{quantity})"
        
        def create_gmail_order_from_balance(msg):
            order_id = f"GMAIL{int(time.time())}{user_id}"
            orders[order_id] = {
                "user_id": user_id, "service": "Gmail", "type": gmail_type, 
                "quantity": quantity, "price": price, "method": "Balance", 
                "txn_id": "N/A", "status": "pending"
            }
            save_data()
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_gmail_{order_id}"))
            
            admin_msg = f"""
🛒 নতুন Gmail অর্ডার (Balance):

📦 Order ID: {order_id}
👤 User: @{message.from_user.username or 'N/A'}
🆔 User ID: {user_id}
📧 Type: {gmail_type}
🔢 Quantity: {quantity} টি
💰 Amount: {price} TK
💳 Method: Balance
📝 Txn ID: N/A
⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
            bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
            
            user_confirmation = f"""
✅ আপনার অর্ডার কনফার্ম হয়েছে! (Paid with Balance)

📦 Order ID: {order_id}
📧 Service: {gmail_type}
🔢 Quantity: {quantity} টি
💰 Paid: {price} TK
💳 আপনার নতুন ব্যালেন্স: {users[user_id]['balance']} TK

আপনার অর্ডারটি প্রসেস করা হচ্ছে। 
ডেলিভারি সময়: ১-১২ ঘন্টা
সেবা নেওয়ার জন্য ধন্যবাদ! 🙏
"""
            bot.send_message(message.chat.id, user_confirmation)
            
            if user_id in users:
                users[user_id].pop("gmail_type", None); users[user_id].pop("gmail_price_per", None)
                users[user_id].pop("gmail_quantity", None); users[user_id].pop("gmail_price", None)
                
            home_menu(message.chat.id)

        handle_balance_payment(
            message, 
            service_name, 
            price, 
            on_success_callback=create_gmail_order_from_balance, 
            on_fail_callback=home_menu
        )
        return # Stop execution

    elif message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"; 
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=payment_markup())
        bot.register_next_step_handler(msg, process_gmail_payment); return
        
    # --- Existing Bkash/Nagad logic ---
    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO

    payment_instructions = f"💳 {method} এ টাকা পাঠান:\n\n📱 Number: {payment_number}\n💰 Amount: {price} TK\n📝 Reference: Gmail{quantity}\n\n⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন\n\n📨 এখন আপনার Transaction ID লিখুন:"
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_gmail_order(m, method, price, gmail_type, quantity))


def confirm_gmail_order(message, method, price, gmail_type, quantity):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    txn_id = message.text.strip()
    if len(txn_id) < 3:
        error_msg = "❌ অবৈধ Transaction ID! দয়া করে সঠিক Transaction ID লিখুন:"; 
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, lambda m: confirm_gmail_order(m, method, price, gmail_type, quantity)); return
        
    user_id = str(message.from_user.id)
    order_id = f"GMAIL{int(time.time())}{user_id}"
    orders[order_id] = {"user_id": user_id, "service": "Gmail", "type": gmail_type, "quantity": quantity, "price": price, "method": method, "txn_id": txn_id, "status": "pending"}
    save_data()
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_gmail_{order_id}"))
    
    admin_msg = f"🛒 নতুন Gmail অর্ডার:\n\n📦 Order ID: {order_id}\n👤 User: @{message.from_user.username or 'N/A'}\n🆔 User ID: {user_id}\n📧 Type: {gmail_type}\n🔢 Quantity: {quantity} টি\n💰 Amount: {price} TK\n💳 Method: {method}\n📝 Txn ID: {txn_id}\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
    
    user_confirmation = f"✅ আপনার অর্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n📧 Service: {gmail_type}\n🔢 Quantity: {quantity} টি\n💰 Paid: {price} TK\n\nআপনার অর্ডারটি প্রসেস করা হচ্ছে। \nডেলিভারি সময়: ১-১২ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
    bot.send_message(message.chat.id, user_confirmation)
    
    if user_id in users:
        users[user_id].pop("gmail_type", None); users[user_id].pop("gmail_price_per", None)
        users[user_id].pop("gmail_quantity", None); users[user_id].pop("gmail_price", None)
        
    home_menu(message.chat.id)
# --- End of Gmail Buy Flow ---


# --- VPN Buy Flow (Stock-Aware) ---
@bot.message_handler(func=lambda m: m.text == "🌐 Paid VPN Buy")
def vpn_buy(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    options_available = False
    
    vpn_services = {
        "vpn_nord": f"NordVPN 7 Days ({VPN_PRICE}TK)",
        "vpn_express": f"ExpressVPN 7 Days ({VPN_PRICE}TK)",
        "vpn_hma": f"HMA VPN 7 Days ({VPN_PRICE}TK)",
        "vpn_pia": f"PIA VPN 7 Days ({VPN_PRICE}TK)",
        "vpn_ipvanis": f"Ipvanis VPN 7 Days ({VPN_PRICE}TK)"
    }
    
    buttons_to_add = []
    for key, text in vpn_services.items():
        if service_stock.get(key, -1) != 0:
            buttons_to_add.append(text)
            options_available = True
            
    if not options_available:
        bot.send_message(message.chat.id, "❌ দুঃখিত, সকল VPN বর্তমানে স্টক আউট আছে।")
        return home_menu(message.chat.id)
        
    markup.add(*buttons_to_add)
    markup.add("↩️ মেনুতে ফিরে যান")
    
    vpn_options = f"""
🔒 VPN প্যাকেজ নির্বাচন করুন:
(মূল্য: {VPN_PRICE} TK প্রতিটি)

(স্টক আউট থাকলে অপশন দেখাবে না)
"""
    msg = bot.send_message(message.chat.id, vpn_options, reply_markup=markup)
    bot.register_next_step_handler(msg, select_vpn_type)

def select_vpn_type(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    
    selected_vpn = message.text
    
    # Check if the selected option is valid (and implicitly in stock)
    vpn_services_texts = [
        f"NordVPN 7 Days ({VPN_PRICE}TK)", f"ExpressVPN 7 Days ({VPN_PRICE}TK)",
        f"HMA VPN 7 Days ({VPN_PRICE}TK)", f"PIA VPN 7 Days ({VPN_PRICE}TK)",
        f"Ipvanis VPN 7 Days ({VPN_PRICE}TK)"
    ]
    if selected_vpn not in vpn_services_texts:
        bot.send_message(message.chat.id, "❌ অবৈধ নির্বাচন বা স্টক আউট। আবার চেষ্টা করুন।"); return vpn_buy(message)
        
    user_id = str(message.from_user.id)
    if user_id not in users: users[user_id] = {}
    users[user_id]["vpn"] = selected_vpn
    
    order_summary = f"📝 অর্র্ডার সারাংশ:\n\n🔒 Service: {selected_vpn}\n💰 মূল্য: {VPN_PRICE} TK\n\n💳 পেমেন্ট মাধ্যম নির্বাচন করুন:"
    bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
    bot.register_next_step_handler(message, process_vpn_payment)

def process_vpn_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    
    user_id = str(message.from_user.id)
    if user_id not in users or "vpn" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন."); return vpn_buy(message)
    
    vpn = users[user_id]["vpn"]
    price = VPN_PRICE

    if message.text == "💰 Balance":
        # --- Handle Balance Payment ---
        service_name = f"VPN ({vpn})"
        
        def create_vpn_order_from_balance(msg):
            order_id = f"VPN{int(time.time())}{user_id}"
            orders[order_id] = {
                "user_id": user_id, "service": "VPN", "type": vpn, 
                "price": price, "method": "Balance", "txn_id": "N/A", "status": "pending"
            }
            save_data()
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_vpn_{order_id}"))
            
            admin_msg = f"""
🔐 নতুন VPN অর্ডার (Balance):

📦 Order ID: {order_id}
👤 User: @{message.from_user.username or 'N/A'}
🆔 User ID: {user_id}
🔒 VPN: {vpn}
💰 Amount: {price} TK
💳 Method: Balance
📝 Txn ID: N/A
⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
            bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
            
            user_confirmation = f"""
✅ আপনার অর্ডার কনফার্ম হয়েছে! (Paid with Balance)

📦 Order ID: {order_id}
🔒 Service: {vpn}
💰 Paid: {price} TK
💳 আপনার নতুন ব্যালেন্স: {users[user_id]['balance']} TK

আপনার অর্ডারটি প্রসেস করা হচ্ছে। 
ডেলিভারি সময়: ১-৬ ঘন্টা
সেবা নেওয়ার জন্য ধন্যবাদ! 🙏
"""
            bot.send_message(message.chat.id, user_confirmation)
            home_menu(message.chat.id)

        handle_balance_payment(
            message, 
            service_name, 
            price, 
            on_success_callback=create_vpn_order_from_balance, 
            on_fail_callback=home_menu
        )
        return # Stop execution

    elif message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"; 
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=payment_markup())
        bot.register_next_step_handler(msg, process_vpn_payment); return
        
    # --- Existing Bkash/Nagad logic ---
    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    
    payment_instructions = f"💳 {method} এ টাকা পাঠান:\n\n📱 Number: {payment_number}\n💰 Amount: {price} TK\n📝 Reference: VPN\n\n⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন\n\n📨 এখন আপনার Transaction ID লিখুন:"
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_vpn_order(m, method, price))


def confirm_vpn_order(message, method, price):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    txn_id = message.text
    user_id = str(message.from_user.id)
    if user_id not in users or "vpn" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন."); return home_menu(message.chat.id)
        
    vpn = users[user_id]["vpn"]
    order_id = f"VPN{int(time.time())}{user_id}"
    orders[order_id] = {"user_id": user_id, "service": "VPN", "type": vpn, "price": price, "method": method, "txn_id": txn_id, "status": "pending"}
    save_data()
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_vpn_{order_id}"))
    
    admin_msg = f"🔐 নতুন VPN অর্ডার:\n\n📦 Order ID: {order_id}\n👤 User: @{message.from_user.username or 'N/A'}\n🆔 User ID: {user_id}\n🔒 VPN: {vpn}\n💰 Amount: {price} TK\n💳 Method: {method}\n📝 Txn ID: {txn_id}\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
    
    user_confirmation = f"✅ আপনার অর্র্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n🔒 Service: {vpn}\n💰 Paid: {price} TK\n\nআপনার অর্র্ডারটি প্রসেস করা হচ্ছে। \nডেলিভারি সময়: ১-৬ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
    bot.send_message(message.chat.id, user_confirmation)
    home_menu(message.chat.id)
# --- End of VPN Flow ---


# --- YouTube Premium Flow (Stock-Aware) ---
@bot.message_handler(func=lambda m: m.text == "🎥 YouTube Premium")
def yt_premium(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    options_available = False
    
    if service_stock.get("yt_1_month", -1) != 0:
        markup.add(f"1 Month ({YT_1M_PRICE}TK)")
        options_available = True
    if service_stock.get("yt_1_year", -1) != 0:
        markup.add(f"1 Year ({YT_1Y_PRICE}TK)")
        options_available = True

    if not options_available:
        bot.send_message(message.chat.id, "❌ দুঃখিত, সকল YouTube Premium প্যাকেজ বর্তমানে স্টক আউট আছে।")
        return home_menu(message.chat.id)
        
    yt_options = """
🎬 YouTube Premium প্যাকেজ:
(স্টক আউট থাকলে অপশন দেখাবে না)
"""
    markup.add("↩️ মেনুতে ফিরে যান")
    msg = bot.send_message(message.chat.id, yt_options, reply_markup=markup)
    bot.register_next_step_handler(msg, select_yt_plan)

def select_yt_plan(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
        
    selected_plan = message.text
    
    if selected_plan == f"1 Month ({YT_1M_PRICE}TK)" and service_stock.get("yt_1_month", -1) != 0:
        price = YT_1M_PRICE
    elif selected_plan == f"1 Year ({YT_1Y_PRICE}TK)" and service_stock.get("yt_1_year", -1) != 0:
        price = YT_1Y_PRICE
    else:
        bot.send_message(message.chat.id, "❌ অবৈধ নির্বাচন বা স্টক আউট। আবার চেষ্টা করুন।"); return yt_premium(message)
        
    user_id = str(message.from_user.id)
    if user_id not in users: users[user_id] = {}
    users[user_id]["yt_plan"] = selected_plan
    
    order_summary = f"📝 অর্ডার সারাংশ:\n\n🎬 Service: {selected_plan}\n💰 মূল্য: {price} TK\n\n💳 পেমেন্ট মাধ্যম নির্বাচন করুন:"
    bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
    bot.register_next_step_handler(message, process_yt_payment)

def process_yt_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    
    user_id = str(message.from_user.id)
    if user_id not in users or "yt_plan" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন."); return yt_premium(message)
    
    yt_plan = users[user_id]["yt_plan"]
    price = YT_1M_PRICE if "Month" in yt_plan else YT_1Y_PRICE

    if message.text == "💰 Balance":
        # --- Handle Balance Payment ---
        service_name = f"YouTube Premium ({yt_plan})"
        
        def create_yt_order_from_balance(msg):
            order_id = f"YT{int(time.time())}{user_id}"
            orders[order_id] = {
                "user_id": user_id, "service": "YouTube Premium", "type": yt_plan, 
                "price": price, "method": "Balance", "txn_id": "N/A", "status": "pending"
            }
            save_data()
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_yt_{order_id}"))
            
            admin_msg = f"""
📺 নতুন YouTube Premium অর্ডার (Balance):

📦 Order ID: {order_id}
👤 User: @{message.from_user.username or 'N/A'}
🆔 User ID: {user_id}
🎬 Plan: {yt_plan}
💰 Amount: {price} TK
💳 Method: Balance
📝 Txn ID: N/A
⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
            bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
            
            user_confirmation = f"""
✅ আপনার অর্ডার কনফার্ম হয়েছে! (Paid with Balance)

📦 Order ID: {order_id}
🎬 Service: {yt_plan}
💰 Paid: {price} TK
💳 আপনার নতুন ব্যালেন্স: {users[user_id]['balance']} TK

আপনার অর্ডারটি প্রসেস করা হচ্ছে। 
ডেলিভারি সময়: ১-৬ ঘন্টা
সেবা নেওয়ার জন্য ধন্যবাদ! 🙏
"""
            bot.send_message(message.chat.id, user_confirmation)
            home_menu(message.chat.id)

        handle_balance_payment(
            message, 
            service_name, 
            price, 
            on_success_callback=create_yt_order_from_balance, 
            on_fail_callback=home_menu
        )
        return # Stop execution

    elif message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"; 
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=payment_markup())
        bot.register_next_step_handler(msg, process_yt_payment); return
        
    # --- Existing Bkash/Nagad logic ---
    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    
    payment_instructions = f"💳 {method} এ টাকা পাঠান:\n\n📱 Number: {payment_number}\n💰 Amount: {price} TK\n📝 Reference: YT\n\n⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন\n\n📨 এখন আপনার Transaction ID লিখুন:"
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_yt_order(m, method, price))


def confirm_yt_order(message, method, price):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    txn_id = message.text
    user_id = str(message.from_user.id)
    if user_id not in users or "yt_plan" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন."); return yt_premium(message)
        
    yt_plan = users[user_id]["yt_plan"]
    order_id = f"YT{int(time.time())}{user_id}"
    orders[order_id] = {"user_id": user_id, "service": "YouTube Premium", "type": yt_plan, "price": price, "method": method, "txn_id": txn_id, "status": "pending"}
    save_data()
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_yt_{order_id}"))
    
    admin_msg = f"📺 নতুন YouTube Premium অর্ডার:\n\n📦 Order ID: {order_id}\n👤 User: @{message.from_user.username or 'N/A'}\n🆔 User ID: {user_id}\n🎬 Plan: {yt_plan}\n💰 Amount: {price} TK\n💳 Method: {method}\n📝 Txn ID: {txn_id}\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
    
    user_confirmation = f"✅ আপনার অর্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n🎬 Service: {yt_plan}\n💰 Paid: {price} TK\n\nআপনার অর্ডারটি প্রসেস করা হচ্ছে। \nডেলিভারি সময়: ১-৬ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
    bot.send_message(message.chat.id, user_confirmation)
    home_menu(message.chat.id)
# --- End of YouTube Premium Flow ---


# --- NEW: Crunchyroll Premium Flow (Stock-Aware) ---
@bot.message_handler(func=lambda m: m.text == "🍿 Crunchyroll Premium")
def crunchyroll_buy(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return
    
    # Stock Check
    if service_stock.get("crunchyroll_7_day", -1) == 0:
        bot.send_message(message.chat.id, "❌ দুঃখিত, Crunchyroll Premium বর্তমানে স্টক আউট আছে।")
        return home_menu(message.chat.id)
        
    plan_text = f"7 Days ({CRUNCHYROLL_PRICE}TK)"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(plan_text, "↩️ মেনুতে ফিরে যান")
    
    options = f"""
🍿 Crunchyroll Premium প্যাকেজ:
{plan_text}
- ৭ দিনের প্রিমিয়াম অ্যাক্সেস
- দ্রুত ডেলিভারি
"""
    msg = bot.send_message(message.chat.id, options, reply_markup=markup)
    bot.register_next_step_handler(msg, select_crunchyroll_plan)

def select_crunchyroll_plan(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
        
    selected_plan = message.text
    plan_text = f"7 Days ({CRUNCHYROLL_PRICE}TK)"
    
    if selected_plan != plan_text:
        bot.send_message(message.chat.id, "❌ অবৈধ নির্বাচন। আবার চেষ্টা করুন।"); return crunchyroll_buy(message)
        
    price = CRUNCHYROLL_PRICE
    user_id = str(message.from_user.id)
    if user_id not in users: users[user_id] = {}
    users[user_id]["cr_plan"] = selected_plan
    
    order_summary = f"📝 অর্ডার সারাংশ:\n\n🍿 Service: {selected_plan}\n💰 মূল্য: {price} TK\n\n💳 পেমেন্ট মাধ্যম নির্বাচন করুন:"
    bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
    bot.register_next_step_handler(message, process_crunchyroll_payment)

def process_crunchyroll_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    
    user_id = str(message.from_user.id)
    if user_id not in users or "cr_plan" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন."); return crunchyroll_buy(message)
    
    cr_plan = users[user_id]["cr_plan"]
    price = CRUNCHYROLL_PRICE

    if message.text == "💰 Balance":
        # --- Handle Balance Payment ---
        service_name = f"Crunchyroll Premium ({cr_plan})"
        
        def create_cr_order_from_balance(msg):
            order_id = f"CR{int(time.time())}{user_id}"
            orders[order_id] = {
                "user_id": user_id, "service": "Crunchyroll Premium", "type": cr_plan, 
                "price": price, "method": "Balance", "txn_id": "N/A", "status": "pending"
            }
            save_data()
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_cr_{order_id}"))
            
            admin_msg = f"""
🍿 নতুন Crunchyroll অর্ডার (Balance):

📦 Order ID: {order_id}
👤 User: @{message.from_user.username or 'N/A'}
🆔 User ID: {user_id}
🎬 Plan: {cr_plan}
💰 Amount: {price} TK
💳 Method: Balance
📝 Txn ID: N/A
⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
            bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
            
            user_confirmation = f"""
✅ আপনার অর্ডার কনফার্ম হয়েছে! (Paid with Balance)

📦 Order ID: {order_id}
🎬 Service: {cr_plan}
💰 Paid: {price} TK
💳 আপনার নতুন ব্যালেন্স: {users[user_id]['balance']} TK

আপনার অর্ডারটি প্রসেস করা হচ্ছে। 
ডেলিভারি সময়: ১-৬ ঘন্টা
সেবা নেওয়ার জন্য ধন্যবাদ! 🙏
"""
            bot.send_message(message.chat.id, user_confirmation)
            home_menu(message.chat.id)

        handle_balance_payment(
            message, 
            service_name, 
            price, 
            on_success_callback=create_cr_order_from_balance, 
            on_fail_callback=home_menu
        )
        return # Stop execution

    elif message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"; 
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=payment_markup())
        bot.register_next_step_handler(msg, process_crunchyroll_payment); return
        
    # --- Existing Bkash/Nagad logic ---
    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    
    payment_instructions = f"💳 {method} এ টাকা পাঠান:\n\n📱 Number: {payment_number}\n💰 Amount: {price} TK\n📝 Reference: CR\n\n⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন\n\n📨 এখন আপনার Transaction ID লিখুন:"
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_crunchyroll_order(m, method, price))


def confirm_crunchyroll_order(message, method, price):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    txn_id = message.text
    user_id = str(message.from_user.id)
    if user_id not in users or "cr_plan" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন."); return crunchyroll_buy(message)
        
    cr_plan = users[user_id]["cr_plan"]
    order_id = f"CR{int(time.time())}{user_id}"
    orders[order_id] = {"user_id": user_id, "service": "Crunchyroll Premium", "type": cr_plan, "price": price, "method": method, "txn_id": txn_id, "status": "pending"}
    save_data()
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_cr_{order_id}"))
    
    admin_msg = f"🍿 নতুন Crunchyroll অর্ডার:\n\n📦 Order ID: {order_id}\n👤 User: @{message.from_user.username or 'N/A'}\n🆔 User ID: {user_id}\n🎬 Plan: {cr_plan}\n💰 Amount: {price} TK\n💳 Method: {method}\n📝 Txn ID: {txn_id}\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
    
    user_confirmation = f"✅ আপনার অর্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n🎬 Service: {cr_plan}\n💰 Paid: {price} TK\n\nআপনার অর্ডারটি প্রসেস করা হচ্ছে। \nডেলিভারি সময়: ১-৬ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
    bot.send_message(message.chat.id, user_confirmation)
    home_menu(message.chat.id)
# --- End of Crunchyroll Premium Flow ---


# --- NEW: Google Veo 3 Flow (Stock-Aware) ---
@bot.message_handler(func=lambda m: m.text == "🧠 Google Veo 3 (Gemin)")
def veo_buy(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    options_available = False
    
    if service_stock.get("veo_1_month", -1) != 0:
        markup.add(f"1 Month ({VEO_1M_PRICE}TK)")
        options_available = True
    if service_stock.get("veo_12_month", -1) != 0:
        markup.add(f"12 Month ({VEO_12M_PRICE}TK)")
        options_available = True

    if not options_available:
        bot.send_message(message.chat.id, "❌ দুঃখিত, সকল Google Veo 3 প্যাকেজ বর্তমানে স্টক আউট আছে।")
        return home_menu(message.chat.id)
        
    options = """
🧠 Google Veo 3 (Gemin) প্যাকেজ:
(স্টক আউট থাকলে অপশন দেখাবে না)
"""
    markup.add("↩️ মেনুতে ফিরে যান")
    msg = bot.send_message(message.chat.id, options, reply_markup=markup)
    bot.register_next_step_handler(msg, select_veo_plan)

def select_veo_plan(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
        
    selected_plan = message.text
    
    if selected_plan == f"1 Month ({VEO_1M_PRICE}TK)" and service_stock.get("veo_1_month", -1) != 0:
        price = VEO_1M_PRICE
    elif selected_plan == f"12 Month ({VEO_12M_PRICE}TK)" and service_stock.get("veo_12_month", -1) != 0:
        price = VEO_12M_PRICE
    else:
        bot.send_message(message.chat.id, "❌ অবৈধ নির্বাচন বা স্টক আউট। আবার চেষ্টা করুন।"); return veo_buy(message)
        
    user_id = str(message.from_user.id)
    if user_id not in users: users[user_id] = {}
    users[user_id]["veo_plan"] = selected_plan
    
    order_summary = f"📝 অর্ডার সারাংশ:\n\n🧠 Service: {selected_plan}\n💰 মূল্য: {price} TK\n\n💳 পেমেন্ট মাধ্যম নির্বাচন করুন:"
    bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
    
    # Pass price as an argument to the next step handler
    bot.register_next_step_handler(message, process_veo_payment, price)

def process_veo_payment(message, price):
    """
    Handles VEO payment, including the new 'Balance' option.
    'price' is passed directly from the select_veo_plan step.
    """
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    
    user_id = str(message.from_user.id)
    if user_id not in users or "veo_plan" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন."); return veo_buy(message)
    
    veo_plan = users[user_id]["veo_plan"]

    if message.text == "💰 Balance":
        # --- Handle Balance Payment ---
        service_name = f"Google Veo 3 ({veo_plan})"
        
        def create_veo_order_from_balance(msg):
            order_id = f"VEO{int(time.time())}{user_id}"
            orders[order_id] = {
                "user_id": user_id, "service": "Google Veo 3", "type": veo_plan, 
                "price": price, "method": "Balance", "txn_id": "N/A", "status": "pending"
            }
            save_data()
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_veo_{order_id}"))
            
            admin_msg = f"""
🧠 নতুন Google Veo 3 অর্ডার (Balance):

📦 Order ID: {order_id}
👤 User: @{message.from_user.username or 'N/A'}
🆔 User ID: {user_id}
🎬 Plan: {veo_plan}
💰 Amount: {price} TK
💳 Method: Balance
📝 Txn ID: N/A
⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
            bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
            
            user_confirmation = f"""
✅ আপনার অর্ডার কনফার্ম হয়েছে! (Paid with Balance)

📦 Order ID: {order_id}
🎬 Service: {veo_plan}
💰 Paid: {price} TK
💳 আপনার নতুন ব্যালেন্স: {users[user_id]['balance']} TK

আপনার অর্ডারটি প্রসেস করা হচ্ছে। 
ডেলিভারি সময়: ১-৬ ঘন্টা
সেবা নেওয়ার জন্য ধন্যবাদ! 🙏
"""
            bot.send_message(message.chat.id, user_confirmation)
            home_menu(message.chat.id)

        handle_balance_payment(
            message, 
            service_name, 
            price, 
            on_success_callback=create_veo_order_from_balance, 
            on_fail_callback=home_menu
        )
        return # Stop execution
    
    elif message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"; 
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=payment_markup())
        bot.register_next_step_handler(msg, process_veo_payment, price); return # Pass price again
        
    # --- Existing Bkash/Nagad logic ---
    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    
    payment_instructions = f"💳 {method} এ টাকা পাঠান:\n\n📱 Number: {payment_number}\n💰 Amount: {price} TK\n📝 Reference: VEO\n\n⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন\n\n📨 এখন আপনার Transaction ID লিখুন:"
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_veo_order(m, method, price))


def confirm_veo_order(message, method, price):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message); return home_menu(message.chat.id)
    txn_id = message.text
    user_id = str(message.from_user.id)
    if user_id not in users or "veo_plan" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন."); return veo_buy(message)
        
    veo_plan = users[user_id]["veo_plan"]
    order_id = f"VEO{int(time.time())}{user_id}"
    orders[order_id] = {"user_id": user_id, "service": "Google Veo 3", "type": veo_plan, "price": price, "method": method, "txn_id": txn_id, "status": "pending"}
    save_data()
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_veo_{order_id}"))
    
    admin_msg = f"🧠 নতুন Google Veo 3 অর্ডার:\n\n📦 Order ID: {order_id}\n👤 User: @{message.from_user.username or 'N/A'}\n🆔 User ID: {user_id}\n🎬 Plan: {veo_plan}\n💰 Amount: {price} TK\n💳 Method: {method}\n📝 Txn ID: {txn_id}\n⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)
    
    user_confirmation = f"✅ আপনার অর্ডার কনফার্ম হয়েছে!\n\n📦 Order ID: {order_id}\n🎬 Service: {veo_plan}\n💰 Paid: {price} TK\n\nআপনার অর্ডারটি প্রসেস করা হচ্ছে। \nডেলিভারি সময়: ১-৬ ঘন্টা\n\nসেবা নেওয়ার জন্য ধন্যবাদ! 🙏"
    bot.send_message(message.chat.id, user_confirmation)
    home_menu(message.chat.id)
# --- End of Google Veo 3 Flow ---


# --- Balance, Withdraw, Refer, Support (Updated) ---
@bot.message_handler(func=lambda m: m.text == "💳 Balance")
def check_balance(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return
    if user_id in users:
        balance = users[user_id].get("balance", 0)
        hold = users[user_id].get("hold", 0)
        ref_count = users[user_id].get("referral_count", 0)
        join_date = users[user_id].get("joined_date", "N/A")
        estimated_earnings = balance + hold + (ref_count * 2)
        balance_msg = f"💰 আপনার একাউন্ট বিবরণী:\n\n💵 Available Balance: {balance} TK\n⏳ Hold Balance: {hold} TK\n💰 Total Balance: {balance + hold} TK\n👥 Referrals: {ref_count} জন\n📈 Estimated Earnings: {estimated_earnings} TK\n📅 Join Date: {join_date}\n\n💡 টাকা উত্তোলন করতে '💵 Withdraw' অপশন ব্যবহার করুন"
        bot.send_message(message.chat.id, balance_msg)
    else:
        error_msg = "❌ একাউন্ট খুঁজে পাওয়া যায়নি!\n\n/start লিখে আবার রেজিস্টার করুন"
        bot.send_message(message.chat.id, error_msg)

@bot.message_handler(func=lambda m: m.text == "💵 Withdraw")
def withdraw(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return
    if user_id in users:
        balance = users[user_id]["balance"]
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
        balance = users[user_id]["balance"]
        if amount < MIN_WITHDRAW:    
            error_msg = f"❌ সর্বনিম্ন {MIN_WITHDRAW} টাকা উত্তোলন করতে পারবেন!\n\nআবার চেষ্টা করুন:"; 
            msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())    
            bot.register_next_step_handler(msg, process_withdraw_amount); return    
        if amount > balance:    
            error_msg = f"❌ আপনার একাউন্টে পর্যাপ্ত টাকা নেই!\n\n💰 আপনার ব্যালেন্স: {balance} TK\n💸 চাহিদাকৃত: {amount} TK\n📉 ঘাটতি: {amount - balance} TK\n\nকম পরিমাণ লিখুন:"; 
            msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())    
            bot.register_next_step_handler(msg, process_withdraw_amount); return    
        
        users[user_id]["balance"] -= amount    
        users[user_id]["hold"] += amount
        save_data()
        
        method_msg = "📲 উত্তোলনের মাধ্যম নির্বাচন করুন:"
        msg = bot.send_message(message.chat.id, method_msg, reply_markup=withdraw_method_markup())    
        bot.register_next_step_handler(msg, lambda m: process_withdraw_method(m, amount))
    except:
        error_msg = f"❌ অবৈধ পরিমাণ! শুধুমাত্র সংখ্যা লিখুন:\n\nউদাহরণ: {MIN_WITHDRAW}, 100, 200\n\nআবার চেষ্টা করুন:"; 
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, process_withdraw_amount)

def process_withdraw_method(message, amount):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        users[str(message.from_user.id)]["balance"] += amount
        users[str(message.from_user.id)]["hold"] -= amount
        save_data(); return home_menu(message.chat.id)
        
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
        # Fallback, should not happen
        number_msg = "📱 আপনার একাউন্ট নম্বর লিখুন:"

    msg = bot.send_message(message.chat.id, number_msg, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_withdraw_request(m, amount, method_name))

def confirm_withdraw_request(message, amount, method):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        users[str(message.from_user.id)]["balance"] += amount
        users[str(message.from_user.id)]["hold"] -= amount
        save_data(); return home_menu(message.chat.id)
        
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
    
    orders[withdraw_id] = {
        "user_id": user_id, 
        "service": "Withdrawal", 
        "amount": amount, 
        "fee": fee,
        "final_amount": final_amount_to_pay,
        "method": method, 
        "account": account_details, 
        "status": "pending"
    }
    save_data()
    
    markup.add(types.InlineKeyboardButton("✅ Pay (Funds are on hold)", callback_data=f"pay_{user_id}_{amount}_{withdraw_id}"))
    
    admin_msg = f"""
💸 নতুন উত্তোলনের অনুরোধ:

📋 Withdrawal ID: {withdraw_id}
👤 User: @{message.from_user.username or 'N/A'}
🆔 User ID: {user_id}
💰 Amount: {amount} TK
💸 Fee: {fee} TK
💵 To Pay: {final_amount_to_pay} TK
💳 Method: {method}
📞 Account: {account_details}
⏰ Time: {time.strftime('%Y-%m-%d %H:%M:%S')}

💡 User Balance (After Hold): {users[user_id]['balance']} TK
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
    if user_id in users and users[user_id].get("is_blocked"): return
    if user_id in users:
        ref_count = users[user_id]["referral_count"]
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
    else:
        error_msg = "❌ একাউন্ট খুঁজে পাওয়া যায়নি!\n\n/start লিখে আবার রেজিস্টার করুন"; bot.send_message(message.chat.id, error_msg)

@bot.message_handler(func=lambda m: m.text == "🆘 Support")
def support(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return
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
# --- Admin Panel (Button System) ---
# ----------------------------------------------------

def admin_markup():
    """Creates the main admin keyboard markup."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📊 স্ট্যাটাস", "💰 ব্যালেন্স ম্যানেজ")
    markup.add("👤 ইউজার/ব্রডকাস্ট", "🚫 ব্লক/আনব্লক")
    markup.add("📧 Gmail টাস্ক ম্যানেজ", "📦 স্টক ম্যানেজ") # Added Stock
    markup.add("↩️ মেনুতে ফিরে যান")
    return markup

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ আপনার অনুমতি নেই!")
        return
    
    bot.clear_step_handler(message)

    total_users = len(users)
    total_balance = sum(user.get("balance", 0) for user in users.values())
    total_hold = sum(user.get("hold", 0) for user in users.values())
    total_pending_gmails = sum(len(sub["gmails"]) for subs in pending_gmails.values() for sub in subs.values() if subs)
    total_available_tasks = len(available_gmail_tasks)
    total_active_tasks = len(active_gmail_tasks)

    admin_msg = f"""
👑 অ্যাডমিন প্যানেল:

📊 স্ট্যাটিস্টিক্স (সারসংক্ষেপ):
👥 মোট ইউজার: {total_users}
💰 মোট ব্যালেন্স: {total_balance} TK
⏳ মোট Hold: {total_hold} TK
📧 Pending Gmail Submissions: {total_pending_gmails} টি
📋 Available Gmail Tasks: {total_available_tasks} টি
🏃 Active Gmail Tasks: {total_active_tasks} টি

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

# --- Admin Sub-Menu Handlers ---

def admin_show_stats(message):
    """Handles the '📊 স্ট্যাটাস' button"""
    total_earnings = sum(user.get("balance", 0) + user.get("hold", 0) for user in users.values())
    total_ref_earnings = sum(user.get("referral_count", 0) * 2 for user in users.values())
    total_gmail_earnings = total_earnings - total_ref_earnings
    
    stats_msg = f"""
📈 বিস্তারিত স্ট্যাটিস্টিক্স:

💰 মোট আয় (All Time): {total_earnings} TK
📧 Gmail, Buy/Sell, Other: {total_gmail_earnings} TK
👥 রেফার থেকে: {total_ref_earnings} TK

📊 ইউজার এক্টিভিটি:
- মোট ইউজার: {len(users)}
- গড় ব্যালেন্স: {total_earnings/len(users) if len(users) > 0 else 0:.2f} TK/User
- গড় রেফার: {sum(user.get('referral_count', 0) for user in users.values())/len(users) if len(users) > 0 else 0:.2f}/User
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
    users_list = "\n".join([f"👤 @{u.get('username', 'N/A')} | ID: {uid} | Bal: {u.get('balance', 0)} TK" for uid, u in list(users.items())[:10]])
    users_msg = f"👥 সর্বশেষ ১০ ইউজার:\n\n{users_list}\n\n💡 সকল ইউজার ডাউনলোড করতে নিচের বাটনটি ব্যবহার করুন:"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬇️ সকল ইউজার ডাউনলোড (.txt)", callback_data="download_all_users"))
    
    bot.send_message(message.chat.id, users_msg, reply_markup=markup)
    
    # Return to User/Broadcast menu
    markup = types.ReplyKey