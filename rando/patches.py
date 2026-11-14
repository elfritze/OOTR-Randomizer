"""Changes to the game's data outside the chests, each one a setting."""
import copy
import os

from .events import EVENT_SETTING
from .formats import byml, evfl, evfl_patch, sarc

# The new game's opening (OpeningEvent: Opening_LoadingKokiriForest, then Opening_Introduction) plays two movies by
# EventTransition: Dm_Kokiri_0000 (the story's opening) and Dm_Kokiri_0030 (Navi waking Link). Nothing else plays them. Their
# RSDB/EventSetting rows are made DefaultParentEvent's, the engine's own empty event (a 30-frame wait), so the opening goes on
# with what it does around them: the time set to 6:00, the Meet_DekuTree quest step, Navi placed and talked to, an autosave.
# The opening asks whether the last event was skipped and handles both answers, as a player's own skip of the movies does.
OPENING_MOVIES = ("Dm_Kokiri_0000", "Dm_Kokiri_0030")
EMPTY_EVENT = "DefaultParentEvent"


def skip_intro(romfs, codec, mod):
    raw = mod.read(EVENT_SETTING)
    rows, version = byml.read(raw)
    by_id = {r["__RowId"]: i for i, r in enumerate(rows)}
    empty = rows[by_id[EMPTY_EVENT]]
    for name in OPENING_MOVIES:
        row = copy.deepcopy(empty)
        row["__RowId"] = name
        rows[by_id[name]] = row
    mod.write(EVENT_SETTING, byml.write(rows, version, byml.endian(raw)))


# The remake's bombs carry the bomb flowers' lift grade, the one the Goron's Bracelet grants (Item_Gauntlet_Goron's
# ExpansionAbilityActor LiftableGrade): without the bracelet Link takes a bomb out and puts it away at once (seen in game
# without mods, 2026-11-12). The game never shows it (the bomb bag comes after the bracelet); a randomizer's bag can come
# first. The bomb gets the grade nothing needs strength for (the Bombchu's, the pots'), in every pack holding a copy of its
# lift file; the bomb flowers keep their own file (Obj_BombFlower_Fruit), so they still need the bracelet. (The values were
# found by the OotrR randomizer, free_bomb_lift; checked against this game's files.)
BOMB_LIFT = "Component/LiftableParam/Item_Bomb.game__component__LiftableParam.bgyml"
BRACELET_LIFT_GRADE = 3655598229
FREE_LIFT_GRADE = 3069107721
BOMB_LIFT_PACKS = ("Item_Bomb", "Npc_Hylia_ImperialSoldier_Bomb", "Obj_BombFlower_A_01", "Obj_BombFlower_A_04",
                   "Obj_BombFlower_Fruit_For_Break_Obj_DeathMtTrail_BrokenRock_A_01")


def free_bomb_lift(romfs, codec, mod):
    """the player's bombs lifted without the Goron's Bracelet"""
    bracelet = sarc.read(mod.read("Pack/Actor/Item_Gauntlet_Goron.pack.zs"))
    grade = [byml.read(v)[0].get("LiftableGrade") for k, v in bracelet.items() if "ExpansionAbilityActor" in k]
    if grade != [BRACELET_LIFT_GRADE]:
        raise ValueError("the Goron's Bracelet's lift grade is %s, not %d" % (grade, BRACELET_LIFT_GRADE))
    chu = sarc.read(mod.read("Pack/Actor/Item_Bombchu.pack.zs"))
    if byml.read(chu["Component/LiftableParam/Item_Bombchu.game__component__LiftableParam.bgyml"])[0].get("LiftGrade") != \
            FREE_LIFT_GRADE:
        raise ValueError("the Bombchu's lift grade is not %d" % FREE_LIFT_GRADE)
    for actor in BOMB_LIFT_PACKS:
        rel = "Pack/Actor/%s.pack.zs" % actor
        files = sarc.read(mod.read(rel))
        doc, version = byml.read(files[BOMB_LIFT])
        if doc.get("LiftGrade") != BRACELET_LIFT_GRADE:
            raise ValueError("%s: the bomb's lift grade is %r" % (rel, doc.get("LiftGrade")))
        doc["LiftGrade"] = byml.U32(FREE_LIFT_GRADE)
        files[BOMB_LIFT] = byml.write(doc, version, byml.endian(files[BOMB_LIFT]))
        mod.write(rel, sarc.write(files))


