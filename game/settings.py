"""Spēles uzstādījumi.

ŠEIT maina visus skaitļus: ātrumu, punktus, gaismas ilgumu utt.
Ja skolotājs saka "ieliec 2x ātrāk" — maini PLAYER_SPEED šeit.
"""

# --- EKRĀNS ---
TILE_SIZE = 48        # viena kartes lauciņa izmērs pikseļos
PLAYER_SIZE = 32      # spēlētāja kvadrāta izmērs (mazāks par lauciņu, lai tilptu ejas)

# --- SPĒLĒTĀJS ---
PLAYER_SPEED = 200    # pikseļi sekundē — cik ātrs ir kurjers
START_LIVES = 3       # ar cik dzīvībām sāk (sargs/gaisma noņem vienu)

# --- 1. UNIKĀLĀ MEHĀNIKA: gaismas briesmas ---
LIGHT_RADIUS = 120        # cik lielu laukumu apgaismo viena lampa (pikseļi)
LIGHT_TIME_LIMIT = 3.0    # cik sekundes drīkst stāvēt gaismā, pirms spēle beidzas

# --- 2. UNIKĀLĀ MEHĀNIKA: lampu atslēgšana ---
LAMP_DISABLE_RANGE = 150  # no cik tālu var atslēgt lampu ar Space (pikseļi)
LAMP_OFF_TIME = 5.0       # cik sekundes lampa paliek izslēgta
LAMP_COOLDOWN = 8.0       # cik sekundes jāgaida, līdz var atkal atslēgt lampu

# --- SARGI ---
GUARD_SPEEDS = [80, 110, 140]  # sarga ātrums (pikseļi/sek) katram līmenim: 1., 2., 3.

# --- PUNKTU SISTĒMA ---
COIN_POINTS = 10              # punkti par vienu monētu
KEY_POINTS = 25               # punkti par atslēgas paņemšanu
LEVEL_BONUS = 100             # punkti par līmeņa pabeigšanu
TIME_BONUS_PER_SECOND = 2     # bonusa punkti par katru ietaupītu sekundi
LEVEL_TIME_LIMIT = 120.0      # ja līmeni pabeidz ātrāk par šo, dabū laika bonusu
