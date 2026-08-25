"""
Тесты моста Beeline <-> UTM5.

Запуск:  pytest tests/test_utm5.py -v

Мост не содержит своей бизнес-логики (mapper/ledger/*_sync больше нет),
поэтому тесты бьют напрямую в utm5/*.py (SDK) и в утилиту
routers.utm5_router._resolve_account, которая свод к минимуму решает,
какой account_id использовать.
"""

from __future__ import annotations

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from routers.utm5_router import _resolve_account  # noqa: E402
from utm5 import UTM5Client, UTM5NotFound, UTM5Settings, UTM5BadRequest  # noqa: E402
from utm5.transport import UTM5Transport  # noqa: E402

# ---------------------------------------------------------------------- #
# фейковый UTM5
# ---------------------------------------------------------------------- #
class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.content = b"x"
        self.text = str(self._payload)
        self.cookies = {}

    def json(self):
        return self._payload

class FakeUTM5Session:
    """
    Минимальная имитация REST API UTM5 на requests.Session.
    """
    def __init__(self):
        self.calls = []
        self.payments = []
        self.tariff_links = [
            {"id": 10, "account_id": 100, "current_tariff_id": 1, "accounting_period_id": 5}
        ]
        self.account = {
            "account_id": 100, "user_id": 42, "balance": 15.5, "credit": 0.0,
            "block_type": 0, "external_id": "", "contract_number": "Д-1",
            "vat_rate": 0.0, "int_status": 1,
        }
        self.fail_next_payment = False

    def request(
        self,
        method,
        url,
        params=None,
        json=None,
        cookies=None,
        timeout=None,
        verify=None
    ):
        path = url.split("/api/", 1)[-1]
        self.calls.append((method, path, params, json))

        if path == "users/search":
            value = (json or {}).get("value", "")
            if value in ("9608029838", "79608029838", "+79608029838"):
                return FakeResponse(200, {
                    "user_id": "42", "login": "ivanov", "full_name": "Иванов И.И.",
                    "basic_account": "100", "accounts": ["100"], "email": "",
                })
            return FakeResponse(200, [])

        if path == "users/accounts":
            if method == "PUT":
                self.account["block_type"] = (json or {}).get("block_type", 0)
                return FakeResponse(200, {"result": "ok"})
            account_id = (params or {}).get("account_id")
            if account_id and str(account_id) != str(self.account["account_id"]):
                return FakeResponse(404, {"error": "not found"})
            return FakeResponse(200, [dict(self.account)])

        if path == "users/tarifflinks":
            if method == "POST":
                self.tariff_links[0]["current_tariff_id"] = json["first_tariff_id"]
                return FakeResponse(200, {"tariff_link_id": 10})
            return FakeResponse(200, list(self.tariff_links))

        if path == "tariffing/tariffs":
            return FakeResponse(200, [
                {"id": 1, "name": "Базовый"}, {"id": 2, "name": "Безлимитный 100"},
            ])

        if path == "tariffing/payments":
            if self.fail_next_payment:
                self.fail_next_payment = False
                return FakeResponse(500, {"error": "billing busy"})
            self.payments.append(json)
            return FakeResponse(200, {"payment_transaction_id": 1000 + len(self.payments)})

        if path == "users/blocks_info":
            return FakeResponse(200, [])

        return FakeResponse(404, {"error": f"unknown path {path}"})

    def post(self, url, json=None, timeout=None, verify=None):
        return self.request("POST", url, json=json)

    def close(self):
        pass


@pytest.fixture
def settings():
    return UTM5Settings(
        base_url="http://utm.test",
        api_prefix="/api",
        permanent_token="TESTTOKEN",
        login="",
        password="",
        timeout=5.0,
        max_retries=3,
        retry_backoff=0.0,
        verify_ssl=False,
        payment_method_id=1,
        currency_id=1,
        payment_comment_prefix="Beeline",
        turn_on_inet=1,
    )


@pytest.fixture
def fake_session():
    return FakeUTM5Session()


@pytest.fixture
def client(settings, fake_session):
    transport = UTM5Transport(settings, session=fake_session)
    return UTM5Client(settings, session=fake_session, transport=transport)

# ---------------------------------------------------------------------- #
# поиск абонента (utm5/users.py)
# ---------------------------------------------------------------------- #
def test_find_user_by_phone_tries_formats(client):
    user = client.users.find_by_phone("+7 (960) 802-98-38")
    assert user is not None
    assert user.user_id == 42
    assert user.preferred_account_id == 100

def test_unknown_phone_returns_none(client):
    assert client.users.find_by_phone("9990000000") is None

# ---------------------------------------------------------------------- #
# мост: определение account_id — единственная "логика" роутера
# ---------------------------------------------------------------------- #
def test_resolve_account_by_ctn(client):
    user_id, account_id = _resolve_account(client, ctn="9608029838", account_id=None, user_id=None)
    assert user_id == 42
    assert account_id == 100


def test_resolve_account_by_ctn_not_found_raises_404_class(client):
    with pytest.raises(UTM5NotFound):
        _resolve_account(client, ctn="9990000000", account_id=None, user_id=None)


def test_resolve_account_by_account_id_direct(client):
    """
    Второй вариант идентификации: account_id передан явно, поиск по ctn не выполняется.
    """
    user_id, account_id = _resolve_account(client, ctn=None, account_id=100, user_id=None)
    assert account_id == 100
    assert user_id == 42  # доёргано из карточки счёта


