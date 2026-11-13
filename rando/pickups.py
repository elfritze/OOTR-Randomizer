"""Items lying in the world as the items themselves: a new pickup actor for each item, made as the remake made its own loose
major items (Obj_Arrow_Fire, the Fire Arrows on Lake Hylia; Obj_Shield_Deku, Obj_Armor_Zora): an Obj_Item_Base pickup
whose PouchContentParam's PouchActor is the item it gives, with that item's name, model, animations and icon.

A new pickup is Obj_Arrow_Fire's pack with its item swapped (Pack/Actor/<name>.pack.zs, a new file: Hookshot's mods may add
files), and rows like Obj_Arrow_Fire's in RSDB ActorInfo and GameActorInfo, and like the item's in PouchActorInfo. A map
actor (a Heart Piece, a Heart Container, a rupee) becomes one by its Gyaml; its Hash, place and links stay, so whatever
spawned it (a boss room's logic) spawns the new one."""
import copy
import os

from . import patches
from .formats import byml, sarc

BASE = "Obj_Arrow_Fire"
PREFIX = "Obj_Rando_"
ACTOR_INFO = "RSDB/ActorInfo.Product.111.rstbl.byml.zs"
GAME_ACTOR_INFO = "RSDB/GameActorInfo.Product.111.rstbl.byml.zs"
POUCH_ACTOR_INFO = "RSDB/PouchActorInfo.Product.111.rstbl.byml.zs"
# (the components an item's own actor gives its pickup: what it is, how it looks, its icon; its game parameters are merged
# with the pickup's below)
FROM_ITEM = ("ActorNameRef", "ModelInfoRef", "AnimationRef", "CaptureRef")
GPT = "GameParameterTableRef"


def name_for(item):
    return PREFIX + item


def pack_path(actor):
    return "Pack/Actor/%s.pack.zs" % actor


def _ref_file(ref):
    """a component reference's file in a pack: "?Component/X/Y.bgyml" -> "Component/X/Y.bgyml" """
    if not ref.startswith("?"):
        raise ValueError("not a pack reference: %r" % ref)
    return ref[1:]


def _work(file):
    """a pack file's source name, as a $parent or PouchActor names it: "Component/X/Y.bgyml" -> "Work/Component/X/Y.gyml" """
    if not file.endswith(".bgyml"):
        raise ValueError(file)
    return "Work/" + file[:-len(".bgyml")] + ".gyml"


def _refs_in(files, root):
    """every pack file a yaml's references reach, itself included (component files name their parents and sub-files)"""
    out, todo = set(), [root]
    while todo:
        f = todo.pop()
        if f in out or f not in files:
            continue
        out.add(f)
        doc, _ = byml.read(files[f])
        for v in _strings(doc):
            if v.startswith("?"):
                todo.append(v[1:])
            elif v.startswith("Work/") and v.endswith(".gyml"):
                todo.append(v[len("Work/"):-len(".gyml")] + ".bgyml")
    return out


