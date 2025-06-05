import uuid
from typing import List

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, Integer, DECIMAL, ForeignKey
from sqlalchemy import UUID as UUID1
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from uuid import UUID


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

class User(Base):
    __tablename__ = "user_account"

    id: Mapped[UUID] = mapped_column(UUID1(as_uuid=True),primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password: Mapped[str] = mapped_column(String(64))
    token: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(6))
    orders: Mapped[List["Order"]] = relationship(back_populates="user")

class Order(Base):
    __tablename__ = "order"

    id: Mapped[UUID] = mapped_column(UUID1(as_uuid=True),primary_key=True, default=uuid.uuid4)
    status: Mapped[bool] = mapped_column(Boolean())
    type: Mapped[int] = mapped_column(Integer())
    cost: Mapped[float] = mapped_column(DECIMAL())
    user_id = mapped_column(ForeignKey("user_account.id"))
    user: Mapped["User"] = relationship("User", back_populates="orders")

class Instrument(Base):
    __tablename__ = "instrument"

    ticker: Mapped[str] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64))
