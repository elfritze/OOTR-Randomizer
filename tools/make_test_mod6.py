"""Seventh test round (2026-11-13): which part of seed "whatever"'s mod kept its Boomerang from being thrown (test mod 5:
the same chest alone works).

    python tools/make_test_mod6.py <romfs> <mods folder> <seed mod folder>

- HookshotRando-Test6a: test mod 5's chest + the opening skipped (rando.patches.skip_intro). Needs a new game.
- _HookshotRando-Test6b (off): test mod 5's chest + the seed's RSDB tables (ActorInfo, GameActorInfo, PouchActorInfo with
  its pickups' rows) and its pickup packs, as the seed had them; no intro skip."""
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando import chests, patches, pickups  # noqa: E402
from rando.formats import zs  # noqa: E402
from rando.mod import Mod  # noqa: E402

MIDO_TOP_LEFT = 9725242744547055868


def chest(romfs, codec, m):
    c = chests.scan(romfs, codec)[MIDO_TOP_LEFT]
    chests.write(romfs, codec, m, {MIDO_TOP_LEFT: ("Item_Boomerang", chests.event_for(c, "Item_Boomerang"))})


def main():
    romfs, mods, seed = sys.argv[1], sys.argv[2], sys.argv[3]
    codec = zs.Codec(romfs)
    a = Mod(romfs, codec, os.path.join(mods, "HookshotRando-Test6a", "romfs"))
    chest(romfs, codec, a)
    patches.skip_intro(romfs, codec, a)
    a.finish()
    b = Mod(romfs, codec, os.path.join(mods, "_HookshotRando-Test6b", "romfs"))
    chest(romfs, codec, b)
    seed_romfs = os.path.join(seed, "romfs")
    for t in (pickups.ACTOR_INFO, pickups.GAME_ACTOR_INFO, pickups.POUCH_ACTOR_INFO):
        b.write(t, codec.decompress(open(os.path.join(seed_romfs, *t.split("/")), "rb").read()))
    packs = os.path.join(seed_romfs, "Pack", "Actor")
    for f in sorted(os.listdir(packs)):
        if f.startswith(pickups.PREFIX):
            rel = "Pack/Actor/" + f
            b.add(rel, codec.decompress(open(os.path.join(packs, f), "rb").read()), like=pickups.pack_path(pickups.BASE))
    b.finish()
    for d in ("HookshotRando-Test6a", "_HookshotRando-Test6b"):
        for root, _, files in os.walk(os.path.join(mods, d)):
            for f in files:
                print("wrote", os.path.relpath(os.path.join(root, f), mods))


if __name__ == "__main__":
    main()
