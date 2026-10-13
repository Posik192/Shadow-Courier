"""Izgriež VISUS sprite'us no asset kolāžas un saglabā assets/ mapē.

Paplašina cut_assets.py pieeju: maska pret pelēko fonu, ndimage.label
komponentes, meklēšana pēc enkurpunkta (x, y). Režīmi:
  "center" — caurspīdīgs fons (mīkstas malas), objekts centrēts kvadrātā
  "tile"   — kvadrātveida centra izgriezums bez caurspīdīguma
  "top:X"  — patur tikai augšējo X daļu (nogriež luktura/gaismas konusu)
Papildu krāsu filtri "red"/"yellow" UI elementiem uz tumšās joslas.

Palaišana:  python cut_all_assets.py
"""

import shutil

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

COLLAGE = r"C:\Users\rober\Downloads\Топдаун-ассеты для стелс-игры Shadow Courier.png"
BG_COLOR = np.array([148, 148, 150])
THRESHOLD = 40

# (nosaukums, x, y, režīms, krāsu_filtrs)
CUTS = [
    # Kurjeri (1. = ar mugursomu, no kreisās pa labi)
    ("player_1", 1175, 88, "center", None),
    ("player_2", 1268, 88, "center", None),
    ("player_3", 1360, 86, "center", None),
    ("player_4", 1455, 86, "center", None),
    # Sargi (bez konusiem), 5. = tūpējošais (konuss pa labi -> left krop)
    ("guard_1", 1175, 300, "top:0.45", None),
    ("guard_2", 1295, 300, "top:0.45", None),
    ("guard_3", 1410, 300, "top:0.45", None),
    ("guard_4", 1530, 300, "top:0.66|nobeam", None),
    ("guard_5", 1592, 412, "left:0.62", None),
    # Naži
    ("knife_1", 1605, 116, "center", None),
    ("knife_2", 1613, 236, "center", None),
    # Map tiles: rinda pa rindai no kreisās
    ("tile_1", 23, 61, "tile", None),
    ("tile_2", 143, 61, "tile", None),
    ("tile_3", 263, 61, "tile", None),
    ("tile_4", 384, 61, "tile", None),
    ("tile_5", 23, 184, "tile", None),
    ("tile_6", 143, 184, "tile", None),
    ("tile_7", 263, 184, "tile", None),
    ("tile_8", 384, 184, "tile", None),
    # Textures (grungy)
    ("tex_1", 533, 63, "center", None),
    ("tex_2", 679, 62, "center", None),
    ("tex_3", 839, 62, "center", None),
    ("tex_4", 988, 55, "center", None),
    ("tex_5", 528, 215, "center", None),
    ("tex_6", 726, 215, "center", None),
    ("tex_7", 885, 217, "center", None),
    ("tex_8", 968, 228, "center", None),
    # Durvis
    ("door_metal", 24, 366, "tile", None),
    ("door_locked", 150, 365, "tile", None),
    ("door_exit", 278, 355, "tile", None),
    ("door_open", 570, 430, "tile", None),
    # Atslēga un monētas
    ("key", 708, 423, "center", None),
    ("coin_1", 829, 414, "center", None),
    ("coin_2", 939, 417, "center", None),
    ("coin_3", 1014, 409, "center", None),
    # Lampas (bez gaismas konusiem); 2./3. = kupols uz tumša paneļa -> logs
    ("lamp_1", 75, 630, "top:0.28", None),
    ("lamp_2", 228, 664, "win:48:48", None),
    ("lamp_3", 357, 638, "win:56:56", None),
    # lamp_4: sienas lampa; konuss saplūdis ar lamp_3 -> logs + konusa krāsas izgriešana
    ("lamp_4", 529, 660, "win:70:140|nobeam", None),
    # Props
    ("prop_crate_big", 645, 675, "center", None),
    ("prop_crate_mid", 740, 670, "center", None),
    ("prop_crate_small", 817, 680, "center", None),
    ("prop_pallet", 890, 620, "center", None),
    ("prop_covered", 1010, 630, "center", None),
    ("prop_barrel", 1115, 630, "center", None),
    ("prop_shelf", 895, 730, "center", None),
    ("prop_boxes", 1015, 750, "center", None),
    ("prop_cabinet", 1115, 740, "center", None),
    ("prop_crowbar", 1240, 640, "center", None),
    # UI (sirds/monēta atdala ar krāsu filtru no tumšās joslas)
    ("ui_heart", 88, 878, "center", "red"),
    ("ui_coin", 311, 873, "center", "yellow"),
]

ALIASES = {
    "player.png": "player_1.png",
    "guard.png": "guard_1.png",
    "coin.png": "coin_1.png",
    "door.png": "door_metal.png",
    "exit.png": "door_exit.png",
    "floor.png": "tile_1.png",
    "wall.png": "tile_7.png",
    "lamp_on.png": "lamp_1.png",
}


def find_component(labels: np.ndarray, tx: int, ty: int) -> np.ndarray:
    for radius in (0, 10, 25, 50, 80):
        y0, y1 = max(0, ty - radius), ty + radius + 1
        x0, x1 = max(0, tx - radius), tx + radius + 1
        found = labels[y0:y1, x0:x1]
        nonzero = found[found > 0]
        if len(nonzero) > 0:
            comp_id = np.bincount(nonzero).argmax()
            return labels == comp_id
    raise ValueError(f"Komponente nav atrasta pie ({tx}, {ty})")


