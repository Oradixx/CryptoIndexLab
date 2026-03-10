from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.user import User


class UserRepository:
    def __init__(self, db_session: Session) -> None:
        self._db_session = db_session

    def create(self, email: str, hashed_password: str, name: str | None) -> User:
        user = User(email=email, hashed_password=hashed_password, name=name)
        self._db_session.add(user)
        return user

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        return self._db_session.scalar(stmt)

    def get_by_id(self, user_id: str) -> User | None:
        stmt = select(User).where(User.id == user_id)
        return self._db_session.scalar(stmt)
