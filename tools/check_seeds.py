"""Many seeds in a row, each filled and verified (beatable, every check in logic reachable, the ORDERED pairs in order, the
upgrade tiers assigned), as generate makes them, without writing a mod: how often a seed needs more than one attempt, and that
none fails.

    python tools/check_seeds.py <romfs> <count> [--chests-only]"""
import collections
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando import fill, generate  # noqa: E402
from rando import items as I  # noqa: E402
from rando.formats import zs  # noqa: E402


def main():
    romfs, count = sys.argv[1], int(sys.argv[2])
    s = generate.Setup(romfs, zs.Codec(romfs), with_gifts="--chests-only" not in sys.argv)
    kinds = collections.Counter(l.kind for l in s.locs)
    print("locations: %s; %d not in logic (junk only)" % (dict(kinds), len(s.closed)))
    failures, times = 0, []
    where = collections.Counter()
    for n in range(count):
        t = time.time()
        try:
            rng = random.Random(n)
            placed = generate.assign_tiers(s, s.fill(rng), rng)
            by_id = {l.id: l for l in s.locs}
            for lid, a in placed.items():   # (every item where its kind of location can hold it)
                if not I.allowed(a, by_id[lid].kind):
                    raise fill.FillError("%s in %s" % (a, by_id[lid].name))
                if by_id[lid].kind != "chest" and I.soh_item(a, by_id[lid].map) in s.progression:
                    where[by_id[lid].kind] += 1
            print("seed %d ok in %.1f s" % (n, time.time() - t), flush=True)
        except fill.FillError as e:
            failures += 1
            print("seed %d failed: %s" % (n, e), flush=True)
        times.append(time.time() - t)
    print("%d seeds: %d failed; %.1f s each on average, %.1f s at most" % (count, failures, sum(times) / len(times), max(times)))
    print("progression items placed outside chests, per seed: %s" % {k: round(v / count, 1) for k, v in where.items()})


if __name__ == "__main__":
    main()
