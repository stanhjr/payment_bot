import os

TOKEN = '5134733454:AAFPQ9DbCYc7PlgVE8P_bwZOqGpPyi0Ty1k'
WEBHOOK_HOST = 'https://2ce6-88-155-2-99.ngrok.io'
WEBHOOK_PATH = f'/webhook/{TOKEN}'
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
WEBAPP_HOST = '0.0.0.0'
WEBAPP_PORT = os.getenv('PORT', default=5000)


host = "localhost"
DATABASE_URL = f'postgresql://stan:stan@{host}:5432/bot_test'
PRICES = [{"label": "UAH", "amount": 1000}]

ADMIN_ID = [589380091, 436985071, 336609833]
TIME_LIMIT_FOR_RECURRING_PAYMENTS = 30 * 24 * 60 * 60


# Payment part
PAYMENT_TOKEN = '632593626:TEST:sandbox_i2752149886'
TITLE_PAYMENT = "Оплата"
DESCRIPTION_PAYMENT = "Описание оплаты"
PAYLOAD = "Оплата курсов"