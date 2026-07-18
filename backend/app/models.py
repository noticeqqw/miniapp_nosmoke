from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quit_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    vape_price: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)
    vape_days: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    vape_puffs: Mapped[int] = mapped_column(Integer, default=18000, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    checkins: Mapped[list["CheckIn"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="raise"
    )


class CheckIn(Base):
    __tablename__ = "checkins"
    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_checkin_user_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.tg_id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    mood: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    user: Mapped["User"] = relationship(back_populates="checkins")
