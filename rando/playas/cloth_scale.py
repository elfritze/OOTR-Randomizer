"""A Havok cloth file (Phive/Cloth/*.bphcl) scaled uniformly: the cloth of a model made K times its size. In place: the
numbers change, nothing moves.

Every length in the simulation is multiplied by K: where particles rest, how long links are, how big the collision shapes
are and where they sit on their bones, how the simulated mesh is skinned to the bones that pin it, and how bones are read
back off its triangles. Masses, stiffnesses, damping, gravity and times stay (the cloth is a smaller cloth in the same
world). Each field holding real numbers is named below, scaled or kept: one this file does not know stops the build.

by field, values multiplied by K ** power:
  scalars   SCALED
  vectors   xyz of an hkVector4 (XYZ), all four of an hkSphere's (centre and radius), the fourth of an hclPlaneShape's
            plane equation (its distance; the first three are its unit normal)
  matrices  the translation column of an hkMatrix4 (MATRIX_T), of an hkPreciseTransform (hclCollidable.transform), of an
            hkQsTransform (the cloth's skeleton's reference pose)
  packed    an hkPackedVector3's three mantissas (values[3] is the unit they share, the upper 16 bits of a float that
            is a power of two: raised when a mantissa scaled up no longer fits its 16 bits)
  hclSimpleMeshBoneDeformOperator.localBoneTransforms: a bone's transform in the frame of a triangle of the simulated
            mesh, whose axes are its two edges and their cross product, not normalised: the rows of that matrix take
            1/K, 1/K and 1/K**2 (1, 1, 1/K for its translation column), so that the bone comes out K times as far and
            turned the same
"""
import struct

from .hk_tag import KIND_FLOAT, Tagfile

SCALED = {   # field: power of K
    "bendMinLength": 1, "stretchMaxLength": 1,                        # hclBendLinkConstraintSet::Link
    "restCurvature": 1, "maxRestPoseHeightSq": 2,                     # hclBendStiffnessConstraintSet
    "radius": 1, "capLenSqrdInv": -2,                                 # hclCapsuleShape, ParticleData
    "pinchDetectionRadius": 1,                                        # hclCollidable, CollidablePinchingData, Landscape
    "restLength": 1, "compressionLength": 1,                          # the link constraint sets
    "maxNormalDistance": 1, "minNormalDistance": 1, "shapeRadius": 1,  # hclLocalRangeConstraintSet::LocalConstraint
    "maxParticleRadius": 1,                                           # hclSimClothData
    "collisionTolerance": 1, "landscapeRadius": 1,                    # LandscapeCollisionData
    "maxTranslationSpeed": 1, "minTranslationSpeed": 1,               # TransferMotionData
    "toSimMaxDistance": 1,                                            # hclTransitionConstraintSet::PerParticle
}
KEPT = {
    "constantParticleDragFactor", "constantParticleLiftFactor", "dragCoefficient", "liftCoefficient", "surfaceDensity",
    "bendStiffness", "stretchStiffness", "stiffness", "weightA", "weightB", "weightC", "weightD",
    "dir", "angularVelocity", "linearVelocity", "totalMass", "virtualCollisionPointsRadiusScale",
    "stuckParticlesStretchFactorSq", "globalDampingPerSecond", "gravity", "friction", "invMass", "mass",
    "maxRotationBlend", "maxRotationSpeed", "maxTranslationBlend", "minRotationBlend", "minRotationSpeed",
    "minTranslationBlend", "toAnimPeriod", "toAnimPlusDelayPeriod", "toSimPeriod", "toSimPlusDelayPeriod",
    "toAnimDelay", "toSimDelay", "rotation", "scale",
    "weight",                                             # hclVolumeConstraint::FrameData
    "edgeBarycentricsDictionary", "u", "v",               # hclVirtualCollisionPointsData: barycentric coordinates
}
XYZ = {"start", "end", "positions",                      # hkVector4: hclCapsuleShape, hclSimClothPose
       "frameVector"}                                    # hclVolumeConstraint's frame and apply data: positions in its frame
