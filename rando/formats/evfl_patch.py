"""Changing a string parameter of one event in a BFEVFL (as an NPC's gift: Dm_SY_GetInEvent's ActorName) without rewriting
the file: the new string is put after the file's end and the parameter's pointer is moved to it. Nothing else changes: every
other pointer, the relocation table (the parameter's pointer was in it already) and the string pool stay as they were; the
header's file size grows."""
import struct

from . import evfl


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
