from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from models.db_api import data_api


def get_inline_buttons():
    inline_kb_full = InlineKeyboardMarkup(row_width=1)
    group_list = data_api.get_group_by_inline()
    if group_list:
        for title, chat_id in group_list:
            callback_data = 'btn' + str(chat_id)
            inline_kb_full.add(InlineKeyboardButton(title, callback_data=callback_data))
    inline_kb_full.add(InlineKeyboardButton('❌Отмена', callback_data="btndone"))
    return inline_kb_full


def get_invoices():
    inline_kb_full = InlineKeyboardMarkup(row_width=2)
    invoices_list = data_api.get_invoice_by_inline()
    if invoices_list:
        for title, price, invoice_id in invoices_list:
            callback_data_send_invoice = 'sent' + str(invoice_id)
            callback_data_edit_invoice = 'edit' + str(invoice_id)
            title = title + ' ' + str(price / 100)
            inline_kb_full.add(InlineKeyboardButton(title, callback_data=callback_data_send_invoice),
                               InlineKeyboardButton('✏Изменить', callback_data=callback_data_edit_invoice))
        inline_kb_full.add(InlineKeyboardButton('❌Отмена', callback_data="sentdone"))
        return inline_kb_full

    else:
        return False


def get_currency_buttons():
    inline_kb_full = InlineKeyboardMarkup(row_width=2)
    inline_kb_full.add(InlineKeyboardButton('UAH', callback_data="currencyUAH"),
                       InlineKeyboardButton('USD', callback_data="currencyUSD"))
    return inline_kb_full


get_my_groups_button = KeyboardButton("👩‍👧‍👧Все группы")
send_invoice_button = KeyboardButton("💰Отправить оплату")
download_button = KeyboardButton("📈Отчет")
create_invoice_button = KeyboardButton("➕Добавить оплату")
cancel_button = KeyboardButton("❌Отмена")

main_menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).add(download_button)
main_menu.add(send_invoice_button, create_invoice_button)

cancel_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(cancel_button)


