import telebot
from telebot import types
import time
import json
import os
import uuid
from collections import defaultdict

TOKEN = '8204693585:AAHo3H_NsANMskc9ubQICp2MKP6H-K0dcdg'
ADMIN_ID = '7943354448'
ADMIN_BKASH_NO = '01774049543'
ADMIN_NAGAD_NO = '01774049543'
BOT_USERNAME = "sohojbuysellbdbot"

# Note: The TeleBot instance should be created after defining the token
bot = telebot.TeleBot(TOKEN)

# --- Global Data Structures ---
users = {}
pending_gmails = defaultdict(dict) # Nested dict for batch processing
orders = {}
# Global variable for admin session data (to manage multi-step commands like /balance and /block)
admin_sessions = {} 
# --- End of Global Data Structures ---


# --- Data Persistence Functions ---
def save_data():
    """Saves all persistent data (users, orders, pending_gmails)."""
    try:
        with open('users.json', 'w', encoding='utf-8') as f:
            # Convert defaultdict to dict before saving
            json.dump({
                "users": users,
                "orders": orders,
                "pending_gmails": dict(pending_gmails)
            }, f, indent=4)
        print("All data saved successfully.")
    except Exception as e:
        print(f"Error saving data: {e}")

def load_data():
    """Loads all persistent data from a JSON file."""
    global users, orders, pending_gmails
    if os.path.exists('users.json'):
        try:
            with open('users.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                users = data.get("users", {})
                orders = data.get("orders", {})
                
                # Convert back to defaultdict
                loaded_pending_gmails = data.get("pending_gmails", {})
                pending_gmails.clear()
                pending_gmails.update(loaded_pending_gmails)
                
            print("All data loaded successfully.")
        except json.JSONDecodeError:
            print("Corrupted users.json file. Starting with empty data.")
            users = {}
            orders = {}
            pending_gmails.clear()
    else:
        print("users.json not found. Creating new data structures.")
        users = {}
        orders = {}
        pending_gmails.clear()

# --- Bot Initialization ---
load_data()
# --- End of Data Persistence Functions ---

LOGO = """
╔═════════════════════════╗
║    🛒 Sohoj Buy Sell BD    ║
╚═════════════════════════╝

🌟 আপনার ডিজিটাল সার্ভিসের বিশ্বস্ত পার্টনার 🌟
"""

def home_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        "📤 Gmail Sell", "📥 Gmail Buy", "📞 Twillo Sid Buy",
        "💳 Balance", "💵 Withdraw",
        "🌐 Paid VPN Buy", "🎥 YouTube Premium",
        "👥 Refer", "🆘 Support",
        "🎁 Play Point Park On"
    ]
    markup.add(*buttons)
    
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

def back_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("↩️ মেনুতে ফিরে যান")
    return markup

def payment_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📲 Bkash", "📲 Nagad", "↩️ মেনুতে ফিরে যান")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    
    # Check for block status first
    if user_id in users and users[user_id].get("is_blocked"):
        bot.send_message(message.chat.id, "❌ আপনাকে এই বট ব্যবহার থেকে ব্লক করা হয়েছে। Admin এর সাথে যোগাযোগ করুন।")
        return
        
    bot.send_message(message.chat.id, LOGO)
    time.sleep(0.5)

    is_new_user = user_id not in users

    if is_new_user:
        users[user_id] = {
            "username": message.from_user.username,
            "balance": 0,
            "hold": 0,
            "referral_count": 0,
            "referred_users": [],
            "joined_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "is_blocked": False # New block flag added
        }
        save_data()

    if len(message.text.split()) > 1:
        referrer_id_str = message.text.split()[1]
        try:
            if referrer_id_str in users and referrer_id_str != user_id:
                if user_id not in users[referrer_id_str]["referred_users"]:
                    users[referrer_id_str]["balance"] += 2
                    users[referrer_id_str]["referral_count"] += 1
                    users[referrer_id_str]["referred_users"].append(user_id)
                    bot.send_message(referrer_id_str, f"🎉 আপনি ২ টাকা পেয়েছেন রেফার বোনাস হিসেবে! নতুন ইউজার: @{message.from_user.username or 'NoUsername'}")
                    save_data()
        except:
            pass # Ignore if referrer_id_str is not a valid user ID

    welcome_msg = f"""
✨ স্বাগতম {message.from_user.first_name}!

ডিজিটাল Sohoj Buy Sell BD বটে আপনাকে স্বাগতম! 🎉

🔹 Gmail বিক্রি/ক্রয়
🔹 Premium VPN সার্ভিস
🔹 Twillo Sid Buy
🔹 YouTube Premium অ্যাকাউন্ট
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

# --- Play Point Park On Flow ---

@bot.message_handler(func=lambda m: m.text == "🎁 Play Point Park On")
def play_point_menu(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return

    options = """
🌍 দেশ নির্বাচন করুন:

🇺🇸 USA
🇹🇼 Taiwan
🇬🇧 UK
🇰🇷 South Korean

💡 প্রতিটি Park On-এর জন্য 20 টাকা খরচ হবে
"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🇺🇸 USA", "🇹🇼 Taiwan", "🇬🇧 UK", "🇰🇷 South Korean", "↩️ মেনুতে ফিরে যান")
    msg = bot.send_message(message.chat.id, options, reply_markup=markup)
    bot.register_next_step_handler(msg, process_play_point_country)

def process_play_point_country(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)
    
    country = message.text
    user_id = str(message.from_user.id)
    if user_id not in users: users[user_id] = {} # Safety check
    
    users[user_id]["play_point_country"] = country
    quantity_msg = f"""
🔢 কতগুলো Park On চান?

💡 পরিমাণ লিখুন (সংখ্যা):
"""
    msg = bot.send_message(message.chat.id, quantity_msg, reply_markup=back_markup())
    bot.register_next_step_handler(msg, process_play_point_quantity)

def process_play_point_quantity(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)
    
    try:
        quantity = int(message.text)
        if quantity <= 0:
            raise ValueError
        
        user_id = str(message.from_user.id)
        if user_id not in users: return home_menu(message.chat.id) # Session check

        users[user_id]["play_point_quantity"] = quantity
        total_price = quantity * 20
        users[user_id]["play_point_price"] = total_price
        
        details_msg = f"""
💰 মোট মূল্য: {total_price} টাকা

এখন আপনি যে Gmail/Password-গুলোতে Park On করতে চান সেগুলো একসাথে লিখুন:
(প্রতি লাইনে একটি Gmail/Password)

ফরম্যাট:
example1@gmail.com/password1
example2@gmail.com/password2
"""
        msg = bot.send_message(message.chat.id, details_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, process_play_point_details)
        
    except ValueError:
        error_msg = """
❌ অবৈধ সংখ্যা! শুধুমাত্র সংখ্যা লিখুন।

আবার চেষ্টা করুন:
"""
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, process_play_point_quantity)

def process_play_point_details(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)
    
    user_id = str(message.from_user.id)
    if user_id not in users or "play_point_price" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।")
        return home_menu(message.chat.id)
        
    play_point_details = message.text
    users[user_id]["play_point_details"] = play_point_details

    order_summary = f"""
📝 অর্ডার সারাংশ:

🌍 Country: {users[user_id]["play_point_country"]}
🔢 Quantity: {users[user_id]["play_point_quantity"]} টি
💰 মোট মূল্য: {users[user_id]["play_point_price"]} TK

💳 পেমেন্ট মাধ্যম নির্বাচন করুন:
"""
    bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
    bot.register_next_step_handler(message, process_play_point_payment)

def process_play_point_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    user_id = str(message.from_user.id)
    if user_id not in users or "play_point_price" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।")
        return home_menu(message.chat.id)
        
    user_data = users[user_id]
    
    if message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=payment_markup())
        bot.register_next_step_handler(msg, process_play_point_payment)
        return
        
    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    price = user_data["play_point_price"]
    
    payment_instructions = f"""
💳 {method} এ টাকা পাঠান:

📱 Number: {payment_number}
💰 Amount: {price} TK
📝 Reference: PPON{user_id}

⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন

📨 এখন আপনার Transaction ID লিখুন:
"""
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_play_point_order(m, method, price))