BLOCK_XYZ = {"localPosition"}                            # hkVector4 in hclBoneSpaceDeformer::LocalBlockP (w is 1)
MATRIX_T = {"boneFromSkinMeshTransforms", "offsets"}     # hkMatrix4: translation in floats 12..14
TRIANGLE = {"localBoneTransforms"}


def scale(data, k):
    """the cloth file's bytes scaled by k, and {field: how many values changed}"""
    t = Tagfile(data)
    done = {}

    def mul(off, index, factor):
        v = t.floats(off + 4 * index, 1)[0]
        if abs(v * factor) > 3.4028234e38:   # (the largest float, for "no limit", scaled up: no float holds it. It stays)
            return
        t.set_floats(off + 4 * index, [v * factor])

    def count(field, n=1):
        done[field] = done.get(field, 0) + n

    def visit(path, ti, off):
        if not path:
            return None
        field = path[-1][1]
        ty = t.types[ti]
        name = ty.name
        if name == "hkVector4" and field in XYZ | BLOCK_XYZ:
            for i in range(3):
                mul(off, i, k)
            count(field)
            return False
        if name == "hkVector4" and path[-1][0] == "hkSphere" and field == "pos":
            for i in range(4):
                mul(off, i, k)
            count("hkSphere.pos")
            return False
        if name == "hkVector4" and field == "planeEquation":   # (hclPlaneShape: a unit normal, and the plane's distance)
            mul(off, 3, k)
            count(field)
            return False
        if name == "hkMatrix4" and field in MATRIX_T:
            for i in (12, 13, 14):
                mul(off, i, k)
            count(field)
            return False
        if name == "hkMatrix4" and field in TRIANGLE:
            for col in range(4):
                for row in range(3):
                    power = (0 if row < 2 else -1) if col == 3 else (-1 if row < 2 else -2)
                    mul(off, col * 4 + row, k ** power)
            count(field)
            return False
        if name == "hkPreciseTransform" and field == "transform":
            for i in (12, 13, 14, 16, 17, 18):   # (the translation, and the four floats after it: its fine part)
                mul(off, i, k)
            count(field)
            return False
        if name == "hkQsTransform" and field == "referencePose":
            for i in range(3):
                mul(off, i, k)
            count(field)
            return False
        if name == "hkPackedVector3":
            *m, e = struct.unpack_from("<3hH", t.data, t.data_at + off)
            m = [x * k for x in m]
            while max(abs(x) for x in m) > 32767:   # (scaled up past 16 bits: half the mantissas, twice their unit, the
                m = [x / 2 for x in m]              #  upper half of a float that is a power of two: its exponent one more)
                e += 0x80
            struct.pack_into("<3hH", t.data, t.data_at + off, *(int(round(x)) for x in m), e)
            count("hkPackedVector3")
            return False
        if t.types[t.resolved(ti)].kind == KIND_FLOAT:
            if t.size_of(ti) != 4:
                raise ValueError("%s.%s is not a 32-bit float" % path[-1])
            if field in SCALED:
                mul(off, 0, k ** SCALED[field])
                count(field)
            elif field not in KEPT:
                raise ValueError("a field this scaler does not know: %s.%s" % path[-1])
        return None

    t.walk(visit)
    need = {"positions", "restLength", "radius", "localBoneTransforms", "referencePose"}   # (what every cloth has)
    if need - set(done):
        raise ValueError("fields the cloth file has not: %s" % sorted(need - set(done)))
    out = bytes(t.data)
    if len(out) != len(data):
        raise ValueError("the cloth file changed size")
    return out, done


def _un(o):
    """a value read through hkRefPtr wrappers ({"ptr": x})"""
    while isinstance(o, dict) and [k for k in o if not k.startswith("@")] == ["ptr"]:
        o = o["ptr"]
    return o


