from dataclasses import dataclass
from threading import Lock
from typing import Dict
from uuid import uuid4


@dataclass
class UserRecord:
    id: str
    email: str
    password_hash: str
    name: str | None = None


class InMemoryUserStore:
    def __init__(self) -> None:
        self._users_by_id: Dict[str, UserRecord] = {}
        self._users_by_email: Dict[str, UserRecord] = {}
        self._lock = Lock()

    def create_user(self, email: str, password_hash: str, name: str | None) -> UserRecord:
        email_key = email.lower()

        with self._lock:
            if email_key in self._users_by_email:
                raise ValueError("User with this email already exists.")

            user = UserRecord(
                id=str(uuid4()),
                email=email_key,
                password_hash=password_hash,
                name=name,
            )
            self._users_by_id[user.id] = user
            self._users_by_email[email_key] = user

        return user

    def get_by_email(self, email: str) -> UserRecord | None:
        return self._users_by_email.get(email.lower())

    def get_by_id(self, user_id: str) -> UserRecord | None:
        return self._users_by_id.get(user_id)
