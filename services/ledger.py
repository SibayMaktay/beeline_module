from __future__ import annotations

import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_payments (
    fingerprint     TEXT PRIMARY KEY,
    ctn             TEXT NOT NULL,
    account_id      INTEGER NOT NULL,
    amount          REAL NOT NULL,
    transaction_id  INTEGER,
    created_at      INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_processed_ctn ON processed_payments (ctn);
CREATE INDEX IF NOT EXISTS idx_processed_created ON processed_payments (created_at);
"""


class PaymentLedger:
    """Хранилище отпечатков уже проведённых платежей."""

    def __init__(self, db_path: str = "./store/payments.db"):
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_schema()

    # ------------------------------------------------------------------ #
    def is_processed(self, fingerprint: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM processed_payments WHERE fingerprint = ?", (fingerprint,)
            ).fetchone()
        return row is not None

    def remember(
        self,
        fingerprint: str,
        *,
        ctn: str,
        account_id: int,
        amount: float,
        transaction_id: Optional[int] = None,
    ) -> bool:
        """
        Записывает отпечаток. Возвращает False, если он уже был —
        значит платёж провёл параллельный воркер.
        """
        with self._lock, self._connect() as conn:
            try:
                conn.execute(
                    "INSERT INTO processed_payments "
                    "(fingerprint, ctn, account_id, amount, transaction_id, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (fingerprint, ctn, int(account_id), float(amount),
                     int(transaction_id or 0), int(time.time())),
                )
                return True
            except sqlite3.IntegrityError:
                logger.info("Ledger: отпечаток %s уже записан, пропускаю", fingerprint)
                return False

    def claim(self, fingerprint: str, *, ctn: str, account_id: int, amount: float) -> bool:
        """
        Атомарно «бронирует» платёж ДО обращения к UTM5.

        True — бронь получена, можно проводить платёж.
        False — платёж уже обработан или обрабатывается прямо сейчас.
        """
        return self.remember(fingerprint, ctn=ctn, account_id=account_id, amount=amount)

    def attach_transaction(self, fingerprint: str, transaction_id: int) -> None:
        """Дописывает id транзакции UTM5 к ранее забронированному отпечатку."""
        with self._lock, self._connect() as conn:
            conn.execute(
                "UPDATE processed_payments SET transaction_id = ? WHERE fingerprint = ?",
                (int(transaction_id), fingerprint),
            )

    def release(self, fingerprint: str) -> None:
        """
        Снимает бронь, если платёж провести не удалось,
        чтобы следующий запуск синхронизации попробовал снова.
        """
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM processed_payments WHERE fingerprint = ?", (fingerprint,))
        logger.info("Ledger: бронь %s снята после ошибки", fingerprint)

    def purge_older_than(self, days: int = 180) -> int:
        """Чистит старые записи, чтобы база не росла бесконечно."""
        threshold = int(time.time()) - days * 86400
        with self._lock, self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM processed_payments WHERE created_at < ?", (threshold,)
            )
            return cursor.rowcount

    # ------------------------------------------------------------------ #
    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, timeout=15, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn