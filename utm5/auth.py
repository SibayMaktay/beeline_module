from __future__ import annotations

import logging
import threading
import time
from typing import Dict, Optional

import requests

from .errors import UTM5AuthError, UTM5Unavailable
from .settings import UTM5Settings

logger = logging.getLogger(__name__)

class UTM5Auth:
    """Хранит и обновляет cookie авторизации UTM5."""

    #: сколько секунд считать полученный session_id действительным
    SESSION_TTL = 20 * 60

    def __init__(self, settings: UTM5Settings, session: Optional[requests.Session] = None):
        self._settings = settings
        self._session = session or requests.Session()
        self._lock = threading.Lock()
        self._session_id: Optional[str] = None
        self._obtained_at: float = 0.0

    # ------------------------------------------------------------------ #
    # публичный интерфейс
    # ------------------------------------------------------------------ #
    def cookies(self) -> Dict[str, str]:
        """Cookie для очередного запроса. При необходимости логинится."""
        if self._settings.uses_permanent_token:
            return {"token": self._settings.permanent_token}
        return {"session_id": self._ensure_session_id()}

    def refresh(self) -> Dict[str, str]:
        """
        Принудительно обновляет сессию — вызывается транспортом после 401.

        Для постоянного токена обновлять нечего: если он отвергнут,
        значит токен отозван или неверен, и это ошибка конфигурации.
        """
        if self._settings.uses_permanent_token:
            raise UTM5AuthError(
                "UTM5 отверг постоянный токен. Проверьте UTM5_TOKEN "
                "в карточке системного пользователя веб-интерфейса."
            )
        with self._lock:
            self._session_id = None
            self._obtained_at = 0.0
        return {"session_id": self._ensure_session_id()}

    def logout(self) -> None:
        """Забывает текущую сессию (нужно при остановке приложения)."""
        with self._lock:
            self._session_id = None
            self._obtained_at = 0.0

    # ------------------------------------------------------------------ #
    # внутреннее
    # ------------------------------------------------------------------ #
    def _ensure_session_id(self) -> str:
        if self._is_fresh():
            return self._session_id  # type: ignore[return-value]

        with self._lock:
            # другой поток мог успеть залогиниться, пока мы ждали мьютекс
            if self._is_fresh():
                return self._session_id  # type: ignore[return-value]
            self._session_id = self._login()
            self._obtained_at = time.monotonic()
            return self._session_id

    def _is_fresh(self) -> bool:
        return bool(self._session_id) and (time.monotonic() - self._obtained_at) < self.SESSION_TTL

    def _login(self) -> str:
        url = f"{self._settings.api_url}/login"
        logger.info("UTM5: логин пользователя %s", self._settings.login)
        try:
            response = self._session.post(
                url,
                json={"username": self._settings.login, "password": self._settings.password},
                timeout=self._settings.timeout,
                verify=self._settings.verify_ssl,
            )
        except requests.exceptions.RequestException as exc:
            raise UTM5Unavailable(f"UTM5 недоступен при логине ({url}): {exc}") from exc

        if response.status_code >= 400:
            raise UTM5AuthError(
                f"UTM5 отклонил логин: HTTP {response.status_code}. {response.text[:300]}"
            )

        session_id = self._extract_session_id(response)
        if not session_id:
            raise UTM5AuthError(
                f"UTM5 не вернул session_id. Тело ответа: {response.text[:300]}"
            )
        logger.info("UTM5: сессия получена")
        return session_id

    @staticmethod
    def _extract_session_id(response: requests.Response) -> Optional[str]:
        """session_id приходит в теле, но некоторые сборки ставят его cookie."""
        try:
            body = response.json()
        except ValueError:
            body = {}
        if isinstance(body, dict):
            for key in ("session_id", "sessionId", "token"):
                value = body.get(key)
                if value:
                    return str(value)
        return response.cookies.get("session_id")