"""Animated mascots for Pixel Pomo: the square dude and the cat.

Everything is drawn from tiny pixel data (no image files needed), so you can
see the motion now and swap in your own sprites later.

    draw(surf, kind, state, t, cx, bottom)
    set_theme(outline, body, body_hi, body_dk)   # recolour for a palette

    kind   "square" or "cat"
    state  "idle" | "work" | "break" | "sleep" | "celebrate"
    t      seconds (any increasing clock)
    cx     x centre of the mascot
    bottom y just below the mascot's feet (exclusive)

Only uses surf.fill(color, (x, y, w, h)) and surf.set_at((x, y), color), so it
works with a pygame Surface. Set a clip rect on the surface first if you want
jumps and particles kept inside a box.
"""
import math
from functools import lru_cache

KINDS = ("square", "cat")
STATES = ("idle", "work", "break", "sleep", "celebrate")

OUT = (89, 57, 48)
PAL = {
    "o": OUT,
    "f": (255, 183, 110),    # cat fur
    "d": (232, 146, 80),     # tabby stripes
    "l": (255, 238, 210),    # cat belly / cheeks
    "p": (255, 140, 165),    # nose / inner ear
    "g": (189, 201, 224),    # laptop
    "G": (150, 164, 196),    # laptop shade
    "w": (255, 255, 255),
}
BODY = (255, 158, 178)       # square dude
BODY_HI = (255, 190, 204)
BODY_DK = (255, 120, 148)
CUP = (189, 201, 224)
HEART = (255, 120, 148)
HEART_PINK = (255, 140, 165)   # the cat's hearts stay pink in every theme
CONFETTI = ((255, 120, 148), (255, 217, 102), (108, 190, 128), (150, 130, 230))


def set_theme(outline, body, body_hi, body_dk):
    """Recolour the mascots to match the current palette."""
    global OUT, BODY, BODY_HI, BODY_DK, HEART
    OUT = outline
    PAL["o"] = outline
    BODY, BODY_HI, BODY_DK = body, body_hi, body_dk
    HEART = body_dk


# ------------------------------------------------------------------ tiny helpers
def _blit(surf, rows, x, y):
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != ".":
                surf.set_at((x + i, y + j), PAL[ch])


def _pts(surf, pts, color, ox=0, oy=0):
    for px, py in pts:
        surf.set_at((ox + px, oy + py), color)


def _heart(surf, x, y, color=None):
    _pts(surf, [(1, 0), (3, 0), (0, 1), (1, 1), (2, 1), (3, 1), (4, 1),
                (1, 2), (2, 2), (3, 2), (2, 3)], color or HEART, x, y)


def _z(surf, x, y, color=None):
    _pts(surf, [(0, 0), (1, 0), (2, 0), (3, 0), (2, 1), (1, 2),
                (0, 3), (1, 3), (2, 3), (3, 3)], color or OUT, x, y)


def _note(surf, x, y, color=None):
    _pts(surf, [(1, 0), (2, 0), (1, 1), (1, 2), (0, 3), (1, 3)], color or OUT, x, y)


def _star(surf, x, y, color=(255, 255, 255)):
    _pts(surf, [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)], color, x, y)


def _phase(t, period, offset=0.0):
    return ((t / period) + offset) % 1.0


def _zzz(surf, cx, top, t):
    for k in range(3):
        p = _phase(t, 3.0, k / 3)
        if p < 0.85:
            _z(surf, cx + 6 + int(math.sin(p * 6) * 2) + k, top - int(p * 22))


def _hearts(surf, cx, top, t):
    for k in range(2):
        p = _phase(t, 2.4, k / 2)
        if p < 0.9:
            _heart(surf, cx - 12 + k * 14 + int(math.sin(p * 5) * 2), top - int(p * 14), HEART_PINK)


def _confetti(surf, cx, bottom, t):
    for i in range(9):
        x = cx - 26 + (i * 13) % 52
        y = bottom - 34 + int((t * 22 + i * 11) % 34)
        surf.set_at((x, y), CONFETTI[i % 4])
        surf.set_at((x + 1, y), CONFETTI[i % 4])


