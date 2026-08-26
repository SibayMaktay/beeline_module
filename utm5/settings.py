from dataclasses import dataclass
from functools import lru_cache
import config.config as cfg

@dataclass(frozen=True)
class UTM5Settings:
    # --- подключение ---
    base_url: str # http://127.0.0.1:9080  или https://utm.example.ru
    api_prefix: str # "/api" при проксировании через nginx, "" при прямом доступе к 9080

    # --- авторизация ---
    # Вариант A (рекомендуется): постоянный токен из веб-интерфейса администратора.
    permanent_token: str # кладётся в cookie "token"
    # Вариант B: логин/пароль системного пользователя -> временный session_id (cookie "session_id").
    login: str
    password: str

    # --- поведение HTTP ---
    timeout: float
    max_retries: int
    retry_backoff: float
    verify_ssl: bool

    # --- бизнес-умолчания для платежей ---
    payment_method_id: int # id из справочника "Методы платежей" (referencebooks/paymentmethods)
    currency_id: int
    payment_comment_prefix: str
    turn_on_inet: int # 1 — включать интернет после платежа

    @property
    def api_url(self) -> str:
        """
        Полный корень REST API без завершающего слэша.
        """
        return f"{self.base_url.rstrip('/')}{self.api_prefix.rstrip('/')}"

    @property
    def uses_permanent_token(self) -> bool:
        """
        True если используется постоянный токен, иначе login/password.
        """
        return bool(self.permanent_token)

@lru_cache(maxsize=1)
def get_utm5_settings() -> UTM5Settings:
    """
    Собирает настройки один раз за процесс.

    Требуется либо UTM5_TOKEN, либо пара UTM5_LOGIN/UTM5_PASSWORD.
    """
    settings = UTM5Settings(
        base_url=cfg.utm5_url_base,
        api_prefix=cfg.utm5_api_prefix,
        permanent_token=cfg.utm5_api_key,
        login=cfg.utm5_login,
        password=cfg.utm5_password,
        timeout=cfg.utm5_timeout,
        max_retries=cfg.utm5_max_retries,
        retry_backoff=cfg.utm5_retry_backoff,
        verify_ssl=cfg.utm5_verify_ssl,
        payment_method_id=cfg.utm5_payment_method_id,
        currency_id=cfg.utm5_currency_id,
        payment_comment_prefix=cfg.utm5_payment_comment_prefix,
        turn_on_inet=cfg.utm5_turn_on_inet,
    )

    if not settings.base_url:
        raise ValueError("UTM5_BASE_URL не задан в config/config.py или .env")
    
    if not settings.permanent_token and not (settings.login and settings.password):
        raise ValueError(
            "Нужен либо UTM5_API_KEY (постоянный токен API из администраторского интерфейса), "
            "либо пара UTM5_LOGIN/UTM5_PASSWORD"
        )
    return settings