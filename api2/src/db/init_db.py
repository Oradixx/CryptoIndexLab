from src.db.base import Base
from src.db.session import engine
from src.models.index import CryptoIndex, IndexAsset  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
