"""Līmeņu kartes un Level klase.

Karte ir saraksts ar teksta rindām. Katrs simbols nozīmē vienu lauciņu:
    # - siena (nevar iet cauri)
    . - grīda (var iet)
    P - spēlētāja sākuma vieta
    C - monēta (+10 punkti)
    K - atslēga (+25 punkti, vajadzīga durvju atvēršanai)
    D - durvis (atver ar E, ja ir atslēga)
    E - izeja (līmeņa beigas)
    L - lampa (apgaismo laukumu ap sevi)
    x - kaste vai muca (dekoratīvs šķērslis, caur nevar iet)
    M - slepenais sūtījums (misijas objekts; bez tā izeja nedarbojas)
    H - slēptuve (metāla skapītis; ar E var paslēpties, flīze paliek brīva)
    G - sargs, kas kustas horizontāli
    V - sargs, kas kustas vertikāli
"""

from game.guard import Guard
from game import settings as s
from game.settings import (TILE_SIZE, GUARD_SPEEDS,
                           PLAYER_HIT_W, PLAYER_HIT_H, FEET_MARGIN)
import math

# --- TRĪS LĪMEŅU KARTES (24x16, grūtība aug: vairāk sargu, lampu un sienu) ---

LEVEL_MAPS = [
    # 1. līmenis — viegls: liela noliktavas zāle ar kastu grupām, 2 sargi
    # (viens patrulē galveno zāli, otrs austrumu spārnā pie durvīm),
    # 6 lampas pie eju krustojumiem, 5 monētas.
    # Atslēga dienvidrietumu istabā (ieleja (3,11)), sūtījums —
    # dienvidu vidējā istabā (ieleja (12,11)); katrai istabai sava lampa.
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
        "#CH....G.......#L......#",
        "###.########.########D##",
        "#.......#.....xx...#...#",
        "#L.K....#L....xx...#.E.#",
        "#.........M.....C..#...#",
        "########################",
    ],
    # 2. līmenis — vidējs: vairākas telpas, garas patruļu līnijas,
    # 3 sargi (divi vertikālie sargā ZA un austrumu koridorus, viens
    # horizontālais lielajā dienvidu zālē), 5 lampas, 5 monētas.
    # Atslēga ZA istabā (vienīgā ieleja (18,5), lampa (20,1) virs tās),
    # sūtījums dienvidu zālē pie lampas (22,12). Izejas telpa
    # dienvidrietumos aiz durvīm.
    [
        "########################",
        "#P....#...C...#.....L..#",
        "#.....#.V.....#..xxK...#",
        "#H........xx..#..xx....#",
        "#L........xx..#.......C#",
        "#.....#L.......###.#####",
        "#C....#.......####..####",
        "#.....#................#",
        "#..xx....xx.....xx...V.#",
        "#..xxH...xx..C..xx.....#",
        "#.....G.......L........#",
        "##D##.############.#####",
        "#...#.........xxH....ML#",
        "#.E.#.........xx....C..#",
        "#...#..................#",
        "########################",
    ],
    # 3. līmenis — grūts: blīva noliktava ar daudzām kastu grupām,
    # 4 sargi (garo zāli sargā horizontālais, vēl trīs ZA, austrumu
    # un dienvidu rajonos), 7 lampas, 5 monētas.
    # Sūtījums dienvidrietumu istabā (ieleja (3,10), lampa (1,11)),
    # atslēga dienvidu vidējā istabā (ieleja (18,10), lampa (11,14)) —
    # divas atsevišķas istabas, katra ar savu lampu. Izeja aiz durvīm.
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
        self.props: set[tuple[int, int]] = set()  # kastes/mucas ('x') — cieta šķēršļi
        self.coins: set[tuple[int, int]] = set()
        self.lamps: dict[tuple[int, int], float] = {}  # lauciņš -> cik ilgi vēl izslēgta
        self.guards: list[Guard] = []
        self.key_pos: tuple[int, int] | None = None
        self.door_pos: tuple[int, int] | None = None
        self.door_open = False
        self.exit_pos: tuple[int, int] = (0, 0)
        self.package_pos: tuple[int, int] | None = None  # sūtījuma flīze (simbols M)
        self.package_taken = False   # vai sūtījums jau paņemts
        self.hideouts: set[tuple[int, int]] = set()  # slēptuves (simbols H, flīze paliek brīva)
        self.player_start: tuple[int, int] = (0, 0)  # pikseļos (kreisais augšējais stūris)

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
                    self.lamps[pos] = 0.0  # 0.0 nozīmē: lampa deg
                elif symbol == "M":
                    self.package_pos = pos
                elif symbol == "H":
                    # Slēptuve NAV cieta flīze — uz tās var uzkāpt,
                    # interakcija notiek ar tuvuma rādiusu (skat. game_state)
                    self.hideouts.add(pos)
                elif symbol == "P":
                    # Sākuma vieta ir hitboxa augšējais kreisais stūris:
                    # centrēts horizontāli, tuvu lauciņa apakšai ("kājas")
                    self.player_start = (
                        col_index * TILE_SIZE + (TILE_SIZE - PLAYER_HIT_W) // 2,
                        row_index * TILE_SIZE + TILE_SIZE - PLAYER_HIT_H - FEET_MARGIN,
                    )
                elif symbol == "G":
                    self.guards.append(Guard(col_index, row_index, True, guard_speed))
                elif symbol == "V":
                    self.guards.append(Guard(col_index, row_index, False, guard_speed))

        # Lampu stiprinājumi: katrai lampai atrodam sienu, uz kuras tā
        # piestiprināta, un gaismas virzienu (prom no sienas, telpā).
        # lamp_info[lampas_flīze] = (sienas_flīze, (dx, dy))
        self.lamp_info: dict[tuple[int, int], tuple] = {}
        for lamp in self.lamps:
            self.lamp_info[lamp] = self._compute_lamp_mount(*lamp)

    def _compute_lamp_mount(self, col: int, row: int) -> tuple:
        """Izvēlas, uz kuras kaimiņu sienas lampa ir stiprināta.

        Atgriež (sienas_flīze, gaismas_virziens). Gaismas virziens ir
        pretējs sienas virzienam: siena virs lampas -> gaisma uz leju (0,1),
        siena apakšā -> uz augšu (0,-1), siena pa kreisi -> pa labi (1,0),
        siena pa labi -> pa kreisi (-1,0).

        Ja lampai ir VAIRĀKAS sienas kaimiņos (stūris), izvēlamies to sienu,
        kuras gaismas virzienā ir garākā brīvā flīžu līnija — tā gaisma
        spīd telpas dziļumā (parasti tieši uz priekšmetu), nevis stūrī.
        Pie vienāda garuma uzvar agrākā kandidātu secībā: vispirms
        horizontālās sienas (virs/apakšā), tad vertikālās (kreisā/labā).
        """
        candidates = []
        for dc, dr in ((0, -1), (0, 1), (-1, 0), (1, 0)):  # horizontālās sienas pirmās
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
            # Lampai nav nevienas sienas kaimiņos (karšu tests to aizliedz) —
            # rezervē: spīd uz leju, stiprinājuma siena nav zināma.
            return (None, (0, 1))
        return best

    def lamp_light_origin(self, lamp_pos: tuple[int, int]) -> tuple[float, float]:
        """Gaismas sākumpunkts pikseļos — pie stiprinājuma sienas IEKŠĒJĀS
        malas telpas pusē (ne flīzes centrā), lai siena nenobloķētu pašu staru.
        Punkts atrodas tieši uz kopējās malas starp lampas un sienas flīzi."""
        col, row = lamp_pos
        _, (dx, dy) = self.lamp_info[lamp_pos]
        return (col * TILE_SIZE + TILE_SIZE / 2 - dx * TILE_SIZE / 2,
                row * TILE_SIZE + TILE_SIZE / 2 - dy * TILE_SIZE / 2)

    def point_in_lamp_light(self, lamp_pos: tuple[int, int],
                            px: float, py: float) -> bool:
        """Vai punkts (px, py) pikseļos atrodas lampas gaismas zonā.

        Zona = sektors (110° konus, LIGHT_RADIUS rādiuss) lampas gaismas
        virzienā NO stiprinājuma sienas iekšējās malas, UN punktam jābūt
        brīvā redzeslīnijā no lampas (sienas/kastes/aizvērtas durvis
        gaismu bloķē). Izslēgta lampa neko neapgaismo.
        Šo pašu zonu zīmē arī klients (client/main.py), tāpēc redzamā
        gaisma un EXPOSURE detekcijas zona vienmēr sakrīt.
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
        # Redzeslīnija: ejam pa ~8 px soļiem no lampas līdz punktam;
        # ja stars šķērso cietu flīzi, punkts ir ēnā.
        steps = max(1, int(distance // 8))
        for i in range(1, steps + 1):
            t = i / steps
            col, row = self.tile_at_pixel(ox + vx * t, oy + vy * t)
            if self.is_solid_tile(col, row):
                return False
        return True

    def is_solid_tile(self, col: int, row: int) -> bool:
        """Vai uz šī lauciņa nedrīkst uzkāpt (siena, kaste, aizvērtas durvis vai ārpus kartes)."""
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
