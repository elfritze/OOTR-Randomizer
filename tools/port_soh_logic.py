"""Generate rando/logic/soh_data.py and rando/logic/soh_regions.py from Ship of Harkinian's randomizer sources.

    python tools/port_soh_logic.py [--soh <Shipwright checkout>]

soh_data.py: SoH's enums (values), Logic/free function declarations (logic.h, location_access.h), the item table
(item_list.cpp) and the location table (location_list.cpp and the Shuffle*.cpp / fishsanity.cpp tables).
soh_regions.py: SoH's region graph (location_access/root.cpp, overworld/*.cpp, dungeons/*.cpp; the region data in
location_access.cpp: grottoEvents, spiritLogicData), every rule translated by rando.logic.translate.

Master Quest is left out. The rule (checked here, a violation is an error):
  - a region is MQ iff its RR_* name contains "_MQ_" or ends in "_MQ"; in the dungeon files every region inside a
    `#pragma region MQ` block is MQ-named and none in a `#pragma region Vanilla` block is;
  - an exit from a vanilla region into an MQ region is dropped, and must be conditioned (a top-level && term) on
    ctx->GetDungeon(X)->IsMQ() (the dungeon entryways' "Vanilla/MQ Decider" and the boss-door back exits), which
    is false with vanilla dungeons; no MQ region is reachable otherwise;
  - a location in a vanilla region must not be RCQUEST_MQ (location tables); MQ regions' locations are dropped;
  - spiritLogicData entries keyed by MQ regions are dropped.
Anything the parser or the translator does not handle is an error naming the construct and file:line."""
import argparse
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

OUT_DATA = os.path.join(ROOT, "rando", "logic", "soh_data.py")
OUT_REGIONS = os.path.join(ROOT, "rando", "logic", "soh_regions.py")
TOOL = "tools/port_soh_logic.py"


class PortError(Exception):
    pass


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


# ---- C++ text helpers (comment stripping is translate.strip_comments, imported late: translate needs soh_data)

def _strip(text):
    # (a local copy of the comment stripper, so soh_data can be generated before rando.logic.translate imports)
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            out.append("".join(ch if ch == "\n" else " " for ch in text[i:j + 2]))
            i = j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def matching(text, i, open_="(", close=")"):
    """index of the bracket closing text[i] (== open_), skipping strings"""
    depth = 0
    n = len(text)
    while i < n:
        c = text[i]
        if c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        if c == open_:
            depth += 1
        elif c == close:
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise PortError(f"unbalanced {open_}")


def split_args(text, base, where, protect="([{"):
    """[(arg text, offset)] of a comma separated list, split at depth 0 of the given brackets (the C preprocessor
    protects commas only inside parentheses: protect="(")"""
    pairs = {"(": ")", "[": "]", "{": "}"}
    closers = {pairs[p] for p in protect}
    args, depth, start, i, n = [], 0, 0, 0, len(text)
    allb = 0
    while i < n:
        c = text[i]
        if c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        if c in protect:
            depth += 1
        elif c in closers:
            depth -= 1
        if c in "([{":
            allb += 1
        elif c in ")]}":
            allb -= 1
        if c == "," and depth == 0:
            if allb != 0:
                raise PortError(f"{where(base + i)}: a macro argument splits inside braces/brackets")
            args.append((text[start:i], base + start))
            start = i + 1
        i += 1
    if text[start:].strip():
        args.append((text[start:], base + start))
    return args


def line_of(text):
    starts = [0]
    for m in re.finditer("\n", text):
        starts.append(m.end())

    def line(off):
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= off:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1
    return line


# ---- enums

def parse_rando_enums(soh_rando):
    """{enum type: {name: value}} of randomizerEnums/*.h (RANDO_ENUM_BEGIN/ITEM/END)"""
    enums = {}
    d = os.path.join(soh_rando, "randomizerEnums")
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".h"):
            continue
        path = os.path.join(d, fn)
        text = _strip(read(path))
        line = line_of(text)
        for m in re.finditer(r"^\s*#\s*(if|ifdef|ifndef|elif|else)\b(.*)$", text, re.M):
            if not re.match(r"\s*RANDO_ENUM_(BEGIN|ITEM|END)(_CLEANUP)?\s*$", m.group(2)) and m.group(1) != "else":
                raise PortError(f"{path}:{line(m.start())}: conditional compilation {m.group().strip()!r}")
        cur = None
        for m in re.finditer(r"RANDO_ENUM_(BEGIN|ITEM|END)\(([^()]*)\)", text):
            kind, args = m.group(1), m.group(2).strip()
            if kind == "BEGIN":
                if args in ("...",):
                    continue
                cur, nxt = args, 0
                if cur in enums:
                    raise PortError(f"{path}: enum {cur} twice")
                enums[cur] = {}
            elif kind == "ITEM":
                if args == "...":
                    continue
                parts = [p.strip() for p in args.split(",", 1)]
                name = parts[0]
                if len(parts) == 2:
                    val = eval_enum_value(parts[1], enums, f"{path}:{line(m.start())}")
                else:
                    val = nxt
                enums[cur][name] = val
                nxt = val + 1
            else:
                if args != "..." and args != cur:
                    raise PortError(f"{path}: RANDO_ENUM_END({args}) closes {cur}")
                cur = None
    return enums


def eval_enum_value(expr, enums, where):
    known = {}
    for e in enums.values():
        known.update(e)
    toks = re.findall(r"0[xX][0-9a-fA-F]+|\d+|[A-Za-z_]\w*|[-+*()|<>]+|\S", expr)
    out = []
    for t in toks:
        if re.fullmatch(r"[A-Za-z_]\w*", t):
            if t not in known:
                raise PortError(f"{where}: enum value {expr!r}: unknown {t}")
            out.append(str(known[t]))
        elif re.fullmatch(r"0[xX][0-9a-fA-F]+|\d+|[-+*()|]|<<|>>", t):
            out.append(t)
        else:
            raise PortError(f"{where}: enum value {expr!r}")
    return int(eval(" ".join(out), {"__builtins__": {}}))


