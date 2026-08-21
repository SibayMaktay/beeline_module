from __future__ import annotations

from typing import Optional

import requests

from .auth import UTM5Auth
from .blocks import BlockRepository
from .payments import PaymentRepository
from .settings import UTM5Settings, get_utm5_settings
from .tariffs import TariffRepository
from .transport import UTM5Transport
from .users import UserRepository


class UTM5Client:
    """Единая точка входа в UTM5."""

    def __init__(
        self,
        settings: Optional[UTM5Settings] = None,
        *,
        session: Optional[requests.Session] = None,
        transport: Optional[UTM5Transport] = None,
    ):
        self.settings = settings or get_utm5_settings()
        http_session = session or requests.Session()

        self.auth = UTM5Auth(self.settings, http_session)
        self.transport = transport or UTM5Transport(self.settings, self.auth, http_session)

        self.users = UserRepository(self.transport)
        self.payments = PaymentRepository(self.transport, self.settings)
        self.tariffs = TariffRepository(self.transport)
        self.blocks = BlockRepository(self.transport)

    # ------------------------------------------------------------------ #
    def ping(self) -> bool:
        """
        Проверка живости: любой дешёвый авторизованный GET.

        Возвращает True, если биллинг ответил и авторизация принята.
        """
        self.transport.get("tariffing/tariffs")
        return True

    def close(self) -> None:
        self.transport.close()

    # ------------------------------------------------------------------ #
    def __enter__(self) -> "UTM5Client":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()