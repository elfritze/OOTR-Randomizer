"""A seed: the chests, the NPCs' gifts and the items lying in the world filled (rando.fill) by the logic (rando.logic: SoH's,
with the remake's changes from data/locations.json and data/gifts.json), written as a RomFS mod, with its spoiler log."""
import collections
import hashlib
import json
import os
import random
import shutil

from . import chests, dungeon_items, fill, gifts, hints, patches, pickups, shops
from . import items as I
from .formats import sarc, zs
from .logic import soh_regions as R
from .logic.search import World, item_info, vanilla_items
from .mod import Mod

HERE = os.path.dirname(os.path.abspath(__file__))
LOCATIONS = os.path.join(HERE, "..", "data", "locations.json")
GIFTS = os.path.join(HERE, "..", "data", "gifts.json")
SKULLTULAS = os.path.join(HERE, "..", "data", "skulltulas.json")
TOKEN = "Item_Token_Gold"
FIRE_ARROWS = "Item_Arrow_Fire"
MOD_NAME = "HookshotRando"


def load_table(path=LOCATIONS):
    """data/locations.json: every randomized chest (by placement Hash) with its SoH check (or none: a remake-only chest, with
    its region and rule), the SoH checks the remake does not have, and the remake's changes to SoH's rules"""
    with open(path, encoding="utf-8") as f:
        t = json.load(f)
    seen_rc = collections.Counter(l["rc"] for l in t["locations"] if l["rc"])
    dup = [rc for rc, n in seen_rc.items() if n > 1]
    if dup:
        raise ValueError("checks used twice: %s" % dup)
    return t


def load_gifts(path=GIFTS):
    """data/gifts.json: every randomized NPC gift (the event parameters naming what it gives) and item lying in the world (its
    map actors), with its SoH check (or none: a remake-only one) and the remake's rule where it differs"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_skulltulas(path=SKULLTULAS):
    """data/skulltulas.json: each of the remake's 100 Gold Skulltulas (by Hash, its map folder) with its SoH check, and
    its rule where the remake's place differs"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)["skulltulas"]


def soh_rule(key):
    """SoH's C++ text of the rule an override key names (exit, event or location)"""
    kind, rr = key[0], key[1]
    r = R.REGIONS.get(rr)
    if r is None:
        raise ValueError("override %s: no region %s" % (key, rr))
    entries = {"exit": r["exits"], "event": r["events"], "location": r["locations"]}[kind]
    hits = [cpp for name, (_, cpp, _) in entries if name == key[2]]
    if len(hits) != 1:
        raise ValueError("override %s: %d such rules in SoH" % (key, len(hits)))
    return hits[0]


def _entries(table, gift_table, skulltulas=()):
    """chests, gifts and Gold Skulltulas alike: {"id", "rc", "region", "condition"}"""
    out = [{"id": l["id"], "rc": l["rc"], "region": l["region"], "condition": l.get("condition")} for l in table["locations"]]
    if gift_table:
        out += [{"id": c["id"], "rc": c["rc"], "region": c["soh_region"], "condition": c.get("rule")}
                for c in gift_table["checks"]]
    out += [{"id": s["rc"], "rc": s["rc"], "region": s.get("region"), "condition": s.get("rule")} for s in skulltulas]
    return out


# The castle moat (Zelda's escape: the Ocarina of Time, the Song of Time): SoH's rule, and Zelda met, as the remake's escape
# (the DoorOfTime quest) waits for the castle garden and Impa's send-off (OotrR's remake layer, Song from Ocarina of Time)
MOAT_CHECKS = ("RC_HF_OCARINA_OF_TIME_ITEM", "RC_SONG_FROM_OCARINA_OF_TIME")
MOAT_RULE = "logic->IsChild && logic->StoneCount() == 3 && logic->HasItem(RG_BRONZE_SCALE) && logic->Get(LOGIC_MET_ZELDA)"


