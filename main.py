import re

import asyncio
from aiogram import Bot, types
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.types import PreCheckoutQuery, ContentType
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.exceptions import ChatNotFound, PaymentProviderInvalid, BotKicked

from deploy.config import TOKEN, PAYMENT_TOKEN, ADMIN_ID
from markup.markup import get_inline_buttons, get_invoices, get_currency_buttons, cancel_menu
from models.db_api import data_api
from markup import main_menu
from messages import MESSAGES
from state.state_invoice import CreateInvoice, UpdateInvoice, SendInvoiceState

bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())


async def collect_message_id(state: FSMContext, *args):
    data = await state.get_data()

    if data.get("msg_list"):
        msg_list = data.get("msg_list")
    else:
        msg_list = []
    msg_list += list(args)
    await state.update_data(msg_list=msg_list)


async def delete_message_id(state: FSMContext, chat_id, lasts_message_id: tuple,
                            last_message_text, reply_markup, time_pause=True):
    data = await state.get_data()
    if data.get("msg_list"):
        msg_list = list(set(data.get("msg_list")))
        for msg_id in msg_list:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        if time_pause:
            await asyncio.sleep(1)
        for last_id in lasts_message_id:
            await bot.delete_message(chat_id=chat_id, message_id=last_id)
        await state.reset_data()
        await state.finish()
        msg = await bot.send_message(text=last_message_text, chat_id=chat_id, reply_markup=reply_markup)
        await collect_message_id(state, msg.message_id)


@dp.message_handler(text="❌Отмена", state="*")
async def cancel_currency(message: types.Message, state: FSMContext):
    msg = await bot.send_message(message.chat.id, MESSAGES["state_reset"])

    await delete_message_id(state=state,
                            lasts_message_id=(msg.message_id, message.message_id),
                            reply_markup=main_menu,
                            chat_id=message.chat.id,
                            last_message_text=MESSAGES["work_continue"])


