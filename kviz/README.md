# ⚡ Hlasovátko — kvízový server pro hodinu elektrotechniky

Děti mají ESP8266 jako hlasovací zařízení, ty promítáš živý graf s konfetami.

## Spuštění serveru (na tvém PC)

```powershell
cd kviz
python -m pip install -r requirements.txt
python -m uvicorn server:app --host 0.0.0.0 --port 8000
```

Otevři **http://localhost:8000** a promítej. IP pro děti se ukáže v hlavičce
(např. `http://192.168.0.10:8000`). SSID a heslo WiFi dopiš do políček v hlavičce.

## ESP pro děti

`esp_hlasovatko.ino` — děti doplní jen 3 věci nahoře:
1. `NICK` — přezdívka
2. `SSID` + `HESLO` — z plátna
3. `SERVER` — IP z plátna

Serial monitor: **115200 baud**, řádkování **Newline (Nový řádek)**.

## Průběh hodiny

1. Napiš otázku + A–D vlevo, klikni **🚀 Aplikovat** — otázka se spustí, ale
   v inputech zůstává: kdykoli text uprav a znovu Aplikovat (odpovědi zůstávají).
2. Dětem do 2 s naskočí otázka v Serial monitoru, napíšou A–D + Enter.
3. Jména přilétají do grafu s konfetami. Klik na jméno = smazat odpověď (pošle znovu).
4. **✅ Odhalit správnou** → vítězný sloupec exploduje, ostatní zšednou.
5. **➡️ Další otázka** vyčistí formulář, vyplň novou a Aplikovat (graf se sám resetuje).
6. **Historie** dole vlevo: klik na starou otázku ji načte do formuláře — můžeš ji
   pustit znovu nebo upravit. Otázky na hodinu jsou v `OTAZKY.md`.

Oprava odpovědi: dítě prostě pošle jinou volbu — platí poslední.

## Checklist před hodinou

- [ ] Router zapnutý, PC připojené, znáš SSID + heslo
- [ ] **Firewall**: povolit Python/port 8000 příchozí — nejrychleji (admin PowerShell):
      `netsh advfirewall firewall add rule name="kviz" dir=in action=allow protocol=TCP localport=8000`
- [ ] Server běží, na projektoru vidíš IP
- [ ] Smoke test s jedním ESP: připojí se, dostane otázku, hlas dorazí
- [ ] Smazat starou DB pokud chceš čistý start: smaž soubor `kviz.db`
- [ ] Zvuk na PC zapnutý 🔊 (tlačítkem vpravo nahoře lze ztlumit)

## Testy

```powershell
python -m pytest kviz/test_server.py -v
```
