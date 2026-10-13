"""Shadow Courier — pygame klients.

Šis fails TIKAI nolasa taustiņus un zīmē ekrānu.
Visa spēles loģika (noteikumi) ir mapē game/ — skaties game/game_state.py.

Palaišana:  python -m client.main
Vadība:     WASD/bultiņas — kustēties, Space — izslēgt lampu,
            E — paņemt atslēgu/atvērt durvis, P — pauze, Esc — izvēlne.
"""

import os
import sys

import pygame

from game import settings as gs
from game.game_state import GameState, STATUS_PLAYING, STATUS_GAME_OVER, STATUS_WON
from game.guard import GUARD_SIZE

# --- LOGA UZSTĀDĪJUMI ---
FPS = 60           # kadri sekundē
HUD_HEIGHT = 64    # augšējā josla punktiem un paziņojumiem (pikseļi)

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
COLOR_LIGHT = (255, 245, 170)   # gaismas laukums (caurspīdīgs)
COLOR_TEXT = (230, 230, 235)    # teksts
COLOR_WARNING = (250, 80, 60)   # brīdinājums (gaismas taimeris)

# Ekrānu nosaukumi (kā "lapas" programmā)
SCREEN_MENU = "menu"
SCREEN_GAME = "game"
SCREEN_PAUSED = "paused"
SCREEN_GAME_OVER = "game_over"
SCREEN_WON = "won"


# Cik lielus sprites zīmēt spēlē (pikseļi)
SPRITE_SIZES = {
    "floor": gs.TILE_SIZE, "wall": gs.TILE_SIZE,
    "door": gs.TILE_SIZE, "exit": gs.TILE_SIZE,
    "lamp_on": gs.TILE_SIZE, "lamp_off": gs.TILE_SIZE,
    "player": gs.PLAYER_SIZE, "guard": GUARD_SIZE,
    "coin": 26, "key": 30,
}


def load_sprites() -> dict[str, pygame.Surface | None]:
    """Ielādē tekstūras no assets/ mapes un samazina līdz spēles izmēram.

    Ja kādas bildes nav (piem., aizmirsa palaist cut_assets.py),
    spēle nestrādā ar kļūdu — tā vietā zīmē parastos kvadrātus.
    """
    sprites = {}
    for name, size in SPRITE_SIZES.items():
        path = os.path.join("assets", name + ".png")
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            sprites[name] = pygame.transform.smoothscale(img, (size, size))
        else:
            sprites[name] = None
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


def main() -> None:
    """Spēles galvenā funkcija: atver logu un griež spēles ciklu."""
    pygame.init()
    pygame.display.set_caption("Shadow Courier")

    state = GameState()
    world_width = state.level.width * gs.TILE_SIZE
    world_height = state.level.height * gs.TILE_SIZE
    window = pygame.display.set_mode((world_width, world_height + HUD_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 24)
    big_font = pygame.font.SysFont("arial", 48, bold=True)
    sprites = load_sprites()

    current_screen = SCREEN_MENU
    player_facing = (0, 1)  # kurp spēlētājs skatās (sākumā — uz leju)

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
                current_screen = handle_key(event.key, current_screen, state)

        # --- 2. solis: atjaunināšana (tikai ja spēle rit) ---
        if current_screen == SCREEN_GAME:
            keys = pygame.key.get_pressed()
            move_x = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) \
                   - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
            move_y = int(keys[pygame.K_s] or keys[pygame.K_DOWN]) \
                   - int(keys[pygame.K_w] or keys[pygame.K_UP])
            if move_x != 0 or move_y != 0:
                player_facing = (move_x, move_y)  # atceramies pēdējo virzienu
            # Space un E apstrādājam šeit, lai viens nospiešanas = viena darbība
            state.update(dt, move_x, move_y, False, False)
            if state.status == STATUS_GAME_OVER:
                current_screen = SCREEN_GAME_OVER
            elif state.status == STATUS_WON:
                current_screen = SCREEN_WON

        # --- 3. solis: zīmēšana ---
        window.fill(COLOR_FLOOR)
        if current_screen == SCREEN_MENU:
            draw_menu(window, font, big_font)
        else:
            draw_world(window, state, sprites, player_facing)
            draw_hud(window, state, font)
            if current_screen == SCREEN_PAUSED:
                draw_center_text(window, big_font, font, "PAUZE",
                                 "P — turpināt | Esc — izvēlne")
            elif current_screen == SCREEN_GAME_OVER:
                draw_center_text(window, big_font, font, "SPĒLE BEIGUSIES",
                                 state.game_over_reason + "  |  R — no jauna | Esc — izvēlne")
            elif current_screen == SCREEN_WON:
                draw_center_text(window, big_font, font, "TU UZVARĒJI!",
                                 f"Punkti: {state.score}  |  R — no jauna | Esc — izvēlne")

        pygame.display.flip()


def handle_key(key: int, current_screen: str, state: GameState) -> str:
    """Apstrādā vienu taustiņa nospiešanu un atgriež jauno ekrānu."""
    if current_screen == SCREEN_MENU:
        if key == pygame.K_RETURN:
            return SCREEN_GAME
        if key in (pygame.K_ESCAPE, pygame.K_q):
            pygame.quit()
            sys.exit()
    elif current_screen == SCREEN_GAME:
        if key == pygame.K_p:
            return SCREEN_PAUSED
        if key == pygame.K_ESCAPE:
            return SCREEN_MENU
        if key == pygame.K_SPACE:
            # Space = 2. mehānika: izslēgt tuvāko lampu (viena darbība)
            state.update(0.0, 0, 0, True, False)
        if key == pygame.K_e:
            # E = paņemt atslēgu / atvērt durvis (viena darbība)
            state.update(0.0, 0, 0, False, True)
    elif current_screen == SCREEN_PAUSED:
        if key == pygame.K_p:
            return SCREEN_GAME
        if key == pygame.K_ESCAPE:
            return SCREEN_MENU
    elif current_screen in (SCREEN_GAME_OVER, SCREEN_WON):
        if key == pygame.K_r:
            # R = sākt jaunu spēli no 1. līmeņa
            state.__init__()
            return SCREEN_GAME
        if key == pygame.K_ESCAPE:
            state.__init__()
            return SCREEN_MENU
    return current_screen


