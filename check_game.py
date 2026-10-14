"""Ad-hoc pārbaude bez loga: kartes + spēles loģika + sargu AI."""
import math
import sys
sys.path.insert(0, r"C:\projects\Shadow-Courier")

from game.game_state import GameState, STATUS_GAME_OVER, STATUS_PLAYING
from game.level import LEVEL_MAPS, Level
from game.pathfind import find_path, reachable_tiles
from game.guard import (STATE_PATROL, STATE_LAMP_ALERT, STATE_SEARCH,
                        STATE_WARNING, STATE_CHASE, tile_hitbox_corner)
from game import settings as s

# 1. Karšu pārbaude
def flood(rows, start, door_is_wall):
    """Plūdmaiņa no sākuma lauciņa. Ja door_is_wall=True, durvis skaitās siena."""
    seen = {start}
    stack = [start]
    while stack:
        c, r = stack.pop()
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (c + dc, r + dr)
            if n in seen:
                continue
            ch = rows[n[1]][n[0]]
            if ch == "#" or ch == "x" or (door_is_wall and ch == "D"):
                continue
            seen.add(n)
            stack.append(n)
    return seen

for i, rows in enumerate(LEVEL_MAPS, 1):
    widths = {len(r) for r in rows}
    assert len(widths) == 1, f"Līmenis {i}: rindas nav vienāda garuma: {widths}"
    w, h = len(rows[0]), len(rows)
    # Ārējai robežai jābūt no sienām (nekādu caurumu malās)
    for c in range(w):
        assert rows[0][c] == "#" and rows[h - 1][c] == "#", f"Līmenis {i}: caurums robežā rindā 0/{h-1}, kol {c}"
    for r in range(h):
        assert rows[r][0] == "#" and rows[r][w - 1] == "#", f"Līmenis {i}: caurums robežā rindā {r}"
    flat = "".join(rows)
    assert flat.count("P") == 1, f"Līmenis {i}: jābūt vienam P"
    assert flat.count("E") == 1, f"Līmenis {i}: jābūt vienai izejai E"
    start = exit_pos = None
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "P":
                start = (c, r)
            elif ch == "E":
                exit_pos = (c, r)
    # Ar atvērtām durvīm viss jāsasniedz
    seen_open = flood(rows, start, door_is_wall=False)
    assert exit_pos in seen_open, f"Līmenis {i}: izeja nav sasniedzama pat ar atslēgu!"
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch in "CK" and (c, r) not in seen_open:
                raise AssertionError(f"Līmenis {i}: '{ch}' ({c},{r}) nav sasniedzams")
    # GALVENĀ PĀRBAUDE: bez atslēgas (durvis = siena) izeju drīkst NESASNIEDZT
    seen_closed = flood(rows, start, door_is_wall=True)
    assert exit_pos not in seen_closed, \
        f"Līmenis {i}: KĻŪDA — izeju var sasniegt apejot durvis (atslēga nav vajadzīga)!"
    # Katrai lampai jābūt pie sienas (vismaz vienam no 4 kaimiņiem jābūt '#')
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "L":
                neighbours = (rows[r - 1][c], rows[r + 1][c],
                              rows[r][c - 1], rows[r][c + 1])
                assert "#" in neighbours, \
                    f"Līmenis {i}: lampa ({c},{r}) nav pie sienas!"
    # Starta pozīcijas (hitboxi) nedrīkst atrasties sienās
    lvl = Level(rows, i)
    assert not lvl.rect_hits_solid(*lvl.player_start,
                                   s.PLAYER_HIT_W, s.PLAYER_HIT_H), \
        f"Līmenis {i}: spēlētāja starts atrodas sienā!"
    for gd in lvl.guards:
        assert not lvl.rect_hits_solid(gd.x, gd.y, s.GUARD_HIT_W, s.GUARD_HIT_H), \
            f"Līmenis {i}: sargs ({gd.x:.0f},{gd.y:.0f}) sākas sienā!"
    print(f"Līmenis {i}: OK ({w}x{h}, sargu: {flat.count('G') + flat.count('V')}, izeja aiz durvīm ✓)")

