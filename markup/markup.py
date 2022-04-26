from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from models.db_api import data_api


def get_inline_buttons():
    list_button = []
    group_list = data_api.get_group_by_inline()
    if group_list:
        for title, chat_id in group_list:
            _tuple = []
            inline_kb_full = InlineKeyboardMarkup(row_width=1)
            callback_data = 'btn' + str(chat_id)
            inline_kb_full.add(InlineKeyboardButton(title, callback_data=callback_data))
            _tuple.append(title)
            _tuple.append(inline_kb_full)
            _tuple = tuple(_tuple)
            list_button.append(_tuple)

    return list_button


get_my_groups_button = KeyboardButton("/get_my_groups")
send_invoice_button = KeyboardButton("/send_invoice")
download_button = KeyboardButton("/download_statistics")
main_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(download_button, send_invoice_button, get_my_groups_button)



