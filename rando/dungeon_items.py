"""Dungeon items of their own: a boss key, map, compass or small key that belongs to one dungeon, whatever chest, gift or
spot gives it (the idea of the OotrR randomizer's key_adapter, MIT; built here on the game's own dungeon item packs).

The game's dungeon items are one actor for every dungeon (Item_Dungeon_SmallKey, _BossKey, _Map, _Compass), credited to the
dungeon Link stands in: the small key by the pouch, the other three only by the big chests' flow (Dm_SY_Treasurebox:
EventGetDungeonMap / Compass / BossKey); a dungeon's state is the saved DungeonInfo.<dungeon>.SmallKeyNum (Int: keys held,
what the locked doors use), .IsGetBossKey, .IsGetMap, .IsGetCompass (Bool).

An item of its own (Item_BossKey_Forest, Item_SmallKey_Fire...: at most 25 characters, longer names crashed OotrR's item
gets) is the game's item's pack under a new name, going into the pouch as a key item (SpecialDeal None, not the native
NotPushToPouch / SmallKey), with its RSDB rows and its names in every language ("Boss Key (Forest Temple)"). Every item get
ends in ActionGuide/ActionGuide (the chests' flows, Dm_SY_Get, Dm_SY_GetInEvent): hook() puts first there, for each such
item of the seed, its check: in the pouch? the boss key, map or compass sets its dungeon's flag (and stays in the pouch:
the check is the same each time); a small key adds one to its dungeon's SmallKeyNum and leaves the pouch. A gift that does
not end in ActionGuide (GetPouchContent: a boss's reward) applies at the next item get."""
import copy
import os
import struct

from . import gamedata, pickups as P
from .formats import byml, evfl_edit, msbt, sarc

# (each dungeon's short name, in the items' names: the 25 characters)
CODES = {"InsideTheDekuTree": "DekuTree", "DodongoCavern": "Dodongo", "InsideJabuJabuBelly": "Jabu",
         "ForestTemple": "Forest", "FireTemple": "Fire", "WaterTemple": "Water", "ShadowTemple": "Shadow",
         "SpiritTemple": "Spirit", "BottomOfTheWell": "Well", "IceCavern": "Ice", "GerudoTrainingGround": "GTG",
         "InsideGanonCastle": "Ganon"}
DUNGEON_OF_CODE = {v: k for k, v in CODES.items()}
# (the dungeon's name in its colour, in the get message; the message colours, seen 2026-11-15: 0 and 6 salmon (the game's
#  names), 2 magenta, 3 teal, 8 to 15 red, 1 4 5 7 white; no green, blue or yellow)
TEAL, MAGENTA, SALMON, RED = 3, 2, 0, 8
COLORS = {"InsideTheDekuTree": TEAL, "DodongoCavern": RED, "InsideJabuJabuBelly": TEAL, "ForestTemple": TEAL,
          "FireTemple": RED, "WaterTemple": TEAL, "ShadowTemple": MAGENTA, "SpiritTemple": SALMON,
          "BottomOfTheWell": MAGENTA, "IceCavern": TEAL, "GerudoTrainingGround": SALMON, "InsideGanonCastle": RED}
IS_TRUE, IS_FALSE = 0, 1   # (a bool query's cases, as the game's flows have them)
# (the game's item: (the kind's name in the new items, the DungeonInfo member it sets))
KINDS = {"Item_Dungeon_BossKey": ("BossKey", "IsGetBossKey"), "Item_Dungeon_Map": ("Map", "IsGetMap"),
         "Item_Dungeon_Compass": ("Compass", "IsGetCompass"), "Item_Dungeon_SmallKey": ("SmallKey", "SmallKeyNum")}
GENERIC_OF_KIND = {v[0]: k for k, v in KINDS.items()}
MAX_NAME = 25
SPECIAL_DEAL_NONE = byml.U32(3069107721)   # (murmur3 "None": the pouch keeps it, as a key item; a UInt, as read)
POUCH_MSBT = "ActorMsg/PouchContent.msbt"
LOCATION_MSBT = "LocationMsg/Location.msbt"
ACTION_GUIDE = "Event/EventFlow/ActionGuide.bfevfl.zs"
ACTION_GUIDE_ENTRY = "ActionGuide"
TEMPLATE = "Item_Medal_Forest"   # (a key item the pouch keeps: OotrR's template for its own items)
GAME_DATA = gamedata.GAME_DATA


def actor_name(generic, dungeon):
    name = "Item_%s_%s" % (KINDS[generic][0], CODES[dungeon])
    if len(name) > MAX_NAME:
        raise ValueError("%s: longer than %d characters" % (name, MAX_NAME))
    return name


def parse(actor):
    """(the game's item, dungeon) of an item of its own, or None"""
    parts = actor.split("_")
    if len(parts) == 3 and parts[0] == "Item" and parts[1] in GENERIC_OF_KIND and parts[2] in DUNGEON_OF_CODE:
        return GENERIC_OF_KIND[parts[1]], DUNGEON_OF_CODE[parts[2]]
    return None


