"""Pixel Pomo - tiny frameless desktop widget (no art assets needed).

A 128x176 pixel canvas scaled up with hard pixels. The OS window frame is
removed and replaced with our own pixel "wrapper": a title bar you drag, with
buttons for tasks, settings, pin-on-top, minimize and close. The app
remembers where you left it.

Controls: click things, Space = start/pause.
Title bar:  check = tasks, lines = settings, dot = pin on top, _ = minimize, x = close.
Tasks:      click [+], type, Enter to add, Esc to cancel, click a row to check it.
Click the session dots to reset the cycle.
Mascot:     M swaps square/cat (or use Settings). Preview animations with keys
            1 idle, 2 work, 3 break, 4 sleep, 5 celebrate, 0 = automatic.
Theme:      C cycles colour palettes (or use Settings).
Custom:     Settings > Edit lets you set your own focus / short / long lengths
            and how many rounds come before the long break. Hold + or - to
            speed up, or scroll the mouse wheel over a row.
When a timer ends the widget pops to the front (and un-minimizes).
"""
import json
import math
import os
import struct
import sys
import time
from pathlib import Path

import pygame

import mascots

# ================================================================ FONTS
# Jacquarda's clean sizes are multiples of 13. Put .ttf files in assets/fonts/.
FONT_UI_FILE = "JacquardaBastarda9-Regular.ttf"
FONT_UI_SIZE = 13          # labels, buttons, tasks
FONT_TIMER_FILE = "JacquardaBastarda9-Regular.ttf"
FONT_TIMER_SIZE = 26       # big countdown (2 x 13)
FONT_UI_BOLD = 0           # 0 = off, 1 = thicker
FONT_GRID = 13

# ================================================================ SIZE
# The app draws on a tiny W x H canvas and scales it up by WINDOW_SCALE.
# 2 = small (default), 3 = bigger, 1 = truly tiny. Whole numbers only.
# On high-DPI screens this is multiplied up so the size stays the same.
WINDOW_SCALE = 2
W, H = 128, 176
SHOW_DONE_COUNT = True     # little "2/5" next to the Tasks title; False = hide it

# ================================================================ POP TO FRONT
POP_TO_FRONT = True        # bring the widget to the front when a timer ends
POP_STAY_SECONDS = 10      # if pin-on-top is off, drop back to normal after this long

# ================================================================ CONFIG
# When packaged as an .exe (PyInstaller), bundled assets live in a temp folder
# (sys._MEIPASS) and settings go to %APPDATA%\PixelPomo so they survive restarts.
FROZEN = getattr(sys, "frozen", False)
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
if FROZEN:
    DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "PixelPomo"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
else:
    DATA_DIR = BASE_DIR
SETTINGS_FILE = DATA_DIR / "settings.json"

FPS = 30
RATE = 22050             # audio sample rate

PRESETS = {
    "Classic":   {"focus": 25, "short": 5,  "long": 15, "every": 4},
    "Light":     {"focus": 15, "short": 3,  "long": 10, "every": 4},
    "Deep work": {"focus": 50, "short": 10, "long": 30, "every": 3},
    "Marathon":  {"focus": 90, "short": 20, "long": 30, "every": 2},
    "Custom":    {"focus": 30, "short": 5,  "long": 20, "every": 4},  # edit in-app: Settings > Edit
}
# limits for the in-app Custom editor: (min, max)
CUSTOM_LIMITS = {"focus": (1, 180), "short": (1, 60), "long": (1, 90), "every": (1, 8)}

DEFAULTS = {
    "presets": PRESETS,
    "preset": "Classic",
    "alarm": "Chime",
    "muted": False,
    "pinned": True,
    "mascot": "square",
    "palette": "Peach",
    "pos": None,
    "sessions_done": 0,
    "tasks": [],
}

MODES = ["focus", "short", "long"]
MODE_LABEL = {"focus": "Focus", "short": "Short", "long": "Long"}

# ================================================================ PALETTES
# Press C (or use Settings) to cycle. Every palette needs every key.
#   accent / accent_hi / accent_dn also recolour the square mascot.
#   on_accent = text drawn on top of accent-coloured buttons.
#   sky = the window pane in the cat's study.
PALETTES = {
    "Peach": {      # the original: soft pastel with brown outlines
        "frame": (255, 217, 102), "frame_dark": (240, 186, 70), "outline": (89, 57, 48),
        "cream": (255, 243, 205), "cream2": (255, 250, 232), "shine": (255, 236, 240),
        "panel": (255, 246, 220), "panel_hi": (255, 226, 160),
        "text": (89, 57, 48), "dim": (156, 120, 104),
        "accent": (255, 158, 178), "accent_hi": (255, 190, 204), "accent_dn": (255, 120, 148),
        "good": (108, 190, 128), "bad": (214, 76, 92),
        "focus": (255, 214, 196), "short": (198, 236, 214), "long": (208, 200, 240),
        "focus_dk": (240, 186, 164), "short_dk": (160, 214, 188), "long_dk": (178, 168, 222),
        "star": (255, 250, 232), "glint": (255, 236, 240), "on_accent": (89, 57, 48),
        "sky": (176, 204, 236),
    },
    "Matcha": {     # sage green, cream and a terracotta accent
        "frame": (150, 176, 132), "frame_dark": (118, 146, 104), "outline": (46, 62, 50),
        "cream": (240, 242, 222), "cream2": (250, 251, 238), "shine": (252, 253, 244),
        "panel": (232, 238, 210), "panel_hi": (208, 222, 170),
        "text": (46, 62, 50), "dim": (108, 128, 104),
        "accent": (232, 164, 120), "accent_hi": (244, 192, 152), "accent_dn": (208, 132, 92),
        "good": (98, 160, 108), "bad": (196, 80, 70),
        "focus": (238, 222, 180), "short": (198, 228, 208), "long": (196, 216, 228),
        "focus_dk": (218, 200, 150), "short_dk": (168, 206, 184), "long_dk": (164, 190, 208),
        "star": (252, 253, 244), "glint": (255, 240, 224), "on_accent": (46, 62, 50),
        "sky": (176, 212, 224),
    },
    "Midnight": {   # dark navy study-at-night with warm amber
        "frame": (62, 72, 120), "frame_dark": (42, 50, 92), "outline": (14, 16, 36),
        "cream": (40, 46, 86), "cream2": (54, 62, 108), "shine": (92, 104, 158),
        "panel": (50, 58, 102), "panel_hi": (72, 84, 138),
        "text": (232, 232, 250), "dim": (140, 152, 196),
        "accent": (240, 174, 96), "accent_hi": (250, 204, 140), "accent_dn": (214, 140, 66),
        "good": (110, 200, 150), "bad": (238, 104, 110),
        "focus": (86, 112, 166), "short": (84, 148, 148), "long": (124, 112, 150),
        "focus_dk": (66, 90, 140), "short_dk": (64, 120, 124), "long_dk": (98, 88, 126),
        "star": (236, 240, 255), "glint": (255, 232, 186), "on_accent": (40, 28, 24),
        "sky": (22, 28, 66),
    },
    "Latte": {      # coffee-shop browns with dusty terracotta
        "frame": (184, 140, 108), "frame_dark": (150, 108, 82), "outline": (62, 42, 36),
        "cream": (242, 230, 210), "cream2": (251, 244, 229), "shine": (253, 248, 236),
        "panel": (238, 224, 200), "panel_hi": (220, 198, 162),
        "text": (62, 42, 36), "dim": (146, 120, 104),
        "accent": (204, 138, 106), "accent_hi": (224, 168, 138), "accent_dn": (178, 106, 80),
        "good": (124, 152, 98), "bad": (176, 70, 62),
        "focus": (234, 210, 178), "short": (204, 220, 188), "long": (200, 208, 218),
        "focus_dk": (212, 184, 148), "short_dk": (176, 196, 158), "long_dk": (172, 182, 196),
        "star": (251, 244, 229), "glint": (252, 236, 220), "on_accent": (62, 42, 36),
        "sky": (200, 214, 226),
    },
}
C = dict(PALETTES["Peach"])     # the live colours; apply_palette() rewrites these

