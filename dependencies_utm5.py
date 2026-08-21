from __future__ import annotations

import os
from functools import lru_cache

from fastapi import Depends

from services import (
    BeelineUTM5Mapper,
    BlockSyncService,
    PaymentLedger,
    PaymentSyncService,
    TariffSyncService,
)
from utm5 import UTM5Client


# ---------------------------------------------------------------------- #
# синглтоны процесса
# ---------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def get_utm5_client() -> UTM5Client:
    """
    Один клиент на процесс: внутри requests.Session с keep-alive,
    поэтому пересоздавать его на каждый запрос расточительно.
    """
    return UTM5Client()


@lru_cache(maxsize=1)
def get_payment_ledger() -> PaymentLedger:
    return PaymentLedger(os.getenv("PAYMENT_LEDGER_DB", "./store/payments.db"))


@lru_cache(maxsize=1)
def get_mapper() -> BeelineUTM5Mapper:
    return BeelineUTM5Mapper(get_utm5_client())


# ---------------------------------------------------------------------- #
# сервисы
# ---------------------------------------------------------------------- #
def get_payment_sync_service(
    client: UTM5Client = Depends(get_utm5_client),
    mapper: BeelineUTM5Mapper = Depends(get_mapper),
    ledger: PaymentLedger = Depends(get_payment_ledger),
) -> PaymentSyncService:
    return PaymentSyncService(client, mapper, ledger)


def get_tariff_sync_service(
    client: UTM5Client = Depends(get_utm5_client),
    mapper: BeelineUTM5Mapper = Depends(get_mapper),
) -> TariffSyncService:
    return TariffSyncService(client, mapper)


def get_block_sync_service(
    client: UTM5Client = Depends(get_utm5_client),
    mapper: BeelineUTM5Mapper = Depends(get_mapper),
) -> BlockSyncService:
    return BlockSyncService(client, mapper)


# ---------------------------------------------------------------------- #
def shutdown_utm5() -> None:
    """Закрывает HTTP-сессию при остановке приложения (вызывать в lifespan)."""
    if get_utm5_client.cache_info().currsize:
        get_utm5_client().close()
        get_utm5_client.cache_clear()