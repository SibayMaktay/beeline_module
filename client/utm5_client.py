import requests
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class UTM5Client:
    def __init__(self, base_url: str, session_id_provider: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.session_id_provider = session_id_provider
        self.session = requests.Session()
        self.session.timeout = timeout

    def _get_session_id(self):
        return self.session_id_provider()

    def get_user_by_phone(self, phone: str) -> Optional[Any]:
        session_id = self.session_id_provider()
        if not session_id:
            return None
        try:
            response = self.session.post(
                f"{self.base_url}/api/user/search",
                json = {'query':phone},
                headers = {'Content-Type': 'application/json', 'Authorization': f'Session {session_id}'}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка поиска абонента: {e}")
            return None

    def update_user_balance(self, user_id: int, balance: float) -> Optional[Any]:
        session_id = self.session_id_provider()
        if not session_id:
            return None
        try:
            response = self.session.post(
                f"{self.base_url}/api/user/{user_id}/balance",
                json={'balance':balance},
                headers={'Content-Type': 'application/json', 'Authorization': f'Session {session_id}'}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка обновления баланса: {e}")
            return None

    def change_user_tariff(self, user_id: int, tariff_id: int) -> Optional[Any]:
        session_id = self.session_id_provider()
        if not session_id:
            return None
        try:
            response = self.session.post(
                f"{self.base_url}/api/user/{user_id}/tariff",
                json={'tariff_id': tariff_id},
                headers={'Content-Type': 'application/json', 'Authorization': f'Session {session_id}'}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Ошибка смены тарифа: {e}")
            return None