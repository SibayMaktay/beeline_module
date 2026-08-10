import requests
import logging
from typing import Optional, Any

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
        response = self.session.post(
            f"{self.base_url}/api/login",
            json={'username': self.login, 'password': self.password},
            headers={'Content-Type':'application/json'}
        )
        response.raise_for_status()
        data = response.json()

        self.session_id = data.get('session_id')

        if not self.session_id and 'session_id' in self.session.cookies:
            self.session_id = self.session.cookies['session_id']

        if self.session_id:
            logger.info("Аутентификация в UTM5 успешна")
            return True

        logger.warning("Аутентификация не удалось: sessoin_id не получен в ответе")
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

def _ensure_authenticated(self) -> bool:
    """
    Вспомогательный метод: проверяет и выполняет аутентификацию при необходимости
    """
    if not self.session_id:
        return self.authenticate()
    return True