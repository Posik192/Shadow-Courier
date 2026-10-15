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
