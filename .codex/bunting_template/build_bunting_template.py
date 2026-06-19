from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


OUT_DIR = Path(r"C:\Users\wanza\Downloads")
PRINT_PATH = OUT_DIR / "ePustaka_Munshi_FYP_Bunting_WOW_Template.png"
PREVIEW_PATH = OUT_DIR / "ePustaka_Munshi_FYP_Bunting_WOW_Template_preview.png"

W, H = 3600, 10800

GREEN_DARK = (0, 83, 49)
GREEN = (0, 116, 70)
GREEN_2 = (21, 146, 102)
MINT = (166, 229, 198)
LIME = (105, 225, 142)
PURPLE = (120, 104, 228)
CORAL = (238, 111, 114)
INK = (23, 43, 38)
MUTED = (73, 99, 92)
PALE = (241, 250, 246)
WHITE = (255, 255, 255)


FONT_DIR = Path(r"C:\Windows\Fonts")
FONT_REG = FONT_DIR / "arial.ttf"
FONT_BOLD = FONT_DIR / "arialbd.ttf"
FONT_BLACK = FONT_DIR / "ariblk.ttf"
FONT_NARROW_BOLD = FONT_DIR / "ARIALNB.TTF"


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def wrap_text(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        trial = " ".join(current + [word])
        if text_size(draw, trial, fnt)[0] <= max_width or not current:
            current.append(word)
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def draw_wrapped(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    fnt: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    max_width: int,
    line_gap: int,
    align: str = "left",
) -> int:
    x, y = xy
    for line in wrap_text(draw, text, fnt, max_width):
        line_w, line_h = text_size(draw, line, fnt)
        if align == "center":
            tx = x + (max_width - line_w) // 2
        elif align == "right":
            tx = x + max_width - line_w
        else:
            tx = x
        draw.text((tx, y), line, font=fnt, fill=fill)
        y += line_h + line_gap
    return y


def add_shadow(base: Image.Image, layer: Image.Image, offset=(0, 30), blur=60, alpha=90) -> None:
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    mask = layer.split()[-1]
    shadow_layer = Image.new("RGBA", base.size, (0, 0, 0, alpha))
    shadow.paste(shadow_layer, offset, mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(shadow)
    base.alpha_composite(layer)


def rounded_panel(
    base: Image.Image,
    box: tuple[int, int, int, int],
    fill: tuple[int, int, int, int],
    radius: int,
    outline: tuple[int, int, int, int] | None = None,
    width: int = 4,
    shadow=True,
) -> ImageDraw.ImageDraw:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
    if shadow:
        add_shadow(base, layer, blur=46, alpha=45)
    else:
        base.alpha_composite(layer)
    return ImageDraw.Draw(base)


def draw_bg(img: Image.Image) -> None:
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    y_grad = np.linspace(0, 1, H)[:, None]
    x_grad = np.linspace(0, 1, W)[None, :]
    base = np.array([251, 255, 252])
    mint = np.array([232, 249, 240])
    green = np.array([218, 244, 231])
    mix = (base * (1 - y_grad) + mint * y_grad)[:, None, :]
    side = (np.sin(x_grad * math.pi * 2.1 + y_grad * 5.5) + 1) / 2
    arr[:] = np.clip(mix + (green - base) * side[..., None] * 0.28, 0, 255)
    bg = Image.fromarray(arr, "RGB").convert("RGBA")
    img.alpha_composite(bg)
    d = ImageDraw.Draw(img, "RGBA")

    # Circuit traces on left.
    for i in range(26):
        x = 90 + i * 46
        d.line((x, 850, x, H - 1260), fill=(27, 129, 91, 48), width=4)
        for j in range(9):
            y = 1080 + j * 990 + (i % 4) * 80
            d.line((x, y, x + 180 + (i % 3) * 55, y), fill=(27, 129, 91, 42), width=4)
            d.ellipse((x + 168, y - 13, x + 194, y + 13), fill=(27, 129, 91, 62))

    # Dotted wave on right.
    for j in range(110):
        yy = 900 + j * 82
        wave = math.sin(j / 7.0) * 310
        for k in range(8):
            xx = W - 720 + wave + k * 78
            if 0 < xx < W:
                r = 5 + (k % 3)
                d.ellipse((xx - r, yy - r, xx + r, yy + r), fill=(16, 116, 80, 40))

    # Top and bottom ribbons.
    d.pieslice((-780, -900, 2600, 1750), 8, 172, fill=(0, 96, 57, 225))
    d.pieslice((-540, -750, 2320, 1360), 10, 170, fill=(56, 163, 107, 160))
    d.pieslice((-250, -570, 1960, 1000), 12, 168, fill=(245, 255, 247, 230))
    d.polygon([(0, H - 1180), (W, H - 1880), (W, H), (0, H)], fill=(0, 87, 55, 235))
    d.polygon([(0, H - 980), (W, H - 1590), (W, H - 1310), (0, H - 690)], fill=(95, 181, 125, 160))
    d.polygon([(0, H - 750), (W, H - 1310), (W, H - 1120), (0, H - 520)], fill=(255, 255, 255, 225))

    # Subtle spark nodes.
    for i in range(95):
        x = int((i * 147) % W)
        y = int(7350 + ((i * 251) % 2650))
        r = 7 + (i % 5)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, 105))
        if i % 4 == 0:
            d.line((x - 55, y, x + 55, y), fill=(255, 255, 255, 40), width=3)
            d.line((x, y - 55, x, y + 55), fill=(255, 255, 255, 40), width=3)


