import logging
import time
import sqlite3
import uuid
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Bot configuration
BOT_TOKEN = "8381651968:AAF_aElufjur3GUnSwaSAYyrnc6eT2A-zxQ"  # Replace with your actual bot token from @BotFather
ADMIN_IDS = [8367788232]  # Replace with your admin user ID(s)
BANK_ACCOUNT = {"bank": "Moremonee", "name": "Victor Chukwuka", "number": "7062791952"}
SUPPORT_EMAIL = "victorextrader@gmail.com"
VERIFICATION_FEE = 10000  # ₦10,000
MIN_WITHDRAWAL = 50000  # ₦50,000

# Database setup
def init_db():
    conn = sqlite3.connect('money_bot.db')
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        balance INTEGER DEFAULT 0,
        total_earned INTEGER DEFAULT 0,
        verified INTEGER DEFAULT 0,
        joined_date TEXT,
        last_claim INTEGER DEFAULT 0,
        referrals INTEGER DEFAULT 0,
        banned INTEGER DEFAULT 0,
        referred_by INTEGER DEFAULT NULL,
        unique_code TEXT
    )
    ''')
    
    # Transactions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        type TEXT,
        amount INTEGER,
        status TEXT,
        timestamp TEXT,
        details TEXT,
        unique_id TEXT
    )
    ''')
    
    # Withdrawal requests table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        bank_name TEXT,
        account_name TEXT,
        account_number TEXT,
        status TEXT DEFAULT 'pending',
        timestamp TEXT,
        unique_id TEXT
    )
    ''')
    
    # Verification requests table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount INTEGER,
        receipt_url TEXT,
        status TEXT DEFAULT 'pending',
        timestamp TEXT,
        unique_id TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

# Database helper functions
def get_user(user_id):
    conn = sqlite3.connect('money_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {
            'user_id': user[0],
            'username': user[1],
            'first_name': user[2],
            'last_name': user[3],
            'balance': user[4],
            'total_earned': user[5],
            'verified': user[6],
            'joined_date': user[7],
            'last_claim': user[8],
            'referrals': user[9],
            'banned': user[10],
            'referred_by': user[11],
            'unique_code': user[12]
        }
    return None

def create_user(user_id, username, first_name, last_name):
    conn = sqlite3.connect('money_bot.db')
    cursor = conn.cursor()
    joined_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    unique_code = str(uuid.uuid4())[:8].upper()
    cursor.execute(
        "INSERT INTO users (user_id, username, first_name, last_name, joined_date, unique_code) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, username, first_name, last_name, joined_date, unique_code)
    )
    conn.commit()
    conn.close()

def update_user(user_id, field, value):
    conn = sqlite3.connect('money_bot.db')
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()

def add_transaction(user_id, type, amount, status, details=""):
    conn = sqlite3.connect('money_bot.db')
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    unique_id = str(uuid.uuid4())[:12].upper()
    cursor.execute(
        "INSERT INTO transactions (user_id, type, amount, status, timestamp, details, unique_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, type, amount, status, timestamp, details, unique_id)
    )
    conn.commit()
    conn.close()
    return unique_id

def add_withdrawal_request(user_id, amount, bank_name, account_name, account_number):
    conn = sqlite3.connect('money_bot.db')
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    unique_id = str(uuid.uuid4())[:12].upper()
    cursor.execute(
        "INSERT INTO withdrawals (user_id, amount, bank_name, account_name, account_number, timestamp, unique_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, amount, bank_name, account_name, account_number, timestamp, unique_id)
    )
    conn.commit()
    conn.close()
    return unique_id

def add_verification_request(user_id, amount, receipt_url):
    conn = sqlite3.connect('money_bot.db')
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    unique_id = str(uuid.uuid4())[:12].upper()
    cursor.execute(
        "INSERT INTO verifications (user_id, amount, receipt_url, timestamp, unique_id) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, receipt_url, timestamp, unique_id)
    )
    conn.commit()
    conn.close()
    return unique_id

def get_all_users():
    conn = sqlite3.connect('money_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    conn.close()
    return users

def get_pending_withdrawals():
    conn = sqlite3.connect('money_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM withdrawals WHERE status = 'pending'")
    withdrawals = cursor.fetchall()
    conn.close()
    return withdrawals

def get_pending_verifications():
    conn = sqlite3.connect('money_bot.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM verifications WHERE status = 'pending'")
    verifications = cursor.fetchall()
    conn.close()
    return verifications

def update_withdrawal_status(withdrawal_id, status):
    conn = sqlite3.connect('money_bot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE withdrawals SET status = ? WHERE id = ?", (status, withdrawal_id))
    conn.commit()
    conn.close()

def update_verification_status(verification_id, status):
    conn = sqlite3.connect('money_bot.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE verifications SET status = ? WHERE id = ?", (status, verification_id))
    conn.commit()
    conn.close()

# Keyboard functions
def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("💰 Fund Me", callback_data='fund_me')],
        [InlineKeyboardButton("🏦 Bank Details", callback_data='bank_details'),
         InlineKeyboardButton("💳 Withdraw", callback_data='withdraw')],
        [InlineKeyboardButton("👥 Referral", callback_data='referral'),
         InlineKeyboardButton("✅ Verify Account", callback_data='verify_account')],
        [InlineKeyboardButton("🆘 Support", callback_data='support'),
         InlineKeyboardButton("ℹ️ About", callback_data='about')],
        [InlineKeyboardButton("📜 Rules", callback_data='rules')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔙 Back to Main", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_data = get_user(user.id)
    
    if not user_data:
        create_user(user.id, user.username, user.first_name, user.last_name)
        user_data = get_user(user.id)
    
    if user_data['banned']:
        await update.message.reply_text("🚫 Your account has been banned for fraudulent activity.")
        return
    
    # Check if user was referred
    if context.args and not user_data.get('referred_by'):
        try:
            referrer_id = int(context.args[0])
            referrer_data = get_user(referrer_id)
            if referrer_data and referrer_id != user.id:
                update_user(user.id, 'referred_by', referrer_id)
                update_user(referrer_id, 'referrals', referrer_data['referrals'] + 1)
                update_user(referrer_id, 'balance', referrer_data['balance'] + 5000)
                update_user(referrer_id, 'total_earned', referrer_data['total_earned'] + 5000)
                add_transaction(referrer_id, 'referral', 5000, 'completed', f"Referral bonus for {user.id}")
                
                # Notify referrer
                try:
                    await context.bot.send_message(
                        chat_id=referrer_id, 
                        text=f"🎉 You've received ₦5000 referral bonus from {user.first_name}! Your new balance: ₦{referrer_data['balance'] + 5000}"
                    )
                except:
                    pass
        except ValueError:
            pass
    
    welcome_text = (
        f"👑 Welcome {user.first_name} to Victorex Trader Grant! 👑\n\n"
        "🌟 The Premier Platform for Financial Freedom in Nigeria 🌟\n\n"
        "💵 Earn ₦1000 every minute by clicking 'Fund Me'!\n"
        "👥 Refer friends and get ₦5000 for each referral!\n"
        "🏦 Withdraw your earnings directly to your bank account!\n\n"
        "Your Unique ID: {user_data['unique_code']}\n\n"
        "Use the buttons below to navigate:"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 <b>Victorex Trader Grant Help Center</b>\n\n"
        "• <b>💰 Fund Me</b>: Click every minute to claim ₦1000\n"
        "• <b>🏦 Bank Details</b>: View our bank account information\n"
        "• <b>💳 Withdraw</b>: Request a withdrawal of your earnings (Min: ₦50,000)\n"
        "• <b>👥 Referral</b>: Get your referral link and earn ₦5000 per referral\n"
        "• <b>✅ Verify Account</b>: Verify your account by depositing ₦10,000\n"
        "• <b>🆘 Support</b>: Contact our support team\n"
        "• <b>ℹ️ About</b>: Learn more about our platform\n"
        "• <b>📜 Rules</b>: Read our terms and conditions\n\n"
        "Start your journey to financial freedom now!"
    )
    await update.message.reply_text(help_text, parse_mode='HTML', reply_markup=get_main_keyboard())

# Admin commands
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    commands = (
        "👑 <b>Victorex Trader Grant Admin Panel</b>\n\n"
        "/users - View all users\n"
        "/broadcast [message] - Send message to all users\n"
        "/bann [user_id] - Ban a user\n"
        "/unbann [user_id] - Unban a user\n"
        "/pay [user_id] [amount] - Pay a user\n"
        "/stats - View bot statistics\n"
        "/pending_verifications - View pending verification requests\n"
        "/pending_withdrawals - View pending withdrawal requests\n"
        "/approve_verification [verification_id] - Approve a verification\n"
        "/approve_withdrawal [withdrawal_id] - Approve a withdrawal\n"
        "/reject_withdrawal [withdrawal_id] - Reject a withdrawal"
    )
    await update.message.reply_text(commands, parse_mode='HTML')

async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    users = get_all_users()
    if not users:
        await update.message.reply_text("No users yet.")
        return
    
    users_text = "👥 <b>All Users</b>\n\n"
    for user in users:
        users_text += f"ID: {user[0]}, Name: {user[2]} {user[3]}, Balance: ₦{user[4]}, Total Earned: ₦{user[5]}, Verified: {bool(user[6])}, Banned: {bool(user[10])}\n"
    
    await update.message.reply_text(users_text, parse_mode='HTML')

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast [message]")
        return
    
    message = " ".join(context.args)
    users = get_all_users()
    success_count = 0
    
    for user in users:
        try:
            await context.bot.send_message(chat_id=user[0], text=f"📢 Victorex Trader Grant-Bot Announcement:\n\n{message}")
            success_count += 1
        except Exception as e:
            print(f"Failed to send message to user {user[0]}: {e}")
    
    await update.message.reply_text(f"Broadcast sent to {success_count} users.")

async def admin_bann(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Usage: /bann [user_id]")
        return
    
    try:
        target_user_id = int(context.args[0])
        user_data = get_user(target_user_id)
        
        if not user_data:
            await update.message.reply_text("User not found.")
            return
        
        update_user(target_user_id, 'banned', 1)
        await update.message.reply_text(f"User {target_user_id} has been banned.")
        
        # Notify user
        try:
            await context.bot.send_message(chat_id=target_user_id, text="🚫 Your account has been banned for violating our terms of service.")
        except:
            pass
    except ValueError:
        await update.message.reply_text("Invalid user ID.")

async def admin_unbann(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Usage: /unbann [user_id]")
        return
    
    try:
        target_user_id = int(context.args[0])
        user_data = get_user(target_user_id)
        
        if not user_data:
            await update.message.reply_text("User not found.")
            return
        
        update_user(target_user_id, 'banned', 0)
        await update.message.reply_text(f"User {target_user_id} has been unbanned.")
        
        # Notify user
        try:
            await context.bot.send_message(chat_id=target_user_id, text="✅ Your account has been unbanned. You can now use our services again.")
        except:
            pass
    except ValueError:
        await update.message.reply_text("Invalid user ID.")

async def admin_pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /pay [user_id] [amount]")
        return
    
    try:
        target_user_id = int(context.args[0])
        amount = int(context.args[1])
        
        user_data = get_user(target_user_id)
        if not user_data:
            await update.message.reply_text("User not found.")
            return
        
        new_balance = user_data['balance'] + amount
        new_total = user_data['total_earned'] + amount
        update_user(target_user_id, 'balance', new_balance)
        update_user(target_user_id, 'total_earned', new_total)
        add_transaction(target_user_id, 'admin_payment', amount, 'completed', f"Admin payment from user {user_id}")
        
        await update.message.reply_text(f"₦{amount} has been added to user {target_user_id}'s balance. New balance: ₦{new_balance}")
        
        # Notify the user
        try:
            await context.bot.send_message(chat_id=target_user_id, text=f"🎉 You have received ₦{amount} from admin. Your new balance: ₦{new_balance}")
        except Exception as e:
            print(f"Failed to notify user {target_user_id}: {e}")
    except ValueError:
        await update.message.reply_text("Invalid user ID or amount.")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    users = get_all_users()
    total_users = len(users)
    total_balance = sum(user[4] for user in users)
    total_earned = sum(user[5] for user in users)
    total_verified = sum(1 for user in users if user[6])
    total_banned = sum(1 for user in users if user[10])
    total_referrals = sum(user[9] for user in users)
    
    stats_text = (
        "📊 <b>Victorex Trader Grant Statistics</b>\n\n"
        f"Total Users: {total_users}\n"
        f"Total Balance: ₦{total_balance}\n"
        f"Total Earned: ₦{total_earned}\n"
        f"Verified Users: {total_verified}\n"
        f"Banned Users: {total_banned}\n"
        f"Total Referrals: {total_referrals}"
    )
    
    await update.message.reply_text(stats_text, parse_mode='HTML')

async def admin_pending_verifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    verifications = get_pending_verifications()
    if not verifications:
        await update.message.reply_text("No pending verification requests.")
        return
    
    verification_text = "📋 <b>Pending Verification Requests</b>\n\n"
    for verification in verifications:
        user_data = get_user(verification[1])
        username = user_data['username'] if user_data else "Unknown"
        verification_text += f"ID: {verification[0]}, User: {username} (ID: {verification[1]}), Amount: ₦{verification[2]}, Receipt: {verification[3]}\n"
    
    await update.message.reply_text(verification_text, parse_mode='HTML')

async def admin_pending_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    withdrawals = get_pending_withdrawals()
    if not withdrawals:
        await update.message.reply_text("No pending withdrawal requests.")
        return
    
    withdrawal_text = "📋 <b>Pending Withdrawal Requests</b>\n\n"
    for withdrawal in withdrawals:
        user_data = get_user(withdrawal[1])
        username = user_data['username'] if user_data else "Unknown"
        withdrawal_text += f"ID: {withdrawal[0]}, User: {username} (ID: {withdrawal[1]}), Amount: ₦{withdrawal[2]}, Bank: {withdrawal[3]}, Account: {withdrawal[5]}\n"
    
    await update.message.reply_text(withdrawal_text, parse_mode='HTML')

async def admin_approve_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Usage: /approve_verification [verification_id]")
        return
    
    try:
        verification_id = int(context.args[0])
        update_verification_status(verification_id, 'approved')
        
        # Get verification details
        conn = sqlite3.connect('money_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM verifications WHERE id = ?", (verification_id,))
        verification = cursor.fetchone()
        conn.close()
        
        if verification:
            user_id = verification[1]
            update_user(user_id, 'verified', 1)
            
            await update.message.reply_text(f"Verification {verification_id} approved. User {user_id} is now verified.")
            
            # Notify user
            try:
                await context.bot.send_message(chat_id=user_id, text="✅ Your account verification has been approved! You can now make withdrawals.")
            except:
                pass
        else:
            await update.message.reply_text("Verification not found.")
    except ValueError:
        await update.message.reply_text("Invalid verification ID.")

async def admin_approve_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Usage: /approve_withdrawal [withdrawal_id]")
        return
    
    try:
        withdrawal_id = int(context.args[0])
        
        # Get withdrawal details
        conn = sqlite3.connect('money_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,))
        withdrawal = cursor.fetchone()
        conn.close()
        
        if not withdrawal:
            await update.message.reply_text("Withdrawal not found.")
            return
        
        user_id = withdrawal[1]
        amount = withdrawal[2]
        
        user_data = get_user(user_id)
        if not user_data:
            await update.message.reply_text("User not found.")
            return
        
        if user_data['balance'] < amount:
            await update.message.reply_text("User doesn't have enough balance for this withdrawal.")
            return
        
        # Update user balance and withdrawal status
        new_balance = user_data['balance'] - amount
        update_user(user_id, 'balance', new_balance)
        update_withdrawal_status(withdrawal_id, 'approved')
        
        await update.message.reply_text(f"Withdrawal {withdrawal_id} approved. ₦{amount} has been deducted from user {user_id}'s balance.")
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=user_id, 
                text=f"💸💸 Your withdrawal request of ₦{amount} has been approved! Please allow 24-72 hours for the funds to reflect in your bank account due to bank processing times."
            )
        except:
            pass
    except ValueError:
        await update.message.reply_text("Invalid withdrawal ID.")

async def admin_reject_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized access.")
        return
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("Usage: /reject_withdrawal [withdrawal_id]")
        return
    
    try:
        withdrawal_id = int(context.args[0])
        update_withdrawal_status(withdrawal_id, 'rejected')
        
        await update.message.reply_text(f"Withdrawal {withdrawal_id} has been rejected.")
        
        # Get withdrawal details to notify user
        conn = sqlite3.connect('money_bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM withdrawals WHERE id = ?", (withdrawal_id,))
        withdrawal = cursor.fetchone()
        conn.close()
        
        if withdrawal:
            user_id = withdrawal[1]
            amount = withdrawal[2]
            
            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=user_id, 
                    text=f"❌ Your withdrawal request of ₦{amount} has been rejected. Please contact support for more information."
                )
            except:
                pass
    except ValueError:
        await update.message.reply_text("Invalid withdrawal ID.")

# Callback query handler
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data = get_user(user_id)
    
    if not user_data:
        create_user(user_id, query.from_user.username, query.from_user.first_name, query.from_user.last_name)
        user_data = get_user(user_id)
    
    if user_data['banned']:
        await query.edit_message_text("🚫 Your account has been banned for fraudulent activity.")
        return
    
    if query.data == 'main_menu':
        await query.edit_message_text("Main menu:", reply_markup=get_main_keyboard())
        return
    
    if query.data == 'fund_me':
        current_time = time.time()
        last_claim = user_data['last_claim']
        
        if current_time - last_claim < 60:  # 60 seconds cooldown
            wait_time = int(60 - (current_time - last_claim))
            await query.edit_message_text(
                f"⏳ Please wait {wait_time} seconds before claiming again.",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Update balance and last claim time
        new_balance = user_data['balance'] + 1000
        new_total = user_data['total_earned'] + 1000
        update_user(user_id, 'balance', new_balance)
        update_user(user_id, 'total_earned', new_total)
        update_user(user_id, 'last_claim', current_time)
        transaction_id = add_transaction(user_id, 'claim', 1000, 'completed', "Claimed ₦1000")
        
        await query.edit_message_text(
            f"🎉 You've claimed ₦1000! Your new balance: ₦{new_balance}\n\n"
            f"Transaction ID: {transaction_id}",
            reply_markup=get_back_keyboard()
        )
    
    elif query.data == 'bank_details':
        bank_text = (
            "🏦 <b> Victorex Trader Grant-Bot</b>\n\n"
            f"Bank: {BANK_ACCOUNT['bank']}\n"
            f"Account Name: {BANK_ACCOUNT['name']}\n"
            f"Account Number: {BANK_ACCOUNT['number']}\n\n"
            "Use these details for verification deposit of ₦10,000."
        )
        await query.edit_message_text(bank_text, parse_mode='HTML', reply_markup=get_back_keyboard())
    
    elif query.data == 'withdraw':
        if user_data['balance'] < MIN_WITHDRAWAL:
            await query.edit_message_text(
                f"❌ Minimum withdrawal amount is ₦{MIN_WITHDRAWAL}. Continue earning to reach this amount.",
                reply_markup=get_back_keyboard()
            )
            return
        
        if not user_data['verified']:
            await query.edit_message_text(
                "❌ You need to verify your account before withdrawing. Please use the 'Verify Account' option.",
                reply_markup=get_back_keyboard()
            )
            return
        
        # Store user ID in context for the next message
        context.user_data['awaiting_withdrawal'] = True
        context.user_data['withdrawal_amount'] = user_data['balance']
        
        await query.edit_message_text(
            f"💳 <b>Withdrawal Request</b>\n\n"
            f"Your balance: ₦{user_data['balance']}\n"
            f"Minimum withdrawal: ₦{MIN_WITHDRAWAL}\n\n"
            "Please send your bank details in the following format:\n\n"
            "<code>Bank Name, Account Name, Account Number</code>\n\n"
            "Example:\n"
            "<code>GTBank, John Doe, 0123456789</code>",
            parse_mode='HTML',
            reply_markup=get_back_keyboard()
        )
    
    elif query.data == 'referral':
        referral_link = f"https://t.me/{(await context.bot.get_me()).username}?start={user_id}"
        referral_text = (
            "👥 <b>Victorex Trader Grant Referral Program</b>\n\n"
            "Earn ₦5000 for each friend who joins using your referral link and completes verification!\n\n"
            f"Your referral link:\n<code>{referral_link}</code>\n\n"
            f"Total referrals: {user_data['referrals']}\n"
            f"Earned from referrals: ₦{user_data['referrals'] * 5000}"
        )
        await query.edit_message_text(referral_text, parse_mode='HTML', reply_markup=get_back_keyboard())
    
    elif query.data == 'verify_account':
        if user_data['verified']:
            await query.edit_message_text(
                "✅ Your account is already verified!",
                reply_markup=get_back_keyboard()
            )
            return
        
        verification_text = (
            "✅ <b>Victorex Trader Grant Account Verification</b>\n\n"
            "To verify your account, please deposit ₦10,000 to our bank account:\n\n"
            f"Bank: {BANK_ACCOUNT['bank']}\n"
            f"Account Name: {BANK_ACCOUNT['name']}\n"
            f"Account Number: {BANK_ACCOUNT['number']}\n\n"
            "After depositing, please send the receipt to this bot. "
            "Include your unique code in the transaction description: "
            f"<code>{user_data['unique_code']}</code>\n\n"
            "Your account will be verified within 24 hours after receipt confirmation."
        )
        await query.edit_message_text(verification_text, parse_mode='HTML', reply_markup=get_back_keyboard())
    
    elif query.data == 'support':
        support_text = (
            "🆘 <b>Victorex Trader Grant Support</b>\n\n"
            "For any issues or questions, please contact our support team:\n\n"
            f"Email: {SUPPORT_EMAIL}\n\n"
            "We're here to help you 24/7!"
        )
        await query.edit_message_text(support_text, parse_mode='HTML', reply_markup=get_back_keyboard())
    
    elif query.data == 'about':
        about_text = (
            "ℹ️ <b>About Victorex Trader Grant</b>\n\n"
            "We are Nigeria's premier platform for financial empowerment! 🇳🇬\n\n"
            "🌟 <b>Our Mission</b>: To help Nigerians achieve financial freedom through our innovative earning platform.\n\n"
            "💰 <b>What We Offer</b>:\n"
            "• Earn ₦1000 every minute\n"
            "• ₦5000 referral bonuses\n"
            "• Secure withdrawals to your bank account\n"
            "• 24/7 customer support\n\n"
            "We've distributed over ₦10B to Nigerians seeking legitimate online income opportunities!\n\n"
            "Join thousands of satisfied users who are transforming their financial lives with RoyalEarnings! 🚀"
        )
        await query.edit_message_text(about_text, parse_mode='HTML', reply_markup=get_back_keyboard())
    
    elif query.data == 'rules':
        rules_text = (
            "📜 <b>Victorex Trader Grant Rules & Terms</b>\n\n"
            "1. We will ban you if you perform fraudulent activity.\n"
            "2. Account verification requires a ₦10,000 deposit.\n"
            "3. Minimum withdrawal amount is ₦50,000.\n"
            "4. Withdrawals take 24-72 hours to process due to bank procedures.\n"
            "5. Only one account per person.\n"
            "6. Respect all users and administrators.\n"
            "7. Transactions are secured with bank-level encryption.\n"
            "8. All earnings are subject to verification.\n\n"
            "Violation of these rules will result in account suspension."
        )
        await query.edit_message_text(rules_text, parse_mode='HTML', reply_markup=get_back_keyboard())

# Handle bank details for withdrawal
async def handle_bank_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    if 'awaiting_withdrawal' not in context.user_data or not context.user_data['awaiting_withdrawal']:
        return
    
    # Parse bank details
    try:
        parts = update.message.text.split(',')
        if len(parts) < 3:
            await update.message.reply_text(
                "Invalid format. Please use: Bank Name, Account Name, Account Number",
                reply_markup=get_back_keyboard()
            )
            return
        
        bank_name = parts[0].strip()
        account_name = parts[1].strip()
        account_number = parts[2].strip()
        
        # Validate account number (basic check)
        if not account_number.isdigit() or len(account_number) < 10:
            await update.message.reply_text(
                "Invalid account number. Please provide a valid account number.",
                reply_markup=get_back_keyboard()
            )
            return
        
        amount = context.user_data['withdrawal_amount']
        withdrawal_id = add_withdrawal_request(user_id, amount, bank_name, account_name, account_number)
        
        # Reset the flag
        context.user_data['awaiting_withdrawal'] = False
        
        await update.message.reply_text(
            f"✅ Your withdrawal request for ₦{amount} has been submitted!\n\n"
            f"Withdrawal ID: {withdrawal_id}\n"
            "Status: Pending Approval\n\n"
            "Your request will be processed within 24-72 hours. "
            "You will receive a notification once it's approved.",
            reply_markup=get_back_keyboard()
        )
        
        # Notify admin
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"🆕 New withdrawal request!\n\n"
                         f"User: {user_data['first_name']} {user_data['last_name']} (@{user_data['username']})\n"
                         f"Amount: ₦{amount}\n"
                         f"Bank: {bank_name}\n"
                         f"Account: {account_name} ({account_number})\n"
                         f"Withdrawal ID: {withdrawal_id}"
                )
            except Exception as e:
                print(f"Failed to notify admin {admin_id}: {e}")
                
    except Exception as e:
        await update.message.reply_text(
            "Error processing your bank details. Please try again.",
            reply_markup=get_back_keyboard()
        )

# Handle receipt photos for verification
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data:
        await update.message.reply_text("Please use /start first.")
        return
    
    if user_data['verified']:
        await update.message.reply_text("Your account is already verified.")
        return
    
    # Check if the photo is likely a receipt
    if update.message.caption and ("receipt" in update.message.caption.lower() or "deposit" in update.message.caption.lower()):
        # Get the largest available photo size
        photo = update.message.photo[-1]
        file_id = photo.file_id
        
        # Store verification request
        verification_id = add_verification_request(user_id, VERIFICATION_FEE, file_id)
        
        await update.message.reply_text(
            "✅ Thank you for submitting your receipt. "
            "Your verification request has been sent to our admin team for review. "
            "This usually takes up to 24 hours.\n\n"
            f"Verification ID: {verification_id}",
            reply_markup=get_back_keyboard()
        )
        
        # Notify admin
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"📋 New verification request from user {user_id} (@{user_data['username']})"
                )
                # Forward the photo to admin
                await context.bot.send_photo(
                    chat_id=admin_id,
                    photo=file_id,
                    caption=f"Verification receipt from user {user_id} - Verification ID: {verification_id}"
                )
            except Exception as e:
                print(f"Failed to notify admin {admin_id}: {e}")
    else:
        await update.message.reply_text(
            "Please send the transaction receipt.",
            reply_markup=get_back_keyboard()
        )

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Update {update} caused error {context.error}")

# Main function
def main():
    # Initialize database
    init_db()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CommandHandler("users", admin_users))
    application.add_handler(CommandHandler("broadcast", admin_broadcast))
    application.add_handler(CommandHandler("bann", admin_bann))
    application.add_handler(CommandHandler("unbann", admin_unbann))
    application.add_handler(CommandHandler("pay", admin_pay))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("pending_verifications", admin_pending_verifications))
    application.add_handler(CommandHandler("pending_withdrawals", admin_pending_withdrawals))
    application.add_handler(CommandHandler("approve_verification", admin_approve_verification))
    application.add_handler(CommandHandler("approve_withdrawal", admin_approve_withdrawal))
    application.add_handler(CommandHandler("reject_withdrawal", admin_reject_withdrawal))
    
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bank_details))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    application.add_error_handler(error_handler)
    
    # Start the bot
    print("Victorex Trader Grant Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
