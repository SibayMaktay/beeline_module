xml_head_template = """<soapenv:Envelope
xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
xmlns:urn="urn:uss-wsapi:{interface}">
    <soapenv:Header/>
    <soapenv:Body>
        <urn:{action}>"""

xml_footer_template = """       </urn:{action}>
    </soapenv:Body>
</soapenv:Envelope>"""

def make_soap_xml(
    action: str,
    interface: str,
    params: dict
) -> str:
    """
    Формирует XML для любого SOAP-запроса Beeline.
    """
    head = xml_head_template.format(interface=interface, action=action)
    footer = xml_footer_template.format(action=action)
    body = ""
    for key, value in params.items():
        if value is None:
            continue
        body += f"\n            <{key}>{value}</{key}>"
    return f"{head}{body}\n{footer}"

def universal_soap_template(
    session_id: str,
    action: str,
    interface: str = "Subscriber",
    **kwargs
) -> str:
    params = {**kwargs, "token": session_id}
    return make_soap_xml(action, interface, params)

# Method Auth
def get_auth_template(
    login: str,
    password: str
) -> str:
    """
    Аутентификация пользователя по связке логин/пароль.
    """
    action = "auth"
    interface = "Auth"
    head = xml_head_template.format(interface=interface, action=action)
    footer = xml_footer_template.format(action=action)
    return f"""{head}
            <login>{login}</login>
            <password>{password}</password>
{footer}"""

# Method service Subscriber
def get_ctn_info_list_template(
    ban: str,
    session_id: str,
    ctn: str = None,
    login: str = None
):
    """
    Получения информации об абонентах на уровне BAN/CTN.
    """
    return universal_soap_template(
        session_id,
        "getCTNInfoList",
        ban=ban,
        ctn=ctn,
        login=login,
    )

def get_ctn_info_list_paged_template(
    ban: str,
    session_id: str,
    page: int = 1,
    login: str = None,
    ctn: str = None,
    records_per_page: str = None
):
    """
    Получения информации об абонентах на уровне BAN/CTN.
    """
    return universal_soap_template(
        session_id,
        "getCTNInfoListPaged",
        ban=ban,
        ctn=ctn,
        login=login,
        page=page,
        recordsPerPage=records_per_page
    )

def get_payment_list_template(
    ban: str,
    start_date: str,
    end_date: str,
    session_id: str,
    ctn: str = None,
    login: str = None
):
    return universal_soap_template(
        session_id,
        "getPaymentList",
        ban=ban,
        ctn=ctn,
        startDate=start_date,
        endDate=end_date,
        login=login
    )

def get_payment_list_paged_template(
    ban: str,
    start_date: str,
    end_date: str,
    session_id: str,
    page: int = 1,
    ctn: str = None,
    login: str = None,
    records_per_page: str = None
):
    return universal_soap_template(
        session_id,
        "getPaymentListPaged",
        ban=ban,
        ctn=ctn,
        startDate=start_date,
        endDate=end_date,
        login=login,
        page=page,
        recordsPerPage=records_per_page
    )

def change_pp_template(
    ctn: str,
    price_plan: str,
    session_id: str,
    future_date: str = None,
    login: str = None,
    free_change: str = "false"
):
    """
    Создание запроса на смену тарифного плана.
    """
    return universal_soap_template(
        session_id,
        "changePP",
        ctn=ctn,
        pricePlan=price_plan,
        futureData=future_date,
        login=login,
        freeChange=free_change
    )

def get_unbilled_balance_template(
    ctn: str,
    session_id: str,
    login: str
):
    """
    Возвращает сумму списания за текущий период абонента (постпейд).
    """
    return universal_soap_template(
        session_id,
        "getUnbilledBalances",
        ctn=ctn,
        login=login
    )

def add_del_soc_template(
    ctn: str,
    soc: str,
    inclusion_type: str,
    session_id: str,
    eff_date: str = None,
    exp_date: str = None,
    login: str = None
):
    """
    Создание запроса на подключение/отключение услуги.
    """
    return universal_soap_template(
        session_id,
        "addDelSOC",
        ctn=ctn,
        SOC=soc,
        inclusionType=inclusion_type,
        effDate=eff_date,
        expDate=exp_date,
        login=login
    )

def suspend_ctn_template(
    ctn: str,
    reason_code: str,
    session_id: str,
    login: str = None,
    actv_date: str = None
):
    """
    Создание запроса на блокировку абонента.
    """
    return universal_soap_template(
        session_id,
        "suspendCTN",
        ctn=ctn,
        actvData=actv_date,
        reasonCode=reason_code,
        login=login
    )

