"""Spēles stāvoklis — visa spēles loģika vienā klasē.

Šis fails ir spēles "smadzenes": kustība, sadursmes, punkti, līmeņi.
Šeit APZINĀTI nav pygame — klasi var pārbaudīt arī bez loga.
Klients (client/main.py) tikai nolasa taustiņus un uzzīmē šo stāvokli.
"""

import math

from game import settings as s
from game.level import Level, LEVEL_MAPS
from game.guard import GUARD_SIZE

# Iespējamie spēles stāvokļi
STATUS_PLAYING = "playing"
STATUS_GAME_OVER = "game_over"
STATUS_WON = "won"


class GameState:
    """Viss, kas notiek spēlē: spēlētājs, sargi, punkti, līmenis."""

    def __init__(self) -> None:
        """Sāk jaunu spēli no 1. līmeņa ar 0 punktiem."""
        self.score = 0
        self.level_number = 1
        self.status = STATUS_PLAYING
        self.game_over_reason = ""  # kāpēc spēle beidzās (sargs vai gaisma)
        self.load_level(1)

    def load_level(self, number: int) -> None:
        """Ielādē līmeni un uzliek spēlētāju sākuma vietā."""
        self.level_number = number
        self.level = Level(LEVEL_MAPS[number - 1], number)
        self.player_x, self.player_y = self.level.player_start
        self.has_key = False
        self.light_timer = 0.0    # cik ilgi spēlētājs jau stāv gaismā
        self.lamp_cooldown = 0.0  # cik ilgi vēl nevar atslēgt lampu
        self.level_time = 0.0     # cik ilgi spēlē šo līmeni (laika bonusam)
        self.message = ""         # paziņojums spēlētājam (piem. "Vajag atslēgu!")

    # --- Galvenā metode: klients to izsauc 60 reizes sekundē ---

    def update(self, dt: float, move_x: int, move_y: int,
               disable_lamp: bool, interact: bool) -> None:
        """Viens spēles solis.

        dt — cik sekundes pagājušas kopš iepriekšējā kadra.
        move_x, move_y — kustības virziens: -1, 0 vai 1 (no taustiņiem).
        disable_lamp — vai nospiests Space (atslēgt lampu).
        interact — vai nospiests E (paņemt atslēgu / atvērt durvis).
        """
        if self.status != STATUS_PLAYING:
            return

        self.level_time += dt
        self._update_timers(dt)
        self._move_player(move_x, move_y, dt)
        self._collect_coins()
        self._update_guards(dt)
        self._check_light(dt)

        if disable_lamp:
            self._disable_nearest_lamp()
        if interact:
            self._interact()

        self._check_exit()

    # --- Atsevišķas mazas metodes katram noteikumam ---

    def _update_timers(self, dt: float) -> None:
        """Samazina visus taimerus (lampu izslēgšana un cooldown)."""
        if self.lamp_cooldown > 0:
            self.lamp_cooldown = max(0.0, self.lamp_cooldown - dt)
        for lamp in self.level.lamps:
            if self.level.lamps[lamp] > 0:
                self.level.lamps[lamp] = max(0.0, self.level.lamps[lamp] - dt)

    def _move_player(self, move_x: int, move_y: int, dt: float) -> None:
        """Pabīda spēlētāju, bet neļauj iet caur sienām.

        Kustību dala pa asīm: vispirms X, tad Y. Tā var slīdēt gar sienu,
        pat ja spiež pa diagonāli.
        """
        new_x = self.player_x + move_x * s.PLAYER_SPEED * dt
        if not self.level.rect_hits_solid(new_x, self.player_y, s.PLAYER_SIZE, s.PLAYER_SIZE):
            self.player_x = new_x

        new_y = self.player_y + move_y * s.PLAYER_SPEED * dt
        if not self.level.rect_hits_solid(self.player_x, new_y, s.PLAYER_SIZE, s.PLAYER_SIZE):
            self.player_y = new_y

    def player_center(self) -> tuple[float, float]:
        """Spēlētāja centra punkts pikseļos (vajadzīgs attālumu mērīšanai)."""
        return (self.player_x + s.PLAYER_SIZE / 2, self.player_y + s.PLAYER_SIZE / 2)

    def _collect_coins(self) -> None:
        """Paņem monētu, ja spēlētājs uz tās uzkāpj."""
        tile = self.level.tile_at_pixel(*self.player_center())
        if tile in self.level.coins:
            self.level.coins.remove(tile)
            self.score += s.COIN_POINTS

    def _update_guards(self, dt: float) -> None:
        """Kustina sargus un pārbauda, vai kāds noķēris spēlētāju."""
        for guard in self.level.guards:
            guard.update(dt, self.level.rect_hits_solid)
            if self._rects_overlap(self.player_x, self.player_y, s.PLAYER_SIZE,
                                   guard.x, guard.y, GUARD_SIZE):
                self.status = STATUS_GAME_OVER
                self.game_over_reason = "Sargs tevi noķēra!"

    @staticmethod
    def _rects_overlap(ax: float, ay: float, a_size: int,
                       bx: float, by: float, b_size: int) -> bool:
        """Vai divi kvadrāti pārklājas (sadursmes pārbaude)."""
        return (ax < bx + b_size and ax + a_size > bx
                and ay < by + b_size and ay + a_size > by)

    def _check_light(self, dt: float) -> None:
        """1. mehānika: ja spēlētājs par ilgu stāv gaismā, spēle beidzas."""
        if self._player_in_light():
            self.light_timer += dt
            if self.light_timer >= s.LIGHT_TIME_LIMIT:
                self.status = STATUS_GAME_OVER
                self.game_over_reason = "Pārāk ilgi stāvēji gaismā!"
        else:
            self.light_timer = 0.0  # ārā no gaismas taimeris atiestatās

    def _player_in_light(self) -> bool:
        """Vai spēlētājs šobrīd atrodas kādas DEDZOŠAS lampas gaismā."""
        px, py = self.player_center()
        for (col, row), off_timer in self.level.lamps.items():
            if off_timer > 0:
                continue  # izslēgtā lampa neapdraud
            lamp_x = col * s.TILE_SIZE + s.TILE_SIZE / 2
            lamp_y = row * s.TILE_SIZE + s.TILE_SIZE / 2
            distance = math.hypot(px - lamp_x, py - lamp_y)
            if distance <= s.LIGHT_RADIUS:
                return True
        return False

    def _disable_nearest_lamp(self) -> None:
        """2. mehānika: izslēdz tuvāko lampu uz īsu laiku (ar cooldown)."""
        if self.lamp_cooldown > 0:
            self.message = "Lampas slēdzis vēl uzlādējas!"
            return
        nearest = self._nearest_lamp()
        if nearest is None:
            self.message = "Nav lampas pietiekami tuvu!"
            return
        self.level.lamps[nearest] = s.LAMP_OFF_TIME
        self.lamp_cooldown = s.LAMP_COOLDOWN
        self.message = "Lampa izslēgta!"

    def _nearest_lamp(self) -> tuple[int, int] | None:
        """Atrod tuvāko lampu, kas ir pietiekami tuvu, lai to izslēgtu."""
        px, py = self.player_center()
        best_lamp = None
        best_distance = s.LAMP_DISABLE_RANGE
        for col, row in self.level.lamps:
            lamp_x = col * s.TILE_SIZE + s.TILE_SIZE / 2
            lamp_y = row * s.TILE_SIZE + s.TILE_SIZE / 2
            distance = math.hypot(px - lamp_x, py - lamp_y)
            if distance <= best_distance:
                best_distance = distance
                best_lamp = (col, row)
        return best_lamp

    def _interact(self) -> None:
        """E taustiņš: paņem atslēgu vai atver durvis (jāstāv blakus)."""
        px, py = self.player_center()
        # Atslēgu var paņemt, ja ir tuvumā (mazāk par pusotru lauciņu)
        if self.level.key_pos is not None:
            kx = self.level.key_pos[0] * s.TILE_SIZE + s.TILE_SIZE / 2
            ky = self.level.key_pos[1] * s.TILE_SIZE + s.TILE_SIZE / 2
            if math.hypot(px - kx, py - ky) < s.TILE_SIZE * 1.5:
                self.level.key_pos = None
                self.has_key = True
                self.score += s.KEY_POINTS
                self.message = "Paņēmi atslēgu!"
                return
        # Durvis var atvērt tikai ar atslēgu
        if self.level.door_pos is not None and not self.level.door_open:
            dx = self.level.door_pos[0] * s.TILE_SIZE + s.TILE_SIZE / 2
            dy = self.level.door_pos[1] * s.TILE_SIZE + s.TILE_SIZE / 2
            if math.hypot(px - dx, py - dy) < s.TILE_SIZE * 1.5:
                if self.has_key:
                    self.level.door_open = True
                    self.message = "Durvis atvērtas!"
                else:
                    self.message = "Vajag atslēgu!"

    def _check_exit(self) -> None:
        """Ja spēlētājs sasniedz izeju — nākamais līmenis vai uzvara."""
        tile = self.level.tile_at_pixel(*self.player_center())
        if tile != self.level.exit_pos:
            return
        # Laika bonuss: jo ātrāk pabeidz, jo vairāk punktu
        time_left = max(0.0, s.LEVEL_TIME_LIMIT - self.level_time)
        self.score += s.LEVEL_BONUS + int(time_left * s.TIME_BONUS_PER_SECOND)
        if self.level_number >= len(LEVEL_MAPS):
            self.status = STATUS_WON
        else:
            self.load_level(self.level_number + 1)