def make_world(table, gift_table=None, options=None, skulltulas=(), more=None):
    entries = _entries(table, gift_table, skulltulas)
    seen = collections.Counter(e["rc"] for e in entries if e["rc"])
    if any(n > 1 for n in seen.values()):
        raise ValueError("checks both a chest and a gift: %s" % [rc for rc, n in seen.items() if n > 1])
    extra = {}
    for e in entries:
        if not e["rc"]:
            extra[e["id"]] = (e["region"], e["condition"])
    overrides = {}
    soh_regions = {}   # (RC: SoH's regions holding it)
    for rr, r in R.REGIONS.items():
        for rc, _ in r["locations"]:
            soh_regions.setdefault(rc, set()).add(rr)
    for e in entries:
        if not e["rc"]:
            continue
        if e.get("condition"):
            overrides[("location", e["rc"])] = e["condition"]
        regs = soh_regions.get(e["rc"], set())
        # (the check's region when the remake moved it, or when its rule is replaced and SoH has it in several regions
        #  (one rule needs one region). A check SoH reaches from several regions with their own rules, as the Forest
        #  Temple's well chest (underwater, or dry in the drained well), keeps them all otherwise)
        if e["region"] and (e["region"] not in regs or (e.get("condition") and len(regs) > 1)):
            overrides[("location_region", e["rc"])] = e["region"]
    for o in table.get("overrides", []):
        key = tuple(o["key"])
        if "region" in o:
            overrides[key] = o["region"]
        elif "sub" in o:
            old, new = o["sub"]
            text = soh_rule(key)
            if text.count(old) != 1:
                raise ValueError("override %s: %r is %d times in SoH's rule %r" % (key, old, text.count(old), text))
            overrides[key] = text.replace(old, new)
        else:
            overrides[key] = o["rule"]
    overrides.update(more or {})
    return World(extra_locations=extra, rule_overrides=overrides, removed_locations=tuple(table.get("removed", ())),
                 options=options)


def seed_number(seed):
    return int.from_bytes(hashlib.sha256(str(seed).encode("utf-8")).digest()[:8], "little")


SCAN_CACHE_VERSION = 1


def _scan_stamp(romfs):
    """what the chests' and shops' scans read, as sizes and times: the cache is only used while these are the same"""
    parts = []
    shop_packs = [shops.pack_path(s) for s in ("Npc_Kokiri_001_Shop_Child", "Npc_Goron_011_Shop_Child")]
    for rel in chests.map_files(romfs) + [pickups.POUCH_ACTOR_INFO] + shop_packs:
        st = os.stat(os.path.join(romfs, *rel.split("/")))
        parts.append("%s %d %d" % (rel, st.st_size, st.st_mtime_ns))
    text = "\n".join(["%d" % SCAN_CACHE_VERSION] + parts)
    return hashlib.sha256(text.encode()).hexdigest()[:20]


def scan_game(romfs, codec, cache_dir=None):
    """(chests.scan, shops.scan) of the game; with cache_dir, kept there as JSON and read back while the game's files
    are the same (the tracker opens in a second instead of reading every map again: about 4 s)"""
    path = os.path.join(cache_dir, "scan-%s.json" % _scan_stamp(romfs)) if cache_dir else None
    if path and os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            found = {int(h): c for h, c in data["chests"].items()}
            return found, [shops.Slot(**dict(s, copies=[tuple(c) for c in s["copies"]])) for s in data["shops"]]
        except (OSError, ValueError, KeyError, TypeError):
            pass
    found, slots = chests.scan(romfs, codec), shops.scan(romfs, codec)
    if path:
        try:
            os.makedirs(cache_dir, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"chests": {str(h): c for h, c in found.items()}, "shops": [vars(s) for s in slots]}, f)
        except OSError:
            pass
    return found, slots


