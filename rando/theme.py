"""The window's look: Hyrule at night (deep blue, Triforce gold), rounded anti-aliased cards, buttons, fields and switches.

Only Tk: each shape is painted once into a small PNG (signed distance, 4x4 supersampling for smooth edges) and ttk stretches
it as a nine-slice element. Nothing to install, no image file."""
import base64
import struct
import tkinter as tk
import zlib
from tkinter import font as tkfont
from tkinter import ttk

C = {
    "night": "#0b1220",       # the window behind everything
    "night2": "#101a2c",      # the sidebar
    "card": "#16233a",        # cards
    "card2": "#1c2c47",       # fields, secondary buttons, the log
    "card3": "#243756",       # hover
    "line": "#2b3f60",
    "line2": "#3a5279",
    "text": "#e9eef7",
    "muted": "#93a4c0",
    "faint": "#62759a",
    "gold": "#e6b84a",
    "gold2": "#f3cb66",       # hover
    "gold3": "#c99a2e",       # pressed
    "gold_text": "#1f1604",
    "green": "#47c28d",
    "red": "#ef7a7a",
    "blue": "#6aa8ff",
    "violet": "#a58bff",
}

SCALE = [1.0]   # (the screen's scale, 2.0 on a 200% screen: set by apply; every size below goes through px)


def px(n):
    return max(1, int(round(n * SCALE[0])))


# (tracker states: reachable, done, out of reach, unknown)
STATE = {"available": C["green"], "done": C["faint"], "blocked": C["red"], "unknown": C["blue"]}


