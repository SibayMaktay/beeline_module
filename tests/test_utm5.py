"""
Запуск:  pytest tests/test_utm5.py -v
"""

from __future__ import annotations

import os
import sys
import tempfile

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services import BeelineUTM5Mapper, BlockSyncService, PaymentLedger, PaymentSyncService, TariffSyncService  # noqa: E402
from utm5 import UTM5Client, UTM5NotFound, UTM5Settings  # noqa: E402
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
    """Минимальная имитация REST API UTM5 на requests.Session."""

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

    def request(self, method, url, params=None, json=None, cookies=None, timeout=None, verify=None):
        path = url.split("/api/", 1)[-1]
        self.calls.append((method, path, params, json))

        if path == "users/search":
            value = (json or {}).get("value", "")
            if value in ("9161234567", "79161234567", "+79161234567"):
                return FakeResponse(200, [{
                    "user_id": "42", "login": "ivanov", "full_name": "Иванов И.И.",
                    "basic_account": "100", "accounts": ["100"], "email": "",
                }])
            return FakeResponse(200, [])

        if path == "users/accounts":
            if method == "PUT":
                self.account["block_type"] = (json or {}).get("block_type", 0)
                return FakeResponse(200, {"result": "ok"})
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
        base_url="http://utm.test", api_prefix="/api", permanent_token="TESTTOKEN",
        login="", password="", timeout=5.0, max_retries=3, retry_backoff=0.0,
        verify_ssl=False, payment_method_id=1, currency_id=1,
        payment_comment_prefix="Beeline", turn_on_inet=1,
    )


@pytest.fixture
def fake_session():
    return FakeUTM5Session()


@pytest.fixture
def client(settings, fake_session):
    transport = UTM5Transport(settings, session=fake_session)
    return UTM5Client(settings, session=fake_session, transport=transport)


@pytest.fixture
def mapper(client):
    return BeelineUTM5Mapper(client, tariff_map={"EXCLH12": 2, "EXCLH_BY_NAME": "Безлимитный 100"})


@pytest.fixture
def ledger():
    path = os.path.join(tempfile.mkdtemp(), "ledger.db")
    return PaymentLedger(path)


# ---------------------------------------------------------------------- #
# поиск абонента
# ---------------------------------------------------------------------- #
def test_find_user_by_phone_tries_formats(client):
    user = client.users.find_by_phone("+7 (916) 123-45-67")
    assert user is not None
    assert user.user_id == 42
    assert user.preferred_account_id == 100


def test_unknown_phone_returns_none(client):
    assert client.users.find_by_phone("9990000000") is None


def test_bind_subscriber_raises_when_absent(mapper):
    with pytest.raises(UTM5NotFound):
        mapper.bind_subscriber("9990000000")


# ---------------------------------------------------------------------- #
# платежи
# ---------------------------------------------------------------------- #
def test_payments_applied_once(client, mapper, ledger, fake_session):
    service = PaymentSyncService(client, mapper, ledger)
    raw = [
        {"paymentId": "P-1", "amount": "100,50", "date": "2026-08-01 12:00:00"},
        {"paymentId": "P-2", "amount": 250, "date": "2026-08-02 12:00:00"},
    ]

    first = service.sync("9161234567", raw)
    assert len(first.applied) == 2
    assert first.total_applied == 350.5
    assert len(fake_session.payments) == 2

    # повторная синхронизация тех же данных не должна зачислить деньги снова
    second = service.sync("9161234567", raw)
    assert len(second.applied) == 0
    assert len(second.duplicates) == 2
    assert len(fake_session.payments) == 2


def test_failed_payment_is_retryable(client, mapper, ledger, fake_session):
    service = PaymentSyncService(client, mapper, ledger)
    raw = [{"paymentId": "P-9", "amount": 90, "date": "2026-08-03"}]

    fake_session.fail_next_payment = True
    report = service.sync("9161234567", raw)
    assert len(report.failed) == 1
    assert len(fake_session.payments) == 0

    # бронь снята -> вторая попытка проходит
    retry = service.sync("9161234567", raw)
    assert len(retry.applied) == 1
    assert len(fake_session.payments) == 1


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


def test_zero_and_broken_amounts_do_not_crash(client, mapper, ledger):
    service = PaymentSyncService(client, mapper, ledger)
    report = service.sync("9161234567", [
        {"paymentId": "Z-1", "amount": 0},
        {"paymentId": "Z-2", "amount": "не число"},
    ])
    assert len(report.applied) == 0
    assert len(report.failed) == 2


def test_payment_body_matches_utm5_contract(client, mapper, ledger, fake_session):
    PaymentSyncService(client, mapper, ledger).sync(
        "9161234567", [{"paymentId": "C-1", "amount": 500, "date": "2026-08-01"}]
    )
    body = fake_session.payments[0]
    for field in ("account_id", "user_id", "payment_incurrency", "currency_id",
                  "actual_date", "method", "comment", "turn_on_inet"):
        assert field in body
    assert body["account_id"] == 100
    assert body["payment_incurrency"] == 500.0


# ---------------------------------------------------------------------- #
# тарифы
# ---------------------------------------------------------------------- #
def test_tariff_change_and_idempotency(client, mapper):
    service = TariffSyncService(client, mapper)

    result = service.sync("9161234567", "EXCLH12")
    assert result.changed is True
    assert result.previous_tariff_id == 1
    assert result.utm5_tariff_id == 2

    again = service.sync("9161234567", "EXCLH12")
    assert again.changed is False


def test_tariff_resolved_by_name(client, mapper):
    assert mapper.resolve_tariff_id("EXCLH_BY_NAME") == 2


def test_unknown_price_plan_is_reported(client, mapper):
    from utm5 import UTM5MappingError
    with pytest.raises(UTM5MappingError):
        mapper.resolve_tariff_id("NO_SUCH_PLAN")


# ---------------------------------------------------------------------- #
# блокировки
# ---------------------------------------------------------------------- #
def test_block_and_unblock(client, mapper, fake_session):
    service = BlockSyncService(client, mapper)

    blocked = service.sync("9161234567", blocked=True)
    assert blocked.changed is True
    assert fake_session.account["block_type"] == 2

    repeat = service.sync("9161234567", blocked=True)
    assert repeat.changed is False

    unblocked = service.sync("9161234567", blocked=False)
    assert unblocked.changed is True
    assert fake_session.account["block_type"] == 0


def test_block_update_preserves_contract_fields(client, mapper, fake_session):
    BlockSyncService(client, mapper).sync("9161234567", blocked=True)
    put_calls = [c for c in fake_session.calls if c[0] == "PUT" and c[1] == "users/accounts"]
    body = put_calls[-1][3]
    assert body["contract_number"] == "Д-1"
    assert body["credit"] == 0.0


# ---------------------------------------------------------------------- #
# транспорт
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
        transport.get("no/such/path")