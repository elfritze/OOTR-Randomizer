"""A Havok tagfile (TAG0, SDK 2025.2, little endian data) inside the engine's Phive wrapper, as the cloth files
(Phive/Cloth/*.bphcl): the types it describes itself with, and its objects walked field by field. Read only, but for
numbers rewritten in place (nothing moves).

Phive wrapper: "Phive", ..., u32 header size (0x30) at 0x0c; the tagfile starts there.
Sections: u32 big endian (size with flags in the top 2 bits, counting the 8-byte header), 4 chars. TAG0 { SDKV, DATA, TYPE {
TPTR, TST1 (type strings), TNA1 (type names, templates), FST1 (field strings), TBDY (type bodies), THSH, TPAD }, INDX { ITEM,
PTCH } }.
TNA1: packed count, then per type from 1: packed name (TST1 index), packed template count, per template packed name, value
(a type when the name starts with 't').
TBDY: per type: packed id, parent, flags; by flag bit: 1 format, 2 subtype, 4 version, 8 size and alignment, 0x10 type flags,
0x20 fields (packed count: low 16 bits fields, the rest properties; each packed name (FST1), flags (with 0x80: one more
value follows), offset, type),
0x40 interfaces (count; type, flags), 0x80 attributes (a string index).
format: low 5 bits the kind (2 bool, 3 string, 4 int, 5 float, 6 pointer, 7 record, 8 array); a fixed array's count in
format >> 8, its element the subtype. ITEM: 12 bytes each: u32 type | kind << 28 (1 one object, 2 an array), u32 offset in
DATA, u32 count. A pointer or an hkArray's m_data, in DATA, holds an item index.
"""
import struct

KIND_BOOL, KIND_STRING, KIND_INT, KIND_FLOAT, KIND_POINTER, KIND_RECORD, KIND_ARRAY = 2, 3, 4, 5, 6, 7, 8


class Type:
    def __init__(self):
        self.name, self.templates = "", []
        self.parent = self.format = self.subtype = self.version = 0
        self.size = self.align = None
        self.fields = []   # (name, offset, type index)

    @property
    def kind(self):
        return self.format & 0x1F

    @property
    def fixed_count(self):
        return self.format >> 8


class Reader:
    def __init__(self, data, at, end):
        self.d, self.at, self.end = data, at, end

    def packed(self):
        b = self.d[self.at]
        if b < 0x80:
            n, v = 1, b
        elif b < 0xC0:
            n, v = 2, b & 0x3F
        elif b < 0xE0:
            n, v = 3, b & 0x1F
        elif b < 0xE8:
            n, v = 4, b & 0x07
        elif b < 0xF0:
            n, v = 5, b & 0x07
        elif b < 0xF8:
            n, v = 8, b & 0x07
        else:
            raise ValueError("packed integer %#x at %#x" % (b, self.at))
        for k in range(1, n):
            v = (v << 8) | self.d[self.at + k]
        self.at += n
        return v


