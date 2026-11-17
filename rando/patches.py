"""Changes to the game's data outside the chests, each one a setting."""
import copy
import os

from .events import EVENT_SETTING
from .formats import byml, evfl, evfl_patch, msbt, sarc

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


def opening_with_bags(raw, pouch_actor_flow):
    """OpeningEvent.bfevfl with the small quiver and seed bag added after its first event"""
    vanilla = [a for a in evfl.read(pouch_actor_flow)[0]["actors"] if a["name"] == POUCH_ACTOR]
    if len(vanilla) != 1 or vanilla[0]["actions"] != [POUCH_ADD] or not vanilla[0]["params"]:
        raise ValueError("%s: not the PouchSystemActor known" % POUCH_ACTOR_FROM)
    flow = evfl.read(raw)[0]
    first = [e for e in flow["events"] if e["name"] == OPENING_ANCHOR]
    if flow["entries"].get("Opening_LoadingKokiriForest") != flow["events"].index(first[0]) or \
            first[0]["params"].get("EventName") != "Dm_Kokiri_0000":
        raise ValueError("the opening's first event is not the one known")
    return evfl_patch.add_actions(raw, OPENING_ANCHOR, POUCH_ACTOR, POUCH_ADD, vanilla[0]["params"],
                                  [(start_item_event(a), start_item_params(a)) for a in START_ITEMS])


def starting_bags(romfs, codec, mod):
    """the small quiver and seed bag given at the new game's start"""
    mod.write(OPENING_FLOW, opening_with_bags(mod.read(OPENING_FLOW), mod.read(POUCH_ACTOR_FROM)))


# The remake holds the clock at 15:00 until Impa's send-off from the castle (HavePlayedEvent.Dm_HrlField_0020; the game's code
# reads it, not its data): no night, so no night-only Gold Skulltulas, no Dampe, before Zelda, which SoH's logic never
# waits for (OotrR's story_fixes CLOCK_FLAG, its issue #40; here seed 7cc65105, 2026-11-15: no night with Zelda's Letter
# from Saria, the castle not yet seen). The flag is set at the new game's start, after the starting bags: the clock runs
# from the start. The send-off still plays (DoorOfTime_SendOff, from Impa's talk, an EventTransition not asking the flag);
# the flag is read otherwise only by two children's lines (Npc_Hylia_043_Child, Npc_Hylia_Soldier_008_Child) and the
# Zora's River owl (ZoraRiver_Child_Prefab_07cf, with Saria's Song).
CLOCK_FLAG = "HavePlayedEvent.Dm_HrlField_0020"
CLOCK_EVENT = "RandoClockRuns"


GAME_DATA_ACTOR_FROM = "Event/EventFlow/Get_StoneOfWater.bfevfl.zs"   # (the opening has no GameDataActor: its parameters)


# That was half of it. Before the cap, the clock is held outright: each frame set back to a fixed hour (no night, and a
# bed slept in until night wakes in the day: seed 889a1e52, 2026-11-17) until HyruleField_ArriveEntrance is set (the
# game's code again: main+0x345c020, asked each frame by the clock's update, main+0x3cdf70; the Deku Tree's quest not yet
# started leaves the clock free). One event sets it: the owl's scene at Hyrule Field's entrance (Goto_HyruleCastle,
# Goto_HyruleCastle_Kaepora_00), a step of the story a seed need not reach: that save had been all over the field without
# it. So the opening sets it too, after the cap's flag.
# The scene on the bridge out of the forest (Dm_Kokiri_0155, in the same flow) sets HyruleField_ChangeENV: the field's
# sky of the first arrival (WorldParam HyruleField_Child: MainField_Bluesky_First; a light area of the field's map by the
# flag too), which the owl's scene clears, rebuilding the light (Event_RebuildConditionEnvTimePalette): left set, as in
# that save. Here the bridge's scene sets it false.
# A save made before this has neither: for it (and for whatever else might set the field's flag), the get of any item sets
# the first and clears the second (ActionGuide's ActionGuide entry, where every item get ends: first in it, after the
# ocarina's guide and the own items' hook are put there).
ARRIVED_FLAG = "HyruleField_ArriveEntrance"
ARRIVED_EVENT = "RandoClockArrived"
FIELD_LIGHT_FLAG = "HyruleField_ChangeENV"
FIELD_FLOW = "Event/EventFlow/Goto_HyruleCastle.bfevfl.zs"
CLOCK_GUIDE_FLOW = "Event/EventFlow/ActionGuide.bfevfl.zs"
CLOCK_ON_GET = ("RandoClockArrivedOnGet", "RandoFieldLightOnGet")
SET_BOOL = ("GameDataActor", "EventTriggerSetGameDataBool")


def bool_set(flag, value):
    return {"GameDataName": flag, "Value": value, "Index": -1}


def opening_with_arrival(raw):
    """OpeningEvent.bfevfl (with the cap's flag set) with the field's arrival set after it"""
    return evfl_patch.add_actions(raw, CLOCK_EVENT, SET_BOOL[0], SET_BOOL[1], None,
                                  [(ARRIVED_EVENT, bool_set(ARRIVED_FLAG, True))])


def opening_with_clock(raw, game_data_actor_flow):
    """OpeningEvent.bfevfl (with the starting bags) with the clock's two flags set after them"""
    actor = [a for a in evfl.read(game_data_actor_flow)[0]["actors"] if a["name"] == "GameDataActor" and not a["sub"]]
    if len(actor) != 1 or not actor[0]["params"]:
        raise ValueError("%s: not the GameDataActor known" % GAME_DATA_ACTOR_FROM)
    return opening_with_arrival(evfl_patch.add_actions(raw, start_item_event(START_ITEMS[-1]), SET_BOOL[0], SET_BOOL[1],
                                                       actor[0]["params"], [(CLOCK_EVENT, bool_set(CLOCK_FLAG, True))]))


def field_light_kept(data):
    """Goto_HyruleCastle.bfevfl with its one event setting the field's first light setting it false"""
    from .formats import evfl_edit
    edit = evfl_edit.FlowEdit(data)
    flow = edit.flow
    sets = [e["name"] for e in flow["events"] if e["type"] == "action" and
            (flow["actors"][e["actor"]]["name"], flow["actors"][e["actor"]]["actions"][e["action"]]) == SET_BOOL and
            e["params"].get("GameDataName") == FIELD_LIGHT_FLAG and e["params"].get("Value") is True]
    if len(sets) != 1:
        raise ValueError("Goto_HyruleCastle: %d events set %s" % (len(sets), FIELD_LIGHT_FLAG))
    edit.set_values(sets[0], {"Value": False})
    return edit.apply()