# Zora's River: seven invisible walls (FldObj_AirWall_Player_GenerateNavMesh, no flag) stand in the water across the river at
# the line of the two bomb boulders (Obj_BrokenRock_A_01, (-77.8, 98.0, 6.5) and (-75.7, 98.1, 5.0)), from x -83 to -61,
# in both ages' maps: N64's river let a child swim down past the boulders to the front (SoH: Zora River to ZR Front with the
# Bronze Scale, the ability to swim), the remake's does not. A child come in upstream without explosives (the Lost Woods
# dive) is caught there by the current (seen in game, 2026-11-13). Their collision is baked in the map's static compound
# (Phive/StaticCompoundBody/ZoraRiver/*_X3_Z4, with the boulders'), so they are not taken out of the map: each gets a
# Presence it never meets, as the game gives its own static actors with baked collision (soft soil, gossip stones, the
# well's water): in the child's map present only for an adult, in the adult's only for a child. Seen in game (2026-11-13):
# the child swims down past the boulders, so the logic keeps SoH's rule (Zora River to ZR Front by swimming), which counts
# on this patch.
ZR_RIVER_WALL = "FldObj_AirWall_Player_GenerateNavMesh"
ZR_RIVER_WALLS = {
    "Banc/ZoraRiver/ZoraRiver_Child_Static.bcett.byml.zs": (True, (
        8855423962460166888, 4942866467657729468, 2863011381430310501, 1671256346243721333, 12374977777450469396,
        15623121253783701078, 14519305071033520687)),
    "Banc/ZoraRiver/ZoraRiver_Adult_Static.bcett.byml.zs": (False, (
        7850395794748438732, 7982339630050931435, 13781426553798151043, 4565321854739336115, 14077907143773739344,
        9371429508151251838, 11266001672277786960)),
}
AGE_FLAG = "Sequence_IsChildhood"


def zr_river_presence(negate):
    return {"FlagName": AGE_FLAG, "IsCheckLazy": False, "IsNegation": negate}


def open_zr_river(romfs, codec, mod):
    """the walls across Zora's River at the boulders never present"""
    for rel, (negate, hashes) in ZR_RIVER_WALLS.items():
        raw = mod.read(rel)
        doc, version = byml.read(raw)
        by = {int(a["Hash"]): a for a in doc["Actors"]}
        if sum(1 for a in doc["Actors"] if a.get("Gyaml") == ZR_RIVER_WALL) != len(hashes):
            raise ValueError("%s: not %d %s" % (rel, len(hashes), ZR_RIVER_WALL))
        for h in hashes:
            a = by.get(h)
            if a is None or a.get("Gyaml") != ZR_RIVER_WALL or "Presence" in a or not 94 < a["Translate"][1] < 97:
                raise ValueError("%s: actor %d is not the river wall it was" % (rel, h))
            a["Presence"] = zr_river_presence(negate)
        mod.write(rel, byml.write(doc, version, byml.endian(raw)))


# The Bow and the Slingshot carry no ammunition capacity in the remake: Item_Range_Bow's and Item_Range_SlingShot's pouch rows
# have none, the first 30 arrows and seeds are Item_Quiver_Small's and Item_BulletBag_Small's (ExpansionMaxNumActor, MaxNum
# 30). No event or map of the game gives those two (the game's code must, with its own Bow and Slingshot), and shops and
# scrubs sell arrows and seeds only once they are had (DisplayShop's IsGet.Item_Quiver_Small, the scrubs' NecessaryActor).
# A seed's Bow showed 0/0 in game (2026-11-13, given by Dampe). So, as the OotrR randomizer does, the new game's opening gives
# both, silently: two PouchSystemActor.EventTriggerAddOrRemovePouchContent after its first event (Event3, the opening movie's
# transition, the entry Opening_LoadingKokiriForest), as Saria's Fairy Ocarina is added (Dm_Kokiri_0155, IsGetEvent false).
# The quivers and bags found later set 40 and 50 (their tiers come in order: rando.items.TIERS).
OPENING_FLOW = "Event/EventFlow/OpeningEvent.bfevfl.zs"
OPENING_ANCHOR = "Event3"
START_ITEMS = ("Item_Quiver_Small", "Item_BulletBag_Small")
POUCH_ACTOR, POUCH_ADD = "PouchSystemActor", "EventTriggerAddOrRemovePouchContent"
POUCH_ACTOR_FROM = "Event/EventFlow/Dm_Kokiri_0155.bfevfl.zs"   # (the vanilla actor's parameters are copied from here)


