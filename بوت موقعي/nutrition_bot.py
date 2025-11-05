import logging
import random
import os
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
    ConversationHandler
)
from functools import wraps
import matplotlib.pyplot as plt
import io

# -----------------
# 1. الإعدادات والثوابت
# -----------------
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8499517383:AAEG_NXVseCEmOlAyGnDdTNBwReQfR62E00')
OWNER_ID = int(os.getenv('OWNER_ID', '123456789'))

CHANNEL_ID = '@fiteatmi'
CHANNEL_URL = 'https://t.me/fiteatmi'
FB_POST = 'https://www.facebook.com/share/17UZpM2KdG/'
SITE_URL = 'https://fiteatmi.netlify.app/'
WHATSAPP_URL = 'https://wa.me/201145237482'
PHOTO_URL = 'https://i.imgur.com/professional-fitness.jpg'

BOT_DESC = """
🤖 بوت FitEatMi الاحترافي (مع قاعدة بيانات بسيطة)
- أزرار سريعة للروابط الهامة
- حاسبة سعرات دقيقة وتفاعلية (مع حفظ النتائج)
- أسرار يومية + تذكير ماء تلقائي
- تتبع التقدم اليومي
"""

SECRETS = [
    "سر احترافي: اشرب ماء ليمون صباحاً لحرق دهون أسرع 🔥",
    "سر: تمارين HIIT 20 دقيقة = ساعة جيم 💥",
    "سر: بروتين 1.6ج/كجم وزن لعضلات قوية 🏋",
    "سر: نوم 8 ساعات يزود هرمون النمو 30% 😴"
]

HEIGHT, WEIGHT, AGE, GENDER, ACTIVITY = range(5)

# -----------------
# 2. قاعدة البيانات (SQLite)
# -----------------
def init_db():
    conn = sqlite3.connect('fiteatmi.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        height REAL,
        weight REAL,
        age INTEGER,
        gender TEXT,
        activity TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS progress (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        tdee REAL,
        bmi REAL,
        fat_percent REAL,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )''')
    conn.commit()
    conn.close()

def save_user_data(user_id, data):
    conn = sqlite3.connect('fiteatmi.db')
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO users (user_id, height, weight, age, gender, activity)
                 VALUES (?, ?, ?, ?, ?, ?)''', (user_id, data['height'], data['weight'], data['age'], data['gender'], data['activity']))
    conn.commit()
    conn.close()

def save_progress(user_id, tdee, bmi, fat_percent):
    conn = sqlite3.connect('fiteatmi.db')
    c = conn.cursor()
    date = datetime.now().strftime('%Y-%m-%d')
    c.execute('INSERT INTO progress (user_id, date, tdee, bmi, fat_percent) VALUES (?, ?, ?, ?, ?)',
              (user_id, date, tdee, bmi, fat_percent))
    conn.commit()
    conn.close()

def get_progress(user_id):
    conn = sqlite3.connect('fiteatmi.db')
    c = conn.cursor()
    c.execute('SELECT date, tdee, bmi FROM progress WHERE user_id = ? ORDER BY date DESC LIMIT 7', (user_id,))
    data = c.fetchall()
    conn.close()
    return data