# Hand-drawn pixel shapes ('#' = outline). Insides are filled automatically.
CIRCLE_13 = [
    "....#####....",
    "..##.....##..",
    ".#.........#.",
    ".#.........#.",
    "#...........#",
    "#...........#",
    "#...........#",
    "#...........#",
    "#...........#",
    ".#.........#.",
    ".#.........#.",
    "..##.....##..",
    "....#####....",
]
DOT_5 = [
    ".###.",
    "#...#",
    "#...#",
    "#...#",
    ".###.",
]
SHINE_13 = [(3, 3), (4, 3), (3, 4)]   # tiny highlight on round buttons

# alarm = list of (freq_hz, ms, wave, decay). freq 0 = rest.
# waves: "tri"/"square"/"sine" are plain; "soft" = warm plucked tone, "glass" = gentle bell.
ALARMS = {
    "Chime":   [(523, 110, "tri", False), (659, 110, "tri", False),
                (784, 110, "tri", False), (1047, 500, "tri", True)],
    "Marimba": [(523, 240, "soft", False), (659, 240, "soft", False),
                (784, 240, "soft", False), (659, 240, "soft", False),
                (1047, 800, "soft", False)],
    "Kalimba": [(784, 220, "glass", False), (988, 220, "glass", False),
                (1175, 220, "glass", False), (988, 220, "glass", False),
                (1319, 900, "glass", False)],
    "Drops":   [(880, 170, "soft", False), (0, 110, "soft", False),
                (660, 170, "soft", False), (0, 110, "soft", False),
                (990, 500, "soft", False)],
    "Bell":    [(659, 1300, "glass", False), (0, 60, "glass", False),
                (523, 1700, "glass", False)],
}

# little button sounds (quiet, soft)
SFX = {
    "start": [(659, 50, "soft", False), (880, 130, "soft", False)],
    "pause": [(880, 50, "soft", False), (659, 130, "soft", False)],
    "skip":  [(784, 45, "soft", False), (988, 100, "soft", False)],
    "reset": [(523, 60, "soft", False), (392, 150, "soft", False)],
    "check":   [(988, 40, "soft", False), (1319, 120, "soft", False)],
    "uncheck": [(659, 90, "soft", False)],
}
SFX_VOL = 0.18


# ================================================================ sound
def make_tone(freq, ms, wave="square", decay=False, vol=0.3):
    n = int(RATE * ms / 1000)
    out = bytearray()
    for i in range(n):
        t = i / RATE
        if freq == 0:
            s = 0.0
        else:
            ph = (t * freq) % 1.0
            if wave == "square":
                s = 1.0 if ph < 0.5 else -1.0
            elif wave == "tri":
                s = 4 * abs(ph - 0.5) - 1
            elif wave == "soft":
                s = (math.sin(2 * math.pi * freq * t)
                     + 0.25 * math.sin(4 * math.pi * freq * t)) / 1.25
            elif wave == "glass":
                s = (math.sin(2 * math.pi * freq * t)
                     + 0.2 * math.sin(2 * math.pi * 2.76 * freq * t)) / 1.2
            else:
                s = math.sin(2 * math.pi * freq * t)
        if wave in ("soft", "glass"):        # soft attack, smooth exponential fade
            env = min(1.0, i / (RATE * 0.004)) * math.exp((-3.0 if wave == "glass" else -4.0) * i / n)
        elif decay:
            env = 1 - i / n
        else:
            env = min(1.0, i / (RATE * 0.005), (n - i) / (RATE * 0.01))
        out += struct.pack("<h", int(s * vol * env * 32767))
    return bytes(out)


def build_alarm(notes, vol=0.3):
    data = b"".join(make_tone(f, ms, w, d, vol) for f, ms, w, d in notes)
    return pygame.mixer.Sound(buffer=data)


# ================================================================ pixel helpers
def draw_mask(surf, topleft, mask, outline, fill=None):
    """Draw a hand-made pixel shape. '#' cells get `outline`; empty cells
    between the first and last '#' on a row get `fill` (if given)."""
    x0, y0 = topleft
    for j, row in enumerate(mask):
        cols = [i for i, ch in enumerate(row) if ch == "#"]
        if not cols:
            continue
        if fill is not None:
            for i in range(cols[0] + 1, cols[-1]):
                if row[i] != "#":
                    surf.set_at((x0 + i, y0 + j), fill)
        for i in cols:
            surf.set_at((x0 + i, y0 + j), outline)


def dither(surf, rect, color, phase=0):
    """Checkerboard dither - the classic pixel-art shading trick."""
    for y in range(rect.h):
        for x in range(rect.w):
            if (x + y + phase) % 2 == 0:
                surf.set_at((rect.x + x, rect.y + y), color)


def fmt_num(v):
    """25 -> '25', 25.0 -> '25', 0.5 -> '0.5'."""
    try:
        return str(int(v)) if float(v).is_integer() else str(v)
    except (TypeError, ValueError):
        return str(v)


def enable_dpi_awareness():
    """Stop Windows from blurry-stretching the window on scaled displays.
    Returns the display scale (1.0 = 100%, 1.5 = 150%, ...)."""
    if sys.platform != "win32":
        return 1.0
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            return 1.0
    try:
        return ctypes.windll.user32.GetDpiForSystem() / 96
    except Exception:
        return 1.0


