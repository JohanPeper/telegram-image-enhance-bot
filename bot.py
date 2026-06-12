# bot.py
import os
import logging
import asyncio
import httpx
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, PreCheckoutQueryHandler
from db import init_db, save_payment
from enhance import enhance_image

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
if not BOT_TOKEN or not REPLICATE_API_TOKEN:
    raise ValueError("Missing BOT_TOKEN or REPLICATE_API_TOKEN in .env")

init_db()

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
        return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{data['result']['file_path']}"

async def start(update: Update, context):
    await update.message.reply_text(
        "Привет! Отправь фото, я улучшу его.\n"
        "🆓 Бесплатно (scale 2)\n"
        "⭐ Supreme за 50 Telegram Stars (scale 4)"
    )

async def handle_photo(update: Update, context):
    photo = update.message.photo[-1]
    context.user_data['last_photo'] = photo.file_id
    keyboard = [
        [InlineKeyboardButton("🆓 Бесплатно", callback_data="free")],
        [InlineKeyboardButton("⭐ Supreme за 50 Stars", callback_data="supreme")]
    ]
    await update.message.reply_text(
        "Выбери вариант:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    file_id = context.user_data.get('last_photo')
    if not file_id:
        await query.edit_message_text("Сначала отправь фото.")
        return

    if query.data == "free":
        await query.edit_message_text("🔄 Улучшаю бесплатно...")
        file_url = await get_telegram_file_url(file_id)
        if not file_url:
            await query.edit_message_text("Ошибка получения файла.")
            return
        result = await enhance_image(file_url, scale=2)
        if result:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=result)
            await query.edit_message_text("Готово! Бесплатная версия.")
        else:
            await query.edit_message_text("Ошибка улучшения. Попробуй позже.")

    elif query.data == "supreme":
        context.user_data['supreme_file_id'] = file_id
        await context.bot.send_invoice(
            chat_id=update.effective_chat.id,
            title="Supreme улучшение",
            description="Высокое разрешение (scale 4)",
            payload="supreme_upgrade",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice("⭐ Улучшение", 50)],
            start_parameter="supreme"
        )

async def pre_checkout(update: Update, context):
    query = update.pre_checkout_query
    await query.answer(ok=True)
    file_id = context.user_data.get('supreme_file_id', '')
    save_payment(update.effective_user.id, 50, 'pending', file_id)

async def successful_payment(update: Update, context):
    file_id = context.user_data.get('supreme_file_id')
    if not file_id:
        await update.message.reply_text("Ошибка: фото не найдено.")
        return
    await update.message.reply_text("✅ Оплачено! Улучшаю Supreme...")
    save_payment(update.effective_user.id, 50, 'completed', file_id)
    file_url = await get_telegram_file_url(file_id)
    if not file_url:
        await update.message.reply_text("Не удалось получить фото.")
        return
    result = await enhance_image(file_url, scale=4)
    if result:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=result)
        await update.message.reply_text("Готово! Твоё улучшенное фото.")
    else:
        await update.message.reply_text("Ошибка улучшения. Попробуй позже.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.run_polling()

if __name__ == "__main__":
    main()