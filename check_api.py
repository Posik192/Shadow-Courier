"""Servera pašpārbaude — palaiž, kamēr otrā terminālī strādā uvicorn.

    1. terminālis: uvicorn api.main:app --reload
    2. terminālis: python check_api.py
"""

import requests

BASE = "http://localhost:8000"


def parbaudiet(nosaukums: str, nosacijums: bool) -> None:
    """Izdrukā OK vai NAV OK — tāpat kā check_game.py spēlei."""
    print(f"{nosaukums}: {'OK' if nosacijums else 'NAV OK!'}")
    assert nosacijums, nosaukums


def main() -> None:
    """Iziet cauri visiem servera scenārijiem pēc kārtas."""
    r = requests.get(f"{BASE}/hello", timeout=5)
    parbaudiet("/hello atbild", r.status_code == 200)

    # Reģistrācija: jauns vārds -> 201, tas pats otrreiz -> 400
    r = requests.post(f"{BASE}/register",
                      json={"name": "testotajs", "password": "parole123"},
                      timeout=5)
    parbaudiet("register 201 (vai jau eksistē no iepriekš)", r.status_code in (201, 400))
    r = requests.post(f"{BASE}/register",
                      json={"name": "testotajs", "password": "cita"},
                      timeout=5)
    parbaudiet("register aizņemts vārds -> 400", r.status_code == 400)

    # Pieteikšanās: pareiza parole -> tokens, nepareiza -> 401
    r = requests.post(f"{BASE}/login",
                      json={"name": "testotajs", "password": "parole123"},
                      timeout=5)
    parbaudiet("login atdod tokenu", r.status_code == 200 and "token" in r.json())
    token = r.json()["token"]
    r = requests.post(f"{BASE}/login",
                      json={"name": "testotajs", "password": "nepareiza"},
                      timeout=5)
    parbaudiet("login nepareiza parole -> 401", r.status_code == 401)

    # Rekords bez tokena -> 401, ar tokenu -> 201
    r = requests.post(f"{BASE}/scores", json={"score": 120}, timeout=5)
    parbaudiet("scores bez tokena -> 401/422", r.status_code in (401, 422))
    r = requests.post(f"{BASE}/scores", json={"score": 120},
                      headers={"token": token}, timeout=5)
    parbaudiet("scores ar tokenu -> 201", r.status_code == 201)
    parbaudiet("atbilde ar spēlētāja vārdu", r.json()["player"] == "testotajs")

    # Slikti dati: negatīvi punkti -> 422, tukšs JSON -> 422
    r = requests.post(f"{BASE}/scores", json={"score": -5},
                      headers={"token": token}, timeout=5)
    parbaudiet("negatīvi punkti -> 422", r.status_code == 422)
    r = requests.post(f"{BASE}/scores", json={}, headers={"token": token},
                      timeout=5)
    parbaudiet("tukšs JSON -> 422", r.status_code == 422)

    # Top 10: mūsu rekords ir sarakstā
    r = requests.get(f"{BASE}/scores/top", timeout=5)
    parbaudiet("top 10 atbild 200", r.status_code == 200)
    parbaudiet("rekords ir top sarakstā",
               any(s["player"] == "testotajs" and s["score"] == 120
                   for s in r.json()))

    # Statistika: eksistējošs -> 200, neeksistējošs -> 404
    r = requests.get(f"{BASE}/players/testotajs/stats", timeout=5)
    parbaudiet("stats 200 ar spēļu skaitu",
               r.status_code == 200 and r.json()["games"] >= 1)
    r = requests.get(f"{BASE}/players/nebuna/stats", timeout=5)
    parbaudiet("stats nezināms -> 404", r.status_code == 404)

    # --- Mājaslapas (Jinja) ---
    r = requests.get(f"{BASE}/", timeout=5)
    parbaudiet("GET / atbild 200", r.status_code == 200)
    parbaudiet("GET / satur tabulu", "<table" in r.text)
    parbaudiet("GET / satur testa spēlētāju", "testotajs" in r.text)

    r = requests.get(f"{BASE}/players/testotajs", timeout=5)
    parbaudiet("profils 200 un satur vārdu",
               r.status_code == 200 and "testotajs" in r.text)
    r = requests.get(f"{BASE}/players/nebuna", timeout=5)
    parbaudiet("profils nezināms -> 404", r.status_code == 404)

    # Statiskie faili (style.css) no /static/
    r = requests.get(f"{BASE}/static/style.css", timeout=5)
    parbaudiet("/static/style.css atbild 200", r.status_code == 200)

    print("\nVISI SERVERA TESTI IZJAUTI ✅")


if __name__ == "__main__":
    main()
