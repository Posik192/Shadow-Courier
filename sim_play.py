"""Simulē reālu spēlēšanu bez loga: kustina spēlētāju un zīmē visus kadrus."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from game import settings as gs
from game.game_state import GameState
from client.main import (HUD_HEIGHT, draw_world, draw_hud, load_sprites,
                         draw_level_complete, load_hud_fonts)

pygame.init()
state = GameState()
w = state.level.width * gs.TILE_SIZE
h = state.level.height * gs.TILE_SIZE + HUD_HEIGHT
surface = pygame.display.set_mode((w, h))
sprites = load_sprites()
fonts = {
    "font": pygame.font.SysFont("consolas", 20),
    "big": pygame.font.SysFont("consolas", 44, bold=True),
    "small": pygame.font.SysFont("consolas", 16),
}
fonts["hud"] = load_hud_fonts()

clock = pygame.time.Clock()
# 3600 kadri = 60 sekundes spēles
for frame in range(3600):
    dt = clock.tick(60) / 1000.0
    # Ja sūtījums vēl nav paņemts — teleportējamies pie M un "nospiežam" E.
    # Bez sūtījuma izeja nedarbojas, tāpēc sims to paņem vispirms.
    if state.status == "playing" and not state.level.package_taken:
        pc, pr = state.level.package_pos
        state.player_x = pc * gs.TILE_SIZE + (gs.TILE_SIZE - gs.PLAYER_HIT_W) // 2
        state.player_y = pr * gs.TILE_SIZE + (gs.TILE_SIZE - gs.PLAYER_HIT_H) // 2
        state.update(dt, 0, 0, False, True)  # E = paņemt sūtījumu
    # Spēlētājs staigā pa apli: pa labi, lejup, pa kreisi, augšup,
    # un pa diagonāli (diagonālā kustība reiz nokrasoja spēli — KeyError!)
    direction = (frame // 60) % 5
    moves = [(1, 0), (0, 1), (-1, 0), (0, -1), (1, -1)]
    mx, my = moves[direction]
    state.update(dt, mx, my, frame % 90 == 0, frame % 120 == 0)
    # Ja līmenis izpildīts (vai uzvara), simulācija uzreiz turpina tālāk
    if state.status == "level_complete":
        # Uzzīmējam LEVEL COMPLETE ekrānu (ar vērtējumu), lai pārbaudītu,
        # ka tas nekritīs reālā spēlē
        draw_level_complete(surface, fonts, state, {"selection": 0})
        state.next_level()
    elif state.status in ("game_over", "won"):
        state.__init__()
    draw_world(surface, state, sprites, (mx, my) if (mx, my) != (0, 0) else (0, 1), True)
    draw_hud(surface, state, fonts, sprites)
    pygame.display.flip()
    if frame % 600 == 0:
        print(f"kadrs {frame}: punkti={state.score}, statuss={state.status}, līmenis={state.level_number}")

print("3600 kadri bez kļūdām — spēle nenokrīt!")