def clock_on_get(data):
    """ActionGuide.bfevfl (with what else a seed puts first in it) setting the clock free first, at every item get"""
    from .formats import evfl_edit
    edit = evfl_edit.FlowEdit(data)
    flow = edit.flow
    arrived, light = CLOCK_ON_GET
    first = flow["events"][flow["entries"]["ActionGuide"]]["name"]
    edit.add_event({"name": arrived, "type": "action", "actor": SET_BOOL[0], "action": SET_BOOL[1],
                    "params": bool_set(ARRIVED_FLAG, True), "next": light})
    edit.add_event({"name": light, "type": "action", "actor": SET_BOOL[0], "action": SET_BOOL[1],
                    "params": bool_set(FIELD_LIGHT_FLAG, False), "next": first})
    edit.set_entry("ActionGuide", arrived)
    return edit.apply()


def clock_runs(romfs, codec, mod):
    """the clock running from the new game's start (after starting_bags)"""
    mod.write(OPENING_FLOW, opening_with_clock(mod.read(OPENING_FLOW), mod.read(GAME_DATA_ACTOR_FROM)))
    mod.write(FIELD_FLOW, field_light_kept(mod.read(FIELD_FLOW)))


def clock_runs_on_get(mod):
    """the clock set free at every item get (after the ocarina's guide and the own items' hook)"""
    mod.write(CLOCK_GUIDE_FLOW, clock_on_get(mod.read(CLOCK_GUIDE_FLOW)))


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


# Darunia gives the Goron's Bracelet in his dance's scene Dm_Goron_0030 (its strings: Item_Gauntlet_Goron, the quest's
# EventExecuteProgressChallengeStep). His ocarina reaction (Get_StoneOfFire_PlayOcarina, always on) has two ways through:
#   - the song is not the "recommended" one (switch Event35 case 0): scene Dm_Goron_0025, then switch Event39 on
#     Get_StoneOfFire_IsAfter_SariaMelodyPlay_Exp: case 1 plays Dm_Goron_0030 (the bracelet), case 0 a camera move (Event42)
#     and a talk;
#   - it is (case 1): scene Dm_Goron_0028 (Event147), then only Darunia's mood and walk (Event149): no bracelet.
# A seed can bring Saria's Song after the quest moved past his dance (a bomb broke the boulder over Dodongo's Cavern: the quest
# jumps to DungeonStart from any step; King Dodongo ends it). Seen in game 2026-11-14 on such a save: the song played one
# scene and gave nothing (the first fix gave the bracelet after Event42 only). Fixed after Event42 and Event147 (the end of
# both ways that do not play Dm_Goron_0030): seen in game 2026-11-14, the bracelet came, but silently. A third try asked
# IsGet.Item_Gauntlet_Goron before a get-item scene: no window in game; that flag is not one of the game's (the bracelet's
# is IsGet.Armor_Child_Gauntlet_Goron; the save has no Item_Gauntlet_Goron key). Replaying Dm_Goron_0030 is no way either:
# it sets the quest back to DodongoCavernOpne even when done (IsIgnoreCompletedChallenge false).
# Then, for any item (the gift can go in the item pool): each way asks whether Darunia gave his gift
# (HavePlayedEvent.Dm_Goron_0030: the dance's scene, set by the game when it plays; read only by six Gorons' talks, for their
# after-the-dance lines) and, if not, sets it and adds the gift to the pouch, silently. Seen in game 2026-11-14 (fourth try):
# that gives the bracelet. Tries to show the item's window as well all failed in game, and took the gift with them:
#   - Dm_SY_GetInEvent:GetInEvent_NotTurn_NotNpc (the frogs' get-item scene) called from here did nothing: the event's RSDB
#     GameAnalyzedEventInfo row (Meet_Darunia_PlayOcarina) does not list Dm_SY_GetInEvent (an event loads only the
#     flowcharts its row lists: events.subflow_closure);
#   - listed there (fifth try), and GetPouchContent:GetPouchContentByActorName (the medallions' window) listed and called
#     after the flag and the add (sixth try): Darunia danced (the scene is a child event) and nothing of his own event
#     after it ran: no flag, no bracelet, no window. Extending that row's SubFlowList seems to keep his event from going
#     on after the dance. Left for later: the window from his own flowchart's actors only (no other flowchart called).
# Seventh try (that alone again): no bracelet; the save (written after the song) shows Dm_Goron_0025 played, Dm_Goron_0030
# not, the given flag false: on the first way, nothing after Dm_Goron_0025's transition ran (as the first try's add after
# Event42 never came: the bracelet of the second and fourth tries came by the other way, after Dm_Goron_0028). So the
# first way gives before its dance: after its fade-out (Event290, just before the transition Event185), when the song
# played is Saria's (GameSystemActor.EventQueryMelodyTypeForNormal 2, as Dm_SY_Ocarina numbers the songs: 0 Zelda's
# Lullaby, 1 Epona, 2 Saria, 3 Sun, 4 Time, 5 Storms, 6-11 the warps, 12 the scarecrow; this way is taken by every song not
# "recommended") and the gift was not given; the second way keeps its gift after its dance.
FIRE_FLOW = "Event/EventFlow/Get_StoneOfFire.bfevfl.zs"
TALK_FLOW = "Event/EventFlow/Npc_Goron_Darunia_Child.bfevfl.zs"
DARUNIA_SWITCH, DARUNIA_RECOMMENDED = "Event39", "Event35"
DARUNIA_STEP_FLAG = "Get_StoneOfFire_IsAfter_SariaMelodyPlay_Exp"
DARUNIA_GIVEN = "HavePlayedEvent.Dm_Goron_0030"
BRACELET = "Item_Gauntlet_Goron"
SARIA_SONG_HAD = "IsGet.Item_Melody_SariaSong"
# GameDataActor.EventQueryIsGameDataBool (and ...BoolExp) answer case 0 when the flag is TRUE, case 1 when it is FALSE: of
# the game's 1015 switches on a flag with a branch setting that same flag to true, 989 do it from case 1. Read the other
# way round from the third to the eleventh try (2026-11-14: nine tries in game failed so); found by changing Darunia's talk
# lines (his edited flow loaded, his lines came, the gift's switches skipped it).
IS_TRUE, IS_FALSE = 0, 1
# Darunia's song reaction (Get_StoneOfFire, entry Get_StoneOfFire_PlayOcarina; RSDB EventSetting row
# Meet_Darunia_PlayOcarina, from his ReplaceEventParam), read the right way: Event35 (GameSystemActor
# EventQueryIsRecommendedMelody): Saria's Song, the song asked for (case 0), fades out (Event290) and plays his dance
# Dm_Goron_0025 (Event185), then Event39 (Get_StoneOfFire_IsAfter_SariaMelodyPlay_Exp): the quest not past that step (case
# 1) plays Dm_Goron_0030, the bracelet's scene; past it (case 0), a camera move (Event42) and a talk. Another song (case 1)
# plays Dm_Goron_0028 (Event147). His talk (RSDB EventSetting Npc_Goron_Darunia_Child_DC1_TT: flow Npc_Goron_Darunia_Child,
# entry Talk; his schedule's talk after the quest and by default) is plain lines after /Mask_All (Event20).
# A seed can bring Saria's Song after the quest moved past his dance (a bomb broke the boulder over Dodongo's Cavern: the
# quest jumps to DungeonStart from any step; King Dodongo ends it): the bracelet's scene never comes. So, while he has not
# given his gift (HavePlayedEvent.Dm_Goron_0030, the scene's own flag; read only by six Gorons' talks, for their
# after-the-dance lines): Saria's Song (after its fade-out, before his dance) and his talk when Saria's Song is had set that
# flag, add the bracelet silently (the gift is had whatever follows), then show its get window (GetPouchContent:
# GetPouchContentByActorName, as the medallions' scenes give theirs: the window, the add again (had already: no change),
# the auto-save), which their RSDB GameAnalyzedEventInfo rows must list (an event loads only the flowcharts its row lists:
# events.subflow_closure). Seen in game 2026-11-14 (twelfth try): the talk gives the bracelet (silently then). The silent
# add goes when the gift joins the item pool (the window's own add gives it then).
DARUNIA_FADE, DARUNIA_FIRST_DANCE = "Event290", "Event185"
TALK_START = "Event20"
# (the talk's window: fourteenth try, GetPouchContent:GetPouchContentByActorName with only GetPouchContent listed in the
# talk's row, crashed the game at once (its get message is Dm_SY_Get's, not loaded). Now the way an NPC hands an item in a
# talk in the game, as the House of Skulltula's rewards (GatheringTokenGold Event563, an NPCTalkNoPause talk as Darunia's):
# Dm_SY_GetInEvent:GetInEvent_NotTurn by the talk's starter, Link holding the item up; its row lists the whole closure
# (ActionGuide, Dm_SY_Get, Dm_SY_GetInEvent, GetPouchContent, NaviEventCommon), as theirs does)
# Fifteenth try (that): no crash, but stuck at once in Darunia's talk shot (no item shown, no camera move: the scene's
# first steps, Link's shown item, the camera save point, the Dm_Locator warp, never ended in that talk). So the window
# alone again, GetPouchContent:GetPouchContentByActorName (no pose, camera or locator), the row as the fifteenth try's
# (Dm_SY_Get now loaded: its messages are the window's).
# Seventeenth try (his line, then that window): the line came, then the talk waited for ever on the window: the game calls
# that window by itself only in cutscenes (the medallions'). In an NPCTalkNoPause talk the game hands items as the House of
# Skulltula does: the NPC's line, then Dm_SY_GetInEvent:GetInEvent_NotTurn by the talk's starter (its first steps never
# ended in the fifteenth try, with no line before it).
GET_ITEM_FLOW, GET_ITEM_ENTRY = "Dm_SY_GetInEvent", "GetInEvent_NotTurn"
GET_ITEM_BY_STARTER = {"ASName": "Wait", "Target": 3, "NpcActorName": "Npc_EventStarter",
                       "Npc_EventStarter": {"actor": "Npc_EventStarter", "sub": ""}, "NpcInstanceName": ""}
