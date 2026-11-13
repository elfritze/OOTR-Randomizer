"""BYML (either byte order, versions 2 to 7, as the game's .byml files): read into Python values, write back.

Types that Python cannot tell apart are wrapped so a file written back keeps them: int is BYML's int32 and float its float32;
U32, I64, U64 and F64 are the others. Hash32Dict and Hash64Dict are version 7's dictionaries keyed by hash."""
import struct


class U32(int):
    pass


class I64(int):
    pass


class U64(int):
    pass


class F64(float):
    pass


class Hash32Dict(dict):
    pass


class Hash64Dict(dict):
    pass


STRING, BINARY, FILE, ARRAY, DICT, STRING_TABLE = 0xA0, 0xA1, 0xA2, 0xC0, 0xC1, 0xC2
HASH32, HASH64 = 0x20, 0x21
BOOL, INT, FLOAT, UINT, INT64, UINT64, DOUBLE, NULL = 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xFF
CONTAINERS = (ARRAY, DICT, HASH32, HASH64)


def _string_table(data, at, e="<"):
    if not at:
        return []
    if data[at] != STRING_TABLE:
        raise ValueError("bad string table at %#x" % at)
    n = int.from_bytes(data[at + 1:at + 4], _BO[e])
    offs = struct.unpack_from(e + "%dI" % (n + 1), data, at + 4)
    return [data[at + offs[i]:data.index(b"\0", at + offs[i])].decode("utf-8") for i in range(n)]


_BO = {"<": "little", ">": "big"}
_MAGIC = {"<": b"YB", ">": b"BY"}


def endian(data):
    """'<' for a little-endian BYML (YB), '>' for a big-endian one (BY)"""
    for e, m in _MAGIC.items():
        if data[:2] == m:
            return e
    raise ValueError("not a BYML")


def read(data):
    """(root, version); the byte order is endian(data)"""
    e = endian(data)
    bo = _BO[e]
    version, keys_at, strings_at, root_at = struct.unpack_from(e + "HIII", data, 2)
    keys, strings = _string_table(data, keys_at, e), _string_table(data, strings_at, e)

    def value(t, raw):
        if t == STRING:
            return strings[raw]
        if t == BOOL:
            return bool(raw)
        if t == INT:
            return struct.unpack(e + "i", struct.pack(e + "I", raw))[0]
        if t == FLOAT:
            return struct.unpack(e + "f", struct.pack(e + "I", raw))[0]
        if t == UINT:
            return U32(raw)
        if t == INT64:
            return I64(struct.unpack_from(e + "q", data, raw)[0])
        if t == UINT64:
            return U64(struct.unpack_from(e + "Q", data, raw)[0])
        if t == DOUBLE:
            return F64(struct.unpack_from(e + "d", data, raw)[0])
        if t == NULL:
            return None
        if t == BINARY:
            n = struct.unpack_from(e + "I", data, raw)[0]
            return bytes(data[raw + 4:raw + 4 + n])
        if t in CONTAINERS:
            return node(raw)
        raise ValueError("BYML type %#x not supported" % t)

    def node(at):
        t, n = data[at], int.from_bytes(data[at + 1:at + 4], bo)
        if t == ARRAY:
            types = data[at + 4:at + 4 + n]
            vals_at = at + 4 + ((n + 3) & ~3)
            return [value(types[i], struct.unpack_from(e + "I", data, vals_at + 4 * i)[0]) for i in range(n)]
        if t == DICT:
            out = {}
            for i in range(n):
                p = at + 4 + 8 * i
                k = int.from_bytes(data[p:p + 3], bo)
                out[keys[k]] = value(data[p + 3], struct.unpack_from(e + "I", data, p + 4)[0])
            return out
        if t in (HASH32, HASH64):
            hw = 4 if t == HASH32 else 8
            ent = hw + 4
            types_at = at + 4 + ent * n
            out = Hash32Dict() if t == HASH32 else Hash64Dict()
            for i in range(n):
                p = at + 4 + ent * i
                h = int.from_bytes(data[p:p + hw], bo)
                out[h] = value(data[types_at + i], struct.unpack_from(e + "I", data, p + hw)[0])
            return out
        raise ValueError("BYML node %#x at %#x not supported" % (t, at))

    return (node(root_at) if root_at else None), version


def _type_of(v):
    if isinstance(v, bool):
        return BOOL
    if isinstance(v, U32):
        return UINT
    if isinstance(v, I64):
        return INT64
    if isinstance(v, U64):
        return UINT64
    if isinstance(v, int):
        return INT
    if isinstance(v, F64):
        return DOUBLE
    if isinstance(v, float):
        return FLOAT
    if isinstance(v, str):
        return STRING
    if isinstance(v, bytes):
        return BINARY
    if v is None:
        return NULL
    if isinstance(v, Hash32Dict):
        return HASH32
    if isinstance(v, Hash64Dict):
        return HASH64
    if isinstance(v, dict):
        return DICT
    if isinstance(v, list):
        return ARRAY
    raise TypeError("cannot write %r to BYML" % type(v))


def _key(v):
    """a hashable value equal for equal BYML values of the same types (the writer's sharing of equal nodes)"""
    t = _type_of(v)
    if t in (ARRAY,):
        return (t, tuple(_key(x) for x in v))
    if t in (DICT, HASH32, HASH64):
        return (t, tuple((k, _key(x)) for k, x in v.items()))
    if t in (FLOAT, DOUBLE):
        return (t, struct.pack("<d", v))   # (NaN and -0.0 by their bits)
    return (t, v)