def start_item_event(actor):
    return "RandoStartItem_" + actor


def start_item_params(actor):
    return {"Num": 1, "IsEquipDIrect": False, "IsSetMessageTargetActorName": False, "Actor": actor, "IsGetEvent": False}


def starting_bags(romfs, codec, mod):
    """the small quiver and seed bag given at the new game's start"""
    vanilla = [a for a in evfl.read(mod.read(POUCH_ACTOR_FROM))[0]["actors"] if a["name"] == POUCH_ACTOR]
    if len(vanilla) != 1 or vanilla[0]["actions"] != [POUCH_ADD] or not vanilla[0]["params"]:
        raise ValueError("%s: not the PouchSystemActor known" % POUCH_ACTOR_FROM)
    raw = mod.read(OPENING_FLOW)
    flow = evfl.read(raw)[0]
    first = [e for e in flow["events"] if e["name"] == OPENING_ANCHOR]
    if flow["entries"].get("Opening_LoadingKokiriForest") != flow["events"].index(first[0]) or \
            first[0]["params"].get("EventName") != "Dm_Kokiri_0000":
        raise ValueError("the opening's first event is not the one known")
    mod.write(OPENING_FLOW, evfl_patch.add_actions(raw, OPENING_ANCHOR, POUCH_ACTOR, POUCH_ADD, vanilla[0]["params"],
                                                   [(start_item_event(a), start_item_params(a)) for a in START_ITEMS]))


# King Zora (child) stands aside by the water quest's step: his schedule for each step of Get_StoneOfWater (Pack/
# AIScheduleParam.pack), the moved one from Step07, the step showing him Ruto's Letter sets (Get_StoneOfWater: the letter's
# scene Dm_Zora_0010, the letter taken from its bottle, Step07). The first time Zora's Domain is entered from Zora's River,
# its arrival scene (the river's banc change: InitEventName Goto_ZoraDomain while HavePlayedEvent.Dm_Zora_0000 is unset, in
# Dm_SY_BancChangeArrive) sets the quest to Step03 or Step03_Impa, whatever step it is at. The game always comes that way
# first; a seed need not (Zora's Domain from Lake Hylia under water): the letter shown, then the river's way in, and the
# quest went back to Step03 and the King to his seat for good, the letter gone (seen in game, 2026-11-13). The letter's own
# step now also marks the arrival scene played (HavePlayedEvent.Dm_Zora_0000, which the game's flows set as they set other
# HavePlayedEvent flags), so it never comes after the letter; it is only skipped by one who came in another way first.
WATER_FLOW = "Event/EventFlow/Get_StoneOfWater.bfevfl.zs"
ZD_ARRIVAL_FLAG = "HavePlayedEvent.Dm_Zora_0000"
ZD_ARRIVAL_MAPS = ("Banc/ZoraRiver/ZoraRiver_Child_Static.bcett.byml.zs", "Banc/ZoraRiver/ZoraRiver_Adult_Static.bcett.byml.zs")
ZD_ARRIVAL_EVENT = "RandoZoraArrivalPlayed"


def letter_step_event(flow):
    """the index of the event giving the water quest Step07 after the letter is taken from its bottle"""
    found = [i for i, e in enumerate(flow["events"]) if e["type"] == "action" and
             (e.get("params") or {}).get("ChallengeName") == "Get_StoneOfWater" and e["params"].get("StepName") == "Step07"]
    if len(found) != 1:
        raise ValueError("Get_StoneOfWater: %d events give Step07" % len(found))
    before = [e for e in flow["events"] if e.get("next") == found[0]]
    if len(before) != 1 or flow["actors"][before[0]["actor"]]["actions"][before[0]["action"]] != \
            "EventTriggerRemoveFromSpecificBottle":
        raise ValueError("Get_StoneOfWater: Step07 does not come after the letter's bottle")
    return found[0]


