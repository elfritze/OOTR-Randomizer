"""Play as Ganondorf, or as Zelda: a RomFS mod for the remake (Longshot) that dresses adult Link as another character
(characters.py: which, and what differs from one to the other).

Putting the character's model on the player crashed in the Chamber of Sages: the game's code looks up some of Link's
bones by name (Pod_A, Pod_B, Weapon_Root, Head_2, Ear_L/R, Ph_Cap_1..7...), the other skeleton has not them, and a bone
handle that was never found is read (longshot.exe, guest 0x80020000 + 0xe4a110 called from 0x4b72e4).

So the player keeps Link's model and skeleton, and the character is worn as a tunic: the Goron and Zora tunics are their
own models that follow the player's bones by name (SameBoneModelBind), and an armor hides the player's materials by group
name (HideMaterialGroupNameList). The Kokiri tunic is part of Link's own model, and the game's code takes the upper armor
off when the item equipped is named Armor_Adult_Normal (six places, compared by name): Link is Link in the Kokiri tunic,
the character in the Goron or Zora one.
  Goron, Zora tunics   the character's model, bound by local transforms (theirs is by world matrix: the bones Link has
                       not, a cape, a face, stayed where they sit on the model's own body), with its cloth simulated
                       (the character's cloth settings and reactions, its cloth file scaled: cloth_scale.py); each hides
                       every group of Link's body the player's equipment defines
  Kokiri tunic         the same model and hidden groups (the pause menu shows it worn)
  the hat              the empty model Dm_Locator
  Link's equipment     his head and hands, in no group of the game's, added to groups only those tunics hide
  Link's voice         with --voice, the character's (voice.py), in any tunic
The model is refitted to Link's skeleton (retarget.py): it takes Link's bones (rotation and translation), so its own rest
mesh, unchanged, came out on Link's bone lengths; refitted, at Link's rest it is the character posed like Link, scaled to
fit his joints, with its own proportions. It is a model file of its own (Model/<mod>.<model>.bfres.zs): the game's
character keeps its model, and its cloth file.

The new files need size-table entries, and the parameter files that grow more room in theirs: the mod ships a size table,
the one the game would read without it (the randomizer seed's, when one is installed) with these raised. The game reads
one table, the mod's sorting last: rebuild and reinstall this mod after installing a new seed (--check says whether it
is needed). The two characters' mods change the same files: installing one turns the other off (its folder renamed with
a leading "_").

One character's mod is on at a time (they change the same files): install() turns the others off, turn_off() all of
them (Link as he is). The randomizer's window does it from its Character page (rando/playas_gui.py), and builds the
character again after a new seed is installed; from a console:

python -m rando.playas <game folder> --list
python -m rando.playas <game folder> --as zelda     builds the mod and installs it in <game folder>/mods
python -m rando.playas <game folder> --as link      turns every character's mod off
python -m rando.playas <game folder> --check        whether the installed mod's size table still matches the others'
(never while the game runs: it reads the mod's files as it goes)
"""
import hashlib
import os
import shutil
import struct
import subprocess
import tempfile

from ..formats import byml, restbl, sarc, zs
from .. import mod as modfile
from . import cloth_scale, voice
from .bfres_skel import Skeleton
from .characters import CHARACTERS
from .retarget import retarget

GAME_EXES = ("longshot.exe", "hookshot.exe")
GAME = None    # the game folder (it holds romfs and mods), ROMFS its romfs: set by use()
ROMFS = None
C = None       # the character built (characters.py): set by use()
LOG = print    # where the build's lines go: set by use()
LINK_MODEL = "Model/Player_Adult.Player_Adult.bfres.zs"
LINK_SOUNDS = "Sound/Resource/Player_Adult.bars.zs"
STREAMS = "Sound/Resource/Stream"


class Problem(Exception):
    """what stops a build or an install, in words for the user"""


