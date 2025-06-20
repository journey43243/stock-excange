from pydantic import BaseModel, UUID4, Field
from typing import List
from enum import Enum
from datetime import datetime
from typing_extensions import Annotated


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"


class Deposit(BaseModel):
    user_id: UUID4
    ticker: str
    amount: int


class Withdraw(BaseModel):
    user_id: UUID4
    ticker: str
    amount: int


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class NewUser(BaseModel):
    name: str


class User(BaseModel):
    id: UUID4
    name: str
    role: UserRole
    api_key: str


class Instrument(BaseModel):
    name: str
    ticker: Annotated[str, Field(pattern='^[A-Z]{2,10}$')]


class Level(BaseModel):
    price: int
    qty: int


class L2OrderBook(BaseModel):
    bid_levels: List[Level]
    ask_levels: List[Level]


class Transaction(BaseModel):
    ticker: str
    amount: int
    price: int
    timestamp: datetime


class LimitOrderBody(BaseModel):
    direction: Direction
    ticker: str | None
    qty: int
    price: int


class MarketOrderBody(BaseModel):
    direction: Direction
    ticker: str | None
    qty: int


class LimitOrder(BaseModel):
    id: UUID4
    status: OrderStatus
    user_id: UUID4
    timestamp: datetime
    body: LimitOrderBody
    filled: int = 0


class MarketOrder(BaseModel):
    id: UUID4
    status: OrderStatus
    user_id: UUID4
    timestamp: datetime
    body: MarketOrderBody


class CreateOrderResponse(BaseModel):
    success: bool = True
    order_id: UUID4


class Ok(BaseModel):
    success: bool = True
