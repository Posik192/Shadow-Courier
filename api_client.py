"""Savienojums ar Shadow Courier serveri no spēles puses.

Spēle beigās (CAUGHT vai WIN) aizsūta rekordu serverim, lai tas
parādītos līderu tabulā (http://localhost:8000/).

Svarīgi: visas funkcijas ir ar try/except — spēle NEKAD nedrīkst
nokrist, ja serveris ir izslēgts. Sliktākajā gadījumā rekords
vienkārši netiek saglabāts.
"""

import requests

# --- SERVERA UZSTĀDĪJUMI ---
SERVER = "http://localhost:8000"  # kur strādā uvicorn (api.main:app)
TIMEOUT = 3                       # sekundes — cik ilgi gaidām atbildi

# Fiksēta parole visiem spēles spēlētājiem.
# Kāpēc tā: /scores prasa tokenu (3. dienas uzdevums), bet spēle pati
# noformē spēlētāju — spēlētājs ievada tikai vārdu, paroli viņš nezina.
# Tā nav īsta drošība, tikai veids, kā serveris atšķir spēlētājus.
GAME_PASSWORD = "shadow-courier-spele"


def login_or_register(name: str) -> str | None:
    """Atgriež servera tokenu šim spēlētājam vai None, ja neizdevās.

    Plūsma:
    1. Mēģina POST /login — ja spēlētājs jau eksistē, viss kārtībā.
    2. Ja 401 (spēlētāja nav vai cita parole) — POST /register.
    3. Pēc reģistrācijas vēlreiz POST /login, lai dabūtu tokenu.

    None nākas, ja serveris ir izslēgts vai atbild ar kļūdu.
    """
    try:
        dati = {"name": name, "password": GAME_PASSWORD}
        r = requests.post(f"{SERVER}/login", json=dati, timeout=TIMEOUT)
        if r.status_code == 401:
            # Spēlētāja vēl nav — reģistrējam un piesakāmies no jauna
            requests.post(f"{SERVER}/register", json=dati, timeout=TIMEOUT)
            r = requests.post(f"{SERVER}/login", json=dati, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()["token"]
    except requests.RequestException:
        pass  # serveris izslēgts vai tīkla kļūda — spēle turpina bez servera
    return None


def send_score(token: str, score: int) -> bool:
    """Aizsūta rekordu serverim. True, ja saglabāts (201), False citādi.

    Serveris vārdu paņem no tokena, tāpēc sūtām tikai punktus.
    """
    try:
        r = requests.post(f"{SERVER}/scores", json={"score": score},
                          headers={"token": token}, timeout=TIMEOUT)
        return r.status_code == 201
    except requests.RequestException:
        return False  # serveris izslēgts — rekords vienkārši netiek sūtīts
