import config
import requests
import logging
from zeep import Client
from zeep.transports import Transport
from zeep.exceptions import Fault
from typing import Optional, Any

logger = logging.getLogger(__name__)

# url = f"{config.beeline_url_base}/api/1.0/auth"

# querystring = {"login":config.beeline_login,"password":config.beeline_password}

# payload = ""
# headers = ""

# response = requests.get(url, data=payload, headers=headers, params=querystring)

# print(response.json())

# url = f"{config.beeline_url_base}/api/AuthService"

# payload = f"<soapenv:Envelope\n\txmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\"\n\txmlns:urn=\"urn:uss-wsapi:Auth\">\n\t<soapenv:Header/>\n\t<soapenv:Body>\n\t\t<urn:auth>\n\t\t\t<login>{config.beeline_login}</login>\n\t\t\t<password>{config.beeline_password}</password>\n\t\t</urn:auth>\n\t</soapenv:Body>\n</soapenv:Envelope>"
# headers = {
#     "Content-Type": "text/xml",
#     "SUAPAction": "\"urn:uss-wsapi:Auth:AuthInterface:authRequest\""
# }

# response = requests.post(url, data=payload, headers=headers)

# print(response.text)

class BeelineClient:
    def __init__(self, auth_url: str, subscriber_url: str, timeout: int = 30):
        self.auth_url = auth_url
        self.subscriber_url = subscriber_url
        self.session_id = Optional[str] = None

        # Создаем HTTP сессию с таймаутами
        session = requests.Session()
        transport = Transport(session=session, timeout=timeout)

        # Инициализируем SOAP клиенты
        self.auth_client = Client(wsdl=self.auth_url, transport=transport)
        self.subscriber_client = Client(wsdl=self.subscriber_url, transport=transport)

    def authenticate(self, login: str, password: str) -> bool:
        """
        Аутентификация в системе BeeLine
        """
        try:
            response = self.auth_client.service.auth(login = login, password = password)
            # получение session_id
            if isinstance(response, str):
                self.session_id = response
            elif hasattr(response, 'return_'):
                self.session_id = response.return_
            else:
                self.session_id = str(response)

            if self.session_id and len(self.session_id) > 5:
                logger.info("Аутентификация успешна, получен sesion_id")
                return True
            return False
        except Fault as e:
            logger.error(f"SOAP Fault при аутентификации: {e.message}")
            return False
        except Exception as e:
            logger.error(f"Ошибка аутентификации: {e}")
            return False

    def get_subscriber_info(self, phone_number: str) -> Optional[Any]:
        """
        Получение информации об абоненте
        """
        if not self.session_id:
            logger.error("Отсутствует session_id. Выполните аутенификацию.")
            return None
        try:
            return self.subscriber_client.service.getCTNInfoList(
                ctn=phone_number,
                session_id=self.session_id
            )
        except Fault as e:
            logger.error(f"SOAP Fault при получнеии инфо об абоненте: {e.message}")
            return None
        except Exception as e:
            logger.error(f"Ошибка пполучения информации: {e}")
            return None

    def get_payments(self, account_id: str, start_date: str, end_date: str) -> Optional[Any]:
        """
        Получение списка платежей
        """
        if not self.session_id:
            logger.error("Отсутствует session_id. Выполните аутенификацию.")
            return None
        try:
            return self.subscriber_client.service.getPaymentList(
                ban = account_id,
                startDate = start_date,
                endDate = end_date,
                session_id = self.session_id
            )
        except Fault as e:
            logger.error(f"SOAP Fault при получнеии платежей: {e.message}")
            return None
        except Exception as e:
            logger.error(f"Ошибка получения платежей: {e}")
            return None

    def get_bill_charges(self, account_id: str, start_date: str, end_date: str) -> Optional[Any]:
        """
        Получение начислений
        """
        if not self.session_id:
            logger.error("Отсутствует session_id. Выполните аутенификацию.")
            return None
        try:
            return self.subscriber_client.service.getBillCharges(
                ban=account_id,
                startDate=start_date,
                endDate=end_date,
                session_id=self.session_id
            )
        except Fault as e:
            logger.error(f"SOAP Fault при получнеии начислений: {e.message}")
            return None
        except Exception as e:
            logger.error(f"Ошибка получения начислений: {e}")
            return None

    def change_tariff(self, phone_number: str, new_tariff_code: str) -> Optional[Any]:
        """
        Смена тарифного плана
        """
        if not self.session_id:
            logger.error("Отсутствует session_id. Выполните аутенификацию.")
            return None
        try:
            result = self.subscriber_client.service.changePP(
                ctn = phone_number,
                newPPCode = new_tariff_code,
                session_id = self.session_id
            )
            logger.info(f"Тариф изменен для {phone_number}")
            return result
        except Fault as e:
            logger.error(f"SOAP Fault при смене тарифа: {e.message}")
            return None
        except Exception as e:
            logger.error(f"Ошибка смены тарифа: {e}")
            return None

    def get_services(self, phone_number: str) -> Optional[Any]:
        """
        Получение списка услуг
        """
        if not self.session_id:
            logger.error("Отсутствует session_id. Выполните аутенификацию.")
            return None
        try:
            return self.subscriber_client.service.getServicesList(
                ctn=phone_number,
                session_id=self.session_id
            )
        except Fault as e:
            logger.error(f"SOAP Fault при получении услуг: {e.message}")
            return None
        except Exception as e:
            logger.error(f"Ошибка получения услуг: {e}")
            return None