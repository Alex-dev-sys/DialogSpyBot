"""Базовый декларативный класс для всех ORM-моделей."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Общий Base для SQLAlchemy 2.0 declarative-моделей."""