def restore_ctn_template(
    ctn: str,
    reason_code: str,
    session_id: str,
    login: str = None,
    actv_date: str = None
):
    """
    Создание запроса на разблокировку абонента.
    """
    return universal_soap_template(
        session_id,
        "restoreCTN",
        ctn=ctn,
        actvData=actv_date,
        reasonCode=reason_code,
        login=login
    )

def replace_sim_template(
    ctn: str,
    serial_number: str,
    session_id: str,
    login: str = None
):
    """
    Создание запроса на замену SIM карты абонента.
    """
    return universal_soap_template(
        session_id,
        "replaceSIM",
        ctn=ctn,
        serialNumber=serial_number,
        login=login
    )

def get_details_template(
    session_id: str,
    request_id: str,
    login: str = None
):
    """
    Получить детализацию запроса по его requestId.
    """
    return universal_soap_template(
        session_id,
        "getDetails",
        requestId=request_id,
        login=login
    )

def get_request_list_template(
    session_id: str,
    page: int = 1,
    login: str = None,
    start_date: str = None,
    end_date: str = None,
    request_id: str = None,
    records_per_page: str = None
):
    """
    Получить список заявок.
    """
    return universal_soap_template(
        session_id,
        "getRequestList",
        startDate=start_date,
        endDate=end_date,
        requestId=request_id,
        page=page,
        recordsPerPage=records_per_page,
        login=login
    )

def get_bill_calls_template(
    session_id: str,
    request_id: str,
    login: str = None
):
    """
    Получить список звонков по запросу детализации.
    """
    return universal_soap_template(
        session_id,
        "getBillCalls",
        requestId=request_id,
        login=login
    )

def get_adjustment_list_template(
    session_id: str,
    ban: str,
    start_date: str,
    end_date: str,
    login: str = None
):
    """
    Получить список корректировок по BAN за период.
    """
    return universal_soap_template(
        session_id,
        "getAdjustmentList",
        ban=ban,
        startDate=start_date,
        endDate=end_date,
        login=login
    )

def get_bill_charges_template(
    session_id: str,
    request_id: str,
    login: str = None
):
    """
    Получить итоговые услуги по запросу детализации.
    """
    return universal_soap_template(
        session_id,
        "getBillCharges",
        requestId=request_id,
        login=login
    )

def get_bill_charges_paged_template(
    session_id: str,
    request_id: str,
    page: int = 1,
    login: str = None,
    records_per_page: str = None
):
    """
    Получить итоговые услуги по запросу детализации (с пагинацией).
    """
    return universal_soap_template(
        session_id,
        "getBillChargesPaged",
        requestId=request_id,
        page=page,
        recordsPerPage=records_per_page,
        login=login
    )

def get_sim_list_template(
    session_id: str,
    ban: str,
    ctn: str = None,
    login: str = None
):
    """
    Получить список SIM по BAN/CTN.
    """
    return universal_soap_template(
        session_id,
        "getSIMList",
        ban=ban,
        ctn=ctn,
        login=login
    )

def get_sim_list_paged_template(
    session_id: str,
    ban: str,
    page: int = 1,
    ctn: str = None,
    login: str = None,
    records_per_page: str = None
):
    """
    Получить список SIM по BAN/CTN с пагинацией.
    """
    return universal_soap_template(
        session_id,
        "getSIMListPaged",
        ban=ban,
        ctn=ctn,
        page=page,
        recordsPerPage=records_per_page,
        login=login
    )

def get_services_list_template(
    session_id: str,
    ban: str,
    ctn: str = None,
    login: str = None
):
    """
    Получить список услуг по BAN/CTN.
    """
    return universal_soap_template(
        session_id,
        "getServicesList",
        ban=ban,
        ctn=ctn,
        login=login
    )

def get_services_list_paged_template(
    session_id: str,
    ban: str,
    page: int = 1,
    ctn: str = None,
    login: str = None,
    ctn_amount_per_page: str = None
):
    """
    Получить список услуг по BAN/CTN с пагинацией.
    """
    return universal_soap_template(
        session_id,
        "getServicesListPaged",
        ban=ban,
        ctn=ctn,
        page=page,
        ctnAmountPerPage=ctn_amount_per_page,
        login=login
    )

def get_unbilled_calls_list_template(
    session_id: str,
    ctn: str,
    login: str = None
):
    """
    Получить список невыставленных звонков по CTN.
    """
    return universal_soap_template(
        session_id,
        "getUnbilledCallsList",
        ctn=ctn,
        login=login
    )

def add_shared_number_list_dol_template(
    session_id: str,
    ctn_from: str,
    ctn_to_list: str,
    ctn_to: str,
    soc: str = None,
    prepaid_state_chk_cancel: str = None,
    check_add_number_registration: str = None
):
    """
    Добавить абонентов в shared list DOL.
    """
    return universal_soap_template(
        session_id,
        "addSharedNumberListDOL",
        ctnFrom=ctn_from,
        ctnToList=ctn_to_list,
        ctnTo=ctn_to,
        soc=soc,
        prepaidStateChkCancel=prepaid_state_chk_cancel,
        checkAddNumberRegistration=check_add_number_registration
    )

