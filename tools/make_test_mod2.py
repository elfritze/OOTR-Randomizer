"""Third test round (2026-11-12): items that are not in chests, all in Kokiri Forest as a child.

    python tools/make_test_mod2.py <romfs> <mods folder>

- the blue rupee lying in the sword training area (by the Kokiri Sword's chest) becomes a small chest with the Boomerang
  (rando.freestanding: how Heart Pieces and other items lying in the world would be randomized)
- the Kokiri who rewards breaking all the liftable rocks (Npc_Kokiri_008_Child) gives the Hookshot instead of a blue rupee
- the Kokiri who rewards the weeding (Npc_Kokiri_005_Child) gives Zelda's Lullaby instead of a blue rupee (a song from an NPC)
(rando.formats.evfl_patch: how NPCs' gifts would be randomized.) With the songs' harp and the opening skipped, as before."""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando import freestanding, patches  # noqa: E402
from rando.formats import evfl, evfl_patch, zs  # noqa: E402
from rando.mod import Mod  # noqa: E402

TRAINING_RUPEE = 6618764049130440222
GIFTS = (("Npc_Kokiri_008_Child", 218, "Item_Hookshot"), ("Npc_Kokiri_005_Child", 122, "Item_Melody_ZeldaLullaby"))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("romfs")
    p.add_argument("mods")
    a = p.parse_args()
    codec = zs.Codec(a.romfs)
    m = Mod(a.romfs, codec, os.path.join(a.mods, "HookshotRando-Test2", "romfs"))
    for rel in freestanding.write(a.romfs, codec, m, {TRAINING_RUPEE: "Item_Boomerang"}):
        print("wrote", rel)
    for flow, event, item in GIFTS:
        rel = "Event/EventFlow/%s.bfevfl.zs" % flow
        raw = codec.read(os.path.join(a.romfs, *rel.split("/")))
        old = evfl.read(raw)[0]["events"][event]["params"]["ActorName"]
        new = evfl_patch.set_string_param(raw, event, "ActorName", item)
        if evfl.read(new)[0]["events"][event]["params"]["ActorName"] != item:
            raise SystemExit("%s: the patch did not take" % flow)
        m.write(rel, new)
        print("wrote %s: event %d %s -> %s" % (rel, event, old, item))
    patches.song_models(a.romfs, codec, m)
    patches.skip_intro(a.romfs, codec, m)
    m.finish()
    for rel, old, new in m.grown:
        print("size table: %s %d -> %d" % (rel, old, new))


if __name__ == "__main__":
    main()
