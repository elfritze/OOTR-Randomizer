"""Quality-of-life options (each a setting, rando.settings): changes to the game's data that save time and touch no check.

They follow the OotrR randomizer's (C:\\Projects\\ootremake-recomp\\OotrR, src/oot_rando/patching/qol_patches.py, MIT,
by Mozencaz), reimplemented on this project's own formats; each checks the game's data is the one it was made for and
raises otherwise (a game update), and the result is read back (rando.formats.evfl_edit). Every one is listed in README.md
with whether it was seen in game.

    fast_chests(romfs, codec, mod)            # (chests open without their cutscene: the lid opens, Link holds the item up)
    skulltulas_day_and_night(romfs, codec, mod)
    skippable_auto_dialogues(romfs, codec, mod)
    skippable_title_and_credits(romfs, codec, mod)
"""
from . import chests
from .formats import byml
from .formats.evfl_edit import FlowEdit

# ---- fast chests

BIG_CHEST_FLOW = "Event/EventFlow/Dm_SY_Treasurebox.bfevfl.zs"
SMALL_CHEST_FLOW = "Event/EventFlow/Dm_SY_TreasureboxSmall.bfevfl.zs"
BIG_LIDS = ("FrontOpen", "FrontOpen_Adult")
SMALL_LID = "FrontOpenSmall"
# (Link holding the item up while its window is open: the vanilla get pose of Dm_SY_GetInEvent:GetInEvent_NotTurn_NotNpc,
# the item the chest's own ContentName argument; OotrR's CHEST_SHOW_ITEM / CHEST_HIDE_ITEM)
SHOW_ITEM = (
    ("Player_Event", "EventCreateShowItemFromActorFileName", {"IsWaitEnd": True, "Actor": {"argument": "ContentName"}}),
    ("Player_Event", "EventPlayerPlayASForFlowchart", {
        "UseAnmDriven": False, "KeepOneTimeAnm": False, "IsWaitEnd": False, "ASCommand": "DemoGet",
        "IsAllSlot": True, "ForceFadeFrame": 0.0, "ClothWarpMode": -1}),
    ("Player_Event", "EventIgnitionShowItem", {
        "IsWaitEnd": True, "ItemPos": [0.0, 0.0, 0.0], "IsScale": False, "CreateTime": 0.0,
        "IsInvalidateShadow": True, "IsAsPlay": True, "ASCommand": "Rotate_GetDemo"}),
    ("EventSystemActor", "EventWait", {"IsWaitEnd": True, "Frames": 40}),
)
HIDE_ITEM = ("Player_Event", "EventDeleteShowItem", {
    "IsWaitEnd": True, "IsFadeOut": False, "IsScaleOut": False, "ChangeVisibleOffWithRequestDelete": False})


def _action(flow, e):
    a = flow["actors"][e["actor"]]
    return a["name"], a["actions"][e["action"]]


def quick_big_chest(data):
    """Dm_SY_Treasurebox: Success_ (a switch; its case 0: the fanfare, /Success_PlayerPerform (Link's whole opening
    performance, ~8 s), a wait, /Success_AddContent, /Success_Leave) plays /Open instead of the performance (the lid only),
    then Link's get pose with the item, then adds it; the fanfare without its intro; the lid's animation not awaited (it is
    timed on the performance: Link stood frozen through it). As OotrR's quick_chest."""
    edit = FlowEdit(data)
    flow, ev = edit.flow, edit.flow["events"]
    switch = ev[flow["entries"]["Success_"]]
    fanfare = ev[switch["cases"][0]] if switch["type"] == "switch" and 0 in switch["cases"] else {}
    perform = ev[fanfare["next"]] if fanfare.get("next") is not None else {}
    wait = ev[perform["next"]] if perform.get("next") is not None else {}
    add = ev[wait["next"]] if wait.get("next") is not None else {}
    leave = ev[add["next"]] if add.get("next") is not None else {}
    if not (fanfare.get("type") == "action" and _action(flow, fanfare)[1] == "EventTriggerSoundStartFanfare" and
            (fanfare.get("params") or {}).get("IsEnableIntro") is True and
            perform.get("type") == "subflow" and (perform["flowchart"], perform["entry"]) == ("", "Success_PlayerPerform") and
            (perform.get("params") or {}).get("ContentName") == {"argument": "ContentName"} and
            wait.get("type") == "action" and _action(flow, wait)[1] == "EventWait" and
            add.get("type") == "subflow" and (add["flowchart"], add["entry"]) == ("", "Success_AddContent") and
            leave.get("type") == "subflow" and leave["entry"] == "Success_Leave" and "Open" in flow["entries"]):
        raise ValueError("%s: not the big chest flow known" % BIG_CHEST_FLOW)
    lids = [e for e in ev if e["type"] == "action" and _action(flow, e)[1] == "EventPlayAS" and
            (e.get("params") or {}).get("ASName") in BIG_LIDS]
    if sorted(e["params"]["ASName"] for e in lids) != sorted(BIG_LIDS) or \
            any(e["params"].get("IsWaitEnd") is not True for e in lids):
        raise ValueError("%s: not the chest lid animations known" % BIG_CHEST_FLOW)
    edit.set_values(fanfare["name"], {"IsEnableIntro": False})
    for e in lids:
        edit.set_values(e["name"], {"IsWaitEnd": False})
    names = ["RandoQuickChestShow_%d" % i for i in range(len(SHOW_ITEM))]
    for i, (actor, action, params) in enumerate(SHOW_ITEM):
        edit.add_event({"name": names[i], "type": "action", "actor": actor, "action": action, "params": params,
                        "next": names[i + 1] if i + 1 < len(names) else add["name"]})
    actor, action, params = HIDE_ITEM
    edit.add_event({"name": "RandoQuickChestHide", "type": "action", "actor": actor, "action": action, "params": params,
                    "next": leave["name"]})
    edit.set_next(add["name"], "RandoQuickChestHide")
    edit.set_subflow(perform["name"], entry="Open", params=None)
    edit.set_next(perform["name"], names[0])
    return edit.apply()


