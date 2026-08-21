from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import requests

from .auth import UTM5Auth
from .errors import UTM5ServerError, UTM5Unavailable, raise_for_status
from .settings import UTM5Settings

logger = logging.getLogger(__name__)


class UTM5Transport:
    """Тонкая обёртка над requests.Session с ретраями и авто-релогином."""

    #: статусы, при которых имеет смысл повторить запрос
    RETRY_STATUSES = frozenset({500, 502, 503, 504})

    def __init__(
        self,
        settings: UTM5Settings,
        auth: Optional[UTM5Auth] = None,
        session: Optional[requests.Session] = None,
    ):
        self._settings = settings
        self._session = session or requests.Session()
        self._auth = auth or UTM5Auth(settings, self._session)

    # ------------------------------------------------------------------ #
    # публичные шорткаты
    # ------------------------------------------------------------------ #
    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self.request("GET", path, params=params)

    def post(
        self,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
        *,
        idempotent: bool = False,
    ) -> Any:
        """
        POST по умолчанию НЕ повторяется при 5xx.

        Причина: если UTM5 успел записать платёж и упал уже на формировании
        ответа, повтор создаст второй платёж. Лучше вернуть ошибку наверх —
        сервис снимет бронь в журнале, и следующий проход попробует снова,
        уже проверив идемпотентность по отпечатку.
        """
        return self.request("POST", path, json_body=json_body, retry_on_server_error=idempotent)

    def put(
        self,
        path: str,
        json_body: Optional[Dict[str, Any]] = None,
        *,
        idempotent: bool = True,
    ) -> Any:
        """PUT перезаписывает состояние целиком, поэтому повтор безопасен."""
        return self.request("PUT", path, json_body=json_body, retry_on_server_error=idempotent)

    def delete(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self.request("DELETE", path, params=params)

    # ------------------------------------------------------------------ #
    # ядро
    # ------------------------------------------------------------------ #
    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        retry_on_server_error: bool = True,
    ) -> Any:
        url = f"{self._settings.api_url}/{path.lstrip('/')}"
        cookies = self._auth.cookies()
        relogin_used = False
        last_error: Optional[Exception] = None
        request_sent = False

        for attempt in range(1, self._settings.max_retries + 1):
            try:
                response = self._session.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    json=json_body,
                    cookies=cookies,
                    timeout=self._settings.timeout,
                    verify=self._settings.verify_ssl,
                )
                request_sent = True
            except requests.exceptions.ConnectTimeout as exc:
                # соединение не установлено — сервер запрос точно не видел
                last_error = UTM5Unavailable(f"UTM5 недоступен ({method} {url}): {exc}")
                self._sleep_before_retry(attempt, f"таймаут подключения: {exc}")
                continue
            except requests.exceptions.RequestException as exc:
                last_error = UTM5Unavailable(f"UTM5 недоступен ({method} {url}): {exc}")
                if not retry_on_server_error and request_sent:
                    raise last_error from exc
                self._sleep_before_retry(attempt, f"сетевая ошибка: {exc}")
                continue

            # сессия истекла — один раз пробуем перелогиниться
            if response.status_code in (401, 403) and not relogin_used:
                relogin_used = True
                logger.warning("UTM5 вернул %s, обновляю сессию", response.status_code)
                cookies = self._auth.refresh()
                continue

            if response.status_code in self.RETRY_STATUSES:
                error = UTM5ServerError(
                    f"UTM5 ответил {response.status_code} на {method} {url}",
                    payload=self._parse_body(response),
                )
                # неидемпотентный запрос повторять нельзя: возможно, он уже применён
                if not retry_on_server_error:
                    logger.error(
                        "UTM5: %s %s вернул %s, повтор запрещён (запрос мог быть применён)",
                        method, url, response.status_code,
                    )
                    raise error
                last_error = error
                self._sleep_before_retry(attempt, f"HTTP {response.status_code}")
                continue

            body = self._parse_body(response)
            raise_for_status(response.status_code, body, url)
            return body

        raise last_error or UTM5Unavailable(f"UTM5: исчерпаны попытки для {method} {url}")

    # ------------------------------------------------------------------ #
    # вспомогательное
    # ------------------------------------------------------------------ #
    def _sleep_before_retry(self, attempt: int, reason: str) -> None:
        if attempt >= self._settings.max_retries:
            return
        delay = self._settings.retry_backoff * (2 ** (attempt - 1))
        logger.warning("UTM5: попытка %s не удалась (%s), повтор через %.1f с", attempt, reason, delay)
        time.sleep(delay)

    @staticmethod
    def _parse_body(response: requests.Response) -> Any:
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            return response.text

    # ------------------------------------------------------------------ #
    def close(self) -> None:
        self._auth.logout()
        self._session.close()