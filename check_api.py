"""Servera pašpārbaude: palaiž pēc tam, kad strādā uvicorn.

Lietošana:
    1. terminālī: uvicorn api.main:app --reload
    2. citā terminālī: python check_api.py

Pārbauda visus endpointus un statusa kodus (201, 400, 401, 404, 422).
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

    print("\nVISI SERVERA TESTI IZJAUTI ✅")


if __name__ == "__main__":
    main()
