import telebot
from telebot import types
import time
import json
import os

TOKEN = '8204693585:AAHo3H_NsANMskc9ubQICp2MKP6H-K0dcdg'
ADMIN_ID = '7943354448'
ADMIN_BKASH_NO = '01774049543'
ADMIN_NAGAD_NO = '01774049543'
BOT_USERNAME = "sohojbuysellbdbot"

bot = telebot.TeleBot(TOKEN)
users = {}
pending_gmails = {}
orders = {}

# --- Data Persistence Functions ---
def save_users():
    """Saves the users data to a JSON file."""
    try:
        with open('users.json', 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=4)
        print("Users data saved successfully.")
    except Exception as e:
        print(f"Error saving users data: {e}")

def load_users():
    """Loads users data from a JSON file."""
    global users
    if os.path.exists('users.json'):
        try:
            with open('users.json', 'r', encoding='utf-8') as f:
                users = json.load(f)
            print("Users data loaded successfully.")
        except json.JSONDecodeError:
            print("Corrupted users.json file. Starting with empty data.")
            users = {}
    else:
        print("users.json not found. Creating a new one.")
        users = {}
# --- End of Data Persistence Functions ---

# --- Bot Initialization ---
load_users()
# --- End of Bot Initialization ---

LOGO = """
╔═════════════════════════╗
║    🛒 Sohoj Buy Sell BD    ║
╚═════════════════════════╝

🌟 আপনার ডিজিটাল সার্ভিসের বিশ্বস্ত পার্টনার 🌟
"""

