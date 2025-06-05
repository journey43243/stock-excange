import os
import uuid

import jwt

from src.backend.database.database import User, session_var, Instrument, Order, OrderBookLevel, Transaction
from sqlalchemy import select, bindparam, insert, String, Integer
import hashlib
from src.backend.server.models import NewUser, UserRole


class PublicORM:

    @classmethod
    async def check_token(cls, token):
        stmt = select(User).where(User.api_key == bindparam("token", type_=String()))
        async with session_var() as session:
            query = await session.execute(stmt, {"token": token})
        if query.one_or_none():
            return True
        else:
            return False

    @classmethod
    async def registration(cls, user: NewUser):
        token = jwt.encode({"username": user.name}, os.environ.get('SECRET_KEY'),
                           algorithm='HS256')
        uuid_id = uuid.uuid4()
        stmt = insert(User).values(
            [{"name": bindparam("name", type_=String(128)), "password_hash": bindparam("password_hash", type_=String(64)),
              "api_key": token,
              "role": bindparam("role"),
              "id": uuid_id}])
        async with session_var() as session:
            await session.execute(stmt, {"name": user.name,
                                         "password_hash": hashlib.sha256(user.password.encode()).hexdigest(),
                                         "role": UserRole.USER})
            await session.commit()
        return user, token, uuid_id

    @classmethod
    async def select_instruments(cls):
        stmt = select(Instrument)
        async with session_var() as session:
            query = await session.execute(stmt)
        return query.scalars()

    @classmethod
    async def select_orderbook(cls, ticker, limit):
        stmt = select(OrderBookLevel).where(OrderBookLevel.ticker == bindparam("ticker", type_=String())).limit(
            bindparam("limit", type_=Integer()))
        async with session_var() as session:
            query = await session.execute(stmt, {"limit": int(limit), "ticker": ticker})
        return query.scalars()

    @classmethod
    async def transactions(cls, ticker, limit):
        stmt = select(Transaction).where(Transaction.ticker == bindparam("ticker", type_=String())).limit(
            bindparam("limit", type_=Integer()))
        async with session_var() as session:
            query = await session.execute(stmt, {"limit": int(limit), "ticker": ticker})
        return query.scalars()