def confirm_play_point_order(message, method, price):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)
        
    txn_id = message.text
    user_id = str(message.from_user.id)
    if user_id not in users or "play_point_details" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।")
        return home_menu(message.chat.id)
        
    order_id = f"PPON{int(time.time())}{user_id}"
    orders[order_id] = {
        "user_id": user_id,
        "service": "Play Point Park On",
        "country": users[user_id]["play_point_country"],
        "quantity": users[user_id]["play_point_quantity"],
        "details": users[user_id]["play_point_details"],
        "price": price,
        "method": method,
        "txn_id": txn_id,
        "status": "pending"
    }
    save_data() # Save the new order

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_pp_{order_id}")) # Changed to use order_id

    admin_msg = f"""
🎁 নতুন Play Point Park On অর্ডার:

📦 Order ID: {order_id}
👤 User: @{message.from_user.username or 'N/A'}
🆔 User ID: {user_id}
🌍 Country: {orders[order_id]["country"]}
🔢 Quantity: {orders[order_id]["quantity"]} টি
💰 Amount: {price} TK
💳 Method: {method}
📝 Txn ID: {txn_id}
⏰ Time: {time.strftime("%Y-%m-%d %H:%M:%S")}

📩 Gmail Details:
{orders[order_id]["details"]}
"""
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)

    user_confirmation = f"""
✅ আপনার অর্ডার কনফার্ম হয়েছে!

📦 Order ID: {order_id}
🎁 Service: Play Point Park On
💰 Paid: {price} TK

আপনার অর্ডারটি প্রসেস করা হচ্ছে।
ডেলিভারি সময়: ১-১২ ঘন্টা

সেবা নেওয়ার জন্য ধন্যবাদ! 🙏
"""
    bot.send_message(message.chat.id, user_confirmation)
    home_menu(message.chat.id)

# --- Gmail Sell Flow (Batch System) ---

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
        total_amount = approved_count * 6
        
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
        
        # Remove this submission
        del pending_gmails[user_id][submission_id]
        
        # If no more submissions for this user, remove user entry
        if not pending_gmails[user_id]:
            del pending_gmails[user_id]
        
        save_data()

@bot.message_handler(func=lambda m: m.text == "📤 Gmail Sell")
def gmail_sell(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return
    
    instructions = """
📧 Gmail বিক্রি করার নিয়ম:

1. ফরম্যাট: example@gmail.com:password
2. Gmail সম্পূর্ণ অ্যাক্সেস সহ হতে হবে
3. কোনো 2FA/2-Step Verification থাকা যাবে না
4. প্রতিটি Gmail এর জন্য পাবেন ৬ টাকা

⚠️ ভুল ফরম্যাট বা Fake Gmail দিলে টাকা দেওয়া হবে না

এখন আপনার Gmail আইডি ও পাসওয়ার্ড দিন:
(একাধিক Gmail দিতে চাইলে প্রতি লাইনে একটি করে দিন)

উদাহরণ:
example1@gmail.com:password1
example2@gmail.com:password2
"""
    msg = bot.send_message(message.chat.id, instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, process_gmail_sell)

def process_gmail_sell(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    user_id = str(message.from_user.id)
    gmail_list = message.text.strip().split('\n')
    valid_gmails = []
    
    for gmail in gmail_list:
        gmail = gmail.strip()
        if ":" in gmail and "@" in gmail:
            valid_gmails.append({
                "email": gmail,
                "status": "pending"
            })

    if not valid_gmails:
        error_msg = """
❌ ভুল ফরম্যাট! সঠিক ফরম্যাটে দিন:

example@gmail.com:password

আবার চেষ্টা করুন:
"""
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, process_gmail_sell)
        return
    
    # Generate unique submission ID for this batch
    submission_id = str(uuid.uuid4())[:8]
    
    # Store pending gmails with submission ID
    pending_gmails[user_id][submission_id] = {
        "gmails": valid_gmails,
        "timestamp": time.time()
    }
    
    # Calculate total hold amount
    total_hold = len(valid_gmails) * 6
    users[user_id]["hold"] += total_hold
    save_data()

    success_msg = f"""
✅ {len(valid_gmails)}টি Gmail জমা দেওয়া হয়েছে!

📧 মোট Gmail: {len(valid_gmails)}টি
💰 Hold Amount: {total_hold} TK

আপনার Gmail Admin এর রিভিউ এর জন্য পাঠানো হয়েছে। 
সঠিক হলে {total_hold} টাকা আপনার একাউন্টে যোগ করা হবে।

⏳ সর্বোচ্চ ২৪ ঘন্টার মধ্যে রিভিউ করা হবে।
"""
    bot.send_message(message.chat.id, success_msg)

    username = message.from_user.username or "NoUsername"
    
    admin_msg = f"""
📧 নতুন Gmail Submission:

👤 User: @{username}
🆔 ID: {user_id}
📅 Time: {time.strftime("%Y-%m-%d %H:%M:%S")}
📋 Submission ID: {submission_id}

👥 মোট Gmail: {len(valid_gmails)}টি
💰 সম্ভাব্য Amount: {total_hold} TK
"""
    bot.send_message(ADMIN_ID, admin_msg)

    # Create inline keyboard for each Gmail separately
    for i, gmail_data in enumerate(valid_gmails):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_gmail_{user_id}_{submission_id}_{i}"),
            types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_gmail_{user_id}_{submission_id}_{i}")
        )
        bot.send_message(ADMIN_ID, f"📧 Gmail {i+1}: {gmail_data['email']}", reply_markup=markup)


# --- Gmail Buy Flow (Corrected) ---

# Gmail প্রাইস সেটআপ
USA_GMAIL_PRICE = 15
BD_GMAIL_PRICE = 10

