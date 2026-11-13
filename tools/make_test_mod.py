"""A test mod for five Kokiri Forest chests, the opening skip and the songs' models, to see each in game.

    python tools/make_test_mod.py <romfs> <mods folder> [--no-skip-intro]

Each chest gets an item no other one has, so what comes out of it tells which case it is (second round, 2026-11-12):
- the Kokiri Sword's chest: the Boomerang, its sword event dropped (rando.chests.event_for): the Boomerang alone, no sword
- Mido's house, its event kept: the Kokiri Sword (as in the first round, so you have a sword to go on with)
- Mido's house: the Hookshot (as in the first round)
- Mido's house: Zelda's Lullaby, shown as Sheik's harp
- Mido's house: Saria's Song, shown as Sheik's harp (every song is)
With the opening skip (the default), a new game goes past its two movies."""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando import chests, patches, settings  # noqa: E402
from rando.formats import zs  # noqa: E402
from rando.mod import Mod  # noqa: E402

KOKIRI_SWORD_CHEST = 16757992849254467386
MIDO = (4555665598794293658, 9725242744547055868, 12786193094758345086, 10831981390482426294)

TEST = {
    KOKIRI_SWORD_CHEST: "Item_Boomerang",
    MIDO[0]: "Item_Sword_Kokiri",
    MIDO[1]: "Item_Hookshot",
    MIDO[2]: "Item_Melody_ZeldaLullaby",
    MIDO[3]: "Item_Melody_SariaSong",
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("romfs")
    p.add_argument("mods")
    settings.add_arguments(p)
    a = p.parse_args()
    codec = zs.Codec(a.romfs)
    found = chests.scan(a.romfs, codec)
    contents = {}
    for h, drop in TEST.items():
        c = found[h]
        if not os.path.exists(os.path.join(a.romfs, "Pack", "Actor", drop + ".pack.zs")):
            raise SystemExit("no actor %s" % drop)
        contents[h] = (drop, chests.event_for(c, drop))
        print("%-22d %-14s %-18s -> %-26s event %s" % (h, c["gyaml"], c["drop"], drop, contents[h][1] or "(none)"))
    m = Mod(a.romfs, codec, os.path.join(a.mods, "HookshotRando-Test", "romfs"))
    for rel in chests.write(a.romfs, codec, m, contents):
        print("wrote", rel)
    patches.song_models(a.romfs, codec, m)
    print("songs: all %d shown as %s" % (len(patches.SONGS), patches.SONG_MODEL[1]))
    if a.skip_intro:
        patches.skip_intro(a.romfs, codec, m)
        print("opening movies skipped")
    m.finish()
    for rel, old, new in m.grown:
        print("size table: %s %d -> %d" % (rel, old, new))


if __name__ == "__main__":
    main()
