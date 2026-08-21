from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class UTM5Settings:
    # --- подключение ---
    base_url: str                 # http://127.0.0.1:9080  или https://utm.example.ru
    api_prefix: str               # "/api" при проксировании через nginx, "" при прямом доступе к 9080

    # --- авторизация ---
    # Вариант A (рекомендуется): постоянный токен из веб-интерфейса администратора.
    permanent_token: str          # кладётся в cookie "token"
    # Вариант B: логин/пароль системного пользователя -> временный session_id (cookie "session_id").
    login: str
    password: str

    # --- поведение HTTP ---
    timeout: float
    max_retries: int
    retry_backoff: float
    verify_ssl: bool

    # --- бизнес-умолчания для платежей ---
    payment_method_id: int        # id из справочника "Методы платежей" (referencebooks/paymentmethods)
    currency_id: int
    payment_comment_prefix: str
    turn_on_inet: int             # 1 — включать интернет после платежа

    @property
    def api_url(self) -> str:
        """Полный корень REST API без завершающего слэша."""
        return f"{self.base_url.rstrip('/')}{self.api_prefix.rstrip('/')}"

    @property
    def uses_permanent_token(self) -> bool:
        return bool(self.permanent_token)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "y", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Переменная {name} должна быть целым числом, получено: {raw!r}") from exc


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Переменная {name} должна быть числом, получено: {raw!r}") from exc


@lru_cache(maxsize=1)
def get_utm5_settings() -> UTM5Settings:
    """
    Собирает настройки один раз за процесс.

    Требуется либо UTM5_TOKEN, либо пара UTM5_LOGIN/UTM5_PASSWORD.
    """
    settings = UTM5Settings(
        base_url=os.getenv("UTM5_BASE_URL", "http://127.0.0.1:9080").strip(),
        api_prefix=os.getenv("UTM5_API_PREFIX", "/api").strip(),
        permanent_token=os.getenv("UTM5_TOKEN", "").strip(),
        login=os.getenv("UTM5_LOGIN", "").strip(),
        password=os.getenv("UTM5_PASSWORD", "").strip(),
        timeout=_env_float("UTM5_TIMEOUT", 20.0),
        max_retries=_env_int("UTM5_MAX_RETRIES", 3),
        retry_backoff=_env_float("UTM5_RETRY_BACKOFF", 0.5),
        verify_ssl=_env_bool("UTM5_VERIFY_SSL", True),
        payment_method_id=_env_int("UTM5_PAYMENT_METHOD_ID", 1),
        currency_id=_env_int("UTM5_CURRENCY_ID", 1),
        payment_comment_prefix=os.getenv("UTM5_PAYMENT_COMMENT_PREFIX", "Beeline").strip(),
        turn_on_inet=_env_int("UTM5_TURN_ON_INET", 1),
    )

    if not settings.base_url:
        raise ValueError("UTM5_BASE_URL не задан")
    if not settings.permanent_token and not (settings.login and settings.password):
        raise ValueError(
            "Нужен либо UTM5_TOKEN (постоянный токен из веб-интерфейса), "
            "либо пара UTM5_LOGIN/UTM5_PASSWORD"
        )
    return settings