def parse_scenes(soh_root):
    path = os.path.join(soh_root, "soh", "include", "tables", "scene_table.h")
    if not os.path.exists(path):
        path = os.path.join(soh_root, "include", "tables", "scene_table.h")
    text = _strip(read(path))
    names = re.findall(r"^\s*DEFINE_SCENE\(\s*\w+\s*,\s*\w+\s*,\s*(SCENE_\w+)", text, re.M)
    if len(names) != len(re.findall(r"^\s*DEFINE_SCENE\(", text, re.M)):
        raise PortError(f"{path}: unparsed DEFINE_SCENE")
    if re.search(r"^\s*#\s*if", text, re.M):
        raise PortError(f"{path}: conditional compilation")
    vals = {n: i for i, n in enumerate(names)}
    vals["SCENE_ID_MAX"] = len(names)
    return vals, path


def parse_c_enums(text, where):
    """{enum name: {name: value}} of every `typedef enum { ... } Name;` in C text (comments stripped)"""
    out = {}
    for m in re.finditer(r"typedef\s+enum\s*\w*\s*\{([^}]*)\}\s*(\w+)\s*;", text):
        vals, nxt = {}, 0
        for part in m.group(1).split(","):
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                name, v = [p.strip() for p in part.split("=", 1)]
                nxt = eval_enum_value(v, {"_": vals, **out}, f"{where}: {m.group(2)}")
            else:
                name = part
            if not re.fullmatch(r"[A-Za-z_]\w*", name):
                raise PortError(f"{where}: enum {m.group(2)} item {name!r}")
            vals[name] = nxt
            nxt += 1
        out[m.group(2)] = vals
    return out


def parse_c_array(text, name, where):
    """the values of `<type> name[] = { ... };` (numbers or names)"""
    m = re.search(r"\b" + name + r"\[\]\s*=\s*\{([^}]*)\}", text)
    if not m:
        raise PortError(f"{where}: array {name} not found")
    return [v.strip() for v in m.group(1).split(",") if v.strip()]


def parse_oot_inventory(soh_soh):
    hpath = os.path.join(soh_soh, "include", "z64item.h")
    cpath = os.path.join(soh_soh, "src", "code", "z_inventory.c")
    henums = parse_c_enums(_strip(read(hpath)), "z64item.h")
    ctext = _strip(read(cpath))
    oot = {}
    for e in ("ItemID", "InventorySlot", "UpgradeType", "QuestItem", "DungeonItem", "EquipmentFlag"):
        if e not in henums:
            raise PortError(f"{hpath}: enum {e} not found")
        oot[e] = henums[e]
    slots = parse_c_array(ctext, "gItemSlots", cpath)
    for v in slots:
        if v not in oot["InventorySlot"]:
            raise PortError(f"{cpath}: gItemSlots entry {v!r}")
    oot["gItemSlots"] = slots
    for a in ("gUpgradeMasks", "gUpgradeNegMasks", "gUpgradeShifts"):
        oot[a] = [int(v, 0) for v in parse_c_array(ctext, a, cpath)]
    return oot


def parse_c_enum(text, enum_name, where):
    m = re.search(r"typedef\s+enum\s*\w*\s*\{([^}]*)\}\s*" + enum_name + r"\s*;", text)
    if not m:
        raise PortError(f"{where}: enum {enum_name} not found")
    vals, nxt = {}, 0
    for part in m.group(1).split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            name, v = [p.strip() for p in part.split("=")]
            nxt = int(v, 0)
        else:
            name = part
        vals[name] = nxt
        nxt += 1
    return vals


# ---- declarations

def parse_params(text, where):
    params = []
    if not text.strip() or text.strip() == "void":
        return params
    for arg, _ in split_args(text, 0, lambda o: where):
        arg = " ".join(arg.split())
        default = None
        if "=" in arg:
            arg, default = [p.strip() for p in arg.split("=", 1)]
        m = re.fullmatch(r"(?:const\s+)?([\w:]+)\s*&?\s*(\w+)", arg)
        if not m:
            raise PortError(f"{where}: parameter {arg!r}")
        params.append((m.group(1), m.group(2), default))
    return params


SIMPLE_TYPES = {"bool", "uint8_t", "uint16_t", "uint32_t", "int8_t", "int16_t", "int32_t", "int", "void"}


def parse_logic_h(soh_rando):
    path = os.path.join(soh_rando, "logic.h")
    text = _strip(read(path))
    m = re.search(r"class\s+Logic\s*\{(.*?)\n\s*private:", text, re.S)
    if not m:
        raise PortError(f"{path}: class Logic not found")
    body = m.group(1).replace("public:", "")
    methods, fields, skipped = {}, {}, []
    for stmt in body.split(";"):
        s = " ".join(stmt.split())
        if not s:
            continue
        fm = re.fullmatch(r"([\w:]+)\s+(\w+)(?:\[\w+\])?(?:\s*=\s*(.+))?", s)
        mm = re.fullmatch(r"([\w:]+\*?)\s+(\w+)\((.*)\)", s)
        if mm:
            ret, name, params = mm.groups()
            if ret not in SIMPLE_TYPES and not ret.startswith("Randomizer"):
                skipped.append(s)
                continue
            try:
                methods[name] = (ret, parse_params(params, f"{path}: {name}"))
            except PortError:
                skipped.append(s)   # (a parameter of a type rules cannot pass, e.g. Item&, std::shared_ptr)
        elif fm:
            typ, name, _ = fm.groups()
            if typ in SIMPLE_TYPES or typ.startswith("Randomizer"):
                fields[name] = typ
            else:
                skipped.append(s)
        else:
            skipped.append(s)
    return methods, fields, skipped


