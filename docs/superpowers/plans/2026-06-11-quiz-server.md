# Hlasovací quiz server — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Lokální hlasovací server (FastAPI + SQLite) s animovaným promítaným UI a ESP8266 klientem pro poslední hodinu elektrotechniky — DNES.

**Architecture:** Jeden `server.py` (FastAPI, SQLite, statika), jeden `index.html` (vanilla JS/CSS, polling 1 s, canvas konfety, WebAudio), jeden `esp_hlasovatko.ino` (polling 2 s přes millis(), Serial vstup A–D → POST). Spec: `docs/superpowers/specs/2026-06-11-quiz-server-design.md`.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, sqlite3 (stdlib), pytest + httpx; Arduino ESP8266 core.

---

### Task 1: Server API s testy

**Files:**
- Create: `kviz/server.py`, `kviz/requirements.txt`, `kviz/test_server.py`

- [ ] **Step 1: requirements.txt** — `fastapi`, `uvicorn[standard]`, `pytest`, `httpx`
- [ ] **Step 2: Failing testy** v `kviz/test_server.py` (TestClient, tmp DB přes env `KVIZ_DB`):
  - `test_zadna_otazka` — GET `/api/otazka` → text začíná `0`
  - `test_vytvor_otazku_a_poll` — POST `/api/admin/otazka` {text,a,b,c,d} → GET `/api/otazka` vrátí id 1 na 1. řádku + text otázky a možnosti
  - `test_odpoved_upsert` — 2× POST `/api/odpoved?nick=Pepa` (A pak B) → `/api/vysledky` má Pepu jen u B, počty A=0 B=1
  - `test_odpoved_validace` — volba "X" → 400; bez aktivní otázky → 409; prázdný/dlouhý nick → 400
  - `test_delete_odpoved` — DELETE `/api/admin/odpoved?nick=Pepa` → zmizí z výsledků
  - `test_odhalit` — POST `/api/admin/odhalit` {volba:"B"} → `/api/vysledky` má `spravna:"B"`
  - `test_nova_otazka_resetuje` — druhá admin otázka → odpovědi se vážou k id 2, výsledky prázdné
- [ ] **Step 3: Run** `python -m pytest kviz/test_server.py -v` → FAIL (server.py neexistuje)
- [ ] **Step 4: Implementace `server.py`** — endpoints dle spec tabulky, SQLite schéma dle spec, UPSERT `ON CONFLICT(otazka_id,nick) DO UPDATE`, `/api/info` vrací LAN IP (UDP socket trik na 8.8.8.8), mount statiky, `GET /` → `index.html`
- [ ] **Step 5: Run testy** → PASS
- [ ] **Step 6: Commit** `feat: kviz server API`

### Task 2: Promítané UI — layout + admin

**Files:**
- Create: `kviz/static/index.html` (jediný soubor: CSS+JS inline)

- [ ] **Step 1: Struktura** — hlavička (IP z `/api/info`, editovatelné SSID/heslo → localStorage), levý admin panel (textarea + 4 inputy + „Uložit a spustit" + „Odhalit" výběr A–D), pravý panel se 4 sloupci A–D
- [ ] **Step 2: Polling JS** — `setInterval(1000)` na `/api/vysledky`, render sloupců (výška dle podílu hlasů), jmenovky-chips pod sloupci, klik na chip → confirm → DELETE
- [ ] **Step 3: Ruční test** — spustit `uvicorn`, curl vytvořit otázku + 3 odpovědi, ověřit v prohlížeči
- [ ] **Step 4: Commit** `feat: kviz UI layout + polling`

### Task 3: Gamifikace a animace

**Files:**
- Modify: `kviz/static/index.html`

- [ ] **Step 1: Živé pozadí** — animovaný gradient + 3 plovoucí blob divy (CSS keyframes)
- [ ] **Step 2: Animace hlasů** — diff nových nicků mezi polly: nový chip = fly-in/bounce (CSS), sloupec spring-grow (transition cubic-bezier overshoot), pulz; počítadlo „🔥 N hlasů" pop
- [ ] **Step 3: Konfety canvas** — fullscreen canvas, burst u sloupce při novém hlasu (malý), megaburst při „Odhalit" + zšednutí ostatních sloupců + glow vítěze
- [ ] **Step 4: WebAudio pop** — krátký oscilátor „pop" při hlasu, fanfára (3 tóny) při odhalení; tlačítko mute
- [ ] **Step 5: Nová otázka** — wipe přechod výsledků, otázka se „napíše" (typewriter)
- [ ] **Step 6: Ruční test v prohlížeči** (curl simulace hlasů), vizuální kontrola
- [ ] **Step 7: Commit** `feat: kviz animace + gamifikace`

### Task 4: ESP8266 hlasovátko

**Files:**
- Create: `kviz/esp_hlasovatko.ino`

- [ ] **Step 1: Sketch** — styl repa („---- SEM napiš ----", české komentáře): konfigurace NICK/SSID/HESLO/SERVER_IP; `setup()` WiFi; `loop()`: millis() polling 2 s GET `/api/otazka` (WiFiClient, ne HTTPS — komentář proč), nové id → vypiš otázku; `Serial.available()` čtení řádku, A–D → POST `/api/odpoved?nick=` s `{"volba":"X"}`, potvrzení/chyba česky; komentář-blok „NOVINKA: polling a proč ne delay()"
- [ ] **Step 2: Kontrola kompilovatelnosti** — arduino-cli pokud je, jinak pečlivá revize (HTTPClient API dle existujících .ino v repu)
- [ ] **Step 3: Commit** `feat: ESP hlasovatko sketch`

### Task 5: Otázky na hodinu + README

**Files:**
- Create: `kviz/OTAZKY.md`, `kviz/README.md`

- [ ] **Step 1: OTAZKY.md** — 3 bloky: (1) kvíz z učiva — rezistory, PWM, button, I2C, maticový panel, HTTP GET/POST (~8 otázek s odpověďmi A–D + správná), (2) zpětná vazba (~4), (3) hlasování o příštím roce IoT (~4: MQTT/home automation/meteostanice/robot…)
- [ ] **Step 2: README.md** — instalace (`pip install -r requirements.txt`), spuštění (`uvicorn server:app --host 0.0.0.0 --port 8000`), checklist před hodinou (router, IP, firewall povolit port, smoke test s 1 ESP)
- [ ] **Step 3: Commit** `docs: otazky na hodinu + README`

### Task 6: End-to-end smoke test

- [ ] **Step 1: Spustit server**, curl scénář ze spec (otázka → otazka GET → 2× POST stejný nick → přepis → DELETE → odhalit), ověřit UI v prohlížeči (chrome-devtools screenshot)
- [ ] **Step 2: Fix čehokoli, commit** `chore: smoke test fixes`
