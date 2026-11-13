"""BFEVFL event flows (version 4, little endian, as the game's Event/EventFlow/*.bfevfl): read only.

The layout is Breath of the Wild's (leoetlino's evfl documents version 3) with larger records: an actor is 0x38 bytes, an
event 0x30 and an entry point 0x20; a switch's case is 8 bytes (u32 value, u32 event). Pointers are absolute file offsets (u64); a string is a u16 length, its bytes and a
null, and is referenced by the offset of its length."""
import struct

# (5 and 6 are new in version 4: a sub flow called and its returned label switched on (cases keyed by the label's hash), and
# the end of a sub flow returning a label)
ACTION, SWITCH, FORK, JOIN, SUBFLOW, SUBFLOW_SWITCH, RETURN = range(7)
TYPE_NAMES = ("action", "switch", "fork", "join", "subflow", "subflow_switch", "return")

# parameter container data types
ARGUMENT, CONTAINER, INT, BOOL, FLOAT, STRING, WSTRING, INT_ARRAY, BOOL_ARRAY, FLOAT_ARRAY, STRING_ARRAY, WSTRING_ARRAY, \
    ACTOR_ID = range(13)


class Reader:
    def __init__(self, data):
        self.d = data

    def u8(self, at):
        return self.d[at]

    def u16(self, at):
        return struct.unpack_from("<H", self.d, at)[0]

    def u32(self, at):
        return struct.unpack_from("<I", self.d, at)[0]

    def u64(self, at):
        return struct.unpack_from("<Q", self.d, at)[0]

    def string(self, ptr):
        if not ptr:
            return None
        n = self.u16(ptr)
        return self.d[ptr + 2:ptr + 2 + n].decode("utf-8")

    def dic(self, ptr):
        """a DIC's names in entry order (entry 0 is the root and has none)"""
        if not ptr:
            return []
        if self.d[ptr:ptr + 4] != b"DIC ":
            raise ValueError("no DIC at %#x" % ptr)
        n = self.u32(ptr + 4)
        return [self.string(self.u64(ptr + 8 + 16 * i + 8)) for i in range(1, n + 1)]

    def container(self, ptr):
        if not ptr:
            return None
        t, n = self.u8(ptr), self.u16(ptr + 2)
        items = ptr + 0x10
        if t == CONTAINER:
            names = self.dic(self.u64(ptr + 8))
            return {name: self.container(self.u64(items + 8 * i)) for i, name in enumerate(names)}
        if t in (INT, INT_ARRAY):
            vals = [struct.unpack_from("<i", self.d, items + 4 * i)[0] for i in range(n)]
        elif t in (BOOL, BOOL_ARRAY):
            vals = [self.u32(items + 4 * i) != 0 for i in range(n)]
        elif t in (FLOAT, FLOAT_ARRAY):
            vals = [struct.unpack_from("<f", self.d, items + 4 * i)[0] for i in range(n)]
        elif t in (STRING, STRING_ARRAY, WSTRING, WSTRING_ARRAY, ARGUMENT):
            vals = [self.string(self.u64(items + 8 * i)) for i in range(n)]
        elif t == ACTOR_ID:
            return {"actor": self.string(self.u64(items)), "sub": self.string(self.u64(items + 8))}
        else:
            raise ValueError("container type %d at %#x" % (t, ptr))
        if t == ARGUMENT:
            return {"argument": vals[0]}
        return vals[0] if t in (INT, BOOL, FLOAT, STRING, WSTRING) else vals


def read(data):
    if data[:8] != b"BFEVFL\0\0":
        raise ValueError("not a BFEVFL")
    r = Reader(data)
    flowcharts = []
    count = r.u16(0x20)
    array = r.u64(0x28)
    for i in range(count):
        flowcharts.append(_flowchart(r, r.u64(array + 8 * i)))
    return flowcharts


def _flowchart(r, at):
    if r.d[at:at + 4] != b"EVFL":
        raise ValueError("no EVFL at %#x" % at)
    n_actors, _n_actions, _n_queries, n_events, n_entries = (r.u16(at + 0x10 + 2 * i) for i in range(5))
    name = r.string(r.u64(at + 0x20))
    actors_at, events_at, entry_dic, entries_at = (r.u64(at + 0x28 + 8 * i) for i in range(4))
    actors = []
    for i in range(n_actors):
        a = actors_at + 0x38 * i
        n_act, n_q = r.u16(a + 0x30), r.u16(a + 0x32)
        actors.append({
            "name": r.string(r.u64(a)), "sub": r.string(r.u64(a + 8)), "argument": r.string(r.u64(a + 0x10)),
            "actions": [r.string(r.u64(r.u64(a + 0x18) + 8 * k)) for k in range(n_act)],
            "queries": [r.string(r.u64(r.u64(a + 0x20) + 8 * k)) for k in range(n_q)],
            "params": r.container(r.u64(a + 0x28)),
        })
    events = []
    for i in range(n_events):
        e = events_at + 0x30 * i
        t = r.u8(e + 8)
        ev = {"name": r.string(r.u64(e)), "type": TYPE_NAMES[t]}
        if t == ACTION:
            ev.update(next=_idx(r.u16(e + 0xA)), actor=r.u16(e + 0xC), action=r.u16(e + 0xE), params=r.container(r.u64(e + 0x10)))
        elif t == SWITCH:
            n = r.u16(e + 0xA)
            cases_at = r.u64(e + 0x18)
            ev.update(actor=r.u16(e + 0xC), query=r.u16(e + 0xE), params=r.container(r.u64(e + 0x10)),
                      cases={r.u32(cases_at + 8 * k): r.u32(cases_at + 8 * k + 4) for k in range(n)})
        elif t == SUBFLOW_SWITCH:
            n = r.u16(e + 0xA)
            cases_at = r.u64(e + 0x18)
            ev.update(params=r.container(r.u64(e + 0x10)), flowchart=r.string(r.u64(e + 0x20)),
                      entry=r.string(r.u64(e + 0x28)),
                      cases={r.u32(cases_at + 8 * k): r.u32(cases_at + 8 * k + 4) for k in range(n)})
        elif t == RETURN:
            ev.update(label=r.u32(e + 0xC))
        elif t == FORK:
            n = r.u16(e + 0xA)
            forks_at = r.u64(e + 0x10)
            ev.update(join=r.u16(e + 0xC), forks=[r.u16(forks_at + 2 * k) for k in range(n)])
        elif t == JOIN:
            ev.update(next=_idx(r.u16(e + 0xA)))
        elif t == SUBFLOW:
            ev.update(next=_idx(r.u16(e + 0xA)), params=r.container(r.u64(e + 0x10)),
                      flowchart=r.string(r.u64(e + 0x18)), entry=r.string(r.u64(e + 0x20)))
        else:
            raise ValueError("event type %d at %#x" % (t, e))
        events.append(ev)
    entry_names = r.dic(entry_dic)
    entries = {}
    for i, en in enumerate(entry_names):
        e = entries_at + 0x20 * i
        entries[en] = r.u16(e + 0x1C)
    return {"name": name, "actors": actors, "events": events, "entries": entries}


def _idx(v):
    return None if v == 0xFFFF else v