# 2. Kustība un siena
g = GameState()
x0 = g.player_x
g.update(0.1, 1, 0, False, False)
assert g.player_x > x0, "spēlētājam vajadzēja pārvietoties pa labi"
g.update(0.1, -1, 0, False, False)
g.update(0.5, -1, 0, False, False)  # siena kreisajā pusē — nedrīkst iziet cauri
assert g.player_x > 0, "spēlētājs izgāja caur sienu!"
print("Kustība un sienas: OK")

def place_on_tile(g: GameState, col: int, row: int) -> None:
    """Uzliek spēlētāja hitboxu uz lauciņa (centrēts) — testu palīgs."""
    g.player_x = col * s.TILE_SIZE + (s.TILE_SIZE - s.PLAYER_HIT_W) // 2
    g.player_y = row * s.TILE_SIZE + (s.TILE_SIZE - s.PLAYER_HIT_H) // 2

# 3. Monēta dod punktus
g = GameState()
coin = next(iter(g.level.coins))
place_on_tile(g, *coin)
g.update(0.01, 0, 0, False, False)
assert g.score == s.COIN_POINTS, f"monēta nedeva punktus: {g.score}"
print("Monēta: OK (+10)")

# 4. Lampa: izslēgšana un cooldown
g = GameState()
lamp = next(iter(g.level.lamps))
place_on_tile(g, *lamp)
g.update(0.01, 0, 0, True, False)
assert g.level.lamps[lamp] > 0, "lampa neizslēdzās"
assert g.lamp_cooldown > 0, "cooldown neieslēdzās"
print("Lampas izslēgšana: OK")

# 5. LAMP_ALERT: spēlētājs degošas lampas gaismā 0.8 s -> sargu trauksme
# (Lampa (12,6) 1. līmenī ir tālu no abu sargu startiem, tāpēc lukturu
# konussi šeit nejauši neiejaucas.)
g = GameState()
assert (12, 6) in g.level.lamps, "1. līmenī nav lampas (12,6) — tests jāpārskata"
place_on_tile(g, 12, 6)
player_center = g.player_center()
for _ in range(int(s.LAMP_DETECT_TIME * 60) + 5):
    g.update(1 / 60, 0, 0, False, False)
states = {gd.state for gd in g.level.guards}
assert states <= {STATE_LAMP_ALERT, STATE_SEARCH}, \
    f"sargi nereaģēja uz lampas gaismu: {states}"
assert g.alert_count == 1, f"trauksme jāpalaiž tieši vienreiz: {g.alert_count}"
for gd in g.level.guards:
    assert math.hypot(gd.last_known_position[0] - player_center[0],
                      gd.last_known_position[1] - player_center[1]) < 1, \
        "last_known_position nav spēlētāja centrs"
    assert gd.alert_icon_timer > 0, "virs sarga jāparādās '!' ikonai"
assert g.lives == s.START_LIVES, "lampas gaisma vairs nedrīkst noņemt dzīvību!"
print("LAMP_ALERT: OK (trauksme pēc 0.8 s gaismā, dzīvības netiek noņemtas)")

# 5b. Ja spēlētājs iziet no gaismas pirms 0.8 s — nekādas trauksmes
g = GameState()
place_on_tile(g, 12, 6)
for _ in range(30):  # 0.5 s gaismā — mazāk par LAMP_DETECT_TIME
    g.update(1 / 60, 0, 0, False, False)
assert all(gd.state == STATE_PATROL for gd in g.level.guards), \
    "trauksme iestājās pārāk agri"
assert g.lamp_detect_timer > 0 and g.lamp_exposure > 0
place_on_tile(g, 1, 1)  # ārā no gaismas
g.update(1 / 60, 0, 0, False, False)
assert g.lamp_detect_timer == 0.0 and g.lamp_exposure == 0.0, \
    "lampas taimerim jāatiestatās, izējot no gaismas"
assert g.alert_count == 0
print("Lampas taimera atiestate: OK (iziešana pirms 0.8 s — bez trauksmes)")

