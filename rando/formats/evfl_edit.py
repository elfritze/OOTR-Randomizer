"""Several changes to one flowchart of a BFEVFL, written in one go after the end of the file (as evfl_patch does) and checked
by reading the result back against the flowchart the changes describe:

    edit = FlowEdit(data)
    edit.add_event({"name": ..., "type": "action", "actor": ..., "action": ..., "params": {...}, "next": ...})
    edit.add_event({"name": ..., "clone": "Event12", "changes": {"IsWaitEnd": False}, "next": ...})
    edit.set_next("Event12", "RandoX")              # (an action, subflow or join's next: an event's name, or None)
    edit.set_entry("Success_", "RandoX")            # (an entry point's first event)
    edit.set_values("Event5", {"IsWaitEnd": False})  # (scalar parameters of an event, in place, same type)
    edit.set_subflow("Event7", entry="Open", params=None)   # (a subflow's entry; its parameters dropped, or kept)
    out = edit.apply()

New events take the types of add_events (evfl_patch): "action" (actor, action, params, next), "subflow" (flowchart, entry,
params, next), "switch" (actor, query, params, cases {value: target}); a target is an event's name (an old or a new one),
or None for the end. "clone" copies an existing action or subflow event (actor and action, or flowchart and entry), its
parameter container shared, or copied with the "changes" given (each untouched value keeps its own container, so its exact
type). An action a new event needs is added to its actor's list (the actor must exist, with no sub actor name)."""
import struct

from . import evfl
from .evfl_patch import BOOL_TRUE, _Blob, relt_pointers, relt_write

KEEP = object()


