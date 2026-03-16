import logging
import time

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.inspection import inspect
from sqlalchemy.sql import text

from src.core.config import settings
from src.db.base import Base
from src.db.session import engine
from src.models.index import CryptoIndex, IndexAsset  # noqa: F401

logger = logging.getLogger(__name__)


def init_db() -> None:
    last_error: Exception | None = None
    for attempt in range(1, settings.db_init_max_attempts + 1):
        try:
            Base.metadata.create_all(bind=engine)
            with engine.begin() as connection:
                inspector = inspect(connection)
                index_columns = {column["name"] for column in inspector.get_columns("indexes")}
                if "description" not in index_columns:
                    connection.execute(
                        text("ALTER TABLE indexes ADD COLUMN description VARCHAR(500)")
                    )
            if attempt > 1:
                logger.info(
                    "Database initialization succeeded on attempt %s/%s.",
                    attempt,
                    settings.db_init_max_attempts,
                )
            return
        except SQLAlchemyError as exc:
            last_error = exc
            if attempt >= settings.db_init_max_attempts:
                break

            logger.warning(
                "Database initialization attempt %s/%s failed; retrying in %.1fs.",
                attempt,
                settings.db_init_max_attempts,
                settings.db_init_retry_delay_seconds,
            )
            time.sleep(settings.db_init_retry_delay_seconds)

    raise RuntimeError(
        f"Failed to initialize database after {settings.db_init_max_attempts} attempts."
    ) from last_error
