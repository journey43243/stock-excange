import os
from datetime import datetime
from typing import List, Optional, Dict

from fastapi import FastAPI, APIRouter, Header, HTTPException, Depends, Request
from fastapi_restful.cbv import cbv
from pydantic import UUID4
from sqlalchemy import inspect

from models import Transaction, L2OrderBook, Level, Instrument, UserRole, User, NewUser, \
    CreateOrderResponse, LimitOrderBody, MarketOrder, LimitOrder, MarketOrderBody, Ok, Direction
import uvicorn
from src.backend.database.orm import PublicORM, AuthORM, BalanceORM, AdminORM, OrderORM


async def verify_user_token(authorization: str = Header(...)):
    if authorization:
        res = await AuthORM.verify_token_orm(authorization)
        if res:
            return True
        raise HTTPException(status_code=401)


async def verify_admin_token(authorization: str = Header(...)):
    if authorization:
        res = await AuthORM.verify_admin_token_orm(authorization)
        if res:
            return True
        raise HTTPException(status_code=401)


app = FastAPI()
public_router = APIRouter(prefix='/api/v1')
balance_router = APIRouter(prefix='/api/v1', dependencies=[Depends(verify_user_token)])
order_router = APIRouter(prefix='/api/v1', dependencies=[Depends(verify_user_token)])
admin_router = APIRouter(prefix='/api/v1', dependencies=[Depends(verify_admin_token)])
user_router = APIRouter(prefix='/api/v1', dependencies=[Depends(verify_user_token)])


@cbv(public_router)
class PublicCBV:

    @public_router.post("/public/register", response_model=User, tags=["public"])
    async def register(self, new_user: NewUser):
        """Регистрация пользователя"""
        # Реализация регистрации
        user = await PublicORM.registration(new_user)
        return User(
            id=user[2],
            name=user[0].name,
            role=UserRole.USER,
            api_key=user[1]
        )

    @public_router.get("/public/instrument", response_model=List[Instrument], tags=["public"])
    async def list_instruments(self):
        response = []
        for i in await PublicORM.select_instruments():
            response.append(Instrument(name=i.name, ticker=i.ticker))
        return response

    @public_router.get("/public/orderbook/{ticker}", response_model=L2OrderBook, tags=["public"])
    async def get_orderbook(self, ticker: str, limit=10):
        bid_levels = []
        ask_levels = []
        for i in await PublicORM.select_orderbook(ticker, limit):
            if i.is_bid:
                bid_levels.append(Level(price=i.cost, qty=i.qty))
            else:
                ask_levels.append(Level(price=i.cost, qty=i.qty))
        return L2OrderBook(
            bid_levels=bid_levels,
            ask_levels=ask_levels
        )

    @public_router.get("/public/transactions/{ticker}", response_model=List[Transaction], tags=["public"])
    async def get_transaction_history(self, ticker: str, limit=10):
        """История сделок"""
        return [Transaction(
            ticker=i.ticker,
            amount=i.amount,
            price=i.ptice,
            timestamp=i.timestamp
        ) for i in await PublicORM.transactions(ticker, limit)]


@cbv(balance_router)
class BalanceCBV:

    # --- Balance Endpoints ---
    @balance_router.get("/balance", tags=["balance"])
    async def get_balances(self, request: Request) -> Dict[str, int]:
        """Получить балансы"""
        balance = await BalanceORM.get_balance(request.headers["Authorization"])
        return {i.ticker: i.amount for i in balance}


@cbv(order_router)
class OrderCBV:

    # --- Order Endpoints ---
    @order_router.post("/order", response_model=CreateOrderResponse, tags=["order"])
    async def create_order(self, request: Request,
                           order: LimitOrderBody | MarketOrderBody):
        query = await OrderORM.create_order(request.headers["Authorization"], order)
        return CreateOrderResponse(order_id=query)

    @order_router.get("/order", response_model=List[LimitOrder | MarketOrder], tags=["order"])
    async def list_orders(self):
        query = await OrderORM.orders_list()
        response = []
        for order in query:
            if getattr(order, "price") and order.price is not None:
                attrs = {c.key: getattr(order, c.key) for c in inspect(order).mapper.column_attrs}
                body = LimitOrderBody(**attrs)
                attrs["body"] = body
                entry = LimitOrder(**attrs)
                response.append(entry)
            else:
                attrs = {c.key: getattr(order, c.key) for c in inspect(order).mapper.column_attrs}
                body = MarketOrderBody(**attrs)
                attrs["body"] = body
                entry = MarketOrder(**attrs)
                response.append(entry)
        return response
    @order_router.get("/order/{order_id}", response_model=LimitOrder | MarketOrder, tags=["order"])
    async def get_order(self, order_id: UUID4):
        order = await OrderORM.get_order(order_id)
        if getattr(order, "price") and order.price is not None:
            attrs = {c.key: getattr(order, c.key) for c in inspect(order).mapper.column_attrs}
            body = LimitOrderBody(**attrs)
            attrs["body"] = body
            entry = LimitOrder(**attrs)
        else:
            attrs = {c.key: getattr(order, c.key) for c in inspect(order).mapper.column_attrs}
            body = MarketOrderBody(**attrs)
            attrs["body"] = body
            entry = MarketOrder(**attrs)
        return entry

    @order_router.delete("/order/{order_id}", response_model=Ok, tags=["order"])
    async def cancel_order(self, order_id: UUID4):
        await OrderORM.cancel_order(order_id)
        return Ok()


@cbv(admin_router)
class AdminCBV:

    # --- Admin Endpoints ---
    @admin_router.delete("/admin/user/{user_id}", response_model=User, tags=["admin", "user"])
    async def delete_user(self, user_id: UUID4):
        """Удалить пользователя"""
        user = await AdminORM.delete_user(user_id)
        return User(
            id=user_id,
            name=user.name,
            role=user.role,
            api_key=user.api_key
        )

    @admin_router.post("/admin/instrument", response_model=Ok, tags=["admin"])
    async def add_instrument(self,
                             instrument: Instrument):
        await AdminORM.add_instrument(instrument.ticker, instrument.name)
        return Ok()

    @admin_router.delete("/admin/instrument/{ticker}", response_model=Ok, tags=["admin"])
    async def delete_instrument(self, ticker: str):
        await AdminORM.delete_instrument(ticker)
        return Ok()

    @admin_router.post("/admin/balance/deposit", response_model=Ok, tags=["admin", "balance"])
    async def deposit(self,
                      user_id: UUID4,
                      ticker: str,
                      amount: int):
        await AdminORM.do_deposit(user_id, ticker, amount)

        return Ok()

    @admin_router.post("/admin/balance/withdraw", response_model=Ok, tags=["admin", "balance"])
    async def withdraw(self,
                       user_id: UUID4,
                       ticker: str,
                       amount: int):
        """Вывод средств"""
        await AdminORM.do_withdraw(user_id, ticker, amount)
        return Ok()


app.include_router(public_router)
app.include_router(admin_router)
app.include_router(balance_router)
app.include_router(order_router)

if __name__ == "__main__":
    uvicorn.run("src.backend.server.api:app", host='0.0.0.0', port=8000, reload=True)
