"""Builds the Windows app: dist/LostWoods.exe, one file, nothing to install.

    python -m pip install pyinstaller zstandard ainb==0.2.17 texture2ddecoder
    python tools/build_exe.py

Also makes dist/LostWoods-<version>.zip (the exe and README.md), the file to publish. 
The exe holds the code (rando/), its tables (data/) and the verifier (tools/verify_mod.py); it reads the player's own copy
of the game as gui.py does. No game file goes in it."""
import math
import os
import shutil
import struct
import subprocess
import sys
import zipfile
import zlib

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from rando.gui import BRAND, VERSION   # noqa: E402

NAME = "LostWoods"
BUILD = os.path.join(HERE, "build")
DIST = os.path.join(HERE, "dist")
GOLD, NIGHT, HALO = (0xe6, 0xb8, 0x4a), (0x0b, 0x12, 0x20), (0x1b, 0x2f, 0x55)


def icon_pixels(n):
    """an n x n RGBA image: the window header's gold Triforce on a rounded night-blue tile (4x supersampled)"""
    ss = 4
    out = bytearray()
    side = 0.80 * n
    h = side * math.sqrt(3) / 2
    top = (n - h) / 2 + 0.02 * n
    left = (n - side) / 2
    radius = 0.18 * n

    def in_tri(x, y, ax, ay, s):   # (upward triangle, apex (ax, ay), side s)
        th = s * math.sqrt(3) / 2
        if y < ay or y > ay + th:
            return False
        half = (y - ay) / math.sqrt(3)
        return ax - half <= x <= ax + half

    def in_triforce(x, y):
        s = side / 2
        cx = left + side / 2
        return (in_tri(x, y, cx, top, s) or in_tri(x, y, cx - s / 2, top + h / 2, s) or
                in_tri(x, y, cx + s / 2, top + h / 2, s))

    def in_tile(x, y):
        dx = max(radius - x, 0, x - (n - radius))
        dy = max(radius - y, 0, y - (n - radius))
        return dx * dx + dy * dy <= radius * radius

    for py in range(n):
        for px_ in range(n):
            gold = tile = 0
            for sy in range(ss):
                for sx in range(ss):
                    x, y = px_ + (sx + 0.5) / ss, py + (sy + 0.5) / ss
                    if in_tile(x, y):
                        tile += 1
                        gold += in_triforce(x, y)
            total = ss * ss
            if not tile:
                out += b"\0\0\0\0"
                continue
            t = py / n   # (the header's gradient, top to bottom)
            bg = [int(HALO[i] * (1 - t) + NIGHT[i] * t) for i in range(3)]
            f = gold / tile
            rgb = [int(bg[i] * (1 - f) + GOLD[i] * f) for i in range(3)]
            out += bytes(rgb + [int(255 * tile / total)])
    return bytes(out)


def png(n, rgba):
    raw = b"".join(b"\0" + rgba[y * n * 4:(y + 1) * n * 4] for y in range(n))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 6, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def make_icon(path):
    sizes = (256, 64, 48, 32, 16)
    images = [png(n, icon_pixels(n)) for n in sizes]
    head = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    entries = b""
    for n, data in zip(sizes, images):
        entries += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    with open(path, "wb") as f:
        f.write(head + entries + b"".join(images))


def version_file(path):
    parts = [int(p) for p in VERSION.split(".")] + [0] * 4
    v = tuple(parts[:4])
    text = """VSVersionInfo(
  ffi=FixedFileInfo(filevers=%(v)r, prodvers=%(v)r, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0,
                    date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('FileDescription', '%(brand)s - Ocarina of Time (Switch 2 remake) randomizer'),
      StringStruct('FileVersion', '%(ver)s'),
      StringStruct('InternalName', '%(name)s'),
      StringStruct('OriginalFilename', '%(name)s.exe'),
      StringStruct('ProductName', '%(brand)s'),
      StringStruct('ProductVersion', '%(ver)s')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""" % {"v": v, "brand": BRAND, "ver": VERSION, "name": NAME}
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    os.makedirs(BUILD, exist_ok=True)
    icon = os.path.join(HERE, "rando", "icon.ico")
    make_icon(icon)
    version = os.path.join(BUILD, "version.txt")
    version_file(version)
    sep = os.pathsep
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
           "--name", NAME, "--icon", icon, "--version-file", version,
           "--workpath", os.path.join(BUILD, "pyinstaller"), "--specpath", BUILD, "--distpath", DIST,
           "--add-data", os.path.join(HERE, "data") + sep + "data",
           "--add-data", os.path.join(HERE, "tools", "verify_mod.py") + sep + "tools",
           "--add-data", icon + sep + "rando",
           "--collect-submodules", "rando",
           "--collect-all", "ainb",
           "--hidden-import", "texture2ddecoder",
           "--hidden-import", "zstandard",
           os.path.join(HERE, "gui.py")]
    print(" ".join(cmd))
    subprocess.run(cmd, check=True, cwd=HERE)
    exe = os.path.join(DIST, NAME + ".exe")
    shutil.copy(os.path.join(HERE, "README.md"), os.path.join(DIST, "README.md"))
    print("built %s (%.1f MB)" % (exe, os.path.getsize(exe) / 1e6))
    package = os.path.join(DIST, "%s-%s.zip" % (NAME, VERSION))
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(exe, NAME + ".exe")
        z.write(os.path.join(HERE, "README.md"), "README.md")
    print("release %s (%.1f MB)" % (package, os.path.getsize(package) / 1e6))


if __name__ == "__main__":
    main()