def use(game, who=None, log=None):
    """the game folder and the character the functions below work on"""
    global GAME, ROMFS, C, LOG
    GAME, ROMFS = game, os.path.join(game, "romfs")
    if not os.path.isfile(os.path.join(ROMFS, "Pack", "ZsDic.pack.zs")):
        raise Problem("%s has no game romfs" % game)
    if who is not None:
        if who not in CHARACTERS:
            raise Problem("no character named %r" % who)
        C = CHARACTERS[who]
    LOG = log or print
    GREW.clear()   # (what grew in the last build, in a window that builds more than once)


def cloth_name():
    """the character's cloth file's name: its model's, but for the Great Fairy's (Npc_U_GreantFairy)"""
    return getattr(C, "cloth", C.model)


def has_cloth():
    return getattr(C, "set", None) is not None


def model_file(project, model):
    return "Model/%s.%s.bfres.zs" % (project, model)


def cloth_file(name):   # (named in parameters as Work/Phive/Cloth/<name>.phcl)
    return "Phive/Cloth/%s.Nin_Ounce_NVN2.bphcl" % name


EMPTY = "Dm_Locator"
PLAYER_EQUIP = ("Pack/Actor/Player_Adult.pack.zs",
                "Component/EquipmentUserParam/Player_Adult.game__component__EquipmentUserParam.bgyml")

# Link's materials no group of the game's has (his face, ears with it, hair, eyes, teeth, hands), put into groups only the
# Goron and Zora tunics hide in the game (so only Ganondorf hides them)
HEAD_INTO = {
    "G_Body": ["Mt_Face", "Mt_Face_SoftEdge", "Mt_Hairs"],
    "G_Angin": ["Mt_Eye_Inner", "Mt_Eye_Outer", "Mt_Eyebrow"],
    "G_Vest": ["Mt_Eyelashes", "Mt_Eyeshadow", "Mt_Teeth"],
    "G_Feather": ["Mt_Hand"],
}
MAX_PER_GROUP = 4   # (G_Boots's four)
# the size table has an entry for every file inside a pack too: the memory the game unpacks that file in. Each material
# added to the player's groups is an allocation of its own there (the equipment's 9056 for 2216 bytes of file: with ten
# materials more, an allocation of 0x70 bytes failed, longshot.exe guest 0x80020000 + 0xe9d17c, whatever the pack's entry)
HEADROOM = {PLAYER_EQUIP[1]: 0x2000}
TUNICS = {   # pack: (its ModelInfo, its ArmorParam)
    "Armor_Adult_Normal": ("Component/ModelInfo/Armor_Normal.engine__component__ModelInfo.bgyml",
                           "Component/ArmorParam/Armor_Normal.game__component__ArmorParam.bgyml"),
    "Armor_Adult_Goron": ("Component/ModelInfo/Armor_Goron.engine__component__ModelInfo.bgyml",
                          "Component/ArmorParam/Armor_Goron.game__component__ArmorParam.bgyml"),
    "Armor_Adult_Zora": ("Component/ModelInfo/Armor_Zora.engine__component__ModelInfo.bgyml",
                         "Component/ArmorParam/Armor_Zora.game__component__ArmorParam.bgyml"),
}
# the Goron and Zora tunics' bind: world matrices (Normal's is local, RotTrans)
WORLD_BIND = "Component/SameBoneModelBindParam/ArmorWolrdMtxBind.game__component__SameBoneModelBindParam.bgyml"
# groups the Kokiri tunic hid that nothing of the adult's defines (G_UpperBeltSet is the child's, the rest no one's)
DEAD = {"G_Skirt", "G_UpperBeltSet", "G_Upper_RaulHand_A"}
CLOTH_KEYS = ("Cloth", "ClothAdvandecOption", "ClothGroundType", "ClothList", "ClothReaction")
TUNIC_SET = {   # the tunics worn as models: their physics (empty)
    "Pack/Actor/Armor_Adult_Goron.pack.zs": "Phive/ControllerSetParam/Armor_Goron.phive__ControllerSetParam.bgyml",
    "Pack/Actor/Armor_Adult_Zora.pack.zs": "Phive/ControllerSetParam/Armor_Zora.phive__ControllerSetParam.bgyml",
}
HAT = ("Armor_Adult_Default_Head", "Component/ModelInfo/Armor_Adult_Default_Head.engine__component__ModelInfo.bgyml")