@bot.message_handler(func=lambda m: m.text == "📥 Gmail Buy")
def gmail_buy(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return
    
    options = """
🎯 Gmail টাইপ নির্বাচন করুন:

🇺🇸 USA Gmail (15TK)
- উচ্চ মানের Gmail
- বিশ্বব্যাপী অ্যাক্সেস
- দ্রুত ডেলিভারি

🇧🇩 BD Gmail (10TK)
- স্থানীয়ভাবে তৈরি
- ভাল মানের
- সাশ্রয়ী মূল্য
"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🇺🇸 USA Gmail (15TK)", "🇧🇩 BD Gmail (10TK)", "↩️ মেনুতে ফিরে যান")
    msg = bot.send_message(message.chat.id, options, reply_markup=markup)
    # Next step handler is correctly set to process the type selection
    bot.register_next_step_handler(msg, process_gmail_type)

def process_gmail_type(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)
    
    user_id = str(message.from_user.id)
    if user_id not in users: users[user_id] = {} # Safety check
    
    selected_text = message.text
    
    # 1. Determine Gmail Type and Price
    if selected_text == "🇺🇸 USA Gmail (15TK)":
        users[user_id]["gmail_type"] = "USA Gmail"
        users[user_id]["gmail_price_per"] = USA_GMAIL_PRICE
        selected_type = "USA Gmail"
        price_per = USA_GMAIL_PRICE
    elif selected_text == "🇧🇩 BD Gmail (10TK)":
        users[user_id]["gmail_type"] = "BD Gmail" 
        users[user_id]["gmail_price_per"] = BD_GMAIL_PRICE
        selected_type = "BD Gmail"
        price_per = BD_GMAIL_PRICE
    else:
        # Invalid selection, go back
        error_msg = "❌ দয়া করে একটি বৈধ অপশন সিলেক্ট করুন:"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("🇺🇸 USA Gmail (15TK)", "🇧🇩 BD Gmail (10TK)", "↩️ মেনুতে ফিরে যান")
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=markup)
        bot.register_next_step_handler(msg, process_gmail_type)
        return
    
    # 2. Ask for Quantity (No buttons, user must write the number)
    quantity_options = f"""
✅ {selected_type} সিলেক্ট করেছেন
💵 প্রতি একাউন্ট: {price_per} TK

🔢 কতটি Gmail অ্যাকাউন্ট কিনতে চান?
💡 শুধু সংখ্যা লিখুন:
"""
    
    msg = bot.send_message(message.chat.id, quantity_options, reply_markup=back_markup())
    # Next step is correctly set to process the quantity button click/text
    bot.register_next_step_handler(msg, process_gmail_quantity)

def process_gmail_quantity(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    user_id = str(message.from_user.id)
    
    # Safety check: Ensure type and price are set from previous step
    if user_id not in users or "gmail_type" not in users[user_id]:
        bot.send_message(message.chat.id, "❌ ডাটা লস্ট হয়েছে! দয়া করে আবার শুরু করুন:")
        return gmail_buy(message)

    try:
        quantity = int(message.text)
        if quantity <= 0:
            raise ValueError
    except ValueError:
        error_msg = "❌ অবৈধ সংখ্যা! শুধুমাত্র সংখ্যা লিখুন:"
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, process_gmail_quantity)
        return

    # Get stored data
    gmail_type = users[user_id].get("gmail_type")
    price_per = users[user_id].get("gmail_price_per")
    
    # Calculate price
    price = price_per * quantity
    
    # Discount calculation
    discount_msg = ""
    discount = 0
    if quantity >= 10:
        discount = price * 0.10
        price -= discount
        discount_msg = f"🎉 ১০+ অর্ডারে ১০% ডিসকাউন্ট পেয়েছেন! (-{discount:.0f} TK)"
    elif quantity >= 5:
        discount = price * 0.05
        price -= discount
        discount_msg = f"🎉 ৫+ অর্ডারে ৫% ডিসকাউন্ট পেয়েছেন! (-{discount:.0f} TK)"
    
    # Store final data
    users[user_id]["gmail_quantity"] = quantity
    users[user_id]["gmail_price"] = int(price)
    
    order_summary = f"""
📝 অর্ডার সারাংশ:

📧 Type: {gmail_type}
🔢 Quantity: {quantity} টি
💵 প্রতি একাউন্ট: {price_per} TK
{discount_msg}
💰 মোট মূল্য: {int(price)} TK

💳 পেমেন্ট মাধ্যম নির্বাচন করুন:
"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📲 Bkash", "📲 Nagad", "↩️ মেনুতে ফিরে যান")
    bot.send_message(message.chat.id, order_summary, reply_markup=markup)
    bot.register_next_step_handler(message, process_gmail_payment)

def process_gmail_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    user_id = str(message.from_user.id)
    
    # Safety check: Ensure all data is present
    if user_id not in users or "gmail_price" not in users[user_id]:
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন:")
        return gmail_buy(message)
    
    user_data = users[user_id]

    if message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add("📲 Bkash", "📲 Nagad", "↩️ মেনুতে ফিরে যান")
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=markup)
        bot.register_next_step_handler(msg, process_gmail_payment)
        return

    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    
    # Get the FINAL data
    gmail_type = user_data.get("gmail_type", "N/A")
    quantity = user_data.get("gmail_quantity", 0)
    price = user_data.get("gmail_price", 0)

    payment_instructions = f"""
💳 {method} এ টাকা পাঠান:

📱 Number: {payment_number}
💰 Amount: {price} TK
📝 Reference: Gmail{quantity}

⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন

📨 এখন আপনার Transaction ID লিখুন:
"""
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_gmail_order(m, method, price, gmail_type, quantity))

def confirm_gmail_order(message, method, price, gmail_type, quantity):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    txn_id = message.text.strip()
    
    if len(txn_id) < 3:
        error_msg = "❌ অবৈধ Transaction ID! দয়া করে সঠিক Transaction ID লিখুন:"
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, lambda m: confirm_gmail_order(m, method, price, gmail_type, quantity))
        return

    user_id = str(message.from_user.id)

    order_id = f"GMAIL{int(time.time())}{user_id}"
    
    orders[order_id] = {
        "user_id": user_id,
        "service": "Gmail",
        "type": gmail_type,
        "quantity": quantity,
        "price": price,
        "method": method,
        "txn_id": txn_id,
        "status": "pending"
    }
    save_data() # Save the new order

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_gmail_{order_id}"))

    admin_msg = f"""
🛒 নতুন Gmail অর্ডার:

📦 Order ID: {order_id}
👤 User: @{message.from_user.username or 'N/A'}
🆔 User ID: {user_id}
📧 Type: {gmail_type}
🔢 Quantity: {quantity} টি
💰 Amount: {price} TK
💳 Method: {method}
📝 Txn ID: {txn_id}
⏰ Time: {time.strftime("%Y-%m-%d %H:%M:%S")}
"""
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)

    user_confirmation = f"""
✅ আপনার অর্ডার কনফার্ম হয়েছে!

📦 Order ID: {order_id}
📧 Service: {gmail_type}
🔢 Quantity: {quantity} টি
💰 Paid: {price} TK

আপনার অর্ডারটি প্রসেস করা হচ্ছে। 
ডেলিভারি সময়: ১-১২ ঘন্টা

সেবা নেওয়ার জন্য ধন্যবাদ! 🙏
"""
    bot.send_message(message.chat.id, user_confirmation)
    
    # Clear temporary user data after order completion
    if user_id in users:
        users[user_id].pop("gmail_type", None)
        users[user_id].pop("gmail_price_per", None)
        users[user_id].pop("gmail_quantity", None)
        users[user_id].pop("gmail_price", None)
    
    home_menu(message.chat.id)

# --- Twillo SID Buy Flow ---

@bot.message_handler(func=lambda m: m.text == "📞 Twillo Sid Buy")
def twillo_sid_buy(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return
    
    options = """
📞 Twillo SID কিনুন:

💰 প্রতি SID এর দাম: ৭ টাকা

💡 Twillo SID Features:
- হাই কোয়ালিটি SID
- দ্রুত ডেলিভারি
- বিশ্বস্ত সার্ভিস

🔢 কতগুলো SID কিনতে চান? সংখ্যা লিখুন:
"""
    msg = bot.send_message(message.chat.id, options, reply_markup=back_markup())
    bot.register_next_step_handler(msg, process_twillo_quantity)

def process_twillo_quantity(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    try:
        quantity = int(message.text)
        if quantity <= 0:
            raise ValueError

        user_id = str(message.from_user.id)
        if user_id not in users: users[user_id] = {} # Safety check

        users[user_id]["twillo_quantity"] = quantity
        
        base_price = 7
        price = base_price * quantity
        
        # Discount calculation
        discount_msg = ""
        if quantity >= 10:
            discount = price * 0.10
            price -= discount
            discount_msg = f"🎉 ১০+ অর্ডারে ১০% ডিসকাউন্ট পেয়েছেন! (-{discount:.0f} TK)"
        elif quantity >= 5:
            discount = price * 0.05
            price -= discount
            discount_msg = f"🎉 ৫+ অর্ডারে ৫% ডিসকাউন্ট পেয়েছেন! (-{discount:.0f} TK)"
        
        users[user_id]["twillo_price"] = int(price)
        
        order_summary = f"""
📝 অর্ডার সারাংশ:

📞 Service: Twillo SID
🔢 Quantity: {quantity} টি
{discount_msg}
💰 মোট মূল্য: {int(price)} TK

💳 পেমেন্ট মাধ্যম নির্বাচন করুন:
"""
        bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
        bot.register_next_step_handler(message, process_twillo_payment)

    except:
        error_msg = """
❌ অবৈধ সংখ্যা! শুধুমাত্র সংখ্যা লিখুন:

উদাহরণ: 1, 5, 10

আবার চেষ্টা করুন:
"""
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, process_twillo_quantity)

def process_twillo_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    user_id = str(message.from_user.id)
    if user_id not in users or "twillo_price" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।")
        return twillo_sid_buy(message)
        
    user_data = users[user_id]

    if message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=payment_markup())
        bot.register_next_step_handler(msg, process_twillo_payment)
        return

    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    price = user_data["twillo_price"]
    quantity = user_data["twillo_quantity"]

    payment_instructions = f"""
💳 {method} এ টাকা পাঠান:

📱 Number: {payment_number}
💰 Amount: {price} TK
📝 Reference: Twillo{quantity}

⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন

📨 এখন আপনার Transaction ID লিখুন:
"""
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_twillo_order(m, method, price, quantity))

