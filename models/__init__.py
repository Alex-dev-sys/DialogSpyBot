"""ORM-модели приложения."""
from .base import Base
from .message import Message, MessageEdit

__all__ = ["Base", "Message", "MessageEdit"]
