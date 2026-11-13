"""Items lying in the world (Heart Pieces, keys, rupees: Obj_Item_Base actors, whose own actor is the item) made chests: the
actor keeps its Hash, place and turn, and becomes a small chest with the item in it (Dynamic.Drop__DropActor), as the remake
itself made two of N64's Heart Pieces big chests (Dampe's race, Gerudo Valley's crate ledge). The chest is the content's way
in: a chest gives any item with its get-item scene (rando.chests), where an Obj_* pickup gives only its own."""
import math
import os

from . import chests
from .formats import byml

CHEST = "Obj_TBox_A_01"


def upright_yaw(rotate):
    """the heading (radians about +Y) of an actor's Euler rotation (x, y, z): the angle its forward axis makes in the ground
    plane, so a chest put there faces the same way upright. (A rupee lying at (-pi, a, -pi) is upright, facing -a - pi.)"""
    x, y, z = rotate
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    # (R = Rz * Ry * Rx; its third column is where +Z, the forward axis, goes)
    fx = cz * sy * cx + sz * sx
    fz = cy * cx
    return math.atan2(fx, fz)


def write(romfs, codec, mod, contents):
    """contents: {hash: drop actor}: each such item actor in the maps becomes a chest holding that actor. Returns the files
    written."""
    want = {int(h): v for h, v in contents.items()}
    written, seen = [], set()
    for rel in chests.map_files(romfs):
        root, version = byml.read(codec.read(os.path.join(romfs, rel)))
        changed = False
        for a in root.get("Actors", []):
            h = int(a.get("Hash", 0))
            if h not in want:
                continue
            if chests.is_chest(a):
                raise ValueError("%d is a chest already" % h)
            a["Gyaml"] = CHEST
            a.setdefault("Dynamic", {})[chests.DROP] = want[h]
            if "Rotate" in a:   # (a chest stands upright: only the item's heading is kept)
                a["Rotate"] = [0.0, upright_yaw(a["Rotate"]), 0.0]
            seen.add(h)
            changed = True
        if changed:
            mod.write(rel, byml.write(root, version))
            written.append(rel)
    if seen != set(want):
        raise ValueError("not in any map: %s" % sorted(set(want) - seen))
    return written
