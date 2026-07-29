import requests
import json
import logging

logger = logging.getLogger(__name__)

class UTM5Client:
    def __init__(self, base_url: str, login: str, password: str):
        self.base_url = base_url.rstrip('/')
        self.login = login
        self.password = password
        self.session_id = None

    def _get_session_id(self) -> str:
        """
        Получение session_id для UTM5
        """
        if self.session_id:
            return self.session_id

        try:
            response = requests.post(
                f"{self.base_url}/api/login",
                json={'username': self.login, 'password': self.password},
                headers={'Content-Type':'application/json'}
            )
            data = response.json()
            self.session_id = data.get('session_id')
            return self.session_id
        except Exception as e:
            return None

    def get_user_by_phone(self, phone: str):
        """
        Поиск абонента по номеру телефона
        """
        session_id = self._get_session_id()
        if not session_id:
            return None

        try:
            response = requests.get(
                f"{self.base_url}/api/user/searche",
                params = {'query':phone},
                headers = {'Cookie': f'session_id={session_id}'}
            )
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка поиска абонента: {e}")
            return None

    def update_user_balance(self, user_id: int, balance: float):
        """
        Обновление баланса абонента
        """
        session_id = self.session_id()
        if not session_id:
            return None

        try:
            response = requests.post(
                f"{self.base_url}/api/user/{user_id}/balance",
                json={'balance':balance},
                headers={
                    'Cookie': f'session_id={session_id}',
                    'Content_Type': 'application/json'
                }
            )
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка обновления баланса: {e}")
            return None

    def change_user_tariff(self, user_id: int, tariff_id: int):
        """
        Смена тарифа абонента
        """
        session_id = self.session_id()
        if not session_id:
            return None

        try:
            response = requests.post(
                f"{self.base_url}/api/user/{user_id}/tariff",
                json={'tariff_id': tariff_id},
                headers={
                    'Cookie': f'session_id={session_id}',
                    'Content-Type': 'application/json'
                }
            )
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка смены тарифа: {e}")
            return None