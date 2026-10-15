"""Datubāzes savienojums (SQLite).

Datubāze ir viens fails game.db. Tabulas izveido pirmajā reizē,
IF NOT EXISTS tāpēc nākamajās reizēs neko nemaina.
"""

import sqlite3

DB_PATH = "game.db"


def get_connection() -> sqlite3.Connection:
    """Atver savienojumu un nodrošina, ka abas tabulas eksistē."""
    conn = sqlite3.connect(DB_PATH)
    # Rekordu tabula: id datubāze piešķir pati
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player TEXT NOT NULL,
            score INTEGER NOT NULL
        )""")
    # Spēlētāju tabula: parole tikai kā hash, completed = cik līmeņi pabeigti
    conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            name TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            token TEXT,
            completed INTEGER DEFAULT 0
        )""")
    # Vecām datubāzēm kolonnas completed var nebūt — pievienojam
    try:
        conn.execute("ALTER TABLE players ADD COLUMN completed INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # kolonna jau ir — viss kārtībā
    return conn


def get_progress(name: str) -> int:
    """Cik līmeņus spēlētājs pabeidzis (0 = neviens). Ja nav spēlētāja — 0."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT completed FROM players WHERE name = ?", (name,)).fetchone()
    return row[0] if row else 0


def save_progress(name: str, completed: int) -> None:
    """Saglabā progresu, bet tikai uz augšu — atpakaļ nekad nenulējam."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE players SET completed = MAX(completed, ?) WHERE name = ?",
            (completed, name))


def get_top_scores(limit: int = 10) -> list[dict]:
    """Labākie rekordi (lielākie pirmie). To lieto gan /scores/top,
    gan mājaslapa GET / — lai abi rāda tos pašus datus."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT player, score FROM scores "
            "ORDER BY score DESC LIMIT ?", (limit,)).fetchall()
    return [{"player": p, "score": s} for p, s in rows]


def get_player_page(name: str) -> dict | None:
    """Profila dati Jinja lapai: spēļu skaits, labākais un 5 pēdējie
    rezultāti (jaunākie pirmie pēc id). None, ja spēlētāja nav."""
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