# (what the talk's row lists: the House of Skulltula's item get closure, which loads Dm_SY_Get's messages)
DARUNIA_ROW_FLOWS = ("Dm_SY_GetInEvent", "GetInEvent_NotTurn")
# (the song's chain asks first whether the quest is past his dance's step, as Event39 asks after the dance: not past, the
# game's own bracelet scene comes and nothing is added. It shows no window: the screen is faded out there, and the window
# opened behind the black (thirteenth try, 2026-11-14: stuck on a black screen before the dance); the talk shows it)
# Twentieth try: the song's chain silent, before the dance (seen: the talk's line, the bracelet). Now (user's ask) the song
# says the gift's line too: so its chain goes after the dance, where the game itself has him talk when the quest is past
# that step: Event39 (past) -> Event42 (camera) -> Event37 (InitTalk/InitTalk_OnEvent, Arg_Actor Darunia) -> Event32 (his EventTalk,
# PlayOcarina_Talk_01). After Event37: given? set given, the silent add, his gift line (Event32's parameters, the gift's
# message), then Event32. (Not past: the game's bracelet scene, Dm_Goron_0030, as before.)
SONG_AFTER, SONG_LINE_FROM, SONG_CAMERA = "Event37", "Event32", "Event42"
DARUNIA_SONG = ("RandoDaruniaGiven", "RandoDaruniaSetGiven", "RandoDaruniaBracelet", "RandoDaruniaLine")
# Sixteenth try (the window alone at the talk's start): the talk waited for ever, nothing said (the window's first step
# closes the open message box and waits for it: there was none). Every gift of the game comes after the giver's line
# (Fado, the frogs, Skull Kid: an EventTalk, then the get): so Darunia says one of his lines first (his talk's own EventTalk
# parameters, Event6's, with another of his messages), then the window.
# Eighteenth try (his line, then GetInEvent_NotTurn as the House of Skulltula's talk): stuck after the line too. His plain
# talk (no InitTalk: the talk camera, Link joining) lets neither the item get scene nor the window run. So, for now, no
# window: the bracelet is added silently and his line marks the gift. (To try later: InitTalk/InitTalk_OnEvent before
# the get, as his quest talks do.)
DARUNIA_TALK = ("RandoDaruniaTalkGiven", "RandoDaruniaTalkSong", "RandoDaruniaTalkSetGiven", "RandoDaruniaTalkBracelet",
                "RandoDaruniaTalkLine")