def doc(files, name):
    if name not in files:
        raise ValueError("no %s in the pack" % name)
    d, version = byml.read(files[name])
    return d, version, byml.endian(files[name])


GREW = {}   # a file inside a pack: the most bytes it grew by here (its own size-table entry gets room: size_table)


def put(files, name, d, version, e):
    before = len(files[name]) if name in files else 0
    files[name] = byml.write(d, version, e)
    if byml.read(files[name])[0] != d:
        raise ValueError("%s: does not read back" % name)
    if len(files[name]) > before:
        GREW[name] = max(GREW.get(name, 0), len(files[name]) - before)


def set_model(files, name, model, project=None):
    d, v, e = doc(files, name)
    if d.get("FmdbName") != d.get("ModelProjectName"):
        raise ValueError("%s: FmdbName %r, ModelProjectName %r" % (name, d.get("FmdbName"), d.get("ModelProjectName")))
    d["FmdbName"], d["ModelProjectName"] = model, project or model
    put(files, name, d, v, e)


def refit(m, with_cloth, k):
    """the character's model refitted to Link's skeleton (retarget.py), as a model file of its own; with cloth, the bones
    its cloth sets are its own (Link's back hair has bones of the same names as Ganondorf's)"""
    own = cloth_scale.driven_bones(m.read(cloth_file(cloth_name()))) if with_cloth else ()
    data, worst = retarget(m.read(model_file(C.model, C.model)), m.read(LINK_MODEL), k, C.moved, own=own,
                           held=getattr(C, "held", None), shift=getattr(C, "shift", (0.0, 0.0, 0.0)),
                           as_own=getattr(C, "as_own", ()), as_stood=getattr(C, "as_stood", ()))
    m.add(model_file(C.mod, C.model), data, like=model_file(C.model, C.model))
    return worst


