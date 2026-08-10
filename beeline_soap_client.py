import logging
import requests
from typing import Optional, Any, Dict
import config
from token_beeline import get_beeline_token, invalidate_token
from wsdl_template_beeline import (
    get_ctn_info_template,
    get_payment_list_template,
    change_pp_template,
    get_unbilled_balance_template,
    manage_service_template,
    suspend_ctn_template,
    restore_ctn_template,
    replace_sim_template
)

logger = logging.getLogger(__name__)

def _make_soap_request(xml_payload: str, action: str) -> Optional[Any]:
    """
    Внутренний универсальный метод отправки SOAP.
    """
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f'"{action}"'
    }

    try:
        response = requests.post(
            f"{config.beeline_url_base}/api/SubscriberService",
            data=xml_payload,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        try:
            import xmltodict
            result = xmltodict.parse(response.content)
            return result.get('soap:Envelope', {}).get('soap:Body', {})
        except ImportError:
            logger.warning("Установите 'xmltodict' для удобного парсинга.")
            return {"raw_xml": response.text}
            
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP ошибка SOAP: {e}. Ответ: {response.text[:200]}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Сетевая ошибка при запросе {action}: {e}")
        return None
    except Exception as e:
        logger.error(f"Ошибка запроса {action}: {e}", exc_info=True)
        return None

def get_subscriber_info(self, phone_number: str) -> Optional[Any]:
    """
    Получение информации об абоненте и балансе.
    """
    token = get_beeline_token()
    xml = get_ctn_info_template(phone_number, token)
    return self._make_soap_request(
        xml,
        "urn:uss-wsapi:Subscriber:SubscriberInterface:getCTNInfoListRequest"
    )

def get_payments(self, ban: str, start_date: str, end_date: str) -> Optional[Any]:
    """
    Получение списка платежей.
    """
    token = get_beeline_token()
    xml = get_payment_list_template(ban, start_date, end_date, token)
    return _make_soap_request(
        xml,
        "urn:uss-wsapi:Subscriber:SubscriberInterface:getPaymentListRequest"
    )

def change_tariff(self, phone_number: str, new_tariff_code: str) -> Optional[Any]:
    """
    Смена тарифного плана.
    """
    token = get_beeline_token()
    xml = change_pp_template(phone_number, new_tariff_code, token)
    return _make_soap_request(
        xml,
        "urn:uss-wsapi:Subscriber:SubscriberInterface:changePPRequest"
    )
def get_unbilled_balances(self, ban: str) -> Optional[Any]:
    """
    Небиллингованный баланс лицевого счёта (getUnbilledBalances).
    """
    token = get_beeline_token()
    xml = get_unbilled_balance_template(ban, token)
    return _make_soap_request(
        xml,
        "urn:uss-wsapi:Subscriber:SubscriberInterface:getUnbilledBalancesRequest"
    )

def manage_service(self, phone_number: str, soc_code: str, add: bool = True) -> Optional[Any]:
    """
    Подключение/отключение услуги (addDelSOC). add=True — подключить, False — отключить.
    """
    token = get_beeline_token()
    xml = manage_service_template(phone_number, soc_code, add, token)
    return _make_soap_request(
        xml,
        "urn:uss-wsapi:Subscriber:SubscriberInterface:addDelSOCRequest"
    )

def suspend_ctn(self, phone_number: str) -> Optional[Any]:
    """
    Добровольная блокировка номера (suspendCTN).
    """
    token = get_beeline_token()
    xml = suspend_ctn_template(phone_number, token)
    return _make_soap_request(
        xml,
        "urn:uss-wsapi:Subscriber:SubscriberInterface:suspendCTNRequest"
    )

def restore_ctn(self, phone_number: str) -> Optional[Any]:
    """
    Снятие блокировки номера (restoreCTN).
    """
    token = get_beeline_token()
    xml = restore_ctn_template(phone_number, token)
    return _make_soap_request(
        xml,
        "urn:uss-wsapi:Subscriber:SubscriberInterface:restoreCTNRequest"
    )

def replace_sim(self, phone_number: str, new_sim: str) -> Optional[Any]:
    """
    Замена SIM-карты (replaceSIM).
    """
    token = get_beeline_token()
    xml = replace_sim_template(phone_number, new_sim, token)
    return self._make_soap_request(
        xml,
        "urn:uss-wsapi:Subscriber:SubscriberInterface:restoreCTNRequest"
    )