# (his line: a message of his own file, added: "Here, Brother, take this <item>!" in each of the game's languages, with the
# item's own name as that language's ActorMsg/PouchContent.msbt gives it (<pouch name>_Name). The nineteenth try said
# his "Ya gotta play that song again" line, Talk_04: seen in game)
TALK_LINE_FROM = "Event6"
GIFT_MSBT = "EventFlowMsg/Npc_Goron_Darunia_Child.msbt"
GIFT_LABEL = "Rando_DaruniaGift"
TALK_LINE = "EventFlowMsg/Npc_Goron_Darunia_Child:" + GIFT_LABEL
MALS = "Mals"
MALS_DATA_ALIGNMENT = 8   # (the message archives' data block: sarc.write gives them back byte for byte with it)
POUCH_MSBT = "ActorMsg/PouchContent.msbt"
GIFT_PHRASES = {   # (by the archive's language: its name's last two letters, and the region for Chinese)
    "en": "Here, Brother, take this {item}!",
    "fr": "Tiens, frérot, c'est pour toi : {item} !",
    "es": "¡Toma, hermano, esto es para ti: {item}!",
    "de": "Hier, Bruder, das ist für dich: {item}!",
    "it": "Tieni, fratello, questo è per te: {item}!",
    "pt": "Tome, irmão, isto é para você: {item}!",
    "nl": "Hier, broeder, dit is voor jou: {item}!",
    "pl": "Proszę, bracie, to dla ciebie: {item}!",
    "ru": "Держи, брат, это тебе: {item}!",
    "ja": "兄弟、これを受け取ってくれ！ {item}だ！",
    "ko": "형제여, 이걸 받아 줘! {item}!",
    "CNzh": "兄弟，这个给你：{item}！",
    "TWzh": "兄弟，這個給你：{item}！",
}


def gift_phrase(archive):
    """the phrase for a Mals archive ("USen.Product.110.sarc.zs")"""
    region = archive.split(".")[0]
    return GIFT_PHRASES.get(region) or GIFT_PHRASES[region[2:]]


def gift_message(archive, item_name):
    """the gift's line for a Mals archive, the item's name in red"""
    before, after = gift_phrase(archive).split("{item}")
    return before.encode("utf-8") + msbt.colored(item_name) + after.encode("utf-8")


def mals_archives(romfs):
    return sorted(f for f in os.listdir(os.path.join(romfs, MALS)) if f.endswith(".sarc.zs"))


def gift_name_label(item, labels):
    """the PouchContent label naming the item Darunia gives (hints.item_name_label: its own, else its pouch form's)"""
    from .hints import item_name_label
    label = item_name_label(item, labels)
    if label is None:
        raise ValueError("no name for %s" % item)
    return label


def gift_message_files(romfs, mod, item=BRACELET):
    """{Mals archive rel: its files, Darunia's message file with the gift's line added} (the rest as the game has it); the
    item's name as each language has it, else as English has it"""
    out = {}
    english = msbt.read(sarc.read(mod.read("%s/USen.Product.110.sarc.zs" % MALS))[POUCH_MSBT])
    for f in mals_archives(romfs):
        rel = "%s/%s" % (MALS, f)
        files = sarc.read(mod.read(rel))
        pouch = msbt.read(files[POUCH_MSBT])
        name_label = gift_name_label(item, pouch.labels)
        name = pouch.text(name_label)
        if not name or not name.strip():
            name = english.text(name_label)
        if not name:
            raise ValueError("%s: no %s" % (rel, name_label))
        m = msbt.read(files[GIFT_MSBT])
        m.add(GIFT_LABEL, gift_message(f, name))
        files = dict(files)
        files[GIFT_MSBT] = m.write()
        out[rel] = files
    return out
DARUNIA_ROWS = ()   # (events whose GameAnalyzedEventInfo row must list the item get's flowcharts: none while no window)


def darunia_song_events(given, set_given, line, line_params):
    """after the dance's InitTalk (the quest past his dance's step): gift given? if not, set given (the silent add goes
    after it), his gift line, then his talk as the game has it"""
    return [{"name": given, "type": "switch", "actor": "GameDataActor", "query": "EventQueryIsGameDataBool",
             "params": {"Index": -1, "GameDataName": DARUNIA_GIVEN}, "cases": {IS_FALSE: set_given, IS_TRUE: None}},
            {"name": set_given, "type": "action", "actor": "GameDataActor", "action": "EventTriggerSetGameDataBool",
             "params": {"Index": -1, "Value": True, "GameDataName": DARUNIA_GIVEN}, "next": line},
            {"name": line, "type": "action", "actor": "Npc_Goron_Darunia_Child", "action": "EventTalk",
             "params": line_params, "next": None}]


def song_line_params(fire_flow):
    """his after-dance line's parameters (Event32's) with the gift's message"""
    e = next(e for e in fire_flow["events"] if e["name"] == SONG_LINE_FROM)
    a = fire_flow["actors"][e["actor"]]
    if (a["name"], a["actions"][e["action"]]) != ("Npc_Goron_Darunia_Child", "EventTalk"):
        raise ValueError("%s: %s is not Darunia's talk line" % (FIRE_FLOW, SONG_LINE_FROM))
    return dict(e["params"], MessageId=TALK_LINE)


def talk_line_params(talk_flow):
    """Darunia's talk line's parameters (Event6's) with the gift's message"""
    e = next(e for e in talk_flow["events"] if e["name"] == TALK_LINE_FROM)
    a = talk_flow["actors"][e["actor"]]
    if (a["name"], a["actions"][e["action"]]) != ("Npc_Goron_Darunia_Child", "EventTalk"):
        raise ValueError("%s: %s is not Darunia's talk line" % (TALK_FLOW, TALK_LINE_FROM))
    return dict(e["params"], MessageId=TALK_LINE)


def darunia_talk_events(given, song, set_given, line, line_params):
    """after the talk's first event: gift given? Saria's Song had? set given, then his line (the silent add between the
    flag and the line), then his talk as the game has it"""
    return [{"name": given, "type": "switch", "actor": "GameDataActor", "query": "EventQueryIsGameDataBool",
             "params": {"Index": -1, "GameDataName": DARUNIA_GIVEN}, "cases": {IS_FALSE: song, IS_TRUE: None}},
            {"name": song, "type": "switch", "actor": "GameDataActor", "query": "EventQueryIsGameDataBool",
             "params": {"Index": -1, "GameDataName": SARIA_SONG_HAD}, "cases": {IS_TRUE: set_given, IS_FALSE: None}},
            {"name": set_given, "type": "action", "actor": "GameDataActor", "action": "EventTriggerSetGameDataBool",
             "params": {"Index": -1, "Value": True, "GameDataName": DARUNIA_GIVEN}, "next": line},
            {"name": line, "type": "action", "actor": "Npc_Goron_Darunia_Child", "action": "EventTalk",
             "params": line_params, "next": None}]


