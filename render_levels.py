"""Uzzīmē katru līmeni PNG failā (bez loga), lai pārbaudītu kartes vizuāli."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from game import settings as gs
from game.game_state import GameState
from client.main import draw_world, draw_hud

pygame.init()
state = GameState()
font = pygame.font.SysFont("arial", 24)

for level_num in (1, 2, 3):
    state.load_level(level_num)
    w = state.level.width * gs.TILE_SIZE
    h = state.level.height * gs.TILE_SIZE + 64
    surface = pygame.display.set_mode((w, h))
    surface.fill((34, 40, 52))
    draw_world(surface, state)
    draw_hud(surface, state, font)
    pygame.image.save(surface, f"level_{level_num}.png")
    print(f"level_{level_num}.png saglabāts")

pygame.quit()
