"""Sargs ar stāvokļu sistēmu (mākslīgais intelekts).

Sargs vienmēr ir tieši vienā no pieciem stāvokļiem:

    PATROL              — iet uz nejaušiem kartes punktiem pa BFS ceļu
    LAMP_ALERT          — lampas trauksme: skrien uz pēdējo redzēto vietu
    SEARCH              — meklē apkārt pēdējai redzētajai vietai (6 sekundes)
    FLASHLIGHT_WARNING  — ierauga spēlētāju lukturī un apstājas (1.30 s)
    CHASE               — dzenās pakaļ spēlētājam, kamēr viņš redzams konusā

Visi taimeri tiek rēķināti ar dt (sekundes), nevis kadru skaitu.
x, y — hitboxa augšējais kreisais stūris (tāpat kā spēlētājam).
"""

import math
import random

from game import settings as s
from game.pathfind import find_path, reachable_tiles
from game.settings import TILE_SIZE, GUARD_HIT_W, GUARD_HIT_H, PLAYER_SPEED

# Sarga stāvokļi (virknes, lai testos un HUD viegli salīdzinātu)
STATE_PATROL = "PATROL"
STATE_LAMP_ALERT = "LAMP_ALERT"
STATE_SEARCH = "SEARCH"
STATE_WARNING = "FLASHLIGHT_WARNING"
STATE_CHASE = "CHASE"

# Varbūtība, ka sargs patruļas punktā apstājas uz mazu brīdi
PATROL_PAUSE_CHANCE = 0.5


def tile_hitbox_corner(col: int, row: int) -> tuple[float, float]:
    """Hitboxa augšējais kreisais stūris, ja hitboxa centrs ir lauciņa centrā."""
    return (col * TILE_SIZE + TILE_SIZE / 2 - GUARD_HIT_W / 2,
            row * TILE_SIZE + TILE_SIZE / 2 - GUARD_HIT_H / 2)


