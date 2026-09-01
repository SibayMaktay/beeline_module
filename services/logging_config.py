"""
Модуль структурированного логирования в формате JSON.
"""
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """
    Форматтер для вывода логов в JSON формате.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Добавляем exception info если есть
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Добавляем extra поля если есть
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", "funcName",
                          "levelname", "levelno", "lineno", "module", "msecs",
                          "pathname", "process", "processName", "relativeCreated",
                          "stack_info", "exc_info", "thread", "threadName"]:
                log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False, default=str)


def setup_logging(level: str = "INFO", log_file: str = None) -> None:
    """
    Настраивает структурированное логирование в JSON формате.

    Args:
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Путь к файлу лога (опционально). Если None - только в stdout.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Очищаем существующие хендлеры
    root_logger.handlers.clear()

    # Создаём JSON форматтер
    json_formatter = JSONFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)
    root_logger.addHandler(console_handler)

    # File handler (опционально)
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(json_formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            root_logger.warning(f"Не удалось создать файл лога {log_file}: {e}")
