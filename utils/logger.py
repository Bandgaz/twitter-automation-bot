import sys
from loguru import logger
from pathlib import Path

from config import LOG_LEVEL, LOG_FORMAT, LOGS_DIR


def setup_logger():
    """Настройка логирования для проекта"""

    # Удаляем стандартный обработчик
    logger.remove()

    # Добавляем консольный вывод с цветами
    logger.add(
        sys.stdout,
        format=LOG_FORMAT,
        level=LOG_LEVEL,
        colorize=True,
        enqueue=True
    )

    # Добавляем файловый вывод
    logger.add(
        LOGS_DIR / "twitter_automation.log",
        format=LOG_FORMAT,
        level=LOG_LEVEL,
        rotation="1 day",
        retention="30 days",
        compression="zip",
        enqueue=True
    )

    # Отдельный файл для ошибок
    logger.add(
        LOGS_DIR / "errors.log",
        format=LOG_FORMAT,
        level="ERROR",
        rotation="1 week",
        retention="2 months",
        compression="zip",
        enqueue=True
    )

    # Отдельный файл для активности аккаунтов
    logger.add(
        LOGS_DIR / "activity.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
        level="INFO",
        filter=lambda record: "activity" in record["extra"],
        rotation="1 day",
        retention="7 days",
        enqueue=True
    )

    return logger


# Экспортируем настроенный логгер
logger = setup_logger()


# Удобные функции для логирования активности
def log_activity(account_username: str, action: str, details: str = ""):
    """Логировать активность аккаунта"""
    logger.bind(activity=True).info(
        f"[{account_username}] {action} - {details}"
    )


def log_error(account_username: str, error: str, exception: Exception = None):
    """Логировать ошибку аккаунта"""
    if exception:
        logger.error(
            f"[{account_username}] {error}: {str(exception)}",
            exc_info=True
        )
    else:
        logger.error(f"[{account_username}] {error}")


def log_success(account_username: str, action: str):
    """Логировать успешное действие"""
    logger.success(f"[{account_username}] ✅ {action}")


def log_warning(account_username: str, warning: str):
    """Логировать предупреждение"""
    logger.warning(f"[{account_username}] ⚠️ {warning}")