"""Changes to a BFEVFL without rewriting what is there: new data goes after the file's end, pointers move to it, and (when new
pointers are written) the relocation table is written again after it.

- set_string_param: an event's string parameter (an NPC's gift: Dm_SY_GetInEvent's ActorName). The new string goes after the
  end and the parameter's pointer moves to it (that pointer is in the relocation table already): nothing else changes.
- add_actions: new action events after an event (as starting items given at the new game's opening), with their actor when
  the flowchart has none of that name. The flowchart's actor and event arrays are copied after the end with the new records
  added (indices stay: the new ones come last), and the relocation table is written again with the new pointers; the old
  arrays and table stay in the file, unused.

The relocation table (RELT, its offset at 0x18): one section from the file's start to its data's end, then entries of (u32 offset,
u32 mask): bit i set = a pointer at offset + 8 * i; the game's own tables are the pointers' offsets taken in order, each
entry starting at the first pointer not yet covered (relt_entries, checked against every flow of the game by
tools/check_evfl.py). A DIC (a container's keys, the entry points) is Nintendo's radix tree: dic_nodes builds one as the
game's are built (also checked against every flow)."""
import struct

from . import evfl

BOOL_TRUE = 0x80000001   # (how the game's flows store true)


def _param_pointer(r, flow_at, event_index, key):
    """the file offset of the u64 pointer holding the string value of an event's parameter key"""
    events_at = r.u64(flow_at + 0x30)
    e = events_at + 0x30 * event_index
    t = r.u8(e + 8)
    params = r.u64(e + 0x10)
    if t not in (evfl.ACTION, evfl.SWITCH, evfl.SUBFLOW, evfl.SUBFLOW_SWITCH) or not params:
        raise ValueError("event %d has no parameters" % event_index)
    if r.u8(params) != evfl.CONTAINER:
        raise ValueError("event %d: parameters are not a container" % event_index)
    names = r.dic(r.u64(params + 8))
    if names.count(key) != 1:
        raise ValueError("event %d has no parameter %s" % (event_index, key))
    child = r.u64(params + 0x10 + 8 * names.index(key))
    if r.u8(child) != evfl.STRING or r.u16(child + 2) != 1:
        raise ValueError("event %d: %s is not a string" % (event_index, key))
    return child + 0x10


def set_string_param(data, event_index, key, value, flow_index=0):
    """data with event event_index's parameter key (a string) set to value"""
    r = evfl.Reader(data)
    flow_at = r.u64(r.u64(0x28) + 8 * flow_index)
    ptr = _param_pointer(r, flow_at, event_index, key)
    out = bytearray(data)
    out += b"\0" * (-len(out) % 8)
    at = len(out)
    raw = value.encode("utf-8")
    out += struct.pack("<H", len(raw)) + raw + b"\0"
    out += b"\0" * (-len(out) % 8)
    struct.pack_into("<Q", out, ptr, at)
    struct.pack_into("<I", out, 0x1C, len(out))   # (the header's file size)
    return bytes(out)


# ---- the relocation table

def relt_section_size(data):
    """the relocation section's size: the file's data up to the table, its padding before the table left out"""
    at = evfl.Reader(data).u32(0x18)
    return evfl.Reader(data).u32(at + 0x1C)


def relt_pointers(data):
    """the offsets of every pointer the relocation table lists"""
    r = evfl.Reader(data)
    at = r.u32(0x18)
    if data[at:at + 4] != b"RELT" or r.u32(at + 4) != at or r.u32(at + 8) != 1:
        raise ValueError("not a one-section relocation table at %#x" % at)
    sec = at + 0x10
    base, first, count = r.u32(sec + 8), r.u32(sec + 0x10), r.u32(sec + 0x14)
    if base != 0 or r.u64(sec) != 0 or first != 0:
        raise ValueError("relocation section %r" % (data[sec:sec + 0x18],))
    out = []
    for k in range(count):
        e = sec + 0x18 + 8 * k
        offset, mask = r.u32(e), r.u32(e + 4)
        out += [offset + 8 * i for i in range(32) if mask >> i & 1]
    return out


