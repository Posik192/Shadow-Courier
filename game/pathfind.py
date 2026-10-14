"""Ceļa meklēšana pa kartes lauciņiem ar vienkāršu BFS.

Karte ir maza (24x16 lauciņi), tāpēc pietiek ar platuma meklēšanu
(BFS) — sarežģītāks A* algoritms šeit nav vajadzīgs. Abas funkcijas
saņem `is_solid(col, row)` funkciju (Level.is_solid_tile), tāpēc
šis fails pats nezina neko par sienām, kastēm vai durvīm.
"""

from collections import deque

# Kustība pa četrām pusēm (pa diagonāli sargi neiet)
NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def reachable_tiles(is_solid, start: tuple[int, int]) -> set[tuple[int, int]]:
    """Atgriež visus lauciņus, kurus var sasniegt no starta (BFS plūdmaiņa)."""
    seen = {start}
    queue = deque([start])
    while queue:
        col, row = queue.popleft()
        for dcol, drow in NEIGHBOURS:
            nxt = (col + dcol, row + drow)
            if nxt in seen or is_solid(*nxt):
                continue
            seen.add(nxt)
            queue.append(nxt)
    return seen


def find_path(is_solid, start: tuple[int, int],
              goal: tuple[int, int]) -> list[tuple[int, int]] | None:
    """Atrod īsāko ceļu no starta uz mērķi (lauciņu saraksts, abi ieskaitot).

    Ja mērķis ir ciets lauciņš vai nav sasniedzams — atgriež None.
    """
    if start == goal:
        return [start]
    if is_solid(*goal):
        return None
    came_from = {start: None}  # lauciņš -> no kura lauciņa uz viņu atnācām
    queue = deque([start])
    while queue:
        col, row = queue.popleft()
        for dcol, drow in NEIGHBOURS:
            nxt = (col + dcol, row + drow)
            if nxt in came_from or is_solid(*nxt):
                continue
            came_from[nxt] = (col, row)
            if nxt == goal:
                # Atjaunojam ceļu, ejot no mērķa atpakaļ uz startu
                path = [goal]
                while came_from[path[-1]] is not None:
                    path.append(came_from[path[-1]])
                path.reverse()
                return path
            queue.append(nxt)
    return None
