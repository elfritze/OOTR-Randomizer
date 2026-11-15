"""New saved flags in the game's data list (GameData/GameDataList.Product.110.byml.zs): a Bool the save keeps, as the game's
own IsGet flags are (OotrR's soul_adapter, tested in game for its souls; this project's dungeon items, seen in game
2026-11-15): an entry like the template's (SaveFileIndex 0, its ResetTypeValue), false at first, and the saved part of the
list grown by 8 bytes each (MetaData: SaveDataSize and SaveDataOffsetPos of that save file, AllDataSaveSize and
AllDataSaveOffset). A save made before has no such key: the game reads the default.

    data = with_bools(data, ["RandoGreatFairy_Din"])
    data = with_bools(data, ["IsGet.Item_SmallKey_Forest"], members=["Item_SmallKey_Forest"])   # (+ its IsGet member)"""
import copy

from .formats import byml
from .savefile import murmur3

GAME_DATA = "GameData/GameDataList.Product.110.byml.zs"
TEMPLATE = "IsGet.Item_Medal_Forest"   # (a saved Bool of the game: SaveFileIndex 0)


def with_bools(data, names, members=()):
    """GameDataList with each name a new saved Bool; members: actors whose IsGet struct member (actor -> IsGet.<actor>) is
    added too (the pouch writes IsGet.<name> only for the names that struct has)"""
    root, version = byml.read(data)
    root = copy.deepcopy(root)
    d = root["Data"]
    known = {en["Hash"] for entries in d.values() for en in entries if isinstance(en, dict) and "Hash" in en}
    sample = next(en for en in d["Bool"] if en["Hash"] == murmur3(TEMPLATE))
    for name in names:
        if murmur3(name) in known:
            raise ValueError("%s: the game has it already" % name)
        entry = copy.deepcopy(sample)
        entry["Hash"], entry["DefaultValue"] = byml.U32(murmur3(name)), False
        d["Bool"].append(entry)
        known.add(murmur3(name))
    if members:
        struct = next(en for en in d["Struct"] if en["Hash"] == murmur3("IsGet"))["DefaultValue"]
        present = {m["Hash"] for m in struct}
        for a in members:
            if murmur3(a) in present:
                raise ValueError("IsGet member %s: the game has it already" % a)
            struct.append({"Hash": byml.U32(murmur3(a)), "Value": byml.U32(murmur3("IsGet." + a))})
    meta, i, grown = root["MetaData"], sample["SaveFileIndex"], 8 * len(names)
    meta["SaveDataSize"][i] += grown
    meta["SaveDataOffsetPos"][i] += grown
    meta["AllDataSaveSize"] += grown
    meta["AllDataSaveOffset"] += grown
    return byml.write(root, version, byml.endian(data))