def zora_arrival_after_letter(romfs, codec, mod):
    """the letter's step marks Zora's Domain's arrival scene played"""
    for rel in ZD_ARRIVAL_MAPS:
        doc = byml.read(mod.read(rel))[0]
        gates = [a["Dynamic"] for a in doc["Actors"] if (a.get("Dynamic") or {}).get("InitEventName") == "Goto_ZoraDomain"]
        if len(gates) != 1 or gates[0].get("InitEventFlag") != ZD_ARRIVAL_FLAG:
            raise ValueError("%s: the way into Zora's Domain is not the one known" % rel)
    raw = mod.read(WATER_FLOW)
    flow = evfl.read(raw)[0]
    anchor = flow["events"][letter_step_event(flow)]["name"]
    mod.write(WATER_FLOW, evfl_patch.add_actions(raw, anchor, "GameDataActor", "EventTriggerSetGameDataBool", None,
                                                 [(ZD_ARRIVAL_EVENT, zora_arrival_params())]))


def zora_arrival_params():
    return {"GameDataName": ZD_ARRIVAL_FLAG, "Value": True, "Index": -1}


# Mido (Npc_Kokiri_Mido_Child) blocks the way to the Deku Tree with an invisible wall (FldObj_AirWall_Player_GenerateNavMesh in
# KokiriForest_Child_Dynamic) present while KokiriForest_Npc_Kokiri_Mido_Child_Blocker is set. Only two talks clear it: his
# "Talk" entry with the Kokiri Sword and a shield (Meet_DekuTree Step03), and the scene after the Kokiri Emerald (Dm_Kokiri_0145).
# His schedule (Component/AIScheduleParam, the first row whose flag is set) has a row for after meeting Zelda
# (Goto_HyruleCastle_IsCompleted_Exp: ActionType 531034651, his post-Deku Tree spot, the DoorOfTime_IsAfter_Step01_Exp talks,
# none of which clears the flag). The game never gets there with Mido still blocking (Zelda comes after the Deku Tree); a seed
# can: Mido walks off and his wall stays for good (seen in game, 2026-11-13: met Zelda first, a Kokiri Sword given by debug
# did not help). The row is taken out: until the wall is down he keeps his place and the talk that lets you pass; after it,
# his post-Emerald row (Get_StoneOfForest_Complete_Mido_TalkEnd, same spot) stands in for it.
MIDO_SCHEDULE = "Component/AIScheduleParam/Npc_Kokiri_Mido_Child.game__component__AIScheduleParam.bgyml"
MIDO_ZELDA_ROW = "Goto_HyruleCastle_IsCompleted_Exp"
MIDO_ROWS = ("KokiriForest_Npc_Kokiri_Blocker", "Meet_DekuTree_IsAfter_Step02_Exp", "Meet_DekuTree_IsCompleted_Exp",
             "Get_StoneOfForest_IsAfter_DefeatBoss_Exp", "Get_StoneOfForest_Complete_Mido_TalkEnd", MIDO_ZELDA_ROW)


# Not done (crashes): the boulder over Dodongo's Cavern's entrance (Obj_DeathMtTrail_BrokenRock_A_01, "DodongoCavern_CrackRock",
# only in the child's Death Mountain Trail map) has no life, so the player's bombs do nothing to it (seen in game, 2026-11-13);
# only its bomb flower above breaks it (an event requests its death), and picking that flower needs the Goron's Bracelet. Giving
# it the bombable boulders' life (Obj_BrokenRock_A_01's WallCrack LifeParam, CrackStoneObject damage, WallCrack life files, a
# LifeRef in its ActorParam), with or without its ActorInfo heap raised (+32768) and GameActorInfo MaxLife 6, made the game
# crash creating it on entering the trail (three times, 2026-11-13: write to 0x100000000000 in BaseProcCreateAndDeleteThread,
# the registers naming Actor/Obj_DeathMt..., right after the trail's logic module, which creates it, loaded). So the logic
# asks a child for the bracelet there (data/overrides.json), and the boulder stays as the game has it.
DC_BOULDER = "Obj_DeathMtTrail_BrokenRock_A_01"
# The trail's logic module (Logic/DeathMountainTrail_Child_Prefab_ffa7.logic.module.ainb) also sets the Goron quest
# (Get_StoneOfFire) to DungeonStart (step 16) when the boulder's death procedure is complete, while the quest is before it
# (TriggerChallengeSetStepNoEventPause <- OperateAND(HoldChallengeCurrentStepCheckOrder(DungeonStart).IsBefore,
# OperateOR(boulder.Dead, ...))); the game breaks it only after Darunia's dance (DodongoCavernOpne, Dm_Goron_0030). An edit of
# that check (in place) was in the mod in the first two crashes; it is not made either. (rando/formats/ainb.py reads these.)
DC_LOGIC = "Logic/DeathMountainTrail_Child_Prefab_ffa7.logic.module.ainb"