def load_font(filename, size):
    path = BASE_DIR / "assets" / "fonts" / filename
    try:
        return pygame.font.Font(str(path), size)
    except (FileNotFoundError, OSError):
        print(f"[font] couldn't load {path} - using the default font instead")
        return pygame.font.Font(None, int(size * 1.4))


# ================================================================ app
class App:
    def __init__(self):
        dpi = enable_dpi_awareness()
        self.scale = max(1, round(WINDOW_SCALE * dpi))   # whole-number pixel scale
        pygame.mixer.pre_init(RATE, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption("Pixel Pomo")
        try:
            pygame.display.set_icon(pygame.image.load(str(BASE_DIR / "assets" / "icon.png")))
        except (FileNotFoundError, pygame.error):
            pass
        self.clock = pygame.time.Clock()

        self.load_settings()
        self.apply_palette()
        self.open_window()

        self.font = load_font(FONT_UI_FILE, FONT_UI_SIZE)
        self.big = load_font(FONT_TIMER_FILE, FONT_TIMER_SIZE)
        self.build_sounds()

        self.mode = "focus"
        self.running = False
        self.end_time = 0.0
        self.remaining = self.duration("focus")
        self.flash_until = 0.0

        self.view = "main"          # "main" | "tasks" | "settings" | "custom"
        self.adding = False
        self.input_text = ""
        self.scroll = 0
        self.sparkle = None         # (task, time) - twinkle when a task is checked
        self.confirm_del = None     # (task, until) - first click on x arms it
        self.t0 = time.time()
        self.force_state = None     # dev preview: keys 1-5, 0 = automatic
        self.drag = None
        self.hold = None            # held +/- button in the custom editor
        self.custom_dirty = False   # custom lengths changed since the editor opened
        self.drop_back_at = 0       # when to stop floating above other windows
        self.alive = True

        self.layout()
        self.apply_pin()

    # ---------------- window (frameless, corner placement, dragging)
    def open_window(self):
        S = self.scale
        size = (W * S, H * S)
        dw, dh = pygame.display.get_desktop_sizes()[0]

        pos = self.s.get("pos")
        if not (isinstance(pos, list) and len(pos) == 2
                and 0 <= pos[0] <= dw - 60 and 0 <= pos[1] <= dh - 60):
            pos = [dw - size[0] - 24, dh - size[1] - 72]   # bottom-right corner
        os.environ["SDL_VIDEO_WINDOW_POS"] = f"{pos[0]},{pos[1]}"

        self.window = pygame.display.set_mode(size, pygame.NOFRAME)
        self.screen = pygame.Surface((W, H))    # everything draws onto this small canvas

        self.win = None
        try:
            from pygame._sdl2.video import Window
            self.win = Window.from_display_module()
        except Exception:
            print("[window] dragging unavailable with this pygame build")

    def global_mouse(self):
        try:
            return pygame.mouse.get_pos(desktop=True)
        except TypeError:
            pass
        if sys.platform == "win32":
            import ctypes

            class POINT(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            pt = POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            return pt.x, pt.y
        return pygame.mouse.get_pos()

    def start_drag(self):
        if self.win:
            self.drag = (self.global_mouse(), tuple(int(v) for v in self.win.position))

    def do_drag(self):
        if self.drag and self.win:
            (gx, gy), (wx, wy) = self.drag
            mx, my = self.global_mouse()
            self.win.position = (wx + mx - gx, wy + my - gy)

    def end_drag(self):
        if self.drag:
            self.drag = None
            self.save_position()

    def save_position(self):
        if self.win:
            try:
                self.s["pos"] = [int(v) for v in self.win.position]
                self.save_settings()
            except Exception:
                pass

    # ---------------- always-on-top / pop to front
    def set_topmost(self, on):
        if self.win is not None:
            try:
                self.win.always_on_top = on
                return
            except Exception:
                pass
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = ctypes.c_void_p(pygame.display.get_wm_info()["window"])
                # flags: NOMOVE | NOSIZE | NOACTIVATE  (change the layering, never grab focus)
                ctypes.windll.user32.SetWindowPos(hwnd, ctypes.c_void_p(-1 if on else -2),
                                                  0, 0, 0, 0, 0x0013)
            except Exception:
                pass

    def apply_pin(self):
        self.set_topmost(self.s["pinned"])

    def bring_to_front(self):
        """Timer ended: un-minimize and float above other windows without
        stealing keyboard focus, so it can't swallow what you're typing."""
        if not POP_TO_FRONT:
            return
        self.set_topmost(True)
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = ctypes.c_void_p(pygame.display.get_wm_info()["window"])
                ctypes.windll.user32.ShowWindow(hwnd, 4)        # restore if minimized, don't activate
                ctypes.windll.user32.FlashWindow(hwnd, True)    # blink the taskbar button
            except Exception:
                pass
        elif self.win is not None:
            try:
                self.win.restore()
            except Exception:
                pass
        if not self.s["pinned"]:
            self.drop_back_at = time.time() + POP_STAY_SECONDS   # then go back to a normal window

    # ---------------- settings
    def load_settings(self):
        data = {}
        if SETTINGS_FILE.exists():
            try:
                data = json.loads(SETTINGS_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                data = {}
        self.s = {**DEFAULTS, **data}
        self.s["presets"] = {**PRESETS, **self.s.get("presets", {})}
        if self.s["preset"] not in self.s["presets"]:
            self.s["preset"] = "Classic"
        if self.s["alarm"] not in ALARMS:
            self.s["alarm"] = "Chime"
        if self.s["mascot"] not in mascots.KINDS:
            self.s["mascot"] = "square"
        if self.s["palette"] not in PALETTES:
            self.s["palette"] = "Peach"
        self.s["tasks"].sort(key=lambda t: t.get("done", False))   # finished ones sit at the bottom
        self.save_settings()

    def save_settings(self):
        try:
            SETTINGS_FILE.write_text(json.dumps(self.s, indent=2))
        except OSError:
            pass

    # ---------------- palette
    def apply_palette(self):
        C.update(PALETTES[self.s["palette"]])
        mascots.set_theme(C["outline"], C["accent"], C["accent_hi"], C["accent_dn"])

    def cycle_palette(self):
        names = list(PALETTES)
        self.s["palette"] = names[(names.index(self.s["palette"]) + 1) % len(names)]
        self.apply_palette()
        self.save_settings()

    # ---------------- sounds
    def build_sounds(self):
        self.sounds = {}
        self.audio_ok = pygame.mixer.get_init() is not None
        if self.audio_ok:
            for name, notes in ALARMS.items():
                self.sounds[name] = build_alarm(notes)
        self.sfx = {}
        if self.audio_ok:
            for name, notes in SFX.items():
                self.sfx[name] = build_alarm(notes, SFX_VOL)

    def play_sfx(self, name):
        if self.audio_ok and not self.s["muted"]:
            self.sfx[name].play()

    def play_alarm(self, force=False):
        if self.audio_ok and (force or not self.s["muted"]):
            self.sounds[self.s["alarm"]].play()

    def notify(self):
        """Hook for a desktop notification (e.g. the 'plyer' package)."""
        pass

    # ---------------- timer logic
    @property
    def cfg(self):
        return self.s["presets"][self.s["preset"]]

    def duration(self, mode):
        return self.cfg[mode] * 60

    def remaining_now(self):
        if self.running:
            return max(0.0, self.end_time - time.time())
        return self.remaining

    def set_mode(self, mode):
        self.mode = mode
        self.running = False
        self.remaining = self.duration(mode)

    def toggle(self):
        if self.running:
            self.remaining = self.remaining_now()
            self.running = False
        else:
            if self.remaining <= 0:
                self.remaining = self.duration(self.mode)
            self.end_time = time.time() + self.remaining  # wall clock: survives lag/sleep
            self.running = True
        self.play_sfx("start" if self.running else "pause")

    def cycle_mascot(self):
        kinds = mascots.KINDS
        self.s["mascot"] = kinds[(kinds.index(self.s["mascot"]) + 1) % len(kinds)]
        self.save_settings()

    def mascot_state(self, now):
        if self.force_state:
            return self.force_state
        if now < self.flash_until:
            return "celebrate"
        if self.mode == "focus":
            return "work" if self.running else "idle"
        return "break" if self.mode == "short" else "sleep"

    def reset(self):
        self.running = False
        self.remaining = self.duration(self.mode)
        self.play_sfx("reset")

    def next_mode(self, count_session):
        if self.mode == "focus":
            if count_session:
                self.s["sessions_done"] += 1
            nxt = "long" if self.s["sessions_done"] >= self.cfg["every"] else "short"
        elif self.mode == "long":
            self.s["sessions_done"] = 0
            nxt = "focus"
        else:
            nxt = "focus"
        self.save_settings()
        self.set_mode(nxt)

    def finish(self):
        self.play_alarm()
        self.notify()
        self.bring_to_front()
        self.flash_until = time.time() + 3
        self.next_mode(count_session=True)

    def skip(self):
        self.next_mode(count_session=False)
        self.play_sfx("skip")

    def update(self):
        if self.running and self.remaining_now() <= 0:
            self.finish()
        if self.drop_back_at and time.time() > self.drop_back_at:
            self.drop_back_at = 0
            self.apply_pin()                         # back to the pin setting you chose
        self.update_hold()

    # ---------------- custom lengths editor
    def open_editor(self):
        if self.s["preset"] != "Custom":
            self.s["preset"] = "Custom"
            self.set_mode(self.mode)                 # switching preset resets the timer
            self.save_settings()
        self.custom_dirty = False
        self.hold = None
        self.view = "custom"

    def close_editor(self, to="settings"):
        if self.custom_dirty:
            self.custom_dirty = False
            self.set_mode(self.mode)                 # new lengths take effect; timer resets
        self.hold = None
        self.save_settings()
        self.view = to

    def step_custom(self, key, delta):
        lo, hi = CUSTOM_LIMITS[key]
        cfg = self.s["presets"]["Custom"]
        new = max(lo, min(hi, cfg[key] + delta))
        if new != cfg[key]:
            cfg[key] = new
            self.custom_dirty = True

    def update_hold(self):
        """Holding + or - repeats, then speeds up after a moment."""
        h = self.hold
        if not h:
            return
        if not pygame.mouse.get_pressed()[0] or not h["rect"].collidepoint(self.mouse_pos()):
            self.hold = None
            return
        now = time.time()
        if now >= h["next"]:
            fast = (now - h["start"]) > 1.6 and h["key"] != "every"
            self.step_custom(h["key"], h["delta"] * (5 if fast else 1))
            h["next"] = now + 0.07

    # ---------------- layout (adapts to your font height)
    def layout(self):
        lh = self.font.get_height()
        self.lh = lh
        self.row_h = lh + 3
        btn_h = lh + 3

        # --- wrapper: title bar with tiny icon buttons
        self.tb = pygame.Rect(1, 1, W - 2, lh + 3)
        names = ["tasks", "menu", "pin", "min", "close"]
        bs = 11
        self.tb_buttons = {}
        for i, name in enumerate(names):
            x = self.tb.right - 3 - bs - (len(names) - 1 - i) * (bs + 1)
            self.tb_buttons[name] = pygame.Rect(x, self.tb.y + (self.tb.h - bs) // 2, bs, bs)

        self.inner = pygame.Rect(2, self.tb.bottom + 2, W - 4, H - 2 - (self.tb.bottom + 2))
        self.content = pygame.Rect(5, self.tb.bottom + 5, W - 10, H - 5 - (self.tb.bottom + 5))
        ct = self.content
        cx = ct.centerx

        # --- main view
        tab_h = lh + 2
        tab_w = (ct.w - 4) // 3
        self.tab_rects = {
            m: pygame.Rect(ct.x + i * (tab_w + 2), ct.y, tab_w, tab_h)
            for i, m in enumerate(MODES)
        }

        self.btn_r = 6                                   # 13px round buttons
        self.label_y = ct.bottom - lh
        btn_cy = self.label_y - 3 - self.btn_r
        self.btn_centers = {
            "start": (cx - 40, btn_cy),
            "skip": (cx, btn_cy),
            "reset": (cx + 40, btn_cy),
        }
        self.dots_cy = btn_cy - self.btn_r - 7
        self.dots_rect = pygame.Rect(cx - 40, self.dots_cy - 5, 80, 10)

        top = self.tab_rects["focus"].bottom + 3
        bottom = self.dots_cy - 6
        self.scene_rect = pygame.Rect(ct.x, top, ct.w, bottom - top)
        sr = self.scene_rect
        self.band_h = self.big.get_height() + 2
        zero = self.big.render("0", False, (255, 255, 255))
        self.zero_box = zero.get_bounding_rect()          # where the digits really sit in the font box
        if self.zero_box.h == 0:
            self.zero_box = pygame.Rect(0, 0, 1, self.big.get_height())
        self.bar_rect = pygame.Rect(sr.x + 4, sr.bottom - 8, sr.w - 8, 5)

        # --- settings view
        self.preset_rect = pygame.Rect(ct.x, ct.y, ct.w - 31, btn_h)
        self.edit_rect = pygame.Rect(ct.right - 28, ct.y, 28, btn_h)
        self.alarm_rect = pygame.Rect(ct.x, ct.y + (btn_h + 3), ct.w, btn_h)
        self.mute_rect = pygame.Rect(ct.x, ct.y + 2 * (btn_h + 3), ct.w, btn_h)
        self.mascot_rect = pygame.Rect(ct.x, ct.y + 3 * (btn_h + 3), ct.w, btn_h)
        self.palette_rect = pygame.Rect(ct.x, ct.y + 4 * (btn_h + 3), ct.w, btn_h)
        self.info_y = ct.y + 5 * (btn_h + 3) + 3

        # --- custom lengths editor: label  [-]  value  [+]
        self.custom_rows = []
        y0 = ct.y + lh + 5
        for i, (key, label) in enumerate((("focus", "Focus"), ("short", "Short"),
                                          ("long", "Long"), ("every", "Rounds"))):
            y = y0 + i * (btn_h + 3)
            self.custom_rows.append((key, label,
                                     pygame.Rect(ct.x + 48, y, 16, btn_h),
                                     pygame.Rect(ct.right - 16, y, 16, btn_h)))
        self.done_rect = pygame.Rect(ct.x, ct.bottom - btn_h, ct.w, btn_h)

        # --- tasks view
        self.add_rect = pygame.Rect(ct.right - 16, ct.y, 16, lh)
        self.list_top = ct.y + lh + 4

    def visible_rows(self):
        rows = (self.content.bottom - self.list_top) // self.row_h
        return max(1, rows - (1 if self.adding else 0))

    def task_row_rect(self, i):
        offset = 1 if self.adding else 0
        y = self.list_top + (i + offset) * self.row_h
        return pygame.Rect(self.content.x, y, self.content.w, self.row_h)

    # ---------------- input
    def circle_hit(self, name, pos):
        cx, cy = self.btn_centers[name]
        return math.hypot(pos[0] - cx, pos[1] - cy) <= self.btn_r + 1

    def title_button_at(self, pos):
        for name, r in self.tb_buttons.items():
            if r.collidepoint(pos):
                return name
        return None

    def press_title_button(self, name):
        if name == "tasks":
            if self.view == "custom":
                self.close_editor()
            self.view = "main" if self.view == "tasks" else "tasks"
            self.adding = False
        elif name == "menu":
            if self.view == "custom":
                self.close_editor("settings")            # one step back, applies your changes
            else:
                self.view = "main" if self.view == "settings" else "settings"
            self.adding = False
        elif name == "pin":
            self.s["pinned"] = not self.s["pinned"]
            self.save_settings()
            self.apply_pin()
        elif name == "min":
            pygame.display.iconify()
        elif name == "close":
            self.quit()

    def quit(self):
        self.save_position()
        self.save_settings()
        self.alive = False

    def handle_click(self, pos):
        if self.tb.collidepoint(pos):
            name = self.title_button_at(pos)
            if name:
                self.press_title_button(name)
            else:
                self.start_drag()
            return
        if self.view == "main":
            self.click_main(pos)
        elif self.view == "settings":
            self.click_settings(pos)
        elif self.view == "custom":
            self.click_custom(pos)
        else:
            self.click_tasks(pos)

    def click_main(self, pos):
        for m, r in self.tab_rects.items():
            if r.collidepoint(pos):
                self.set_mode(m)
                return
        if self.circle_hit("start", pos):
            self.toggle()
        elif self.circle_hit("skip", pos):
            self.skip()
        elif self.circle_hit("reset", pos):
            self.reset()
        elif self.dots_rect.collidepoint(pos):
            self.s["sessions_done"] = 0
            self.save_settings()

    def click_settings(self, pos):
        if self.edit_rect.collidepoint(pos):
            self.open_editor()
        elif self.mute_rect.collidepoint(pos):
            self.s["muted"] = not self.s["muted"]
            self.save_settings()
        elif self.mascot_rect.collidepoint(pos):
            self.cycle_mascot()
        elif self.palette_rect.collidepoint(pos):
            self.cycle_palette()
        elif self.preset_rect.collidepoint(pos):
            names = list(self.s["presets"])
            self.s["preset"] = names[(names.index(self.s["preset"]) + 1) % len(names)]
            self.save_settings()
            self.set_mode(self.mode)
        elif self.alarm_rect.collidepoint(pos):
            names = list(ALARMS)
            self.s["alarm"] = names[(names.index(self.s["alarm"]) + 1) % len(names)]
            self.save_settings()
            self.play_alarm(force=True)  # preview

    def click_custom(self, pos):
        for key, label, minus, plus in self.custom_rows:
            for rect, delta in ((minus, -1), (plus, 1)):
                if rect.collidepoint(pos):
                    self.step_custom(key, delta)
                    now = time.time()
                    self.hold = {"key": key, "delta": delta, "rect": rect,
                                 "start": now, "next": now + 0.4}
                    return
        if self.done_rect.collidepoint(pos):
            self.close_editor()

    def wheel_custom(self, dy):
        pos = self.mouse_pos()
        for key, label, minus, plus in self.custom_rows:
            if pygame.Rect(self.content.x, minus.y, self.content.w, minus.h).collidepoint(pos):
                self.step_custom(key, dy)
                return

    def toggle_task(self, idx):
        """Check/uncheck a task. Undone tasks stay on top, done ones sink below."""
        tasks = self.s["tasks"]
        t = tasks.pop(idx)
        t["done"] = not t["done"]
        tasks.insert(sum(1 for x in tasks if not x["done"]), t)
        self.play_sfx("check" if t["done"] else "uncheck")
        if t["done"]:
            self.sparkle = (t, time.time())
        self.save_settings()

    def click_tasks(self, pos):
        if self.add_rect.collidepoint(pos):
            self.confirm_del = None
            self.adding = True
            self.input_text = ""
            return
        tasks = self.s["tasks"]
        now = time.time()
        for i in range(self.visible_rows()):
            idx = self.scroll + i
            if idx >= len(tasks):
                break
            row = self.task_row_rect(i)
            t = tasks[idx]
            delete = pygame.Rect(row.right - 12, row.y, 12, row.h)
            if delete.collidepoint(pos):
                if self.confirm_del and self.confirm_del[0] is t and now < self.confirm_del[1]:
                    tasks.pop(idx)                      # second click: really delete
                    self.confirm_del = None
                    self.save_settings()
                else:
                    self.confirm_del = (t, now + 2.5)   # first click: arm it
                return
            if row.collidepoint(pos):
                self.confirm_del = None
                self.toggle_task(idx)
                return
        self.confirm_del = None

    def handle_key(self, event):
        if self.adding:
            if event.key == pygame.K_RETURN:
                text = self.input_text.strip()
                if text:
                    tasks = self.s["tasks"]
                    tasks.insert(sum(1 for t in tasks if not t["done"]), {"text": text, "done": False})
                    self.save_settings()
                self.adding = False
            elif event.key == pygame.K_ESCAPE:
                self.adding = False
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            elif event.unicode and event.unicode.isprintable() and len(self.input_text) < 60:
                self.input_text += event.unicode
        elif event.key == pygame.K_ESCAPE and self.view == "custom":
            self.close_editor()
        elif event.key == pygame.K_SPACE:
            self.toggle()
        elif event.key == pygame.K_m:                    # swap mascot
            self.cycle_mascot()
        elif event.key == pygame.K_c:                    # swap colour palette
            self.cycle_palette()
        elif pygame.K_0 <= event.key <= pygame.K_5:      # preview: 1 idle 2 work 3 break 4 sleep 5 celebrate
            n = event.key - pygame.K_0
            self.force_state = mascots.STATES[n - 1] if n else None

    def mouse_pos(self):
        """Mouse position in canvas coordinates."""
        mx, my = pygame.mouse.get_pos()
        return (mx // self.scale, my // self.scale)

    # ---------------- drawing helpers
    def text(self, s, pos, color="text", font=None, center=False, clip=None):
        font = font or self.font
        surf = font.render(s, False, C[color] if isinstance(color, str) else color)
        rect = surf.get_rect()
        if center:
            rect.center = pos
        else:
            rect.topleft = pos
        offsets = [(0, 0)]
        if font is self.font and FONT_UI_BOLD >= 1:
            offsets.append((1, 0))
        old_clip = self.screen.get_clip()
        if clip:
            self.screen.set_clip(clip)
        for dx, dy in offsets:
            self.screen.blit(surf, rect.move(dx, dy))
        self.screen.set_clip(old_clip)
        return rect

    def button(self, rect, label="", active=False):
        scr = self.screen
        hover = rect.collidepoint(self.mouse_pos())
        col = C["accent"] if active else (C["panel_hi"] if hover else C["panel"])
        scr.fill(col, rect)
        pygame.draw.rect(scr, C["outline"], rect, 1)
        hi = C["accent_hi"] if active else C["shine"]
        pygame.draw.line(scr, hi, (rect.x + 1, rect.y + 1), (rect.right - 2, rect.y + 1))
        if label:
            self.text(label, rect.center, "on_accent" if active else "text",
                      center=True, clip=rect)

    def round_button(self, name, label, active=False):
        scr = self.screen
        cx, cy = self.btn_centers[name]
        hover = self.circle_hit(name, self.mouse_pos())
        down = hover and pygame.mouse.get_pressed()[0]
        tl = (cx - 6, cy - 6)
        base = C["accent_dn"] if active else (C["accent_hi"] if hover else C["accent"])
        if down:
            tl = (tl[0], tl[1] + 1)
        else:
            draw_mask(scr, (tl[0], tl[1] + 1), CIRCLE_13, C["frame_dark"], C["frame_dark"])  # shadow
        draw_mask(scr, tl, CIRCLE_13, C["outline"], base)
        if not down:
            for sx, sy in SHINE_13:
                scr.set_at((tl[0] + sx, tl[1] + sy), C["glint"])
        self.text(label, (cx, self.label_y + self.lh // 2), "text", center=True)

    def title_button(self, name, active=False):
        scr = self.screen
        r = self.tb_buttons[name]
        hover = r.collidepoint(self.mouse_pos())
        col = C["accent"] if active else (C["panel_hi"] if hover else C["cream"])
        scr.fill(col, r)
        pygame.draw.rect(scr, C["outline"], r, 1)
        ink = C["on_accent"] if active else C["text"]
        x, y = r.x, r.y
        if name == "tasks":       # check mark
            pygame.draw.lines(scr, ink, False, [(x + 2, y + 5), (x + 4, y + 7), (x + 8, y + 3)])
        elif name == "menu":      # three lines
            for ly in (3, 5, 7):
                pygame.draw.line(scr, ink, (x + 2, y + ly), (x + 8, y + ly))
        elif name == "pin":       # filled square when pinned on top, single dot when not
            if self.s["pinned"]:
                scr.fill(ink, (x + 3, y + 3, 5, 5))
            else:
                scr.set_at((x + 5, y + 5), ink)
        elif name == "min":
            pygame.draw.line(scr, ink, (x + 2, y + 8), (x + 8, y + 8))
        elif name == "close":
            pygame.draw.line(scr, ink, (x + 2, y + 2), (x + 8, y + 8))
            pygame.draw.line(scr, ink, (x + 8, y + 2), (x + 2, y + 8))

    # ---------------- drawing
    def draw(self):
        scr = self.screen
        scr.fill(C["frame"])

        # wrapper: frame, title bar, inner cream area
        scr.fill(C["frame_dark"], self.tb)
        self.text("Pomo", (self.tb.x + 4, self.tb.centery - self.lh // 2), "text")
        for name in self.tb_buttons:
            active = (name == "tasks" and self.view == "tasks") or \
                     (name == "menu" and self.view in ("settings", "custom"))
            self.title_button(name, active)
        scr.fill(C["cream"], self.inner)
        pygame.draw.rect(scr, C["outline"], self.inner, 1)
        pygame.draw.rect(scr, C["outline"], (0, 0, W, H), 1)

        if self.view == "main":
            self.draw_main()
        elif self.view == "settings":
            self.draw_settings()
        elif self.view == "custom":
            self.draw_custom()
        else:
            self.draw_tasks()
        self.present()

    def draw_study(self, sr, top, gt, now, cx):
        """The cat's little study nook: window, bookshelf, mug, book stack.
        `top` = first row under the timer band, `gt` = top of the ground."""
        scr = self.screen
        ol, dk = C["outline"], C["frame_dark"]

        # window with moon + twinkling star
        wx, wy = sr.x + 8, top + 2
        wh = min(11, gt - wy - 3)
        if wh >= 7:
            scr.fill(ol, (wx, wy, 11, wh))
            scr.fill(C["sky"], (wx + 1, wy + 1, 9, wh - 2))
            scr.fill(ol, (wx + 5, wy + 1, 1, wh - 2))
            scr.fill(ol, (wx + 1, wy + wh // 2, 9, 1))
            for px, py in ((2, 2), (3, 2), (2, 3)):
                scr.set_at((wx + px, wy + py), (255, 244, 200))
            if int(now * 1.2) % 3:
                scr.set_at((wx + 8, wy + 3), C["star"])
            scr.fill(dk, (wx - 1, wy + wh, 13, 1))
            scr.fill(ol, (wx - 1, wy + wh + 1, 13, 1))

        # bookshelf with a little plant
        sx, sy = sr.right - 33, top + 9
        heights = (6, 5, 7, 5, 6, 4, 6, 5)
        widths = (2, 3, 2, 2, 3, 2, 2, 2)
        cols = (C["accent_dn"], C["good"], C["frame"], C["long_dk"],
                C["accent"], C["short_dk"], C["frame_dark"], C["accent_hi"])
        x = sx
        for h, w, c in zip(heights, widths, cols):
            scr.fill(c, (x, sy - h, w, h))
            scr.fill(ol, (x, sy - h, w, 1))
            scr.set_at((x, sy - h + 2), C["cream2"])
            x += w
        px = x + 2
        scr.fill(C["accent_dn"], (px, sy - 2, 4, 2))
        for lx, ly in ((1, 3), (2, 3), (0, 4), (1, 4), (2, 4), (3, 4), (1, 5), (2, 6)):
            scr.set_at((px + lx, sy - ly), C["good"])
        scr.fill(dk, (sx - 1, sy, x + 7 - sx, 1))
        scr.fill(ol, (sx - 1, sy + 1, x + 7 - sx, 1))

        # steaming mug on the floor, left of the cat
        mx = cx - 22
        scr.fill(ol, (mx, gt - 3, 5, 5))
        scr.fill(C["cream2"], (mx + 1, gt - 2, 3, 3))
        scr.fill(C["frame_dark"], (mx + 1, gt - 2, 3, 1))
        scr.set_at((mx + 5, gt - 1), ol)
        scr.set_at((mx + 5, gt), ol)
        for k in range(2):
            p = (now * 0.8 + k * 0.5) % 1.0
            if p < 0.9:
                scr.set_at((mx + 1 + k * 2 + int(math.sin(p * 6 + k)), gt - 4 - int(p * 5)),
                           C["star"])

        # stack of books, right of the cat
        bx = cx + 14
        for (ox, by, w, c) in ((0, gt - 1, 9, C["accent_dn"]),
                               (1, gt - 4, 8, C["good"]),
                               (0, gt - 7, 7, C["frame"])):
            scr.fill(ol, (bx + ox, by, w, 3))
            scr.fill(c, (bx + ox + 1, by + 1, w - 2, 1))

    def draw_main(self):
        scr = self.screen
        now = time.time()
        is_cat = self.s["mascot"] == "cat"

        for m, r in self.tab_rects.items():
            self.button(r, MODE_LABEL[m], active=(m == self.mode))

        # ---- screen: scene + mascot + timer
        sr = self.scene_rect
        scr.fill(C[self.mode], sr)
        dark = C[self.mode + "_dk"]

        band = pygame.Rect(sr.x + 1, sr.y + 1, sr.w - 2, self.band_h)
        area_top = band.bottom + 1
        ground_top = self.bar_rect.y - 10

        # tiny twinkling stars (square's backdrop; the cat has a window instead)
        if not is_cat:
            for fx, fy, ph in ((0.12, 0.2, 0.0), (0.86, 0.15, 0.7), (0.22, 0.6, 1.4), (0.78, 0.55, 2.1)):
                x = sr.x + int(sr.w * fx)
                y = area_top + int((ground_top - area_top) * fy)
                t = int(now * 1.5 + ph) % 4
                if t in (0, 2):
                    scr.set_at((x, y), C["star"])
                elif t == 1:
                    for ox, oy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
                        scr.set_at((x + ox, y + oy), C["star"])

        # ground: dithered edge + solid fill
        dither(scr, pygame.Rect(sr.x + 1, ground_top, sr.w - 2, 2), dark)
        scr.fill(dark, (sr.x + 1, ground_top + 2, sr.w - 2, self.bar_rect.y - 3 - (ground_top + 2)))

        # scenery + animated mascot (see mascots.py). Keep it inside the scene box.
        old_clip = scr.get_clip()
        scr.set_clip(pygame.Rect(sr.x + 1, band.bottom + 1, sr.w - 2,
                                 self.bar_rect.y - band.bottom - 2))
        if is_cat:
            self.draw_study(sr, area_top, ground_top, now, sr.centerx)
        scr.fill(dark, (sr.centerx - 6, ground_top + 3, 12, 2))
        mascots.draw(scr, self.s["mascot"], self.mascot_state(now), now - self.t0,
                     sr.centerx, ground_top + 2)
        scr.set_clip(old_clip)

        flashing = now < self.flash_until and int(now * 6) % 2 == 0
        pygame.draw.rect(scr, C["accent_dn"] if flashing else C["outline"], sr, 1)

        # timer band across the top of the screen
        scr.fill(C["cream2"], band)
        pygame.draw.line(scr, C["outline"], (band.x, band.bottom), (band.right - 1, band.bottom))
        secs = int(math.ceil(self.remaining_now()))
        mm, ss = f"{secs // 60:02d}", f"{secs % 60:02d}"
        w_mm, w_ss = self.big.size(mm)[0], self.big.size(ss)[0]
        u = max(1, FONT_TIMER_SIZE // FONT_GRID)      # size of one timer "pixel"
        gap = 4 * u
        x0 = sr.centerx - (w_mm + gap + w_ss) // 2
        cy = band.centery
        ty = cy - self.big.get_height() // 2
        x0 -= x0 % u                                   # snap digits to the timer's pixel lattice
        ty -= ty % u
        self.text(mm, (x0, ty), "text", font=self.big)
        self.text(ss, (x0 + w_mm + gap, ty), "text", font=self.big)
        d = u                                          # small colon dots (1 timer pixel each)
        dx = x0 + w_mm + (gap - d) // 2
        dx -= dx % u
        mid = ty + self.zero_box.centery               # centre of the digits, not of the font box
        scr.fill(C["text"], (dx, mid - u - d, d, d))
        scr.fill(C["text"], (dx, mid + u, d, d))

        # progress bar at the bottom of the screen
        total = self.duration(self.mode)
        frac = 1 - (self.remaining_now() / total) if total else 0
        bar = self.bar_rect
        scr.fill(C["cream2"], bar)
        inner_w = bar.w - 2
        scr.fill(C["good"], (bar.x + 1, bar.y + 1, int(inner_w * frac), bar.h - 2))
        pygame.draw.rect(scr, C["outline"], bar, 1)

        # session dots (hand-drawn 5px circles)
        every = self.cfg["every"]
        spacing = 9
        start_x = self.content.centerx - ((every - 1) * spacing) // 2
        for i in range(every):
            fill = C["accent"] if i < self.s["sessions_done"] else C["cream2"]
            draw_mask(scr, (start_x + i * spacing - 2, self.dots_cy - 2), DOT_5, C["outline"], fill)

        # round buttons
        self.round_button("start", "Pause" if self.running else "Start", active=self.running)
        self.round_button("skip", "Skip")
        self.round_button("reset", "Reset")

    def draw_settings(self):
        self.button(self.preset_rect, self.s["preset"])
        self.button(self.edit_rect, "Edit", active=(self.s["preset"] == "Custom"))
        self.button(self.alarm_rect, f"Alarm: {self.s['alarm']}")
        self.button(self.mute_rect, "Sound: off" if self.s["muted"] else "Sound: on")
        self.button(self.mascot_rect, f"Mascot: {self.s['mascot'].capitalize()}")
        self.button(self.palette_rect, f"Theme: {self.s['palette']}")
        c = self.cfg
        y = self.info_y
        for line in (f"{fmt_num(c['focus'])} / {fmt_num(c['short'])} / {fmt_num(c['long'])} min",
                     f"long break every {fmt_num(c['every'])}"):
            self.text(line, (self.content.x + 2, y), "dim", clip=self.content)
            y += self.lh + 1

    def draw_custom(self):
        scr = self.screen
        ct = self.content
        self.text("Custom lengths", (ct.x + 1, ct.y), "text", clip=ct)
        cfg = self.s["presets"]["Custom"]
        for key, label, minus, plus in self.custom_rows:
            label_clip = pygame.Rect(ct.x, minus.y, 47, minus.h)
            self.text(label, (ct.x + 2, minus.centery - self.lh // 2), "text", clip=label_clip)
            self.button(minus)
            self.button(plus)
            mx, my = minus.center
            pygame.draw.line(scr, C["text"], (mx - 3, my), (mx + 3, my))          # pixel "-"
            px, py = plus.center
            pygame.draw.line(scr, C["text"], (px - 3, py), (px + 3, py))          # pixel "+"
            pygame.draw.line(scr, C["text"], (px, py - 3), (px, py + 3))
            self.text(fmt_num(cfg[key]), ((minus.right + plus.x) // 2, minus.centery),
                      "text", center=True)
        self.button(self.done_rect, "Done", active=True)

    def draw_tasks(self):
        scr = self.screen
        ct = self.content
        now = time.time()
        tasks = self.s["tasks"]
        head = self.text("Tasks", (ct.x + 1, ct.y), "text")
        if SHOW_DONE_COUNT and tasks:
            done = sum(1 for t in tasks if t["done"])
            self.text(f"{done}/{len(tasks)}", (head.right + 6, ct.y), "dim")
        self.button(self.add_rect)
        px, py = self.add_rect.center                      # pixel "+"
        pygame.draw.line(scr, C["text"], (px - 3, py), (px + 3, py))
        pygame.draw.line(scr, C["text"], (px, py - 3), (px, py + 3))

        if self.adding:
            row = pygame.Rect(ct.x, self.list_top, ct.w, self.row_h)
            scr.fill(C["panel_hi"], row)
            cursor = "_" if int(now * 2) % 2 == 0 else ""
            self.text(self.input_text + cursor, (row.x + 3, row.y + 1), "text", clip=row)

        vis = self.visible_rows()
        self.scroll = max(0, min(self.scroll, max(0, len(tasks) - vis)))
        mouse = self.mouse_pos()
        old_clip = scr.get_clip()
        scr.set_clip(ct)
        for i in range(vis):
            idx = self.scroll + i
            if idx >= len(tasks):
                break
            t = tasks[idx]
            row = self.task_row_rect(i)
            if row.collidepoint(mouse):
                scr.fill(C["panel_hi"], row)
            box = pygame.Rect(row.x + 2, row.centery - 3, 7, 7)
            scr.fill(C["cream2"], box)
            pygame.draw.rect(scr, C["outline"], box, 1)
            if t["done"]:
                pygame.draw.lines(scr, C["good"], False,
                                  [(box.x + 1, box.y + 3), (box.x + 2, box.y + 4), (box.x + 5, box.y + 1)])
            text_clip = pygame.Rect(row.x + 11, row.y, row.w - 11 - 12, row.h)
            col = "dim" if t["done"] else "text"
            r = self.text(t["text"], (row.x + 12, row.y + 1), col, clip=text_clip)
            if t["done"]:
                end_x = min(r.right, text_clip.right)
                pygame.draw.line(scr, C["dim"], (r.x, r.centery), (end_x, r.centery))

            # little twinkle around the box when a task was just checked
            if self.sparkle and self.sparkle[0] is t:
                k = int((now - self.sparkle[1]) / 0.15)
                if k < 3:
                    pts = ([(-1, -1), (7, -1), (-1, 7), (7, 7)],
                           [(-2, -2), (8, -2), (-2, 8), (8, 8), (3, -3), (3, 9)],
                           [(-3, -3), (9, -3), (-3, 9), (9, 9)])[k]
                    for j, (sx, sy) in enumerate(pts):
                        scr.set_at((box.x + sx, box.y + sy), C["accent_dn"] if j % 2 else C["star"])
                else:
                    self.sparkle = None

            # x to delete: first click arms it (turns red), second click deletes
            armed = bool(self.confirm_del and self.confirm_del[0] is t and now < self.confirm_del[1])
            xc = (row.right - 6, row.centery)
            if armed:
                scr.fill(C["bad"], (row.right - 11, row.y + 1, 10, row.h - 2))
            ink = C["cream2"] if armed else C["bad"]
            pygame.draw.line(scr, ink, (xc[0] - 2, xc[1] - 2), (xc[0] + 2, xc[1] + 2))
            pygame.draw.line(scr, ink, (xc[0] + 2, xc[1] - 2), (xc[0] - 2, xc[1] + 2))

        # thin scroll bar on the right edge when the list is longer than the view
        if len(tasks) > vis:
            y0 = self.list_top + (self.row_h if self.adding else 0)
            h = vis * self.row_h
            th = max(4, h * vis // len(tasks))
            ty = y0 + (h - th) * self.scroll // max(1, len(tasks) - vis)
            scr.fill(C["dim"], (ct.right - 1, ty, 1, th))
        scr.set_clip(old_clip)

    def present(self):
        """Scale the small canvas up to the window with crisp pixels."""
        size = (W * self.scale, H * self.scale)
        self.window.blit(pygame.transform.scale(self.screen, size), (0, 0))
        pygame.display.flip()

    # ---------------- main loop
    def run(self):
        while self.alive:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(self.mouse_pos())
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.hold = None
                    self.end_drag()
                elif event.type == pygame.MOUSEMOTION and self.drag:
                    self.do_drag()
                elif event.type == pygame.MOUSEWHEEL and self.view == "tasks":
                    self.scroll -= event.y
                elif event.type == pygame.MOUSEWHEEL and self.view == "custom":
                    self.wheel_custom(event.y)
                elif event.type == pygame.KEYDOWN:
                    self.handle_key(event)
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()


if __name__ == "__main__":
    App().run()