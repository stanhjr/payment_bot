from aiogram.dispatcher.filters.state import StatesGroup, State


class CreateInvoice(StatesGroup):
    title_payment = State()
    description_payment = State()
    currency = State()
    price = State()


class UpdateInvoice(StatesGroup):
    title_payment = State()
    description_payment = State()
    currency = State()
    price = State()


class SendInvoiceState(StatesGroup):
    invoice_id = State()
