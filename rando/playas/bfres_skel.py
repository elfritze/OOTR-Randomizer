"""The skeleton of a BFRES model (Switch, version 10.4, as the remake's Model/*.bfres): bones and inverse bind matrices,
read and rewritten in place (same size: nothing moves in the file).

FSKL (at the FMDL's skeleton offset; found here by its magic, one model per file):
  +0x00 "FSKL", u32 flags (0x1000: rotations are XYZ Euler angles)
  +0x08 u64 bone dictionary, +0x10 u64 bone array, +0x18 u64 matrix-to-bone list (u16 per matrix: the smooth ones, then
  the rigid ones), +0x20 u64 inverse bind matrices (3x4 floats, row major, one per smooth matrix)
  +0x38 u16 bones, u16 smooth matrices, u16 rigid matrices
bone (0x58): +0x00 u64 name (u16 length, chars), +0x20 u16 index, u16 parent (0xffff: none), s16 smooth matrix, s16 rigid
matrix, +0x30 scale (3 floats), +0x3c rotation (4 floats: X, Y, Z Euler, then 1), +0x4c translation (3 floats)
"""
import math
import struct

BONE_SIZE = 0x58


class Bone:
    def __init__(self, at, name, index, parent, smooth, rigid, scale, rot, trans):
        self.at, self.name, self.index, self.parent = at, name, index, parent
        self.smooth, self.rigid = smooth, rigid
        self.scale, self.rot, self.trans = scale, rot, trans

    def local(self):
        return compose(self.scale, self.rot, self.trans)


def mul(a, b):
    """4x4 matrices (lists of 4 rows) multiplied"""
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def eye():
    return [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]


def inv(m):
    """an affine 4x4 matrix inverted (3x3 part by its adjugate, then the translation)"""
    a = [row[:3] for row in m[:3]]
    det = (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1]) - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
           + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    if abs(det) < 1e-12:
        raise ValueError("a singular matrix")
    c = [[(a[(j + 1) % 3][(i + 1) % 3] * a[(j + 2) % 3][(i + 2) % 3] - a[(j + 1) % 3][(i + 2) % 3] * a[(j + 2) % 3][(i + 1) % 3]) / det
          for j in range(3)] for i in range(3)]
    t = [-sum(c[i][k] * m[k][3] for k in range(3)) for i in range(3)]
    return [c[0] + [t[0]], c[1] + [t[1]], c[2] + [t[2]], [0.0, 0.0, 0.0, 1.0]]


def max_diff(a, b):
    return max(abs(a[i][j] - b[i][j]) for i in range(4) for j in range(4))


