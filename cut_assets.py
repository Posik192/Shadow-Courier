"""Izgriež tekstūras no asset kolāžas un saglabā assets/ mapē.

Kolāža = liela bilde ar daudziem sprites uz pelēka fona.
Skripts atrod katru objektu pēc tā atrašanās vietas (x, y),
noņem fonu (padara caurspīdīgu) un saglabā atsevišķus PNG.

Palaišana:  python cut_assets.py
"""

import numpy as np
from PIL import Image
from scipy import ndimage

COLLAGE = r"C:\Users\rober\Downloads\Топдаун-ассеты для стелс-игры Shadow Courier.png"
BG_COLOR = np.array([148, 148, 150])  # kolāžas pelēkais fons
THRESHOLD = 40  # cik ļoti pikselim jāatšķiras no fona, lai skaitītos objekts

# --- Izgriežamie objekti ---
# (nosaukums, x, y, platums, augstums, režīms)
# Koordinātes no segments_preview.png analīzes.
# Režīmi:
#   "center" — caurspīdīgs fons, objekts centrēts kvadrātā
#   "top:X"  — vispirms nogriež apakšējo daļu (atstāj augšējo X daļu)
#   "tile"   — kvadrātveida izgriezums bez caurspīdīguma (grīdai/sienām)
CUTS = [
    ("player", 1155, 55, 79, 118, "center"),     # kurjers ar mugursomu
    ("guard", 1138, 244, 94, 193, "top:0.45"),   # sargs (bez luktura konusa)
    ("coin", 829, 414, 78, 92, "center"),        # zelta monēta ar kroni
    ("key", 708, 423, 50, 100, "center"),        # atslēga
    ("door", 24, 366, 103, 132, "tile"),         # metāla durvis
    ("exit", 278, 355, 101, 143, "tile"),        # zaļās izejas durvis
    ("lamp_on", 21, 604, 134, 164, "top:0.32"),  # karājošā kupola lampa
    ("floor", 23, 61, 112, 114, "tile"),         # tumša grīdas flīze
    ("wall", 263, 184, 112, 113, "tile"),        # gaiša sienu flīze
]


def find_component(labels: np.ndarray, tx: int, ty: int) -> np.ndarray:
    """Atrod maskas komponenti, kurā atrodas punkts (tx, ty)."""
    # Punkts var trāpīt uz cauruma objektā — meklējam tuvumā
    for radius in (0, 10, 25, 50):
        y0, y1 = max(0, ty - radius), ty + radius + 1
        x0, x1 = max(0, tx - radius), tx + radius + 1
        found = labels[y0:y1, x0:x1]
        nonzero = found[found > 0]
        if len(nonzero) > 0:
            # Biežākā komponente šajā apgabalā
            comp_id = np.bincount(nonzero).argmax()
            return labels == comp_id
    raise ValueError(f"Komponente nav atrasta pie ({tx}, {ty})")


def main() -> None:
    img = Image.open(COLLAGE).convert("RGB")
    a = np.array(img).astype(int)

    # Maska: kuri pikseļi NAV fons
    dist = np.abs(a - BG_COLOR).sum(axis=2)
    mask = dist > THRESHOLD
    labels, _ = ndimage.label(mask)

    for name, x, y, w, h, mode in CUTS:
        comp_mask = find_component(labels, x + w // 2, y + h // 2)
        ys, xs = np.where(comp_mask)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1

        piece = np.array(img)[y0:y1, x0:x1].copy()
        piece_mask = comp_mask[y0:y1, x0:x1]

        if mode.startswith("top:"):
            # Nogriežam apakšējo daļu (piem., luktura konusu)
            keep = int(piece.shape[0] * float(mode.split(":")[1]))
            piece = piece[:keep]
            piece_mask = piece_mask[:keep]

        if mode == "tile":
            # Flīzes: kvadrātveida centra izgriezums bez caurspīdīguma
            ph, pw = piece.shape[:2]
            side = min(ph, pw) - 8
            cy, cx = ph // 2, pw // 2
            piece = piece[cy - side // 2:cy + side // 2, cx - side // 2:cx + side // 2]
            result = Image.fromarray(piece).convert("RGB")
        else:
            # Mīkstas malas: masku nedaudz izpludinām
            soft = ndimage.gaussian_filter(piece_mask.astype(float), 1.0)
            alpha = np.clip(soft * 255 * 1.3, 0, 255).astype(np.uint8)
            rgba = np.dstack([piece, alpha])
            result = Image.fromarray(rgba, "RGBA")
            # Ieliekam kvadrātveida kadrojumā ar objektu centrā
            side = max(result.size)
            canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
            canvas.paste(result, ((side - result.width) // 2,
                                  (side - result.height) // 2), result)
            result = canvas

        result.save(f"assets/{name}.png")
        print(f"assets/{name}.png  ({result.width}x{result.height})")

    # Izslēgtā lampa = tā pati lampa, tikai patumšota
    lamp = Image.open("assets/lamp_on.png").convert("RGBA")
    r, g, b, alpha = lamp.split()
    dark = Image.merge("RGBA", (r.point(lambda px: int(px * 0.35)),
                                g.point(lambda px: int(px * 0.35)),
                                b.point(lambda px: int(px * 0.35)),
                                alpha))
    dark.save("assets/lamp_off.png")
    print("assets/lamp_off.png  (izslēgtā lampa)")


if __name__ == "__main__":
    main()
