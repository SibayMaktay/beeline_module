import requests
import logging
from typing import Optional

import config.config as config

logger = logging.getLogger(__name__)
_utm5_session_id = None

def get_utm5_token() -> Optional[str]:
    global _utm5_session_id
    if _utm5_session_id:
        return _utm5_session_id

    logger.info("Попытка аутентификации в utm5...")

    try:
        session = requests.Session()
        session.timeout = 15
        response = session.post(
            f"{config.utm5_api_url}/api/login",
            json={'username': config.utm5_login, 'password': config.utm5_password},
            headers={'Content-Type':'application/json'}
        )
        response.raise_for_status()
        data = response.json()

        _utm5_session_id = data.get('session_id')

        if not _utm5_session_id and 'session_id' in session.cookies:
            _utm5_session_id = session.cookies['session_id']

        if _utm5_session_id:
            logger.info("Аутентификация в UTM5 успешна")
            return _utm5_session_id

        logger.warning("Аутентификация не удалась: session_id не получен в ответе")
        return None

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP ошибка при аутентификации: {e}. Ответ: {response.text}")
        return None
    except requests.exceptions.RequestException:
        logger.error(f"Сетевая ошибка аутентификации")
        return None
    except Exception as e:
        logger.error(f"Ошибка получения session_id: {e}")
        return None