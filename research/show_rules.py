"""print SoH's rule text for exits / events / locations: python research/show_rules.py EXIT:RR_A:RR_B EVENT:RR:LOGIC LOC:RC REGION:RR"""
import sys
sys.path.insert(0, ".")
from rando.logic import soh_regions as R
for arg in sys.argv[1:]:
    kind, *rest = arg.split(":")
    if kind == "REGION":
        r = R.REGIONS.get(rest[0])
        if not r: print(arg, "NO REGION"); continue
        print("==", rest[0], r["name"])
        for ev, (_, cpp, wh) in r["events"]: print("   EVENT", ev, "|", cpp)
        for rc, (_, cpp, wh) in r["locations"]: print("   LOC", rc, "|", cpp)
        for to, (_, cpp, wh) in r["exits"]: print("   EXIT ->", to, "|", cpp)
    elif kind == "EXIT":
        r = R.REGIONS.get(rest[0]); hits = [cpp for to, (_, cpp, wh) in (r["exits"] if r else []) if to == rest[1]]
        print(arg, "|", hits or "NO SUCH EXIT")
    elif kind == "EVENT":
        r = R.REGIONS.get(rest[0]); hits = [cpp for ev, (_, cpp, wh) in (r["events"] if r else []) if ev == rest[1]]
        print(arg, "|", hits or "NO SUCH EVENT")
    elif kind == "LOC":
        hits = [(rr, cpp) for rr, r in R.REGIONS.items() for rc, (_, cpp, wh) in r["locations"] if rc == rest[0]]
        print(arg, "|", hits or "NO SUCH LOCATION")
