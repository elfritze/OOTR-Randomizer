"""A test mod for dungeon items of their own (rando/dungeon_items.py): the game as it is, the opening movies skipped, and in
Kokiri Forest the Forest Temple's boss key, map and compass and two of its small keys, each its own item, in small chests
(the kind whose flow never gave the game's own boss key):

    Mido's house top left: Item_BossKey_Forest      top right: Item_Map_Forest
    Mido's house bottom left: Item_Compass_Fire     bottom right: Item_SmallKey_Forest
    the Kokiri Sword's chest: Item_SmallKey_Forest
    the Lost Woods' small chest under the bridge (remake only; one chest drawn by the KokiriForest and LostWood maps,
    each its own copy): Item_SmallKey_Forest

After opening Mido's four and the sword's, tools/read_dungeon_info.py <game> ForestTemple FireTemple on the save should
show ForestTemple: IsGetBossKey, IsGetMap true and SmallKeyNum 2; FireTemple: IsGetCompass true.

    python tools/make_dungeon_item_test.py <romfs> <mod folder (its romfs is written inside)>"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando import chests, dungeon_items as D, patches, pickups  # noqa: E402
from rando.formats import evfl, msbt, sarc, zs  # noqa: E402
from rando.mod import Mod  # noqa: E402

LAYOUT = {
    "9725242744547055868": ("Item_Dungeon_BossKey", "ForestTemple"),    # (Mido top left)
    "4555665598794293658": ("Item_Dungeon_Map", "ForestTemple"),        # (Mido top right)
    "10831981390482426294": ("Item_Dungeon_Compass", "FireTemple"),     # (Mido bottom left: another dungeon, its colour)
    "12786193094758345086": ("Item_Dungeon_SmallKey", "ForestTemple"),  # (Mido bottom right)
    "4349272251343787229": ("Item_Dungeon_SmallKey", "ForestTemple"),   # (LW under the bridge, remake only: KokiriForest)
    "17479747339356189279": ("Item_Dungeon_SmallKey", "ForestTemple"),  # (the same chest in the LostWood map)
    "16757992849254467386": ("Item_Dungeon_SmallKey", "ForestTemple"),  # (the Kokiri Sword's chest: a second key counted)
}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    romfs, out = sys.argv[1], sys.argv[2]
    codec = zs.Codec(romfs)
    mod = Mod(romfs, codec, os.path.join(out, "romfs"))
    found = chests.scan(romfs, codec)
    made = pickups.Pickups(romfs, codec, mod)
    builder = D.Builder(romfs, codec, mod, made)
    contents = {}
    for h, (generic, dungeon) in LAYOUT.items():
        a = builder.actor(generic, dungeon)
        contents[int(h)] = (a, chests.event_for(found[int(h)], a))
    chests.write(romfs, codec, mod, contents)
    patches.skip_intro(romfs, codec, mod)
    builder.finish()
    made.finish()
    mod.finish()
    # (read back: the hook first in ActionGuide, the names in every language, the packs)
    flow = evfl.read(mod.read(D.ACTION_GUIDE))[0]
    names = [e["name"] for e in flow["events"]]
    first = flow["events"][flow["entries"][D.ACTION_GUIDE_ENTRY]]["name"]
    chain, at = [], flow["entries"][D.ACTION_GUIDE_ENTRY]
    while names[at].startswith("Rando"):
        chain.append(names[at])
        e = flow["events"][at]
        at = e["cases"][1] if e["type"] == "switch" else e["next"]
    print("ActionGuide starts at", first, "->", " -> ".join(chain), "->", names[at])
    for f in patches.mals_archives(romfs):
        m = msbt.read(sarc.read(mod.read("Mals/" + f))[D.POUCH_MSBT])
        print(f[:4], m.text("Item_BossKey_Forest_Name"), "|", m.text("Item_SmallKey_Forest_GetMessage").replace("\n", " "))
    for a in sorted(builder.made):
        files = sarc.read(codec.read(os.path.join(out, "romfs", *pickups.pack_path(a).split("/"))))
        print(a, len(files), "files;", "size table", mod.table.get(pickups.pack_path(a)))
    print("grown:", [(r, a, b) for r, a, b in mod.grown])
    # (the game data read back: each new item's IsGet flag and IsGet member)
    from rando import savefile
    from rando.formats import byml
    gd = byml.read(mod.read(D.GAME_DATA))[0]
    flags = {e["Hash"] for e in gd["Data"]["Bool"]}
    struct_ = next(e for e in gd["Data"]["Struct"] if e["Hash"] == savefile.murmur3("IsGet"))["DefaultValue"]
    members = {m["Hash"]: m["Value"] for m in struct_}
    for a in sorted(builder.made):
        print(a, "IsGet flag", savefile.murmur3("IsGet." + a) in flags,
              "member", members.get(savefile.murmur3(a)) == savefile.murmur3("IsGet." + a))
    print("MetaData", gd["MetaData"])


if __name__ == "__main__":
    main()