def home_menu(chat_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        "📤 Gmail Sell", "📥 Gmail Buy",
        "💳 Balance", "💵 Withdraw",
        "🌐 Paid VPN Buy", "🎥 YouTube Premium",
        "👥 Refer", "🆘 Support",
        "🎁 Play Point Park On"
    ]
    markup.add(*buttons)
    
    user_info = ""
    if str(chat_id) in users:
        user = users[str(chat_id)]
        user_info = f"\n👤 User: @{user['username'] or 'NoUsername'}\n💰 Balance: {user['balance']} TK"
    
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
    bot.send_message(message.chat.id, LOGO)
    time.sleep(0.5)

    user_id = str(message.from_user.id)
    
    is_new_user = user_id not in users

    if is_new_user:
        users[user_id] = {
            "username": message.from_user.username,
            "balance": 0,
            "hold": 0,
            "referral_count": 0,
            "referred_users": [],
            "joined_date": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        save_users()

    if len(message.text.split()) > 1:
        referrer_id_str = message.text.split()[1]
        try:
            if referrer_id_str in users and referrer_id_str != user_id:
                if user_id not in users[referrer_id_str]["referred_users"]:
                    users[referrer_id_str]["balance"] += 2
                    users[referrer_id_str]["referral_count"] += 1
                    users[referrer_id_str]["referred_users"].append(user_id)
                    bot.send_message(referrer_id_str, f"🎉 আপনি ২ টাকা পেয়েছেন রেফার বোনাস হিসেবে! নতুন ইউজার: @{message.from_user.username or 'NoUsername'}")
                    save_users()
        except ValueError:
            pass

    welcome_msg = f"""
✨ স্বাগতম {message.from_user.first_name}!

ডিজিটাল Sohoj Buy Sell BD বটে আপনাকে স্বাগতম! 🎉

🔹 Gmail বিক্রি/ক্রয়
🔹 Premium VPN সার্ভিস
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

# Play Point Park On section
@bot.message_handler(func=lambda m: m.text == "🎁 Play Point Park On")
def play_point_menu(message):
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
    if country not in ["🇺🇸 USA", "🇹🇼 Taiwan", "🇬🇧 UK", "🇰🇷 South Korean"]:
        error_msg = "❌ অনুগ্রহ করে একটি বৈধ দেশ নির্বাচন করুন।"
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, process_play_point_country)
        return

    users[str(message.from_user.id)]["play_point_country"] = country
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
        users[user_id]["play_point_quantity"] = quantity
        total_price = quantity * 20
        users[user_id]["play_point_price"] = total_price
        
        details_msg = f"""
💰 মোট মূল্য: {total_price} টাকা

এখন আপনি যে Gmail/Password-গুলোতে Park On করতে চান সেগুলো একসাথে লিখুন:
(প্রতি লাইনে একটি Gmail/Password)

ফরম্যাট:
example1@gmail.com:password1
example2@gmail.com:password2
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
    user_data = users[user_id]
    
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

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_pp_{user_id}"))

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

# Gmail Sell Section
@bot.message_handler(func=lambda m: m.text == "📤 Gmail Sell")
def gmail_sell(message):
    instructions = """
📧 Gmail বিক্রি করার নিয়ম:

1. ফরম্যাট: example@gmail.com:password
2. Gmail সম্পূর্ণ অ্যাক্সেস সহ হতে হবে
3. কোনো 2FA/2-Step Verification থাকা যাবে না
4. প্রতিটি Gmail এর জন্য পাবেন ৭ টাকা

⚠️ ভুল ফরম্যাট বা Fake Gmail দিলে টাকা দেওয়া হবে না

এখন আপনার Gmail আইডি ও পাসওয়ার্ড দিন:
"""
    msg = bot.send_message(message.chat.id, instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, process_gmail)

def process_gmail(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    if ":" not in message.text or "@" not in message.text:
        error_msg = """
❌ ভুল ফরম্যাট! সঠিক ফরম্যাটে দিন:

example@gmail.com:password

আবার চেষ্টা করুন:
"""
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, process_gmail)
        return

    user_id = str(message.from_user.id)
    pending_gmails[user_id] = message.text
    users[user_id]["hold"] += 7
    save_users()

    success_msg = """
✅ Gmail জমা দেওয়া হয়েছে!

আপনার Gmail Admin এর রিভিউ এর জন্য পাঠানো হয়েছে। 
সঠিক হলে ৭ টাকা আপনার একাউন্টে যোগ করা হবে।

⏳ সর্বোচ্চ ২৪ ঘন্টার মধ্যে রিভিউ করা হবে।
"""
    bot.send_message(message.chat.id, success_msg)

    username = message.from_user.username or "NoUsername"
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
    )
    
    admin_msg = f"""
📧 নতুন Gmail Submission:

👤 User: @{username}
🆔 ID: {user_id}
📅 Time: {time.strftime("%Y-%m-%d %H:%M:%S")}

📩 Gmail Details:
{message.text}
"""
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if str(call.from_user.id) != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ আপনার অনুমতি নেই এই কাজটি করতে!")
        return

    data = call.data.split('_')
    action = data[0]
    user_id = str(data[1])

    if action == "approve":
        if user_id in pending_gmails:
            gmail = pending_gmails[user_id]
            users[user_id]["hold"] -= 7
            users[user_id]["balance"] += 7
            
            user_msg = f"""
✅ আপনার Gmail অনুমোদিত হয়েছে!

📧 Gmail: {gmail.split(':')[0]}
💰 প্রাপ্ত Amount: ৭ টাকা

আপনার নতুন ব্যালেন্স: {users[user_id]['balance']} TK
"""
            bot.send_message(user_id, user_msg)
            
            bot.answer_callback_query(call.id, "✅ Gmail Approved")
            bot.send_message(ADMIN_ID, f"✅ Gmail approved for user {user_id}")
            
            del pending_gmails[user_id]
            save_users()

    elif action == "reject":
        if user_id in pending_gmails:
            users[user_id]["hold"] -= 7
            
            user_msg = """
❌ আপনার Gmail রিজেক্ট হয়েছে!

কারণ: 
- ভুল ফরম্যাট
- Fake বা অচল Gmail
- 2FA enabled

আরও তথ্যের জন্য সাপোর্টে যোগাযোগ করুন।
"""
            bot.send_message(user_id, user_msg)
            
            bot.answer_callback_query(call.id, "❌ Gmail Rejected")
            bot.send_message(ADMIN_ID, f"❌ Gmail rejected for user {user_id}")
            
            del pending_gmails[user_id]
            save_users()

    elif action == "pay":
        amount = int(data[2])
        users[user_id]["hold"] -= amount
        
        user_msg = f"""
✅ আপনার উত্তোলনের অনুরোধ অনুমোদিত হয়েছে!

💰 Amount: {amount} TK
📊 নতুন ব্যালেন্স: {users[user_id]['balance']} TK

টাকা ১-২ ঘন্টার মধ্যে আপনার অ্যাকাউন্টে যোগ হবে।
"""
        bot.send_message(user_id, user_msg)
        
        bot.answer_callback_query(call.id, "✅ Payment sent")
        bot.send_message(ADMIN_ID, f"✅ Payment of {amount} TK sent to user {user_id}")
        save_users()

    elif action == "deliver":
        service = data[1]
        user_id = str(data[2])
        
        if service == "gmail":
            quantity = users[user_id].get("gmail_quantity", 1)
            gmail_type = users[user_id].get("gmail_type", "Gmail")
            instructions = f"📩 User {user_id} কে {quantity}টি {gmail_type} পাঠান:\n\n/delivery_{user_id}"
        elif service == "vpn":
            vpn = users[user_id].get("vpn", "VPN")
            instructions = f"📩 User {user_id} কে {vpn} পাঠান:\n\n/delivery_{user_id}"
        elif service == "yt":
            yt_plan = users[user_id].get("yt_plan", "YouTube Premium")
            instructions = f"📩 User {user_id} কে {yt_plan} পাঠান:\n\n/delivery_{user_id}"
        elif service == "pp":
            instructions = f"📩 User {user_id} কে Play Point Park On পাঠান:\n\n/delivery_pp_{user_id}"

        bot.send_message(ADMIN_ID, instructions)
        bot.answer_callback_query(call.id, "✅ Delivery instructions sent")

