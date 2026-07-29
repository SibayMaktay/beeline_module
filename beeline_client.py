import config
from zeep import Client
from zeep.transports import Transport
from requests import  Session
import logging

logger = logging.getLogger(__name__)

class BeelineClient:
    def __init__(self, auth_url: str, subsciber_url: str):
        self.auth_url = auth_url
        self.subsciber_url = subsciber_url
        self.session_id = None

        # Создаем HTTP сессию с таймаутами
        session = Session()
        session.timeout = 30
        transport = Transport(session=session)

        # Инициализируем SOAP клиенты
        self.auth_client = Client(wsdl=self.auth_url, transport=transport)
        self.subsciber_client = Client(wsdl=self.subsciber_url, transport=transport)

    def aurhenticate(self, login: str, password: str) -> bool:
        """
        Аутентификация в системе BeeLine
        """
        try:
            response = self.auth_client.service.auth(
                login = login,
                password = password
            )
            # получение session_id
            if hasattr(response, 'session_id'):
                self.session_id = response.session_id
                logger.info("Аутентификация успешна")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка аутентификации: {e}")
            return False

    def get_subscriber_info(self, phone_namber: str):
        """
        Получение информации об абоненте
        """
        try:
            info = self.subsciber_client.service.getCTNInfoList(
                ctn=phone_namber,
                session_id=self.session_id
            )
            return info
        except Exception as e:
            logger.error(f"Ошибка пполучения информации: {e}")
            return None

    def get_payments(self, account_id: str, start_date: str, end_date: str):
        """
        Получение списка платежей
        """
        try:
            payments = self.subsciber_client.service.getPaymentList(
                ban = account_id,
                startDate = start_date,
                endData = end_date,
                session_id = self.session_id
            )
            return payments
        except Exception as e:
            logger.error(f"Ошибка получения платежей: {e}")
            return None

    def get_bill_charges(self, account_id: str, start_date: str, end_date: str):
        """
        Получение начислений
        """
        try:
            charges = self.subsciber_client.service.getBillCharges(
                ban = account_id,
                startDate = start_date,
                endDate = end_date,
                session_id = self.session_id
            )
            return charges
        except Exception as e:
            logger.error(f"Ошибка получения начислений: {e}")
            return None

    def change_tariff(self, phone_numder: str, new_tariff_code: str):
        """
        Смена тарифного плана
        """
        try:
            result = self.subsciber_client.service.changePP(
                ctn = phone_numder,
                newPPCode = new_tariff_code,
                session_id = self.session_id
            )
            logger.info(f"Тариф изменен для {phone_numder}")
            return result
        except Exception as e:
            logger.error(f"Ошибка смены тарифа: {e}")
            return None

    def get_services(self, phone_number: str):
        """
        Получение списка услуг
        """
        try:
            services = self.subsciber_client.service.getServicesList(
                ctn = phone_number,
                session_id = self.session_id
            )
            return services
        except Exception as e:
            logger.error(f"Ошибка получения услуг: {e}")
            return None