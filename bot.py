import os
import logging
import httpx
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import stripe
from enhance import enhance_image
from db import init_db, add_payment

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
stripe.api_key = STRIPE_SECRET_KEY

logging.basicConfig(level=logging.INFO)
init_db()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для улучшения фото.\n"
        "Отправь мне фото, и я предложу бесплатное улучшение или платное Supreme (высокое разрешение).\n"
        "Платное улучшение стоит $1 (тестовый режим)."
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file_id = photo.file_id
    context.user_data['last_photo'] = file_id

    keyboard = [
        [InlineKeyboardButton("🆓 Бесплатное улучшение", callback_data="free_enhance")],
        [InlineKeyboardButton("💎 Supreme улучшение (платно)", callback_data="supreme_enhance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери вариант улучшения:", reply_markup=reply_markup)

async def get_telegram_file_url(file_id: str, bot_token: str) -> str:
    """Получает прямую ссылку на файл Telegram через API."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"https://api.telegram.org/bot{bot_token}/getFile",
                json={"file_id": file_id}
            )
            data = resp.json()
            if not data.get("ok"):
                logging.error(f"Telegram API error: {data}")
                return None
            file_path = data["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
            logging.info(f"Generated file URL: {file_url}")
            return file_url
        except Exception as e:
            logging.error(f"Error getting file URL: {e}")
            return None

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "free_enhance":
        file_id = context.user_data.get('last_photo')
        if not file_id:
            await query.edit_message_text("Сначала отправьте фото.")
            return
        await query.edit_message_text("🔄 Улучшаю фото (бесплатно)...")
        file_url = await get_telegram_file_url(file_id, BOT_TOKEN)
        if not file_url:
            await query.edit_message_text("Не удалось получить фото. Попробуйте еще раз.")
            return
        result_url = await enhance_image(file_url, scale=2)
        if result_url:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=result_url)
            await query.edit_message_text("Вот ваше улучшенное фото (бесплатная версия).")
        else:
            await query.edit_message_text("Ошибка при улучшении. Попробуйте позже.")

    elif query.data == "supreme_enhance":
        file_id = context.user_data.get('last_photo')
        if not file_id:
            await query.edit_message_text("Сначала отправьте фото.")
            return
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Supreme улучшение фото',
                            'description': 'Высокое разрешение (scale=4)',
                        },
                        'unit_amount': 100,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url='https://example.com/success',
                cancel_url='https://example.com/cancel',
                metadata={
                    'user_id': update.effective_user.id,
                    'file_id': file_id
                }
            )
            add_payment(session.id, update.effective_user.id, file_id, 'pending')
            keyboard = [[InlineKeyboardButton("💳 Оплатить $1", url=session.url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "Для улучшения Supreme необходимо оплатить $1.\n"
                "После оплаты вы получите улучшенное фото в этом чате.\n"
                "Нажмите кнопку ниже для оплаты:",
                reply_markup=reply_markup
            )
        except Exception as e:
            logging.error(f"Stripe error: {e}")
            await query.edit_message_text("Ошибка при создании платежной сессии. Попробуйте позже.")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.run_polling()

if __name__ == "__main__":
    main()