"""The window's Character page: who adult Link is dressed as (rando.playas), switched whenever the game is closed.

The character is a mod of its own beside the seed's: the seed, its spoiler log and the save are not touched, and the same
seed plays the same as any character. One press builds the character's mod from the game's own files (a few seconds) and
installs it; "Link" turns it off. The window builds it again by itself after a new seed is installed (the character's mod
ships the one resource size table the game reads, built on the seed's)."""
import threading
import tkinter as tk
import traceback
from tkinter import messagebox, ttk

from . import playas
from .theme import C, px

LINK = "link"
COLUMNS = 4
MARK_SEEN, MARK_NEW, MARK_ROUGH = "✓", "·", "≈"


def tile_text(c):
    return "%s  %s" % (MARK_ROUGH if getattr(c, "rough", False) else MARK_SEEN if c.seen else MARK_NEW, c.label)


class CharacterPage:
    def __init__(self, frame, window):
        self.frame, self.window = frame, window
        saved = window.state.get("character", LINK)
        self.choice = tk.StringVar(value=saved if saved in playas.CHARACTERS else LINK)
        self.shown_for = None   # (the game folder the choice was last set from)
        self._build()
        self.refresh()

    def _build(self):
        from .gui import card, set_wrap
        page = self.frame
        ttk.Label(page, text="Character", style="Page.TLabel").pack(anchor="w")
        ttk.Label(page, text="Play adult Link as someone else. The seed, its logic and your save stay as they are: switch "
                             "whenever the game is closed.", style="PageMuted.TLabel").pack(anchor="w", pady=(px(0), px(10)))

        # (the Apply bar stays at the bottom; the list above it scrolls when the window is short)
        bottom, body = card(page)
        bottom.pack(side="bottom", fill="x", pady=(px(12), px(0)))
        bar = ttk.Frame(body, style="CardBody.TFrame")
        bar.pack(fill="x")
        self.apply_button = ttk.Button(bar, text="✦  Apply", style="Gold.TButton", command=self.apply)
        self.apply_button.pack(side="left")
        self.status = ttk.Label(bar, text="", style="CardStrong.TLabel", justify="left")
        self.status.pack(side="left", padx=(px(14), px(0)))
        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=px(120))
        self.note = ttk.Label(body, text="", style="CardMuted.TLabel", wraplength=px(700), justify="left")

        outer = ttk.Frame(page)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, background=C["night"], highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        window = canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window, width=e.width - px(4)))

        def wheel(event):
            if inner.winfo_height() > canvas.winfo_height():
                canvas.yview_scroll(int(-event.delta / 120) * 3, "units")
        canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", wheel))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        who, body = card(inner, "Who", flat=True)
        who.pack(fill="x")
        about = ttk.Label(body, text="Worn as the Goron and Zora tunics, with the character's own cloth and voice. In the "
                                     "Kokiri tunic Link is Link (the game builds that one into him), so keep one of the "
                                     "other two on. Young Link is never changed.",
                          style="CardMuted.TLabel", wraplength=px(700), justify="left")
        about.pack(anchor="w", fill="x", pady=(px(0), px(8)))
        ttk.Radiobutton(body, text="Link, as he is", value=LINK, variable=self.choice,
                        style="SegCard.TRadiobutton").pack(anchor="w")
        for group, what in playas.GROUPS:
            ttk.Label(body, text=group, style="CardStrong.TLabel").pack(anchor="w", pady=(px(10), px(0)))
            ttk.Label(body, text=what, style="CardMuted.TLabel").pack(anchor="w", pady=(px(0), px(3)))
            grid = ttk.Frame(body, style="CardBody.TFrame")
            grid.pack(fill="x", anchor="w")
            for i in range(COLUMNS):
                grid.columnconfigure(i, weight=1, uniform="who")
            keys = [k for k, c in playas.CHARACTERS.items() if c.group == group]
            for i, key in enumerate(keys):
                ttk.Radiobutton(grid, text=tile_text(playas.CHARACTERS[key]), value=key, variable=self.choice,
                                style="SegCard.TRadiobutton").grid(row=i // COLUMNS, column=i % COLUMNS, sticky="ew",
                                                                   padx=(px(0), px(3)), pady=px(2))
        legend = ttk.Label(body, text="\n".join((
            "%s  seen in game and approved" % MARK_SEEN,
            "%s  built the same way, not yet seen in game" % MARK_NEW,
            "%s  rough fit: a body far from Link's, limbs can look pulled where they bend" % MARK_ROUGH)),
            style="CardMuted.TLabel", justify="left")
        legend.pack(anchor="w", pady=(px(12), px(0)))
        body.bind("<Configure>", lambda e: [set_wrap(n, max(px(160), e.width - px(8))) for n in (about, self.note)], add="+")
        self.choice.trace_add("write", lambda *_: self._remember())

    def _remember(self):
        self.window.state["character"] = self.choice.get()

    def refresh(self):
        """what is installed in the game folder, in words; the choice follows it when the folder changes"""
        from .gui import game_problem
        folder = self.window.folder.get().strip()
        if game_problem(folder):
            self.status.configure(text="Choose the game folder on the Generate page first.")
            self.note.configure(text="")
            return
        on = playas.current(folder)
        if self.shown_for != folder:
            self.shown_for = folder
            self.choice.set(on or LINK)
        if on is None:
            text = "Now:  Link, as he is."
        else:
            text = "Now:  %s." % playas.CHARACTERS[on].label
        notes = []
        try:
            why = playas.outdated(folder) if on and not self.window.busy else None
        except (playas.Problem, OSError):
            why = None
        if why:
            notes.append("Its mod was built for another seed (%s): press Apply to build it again before you play." % why)
        if self.window.games:
            notes.append("The game is running: close it to switch.")
        self.status.configure(text=text)
        self.note.configure(text="\n".join(notes))
        if notes:   # (no empty line under the button when there is nothing to say)
            self.note.pack(anchor="w", pady=(px(6), px(0)))
        else:
            self.note.pack_forget()

    def apply(self):
        folder = self.window.ready("switch the character")
        if not folder:
            return
        who = self.choice.get()
        name = "Link" if who == LINK else playas.CHARACTERS[who].label
        self.window.remember()
        self.run(folder, who, "Character: %s…" % name)

    def run(self, folder, who, line, again=False):
        """the switch on a worker thread (again: only if the mod that is on needs building again), the window busy
        meanwhile"""
        w = self.window
        w.busy = True
        w.generate_button.configure(state="disabled")
        self.apply_button.configure(state="disabled")
        self.progress.pack(side="right")
        self.progress.start(12)
        if line:
            w.log(line, "note")

        def work():
            try:
                if again:
                    playas.again(folder, log=w.log)
                else:
                    playas.install(folder, None if who == LINK else who, log=w.log)
                    w.log("Done: %s." % ("Link is Link again" if who == LINK else
                                         "put on the Goron or Zora tunic to be " + playas.CHARACTERS[who].who), "ok")
            except playas.Problem as e:
                w.log("Character not switched: %s" % e, "bad")
                w.call_soon(lambda: messagebox.showerror("Character", str(e)))
            except Exception:   # (shown, not swallowed)
                w.log("Character switch failed:\n" + traceback.format_exc(), "bad")
                w.call_soon(lambda: messagebox.showerror(
                    "Character", "The switch failed: the Generate page's log has the details."))
            w.queue.put(("done", None))   # (the window then calls finished())
        threading.Thread(target=work, daemon=True).start()

    def finished(self):
        self.progress.stop()
        self.progress.pack_forget()
        self.apply_button.configure(state="normal")
        self.shown_for = None   # (the choice shows what is installed now)
        self.refresh()
