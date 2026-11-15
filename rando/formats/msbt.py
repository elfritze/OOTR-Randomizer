"""The remake's message files (MSBT, "MsgStdBn"), as its Mals archives hold them: little-endian, UTF-8 text, two sections,
LBL1 (labels in a hash table: bucket count, then per bucket (label count, offset), then each label as a length byte, its
name and its text index) and TXT2 (text count, offsets, then each text NUL-terminated, with its control tags: 0x0E ...).
Sections are 16-aligned, padded with 0xAB. read() then write() gives the file back byte for byte (tools: checked on every
message file of the 16 languages).

    m = read(data)
    m.add("Rando_Gift", "Here, take this!")   # (a new label at the end of the texts)
    data = m.write()
"""
import struct

MAGIC = b"MsgStdBn"
PAD = b"\xab"
# (the colour tag: group 0, type 3, two bytes of colour index; 0xFFFF goes back to the box's own colour. 0 is the red the
# game's lines give names: Darunia's "That <Goron Bracelet> will allow ya...", Navi's "<Gohma>!")
COLOR_TAG = b"\x0e\x00\x00\x03\x00\x02\x00"
RED, COLOR_END = 0, 0xFFFF


def colored(text, color=RED):
    """text's bytes in a colour, then the box's own colour again"""
    return COLOR_TAG + struct.pack("<H", color) + text.encode("utf-8") + COLOR_TAG + struct.pack("<H", COLOR_END)


def label_hash(label, buckets):
    h = 0
    for ch in label.encode("utf-8"):
        h = (h * 0x492 + ch) & 0xFFFFFFFF
    return h % buckets


class Msbt:
    def __init__(self, header, labels, texts, buckets, bucket_order):
        self.header = header            # (the 0x20-byte header, its size field rewritten on write)
        self.labels = labels            # {label: text index}
        self.texts = texts              # [raw text bytes, NUL included]
        self.buckets = buckets
        self.bucket_order = bucket_order  # {bucket: [labels in file order]}

    def get(self, label):
        i = self.labels.get(label)
        return None if i is None else self.texts[i]

    def text(self, label):
        """a label's text without its control tags (0x0E group, type, size, then size bytes), or None"""
        raw = self.get(label)
        if raw is None:
            return None
        out, i = bytearray(), 0
        while i < len(raw):
            b = raw[i]
            if b == 0x0E:
                size = struct.unpack_from("<H", raw, i + 5)[0]
                i += 7 + size
            elif b == 0x0F:   # (a tag's end: group and type)
                i += 5
            elif b == 0:
                break
            else:
                out.append(b)
                i += 1
        return out.decode("utf-8", "replace")

    def add(self, label, text):
        """a new label: text plain (str, no tags) or the message's bytes (tags made with colored() etc.: their parameters
        hold zero bytes, the texts go by their offsets; the NUL ending it is added)"""
        if label in self.labels:
            raise ValueError("label %s already" % label)
        if isinstance(text, str):
            raw = text.encode("utf-8")
            if b"\x0e" in raw or b"\x0f" in raw or b"\0" in raw:
                raise ValueError("plain text only (bytes for tags)")
        else:
            raw = bytes(text)
        self.labels[label] = len(self.texts)
        self.texts.append(raw + b"\0")
        self.bucket_order.setdefault(label_hash(label, self.buckets), []).append(label)

    def write(self):
        lbl = bytearray(struct.pack("<I", self.buckets))
        table = bytearray()
        entries = 4 + 8 * self.buckets
        for b in range(self.buckets):
            names = self.bucket_order.get(b, [])
            lbl += struct.pack("<II", len(names), entries + len(table))
            for name in names:
                raw = name.encode("utf-8")
                table += bytes([len(raw)]) + raw + struct.pack("<I", self.labels[name])
        lbl += table
        txt = bytearray(struct.pack("<I", len(self.texts)))
        at = 4 + 4 * len(self.texts)
        for t in self.texts:
            txt += struct.pack("<I", at)
            at += len(t)
        for t in self.texts:
            txt += t
        out = bytearray(self.header)
        for magic, body in ((b"LBL1", lbl), (b"TXT2", txt)):
            out += magic + struct.pack("<I", len(body)) + b"\0" * 8 + body
            out += PAD * (-len(out) % 16)
        struct.pack_into("<I", out, 0x12, len(out))
        return bytes(out)


def read(data):
    if data[:8] != MAGIC or data[8:10] != b"\xff\xfe" or data[0xC] != 0:
        raise ValueError("not a little-endian UTF-8 MSBT")
    n = struct.unpack_from("<H", data, 0xE)[0]
    at, sections = 0x20, {}
    for _ in range(n):
        magic, size = data[at:at + 4], struct.unpack_from("<I", data, at + 4)[0]
        sections[magic] = data[at + 0x10:at + 0x10 + size]
        at = (at + 0x10 + size + 15) & ~15
    if set(sections) != {b"LBL1", b"TXT2"}:
        raise ValueError("MSBT sections %s" % sorted(sections))
    lbl, txt = sections[b"LBL1"], sections[b"TXT2"]
    buckets = struct.unpack_from("<I", lbl, 0)[0]
    labels, order = {}, {}
    for b in range(buckets):
        count, off = struct.unpack_from("<II", lbl, 4 + 8 * b)
        for _ in range(count):
            ln = lbl[off]
            name = lbl[off + 1:off + 1 + ln].decode("utf-8")
            labels[name] = struct.unpack_from("<I", lbl, off + 1 + ln)[0]
            order.setdefault(b, []).append(name)
            off += 1 + ln + 4
    count = struct.unpack_from("<I", txt, 0)[0]
    offs = list(struct.unpack_from("<%dI" % count, txt, 4)) + [len(txt)]
    texts = [bytes(txt[offs[i]:offs[i + 1]]) for i in range(count)]
    return Msbt(bytes(data[:0x20]), labels, texts, buckets, order)
