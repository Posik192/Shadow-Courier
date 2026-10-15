"""Pagaidu skripts: UI ekrānu screenshoti bez loga (verifikācijai)."""
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
ui = {
    "selection": 0,
    "settings_from": cm.SCREEN_MENU,
    "volumes": {"MASTER VOLUME": 70, "MUSIC": 60, "SOUND EFFECTS": 40},
    "fullscreen": True,
    "game_started": True,
    "completed_levels": {1},
    "best_ranks": {1: "A"},
}


def shot(name):
    pygame.image.save(window, os.path.join("shots", name))
    print(name)


# MAIN MENU (ar CONTINUE, jo game_started=True)
window.fill(cm.UI_BG)
cm.draw_menu(window, fonts, state, ui)
shot("screen_menu.png")

# LEVEL SELECT (1. līmenis pabeigts, 2. pieejams, 3. bloķēts)
ui["selection"] = 1
window.fill(cm.UI_BG)
cm.draw_level_select(window, fonts, ui)
shot("screen_level_select.png")

# SETTINGS (izvēlēts 1. slīdnis)
ui["selection"] = 0
window.fill(cm.UI_BG)
cm.draw_settings(window, fonts, ui)
shot("screen_settings.png")


def draw_game_behind():
    window.fill(cm.UI_BG)
    cm.draw_world(window, state, sprites, (0, 1), False)
    cm.draw_hud(window, state, fonts, sprites)


# PAUSE
ui["selection"] = 0
draw_game_behind()
cm.draw_paused(window, fonts, ui)
shot("screen_paused.png")

# CAUGHT
state.game_over_reason = "A guard spotted you."
ui["selection"] = 0
draw_game_behind()
cm.draw_game_over(window, fonts, state, ui)
shot("screen_caught.png")

# LEVEL COMPLETE
state.level_stats = {"coins": 3, "coins_total": 5, "time": 75.4, "score": 350,
                     "alerts": 1, "rank": "A"}
ui["selection"] = 0
draw_game_behind()
cm.draw_level_complete(window, fonts, state, ui)
shot("screen_level_complete.png")

# WIN
state.score = 1234
ui["selection"] = 0
draw_game_behind()
cm.draw_won(window, fonts, state, ui)
shot("screen_won.png")

pygame.quit()
print("Gatavs.")
