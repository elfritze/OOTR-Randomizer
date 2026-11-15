"""The tracker page of the window: the installed seed's checks on the game's area maps, coloured by what logic reaches with
what Link holds (read from the game's save every few seconds), marked done by a click.

Each area's map is drawn from the game's own data: the map texture of the pause menu when the ASTC decoder
(texture2ddecoder) is installed, else the outline of the area's placed actors (paths, houses, trees). Checks sit at their
chest's, pickup's or giver's position in the world."""
import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import savefile, tracker
from .theme import C, STATE, px

STATE_LABEL = {"available": "In logic", "blocked": "Out of reach", "done": "Done", "unknown": "Unknown way in"}
MAJOR = ("RG_PROGRESSIVE_HOOKSHOT", "RG_PROGRESSIVE_BOW", "RG_PROGRESSIVE_SLINGSHOT", "RG_PROGRESSIVE_BOMB_BAG",
         "RG_BOOMERANG", "RG_MEGATON_HAMMER", "RG_LENS_OF_TRUTH", "RG_IRON_BOOTS", "RG_HOVER_BOOTS",
         "RG_PROGRESSIVE_STRENGTH", "RG_PROGRESSIVE_SCALE", "RG_MIRROR_SHIELD", "RG_ZORA_TUNIC", "RG_GORON_TUNIC",
         "RG_FIRE_ARROWS", "RG_ICE_ARROWS", "RG_LIGHT_ARROWS", "RG_DINS_FIRE", "RG_FARORES_WIND", "RG_NAYRUS_LOVE",
         "RG_PROGRESSIVE_MAGIC_METER", "RG_PROGRESSIVE_OCARINA", "RG_ZELDAS_LULLABY", "RG_EPONAS_SONG", "RG_SARIAS_SONG",
         "RG_SUNS_SONG", "RG_SONG_OF_TIME", "RG_SONG_OF_STORMS", "RG_MINUET_OF_FOREST", "RG_BOLERO_OF_FIRE",
         "RG_SERENADE_OF_WATER", "RG_NOCTURNE_OF_SHADOW", "RG_REQUIEM_OF_SPIRIT", "RG_PRELUDE_OF_LIGHT",
         "RG_KOKIRI_EMERALD", "RG_GORON_RUBY", "RG_ZORA_SAPPHIRE", "RG_FOREST_MEDALLION", "RG_FIRE_MEDALLION",
         "RG_WATER_MEDALLION", "RG_SPIRIT_MEDALLION", "RG_SHADOW_MEDALLION", "RG_LIGHT_MEDALLION")


def pretty(rg):
    words = rg[3:].replace("PROGRESSIVE_", "").replace("_", " ").title()
    return words.replace("Of ", "of ").replace("'S", "'s")


def item_label(actor):
    a = actor.replace("Item_Melody_", "Song: ").replace("Item_", "").replace("Obj_", "").replace("TBox_", "")
    return a.replace("_", " ")


