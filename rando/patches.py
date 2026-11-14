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