def cut_one(img: Image.Image, name: str, x: int, y: int,
            mode: str, color: str | None) -> Image.Image:
    a = np.array(img).astype(int)
    dist = np.abs(a - BG_COLOR).sum(axis=2)
    mask = dist > THRESHOLD
    if color == "red":
        mask &= (a[:, :, 0] > 150) & (a[:, :, 1] < 110) & (a[:, :, 2] < 110)
    elif color == "yellow":
        mask &= (a[:, :, 0] > 170) & (a[:, :, 1] > 130) & (a[:, :, 2] < 110)

    labels, _ = ndimage.label(mask)
    comp_mask = find_component(labels, x, y)
    ys, xs = np.where(comp_mask)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1

    piece = np.array(img)[y0:y1, x0:x1].copy()
    piece_mask = comp_mask[y0:y1, x0:x1]

    if mode.startswith("win:"):
        # Fiksēts logs ap enkurpunktu; alpha no pilnās maskas loga iekšpusē
        parts = mode.split("|")
        _, w, h = parts[0].split(":")
        w, h = int(w), int(h)
        wy0, wy1 = y - h // 2, y + h // 2
        wx0, wx1 = x - w // 2, x + w // 2
        piece = np.array(img)[wy0:wy1, wx0:wx1].copy()
        piece_mask = mask[wy0:wy1, wx0:wx1]
        if "nobeam" in parts:
            # Izmetam spilgti dzeltenos gaismas konusa pikseļus
            beam = ((piece[:, :, 0] > 190) & (piece[:, :, 1] > 170)
                    & (piece[:, :, 2] < 150))
            piece_mask = piece_mask & ~beam
    else:
        parts = mode.split("|")
        geom = parts[0]
        if geom.startswith("top:"):
            keep = int(piece.shape[0] * float(geom.split(":")[1]))
            piece = piece[:keep]
            piece_mask = piece_mask[:keep]
        elif geom.startswith("left:"):
            keep = int(piece.shape[1] * float(geom.split(":")[1]))
            piece = piece[:, :keep]
            piece_mask = piece_mask[:, :keep]
        elif geom.startswith("right:"):
            keep = int(piece.shape[1] * (1 - float(geom.split(":")[1])))
            piece = piece[:, keep:]
            piece_mask = piece_mask[:, keep:]
        if "nobeam" in parts:
            # Izmetam spilgti dzeltenos gaismas konusa pikseļus
            beam = ((piece[:, :, 0] > 190) & (piece[:, :, 1] > 170)
                    & (piece[:, :, 2] < 150))
            piece_mask = piece_mask & ~beam

    if mode == "tile":
        ph, pw = piece.shape[:2]
        side = min(ph, pw) - 8
        cy, cx = ph // 2, pw // 2
        piece = piece[cy - side // 2:cy + side // 2, cx - side // 2:cx + side // 2]
        return Image.fromarray(piece).convert("RGB")

    soft = ndimage.gaussian_filter(piece_mask.astype(float), 1.0)
    alpha = np.clip(soft * 255 * 1.3, 0, 255).astype(np.uint8)
    rgba = np.dstack([piece, alpha])
    result = Image.fromarray(rgba, "RGBA")
    side = max(result.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(result, ((side - result.width) // 2,
                          (side - result.height) // 2), result)
    return canvas


def make_contact_sheet(names: list[str], path: str) -> None:
    cell, label_h, cols = 120, 18, 7
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + label_h)), (28, 28, 32))
    draw = ImageDraw.Draw(sheet)
    for i, name in enumerate(names):
        img = Image.open(f"assets/{name}.png").convert("RGBA")
        img.thumbnail((cell - 8, cell - 8))
        cx = (i % cols) * cell
        cy = (i // cols) * (cell + label_h)
        sheet.paste(img, (cx + (cell - img.width) // 2,
                          cy + (cell - img.height) // 2), img)
        draw.text((cx + 4, cy + cell + 2), name, fill=(255, 255, 120))
    sheet.save(path)
    print(f"Kontaktlapa: {path} ({len(names)} attēli)")


def main() -> None:
    img = Image.open(COLLAGE).convert("RGB")
    done = []
    for name, x, y, mode, color in CUTS:
        try:
            result = cut_one(img, name, x, y, mode, color)
        except ValueError as exc:
            print(f"KĻŪDA {name}: {exc}")
            continue
        result.save(f"assets/{name}.png")
        done.append(name)
        print(f"assets/{name}.png  ({result.width}x{result.height})")

    for alias, src in ALIASES.items():
        shutil.copy(f"assets/{src}", f"assets/{alias}")
        print(f"assets/{alias} = {src}")

    lamp = Image.open("assets/lamp_1.png").convert("RGBA")
    r, g, b, alpha = lamp.split()
    dark = Image.merge("RGBA", (r.point(lambda px: int(px * 0.35)),
                                g.point(lambda px: int(px * 0.35)),
                                b.point(lambda px: int(px * 0.35)),
                                alpha))
    dark.save("assets/lamp_off.png")
    print("assets/lamp_off.png  (patumšota lamp_1)")

    make_contact_sheet(done, "_tmp_crops/contact_sheet.png")


if __name__ == "__main__":
    main()