def parse_free_functions(soh_rando):
    path = os.path.join(soh_rando, "location_access.h")
    text = _strip(read(path))
    funcs = {}
    for m in re.finditer(r"^(bool|uint16_t|uint8_t)\s+(\w+)\(", text, re.M):
        close = matching(text, m.end() - 1)
        if not text[close + 1:].lstrip().startswith(";"):
            raise PortError(f"{path}: {m.group(2)} is not a declaration")
        funcs[m.group(2)] = (m.group(1), parse_params(text[m.end():close], f"{path}: {m.group(2)}"))
    return funcs


# ---- items

ITEM_SHORT = ["rg", "name", "type", "getItemId", "advancement", "logicVal", "hintKey", "category", "article", "color",
              "price"]
ITEM_LONG = ["rg", "name", "type", "getItemId", "advancement", "logicVal", "hintKey", "itemId", "objectId", "gid",
             "textId", "field", "chestAnimation", "category", "modIndex", "article", "color", "price"]


def parse_items(soh_rando):
    path = os.path.join(soh_rando, "item_list.cpp")
    raw = read(path)
    text = _strip(raw)
    line = line_of(text)
    items = {}
    for m in re.finditer(r"itemTable\[(RG_\w+)\]\s*=\s*Item\(", text):
        close = matching(text, m.end() - 1)
        args = [a.strip() for a, _ in split_args(text[m.end():close], m.end(), lambda o: f"{path}:{line(o)}")]
        where = f"{path}:{line(m.start())}"
        if args[0] != m.group(1):
            raise PortError(f"{where}: Item({args[0]}) stored at {m.group(1)}")
        # (item.h: the two constructors; article, color and price have defaults)
        names = ITEM_SHORT if args[7].startswith("ITEM_CATEGORY") else ITEM_LONG
        if len(args) > len(names) or len(args) < names.index("article"):
            raise PortError(f"{where}: {len(args)} Item arguments")
        d = dict(zip(names, args))
        it = {"type": d["type"], "advancement": {"true": True, "false": False}[d["advancement"]],
              "logicVal": d["logicVal"], "category": d["category"], "getItemId": d["getItemId"]}
        nm = re.match(r'Text\{\s*"((?:[^"\\]|\\.)*)"', d["name"])
        if not nm:
            raise PortError(f"{where}: item name {d['name'][:40]!r}")
        it["name"] = nm.group(1)
        if names is ITEM_LONG:
            it["itemId"] = d["itemId"]
            it["objectId"] = d["objectId"]
            it["modIndex"] = d["modIndex"]
        it["price"] = int(d["price"], 0) if "price" in d else 0
        if m.group(1) in items:
            raise PortError(f"{where}: {m.group(1)} defined twice")
        items[m.group(1)] = it
    if not items:
        raise PortError(f"{path}: no items")
    return items


# ---- locations

# (Location factory overloads, location.h/location.cpp: parameter kinds; fixed fields the factory fills in)
FACTORIES = {
    "Base": [
        (["rc", "quest", "type", "actor", "scene", "params", "str", "str", "hint", "item", "cc?", "bool?", "price?"], {}),
        (["rc", "quest", "type", "actor", "scene", "params", "str", "hint", "item", "cc?", "bool?", "price?"], {}),
        (["rc", "quest", "type", "area", "actor", "scene", "params", "str", "str", "hint", "item", "cc?", "bool?",
          "price?"], {}),
        (["rc", "quest", "type", "area", "actor", "scene", "params", "str", "hint", "item", "cc?", "bool?", "price?"],
         {}),
    ],
    "Chest": [
        (["rc", "quest", "type", "actor", "scene", "params", "flag", "str", "hint", "item", "bool?"], {}),
        (["rc", "quest", "type", "area", "actor", "scene", "params", "flag", "str", "hint", "item", "bool?"], {}),
        (["rc", "quest", "type", "actor", "scene", "params", "str", "hint", "item", "cc", "bool?"], {}),
        (["rc", "quest", "type", "area", "actor", "scene", "params", "str", "hint", "item", "cc", "bool?"], {}),
    ],
    "Collectable": [
        (["rc", "quest", "type", "actor", "scene", "params", "flag", "str", "hint", "item", "bool?"], {}),
        (["rc", "quest", "type", "area", "actor", "scene", "params", "flag", "str", "hint", "item", "bool?"], {}),
        (["rc", "quest", "type", "actor", "scene", "params", "str", "hint", "item", "cc?", "bool?"], {}),
        (["rc", "quest", "type", "area", "actor", "scene", "params", "str", "hint", "item", "cc?", "bool?"], {}),
    ],
    "GSToken": [
        (["rc", "quest", "scene", "params", "flag", "str", "hint"], {"type": "RCTYPE_SKULL_TOKEN",
                                                                      "item": "RG_GOLD_SKULLTULA_TOKEN"}),
        (["rc", "quest", "scene", "params", "flag", "str", "hint", "flag"], {"type": "RCTYPE_SKULL_TOKEN",
                                                                              "item": "RG_GOLD_SKULLTULA_TOKEN"}),
        (["rc", "quest", "area", "scene", "params", "flag", "str", "hint", "flag"],
         {"type": "RCTYPE_SKULL_TOKEN", "item": "RG_GOLD_SKULLTULA_TOKEN"}),
    ],
    "OtherHint": [
        (["rc", "quest", "area", "actor", "scene", "str", "str"], {"type": "RCTYPE_STATIC_HINT", "item": "RG_NONE"}),
        (["rc", "quest", "actor", "scene", "str"], {"type": "RCTYPE_STATIC_HINT", "item": "RG_NONE"}),
        (["rc", "quest", "area", "actor", "scene", "str"], {"type": "RCTYPE_STATIC_HINT", "item": "RG_NONE"}),
    ],
    "HintStone": [
        (["rc", "quest", "scene", "params", "str"], {"type": "RCTYPE_GOSSIP_STONE", "item": "RG_NONE"}),
        (["rc", "quest", "area", "scene", "params", "str"], {"type": "RCTYPE_GOSSIP_STONE", "item": "RG_NONE"}),
    ],
    "Fish": [(["rc", "quest", "actor", "scene", "params", "flag", "str", "hint", "item"], {"type": "RCTYPE_FISH"})],
    "GrottoFish": [(["rc", "quest", "area", "params", "flag", "str", "hint"],
                    {"type": "RCTYPE_FISH", "item": "RG_FISH", "scene": "SCENE_GROTTOS"})],
}
for _f, _t in [("Pot", "RCTYPE_POT"), ("Crate", "RCTYPE_CRATE"), ("NLCrate", "RCTYPE_NLCRATE"),
               ("SmallCrate", "RCTYPE_SMALL_CRATE"), ("Rock", "RCTYPE_ROCK"), ("Tree", "RCTYPE_TREE"),
               ("NLTree", "RCTYPE_NLTREE"), ("Bush", "RCTYPE_BUSH"), ("WonderItem", "RCTYPE_WONDER_ITEM"),
               ("Grass", "RCTYPE_GRASS")]:
    FACTORIES[_f] = [(["rc", "quest", "area", "scene", "params", "str", "hint", "item", "cc"], {"type": _t})]
