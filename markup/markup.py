from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

get_my_groups_button = KeyboardButton("/get_my_groups")
send_invoice_button = KeyboardButton("/send_invoice")
download_button = KeyboardButton("/download_statistics")
main_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(download_button, send_invoice_button, get_my_groups_button)
