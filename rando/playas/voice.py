"""Adult Link's voice replaced by another character's: that character's grunts, cries and laughs (its
NV_<language>_Custom_<name>.bars archives: Ganondorf's 68 clips of the final battle; Zelda's six and Sheik's forty) in
place of Link's 352 voice clips (Vo_PlAdult_* in Sound/Resource/Player_Adult.bars), each by a clip of the fitting kind
and the nearest length (characters.py: which kinds for which of Link's).

The game's sound has nothing that knows which tunic is worn (its conditions are the ground's material, the two boots...):
the voice is adult Link's whatever he wears, the Kokiri tunic too. Child Link keeps his.

A sound archive (BARS 1.2): "BARS", u32 size, BOM, version, u32 count; count CRC32s of the assets' names (sorted); count
pairs (u32 metadata offset, u32 audio offset). Metadata (AMTA): +0x08 u32 size, +0x24 u32 offset of its name from that
field, +0x2c u32 type (2 audio whole in the archive, 3 streamed: bit 0), +0x38 four floats of loudness. Audio (BWAV):
+0x08 u32 CRC of the whole clip, +0x0c u16 prefetch (1: only the start is here, 0x2080 bytes for one channel, the whole
clip in Sound/Resource/Stream/<asset name>.bwav with the same CRC), +0x14 u32 sample rate, +0x18 u32 samples in all.
Several assets may share one audio offset.

So, in place (the archive keeps its size):
  a streamed clip of Link's   its start in the archive overwritten by the start of the other's clip, its stream file
                              replaced by that clip's (a loose file: not in the resource size table); or, by a short
                              clip the other's archive holds whole, that clip whole, the asset typed as whole
  a whole clip of Link's      (35 short ones, smaller than a start) its audio offset pointed at a clip already written
                              for another, its type that clip's, a stream file added under its name if it is streamed
  loudness                    the other's clip's
"""
import re
import struct
import zlib

PREFETCH = 0x2080   # (a one-channel clip's start in an archive)
LINK = "Vo_PlAdult_"


class Asset:
    def __init__(self, data, index, count):
        self.entry = 0x10 + 4 * count + 8 * index
        self.amta, self.at = struct.unpack_from("<II", data, self.entry)
        name = self.amta + 0x24 + struct.unpack_from("<I", data, self.amta + 0x24)[0]   # (an offset from its own field)
        self.name = bytes(data[name:data.index(b"\0", name)]).decode()
        self.type = struct.unpack_from("<I", data, self.amta + 0x2c)[0]
        self.crc = struct.unpack_from("<I", data, self.at + 8)[0]
        self.prefetch, self.channels = struct.unpack_from("<HH", data, self.at + 0xc)
        rate, samples = struct.unpack_from("<II", data, self.at + 0x14)
        self.seconds = samples / rate


def assets(data):
    if data[:4] != b"BARS" or struct.unpack_from("<H", data, 0xa)[0] != 0x102:
        raise ValueError("not a BARS 1.2 archive")
    count = struct.unpack_from("<I", data, 0xc)[0]
    out = [Asset(data, i, count) for i in range(count)]
    for i, a in enumerate(out):
        if zlib.crc32(a.name.encode()) & 0xFFFFFFFF != struct.unpack_from("<I", data, 0x10 + 4 * i)[0]:
            raise ValueError("asset %d's name read as %r does not match its CRC" % (i, a.name))
    return out


def kinds_for(name, rules, other):
    rest = name[len(LINK):]
    for match, kinds in rules:
        if isinstance(match, str):
            if re.sub(r"_?\d+$", "", rest).endswith(match):
                return kinds
        elif rest.startswith(match):
            return kinds
    return other