def anchor_to_parents(data, moved, leave=()):
    """the cloth file with its skinning operators no longer reading the bones named in `moved`: each such input reads
    instead the bone's nearest parent (in the cloth's skeleton) that is an input not in `moved`, with that parent's own
    skin-to-bone matrix, so at rest the skinned mesh is where it was. For bones something else moves under the cloth (Link's
    hair bones of the same names, set from his hair each frame): the simulated mesh's reference then follows the parent
    (the head) alone. {mesh: [bone -> parent]} of what changed. leave: meshes whose operators are left as they are
    (a bone-space skin, as the sleeves of Richard's lady: its reference then follows what moves those bones)"""
    t = Tagfile(data)
    root = t.root(30)
    variants = {v["className"]: _un(v["variant"]) for v in root["namedVariants"]}
    skeletons = {_un(s)["name"]: _un(s) for s in variants["hkaAnimationContainer"]["skeletons"]}
    changed = {}
    for cd in variants["hclClothContainer"]["clothDatas"]:
        cd = _un(cd)
        sets = [_un(ts)["name"] for ts in cd["transformSetDefinitions"]]
        for op in (_un(o) for o in cd["operators"]):
            if "transformSubset" not in op or "transformSetIndex" not in op:
                continue
            sk = skeletons[sets[op["transformSetIndex"]]]
            names, parents = [b["name"] for b in sk["bones"]], sk["parentIndices"]
            subset = op["transformSubset"]
            hit = [j for j, i in enumerate(subset) if names[i] in moved]
            if not hit or cd["name"] in leave:
                continue
            if "boneFromSkinMeshTransforms" not in op or len(op["boneFromSkinMeshTransforms"]) != len(subset):
                raise ValueError("%s: its skinning is not object space, one matrix per input" % cd["name"])
            _et, sub_at, _n = op["@transformSubset"]
            mt, mat_at, _n = op["@boneFromSkinMeshTransforms"]
            size = t.size_of(mt)
            for j in hit:
                i = subset[j]
                while names[i] in moved or i not in subset:   # (Nabooru's back hair: under Hair_Root, not an input; Head is)
                    i = parents[i]
                    if not 0 <= i < len(names):
                        raise ValueError("%s: %s has no parent among the inputs outside the moved bones" %
                                         (cd["name"], names[subset[j]]))
                src = subset.index(i)
                struct.pack_into("<H", t.data, t.data_at + sub_at + 2 * j, i)
                a = t.data_at + mat_at
                t.data[a + size * j:a + size * (j + 1)] = t.data[a + size * src:a + size * (src + 1)]
                changed.setdefault(cd["name"], []).append("%s -> %s" % (names[subset[j]], names[i]))
    return bytes(t.data), changed


def cloth_children(data, roots):
    """the names in `roots` and of every bone under one of them in the cloth file's skeletons"""
    t = Tagfile(data)
    root = t.root(30)
    variants = {v["className"]: _un(v["variant"]) for v in root["namedVariants"]}
    out = set()
    for s in variants["hkaAnimationContainer"]["skeletons"]:
        s = _un(s)
        names, parents = [b["name"] for b in s["bones"]], s["parentIndices"]
        for i, n in enumerate(names):
            j = i
            while 0 <= j < len(names):
                if names[j] in roots:
                    out.add(n)
                    break
                j = parents[j]
    return out


def driven_bones(data):
    """the names of the bones the cloth file's simulations set (their mesh-to-bone operators' outputs)"""
    t = Tagfile(data)
    root = t.root(30)

    variants = {v["className"]: _un(v["variant"]) for v in root["namedVariants"]}
    skeletons = {_un(s)["name"]: [b["name"] for b in _un(s)["bones"]] for s in variants["hkaAnimationContainer"]["skeletons"]}
    un = _un
    out = set()
    for cd in variants["hclClothContainer"]["clothDatas"]:
        cd = un(cd)
        sets = [un(ts)["name"] for ts in cd["transformSetDefinitions"]]
        for op in (un(o) for o in cd["operators"]):
            if "triangleBonePairs" in op:
                names = skeletons[sets[op["outputTransformSetIdx"]]]
                out |= {names[p["boneOffset"] // 64] for p in op["triangleBonePairs"]}
    return out
