"""Shadow Courier — pygame klients.

Šis fails TIKAI nolasa taustiņus un zīmē ekrānu.
Visa loģika ir mapē game/ (skat. game/game_state.py).

Palaišana:  python -m client.main
Vadība:     WASD/bultiņas — kustēties, Space — izslēgt lampu,
            E — paņemt/atvērt, P — pauze, Esc — atpakaļ.
"""

import math
import os
import sys

import pygame

from game import settings as gs
from game.game_state import (GameState, STATUS_PLAYING, STATUS_GAME_OVER,
                             STATUS_WON, STATUS_LEVEL_COMPLETE)
from game.level import LEVEL_MAPS
from game.rank import better_rank

# Servera klients rekordu sūtīšanai (spēles beigās).
# Simulācijas skripti to nelieto, tāpēc sims nekad nesūta uz serveri.
import api_client

# --- LOGA UZSTĀDĪJUMI ---
FPS = 60           # kadri sekundē
HUD_HEIGHT = 112   # apakšējā HUD josla (pikseļi); karte zīmējas virs tās
TOP_BAR_HEIGHT = 30  # augšējā plānā josla (zīmējas PĀRKLĀJ pasaulei)

# --- HITBOXI (līgums ar game/ moduli) ---
# getattr noklusējumi, lai klients strādātu arī ar vecāku game/ versiju
PLAYER_HIT_W = getattr(gs, "PLAYER_HIT_W", 24)
PLAYER_HIT_H = getattr(gs, "PLAYER_HIT_H", 14)
GUARD_HIT_W = getattr(gs, "GUARD_HIT_W", 36)
GUARD_HIT_H = getattr(gs, "GUARD_HIT_H", 36)
PLAYER_SPRITE = getattr(gs, "PLAYER_SPRITE", 64)
GUARD_SPRITE = getattr(gs, "GUARD_SPRITE", 72)
START_LIVES = getattr(gs, "START_LIVES", 3)


def sprite_pos(hit_x: float, hit_y: float, hit_w: int, hit_h: int,
               sprite_size: int) -> tuple[float, float]:
    """Sprite augšējais kreisais stūris tā, lai tēls "stāvētu" uz hitboxa
    (kājas uz hitboxa apakšas, horizontāli centrēts)."""
    return (hit_x + hit_w / 2 - sprite_size / 2, hit_y + hit_h - sprite_size)


# --- PASAULES KRĀSAS (R, G, B) ---
COLOR_FLOOR = (34, 40, 52)      # grīda
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

# --- PIKSEĻU UI KRĀSAS ---
UI_BG = (20, 23, 28)        # ogļu pelēks fons (#14171c)
UI_PANEL = (27, 31, 38)     # paneļa fons
UI_LINE = (58, 63, 72)      # plānas līnijas / kontūras
UI_TEXT = (232, 227, 211)   # krēmkrāsas gaišs teksts (#e8e3d3)
UI_DIM = (126, 128, 134)    # pelēks palīgteksts
UI_LOCKED = (88, 90, 96)    # bloķēts elements
UI_ACCENT = (232, 185, 60)  # VIENS dzeltens akcents (#e8b93c)

# --- APAKŠĒJĀ HUD JOSLA ---
# Fonts nokopēts projektā — lai izskats vienāds jebkurā datorā
HUD_FONT_PATH = os.path.join("assets", "fonts", "VerdanaBold.ttf")
HUD_TITLE_SIZE = 16          # sadaļu virsraksti (HEALTH, COINS, ...)
HUD_VALUE_SIZE = 30          # lielās vērtības ("READY", "85%", "2 / 5")
HUD_BG = (17, 22, 25)        # joslas fons (#111619)
HUD_TEXT = (244, 243, 235)   # gandrīz balts teksts (#F4F3EB)
HUD_DIVIDER = (42, 49, 56)   # vertikālās dalītājlīnijas (#2a3138)
HUD_PADDING = 16             # sadaļas iekšējā atstarpe no malām (px)
HUD_READY = (90, 200, 120)   # zaļš "READY" un uzlādes josla
HUD_DANGER = (255, 59, 48)   # sarkans briesmu aizpildījums (#ff3b30)
HUD_DANGER_BG = (58, 18, 16) # EXPOSURE fons pie >= 75% (#3a1210)
HEART_RED = (228, 72, 60)    # aizpildītā sirds
HEART_EMPTY = (150, 156, 162)  # zaudētās sirds kontūra
HUD_BAR_EMPTY = (40, 46, 52) # tukšā progresa joslas daļa
EXPOSURE_CRITICAL = 0.75     # no šejienes EXPOSURE ir "bīstams"
PROMPT_LINE_HEIGHT = 28      # E-uzvednes rinda tieši virs HUD joslas

# --- APGAISMOJUMA UZSTĀDĪJUMI ---
DARKNESS_ALPHA = 110        # cik tumši ārpus gaismas (0-255)
GLOW_COLOR = (255, 200, 90) # lampu un lukturu siltā krāsa
GLOW_GAIN = 0.35            # lampu mirdzuma spilgtums
GUARD_LIGHT_RADIUS = 150    # sarga luktura attālums (pikseļi)
GUARD_CONE_ANGLE = 32       # luktura konusa puse (grādi)
CONE_GLOW_GAIN = 0.30       # luktura mirdzuma spilgtums
VIGNETTE_ALPHA = 90         # cik tumšas ekrāna malas (0-255)
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

# Izvēļņu opcijas (bultiņas/WASD + Enter, kursors = trijstūris)
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
    "coin": 26, "key": 30, "package": 26,
    # Slēptuve (metāla skapītis) — aizņem visu flīzi, bet flīze nav cieta
    "hideout": gs.TILE_SIZE,
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
FRAME_SWITCH_MS = 120  # ik pēc tik ms mainās soļa kadrs
SWAY_DEGREES = 4       # par cik grādiem tēls "šūpojas", ejot


