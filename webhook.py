import os
import logging
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
import stripe
import httpx
from enhance import enhance_image
from db import update_payment_status, get_payment

load_dotenv()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_ENDPOINT_SECRET = os.getenv("STRIPE_ENDPOINT_SECRET")
BOT_TOKEN = os.getenv("BOT_TOKEN")

stripe.api_key = STRIPE_SECRET_KEY
app = FastAPI()
logging.basicConfig(level=logging.INFO)

async def get_telegram_file_url(file_id: str, bot_token: str) -> str:
    async with httpx.AsyncClient() as client:
        url = f"https://api.telegram.org/bot{bot_token}/getFile"
        response = await client.post(url, json={"file_id": file_id})
        if response.status_code != 200:
            return None
        data = response.json()
        if not data.get("ok"):
            return None
        file_path = data["result"]["file_path"]
        return f"https://api.telegram.org/file/bot{bot_token}/{file_path}"

async def send_photo_to_user(chat_id: int, photo_url: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "photo": photo_url})

async def send_message_to_user(chat_id: int, text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "text": text})

@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_ENDPOINT_SECRET)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        session_id = session["id"]
        metadata = session.get("metadata", {})
        user_id = metadata.get("user_id")
        file_id = metadata.get("file_id")

        if not user_id or not file_id:
            logging.error("Missing user_id or file_id in metadata")
            return {"status": "error", "message": "Missing metadata"}

        update_payment_status(session_id, "completed")
        payment_info = get_payment(session_id)
        if payment_info:
            user_id, file_id, _ = payment_info

        file_url = await get_telegram_file_url(file_id, BOT_TOKEN)
        if not file_url:
            logging.error("Could not get file URL")
            await send_message_to_user(user_id, "Не удалось получить ваше фото. Попробуйте еще раз.")
            return {"status": "error", "message": "File not found"}

        result_url = await enhance_image(file_url, scale=4)
        if result_url:
            await send_photo_to_user(user_id, result_url)
            await send_message_to_user(user_id, "Готово! Вот твоё улучшенное фото (Supreme качество).")
        else:
            await send_message_to_user(user_id, "Извините, не удалось улучшить фото. Попробуйте позже.")

    return {"status": "success"}