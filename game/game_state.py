"""Spēles stāvoklis — visa spēles loģika vienā klasē.

Šis fails ir spēles "smadzenes": kustība, sadursmes, punkti, līmeņi.
Šeit APZINĀTI nav pygame — klasi var pārbaudīt arī bez loga.
Klients (client/main.py) tikai nolasa taustiņus un uzzīmē šo stāvokli.
"""

import math

from game import settings as s
from game.level import Level, LEVEL_MAPS
from game.guard import STATE_PATROL
from game.rank import calculate_rank

# Iespējamie spēles stāvokļi
STATUS_PLAYING = "playing"
STATUS_GAME_OVER = "game_over"
STATUS_WON = "won"
STATUS_LEVEL_COMPLETE = "level_complete"  # līmenis izpildīts, gaida Enter


class GameState:
    """Viss, kas notiek spēlē: spēlētājs, sargi, punkti, līmenis."""

    def __init__(self) -> None:
        """Sāk jaunu spēli no 1. līmeņa ar 0 punktiem."""
        self.score = 0
        self.lives = s.START_LIVES
        self.level_number = 1
        self.status = STATUS_PLAYING
        self.game_over_reason = ""  # kāpēc spēle beidzās (sargs noķēra)
        self.level_stats = {}       # pēdējā pabeigtā līmeņa statistika
        self.alert_count = 0        # cik lampas trauksmes izsauktas (fāzes 3 āķis)
        self.load_level(1)

    def load_level(self, number: int) -> None:
        """Ielādē līmeni un uzliek spēlētāju sākuma vietā."""
        self.level_number = number
        self.level = Level(LEVEL_MAPS[number - 1], number)
        self.player_x, self.player_y = self.level.player_start
        self.has_key = False
        self.lamp_detect_timer = 0.0  # cik ilgi spēlētājs jau stāv lampas gaismā
        self.lamp_exposure = 0.0      # 0..1 — cik tuvu trauksmei (HUD un fāzes 3 āķis)
        self.lamp_cooldown = 0.0      # cik ilgi vēl nevar atslēgt lampu
        self.level_time = 0.0         # cik ilgi spēlē šo līmeni (laika bonusam)
        self.coins_collected = 0      # paņemtās monētas šajā līmenī (HUD rādīšanai)
        self.alert_count = 0          # izsauktās trauksmes šajā līmenī (rangam)
        self.hidden = False           # vai kurjers šobrīd paslēpies slēptuvē
        self.mission_text_timer = s.MISSION_TEXT_TIME  # misijas teksts ekrānā
        self.level_start_score = self.score  # punkti līmeņa sākumā (RETRY tos atjauno)
        self.message = ""             # paziņojums spēlētājam (piem. "Vajag atslēgu!")

    def _caught(self) -> None:
        """Sargs fiziski pieskāries spēlētājam — spēle uzreiz beidzas.

        Dzīvības paliek tikai HUD atmiņai; TRY AGAIN ekrāns tās atjauno.
        """
        self.status = STATUS_GAME_OVER
        self.game_over_reason = "A guard spotted you."

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
        if self.status != STATUS_PLAYING:
            return  # sargs noķēra — tālāk šajā kadrā neko neskaitām
        self._check_lamp_alert(dt)

        if disable_lamp and not self.hidden:
            self._disable_nearest_lamp()  # paslēpies lampu izslēgt nevar
        if interact:
            self._interact()

        self._check_exit()

    # --- Atsevišķas mazas metodes katram noteikumam ---

    def _update_timers(self, dt: float) -> None:
        """Samazina visus taimerus (lampu izslēgšana, cooldown, misijas teksts)."""
        if self.lamp_cooldown > 0:
            self.lamp_cooldown = max(0.0, self.lamp_cooldown - dt)
        if self.mission_text_timer > 0:
            self.mission_text_timer = max(0.0, self.mission_text_timer - dt)
        for lamp in self.level.lamps:
            if self.level.lamps[lamp] > 0:
                self.level.lamps[lamp] = max(0.0, self.level.lamps[lamp] - dt)

    def _move_player(self, move_x: int, move_y: int, dt: float) -> None:
        """Pabīda spēlētāju, bet neļauj iet caur sienām.

        Kustību dala pa asīm: vispirms X, tad Y. Tā var slīdēt gar sienu,
        pat ja spiež pa diagonāli. Sadursmēm lieto hitboxu "pie kājām",
        nevis visu sprite — tā var normāli paiet garām kastēm.
        Paslēpies slēptuvē (hidden) kurjers nekustas — WASD ignorējas.
        """
        if self.hidden:
            return
        new_x = self.player_x + move_x * s.PLAYER_SPEED * dt
        if not self.level.rect_hits_solid(new_x, self.player_y,
                                          s.PLAYER_HIT_W, s.PLAYER_HIT_H):
            self.player_x = new_x

        new_y = self.player_y + move_y * s.PLAYER_SPEED * dt
        if not self.level.rect_hits_solid(self.player_x, new_y,
                                          s.PLAYER_HIT_W, s.PLAYER_HIT_H):
            self.player_y = new_y

    def player_center(self) -> tuple[float, float]:
        """Hitboxa centra punkts pikseļos (vajadzīgs attālumu mērīšanai)."""
        return (self.player_x + s.PLAYER_HIT_W / 2,
                self.player_y + s.PLAYER_HIT_H / 2)

    def _collect_coins(self) -> None:
        """Paņem monētu, ja spēlētājs uz tās uzkāpj. Paslēpies nevar vākt."""
        if self.hidden:
            return
        tile = self.level.tile_at_pixel(*self.player_center())
        if tile in self.level.coins:
            self.level.coins.remove(tile)
            self.score += s.COIN_POINTS
            self.coins_collected += 1

    def _update_guards(self, dt: float) -> None:
        """Kustina sargus un pārbauda, vai kāds fiziski noķēris spēlētāju."""
        # Paslēpies spēlētājs sargiem ir neredzams: padodam None,
        # tad guard._can_see_player vienmēr atgriež False.
        player_center = None if self.hidden else self.player_center()
        for guard in self.level.guards:
            guard.update(dt, self.level, player_center)
            # Paslēpies = drošs: pat ja sargs stāv uz tās pašas vietas,
            # noķeršana nenotiek (hitboxu pārbaudi izlaižam).
            if self.hidden:
                continue
            if self._rects_overlap(self.player_x, self.player_y,
                                   s.PLAYER_HIT_W, s.PLAYER_HIT_H,
                                   guard.x, guard.y,
                                   s.GUARD_HIT_W, s.GUARD_HIT_H):
                self._caught()
                return  # viena noķeršana uz kadru ir gana

    @staticmethod
    def _rects_overlap(ax: float, ay: float, aw: int, ah: int,
                       bx: float, by: float, bw: int, bh: int) -> bool:
        """Vai divi taisnstūri pārklājas (sadursmes pārbaude)."""
        return (ax < bx + bw and ax + aw > bx
                and ay < by + bh and ay + ah > by)

    def _check_lamp_alert(self, dt: float) -> None:
        """1. mehānika: lampas gaisma izsauc sargu trauksmi (vairs nenoņem dzīvību).

        Ja spēlētāja hitboxa centrs nepārtraukti uzturas kādas DEDZOŠAS
        lampas gaismas zonā, EXPOSURE josla piepildās LAMP_DETECT_TIME
        sekundēs; pie pilnas joslas visi sargi pāriet LAMP_ALERT stāvoklī.
        Ārpus gaismas trauksmes taimeris atiestatās uzreiz, bet EXPOSURE
        josla krīt lēnām — līdz 0 par EXPOSURE_DECAY_TIME sekundēm.
        Paslēpies slēptuvē (hidden) exposure neaug un trauksme nenotiek.
        Kamēr kāda trauksme jau rit (sargi nav PATROL), taimeris nekrājas —
        tā viena un tā pati trauksme netiek palaista katrā kadrā.
        """
        alarm_active = any(guard.state != STATE_PATROL
                           for guard in self.level.guards)
        in_light = self._player_in_light() and not self.hidden
        if in_light and not alarm_active:
            self.lamp_detect_timer += dt
            if self.lamp_detect_timer >= s.LAMP_DETECT_TIME:
                self._raise_lamp_alarm()
        else:
            self.lamp_detect_timer = 0.0  # ārā no gaismas taimeris atiestatās
        # EXPOSURE josla: gaismā aug līdz 1.0 par 0.8 s, ārpus krīt par ~1.0 s
        if in_light:
            self.lamp_exposure = min(1.0, self.lamp_exposure
                                     + dt / s.LAMP_DETECT_TIME)
        else:
            self.lamp_exposure = max(0.0, self.lamp_exposure
                                     - dt / s.EXPOSURE_DECAY_TIME)

    def _raise_lamp_alarm(self) -> None:
        """Izsauc trauksmi: visi sargi skrien uz spēlētāja pašreizējo vietu."""
        position = self.player_center()
        for guard in self.level.guards:
            guard.start_lamp_alert(position, self.level)
        self.alert_count += 1  # fāzes 3 āķis: trauksmju skaitītājs
        self.lamp_detect_timer = 0.0
        self.lamp_exposure = 0.0
        self.message = "Sargi pamanīja tevi lampas gaismā!"

    def _player_in_light(self) -> bool:
        """Vai spēlētāja centrs šobrīd atrodas kādas DEDZOŠAS lampas zonā."""
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

    # --- Tuvuma pārbaudes interakcijām (izmanto arī klients promptiem) ---

    def package_in_range(self) -> bool:
        """Vai sūtījumu šobrīd var paņemt (hitboxa centrs tuvu flīzes centram)."""
        if self.level.package_pos is None or self.level.package_taken:
            return False
        px, py = self.player_center()
        mx = self.level.package_pos[0] * s.TILE_SIZE + s.TILE_SIZE / 2
        my = self.level.package_pos[1] * s.TILE_SIZE + s.TILE_SIZE / 2
        return math.hypot(px - mx, py - my) <= s.INTERACT_RADIUS

    def hideout_in_range(self) -> tuple[int, int] | None:
        """Atgriež tuvākās slēptuves flīzi, ja tā ir INTERACT_RADIUS attālumā."""
        px, py = self.player_center()
        for col, row in self.level.hideouts:
            hx = col * s.TILE_SIZE + s.TILE_SIZE / 2
            hy = row * s.TILE_SIZE + s.TILE_SIZE / 2
            if math.hypot(px - hx, py - hy) <= s.INTERACT_RADIUS:
                return (col, row)
        return None

    def _interact(self) -> None:
        """E taustiņš: slēptuve, sūtījums, atslēga vai durvis.

        Paslēpies slēptuvē E vienmēr nozīmē "iznāk" — citas darbības
        (vākt priekšmetus, atvērt durvis) paslēpies nevar.
        """
        px, py = self.player_center()
        # Iziešana no slēptuves
        if self.hidden:
            self.hidden = False
            self.message = "You left the hideout."
            return
        # Sūtījuma paņemšana (misijas objekts)
        if self.package_in_range():
            self.level.package_taken = True
            self.message = "Package retrieved!"
            return
        # Paslēpšanās slēptuvē
        if self.hideout_in_range() is not None:
            self.hidden = True
            self.message = "Hidden!"
            return
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
        """Ja spēlētājs sasniedz izeju — līmenis izpildīts vai uzvara.

        Bez paņemta sūtījuma izeja nedarbojas — līmenis turpinās.
        """
        tile = self.level.tile_at_pixel(*self.player_center())
        if tile != self.level.exit_pos:
            return
        if not self.level.package_taken:
            self.message = "MISSION ITEM REQUIRED"
            return
        # Laika bonuss: jo ātrāk pabeidz, jo vairāk punktu
        time_left = max(0.0, s.LEVEL_TIME_LIMIT - self.level_time)
        self.score += s.LEVEL_BONUS + int(time_left * s.TIME_BONUS_PER_SECOND)
        # Līmeņa vērtējums (S/A/B/C) pēc monētām, trauksmēm un laika
        coins_total = self.coins_collected + len(self.level.coins)
        rank = calculate_rank(self.coins_collected, coins_total,
                              self.alert_count, self.level_time,
                              self.level_number)
        # Līmeņa statistika "līmenis izpildīts" ekrānam (un rangam WIN gadījumā)
        self.level_stats = {
            "coins": self.coins_collected,
            "coins_total": coins_total,
            "time": self.level_time,
            "score": self.score,
            "alerts": self.alert_count,
            "rank": rank,
        }
        if self.level_number >= len(LEVEL_MAPS):
            self.status = STATUS_WON
            return
        # Nav pēdējais līmenis: apstājamies uz "līmenis izpildīts" ekrāna.
        # Klients parādīs statistiku un pēc Enter izsauks next_level().
        self.status = STATUS_LEVEL_COMPLETE

    def next_level(self) -> None:
        """Ielādē nākamo līmeni un turpina spēli (Enter LEVEL COMPLETE ekrānā)."""
        self.load_level(self.level_number + 1)
        self.status = STATUS_PLAYING
