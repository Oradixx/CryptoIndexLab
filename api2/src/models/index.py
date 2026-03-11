from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base


class CryptoIndex(Base):
    __tablename__ = "indexes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    assets: Mapped[list["IndexAsset"]] = relationship(
        back_populates="index",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class IndexAsset(Base):
    __tablename__ = "index_assets"
    __table_args__ = (
        UniqueConstraint("index_id", "symbol", name="uq_index_assets_index_id_symbol"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    index_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("indexes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(String(10), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)

    index: Mapped[CryptoIndex] = relationship(back_populates="assets")
