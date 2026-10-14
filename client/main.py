"""Shadow Courier — pygame klients.

Šis fails TIKAI nolasa taustiņus un zīmē ekrānu.
Visa spēles loģika (noteikumi) ir mapē game/ — skaties game/game_state.py.

Palaišana:  python -m client.main
Vadība:     WASD/bultiņas — kustēties, Space — izslēgt lampu,
            E — paņemt atslēgu/atvērt durvis, P — pauze, Esc — atpakaļ.
"""

import math
import os
import sys

import pygame

from game import settings as gs
from game.game_state import (GameState, STATUS_PLAYING, STATUS_GAME_OVER,
                             STATUS_WON, STATUS_LEVEL_COMPLETE)
from game.level import LEVEL_MAPS

# --- LOGA UZSTĀDĪJUMI ---
FPS = 60           # kadri sekundē
HUD_HEIGHT = 64    # apakšējā informācijas josla (pikseļi)
TOP_BAR_HEIGHT = 30  # augšējā plānā josla (zīmējas PĀRKLĀJ pasaulei)

# --- TĒLU IZMĒRI UN HITBOXI (līgums ar game/ moduli) ---
# game/settings.py definē šīs konstantes. getattr noklusējumi ļauj
# klientam strādāt arī tad, ja game/ versija tās vēl nepiedāvā.
PLAYER_HIT_W = getattr(gs, "PLAYER_HIT_W", 24)
PLAYER_HIT_H = getattr(gs, "PLAYER_HIT_H", 14)
GUARD_HIT_W = getattr(gs, "GUARD_HIT_W", 36)
GUARD_HIT_H = getattr(gs, "GUARD_HIT_H", 36)
PLAYER_SPRITE = getattr(gs, "PLAYER_SPRITE", 64)  # spēlētāja tēls 2x lielāks
GUARD_SPRITE = getattr(gs, "GUARD_SPRITE", 72)    # sarga tēls 2x lielāks
START_LIVES = getattr(gs, "START_LIVES", 3)


def sprite_pos(hit_x: float, hit_y: float, hit_w: int, hit_h: int,
               sprite_size: int) -> tuple[float, float]:
    """Sprite augšējais kreisais stūris tā, lai tēls "stāvētu" uz hitboxa:
    kājas uz hitboxa apakšas, horizontāli centrēts."""
    return (hit_x + hit_w / 2 - sprite_size / 2, hit_y + hit_h - sprite_size)


# --- PASAULES KRĀSAS (R, G, B) ---
COLOR_FLOOR = (34, 40, 52)      # grīda — tumši pelēka
COLOR_WALL = (90, 100, 120)     # sienas
COLOR_PLAYER = (80, 160, 255)   # kurjers (rezerves kvadrāts, ja nav bildes)
COLOR_GUARD = (230, 70, 70)     # sargs (rezerves kvadrāts)
COLOR_COIN = (250, 210, 60)     # monēta
COLOR_KEY = (255, 150, 40)      # atslēga
COLOR_DOOR = (140, 90, 50)      # durvis
COLOR_EXIT = (60, 210, 110)     # izeja
COLOR_LAMP_ON = (255, 240, 160) # lampa, kas deg
COLOR_LAMP_OFF = (80, 80, 90)   # izslēgta lampa
COLOR_BAD = (214, 84, 72)       # sarkans — brīdinājumi un CAUGHT

# --- INDUSTRIĀLAIS PIKSEĻU UI STILS ---
UI_BG = (20, 23, 28)        # ogļu pelēks fons (#14171c)
UI_PANEL = (27, 31, 38)     # paneļa fons (nedaudz gaišāks par fonu)
UI_LINE = (58, 63, 72)      # plānas līnijas / kontūras
UI_TEXT = (232, 227, 211)   # krēmkrāsas gaišs teksts (#e8e3d3)
UI_DIM = (126, 128, 134)    # pelēks palīgteksts
UI_LOCKED = (88, 90, 96)    # bloķēts elements
UI_ACCENT = (232, 185, 60)  # VIENS dzeltens akcents (#e8b93c)

# --- APGAISMOJUMA UZSTĀDĪJUMI ---
DARKNESS_ALPHA = 110        # cik tumša ir noliktava ārpus gaismas (0–255)
GLOW_COLOR = (255, 200, 90) # lampu un lukturu siltā dzeltenā krāsa
GLOW_GAIN = 0.35            # lampu mirdzuma spilgtums (aditīvs)
GUARD_LIGHT_RADIUS = 150    # cik tālu sniedzas sarga lukturis (pikseļi)
GUARD_CONE_ANGLE = 32       # luktura konusa puse leņķī (grādi)
CONE_GLOW_GAIN = 0.30       # luktura mirdzuma spilgtums
VIGNETTE_ALPHA = 90         # cik tumšas ir ekrāna malas (0–255)
# Kurjera silto dzintaru gaismas aplis (~1.5 flīzes rādiuss):
PLAYER_LIGHT_RADIUS = 72
PLAYER_LIGHT_CUT = 0.8          # cik spēcīgi aplis izgriež tumsu (0..1)
PLAYER_GLOW_COLOR = (255, 176, 84)  # silts dzintars
PLAYER_GLOW_GAIN = 0.5          # kurjera mirdzuma spilgtums

# Ekrānu nosaukumi (kā "lapas" programmā)
SCREEN_MENU = "menu"
SCREEN_LEVEL_SELECT = "level_select"
SCREEN_SETTINGS = "settings"
SCREEN_GAME = "game"
SCREEN_PAUSED = "paused"
SCREEN_GAME_OVER = "game_over"
SCREEN_WON = "won"
SCREEN_LEVEL_COMPLETE = "level_complete"

# Izvēļņu opcijas (navigācija: bultiņas/WASD + Enter, kursors = trijstūris)
LEVEL_NAMES = ["STORAGE", "SECURITY", "LOADING BAY"]
PAUSE_OPTIONS = ["RESUME", "RESTART LEVEL", "SETTINGS", "MAIN MENU"]
SETTINGS_ROWS = ["MASTER VOLUME", "MUSIC", "SOUND EFFECTS",
                 "FULLSCREEN", "CONTROLS"]
CAUGHT_OPTIONS = ["TRY AGAIN", "MAIN MENU"]
WON_OPTIONS = ["PLAY AGAIN", "MAIN MENU"]
CONTROLS_HELP = "WASD MOVE   |   SPACE DISABLE LAMP   |   E INTERACT"

# Cik lielus sprites zīmēt spēlē (pikseļi)
SPRITE_SIZES = {
    "floor": gs.TILE_SIZE, "wall": gs.TILE_SIZE,
    "door": gs.TILE_SIZE, "exit": gs.TILE_SIZE,
    "lamp_on": gs.TILE_SIZE, "lamp_off": gs.TILE_SIZE,
    "player": PLAYER_SPRITE, "guard": GUARD_SPRITE,
    "coin": 26, "key": 30,
    # Dekoratīvie šķēršļi (kastes un mucas kartēs apzīmētas ar 'x')
    "prop_crate_big": gs.TILE_SIZE, "prop_crate_mid": gs.TILE_SIZE,
    "prop_crate_small": gs.TILE_SIZE, "prop_barrel": gs.TILE_SIZE,
}

# Kastes/mucas, no kurām izvēlas dekoratīvos šķēršļus kartēs ('x')
PROP_SPRITES = ["prop_crate_big", "prop_crate_mid",
                "prop_crate_small", "prop_barrel"]

# HUD ikonu izmērs (sirdis, monēta apakšējā joslā)
HUD_ICON_SIZE = 24