class TrackerTab:
    def __init__(self, frame, window):
        self.frame, self.window = frame, window
        self.model = None
        self.model_folder = None
        self.marks = set()
        self.have = {}
        self.states = {}
        self.save_path = None
        self.save_stamp = None
        self.area = None
        self.age = tk.StringVar(value="Child")
        self.reveal = tk.BooleanVar(value=False)
        self.follow = tk.BooleanVar(value=True)
        self.loading = False
        self.taken = {}
        self.floor = tk.StringVar(value="")
        self.decoding = set()
        self.floor_of = {}
        self.markers = {}
        self._build()
        self._tick()

    # (layout)
    def _build(self):
        f = self.frame
        top = ttk.Frame(f)
        top.pack(fill="x")
        ttk.Label(top, text="Tracker", style="Page.TLabel").pack(side="left")
        self.summary = ttk.Label(top, text="", style="PageMuted.TLabel")
        self.summary.pack(side="left", padx=px(16), pady=(px(10), 0))
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=(px(4), px(10)))
        ttk.Checkbutton(bar, text=" Follow the newest save", variable=self.follow, style="SwitchDark.TCheckbutton",
                        command=self.reload).pack(side="left")
        ttk.Checkbutton(bar, text=" Show items", variable=self.reveal, style="SwitchDark.TCheckbutton",
                        command=self.redraw).pack(side="left", padx=px(14))
        for age in ("Child", "Adult"):
            ttk.Radiobutton(bar, text=age, value=age, variable=self.age, style="Seg.TRadiobutton",
                            command=self.redraw).pack(side="left", padx=(px(4), 0))
        ttk.Button(bar, text="⟳  Reload", style="Small.TButton", command=lambda: self.reload(force=True)).pack(side="right")
        self.save_label = ttk.Label(bar, text="", style="PageMuted.TLabel")
        self.save_label.pack(side="right", padx=px(10))

        body = ttk.Frame(f)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body, style="Card.TFrame", padding=(px(8), px(10), px(8), px(10)))
        left.grid(row=0, column=0, sticky="ns", padx=(0, px(10)))
        ttk.Label(left, text="Areas", style="CardHeading.TLabel").pack(anchor="w", padx=px(6))
        self.areas = ttk.Treeview(left, columns=("n",), show="tree", selectmode="browse", height=18)
        self.areas.column("#0", width=px(150))
        self.areas.column("n", width=px(52), anchor="e")
        self.areas.pack(fill="y", expand=True, pady=(px(6), 0))
        self.areas.bind("<<TreeviewSelect>>", self._pick_area)
        for st, colour in STATE.items():
            self.areas.tag_configure(st, foreground=colour)

        mid = ttk.Frame(body, style="Card.TFrame", padding=px(10))
        mid.grid(row=0, column=1, sticky="nsew")
        head = ttk.Frame(mid, style="CardBody.TFrame")
        head.pack(fill="x")
        self.area_title = ttk.Label(head, text="", style="CardHeading.TLabel")
        self.area_title.pack(side="left")
        self.floor_bar = ttk.Frame(head, style="CardBody.TFrame")
        self.floor_bar.pack(side="right")

        self.floor_names = None
        self.canvas = tk.Canvas(mid, background="#0e1828", highlightthickness=0, cursor="hand2")
        self.canvas.pack(fill="both", expand=True, pady=(px(6), 0))
        self.canvas.bind("<Configure>", lambda e: self.redraw())
        self.tip = None
        legend = ttk.Frame(mid, style="CardBody.TFrame")
        legend.pack(fill="x", pady=(px(6), 0))
        self.area_button = ttk.Button(legend, text="✓  Mark area done", style="Small.TButton", command=self.mark_area)
        self.area_button.pack(side="right")
        for st in ("available", "blocked", "done"):
            ttk.Label(legend, image=self.window.images["dot_" + st], style="Card.TLabel").pack(side="left")
            ttk.Label(legend, text=" %s   " % STATE_LABEL[st], style="CardMuted.TLabel").pack(side="left")
        self.map_note = ttk.Label(legend, text="", style="CardMuted.TLabel")
        self.map_note.pack(side="left", padx=px(10))

        right = ttk.Frame(body, style="Card.TFrame", padding=(px(8), px(10), px(8), px(10)))
        right.grid(row=0, column=2, sticky="ns", padx=(px(10), 0))
        ttk.Label(right, text="Checks", style="CardHeading.TLabel").pack(anchor="w", padx=px(6))
        self.list = ttk.Treeview(right, columns=("item",), show="tree", selectmode="browse", height=12)
        self.list.column("#0", width=px(175))
        self.list.column("item", width=px(95))
        self.list.pack(fill="both", expand=True, pady=(px(6), px(8)))
        self.list.bind("<Double-1>", self._toggle_from_list)
        for st, colour in STATE.items():
            self.list.tag_configure(st, foreground=colour)
        ttk.Label(right, text="Items", style="CardHeading.TLabel").pack(anchor="w", padx=px(6))
        self.items = tk.Text(right, height=9, width=1, wrap="word", background=C["card"], foreground=C["text"],
                             relief="flat", borderwidth=0, font=self.window.fonts.small, state="disabled")
        self.items.pack(fill="both", padx=px(6), pady=(px(4), 0))
        self.items.tag_configure("dim", foreground=C["faint"])
        self.status = ttk.Label(f, text="", style="PageMuted.TLabel")
        self.status.pack(anchor="w", pady=(px(6), 0))

    # (data)
    def reload(self, force=False):
        folder = self.window.folder.get().strip()
        if not folder or self.loading:
            return
        if force or self.model is None or self.model_folder != folder:
            self.loading = True
            self.status.configure(text="Loading the seed and the maps…")

            def work():
                try:
                    model = tracker.Model(folder, log=lambda *_: None)
                    err = None
                except Exception as e:   # (no seed installed, no game: shown, the page stays usable)
                    model, err = None, e
                if model is not None:
                    try:
                        from . import maptex
                        model.geo = maptex.geometry(model.romfs)
                    except Exception:   # (an unexpected romfs: the maps drawn from the placed objects)
                        model.geo = {}
                self.frame.after(0, lambda: self._loaded(folder, model, err))
            threading.Thread(target=work, daemon=True).start()
            return
        self.read_save(force=True)

    def _loaded(self, folder, model, err):
        self.loading = False
        if err is not None:
            self.model = None
            self.status.configure(text="No tracker: %s" % err)
            return
        self.model, self.model_folder = model, folder
        self.marks = tracker.load_marks(model.seed)
        self.floor_of = {}
        self.status.configure(text="Seed %s: %d checks. What your save shows taken is marked done by itself; double-click "
                                   "a check, or click its marker, to mark the others (chests of rupees, ammunition...)." % (
                                       model.seed, len(model.checks)))
        self.read_save(force=True)

    def read_save(self, force=False):
        if not self.model:
            return
        saves = savefile.find_saves(self.model_folder)
        path = saves[0][1] if saves else None
        if not self.follow.get() and self.save_path:
            path = self.save_path
        stamp = os.path.getmtime(path) if path and os.path.exists(path) else None
        if not force and (path, stamp) == (self.save_path, self.save_stamp):
            return
        self.save_path, self.save_stamp = path, stamp
        if path:
            try:
                save = savefile.read(path)
                self.have = self.model.inventory(save)
                self.taken = self.model.collected(save)
                child = save["bool"].get(savefile.murmur3("Sequence_IsChildhood"))
                if child is not None and force:
                    self.age.set("Child" if child else "Adult")
                slot = os.path.basename(os.path.dirname(path))
                self.save_label.configure(text="Save: %s" % slot.replace("slot_", "slot "))
            except (OSError, savefile.SaveError) as e:
                self.save_label.configure(text="Save unreadable (%s)" % e)
        else:
            self.have, self.taken = {}, {}
            self.save_label.configure(text="No save yet")
        self.states = self.model.states(self.have, self.marks, self.taken)
        self.refresh_lists()
        self.redraw()

    def _tick(self):
        if self.model and self.frame.winfo_ismapped():
            try:
                self.read_save()
            except Exception:   # (a save caught mid-write: the next tick reads it)
                pass
        self.frame.after(2500, self._tick)

    # (lists)
    def refresh_lists(self):
        m = self.model
        if not m:
            return
        counts = {}
        for c in m.checks:
            key = c.folder or "Other"
            done, avail, total = counts.get(key, (0, 0, 0))
            st = self.states.get(c.id)
            counts[key] = (done + (st == "done"), avail + (st == "available"), total + 1)
        sel = self.area
        self.areas.delete(*self.areas.get_children())
        order = [k for k in tracker.AREAS if k in counts] + [k for k in counts if k not in tracker.AREAS]
        for key in order:
            done, avail, total = counts[key]
            tag = "available" if avail else "done" if done == total else "blocked"
            name = tracker.AREAS.get(key, key)
            self.areas.insert("", "end", iid=key, text="  " + name, values=("%d / %d" % (avail, total - done),), tags=(tag,))
        if sel not in counts:
            sel = order[0] if order else None
        if sel:
            self.areas.selection_set(sel)
            self.areas.see(sel)
        total_avail = sum(1 for s in self.states.values() if s == "available")
        total_done = sum(1 for s in self.states.values() if s == "done")
        self.summary.configure(text="%d in logic  ·  %d done  ·  %d checks  ·  seed %s" % (
            total_avail, total_done, len(m.checks), m.seed))
        self.items.configure(state="normal")
        self.items.delete("1.0", "end")
        for rg in MAJOR:
            n = self.have.get(rg, 0)
            label = pretty(rg) + (" ×%d" % n if n > 1 else "")
            self.items.insert("end", ("✓ " if n else "· ") + label + "\n", () if n else ("dim",))
        self.items.configure(state="disabled")

    def _pick_area(self, _=None):
        sel = self.areas.selection()
        if sel and sel[0] != self.area:
            self.area = sel[0]
            self.floor.set("")   # (a dungeon opens on its floor with the most to do)
            self.redraw()

    def area_checks(self):
        return [c for c in self.model.checks if (c.folder or "Other") == self.area] if self.model else []

    def show_item(self, c):
        return self.reveal.get() or self.states.get(c.id) == "done"

    def fill_list(self):
        self.list.delete(*self.list.get_children())
        order = {"available": 0, "unknown": 1, "blocked": 2, "done": 3}
        for c in sorted(self.area_checks(), key=lambda c: (order.get(self.states.get(c.id), 9), c.name)):
            st = self.states.get(c.id, "blocked")
            name = c.name.split(": ", 1)[-1]
            self.list.insert("", "end", iid=c.id, text="  " + name,
                             values=(item_label(c.item) if self.show_item(c) else "",), tags=(st,))

    def _toggle_from_list(self, _=None):
        sel = self.list.selection()
        if sel:
            self.toggle(sel[0])

    def mark_area(self):
        """every check of the area marked done (chests of rupees or ammunition leave no trace in the save), or, when all
        are, the player's own marks of the area taken back"""
        if not self.model or not self.area:
            return
        name = tracker.AREAS.get(self.area, self.area)
        ids = [c.id for c in self.area_checks() if c.id not in self.taken]
        if ids and all(i in self.marks for i in ids):
            if not messagebox.askyesno("Tracker", "Take back your marks in %s (%d checks)? What the save shows taken "
                                       "stays done." % (name, len(ids)), parent=self.frame):
                return
            self.marks -= set(ids)
        else:
            left = [i for i in ids if i not in self.marks]
            if not left or not messagebox.askyesno("Tracker", "Mark the %d check%s of %s not yet done as done?" % (
                    len(left), "" if len(left) == 1 else "s", name), parent=self.frame):
                return
            self.marks |= set(left)
        tracker.save_marks(self.model.seed, self.marks)
        self.states = self.model.states(self.have, self.marks, self.taken)
        self.refresh_lists()
        self.redraw()

    def toggle(self, cid):
        if cid in self.taken:
            self.status.configure(text="Your save shows that check taken (%s): it stays done." % self.taken[cid])
            return
        if cid in self.marks:
            self.marks.discard(cid)
        else:
            self.marks.add(cid)
        tracker.save_marks(self.model.seed, self.marks)
        self.states = self.model.states(self.have, self.marks, self.taken)
        self.refresh_lists()
        self.redraw()

    # (the map)
    def _sheets(self):
        """(the sheet shown, the dungeon's floors or None): the pause menu's map of the area at this age, or of the floor
        picked; (None, None) when the game has no map for it"""
        geo = getattr(self.model, "geo", None) or {}
        floors = geo.get("dungeons", {}).get(self.area)
        if floors:
            if self.floor.get() not in [f.name for f in floors]:
                self.floor.set(self._best_floor(floors))   # ("" until the floors are decoded)
            return next((f for f in floors if f.name == self.floor.get()), floors[0]), floors
        ages = geo.get("fields", {}).get(self.area) or {}
        age = self.age.get()
        return ages.get(age) or ages.get("Adult" if age == "Child" else "Child"), None

    def _ready(self, sheets):
        """whether these maps are decoded; if not, decode them in the background (seconds each, once) and redraw"""
        todo = [s for s in sheets if s._image is None]
        if not todo:
            return True
        key = tuple(s.rel for s in todo)
        if key not in self.decoding:
            self.decoding.add(key)

            def work():
                for s in todo:
                    try:
                        s.image()
                    except Exception:   # (no decoder, an unexpected texture: the outline is drawn instead)
                        s.failed = True
                self.frame.after(0, lambda: self._decoded(key))
            threading.Thread(target=work, daemon=True).start()
        return False

    def _decoded(self, key):
        self.decoding.discard(key)
        self.redraw()

    def _floor(self, c, floors):
        if c.id not in self.floor_of:
            from . import maptex
            f = maptex.floor_of(floors, c.pos[0], c.y, c.pos[1]) if c.pos else None
            self.floor_of[c.id] = f.name if f else None
        return self.floor_of[c.id]

    def _best_floor(self, floors):
        """the floor with the most checks in logic, else the most checks left, else the lowest"""
        if not all(f._image is not None for f in floors):
            return ""
        score = {f.name: [0, 0] for f in floors}
        for c in self.area_checks():
            name = self._floor(c, floors)
            if name in score:
                score[name][0] += self.states.get(c.id) == "available"
                score[name][1] += self.states.get(c.id) != "done"
        return max(floors, key=lambda f: tuple(score[f.name])).name

    def _floor_buttons(self, floors):
        names = [f.name for f in floors] if floors else []
        if names == self.floor_names:
            return
        self.floor_names = names
        for w in self.floor_bar.winfo_children():
            w.destroy()
        for name in reversed(names):   # (the highest floor first, as the game lists them)
            ttk.Radiobutton(self.floor_bar, text=name, value=name, variable=self.floor, style="SegCard.TRadiobutton",
                            command=self.redraw).pack(side="left", padx=(px(4), 0))

    def redraw(self):
        cv = self.canvas
        cv.delete("all")
        self.markers = {}
        if not self.model or not self.area:
            return
        name = tracker.AREAS.get(self.area, self.area)
        self.area_title.configure(text=name)
        self.fill_list()
        w, h = max(cv.winfo_width(), 50), max(cv.winfo_height(), 50)
        sheet, floors = self._sheets()
        self._floor_buttons(floors)
        failed = any(getattr(s, "failed", False) for s in (floors or [sheet] if sheet else []))
        if sheet is not None and not failed:
            if self._ready(floors or [sheet]):
                if floors and self.floor.get() != sheet.name:
                    sheet, _ = self._sheets()   # (the floors just decoded: the floor with the most to do)
                return self._draw_sheet(sheet, floors, w, h)
            self.map_note.configure(text="(reading the game's map, once…)")
        self._draw_outline(w, h)

    def _draw_sheet(self, sheet, floors, w, h):
        cv, age = self.canvas, self.age.get()
        img = sheet.image()
        here, other_age, tray = [], [], []
        for c in self.area_checks():
            if not c.pos:
                tray.append(c)
            elif floors:
                fl = self._floor(c, floors)
                if fl is None:
                    tray.append(c)
                elif fl == sheet.name:
                    here.append(c)
            elif not img.opaque(*sheet.to_tex(*c.pos)):
                tray.append(c)   # (inside a house or a grotto: the remake builds them away from the drawn map)
            elif c.age in (age, "All", None):
                here.append(c)
            else:
                other_age.append(c)
        tray_h = self._tray_height(tray, w)
        mh = max(50, h - tray_h)
        # (the drawn part of the map and every marker on it, with a margin)
        x0, y0, x1, y1 = img.bbox
        for c in here + other_age:
            u, v = sheet.to_tex(*c.pos)
            x0, y0, x1, y1 = min(x0, u), min(y0, v), max(x1, u), max(y1, v)
        m = 0.04 * max(x1 - x0, y1 - y0)
        x0, y0 = max(0, x0 - m), max(0, y0 - m)
        x1, y1 = min(img.size[0], x1 + m), min(img.size[1], y1 + m)
        k = min(w / (x1 - x0), mh / (y1 - y0))
        ox, oy = (w - (x1 - x0) * k) / 2, (mh - (y1 - y0) * k) / 2
        self._tex_ref = img.scaled((x0, y0, x1, y1), (x1 - x0) * k, (y1 - y0) * k)
        cv.create_image(ox, oy, image=self._tex_ref, anchor="nw")
        self.map_note.configure(text="(game map%s)" % (", " + sheet.name if floors else ""))

        def to(x, z):
            u, v = sheet.to_tex(x, z)
            return ox + (u - x0) * k, oy + (v - y0) * k

        self._draw_markers(here, other_age, to)
        self._draw_tray(tray, w, h, tray_h)

    def _draw_outline(self, w, h):
        """the area drawn from its placed objects (no map texture: no decoder, or an area the pause menu has no map of)"""
        cv, age = self.canvas, self.age.get()
        idx = self.model.index
        pts = idx["outline"].get("%s/%s" % (self.area, age)) or idx["outline"].get("%s/All" % self.area) or \
            idx["outline"].get("%s/%s" % (self.area, "Adult" if age == "Child" else "Child")) or []
        checks = [c for c in self.area_checks() if c.pos and c.age in (age, "All", None)]
        others = [c for c in self.area_checks() if c.pos and c not in checks]
        tray = [c for c in self.area_checks() if not c.pos]
        if not self.decoding:
            self.map_note.configure(text="(drawn from the area's objects)")
        tray_h = self._tray_height(tray, w)
        if not pts and not checks and not others:
            self._draw_tray(tray, w, h, tray_h)
            if not tray:
                cv.create_text(w / 2, h / 2, text="No map for this area", fill=C["muted"], font=self.window.fonts.body)
            return
        mh = max(50, h - tray_h)
        # (the area's own extent: its objects without the farthest 2% (a stray far actor), and every check)
        xs = sorted(p[0] for p in pts)
        zs_ = sorted(p[1] for p in pts)
        cut = len(xs) // 50
        if xs:
            xs, zs_ = xs[cut:len(xs) - cut] or xs, zs_[cut:len(zs_) - cut] or zs_
        xs += [c.pos[0] for c in checks + others]
        zs_ += [c.pos[1] for c in checks + others]
        x0, x1, z0, z1 = min(xs), max(xs), min(zs_), max(zs_)
        dx, dz = (x1 - x0) or 1, (z1 - z0) or 1
        x0, x1, z0, z1 = x0 - dx * 0.04, x1 + dx * 0.04, z0 - dz * 0.04, z1 + dz * 0.04
        s = min(w / (x1 - x0), mh / (z1 - z0))
        ox, oy = (w - (x1 - x0) * s) / 2, (mh - (z1 - z0) * s) / 2

        def to(x, z):
            return ox + (x - x0) * s, oy + (z - z0) * s

        dot = max(1.5, px(1.6))
        for x, z in pts:
            cx, cy = to(x, z)
            cv.create_rectangle(cx, cy, cx + dot, cy + dot, fill="#35507a", outline="")
        self._draw_markers(checks, others, to)
        self._draw_tray(tray, w, h, tray_h)

    def _draw_markers(self, checks, others, to):
        import math
        cv, r = self.canvas, px(7)
        for c in others:   # (the other age's checks: a faint ring)
            cx, cy = to(*c.pos)
            cv.create_oval(cx - r * 0.6, cy - r * 0.6, cx + r * 0.6, cy + r * 0.6, outline=C["faint"], width=1)
        # (checks at one spot (Mido's four chests, the House of Skulltula's five rewards) fan out in a ring, each clickable)
        spots = []   # ([x, y, n], [checks]): markers closer than a marker's width share one ring
        for c in checks:
            p = to(*c.pos)
            for centre, group in spots:
                if math.hypot(p[0] - centre[0] / centre[2], p[1] - centre[1] / centre[2]) < r * 1.8:
                    centre[0] += p[0]
                    centre[1] += p[1]
                    centre[2] += 1
                    group.append(c)
                    break
            else:
                spots.append(([p[0], p[1], 1], [c]))
        place = {}
        for _, group in spots:
            if len(group) == 1:
                place[group[0].id] = to(*group[0].pos)
                continue
            gx = sum(to(*c.pos)[0] for c in group) / len(group)
            gy = sum(to(*c.pos)[1] for c in group) / len(group)
            ring = r * 1.25 / math.sin(math.pi / len(group))
            for i, c in enumerate(sorted(group, key=lambda c: c.name)):
                a = 2 * math.pi * i / len(group) - math.pi / 2
                place[c.id] = (gx + ring * math.cos(a), gy + ring * math.sin(a))
        for c in sorted(checks, key=lambda c: {"done": 0, "blocked": 1, "unknown": 2, "available": 3}.get(
                self.states.get(c.id), 0)):
            self._marker(c, *place[c.id])

    def _marker(self, c, cx, cy):
        cv, r = self.canvas, px(7)
        st = self.states.get(c.id, "blocked")
        colour = STATE.get(st, C["muted"])
        if st == "available":
            cv.create_oval(cx - r - px(4), cy - r - px(4), cx + r + px(4), cy + r + px(4), outline=colour, width=1)
        tag = "m_" + c.id
        cv.create_oval(cx - r, cy - r, cx + r, cy + r, fill=colour, outline="#0b1220", width=2, tags=(tag,))
        if c.kind == "gift":
            cv.create_text(cx, cy, text="!", fill="#0b1220", font=self.window.fonts.strong, tags=(tag,))
        elif c.kind == "loose":
            cv.create_text(cx, cy, text="✦", fill="#0b1220", font=self.window.fonts.small, tags=(tag,))
        elif c.kind == "shop":
            cv.create_text(cx, cy, text="$", fill="#0b1220", font=self.window.fonts.small, tags=(tag,))
        cv.tag_bind(tag, "<Enter>", lambda e, c=c: self._show_tip(e, c))
        cv.tag_bind(tag, "<Leave>", lambda e: self._hide_tip())
        cv.tag_bind(tag, "<Button-1>", lambda e, c=c: self.toggle(c.id))
        self.markers[c.id] = (cx, cy)

    def _tray_height(self, tray, w):
        if not tray:
            return 0
        per_row = max(1, int((w - px(20)) // px(26)))
        return px(34) + px(26) * (-(-len(tray) // per_row))

    def _draw_tray(self, tray, w, h, tray_h):
        """the checks with no place on this map (inside a building, a grotto, a cutscene): a row under it"""
        if not tray:
            return
        cv = self.canvas
        top = h - tray_h
        cv.create_line(px(10), top + px(4), w - px(10), top + px(4), fill=C["line"])
        cv.create_text(px(10), top + px(16), anchor="w", fill=C["muted"], font=self.window.fonts.small,
                       text="Not on this map (inside a building, a grotto, a cutscene): hover for its name")
        per_row = max(1, int((w - px(20)) // px(26)))
        order = {"available": 0, "unknown": 1, "blocked": 2, "done": 3}
        for i, c in enumerate(sorted(tray, key=lambda c: (order.get(self.states.get(c.id), 9), c.name))):
            row, col = divmod(i, per_row)
            self._marker(c, px(23) + col * px(26), top + px(43) + row * px(26))

    def _show_tip(self, event, c):
        self._hide_tip()
        st = self.states.get(c.id, "blocked")
        text = "%s\n%s" % (c.name, STATE_LABEL.get(st, st))
        if c.id in self.taken:
            text += " (your save: %s)" % self.taken[c.id]
        if self.show_item(c):
            text += "  ·  " + item_label(c.item)
        if c.id not in self.taken:
            text += "\nclick: mark %s" % ("not done" if st == "done" else "done")
        x, y = event.x + px(14), event.y + px(10)
        t = self.canvas.create_text(x + px(8), y + px(6), text=text, anchor="nw", fill=C["text"],
                                    font=self.window.fonts.small)
        bx = self.canvas.bbox(t)
        # (kept inside the canvas: a marker at the right or bottom edge shows its tip on the other side)
        dx = min(0, self.canvas.winfo_width() - px(10) - bx[2])
        dy = 0 if bx[3] + px(10) <= self.canvas.winfo_height() else -(bx[3] - bx[1]) - px(36)
        if dx < 0 and bx[0] + dx < px(10):
            dx = px(10) - bx[0]
        self.canvas.move(t, dx, dy)
        bx = self.canvas.bbox(t)
        bg = self.canvas.create_rectangle(bx[0] - px(8), bx[1] - px(6), bx[2] + px(8), bx[3] + px(6), fill=C["card2"],
                                          outline=C["gold"])
        self.canvas.tag_raise(t, bg)
        self.tip = (t, bg)

    def _hide_tip(self):
        if self.tip:
            for i in self.tip:
                self.canvas.delete(i)
            self.tip = None

    def close(self):
        pass