@bot.message_handler(func=lambda m: m.text == "📥 Gmail Buy")
def gmail_buy(message):
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
    bot.send_message(message.chat.id, options, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["🇺🇸 USA Gmail (15TK)", "🇧🇩 BD Gmail (10TK)"])
def select_gmail_type(message):
    users[str(message.from_user.id)]["gmail_type"] = message.text
    
    quantity_msg = """
🔢 কতগুলো Gmail চান?

💡 পরিমাণ লিখুন (সংখ্যা):
- 1 টি Gmail
- 5 টি Gmail
- 10 টি Gmail

বিঃদ্রঃ: বেশি কিনলে ডিসকাউন্ট পেতে পারেন!
"""
    msg = bot.send_message(message.chat.id, quantity_msg, reply_markup=back_markup())
    bot.register_next_step_handler(msg, process_gmail_quantity)

def process_gmail_quantity(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    try:
        quantity = int(message.text)
        if quantity <= 0:
            raise ValueError

        user_id = str(message.from_user.id)    
        users[user_id]["gmail_quantity"] = quantity    
        gmail_type = users[user_id]["gmail_type"]    
        
        base_price = 15 if "USA" in gmail_type else 10
        price = base_price * quantity
        
        if quantity >= 10:
            discount = price * 0.10
            price -= discount
            discount_msg = f"🎉 ১০+ অর্ডারে ১০% ডিসকাউন্ট পেয়েছেন! (-{discount:.0f} TK)"
        elif quantity >= 5:
            discount = price * 0.05
            price -= discount
            discount_msg = f"🎉 ৫+ অর্ডারে ৫% ডিসকাউন্ট পেয়েছেন! (-{discount:.0f} TK)"
        else:
            discount_msg = ""
        
        users[user_id]["gmail_price"] = int(price)
        
        order_summary = f"""
📝 অর্ডার সারাংশ:

📧 Type: {gmail_type}
🔢 Quantity: {quantity} টি
{discount_msg}
💰 মোট মূল্য: {int(price)} TK

💳 পেমেন্ট মাধ্যম নির্বাচন করুন:
"""
        bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
        bot.register_next_step_handler(message, process_gmail_payment)

    except:
        error_msg = """
❌ অবৈধ সংখ্যা! শুধুমাত্র সংখ্যা লিখুন:

উদাহরণ: 1, 5, 10

আবার চেষ্টা করুন:
"""
        msg = bot.send_message(message.chat.id, error_msg, reply_markup=back_markup())
        bot.register_next_step_handler(msg, process_gmail_quantity)

@bot.message_handler(func=lambda m: m.text in ["📲 Bkash", "📲 Nagad"] and "gmail_price" in users.get(str(m.from_user.id), {}))
def process_gmail_payment(message):
    user_id = str(message.from_user.id)
    user_data = users[user_id]

    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    price = user_data["gmail_price"]
    gmail_type = user_data["gmail_type"]
    quantity = user_data["gmail_quantity"]

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

    txn_id = message.text
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

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_gmail_{user_id}"))

    admin_msg = f"""
🛒 নতুন Gmail অর্ডার:

📦 Order ID: {order_id}
👤 User: @{message.from_user.username or 'N/A'}
🆔 User ID: {user_id}
📧 Type: {gmail_type}
🔢 Quantity: {quantity}
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
🔢 Quantity: {quantity}
💰 Paid: {price} TK

আপনার অর্ডারটি প্রসেস করা হচ্ছে। 
ডেলিভারি সময়: ১-১২ ঘন্টা

সেবা নেওয়ার জন্য ধন্যবাদ! 🙏
"""
    bot.send_message(message.chat.id, user_confirmation)
    home_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "💳 Balance")
