# Telegram бот для улучшения фото с оплатой Telegram Stars

Бот увеличивает качество фото через Replicate (GFPGAN).  
Бесплатно — scale 2, платно — scale 4 за 50 Stars.

## Запуск локально

1. Клонируйте репозиторий
2. Создайте виртуальное окружение и установите зависимости:  
   `pip install -r requirements.txt`
3. Создайте файл `.env` с `BOT_TOKEN` и `REPLICATE_API_TOKEN`
4. Запустите: `python bot.py`

## Деплой на Render.com

1. Загрузите код на GitHub.
2. На Render создайте **Background Worker**, подключите репозиторий.
3. Добавьте переменные окружения: `BOT_TOKEN`, `REPLICATE_API_TOKEN`.
4. Нажмите **Create**. Бот запустится и будет работать.

## Важно

- Для платных улучшений нужны **Telegram Stars**. Убедитесь, что бот создан после 1 июня 2024 и у него включены Stars (`/setstars` в BotFather).
- Replicate может требовать оплаты после исчерпания бесплатных кредитов. Используйте модель `tencentarc/gfpgan`.

## Лицензия

MIT