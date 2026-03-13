import logging
import time

from sqlalchemy.exc import SQLAlchemyError

from src.core.config import settings
from src.db.base import Base
from src.db.session import engine
from src.models.user import User  # noqa: F401

logger = logging.getLogger(__name__)


def init_db() -> None:
    last_error: Exception | None = None
    for attempt in range(1, settings.db_init_max_attempts + 1):
        try:
            Base.metadata.create_all(bind=engine)
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