# --- ZĪMĒŠANAS FUNKCIJAS (katra zīmē vienu lietu) ---


# Virziens (x, y) -> rotācijas leņķis bildēm (sprites zīmēti "skatās uz leju")
FACING_ANGLES = {(0, 1): 0, (1, 0): 90, (0, -1): 180, (-1, 0): 270}


def draw_world(window: pygame.Surface, state: GameState,
               sprites: dict[str, pygame.Surface | None],
               player_facing: tuple[int, int]) -> None:
    """Uzzīmē visu līmeni: grīdu, sienas, lampas, monētas, spēlētāju, sargus."""
    level = state.level
    t = gs.TILE_SIZE

    # Grīda (visi lauciņi, kas nav sienas) un sienas
    for row in range(level.height):
        for col in range(level.width):
            if (col, row) in level.walls:
                draw_sprite(window, sprites["wall"], col * t, row * t, t, COLOR_WALL)
            else:
                draw_sprite(window, sprites["floor"], col * t, row * t, t, COLOR_FLOOR)

    # Gaismas laukumi ap dedzinošām lampām (caurspīdīgi dzelteni apļi)
    light_layer = pygame.Surface((window.get_width(), window.get_height()), pygame.SRCALPHA)
    for (col, row), off_timer in level.lamps.items():
        if off_timer <= 0:
            center = (col * t + t // 2, row * t + t // 2)
            pygame.draw.circle(light_layer, (*COLOR_LIGHT, 60), center, gs.LIGHT_RADIUS)
    window.blit(light_layer, (0, 0))

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
    for (col, row), off_timer in level.lamps.items():
        lamp = sprites["lamp_on"] if off_timer <= 0 else sprites["lamp_off"]
        color = COLOR_LAMP_ON if off_timer <= 0 else COLOR_LAMP_OFF
        draw_sprite(window, lamp, col * t, row * t, t, color)

    # Sargi (pagriežas kustības virzienā)
    for guard in level.guards:
        if guard.horizontal:
            guard_dir = (guard.direction, 0)
        else:
            guard_dir = (0, guard.direction)
        draw_sprite(window, sprites["guard"], guard.x, guard.y, GUARD_SIZE,
                    COLOR_GUARD, FACING_ANGLES[guard_dir])

    # Spēlētājs (kurjers, pagriežas kustības virzienā)
    draw_sprite(window, sprites["player"], state.player_x, state.player_y,
                gs.PLAYER_SIZE, COLOR_PLAYER, FACING_ANGLES[player_facing])


def draw_hud(window: pygame.Surface, state: GameState, font: pygame.font.Font) -> None:
    """Uzzīmē augšējo joslu: punkti, līmenis, brīdinājumi, paziņojumi."""
    hud_top = state.level.height * gs.TILE_SIZE
    pygame.draw.rect(window, (20, 24, 32), (0, hud_top, window.get_width(), HUD_HEIGHT))

    info = f"Punkti: {state.score}   Līmenis: {state.level_number}"
    if state.has_key:
        info += "   [Atslēga]"
    window.blit(font.render(info, True, COLOR_TEXT), (12, hud_top + 6))

    # Gaismas brīdinājums: sarkana josla, kas piepildās, kamēr stāv gaismā
    if state.light_timer > 0:
        part = state.light_timer / gs.LIGHT_TIME_LIMIT
        pygame.draw.rect(window, COLOR_WARNING,
                         (12, hud_top + 38, int(200 * part), 12))
        window.blit(font.render("GAISMA!", True, COLOR_WARNING), (220, hud_top + 30))

    # Lampas slēdža uzlāde
    if state.lamp_cooldown > 0:
        text = f"Lampas slēdzis: {state.lamp_cooldown:.0f}s"
        window.blit(font.render(text, True, COLOR_TEXT), (420, hud_top + 30))

    if state.message:
        window.blit(font.render(state.message, True, COLOR_COIN), (420, hud_top + 6))


def draw_menu(window: pygame.Surface, font: pygame.font.Font,
              big_font: pygame.font.Font) -> None:
    """Uzzīmē galveno izvēlni."""
    draw_center_text(window, big_font, font, "SHADOW COURIER",
                     "Enter — spēlēt | Esc — iziet",
                     extra="Izdzēs lampas, apiet sargus un aiznes paketi līdz izejai!")


def draw_center_text(window: pygame.Surface, big_font: pygame.font.Font,
                     font: pygame.font.Font, title: str, subtitle: str,
                     extra: str = "") -> None:
    """Uzzīmē lielu virsrakstu ekrāna vidū un mazāku tekstu zem tā."""
    cx = window.get_width() // 2
    cy = window.get_height() // 2

    title_img = big_font.render(title, True, COLOR_TEXT)
    window.blit(title_img, title_img.get_rect(center=(cx, cy - 60)))

    if extra:
        extra_img = font.render(extra, True, COLOR_COIN)
        window.blit(extra_img, extra_img.get_rect(center=(cx, cy)))

    sub_img = font.render(subtitle, True, COLOR_TEXT)
    window.blit(sub_img, sub_img.get_rect(center=(cx, cy + 60)))


if __name__ == "__main__":
    main()