FACTORIES["Boulder"] = [(["rc", "quest", "area", "scene", "params", "str", "hint", "cc"],
                         {"type": "RCTYPE_BOULDER", "item": "RG_BOMBS_5"})]
FACTORIES["Sign"] = [(["rc", "quest", "area", "scene", "params", "str", "hint", "actor", "cc"],
                      {"type": "RCTYPE_SIGN", "item": "RG_NONE"})]
for _f, _t in [("FountainFairy", "RCTYPE_FOUNTAIN_FAIRY"), ("StoneFairy", "RCTYPE_STONE_FAIRY"),
               ("BeanFairy", "RCTYPE_BEAN_FAIRY"), ("SongFairy", "RCTYPE_SONG_FAIRY"),
               ("ButterflyFairy", "RCTYPE_BUTTERFLY_FAIRY"), ("Icicle", "RCTYPE_ICICLE"),
               ("RedIce", "RCTYPE_RED_ICE"), ("FireGoron", "RCTYPE_FIRE_GORON")]:
    FACTORIES[_f] = [(["rc", "quest", "area", "scene", "params", "str", "hint", "cc"], {"type": _t, "item": "RG_NONE"})]


def _arg_kind(a):
    a = a.strip()
    if a.startswith('"'):
        return "str"
    if a.startswith("SpoilerCollectionCheck"):
        return "cc"
    if a in ("true", "false"):
        return "bool"
    for p, k in (("RCQUEST_", "quest"), ("RCTYPE_", "type"), ("RCAREA_", "area"), ("ACTOR_", "actor"),
                 ("SCENE_", "scene"), ("RHT_", "hint"), ("RG_", "item"), ("RC_", "rc"), ("RAND_INF_", "flag")):
        if a.startswith(p):
            return k
    # (actor params / flags: a constant expression of numbers, TWO_ACTOR_PARAMS(...), TEXT_* ids)
    words = re.findall(r"[A-Za-z_]\w*", re.sub(r"\b0[xX][0-9a-fA-F]+", "0", a))
    if re.fullmatch(r"[-+*/^|&~()\s\w,]+", a) and all(w == "TWO_ACTOR_PARAMS" or w.startswith("TEXT_")
                                                       for w in words):
        return "num"
    return "?" + a


def _fits(kind, param):
    p = param.rstrip("?")
    if p == kind:
        return True
    if kind == "num":
        return p in ("params", "flag", "price")
    if kind == "flag":
        return p == "flag"
    return False


def resolve_factory(fname, args, where):
    kinds = [_arg_kind(a) for a in args]
    for k in kinds:
        if k.startswith("?"):
            raise PortError(f"{where}: Location::{fname} argument {k[1:]!r} of unknown kind")
    found = []
    for params, fixed in FACTORIES.get(fname, []):
        need = sum(1 for p in params if not p.endswith("?"))
        if not (need <= len(args) <= len(params)):
            continue
        if all(_fits(k, p) for k, p in zip(kinds, params)):
            found.append((params, fixed))
    if fname not in FACTORIES:
        raise PortError(f"{where}: unknown factory Location::{fname}")
    if len(found) != 1:
        raise PortError(f"{where}: Location::{fname}{tuple(kinds)} matches {len(found)} overloads")
    params, fixed = found[0]
    loc = dict(fixed)
    for a, p in zip(args, params):
        p = p.rstrip("?")
        if p in ("rc", "quest", "type", "scene", "item", "area") and p not in fixed:
            loc[p] = a.strip()
        elif p == "price":
            loc["price"] = int(a.strip(), 0)
    loc.setdefault("price", 0)
    for k in ("rc", "quest", "type", "scene", "item"):
        if k not in loc:
            raise PortError(f"{where}: Location::{fname}: no {k}")
    return loc


def parse_locations(soh_rando):
    locs = {}
    files = []
    for fn in sorted(os.listdir(soh_rando)):
        if not fn.endswith(".cpp"):
            continue
        path = os.path.join(soh_rando, fn)
        text = _strip(read(path))
        if "locationTable[RC_" not in text:
            continue
        files.append(fn)
        line = line_of(text)
        for m in re.finditer(r"locationTable\[(RC_\w+)\]\s*=\s*Location::(\w+)\(", text):
            close = matching(text, m.end() - 1)
            where = f"{fn}:{line(m.start())}"
            args = [a for a, _ in split_args(text[m.end():close], m.end(), lambda o: f"{fn}:{line(o)}")]
            loc = resolve_factory(m.group(2), args, where)
            if loc["rc"] != m.group(1):
                raise PortError(f"{where}: Location({loc['rc']}) stored at {m.group(1)}")
            if loc["rc"] in locs:
                raise PortError(f"{where}: {loc['rc']} defined twice ({locs[loc['rc']]['file']})")
            loc["file"] = where
            locs[loc["rc"]] = loc
        if len(re.findall(r"locationTable\[RC_", text)) != len([1 for _ in re.finditer(
                r"locationTable\[(RC_\w+)\]\s*=\s*Location::(\w+)\(", text)]):
            raise PortError(f"{fn}: a locationTable[RC_] use that is not `= Location::F(...)`")
    return locs, files


