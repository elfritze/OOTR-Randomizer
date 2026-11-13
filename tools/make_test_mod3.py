"""Fourth test round (2026-11-13): the gift mechanisms not yet seen in game, all on a child's way from a new game to Zelda.

    python tools/make_test_mod3.py <romfs> <mods folder>

In the order a player meets them (research/mapping/gifts_*.json has each one's evidence):
1. the Kokiri shop owner's free Deku Shield (remake-only, during the Deku Tree quest; Dm_SY_GetInEvent:GetInEvent_Mask)
   gives the Fairy Ocarina
2. the grass-cutting Kokiri (Npc_Kokiri_005_Child) gives Saria's Song: a song never taught: can it be played?
3. Queen Gohma's Heart Container (a world item spawned by the boss room's logic) is a small chest with the Hover Boots
4. Saria's gift on the bridge (Dm_Kokiri_0155: a silent pouch add and a separate get window) gives the Boomerang
5. the Lost Woods scrub near the bridge (Deku stick upgrade, shared Enemy_Scrub_Business_Common flow) sells a Heart Piece
6. the Lost Woods target game (Dm_LostWood_0040, prize by bullet bag owned) gives the Iron Boots
7. Impa's song (Dm_MelodyGet_Zelda, after Zelda) gives the Bow, and the song lesson's own silent add of Zelda's Lullaby
   (Dm_SY_Ocarina event 26) gives a scrub seed instead: is the Lullaby still learned?
With the songs' harp and the opening skipped, as before."""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando import freestanding, patches  # noqa: E402
from rando.formats import evfl, evfl_patch, zs  # noqa: E402
from rando.mod import Mod  # noqa: E402

GOHMA_HEART = 17948245526767051747
# (flow: [(event, parameter, the game's value, new value)])
FLOWS = {
    "Npc_Kokiri_001_Shop_Child": [(110, "ActorName", "Obj_Shield_Deku", "Item_Ocarina_Fairy"),
                                  (109, "ActorName", "Obj_Shield_Deku", "Item_Ocarina_Fairy")],
    "Npc_Kokiri_005_Child": [(122, "ActorName", "Obj_Rupee_Blue", "Item_Melody_SariaSong")],
    "Dm_Kokiri_0155": [(51, "Actor", "Item_Ocarina_Fairy", "Item_Boomerang"),
                       (52, "ActorName", "Item_Ocarina_Fairy", "Item_Boomerang")],
    "Enemy_Scrub_Business_Common": [(325, "ActorName", "Item_StickBag_Medium", "Obj_Heart_Piece"),
                                    (167, "ActorName", "Item_StickBag_Medium", "Obj_Heart_Piece"),
                                    (165, "ActorName", "Item_StickBag_Large", "Obj_Heart_Piece")],
    "Dm_LostWood_0040": [(85, "ActorName", "Item_BulletBag_Medium", "Item_HeavyBoot"),
                         (84, "ActorName", "Item_BulletBag_Large", "Item_HeavyBoot")],
    "Dm_MelodyGet_Zelda": [(66, "ActorName", "Item_Melody_ZeldaLullaby", "Item_Range_Bow")],
    "Dm_SY_Ocarina": [(26, "Actor", "Item_Melody_ZeldaLullaby", "Item_ScrubBusinessSeed")],
}


def param(data, event, key):
    return evfl.read(data)[0]["events"][event]["params"][key]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("romfs")
    p.add_argument("mods")
    p.add_argument("--keep-intro", action="store_true", help="leave the opening movies (to skip with the game's own button)")
    a = p.parse_args()
    codec = zs.Codec(a.romfs)
    m = Mod(a.romfs, codec, os.path.join(a.mods, "HookshotRando-Test3", "romfs"))
    for rel in freestanding.write(a.romfs, codec, m, {GOHMA_HEART: "Item_HoverBoot"}):
        print("wrote", rel)
    for flow, edits in FLOWS.items():
        rel = "Event/EventFlow/%s.bfevfl.zs" % flow
        data = codec.read(os.path.join(a.romfs, *rel.split("/")))
        for event, key, old, new in edits:
            if param(data, event, key) != old:
                raise SystemExit("%s event %d: %s is %r, not %r" % (flow, event, key, param(data, event, key), old))
            data = evfl_patch.set_string_param(data, event, key, new)
            if param(data, event, key) != new:
                raise SystemExit("%s event %d: the patch did not take" % (flow, event))
            print("%s event %d %s: %s -> %s" % (flow, event, key, old, new))
        m.write(rel, data)
    patches.song_models(a.romfs, codec, m)
    if not a.keep_intro:
        patches.skip_intro(a.romfs, codec, m)
    m.finish()
    for rel, old, new in m.grown:
        print("size table: %s %d -> %d" % (rel, old, new))


if __name__ == "__main__":
    main()
