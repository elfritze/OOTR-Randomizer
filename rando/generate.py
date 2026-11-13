"""A seed: the chests, the NPCs' gifts and the items lying in the world filled (rando.fill) by the logic (rando.logic: SoH's,
with the remake's changes from data/locations.json and data/gifts.json), written as a RomFS mod, with its spoiler log."""
import collections
import hashlib
import json
import os
import random

from . import chests, fill, gifts, patches, pickups
from . import items as I
from .formats import zs
from .logic import soh_regions as R
from .logic.search import World, item_info, vanilla_items
from .mod import Mod

HERE = os.path.dirname(os.path.abspath(__file__))
LOCATIONS = os.path.join(HERE, "..", "data", "locations.json")
GIFTS = os.path.join(HERE, "..", "data", "gifts.json")
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


def _entries(table, gift_table):
    """chests and gifts alike: {"id", "rc", "region", "condition"}"""
    out = [{"id": l["id"], "rc": l["rc"], "region": l["region"], "condition": l.get("condition")} for l in table["locations"]]
    if gift_table:
        out += [{"id": c["id"], "rc": c["rc"], "region": c["soh_region"], "condition": c.get("rule")}
                for c in gift_table["checks"]]
    return out


def make_world(table, gift_table=None):
    entries = _entries(table, gift_table)
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
    return World(extra_locations=extra, rule_overrides=overrides, removed_locations=tuple(table.get("removed", ())))


def seed_number(seed):
    return int.from_bytes(hashlib.sha256(str(seed).encode("utf-8")).digest()[:8], "little")


class Setup:
    """everything a seed is made from: the tables, the chests found in this game, the locations, the logic"""

    def __init__(self, romfs, codec, with_gifts=True):
        self.table = load_table()
        self.gifts = load_gifts() if with_gifts else {"checks": [], "excluded": []}
        self.found = chests.scan(romfs, codec)
        locs = []
        for l in self.table["locations"]:
            h = int(l["hash"])
            if h not in self.found:
                raise ValueError("chest %s (%s) is not in this game's maps" % (l["hash"], l["name"]))
            if self.found[h]["drop"] != l["vanilla"]:
                raise ValueError("chest %s holds %s, the table says %s" % (l["hash"], self.found[h]["drop"], l["vanilla"]))
            locs.append(fill.Location(l["id"], h, self.found[h]["map"], l["vanilla"], "%s: %s" % (l["area"], l["name"])))
        covered = {x.hash for x in locs} | {int(c) for l in self.table["locations"] for c in l["copies"]} | \
            {int(h) for h in self.table.get("skipped", ())}
        missing = [h for h in self.found if h not in covered]
        if missing:
            raise ValueError("chests not in data/locations.json: %s" % missing[:5])
        for c in self.gifts["checks"]:
            remake_map = c["loose"][0]["map"].split("/")[1] if c["kind"] == "loose" else None
            locs.append(fill.Location(c["id"], None, remake_map, I.canonical(c["vanilla"]), "%s: %s" % (c["area"], c["name"]),
                                      kind=c["kind"]))
        self.locs = locs
        self.world = make_world(self.table, self.gifts)
        mapped = {e["rc"] for e in _entries(self.table, self.gifts) if e["rc"]}
        removed = set(self.table.get("removed", ()))
        self.fixed = {rc: rg for rc, rg in vanilla_items().items()
                      if rc not in mapped and rc not in removed and rc in self.world.location_ids}
        self.progression = {rg for rg, info in item_info().items() if info.get("progression")}
        self.closed = closed_locations(self.world, self.locs, self.progression, self.fixed)

    def fill(self, rng):
        return fill.fill(self.world, self.locs, self.fixed, self.progression, rng, self.closed)


def generate(romfs, mods_dir, seed, settings, log=print):
    codec = zs.Codec(romfs)
    s = Setup(romfs, codec)
    rng = random.Random(seed_number(seed))
    placed = s.fill(rng)
    placed = assign_tiers(s, placed, rng)

    out = os.path.join(mods_dir, MOD_NAME)
    mod = Mod(romfs, codec, os.path.join(out, "romfs"))
    by_id = {l.id: l for l in s.locs}
    copies = {l["id"]: [int(c) for c in l["copies"]] for l in s.table["locations"]}
    contents = {}
    for lid, actor in placed.items():
        if by_id[lid].kind != "chest":
            continue
        for h in [by_id[lid].hash] + copies[lid]:   # (a chest placed twice gets the same item in each copy)
            contents[h] = (actor, chests.event_for(s.found[h], actor))
    chests.write(romfs, codec, mod, contents)
    gift_by_id = {c["id"]: c for c in s.gifts["checks"]}
    given, loose = {}, {}
    for lid, actor in placed.items():
        kind = by_id[lid].kind
        if kind == "gift":
            given[lid] = I.form(actor, "gift")
        elif kind == "loose":
            new = I.form(actor, "loose")
            for a in gift_by_id[lid]["loose"]:
                if new != a.get("gyaml"):   # (an item left where it was stays as the game has it)
                    loose[int(a["hash"])] = new
    gifts.write(romfs, codec, mod, [(gift_by_id[lid], actor) for lid, actor in given.items()])
    made = pickups.Pickups(romfs, codec, mod)
    if loose:
        pickups.place(romfs, codec, mod, loose, made)
    made.finish()
    patches.song_models(romfs, codec, mod)
    if settings["skip_intro"]:
        patches.skip_intro(romfs, codec, mod)
    mod.finish()
    spoiler = write_spoiler(out, seed, settings, s.world, s.locs, s.fixed, placed, s.closed)
    with open(os.path.join(out, "placements.json"), "w", encoding="utf-8") as f:   # (what each check got: tools)
        json.dump({"seed": seed, "settings": settings,
                   "chests": {str(h): {"item": a, "event": e} for h, (a, e) in sorted(contents.items())},
                   "gifts": {lid: a for lid, a in sorted(given.items())},
                   "loose": {str(h): a for h, a in sorted(loose.items())}}, f, indent=1)
    log("seed %s: %d checks (%d chests, %d gifts, %d lying in the world), mod in %s, spoiler %s" % (
        seed, len(placed), sum(1 for l in s.locs if l.kind == "chest"), len(given),
        sum(1 for l in s.locs if l.kind == "loose"), out, spoiler))
    return placed


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
            if not I.allowed(placed[lid], by_id[lid].kind):
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


def write_spoiler(out, seed, settings, world, locs, fixed, placed, closed=()):
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
    for kind, title in (("chest", "Chests"), ("gift", "Gifts (NPCs, minigames, scrubs)"), ("loose", "Lying in the world")):
        lines += ["", title + ":"]
        for l in sorted((l for l in locs if l.kind == kind), key=lambda l: l.name):
            lines.append("  %-70s %s%s" % (l.name, placed[l.id], "   (not in logic: junk only)" if l.id in closed else ""))
    path = os.path.join(out, "spoiler.txt")
    os.makedirs(out, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path
