# Hlasovací server pro poslední hodinu elektrotechniky — design

Datum: 2026-06-11

## Cíl

Zábavná aktivita na poslední hodinu: děti mají ESP8266 jako „hlasovací zařízení", učitel promítá moderní animované UI s live výsledky. Děti se mimochodem naučí polling (`loop()` + `millis()`), využijí GET/POST z minulé hodiny. Stejným nástrojem se posbírá zpětná vazba a nápady na příští rok (IoT).

## Prostředí

- Učitelovo Windows PC v lokální síti (vlastní přinesený router — žádná client isolation).
- Server: Python + FastAPI + SQLite, **jeden soubor `server.py`** + **jeden `index.html`** (vanilla JS/CSS, žádný build).
- Klienti: ESP8266, Arduino IDE, knihovny už známé dětem (`ESP8266WiFi`, `ESP8266HTTPClient`).

## Architektura

```
ESP8266 (×N dětí)  --GET /api/otazka (polling 2 s)-->   server.py (FastAPI)
                   --POST /api/odpoved?nick=X------->       |  SQLite (kviz.db)
Prohlížeč (projektor) --GET / + polling /api/vysledky-->    |
```

## API

| Metoda + cesta | Klient | Chování |
|---|---|---|
| `GET /api/otazka` | ESP | Plain text. 1. řádek = id aktivní otázky, další řádky = text otázky a možnosti A–D. Když žádná aktivní otázka, vrátí `0` na prvním řádku. ESP si pamatuje poslední id a vypíše do Serial jen novou otázku. |
| `POST /api/odpoved?nick=Pepa` | ESP | Body JSON `{"volba":"A"}`. Server přiřadí k **aktuálně aktivní** otázce. Opakovaná odpověď stejného nicku tutéž otázku **přepíše** (UPSERT) — dítě se opraví samo. Validace: volba ∈ {A,B,C,D}, nick neprázdný, max 20 znaků. Mimo aktivní otázku → 409. |
| `GET /` | učitel | Promítané UI (viz níže). |
| `POST /api/admin/otazka` | UI | JSON `{text, a, b, c, d}` → INSERT, nová otázka se stane aktivní. = tlačítko „Uložit a spustit" i „Další otázka" (vždy vytvoří novou řádku). |
| `POST /api/admin/odhalit` | UI | JSON `{volba}` → označí správnou odpověď aktivní otázky (sloupec UI oslaví). |
| `DELETE /api/admin/odpoved?nick=X` | UI | Smaže odpověď žáka u aktivní otázky (klik na jmenovku v grafu). |
| `GET /api/vysledky` | UI | JSON: aktivní otázka + počty A–D + seznam nicků u každé možnosti + případná odhalená správná odpověď. UI polluje každou 1 s. |
| `GET /api/info` | UI | IP adresa serveru (autodetekce), pro hlavičku. |

## DB schéma (SQLite, soubor `kviz.db`)

```sql
CREATE TABLE otazky (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  text TEXT NOT NULL,
  a TEXT NOT NULL, b TEXT NOT NULL, c TEXT NOT NULL, d TEXT NOT NULL,
  spravna TEXT,              -- NULL dokud neodhaleno
  vytvoreno TEXT DEFAULT (datetime('now'))
);
CREATE TABLE odpovedi (
  otazka_id INTEGER NOT NULL REFERENCES otazky(id),
  nick TEXT NOT NULL,
  volba TEXT NOT NULL CHECK (volba IN ('A','B','C','D')),
  cas TEXT DEFAULT (datetime('now')),
  PRIMARY KEY (otazka_id, nick)   -- UPSERT: poslední odpověď vyhrává
);
```

Aktivní otázka = řádek s nejvyšším `id`. Žádný stav navíc.

## UI (promítané, jedna stránka)

**Hlavička:** velká IP serveru (např. `http://192.168.0.10:8000`), editovatelná políčka SSID + heslo WiFi (persistuje localStorage). Vše velké — čitelné ze zadní lavice.

**Levý panel (admin, ~1/3):** textarea otázka, 4 inputy A–D, tlačítka **Uložit a spustit** a **Odhalit správnou** (vybere A–D). Po spuštění se formulář vyčistí pro další otázku.

**Pravý panel (live výsledky, ~2/3):** 4 svislé sloupce A–D s textem možnosti, pod/v každém sloupci jmenovky (chips) hlasujících. Klik na jmenovku → confirm → DELETE odpovědi.

**Gamifikace a animace (důraz!):**
- Nová došlá odpověď: jmenovka **vlétne** do sloupce (pop/bounce), krátký confetti burst, zvukový „pop" (WebAudio, žádné soubory).
- Sloupce rostou pružinovou (spring) animací, při změně pulznou.
- Živé pozadí: pomalu se přelévající gradient + plovoucí blob tvary — pořád se něco hýbe.
- Počítadlo „🔥 N hlasů" s pop efektem při každém hlasu.
- „Odhalit": vítězný sloupec exploduje konfetami přes celou obrazovku, ostatní zšednou; nicky u správné odpovědi zazáří.
- Nová otázka: panel výsledků se promáznе s přechodovou animací, otázka „napíše se" na obrazovku.
- Vše vanilla CSS animace + malý canvas pro konfety. Žádné externí CDN — učebna nemusí mít internet.

## ESP kód (`esp_hlasovatko.ino`)

Stejný didaktický styl jako existující `.ino` v repu („---- SEM napiš ----", husté české komentáře):

1. Konfigurace nahoře: `NICK`, `SSID`, `HESLO`, `SERVER_IP`.
2. `setup()`: WiFi připojení (známé z minula), Serial 115200.
3. `loop()` — **novinka hodiny — polling:**
   - každé 2 s (přes `millis()`, komentář proč ne `delay()` — aby šlo zároveň číst klávesnici) `GET /api/otazka`;
   - když se id liší od posledního → vypíše otázku do Serial monitoru;
   - čte Serial vstup: žák napíše `A`/`B`/`C`/`D` + Enter → `POST /api/odpoved?nick=...` s JSON body → vypíše potvrzení „Odpoved odeslana!" / chybu.
4. HTTP přes plain `WiFiClient` (lokální síť, žádné HTTPS) — jednodušší než minule, stojí za komentář.

## Chyby

- ESP: timeouty a ne-200 odpovědi vypsat do Serial česky („Server neodpovida, zkusim za chvili").
- Server: validace vstupů (volba, nick, prázdná otázka → 400/409 s českou hláškou).
- UI: když `/api/vysledky` spadne, ukáže nenápadný „offline" indikátor, polling běží dál.

## Testování

- Ruční: `curl` scénář (vytvoř otázku → ESP GET → 2× POST stejný nick → ověř přepis → DELETE → odhalit).
- Mini pytest na API logiku (upsert, aktivní otázka, validace) — rychlé, server je jeden soubor.
- Před hodinou: smoke test s jedním reálným ESP.

## Mimo rozsah (YAGNI)

Leaderboard/skóre, autentizace admina (lokální síť, jednorázovka), historie otázek v UI, HTTPS, perzistence mezi hodinami.

## Dodávky

1. `kviz/server.py` + `kviz/static/index.html` (+ `requirements.txt`)
2. `kviz/esp_hlasovatko.ino`
3. `kviz/OTAZKY.md` — připravené otázky na hodinu: kvíz z učiva (rezistory, PWM, I2C…), zpětná vazba, hlasování o náplni příštího roku (IoT témata)
4. `kviz/README.md` — jak spustit (jeden příkaz), checklist před hodinou