def confirm_twillo_order(message, method, price, quantity):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    txn_id = message.text
    user_id = str(message.from_user.id)

    order_id = f"TWILLO{int(time.time())}{user_id}"
    orders[order_id] = {
        "user_id": user_id,
        "service": "Twillo SID",
        "quantity": quantity,
        "price": price,
        "method": method,
        "txn_id": txn_id,
        "status": "pending"
    }
    save_data() # Save the new order

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_twillo_{order_id}"))

    admin_msg = f"""
📞 নতুন Twillo SID অর্ডার:

📦 Order ID: {order_id}
👤 User: @{message.from_user.username or 'N/A'}
🆔 User ID: {user_id}
🔢 Quantity: {quantity} টি
💰 Amount: {price} TK
💳 Method: {method}
📝 Txn ID: {txn_id}
⏰ Time: {time.strftime("%Y-%m-%d %H:%M:%S")}
"""
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)

    user_confirmation = f"""
✅ আপনার অর্ডার কনফার্ম হয়েছে!

📦 Order ID: {order_id}
📞 Service: Twillo SID
🔢 Quantity: {quantity} টি
💰 Paid: {price} TK

আপনার অর্ডারটি প্রসেস করা হচ্ছে। 
ডেলিভারি সময়: ১-১২ ঘন্টা

সেবা নেওয়ার জন্য ধন্যবাদ! 🙏
"""
    bot.send_message(message.chat.id, user_confirmation)
    home_menu(message.chat.id)

# --- VPN Buy Flow (Price Corrected to 40 TK) ---

@bot.message_handler(func=lambda m: m.text == "🌐 Paid VPN Buy")
def vpn_buy(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return

    vpn_options = """
🔒 VPN প্যাকেজ নির্বাচন করুন:

NordVPN 7 Days (40TK)
- উচ্চ গতি
- 60+ দেশ
- No Logs Policy

ExpressVPN 7 Days (40TK)
- সর্বোচ্চ গতি
- 90+ দেশ
- TrustedServer Technology

HMA VPN 7 Days (40TK)
- Global coverage
- Fast speeds
- Secure connection

PIA VPN 7 Days (40TK)
- Private Internet Access
- Multiple devices
- Strong encryption

Ipvanis VPN 7 Days (40TK)
- Premium service
- Reliable connection
- Global servers

💡 সবগুলো VPN Premium quality এর
"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        "NordVPN 7 Days (40TK)", 
        "ExpressVPN 7 Days (40TK)",
        "HMA VPN 7 Days (40TK)",
        "PIA VPN 7 Days (40TK)", 
        "Ipvanis VPN 7 Days (40TK)",
        "↩️ মেনুতে ফিরে যান"
    )
    msg = bot.send_message(message.chat.id, vpn_options, reply_markup=markup)
    bot.register_next_step_handler(msg, select_vpn_type)

def select_vpn_type(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)
    
    selected_vpn = message.text
    if "40TK" not in selected_vpn:
        bot.send_message(message.chat.id, "❌ অবৈধ নির্বাচন। আবার চেষ্টা করুন।")
        return vpn_buy(message)
    
    user_id = str(message.from_user.id)
    if user_id not in users: users[user_id] = {} # Safety check
    
    users[user_id]["vpn"] = selected_vpn
    
    # Proceed to payment
    order_summary = f"""
📝 অর্র্ডার সারাংশ:

🔒 Service: {selected_vpn}
💰 মূল্য: 40 TK

💳 পেমেন্ট মাধ্যম নির্বাচন করুন:
"""
    bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
    bot.register_next_step_handler(message, process_vpn_payment)

def process_vpn_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)
    
    user_id = str(message.from_user.id)
    if user_id not in users or "vpn" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।")
        return vpn_buy(message)

    if message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=payment_markup())
        bot.register_next_step_handler(msg, process_vpn_payment)
        return

    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    
    price = 40 # Fixed VPN price

    payment_instructions = f"""
💳 {method} এ টাকা পাঠান:

📱 Number: {payment_number}
💰 Amount: {price} TK
📝 Reference: VPN

⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন

📨 এখন আপনার Transaction ID লিখুন:
"""
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_vpn_order(m, method, price))

def confirm_vpn_order(message, method, price):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    txn_id = message.text
    user_id = str(message.from_user.id)
    if user_id not in users or "vpn" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।")
        return home_menu(message.chat.id)
        
    vpn = users[user_id]["vpn"]

    order_id = f"VPN{int(time.time())}{user_id}"
    orders[order_id] = {
        "user_id": user_id,
        "service": "VPN",
        "type": vpn,
        "price": price,
        "method": method,
        "txn_id": txn_id,
        "status": "pending"
    }
    save_data() # Save the new order

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_vpn_{order_id}"))

    admin_msg = f"""
🔐 নতুন VPN অর্ডার:

📦 Order ID: {order_id}
👤 User: @{message.from_user.username or 'N/A'}
🆔 User ID: {user_id}
🔒 VPN: {vpn}
💰 Amount: {price} TK
💳 Method: {method}
📝 Txn ID: {txn_id}
⏰ Time: {time.strftime("%Y-%m-%d %H:%M:%S")}
"""
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)

    user_confirmation = f"""
✅ আপনার অর্র্ডার কনফার্ম হয়েছে!

📦 Order ID: {order_id}
🔒 Service: {vpn}
💰 Paid: {price} TK

আপনার অর্র্ডারটি প্রসেস করা হচ্ছে। 
ডেলিভারি সময়: ১-৬ ঘন্টা

সেবা নেওয়ার জন্য ধন্যবাদ! 🙏
"""
    bot.send_message(message.chat.id, user_confirmation)
    home_menu(message.chat.id)


# --- YouTube Premium Flow ---

@bot.message_handler(func=lambda m: m.text == "🎥 YouTube Premium")
def yt_premium(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return
    
    yt_options = """
🎬 YouTube Premium প্যাকেজ:

1 Month (25TK)
- বিনা বিজ্ঞাপনে ভিডিও
- ব্যাকগ্রাউন্ড প্লেব্যাক
- অফলাইন ডাউনলোড

1 Year (150TK)
- 12 মাসের জন্য উপরের সব সুবিধা
- মাসিক 12.5 TK (50% সাশ্রয়ী)
- একবারে ১২ মাসের অ্যাক্সেস

💡 উভয় প্যাকেজ Premium quality এর
"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("1 Month (25TK)", "1 Year (150TK)", "↩️ মেনুতে ফিরে যান")
    msg = bot.send_message(message.chat.id, yt_options, reply_markup=markup)
    bot.register_next_step_handler(msg, select_yt_plan)

def select_yt_plan(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)
    
    selected_plan = message.text
    if "Month" in selected_plan:
        price = 25
    elif "Year" in selected_plan:
        price = 150
    else:
        bot.send_message(message.chat.id, "❌ অবৈধ নির্বাচন। আবার চেষ্টা করুন।")
        return yt_premium(message)
        
    user_id = str(message.from_user.id)
    if user_id not in users: users[user_id] = {} # Safety check
    
    users[user_id]["yt_plan"] = selected_plan
    
    order_summary = f"""
📝 অর্ডার সারাংশ:

🎬 Service: {selected_plan}
💰 মূল্য: {price} TK

💳 পেমেন্ট মাধ্যম নির্বাচন করুন:
"""
    bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
    bot.register_next_step_handler(message, process_yt_payment)

def process_yt_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    user_id = str(message.from_user.id)
    if user_id not in users or "yt_plan" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।")
        return yt_premium(message)

    if message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=payment_markup())
        bot.register_next_step_handler(msg, process_yt_payment)
        return

    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    yt_plan = users[user_id]["yt_plan"]
    price = 25 if "Month" in yt_plan else 150
    
    payment_instructions = f"""
💳 {method} এ টাকা পাঠান:

📱 Number: {payment_number}
💰 Amount: {price} TK
📝 Reference: YT

⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন

📨 এখন আপনার Transaction ID লিখুন:
"""
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_yt_order(m, method, price))