# --- KUSTĪBAS ANIMĀCIJAS ---
FRAME_SWITCH_MS = 120  # ik pēc tik milisekundēm mainās soļa kadrs
SWAY_DEGREES = 4       # par cik grādiem tēls "šūpojas", ejot


def load_sprites() -> dict:
    """Ielādē tekstūras no assets/ mapes un samazina līdz spēles izmēram.

    Ja kādas bildes nav (piem., aizmirsa palaist cut_assets.py),
    spēle nestrādā ar kļūdu — tā vietā zīmē parastos kvadrātus.

    Papildus ielādē kustības kadru sarakstus:
    sprites["player_frames"] un sprites["guard_frames"] satur
    player_1..4.png / guard_1..4.png. Ja kadru bilžu nav,
    sarakstā ir viena bilde (parastais sprites) — animācija vienkārši nerit.
    """
    sprites = {}
    for name, size in SPRITE_SIZES.items():
        path = os.path.join("assets", name + ".png")
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            sprites[name] = pygame.transform.smoothscale(img, (size, size))
        else:
            sprites[name] = None

    # Soļu kadri spēlētājam un sargiem (viena bilde = bez animācijas)
    for name in ("player", "guard"):
        frames = []
        size = SPRITE_SIZES[name]
        for i in range(1, 5):
            path = os.path.join("assets", f"{name}_{i}.png")
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                frames.append(pygame.transform.smoothscale(img, (size, size)))
        if not frames:
            frames = [sprites[name]]  # rezerves variants: viens kadrs
        sprites[name + "_frames"] = frames

    # Virzienu sprites: player_down/up/left/right.png (un guard_*).
    # Ja left/right nav, ņemam pretējā virziena spoguļattēlu;
    # ja vispār nav nevienas virzienu bildes, vārdnīcā ir None
    # un draw_world lieto veco variantu (kadri + rotācija).
    for name in ("player", "guard"):
        size = SPRITE_SIZES[name]
        directions = {}
        for direction in ("down", "up", "left", "right"):
            path = os.path.join("assets", f"{name}_{direction}.png")
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                directions[direction] = pygame.transform.smoothscale(
                    img, (size, size))
            else:
                directions[direction] = None
        # Spoguļattēls, ja trūkst tieši viena no sānu bildēm
        if directions["left"] is None and directions["right"] is not None:
            directions["left"] = pygame.transform.flip(
                directions["right"], True, False)
        if directions["right"] is None and directions["left"] is not None:
            directions["right"] = pygame.transform.flip(
                directions["left"], True, False)
        # Ja ir kaut viena virzienu bilde — aizpildām pārējos trūkumus
        existing = [directions[d] for d in ("down", "up", "left", "right")
                    if directions[d] is not None]
        if existing:
            for direction in directions:
                if directions[direction] is None:
                    directions[direction] = existing[0]
            sprites[name + "_dir"] = directions
        else:
            sprites[name + "_dir"] = None

    # Dedzinošā lampa: ja ir lamp_on.png, lieto to visām lampām;
    # citādi — vecie varianti lamp_1..4.png pa vietām
    if sprites["lamp_on"] is not None:
        sprites["lamp_frames"] = [sprites["lamp_on"]]
    else:
        lamp_frames = []
        for i in range(1, 5):
            path = os.path.join("assets", f"lamp_{i}.png")
            if os.path.exists(path):
                img = pygame.image.load(path).convert_alpha()
                lamp_frames.append(pygame.transform.smoothscale(
                    img, (gs.TILE_SIZE, gs.TILE_SIZE)))
        if not lamp_frames:
            lamp_frames = [sprites["lamp_on"]]
        sprites["lamp_frames"] = lamp_frames

    # HUD ikonas (sirds, monēta, atslēga) — katrā divas versijas:
    # parastā un tumšā ("tukšā", piem., zaudēta dzīvība vai nav atslēgas)
    for name, filename in (("ui_heart", "ui_heart.png"),
                           ("ui_coin", "ui_coin.png"),
                           ("ui_key", "key.png")):
        path = os.path.join("assets", filename)
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            icon = pygame.transform.smoothscale(
                img, (HUD_ICON_SIZE, HUD_ICON_SIZE))
            sprites[name] = icon
            # Tumšā versija: krāsas reizina ar pelēku — ikona "nodziest"
            dark = icon.copy()
            dark.fill((70, 70, 80, 255), special_flags=pygame.BLEND_RGBA_MULT)
            sprites[name + "_dark"] = dark
        else:
            sprites[name] = None
            sprites[name + "_dark"] = None
    return sprites


def draw_sprite(window: pygame.Surface, sprite: pygame.Surface | None,
                x: float, y: float, size: int,
                fallback_color: tuple, angle: float = 0.0) -> None:
    """Uzzīmē bildi ar augšējo kreiso stūri vietā (x, y).

    Ja bildes nav — zīmē kvadrātu. angle — par cik grādiem pagriezt.
    """
    if sprite is None:
        pygame.draw.rect(window, fallback_color, (x, y, size, size))
        return
    if angle != 0.0:
        sprite = pygame.transform.rotate(sprite, angle)
    # Rotācija maina bildes izmēru, tāpēc centrējam ap vēlamo punktu
    rect = sprite.get_rect(center=(x + size / 2, y + size / 2))
    window.blit(sprite, rect)


# ============================================================
#  APGAISMOJUMS — kā tas strādā (3 teikumi):
#  1. Reiz programmas darbības laikā uzzīmējam "gaismas sprites" —
#     mīkstus gradientus (aplis lampai un kurjeram, konuss lukturim).
#  2. Katrā kadrā pār pasaules uzklājam puscaurspīdīgu melnu "tumsas"
#     slāni un ar BLEND_RGBA_SUB no tā "izgriežam" gaišas peles tur,
#     kur deg lampas, spīd lukturi un kur iet kurjers.
#  3. Beigās pievienojam siltu mirdzumu (BLEND_RGB_ADD) un vinjetti
#     (tumšākas ekrāna malas) — karte ir lasāma, bet nakts sajūta paliek.
# ============================================================

# Kešatmiņa gatavajiem gradientiem: gradientu rēķina VIENREIZ (tas ir
# "dārgi" — daudz pikseļu), katrā kadrā tikai zīmē (blit) un griež (rotate).
_light_cache: dict = {}


def _build_radial_pixels(radius: int, alpha_func) -> pygame.Surface:
    """Uzzīmē kvadrātveida Surface (2*radius), kura pikseļu alpha
    nosaka funkcija alpha_func(distance, angle) -> 0..255.

    distance — attālums no centra (0..radius), angle — leņķis radianos
    (0 = pa labi). Centrā parasti alpha liela, uz malām 0 — mīksta pāreja.
    """
    size = radius * 2
    pixels = bytearray(size * size * 4)
    i = 0
    for y in range(size):
        for x in range(size):
            dx = x - radius
            dy = y - radius
            distance = math.hypot(dx, dy)
            angle = math.atan2(dy, dx)
            pixels[i + 3] = max(0, min(255, int(alpha_func(distance, angle))))
            i += 4
    return pygame.image.frombuffer(bytes(pixels), (size, size), "RGBA")


def _build_glow_pixels(radius: int, color: tuple, gain: float,
                       value_func) -> pygame.Surface:
    """Krāsains gradients aditīvam mirdzumam (BLEND_RGB_ADD).

    Pikseļa RGB = krāsa * value_func(distance, angle)/255 * gain.
    Zīmējot ar ADD, pikseļi paliek gaišāki un siltāki ap gaismas avotu.
    """
    size = radius * 2
    pixels = bytearray(size * size * 4)
    i = 0
    for y in range(size):
        for x in range(size):
            dx = x - radius
            dy = y - radius
            value = max(0.0, min(255.0, value_func(math.hypot(dx, dy),
                                                   math.atan2(dy, dx))))
            k = value / 255.0 * gain
            pixels[i] = int(color[0] * k)
            pixels[i + 1] = int(color[1] * k)
            pixels[i + 2] = int(color[2] * k)
            pixels[i + 3] = 255
            i += 4
    return pygame.image.frombuffer(bytes(pixels), (size, size), "RGBA")


