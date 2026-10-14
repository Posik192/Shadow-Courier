"""Sargs, kas patrulē pa līmeni.

Sargs iet taisni vienā virzienā. Kad priekšā ir siena vai aizvērtas
durvis, viņš apgriežas un iet atpakaļ. Tik vienkārši.
"""

from game.settings import TILE_SIZE, GUARD_HIT_W, GUARD_HIT_H, FEET_MARGIN


class Guard:
    """Viens sargs ar pozīciju un kustības virzienu.

    x, y — hitboxa augšējais kreisais stūris (tāpat kā spēlētājam).
    """

    def __init__(self, col: int, row: int, horizontal: bool, speed: int) -> None:
        """Uzliek sargu uz lauciņa: hitboxs centrēts, tuvu lauciņa apakšai."""
        self.x = col * TILE_SIZE + (TILE_SIZE - GUARD_HIT_W) // 2
        self.y = row * TILE_SIZE + TILE_SIZE - GUARD_HIT_H - FEET_MARGIN
        self.horizontal = horizontal
        self.speed = speed
        self.direction = 1  # 1 = pa labi/uz leju, -1 = pa kreisi/uz augšu

    def update(self, dt: float, rect_hits_solid) -> None:
        """Pabīda sargu. Ja priekšā šķērslis — apgriežas.

        rect_hits_solid ir funkcija no Level, kas pasaka, vai taisnstūris
        aizskar sienu. Tā sargam pašam nav jāzina nekas par karti.
        """
        step = self.speed * self.direction * dt
        if self.horizontal:
            new_x, new_y = self.x + step, self.y
        else:
            new_x, new_y = self.x, self.y + step

        if rect_hits_solid(new_x, new_y, GUARD_HIT_W, GUARD_HIT_H):
            self.direction = -self.direction  # siena priekšā — ejam atpakaļ
        else:
            self.x, self.y = new_x, new_y
