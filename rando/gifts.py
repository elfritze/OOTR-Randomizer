"""NPCs' and minigames' prizes: each data/gifts.json check's edits (the event parameters naming what it gives, both branches of a
prize chosen by what the player owns, both copies of a flow the game has an updated one of) set to the new item. A parameter
is changed only while it still holds the game's own value (the table's), so a game update that moved an event stops the
seed instead of breaking a prize."""
import collections
import os

from .formats import evfl, evfl_patch


def flow_path(flow):
    return "Event/EventFlow/%s.bfevfl.zs" % flow


def write(romfs, codec, mod, assignments):
    """assignments: [(gifts.json check, the actor its gift is to give)]. Returns the flow files written."""
    by_flow = edits_by_flow(assignments)   # (an edit's "set": a value of its own, whatever the item: a song lesson's
    #                                          silent add switched off, a Great Fairy's once-flag)
    written = []
    for flow, edits in sorted(by_flow.items()):
        rel = flow_path(flow)
        mod.write(rel, edited(mod.read(rel), flow, edits))
        written.append(rel)
    return written


def edits_by_flow(assignments):
    """{flow: [(edit, the value it sets, check id)]} of [(gifts.json check, actor)]"""
    by_flow = collections.defaultdict(list)
    for check, actor in assignments:
        for e in check["edits"]:
            by_flow[e["flow"]].append((e, e.get("set", actor), check["id"]))
    return by_flow


def edited(data, flow, edits):
    """a flow's data with its edits made: [(edit, value, check id)] (edits_by_flow's)"""
    seen = {}
    for e, actor, cid in edits:
        key = (e["event"], e["param"])
        if key in seen:
            if seen[key] != actor:
                raise ValueError("%s event %d %s: two checks give through it (%s)" % (flow, e["event"], e["param"], cid))
            continue
        seen[key] = actor
        now = evfl.read(data)[0]["events"][e["event"]]["params"].get(e["param"])
        if now != e["value"]:
            raise ValueError("%s event %d %s is %r, the table says %r (%s)" % (flow, e["event"], e["param"], now,
                                                                              e["value"], cid))
        data = evfl_patch.set_string_param(data, e["event"], e["param"], actor)
        if evfl.read(data)[0]["events"][e["event"]]["params"].get(e["param"]) != actor:
            raise ValueError("%s event %d: the change did not take" % (flow, e["event"]))
    return data