class Setup:
    """everything a seed is made from: the tables, the chests found in this game, the locations, the logic"""

    def __init__(self, romfs, codec, with_gifts=True, songs=True, settings=None, cache_dir=None):
        self.settings = settings
        scanned_chests, scanned_shops = scan_game(romfs, codec, cache_dir)
        """settings (rando.settings, normalized): which checks are shuffled; songs: as settings' shuffle_songs (older
        callers). A check not shuffled leaves the fill and keeps the game's item, which logic counts where it is (fixed)."""
        if settings is not None:
            songs = settings["shuffle_songs"]
        self.places = fill.places_of(settings)
        self.table = load_table()
        self.gifts = load_gifts() if with_gifts else {"checks": [], "excluded": []}

        def kept(c):
            if c.get("lake_sun"):
                return settings is not None and settings.get("shuffle_lake_fire_arrows", False)
            if c.get("ocarina_of_time"):
                return settings is not None and settings.get("shuffle_ocarina_of_time", False)
            if c.get("ocarina"):
                return settings is not None and settings["shuffle_fairy_ocarina"]
            if c.get("quest"):
                return settings is not None and settings["shuffle_quest_items"]
            if c.get("great_fairy"):
                return settings is not None and settings["shuffle_great_fairies"]
            if c.get("reward"):   # (the dungeon rewards: shuffled among themselves, or where the game gives them)
                return settings is not None and settings["shuffle_dungeon_rewards"] == "end_of_dungeon"
            if c["vanilla"].startswith("Item_Melody_"):
                return songs   # (the songs where the game teaches them, as SoH's "song locations" off)
            if settings is None:
                return True
            return settings["shuffle_freestanding"] if c["kind"] == "loose" else settings["shuffle_gifts"]
        self.gifts = {"checks": [c for c in self.gifts["checks"] if kept(c)], "excluded": self.gifts["excluded"]}
        self.found = scanned_chests
        locs = []
        for l in self.table["locations"]:
            h = int(l["hash"])
            if h not in self.found:
                raise ValueError("chest %s (%s) is not in this game's maps" % (l["hash"], l["name"]))
            if self.found[h]["drop"] != l["vanilla"]:
                raise ValueError("chest %s holds %s, the table says %s" % (l["hash"], self.found[h]["drop"], l["vanilla"]))
            locs.append(fill.Location(l["id"], h, self.found[h]["map"], l["vanilla"], "%s: %s" % (l["area"], l["name"]),
                                      small_chest=self.found[h]["gyaml"] in chests.SMALL_FLOW))
        covered = {x.hash for x in locs} | {int(c) for l in self.table["locations"] for c in l["copies"]} | \
            {int(h) for h in self.table.get("skipped", ())}
        missing = [h for h in self.found if h not in covered]
        if missing:
            raise ValueError("chests not in data/locations.json: %s" % missing[:5])
        for c in self.gifts["checks"]:
            remake_map = c["loose"][0]["map"].split("/")[1] if c["kind"] == "loose" else None
            locs.append(fill.Location(c["id"], None, remake_map, I.canonical(c["vanilla"]), "%s: %s" % (c["area"], c["name"]),
                                      kind=c["kind"]))
        # (the Gold Skulltulas, with settings shuffle_tokens: each drops the item placed there)
        self.skulltulas = load_skulltulas() if settings is not None and settings.get("shuffle_tokens") else []
        for g in self.skulltulas:
            locs.append(fill.Location(g["rc"], int(g["hash"]), g["folder"], TOKEN, "%s: Gold Skulltula (%s)" % (
                g["area"], g["rc"].split("_GS", 1)[1].strip("_").replace("_", " ").title() or "the area's"),
                kind="skulltula"))
        self.locs = locs
        self.options = fill.soh_options(self.places)   # (for hints: fill.soh_options says why not for logic)
        # (the Ocarina of Time shuffled: the moat's two checks need an ocarina first, its lesson having Link play along)
        more = {("location", rc): MOAT_RULE + " && logic->HasItem(RG_FAIRY_OCARINA)" for rc in MOAT_CHECKS} \
            if settings is not None and settings.get("shuffle_ocarina_of_time") else {}
        self.world = make_world(self.table, self.gifts, skulltulas=self.skulltulas, more=more)
        mapped = {e["rc"] for e in _entries(self.table, self.gifts, self.skulltulas) if e["rc"]}
        removed = set(self.table.get("removed", ()))
        self.fixed = {rc: rg for rc, rg in vanilla_items().items()
                      if rc not in mapped and rc not in removed and rc in self.world.location_ids}
        # (the shops: each of SoH's 64 shop checks is a remake shelf, what it sells as logic counts it, at the remake's price
        #  (rando.shops); some become checks with settings shuffle_shops, chosen with each fill's draw)
        self.shop_slots = scanned_shops
        self.shop_by_rc = {slot.rc: slot for slot in self.shop_slots}
        for slot in self.shop_slots:
            self.fixed[slot.rc] = slot.rg
            self.world.prices[slot.rc] = shops.logic_price(slot.price)
        self.shop_prices = {}
        self.progression = {rg for rg, info in item_info().items() if info.get("progression")}
        self.closed = closed_locations(self.world, self.locs, self.progression, self.fixed)
        # (a chest only the remake has whose way in the research could not establish (confidence "low") gets junk only, as
        #  logic not reaching it does: the Lost Woods' under-bridge chest, given a rule needing nothing, could not be found
        #  a way up to in game (2026-11-13), and a seed had put the only way out of the forest in it)
        self.closed |= {l["id"] for l in self.table["locations"] if not l["rc"] and l.get("confidence") == "low"}
        # (a Gold Skulltula whose match or way in is not sure (data/skulltulas.json "closed"): junk only too)
        self.closed |= {g["rc"] for g in self.skulltulas if g.get("closed")}
        self.base = (list(self.locs), dict(self.fixed), set(self.closed))
        if settings is not None and settings.get("shuffle_shops", "off") != "off":
            every = [fill.Location(slot.rc, None, slot.folder, shops.JUNK[0], slot.name, kind="shop")
                     for slot in self.shop_slots]
            self.shop_closed = closed_locations(self.world, every, self.progression,
                                                {k: v for k, v in self.fixed.items() if k not in self.shop_by_rc})

    def choose_shops(self, rng):
        """the shelves shuffled this time (settings shuffle_shops: that many per shop, in SoH's order, or a random number)
        and their prices: the locations, the checks left as they are, the prices logic counts"""
        self.locs, self.fixed, self.closed = list(self.base[0]), dict(self.base[1]), set(self.base[2])
        self.shop_prices = {}
        for slot in self.shop_slots:
            self.world.prices[slot.rc] = shops.logic_price(slot.price)
        choice = (self.settings or {}).get("shuffle_shops", "off")
        if choice == "off":
            return
        n = 0
        for code, *_ in shops.SHOPS:
            count = shops.count_for(choice, rng)
            for slot in sorted((s for s in self.shop_slots if s.code == code), key=lambda s: s.order)[:count]:
                price = shops.price_for(slot, self.settings["shop_prices"], rng)
                self.shop_prices[slot.rc] = price
                self.world.prices[slot.rc] = shops.logic_price(price)
                del self.fixed[slot.rc]
                self.locs.append(fill.Location(slot.rc, None, slot.folder, shops.JUNK[n % len(shops.JUNK)], slot.name,
                                               kind="shop"))
                if slot.rc in self.shop_closed:
                    self.closed.add(slot.rc)
                n += 1

    def apply_shops(self, chosen):
        """a seed's shelves as its placements.json lists them ({RC: {"price"...}}): for the tracker and tools"""
        self.locs, self.fixed, self.closed = list(self.base[0]), dict(self.base[1]), set(self.base[2])
        self.shop_prices = {}
        for slot in self.shop_slots:
            self.world.prices[slot.rc] = shops.logic_price(slot.price)
        for rc, v in sorted(chosen.items()):
            slot = self.shop_by_rc[rc]
            self.shop_prices[rc] = v["price"]
            self.world.prices[rc] = shops.logic_price(v["price"])
            self.fixed.pop(rc, None)
            self.locs.append(fill.Location(rc, None, slot.folder, shops.JUNK[0], slot.name, kind="shop"))

    def fill(self, rng):
        self.choose_shops(rng)
        return fill.fill(self.world, self.locs, self.fixed, self.progression, rng, self.closed, places=self.places)


