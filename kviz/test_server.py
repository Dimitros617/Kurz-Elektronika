"""Testy pro kvízový server. Spuštění: python -m pytest kviz/test_server.py -v"""
import os
import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("KVIZ_DB", str(tmp_path / "test_kviz.db"))
    import server
    importlib.reload(server)
    with TestClient(server.app) as c:
        yield c


def nova_otazka(client, text="Kolik je 2+2?", a="3", b="4", c="5", d="22"):
    r = client.post("/api/admin/otazka", json={"text": text, "a": a, "b": b, "c": c, "d": d})
    assert r.status_code == 200
    return r.json()


def test_zadna_otazka(client):
    r = client.get("/api/otazka")
    assert r.status_code == 200
    assert r.text.splitlines()[0] == "0"


def test_vytvor_otazku_a_poll(client):
    nova_otazka(client)
    r = client.get("/api/otazka")
    lines = r.text.splitlines()
    assert lines[0] == "1"
    assert "Kolik je 2+2?" in r.text
    assert "A) 3" in r.text and "B) 4" in r.text and "C) 5" in r.text and "D) 22" in r.text


def test_odpoved_upsert(client):
    nova_otazka(client)
    r1 = client.post("/api/odpoved?nick=Pepa", json={"volba": "A"})
    assert r1.status_code == 200
    r2 = client.post("/api/odpoved?nick=Pepa", json={"volba": "B"})
    assert r2.status_code == 200
    v = client.get("/api/vysledky").json()
    assert v["pocty"]["A"] == 0
    assert v["pocty"]["B"] == 1
    assert v["nicky"]["B"] == ["Pepa"]
    assert v["nicky"]["A"] == []


def test_odpoved_validace(client):
    # bez aktivní otázky -> 409
    r = client.post("/api/odpoved?nick=Pepa", json={"volba": "A"})
    assert r.status_code == 409
    nova_otazka(client)
    # neplatná volba -> 400
    r = client.post("/api/odpoved?nick=Pepa", json={"volba": "X"})
    assert r.status_code == 400
    # prázdný nick -> 400
    r = client.post("/api/odpoved?nick=", json={"volba": "A"})
    assert r.status_code == 400
    # moc dlouhý nick -> 400
    r = client.post("/api/odpoved?nick=" + "x" * 30, json={"volba": "A"})
    assert r.status_code == 400


def test_delete_odpoved(client):
    nova_otazka(client)
    client.post("/api/odpoved?nick=Pepa", json={"volba": "A"})
    r = client.delete("/api/admin/odpoved?nick=Pepa")
    assert r.status_code == 200
    v = client.get("/api/vysledky").json()
    assert v["pocty"]["A"] == 0
    assert v["nicky"]["A"] == []


def test_odhalit(client):
    nova_otazka(client)
    r = client.post("/api/admin/odhalit", json={"volba": "B"})
    assert r.status_code == 200
    v = client.get("/api/vysledky").json()
    assert v["spravna"] == "B"


def test_nova_otazka_resetuje(client):
    nova_otazka(client)
    client.post("/api/odpoved?nick=Pepa", json={"volba": "A"})
    nova_otazka(client, text="Druhá otázka?")
    r = client.get("/api/otazka")
    assert r.text.splitlines()[0] == "2"
    v = client.get("/api/vysledky").json()
    assert v["otazka_id"] == 2
    assert v["pocty"]["A"] == 0
    assert v["spravna"] is None


def test_info(client):
    r = client.get("/api/info")
    assert r.status_code == 200
    assert "ip" in r.json()