# ---- time pass (location_access.cpp GetTimePassFromScene)

def parse_time_pass(soh_rando, scenes):
    path = os.path.join(soh_rando, "location_access.cpp")
    text = _strip(read(path))
    m = re.search(r"bool GetTimePassFromScene\(SceneID scene\)\s*\{", text)
    body = text[m.end():matching(text, m.end() - 1, "{", "}")]
    out, pending = {}, []
    for t in re.finditer(r"case\s+(SCENE_\w+)\s*:|default\s*:|return\s+(true|false)\s*;|assert\([^)]*\)\s*;", body):
        if t.group(1):
            pending.append(t.group(1))
        elif t.group(2):
            for s in pending:
                out[s] = t.group(2) == "true"
            pending = []
    missing = [s for s in scenes if s not in out]
    return out, missing


# ---- the region files

def region_files(soh_rando):
    la = os.path.join(soh_rando, "location_access")
    files = [os.path.join(la, "root.cpp")]
    for sub in ("overworld", "dungeons"):
        d = os.path.join(la, sub)
        files += [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".cpp")]
    return files


TRAILING_SEMICOLONS = []   # (rules written `cond;` inside the macro: see Rule)


class Rule:
    def __init__(self, cpp, where, line, macro=False):
        cpp = " ".join(cpp.split())
        # (EVENT_ACCESS/LOCATION/ENTRANCE expand the condition into `[] { return condition; }`: a condition written
        #  with a trailing `;` is `return cond;;`, the extra `;` an empty statement; nothing else may follow it)
        if macro and cpp.endswith(";"):
            stripped = cpp.rstrip(";").rstrip()
            if ";" in stripped:
                raise PortError(f"{where}:{line}: statements in a rule: {cpp}")
            TRAILING_SEMICOLONS.append(f"{where}:{line}")
            cpp = stripped
        self.cpp = cpp
        self.where = where
        self.line = line


def parse_macro_list(text, base, where, line, macro, fname):
    """[(first arg, Rule, extra args)] of `{ MACRO(a, cond[, ...]), ... }`"""
    t = text.strip()
    if not (t.startswith("{") and t.endswith("}")):
        raise PortError(f"{where(base)}: expected {{...}} list of {macro}, found {t[:40]!r}")
    inner_off = base + text.index("{") + 1
    inner = text[text.index("{") + 1:text.rindex("}")]
    out = []
    pos = 0
    for m in re.finditer(r"\b(\w+)\s*\(", inner):
        if m.start() < pos:
            continue
        gap = inner[pos:m.start()].strip().strip(",").strip()
        if gap:
            raise PortError(f"{where(inner_off + pos)}: unexpected {gap[:40]!r} in {macro} list")
        if m.group(1) != macro:
            raise PortError(f"{where(inner_off + m.start())}: {m.group(1)}(...) in a {macro} list")
        close = matching(inner, m.end() - 1)
        args = split_args(inner[m.end():close], inner_off + m.end(), where, protect="(")
        if len(args) < 2:
            raise PortError(f"{where(inner_off + m.start())}: {macro} with {len(args)} arguments")
        first = args[0][0].strip()
        cond_text, cond_off = args[1]
        if macro in ("EVENT_ACCESS", "LOCATION") and len(args) != 2:
            raise PortError(f"{where(inner_off + m.start())}: {macro} with {len(args)} arguments")
        if macro == "ENTRANCE" and len(args) > 3:
            raise PortError(f"{where(inner_off + m.start())}: ENTRANCE with {len(args)} arguments")
        extra = [a.strip() for a, _ in args[2:]]
        out.append((first, Rule(cond_text, fname, line(cond_off + len(cond_text) - len(cond_text.lstrip())), True),
                    extra))
        pos = close + 1
    rest = inner[pos:].strip().strip(",").strip()
    if rest:
        raise PortError(f"{where(inner_off + pos)}: unexpected {rest[:40]!r} in {macro} list")
    return out


def parse_region_file(path, soh_rando, grotto_events):
    raw = read(path)
    text = _strip(raw)
    line = line_of(text)
    fname = os.path.relpath(path, soh_rando).replace("\\", "/")

    def where(off):
        return f"{fname}:{line(off)}"

    # pragma blocks: (start offset, end offset, kind)
    blocks, stack = [], []
    for m in re.finditer(r"^\s*#pragma\s+(region\b(.*)|endregion\b.*)$", text, re.M):
        if m.group(1).startswith("region"):
            stack.append((m.start(), m.group(2).strip()))
        else:
            if not stack:
                raise PortError(f"{where(m.start())}: #pragma endregion without region")
            s, kind = stack.pop()
            blocks.append((s, m.start(), kind))
    if stack:
        raise PortError(f"{fname}: unclosed #pragma region")
    for m in re.finditer(r"^\s*#\s*(if|ifdef|ifndef|define)\b.*$", text, re.M):
        raise PortError(f"{where(m.start())}: preprocessor {m.group().strip()!r}")

    regions = []
    starts = [m for m in re.finditer(r"areaTable\[(RR_\w+)\]\s*=\s*Region\(", text)]
    if len(starts) != len(re.findall(r"areaTable\[", text)):
        raise PortError(f"{fname}: an areaTable use that is not `areaTable[RR_X] = Region(...)`")
    for m in starts:
        rr = m.group(1)
        close = matching(text, m.end() - 1)
        if not text[close + 1:].lstrip().startswith(";"):
            raise PortError(f"{where(close)}: expected ; after Region(...)")
        args = split_args(text[m.end():close], m.end(), where, protect="([{")
        vals = [a.strip() for a, _ in args]
        nm = re.fullmatch(r'"((?:[^"\\]|\\.)*)"', vals[0])
        if not nm:
            raise PortError(f"{where(m.start())}: region name {vals[0][:40]!r}")
        scene = vals[1]
        if len(args) == 7:
            tp = {"TIME_PASSES": True, "TIME_DOESNT_PASS": False}.get(vals[2])
            if tp is None:
                raise PortError(f"{where(args[2][1])}: time pass {vals[2]!r}")
            areas = re.findall(r"RA_\w+", vals[3])
            ev, lo, ex = args[4], args[5], args[6]
        elif len(args) == 5:
            tp, areas = None, None
            ev, lo, ex = args[2], args[3], args[4]
        else:
            raise PortError(f"{where(m.start())}: Region with {len(args)} arguments")
        if ev[0].strip() == "grottoEvents":
            events = list(grotto_events)
            grotto = True
        else:
            events = [(a, r) for a, r, _ in parse_macro_list(ev[0], ev[1], where, line, "EVENT_ACCESS", fname)]
            grotto = False
        locations = [(a, r) for a, r, _ in parse_macro_list(lo[0], lo[1], where, line, "LOCATION", fname)]
        exits = [(a, r, x) for a, r, x in parse_macro_list(ex[0], ex[1], where, line, "ENTRANCE", fname)]
        block = None
        for s, e, kind in blocks:
            if s <= m.start() < e:
                block = kind if block is None else block + "/" + kind
        regions.append({"rr": rr, "name": nm.group(1), "scene": scene, "time_pass": tp, "areas": areas,
                        "events": events, "grotto_events": grotto, "locations": locations, "exits": exits,
                        "where": where(m.start()), "block": block, "file": fname})
    init = re.findall(r"^void\s+(RegionTable_Init_\w+)\s*\(\)", text, re.M)
    return regions, init


