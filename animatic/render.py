#!/usr/bin/env python3
"""Render the picture for the animatic of "The Faithful Friend".

Every frame is drawn procedurally: 30 illustrated storyboard panels with the
camera moves, cuts, dissolves, captions and timings of the production package.
Nothing here is photographed, licensed archive or AI-generated video.

Usage:
  render.py segment <index> <count> <out.mp4>   render one slice of the timeline
  render.py sheet <out.jpg>                     contact sheet, one frame per shot
  render.py frame <n> <out.png>                 a single frame
"""
import json
import math
import os
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from timeline import FPS, SHOTS, TOTAL_FRAMES, DISSOLVES, TITLE

W, H = 3840, 2160
DW, DH = 2112, 1188            # plates are drawn at half size, 1.1x overscan
HERE = os.path.dirname(os.path.abspath(__file__))
SERIF = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
ITALIC = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"
SANS = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

CREAM = (226, 214, 182)
WOOD = (112, 84, 58)


# ---------------------------------------------------------------- helpers
def font(path, size):
    return ImageFont.truetype(path, size)


def grad(w, h, top, bot):
    t = np.linspace(0, 1, h)[:, None, None]
    a = np.array(top, float)[None, None, :]
    b = np.array(bot, float)[None, None, :]
    arr = (a * (1 - t) + b * t) * np.ones((1, w, 1))
    return Image.fromarray(arr.astype(np.uint8))