# (painting)
def _png(w, h, rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return base64.b64encode(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)) +
                            chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def _rgb(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def _rounded_sd(px, py, x0, y0, x1, y1, r):
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    qx = abs(px - cx) - ((x1 - x0) / 2 - r)
    qy = abs(py - cy) - ((y1 - y0) / 2 - r)
    return (max(qx, 0) ** 2 + max(qy, 0) ** 2) ** 0.5 + min(max(qx, qy), 0) - r


def paint(w, h, layers, ss=4):
    """layers: [(signed distance (x, y) -> d, colour, alpha)], painted in order over a transparent image"""
    rows = []
    for y in range(h):
        row = bytearray()
        for x in range(w):
            r = g = b = a = 0.0
            for fn, colour, alpha in layers:
                cover = 0
                for sy in range(ss):
                    for sx in range(ss):
                        if fn(x + (sx + 0.5) / ss, y + (sy + 0.5) / ss) <= 0:
                            cover += 1
                if not cover:
                    continue
                k = alpha * cover / (ss * ss)
                cr, cg, cb = _rgb(colour)
                na = k + a * (1 - k)
                if na > 0:
                    r = (cr * k + r * a * (1 - k)) / na
                    g = (cg * k + g * a * (1 - k)) / na
                    b = (cb * k + b * a * (1 - k)) / na
                a = na
            row += bytes((int(r + 0.5), int(g + 0.5), int(b + 0.5), int(a * 255 + 0.5)))
        rows.append(row)
    return tk.PhotoImage(data=_png(w, h, rows), format="png")


def rounded(fill, border=None, radius=10, size=None, width=1.2, glow=None):
    radius, width = radius * SCALE[0], width * SCALE[0]
    s = int(size or radius * 2 + 12 * SCALE[0])
    m = 3 * SCALE[0] if glow else 0.5
    layers = []
    if glow:
        layers.append((lambda x, y: _rounded_sd(x, y, 0.5, 0.5, s - 0.5, s - 0.5, radius + 2.5 * SCALE[0]), glow, 0.35))
    if border:
        layers.append((lambda x, y: _rounded_sd(x, y, m, m, s - m, s - m, radius), border, 1.0))
        inner = width
    else:
        inner = 0
    layers.append((lambda x, y: _rounded_sd(x, y, m + inner, m + inner, s - m - inner, s - m - inner,
                                           max(radius - inner, 1)), fill, 1.0))
    return paint(s, s, layers)


def switch(on):
    w, h, r = px(46), px(26), px(13)
    track = C["gold"] if on else C["line"]
    kx = w - r if on else r
    knob = C["gold_text"] if on else C["muted"]
    return paint(w, h, [(lambda x, y: _rounded_sd(x, y, 1, 1, w - 1, h - 1, r - 1), track, 1.0),
                        (lambda x, y: ((x - kx) ** 2 + (y - h / 2) ** 2) ** 0.5 - (r - px(4)), knob, 1.0)])


def dot(colour, size=12):
    size = px(size)
    return paint(size, size, [(lambda x, y: ((x - size / 2) ** 2 + (y - size / 2) ** 2) ** 0.5 - size / 2 + 1, colour, 1.0)])


# (fonts)
def _pick(root, *names):
    have = set(tkfont.families(root))
    return next((n for n in names if n in have), names[-1])


class Fonts:
    def __init__(self, root):
        ui = _pick(root, "Segoe UI Variable Text", "Segoe UI", "Noto Sans", "DejaVu Sans", "Helvetica")
        strong = _pick(root, "Segoe UI Semibold", "Segoe UI Variable Text Semibold", ui)
        display = _pick(root, "Segoe UI Variable Display Semibold", "Segoe UI Semibold", ui)
        mono = _pick(root, "Cascadia Mono", "Cascadia Code", "Consolas", "DejaVu Sans Mono", "Courier New")
        self.body = (ui, 10)
        self.small = (ui, 9)
        self.strong = (strong, 10)
        self.heading = (display, 13)
        self.title = (display, 20)
        self.subtitle = (ui, 10)
        self.nav = (strong, 11)
        self.mono = (mono, 9)


def gradient(canvas, w, h, top, bottom, steps=64):
    t, b = _rgb(top), _rgb(bottom)
    for i in range(steps):
        k = i / (steps - 1)
        col = "#%02x%02x%02x" % tuple(int(t[j] + (b[j] - t[j]) * k) for j in range(3))
        y0, y1 = h * i / steps, h * (i + 1) / steps + 1
        canvas.create_rectangle(0, y0, w, y1, fill=col, outline="")


def triforce(canvas, x, y, size, colour, halo=False):
    """three triangles, the top one's apex at (x, y); halo: soft rings of light behind it"""
    s = size
    if halo:
        cx, cy = x, y + s * 0.866 * 1.1
        for i, col in enumerate(("#1a2c4f", "#20365f", "#27416f")):
            r = s * (1.45 - 0.2 * i)
            canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=col, outline="")

    def tri(ax, ay):
        return [ax, ay, ax - s / 2, ay + s * 0.866, ax + s / 2, ay + s * 0.866]
    for ax, ay in ((x, y), (x - s / 2, y + s * 0.866), (x + s / 2, y + s * 0.866)):
        canvas.create_polygon(tri(ax, ay), fill=colour, outline="")


