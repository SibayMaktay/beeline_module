import logging
import requests
import xml.etree.ElementTree as ET

import config.config as config
from templates.wsdl_template_beeline import get_auth_template

logger = logging.getLogger(__name__)
_beeline_session_id = None

def get_beeline_token() -> str:
    """
    Получает токен Beeline с кешированием.
    1. Сначала через raw SOAP с requests.
    2. Если не удалось — через REST API.
    """
    global _beeline_session_id
    if _beeline_session_id:
        return _beeline_session_id

    logger.info("Попытка аутентификации в Beeline...")

    # 1. Пробуем через raw SOAP с requests
    try:
        logger.info("Попытка аутентификации в Beeline через raw SOAP...")
        xml_payload = get_auth_template(config.beeline_login, config.beeline_password)
        headers = {"Content-Type": "text/xml", "SOAPAction": '"urn:uss-wsapi:Auth:AuthInterface:authRequest"'}
        response = requests.post(f"{config.beeline_url_base}/api/AuthService", data=xml_payload, headers=headers, timeout=15)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        for elem in root.iter():
            if elem.tag.endswith('return') or elem.tag.endswith('session_id'):
                if elem.text and len(elem.text) > 5:
                    logger.info("Raw SOAP аутентификация Beeline успешна.")
                    _beeline_session_id = elem.text
                    return _beeline_session_id
        logger.error("Токен не найден в raw SOAP ответе.")
    except Exception as e:
        logger.warning(f"Raw SOAP аутентификация не удалась: {e}.")

    # 2. Пробуем через REST API
    try:
        logger.info("Попытка аутентификации в Beeline через REST API...")
        rest_url = f"{config.beeline_url_base}/api/1.0/auth?login={config.beeline_login}&password={config.beeline_password}"
        resp = requests.get(rest_url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        token = data.get("token") or data.get("session_id") or data.get("return")
        if token:
             logger.info("REST API аутентификация Beeline успешна.")
             _beeline_session_id = token
             return _beeline_session_id
        logger.warning("Токен не найден в ответе REST API Beeline.")
    except Exception as e:
        logger.warning(f"Ошибка REST API аутентификации Beeline: {e}.")

    raise Exception("Не удалось получить токен Beeline.")

def invalidate_token():
    global _beeline_session_id
    _beeline_session_id = None
    logger.info("Токен Beeline аннулирован.")