def _param_file(actor):
    return "Actor/%s.engine__actor__ActorParam.bgyml" % actor


def _pouch_file(actor):
    return "Component/PouchContentParam/%s.game__component__PouchContentParam.bgyml" % actor


def _model_file(actor):
    return "Component/ModelInfo/%s.engine__component__ModelInfo.bgyml" % actor


def build_pack(template_files, native_files, generic, actor):
    """the new item's pack files: the key item TEMPLATE's (an item the pouch keeps: the game's dungeon items, never kept,
    were not, tested 2026-11-15) under the new name (what the pouch knows it by), with the game's item's model and a pouch
    content of its own: the template's (KeyItemDefault) with the get event played each time, as the game's keys have it"""
    pfile = _param_file(TEMPLATE)
    param, version = byml.read(template_files[pfile])
    e = byml.endian(template_files[pfile])
    param = copy.deepcopy(param)
    comps = param["Components"]
    comps["ActorNameRef"] = "?ActorSystem/ActorName/%s.engine__actor__ActorName.bgyml" % actor
    comps["ModelInfoRef"] = "?" + _model_file(actor)
    pouch_ref = comps["PouchContentRef"][1:]
    pouch, pv = byml.read(template_files[pouch_ref])
    pouch = copy.deepcopy(pouch)
    if pouch.get("SpecialDeal") != SPECIAL_DEAL_NONE:
        raise ValueError("%s: not a plain key item" % TEMPLATE)
    pouch["PlayGetEventManyTimes"] = True
    comps["PouchContentRef"] = "?" + _pouch_file(actor)
    out = {k: v for k, v in template_files.items() if k not in (pfile, _model_file(TEMPLATE))}
    out[_param_file(actor)] = byml.write(param, version, e)
    out[_pouch_file(actor)] = byml.write(pouch, pv, byml.endian(template_files[pouch_ref]))
    out[_model_file(actor)] = native_files[_model_file(generic)]
    return out


def with_flags(data, actors):
    """GameDataList with each new item's IsGet.<actor> (a saved Bool) and its member of the IsGet struct: the pouch writes
    IsGet.<name> only for the names that struct has, and keeps track of an item by it (OotrR, tested in game for its
    souls; these items, 2026-11-15)"""
    actors = sorted(actors)
    return gamedata.with_bools(data, ["IsGet." + a for a in actors], members=actors)


def texts(files, english, generic, dungeon):
    """{label: message bytes} of the new item in one archive (files: its {name: bytes}; english: the English archive's,
    for a name a language leaves empty)"""
    def get(rel, label):
        for src in (files, english):
            raw = msbt.read(src[rel]).get(label)
            if raw and raw[:-1].strip():
                return raw[:-1]
        raise ValueError("no %s %s" % (rel, label))
    place = get(LOCATION_MSBT, dungeon)
    name = get(POUCH_MSBT, generic + "_Name") + b" (" + place + b")"
    shown = msbt.COLOR_TAG + struct.pack("<H", COLORS[dungeon]) + place + msbt.COLOR_TAG + struct.pack("<H", msbt.COLOR_END)
    out = {"_Name": name, "_Caption": place,
           "_GetMessage": get(POUCH_MSBT, generic + "_GetMessage") + b"\n(" + shown + b")",
           "_GetCaption": place if generic == "Item_Dungeon_SmallKey" else get(POUCH_MSBT, generic + "_GetCaption")}
    return {actor_name(generic, dungeon) + k: v for k, v in out.items()}


def with_texts(files, english, actors):
    """an archive's files with the new items' names added to ActorMsg/PouchContent.msbt"""
    files = dict(files)
    m = msbt.read(files[POUCH_MSBT])
    for a in sorted(actors):
        generic, dungeon = parse(a)
        for label, raw in texts(files, english, generic, dungeon).items():
            m.add(label, raw)
    files[POUCH_MSBT] = m.write()
    return files


