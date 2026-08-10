import logging
import requests
import xml.etree.ElementTree as ET
from zeep import Client
from zeep.transports import Transport
from requests import Session

import config.config as config
from templates.wsdl_template_beeline import get_auth_template

logger = logging.getLogger(__name__)

# Глобальная переменная для кэширования токена (в продакшене лучше использовать Redis или память с TTL)
_beeline_session_id = None

def get_beeline_token() -> str:
    """
    Получает или возвращает закэшированный токен Beeline.
    """
    global _beeline_session_id
    if _beeline_session_id:
        return _beeline_session_id

    logger.info("Попытка аутентификации в Beeline...")
    
    # ВАРИАНТ 1: Попытка через Zeep (официальный WSDL парсер)
    try:
        logger.debug("Variant 1: Trying Zeep...")
        session = Session()
        session.timeout = 15
        transport = Transport(session=session)
        client = Client(wsdl=f"{config.beeline_url_base}/api/AuthService?WSDL", transport=transport)
        
        response = client.service.auth(login=config.beeline_login, password=config.beeline_password)
        # Zeep возвращает объект, ищем в нем return или session_id
        token = getattr(response, 'return', None) or getattr(response, 'session_id', None)
        
        if token:
            logger.info("Аутентификация через Zeep успешна.")
            _beeline_session_id = token
            return _beeline_session_id
    except Exception as e:
        logger.warning(f"Zeep аутентификация не удалась: {e}. Переход к Variant 2...")

    # ВАРИАНТ 2: Fallback на сырой SOAP запрос через requests + шаблон
    try:
        logger.debug("Variant 2: Trying raw SOAP request with template...")
        xml_payload = get_auth_template(config.BEELINE_LOGIN, config.BEELINE_PASSWORD)
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": '"urn:uss-wsapi:Auth:AuthInterface:authRequest"'
        }
        
        response = requests.post(
            f"{config.BEELINE_BASE_URL}/api/AuthService",
            data=xml_payload,
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        
        # Парсим XML вручную
        root = ET.fromstring(response.content)
        for elem in root.iter():
            if elem.tag.endswith('return') or elem.tag.endswith('session_id'):
                if elem.text and len(elem.text) > 5:
                    logger.info("Аутентификация через raw SOAP успешна.")
                    _beeline_session_id = elem.text
                    return _beeline_session_id
                    
        logger.error("Токен не найден в ответе raw SOAP запроса.")

    except Exception as e:
        logger.error(f"Raw SOAP аутентификация также не удалась: {e}")
        logger.warning(f"Zeep аутентификация не удалась: {e}. Переход к Variant 3...")

    # ВАРИАНТ 3: REST API string
    try:
        logger.debug("Variant 3: Trying raw REST request with string...")

        url = f"{config.beeline_url_base}/api/1.0/auth"
        try:
            response = session.get(url, params={"login": config.beeline_login, "password": config.beeline_password})
            response.raise_for_status()
            data = response.json()
            _beeline_session_id = data.get("token") or (data.get("meta") or {}).get("token")
            if _beeline_session_id:
                session.cookies.get("token", _beeline_session_id)
                logger.info("REST Beeline: token получен")
                return True
            logger.warning(f"REST Beeline: token не найден. Ответ: {response.text[:200]}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"REST Beeline auth ошибка: {e}")
            return False
        
    except Exception as e:
        logger.error(f"Raw REST аутентификация также не удалась: {e}")

    raise Exception("Не удалось получить токен Beeline ни одним из доступных методов.")

def invalidate_token():
    """
    Сбрасывает токен, если он протух (вызывать при получении 401/ошибки сессии).
    """
    global _beeline_session_id
    _beeline_session_id = None
    logger.info("Токен Beeline аннулирован.")

print(get_beeline_token, _beeline_session_id)