"""The game's event flows by event name (as a chest's GetEventName or an EventTransition's EventName): where an event is, and
the actions and queries it can reach (following switches, forks, joins and sub flows).

An event name is a row of RSDB/EventSetting (its __RowId), which names the flow file (FlowchartFileName,
"Work/Event/EventFlow/<flow>.evfc") and the entry point (EntryPointName)."""
import os

from .formats import byml, evfl

EVENT_SETTING = "RSDB/EventSetting.Product.111.rstbl.byml.zs"


class Events:
    def __init__(self, romfs, codec):
        self.dir = os.path.join(romfs, "Event", "EventFlow")
        self.codec = codec
        self.names = {f[:-len(".bfevfl.zs")] for f in os.listdir(self.dir) if f.endswith(".bfevfl.zs")}
        self._cache = {}
        rows, _ = byml.read(codec.read(os.path.join(romfs, *EVENT_SETTING.split("/"))))
        self.settings = {}   # (event name: (flow, entry point); entry None: the flow's default; flow None: a movie or timeline)
        self.rows = {r["__RowId"]: r for r in rows}
        for r in rows:
            flow = r.get("FlowchartFileName", "").rsplit("/", 1)[-1]
            flow = flow[:-len(".evfc")] if flow.endswith(".evfc") else flow
            self.settings[r["__RowId"]] = (flow or None, r.get("EntryPointName"))

    def flow(self, name):
        if name not in self._cache:
            flows = evfl.read(self.codec.read(os.path.join(self.dir, name + ".bfevfl.zs")))
            # (a file with no flowchart: timelines only)
            self._cache[name] = flows[0] if flows else {"name": name, "actors": [], "events": [], "entries": {}}
        return self._cache[name]

    def locate(self, event_name):
        """(flow file, entry point) for an event name, or None: its RSDB/EventSetting row; else (an event no row names) the
        longest flow name whose flow has the rest as an entry."""
        if event_name in self.settings:
            flow, entry = self.settings[event_name]
            if not flow or flow not in self.names:
                return None
            if entry is None:   # (the flow's default entry: EntryPoint0, or its only one)
                entries = list(self.flow(flow)["entries"])
                entry = "EntryPoint0" if "EntryPoint0" in entries else entries[0] if len(entries) == 1 else None
            return (flow, entry) if entry else None
        parts = event_name.split("_")
        for i in range(len(parts) - 1, 0, -1):
            flow, entry = "_".join(parts[:i]), "_".join(parts[i:])
            if flow in self.names:
                entries = self.flow(flow)["entries"]
                if entry in entries:
                    return flow, entry
                if event_name in entries:   # (some flows name the entry by the whole event name)
                    return flow, event_name
        return None

    def walk(self, flow_name, entry, depth=0, max_depth=4, seen=None):
        """Every action and query reachable from the entry, depth-first: (depth, flow, kind, actor, name, params)"""
        seen = set() if seen is None else seen
        fc = self.flow(flow_name)
        if entry not in fc["entries"]:
            return
        stack = [fc["entries"][entry]]
        while stack:
            i = stack.pop()
            if i is None or (flow_name, i) in seen:
                continue
            seen.add((flow_name, i))
            ev = fc["events"][i]
            t = ev["type"]
            if t == "action":
                a = fc["actors"][ev["actor"]]
                yield depth, flow_name, "action", a["name"], a["actions"][ev["action"]], ev["params"]
                stack.append(ev["next"])
            elif t == "switch":
                a = fc["actors"][ev["actor"]]
                yield depth, flow_name, "query", a["name"], a["queries"][ev["query"]], ev["params"]
                stack.extend(ev["cases"].values())
            elif t == "fork":
                stack.extend(ev["forks"])
                stack.append(ev["join"])
            elif t == "join":
                stack.append(ev["next"])
            elif t in ("subflow", "subflow_switch"):
                target = ev["flowchart"] or flow_name
                yield depth, flow_name, "call", target, ev["entry"], ev["params"]
                if depth < max_depth and target in self.names:
                    yield from self.walk(target, ev["entry"], depth + 1, max_depth, seen)
                stack.extend(ev["cases"].values() if t == "subflow_switch" else [ev["next"]])


# ---- what an event must list to call another flowchart

GAME_ANALYZED_EVENT_INFO = "RSDB/GameAnalyzedEventInfo.Product.111.rstbl.byml.zs"


def subflow_closure(read_flow, flowchart, entry):
    """the flowcharts an event needs loaded to call flowchart/entry: that flowchart and every other one its entry reaches
    by sub flows, in turn (read_flow(name) -> the flowchart dict, or None for a file with none).

    The game loads, when an event starts, only the flowcharts its RSDB/GameAnalyzedEventInfo row lists (SubFlowList, its
    own excepted); a call to one not listed does nothing (seen 2026-11-14: Darunia's get-item call; as the OotrR randomizer
    found for its Deku Tree gift, event_info.py, MIT). A sub flow switch picks its entry at run time: all its cases' are
    followed; one naming no entry is refused (it cannot be listed whole)."""
    out, seen, todo = set(), set(), [(flowchart, entry)]
    while todo:
        name, ent = todo.pop()
        if (name, ent) in seen:
            continue
        seen.add((name, ent))
        out.add(name)
        fc = read_flow(name)
        if not fc or ent not in fc["entries"]:
            continue
        events, stack, visited = fc["events"], [fc["entries"][ent]], set()
        while stack:
            i = stack.pop()
            if i is None or i in visited:
                continue
            visited.add(i)
            ev = events[i]
            t = ev["type"]
            if t in ("subflow", "subflow_switch"):
                if not ev.get("entry"):
                    raise ValueError("%s/%s: a sub flow with no entry" % (name, ent))
                todo.append((ev["flowchart"] or name, ev["entry"]))
            if t == "switch" or t == "subflow_switch":
                stack.extend(ev["cases"].values())
            elif t == "fork":
                stack.extend(ev["forks"])
                stack.append(ev["join"])
            elif "next" in ev:
                stack.append(ev["next"])
    return out


def list_subflows(rows, row_id, names):
    """add names to the SubFlowList of the GameAnalyzedEventInfo row row_id (kept sorted, as the game's); returns the ones
    added"""
    row = next((r for r in rows if r.get("__RowId") == row_id), None)
    if row is None:
        raise ValueError("%s: no row %s" % (GAME_ANALYZED_EVENT_INFO, row_id))
    have = set(row.get("SubFlowList") or [])
    added = sorted(set(names) - have)
    if added:
        row["SubFlowList"] = sorted(have | set(names))
    return added
