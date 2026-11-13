"""A port of SoH's reachability search (3drando/fill.cpp: ReachabilitySearch, ProcessRegion, ProcessExits,
UpdateToDAccess, PropagateTimeTravel, AddCheckToLogic; location_access.cpp: Region::ApplyTimePass, UpdateEvents,
LocationAccess/Entrance::ConditionsMet, AnyAgeTime, SpiritShared, SpiritCertainAccess, CanPlantBean, GetCheckPrice,
GetWalletCapacity) over the generated region graph (soh_regions).

As SoH tracks it, each region has four access bits (child/adult x day/night); a rule is evaluated once per bit the
region has, with Logic.IsChild/IsAdult/AtDay/AtNight set to that one; a region whose scene lets time pass gives its
ages both times, and gives them to Root (so the warp songs and spawns carry both times); Root gains the other age from
beyond the Door of Time (PropagateTimeTravel). Events, once met, stay set. The processing order is SoH's (regions in
pool order, an exit's newly reached region processed at once, recursively), as some rules (AnyAgeTime, SpiritShared)
read the access bits of the moment.

Settings (logic.SETTINGS) are those of SoH with the game's vanilla behavior: no entrance shuffle, so the whole of
ValidateEntrances' sphere-zero machinery is off (ResetLogic sets haveTimeAccess etc. true)."""
import collections
import sys

from . import logic as logic_mod
from . import soh_data as D
from . import soh_regions as R
from .translate import compile_rule, cpp_to_py

SPIRIT_TEMPLE = "SCENE_SPIRIT_TEMPLE"


class WorldError(Exception):
    pass


class _Access:
    __slots__ = ("childDay", "childNight", "adultDay", "adultNight", "addedToPool")

    def __init__(self):
        self.childDay = self.childNight = self.adultDay = self.adultNight = False
        self.addedToPool = False

    def Child(self):
        return self.childDay or self.childNight

    def Adult(self):
        return self.adultDay or self.adultNight


class _Region:
    __slots__ = ("key", "name", "scene", "time_pass", "events", "locations", "exits")

    def __init__(self, key, name, scene, time_pass, events, locations, exits):
        self.key, self.name, self.scene, self.time_pass = key, name, scene, time_pass
        self.events, self.locations, self.exits = events, locations, exits


class _RegionRef:
    """areaTable[RR] as rules use it (.AnyAgeTime)"""

    def __init__(self, search, rr):
        self.search = search
        self.rr = rr

    def AnyAgeTime(self, condition):
        return self.search.any_age_time(self.rr, condition)


