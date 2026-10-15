"""Shadow Courier REST API serveris (FastAPI).

Palaišana no projekta mapes:
    uvicorn api.main:app --reload
Pēc tam pārlūkā http://localhost:8000/docs — tur visu var izmēģināt.

Galvenie endpointi:
    POST /register              jauns spēlētājs (201 / 400 ja vārds aizņemts)
    POST /login                 parole -> tokens (200 / 401)
    POST /scores                saglabā rekordu (201, prasa token galveni)
    GET  /scores/top            10 labākie (200)
    GET  /players/{name}/stats  statistika (200 / 404)

Mājaslapas (Jinja2 no web/ mapes):
    GET  /                      līderu tabula
    GET  /players/{name}        spēlētāja profils
    GET  /rules                 spēles noteikumi
"""

import hashlib
import secrets

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from api.db import (get_connection, get_top_scores, get_player_page,
                    get_progress, save_progress)

# --- Ierobežojumi ievaddatiem ---
MAX_NAME_LEN = 20
MAX_PASSWORD_LEN = 50

app = FastAPI(title="Shadow Courier API")

# Statiskie faili un Jinja veidnes — abas no web/ mapes
app.mount("/static", StaticFiles(directory="web"), name="static")
templates = Jinja2Templates(directory="web")


class UserIn(BaseModel):
    """Dati reģistrācijai un pieteikšanai."""

    name: str = Field(min_length=1, max_length=MAX_NAME_LEN)
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_LEN)


class ScoreIn(BaseModel):
    """Dati rekorda saglabāšanai (vārds nāk no tokena)."""

    score: int = Field(ge=0)


def hash_password(password: str) -> str:
    """Paroli glabājam tikai kā hash, nekad pašu paroli."""
    return hashlib.sha256(password.encode()).hexdigest()


def player_by_token(conn, token: str) -> str | None:
    """Spēlētāja vārds pēc tokena. Ja nav — None."""
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
    """10 labākie rekordi (lielākie pirmie)."""
    return get_top_scores(10)


@app.get("/players/{name}/stats")
def player_stats(name: str) -> dict:
    """Spēļu skaits un labākais rezultāts (404, ja nav tāda spēlētāja)."""
    with get_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM players WHERE name = ?", (name,)).fetchone()
        if not exists:
            raise HTTPException(404, "Spēlētājs nav atrasts")
        row = conn.execute(
            "SELECT COUNT(*), MAX(score) FROM scores WHERE player = ?",
            (name,)).fetchone()
    return {"name": name, "games": row[0], "best_score": row[1] or 0}


class ProgressIn(BaseModel):
    """Cik līmeņi pabeigti (1-3)."""

    completed: int = Field(ge=0, le=99)


@app.get("/players/{name}/progress")
def read_progress(name: str, token: str = Header()) -> dict:
    """Spēlētāja progress — tikai pats sev, tāpēc prasa tokenu."""
    with get_connection() as conn:
        owner = player_by_token(conn, token)
    if owner is None or owner != name:
        raise HTTPException(401, "Nav pieteicies")
    return {"name": name, "completed": get_progress(name)}


@app.post("/players/{name}/progress", status_code=201)
def write_progress(name: str, item: ProgressIn, token: str = Header()) -> dict:
    """Saglabā progresu serverī. Tikai pats sev, un tikai uz augšu."""
    with get_connection() as conn:
        owner = player_by_token(conn, token)
    if owner is None or owner != name:
        raise HTTPException(401, "Nav pieteicies")
    save_progress(name, item.completed)
    return {"name": name, "completed": get_progress(name)}


# --- Mājaslapas (Jinja2 veidnes) ---
# Šiem jābūt PĒC API maršrutiem — citādi /players/{name}/stats
# FastAPI uztvertu kā profila lapu ar dīvainu vārdu.

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
    """Spēlētāja profils pārlūkā (404, ja nav)."""
    player = get_player_page(name)
    if player is None:
        raise HTTPException(404, "Spēlētājs nav atrasts")
    return templates.TemplateResponse(
        request, "player.html", {"player": player})
