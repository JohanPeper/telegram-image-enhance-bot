# Telegram бот для улучшения фото с оплатой через Stripe

Бот принимает фото, бесплатно улучшает через Replicate (модель real-esrgan, scale 2), а также предлагает платное улучшение Supreme (scale 4) за $1 через Stripe Checkout.

## Требования

- Python 3.10+
- Токен Telegram бота (через @BotFather)
- API ключ Replicate (https://replicate.com)
- Stripe аккаунт (тестовый режим)

## Установка

1. Клонируйте репозиторий и перейдите в папку проекта.
2. Создайте виртуальное окружение: `python -m venv venv`
3. Активируйте: `venv\Scripts\activate` (Windows) или `source venv/bin/activate` (Linux/Mac)
4. Установите зависимости: `pip install -r requirements.txt`
5. Создайте файл `.env` и заполните как в примере.

## Получение ключей

### Telegram
- Напишите @BotFather, создайте бота, получите `BOT_TOKEN`.

### Replicate
- Зарегистрируйтесь на replicate.com, в разделе Account получите API токен.

### Stripe
- Зарегистрируйтесь на stripe.com, переключитесь в тестовый режим.
- В разделе Developers → API keys получите `STRIPE_SECRET_KEY` (sk_test_...).
- Создайте webhook endpoint: `https://ваш_домен/webhook`. Для локальной разработки используйте `stripe listen --forward-to localhost:8000/webhook`.
- Скопируйте подписной ключ (whsec_...) в `STRIPE_ENDPOINT_SECRET`.

## Запуск

1. Запустите вебхук-сервер:
   ```bash
   uvicorn webhook:app --host 0.0.0.0 --port 8000