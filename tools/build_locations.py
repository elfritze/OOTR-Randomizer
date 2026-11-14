"""data/locations.json from the research (research/mapping/*.json: each remake chest against SoH's checks) and the decisions
below; data/overrides.json (written by hand from the mappings' divergences) is merged in as it is.

    python tools/build_locations.py <romfs>

Checks the result against the game's maps: every one-time chest is a location (or a copy of one), each once."""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, ROOT)
import re  # noqa: E402

from rando import chests  # noqa: E402
from rando.formats import zs  # noqa: E402
from rando.logic import soh_regions as R  # noqa: E402

SOH = os.path.join(ROOT, "..", "Shipwright", "soh", "soh", "Enhancements", "randomizer", "location_list.cpp")


def soh_names():
    """{RC: SoH's display name} from location_list.cpp (each location's first string argument)"""
    with open(SOH, encoding="utf-8") as h:
        text = h.read()
    return {m.group(1): m.group(2) for m in re.finditer(r'locationTable\[(RC_\w+)\]\s*=\s*Location::\w+\([^"]*"([^"]*)"', text)}

# Minigame chests filled again at each play (IsEnableRepeatOpen, or the race's consolation): not one-time checks, as SoH
# has them. The Hall of Fallen Foes' 10 (DreamWorld, a chest between boss battles), the treasure chest game's but its Heart
# Piece prize, Dampe's race's rupee chests.
REPEAT_KEPT = {16881481538337649070}   # (the treasure chest game's Heart Piece prize: RC_MARKET_TREASURE_CHEST_GAME_REWARD)
RACE_CONSOLATION = {234006393181394602, 4322670163630771947}

# One chest placed twice (two maps, or two states of a map), each copy with its own Hash: one location, the same item in both.
COPIES = {
    4349272251343787229: [17479747339356189279],   # (Lost Woods under the bridge: KokiriForest's and LostWood's maps)
    11929552275106311978: [13080955777249750889],   # (Kakariko windmill top: the adult map and its alternative state)
    18413589940135955604: [6205043616869463865],   # (GV storms grotto invisible chest: adult and child)
}

# Remake chests that are SoH checks other than chests (soh_rc null in the mappings), and the chests with no Drop__DropActor
# (not in the mappings): (hash: (SoH check, its region, the rule in the remake or None for SoH's own))
EXTRA_RC = {
    5534919361313859554: ("RC_GRAVEYARD_DAMPE_RACE_FREESTANDING_POH", None, None),   # (a big chest in the remake)
    15856256242099990922: ("RC_GV_CRATE_FREESTANDING_POH", None, None),   # (a big chest, no crate)
    1883068192328530224: ("RC_GERUDO_TRAINING_GROUND_FREESTANDING_KEY", None, None),   # (the maze's key, now a chest)
    15117164073907033527: ("RC_FOREST_TEMPLE_FALLING_CEILING_ROOM_CHEST", "RR_FOREST_TEMPLE_FALLING_ROOM", None),
    11182647876438515984: ("RC_GERUDO_TRAINING_GROUND_LOBBY_LEFT_CHEST", "RR_GERUDO_TRAINING_GROUND_LOBBY",
                           "(ctx->GetTrickOption(RT_LENS_GTG) || logic->CanUse(RG_LENS_OF_TRUTH)) && logic->HasItem(RG_OPEN_CHEST)"),
    4961588221597286817: ("RC_GERUDO_TRAINING_GROUND_HAMMER_ROOM_CLEAR_CHEST", "RR_GERUDO_TRAINING_GROUND_HAMMER_ROOM", None),
}

# SoH checks the remake does not have besides the mappings' lists: its ice traps are trap chests (Obj_TBox_A_04, no content)
TRAP_RCS = ["RC_GERUDO_TRAINING_GROUND_HEAVY_BLOCK_FOURTH_CHEST", "RC_GANONS_CASTLE_WATER_TRIAL_LEFT_CHEST",
            "RC_GANONS_CASTLE_LIGHT_TRIAL_SECOND_LEFT_CHEST", "RC_GANONS_CASTLE_LIGHT_TRIAL_FIRST_RIGHT_CHEST",
            "RC_GANONS_CASTLE_LIGHT_TRIAL_THIRD_RIGHT_CHEST", "RC_SPIRIT_TEMPLE_FIRST_MIRROR_LEFT_CHEST"]


def main():
    romfs = sys.argv[1]
    found = chests.scan(romfs, zs.Codec(romfs))
    mapped = {}
    removed = set(TRAP_RCS)
    for f in sorted(glob.glob(os.path.join(ROOT, "research", "mapping", "*.json"))):
        with open(f, encoding="utf-8") as h:
            d = json.load(h)
        if "chests" not in d:   # (research/mapping/gifts_*.json: the non-chest checks, data/gifts.json's sources)
            continue
        for c in d["chests"]:
            mapped[int(c["hash"])] = c
        removed |= {x["rc"] for x in d.get("soh_chests_without_remake_counterpart", [])}
    copy_of = {c: p for p, cs in COPIES.items() for c in cs}
    names = soh_names()
    op = os.path.join(ROOT, "data", "overrides.json")
    with open(op, encoding="utf-8") as h:
        overrides = json.load(h)["overrides"]
    region_names = {rr: r["name"] for rr, r in R.REGIONS.items()}
    region_names.update({o["key"][1]: o["region"]["name"] for o in overrides if o["key"][0] == "add_region"})
    locations, skipped = [], []
    for h, ch in sorted(found.items(), key=lambda kv: (kv[1]["map"], kv[0])):
        if h in copy_of:
            continue
        if (ch["repeat"] and h not in REPEAT_KEPT) or h in RACE_CONSOLATION:
            skipped.append(h)
            continue
        m = mapped.get(h)
        rc, region, rule = (m["soh_rc"], m["soh_region"], m["condition"]) if m else (None, None, None)
        if h in EXTRA_RC:
            rc, region_x, rule_x = EXTRA_RC[h]
            region = region_x or region
            rule = rule_x if rule_x is not None else rule
        if rc is None and not (region and rule):
            raise SystemExit("chest %d (%s) has neither a SoH check nor a region and rule" % (h, ch["map"]))
        locations.append({
            "id": rc or "CHEST_%d" % h, "hash": str(h), "copies": [str(x) for x in COPIES.get(h, [])], "map": ch["map"],
            "rc": rc, "region": region, "condition": rule, "vanilla": ch["drop"],
            "name": names.get(rc) if rc else "Chest (remake only, %s)" % ("Big" if "A_02" in ch["gyaml"] else "Small"),
            "area": region_names.get(region, region or ""),
            "confidence": (m or {}).get("confidence", "high"), "evidence": (m or {}).get("evidence", "")})
    removed -= {l["rc"] for l in locations if l["rc"]}
    out = {"locations": locations, "skipped": [str(h) for h in skipped], "removed": sorted(removed), "overrides": overrides}
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "locations.json"), "w", encoding="utf-8") as h:
        json.dump(out, h, indent=1)
    rcs = [l["rc"] for l in locations if l["rc"]]
    assert len(rcs) == len(set(rcs)), "a SoH check used twice"
    covered = {int(l["hash"]) for l in locations} | set(copy_of) | set(skipped)
    assert covered == set(found), "chests missing: %s" % (set(found) - covered)
    print("locations %d (SoH checks %d, remake-only %d), copies %d, minigame chests left as they are %d, SoH checks removed %d"
          % (len(locations), len(rcs), len(locations) - len(rcs), len(copy_of), len(skipped), len(removed)))


if __name__ == "__main__":
    main()
