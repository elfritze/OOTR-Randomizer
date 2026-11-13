"""Treasure chests: where each is (by its placement Hash, the same in a map's child and adult files) and what it holds, read
from the maps (Banc/<map>/*.bcett.byml.zs: an actor's Dynamic.Drop__DropActor and GetEventName), and the maps written again
with other contents into a mod's romfs."""
import os

from .formats import byml

DROP, EVENT = "Drop__DropActor", "GetEventName"
SUBSTITUTE = ("Drop__CheckActor", "Drop__DropActor_Substitute")
REPEAT = "IsEnableRepeatOpen"   # (a minigame's chest, filled again each play: the treasure chest game's, DreamWorld's)

# A chest's GetEventName replaces the default chest event (Dm_SY_Treasurebox, or Dm_SY_TreasureboxSmall), which gives
# whatever the chest holds. Most are made for the chest's own item: the Kokiri Sword's (Get_StoneOfForest_GetSword) plays a
# scene that gives Link the sword whatever came out of the chest (seen in game, 2026-11-12). A chest with another item drops
# its event unless the event is here: seen in game to give another item as it gives its own.
ITEM_AGNOSTIC_EVENTS = {
    "KokiriForest_TreasureBox_NaviChatOff",   # (Mido's house: Dm_SY_TreasureboxSmall's Success_MidoHouse; gave the sword)
}
# Events the game needs whatever the chest holds: each runs the default chest event with the chest's own content (by its actor
# name), and does more that is not about the item. Read from the flows (rando.events), not yet each seen in game.
STORY_EVENTS = {
    "SageOfWater_MelodyGet_Water",            # (the Iron Boots' chest: Sheik then teaches the Serenade of Water)
    "SageOfSpirit_NaboorIsTakenAway",         # (the Silver Gauntlets' chest: Nabooru is taken, the Spirit quest goes on)
    "SubEvent_GetIceArrow_OpenTBox",          # (the Ice Arrows' chest: its quest's step)
    "MiniGame_DampeRace_OpenGoalTBox",        # (the race's state, from which chest the race made appear, not its item)
    "InsideJabuJabuBelly_TreasureBoxWithRuto09",   # (Ruto's room flags)
    "InsideJabuJabuBelly_TreasureBoxWithRuto12",
    "MiniGame_ChoiceTreasure_OpenClearTreasureBox",   # (the treasure chest game's prize: the game's end)
}
ITEM_AGNOSTIC_EVENTS |= STORY_EVENTS


def event_for(chest, drop):
    """the GetEventName a chest gets with drop in it: its own with its own item, else its own only when ITEM_AGNOSTIC_EVENTS
    has it"""
    if drop == chest["drop"] or chest["event"] in ITEM_AGNOSTIC_EVENTS:
        return chest["event"]
    return None


# A chest with no Drop__DropActor gives what its drop table (Drop/DropSubTable/Obj_TBox) picks when it opens: a resource the
# player is short of. Three are like that (the Forest Temple's falling ceiling room, two in the Gerudo Training Ground); they
# are filled like the others. For the pool each counts as this:
DYNAMIC_DROP = "TBox_ArrowBundle_Medium"
TRAP = "Obj_TBox_A_04"   # (an ice trap's chest: no content, it opens with TrapTreasureBoxOpen)


def is_chest(actor):
    g = actor.get("Gyaml", "")
    return g.startswith("Obj_") and "TBox" in g and "Pedestal" not in g and g != TRAP and (
        DROP in (actor.get("Dynamic") or {}) or g.startswith(("Obj_TBox_A_", "Obj_TBox_GlassTruth")))


def drop_of(actor):
    return (actor.get("Dynamic") or {}).get(DROP, DYNAMIC_DROP)


def map_files(romfs):
    """every map file, as a path relative to the romfs ("Banc/KokiriForest/KokiriForest_Child_Static.bcett.byml.zs")"""
    out = []
    banc = os.path.join(romfs, "Banc")
    for d in sorted(os.listdir(banc)):
        p = os.path.join(banc, d)
        if os.path.isdir(p):
            out.extend("Banc/%s/%s" % (d, f) for f in sorted(os.listdir(p)) if f.endswith(".bcett.byml.zs"))
    return out


def scan(romfs, codec):
    """{hash: {"gyaml", "drop", "event", "dynamic_drop", "map", "repeat", "files"}} for every chest. A chest placed in more than one file (the child's and
    the adult's maps) is one entry; its copies must agree."""
    chests = {}
    for rel in map_files(romfs):
        root, _ = byml.read(codec.read(os.path.join(romfs, rel)))
        for a in root.get("Actors", []):
            if not is_chest(a):
                continue
            dyn = a.get("Dynamic") or {}
            c = chests.setdefault(int(a["Hash"]), {"gyaml": a["Gyaml"], "drop": drop_of(a), "event": dyn.get(EVENT),
                                                   "dynamic_drop": DROP not in dyn, "map": rel.split("/")[1],
                                                   "repeat": bool(dyn.get(REPEAT)), "files": []})
            if (c["drop"], c["event"]) != (drop_of(a), dyn.get(EVENT)):
                raise ValueError("chest %d differs between %s and %s" % (a["Hash"], c["files"][0], rel))
            c["files"].append(rel)
    return chests


def write(romfs, codec, mod, contents):
    """contents: {hash: (drop actor, event name or None)}. Each map file holding one of those chests is written to the mod
    (rando.mod.Mod) with them changed; nothing else in it changes. Returns the files written."""
    want = {int(h): v for h, v in contents.items()}
    written = []
    for rel in map_files(romfs):
        root, version = byml.read(codec.read(os.path.join(romfs, rel)))
        changed = False
        for a in root.get("Actors", []):
            h = int(a.get("Hash", 0))
            if h not in want or not is_chest(a):
                continue
            drop, event = want[h]
            dyn = a.setdefault("Dynamic", {})
            if dyn.get(DROP) != drop:
                # (a chest that gives its substitute instead when the player has the check actor, as the shields' chests give
                # rupees to one who has the shield: off, or the randomized item could become rupees)
                for k in SUBSTITUTE:
                    dyn.pop(k, None)
            dyn[DROP] = drop
            if event:
                dyn[EVENT] = event
            else:
                dyn.pop(EVENT, None)
            changed = True
        if not changed:
            continue
        mod.write(rel, byml.write(root, version))
        written.append(rel)
    return written