def quick_small_chest(data):
    """Dm_SY_TreasureboxSmall: Success_ calls /Open (space and camera checks, Link's opening or kicking animation awaited,
    event cameras, Navi, the lid, then /Pack_ItemDisplay: item shown, added, get window). It now runs the lid's own actions
    (not awaited), Link's get pose (/GetAnimationAction) and /Pack_ItemDisplay with /Open's arguments. As OotrR's
    quick_small_chest."""
    edit = FlowEdit(data)
    flow, ev = edit.flow, edit.flow["events"]
    opened = ev[flow["entries"]["Success_"]]
    if not (opened["type"] == "subflow" and (opened["flowchart"], opened["entry"]) == ("", "Open") and
            (opened.get("params") or {}).get("ContentName") == {"argument": "ContentName"} and
            "IsMiniGame" in opened["params"] and
            {"Pack_ItemDisplay", "GetAnimationAction", "TresureboxSmall_Animation"} <= set(flow["entries"])):
        raise ValueError("%s: not the small chest flow known" % SMALL_CHEST_FLOW)

    def actions(name):
        return [e for e in ev if e["type"] == "action" and _action(flow, e)[1] == name]
    push = actions("EventTriggerTBoxPushPoseMask")
    lid = [e for e in actions("EventPlayAS") if (e.get("params") or {}).get("ASName") == SMALL_LID]
    light = actions("EventTreasureBoxSetRigLightIntensityScale")
    pose = [e for e in ev if e["type"] == "subflow" and (e["flowchart"], e["entry"]) == ("", "GetAnimationAction")]
    if len(push) != 1 or len(lid) != 1 or len(light) != 1 or not pose:
        raise ValueError("%s: not the small chest lid known" % SMALL_CHEST_FLOW)
    steps = [("RandoQuickChestPose", push[0], {}), ("RandoQuickChestLid", lid[0], {"IsWaitEnd": False}),
             ("RandoQuickChestLight", light[0], {"IsWaitEnd": False}), ("RandoQuickChestGetPose", pose[0], {})]
    for i, (name, src, changes) in enumerate(steps):
        edit.add_event({"name": name, "clone": src["name"], "changes": changes,
                        "next": steps[i + 1][0] if i + 1 < len(steps) else opened["name"]})
    edit.set_subflow(opened["name"], entry="Pack_ItemDisplay")
    edit.set_entry("Success_", steps[0][0])
    return edit.apply()


def fast_chests(romfs, codec, mod):
    mod.write(BIG_CHEST_FLOW, quick_big_chest(mod.read(BIG_CHEST_FLOW)))
    mod.write(SMALL_CHEST_FLOW, quick_small_chest(mod.read(SMALL_CHEST_FLOW)))


# ---- gold skulltulas by day

# (30 gold skulltulas in 18 maps appear only at night: Dynamic Enemy_Skulltula_Gold_Nocturnal true on their map instance;
# false, they are there day and night as the others: OotrR's nocturnal_skulltula_edits)
NOCTURNAL = "Enemy_Skulltula_Gold_Nocturnal"
SKULLTULA = "Enemy_Skulltula_Gold"


def is_nocturnal(actor):
    return actor.get("Gyaml") == SKULLTULA and (actor.get("Dynamic") or {}).get(NOCTURNAL) is True


# Each of the 30 is also one of its map's AiGroups run by the shared logic module Gimmick_Nighttime_Skulltula_Gold_Appear (with
# its spider web): it creates both, and deletes the skulltula by day (loaded by day before any night, or day come while it
# is alive and not fighting: HoldWmGetTimeDiv). Seen in game (seed 7cc65105, 2026-11-15): with the flag off alone, the House
# of Skulltula's skulltula was not there by day. The module's skulltula is now never deleted (Logic_Delete a constant
# false, as Gimmick_AllDay_Skulltula's own skulltula has it), changed in place (the file keeps its size); its web still
# goes when it dies.
NIGHT_MODULE = "Logic/Gimmick_Nighttime_Skulltula_Gold_Appear_05a9.logic.module.ainb"