# Not done either (crashed, 2026-11-14): letting a bomb bag pick the flower that breaks the boulder by its fruit's AI (its
# QueryGetGameDataBool IsGet.Armor_Child_Gauntlet_Goron asking for IsGet.Item_BombBag_Small instead, the name added to the
# AI's string pool) and a lift file of its own named in its ActorParam's LiftableRef. The game crashed creating the fruit,
# as it did the boulder: the one thing both had was a changed ActorParam of an actor the game has (new actors with their own
# ActorParams, the pickups, work). Every changed file stayed within its size-table entry. Lifting every bomb flower's fruit
# without the bracelet (its shared lift file's grade) worked: the flower's scene broke the boulder for a child without the
# bracelet (seen in game, 2026-11-14), but every bomb flower was then liftable, so that is not kept either.
FRUIT_LIFT = "Component/LiftableParam/Obj_BombFlower_Fruit.game__component__LiftableParam.bgyml"
FRUIT_LIFT_PACKS = ("Obj_BombFlower_A_01", "Obj_BombFlower_A_04",
                    "Obj_BombFlower_Fruit_For_Break_Obj_DeathMtTrail_BrokenRock_A_01")


# Instead, a bomb at the boulder sets off the flower's scene. The trail's logic module plays it (its EventRequestActor
# Get_StoneOfFire_DodongoCavernOpne: Dm_DeathMtTrail_0010, the fruit flying to the boulder and the boulder's death) when
# OperateAND(the flower's CanExplosionPerformance, OperateOR(a BombFruit in Area_d584, in Area_4605, in Area_e01c)). The
# module also watches for Item_Bomb in those same three areas (a HoldActorObserverBySensorHitInfo nothing reads: the game's
# own, left unconnected). The OR's second source, the fruit in Area_4605, is made that bomb watcher (in place: the multi-source
# entry, the OR's precondition entry, the two outputs' "read" bits, as all 1821 logic files keep them): a player's bomb in any
# of the three areas, or the fruit in the first or the third, sets off the scene.
DC_BOMB_SENSOR, DC_FRUIT_SENSOR = "Item_Bomb", "BombFruit"
DC_FLOWER_NODE = "ActorLogicBombFlowerGrassBreakBreakDeathMtTrailBrokenRock"
SENSOR = "HoldActorObserverBySensorHitInfo"


