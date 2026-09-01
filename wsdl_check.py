"""
Проверка доступности WSDL и парсинг операций.

Назначение: валидировать WSDL-ссылки и извлекать из них только имена операций.
Без этого вывод был бы килобайтом XML, что бесполезно.
"""

import logging
import re
from typing import Optional, Dict, List
from xml.etree import ElementTree as ET
import requests

logger = logging.getLogger(__name__)

# WSDL-ссылки Beeline (из .env)
WSDL_URLS = {
    "AuthService": "https://my.beeline.ru/api/AuthService?WSDL",
    "SubscriberService": "https://my.beeline.ru/api/SubscriberService?WSDL",
}

# Таймаут для всех HTTP-запросов
HTTP_TIMEOUT = 10


def check_wsdl_health() -> Dict[str, dict]:
    """
    Проверяет доступность WSDL и парсит операции.

    Возвращает словарь:
    {
        "AuthService": {
            "status": 200,
            "available": True,
            "operations": ["auth"],
            "error": None
        },
        "SubscriberService": {
            "status": 403,
            "available": False,
            "operations": [],
            "error": "wsdl не доступны, 403"
        }
    }
    """
    result = {}

    for service_name, url in WSDL_URLS.items():
        result[service_name] = _check_single_wsdl(service_name, url)

    return result


def _check_single_wsdl(service_name: str, url: str) -> dict:
    """Проверяет одну WSDL-ссылку и парсит операции."""
    try:
        response = requests.get(url, timeout=HTTP_TIMEOUT, verify=False)

        if response.status_code == 403:
            logger.warning(f"{service_name} недоступен: HTTP 403")
            return {
                "status": 403,
                "available": False,
                "operations": [],
                "error": f"wsdl не доступны, 403",
            }

        response.raise_for_status()

        # Парсим XML и извлекаем операции
        operations = _extract_operations(response.text)

        logger.info(f"{service_name} доступен. Операции: {operations}")
        return {
            "status": response.status_code,
            "available": True,
            "operations": operations,
            "error": None,
        }

    except requests.exceptions.Timeout:
        logger.error(f"{service_name} таймаут ({HTTP_TIMEOUT}с)")
        return {
            "status": None,
            "available": False,
            "operations": [],
            "error": f"таймаут ({HTTP_TIMEOUT}с)",
        }
    except requests.exceptions.ConnectionError as exc:
        logger.error(f"{service_name} ошибка подключения: {exc}")
        return {
            "status": None,
            "available": False,
            "operations": [],
            "error": "ошибка подключения",
        }
    except requests.exceptions.RequestException as exc:
        logger.error(f"{service_name} HTTP ошибка: {exc}")
        return {
            "status": None,
            "available": False,
            "operations": [],
            "error": str(exc)[:100],
        }
    except Exception as exc:
        logger.error(f"{service_name} неизвестная ошибка: {exc}")
        return {
            "status": None,
            "available": False,
            "operations": [],
            "error": str(exc)[:100],
        }


def _extract_operations(wsdl_xml: str) -> List[str]:
    """
    Извлекает имена операций из WSDL.

    Ищет <operation name="..."> внутри <portType>.
    """
    operations = []

    try:
        # Парсим XML
        root = ET.fromstring(wsdl_xml)

        # WSDL использует namespace http://schemas.xmlsoap.org/wsdl/
        wsdl_ns = {"wsdl": "http://schemas.xmlsoap.org/wsdl/"}

        # Ищем <portType> с namespace
        port_types = root.findall(".//wsdl:portType", wsdl_ns)
        
        # Если не нашли с namespace, ищем без
        if not port_types:
            port_types = root.findall(".//portType", {})

        for port_type in port_types:
            # Ищем <operation name="..."> с namespace
            operations_elem = port_type.findall("wsdl:operation", wsdl_ns)
            
            # Если не нашли, ищем без
            if not operations_elem:
                operations_elem = port_type.findall("operation", {})

            for op in operations_elem:
                name = op.get("name")
                if name:
                    operations.append(name)

    except ET.ParseError as exc:
        logger.warning(f"Ошибка парсинга XML: {exc}")
        return []
    except Exception as exc:
        logger.warning(f"Ошибка парсинга операций: {exc}")
        return []

    return sorted(operations)


def format_health_response(health: Dict[str, dict]) -> str:
    """Форматирует результаты для вывода."""
    lines = []

    for service_name, data in sorted(health.items()):
        if data["available"]:
            lines.append(f"{service_name} WSDL:")
            for op in data["operations"]:
                lines.append(f"    {op}")
        else:
            lines.append(f"{service_name} WSDL: {data['error']}")

    return "\n".join(lines)