# ------------------------------------------------------------------ cat
def _sym(rows):
    return [l + c + l[::-1] for l, c in rows]


def _pad(rows):
    return ["." + r + "." for r in rows]


_HEAD = _sym([
    ("..o....", "."),
    ("..oo...", "."),
    ("..oppoo", "o"),
    (".offfff", "f"),
    (".offfff", "f"),
    (".offfff", "f"),
    (".offffl", "p"),
    (".offfff", "f"),
    (".offfff", "f"),
    ("..ooooo", "o"),
])
_BODY = _sym([
    ("..offff", "f"),
    ("..offll", "l"),
    ("..offll", "l"),
    (".offfll", "l"),
    (".oooooo", "o"),
])
_SIT = _pad(_HEAD + _BODY)       # 17 x 15
_LOAF = _pad(_sym([
    ("..o....", "."),
    ("..oo...", "."),
    ("..oppoo", "o"),
    (".offfff", "f"),
    (".offfff", "f"),
    (".offffl", "p"),
    ("offffff", "f"),
    ("offffff", "f"),
    ("ooooooo", "o"),
]))                              # 17 x 9

_TAILS = {
    "a": [(15, 14), (16, 14), (16, 13), (16, 12), (16, 11)],
    "b": [(15, 14), (16, 14), (16, 13), (15, 12), (15, 11)],
    "c": [(15, 14), (16, 14), (16, 13), (16, 12), (15, 11), (15, 10)],
}


def _mut(rows):
    return [list(r) for r in rows]


def _set(rows, pts, ch):
    for x, y in pts:
        if 0 <= y < len(rows) and 0 <= x < len(rows[0]):
            rows[y][x] = ch


def _done(rows):
    return tuple("".join(r) for r in rows)


@lru_cache(maxsize=None)
def cat_sit(eyes="open", mouth="closed", tail="a", ear="up"):
    r = _mut(_SIT)
    if eyes == "open":
        _set(r, [(5, 4), (5, 5), (11, 4), (11, 5)], "o")
    elif eyes == "blink":
        _set(r, [(4, 5), (5, 5), (11, 5), (12, 5)], "o")
    elif eyes == "happy":
        _set(r, [(4, 5), (5, 4), (6, 5), (10, 5), (11, 4), (12, 5)], "o")
    if mouth == "yawn":
        _set(r, [(7, 8), (8, 8), (9, 8), (7, 9), (9, 9)], "o")
        _set(r, [(8, 9)], "p")
    else:
        _set(r, [(8, 7)], "o")
    if ear == "twitch":
        _set(r, [(3, 0)], ".")
    _set(r, [(6, 3), (8, 3), (10, 3)], "d")
    _set(r, _TAILS[tail], "o")
    return _done(r)


# Laptop seen from behind (the cat is working behind it): lid with a little
# logo, a hinge line, and a wider base with a trackpad notch.
_LID = ("ooooooooooooo",
        "oggggggggggGo",
        "ogggggwggggGo",
        "oggggggggggGo",
        "ooooooooooooo")
_BASE = ("oggggggGGGggggggo",
         "ooooooooooooooooo")


@lru_cache(maxsize=None)
def cat_laptop(nod=0, eyes="open", paw=0):
    r = [list("." * 17) for _ in range(16)]
    for y in range(10):                       # head, optionally nodded down 1px
        for x in range(17):
            ch = _SIT[y][x]
            if ch != "." and y + nod < 16:
                r[y + nod][x] = ch
    if eyes == "open":
        _set(r, [(5, 4 + nod), (5, 5 + nod), (11, 4 + nod), (11, 5 + nod)], "o")
    else:
        _set(r, [(4, 5 + nod), (5, 5 + nod), (11, 5 + nod), (12, 5 + nod)], "o")
    _set(r, [(8, 7 + nod)], "o")
    _set(r, [(6, 3 + nod), (8, 3 + nod), (10, 3 + nod)], "d")
    for j, line in enumerate(_LID):           # lid hides the body
        for i, ch in enumerate(line):
            r[9 + j][2 + i] = ch
    for j, line in enumerate(_BASE):          # base / keyboard deck
        r[14 + j] = list(line)
    px = 4 if paw == 0 else 11                # one paw taps at a time
    _set(r, [(px, 14), (px + 1, 14)], "f")
    _set(r, [(px - 1, 14), (px + 2, 14)], "o")
    return _done(r)


