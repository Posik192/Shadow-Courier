"""Simulē reālu spēlēšanu bez loga: kustina spēlētāju un zīmē visus kadrus."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from game import settings as gs
from game.game_state import GameState
from client.main import draw_world, draw_hud, load_sprites

pygame.init()
state = GameState()
w = state.level.width * gs.TILE_SIZE
h = state.level.height * gs.TILE_SIZE + 64
surface = pygame.display.set_mode((w, h))
sprites = load_sprites()
font = pygame.font.SysFont("arial", 24)

clock = pygame.time.Clock()
moving = True
# 3600 kadri = 60 sekundes spēles
for frame in range(3600):
    dt = clock.tick(60) / 1000.0
    # Spēlētājs staigā pa apli: pa labi, lejup, pa kreisi, augšup,
    # un pa diagonāli (diagonālā kustība reiz nokrasoja spēli — KeyError!)
    direction = (frame // 60) % 5
    moves = [(1, 0), (0, 1), (-1, 0), (0, -1), (1, -1)]
    mx, my = moves[direction]
    state.update(dt, mx, my, frame % 90 == 0, frame % 120 == 0)
    draw_world(surface, state, sprites, (mx, my) if (mx, my) != (0, 0) else (0, 1), True)
    draw_hud(surface, state, font)
    pygame.display.flip()
    if frame % 600 == 0:
        print(f"kadrs {frame}: punkti={state.score}, statuss={state.status}, līmenis={state.level_number}")

print("3600 kadri bez kļūdām — spēle nenokrīt!")
