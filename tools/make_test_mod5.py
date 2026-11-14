"""Sixth test round (2026-11-13): the Boomerang from a chest, nothing else changed. In seed "whatever" the Boomerang from Mido's
house's top left chest could not be thrown; the game's own Boomerang (given by the inventory cheat, with or without the Bow)
can. This mod changes only that chest (no other chest, gift, pickup, table or intro skip), to tell the chest's get from the
rest of a seed's mod.

    python tools/make_test_mod5.py <romfs> <mods folder>"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando import chests  # noqa: E402
from rando.formats import zs  # noqa: E402
from rando.mod import Mod  # noqa: E402

MIDO_TOP_LEFT = 9725242744547055868   # (the chest seed "whatever" put the Boomerang in)


def main():
    romfs, mods = sys.argv[1], sys.argv[2]
    codec = zs.Codec(romfs)
    found = chests.scan(romfs, codec)
    c = found[MIDO_TOP_LEFT]
    print("chest:", c["map"], c["drop"], c["event"])
    m = Mod(romfs, codec, os.path.join(mods, "HookshotRando-Test5", "romfs"))
    chests.write(romfs, codec, m, {MIDO_TOP_LEFT: ("Item_Boomerang", chests.event_for(c, "Item_Boomerang"))})
    m.finish()
    for root, _, files in os.walk(os.path.join(mods, "HookshotRando-Test5")):
        for f in files:
            print("wrote", os.path.relpath(os.path.join(root, f), mods))


if __name__ == "__main__":
    main()
