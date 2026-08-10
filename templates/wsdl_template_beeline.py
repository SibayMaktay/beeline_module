xml_head_template = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/" xmlns:urn="urn:uss-wsapi:{interface}">
    <soapenv:Header/>
    <soapenv:Body>
        <urn:{action}>"""

xml_footer_template = """       </urn:{action}>
    </soapenv:Body>
</soapenv:Envelope>"""

def get_auth_template(login: str, password: str) -> str:
    action = "auth"
    interface = "Auth"
    head = xml_head_template.format(interface=interface, action=action)
    footer = xml_footer_template.format(action=action)
    return f"""{head}
            <login>{login}</login>
            <password>{password}</password>
{footer}"""

def get_ctn_info_template(phone: str, session_id: str) -> str:
    action = "getCTNInfoList"
    interface = "Subscriber"
    head = xml_head_template.format(interface=interface, action=action)
    footer = xml_footer_template.format(action=action)
    return f"""{head}
            <ctn>{phone}</ctn>
            <token>{session_id}</token>
{footer}"""

def get_payment_list_template(ban: str, start_date: str, end_date: str, session_id: str) -> str:
    action = "getPaymentList"
    interface = "Subscriber"
    head = xml_head_template.format(interface=interface, action=action)
    footer = xml_footer_template.format(action=action)
    return f"""{head}
            <ban>{ban}</ban>
            <startDate>{start_date}</startDate>
            <endDate>{end_date}</endDate>
            <token>{session_id}</token>
{footer}"""

def change_pp_template(phone: str, new_pp_code: str, session_id: str) -> str:
    action = "changePP"
    interface = "Subscriber"
    head = xml_head_template.format(interface=interface, action=action)
    footer = xml_footer_template.format(action=action)
    return f"""{head}
            <ctn>{phone}</ctn>
            <newPPCode>{new_pp_code}</newPPCode>
            <token>{session_id}</token>
{footer}"""

def get_unbilled_balance_template(ban: str, session_id: str) -> str:
    action = "getUnbilledBalances"
    interface = "Subscriber"
    head = xml_head_template.format(interface=interface, action=action)
    footer = xml_footer_template.format(action=action)
    return f"""{head}
            <ban>{ban}</ban>
            <token>{session_id}</token>
{footer}"""

def manage_service_template(phone: str, soc_code: str, add: str, session_id: str) -> str:
    action = "addDelSOC"
    interface = "Subscriber"
    head = xml_head_template.format(interface=interface, action=action)
    footer = xml_footer_template.format(action=action)
    return f"""{head}
            <ctn>{phone}</ctn>
            <?>{soc_code}</?>
            <?>{add: "ADD" if add else "DEL"}</?>
            <token>{session_id}</token>
{footer}"""

def suspend_ctn_template(phone: str, session_id: str) -> str:
    action = "suspendCTN"
    interface = "Subscriber"
    head = xml_head_template.format(interface=interface, action=action)
    footer = xml_footer_template.format(action=action)
    return f"""{head}
            <ctn>{phone}</ctn>
            <token>{session_id}</token>
{footer}"""

def restore_ctn_template(phone: str, session_id: str) -> str:
    action = "restoreCTN"
    interface = "Subscriber"
    head = xml_head_template.format(interface=interface, action=action)
    footer = xml_footer_template.format(action=action)
    return f"""{head}
            <ctn>{phone}</ctn>
            <token>{session_id}</token>
{footer}"""

def replace_sim_template(phone: str, new_sim: str, session_id: str) -> str:
    action = "replaceSIM"
    interface = "Subscriber"
    head = xml_head_template.format(interface=interface, action=action)
    footer = xml_footer_template.format(action=action)
    return f"""{head}
            <ctn>{phone}</ctn>
            <?>{new_sim}</?>
            <token>{session_id}</token>
{footer}"""