# 5c. Izslēgta lampa nerada trauksmi (sargus aiznesam projām, lai lukturi nejauktu)
g = GameState()
g.level.lamps[(12, 6)] = 5.0  # lampa izslēgta
for gd in g.level.guards:
    gd.x, gd.y = tile_hitbox_corner(1, 13)  # tālu prom, ārpus luktura riska
place_on_tile(g, 12, 6)
for _ in range(120):  # 2 s uz izslēgtās lampas
    g.update(1 / 60, 0, 0, False, False)
assert g.alert_count == 0, "izslēgta lampa izsauca trauksmi!"
assert all(gd.state == STATE_PATROL for gd in g.level.guards)
print("Izslēgta lampa: OK (bez trauksmes)")

# 5d. SEARCH beidzas pēc SEARCH_TIME -> PATROL ar jaunu mērķi
g = GameState()
for gd in g.level.guards:
    gd.state = STATE_SEARCH
    gd.search_timer = 0.05
    gd.path = []
    gd.search_points = []
    gd.last_known_position = (600.0, 312.0)
place_on_tile(g, 1, 1)  # spēlētājs tālu prom, tumsā
for _ in range(30):  # 0.5 s — pietiek, lai SEARCH beigtos
    g.update(1 / 60, 0, 0, False, False)
assert all(gd.state == STATE_PATROL for gd in g.level.guards), \
    "pēc SEARCH laika beigām sargiem jāatgriežas PATROL"
print("SEARCH -> PATROL: OK (pēc 6 s atgriežas patrulēšanā)")

# 6. Atslēga + durvis
g = GameState()
place_on_tile(g, *g.level.key_pos)
g.update(0.01, 0, 0, False, True)
assert g.has_key and g.level.key_pos is None and g.score == s.KEY_POINTS
d = g.level.door_pos
place_on_tile(g, d[0], d[1] - 1)  # stāvam vienu lauciņu virs durvīm
g.update(0.01, 0, 0, False, True)
assert g.level.door_open, "durvis neatvērās ar atslēgu"
print("Atslēga un durvis: OK (+25)")

# 7. Izeja -> "līmenis izpildīts" ar bonusu, tad next_level() -> līmenis 2
from game.game_state import STATUS_LEVEL_COMPLETE
g = GameState()
place_on_tile(g, *g.level.exit_pos)
g.update(0.01, 0, 0, False, False)
assert g.status == STATUS_LEVEL_COMPLETE and g.score >= s.LEVEL_BONUS
assert g.level_stats["coins_total"] > 0, "level_stats nesaglabāja statistiku"
g.next_level()
assert g.level_number == 2 and g.status == STATUS_PLAYING
print(f"Izeja: OK (līmenis izpildīts -> līmenis 2, punkti: {g.score})")

# 8. Noķeršana: hitboxu pārklāšanās -> uzreiz game_over (dzīvības netiek noņemtas)
g = GameState()
guard = g.level.guards[0]
g.player_x, g.player_y = guard.x, guard.y
g.update(0.01, 0, 0, False, False)
assert g.status == STATUS_GAME_OVER, "noķeršana nebeidza spēli"
assert g.lives == s.START_LIVES, "sargs nedrīkst noņemt dzīvību — uzreiz game over"
assert g.game_over_reason, "game_over_reason jābūt aizpildītam (CAUGHT ekrāns)"
print(f"Noķeršana: OK (uzreiz game over — '{g.game_over_reason}')")

# 9. 1-flīžu koridors: hitboxs iet cauri abos virzienos, neiestrēgst
def run_corridor(rows: list[str], start_tile: tuple[int, int],
                 moves: list[tuple[int, int, int]]) -> GameState:
    """Spēle ar pašu karti. moves = (move_x, move_y, kadru_skaits) saraksts."""
    g = GameState()
    g.level = Level(rows, 1)
    place_on_tile(g, *start_tile)
    for mx, my, frames in moves:
        for _ in range(frames):
            g.update(0.1, mx, my, False, False)
    return g

