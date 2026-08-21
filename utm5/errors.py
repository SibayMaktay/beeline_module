from typing import Any, Optional


class UTM5Error(Exception):
    """Базовая ошибка интеграции с UTM5."""

    def __init__(self, message: str, *, payload: Any = None):
        super().__init__(message)
        self.message = message
        self.payload = payload


class UTM5AuthError(UTM5Error):
    """Не удалось авторизоваться или сессия истекла (401/403)."""


class UTM5NotFound(UTM5Error):
    """Объект не найден: пользователь, лицевой счёт, тариф (404)."""


class UTM5BadRequest(UTM5Error):
    """UTM5 отверг запрос: неверные параметры (4xx, кроме 401/403/404)."""


class UTM5ServerError(UTM5Error):
    """UTM5 ответил 5xx — имеет смысл повторить попытку."""


class UTM5Unavailable(UTM5Error):
    """Сеть/таймаут: до UTM5 не достучались."""


class UTM5MappingError(UTM5Error):
    """Данные Beeline не удалось сопоставить с сущностями UTM5."""


def raise_for_status(status: int, body: Any, url: str) -> None:
    """Превращает HTTP-статус UTM5 в исключение нужного класса."""
    detail = _extract_detail(body)
    where = f"{url} -> HTTP {status}"

    if status in (401, 403):
        raise UTM5AuthError(f"UTM5 авторизация отклонена: {where}. {detail}", payload=body)
    if status == 404:
        raise UTM5NotFound(f"UTM5 объект не найден: {where}. {detail}", payload=body)
    if 400 <= status < 500:
        raise UTM5BadRequest(f"UTM5 отклонил запрос: {where}. {detail}", payload=body)
    if status >= 500:
        raise UTM5ServerError(f"UTM5 внутренняя ошибка: {where}. {detail}", payload=body)


def _extract_detail(body: Any) -> str:
    """UTM5 кладёт текст ошибки в разные поля — достаём что найдём."""
    if isinstance(body, dict):
        for key in ("error", "message", "detail", "result", "description"):
            value: Optional[Any] = body.get(key)
            if value:
                return str(value)[:500]
    if isinstance(body, str):
        return body[:500]
    return ""