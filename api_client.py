"""Savienojums ar serveri no spēles puses (rekordu sūtīšanai).

Spēles beigās aizsūtām rekordu, lai tas parādās līderu tabulā.
Spēlētājs sākumā ievada vārdu un paroli: ja konts nav — izveido,
ja ir — pārbauda paroli. Konts paliek datubāzē, statistika krājas tālāk.

Svarīgi: visas funkcijas ar try/except — spēle NEDRĪKST nokrist,
ja serveris ir izslēgts. Sliktākajā gadījumā rekords vienkārši
netiek saglabāts.
"""

import os

import requests

# --- SERVERA UZSTĀDĪJUMI ---
# Pēc noklusējuma lokālais uvicorn. Ja serveris internetā (Render),
# pirms palaišanas iestatīt: $env:SHADOW_SERVER="https://tavs.onrender.com"
SERVER = os.environ.get("SHADOW_SERVER", "http://localhost:8000")
TIMEOUT = 3                       # sekundes — cik ilgi gaidām atbildi

# Atbilžu statusi: "ok", "wrong_password" (vārds aizņemts / slikta parole),
# "taken" (reģistrējot vārds jau ir), "no_server" (serveris neatbild)


def try_login(name: str, password: str) -> tuple[str | None, str]:
    """Mēģina ielogoties. Atgriež (tokens, statuss); tokens None, ja neizdevās."""
    try:
        r = requests.post(f"{SERVER}/login",
                          json={"name": name, "password": password},
                          timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()["token"], "ok"
        if r.status_code == 401:
            return None, "wrong_password"
    except requests.RequestException:
        pass  # serveris izslēgts — spēle turpina bez tā
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
            return "taken"  # vārds jau aizņemts
    except requests.RequestException:
        pass
    return "no_server"


def login_or_register(name: str, password: str) -> tuple[str | None, str]:
    """Vispirms login; ja 401 (varbūt konta nav) — register un login vēlreiz.
    Ja arī reģistrējot saka "taken" — parole bija nepareiza."""
    token, status = try_login(name, password)
    if status != "wrong_password":
        return token, status  # "ok" vai "no_server"
    if try_register(name, password) == "ok":
        return try_login(name, password)  # jauns konts — ielogojamies
    return None, "wrong_password"  # vārds aizņemts, parole nesakrīt


def send_score(token: str, score: int) -> bool:
    """Aizsūta rekordu serverim. True, ja saglabāts (201). Vārdu serveris
    paņem no tokena, tāpēc sūtām tikai punktus."""
    try:
        r = requests.post(f"{SERVER}/scores", json={"score": score},
                          headers={"token": token}, timeout=TIMEOUT)
        return r.status_code == 201
    except requests.RequestException:
        return False  # serveris izslēgts — rekords netiek sūtīts


def get_progress(name: str, token: str) -> int | None:
    """Cik līmeņus pabeidzis (no servera). None, ja serveris nepieejams."""
    try:
        r = requests.get(f"{SERVER}/players/{name}/progress",
                         headers={"token": token}, timeout=TIMEOUT)
        if r.status_code == 200:
            return r.json()["completed"]
    except requests.RequestException:
        pass
    return None


def save_progress(name: str, token: str, completed: int) -> bool:
    """Aizsūta progresu serverim. True, ja saglabāts."""
    try:
        r = requests.post(f"{SERVER}/players/{name}/progress",
                          json={"completed": completed},
                          headers={"token": token}, timeout=TIMEOUT)
        return r.status_code == 201
    except requests.RequestException:
        return False
