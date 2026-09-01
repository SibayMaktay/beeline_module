"""
Middleware для rate limiting (ограничения частоты запросов).
"""
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, Tuple
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimiter:
    """
    Простой rate limiter на основе скользящего окна.

    Хранит timestamps запросов для каждого клиента и ограничивает
    количество запросов в заданный период времени.
    """

    def __init__(self, requests_per_window: int = 100, window_seconds: int = 60):
        """
        Args:
            requests_per_window: Максимальное количество запросов в окно
            window_seconds: Размер окна в секундах
        """
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = Lock()

    def is_allowed(self, client_id: str) -> Tuple[bool, float]:
        """
        Проверяет, разрешён ли запрос для данного клиента.

        Args:
            client_id: Уникальный идентификатор клиента (IP, API key, etc.)

        Returns:
            Tuple[bool, float]: (разрешено?, секунд до следующего запроса)
        """
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            # Очищаем старые записи
            self._requests[client_id] = [
                ts for ts in self._requests[client_id]
                if ts > window_start
            ]

            # Проверяем лимит
            if len(self._requests[client_id]) >= self.requests_per_window:
                # Вычисляем время до освобождения слота
                oldest_request = min(self._requests[client_id])
                retry_after = oldest_request + self.window_seconds - now
                return False, max(0, retry_after)

            # Добавляем текущий запрос
            self._requests[client_id].append(now)
            return True, 0.0

    def cleanup(self):
        """Очищает старые записи для всех клиентов."""
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            for client_id in list(self._requests.keys()):
                self._requests[client_id] = [
                    ts for ts in self._requests[client_id]
                    if ts > window_start
                ]
                # Удаляем пустые записи
                if not self._requests[client_id]:
                    del self._requests[client_id]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware для применения rate limiting ко всем запросам.

    Исключения:
    - /health, /docs, /redoc, /openapi.json - эндпоинты здоровья и документации
    - Запросы с специальным API ключом (admin)
    """

    def __init__(self, app,
                 requests_per_window: int = 100,
                 window_seconds: int = 60,
                 excluded_paths: list = None,
                 admin_api_key: str = None):
        """
        Args:
            app: FastAPI приложение
            requests_per_window: Максимум запросов в окно
            window_seconds: Размер окна в секундах
            excluded_paths: Список путей, исключённых из rate limiting
            admin_api_key: API ключ, освобождающий от ограничений
        """
        super().__init__(app)
        self.limiter = RateLimiter(requests_per_window, window_seconds)
        self.excluded_paths = excluded_paths or [
            "/health", "/docs", "/redoc", "/openapi.json"
        ]
        self.admin_api_key = admin_api_key

    async def dispatch(self, request: Request, call_next):
        # Проверяем исключения по пути
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.excluded_paths):
            return await call_next(request)

        # Получаем идентификатор клиента (IP адрес)
        client_ip = request.client.host if request.client else "unknown"

        # Проверяем admin API key
        api_key = request.headers.get("X-API-Key")
        if api_key and api_key == self.admin_api_key:
            return await call_next(request)

        # Проверяем rate limit
        allowed, retry_after = self.limiter.is_allowed(client_ip)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests",
                    "retry_after": int(retry_after) + 1
                },
                headers={"Retry-After": str(int(retry_after) + 1)}
            )

        response = await call_next(request)
        return response