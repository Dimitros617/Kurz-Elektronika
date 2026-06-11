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


def test_uprava_otazky_za_behu(client):
    nova_otazka(client)
    client.post("/api/odpoved?nick=Pepa", json={"volba": "A"})
    # úprava textu aktivní otázky — odpovědi zůstávají
    r = client.put("/api/admin/otazka/1", json={"text": "Kolik je 2+3?", "a": "4", "b": "5", "c": "6", "d": "7"})
    assert r.status_code == 200
    v = client.get("/api/vysledky").json()
    assert v["otazka_id"] == 1
    assert v["text"] == "Kolik je 2+3?"
    assert v["moznosti"]["B"] == "5"
    assert v["pocty"]["A"] == 1  # odpověď přežila editaci
    # update neexistující otázky -> 404
    r = client.put("/api/admin/otazka/99", json={"text": "x", "a": "1", "b": "2", "c": "3", "d": "4"})
    assert r.status_code == 404


def test_historie(client):
    nova_otazka(client, text="První?")
    nova_otazka(client, text="Druhá?")
    h = client.get("/api/admin/historie").json()
    assert [q["text"] for q in h] == ["Druhá?", "První?"]  # nejnovější první
    assert h[0]["id"] == 2 and "a" in h[0]


def test_aktivace_stare_otazky(client):
    # otázka 1 + 2 odpovědi
    nova_otazka(client, text="První?")
    client.post("/api/odpoved?nick=Pepa", json={"volba": "A"})
    client.post("/api/odpoved?nick=Anicka", json={"volba": "B"})
    # otázka 2 + odpověď
    nova_otazka(client, text="Druhá?")
    client.post("/api/odpoved?nick=Kuba", json={"volba": "C"})
    # zpět na první — odpovědi dětí se vrátí s ní
    r = client.post("/api/admin/aktivovat", json={"id": 1})
    assert r.status_code == 200
    v = client.get("/api/vysledky").json()
    assert v["otazka_id"] == 1 and v["text"] == "První?"
    assert v["nicky"]["A"] == ["Pepa"] and v["nicky"]["B"] == ["Anicka"]
    # třetí dítě může doodpovědět ke staré otázce
    client.post("/api/odpoved?nick=Terka", json={"volba": "A"})
    v = client.get("/api/vysledky").json()
    assert v["pocty"]["A"] == 2
    # ESP polling vrací reaktivovanou otázku
    assert client.get("/api/otazka").text.splitlines()[0] == "1"
    # odpovědi u druhé otázky zůstaly netknuté
    client.post("/api/admin/aktivovat", json={"id": 2})
    v = client.get("/api/vysledky").json()
    assert v["nicky"]["C"] == ["Kuba"]
    # aktivace neexistující -> 404
    assert client.post("/api/admin/aktivovat", json={"id": 99}).status_code == 404


def test_info(client):
    r = client.get("/api/info")
    assert r.status_code == 200
    assert "ip" in r.json()
