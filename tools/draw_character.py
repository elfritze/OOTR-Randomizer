"""A character of the Character page drawn without the game: the model as it stands in its own rest, and as it is worn
(the built mod's model, posed as the game poses it when Link stands still: the bones Link has take his rotation and
translation), each from the front and from the side, as clouds of its vertices, with Link's joints as red dots and the
ground as a line. What it shows: a head facing the sky, a limb wrung, a mesh left behind, feet under the ground; not how
it moves, nor its cloth (the bones a cloth sets are drawn where the model's rest has them).

    python tools/draw_character.py <game folder> <character> <out.png> [--half=1.1] [--lo=-0.15] [--hi=2.05] [--size=520]

(--half: metres from the middle to each side; --lo, --hi: the heights drawn; a head: --half=0.3 --lo=1.25 --hi=1.85)"""
import os
import shutil
import struct
import sys
import tempfile
import zlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rando import playas                                       # noqa: E402
from rando.formats import zs                                   # noqa: E402
from rando.playas.bfres_skel import Skeleton, compose          # noqa: E402
from rando.playas.retarget import shapes                       # noqa: E402

COMP = {0x02: ("B", 1), 0x09: ("B", 2), 0x0b: ("B", 4), 0x0a: ("H", 1), 0x12: ("H", 2), 0x15: ("H", 4)}
JOINTS = ["Head", "Neck", "Spine_1", "Spine_2", "Waist", "Arm_1_L", "Arm_2_L", "Wrist_L", "Arm_1_R", "Arm_2_R", "Wrist_R",
          "Leg_1_L", "Leg_2_L", "Ankle_L", "Leg_1_R", "Leg_2_R", "Ankle_R", "Toe_L", "Toe_R"]


def vertices(d, g, W, step=1):
    """[(x, y, z)] of every shape's vertices in the pose W (bone world matrices)"""
    pool = struct.unpack_from("<Q", d, 0xb0)[0]
    base = struct.unpack_from("<Q", d, pool + 8)[0]
    # each matrix's skinning matrix: W[bone] @ inverse bind (smooth), W[bone] (rigid)
    M = []
    for i, b in enumerate(g.matrix_bone):
        if i < g.n_smooth:
            inv = g.inverse(i)
            w = W[b]
            M.append([[sum(w[a][k] * inv[k][j] for k in range(3)) + (w[a][3] if j == 3 else 0.0) for j in range(4)]
                      for a in range(3)])
        else:
            M.append([row[:] for row in W[b][:3]])
    out, done = [], set()
    for at, skin, lst, n in shapes(d):
        v = struct.unpack_from("<Q", d, at + 0x10)[0]
        if v in done:
            continue
        done.add(v)
        attrs, strides = struct.unpack_from("<Q", d, v + 0x08)[0], struct.unpack_from("<Q", d, v + 0x38)[0]
        offset, n_attr, n_buf = struct.unpack_from("<IBB", d, v + 0x48)
        n_vert = struct.unpack_from("<I", d, v + 0x50)[0]
        stride = struct.unpack_from("<I", d, strides)[0]
        found = {}
        for a in range(n_attr):
            e = attrs + 0x10 * a
            p = struct.unpack_from("<Q", d, e)[0]
            name = bytes(d[p + 2:p + 2 + struct.unpack_from("<H", d, p)[0]]).decode()
            found[name] = (struct.unpack_from("<I", d, e + 8)[0], struct.unpack_from("<H", d, e + 0xc)[0])
        first = base + offset
        if skin == 0:
            bone = struct.unpack_from("<H", d, at + 0x52)[0]   # (not seen in these models)
            raise ValueError("an unskinned shape (bone %d)" % bone)
        idx = [(COMP[found[k][0] >> 8], found[k][1]) for k in ("_i0", "_i1") if k in found]
        wts = [(COMP[found[k][0] >> 8], found[k][1]) for k in ("_w0", "_w1") if k in found]
        p_off = found["_p0"][1]
        for i in range(0, n_vert, step):
            a0 = first + i * stride
            p = struct.unpack_from("<3f", d, a0 + p_off)
            ii = [x for (ch, n), off in idx for x in struct.unpack_from("<%d%s" % (n, ch), d, a0 + off)]
            if skin == 1:
                pairs = [(ii[0], 1.0)]
            else:
                ww = [x / 255.0 for (ch, n), off in wts for x in struct.unpack_from("<%d%s" % (n, ch), d, a0 + off)]
                if not ww:
                    ww = [1.0]
                pairs = [(ii[j], ww[j]) for j in range(min(len(ii), len(ww), skin)) if ww[j] > 0]
                total = sum(w for _, w in pairs) or 1.0
                pairs = [(j, w / total) for j, w in pairs]
            x = y = z = 0.0
            for j, w in pairs:
                m = M[j]
                x += w * (m[0][0] * p[0] + m[0][1] * p[1] + m[0][2] * p[2] + m[0][3])
                y += w * (m[1][0] * p[0] + m[1][1] * p[1] + m[1][2] * p[2] + m[1][3])
                z += w * (m[2][0] * p[0] + m[2][1] * p[1] + m[2][2] * p[2] + m[2][3])
            out.append((x, y, z))
    return out


