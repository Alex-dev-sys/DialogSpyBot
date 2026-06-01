"""Пакет конфигурации. Экспортирует готовый singleton настроек."""
from .settings import Settings

# Единый экземпляр настроек на всё приложение.
settings = Settings()  # type: ignore[call-arg]

__all__ = ["Settings", "settings"]
