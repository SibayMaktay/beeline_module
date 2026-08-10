import requests
import logging
from typing import Optional, Any

import config.config as config

logger = logging.getLogger(__name__)

# Глобальная переменная для кэширования токена (в продакшене лучше использовать Redis или память с TTL)
_utm5_session_id = None

def get_utm5_token() -> str:
    """
    Аутентификация в UTM5 и получение session_id
    """
    global _utm5_session_id
    if _utm5_session_id:
        return _utm5_session_id

    logger.info("Попытка аутентификации в utm5...")

    try:
        session = requests.Session()
        session.timeout = 15
        response = requests.session.post(
            f"{config.utm5_api_url}/api/login",
            json={'username': config.beeline_login, 'password': config.beeline_password},
            headers={'Content-Type':'application/json'}
        )
        response.raise_for_status()
        data = response.json()

        _utm5_session_id = data.get('_utm5_session_id')

        if not _utm5_session_id and '_utm5_session_id' in session.cookies:
            _utm5_session_id = session.cookies['_utm5_session_id']

        if _utm5_session_id:
            logger.info("Аутентификация в UTM5 успешна")
            return True

        logger.warning("Аутентификация не удалось: _utm5_sessoin_id не получен в ответе")
        return False

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP ошибка при аутентификации: {e}. Ответ: {response.text}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Сетевая ошибка аутентификации")
        return False
    except Exception as e:
        logger.error(f"Ошибка получения session_id: {e}")
        return False

def _ensure_utm5_token(self) -> bool:
    """
    Вспомогательный метод: проверяет и выполняет аутентификацию при необходимости
    """
    if not _utm5_session_id:
        return get_utm5_token()
    return True