def darunia_bracelet_after_quest(romfs, codec, mod, item=BRACELET):
    """Darunia gives his gift (the bracelet, or the item placed at his check: his dance's own scene gives it by the gift
    edit) to Saria's Song and in his talk (with his line) past his dance's step too"""
    vanilla = [a for a in evfl.read(mod.read(POUCH_ACTOR_FROM))[0]["actors"] if a["name"] == POUCH_ACTOR]
    if len(vanilla) != 1 or vanilla[0]["actions"] != [POUCH_ADD] or not vanilla[0]["params"]:
        raise ValueError("%s: not the PouchSystemActor known" % POUCH_ACTOR_FROM)
    raw = mod.read(FIRE_FLOW)
    flow = evfl.read(raw)[0]
    ev = flow["events"]
    by = {e["name"]: i for i, e in enumerate(ev)}
    switch, rec = ev[by[DARUNIA_SWITCH]], ev[by[DARUNIA_RECOMMENDED]]
    fade, dance = ev[by[DARUNIA_FADE]], ev[by[DARUNIA_FIRST_DANCE]]
    if switch.get("params") != {"GameDataName": DARUNIA_STEP_FLAG} or switch["cases"].get(IS_TRUE) != by["Event42"] or \
            (ev[switch["cases"][IS_FALSE]].get("params") or {}).get("EventName") != "Dm_Goron_0030" or \
            rec["cases"].get(IS_TRUE) != by[DARUNIA_FADE] or fade.get("next") != by[DARUNIA_FIRST_DANCE] or \
            (dance.get("params") or {}).get("EventName") != "Dm_Goron_0025" or dance.get("next") != by[DARUNIA_SWITCH]:
        raise ValueError("%s: Darunia's song reaction is not the one known" % FIRE_FLOW)
    camera, init = ev[by[SONG_CAMERA]], ev[by[SONG_AFTER]]
    if switch["cases"].get(IS_TRUE) != by[SONG_CAMERA] or camera.get("next") != by[SONG_AFTER] or \
            init["type"] != "subflow" or (init.get("flowchart"), init.get("entry")) != ("InitTalk", "InitTalk_OnEvent") or init.get("next") != by[SONG_LINE_FROM]:
        raise ValueError("%s: Darunia's after-dance talk is not the one known" % FIRE_FLOW)
    given, set_given, silent, line = DARUNIA_SONG
    raw = evfl_patch.add_events(raw, SONG_AFTER, darunia_song_events(given, set_given, line, song_line_params(flow)))
    raw = evfl_patch.add_actions(raw, set_given, POUCH_ACTOR, POUCH_ADD, vanilla[0]["params"],
                                 [(silent, start_item_params(item))])
    mod.write(FIRE_FLOW, raw)
    raw = mod.read(TALK_FLOW)
    talk = evfl.read(raw)[0]
    first = talk["events"][talk["entries"]["Talk"]]
    if first["name"] != TALK_START or first["type"] != "subflow" or first.get("next") is None:
        raise ValueError("%s: Darunia's talk does not start as known" % TALK_FLOW)
    given, song, set_given, silent, line = DARUNIA_TALK
    raw = evfl_patch.add_events(raw, TALK_START, darunia_talk_events(given, song, set_given, line,
                                                                     talk_line_params(talk)))
    raw = evfl_patch.add_actions(raw, set_given, POUCH_ACTOR, POUCH_ADD, vanilla[0]["params"],
                                 [(silent, start_item_params(item))])
    mod.write(TALK_FLOW, raw)
    for rel, files in gift_message_files(romfs, mod, item).items():
        mod.write(rel, sarc.write(files, data_alignment=MALS_DATA_ALIGNMENT))
    for row in DARUNIA_ROWS:
        list_event_subflows(mod, row, darunia_subflows(mod))


def mod_flow(mod, name):
    """the flowchart of Event/EventFlow/<name> as the mod has it (the game's when the mod does not change it), or None"""
    try:
        flows = evfl.read(mod.read("Event/EventFlow/%s.bfevfl.zs" % name))
    except (OSError, KeyError):
        return None
    return flows[0] if flows else None


def darunia_subflows(mod):
    from . import events
    return events.subflow_closure(lambda n: mod_flow(mod, n), *DARUNIA_ROW_FLOWS)


def list_event_subflows(mod, row_id, names):
    """names added to the GameAnalyzedEventInfo row's SubFlowList (the flowcharts loaded when that event starts)"""
    from . import events
    raw = mod.read(events.GAME_ANALYZED_EVENT_INFO)
    rows, version = byml.read(raw)
    if events.list_subflows(rows, row_id, names):
        mod.write(events.GAME_ANALYZED_EVENT_INFO, byml.write(rows, version, byml.endian(raw)))


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


# The Kokiri at the tunnel to the Lost Woods bridge (Npc_Kokiri_007_Child) has the same trap: his invisible wall
# (KokiriForest_Npc_Kokiri_007_Child_Blocker_00, see data/locations.json) goes only with his talk after the Kokiri Emerald
# (row Get_StoneOfForest_IsCompleted_Exp, events C1_T/C1_N); a row for after meeting Zelda (Goto_HyruleCastle_IsCompleted_Exp,
# talk C2C3_TT: "you don't visit often...") comes last and wins. The game meets Zelda only after his wall is down; a seed
# need not (seen in game, seed 7cc65105, 2026-11-15: Gohma beaten after Zelda's Letter, the wall stayed and he only said
# that). The row is taken out: the wall down, his row for that (Blocker_00 reversed) gives the same talk.
KOKIRI_007_SCHEDULE = "Component/AIScheduleParam/Npc_Kokiri_007_Child.game__component__AIScheduleParam.bgyml"
KOKIRI_007_ZELDA_ROW = "Goto_HyruleCastle_IsCompleted_Exp"
KOKIRI_007_ROWS = ("KokiriForest_Npc_Kokiri_007_Child_Blocker", "Get_StoneOfForest_IsCompleted_Exp",
                   "KokiriForest_Npc_Kokiri_007_Child_Blocker_00", KOKIRI_007_ZELDA_ROW)


def kokiri_007_schedule(data):
    """the tunnel Kokiri's schedule without its after-Zelda row"""
    doc, version = byml.read(data)
    rows = doc["ConditionalSchedule"]
    if tuple(r.get("ConditionFlag") for r in rows) != KOKIRI_007_ROWS or             [e.get("EventName") for e in rows[2]["EventEntry"]] != [e.get("EventName") for e in rows[3]["EventEntry"]] or             not rows[2].get("IsReverseCondition"):
        raise ValueError("the tunnel Kokiri's schedule rows are not the ones known")
    doc["ConditionalSchedule"] = [r for r in rows if r.get("ConditionFlag") != KOKIRI_007_ZELDA_ROW]
    return byml.write(doc, version, byml.endian(data))


def kokiri_007_keeps_blocking(romfs, codec, mod):
    mod.write(KOKIRI_007_SCHEDULE, kokiri_007_schedule(mod.read(KOKIRI_007_SCHEDULE)))