@dp.message_handler(commands=['start'])
async def start(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        await bot.send_message(message.chat.id, MESSAGES["start_error"])

    elif message.chat.id < 0:
        pass
    else:
        msg = await bot.send_message(message.chat.id, MESSAGES["start_ok"], reply_markup=main_menu,
                                     parse_mode="Markdown")
        await collect_message_id(state, message.message_id, msg.message_id)


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
    bot_obj = await bot.get_me()
    bot_id = bot_obj.id
    if message.left_chat_member.id == bot_id:
        data_api.remove_group_for_db(chat_id=message.chat.id)


@dp.message_handler(text="📈Отчет")
async def download_statistics(message: types.Message):
    if message.from_user.id not in ADMIN_ID:
        await bot.send_message(message.chat.id, MESSAGES["start_error"], reply_markup=main_menu)
    elif message.chat.id < 0:
        pass
    else:
        if data_api.render_excel_file(telegram_id=message.from_user.id):
            await bot.send_document(message.chat.id, open('report.xlsx', 'rb'))
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


# ----------------------------CREATE INVOICE----------------------------------

@dp.message_handler(text='➕Добавить оплату')
async def create_invoice(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        await bot.send_message(message.chat.id, MESSAGES["start_error"], reply_markup=main_menu)
    elif message.chat.id < 0:
        pass
    else:
        msg = await bot.send_message(message.chat.id, MESSAGES["invoice_title"], reply_markup=cancel_menu)
        await collect_message_id(state, message.message_id, msg.message_id)
        await CreateInvoice.first()


@dp.message_handler(state=(CreateInvoice.title_payment, UpdateInvoice.title_payment))
async def create_invoice_description(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        await bot.send_message(message.chat.id, MESSAGES["start_error"], reply_markup=main_menu)
    elif message.chat.id < 0:
        pass
    else:
        await state.update_data(title_payment=message.text)
        msg = await bot.send_message(message.chat.id, MESSAGES["invoice_description"], reply_markup=cancel_menu)

        await collect_message_id(state, message.message_id, msg.message_id)
        my_state = await state.get_state()
        if my_state == "CreateInvoice:title_payment":
            await CreateInvoice.next()
        elif my_state == "UpdateInvoice:title_payment":
            await UpdateInvoice.next()


@dp.message_handler(state=(CreateInvoice.description_payment, UpdateInvoice.description_payment))
async def create_invoice_description(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        await bot.send_message(message.chat.id, MESSAGES["start_error"], reply_markup=main_menu)
    elif message.chat.id < 0:
        pass
    else:
        await state.update_data(description_payment=message.text)
        msg = await bot.send_message(message.chat.id, MESSAGES["invoice_currency"], reply_markup=get_currency_buttons())
        await collect_message_id(state, message.message_id, msg.message_id)
        my_state = await state.get_state()
        if my_state == "CreateInvoice:description_payment":
            await CreateInvoice.next()
        elif my_state == "UpdateInvoice:description_payment":
            await UpdateInvoice.next()


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('currency'),
                           state=(CreateInvoice.currency, UpdateInvoice.currency))
async def create_invoice_currency(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_ID:
        await bot.send_message(callback_query.message.chat.id, MESSAGES["start_error"], reply_markup=main_menu)
    elif callback_query.message.chat.id < 0:
        pass
    else:

        await state.update_data(currency=callback_query.data[8:])
        msg = await bot.send_message(callback_query.message.chat.id, MESSAGES["invoice_price"],
                                     reply_markup=cancel_menu)

        await collect_message_id(state, msg.message_id, callback_query.message.message_id)
        my_state = await state.get_state()
        if my_state == "CreateInvoice:currency":
            await CreateInvoice.next()
        elif my_state == "UpdateInvoice:currency":
            await UpdateInvoice.next()


@dp.message_handler(state=(CreateInvoice.price, UpdateInvoice.price))
async def create_invoice_price(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        await bot.send_message(message.chat.id, MESSAGES["start_error"], reply_markup=main_menu)
    elif message.chat.id < 0:
        pass
    else:
        data = await state.get_data()
        msg_list = data.get("msg_list")
        msg_list.append(message.message_id)

        await state.update_data(price=message.text)

        data = await state.get_data()
        my_state = await state.get_state()
        if my_state == "CreateInvoice:price":
            if data_api.create_invoice(data):
                msg = await bot.send_message(message.chat.id, MESSAGES["invoice_finish"], reply_markup=main_menu)
            else:
                msg = await bot.send_message(message.chat.id, MESSAGES["invoice_input_error"],
                                             parse_mode="Markdown", reply_markup=main_menu)

        elif my_state == "UpdateInvoice:price":
            if data_api.update_invoice(data):
                msg = await bot.send_message(message.chat.id, MESSAGES["update_invoice_finish"], reply_markup=main_menu)
            else:
                msg = await bot.send_message(message.chat.id, MESSAGES["invoice_input_error"],
                                             parse_mode="Markdown", reply_markup=main_menu)

        await delete_message_id(state=state,
                                lasts_message_id=(msg.message_id, message.message_id),
                                reply_markup=main_menu,
                                chat_id=message.chat.id,
                                last_message_text=MESSAGES["work_continue"])


# ----------------------------INVOICE LIST----------------------------------

@dp.message_handler(text='💰Отправить оплату')
async def send_link_group(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        await bot.send_message(message.chat.id, MESSAGES["start_error"], reply_markup=main_menu)
    elif message.chat.id < 0:
        pass
    else:

        inline_buttons = get_invoices()
        if inline_buttons:

            msg = await bot.send_message(message.chat.id, MESSAGES["invoices_list"], reply_markup=inline_buttons,
                                         parse_mode="Markdown")
            # await collect_message_id(msg.message_id)
            await state.update_data(message_send_invoice_id=msg.message_id)
            await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

        else:
            await bot.send_message(message.chat.id, MESSAGES["not_group"])


# ----------------------------UPDATE INVOICE STARTING----------------------------------


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('edit'))
async def edit_invoice_start(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_ID:
        await bot.send_message(callback_query.message.chat.id, MESSAGES["start_error"])
    elif callback_query.message.chat.id < 0:
        pass
    else:
        invoice_id = callback_query.data[4:]
        await bot.send_message(callback_query.message.chat.id, MESSAGES["invoice_title"], reply_markup=cancel_menu)
        await state.finish()
        await UpdateInvoice.first()
        await state.update_data(invoice_id=invoice_id)


# ----------------------------SEND INVOICE-------------------------------------------


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('sent'))
async def send_link_group(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.from_user.id not in ADMIN_ID:
        await bot.send_message(callback_query.message.chat.id, MESSAGES["start_error"], reply_markup=main_menu)
    elif callback_query.message.chat.id < 0:
        pass
    else:
        invoice_id = callback_query.data[4:]
        if invoice_id == 'done':
            data = await state.get_data()
            message_send_invoice_id = data.get("message_send_invoice_id")
            await bot.answer_callback_query(callback_query.id, text=MESSAGES["operation_canceled"], show_alert=True)
            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=message_send_invoice_id)
            msg = await bot.send_message(chat_id=callback_query.message.chat.id, text=MESSAGES["operation_canceled"],
                                         reply_markup=main_menu)

            await delete_message_id(state=state,
                                    lasts_message_id=(msg.message_id,),
                                    reply_markup=main_menu,
                                    chat_id=callback_query.message.chat.id,
                                    last_message_text=MESSAGES["work_continue"],
                                    time_pause=False)

        else:
            inline_buttons = get_inline_buttons()
            if inline_buttons:
                data = await state.get_data()
                message_send_invoice_id = data.get("message_send_invoice_id")
                msg = await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                                  message_id=message_send_invoice_id, text='Список групп',
                                                  reply_markup=get_inline_buttons())

                await state.update_data(message_send_invoice_id=msg.message_id)
                await SendInvoiceState.first()
                await state.update_data(invoice_id=invoice_id)

            else:
                msg = await bot.send_message(callback_query.message.chat.id, MESSAGES["not_group"], reply_markup=main_menu,
                                       parse_mode="Markdown")

                await delete_message_id(state=state,
                                        lasts_message_id=(msg.message_id,),
                                        reply_markup=main_menu,
                                        chat_id=callback_query.message.chat.id,
                                        last_message_text=MESSAGES["work_continue"],
                                        time_pause=False)


@dp.callback_query_handler(lambda c: c.data and c.data.startswith('btn'), state=SendInvoiceState.invoice_id)
async def send_invoice(callback_query: types.CallbackQuery, state: FSMContext):
    system_message = ''
    if callback_query.from_user.id not in ADMIN_ID:
        await bot.send_message(callback_query.message.chat.id, MESSAGES["start_error"])
    elif callback_query.message.chat.id < 0:
        pass
    else:
        chat_id = callback_query.data[3:]
        if chat_id == 'done':
            data = await state.get_data()
            message_send_invoice_id = data.get("message_send_invoice_id")

            await bot.answer_callback_query(callback_query.id, text=MESSAGES["operation_canceled"], show_alert=True)
            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=message_send_invoice_id)
            msg = await bot.send_message(chat_id=callback_query.message.chat.id, text=MESSAGES["operation_canceled"],
                                         reply_markup=main_menu)

            await delete_message_id(state=state,
                                    lasts_message_id=(msg.message_id,),
                                    reply_markup=main_menu,
                                    chat_id=callback_query.message.chat.id,
                                    last_message_text=MESSAGES["work_continue"],
                                    time_pause=False)

        else:
            try:
                invoice_id = await state.get_data()
                invoice = data_api.get_invoice(invoice_id=invoice_id.get("invoice_id"))
                await bot.send_invoice(chat_id, title=invoice.title_payment,
                                       description=invoice.description_payment,
                                       provider_token=PAYMENT_TOKEN,
                                       currency=invoice.currency,
                                       payload=invoice.payload,
                                       prices=invoice.get_prices())

            except ChatNotFound:
                await bot.send_message(callback_query.message.chat.id, MESSAGES["no_access"])
            except PaymentProviderInvalid:
                if not re.search(r'\bpayment_provider_invalid\b', system_message):
                    system_message += '\n' * 2 + MESSAGES["payment_provider_invalid"]
            except BotKicked:
                if not re.search(r'\bbot_kicked\b', system_message):
                    system_message += '\n' * 2 + MESSAGES["bot_kicked"]

            if system_message:
                await bot.answer_callback_query(callback_query.id, text=system_message, show_alert=True)
                msg = await bot.send_message(callback_query.message.chat.id, system_message,
                                             reply_markup=main_menu,
                                             parse_mode="Markdown")

            else:
                await bot.answer_callback_query(callback_query.id, text=MESSAGES["payment_provider_valid"],
                                                show_alert=True)
                msg = await bot.send_message(callback_query.message.chat.id, MESSAGES["payment_provider_valid"],
                                             reply_markup=main_menu,
                                             parse_mode="Markdown")

            data = await state.get_data()
            message_send_invoice_id = data.get("message_send_invoice_id")
            await delete_message_id(state=state,
                                    lasts_message_id=(msg.message_id, message_send_invoice_id),
                                    reply_markup=main_menu,
                                    chat_id=callback_query.message.chat.id,
                                    last_message_text=MESSAGES["work_continue"],
                                    time_pause=False)


# ----------------------------SYSTEM PAYMENT TELEGRAM-------------------------------------------

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


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
