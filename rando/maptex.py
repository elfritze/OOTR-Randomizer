"""The game's own maps (the pause menu's: UI/CustomTex/Map/Field/<Area>_<Age>_00 and Dungeon/<Dungeon>_<Floor>_Main) as
images the tracker draws, decoded on this PC from the player's copy and cached as PNG in %APPDATA%/HookshotRando/maps (never
shipped), and where the world is on them.

Where the world is: Game/MapCaptureInfo holds the camera the maps were captured with, one entry per entry of
Game/MapMenuInfo, in the same order (anchors: entry 0 has Kokiri's Dm_Kokiri_0145, 6 the Gerudo token, 11 the royal tomb's
flag, 16 Lake Hylia's water after the Water Temple, 30 Ganon's tower falling). A texture is centred on the camera's X/Z and
spans its Height in world units across its width (north up: x to the right, z down). Checked by drawing landmarks on the
maps (Kakariko's well, windmill, houses and gates; Kokiri's houses; Lake Hylia's lab; the ranch; Dodongo's Cavern's chests).
Dungeon floors are MapParam's Floor list (TransY, from MinFloor: B2, B1, 1F, 2F...).

The textures are ASTC in Tegra block-linear layout: the layout is undone here (the swizzle as the OotrR randomizer's
tracker/icon_extract.py works it out, MIT), the ASTC blocks are decoded by the texture2ddecoder package (python -m pip install
texture2ddecoder); without it Sheet.image raises ImportError and the tracker draws the area from its placed objects."""
import os
import struct

from . import tracker
from .formats import byml, zs

ASTC = {0x2D: (4, 4), 0x2E: (5, 4), 0x2F: (5, 5), 0x30: (6, 5), 0x31: (6, 6), 0x32: (8, 5), 0x33: (8, 6), 0x34: (8, 8)}
MAP_DIR = ("UI", "CustomTex", "Map")


def parse_bntx(data):
    """(width, height, format, block height log2, image bytes) of a BNTX's first texture"""
    if data[:4] != b"BNTX":
        raise ValueError("not a BNTX")
    at = data.find(b"BRTI")
    if at < 0:
        raise ValueError("no texture")
    tile_mode = struct.unpack_from("<H", data, at + 0x12)[0]
    fmt = struct.unpack_from("<I", data, at + 0x1C)[0]
    width, height = struct.unpack_from("<II", data, at + 0x24)
    layout = struct.unpack_from("<I", data, at + 0x34)[0]
    size = struct.unpack_from("<I", data, at + 0x50)[0]
    mips = struct.unpack_from("<Q", data, at + 0x70)[0]
    start = struct.unpack_from("<Q", data, mips)[0]
    if tile_mode != 0:
        raise ValueError("linear textures are not handled")
    return width, height, fmt >> 8, layout & 7, data[start:start + size]


