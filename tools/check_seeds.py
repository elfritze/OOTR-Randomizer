"""Many seeds in a row, each filled and verified (beatable, every check in logic reachable, the ORDERED pairs in order, the
upgrade tiers assigned), as generate makes them, without writing a mod: how often a seed needs more than one attempt, and that
none fails.

    python tools/check_seeds.py <romfs> <count> [--chests-only] [--dungeon-items <place>]

--dungeon-items: maps and compasses, small keys and boss keys all where <place> lets them (own_dungeon, any_dungeon,
overworld, anywhere), or one place each: <maps and compasses>,<small keys>,<boss keys>; each item is checked to be where
its setting lets it.
--set KEY=VALUE (any number): another setting (rando.settings), e.g. --set shuffle_dungeon_rewards=end_of_dungeon."""
import collections
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando import fill, generate  # noqa: E402
from rando import items as I  # noqa: E402
from rando import settings as rando_settings  # noqa: E402
from rando.formats import zs  # noqa: E402


def main():
    romfs, count = sys.argv[1], int(sys.argv[2])
    place = sys.argv[sys.argv.index("--dungeon-items") + 1] if "--dungeon-items" in sys.argv else "own_dungeon"
    keys = ("shuffle_maps_compasses", "shuffle_small_keys", "shuffle_boss_keys")
    chosen = dict(zip(keys, place.split(","))) if "," in place else {k: place for k in keys}
    for i, a in enumerate(sys.argv):
        if a == "--set":
            k, _, v = sys.argv[i + 1].partition("=")
            chosen[k] = {"true": True, "false": False}.get(v.lower(), v)
    s = generate.Setup(romfs, zs.Codec(romfs), with_gifts="--chests-only" not in sys.argv,
                       settings=rando_settings.normalized(chosen))
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
                if not I.fits(a, lid, by_id[lid].kind):
                    raise fill.FillError("%s in %s" % (a, by_id[lid].name))
                own = I.dungeon_item(a)
                if own and not fill.PLACES[s.places[own[0]]](own[1], by_id[lid]):
                    raise fill.FillError("%s in %s (%s)" % (a, by_id[lid].name, place))
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