def write(root, version=7, e="<"):
    """root as a BYML of this version and byte order (e: '<' little, '>' big)"""
    bo = _BO[e]
    keys, strings = set(), set()

    def collect(v):
        if isinstance(v, (Hash32Dict, Hash64Dict)):
            for x in v.values():
                collect(x)
        elif isinstance(v, dict):
            for k, x in v.items():
                keys.add(k)
                collect(x)
        elif isinstance(v, list):
            for x in v:
                collect(x)
        elif isinstance(v, str):
            strings.add(v)

    collect(root)
    # (sorted by their UTF-8 bytes: the game looks keys up by binary search)
    key_list = sorted(keys, key=lambda s: s.encode("utf-8"))
    str_list = sorted(strings, key=lambda s: s.encode("utf-8"))
    key_index = {k: i for i, k in enumerate(key_list)}
    str_index = {s: i for i, s in enumerate(str_list)}

    out = bytearray(16)

    def align(a=4):
        out.extend(b"\0" * (-len(out) % a))

    def table(lst):
        if not lst:
            return 0
        align()
        at = len(out)
        enc = [s.encode("utf-8") + b"\0" for s in lst]
        offs, pos = [], 4 + 4 * (len(lst) + 1)
        for b in enc:
            offs.append(pos)
            pos += len(b)
        offs.append(pos)
        out.extend(bytes([STRING_TABLE]) + len(lst).to_bytes(3, bo))
        out.extend(struct.pack(e + "%dI" % len(offs), *offs))
        for b in enc:
            out.extend(b)
        return at

    keys_at = table(key_list)
    strings_at = table(str_list)

    # (Nintendo's writer puts every 64-bit value before the root, once each, in the order a depth-first walk meets them)
    wide = {}

    def collect_wide(v):
        t = _type_of(v)
        if t in (INT64, UINT64, DOUBLE):
            bits = struct.pack({INT64: e + "q", UINT64: e + "Q", DOUBLE: e + "d"}[t], v)
            if bits not in wide:
                align()
                wide[bits] = len(out)
                out.extend(bits)
        elif t == DICT:
            for k in sorted(v, key=lambda s: s.encode("utf-8")):
                collect_wide(v[k])
        elif t in (HASH32, HASH64):
            for h in sorted(v):
                collect_wide(v[h])
        elif t == ARRAY:
            for x in v:
                collect_wide(x)

    if root is not None:
        collect_wide(root)

    def scalar(t, v):
        """the 4-byte value of v (writing out-of-line data first when the type needs it)"""
        if t == STRING:
            return str_index[v]
        if t == BOOL:
            return 1 if v else 0
        if t == INT:
            return struct.unpack(e + "I", struct.pack(e + "i", v))[0]
        if t == FLOAT:
            return struct.unpack(e + "I", struct.pack(e + "f", v))[0]
        if t == UINT:
            return int(v) & 0xFFFFFFFF
        if t == NULL:
            return 0
        if t in (INT64, UINT64, DOUBLE):
            return wide[struct.pack({INT64: e + "q", UINT64: e + "Q", DOUBLE: e + "d"}[t], v)]
        if t == BINARY:
            align()
            at = len(out)
            out.extend(struct.pack(e + "I", len(v)) + v)
            return at
        raise TypeError(t)

    # As Nintendo's writer lays a file out (and oead's): a container's own node first, then the out-of-line values its items
    # point at (containers, 64-bit numbers, binary data) in item order, each written once: an equal value written before is
    # pointed at again.
    written = {}

    def inline(t, v):
        return t not in CONTAINERS and t != BINARY

    def node(t, v):
        key = _key(v)
        if key in written:
            return written[key]
        at = container(t, v) if t in CONTAINERS else scalar(t, v)
        written[key] = at
        return at

    def container(t, v):
        if t == ARRAY:
            items = [(_type_of(x), x, None) for x in v]
        elif t == DICT:
            items = [(_type_of(v[k]), v[k], k) for k in sorted(v, key=lambda s: s.encode("utf-8"))]
        else:
            items = [(_type_of(v[h]), v[h], h) for h in sorted(v)]
        align()
        at = len(out)
        out.extend(bytes([t]) + len(items).to_bytes(3, bo))
        slots = []   # (offset of a value to fill in, its type, the value)
        if t == ARRAY:
            out.extend(bytes(it[0] for it in items))
            align()
            for it in items:
                slots.append((len(out), it[0], it[1]))
                out.extend(b"\0\0\0\0")
        elif t == DICT:
            for it in items:
                out.extend(key_index[it[2]].to_bytes(3, bo) + bytes([it[0]]))
                slots.append((len(out), it[0], it[1]))
                out.extend(b"\0\0\0\0")
        else:
            hw = 4 if t == HASH32 else 8
            for it in items:
                out.extend(it[2].to_bytes(hw, bo))
                slots.append((len(out), it[0], it[1]))
                out.extend(b"\0\0\0\0")
            out.extend(bytes(it[0] for it in items))
            align()
        for pos, it_t, it_v in slots:
            if inline(it_t, it_v):
                struct.pack_into(e + "I", out, pos, scalar(it_t, it_v))
        for pos, it_t, it_v in slots:
            if not inline(it_t, it_v):
                struct.pack_into(e + "I", out, pos, node(it_t, it_v))
        return at

    root_at = node(_type_of(root), root) if root is not None else 0
    struct.pack_into(e + "2sHIII", out, 0, _MAGIC[e], version, keys_at, strings_at, root_at)
    return bytes(out)
