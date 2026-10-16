"""Līmeņu kartes un Level klase.

Karte ir teksta rindas, katrs simbols = viens lauciņš:
    # - siena
    . - grīda
    P - spēlētāja starts
    C - monēta (+10)
    K - atslēga (+25, vajadzīga durvīm)
    D - durvis (atver ar E, ja ir atslēga)
    E - izeja
    L - lampa (apgaismo apkārtni)
    x - kaste/muca (šķērslis, caur nevar)
    M - sūtījums (bez tā izeja nedarbojas)
    H - slēptuve (ar E var paslēpties, flīze paliek brīva)
    G - sargs (horizontālais), V - sargs (vertikālais)
"""

from game.guard import Guard
from game import settings as s
from game.settings import (TILE_SIZE, GUARD_SPEEDS,
                           PLAYER_HIT_W, PLAYER_HIT_H, FEET_MARGIN)
import math

# --- TRĪS LĪMEŅU KARTES (24x16, grūtība aug) ---

LEVEL_MAPS = [
    # 1. līmenis: liela noliktavas zāle, 2 sargi, 5 lampas, 5 monētas.
    # Atslēga ZR istabā, sūtījums D vidējā istabā — katrai sava lampa.
    [
        "########################",
        "#P......#.....C#.xx....#",
        "#.......#..xx..#.xx....#",
        "#.......#..xx..#......C#",
        "#.......#......#.......#",
        "####.######.####.......#",
        "#....L......L..........#",
        "#..xxH...xx............#",
        "#..xx....xx....L..V.C..#",
        "#..............#.xxx...#",
        "#CH....G.......#.......#",
        "###.########.########D##",
        "#.......#.....xx...#...#",
        "#L.K....#L....xx...#.E.#",
        "#.........M.....C..#...#",
        "########################",
    ],
    # 2. līmenis: vairākas telpas, 3 sargi (2 vertikālie + 1 horizontālais),
    # 6 lampas, 5 monētas. Izejas telpa ZR aiz durvīm.
    [
        "########################",
        "#P....#...C...#.....L..#",
        "#.....#.V.....#..xxK...#",
        "#H........xx..#..xx....#",
        "#L........xx..#.......C#",
        "#.....#L.......###.#####",
        "#C....#.......####..####",
        "#.....#..............L.#",
        "#..xx....xx.....xx...V.#",
        "#..xxH...xx..C..xx.....#",
        "#.....G.......L........#",
        "##D##.############.#####",
        "#...#.........xxH....ML#",
        "#.E.#.........xx....C..#",
        "#...#..................#",
        "########################",
    ],
    # 3. līmenis: blīvāka noliktava, 4 sargi, 7 lampas, 5 monētas.
    # Sūtījums un atslēga divās atsevišķās istabās, katrai sava lampa.
    [
        "########################",
        "#P.....#......#........#",
        "#......#..xx..#.Vxx....#",
        "#......#..xx..#..xx....#",
        "#..L........C.........L#",
        "####.#####.###.........#",
        "#....Lxx...L.L.........#",
        "#.....xx.........xx...C#",
        "#..........G...........#",
        "#C......xx..........V..#",
        "###.##############.#####",
        "#LM....C..#........#...#",
        "#..Hxx....#..xx....#H..#",
        "#...xx...H#..xx....D.E.#",
        "#....G....#LK.....C.#..#",
        "########################",
    ],
]