def dc_logic_bomb_edits(data):
    """[(offset, old u32, new u32)] for the trail's logic module, or ValueError if it is not the one known"""
    from .formats import ainb
    f = ainb.File(data)
    pre_at = f.u32(0x30)
    if f.u32(0x4C) != pre_at or f.u32(0x50) != pre_at:
        raise ValueError("%s: the precondition table is not where it is known" % DC_LOGIC)

    def watches(n):
        i = n["inputs"].get("ActorName")
        return f.value(i["value_at"], "string") if i and not i["sources"] else None

    bombs = [n for n in f.nodes if n["name"] == SENSOR and watches(n) == DC_BOMB_SENSOR]
    if len(bombs) != 1 or f.readers(bombs[0]["index"], 0) or f.readers(bombs[0]["index"], 1):
        raise ValueError("%s: not one bomb watcher read by nothing" % DC_LOGIC)
    bomb = bombs[0]
    ors = [n for n in f.nodes if n["name"] == "OperateOR" and len(n["inputs"]["BoolMulti"]["sources"]) == 3 and
           all(f.nodes[s[0]]["name"] == SENSOR and watches(f.nodes[s[0]]) == DC_FRUIT_SENSOR and s[1] == 0
               for s in n["inputs"]["BoolMulti"]["sources"])]
    if len(ors) != 1:
        raise ValueError("%s: not one OR of three fruit watchers" % DC_LOGIC)
    gate = ors[0]
    fruit, _, entry = gate["inputs"]["BoolMulti"]["sources"][1]
    if f.readers(fruit, 0) != [(gate["index"], "BoolMulti")] or f.readers(fruit, 1):
        raise ValueError("%s: the fruit watcher is read by more than the OR" % DC_LOGIC)
    o = f.nodes_at + gate["index"] * ainb.NODE_SIZE
    base, count = f.i16(o + 0x24) & 0xFFFF, f.i16(o + 0x26) & 0xFFFF
    pre = [pre_at + 4 * k for k in range(base, base + count)]
    hits = [at for at in pre if f.u32(at) == fruit]
    if len(hits) != 1 or bomb["index"] in [f.u32(at) for at in pre]:
        raise ValueError("%s: the OR's preconditions are not the ones known" % DC_LOGIC)
    (fruit_name, fruit_out), (bomb_name, bomb_out) = f.nodes[fruit]["outputs"]["bool"][0], bomb["outputs"]["bool"][0]
    if fruit_name != "IsHit" or bomb_name != "IsHit" or not f.u32(fruit_out) & ainb.USED or f.u32(bomb_out) & ainb.USED:
        raise ValueError("%s: the watchers' outputs are not the ones known" % DC_LOGIC)
    old = f.u32(entry)
    if old & 0xFFFF != fruit or old >> 16:
        raise ValueError("%s: the multi-source entry is not the fruit watcher's" % DC_LOGIC)
    # (the AND that requests the scene also asks for the flower's CanExplosionPerformance, which its AI sets only while a
    #  picked fruit burns (HasTimeUntilTheExplosion): a bomb dropped at the boulder did nothing, 2026-11-14. Its first source
    #  is made the OR's True, as its second: the scene is requested on a hit in the areas alone)
    ands = [n for n in f.nodes if n["name"] == "OperateAND" and
            [(s[0], s[1]) for s in n["inputs"]["BoolMulti"]["sources"]][1:] == [(gate["index"], 1)] and
            len(n["inputs"]["BoolMulti"]["sources"]) == 2]
    if len(ands) != 1:
        raise ValueError("%s: not one AND of the flower and the OR" % DC_LOGIC)
    flower, flower_out, flower_entry = ands[0]["inputs"]["BoolMulti"]["sources"][0]
    flower_outs = f.nodes[flower]["outputs"]["bool"]
    if f.nodes[flower]["name"] != DC_FLOWER_NODE or flower_outs[flower_out][0] != "CanExplosionPerformance" or \
            f.readers(flower, flower_out) != [(ands[0]["index"], "BoolMulti")] or \
            f.u32(flower_entry) != flower | (flower_out << 16) or not f.u32(flower_outs[flower_out][1]) & ainb.USED:
        raise ValueError("%s: the AND's first source is not the flower's CanExplosionPerformance" % DC_LOGIC)
    explode_at = flower_outs[flower_out][1]
    return [(entry, old, bomb["index"]),
            (hits[0], fruit, bomb["index"]),
            (fruit_out, f.u32(fruit_out), f.u32(fruit_out) & ~ainb.USED),
            (bomb_out, f.u32(bomb_out), f.u32(bomb_out) | ainb.USED),
            (flower_entry, f.u32(flower_entry), gate["index"] | (1 << 16)),
            (explode_at, f.u32(explode_at), f.u32(explode_at) & ~ainb.USED)]


def dc_bombs_set_off_flower(romfs, codec, mod):
    """a bomb at the boulder over Dodongo's Cavern sets off its bomb flower's scene"""
    data = bytearray(mod.read(DC_LOGIC))
    for at, _, new in dc_logic_bomb_edits(bytes(data)):
        data[at:at + 4] = new.to_bytes(4, "little")
    mod.write(DC_LOGIC, bytes(data))


# Darunia gives the Goron's Bracelet in his dance's scene (Dm_Goron_0030), played when Saria's Song is played to him
# (his ocarina reaction, always on: Get_StoneOfFire_PlayOcarina) while the Goron quest is not yet past SariaMelodyPlay; past
# it, the same song plays his dance (Dm_Goron_0025) and then only a talk (the switch Event39 on
# Get_StoneOfFire_IsAfter_SariaMelodyPlay_Exp: its true case Event42, a camera move, then the talk). The game never gets
# past that step without the dance; a seed does: breaking the boulder over Dodongo's Cavern moves the quest to DungeonStart
# from any step, and beating King Dodongo to its end (seen in game, 2026-11-14: "Explore Dodongo's Cavern" after a bomb
# broke the boulder), and a seed can ask for the bracelet after (Saria's Song somewhere only an adult reaches). The talk's
# way gets the bracelet added to the pouch, silently, as Saria's Fairy Ocarina is (Dm_Kokiri_0155): after the dance it is
# had already, and adding it again changes nothing.
FIRE_FLOW = "Event/EventFlow/Get_StoneOfFire.bfevfl.zs"
DARUNIA_SWITCH, DARUNIA_AFTER = "Event39", "Event42"
DARUNIA_STEP_FLAG = "Get_StoneOfFire_IsAfter_SariaMelodyPlay_Exp"
BRACELET = "Item_Gauntlet_Goron"
DARUNIA_EVENT = "RandoDaruniaBracelet"