def generate(romfs, mods_dir, seed, settings, log=print):
    from . import qol, settings as rando_settings
    settings = rando_settings.normalized(settings)
    codec = zs.Codec(romfs)
    s = Setup(romfs, codec, settings=settings)
    rng = random.Random(seed_number(seed))
    placed = s.fill(rng)
    placed = assign_tiers(s, placed, rng)

    out = os.path.join(mods_dir, MOD_NAME)
    archived = archive_installed(mods_dir)
    if archived:
        log("the seed installed before is kept in %s" % archived)
    if os.path.isdir(os.path.join(out, "romfs")):   # (the last seed's files go: one it changed and this one does not
        shutil.rmtree(os.path.join(out, "romfs"))  #  would stay as the last seed had it)
    mod = Mod(romfs, codec, os.path.join(out, "romfs"))
    by_id = {l.id: l for l in s.locs}
    copies = {l["id"]: [int(c) for c in l["copies"]] for l in s.table["locations"]}
    made = pickups.Pickups(romfs, codec, mod)
    own_items = dungeon_items.Builder(romfs, codec, mod, made)
    contents = {}
    for lid, actor in placed.items():
        if by_id[lid].kind != "chest":
            continue
        for h in [by_id[lid].hash] + copies[lid]:   # (a chest placed twice gets the same item in each copy)
            written = I.dungeon_form(actor, s.found[h]["map"], s.found[h]["gyaml"] in chests.SMALL_FLOW)
            if written != actor or I.dungeon_item(actor) is None:
                contents[h] = (written, chests.event_for(s.found[h], written))
            else:   # (a dungeon's own item, out of the game's one's reach)
                own = own_items.actor(*I.dungeon_item(actor))
                contents[h] = (own, chests.event_for(s.found[h], own))
    chests.write(romfs, codec, mod, contents)
    gift_by_id = {c["id"]: c for c in s.gifts["checks"]}
    given, loose = {}, {}
    for lid, actor in placed.items():
        kind = by_id[lid].kind
        if kind == "gift":
            given[lid] = I.form(actor, "gift")
        elif kind == "loose":
            if lid == I.LAKE_SUN and actor == FIRE_ARROWS:   # (the arrows where they are: nothing changes)
                continue
            new = I.loose_form(actor, by_id[lid].map)
            if I.dungeon_item(new):   # (a dungeon's own item: its pack and rows first, the pickup made of it)
                new = own_items.actor(*I.dungeon_item(new))
            for a in gift_by_id[lid]["loose"]:
                if new != a.get("gyaml"):   # (an item left where it was stays as the game has it)
                    loose[int(a["hash"])] = new
    gifts.write(romfs, codec, mod, [(gift_by_id[lid], actor) for lid, actor in given.items()])
    patches.great_fairies_once(romfs, codec, mod, [lid for lid in given if lid in patches.GREAT_FAIRIES])
    patches.fairies_any_order(romfs, codec, mod)
    if SARIA in given or OCARINA_OF_TIME in given:   # (an ocarina found elsewhere made playable; before the own items' hook)
        patches.ocarina_guide_on_get(mod)
    if loose:
        pickups.place(romfs, codec, mod, loose, made)
    if I.LAKE_SUN in placed and placed[I.LAKE_SUN] != FIRE_ARROWS:   # (the sun's scene and the arrows' quest: the pickup)
        patches.lake_sun(romfs, codec, mod, pickups.name_for(placed[I.LAKE_SUN]))
    drops = {}   # (the Gold Skulltulas: a token left as it is; any other item, a pickup built on the token)
    for lid, actor in placed.items():
        if by_id[lid].kind == "skulltula" and actor != TOKEN:
            item = own_items.actor(*I.dungeon_item(actor)) if I.dungeon_item(actor) else actor
            drops[by_id[lid].hash] = made.actor_for(item, drop=True)
    if drops:
        pickups.set_drops(romfs, codec, mod, drops)
    shelves = []   # (the shops' shuffled shelves: a new shelf actor each, rando.shops)
    shop_builder = None
    for lid, actor in sorted(placed.items()):
        if by_id[lid].kind != "shop":
            continue
        shop_builder = shop_builder or shops.Builder(romfs, codec, mod, made)
        slot = s.shop_by_rc[lid]
        shelves.append((slot, shop_builder.shelf(slot, I.form(actor, "shop"), s.shop_prices[lid])))
    if shelves:
        shops.write(romfs, codec, mod, shelves)
    own_items.finish()   # (their names, rows, flags and the hook: before the tables are written)
    if shop_builder:
        shop_builder.finish()   # (the shelves' saved flags)
    made.finish()
    patches.song_models(romfs, codec, mod)
    patches.free_bomb_lift(romfs, codec, mod)
    patches.dc_bombs_set_off_flower(romfs, codec, mod)
    patches.open_zr_river(romfs, codec, mod)
    patches.mido_keeps_blocking(romfs, codec, mod)
    patches.kokiri_007_keeps_blocking(romfs, codec, mod)
    patches.second_malon_after_talon(romfs, codec, mod)
    patches.starting_bags(romfs, codec, mod)
    patches.clock_runs(romfs, codec, mod)
    patches.zora_arrival_after_letter(romfs, codec, mod)
    patches.darunia_bracelet_after_quest(romfs, codec, mod, given.get(DARUNIA, patches.BRACELET))
    patches.free_time_travel(romfs, codec, mod)
    if settings["skip_intro"]:
        patches.skip_intro(romfs, codec, mod)
    if settings["fast_chests"]:
        qol.fast_chests(romfs, codec, mod)
    if settings["skip_auto_dialogues"]:
        qol.skippable_auto_dialogues(romfs, codec, mod)
    if settings["skip_title_and_credits"]:
        qol.skippable_title_and_credits(romfs, codec, mod)
    if settings["skulltulas_day_and_night"]:
        qol.skulltulas_day_and_night(romfs, codec, mod)
    stones = {}
    if settings["gossip_stone_hints"] != "none":   # (after Darunia's line: both change the message archives)
        stones = hints.make(s.world, s.locs, s.fixed, placed, s.closed, settings["hint_distribution"],
                            random.Random(seed_number(seed) ^ HINT_SEED), info=item_info(s.options), log=log)
        hints.write(romfs, mod, stones, settings["gossip_stone_hints"])
    mod.finish()
    spoiler = write_spoiler(out, seed, settings, s.world, s.locs, s.fixed, placed, s.closed, s.shop_prices)
    if stones:
        english = hints.Names(sarc.read(mod.read("Mals/USen.Product.110.sarc.zs")))
        with open(spoiler, "a", encoding="utf-8") as f:
            f.write("\nGossip stones (where each stands, its rumor's label, what it says):\n")
            for label, hint in sorted(stones.items(), key=lambda kv: (hints.STONES[kv[0]][0], kv[0])):
                f.write("  %-20s %-34s %s\n" % (hints.STONES[label][0], label, hints.english(hint, english)))
    with open(os.path.join(out, "placements.json"), "w", encoding="utf-8") as f:   # (what each check got: tools)
        json.dump({"seed": seed, "settings": settings,
                   "chests": {str(h): {"item": a, "event": e} for h, (a, e) in sorted(contents.items())},
                   "gifts": {lid: a for lid, a in sorted(given.items())},
                   "loose": {str(h): a for h, a in sorted(loose.items())},
                   "skulltulas": {str(h): a for h, a in sorted(drops.items())},
                   "shops": {slot.rc: {"item": placed[slot.rc], "price": s.shop_prices[slot.rc], "shelf": actor,
                                       "flag": slot.flag, "copies": [[rel, str(h)] for rel, h in slot.copies]}
                             for slot, actor in shelves},
                   "hints": dict(sorted(stones.items()))}, f, indent=1)
    log("seed %s: %d checks (%d chests, %d gifts, %d lying in the world, %d shelves), mod in %s, spoiler %s" % (
        seed, len(placed), sum(1 for l in s.locs if l.kind == "chest"), len(given),
        sum(1 for l in s.locs if l.kind == "loose"), len(shelves), out, spoiler))
    return placed


