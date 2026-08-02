import logging
import requests
from typing import Optional, Any
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class BeelineClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.session_id: Optional[str] = None
        self.timeout = timeout
        
        # Используем сессию для переиспользования TCP-соединений (keep-alive)
        self.session = requests.Session()
        self.session.timeout = timeout

    def authenticate(self, login: str, password: str) -> bool:
        """
        Аутентификация в системе Beeline через SOAP
        """
        url = f"{self.base_url}/api/AuthService"
        
        payload = f"""<soapenv:Envelope
        xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:urn="urn:uss-wsapi:Auth">
        <soapenv:Header/>
        <soapenv:Body>
            <urn:auth>
                <login>{login}</login>
                <password>{password}</password>
            </urn:auth>
        </soapenv:Body>
        </soapenv:Envelope>"""
        
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SUAPAction": '"urn:uss-wsapi:Auth:AuthInterface:authRequest"'
        }
        
        try:
            response = self.session.post(url, data=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            # Парсим XML ответ для извлечения токена
            root = ET.fromstring(response.content)
            
            # Ищем тег <return> в любом пространстве имен
            token = None
            for elem in root.iter():
                if elem.tag.endswith('return'):
                    token = elem.text
                    break
                    
            if token and len(token) > 5:
                self.session_id = token
                logger.info("Аутентификация Beeline успешна, получен session_id")
                return True
                
            logger.warning(f"Аутентификация не удалась: токен не найден. Ответ: {response.text[:200]}")
            return False
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP ошибка при аутентификации Beeline: {e}. Ответ: {response.text[:200]}")
            return False
        except ET.ParseError as e:
            logger.error(f"Ошибка парсинга XML ответа Beeline: {e}. Ответ: {response.text[:200]}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка аутентификации Beeline: {e}")
            return False

    def _make_soap_request(self, endpoint: str, action: str, body_params: dict, namespace: str = "urn:uss-wsapi:Subscriber") -> Optional[Any]:
        """
        Универсальный метод для отправки SOAP запросов
        """
        if not self.session_id:
            logger.error("Отсутствует session_id. Выполните аутентификацию.")
            return None
            
        url = f"{self.base_url}/api/{endpoint}"
        
        # Формируем параметры для тела SOAP
        params_xml = "".join([f"<{k}>{v}</{k}>" for k, v in body_params.items()])
        
        payload = f"""<soapenv:Envelope
        xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:urn="{namespace}">
        <soapenv:Header/>
        <soapenv:Body>
            <urn:{action}>
                {params_xml}
                <token>{self.session_id}</token>
            </urn:{action}>
        </soapenv:Body>
        </soapenv:Envelope>"""
        
        # SOAPAction может отличаться для разных методов, это шаблон
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"urn:uss-wsapi:Subscriber:SubscriberInterface:{action}"'
        }
        
        try:
            response = self.session.post(url, data=payload, headers=headers, timeout=self.timeout)
            response.raise_for_status()
            
            # Простой парсинг XML в словарь для удобства работы (требует xmltodict)
            try:
                import xmltodict
                return xmltodict.parse(response.content)
            except ImportError:
                logger.warning("Модуль 'xmltodict' не установлен. Возвращаю сырой XML текст. Установите: pip install xmltodict")
                return response.text
                
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP ошибка при запросе {action}: {e}. Ответ: {response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"Ошибка запроса {action}: {e}")
            return None

    def get_subscriber_info(self, phone_number: str) -> Optional[Any]:
        return self._make_soap_request("SubscriberService", "getCTNInfoList", {"ctn": phone_number})

    def get_payments(self, account_id: str, start_date: str, end_date: str) -> Optional[Any]:
        return self._make_soap_request("SubscriberService", "getPaymentList", {
            "ban": account_id,
            "startDate": start_date,
            "endDate": end_date
        })

    def change_tariff(self, phone_number: str, new_tariff_code: str) -> Optional[Any]:
        return self._make_soap_request("SubscriberService", "changePP", {
            "ctn": phone_number,
            "newPPCode": new_tariff_code
        })