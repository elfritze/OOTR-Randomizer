"""Read-only decoder for the remake's progress.sav (the save of one slot), for the tracker.

Layout (as documented by the OotrR randomizer's tracker/save_reader.py, MIT): a 32-byte header (magic 0x01020304, format
version, end of the tables), then 33 typed tables of (key, value) u32 pairs, each opened by a (0, type) record, then
out-of-line data. Type 0 holds the Bool flags, keyed by murmur3 of the flag's name ("IsGet.Item_Hookshot"); type 32
points at a sorted, zero-terminated list of the true Bool64bitKey keys (one per placed actor that remembers being taken,
by the actor's hash in its map). Nothing is ever written."""
import os
import struct

MAGIC = 0x01020304
MAX_SIZE = 16 * 1024 * 1024


class SaveError(ValueError):
    pass


def murmur3(text, seed=0):
    """MurmurHash3 x86 32-bit of the UTF-8 text: the game's GameData key of a flag name"""
    data = text.encode("utf-8")
    h, c1, c2, n = seed, 0xCC9E2D51, 0x1B873593, len(data)
    for i in range(0, n // 4 * 4, 4):
        k = int.from_bytes(data[i:i + 4], "little")
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        h ^= (k * c2) & 0xFFFFFFFF
        h = ((h << 13) | (h >> 19)) & 0xFFFFFFFF
        h = (h * 5 + 0xE6546B64) & 0xFFFFFFFF
    tail, k = data[n // 4 * 4:], 0
    for i, b in enumerate(tail):
        k |= b << (8 * i)
    if tail:
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        h ^= (k * c2) & 0xFFFFFFFF
    h ^= n
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= h >> 16
    return h


def decode(data):
    """{"bool": {key: bool}, "int": {key: int}, "bool64": set of true 64-bit keys}"""
    if not 32 + 33 * 8 + 16 <= len(data) <= MAX_SIZE:
        raise SaveError("not a progress save (size)")
    magic, _version, end = struct.unpack_from("<III", data)
    if magic != MAGIC or end % 8 or not 32 + 33 * 8 <= end <= len(data) - 8:
        raise SaveError("not a progress save")
    tables = [dict() for _ in range(33)]
    section = -1
    for at in range(32, end, 8):
        key, value = struct.unpack_from("<II", data, at)
        if key == 0:
            if value != section + 1 or value >= 33:
                raise SaveError("tables out of order")
            section = value
        elif section >= 0:
            tables[section][key] = value
    if section != 32 or len(tables[32]) != 1:
        raise SaveError("not a progress save (tables)")
    bools = {k: bool(v) for k, v in tables[0].items()}
    ints = {k: struct.unpack("<i", struct.pack("<I", v))[0] for k, v in tables[2].items()}
    start = next(iter(tables[32].values()))
    keys64, cursor = set(), start
    while cursor + 8 <= len(data):
        v = struct.unpack_from("<Q", data, cursor)[0]
        cursor += 8
        if v == 0:
            break
        keys64.add(v)
    return {"bool": bools, "int": ints, "bool64": keys64}


def read(path, attempts=3):
    """the save at path, read twice to be sure the game was not writing it"""
    for _ in range(attempts):
        with open(path, "rb") as f:
            first = f.read(MAX_SIZE + 1)
        with open(path, "rb") as f:
            second = f.read(MAX_SIZE + 1)
        if first == second:
            return decode(second)
    raise SaveError("the save kept changing while it was read")


def find_saves(game_folder):
    """[(mtime, path)] of every progress.sav under the game folder's user/save, newest first"""
    out = []
    root = os.path.join(game_folder, "user", "save")
    for d, _, files in os.walk(root):
        if "progress.sav" in files:
            p = os.path.join(d, "progress.sav")
            out.append((os.path.getmtime(p), p))
    return sorted(out, reverse=True)


def is_get(save, name):
    return save["bool"].get(murmur3("IsGet." + name), False)