def delete_shared_number_list_dol_template(
    session_id: str,
    ctn_from: str,
    ctn_to_list: str,
    ctn_to: str
):
    """
    Удалить абонентов из shared list DOL.
    """
    return universal_soap_template(
        session_id,
        "deleteSharedNumberListDOL",
        ctnFrom=ctn_from,
        ctnToList=ctn_to_list,
        ctnTo=ctn_to
    )

def personal_data_update_template(
    session_id: str,
    data: dict,
    login: str = None
):
    """
    Обновление персональных данных абонента.
    """
    data_xml = "".join(
        f"<{key}>{val}</{key}>" for key, val in data.items() if val is not None
    )
    return universal_soap_template(
        session_id,
        "personalDataUpdate",
        data_xml,
        login=login
    )

def personal_data_result_template(
    session_id: str,
    request_id: str,
    login: str = None
):
    """
    Получение результата обновления персональных данных по request_id.
    """
    return universal_soap_template(
        session_id,
        "personalDataResult",
        requestId=request_id,
        login=login
    )

def get_data_report_template(
    session_id: str,
    request_id: str,
    page: int = 1,
    login: str = None,
    records_per_page: str = None
):
    """
    Получить отчёт о данных.
    """
    return universal_soap_template(
        session_id,
        "getDataReport",
        requestId=request_id,
        page=page,
        recordsPerPage=records_per_page,
        login=login
    )

def get_ban_info_list_template(
    session_id: str,
    login: str
):
    """
    Получить список BAN по логину.
    """
    return universal_soap_template(
        session_id,
        "getBANInfoList",
        login=login
    )

def add_shared_number_dol_template(
    session_id: str,
    ctn_to: str,
    ctn_type: str,
    soc: str,
    prepaid_state_chk_cancel: str,
    check_add_number_registration: str
):
    """
    Добавить номер в shared DOL (предполагается, что все параметры обязательные).
    """
    return universal_soap_template(
        session_id,
        "addSharedNumberDOL",
        ctnTo=ctn_to,
        ctnType=ctn_type,
        soc=soc,
        prepaidStateChkCancel=prepaid_state_chk_cancel,
        checkAddNumberRegistration=check_add_number_registration
    )

def create_bill_calls_request_template(
    session_id: str,
    ban: str,
    bill_date: str,
    login: str = None,
    ctn_list: str = None
):
    """
    Создать запрос на получение звонков по счёту.
    """
    return universal_soap_template(
        session_id,
        "createBillCallsRequest",
        ban=ban,
        billDate=bill_date,
        CTNList=ctn_list,
        login=login
    )

def create_bill_charges_request_template(
    session_id: str,
    ban: str,
    bill_date: str,
    login: str = None,
    ctn_list: str = None
):
    """
    Создать запрос на получение списаний по счёту.
    """
    return universal_soap_template(
        session_id,
        "createBillChargesRequest",
        ban=ban,
        billDate=bill_date,
        CTNList=ctn_list,
        login=login
    )

def create_details_request_template(
    session_id: str,
    ctn: str,
    period_start: str,
    period_end: str,
    format_: str,
    login: str = None,
    channel: str = None,
    email: str = None
):
    """
    Создать запрос детализации.
    """
    return universal_soap_template(
        session_id,
        "createDetailsRequest",
        ctn=ctn,
        periodStart=period_start,
        periodEnd=period_end,
        format=format_,
        channel=channel,
        email=email,
        login=login
    )

def get_ban_info_list_paged_template(
    session_id: str,
    login: str,
    page: int = 1,
    records_per_page: str = None
):
    """
    Получить список BAN по логину с пагинацией.
    """
    return universal_soap_template(
        session_id,
        "getBANInfoListPaged",
        page=page,
        recordsPerPage=records_per_page,
        login=login
    )

def get_bill_calls_paged_template(
    session_id: str,
    request_id: str,
    page: int = 1,
    login: str = None,
    records_per_page: str = None
):
    """
    Получить звонки по детализации с пагинацией.
    """
    return universal_soap_template(
        session_id,
        "getBillCallsPaged",
        requestId=request_id,
        page=page,
        recordsPerPage=records_per_page,
        login=login
    )

def get_data_template(
    session_id: str,
    login: str,
    ban: str,
    hierarchy_id: str,
    subscriber_no: str
):
    """
    Получить данные по абоненту и иерархии.
    """
    return universal_soap_template(
        session_id,
        "getData",
        ban=ban,
        hierarchyId=hierarchy_id,
        subscriberNo=subscriber_no,
        login=login
    )