def deblock(raw, wb, hb, bh_log2, bpe=16):
    """Tegra block-linear -> rows of 16-byte ASTC blocks (GOB: 64 bytes x 8 rows; 2**bh_log2 GOBs stacked)"""
    gob_h = 1 << bh_log2
    width_gobs = -(-wb * bpe // 64)
    out = bytearray(wb * hb * bpe)
    stride = wb * bpe
    for y in range(hb):
        row = (y // (8 * gob_h)) * 512 * gob_h * width_gobs + ((y % (8 * gob_h)) // 8) * 512
        yin = (y & 1) * 16 + ((y >> 1) & 1) * 32 + ((y >> 2) & 1) * 128
        for x in range(wb):
            a = row + (x // 4) * 512 * gob_h + yin + (x & 1) * 64 + ((x >> 1) & 1) * 256
            out[y * stride + x * bpe:y * stride + (x + 1) * bpe] = raw[a:a + bpe]
    return bytes(out)


def png_path(rel):
    """the cached PNG of a texture ("Field/KakarikoVillage_Child_00", "Dungeon/DodongoCavern_1F_Main")"""
    kind, name = rel.split("/")
    return os.path.join(tracker.APPDATA, "maps", name + ".png" if kind == "Field" else "%s_%s.png" % (kind, name))


def texture_file(romfs, rel):
    kind, name = rel.split("/")
    return os.path.join(romfs, *MAP_DIR, kind, name + ".bntx.zs")


def decode_to_png(romfs, rel):
    import texture2ddecoder   # (optional: ImportError when it is not installed)
    from PIL import Image
    data = zs.Codec(romfs).read(texture_file(romfs, rel))
    w, h, fmt, bh, raw = parse_bntx(data)
    if fmt not in ASTC:
        raise ValueError("texture format %#x not handled" % fmt)
    bw, bhk = ASTC[fmt]
    pixels = texture2ddecoder.decode_astc(deblock(raw, -(-w // bw), -(-h // bhk), bh), w, h, bw, bhk)
    img = Image.frombytes("RGBA", (w, h), pixels, "raw", "BGRA")
    path = png_path(rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path + ".part", "PNG")
    os.replace(path + ".part", path)
    return path


class Sheet:
    """one map texture and where the world is on it"""

    def __init__(self, romfs, rel, cx, cz, span, name=None, y=None):
        self.romfs, self.rel, self.cx, self.cz, self.span = romfs, rel, cx, cz, span
        self.name, self.y = name, y
        self._image = None

    def exists(self):
        return os.path.isfile(texture_file(self.romfs, self.rel))

    def cached(self):
        return self._image is not None or os.path.isfile(png_path(self.rel))

    def image(self):
        """the AreaImage (decoding it the first time: seconds; ImportError without texture2ddecoder)"""
        if self._image is None:
            path = png_path(self.rel)
            if not os.path.isfile(path):
                path = decode_to_png(self.romfs, self.rel)
            self._image = AreaImage(path)
        return self._image

    def to_tex(self, x, z):
        """world X/Z -> the texture's pixels"""
        w, h = self._image.size if self._image else (2000, 1440)
        s = w / self.span
        return w / 2 + (x - self.cx) * s, h / 2 + (z - self.cz) * s

    def on_map(self, x, z):
        """whether the world point falls on the drawn map (not on its transparent margin)"""
        u, v = self.to_tex(x, z)
        return self.image().opaque(u, v)


class AreaImage:
    """a map image that the tracker crops and scales to its canvas"""

    def __init__(self, path):
        from PIL import Image
        self.image = Image.open(path).convert("RGBA")
        self.size = self.image.size
        self.alpha = self.image.getchannel("A")
        self.bbox = self.alpha.getbbox() or (0, 0) + self.size
        self._small = self.alpha.resize((self.size[0] // 4, self.size[1] // 4))
        self._cache = {}

    def opaque(self, u, v, radius=6):
        """some map under this pixel (or within a few pixels: a chest at a room's edge)"""
        w, h = self._small.size
        for du in (0, -radius, radius):
            for dv in (0, -radius, radius):
                i, j = int((u + du) / 4), int((v + dv) / 4)
                if 0 <= i < w and 0 <= j < h and self._small.getpixel((i, j)) > 40:
                    return True
        return False

    def scaled(self, box, w, h):
        """the image's box (left, top, right, bottom in pixels) as a Tk image of w x h"""
        from PIL import Image, ImageTk
        box = tuple(int(round(v)) for v in box)
        key = (box, max(1, int(w)), max(1, int(h)))
        if key not in self._cache:
            crop = self.image.crop(box).resize(key[1:], Image.LANCZOS)
            self._cache = {key: ImageTk.PhotoImage(crop)}
        return self._cache[key]


def _floor_name(level):
    return "B%d" % -level if level < 0 else "%dF" % (level + 1)


def geometry(romfs):
    """{"fields": {area: {"Child": Sheet, "Adult": Sheet}}, "dungeons": {area: [Sheet per floor, lowest first]}}"""
    root = os.path.join(romfs, "Game")
    menu = byml.read(open(os.path.join(root, "MapMenuInfo", "MapMenuInfo.game__ui__MapMenuInfo.bgyml"), "rb").read())[0]
    cap = byml.read(open(os.path.join(root, "MapCaptureInfo", "MapCaptureInfo.game__MapCaptureInfo.bgyml"), "rb").read())[0]
    param = byml.read(zs.Codec(romfs).read(os.path.join(romfs, "Banc", "BancBasedResource", "MapParam.byml.zs")))[0]
    menu, cap = menu["MapMenuParamArray"], cap["MapCaptureParamArray"]
    fields, dungeons = {}, {}
    for i, m in enumerate(menu):
        if i >= len(cap) or "CameraPos" not in cap[i] or not cap[i].get("Height"):
            continue
        e, loc = cap[i], m.get("LocationName")
        cx, cz, span = e["CameraPos"]["X"], e["CameraPos"]["Z"], e["Height"]
        if e.get("IsDungeon"):
            p = param.get(loc) or {}
            floors = []
            for n, f in enumerate(p.get("Floor", [])):
                name = _floor_name(p.get("MinFloor", 0) + n)
                for tex in ("%s_%s_Main" % (loc, name), "%s_%s_State00_Main" % (loc, name)):
                    sheet = Sheet(romfs, "Dungeon/" + tex, cx, cz, span, name=name, y=f.get("TransY", 0))
                    if sheet.exists():
                        floors.append(sheet)
                        break
            if floors:
                dungeons[loc] = floors
        else:
            ages = {}
            for age, tex in zip(("Child", "Adult"), m.get("TextureName", [])):
                if tex:
                    sheet = Sheet(romfs, "Field/" + tex, cx, cz, span, name=age)
                    if sheet.exists():
                        ages[age] = sheet
            if ages:
                fields[loc] = ages
    return {"fields": fields, "dungeons": dungeons}


def floor_of(floors, x, y, z):
    """the floor a dungeon point is on: the highest floor at or below it (3 units of slack) whose map is drawn under it"""
    if y is None:
        return None
    below = [f for f in floors if y >= f.y - 3] or floors[:1]
    for f in sorted(below, key=lambda f: -f.y):
        try:
            if f.on_map(x, z):
                return f
        except Exception:
            break
    return max(below, key=lambda f: f.y)
