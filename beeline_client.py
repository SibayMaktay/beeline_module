import logging
import requests
from typing import Optional, Any, Dict
import xml.etree.ElementTree as ET

try:
    import xmltodict
    HAS_XMLTODICT = True
except ImportError:
    HAS_XMLTODICT = False
    logging.getLogger(__name__).warning("Модуль 'xmltodict' не найден. Установите: pip install xmltodict")

logger = logging.getLogger(__name__)

class BeelineClient:
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.session_id: Optional[str] = None
        self.timeout = timeout
        
        # Используем сессию для переиспользования TCP-соединений (keep-alive)
        self.session = requests.Session()
        self.session.timeout = timeout

    def _build_soap_envelope(self, interface: str, action: str, body_params: Dict[str, Any]) -> str:
        """
        Безопасная сборка SOAP-конверта с защитой от XML-инъекций
        """
        root = ET.Element(
            "soapenv:Envelope",
            attrib={
                "xmlns:soapenv": "http://schemas.xmlsoap.org/soap/envelope/",
                "xmlns:urn": f"urn:uss-wsapi:{interface}"
            }
        )
        ET.SubElement(root, "soapenv:Header")
        body = ET.SubElement(root, "soapenv:Body")
        action_elem = ET.SubElement(body, f"urn:{action}")

        for key, value in body_params.items():
            param = ET.SubElement(action_elem, key)
            param.text = str(value)

        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding='unicode')

    def authenticate(self, login: str, password: str) -> bool:
        """
        Аутентификация в системе Beeline через SOAP
        """
        url = f"{self.base_url}/api/AuthService"

        payload = self._build_soap_envelope("Auth", "auth", {
            "login": login,
            "password": password
        })
        
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": '"urn:uss-wsapi:Auth:AuthInterface:authRequest"'
        }
        
        try:
            response = self.session.post(url, data=payload, headers=headers)
            response.raise_for_status()
            
            # Парсим XML ответ для извлечения токена
            root = ET.fromstring(response.content)
            
            # Ищем тег <return> в любом пространстве имен
            token = None
            for elem in root.iter():
                if elem.tag.endswith('return') or elem.tag.endswith('session_id'):
                    token = elem.text
                    break

            if token and len(str(token).strip()) > 5:
                self.session_id = str(token).strip()
                logger.info("Аутентификация Beeline успешна, получен session_id")
                return True
                
            logger.warning(f"Аутентификация не удалась: токен не найден. Ответ: {response.text[:200]}")
            return False
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP ошибка при аутентификации Beeline: {e}. Ответ: {response.text[:200]}")
            return False
        except ET.ParseError as e:
            logger.error(f"Ошибка парсинга XML ответа: {e}. Ответ: {response.text[:200]}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Сетевая ошибка при аутентификации (таймаут, DNS и т.д.): {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка аутентификации Beeline: {e}")
            return False

    def _make_soap_request(self, interface: str, endpoint: str, action: str, namespace: str, body_params: Dict[str, Any]) -> Optional[Any]:
        """
        Универсальный метод для отправки SOAP запросов
        """
        if not self.session_id:
            logger.error("Отсутствует session_id. Выполните аутентификацию.")
            return None
            
        url = f"{self.base_url}/api/{endpoint}"

        requests_params = body_params.copy()
        requests_params["return"] = self.session_id

        payload = self._build_soap_envelope(interface, action, requests_params)

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"urn:uss-wsapi:{interface}:{interface}Interface:{action}Request"'
        }

        try:
            response = self.session.post(url, data=payload, headers=headers)
            response.raise_for_status()

            if HAS_XMLTODICT:
                return response.text
                
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP ошибка при запросе {action}: {e}. Ответ: {response.text[:200]}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Сетевая ошибка при запросе {action}: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка запроса {action}: {e}", exc_info=True)
            return None

    def get_subscriber_info(self, phone_number: str) -> Optional[Any]:
        return self._make_soap_request(
            interface="Subscriber",
            endpoint="SubscriberService",
            action="getCTNInfoList",
            body_params={
                "ctn": phone_number
            }
        )

    def get_payments(self, account_id: str, start_date: str, end_date: str) -> Optional[Any]:
        return self._make_soap_request(
            interface="Subscriber",
            endpoint="SubscriberService",
            action="getPaymentList",
            body_params={
                "ban": account_id,
                "startDate": start_date,
                "endDate": end_date
            }
        )

    def change_tariff(self, phone_number: str, new_tariff_code: str) -> Optional[Any]:
        return self._make_soap_request(
            interface="Subscriber",
            endpoint="SubscriberService",
            action="changePP",
            body_params={
                "ctn": phone_number,
                "newPPCode": new_tariff_code
            }
        )
    def get_unbilled_balances(self, account_id: str) -> Optional[Any]:
        """
        Небиллингованный баланс лицевого счёта (getUnbilledBalances).
        """
        return self._make_soap_request(
            interface="Subscriber",
            endpoint="SubscriberService",
            action="getUnbilledBalances",
            body_params={
                "ban": account_id
            }
        )

    def manage_service(self, phone_number: str, soc_code: str, add: bool = True) -> Optional[Any]:
        """
        Подключение/отключение услуги (addDelSOC). add=True — подключить, False — отключить.
        """
        return self._make_soap_request(
            interface="Subscriber",
            endpoint="SubscriberService",
            action="addDelSOC",
            body_params={
                "ctn": phone_number,
                "soc": soc_code,
                "action": "ADD" if add else "DEL"
            }
        )

    def suspend_ctn(self, phone_number: str) -> Optional[Any]:
        """
        Добровольная блокировка номера (suspendCTN).
        """
        return self._make_soap_request(
            interface="Subscriber",
            endpoint="SubscriberService",
            action="suspendCTN",
            body_params={
                "ctn": phone_number
            }
        )

    def restore_ctn(self, phone_number: str) -> Optional[Any]:
        """
        Снятие блокировки номера (restoreCTN).
        """
        return self._make_soap_request(
            interface="Subscriber",
            endpoint="SubscriberService",
            action="restoreCTN",
            body_params={
                "ctn": phone_number
            }
        )

    def replace_sim(self, phone_number: str, new_sim: str) -> Optional[Any]:
        """
        Замена SIM-карты (replaceSIM).
        """
        return self._make_soap_request(
            interface="Subscriber",
            endpoint="SubscriberService",
            action="replaceSIM",
            body_params={
                "ctn": phone_number,
                "newSIM": new_sim
            }
        )