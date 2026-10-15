"""Ceļa meklēšana pa kartes lauciņiem ar BFS.

Karte ir maza (24x16), tāpēc pietiek ar parasto platuma meklēšanu,
A* šeit nevajag. Abas funkcijas saņem is_solid(col, row) no ārpuses,
tāpēc fails pats nezina neko par sienām un durvīm.
"""

from collections import deque

# Kustība pa četrām pusēm (pa diagonāli sargi neiet)
NEIGHBOURS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def reachable_tiles(is_solid, start: tuple[int, int]) -> set[tuple[int, int]]:
    """Visi lauciņi, kurus var sasniegt no starta (BFS plūdmaiņa)."""
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
    """Īsākais ceļš no starta uz mērķi (lauciņu saraksts, abi ieskaitot).
    Ja mērķis ciets vai nav sasniedzams — None."""
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
