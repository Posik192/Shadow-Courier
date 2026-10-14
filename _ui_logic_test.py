"""Pagaidu tests: izvēļņu navigācijas loģika bez loga (verifikācijai)."""
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"

import pygame
from game.game_state import GameState, STATUS_PLAYING
from client import main as cm

pygame.init()
state = GameState()
pygame.display.set_mode((100, 100))
ui = {
    "selection": 0,
    "settings_from": cm.SCREEN_MENU,
    "volumes": {"MASTER VOLUME": 70, "MUSIC": 60, "SOUND EFFECTS": 60},
    "fullscreen": False,
    "game_started": False,
    "completed_levels": set(),
    "best_ranks": {},
}
K = pygame.K_RETURN
UP, DOWN, LEFT, RIGHT, ESC = pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_ESCAPE

# 1. MENU bez CONTINUE (game_started=False): 4 opcijas
assert cm.main_menu_options(ui, state) == ["NEW GAME", "LEVEL SELECT", "SETTINGS", "QUIT"]

# 2. NEW GAME -> game, game_started=True
s = cm.handle_key(K, cm.SCREEN_MENU, state, ui)
assert s == cm.SCREEN_GAME and ui["game_started"], s

# 3. Tagad MENU ir ar CONTINUE
opts = cm.main_menu_options(ui, state)
assert opts[0] == "CONTINUE" and len(opts) == 5, opts

# 4. ESC no spēles -> menu; CONTINUE atgriež spēlē
s = cm.handle_key(ESC, cm.SCREEN_GAME, state, ui)
assert s == cm.SCREEN_MENU and ui["selection"] == 0
s = cm.handle_key(K, cm.SCREEN_MENU, state, ui)  # CONTINUE ir 0. pozīcijā
assert s == cm.SCREEN_GAME, s

# 5. P -> pauze; pārvietojas uz SETTINGS un atpakaļ
s = cm.handle_key(pygame.K_p, cm.SCREEN_GAME, state, ui)
assert s == cm.SCREEN_PAUSED
cm.handle_key(DOWN, cm.SCREEN_PAUSED, state, ui)
cm.handle_key(DOWN, cm.SCREEN_PAUSED, state, ui)
s = cm.handle_key(K, cm.SCREEN_PAUSED, state, ui)  # SETTINGS
assert s == cm.SCREEN_SETTINGS and ui["settings_from"] == cm.SCREEN_PAUSED
# Slīdņi: LEFT samazina par 10, RIGHT palielina; robežas 0..100
ui["selection"] = 0
cm.handle_key(LEFT, cm.SCREEN_SETTINGS, state, ui)
assert ui["volumes"]["MASTER VOLUME"] == 60, ui["volumes"]
for _ in range(8):
    cm.handle_key(LEFT, cm.SCREEN_SETTINGS, state, ui)
assert ui["volumes"]["MASTER VOLUME"] == 0
for _ in range(12):
    cm.handle_key(RIGHT, cm.SCREEN_SETTINGS, state, ui)
assert ui["volumes"]["MASTER VOLUME"] == 100
# FULLSCREEN checkbox (4. rinda): toggle_fullscreen
ui["selection"] = 3
cm.handle_key(K, cm.SCREEN_SETTINGS, state, ui)
assert ui["fullscreen"] is True
cm.handle_key(K, cm.SCREEN_SETTINGS, state, ui)
assert ui["fullscreen"] is False
# ESC -> atpakaļ uz pauzi
s = cm.handle_key(ESC, cm.SCREEN_SETTINGS, state, ui)
assert s == cm.SCREEN_PAUSED, s
# Pauzes RESTART LEVEL
ui["selection"] = 1
s = cm.handle_key(K, cm.SCREEN_PAUSED, state, ui)
assert s == cm.SCREEN_GAME and state.status == STATUS_PLAYING

# 6. LEVEL SELECT: 2. līmenis bloķēts, kamēr 1. nav pabeigts
s = cm.handle_key(ESC, cm.SCREEN_GAME, state, ui)  # menu
ui["selection"] = 2  # LEVEL SELECT (ar CONTINUE: 0=CONTINUE,1=NEW GAME,2=LEVEL SELECT)
s = cm.handle_key(K, cm.SCREEN_MENU, state, ui)
assert s == cm.SCREEN_LEVEL_SELECT
cm.handle_key(DOWN, cm.SCREEN_LEVEL_SELECT, state, ui)  # 02 SECURITY (bloķēts)
s = cm.handle_key(K, cm.SCREEN_LEVEL_SELECT, state, ui)
assert s == cm.SCREEN_LEVEL_SELECT, "bloķēto līmeni nedrīkst ielādēt"
ui["completed_levels"].add(1)
s = cm.handle_key(K, cm.SCREEN_LEVEL_SELECT, state, ui)
assert s == cm.SCREEN_GAME and state.level_number == 2, (s, state.level_number)

# 7. CAUGHT: TRY AGAIN atjauno dzīvības un līmeni
state.lives = 0
state.status = "game_over"
state.game_over_reason = "A guard spotted you."
s = cm.handle_key(K, cm.SCREEN_GAME_OVER, state, ui)  # TRY AGAIN (0)
assert s == cm.SCREEN_GAME and state.lives == 3 and state.status == STATUS_PLAYING

# 8. LEVEL COMPLETE: NEXT LEVEL -> nākamais līmenis; pēdējā līmenī nav NEXT LEVEL
state.status = "level_complete"
state.level_stats = {"coins": 1, "coins_total": 5, "time": 10.0, "score": 50,
                     "alerts": 0, "rank": "A"}
ui["selection"] = 0
s = cm.handle_key(K, cm.SCREEN_LEVEL_COMPLETE, state, ui)
assert s == cm.SCREEN_GAME and state.level_number == 3
assert cm.level_complete_options(state) == ["RETRY FOR BETTER RANK", "LEVEL SELECT"]  # pēdējais līmenis

# 8b. RETRY FOR BETTER RANK: restartē līmeni, punkti uz līmeņa sākuma vērtību
state.status = "level_complete"
state.level_stats = {"coins": 0, "coins_total": 5, "time": 99.0, "score": 10,
                     "alerts": 2, "rank": "C"}
state.score = state.level_start_score + 50  # it kā līmeņa laikā iekrāti punkti
ui["selection"] = 0  # RETRY (NEXT LEVEL pēdējā līmenī nav)
s = cm.handle_key(K, cm.SCREEN_LEVEL_COMPLETE, state, ui)
assert s == cm.SCREEN_GAME and state.level_number == 3
assert state.status == STATUS_PLAYING and state.score == state.level_start_score

# 9. WIN: PLAY AGAIN -> jauna spēle
state.status = "won"
ui["selection"] = 0
s = cm.handle_key(K, cm.SCREEN_WON, state, ui)
assert s == cm.SCREEN_GAME and state.level_number == 1 and state.score == 0

print("Izvēļņu navigācijas tests: VISI OK")
pygame.quit()