class _Search:
    """one search: the Logic, region access, events, the locations added to the pool (SoH's ItemLocation
    IsAddedToPool); also the free functions rules call (F.*)"""

    def __init__(self, world, items, placed):
        self.world = world
        self.L = logic_mod.Logic(world.ctx)
        self.C = world.ctx
        self.placed = placed or {}
        self.L.PlacedItem = lambda rc: self.placed.get(rc, "RG_NONE")
        self.access = {rr: _Access() for rr in world.regions}
        self.added = set()
        self.pool = []
        self.updated = False
        self.pending = []          # (locations whose placed items wait for the next sphere)
        self.hold_items = False
        # (ResetLogic: ApplyStartingInventory (empty with these settings: starting_inventory.cpp), AccessReset)
        for rg in sorted(items, key=lambda r: D.ENUM_VALUE[r]):
            if rg not in D.ITEMS:
                raise WorldError(f"unknown item {rg}")
            for _ in range(items[rg]):
                self.L.ApplyEffect(rg)
        root = self.access["RR_ROOT"]
        if self.C.GetOption("RSK_SELECTED_STARTING_AGE").Is("RO_AGE_CHILD"):
            root.childDay = True
        else:
            root.adultDay = True
        root.addedToPool = True
        self.pool.append("RR_ROOT")

    # ---- free functions of rules (location_access.h)

    def Region(self, rr):
        if rr not in self.world.regions:
            raise WorldError(f"areaTable[{rr}]: not a region of the vanilla graph")
        return _RegionRef(self, rr)

    def any_age_time(self, rr, condition):
        L = self.L
        a = self.access[rr]
        pastAdult, pastChild = L.IsAdult, L.IsChild
        L.IsChild = a.Child()
        L.IsAdult = a.Adult()
        hereVal = bool(condition()) and (L.IsAdult or L.IsChild)
        L.IsChild = pastChild
        L.IsAdult = pastAdult
        return hereVal

    def AnyAgeTime(self, condition):
        if self.L.CurrentRegionKey == "RR_NONE":
            raise WorldError("AnyAgeTime outside a region")
        return self.any_age_time(self.L.CurrentRegionKey, condition)

    def _spirit(self, rr):
        try:
            return self.world.spirit[rr]
        except KeyError:
            raise WorldError(f"spiritLogicData has no {rr}") from None

    def SpiritCertainAccess(self, region):
        L, C = self.L, self.C
        childKeys, childRevKeys, adultKeys, adultRevKeys, childAccess, adultAccess, reverseAccess = self._spirit(region)

        def call(fn):
            return bool(fn(L, C, self))
        if L.IsChild:
            keys, revKeys = childKeys, childRevKeys
            knownFrontAccess = L.Get("LOGIC_FORWARDS_SPIRIT_CHILD") or not L.IsReverseAccessPossible()
            # (If we have enough keys that an age cannot be kept out, we have Certain Access; otherwise if we have
            #  entered in reverse and can reach from the face, we have Certain Access)
            return ((knownFrontAccess and call(childAccess)) and L.SmallKeys(SPIRIT_TEMPLE, keys)) or \
                ((L.Get("LOGIC_REVERSE_SPIRIT_CHILD") and call(reverseAccess)) and
                 L.SmallKeys(SPIRIT_TEMPLE, revKeys)) or \
                (call(childAccess) and call(reverseAccess) and
                 L.SmallKeys(SPIRIT_TEMPLE, keys if keys > revKeys else revKeys))
        keys, revKeys = adultKeys, adultRevKeys
        knownFrontAccess = L.Get("LOGIC_FORWARDS_SPIRIT_ADULT") or not L.IsReverseAccessPossible()
        return ((knownFrontAccess and call(adultAccess)) and L.SmallKeys(SPIRIT_TEMPLE, keys)) or \
            ((L.Get("LOGIC_REVERSE_SPIRIT_ADULT") and call(reverseAccess)) and L.SmallKeys(SPIRIT_TEMPLE, revKeys)) or \
            (call(adultAccess) and call(reverseAccess) and
             L.SmallKeys(SPIRIT_TEMPLE, keys if keys > revKeys else revKeys))

    def SpiritShared(self, region, condition, anyAge=False, otherRegion="RR_NONE", otherCondition=lambda: False,
                     thirdRegion="RR_NONE", thirdCondition=lambda: False):
        L, C = self.L, self.C
        cur = self._spirit(region)

        def call(fn):
            return bool(fn(L, C, self))

        def data(rr, i):
            return call(self._spirit(rr)[i])
        result = False
        pastAdult, pastChild = L.IsAdult, L.IsChild
        L.IsChild, L.IsAdult = True, False
        ChildCertainAccess = self.SpiritCertainAccess(region)
        L.IsChild, L.IsAdult = False, True
        AdultCertainAccess = self.SpiritCertainAccess(region)
        if region not in self.access:
            raise WorldError(f"SpiritShared: {region} is not a region of the vanilla graph")
        a = self.access[region]
        IRAP = L.IsReverseAccessPossible
        if anyAge and (ChildCertainAccess or AdultCertainAccess):
            L.IsChild, L.IsAdult = ChildCertainAccess, AdultCertainAccess
            result = bool(condition())
        elif a.Child() and pastChild:
            L.IsChild, L.IsAdult = True, False
            result = bool(condition())
            if not ChildCertainAccess and result:
                L.IsChild, L.IsAdult = False, True
                # (SoH writes `curRegionData.reverseAccess` here without calling it: a non-null function pointer,
                #  true; the adult and other/third terms call theirs)
                result = (call(cur[5]) and (not IRAP() or True) and bool(condition())) or \
                    (otherRegion != "RR_NONE" and (data(otherRegion, 5) and
                                                   (not IRAP() or data(otherRegion, 6)) and bool(otherCondition()))) or \
                    (thirdRegion != "RR_NONE" and (data(thirdRegion, 5) and
                                                   (not IRAP() or data(thirdRegion, 6)) and bool(thirdCondition())))
        elif a.Adult() and pastAdult:
            result = bool(condition())
            if not AdultCertainAccess and result:
                L.IsChild, L.IsAdult = True, False
                result = (call(cur[4]) and (not IRAP() or call(cur[6])) and bool(condition())) or \
                    (otherRegion != "RR_NONE" and (data(otherRegion, 4) and
                                                   (not IRAP() or data(otherRegion, 6)) and bool(otherCondition()))) or \
                    (thirdRegion != "RR_NONE" and (data(thirdRegion, 4) and
                                                   (not IRAP() or data(thirdRegion, 6)) and bool(thirdCondition())))
        L.IsChild, L.IsAdult = pastChild, pastAdult
        return result

    def CanPlantBean(self, bean):
        L = self.L
        return L.HasItem(bean) and L.GetAmmo("ITEM_BEAN") > 0 and \
            (L.IsChild or bool(self.C.GetOption("RSK_SKIP_PLANTING_BEANS")))

    def GetWalletCapacity(self):
        L = self.L
        if L.HasItem("RG_TYCOON_WALLET"):
            return 999
        if L.HasItem("RG_GIANT_WALLET"):
            return 500
        if L.HasItem("RG_ADULT_WALLET"):
            return 200
        if L.HasItem("RG_CHILD_WALLET"):
            return 99
        return 0

    def GetCheckPrice(self, check="RC_UNKNOWN_CHECK"):
        rc = check if check != "RC_UNKNOWN_CHECK" else self.L.CurrentCheckKey
        return self.world.price(rc, self.placed.get(rc, "RG_NONE"))

    def DMCPadToPots(self):
        raise WorldError("DMCPadToPots(): declared in location_access.h, defined nowhere in SoH (rules use "
                         "logic->DMCPadToPots())")

    # ---- the search (fill.cpp)

    def condition_at(self, fn, age, time):
        # (CheckConditionAtAgeTime: one age and one time set, the others cleared; RSK_NO_LOGIC off)
        L = self.L
        L.IsChild = age == "child"
        L.IsAdult = age == "adult"
        L.AtDay = time == "day"
        L.AtNight = time == "night"
        return fn(L, self.C, self)

    def met(self, fn, a):
        c = self.condition_at
        return (a.childDay and c(fn, "child", "day")) or (a.childNight and c(fn, "child", "night")) or \
            (a.adultDay and c(fn, "adult", "day")) or (a.adultNight and c(fn, "adult", "night"))

    def apply_time_pass(self, region, a):
        if region.time_pass:
            root = self.access["RR_ROOT"]
            if a.Child():
                a.childDay = a.childNight = True
                root.childDay = root.childNight = True
            if a.Adult():
                a.adultDay = a.adultNight = True
                root.adultDay = root.adultNight = True

    def update_events(self, region, a):
        updated = False
        for ev, fn, _, _ in region.events:
            if self.L.Get(ev):
                continue
            if self.met(fn, a):
                self.L.Set(ev, True)
                updated = True
        return updated

    def update_tod_access(self, fn, parent, conn):
        c = self.condition_at
        changed = False
        if not conn.childDay and parent.childDay and c(fn, "child", "day"):
            conn.childDay = changed = True
        if not conn.childNight and parent.childNight and c(fn, "child", "night"):
            conn.childNight = changed = True
        if not conn.adultDay and parent.adultDay and c(fn, "adult", "day"):
            conn.adultDay = changed = True
        if not conn.adultNight and parent.adultNight and c(fn, "adult", "night"):
            conn.adultNight = changed = True
        return changed

    def process_exits(self, region, a):
        for to, fn, _, _ in region.exits:
            conn = self.access[to]
            if self.update_tod_access(fn, a, conn):
                self.updated = True
                if not conn.addedToPool:
                    conn.addedToPool = True
                    self.pool.append(to)
                self.process_region(to)

    def propagate_time_travel(self):
        root = self.access["RR_ROOT"]
        beyond = self.access["RR_TOT_BEYOND_DOOR_OF_TIME"]
        # (RANDOTODO in SoH: sphere weirdness, other age locations not propagated in this sphere)
        if not root.Adult() and beyond.Child():
            root.adultDay = beyond.childDay
            root.adultNight = beyond.childNight
            self.process_region("RR_ROOT")
        elif not root.Child() and beyond.Adult():
            root.childDay = beyond.adultDay
            root.childNight = beyond.adultNight
            self.process_region("RR_ROOT")

    def add_check(self, rc, fn, region, a):
        if rc in self.added:
            return
        L = self.L
        L.CurrentCheckKey = rc
        if self.met(fn, a) and not (rc in D.LOCATIONS and L.ShopItemNotForSale(rc)):
            self.added.add(rc)
            item = self.placed.get(rc)
            if item is not None and item != "RG_NONE":
                if self.hold_items:
                    self.pending.append(rc)
                else:
                    L.ApplyEffect(item)
                self.updated = True
        L.CurrentCheckKey = "RC_UNKNOWN_CHECK"

    def process_region(self, rr):
        L = self.L
        region = self.world.regions[rr]
        a = self.access[rr]
        previous = L.CurrentRegionKey
        L.CurrentRegionKey = rr
        self.apply_time_pass(region, a)
        if self.update_events(region, a):
            self.updated = True
        self.process_exits(region, a)
        self.propagate_time_travel()
        for rc, fn, _, _ in region.locations:
            self.add_check(rc, fn, region, a)
        L.CurrentRegionKey = previous

    def run(self):
        """passes over the region pool until one changes nothing (ReachabilitySearch's do/while)"""
        while True:
            self.updated = False
            i = 0
            while i < len(self.pool):
                self.process_region(self.pool[i])
                i += 1
            if not self.updated:
                return