def soft(base, fn, r=0):
    """Draw with fn(ImageDraw) on a transparent layer, blur it, lay it on base."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    fn(ImageDraw.Draw(layer))
    if r:
        layer = layer.filter(ImageFilter.GaussianBlur(r))
    base.paste(layer, (0, 0), layer)
    return base


def glow(base, cx, cy, rx, ry, col, r):
    return soft(base, lambda d: d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=col), r)


def finish(img, vig=0.45, noise=1.2, seed=0):
    """Upscale a half-size plate to full size, add vignette and static grain."""
    img = img.convert("RGB").resize((img.width * 2, img.height * 2), Image.BICUBIC)
    a = np.asarray(img).astype(np.float32)
    h, w = a.shape[:2]
    if vig:
        y = np.linspace(-1, 1, h)[:, None]
        x = np.linspace(-1, 1, w)[None, :]
        a *= (1 - vig * np.clip((x * x + y * y) / 2, 0, 1) ** 1.5)[:, :, None]
    if noise:
        rng = np.random.default_rng(seed)
        a += rng.normal(0, noise, (h, w, 1)).astype(np.float32)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def sprite(w, h, fn, r=0):
    im = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
    fn(ImageDraw.Draw(im))
    if r:
        im = im.filter(ImageFilter.GaussianBlur(r))
    return im


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def lerp(a, b, u):
    return a + (b - a) * u


def cod_points(L):
    """Outline of an Atlantic cod, head to the left, in a box L x 0.42L."""
    h = L * 0.42
    top, bot = [], []
    for i in range(41):
        x = i / 40 * 0.84
        th = 0.17 * math.sin(math.pi * (x / 0.84) ** 0.62) ** 0.75 + 0.012
        top.append((x * L, h / 2 - th * L))
        bot.append((x * L, h / 2 + th * L * 0.9))
    tail = [(0.90 * L, h / 2 - 0.10 * L), (L, h / 2 - 0.13 * L), (0.965 * L, h / 2),
            (L, h / 2 + 0.13 * L), (0.90 * L, h / 2 + 0.10 * L)]
    return top + tail + bot[::-1]


def draw_cod(d, x, y, L, col, flip=False, detail=True):
    pts = cod_points(L)
    h = L * 0.42
    fx = (lambda px: x + L - px) if flip else (lambda px: x + px)
    P = lambda p: (fx(p[0]), y + p[1])
    d.polygon([P(p) for p in pts], fill=col)
    dark = tuple(int(c * 0.82) for c in col[:3]) + (col[3] if len(col) > 3 else 255,)
    for a, b in ((0.25, 0.40), (0.43, 0.60), (0.63, 0.76)):          # three dorsal fins
        d.polygon([P((a * L, h / 2 - 0.15 * L)), P(((a * 0.6 + b * 0.4) * L, h / 2 - 0.24 * L)),
                   P((b * L, h / 2 - 0.13 * L))], fill=dark)
    for a, b in ((0.45, 0.60), (0.63, 0.76)):                        # two anal fins
        d.polygon([P((a * L, h / 2 + 0.13 * L)), P(((a * 0.6 + b * 0.4) * L, h / 2 + 0.21 * L)),
                   P((b * L, h / 2 + 0.11 * L))], fill=dark)
    if detail:
        d.line([P((0.06 * L, h / 2 + 0.06 * L)), P((0.05 * L, h / 2 + 0.12 * L))], fill=dark, width=max(2, int(L / 150)))
        e = L * 0.018
        ex, ey = P((0.085 * L, h / 2 - 0.035 * L))
        d.ellipse([ex - e, ey - e, ex + e, ey + e], fill=(20, 24, 22, 255))
        d.line([P((0.2 * L, h / 2 - 0.03 * L)), P((0.8 * L, h / 2 - 0.005 * L))],
               fill=tuple(min(255, int(c * 1.25)) for c in col[:3]) + (140,), width=max(1, int(L / 220)))


def split_cod(d, cx, cy, s, rot=0.0, col=CREAM):
    """A dried, split salt cod: a flat kite with the tail at the top."""
    shape = [(0, -1.05), (0.10, -0.95), (0.05, -0.8), (0.18, -0.55), (0.52, 0.45), (0.40, 0.95),
             (0.12, 0.78), (0, 0.9), (-0.12, 0.78), (-0.40, 0.95), (-0.52, 0.45), (-0.18, -0.55),
             (-0.05, -0.8), (-0.10, -0.95)]
    c, sn = math.cos(rot), math.sin(rot)
    T = lambda p: (cx + (p[0] * c - p[1] * sn) * s, cy + (p[0] * sn + p[1] * c) * s)
    edge = tuple(int(v * 0.78) for v in col)
    d.polygon([T(p) for p in shape], fill=col, outline=edge)
    d.line([T((0, -0.75)), T((0, 0.8))], fill=edge, width=max(2, int(s / 60)))
    for k in (-0.3, -0.05, 0.2, 0.45):
        d.line([T((-0.1 - (k + 0.6) * 0.3, k)), T((0, k + 0.12)), T((0.1 + (k + 0.6) * 0.3, k))],
               fill=edge, width=max(1, int(s / 110)))


def bust(d, cx, cy, s, col, apron=None):
    """Head and shoulders, seen square on. cy is the chin."""
    d.rounded_rectangle([cx - 0.95 * s, cy + 0.25 * s, cx + 0.95 * s, cy + 3.2 * s], radius=int(0.5 * s), fill=col)
    d.rectangle([cx - 0.22 * s, cy - 0.1 * s, cx + 0.22 * s, cy + 0.4 * s], fill=col)
    d.ellipse([cx - 0.42 * s, cy - 1.0 * s, cx + 0.42 * s, cy + 0.08 * s], fill=col)
    if apron:
        d.polygon([(cx - 0.45 * s, cy + 0.6 * s), (cx + 0.45 * s, cy + 0.6 * s),
                   (cx + 0.7 * s, cy + 3.2 * s), (cx - 0.7 * s, cy + 3.2 * s)], fill=apron)


def arm(d, x0, y0, x1, y1, w, col, hand=None):
    d.line([(x0, y0), (x1, y1)], fill=col, width=int(w))
    d.ellipse([x1 - w * 0.62, y1 - w * 0.62, x1 + w * 0.62, y1 + w * 0.62], fill=hand or col)


def wood(w=DW, h=DH, col=WOOD, seed=1):
    img = grad(w, h, tuple(int(c * 1.08) for c in col), tuple(int(c * 0.9) for c in col))
    rnd = random.Random(seed)

    def f(d):
        for i in range(0, h, 150):
            d.line([(0, i + rnd.randint(-6, 6)), (w, i + rnd.randint(-6, 6))], fill=(40, 28, 18, 150), width=3)
        for _ in range(160):
            y = rnd.randint(0, h)
            x = rnd.randint(0, w)
            d.line([(x, y), (x + rnd.randint(80, 500), y + rnd.randint(-3, 3))], fill=(60, 42, 26, 60), width=2)
    return soft(img, f, 1)


def shelves(img, seed=3, dim=1.0):
    rnd = random.Random(seed)
    w, h = img.size

    def f(d):
        for row in range(5):
            y = int(h * (0.08 + row * 0.13))
            d.rectangle([0, y + int(h * 0.105), w, y + int(h * 0.118)], fill=(52, 36, 24, 255))
            x = 20
            while x < w:
                bw = rnd.randint(34, 80)
                bh = rnd.randint(int(h * 0.05), int(h * 0.1))
                c = rnd.choice([(150, 60, 48), (170, 140, 70), (70, 96, 84), (190, 176, 150), (80, 70, 110), (140, 90, 50)])
                c = tuple(int(v * dim) for v in c)
                d.rectangle([x, y + int(h * 0.105) - bh, x + bw, y + int(h * 0.105)], fill=c + (255,))
                x += bw + rnd.randint(6, 22)
    return soft(img, f, 0)


def static_cam(pw, ph, z0=1.0, z1=1.0, dx=0, dy=0):
    def cam(u, t):
        e = ease(u)
        return pw / 2 + dx * (e - 0.5), ph / 2 + dy * (e - 0.5), lerp(z0, z1, e)
    return cam


# ---------------------------------------------------------------- the shots
def tank_plate(seed):
    img = grad(DW, DH, (6, 15, 15), (3, 8, 9))
    glow(img, DW * 0.5, DH * 0.42, 620, 330, (46, 78, 68, 255), 200)
    glow(img, DW * 0.3, DH * 0.2, 300, 120, (60, 90, 80, 120), 150)
    rnd = random.Random(seed)

    def f(d):
        for _ in range(140):
            x, y, r = rnd.randint(0, DW), rnd.randint(0, DH), rnd.choice([1, 1, 2])
            d.ellipse([x - r, y - r, x + r, y + r], fill=(150, 180, 165, rnd.randint(30, 110)))
        draw_cod(d, 250, 760, 330, (16, 30, 28, 200), flip=True, detail=False)
        draw_cod(d, 1560, 240, 260, (20, 36, 32, 170), detail=False)
    soft(img, f, 2)
    return finish(img, vig=0.7, seed=seed)


def b1():
    plate = tank_plate(1)
    cod = sprite(1700, 760, lambda d: draw_cod(d, 20, 20, 1640, (124, 140, 122, 255)), 2.5)

    def pos(t, u):
        return 3500 - 1900 * ease(u * 0.95), 820 + 30 * math.sin(t * 1.3), min(1, u / 0.55) * 0.95
    return dict(plate=plate, sprites=[(cod, pos)])


def b30():
    plate = tank_plate(1)
    cod = sprite(1700, 760, lambda d: draw_cod(d, 20, 20, 1640, (124, 140, 122, 255), flip=True), 2.5)

    def pos(t, u):
        return 1450 + 1500 * ease(u) ** 1.2, 840 - 50 * u, max(0, 1 - u / 0.8) * 0.95
    return dict(plate=plate, sprites=[(cod, pos)])


def b2():
    img = grad(DW, DH, (10, 24, 22), (5, 12, 12))
    glow(img, DW * 0.5, DH * 0.5, 800, 400, (40, 70, 60, 255), 220)
    plate = finish(img, vig=0.6, seed=2)

    def head(d):
        d.ellipse([-900, 120, 5200, 1900], fill=(128, 142, 120, 255))                 # flank
        d.polygon([(0, 1050), (500, 520), (1500, 250), (1500, 1800), (520, 1560)], fill=(128, 142, 120, 255))
        rnd = random.Random(5)
        for _ in range(260):                                                           # mottling
            x, y, r = rnd.randint(500, 3600), rnd.randint(300, 1100), rnd.randint(14, 44)
            d.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=(96, 108, 86, 150))
        d.line([(1500, 900), (3600, 800)], fill=(196, 204, 180, 200), width=22)        # pale lateral line
        d.ellipse([760, 640, 1120, 1000], fill=(196, 186, 128, 255))                   # eye
        d.ellipse([850, 730, 1030, 910], fill=(14, 18, 16, 255))
        d.ellipse([930, 760, 975, 805], fill=(220, 230, 220, 200))
        d.line([(60, 1080), (420, 1190), (700, 1210)], fill=(70, 82, 66, 255), width=20, joint="curve")   # mouth
        d.line([(420, 1500), (400, 1700), (440, 1880)], fill=(150, 160, 136, 255), width=26, joint="curve")  # barbel
        d.arc([1180, 500, 1700, 1700], 100, 250, fill=(92, 104, 84, 255), width=18)    # gill cover
    spr = sprite(3800, 2000, head, 5)
    return dict(plate=plate, sprites=[(spr, lambda t, u: (1500 - 1500 * u, 240 + 20 * math.sin(t), 1.0))])


def b3():
    img = Image.new("RGB", (DW, DH), (9, 11, 13))

    def win(d):
        d.rounded_rectangle([330, 150, 1780, 880], radius=40, fill=(58, 96, 88, 255))
    soft(img, win, 14)
    glow(img, 1050, 480, 500, 240, (96, 140, 126, 150), 150)

    def fish(d):
        draw_cod(d, 520, 330, 300, (26, 46, 42, 230), detail=False)
        draw_cod(d, 1180, 560, 380, (22, 40, 38, 230), flip=True, detail=False)
        draw_cod(d, 1400, 250, 200, (34, 58, 52, 200), detail=False)
    soft(img, fish, 3)
    glow(img, 1050, 1040, 760, 60, (40, 70, 64, 120), 60)                               # floor reflection
    soft(img, lambda d: bust(d, 800, 610, 200, (3, 4, 5, 255)), 3)                      # the visitor
    return dict(plate=finish(img, vig=0.6, seed=3), cam=static_cam(DW * 2, DH * 2, 1.0, 1.06))


def b4():
    y = np.linspace(0, 1, DH)[:, None]
    x = np.linspace(0, 1, DW)[None, :]
    d = 1.0 / (y + 0.16)
    rng = np.random.default_rng(4)
    v = np.zeros((DH, DW))
    for k in range(9):
        fx, fy, ph = rng.uniform(2, 9), rng.uniform(14, 40), rng.uniform(0, 6.28)
        v += np.sin(x * fx * d * 2.2 + y * d * fy + ph + 0.6 * np.sin(x * 5 + k)) / (1 + 0.25 * k)
    v = v / 3.5
    crest = np.clip(v - 0.55, 0, 1) * 1.6 * np.clip(y * 1.5, 0, 1)
    base = np.stack([84 + 26 * v, 96 + 26 * v, 100 + 25 * v], -1) + crest[..., None] * 90
    fog = np.exp(-y * 4.2)[..., None]
    arr = base * (1 - fog) + np.array([176, 181, 181]) * fog
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6))
    return dict(plate=finish(img, vig=0.3, seed=4), cam=static_cam(DW * 2, DH * 2, 1.0, 1.07, dy=-60))


# map projection for shot 5 (Mercator, 85W-45E, 26N-78N)
LON0, LON1, LAT0, LAT1 = -85.0, 45.0, 26.0, 78.0
MW = DW
_merc = lambda lat: math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
MH = int(MW * (_merc(LAT1) - _merc(LAT0)) / math.radians(LON1 - LON0))


def proj(lon, lat):
    return ((lon - LON0) / (LON1 - LON0) * MW,
            (_merc(LAT1) - _merc(max(min(lat, 84), -60))) / (_merc(LAT1) - _merc(LAT0)) * MH)


def b5():
    land = Image.new("L", (MW, MH), 0)
    dl = ImageDraw.Draw(land)
    gj = json.load(open(os.path.join(HERE, "data", "ne_110m_land.geojson")))
    for f in gj["features"]:
        g = f["geometry"]
        polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for p in polys:
            ring = p[0]
            if max(c[0] for c in ring) < LON0 - 30 or min(c[0] for c in ring) > LON1 + 30:
                continue
            dl.polygon([proj(lo, la) for lo, la in ring], fill=255)
    landa = np.asarray(land) > 128
    near = np.asarray(land.filter(ImageFilter.GaussianBlur(34))).astype(float) / 255 > 0.10
    # lon/lat of every pixel, to apply the limits of the range described by EUMOFA:
    # west Atlantic from Cape Hatteras (35N) north; Greenland; Iceland; east Atlantic
    # from the Bay of Biscay (about 44N) north to the Barents Sea; North Sea and Baltic.
    xs = LON0 + (np.arange(MW)[None, :] / MW) * (LON1 - LON0)
    m = _merc(LAT1) - (np.arange(MH)[:, None] / MH) * (_merc(LAT1) - _merc(LAT0))
    ys = np.degrees(2 * np.arctan(np.exp(m)) - math.pi / 2)
    west = (xs < -42) & (ys > 35) & (ys < 63) & ~((xs < -76) & (ys > 39.5)) & ~((xs < -66) & (ys > 51))
    green = (xs > -60) & (xs < -18) & (ys > 59) & (ys < 73)
    ice = (xs > -28) & (xs < -10) & (ys > 62) & (ys < 68)
    east = (xs > -15) & (ys > 44.2) & ~((xs > 1) & (ys < 48.5)) & ~((xs > 18) & (ys < 53))
    shelf = near & (west | green | ice | east)
    open_sea = ((xs > -5) & (xs < 12) & (ys > 51) & (ys < 62)) | ((xs > 12) & (xs < 45) & (ys > 69) & (ys < 76.5))
    rng_mask = (shelf | open_sea) & ~landa
    rm = Image.fromarray((rng_mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(18))

    img = Image.new("RGB", (MW, MH), (214, 208, 192))                      # sea, paper tone
    img.paste(Image.new("RGB", (MW, MH), (118, 146, 150)), (0, 0), rm.point(lambda v: int(v * 0.85)))
    img.paste(Image.new("RGB", (MW, MH), (236, 231, 218)), (0, 0), land)   # land
    edge = land.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(0.8))
    img.paste(Image.new("RGB", (MW, MH), (120, 112, 98)), (0, 0), edge.point(lambda v: min(255, v * 2)))
    plate = finish(img, vig=0.25, noise=1.8, seed=5)
    d = ImageDraw.Draw(plate)
    ink, f1, f2 = (70, 64, 54), font(ITALIC, 62), font(SERIF, 50)

    def label(lon, lat, text, fnt=f2, dx=0, dy=0, dot=False):
        px, py = proj(lon, lat)
        px, py = px * 2 + dx, py * 2 + dy
        if dot:
            d.ellipse([px - 9, py - 9, px + 9, py + 9], fill=ink)
            px += 26
            py -= 30
        d.text((px, py), text, font=fnt, fill=ink)
    label(13, 65.5, "NORWAY", dx=-60)
    label(-23, 64.3, "ICELAND", dx=-40, dy=-110)
    label(-48, 71, "GREENLAND")
    label(-57.5, 48.3, "Newfoundland", f1, dx=-60, dy=40)
    label(-7, 45.6, "Bay of Biscay", f1, dx=-330)
    label(-9.14, 38.72, "Lisbon", f1, dot=True, dx=-10)
    label(-8.6, 39.9, "PORTUGAL", dx=40, dy=-30)
    label(-40, 55.5, "Atlantic cod, Gadus morhua", f1)
    label(-40, 55.5, "approximate range (schematic)", font(ITALIC, 46), dy=74)
    pw, ph = plate.size

    def cam(u, t):
        return 2330, lerp(1130, ph - 1090, ease(u)), 1.0
    return dict(plate=plate, cam=cam)


def b6():
    img = grad(DW, DH, (146, 166, 188), (240, 208, 174))
    sky = grad(DW, int(DH * 0.5), (146, 166, 188), (243, 212, 178))
    img.paste(sky, (0, 0))
    glow(img, DW * 0.72, DH * 0.47, 420, 90, (255, 232, 196, 200), 90)
    soft(img, lambda d: d.polygon([(0, 560), (300, 536), (700, 548), (1100, 530), (1600, 546), (DW, 534),
                                   (DW, 600), (0, 600)], fill=(150, 152, 166, 255)), 5)       # far bank
    soft(img, lambda d: d.rectangle([0, 578, DW, 700], fill=(222, 204, 186, 255)), 8)          # the Tagus
    glow(img, DW * 0.7, 640, 500, 26, (250, 228, 200, 180), 30)
    rnd = random.Random(6)
    walls = [(214, 198, 172), (226, 214, 190), (204, 176, 160), (232, 226, 212), (196, 186, 150), (210, 190, 178)]

    def town(d):
        for row in range(7):
            base = 700 + row * 80
            haze = 0.55 + row * 0.07
            x = -40 - rnd.randint(0, 60)
            while x < DW:
                bw, bh = rnd.randint(110, 240), rnd.randint(90, 190)
                wc = tuple(int(lerp(190, c * haze + 30, 0.9)) for c in rnd.choice(walls))
                rc = tuple(int(lerp(190, c * haze + 20, 0.9)) for c in (168, 92, 66))
                top = base - bh + 80
                d.rectangle([x, top, x + bw, DH], fill=wc + (255,))
                d.polygon([(x - 8, top), (x + bw / 2, top - rnd.randint(22, 46)), (x + bw + 8, top)], fill=rc + (255,))
                for wy in range(top + 26, top + bh, 46):
                    for wx in range(x + 18, x + bw - 20, 42):
                        d.rectangle([wx, wy, wx + 12, wy + 22], fill=tuple(int(c * 0.6) for c in wc) + (255,))
                x += bw + rnd.randint(-10, 8)
    soft(img, town, 1.2)
    return dict(plate=finish(img, vig=0.3, seed=6))


def b7():
    img = grad(DW, DH, (78, 82, 90), (56, 60, 66))
    rnd = random.Random(7)

    def wall(d):
        for yy in range(0, 1000, 120):
            d.line([(0, yy), (DW, yy)], fill=(44, 48, 54, 160), width=3)
            for xx in range((yy // 120 % 2) * 130, DW, 260):
                d.line([(xx, yy), (xx, yy + 120)], fill=(44, 48, 54, 160), width=3)
        d.rectangle([640, 130, 1470, 1010], fill=(46, 34, 24, 255))                      # doorway
        for i in range(6):
            split_cod(d, 730 + i * 130, 400, 110, 0.0, (176, 160, 124))
        d.rectangle([640, 760, 1470, 800], fill=(96, 80, 60, 255))
        d.rectangle([0, 1010, DW, DH], fill=(50, 52, 56, 255))                           # wet cobbles
        for _ in range(500):
            x, y = rnd.randint(0, DW), rnd.randint(1016, DH)
            d.ellipse([x, y, x + 34, y + 14], fill=(74, 78, 84, 255))
    soft(img, wall, 1)
    glow(img, 1055, 560, 330, 300, (196, 140, 70, 110), 90)
    glow(img, 1055, 1090, 380, 40, (190, 150, 90, 90), 40)

    def slats(d):
        d.rectangle([0, 0, 1680, 1800], fill=(84, 96, 92, 255))
        for yy in range(0, 1800, 52):
            d.line([(0, yy), (1680, yy)], fill=(52, 62, 60, 255), width=10)
            d.line([(0, yy + 12), (1680, yy + 12)], fill=(112, 124, 118, 255), width=4)
    shutter = sprite(1680, 1800, slats)
    return dict(plate=finish(img, vig=0.5, seed=7),
                sprites=[(shutter, lambda t, u: (1270, 240 - 1560 * ease(min(1, u * 1.15)), 1.0))])


def b8():
    w = int(DW * 1.3)
    img = grad(w, DH, (60, 46, 34), (34, 26, 20))
    rnd = random.Random(8)

    def piles(d):
        for row, (y, s, k) in enumerate(((520, 330, 0.72), (700, 400, 0.88), (900, 470, 1.0))):
            x = -100
            while x < w + 200:
                j = rnd.uniform(0.93, 1.03)
                col = tuple(int(c * k * j) for c in CREAM)
                split_cod(d, x, y + rnd.randint(-20, 20), s, rnd.uniform(-0.12, 0.12), col)
                x += int(s * rnd.uniform(0.42, 0.56))
    soft(img, piles, 1)

    def salt(d):
        for _ in range(2600):
            x, y = rnd.randint(0, w), rnd.randint(300, DH)
            d.point((x, y), fill=(250, 248, 240, rnd.randint(70, 200)))
    soft(img, salt, 0.6)
    glow(img, w * 0.2, 300, 700, 500, (255, 240, 210, 46), 220)
    plate = finish(img, vig=0.35, seed=8)

    def cam(u, t):
        return lerp(W / 2 + 80, plate.width - W / 2 - 80, u), plate.height / 2, 1.0
    return dict(plate=plate, cam=cam)


def shop_back(seed, blur=0, dim=1.0):
    img = grad(DW, DH, (86, 62, 42), (58, 42, 30))
    shelves(img, seed, dim)
    glow(img, 300, 500, 500, 700, (255, 236, 200, 60), 200)
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    return img


def counter(img, y=900):
    soft(img, lambda d: d.rectangle([0, y, DW, DH], fill=(176, 172, 164, 255)), 0)
    soft(img, lambda d: d.rectangle([0, y, DW, y + 16], fill=(214, 210, 202, 255)), 0)
    return img


def b9():
    img = shop_back(9, blur=3)
    soft(img, lambda d: [split_cod(d, 260 + i * 150, 250, 150, 0, (190, 176, 140)) for i in range(3)], 2)
    soft(img, lambda d: bust(d, 1300, 520, 250, (64, 56, 52, 255), apron=(222, 218, 208, 255)), 2)
    glow(img, 1180, 420, 90, 200, (255, 236, 206, 70), 60)
    counter(img, 960)
    return dict(plate=finish(img, vig=0.5, seed=9))


def marble(seed):
    img = grad(DW, DH, (188, 184, 176), (160, 156, 150))
    rnd = random.Random(seed)

    def veins(d):
        for _ in range(26):
            x, y = rnd.randint(0, DW), rnd.randint(0, DH)
            pts = [(x, y)]
            for _ in range(6):
                x += rnd.randint(60, 240)
                y += rnd.randint(-70, 70)
                pts.append((x, y))
            d.line(pts, fill=(128, 126, 124, 120), width=3)
    return soft(img, veins, 3)


def b10():
    img = marble(10)
    soft(img, lambda d: split_cod(d, 1000, 560, 520, math.pi / 2 + 0.06), 1)
    soft(img, lambda d: arm(d, 420, DH + 100, 620, 760, 170, (226, 222, 212, 255), (196, 156, 130, 255)), 2)
    fist = sprite(900, 1500, lambda d: arm(d, 700, 1500, 380, 330, 300, (226, 222, 212, 255), (196, 156, 130, 255)), 4)

    def pos(t, u):
        k = abs(math.sin((t - 0.7) * math.pi / 0.45)) if 0.7 < t < 1.6 else 0
        return 2500, 1170 - 150 * k, 1.0
    return dict(plate=finish(img, vig=0.45, seed=10), sprites=[(fist, pos)],
                cam=lambda u, t: (DW + 10 * math.sin(t * 1.9), DH + 8 * math.sin(t * 2.6 + 1), 1.03))


def b11():
    img = grad(DW, DH, (52, 40, 30), (30, 24, 18))
    cx, cy, R = 1056, 640, 520

    def dial(d):
        d.ellipse([cx - R - 40, cy - R - 40, cx + R + 40, cy + R + 40], fill=(150, 116, 60, 255))
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(232, 226, 208, 255))
        for i in range(61):
            a = math.radians(-210 + i * 4)
            r0 = R - (70 if i % 5 == 0 else 38)
            d.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)), (cx + (R - 14) * math.cos(a), cy + (R - 14) * math.sin(a))],
                   fill=(40, 36, 30, 255), width=6 if i % 5 == 0 else 3)
    soft(img, dial, 1)
    plate = finish(img, vig=0.55, seed=11)
    ImageDraw.Draw(plate).text((cx * 2, cy * 2 + 330), "kg", font=font(ITALIC, 120), fill=(60, 54, 46), anchor="mm")

    def ndl(d):
        d.polygon([(1100, 1088), (1100, 1112), (2020, 1104), (2020, 1096)], fill=(150, 40, 34, 255))
        d.ellipse([1040, 1040, 1160, 1160], fill=(60, 50, 40, 255))
    needle = sprite(2200, 2200, ndl, 1.5)

    def pos(t, u):
        ang = -(-150 + 190 * (1 - math.exp(-2.6 * t)) + 26 * math.exp(-1.7 * t) * math.sin(9 * t))
        return cx * 2 - 1100, cy * 2 - 1100, 1.0, ang
    return dict(plate=plate, sprites=[(needle, pos)])


def b12():
    img = shop_back(9, blur=5, dim=0.9)
    soft(img, lambda d: bust(d, 1420, 520, 190, (64, 56, 52, 255), apron=(222, 218, 208, 255)), 2)
    counter(img, 880)
    soft(img, lambda d: split_cod(d, 1150, 930, 200, math.pi / 2), 2)
    soft(img, lambda d: bust(d, 560, 640, 520, (14, 12, 12, 255)), 12)        # the customer's shoulder
    return dict(plate=finish(img, vig=0.5, seed=12),
                cam=lambda u, t: (DW + 12 * math.sin(t * 1.5), DH + 9 * math.sin(t * 2.1), 1.03))


def b13():
    img = wood(col=(96, 74, 52), seed=13)
    soft(img, lambda d: split_cod(d, 1056, 760, 560, math.pi / 2), 1)
    glow(img, 300, 300, 600, 400, (255, 244, 220, 60), 200)

    def blade(d):
        d.polygon([(0, 500), (2600, 80), (2600, 420), (0, 640)], fill=(170, 176, 180, 255))
        d.polygon([(0, 600), (2600, 380), (2600, 420), (0, 640)], fill=(226, 230, 232, 255))
        d.rectangle([2500, 0, 2900, 470], fill=(40, 34, 30, 255))
    bl = sprite(2900, 700, blade, 2)

    def pos(t, u):
        k = min(1, max(0, (t - 0.9) / 0.5)) ** 2
        return 1350, lerp(-200, 870, k), 1.0
    return dict(plate=finish(img, vig=0.5, seed=13), sprites=[(bl, pos)])


def b14():
    img = shop_back(14, blur=7, dim=0.8)
    counter(img, 820)
    soft(img, lambda d: arm(d, -60, 520, 560, 700, 200, (226, 222, 212, 255), (196, 156, 130, 255)), 2)

    def parcel(d):
        d.rounded_rectangle([40, 40, 1160, 600], radius=30, fill=(192, 164, 124, 255))
        d.polygon([(40, 40), (600, 330), (1160, 40)], fill=(176, 148, 110, 255))
        d.line([(600, 40), (600, 600)], fill=(236, 230, 214, 255), width=10)
        d.line([(40, 330), (1160, 330)], fill=(236, 230, 214, 255), width=10)
    pc = sprite(1200, 640, parcel, 1.5)
    hand = sprite(1500, 800, lambda d: arm(d, 1500, 300, 500, 420, 380, (84, 96, 110, 255), (206, 168, 140, 255)), 3)
    return dict(plate=finish(img, vig=0.5, seed=14),
                sprites=[(pc, lambda t, u: (1250 + 420 * ease(u), 1250, 1.0)),
                         (hand, lambda t, u: (3300 - 300 * ease(u * 1.4), 1150, 1.0))],
                cam=lambda u, t: (DW + 10 * math.sin(t * 1.7), DH + 8 * math.sin(t * 2.3), 1.03))


def bowl_plate(seed, morning=False):
    img = wood(col=(124, 96, 68) if morning else (112, 84, 58), seed=15)
    cx, cy = 1056, 594
    soft(img, lambda d: d.ellipse([cx - 500, cy - 440, cx + 560, cy + 520], fill=(20, 14, 10, 110)), 40)
    water = (176, 196, 198) if morning else (150, 168, 170)
    soft(img, lambda d: d.ellipse([cx - 470, cy - 470, cx + 470, cy + 470], fill=(236, 234, 226, 255)), 1)
    soft(img, lambda d: d.ellipse([cx - 410, cy - 410, cx + 410, cy + 410], fill=water + (255,)), 3)
    glow(img, cx - 160, cy - 190, 200, 120, (255, 255, 250, 90 if morning else 60), 60)
    if morning:
        glow(img, 300, 200, 700, 500, (255, 250, 236, 50), 220)
    return img


PIECES = [(-230, -150, 330, 210, -0.3), (40, -40, 360, 230, 0.25), (-160, 130, 300, 200, 0.1)]


def piece_sprite(w, h, rot, col):
    def f(d):
        d.rounded_rectangle([60, 60, 60 + w * 2, 60 + h * 2], radius=60, fill=col + (255,))
        d.line([(90, 60 + h), (30 + w * 2, 60 + h)], fill=tuple(int(c * 0.86) for c in col) + (255,), width=8)
    return sprite(w * 2 + 120, h * 2 + 120, f, 3).rotate(math.degrees(rot), expand=True, resample=Image.BICUBIC)


def b15():
    img = bowl_plate(15)
    sprites = []
    for i, (dx, dy, w, h, rot) in enumerate(PIECES):
        sp = piece_sprite(w, h, rot, (214, 202, 170))
        x0, y0 = (1056 + dx) * 2 - 60, (594 + dy) * 2 - 60
        sprites.append((sp, (lambda i, x0, y0: lambda t, u: (x0, y0 - 60 * (1 - ease(min(1, max(0, (t - i * 0.5) / 0.9)))),
                                                             ease(min(1, max(0, (t - i * 0.5) / 0.7)))))(i, x0, y0)))
    haze = sprite(1700, 1700, lambda d: [d.ellipse([300 + a, 300 + b, 1100 + a, 1000 + b], fill=(246, 248, 246, 120))
                                         for a, b in ((0, 0), (260, 180), (-120, 300))], 110)
    sprites.append((haze, lambda t, u: (1056 * 2 - 850, 594 * 2 - 850, 0.85 * ease(max(0, (t - 1.4) / 3.2)))))
    return dict(plate=finish(img, vig=0.5, seed=15), sprites=sprites)


def b23():
    img = bowl_plate(23, morning=True)
    sprites = []
    for i, (dx, dy, w, h, rot) in enumerate(PIECES):
        sp = piece_sprite(int(w * 1.12), int(h * 1.12), rot, (238, 232, 214))
        x0, y0 = (1056 + dx) * 2 - 80, (594 + dy) * 2 - 80
        if i == 1:
            sprites.append((sp, lambda t, u, x0=x0, y0=y0: (x0 + 420 * ease(max(0, (t - 0.6) / 2.2)),
                                                           y0 - 520 * ease(max(0, (t - 0.6) / 2.2)), 1.0)))
        else:
            sprites.insert(0, (sp, lambda t, u, x0=x0, y0=y0: (x0, y0, 1.0)))
    hand = sprite(1700, 1500, lambda d: arm(d, 1700, 0, 500, 900, 330, (84, 96, 110, 255), (206, 168, 140, 255)), 4)
    sprites.append((hand, lambda t, u: (2400 + 420 * ease(max(0, (t - 0.6) / 2.2)), 440 - 520 * ease(max(0, (t - 0.6) / 2.2)), 1.0)))
    return dict(plate=finish(img, vig=0.45, seed=23), sprites=sprites)


def b16():
    img = grad(DW, DH, (132, 136, 134), (98, 102, 102))
    rnd = random.Random(16)

    def scales(d):
        for yy in range(-40, DH + 80, 76):
            for xx in range(-40 + (yy // 76 % 2) * 60, DW + 120, 120):
                d.arc([xx, yy, xx + 130, yy + 120], 200, 340, fill=(80, 84, 84, 150), width=5)
    soft(img, scales, 2)

    def crystals(d):
        for _ in range(520):
            x, y, s = rnd.randint(0, DW), rnd.randint(0, DH), rnd.randint(8, 44)
            a = rnd.uniform(0, 1.5)
            pts = [(x + s * math.cos(a + k * math.pi / 2), y + s * math.sin(a + k * math.pi / 2)) for k in range(4)]
            d.polygon([(px + 7, py + 9) for px, py in pts], fill=(50, 54, 56, 120))
            d.polygon(pts, fill=(236, 238, 238, rnd.randint(190, 250)))
            d.line([pts[0], pts[1]], fill=(255, 255, 255, 255), width=3)
    soft(img, crystals, 0.8)
    glow(img, 300, 250, 800, 500, (255, 255, 255, 40), 200)
    sharp = finish(img, vig=0.5, seed=16)
    blurred = finish(img.filter(ImageFilter.GaussianBlur(26)), vig=0.5, seed=16)
    return dict(plate=sharp, alt=blurred, mix=lambda u: 1 - ease(min(1, u / 0.62)),
                cam=static_cam(DW * 2, DH * 2, 1.0, 1.04))


def schooner(d, x, y, s, hull, sail, masts=4, furled=False):
    d.polygon([(x - 1.25 * s, y - 0.14 * s), (x + 1.3 * s, y - 0.2 * s), (x + 1.02 * s, y + 0.08 * s),
               (x - 1.05 * s, y + 0.08 * s)], fill=hull)
    d.line([(x + 1.2 * s, y - 0.2 * s), (x + 1.75 * s, y - 0.42 * s)], fill=hull, width=max(2, int(s * 0.025)))
    for i in range(masts):
        mx = x - 0.85 * s + i * (1.7 * s / max(1, masts - 1))
        d.line([(mx, y - 0.16 * s), (mx, y - 1.15 * s)], fill=hull, width=max(2, int(s * 0.022)))
        if not furled:
            d.polygon([(mx + 0.03 * s, y - 1.08 * s), (mx + 0.03 * s, y - 0.24 * s), (mx + 0.44 * s, y - 0.3 * s),
                       (mx + 0.3 * s, y - 0.86 * s)], fill=sail)
    if not furled:
        d.polygon([(x + 0.88 * s, y - 1.05 * s), (x + 1.7 * s, y - 0.42 * s), (x + 0.95 * s, y - 0.3 * s)], fill=sail)


def b17():
    img = grad(DW, DH, (20, 16, 13), (10, 8, 7))
    rnd = random.Random(17)

    def chart(d):
        d.rectangle([180, 110, 1240, 800], fill=(150, 130, 96, 255))
        for _ in range(26):
            a = rnd.uniform(0, math.pi)
            d.line([(710 - 900 * math.cos(a), 455 - 900 * math.sin(a)), (710 + 900 * math.cos(a), 455 + 900 * math.sin(a))],
                   fill=(110, 92, 64, 130), width=2)
        d.rectangle([0, 0, 180, DH], fill=(14, 11, 9, 255))
        d.rectangle([1240, 0, DW, DH], fill=(14, 11, 9, 255))
        d.rectangle([0, 0, DW, 110], fill=(14, 11, 9, 255))
        d.rectangle([0, 800, DW, DH], fill=(14, 11, 9, 255))
    soft(img, chart, 3)
    glow(img, 1250, 620, 560, 330, (255, 224, 170, 46), 150)
    soft(img, lambda d: d.rectangle([820, 920, 1760, DH], fill=(44, 34, 26, 255)), 1)          # plinth
    soft(img, lambda d: schooner(d, 1270, 880, 300, (60, 44, 32, 255), (226, 214, 186, 255)), 1.2)
    soft(img, lambda d: d.rectangle([800, 440, 1780, 920], outline=(190, 200, 204, 90), width=4), 1)   # glass case
    return dict(plate=finish(img, vig=0.6, seed=17), cam=static_cam(DW * 2, DH * 2, 1.0, 1.08, dx=120))


def archive_frame(fn, seed):
    """A 4:3 monochrome panel, pillarboxed, standing in for archive film."""
    aw = int(DH * 4 / 3 / 1.1)
    ah = int(DH / 1.1)
    panel = Image.new("RGB", (aw, ah), (150, 150, 150))
    fn(panel, aw, ah)
    panel = panel.convert("L").convert("RGB")
    img = Image.new("RGB", (DW, DH), (0, 0, 0))
    img.paste(panel, ((DW - aw) // 2, (DH - ah) // 2))
    return finish(img, vig=0, noise=3.5, seed=seed)


def b18():
    def f(p, w, h):
        p.paste(grad(w, int(h * 0.62), (186, 186, 186), (150, 150, 150)), (0, 0))
        p.paste(grad(w, h - int(h * 0.62), (84, 84, 84), (58, 58, 58)), (0, int(h * 0.62)))
        soft(p, lambda d: [d.line([(0, y), (w, y + 6)], fill=(120, 120, 120, 90), width=4)
                           for y in range(int(h * 0.66), h, 46)], 2)
        soft(p, lambda d: schooner(d, w * 0.47, h * 0.63, 330, (214, 214, 214, 255), (232, 232, 232, 255)), 1.5)
    return dict(plate=archive_frame(f, 18))


def dory(d, x, y, s, col):
    d.polygon([(x - s, y - 0.2 * s), (x + s, y - 0.24 * s), (x + 0.62 * s, y + 0.06 * s), (x - 0.66 * s, y + 0.06 * s)], fill=col)


def b19():
    def f(p, w, h):
        p.paste(grad(w, h, (176, 176, 176), (120, 120, 120)), (0, 0))
        soft(p, lambda d: d.polygon([(0, h * 0.3), (w * 0.62, h * 0.5), (w * 0.56, h), (0, h)], fill=(54, 54, 54, 255)), 2)
        soft(p, lambda d: d.rectangle([0, h * 0.84, w, h], fill=(80, 80, 80, 255)), 3)
        soft(p, lambda d: [dory(d, w * 0.25, h * (0.46 - i * 0.045), 210, (140 + i * 16,) * 3 + (255,)) for i in range(4)], 1.2)
        soft(p, lambda d: (d.line([(w * 0.6, h * 0.08), (w * 0.72, h * 0.6)], fill=(40, 40, 40, 255), width=6),
                           d.line([(w * 0.6, h * 0.08), (w * 0.9, h * 0.6)], fill=(40, 40, 40, 255), width=6),
                           dory(d, w * 0.81, h * 0.66, 190, (200, 200, 200, 255))), 1.2)
    return dict(plate=archive_frame(f, 19))


def b20():
    img = grad(DW, DH, (166, 170, 170), (112, 120, 122))
    y = np.linspace(0, 1, DH)[:, None]
    x = np.linspace(0, 1, DW)[None, :]
    wave = (np.sin(x * 26 + y * 60) * 0.5 + np.sin(x * 61 + y * 130 + 2) * 0.3) * np.clip((y - 0.55) * 3, 0, 1)
    arr = np.asarray(img).astype(float) + wave[..., None] * 14
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(2))

    def boat(d):
        dory(d, 420, 380, 300, (58, 60, 60, 255))
        d.rounded_rectangle([330, 215, 440, 345], radius=34, fill=(40, 42, 42, 255))      # seated figure, from behind
        d.ellipse([352, 150, 418, 222], fill=(40, 42, 42, 255))
        d.polygon([(335, 196), (435, 196), (410, 164), (360, 164)], fill=(40, 42, 42, 255))   # sou'wester brim
        d.line([(440, 270), (560, 300), (640, 470)], fill=(50, 52, 52, 255), width=4)     # the line over the side
    bt = sprite(840, 520, boat, 2.5)
    fog = sprite(4300, 900, lambda d: d.rectangle([0, 200, 4300, 700], fill=(178, 182, 182, 110)), 120)
    return dict(plate=finish(img, vig=0.25, seed=20),
                sprites=[(bt, lambda t, u: (1280, 1240 + 26 * math.sin(t * 1.5), 0.92)),
                         (fog, lambda t, u: (-40 + 30 * t, 760, 1.0))],
                cam=lambda u, t: (DW, DH + 22 * math.sin(t * 1.5 + 0.8), 1.02))


def b21():
    h = int(DH * 1.75)
    img = grad(DW, h, (40, 36, 34), (26, 22, 20))
    glow(img, 0, 500, 700, 900, (236, 232, 220, 70), 260)

    def face(d):
        skin = (156, 126, 106, 255)
        d.ellipse([560, 170, 1500, 1330], fill=skin)
        d.rounded_rectangle([760, 1120, 1320, 1700], radius=120, fill=skin)
        d.rounded_rectangle([200, 1500, 1900, 2300], radius=260, fill=(46, 54, 66, 255))   # jacket
        d.polygon([(480, 420), (1560, 380), (1620, 520), (900, 470), (430, 560)], fill=(38, 40, 46, 255))   # flat cap
        d.ellipse([560, 150, 1500, 560], fill=(38, 40, 46, 255))
        for yy, x0, x1 in ((640, 760, 1000), (640, 1120, 1360), (980, 900, 1220), (1080, 940, 1180), (760, 640, 760), (760, 1340, 1440)):
            d.line([(x0, yy), ((x0 + x1) / 2, yy + 16), (x1, yy)], fill=(104, 80, 66, 255), width=10, joint="curve")
        d.polygon([(1000, 690), (1090, 930), (960, 930)], fill=(136, 108, 90, 255))
    soft(img, face, 5)
    soft(img, lambda d: d.rectangle([1200, 0, DW, 1500], fill=(10, 8, 8, 120)), 200)                 # shadow side

    def hand(d):
        d.polygon([(0, 1700), (DW, 1560), (DW, 1790), (0, 1930)], fill=(128, 98, 66, 255))            # gunwale
        d.line([(0, 1700), (DW, 1560)], fill=(172, 140, 100, 255), width=12)
        d.rounded_rectangle([760, 1530, 1330, 1760], radius=100, fill=(160, 128, 106, 255))
        for i in range(4):
            d.rounded_rectangle([790 + i * 132, 1700, 890 + i * 132, 1900], radius=46, fill=(150, 118, 98, 255))
        d.polygon([(900, 1380), (1320, 1320), (1330, 1600), (800, 1600)], fill=(46, 54, 66, 255))
    soft(img, hand, 4)
    plate = finish(img, vig=0.5, seed=21)

    def cam(u, t):
        return DW, lerp(1110, plate.height - 1110, ease(max(0, (t - 1.0) / 2.8))), 1.0
    return dict(plate=plate, cam=cam)


def b22():
    w = int(DW * 1.25)
    img = grad(w, DH, (206, 220, 228), (150, 170, 184))
    rnd = random.Random(22)

    def hall(d):
        for i in range(8):
            d.rectangle([i * 380 + 40, 60, i * 380 + 300, 80], fill=(246, 250, 252, 255))       # strip lights
        d.rectangle([0, 900, w, DH], fill=(136, 146, 152, 255))
        for px in range(60, w, 520):
            for lvl in range(rnd.randint(3, 5)):
                y = 880 - lvl * 130
                d.rectangle([px, y - 120, px + 400, y], fill=(226, 214, 186, 255), outline=(170, 158, 130, 255), width=3)
                d.rectangle([px + 60, y - 120, px + 80, y], fill=(60, 96, 140, 255))
                d.rectangle([px + 320, y - 120, px + 340, y], fill=(60, 96, 140, 255))
            d.rectangle([px - 10, 880, px + 410, 905], fill=(150, 116, 76, 255))
    soft(img, hall, 1.5)

    def truck(d):
        d.rounded_rectangle([1460, 560, 1820, 900], radius=30, fill=(198, 160, 60, 255))
        d.rectangle([1500, 380, 1790, 580], outline=(50, 54, 58, 255), width=14)
        d.rectangle([1400, 420, 1430, 920], fill=(50, 54, 58, 255))
        d.rectangle([1250, 890, 1430, 912], fill=(50, 54, 58, 255))
        d.ellipse([1490, 840, 1630, 980], fill=(30, 32, 34, 255))
        d.ellipse([1700, 860, 1820, 980], fill=(30, 32, 34, 255))
    soft(img, truck, 2)
    plate = finish(img, vig=0.35, seed=22)
    d = ImageDraw.Draw(plate)
    d.rectangle([3900, 1500, 4960, 2130], fill=(244, 244, 240), outline=(120, 120, 120), width=6)
    d.text((3960, 1560), "SALTED COD  ·  Gadus morhua", font=font(SANS, 58), fill=(40, 40, 40))
    d.text((3960, 1680), "ORIGIN: NORWAY", font=font(SANS, 96), fill=(20, 20, 20))
    d.text((3960, 1850), "(placeholder: film a real label on site)", font=font(ITALIC, 46), fill=(110, 110, 110))
    for i in range(34):
        d.rectangle([3960 + i * 26, 1960, 3960 + i * 26 + (8 if i % 3 else 16), 2070], fill=(30, 30, 30))

    def cam(u, t):
        return lerp(W / 2 + 60, plate.width - W / 2 - 60, ease(u)), DH, 1.0
    return dict(plate=plate, cam=cam)


def b24():
    w = int(DW * 1.15)
    img = wood(w=w, col=(124, 96, 68), seed=24)
    rnd = random.Random(24)

    def food(d):
        for x, y, a, b in ((380, 520, 150, 105), (640, 660, 135, 100), (420, 800, 160, 110), (700, 430, 125, 92), (250, 660, 120, 90)):
            d.ellipse([x - a + 12, y - b + 16, x + a + 12, y + b + 16], fill=(40, 28, 18, 120))
            d.ellipse([x - a, y - b, x + a, y + b], fill=(196, 164, 112, 255))
            for _ in range(5):
                px, py = x + rnd.randint(-80, 80), y + rnd.randint(-50, 50)
                d.ellipse([px, py, px + 9, py + 7], fill=(150, 120, 78, 255))
        cx, cy = 1320, 600
        d.ellipse([cx - 330, cy - 310, cx + 350, cy + 350], fill=(40, 28, 18, 120))
        for r, c in ((330, (70, 108, 66)), (270, (88, 128, 76)), (200, (112, 150, 92)), (120, (146, 178, 116))):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c + (255,))
        for k in range(9):
            a = k * 0.7
            d.line([(cx, cy), (cx + 320 * math.cos(a), cy + 320 * math.sin(a))], fill=(170, 196, 140, 150), width=5)
        for x, y in ((1900, 480), (2060, 640), (1880, 760)):
            d.ellipse([x - 78 + 10, y - 100 + 14, x + 78 + 10, y + 100 + 14], fill=(40, 28, 18, 120))
            d.ellipse([x - 78, y - 100, x + 78, y + 100], fill=(240, 234, 222, 255))
    soft(img, food, 2)
    glow(img, 300, 200, 800, 500, (255, 250, 236, 50), 220)
    plate = finish(img, vig=0.4, seed=24)

    def cam(u, t):
        return lerp(W / 2 + 100, plate.width - W / 2 - 100, u), DH, 1.0
    return dict(plate=plate, cam=cam)


def b25():
    img = grad(DW, DH, (44, 40, 38), (26, 24, 22))
    soft(img, lambda d: d.rectangle([980, 60, 1900, 760], fill=(236, 234, 222, 255)), 6)        # window
    soft(img, lambda d: (d.line([(1440, 60), (1440, 760)], fill=(60, 54, 48, 255), width=22),
                         d.line([(980, 410), (1900, 410)], fill=(60, 54, 48, 255), width=22)), 2)
    glow(img, 1440, 420, 700, 500, (255, 250, 232, 60), 200)

    def pot(d):
        d.rectangle([0, 1000, DW, DH], fill=(36, 34, 34, 255))
        d.rounded_rectangle([640, 620, 1380, 1010], radius=40, fill=(92, 98, 104, 255))
        d.rectangle([640, 620, 1380, 660], fill=(150, 156, 160, 255))
        d.rounded_rectangle([540, 690, 660, 740], radius=20, fill=(60, 64, 68, 255))
        d.rounded_rectangle([1360, 690, 1480, 740], radius=20, fill=(60, 64, 68, 255))
        d.ellipse([660, 600, 1360, 680], fill=(214, 216, 206, 255))
    soft(img, pot, 2)
    steam = sprite(900, 900, lambda d: [d.ellipse([200 + a, 200 + b, 600 + a, 640 + b], fill=(250, 250, 246, 150))
                                        for a, b in ((0, 0), (90, -80), (-70, 60))], 70)
    sprites = []
    for i in range(5):
        def pos(t, u, i=i):
            p = ((t * 0.34 + i * 0.2) % 1.0)
            return 1450 + i * 170 + 60 * math.sin(t * 0.9 + i * 2), 900 - 950 * p, 0.75 * math.sin(math.pi * p)
        sprites.append((steam, pos))
    return dict(plate=finish(img, vig=0.5, seed=25), sprites=sprites)


def b26():
    img = grad(DW, DH, (236, 230, 212), (206, 198, 176))
    rnd = random.Random(26)

    def flakes(d):
        for i in range(15):
            y = 60 + i * 84
            pts = [(x, y + 34 * math.sin(x / 260 + i * 0.9) + rnd.randint(-5, 5)) for x in range(-40, DW + 80, 60)]
            d.polygon(pts + [(DW + 80, y + 150), (-40, y + 150)], fill=(lambda v: (v, v - 6, v - 30, 255))(rnd.randint(236, 250)))
            d.line(pts, fill=(170, 158, 130, 255), width=6)
    soft(img, flakes, 2.5)
    glow(img, 1056, 200, 900, 300, (255, 255, 250, 80), 180)

    def frk(d):
        for i in range(4):
            d.rounded_rectangle([0, 60 + i * 90, 900, 104 + i * 90], radius=20, fill=(176, 182, 188, 255))
            d.line([(0, 70 + i * 90), (900, 70 + i * 90)], fill=(232, 236, 240, 255), width=6)
        d.rounded_rectangle([860, 40, 1300, 400], radius=80, fill=(176, 182, 188, 255))
        d.rectangle([1260, 150, 2400, 290], fill=(176, 182, 188, 255))
    fork = sprite(2400, 440, frk, 3).rotate(-14, expand=True, resample=Image.BICUBIC)
    shadow = sprite(2400, 440, lambda d: d.rectangle([0, 60, 2400, 400], fill=(60, 50, 30, 90)), 30).rotate(-14, expand=True, resample=Image.BICUBIC)
    mv = lambda t, u: 2050 + 420 * ease(u)
    return dict(plate=finish(img, vig=0.45, seed=26),
                sprites=[(shadow, lambda t, u: (mv(t, u) + 40, 960, 1.0)), (fork, lambda t, u: (mv(t, u), 900, 1.0))])


def dinner_plate(d, cx, cy, R, full=True):
    d.ellipse([cx - R + 14, cy - R + 20, cx + R + 14, cy + R + 20], fill=(20, 14, 10, 120))
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(238, 236, 228, 255))
    d.ellipse([cx - R * 0.74, cy - R * 0.74, cx + R * 0.74, cy + R * 0.74], fill=(246, 244, 238, 255))
    if full:
        d.rounded_rectangle([cx - 0.5 * R, cy - 0.42 * R, cx + 0.12 * R, cy + 0.1 * R], radius=int(R * 0.1), fill=(240, 232, 208, 255))
        for k in range(4):
            d.line([(cx - 0.46 * R, cy - 0.3 * R + k * 0.1 * R), (cx + 0.08 * R, cy - 0.34 * R + k * 0.1 * R)], fill=(206, 194, 164, 255), width=5)
        for x, y in ((0.36, -0.3), (0.42, 0.12)):
            d.ellipse([cx + (x - 0.2) * R, cy + (y - 0.15) * R, cx + (x + 0.2) * R, cy + (y + 0.15) * R], fill=(212, 186, 124, 255))
        d.ellipse([cx - 0.5 * R, cy + 0.16 * R, cx - 0.02 * R, cy + 0.56 * R], fill=(84, 124, 74, 255))
        d.ellipse([cx - 0.4 * R, cy + 0.22 * R, cx - 0.1 * R, cy + 0.48 * R], fill=(116, 152, 96, 255))
        d.ellipse([cx + 0.02 * R, cy + 0.28 * R, cx + 0.3 * R, cy + 0.6 * R], fill=(244, 240, 230, 255))
        d.ellipse([cx + 0.1 * R, cy + 0.38 * R, cx + 0.22 * R, cy + 0.5 * R], fill=(226, 176, 60, 255))


def b27():
    img = wood(col=(70, 52, 38), seed=27)
    soft(img, lambda d: dinner_plate(d, 1056, 640, 520), 1.5)
    glow(img, 500, 300, 700, 500, (255, 220, 170, 46), 220)
    oil = sprite(120, 1700, lambda d: d.rounded_rectangle([44, 0, 76, 1700], radius=16, fill=(214, 176, 52, 230)), 5)
    pool = sprite(1500, 1100, lambda d: [d.ellipse([a, b, a + w, b + h], fill=(220, 184, 60, 120))
                                         for a, b, w, h in ((300, 260, 620, 330), (620, 420, 520, 300), (200, 560, 520, 260), (700, 700, 380, 200))], 24)

    def stream(t, u):
        a = min(1, max(0, (t - 0.5) / 0.4)) * min(1, max(0, (4.2 - t) / 0.4))
        return 1900 + 220 * ease(max(0, (t - 0.5) / 3.7)), -560 + 60 * math.sin(t * 2), a
    return dict(plate=finish(img, vig=0.5, seed=27),
                sprites=[(pool, lambda t, u: (1330, 760, 0.95 * ease(max(0, (t - 0.8) / 3.4)))), (oil, stream)],
                cam=static_cam(DW * 2, DH * 2, 1.0, 1.03))


def b28():
    img = grad(DW, DH, (88, 60, 40), (52, 36, 26))
    glow(img, 1056, 330, 520, 380, (255, 206, 130, 150), 170)
    soft(img, lambda d: (d.line([(1056, 0), (1056, 210)], fill=(30, 24, 20, 255), width=8),
                         d.polygon([(960, 290), (1152, 290), (1100, 205), (1012, 205)], fill=(40, 32, 26, 255))), 1.5)
    glow(img, 1056, 300, 70, 26, (255, 240, 200, 255), 14)

    def people(d):
        for x, s in ((640, 120), (1056, 112), (1480, 120)):
            bust(d, x, 560, s, (150, 104, 74, 255))
    soft(img, people, 3)
    soft(img, lambda d: d.polygon([(380, 800), (1740, 800), (1900, 990), (220, 990)], fill=(226, 214, 196, 255)), 2)

    def dishes(d):
        for x in (640, 880, 1240, 1480):
            d.ellipse([x - 86, 842, x + 86, 892], fill=(246, 244, 236, 255))
        d.ellipse([960, 820, 1160, 876], fill=(110, 116, 122, 255))
        d.rectangle([1028, 790, 1060, 850], fill=(60, 84, 50, 255))
    soft(img, dishes, 1.5)
    soft(img, lambda d: [bust(d, x, 880, 190, (22, 16, 14, 255)) for x in (780, 1360)], 4)
    soft(img, lambda d: (d.rectangle([0, 0, 250, DH], fill=(6, 5, 5, 255)), d.rectangle([1870, 0, DW, DH], fill=(6, 5, 5, 255)),
                         d.rectangle([0, 0, DW, 70], fill=(6, 5, 5, 255))), 22)                   # the doorway
    return dict(plate=finish(img, vig=0.5, seed=28))


def b29():
    img = wood(col=(70, 52, 38), seed=27)
    glow(img, 500, 300, 700, 500, (255, 220, 170, 46), 220)

    def empty(d):
        dinner_plate(d, 1100, 1100, 1000, full=False)
        for a, b, w, h in ((560, 700, 620, 330), (980, 1000, 560, 300), (520, 1180, 520, 240)):
            d.ellipse([a, b, a + w, b + h], fill=(238, 226, 178, 255))
        for k in range(5):
            d.line([(900 + k * 60, 700 - k * 20), (1180 + k * 50, 620 - k * 30)], fill=(214, 204, 180, 255), width=8)
        d.rounded_rectangle([1250, 1150, 1700, 1210], radius=30, fill=(176, 182, 188, 255))
    pl = sprite(2200, 2200, empty, 4)
    hand = sprite(1800, 900, lambda d: arm(d, 1800, 200, 420, 480, 360, (84, 96, 110, 255), (206, 168, 140, 255)), 4)

    def mv(t):
        return 1500 * ease(max(0, (t - 2.3) / 1.6))
    return dict(plate=finish(img, vig=0.5, seed=29),
                sprites=[(pl, lambda t, u: (1010 + mv(t), 180, 1.0)),
                         (hand, lambda t, u: (4300 - 1500 * ease(min(1, max(0, (t - 1.2) / 1.1))) + mv(t), 1100, 1.0))])


BUILD = {1: b1, 2: b2, 3: b3, 4: b4, 5: b5, 6: b6, 7: b7, 8: b8, 9: b9, 10: b10, 11: b11, 12: b12, 13: b13,
         14: b14, 15: b15, 16: b16, 17: b17, 18: b18, 19: b19, 20: b20, 21: b21, 22: b22, 23: b23, 24: b24,
         25: b25, 26: b26, 27: b27, 28: b28, 29: b29, 30: b30}

SOURCE_LABEL = {"real": "LIVE ACTION  ·  to be filmed", "ai": "AI-GENERATED  ·  to be generated",
                "archive": "ARCHIVE  ·  to be licensed", "graphic": "GRAPHIC"}

_cache = {}


def shot_data(i):
    if i not in _cache:
        if len(_cache) >= 3:
            _cache.pop(next(iter(_cache)))
        s = SHOTS[i]
        d = BUILD[s["n"]]()
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(ov)
        small = font(SANS, 34)
        dr.text((90, 70), "ANIMATIC  ·  storyboard previsualisation, not final footage", font=small, fill=(255, 255, 255, 120),
                stroke_width=2, stroke_fill=(0, 0, 0, 90))
        tag = "SHOT %02d  ·  %s" % (s["n"], SOURCE_LABEL[s["src"]] if not s.get("ai_id") else s["ai_id"] + "  ·  to be generated")
        dr.text((W - 90, H - 80), tag, font=small, fill=(255, 255, 255, 150), anchor="rs", stroke_width=2, stroke_fill=(0, 0, 0, 110))
        if s.get("caption"):
            dr.text((150, H - 170), s["caption"], font=font(ITALIC, 76), fill=(255, 255, 255, 230), anchor="ls",
                    stroke_width=3, stroke_fill=(0, 0, 0, 120))
        d["overlay"] = ov
        _cache[i] = d
    return _cache[i]


def shot_frame(i, t):
    s = SHOTS[i]
    d = shot_data(i)
    u = min(max(t / s["dur"], 0.0), 1.0)
    img = d["plate"]
    if "alt" in d:
        m = d["mix"](u)
        if m > 0.003:
            img = Image.blend(img, d["alt"], m)
    if d.get("sprites"):
        img = img.copy()
        for spr in d["sprites"]:
            im, fn = spr
            r = fn(t, u)
            x, y, a = r[0], r[1], r[2]
            if a <= 0.004:
                continue
            if len(r) > 3:
                im = im.rotate(r[3], resample=Image.BICUBIC)
            mask = im.getchannel("A")
            if a < 0.996:
                mask = mask.point(lambda v, a=a: int(v * a))
            img.paste(im, (int(round(x)), int(round(y))), mask)
    cam = d.get("cam")
    cx, cy, z = cam(u, t) if cam else (img.width / 2, img.height / 2, 1.0)
    w, h = W / z, H / z
    cx = min(max(cx, w / 2), img.width - w / 2)
    cy = min(max(cy, h / 2), img.height - h / 2)
    out = img.resize((W, H), Image.BICUBIC, box=(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
    out.paste(d["overlay"], (0, 0), d["overlay"])
    return out


_title = None


def title_card():
    global _title
    if _title is None:
        _title = Image.new("RGB", (W, H), (0, 0, 0))
        ImageDraw.Draw(_title).text((W / 2, H / 2), TITLE["text"], font=font(SERIF, 92), fill=(226, 222, 212), anchor="mm")
    return _title


def frame(n):
    t = n / FPS
    if n >= TITLE["start_frame"]:
        return title_card()
    i = max(k for k, s in enumerate(SHOTS) if round(s["start"] * FPS) <= n)
    img = None
    for a, b, length in DISSOLVES:                       # a -> b, centred on the cut
        cut = round(SHOTS[b]["start"] * FPS)
        lo = cut - length // 2
        if lo <= n < lo + length:
            fa = shot_frame(a, t - SHOTS[a]["start"])
            fb = shot_frame(b, max(0.0, t - SHOTS[b]["start"]))
            img = Image.blend(fa, fb, (n - lo + 1) / (length + 1))
    if img is None:
        img = shot_frame(i, t - SHOTS[i]["start"])
    k = 1.0
    if n < TITLE["fade_in_frames"]:
        k = (n + 1) / (TITLE["fade_in_frames"] + 1)
    if n >= TITLE["fade_out_start"]:
        k = max(0.0, 1 - (n - TITLE["fade_out_start"] + 1) / (TITLE["start_frame"] - TITLE["fade_out_start"]))
    if k < 1:
        img = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), img, k)
    return img


def main():
    cmd = sys.argv[1]
    if cmd == "frame":
        frame(int(sys.argv[2])).save(sys.argv[3])
    elif cmd == "sheet":
        cols, tw, th = 6, 640, 360
        rows = math.ceil(len(SHOTS) / cols)
        sheet = Image.new("RGB", (cols * tw, rows * th), (0, 0, 0))
        for k, s in enumerate(SHOTS):
            n = round((s["start"] + s["dur"] * 0.6) * FPS)
            sheet.paste(frame(n).resize((tw, th), Image.LANCZOS), ((k % cols) * tw, (k // cols) * th))
        sheet.save(sys.argv[2], quality=88)
    elif cmd == "segment":
        idx, count, out = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
        bounds = [round(SHOTS[min(len(SHOTS) - 1, round(j * len(SHOTS) / count))]["start"] * FPS) if j < count else TOTAL_FRAMES
                  for j in range(count + 1)]
        lo, hi = bounds[idx], bounds[idx + 1]
        ff = subprocess.Popen(
            ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "22", "-pix_fmt", "yuv420p",
             "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-r", str(FPS), out],
            stdin=subprocess.PIPE)
        for n in range(lo, hi):
            ff.stdin.write(frame(n).tobytes())
        ff.stdin.close()
        ff.wait()
        print("segment %d: frames %d-%d" % (idx, lo, hi - 1), flush=True)


if __name__ == "__main__":
    main()
