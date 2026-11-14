import sys, json
sys.path.insert(0, r"C:\Projects\ootremake-recomp\HookshotRando")
from rando.formats import zs
from rando.events import Events
R = r"C:\Projects\ootremake-recomp\Longshot-Build\romfs"
E = Events(R, zs.Codec(R))
fc = E.flow(sys.argv[1])
print("entries:", fc["entries"])
print("actors:", [(i, a["name"], a["sub"], a["actions"], a["queries"]) for i, a in enumerate(fc["actors"])])
for i, ev in enumerate(fc["events"]):
    t = ev["type"]
    if t == "action":
        a = fc["actors"][ev["actor"]]; s = "%s.%s -> %s" % (a["name"], a["actions"][ev["action"]], ev["next"])
    elif t == "switch":
        a = fc["actors"][ev["actor"]]; s = "?%s.%s cases %s" % (a["name"], a["queries"][ev["query"]], ev["cases"])
    elif t in ("subflow", "subflow_switch"):
        s = "call %s:%s -> %s" % (ev["flowchart"] or "(self)", ev["entry"], ev.get("next", ev.get("cases")))
    elif t == "fork": s = "fork %s join %s" % (ev["forks"], ev["join"])
    elif t == "join": s = "join -> %s" % ev["next"]
    else: s = "return %#x" % ev["label"]
    p = ev.get("params")
    print("%3d %s %s" % (i, s, json.dumps(p, ensure_ascii=False, default=str)[:220] if p else ""))
