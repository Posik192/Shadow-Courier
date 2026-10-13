"""Shadow Courier — pygame klients.

Šis fails TIKAI nolasa taustiņus un zīmē ekrānu.
Visa spēles loģika (noteikumi) ir mapē game/ — skaties game/game_state.py.

Palaišana:  python -m client.main
Vadība:     WASD/bultiņas — kustēties, Space — izslēgt lampu,
            E — paņemt atslēgu/atvērt durvis, P — pauze, Esc — izvēlne.
"""

import math
import os
import sys

import pygame

from game import settings as gs
from game.game_state import (GameState, STATUS_PLAYING, STATUS_GAME_OVER,
                             STATUS_WON, STATUS_LEVEL_COMPLETE)
from game.guard import GUARD_SIZE

# --- LOGA UZSTĀDĪJUMI ---
FPS = 60           # kadri sekundē
HUD_HEIGHT = 64    # apakšējā informācijas josla (pikseļi)
TOP_BAR_HEIGHT = 30  # augšējā plānā josla ar nosaukumu (zīmējas PĀRKLĀJ pasaulei)

# --- KRĀSAS (R, G, B) ---
COLOR_FLOOR = (34, 40, 52)      # grīda — tumši zilpelēka
COLOR_WALL = (90, 100, 120)     # sienas
COLOR_PLAYER = (80, 160, 255)   # kurjers — zils
COLOR_GUARD = (230, 70, 70)     # sargs — sarkans
COLOR_COIN = (250, 210, 60)     # monēta — dzeltena
COLOR_KEY = (255, 150, 40)      # atslēga — oranža
COLOR_DOOR = (140, 90, 50)      # durvis — brūnas
COLOR_EXIT = (60, 210, 110)     # izeja — zaļa
COLOR_LAMP_ON = (255, 240, 160) # lampa, kas deg
COLOR_LAMP_OFF = (80, 80, 90)   # izslēgta lampa
COLOR_TEXT = (230, 230, 235)    # teksts
COLOR_WARNING = (250, 80, 60)   # brīdinājums (gaismas taimeris)

# --- EKRĀNU (izvēļņu) TERMINĀĻA STILS ---
COLOR_PANEL_BG = (13, 21, 32)      # paneļa fons — tumši zils
COLOR_PANEL_EDGE = (22, 32, 46)    # gaišāka malas josla panelim
COLOR_ACCENT = (242, 182, 74)      # dzeltens akcents (kursors, kontūras)
COLOR_OK = (90, 200, 120)          # zaļš — izeja / līmenis izpildīts
COLOR_BAD = (230, 80, 70)          # sarkans — noķerts
COLOR_DIM = (120, 130, 145)        # pelēks — palīgteiksti
PANEL_WIDTH = 520                  # izvēlnes "kartītes" platums (pikseļi)
PANEL_BORDER = 3                   # paneļa dzeltenās kontūras biezums

# --- APGAISMOJUMA UZSTĀDĪJUMI ---
DARKNESS_ALPHA = 175        # cik tumša ir noliktava ārpus gaismas (0–255)
GLOW_COLOR = (255, 200, 90) # lampu un lukturu siltā dzeltenā krāsa
GUARD_LIGHT_RADIUS = 150    # cik tālu sniedzas sarga lukturis (pikseļi)
GUARD_CONE_ANGLE = 32       # luktura konusa puse leņķī (grādi)
VIGNETTE_ALPHA = 130        # cik tumšas ir ekrāna malas (0–255)

# Ekrānu nosaukumi (kā "lapas" programmā)
SCREEN_MENU = "menu"
SCREEN_GAME = "game"
SCREEN_PAUSED = "paused"
SCREEN_GAME_OVER = "game_over"
SCREEN_WON = "won"
SCREEN_LEVEL_COMPLETE = "level_complete"

# Izvēļņu opcijas (termināļa stilā: ▶ kursors, bultiņas + Enter)
MENU_OPTIONS = ["NEW GAME", "QUIT"]
PAUSED_OPTIONS = ["RESUME", "RESTART LEVEL", "MAIN MENU"]
CONTROLS_HELP = "WASD Move | SPACE Disable lamp | E Interact"


