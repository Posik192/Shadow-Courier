"""Savienojums ar Shadow Courier serveri no spēles puses.

Spēle beigās (CAUGHT vai WIN) aizsūta rekordu serverim, lai tas
parādītos līderu tabulā (http://localhost:8000/).

Spēlētājs spēles sākumā ievada savu vārdu UN paroli:
- ja konts ar šādu vārdu vēl nav — serveris to izveido (register);
- ja konts ir — serveris pārbauda paroli (login) un iedod tokenu.
Konts paliek datubāzē, tāpēc nākamajā reizē ar to pašu vārdu un
paroli spēlētājs ienāk savā vecmā kontā un statistika krājas tālāk.

Svarīgi: visas funkcijas ir ar try/except — spēle NEKAD nedrīkst
nokrist, ja serveris ir izslēgts. Sliktākajā gadījumā rekords
vienkārši netiek saglabāts.
"""

import os

import requests

# --- SERVERA UZSTĀDĪJUMI ---
# Kur strādā serveris. Pēc noklusējuma lokālais uvicorn (api.main:app).
# Ja serveris ir izlikts internetā (Render), palaižot spēli iestati
# vides mainīgo, piem.: $env:SHADOW_SERVER="https://tavs.onrender.com"
SERVER = os.environ.get("SHADOW_SERVER", "http://localhost:8000")
TIMEOUT = 3                       # sekundes — cik ilgi gaidām atbildi

# Iespējamie atbilžu statusi (lai spēle var atšķirt kļūdu veidus):
# "ok" — viss kārtībā; "wrong_password" — vārds aizņemts / parole nepareiza;
# "taken" — reģistrējot vārds jau eksistē; "no_server" — serveris neatbild.


def try_login(name: str, password: str) -> tuple[str | None, str]:
    """Mēģina ielogoties. Atgriež (tokens, statuss).

    Tokens ir None, ja statuss nav "ok".
    """
    try:
        r = requests.post(f"{SERVER}/login",
                          json={"name": name, "password": password},
                          timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()["token"], "ok"
        if r.status_code == 401:
            return None, "wrong_password"
    except requests.RequestException:
        pass  # serveris izslēgts vai tīkla kļūda — spēle turpina bez servera
    return None, "no_server"


def try_register(name: str, password: str) -> str:
    """Mēģina izveidot jaunu kontu. Atgriež statusu."""
    try:
        r = requests.post(f"{SERVER}/register",
                          json={"name": name, "password": password},
                          timeout=TIMEOUT)
        if r.status_code == 201:
            return "ok"
        if r.status_code == 400:
            return "taken"  # vārds jau aizņemts — droši vien parole nepareiza
    except requests.RequestException:
        pass
    return "no_server"


def login_or_register(name: str, password: str) -> tuple[str | None, str]:
    """Ienāk esošā kontā vai izveido jaunu. Atgriež (tokens, statuss).

    Plūsma:
    1. Mēģina login — ja konts ir un parole pareiza, viss kārtībā.
    2. Ja 401 — konta varētu nebūt: mēģina register.
    3. Ja reģistrācija izdodas — login vēlreiz, lai dabūtu tokenu.
    4. Ja reģistrējot saka "taken" — vārds eksistē, parole bija nepareiza.
    """
    token, status = try_login(name, password)
    if status != "wrong_password":
        return token, status  # "ok" vai "no_server"
    if try_register(name, password) == "ok":
        return try_login(name, password)  # jauns konts — ielogojamies
    return None, "wrong_password"  # vārds aizņemts, parole nesakrīt


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
