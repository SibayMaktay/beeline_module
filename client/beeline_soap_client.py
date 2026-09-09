import logging
import requests
from typing import Optional, Any, Dict
import config.config as config
from templates.wsdl_template_beeline import *
import re
import xmltodict

logger = logging.getLogger(__name__)

def parse_soap_error_xml(response_test):
    """
    Разбирает SOAP Fault и вытаскивает подробности: код, описание, message, faultstring.
    Формирует дружелюбный dict-ответ.
    """
    try:
        d = xmltodict.parse(response_test)
        env = d.get('S:Envelope') or d.get('soap:Envelope') or d.get('Envelope') or next((v for k, v in d.items() if k.endswith('Envelope')), None)
        body = env.get('S:Body') or env.get('soap:Body') or env.get('Body') or next((v for k, v in env.items() if k.endswith(':Body')), None)
        fault = next((v for k, v in body.items() if 'Fault' in k), None)
        if not fault:
            return None
        res = {}
        res['faultcode'] = fault.get('faultcode')
        res['faultstring'] = fault.get('faultstring')
        detail = fault.get('detail')
        if detail:
            uss = None
            for v in detail.values():
                if isinstance(v, dict) and ('errorCode' in v or 'errorDescription' in v):
                    uss = v
                    break
            if uss:
                res['error_code'] = uss.get('errorCode')
                res['error_description'] = uss.get('errorDescription')
                res['message'] = uss.get('message')
        return res
    except Exception as e:
        logger.warning(f"Ошибка парсинга SOAP Fault: {e}")
        return None

def find_soap_response_element(body: dict, response_tag: str):
    """
    Ищет в body элемент с ключом, который содержит response_tag
    (например, 'getBANInfoListResponse', 'suspendCTNResponse').
    Возвращает содержимое этого элемента или None.
    """
    for k, v in body.items():
        if k.endswith(response_tag):
            return v
    for k, v in body.items():
        if response_tag in k:
            return v
    return None