# Cik lielus sprites zīmēt spēlē (pikseļi)
SPRITE_SIZES = {
    "floor": gs.TILE_SIZE, "wall": gs.TILE_SIZE,
    "door": gs.TILE_SIZE, "exit": gs.TILE_SIZE,
    "lamp_on": gs.TILE_SIZE, "lamp_off": gs.TILE_SIZE,
    "player": gs.PLAYER_SIZE, "guard": GUARD_SIZE,
    "coin": 26, "key": 30,
    # Dekoratīvie šķēršļi (kastes un mucas kartēs apzīmētas ar 'x')
    "prop_crate_big": gs.TILE_SIZE, "prop_crate_mid": gs.TILE_SIZE,
    "prop_crate_small": gs.TILE_SIZE, "prop_barrel": gs.TILE_SIZE,
}

# Kastes/mucas, no kurām izvēlas dekoratīvos šķēršļus kartēs ('x')
PROP_SPRITES = ["prop_crate_big", "prop_crate_mid",
                "prop_crate_small", "prop_barrel"]

# HUD ikonu izmērs (sirdis, monēta, atslēga apakšējā joslā)
HUD_ICON_SIZE = 24

# --- KUSTĪBAS ANIMĀCIJAS ---
FRAME_SWITCH_MS = 120  # ik pēc tik milisekundēm mainās soļa kadrs
SWAY_DEGREES = 4       # par cik grādiem spēlētājs "šūpojas", ejot


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
    # Cits aģents tās gatavo — tāpēc šeit viss ir "mīksts":
    #   * ja left/right nav, ņemam pretējā virziena spoguļattēlu;
    #   * ja vispār nav nevienas virzienu bildes, vārdnīcā ir None
    #     un draw_world lieto veco variantu (kadri + rotācija).
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
        # ar to, kas ir (prioritāte: down -> up -> left -> right)
        existing = [directions[d] for d in ("down", "up", "left", "right")
                    if directions[d] is not None]
        if existing:
            for direction in directions:
                if directions[direction] is None:
                    directions[direction] = existing[0]
            sprites[name + "_dir"] = directions
        else:
            sprites[name + "_dir"] = None

    # Dedzinošā lampa: ja ir jaunā rūpnieciskā lampa (lamp_on.png), lieto to
    # visām lampām; citādi — vecie varianti lamp_1..4.png pa vietām
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
            # Tumšā versija: krāsas reizina ar pelēku — ikona paliek, bet "nodziest"
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
    """Uzzīmē bildi vietā (x, y). Ja bildes nav — zīmē kvadrātu.

    angle — par cik grādiem pagriezt (0 = skatās uz leju, kā uzzīmēts).
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
#     mīkstus gradientus (aplis lampai, konuss sarga lukturim).
#  2. Katrā kadrā pār pasaules uzklājam puscaurspīdīgu melnu "tumsas"
#     slāni un ar BLEND_RGBA_SUB no tā "izgriežam" gaišas peles tur,
#     kur deg lampas un spīd lukturi.
#  3. Beigās pievienojam siltu dzeltenu mirdzumu (BLEND_RGB_ADD) un
#     vinjetti (tumšākas ekrāna malas) — noliktava izskatās tumša,
#     bet apgaismotās vietas silktas un lasāmas.
# ============================================================

# Kešatmiņa gatavajiem gradientiem: gradientu rēķina VIENREIZ (tas ir
# "dārgi" — daudz pikseļu), katrā kadrā tikai zīmē (blit) un griež (rotate).
_light_cache: dict = {}


def _build_radial_pixels(radius: int, alpha_func) -> pygame.Surface:
    """Uzzīmē kvadrātveida Surface (2*radius), kura pikseļu alpha
    nosaka funkcija alpha_func(distance, angle) -> 0..255.

    distance — attālums no centra (0..radius), angle — leņķis radianos
    (0 = pa labi). Centrā parasti alpha=255, uz malām 0 — mīksta pāreja.
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


def get_light_circle(radius: int) -> pygame.Surface:
    """Lampas gaismas pele: centrā caurspīdīga, uz malām melna ar alpha.

    Šo sprite zīmē uz tumsas slāņa ar BLEND_RGBA_SUB — kur sprite alpha
    ir liela, tur tumsa "izgriežas" (paliek gaiši), malās pāreja ir mīksta.
    """
    key = ("circle", radius)
    if key not in _light_cache:
        def fade(distance, angle):
            if distance >= radius:
                return 0
            t = 1.0 - distance / radius
            return 255 * t * t  # kvadrātiska pāreja = mīkstākas malas
        _light_cache[key] = _build_radial_pixels(radius, fade)
    return _light_cache[key]


