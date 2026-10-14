"""Līmeņa vērtējuma (ranga) aprēķins — S / A / B / C.

Rangi parāda, cik "tīri" līmenis izietas:
    S — visas monētas, 0 trauksmes un laiks nepārsniedz RANK_S_TIME
    A — gandrīz visas monētas (trūkst ne vairāk par 1) un ne vairāk par 1 trauksmi
    B — pabeigts ar vairākām kļūdām
    C — ļoti lēns vai daudz trauksmju

Sūtījums rangā nav jāpārbauda — bez tā līmenis vispār nebeidzas.
"""

from game.settings import RANK_S_TIME

# Rangu secība no labākā uz sliktāko (mazāks indekss = labāks)
RANK_ORDER = ["S", "A", "B", "C"]


def calculate_rank(coins_got: int, coins_total: int, alerts: int,
                   time_sec: float, level_number: int) -> str:
    """Atgriež burtu S/A/B/C pēc līmeņa statistikas.

    coins_got / coins_total — paņemtās un visas monētas līmenī,
    alerts — izsauktās lampas trauksmes, time_sec — līmeņa laiks sekundēs,
    level_number — līmenis (1..3), no tā ņem S laika robežu.
    """
    s_time = RANK_S_TIME[level_number - 1]
    if coins_got == coins_total and alerts == 0 and time_sec <= s_time:
        return "S"
    # Daudz trauksmju vai ļoti lēns (vairāk nekā 2x no S laika) — vienmēr C
    if alerts >= 3 or time_sec > s_time * 2:
        return "C"
    if coins_got >= coins_total - 1 and alerts <= 1:
        return "A"
    return "B"


def better_rank(rank_a: str, rank_b: str) -> str:
    """Atgriež labāko no diviem rangiem (piem., better_rank('A', 'S') == 'S')."""
    if RANK_ORDER.index(rank_a) <= RANK_ORDER.index(rank_b):
        return rank_a
    return rank_b
