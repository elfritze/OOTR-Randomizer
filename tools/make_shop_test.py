"""A shop pilot on an installed seed: its mod as it is (every file copied, nothing rebuilt: today's logic would fill the same
seed otherwise), with three of the Kokiri shop's shelves sold once as rando.shops makes them (Shopsanity's own code), and
the shop's whole stock shown:

    the Recovery Heart shelf:   a Red Rupee for 10
    the Deku Seeds (10) shelf:  a Heart Piece for 20
    the Deku Seeds (30) shelf:  the large Deku Stick bag for 30 (the largest: buying it never lowers a capacity)

Also, for a seed with Saria's gift shuffled made before the fix: the ocarina's first play event listed by every event loading
ActionGuide (rando.patches.ocarina_child_events: a Fairy Ocarina found elsewhere could not be equipped); with the night
skulltulas made day and night, their logic module no longer deleting them by day (rando.qol.night_module_by_day).

To see: each shelf shows the item's model, name and price; buying gives the item; then "Sold Out" on that shelf, and
still after leaving the shop and after reloading the save; the other shelves sell as before.

    python tools/make_shop_test.py <romfs> <installed mod folder (HookshotRando)> <new mod folder>"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando import pickups, shops  # noqa: E402
from rando.formats import restbl, zs  # noqa: E402
from rando.mod import RSTB, Mod  # noqa: E402

PILOT = {0: ("TBox_Rupee_Red", 10), 1: ("Obj_Heart_Piece", 20), 2: ("Item_StickBag_Large", 30)}   # (Kokiri order: item, price)


class OnTop(Mod):
    """a Mod whose files start as an installed mod's (its size table too)"""

    def __init__(self, romfs, codec, base_romfs, out_romfs):
        super().__init__(romfs, codec, out_romfs)
        self.base = base_romfs
        path = os.path.join(base_romfs, *RSTB.split("/"))
        if os.path.exists(path):
            self.table = restbl.Table(codec.read(path))
            self.grown.append((RSTB, 0, 0))   # (the table is shipped: the installed mod's entries are needed)

    def read(self, rel):
        path = os.path.join(self.base, *rel.split("/"))
        if rel not in self.data and os.path.exists(path):
            return self.codec.read(path) if rel.endswith(".zs") else open(path, "rb").read()
        return super().read(rel)


def main():
    romfs, base, out = sys.argv[1], sys.argv[2], sys.argv[3]
    codec = zs.Codec(romfs)
    if os.path.exists(out):
        raise SystemExit("%s exists" % out)
    shutil.copytree(base, out)
    mod = OnTop(romfs, codec, os.path.join(base, "romfs"), os.path.join(out, "romfs"))
    made = pickups.Pickups(romfs, codec, mod)
    slots = [s for s in shops.scan(romfs, codec, read=mod.read) if s.code == "KF" and s.order in PILOT]
    b = shops.Builder(romfs, codec, mod, made)
    shelves = [(s, b.shelf(s, *PILOT[s.order])) for s in slots]
    shops.write(romfs, codec, mod, shelves)
    made.finish()
    b.finish()
    plan = json.load(open(os.path.join(out, "placements.json"), encoding="utf-8"))
    if "RC_LW_GIFT_FROM_SARIA" in plan.get("gifts", {}):   # (the ocarina's play event, missing from seeds before the fix)
        from rando import events, patches
        from rando.formats import byml
        raw = mod.read(events.GAME_ANALYZED_EVENT_INFO)
        rows, version = byml.read(raw)
        if patches.ocarina_child_events(rows):
            mod.write(events.GAME_ANALYZED_EVENT_INFO, byml.write(rows, version, byml.endian(raw)))
            print("ocarina: its play event listed by the item gets' events")
    if plan.get("settings", {}).get("skulltulas_day_and_night"):   # (the night skulltulas' module, missing before its fix)
        from rando import qol
        game = mod.read(qol.NIGHT_MODULE) if qol.NIGHT_MODULE not in mod.data else None
        if game is not None and game == open(os.path.join(romfs, *qol.NIGHT_MODULE.split("/")), "rb").read():
            mod.write(qol.NIGHT_MODULE, qol.night_module_by_day(game))
            print("night skulltulas: their logic module no longer deletes them by day")
    mod.finish()
    plan_path = os.path.join(out, "placements.json")
    plan = json.load(open(plan_path, encoding="utf-8"))
    plan["shop_pilot"] = {s.rc: {"item": PILOT[s.order][0], "price": PILOT[s.order][1], "shelf": actor, "flag": s.flag}
                          for s, actor in shelves}
    with open(plan_path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=1)
    for s, actor in shelves:
        print("%s: %s for %d (%s)" % (s.name, PILOT[s.order][0], PILOT[s.order][1], actor))


if __name__ == "__main__":
    main()