def get_glow_circle(radius: int) -> pygame.Surface:
    """Silta dzeltena mirdzuma pele (krāsains gradients).

    Zīmē uz pasaules ar BLEND_RGB_ADD — pikseļi paliek gaišāki un
    dzeltenīgāki, it kā lampa sildītu grīdu ap sevi.
    """
    key = ("glow", radius)
    if key not in _light_cache:
        base = get_light_circle(radius)  # alpha gradients (melna krāsā)
        glow = base.copy()
        # Aizkrāso melno RGB ar siltu dzelteno, alpha paliek tā pati
        glow.fill(GLOW_COLOR, special_flags=pygame.BLEND_RGB_MULT)
        _light_cache[key] = glow
    return _light_cache[key]


def get_light_cone(radius: int) -> pygame.Surface:
    """Sarga luktura konuss: trīsstūrveida gradients, kas rāda pa labi.

    Virsotne (gaišākā vieta) ir sprite centrā, konuss atveras pa labi.
    Vēlāk to pagriež ar pygame.transform.rotate pēc sarga virziena.
    """
    key = ("cone", radius)
    if key not in _light_cache:
        half = math.radians(GUARD_CONE_ANGLE)

        def fade(distance, angle):
            if distance >= radius or abs(angle) > half:
                return 0
            along = 1.0 - distance / radius      # mazāk gaismas tālāk
            side = 1.0 - abs(angle) / half       # mazāk gaismas pie malām
            return 255 * along * along * (0.35 + 0.65 * side)
        _light_cache[key] = _build_radial_pixels(radius, fade)
    return _light_cache[key]


