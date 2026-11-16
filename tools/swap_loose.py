"""Two loose spots of an installed seed trading their items, put on top of it (every other file as installed: the same seed,
nothing rebuilt), for a seed whose item lies where the game does not let the player reach it yet:

    python tools/swap_loose.py <romfs> <installed mod folder (HookshotRando)> <new mod folder> <check id> <check id>

Each spot's map actors (every map holding them: child, adult...) take the other item, at the game's own position lifted as
generate lifts it (rando.pickups.place); placements.json and the spoiler say so. Both items must already be in the seed
(their pickups are made: nothing new is built), each where the other's spot can hold it (rando.items.fits)."""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando import chests, generate, items as I, pickups  # noqa: E402
from rando.formats import byml, zs  # noqa: E402
from make_shop_test import OnTop  # noqa: E402


def main():
    romfs, base, out, first, second = sys.argv[1:6]
    codec = zs.Codec(romfs)
    if os.path.exists(out):
        raise SystemExit("%s exists" % out)
    plan = json.load(open(os.path.join(base, "placements.json"), encoding="utf-8"))
    gifts = {c["id"]: c for c in generate.load_gifts()["checks"]}
    spots = {}
    for lid in (first, second):
        c = gifts.get(lid)
        if not c or c["kind"] != "loose":
            raise SystemExit("%s: not a loose check" % lid)
        hashes = {a["hash"] for a in c["loose"]}
        held = {plan.get("loose", {}).get(h) for h in hashes} - {None}
        if len(held) != 1:
            raise SystemExit("%s: its spot's item is not in placements.json (%s)" % (lid, sorted(held)))
        spots[lid] = (hashes, held.pop())
    (ha, ia), (hb, ib) = spots[first], spots[second]
    for item, lid in ((ia, second), (ib, first)):
        if not I.fits(I.canonical(item), lid, "loose"):
            raise SystemExit("%s cannot lie at %s" % (item, lid))
    want = {h: ib for h in ha}
    want.update({h: ia for h in hb})

    shutil.copytree(base, out)
    mod = OnTop(romfs, codec, os.path.join(base, "romfs"), os.path.join(out, "romfs"))
    made = pickups.Pickups(romfs, codec, mod)
    for item in (ia, ib):
        if not item.startswith("Obj_") and not os.path.exists(os.path.join(base, "romfs", *pickups.pack_path(
                pickups.name_for(item)).split("/"))):
            raise SystemExit("%s: no pickup of it in the seed" % item)
    seen = set()
    for rel in chests.map_files(romfs):
        root, version = byml.read(mod.read(rel))
        game = None
        changed = False
        for a in root.get("Actors", []):
            h = str(a.get("Hash", 0))
            if h not in want:
                continue
            if game is None:
                game = {str(g.get("Hash", 0)): g for g in byml.read(codec.read(os.path.join(romfs, *rel.split("/"))))[0]
                        .get("Actors", [])}
            orig = game[h]   # (the game's own actor: its position before any lift)
            item = want[h]
            lift = pickups.LIFT_FROM.get(orig["Gyaml"], 0.0) + pickups.model_bottom(made, item)
            t = orig["Translate"]
            a["Translate"] = [t[0], type(t[1])(t[1] + lift), t[2]] if lift else list(t)
            a["Gyaml"] = item if item.startswith("Obj_") else pickups.name_for(item)
            seen.add(h)
            changed = True
        if changed:
            mod.write(rel, byml.write(root, version))
    if seen != set(want):
        raise SystemExit("not in any map: %s" % sorted(set(want) - seen))
    mod.finish()
    for h, item in want.items():
        plan["loose"][h] = item
    with open(os.path.join(out, "placements.json"), "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=1, ensure_ascii=False)
    with open(os.path.join(out, "spoiler.txt"), "a", encoding="utf-8") as f:
        f.write("\nSwapped after install (tools/swap_loose.py): %s now holds %s, %s now holds %s.\n" % (
            gifts[first]["name"], ib, gifts[second]["name"], ia))
    print("%s: %s -> %s; %s: %s -> %s" % (first, ia, ib, second, ib, ia))


if __name__ == "__main__":
    main()