def check_balance(message):
    user_id = str(message.from_user.id)
    if user_id in users:
        balance = users[user_id]["balance"]
        hold = users[user_id]["hold"]
        ref_count = users[user_id]["referral_count"]
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
    if user_id in users:
        balance = users[user_id]["balance"]

        if balance < 60:
            error_msg = f"""
❌ সর্বনিম্ন উত্তোলন 60 টাকা

💰 আপনার ব্যালেন্স: {balance} TK
🎯 প্রয়োজন: {60 - balance} TK more

💡 টাকা উপার্জনের উপায়:
1. Gmail বিক্রি করুন (৭ TK/Gmail)
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
            
        users[user_id]["balance"] -= amount    
        users[user_id]["hold"] += amount
        save_users()
        
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
        users[str(message.from_user.id)]["balance"] += amount
        users[str(message.from_user.id)]["hold"] -= amount
        save_users()
        return home_menu(message.chat.id)

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
        users[str(message.from_user.id)]["balance"] += amount
        users[str(message.from_user.id)]["hold"] -= amount
        save_users()
        return home_menu(message.chat.id)

    number = message.text
    user_id = str(message.from_user.id)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Pay", callback_data=f"pay_{user_id}_{amount}"))

    withdraw_id = f"WD{int(time.time())}{user_id}"
    
    admin_msg = f"""
💸 নতুন উত্তোলনের অনুরোধ:

📋 Withdrawal ID: {withdraw_id}
👤 User: @{message.from_user.username or 'N/A'}
🆔 User ID: {user_id}
💰 Amount: {amount} TK
📱 Method: {method}
📞 Number: {number}
⏰ Time: {time.strftime("%Y-%m-%d %H:%M:%S")}

💡 User Balance: {users[user_id]['balance']} TK
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

