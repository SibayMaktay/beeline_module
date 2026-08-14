import logging
import requests
from typing import Optional, Any, Dict
import config.config as config
from token_api.token_beeline import get_beeline_token, invalidate_token
from templates.wsdl_template_beeline import *

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

class BeelineSoapClient:
    def __init__(self, token_provider):
        self.token_provider = token_provider

    def get_ctn_info_list(
        self,
        ban: str,
        ctn: str = None
    ) -> Optional[Any]:
        """
        Получения информации об абонентах на уровне BAN/CTN.
        """
        session_id = self.token_provider() # get_beeline_token()
        xml = get_ctn_info_list_template(
            ban=ban,
            session_id=session_id,
            ctn=ctn,
            login=config.beeline_login
        )
        return self._make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getCTNInfoListRequest"
        )

    def get_ctn_info_list_paged(
        self,
        ban: str,
        ctn: str = None,
        page: int = None,
        records_per_page: str = None
    ) -> Optional[Any]:
        """
        Получения информации об абонентах на уровне BAN/CTN.
        """
        session_id = self.token_provider()
        xml = get_ctn_info_list_paged_template(
            ban=ban,
            session_id=session_id,
            ctn=ctn,
            page=page,
            records_per_page=records_per_page,
            login=config.beeline_login
        )
        return self._make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getCTNInfoListRequest"
        )

    def get_payment_list(
        self,
        ban: str,
        start_date: str,
        end_date: str,
        ctn: str
    ) -> Optional[Any]:
        """
        Получение списка платежей.
        """
        session_id = self.token_provider()
        xml = get_payment_list_template(
            ban=ban,
            start_date=start_date,
            end_date=end_date,
            ctn=ctn,
            session_id=session_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getPaymentListRequest"
        )

    def get_payment_list_paged(
        self,
        ban: str,
        start_date: str,
        end_date: str,
        ctn: str,
        page: int = None,
        records_per_page: str = None
    ) -> Optional[Any]:
        """
        Получение списка платежей.
        """
        session_id = self.token_provider()
        xml = get_payment_list_paged_template(
            ban=ban,
            start_date=start_date,
            end_date=end_date,
            ctn=ctn,
            session_id=session_id,
            login=config.beeline_login,
            page=page,
            records_per_page=records_per_page
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getPaymentListRequest"
        )

    def change_pp(
        self,
        ctn: str,
        price_plan: str,
        future_date: str = None,
        free_change: str = None
    ) -> Optional[Any]:
        """
        Смена тарифного плана.
        """
        session_id = self.token_provider()
        xml = change_pp_template(
            ctn=ctn,
            price_plan=price_plan,
            session_id=session_id,
            future_date=future_date,
            free_change=free_change,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:changePPRequest"
        )
    def get_unbilled_balance(
        self,
        ctn: str
    ) -> Optional[Any]:
        """
        Небиллингованный баланс лицевого счёта (getUnbilledBalances).
        """
        session_id = self.token_provider()
        xml = get_unbilled_balance_template(
            ctn=ctn,
            session_id=session_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getUnbilledBalancesRequest"
        )

    def add_del_soc(
        self,
        ctn: str,
        soc: str,
        inclusion_type: str,
        eff_date: str = None,
        exp_date: str = None
    ) -> Optional[Any]:
        """
        Подключение/отключение услуги (addDelSOC). add=True — подключить, False — отключить.
        """
        session_id = self.token_provider()
        xml = add_del_soc_template(
            ctn=ctn,
            soc=soc,
            inclusion_type=inclusion_type,
            eff_date=eff_date,
            exp_date=exp_date,
            session_id=session_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:addDelSOCRequest"
        )

    def suspend_ctn(
        self,
        ctn: str,
        reason_code: str,
        actv_date: str = None
    ) -> Optional[Any]:
        """
        Добровольная блокировка номера (suspendCTN).
        """
        session_id = self.token_provider()
        xml = suspend_ctn_template(
            ctn=ctn,
            reason_code=reason_code,
            actv_date=actv_date,
            session_id=session_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:suspendCTNRequest"
        )

    def restore_ctn(
        self,
        ctn: str,
        reason_code: str,
        actv_date: str = None
    ) -> Optional[Any]:
        """
        Снятие блокировки номера (restoreCTN).
        """
        session_id = self.token_provider()
        xml = restore_ctn_template(
            ctn=ctn,
            reason_code=reason_code,
            actv_date=actv_date,
            session_id=session_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:restoreCTNRequest"
        )

    def replace_sim(
        self,
        ctn: str,
        serial_number: str
    ) -> Optional[Any]:
        """
        Замена SIM-карты (replaceSIM).
        """
        session_id = self.token_provider()
        xml = replace_sim_template(
            ctn=ctn,
            serial_number=serial_number,
            session_id=session_id,
            login=config.beeline_login
        )
        return self._make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:restoreCTNRequest"
        )

    def get_details(
        self,
        request_id: str
    ) -> Optional[Any]:
        session_id = self.token_provider()
        xml = get_details_template(
            session_id=session_id,
            request_id=request_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getDetailsRequest"
        )

    def get_request_list(
        self,
        page: int = None,
        start_date: str = None,
        end_date: str = None,
        request_id: str = None,
        records_per_page: str = None
    ) -> Optional[Any]:
        session_id = self.token_provider()
        xml = get_request_list_template(
            session_id=session_id,
            page=page,
            login=config.beeline_login,
            start_date=start_date,
            end_date=end_date,
            request_id=request_id,
            records_per_page=records_per_page
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getRequestListRequest"
        )

    def get_bill_calls(
        self,
        request_id: str
    ) -> Optional[Any]:
        session_id = self.token_provider()
        xml = get_bill_calls_template(
            session_id=session_id,
            request_id=request_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getBillCallsRequest"
        )

    def get_adjustment_list(
        self,
        ban: str,
        start_date: str,
        end_date: str
    ) -> Optional[Any]:
        session_id = self.token_provider()
        xml = get_adjustment_list_template(
            session_id=session_id,
            ban=ban,
            start_date=start_date,
            end_date=end_date,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getAdjustmentListRequest"
        )

    def get_bill_charges(
        self,
        request_id: str
    ) -> Optional[Any]:
        session_id = self.token_provider()
        xml = get_bill_charges_template(
            session_id=session_id,
            request_id=request_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getBillChargesRequest"
        )

    def get_bill_charges_paged(
        self,
        request_id: str,
        page: int = None,
        records_per_page: str = None
    ) -> Optional[Any]:
        session_id = self.token_provider()
        xml = get_bill_charges_paged_template(
            session_id=session_id,
            request_id=request_id,
            page=page,
            login=config.beeline_login,
            records_per_page=records_per_page
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getBillChargesPagedRequest"
        )

    def get_sim_list(
        self,
        ban: str,
        ctn: str = None
    ) -> Optional[Any]:
        session_id = self.token_provider()
        xml = get_sim_list_template(
            session_id=session_id,
            ban=ban,
            ctn=ctn,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getSIMListRequest"
        )

    def get_sim_list_paged(
        self,
        ban: str,
        page: int = None,
        ctn: str = None,
        records_per_page: str = None
    ) -> Optional[Any]:
        session_id = self.token_provider()
        xml = get_sim_list_paged_template(
            session_id=session_id,
            ban=ban,
            page=page,
            ctn=ctn,
            login=config.beeline_login,
            records_per_page=records_per_page
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getSIMListPagedRequest"
        )

    def get_services_list(
        self,
        ban: str,
        ctn: str = None
    ) -> Optional[Any]:
        session_id = self.token_provider()
        xml = get_services_list_template(
            session_id=session_id,
            ban=ban,
            ctn=ctn,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getServicesListRequest"
        )

    def get_services_list_paged(
        self,
        ban: str,
        page: int = None,
        ctn: str = None,
        ctn_amount_per_page: str = None
    ) -> Optional[Any]:
        session_id = self.token_provider()
        xml = get_services_list_paged_template(
            session_id=session_id,
            ban=ban,
            page=page,
            ctn=ctn,
            login=config.beeline_login,
            ctn_amount_per_page=ctn_amount_per_page
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getServicesListPagedRequest"
        )

    def get_unbilled_calls_list(
        self,
        ctn: str
    ) -> Optional[Any]:
        session_id = self.token_provider()
        xml = get_unbilled_calls_list_template(
            session_id=session_id,
            ctn=ctn,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getUnbilledCallsListRequest"
        )

    def add_shared_number_list_dol(
        self,
        ctn_from: str,
        ctn_to_list: str,
        ctn_to: str,
        soc: str = None,
        prepaid_state_chk_cancel: str = None,
        check_add_number_registration: str = None
    ) -> Optional[Any]:
        """
        Добавление списка номеров в shared DOL.
        """
        session_id = self.token_provider()
        xml = add_shared_number_list_dol_template(
            session_id=session_id,
            ctn_from=ctn_from,
            ctn_to_list=ctn_to_list,
            ctn_to=ctn_to,
            soc=soc,
            prepaid_state_chk_cancel=prepaid_state_chk_cancel,
            check_add_number_registration=check_add_number_registration
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:addSharedNumberListDOLRequest"
        )

    def delete_shared_number_list_dol(
        self,
        ctn_from: str,
        ctn_to_list: str,
        ctn_to: str
    ) -> Optional[Any]:
        """
        Удаление списка номеров из shared DOL.
        """
        session_id = self.token_provider()
        xml = delete_shared_number_list_dol_template(
            session_id=session_id,
            ctn_from=ctn_from,
            ctn_to_list=ctn_to_list,
            ctn_to=ctn_to
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:deleteSharedNumberListDOLRequest"
        )

    def personal_data_update(
        self,
        data: str
    ) -> Optional[Any]:
        """
        Обновление персональных данных.
        """
        session_id = self.token_provider()
        xml = personal_data_update_template(
            session_id=session_id,
            data=data,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:personalDataUpdateRequest"
        )

    def personal_data_result(
        self,
        request_id: str
    ) -> Optional[Any]:
        """
        Получение результата обновления персональных данных.
        """
        session_id = self.token_provider()
        xml = personal_data_result_template(
            session_id=session_id,
            request_id=request_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:personalDataResultRequest"
        )

    def get_data_report(
        self,
        request_id: str,
        page: int = None,
        records_per_page: str = None
    ) -> Optional[Any]:
        """
        Получение отчета о данных.
        """
        session_id = self.token_provider()
        xml = get_data_report_template(
            session_id=session_id,
            request_id=request_id,
            page=page,
            login=config.beeline_login,
            records_per_page=records_per_page
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getDataReportRequest"
        )

    def get_ban_info_list(
        self,
    ) -> Optional[Any]:
        """
        Получение информации о BAN по логину.
        """
        session_id = self.token_provider()
        xml = get_ban_info_list_template(
            session_id=session_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getBANInfoListRequest"
        )

    def add_shared_number_dol(
        self,
        request_id: str,
        ctn_to: str,
        ctn_type: str,
        soc: str,
        prepaid_state_chk_cancel: str,
        check_add_number_registration: str
    ) -> Optional[Any]:
        """
        Добавление одного номера в shared DOL.
        """
        session_id = self.token_provider()
        xml = add_shared_number_dol_template(
            session_id=session_id,
            request_id=request_id,
            ctn_to=ctn_to,
            ctn_type=ctn_type,
            soc=soc,
            prepaid_state_chk_cancel=prepaid_state_chk_cancel,
            check_add_number_registration=check_add_number_registration
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:addSharedNumberDOLRequest"
        )

    def create_bill_calls_request(
        self,
        ban: str,
        bill_date: str,
        ctn_list: str = None
    ) -> Optional[Any]:
        """
        Запрос звонков по счёту.
        """
        session_id = self.token_provider()
        xml = create_bill_calls_request_template(
            session_id=session_id,
            ban=ban,
            bill_date=bill_date,
            login=config.beeline_login,
            ctn_list=ctn_list
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:createBillCallsRequest"
        )

    def create_bill_charges_request(
        self,
        ban: str,
        bill_date: str,
        ctn_list: str = None
    ) -> Optional[Any]:
        """
        Запрос начислений по счёту.
        """
        session_id = self.token_provider()
        xml = create_bill_charges_request_template(
            session_id=session_id,
            ban=ban,
            bill_date=bill_date,
            login= config.beeline_login,
            ctn_list=ctn_list
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:createBillChargesRequest"
        )

    def create_details_request(
        self,
        ctn: str,
        period_start: str,
        period_end: str,
        format_: str,
        channel: str = None,
        email: str = None
    ) -> Optional[Any]:
        """
        Создать детализацию.
        """
        session_id = self.token_provider()
        xml = create_details_request_template(
            session_id=session_id,
            ctn=ctn,
            period_start=period_start,
            period_end=period_end,
            format_=format_,
            login=config.beeline_login,
            channel=channel,
            email=email
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:createDetailsRequest"
        )

    def get_ban_info_list_paged(
        self,
        page: int = None,
        records_per_page: str = None
    ) -> Optional[Any]:
        """
        Получить BAN с пагинацией.
        """
        session_id = self.token_provider()
        xml = get_ban_info_list_paged_template(
            session_id=session_id,
            login=config.beeline_login,
            page=page,
            records_per_page=records_per_page
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getBANInfoListPagedRequest"
        )

    def get_bill_calls_paged(
        self,
        request_id: str,
        page: int = None,
        records_per_page: str = None
    ) -> Optional[Any]:
        """
        Получить звонки с пагинацией.
        """
        session_id = self.token_provider()
        xml = get_bill_calls_paged_template(
            session_id=session_id,
            request_id=request_id,
            page=page,
            login=config.beeline_login,
            records_per_page=records_per_page
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getBillCallsPagedRequest"
        )

    def get_data(
        self,
        ban: str,
        hierarchy_id: str,
        subscriber_no: str
    ) -> Optional[Any]:
        """
        Получить данные о абоненте.
        """
        session_id = self.token_provider()
        xml = get_data_template(
            session_id=session_id,
            login=config.beeline_login,
            ban=ban,
            hierarchy_id=hierarchy_id,
            subscriber_no=subscriber_no
        )
        return _make_soap_request(
            xml,
            "urn:uss-wsapi:Subscriber:SubscriberInterface:getDataRequest"
        )