DARUNIA = "RC_GC_DARUNIAS_JOY"
SARIA = "RC_LW_GIFT_FROM_SARIA"
OCARINA_OF_TIME = "RC_HF_OCARINA_OF_TIME_ITEM"   # (his gift: his scene's edit, and the patch's silent adds with it)
HINT_SEED = 0x6057   # (the hints draw from their own generator: the same seed's items whatever the hint settings)
ARCHIVE = "rando-archive"   # (beside mods: Longshot loads every folder inside mods)


def archive_installed(mods_dir):
    """a copy of the installed seed (its whole mod folder, hand-made fixes included) in <game>/rando-archive/<seed>-<time>,
    before a new seed replaces it: a mistaken click never loses a playthrough's mod. Returns the copy's folder, or None"""
    import time
    src = os.path.join(mods_dir, MOD_NAME)
    if not os.path.isfile(os.path.join(src, "placements.json")):
        return None
    try:
        with open(os.path.join(src, "placements.json"), encoding="utf-8") as f:
            seed = str(json.load(f).get("seed", "seed"))
    except (OSError, ValueError):
        seed = "seed"
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in seed)[:60] or "seed"
    dst = os.path.join(os.path.dirname(os.path.abspath(mods_dir)), ARCHIVE, "%s-%s" % (safe, time.strftime("%Y%m%d-%H%M%S")))
    shutil.copytree(src, dst)
    return dst


