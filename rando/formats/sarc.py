"""SARC archives (little endian, as the game's .pack files): read into {name: bytes}, write back."""
import struct

HASH_KEY = 0x65


def name_hash(name, key=HASH_KEY):
    h = 0
    for b in name.encode("utf-8"):
        h = (h * key + b) & 0xFFFFFFFF
    return h


def read(data):
    if data[:4] != b"SARC":
        raise ValueError("not a SARC archive")
    header_size, bom = struct.unpack_from("<HH", data, 4)
    if bom != 0xFEFF:
        raise ValueError("big-endian SARC is not supported")
    data_offset = struct.unpack_from("<I", data, 12)[0]
    sfat = header_size
    if data[sfat:sfat + 4] != b"SFAT":
        raise ValueError("SFAT section missing")
    sfat_size, count, key = struct.unpack_from("<HHI", data, sfat + 4)
    nodes = []
    for i in range(count):
        nodes.append(struct.unpack_from("<IIII", data, sfat + sfat_size + i * 16))
    sfnt = sfat + sfat_size + count * 16
    if data[sfnt:sfnt + 4] != b"SFNT":
        raise ValueError("SFNT section missing")
    names_at = sfnt + struct.unpack_from("<H", data, sfnt + 4)[0]
    files = {}
    for _hash, attrs, start, end in nodes:
        if not attrs >> 24:
            raise ValueError("SARC entry without a name")
        at = names_at + (attrs & 0xFFFF) * 4
        name = data[at:data.index(b"\0", at)].decode("utf-8")
        files[name] = bytes(data[data_offset + start:data_offset + end])
    return files


def _align(n, a):
    return (n + a - 1) & ~(a - 1)


def write(files, alignment=8):
    """files: {name: bytes}. Entries sorted by name hash, as the game's archives are."""
    entries = sorted(files.items(), key=lambda kv: name_hash(kv[0]))
    names = bytearray()
    name_offsets = []
    for name, _ in entries:
        name_offsets.append(len(names) // 4)
        names += name.encode("utf-8") + b"\0"
        names += b"\0" * (_align(len(names), 4) - len(names))
    blobs = bytearray()
    ranges = []
    for _, blob in entries:
        start = _align(len(blobs), alignment)
        blobs += b"\0" * (start - len(blobs))
        blobs += blob
        ranges.append((start, start + len(blob)))
    sfat = struct.pack("<4sHHI", b"SFAT", 0xC, len(entries), HASH_KEY)
    for (name, _), off, (start, end) in zip(entries, name_offsets, ranges):
        sfat += struct.pack("<IIII", name_hash(name), 0x01000000 | off, start, end)
    sfnt = struct.pack("<4sHH", b"SFNT", 8, 0) + bytes(names)
    head_len = 0x14 + len(sfat) + len(sfnt)
    data_offset = _align(head_len, max(alignment, 0x10))
    total = data_offset + len(blobs)
    header = struct.pack("<4sHHIIHH", b"SARC", 0x14, 0xFEFF, total, data_offset, 0x100, 0)
    return header + sfat + sfnt + b"\0" * (data_offset - head_len) + bytes(blobs)