class World:
    """SoH's vanilla (non-MQ) region graph with the settings of logic.SETTINGS, edited for the remake:

    extra_locations: {location_id: (region "RR_*", "C++ expr")}: new locations (remake-only chests), any id string
    rule_overrides: {("location", "RC_X"): "C++ expr", ("exit", "RR_A", "RR_B"): "C++ expr",
                     ("event", "RR_A", "LOGIC_X"): "C++ expr", ("location_region", "RC_X"): "RR_Y",
                     ("add_region", "RR_NEW"): {"name", "like"}, ("add_exit", "RR_A", "RR_B"): "C++ expr",
                     ("add_event", "RR_A", "LOGIC_X"): "C++ expr"}
        replace SoH's rule (or region) for that location / exit / event. A location SoH lists in several regions
        (with each its rule) becomes one entry: in the location_region override's region if given, else SoH's region
        if it has one only (else an error: name the region); with the location override's rule if given, else SoH's
        rule there. An override naming something that does not exist is an error.
    removed_locations: SoH locations the remake does not have (taken out of every region)"""

    def __init__(self, extra_locations=None, rule_overrides=None, removed_locations=()):
        self.ctx = logic_mod.Ctx()
        self.regions = {}
        for rr, r in R.REGIONS.items():
            self.regions[rr] = _Region(rr, r["name"], r["scene"], r["time_pass"],
                                       [(ev, fn, cpp, wh) for ev, (fn, cpp, wh) in r["events"]],
                                       [(rc, fn, cpp, wh) for rc, (fn, cpp, wh) in r["locations"]],
                                       [(to, fn, cpp, wh) for to, (fn, cpp, wh) in r["exits"]])
        self.spirit = {rr: (a, b, c, d, e[0], f[0], g[0]) for rr, (a, b, c, d, e, f, g) in R.SPIRIT_LOGIC_DATA.items()}
        self._edit(extra_locations or {}, rule_overrides or {}, set(removed_locations))
        self.location_ids = set()
        for r in self.regions.values():
            for rc, _, _, _ in r.locations:
                self.location_ids.add(rc)

    @staticmethod
    def compile(expr, where):
        return compile_rule(cpp_to_py(expr, where), where), expr, where

    def _edit(self, extra, overrides, removed):
        # (HookshotRando: what the remake has that SoH does not, before the overrides of what SoH has:
        #  ("add_region", RR): {"name", "like": a SoH region whose scene and time passing it shares};
        #  ("add_exit", RR_A, RR_B) and ("add_event", RR, LOGIC_X): "C++ expr")
        additions = {k: v for k, v in overrides.items() if isinstance(k, tuple) and k and
                     k[0] in ("add_region", "add_exit", "add_event")}
        overrides = {k: v for k, v in overrides.items() if k not in additions}
        for k, v in additions.items():
            if k[0] == "add_region":
                if len(k) != 2 or k[1] in self.regions or not isinstance(v, dict) or v.get("like") not in self.regions:
                    raise WorldError(f"addition {k!r}: a new region needs a new name and an existing 'like' region")
                like = self.regions[v["like"]]
                self.regions[k[1]] = _Region(k[1], v["name"], like.scene, like.time_pass, [], [], [])
        for k, expr in additions.items():
            if k[0] == "add_exit":
                if len(k) != 3 or k[1] not in self.regions or k[2] not in self.regions or \
                        any(to == k[2] for to, _, _, _ in self.regions[k[1]].exits):
                    raise WorldError(f"addition {k!r}: both regions must exist and the exit must be new")
                self.regions[k[1]].exits = list(self.regions[k[1]].exits) + \
                    [(k[2], *self.compile(expr, f"added exit {k[1]} -> {k[2]}"))]
            elif k[0] == "add_event":
                if len(k) != 3 or k[1] not in self.regions or \
                        any(ev == k[2] for ev, _, _, _ in self.regions[k[1]].events):
                    raise WorldError(f"addition {k!r}: the region must exist and the event must be new there")
                self.regions[k[1]].events = list(self.regions[k[1]].events) + \
                    [(k[2], *self.compile(expr, f"added event {k[1]} {k[2]}"))]
        where_of = collections.defaultdict(list)   # (RC: [region])
        for rr, r in self.regions.items():
            for rc, _, _, _ in r.locations:
                where_of[rc].append(rr)
        for rc in removed:
            if rc not in where_of:
                raise WorldError(f"removed location {rc} is not in the region graph")
        for k in overrides:
            if not isinstance(k, tuple) or not k:
                raise WorldError(f"override key {k!r}")
            if k[0] in ("location", "location_region"):
                if len(k) != 2:
                    raise WorldError(f"override key {k!r}")
                if k[1] not in where_of:
                    raise WorldError(f"override {k!r}: {k[1]} is not in the region graph")
                if k[1] in removed:
                    raise WorldError(f"override {k!r}: {k[1]} is also removed")
                if k[0] == "location_region" and overrides[k] not in self.regions:
                    raise WorldError(f"override {k!r}: no region {overrides[k]}")
            elif k[0] == "exit":
                if len(k) != 3 or k[1] not in self.regions or \
                        not any(to == k[2] for to, _, _, _ in self.regions[k[1]].exits):
                    raise WorldError(f"override {k!r}: no such exit")
                if sum(1 for to, _, _, _ in self.regions[k[1]].exits if to == k[2]) != 1:
                    raise WorldError(f"override {k!r}: the exit is listed more than once")
            elif k[0] == "event":
                if len(k) != 3 or k[1] not in self.regions or \
                        not any(ev == k[2] for ev, _, _, _ in self.regions[k[1]].events):
                    raise WorldError(f"override {k!r}: no such event")
                if sum(1 for ev, _, _, _ in self.regions[k[1]].events if ev == k[2]) != 1:
                    raise WorldError(f"override {k!r}: the event is listed more than once in {k[1]}")
            else:
                raise WorldError(f"override key {k!r}: kind {k[0]!r}")
        # (the regions' lists are rebuilt, so shared grotto event lists are not edited through another region)
        for rr, r in self.regions.items():
            r.events = list(r.events)
            r.exits = list(r.exits)
            r.locations = [e for e in r.locations if e[0] not in removed]
        for k, expr in overrides.items():
            if k[0] == "exit":
                r = self.regions[k[1]]
                r.exits = [(to, *self.compile(expr, f"override exit {k[1]} -> {k[2]}")) if to == k[2]
                           else (to, fn, cpp, wh) for to, fn, cpp, wh in r.exits]
            elif k[0] == "event":
                r = self.regions[k[1]]
                r.events = [(ev, *self.compile(expr, f"override event {k[1]} {k[2]}")) if ev == k[2]
                            else (ev, fn, cpp, wh) for ev, fn, cpp, wh in r.events]
        moved = {k[1] for k in overrides if k[0] in ("location", "location_region")}
        for rc in moved:
            regs = where_of[rc]
            rr = overrides.get(("location_region", rc))
            if rr is None:
                if len(set(regs)) != 1:
                    raise WorldError(f"location {rc} is in {len(set(regs))} SoH regions ({', '.join(sorted(set(regs)))})"
                                     f": give its region with a ('location_region', '{rc}') override")
                rr = regs[0]
            if ("location", rc) in overrides:
                entry = (rc, *self.compile(overrides[("location", rc)], f"override location {rc}"))
            else:
                old = [e for e in self.regions[rr].locations if e[0] == rc] if rr in regs else []
                if len(old) == 1:
                    entry = old[0]
                elif len(set(regs)) == 1:
                    entry = [e for e in self.regions[regs[0]].locations if e[0] == rc][0]
                else:
                    raise WorldError(f"location {rc} moved to {rr}: SoH has it in several regions with their own "
                                     f"rules; give its rule with a ('location', '{rc}') override")
            for r in self.regions.values():
                r.locations = [e for e in r.locations if e[0] != rc]
            self.regions[rr].locations.append(entry)
        for loc_id, (rr, expr) in extra.items():
            if loc_id in where_of or loc_id in D.LOCATIONS:
                raise WorldError(f"extra location {loc_id} collides with a SoH location")
            if rr not in self.regions:
                raise WorldError(f"extra location {loc_id}: no region {rr}")
            self.regions[rr].locations.append((loc_id, *self.compile(expr, f"extra location {loc_id}")))

    def price(self, rc, placed_item):
        """(GetCheckPrice -> ItemLocation::GetPrice) a shop item's own price, else the location's vanilla price
        (SoH's vanilla-price settings: SetCustomPrice(GetVanillaPrice()) for scrubs and merchants)"""
        if rc not in D.LOCATIONS:
            raise WorldError(f"GetCheckPrice of {rc}: not a SoH location")
        if placed_item != "RG_NONE" and D.ITEMS[placed_item]["type"] == "ITEMTYPE_SHOP":
            return D.ITEMS[placed_item]["price"]
        return D.LOCATIONS[rc]["price"]

    def _search(self, items, placed=None):
        old = sys.getrecursionlimit()
        sys.setrecursionlimit(max(old, 20000))
        try:
            s = _Search(self, collections.Counter(items), placed)
            s.run()
        finally:
            sys.setrecursionlimit(old)
        return s

    def reachable(self, items):
        """the location ids reachable with these items (a Counter of RG_* names, progressive items as counts), with
        every event obtainable from them resolved to a fixpoint"""
        return set(self._search(items).added)

    def collect(self, items, placed):
        """(Counter of the final items, [set of location ids per sphere]): starting from `items`, collect the items
        at reachable `placed` locations ({location id: RG_*}) until nothing new; a sphere is the placed locations
        reachable with the items of the spheres before it (SoH's GeneratePlaythrough holds items to the next loop
        the same way; its own spheres can split one of these where a pass misses access gained later in it)"""
        for loc, rg in placed.items():
            if loc not in self.location_ids:
                raise WorldError(f"placed location {loc} is not in the region graph")
            if rg not in D.ITEMS:
                raise WorldError(f"placed item {rg} at {loc}: unknown item")
        old = sys.getrecursionlimit()
        sys.setrecursionlimit(max(old, 20000))
        try:
            final = collections.Counter(items)
            s = _Search(self, final, placed)
            s.hold_items = True
            spheres = []
            while True:
                s.run()
                if not s.pending:
                    break
                sphere = set(s.pending)
                for loc in s.pending:
                    s.L.ApplyEffect(placed[loc])
                    final[placed[loc]] += 1
                s.pending = []
                spheres.append(sphere)
        finally:
            sys.setrecursionlimit(old)
        return final, spheres

    def can_beat(self, items):
        """SoH's win condition (RSK_WINCON defeat Ganon: the Triforce at RC_GANON) reachable with these items"""
        if "RC_GANON" not in self.location_ids:
            raise WorldError("RC_GANON (the win condition) is not in the region graph")
        return "RC_GANON" in self.reachable(items)