def assign_tiers(s, placed, rng):
    """each tier group's spots, in playthrough order, get its tiers in order (I.TIERS: logic counts the group as one
    progressive item, the game sets each tier's capacity outright)"""
    by_id = {l.id: l for l in s.locs}
    every = {**s.fixed, **{lid: I.soh_item(a, by_id[lid].map) for lid, a in placed.items()}}
    every = {k: v for k, v in every.items() if v != "RG_NONE"}
    _, spheres = s.world.collect(collections.Counter(), every)
    when = {lid: i for i, sphere in enumerate(spheres) for lid in sphere}
    placed = dict(placed)
    for group in I.TIERS:
        spots = [lid for lid, a in placed.items() if a in group]
        rng.shuffle(spots)   # (spots in the same sphere: any order)
        spots.sort(key=lambda lid: when.get(lid, len(spheres)))
        for i, lid in enumerate(spots):
            placed[lid] = group[min(i, len(group) - 1)]
            if not I.fits(placed[lid], lid, by_id[lid].kind):
                raise fill.FillError("%s cannot go in %s" % (placed[lid], by_id[lid].name))
    return placed


# (progressive items at the most the game gives: SoH keeps upgrades in bit fields, and more (a 10th bomb bag) runs into the
# next field (the strength's))
MOST = {"RG_PROGRESSIVE_HOOKSHOT": 2, "RG_PROGRESSIVE_SCALE": 2, "RG_PROGRESSIVE_MAGIC_METER": 2, "RG_PROGRESSIVE_OCARINA": 2,
        "RG_PROGRESSIVE_GORONSWORD": 2}