def darunia_bracelet_after_quest(romfs, codec, mod):
    """Darunia gives the bracelet to Saria's Song past his dance's step too"""
    vanilla = [a for a in evfl.read(mod.read(POUCH_ACTOR_FROM))[0]["actors"] if a["name"] == POUCH_ACTOR]
    if len(vanilla) != 1 or vanilla[0]["actions"] != [POUCH_ADD] or not vanilla[0]["params"]:
        raise ValueError("%s: not the PouchSystemActor known" % POUCH_ACTOR_FROM)
    raw = mod.read(FIRE_FLOW)
    flow = evfl.read(raw)[0]
    ev = flow["events"]
    by = {e["name"]: i for i, e in enumerate(ev)}
    switch = ev[by[DARUNIA_SWITCH]]
    dance = ev[switch["cases"].get(1)] if switch.get("type") == "switch" and 1 in switch["cases"] else {}
    if switch.get("params") != {"GameDataName": DARUNIA_STEP_FLAG} or switch["cases"].get(0) != by[DARUNIA_AFTER] or \
            (dance.get("params") or {}).get("EventName") != "Dm_Goron_0030":
        raise ValueError("%s: Darunia's dance switch is not the one known" % FIRE_FLOW)
    mod.write(FIRE_FLOW, evfl_patch.add_actions(raw, DARUNIA_AFTER, POUCH_ACTOR, POUCH_ADD, vanilla[0]["params"],
                                                [(DARUNIA_EVENT, start_item_params(BRACELET))]))


# Back to child as soon as Link is adult: the Temple of Time's logic module (Market_Adult_Prefab_89da) deletes the Master
# Sword's interaction (ActorLogicAttentionActor, its ReceiveDoAction requesting Market_Adult_Field_AdultToChild) while the
# Forest Temple's sage is not awakened (Logic_Delete <- InvBool(SageOfForest_IsCompleted_Exp)): the remake keeps an adult
# Link adult until the Forest Temple is done (seen in game, 2026-11-14: no way back to child at the pedestal). The original
# game, and SoH's logic, let him go back as soon as he is adult; a seed counts on it (a child-only item needed for the Forest
# Temple: the Hammer by the frogs, the Hookshot behind hammer rocks). The sword's Logic_Delete is made unconnected, as the
# module's other actor's is (no source, the unlinked flags, false), in place; the inverted flag's output loses its "read" bit.
# The back-to-child event itself asks nothing of the Forest Temple.
TIME_LOGIC = "Logic/Market_Adult_Prefab_89da.logic.module.ainb"
TIME_FLAG = "SageOfForest_IsCompleted_Exp"
UNLINKED_FLAGS = 0x01800000