@bot.message_handler(func=lambda m: m.text == "🌐 Paid VPN Buy")
def vpn_buy(message):
    vpn_options = """
🔒 VPN প্যাকেজ নির্বাচন করুন:

NordVPN 7 Days (30TK)
- উচ্চ গতি
- 60+ দেশ
- No Logs Policy

ExpressVPN 7 Days (30TK)
- সর্বোচ্চ গতি
- 90+ দেশ
- TrustedServer Technology

💡 উভয় VPN Premium quality এর
"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("NordVPN 7 Days (30TK)", "ExpressVPN 7 Days (30TK)", "↩️ মেনুতে ফিরে যান")
    bot.send_message(message.chat.id, vpn_options, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["NordVPN 7 Days (30TK)", "ExpressVPN 7 Days (30TK)"])
def select_vpn(message):
    users[str(message.from_user.id)]["vpn"] = message.text
    
    order_summary = f"""
📝 অর্ডার সারাংশ:

🔒 Service: {message.text}
💰 মূল্য: 30 TK

💳 পেমেন্ট মাধ্যম নির্বাচন করুন:
"""
    bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
    bot.register_next_step_handler(message, process_vpn_payment)

def process_vpn_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    
    payment_instructions = f"""
💳 {method} এ টাকা পাঠান:

📱 Number: {payment_number}
💰 Amount: 30 TK
📝 Reference: VPN

⚠️ টাকা পাঠানোর পর Transaction ID নোট করে রাখুন

📨 এখন আপনার Transaction ID লিখুন:
"""
    msg = bot.send_message(message.chat.id, payment_instructions, reply_markup=back_markup())
    bot.register_next_step_handler(msg, lambda m: confirm_vpn_order(m, method))

def confirm_vpn_order(message, method):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    txn_id = message.text
    user_id = str(message.from_user.id)
    vpn = users[user_id]["vpn"]

    order_id = f"VPN{int(time.time())}{user_id}"
    orders[order_id] = {
        "user_id": user_id,
        "service": "VPN",
        "type": vpn,
        "price": 30,
        "method": method,
        "txn_id": txn_id,
        "status": "pending"
    }

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_vpn_{user_id}"))

    admin_msg = f"""
🔐 নতুন VPN অর্ডার:

📦 Order ID: {order_id}
👤 User: @{message.from_user.username or 'N/A'}
🆔 User ID: {user_id}
🔒 VPN: {vpn}
💰 Amount: 30 TK
💳 Method: {method}
📝 Txn ID: {txn_id}
⏰ Time: {time.strftime("%Y-%m-%d %H:%M:%S")}"
"""
    bot.send_message(ADMIN_ID, admin_msg, reply_markup=markup)

    user_confirmation = f"""
✅ আপনার অর্ডার কনফার্ম হয়েছে!

📦 Order ID: {order_id}
🔒 Service: {vpn}
💰 Paid: 30 TK

আপনার অর্ডারটি প্রসেস করা হচ্ছে। 
ডেলিভারি সময়: ১-৬ ঘন্টা

সেবা নেওয়ার জন্য ধন্যবাদ! 🙏
"""
    bot.send_message(message.chat.id, user_confirmation)
    home_menu(message.chat.id)

@bot.message_handler(func=lambda m: m.text == "🎥 YouTube Premium")
def yt_premium(message):
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
    bot.send_message(message.chat.id, yt_options, reply_markup=markup)

@bot.message_handler(func=lambda m: m.text in ["1 Month (25TK)", "1 Year (150TK)"])
def select_yt_plan(message):
    users[str(message.from_user.id)]["yt_plan"] = message.text
    price = 25 if "Month" in message.text else 150
    
    order_summary = f"""
📝 অর্ডার সারাংশ:

🎬 Service: {message.text}
💰 মূল্য: {price} TK

