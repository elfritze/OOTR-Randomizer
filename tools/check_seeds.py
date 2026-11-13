"""Many seeds in a row, each filled and verified (beatable, every chest in logic reachable, the ORDERED pairs in order), into a
scratch folder: how often a seed needs more than one attempt, and that none fails.

    python tools/check_seeds.py <romfs> <count>"""
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando import chests, fill, generate  # noqa: E402
from rando.formats import zs  # noqa: E402
from rando.logic.search import item_info, vanilla_items  # noqa: E402


def main():
    romfs, count = sys.argv[1], int(sys.argv[2])
    table = generate.load_table()
    world = generate.make_world(table)
    found = chests.scan(romfs, zs.Codec(romfs))
    locs = [fill.Location(l["id"], int(l["hash"]), found[int(l["hash"])]["map"], l["vanilla"], l["name"]) for l in table["locations"]]
    mapped = {l["rc"] for l in table["locations"] if l["rc"]}
    fixed = {rc: rg for rc, rg in vanilla_items().items() if rc not in mapped and rc not in set(table["removed"]) and rc in world.location_ids}
    progression = {rg for rg, i in item_info().items() if i["progression"]}
    closed = generate.closed_locations(world, locs, progression)
    failures, times = 0, []
    for n in range(count):
        t = time.time()
        try:
            fill.fill(world, locs, fixed, progression, random.Random(n), closed)
            print("seed %d ok in %.1f s" % (n, time.time() - t), flush=True)
        except fill.FillError as e:
            failures += 1
            print("seed %d failed: %s" % (n, e), flush=True)
        times.append(time.time() - t)
    print("%d seeds: %d failed; %.1f s each on average, %.1f s at most" % (count, failures, sum(times) / len(times), max(times)))


if __name__ == "__main__":
    main()
