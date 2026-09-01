"""
Модуль для управления токенами Beeline с автоматическим refresh.
"""
import logging
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional
from threading import Lock

import config.config as config
from templates.wsdl_template_beeline import get_auth_template

logger = logging.getLogger(__name__)


class TokenManager:
    """
    Менеджер токенов Beeline с поддержкой автоматического обновления.

    Реализует:
    - Кеширование токена в памяти
    - Автоматический refresh перед истечением
    - Потокобезопасность через Lock
    - Два метода аутентификации (SOAP и REST)
    """

    # Время жизни токена (предполагаемое, можно настроить)
    TOKEN_LIFETIME_SECONDS = 3600  # 1 час

    # Буфер времени для обновления токена до истечения
    REFRESH_BUFFER_SECONDS = 300  # 5 минут

    def __init__(self):
        self._token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._lock = Lock()

    def get_token(self) -> str:
        """
        Получает токен Beeline с автоматическим обновлением при необходимости.

        Returns:
            str: Активный токен доступа

        Raises:
            Exception: Если не удалось получить токен ни одним из методов
        """
        with self._lock:
            # Проверяем, нужен ли refresh
            if self._needs_refresh():
                logger.info("Токен требует обновления или отсутствует")
                self._refresh_token()

            if not self._token:
                raise Exception("Не удалось получить токен Beeline.")

            return self._token

    def invalidate_token(self) -> None:
        """
        Принудительно инвалидирует текущий токен.
        """
        with self._lock:
            self._token = None
            self._token_expires_at = None
            logger.info("Токен Beeline аннулирован принудительно.")

    def _needs_refresh(self) -> bool:
        """
        Проверяет, требуется ли обновление токена.

        Returns:
            bool: True если токен отсутствует или скоро истечёт
        """
        if not self._token or not self._token_expires_at:
            return True

        # Обновляем за 5 минут до истечения
        refresh_threshold = datetime.utcnow() + timedelta(seconds=self.REFRESH_BUFFER_SECONDS)
        return self._token_expires_at <= refresh_threshold

    def _refresh_token(self) -> None:
        """
        Выполняет обновление токена используя доступные методы.
        """
        logger.info("Попытка аутентификации в Beeline...")

        # Пробуем SOAP метод
        token = self._authenticate_soap()
        if token:
            self._set_token(token)
            logger.info("Аутентификация Beeline успешна через SOAP.")
            return

        # Пробуем REST метод
        token = self._authenticate_rest()
        if token:
            self._set_token(token)
            logger.info("Аутентификация Beeline успешна через REST API.")
            return

        logger.error("Все методы аутентификации Beeline не удались.")
        raise Exception("Не удалось получить токен Beeline.")

    def _authenticate_soap(self) -> Optional[str]:
        """
        Аутентификация через raw SOAP запрос.

        Returns:
            Optional[str]: Токен или None если не удалось
        """
        try:
            logger.debug("Попытка SOAP аутентификации...")
            xml_payload = get_auth_template(config.beeline_login, config.beeline_password)
            headers = {
                "Content-Type": "text/xml",
                "SOAPAction": '"urn:uss-wsapi:Auth:AuthInterface:authRequest"'
            }
            response = requests.post(
                f"{config.beeline_url_base}/api/AuthService",
                data=xml_payload,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()

            root = ET.fromstring(response.content)
            for elem in root.iter():
                if (elem.tag.endswith('return') or elem.tag.endswith('session_id')) and elem.text:
                    if len(elem.text) > 5:
                        logger.debug("SOAP аутентификация вернула токен.")
                        return elem.text

            logger.warning("Токен не найден в SOAP ответе.")
            return None

        except Exception as e:
            logger.warning(f"SOAP аутентификация не удалась: {e}")
            return None

    def _authenticate_rest(self) -> Optional[str]:
        """
        Аутентификация через REST API.

        Returns:
            Optional[str]: Токен или None если не удалось
        """
        try:
            logger.debug("Попытка REST API аутентификации...")
            rest_url = (
                f"{config.beeline_url_base}/api/1.0/auth"
                f"?login={config.beeline_login}&password={config.beeline_password}"
            )
            resp = requests.get(rest_url, timeout=15)
            resp.raise_for_status()

            data = resp.json()
            token = data.get("token") or data.get("session_id") or data.get("return")

            if token:
                logger.debug("REST API аутентификация вернула токен.")
                return token

            logger.warning("Токен не найден в REST API ответе.")
            return None

        except Exception as e:
            logger.warning(f"REST API аутентификация не удалась: {e}")
            return None

    def _set_token(self, token: str) -> None:
        """
        Устанавливает токен и вычисляет время его истечения.

        Args:
            token: Новый токен доступа
        """
        self._token = token
        self._token_expires_at = datetime.utcnow() + timedelta(seconds=self.TOKEN_LIFETIME_SECONDS)
        logger.debug(f"Токен установлен, истекает в {self._token_expires_at.isoformat()}")


# Глобальный экземпляр менеджера токенов
_token_manager = TokenManager()


def get_beeline_token() -> str:
    """
    Получает токен Beeline через глобальный менеджер токенов.

    Returns:
        str: Активный токен доступа
    """
    return _token_manager.get_token()


def invalidate_token() -> None:
    """
    Инвалидирует текущий токен Beeline.
    """
    _token_manager.invalidate_token()