# Malon's second visit (the remake's guide to Lon Lon Ranch, SubEvent_GetEponaSong:GetEponaSong_StepCheck, run by
# Dm_SY_BancChange_EscapeDungeon at every dungeon's end): until the ranch is reached after it, once the Goron's Ruby is
# had, Malon waits at the castle (IsMalonAppear_HyruleCastleSecondTime: Malon and Npc_Hylia_Talon_Child_SecondTime, asleep
# beside her, in HyruleCastle_Static) or, with the Zora's Sapphire too, in the market (IsMalonAppear_Market). The game has
# Talon woken (Dm_HrlCastle_0020, Goto_HyruleCastle Step04) long before; a seed need not: seen in game (seed 889a1e52,
# 2026-11-15: Dodongo's Cavern and the Deku Tree before the castle) a Malon at the castle's entrance with a second Talon
# asleep beside her, and the first Talon asleep at his crates. Each visit now also waits for Talon woken, both flags
# cleared until then (OotrR's story_fixes.second_malon_after_talon, for the castle's; the market's guarded the same way).
EPONA_FLOW = "Event/EventFlow/SubEvent_GetEponaSong.bfevfl.zs"
EPONA_STONES_SWITCH = "Event38"   # (the Zora's Sapphire: had, case 0, the market's visit; not, case 1, the castle's)
MALON_FLAGS = ("IsMalonAppear_HyruleCastleSecondTime", "IsMalonAppear_Market")
# (each case's first event: the market's clears the castle's flag, then sets its own; the castle's sets its own)
EPONA_VISITS = {IS_TRUE: ("Event39", MALON_FLAGS[0], False), IS_FALSE: ("Event36", MALON_FLAGS[0], True)}
TALON_AWAKE = "HavePlayedEvent.Dm_HrlCastle_0020"
EPONA_EVENTS = ("RandoTalonAwakeMarket", "RandoTalonAwakeCastle", "RandoMalonNotYetCastle", "RandoMalonNotYetMarket")


def epona_step_check_flow(data):
    """SubEvent_GetEponaSong with Malon's second visits waiting for Talon woken"""
    from .formats import evfl_edit
    edit = evfl_edit.FlowEdit(data)
    flow = edit.flow
    switch = edit.event(EPONA_STONES_SWITCH)
    if switch["type"] != "switch" or switch["params"] != {"GameDataName": "Get_StoneOfWater_IsCompleted_Exp"}:
        raise ValueError("%s: not the stones' check known" % EPONA_FLOW)
    for case, (event, flag, value) in EPONA_VISITS.items():
        e = flow["events"][switch["cases"][case]] if case in switch.get("cases", {}) else {}
        if e.get("name") != event or e.get("type") != "action" or \
                e.get("params") != {"GameDataName": flag, "Index": -1, "Value": value}:
            raise ValueError("%s: Malon's visit %d is not the one known" % (EPONA_FLOW, case))
    market, castle, not_castle, not_market = EPONA_EVENTS
    for name, visit in ((market, EPONA_VISITS[IS_TRUE][0]), (castle, EPONA_VISITS[IS_FALSE][0])):
        edit.add_event({"name": name, "type": "switch", "actor": "GameDataActor", "query": "EventQueryIsGameDataBool",
                        "params": {"GameDataName": TALON_AWAKE, "Index": -1},
                        "cases": {IS_TRUE: visit, IS_FALSE: not_castle}})
    edit.add_event({"name": not_castle, "type": "action", "actor": "GameDataActor", "action": "EventTriggerSetGameDataBool",
                    "params": {"GameDataName": MALON_FLAGS[0], "Index": -1, "Value": False}, "next": not_market})
    edit.add_event({"name": not_market, "type": "action", "actor": "GameDataActor", "action": "EventTriggerSetGameDataBool",
                    "params": {"GameDataName": MALON_FLAGS[1], "Index": -1, "Value": False}, "next": None})
    out = edit.apply()
    i = edit.names.index(EPONA_STONES_SWITCH)
    out = evfl_patch.set_case(out, i, IS_TRUE, edit.index(market))
    return evfl_patch.set_case(out, i, IS_FALSE, edit.index(castle))


def second_malon_after_talon(romfs, codec, mod):
    mod.write(EPONA_FLOW, epona_step_check_flow(mod.read(EPONA_FLOW)))


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


# Great Fairies (with settings shuffle_great_fairies): each fairy's flow asks IsGet of her own item to know she gave it
# (Dm_FairyFountain_Din Event78: had -> RecoverSequence, she only heals; not had -> her visit, the price asked, her gift).
# With another item placed there, that flag would never come and she would sell her gift again on every visit. So the
# switch asks a flag of her own instead (a gift edit "set" in data/gifts.json, the flag added to the saved game data), set
# just before her gift (Dm_SY_GetInEvent: the one event before it is an action, made to go to the flag first). Her prices
# stay the game's (25, 50, 100, 200, 300, 500: Din, the mountain's, Farore, the crater's, Nayru, the castle's): the
# last two need the 500-rupee wallet (data/gifts.json rules). Din's asks the magic meter only to note a flag
# (GreatFairy_HasNoMPOnDinDemo): she gives either way. The other reads of these IsGet flags (her count of the fairies
# left, NPCs' lines, TriForcePoint) are left as they are.
# (check: flow, her flag, her give event, the action before it)
GREAT_FAIRIES = {
    "RC_HC_GREAT_FAIRY_REWARD": ("Dm_FairyFountain_Din", "RandoGreatFairy_Din", "Event212", "Event403"),
    "RC_ZF_GREAT_FAIRY_REWARD": ("Dm_FairyFountain_Frore", "RandoGreatFairy_Farore", "Event174", "Event147"),
    "RC_COLOSSUS_GREAT_FAIRY_REWARD": ("Dm_FairyFountain_Nayru", "RandoGreatFairy_Nayru", "Event163", "Event136"),
    "RC_DMT_GREAT_FAIRY_REWARD": ("Dm_FairyFountain_Power", "RandoGreatFairy_Power", "Event141", "Event154"),
    "RC_DMC_GREAT_FAIRY_REWARD": ("Dm_FairyFountain_Wisdom", "RandoGreatFairy_Wisdom", "Event144", "Event124"),
    "RC_OGC_GREAT_FAIRY_REWARD": ("Dm_FairyFountain_Courage", "RandoGreatFairy_Courage", "Event144", "Event131"),
}
GREAT_FAIRY_GIVEN = "RandoGreatFairyGiven"

