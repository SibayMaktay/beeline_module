import os
from dotenv import load_dotenv
from functools import lru_cache

dotenv_path = "./config/.env"
load_dotenv(dotenv_path=dotenv_path)

# ============================================================================
# BEELINE
# ============================================================================
beeline_login = os.getenv("BEELINE_LOGIN", "").split()
beeline_password = os.getenv("BEELINE_PASSWORD", "").strip()
beeline_url_base = os.getenv("BEELINE_URL_BASE", "https://my.beeline.ru").strip()
beeline_rest_signature = os.getenv("BEELINE_REST_SIGNATURE", "").strip()

# ============================================================================
# UTM5
# ============================================================================
utm5_url_base = os.getenv("UTM5_URL_BASE", "http://127.0.0.1:9080").strip()
utm5_api_prefix = os.getenv("UTM5_API_PREFIX", "/api").strip()

# Авторизация
utm5_api_key = os.getenv("UTM5_API_KEY").strip()
utm5_login = os.getenv("UTM5_LOGIN", "").strip()
utm5_password = os.getenv("UTM5_PASSWORD", "").strip()

# HTTP поведение
utm5_timeout = float(os.getenv("UTM5_TIMEOUT", "30"))
utm5_max_retries = int(os.getenv("UTM5_MAX_RETRIES", "3"))
utm5_retry_backoff = float(os.getenv("UTM5_RETRY_BACKOFF", "0.5"))
utm5_verify_ssl = os.getenv("UTM5_VERIFY_SSL", "true").lower() in ("1", "true", "yes")

# Бизнес-параметры платежей
utm5_payment_method_id = int(os.getenv("UTM5_PAYMENT_METHOD_ID", "1"))
utm5_currency_id = int(os.getenv("UTM5_CURRENCY_ID", "1"))
utm5_payment_comment_prefix = os.getenv("UTM5_PAYMENT_COMMENT_PREFIX", "Beeline").strip()
utm5_turn_on_inet = int(os.getenv("UTM5_TURN_ON_INET", "1"))

# ============================================================================
# МОСТ (Beeline ↔ UTM5)
# ============================================================================
module_host = os.getenv("MODULE_HOST", "127.0.0.1").strip()
module_port = int(os.getenv("MODULE_PORT", "9090"))
module_api_key = os.getenv("MODULE_API_KEY", "bee_test").strip()

# ============================================================================
# ЛОГИРОВАНИЕ
# ============================================================================
log_level = os.getenv("LOG_LEVEL", "INFO").strip() # default = INFO
#log_file = "/var/log/beeline_module/module.log" # default = /var/log/beeline_module/module.log

# ============================================================================
# Валидация при импорте
# ============================================================================
def validate_config():
    """
    Проверяет обязательные параметры при старте приложения.
    """
    errors = []

    # Beeline
    if not beeline_login:
        errors.append("BEELINE_LOGIN не задан")
    if not beeline_password:
        errors.append("BEELINE_PASSWORD не задан")

    # UTM5
    if not utm5_url_base:
        errors.append("UTM5_BASE_URL не задан")

    if not utm5_api_key and not (utm5_login and utm5_password):
        errors.append("Нужен либо UTM5_API_KEY, либо пара UTM5_LOGIN/UTM5_PASSWORD")

    # Мост
    if not module_api_key:
        errors.append("MODULE_API_KEY не задан (ключ для проверки запросов)")

    if errors:
        error_msg = "\n".join(f"  ❌ {e}" for e in errors)
        raise ValueError(f"Ошибки конфигурации:\n{error_msg}")

# Валидируем при первом импорте
validate_config()