def confirm_yt_order(message, method, price):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    txn_id = message.text
    user_id = str(message.from_user.id)
    if user_id not in users or "yt_plan" not in users[user_id]: 
        bot.send_message(message.chat.id, "❌ সেশন এক্সপায়ার্ড! আবার চেষ্টা করুন।")
        return home_menu(message.chat.id)
        
    yt_plan = users[user_id]["yt_plan"]

    order_id = f"YT{int(time.time())}{user_id}"
    orders[order_id] = {
        "user_id": user_id,
        "service": "YouTube Premium",
        "type": yt_plan,
        "price": price,
        "method": method,
        "txn_id": txn_id,
        "status": "pending"
    }
    save_data() # Save the new order

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_yt_{order_id}"))

    admin_msg = f"""
📺 নতুন YouTube Premium অর্ডার:

📦 Order ID: {order_id}
👤 User: @{message.from_user.username or 'N/A'}
🆔 User ID: {user_id}
🎬 Plan: {yt_plan}
💰 Amount: {price} TK
💳 Method: {method}
📝 Txn ID: {txn_id}
⏰ Time: {time.strftime("%Y-%m-%d %H:%M:%S")}
"""
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)

    user_confirmation = f"""
✅ আপনার অর্ডার কনফার্ম হয়েছে!

📦 Order ID: {order_id}
🎬 Service: {yt_plan}
💰 Paid: {price} TK

আপনার অর্ডারটি প্রসেস করা হচ্ছে। 
ডেলিভারি সময়: ১-৬ ঘন্টা

সেবা নেওয়ার জন্য ধন্যবাদ! 🙏
"""
    bot.send_message(message.chat.id, user_confirmation)
    home_menu(message.chat.id)

# --- Balance, Withdraw, Refer, Support ---

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
    else:
        error_msg = """
❌ একাউন্ট খুঁজে পাওয়া যায়নি!

/start লিখে আবার রেজিস্টার করুন
"""
        bot.send_message(message.chat.id, error_msg)

@bot.message_handler(func=lambda m: m.text == "💵 Withdraw")
def withdraw(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return
    
    if user_id in users:
        balance = users[user_id]["balance"]

        if balance < 60:
            error_msg = f"""
❌ সর্বনিম্ন উত্তোলন 60 টাকা

💰 আপনার ব্যালেন্স: {balance} TK
🎯 প্রয়োজন: {60 - balance} TK more

💡 টাকা উপার্জনের উপায়:
1. Gmail বিক্রি করুন (৬ TK/Gmail)
2. বন্ধুদের রেফার করুন (২ TK/Referral)
"""
            bot.send_message(message.chat.id, error_msg)
            return

        withdraw_msg = f"""
💵 উত্তোলনের পরিমাণ লিখুন:

💰 Available: {balance} TK
🎯 Minimum: 60 TK
💸 Maximum: {balance} TK

উদাহরণ: 60, 100, 200
"""
        msg = bot.send_message(message.chat.id, withdraw_msg, reply_markup=back_markup())    
        bot.register_next_step_handler(msg, process_withdraw_amount)

def process_withdraw_amount(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    try:
        amount = int(message.text)
        user_id = str(message.from_user.id)
        balance = users[user_id]["balance"]

        if amount < 60:    
            error_msg = """
❌ সর্বনিম্ন 60 টাকা উত্তোলন করতে পারবেন!

আবার চেষ্টা করুন:
"""
            msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())    
            bot.register_next_step_handler(msg, process_withdraw_amount)    
            return    
            
        if amount > balance:    
            error_msg = f"""
❌ আপনার একাউন্টে পর্যাপ্ত টাকা নেই!

💰 আপনার ব্যালেন্স: {balance} TK
💸 চাহিদাকৃত: {amount} TK
📉 ঘাটতি: {amount - balance} TK

কম পরিমাণ লিখুন:
"""
            msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())    
            bot.register_next_step_handler(msg, process_withdraw_amount)    
            return    
            
        # Move fund from balance to hold temporarily
        users[user_id]["balance"] -= amount    
        users[user_id]["hold"] += amount
        save_data()
        
        method_msg = """
📲 উত্তোলনের মাধ্যম নির্বাচন করুন:

📱 Bkash - দ্রুত প্রক্রিয়াকরণ
📱 Nagad - দ্রুত প্রক্রিয়াকরণ

বিঃদ্রঃ: একই নম্বরে টাকা পাঠানো হবে যেখান থেকে পেমেন্ট করেছেন
"""
        msg = bot.send_message(message.chat.id, method_msg, reply_markup=payment_markup())    
        bot.register_next_step_handler(msg, lambda m: process_withdraw_method(m, amount))

    except:
        error_msg = """
❌ অবৈধ পরিমাণ! শুধুমাত্র সংখ্যা লিখুন:

উদাহরণ: 60, 100, 200

আবার চেষ্টা করুন:
"""
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, process_withdraw_amount)

def process_withdraw_method(message, amount):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        # Revert funds if cancelled
        users[str(message.from_user.id)]["balance"] += amount
        users[str(message.from_user.id)]["hold"] -= amount
        save_data()
        return home_menu(message.chat.id)

    if message.text not in ["📲 Bkash", "📲 Nagad"]:
        error_msg = "❌ দয়া করে পেমেন্ট মাধ্যম নির্বাচন করুন:"
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=payment_markup())
        bot.register_next_step_handler(msg, lambda m: process_withdraw_method(m, amount))
        return

    method = "Bkash" if "Bkash" in message.text else "Nagad"
    
    number_msg = f"""
📱 আপনার {method} নম্বর লিখুন:

⚠️ নিশ্চিত করুন যে নম্বরটি সঠিক
💡 একই নম্বর ব্যবহার করুন যেখান থেকে পেমেন্ট করেছেন

নম্বরটি এই ফরম্যাটে লিখুন:
01XXXXXXXXX
"""
    msg = bot.send_message(message.chat.id, number_msg, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: complete_withdraw(m, amount, method))