def other_voice(m):
    """adult Link's voice clips replaced by the character's (voice.py): his sound archive, in place, and each clip's
    stream file (loose files the size table does not list). How many clips"""
    def stream(name):
        return open(os.path.join(m.romfs, *STREAMS.split("/"), name + ".bwav"), "rb").read()
    sources = [(m.read("Sound/Resource/%s.bars.zs" % bars), strip, prefix) for bars, strip, prefix in C.voices]
    data, streams, done = voice.swap(m.read(LINK_SOUNDS), sources, stream, C.rules, C.other)
    m.write(LINK_SOUNDS, data)
    for name, whole in streams.items():
        rel = "%s/%s.bwav" % (STREAMS, name)
        if m.table.get(rel) is not None:
            raise ValueError("%s is in the resource size table" % rel)
        dst = os.path.join(m.out, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(whole)
    return len(done)


def scaled_cloth(m, k):
    """the character's cloth file scaled to the refitted model (cloth_scale.py), as a file of its own (not compressed, as
    the game's cloth files): the game's character keeps its own. Its size-table entry is that file's (the same size)"""
    source, mine = cloth_file(cloth_name()), cloth_file(C.mod)
    raw = m.read(source)
    # bones the cloth sets that Link has too (his back hair's): Link's hair moves them, and what hangs from them, under
    # the cloth, which reads them to place the hair's reference: read the head instead
    link = Skeleton(m.read(LINK_MODEL))
    moved = cloth_scale.cloth_children(raw, {n for n in cloth_scale.driven_bones(raw) if n in link.by_name})
    raw, changed = cloth_scale.anchor_to_parents(raw, moved, leave=getattr(C, "unanchored", ()))
    for mesh, what in changed.items():
        LOG("%s: reference inputs moved off Link's bones: %s" % (mesh, ", ".join(what)))
    data, done = cloth_scale.scale(raw, k)
    entry = m.original_entry(source)
    if entry is None:
        raise ValueError("%s has no size-table entry" % source)
    if os.path.exists(os.path.join(m.romfs, *mine.split("/"))) or m.table.get(mine) is not None:
        raise ValueError("%s is a game file" % mine)
    m.table.set(mine, entry)
    m.grown.append((mine, 0, entry))
    dst = os.path.join(m.out, *mine.split("/"))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as f:
        f.write(data)
    m.data[mine] = data
    return sum(done.values())


def link_groups(m):
    """the names of the player's material groups (Link's body: G_Body, G_Glove, G_Boots...), Link's head and hands added
    to those HEAD_INTO names (in none of the game's groups, they showed through Ganondorf's smaller head). Not a group of
    their own: a ninth group crashed the game as the player's pack was read (it has 8: a fixed list, it seems), so no group
    is added and none gets more materials than the most the game's have (MAX_PER_GROUP)"""
    rel, name = PLAYER_EQUIP
    files = sarc.read(m.read(rel))
    d, v, e = doc(files, name)
    have = d.get("HiddenMaterialGroupList", [])
    if len(have) != 8:
        raise ValueError("the player's equipment has %d material groups, not 8" % len(have))
    most = max(len(g["MaterialNameList"]) for g in have)
    if most != MAX_PER_GROUP:
        raise ValueError("the game's material groups hold up to %d, not %d" % (most, MAX_PER_GROUP))
    taken = {mt for g in have for mt in g["MaterialNameList"]}
    if taken & {mt for mts in HEAD_INTO.values() for mt in mts}:
        raise ValueError("Link's head materials are in the game's groups already")
    by_name = {g["GroupName"]: g for g in have}
    for group, mts in HEAD_INTO.items():
        g = by_name[group]
        g["MaterialNameList"] = list(g["MaterialNameList"]) + mts
        if len(g["MaterialNameList"]) > MAX_PER_GROUP:
            raise ValueError("%s would hold %d materials" % (group, len(g["MaterialNameList"])))
    put(files, name, d, v, e)
    m.write(rel, sarc.write(files))
    return [g["GroupName"] for g in have]


def work(path):
    """a pack's file name from the path a parameter gives it ("Work/X/Y.gyml" -> "X/Y.bgyml")"""
    if not (path.startswith("Work/") and path.endswith(".gyml")):
        raise ValueError("not a Work/ .gyml path: %r" % path)
    return path[len("Work/"):-len(".gyml")] + ".bgyml"


def cloth(files, source, rel):
    """the character's cloth simulated on the tunic: its cloth settings, its cloth reactions and the cloth file of its
    model, in the tunic's physics (empty in the game's: the Goron and Zora tunics have none)"""
    g = byml.read(source[C.set])[0]
    for key in ("Cloth", "ClothReaction"):   # (a set with a cloth file and no settings for it, as the ReDead's: none)
        g.setdefault(key, [])
    # (a reaction named by the character's settings that its pack does not hold, as Impa's "String" for her ribbons and
    #  belt, in no character's pack: the game's character goes without it, and so does the tunic, without the entry)
    g["ClothReaction"] = [r for r in g["ClothReaction"] if not r["FilePath"] or work(r["FilePath"]) in source]
    d, v, e = doc(files, TUNIC_SET[rel])
    for key in CLOTH_KEYS:
        if d.get(key):
            raise ValueError("%s: the tunic already has %s" % (rel, key))
        if key in g:
            d[key] = g[key]
    for entry in g["Cloth"] + g["ClothReaction"]:
        if entry["FilePath"]:   # (a mesh without a reaction of its own has none)
            name = work(entry["FilePath"])
            files[name] = source[name]
    for entry in g["Cloth"]:   # (the tunic's copy of the cloth settings: hair and skirts kept near where they sit)
        name = work(entry["FilePath"])
        c, cv, ce = doc(files, name)
        meshes = {mesh["Name"]: mesh for mesh in c["MeshList"]}
        for mesh, coef in C.leash.items():
            if meshes[mesh]["ParamCoefDict"].get("localRange_maximumDistance", 0) <= coef:
                raise ValueError("%s: %s's range is already %r" % (name, mesh, meshes[mesh]["ParamCoefDict"]))
            # (as the 32-bit float the file holds: 0.35 reads back as 0.3499999940395355)
            meshes[mesh]["ParamCoefDict"]["localRange_maximumDistance"] = struct.unpack("<f", struct.pack("<f", coef))[0]
        put(files, name, c, cv, ce)
    want = "Work/Phive/Cloth/%s.phcl" % cloth_name()
    if [c.get("Path") for c in d["ClothList"]] != [want]:
        raise ValueError("%s: the character's cloth list is %r" % (rel, d["ClothList"]))
    d["ClothList"] = [dict(c, Path="Work/Phive/Cloth/%s.phcl" % C.mod) for c in d["ClothList"]]   # (the scaled one)
    put(files, TUNIC_SET[rel], d, v, e)


def tunics(m, groups, with_cloth):
    """each tunic: the character's model, its own material groups dropped (they name Link's tunic's materials:
    Mt_Upper_Skin, Mt_Glove, Mt_Boots, which the character's model has not), the groups only it hid dropped (DEAD), and
    every group of the player's hidden; the Goron and Zora tunics (the ones worn as models) bound locally and with the
    character's cloth"""
    source = sarc.read(m.read("Pack/Actor/%s.pack.zs" % C.pack))
    for pack, (info, armor) in TUNICS.items():
        rel = "Pack/Actor/%s.pack.zs" % pack
        files = sarc.read(m.read(rel))
        set_model(files, info, C.model, C.mod)
        if WORLD_BIND in files:   # (bones Link has not, bound by world matrix, stay where they sit on Ganondorf's own body)
            b, bv, be = doc(files, WORLD_BIND)
            if b.get("IsWorldMtxBind") is not True:
                raise ValueError("%s: %s is %r" % (rel, WORLD_BIND, b))
            b["IsWorldMtxBind"] = False
            put(files, WORLD_BIND, b, bv, be)
        if with_cloth and rel in TUNIC_SET:
            cloth(files, source, rel)
        d, v, e = doc(files, armor)
        d.pop("HiddenMaterialGroupList", None)
        hide = [g for g in d.get("HideMaterialGroupNameList", []) if g not in DEAD]
        d["HideMaterialGroupNameList"] = hide + [g for g in groups if g not in hide]
        put(files, armor, d, v, e)
        m.write(rel, sarc.write(files))


def mod_order(mods):
    """the enabled mods, in the order the game's loader takes them (Longshot host/mods.c: the path sorting last wins)"""
    return sorted((n for n in os.listdir(mods) if os.path.isdir(os.path.join(mods, n)) and not n.startswith(("-", "_"))),
                  key=lambda n: n.lower())


def table_base(mods, romfs=None):
    """(the size table the game would read without a character's mod, whose it is, the other mods that are on): the last
    enabled mod's that has one (a randomizer seed's), else the game's ("game")"""
    mine = {c.mod for c in CHARACTERS.values()}   # (one character's mod is on at a time: never the other's table)
    others = [n for n in mod_order(mods) if n not in mine] if os.path.isdir(mods) else []
    for other in reversed(others):
        p = os.path.join(mods, other, "romfs", *modfile.RSTB.split("/"))
        if os.path.isfile(p):
            return p, other, others
    return os.path.join(romfs or ROMFS, *modfile.RSTB.split("/")), "game", others


def size_table(m, codec, with_cloth=False):
    """the size table to ship: the one the game would read without this mod (table_base), with this mod's grown files
    raised. Only one table is read: this mod's must sort last, and must be rebuilt when that other table changes (a new
    seed installed, the seed's mod turned on or off)"""
    mods = os.path.join(GAME, "mods")
    path, source, others = table_base(mods)
    if others and others[-1].lower() > C.mod.lower():
        raise Problem("the mod %s sorts after %s: its size table would win over the character's. Rename it or turn "
                      "it off" % (others[-1], C.mod))
    base = restbl.Table(codec.read(path))
    stamp = hashlib.sha256(open(path, "rb").read()).hexdigest()
    for rel, _, need in m.grown:
        base.set(rel, max(base.get(rel) or 0, need))
    # every file inside a pack that grew: the memory it is unpacked in is its own entry, and what was added costs more
    # there than its bytes (three crashes taught this: the player's equipment, the tunics' physics, their model settings)
    for inner, grew in GREW.items():
        if base.get(inner) is None:
            raise ValueError("%s has no size-table entry" % inner)
        base.set(inner, base.get(inner) + 0x400 + 8 * grew)
    for inner, more in HEADROOM.items():   # (a file inside a pack: its own entry)
        if base.get(inner) is None:
            raise ValueError("%s has no size-table entry" % inner)
        base.set(inner, base.get(inner) + more)
    if with_cloth:   # (the tunics' physics, now holding the character's cloth lists: the memory its own is unpacked in)
        for inner in TUNIC_SET.values():
            if base.get(inner) is None or base.get(C.set) is None:
                raise ValueError("%s or the character's has no size-table entry" % inner)
            base.set(inner, max(base.get(inner), base.get(C.set)))
    data = base.write()
    game = open(os.path.join(ROMFS, *modfile.RSTB.split("/")), "rb").read()
    packed = codec.compress_like(data, game)
    if restbl.Table(codec.decompress(packed)).write() != data:
        raise ValueError("the size table does not read back")
    dst = os.path.join(m.out, *modfile.RSTB.split("/"))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as f:
        f.write(packed)
    with open(os.path.join(os.path.dirname(m.out), "size_table_base.txt"), "w", encoding="utf-8") as f:
        f.write("%s\n%s\n" % (source, stamp))
    return source


def stale(mods, mod=None, romfs=None):
    """why the installed mod's size table no longer fits the other mods (a new seed installed since, the seed's mod
    turned on or off), or None"""
    try:
        source, stamp = open(os.path.join(mods, mod or C.mod, "size_table_base.txt"), encoding="utf-8").read().split()[:2]
    except (OSError, ValueError):
        return None
    path, now, _ = table_base(mods, romfs)
    if now != source:
        return "it was built on %s's size table, and %s's is the one in use now" % (source, now)
    if hashlib.sha256(open(path, "rb").read()).hexdigest() != stamp:
        return "%s's size table changed" % source
    return None


def hat(m):
    pack, info = HAT
    rel = "Pack/Actor/%s.pack.zs" % pack
    files = sarc.read(m.read(rel))
    set_model(files, info, EMPTY)
    m.write(rel, sarc.write(files))


def check(out_romfs, codec):
    """every written pack and its bgyml files read back"""
    for dirpath, _, names in os.walk(out_romfs):
        for n in names:
            if not n.endswith(".pack.zs"):
                continue
            files = sarc.read(codec.decompress(open(os.path.join(dirpath, n), "rb").read(), n))
            for k, data in files.items():
                if k.endswith(".bgyml"):
                    byml.read(data)


def running_games():
    """the game executables running now (Windows; elsewhere none can be told)"""
    if os.name != "nt":
        return []
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=15,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout.lower()
    except (OSError, subprocess.SubprocessError):
        return []
    return [exe for exe in GAME_EXES if '"%s"' % exe in out]


def ours():
    return {c.mod: key for key, c in CHARACTERS.items()}


def current(game):
    """the key of the character whose mod is on in the game folder (characters.CHARACTERS), or None: Link"""
    mods = os.path.join(game, "mods")
    for mod, key in sorted(ours().items()):
        if os.path.isdir(os.path.join(mods, mod)):
            return key
    return None


def outdated(game):
    """why the character's mod that is on must be built again (a new seed installed since), or None"""
    key = current(game)   # (reads only: the window asks while a build may be running, which use() would disturb)
    if key is None:
        return None
    return stale(os.path.join(game, "mods"), CHARACTERS[key].mod, os.path.join(game, "romfs"))


def build(game, who, out, log=None, taller=1.0):
    """the character's mod built in the folder out (emptied first): its romfs and the note of the size table it was
    built on. Reads the game folder, writes nothing in it"""
    use(game, who, log)
    if os.path.exists(out):
        shutil.rmtree(out)
    codec = zs.Codec(ROMFS)
    m = modfile.Mod(ROMFS, codec, os.path.join(out, "romfs"))
    groups = link_groups(m)
    k = C.k * taller
    with_cloth = has_cloth()
    LOG("%s's model refitted to Link's skeleton at %.3f of its size (off by %.1g at most)" % (
        C.who, k, refit(m, with_cloth, k)))
    if with_cloth:
        LOG("its cloth scaled by %.3f (%d values)" % (k, scaled_cloth(m, k)))
    tunics(m, groups, with_cloth)
    hat(m)
    if getattr(C, "voices", None):
        LOG("adult Link's voice: %d clips replaced by %s's" % (other_voice(m), C.who))
    if m.grown:
        LOG("size table: built on %s's, %d entries raised" % (size_table(m, codec, with_cloth), len(m.grown)))
    else:
        m.finish()
    check(os.path.join(out, "romfs"), codec)
    LOG("built %s (the tunics hide %s)" % (C.mod, ", ".join(groups)))
    return sorted(m.data)


def turn_off(game, log=None, keep=None):
    """every character's mod that is on in the game folder turned off (its folder renamed with a leading "_": kept),
    but keep's. Which were"""
    if running_games():
        raise Problem("the game is running: close it first")
    mods = os.path.join(game, "mods")
    done = []
    for mod in sorted(ours()):
        if mod == keep or not os.path.isdir(os.path.join(mods, mod)):
            continue
        if os.path.exists(os.path.join(mods, "_" + mod)):
            shutil.rmtree(os.path.join(mods, "_" + mod))
        os.rename(os.path.join(mods, mod), os.path.join(mods, "_" + mod))
        (log or print)("turned off %s (now _%s)" % (mod, mod))
        done.append(mod)
    return done


def install(game, who, log=None, taller=1.0):
    """the character's mod built and put in the game folder's mods, on; the other characters' turned off. who "link"
    (or None): all of them off. Never while the game runs"""
    log = log or print
    if running_games():
        raise Problem("the game is running: close it first")
    if who in (None, "link"):
        if not turn_off(game, log):
            log("no character's mod was on")
        return None
    mods = os.path.join(game, "mods")
    os.makedirs(mods, exist_ok=True)
    work = tempfile.mkdtemp(prefix="playas-")
    try:
        out = os.path.join(work, CHARACTERS[who].mod)
        files = build(game, who, out, log, taller)
        if running_games():   # (started while the mod was being built)
            raise Problem("the game is running: close it first")
        mine = set(ours())
        for other in os.listdir(mods):   # (another mod with one of these files: the one sorting last wins)
            if other in mine or other.startswith(("-", "_")) or not os.path.isdir(os.path.join(mods, other)):
                continue
            for d in files:
                if os.path.exists(os.path.join(mods, other, "romfs", *d.split("/"))):
                    log("warning: %s also has %s" % (other, d))
        for old in (C.mod, "_" + C.mod):   # (the mod on or off: replaced, on)
            if os.path.exists(os.path.join(mods, old)):
                shutil.rmtree(os.path.join(mods, old))
        turn_off(game, log, keep=C.mod)
        shutil.copytree(out, os.path.join(mods, C.mod))
        log("installed %s: %s is worn as the Goron and Zora tunics" % (C.mod, C.who))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return C.mod


def again(game, log=None):
    """the character's mod that is on, built again when the size table it was built on changed (a new seed installed);
    whether it was"""
    key = current(game)
    if key is None or outdated(game) is None:
        return False
    (log or print)("The character's mod (%s) was built on the last seed's size table: building it again…" % CHARACTERS[key].who)
    install(game, key, log)
    return True