def _strings(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from _strings(x)
    elif isinstance(v, list):
        for x in v:
            yield from _strings(x)


def _components(files, actor_file):
    """an actor's components with its parents' (its $parent chain, in the pack): the nearest one's wins"""
    chain = []
    f = actor_file
    while f:
        if f not in files:
            raise ValueError("%s: not in the pack" % f)
        doc, _ = byml.read(files[f])
        chain.append(doc)
        parent = doc.get("$parent")
        f = parent[len("Work/"):-len(".gyml")] + ".bgyml" if parent else None
    comps = {}
    for doc in reversed(chain):
        comps.update(doc.get("Components", {}))
    return comps


class Pickups:
    """the pickups a seed needs, made once each, written with mod.finish's tables"""

    def __init__(self, romfs, codec, mod):
        self.romfs, self.codec, self.mod = romfs, codec, mod
        self.base = sarc.read(codec.read(os.path.join(romfs, *pack_path(BASE).split("/"))))
        self.tables = {}
        self.made = {}

    def _table(self, rel):
        if rel not in self.tables:
            raw = self.mod.read(rel)
            rows, version = byml.read(raw)
            self.tables[rel] = (rows, version, byml.endian(raw))
        return self.tables[rel][0]

    def _row(self, rel, row_id):
        rows = [r for r in self._table(rel) if r["__RowId"] == row_id]
        if len(rows) != 1:
            raise ValueError("%s: %d rows %s" % (rel, len(rows), row_id))
        return rows[0]

    def actor_for(self, item):
        """the pickup actor giving item (an existing one when the game has it: Obj_Shield_Deku for the Deku Shield...)"""
        if item in self.made:
            return self.made[item]
        name = name_for(item)
        files = sarc.read(self.codec.read(os.path.join(self.romfs, *pack_path(item).split("/"))))
        comps = _components(files, "Actor/%s.engine__actor__ActorParam.bgyml" % item)
        if "PouchContentRef" not in comps:
            raise ValueError("%s has no PouchContentRef" % item)

        out = {k: v for k, v in self.base.items() if k != "Actor/%s.engine__actor__ActorParam.bgyml" % BASE}
        param_file = "Actor/%s.engine__actor__ActorParam.bgyml" % BASE
        param, version = byml.read(self.base[param_file])
        e = byml.endian(self.base[param_file])
        param = copy.deepcopy(param)
        for key in FROM_ITEM:
            if key not in comps:
                continue
            param["Components"][key] = comps[key]
            if not comps[key]:   # (an empty reference: the item has none (a bottle's icon))
                continue
            ref = comps[key][1:]
            for f in _refs_in(files, ref):   # (the item's own files those reach, if it carries them)
                out.setdefault(f, files[f])
        song = item in patches.SONGS   # (a song's own model is a rupee the game never shows: Sheik's harp, as in chests)
        if song:
            mi = _ref_file(comps["ModelInfoRef"])
            info, v = byml.read(out[mi])
            info["ModelProjectName"], info["FmdbName"] = patches.SONG_MODEL
            out[mi] = byml.write(info, v, byml.endian(out[mi]))
        # (game parameters: the item's (what the menu and its use know of it), with the pickup's physics controller, which
        #  an item's own actor, never lying in the world, has none of)
        base_gpt_file = _ref_file(param["Components"][GPT])
        base_gpt, _ = byml.read(self.base[base_gpt_file])
        gpt = {"Category": "GameParameterTableDefault", "Components": {}}
        if GPT in comps:
            item_gpt_file = _ref_file(comps[GPT])
            item_gpt, _ = byml.read(files[item_gpt_file])
            gpt = copy.deepcopy(item_gpt)
            for f in _refs_in(files, item_gpt_file):
                if f != item_gpt_file:
                    out.setdefault(f, files[f])
        for k in ("GamePhysicsControllerParam",):
            if k not in gpt.get("Components", {}) and k in base_gpt["Components"]:
                gpt.setdefault("Components", {})[k] = base_gpt["Components"][k]
        gpt_file = "GameParameter/GameParameterTable/%s.engine__actor__GameParameterTable.bgyml" % name
        out[gpt_file] = byml.write(gpt, version, e)
        param["Components"][GPT] = "?" + gpt_file
        # (what is got: the item's own pouch content as the parent, the item as the PouchActor)
        item_pouch = _ref_file(comps["PouchContentRef"])
        for f in _refs_in(files, item_pouch):
            out.setdefault(f, files[f])
        base_pouch, _ = byml.read(self.base["Component/PouchContentParam/%s.game__component__PouchContentParam.bgyml" % BASE])
        pouch = {"$parent": _work(item_pouch), "IsPickedUpEmitXlinkKey": True,
                 "PickedUpEmitXlinkKey": base_pouch["PickedUpEmitXlinkKey"],
                 "PouchActor": "Work/Actor/%s.engine__actor__ActorParam.gyml" % item}
        pouch_file = "Component/PouchContentParam/%s.game__component__PouchContentParam.bgyml" % name
        out[pouch_file] = byml.write(pouch, version, e)
        param["Components"]["PouchContentRef"] = "?" + pouch_file
        out["Actor/%s.engine__actor__ActorParam.bgyml" % name] = byml.write(param, version, e)
        self.mod.add(pack_path(name), sarc.write(out), like=pack_path(BASE))

        # (the tables: the pickup as Obj_Arrow_Fire is, with the item's model; in the pouch, as the item is)
        base_row, item_row = self._row(ACTOR_INFO, BASE), self._row(ACTOR_INFO, item)
        row = copy.deepcopy(base_row)
        for k in ("ActorName", "ModelProjectName", "FmdbName", "AnimationResources", "ModelAabbMin", "ModelAabbMax"):
            if k in item_row:
                row[k] = copy.deepcopy(item_row[k])
            else:
                row.pop(k, None)
        for k in ("InstanceHeapSize", "PreActorRenderInfoHeapSize"):   # (room for both: the pickup's parts, the item's model)
            row[k] = max(base_row.get(k, 0), item_row.get(k, 0)) + max(0, min(base_row.get(k, 0), item_row.get(k, 0)) // 2)
        if song:
            row["ModelProjectName"], row["FmdbName"] = patches.SONG_MODEL
        row["__RowId"] = name
        self._add(ACTOR_INFO, row)
        g = copy.deepcopy(self._row(GAME_ACTOR_INFO, BASE))
        g["__RowId"] = name
        self._add(GAME_ACTOR_INFO, g)
        p = copy.deepcopy(self._row(POUCH_ACTOR_INFO, item))
        p["__RowId"] = name
        self._add(POUCH_ACTOR_INFO, p)
        self.made[item] = name
        return name

    def _add(self, rel, row):
        rows = self._table(rel)
        if any(r["__RowId"] == row["__RowId"] for r in rows):
            raise ValueError("%s has %s already" % (rel, row["__RowId"]))
        rows.append(row)
        rows.sort(key=lambda r: r["__RowId"])   # (the tables are sorted by row id)

    def finish(self):
        for rel, (rows, version, e) in self.tables.items():
            self.mod.write(rel, byml.write(rows, version, e))


# A pickup stands where the actor it replaces stood, its model drawn from there. A boss's Heart Container stands at the floor
# or a little under it, its own floating animation lifting it clear: the Hover Boots put there were half in the floor (seen in
# game, 2026-11-13). So each pickup is raised by how far its model reaches below its origin, and by LIFT_FROM more where the
# actor it replaces was one of those.
LIFT_FROM = {"Obj_Heart_Container": 0.25}


def model_bottom(pickups, item):
    """how far below its origin the item's model reaches (metres, >= 0), by its ActorInfo bounding box"""
    rows = pickups._table(ACTOR_INFO)
    if item in patches.SONGS:   # (shown as the harp)
        row = next(r for r in rows if r.get("ModelProjectName") == patches.SONG_MODEL[0] and "ModelAabbMin" in r)
    else:
        row = pickups._row(ACTOR_INFO, item)
    return max(0.0, -row.get("ModelAabbMin", {}).get("Y", 0.0))


def place(romfs, codec, mod, contents, pickups):
    """contents: {hash: item}: each map actor with that Hash becomes the pickup giving item. Returns the files written."""
    from . import chests
    want = {int(h): v for h, v in contents.items()}
    written, seen = [], set()
    for rel in chests.map_files(romfs):
        root, version = byml.read(mod.read(rel))
        changed = False
        for a in root.get("Actors", []):
            h = int(a.get("Hash", 0))
            if h in want:   # (an "Obj_" name: one of the game's own pickups, as it is)
                lift = LIFT_FROM.get(a["Gyaml"], 0.0) + model_bottom(pickups, want[h])
                if lift and "Translate" in a:
                    y = a["Translate"][1]
                    a["Translate"] = [a["Translate"][0], type(y)(y + lift), a["Translate"][2]]   # (its own float type)
                a["Gyaml"] = want[h] if want[h].startswith("Obj_") else pickups.actor_for(want[h])
                seen.add(h)
                changed = True
        if changed:
            mod.write(rel, byml.write(root, version))
            written.append(rel)
    if seen != set(want):
        raise ValueError("not in any map: %s" % sorted(set(want) - seen))
    return written
