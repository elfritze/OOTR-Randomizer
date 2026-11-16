"""HookshotRando's window: choose the game folder, the seed and the settings, generate and install the mod, verify it, turn it
on or off, open its spoiler log; the tracker (rando.tracker_gui) is a page of it. Tkinter only.

    python gui.py

The window never writes in the game folder while the game runs (Longshot or Hookshot): a running game reads the mod's files
as it goes, and replacing them under it can break the session."""
import json
import os
import queue
import secrets
import subprocess
import sys
import threading
import tkinter as tk
import traceback
from tkinter import filedialog, messagebox, ttk

from . import generate, settings, theme
from .theme import C, px

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_EXES = ("longshot.exe", "hookshot.exe")
STATE_FILE = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "HookshotRando", "window.json")
MOD = generate.MOD_NAME
OFF = "_" + MOD   # (a mods sub-folder starting with "_" is off for Longshot and Hookshot)
VERSION = "0.6"
# (the randomizer's public name: "HookshotRando" was a working name; the mod's folder keeps it, see generate.MOD_NAME)
BRAND = "Lost Woods"
TAGLINE = "Ocarina of Time (Switch 2 remake) randomizer  ·  every path leads somewhere new"


def option_var(option, saved):
    """a setting's variable: on/off, or its choice's value (a saved value it no longer has: its default)"""
    if option.choices:
        return tk.StringVar(value=saved if saved in dict(option.choices) else option.default)
    return tk.BooleanVar(value=saved if isinstance(saved, bool) else option.default)


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_state(state):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=1)
    except OSError:
        pass


def running_games():
    """the game executables running now (Windows; elsewhere none can be told)"""
    if os.name != "nt":
        return []
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=15,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.lower()
    except (OSError, subprocess.SubprocessError):
        return []
    return [exe for exe in GAME_EXES if '"%s"' % exe in out]


# (a note's wrap width before its card has a size: without one, the Settings page's long notes each asked for one line
#  thousands of pixels wide inside its scrolling canvas, and Tk's layout never settled: no event, no timer ran)
NOTE_WRAP = px(360)


def set_wrap(label, width):
    """a label's wrap width, changed only when it differs: setting it, even to the same value, has Tk measure the label
    again, which resizes its parent, whose <Configure> set it again: on the Settings page that loop never ended and the
    window stopped answering (2026-11-15: minutes to start, laggy)"""
    width = int(width)
    if abs(int(str(label.cget("wraplength") or 0)) - width) > 2:
        label.configure(wraplength=width)


def game_problem(folder):
    """why folder is not a game folder the mod can be made for (None when it is)"""
    if not folder:
        return "Choose the game folder: the one that holds romfs and mods (Longshot-Build)."
    if not os.path.isfile(os.path.join(folder, "romfs", "Pack", "ZsDic.pack.zs")):
        return "No game romfs in this folder."
    return None


def installed(folder):
    """(state, placements) of the mod in the game folder: state is "on", "off" or None"""
    for name, state in ((MOD, "on"), (OFF, "off")):
        path = os.path.join(folder, "mods", name, "placements.json")
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return state, json.load(f)
            except (OSError, ValueError):
                return state, None
    return None, None


def mod_dir(folder):
    state = installed(folder)[0]
    return os.path.join(folder, "mods", MOD if state != "off" else OFF) if state else None


def open_path(path):
    if os.name == "nt":
        os.startfile(path)   # noqa: S606 (the user's own file or folder)
    else:
        subprocess.Popen(["xdg-open", path])