def _circle_fade(distance: float, radius: int) -> float:
    """Aplja spilgtums: centrā 255, uz malām 0 (kvadrātiska pāreja)."""
    if distance >= radius:
        return 0.0
    t = 1.0 - distance / radius
    return 255 * t * t


def get_light_circle(radius: int, strength: float = 1.0) -> pygame.Surface:
    """Gaismas pele tumsas izgriešanai (BLEND_RGBA_SUB).

    Kur sprite alpha ir liela, tur tumsa "izgriežas" (paliek gaiši).
    strength < 1 atstaj daļu tumsas — gaišs, bet ne pilnīgi spilgts laukums.
    """
    key = ("circle", radius, strength)
    if key not in _light_cache:
        _light_cache[key] = _build_radial_pixels(
            radius, lambda d, a: _circle_fade(d, radius) * strength)
    return _light_cache[key]


def get_glow_circle(radius: int, color: tuple = GLOW_COLOR,
                    gain: float = GLOW_GAIN) -> pygame.Surface:
    """Silta krāsaina mirdzuma pele (BLEND_RGB_ADD) ap gaismas avotu."""
    key = ("glow", radius, color, gain)
    if key not in _light_cache:
        _light_cache[key] = _build_glow_pixels(
            radius, color, gain, lambda d, a: _circle_fade(d, radius))
    return _light_cache[key]


def _cone_value(distance: float, angle: float, radius: int) -> float:
    """Luktura konusa spilgtums punktā (konuss zīmēts rādot pa labi)."""
    half = math.radians(GUARD_CONE_ANGLE)
    if distance >= radius or abs(angle) > half:
        return 0.0
    along = 1.0 - distance / radius      # mazāk gaismas tālāk
    side = 1.0 - abs(angle) / half       # mazāk gaismas pie malām
    return 255 * along * along * (0.35 + 0.65 * side)


def get_light_cone(radius: int) -> pygame.Surface:
    """Sarga luktura konuss (alpha versija tumsas izgriešanai)."""
    key = ("cone", radius)
    if key not in _light_cache:
        _light_cache[key] = _build_radial_pixels(
            radius, lambda d, a: _cone_value(d, a, radius))
    return _light_cache[key]


def get_rotated_cone(direction: tuple[float, float], colored: bool) -> pygame.Surface:
    """Atgriež luktura konusu, pagrieztu konkrētā virzienā (kešots).

    direction — (dx, dy), piem., (1, 0) = pa labi, (0, 1) = uz leju.
    Peldošie virzieni tiek noapaļoti līdz 5 grādiem, lai kešā neuzkrātos
    simtiem gandrīz vienādu konusu.
    colored=False — melna/alpha versija tumsas izgriešanai (SUB),
    colored=True  — silti dzeltena versija mirdzumam (ADD).
    """
    dx, dy = direction
    # Konuss zīmēts pa labi; pygame.rotate griež pretēji pulkstenim
    # matemātiskajā nozīmē, tāpēc ekrānā (y uz leju) formula ir šāda:
    angle = -math.degrees(math.atan2(dy, dx))
    rounded = 5 * round(angle / 5)
    key = ("cone_rot", rounded, colored)
    if key not in _light_cache:
        if colored:
            cone = _build_glow_pixels(
                GUARD_LIGHT_RADIUS, GLOW_COLOR, CONE_GLOW_GAIN,
                lambda d, a: _cone_value(d, a, GUARD_LIGHT_RADIUS))
        else:
            cone = get_light_cone(GUARD_LIGHT_RADIUS)
        _light_cache[key] = pygame.transform.rotate(cone, rounded)
    return _light_cache[key]


def get_vignette(width: int, height: int) -> pygame.Surface:
    """Vinjette — tumšs gradients pa ekrāna malām (centrā caurspīdīgs)."""
    key = ("vignette", width, height)
    if key not in _light_cache:
        pixels = bytearray(width * height * 4)
        cx, cy = width / 2, height / 2
        # Attālums līdz stūrim — tur vinjette ir vis tumšākā
        max_dist = math.hypot(cx, cy)
        i = 0
        for y in range(height):
            for x in range(width):
                d = math.hypot(x - cx, y - cy) / max_dist  # 0 centrā, 1 stūrī
                if d > 0.55:
                    pixels[i + 3] = int(VIGNETTE_ALPHA * (d - 0.55) / 0.45)
                i += 4
        _light_cache[key] = pygame.image.frombuffer(
            bytes(pixels), (width, height), "RGBA")
    return _light_cache[key]


