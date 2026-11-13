"""A generated mod against the game's own files: each chest holds what placements.json says, with its event as
rando.chests.event_for gives it and no substitute left where its item changed; each item lying in the world is the planned
pickup (only its Gyaml and its height changed); each gift's flow differs from the game's in exactly data/gifts.json's
parameters, set to the planned item; nothing else in any map or flow changed; every new pickup has its pack and its rows;
every file fits its resource size table entry; the songs show the harp; the opening's two movies point at the empty event.

    python tools/verify_mod.py <romfs> <mod folder (with romfs, placements.json)>"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando import chests, generate, gifts, patches, pickups  # noqa: E402
from rando.formats import evfl  # noqa: E402
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
    loose = {int(h): a for h, a in plan.get("loose", {}).items()}
    loose_seen = set()
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
            elif h in loose:
                loose_seen.add(h)
                name = loose[h] if loose[h].startswith("Obj_") else pickups.name_for(loose[h])
                if y.get("Gyaml") != name:
                    problems.append("%s: %d is %s, planned %s" % (rel, h, y.get("Gyaml"), name))
                if key({k: v for k, v in x.items() if k not in ("Gyaml", "Translate")}) !=                         key({k: v for k, v in y.items() if k not in ("Gyaml", "Translate")}) or                         [x["Translate"][0], x["Translate"][2]] != [y["Translate"][0], y["Translate"][2]] or                         not 0 <= y["Translate"][1] - x["Translate"][1] <= 0.6:
                    problems.append("%s: %d changed beyond its item and height" % (rel, h))
            elif key(x) != key(y):
                problems.append("%s: actor %s (%s) changed" % (rel, x.get("Hash"), x.get("Gyaml")))
        need = align32(len(data)) + original_table.get(rel) - align32(len(codec.read(os.path.join(romfs, rel))))
        if table.get(rel) < need:
            problems.append("%s: %d bytes, its table entry %d" % (rel, len(data), table.get(rel)))
    missing = set(want) - seen
    if missing:
        problems.append("planned chests not found in any map: %s" % sorted(missing)[:5])
    if set(loose) - loose_seen:
        problems.append("planned loose items not found in any map: %s" % sorted(set(loose) - loose_seen)[:5])
    # (the gifts: exactly the table's parameters changed, each to its check's item)
    table_g = {c["id"]: c for c in generate.load_gifts()["checks"]}
    expect = {}
    for cid, actor in plan.get("gifts", {}).items():
        for e in table_g[cid]["edits"]:
            expect[(e["flow"], e["event"], e["param"])] = actor
    flows = {f for f, _, _ in expect}
    flow_dir = os.path.join(mod_romfs, "Event", "EventFlow")
    in_mod = {f[:-len(".bfevfl.zs")] for f in os.listdir(flow_dir)} if os.path.isdir(flow_dir) else set()
    for f in sorted(flows | in_mod):
        rel = gifts.flow_path(f)
        if f not in in_mod:
            problems.append("%s: not in the mod" % rel)
            continue
        a = evfl.read(codec.read(os.path.join(romfs, *rel.split("/"))))[0]
        b = evfl.read(codec.read(os.path.join(mod_romfs, *rel.split("/"))))[0]
        if key({k: v for k, v in a.items() if k != "events"}) != key({k: v for k, v in b.items() if k != "events"}) or                 len(a["events"]) != len(b["events"]):
            problems.append("%s: more than events changed" % rel)
            continue
        for i, (x, y) in enumerate(zip(a["events"], b["events"])):
            for k in set((x.get("params") or {})) | set((y.get("params") or {})):
                vx, vy = (x.get("params") or {}).get(k), (y.get("params") or {}).get(k)
                want_v = expect.get((f, i, k), vx)
                if vy != want_v:
                    problems.append("%s event %d %s: %r, planned %r" % (rel, i, k, vy, want_v))
            if key({k: v for k, v in x.items() if k != "params"}) != key({k: v for k, v in y.items() if k != "params"}):
                problems.append("%s event %d: changed beyond its parameters" % (rel, i))
    # (the new pickups: a pack each, and their rows)
    made = {a for a in loose.values() if not a.startswith("Obj_")}
    for t in (pickups.ACTOR_INFO, pickups.GAME_ACTOR_INFO, pickups.POUCH_ACTOR_INFO):
        path = os.path.join(mod_romfs, *t.split("/"))
        ids = {r["__RowId"] for r in byml.read(codec.read(path))[0]} if os.path.exists(path) else set()
        for a in made:
            if pickups.name_for(a) not in ids:
                problems.append("%s: no row %s" % (t, pickups.name_for(a)))
    for a in made:
        if not os.path.exists(os.path.join(mod_romfs, *pickups.pack_path(pickups.name_for(a)).split("/"))):
            problems.append("no pack for %s" % pickups.name_for(a))
    # (every file of the mod fits its size table entry)
    for root, _, files in os.walk(mod_romfs):
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), mod_romfs).replace(os.sep, "/")
            if rel == RSTB:
                continue
            size = len(codec.read(os.path.join(root, fn)))
            entry = table.get(rel)
            if entry is None or entry < size:
                problems.append("%s: %d bytes, its table entry %s" % (rel, size, entry))
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
    print("%d chests planned, %d found; %d loose items planned, %d found; %d gift parameters; %d new pickups; %d problems" % (
        len(want), len(seen), len(loose), len(loose_seen), len(expect), len(made), len(problems)))
    for p in problems[:30]:
        print("  ", p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
