"""
Смоук-тесты модуля: проверяем, что все endpoints корректно связаны с клиентами.
Сеть не используется - клиенты Beeline/UTM5 замоканы.
Запуск: pytest -q
"""
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

import beeline_client, beeline_rest_client, utm5_client
beeline_client.BeelineClient.authenticate = lambda self, *a, **k: True
beeline_rest_client.BeelineRestClient.authenticate = lambda self, *a, **k: True
utm5_client.UTM5Client.authenticate = lambda self, *a, **k: True

import app as appmod


@pytest.fixture
def client():
    with TestClient(appmod.app) as c:
        # Подменяем боевые клиенты на моки уже после старта lifespan
        appmod.beeline_client = MagicMock()
        appmod.beeline_rest = MagicMock()
        appmod.utm5_client = MagicMock()
        appmod.utm5_client.session_id = "sess-123"
        yield c

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"

def test_rests(client):
    appmod.beeline_rest.get_rests.return_value = {"data": [{"name": "GB", "value": 10}]}
    r = client.get("/rests/79608029838")
    assert r.status_code == 200
    assert r.json()["data"]["data"][0]["value"] == 10
    appmod.beeline_rest.get_rests.assert_called_once_with("79608029838")

def test_subscriptions(client):
    appmod.beeline_rest.get_subscriptions.return_value = {"subs": []}
    r = client.get("/subscriptions/79608029838")
    assert r.status_code == 200 and r.json()["status"] == "success"

def test_callforward(client):
    appmod.beeline_rest.get_call_forward.return_value = {"forward": "off"}
    r = client.get("/callforward/79608029838")
    assert r.status_code == 200

def test_rests_upstream_error(client):
    appmod.beeline_rest.get_rests.return_value = None
    r = client.get("/rests/79608029838")
    assert r.status_code == 502

def test_balance(client):
    appmod.beeline_client.get_unbilled_balances.return_value = {"balance": 100}
    r = client.get("/balance/906144076")
    assert r.status_code == 200
    appmod.beeline_client.get_unbilled_balances.assert_called_once_with("906144076")

def test_service_add(client):
    appmod.beeline_client.manage_service.return_value = {"ok": True}
    r = client.post("/service", json={"phone_number": "79608029838", "soc_code": "EXCLH12", "add": True})
    assert r.status_code == 200
    assert r.json()["action"] == "ADD"
    appmod.beeline_client.manage_service.assert_called_once_with("79608029838", "EXCLH12", True)

def test_block_unblock(client):
    appmod.beeline_client.suspend_ctn.return_value = {"ok": 1}
    appmod.beeline_client.restore_ctn.return_value = {"ok": 1}
    assert client.post("/block/79608029838").status_code == 200
    assert client.post("/unblock/79608029838").status_code == 200

def test_sim_replace(client):
    appmod.beeline_client.replace_sim.return_value = {"ok": 1}
    r = client.post("/sim/replace", json={"phone_number": "79608029838", "new_sim": "897019924111165944"})
    assert r.status_code == 200
    appmod.beeline_client.replace_sim.assert_called_once_with("79608029838", "897019924111165944")

def test_auth_beeline(client):
    appmod.beeline_client.authenticate.return_value = True
    r = client.post("/auth/beeline", json={"login": "l", "password": "p"})
    assert r.status_code == 200 and r.json()["status"] == "success"

def test_tariff_change_unknown_code(client):
    # неизвестный код тарифа -> 400 (нет маппинга)
    appmod.beeline_client.change_tariff.return_value = {"ok": 1}
    r = client.post("/tariff/change", json={
        "phone_number": "79608029838", "new_tariff_code": "NOPE", "utm5_user_id": 1})
    assert r.status_code == 400