def draw_lighting(window: pygame.Surface, state: GameState) -> None:
    """Uzzīmē tumsu, lampu peles, sargu lukturus, kurjera apli un vinjetti.

    Izsauc PĒC tam, kad visa pasaule (grīda, sprites) jau uzzīmēta.
    """
    t = gs.TILE_SIZE
    world_w = state.level.width * t
    world_h = state.level.height * t

    # 1. solis: tumsas slānis pār visu pasauli
    darkness = pygame.Surface((world_w, world_h), pygame.SRCALPHA)
    darkness.fill((0, 0, 0, DARKNESS_ALPHA))

    # 2. solis: katrai DEGLOŠAI lampai "izgriež" gaišu peli tumsā.
    # BLEND_RGBA_SUB atņem sprite alpha no tumsas alpha — tur paliek caurspīdīgi.
    circle = get_light_circle(gs.LIGHT_RADIUS)
    for (col, row), off_timer in state.level.lamps.items():
        if off_timer <= 0:
            center = (col * t + t // 2, row * t + t // 2)
            darkness.blit(circle, circle.get_rect(center=center),
                          special_flags=pygame.BLEND_RGBA_SUB)

    # 3. solis: sargu lukturu konusi (centri = hitboxa centrs)
    for guard in state.level.guards:
        cone = get_rotated_cone(guard.facing, colored=False)
        center = (guard.x + GUARD_HIT_W / 2, guard.y + GUARD_HIT_H / 2)
        darkness.blit(cone, cone.get_rect(center=center),
                      special_flags=pygame.BLEND_RGBA_SUB)

    # 4. solis: kurjera silto dzintaru gaismas aplis (seko hitboxa centram)
    player_center = (state.player_x + PLAYER_HIT_W / 2,
                     state.player_y + PLAYER_HIT_H / 2)
    player_circle = get_light_circle(PLAYER_LIGHT_RADIUS, PLAYER_LIGHT_CUT)
    darkness.blit(player_circle, player_circle.get_rect(center=player_center),
                  special_flags=pygame.BLEND_RGBA_SUB)

    # 5. solis: uzklāj tumsu ar izgrieztajām gaismas vietām
    window.blit(darkness, (0, 0))

    # 6. solis: silti mirdzumi gaismas vietās (aditīvi — gaišāk un siltāk)
    glow = get_glow_circle(gs.LIGHT_RADIUS)
    for (col, row), off_timer in state.level.lamps.items():
        if off_timer <= 0:
            center = (col * t + t // 2, row * t + t // 2)
            window.blit(glow, glow.get_rect(center=center),
                        special_flags=pygame.BLEND_RGB_ADD)
    for guard in state.level.guards:
        cone_glow = get_rotated_cone(guard.facing, colored=True)
        center = (guard.x + GUARD_HIT_W / 2, guard.y + GUARD_HIT_H / 2)
        window.blit(cone_glow, cone_glow.get_rect(center=center),
                    special_flags=pygame.BLEND_RGB_ADD)
    # Kurjera dzintara mirdzums (viegls, statisks gradients)
    player_glow = get_glow_circle(PLAYER_LIGHT_RADIUS, PLAYER_GLOW_COLOR,
                                  PLAYER_GLOW_GAIN)
    window.blit(player_glow, player_glow.get_rect(center=player_center),
                special_flags=pygame.BLEND_RGB_ADD)

    # 7. solis: vinjette — ekrāna malas nedaudz tumšākas
    window.blit(get_vignette(world_w, world_h), (0, 0))


# ============================================================
#  PASAULES ZĪMĒŠANA
# ============================================================

# Virziens (x, y) -> rotācijas leņķis bildēm (sprites zīmēti "skatās uz leju")
FACING_ANGLES = {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}

# Virziens (x, y) -> virzienu sprites vārdnīcas atslēga
FACING_NAMES = {(0, 1): "down", (0, -1): "up", (1, 0): "right", (-1, 0): "left"}


def _facing_cardinal(facing: tuple[float, float]) -> tuple[int, int]:
    """No sarga peldošā skata virziena atgriež tuvāko no 4 virzieniem (sprites)."""
    fx, fy = facing
    if abs(fx) >= abs(fy):
        return (1, 0) if fx >= 0 else (-1, 0)
    return (0, 1) if fy >= 0 else (0, -1)


def _draw_alert_icon(window: pygame.Surface, sx: float, sy: float,
                     sprite_size: int) -> None:
    """Uzzīmē sarkanu "!" virs sarga (divi pikseļu taisnstūri: svītra + punkts)."""
    center_x = sx + sprite_size / 2
    top = sy - 24
    pygame.draw.rect(window, COLOR_BAD, (center_x - 3, top, 6, 14))
    pygame.draw.rect(window, COLOR_BAD, (center_x - 3, top + 17, 6, 5))


def _pick_character_sprite(sprites: dict, name: str, facing: tuple[int, int],
                           now: int, frame_offset: int, moving: bool) -> tuple:
    """Izvēlas bildi spēlētājam/sargam un rotācijas leņķi.

    Ja ir virzienu sprites (name_dir vārdnīca) — ņem pareizo bildi,
    rotācijas nav, paliek tikai soļu šūpošanās (to pieskaita izsaucējs).
    Ja virzienu bilžu nav — vecais variants: soļu kadri + rotācija.
    Atgriež (bilde, rotācijas_leņķis).
    """
    dir_sprites = sprites.get(name + "_dir")
    if dir_sprites is not None:
        # Diagonālei (piem., (1, -1)) nav savas bildes — rādam "down"
        return dir_sprites[FACING_NAMES.get(facing, "down")], 0.0
    frames = sprites[name + "_frames"]
    if moving:
        frame = (now // FRAME_SWITCH_MS + frame_offset) % len(frames)
    else:
        frame = 0
    return frames[frame], FACING_ANGLES.get(facing, 0)


def draw_world(window: pygame.Surface, state: GameState,
               sprites: dict, player_facing: tuple[int, int],
               player_moving: bool = False) -> None:
    """Uzzīmē visu līmeni: grīdu, sienas, lampas, monētas, spēlētāju, sargus.

    player_moving — vai spēlētājs šobrīd kustas (ja True, rit soļu
    animācija un viegla šūpošanās; stāvot rāda 1. kadru).
    """
    level = state.level
    t = gs.TILE_SIZE
    # Pašreizējais laiks milisekundēs — no tā rēķina animācijas kadru
    now = pygame.time.get_ticks()

    # Grīda (visi lauciņi, kas nav sienas) un sienas
    for row in range(level.height):
        for col in range(level.width):
            if (col, row) in level.walls:
                draw_sprite(window, sprites["wall"], col * t, row * t, t, COLOR_WALL)
            else:
                draw_sprite(window, sprites["floor"], col * t, row * t, t, COLOR_FLOOR)

    # Izeja, monētas, atslēga, durvis
    ex, ey = level.exit_pos
    draw_sprite(window, sprites["exit"], ex * t, ey * t, t, COLOR_EXIT)
    for col, row in level.coins:
        draw_sprite(window, sprites["coin"],
                    col * t + 11, row * t + 11, 26, COLOR_COIN)
    if level.key_pos is not None:
        kx, ky = level.key_pos
        draw_sprite(window, sprites["key"], kx * t + 9, ky * t + 9, 30, COLOR_KEY)
    if level.door_pos is not None and not level.door_open:
        dx, dy = level.door_pos
        draw_sprite(window, sprites["door"], dx * t, dy * t, t, COLOR_DOOR)

    # Lampas (deg = gaiša, izslēgta = tumša)
    lamp_frames = sprites["lamp_frames"]
    for lamp_index, ((col, row), off_timer) in enumerate(level.lamps.items()):
        if off_timer <= 0:
            lamp = lamp_frames[lamp_index % len(lamp_frames)]
            color = COLOR_LAMP_ON
        else:
            lamp = sprites["lamp_off"]
            color = COLOR_LAMP_OFF
        draw_sprite(window, lamp, col * t, row * t, t, color)

    # Dekoratīvie šķēršļi (kastes/mucas) — kartē apzīmēti ar 'x'
    # Kuras kastes kur — izvēlamies pēc lauciņa koordinātām, lai vienmēr vienādi
    for col, row in level.props:
        prop_name = PROP_SPRITES[(col * 7 + row * 13) % len(PROP_SPRITES)]
        draw_sprite(window, sprites[prop_name], col * t, row * t, t, COLOR_WALL)

    # Sargi (pagriežas skata virzienā; brīdinājuma laikā stāv uz vietas).
    # guard.x/.y ir sarga HITBOXA augšējais kreisais stūris; tēlu
    # zīmē ar "kājām uz hitboxa" (skat. sprite_pos).
    for guard in level.guards:
        guard_dir = _facing_cardinal(guard.facing)
        # Nobīde no sarga pozīcijas, lai visi sargi neietu sinhroni
        offset = (int(guard.x) + int(guard.y)) // 10
        sprite, angle = _pick_character_sprite(
            sprites, "guard", guard_dir, now, offset, moving=guard.moving)
        sway = SWAY_DEGREES * math.sin(now * 0.02 + offset) if guard.moving else 0.0
        sx, sy = sprite_pos(guard.x, guard.y, GUARD_HIT_W, GUARD_HIT_H,
                            GUARD_SPRITE)
        draw_sprite(window, sprite, sx, sy, GUARD_SPRITE,
                    COLOR_GUARD, angle + sway)

    # Spēlētājs (kurjers). state.player_x/.y ir hitboxa augšējais kreisais
    # stūris; tēls stāv uz hitboxa apakšas, centrēts horizontāli.
    if player_moving:
        # Soļu šūpošanās: sprite viegli griežas pa labi/kreisi (sinusa vilnis)
        sway = SWAY_DEGREES * math.sin(now * 0.02)
    else:
        sway = 0.0
    sprite, angle = _pick_character_sprite(
        sprites, "player", player_facing, now, 0, player_moving)
    sx, sy = sprite_pos(state.player_x, state.player_y,
                        PLAYER_HIT_W, PLAYER_HIT_H, PLAYER_SPRITE)
    draw_sprite(window, sprite, sx, sy, PLAYER_SPRITE,
                COLOR_PLAYER, angle + sway)

    # Tumsa + gaismas PĒC visa cita — tā "nosedz" pasauli,
    # izņemot vietas, kur deg lampas, spīd lukturi un iet kurjers
    draw_lighting(window, state)

    # Sarkanais "!" virs sarga zīmējam PĒC tumsas slāņa, lai ikona
    # paliktu spilgta arī tumsā (tā ir UI zīme, ne pasaules daļa)
    for guard in level.guards:
        if guard.alert_icon_timer > 0:
            sx, sy = sprite_pos(guard.x, guard.y, GUARD_HIT_W, GUARD_HIT_H,
                                GUARD_SPRITE)
            _draw_alert_icon(window, sx, sy, GUARD_SPRITE)


# ============================================================
#  HUD — augšējā plānā josla un apakšējā informācijas josla
# ============================================================


def _draw_hud_icon(window: pygame.Surface, sprite: pygame.Surface | None,
                   x: int, y: int, fallback_color: tuple) -> None:
    """Uzzīmē vienu HUD ikonu; ja bildes nav — zīmē mazu kvadrātu."""
    if sprite is None:
        pygame.draw.rect(window, fallback_color,
                         (x, y, HUD_ICON_SIZE, HUD_ICON_SIZE))
    else:
        window.blit(sprite, (x, y))


def draw_top_bar(window: pygame.Surface, state: GameState,
                 fonts: dict) -> None:
    """Plānā augšējā josla: nosaukums, līmenis, punkti, atslēga."""
    font = fonts["small"]
    width = window.get_width()
    bar = pygame.Surface((width, TOP_BAR_HEIGHT), pygame.SRCALPHA)
    bar.fill((14, 16, 20, 215))  # gandrīz melna, nedaudz caurspīdīga
    window.blit(bar, (0, 0))
    pygame.draw.line(window, UI_LINE,
                     (0, TOP_BAR_HEIGHT - 1), (width, TOP_BAR_HEIGHT - 1), 1)
    title = font.render("SHADOW COURIER", True, UI_ACCENT)
    window.blit(title, (12, (TOP_BAR_HEIGHT - title.get_height()) // 2))
    info = (f"LEVEL {state.level_number}   |   SCORE {state.score}"
            f"   |   KEY {1 if state.has_key else 0}")
    img = font.render(info, True, UI_TEXT)
    window.blit(img, (width - img.get_width() - 12,
                      (TOP_BAR_HEIGHT - img.get_height()) // 2))


def draw_hud(window: pygame.Surface, state: GameState,
             fonts: dict, sprites: dict) -> None:
    """Uzzīmē HUD: apakšējo joslu un augšējo plāno joslu.

    Apakšējā josla (HUD_HEIGHT px): sirdis (dzīvības), COINS x/y,
    lampas slēdža uzlādes josla ar READY, gaismas brīdinājums, paziņojumi.
    """
    width = window.get_width()
    font = fonts["small"]
    hud_top = state.level.height * gs.TILE_SIZE
    row1_y = hud_top + 8    # 1. rinda: ikonas
    row2_y = hud_top + 40   # 2. rinda: joslas

    # Joslas fons — tumšs, ar plānu gaišu līniju virsotnē
    pygame.draw.rect(window, (18, 21, 26), (0, hud_top, width, HUD_HEIGHT))
    pygame.draw.line(window, UI_LINE, (0, hud_top), (width, hud_top), 1)

    x = 12

    # --- Sirdis (dzīvības): pilnas, zaudētās — tumšas ---
    for i in range(START_LIVES):
        if i < state.lives:
            heart = sprites.get("ui_heart")
        else:
            heart = sprites.get("ui_heart_dark")
        _draw_hud_icon(window, heart, x, row1_y, COLOR_BAD)
        x += HUD_ICON_SIZE + 5
    x += 12

    # --- Monētas: "COINS X/Y" (paņemtās / visas šajā līmenī) ---
    _draw_hud_icon(window, sprites.get("ui_coin"), x, row1_y, COLOR_COIN)
    x += HUD_ICON_SIZE + 6
    total_coins = state.coins_collected + len(state.level.coins)
    coin_img = font.render(f"COINS {state.coins_collected}/{total_coins}",
                           True, UI_TEXT)
    window.blit(coin_img, (x, row1_y + 3))

    # --- Paziņojums (piem., "Vajag atslēgu!") — 1. rindas labajā pusē ---
    if state.message:
        msg_img = font.render(state.message, True, UI_ACCENT)
        window.blit(msg_img, (width - msg_img.get_width() - 12, row1_y + 3))

    # --- 2. rinda: lampas slēdža uzlādes josla ---
    x2 = 12
    label = font.render("LAMP", True, UI_DIM)
    window.blit(label, (x2, row2_y))
    x2 += label.get_width() + 10
    bar_w, bar_h = 110, 10
    bar_y = row2_y + 3
    pygame.draw.rect(window, (44, 48, 54), (x2, bar_y, bar_w, bar_h))
    if state.lamp_cooldown > 0:
        # Josla piepildās, kamēr slēdzis uzlādējas
        part = 1.0 - state.lamp_cooldown / gs.LAMP_COOLDOWN
    else:
        part = 1.0  # pilna = gatavs lietošanai
    if part > 0:
        pygame.draw.rect(window, UI_ACCENT,
                         (x2, bar_y, int(bar_w * part), bar_h))
    if part >= 1.0:
        window.blit(font.render("READY", True, UI_ACCENT),
                    (x2 + bar_w + 10, row2_y))

    # --- 2. rinda: lampas atklāšanas brīdinājums (sarkana josla + teksts) ---
    if state.lamp_exposure > 0:
        warn_x = x2 + bar_w + 70
        pygame.draw.rect(window, COLOR_BAD,
                         (warn_x, bar_y, int(100 * state.lamp_exposure), bar_h))
        window.blit(font.render("LIGHT!", True, COLOR_BAD),
                    (warn_x + 108, row2_y))

    # Augšējā plānā josla (zīmējas pār pasaules augšu)
    draw_top_bar(window, state, fonts)


# ============================================================
#  INDUSTRIĀLĀ PIKSEĻU STILA EKRĀNI (izvēlnes, pauze, beigu ekrāni)
#  Tumšs ogļu fons, krēmkrāsas teksts, viens dzeltens akcents,
#  plānas līnijas, monospace fonts. Izvēlētais variants =
#  dzeltens trijstūris pa kreisi + dzeltens teksts.
# ============================================================


def draw_panel(window: pygame.Surface, panel_width: int,
               panel_height: int) -> pygame.Rect:
    """Uzzīmē pārkares paneli ekrāna centrā un atgriež tās Rect.

    Aiz paneļa ekrāns nedaudz aptumšots, pats panelis — tumši pelēks
    ar plānu pelēku kontūru (nekādu lielu spīdīgu bloku).
    """
    width, height = window.get_size()
    rect = pygame.Rect(0, 0, panel_width, panel_height)
    rect.center = (width // 2, height // 2)
    shade = pygame.Surface((width, height), pygame.SRCALPHA)
    shade.fill((10, 11, 14, 170))
    window.blit(shade, (0, 0))
    pygame.draw.rect(window, UI_PANEL, rect)
    pygame.draw.rect(window, UI_LINE, rect, 1)
    return rect


def draw_cursor_triangle(window: pygame.Surface, x: int, y_center: int,
                         size: int = 12) -> None:
    """Uzzīmē dzeltenu kursora trijstūri (rāda pa labi).

    Zīmējam kā daudzstūri, nevis fonta simbolu — konsolas fontā
    trijstūra burtam reizēm nav glifi un tas rādās kā kvadrāts.
    """
    half = size // 2
    pygame.draw.polygon(window, UI_ACCENT,
                        [(x, y_center - half), (x, y_center + half),
                         (x + size, y_center)])


def draw_screen_title(window: pygame.Surface, fonts: dict, text: str,
                      y: int) -> None:
    """Liels virsraksts pilna ekrāna izvēlnē + plāna dzeltena līnija."""
    title = fonts["big"].render(text, True, UI_TEXT)
    window.blit(title, title.get_rect(center=(window.get_width() // 2, y)))
    pygame.draw.line(window, UI_ACCENT,
                     (window.get_width() // 2 - 150, y + 32),
                     (window.get_width() // 2 + 150, y + 32), 2)


def draw_panel_title(window: pygame.Surface, fonts: dict, rect: pygame.Rect,
                     text: str, color: tuple = UI_TEXT) -> None:
    """Virsraksts pārkares paneļa iekšpusē + plāna dzeltena līnija."""
    title = fonts["big"].render(text, True, color)
    window.blit(title, title.get_rect(center=(rect.centerx, rect.top + 50)))
    pygame.draw.line(window, UI_ACCENT,
                     (rect.left + 50, rect.top + 84),
                     (rect.right - 50, rect.top + 84), 2)


def draw_footer(window: pygame.Surface, fonts: dict, text: str) -> None:
    """Pelēks palīgteksts ekrāna apakšā (piem., vadības taustiņi)."""
    img = fonts["small"].render(text, True, UI_DIM)
    window.blit(img, img.get_rect(center=(window.get_width() // 2,
                                          window.get_height() - 40)))


def draw_menu_options(window: pygame.Surface, font: pygame.font.Font,
                      options: list[str], selection: int,
                      cx: int, y: int, line_height: int = 46) -> int:
    """Uzzīmē izvēlnes opcijas ar trijstūra kursoru. Atgriež y zem izvēlnes."""
    for i, option in enumerate(options):
        if i == selection:
            # Izvēlētā opcija: dzeltena ar trijstūri pa kreisi
            text = font.render(option, True, UI_ACCENT)
            draw_cursor_triangle(window, cx - text.get_width() // 2 - 34,
                                 y + i * line_height + text.get_height() // 2)
        else:
            text = font.render(option, True, UI_TEXT)
        window.blit(text, text.get_rect(center=(cx, y + i * line_height
                                                + text.get_height() // 2)))
    return y + len(options) * line_height


def main_menu_options(ui: dict, state: GameState) -> list[str]:
    """Galvenās izvēlnes opcijas. CONTINUE rādam tikai tad, ja šajā
    sesijā spēle ir sākta un pašlaik rit (var turpināt)."""
    options = []
    if ui["game_started"] and state.status == STATUS_PLAYING:
        options.append("CONTINUE")
    options.extend(["NEW GAME", "LEVEL SELECT", "SETTINGS", "QUIT"])
    return options


def level_complete_options(state: GameState) -> list[str]:
    """LEVEL COMPLETE opcijas. Pēdējā līmenī NEXT LEVEL nav (tad ir WIN)."""
    options = []
    if state.level_number < len(LEVEL_MAPS):
        options.append("NEXT LEVEL")
    options.append("LEVEL SELECT")
    return options


def draw_menu(window: pygame.Surface, fonts: dict, state: GameState,
              ui: dict) -> None:
    """Galvenā izvēlne: virsraksts + opcijas + vadības palīgs apakšā."""
    width, height = window.get_size()
    draw_screen_title(window, fonts, "SHADOW COURIER", height // 4 - 10)
    options = main_menu_options(ui, state)
    draw_menu_options(window, fonts["font"], options, ui["selection"],
                      width // 2, height // 2 - 50, line_height=48)
    draw_footer(window, fonts, CONTROLS_HELP)


def draw_level_select(window: pygame.Surface, fonts: dict, ui: dict) -> None:
    """Līmeņu izvēle: 01 STORAGE / 02 SECURITY / 03 LOADING BAY.

    Līmenis atbloķēts, ja iepriekšējais pabeigts šajā sesijā.
    Statuss: AVAILABLE / COMPLETED / LOCKED (bloķētais pelēks).
    """
    width, height = window.get_size()
    draw_screen_title(window, fonts, "LEVEL SELECT", height // 4 - 10)
    name_x = width // 2 - 170   # līmeņu nosaukumu kolonna (kreisi)
    status_x = width // 2 + 170  # statusa kolonna (labi, right-aligned)
    y = height // 2 - 70
    for i, name in enumerate(LEVEL_NAMES):
        n = i + 1
        unlocked = n == 1 or (n - 1) in ui["completed_levels"]
        completed = n in ui["completed_levels"]
        if completed:
            status, status_color = "COMPLETED", UI_ACCENT
        elif unlocked:
            status, status_color = "AVAILABLE", UI_DIM
        else:
            status, status_color = "LOCKED", UI_LOCKED
        selected = i == ui["selection"]
        if selected:
            name_color = UI_ACCENT
        elif unlocked:
            name_color = UI_TEXT
        else:
            name_color = UI_LOCKED
        img = fonts["font"].render(f"0{n} {name}", True, name_color)
        iy = y + i * 52
        window.blit(img, (name_x, iy))
        status_img = fonts["small"].render(status, True, status_color)
        window.blit(status_img, (status_x - status_img.get_width(), iy + 4))
        if selected:
            draw_cursor_triangle(window, name_x - 30,
                                 iy + img.get_height() // 2)
    draw_footer(window, fonts, "ENTER START   |   ESC BACK")


def draw_slider(window: pygame.Surface, fonts: dict, x: int, y: int,
                value: int, selected: bool) -> None:
    """Segmentēts slīdnis 0-100 (soli pa 10): 10 mazas kārbas + vērtība.

    Izvēlētam slīdnim vērtību rāda kā "< 70 >" — mājiens, ka
    kreiso/labo bultiņu var spiest, lai mainītu.
    """
    seg_w, seg_h, gap = 16, 10, 4
    for i in range(10):
        rx = x + i * (seg_w + gap)
        if value >= (i + 1) * 10:
            pygame.draw.rect(window, UI_ACCENT, (rx, y, seg_w, seg_h))
        else:
            pygame.draw.rect(window, (46, 50, 57), (rx, y, seg_w, seg_h))
    text_x = x + 10 * (seg_w + gap) + 12
    label = f"< {value} >" if selected else str(value)
    img = fonts["font"].render(label, True, UI_TEXT if selected else UI_DIM)
    window.blit(img, (text_x, y - 7))


def draw_settings(window: pygame.Surface, fonts: dict, ui: dict) -> None:
    """Iestatījumi: trīs skaļuma slīdņi, FULLSCREEN checkbox, CONTROLS.

    Skaļuma slīdņi pagaidām tikai glabā vērtību ui["volumes"]
    (audio sistēmas spēlē vēl nav). ESC = atpakaļ.
    """
    width, height = window.get_size()
    draw_screen_title(window, fonts, "SETTINGS", height // 4 - 20)
    label_x = width // 2 - 240
    ctrl_x = width // 2 + 20
    y = height // 2 - 110
    for i, row in enumerate(SETTINGS_ROWS):
        selected = i == ui["selection"]
        color = UI_ACCENT if selected else UI_TEXT
        img = fonts["font"].render(row, True, color)
        iy = y + i * 54
        window.blit(img, (label_x, iy))
        if selected:
            draw_cursor_triangle(window, label_x - 32,
                                 iy + img.get_height() // 2)
        if row in ui["volumes"]:
            draw_slider(window, fonts, ctrl_x, iy + 8,
                        ui["volumes"][row], selected)
        elif row == "FULLSCREEN":
            box = "[x]" if ui["fullscreen"] else "[ ]"
            box_img = fonts["font"].render(
                box, True, UI_ACCENT if selected else UI_DIM)
            window.blit(box_img, (ctrl_x, iy))
        else:  # CONTROLS — tikai parāda, neko nemaina
            ctrl_img = fonts["font"].render("WASD / ARROWS", True, UI_DIM)
            window.blit(ctrl_img, (ctrl_x, iy))
    draw_footer(window, fonts, "LEFT/RIGHT ADJUST   |   ESC BACK")


def draw_paused(window: pygame.Surface, fonts: dict, ui: dict) -> None:
    """Pauzes ekrāns: RESUME / RESTART LEVEL / SETTINGS / MAIN MENU."""
    rect = draw_panel(window, 480, 400)
    draw_panel_title(window, fonts, rect, "PAUSED")
    draw_menu_options(window, fonts["font"], PAUSE_OPTIONS, ui["selection"],
                      rect.centerx, rect.top + 120)


def _format_time(seconds: float) -> str:
    """Sekundes -> 'mm:ss' teksts LEVEL COMPLETE statistikai."""
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02d}:{secs:02d}"


def draw_level_complete(window: pygame.Surface, fonts: dict,
                        state: GameState, ui: dict) -> None:
    """LEVEL COMPLETE ekrāns: statistika (COINS, TIME, SCORE) + opcijas."""
    rect = draw_panel(window, 520, 450)
    cx = rect.centerx
    draw_panel_title(window, fonts, rect, "LEVEL COMPLETE")
    sub = fonts["small"].render(
        f"LEVEL {state.level_number:02d} — {LEVEL_NAMES[state.level_number - 1]}",
        True, UI_DIM)
    window.blit(sub, sub.get_rect(center=(cx, rect.top + 100)))

    # Statistika: kreisajā pusē nosaukums, labajā — vērtība
    stats = state.level_stats or {}
    rows = [
        ("COINS", f"{stats.get('coins', 0)}/{stats.get('coins_total', 0)}"),
        ("TIME", _format_time(stats.get("time", 0.0))),
        ("SCORE", str(stats.get("score", state.score))),
    ]
    y = rect.top + 140
    for label, value in rows:
        label_img = fonts["font"].render(label, True, UI_DIM)
        value_img = fonts["font"].render(value, True, UI_TEXT)
        window.blit(label_img, (rect.left + 70, y))
        window.blit(value_img, (rect.right - 70 - value_img.get_width(), y))
        y += 38

    draw_menu_options(window, fonts["font"], level_complete_options(state),
                      ui["selection"], cx, rect.bottom - 110, line_height=42)


def draw_game_over(window: pygame.Surface, fonts: dict,
                   state: GameState, ui: dict) -> None:
    """CAUGHT ekrāns: virsraksts + iemesls + TRY AGAIN / MAIN MENU."""
    rect = draw_panel(window, 500, 400)
    cx = rect.centerx
    draw_panel_title(window, fonts, rect, "CAUGHT", COLOR_BAD)
    reason = state.game_over_reason or "A guard spotted you."
    reason_img = fonts["font"].render(reason, True, UI_TEXT)
    window.blit(reason_img, reason_img.get_rect(center=(cx, rect.top + 120)))
    score = fonts["font"].render(f"SCORE  {state.score}", True, UI_DIM)
    window.blit(score, score.get_rect(center=(cx, rect.top + 160)))
    draw_menu_options(window, fonts["font"], CAUGHT_OPTIONS, ui["selection"],
                      cx, rect.top + 215, line_height=44)


def draw_won(window: pygame.Surface, fonts: dict, state: GameState,
             ui: dict) -> None:
    """Uzvaras ekrāns (visi līmeņi izieti): ALL MISSIONS COMPLETE."""
    rect = draw_panel(window, 560, 400)
    cx = rect.centerx
    draw_panel_title(window, fonts, rect, "ALL MISSIONS COMPLETE")
    score = fonts["font"].render(f"FINAL SCORE  {state.score}", True, UI_TEXT)
    window.blit(score, score.get_rect(center=(cx, rect.top + 130)))
    draw_menu_options(window, fonts["font"], WON_OPTIONS, ui["selection"],
                      cx, rect.top + 195, line_height=44)


# ============================================================
#  IEVADE — taustiņu apstrāde katram ekrānam
# ============================================================


def handle_key(key: int, current_screen: str, state: GameState,
               ui: dict) -> str:
    """Apstrādā vienu taustiņa nospiešanu un atgriež jauno ekrānu.

    ui["selection"] ir izvēlnes kursora pozīcija (to šeit arī maina).
    Pārējie ui lauki: settings_from, volumes, fullscreen, game_started,
    completed_levels — skat. main().
    """
    sel = ui["selection"]

    if current_screen == SCREEN_MENU:
        options = main_menu_options(ui, state)
        if key in (pygame.K_UP, pygame.K_w):
            ui["selection"] = (sel - 1) % len(options)
        elif key in (pygame.K_DOWN, pygame.K_s):
            ui["selection"] = (sel + 1) % len(options)
        elif key == pygame.K_RETURN:
            option = options[sel]
            if option == "QUIT":
                pygame.quit()
                sys.exit()
            if option == "CONTINUE":
                return SCREEN_GAME
            if option == "NEW GAME":
                state.__init__()   # jauna spēle no 1. līmeņa
                ui["game_started"] = True
                return SCREEN_GAME
            if option == "LEVEL SELECT":
                ui["selection"] = 0
                return SCREEN_LEVEL_SELECT
            if option == "SETTINGS":
                ui["settings_from"] = SCREEN_MENU
                ui["selection"] = 0
                return SCREEN_SETTINGS
        elif key in (pygame.K_ESCAPE, pygame.K_q):
            pygame.quit()
            sys.exit()

    elif current_screen == SCREEN_LEVEL_SELECT:
        if key in (pygame.K_UP, pygame.K_w):
            ui["selection"] = (sel - 1) % len(LEVEL_NAMES)
        elif key in (pygame.K_DOWN, pygame.K_s):
            ui["selection"] = (sel + 1) % len(LEVEL_NAMES)
        elif key == pygame.K_RETURN:
            n = sel + 1
            # Atbloķēts: 1. līmenis vai ja iepriekšējais pabeigts šajā sesijā
            if n == 1 or (n - 1) in ui["completed_levels"]:
                state.load_level(n)
                state.status = STATUS_PLAYING
                ui["game_started"] = True
                ui["selection"] = 0
                return SCREEN_GAME
        elif key == pygame.K_ESCAPE:
            ui["selection"] = 0
            return SCREEN_MENU

    elif current_screen == SCREEN_SETTINGS:
        if key in (pygame.K_UP, pygame.K_w):
            ui["selection"] = (sel - 1) % len(SETTINGS_ROWS)
        elif key in (pygame.K_DOWN, pygame.K_s):
            ui["selection"] = (sel + 1) % len(SETTINGS_ROWS)
        elif key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d,
                     pygame.K_RETURN):
            row = SETTINGS_ROWS[sel]
            if row in ui["volumes"]:
                step = 10 if key in (pygame.K_RIGHT, pygame.K_d,
                                     pygame.K_RETURN) else -10
                ui["volumes"][row] = max(0, min(100,
                                                ui["volumes"][row] + step))
            elif row == "FULLSCREEN":
                ui["fullscreen"] = not ui["fullscreen"]
                pygame.display.toggle_fullscreen()
        elif key == pygame.K_ESCAPE:
            target = ui["settings_from"]
            ui["selection"] = 0
            return target

    elif current_screen == SCREEN_GAME:
        if key == pygame.K_p:
            ui["selection"] = 0
            return SCREEN_PAUSED
        if key == pygame.K_ESCAPE:
            ui["selection"] = 0
            return SCREEN_MENU
        if key == pygame.K_SPACE:
            # Space = 2. mehānika: izslēgt tuvāko lampu (viena darbība)
            state.update(0.0, 0, 0, True, False)
        if key == pygame.K_e:
            # E = paņemt atslēgu / atvērt durvis (viena darbība)
            state.update(0.0, 0, 0, False, True)

    elif current_screen == SCREEN_PAUSED:
        if key in (pygame.K_UP, pygame.K_w):
            ui["selection"] = (sel - 1) % len(PAUSE_OPTIONS)
        elif key in (pygame.K_DOWN, pygame.K_s):
            ui["selection"] = (sel + 1) % len(PAUSE_OPTIONS)
        elif key in (pygame.K_RETURN, pygame.K_p):
            if key == pygame.K_p:  # P = ātrais ceļš uz RESUME
                return SCREEN_GAME
            option = PAUSE_OPTIONS[sel]
            if option == "RESUME":
                return SCREEN_GAME
            if option == "RESTART LEVEL":
                state.load_level(state.level_number)
                state.status = STATUS_PLAYING
                return SCREEN_GAME
            if option == "SETTINGS":
                ui["settings_from"] = SCREEN_PAUSED
                ui["selection"] = 0
                return SCREEN_SETTINGS
            # MAIN MENU: spēle paliek stāvoklī — to var turpināt ar CONTINUE
            ui["selection"] = 0
            return SCREEN_MENU
        elif key == pygame.K_ESCAPE:
            return SCREEN_GAME

    elif current_screen == SCREEN_LEVEL_COMPLETE:
        options = level_complete_options(state)
        if key in (pygame.K_UP, pygame.K_w):
            ui["selection"] = (sel - 1) % len(options)
        elif key in (pygame.K_DOWN, pygame.K_s):
            ui["selection"] = (sel + 1) % len(options)
        elif key == pygame.K_RETURN:
            if options[sel] == "NEXT LEVEL":
                state.next_level()
                ui["selection"] = 0
                return SCREEN_GAME
            ui["selection"] = 0
            return SCREEN_LEVEL_SELECT

    elif current_screen == SCREEN_GAME_OVER:
        if key in (pygame.K_UP, pygame.K_w):
            ui["selection"] = (sel - 1) % len(CAUGHT_OPTIONS)
        elif key in (pygame.K_DOWN, pygame.K_s):
            ui["selection"] = (sel + 1) % len(CAUGHT_OPTIONS)
        elif key == pygame.K_RETURN:
            if CAUGHT_OPTIONS[sel] == "TRY AGAIN":
                # Pārlādē pašreizējo līmeni ar pilnām dzīvībām
                state.lives = START_LIVES
                state.load_level(state.level_number)
                state.status = STATUS_PLAYING
                ui["game_started"] = True
                ui["selection"] = 0
                return SCREEN_GAME
            ui["selection"] = 0
            return SCREEN_MENU
        elif key == pygame.K_ESCAPE:
            ui["selection"] = 0
            return SCREEN_MENU

    elif current_screen == SCREEN_WON:
        if key in (pygame.K_UP, pygame.K_w):
            ui["selection"] = (sel - 1) % len(WON_OPTIONS)
        elif key in (pygame.K_DOWN, pygame.K_s):
            ui["selection"] = (sel + 1) % len(WON_OPTIONS)
        elif key == pygame.K_RETURN:
            if WON_OPTIONS[sel] == "PLAY AGAIN":
                state.__init__()
                ui["game_started"] = True
                ui["selection"] = 0
                return SCREEN_GAME
            ui["selection"] = 0
            return SCREEN_MENU
        elif key == pygame.K_ESCAPE:
            ui["selection"] = 0
            return SCREEN_MENU

    return current_screen


def main() -> None:
    """Spēles galvenā funkcija: atver logu un griež spēles ciklu."""
    pygame.init()
    pygame.display.set_caption("Shadow Courier")

    state = GameState()
    world_width = state.level.width * gs.TILE_SIZE
    world_height = state.level.height * gs.TILE_SIZE
    window = pygame.display.set_mode((world_width, world_height + HUD_HEIGHT))
    clock = pygame.time.Clock()
    # Industriālā stila ekrāniem — monospace fonts
    fonts = {
        "font": pygame.font.SysFont("consolas", 20),
        "big": pygame.font.SysFont("consolas", 44, bold=True),
        "small": pygame.font.SysFont("consolas", 16),
    }
    sprites = load_sprites()

    # Klienta pusē glabājamie UI dati (spēles loģikai tie nav vajadzīgi)
    ui = {
        "selection": 0,            # izvēlnes kursora pozīcija
        "settings_from": SCREEN_MENU,  # no kurienes atnācām uz SETTINGS
        "volumes": {"MASTER VOLUME": 70, "MUSIC": 60, "SOUND EFFECTS": 60},
        "fullscreen": False,
        "game_started": False,     # vai šajā sesijā spēle jau sākta (CONTINUE)
        "completed_levels": set(), # šajā sesijā pabeigtie līmeņi (1, 2, 3)
    }

    current_screen = SCREEN_MENU
    player_facing = (0, 1)  # kurp spēlētājs skatās (sākumā — uz leju)
    player_moving = False   # vai spēlētājs kustas (animācijai)

    while True:
        # dt = cik sekundes pagāja kopš iepriekšējā kadra (lai ātrums
        # nebūtu atkarīgs no datora jaudas)
        dt = clock.tick(FPS) / 1000.0

        # --- 1. solis: ievade (taustiņi un loga aizvēršana) ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                current_screen = handle_key(event.key, current_screen,
                                            state, ui)

        # --- 2. solis: atjaunināšana (tikai ja spēle rit) ---
        if current_screen == SCREEN_GAME:
            keys = pygame.key.get_pressed()
            move_x = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) \
                   - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
            move_y = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) \
                   - int(keys[pygame.K_w] or keys[pygame.K_UP])
            player_moving = (move_x != 0 or move_y != 0)
            # Virzienu bildēm atjauninām tikai taisnai kustībai.
            # Diagonāle (piem., W+D reizē) virzienā nav — tad atstājam
            # iepriekšējo (citādi FACING_ANGLES mestu KeyError un spēle aizvērtos!)
            if player_moving and (move_x == 0 or move_y == 0):
                player_facing = (move_x, move_y)  # atceramies pēdējo taisno virzienu
            # Space un E apstrādājam handle_key, lai viens nospiešanas = viena darbība
            state.update(dt, move_x, move_y, False, False)
            if state.status == STATUS_GAME_OVER:
                current_screen = SCREEN_GAME_OVER
                ui["selection"] = 0
            elif state.status == STATUS_WON:
                ui["completed_levels"].add(state.level_number)
                current_screen = SCREEN_WON
                ui["selection"] = 0
            elif state.status == STATUS_LEVEL_COMPLETE:
                ui["completed_levels"].add(state.level_number)
                current_screen = SCREEN_LEVEL_COMPLETE
                ui["selection"] = 0
        else:
            # Pauzē/izvēlnē spēlētājs nekustas — animācija apstājas
            player_moving = False

        # --- 3. solis: zīmēšana ---
        window.fill(UI_BG)
        if current_screen == SCREEN_MENU:
            draw_menu(window, fonts, state, ui)
        elif current_screen == SCREEN_LEVEL_SELECT:
            draw_level_select(window, fonts, ui)
        elif current_screen == SCREEN_SETTINGS:
            draw_settings(window, fonts, ui)
        else:
            draw_world(window, state, sprites, player_facing, player_moving)
            draw_hud(window, state, fonts, sprites)
            if current_screen == SCREEN_PAUSED:
                draw_paused(window, fonts, ui)
            elif current_screen == SCREEN_LEVEL_COMPLETE:
                draw_level_complete(window, fonts, state, ui)
            elif current_screen == SCREEN_GAME_OVER:
                draw_game_over(window, fonts, state, ui)
            elif current_screen == SCREEN_WON:
                draw_won(window, fonts, state, ui)

        pygame.display.flip()


if __name__ == "__main__":
    main()