def swap(link_bars, sources, stream, rules, other):
    """(Link's archive with the other voice, {stream file name: bytes}, [(Link's clip, the clip it now is)]); sources:
    [(archive bytes, what its clips' names start with, a prefix for their kinds)]; stream(name) reads
    Sound/Resource/Stream/<name>.bwav"""
    data = bytearray(link_bars)
    link = assets(data)
    clips = {}
    for bars, strip, prefix in sources:
        found = assets(bars)
        ends = sorted({g.at for g in found}) + [len(bars)]
        if not any(g.name.startswith(strip) for g in found):
            raise ValueError("no clip's name starts with %s" % strip)
        for g in found:
            if not g.name.startswith(strip):   # (an enemy's archive holds other sounds too: the Lizalfos's)
                continue
            g.kind = prefix + re.sub(r"\d+$", "", g.name[len(strip):]).strip()   # (some of its names have a space there)
            if g.channels != 1:
                raise ValueError("%s has %d channels" % (g.name, g.channels))
            if g.prefetch:
                g.whole = stream(g.name)
                if struct.unpack_from("<I", g.whole, 8)[0] != g.crc:
                    raise ValueError("%s: its stream file is another clip's" % g.name)
                g.start = bytes(bars[g.at:g.at + PREFETCH])
            else:   # (held whole in its archive: as it is, if it fits where a start does)
                g.whole = None
                g.start = bytes(bars[g.at:ends[ends.index(g.at) + 1]])
                if len(g.start) > PREFETCH:
                    continue
            g.loudness = bytes(bars[g.amta + 0x38:g.amta + 0x48])
            clips.setdefault(g.kind, []).append(g)

    def pick(a, among=None):
        pool = [g for k in kinds_for(a.name, rules, other) for g in clips.get(k, []) if among is None or g.name in among]
        if not pool:
            pool = [g for gs in clips.values() for g in gs if among is None or g.name in among]
        pool.sort(key=lambda g: (abs(g.seconds - a.seconds), g.name))
        near = pool[:3]   # (the three nearest in length: which, by the clip's name, so the same clip always gets the same)
        return near[zlib.crc32(a.name.encode()) % len(near)]

    voice = [a for a in link if a.name.startswith(LINK)]
    offsets = sorted({a.at for a in link}) + [len(data)]
    room = {offsets[i]: offsets[i + 1] - offsets[i] for i in range(len(offsets) - 1)}
    others = {a.at for a in link if not a.name.startswith(LINK)}
    placed, streams, done = {}, {}, []   # placed: a clip -> an offset in Link's archive holding its start (or all of it)

    def use(a, g):
        struct.pack_into("<I", data, a.amta + 0x2c, a.type | 1 if g.whole else a.type & ~1)
        data[a.amta + 0x38:a.amta + 0x48] = g.loudness
        if g.whole:
            streams[a.name] = g.whole
        done.append((a.name, g.name))

    at_of = {}
    for a in voice:
        at_of.setdefault(a.at, []).append(a)
    for at in sorted(at_of):
        group = at_of[at]
        if not group[0].prefetch:
            continue
        if at in others or room[at] < PREFETCH:
            raise ValueError("%s: its start cannot be overwritten (%d bytes)" % (group[0].name, room[at]))
        g = pick(group[0])
        data[at:at + len(g.start)] = g.start
        placed.setdefault(g.name, at)
        for a in group:   # (assets sharing the audio: the same clip)
            use(a, g)
    for at in sorted(at_of):
        group = at_of[at]
        if group[0].prefetch:
            continue
        if any(a.type & 1 for a in group):
            raise ValueError("%s is whole in the archive but typed as streamed" % group[0].name)
        g = pick(group[0], among=set(placed))
        for a in group:
            struct.pack_into("<I", data, a.entry + 4, placed[g.name])
            use(a, g)
    if len(done) != len(voice) or len(data) != len(link_bars):
        raise ValueError("%d of %d clips replaced" % (len(done), len(voice)))
    # read back: every voice asset is a streamed clip whose start and stream file are the same clip, or a whole one
    for a in assets(data):
        if a.name.startswith(LINK):
            if a.name in streams:
                good = a.prefetch and a.type & 1 and struct.unpack_from("<I", streams[a.name], 8)[0] == a.crc
            else:
                good = not a.prefetch and not a.type & 1
            if not good:
                raise ValueError("%s does not read back as the clip it was given" % a.name)
    return bytes(data), streams, done