def player_tile(g: GameState) -> tuple[int, int]:
    """Lauciņš, kurā šobrīd atrodas spēlētāja hitboxa centrs."""
    return g.level.tile_at_pixel(*g.player_center())

horizontal = ["#####",
              "#...#",
              "#####"]
g = run_corridor(horizontal, (1, 1), [(1, 0, 12)])
assert player_tile(g) == (3, 1), \
    f"iestrēga horizontālajā koridorā: {player_tile(g)}"
g = run_corridor(horizontal, (3, 1), [(-1, 0, 12)])
assert player_tile(g) == (1, 1), \
    f"neatgriezās horizontālajā koridorā: {player_tile(g)}"

vertical = ["###",
            "#.#",
            "#.#",
            "#.#",
            "###"]
g = run_corridor(vertical, (1, 1), [(0, 1, 12)])
assert player_tile(g) == (1, 3), \
    f"iestrēga vertikālajā koridorā: {player_tile(g)}"
g = run_corridor(vertical, (1, 3), [(0, -1, 12)])
assert player_tile(g) == (1, 1), \
    f"neatgriezās vertikālajā koridorā: {player_tile(g)}"
print("1-flīžu koridori: OK (abos virzienos, bez iestrēgšanas)")

# 10. BFS: ceļš starp brīvām flīzēm eksistē; patruļas mērķis nekad nav ciets
for i, rows in enumerate(LEVEL_MAPS, 1):
    lvl = Level(rows, i)
    free = [(c, r) for r in range(lvl.height) for c in range(lvl.width)
            if not lvl.is_solid_tile(c, r)]
    start = free[0]
    reach = reachable_tiles(lvl.is_solid_tile, start)
    goal = next(iter(reach - {start}))
    path = find_path(lvl.is_solid_tile, start, goal)
    assert path is not None and path[0] == start and path[-1] == goal, \
        f"Līmenis {i}: BFS neatrada ceļu starp brīvām flīzēm"
    assert all(not lvl.is_solid_tile(c, r) for c, r in path), \
        f"Līmenis {i}: BFS ceļš iet caur cietu flīzi"
    # Ar atvērtām durvīm no starta līdz izejai jānokļūst
    lvl.door_open = True
    start_tile = lvl.tile_at_pixel(*lvl.player_start)
    path = find_path(lvl.is_solid_tile, start_tile, lvl.exit_pos)
    assert path is not None, f"Līmenis {i}: ar atvērtām durvīm BFS nesasniedz izeju"

lvl = Level(LEVEL_MAPS[0], 1)
gd = lvl.guards[0]
for _ in range(100):
    target = gd._choose_patrol_target(lvl)
    assert not lvl.is_solid_tile(*target), \
        f"patruļas mērķis trāpīja cietā flīzē: {target}"
print("BFS un patruļas mērķi: OK (ceļi eksistē, 100 nejauši mērķi — visi brīvi)")

# 11. PATROL: sargs kustas un nekad neieiet cietā flīzē (simulējam 10 s)
g = GameState()  # spēlētājs paliek starta vietā (1,1) — tumsā, tālu no sargiem
gd = g.level.guards[0]
x0, y0 = gd.x, gd.y
moved = False
for _ in range(600):
    g.update(1 / 60, 0, 0, False, False)
    for guard in g.level.guards:
        assert not g.level.rect_hits_solid(guard.x, guard.y,
                                           s.GUARD_HIT_W, s.GUARD_HIT_H), \
            f"sargs iegāja cietā flīzē: ({guard.x:.0f},{guard.y:.0f})"
    if (gd.x, gd.y) != (x0, y0):
        moved = True
    if g.status != STATUS_PLAYING:
        break  # ja sargs noķēra stāvošo spēlētāju, kustība jau pierādīta
assert moved, "sargs 10 s laikā nekad nepārvietojās"
print("PATROL kustība: OK (sargs pārvietojas un nekad neieiet sienā)")

# 12. FLASHLIGHT_WARNING: spēlētājs konusā ar brīvu skata līniju -> sargs apstājas
warning_map = ["#########",
               "#...G...#",
               "#.......#",
               "#.......#",
               "#...P...#",
               "#########"]
