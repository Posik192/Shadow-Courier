# -*- coding: utf-8 -*-
"""Izgriež jaunos sprite'us: lampas (balts fons) un personāži (melns fons).

Melnais fons: maska = "gandrīz melni" pikseļi SAVIENOTI ar bildes malu
(ndimage.label + komponentes pie malas) -> tumšās drēves paliek.
"""

import shutil

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

LAMP_SRC = r"C:\Users\rober\Downloads\Промышленные лампы_ включённые и выключенные.png"
PLAYER_SRC = r"C:\Users\rober\Downloads\Курьер-тень_ разворот персонажа-1.png"
GUARD_SRC = r"C:\Users\rober\Downloads\Пиксельный охранник склада_ вид со всех сторон.png"

# kvadranti: (x0, y0, x1, y1) daļās no bildes
QUADS = {
    "down": (0.0, 0.0, 0.5, 0.5),
    "right": (0.5, 0.0, 1.0, 0.5),
    "up": (0.0, 0.5, 0.5, 1.0),
    "left": (0.5, 0.5, 1.0, 1.0),
}


def square_canvas(piece: np.ndarray, alpha: np.ndarray) -> Image.Image:
    soft = ndimage.gaussian_filter(alpha.astype(float), 1.0)
    a = np.clip(soft * 255 * 1.3, 0, 255).astype(np.uint8)
    result = Image.fromarray(np.dstack([piece, a]), "RGBA")
    side = max(result.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(result, ((side - result.width) // 2,
                          (side - result.height) // 2), result)
    return canvas


def cut_black_bg(path: str, prefix: str) -> list[str]:
    img = np.array(Image.open(path).convert("RGB")).astype(int)
    h, w = img.shape[:2]
    dark = img.sum(axis=2) < 60
    labels, _ = ndimage.label(dark)
    border_ids = np.unique(np.concatenate([
        labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]]))
    border_ids = border_ids[border_ids > 0]
    bg = np.isin(labels, border_ids)
    fg = ~bg
    saved = []
    for direction, (fx0, fy0, fx1, fy1) in QUADS.items():
        x0, y0, x1, y1 = int(fx0 * w), int(fy0 * h), int(fx1 * w), int(fy1 * h)
        sub = fg[y0:y1, x0:x1]
        ys, xs = np.where(sub)
        if len(ys) == 0:
            print(f"KĻŪDA {prefix}_{direction}: nav priekšplāna")
            continue
        py0, py1 = y0 + ys.min(), y0 + ys.max() + 1
        px0, px1 = x0 + xs.min(), x0 + xs.max() + 1
        piece = img[py0:py1, px0:px1].astype(np.uint8)
        mask = fg[py0:py1, px0:px1]
        name = f"{prefix}_{direction}"
        square_canvas(piece, mask).save(f"assets/{name}.png")
        saved.append(name)
        print(f"assets/{name}.png ({px1-px0}x{py1-py0})")
    return saved


def cut_lamps() -> list[str]:
    rgba = np.array(Image.open(LAMP_SRC).convert("RGBA"))
    img = rgba[:, :, :3].astype(int)
    h, w = img.shape[:2]
    mask = rgba[:, :, 3] > 128  # fons jau ir caurspīdīgs
    labels, _ = ndimage.label(mask)
    saved = []
    for name, ax, ay in (("lamp_on", int(0.27 * w), int(0.36 * h)),
                         ("lamp_off", int(0.73 * w), int(0.36 * h))):
        # tikai augšējā puse
        region = labels[:h // 2]
        comp_id = region[ay, ax]
        if comp_id == 0:
            print(f"KĻŪDA {name}: enkurpunkts ({ax},{ay}) nav uz komponentes")
            continue
        comp = labels == comp_id
        ys, xs = np.where(comp)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        piece = img[y0:y1, x0:x1].astype(np.uint8)
        square_canvas(piece, comp[y0:y1, x0:x1]).save(f"assets/{name}.png")
        saved.append(name)
        print(f"assets/{name}.png ({x1-x0}x{y1-y0})")
    return saved


def make_contact_sheet(names: list[str], path: str) -> None:
    cell, label_h, cols = 160, 18, 5
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + label_h)),
                      (0x1d, 0x2a, 0x3d))
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
    print(f"Kontaktlapa: {path}")


def main() -> None:
    saved = cut_lamps()
    saved += cut_black_bg(PLAYER_SRC, "player")
    saved += cut_black_bg(GUARD_SRC, "guard")
    shutil.copy("assets/player_down.png", "assets/player.png")
    shutil.copy("assets/guard_down.png", "assets/guard.png")
    print("assets/player.png = player_down, assets/guard.png = guard_down")
    make_contact_sheet(saved, "_tmp_crops/contact_sheet_new.png")


if __name__ == "__main__":
    main()
