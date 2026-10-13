"""Tekstūru (sprite) ģenerators — uzzīmē visas spēles bildes assets/ mapē.

Palaišana:  python make_assets.py
Bildes zīmē ar Pillow bibliotēku (tīra Python, bez Photoshop).
Visas krāsas sakrīt ar spēles stilu (skat. client/main.py).

Personāži zīmēti "skatā no augšas" (top-down):
  - aplis = galva/cepure, ovāls ap to = ķermenis/pleci
  - personāži "skatās uz leju" — spēlē tos pagriež vajadzīgajā virzienā
    ar pygame.transform.rotate()
"""

import os
import random

from PIL import Image, ImageDraw

os.makedirs("assets", exist_ok=True)
random.seed(42)  # vienāds "juceklis" katrā palaišanā — bildes vienmēr vienādas

TILE = 48  # flīzes izmērs (tāds pats kā game/settings.py TILE_SIZE)


def save(img: Image.Image, name: str) -> None:
    """Saglabā bildi assets/ mapē un izvada ziņu."""
    img.save(f"assets/{name}.png")
    print(f"assets/{name}.png")


# --- GRĪDA UN SIENAS (flīzes 48x48) ---

def make_floor() -> Image.Image:
    """Tumša grīdas flīze ar smalku troksni un šuvēm."""
    img = Image.new("RGB", (TILE, TILE), (32, 38, 50))
    d = ImageDraw.Draw(img)
    # Troksnis — nejauši tumšāki punkti, lai grīda nav "plakana"
    for _ in range(40):
        x, y = random.randrange(TILE), random.randrange(TILE)
        d.point((x, y), fill=(26, 31, 42))
    # Šuves ap malām (flīžu režģa iespaids)
    d.rectangle([0, 0, TILE - 1, TILE - 1], outline=(24, 29, 39))
    return img


def make_wall() -> Image.Image:
    """Gaiša sienas flīze — metāla panels ar apmaļi."""
    img = Image.new("RGB", (TILE, TILE), (96, 106, 126))
    d = ImageDraw.Draw(img)
    d.rectangle([3, 3, TILE - 4, TILE - 4], fill=(84, 93, 111))   # iekšējais panels
    d.line([3, 3, TILE - 4, 3], fill=(120, 131, 152), width=2)    # gaisma no augšas
    d.line([3, 3, 3, TILE - 4], fill=(120, 131, 152), width=2)
    for _ in range(25):  # neliels nodilums
        x, y = random.randrange(4, TILE - 4), random.randrange(4, TILE - 4)
        d.point((x, y), fill=(74, 82, 98))
    return img


# --- PERSONĀŽI (caurspīdīgs fons, skats no augšas, seja uz leju) ---

