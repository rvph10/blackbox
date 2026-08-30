"""Cartes générées (Pillow) — classement et bienvenue (ADR-022).

Avatars ronds récupérés depuis le CDN Discord, couronne dessinée par code
sur le n°1. Rendu ~1 s, PNG ~150 Ko.
"""

import io
import logging

import aiohttp
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("blackbox-bot.cards")

_FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
]
_FONT_BOLD_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
]

_BG = (24, 26, 31)
_CARD = (32, 35, 42)
_WHITE = (240, 242, 245)
_MUTED = (154, 164, 178)
_GOLD = (241, 196, 15)
_SILVER = (191, 199, 213)
_BRONZE = (205, 127, 50)
_PODIUM_COLOURS = [_GOLD, _SILVER, _BRONZE]


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for path in _FONT_BOLD_PATHS if bold else _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def _text_centered(draw, cx, y, text, font, fill):
    w = draw.textlength(text, font=font)
    draw.text((cx - w / 2, y), text, font=font, fill=fill)


def _circle(image: Image.Image, diameter: int) -> Image.Image:
    image = image.convert("RGBA").resize((diameter, diameter))
    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, diameter, diameter), fill=255)
    out = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    out.paste(image, (0, 0), mask)
    return out


def _placeholder_avatar(diameter: int, label: str, seed: int) -> Image.Image:
    palette = [
        (88, 101, 242),
        (235, 69, 158),
        (87, 242, 135),
        (254, 231, 92),
        (237, 66, 69),
    ]
    colour = palette[seed % len(palette)]
    img = Image.new("RGBA", (diameter, diameter), (*colour, 255))
    draw = ImageDraw.Draw(img)
    initial = (label or "?")[0].upper()
    f = _font(int(diameter * 0.45), bold=True)
    _text_centered(draw, diameter / 2, diameter * 0.24, initial, f, _WHITE)
    return _circle(img, diameter)


def _draw_crown(draw: ImageDraw.ImageDraw, cx: float, top: float, width: float) -> None:
    h = width * 0.66
    left, right = cx - width / 2, cx + width / 2
    tips = [(left, top), (cx, top - h * 0.10), (right, top)]
    points = [
        (left, top + h),
        (left, top),
        ((left + cx) / 2, top + h * 0.52),
        tips[1],
        ((cx + right) / 2, top + h * 0.52),
        (right, top),
        (right, top + h),
    ]
    draw.polygon(points, fill=_GOLD)
    band_top = top + h - h * 0.24
    draw.rounded_rectangle(
        [left - width * 0.05, band_top, right + width * 0.05, top + h + h * 0.05],
        radius=width * 0.06,
        fill=_GOLD,
    )
    for bx, by in tips:
        r = width * 0.08
        draw.ellipse([bx - r, by - r, bx + r, by + r], fill=(255, 232, 150))
    for gx in (cx - width * 0.24, cx, cx + width * 0.24):
        r = width * 0.05
        gy = band_top + h * 0.11
        draw.ellipse([gx - r, gy - r, gx + r, gy + r], fill=(231, 76, 90))


async def fetch_avatar(url: str | None) -> Image.Image | None:
    if not url:
        return None
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as s:
            async with s.get(url) as resp:
                if resp.status != 200:
                    return None
                return Image.open(io.BytesIO(await resp.read()))
    except (aiohttp.ClientError, OSError):
        return None


def _avatar_or_placeholder(
    avatar: Image.Image | None, diameter: int, label: str, seed: int
) -> Image.Image:
    if avatar is not None:
        try:
            return _circle(avatar, diameter)
        except OSError:
            pass
    return _placeholder_avatar(diameter, label, seed)


def render_scoreboard(
    entries: list[dict],
    *,
    period_days: int,
    movie: str | None,
    total_seconds: float,
    total_plays: int,
) -> io.BytesIO:
    """entries : [{name, avatar (Image|None), seconds}], déjà triées (max 3)."""
    W, H = 1200, 690
    img = Image.new("RGB", (W, H), _BG)
    draw = ImageDraw.Draw(img)

    _text_centered(
        draw, W / 2, 44, "CLASSEMENT DE LA QUINZAINE", _font(46, bold=True), _WHITE
    )
    _text_centered(
        draw,
        W / 2,
        104,
        f"les {period_days} derniers jours sur Blackbox",
        _font(24),
        _MUTED,
    )

    order = [1, 0, 2]  # 2e, 1er, 3e de gauche à droite
    pedestal_h = {0: 210, 1: 168, 2: 142}
    col_w, gap = 250, 34
    x0 = (W - (3 * col_w + 2 * gap)) / 2
    baseline = H - 128
    d = 128

    for slot, rank in enumerate(order):
        cx = x0 + slot * (col_w + gap) + col_w / 2
        ph = pedestal_h[rank]
        ptop = baseline - ph
        ring = _PODIUM_COLOURS[rank]
        entry = entries[rank] if rank < len(entries) else None

        draw.rounded_rectangle(
            [cx - col_w / 2, ptop, cx + col_w / 2, baseline], radius=16, fill=_CARD
        )

        if entry is None:
            _text_centered(draw, cx, ptop + ph / 2 - 18, "—", _font(34), _MUTED)
            continue

        ay = ptop - d - 4
        av = _avatar_or_placeholder(entry.get("avatar"), d, entry["name"], rank)
        img.paste(av, (int(cx - d / 2), int(ay)), av)
        draw.ellipse(
            [cx - d / 2 - 4, ay - 4, cx + d / 2 + 4, ay + d + 4], outline=ring, width=5
        )
        if rank == 0:
            _draw_crown(draw, cx, ay - 44, 90)

        _text_centered(draw, cx, ptop + 14, str(rank + 1), _font(38, bold=True), ring)
        _text_centered(
            draw, cx, ptop + 60, _trim(entry["name"], 15), _font(29, bold=True), _WHITE
        )
        _text_centered(
            draw, cx, ptop + 100, _fmt_duration(entry["seconds"]), _font(23), _MUTED
        )

    draw.line([80, H - 84, W - 80, H - 84], fill=_CARD, width=2)
    stats = f"{_fmt_duration(total_seconds)} regardées   ·   {total_plays} lectures"
    if movie:
        stats = f"à l'affiche : {_trim(movie, 38)}      |      " + stats
    _text_centered(draw, W / 2, H - 60, stats, _font(24), _MUTED)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def render_welcome(name: str, avatar: Image.Image | None) -> io.BytesIO:
    W, H = 1000, 360
    img = Image.new("RGB", (W, H), _BG)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([24, 24, W - 24, H - 24], radius=20, fill=_CARD)

    d = 180
    ax, ay = 76, (H - d) // 2
    av = _avatar_or_placeholder(avatar, d, name, 0)
    img.paste(av, (ax, ay), av)
    draw.ellipse([ax - 4, ay - 4, ax + d + 4, ay + d + 4], outline=_GOLD, width=4)

    tx = ax + d + 60
    draw.text(
        (tx, 112), "BIENVENUE SUR BLACKBOX", font=_font(33, bold=True), fill=_GOLD
    )
    draw.text((tx, 162), _trim(name, 22), font=_font(50, bold=True), fill=_WHITE)
    draw.text(
        (tx, 240),
        "ton compte est prêt — vérifie tes messages privés",
        font=_font(22),
        fill=_MUTED,
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _trim(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _fmt_duration(seconds: float) -> str:
    hrs = seconds / 3600
    if hrs >= 1:
        return f"{hrs:.1f} h"
    return f"{int(seconds // 60)} min"
