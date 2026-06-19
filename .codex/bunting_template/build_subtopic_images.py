from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


OUT_DIR = Path("output/bunting_subtopic_images")
W, H = 1600, 1000
S = 2

GREEN_DARK = (0, 83, 49)
GREEN = (0, 116, 70)
GREEN_2 = (21, 146, 102)
MINT = (187, 241, 211)
MINT_LIGHT = (231, 250, 240)
PURPLE = (120, 104, 228)
CORAL = (238, 111, 114)
YELLOW = (247, 196, 83)
INK = (24, 45, 39)
MUTED = (74, 103, 94)
WHITE = (255, 255, 255)

FONT_DIR = Path(r"C:\Windows\Fonts")
FONT_REG = FONT_DIR / "arial.ttf"
FONT_BOLD = FONT_DIR / "arialbd.ttf"
FONT_BLACK = FONT_DIR / "ariblk.ttf"


def sc(v: int | float) -> int:
    return int(round(v * S))


def color(c: tuple[int, int, int], a: int = 255) -> tuple[int, int, int, int]:
    return c[0], c[1], c[2], a


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), sc(size))


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def line(draw: ImageDraw.ImageDraw, pts, fill, width=4):
    draw.line([(sc(x), sc(y)) for x, y in pts], fill=fill, width=sc(width), joint="curve")


