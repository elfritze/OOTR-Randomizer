"""Just enough of the game's AI node files (.ainb, version 0x408, the map logic modules) to read a node graph and change a
value in place: each node's name, its immediate parameters, its inputs (with where each comes from) and its outputs, each
with the file offset of the value, so a change keeps the file's size and layout.

Layout (worked out on Logic/*.logic.module.ainb, checked against the strings each part names):
  header: 0x0C command count; 0x10 node count; 0x24 string pool (the file's last part); 0x2C immediate parameters (6 type offsets: int, bool, float, string, vec3,
  user); 0x34 inputs and outputs (12 offsets: each type's inputs, then its outputs); 0x38 multi-source list.
  commands from 0x74, 0x18 bytes each (an AI root has them; a logic module none), then the nodes, 0x3C bytes each: +0 type, +8 name (pool offset), +0x14 body.
  body: 6 x (base, count) immediates, then 6 x (input base, count, output base, count).
  immediate (int/bool/float/string): 0xC bytes, +0 name, +8 value. input: 0x10 bytes, +0 name, +4 source node (i16; -1
  none, <= -100 a multi list: entries -100 - n, the count in +6), +6 source output, +0xC value. output: 4 bytes, the name
  with bit 31 set when some node reads it. multi entry: 8 bytes, +0 node, +2 output.
"""
import struct

TYPES = ("int", "bool", "float", "string", "vec3", "user")
VERSION = 0x408
HEADER_SIZE, COMMAND_SIZE, NODE_SIZE = 0x74, 0x18, 0x3C
USED = 0x80000000


class File:
    def __init__(self, data):
        self.d = bytes(data)
        if self.d[:4] != b"AIB " or self.u32(4) != VERSION:
            raise ValueError("not an AINB file of version %#x" % VERSION)
        self.pool = self.u32(0x24)
        self.imm = [self.u32(self.u32(0x2C) + 4 * i) for i in range(6)]
        self.io = [self.u32(self.u32(0x34) + 4 * i) for i in range(12)]
        self.multi = self.u32(0x38)
        self.nodes_at = HEADER_SIZE + self.u32(0x0C) * COMMAND_SIZE
        self.nodes = [self._node(i) for i in range(self.u32(0x10))]

    def u32(self, at):
        return struct.unpack_from("<I", self.d, at)[0]

    def i16(self, at):
        return struct.unpack_from("<h", self.d, at)[0]

    def string(self, offset):
        at = self.pool + (offset & 0x3FFFFFFF)
        return self.d[at:self.d.index(b"\0", at)].decode("utf-8")

    def string_offset(self, s):
        """the pool offset of an existing string (a whole one)"""
        key = s.encode("utf-8") + b"\0"
        at = self.pool
        while True:
            at = self.d.find(key, at)
            if at < 0:
                raise ValueError("no string %r in the pool" % s)
            if at == self.pool or self.d[at - 1] == 0:
                return at - self.pool
            at += 1

    def with_string(self, s):
        """(the file with s added at the end of its string pool, s's pool offset): the pool is the file's last part"""
        try:
            return self.d, self.string_offset(s)
        except ValueError:
            return self.d + s.encode("utf-8") + b"\0", len(self.d) - self.pool

    def multi_entry(self, j):
        at = self.multi + 8 * j
        return at, self.i16(at), self.i16(at + 2)

    def _node(self, i):
        at = self.nodes_at + i * NODE_SIZE
        body = self.u32(at + 0x14)
        w = struct.unpack_from("<36I", self.d, body)
        node = {"index": i, "name": self.string(self.u32(at + 8)), "imm": {}, "inputs": {}, "outputs": {}}
        for t in range(4):
            for k in range(w[2 * t], w[2 * t] + w[2 * t + 1]):
                e = self.imm[t] + k * 0xC
                node["imm"][self.string(self.u32(e))] = (TYPES[t], e + 8)
        for t in range(4):
            ib, ic, ob, oc = w[12 + 4 * t:16 + 4 * t]
            for k in range(ib, ib + ic):
                e = self.io[2 * t] + k * 0x10
                src, out = self.i16(e + 4), self.i16(e + 6)
                if src >= 0:
                    sources = [(src, out, None)]
                elif src <= -100:
                    sources = [(n, o, a) for a, n, o in (self.multi_entry(j) for j in range(-100 - src, -100 - src + out))]
                else:
                    sources = []
                node["inputs"][self.string(self.u32(e))] = {"type": TYPES[t], "entry": e, "value_at": e + 0xC,
                                                            "sources": sources}
            node["outputs"][TYPES[t]] = [(self.string(self.u32(self.io[2 * t + 1] + 4 * k)), self.io[2 * t + 1] + 4 * k)
                                         for k in range(ob, ob + oc)]
        return node

    def value(self, at, type_):
        v = self.u32(at)
        return self.string(v) if type_ == "string" else v

    def readers(self, node, output):
        """every (node, input name) reading that bool output"""
        return [(n["index"], name) for n in self.nodes for name, i in n["inputs"].items()
                for s in i["sources"] if (s[0], s[1]) == (node, output) and i["type"] == "bool"]
