import os
import uuid

import jwt
import sqlalchemy.exc
from fastapi import HTTPException

from src.backend.database.database import User, session_var, Instrument, Order, OrderBookLevel, Transaction, Balance
from sqlalchemy import select, bindparam, insert, String, Integer
import hashlib
from src.backend.server.models import NewUser, UserRole


class PublicORM:

    @classmethod
    async def registration(cls, user: NewUser):
        token = jwt.encode({"username": user.name}, os.environ.get('SECRET_KEY'),
                           algorithm='HS256')
        uuid_id = uuid.uuid4()
        stmt = insert(User).values(
            [{"name": bindparam("name", type_=String(128)),
              "password_hash": bindparam("password_hash", type_=String(64)),
              "api_key": token,
              "role": bindparam("role"),
              "id": uuid_id}])
        try:
            async with session_var() as session:
                await session.execute(stmt, {"name": user.name,
                                             "password_hash": hashlib.sha256(user.password.encode()).hexdigest(),
                                             "role": UserRole.USER})
                await session.commit()
            return user, token, uuid_id
        except sqlalchemy.exc.IntegrityError:
            raise HTTPException(status_code=422)

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


class BalanceORM:

    @classmethod
    async def get_balance(cls, token):
        stmt = select(User.id).where(User.api_key == bindparam("api_key", type_=String()))
        async with session_var() as session:
            query = await session.execute(stmt, {"api_key": token})
            user_id = query.scalars().first()
            stmt = select(Balance).where(Balance.user_id == user_id)
            query = await session.execute(stmt)
        return query.scalars()



class AuthORM:
    @classmethod
    async def verify_token_orm(cls, token):
        stmt = select(User).where(User.api_key == bindparam("token"))
        async with session_var() as session:
            query = await session.execute(stmt, {"token": token})
        return query.scalars().one_or_none()
