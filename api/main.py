"""Shadow Courier REST API serveris (FastAPI).

Palaišana no projekta mapes:
    uvicorn api.main:app --reload
Pēc tam pārlūkā atver http://localhost:8000/docs — tur visus
endpointus var izmēģināt bez spēles.

Galvenie endpointi:
    POST /register              jauns spēlētājs (201, vai 400 ja vārds aizņemts)
    POST /login                 parole -> tokens (200, vai 401)
    POST /scores                saglabā rekordu (201, prasa token galveni)
    GET  /scores/top            10 labākie rekordi (200)
    GET  /players/{name}/stats  spēlētāja statistika (200, vai 404)

Mājaslapas (Jinja2 veidnes no web/ mapes):
    GET  /                      līderu tabula (top 10, no tās pašas datubāzes)
    GET  /players/{name}        spēlētāja profils (404, ja nav)
    GET  /rules                 spēles noteikumi
    /static/...                 statiskie faili (style.css u.c.)
"""

import hashlib
import secrets

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from api.db import get_connection, get_top_scores, get_player_page

# --- Ierobežojumi ievaddatiem (lielāki skaitļi vai garāki vārdi nedrīkst) ---
MAX_NAME_LEN = 20
MAX_PASSWORD_LEN = 50

app = FastAPI(title="Shadow Courier API")

# Statiskie faili (style.css u.c.) un Jinja veidnes — abas no web/ mapes
app.mount("/static", StaticFiles(directory="web"), name="static")
templates = Jinja2Templates(directory="web")


class UserIn(BaseModel):
    """Dati, ko sūta reģistrācijai un pieteikšanai."""

    name: str = Field(min_length=1, max_length=MAX_NAME_LEN)
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LEN)


class ScoreIn(BaseModel):
    """Dati, ko sūta rekorda saglabāšanai (vārds nāk no tokena)."""

    score: int = Field(ge=0)


def hash_password(password: str) -> str:
    """Pārveido paroli par hash — paroli nekad neglabājam tādu, kāda tā ir."""
    return hashlib.sha256(password.encode()).hexdigest()


def player_by_token(conn, token: str) -> str | None:
    """Atrod spēlētāja vārdu pēc tokena. Ja nav — None."""
    row = conn.execute(
        "SELECT name FROM players WHERE token = ?", (token,)).fetchone()
    return row[0] if row else None


@app.get("/hello")
def hello() -> dict:
    """Vienkārša pārbaude, ka serveris strādā."""
    return {"message": "Sveiki no Shadow Courier servera!"}


@app.post("/register", status_code=201)
def register(user: UserIn) -> dict:
    """Reģistrē jaunu spēlētāju. Ja vārds aizņemts — 400."""
    with get_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM players WHERE name = ?", (user.name,)).fetchone()
        if exists:
            raise HTTPException(400, "Vārds jau aizņemts")
        conn.execute(
            "INSERT INTO players (name, password_hash) VALUES (?, ?)",
            (user.name, hash_password(user.password)))
    return {"name": user.name}


@app.post("/login")
def login(user: UserIn) -> dict:
    """Pārbauda paroli un iedod tokenu (kā aproci festivālā)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT password_hash FROM players WHERE name = ?",
            (user.name,)).fetchone()
        if row is None or row[0] != hash_password(user.password):
            raise HTTPException(401, "Nepareizs vārds vai parole")
        token = secrets.token_hex(16)
        conn.execute(
            "UPDATE players SET token = ? WHERE name = ?", (token, user.name))
    return {"token": token}


@app.post("/scores", status_code=201)
def add_score(item: ScoreIn, token: str = Header()) -> dict:
    """Saglabā rekordu. Strādā tikai ar derīgu tokenu galvenē."""
    with get_connection() as conn:
        name = player_by_token(conn, token)
        if name is None:
            raise HTTPException(401, "Nav pieteicies")
        conn.execute(
            "INSERT INTO scores (player, score) VALUES (?, ?)",
            (name, item.score))
    return {"player": name, "score": item.score}


@app.get("/scores/top")
def top_scores() -> list[dict]:
    """Atgriež 10 labākos rekordus (lielākie pirmie)."""
    return get_top_scores(10)


@app.get("/players/{name}/stats")
def player_stats(name: str) -> dict:
    """Spēlētāja statistika: spēļu skaits un labākais rezultāts (404, ja nav)."""
    with get_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM players WHERE name = ?", (name,)).fetchone()
        if not exists:
            raise HTTPException(404, "Spēlētājs nav atrasts")
        row = conn.execute(
            "SELECT COUNT(*), MAX(score) FROM scores WHERE player = ?",
            (name,)).fetchone()
    return {"name": name, "games": row[0], "best_score": row[1] or 0}


# --- Mājaslapas (Jinja2 veidnes) ---
# Šie maršruti ir PĒC API maršrutiem, lai /players/{name}/stats
# netiktu uztverts kā profila lapa ar vārdu "{name}/stats".

@app.get("/", response_class=HTMLResponse)
def leaderboard_page(request: Request) -> HTMLResponse:
    """Līderu tabula pārlūkā — tie paši dati, ko atdod /scores/top."""
    return templates.TemplateResponse(
        request, "leaderboard.html", {"scores": get_top_scores(10)})


@app.get("/rules", response_class=HTMLResponse)
def rules_page(request: Request) -> HTMLResponse:
    """Spēles noteikumi pārlūkā."""
    return templates.TemplateResponse(request, "rules.html")


@app.get("/players/{name}", response_class=HTMLResponse)
def player_page(request: Request, name: str) -> HTMLResponse:
    """Spēlētāja profils pārlūkā. Ja spēlētāja nav — 404 ar vienkāršu ziņu."""
    player = get_player_page(name)
    if player is None:
        raise HTTPException(404, "Spēlētājs nav atrasts")
    return templates.TemplateResponse(
        request, "player.html", {"player": player})
