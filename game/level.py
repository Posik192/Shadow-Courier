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
from game.settings import (TILE_SIZE, GUARD_SPEEDS,
                           PLAYER_HIT_W, PLAYER_HIT_H, FEET_MARGIN)

# --- TRĪS LĪMEŅU KARTES (24x16, grūtība aug: vairāk sargu, lampu un sienu) ---

LEVEL_MAPS = [
    # 1. līmenis — viegls: liela noliktavas zāle ar kastu grupām, 2 sargi
    # (viens patrulē galveno zāli, otrs austrumu spārnā pie durvīm),
    # 4 lampas pie eju krustojumiem, 5 monētas. Atslēga dienvidrietumu
    # stūrī — tālu no izejas telpas durvīm dienvidaustrumos.
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
        "#CH....G.......#.L.....#",
        "###.########.########D##",
        "#.......#.....xx...#...#",
        "#..K....#.....xx...#.E.#",
        "#......M#.......C..#...#",
        "########################",
    ],
    # 2. līmenis — vidējs: vairākas telpas, garas patruļu līnijas,
    # 3 sargi (divi vertikālie sargā ZA un austrumu koridorus, viens
    # horizontālais lielajā dienvidu zālē), 4 lampas, 5 monētas.
    # Izejas telpa dienvidrietumos, atslēga ZA augšējā labajā stūrī.
    [
        "########################",
        "#P....#...C...#....K...#",
        "#.....#.V.....#..xx....#",
        "#H........xx..#..xx....#",
        "#L........xx..#.......C#",
        "#.....#L........L......#",
        "#C....#.......####..####",
        "#.....#................#",
        "#..xx....xx.....xx...V.#",
        "#..xxH...xx..C..xx.....#",
        "#.....G........L.......#",
        "##D##.############.#####",
        "#...#.........xxH......#",
        "#.E.#.........xx....C..#",
        "#...#................M.#",
        "########################",
    ],
    # 3. līmenis — grūts: blīva noliktava ar daudzām kastu grupām,
    # 4 sargi (atslēgas telpu sargā vertikālais sargs, garo zāli —
    # horizontālais, vēl divi austrumu un dienvidu rajonos),
    # 5 lampas pie krustojumiem, 5 monētas. Atslēga tālu no durvīm.
    [
        "########################",
        "#P.....#......#.....K..#",
        "#......#..xx..#.Vxx....#",
        "#......#..xx..#..xx....#",
        "#..L........C.........L#",
        "####.#####.###.........#",
        "#....Lxx...L.L.........#",
        "#.....xx.........xx...C#",
        "#..........G...........#",
        "#C......xx..........V..#",
        "###.##############.#####",
        "#......C..#........#...#",
        "#M.Hxx....#..xx....#H..#",
        "#.K.xx...H#..xx....D.E.#",
        "#....G....#......C.#...#",
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
