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

def get_auth_template(
    login: str,
    password: str
) -> str:
    action = "auth"
    interface = "Auth"
    head = xml_head_template.format(interface=interface, action=action)
    footer = xml_footer_template.format(action=action)
    return f"""{head}
            <login>{login}</login>
            <password>{password}</password>
{footer}"""

def suspend_ctn_template(
    ctn: str,
    reason_code: str,
    session_id: str,
    login: str = None,
    actv_date: str = None
):
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
    return universal_soap_template(
        session_id,
        "replaceSIM",
        ctn=ctn,
        serialNumber=serial_number,
        login=login
    )

def change_pp_template(
    ctn: str,
    price_plan: str,
    session_id: str,
    future_date: str = None,
    login: str = None,
    free_change: str = "false"
):
    return universal_soap_template(
        session_id,
        "changePP",
        ctn=ctn,
        pricePlan=price_plan,
        futureData=future_date,
        login=login,
        freeChange=free_change
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

def get_sim_list_template(
    session_id: str,
    ban: str,
    ctn: str = None,
    login: str = None
):
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
    records_per_page: int = None
):
    return universal_soap_template(
        session_id,
        "getSIMListPaged",
        ban=ban,
        ctn=ctn,
        page=page,
        recordsPerPage=records_per_page,
        login=login
    )

def get_request_list_template(
    session_id: str,
    page: int = 1,
    login: str = None,
    start_date: str = None,
    end_date: str = None,
    request_id: str = None,
    records_per_page: int = None
):
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

def get_services_list_template(
    session_id: str,
    ban: str,
    ctn: str = None,
    login: str = None
):
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
    ctn_amount_per_page: int = None
):
    return universal_soap_template(
        session_id,
        "getServicesListPaged",
        ban=ban,
        ctn=ctn,
        page=page,
        recordsPerPage=ctn_amount_per_page,
        login=login
    )

def get_ctn_info_list_template(
    ban: str,
    session_id: str,
    ctn: str = None,
    login: str = None
):
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
    records_per_page: int = None
):
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
    records_per_page: int = None
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

def get_unbilled_balance_template(
    ctn: str,
    session_id: str,
    login: str
):
    return universal_soap_template(
        session_id,
        "getUnbilledBalances",
        ctn=ctn,
        login=login
    )

def get_unbilled_calls_list_template(
    session_id: str,
    ctn: str,
    login: str = None
):
    return universal_soap_template(
        session_id,
        "getUnbilledCallsList",
        ctn=ctn,
        login=login
    )

def get_adjustment_list_template(
    session_id: str,
    ban: str,
    start_date: str,
    end_date: str,
    login: str = None
):
    return universal_soap_template(
        session_id,
        "getAdjustmentList",
        ban=ban,
        startDate=start_date,
        endDate=end_date,
        login=login
    )

def create_bill_calls_request_template(
    session_id: str,
    ban: str,
    bill_date: str,
    login: str = None,
    ctn_list: str = None
):
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
    return universal_soap_template(
        session_id,
        "createBillChargesRequest",
        ban=ban,
        billDate=bill_date,
        CTNList=ctn_list,
        login=login
    )

def get_bill_calls_template(
    session_id: str,
    request_id: str,
    login: str = None
):
    return universal_soap_template(
        session_id,
        "getBillCalls",
        requestId=request_id,
        login=login
    )

def get_bill_calls_paged_template(
    session_id: str,
    request_id: str,
    page: int = 1,
    login: str = None,
    records_per_page: int = None
):
    return universal_soap_template(
        session_id,
        "getBillCallsPaged",
        requestId=request_id,
        page=page,
        recordsPerPage=records_per_page,
        login=login
    )

def get_bill_charges_template(
    session_id: str,
    request_id: str,
    login: str = None
):
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
    records_per_page: int = None
):
    return universal_soap_template(
        session_id,
        "getBillChargesPaged",
        requestId=request_id,
        page=page,
        recordsPerPage=records_per_page,
        login=login
    )

def get_ban_info_list_template(
    session_id: str,
    login: str
):
    return universal_soap_template(
        session_id,
        "getBANInfoList",
        login=login
    )

def get_ban_info_list_paged_template(
    session_id: str,
    login: str,
    page: int = 1,
    records_per_page: int = None
):
    return universal_soap_template(
        session_id,
        "getBANInfoListPaged",
        page=page,
        recordsPerPage=records_per_page,
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

def get_details_template(
    session_id: str,
    request_id: str,
    login: str = None
):
    return universal_soap_template(
        session_id,
        "getDetails",
        requestId=request_id,
        login=login
    )

def add_shared_number_dol_template(
    session_id: str,
    ctn_from: str,
    ctn_to: str,
    ctn_type: str,
    soc: str,
    prepaid_state_chk_cancel: str,
    check_add_number_registration: str
):
    return universal_soap_template(
        session_id,
        "addSharedNumberDOL",
        ctnFrom=ctn_from,
        ctnTo=ctn_to,
        ctnType=ctn_type,
        soc=soc,
        prepaidStateChkCancel=prepaid_state_chk_cancel,
        checkAddNumberRegistration=check_add_number_registration
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
    return universal_soap_template(
        session_id,
        "personalDataResult",
        requestId=request_id,
        login=login
    )

def get_data_template(
    session_id: str,
    login: str,
    ban: str,
    hierarchy_id: str,
    subscriber_no: str
):
    return universal_soap_template(
        session_id,
        "getData",
        ban=ban,
        hierarchyId=hierarchy_id,
        subscriberNo=subscriber_no,
        login=login
    )

def get_data_report_template(
    session_id: str,
    request_id: str,
    page: int = 1,
    login: str = None,
    records_per_page: int = None
):
    return universal_soap_template(
        session_id,
        "getDataReport",
        requestId=request_id,
        page=page,
        recordsPerPage=records_per_page,
        login=login
    )

def activate_convergent_user_template(
    session_id: str,
    login: str = None
):
    return universal_soap_template(
        session_id,
        "activateConvergentUser",
        login=login
    )

def add_ple_subscriber_limit_info_template(
    session_id: str,
    login: str = None
):
    return universal_soap_template(
        session_id,
        "addPleSubscriberLimitInfo",
        login=login
    )

def cancel_fake_subscription_template(
    session_id: str,
    login: str = None
):
    return universal_soap_template(
        session_id,
        "cancelFakeSubscription",
        login=login
    )

def create_or_delete_invited_fttb_ctn_template(
    session_id: str,
    login: str = None
):
    return universal_soap_template(
        session_id,
        "createOrDeleteInvitedFttbCtn",
        login=login
    )

def notify_about_block_template(
    session_id: str,
    login: str = None
):
    return universal_soap_template(
        session_id,
        "notifyAboutBlock",
        login=login
    )