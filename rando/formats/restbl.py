"""The resource size table (System/Resource/ResourceSizeTable.Product.*.rsizetable.zs, "RESTBL"): the memory the game sets aside
for each file, by the CRC32 of its romfs path without ".zs" (and by the full name for the few paths whose CRC32s collide).
A file bigger than its entry does not load (Longshot's readme, "Mods")."""
import struct
import zlib

NAME_SIZE = 160


class Table:
    def __init__(self, data):
        if data[:6] != b"RESTBL":
            raise ValueError("not a RESTBL")
        self.version, self.name_size, n_crc, n_name = struct.unpack_from("<IIII", data, 6)
        if self.name_size != NAME_SIZE:
            raise ValueError("RESTBL name size %d" % self.name_size)
        at = 22
        self.crc = {}
        for i in range(n_crc):
            h, size = struct.unpack_from("<II", data, at + 8 * i)
            self.crc[h] = size
        at += 8 * n_crc
        self.names = {}
        for i in range(n_name):
            e = at + (NAME_SIZE + 4) * i
            name = data[e:e + NAME_SIZE].split(b"\0", 1)[0].decode("utf-8")
            self.names[name] = struct.unpack_from("<I", data, e + NAME_SIZE)[0]
        if at + (NAME_SIZE + 4) * n_name != len(data):
            raise ValueError("RESTBL has %d bytes past its entries" % (len(data) - at - (NAME_SIZE + 4) * n_name))

    @staticmethod
    def key(path):
        return path[:-3] if path.endswith(".zs") else path

    def get(self, path):
        k = self.key(path)
        if k in self.names:
            return self.names[k]
        return self.crc.get(zlib.crc32(k.encode("utf-8")) & 0xFFFFFFFF)

    def set(self, path, size):
        k = self.key(path)
        if k in self.names:
            self.names[k] = size
        else:
            self.crc[zlib.crc32(k.encode("utf-8")) & 0xFFFFFFFF] = size

    def write(self):
        out = bytearray(b"RESTBL" + struct.pack("<IIII", self.version, self.name_size, len(self.crc), len(self.names)))
        for h in sorted(self.crc):
            out += struct.pack("<II", h, self.crc[h])
        for name in sorted(self.names, key=lambda s: s.encode("utf-8")):
            out += name.encode("utf-8").ljust(NAME_SIZE, b"\0") + struct.pack("<I", self.names[name])
        return bytes(out)
