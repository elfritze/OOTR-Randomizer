"""Fifth test round (2026-11-13): items lying in the world as themselves (rando/pickups.py), not chests: test mod 3's chest for
Queen Gohma's Heart Container could not be opened (an actor the boss room's logic makes, not one the map always has).

    python tools/make_test_mod4.py <romfs> <mods folder>

Test mod 3's gifts (tools/make_test_mod3.py: shop, grass Kokiri, Saria, scrub, target game, Impa), and:
- Queen Gohma's Heart Container: a loose Hover Boots (a new pickup actor, made by the boss room's logic as the heart was)
- Kokiri Forest blue rupees lying in the village (Obj_Rupee_Blue):
  * 1564209214895161222 (up high, x -24.8 y 116.1 z -9.4): a loose Hookshot (a new pickup actor)
  * 6079532033038180376 (x -20.0 y 110.4 z -22.5, below the shop's side): a Goron Tunic (Obj_Armor_Goron, the game's own
    loose tunic: a control for the new ones)
  * 14381003020707329822 (x 1.2 y 110.2 z -27.1, beside the shop): a loose Song of Storms (a new pickup, with the harp)"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rando import patches, pickups  # noqa: E402
from rando.formats import evfl_patch, zs  # noqa: E402
from rando.mod import Mod  # noqa: E402
import make_test_mod3 as T3  # noqa: E402

LOOSE = {
    T3.GOHMA_HEART: "Item_HoverBoot",
    1564209214895161222: "Item_Hookshot",
    6079532033038180376: "Obj_Armor_Goron",
    14381003020707329822: "Item_Melody_StormSong",
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("romfs")
    p.add_argument("mods")
    a = p.parse_args()
    codec = zs.Codec(a.romfs)
    m = Mod(a.romfs, codec, os.path.join(a.mods, "HookshotRando-Test4", "romfs"))
    made = pickups.Pickups(a.romfs, codec, m)
    for rel in pickups.place(a.romfs, codec, m, LOOSE, made):
        print("wrote", rel)
    made.finish()
    print("new pickups:", made.made)
    for flow, edits in T3.FLOWS.items():
        rel = "Event/EventFlow/%s.bfevfl.zs" % flow
        data = codec.read(os.path.join(a.romfs, *rel.split("/")))
        for event, key, old, new in edits:
            if T3.param(data, event, key) != old:
                raise SystemExit("%s event %d: %s is %r, not %r" % (flow, event, key, T3.param(data, event, key), old))
            data = evfl_patch.set_string_param(data, event, key, new)
            if T3.param(data, event, key) != new:
                raise SystemExit("%s event %d: the patch did not take" % (flow, event))
        m.write(rel, data)
    patches.song_models(a.romfs, codec, m)
    patches.skip_intro(a.romfs, codec, m)
    m.finish()
    for rel, old, new in m.grown:
        print("size table: %s %d -> %d" % (rel, old, new))


if __name__ == "__main__":
    main()