def rounded(draw: ImageDraw.ImageDraw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(tuple(sc(v) for v in box), radius=sc(radius), fill=fill, outline=outline, width=sc(width))


def ellipse(draw: ImageDraw.ImageDraw, box, fill=None, outline=None, width=1):
    draw.ellipse(tuple(sc(v) for v in box), fill=fill, outline=outline, width=sc(width))


def polygon(draw: ImageDraw.ImageDraw, pts, fill=None, outline=None):
    draw.polygon([(sc(x), sc(y)) for x, y in pts], fill=fill, outline=outline)


def text(draw: ImageDraw.ImageDraw, xy, value, fnt, fill, anchor=None):
    draw.text((sc(xy[0]), sc(xy[1])), value, font=fnt, fill=fill, anchor=anchor)


def shadowed_layer(base: Image.Image, layer: Image.Image, blur=34, y=18, alpha=70):
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    mask = layer.split()[-1]
    shadow_fill = Image.new("RGBA", base.size, (0, 0, 0, alpha))
    shadow.paste(shadow_fill, (0, sc(y)), mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(sc(blur)))
    base.alpha_composite(shadow)
    base.alpha_composite(layer)


def new_canvas() -> Image.Image:
    img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(glow, "RGBA")
    ellipse(d, (190, 160, 1410, 870), color(MINT_LIGHT, 180))
    glow = glow.filter(ImageFilter.GaussianBlur(sc(58)))
    img.alpha_composite(glow)
    return img


def save(img: Image.Image, name: str):
    small = img.resize((W, H), Image.Resampling.LANCZOS)
    small.save(OUT_DIR / f"{name}.png")


def draw_mini_circuits(draw: ImageDraw.ImageDraw, x0=95, y0=760, alpha=92):
    for i in range(6):
        y = y0 + i * 34
        line(draw, [(x0, y), (x0 + 280, y)], color(GREEN_2, alpha), 4)
        ellipse(draw, (x0 + 275, y - 10, x0 + 295, y + 10), fill=color(GREEN_2, alpha))
    for i in range(5):
        x = x0 + 45 + i * 50
        line(draw, [(x, y0 - 35), (x, y0 + 170)], color(GREEN_2, alpha - 25), 3)


def draw_scan_beam(draw: ImageDraw.ImageDraw, left, top, right, bottom):
    polygon(draw, [(left, top), (right, top + 110), (right, bottom - 110), (left, bottom)], fill=color((112, 237, 185), 64))
    line(draw, [(left + 30, (top + bottom) / 2), (right - 30, (top + bottom) / 2)], color((94, 241, 180), 210), 11)


def draw_book(draw: ImageDraw.ImageDraw, x, y, w, h, open_book=True):
    if open_book:
        rounded(draw, (x, y, x + w, y + h), 34, color(WHITE, 245), color(GREEN, 170), 5)
        line(draw, [(x + w / 2, y + 30), (x + w / 2, y + h - 25)], color(GREEN, 95), 4)
        for i in range(6):
            yy = y + 85 + i * 48
            line(draw, [(x + 70, yy), (x + w / 2 - 55, yy + (i % 2) * 8)], color(MUTED, 120), 4)
            line(draw, [(x + w / 2 + 55, yy + 5), (x + w - 70, yy - (i % 2) * 8)], color(MUTED, 120), 4)
    else:
        rounded(draw, (x, y, x + w, y + h), 36, color(WHITE, 250), color(GREEN, 180), 6)
        text(draw, (x + 62, y + 60), "BUKU", font(FONT_BLACK, 38), color(GREEN_DARK), None)
        text(draw, (x + 62, y + 105), "INDUK", font(FONT_BLACK, 38), color(GREEN_DARK), None)
        for i in range(8):
            yy = y + 190 + i * 45
            line(draw, [(x + 62, yy), (x + w - 70 - (i % 3) * 42, yy)], color(GREEN_DARK, 120), 4)


def draw_screen(draw: ImageDraw.ImageDraw, x, y, w, h):
    rounded(draw, (x, y, x + w, y + h), 36, color(WHITE, 248), color(GREEN, 150), 5)
    rounded(draw, (x + 34, y + 34, x + w - 34, y + 105), 22, color(MINT_LIGHT, 255), None, 1)
    for i in range(3):
        cy = y + 165 + i * 105
        rounded(draw, (x + 55, cy, x + 155, cy + 72), 18, color(MINT, 255), None, 1)
        line(draw, [(x + 190, cy + 20), (x + w - 80, cy + 20)], color(GREEN_DARK, 150), 6)
        line(draw, [(x + 190, cy + 52), (x + w - 170, cy + 52)], color(MUTED, 115), 5)


def badge(draw: ImageDraw.ImageDraw, cx, cy, label, fill=GREEN_DARK):
    ellipse(draw, (cx - 70, cy - 70, cx + 70, cy + 70), fill=color(WHITE, 245), outline=color(fill, 190), width=5)
    tw, th = text_size(draw, label, font(FONT_BLACK, 26))
    text(draw, (cx - tw / (2 * S), cy - th / (2 * S)), label, font(FONT_BLACK, 26), color(fill), None)


def icon_introduction():
    img = new_canvas()
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    draw_book(d, 355, 260, 560, 430, True)
    # Magnifier.
    ellipse(d, (810, 480, 1140, 810), fill=color(WHITE, 225), outline=color(GREEN_DARK, 210), width=13)
    line(d, [(1056, 726), (1245, 905)], color(GREEN_DARK, 220), 22)
    ellipse(d, (888, 555, 1045, 712), outline=color(PURPLE, 210), width=10)
    draw_mini_circuits(d, 150, 710, 65)
    text(d, (800, 140), "7,000+ BOOKS", font(FONT_BLACK, 58), color(GREEN_DARK), "mm")
    text(d, (800, 205), "manual records to search", font(FONT_BOLD, 34), color(MUTED), "mm")
    shadowed_layer(img, layer)
    return img


def icon_problem():
    img = new_canvas()
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    draw_book(d, 395, 210, 570, 560, False)
    # Crack lines.
    line(d, [(735, 210), (705, 310), (748, 385), (710, 470), (748, 570), (720, 770)], color(CORAL, 220), 9)
    polygon(d, [(1070, 270), (850, 720), (1290, 720)], fill=color((255, 250, 229), 245), outline=color(CORAL, 230))
    line(d, [(1070, 405), (1070, 590)], color(CORAL, 240), 24)
    ellipse(d, (1050, 630, 1090, 670), fill=color(CORAL, 250))
    rounded(d, (240, 725, 650, 850), 28, color(WHITE, 235), color(GREEN, 110), 4)
    text(d, (445, 760), "SLOW SEARCH", font(FONT_BLACK, 34), color(GREEN_DARK), "ma")
    text(d, (445, 810), "manual status tracking", font(FONT_BOLD, 27), color(MUTED), "ma")
    shadowed_layer(img, layer)
    return img


def icon_methodology():
    img = new_canvas()
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    cx, cy = 800, 505
    # Circular workflow.
    for start in [25, 115, 205, 295]:
        d.arc(tuple(sc(v) for v in (420, 130, 1180, 890)), start, start + 58, fill=color(GREEN_DARK, 220), width=sc(16))
        angle = math.radians(start + 58)
        x = cx + math.cos(angle) * 380
        y = cy + math.sin(angle) * 380
        polygon(d, [(x, y), (x - 36 * math.cos(angle - 0.45), y - 36 * math.sin(angle - 0.45)), (x - 36 * math.cos(angle + 0.45), y - 36 * math.sin(angle + 0.45))], fill=color(GREEN_DARK, 220))
    steps = [
        (800, 135, "UPLOAD", GREEN),
        (1180, 505, "OCR", PURPLE),
        (800, 875, "VERIFY", GREEN_DARK),
        (420, 505, "IMPORT", GREEN_2),
    ]
    for x, y, label, c in steps:
        rounded(d, (x - 145, y - 62, x + 145, y + 62), 45, color(WHITE, 245), color(c, 190), 5)
        text(d, (x, y - 15), label, font(FONT_BLACK, 31), color(c), "mm")
    rounded(d, (610, 375, 990, 635), 50, color(MINT_LIGHT, 250), color(GREEN, 145), 5)
    text(d, (800, 455), "AGILE", font(FONT_BLACK, 56), color(GREEN_DARK), "mm")
    text(d, (800, 535), "SCRUM", font(FONT_BLACK, 56), color(GREEN_DARK), "mm")
    shadowed_layer(img, layer)
    return img


def icon_design():
    img = new_canvas()
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    # Architecture stack.
    draw_screen(d, 190, 220, 440, 440)
    rounded(d, (720, 250, 1040, 425), 42, color(WHITE, 245), color(PURPLE, 190), 5)
    text(d, (880, 305), "FLASK", font(FONT_BLACK, 43), color(PURPLE), "mm")
    text(d, (880, 365), "API", font(FONT_BLACK, 43), color(PURPLE), "mm")
    rounded(d, (720, 555, 1040, 730), 42, color(WHITE, 245), color(GREEN_DARK, 190), 5)
    text(d, (880, 610), "OCR", font(FONT_BLACK, 43), color(GREEN_DARK), "mm")
    text(d, (880, 670), "REVIEW", font(FONT_BLACK, 36), color(GREEN_DARK), "mm")
    # Database cylinder.
    ellipse(d, (1130, 250, 1435, 360), fill=color(MINT_LIGHT, 255), outline=color(GREEN, 190), width=6)
    rounded(d, (1130, 305, 1435, 720), 26, color(MINT_LIGHT, 250), color(GREEN, 190), 6)
    ellipse(d, (1130, 665, 1435, 775), fill=color(MINT_LIGHT, 255), outline=color(GREEN, 190), width=6)
    text(d, (1282, 505), "DB", font(FONT_BLACK, 70), color(GREEN_DARK), "mm")
    # Connections.
    line(d, [(630, 440), (720, 340)], color(GREEN, 180), 8)
    line(d, [(630, 500), (720, 640)], color(GREEN, 180), 8)
    line(d, [(1040, 340), (1130, 355)], color(GREEN, 180), 8)
    line(d, [(1040, 640), (1130, 620)], color(GREEN, 180), 8)
    # Users.
    for i, label in enumerate(["ADMIN", "LIB", "PREF", "STU"]):
        badge(d, 340 + i * 155, 795, label, GREEN_DARK if i % 2 == 0 else PURPLE)
    shadowed_layer(img, layer)
    return img


def icon_results():
    img = new_canvas()
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    draw_screen(d, 360, 185, 760, 520)
    # Bar chart overlay.
    for i, h in enumerate([90, 145, 220]):
        x = 500 + i * 120
        rounded(d, (x, 535 - h, x + 72, 535), 18, color([GREEN_2, PURPLE, GREEN][i], 230), None, 1)
    line(d, [(470, 550), (925, 550)], color(GREEN_DARK, 170), 6)
    # Scanner.
    rounded(d, (955, 610, 1330, 745), 42, color(GREEN_DARK, 245), None, 1)
    text(d, (1142, 655), "BARCODE", font(FONT_BLACK, 38), color(WHITE), "mm")
    draw_scan_beam(d, 300, 635, 950, 725)
    # Check.
    ellipse(d, (1085, 245, 1345, 505), fill=color(WHITE, 240), outline=color(GREEN, 210), width=8)
    line(d, [(1150, 382), (1210, 445), (1290, 320)], color(GREEN, 240), 20)
    text(d, (800, 845), "SEARCHABLE + FASTER", font(FONT_BLACK, 52), color(GREEN_DARK), "mm")
    shadowed_layer(img, layer)
    return img


def icon_conclusion():
    img = new_canvas()
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    # Library building.
    polygon(d, [(420, 355), (800, 185), (1180, 355)], fill=color(GREEN_DARK, 245))
    rounded(d, (480, 355, 1120, 720), 28, color(WHITE, 245), color(GREEN_DARK, 180), 6)
    for i in range(4):
        x = 565 + i * 145
        rounded(d, (x, 425, x + 75, 690), 18, color(MINT_LIGHT, 255), color(GREEN, 130), 4)
    rounded(d, (420, 720, 1180, 790), 24, color(GREEN_DARK, 245), None, 1)
    # Completed check and future dots.
    ellipse(d, (1020, 190, 1310, 480), fill=color(WHITE, 240), outline=color(GREEN, 210), width=8)
    line(d, [(1095, 340), (1160, 405), (1260, 260)], color(GREEN, 240), 20)
    for i, c in enumerate([GREEN, PURPLE, CORAL]):
        ellipse(d, (325 + i * 105, 805, 385 + i * 105, 865), fill=color(c, 220))
    text(d, (800, 875), "SCHOOL-READY WORKFLOW", font(FONT_BLACK, 48), color(GREEN_DARK), "mm")
    shadowed_layer(img, layer)
    return img


def icon_novelty():
    img = new_canvas()
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    # Contribution diamond.
    polygon(d, [(800, 120), (1135, 390), (800, 870), (465, 390)], fill=color(WHITE, 245), outline=color(GREEN_DARK, 190))
    polygon(d, [(800, 120), (1135, 390), (800, 390), (465, 390)], fill=color(MINT_LIGHT, 245), outline=color(GREEN_DARK, 120))
    rounded(d, (615, 335, 985, 620), 48, color(GREEN_DARK, 245), None, 1)
    text(d, (800, 430), "OCR", font(FONT_BLACK, 70), color(WHITE), "mm")
    text(d, (800, 535), "+ VERIFY", font(FONT_BLACK, 42), color(MINT), "mm")
    # Mini ledger and shield.
    draw_book(d, 250, 500, 310, 265, False)
    polygon(d, [(1240, 480), (1405, 555), (1370, 755), (1240, 850), (1110, 755), (1075, 555)], fill=color(WHITE, 245), outline=color(PURPLE, 210))
    line(d, [(1172, 660), (1226, 718), (1320, 585)], color(PURPLE, 230), 16)
    # Sparkles.
    for x, y, r in [(305, 245, 36), (1260, 255, 28), (1320, 890, 24), (460, 840, 22)]:
        line(d, [(x - r, y), (x + r, y)], color(YELLOW, 210), 8)
        line(d, [(x, y - r), (x, y + r)], color(YELLOW, 210), 8)
    text(d, (800, 915), "NOVEL + PRACTICAL", font(FONT_BLACK, 52), color(GREEN_DARK), "mm")
    shadowed_layer(img, layer)
    return img


def make_contact_sheet(files: list[tuple[str, Path]]) -> None:
    cell_w, cell_h = 760, 560
    sheet = Image.new("RGB", (cell_w * 2, cell_h * 4), (245, 253, 248))
    d = ImageDraw.Draw(sheet)
    for idx, (title, path) in enumerate(files):
        row, col = divmod(idx, 2)
        x, y = col * cell_w, row * cell_h
        d.rounded_rectangle((x + 30, y + 30, x + cell_w - 30, y + cell_h - 30), radius=34, fill=(255, 255, 255), outline=(192, 225, 207), width=3)
        im = Image.open(path).convert("RGBA")
        im.thumbnail((500, 310), Image.Resampling.LANCZOS)
        sheet.paste(im, (x + (cell_w - im.width) // 2, y + 90), im)
        title_f = ImageFont.truetype(str(FONT_BLACK), 28)
        box = d.textbbox((0, 0), title, font=title_f)
        d.text((x + (cell_w - (box[2] - box[0])) // 2, y + 430), title, font=title_f, fill=GREEN_DARK)
    sheet.save(OUT_DIR / "subtopic_images_contact_sheet.png", quality=95)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    assets = [
        ("Introduction", "01_introduction", icon_introduction),
        ("Problem Statement", "02_problem_statement", icon_problem),
        ("Methodology", "03_methodology", icon_methodology),
        ("Design & Analysis", "04_design_analysis", icon_design),
        ("Results", "05_results", icon_results),
        ("Conclusion", "06_conclusion", icon_conclusion),
        ("Novelty & Contribution", "07_novelty_contribution", icon_novelty),
    ]
    files = []
    for title, slug, fn in assets:
        save(fn(), slug)
        files.append((title, OUT_DIR / f"{slug}.png"))
    make_contact_sheet(files)
    for _, path in files:
        print(path.resolve())
    print((OUT_DIR / "subtopic_images_contact_sheet.png").resolve())


if __name__ == "__main__":
    main()