def parse_location_access_cpp(soh_rando):
    """grottoEvents, spiritLogicData, and the Init functions RegionTable_Init calls"""
    path = os.path.join(soh_rando, "location_access.cpp")
    text = _strip(read(path))
    line = line_of(text)

    def where(off):
        return f"location_access.cpp:{line(off)}"

    m = re.search(r"grottoEvents\s*=\s*\{", text)
    close = matching(text, m.end() - 1, "{", "}")
    grotto = [(a, r) for a, r, _ in parse_macro_list(text[m.end() - 1:close + 1], m.end() - 1, where, line,
                                                      "EVENT_ACCESS", "location_access.cpp")]
    m = re.search(r"Region::spiritLogicData\s*=\s*\{", text)
    close = matching(text, m.end() - 1, "{", "}")
    body = text[m.end():close]
    spirit = []
    for e, off in split_args(body, m.end(), where, protect="([{"):
        e2 = e.strip()
        em = re.fullmatch(r"\{\s*(RR_\w+)\s*,\s*\{(.*)\}\s*\}", e2, re.S)
        if not em:
            raise PortError(f"{where(off)}: spiritLogicData entry {e2[:50]!r}")
        inner_off = off + e.index(em.group(2))
        fields = split_args(em.group(2), inner_off, where, protect="([{")
        if len(fields) != 7:
            raise PortError(f"{where(off)}: spiritLogicData entry with {len(fields)} fields")
        keys = [int(f.strip(), 0) for f, _ in fields[:4]]
        fns = []
        for f, foff in fields[4:]:
            lm = re.fullmatch(r"\s*\[\]\s*\{\s*return\s+(.*);\s*\}\s*", f, re.S)
            if not lm:
                raise PortError(f"{where(foff)}: spiritLogicData condition {f.strip()[:50]!r} is not "
                                f"[]{{return <expr>;}}")
            fns.append(Rule(lm.group(1), "location_access.cpp", line(foff + f.index(lm.group(1)))))
        spirit.append((em.group(1), keys, fns, where(off)))
    m = re.search(r"void RegionTable_Init\(\)\s*\{", text)
    close = matching(text, m.end() - 1, "{", "}")
    calls = re.findall(r"\b(RegionTable_Init_\w+)\(\)\s*;", text[m.end():close])
    return grotto, spirit, calls


def is_mq(rr):
    return "_MQ_" in rr or rr.endswith("_MQ")


def conj_terms(ast):
    if ast[0] == "bin" and ast[1] == "&&":
        return conj_terms(ast[2]) + conj_terms(ast[3])
    return [ast]


def is_ismq_term(t):
    # ctx->GetDungeon(X)->IsMQ()
    return (t[0] == "call" and t[1][0] == "member" and t[1][3] == "IsMQ" and not t[2]
            and t[1][1][0] == "call" and t[1][1][1][0] == "member" and t[1][1][1][3] == "GetDungeon"
            and t[1][1][1][1] == ("id", "ctx", t[1][1][1][1][2]))


# ---- output

def py_str(s):
    return repr(s)


