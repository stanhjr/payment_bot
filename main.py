import re

from aiogram import Bot, types
from aiogram import Dispatcher
from aiogram.types import PreCheckoutQuery, ContentType
from aiogram.utils import executor
from aiogram.utils.exceptions import ChatNotFound, PaymentProviderInvalid, BotKicked
from aiogram.utils.executor import start_webhook

from deploy.config import TOKEN, WEBHOOK_URL, WEBHOOK_PATH, WEBAPP_HOST, WEBAPP_PORT, PAYMENT_TOKEN, PRICES, ADMIN_ID, \
    TITLE_PAYMENT, DESCRIPTION_PAYMENT, PAYLOAD
from models.db_api import data_api
from markup import main_menu
from messages import MESSAGES

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)


@dp.message_handler(content_types=[ContentType.NEW_CHAT_MEMBERS])
async def new_members_handler(message: types.Message):
    bot_obj = await bot.get_me()
    bot_id = bot_obj.id
    new_member = message.new_chat_members[0]
    if new_member.id != bot_id:
        data_api.set_user(telegram_id=new_member.id,
                          last_name=new_member.last_name,
                          first_name=new_member.first_name,
                          username=new_member.username,
                          chat_id=message.chat.id)
    else:
        data_api.set_group(chat_id=message.chat.id, title=message.chat.title)


@dp.message_handler(content_types=[ContentType.LEFT_CHAT_MEMBER])
async def new_members_handler(message: types.Message):
    print(message)
    bot_obj = await bot.get_me()
    bot_id = bot_obj.id
    if message.left_chat_member.id == bot_id:
        data_api.remove_group_for_db(chat_id=message.chat.id)


@dp.message_handler(commands=['start'])
async def start(message: types.Message):

    if message.from_user.id not in ADMIN_ID:
        await bot.send_message(message.chat.id, MESSAGES["start_error"])

    elif message.chat.id < 0:
        pass
    else:
        await bot.send_message(message.chat.id, MESSAGES["start_ok"], reply_markup=main_menu, parse_mode="Markdown")


@dp.message_handler(commands=['download_statistics'])
async def download_statistics(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        await bot.send_message(message.chat.id, MESSAGES["download_error"], reply_markup=main_menu)
    elif message.chat.id < 0:
        pass
    else:
        if data_api.render_excel_file(telegram_id=message.from_user.id):
            await bot.send_document(message.chat.id, open('report.xlsx', 'rb'))


@dp.message_handler(commands=['send_invoice'])
async def send_invoice_for_all_groups(message: types.Message):
    system_message = ''
    if message.from_user.id not in ADMIN_ID:
        await bot.send_message(message.chat.id, MESSAGES["start_error"])
    elif message.chat.id < 0:
        pass
    else:
        list_group_id = data_api.get_group_chat_id()
        if list_group_id:
            for chat_id in list_group_id:
                try:
                    await bot.send_invoice(chat_id, title="Оплата",
                                           description="Описание оплаты",
                                           provider_token=PAYMENT_TOKEN,
                                           currency='UAH',
                                           payload="Оплата курсов",
                                           prices=PRICES)
                except ChatNotFound:
                    await bot.send_message(message.chat.id, MESSAGES["no_access"])
                except PaymentProviderInvalid:
                    if not re.search(r'\bpayment_provider_invalid\b', system_message):
                        system_message += '\n' * 2 + MESSAGES["payment_provider_invalid"]
                    continue
                except BotKicked:
                    if not re.search(r'\bbot_kicked\b', system_message):
                        system_message += '\n' * 2 + MESSAGES["bot_kicked"]
                    continue
            if system_message:
                await bot.send_message(message.chat.id, system_message)
        else:
            await bot.send_message(message.from_user.id, MESSAGES["not_group"])


@dp.message_handler(commands=['get_my_groups'])
async def get_my_groups(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        await bot.send_message(message.chat.id, MESSAGES["start_error"])
    elif message.chat.id < 0:
        pass
    else:
        answer = "Список групп"
        for title in data_api.get_group_title():
            answer += f'\n{title}'
        if answer == "Список групп":
            answer = "Список групп пока пуст"
        await bot.send_message(message.chat.id, answer, reply_markup=main_menu, parse_mode="Markdown")


@dp.pre_checkout_query_handler(lambda q: True)
async def checkout_process(pre_checkout_query: PreCheckoutQuery):
    if data_api.payment_time_limit(telegram_id=pre_checkout_query.from_user.id):
        await bot.answer_pre_checkout_query(pre_checkout_query.id, True)


@dp.message_handler(content_types=ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: types.Message):

    if data_api.payment_fixation(telegram_id=message.from_user.id,
                                 first_name=message.from_user.first_name,
                                 last_name=message.from_user.last_name,
                                 username=message.from_user.username,
                                 chat_id=message.chat.id):
        await bot.send_message(message.chat.id, MESSAGES.get("payment_ok"))


@dp.message_handler(commands="inline_url")
async def cmd_inline_url(message: types.Message):
    await bot.send_invoice(message.chat.id, title=TITLE_PAYMENT,
                           description=DESCRIPTION_PAYMENT ,
                           provider_token=PAYMENT_TOKEN,
                           currency='UAH',
                           payload=PAYLOAD,
                           prices=PRICES)


async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)


async def on_shutdown(dp):
    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
    # start_webhook(
    #     dispatcher=dp,
    #     webhook_path=WEBHOOK_PATH,
    #     on_startup=on_startup,
    #     on_shutdown=on_shutdown,
    #     skip_updates=True,
    #     host=WEBAPP_HOST,
    #     port=WEBAPP_PORT,
    # )
