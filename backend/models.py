"""Database models for PurNi Menu."""
from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base


class Week(Base):
    """Represents a week. We use year + week_number for identification."""
    __tablename__ = "weeks"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    week_number = Column(Integer, nullable=False)  # 1-52
    start_date = Column(Date, nullable=False)  # Monday of the week
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    menu_items = relationship("MenuItem", back_populates="week", cascade="all, delete-orphan")


class MenuItem(Base):
    """A food item in the weekly menu."""
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    week_id = Column(Integer, ForeignKey("weeks.id"), nullable=False)
    day = Column(Integer, nullable=False)  # 0=Mon, 1=Tue, ..., 6=Sun
    meal_slot = Column(String(20), nullable=False)  # breakfast, lunch, dinner, snack
    food_name = Column(String(200), nullable=False)
    serving_size = Column(String(100), default="1 serving")
    calories = Column(Float, default=0)
    protein = Column(Float, default=0)
    added_by = Column(String(50), default="")  # "Purnima" or "Nitesh"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    week = relationship("Week", back_populates="menu_items")
