"""A generated mod against the game's own files: each chest holds what placements.json says, with its event as
rando.chests.event_for gives it and no substitute left where its item changed; each item lying in the world is the planned
pickup (only its Gyaml and its height changed); each gift's flow differs from the game's in exactly data/gifts.json's
parameters, set to the planned item; nothing else in any map or flow changed; every new pickup has its pack and its rows;
every file fits its resource size table entry; the Zora's River walls get their Presence; the songs show the harp; the opening's two movies point at the empty event.

    python tools/verify_mod.py <romfs> <mod folder (with romfs, placements.json)>"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando import chests, dungeon_items, generate, gifts, hints, patches, pickups, qol, settings as rando_settings  # noqa: E402
from rando import gamedata, items as rando_items  # noqa: E402
from rando.formats import evfl  # noqa: E402
from rando.events import EVENT_SETTING  # noqa: E402
from rando.formats import byml, msbt, restbl, sarc, zs  # noqa: E402
from rando.mod import RSTB, align32  # noqa: E402


def key(v):
    return json.dumps(v, sort_keys=True, default=str)


def hint_problems(romfs, codec, mod_romfs, chosen, stones, plan):
    """the gossip stones: their talk as the setting says (the game's events, but where the talk starts and Event6's next),
    a hint on every stone when hints are on (none when off), and each item hint naming what its check holds"""
    out = []
    rule = chosen["gossip_stone_hints"]
    rel = hints.GOSSIP_FLOW
    path = os.path.join(mod_romfs, *rel.split("/"))
    game = codec.read(os.path.join(romfs, *rel.split("/")))
    if rule in ("none", "mask_of_truth"):
        if os.path.exists(path):
            out.append("%s in the mod (the stones' rule is the game's: %s)" % (rel, rule))
    elif not os.path.exists(path):
        out.append("%s not in the mod (the stones' rule: %s)" % (rel, rule))
    else:
        a, b = evfl.read(game)[0], evfl.read(codec.read(path))[0]
        names = [e["name"] for e in b["events"]]
        ev = {e["name"]: e for e in b["events"]}
        first = b["events"][b["entries"]["Talk"]]
        ok = names[ev[hints.TALK_INIT]["next"]] == hints.TALK_SECRET
        if rule == "need_nothing":
            ok = ok and first["name"] == hints.TALK_INIT and len(b["events"]) == len(a["events"])
        else:
            actor = b["actors"][first.get("actor", 0)]
            ok = ok and first["name"] == hints.AGONY_EVENT and first["type"] == "switch" and \
                first["params"] == {"Actor": hints.AGONY, "Num": 1} and actor["name"] == "PouchSystemActor" and \
                actor["queries"][first["query"]] == "EventQueryIsExistInPouch" and \
                {k: names[v] for k, v in first["cases"].items()} == {0: hints.TALK_INIT, 1: hints.TALK_NAVI} and \
                len(b["events"]) == len(a["events"]) + 1
        olds = [dict(e) for e in b["events"][:len(a["events"])]]
        for e in olds:
            if e["name"] == hints.TALK_INIT:
                e["next"] = a["events"][[x["name"] for x in a["events"]].index(hints.TALK_INIT)]["next"]
        entries = dict(b["entries"], Talk=a["entries"]["Talk"])
        if not (ok and olds == a["events"] and entries == a["entries"]):
            out.append("%s: not the game's with the stones talking as %s" % (rel, rule))
    if rule == "none":
        if stones:
            out.append("hints planned though gossip stone hints are off")
        return out
    if set(stones) != set(hints.STONES):
        out.append("hints: not one per stone (%d planned, %d stones)" % (len(stones), len(hints.STONES)))
    table = {l["id"]: l for l in generate.load_table()["locations"]}
    gift_table = {c["id"]: c for c in generate.load_gifts()["checks"]}

    def holds(lid):
        if lid in table:
            c = plan["chests"].get(str(table[lid]["hash"]))
            return c and c["item"]
        if lid in plan.get("gifts", {}):
            return plan["gifts"][lid]
        if lid in gift_table:
            for a in gift_table[lid].get("loose") or []:
                if str(a["hash"]) in plan.get("loose", {}):
                    return plan["loose"][str(a["hash"])]
        return None
    from rando import items as I
    for label, h in sorted(stones.items()):
        if h["kind"] in ("item", "always"):
            got = holds(h["location"])
            if got is not None and I.canonical(got) != I.canonical(h["item"]):
                out.append("hint on %s: %s holds %s, not %s" % (label, h["location"], got, h["item"]))
        if h["kind"] in ("woth", "foolish", "item", "always") and h.get("location") and \
                hints.area_of(h["location"], (table.get(h["location"]) or {}).get("map")) != h["area"]:
            out.append("hint on %s: %s is not in %s" % (label, h["location"], h["area"]))
    return out


def main():
    romfs, mod = sys.argv[1], sys.argv[2]
    mod_romfs = os.path.join(mod, "romfs")
    codec = zs.Codec(romfs)
    plan = json.load(open(os.path.join(mod, "placements.json"), encoding="utf-8"))
    want = {int(h): (c["item"], c["event"]) for h, c in plan["chests"].items()}
    chosen = rando_settings.normalized(plan.get("settings", {}), legacy=True)
    nocturnal_seen = 0
    loose = {int(h): a for h, a in plan.get("loose", {}).items()}
    loose_seen = set()
    found = chests.scan(romfs, codec)
    problems, seen = [], set()
    walls, walls_seen = patches.ZR_RIVER_WALLS, set()
    table = restbl.Table(codec.read(os.path.join(mod_romfs, *RSTB.split("/"))))
    original_table = restbl.Table(codec.read(os.path.join(romfs, *RSTB.split("/"))))
    for rel in chests.map_files(romfs):
        mod_path = os.path.join(mod_romfs, *rel.split("/"))
        a, _ = byml.read(codec.read(os.path.join(romfs, rel)))
        if not os.path.exists(mod_path):
            for x in a.get("Actors", []):
                if int(x.get("Hash", 0)) in want and chests.is_chest(x):
                    problems.append("%s: chest %s is not in the mod" % (rel, x["Hash"]))
            continue
        data = codec.read(mod_path)
        b, _ = byml.read(data)
        if {k: v for k, v in a.items() if k != "Actors"} != {k: v for k, v in b.items() if k != "Actors"}:
            problems.append("%s: something besides the actors changed" % rel)
        if len(a["Actors"]) != len(b["Actors"]):
            problems.append("%s: actor count changed" % rel)
        for x, y in zip(a["Actors"], b["Actors"]):
            h = int(x.get("Hash", 0))
            if h in want and chests.is_chest(x):
                seen.add(h)
                item, event = want[h]
                dyn = y.get("Dynamic") or {}
                if dyn.get(chests.DROP) != item:
                    problems.append("%s: chest %d holds %s, planned %s" % (rel, h, dyn.get(chests.DROP), item))
                if dyn.get(chests.EVENT) != event or event != chests.event_for(found[h], item):
                    problems.append("%s: chest %d event %s, planned %s" % (rel, h, dyn.get(chests.EVENT), event))
                if item != found[h]["drop"] and any(k in dyn for k in chests.SUBSTITUTE):
                    problems.append("%s: chest %d keeps a substitute" % (rel, h))
                rest_x = {k: v for k, v in (x.get("Dynamic") or {}).items() if k not in (chests.DROP, chests.EVENT) + chests.SUBSTITUTE}
                rest_y = {k: v for k, v in dyn.items() if k not in (chests.DROP, chests.EVENT) + chests.SUBSTITUTE}
                if rest_x != rest_y or key({k: v for k, v in x.items() if k != "Dynamic"}) != key({k: v for k, v in y.items() if k != "Dynamic"}):
                    problems.append("%s: chest %d changed beyond its content" % (rel, h))
            elif h in loose:
                loose_seen.add(h)
                name = loose[h] if loose[h].startswith("Obj_") else pickups.name_for(loose[h])
                if y.get("Gyaml") != name:
                    problems.append("%s: %d is %s, planned %s" % (rel, h, y.get("Gyaml"), name))
                if key({k: v for k, v in x.items() if k not in ("Gyaml", "Translate")}) !=                         key({k: v for k, v in y.items() if k not in ("Gyaml", "Translate")}) or                         [x["Translate"][0], x["Translate"][2]] != [y["Translate"][0], y["Translate"][2]] or                         not 0 <= y["Translate"][1] - x["Translate"][1] <= 0.6:
                    problems.append("%s: %d changed beyond its item and height" % (rel, h))
            elif chosen["skulltulas_day_and_night"] and qol.is_nocturnal(x):
                nocturnal_seen += 1
                if key(y) != key(dict(x, Dynamic=dict(x["Dynamic"], **{qol.NOCTURNAL: False}))):
                    problems.append("%s: skulltula %d changed beyond its night-only flag" % (rel, h))
            elif h in walls.get(rel, ((), ()))[1]:
                walls_seen.add(h)
                if key(y) != key(dict(x, Presence=patches.zr_river_presence(walls[rel][0]))):
                    problems.append("%s: river wall %d is not given its never-met Presence alone" % (rel, h))
            elif key(x) != key(y):
                problems.append("%s: actor %s (%s) changed" % (rel, x.get("Hash"), x.get("Gyaml")))
        need = align32(len(data)) + original_table.get(rel) - align32(len(codec.read(os.path.join(romfs, rel))))
        if table.get(rel) < need:
            problems.append("%s: %d bytes, its table entry %d" % (rel, len(data), table.get(rel)))
    every_wall = {h for _, hs in walls.values() for h in hs}
    if walls_seen != every_wall:
        problems.append("Zora's River walls left as they were: %s" % sorted(every_wall - walls_seen))
    missing = set(want) - seen
    if missing:
        problems.append("planned chests not found in any map: %s" % sorted(missing)[:5])
    if set(loose) - loose_seen:
        problems.append("planned loose items not found in any map: %s" % sorted(set(loose) - loose_seen)[:5])
    # (the gifts: exactly the table's parameters changed, each to its check's item)
    table_g = {c["id"]: c for c in generate.load_gifts()["checks"]}
    expect = {}
    for cid, actor in plan.get("gifts", {}).items():
        for e in table_g[cid]["edits"]:
            expect[(e["flow"], e["event"], e["param"])] = e.get("set", actor)
    flows = {f for f, _, _ in expect}
    flow_dir = os.path.join(mod_romfs, "Event", "EventFlow")
    in_mod = {f[:-len(".bfevfl.zs")] for f in os.listdir(flow_dir)} if os.path.isdir(flow_dir) else set()
    own = {p.rsplit("/", 1)[-1][:-len(".bfevfl.zs")] for p in (patches.OPENING_FLOW, patches.WATER_FLOW, patches.FIRE_FLOW,
                                                                  patches.TALK_FLOW)}
    if chosen["fast_chests"]:   # (checked on their own below)
        own |= {p.rsplit("/", 1)[-1][:-len(".bfevfl.zs")] for p in (qol.BIG_CHEST_FLOW, qol.SMALL_CHEST_FLOW)}
    if chosen["gossip_stone_hints"] in ("need_nothing", "stone_of_agony"):   # (the stones' talk: hint_problems)
        own.add(hints.GOSSIP_FLOW.rsplit("/", 1)[-1][:-len(".bfevfl.zs")])
    own_items = {item for item, _ in want.values() if dungeon_items.parse(item)} | \
        {a for a in loose.values() if dungeon_items.parse(a)}   # (dungeons' own items: below)
    ocarina = generate.SARIA in plan.get("gifts", {})   # (ActionGuide: the ocarina's guide, then the own items' hook)
    if own_items or ocarina:
        own.add(dungeon_items.ACTION_GUIDE.rsplit("/", 1)[-1][:-len(".bfevfl.zs")])
    fairies = sorted(rc for rc in plan.get("gifts", {}) if rc in patches.GREAT_FAIRIES)   # (their flows: below, with
    fairy_flows = {patches.GREAT_FAIRIES[rc][0] for rc in fairies}                         #  their gift edits)
    own |= fairy_flows
    if (own - fairy_flows) & flows:   # (those flows are checked on their own below, without gift edits)
        problems.append("a gift edit in %s (its own check does not cover gifts)" % sorted(own & flows))
    for f in sorted((flows | in_mod) - own):
        rel = gifts.flow_path(f)
        if f not in in_mod:
            problems.append("%s: not in the mod" % rel)
            continue
        a = evfl.read(codec.read(os.path.join(romfs, *rel.split("/"))))[0]
        b = evfl.read(codec.read(os.path.join(mod_romfs, *rel.split("/"))))[0]
        if key({k: v for k, v in a.items() if k != "events"}) != key({k: v for k, v in b.items() if k != "events"}) or                 len(a["events"]) != len(b["events"]):
            problems.append("%s: more than events changed" % rel)
            continue
        for i, (x, y) in enumerate(zip(a["events"], b["events"])):
            for k in set((x.get("params") or {})) | set((y.get("params") or {})):
                vx, vy = (x.get("params") or {}).get(k), (y.get("params") or {}).get(k)
                want_v = expect.get((f, i, k), vx)
                if vy != want_v:
                    problems.append("%s event %d %s: %r, planned %r" % (rel, i, k, vy, want_v))
            if key({k: v for k, v in x.items() if k != "params"}) != key({k: v for k, v in y.items() if k != "params"}):
                problems.append("%s event %d: changed beyond its parameters" % (rel, i))
    # (the new pickups: a pack each, and their rows)
    made = {a for a in loose.values() if not a.startswith("Obj_")}
    for t in (pickups.ACTOR_INFO, pickups.GAME_ACTOR_INFO, pickups.POUCH_ACTOR_INFO):
        path = os.path.join(mod_romfs, *t.split("/"))
        ids = {r["__RowId"] for r in byml.read(codec.read(path))[0]} if os.path.exists(path) else set()
        for a in made:
            if pickups.name_for(a) not in ids:
                problems.append("%s: no row %s" % (t, pickups.name_for(a)))
    for a in made:
        if not os.path.exists(os.path.join(mod_romfs, *pickups.pack_path(pickups.name_for(a)).split("/"))):
            problems.append("no pack for %s" % pickups.name_for(a))
    # (the shuffled Great Fairies: each one's flow the game's with her gift edits and her flag set before her gift)
    for rc in fairies:
        flow, flag, give, before = patches.GREAT_FAIRIES[rc]
        rel = gifts.flow_path(flow)
        edits = gifts.edits_by_flow([(table_g[rc], plan["gifts"][rc])])[flow]
        want_flow = patches.great_fairy_flow(gifts.edited(codec.read(os.path.join(romfs, *rel.split("/"))), flow, edits),
                                             flag, give, before)
        path = os.path.join(mod_romfs, *rel.split("/"))
        if not os.path.exists(path) or evfl.read(codec.read(path)) != evfl.read(want_flow):
            problems.append("%s: not the game's with %s's gift and once-flag" % (rel, rc))
    # (the saved game data: the game's with the fairies' flags, then the own items' IsGet flags, as generate adds them)
    game_data = codec.read(os.path.join(romfs, *dungeon_items.GAME_DATA.split("/")))
    want_data = game_data
    if fairies:
        want_data = gamedata.with_bools(want_data, [patches.GREAT_FAIRIES[rc][1] for rc in fairies])
    if own_items:
        want_data = dungeon_items.with_flags(want_data, own_items)
    data_path = os.path.join(mod_romfs, *dungeon_items.GAME_DATA.split("/"))
    if want_data is game_data:
        if os.path.exists(data_path):
            problems.append("%s in the mod with nothing to add to it" % dungeon_items.GAME_DATA)
    elif not os.path.exists(data_path) or byml.read(codec.read(data_path))[0] != byml.read(want_data)[0]:
        problems.append("%s: not the game's with the fairies' and own items' flags" % dungeon_items.GAME_DATA)
    # (the dungeons' own items: a pack each, their rows, the hook first in ActionGuide)
    if own_items:
        for t in (pickups.ACTOR_INFO, pickups.GAME_ACTOR_INFO, pickups.POUCH_ACTOR_INFO):
            ids = {r["__RowId"] for r in byml.read(codec.read(os.path.join(mod_romfs, *t.split("/"))))[0]}
            problems += ["%s: no row %s" % (t, a) for a in sorted(own_items - ids)]
        for a in sorted(own_items):
            if not os.path.exists(os.path.join(mod_romfs, *pickups.pack_path(a).split("/"))):
                problems.append("no pack for %s" % a)
    if own_items or ocarina:   # (ActionGuide: the ocarina's guide first, then the own items' hook before it)
        guide = codec.read(os.path.join(romfs, *dungeon_items.ACTION_GUIDE.split("/")))
        if ocarina:
            guide = patches.ocarina_guide(guide)
        if own_items:
            guide = dungeon_items.hook(guide, own_items)
        path = os.path.join(mod_romfs, *dungeon_items.ACTION_GUIDE.split("/"))
        if not os.path.exists(path) or evfl.read(codec.read(path)) != evfl.read(guide):
            problems.append("%s: not the game's with the ocarina's guide and the own items' hook" %
                            dungeon_items.ACTION_GUIDE)
    for h, (item, _) in sorted(want.items()):   # (a dungeon item as the game has it only where it does the same)
        d = rando_items.dungeon_item(item, found[h]["map"])
        if d and rando_items.dungeon_form(rando_items.own_actor(d[0], d[1]), found[h]["map"],
                                          found[h]["gyaml"] in chests.SMALL_FLOW) != item:
            problems.append("chest %d (%s): %s, not the form it should be written in" % (h, found[h]["map"], item))
    # (every file of the mod fits its size table entry)
    for root, _, files in os.walk(mod_romfs):
        for fn in files:
            rel = os.path.relpath(os.path.join(root, fn), mod_romfs).replace(os.sep, "/")
            if rel == RSTB:
                continue
            path = os.path.join(root, fn)
            size = len(codec.read(path)) if fn.endswith(".zs") else os.path.getsize(path)
            entry = table.get(rel)
            if entry is None or entry < size:
                problems.append("%s: %d bytes, its table entry %s" % (rel, size, entry))
    # (the songs' model and the opening's events)
    for song in patches.SONGS:
        files = sarc.read(codec.read(os.path.join(mod_romfs, "Pack", "Actor", song + ".pack.zs")))
        info, _ = byml.read(files["Component/ModelInfo/%s.engine__component__ModelInfo.bgyml" % song])
        if (info["ModelProjectName"], info["FmdbName"]) != patches.SONG_MODEL:
            problems.append("%s: model %s" % (song, info))
    # (the bombs: the free lift grade in each pack holding the bomb's lift file, nothing else in those packs changed)
    for actor in patches.BOMB_LIFT_PACKS:
        rel = "Pack/Actor/%s.pack.zs" % actor
        path = os.path.join(mod_romfs, *rel.split("/"))
        if not os.path.exists(path):
            problems.append("%s: not in the mod (bombs would need the bracelet)" % rel)
            continue
        a = sarc.read(codec.read(os.path.join(romfs, *rel.split("/"))))
        b = sarc.read(codec.read(path))
        if set(a) != set(b) or any(a[k] != b[k] for k in a if k != patches.BOMB_LIFT):
            problems.append("%s: more than the bomb's lift file changed (bomb flowers keep the bracelet)" % rel)
        x, y = byml.read(a[patches.BOMB_LIFT])[0], byml.read(b[patches.BOMB_LIFT])[0]
        if y.get("LiftGrade") != patches.FREE_LIFT_GRADE or {k: v for k, v in x.items() if k != "LiftGrade"} !=                 {k: v for k, v in y.items() if k != "LiftGrade"}:
            problems.append("%s: bomb lift %r" % (rel, y.get("LiftGrade")))
    # (the opening: the game's flow, the two starting bags added after its first event)
    path = os.path.join(mod_romfs, *patches.OPENING_FLOW.split("/"))
    if not os.path.exists(path):
        problems.append("the opening does not give the small quiver and seed bag")
    else:
        a = evfl.read(codec.read(os.path.join(romfs, *patches.OPENING_FLOW.split("/"))))[0]
        b = evfl.read(codec.read(path))[0]
        n = len(a["events"])
        anchor = [e["name"] for e in a["events"]].index(patches.OPENING_ANCHOR)
        added = b["events"][n:]
        ok = len(added) == len(patches.START_ITEMS) and b["events"][anchor]["next"] == n
        for k, (e, item) in enumerate(zip(added, patches.START_ITEMS)):
            actor = b["actors"][e.get("actor", 0)]
            ok = ok and e["type"] == "action" and actor["name"] == patches.POUCH_ACTOR and \
                actor["actions"][e["action"]] == patches.POUCH_ADD and e["params"] == patches.start_item_params(item) and \
                e["next"] == (n + k + 1 if k + 1 < len(added) else a["events"][anchor]["next"])
        b["events"][anchor]["next"] = a["events"][anchor]["next"]
        ok = ok and b["events"][:n] == a["events"] and b["actors"][:len(a["actors"])] == a["actors"] and \
            b["entries"] == a["entries"]
        if not ok:
            problems.append("the opening: not the game's with the starting quiver and seed bag")
    # (the water quest: the game's flow, the arrival scene marked played after the letter's step)
    path = os.path.join(mod_romfs, *patches.WATER_FLOW.split("/"))
    if not os.path.exists(path):
        problems.append("the letter's step does not mark Zora's Domain's arrival played")
    else:
        a = evfl.read(codec.read(os.path.join(romfs, *patches.WATER_FLOW.split("/"))))[0]
        b = evfl.read(codec.read(path))[0]
        n, i = len(a["events"]), patches.letter_step_event(a)
        added = b["events"][n:]
        ok = len(added) == 1 and b["events"][i]["next"] == n and added[0]["next"] == a["events"][i]["next"] and \
            added[0]["params"] == patches.zora_arrival_params() and \
            b["actors"][added[0]["actor"]]["name"] == "GameDataActor" and \
            b["actors"][added[0]["actor"]]["actions"][added[0]["action"]] == "EventTriggerSetGameDataBool"
        b["events"][i]["next"] = a["events"][i]["next"]
        if not (ok and b["events"][:n] == a["events"] and b["actors"] == a["actors"] and b["entries"] == a["entries"]):
            problems.append("the water quest's flow: not the game's with the arrival scene marked after the letter")
    # (Darunia: his song reaction's flow and his talk's, the game's with the gift chain after the song's fade-out and after
    # the talk's first event; his talk's row listing the window's flowcharts)
    def darunia_chain(rel, after, names, spec, set_given, silent):
        """problems of one flow: the game's, but `after` -> the spec's events, the silent add inserted after the flag set
        (taking the flag set's next as its own)"""
        path = os.path.join(mod_romfs, *rel.split("/"))
        if not os.path.exists(path):
            return ["%s: not in the mod (Darunia's gift)" % rel]
        a = evfl.read(codec.read(os.path.join(romfs, *rel.split("/"))))[0]
        b = evfl.read(codec.read(path))[0]
        n = len(a["events"])
        new = {e["name"]: k for k, e in enumerate(b["events"]) if k >= n}
        if set(new) != set(names):
            return ["%s: added events %s, not %s" % (rel, sorted(new), sorted(names))]
        i = [e["name"] for e in a["events"]].index(after)
        orig = a["events"][i]["next"]

        def target(t):
            return orig if t is None else new[t]
        ok = b["events"][i]["next"] == new[names[0]]
        after_silent = None
        for e in spec:
            got = b["events"][new[e["name"]]]
            actor = b["actors"][got["actor"]] if "actor" in got else None
            ok = ok and got["type"] == e["type"] and got["params"] == e["params"]
            if e["type"] == "switch":
                ok = ok and got["cases"] == {k: target(t) for k, t in e["cases"].items()} and \
                    actor["name"] == e["actor"] and actor["queries"][got["query"]] == e["query"]
            elif e["type"] == "action":
                if e["name"] == set_given:
                    after_silent = target(e["next"])
                    ok = ok and got["next"] == new[silent]
                else:
                    ok = ok and got["next"] == target(e["next"])
                ok = ok and actor["name"] == e["actor"] and actor["actions"][got["action"]] == e["action"]
            else:
                ok = ok and (got["flowchart"], got["entry"]) == (e["flowchart"], e["entry"]) and \
                    got["next"] == target(e["next"])
        add = b["events"][new[silent]]
        ok = ok and add["params"] == patches.start_item_params(darunia_item) and add["next"] == after_silent and \
            b["actors"][add["actor"]]["name"] == patches.POUCH_ACTOR and \
            b["actors"][add["actor"]]["actions"][add["action"]] == patches.POUCH_ADD
        b["events"][i]["next"] = orig
        if not (ok and b["events"][:n] == a["events"] and b["actors"][:len(a["actors"])] == a["actors"] and
                b["entries"] == a["entries"]):
            return ["%s: not the game's with Darunia's gift chain after %s" % (rel, after)]
        return []
    darunia_item = plan.get("gifts", {}).get(generate.DARUNIA, patches.BRACELET)   # (his gift: the plan's, else his own)
    given, set_given, silent, line = patches.DARUNIA_SONG
    fire_game = evfl.read(codec.read(os.path.join(romfs, *patches.FIRE_FLOW.split("/"))))[0]
    problems += darunia_chain(patches.FIRE_FLOW, patches.SONG_AFTER, patches.DARUNIA_SONG,
                              patches.darunia_song_events(given, set_given, line, patches.song_line_params(fire_game)),
                              set_given, silent)
    given, song, set_given, silent, line = patches.DARUNIA_TALK
    talk_game = evfl.read(codec.read(os.path.join(romfs, *patches.TALK_FLOW.split("/"))))[0]
    problems += darunia_chain(patches.TALK_FLOW, patches.TALK_START, patches.DARUNIA_TALK,
                              patches.darunia_talk_events(given, song, set_given, line,
                                                          patches.talk_line_params(talk_game)), set_given, silent)
    from rando import events as rando_events
    info_path = os.path.join(mod_romfs, *rando_events.GAME_ANALYZED_EVENT_INFO.split("/"))
    game_info = byml.read(codec.read(os.path.join(romfs, *rando_events.GAME_ANALYZED_EVENT_INFO.split("/"))))[0]
    mod_info = byml.read(codec.read(info_path))[0] if os.path.exists(info_path) else game_info
    need = patches.darunia_subflows(type("GameOnly", (), {"read": lambda self, rel: codec.read(
        os.path.join(romfs, *rel.split("/")))})())
    expected = []
    for r in game_info:
        r = dict(r)
        if r.get("__RowId") in patches.DARUNIA_ROWS:
            r["SubFlowList"] = sorted(set(r.get("SubFlowList") or []) | need)
        expected.append(r)
    if mod_info != expected:
        problems.append("%s: not the game's with Darunia's events loading the item window" %
                        rando_events.GAME_ANALYZED_EVENT_INFO)
    # (Darunia's line: each message archive the game's, his message file with the gift's label only)
    # (and the gossip stones' rumors replaced by the plan's hints)
    game_only = type("GameOnly", (), {"read": lambda self, rel: codec.read(os.path.join(romfs, *rel.split("/")))})()
    stones = plan.get("hints") or {}
    problems += hint_problems(romfs, codec, mod_romfs, chosen, stones, plan)
    # (a map, compass or boss key only in a big chest: the small chests' flow never gives them)
    for h, (item, _) in sorted(want.items()):
        if item in rando_items.BIG_CHEST_ONLY and found[h]["gyaml"] in chests.SMALL_FLOW:
            problems.append("chest %d (%s, %s): %s in a small chest, which never gives it" % (
                h, found[h]["map"], found[h]["gyaml"], item))
    english_files = sarc.read(game_only.read("%s/%s" % (patches.MALS, hints.ENGLISH)))
    if own_items:
        english_files = dungeon_items.with_texts(english_files, english_files, own_items)
    english_names = hints.Names(english_files)
    for rel, want_files in patches.gift_message_files(romfs, game_only, darunia_item).items():
        path = os.path.join(mod_romfs, *rel.split("/"))
        if not os.path.exists(path):
            problems.append("%s not in the mod (Darunia's line has no text)" % rel)
            continue
        got = sarc.read(codec.read(path))
        if own_items:   # (the own items' names, added before Darunia's line and the hints)
            want_files = dungeon_items.with_texts(want_files, english_files, own_items)
        if stones:
            want_files = hints.with_hints(rel.split("/")[-1], want_files, english_names, stones)
        if got != want_files:   # (his line naming his gift included: gift_message_files writes it)
            problems.append("%s: not the game's with Darunia's line added%s" % (rel, " and the hints" if stones else ""))
    # (Mido's schedule: the game's rows but the after-Zelda one, each the same)
    path = os.path.join(mod_romfs, *patches.MIDO_SCHEDULE.split("/"))
    if not os.path.exists(path):
        problems.append("Mido's schedule not in the mod (his wall can stay after he leaves)")
    else:
        a = byml.read(open(os.path.join(romfs, *patches.MIDO_SCHEDULE.split("/")), "rb").read())[0]
        b = byml.read(open(path, "rb").read())[0]
        keep = [r for r in a["ConditionalSchedule"] if r.get("ConditionFlag") != patches.MIDO_ZELDA_ROW]
        if b["ConditionalSchedule"] != keep or {k: v for k, v in a.items() if k != "ConditionalSchedule"} != \
                {k: v for k, v in b.items() if k != "ConditionalSchedule"}:
            problems.append("Mido's schedule: not the game's without the after-Zelda row")
    # (the boulder over Dodongo's Cavern stays the game's: changing it crashed the game, 2026-11-13)
    rel = "Pack/Actor/%s.pack.zs" % patches.DC_BOULDER
    if os.path.exists(os.path.join(mod_romfs, *rel.split("/"))):
        problems.append("%s is in the mod (changing it crashed the game)" % rel)
    # (the trail's logic: the game's, with a bomb at the boulder setting off the flower's scene, nothing else)
    path = os.path.join(mod_romfs, *patches.DC_LOGIC.split("/"))
    if not os.path.exists(path):
        problems.append("the trail's logic not in the mod (bombs do not set off the boulder's flower)")
    else:
        logic = bytearray(open(os.path.join(romfs, *patches.DC_LOGIC.split("/")), "rb").read())
        for at, _, value in patches.dc_logic_bomb_edits(bytes(logic)):
            logic[at:at + 4] = value.to_bytes(4, "little")
        if open(path, "rb").read() != bytes(logic):
            problems.append("the trail's logic: not the game's with the bomb watcher in the flower's OR")
    # (the Temple of Time's sword module: the game's, the sword never deleted before the Forest Temple, nothing else)
    path = os.path.join(mod_romfs, *patches.TIME_LOGIC.split("/"))
    if not os.path.exists(path):
        problems.append("the Temple of Time's sword module not in the mod (no way back to child before the Forest Temple)")
    else:
        logic = bytearray(open(os.path.join(romfs, *patches.TIME_LOGIC.split("/")), "rb").read())
        for at, _, value in patches.time_logic_edits(bytes(logic)):
            logic[at:at + 4] = value.to_bytes(4, "little")
        if open(path, "rb").read() != bytes(logic):
            problems.append("the Temple of Time's sword module: not the game's with the sword never deleted")
    setting_path = os.path.join(mod_romfs, *EVENT_SETTING.split("/"))
    game_rows = byml.read(codec.read(os.path.join(romfs, *EVENT_SETTING.split("/"))))[0]
    rows = byml.read(codec.read(setting_path))[0] if os.path.exists(setting_path) else game_rows
    by = {r["__RowId"]: r for r in rows}
    if chosen["skip_intro"]:
        for m in patches.OPENING_MOVIES:
            if {k: v for k, v in by[m].items() if k != "__RowId"} != {k: v for k, v in by[patches.EMPTY_EVENT].items() if k != "__RowId"}:
                problems.append("opening movie %s not skipped" % m)
    # (the event settings: the game's rows, but the opening movies' (skip_intro) and the step-started rows' list
    # (skip_auto_dialogues))
    step_lists = {qol.component_list(n) for n in qol.STEP_START_LISTS}
    if len(rows) != len(game_rows):
        problems.append("%s: rows added or removed" % EVENT_SETTING)
    for g, r in zip(game_rows, rows):
        if chosen["skip_intro"] and g["__RowId"] in patches.OPENING_MOVIES:
            continue
        expected_row = dict(g)
        if chosen["skip_auto_dialogues"] and g.get("EventSettingComponentList") in step_lists:
            expected_row["EventSettingComponentList"] = qol.component_list(qol.PAUSED_LIST)
        if r != expected_row:
            problems.append("%s: row %s not the game's%s" % (EVENT_SETTING, g["__RowId"], " (but its list)"
                                                             if chosen["skip_auto_dialogues"] else ""))
    # (fast chests: both chest flows exactly the quick ones made from the game's; off: the game's)
    for rel, make in ((qol.BIG_CHEST_FLOW, qol.quick_big_chest), (qol.SMALL_CHEST_FLOW, qol.quick_small_chest)):
        path = os.path.join(mod_romfs, *rel.split("/"))
        if chosen["fast_chests"] != os.path.exists(path):
            problems.append("%s: %s the mod with fast chests %s" % (rel, "in" if os.path.exists(path) else "not in",
                                                                     "on" if chosen["fast_chests"] else "off"))
        elif chosen["fast_chests"] and codec.read(path) != make(codec.read(os.path.join(romfs, *rel.split("/")))):
            problems.append("%s: not the quick chest made from the game's" % rel)
    # (the title demo and credits: their lists without the skip ban, or the game's)
    for name in qol.LOCKED_CUTSCENES:
        rel = qol.locked_path(name)
        path = os.path.join(mod_romfs, *rel.split("/"))
        if chosen["skip_title_and_credits"] != os.path.exists(path):
            problems.append("%s: %s the mod" % (rel, "in" if os.path.exists(path) else "not in"))
        elif os.path.exists(path) and open(path, "rb").read() != qol.unlock_cutscene(
                open(os.path.join(romfs, *rel.split("/")), "rb").read()):
            problems.append("%s: not the game's without its skip ban" % rel)
    if chosen["skulltulas_day_and_night"] and nocturnal_seen < 20:
        problems.append("night skulltulas made day and night: %d, about 30 expected" % nocturnal_seen)
    print("%d chests planned, %d found; %d loose items planned, %d found; %d gift parameters; %d new pickups; %d problems" % (
        len(want), len(seen), len(loose), len(loose_seen), len(expect), len(made), len(problems)))
    for p in problems[:30]:
        print("  ", p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
