"""A generated mod against the game's own files: each chest holds what placements.json says, with its event as
rando.chests.event_for gives it and no substitute left where its item changed; nothing else in any map changed; every file
fits its resource size table entry; the songs show the harp; the opening's two movies point at the empty event.

    python tools/verify_mod.py <romfs> <mod folder (with romfs, placements.json)>"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando import chests, patches  # noqa: E402
from rando.events import EVENT_SETTING  # noqa: E402
from rando.formats import byml, restbl, sarc, zs  # noqa: E402
from rando.mod import RSTB, align32  # noqa: E402


def key(v):
    return json.dumps(v, sort_keys=True, default=str)


def main():
    romfs, mod = sys.argv[1], sys.argv[2]
    mod_romfs = os.path.join(mod, "romfs")
    codec = zs.Codec(romfs)
    plan = json.load(open(os.path.join(mod, "placements.json"), encoding="utf-8"))
    want = {int(h): (c["item"], c["event"]) for h, c in plan["chests"].items()}
    found = chests.scan(romfs, codec)
    problems, seen = [], set()
    table = restbl.Table(codec.read(os.path.join(mod_romfs, *RSTB.split("/"))))
    original_table = restbl.Table(codec.read(os.path.join(romfs, *RSTB.split("/"))))
    for rel in chests.map_files(romfs):
        mod_path = os.path.join(mod_romfs, *rel.split("/"))
        a, _ = byml.read(codec.read(os.path.join(romfs, rel)))
        if not os.path.exists(mod_path):
            for x in a.get("Actors", []):
                if int(x.get("Hash", 0)) in want and chests.is_chest(x):
                    problems.append("%s: chest %s is not in the mod" % (rel, x["Hash"]))
            continue
        data = codec.read(mod_path)
        b, _ = byml.read(data)
        if {k: v for k, v in a.items() if k != "Actors"} != {k: v for k, v in b.items() if k != "Actors"}:
            problems.append("%s: something besides the actors changed" % rel)
        if len(a["Actors"]) != len(b["Actors"]):
            problems.append("%s: actor count changed" % rel)
        for x, y in zip(a["Actors"], b["Actors"]):
            h = int(x.get("Hash", 0))
            if h in want and chests.is_chest(x):
                seen.add(h)
                item, event = want[h]
                dyn = y.get("Dynamic") or {}
                if dyn.get(chests.DROP) != item:
                    problems.append("%s: chest %d holds %s, planned %s" % (rel, h, dyn.get(chests.DROP), item))
                if dyn.get(chests.EVENT) != event or event != chests.event_for(found[h], item):
                    problems.append("%s: chest %d event %s, planned %s" % (rel, h, dyn.get(chests.EVENT), event))
                if item != found[h]["drop"] and any(k in dyn for k in chests.SUBSTITUTE):
                    problems.append("%s: chest %d keeps a substitute" % (rel, h))
                rest_x = {k: v for k, v in (x.get("Dynamic") or {}).items() if k not in (chests.DROP, chests.EVENT) + chests.SUBSTITUTE}
                rest_y = {k: v for k, v in dyn.items() if k not in (chests.DROP, chests.EVENT) + chests.SUBSTITUTE}
                if rest_x != rest_y or key({k: v for k, v in x.items() if k != "Dynamic"}) != key({k: v for k, v in y.items() if k != "Dynamic"}):
                    problems.append("%s: chest %d changed beyond its content" % (rel, h))
            elif key(x) != key(y):
                problems.append("%s: actor %s (%s) changed" % (rel, x.get("Hash"), x.get("Gyaml")))
        need = align32(len(data)) + original_table.get(rel) - align32(len(codec.read(os.path.join(romfs, rel))))
        if table.get(rel) < need:
            problems.append("%s: %d bytes, its table entry %d" % (rel, len(data), table.get(rel)))
    missing = set(want) - seen
    if missing:
        problems.append("planned chests not found in any map: %s" % sorted(missing)[:5])
    # (the songs' model and the opening's events)
    for song in patches.SONGS:
        files = sarc.read(codec.read(os.path.join(mod_romfs, "Pack", "Actor", song + ".pack.zs")))
        info, _ = byml.read(files["Component/ModelInfo/%s.engine__component__ModelInfo.bgyml" % song])
        if (info["ModelProjectName"], info["FmdbName"]) != patches.SONG_MODEL:
            problems.append("%s: model %s" % (song, info))
    rows, _ = byml.read(codec.read(os.path.join(mod_romfs, *EVENT_SETTING.split("/"))))
    by = {r["__RowId"]: r for r in rows}
    if plan["settings"].get("skip_intro"):
        for m in patches.OPENING_MOVIES:
            if {k: v for k, v in by[m].items() if k != "__RowId"} != {k: v for k, v in by[patches.EMPTY_EVENT].items() if k != "__RowId"}:
                problems.append("opening movie %s not skipped" % m)
    print("%d chests planned, %d found in the maps; %d problems" % (len(want), len(seen), len(problems)))
    for p in problems[:30]:
        print("  ", p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