def apply(root):
    """every ttk style the window uses; returns (fonts, images): keep the images alive"""
    SCALE[0] = max(1.0, root.winfo_fpixels("1i") / 96.0)
    f = Fonts(root)
    style = ttk.Style(root)
    style.theme_use("clam")
    root.configure(background=C["night"])
    img = {
        "card": rounded(C["card"], C["line"], radius=14),
        "field": rounded(C["card2"], C["line"], radius=8),
        "field_focus": rounded(C["card2"], C["gold"], radius=8),
        "gold": rounded(C["gold"], radius=9),
        "gold_hover": rounded(C["gold2"], radius=9, glow=C["gold"]),
        "gold_pressed": rounded(C["gold3"], radius=9),
        "gold_disabled": rounded(C["line"], radius=9),
        "ghost": rounded(C["card2"], C["line2"], radius=9),
        "ghost_hover": rounded(C["card3"], C["gold"], radius=9),
        "ghost_pressed": rounded(C["line"], C["gold"], radius=9),
        "nav": rounded(C["night2"], radius=9),
        "nav_hover": rounded(C["card"], radius=9),
        "nav_active": rounded(C["card2"], C["gold"], radius=9),
        "switch_on": switch(True),
        "switch_off": switch(False),
    }
    for k, colour in STATE.items():
        img["dot_" + k] = dot(colour)

    style.configure(".", background=C["night"], foreground=C["text"], font=f.body, bordercolor=C["line"],
                    darkcolor=C["night"], lightcolor=C["night"], troughcolor=C["card2"], focuscolor=C["gold"],
                    selectbackground=C["gold"], selectforeground=C["gold_text"], insertcolor=C["text"])
    style.configure("TFrame", background=C["night"])
    style.configure("Side.TFrame", background=C["night2"])
    style.configure("TLabel", background=C["night"], foreground=C["text"])

    # (cards: a rounded frame; labels on them take the card's colour)
    style.element_create("Card.bg", "image", img["card"], border=px(16), sticky="nsew")
    style.layout("Card.TFrame", [("Card.bg", {"sticky": "nsew", "children": [("Frame.padding", {"sticky": "nsew"})]})])
    style.configure("Card.TFrame", padding=(px(18), px(14), px(18), px(16)))
    style.configure("CardBody.TFrame", background=C["card"])   # (a plain row inside a card)
    style.configure("Card.TLabel", background=C["card"], foreground=C["text"])
    style.configure("CardMuted.TLabel", background=C["card"], foreground=C["muted"], font=f.small)
    style.configure("CardHeading.TLabel", background=C["card"], foreground=C["text"], font=f.heading)
    style.configure("CardStrong.TLabel", background=C["card"], foreground=C["text"], font=f.strong)
    style.configure("Bad.TLabel", background=C["card"], foreground=C["red"], font=f.small)
    style.configure("Good.TLabel", background=C["card"], foreground=C["green"], font=f.small)
    style.configure("Page.TLabel", background=C["night"], foreground=C["text"], font=f.title)
    style.configure("PageMuted.TLabel", background=C["night"], foreground=C["muted"], font=f.subtitle)
    style.configure("Card.TCheckbutton", background=C["card"])

    # (fields)
    style.element_create("Field.bg", "image", img["field"], ("focus", img["field_focus"]), border=px(10), sticky="nsew")
    style.layout("TEntry", [("Field.bg", {"sticky": "nsew", "children": [("Entry.padding", {"sticky": "nsew", "children": [
        ("Entry.textarea", {"sticky": "nsew"})]})]})])
    style.configure("TEntry", padding=(px(10), px(7)), foreground=C["text"], fieldbackground=C["card2"])
    style.configure("TCombobox", padding=(px(8), px(5)), foreground=C["text"], fieldbackground=C["card2"], background=C["card2"],
                    arrowcolor=C["gold"])

    # (buttons: gold for the main action, ghost for the others)
    for name, base in (("Gold", "gold"), ("Ghost", "ghost")):
        states = [("disabled", img["gold_disabled"] if base == "gold" else img["ghost"]),
                  ("pressed", img[base + "_pressed"]), ("active", img[base + "_hover"])]
        style.element_create(name + ".bg", "image", img[base], *states, border=px(11), sticky="nsew")
        style.layout(name + ".TButton", [(name + ".bg", {"sticky": "nsew", "children": [
            ("Button.padding", {"sticky": "nsew", "children": [("Button.label", {"sticky": "nsew"})]})]})])
    style.configure("Gold.TButton", padding=(px(18), px(8)), foreground=C["gold_text"], font=f.strong, anchor="center")
    style.map("Gold.TButton", foreground=[("disabled", C["muted"])])
    style.configure("Ghost.TButton", padding=(px(14), px(7)), foreground=C["text"], font=f.body, anchor="center")
    style.layout("Small.TButton", style.layout("Ghost.TButton"))
    style.configure("Small.TButton", padding=(px(12), px(5)), foreground=C["text"], font=f.small, anchor="center", width=0)
    for name in ("Gold.TButton", "Ghost.TButton", "Small.TButton", "TButton"):
        style.configure(name, background=C["card"])
        style.map(name, background=[("active", C["card"]), ("pressed", C["card"])])
    style.configure("TButton", padding=(px(14), px(7)))
    style.layout("TButton", style.layout("Ghost.TButton"))
    style.configure("TButton", foreground=C["text"], font=f.body, anchor="center")

    # (sidebar navigation)
    style.element_create("Nav.bg", "image", img["nav"], ("selected", img["nav_active"]), ("active", img["nav_hover"]),
                         border=px(10), sticky="nsew")
    style.layout("Nav.TRadiobutton", [("Nav.bg", {"sticky": "nsew", "children": [
        ("Radiobutton.padding", {"sticky": "nsew", "children": [("Radiobutton.label", {"sticky": "w"})]})]})])
    style.configure("Nav.TRadiobutton", padding=(px(16), px(10)), background=C["night2"], foreground=C["muted"], font=f.nav)
    style.map("Nav.TRadiobutton", foreground=[("selected", C["gold"]), ("active", C["text"])])

    # (switches)
    style.element_create("Switch.indicator", "image", img["switch_off"], ("selected", img["switch_on"]), sticky="w")
    style.layout("Switch.TCheckbutton", [("Checkbutton.padding", {"sticky": "nsew", "children": [
        ("Switch.indicator", {"side": "left", "sticky": ""}),
        ("Checkbutton.label", {"side": "left", "sticky": "w", "expand": 1})]})])
    style.configure("Switch.TCheckbutton", background=C["card"], foreground=C["text"], font=f.strong, padding=(px(0), px(4)),
                    indicatormargin=0)
    style.map("Switch.TCheckbutton", background=[("active", C["card"])])

    style.layout("SwitchDark.TCheckbutton", style.layout("Switch.TCheckbutton"))
    style.configure("SwitchDark.TCheckbutton", background=C["night"], foreground=C["text"], font=f.body, padding=(0, px(2)))
    style.map("SwitchDark.TCheckbutton", background=[("active", C["night"])])
    # (segmented age switch)
    style.element_create("Seg.bg", "image", img["ghost"], ("selected", img["gold"]), ("active", img["ghost_hover"]),
                         border=px(11), sticky="nsew")
    style.layout("Seg.TRadiobutton", [("Seg.bg", {"sticky": "nsew", "children": [
        ("Radiobutton.padding", {"sticky": "nsew", "children": [("Radiobutton.label", {"sticky": ""})]})]})])
    style.configure("Seg.TRadiobutton", padding=(px(14), px(5)), background=C["night"], foreground=C["text"], font=f.small)
    style.map("Seg.TRadiobutton", foreground=[("selected", C["gold_text"])], background=[("active", C["night"])])
    style.layout("SegCard.TRadiobutton", style.layout("Seg.TRadiobutton"))   # (the same, on a card: a dungeon's floors)
    style.configure("SegCard.TRadiobutton", padding=(px(12), px(3)), background=C["card"], foreground=C["text"],
                    font=f.small)
    style.map("SegCard.TRadiobutton", foreground=[("selected", C["gold_text"])], background=[("active", C["card"])])
    # (scrollbars, trees)
    style.configure("Vertical.TScrollbar", background=C["card2"], troughcolor=C["card"], bordercolor=C["card"],
                    arrowcolor=C["muted"], gripcount=0, relief="flat")
    style.map("Vertical.TScrollbar", background=[("active", C["line2"])])
    style.configure("Treeview", background=C["card"], fieldbackground=C["card"], foreground=C["text"], rowheight=px(26),
                    bordercolor=C["card"], font=f.body)
    style.configure("Treeview.Heading", background=C["card2"], foreground=C["muted"], font=f.small, relief="flat")
    style.map("Treeview", background=[("selected", C["card3"])], foreground=[("selected", C["gold"])])
    style.configure("TProgressbar", background=C["gold"], troughcolor=C["card2"], bordercolor=C["card2"],
                    lightcolor=C["gold"], darkcolor=C["gold3"])
    return f, img