def complete_withdraw(message, amount, method):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        # Revert funds if cancelled
        users[str(message.from_user.id)]["balance"] += amount
        users[str(message.from_user.id)]["hold"] -= amount
        save_data()
        return home_menu(message.chat.id)

    number = message.text
    user_id = str(message.from_user.id)

    # Simple validation for number format
    if not number.isdigit() or len(number) != 11 or not number.startswith('01'):
        error_msg = "❌ অবৈধ ফোন নম্বর! ১১ ডিজিটের সঠিক নম্বর লিখুন (যেমন: 01XXXXXXXXX):"
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, lambda m: complete_withdraw(m, amount, method))
        return

    markup = types.InlineKeyboardMarkup()
    # Using a unique ID for withdrawal for better tracking
    withdraw_id = f"WD{int(time.time())}{user_id}"
    orders[withdraw_id] = {
        "user_id": user_id,
        "service": "Withdrawal",
        "amount": amount,
        "method": method,
        "number": number,
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
📱 Method: {method}
📞 Number: {number}
⏰ Time: {time.strftime("%Y-%m-%d %H:%M:%S")}

💡 User Balance (After Hold): {users[user_id]['balance']} TK
"""
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)

    user_confirmation = f"""
✅ আপনার উত্তোলনের অনুরোধ পাঠানো হয়েছে!

📋 Withdrawal ID: {withdraw_id}
💰 Amount: {amount} TK
📱 Method: {method}
📞 Number: {number}

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
{ref_link}

🎉 প্রতিটি রেফারেলের জন্য পাবেন ২ টাকা
💰 মোট উপার্জন: {ref_earnings} TK
👥 আপনার রেফার্ড ইউজার: {ref_count} জন

📊 রেফার স্ট্যাটাস:
- সফল রেজিস্ট্রেশন: {ref_count} জন

💡 রেফার লিংক শেয়ার করার টিপস:
1. Facebook গ্রুপে শেয়ার করুন
2. WhatsApp/Telegram গ্রুপে শেয়ার করুন
3. বন্ধুদের সাথে শেয়ার করুন

বন্ধুদের সাথে শেয়ার করুন এবং টাকা উপার্জন করুন! 🎊
"""
        bot.send_message(message.chat.id, refer_msg)
    else:
        error_msg = """
❌ একাউন্ট খুঁজে পাওয়া যায়নি!

/start লিখে আবার রেজিস্টার করুন
"""
        bot.send_message(message.chat.id, error_msg)

@bot.message_handler(func=lambda m: m.text == "🆘 Support")
def support(message):
    user_id = str(message.from_user.id)
    if user_id in users and users[user_id].get("is_blocked"): return
    
    support_msg = f"""
🆘 সাপোর্ট সেন্টার:

যেকোনো সমস্যা বা প্রশ্নের জন্য নিচের তথ্য ব্যবহার করে যোগাযোগ করুন:

📞 জরুরী যোগাযোগ:
- Admin: @Raimadmin
- Phone: 01774049543 (WhatsApp/IMO)

⏰ সাপোর্ট সময়:
- সকাল ১০টা - রাত ১০টা
- ৭ দিন সাপোর্ট

📋 সাধারণ সমস্যার সমাধান:
1. অর্ডার না পেলে - Admin কে মেসেজ করুন
2. টাকা পাঠিয়েছেন কিন্তু ব্যালেন্স আপডেট হয়নি - Txn ID সহ মেসেজ করুন
3. Gmail রিজেক্ট হলে - সঠিক ফরম্যাটে আবার পাঠান

💡 দ্রুত সাপোর্ট পেতে:
- আপনার User ID: {message.from_user.id}
- অর্ডার/ট্রানজেকশন ID দিয়ে মেসেজ করুন

আমরা আপনাকে সাহায্য করতে পেরে আনন্দিত! 🙏
"""
    bot.send_message(message.chat.id, support_msg)

# --- Admin Panel ---

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ আপনার অনুমতি নেই!")
        return

    total_users = len(users)
    total_balance = sum(user.get("balance", 0) for user in users.values())
    total_hold = sum(user.get("hold", 0) for user in users.values())
    total_pending_gmails = sum(len(sub["gmails"]) for subs in pending_gmails.values() for sub in subs.values() if subs)

    admin_msg = f"""
👑 অ্যাডমিন প্যানেল:

📊 স্ট্যাটিস্টিক্স:
👥 মোট ইউজার: {total_users}
💰 মোট ব্যালেন্স: {total_balance} TK
⏳ মোট Hold: {total_hold} TK
📧 Pending Gmails: {total_pending_gmails} টি

🛠️ অ্যাডমিন কমান্ড:
/stats - বিস্তারিত স্ট্যাটিস্টিক্স
/users - ইউজার তালিকা
/broadcast - ব্রডকাস্ট মেসেজ
/notify - নির্দিষ্ট ইউজারকে মেসেজ
/balance - ইউজারের ব্যালেন্স পরিবর্তন
/block - ইউজারকে ব্লক/আনব্লক
"""
    bot.send_message(message.chat.id, admin_msg)

# --- NEW ADMIN COMMAND: /balance ---

@bot.message_handler(commands=['balance'])
def admin_manage_balance(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ আপনার অনুমতি নেই!")
        return

    msg = bot.send_message(message.chat.id, "👤 ব্যালেন্স পরিবর্তন করতে চান? ইউজার ID লিখুন:", reply_markup=back_markup())
    bot.register_next_step_handler(msg, get_balance_user_id)

def get_balance_user_id(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)
    
    user_id_to_manage = str(message.text).strip()
    if user_id_to_manage not in users:
        msg = bot.send_message(message.chat.id, "❌ এই ইউজার ID খুঁজে পাওয়া যায়নি! আবার চেষ্টা করুন:", reply_markup=back_markup())
        bot.register_next_step_handler(msg, get_balance_user_id)
        return

    user_data = users[user_id_to_manage]
    
    # Calculate Referral Earnings
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
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add("💵 Main Balance", "⏳ Hold Balance", "👥 Referral Count")
    markup.add("↩️ মেনুতে ফিরে যান")

    # Store the user ID being managed in admin_sessions
    admin_sessions[message.chat.id] = {"manage_user_id": user_id_to_manage}

    msg = bot.send_message(message.chat.id, balance_info, reply_markup=markup)
    bot.register_next_step_handler(msg, select_balance_type)

def select_balance_type(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)
    
    balance_type = message.text
    valid_types = ["💵 Main Balance", "⏳ Hold Balance", "👥 Referral Count"]
    
    if balance_type not in valid_types:
        msg = bot.send_message(message.chat.id, "❌ অবৈধ নির্বাচন। আবার চেষ্টা করুন:", reply_markup=back_markup())
        bot.register_next_step_handler(msg, select_balance_type)
        return

    # Store balance type
    admin_sessions[message.chat.id]["balance_type"] = balance_type

    prompt = f"""
💡 {balance_type} পরিবর্তন করার জন্য পরিমাণ লিখুন:

পদ্ধতি:
- যোগ করতে: +10
- বিয়োগ করতে: -5
- সরাসরি নতুন মান সেট করতে: 100 (শুধু সংখ্যা)

উদাহরণ: +10 অথবা 50 (যদি আপনি চান নতুন মান 50 হোক)
"""
    msg = bot.send_message(message.chat.id, prompt, reply_markup=back_markup())
    bot.register_next_step_handler(msg, apply_balance_change)

def apply_balance_change(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        # Clear temp data
        if message.chat.id in admin_sessions: del admin_sessions[message.chat.id]
        return home_menu(message.chat.id)
    
    chat_id = message.chat.id
    if chat_id not in admin_sessions or "manage_user_id" not in admin_sessions[chat_id]:
        bot.send_message(chat_id, "❌ সেশন এক্সপায়ার্ড! আবার /balance কমান্ডটি ব্যবহার করুন।")
        return home_menu(chat_id)

    user_id_to_manage = admin_sessions[chat_id]["manage_user_id"]
    balance_type = admin_sessions[chat_id]["balance_type"]
    change_input = message.text.strip()
    
    try:
        current_value = 0
        balance_key = ""
        
        if balance_type == "💵 Main Balance":
            balance_key = "balance"
        elif balance_type == "⏳ Hold Balance":
            balance_key = "hold"
        elif balance_type == "👥 Referral Count":
            balance_key = "referral_count"

        current_value = users[user_id_to_manage].get(balance_key, 0)
        new_value = current_value
        
        if change_input.startswith('+') or change_input.startswith('-'):
            # Relative change
            change_amount = int(change_input)
            new_value = current_value + change_amount
            change_type = "পরিবর্তন"
        else:
            # Absolute set
            new_value = int(change_input)
            change_type = "সেট"
        
        if new_value < 0:
            new_value = 0 # Prevent negative values

        # Apply the change
        users[user_id_to_manage][balance_key] = new_value
        save_data()
        
        # Notify the user
        if balance_key in ["balance", "hold"]:
             bot.send_message(user_id_to_manage, f"🎉 Admin আপনার একাউন্টের {balance_type} {change_type} করেছেন।\n\n💰 নতুন ব্যালেন্স: {new_value} TK")
        elif balance_key == "referral_count":
             bot.send_message(user_id_to_manage, f"🎉 Admin আপনার একাউন্টের Referral Count {change_type} করেছেন।\n\n👥 নতুন Referral Count: {new_value} জন")


        admin_confirmation = f"""
✅ সফলভাবে পরিবর্তন করা হয়েছে!

👤 ইউজার: @{users[user_id_to_manage].get('username', 'N/A')}
🔄 টাইপ: {balance_type}
Old Value: {current_value}
New Value: {new_value}
"""
        bot.send_message(chat_id, admin_confirmation)
        
    except ValueError:
        msg = bot.send_message(chat_id, "❌ অবৈধ পরিমাণ! শুধুমাত্র সংখ্যা, +সংখ্যা অথবা -সংখ্যা লিখুন। আবার চেষ্টা করুন:", reply_markup=back_markup())
        bot.register_next_step_handler(msg, apply_balance_change)
        return
    except Exception as e:
        bot.send_message(chat_id, f"❌ একটি অজানা ত্রুটি হয়েছে: {e}")

    # Clear temp data and go home
    if chat_id in admin_sessions:
        del admin_sessions[chat_id]
    home_menu(chat_id)

# --- NEW ADMIN COMMAND: /block ---

@bot.message_handler(commands=['block'])
def admin_block_user(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ আপনার অনুমতি নেই!")
        return

    msg = bot.send_message(message.chat.id, "🚫 ব্লক করতে চান? ইউজার ID লিখুন:", reply_markup=back_markup())
    bot.register_next_step_handler(msg, get_block_user_id)

def get_block_user_id(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)
    
    user_id_to_block = str(message.text).strip()
    
    if user_id_to_block not in users:
        msg = bot.send_message(message.chat.id, "❌ এই ইউজার ID খুঁজে পাওয়া যায়নি! আবার চেষ্টা করুন:", reply_markup=back_markup())
        bot.register_next_step_handler(msg, get_block_user_id)
        return
        
    user_data = users[user_id_to_block]
    
    current_status = "ব্লকড" if user_data.get("is_blocked") else "আনব্লকড"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚫 ব্লক করুন", "✅ আনব্লক করুন")
    markup.add("↩️ মেনুতে ফিরে যান")
    
    prompt = f"""
✅ ইউজার পাওয়া গেছে: @{user_data.get('username', 'N/A')}
🆔 ID: {user_id_to_block}
💡 বর্তমান স্ট্যাটাস: {current_status}

আপনি কি করতে চান?
"""
    
    # Store the user ID being managed
    admin_sessions[message.chat.id] = {"block_user_id": user_id_to_block}

    msg = bot.send_message(message.chat.id, prompt, reply_markup=markup)
    bot.register_next_step_handler(msg, block_user_action)

def block_user_action(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        # Clear temp data
        if message.chat.id in admin_sessions: del admin_sessions[message.chat.id]
        return home_menu(message.chat.id)
        
    chat_id = message.chat.id
    if chat_id not in admin_sessions or "block_user_id" not in admin_sessions[chat_id]:
        bot.send_message(chat_id, "❌ সেশন এক্সপায়ার্ড! আবার /block কমান্ডটি ব্যবহার করুন।")
        return home_menu(chat_id)
        
    user_id_to_block = admin_sessions[chat_id]["block_user_id"]
    action = message.text
    
    if action == "🚫 ব্লক করুন":
        users[user_id_to_block]["is_blocked"] = True
        save_data()
        bot.send_message(user_id_to_block, "❌ দুঃখিত! Admin কর্তৃক আপনাকে এই বট ব্যবহার থেকে ব্লক করা হয়েছে। Admin এর সাথে যোগাযোগ করুন।")
        admin_msg = f"✅ ইউজার @{users[user_id_to_block].get('username', 'N/A')} ({user_id_to_block}) কে সফলভাবে ব্লক করা হয়েছে।"
    elif action == "✅ আনব্লক করুন":
        users[user_id_to_block]["is_blocked"] = False
        save_data()
        bot.send_message(user_id_to_block, "✅ Admin কর্তৃক আপনাকে আনব্লক করা হয়েছে! আপনি এখন বট ব্যবহার করতে পারবেন।")
        admin_msg = f"✅ ইউজার @{users[user_id_to_block].get('username', 'N/A')} ({user_id_to_block}) কে সফলভাবে আনব্লক করা হয়েছে।"
    else:
        msg = bot.send_message(chat_id, "❌ অবৈধ নির্বাচন। আবার চেষ্টা করুন:", reply_markup=back_markup())
        bot.register_next_step_handler(msg, block_user_action)
        return

    bot.send_message(chat_id, admin_msg)
    
    if chat_id in admin_sessions:
        del admin_sessions[chat_id]
    home_menu(chat_id)
    
# --- Other Admin Commands (stats, users, etc.) are kept here ---

@bot.message_handler(commands=['stats'])
def stats(message):
    if str(message.from_user.id) != ADMIN_ID:
        return

    total_earnings = sum(user.get("balance", 0) + user.get("hold", 0) for user in users.values())
    total_ref_earnings = sum(user.get("referral_count", 0) * 2 for user in users.values())
    total_gmail_earnings = total_earnings - total_ref_earnings

    stats_msg = f"""
📈 বিস্তারিত স্ট্যাটিস্টিক্স:

💰 মোট আয়: {total_earnings} TK
📧 Gmail, Buy/Sell, Other: {total_gmail_earnings} TK
👥 রেফার থেকে: {total_ref_earnings} TK

📊 ইউজার এক্টিভিটি:
- গড় ব্যালেন্স: {total_earnings/len(users) if len(users) > 0 else 0:.2f} TK/User
- গড় রেফার: {sum(user.get('referral_count', 0) for user in users.values())/len(users) if len(users) > 0 else 0:.2f}/User
"""
    bot.send_message(message.chat.id, stats_msg)

@bot.message_handler(commands=['users'])
def list_users(message):
    if str(message.from_user.id) != ADMIN_ID:
        return

    users_list = "\n".join([f"👤 @{u.get('username', 'N/A')} | ID: {uid} | Bal: {u.get('balance', 0)} TK" for uid, u in list(users.items())[:10]])
    users_msg = f"""
👥 সর্বশেষ ১০ ইউজার:

{users_list}

💡 আরও দেখতে: /users_all
"""
    bot.send_message(message.chat.id, users_msg)

@bot.message_handler(commands=['users_all'])
def all_users(message):
    if str(message.from_user.id) != ADMIN_ID:
        return

    with open("users.txt", "w", encoding="utf-8") as f:
        for uid, u in users.items():
            f.write(f"ID: {uid} | User: @{u.get('username', 'N/A')} | Bal: {u.get('balance', 0)} TK | Ref: {u.get('referral_count', 0)} | Joined: {u.get('joined_date', 'N/A')}\n")
    
    with open("users.txt", "rb") as f:
        bot.send_document(message.chat.id, f, caption="📊 সকল ইউজারের তালিকা")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ আপনার অনুমতি নেই!")
        return

    msg = bot.send_message(message.chat.id, "📢 ব্রডকাস্ট মেসেজ পাঠাতে চান? একটি ছবিসহ ক্যাপশন লিখে পাঠান। শুধু টেক্সট পাঠাতে চাইলে সরাসরি মেসেজ লিখুন।", reply_markup=back_markup())
    bot.register_next_step_handler(msg, send_broadcast)

def send_broadcast(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    success = 0
    failed = 0
    
    if message.photo:
        photo_id = message.photo[-1].file_id
        caption = message.caption or ""
        
        for user_id in users:
            try:
                if not users[user_id].get("is_blocked"): # Do not broadcast to blocked users
                    bot.send_photo(user_id, photo_id, caption=caption)
                    success += 1
                    time.sleep(0.1)
            except:
                failed += 1
    elif message.text:
        broadcast_msg = message.text
        for user_id in users:
            try:
                if not users[user_id].get("is_blocked"): # Do not broadcast to blocked users
                    bot.send_message(user_id, f"📢 ব্রডকাস্ট:\n\n{broadcast_msg}")
                    success += 1
                    time.sleep(0.1)
            except:
                failed += 1

    bot.send_message(message.chat.id, f"""
✅ ব্রডকাস্ট সম্পন্ন!

📊 রেজাল্ট:
✅ সফল: {success}
❌ ব্যর্থ: {failed}
📊 মোট: {success + failed}
""")
    bot.clear_step_handler(message)
    home_menu(message.chat.id)

@bot.message_handler(commands=['notify'])
def notify_user(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ আপনার অনুমতি নেই!")
        return

    msg = bot.send_message(message.chat.id, "👤 ইউজার ID লিখুন যাকে মেসেজ পাঠাতে চান:", reply_markup=back_markup())
    bot.register_next_step_handler(msg, get_notify_message)

def get_notify_message(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)
    
    user_id = str(message.text)
    if user_id not in users:
        bot.send_message(message.chat.id, "❌ এই ইউজার ID খুঁজে পাওয়া যায়নি!")
        bot.clear_step_handler(message)
        return
        
    msg = bot.send_message(message.chat.id, "💬 মেসেজ পাঠাতে চান? একটি ছবিসহ ক্যাপশন লিখে পাঠান। শুধু টেক্সট পাঠাতে চাইলে সরাসরি মেসেজ লিখুন।", reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: send_notification(m, user_id))

def send_notification(message, user_id):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    try:
        if message.photo:
            photo_id = message.photo[-1].file_id
            caption = message.caption or ""
            bot.send_photo(user_id, photo_id, caption=f"📨 Admin থেকে মেসেজ:\n\n{caption}")
        elif message.text:
            bot.send_message(user_id, f"📨 Admin থেকে মেসেজ:\n\n{message.text}")
        
        bot.send_message(message.chat.id, "✅ মেসেজ পাঠানো হয়েছে!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ ইউজারকে মেসেজ পাঠানো যায়নি! Error: {e}")
    
    bot.clear_step_handler(message)
    home_menu(message.chat.id)

# --- Callback Query Handler (Centralized) ---

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    # Only Admin can use inline buttons for actions
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ আপনার অনুমতি নেই এই কাজটি করতে!")
        return

    data = call.data.split('_')
    action = data[0]
    
    # 1. Gmail Approval/Rejection (Batch System)
    if action in ["approve", "reject"] and data[1] == "gmail":
        user_id = str(data[2])
        submission_id = str(data[3])
        gmail_index = int(data[4])
        
        if (user_id not in pending_gmails or 
            submission_id not in pending_gmails[user_id] or 
            gmail_index >= len(pending_gmails[user_id][submission_id]["gmails"])):
            bot.answer_callback_query(call.id, "❌ Gmail not found!")
            return
        
        submission = pending_gmails[user_id][submission_id]
        gmail_data = submission["gmails"][gmail_index]
        
        if gmail_data["status"] != "pending":
            bot.answer_callback_query(call.id, f"❌ Already {gmail_data['status']}!")    
            return
        
        gmail = gmail_data["email"]
        
        # Update user funds and status
        if action == "approve":
            users[user_id]["hold"] -= 6
            users[user_id]["balance"] += 6
            pending_gmails[user_id][submission_id]["gmails"][gmail_index]["status"] = "approved"
            
            user_msg = f"""
✅ আপনার Gmail অনুমোদিত হয়েছে!
📧 Gmail: {gmail.split(':')[0]}
💰 প্রাপ্ত Amount: ৬ টাকা
আপনার নতুন ব্যালেন্স: {users[user_id]['balance']} TK
"""
            bot.answer_callback_query(call.id, "✅ Gmail Approved")
            new_text = f"✅ APPROVED: {gmail}"
        
        elif action == "reject":
            users[user_id]["hold"] -= 6
            pending_gmails[user_id][submission_id]["gmails"][gmail_index]["status"] = "rejected"
            
            user_msg = "❌ আপনার Gmail রিজেক্ট হয়েছে! কারণ: অচল Gmail / 2FA / ভুল ফরম্যাট।"
            bot.answer_callback_query(call.id, "❌ Gmail Rejected")
            new_text = f"❌ REJECTED: {gmail}"
            
        bot.send_message(user_id, user_msg)
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=new_text,
            reply_markup=None
        )
        
        save_data()
        check_complete_submission(user_id, submission_id)

    # 2. Withdrawal Payment
    elif action == "pay":
        user_id = str(data[1])
        amount = int(data[2])
        withdraw_id = str(data[3])
        
        if withdraw_id in orders and orders[withdraw_id]["status"] == "pending":
            users[user_id]["hold"] -= amount
            orders[withdraw_id]["status"] = "completed"
            
            user_msg = f"""
✅ আপনার উত্তোলনের অনুরোধ অনুমোদিত হয়েছে!

💰 Amount: {amount} TK
📊 নতুন ব্যালেন্স: {users[user_id]['balance']} TK

টাকা ১-২ ঘন্টার মধ্যে আপনার অ্যাকাউন্টে যোগ হবে।
"""
            bot.send_message(user_id, user_msg)
            
            bot.answer_callback_query(call.id, "✅ Payment confirmed. Hold released.")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=call.message.text + "\n\n✅ PAYMENT SENT AND HOLD RELEASED",
                reply_markup=None
            )
            save_data()
        else:
            bot.answer_callback_query(call.id, "❌ Withdrawal not found or already paid.")
            
    # 3. Order Delivery Confirmation (for Buy Services)
    elif action == "deliver":
        service_type = data[1]
        order_id = data[2]
        
        if order_id not in orders:
            bot.answer_callback_query(call.id, "❌ Order not found!")
            return

        order = orders[order_id]
        user_id = order["user_id"]
        
        # Admin is prompted for delivery
        instructions = f"📩 User @{users[user_id].get('username', 'N/A')} ({user_id}) কে অর্ডার ID: {order_id} এর জন্য {order.get('quantity', 1)}টি {order.get('type', service_type)} সরবরাহ করুন।\n\nডেলিভারির পর ম্যানুয়ালি ইউজারকে মেসেজ করুন: /delivered_{order_id}"
        
        bot.send_message(ADMIN_ID, instructions)
        bot.answer_callback_query(call.id, "✅ Delivery instructions sent")
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=call.message.text + "\n\n⏳ DELIVERY IN PROGRESS...",
            reply_markup=None
        )

# --- Catch-all Handler ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    bot.clear_step_handler(message)
    
    user_id = str(message.from_user.id)
    # Blocked check
    if user_id in users and users[user_id].get("is_blocked"):
        # Allow admin commands for admin only if they are blocked (unlikely but safe)
        if str(message.from_user.id) == ADMIN_ID and message.text.startswith('/'):
            pass
        else:
            bot.send_message(message.chat.id, "❌ আপনাকে এই বট ব্যবহার থেকে ব্লক করা হয়েছে। Admin এর সাথে যোগাযোগ করুন।")
            return
            
    if message.text and not message.text.startswith('/'):
        unknown_msg = """
❌ অজানা কমান্ড!

আপনার মেসেজটি বুঝা যায়নি। অনুগ্রহ করে নিচের মেনু থেকে একটি অপশন নির্বাচন করুন।
"""
        bot.send_message(message.chat.id, unknown_msg)
    
    if message.text and not message.text.startswith('/admin') and str(message.from_user.id) != ADMIN_ID:
        home_menu(message.chat.id)

if __name__ == "__main__":
    print("🤖 Bot is running...")
    bot.infinity_polling()