# The Fire Arrows at Lake Hylia (with settings shuffle_lake_fire_arrows): a pickup on the platform (Obj_Arrow_Fire, map Name
# "Item", HyruleField_Adult_Static) that the lake's logic module (HyruleField_LakeHylia_Adult_Prefab_5313) creates while the
# quest SubEvent_GetFireArrow is at Step03 (the sun shot, between 6:00 and 7:30, sets it) and deletes after it. The item placed
# there is our pickup in its place (rando.pickups, itself built on Obj_Arrow_Fire: its glow and Rotate_Obj, which the scene
# plays); the sun's scene (Dm_LakeHrl_0030) finds its member by actor name and instance name, so its actor Obj_Arrow_Fire is
# renamed to the pickup's. And Dm_SY_Get / Dm_SY_Get_WithoutPlayer give any item tagged as the Fire Arrows (wherever got)
# the quest's Complete (SubEvent_GetFireArrow:GetFireArrow, case 1 of their pouch tag switch), which deletes the platform's
# pickup before it is ever shot for: that case goes on without it (Navi's line about them goes, the quest log keeps the step).
LAKE_SUN = "RC_LH_SUN"
LAKE_SUN_FLOW = "Event/EventFlow/Dm_LakeHrl_0030.bfevfl.zs"
LAKE_SUN_ACTOR = ("Obj_Arrow_Fire", "Item")
FIRE_ARROW_QUEST_CALLS = (("Event/EventFlow/Dm_SY_Get.bfevfl.zs", "Event115"),
                          ("Event/EventFlow/Dm_SY_Get_WithoutPlayer.bfevfl.zs", "Event9"))


def lake_sun_flow(data, actor):
    """the sun's scene with its Fire Arrows actor named actor"""
    flow = evfl.read(data)[0]
    found = [i for i, a in enumerate(flow["actors"]) if (a["name"], a["sub"]) == LAKE_SUN_ACTOR]
    if len(found) != 1:
        raise ValueError("%s: not the scene known" % LAKE_SUN_FLOW)
    return evfl_patch.rename_actor(data, found[0], actor)


def no_fire_arrow_quest_flow(data, switch):
    """a get flow whose Fire Arrows tag case goes on without completing their quest"""
    flow = evfl.read(data)[0]
    names = [e["name"] for e in flow["events"]]
    i = names.index(switch)
    e = flow["events"][i]
    call = flow["events"][e["cases"][1]] if e["type"] == "switch" and 1 in e.get("cases", {}) else {}
    if call.get("type") != "subflow" or (call.get("flowchart"), call.get("entry")) != ("SubEvent_GetFireArrow",
                                                                                         "GetFireArrow") \
            or call.get("next") is None:
        raise ValueError("%s: not the Fire Arrows' quest call known" % switch)
    return evfl_patch.set_case(data, i, 1, call["next"])


def lake_sun(romfs, codec, mod, actor):
    """the lake's Fire Arrows spot holding the pickup actor"""
    mod.write(LAKE_SUN_FLOW, lake_sun_flow(mod.read(LAKE_SUN_FLOW), actor))
    for rel, switch in FIRE_ARROW_QUEST_CALLS:
        mod.write(rel, no_fire_arrow_quest_flow(mod.read(rel), switch))

# The remake has the fairies found in order: Zelda's Lullaby on any fountain's Triforce mark but Din's (the castle's) asks
# IsGet.Item_DinFire (TriForcePoint Event8, after the ability switch Event132); without it Navi talks and no fairy comes.
# SoH's logic has them in any order, and a seed may put Din's Fire anywhere (seen in game, seed 7cc65105, 2026-11-15: Din's
# fairy gave a rupee, then the mountain's fountain stayed shut). The switch asks IsGet.Item_Melody_ZeldaLullaby instead,
# always true there (that point is only reached by playing it): every fountain opens in any order. On every seed: with the
# fairies as the game has them, logic does not know of that order either.
FAIRY_ORDER_FLOW = "Event/EventFlow/TriForcePoint.bfevfl.zs"
FAIRY_ORDER_EVENT = "Event8"
FAIRY_ORDER_FLAG = ("IsGet.Item_DinFire", "IsGet.Item_Melody_ZeldaLullaby")


def fairies_any_order_flow(data):
    flow = evfl.read(data)[0]
    names = [e["name"] for e in flow["events"]]
    i = names.index(FAIRY_ORDER_EVENT)
    e = flow["events"][i]
    a = flow["actors"][e["actor"]] if e["type"] == "switch" else None
    if a is None or a["queries"][e["query"]] != "EventQueryIsGameDataBool" or             (e.get("params") or {}).get("GameDataName") != FAIRY_ORDER_FLAG[0]:
        raise ValueError("%s: %s is not the Din's Fire check known" % (FAIRY_ORDER_FLOW, FAIRY_ORDER_EVENT))
    return evfl_patch.set_string_param(data, i, "GameDataName", FAIRY_ORDER_FLAG[1])


def fairies_any_order(romfs, codec, mod):
    """every Great Fairy's fountain opens whichever fairy came before"""
    mod.write(FAIRY_ORDER_FLOW, fairies_any_order_flow(mod.read(FAIRY_ORDER_FLOW)))


def great_fairy_flow(data, flag, give, before):
    """a fairy's flow (its gift edits made) with her flag set between `before` and her gift"""
    from .formats import evfl_edit
    edit = evfl_edit.FlowEdit(data)
    names = [e["name"] for e in edit.flow["events"]]
    b, g = edit.event(before), edit.event(give)
    if b["type"] != "action" or b.get("next") != names.index(give) or g.get("flowchart") != "Dm_SY_GetInEvent":
        raise ValueError("%s: not the fairy's gift as known (%s -> %s)" % (flag, before, give))
    if any(e["next"] == names.index(give) for e in edit.flow["events"] if e["name"] != before and "next" in e) or \
            any(names.index(give) in (e.get("cases") or {}).values() for e in edit.flow["events"]):
        raise ValueError("%s: her gift is reached another way" % flag)
    edit.add_event({"name": GREAT_FAIRY_GIVEN, "type": "action", "actor": "GameDataActor",
                    "action": "EventTriggerSetGameDataBool",
                    "params": {"Index": -1, "Value": True, "GameDataName": flag}, "next": give})
    edit.set_next(before, GREAT_FAIRY_GIVEN)
    return edit.apply()


def great_fairies_once(romfs, codec, mod, checks):
    """the shuffled fairies' flags set at their gift, and saved (after the gift edits: those point her switch at it)"""
    from . import gamedata, gifts
    flags = []
    for rc in sorted(checks):
        flow, flag, give, before = GREAT_FAIRIES[rc]
        rel = gifts.flow_path(flow)
        mod.write(rel, great_fairy_flow(mod.read(rel), flag, give, before))
        flags.append(flag)
    if flags:
        mod.write(gamedata.GAME_DATA, gamedata.with_bools(mod.read(gamedata.GAME_DATA), flags))
    return flags