class Guard:
    """Viens sargs ar pozīciju, skata virzienu un stāvokļu mašīnu."""

    def __init__(self, col: int, row: int, horizontal: bool, speed: int) -> None:
        """Uzliek sargu uz lauciņa: hitboxs centrēts lauciņa vidū.

        horizontal vairs nenosaka patruļas veidu (G un V patrulē brīvi),
        to lieto tikai sākuma skata virzienam.
        """
        self.x, self.y = tile_hitbox_corner(col, row)
        self.speed = speed
        self.state = STATE_PATROL
        self.facing = (1.0, 0.0) if horizontal else (0.0, 1.0)
        self.path = []                 # atlikušie ceļa punkti (hitboxa stūri, pikseļi)
        self.patrol_memory = []        # pēdējie PATROL_MEMORY patruļas mērķi (lauciņi)
        self.pause_timer = 0.0         # cik ilgi vēl stāv patruļas punktā
        self.search_timer = 0.0        # cik ilgi vēl meklē (SEARCH)
        self.search_points = []        # meklēšanas punkti (lauciņi)
        self.warning_timer = 0.0       # cik ilgi vēl brīdina (FLASHLIGHT_WARNING)
        self.replan_timer = 0.0        # kad no jauna plānot dzīšanās ceļu (CHASE)
        self.alert_icon_timer = 0.0    # cik ilgi virs sarga rāda sarkano "!"
        self.last_known_position = (0.0, 0.0)  # kur pēdējo reizi redzēts spēlētājs
        self.moving = False            # vai šobrīd kustas (animācijai klientā)

    def center(self) -> tuple[float, float]:
        """Hitboxa centra punkts pikseļos."""
        return (self.x + GUARD_HIT_W / 2, self.y + GUARD_HIT_H / 2)

    # --- Galvenā metode: GameState to izsauc vienreiz katrā kadrā ---

    def update(self, dt: float, level,
               player_center: tuple[float, float] | None) -> None:
        """Viens domāšanas solis: redze, tad stāvokļa darbība.

        level zina karti (sienas, BFS), player_center — spēlētāja hitboxa
        centrs pikseļos vai None, ja spēlētājs paslēpies slēptuvē
        (tad sargs viņu nevar pamanīt).
        """
        if self.alert_icon_timer > 0:
            self.alert_icon_timer = max(0.0, self.alert_icon_timer - dt)

        seen = self._can_see_player(level, player_center)
        if seen:
            self.last_known_position = player_center

        if self.state == STATE_WARNING:
            self._update_warning(dt, level, player_center, seen)
            return
        if seen and self.state != STATE_CHASE:
            # Pirmoreiz ierauga spēlētāju lukturī — apstājas un brīdina
            self._start_warning()
            return

        if self.state == STATE_PATROL:
            self._update_patrol(dt, level)
        elif self.state == STATE_LAMP_ALERT:
            self._update_lamp_alert(dt, level)
        elif self.state == STATE_SEARCH:
            self._update_search(dt, level)
        elif self.state == STATE_CHASE:
            self._update_chase(dt, level, player_center, seen)

    # --- PATROL: nejauši mērķi pa visu karti ---

    def _update_patrol(self, dt: float, level) -> None:
        """Iet uz patruļas mērķi; sasniedzot — dažreiz apstājas un izvēlas jaunu."""
        if self.pause_timer > 0:
            self.pause_timer -= dt
            self.moving = False
            return
        if not self.path:
            self._choose_patrol_target(level)
        if self._follow_path(dt, level, self.speed):
            self.pause_timer = 0.0
            if random.random() < PATROL_PAUSE_CHANCE:
                self.pause_timer = random.uniform(s.PATROL_PAUSE_MIN,
                                                  s.PATROL_PAUSE_MAX)

    def _choose_patrol_target(self, level) -> tuple[int, int]:
        """Izvēlas nejaušu sasniedzamu brīvu lauciņu (ne no pēdējiem) un plāno ceļu."""
        start = self._current_tile()
        free = reachable_tiles(level.is_solid_tile, start)
        free.discard(start)
        candidates = [tile for tile in free if tile not in self.patrol_memory]
        if not candidates:
            candidates = list(free)  # ja visas vietas jau apstaigātas — drīkst atkārtot
        if not candidates:
            return start  # sargs iesprostots (nav kur iet) — stāv uz vietas
        target = random.choice(candidates)
        self.patrol_memory.append(target)
        if len(self.patrol_memory) > s.PATROL_MEMORY:
            self.patrol_memory.pop(0)
        self._plan_path_to(level, target)
        return target

    def _start_patrol(self, level) -> None:
        """Atgriežas patrulēšanā ar jaunu nejaušu mērķi."""
        self.state = STATE_PATROL
        self.path = []
        self._choose_patrol_target(level)

    # --- LAMP_ALERT: lampas trauksme (izsauc GameState) ---

    def start_lamp_alert(self, position: tuple[float, float], level) -> None:
        """Lampas trauksme: skrien uz vietu, kur spēlētājs stāvēja gaismā."""
        self.state = STATE_LAMP_ALERT
        self.last_known_position = position
        self.alert_icon_timer = s.ALERT_ICON_TIME
        self.pause_timer = 0.0
        self._plan_path_to(level, self._tile_of(position))

    def _update_lamp_alert(self, dt: float, level) -> None:
        """Skrien uz signāla vietu paātrinātā tempā; sasniedzot — SEARCH."""
        if not self.path:
            if not self._plan_path_to(level, self._tile_of(self.last_known_position)):
                self._start_search(level)  # signāla vieta nav sasniedzama
                return
        if self._follow_path(dt, level, self._chase_speed()):
            self._start_search(level)

    # --- SEARCH: meklēšana ap pēdējo redzēto vietu ---

    def _start_search(self, level) -> None:
        """Sāk meklēšanu: 3-5 nejauši punkti 3-6 flīžu rādiusā, laiks 6 s."""
        self.state = STATE_SEARCH
        self.search_timer = s.SEARCH_TIME
        self.path = []
        self._pick_search_points(level)

    def _pick_search_points(self, level) -> None:
        """Izvēlas nejaušus sasniedzamus punktus ap pēdējo redzēto vietu."""
        center = self._tile_of(self.last_known_position)
        start = self._current_tile()
        free = reachable_tiles(level.is_solid_tile, start)
        options = []
        for col, row in free:
            distance = math.hypot(col - center[0], row - center[1])
            if s.SEARCH_RADIUS_MIN <= distance <= s.SEARCH_RADIUS_MAX:
                options.append((col, row))
        count = random.randint(s.SEARCH_POINT_COUNT_MIN, s.SEARCH_POINT_COUNT_MAX)
        if len(options) < count:
            # Ja rādiusā par maz brīvo vietu — meklē jebkur sasniedzamā vietā
            options = [tile for tile in free if tile != start]
        random.shuffle(options)
        self.search_points = options[:count]

    def _update_search(self, dt: float, level) -> None:
        """Apstaigā meklēšanas punktus parastā ātrumā; pēc 6 s — PATROL."""
        self.search_timer -= dt
        if self.search_timer <= 0:
            self._start_patrol(level)
            return
        if not self.path:
            if not self.search_points:
                self._pick_search_points(level)  # punkti beidzās — meklē tālāk
            # Ja punkts nav sasniedzams — uzreiz ņem nākamo
            while self.search_points and not self.path:
                point = self.search_points.pop(0)
                self._plan_path_to(level, point)
            if not self.path:
                self._start_patrol(level)  # nav neviena sasniedzama punkta
                return
        self._follow_path(dt, level, self.speed)

    # --- FLASHLIGHT_WARNING un CHASE: luktura konuss ---

    def _start_warning(self) -> None:
        """Ierauga spēlētāju: apstājas un brīdina 1.30 s."""
        self.state = STATE_WARNING
        self.warning_timer = s.FLASHLIGHT_WARNING_TIME
        self.alert_icon_timer = s.ALERT_ICON_TIME
        self.path = []
        self.pause_timer = 0.0
        self.moving = False

    def _update_warning(self, dt: float, level,
                        player_center: tuple[float, float], seen: bool) -> None:
        """Stāv uz vietas. Pēc 1.30 s: ja spēlētājs vēl redzams — CHASE, citādi SEARCH."""
        self.moving = False
        if seen:
            self.last_known_position = player_center
        self.warning_timer -= dt
        if self.warning_timer <= 0:
            if seen:
                self._start_chase()
            else:
                self._start_search(level)

    def _start_chase(self) -> None:
        """Sāk dzīšanos — ceļu uz spēlētāju izplāno nākamajā solī."""
        self.state = STATE_CHASE
        self.replan_timer = 0.0

    def _update_chase(self, dt: float, level,
                      player_center: tuple[float, float], seen: bool) -> None:
        """Dzenas pakaļ, kamēr spēlētājs redzams; pazūd — SEARCH."""
        if not seen:
            self._start_search(level)
            return
        self.replan_timer -= dt
        if self.replan_timer <= 0:
            self.replan_timer = s.CHASE_REPLAN_TIME
            self._plan_path_to(level, self._tile_of(player_center))
        self._follow_path(dt, level, self._chase_speed())

    def _chase_speed(self) -> float:
        """Dzīšanās ātrums — vienmēr drusku lielāks par spēlētāja ātrumu."""
        return max(self.speed, PLAYER_SPEED) * s.CHASE_SPEED_MULT

    # --- Redze: luktura konuss un skata līnija ---

    def _can_see_player(self, level,
                        player_center: tuple[float, float] | None) -> bool:
        """Vai spēlētājs ir luktura konusā: tuvu, leņķī un bez sienas pa ceļam.

        Ja player_center ir None (spēlētājs paslēpies slēptuvē),
        sargs viņu nevar pamanīt — vienmēr False.
        """
        if player_center is None:
            return False
        gx, gy = self.center()
        px, py = player_center
        dx, dy = px - gx, py - gy
        distance = math.hypot(dx, dy)
        if distance > s.GUARD_LIGHT_RADIUS:
            return False
        if distance > 0:
            # Leņķis starp skata virzienu un virzienu uz spēlētāju
            angle_to_player = math.atan2(dy, dx)
            facing_angle = math.atan2(self.facing[1], self.facing[0])
            diff = abs((angle_to_player - facing_angle + math.pi)
                       % (2 * math.pi) - math.pi)
            if diff > math.radians(s.GUARD_CONE_ANGLE):
                return False
        return self._line_of_sight(level, gx, gy, px, py)

    @staticmethod
    def _line_of_sight(level, x0: float, y0: float,
                       x1: float, y1: float) -> bool:
        """Bresenham līnija pa lauciņiem: True, ja pa ceļam nav cietas flīzes."""
        col0, row0 = int(x0) // TILE_SIZE, int(y0) // TILE_SIZE
        col1, row1 = int(x1) // TILE_SIZE, int(y1) // TILE_SIZE
        dcol, drow = abs(col1 - col0), abs(row1 - row0)
        step_col = 1 if col1 > col0 else -1
        step_row = 1 if row1 > row0 else -1
        col, row = col0, row0
        error = dcol - drow
        while (col, row) != (col1, row1):
            if (col, row) != (col0, row0) and level.is_solid_tile(col, row):
                return False
            double_error = 2 * error
            if double_error > -drow:
                error -= drow
                col += step_col
            if double_error < dcol:
                error += dcol
                row += step_row
        return True

    # --- Kustība pa ceļu un plānošana ---

    def _current_tile(self) -> tuple[int, int]:
        """Lauciņš, kurā atrodas sarga hitboxa centrs."""
        return self._tile_of(self.center())

    @staticmethod
    def _tile_of(point: tuple[float, float]) -> tuple[int, int]:
        """Lauciņš, kurā atrodas šis pikseļu punkts."""
        return (int(point[0]) // TILE_SIZE, int(point[1]) // TILE_SIZE)

    def _plan_path_to(self, level, goal_tile: tuple[int, int]) -> bool:
        """Uzzīmē BFS ceļu uz mērķa lauciņu. Atgriež False, ja nav sasniedzams."""
        tiles = find_path(level.is_solid_tile, self._current_tile(), goal_tile)
        if tiles is None:
            self.path = []
            return False
        # Pirmo lauciņu (kurā jau stāvam) izlaižam; ceļš = hitboxa stūri
        self.path = [tile_hitbox_corner(col, row) for col, row in tiles[1:]]
        return True

    def _follow_path(self, dt: float, level, speed: float) -> bool:
        """Iet pa ceļa punktiem. Atgriež True, kad ceļš noiets līdz galam."""
        self.moving = False
        step = speed * dt  # cik pikseļus var noiet šajā kadrā
        while self.path and step > 0:
            tx, ty = self.path[0]
            dx, dy = tx - self.x, ty - self.y
            distance = math.hypot(dx, dy)
            if distance <= step:
                # Sasniegts ceļa punkts — atlikušo soli tērējam nākamajam
                self.x, self.y = tx, ty
                self.path.pop(0)
                step -= distance
                continue
            self._face(dx, dy)
            if not self._try_move(level, dx / distance * step,
                                  dy / distance * step):
                self.path = []  # iestrēga — nākamajā kadrā plānos no jauna
                return True
            step = 0
        return not self.path

    def _try_move(self, level, move_x: float, move_y: float) -> bool:
        """Pabīda sargu (vispirms X, tad Y), neļaujot iet caur sienām."""
        moved = False
        new_x = self.x + move_x
        if not level.rect_hits_solid(new_x, self.y, GUARD_HIT_W, GUARD_HIT_H):
            self.x = new_x
            moved = True
        new_y = self.y + move_y
        if not level.rect_hits_solid(self.x, new_y, GUARD_HIT_W, GUARD_HIT_H):
            self.y = new_y
            moved = True
        if moved:
            self.moving = True
        return moved

    def _face(self, dx: float, dy: float) -> None:
        """Pagriež skata virzienu kustības virzienā (stāvot paliek vecais)."""
        length = math.hypot(dx, dy)
        if length > 0:
            self.facing = (dx / length, dy / length)
