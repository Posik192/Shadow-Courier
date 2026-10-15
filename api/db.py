"""Datubāzes savienojums (SQLite).

Datubāze ir viens fails game.db projektā. Pirmajā palaišanas reizē
tiek izveidotas abas tabulas (scores un players), nākamajās reizēs
IF NOT EXISTS neko nemaina.
"""

import sqlite3

DB_PATH = "game.db"


def get_connection() -> sqlite3.Connection:
    """Atver savienojumu ar datubāzi un nodrošina, ka tabulas eksistē."""
    conn = sqlite3.connect(DB_PATH)
    # Rekordu tabula: id datubāze piešķir pati (1, 2, 3, ...)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player TEXT NOT NULL,
            score INTEGER NOT NULL
        )""")
    # Spēlētāju tabula: parole tiek glabāta tikai kā hash
    conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            name TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            token TEXT
        )""")
    return conn


def get_top_scores(limit: int = 10) -> list[dict]:
    """Atgriež labākos rekordus (lielākie pirmie).

    Kopīga palīgfunkcija — to lieto gan API endpoint /scores/top,
    gan Jinja mājaslapa GET /, lai abi rāda vienus un tos pašus datus.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT player, score FROM scores "
            "ORDER BY score DESC LIMIT ?", (limit,)).fetchall()
    return [{"player": p, "score": s} for p, s in rows]


def get_player_page(name: str) -> dict | None:
    """Spēlētāja profila dati Jinja lapai. None, ja spēlētāja nav.

    Atgriež vārdu, spēļu skaitu, labāko rezultātu un 5 pēdējos
    rezultātus (jaunākie pirmie, pēc id — tas aug automātiski).
    """
    with get_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM players WHERE name = ?", (name,)).fetchone()
        if not exists:
            return None
        row = conn.execute(
            "SELECT COUNT(*), MAX(score) FROM scores WHERE player = ?",
            (name,)).fetchone()
        recent = conn.execute(
            "SELECT score FROM scores WHERE player = ? "
            "ORDER BY id DESC LIMIT 5", (name,)).fetchall()
    return {
        "name": name,
        "games": row[0],
        "best_score": row[1] or 0,
        "recent_scores": [r[0] for r in recent],
    }
