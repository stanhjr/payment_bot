import time
from functools import wraps

import pandas
from pandas import DataFrame
from sqlalchemy.sql import func

from deploy.config import TIME_LIMIT_FOR_RECURRING_PAYMENTS
from models.models import session, Users, Payment, Group, Invoice


def is_number(string):
    try:
        string = string.replace(" ", "")
        string = string.replace(",", ".")
        return float(string)
    except ValueError:
        return False


def with_session(function):
    @wraps(function)
    def context_session(*args, **kwargs):
        with session() as s:
            kwargs['s'] = s
            return function(*args, **kwargs)

    return context_session


class DataApi:
    def __init__(self):
        self.session = session

    def create_invoice(self, data):
        price = is_number(data.get("price"))
        if not price:
            return False

        with self.session() as s:

            invoice = Invoice(title_payment=data.get("title_payment"),
                              description_payment=data.get("description_payment"),
                              payload=data.get("payload"),
                              currency=data.get("currency"),
                              price=price * 100)
            s.add(invoice)
            s.commit()
            return True

    def update_invoice(self, data):
        price = is_number(data.get("price"))
        if not price:
            return False

        with self.session() as s:
            invoice = s.query(Invoice).filter(Invoice.id == data.get("invoice_id")).first()
            invoice.title_payment = data.get("title_payment")
            invoice.description_payment = data.get("description_payment")
            invoice.payload = data.get("payload")
            invoice.currency = data.get("currency")
            invoice.price = price * 100
            s.add(invoice)
            s.commit()
            return True

    def get_invoice(self, invoice_id):
        with self.session() as s:
            return s.query(Invoice).filter(Invoice.id == invoice_id).first()

    def set_group(self, chat_id, title):
        with self.session() as s:
            group = Group(chat_id=chat_id, title=title)
            s.add(group)
            s.commit()

    def get_group_title(self) -> list:
        with self.session() as s:
            group = s.query(Group.title).all()
            return [x[0] for x in group]

    def get_group_chat_id(self) -> list:
        with self.session() as s:
            group = s.query(Group.chat_id).all()
            return [x[0] for x in group]

    def get_group_by_inline(self):
        with self.session() as s:
            group = s.query(Group.title, Group.chat_id).all()
            return group

    def get_invoice_by_inline(self):
        with self.session() as s:
            invoices = s.query(Invoice.title_payment, Invoice.price, Invoice.id).all()
            return invoices

    def remove_group_for_db(self, chat_id):
        with self.session() as s:
            s.query(Group).filter(Group.chat_id == chat_id).delete()
            s.commit()

    def set_user(self, telegram_id, username, first_name, chat_id, last_name):
        with self.session() as s:
            user = s.query(Users).filter(Users.telegram_id == telegram_id).first()
            if user:
                return user.id
            user = Users(telegram_id=telegram_id,
                         username=username,
                         first_name=first_name,
                         last_name=last_name,
                         chat_id=chat_id)
            user.date_add = time.time()
            s.add(user)
            s.commit()
            payment = Payment(user_id=user.id, payment_date=None)
            s.add(payment)
            s.commit()
            return user

    def payment_time_limit(self, telegram_id):

        with self.session() as s:
            user = s.query(Users).filter(Users.telegram_id == telegram_id).first()
            if not user:
                return True
            payment = s.query(func.max(Payment.payment_date).label("last_date")).filter(Payment.user_id == user.id).one()
            if not payment[0]:
                return True

            if payment[0] + TIME_LIMIT_FOR_RECURRING_PAYMENTS > time.time():
                return False
            return True

    def payment_fixation(self, telegram_id, username, first_name, last_name, chat_id):
        with self.session() as s:
            user = s.query(Users).filter(Users.telegram_id == telegram_id).first()
            if user:
                user.set_pay()
                s.add(user)
                s.commit()
                return True
            else:
                user = self.set_user(telegram_id=telegram_id,
                                     username=username,
                                     first_name=first_name,
                                     last_name=last_name,
                                     chat_id=chat_id)

                user.date_add = time.time()
                s.add(user)
                s.commit()
                user.set_pay()
                s.add(user)
                s.commit()
                return True

    def render_excel_file(self, telegram_id):
        with self.session() as s:
            result = s.query(Users, Payment).filter(Users.id == Payment.user_id).all()
            id_list = []
            telegram_id_list = []
            username_list = []
            status_pay_list = []
            payment_date_list = []
            date_add_list = []
            first_name_list = []
            last_name_list = []
            payment_time_list = []
            for user, payment in result:
                id_list.append(user.id)
                telegram_id_list.append(user.telegram_id)
                username_list.append(user.username)
                status_pay_list.append(payment.get_paid)
                payment_date_list.append(payment.get_payment_date)
                date_add_list.append(user.get_date_add)
                first_name_list.append(user.first_name)
                last_name_list.append(user.last_name)
                payment_time_list.append(payment.get_payment_time)
            df = DataFrame({"id": id_list,
                            "telegram_id": telegram_id_list,
                            "username": username_list,
                            "first_name": first_name_list,
                            "last_name": last_name_list,
                            "date_add": date_add_list,
                            "status_pay": status_pay_list,
                            "payment_date": payment_date_list,
                            "payment_time": payment_time_list
                            })

            with pandas.ExcelWriter('report.xlsx', engine='xlsxwriter') as wb:
                df.to_excel(wb, sheet_name='report', index=False)
                sheet = wb.sheets['report']
                sheet.set_column('A:A', 10)
                sheet.set_column('B:I', 18)
                sheet.autofilter('A1:I' + str(df.shape[0]))

            return True


data_api = DataApi()