def draw_logo_strip(img: Image.Image) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    logo_y = 105
    labels = ["MJIIT 15", "MJIIT", "UTM", "ASCEND\n2030"]
    x_positions = [880, 1435, 1990, 2545]
    for x, label in zip(x_positions, labels):
        d.rounded_rectangle((x - 205, logo_y, x + 205, logo_y + 270), radius=42, fill=(255, 255, 255, 225), outline=(0, 96, 57, 90), width=5)
        lines = label.split("\n")
        yy = logo_y + 78 if len(lines) == 1 else logo_y + 55
        for line in lines:
            tw, th = text_size(d, line, font(FONT_BLACK, 58))
            d.text((x - tw // 2, yy), line, font=font(FONT_BLACK, 58), fill=GREEN_DARK)
            yy += th + 6
    d.rounded_rectangle((250, 410, W - 250, 1035), radius=68, fill=(255, 255, 255, 218))
    d.text((W // 2 - text_size(d, "MALAYSIA-JAPAN INTERNATIONAL INSTITUTE OF TECHNOLOGY", font(FONT_BOLD, 72))[0] // 2, 475), "MALAYSIA-JAPAN INTERNATIONAL INSTITUTE OF TECHNOLOGY", font=font(FONT_BOLD, 72), fill=INK)
    d.text((W // 2 - text_size(d, "DEPARTMENT OF COMPUTER SCIENCE", font(FONT_BOLD, 52))[0] // 2, 585), "DEPARTMENT OF COMPUTER SCIENCE", font=font(FONT_BOLD, 52), fill=MUTED)
    d.text((W // 2 - text_size(d, "BACHELOR OF COMPUTER SCIENCE", font(FONT_BLACK, 82))[0] // 2, 735), "BACHELOR OF COMPUTER SCIENCE", font=font(FONT_BLACK, 82), fill=GREEN)
    d.text((W // 2 - text_size(d, "(SOFTWARE ENGINEERING) WITH HONOURS", font(FONT_BLACK, 67))[0] // 2, 845), "(SOFTWARE ENGINEERING) WITH HONOURS", font=font(FONT_BLACK, 67), fill=GREEN_DARK)


def draw_title(img: Image.Image) -> None:
    rounded_panel(img, (270, 1080, W - 270, 1690), (0, 89, 52, 248), 105, shadow=True)
    d = ImageDraw.Draw(img, "RGBA")
    title = ["EPUSTAKA MUNSHI", "SMART LIBRARY SYSTEM WITH", "OCR LEDGER DIGITIZATION"]
    yy = 1193
    for i, line in enumerate(title):
        f = font(FONT_BLACK, 118 if i == 0 else 106)
        tw, th = text_size(d, line, f)
        d.text((W // 2 - tw // 2, yy), line, font=f, fill=WHITE)
        yy += th + 20


def draw_hero(img: Image.Image) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    rounded_panel(img, (320, 1830, W - 320, 3320), (255, 255, 255, 228), 95, outline=(157, 220, 188, 170), shadow=True)
    d.text((500, 1975), "FROM PAPER LEDGER", font=font(FONT_BOLD, 48), fill=MUTED)
    d.text((W - 1190, 1975), "TO SMART CATALOGUE", font=font(FONT_BOLD, 48), fill=MUTED)
    d.text((W // 2 - text_size(d, "OCR + HUMAN VERIFICATION", font(FONT_BLACK, 76))[0] // 2, 2018), "OCR + HUMAN VERIFICATION", font=font(FONT_BLACK, 76), fill=GREEN_DARK)

    # Ledger page.
    d.rounded_rectangle((500, 2200, 1370, 3035), radius=45, fill=(250, 255, 252, 255), outline=(40, 132, 91, 160), width=6)
    d.text((585, 2280), "BUKU INDUK", font=font(FONT_BLACK, 52), fill=GREEN_DARK)
    for i in range(9):
        y = 2390 + i * 66
        d.line((585, y, 1275, y), fill=(0, 100, 69, 88), width=5)
        d.line((585, y + 30, 1120 - (i % 4) * 50, y + 30), fill=(112, 93, 80, 80), width=4)

    # OCR beam.
    beam = Image.new("RGBA", img.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(beam, "RGBA")
    bd.polygon([(1300, 2240), (2300, 2120), (2420, 2980), (1380, 3105)], fill=(98, 228, 179, 48))
    bd.line((1365, 2680, 2370, 2560), fill=(93, 238, 176, 205), width=18)
    beam = beam.filter(ImageFilter.GaussianBlur(4))
    img.alpha_composite(beam)
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle((1490, 2500, 2110, 2675), radius=42, fill=(0, 99, 64, 245))
    d.text((W // 2 - text_size(d, "VERIFY", font(FONT_BLACK, 58))[0] // 2, 2555), "VERIFY", font=font(FONT_BLACK, 58), fill=WHITE)

    # Digital cards.
    card_x = 2300
    for i in range(4):
        y = 2200 + i * 195
        d.rounded_rectangle((card_x, y, W - 580, y + 140), radius=35, fill=(247, 255, 251, 255), outline=(40, 132, 91, 120), width=4)
        d.rounded_rectangle((card_x + 35, y + 34, card_x + 125, y + 106), radius=18, fill=(218, 246, 231, 255))
        d.line((card_x + 165, y + 43, W - 720, y + 43), fill=(0, 92, 58, 165), width=8)
        d.line((card_x + 165, y + 86, W - 895, y + 86), fill=(0, 92, 58, 88), width=6)

    d.text((520, 3185), "Digitize old records", font=font(FONT_BOLD, 42), fill=GREEN_DARK)
    d.text((W // 2 - text_size(d, "Review before import", font(FONT_BOLD, 42))[0] // 2, 3185), "Review before import", font=font(FONT_BOLD, 42), fill=GREEN_DARK)
    d.text((W - 1080, 3185), "Search and circulate", font=font(FONT_BOLD, 42), fill=GREEN_DARK)

    tagline = "Transforms handwritten ledger records into verified, searchable library data."
    draw_wrapped(d, (560, 3425), tagline, font(FONT_BOLD, 62), GREEN_DARK, W - 1120, 16, align="center")


def draw_icon(d: ImageDraw.ImageDraw, cx: int, cy: int, kind: str) -> None:
    d.ellipse((cx - 85, cy - 85, cx + 85, cy + 85), fill=(255, 255, 255, 240), outline=(0, 99, 70, 160), width=8)
    c = GREEN_DARK
    if kind == "intro":
        d.ellipse((cx - 32, cy - 50, cx + 32, cy + 18), outline=c, width=8)
        d.line((cx - 25, cy + 30, cx + 25, cy + 30), fill=c, width=8)
        d.line((cx - 17, cy + 48, cx + 17, cy + 48), fill=c, width=8)
    elif kind == "problem":
        d.polygon([(cx, cy - 58), (cx - 58, cy + 52), (cx + 58, cy + 52)], outline=c, fill=None)
        d.line((cx, cy - 18, cx, cy + 23), fill=c, width=10)
        d.ellipse((cx - 6, cy + 37, cx + 6, cy + 49), fill=c)
    elif kind == "method":
        d.ellipse((cx - 38, cy - 38, cx + 38, cy + 38), outline=c, width=8)
        for a in range(0, 360, 45):
            x1 = cx + math.cos(math.radians(a)) * 48
            y1 = cy + math.sin(math.radians(a)) * 48
            x2 = cx + math.cos(math.radians(a)) * 67
            y2 = cy + math.sin(math.radians(a)) * 67
            d.line((x1, y1, x2, y2), fill=c, width=7)
    elif kind == "design":
        d.rounded_rectangle((cx - 55, cy - 43, cx + 55, cy + 43), radius=10, outline=c, width=8)
        d.line((cx - 55, cy - 14, cx + 55, cy - 14), fill=c, width=6)
        d.line((cx - 18, cy - 14, cx - 18, cy + 43), fill=c, width=6)
    elif kind == "results":
        for i, h in enumerate([42, 70, 98]):
            x = cx - 55 + i * 44
            d.rounded_rectangle((x, cy + 55 - h, x + 26, cy + 55), radius=8, outline=c, width=7)
        d.line((cx - 65, cy + 60, cx + 65, cy + 60), fill=c, width=7)
        d.line((cx - 60, cy - 50, cx + 60, cy - 52), fill=(120, 104, 228, 170), width=7)
    elif kind == "conclusion":
        d.line((cx - 55, cy, cx - 13, cy + 42), fill=c, width=13)
        d.line((cx - 13, cy + 42, cx + 58, cy - 46), fill=c, width=13)


def draw_section_card(
    img: Image.Image,
    number: str,
    title: str,
    bullets: list[str],
    x: int,
    y: int,
    icon: str,
    side: str,
) -> None:
    card_w, card_h = 1390, 610
    rounded_panel(img, (x, y, x + card_w, y + card_h), (255, 255, 255, 235), 70, outline=(151, 214, 183, 160), width=5, shadow=True)
    d = ImageDraw.Draw(img, "RGBA")
    icon_x = x + 150 if side == "left" else x + card_w - 150
    draw_icon(d, icon_x, y + 160, icon)
    num_x = x + card_w - 220 if side == "left" else x + 60
    d.rounded_rectangle((num_x, y + 55, num_x + 160, y + 130), radius=35, fill=(229, 248, 237, 255))
    d.text((num_x + 37, y + 66), number, font=font(FONT_BLACK, 40), fill=GREEN)
    text_x = x + 285 if side == "left" else x + 80
    max_w = 1010 if side == "left" else 1000
    d.text((text_x, y + 72), title.upper(), font=font(FONT_BLACK, 58), fill=GREEN_DARK)
    yy = y + 180
    for bullet in bullets:
        d.ellipse((text_x, yy + 17, text_x + 18, yy + 35), fill=PURPLE if "OCR" in bullet or "verified" in bullet else GREEN_2)
        yy = draw_wrapped(d, (text_x + 42, yy), bullet, font(FONT_BOLD, 37), INK, max_w - 50, 9) + 18


def draw_content_flow(img: Image.Image) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    start_y, end_y = 4050, 8200
    cx = W // 2
    for r, alpha in [(28, 28), (15, 80), (6, 180)]:
        d.line((cx, start_y, cx, end_y), fill=(0, 131, 83, alpha), width=r)
    for y in [4180, 4920, 5660, 6400, 7140, 7880]:
        d.ellipse((cx - 58, y - 58, cx + 58, y + 58), fill=(255, 255, 255, 255), outline=(0, 111, 70, 220), width=12)
        d.ellipse((cx - 20, y - 20, cx + 20, y + 20), fill=LIME)

    draw_section_card(
        img,
        "01",
        "Introduction",
        ["7,000+ books still depend on manual ledger records.",
         "Goal: searchable catalogue and smarter circulation."],
        270,
        3890,
        "intro",
        "left",
    )
    draw_section_card(
        img,
        "02",
        "Problem Statement",
        ["Buku Induk records are fragile, slow to search, and hard to migrate.",
         "Manual loans make status tracking inefficient."],
        W - 1660,
        4630,
        "problem",
        "right",
    )
    draw_section_card(
        img,
        "03",
        "Methodology",
        ["Agile Scrum with librarian stakeholder feedback.",
         "OCR upload, extraction, correction, and verified import."],
        270,
        5370,
        "method",
        "left",
    )
    draw_section_card(
        img,
        "04",
        "Design & Analysis",
        ["React, Flask, Supabase, roles, and barcode circulation.",
         "Human-in-the-loop OCR protects catalogue quality."],
        W - 1660,
        6110,
        "design",
        "right",
    )
    draw_section_card(
        img,
        "05",
        "Results",
        ["Searchable catalogue and faster checkout-return.",
         "Verified OCR reduces retyping while preserving evidence."],
        270,
        6850,
        "results",
        "left",
    )
    draw_section_card(
        img,
        "06",
        "Conclusion",
        ["A school-ready smart library workflow.",
         "Future: reports, reminders, reservations, and integration."],
        W - 1660,
        7590,
        "conclusion",
        "right",
    )


def draw_novelty(img: Image.Image) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    rounded_panel(img, (350, 8400, W - 350, 9510), (0, 92, 58, 244), 95, shadow=True)
    d.text((W // 2 - text_size(d, "PROJECT NOVELTY & CONTRIBUTION", font(FONT_BLACK, 84))[0] // 2, 8570), "PROJECT NOVELTY & CONTRIBUTION", font=font(FONT_BLACK, 84), fill=WHITE)
    d.text((W // 2 - text_size(d, "What makes this project stand out", font(FONT_BOLD, 44))[0] // 2, 8675), "What makes this project stand out", font=font(FONT_BOLD, 44), fill=(210, 251, 229))
    items = [
        ("01", "Human-Verified OCR", "Ledger extraction is reviewed before it becomes catalogue data."),
        ("02", "School-Ready Workflow", "Roles for librarian, prefect, student, and administrator."),
        ("03", "Digital Preservation", "Old records become searchable evidence instead of fragile paper."),
    ]
    x0 = 520
    for i, (num, title, body) in enumerate(items):
        x = x0 + i * 850
        d.rounded_rectangle((x, 8840, x + 720, 9340), radius=58, fill=(255, 255, 255, 242))
        d.ellipse((x + 48, 8895, x + 178, 9025), fill=(225, 248, 235, 255))
        d.text((x + 78, 8924), num, font=font(FONT_BLACK, 40), fill=GREEN)
        d.text((x + 55, 9075), title, font=font(FONT_BLACK, 42), fill=GREEN_DARK)
        draw_wrapped(d, (x + 55, 9160), body, font(FONT_BOLD, 30), INK, 610, 8)


def draw_footer(img: Image.Image) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    d.text((W // 2 - text_size(d, "IN COLLABORATION WITH", font(FONT_BLACK, 46))[0] // 2, 9700), "IN COLLABORATION WITH", font=font(FONT_BLACK, 46), fill=GREEN_DARK)
    d.text((W // 2 - text_size(d, "SMK ABDULLAH MUNSHI", font(FONT_BLACK, 62))[0] // 2, 9780), "SMK ABDULLAH MUNSHI", font=font(FONT_BLACK, 62), fill=INK)

    people = [
        (880, "STUDENT", "WAN ZAFIRZAN BIN WAN TARMIZAN", "A22MJ8003", "EMAIL: [ADD EMAIL]"),
        (W - 880, "SUPERVISOR", "DR. SITI NUR KHADIJAH AISHAH", "BINTI IBRAHIM", "EMAIL: [ADD EMAIL]"),
    ]
    for x, role, name1, name2, email in people:
        d.ellipse((x - 250, 10005, x + 250, 10505), fill=(238, 249, 243, 255), outline=(255, 255, 255, 255), width=12)
        d.ellipse((x - 116, 10100, x + 116, 10332), outline=GREEN_DARK, width=12)
        d.arc((x - 170, 10270, x + 170, 10500), 200, 340, fill=GREEN_DARK, width=12)
        d.rounded_rectangle((x - 545, 10525, x + 545, 10712), radius=45, fill=(255, 255, 255, 245))
        d.text((x - text_size(d, role, font(FONT_BLACK, 34))[0] // 2, 10546), role, font=font(FONT_BLACK, 34), fill=GREEN)
        d.text((x - text_size(d, name1, font(FONT_BOLD, 32))[0] // 2, 10592), name1, font=font(FONT_BOLD, 32), fill=INK)
        d.text((x - text_size(d, name2, font(FONT_BOLD, 31))[0] // 2, 10634), name2, font=font(FONT_BOLD, 31), fill=INK)
        d.text((x - text_size(d, email, font(FONT_BOLD, 29))[0] // 2, 10675), email, font=font(FONT_BOLD, 29), fill=MUTED)

    footer = "FYP SYMPOSIUM 2026   |   FINAL YEAR PROJECT (FYP) UNIT, MJIIT"
    d.text((W // 2 - text_size(d, footer, font(FONT_BLACK, 34))[0] // 2, H - 74), footer, font=font(FONT_BLACK, 34), fill=WHITE)


def main() -> None:
    img = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    draw_bg(img)
    draw_logo_strip(img)
    draw_title(img)
    draw_hero(img)
    draw_content_flow(img)
    draw_novelty(img)
    draw_footer(img)
    rgb = img.convert("RGB")
    rgb.save(PRINT_PATH, quality=96, optimize=True)
    preview = rgb.resize((1200, 3600), Image.Resampling.LANCZOS)
    preview.save(PREVIEW_PATH, quality=94, optimize=True)
    print(PRINT_PATH)
    print(PREVIEW_PATH)


if __name__ == "__main__":
    main()
