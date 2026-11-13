"""The remake's logic (SoH's, with data/locations.json): every chest reachable with every item, and the unmodified game (each chest
with its own item) beatable from a new game.

    python tools/check_remake.py <romfs>"""
import collections
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando import chests, generate  # noqa: E402
from rando import items as I  # noqa: E402
from rando.formats import zs  # noqa: E402
from rando.logic.search import item_info, vanilla_items  # noqa: E402


def main():
    romfs = sys.argv[1]
    table = generate.load_table()
    world = generate.make_world(table)
    found = chests.scan(romfs, zs.Codec(romfs))
    locs = table["locations"]
    info = item_info()

    reach = world.reachable(generate.every_item({rg for rg, it in info.items() if it["progression"]}))
    missed = [l for l in locs if l["id"] not in reach]
    print("1. every item: %d of %d chest locations reachable" % (len(locs) - len(missed), len(locs)))
    for l in missed:
        print("   unreachable: %s (%s, %s)" % (l["id"], l["map"], l["region"]))

    mapped = {l["rc"] for l in locs if l["rc"]}
    removed = set(table["removed"])
    fixed = {rc: rg for rc, rg in vanilla_items().items() if rc not in mapped and rc not in removed and rc in world.location_ids}
    placed = {l["id"]: I.soh_item(found[int(l["hash"])]["drop"], l["map"]) for l in locs}
    placed = {k: v for k, v in placed.items() if v != "RG_NONE"}
    # (SoH's own key rules are stricter than the game where a vanilla key sits behind the longshot or the gauntlets (its own
    #  vanilla playthrough needs these too, tools/check_logic.py): with the keys shuffled the fill places keys to fit them.
    #  The unmodified game is played here with one key more in each, so the rest of the logic is checked through)
    allowance = collections.Counter({"RG_WATER_TEMPLE_SMALL_KEY": 1, "RG_SPIRIT_TEMPLE_SMALL_KEY": 1})
    have, spheres = world.collect(allowance, {**fixed, **placed})
    print("2. the unmodified remake (+1 Water key, +1 Spirit key): %d spheres, beatable: %s" % (len(spheres), world.can_beat(have)))
    got = set().union(*spheres) if spheres else set()
    stuck = [l for l in locs if l["id"] in placed and l["id"] not in got]
    for l in stuck:
        print("   not reached: %s holding %s (%s, %s)" % (l["id"], placed[l["id"]], l["map"], l["region"]))
    prog = {rg for rg, it in info.items() if it["progression"]}
    missing = collections.Counter(rg for lid, rg in {**fixed, **placed}.items() if lid not in got and rg in prog)
    print("   progression never collected:", dict(missing))


if __name__ == "__main__":
    main()