def card(parent, title=None, subtitle=None, flat=False):
    """a rounded card with an optional heading; returns (outer frame, body frame). flat: a plain card with a thin border
    instead, for pages of many cards: the rounded card's image (alpha, stretched) made the Settings page's layout take
    6 to 40 seconds, freezing the window at its start (2026-11-15)"""
    if flat:
        edge = tk.Frame(parent, background=C["line"], padx=1, pady=1)
        outer = ttk.Frame(edge, style="CardBody.TFrame", padding=(px(20), px(16), px(20), px(18)))
        outer.pack(fill="both", expand=True)
    else:
        edge = outer = ttk.Frame(parent, style="Card.TFrame", padding=(px(20), px(16), px(20), px(18)))
    body = outer
    if title:
        ttk.Label(outer, text=title, style="CardHeading.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(outer, text=subtitle, style="CardMuted.TLabel", wraplength=px(640), justify="left").pack(anchor="w")
        body = ttk.Frame(outer, style="Card.TFrame", padding=0)
        body.configure(style="CardBody.TFrame")
        body.pack(fill="both", expand=True, pady=(px(10), px(0)))
    return edge, body


class Window:
    def __init__(self, root):
        self.root = root
        self.fonts, self.images = theme.apply(root)
        ttk.Style(root).configure("CardBody.TFrame", background=C["card"])
        self.state = load_state()
        self.queue = queue.Queue()
        self.busy = False
        self.games = []
        self.polling = False
        root.title(BRAND + " — OoT remake randomizer")
        self.scale = max(1.0, root.winfo_fpixels("1i") / 96.0)
        root.geometry(self.state.get("geometry") or "%dx%d" % (1120 * self.scale, 800 * self.scale))
        root.minsize(int(960 * self.scale), int(680 * self.scale))
        self._header()
        main = ttk.Frame(root)
        main.pack(fill="both", expand=True)
        self.side = ttk.Frame(main, style="Side.TFrame", padding=(px(10), px(14)))
        self.side.pack(side="left", fill="y")
        self.content = ttk.Frame(main, padding=(px(18), px(14), px(18), px(18)))
        self.content.pack(side="left", fill="both", expand=True)
        self.page = tk.StringVar(value="generate")
        self.pages = {}
        saved = self.state.get("settings", {})
        self.options = {o.key: option_var(o, saved.get(o.key, o.default)) for o in settings.OPTIONS}
        self._nav("generate", "  ◆  Generate")
        self.pages["generate"] = self._build_generate(ttk.Frame(self.content))
        self._nav("settings", "  ☰  Settings")
        self.pages["settings"] = self._build_settings(ttk.Frame(self.content))
        self.tracker = None
        try:
            from . import tracker_gui
            frame = ttk.Frame(self.content)
            self.tracker = tracker_gui.TrackerTab(frame, self)
            self._nav("tracker", "  ◎  Tracker")
            self.pages["tracker"] = frame
        except ImportError:
            pass
        try:
            from . import ap_gui
            frame = ttk.Frame(self.content)
            self.archipelago = ap_gui.ArchipelagoPage(frame, self)
            self._nav("archipelago", "  ✦  Archipelago")
            self.pages["archipelago"] = frame
        except ImportError:
            self.archipelago = None
        self._nav("about", "  ?  About")
        self.pages["about"] = self._build_about(ttk.Frame(self.content))
        ttk.Frame(self.side, style="Side.TFrame").pack(fill="y", expand=True)
        ttk.Label(self.side, text="v" + VERSION, background=C["night2"], foreground=C["faint"],
                  font=self.fonts.small).pack(anchor="w", padx=px(12))
        self.show(self.state.get("page", "generate"))
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh()
        root.after(100, self._pump)
        root.after(4000, self._poll_game)

    # (frame)
    def _header(self):
        from tkinter import font as tkfont
        title_h = tkfont.Font(font=self.fonts.title).metrics("linespace")
        sub_h = tkfont.Font(font=self.fonts.subtitle).metrics("linespace")
        h = int(title_h + sub_h + 30 * self.scale)
        tri = title_h * 0.62
        cv = tk.Canvas(self.root, height=h, highlightthickness=0, background=C["night"])
        cv.pack(fill="x")

        def draw(event=None):
            w = cv.winfo_width() or 1080
            cv.delete("all")
            theme.gradient(cv, w, h, "#1b2f55", C["night"])
            cv.create_line(0, h - 1, w, h - 1, fill=C["line"])
            left = 22 * self.scale + tri
            theme.triforce(cv, left, h / 2 - tri * 0.866, tri, C["gold"], halo=True)
            x = left + tri * 1.6
            top = (h - title_h - sub_h) / 2
            cv.create_text(x, top, text=BRAND, anchor="nw", fill=C["text"], font=self.fonts.title)
            cv.create_text(x + 2, top + title_h, text=TAGLINE,
                           anchor="nw", fill=C["muted"], font=self.fonts.subtitle)
            self._header_status(cv, w)
        self.header = cv
        cv.bind("<Configure>", draw)
        self._draw_header = draw

    def _header_status(self, cv, w):
        if self.games:
            text, colour = "●  Game running", C["red"]
        else:
            text, colour = "●  Game closed", C["green"]
        cv.create_text(w - 24 * self.scale, int(cv.cget("height")) / 2, text=text, anchor="e", fill=colour, font=self.fonts.strong)

    def _nav(self, key, label):
        b = ttk.Radiobutton(self.side, text=label, value=key, variable=self.page, style="Nav.TRadiobutton",
                            command=lambda: self.show(key), width=18)
        b.pack(fill="x", pady=px(2))

    def show(self, key):
        if key not in self.pages:
            key = "generate"
        self.page.set(key)
        for k, frame in self.pages.items():
            if k == key:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
        if key == "tracker" and self.tracker:
            self.tracker.reload()

    # (the Generate page)
    def _build_generate(self, page):
        ttk.Label(page, text="Generate a seed", style="Page.TLabel").pack(anchor="w")
        ttk.Label(page, text="Build a randomized game from your own copy and install it as a mod.",
                  style="PageMuted.TLabel").pack(anchor="w", pady=(px(0), px(12)))
        grid = ttk.Frame(page)
        grid.pack(fill="both", expand=True)
        grid.columnconfigure(0, weight=3, uniform="c")
        grid.columnconfigure(1, weight=2, uniform="c")
        grid.rowconfigure(1, weight=1)

        left = ttk.Frame(grid)
        left.grid(row=0, column=0, sticky="nsew", padx=(px(0), px(10)))
        game, body = card(left, "Game", "Longshot's game folder: it holds romfs and mods.")
        game.pack(fill="x")
        body.columnconfigure(0, weight=1)
        self.folder = tk.StringVar(value=self.state.get("game", ""))
        ttk.Entry(body, textvariable=self.folder).grid(row=0, column=0, sticky="ew")
        ttk.Button(body, text="Browse…", command=self.browse).grid(row=0, column=1, padx=(px(8), px(0)))
        self.folder_note = ttk.Label(body, text="", style="Bad.TLabel")
        self.folder_note.grid(row=1, column=0, columnspan=2, sticky="w", pady=(px(6), px(0)))

        seed, body = card(left, "Seed", "The same seed and settings give the same game, on any PC.")
        seed.pack(fill="x", pady=(px(12), px(0)))
        body.columnconfigure(0, weight=1)
        self.seed = tk.StringVar(value=self.state.get("seed", ""))
        ttk.Entry(body, textvariable=self.seed, font=self.fonts.mono).grid(row=0, column=0, sticky="ew")
        ttk.Button(body, text="⟳  Random", command=self.random_seed).grid(row=0, column=1, padx=(px(8), px(0)))

        opts, body = card(grid, "Settings")
        opts.grid(row=0, column=1, sticky="nsew")
        self.summary_labels = []
        for _ in settings.SECTIONS:
            label = ttk.Label(body, text="", style="CardMuted.TLabel", justify="left", wraplength=NOTE_WRAP)
            label.pack(anchor="w", fill="x", pady=(px(0), px(6)))
            self.summary_labels.append(label)
        body.bind("<Configure>", lambda e: [set_wrap(n, max(px(120), e.width - px(8))) for n in self.summary_labels])
        for var in self.options.values():
            var.trace_add("write", lambda *_: self._show_summary())
        self._show_summary()
        row = ttk.Frame(body, style="CardBody.TFrame")
        row.pack(anchor="w", pady=(px(4), px(0)))
        ttk.Button(row, text="Change…", style="Small.TButton", command=lambda: self.show("settings")).pack(
            side="left", padx=(px(0), px(6)))
        ttk.Button(row, text="Defaults", style="Small.TButton", command=self.defaults).pack(side="left")

        bottom, body = card(grid)
        bottom.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(px(12), px(0)))
        bar = ttk.Frame(body, style="CardBody.TFrame")
        bar.pack(fill="x")
        self.generate_button = ttk.Button(bar, text="✦  Generate and install", style="Gold.TButton", command=self.generate)
        self.generate_button.pack(side="left")
        ttk.Button(bar, text="Verify", command=self.verify).pack(side="left", padx=(px(10), px(0)))
        self.toggle_button = ttk.Button(bar, text="Turn mod off", command=self.toggle)
        self.toggle_button.pack(side="left", padx=px(6))
        ttk.Button(bar, text="Spoiler log", command=self.open_spoiler).pack(side="left")
        ttk.Button(bar, text="Mods folder", command=self.open_mods).pack(side="left", padx=px(6))
        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=px(120))
        self.status = ttk.Label(body, text="", style="CardStrong.TLabel", wraplength=px(900), justify="left")
        self.status.pack(anchor="w", pady=(px(12), px(6)))
        logbox = tk.Frame(body, background=C["line"], padx=px(1), pady=px(1))
        logbox.pack(fill="both", expand=True)
        self.log_text = tk.Text(logbox, height=8, wrap="word", state="disabled", background="#0d1626",
                                foreground="#c9d5ea", insertbackground=C["text"], relief="flat", font=self.fonts.mono,
                                padx=px(10), pady=px(8), borderwidth=0, selectbackground=C["gold"],
                                selectforeground=C["gold_text"])
        scroll = ttk.Scrollbar(logbox, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.tag_configure("ok", foreground=C["green"])
        self.log_text.tag_configure("bad", foreground=C["red"])
        self.log_text.tag_configure("note", foreground=C["gold"])
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.folder.trace_add("write", lambda *_: self.refresh())
        return page

    def _build_about(self, page):
        ttk.Label(page, text="About", style="Page.TLabel").pack(anchor="w")
        ttk.Label(page, text="%s %s  (working name: HookshotRando)" % (BRAND, VERSION), style="PageMuted.TLabel").pack(anchor="w", pady=(px(0), px(12)))
        about, body = card(page, "What it does")
        about.pack(fill="x")
        for line in (
                "Every one-time chest, NPC gift, song and loose item of the remake is shuffled with Ship of Harkinian's "
                "glitchless logic, adapted where the remake differs; every seed is checked to be finishable.",
                "The mod is made on this PC from your own copy of the game: share the seed text, never the mod folder.",
                "Fixes for the remake's own story locks: Mido, King Zora, the Dodongo's Cavern boulder (bombs), Darunia's "
                "bracelet, going back to child as soon as you are adult, Zora's River's walls, ammunition for the Bow "
                "and the Slingshot.",
                "README.md beside gui.py lists every change and what is confirmed in game."):
            ttk.Label(body, text="•  " + line, style="Card.TLabel", wraplength=px(760), justify="left").pack(anchor="w", pady=px(3))
        return page

    # (helpers)
    def log(self, text, tag=None):
        self.queue.put(("log", (text, tag)))

    def call_soon(self, fn):
        """fn run on the window's thread at its next pump: a worker thread hands its result over this way. Tk must not be
        called from another thread (root.after there blocked until Tk took the call: the window froze for minutes)"""
        self.queue.put(("call", fn))

    def _pump(self):
        try:
            while True:
                kind, value = self.queue.get_nowait()
                if kind == "log":
                    text, tag = value
                    if tag is None:
                        low = text.lower()
                        tag = "bad" if ("failed" in low or "problem" in low and " 0 problems" not in low) else \
                            "ok" if ("done" in low or " 0 problems" in low) else None
                    self.log_text.configure(state="normal")
                    self.log_text.insert("end", text.rstrip("\n") + "\n", tag or ())
                    self.log_text.see("end")
                    self.log_text.configure(state="disabled")
                elif kind == "call":
                    value()
                elif kind == "done":
                    self.busy = False
                    self.generate_button.configure(state="normal")
                    self.progress.stop()
                    self.progress.pack_forget()
                    self.refresh()
                    if self.tracker:
                        self.tracker.reload()
        except queue.Empty:
            pass
        self.root.after(100, self._pump)

    def _poll_game(self):
        def work():
            games = running_games()
            self.call_soon(lambda: self._set_games(games))
        if not self.polling:   # (one check at a time: tasklist can take seconds)
            self.polling = True
            threading.Thread(target=work, daemon=True).start()
        self.root.after(5000, self._poll_game)

    def _set_games(self, games):
        self.polling = False
        if games != self.games:
            self.games = games
            self._draw_header()
            self.refresh()

    def _show_summary(self):
        for label, line in zip(self.summary_labels, settings.summary({k: v.get() for k, v in self.options.items()})):
            title, _, rest = line.partition(": ")
            label.configure(text="%s  ·  %s" % (title, rest))

    # (the Settings page: Ship of Harkinian's groups, with what this randomizer does)
    def _build_settings(self, page):
        ttk.Label(page, text="Settings", style="Page.TLabel").pack(anchor="w")
        ttk.Label(page, text="Grouped as Ship of Harkinian's randomizer groups them. The same seed and settings give the "
                             "same game.", style="PageMuted.TLabel").pack(anchor="w", pady=(px(0), px(10)))
        outer = ttk.Frame(page)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, background=C["night"], highlightthickness=0)
        bar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=bar.set)
        canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width - px(4)))

        def wheel(event):
            canvas.yview_scroll(int(-event.delta / 120) * 3, "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", wheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
        inner.columnconfigure(0, weight=1, uniform="s")
        inner.columnconfigure(1, weight=1, uniform="s")
        helps = []

        def wrap(widget, note, indent):
            widget.bind("<Configure>", lambda e: set_wrap(note, max(px(160), e.width - indent)), add="+")

        cards = []
        for key, (title, about) in settings.SECTIONS.items():
            frame, body = card(inner, title, about, flat=True)
            cards.append(frame)
            for o in (o for o in settings.OPTIONS if o.section == key):
                row = ttk.Frame(body, style="CardBody.TFrame")
                row.pack(fill="x", anchor="w")
                if o.choices:   # (its label, then one button per choice)
                    ttk.Label(row, text=o.label, style="CardStrong.TLabel").pack(anchor="w", pady=(px(4), px(2)))
                    seg = ttk.Frame(body, style="CardBody.TFrame")
                    seg.pack(fill="x", anchor="w", padx=(px(44), px(0)))
                    for value, label in o.choices:
                        ttk.Radiobutton(seg, text=label, value=value, variable=self.options[o.key],
                                        style="SegCard.TRadiobutton").pack(side="left", padx=(px(0), px(2)))
                else:
                    ttk.Checkbutton(row, text="  " + o.label, variable=self.options[o.key],
                                    style="Switch.TCheckbutton").pack(side="left")
                if not o.seen:
                    tk.Label(body, text=" not yet tested in game ", background=C["card2"], foreground=C["gold"],
                             font=self.fonts.small).pack(anchor="w", padx=(px(52), px(0)), pady=(px(2), px(4)))
                note = ttk.Label(body, text=o.help, style="CardMuted.TLabel", justify="left", wraplength=NOTE_WRAP)
                note.pack(anchor="w", fill="x", padx=(px(52), px(0)), pady=(px(0), px(10)))
                wrap(body, note, px(60))
                helps.append(note)
        for key, title in settings.FIXED_SECTIONS.items():
            frame, body = card(inner, title, "Fixed in this version: shown as Ship of Harkinian names them.", flat=True)
            cards.append(frame)
            for section, label, value, why in settings.FIXED:
                if section != key:
                    continue
                line = ttk.Frame(body, style="CardBody.TFrame")
                line.pack(fill="x", anchor="w")
                ttk.Label(line, text=label, style="CardStrong.TLabel").pack(side="left")
                ttk.Label(line, text="  " + value, style="Good.TLabel").pack(side="left")
                if why:
                    note = ttk.Label(body, text=why, style="CardMuted.TLabel", justify="left", wraplength=NOTE_WRAP)
                    note.pack(anchor="w", fill="x", pady=(px(0), px(8)))
                    wrap(body, note, px(8))
                else:
                    ttk.Frame(body, style="CardBody.TFrame", height=px(8)).pack()
        for i, frame in enumerate(cards):
            frame.grid(row=i // 2, column=i % 2, sticky="nsew", padx=(px(0) if i % 2 == 0 else px(6), px(6) if i % 2 == 0 else px(0)),
                       pady=(px(0), px(12)))
        row = ttk.Frame(inner)
        row.grid(row=(len(cards) + 1) // 2, column=0, columnspan=2, sticky="w")
        ttk.Button(row, text="Defaults", style="Small.TButton", command=self.defaults).pack(side="left")
        ttk.Button(row, text="Export…", style="Small.TButton", command=self.export_settings).pack(side="left", padx=px(6))
        ttk.Button(row, text="Import…", style="Small.TButton", command=self.import_settings).pack(side="left")
        return page

    def chosen(self):
        return settings.normalized({k: v.get() for k, v in self.options.items()})

    def remember(self):
        self.state.update({"game": self.folder.get().strip(), "seed": self.seed.get().strip(),
                           "settings": {k: v.get() for k, v in self.options.items()}, "page": self.page.get(),
                           "geometry": self.root.geometry()})
        save_state(self.state)

    def refresh(self):
        folder = self.folder.get().strip()
        problem = game_problem(folder)
        self.folder_note.configure(text=problem or "", style="Bad.TLabel")
        if problem:
            self.status.configure(text="")
            return
        self.folder_note.configure(text="✓  Game found.", style="Good.TLabel")
        state, plan = installed(folder)
        if state is None:
            text = "No seed installed yet."
        else:
            seed = plan.get("seed") if plan else "?"
            text = "Installed seed:  %s   (%s)" % (seed, "on" if state == "on" else "off: the game runs without it")
            self.toggle_button.configure(text="Turn mod off" if state == "on" else "Turn mod on")
        if self.games:
            text += "\nThe game is running: close it before installing or turning the mod on or off."
        self.status.configure(text=text)

    def ready(self, action):
        folder = self.folder.get().strip()
        problem = game_problem(folder)
        if problem:
            messagebox.showerror(BRAND, problem)
            return None
        if self.busy:
            messagebox.showinfo(BRAND, "Wait for the current work to finish.")
            return None
        games = running_games()
        if games:
            messagebox.showerror(BRAND, "The game is running (%s). Close it before you %s." % (
                ", ".join(games), action))
            return None
        return folder

    # (actions)
    def browse(self):
        path = filedialog.askdirectory(title="The game folder (it holds romfs and mods)",
                                       initialdir=self.folder.get() or None)
        if path:
            self.folder.set(os.path.normpath(path))
            self.remember()

    def random_seed(self):
        self.seed.set(secrets.token_hex(4))

    def defaults(self):
        for k, v in self.options.items():
            v.set(settings.DEFAULTS[k])   # (RETIRED keys have no switch)

    def export_settings(self):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Settings", "*.json")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"seed": self.seed.get().strip(), "settings": self.chosen()}, f, indent=1)

    def import_settings(self):
        path = filedialog.askopenfilename(filetypes=[("Settings", "*.json")])
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            chosen = settings.normalized(data.get("settings", {}))
        except (OSError, ValueError) as e:
            messagebox.showerror(BRAND, "Not a settings file: %s" % e)
            return
        for k, v in chosen.items():
            if k in self.options:   # (a retired setting has no switch)
                self.options[k].set(v)
        if data.get("seed"):
            self.seed.set(data["seed"])

    def generate(self, confirm=True):
        folder = self.ready("install a seed")
        if not folder:
            return
        state, plan = installed(folder)
        if state == "off":
            messagebox.showerror(BRAND, "The installed seed is turned off (mods\\%s). Turn it on or delete it "
                                 "before installing a new one." % OFF)
            return
        if state == "on" and confirm and not messagebox.askyesno(BRAND, (
                "This replaces the installed seed (%s). A save made with it will not match the new one: start a new game "
                "for the new seed.\n\nReplace it?") % ((plan or {}).get("seed", "?"))):
            return
        seed = self.seed.get().strip() or secrets.token_hex(4)
        self.seed.set(seed)
        chosen = self.chosen()
        self.remember()
        self.busy = True
        self.generate_button.configure(state="disabled")
        self.progress.pack(side="right")
        self.progress.start(12)
        self.log("Generating seed %s (%s)…" % (seed, ", ".join("%s %s" % (k, "on" if v else "off")
                                                               for k, v in chosen.items())), "note")

        def work():
            try:
                generate.generate(os.path.join(folder, "romfs"), os.path.join(folder, "mods"), seed, chosen, log=self.log)
                self.log("Done. Start a new game to play it.", "ok")
            except Exception:   # (shown, not swallowed: the log is the user's only window on it)
                self.log("Generation failed:\n" + traceback.format_exc(), "bad")
            self.queue.put(("done", None))
        threading.Thread(target=work, daemon=True).start()

    def verify(self):
        folder = self.folder.get().strip()
        if game_problem(folder) or installed(folder)[0] is None:
            messagebox.showerror(BRAND, "No seed installed in this game folder.")
            return
        target = mod_dir(folder)
        self.log("Verifying %s…" % target, "note")

        def work():
            try:
                out = subprocess.run([sys.executable, os.path.join(HERE, "tools", "verify_mod.py"),
                                      os.path.join(folder, "romfs"), target], capture_output=True, text=True,
                                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                self.log((out.stdout + out.stderr).strip() or "(no output)")
            except OSError as e:
                self.log("Could not run the verifier: %s" % e, "bad")
        threading.Thread(target=work, daemon=True).start()

    def toggle(self):
        folder = self.ready("turn the mod on or off")
        if not folder:
            return
        state = installed(folder)[0]
        if state is None:
            messagebox.showerror(BRAND, "No seed installed in this game folder.")
            return
        src, dst = (MOD, OFF) if state == "on" else (OFF, MOD)
        if os.path.exists(os.path.join(folder, "mods", dst)):
            messagebox.showerror(BRAND, "mods\\%s exists already: remove one of the two." % dst)
            return
        os.rename(os.path.join(folder, "mods", src), os.path.join(folder, "mods", dst))
        self.log("Mod turned %s (mods\\%s)." % ("off" if state == "on" else "on", dst), "ok")
        self.refresh()

    def open_spoiler(self):
        folder = self.folder.get().strip()
        target = mod_dir(folder) if not game_problem(folder) else None
        if not target or not os.path.isfile(os.path.join(target, "spoiler.txt")):
            messagebox.showerror(BRAND, "No spoiler log: no seed installed in this game folder.")
            return
        open_path(os.path.join(target, "spoiler.txt"))

    def open_mods(self):
        folder = self.folder.get().strip()
        if game_problem(folder):
            messagebox.showerror(BRAND, game_problem(folder))
            return
        os.makedirs(os.path.join(folder, "mods"), exist_ok=True)
        open_path(os.path.join(folder, "mods"))

    def close(self):
        self.remember()
        if self.tracker:
            self.tracker.close()
        self.root.destroy()


def dpi_aware():
    """sharp text on scaled Windows screens (else Windows stretches a blurry bitmap of the window)"""
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


def main(argv=None):
    dpi_aware()
    root = tk.Tk()
    Window(root)
    if argv and "--selftest" in argv:   # (built, shown for a moment, closed: for tests)
        root.after(1500, root.destroy)
    root.mainloop()


if __name__ == "__main__":
    main(sys.argv)
