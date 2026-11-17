"""A character's model refitted to Link's skeleton, in place (the file keeps its size: only numbers and indices change).

Worn as a tunic, the model's bones Link also has take Link's local rotation and translation each frame (SameBoneModelBind,
RotTrans); the others keep their own, under their parent. Unchanged, that puts the character's mesh (Ganondorf's: 1.65
times Link's height, in a T pose) on Link's bone lengths: short, the head sunk in the shoulders. Here, at Link's rest
pose, the mesh is the character posed like Link (Link's rest rotations, its own bone lengths), scaled by K so that its
joints fall nearest Link's (within a few centimetres), and Link's motion moves it from there:

  smooth skinning   each smooth matrix's inverse bind = inv(H[b]) @ S @ GA[b] @ inv(G[b]), where G is the model's own rest
                    pose, GA its rest posed with Link's rotations, S the uniform scale K, and H the skeleton the game will
                    pose at Link's rest (Link's rotation and translation on the shared bones, the model's own elsewhere)
  rigid skinning    (vertices in a bone's own space: the eyes; Ganondorf's finger rings, headpiece, earrings, collar
                    jewels) the vertices themselves scaled by K (32-bit float positions, in the vertex buffer), and the
                    bone placed where S @ GA[b] puts its frame, unscaled: a cloth simulation sets some of these bones
                    (Ganondorf's earrings), and would drop a scale kept in a bone. A bone Link also has is set by Link's
                    (the eyeballs, fingers, the chest): its rigid mesh moves to a spare bone of the character's own (no
                    skin, no children, not in the cloth file), reparented and placed there (characters.py: which)
  its own bones     (a cape's, hair's, a skirt's...: the ones Link has not) keep their rotation, their offset from their
                    parent scaled by K: the skeleton at Link's rest is then the character's at K, as the cloth file scaled
                    by K (cloth_scale.py) expects of the bones it reads and writes
  held bones        (characters.py: held) a bone whose skin must not move as that bone does, held by another, its carrier:
                    a bone Link's cloth swings (his belt's, which Sheik has by name, hers elsewhere and still), or a rigid
                    mesh on a bone Link sets when the model has no spare bone for it (Sheik's eyes, her knife on the
                    waist). Its smooth matrix becomes the carrier's (the matrix's bone in the skeleton's list; its
                    inverse bind = inv(H[carrier]) @ S @ GA[b] @ inv(G[b])); its rigid matrix too, the vertices themselves
                    taken to the carrier's space (inv(H[carrier]) @ S @ GA[b]: positions, and normals and tangents where
                    that turns them). Held by nothing (None): a rigid mesh not worn at all, its vertices all put at
                    the bone's origin, where they draw nothing (Phantom Ganon's spear, in the hand of Link's shield)
"""
import struct

from .bfres_skel import Skeleton, compose, inv, max_diff, mul


def scaled(m, k):
    return [[k * m[i][j] for j in range(4)] if i < 3 else m[i][:] for i in range(4)]


def shapes(data):
    """[(shape at, vertex skin count, skin bone list at, count)]: FSHP blocks found by magic (0x60 each)"""
    out, i = [], 0
    while True:
        i = data.find(b"FSHP", i)
        if i < 0:
            return out
        lst = struct.unpack_from("<Q", data, i + 0x20)[0]
        n = struct.unpack_from("<H", data, i + 0x58)[0]
        out.append((i, data[i + 0x5a], lst, n))
        i += 4


def scale_rigid_vertices(d, k):
    """the positions of every rigid shape's vertices (in their bone's space) multiplied by k; how many vertices"""
    pool = struct.unpack_from("<Q", d, 0xb0)[0]          # (the file's buffer memory pool info: flags, size, data offset)
    base = struct.unpack_from("<Q", d, pool + 8)[0]
    done, count = set(), 0
    for at, skin, _lst, _n in shapes(d):
        if skin != 1:
            continue
        v = struct.unpack_from("<Q", d, at + 0x10)[0]
        if bytes(d[v:v + 4]) != b"FVTX":
            raise ValueError("no vertex buffer at %#x" % v)
        if v in done:
            continue
        done.add(v)
        attrs, strides = struct.unpack_from("<Q", d, v + 0x08)[0], struct.unpack_from("<Q", d, v + 0x38)[0]
        offset, n_attr, n_buf = struct.unpack_from("<IBB", d, v + 0x48)
        n_vert = struct.unpack_from("<I", d, v + 0x50)[0]
        if n_buf != 1:
            raise ValueError("a rigid shape with %d vertex buffers" % n_buf)
        stride = struct.unpack_from("<I", d, strides)[0]
        where = None
        for a in range(n_attr):
            e = attrs + 0x10 * a
            name_at = struct.unpack_from("<Q", d, e)[0]
            name = bytes(d[name_at + 2:name_at + 2 + struct.unpack_from("<H", d, name_at)[0]])
            if name == b"_p0":
                fmt, off = struct.unpack_from("<IH", d, e + 8)[0], struct.unpack_from("<H", d, e + 0xc)[0]
                if fmt != 0x1805:   # (three 32-bit floats)
                    raise ValueError("positions in format %#x" % fmt)
                where = off
        if where is None:
            raise ValueError("a rigid shape without positions")
        for i in range(n_vert):
            p = base + offset + i * stride + where
            x, y, z = struct.unpack_from("<3f", d, p)
            struct.pack_into("<3f", d, p, x * k, y * k, z * k)
        count += n_vert
    return count


