import requests
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class UTM5Client:
    def __init__(self, base_url: str, api_key: str = None, session_id: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session_id = session_id
        self.session = requests.Session()

    def _headers(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-Api-Auth"] = self.api_key
        elif self.session_id:
            headers["Authorization"] = f"Session {self.session_id}"
        return headers

    def search_user_by_phone(self, phone: str) -> Optional[Any]:
        response = self.session.post(
            f"{self.base_url}/api/user/search",
            json={"query": phone},
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        users = response.json()
        return user.get("items", []) or users

    def pay_user(self, user_id: int, amount: float, comment="integration sync"):
        response = self.session.post(
            f"{self.base_url}/api/user/{user_id}/pay",
            json={"amount": float(amount), "comment": comment},
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def change_tariff(self, user_id: int, tariff_id: int):
        response = self.session.post(
            f"{self.base_url}/api/user/{user_id}/tariff",
            json={"tariff_id": tariff_id},
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()