"""Līmeņa vērtējums S / A / B / C — cik "tīri" līmenis iziets.

    S — visas monētas, 0 trauksmes, laiks robežās
    A — trūkst max 1 monēta vai 1 trauksme
    B — vairāk kļūdu
    C — daudz trauksmju vai ļoti lēns

Sūtījumu šeit nepārbauda — bez tā līmenis vispār nebeidzas.
"""

from game.settings import RANK_S_TIME

# No labākā uz sliktāko (mazāks indekss = labāks)
RANK_ORDER = ["S", "A", "B", "C"]


def calculate_rank(coins_got: int, coins_total: int, alerts: int,
                   time_sec: float, level_number: int) -> str:
    """Atgriež burtu S/A/B/C pēc līmeņa statistikas.
    level_number vajadzīgs, lai zinātu S laika robežu."""
    s_time = RANK_S_TIME[level_number - 1]
    if coins_got == coins_total and alerts == 0 and time_sec <= s_time:
        return "S"
    # Daudz trauksmju vai vairāk nekā 2x no S laika — vienmēr C
    if alerts >= 3 or time_sec > s_time * 2:
        return "C"
    if coins_got >= coins_total - 1 and alerts <= 1:
        return "A"
    return "B"


def better_rank(rank_a: str, rank_b: str) -> str:
    """Labākais no diviem rangiem (piem., better_rank('A', 'S') == 'S')."""
    if RANK_ORDER.index(rank_a) <= RANK_ORDER.index(rank_b):
        return rank_a
    return rank_b
