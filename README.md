# Shadow Courier

Shadow Courier is a 2D stealth puzzle game made in Python with pygame.

The player is a secret courier who must deliver a package through guarded areas. The player has to avoid guards, stay out of light zones, collect keys, open doors and reach the exit.

## Features
- Player movement
- 3 levels with increasing difficulty
- Guards with patrol routes
- Light zones
- Temporary lamp shutdown ability
- Score system
- Pause and Game Over screens
- Leaderboard with saved scores

## Palaišana

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Spēle:
```bash
python -m client.main
```

Serveris (atver http://localhost:8000/docs):
```bash
uvicorn api.main:app --reload
```

Pārbaudes:
```bash
python check_game.py    # spēles loģikas testi
python check_api.py     # servera testi (serverim jāstrādā)
```

## API endpointi

| Metode | Adrese | Ko dara | Atbilde |
|--------|--------|---------|---------|
| POST | /register | Reģistrē spēlētāju (vārds + parole) | 201 / 400 |
| POST | /login | Pārbauda paroli, atdod tokenu | 200 / 401 |
| POST | /scores | Saglabā rekordu (prasa `token` galveni) | 201 / 401 / 422 |
| GET | /scores/top | 10 labākie rekordi | 200 |
| GET | /players/{name}/stats | Spēļu skaits un labākais rezultāts | 200 / 404 |

## Mājaslapas (Jinja)

| Adrese | Kas tur ir |
|--------|------------|
| / | Līderu tabula (top 10 no datubāzes) |
| /players/{name} | Spēlētāja profils (spēļu skaits, labākais, pēdējie rezultāti) |
| /rules | Spēles noteikumi |
| /static/style.css | Lapu stili |

Spēle beigās (CAUGHT vai uzvara) pati aizsūta rekordu serverim —
vārdu spēle pajautā ar `input()` pirms loga atvēršanas.
Ja serveris ir izslēgts, spēle turpina normāli, tikai rekords netiek saglabāts.

Rekordi un spēlētāji glabājas SQLite failā `game.db` (netiek iekļauts Git).
