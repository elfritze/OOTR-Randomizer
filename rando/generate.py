"""A seed: the chests filled (rando.fill) by the logic (rando.logic: SoH's, with the remake's changes from data/locations.json),
written as a RomFS mod, with its spoiler log."""
import collections
import hashlib
import json
import os
import random

from . import chests, fill, patches
from . import items as I
from .formats import zs
from .logic import soh_regions as R
from .logic.search import World, item_info, vanilla_items
from .mod import Mod

HERE = os.path.dirname(os.path.abspath(__file__))
LOCATIONS = os.path.join(HERE, "..", "data", "locations.json")
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


def make_world(table):
    extra = {}
    for l in table["locations"]:
        if not l["rc"]:
            extra[l["id"]] = (l["region"], l["condition"])
    overrides = {}
    soh_regions = {}   # (RC: SoH's regions holding it)
    for rr, r in R.REGIONS.items():
        for rc, _ in r["locations"]:
            soh_regions.setdefault(rc, set()).add(rr)
    for l in table["locations"]:
        if not l["rc"]:
            continue
        if l.get("condition"):
            overrides[("location", l["rc"])] = l["condition"]
        regs = soh_regions.get(l["rc"], set())
        # (the chest's region when the remake moved it, or when its rule is replaced and SoH has it in several regions
        #  (one rule needs one region). A check SoH reaches from several regions with their own rules, as the Forest
        #  Temple's well chest (underwater, or dry in the drained well), keeps them all otherwise)
        if l["region"] and (l["region"] not in regs or (l.get("condition") and len(regs) > 1)):
            overrides[("location_region", l["rc"])] = l["region"]
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


def generate(romfs, mods_dir, seed, settings, log=print):
    codec = zs.Codec(romfs)
    table = load_table()
    found = chests.scan(romfs, codec)
    locs = []
    for l in table["locations"]:
        h = int(l["hash"])
        if h not in found:
            raise ValueError("chest %s (%s) is not in this game's maps" % (l["hash"], l["name"]))
        if found[h]["drop"] != l["vanilla"]:
            raise ValueError("chest %s holds %s, the table says %s" % (l["hash"], found[h]["drop"], l["vanilla"]))
        locs.append(fill.Location(l["id"], h, found[h]["map"], l["vanilla"], "%s: %s" % (l["area"], l["name"])))
    covered = {x.hash for x in locs} | {int(c) for l in table["locations"] for c in l["copies"]} |         {int(h) for h in table.get("skipped", ())}
    missing = [h for h in found if h not in covered]
    if missing:
        raise ValueError("chests not in data/locations.json: %s" % missing[:5])
    world = make_world(table)
    mapped = {l["rc"] for l in table["locations"] if l["rc"]}
    fixed = {rc: rg for rc, rg in vanilla_items().items() if rc not in mapped and rc not in set(table.get("removed", ()))}
    progression = {rg for rg, info in item_info().items() if info.get("progression")}
    closed = closed_locations(world, locs, progression)
    rng = random.Random(seed_number(seed))
    placed = fill.fill(world, locs, fixed, progression, rng, closed)

    out = os.path.join(mods_dir, MOD_NAME)
    mod = Mod(romfs, codec, os.path.join(out, "romfs"))
    by_id = {l.id: l for l in locs}
    copies = {l["id"]: [int(c) for c in l["copies"]] for l in table["locations"]}
    contents = {}
    for lid, actor in placed.items():
        for h in [by_id[lid].hash] + copies[lid]:   # (a chest placed twice gets the same item in each copy)
            contents[h] = (actor, chests.event_for(found[h], actor))
    chests.write(romfs, codec, mod, contents)
    patches.song_models(romfs, codec, mod)
    if settings["skip_intro"]:
        patches.skip_intro(romfs, codec, mod)
    mod.finish()
    spoiler = write_spoiler(out, seed, settings, world, locs, fixed, placed, closed)
    with open(os.path.join(out, "placements.json"), "w", encoding="utf-8") as f:   # (what each chest got, by Hash: tools)
        json.dump({"seed": seed, "settings": settings,
                   "chests": {str(h): {"item": a, "event": e} for h, (a, e) in sorted(contents.items())}}, f, indent=1)
    log("seed %s: %d chests, mod in %s, spoiler %s" % (seed, len(placed), out, spoiler))
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


def closed_locations(world, locs, progression):
    """the chests logic does not reach even with every item: their way in is not known (research/mapping's open questions)"""
    reach = world.reachable(every_item(progression))
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
             "Playthrough: by sphere, what the chests give that logic needs, and the major items the game gives as usual",
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
    lines += ["", "Chests:"]
    for l in sorted(locs, key=lambda l: l.name):
        lines.append("  %-70s %s%s" % (l.name, placed[l.id], "   (not in logic: junk only)" if l.id in closed else ""))
    path = os.path.join(out, "spoiler.txt")
    os.makedirs(out, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path