def test_resolve_account_by_account_id_with_user_id_skips_lookup(client, fake_session):
    """Если передали и account_id, и user_id — GET users/accounts не должен вызываться."""
    user_id, account_id = _resolve_account(client, ctn=None, account_id=100, user_id=42)
    assert (user_id, account_id) == (42, 100)
    assert not any(c[1] == "users/accounts" and c[0] == "GET" for c in fake_session.calls)


def test_resolve_account_unknown_account_id_raises_404(client):
    with pytest.raises(UTM5NotFound):
        _resolve_account(client, ctn=None, account_id=999, user_id=None)


def test_resolve_account_without_any_identifier_raises_bad_request(client):
    with pytest.raises(UTM5BadRequest):
        _resolve_account(client, ctn=None, account_id=None, user_id=None)

# ---------------------------------------------------------------------- #
# платежи — мост не проверяет дубли, просто передаёт вызов дальше
# ---------------------------------------------------------------------- #
def test_payment_create_hits_utm5_and_returns_transaction_id(client, fake_session):
    from utm5 import PaymentRequest

    payment = client.payments.create(
        PaymentRequest(account_id=100, user_id=42, amount=500, comment="test")
    )
    assert payment.transaction_id == 1001
    assert len(fake_session.payments) == 1

    payment2 = client.payments.create(
        PaymentRequest(account_id=100, user_id=42, amount=500, comment="test")
    )
    assert payment2.transaction_id == 1002
    assert len(fake_session.payments) == 2

def test_payment_zero_amount_is_rejected_before_http_call(client, fake_session):
    from utm5 import PaymentRequest, UTM5BadRequest as PaymentBadRequest

    with pytest.raises(PaymentBadRequest):
        client.payments.create(PaymentRequest(account_id=100, user_id=42, amount=0, comment="x"))
    assert len(fake_session.payments) == 0

def test_payment_post_is_not_retried_on_5xx(settings):
    """
    Ключевая защита от двойного списания: POST платежа не повторяется,
    потому что UTM5 мог записать его и упасть уже на ответе.
    """
    class CountingSession:
        def __init__(self):
            self.attempts = 0

        def request(self, method, url, **kwargs):
            self.attempts += 1
            return FakeResponse(500, {"error": "boom"})

    session = CountingSession()
    transport = UTM5Transport(settings, session=session)
    with pytest.raises(Exception):
        transport.post("tariffing/payments", {"account_id": 1})
    assert session.attempts == 1, "POST платежа не должен повторяться"

# ---------------------------------------------------------------------- #
# тарифы (utm5/tariffs.py)
# ---------------------------------------------------------------------- #
def test_tariff_assign_by_id(client):
    result = client.tariffs.assign(user_id=42, account_id=100, tariff_id=2, change_now=True)
    assert result["tariff_link_id"] == 10

def test_tariff_require_by_name(client):
    tariff = client.tariffs.require_by_name("Безлимитный 100")
    assert tariff.tariff_id == 2

def test_tariff_unknown_name_reises_not_found(client):
    with pytest.raises(UTM5NotFound):
        client.tariffs.require_by_name("Такого тарифа нет")

# ---------------------------------------------------------------------- #
# блокировки (utm5/blocks.py)
# ---------------------------------------------------------------------- #
def test_block_and_unblock(client, fake_session):
    account = client.users.get_account(100)
    client.blocks.block(account, block_type=2)
    assert fake_session.account["block_type"] == 2

    account = client.users.get_account(100)
    client.blocks.unblock(account)
    assert fake_session.account["block_type"] == 0

def test_block_update_preserves_contract_fields(client, fake_session):
    account = client.users.get_account(100)
    client.blocks.block(account, block_type=2)
    put_calls = [c for c in fake_session.calls if c[0] == "PUT" and c[1] == "users/accounts"]
    body = put_calls[-1][3]
    assert body["contract_number"] == "Д-1"
    assert body["credit"] == 0.0

# ---------------------------------------------------------------------- #
# транспорт (utm5/transport.py)
# ---------------------------------------------------------------------- #
def test_transport_sends_token_cookie(settings, fake_session):
    transport = UTM5Transport(settings, session=fake_session)
    captured = {}

    original = fake_session.request

    def spy(method, url, **kwargs):
        captured.update(kwargs)
        return original(method, url, **kwargs)

    fake_session.request = spy
    transport.get("tariffing/tariffs")
    assert captured["cookies"] == {"token": "TESTTOKEN"}


def test_transport_retries_on_5xx(settings):
    class FlakySession:
        def __init__(self):
            self.attempts = 0

        def request(self, method, url, **kwargs):
            self.attempts += 1
            if self.attempts < 3:
                return FakeResponse(503, {"error": "try later"})
            return FakeResponse(200, {"ok": True})

    session = FlakySession()
    transport = UTM5Transport(settings, session=session)
    assert transport.get("tariffing/tariffs") == {"ok": True}
    assert session.attempts == 3


def test_transport_raises_not_found(settings, fake_session):
    transport = UTM5Transport(settings, session=fake_session)
    with pytest.raises(Exception):
        transport.get("users", {"user_id": 999999})