def rigid_buffers(d):
    """[(first vertex at, stride, vertices, {attribute: (format, offset)})] of the rigid shapes' vertex buffers, once each"""
    pool = struct.unpack_from("<Q", d, 0xb0)[0]
    base = struct.unpack_from("<Q", d, pool + 8)[0]
    out, done = [], set()
    for at, skin, _lst, _n in shapes(d):
        v = struct.unpack_from("<Q", d, at + 0x10)[0]
        if skin != 1 or v in done:
            continue
        done.add(v)
        attrs, strides = struct.unpack_from("<Q", d, v + 0x08)[0], struct.unpack_from("<Q", d, v + 0x38)[0]
        offset, n_attr, n_buf = struct.unpack_from("<IBB", d, v + 0x48)
        if n_buf != 1:
            raise ValueError("a rigid shape with %d vertex buffers" % n_buf)
        found = {}
        for a in range(n_attr):
            e = attrs + 0x10 * a
            name_at = struct.unpack_from("<Q", d, e)[0]
            name = bytes(d[name_at + 2:name_at + 2 + struct.unpack_from("<H", d, name_at)[0]]).decode()
            found[name] = (struct.unpack_from("<I", d, e + 8)[0], struct.unpack_from("<H", d, e + 0xc)[0])
        out.append((base + offset, struct.unpack_from("<I", d, strides)[0], struct.unpack_from("<I", d, v + 0x50)[0], found))
    return out


INDEX = {0x203: "<B", 0xa03: "<H"}   # (a rigid vertex's matrix: one unsigned byte, or 16 bits in a model of over 255)


def turned(word, r):
    """a 10-10-10-2 signed normalized vector (a normal, a tangent: its two top bits kept) turned by the rotation r"""
    v = []
    for i in range(3):
        x = (word >> (10 * i)) & 0x3FF
        v.append(max(-1.0, (x - 1024 if x & 0x200 else x) / 511.0))
    out = word & 0xC0000000
    for i in range(3):
        x = int(round(max(-1.0, min(1.0, sum(r[i][j] * v[j] for j in range(3)))) * 511.0))
        out |= (x & 0x3FF) << (10 * i)
    return out


def carry(d, g, slots, H, T, k, dropped=()):
    """the vertices of the rigid matrices in slots ({matrix: (the bone it was on, its carrier, the carrier's matrix)}),
    already scaled by k, taken to their carriers' spaces; those of the matrices in dropped, to their bone's origin; how
    far off the worst lands"""
    worst = 0.0
    for first, stride, n_vert, attrs in rigid_buffers(d):
        fmt, i_off = attrs.get("_i0", (None, None))
        if fmt not in INDEX:
            raise ValueError("a rigid shape's matrix indices in format %r" % fmt)
        p_off = attrs["_p0"][1]
        for i in range(n_vert):
            at = first + i * stride
            slot = struct.unpack_from(INDEX[fmt], d, at + i_off)[0]
            if slot in dropped:
                struct.pack_into("<3f", d, at + p_off, 0.0, 0.0, 0.0)
            if slot not in slots:
                continue
            old, carrier, new_slot = slots[slot]
            m = mul(inv(H[carrier]), T[old])
            r = [[m[a][b] / k for b in range(3)] for a in range(3)]
            if max(abs(sum(r[a][c] * r[b][c] for c in range(3)) - (a == b)) for a in range(3) for b in range(3)) > 1e-4:
                raise ValueError("%s to %s is not a rotation" % (g.bones[old].name, g.bones[carrier].name))
            x = struct.unpack_from("<3f", d, at + p_off)
            y = [sum(r[a][b] * x[b] for b in range(3)) + m[a][3] for a in range(3)]
            struct.pack_into("<3f", d, at + p_off, *y)
            if max(abs(r[a][b] - (a == b)) for a in range(3) for b in range(3)) > 1e-6:
                for name, (f, off) in attrs.items():
                    if name[:2] in ("_n", "_t", "_b"):
                        if f != 0xe02:
                            raise ValueError("%s in format %#x" % (name, f))
                        struct.pack_into("<I", d, at + off, turned(struct.unpack_from("<I", d, at + off)[0], r))
            struct.pack_into(INDEX[fmt], d, at + i_off, new_slot)
            # (read back: where the carrier at Link's rest puts it, against where the character's own bone, posed and
            #  scaled, would)
            y = struct.unpack_from("<3f", d, at + p_off)
            for a in range(3):
                got = sum(H[carrier][a][b] * y[b] for b in range(3)) + H[carrier][a][3]
                want = sum(T[old][a][b] * x[b] / k for b in range(3)) + T[old][a][3]
                worst = max(worst, abs(got - want))
    return worst