def hook_events(actors, after):
    """ActionGuide's new first events: for each item, got? (its IsGet flag: the pouch sets it, with_flags; the pouch
    itself did not show these items to EventQueryIsExistInPouch, tested 2026-11-15) then its effect; then `after` (the
    game's first). A small key counts once: its flag is cleared, and the key taken from the pouch if it is there."""
    events, first = [], after
    for a in sorted(actors, reverse=True):   # (built from the last: each falls to the next)
        generic, dungeon = parse(a)
        member = "DungeonInfo.%s.%s" % (dungeon, KINDS[generic][1])
        held, give, take = "RandoHas_" + a, "RandoGive_" + a, "RandoTake_" + a
        events.append({"name": held, "type": "switch", "actor": "GameDataActor", "query": "EventQueryIsGameDataBool",
                       "params": {"Index": -1, "GameDataName": "IsGet." + a}, "cases": {IS_TRUE: give, IS_FALSE: first}})
        if generic == "Item_Dungeon_SmallKey":
            found, clear, kept = "RandoFound_" + a, "RandoClear_" + a, "RandoKept_" + a
            events.append({"name": give, "type": "action", "actor": "GameDataActor",
                           "action": "EventTriggerAddOrSubGameDataInt",
                           "params": {"GameDataName": member, "Value": 1, "Index": -1}, "next": found})
            events.append({"name": found, "type": "action", "actor": "GameDataActor",   # (the keys found in all)
                           "action": "EventTriggerAddOrSubGameDataInt",
                           "params": {"GameDataName": "DungeonInfo.%s.SmallKeyTotalNum" % dungeon, "Value": 1,
                                      "Index": -1}, "next": clear})
            events.append({"name": clear, "type": "action", "actor": "GameDataActor",
                           "action": "EventTriggerSetGameDataBool",
                           "params": {"GameDataName": "IsGet." + a, "Value": False, "Index": -1}, "next": kept})
            events.append({"name": kept, "type": "switch", "actor": "PouchSystemActor",
                           "query": "EventQueryIsExistInPouch", "params": {"Actor": a, "Num": 1},
                           "cases": {IS_TRUE: take, IS_FALSE: first}})
            events.append({"name": take, "type": "action", "actor": "PouchSystemActor",
                           "action": "EventTriggerAddOrRemovePouchContent",
                           "params": {"Actor": a, "Num": -1, "IsEquipDIrect": False, "IsSetMessageTargetActorName": True,
                                      "IsGetEvent": False}, "next": first})
        else:
            events.append({"name": give, "type": "action", "actor": "GameDataActor",
                           "action": "EventTriggerSetGameDataBool",
                           "params": {"GameDataName": member, "Value": True, "Index": -1}, "next": first})
        first = held
    return events, first


def hook(data, actors):
    """ActionGuide.bfevfl with the items' checks first in its ActionGuide entry"""
    edit = evfl_edit.FlowEdit(data)
    flow = edit.flow
    after = flow["events"][flow["entries"][ACTION_GUIDE_ENTRY]]["name"]
    events, first = hook_events(actors, after)
    for ev in events:
        edit.add_event(ev)
    edit.set_entry(ACTION_GUIDE_ENTRY, first)
    return edit.apply()


class Builder:
    """the seed's dungeon items of their own, made once each; their names, rows and the ActionGuide hook written by
    finish (the rows with the pickups' tables: P.Pickups.finish writes them)"""

    def __init__(self, romfs, codec, mod, pickups):
        self.romfs, self.codec, self.mod, self.pickups = romfs, codec, mod, pickups
        self.made = set()

    def actor(self, generic, dungeon):
        a = actor_name(generic, dungeon)
        if a in self.made:
            return a
        def pack(name):
            return sarc.read(self.codec.read(os.path.join(self.romfs, *P.pack_path(name).split("/"))))
        self.mod.add(P.pack_path(a), sarc.write(build_pack(pack(TEMPLATE), pack(generic), generic, a)),
                     like=P.pack_path(TEMPLATE))
        # (the rows: the template's; in ActorInfo with the game's item's model, as OotrR's items)
        for table in (P.ACTOR_INFO, P.GAME_ACTOR_INFO, P.POUCH_ACTOR_INFO):
            row = copy.deepcopy(self.pickups._row(table, TEMPLATE))
            row["__RowId"] = a
            if table == P.ACTOR_INFO:
                model = self.pickups._row(table, generic)
                row["ActorName"] = a
                for k in ("FmdbName", "ModelProjectName", "ModelAabbMax", "ModelAabbMin", "AnimationResources"):
                    if k in model:
                        row[k] = copy.deepcopy(model[k])
                for k in ("InstanceHeapSize", "PreActorRenderInfoHeapSize"):
                    row[k] = max(row.get(k, 0), model.get(k, 0))
            if table == P.POUCH_ACTOR_INFO and generic == "Item_Dungeon_SmallKey":
                row["PouchStockable"] = True   # (as the game's: two got before the hook runs stay two)
            self.pickups._add(table, row)
        self.made.add(a)
        return a

    def finish(self):
        """the names in every language and the hook (call before the pickups' finish, after the other message changes)"""
        if not self.made:
            return
        from .patches import MALS, MALS_DATA_ALIGNMENT, mals_archives
        english = sarc.read(self.mod.read("%s/USen.Product.110.sarc.zs" % MALS))
        for f in mals_archives(self.romfs):
            rel = "%s/%s" % (MALS, f)
            self.mod.write(rel, sarc.write(with_texts(sarc.read(self.mod.read(rel)), english, self.made),
                                           data_alignment=MALS_DATA_ALIGNMENT))
        self.mod.write(ACTION_GUIDE, hook(self.mod.read(ACTION_GUIDE), self.made))
        self.mod.write(GAME_DATA, with_flags(self.mod.read(GAME_DATA), self.made))