def euler_matrix(x, y, z):
    """XYZ Euler angles (radians): X applied first, then Y, then Z (column vectors: Rz @ Ry @ Rx)"""
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    # Rz @ Ry @ Rx, written out
    return [[cy * cz, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
            [cy * sz, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx],
            [-sy, cy * sx, cy * cx]]


def matrix_euler(r):
    """the XYZ Euler angles of a rotation matrix (inverse of euler_matrix)"""
    sy = -r[2][0]
    sy = max(-1.0, min(1.0, sy))
    y = math.asin(sy)
    if abs(sy) < 0.999999:
        x = math.atan2(r[2][1], r[2][2])
        z = math.atan2(r[1][0], r[0][0])
    else:   # (gimbal lock: Z folded into X)
        x = math.atan2(-r[1][2], r[1][1])
        z = 0.0
    return x, y, z


def compose(scale, rot, trans):
    r = euler_matrix(*rot[:3])
    return [[r[i][0] * scale[0], r[i][1] * scale[1], r[i][2] * scale[2], trans[i]] for i in range(3)] + [[0.0, 0.0, 0.0, 1.0]]


class Skeleton:
    def __init__(self, data):
        self.data = bytearray(data)
        d = self.data
        at = d.find(b"FSKL")
        if at < 0 or d.find(b"FSKL", at + 4) >= 0:
            raise ValueError("not one skeleton")
        self.at = at
        self.flags = struct.unpack_from("<I", d, at + 4)[0]
        if not self.flags & 0x1000:
            raise ValueError("the rotations are not Euler angles (flags %#x)" % self.flags)
        _, self.bones_at, self.list_at, self.inv_at = struct.unpack_from("<4Q", d, at + 8)
        self.n_bones, self.n_smooth, self.n_rigid = struct.unpack_from("<3H", d, at + 0x38)
        self.bones = []
        for i in range(self.n_bones):
            b = self.bones_at + BONE_SIZE * i
            name_at = struct.unpack_from("<Q", d, b)[0]
            n = struct.unpack_from("<H", d, name_at)[0]
            name = bytes(d[name_at + 2:name_at + 2 + n]).decode("utf-8")
            index, parent, smooth, rigid = struct.unpack_from("<HHhh", d, b + 0x20)
            if index != i:
                raise ValueError("bone %d says it is %d" % (i, index))
            scale = struct.unpack_from("<3f", d, b + 0x30)
            rot = struct.unpack_from("<4f", d, b + 0x3c)
            trans = struct.unpack_from("<3f", d, b + 0x4c)
            self.bones.append(Bone(b, name, i, None if parent == 0xFFFF else parent, smooth, rigid, scale, rot, trans))
        for b in self.bones:
            if b.parent is not None and b.parent >= b.index:
                raise ValueError("bone %s comes before its parent" % b.name)
        self.by_name = {b.name: b for b in self.bones}
        self.matrix_bone = list(struct.unpack_from("<%dH" % (self.n_smooth + self.n_rigid), d, self.list_at))

    def worlds(self, local_of=None):
        """each bone's model-space matrix at rest: local_of(bone) -> 4x4 (default: the bone's own)"""
        out = []
        for b in self.bones:
            m = local_of(b) if local_of else b.local()
            out.append(m if b.parent is None else mul(out[b.parent], m))
        return out

    def inverse(self, i):
        f = struct.unpack_from("<12f", self.data, self.inv_at + 48 * i)
        return [list(f[0:4]), list(f[4:8]), list(f[8:12]), [0.0, 0.0, 0.0, 1.0]]

    def set_inverse(self, i, m):
        struct.pack_into("<12f", self.data, self.inv_at + 48 * i, *(m[0] + m[1] + m[2]))

    def set_trans(self, bone, t):
        """a bone's rest translation (a zero one must stay zero: its hint is not touched)"""
        if all(abs(x) < 1e-9 for x in bone.trans) != all(abs(x) < 1e-9 for x in t):
            raise ValueError("%s: a translation to or from zero" % bone.name)
        struct.pack_into("<3f", self.data, bone.at + 0x4c, *t)
        bone.trans = tuple(t)

    def set_local(self, bone, m, scale=None):
        """a bone's rest transform from a 4x4 matrix: rotation and translation, and the scale given (the bone's own kept
        when none: the matrix's columns are divided by it)"""
        if scale is not None:
            struct.pack_into("<3f", self.data, bone.at + 0x30, *scale)
            bone.scale = tuple(scale)
        r = [[m[i][j] / bone.scale[j] for j in range(3)] for i in range(3)]
        x, y, z = matrix_euler(r)
        t = (m[0][3], m[1][3], m[2][3])
        # the bone's hints (flags bits 24-27: scale uniform, scale of volume one, rotation zero, translation zero): the game
        # skips what a hint says is identity, so they are cleared, but "uniform" for a uniform scale
        flags = struct.unpack_from("<I", self.data, bone.at + 0x2c)[0] & ~0x0F000000
        sx, sy, sz = bone.scale
        if abs(sx - sy) < 1e-6 and abs(sx - sz) < 1e-6:
            flags |= 0x01000000
            if abs(sx - 1.0) < 1e-6:
                flags |= 0x02000000
        struct.pack_into("<I", self.data, bone.at + 0x2c, flags)
        struct.pack_into("<3f", self.data, bone.at + 0x3c, x, y, z)
        struct.pack_into("<3f", self.data, bone.at + 0x4c, *t)
        bone.rot = (x, y, z, bone.rot[3])
        bone.trans = t