class FlowEdit:
    def __init__(self, data, flow_index=0):
        self.data, self.flow_index = data, flow_index
        self.flow = evfl.read(data)[flow_index]
        self.names = [e["name"] for e in self.flow["events"]]
        self.new, self.nexts, self.entries, self.values, self.subflows = [], {}, {}, {}, {}

    def event(self, name):
        return self.flow["events"][self.names.index(name)]

    def index(self, name):
        if name in self.names:
            return self.names.index(name)
        new = [e["name"] for e in self.new]
        if name in new:
            return len(self.names) + new.index(name)
        raise ValueError("no event %s" % name)

    def add_event(self, ev):
        if ev["name"] in self.names or any(e["name"] == ev["name"] for e in self.new):
            raise ValueError("an event %s already" % ev["name"])
        self.new.append(dict(ev))

    def set_next(self, name, target):
        if self.event(name)["type"] not in ("action", "subflow", "join"):
            raise ValueError("%s has no next" % name)
        self.nexts[name] = target

    def set_entry(self, entry, target):
        if entry not in self.flow["entries"]:
            raise ValueError("no entry %s" % entry)
        self.entries[entry] = target

    def set_values(self, name, values):
        self.event(name)
        self.values.setdefault(name, {}).update(values)

    def set_subflow(self, name, entry=None, params=KEEP):
        if self.event(name)["type"] != "subflow":
            raise ValueError("%s is not a subflow" % name)
        self.subflows[name] = (entry, params)

    def apply(self):
        data, r = self.data, evfl.Reader(self.data)
        flow_at = r.u64(r.u64(0x28) + 8 * self.flow_index)
        n_actors, n_actions, n_queries, n_events = (r.u16(flow_at + 0x10 + 2 * i) for i in range(4))
        actors_at, events_at = r.u64(flow_at + 0x28), r.u64(flow_at + 0x30)
        entry_names, entries_at = r.dic(r.u64(flow_at + 0x38)), r.u64(flow_at + 0x40)
        old = bytearray(data)
        old += b"\0" * (-len(old) % 8)
        blob = _Blob(len(old))
        pointers = relt_pointers(data)
        empty = next((r.u64(actors_at + 0x38 * i + 8) for i in range(n_actors)
                      if r.string(r.u64(actors_at + 0x38 * i + 8)) == ""), None)
        if empty is None:
            empty = blob.string("")
        want = evfl.read(data)[self.flow_index]
        actors = want["actors"]

        def actor_index(name):
            hits = [i for i, a in enumerate(actors) if a["name"] == name and a["sub"] == ""]
            if len(hits) != 1:
                raise ValueError("no single actor %s" % name)
            return hits[0]

        def target(t):
            return 0xFFFF if t is None else self.index(t)

        # (clones resolved to their source's kind; actions and queries an actor lacks added to its lists, rewritten after
        #  the end)
        resolved, grow, grow_q = [], {}, {}
        for ev in self.new:
            if "clone" in ev:
                src = self.event(ev["clone"])
                if src["type"] == "action":
                    ev = dict(ev, type="action", actor=actors[src["actor"]]["name"],
                              action=actors[src["actor"]]["actions"][src["action"]])
                elif src["type"] == "subflow":
                    ev = dict(ev, type="subflow", flowchart=src["flowchart"], entry=src["entry"])
                else:
                    raise ValueError("%s: only actions and subflows are cloned" % ev["clone"])
            if ev["type"] == "action":
                ai = actor_index(ev["actor"])
                if ev["action"] not in actors[ai]["actions"]:
                    actors[ai]["actions"].append(ev["action"])
                    grow.setdefault(ai, []).append(ev["action"])
            elif ev["type"] == "switch":
                ai = actor_index(ev["actor"])
                if ev["query"] not in actors[ai]["queries"]:
                    actors[ai]["queries"].append(ev["query"])
                    grow_q.setdefault(ai, []).append(ev["query"])
            resolved.append(ev)
        moved_lists = []

        def grow_list(ai, added, ptr_off, count_off):
            a = actors_at + 0x38 * ai
            count = r.u16(a + count_off)
            arr = blob.reserve(8 * (count + len(added)))
            old_arr = r.u64(a + ptr_off)
            for k in range(count):
                blob.pointer(arr + 8 * k, r.u64(old_arr + 8 * k))
            for k, name in enumerate(added):
                blob.pointer(arr + 8 * (count + k), blob.string(name))
            struct.pack_into("<Q", old, a + ptr_off, arr)
            if a + ptr_off not in pointers:   # (an empty list's pointer may be null, out of the relocation table)
                moved_lists.append(a + ptr_off)
            struct.pack_into("<H", old, a + count_off, count + len(added))
        for ai, added in grow.items():
            grow_list(ai, added, 0x18, 0x30)
            n_actions += len(added)
        for ai, added in grow_q.items():
            grow_list(ai, added, 0x20, 0x32)
            n_queries += len(added)

        # (the events: copied after the end, the new ones last)
        total = n_events + len(resolved)
        new_events = blob.reserve(0x30 * total)
        blob.buf[new_events - blob.base:new_events - blob.base + 0x30 * n_events] = data[events_at:events_at + 0x30 * n_events]
        moved = [new_events + p - events_at for p in pointers if events_at <= p < events_at + 0x30 * n_events]
        for k, ev in enumerate(resolved):
            e = new_events + 0x30 * (n_events + k)
            blob.pointer(e, blob.string(ev["name"]))
            t = ev["type"]
            if "clone" in ev:
                src = self.event(ev["clone"])
                src_params = r.u64(events_at + 0x30 * self.names.index(ev["clone"]) + 0x10)
                changes = ev.get("changes") or {}
                if changes and not src_params:
                    raise ValueError("%s: no parameters to change" % ev["name"])
                p = blob.container_like(r, src_params, changes, empty) if changes else src_params
                params = None if src.get("params") is None else dict(src["params"], **changes)
            else:
                p = blob.container(ev["params"], empty) if ev.get("params") is not None else 0
                params = None if ev.get("params") is None else dict(ev["params"])
            if t == "action":
                ai = actor_index(ev["actor"])
                ki = actors[ai]["actions"].index(ev["action"])
                blob.put(e + 8, "<BxHHH", evfl.ACTION, target(ev.get("next")), ai, ki)
                back = {"next": ev.get("next"), "actor": ai, "action": ki, "params": params}
            elif t == "subflow":
                blob.put(e + 8, "<BxH", evfl.SUBFLOW, target(ev.get("next")))
                blob.pointer(e + 0x18, blob.string(ev["flowchart"]))
                blob.pointer(e + 0x20, blob.string(ev["entry"]))
                back = {"next": ev.get("next"), "params": params, "flowchart": ev["flowchart"], "entry": ev["entry"]}
            elif t == "switch":
                ai = actor_index(ev["actor"])
                qi = actors[ai]["queries"].index(ev["query"])
                cases = list(ev["cases"].items())
                if any(to is None for _, to in cases):
                    raise ValueError("%s: a switch case needs an event" % ev["name"])
                blob.put(e + 8, "<BxHHH", evfl.SWITCH, len(cases), ai, qi)
                tab = blob.reserve(8 * len(cases))
                for j, (value, to) in enumerate(cases):
                    blob.put(tab + 8 * j, "<II", value, target(to))
                blob.pointer(e + 0x18, tab)
                back = {"actor": ai, "query": qi, "params": params, "cases": dict(cases)}
            else:
                raise ValueError("event type %s not written" % t)
            if p:
                blob.pointer(e + 0x10, p)
            want["events"].append(dict({"name": ev["name"], "type": t}, **back))

        # (changes to the old events, in their copy)
        for name, to in self.nexts.items():
            blob.put(new_events + 0x30 * self.index(name) + 0xA, "<H", target(to))
            want["events"][self.index(name)]["next"] = to
        for name, (entry, params) in self.subflows.items():
            i = self.index(name)
            e = new_events + 0x30 * i
            if entry is not None:
                blob.pointer(e + 0x20, blob.string(entry))
                want["events"][i]["entry"] = entry
            if params is None:
                blob.put(e + 0x10, "<Q", 0)
                if e + 0x10 in moved:
                    moved.remove(e + 0x10)
                want["events"][i]["params"] = None
            elif params is not KEEP:
                blob.pointer(e + 0x10, blob.container(params, empty))
                want["events"][i]["params"] = dict(params)
        for name, values in self.values.items():
            i = self.index(name)
            p = r.u64(events_at + 0x30 * i + 0x10)
            keys = r.dic(r.u64(p + 8))
            for k, v in values.items():
                child = r.u64(p + 0x10 + 8 * keys.index(k))
                t = r.u8(child)
                if t == evfl.BOOL and isinstance(v, bool):
                    struct.pack_into("<I", old, child + 0x10, BOOL_TRUE if v else 0)
                elif t == evfl.INT and isinstance(v, int) and not isinstance(v, bool):
                    struct.pack_into("<i", old, child + 0x10, v)
                elif t == evfl.FLOAT and isinstance(v, float):
                    struct.pack_into("<f", old, child + 0x10, v)
                else:
                    raise ValueError("%s %s: a type %d container, not %r" % (name, k, t, v))
                want["events"][i]["params"][k] = v
        for entry, to in self.entries.items():
            struct.pack_into("<H", old, entries_at + 0x20 * entry_names.index(entry) + 0x1C, target(to))
            want["entries"][entry] = self.index(to)

        size = blob.here()
        blob.align()
        out = bytearray(bytes(old) + bytes(blob.buf))
        struct.pack_into("<Q", out, flow_at + 0x30, new_events)
        struct.pack_into("<HHHH", out, flow_at + 0x10, n_actors, n_actions, n_queries, total)
        every = sorted(set(pointers) | set(moved) | set(moved_lists) | set(blob.pointers))
        at = len(out)
        out += relt_write(every, at, size)
        struct.pack_into("<I", out, 0x18, at)
        struct.pack_into("<I", out, 0x1C, len(out))
        out = bytes(out)

        # (the wanted flowchart with indices, as the reader gives them)
        for e in want["events"]:
            if isinstance(e.get("next"), str):
                e["next"] = self.index(e["next"])
            if "cases" in e:
                e["cases"] = {v: (self.index(to) if isinstance(to, str) else to) for v, to in e["cases"].items()}
        back = evfl.read(out)[self.flow_index]
        if back != want:
            diff = [i for i, (x, y) in enumerate(zip(back["events"], want["events"])) if x != y][:5]
            raise ValueError("the flow read back is not the one wanted (events %s)" % diff)
        if sorted(relt_pointers(out)) != every:
            raise ValueError("the relocation table read back is not the one written")
        return out
