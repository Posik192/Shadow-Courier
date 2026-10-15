"""Uzzīmē katru līmeni PNG failā (bez loga), lai pārbaudītu kartes vizuāli."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from game import settings as gs
from game.game_state import GameState
from client.main import HUD_HEIGHT, draw_world, draw_hud, load_sprites, \
    load_hud_fonts

pygame.init()
state = GameState()
fonts = {
    "font": pygame.font.SysFont("consolas", 20),
    "big": pygame.font.SysFont("consolas", 44, bold=True),
    "small": pygame.font.SysFont("consolas", 16),
}
fonts["hud"] = load_hud_fonts()

for level_num in (1, 2, 3):
    state.load_level(level_num)
    w = state.level.width * gs.TILE_SIZE
    h = state.level.height * gs.TILE_SIZE + HUD_HEIGHT
    surface = pygame.display.set_mode((w, h))
    sprites = load_sprites()
    surface.fill((20, 23, 28))
    draw_world(surface, state, sprites, (0, 1), player_moving=False)
    draw_hud(surface, state, fonts, sprites)
    pygame.image.save(surface, f"level_{level_num}.png")
    print(f"level_{level_num}.png saglabāts")

pygame.quit()
