from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Column, String, Boolean, Integer, Float,
    DateTime, ForeignKey, DECIMAL, Enum as SQLEnum, MetaData
)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.backend.server.models import UserRole


class Settings(BaseSettings):

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_PORT: int
    POSTGRES_HOST: str
    POSTGRES_DB: str

    @property
    def DATABASE_URL_psycopg(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}" +\
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file="src/config/.env", extra="ignore")


settings = Settings()

engine_pg = create_async_engine(
    url=settings.DATABASE_URL_psycopg,
    echo=True,
    pool_size=5,
    max_overflow=15
)


session_var = async_sessionmaker(engine_pg, class_=AsyncSession,
                                 expire_on_commit=False)

metadata = MetaData()

class Base(DeclarativeBase):
    pass


class OrderStatus(str, Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class User(Base):
    __tablename__ = "user_account"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(64))
    password_hash: Mapped[str] = mapped_column(String(128))  # Хэш пароля
    api_key: Mapped[str] = mapped_column(String(64), unique=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.USER)

    # Связи
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")
    balances: Mapped[List["Balance"]] = relationship("Balance", back_populates="user")


class Instrument(Base):
    __tablename__ = "instrument"

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)  # Например "MEMCOIN"
    name: Mapped[str] = mapped_column(String(64))

    # Связи
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="instrument")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="instrument")


class Balance(Base):
    __tablename__ = "balance"

    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("user_account.id"), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), ForeignKey("instrument.ticker"), primary_key=True)
    amount: Mapped[int] = mapped_column(Integer, default=0)

    # Связи
    user: Mapped["User"] = relationship("User", back_populates="balances")
    instrument: Mapped["Instrument"] = relationship("Instrument")



class Order(Base):
    __tablename__ = "order"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), default=OrderStatus.NEW)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    filled: Mapped[int] = mapped_column(Integer, default=0)

    # Общие поля для всех типов ордеров
    direction: Mapped[Direction] = mapped_column(SQLEnum(Direction))
    qty: Mapped[int] = mapped_column(Integer)

    # Поля для лимитного ордера
    price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Внешние ключи
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("user_account.id"))
    ticker: Mapped[str] = mapped_column(String(10), ForeignKey("instrument.ticker"))

    # Связи
    user: Mapped["User"] = relationship("User", back_populates="orders")
    instrument: Mapped["Instrument"] = relationship("Instrument", back_populates="orders")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="order")


class Transaction(Base):
    __tablename__ = "transaction"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    amount: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Внешние ключи
    ticker: Mapped[str] = mapped_column(String(10), ForeignKey("instrument.ticker"))
    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("order.id"))

    # Связи
    instrument: Mapped["Instrument"] = relationship("Instrument", back_populates="transactions")
    order: Mapped["Order"] = relationship("Order", back_populates="transactions")


class OrderBookLevel(Base):
    __tablename__ = "order_book_level"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    price: Mapped[int] = mapped_column(Integer)
    qty: Mapped[int] = mapped_column(Integer)
    is_bid: Mapped[bool] = mapped_column(Boolean)  # True для bid, False для ask
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Внешний ключ
    ticker: Mapped[str] = mapped_column(String(10), ForeignKey("instrument.ticker"))

    # Связь
    instrument: Mapped["Instrument"] = relationship("Instrument")