# -----------------
# 3. الدوال المساعدة
# -----------------
def restrict_to_subscribers(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        try:
            member = await context.bot.get_chat_member(CHANNEL_ID, user.id)
            if member.status in ['member', 'administrator', 'creator']:
                return await func(update, context)
            else:
                raise Exception("Not subscribed")
        except Exception as e:
            logger.warning(f"Subscription check failed for user {user.id}: {e}")
            keyboard = [
                [InlineKeyboardButton("انضم للقناة 🚀", url=CHANNEL_URL)],
                [InlineKeyboardButton("تحقق ✅", callback_data='check')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if update.message:
                await update.message.reply_photo(PHOTO_URL, caption=f'📛 اشترك أولاً في {CHANNEL_ID}!\n{BOT_DESC}', reply_markup=reply_markup)
            elif update.callback_query:
                await update.callback_query.edit_message_caption(caption=f'📛 اشترك أولاً في {CHANNEL_ID}!\n{BOT_DESC}', reply_markup=reply_markup)
    return wrapper

# -----------------
# 4. دوال القائمة والأزرار
# -----------------
async def main_menu(update_object, context):
    menu_message = '🔥 القائمة الاحترافية!\n' + BOT_DESC
    keyboard = [
        [InlineKeyboardButton("فيسبوك 📘", url=FB_POST), InlineKeyboardButton("الموقع 🌟", url=SITE_URL)],
        [InlineKeyboardButton("واتساب 📱", url=WHATSAPP_URL), InlineKeyboardButton("القناة 🚀", url=CHANNEL_URL)],
        [InlineKeyboardButton("حاسبة سعرات 🧮", callback_data='calc_guide')],
        [InlineKeyboardButton("أسرار اليوم 🔥", callback_data='secrets')],
        [InlineKeyboardButton("تتبع التقدم 📊", callback_data='progress')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    target = update_object.message if hasattr(update_object, 'message') else update_object
    await target.reply_photo(PHOTO_URL, caption=f'أهلاً {target.from_user.first_name}! 👋\n' + menu_message, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == 'check':
        await restrict_to_subscribers(main_menu)(query, context)
    elif data == 'secrets':
        secret = random.choice(SECRETS)
        keyboard = [[InlineKeyboardButton("رجوع للقائمة 🚀", callback_data='menu')]]
        await query.edit_message_caption(f'🔥 سر احترافي: {secret}\n{BOT_DESC}', reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif data == 'calc_guide':
        keyboard = [
            [InlineKeyboardButton("بدء الحاسبة 🧮", callback_data='start_interactive_calc')],
            [InlineKeyboardButton("رجوع 🚀", callback_data='menu')]
        ]
        await query.edit_message_caption('🧮 حاسبة سعرات FitEatMi تعمل بشكل تفاعلي! اضغط *بدء الحاسبة* أو أرسل الأمر:\n/calc', reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    elif data == 'start_interactive_calc':
        await query.edit_message_caption('👇 اضغط */calc* لبدء الحاسبة التفاعلية! 👇', reply_markup=None, parse_mode='Markdown')
    elif data == 'progress':
        await show_progress(query, context)
    elif data == 'menu':
        await main_menu(query, context)

async def show_progress(update_object, context):
    user_id = update_object.from_user.id
    data = get_progress(user_id)
    if not data:
        await update_object.edit_message_caption('📊 لا توجد بيانات تقدم بعد. ابدأ بحاسبة السعرات أولاً!', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🚀", callback_data='menu')]]))
        return
    # إنشاء رسم بياني بسيط
    dates = [row[0] for row in data]
    tdees = [row[1] for row in data]
    plt.plot(dates, tdees)
    plt.title('تقدم TDEE')
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    await update_object.message.reply_photo(buf, caption='📊 رسم بياني لتقدمك في TDEE (آخر 7 أيام)', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🚀", callback_data='menu')]]))

# -----------------
# 5. دوال التذكير والحاسبة (محدثة)
# -----------------
async def water_reminder(context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("القائمة الاحترافية 🚀", callback_data='menu')]]
    await context.bot.send_message(context.job.chat_id, '🥤 *تذكير FitEatMi:* حان وقت شرب الماء!', reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

@restrict_to_subscribers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await main_menu(update.message, context)
    job_name = f'water_reminder_{update.effective_chat.id}'
    if not context.job_queue.get_jobs_by_name(job_name):
        context.job_queue.run_repeating(water_reminder, interval=timedelta(minutes=30), first=10, chat_id=update.effective_chat.id, name=job_name)

# في calculate_results، أضف حفظ البيانات:
# بعد حساب tdee, bmi, fat_percent:
# save_user_data(update.effective_user.id, data)
# save_progress(update.effective_user.id, tdee, bmi, fat_percent)

# -----------------
# 6. ال