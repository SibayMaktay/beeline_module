"""
Публичный интерфейс пакета utm5.

Единственная задача файла — зафиксировать, что именно импортирует
прикладной код, чтобы внутреннюю структуру пакета можно было менять.
"""

from .blocks import BLOCK_ADMIN, BLOCK_KEEP_CHARGES, BLOCK_NONE, BLOCK_VOLUNTARY
from .client import UTM5Client
from .errors import (
    UTM5AuthError,
    UTM5BadRequest,
    UTM5Error,
    UTM5MappingError,
    UTM5NotFound,
    UTM5ServerError,
    UTM5Unavailable,
)
from .models import (
    PaymentRequest,
    UTM5Account,
    UTM5Payment,
    UTM5Tariff,
    UTM5TariffLink,
    UTM5User,
)
from .settings import UTM5Settings, get_utm5_settings

__all__ = [
    "UTM5Client",
    "UTM5Settings",
    "get_utm5_settings",
    "UTM5User",
    "UTM5Account",
    "UTM5Tariff",
    "UTM5TariffLink",
    "UTM5Payment",
    "PaymentRequest",
    "UTM5Error",
    "UTM5AuthError",
    "UTM5NotFound",
    "UTM5BadRequest",
    "UTM5ServerError",
    "UTM5Unavailable",
    "UTM5MappingError",
    "BLOCK_NONE",
    "BLOCK_ADMIN",
    "BLOCK_VOLUNTARY",
    "BLOCK_KEEP_CHARGES",
]