class Level:
    """Viena līmeņa dati: sienas, monētas, lampas, sargi utt."""

    def __init__(self, rows: list[str], level_number: int) -> None:
        """Izveido līmeni no kartes rindām. level_number nosaka sargu ātrumu."""
        self.rows = rows
        self.height = len(rows)
        self.width = len(rows[0])

        # Lauciņu kopas: (kolonna, rinda)
        self.walls: set[tuple[int, int]] = set()
        self.props: set[tuple[int, int]] = set()  # kastes/mucas ('x')
        self.coins: set[tuple[int, int]] = set()
        self.lamps: dict[tuple[int, int], float] = {}  # flīze -> cik ilgi izslēgta
        self.guards: list[Guard] = []
        self.key_pos: tuple[int, int] | None = None
        self.door_pos: tuple[int, int] | None = None
        self.door_open = False
        self.exit_pos: tuple[int, int] = (0, 0)
        self.package_pos: tuple[int, int] | None = None  # sūtījuma flīze (M)
        self.package_taken = False
        self.hideouts: set[tuple[int, int]] = set()  # slēptuves (H)
        self.player_start: tuple[int, int] = (0, 0)  # pikseļos

        guard_speed = GUARD_SPEEDS[level_number - 1]

        for row_index, row in enumerate(rows):
            for col_index, symbol in enumerate(row):
                pos = (col_index, row_index)
                if symbol == "#":
                    self.walls.add(pos)
                elif symbol == "x":
                    self.props.add(pos)
                elif symbol == "C":
                    self.coins.add(pos)
                elif symbol == "K":
                    self.key_pos = pos
                elif symbol == "D":
                    self.door_pos = pos
                elif symbol == "E":
                    self.exit_pos = pos
                elif symbol == "L":
                    self.lamps[pos] = 0.0  # 0.0 = lampa deg
                elif symbol == "M":
                    self.package_pos = pos
                elif symbol == "H":
                    # Slēptuve NAV cieta flīze — uz tās var uzkāpt,
                    # interakcija ar tuvuma rādiusu (skat. game_state)
                    self.hideouts.add(pos)
                elif symbol == "P":
                    # Starts = hitboxa augšējais kreisais stūris:
                    # centrēts horizontāli, tuvu lauciņa apakšai
                    self.player_start = (
                        col_index * TILE_SIZE + (TILE_SIZE - PLAYER_HIT_W) // 2,
                        row_index * TILE_SIZE + TILE_SIZE - PLAYER_HIT_H - FEET_MARGIN,
                    )
                elif symbol == "G":
                    self.guards.append(Guard(col_index, row_index, True, guard_speed))
                elif symbol == "V":
                    self.guards.append(Guard(col_index, row_index, False, guard_speed))

        # Katrai lampai atrodam sienu, uz kuras tā stiprināta,
        # un gaismas virzienu (prom no sienas telpā)
        self.lamp_info: dict[tuple[int, int], tuple] = {}
        for lamp in self.lamps:
            self.lamp_info[lamp] = self._compute_lamp_mount(*lamp)

    def _compute_lamp_mount(self, col: int, row: int) -> tuple:
        """Atgriež (sienas flīze, gaismas virziens) — gaisma prom no sienas.

        Ja lampai vairākas sienas kaimiņos (stūris), ņem to, kuras
        virzienā ir garākā brīvā flīžu līnija — tā gaisma spīd telpas
        dziļumā, nevis stūrī. Pie vienāda garuma horizontālās sienas
        (virs/apakšā) iet pirmās.
        """
        candidates = []
        for dc, dr in ((0, -1), (0, 1), (-1, 0), (1, 0)):  # horizontālās pirmās
            wall = (col + dc, row + dr)
            if wall in self.walls:
                candidates.append((wall, (-dc, -dr)))
        best, best_len = None, -1
        for wall, (dx, dy) in candidates:
            length = 0
            c, r = col + dx, row + dy
            while length < 10 and not self.is_solid_tile(c, r):
                length += 1
                c += dx
                r += dy
            if length > best_len:
                best, best_len = (wall, (dx, dy)), length
        if best is None:
            # Nav nevienas sienas kaimiņos (karšu tests to aizliedz) — rezervē uz leju
            return (None, (0, 1))
        return best

    def lamp_light_origin(self, lamp_pos: tuple[int, int]) -> tuple[float, float]:
        """Gaismas sākumpunkts pie sienas iekšējās malas (ne flīzes centrā),
        lai siena nenobloķētu pašu staru."""
        col, row = lamp_pos
        _, (dx, dy) = self.lamp_info[lamp_pos]
        return (col * TILE_SIZE + TILE_SIZE / 2 - dx * TILE_SIZE / 2,
                row * TILE_SIZE + TILE_SIZE / 2 - dy * TILE_SIZE / 2)

    def point_in_lamp_light(self, lamp_pos: tuple[int, int],
                            px: float, py: float) -> bool:
        """Vai punkts (px, py) ir lampas gaismas zonā.

        Zona = 110° sektors gaismas virzienā + redzeslīnija (sienas bloķē).
        To pašu zonu zīmē klients, tāpēc redzamais un EXPOSURE sakrīt.
        Izslēgta lampa neapdraud.
        """
        if self.lamps.get(lamp_pos, 1.0) > 0:
            return False  # izslēgta lampa neapdraud
        _, (dx, dy) = self.lamp_info[lamp_pos]
        ox, oy = self.lamp_light_origin(lamp_pos)
        vx, vy = px - ox, py - oy
        distance = math.hypot(vx, vy)
        if distance > s.LIGHT_RADIUS:
            return False
        if distance > 1e-6:
            # Sektora pārbaude: leņķis starp staru un lampas virzienu
            cos_angle = (vx * dx + vy * dy) / distance
            limit = math.cos(math.radians(s.LAMP_LIGHT_HALF_ANGLE))
            if cos_angle < limit:
                return False
        # Redzeslīnija: ejam pa ~8 px soļiem; ja stars trāpa cietā flīzē — ēnā
        steps = max(1, int(distance // 8))
        for i in range(1, steps + 1):
            t = i / steps
            col, row = self.tile_at_pixel(ox + vx * t, oy + vy * t)
            if self.is_solid_tile(col, row):
                return False
        return True

    def is_solid_tile(self, col: int, row: int) -> bool:
        """Vai uz šī lauciņa nedrīkst uzkāpt (siena, kaste, aizvērtas durvis, ārpus kartes)."""
        if col < 0 or row < 0 or col >= self.width or row >= self.height:
            return True
        if (col, row) in self.walls:
            return True
        if (col, row) in self.props:
            return True
        if not self.door_open and (col, row) == self.door_pos:
            return True
        return False

    def rect_hits_solid(self, x: float, y: float, width: int, height: int) -> bool:
        """Vai taisnstūris (pikseļos) aizskar kaut vienu cietu lauciņu."""
        left_col = int(x) // TILE_SIZE
        right_col = int(x + width - 1) // TILE_SIZE
        top_row = int(y) // TILE_SIZE
        bottom_row = int(y + height - 1) // TILE_SIZE
        for row in range(top_row, bottom_row + 1):
            for col in range(left_col, right_col + 1):
                if self.is_solid_tile(col, row):
                    return True
        return False

    def tile_at_pixel(self, x: float, y: float) -> tuple[int, int]:
        """Kurā kartes lauciņā atrodas šis pikselis."""
        return (int(x) // TILE_SIZE, int(y) // TILE_SIZE)
