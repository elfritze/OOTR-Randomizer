"""Indexes for mapping the remake's non-chest checks (facts read from the game, no game data):

- research/gift_events.json: every event flow event with an item-like actor name in its parameters (what NPCs, songs and
  cutscenes give): flow, event index, what it is (call Flow:Entry or Actor.Action), the parameter and its value, and the
  entry points it is reached from.
- research/world_items.json: every actor in the maps that is an item lying in the world (Heart Pieces, keys, rupees,
  containers), chests aside: map file, Hash, Gyaml, position, Dynamic, links.

    python research/index_gifts.py
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando import chests  # noqa: E402
from rando.events import Events  # noqa: E402
from rando.formats import byml, zs  # noqa: E402

ROMFS = r"C:\Projects\ootremake-recomp\Hookshot-Build\romfs"
HERE = os.path.dirname(os.path.abspath(__file__))
ITEMISH = re.compile(r"^(Item_|Obj_Rupee|Obj_Heart|Obj_Item|Weapon_|Armor_|TBox_|Tbox_|Obj_Dungeon|Obj_Key|Obj_Bomb|Obj_Arrow"
                     r"|Obj_DekuNut|Obj_DekuStick|Obj_Seed|Obj_Fairy|Obj_GoldSkull|Obj_HeartContainer|Obj_Magic"
                     r"|Obj_Armor|Obj_Shield|Obj_MiniGame|Shop_|Obj_\w*Heart_(Piece|Container))")


def strings(v, path=""):
    if isinstance(v, str):
        yield path, v
    elif isinstance(v, dict):
        for k, x in v.items():
            yield from strings(x, (path + "." if path else "") + str(k))
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from strings(x, "%s[%d]" % (path, i))


def gifts(codec):
    E = Events(ROMFS, codec)
    out = []
    for name in sorted(E.names):
        try:
            fc = E.flow(name)
        except Exception as e:   # (noted, not hidden)
            out.append({"flow": name, "error": repr(e)})
            continue
        evs = fc["events"]
        # (which entry points reach each event: a plain walk of next/cases/forks)
        reach = {}
        for entry, start in fc["entries"].items():
            todo, seen = [start], set()
            while todo:
                i = todo.pop()
                if i is None or i in seen or not (0 <= i < len(evs)):
                    continue
                seen.add(i)
                reach.setdefault(i, []).append(entry)
                ev = evs[i]
                todo += [ev.get("next")] + list((ev.get("cases") or {}).values()) + list(ev.get("forks") or []) + \
                    [ev.get("join")]
        for i, ev in enumerate(evs):
            # (ArmorName: what Link wears, asked by switches: no gift)
            hits = [(k, v) for k, v in strings(ev.get("params") or {}) if ITEMISH.match(v) and k != "ArmorName"]
            if not hits:
                continue
            t = ev["type"]
            if t == "action":
                a = fc["actors"][ev["actor"]]
                what = "%s.%s" % (a["name"], a["actions"][ev["action"]])
            elif t in ("subflow", "subflow_switch"):
                what = "call %s:%s" % (ev["flowchart"] or name, ev["entry"])
            else:
                what = t
            for k, v in hits:
                out.append({"flow": name, "event": i, "what": what, "param": k, "value": v,
                            "entries": sorted(reach.get(i, []))})
    return out


def world_items(codec):
    out = []
    for rel in chests.map_files(ROMFS):
        root, _ = byml.read(codec.read(os.path.join(ROMFS, rel)))
        for a in root.get("Actors", []):
            g = a.get("Gyaml", "")
            if chests.is_chest(a) or not ITEMISH.match(g):
                continue
            out.append({"map": rel, "hash": str(a.get("Hash")), "gyaml": g,
                        "pos": [round(x, 2) for x in a.get("Translate", [])],
                        "dynamic": a.get("Dynamic"), "phive": bool(a.get("Phive")),
                        "links": [{"dst": str(l.get("Dst")), "name": l.get("Name")} for l in a.get("Links", [])]})
    return out


def main():
    codec = zs.Codec(ROMFS)
    g = gifts(codec)
    with open(os.path.join(HERE, "gift_events.json"), "w", encoding="utf-8") as f:
        json.dump(g, f, indent=0, ensure_ascii=False, default=str)
    w = world_items(codec)
    with open(os.path.join(HERE, "world_items.json"), "w", encoding="utf-8") as f:
        json.dump(w, f, indent=0, ensure_ascii=False, default=str)
    import collections
    print(len(g), "gift events;", len(w), "world items")
    print(collections.Counter(x["gyaml"] for x in w).most_common(40))


if __name__ == "__main__":
    main()