def night_module_by_day(data):
    """the night skulltulas' module with its skulltula never deleted"""
    import struct
    from .formats import ainb
    f = ainb.File(data)
    gs = [n for n in f.nodes if n["name"] == "ActorLogicEnemySkulltulaGold"]
    if len(gs) != 1 or f.nodes[2]["name"] != "OperateOR":
        raise ValueError("%s: not the module known" % NIGHT_MODULE)
    i = gs[0]["inputs"]["Logic_Delete"]
    if i["type"] != "bool" or i["sources"] != [(2, 1, None)] or f.readers(2, 1) != [(gs[0]["index"], "Logic_Delete")]:
        raise ValueError("%s: its skulltula's deletion is not the one known" % NIGHT_MODULE)
    out = bytearray(data)
    struct.pack_into("<hh", out, i["entry"] + 4, -1, 0)   # (no source: its own value)
    struct.pack_into("<I", out, i["value_at"], 0)
    at = dict(f.nodes[2]["outputs"]["bool"])["True"]   # (that output no longer read)
    struct.pack_into("<I", out, at, f.u32(at) & ~ainb.USED)
    g = ainb.File(bytes(out))
    if g.nodes[gs[0]["index"]]["inputs"]["Logic_Delete"]["sources"] or len(out) != len(data):
        raise ValueError("%s: not changed as meant" % NIGHT_MODULE)
    return bytes(out)


def skulltulas_day_and_night(romfs, codec, mod):
    """returns {map file: [hashes]} of the skulltulas changed"""
    mod.write(NIGHT_MODULE, night_module_by_day(mod.read(NIGHT_MODULE)))
    changed = {}
    for rel in chests.map_files(romfs):
        raw = mod.read(rel)
        root, version = byml.read(raw)
        hits = [a for a in root.get("Actors", []) if is_nocturnal(a)]
        if not hits:
            continue
        for a in hits:
            a["Dynamic"][NOCTURNAL] = False
        mod.write(rel, byml.write(root, version, byml.endian(raw)))
        changed[rel] = [int(a["Hash"]) for a in hits]
    if sum(len(v) for v in changed.values()) < 20:
        raise ValueError("night skulltulas: %d found, about 30 expected" % sum(len(v) for v in changed.values()))
    return changed


# ---- dialogues and cutscenes

EVENT_SETTING = "RSDB/EventSetting.Product.111.rstbl.byml.zs"
LISTS = "Event/EventSetting/EventSettingComponentList/"


def component_list(name):
    """an EventSetting row's EventSettingComponentList value for that list"""
    return "Work/%s%s.engine__event__EventSettingComponentList.gyml" % (LISTS, name)


# (events a quest step starts, as Navi's or a minigame's lines: their list lets the world run, so + does not skip them; the
# paused list (FlowchartEvent) does. OotrR's NPC_STEP_START, "automatic dialogues skippable with +")
STEP_START_LISTS = ("NPCStepStart", "NPCStepStartNoPause")
PAUSED_LIST = "FlowchartEvent"


def skippable_auto_dialogues(romfs, codec, mod):
    """returns the rows changed"""
    raw = mod.read(EVENT_SETTING)
    rows, version = byml.read(raw)
    source = {component_list(n) for n in STEP_START_LISTS}
    target = component_list(PAUSED_LIST)
    if not any(r.get("EventSettingComponentList") == target for r in rows):
        raise ValueError("%s: no row with the list %s" % (EVENT_SETTING, PAUSED_LIST))
    changed = []
    for r in rows:
        if r.get("EventSettingComponentList") in source:
            r["EventSettingComponentList"] = target
            changed.append(r["__RowId"])
    if not changed:
        raise ValueError("%s: no step-started row" % EVENT_SETTING)
    mod.write(EVENT_SETTING, byml.write(rows, version, byml.endian(raw)))
    return changed


# (the title screen's demo and the end credits forbid skipping (Components SkipSetting = DisableSkip); OotrR's
# LOCKED_CUTSCENES. The intro has its own setting: skip_intro)
DISABLE_SKIP = "?Event/EventSetting/EventSettingComponent/SkipSetting/DisableSkip.engine__event__SkipSetting.bgyml"
LOCKED_CUTSCENES = ("Dm_StaffCredit_0005", "Dm_Title_0005")


def locked_path(name):
    return "%s%s.engine__event__EventSettingComponentList.bgyml" % (LISTS, name)


def unlock_cutscene(raw):
    root, version = byml.read(raw)
    if byml.write(root, version, byml.endian(raw)) != raw:
        raise ValueError("a component list this BYML writer does not give back as it was")
    if (root.get("Components") or {}).get("SkipSetting") != DISABLE_SKIP:
        raise ValueError("a cutscene without the skip ban known")
    del root["Components"]["SkipSetting"]
    return byml.write(root, version, byml.endian(raw))


def skippable_title_and_credits(romfs, codec, mod):
    for name in LOCKED_CUTSCENES:
        mod.write(locked_path(name), unlock_cutscene(mod.read(locked_path(name))))