def retarget(ganon_bfres, link_bfres, k, moved, own=(), held=None, shift=(0.0, 0.0, 0.0)):
    """k: the refitted mesh's size, as a fraction of the model's own; moved: rigid bones Link also has -> (the spare bone
    that carries their mesh, its new parent) (characters.py); own: bones to treat as the character's own though Link has
    one of the name (the ones a cloth simulation sets: it writes them after the bind has, so their skinning must expect
    the character's, not Link's: Link has back hair bones too); held: bones -> the bone that carries their skin (above);
    shift: where the scaled mesh is moved to as a whole, in metres (a model standing off its own root, as the Lizalfos,
    18 cm behind it: brought back over Link's skeleton, whose root is under him)"""
    g = Skeleton(ganon_bfres)
    link = Skeleton(link_bfres)
    shared = {b.name for b in g.bones if b.name in link.by_name} - set(own)
    G = g.worlds()
    GA = g.worlds(lambda b: compose(b.scale, link.by_name[b.name].rot, b.trans) if b.name in shared else b.local())
    T = [scaled(m, k) for m in GA]   # (where each bone's frame belongs: S @ GA, shifted)
    for m in T:
        for i in range(3):
            m[i][3] += shift[i]
    d = g.data

    # the rigid meshes on bones Link sets: onto spare bones
    target_of = {}   # bone index -> the bone whose T it takes
    for old, (spare, parent) in moved.items():
        o, s, p = g.by_name[old], g.by_name[spare], g.by_name[parent]
        if spare in shared or s.smooth >= 0 or s.rigid >= 0 or any(b.parent == s.index for b in g.bones):
            raise ValueError("%s is not a spare bone" % spare)
        if o.rigid < 0 or p.index >= s.index:
            raise ValueError("%s has no rigid matrix, or %s comes after %s" % (old, parent, spare))
        struct.pack_into("<H", d, s.at + 0x22, p.index)
        struct.pack_into("<h", d, s.at + 0x26, o.rigid)
        struct.pack_into("<h", d, o.at + 0x26, -1)
        struct.pack_into("<H", d, g.list_at + 2 * o.rigid, s.index)
        s.parent, s.rigid, o.rigid = p.index, o.rigid, -1
        g.matrix_bone[s.rigid] = s.index
        target_of[s.index] = o.index
        moved = 0
        for at, skin, lst, n in shapes(d):
            if skin != 1:   # (a smooth shape weights the bone through its smooth matrix, which stays)
                continue
            for j in range(n):
                if struct.unpack_from("<H", d, lst + 2 * j)[0] == o.index:
                    struct.pack_into("<H", d, lst + 2 * j, s.index)
                    moved += 1
        if not moved:
            raise ValueError("no rigid shape uses %s" % old)

    if not scale_rigid_vertices(d, k) and g.n_rigid:   # (a model with no rigid matrix has no rigid shape: a townsman's)
        raise ValueError("no rigid shapes")

    # the held bones' matrices: onto their carriers (the rigid ones' vertices once H is known, below)
    dropped = set()   # (rigid matrices whose meshes are not worn)
    for b in [b for b, c in (held or {}).items() if c is None]:
        if g.by_name[b].rigid < 0:
            raise ValueError("%s has no rigid mesh to leave out" % b)
        dropped.add(g.by_name[b].rigid)
    held = {g.by_name[b].index: g.by_name[c].index for b, c in (held or {}).items() if c is not None}
    first_bone = list(g.matrix_bone)   # (each matrix's bone as the model has it: where its mesh belongs)
    slots = {}
    for b, c in held.items():
        o, carrier = g.bones[b], g.bones[c]
        if o.index in target_of.values() or carrier.name in own:
            raise ValueError("%s is moved, or %s is set by the cloth" % (o.name, carrier.name))
        if o.smooth >= 0 and c != b:
            struct.pack_into("<H", d, g.list_at + 2 * o.smooth, c)
            g.matrix_bone[o.smooth] = c
        if o.rigid >= 0:
            if carrier.name not in shared:
                raise ValueError("%s, to carry a rigid mesh, is not a bone Link sets" % carrier.name)
            if carrier.rigid < 0:   # (the carrier takes the matrix; else it has one, and this one is left unused)
                struct.pack_into("<h", d, carrier.at + 0x26, o.rigid)
                struct.pack_into("<h", d, o.at + 0x26, -1)
                struct.pack_into("<H", d, g.list_at + 2 * o.rigid, c)
                g.matrix_bone[o.rigid] = c
                slots[o.rigid] = (b, c, o.rigid)
                carrier.rigid, o.rigid = o.rigid, -1
            else:
                slots[o.rigid] = (b, c, carrier.rigid)
            for at, skin, lst, n in shapes(d):
                if skin == 1:
                    for j in range(n):
                        if struct.unpack_from("<H", d, lst + 2 * j)[0] == b:
                            struct.pack_into("<H", d, lst + 2 * j, c)

    # Ganondorf's own bones: rigid ones placed where T puts their frame (unscaled: their vertices are), the others' offsets
    # from their parents scaled
    rigid = [g.bones[g.matrix_bone[g.n_smooth + r]] for r in range(g.n_rigid)]
    frame = [[[m[i][j] / k if j < 3 else m[i][j] for j in range(4)] if i < 3 else m[i][:] for i in range(4)] for m in T]
    H = []
    for b in g.bones:
        if b.name in shared:
            lb = link.by_name[b.name]
            local = compose(b.scale, lb.rot, lb.trans)
        elif b in rigid:
            g.set_local(b, mul(inv(H[b.parent]), frame[target_of.get(b.index, b.index)]), scale=(1.0, 1.0, 1.0))
            local = b.local()
        else:
            g.set_trans(b, tuple(k * x for x in b.trans))
            local = b.local()
        H.append(local if b.parent is None else mul(H[b.parent], local))

    # smooth matrices: the mesh at Link's rest is Ganondorf posed like Link, scaled (a held bone's: by its carrier)
    for i in range(g.n_smooth):
        b = first_bone[i]
        g.set_inverse(i, mul(mul(inv(H[g.matrix_bone[i]]), T[b]), inv(G[b])))
    carried = carry(d, g, slots, H, T, k, dropped) if slots or dropped else 0.0

    # check: every skinning matrix at Link's rest maps Ganondorf's rest mesh to S @ GA, read back from the bytes
    out = bytes(d)
    if len(out) != len(ganon_bfres):
        raise ValueError("the file changed size")
    c = Skeleton(out)
    Hc = c.worlds(lambda b: compose(b.scale, link.by_name[b.name].rot, link.by_name[b.name].trans)
                  if b.name in shared else b.local())
    worst = carried
    for i in range(c.n_smooth):
        b = first_bone[i]
        if c.matrix_bone[i] != held.get(b, b):
            raise ValueError("matrix %d is not on the bone meant" % i)
        worst = max(worst, max_diff(mul(Hc[c.matrix_bone[i]], c.inverse(i)), mul(T[b], inv(G[b]))))
    used = {struct.unpack_from(INDEX[attrs["_i0"][0]], out, first + i * stride + attrs["_i0"][1])[0]
            for first, stride, n, attrs in rigid_buffers(out) for i in range(n)} \
        if slots else set(range(c.n_smooth, c.n_smooth + c.n_rigid))
    done = {new for _old, _carrier, new in slots.values()}   # (matrices whose vertices are in their carrier's space)
    for r in range(c.n_rigid):
        b = c.matrix_bone[c.n_smooth + r]
        if c.n_smooth + r in done or c.n_smooth + r not in used or c.n_smooth + r in dropped:
            continue
        if c.bones[b].name in shared:
            raise ValueError("a rigid mesh is left on %s, a bone Link sets" % c.bones[b].name)
        worst = max(worst, max_diff(Hc[b], frame[target_of.get(b, b)]))
    if worst > 1e-3:
        raise ValueError("the refitted skeleton is off by %g" % worst)
    return out, worst
