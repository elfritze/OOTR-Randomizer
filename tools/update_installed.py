"""The fixes made since a seed was installed, put on top of it: its mod as it is (every file copied, nothing rebuilt: today's
logic would fill the same seed otherwise), with each fix it lacks and its settings call for:

    the Great Fairies in any order (rando.patches.fairies_any_order: every seed)
    the tunnel Kokiri lowering his wall after Zelda was met first (rando.patches.kokiri_007_keeps_blocking: every seed)
    Malon's second visit waiting for Talon woken (rando.patches.second_malon_after_talon: every seed)
    a Fairy Ocarina found elsewhere equipped (rando.patches.ocarina_child_events: Saria's gift shuffled)
    an ocarina got usable without a reload (rando.patches.ocarina_sync: an ocarina shuffled)
    the night Gold Skulltulas there by day (rando.qol.night_module_by_day: skulltulas_day_and_night)

Fixes reaching only a new game (the clock from the start: the opening) are not for a save already made.

    python tools/update_installed.py <romfs> <installed mod folder (HookshotRando)> <new mod folder>"""
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_shop_test import OnTop  # noqa: E402
from rando import events, patches, qol  # noqa: E402
from rando.formats import byml, evfl, zs  # noqa: E402


def main():
    romfs, base, out = sys.argv[1], sys.argv[2], sys.argv[3]
    codec = zs.Codec(romfs)
    if os.path.exists(out):
        raise SystemExit("%s exists" % out)
    shutil.copytree(base, out)
    mod = OnTop(romfs, codec, os.path.join(base, "romfs"), os.path.join(out, "romfs"))
    plan = json.load(open(os.path.join(out, "placements.json"), encoding="utf-8"))
    game = lambda rel: codec.read(os.path.join(romfs, *rel.split("/"))) if rel.endswith(".zs") else \
        open(os.path.join(romfs, *rel.split("/")), "rb").read()
    done = []
    if mod.read(patches.FAIRY_ORDER_FLOW) == game(patches.FAIRY_ORDER_FLOW):
        patches.fairies_any_order(romfs, codec, mod)
        done.append("Great Fairies in any order")
    if mod.read(patches.KOKIRI_007_SCHEDULE) == game(patches.KOKIRI_007_SCHEDULE):
        patches.kokiri_007_keeps_blocking(romfs, codec, mod)
        done.append("the tunnel Kokiri's wall after Zelda")
    if mod.read(patches.EPONA_FLOW) == game(patches.EPONA_FLOW):
        patches.second_malon_after_talon(romfs, codec, mod)
        done.append("Malon's second visit after Talon woken")
    if {"RC_LW_GIFT_FROM_SARIA", "RC_HF_OCARINA_OF_TIME_ITEM"} & set(plan.get("gifts", {})):
        raw = mod.read(events.GAME_ANALYZED_EVENT_INFO)
        rows, version = byml.read(raw)
        if patches.ocarina_child_events(rows):
            mod.write(events.GAME_ANALYZED_EVENT_INFO, byml.write(rows, version, byml.endian(raw)))
            done.append("the ocarina's play event")
    guide = mod.read(patches.ACTION_GUIDE_FLOW)
    names = {e["name"] for e in evfl.read(guide)[0]["events"]}
    if patches.OCARINA_EVENTS[0] in names and patches.OCARINA_SYNC not in names:
        mod.write(patches.ACTION_GUIDE_FLOW, patches.ocarina_sync(guide))
        done.append("an ocarina got usable without a reload")
    if plan.get("settings", {}).get("skulltulas_day_and_night") and mod.read(qol.NIGHT_MODULE) == game(qol.NIGHT_MODULE):
        mod.write(qol.NIGHT_MODULE, qol.night_module_by_day(mod.read(qol.NIGHT_MODULE)))
        done.append("the night skulltulas by day")
    mod.finish()
    print("added: %s" % (", ".join(done) or "nothing (the seed has every fix)"))


if __name__ == "__main__":
    main()