# An ocarina found away from Saria's bridge could not be played (OotrR, user test 2026-11-11): the game shows the
# ocarina's action guide, and with it its first play event, only on the first arrival in Hyrule Field
# (Dm_SY_BancChangeArrive -> ActionGuide/OpenActionGuideSceenForOcarina). OotrR's fix (qol_patches.ocarina_guide_on_get,
# MIT), rewritten on FlowEdit: every item get ends in ActionGuide/ActionGuide; it first asks whether the Fairy Ocarina is
# in the pouch and, if so, runs that entry (which shows its guide once only: EventQueryHaveOpenedActionGuide), then goes
# on as the game does. Applied when Saria's gift is shuffled (settings shuffle_fairy_ocarina); before the dungeon items'
# hook, which goes first in turn.
OCARINA = "Item_Ocarina_Fairy"
OCARINA_OF_TIME = "Item_Ocarina_Time"   # (held alone, it needs the same guide: OotrR's 15/11 report)
OCARINA_GUIDE_ENTRY = "OpenActionGuideSceenForOcarina"
OCARINA_EVENTS = ("RandoOcarinaHeld", "RandoOcarinaGuide", "RandoOcarinaTimeHeld")
ACTION_GUIDE_FLOW = "Event/EventFlow/ActionGuide.bfevfl.zs"


def ocarina_guide(data, sync=True):
    """ActionGuide.bfevfl with the ocarina's guide run first while the Fairy Ocarina is held (sync: ocarina_sync's
    event too; a seed installed before it has it added last, after the own items' hook)"""
    from .formats import evfl_edit
    edit = evfl_edit.FlowEdit(data)
    flow = edit.flow
    first = flow["events"][flow["entries"]["ActionGuide"]]
    if first["type"] != "switch" or flow["actors"][first["actor"]]["queries"][first["query"]] != \
            "EventQueryCheckPouchContentCategory" or OCARINA_GUIDE_ENTRY not in flow["entries"]:
        raise ValueError("ActionGuide: not the flow known")
    held, guide, held_time = OCARINA_EVENTS
    edit.add_event({"name": held, "type": "switch", "actor": "PouchSystemActor", "query": "EventQueryIsExistInPouch",
                    "params": {"Actor": OCARINA, "Num": 1}, "cases": {IS_TRUE: guide, IS_FALSE: held_time}})
    edit.add_event({"name": held_time, "type": "switch", "actor": "PouchSystemActor", "query": "EventQueryIsExistInPouch",
                    "params": {"Actor": OCARINA_OF_TIME, "Num": 1}, "cases": {IS_TRUE: guide, IS_FALSE: first["name"]}})
    edit.add_event({"name": guide, "type": "subflow", "flowchart": "", "entry": OCARINA_GUIDE_ENTRY, "params": None,
                    "next": first["name"]})
    edit.set_entry("ActionGuide", held)
    return ocarina_sync(edit.apply()) if sync else edit.apply()


# Still, an ocarina found as a pickup (King Dodongo's Heart Container, seed 7cc65105; the windmill's Heart Piece, seed
# 889a1e52, 2026-11-16, its guide and play event listed) could not be put on a button until the save was reloaded. A load
# syncs the player's equipment with the pouch (Sequence/AfterLoadSaveData: SeqOneShotPouchTargetSyncEquipmentIndex); an
# event does it with UISystemActor.EventTriggerSyncPlayerEquipmentAndPouch (no parameters: the boss rush's, SubEvent_
# AllBossBattle, after it swaps the pouch). So the get of an item while an ocarina is held syncs them, before the guide.
OCARINA_SYNC = "RandoOcarinaSync"
SYNC_ACTION = ("UISystemActor", "EventTriggerSyncPlayerEquipmentAndPouch")


def ocarina_sync(data):
    """ActionGuide.bfevfl (with ocarina_guide's events) syncing the equipment with the pouch before the ocarina's guide"""
    from .formats import evfl_edit
    edit = evfl_edit.FlowEdit(data)
    held, guide, held_time = OCARINA_EVENTS
    names = edit.names
    if OCARINA_SYNC in names or not {held, guide, held_time} <= set(names):
        raise ValueError("ActionGuide: not the ocarina guide known, or synced already")
    for switch in (held, held_time):
        if edit.event(switch)["cases"].get(IS_TRUE) != names.index(guide):
            raise ValueError("ActionGuide: %s does not lead to the guide" % switch)
    edit.add_event({"name": OCARINA_SYNC, "type": "action", "actor": SYNC_ACTION[0], "action": SYNC_ACTION[1],
                    "params": None, "next": guide})
    out = edit.apply()
    for switch in (held, held_time):
        out = evfl_patch.set_case(out, names.index(switch), IS_TRUE, edit.index(OCARINA_SYNC))
    return out


# The guide goes on, when the player asks for it, with EventTransition to Dm_SY_Ocarina (its first play); an event starts
# only the events its GameAnalyzedEventInfo row lists (ChildEventList), and only the Hyrule Field arrival lists that one. From
# an item get the transition never started and ActionGuide_IsRequestOcarina (not saved) stayed set: the ocarina could not be
# put on a button until the save was reloaded (OotrR, user test 2026-11-12; here, seed 7cc65105 2026-11-15: the Fairy
# Ocarina from King Dodongo's Heart Container could not be equipped). So, as OotrR's event_info.add_child_events: every
# event listing ActionGuide among its sub-flows lists Dm_SY_Ocarina and the events it lists in turn.
OCARINA_EVENT = "Dm_SY_Ocarina"


def ocarina_child_events(rows):
    """GameAnalyzedEventInfo rows (edited in place) with OCARINA_EVENT and its children listed by every row loading
    ActionGuide; returns {row: [events added]}"""
    by = {r["__RowId"]: r for r in rows}
    wanted, todo = set(), [OCARINA_EVENT]
    while todo:
        e = todo.pop()
        if e not in wanted:
            wanted.add(e)
            todo.extend(by[e].get("ChildEventList") or [])
    added = {}
    for r in rows:
        if "ActionGuide" not in (r.get("SubFlowList") or []):
            continue
        listed = list(r.get("ChildEventList") or [])
        missing = sorted(wanted - set(listed) - {r["__RowId"]})
        if missing:
            r["ChildEventList"] = sorted(set(listed) | set(missing), key=str.lower)   # (the game's order)
            added[r["__RowId"]] = missing
    return added


def ocarina_guide_on_get(mod):
    mod.write(ACTION_GUIDE_FLOW, ocarina_guide(mod.read(ACTION_GUIDE_FLOW)))
    from . import events
    raw = mod.read(events.GAME_ANALYZED_EVENT_INFO)
    rows, version = byml.read(raw)
    if not ocarina_child_events(rows):
        raise ValueError("no event loading ActionGuide lacked %s" % OCARINA_EVENT)
    mod.write(events.GAME_ANALYZED_EVENT_INFO, byml.write(rows, version, byml.endian(raw)))