def write_data(out, commit, enums, scenes, dungeon_keys, methods, fields, skipped, funcs, items, locs, loc_files,
               time_pass, oot):
    L = []
    w = L.append
    w(f'"""GENERATED by {TOOL} from Ship of Harkinian (Shipwright) commit {commit}: do not edit.')
    w("")
    w("SoH's enums, declarations, item table and location table, as the logic port needs them.")
    w('"""')
    w("")
    w(f"SOH_COMMIT = {commit!r}")
    w("")
    w("# {enum type: {name: value}} (randomizerEnums/*.h; SceneID from include/tables/scene_table.h; DungeonKey from")
    w("# dungeon.h)")
    w("ENUMS = {")
    for et in enums:
        w(f"    {et!r}: {{")
        for name, val in enums[et].items():
            w(f"        {name!r}: {val},")
        w("    },")
    w("    'SceneID': {")
    for name, val in scenes.items():
        w(f"        {name!r}: {val},")
    w("    },")
    w("    'DungeonKey': {")
    for name, val in dungeon_keys.items():
        w(f"        {name!r}: {val},")
    w("    },")
    w("}")
    w("ENUM_TYPES = set(ENUMS)")
    w("ENUM_OF = {n: t for t, vals in ENUMS.items() for n in vals}")
    w("ENUM_VALUE = {n: v for vals in ENUMS.values() for n, v in vals.items()}")
    w("")
    w("# Logic (logic.h): {name: (return type, [(param type, param name, default C++ text or None)])}")
    w("LOGIC_METHODS = {")
    for n, (ret, ps) in methods.items():
        w(f"    {n!r}: ({ret!r}, {ps!r}),")
    w("}")
    w("LOGIC_FIELDS = {")
    for n, t in fields.items():
        w(f"    {n!r}: {t!r},")
    w("}")
    w(f"LOGIC_H_SKIPPED = {skipped!r}   # (logic.h members not usable from rules: not simple types)")
    w("")
    w("# free functions rules call (location_access.h)")
    w("FREE_FUNCTIONS = {")
    for n, (ret, ps) in funcs.items():
        w(f"    {n!r}: ({ret!r}, {ps!r}),")
    w("}")
    w("")
    w("# item_list.cpp: {RG: {type, advancement, logicVal, category, name, itemId/objectId/modIndex (when the Item has")
    w("# a GetItemEntry), price}}")
    w("ITEMS = {")
    for rg, it in items.items():
        w(f"    {rg!r}: {it!r},")
    w("}")
    w("")
    w(f"# the location tables ({', '.join(loc_files)}): {{RC: {{quest, type, scene, item (vanilla), price")
    w("# (vanilla), area, file}}}")
    w("LOCATIONS = {")
    for rc, loc in locs.items():
        w(f"    {rc!r}: {loc!r},")
    w("}")
    w("")
    w("# location_access.cpp GetTimePassFromScene: {scene: time passes}")
    w(f"SCENE_TIME_PASS = {time_pass!r}")
    w("")
    w("# OoT's inventory layout the Logic's save context indexes (include/z64item.h enums; src/code/z_inventory.c")
    w("# gItemSlots, gUpgradeMasks, gUpgradeNegMasks, gUpgradeShifts)")
    w("OOT = {")
    for k, v in oot.items():
        w(f"    {k!r}: {v!r},")
    w("}")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--soh", default=os.path.join(os.path.dirname(ROOT), "Shipwright"),
                    help="the Shipwright checkout (default: ../Shipwright)")
    args = ap.parse_args(argv)
    soh_root = args.soh
    soh_rando = os.path.join(soh_root, "soh", "soh", "Enhancements", "randomizer")
    try:
        commit = subprocess.run(["git", "-C", soh_root, "rev-parse", "HEAD"], capture_output=True, text=True,
                                check=True).stdout.strip()
        dirty = subprocess.run(["git", "-C", soh_root, "status", "--porcelain", "--", "soh/soh/Enhancements",
                                "soh/include"], capture_output=True, text=True, check=True).stdout.strip()
        if dirty:
            commit += " (with local changes)"
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown (not a git checkout)"

    enums = parse_rando_enums(soh_rando)
    scenes, _ = parse_scenes(os.path.join(soh_root, "soh"))
    dungeon_keys = parse_c_enum(_strip(read(os.path.join(soh_rando, "dungeon.h"))), "DungeonKey", "dungeon.h")
    clash = set()
    seen = {}
    for et, vals in list(enums.items()) + [("SceneID", scenes), ("DungeonKey", dungeon_keys)]:
        for n in vals:
            if n in seen and seen[n] != et:
                clash.add((n, seen[n], et))
            seen[n] = et
    if clash:
        raise PortError(f"enum names in two enums: {sorted(clash)[:5]}")
    methods, fields, skipped = parse_logic_h(soh_rando)
    funcs = parse_free_functions(soh_rando)
    items = parse_items(soh_rando)
    locs, loc_files = parse_locations(soh_rando)
    time_pass, tp_missing = parse_time_pass(soh_rando, scenes)
    oot = parse_oot_inventory(os.path.join(soh_root, "soh"))
    write_data(OUT_DATA, commit, enums, scenes, dungeon_keys, methods, fields, skipped, funcs, items, locs,
               loc_files, time_pass, oot)

    # (translate imports the soh_data just written)
    import importlib
    import rando.logic.soh_data
    importlib.reload(rando.logic.soh_data)
    from rando.logic import translate
    importlib.reload(translate)

    grotto, spirit, init_calls = parse_location_access_cpp(soh_rando)
    regions, inits = [], []
    for path in region_files(soh_rando):
        rs, ins = parse_region_file(path, soh_rando, grotto)
        regions += rs
        inits += ins
    if sorted(init_calls) != sorted(inits):
        raise PortError(f"RegionTable_Init calls {sorted(set(init_calls) ^ set(inits))} not matching the region "
                        f"files' Init functions")
    by_rr = {}
    for r in regions:
        if r["rr"] in by_rr:
            raise PortError(f"{r['where']}: {r['rr']} assigned twice (also {by_rr[r['rr']]['where']})")
        if r["rr"] not in rando.logic.soh_data.ENUM_OF or rando.logic.soh_data.ENUM_OF[r["rr"]] != "RandomizerRegion":
            raise PortError(f"{r['where']}: {r['rr']} is not a RandomizerRegion")
        if r["scene"] not in scenes:
            raise PortError(f"{r['where']}: unknown scene {r['scene']}")
        by_rr[r["rr"]] = r

    # MQ rule checks
    for r in regions:
        b = r["block"] or ""
        if "MQ" in b.split("/") and not is_mq(r["rr"]):
            raise PortError(f"{r['where']}: {r['rr']} inside #pragma region MQ is not MQ-named")
        if "Vanilla" in b.split("/") and is_mq(r["rr"]):
            raise PortError(f"{r['where']}: {r['rr']} inside #pragma region Vanilla is MQ-named")

    # translate everything (MQ too, to know the translator handles all of SoH)
    stats = {"rules": 0, "rules_mq": 0, "dropped_exits": [], "dropped_locations": 0}
    tr = {}

    def tr_rule(rule, mq):
        key = (rule.where, rule.line, rule.cpp)
        if key not in tr:
            ast = translate.parse(rule.cpp, rule.where, rule.line)
            text = translate.cpp_to_py(rule.cpp, rule.where, rule.line)
            tr[key] = (ast, text)
            stats["rules_mq" if mq else "rules"] += 1
        return tr[key]

    for r in regions:
        mq = is_mq(r["rr"])
        for kind in ("events", "locations", "exits"):
            for ent in r[kind]:
                tr_rule(ent[1], mq)
        for name, _ in r["events"]:
            if rando.logic.soh_data.ENUM_OF.get(name) != "LogicVal":
                raise PortError(f"{r['where']}: event {name} is not a LogicVal")
        for rc, rule in r["locations"]:
            if rc not in locs:
                raise PortError(f"{rule.where}:{rule.line}: {rc} not in the location tables")
            if not mq and locs[rc]["quest"] == "RCQUEST_MQ":
                raise PortError(f"{rule.where}:{rule.line}: MQ location {rc} in vanilla region {r['rr']}")
        for to, rule, _ in r["exits"]:
            if to not in by_rr:
                raise PortError(f"{rule.where}:{rule.line}: exit to {to}, a region no file defines")
    for rr, keys, fns, wh in spirit:
        for f in fns:
            tr_rule(f, is_mq(rr))

    # the vanilla graph
    out_regions = []
    for r in regions:
        if is_mq(r["rr"]):
            stats["dropped_locations"] += len(r["locations"])
            continue
        exits = []
        for to, rule, extra in r["exits"]:
            ast, text = tr[(rule.where, rule.line, rule.cpp)]
            if is_mq(to):
                if not any(is_ismq_term(t) for t in conj_terms(ast)):
                    raise PortError(f"{rule.where}:{rule.line}: exit {r['rr']} -> MQ region {to} not conditioned on "
                                    f"IsMQ(): {rule.cpp}")
                stats["dropped_exits"].append((r["rr"], to, rule.cpp))
                continue
            exits.append((to, rule, text, extra))
        out_regions.append((r, exits))
    tp_needed = sorted({r["scene"] for r, _ in out_regions if r["time_pass"] is None} - set(time_pass))
    if tp_needed:
        raise PortError(f"GetTimePassFromScene has no case for {tp_needed}")

    write_regions(OUT_REGIONS, commit, out_regions, spirit, tr, time_pass, stats)
    print(f"soh_data.py: {len(items)} items, {len(locs)} locations, {sum(len(v) for v in enums.values())} enum values")
    print(f"soh_regions.py: {len(out_regions)} vanilla regions ({len(regions) - len(out_regions)} MQ left out); "
          f"{stats['rules']} vanilla rules + {stats['rules_mq']} MQ rules translated, 0 untranslated")
    print(f"  {len(stats['dropped_exits'])} exits into MQ regions dropped, {stats['dropped_locations']} MQ region "
          f"location entries dropped")
    return stats


