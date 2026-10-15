"""Spēles uzstādījumi.

ŠEIT maina visus skaitļus: ātrumu, punktus, gaismas ilgumu utt.
Ja skolotājs saka "ieliec 2x ātrāk" — maini PLAYER_SPEED šeit.
"""

# --- EKRĀNS ---
TILE_SIZE = 48        # viena kartes lauciņa izmērs pikseļos

# --- HITBOXI (sadursmju taisnstūri) ---
# Loģika lieto mazus plakanus hitboxus "pie kājām", nevis visu sprite,
# tāpēc spēlētājs var normāli paiet garām kastēm un sienām.
# player_x/player_y un guard.x/guard.y ir hitboxa augšējais kreisais stūris.
PLAYER_HIT_W = 24     # spēlētāja hitboxa platums
PLAYER_HIT_H = 14     # spēlētāja hitboxa augstums
GUARD_HIT_W = 26      # sarga hitboxa platums
GUARD_HIT_H = 14      # sarga hitboxa augstums
FEET_MARGIN = 4       # par cik pikseļiem hitboxs pacelts no lauciņa apakšas

# --- SPRITES (izmēri, ko zīmē klients; sprite stāv uz hitboxa apakšas) ---
PLAYER_SPRITE = 64    # spēlētāja sprits pikseļos
GUARD_SPRITE = 72     # sarga sprits pikseļos

# --- SPĒLĒTĀJS ---
PLAYER_SPEED = 200    # pikseļi sekundē — cik ātrs ir kurjers
START_LIVES = 3       # dzīvības HUD (no 2. fāzes: noķeršana = uzreiz game over)

# --- 1. UNIKĀLĀ MEHĀNIKA: lampas gaisma izsauc trauksmi ---
LIGHT_RADIUS = 120        # cik lielu laukumu apgaismo viena lampa (pikseļi)
LAMP_DETECT_TIME = 0.8    # cik ilgi jāstāv degošas lampas gaismā, līdz sargi trauksmi
LAMP_LIGHT_HALF_ANGLE = 55  # lampas gaismas sektora puse leņķī (kopā 110° konus)

# --- 2. UNIKĀLĀ MEHĀNIKA: lampu atslēgšana ---
LAMP_DISABLE_RANGE = 150  # no cik tālu var atslēgt lampu ar Space (pikseļi)
LAMP_OFF_TIME = 5.0       # cik sekundes lampa paliek izslēgta
LAMP_COOLDOWN = 8.0       # cik sekundes jāgaida, līdz var atkal atslēgt lampu

# --- 3. FĀZE: sūtījums, slēptuves, vērtējumi ---
INTERACT_RADIUS = 28      # cik tuvu flīzes centram (px) jābūt, lai ar E paņemtu sūtījumu vai paslēptos
EXPOSURE_DECAY_TIME = 1.0 # par cik sekundēm EXPOSURE josla nokrīt līdz 0, kad spēlētājs vairs nav gaismā
MISSION_TEXT_TIME = 2.0   # cik sekundes līmeņa sākumā rāda misijas tekstu ekrānā
# Misijas teksti pa līmeņiem (ekrānā, angliski)
MISSION_TEXTS = [
    "MISSION 01: Retrieve the encrypted package.",
    "MISSION 02: Recover the parcel from the security wing.",
    "MISSION 03: Escape the loading bay with the package.",
]
# Laika robežas S vērtējumam (sekundes) katram līmenim — ja lēnāk, S vairs nav
RANK_S_TIME = [60, 90, 120]

# --- SARGI ---
GUARD_SPEEDS = [80, 110, 140]  # sarga patruļas ātrums (pikseļi/sek) katram līmenim

# --- SARGU AI: stāvokļu sistēma (PATROL, LAMP_ALERT, SEARCH, ...) ---
FLASHLIGHT_WARNING_TIME = 1.30  # cik ilgi sargs brīdina ar lukturi, pirms sāk dzīties
SEARCH_TIME = 6.0               # cik sekundes sargs meklē ap pēdējo redzēto vietu
CHASE_SPEED_MULT = 1.15         # dzīšanās ātruma reizinātājs
PATROL_PAUSE_MIN = 0.3          # īsākā apstāšanās patruļas punktā (sekundes)
PATROL_PAUSE_MAX = 1.0          # garākā apstāšanās patruļas punktā (sekundes)
PATROL_MEMORY = 4               # cik pēdējos patruļas mērķus sargs atceras un neizvēlas
SEARCH_RADIUS_MIN = 3           # meklēšanas punkti ne tuvāk par tik flīzēm no signāla vietas
SEARCH_RADIUS_MAX = 6           # meklēšanas punkti ne tālāk par tik flīzēm no signāla vietas
SEARCH_POINT_COUNT_MIN = 3      # cik meklēšanas punktus sargs izvēlas (minimums)
SEARCH_POINT_COUNT_MAX = 5      # cik meklēšanas punktus sargs izvēlas (maksimums)
GUARD_LIGHT_RADIUS = 150        # cik tālu sniedzas sarga lukturis (pikseļi)
GUARD_CONE_ANGLE = 32           # luktura konusa puse leņķis (grādi)
CHASE_REPLAN_TIME = 0.25        # cik bieži dzīšanās laikā pārplāno ceļu (sekundes)
ALERT_ICON_TIME = 1.0           # cik ilgi virs sarga rāda sarkano "!" (sekundes)

# --- PUNKTU SISTĒMA ---
COIN_POINTS = 10              # punkti par vienu monētu
KEY_POINTS = 25               # punkti par atslēgas paņemšanu
LEVEL_BONUS = 100             # punkti par līmeņa pabeigšanu
TIME_BONUS_PER_SECOND = 2     # bonusa punkti par katru ietaupītu sekundi
LEVEL_TIME_LIMIT = 120.0      # ja līmeni pabeidz ātrāk par šo, dabū laika bonusu