def get_rotated_cone(direction: tuple[int, int], colored: bool) -> pygame.Surface:
    """Atgriež luktura konusu, pagrieztu konkrētā virzienā (kešots).

    direction — (dx, dy), piem., (1, 0) = pa labi, (0, 1) = uz leju.
    colored=False — melna/alpha versija tumsas izgriešanai (SUB),
    colored=True  — silti dzeltena versija mirdzumam (ADD).
    """
    dx, dy = direction
    key = ("cone_rot", dx, dy, colored)
    if key not in _light_cache:
        cone = get_light_cone(GUARD_LIGHT_RADIUS)
        if colored:
            # Mirdzums ir vājāks nekā izgriezums — samazinām alpha uz pusi
            cone = cone.copy()
            cone.fill((255, 255, 255, 110), special_flags=pygame.BLEND_RGBA_MULT)
            cone.fill(GLOW_COLOR, special_flags=pygame.BLEND_RGB_MULT)
        # Konuss zīmēts pa labi; pygame.rotate griež pretēji pulkstenim
        # matemātiskajā nozīmē, tāpēc ekrānā (y uz leju) formula ir šāda:
        angle = -math.degrees(math.atan2(dy, dx))
        _light_cache[key] = pygame.transform.rotate(cone, angle)
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
    """Uzzīmē tumsu, lampu peles, sargu lukturus un vinjetti.

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

    # 3. solis: sargu lukturu konusi (pagriezti kustības virzienā)
    for guard in state.level.guards:
        if guard.horizontal:
            guard_dir = (guard.direction, 0)
        else:
            guard_dir = (0, guard.direction)
        cone = get_rotated_cone(guard_dir, colored=False)
        center = (guard.x + GUARD_SIZE / 2, guard.y + GUARD_SIZE / 2)
        darkness.blit(cone, cone.get_rect(center=center),
                      special_flags=pygame.BLEND_RGBA_SUB)

    # 4. solis: uzklāj tumsu ar izgrieztajām gaismas vietām
    window.blit(darkness, (0, 0))

    # 5. solis: silts dzeltens mirdzums gaismas vietās (aditīvi — gaišāk)
    glow = get_glow_circle(gs.LIGHT_RADIUS)
    for (col, row), off_timer in state.level.lamps.items():
        if off_timer <= 0:
            center = (col * t + t // 2, row * t + t // 2)
            window.blit(glow, glow.get_rect(center=center),
                        special_flags=pygame.BLEND_RGB_ADD)
    for guard in state.level.guards:
        if guard.horizontal:
            guard_dir = (guard.direction, 0)
        else:
            guard_dir = (0, guard.direction)
        cone_glow = get_rotated_cone(guard_dir, colored=True)
        center = (guard.x + GUARD_SIZE / 2, guard.y + GUARD_SIZE / 2)
        window.blit(cone_glow, cone_glow.get_rect(center=center),
                    special_flags=pygame.BLEND_RGB_ADD)

    # 6. solis: vinjette — ekrāna malas nedaudz tumšākas
    window.blit(get_vignette(world_w, world_h), (0, 0))


def draw_top_bar(window: pygame.Surface, state: GameState,
                 font: pygame.font.Font) -> None:
    """Plānā augšējā josla: nosaukums, līmenis, punkti (pārklāj pasaulei)."""
    bar = pygame.Surface((window.get_width(), TOP_BAR_HEIGHT), pygame.SRCALPHA)
    bar.fill((10, 12, 18, 200))  # gandrīz melna, nedaudz caurspīdīga
    window.blit(bar, (0, 0))
    text = f"SHADOW COURIER   |   LĪMENIS {state.level_number}   |   PUNKTI {state.score}"
    img = font.render(text, True, COLOR_TEXT)
    window.blit(img, img.get_rect(center=(window.get_width() // 2,
                                          TOP_BAR_HEIGHT // 2)))


def main() -> None:
    """Spēles galvenā funkcija: atver logu un griež spēles ciklu."""
    pygame.init()
    pygame.display.set_caption("Shadow Courier")

    state = GameState()
    world_width = state.level.width * gs.TILE_SIZE
    world_height = state.level.height * gs.TILE_SIZE
    window = pygame.display.set_mode((world_width, world_height + HUD_HEIGHT))
    clock = pygame.time.Clock()
    # Termināļa stila ekrāniem — monospace fonts
    font = pygame.font.SysFont("consolas", 24)
    big_font = pygame.font.SysFont("consolas", 48, bold=True)
    small_font = pygame.font.SysFont("consolas", 18)
    sprites = load_sprites()
    fonts = {"font": font, "big": big_font, "small": small_font}

    current_screen = SCREEN_MENU
    player_facing = (0, 1)  # kurp spēlētājs skatās (sākumā — uz leju)
    player_moving = False   # vai spēlētājs kustas (animācijai)
    selection = 0           # izvēllnes ▶ kursora pozīcija (0 = pirmā opcija)

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
                current_screen, selection = handle_key(
                    event.key, current_screen, selection, state)

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
            # Space un E apstrādājam šeit, lai viens nospiešanas = viena darbība
            state.update(dt, move_x, move_y, False, False)
            if state.status == STATUS_GAME_OVER:
                current_screen = SCREEN_GAME_OVER
            elif state.status == STATUS_WON:
                current_screen = SCREEN_WON
            elif state.status == STATUS_LEVEL_COMPLETE:
                current_screen = SCREEN_LEVEL_COMPLETE
                selection = 0
        else:
            # Pauzē/izvēlnē spēlētājs nekustas — animācija apstājas
            player_moving = False

        # --- 3. solis: zīmēšana ---
        window.fill(COLOR_PANEL_BG)
        if current_screen == SCREEN_MENU:
            draw_menu(window, fonts, selection)
        else:
            draw_world(window, state, sprites, player_facing, player_moving)
            draw_hud(window, state, font, sprites)
            if current_screen == SCREEN_PAUSED:
                draw_paused(window, fonts, selection)
            elif current_screen == SCREEN_LEVEL_COMPLETE:
                draw_level_complete(window, fonts, state)
            elif current_screen == SCREEN_GAME_OVER:
                draw_game_over(window, fonts, state)
            elif current_screen == SCREEN_WON:
                draw_won(window, fonts, state)

        pygame.display.flip()


def handle_key(key: int, current_screen: str, selection: int,
               state: GameState) -> tuple[str, int]:
    """Apstrādā vienu taustiņa nospiešanu.

    Atgriež (jaunais_ekrāns, jaunā_kursora_pozīcija).
    Bultiņas augša/leja kustina ▶ kursoru, Enter izvēlas opciju.
    """
    if current_screen == SCREEN_MENU:
        if key in (pygame.K_UP, pygame.K_w):
            selection = (selection - 1) % len(MENU_OPTIONS)
        elif key in (pygame.K_DOWN, pygame.K_s):
            selection = (selection + 1) % len(MENU_OPTIONS)
        elif key == pygame.K_RETURN:
            if MENU_OPTIONS[selection] == "QUIT":
                pygame.quit()
                sys.exit()
            state.__init__()   # jauna spēle no 1. līmeņa
            return SCREEN_GAME, 0
        elif key in (pygame.K_ESCAPE, pygame.K_q):
            pygame.quit()
            sys.exit()
    elif current_screen == SCREEN_GAME:
        if key == pygame.K_p:
            return SCREEN_PAUSED, 0
        if key == pygame.K_ESCAPE:
            return SCREEN_MENU, 0
        if key == pygame.K_SPACE:
            # Space = 2. mehānika: izslēgt tuvāko lampu (viena darbība)
            state.update(0.0, 0, 0, True, False)
        if key == pygame.K_e:
            # E = paņemt atslēgu / atvērt durvis (viena darbība)
            state.update(0.0, 0, 0, False, True)
    elif current_screen == SCREEN_PAUSED:
        if key in (pygame.K_UP, pygame.K_w):
            selection = (selection - 1) % len(PAUSED_OPTIONS)
        elif key in (pygame.K_DOWN, pygame.K_s):
            selection = (selection + 1) % len(PAUSED_OPTIONS)
        elif key in (pygame.K_RETURN, pygame.K_p):
            if key == pygame.K_p:  # P = ātrais ceļš uz RESUME
                return SCREEN_GAME, 0
            option = PAUSED_OPTIONS[selection]
            if option == "RESUME":
                return SCREEN_GAME, 0
            if option == "RESTART LEVEL":
                state.load_level(state.level_number)
                state.status = STATUS_PLAYING
                return SCREEN_GAME, 0
            # MAIN MENU: atiestata spēli, lai nākamā NEW GAME būtu tīra
            state.__init__()
            return SCREEN_MENU, 0
        elif key == pygame.K_ESCAPE:
            state.__init__()
            return SCREEN_MENU, 0
    elif current_screen == SCREEN_LEVEL_COMPLETE:
        if key == pygame.K_RETURN:
            # Enter = ielādēt nākamo līmeni
            state.next_level()
            return SCREEN_GAME, 0
    elif current_screen in (SCREEN_GAME_OVER, SCREEN_WON):
        if key == pygame.K_r:
            # R = sākt jaunu spēli no 1. līmeņa
            state.__init__()
            return SCREEN_GAME, 0
        if key == pygame.K_ESCAPE:
            state.__init__()
            return SCREEN_MENU, 0
    return current_screen, selection


# --- ZĪMĒŠANAS FUNKCIJAS (katra zīmē vienu lietu) ---


# Virziens (x, y) -> rotācijas leņķis bildēm (sprites zīmēti "skatās uz leju")
FACING_ANGLES = {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}

# Virziens (x, y) -> virzienu sprites vārdnīcas atslēga
FACING_NAMES = {(0, 1): "down", (0, -1): "up", (1, 0): "right", (-1, 0): "left"}


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

    # Lampas (deg = gaiša, izslēgta = tumša; katrā vietā cits lampu variants)
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

    # Sargi (pagriežas kustības virzienā; sargs vienmēr patrulē,
    # tāpēc šūpošanās un kadru animācija rit pastāvīgi)
    for guard in level.guards:
        if guard.horizontal:
            guard_dir = (guard.direction, 0)
        else:
            guard_dir = (0, guard.direction)
        # Nobīde no sarga pozīcijas, lai visi sargi neietu sinhroni
        offset = (int(guard.x) + int(guard.y)) // 10
        sprite, angle = _pick_character_sprite(
            sprites, "guard", guard_dir, now, offset, moving=True)
        sway = SWAY_DEGREES * math.sin(now * 0.02 + offset)
        draw_sprite(window, sprite, guard.x, guard.y, GUARD_SIZE,
                    COLOR_GUARD, angle + sway)

    # Spēlētājs (kurjers, pagriežas kustības virzienā)
    if player_moving:
        # Soļu šūpošanās: sprite viegli griežas pa labi/kreisi (sinusa vilnis)
        sway = SWAY_DEGREES * math.sin(now * 0.02)
    else:
        sway = 0.0
    sprite, angle = _pick_character_sprite(
        sprites, "player", player_facing, now, 0, player_moving)
    draw_sprite(window, sprite, state.player_x, state.player_y,
                gs.PLAYER_SIZE, COLOR_PLAYER, angle + sway)

    # Tumsa + gaismas PĒC visa cita — tā "nosedz" pasauli,
    # izņemot vietas, kur deg lampas un spīd sargu lukturi
    draw_lighting(window, state)


def _draw_hud_icon(window: pygame.Surface, sprite: pygame.Surface | None,
                   x: int, y: int, fallback_color: tuple) -> None:
    """Uzzīmē vienu HUD ikonu; ja bildes nav — zīmē mazu kvadrātu."""
    if sprite is None:
        pygame.draw.rect(window, fallback_color,
                         (x, y, HUD_ICON_SIZE, HUD_ICON_SIZE))
    else:
        window.blit(sprite, (x, y))


def draw_hud(window: pygame.Surface, state: GameState,
             font: pygame.font.Font, sprites: dict) -> None:
    """Uzzīmē HUD: augšējo plāno joslu un apakšējo informācijas joslu.

    Apakšējā joslā (melna, HUD_HEIGHT px): sirdis (dzīvības), monētas
    "X / Y", atslēgas ikona, lampas slēdža uzlādes josla, punkti/līmenis,
    paziņojumi un gaismas brīdinājums.
    """
    width = window.get_width()
    hud_top = state.level.height * gs.TILE_SIZE
    row1_y = hud_top + 6    # 1. rinda: ikonas
    row2_y = hud_top + 38   # 2. rinda: teksti un joslas

    # Joslas fons — gandrīz melns, ar plānu gaišu līniju virsotnē
    pygame.draw.rect(window, (12, 14, 20), (0, hud_top, width, HUD_HEIGHT))
    pygame.draw.line(window, (60, 65, 80), (0, hud_top), (width, hud_top))

    x = 12

    # --- Sirdis (dzīvības): pilnas sarkanas, zaudētās — tumšas ---
    for i in range(gs.START_LIVES):
        if i < state.lives:
            heart = sprites.get("ui_heart")
        else:
            heart = sprites.get("ui_heart_dark")
        _draw_hud_icon(window, heart, x, row1_y, COLOR_WARNING)
        x += HUD_ICON_SIZE + 6
    x += 10

    # --- Monētas: "X / Y" (paņemtās / visas šajā līmenī) ---
    _draw_hud_icon(window, sprites.get("ui_coin"), x, row1_y, COLOR_COIN)
    x += HUD_ICON_SIZE + 4
    total_coins = state.coins_collected + len(state.level.coins)
    coin_img = font.render(f"{state.coins_collected} / {total_coins}",
                           True, COLOR_COIN)
    window.blit(coin_img, (x, row1_y + 2))
    x += coin_img.get_width() + 16

    # --- Atslēga: gaiša, ja paņemta; tumša, ja nav ---
    key_icon = sprites.get("ui_key") if state.has_key \
        else sprites.get("ui_key_dark")
    _draw_hud_icon(window, key_icon, x, row1_y, COLOR_KEY)
    x += HUD_ICON_SIZE + 4
    window.blit(font.render("ir" if state.has_key else "nav", True,
                            COLOR_KEY if state.has_key else (110, 110, 120)),
                (x, row1_y + 2))

    # --- 2. rinda: lampas slēdža uzlādes josla ---
    x2 = 12
    window.blit(font.render("Slēdzis:", True, COLOR_TEXT), (x2, row2_y - 4))
    x2 += font.size("Slēdzis:")[0] + 8
    bar_w, bar_h = 120, 12
    pygame.draw.rect(window, (50, 50, 60), (x2, row2_y, bar_w, bar_h))
    if state.lamp_cooldown > 0:
        # Josla piepildās, kamēr slēdzis uzlādējas
        part = 1.0 - state.lamp_cooldown / gs.LAMP_COOLDOWN
    else:
        part = 1.0  # pilna = gatavs lietošanai
    pygame.draw.rect(window, COLOR_COIN,
                     (x2, row2_y, int(bar_w * part), bar_h))
    if part >= 1.0:
        window.blit(font.render("gatavs", True, COLOR_COIN),
                    (x2 + bar_w + 8, row2_y - 4))

    # --- 2. rinda: gaismas brīdinājums (sarkana josla + teksts) ---
    warn_x = x2 + bar_w + 80
    if state.light_timer > 0:
        part = min(1.0, state.light_timer / gs.LIGHT_TIME_LIMIT)
        pygame.draw.rect(window, COLOR_WARNING,
                         (warn_x, row2_y, int(120 * part), bar_h))
        window.blit(font.render("GAISMA!", True, COLOR_WARNING),
                    (warn_x + 128, row2_y - 4))

    # --- 2. rinda: punkti un līmenis labajā pusē ---
    info = f"Līmenis: {state.level_number}   Punkti: {state.score}"
    info_img = font.render(info, True, COLOR_TEXT)
    window.blit(info_img, (width - info_img.get_width() - 12, row2_y - 4))

    # --- Paziņojums (piem., "Vajag atslēgu!") — joslas labajā augšā ---
    if state.message:
        msg_img = font.render(state.message, True, COLOR_COIN)
        window.blit(msg_img, (width - msg_img.get_width() - 12, row1_y))

    # Augšējā plānā josla ar nosaukumu (zīmējas pār pasaules augšu)
    draw_top_bar(window, state, font)


# --- TERMINĀĻA STILA EKRĀNI (izvēlnes, pauze, beigu ekrāni) ---
#
# Visi ekrāni zīmē "kartīti" ekrāna centrā: tumši zils panelis ar
# dzeltenu kontūru, monospace fonts, izvēlnes ar ▶ kursoru.


def draw_panel(window: pygame.Surface, panel_height: int) -> pygame.Rect:
    """Uzzīmē tumšo paneļa "kartīti" ekrāna centrā un atgriež tās Rect.

    Kartīte: tumši zils fons, gaišāka iekšējā mala un dzeltena kontūra.
    """
    width, height = window.get_size()
    rect = pygame.Rect(0, 0, PANEL_WIDTH, panel_height)
    rect.center = (width // 2, height // 2)
    # Nedaudz caurspīdīgs tumšs fons pār visu ekrānu (pasaule aiz paneļa)
    shade = pygame.Surface((width, height), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 140))
    window.blit(shade, (0, 0))
    # Kartīte: fons + iekšējā mala + dzeltenā kontūra
    pygame.draw.rect(window, COLOR_PANEL_BG, rect)
    inner = rect.inflate(-12, -12)
    pygame.draw.rect(window, COLOR_PANEL_EDGE, inner, 2)
    pygame.draw.rect(window, COLOR_ACCENT, rect, PANEL_BORDER)
    return rect


def draw_cursor_triangle(window: pygame.Surface, x: int, y_center: int,
                         size: int = 14) -> None:
    """Uzzīmē dzeltenu ▶ kursora trīsstūri (rāda pa labi).

    Zīmējam kā daudzstūri, nevis fonta simbolu — konsolas fontā
    '▶' burtam Windows reizēm nav glifi un tas rādās kā kvadrāts.
    """
    half = size // 2
    pygame.draw.polygon(window, COLOR_ACCENT,
                        [(x, y_center - half), (x, y_center + half),
                         (x + size, y_center)])


def draw_menu_options(window: pygame.Surface, font: pygame.font.Font,
                      options: list[str], selection: int,
                      cx: int, y: int, line_height: int = 40) -> int:
    """Uzzīmē izvēlnes opcijas ar ▶ kursoru. Atgriež y zem izvēlnes."""
    for i, option in enumerate(options):
        if i == selection:
            # Izvēlētā opcija: dzeltena ar kursoru
            text = font.render(option, True, COLOR_ACCENT)
            draw_cursor_triangle(window, cx - text.get_width() // 2 - 36,
                                 y + i * line_height + text.get_height() // 2)
        else:
            text = font.render(option, True, COLOR_TEXT)
        window.blit(text, text.get_rect(center=(cx, y + i * line_height
                                                + text.get_height() // 2)))
    return y + len(options) * line_height


def draw_menu(window: pygame.Surface, fonts: dict, selection: int) -> None:
    """Galvenā izvēlne: virsraksts + NEW GAME / QUIT + vadības palīgs."""
    rect = draw_panel(window, 360)
    cx = rect.centerx
    title = fonts["big"].render("SHADOW COURIER", True, COLOR_TEXT)
    window.blit(title, title.get_rect(center=(cx, rect.top + 56)))
    # Dzeltens svītrojums zem virsraksta
    pygame.draw.line(window, COLOR_ACCENT,
                     (rect.left + 40, rect.top + 92),
                     (rect.right - 40, rect.top + 92), 2)
    y = draw_menu_options(window, fonts["font"], MENU_OPTIONS, selection,
                          cx, rect.top + 130)
    help_img = fonts["small"].render(CONTROLS_HELP, True, COLOR_DIM)
    window.blit(help_img, help_img.get_rect(center=(cx, rect.bottom - 36)))


def draw_paused(window: pygame.Surface, fonts: dict, selection: int) -> None:
    """Pauzes ekrāns: RESUME / RESTART LEVEL / MAIN MENU."""
    rect = draw_panel(window, 340)
    cx = rect.centerx
    title = fonts["big"].render("PAUSED", True, COLOR_TEXT)
    window.blit(title, title.get_rect(center=(cx, rect.top + 56)))
    pygame.draw.line(window, COLOR_ACCENT,
                     (rect.left + 40, rect.top + 92),
                     (rect.right - 40, rect.top + 92), 2)
    draw_menu_options(window, fonts["font"], PAUSED_OPTIONS, selection,
                      cx, rect.top + 130)


def _format_time(seconds: float) -> str:
    """Sekundes -> 'mm:ss' teksts LEVEL COMPLETE statistikai."""
    minutes = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{minutes:02d}:{secs:02d}"


def draw_level_complete(window: pygame.Surface, fonts: dict,
                        state: GameState) -> None:
    """LEVEL COMPLETE ekrāns: statistika (monētas, laiks, punkti) + Enter."""
    rect = draw_panel(window, 380)
    cx = rect.centerx
    title = fonts["big"].render("LĪMENIS IZPILDĪTS", True, COLOR_OK)
    window.blit(title, title.get_rect(center=(cx, rect.top + 52)))
    sub = fonts["font"].render(f"LEVEL {state.level_number}", True, COLOR_DIM)
    window.blit(sub, sub.get_rect(center=(cx, rect.top + 96)))
    pygame.draw.line(window, COLOR_ACCENT,
                     (rect.left + 40, rect.top + 124),
                     (rect.right - 40, rect.top + 124), 2)

    # Statistika: kreisajā pusē nosaukums, labajā — vērtība
    stats = state.level_stats or {}
    rows = [
        ("MONĒTAS", f"{stats.get('coins', 0)} / {stats.get('coins_total', 0)}"),
        ("LAIKS", _format_time(stats.get("time", 0.0))),
        ("PUNKTI", str(stats.get("score", state.score))),
    ]
    y = rect.top + 158
    for label, value in rows:
        label_img = fonts["font"].render(label, True, COLOR_DIM)
        value_img = fonts["font"].render(value, True, COLOR_TEXT)
        window.blit(label_img, (rect.left + 60, y))
        window.blit(value_img, (rect.right - 60 - value_img.get_width(), y))
        y += 40

    hint = fonts["font"].render("ENTER — NEXT LEVEL", True, COLOR_ACCENT)
    window.blit(hint, hint.get_rect(center=(cx, rect.bottom - 44)))
    draw_cursor_triangle(window, cx - hint.get_width() // 2 - 30,
                         rect.bottom - 44)


def draw_game_over(window: pygame.Surface, fonts: dict,
                   state: GameState) -> None:
    """GAME OVER ekrāns: NOĶERTS (sarkans) + iemesls + opcijas."""
    rect = draw_panel(window, 340)
    cx = rect.centerx
    title = fonts["big"].render("NOĶERTS", True, COLOR_BAD)
    window.blit(title, title.get_rect(center=(cx, rect.top + 56)))
    pygame.draw.line(window, COLOR_ACCENT,
                     (rect.left + 40, rect.top + 92),
                     (rect.right - 40, rect.top + 92), 2)
    reason = fonts["font"].render(state.game_over_reason, True, COLOR_TEXT)
    window.blit(reason, reason.get_rect(center=(cx, rect.top + 140)))
    score = fonts["font"].render(f"PUNKTI  {state.score}", True, COLOR_DIM)
    window.blit(score, score.get_rect(center=(cx, rect.top + 184)))
    hint = fonts["font"].render("R — TRY AGAIN    ESC — MAIN MENU",
                                True, COLOR_ACCENT)
    window.blit(hint, hint.get_rect(center=(cx, rect.bottom - 44)))
    draw_cursor_triangle(window, cx - hint.get_width() // 2 - 30,
                         rect.bottom - 44)


def draw_won(window: pygame.Surface, fonts: dict, state: GameState) -> None:
    """Uzvaras ekrāns (pēdējais līmenis izietas): UZVARA! + punkti."""
    rect = draw_panel(window, 320)
    cx = rect.centerx
    title = fonts["big"].render("UZVARA!", True, COLOR_OK)
    window.blit(title, title.get_rect(center=(cx, rect.top + 56)))
    pygame.draw.line(window, COLOR_ACCENT,
                     (rect.left + 40, rect.top + 92),
                     (rect.right - 40, rect.top + 92), 2)
    score = fonts["font"].render(f"PUNKTI  {state.score}", True, COLOR_TEXT)
    window.blit(score, score.get_rect(center=(cx, rect.top + 140)))
    hint = fonts["font"].render("R — TRY AGAIN    ESC — MAIN MENU",
                                True, COLOR_ACCENT)
    window.blit(hint, hint.get_rect(center=(cx, rect.bottom - 44)))
    draw_cursor_triangle(window, cx - hint.get_width() // 2 - 30,
                         rect.bottom - 44)


if __name__ == "__main__":
    main()