def make_person(size: int, body: tuple, head: tuple, accent: tuple | None) -> Image.Image:
    """Uzzīmē top-down personāžu: ēna, ķermenis, galva, pēdas.

    accent — maza detaļa apakšā (kurjerim oranžs plecu siksniņš,
    sargam dzeltena kabatas lukturīša uzlāde).
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = size // 2  # centrs

    # Ēna zem personāža
    d.ellipse([c - 12, size - 8, c + 12, size - 2], fill=(0, 0, 0, 70))
    # Ķermenis (pleci) ar tumšu kontūru
    d.ellipse([c - 13, c - 10, c + 13, c + 14], fill=(15, 18, 26, 255))
    d.ellipse([c - 12, c - 9, c + 12, c + 13], fill=body + (255,))
    # Pēdas apakšā (rāda, kurp personāžs skatās)
    d.ellipse([c - 9, c + 12, c - 2, c + 18], fill=(15, 18, 26, 255))
    d.ellipse([c + 2, c + 12, c + 9, c + 18], fill=(15, 18, 26, 255))
    # Galva (kapuce/cepure) ar kontūru
    d.ellipse([c - 9, c - 11, c + 9, c + 7], fill=(15, 18, 26, 255))
    d.ellipse([c - 8, c - 10, c + 8, c + 6], fill=head + (255,))
    # Akcents
    if accent:
        d.rectangle([c - 4, c + 8, c + 4, c + 12], fill=accent + (255,))
    return img


# --- PRIEKŠMETI ---

def make_coin() -> Image.Image:
    """Zelta monēta ar kroni."""
    s = 20
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([0, 0, s - 1, s - 1], fill=(176, 128, 24, 255))     # tumša maliņa
    d.ellipse([2, 2, s - 3, s - 3], fill=(250, 210, 60, 255))     # zelts
    d.ellipse([4, 4, s - 5, s - 5], outline=(255, 236, 150, 255)) # spīdums
    # Kroņiņš vidū
    d.polygon([(6, 13), (6, 8), (9, 10), (10, 6), (11, 10), (14, 8), (14, 13)],
              fill=(176, 128, 24, 255))
    return img


def make_key() -> Image.Image:
    """Zelta atslēga (gulstiņus)."""
    img = Image.new("RGBA", (28, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([1, 3, 13, 13], fill=(230, 168, 40, 255))   # gredzens
    d.ellipse([4, 6, 10, 12], fill=(0, 0, 0, 0))          # caurums gredzenā
    d.rectangle([12, 6, 26, 10], fill=(230, 168, 40, 255))  # kāts
    d.rectangle([20, 10, 23, 14], fill=(230, 168, 40, 255))  # zobi
    d.rectangle([24, 10, 27, 13], fill=(230, 168, 40, 255))
    return img


def make_door() -> Image.Image:
    """Brūnas metāla durvis ar rokturi."""
    img = Image.new("RGB", (TILE, TILE), (60, 45, 32))      # rāmis
    d = ImageDraw.Draw(img)
    d.rectangle([5, 2, TILE - 6, TILE - 3], fill=(122, 84, 50))   # durvju loksne
    d.rectangle([9, 6, TILE - 10, TILE - 7], outline=(90, 60, 34), width=2)
    d.ellipse([TILE - 16, TILE // 2 - 3, TILE - 10, TILE // 2 + 3],
              fill=(230, 168, 40))  # rokturis
    return img


def make_exit() -> Image.Image:
    """Zaļa izejas durvju flīze ar bultiņu."""
    img = Image.new("RGB", (TILE, TILE), (22, 60, 38))
    d = ImageDraw.Draw(img)
    d.rectangle([5, 2, TILE - 6, TILE - 3], fill=(36, 110, 62))
    d.rectangle([9, 6, TILE - 10, TILE - 7], outline=(60, 210, 110), width=2)
    # Bultiņa uz priekšu (pa labi)
    d.polygon([(16, 24), (26, 16), (26, 21), (34, 21), (34, 27), (26, 27), (26, 32)],
              fill=(140, 255, 180))
    return img


def make_lamp(on: bool) -> Image.Image:
    """Sienas lampa: dzeltena (deg) vai pelēka (izslēgta)."""
    s = 24
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([s // 2 - 3, 0, s // 2 + 3, 6], fill=(40, 44, 54, 255))  # kronšteins
    korpus = (255, 240, 160) if on else (90, 92, 100)
    d.ellipse([4, 5, s - 4, s - 5], fill=(15, 18, 26, 255))
    d.ellipse([5, 6, s - 5, s - 6], fill=korpus + (255,))
    if on:  # spīduma punkts
        d.ellipse([8, 9, 12, 13], fill=(255, 255, 230, 255))
    return img


if __name__ == "__main__":
    save(make_floor(), "floor")
    save(make_wall(), "wall")
    save(make_person(32, (70, 140, 230), (110, 180, 255), (255, 150, 40)), "player")
    save(make_person(36, (150, 45, 45), (200, 70, 70), (255, 230, 120)), "guard")
    save(make_coin(), "coin")
    save(make_key(), "key")
    save(make_door(), "door")
    save(make_exit(), "exit")
    save(make_lamp(True), "lamp_on")
    save(make_lamp(False), "lamp_off")
    print("Visas tekstūras gatavas!")
