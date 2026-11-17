"""A test cheat on top of an installed seed: the get of any item gives every song not yet held (silently: no get scene),
for testing what needs songs without finding them. The seed's mod as it is (every file copied), ActionGuide's ActionGuide
entry (where every item get ends) asking the pouch for each song first and adding the ones missing.

The mod made is not the seed any more (tools/verify_mod.py says so of its ActionGuide): keep the installed one to go back.

    python tools/give_songs.py <romfs> <installed mod folder (HookshotRando)> <new mod folder>"""
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_shop_test import OnTop  # noqa: E402
from rando import patches  # noqa: E402
from rando.formats import evfl_edit, zs  # noqa: E402

HAS, GIVE = "RandoCheatHas_", "RandoCheatGive_"


def with_songs(data, songs=patches.SONGS):
    edit = evfl_edit.FlowEdit(data)
    flow = edit.flow
    if any(e["name"].startswith(HAS) for e in flow["events"]):
        raise ValueError("the songs' cheat is in this ActionGuide already")
    first = flow["events"][flow["entries"]["ActionGuide"]]["name"]
    for song in reversed(songs):
        edit.add_event({"name": GIVE + song, "type": "action", "actor": patches.POUCH_ACTOR, "action": patches.POUCH_ADD,
                        "params": patches.start_item_params(song), "next": first})
        edit.add_event({"name": HAS + song, "type": "switch", "actor": patches.POUCH_ACTOR,
                        "query": "EventQueryIsExistInPouch", "params": {"Actor": song, "Num": 1},
                        "cases": {patches.IS_TRUE: first, patches.IS_FALSE: GIVE + song}})
        first = HAS + song
    edit.set_entry("ActionGuide", first)
    return edit.apply()


def main():
    romfs, base, out = sys.argv[1], sys.argv[2], sys.argv[3]
    codec = zs.Codec(romfs)
    if os.path.exists(out):
        raise SystemExit("%s exists" % out)
    shutil.copytree(base, out)
    mod = OnTop(romfs, codec, os.path.join(base, "romfs"), os.path.join(out, "romfs"))
    mod.write(patches.ACTION_GUIDE_FLOW, with_songs(mod.read(patches.ACTION_GUIDE_FLOW)))
    mod.finish()
    print("the next item got gives: %s" % ", ".join(s[len("Item_Melody_"):] for s in patches.SONGS))


if __name__ == "__main__":
    main()
