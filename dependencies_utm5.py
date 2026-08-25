from __future__ import annotations
import logging
from functools import lru_cache
from utm5 import UTM5Client
logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_utm5_client() -> UTM5Client:
    """
    Один клиент на процесс: внутри requests.Session с keep-alive,
    поэтому пересоздавать его на каждый запрос расточительно.
    """
    logger.info("Инициализация UTM5 клиента...")
    client = UTM5Client()
    logger.info("UTM5 клиент создан (api_url=%s)", client.settings.api_url)
    return client

def shutdown_utm5() -> None:
    """
    Закрывает HTTP-сессию при остановке приложения (вызывать в lifespan).
    """
    if get_utm5_client.cache_info().currsize:
        get_utm5_client().close()
        get_utm5_client.cache_clear()
        logger.info("UTM5 клиент закрыт")