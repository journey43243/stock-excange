import datetime
import os
import uuid

import jwt
import sqlalchemy.exc
from fastapi import HTTPException

from src.backend.database.database import User, session_var, Instrument, Order, OrderBookLevel, Transaction, Balance, \
    OrderStatus
from sqlalchemy import select, bindparam, insert, String, Integer, UUID, and_, update, delete, DECIMAL
import hashlib
from src.backend.server.models import NewUser, UserRole, LimitOrderBody, Direction


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
                                             "role": UserRole.ADMIN})
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
        print(query.scalars())
        return query.scalars()


class AdminORM:
    @classmethod
    async def do_deposit(cls, user_id, ticker, amount):
        async with session_var() as session:
            stmt = select(User).where(User.id == bindparam("id", type_=UUID))
            query = await session.execute(stmt, {"id": user_id})
            user = query.scalars().one_or_none()

            stmt = select(Instrument).where(Instrument.ticker == bindparam("ticker", type_=String()))
            query = await session.execute(stmt, {"ticker": ticker})
            instrument = query.scalars().one_or_none()
            if instrument is None or user is None:
                raise HTTPException(status_code=422)
            stmt = select(Balance).where(
                and_(Balance.user_id == bindparam("user_id", type_=UUID), Balance.ticker == bindparam("ticker")))
            query = await session.execute(stmt, {"user_id": user_id, "ticker": ticker})
            user = query.scalars().first()
            if user is None:
                stmt = insert(Balance).values(
                    [{"user_id": bindparam("user_id", type_=UUID), "ticker": bindparam("ticker"),
                      "amount": bindparam("amount")}])
                await session.execute(stmt, {"user_id": user_id, "ticker": ticker, "amount": amount})
            else:
                stmt = update(Balance).where(
                    and_(Balance.user_id == user.user_id, Balance.ticker == user.ticker)).values(
                    amount=user.amount + amount)
                await session.execute(stmt)
            await session.commit()

    @classmethod
    async def do_withdraw(cls, user_id, ticker, amount):
        async with session_var() as session:
            stmt = select(Balance).where(and_(Balance.user_id == bindparam("user_id", type_=UUID),
                                              Balance.ticker == bindparam("ticker", type_=String())))
            query = await session.execute(stmt, {"user_id": user_id, "ticker": ticker})
            temp = query.scalars().first()
            if temp and temp.amount - amount >= 0:
                stmt = update(Balance).where(
                    and_(Balance.user_id == temp.user_id, Balance.ticker == temp.ticker)).values(
                    amount=temp.amount - amount)
                await session.execute(stmt)
                await session.commit()
            else:
                raise HTTPException(status_code=422)

    @classmethod
    async def add_instrument(cls, ticker, name):
        stmt = insert(Instrument).values(
            [{"ticker": bindparam("ticker", type_=String()), "name": bindparam("name", type_=String())}])
        async with session_var() as session:
            try:
                await session.execute(stmt, {"name": name, "ticker": ticker})
                await session.commit()
            except sqlalchemy.exc.IntegrityError:
                raise HTTPException(status_code=422)

    @classmethod
    async def delete_instrument(cls, ticker):
        stmt = delete(Instrument).where(Instrument.ticker == bindparam("ticker", type_=String()))
        async with session_var() as session:
            await session.execute(stmt, {"ticker": ticker})
            await session.commit()

    @classmethod
    async def delete_user(cls, user_id):
        stmt = select(User).where(User.id == bindparam("id", type_=UUID))
        async with session_var() as session:
            user = await session.execute(stmt, {"id": user_id})
            if temp := user.scalars().one_or_none():
                stmt = delete(User).where(User.id == bindparam("id", type_=UUID))
                await session.execute(stmt, {"id": user_id})
                await session.commit()
        return temp


class OrderORM:

    @classmethod
    async def create_order(cls, api_key, order_model):
        stmt = select(User.id).where(User.api_key == bindparam("token", type_=String()))
        async with session_var() as session:
            query = await session.execute(stmt, {"token": api_key})
        user_id = query.scalars().first()
        stmt = select(Balance.amount).where(and_(Balance.user_id == user_id, Balance.ticker == order_model.ticker))
        async with session_var() as session:
            query = await session.execute(stmt)
        amount = query.scalars().one_or_none()
        if (amount is None or amount - order_model.qry < 0) and order_model.direction == Direction.SELL:
            raise HTTPException(status_code=422)
        else:
            stmt = update(Balance).where(and_(Balance.user_id == user_id, Balance.ticker == order_model.ticker)).values(amount=amount-order_model.qty)
            async with session_var() as session:
                await session.execute(stmt)
                await session.commit()
        order_id = uuid.uuid4()
        if isinstance(order_model, LimitOrderBody):
            stmt = insert(Order).values([{"id": order_id, "status": OrderStatus.NEW,
                                          "timestamp": datetime.datetime.utcnow(),
                                          "direction": order_model.direction.value,
                                          "qty": order_model.qty,
                                          "price": order_model.price,
                                          "user_id": user_id,
                                          "ticker": order_model.ticker}])
            async with session_var() as session:
                await session.execute(stmt)
                await session.commit()
        else:
            stmt = insert(Order).values([{"id": order_id, "status": OrderStatus.NEW,
                                          "timestamp": datetime.datetime.utcnow(),
                                          "direction": order_model.direction.value,
                                          "qty": order_model.qty,
                                          "price": None,
                                          "user_id": user_id,
                                          "ticker": order_model.ticker}])
            async with session_var() as session:
                await session.execute(stmt)
                await session.commit()

        return order_id

    @classmethod
    async def cancel_order(cls, order_id):
        stmt = select(Order).where(Order.id == order_id)
        async with session_var() as session:
            query = await session.execute(stmt)
        order = query.scalars().one_or_none()
        if order is None:
            raise HTTPException(status_code=422)

        stmt = delete(Order).where(Order.id == order_id)
        async with session_var() as session:
            await session.execute(stmt)
            await session.commit()
        if order.direction == Direction.SELL:
            stmt = select(Balance.amount).where(and_(Balance.user_id == order.user_id, Balance.ticker == order.ticker))
            async with session_var() as session:
                query = await session.execute(stmt)
            amount = query.scalars().first()
            stmt = update(Balance).where(and_(Balance.user_id == order.user_id, Balance.ticker == order.ticker)).values(amount=amount + order.qty)
            async with session_var() as session:
                await session.execute(stmt)
                await session.commit()

    @classmethod
    async def orders_list(cls):
        stmt = select(Order)
        async with session_var() as session:
            query = await session.execute(stmt)
        return query.scalars()

class AuthORM:
    @classmethod
    async def verify_token_orm(cls, token):
        stmt = select(User).where(User.api_key == bindparam("token"))
        async with session_var() as session:
            query = await session.execute(stmt, {"token": token})
        return query.scalars().one_or_none()

    @classmethod
    async def verify_admin_token_orm(cls, token):
        stmt = select(User).where(and_(User.api_key == bindparam("api_key")), User.role == UserRole.ADMIN)
        async with session_var() as session:
            query = await session.execute(stmt, {"api_key": token})
        return query.scalars().one_or_none()
