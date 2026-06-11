"""
Hlasovací server pro hodinu elektrotechniky.

Spuštění:  uvicorn server:app --host 0.0.0.0 --port 8000
Pak otevři http://localhost:8000 a promítej.

ESP děti volají:
  GET  /api/otazka              -> plain text: 1. řádek id, dál otázka + možnosti
  POST /api/odpoved?nick=Pepa   -> body {"volba": "A"}
"""
import os
import socket
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse, FileResponse
from pydantic import BaseModel

DB_PATH = os.environ.get("KVIZ_DB", str(Path(__file__).parent / "kviz.db"))
STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Kvíz server")

VOLBY = ("A", "B", "C", "D")


@contextmanager
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS otazky (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          text TEXT NOT NULL,
          a TEXT NOT NULL, b TEXT NOT NULL, c TEXT NOT NULL, d TEXT NOT NULL,
          spravna TEXT,
          vytvoreno TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS odpovedi (
          otazka_id INTEGER NOT NULL REFERENCES otazky(id),
          nick TEXT NOT NULL,
          volba TEXT NOT NULL CHECK (volba IN ('A','B','C','D')),
          cas TEXT DEFAULT (datetime('now')),
          PRIMARY KEY (otazka_id, nick)
        );
        -- jednořádková tabulka: která otázka právě běží (lze vrátit i starou)
        CREATE TABLE IF NOT EXISTS aktivni (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          otazka_id INTEGER REFERENCES otazky(id)
        );
        """)


init_db()


def aktivni_otazka(con) -> sqlite3.Row | None:
    return con.execute(
        "SELECT o.* FROM otazky o JOIN aktivni a ON o.id = a.otazka_id WHERE a.id = 1"
    ).fetchone()


def nastav_aktivni(con, otazka_id: int):
    con.execute(
        "INSERT INTO aktivni (id, otazka_id) VALUES (1, ?) "
        "ON CONFLICT(id) DO UPDATE SET otazka_id=excluded.otazka_id",
        (otazka_id,),
    )


# ---------------------------------------------------------------- ESP API

@app.get("/api/otazka", response_class=PlainTextResponse)
def get_otazka():
    """Polling z ESP. Plain text, ať se snadno vypisuje do Serial monitoru."""
    with db() as con:
        q = aktivni_otazka(con)
    if q is None:
        return "0\nZatim zadna otazka, cekej..."
    return (
        f"{q['id']}\n"
        f"{q['text']}\n"
        f"  A) {q['a']}\n"
        f"  B) {q['b']}\n"
        f"  C) {q['c']}\n"
        f"  D) {q['d']}\n"
        f"Napis A, B, C nebo D a zmackni Enter:"
    )


class Odpoved(BaseModel):
    volba: str


@app.post("/api/odpoved")
def post_odpoved(body: Odpoved, nick: str = Query(default="")):
    nick = nick.strip()
    if not nick or len(nick) > 20:
        raise HTTPException(400, "Nick musi mit 1-20 znaku.")
    volba = body.volba.strip().upper()
    if volba not in VOLBY:
        raise HTTPException(400, "Volba musi byt A, B, C nebo D.")
    with db() as con:
        q = aktivni_otazka(con)
        if q is None:
            raise HTTPException(409, "Zadna aktivni otazka.")
        con.execute(
            """INSERT INTO odpovedi (otazka_id, nick, volba) VALUES (?, ?, ?)
               ON CONFLICT(otazka_id, nick) DO UPDATE SET volba=excluded.volba, cas=datetime('now')""",
            (q["id"], nick, volba),
        )
    return {"ok": True, "zprava": f"Odpoved {volba} prijata, diky {nick}!"}


# ---------------------------------------------------------------- Admin API

class NovaOtazka(BaseModel):
    text: str
    a: str
    b: str
    c: str
    d: str


@app.post("/api/admin/otazka")
def admin_otazka(q: NovaOtazka):
    if not q.text.strip():
        raise HTTPException(400, "Otazka nesmi byt prazdna.")
    with db() as con:
        cur = con.execute(
            "INSERT INTO otazky (text, a, b, c, d) VALUES (?, ?, ?, ?, ?)",
            (q.text.strip(), q.a.strip(), q.b.strip(), q.c.strip(), q.d.strip()),
        )
        nastav_aktivni(con, cur.lastrowid)
        return {"ok": True, "id": cur.lastrowid}


@app.put("/api/admin/otazka/{otazka_id}")
def admin_uprav_otazku(otazka_id: int, q: NovaOtazka):
    """Úprava otázky za běhu — odpovědi zůstávají navázané (stejné id)."""
    if not q.text.strip():
        raise HTTPException(400, "Otazka nesmi byt prazdna.")
    with db() as con:
        cur = con.execute(
            "UPDATE otazky SET text=?, a=?, b=?, c=?, d=? WHERE id=?",
            (q.text.strip(), q.a.strip(), q.b.strip(), q.c.strip(), q.d.strip(), otazka_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "Otazka neexistuje.")
    return {"ok": True, "id": otazka_id}


class Aktivace(BaseModel):
    id: int


@app.post("/api/admin/aktivovat")
def admin_aktivovat(body: Aktivace):
    """Vrátí starou otázku zpět na plátno — i s odpověďmi, co u ní už jsou."""
    with db() as con:
        if con.execute("SELECT 1 FROM otazky WHERE id=?", (body.id,)).fetchone() is None:
            raise HTTPException(404, "Otazka neexistuje.")
        nastav_aktivni(con, body.id)
    return {"ok": True, "id": body.id}


@app.get("/api/admin/historie")
def admin_historie():
    with db() as con:
        rows = con.execute(
            "SELECT id, text, a, b, c, d, spravna FROM otazky ORDER BY id DESC"
        ).fetchall()
    return [dict(r) for r in rows]


class Odhaleni(BaseModel):
    volba: str


@app.post("/api/admin/odhalit")
def admin_odhalit(body: Odhaleni):
    volba = body.volba.strip().upper()
    if volba not in VOLBY:
        raise HTTPException(400, "Volba musi byt A, B, C nebo D.")
    with db() as con:
        q = aktivni_otazka(con)
        if q is None:
            raise HTTPException(409, "Zadna aktivni otazka.")
        con.execute("UPDATE otazky SET spravna=? WHERE id=?", (volba, q["id"]))
    return {"ok": True}


@app.delete("/api/admin/odpoved")
def admin_smaz_odpoved(nick: str = Query(...)):
    with db() as con:
        q = aktivni_otazka(con)
        if q is None:
            raise HTTPException(409, "Zadna aktivni otazka.")
        con.execute("DELETE FROM odpovedi WHERE otazka_id=? AND nick=?", (q["id"], nick))
    return {"ok": True}


# ---------------------------------------------------------------- UI API

@app.get("/api/vysledky")
def vysledky():
    with db() as con:
        q = aktivni_otazka(con)
        if q is None:
            return {"otazka_id": 0, "text": None, "moznosti": {}, "pocty": {}, "nicky": {}, "spravna": None}
        rows = con.execute(
            "SELECT nick, volba FROM odpovedi WHERE otazka_id=? ORDER BY cas", (q["id"],)
        ).fetchall()
    pocty = {v: 0 for v in VOLBY}
    nicky = {v: [] for v in VOLBY}
    for r in rows:
        pocty[r["volba"]] += 1
        nicky[r["volba"]].append(r["nick"])
    return {
        "otazka_id": q["id"],
        "text": q["text"],
        "moznosti": {"A": q["a"], "B": q["b"], "C": q["c"], "D": q["d"]},
        "pocty": pocty,
        "nicky": nicky,
        "spravna": q["spravna"],
    }


@app.get("/api/info")
def info():
    """IP adresa serveru v lokální síti. Funguje i bez internetu —
    UDP connect nic neposílá, jen vybere odchozí rozhraní; když ani to
    nejde, projdeme adresy počítače a vezmeme první privátní (192.168./10./172.)."""
    ip = "127.0.0.1"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except OSError:
        pass
    if ip == "127.0.0.1":
        try:
            adresy = socket.gethostbyname_ex(socket.gethostname())[2]
            privatni = [a for a in adresy if a.startswith(("192.168.", "10.", "172."))]
            if privatni:
                ip = privatni[0]
        except OSError:
            pass
    return {"ip": ip, "port": 8000}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/hlasuj")
def hlasuj():
    """Mobilní hlasování — náhrada ESP, když děti hlasují telefonem."""
    return FileResponse(STATIC_DIR / "hlasuj.html")