def write_regions(out, commit, out_regions, spirit, tr, time_pass, stats):
    L = []
    w = L.append
    w(f'"""GENERATED by {TOOL} from Ship of Harkinian (Shipwright) commit {commit}: do not edit.')
    w("")
    w("SoH's randomizer region graph (soh/Enhancements/randomizer/location_access/), Master Quest left out (see the")
    w("tool for the rule), every rule translated by rando.logic.translate. Each rule: (Python function of (L, C, F),")
    w("the C++ text, 'file:line').")
    w("")
    w("REGIONS: {RR: {name, scene, time_pass, events: [(LOGIC, rule)], locations: [(RC, rule)],")
    w("                exits: [(RR, rule)]}}")
    w("SPIRIT_LOGIC_DATA: {RR: (childKeys, childRevKeys, adultKeys, adultRevKeys, childAccess, adultAccess,")
    w("                         reverseAccess)} (location_access.cpp Region::spiritLogicData)")
    w('"""')
    w("from .translate import _cdiv, _cmod  # noqa: F401  (used by translated division, if any)")
    w("")
    w(f"SOH_COMMIT = {commit!r}")
    w(f"RULE_COUNT = {stats['rules']}")
    w(f"MQ_EXITS_DROPPED = {[(a, b) for a, b, _ in stats['dropped_exits']]!r}")
    w("")

    def rule_text(rule, ind):
        _, text = tr[(rule.where, rule.line, rule.cpp)]
        return f"(lambda L, C, F: {text},\n{ind} {rule.cpp!r}, '{rule.where}:{rule.line}')"

    w("REGIONS = {")
    for r, exits in out_regions:
        tp = r["time_pass"] if r["time_pass"] is not None else time_pass[r["scene"]]
        w(f"    {r['rr']!r}: {{")
        w(f"        'name': {r['name']!r}, 'scene': {r['scene']!r}, 'time_pass': {tp!r}, "
          f"'where': {r['where']!r},")
        w(f"        'grotto_events': {r['grotto_events']!r},")
        w("        'events': [")
        for ev, rule in r["events"]:
            w(f"            ({ev!r}, {rule_text(rule, '             ')}),")
        w("        ],")
        w("        'locations': [")
        for rc, rule in r["locations"]:
            w(f"            ({rc!r}, {rule_text(rule, '             ')}),")
        w("        ],")
        w("        'exits': [")
        for to, rule, text, extra in exits:
            w(f"            ({to!r}, {rule_text(rule, '             ')}),")
        w("        ],")
        w("    },")
    w("}")
    w("")
    w("SPIRIT_LOGIC_DATA = {")
    for rr, keys, fns, wh in spirit:
        if is_mq(rr):
            continue
        w(f"    {rr!r}: ({keys[0]}, {keys[1]}, {keys[2]}, {keys[3]},  # {wh}")
        for f in fns:
            w(f"        {rule_text(f, '        ')},")
        w("    ),")
    w("}")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    try:
        main()
    except PortError as e:
        sys.exit(f"port_soh_logic: error: {e}")
    except Exception as e:  # (translate.TranslateError and the like: still an error naming the place)
        if type(e).__name__ == "TranslateError":
            sys.exit(f"port_soh_logic: untranslated construct: {e}")
        raise
