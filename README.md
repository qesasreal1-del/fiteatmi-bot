import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from functools import wraps

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = '8586726423:AAF5d9SeIn2P3x26yMw22NJyYOdFC_w4BwY'

CHANNEL_ID = '@fiteatmi'
CHANNEL_URL = 'https://t.me/fiteatmi'
WEBSITE1_URL = 'https://fitdayet1.netlify.app/'
CHANNEL_DESC = 'مجتمع FitEatMi: نصائح لياقة، خطط تدريب، وجبات صحية! 💪🥗'

# ديكوراتور للتحقق من الانضمام
def restrict_to_subscribers(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        try:
            member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
                return await func(update, context)  # مشترك
            else:
                raise Exception("Not subscribed")
        except:
            # رسالة مع زر تحقق وانضمام
            keyboard = [
                [InlineKeyboardButton("انضم للقناة 🚀", url=CHANNEL_URL)],
                [InlineKeyboardButton("تحقق من الانضمام ✅", callback_data='check_subscription')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                'عذراً! 📛 عشان تستخدم البوت، لازم تشترك في القناة أولاً.\n'
                'اضغط "انضم للقناة"، ثم "تحقق من الانضمام" بعد ما تنضم! 💪',
                reply_markup=reply_markup
            )
    return wrapper

# معالج الزر (Callback للتحقق)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'check_subscription':
        user_id = query.from_user.id
        try:
            member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
            if member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
                await query.edit_message_text('مبروك! ✅ أنت مشترك الآن. ابدأ بـ /start')
            else:
                await query.edit_message_text('لسه مش مشترك! 📛 اضغط "انضم للقناة" وارجع تحقق تاني.')
        except:
            await query.edit_message_text('خطأ في التحقق! حاول تاني أو كلمني بعد الاشتراك.')

# /start
@restrict_to_subscribers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("انضم للقناة 🚀", url=CHANNEL_URL)],
        [InlineKeyboardButton("زور الموقع 🌟", url=WEBSITE1_URL)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = f"مرحباً! 👋💪\n{CHANNEL_DESC}\nخطط تدريبية + وصفات صحية جاهزة!"
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# /join
@restrict_to_subscribers
async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("انضم!", url=CHANNEL_URL)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('مشترك بالفعل! 🎉', reply_markup=reply_markup)

# /workouts
@restrict_to_subscribers
async def workouts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("شوف الخطط", url=WEBSITE1_URL)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "خططنا:\n- تضخيم PPL (6 أيام) 📈\n- تخسيس (4 أيام) 🔥\n- منزلي (3 أيام) 🏠"
    await update.message.reply_text(text, reply_markup=reply_markup)

# /meals
@restrict_to_subscribers
async def meals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("الوصفات", url=f'{WEBSITE1_URL}meals')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('وجبات صحية لأهدافك! 🥦🍗', reply_markup=reply_markup)

# رد عام
@restrict_to_subscribers
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("القناة", url=CHANNEL_URL)],
        [InlineKeyboardButton("الموقع", url=WEBSITE1_URL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('نصائح حصرية! استكشف دلوقتي 💥', reply_markup=reply_markup)

# /check - تحقق يدوي
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # محاكاة callback للتحقق
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
            await update.message.reply_text('مبروك! ✅ أنت مشترك. ابدأ بـ /start')
        else:
            keyboard = [[InlineKeyboardButton("تحقق تاني ✅", callback_data='check_subscription')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text('لسه مش مشترك! 📛 انضم واضغط الزر.', reply_markup=reply_markup)
    except:
        await update.message.reply_text('خطأ! حاول /check تاني.')

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    
    # أوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CommandHandler("workouts", workouts))
    application.add_handler(CommandHandler("meals", meals))
    application.add_handler(CommandHandler("check", check))
    
    # ردود نصية
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    # معالج الأزرار
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("البوت شغال مع تحقق انضمام قوي...")
    application.run_polling()

if __name__ == '__main__':
    main()
