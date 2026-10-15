"""Pagaidu skripts: HUD joslas screenshoti 3 stāvokļos (bez loga)."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from game import settings as gs
from game.game_state import GameState
from client import main as cm

pygame.init()
os.makedirs("shots", exist_ok=True)

state = GameState()
w = state.level.width * gs.TILE_SIZE
h = state.level.height * gs.TILE_SIZE + cm.HUD_HEIGHT
window = pygame.display.set_mode((w, h))
fonts = {
    "font": pygame.font.SysFont("consolas", 20),
    "big": pygame.font.SysFont("consolas", 44, bold=True),
    "small": pygame.font.SysFont("consolas", 16),
}
fonts["hud"] = cm.load_hud_fonts()
sprites = cm.load_sprites()

# Izgriežam tikai apakšējo HUD joslu, lai to var apskatīt tuvplānā
hud_rect = pygame.Rect(0, h - cm.HUD_HEIGHT, w, cm.HUD_HEIGHT)


def shot(name):
    """Uzzīmē pasauli + HUD un saglabā tikai joslas daļu kā PNG."""
    window.fill(cm.UI_BG)
    cm.draw_world(window, state, sprites, (0, 1), False)
    cm.draw_hud(window, state, fonts, sprites)
    pygame.image.save(window.subsurface(hud_rect), os.path.join("shots", name))
    print(name)


# Parasts stāvoklis: 3 dzīvības, 2/5 monētas, LAMP READY, EXPOSURE 0%
state.lives = 3
state.coins_collected = 2
for _ in range(2):
    state.level.coins.pop()
state.lamp_cooldown = 0.0
state.lamp_exposure = 0.0
state.message = ""
shot("hud_normal.png")

# Brīdinājums: EXPOSURE 85% (bīstamais stāvoklis ar sarkano fonu)
state.lamp_exposure = 0.85
shot("hud_warning.png")

# Cooldown: 2 dzīvības, 3/5 monētas, LAMP 4.2 s, EXPOSURE 0%
state.lives = 2
state.coins_collected = 3
state.level.coins.pop()
state.lamp_cooldown = 4.2
state.lamp_exposure = 0.0
shot("hud_cooldown.png")

pygame.quit()
print("Gatavs.")