def relt_entries(pointers):
    """(offset, mask) entries covering the pointers: each from the first one not yet covered"""
    entries = []
    for p in sorted(set(pointers)):
        if entries:
            offset, mask = entries[-1]
            if p - offset < 256 and (p - offset) % 8 == 0:
                entries[-1] = (offset, mask | 1 << (p - offset) // 8)
                continue
        entries.append((p, 1))
    return entries


def relt_write(pointers, at, size):
    """the table for these pointers, written at offset at; its section is the file's first size bytes (the data, without
    the padding before the table)"""
    entries = relt_entries(pointers)
    out = b"RELT" + struct.pack("<III", at, 1, 0)
    out += struct.pack("<QIIII", 0, 0, size, 0, len(entries))
    return out + b"".join(struct.pack("<II", o, m) for o, m in entries)


# ---- DIC

def _bit(key, i):
    b = i >> 3
    return key[len(key) - 1 - b] >> (i & 7) & 1 if b < len(key) else 0


def dic_nodes(keys):
    """[(bit, left, right)] for the root and each key in order, as the game's DICs are built"""
    keys = [k.encode("utf-8") for k in keys]
    nodes = [[-1, 0, 0, b""]]

    def child(i, key):
        return nodes[i][2] if _bit(key, nodes[i][0]) else nodes[i][1]

    for key in keys:
        prev, cur = 0, nodes[0][1]
        while nodes[prev][0] < nodes[cur][0]:
            prev, cur = cur, child(cur, key)
        other = nodes[cur][3]
        if other == key:
            raise ValueError("a key twice in a DIC: %r" % key)
        bit = next(i for i in range(8 * max(len(key), len(other))) if _bit(key, i) != _bit(other, i))
        prev, cur = 0, nodes[0][1]
        while nodes[prev][0] < nodes[cur][0] < bit:
            prev, cur = cur, child(cur, key)
        idx = len(nodes)
        nodes.append([bit, cur, idx, key] if _bit(key, bit) else [bit, idx, cur, key])
        if prev == 0:
            nodes[0][1] = idx
        elif _bit(key, nodes[prev][0]):
            nodes[prev][2] = idx
        else:
            nodes[prev][1] = idx
    return [(b & 0xFFFFFFFF, left, right) for b, left, right, _ in nodes]


# ---- writing new data after the end

class _Blob:
    """bytes to put at file offset base, with the offsets of the pointers in them"""
    def __init__(self, base):
        self.base, self.buf, self.pointers = base, bytearray(), []

    def here(self):
        return self.base + len(self.buf)

    def align(self, n=8):
        self.buf += b"\0" * (-self.here() % n)

    def reserve(self, size):
        self.align()
        at = self.here()
        self.buf += b"\0" * size
        return at

    def put(self, at, fmt, *values):
        struct.pack_into(fmt, self.buf, at - self.base, *values)

    def pointer(self, at, target):
        self.put(at, "<Q", target)
        self.pointers.append(at)

    def string(self, s):
        self.align(2)
        at = self.here()
        raw = s.encode("utf-8")
        self.buf += struct.pack("<H", len(raw)) + raw + b"\0"
        return at

    def container(self, params, empty):
        """a parameter container (dict: int, bool, float or str values) and its children; empty: the file's empty string
        (a DIC's root names it, as in the game's)"""
        keys = list(params)
        at = self.reserve(0x10 + 8 * len(keys))
        self.put(at, "<BxH", evfl.CONTAINER, len(keys))
        dic = self.reserve(8 + 16 * (len(keys) + 1))
        self.buf[dic - self.base:dic - self.base + 8] = b"DIC " + struct.pack("<I", len(keys))
        names = [empty] + [self.string(k) for k in keys]
        for i, (bit, left, right) in enumerate(dic_nodes(keys)):
            self.put(dic + 8 + 16 * i, "<IHH", bit, left, right)
            self.pointer(dic + 8 + 16 * i + 8, names[i])
        self.pointer(at + 8, dic)
        for i, k in enumerate(keys):
            v = params[k]
            child = self.reserve(0x18)
            if isinstance(v, bool):
                self.put(child, "<BxH", evfl.BOOL, 1)
                self.put(child + 0x10, "<I", BOOL_TRUE if v else 0)
            elif isinstance(v, int):
                self.put(child, "<BxH", evfl.INT, 1)
                self.put(child + 0x10, "<i", v)
            elif isinstance(v, float):
                self.put(child, "<BxH", evfl.FLOAT, 1)
                self.put(child + 0x10, "<f", v)
            elif isinstance(v, str):
                self.put(child, "<BxH", evfl.STRING, 1)
                self.pointer(child + 0x10, self.string(v))
            else:
                raise ValueError("parameter %s: %r" % (k, v))
            self.pointer(at + 0x10 + 8 * i, child)
        return at


def add_actions(data, after, actor, action, actor_params, events, flow_index=0):
    """data with action events added after the event named after (its next goes on after the last one):
    events = [(name, params)], each actor.action with its params (dict); the actor is added with actor_params when the
    flowchart has none of that name, and the action to its actions when it has not that one. Returns the new bytes."""
    r = evfl.Reader(data)
    flow_at = r.u64(r.u64(0x28) + 8 * flow_index)
    flow = evfl.read(data)[flow_index]
    names = [e["name"] for e in flow["events"]]
    if names.count(after) != 1 or flow["events"][names.index(after)]["type"] not in ("action", "join", "subflow"):
        raise ValueError("no single event %s with a next" % after)
    for name, _ in events:
        if name in names:
            raise ValueError("an event %s already" % name)
    n_actors, n_actions, n_queries, n_events = (r.u16(flow_at + 0x10 + 2 * i) for i in range(4))
    actors_at, events_at = r.u64(flow_at + 0x28), r.u64(flow_at + 0x30)
    actor_names = [a["name"] for a in flow["actors"]]
    old = bytes(data)
    old += b"\0" * (-len(old) % 8)
    blob = _Blob(len(old))
    pointers = relt_pointers(data)
    # (the empty string, as an actor's empty sub actor name and argument and a DIC's root name: the file's own when an actor
    # has one, else a new one)
    empty = next((r.u64(actors_at + 0x38 * i + 8) for i in range(n_actors)
                  if r.string(r.u64(actors_at + 0x38 * i + 8)) == ""), None)
    if empty is None:
        empty = blob.string("")

    # the actors: the old records copied (their pointers with them), the new actor last
    new_actor = actor not in actor_names
    new_actors = blob.reserve(0x38 * (n_actors + new_actor))
    blob.buf[new_actors - blob.base:new_actors - blob.base + 0x38 * n_actors] = data[actors_at:actors_at + 0x38 * n_actors]
    blob.pointers += [new_actors + p - actors_at for p in pointers if actors_at <= p < actors_at + 0x38 * n_actors]
    if new_actor:
        a = new_actors + 0x38 * n_actors
        actions = blob.reserve(8)
        blob.pointer(a, blob.string(actor))
        blob.pointer(a + 8, empty)
        blob.pointer(a + 0x10, empty)
        blob.pointer(a + 0x18, actions)
        blob.pointer(a + 0x28, blob.container(actor_params, empty))
        blob.put(a + 0x30, "<HHHBB", 1, 0, 0xFFFF, 1, 0)
        blob.pointer(actions, blob.string(action))
        actor_index, action_index = n_actors, 0
        n_actions += 1
    else:
        actor_index = actor_names.index(actor)
        if action not in flow["actors"][actor_index]["actions"]:
            raise ValueError("%s has no action %s" % (actor, action))   # (not needed yet)
        action_index = flow["actors"][actor_index]["actions"].index(action)
        a = new_actors + 0x38 * actor_index
        if flow["actors"][actor_index]["params"] is None:
            raise ValueError("%s has no parameters" % actor)

    # the events: the old records copied, the new ones last, chained after `after`
    new_events = blob.reserve(0x30 * (n_events + len(events)))
    blob.buf[new_events - blob.base:new_events - blob.base + 0x30 * n_events] = data[events_at:events_at + 0x30 * n_events]
    blob.pointers += [new_events + p - events_at for p in pointers if events_at <= p < events_at + 0x30 * n_events]
    anchor = new_events + 0x30 * names.index(after)
    following = struct.unpack_from("<H", blob.buf, anchor - blob.base + 0xA)[0]
    for k, (name, params) in enumerate(events):
        e = new_events + 0x30 * (n_events + k)
        nxt = n_events + k + 1 if k + 1 < len(events) else following
        blob.pointer(e, blob.string(name))
        blob.put(e + 8, "<BxHHH", evfl.ACTION, nxt, actor_index, action_index)
        blob.pointer(e + 0x10, blob.container(params, empty))
    blob.put(anchor + 0xA, "<H", n_events)

    size = blob.here()
    blob.align()
    out = bytearray(old + bytes(blob.buf))
    # the flowchart: its arrays and counts
    struct.pack_into("<Q", out, flow_at + 0x28, new_actors)
    struct.pack_into("<Q", out, flow_at + 0x30, new_events)
    struct.pack_into("<HHHH", out, flow_at + 0x10, n_actors + new_actor, n_actions, n_queries, n_events + len(events))
    # the relocation table after it all, the header pointing to it
    at = len(out)
    out += relt_write(pointers + blob.pointers, at, size)
    struct.pack_into("<I", out, 0x18, at)
    struct.pack_into("<I", out, 0x1C, len(out))
    out = bytes(out)

    # read back: the old flowchart unchanged but for the new events and actor, every pointer of the new data relocated
    back = evfl.read(out)[flow_index]
    want = evfl.read(data)[flow_index]
    if new_actor:
        want["actors"].append({"name": actor, "sub": "", "argument": "", "actions": [action], "queries": [],
                               "params": dict(actor_params)})
    want["events"][names.index(after)]["next"] = n_events
    for k, (name, params) in enumerate(events):
        want["events"].append({"name": name, "type": "action", "next": n_events + k + 1 if k + 1 < len(events) else
                               (None if following == 0xFFFF else following), "actor": actor_index,
                               "action": action_index, "params": dict(params)})
    if back != want:
        raise ValueError("the flow read back is not the one wanted")
    if sorted(relt_pointers(out)) != sorted(set(pointers + blob.pointers)):
        raise ValueError("the relocation table read back is not the one written")
    return out