def every_item(progression):
    """every progression item (silver rupees aside: events give them), as many as the game can give"""
    from .logic.logic import _SILVER_RUPEES
    return collections.Counter({rg: MOST.get(rg, 3 if rg.startswith("RG_PROGRESSIVE_") else 10)
                                for rg in progression if rg not in _SILVER_RUPEES})


def closed_locations(world, locs, progression, fixed=None):
    """the checks logic does not reach even with every item (and what the checks left as they are give: the Gold Skulltulas'
    tokens): their way in is not known (research/mapping's open questions)"""
    have = every_item(progression)
    if fixed:
        have, _ = world.collect(have, fixed)
    reach = world.reachable(have)
    return {l.id for l in locs if l.id not in reach}


def write_spoiler(out, seed, settings, world, locs, fixed, placed, closed=(), prices=None):
    by_id = {l.id: l for l in locs}
    every = {**fixed, **{lid: I.soh_item(a, by_id[lid].map) for lid, a in placed.items()}}
    every = {k: v for k, v in every.items() if v != "RG_NONE"}
    _, spheres = world.collect(collections.Counter(), every)
    info = item_info()
    progression = {rg for rg, i in info.items() if i.get("progression")}
    major = {rg for rg, i in info.items() if i.get("major")}
    lines = ["HookshotRando spoiler", "seed: %s" % seed, "settings: %s" % json.dumps(settings, sort_keys=True), "",
             "Playthrough: by sphere, what the checks give that logic needs, and the major items the game gives as usual",
             "(a sphere: what can be had with everything from the spheres before it)"]
    for i, s in enumerate(spheres):
        got = []
        for lid in sorted(s, key=str):
            if lid in by_id and I.soh_item(placed[lid], by_id[lid].map) in progression:
                got.append("%s -> %s" % (by_id[lid].name, placed[lid]))
            elif lid in fixed and fixed[lid] in major:
                got.append("%s -> %s (as in the game)" % (lid, info[fixed[lid]]["name"]))
        if got:
            lines.append("  sphere %d" % i)
            lines += ["    " + g for g in sorted(got)]
    for kind, title in (("chest", "Chests"), ("gift", "Gifts (NPCs, minigames, scrubs)"), ("loose", "Lying in the world"),
                        ("skulltula", "Gold Skulltulas"), ("shop", "Shops (price in rupees)")):
        lines += ["", title + ":"]
        for l in sorted((l for l in locs if l.kind == kind), key=lambda l: l.name):
            price = " for %d" % prices[l.id] if prices and l.id in prices else ""
            lines.append("  %-70s %s%s%s" % (l.name, placed[l.id], price,
                                             "   (not in logic: junk only)" if l.id in closed else ""))
    path = os.path.join(out, "spoiler.txt")
    os.makedirs(out, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path
