import os
from uuid import UUID, uuid4
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from sqlalchemy import (
    Column, String, Boolean, Integer, Float,
    DateTime, ForeignKey, DECIMAL, Enum as SQLEnum, MetaData, TIMESTAMP, func
)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import relationship, Mapped, mapped_column, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.backend.server.models import UserRole
import dotenv

dotenv.load_dotenv("src/config/.env")

class Settings(BaseSettings):
    POSTGRES_USER: str = os.environ.get("POSTGRES_USER")
    POSTGRES_PASSWORD: str = os.environ.get("POSTGRES_PASSWORD")
    POSTGRES_PORT: int = os.environ.get("POSTGRES_PORT")
    POSTGRES_HOST: str = os.environ.get("POSTGRES_HOST")
    POSTGRES_DB: str = os.environ.get("POSTGRES_DB")

    @property
    def DATABASE_URL_psycopg(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}" + \
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    #model_config = SettingsConfigDict(env_file="src/config/.env", extra="ignore")


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
    name: Mapped[str] = mapped_column(String(512))
    password_hash: Mapped[str] = mapped_column(String(512))
    api_key: Mapped[str] = mapped_column(String(512), unique=True)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.USER)

    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")
    balances: Mapped[List["Balance"]] = relationship("Balance", back_populates="user", cascade="all, delete-orphan",
        passive_deletes=True)


class Instrument(Base):
    __tablename__ = "instrument"

    ticker: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64))

    orders: Mapped[List["Order"]] = relationship("Order", back_populates="instrument")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="instrument",
                                                             )


class Balance(Base):
    __tablename__ = "balance"

    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("user_account.id", ondelete="CASCADE"), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), ForeignKey("instrument.ticker", ondelete="CASCADE"), primary_key=True)
    amount: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped["User"] = relationship("User", back_populates="balances")
    instrument: Mapped["Instrument"] = relationship("Instrument")


class Order(Base):
    __tablename__ = "order"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), default=OrderStatus.NEW)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    filled: Mapped[int] = mapped_column(Integer, default=0)

    direction: Mapped[Direction] = mapped_column(SQLEnum(Direction))
    qty: Mapped[int] = mapped_column(Integer)

    price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("user_account.id", ondelete="CASCADE"))
    ticker: Mapped[str] = mapped_column(String(10), ForeignKey("instrument.ticker", ondelete="CASCADE"))

    user: Mapped["User"] = relationship("User", back_populates="orders")
    instrument: Mapped["Instrument"] = relationship("Instrument", back_populates="orders")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="order")


class Transaction(Base):
    __tablename__ = "transaction"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    amount: Mapped[int] = mapped_column(Integer)
    price: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ticker: Mapped[str] = mapped_column(String(10), ForeignKey("instrument.ticker", ondelete="CASCADE"))
    order_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("order.id"))

    instrument: Mapped["Instrument"] = relationship("Instrument", back_populates="transactions")
    order: Mapped["Order"] = relationship("Order", back_populates="transactions")


class OrderBookLevel(Base):
    __tablename__ = "order_book_level"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    price: Mapped[int] = mapped_column(Integer)
    qty: Mapped[int] = mapped_column(Integer)
    is_bid: Mapped[bool] = mapped_column(Boolean)  # True для bid, False для ask
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ticker: Mapped[str] = mapped_column(String(10), ForeignKey("instrument.ticker", ondelete="CASCADE"))

    instrument: Mapped["Instrument"] = relationship("Instrument")