class Tagfile:
    def __init__(self, data):
        self.data = bytearray(data)
        d = self.data
        if d[:5] != b"Phive":
            raise ValueError("not a Phive file")
        start = struct.unpack_from("<I", d, 0x0c)[0]
        self.sections = {}
        self._sections(start, len(d), 0)
        for need in ("DATA", "TST1", "TNA1", "FST1", "TBDY", "ITEM"):
            if need not in self.sections:
                raise ValueError("no %s section" % need)
        self.data_at = self.sections["DATA"][0]
        self._types()
        a, b = self.sections["ITEM"]
        self.items = []
        for at in range(a, b, 12):
            t, off, n = struct.unpack_from("<III", d, at)
            self.items.append((t & 0x0FFFFFFF, t >> 28, off, n))

    def _sections(self, at, end, depth):
        d = self.data
        while at + 8 <= end:
            head = struct.unpack_from(">I", d, at)[0]
            size, tag = head & 0x3FFFFFFF, bytes(d[at + 4:at + 8]).decode("latin1")
            if size < 8 or not tag.isalnum():
                return
            if tag in ("TAG0", "TYPE", "INDX"):
                self._sections(at + 8, at + size, depth + 1)
            else:
                self.sections[tag] = (at + 8, at + size)
            at += size
            if depth == 0:
                return   # (one tagfile; the Phive tables follow it)

    def _strings(self, tag):
        a, b = self.sections[tag]
        return bytes(self.data[a:b]).split(b"\0")

    def _types(self):
        tstr, fstr = self._strings("TST1"), self._strings("FST1")
        r = Reader(self.data, *self.sections["TNA1"])
        n = r.packed()
        self.types = [Type() for _ in range(n)]
        for t in self.types[1:]:
            t.name = tstr[r.packed()].decode("latin1")
            for _ in range(r.packed()):
                name = tstr[r.packed()].decode("latin1")
                t.templates.append((name, r.packed()))
        r = Reader(self.data, *self.sections["TBDY"])
        while r.at < r.end:
            i = r.packed()
            if i == 0:
                continue
            t = self.types[i]
            t.parent = r.packed()
            flags = r.packed()
            if flags & 0x01:
                t.format = r.packed()
            if flags & 0x02:
                t.subtype = r.packed()
            if flags & 0x04:
                t.version = r.packed()
            if flags & 0x08:
                t.size, t.align = r.packed(), r.packed()
            if flags & 0x10:
                r.packed()
            if flags & 0x20:
                count = r.packed()
                for k in range((count & 0xFFFF) + (count >> 16)):
                    name = fstr[r.packed()].decode("latin1")
                    if r.packed() & 0x80:   # (the field's flags: with 0x80, one more value before the offset)
                        r.packed()
                    offset, ftype = r.packed(), r.packed()
                    if k < (count & 0xFFFF):
                        t.fields.append((name, offset, ftype))
            if flags & 0x40:
                for _ in range(r.packed()):
                    r.packed(), r.packed()
            if flags & 0x80:
                r.packed()
        if r.at != r.end:
            raise ValueError("the type bodies end at %#x, not %#x" % (r.at, r.end))

    # types
    def full_name(self, i):
        t = self.types[i]
        if not t.templates:
            return t.name
        return "%s<%s>" % (t.name, ", ".join(self.full_name(v) if n.startswith("t") else str(v) for n, v in t.templates))

    def resolved(self, i):
        """the type whose format and size stand for type i's (a type without its own takes its parent's)"""
        seen = 0
        while self.types[i].format == 0 and self.types[i].parent and seen < 32:
            i, seen = self.types[i].parent, seen + 1
        return i

    def size_of(self, i):
        seen = 0
        while self.types[i].size is None and self.types[i].parent and seen < 32:
            i, seen = self.types[i].parent, seen + 1
        if self.types[i].size is None:
            raise ValueError("type %s has no size" % self.full_name(i))
        return self.types[i].size

    def all_fields(self, i):
        """(name, offset, type) of a record's fields, its parents' first"""
        chain = []
        while i:
            chain.append(i)
            i = self.types[i].parent
        out = []
        for j in reversed(chain):
            out += self.types[j].fields
        return out

    def is_a(self, i, name):
        while i:
            if self.types[i].name == name:
                return True
            i = self.types[i].parent
        return False

    # data
    def u32(self, off):
        return struct.unpack_from("<I", self.data, self.data_at + off)[0]

    def floats(self, off, n):
        return struct.unpack_from("<%df" % n, self.data, self.data_at + off)

    def set_floats(self, off, values):
        struct.pack_into("<%df" % len(values), self.data, self.data_at + off, *values)

    def walk(self, visit):
        """every object reached from the root, once: visit(path, type index, offset) for each value, where path is the
        tuple of (record type name, field name) steps taken; visit returns False to not go inside a value"""
        seen = set()

        def value(path, ti, off):
            if visit(path, ti, off) is False:
                return
            t = self.types[self.resolved(ti)]
            kind = t.kind
            if kind == KIND_RECORD:
                for name, foff, ftype in self.all_fields(ti):
                    value(path + ((self.types[ti].name, name),), ftype, off + foff)
            elif kind == KIND_ARRAY:
                if t.fixed_count:   # (a fixed array, inline)
                    size = self.size_of(t.subtype)
                    for k in range(t.fixed_count):
                        value(path, t.subtype, off + k * size)
                else:               # (an hkArray and the like: its first field holds the item)
                    item(path, self.u32(off))
            elif kind == KIND_POINTER:
                item(path, self.u32(off))

        def item(path, index):
            if not index or index in seen:
                return
            if index >= len(self.items):
                raise ValueError("item %d of %d" % (index, len(self.items)))
            seen.add(index)
            ti, _kind, off, n = self.items[index]
            if self.types[self.resolved(ti)].kind in (KIND_INT, KIND_BOOL, KIND_STRING) or self.types[ti].name == "char":
                return
            size = self.size_of(ti)
            for k in range(n):
                value(path, ti, off + k * size)

        item((), 1)

    def read(self, ti, off, depth=12):
        """a value as Python: a record a dict of its fields, an array or a pointer's target a list (one object: itself),
        numbers as numbers, a string pointer as a str. A record's dict also has "@": (type, offset), and "@<field>":
        (element type, offset, count) for each array field with elements: where to rewrite them in DATA"""
        t = self.types[self.resolved(ti)]
        kind = t.kind
        if kind == KIND_FLOAT:
            return self.floats(off, 1)[0]
        if kind in (KIND_INT, KIND_BOOL):
            size = self.size_of(ti)
            return int.from_bytes(self.data[self.data_at + off:self.data_at + off + size], "little")
        if kind == KIND_STRING:
            index = self.u32(off)
            if not index:
                return None
            _ti, _k, o, n = self.items[index]
            return bytes(self.data[self.data_at + o:self.data_at + o + n]).split(b"\0")[0].decode("latin1")
        if depth <= 0:
            return None
        if kind == KIND_RECORD:
            out = {"@": (ti, off)}   # (where the record is; "@field": where an array field's elements are)
            for name, fo, ft in self.all_fields(ti):
                out[name] = self.read(ft, off + fo, depth - 1)
                ft_kind = self.types[self.resolved(ft)]
                if ft_kind.kind == KIND_ARRAY and not ft_kind.fixed_count and self.u32(off + fo):
                    eti, _k, o, n = self.items[self.u32(off + fo)]
                    out["@" + name] = (eti, o, n)
            return out
        if kind == KIND_ARRAY and t.fixed_count:
            size = self.size_of(t.subtype)
            return [self.read(t.subtype, off + k * size, depth - 1) for k in range(t.fixed_count)]
        index = self.u32(off)   # (an hkArray or a pointer)
        if not index:
            return [] if kind == KIND_ARRAY else None
        eti, _k, o, n = self.items[index]
        size = self.size_of(eti)
        out = [self.read(eti, o + k * size, depth - 1) for k in range(n)]
        return out if kind == KIND_ARRAY else out[0]

    def root(self, depth=12):
        ti, _k, off, _n = self.items[1]
        return self.read(ti, off, depth)