💳 পেমেন্ট মাধ্যম নির্বাচন করুন:
"""
    bot.send_message(message.chat.id, order_summary, reply_markup=payment_markup())
    bot.register_next_step_handler(message, process_yt_payment)

def process_yt_payment(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    method = "Bkash" if "Bkash" in message.text else "Nagad"
    payment_number = ADMIN_BKASH_NO if method == "Bkash" else ADMIN_NAGAD_NO
    yt_plan = users[str(message.from_user.id)]["yt_plan"]
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
    bot.register_next_step_handler(msg, lambda m: confirm_yt_order(m, method))

def confirm_yt_order(message, method):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    txn_id = message.text
    user_id = str(message.from_user.id)
    yt_plan = users[user_id]["yt_plan"]
    price = 25 if "Month" in yt_plan else 150

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

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Deliver", callback_data=f"deliver_yt_{user_id}"))

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

@bot.message_handler(func=lambda m: m.text == "👥 Refer")
def refer(message):
    user_id = str(message.from_user.id)
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
- বাকি রয়েছে: {ref_count * 2} TK উপার্জন

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

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ আপনার অনুমতি নেই!")
        return

    total_users = len(users)
    total_balance = sum(user["balance"] for user in users.values())
    total_hold = sum(user["hold"] for user in users.values())
    total_pending_gmails = len(pending_gmails)

    admin_msg = f"""
👑 অ্যাডমিন প্যানেল:

📊 স্ট্যাটিস্টিক্স:
👥 মোট ইউজার: {total_users}
💰 মোট ব্যালেন্স: {total_balance} TK
⏳ মোট Hold: {total_hold} TK
📧 Pending Gmails: {total_pending_gmails}

🛠️ অ্যাডমিন কমান্ড:
/stats - বিস্তারিত স্ট্যাটিস্টিক্স
/users - ইউজার তালিকা
/broadcast - ব্রডকাস্ট মেসেজ
/notify - নির্দিষ্ট ইউজারকে মেসেজ
"""
    bot.send_message(message.chat.id, admin_msg)

@bot.message_handler(commands=['stats'])
def stats(message):
    if str(message.from_user.id) != ADMIN_ID:
        return

    total_earnings = sum(user["balance"] + user["hold"] for user in users.values())
    total_ref_earnings = sum(user["referral_count"] * 2 for user in users.values())
    total_gmail_earnings = total_earnings - total_ref_earnings

    stats_msg = f"""
📈 বিস্তারিত স্ট্যাটিস্টিক্স:

💰 মোট আয়: {total_earnings} TK
📧 Gmail থেকে: {total_gmail_earnings} TK
👥 রেফার থেকে: {total_ref_earnings} TK

📊 ইউজার এক্টিভিটি:
- গড় ব্যালেন্স: {total_earnings/len(users):.2f} TK/User
- গড় রেফার: {sum(user["referral_count"] for user in users.values())/len(users):.2f}/User

📅 আজকের স্ট্যাটস:
- নতুন ইউজার: {len([u for u in users.values() if u.get('joined_date', '').startswith(time.strftime('%Y-%m-%d'))])}
- আজকের আয়: {total_earnings/30:.2f} TK (approx)
"""
    bot.send_message(message.chat.id, stats_msg)

@bot.message_handler(commands=['users'])
def list_users(message):
    if str(message.from_user.id) != ADMIN_ID:
        return

    users_list = "\n".join([f"👤 @{u['username'] or 'N/A'} | ID: {uid} | Bal: {u['balance']} TK" for uid, u in list(users.items())[:10]])
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
            f.write(f"ID: {uid} | User: @{u['username'] or 'N/A'} | Bal: {u['balance']} TK | Ref: {u['referral_count']} | Joined: {u.get('joined_date', 'N/A')}\n")
    
    with open("users.txt", "rb") as f:
        bot.send_document(message.chat.id, f, caption="📊 সকল ইউজারের তালিকা")

# New broadcast logic with photo support
@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ আপনার অনুমতি নেই!")
        return

    msg = bot.send_message(message.chat.id, "📢 ব্রডকাস্ট মেসেজ পাঠাতে চান? একটি ছবিসহ ক্যাপশন লিখে পাঠান। শুধু টেক্সট পাঠাতে চাইলে সরাসরি মেসেজ লিখুন।")
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
                bot.send_photo(user_id, photo_id, caption=caption)
                success += 1
                time.sleep(0.1)
            except Exception as e:
                print(f"Failed to send photo broadcast to {user_id}: {e}")
                failed += 1
    else:
        broadcast_msg = message.text
        for user_id in users:
            try:
                bot.send_message(user_id, f"📢 ব্রডকাস্ট:\n\n{broadcast_msg}")
                success += 1
                time.sleep(0.1)
            except Exception as e:
                print(f"Failed to send text broadcast to {user_id}: {e}")
                failed += 1

    bot.send_message(message.chat.id, f"""
