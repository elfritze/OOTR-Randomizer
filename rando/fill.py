"""Placing the chests' items so that the game can be finished, as SoH fills (fill.cpp): dungeon items first, in their own dungeon;
then the progression items by assumed fill (each placed where it is reachable with every item not yet placed); then the rest.
A seed is checked by playing it from a new game (World.collect) and drawn again when it fails."""
import collections

from . import items as I


class FillError(Exception):
    pass


class Location:
    """one randomized chest: id (its SoH check, or CHEST_<hash> for one SoH does not have), hash, map, vanilla actor"""
    def __init__(self, id, hash, remake_map, vanilla, name):
        self.id, self.hash, self.map, self.vanilla, self.name = id, hash, remake_map, vanilla, name
        self.dungeon = remake_map if remake_map in I.DUNGEONS else None


def _soh(actor, loc):
    return I.soh_item(actor, loc.map)


def fill(world, locations, fixed, progression, rng, closed=(), attempts=20):
    """locations: [Location]; fixed: {location id: RG} for the checks the randomizer leaves as they are (they count in logic);
    progression: the set of RG items that matter to logic; closed: the ids of locations logic does not reach even with every
    item (a remake chest whose way in is not known yet): they get items logic does not need. Returns {location id: actor}."""
    last = None
    for _ in range(attempts):
        try:
            placed = _attempt(world, locations, fixed, progression, rng, set(closed))
            _verify(world, [l for l in locations if l.id not in closed], fixed, placed)
            return placed
        except FillError as e:
            last = e
    raise FillError("no beatable seed in %d attempts: %s" % (attempts, last))


def _items_of(placed, by_id):
    """{location id: RG} of the placed items logic counts (the remake's own collectible counts as nothing: RG_NONE)"""
    out = {lid: _soh(actor, by_id[lid]) for lid, actor in placed.items()}
    return {lid: rg for lid, rg in out.items() if rg != "RG_NONE"}


def _reachable(world, fixed, owned, placed, by_id):
    """the locations reachable with owned plus whatever fixed and already placed items that brings in"""
    have, _ = world.collect(collections.Counter(owned), {**fixed, **_items_of(placed, by_id)})
    return world.reachable(have)


KEYS = ("Item_Dungeon_SmallKey", "Item_Dungeon_BossKey")


def _reach_without(world, rg, owned, fixed, placed_items):
    """the locations reachable with none of rg from anywhere: owned, the fixed checks or the placed items"""
    owned = collections.Counter({k: v for k, v in owned.items() if k != rg})
    items = {lid: x for lid, x in {**fixed, **placed_items}.items() if x != rg}
    have, _ = world.collect(owned, items)
    return world.reachable(have)


