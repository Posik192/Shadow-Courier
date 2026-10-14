"""Ad-hoc pārbaude bez loga: kartes + spēles loģika."""
import sys
sys.path.insert(0, r"C:\projects\Shadow-Courier")

from game.game_state import GameState, STATUS_GAME_OVER, STATUS_PLAYING
from game.level import LEVEL_MAPS, Level
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

# 5. Gaisma noņem dzīvību, bet spēle beidzas tikai pie 0 dzīvībām
g = GameState()
lamp = next(iter(g.level.lamps))
place_on_tile(g, *lamp)
lives_before = g.lives
for _ in range(int(s.LIGHT_TIME_LIMIT * 60) + 5):
    g.update(1 / 60, 0, 0, False, False)
assert g.lives == lives_before - 1 and g.status == STATUS_PLAYING, "gaisma nenoņēma dzīvību"
g.light_timer = s.LIGHT_TIME_LIMIT  # beidzamās dzīvības scenārijs
g.lives = 1
place_on_tile(g, *lamp)
g.update(1 / 60, 0, 0, False, False)
assert g.status == STATUS_GAME_OVER and "gaism" in g.game_over_reason
print(f"Gaismas briesmas: OK (-1 dzīvība, pie 0 — {g.game_over_reason})")

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

# 8. Sargs noņem dzīvību; pie 0 dzīvībām — spēles beigas
g = GameState()
guard = g.level.guards[0]
g.player_x, g.player_y = guard.x, guard.y
g.update(0.01, 0, 0, False, False)
assert g.lives == s.START_LIVES - 1 and g.status == STATUS_PLAYING, "sargs nenoņēma dzīvību"
g.lives = 1
g.player_x, g.player_y = guard.x, guard.y
g.update(0.01, 0, 0, False, False)
assert g.status == STATUS_GAME_OVER
print(f"Sargs: OK (-1 dzīvība, pie 0 — {g.game_over_reason})")

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

print("\nVISI TESTI IZJAUTI ✅")