✅ ব্রডকাস্ট সম্পন্ন!

📊 রেজাল্ট:
✅ সফল: {success}
❌ ব্যর্থ: {failed}
📊 মোট: {success + failed}
""")
    bot.clear_step_handler(message)

# New notify logic with photo support
@bot.message_handler(commands=['notify'])
def notify_user(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ আপনার অনুমতি নেই!")
        return

    msg = bot.send_message(message.chat.id, "👤 ইউজার ID লিখুন যাকে মেসেজ পাঠাতে চান:")
    bot.register_next_step_handler(msg, get_notify_message)

def get_notify_message(message):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)
    
    try:
        user_id = str(message.text)
        if user_id not in users:
            bot.send_message(message.chat.id, "❌ এই ইউজার ID খুঁজে পাওয়া যায়নি!")
            bot.clear_step_handler(message)
            return home_menu(message.chat.id)
        
        msg = bot.send_message(message.chat.id, "💬 মেসেজ পাঠাতে চান? একটি ছবিসহ ক্যাপশন লিখে পাঠান। শুধু টেক্সট পাঠাতে চাইলে সরাসরি মেসেজ লিখুন।")
        bot.register_next_step_handler(msg, lambda m: send_notification(m, user_id))
    except:
        bot.send_message(message.chat.id, "❌ অবৈধ ইউজার ID!")
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

def send_notification(message, user_id):
    if message.text == "↩️ মেনুতে ফিরে যান":
        bot.clear_step_handler(message)
        return home_menu(message.chat.id)

    try:
        if message.photo:
            photo_id = message.photo[-1].file_id
            caption = message.caption or ""
            bot.send_photo(user_id, photo_id, caption=f"📨 Admin থেকে মেসেজ:\n\n{caption}")
        else:
            bot.send_message(user_id, f"📨 Admin থেকে মেসেজ:\n\n{message.text}")
        
        bot.send_message(message.chat.id, "✅ মেসেজ পাঠানো হয়েছে!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ ইউজারকে মেসেজ পাঠানো যায়নি! Error: {e}")
    
    bot.clear_step_handler(message)
    home_menu(message.chat.id)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    # Check for menu button presses first
    menu_buttons = {
        "📤 Gmail Sell": gmail_sell,
        "📥 Gmail Buy": gmail_buy,
        "💳 Balance": check_balance,
        "💵 Withdraw": withdraw,
        "🌐 Paid VPN Buy": vpn_buy,
        "🎥 YouTube Premium": yt_premium,
        "👥 Refer": refer,
        "🆘 Support": support,
        "🎁 Play Point Park On": play_point_menu,
    }
    
    if message.text in menu_buttons:
        bot.clear_step_handler(message)
        menu_buttons[message.text](message)
        return

    bot.clear_step_handler(message)
    
    if message.text not in ["🇺🇸 USA", "🇹🇼 Taiwan", "🇬🇧 UK", "🇰🇷 South Korean", "📲 Bkash", "📲 Nagad"] and not message.text.startswith('/'):
        unknown_msg = """
❌ অজানা কমান্ড!

আপনার মেসেজটি বুঝা যায়নি। অনুগ্রহ করে নিচের মেনু থেকে একটি অপশন নির্বাচন করুন।
"""
        bot.send_message(message.chat.id, unknown_msg)
    
    home_menu(message.chat.id)

if __name__ == "__main__":
    print("🤖 Bot is running...")
    bot.infinity_polling()
