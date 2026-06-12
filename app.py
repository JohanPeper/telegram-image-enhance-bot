import os
import logging
from flask import Flask, request, jsonify
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Dispatcher, CommandHandler, CallbackQueryHandler, PreCheckoutQueryHandler, MessageHandler, filters
from dotenv import load_dotenv
import httpx
from db import init_db, save_payment
from enhance import enhance_image   # берём вашу функцию улучшения

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set in .env")
if not REPLICATE_API_TOKEN:
    raise ValueError("REPLICATE_API_TOKEN not set in .env")

bot = Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

init_db()  # создаст таблицы

async def get_telegram_file_url(file_id: str):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getFile",
            json={"file_id": file_id}
        )
        data = resp.json()
        if not data.get("ok"):
            logging.error(f"Telegram API error: {data}")
            return None
        file_path = data["result"]["file_path"]
        return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

# ---------- ОБРАБОТЧИКИ ----------
async def start(update: Update, context):
    await update.message.reply_text(
        "Привет! Отправь мне фото, и я улучшу его.\n"
        "Доступно бесплатное улучшение (scale 2) и платное Supreme за 50 Telegram Stars (scale 4)."
    )

async def handle_photo(update: Update, context):
    photo = update.message.photo[-1]
    context.user_data['last_photo'] = photo.file_id
    keyboard = [
        [InlineKeyboardButton("🆓 Бесплатно", callback_data="free")],
        [InlineKeyboardButton("⭐ Supreme за 50 Stars", callback_data="supreme")]
    ]
    await update.message.reply_text(
        "Выбери вариант улучшения:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    file_id = context.user_data.get('last_photo')
    if not file_id:
        await query.edit_message_text("Ошибка: сначала отправьте фото.")
        return

    if query.data == "free":
        await query.edit_message_text("🔄 Улучшаю бесплатно (scale 2)...")
        file_url = await get_telegram_file_url(file_id)
        if not file_url:
            await query.edit_message_text("Не удалось получить файл.")
            return
        result_url = await enhance_image(file_url, scale=2)
        if result_url:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=result_url)
            await query.edit_message_text("Вот ваше улучшенное фото (бесплатная версия).")
        else:
            await query.edit_message_text("Ошибка при улучшении. Попробуйте позже.")

    elif query.data == "supreme":
        context.user_data['supreme_file_id'] = file_id
        await context.bot.send_invoice(
            chat_id=update.effective_chat.id,
            title="Supreme улучшение фото",
            description="Улучшение в высоком разрешении (scale 4)",
            payload="supreme_upgrade",
            provider_token="",            # обязательно пустая строка
            currency="XTR",               # Telegram Stars
            prices=[LabeledPrice("⭐ Улучшение", 50)],
            start_parameter="supreme"
        )

async def pre_checkout(update: Update, context):
    query = update.pre_checkout_query
    # Можно проверить payload, но для простоты сразу одобряем
    await query.answer(ok=True)
    # Сохраняем в БД со статусом pending (file_id будет добавлен позже)
    file_id = context.user_data.get('supreme_file_id', '')
    save_payment(update.effective_user.id, 50, 'pending', file_id)

async def successful_payment(update: Update, context):
    file_id = context.user_data.get('supreme_file_id')
    if not file_id:
        await update.message.reply_text("Ошибка: не найден идентификатор фото.")
        return
    await update.message.reply_text("✅ Оплата получена! Улучшаю фото Supreme...")
    # Обновляем статус платежа
    save_payment(update.effective_user.id, 50, 'completed', file_id)
    file_url = await get_telegram_file_url(file_id)
    if not file_url:
        await update.message.reply_text("Не удалось получить ваше фото.")
        return
    result_url = await enhance_image(file_url, scale=4)
    if result_url:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=result_url)
        await update.message.reply_text("Готово! Ваше улучшенное фото Supreme.")
    else:
        await update.message.reply_text("Ошибка при улучшении. Попробуйте позже.")

# Регистрация обработчиков
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(filters.PHOTO, handle_photo))
dispatcher.add_handler(CallbackQueryHandler(button_callback))
dispatcher.add_handler(PreCheckoutQueryHandler(pre_checkout))
dispatcher.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

# ---------- FLASK ПРИЛОЖЕНИЕ ----------
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
async def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        await dispatcher.process_update(update)
        return jsonify({"status": "ok"})
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    domain = os.getenv("DOMAIN")
    if not domain:
        return "DOMAIN not set in .env. Example: DOMAIN=yourusername.pythonanywhere.com"
    webhook_url = f"https://{domain}/webhook"
    try:
        bot.set_webhook(webhook_url)
        return f"Webhook successfully set to {webhook_url}"
    except Exception as e:
        return f"Error setting webhook: {e}"

@app.route('/', methods=['GET'])
def index():
    return "Bot is running. Use /set_webhook to configure."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)