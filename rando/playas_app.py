"""Character Changer: the Character page as an app of its own, for players who do not use the randomizer (or use another
one). Choose the game folder, choose who adult Link is, Apply: the character's mod goes in mods\\~PlayAs<Name>, beside
whatever other mods are there (rando.playas.build: it is built on top of them, and sorts after them).

    python character_changer.py          (CharacterChanger.exe, packaged by tools/build_exe.py)"""
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import playas, theme
from .gui import card, dpi_aware, game_problem, load_state, open_path, running_games, save_state
from .playas_gui import CharacterPage
from .theme import C, px

BRAND = "Character Changer"
VERSION = "1.0"
TAGLINE = "Play adult Link as someone else  ·  Ocarina of Time (Switch 2 remake) on Longshot"
STATE_KEY = "character_changer"   # (its own part of the window state file: the randomizer's window keeps the rest)


class App:
    def __init__(self, root, catch_up=True):
        self.root = root
        self.fonts, self.images = theme.apply(root)
        ttk.Style(root).configure("CardBody.TFrame", background=C["card"])
        self.all_state = load_state()
        self.state = self.all_state.setdefault(STATE_KEY, {})
        self.queue = queue.Queue()
        self.busy = False
        self.games = []
        self.polling = False
        root.title(BRAND)
        self.scale = max(1.0, root.winfo_fpixels("1i") / 96.0)
        root.geometry(self.state.get("geometry") or "%dx%d" % (1000 * self.scale, 1000 * self.scale))
        root.minsize(int(760 * self.scale), int(640 * self.scale))
        self._header()
        content = ttk.Frame(root, padding=(px(18), px(14), px(18), px(18)))
        content.pack(fill="both", expand=True)

        game, body = card(content, "Game", "Longshot's game folder: the one that holds romfs and mods.")
        game.pack(fill="x", pady=(px(0), px(12)))
        body.columnconfigure(0, weight=1)
        # (the randomizer's window may have the folder already)
        self.folder = tk.StringVar(value=self.state.get("game") or self.all_state.get("game", ""))
        ttk.Entry(body, textvariable=self.folder).grid(row=0, column=0, sticky="ew")
        ttk.Button(body, text="Browse…", command=self.browse).grid(row=0, column=1, padx=(px(8), px(0)))
        ttk.Button(body, text="Mods folder", command=self.open_mods).grid(row=0, column=2, padx=(px(6), px(0)))
        self.folder_note = ttk.Label(body, text="", style="Bad.TLabel")
        self.folder_note.grid(row=1, column=0, columnspan=3, sticky="w", pady=(px(6), px(0)))

        log_card, log_body = card(content)
        log_card.pack(side="bottom", fill="x", pady=(px(12), px(0)))
        self.log_text = tk.Text(log_body, height=3, background=C["card"], foreground=C["muted"], relief="flat",
                                highlightthickness=0, wrap="word", font=self.fonts.small, state="disabled")
        self.log_text.pack(fill="x")
        self.log_text.tag_configure("ok", foreground=C["green"])
        self.log_text.tag_configure("bad", foreground=C["red"])
        self.log_text.tag_configure("note", foreground=C["text"])

        page = ttk.Frame(content)
        page.pack(fill="both", expand=True)
        self.character = CharacterPage(page, self)
        self.folder.trace_add("write", lambda *_: self.refresh())
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh()
        root.after(100, self._pump)
        root.after(1500, self._poll_game)
        if catch_up:
            root.after(300, self._catch_up)

    def _header(self):
        from tkinter import font as tkfont
        title_h = tkfont.Font(font=self.fonts.title).metrics("linespace")
        sub_h = tkfont.Font(font=self.fonts.subtitle).metrics("linespace")
        h = int(title_h + sub_h + 30 * self.scale)
        tri = title_h * 0.62
        cv = tk.Canvas(self.root, height=h, highlightthickness=0, background=C["night"])
        cv.pack(fill="x")

        def draw(event=None):
            w = cv.winfo_width() or 980
            cv.delete("all")
            theme.gradient(cv, w, h, "#1b2f55", C["night"])
            cv.create_line(0, h - 1, w, h - 1, fill=C["line"])
            left = 22 * self.scale + tri
            theme.triforce(cv, left, h / 2 - tri * 0.866, tri, C["gold"], halo=True)
            x = left + tri * 1.6
            top = (h - title_h - sub_h) / 2
            cv.create_text(x, top, text=BRAND, anchor="nw", fill=C["text"], font=self.fonts.title)
            cv.create_text(x + 2, top + title_h, text=TAGLINE, anchor="nw", fill=C["muted"], font=self.fonts.subtitle)
            text, colour = ("●  Game running", C["red"]) if self.games else ("●  Game closed", C["green"])
            cv.create_text(w - 24 * self.scale, h / 2, text=text, anchor="e", fill=colour, font=self.fonts.strong)
        cv.bind("<Configure>", draw)
        self._draw_header = draw

    # (what CharacterPage asks of its window)
    def log(self, text, tag=None):
        self.queue.put(("log", (text, tag)))

    def call_soon(self, fn):
        self.queue.put(("call", fn))

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
            messagebox.showerror(BRAND, "The game is running (%s). Close it before you %s." % (", ".join(games), action))
            return None
        return folder

    def remember(self):
        self.state.update({"game": self.folder.get().strip(), "geometry": self.root.geometry()})
        save_state(self.all_state)

    def refresh(self):
        problem = game_problem(self.folder.get().strip())
        self.folder_note.configure(text=problem or "✓  Game found.", style="Bad.TLabel" if problem else "Good.TLabel")
        self.character.refresh()

    def _catch_up(self):
        """at the start: the character that is on built again if the other mods changed since (a new seed, a mod added)"""
        folder = self.folder.get().strip()
        if game_problem(folder) or self.busy or running_games():
            return
        try:
            why = playas.outdated(folder)
        except (playas.Problem, OSError):
            return
        if why:
            self.character.run(folder, None, "Your other mods changed (%s): building the character again…" % why,
                               again=True)

    def _pump(self):
        try:
            while True:
                kind, value = self.queue.get_nowait()
                if kind == "log":
                    text, tag = value
                    self.log_text.configure(state="normal")
                    self.log_text.insert("end", text.rstrip("\n") + "\n", tag or ())
                    self.log_text.see("end")
                    self.log_text.configure(state="disabled")
                elif kind == "call":
                    value()
                elif kind == "done":
                    self.busy = False
                    self.character.finished()
                    self.refresh()
        except queue.Empty:
            pass
        self.root.after(100, self._pump)

    def _poll_game(self):
        def work():
            games = running_games()
            self.call_soon(lambda: self._set_games(games))
        if not self.polling:
            self.polling = True
            threading.Thread(target=work, daemon=True).start()
        self.root.after(5000, self._poll_game)

    def _set_games(self, games):
        self.polling = False
        if games != self.games:
            self.games = games
            self._draw_header()
            self.refresh()

    def browse(self):
        path = filedialog.askdirectory(title="The game folder (it holds romfs and mods)",
                                       initialdir=self.folder.get() or None)
        if path:
            self.folder.set(os.path.normpath(path))
            self.remember()

    def open_mods(self):
        folder = self.folder.get().strip()
        if game_problem(folder):
            messagebox.showerror(BRAND, game_problem(folder))
            return
        os.makedirs(os.path.join(folder, "mods"), exist_ok=True)
        open_path(os.path.join(folder, "mods"))

    def close(self):
        self.remember()
        self.root.destroy()


def main(argv=None):
    dpi_aware()
    root = tk.Tk()
    icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
    if os.path.exists(icon):
        try:
            root.iconbitmap(default=icon)
        except tk.TclError:
            pass
    test = bool(argv and "--selftest" in argv)
    App(root, catch_up=not test)
    if test:
        root.after(2500, root.destroy)
    root.mainloop()