def _attempt(world, locations, fixed, progression, rng, closed):
    """1. each dungeon's keys forward: its k-th small key where it is reachable with the k-1 placed before it (every other
    item counted as owned), then its boss key; SoH's key rules count the worst case, so this order always opens.
    2. maps and compasses anywhere in their dungeon (logic does not use them). 3. the second of each ORDERED pair, where it
    is reachable only with the first; then every other progression item by assumed fill. 4. the rest anywhere."""
    by_id = {l.id: l for l in locations}
    pool = [(l.vanilla, l) for l in locations]   # (an actor and the location it came from: a dungeon item stays in its dungeon)
    placed = {}
    for lid, choices in I.ONE_OF.items():   # (a room's way out drawn first, from the pool)
        if lid not in by_id:
            continue
        entry = rng.choice([(a, o) for a, o in pool if a in choices])
        pool.remove(entry)
        placed[lid] = entry[0]
    empty = [l for l in locations if l.id not in closed and l.id not in placed]
    junk_only = [l for l in locations if l.id in closed]
    rng.shuffle(empty)

    def is_prog(actor, origin):
        return _soh(actor, origin) in progression

    keys = [(a, o) for a, o in pool if a in KEYS]
    other_dungeon = [(a, o) for a, o in pool if I.dungeon_bound(a) and a not in KEYS]
    prog = [(a, o) for a, o in pool if not I.dungeon_bound(a) and is_prog(a, o)]
    rest = [(a, o) for a, o in pool if not I.dungeon_bound(a) and not is_prog(a, o)]
    rng.shuffle(prog)

    def reach(owned, fixed_=fixed):
        have, _ = world.collect(collections.Counter(owned), {**fixed_, **_items_of(placed, by_id)})
        return world.reachable(have)

    def put(item, origin, spots):
        if not spots:
            raise FillError("nowhere reachable for %s (from %s)" % (item, origin.name))
        spot = rng.choice(spots)
        placed[spot.id] = item
        (empty if spot in empty else junk_only).remove(spot)

    def counted(items):
        return collections.Counter(_soh(a, o) for a, o in items)

    def without(rg, owned):
        """the locations reachable with owned and everything placed and fixed, none of it rg (an ammunition's container)"""
        return _reach_without(world, rg, owned, fixed, _items_of(placed, by_id))

    def container_spots(item, owned, spots):
        rg = I.NEEDS_CONTAINER.get(item)
        if rg is None:
            return spots
        open_without = without(rg, owned)
        return [l for l in spots if l.id not in open_without]

    # 1. keys
    by_dungeon = collections.defaultdict(list)
    for a, o in keys:
        by_dungeon[o.map].append((a, o))
    order = sorted(by_dungeon)
    rng.shuffle(order)
    for i, d in enumerate(order):
        later = [k for dd in order[i + 1:] for k in by_dungeon[dd]]   # (the dungeons still to fill: their keys assumed)
        for item, origin in sorted(by_dungeon[d], key=lambda k: k[0] != "Item_Dungeon_SmallKey"):
            r = reach(counted(prog) + counted(later))
            put(item, origin, [l for l in empty if l.map == d and l.id in r])
    # 2. maps and compasses
    for item, origin in other_dungeon:
        put(item, origin, [l for l in empty + junk_only if l.map == origin.map])
    # 3. the ORDERED pairs' second items, then the rest of the progression
    seconds = [s for _, s in I.ORDERED][::-1]   # (Gold before Silver: Silver is itself the second of ORDERED_FIXED)
    for second in seconds + [s for _, s in I.ORDERED_FIXED if s not in seconds]:
        entry = next(((a, o) for a, o in prog if a == second), None)
        if entry is None:
            continue
        prog.remove(entry)
        owned = counted(prog)
        r = reach(owned)
        firsts = [f for f, s in I.ORDERED if s == second and any(a == f for a, _ in prog)]
        blocked = set()
        for f in firsts:   # (where it is not reachable without the first: one count of the first's item less)
            fo = next(o for a, o in prog if a == f)
            less = owned.copy()
            less[_soh(f, fo)] -= 1
            blocked |= {l.id for l in empty} - reach(+less)
        for rc, s in I.ORDERED_FIXED:
            if s == second and rc in fixed:
                blocked_fixed = {l.id for l in empty} - reach(owned, {k: v for k, v in fixed.items() if k != rc})
                blocked = blocked & blocked_fixed if firsts else blocked_fixed
        put(entry[0], entry[1], [l for l in empty if l.id in r and l.id in blocked])
    while prog:
        item, origin = prog.pop()
        owned = counted(prog)
        r = reach(owned)   # (assumed fill: every item still to place counts as owned)
        put(item, origin, container_spots(item, owned, [l for l in empty if l.id in r]))
    # 4. the rest: the ammunition first, where its container is needed
    rng.shuffle(rest)
    rest.sort(key=lambda x: x[0] not in I.NEEDS_CONTAINER)
    for item, origin in rest:
        spots = empty + junk_only
        if item in I.NEEDS_CONTAINER:
            put(item, origin, container_spots(item, collections.Counter(), spots))
        else:
            put(item, origin, spots)
    if len(placed) != len(locations):
        raise FillError("%d locations for %d items" % (len(locations), len(placed)))
    return placed


def _verify(world, locations, fixed, placed):
    """the seed played from a new game: beatable, every location (but the closed ones) reachable, and the ORDERED pairs
    come in order"""
    by_id = {l.id: l for l in locations}
    every = {**fixed, **_items_of({k: v for k, v in placed.items() if k in by_id}, by_id)}
    have, spheres = world.collect(collections.Counter(), every)
    if not world.can_beat(have):
        raise FillError("not beatable")
    reach = world.reachable(have)
    missed = [l.name for l in locations if l.id not in reach]
    if missed:
        raise FillError("unreachable: %s" % ", ".join(missed[:5]))
    where = {actor: lid for lid, actor in placed.items()}
    for first, second in I.ORDERED:
        if first not in where or second not in where:
            continue
        # (the second may not be reachable while the first is still in its chest)
        without = {lid: rg for lid, rg in every.items() if lid != where[first]}
        have_without, _ = world.collect(collections.Counter(), without)
        if where[second] in world.reachable(have_without):
            raise FillError("%s can be had before %s" % (second, first))
    for lid, actor in placed.items():
        rg = I.NEEDS_CONTAINER.get(actor)
        if rg and lid in by_id and lid in _reach_without(world, rg, collections.Counter(), fixed, _items_of(
                {k: v for k, v in placed.items() if k in by_id}, by_id)):
            raise FillError("%s can be had without its container (%s)" % (actor, by_id[lid].name))
    for first_rc, second in I.ORDERED_FIXED:
        if second not in where or first_rc not in every:
            continue
        without = {lid: rg for lid, rg in every.items() if lid != first_rc}
        have_without, _ = world.collect(collections.Counter(), without)
        if where[second] in world.reachable(have_without):
            raise FillError("%s can be had before %s's item" % (second, first_rc))
    return spheres