def load_sprites() -> dict:
    """Ielādē tekstūras no assets/ un samazina līdz spēles izmēram.

    Ja kādas bildes nav — zīmē parastos kvadrātus, spēle nestājas.
    Papildus ielādē soļu kadru sarakstus (player_1..4.png utt.);
    ja kadru nav, sarakstā viena bilde — animācija vienkārši nerit.
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
    # ja vispār nav — vārdnīcā None un draw_world lieto veco
    # variantu (kadri + rotācija).
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

    # Dedzinošā lampa: ja ir lamp_on.png, lieto to visām;
    # citādi vecie varianti lamp_1..4.png
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
    # parastā un tumšā ("tukšā", piem., zaudēta dzīvība)
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
    """Uzzīmē bildi vietā (x, y). Ja bildes nav — kvadrātu.
    angle — par cik grādiem pagriezt."""
    if sprite is None:
        pygame.draw.rect(window, fallback_color, (x, y, size, size))
        return
    if angle != 0.0:
        sprite = pygame.transform.rotate(sprite, angle)
    # Rotācija maina bildes izmēru, tāpēc centrējam ap vēlamo punktu
    rect = sprite.get_rect(center=(x + size / 2, y + size / 2))
    window.blit(sprite, rect)


# ============================================================
#  APGAISMOJUMS — kā tas strādā:
#  Vienreiz uztaisam "gaismas sprites" (mīkstus gradientus),
#  katrā kadrā uzklājam melnu tumsas slāni un ar BLEND_RGBA_SUB
#  "izgriežam" gaišas vietas, kur deg lampas un lukturi.
#  Beigās pievienojam siltu mirdzumu (ADD) un vinjetti.
# ============================================================

# Kešs gatavajiem gradientiem: gradientu rēķina VIENREIZ (tas ir dārgi),
# katrā kadrā tikai zīmē un griež
_light_cache: dict = {}


def _build_radial_pixels(radius: int, alpha_func) -> pygame.Surface:
    """Kvadrātveida Surface (2*radius); katra pikseļa alpha nosaka
    alpha_func(distance, angle). Centrā alpha liela, uz malām 0."""
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
    Pikseļa RGB = krāsa * value_func(distance, angle)/255 * gain."""
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
    strength < 1 atstaj daļu tumsas — gaiši, bet ne pilnīgi spilgti."""
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


def _sector_value(distance: float, angle: float, radius: int,
                  half_angle_deg: float) -> float:
    """Gaismas sektora spilgtums punktā (sektors zīmēts rādot pa labi).
    Mazāk gaismas tālāk no avota un pie sektora malām."""
    half = math.radians(half_angle_deg)
    if distance >= radius or abs(angle) > half:
        return 0.0
    along = 1.0 - distance / radius      # mazāk gaismas tālāk
    side = 1.0 - abs(angle) / half       # mazāk gaismas pie malām
    return 255 * along * along * (0.35 + 0.65 * side)


def _cone_value(distance: float, angle: float, radius: int) -> float:
    """Luktura konusa spilgtums punktā (konuss zīmēts rādot pa labi)."""
    return _sector_value(distance, angle, radius, GUARD_CONE_ANGLE)


def get_light_cone(radius: int) -> pygame.Surface:
    """Sarga luktura konuss (alpha versija tumsas izgriešanai)."""
    key = ("cone", radius)
    if key not in _light_cache:
        _light_cache[key] = _build_radial_pixels(
            radius, lambda d, a: _cone_value(d, a, radius))
    return _light_cache[key]


def get_rotated_cone(direction: tuple[float, float], colored: bool) -> pygame.Surface:
    """Luktura konuss, pagriezts konkrētā virzienā (kešots).

    Virzienu noapaļo līdz 5 grādiem, lai kešā neuzkrātos simtiem
    gandrīz vienādu konusu.
    colored=False — alpha tumsas izgriešanai (SUB), True — mirdzumam (ADD).
    """
    dx, dy = direction
    # Konuss zīmēts pa labi; pygame.rotate griež pretēji pulkstenim,
    # tāpēc ekrānā (y uz leju) formula ir šāda:
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


def get_lamp_sector(direction: tuple[int, int], colored: bool) -> pygame.Surface:
    """Lampas gaismas sektors, pagriezts lampas virzienā (kešots).

    110° konuss ar LIGHT_RADIUS rādiusu — tā pati zona, ko detekcijai
    lieto Level.point_in_lamp_light, tāpēc redzamais un EXPOSURE sakrīt.
    Lampas virzieni ir tikai 4, tāpēc kešā arī tikai 4 varianti.
    """
    dx, dy = direction
    # Sektors zīmēts pa labi; rotācijas formula kā konusam augstāk
    angle = -math.degrees(math.atan2(dy, dx))
    key = ("lamp_sector", angle, colored)
    if key not in _light_cache:
        if colored:
            sector = _build_glow_pixels(
                gs.LIGHT_RADIUS, GLOW_COLOR, GLOW_GAIN,
                lambda d, a: _sector_value(d, a, gs.LIGHT_RADIUS,
                                           gs.LAMP_LIGHT_HALF_ANGLE))
        else:
            sector = _build_radial_pixels(
                gs.LIGHT_RADIUS,
                lambda d, a: _sector_value(d, a, gs.LIGHT_RADIUS,
                                           gs.LAMP_LIGHT_HALF_ANGLE))
        _light_cache[key] = pygame.transform.rotate(sector, angle) \
            if angle else sector
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
    """Tumsa + lampu peles + lukturi + kurjera aplis + vinjete.
    Izsauc PĒC tam, kad visa pasaule jau uzzīmēta."""
    t = gs.TILE_SIZE
    world_w = state.level.width * t
    world_h = state.level.height * t

    # 1. tumsas slānis pār visu pasauli
    darkness = pygame.Surface((world_w, world_h), pygame.SRCALPHA)
    darkness.fill((0, 0, 0, DARKNESS_ALPHA))

    # 2. katrai degošai lampai "izgriež" gaišu sektoru tumsā
    # (SUB atņem sprite alpha no tumsas alpha — tur paliek caurspīdīgi)
    for lamp_pos, off_timer in state.level.lamps.items():
        if off_timer <= 0:
            direction = state.level.lamp_info[lamp_pos][1]
            origin = state.level.lamp_light_origin(lamp_pos)
            sector = get_lamp_sector(direction, colored=False)
            darkness.blit(sector, sector.get_rect(center=origin),
                          special_flags=pygame.BLEND_RGBA_SUB)

    # 3. sargu lukturu konusi (centri = hitboxa centrs)
    for guard in state.level.guards:
        cone = get_rotated_cone(guard.facing, colored=False)
        center = (guard.x + GUARD_HIT_W / 2, guard.y + GUARD_HIT_H / 2)
        darkness.blit(cone, cone.get_rect(center=center),
                      special_flags=pygame.BLEND_RGBA_SUB)

    # 4. kurjera silto dzintaru gaismas aplis (seko hitboxa centram)
    player_center = (state.player_x + PLAYER_HIT_W / 2,
                     state.player_y + PLAYER_HIT_H / 2)
    player_circle = get_light_circle(PLAYER_LIGHT_RADIUS, PLAYER_LIGHT_CUT)
    darkness.blit(player_circle, player_circle.get_rect(center=player_center),
                  special_flags=pygame.BLEND_RGBA_SUB)

    # 5. gaisma neiet caur cietām flīzēm: cietās flīzes aizkrāsojam
    # atpakaļ ar tumsu, citādi gaisma aizplūst uz blakus istabu
    for row in range(state.level.height):
        for col in range(state.level.width):
            if state.level.is_solid_tile(col, row):
                darkness.fill((0, 0, 0, DARKNESS_ALPHA),
                              (col * t, row * t, t, t))

    # 6. uzklāj tumsu ar izgrieztajām gaismas vietām
    window.blit(darkness, (0, 0))

    # 7. silti mirdzumi gaismas vietās (aditīvi)
    for lamp_pos, off_timer in state.level.lamps.items():
        if off_timer <= 0:
            direction = state.level.lamp_info[lamp_pos][1]
            origin = state.level.lamp_light_origin(lamp_pos)
            sector_glow = get_lamp_sector(direction, colored=True)
            window.blit(sector_glow, sector_glow.get_rect(center=origin),
                        special_flags=pygame.BLEND_RGB_ADD)
    for guard in state.level.guards:
        cone_glow = get_rotated_cone(guard.facing, colored=True)
        center = (guard.x + GUARD_HIT_W / 2, guard.y + GUARD_HIT_H / 2)
        window.blit(cone_glow, cone_glow.get_rect(center=center),
                    special_flags=pygame.BLEND_RGB_ADD)
    # Kurjera dzintara mirdzums (viegls, statisks)
    player_glow = get_glow_circle(PLAYER_LIGHT_RADIUS, PLAYER_GLOW_COLOR,
                                  PLAYER_GLOW_GAIN)
    window.blit(player_glow, player_glow.get_rect(center=player_center),
                special_flags=pygame.BLEND_RGB_ADD)

    # 8. vinjete — ekrāna malas nedaudz tumšākas
    window.blit(get_vignette(world_w, world_h), (0, 0))


# ============================================================
#  PASAULES ZĪMĒŠANA
# ============================================================

# Virziens (x, y) -> rotācijas leņķis bildēm (sprites zīmēti "skatās uz leju")
FACING_ANGLES = {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}

# Virziens (x, y) -> virzienu sprites vārdnīcas atslēga
FACING_NAMES = {(0, 1): "down", (0, -1): "up", (1, 0): "right", (-1, 0): "left"}


def _facing_cardinal(facing: tuple[float, float]) -> tuple[int, int]:
    """No sarga peldošā skata virziena atgriež tuvāko no 4 virzieniem."""
    fx, fy = facing
    if abs(fx) >= abs(fy):
        return (1, 0) if fx >= 0 else (-1, 0)
    return (0, 1) if fy >= 0 else (0, -1)


def _draw_alert_icon(window: pygame.Surface, sx: float, sy: float,
                     sprite_size: int) -> None:
    """Sarkanais "!" virs sarga (divi taisnstūri: svītra + punkts)."""
    center_x = sx + sprite_size / 2
    top = sy - 24
    pygame.draw.rect(window, COLOR_BAD, (center_x - 3, top, 6, 14))
    pygame.draw.rect(window, COLOR_BAD, (center_x - 3, top + 17, 6, 5))


def _pick_character_sprite(sprites: dict, name: str, facing: tuple[int, int],
                           now: int, frame_offset: int, moving: bool) -> tuple:
    """Izvēlas bildi spēlētājam/sargam un rotācijas leņķi.

    Ja ir virzienu sprites — ņem pareizo bildi, rotācijas nav.
    Ja nav — vecais variants: soļu kadri + rotācija.
    Atgriež (bilde, rotācijas_leņķis).
    """
    dir_sprites = sprites.get(name + "_dir")
    if dir_sprites is not None:
        # Diagonālei nav savas bildes — rādam "down"
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
    player_moving — ja True, rit soļu animācija un šūpošanās."""
    level = state.level
    t = gs.TILE_SIZE
    # Pašreizējais laiks ms — no tā rēķina animācijas kadru
    now = pygame.time.get_ticks()

    # Grīda un sienas
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

    # Lampas: korpuss zīmēts pie sienas iekšējās malas (lamp_light_origin),
    # pagriezts gaismas virzienā. ON un OFF zīmē vienādā punktā,
    # tāpēc lampa nepārvietojas, pārslēdzoties. Zīmējam PĒC sienām,
    # lai siena korpusu neaizsegtu.
    lamp_frames = sprites["lamp_frames"]
    for lamp_index, (lamp_pos, off_timer) in enumerate(level.lamps.items()):
        if off_timer <= 0:
            lamp = lamp_frames[lamp_index % len(lamp_frames)]
            color = COLOR_LAMP_ON
        else:
            lamp = sprites["lamp_off"]
            color = COLOR_LAMP_OFF
        direction = level.lamp_info[lamp_pos][1]
        angle = FACING_ANGLES[direction]
        origin = level.lamp_light_origin(lamp_pos)
        if lamp is None:
            pygame.draw.rect(window, color,
                             (origin[0] - t // 4, origin[1] - t // 4,
                              t // 2, t // 2))
        else:
            rotated = pygame.transform.rotate(lamp, angle) if angle else lamp
            window.blit(rotated, rotated.get_rect(center=origin))

    # Dekoratīvie šķēršļi ('x' kartē)
    # Kuras kastes kur — izvēlamies pēc koordinātām, lai vienmēr vienādi
    for col, row in level.props:
        prop_name = PROP_SPRITES[(col * 7 + row * 13) % len(PROP_SPRITES)]
        draw_sprite(window, sprites[prop_name], col * t, row * t, t, COLOR_WALL)

    # Slēptuves ('H' kartē, flīze paliek brīva)
    for col, row in level.hideouts:
        draw_sprite(window, sprites["hideout"], col * t, row * t, t, UI_LINE)

    # Sūtījums ar vieglu pulsējošu mirdzumu, kamēr nav paņemts
    if level.package_pos is not None and not level.package_taken:
        pcol, prow = level.package_pos
        draw_sprite(window, sprites["package"],
                    pcol * t + 11, prow * t + 11, 26, UI_ACCENT)
        # Mirdzums elpo ar sinusa viļņi
        # (noapaļots, lai kešā neuzkrātos simtiem variantu)
        pulse = round(0.25 + 0.15 * math.sin(now * 0.006), 2)
        glow = get_glow_circle(30, UI_ACCENT, pulse)
        center = (pcol * t + t // 2, prow * t + t // 2)
        window.blit(glow, glow.get_rect(center=center),
                    special_flags=pygame.BLEND_RGB_ADD)

    # Sargi (pagriežas skata virzienā; brīdinājuma laikā stāv).
    # guard.x/.y ir hitboxa stūris; tēlu zīmē ar "kājām uz hitboxa".
    for guard in level.guards:
        guard_dir = _facing_cardinal(guard.facing)
        # Nobīde, lai visi sargi neietu sinhroni
        offset = (int(guard.x) + int(guard.y)) // 10
        sprite, angle = _pick_character_sprite(
            sprites, "guard", guard_dir, now, offset, moving=guard.moving)
        sway = SWAY_DEGREES * math.sin(now * 0.02 + offset) if guard.moving else 0.0
        sx, sy = sprite_pos(guard.x, guard.y, GUARD_HIT_W, GUARD_HIT_H,
                            GUARD_SPRITE)
        draw_sprite(window, sprite, sx, sy, GUARD_SPRITE,
                    COLOR_GUARD, angle + sway)

    # Spēlētājs (kurjers): tēls stāv uz hitboxa apakšas, centrēts
    if player_moving:
        # Soļu šūpošanās: sprite viegli griežas pa labi/kreisi (sinusa vilnis)
        sway = SWAY_DEGREES * math.sin(now * 0.02)
    else:
        sway = 0.0
    sprite, angle = _pick_character_sprite(
        sprites, "player", player_facing, now, 0, player_moving)
    sx, sy = sprite_pos(state.player_x, state.player_y,
                        PLAYER_HIT_W, PLAYER_HIT_H, PLAYER_SPRITE)
    if state.hidden and sprite is not None:
        # Paslēpies slēptuvē: kurjers puscaurspīdīgs
        sprite = sprite.copy()
        sprite.set_alpha(70)
    draw_sprite(window, sprite, sx, sy, PLAYER_SPRITE,
                COLOR_PLAYER, angle + sway)

    # Tumsa + gaismas PĒC visa cita — tā "nosedz" pasauli,
    # izņemot vietas, kur deg lampas, spīd lukturi un iet kurjers
    draw_lighting(window, state)

    # Sarkanais "!" virs sarga zīmējam PĒC tumsas, lai paliktu
    # spilgts arī tumsā (tā ir UI zīme, ne pasaules daļa)
    for guard in level.guards:
        if guard.alert_icon_timer > 0:
            sx, sy = sprite_pos(guard.x, guard.y, GUARD_HIT_W, GUARD_HIT_H,
                                GUARD_SPRITE)
            _draw_alert_icon(window, sx, sy, GUARD_SPRITE)


# ============================================================
#  HUD — augšējā plānā josla un apakšējā informācijas josla
# ============================================================


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
            f"   |   KEY {1 if state.has_key else 0}"
            f"   |   PACKAGE {1 if state.level.package_taken else 0}/1")
    img = font.render(info, True, UI_TEXT)
    window.blit(img, (width - img.get_width() - 12,
                      (TOP_BAR_HEIGHT - img.get_height()) // 2))


def load_hud_fonts() -> dict:
    """HUD fonti no assets/fonts/ (nokopēts Windows fonts).
    Ja fails pazudis — sistēmas fonts, lai spēle nestātos."""
    if os.path.exists(HUD_FONT_PATH):
        return {
            "title": pygame.font.Font(HUD_FONT_PATH, HUD_TITLE_SIZE),
            "value": pygame.font.Font(HUD_FONT_PATH, HUD_VALUE_SIZE),
        }
    return {
        "title": pygame.font.SysFont("verdana", HUD_TITLE_SIZE, bold=True),
        "value": pygame.font.SysFont("verdana", HUD_VALUE_SIZE, bold=True),
    }


def _draw_heart(window: pygame.Surface, cx: int, cy: int, size: int,
                filled: bool) -> None:
    """Viena sirds: divi apļi augšā un rombs apakšā.
    filled=True — sarkana (atlikusi dzīvība), False — tikai kontūra."""
    r = size // 4 + 1                      # apļu rādiuss
    color = HEART_RED if filled else HEART_EMPTY
    outline = 0 if filled else 2           # 0 = aizpildīts, 2 = tikai kontūra
    pygame.draw.circle(window, color, (cx - r + 1, cy - 2), r, outline)
    pygame.draw.circle(window, color, (cx + r - 1, cy - 2), r, outline)
    pygame.draw.polygon(window, color,
                        [(cx - 2 * r + 1, cy - 3), (cx + 2 * r - 1, cy - 3),
                         (cx, cy + size // 2)], outline)


def _draw_warning_triangle(window: pygame.Surface, cx: int, cy: int,
                           color: tuple) -> None:
    """Brīdinājuma trijstūris ar tumšu "!" iekšā."""
    r = 10
    pygame.draw.polygon(window, color,
                        [(cx, cy - r), (cx - r + 1, cy + r - 2),
                         (cx + r - 1, cy + r - 2)])
    pygame.draw.rect(window, HUD_BG, (cx - 1, cy - 5, 3, 8))   # "!" svītra
    pygame.draw.rect(window, HUD_BG, (cx - 1, cy + 4, 3, 3))   # "!" punkts


def _draw_section_title(window: pygame.Surface, fonts: dict, text: str,
                        x: int, y: int) -> None:
    """Sadaļas virsraksts (HEALTH, COINS, LAMP, EXPOSURE)."""
    window.blit(fonts["hud"]["title"].render(text, True, HUD_TEXT), (x, y))


def _draw_hud_health(window: pygame.Surface, state: GameState,
                     fonts: dict, bounds: tuple, hud_top: int) -> None:
    """HEALTH sadaļa: 3 sirdis (pilnas sarkanas, zaudētās — kontūra)."""
    x0, _ = bounds
    _draw_section_title(window, fonts, "HEALTH", x0 + HUD_PADDING,
                        hud_top + 12)
    size, gap = 28, 10
    cy = hud_top + 66
    for i in range(START_LIVES):
        cx = x0 + HUD_PADDING + size // 2 + i * (size + gap)
        _draw_heart(window, cx, cy, size, filled=(i < state.lives))


def _draw_hud_coins(window: pygame.Surface, state: GameState,
                    fonts: dict, sprites: dict, bounds: tuple,
                    hud_top: int) -> None:
    """COINS sadaļa: monētas ikona + lielā vērtība "2 / 5"."""
    x0, _ = bounds
    _draw_section_title(window, fonts, "COINS", x0 + HUD_PADDING,
                        hud_top + 12)
    icon_y = hud_top + 54
    coin = sprites.get("ui_coin")
    if coin is not None:
        window.blit(coin, (x0 + HUD_PADDING, icon_y))
    else:
        # Rezerves variants, ja nav bildes: zelta aplis ar kontūru
        center = (x0 + HUD_PADDING + 12, icon_y + 12)
        pygame.draw.circle(window, UI_ACCENT, center, 12)
        pygame.draw.circle(window, (150, 112, 25), center, 12, 2)
    total = state.coins_collected + len(state.level.coins)
    img = fonts["hud"]["value"].render(
        f"{state.coins_collected} / {total}", True, HUD_TEXT)
    window.blit(img, (x0 + HUD_PADDING + 36, icon_y + 12
                      - img.get_height() // 2))


def _draw_hud_lamp(window: pygame.Surface, state: GameState,
                   fonts: dict, bounds: tuple, hud_top: int) -> None:
    """LAMP sadaļa: SPACE taustiņa rāmītis + READY vai atlikušais laiks.
    Pozīcijas fiksētas — nekas nepārbīdās, mainoties stāvoklim."""
    x0, x1 = bounds
    _draw_section_title(window, fonts, "LAMP", x0 + HUD_PADDING, hud_top + 12)
    ready = state.lamp_cooldown <= 0
    key_color = HUD_TEXT if ready else UI_LOCKED  # cooldown = pieklusināts

    # Taustiņa rāmītis ar uzrakstu SPACE
    key_img = fonts["hud"]["title"].render("SPACE", True, key_color)
    key_rect = pygame.Rect(x0 + HUD_PADDING, hud_top + 42,
                           key_img.get_width() + 14, key_img.get_height() + 8)
    pygame.draw.rect(window, key_color, key_rect, 1, border_radius=4)
    window.blit(key_img, (key_rect.x + 7, key_rect.y + 4))

    if ready:
        img = fonts["hud"]["value"].render("READY", True, HUD_READY)
    else:
        img = fonts["hud"]["value"].render(
            f"{state.lamp_cooldown:.1f} s", True, HUD_TEXT)
    window.blit(img, (key_rect.right + 12,
                      key_rect.centery - img.get_height() // 2))

    if not ready:
        # Plāna uzlādes josla: piepildās, tuvojoties gatavībai
        bar_y = key_rect.bottom + 8
        bar_w = x1 - HUD_PADDING - key_rect.x
        pygame.draw.rect(window, HUD_BAR_EMPTY,
                         (key_rect.x, bar_y, bar_w, 10))
        part = 1.0 - state.lamp_cooldown / gs.LAMP_COOLDOWN
        if part > 0:
            pygame.draw.rect(window, HUD_READY,
                             (key_rect.x, bar_y, int(bar_w * part), 10))


def _draw_hud_exposure(window: pygame.Surface, state: GameState,
                       fonts: dict, bounds: tuple, hud_top: int) -> None:
    """EXPOSURE sadaļa: procenti + progresa josla + brīdinājums.

    >0%: dzintara aizpildījums + "MOVE INTO SHADOW".
    >=75%: sarkans aizpildījums, tumši sarkans fons un sarkana
    līnija kreisajā malā. Brīdinājuma vieta rezervēta izkārtojumā.
    """
    x0, x1 = bounds
    exposure = max(0.0, min(1.0, state.lamp_exposure))
    critical = exposure >= EXPOSURE_CRITICAL
    pad = HUD_PADDING + 4  # mazliet lielāka atstarpe sarkanas malas dēļ

    if critical:
        pygame.draw.rect(window, HUD_DANGER_BG,
                         (x0 + 1, hud_top + 1, x1 - x0 - 1, HUD_HEIGHT - 2))
        pygame.draw.rect(window, HUD_DANGER,
                         (x0 + 1, hud_top + 1, 4, HUD_HEIGHT - 2))

    # Virsraksts pa kreisi, lielie procenti pa labi (vienā augstumā)
    _draw_section_title(window, fonts, "EXPOSURE", x0 + pad, hud_top + 12)
    pct_color = HUD_DANGER if critical else HUD_TEXT
    pct_img = fonts["hud"]["value"].render(
        f"{round(exposure * 100)}%", True, pct_color)
    window.blit(pct_img, (x1 - HUD_PADDING - pct_img.get_width(),
                          hud_top + 8))

    # Progresa josla: tukšā daļa tumši pelēka ar plānu kontūru
    bar_x = x0 + pad
    bar_y = hud_top + 52
    bar_w = x1 - HUD_PADDING - bar_x
    pygame.draw.rect(window, HUD_BAR_EMPTY, (bar_x, bar_y, bar_w, 18))
    pygame.draw.rect(window, HUD_DIVIDER, (bar_x, bar_y, bar_w, 18), 1)
    if exposure > 0:
        fill = HUD_DANGER if critical else UI_ACCENT
        pygame.draw.rect(window, fill,
                         (bar_x + 1, bar_y + 1,
                          int((bar_w - 2) * exposure), 16))

    # Brīdinājums (vieta rezervēta jau izkārtojumā)
    if exposure > 0:
        color = HUD_DANGER if critical else UI_ACCENT
        _draw_warning_triangle(window, bar_x + 10, bar_y + 34, color)
        warn_font = fonts["hud"]["value"] if critical \
            else fonts["hud"]["title"]
        warn_img = warn_font.render("MOVE INTO SHADOW", True, color)
        window.blit(warn_img, (bar_x + 28,
                               bar_y + 34 - warn_img.get_height() // 2))


def draw_hud(window: pygame.Surface, state: GameState,
             fonts: dict, sprites: dict) -> None:
    """Apakšējā 4-sadaļu HUD josla + augšējā plānā josla.
    E-uzvedne un paziņojums zīmējas rindā tieši virs joslas."""
    width = window.get_width()
    font = fonts["small"]
    hud_top = window.get_height() - HUD_HEIGHT

    # E-uzvedne un paziņojums ("E PICK UP PACKAGE", "Vajag atslēgu!" u.tml.)
    prompt = interaction_prompt(state)
    if prompt:
        prompt_img = font.render(prompt, True, UI_ACCENT)
        window.blit(prompt_img, (12, hud_top - PROMPT_LINE_HEIGHT + 6))
    if state.message:
        msg_img = font.render(state.message, True, UI_ACCENT)
        window.blit(msg_img, (width - msg_img.get_width() - 12,
                              hud_top - PROMPT_LINE_HEIGHT + 6))

    # Sadaļu robežas: ~17% / 16% / 23% / 44% no loga platuma
    health_w = int(width * 0.17)
    coins_w = int(width * 0.16)
    lamp_w = int(width * 0.23)
    bounds = [(0, health_w),
              (health_w, health_w + coins_w),
              (health_w + coins_w, health_w + coins_w + lamp_w),
              (health_w + coins_w + lamp_w, width)]

    # Joslas fons — vienkrāsains tumšs ar minimāli noapaļotiem stūriem
    pygame.draw.rect(window, HUD_BG, (0, hud_top, width, HUD_HEIGHT),
                     border_radius=6)

    # Plāni vertikālie dalītāji starp sadaļām
    for x, _ in bounds[1:]:
        pygame.draw.line(window, HUD_DIVIDER,
                         (x, hud_top + 12), (x, hud_top + HUD_HEIGHT - 12), 1)

    _draw_hud_health(window, state, fonts, bounds[0], hud_top)
    _draw_hud_coins(window, state, fonts, sprites, bounds[1], hud_top)
    _draw_hud_lamp(window, state, fonts, bounds[2], hud_top)
    _draw_hud_exposure(window, state, fonts, bounds[3], hud_top)

    # Augšējā plānā josla (zīmējas pār pasaules augšu)
    draw_top_bar(window, state, fonts)

    # Misijas teksts līmeņa sākumā (~2 s, centrā pāri pasaulei)
    if state.mission_text_timer > 0 and state.level_number <= len(gs.MISSION_TEXTS):
        mission = gs.MISSION_TEXTS[state.level_number - 1]
        mission_img = fonts["font"].render(mission, True, UI_ACCENT)
        world_h = state.level.height * gs.TILE_SIZE
        mx = (width - mission_img.get_width()) // 2
        my = world_h // 3
        # Tumšs pamatnes aiz teksta, lai lasās arī gaišās vietās
        back = pygame.Surface((mission_img.get_width() + 24,
                               mission_img.get_height() + 12), pygame.SRCALPHA)
        back.fill((14, 16, 20, 200))
        window.blit(back, (mx - 12, my - 6))
        window.blit(mission_img, (mx, my))


def interaction_prompt(state: GameState) -> str:
    """Kuru E-darbības uzvedni rādīt HUD (tukša virkne = nekā)."""
    if state.hidden:
        return "E EXIT HIDEOUT"
    if state.package_in_range():
        return "E PICK UP PACKAGE"
    if state.hideout_in_range() is not None:
        return "E HIDE"
    # Pie izejas bez sūtījuma — atgādinām, ka misijas objekts vēl nav rokā
    if not state.level.package_taken:
        px, py = state.player_center()
        ex = state.level.exit_pos[0] * gs.TILE_SIZE + gs.TILE_SIZE / 2
        ey = state.level.exit_pos[1] * gs.TILE_SIZE + gs.TILE_SIZE / 2
        if math.hypot(px - ex, py - ey) < gs.TILE_SIZE:
            return "MISSION ITEM REQUIRED"
    return ""


# ============================================================
#  EKRĀNI (izvēlnes, pauze, beigu ekrāni)
#  Tumšs ogļu fons, krēmkrāsas teksts, viens dzeltens akcents,
#  plānas līnijas, monospace fonts. Izvēlētais variants =
#  dzeltens trijstūris pa kreisi + dzeltens teksts.
# ============================================================


def draw_panel(window: pygame.Surface, panel_width: int,
               panel_height: int) -> pygame.Rect:
    """Pārkares panelis ekrāna centrā. Aiz paneļa ekrāns aptumšots."""
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
    """Dzeltens kursora trijstūris (rāda pa labi).

    Zīmēts kā daudzstūris, nevis fonta simbols — konsolas fontā
    trijstūrim reizēm nav glifa un rādās kā kvadrāts.
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
    sesijā spēle ir sākta un pašlaik rit."""
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
    # RETRY restartē līmeni un atjauno punktus uz līmeņa sākuma stāvokli
    options.append("RETRY FOR BETTER RANK")
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
    """Līmeņu izvēle ar statusiem AVAILABLE / COMPLETED / LOCKED.
    Līmenis atbloķēts, ja iepriekšējais pabeigts šajā sesijā."""
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
            # Ja šajā sesijā pabeigts — rādam labāko vērtējumu
            if n in ui["best_ranks"]:
                status = f"COMPLETED  {ui['best_ranks'][n]}"
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
    """Segmentēts slīdnis 0-100 (soli pa 10).

    Izvēlētam slīdnim vērtību rāda kā "< 70 >" — mājiens, ka
    ar bultiņām var mainīt.
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
    """Iestatījumi: skaļuma slīdņi, FULLSCREEN checkbox, CONTROLS.
    Slīdņi pagaidām tikai glabā vērtību (audio sistēmas vēl nav)."""
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
    """LEVEL COMPLETE ekrāns: statistika, lielais vērtējuma burts + opcijas."""
    rect = draw_panel(window, 560, 520)
    cx = rect.centerx
    draw_panel_title(window, fonts, rect, "LEVEL COMPLETE")
    sub = fonts["small"].render(
        f"LEVEL {state.level_number:02d} — {LEVEL_NAMES[state.level_number - 1]}",
        True, UI_DIM)
    window.blit(sub, sub.get_rect(center=(cx, rect.top + 100)))

    # Lielais vērtējuma burts (S/A/B/C) paneļa labajā augšējā stūrī
    stats = state.level_stats or {}
    rank = stats.get("rank", "C")
    rank_img = fonts["big"].render(rank, True, UI_ACCENT)
    window.blit(rank_img, rank_img.get_rect(center=(rect.right - 70,
                                                    rect.top + 140)))

    # Statistika: kreisajā pusē nosaukums, labajā — vērtība
    rows = [
        ("PACKAGE DELIVERED", "YES"),
        ("COINS", f"{stats.get('coins', 0)}/{stats.get('coins_total', 0)}"),
        ("TIME", _format_time(stats.get("time", 0.0))),
        ("ALERTS", str(stats.get("alerts", 0))),
        ("SCORE", str(stats.get("score", state.score))),
    ]
    y = rect.top + 150
    for label, value in rows:
        label_img = fonts["font"].render(label, True, UI_DIM)
        value_img = fonts["font"].render(value, True, UI_TEXT)
        window.blit(label_img, (rect.left + 70, y))
        window.blit(value_img, (rect.right - 150 - value_img.get_width(), y))
        y += 38

    draw_menu_options(window, fonts["font"], level_complete_options(state),
                      ui["selection"], cx, rect.bottom - 140, line_height=42)


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
    draw_score_status(window, fonts, ui, cx, rect.top + 190)
    draw_menu_options(window, fonts["font"], CAUGHT_OPTIONS, ui["selection"],
                      cx, rect.top + 225, line_height=44)


def draw_won(window: pygame.Surface, fonts: dict, state: GameState,
             ui: dict) -> None:
    """Uzvaras ekrāns (visi līmeņi izieti): ALL MISSIONS COMPLETE."""
    rect = draw_panel(window, 560, 400)
    cx = rect.centerx
    draw_panel_title(window, fonts, rect, "ALL MISSIONS COMPLETE")
    score = fonts["font"].render(f"FINAL SCORE  {state.score}", True, UI_TEXT)
    window.blit(score, score.get_rect(center=(cx, rect.top + 130)))
    draw_score_status(window, fonts, ui, cx, rect.top + 160)
    draw_menu_options(window, fonts["font"], WON_OPTIONS, ui["selection"],
                      cx, rect.top + 205, line_height=44)


# Zaļā, ja rekords aizgāja uz serveri; pelēkā, ja nē
SCORE_SAVED_COLOR = (90, 200, 120)


def draw_score_status(window: pygame.Surface, fonts: dict, ui: dict,
                      cx: int, y: int) -> None:
    """Rāda vienu rindu par rekorda nosūtīšanu serverim (CAUGHT/WIN ekrāni).
    True -> "SCORE SAVED TO SERVER", False -> "SERVER NOT AVAILABLE"."""
    result = ui.get("score_result")
    if result is None:
        return
    if result:
        text, color = "SCORE SAVED TO SERVER", SCORE_SAVED_COLOR
    else:
        text, color = "SERVER NOT AVAILABLE", UI_DIM
    img = fonts["small"].render(text, True, color)
    window.blit(img, img.get_rect(center=(cx, y)))


# ============================================================
#  IEVADE — taustiņu apstrāde katram ekrānam
# ============================================================


def handle_key(key: int, current_screen: str, state: GameState,
               ui: dict) -> str:
    """Apstrādā vienu taustiņa nospiešanu un atgriež jauno ekrānu.
    ui["selection"] ir izvēlnes kursora pozīcija (to šeit arī maina)."""
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
                reset_score_flag(ui)  # jaunā spēle beigās sūtīs jaunu rekordu
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
            # Space = izslēgt tuvāko lampu (viena darbība)
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
            if options[sel] == "RETRY FOR BETTER RANK":
                # Restartē līmeni; punkti atgriežas uz līmeņa sākuma vērtību
                state.score = state.level_start_score
                state.load_level(state.level_number)
                state.status = STATUS_PLAYING
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
                reset_score_flag(ui)  # nākamā spēle beigās sūtīs jaunu rekordu
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
                reset_score_flag(ui)  # nākamā spēle beigās sūtīs jaunu rekordu
                ui["game_started"] = True
                ui["selection"] = 0
                return SCREEN_GAME
            ui["selection"] = 0
            return SCREEN_MENU
        elif key == pygame.K_ESCAPE:
            ui["selection"] = 0
            return SCREEN_MENU

    return current_screen


def remember_rank(ui: dict, state: GameState) -> None:
    """Saglabā labāko vērtējuma burtu līmenim sesijas atmiņā."""
    rank = state.level_stats.get("rank")
    if rank is None:
        return
    previous = ui["best_ranks"].get(state.level_number)
    if previous is None:
        ui["best_ranks"][state.level_number] = rank
    else:
        ui["best_ranks"][state.level_number] = better_rank(previous, rank)


PLAYER_NAME_FILE = "player_name.txt"  # šeit atceramies pēdējo vārdu


def ask_credentials() -> dict:
    """Pajautā vārdu un paroli konsolē PIRMS pygame.init().

    Apzināti vienkārši: spēle sākas no termināļa, tāpēc prasām turpat.
    - Ja konts nav — serveris to izveido; ja ir — pārbauda paroli.
    - Tukša parole = spēle bez konta (rekords netiks sūtīts).
    - Vārdu saglabājam player_name.txt, lai nākamreiz piedāvātu to pašu.
    Headless režīmā (testi) nejautājam neko — tur neviens nevar atbildēt.
    """
    player = {"name": "PLAYER", "password": "", "token": None, "completed": 0}
    if os.environ.get("SDL_VIDEODRIVER") == "dummy":
        return player
    # Pēdējais lietotais vārds — lai nākamreiz nav jāraksta no jauna
    saved_name = ""
    if os.path.exists(PLAYER_NAME_FILE):
        with open(PLAYER_NAME_FILE, encoding="utf-8") as f:
            saved_name = f.read().strip()
    try:
        while True:
            prompt = f"Tavs vārds [{saved_name}]: " if saved_name else "Tavs vārds: "
            name = input(prompt).strip() or saved_name or "PLAYER"
            password = input("Parole (tukšs = spēlēt bez konta): ").strip()
            if not password:
                print("Spēlē bez konta — rekords netiks saglabāts serverī.")
                player["name"] = name
                return player
            token, status = api_client.login_or_register(name, password)
            if status == "ok":
                print(f"Sveiki, {name}! Rekords tiks saglabāts serverī.")
                with open(PLAYER_NAME_FILE, "w", encoding="utf-8") as f:
                    f.write(name)
                player.update(name=name, password=password, token=token)
                return player
            if status == "no_server":
                print("Serveris nav pieejams — spēlē bez rekordu saglabāšanas.")
                player.update(name=name, password=password)
                return player
            print("Nepareiza parole šim vārdam (vai vārds jau aizņemts) — mēģini vēlreiz.")
    except EOFError:
        return player  # nav konsoles (piem., palaists no citas programmas)


def reset_score_flag(ui: dict) -> None:
    """Atiestata rekorda sūtīšanas karodziņu — nākamā spēle sūtīs no jauna."""
    ui["score_sent"] = False
    ui["score_result"] = None


def send_score_to_server(ui: dict, state: GameState, player: dict) -> None:
    """Nosūta rekordu serverim VIENU REIZI, kad spēle beigusies.

    Tokens parasti jau ir no spēles sākuma. Ja toreiz serveris bija
    izslēgts, šeit mēģinām vēlreiz — tāpēc spēle nesasalst palaišanas
    brīdī. api_client pats noķer visas kļūdas — spēle nekad nenokrīt.
    """
    if ui["score_sent"]:
        return
    ui["score_sent"] = True  # lai nesūta atkārtoti katrā kadrā
    token = player["token"]
    if token is None and player["password"]:
        # Serveris sākumā nebija pieejams — mēģinām vēlreiz tagad
        token, _ = api_client.login_or_register(player["name"],
                                                player["password"])
        player["token"] = token
    ui["score_result"] = token is not None and \
        api_client.send_score(token, state.score)


def save_progress_to_server(state: GameState, player: dict) -> None:
    """Pēc līmeņa pabeigšanas aizsūtām progresu serverim (ja ielogots).
    Tā nākamreiz ielogojoties līmeņi paliek atbloķēti."""
    if not player.get("token"):
        return  # bez konta progress nekur netiek sūtīts
    if state.level_number > player.get("completed", 0):
        player["completed"] = state.level_number
        api_client.save_progress(player["name"], player["token"],
                                 player["completed"])


def main() -> None:
    """Spēles galvenā funkcija: atver logu un griež spēles ciklu."""
    # Vārdu un paroli jautājam PIRMS pygame.init() — konsolē
    player = ask_credentials()

    pygame.init()
    pygame.display.set_caption("Shadow Courier")

    state = GameState()
    world_width = state.level.width * gs.TILE_SIZE
    world_height = state.level.height * gs.TILE_SIZE
    window = pygame.display.set_mode((world_width, world_height + HUD_HEIGHT))
    clock = pygame.time.Clock()
    # Ekrāniem — monospace fonts
    fonts = {
        "font": pygame.font.SysFont("consolas", 20),
        "big": pygame.font.SysFont("consolas", 44, bold=True),
        "small": pygame.font.SysFont("consolas", 16),
    }
    sprites = load_sprites()
    fonts["hud"] = load_hud_fonts()  # treknais Verdana apakšējai joslai

    # Klienta pusē glabājamie UI dati (spēles loģikai tie nav vajadzīgi)
    ui = {
        "selection": 0,            # izvēlnes kursora pozīcija
        "settings_from": SCREEN_MENU,  # no kurienes atnācām uz SETTINGS
        "volumes": {"MASTER VOLUME": 70, "MUSIC": 60, "SOUND EFFECTS": 60},
        "fullscreen": False,
        "game_started": False,     # vai šajā sesijā spēle jau sākta (CONTINUE)
        "completed_levels": set(), # šajā sesijā pabeigtie līmeņi (1, 2, 3)
        "best_ranks": {},          # labākais vērtējuma burts katram līmenim
        "score_sent": False,       # vai šīs spēles rekords jau nosūtīts serverim
        "score_result": None,      # True = saglabāts, False = serveris nepieejams
    }

    current_screen = SCREEN_MENU
    # Progress no servera: ja ielogojies, atbloķējam jau pabeigtos līmeņus
    if player.get("token"):
        server_completed = api_client.get_progress(player["name"],
                                                   player["token"])
        if server_completed:
            player["completed"] = server_completed
            ui["completed_levels"] = set(range(1, server_completed + 1))
    player_facing = (0, 1)  # kurp spēlētājs skatās (sākumā — uz leju)
    player_moving = False   # vai spēlētājs kustas (animācijai)

    while True:
        # dt = sekundes kopš iepriekšējā kadra (lai ātrums
        # nebūtu atkarīgs no datora ātruma)
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
                send_score_to_server(ui, state, player)
                current_screen = SCREEN_GAME_OVER
                ui["selection"] = 0
            elif state.status == STATUS_WON:
                ui["completed_levels"].add(state.level_number)
                remember_rank(ui, state)
                save_progress_to_server(state, player)
                send_score_to_server(ui, state, player)
                current_screen = SCREEN_WON
                ui["selection"] = 0
            elif state.status == STATUS_LEVEL_COMPLETE:
                ui["completed_levels"].add(state.level_number)
                remember_rank(ui, state)
                save_progress_to_server(state, player)
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
