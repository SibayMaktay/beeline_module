import hmac
import hashlib
import logging
import requests
from typing import Optional, Any, Dict, List

logger = logging.getLogger(__name__)

class BeelineRestClient:
    def __init__(
        self,
        base_url: str,
        signature: Optional[str] = None,
        token: Optional[str] = None,
        timeout: int = 30
    ):
        self.base_url = base_url.rstrip('/')
        self.signature = signature          # секретный ключ для hash (может отсутствовать в демо)
        self.token = token
        self.timeout = timeout
        self.session = requests.Session()

    # ---------- auth ----------
    def set_token(self, token: str):
        """
        Позволяет передавать токен извне.
        """
        self.token = token
        self.session.cookies.set("token", token)

    def _hash(self, values: List[str]) -> Optional[str]:
        if not self.signature:
            return None
        msg = "".join(str(v) for v in values)
        return hmac.new(self.signature.encode(), msg.encode(), hashlib.sha1).hexdigest()

    def _get(
        self,
        path: str,
        params: Dict[str, Any],
        hash_values: Optional[List[str]] = None
    ) -> Optional[Any]:
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
    def get_rests(
        self,
        ctn: str,
        client: Optional[str] = None
    ) -> Optional[Any]:
        """
        Остатки пакетов (минуты/ГБ/SMS).
        """
        return self._get(
            "/api/1.0/info/rests",
            {
                "ctn": ctn,
                "client": client
            },
            hash_values=[ctn]
        )

    def get_subscriptions(
        self,
        ctn: str,
        client: Optional[str] = None
    ) -> Optional[Any]:
        """
        Активные контент-подписки.
        """
        return self._get(
            "/api/1.0/info/subscriptions",
            {
                "ctn": ctn,
                "client": client
            },
            hash_values=[ctn]
        )

    def remove_subscription(
        self,
        ctn: str,
        subscription_id: str = None,
        type: str = None,
        client: Optional[str] = None
    ) -> Optional[Any]:
        """
        Отключение подписки.
        """
        return self._get(
            "/api/1.0/request/subscription/remove",
            {
                "ctn": ctn,
                "subscriptionId": subscription_id,
                "type": type,
                "client": client
            },
            hash_values=[ctn, subscription_id],
        )

    def request_call_forward(
        self,
        ctn: str,
        client: Optional[str] = None
    ) -> Optional[Any]:
        """
        Шаг 1. Создать запрос на получение параметров переадресации (GET /1.0/request/callForward).
        Возвращает: {"requestId": integer}
        """
        params = {
            "ctn": ctn,
        }
        if client:
            params["client"] = client
        return self._get(
            "/api/1.0/request/CallForward",
            params,
            hash_values=[ctn]
        )

    def get_call_forward_by_request(
        self,
        request_id: int,
        client: Optional[str] = None
    ) -> Optional[Any]:
        """
        Шаг 2. Получить параметры переадресации (GET /api/1.0/info/callForward?requestId=...).
        Возвращает параметры переадресации по requestId.
        """
        params = {
            "requestId": request_id,
        }
        if client:
            params["client"] = client
        return self._get(
            "/api/1.0/info/callForward",
            params,
            hash_values=[str(request_id)]
        )

    def edit_call_forward(
        self,
        ctn: str,
        call_forward_edit_request: list,
        call_forward: list,
        cf_type: str = None,
        cf_ctn: str = None,
        client: Optional[str] = None
    ) -> Optional[Any]:
        """
        Шаг 3. Установить параметры переадресации (PUT /1.0/request/callForward/edit).
        call_forward_list — список словарей с cfType/cfCtn и т.д.
        Возвращает: {"requestId": integer}
        """
        if not self.token:
            logger.error("REST Beeline: нет token, сначала authenticate()")
            return None
        params = {
            "token": self.token,
            "ctn": ctn,
        }
        if client:
            params["client"] = client
        if self.signature:
            h = self._hash([ctn])
            if h:
                params["hash"] = h
        data = {
            "CallForwardEditRequestDO": call_forward_edit_request,
            "CallForwardDO": call_forward,
            "cfType": cf_type,
            "cfCtn": cf_ctn
        }
        try:
            r = self.session.put(
                f"{self.base_url}/api/1.0/request/callForward/edit",
                params=params,
                json=data,
                timeout=self.timeout
            )
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"REST Beeline /api/1.0/request/callForward/edit ошибка: {e}")
            return None