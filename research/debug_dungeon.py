"""where a dungeon stops in the unmodified remake's playthrough: python research/debug_dungeon.py <romfs> <RR prefix>"""
import collections, sys
sys.path.insert(0, ".")
from rando import chests, generate, items as I
from rando.formats import zs
from rando.logic.search import vanilla_items
from rando.logic import soh_regions as R
romfs, prefix = sys.argv[1], sys.argv[2]
table = generate.load_table(); world = generate.make_world(table)
found = chests.scan(romfs, zs.Codec(romfs))
mapped = {l["rc"] for l in table["locations"] if l["rc"]}
fixed = {rc: rg for rc, rg in vanilla_items().items() if rc not in mapped and rc not in set(table["removed"]) and rc in world.location_ids}
placed = {l["id"]: I.soh_item(found[int(l["hash"])]["drop"], l["map"]) for l in table["locations"]}
placed = {k: v for k, v in placed.items() if v != "RG_NONE"}
have, spheres = world.collect(collections.Counter(), {**fixed, **placed})
s = world._search(have)
print("keys:", {k: v for k, v in have.items() if "KEY" in k})
reached = {rr for rr, a in s.access.items() if a.childDay or a.childNight or a.adultDay or a.adultNight}
for rr in world.regions:
    if not rr.startswith(prefix): continue
    if rr in reached: continue
    ins = [(src, cpp) for src, r in world.regions.items() if src in reached for to, fn, cpp, wh in r.exits if to == rr]
    if ins: print("NOT REACHED", rr, "| from reached:", ins[:3])
