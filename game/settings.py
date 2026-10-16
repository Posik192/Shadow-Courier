"""Visi skaitļi, ko spēle lieto — ja skolotājs prasa kaut ko mainīt, mainu šeit."""

# --- EKRĀNS ---
TILE_SIZE = 48        # viena kartes lauciņa izmērs pikseļos

# --- HITBOXI ---
# Hitboxs ir mazs un plakans "pie kājām", nevis viss sprite — citādi
# garām kastēm un sienām normāli nepaiet. player_x un guard.x ir
# hitboxa augšējais kreisais stūris.
PLAYER_HIT_W = 24     # spēlētāja hitboxa platums
PLAYER_HIT_H = 14     # spēlētāja hitboxa augstums
GUARD_HIT_W = 26      # sarga hitboxa platums
GUARD_HIT_H = 14      # sarga hitboxa augstums
FEET_MARGIN = 4       # par cik pikseļiem hitboxs pacelts no lauciņa apakšas

# --- SPRITES (klients zīmē; sprite stāv uz hitboxa apakšas) ---
PLAYER_SPRITE = 64
GUARD_SPRITE = 72

# --- SPĒLĒTĀJS ---
PLAYER_SPEED = 200    # pikseļi sekundē — ja jāaiztiek, mainu šeit
START_LIVES = 3       # HUD atmiņai; noķeršana tagad = uzreiz game over

# --- LAMPAS GAISMA IZSAUC TRAUKSMI (1. mehānika) ---
LIGHT_RADIUS = 120        # lampas detect rādiuss — ja skolotājs prasa, mainu šeit
LAMP_DETECT_TIME = 0.8    # 1. līmenis: cik ilgi jāstāv gaismā līdz trauksmei
# Grūtākajos līmeņos laiks ēnā ir īsāks (tā solīts spēles tabulā):
LAMP_DETECT_TIMES = [0.8, 0.7, 0.6]  # sekundes pa līmeņiem 1, 2, 3
LAMP_LIGHT_HALF_ANGLE = 55  # lampas sektora puse (kopā 110° konuss)

# --- LAMPU ATSLĒGŠANA (2. mehānika) ---
LAMP_DISABLE_RANGE = 150  # no cik tālu ar Space var izslēgt lampu — mainu šeit
LAMP_OFF_TIME = 5.0       # cik sekundes lampa paliek izslēgta
LAMP_COOLDOWN = 8.0       # cik ilgi jāgaida, līdz var atkal izslēgt

# --- 3. FĀZE: sūtījums, slēptuves, vērtējumi ---
INTERACT_RADIUS = 28      # cik tuvu jābūt, lai ar E paņemtu sūtījumu vai paslēptos
EXPOSURE_DECAY_TIME = 1.0 # par cik sekundēm EXPOSURE josla nokrīt līdz 0
MISSION_TEXT_TIME = 2.0   # cik ilgi rāda misijas tekstu līmeņa sākumā
# Misijas teksti pa līmeņiem (ekrānā, angliski)
MISSION_TEXTS = [
    "MISSION 01: Retrieve the encrypted package.",
    "MISSION 02: Recover the parcel from the security wing.",
    "MISSION 03: Escape the loading bay with the package.",
]
# Laika robežas S vērtējumam katram līmenim — ja lēnāk, S vairs nav
RANK_S_TIME = [60, 90, 120]

# --- SARGI ---
GUARD_SPEEDS = [80, 110, 140]  # sarga ātrums katram līmenim (px/sek)

# --- SARGU AI ---
FLASHLIGHT_WARNING_TIME = 1.30  # cik ilgi sargs brīdina, pirms sāk dzīties
SEARCH_TIME = 6.0               # cik ilgi meklē ap pēdējo redzēto vietu
CHASE_SPEED_MULT = 1.15         # dzīšanās ātruma reizinātājs
PATROL_PAUSE_MIN = 0.3          # īsākā apstāšanās patruļas punktā
PATROL_PAUSE_MAX = 1.0          # garākā apstāšanās
PATROL_MEMORY = 4               # cik pēdējos patruļas mērķus sargs neizvēlas
SEARCH_RADIUS_MIN = 3           # meklēšanas punkti ne tuvāk par tik flīzēm
SEARCH_RADIUS_MAX = 6           # un ne tālāk par tik
SEARCH_POINT_COUNT_MIN = 3      # cik meklēšanas punktus izvēlas (min)
SEARCH_POINT_COUNT_MAX = 5      # (max)
GUARD_LIGHT_RADIUS = 150        # sarga luktura attālums (pikseļi)
GUARD_CONE_ANGLE = 32           # luktura konusa puse (grādi)
CHASE_REPLAN_TIME = 0.25        # cik bieži dzīšanās laikā pārplāno ceļu
ALERT_ICON_TIME = 1.0           # cik ilgi virs sarga rāda sarkano "!"

# --- PUNKTI ---
COIN_POINTS = 10              # par monētu
KEY_POINTS = 25               # par atslēgu
LEVEL_BONUS = 100             # par līmeņa pabeigšanu
TIME_BONUS_PER_SECOND = 2     # par katru ietaupītu sekundi
LEVEL_TIME_LIMIT = 120.0      # ja ātrāk par šo, dabū laika bonusu