def _make_soap_request(xml_payload: str, action: str) -> Optional[Any]:
    """
    Внутренний универсальный метод отправки SOAP.
    """
    response_tag = f"{action}Response"
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f"urn:uss-wsapi:Subscriber:SubscriberInterface:{action}Request"
    }

    try:
        logger.debug("SOAP XML:\n%s", xml_payload)
        logger.debug("Headers: %s", headers)
        logger.debug("URL: %s", f"{config.beeline_url_base}/api/SubscriberService")
        response = requests.post(
            f"{config.beeline_url_base}/api/SubscriberService",
            data=xml_payload,
            headers=headers,
            timeout=30
        )
        logger.debug(f"SOAP RESPONSE: {response.text}")
        response.raise_for_status()

        try:
            result = xmltodict.parse(response.content)
            envelope = result.get('S:Envelope') or result.get('soap:Envelope') or result.get('Envelope') or next((v for k, v in result.items() if k.endswith('Envelope')), None)
            if not envelope:
                logger.error('SOAP ENV not found')
                return {"error": "no-envelope"}
            body = envelope.get('S:Body') or envelope.get('soap:Body') or ('Body') or next((v for k, v in envelope.items() if k.endswith(':Body')), None)
            if not body:
                logger.error('SOAP BODY not found')
                return {'error': "no-body"}
            resp = None
            if response_tag:
                resp = find_soap_response_element(body,response_tag)
                if not resp:
                    logger.error(f'SOAP RESPONSE "{response_tag}" element not found')
                    return {"error": "no-response"}
                return resp
            return body
        except ImportError:
            logger.warning("Установите 'xmltodict' для удобного парсинга.")
            return {"raw_xml": response.text}
            
    except requests.exceptions.HTTPError as e:
        err = parse_soap_error_xml(response.text)
        if err:
            commentary = ''
            if err.get('error_description') == 'INVALID_QUERY_PARAM' and err.get('message'):
                commentary = f"{err['error_description']}: {err['message']}"
            msg = f"SOAP Fault {err.get('error_code')}: {err.get('error_description')} {commentary or ''}".strip()
            logger.error(msg)
            return {
                "error": err.get("error_description") or "soap-fault",
                "code": err.get("error_code"),
                "detail": err.get("message") or err.get("faultstring") or '',
                "commentary": commentary or err.get("faultstring") or ''
            }
        else:
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

    def suspend_ctn(
        self,
        ctn: str,
        reason_code: str,
        actv_date: str = None
    ) -> Optional[Any]:
        """
        Добровольная блокировка номера (suspendCTN).
        """
        name = "suspendCTN"
        session_id = self.token_provider
        xml = suspend_ctn_template(
            ctn=ctn,
            reason_code=reason_code,
            actv_date=actv_date,
            session_id=session_id,
            login=config.beeline_login,
        )
        return _make_soap_request(
            xml_payload=xml,
            action="suspendCTN"
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
        session_id = self.token_provider
        xml = restore_ctn_template(
            ctn=ctn,
            reason_code=reason_code,
            actv_date=actv_date,
            session_id=session_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml_payload=xml,
            action="restoreCTN"
        )

    def replace_sim(
        self,
        ctn: str,
        serial_number: str
    ) -> Optional[Any]:
        """
        Замена SIM-карты (replaceSIM).
        """
        session_id = self.token_provider
        xml = replace_sim_template(
            ctn=ctn,
            serial_number=serial_number,
            session_id=session_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml_payload=xml,
            action="replaceSIM"
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
        session_id = self.token_provider
        xml = change_pp_template(
            ctn=ctn,
            price_plan=price_plan,
            session_id=session_id,
            future_date=future_date,
            free_change=free_change,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml_payload=xml,
            action="changePP"
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
        session_id = self.token_provider
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
            xml_payload=xml,
            action="addDelSOC"
        )

    def get_sim_list(
        self,
        ban: str,
        ctn: str = None
    ) -> Optional[Any]:
        session_id = self.token_provider
        xml = get_sim_list_template(
            session_id=session_id,
            ban=ban,
            ctn=ctn,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getSIMList"
        )

    def get_sim_list_paged(
        self,
        ban: str,
        page: int = None,
        ctn: str = None,
        records_per_page: int = None
    ) -> Optional[Any]:
        session_id = self.token_provider
        xml = get_sim_list_paged_template(
            session_id=session_id,
            ban=ban,
            page=page,
            ctn=ctn,
            login=config.beeline_login,
            records_per_page=records_per_page
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getSIMListPaged"
        )

    def get_request_list(
        self,
        page: int = None,
        start_date: str = None,
        end_date: str = None,
        request_id: str = None,
        records_per_page: int = None
    ) -> Optional[Any]:
        session_id = self.token_provider
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
            xml_payload=xml,
            action="getRequestList"
        )

    def get_services_list(
        self,
        ban: str,
        ctn: str = None
    ) -> Optional[Any]:
        session_id = self.token_provider
        xml = get_services_list_template(
            session_id=session_id,
            ban=ban,
            ctn=ctn,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getServicesList"
        )

    def get_services_list_paged(
        self,
        ban: str,
        page: int = None,
        ctn: str = None,
        ctn_amount_per_page: int = None
    ) -> Optional[Any]:
        session_id = self.token_provider
        xml = get_services_list_paged_template(
            session_id=session_id,
            ban=ban,
            page=page,
            ctn=ctn,
            login=config.beeline_login,
            ctn_amount_per_page=ctn_amount_per_page
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getServicesListPaged"
        )

    def get_ctn_info_list(
        self,
        ban: str,
        ctn: str = None
    ) -> Optional[Any]:
        """
        Получения информации об абонентах на уровне BAN/CTN.
        """
        session_id = self.token_provider # get_beeline_token()
        xml = get_ctn_info_list_template(
            ban=ban,
            session_id=session_id,
            ctn=ctn,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getCTNInfoList"
        )

    def get_ctn_info_list_paged(
        self,
        ban: str,
        ctn: str = None,
        page: int = None,
        records_per_page: int = None
    ) -> Optional[Any]:
        """
        Получения информации об абонентах на уровне BAN/CTN.
        """
        session_id = self.token_provider
        xml = get_ctn_info_list_paged_template(
            ban=ban,
            session_id=session_id,
            ctn=ctn,
            page=page,
            records_per_page=records_per_page,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getCTNInfoListPaged"
        )

    def get_payment_list(
        self,
        ban: str,
        start_date: str,
        end_date: str,
        ctn: str = None
    ) -> Optional[Any]:
        """
        Получение списка платежей.
        """
        session_id = self.token_provider
        xml = get_payment_list_template(
            ban=ban,
            start_date=start_date,
            end_date=end_date,
            ctn=ctn,
            session_id=session_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getPaymentList"
        )

    def get_payment_list_paged(
        self,
        ban: str,
        start_date: str,
        end_date: str,
        ctn: str = None,
        page: int = None,
        records_per_page: int = None
    ) -> Optional[Any]:
        """
        Получение списка платежей.
        """
        session_id = self.token_provider
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
            xml_payload=xml,
            action="getPaymentListPaged"
        )

    def get_unbilled_balance(
        self,
        ctn: str
    ) -> Optional[Any]:
        """
        Небиллингованный баланс лицевого счёта (getUnbilledBalances).
        """
        session_id = self.token_provider
        xml = get_unbilled_balance_template(
            ctn=ctn,
            session_id=session_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getUnbilledBalances"
        )

    def get_unbilled_calls_list(
        self,
        ctn: str
    ) -> Optional[Any]:
        session_id = self.token_provider
        xml = get_unbilled_calls_list_template(
            session_id=session_id,
            ctn=ctn,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getUnbilledCallsList"
        )

    def get_adjustment_list(
        self,
        ban: str,
        start_date: str,
        end_date: str
    ) -> Optional[Any]:
        session_id = self.token_provider
        xml = get_adjustment_list_template(
            session_id=session_id,
            ban=ban,
            start_date=start_date,
            end_date=end_date,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getAdjustmentList"
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
        session_id = self.token_provider
        xml = create_bill_calls_request_template(
            session_id=session_id,
            ban=ban,
            bill_date=bill_date,
            login=config.beeline_login,
            ctn_list=ctn_list
        )
        return _make_soap_request(
            xml_payload=xml,
            action="createBillCallsRequest"
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
        session_id = self.token_provider
        xml = create_bill_charges_request_template(
            session_id=session_id,
            ban=ban,
            bill_date=bill_date,
            login= config.beeline_login,
            ctn_list=ctn_list
        )
        return _make_soap_request(
            xml_payload=xml,
            action="createBillChargesRequest"
        )

    def get_bill_calls(
        self,
        request_id: str
    ) -> Optional[Any]:
        session_id = self.token_provider
        xml = get_bill_calls_template(
            session_id=session_id,
            request_id=request_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getBillCalls"
        )

    def get_bill_calls_paged(
        self,
        request_id: str,
        page: int = None,
        records_per_page: int = None
    ) -> Optional[Any]:
        """
        Получить звонки с пагинацией.
        """
        session_id = self.token_provider
        xml = get_bill_calls_paged_template(
            session_id=session_id,
            request_id=request_id,
            page=page,
            login=config.beeline_login,
            records_per_page=records_per_page
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getBillCallsPaged"
        )

    def get_bill_charges(
        self,
        request_id: str
    ) -> Optional[Any]:
        session_id = self.token_provider
        xml = get_bill_charges_template(
            session_id=session_id,
            request_id=request_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getBillCharges"
        )

    def get_bill_charges_paged(
        self,
        request_id: str,
        page: int = None,
        records_per_page: int = None
    ) -> Optional[Any]:
        session_id = self.token_provider
        xml = get_bill_charges_paged_template(
            session_id=session_id,
            request_id=request_id,
            page=page,
            login=config.beeline_login,
            records_per_page=records_per_page
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getBillChargesPaged"
        )

    def get_ban_info_list(
        self,
    ) -> Optional[Any]:
        """
        Получение информации о BAN по логину.
        """
        session_id = self.token_provider
        xml = get_ban_info_list_template(
            session_id=session_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getBANInfoList"
        )

    def get_ban_info_list_paged(
        self,
        page: int = None,
        records_per_page: int = None
    ) -> Optional[Any]:
        """
        Получить BAN с пагинацией.
        """
        session_id = self.token_provider
        xml = get_ban_info_list_paged_template(
            session_id=session_id,
            login=config.beeline_login,
            page=page,
            records_per_page=records_per_page
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getBANInfoListPaged"
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
        session_id = self.token_provider
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
            xml_payload=xml,
            action="createDetailsRequest"
        )

    def get_details(
        self,
        request_id: str
    ) -> Optional[Any]:
        session_id = self.token_provider
        xml = get_details_template(
            session_id=session_id,
            request_id=request_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getDetails"
        )

    def add_shared_number_dol(
        self,
        ctn_form: str,
        ctn_to: str,
        ctn_type: str = None,
        soc: str = None,
        prepaid_state_chk_cancel: str = None,
        check_add_number_registration: str = None
    ) -> Optional[Any]:
        """
        Добавление одного номера в shared DOL.
        """
        session_id = self.token_provider
        xml = add_shared_number_dol_template(
            session_id=session_id,
            ctn_form=ctn_form,
            ctn_to=ctn_to,
            ctn_type=ctn_type,
            soc=soc,
            prepaid_state_chk_cancel=prepaid_state_chk_cancel,
            check_add_number_registration=check_add_number_registration
        )
        return _make_soap_request(
            xml_payload=xml,
            action="addSharedNumberDOL"
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
        session_id = self.token_provider
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
            xml_payload=xml,
            action="addSharedNumberListDOL"
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
        session_id = self.token_provider
        xml = delete_shared_number_list_dol_template(
            session_id=session_id,
            ctn_from=ctn_from,
            ctn_to_list=ctn_to_list,
            ctn_to=ctn_to
        )
        return _make_soap_request(
            xml_payload=xml,
            action="deleteSharedNumberListDOL"
        )

    def personal_data_update(
        self,
        data: dict
    ) -> Optional[Any]:
        """
        Обновление персональных данных.
        """
        session_id = self.token_provider
        xml = personal_data_update_template(
            session_id=session_id,
            data=data,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml_payload=xml,
            action="personalDataUpdate"
        )

    def personal_data_result(
        self,
        request_id: str
    ) -> Optional[Any]:
        """
        Получение результата обновления персональных данных.
        """
        session_id = self.token_provider
        xml = personal_data_result_template(
            session_id=session_id,
            request_id=request_id,
            login=config.beeline_login
        )
        return _make_soap_request(
            xml_payload=xml,
            action="personalDataResult"
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
        session_id = self.token_provider
        xml = get_data_template(
            session_id=session_id,
            login=config.beeline_login,
            ban=ban,
            hierarchy_id=hierarchy_id,
            subscriber_no=subscriber_no
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getData"
        )

    def get_data_report(
        self,
        request_id: str,
        page: int = None,
        records_per_page: int = None
    ) -> Optional[Any]:
        """
        Получение отчета о данных.
        """
        session_id = self.token_provider
        xml = get_data_report_template(
            session_id=session_id,
            request_id=request_id,
            page=page,
            login=config.beeline_login,
            records_per_page=records_per_page
        )
        return _make_soap_request(
            xml_payload=xml,
            action="getDataReport"
        )