"""Bikin gambar welcome: background + foto profil bulat + tulisan WELCOME + username."""
import glob
import io
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import config

WIDTH, HEIGHT = 1024, 450
AVATAR_SIZE = 210
ACCENT = (72, 140, 255)  # biru, senada sama grid di background

HERE = os.path.dirname(os.path.abspath(__file__))


def _load_font(candidates, size, weight):
    for path in candidates:
        full = path if os.path.isabs(path) else os.path.join(HERE, path)
        for match in sorted(glob.glob(full)):
            font = ImageFont.truetype(match, size)
            try:
                font.set_variation_by_name(weight)  # font variable (misal Montserrat.ttf)
            except (OSError, ValueError):
                pass
            return font
    return ImageFont.load_default(size)


def _background():
    bg = Image.open(os.path.join(HERE, config.WELCOME_BACKGROUND)).convert("RGB")
    # Skala ke lebar kartu, lalu potong bagian sesuai WELCOME_BG_FOCUS (0 = atas, 1 = bawah)
    scale = WIDTH / bg.width
    bg = bg.resize((WIDTH, max(HEIGHT, round(bg.height * scale))), Image.LANCZOS)
    top = round((bg.height - HEIGHT) * config.WELCOME_BG_FOCUS)
    bg = bg.crop((0, top, WIDTH, top + HEIGHT))

    # Gelapkan sedikit di tengah supaya teks kebaca
    shade = Image.new("L", (WIDTH, HEIGHT), 0)
    ImageDraw.Draw(shade).ellipse((WIDTH * 0.2, -60, WIDTH * 0.8, HEIGHT + 60), fill=150)
    shade = shade.filter(ImageFilter.GaussianBlur(80))
    return Image.composite(Image.new("RGB", bg.size, (0, 0, 0)), bg, shade)


def _circle_avatar(avatar_bytes):
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS)
    mask = Image.new("L", (AVATAR_SIZE * 4, AVATAR_SIZE * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, AVATAR_SIZE * 4, AVATAR_SIZE * 4), fill=255)
    avatar.putalpha(mask.resize((AVATAR_SIZE, AVATAR_SIZE), Image.LANCZOS))
    return avatar


def _text_centered(card, y, text, font, glow=True):
    draw = ImageDraw.Draw(card)
    w = draw.textlength(text, font=font)
    x = (WIDTH - w) / 2
    if glow:
        layer = Image.new("RGBA", card.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((x, y), text, font=font, fill=ACCENT + (255,))
        card.alpha_composite(layer.filter(ImageFilter.GaussianBlur(10)))
    draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0, 160))
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))


def make_welcome_card(avatar_bytes: bytes, username: str) -> io.BytesIO:
    card = _background().convert("RGBA")

    cx, cy = WIDTH // 2, 40 + AVATAR_SIZE // 2
    ring = AVATAR_SIZE // 2 + 8

    # Glow biru + ring putih di sekeliling foto
    glow = Image.new("RGBA", card.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((cx - ring - 6, cy - ring - 6, cx + ring + 6, cy + ring + 6), fill=ACCENT + (200,))
    card.alpha_composite(glow.filter(ImageFilter.GaussianBlur(18)))
    ImageDraw.Draw(card).ellipse((cx - ring, cy - ring, cx + ring, cy + ring), fill=(255, 255, 255, 255))
    card.alpha_composite(_circle_avatar(avatar_bytes), (cx - AVATAR_SIZE // 2, cy - AVATAR_SIZE // 2))

    _text_centered(card, 272, "WELCOME", _load_font(config.FONT_TITLE, 86, "Black"))

    name = username.upper()
    name_font = _load_font(config.FONT_NAME, 42, "ExtraBold")
    while ImageDraw.Draw(card).textlength(name, font=name_font) > WIDTH - 80 and len(name) > 4:
        name = name[:-2] + "…"
    _text_centered(card, 370, name, name_font, glow=False)

    out = io.BytesIO()
    card.convert("RGB").save(out, "PNG")
    out.seek(0)
    return out
