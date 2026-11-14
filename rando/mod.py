"""A RomFS mod being written: changed game files compressed as the game's own were, and the resource size table shipped with
the mod when a file grew past what the game sets aside for it."""
import os

from .formats import restbl

RSTB = "System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs"


def align32(n):
    return (n + 31) & ~31


def entry_for(size, original_size, original_entry):
    """the table entry a file of this decompressed size needs: the game's entries are the size rounded up to 32 plus a margin
    per kind of file (264 for every map and the RSDB tables, 312 for actor packs), so the original's own margin is kept"""
    margin = original_entry - align32(original_size)
    if margin < 0:
        raise ValueError("an entry below its file's size")
    return align32(size) + margin


class Mod:
    def __init__(self, romfs, codec, out_romfs):
        self.romfs, self.codec, self.out = romfs, codec, out_romfs
        raw = codec.read(os.path.join(romfs, *RSTB.split("/")))
        self.table = restbl.Table(raw)
        self.original = restbl.Table(raw)   # (the game's own entries, for each kind of file's margin)
        self.grown = []
        self.data = {}   # (rel: what was last written: a second change to a file builds on the first)

    def original_entry(self, rel):
        return self.original.get(rel)

    def read(self, rel):
        """a file's contents as the mod has it so far: the game's own, or what was last written for it"""
        if rel in self.data:
            return self.data[rel]
        path = os.path.join(self.romfs, *rel.split("/"))
        if not rel.endswith(".zs"):   # (a loose uncompressed file, as Component/AIScheduleParam's)
            return open(path, "rb").read()
        return self.codec.read(path)

    def write(self, rel, data):
        """rel: the romfs path ("Banc/X/Y.bcett.byml.zs"); data: its new decompressed contents (build it on read(rel))"""
        self.data[rel] = data
        original = open(os.path.join(self.romfs, *rel.split("/")), "rb").read()
        name = os.path.basename(rel)
        if rel.endswith(".zs"):
            packed = self.codec.compress_like(data, original)
            if self.codec.decompress(packed, name) != data:
                raise ValueError("%s: does not decompress back" % rel)
            original_size = len(self.codec.decompress(original, name))
        else:
            packed, original_size = data, len(original)
        entry = self.table.get(rel)
        if entry is None:
            raise ValueError("%s: not in the resource size table" % rel)
        need = entry_for(len(data), original_size, self.original_entry(rel))
        if need > entry:
            self.table.set(rel, need)
            self.grown.append((rel, entry, need))
        dst = os.path.join(self.out, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(packed)

    def add(self, rel, data, like):
        """a file the game does not have (Hookshot's mods may add files): compressed as the game file `like` is, with a
        size-table entry of its size and `like`'s margin"""
        import zlib
        if os.path.exists(os.path.join(self.romfs, *rel.split("/"))):
            raise ValueError("%s is a game file: write it" % rel)
        original = open(os.path.join(self.romfs, *like.split("/")), "rb").read()
        packed = self.codec.compress_like(data, original)
        if self.codec.decompress(packed, os.path.basename(rel)) != data:
            raise ValueError("%s: does not decompress back" % rel)
        key = restbl.Table.key(rel)
        if key in self.table.names or (zlib.crc32(key.encode("utf-8")) & 0xFFFFFFFF) in self.table.crc:
            raise ValueError("%s: its CRC32 is another file's" % rel)
        need = entry_for(len(data), len(self.codec.decompress(original, os.path.basename(like))), self.original_entry(like))
        self.table.set(rel, need)
        self.grown.append((rel, 0, need))
        dst = os.path.join(self.out, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(packed)

    def finish(self):
        """the table, when a file grew past its entry (the game's own table otherwise stays the one used)"""
        dst = os.path.join(self.out, *RSTB.split("/"))
        if not self.grown:
            if os.path.exists(dst):
                os.remove(dst)
            return
        data = self.table.write()
        packed = self.codec.compress_like(data, open(os.path.join(self.romfs, *RSTB.split("/")), "rb").read())
        if restbl.Table(self.codec.decompress(packed)).write() != data:
            raise ValueError("the size table does not read back")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(packed)