@lru_cache(maxsize=None)
def cat_loaf(tail="a", breath=0):
    r = _mut(_LOAF)
    _set(r, [(4, 4), (5, 4), (11, 4), (12, 4)], "o")
    _set(r, [(6, 3), (8, 3), (10, 3)], "d")
    if breath:                                # inhale: body grows 1px, feet stay put
        r.insert(6, list(r[6]))
    n = len(r)
    _set(r, [(15, n - 2), (16, n - 2), (16, n - 3)] if tail == "a"
         else [(15, n - 2), (16, n - 2)], "o")
    return _done(r)


def _cat(surf, state, t, cx, bottom):
    x = cx - 8
    dy = 0
    if state == "idle":
        ph = t % 6.0
        rows = cat_sit(eyes="blink" if 3.0 <= ph < 3.15 else "open",
                       tail="a" if int(t / 0.7) % 2 == 0 else "b",
                       ear="twitch" if 4.6 <= ph < 4.8 else "up")
    elif state == "work":
        ph = t % 5.0
        rows = cat_laptop(nod=int(t / 0.35) % 2,
                          eyes="blink" if 3.4 <= ph < 3.55 else "open",
                          paw=int(t / 0.22) % 2)
    elif state == "break":
        # calm: face stays still, just the tail wagging and the hearts
        rows = cat_sit(eyes="happy", mouth="closed",
                       tail="c" if int(t / 0.5) % 2 == 0 else "b")
        _hearts(surf, cx, bottom - 15, t)
    elif state == "sleep":
        breath = 1 if math.sin(t * 2.0) > 0 else 0           # slow breathing, feet stay planted
        rows = cat_loaf(tail="a", breath=breath)
        _zzz(surf, cx, bottom - 9 - breath, t)
    else:                                                    # celebrate
        hops = (0, -3, -6, -8, -6, -3)
        dy = hops[int(t / 0.07) % len(hops)]
        rows = cat_sit(eyes="happy", mouth="closed", tail="c" if int(t / 0.14) % 2 == 0 else "b")
        _confetti(surf, cx, bottom, t)
    _blit(surf, rows, x, bottom - len(rows) + dy)


