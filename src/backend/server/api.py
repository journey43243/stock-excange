import os
from datetime import datetime
from typing import List, Optional, Dict

from fastapi import FastAPI, APIRouter, Header, HTTPException
from fastapi_restful.cbv import cbv
from pydantic import UUID4
from starlette.requests import Request
from models import Transaction, L2OrderBook, Level, Instrument, UserRole, User, NewUser, \
    CreateOrderResponse, LimitOrderBody, MarketOrder, LimitOrder, MarketOrderBody, Ok
import uvicorn
from src.backend.database.orm import PublicORM
import jwt

app = FastAPI()
public_router = APIRouter(prefix='/api/v1')
balance_router = APIRouter(prefix='/api/v1')
order_router = APIRouter(prefix='/api/v1')
admin_router = APIRouter(prefix='/api/v1')
user_router = APIRouter(prefix='/api/v1')


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


@cbv(balance_router)
class BalanceCBV:
    @balance_router.get("/public/transactions/{ticker}", response_model=List[Transaction], tags=["public"])
    async def get_transaction_history(self, ticker: str, limit=10):
        """История сделок"""
        return [Transaction(
            ticker=i.ticker,
            amount=i.amount,
            price=i.ptice,
            timestamp=i.timestamp
        ) for i in await PublicORM.transactions(ticker, limit)]

    # --- Balance Endpoints ---
    @balance_router.get("/balance", tags=["balance"])
    async def get_balances(self, authorization: Optional[str] = Header(None)) -> Dict[str, int]:
        """Получить балансы"""
        return {"MEMCOIN": 0, "DODGE": 100500}


@cbv(order_router)
class OrderCBV:

    # --- Order Endpoints ---
    @order_router.post("/order", response_model=CreateOrderResponse, tags=["order"])
    async def create_order(self,
                           order: LimitOrderBody | MarketOrderBody,
                           authorization: Optional[str] = Header(None)
                           ):
        """Создать ордер"""
        return CreateOrderResponse(order_id="35b0884d-9a1d-47b0-91c7-eecf0ca56bc8")

    @order_router.get("/order", response_model=List[LimitOrder | MarketOrder], tags=["order"])
    async def list_orders(self, authorization: Optional[str] = Header(None)):
        """Список ордеров"""
        return []

    @order_router.get("/order/{order_id}", response_model=LimitOrder | MarketOrder, tags=["order"])
    async def get_order(self, order_id: UUID4, authorization: Optional[str] = Header(None)):
        """Получить ордер"""
        raise HTTPException(status_code=404, detail="Order not found")

    @order_router.delete("/order/{order_id}", response_model=Ok, tags=["order"])
    async def cancel_order(self, order_id: UUID4, authorization: Optional[str] = Header(None)):
        """Отменить ордер"""
        return Ok()


cbv(admin_router)


class AdminCBV:

    # --- Admin Endpoints ---
    @admin_router.delete("/admin/user/{user_id}", response_model=User, tags=["admin", "user"])
    async def delete_user(self, user_id: UUID4, authorization: Optional[str] = Header(None)):
        """Удалить пользователя"""
        return User(
            id=user_id,
            name="Deleted User",
            role=UserRole.USER,
            api_key=""
        )

    @admin_router.post("/admin/instrument", response_model=Ok, tags=["admin"])
    async def add_instrument(self,
                             instrument: Instrument,
                             authorization: Optional[str] = Header(None)):
        """Добавить инструмент"""
        return Ok()

    @admin_router.delete("/admin/instrument/{ticker}", response_model=Ok, tags=["admin"])
    async def delete_instrument(self, ticker: str, authorization: Optional[str] = Header(None)):
        """Удалить инструмент"""
        return Ok()

    @admin_router.post("/admin/balance/deposit", response_model=Ok, tags=["admin", "balance"])
    async def deposit(self,
                      user_id: UUID4,
                      ticker: str,
                      amount: int,
                      authorization: Optional[str] = Header(None)):
        """Пополнение баланса"""
        return Ok()

    @admin_router.post("/admin/balance/withdraw", response_model=Ok, tags=["admin", "balance"])
    async def withdraw(
            user_id: UUID4,
            ticker: str,
            amount: int,
            authorization: Optional[str] = Header(None)):
        """Вывод средств"""
        return Ok()


app.include_router(public_router)
app.include_router(admin_router)
app.include_router(balance_router)
app.include_router(order_router)

if __name__ == "__main__":
    uvicorn.run("src.backend.server.api:app", host='0.0.0.0', port=8000, reload=True)
