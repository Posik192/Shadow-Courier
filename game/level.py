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
    G - sargs, kas kustas horizontāli
    V - sargs, kas kustas vertikāli
"""

from game.guard import Guard
from game.settings import TILE_SIZE, GUARD_SPEEDS

# --- TRĪS LĪMEŅU KARTES (grūtība aug: vairāk sargu, lampu un sienu) ---

LEVEL_MAPS = [
    # 1. līmenis — viegls: viens sargs sargā apakšējo koridoru
    [
        "################",
        "#P..C.....#...x#",
        "#.###.###.#.##.#",
        "#...#...#...#..#",
        "##..#.#.###.#..#",
        "#...#L#.....#..#",
        "#...#.#####.#..#",
        "#.###....L#.#.x#",
        "#..C..###.#.#..#",
        "#.####..#...####",
        "#..G.K..C...DE.#",
        "################",
    ],
    # 2. līmenis — vidējs: divas lampas, sargs sargā durvju pieeju
    [
        "################",
        "#P....#.....C..#",
        "#.##..#..####..#",
        "#..#.....#L....#",
        "#..#.###.#.###.#",
        "#C.#.#...#...#.#",
        "#..#.#.###.#.#.#",
        "##.#.#.....#.#.#",
        "#..L.#####.#..x#",
        "#x###......#####",
        "#..K..#...G.DE.#",
        "################",
    ],
    # 3. līmenis — grūts: divi sargi, izeju sargā durvis (vajag atslēgu)
    [
        "################",
        "#P.x#..C....#..#",
        "#.#.#.#####.#..#",
        "#.#...#...#L#..#",
        "#.#####.#.#.#.C#",
        "#C....#.#.#.#..#",
        "#.###.#.#.#.##.#",
        "#...#.#.G.#....#",
        "###.#.#####.##x#",
        "#...#..L...V.###",
        "#..K..##.###DE.#",
        "################",
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
                elif symbol == "P":
                    # Spēlētājs sākas lauciņa centrā (pārvēršam pikseļos)
                    self.player_start = (
                        col_index * TILE_SIZE + (TILE_SIZE - 32) // 2,
                        row_index * TILE_SIZE + (TILE_SIZE - 32) // 2,
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
