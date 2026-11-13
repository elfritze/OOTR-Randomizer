import sys, json, collections
sys.path.insert(0, r"C:\Projects\ootremake-recomp\HookshotRando")
from rando.formats import zs
from rando.events import Events
R = r"C:\Projects\ootremake-recomp\Hookshot-Build\romfs"
E = Events(R, zs.Codec(R))
def targets(name):
    loc = E.locate(name)
    if loc: return [loc]
    if name in E.names:
        en = E.flow(name)["entries"]
        if not en: return []
        return [(name, "EntryPoint0")] if "EntryPoint0" in en else [(name, e) for e in en]
    return []
def summarize(name, depth=0, seen=None, out=None):
    seen = set() if seen is None else seen; out = collections.defaultdict(set) if out is None else out
    if name in seen or depth > 3: return out
    seen.add(name)
    for loc in targets(name):
        for d, flow, kind, actor, act, params in E.walk(*loc, max_depth=3):
            p = params or {}
            if kind == "action" and act == "EventTransition" and p.get("EventName"):
                out["transition"].add(p["EventName"])
                if not p["EventName"].startswith("Dm_SY_Treasurebox"): summarize(p["EventName"], depth + 1, seen, out)
            elif kind == "action" and ("GameData" in act or "GameData" in actor) and "Query" not in act:
                out["gamedata"].add("%s.%s %s" % (actor, act, json.dumps(p, default=str)))
            elif kind == "call":
                out["call"].add("%s:%s %s" % (actor, act, json.dumps(p, default=str)[:120]))
            elif kind == "action" and ("Pouch" in act or "Pouch" in actor or "Item" in act or "Equip" in act):
                out["pouch"].add("%s.%s %s" % (actor, act, json.dumps(p, default=str)))
    return out
evs = sys.argv[1:] or sorted({r["event"] for r in json.load(open("chests.json")).values() if r["event"]})
for ev in evs:
    o = summarize(ev)
    print("=====", ev, targets(ev))
    for k in ("transition", "call", "gamedata", "pouch"):
        for v in sorted(o.get(k, ())): print("   %-10s %s" % (k, v[:260]))
