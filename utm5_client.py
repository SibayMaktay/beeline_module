import config
import requests
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class UTM5Client:
    def __init__(self, base_url: str, login: str, password: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.login = login
        self.password = password
        self.session_id: Optional[str] = None

        self.session = requests.Session()
        self.session.timeout = timeout

    def authenticate(self) -> bool:
        """
        Аутентификация в UTM5 и получение session_id
        """
        if self.session_id:
            return True

        try:
            response = self.session.post(
                f"{self.base_url}/api/login",
                json={'username': self.login, 'password': self.password},
                headers={'Content-Type':'application/json'}
            )
            response.raise_for_status()
            data = response.json()

            self.session_id = data.get('session_id')

            if not self.session_id and 'session_id' in self.session.cookies:
                self.session_id = self.session.cookies['session_id']

            if self.session_id:
                logger.info("Аутентификация в UTM5 успешна")
                return True

            logger.warning("Аутентификация не удалось: sessoin_id не получен в ответе")
            return False

        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP ошибка при аутентификации: {e}. Ответ: {response.text}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Сетевая ошибка аутентификации")
            return False
        except Exception as e:
            logger.error(f"Ошибка получения session_id: {e}")
            return False

    def _ensure_authenticated(self) -> bool:
        """
        Вспомогательный метод: проверяет и выполняет аутентификацию при необходимости
        """
        if not self.session_id:
            return self.authenticate()
        return True

    def get_user_by_phone(self, phone: str) -> Optional[Any]:
        """
        Поиск абонента по номеру телефона
        """
        if not self._ensure_authenticated():
            return None

        try:
            response = self.session.post(
                f"{self.base_url}/api/user/search",
                json = {'query':phone},
                headers = {'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP ошибка при поиске абонента: {e}. Ответ: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Ошибка поиска абонента: {e}")
            return None

    def update_user_balance(self, user_id: int, balance: float) -> Optional[Any]:
        """
        Обновление баланса абонента
        """
        if not self._ensure_authenticated():
            return None

        try:
            response = self.session.post(
                f"{self.base_url}/api/user/{user_id}/balance",
                json={'balance':balance},
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP ошибка при обновлении баланса: {e}. Ответ: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Ошибка обновления баланса: {e}")
            return None

    def change_user_tariff(self, user_id: int, tariff_id: int) -> Optional[Any]:
        """
        Смена тарифа абонента
        """
        if not self._ensure_authenticated():
            return None

        try:
            response = self.session.post(
                f"{self.base_url}/api/user/{user_id}/tariff",
                json={'tariff_id': tariff_id},
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP ошибка при смене тарифа: {e}. Ответ: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Ошибка смены тарифа: {e}")
            return None