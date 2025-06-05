import os
import uuid

import jwt

from src.backend.database.database import User, session_var
from sqlalchemy import select, bindparam, insert
import hashlib
from src.backend.server.models import NewUser, UserRole


class UserORM:

    @classmethod
    async def check_token(cls, token):
        stmt = select(User).where(User.token == bindparam("token"))
        async with session_var() as session:
            query = await session.execute(stmt, {"token": token})
        print(query)
        if query.one_or_none():
            return True
        else:
            return False

    @classmethod
    async def registration(cls, user: NewUser):
        token = jwt.encode({"username": user.name}, os.environ.get('SECRET_KEY'),
                                                         algorithm='HS256')
        uuid_id = uuid.uuid4()
        stmt = insert(User).values([{"username": bindparam("username"), "password": bindparam("password"),
                                     "token": token,
                                     "role": bindparam("role"),
                                     "id": uuid_id}])
        async with session_var() as session:
            await session.execute(stmt, {"username": user.name, "password": hashlib.sha256(user.password.encode()).hexdigest(),
                                         "role": UserRole.ADMIN})
            await session.commit()
        return user, token, uuid_id