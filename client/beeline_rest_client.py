import hmac
import hashlib
import logging
import requests
from typing import Optional, Any, Dict, List

logger = logging.getLogger(__name__)

class BeelineRestClient:
    def __init__(self, base_url: str, signature: Optional[str] = None, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.signature = signature          # секретный ключ для hash (может отсутствовать в демо)
        self.token: Optional[str] = None
        self.timeout = timeout
        self.session = requests.Session()

    # ---------- auth ----------
    def authenticate(self, login: str, password: str) -> bool:
        """
        GET /1.0/auth?login&password -> token (кладём в cookie 'token').
        """
        url = f"{self.base_url}/api/1.0/auth"
        try:
            r = self.session.get(url, params={"login": login, "password": password}, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            self.token = data.get("token") or (data.get("meta") or {}).get("token")
            if self.token:
                self.session.cookies.set("token", self.token)
                logger.info("REST Beeline: token получен")
                return True
            logger.warning(f"REST Beeline: token не найден. Ответ: {r.text[:200]}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"REST Beeline auth ошибка: {e}")
            return False

    # ---------- hash ----------
    def _hash(self, values: List[str]) -> Optional[str]:
        """
        HMAC_SHA1(конкатенация значений, signature) в hex. None если signature не задан.
        """
        if not self.signature:
            return None
        msg = "".join(str(v) for v in values)
        return hmac.new(self.signature.encode(), msg.encode(), hashlib.sha1).hexdigest()

    def _get(self, path: str, params: Dict[str, Any], hash_values: Optional[List[str]] = None) -> Optional[Any]:
        if not self.token:
            logger.error("REST Beeline: нет token, сначала authenticate()")
            return None
        q = dict(params)
        q["token"] = self.token
        if hash_values is not None:
            h = self._hash(hash_values)
            if h:
                q["hash"] = h
        try:
            r = self.session.get(f"{self.base_url}{path}", params=q, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"REST Beeline {path} ошибка: {e}")
            return None

    # ---------- методы ----------
    def get_rests(self, ctn: str) -> Optional[Any]:
        """
        Остатки пакетов (минуты/ГБ/SMS).
        """
        return self._get(
            "/api/1.0/info/rests",
            {
                "ctn": ctn
            },
            hash_values=[ctn]
        )

    def get_subscriptions(self, ctn: str) -> Optional[Any]:
        """
        Активные контент-подписки.
        """
        return self._get(
            "/api/1.0/info/subscriptions",
            {
                "ctn": ctn
            },
            hash_values=[ctn]
        )

    def get_call_forward(self, ctn: str) -> Optional[Any]:
        """
        Параметры переадресации.
        """
        return self._get(
            "/api/1.0/info/callForward",
            {
                "ctn": ctn
            },
            hash_values=[ctn]
        )

    def remove_subscription(self, ctn: str, subscription_id: str) -> Optional[Any]:
        """
        Отключение подписки.
        """
        return self._get(
            "/api/1.0/request/subscription/remove",
            {
                "ctn": ctn,
                "subscriptionId": subscription_id
            },
            hash_values=[ctn, subscription_id],
        )