def time_logic_edits(data):
    """[(offset, old u32, new u32)] for the Temple of Time's sword module, or ValueError if it is not the one known"""
    from .formats import ainb
    f = ainb.File(data)
    swords = [n for n in f.nodes if n["name"] == "ActorLogicAttentionActor" and
              f.value(n["imm"]["InstanceName"][1], "string").startswith("Obj_TimeTemple_MasterSword_A_01")]
    if len(swords) != 1:
        raise ValueError("%s: not one Master Sword attention node" % TIME_LOGIC)
    delete = swords[0]["inputs"]["Logic_Delete"]
    if len(delete["sources"]) != 1 or delete["sources"][0][2] is not None:
        raise ValueError("%s: the sword's Logic_Delete is not one single source" % TIME_LOGIC)
    inv, out, _ = delete["sources"][0]
    flags = f.nodes[inv]["inputs"].get("BoolMulti", {}).get("sources", [])
    if f.nodes[inv]["name"] != "InvBool.module" or len(flags) != 1 or \
            f.value(f.nodes[flags[0][0]]["inputs"]["GameDataNameBoolExp"]["value_at"], "string") != TIME_FLAG or \
            f.readers(inv, out) != [(swords[0]["index"], "Logic_Delete")]:
        raise ValueError("%s: the sword is not deleted by the inverted %s alone" % (TIME_LOGIC, TIME_FLAG))
    unlinked = [i for n in f.nodes for k, i in n["inputs"].items() if k == "Logic_Delete" and not i["sources"]]
    e = delete["entry"]
    if not unlinked or any(f.u32(i["entry"] + 4) != 0xFFFF or f.u32(i["entry"] + 8) != UNLINKED_FLAGS for i in unlinked) or \
            f.u32(e + 8) != 0 or f.u32(e + 12) != 0:
        raise ValueError("%s: the unconnected inputs are not encoded as known" % TIME_LOGIC)
    out_at = f.nodes[inv]["outputs"]["bool"][out][1]
    if not f.u32(out_at) & ainb.USED:
        raise ValueError("%s: the inverted flag's output is not marked read" % TIME_LOGIC)
    return [(e + 4, f.u32(e + 4), 0xFFFF),
            (e + 8, 0, UNLINKED_FLAGS),
            (out_at, f.u32(out_at), f.u32(out_at) & ~ainb.USED)]


def free_time_travel(romfs, codec, mod):
    """the Master Sword takes Link back to child as soon as he is adult"""
    data = bytearray(mod.read(TIME_LOGIC))
    for at, _, new in time_logic_edits(bytes(data)):
        data[at:at + 4] = new.to_bytes(4, "little")
    mod.write(TIME_LOGIC, bytes(data))


def mido_keeps_blocking(romfs, codec, mod):
    """Mido's schedule without its after-Zelda row"""
    raw = mod.read(MIDO_SCHEDULE)
    doc, version = byml.read(raw)
    rows = doc["ConditionalSchedule"]
    if tuple(r.get("ConditionFlag") for r in rows) != MIDO_ROWS:
        raise ValueError("Mido's schedule rows are not the ones known: %r" % [r.get("ConditionFlag") for r in rows])
    doc["ConditionalSchedule"] = [r for r in rows if r.get("ConditionFlag") != MIDO_ZELDA_ROW]
    mod.write(MIDO_SCHEDULE, byml.write(doc, version, byml.endian(raw)))


# A song's item (Item_Melody_*, as a chest gives it) has a rupee for its model: the game never shows one. Every song shows
# Sheik's harp instead: (model project, model) as a ModelInfo names them, Model/<project>.<model>.bfres.zs. (Not tinted by the
# song: the engine recolors a model only by a material animation in its own files, as the rupee's Obj_Rupee_Color, and the
# harp has none; its color is its textures'.)
SONG_MODEL = ("Item_Harp_Sheik", "Item_Harp_Sheik")
SONGS = ("Item_Melody_ZeldaLullaby", "Item_Melody_EponaSong", "Item_Melody_SariaSong", "Item_Melody_SunSong",
         "Item_Melody_TimeSong", "Item_Melody_StormSong", "Item_Melody_ForestMinuet", "Item_Melody_FireBolero",
         "Item_Melody_WaterSerenade", "Item_Melody_ShadowNocturne", "Item_Melody_SpiritRequiem", "Item_Melody_LightPrelude")


def song_models(romfs, codec, mod, songs=SONGS):
    """each song's item shows SONG_MODEL"""
    project, model = SONG_MODEL
    for actor in songs:
        if not os.path.exists(os.path.join(romfs, "Model", "%s.%s.bfres.zs" % (project, model))):
            raise ValueError("no model %s.%s" % (project, model))
        rel = "Pack/Actor/%s.pack.zs" % actor
        files = sarc.read(mod.read(rel))
        key = "Component/ModelInfo/%s.engine__component__ModelInfo.bgyml" % actor
        info, version = byml.read(files[key])
        if info != {"FmdbName": "Obj_Rupee", "ModelProjectName": "Obj_Rupee"}:
            raise ValueError("%s: its model is not the rupee any more: %r" % (actor, info))
        info["FmdbName"], info["ModelProjectName"] = model, project
        files[key] = byml.write(info, version, byml.endian(files[key]))
        mod.write(rel, sarc.write(files))