def vanilla_items():
    """{RC: RG}: SoH's vanilla item (location tables) of every non-MQ location that has one (RG_NONE left out)"""
    return {rc: loc["item"] for rc, loc in D.LOCATIONS.items()
            if loc["quest"] != "RCQUEST_MQ" and loc["item"] != "RG_NONE"}


def _is_advancement(rg, ctx):
    # (Item::IsAdvancement)
    it = D.ITEMS[rg]
    if not it["advancement"] and rg in ("RG_DEKU_SHIELD", "RG_HYLIAN_SHIELD") and \
            ctx.GetOption("RSK_SHOP_SHIELDS_AND_TUNICS_ONLY_REFILL").Is("RO_GENERIC_ON"):
        return True
    return it["advancement"]


def _is_major(rg, ctx):
    # (Item::IsMajorItem: what hints count as major)
    it = D.ITEMS[rg]
    t = it["type"]
    O = ctx.GetOption
    if t == "ITEMTYPE_TOKEN":
        return O("RSK_RAINBOW_BRIDGE").Is("RO_BRIDGE_TOKENS") or ctx.GBKCondition() == "RO_CHECK_TRIGGER_TOKENS"
    if t in ("ITEMTYPE_DROP", "ITEMTYPE_EVENT", "ITEMTYPE_SHOP", "ITEMTYPE_MAP", "ITEMTYPE_COMPASS"):
        return False
    if t == "ITEMTYPE_DUNGEONREWARD" and O("RSK_SHUFFLE_DUNGEON_REWARDS").Is("RO_DUNGEON_REWARDS_END_OF_DUNGEON"):
        return False
    if rg in ("RG_BOMBCHU_5", "RG_BOMBCHU_10", "RG_BOMBCHU_20") and O("RSK_BOMBCHU_BAG").Is("RO_BOMBCHU_BAG_NONE"):
        return False
    if rg in ("RG_HEART_CONTAINER", "RG_PIECE_OF_HEART", "RG_TREASURE_GAME_HEART"):
        return False
    vanilla_or_own = ("RO_DUNGEON_ITEM_LOC_VANILLA", "RO_DUNGEON_ITEM_LOC_OWN_DUNGEON")
    if t == "ITEMTYPE_SMALLKEY" and any(O("RSK_KEYSANITY").Is(v) for v in vanilla_or_own):
        return False
    if t == "ITEMTYPE_FORTRESS_SMALLKEY" and O("RSK_GERUDO_KEYS").Is("RO_GERUDO_KEYS_VANILLA"):
        return False
    # (SoH tests getItemId 0xAD for Ganon's Boss Key; in this item table 0xAD is the Bottom of the Well map and
    #  Ganon's Boss Key is 0x9A, so it is a boss key like the others here: ported as written)
    gid = int(it["getItemId"], 0) if it["getItemId"][:1].isdigit() else None
    if t == "ITEMTYPE_BOSSKEY" and gid != 0xAD and any(O("RSK_BOSS_KEYSANITY").Is(v) for v in vanilla_or_own):
        return False
    if gid == 0xAD and (O("RSK_GANONS_BOSS_KEY").Is("RO_GANON_BOSS_KEY_VANILLA") or
                        O("RSK_GANONS_BOSS_KEY").Is("RO_GANON_BOSS_KEY_OWN_DUNGEON")):
        return False
    if rg == "RG_GREG_RUPEE":
        return O("RSK_RAINBOW_BRIDGE").Is("RO_BRIDGE_GREG")
    return _is_advancement(rg, ctx)


def item_info():
    """{RG: {name, type (ITEMTYPE_*), progression (Item::IsAdvancement: what logic and playthroughs track), major
    (Item::IsMajorItem: what hints treat as major, with these settings), category (ITEM_CATEGORY_*), logicVal,
    price}} of SoH's item table (item_list.cpp)"""
    ctx = logic_mod.Ctx()
    out = {}
    for rg, it in D.ITEMS.items():
        out[rg] = {"name": it["name"], "type": it["type"], "progression": _is_advancement(rg, ctx),
                   "major": _is_major(rg, ctx), "category": it["category"], "logicVal": it["logicVal"],
                   "price": it["price"]}
    return out