# ------------------------------------------------------------------ square dude
def _square(surf, cx, bottom, w, h, dy=0, eyes="open", mouth="smile",
            phones=False, arms=0, blush=True):
    x = cx - w // 2
    y = bottom - h + dy
    surf.fill(OUT, (x, y, w, h))
    surf.fill(BODY, (x + 1, y + 1, w - 2, h - 2))
    surf.fill(BODY_HI, (x + 2, y + 2, 2, 1))
    surf.fill(BODY_HI, (x + 2, y + 3, 1, 1))
    ey = y + (2 if h <= 12 else max(3, h // 3))   # squashed = eyes higher, so they never touch the mouth
    if eyes == "open":
        surf.fill(OUT, (x + 3, ey, 2, 3))
        surf.fill(OUT, (x + w - 5, ey, 2, 3))
    elif eyes == "blink":
        surf.fill(OUT, (x + 3, ey + 1, 2, 1))
        surf.fill(OUT, (x + w - 5, ey + 1, 2, 1))
    elif eyes == "happy":
        _pts(surf, [(3, 2), (4, 1), (5, 2)], OUT, x, ey)
        _pts(surf, [(w - 6, 2), (w - 5, 1), (w - 4, 2)], OUT, x, ey)
    elif eyes == "closed":
        surf.fill(OUT, (x + 3, ey + 1, 3, 1))
        surf.fill(OUT, (x + w - 6, ey + 1, 3, 1))
    ym = y + h - 5
    c0 = w // 2
    if mouth == "smile":
        _pts(surf, [(c0 - 2, 0), (c0 - 1, 1), (c0, 1), (c0 + 1, 0)], OUT, x, ym)
    elif mouth == "flat":
        surf.fill(OUT, (x + c0 - 1, ym + 1, 2, 1))
    elif mouth == "open":
        surf.fill(OUT, (x + c0 - 1, ym, 2, 3))
        surf.fill(BODY_DK, (x + c0 - 1, ym + 1, 2, 1))
    if blush and mouth != "none":
        surf.fill(BODY_DK, (x + 2, ym - 1, 2, 1))
        surf.fill(BODY_DK, (x + w - 4, ym - 1, 2, 1))
    if phones:
        surf.fill(OUT, (x + 2, y - 2, w - 4, 1))
        surf.fill(OUT, (x + 1, y - 1, 1, 1))
        surf.fill(OUT, (x + w - 2, y - 1, 1, 1))
        for cxp in (x - 2, x + w - 1):
            surf.fill(OUT, (cxp, y + 3, 3, 6))
            surf.fill(CUP, (cxp + 1, y + 4, 1, 4))
    if arms:
        up = arms > 0
        for ax in (x - 2, x + w):
            ay = y - 3 if up else y + 4
            surf.fill(OUT, (ax, ay, 2, 5))
            surf.fill(BODY, (ax, ay + 1, 1, 3))


def _sq(surf, state, t, cx, bottom):
    if state == "idle":
        ph = t % 3.6
        _square(surf, cx, bottom, 14, 14 if int(t / 0.8) % 2 == 0 else 13,
                eyes="blink" if 2.4 <= ph < 2.55 else "open", mouth="flat", blush=False)
    elif state == "work":
        ph = t % 4.0
        _square(surf, cx, bottom, 14, 14 if int(t / 0.3) % 2 == 0 else 13,
                eyes="blink" if 3.0 <= ph < 3.15 else "open", mouth="flat",
                phones=True, blush=False)
        p = _phase(t, 2.2)
        if p < 0.8:
            _note(surf, cx + 9 + int(math.sin(p * 7) * 2), bottom - 16 - int(p * 12))
    elif state == "break":
        # (duration, width, height, lift, eyes, mouth)
        seq = [(1.0, 14, 14, 0, "happy", "smile"),
               (0.12, 16, 12, 0, "happy", "smile"),
               (0.10, 12, 17, -2, "happy", "smile"),
               (0.15, 14, 15, -7, "happy", "smile"),
               (0.10, 12, 17, -2, "happy", "smile"),
               (0.12, 16, 12, 0, "happy", "smile")]
        total = sum(s[0] for s in seq)
        ph = t % total
        for frame in seq:
            if ph < frame[0]:
                break
            ph -= frame[0]
        _, w, h, dy, eyes, mouth = frame
        _square(surf, cx, bottom, w, h, dy, eyes=eyes, mouth=mouth)
        p = _phase(t, 1.6)
        if p < 0.7:
            _star(surf, cx - 12, bottom - 14 - int(p * 8), (255, 255, 255))
            _star(surf, cx + 12, bottom - 18 + int(p * 4), (255, 217, 102))
    elif state == "sleep":
        _square(surf, cx, bottom, 16, 11 if int(t / 1.2) % 2 == 0 else 10,
                eyes="closed", mouth="none", blush=True)
        _zzz(surf, cx, bottom - 12, t)
    else:                                                    # celebrate
        hop = abs(math.sin(t * 9)) * 9
        _confetti(surf, cx, bottom, t)
        _square(surf, cx, bottom, 14, 14, -int(hop), eyes="happy", mouth="open", arms=1)


# ------------------------------------------------------------------ public
def draw(surf, kind, state, t, cx, bottom):
    if state not in STATES:
        state = "idle"
    if kind == "cat":
        _cat(surf, state, t, cx, bottom)
    else:
        _sq(surf, state, t, cx, bottom)