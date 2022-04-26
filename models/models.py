import time
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session, relationship

from deploy.config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL, echo=False)


@contextmanager
def session():
    connection = engine.connect()
    db_session = scoped_session(sessionmaker(autocommit=False, autoflush=True, bind=engine))
    try:
        yield db_session
    except Exception as e:
        print(e)
    finally:
        db_session.remove()
        connection.close()


class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, unique=True, primary_key=True)
    telegram_id = Column(Integer)
    username = Column(String(120))
    first_name = Column(String(120))
    last_name = Column(String(120))
    chat_id = Column(Integer)
    date_add = Column(Integer)
    payment = relationship("Payment", backref="users", lazy='dynamic')

    def __int__(self, telegram_id, username, chat_id, first_name, last_name):
        self.telegram_id = telegram_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.chat_id = chat_id

    def set_pay(self):
        with session() as s:
            payment_date = time.time()
            payment = Payment(user_id=self.id, payment_date=payment_date)
            payment.paid = True
            s.add(payment)
            s.commit()

    @property
    def get_date_add(self):
        return datetime.fromtimestamp(self.date_add).strftime('%Y-%m-%d')


class Payment(Base):
    __tablename__ = 'payment'
    id = Column(Integer, unique=True, primary_key=True)
    payment_date = Column(Integer)
    paid = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey('users.id'))

    def __int__(self, user_id, payment_date):
        self.user_id = user_id
        self.payment_date = payment_date

    @property
    def get_paid(self):
        if self.paid:
            return "True"
        return "False"

    @property
    def get_payment_date(self):
        if self.payment_date:
            return datetime.fromtimestamp(self.payment_date).strftime('%Y-%m-%d')

    @property
    def get_payment_time(self):
        if self.payment_date:
            return datetime.fromtimestamp(self.payment_date).strftime('%H:%M')


class Group(Base):
    __tablename__ = 'telegram_groups'
    id = Column(Integer, unique=True, primary_key=True)
    chat_id = Column(Integer)
    title = Column(String(240))

    def __int__(self, chat_id, title):
        self.chat_id = chat_id
        self.title = title


Base.metadata.create_all(engine)