def png(path, w, h, pix):
    raw = b"".join(b"\0" + bytes(pix[y * w * 3:(y + 1) * w * 3]) for y in range(h))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    open(path, "wb").write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) +
                           chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def draw(panels, path, size=520, lo=-0.15, hi=2.05, half=1.1):
    """panels: [(points, joints)] each drawn front (x, y) and side (z, y), metres: y lo..hi, x and z -half..half"""
    w, h = size * 2 * len(panels), int(size * (hi - lo) / (2 * half))
    pix = bytearray(b"\x14" * (w * h * 3))
    sc = size / (2 * half)
    for pi, (pts, joints) in enumerate(panels):
        for view in (0, 1):
            ox = (pi * 2 + view) * size
            depth = sorted(pts, key=lambda p: p[2] if view == 0 else -p[0])
            zs_ = [p[2] if view == 0 else -p[0] for p in depth]
            z0, z1 = (zs_[0], zs_[-1]) if zs_ else (0, 1)
            for p, zv in zip(depth, zs_):
                u = p[0] if view == 0 else p[2]
                px_, py_ = int(ox + size / 2 + u * sc), int(h - (p[1] - lo) * sc)
                if ox <= px_ < ox + size and 0 <= py_ < h:
                    s = int(70 + 170 * (zv - z0) / ((z1 - z0) or 1))
                    o = (py_ * w + px_) * 3
                    pix[o:o + 3] = bytes((s, s, min(255, s + 15)))
            gy = int(h - (0 - lo) * sc)   # (the ground)
            for xx in range(ox, ox + size):
                o = (gy * w + xx) * 3
                pix[o:o + 3] = b"\x40\x90\x40"
            for j in joints:
                u = j[0] if view == 0 else j[2]
                cx, cy = int(ox + size / 2 + u * sc), int(h - (j[1] - lo) * sc)
                for dx in range(-2, 3):
                    for dy in range(-2, 3):
                        if ox <= cx + dx < ox + size and 0 <= cy + dy < h:
                            o = ((cy + dy) * w + cx + dx) * 3
                            pix[o:o + 3] = b"\xff\x30\x30"
    png(path, w, h, pix)


def main():
    opts = dict(a[2:].split("=") for a in sys.argv[1:] if a.startswith("--"))
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 3 or args[1] not in playas.CHARACTERS:
        raise SystemExit(__doc__)
    game, who, out = args
    romfs = os.path.join(game, "romfs")
    codec = zs.Codec(romfs)
    C = playas.CHARACTERS[who]
    link = Skeleton(codec.read(os.path.join(romfs, "Model", "Player_Adult.Player_Adult.bfres.zs")))
    L = link.worlds()
    joints = [tuple(L[link.by_name[n].index][a][3] for a in range(3)) for n in JOINTS if n in link.by_name]
    own = codec.read(os.path.join(romfs, "Model", "%s.%s.bfres.zs" % (C.model, C.model)))
    g = Skeleton(own)
    step = 3 if len(own) > 6_000_000 else 1
    panels = [(vertices(own, g, g.worlds(), step), [])]
    work = tempfile.mkdtemp(prefix="playas-draw-")
    try:
        playas.build(game, who, os.path.join(work, C.mod), log=lambda line: None)
        built = os.path.join(work, C.mod, "romfs", "Model", "%s.%s.bfres.zs" % (C.mod, C.model))
        worn = codec.decompress(open(built, "rb").read(), os.path.basename(built))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    g = Skeleton(worn)
    pose = g.worlds(lambda b: compose(b.scale, link.by_name[b.name].rot, link.by_name[b.name].trans)
                    if b.name in link.by_name else b.local())
    panels.append((vertices(worn, g, pose, step), joints))
    draw(panels, out, size=int(opts.get("size", 520)), lo=float(opts.get("lo", -0.15)), hi=float(opts.get("hi", 2.05)),
         half=float(opts.get("half", 1.1)))
    print("%s: its own rest (left pair), worn (right pair, Link's joints in red): %s" % (C.who, out))


if __name__ == "__main__":
    main()