g = GameState()
g.level = Level(warning_map, 1)
gd = g.level.guards[0]
gd.facing = (0.0, 1.0)  # skatās uz leju, kur stāv spēlētājs
place_on_tile(g, 4, 3)
g.update(1 / 60, 0, 0, False, False)
assert gd.state == STATE_WARNING, f"sargs neieraudzīja spēlētāju konusā: {gd.state}"
assert gd.alert_icon_timer > 0, "virs sarga jāparādās '!' ikonai"
gx, gy = gd.x, gd.y
for _ in range(70):  # kopā ~1.18 s — mazāk par FLASHLIGHT_WARNING_TIME
    g.update(1 / 60, 0, 0, False, False)
assert (gd.x, gd.y) == (gx, gy), "sargs kustējās brīdinājuma laikā!"
assert gd.state == STATE_WARNING, "brīdinājums beidzās pārāk agri"
print("FLASHLIGHT_WARNING: OK (sargs apstājas uz 1.30 s ar '!' ikonu)")

# 12b. Spēlētājs aiz sienas — sargs nereaģē (skata līniju bloķē siena)
wall_map = ["#####",
            "#.G.#",
            "#####",
            "#.P.#",
            "#####"]
g = GameState()
g.level = Level(wall_map, 1)
gd = g.level.guards[0]
gd.facing = (0.0, 1.0)  # skatās tieši uz spēlētāju, bet starp viņiem siena
place_on_tile(g, 2, 3)
for _ in range(30):
    g.update(1 / 60, 0, 0, False, False)
assert gd.state == STATE_PATROL, "sargs ierauga spēlētāju caur sienu!"
assert g.status == STATUS_PLAYING
print("Skata līnija: OK (siena bloķē lukturi — reakcijas nav)")

# 13. CHASE: pēc brīdinājuma, ja spēlētājs joprojām redzams -> dzīšanās un tuvošanās
g = GameState()
g.level = Level(warning_map, 1)
gd = g.level.guards[0]
gd.facing = (0.0, 1.0)
place_on_tile(g, 4, 3)
for _ in range(86):  # ~1.43 s — brīdinājums (1.30 s) ir beidzies
    g.update(1 / 60, 0, 0, False, False)
assert gd.state == STATE_CHASE, f"pēc brīdinājuma nav CHASE: {gd.state}"
assert gd._chase_speed() > s.PLAYER_SPEED, "dzīšanās ātrumam jāpārsniedz spēlētāju"
d0 = math.hypot(gd.center()[0] - g.player_center()[0],
                gd.center()[1] - g.player_center()[1])
for _ in range(10):
    g.update(1 / 60, 0, 0, False, False)
if g.status == STATUS_PLAYING:
    d1 = math.hypot(gd.center()[0] - g.player_center()[0],
                    gd.center()[1] - g.player_center()[1])
    assert d1 < d0, "sargs CHASE laikā netuvojas spēlētājam!"
print("CHASE: OK (pēc brīdinājuma sargs dzenas pakaļ un tuvojas)")

# 13b. Spēlētājs pazūd (teleports aiz sarga, ārpus konusa) -> SEARCH
g = GameState()
g.level = Level(warning_map, 1)
gd = g.level.guards[0]
gd.facing = (0.0, 1.0)
place_on_tile(g, 4, 3)
for _ in range(90):  # 1.5 s — sargs jau dzenas pakaļ
    g.update(1 / 60, 0, 0, False, False)
assert gd.state == STATE_CHASE
place_on_tile(g, 1, 1)  # aiz sarga muguras, ārpus luktura konusa
g.update(1 / 60, 0, 0, False, False)
assert gd.state == STATE_SEARCH, \
    f"pazudušais spēlētājs neizsauca SEARCH: {gd.state}"
assert gd.search_timer > 0, "SEARCH taimerim jābūt iestatītam"
print("CHASE -> SEARCH: OK (spēlētājs pazūd — sargs meklē pēdējā redzētajā vietā)")

print("\nVISI TESTI IZJAUTI ✅")
