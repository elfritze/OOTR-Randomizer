"""Check rando/logic/logic.py (a hand port) against SoH's logic.cpp, mechanically.

Each Logic method of logic.cpp is parsed (a small C++ statement subset: blocks, return, if/else, switch/case with
fallthrough and break, local declarations and assignments, logging and asserts) and interpreted with C++ semantics;
the Python method runs on the same inputs. Every other call either side makes (other Logic methods, ctx options,
tricks, dungeons, the save context fields) is answered by the same deterministic pseudo-random environment, keyed by
the call and its arguments (enum names as their values, defaults filled in from logic.h), so the two must agree call
for call. Each method runs on every value of its enum parameters (RG_*, RE_*, ED_*, ...) and both bools, in two
environments: options random (every branch) and options as logic.SETTINGS with tricks off.

Also compared: logic.py's tables (equip flags, rand inf, dungeon scenes, quest items, bottles, the hookshot and
ocarina steps, the item-use sets) with logic.cpp's."""
import itertools
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from rando.logic import logic as LG          # noqa: E402
from rando.logic import soh_data as D        # noqa: E402
from rando.logic import translate as T       # noqa: E402

SOH = os.path.join(os.path.dirname(os.path.dirname(HERE)), "Shipwright", "soh", "soh", "Enhancements", "randomizer")

VALUE = dict(D.ENUM_VALUE)
for _e in ("ItemID", "InventorySlot", "UpgradeType", "QuestItem", "DungeonItem", "EquipmentFlag"):
    VALUE.update(D.OOT[_e])
VALUE["UINT16_MAX"] = 0xFFFF
VALUE["FULL_HEART_HEALTH"] = 16
NAME_OF = {}
for _t, _vals in D.ENUMS.items():
    for _n, _v in _vals.items():
        NAME_OF.setdefault((_t, _v), _n)

# (methods not checked here: state, not expressions of the inputs (save context writes, Reset), loops or pointers
#  this interpreter does not run; each is a few lines, ported by hand and read against logic.cpp)
SKIP = {"ApplyItemEffect", "Reset", "SetContext", "GetSaveContext", "SetSaveContext", "InitSaveContext",
        "NewSaveContext", "InventorySlot", "SetUpgrade", "CurrentUpgrade", "CurrentInventory", "CheckInventory",
        "SetInventory", "CheckEquipment", "CheckQuestItem", "SetQuestItem", "GetSmallKeyCount", "SetSmallKeyCount",
        "CheckDungeonItem", "SetDungeonItem", "CheckRandoInf", "SetRandoInf", "CheckEventChkInf", "SetEventChkInf",
        "GetGSCount", "GetTriforcePieceCount", "GetAmmo", "SetAmmo", "Get", "Set", "BottleCount", "BeanPlanted",
        "HasProjectile", "Logic"}


class Unsupported(Exception):
    pass


class Assert(Exception):
    pass


class _Return(Exception):
    def __init__(self, v):
        self.v = v


class _Break(Exception):
    pass


# ---- parsing logic.cpp

class _StmtParser(T._Parser):
    DECL = {"bool", "uint8_t", "uint16_t", "uint32_t", "int8_t", "int16_t", "int32_t", "int", "auto", "s8",
            "RandomizerGet", "u8", "u16"}

    def unary(self):
        tok = self.peek()
        if tok[0] == "op" and tok[1] in ("*", "&"):
            self.i += 1
            return ("un", tok[1], self.unary(), tok[2])
        return super().unary()

    def block(self):
        self.take("{")
        out = []
        while not self.at("}"):
            out.append(self.stmt())
        self.take("}")
        return ("block", out)

    def stmt(self):
        tok = self.peek()
        v = tok[1]
        if tok[0] == "op" and v == "{":
            return self.block()
        if tok[0] == "op" and v == ";":
            self.i += 1
            return ("nop",)
        if tok[0] == "op" and v == "[" and self.peek(1)[1] == "[":
            while not self.at(";"):
                self.i += 1
            self.i += 1
            return ("nop",)
        if tok[0] == "id":
            if v == "return":
                self.i += 1
                if self.at(";"):
                    self.i += 1
                    return ("return", None)
                e = self.expr()
                self.take(";")
                return ("return", e)
            if v == "if":
                self.i += 1
                self.take("(")
                c = self.expr()
                self.take(")")
                a = self.stmt()
                b = None
                if self.at("else"):
                    self.i += 1
                    b = self.stmt()
                return ("if", c, a, b)
            if v == "switch":
                self.i += 1
                self.take("(")
                c = self.expr()
                self.take(")")
                self.take("{")
                items = []
                while not self.at("}"):
                    if self.at("case"):
                        self.i += 1
                        items.append(("case", self.expr()))
                        self.take(":")
                    elif self.at("default"):
                        self.i += 1
                        self.take(":")
                        items.append(("default",))
                    else:
                        items.append(self.stmt())
                self.take("}")
                return ("switch", c, items)
            if v == "break":
                self.i += 1
                self.take(";")
                return ("break",)
            if v in ("SPDLOG_ERROR", "SPDLOG_INFO", "SPDLOG_DEBUG", "StartPerformanceTimer",
                     "StopPerformanceTimer"):
                self.i += 1
                self.take("(")
                depth = 1
                while depth:
                    t = self.take()
                    depth += {"(": 1, ")": -1}.get(t[1], 0)
                self.take(";")
                return ("nop",)
            if v == "assert":
                self.i += 1
                self.take("(")
                e = self.expr()
                self.take(")")
                self.take(";")
                return ("assert", e)
            if v in ("for", "while", "do", "goto"):
                raise T.TranslateError(f"line {tok[2]}: {v} loop")
            if v in self.DECL and self.peek(1)[0] == "id":
                self.i += 1
                name = self.take(kind="id")[1]
                e = None
                if self.at("="):
                    self.i += 1
                    e = self.expr()
                self.take(";")
                return ("decl", name, e)
            if self.peek(1)[1] == "=" and self.peek(2)[1] != "=":
                name = v
                self.i += 2
                e = self.expr()
                self.take(";")
                return ("assign", name, e)
        e = self.expr()
        self.take(";")
        return ("expr", e)


def parse_methods():
    text = T.strip_comments(open(os.path.join(SOH, "logic.cpp"), encoding="utf-8").read())
    out = {}
    for m in re.finditer(r"^[\w:<>* ]+?\bLogic::(\w+)\(([^)]*)\)\s*\{", text, re.M):
        name = m.group(1)
        start = m.end() - 1
        depth, i = 0, start
        while True:
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = text[start:i + 1]
        line = text.count("\n", 0, start) + 1
        try:
            toks = T.tokenize(body, line, "logic.cpp")
            p = _StmtParser(toks, "logic.cpp")
            out[name] = ("ok", p.block(), line)
        except T.TranslateError as e:
            out[name] = ("unparsed", str(e), line)
    return out, text


def parse_tables(text):
    """logic.cpp's static tables: {name: {key: value}} and its sets"""
    tables = {}
    for name in ("equipFlagTable", "randInfTable", "dungeonSceneTable", "questItemTable"):
        m = re.search(name + r"\[\]\s*=\s*\{(.*?)\};", text, re.S)
        tables[name] = dict(re.findall(r"\{\s*(\w+)\s*,\s*(\w+)\s*\}", m.group(1)))
    m = re.search(r"BottleRandomizerGetToItemID\s*=\s*\{(.*?)\};", text, re.S)
    tables["BottleRandomizerGetToItemID"] = dict(re.findall(r"\{\s*(\w+)\s*,\s*(\w+)\s*\}", m.group(1)))
    for name in ("HookshotLookup", "OcarinaLookup"):
        m = re.search(name + r"\[3\]\s*=\s*\{([^}]*)\}", text)
        tables[name] = [v.strip() for v in m.group(1).split(",")]
    sets = {}
    for m in re.finditer(r"std::set<RandomizerGet>\s+StaticData::(\w+)\s*=\s*\{([^}]*)\}", text):
        sets[m.group(1)] = set(re.findall(r"RG_\w+", m.group(2)))
    return tables, sets


# ---- the environment both sides read

class Env:
    INTS = [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 16, 17, 24, 25, 32, 48, 64, 100, 0xFFFF]

    # (P(true) of a call: OR chains need most calls false to show a missing term, AND chains most true)
    BIAS = [0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 0.65, 0.8, 0.9, 0.95, 0.98]

    def __init__(self, seed, fixed):
        self.seed = seed
        self.fixed = fixed
        self.p = self.BIAS[hash(("bias", seed)) % len(self.BIAS)]

    def b(self, *key):
        return (self.h(*key) % 10007) < self.p * 10007

    def h(self, *key):
        return hash((self.seed,) + key)

    def method(self, name, args):
        ret, params = D.LOGIC_METHODS[name]
        key = norm_args(name, args)
        if T.type_kind(ret) == "bool":
            return self.b("L", name, key)
        if ret.startswith("Randomizer"):
            raise Unsupported(f"{name} returns {ret}")
        return self.INTS[self.h("L", name, key) % len(self.INTS)]

    def field(self, name):
        if name == "CurrentRegionKey":
            return ["RR_NONE", "RR_LH_LAB_UNDERWATER", "RR_KOKIRI_FOREST"][self.h("F", name) % 3]
        if name == "CalculatingAvailableChecks":
            return False
        if D.LOGIC_FIELDS[name] == "bool":
            return self.b("F", name)
        return self.INTS[self.h("F", name) % len(self.INTS)]

    def option(self, name):
        if self.fixed:
            if name.startswith("RT_"):
                return Opt(0)
            return Opt(LG._value(LG.SETTINGS[name]))
        return Opt([0, 0, 1, 2, 3, 10][self.h("O", name) % 6])

    def bit(self, *key):
        if self.fixed and key[0] == "DM":
            return False
        if self.fixed and key[0] == "DV":
            return True
        return self.b(*key)

    def save(self, name):
        return self.INTS[self.h("S", name) % len(self.INTS)] if name != "bgsFlag" else self.h("S", name) & 1

    def scene(self):
        scenes = sorted(D.ENUMS["SceneID"])
        return scenes[self.h("scene") % len(scenes)]

    def condition(self, name):
        if self.fixed:
            return {"GBKCondition": LG.GBK_CONDITION, "GanonsSoulCondition": LG.GANONS_SOUL_CONDITION,
                    "WinCondition": LG.SETTINGS["RSK_WINCON"]}[name]
        enum = "RandoOptionWincon" if name == "WinCondition" else "RandoOptionCheckTrigger"
        names = sorted(D.ENUMS[enum])
        return names[self.h("C", name) % len(names)]


class SparseEnv(Env):
    """every call answers `default`, but those in `flip` the opposite (options: 0 / 1, numbers 0 / 100); records the
    calls it answers"""

    def __init__(self, fixed, default, flip):
        self.fixed = fixed
        self.default = default
        self.flip = flip
        self.seen = set()
        self.seed = "sparse"
        self.p = 0.5

    def ans(self, key):
        self.seen.add(key)
        return self.default != (key in self.flip)

    def method(self, name, args):
        ret = D.LOGIC_METHODS[name][0]
        key = ("L", name, norm_args(name, args))
        if T.type_kind(ret) == "bool":
            return self.ans(key)
        if ret.startswith("Randomizer"):
            raise Unsupported(f"{name} returns {ret}")
        return 100 if self.ans(key) else 0

    def field(self, name):
        if name == "CurrentRegionKey":
            return "RR_KOKIRI_FOREST"
        if name == "CalculatingAvailableChecks":
            return False
        if D.LOGIC_FIELDS[name] == "bool":
            return self.ans(("F", name))
        return 100 if self.ans(("F", name)) else 0

    def option(self, name):
        if self.fixed:
            return super().option(name)
        return Opt(1 if self.ans(("O", name)) else 0)

    def bit(self, *key):
        if self.fixed:
            return super().bit(*key)
        return self.ans(key)

    def save(self, name):
        return (1 if name == "bgsFlag" else 100) if self.ans(("S", name)) else 0

    def scene(self):
        return "SCENE_KOKIRI_FOREST"

    def condition(self, name):
        return super().condition(name) if self.fixed else             ("RO_WINCON_DEFEAT_GANON" if name == "WinCondition" else "RO_CHECK_TRIGGER_NONE")


class Opt(LG.OptionValue):
    def __init__(self, v):
        super().__init__("mock", v)


def num(v):
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, str):
        if v in VALUE:
            return VALUE[v]
        raise Unsupported(f"value of {v}")
    if isinstance(v, Opt):
        raise Unsupported("option as number")
    return v


def norm_args(name, args):
    params = D.LOGIC_METHODS[name][1]
    args = list(args)
    for t, pn, d in params[len(args):]:
        if d is None:
            raise Unsupported(f"{name}: missing argument {pn}")
        args.append({"true": True, "false": False}.get(d, d if not re.fullmatch(r"\d+", d) else int(d)))
    out = []
    for a in args:
        if isinstance(a, Opt):
            a = a.value != 0
        if isinstance(a, str) and a not in VALUE:
            out.append(a.split("::")[-1])   # (enum class values: GlitchType::EquipSwap is "EquipSwap" in the port)
        else:
            out.append(num(a) if isinstance(a, (str, bool)) else a)
    return tuple(out)


# ---- the C++ interpreter

class Interp:
    def __init__(self, env, tables, sets, method, args, params):
        self.env = env
        self.tables = tables
        self.sets = sets
        self.vars = {pn: a for (t, pn, d), a in zip(params, args)}
        self.method = method

    def run(self, body):
        try:
            self.exec(body)
        except _Return as r:
            return r.v
        return None

    def exec(self, s):
        k = s[0]
        if k == "block":
            for x in s[1]:
                self.exec(x)
        elif k == "nop":
            pass
        elif k == "return":
            raise _Return(None if s[1] is None else self.eval(s[1]))
        elif k == "if":
            if self.truth(self.eval(s[1])):
                self.exec(s[2])
            elif s[3] is not None:
                self.exec(s[3])
        elif k == "switch":
            v = num(self.eval(s[1]))
            items = s[2]
            start = None
            for i, it in enumerate(items):
                if it[0] == "case" and num(self.eval(it[1])) == v:
                    start = i
                    break
            if start is None:
                for i, it in enumerate(items):
                    if it[0] == "default":
                        start = i
            if start is None:
                return
            try:
                for it in items[start:]:
                    if it[0] in ("case", "default"):
                        continue
                    self.exec(it)
            except _Break:
                pass
        elif k == "break":
            raise _Break()
        elif k == "assert":
            if not self.truth(self.eval(s[1])):
                raise Assert()
        elif k == "decl":
            self.vars[s[1]] = None if s[2] is None else self.eval(s[2])
        elif k == "assign":
            if s[1] not in self.vars:
                raise Unsupported(f"assignment to {s[1]}")
            self.vars[s[1]] = self.eval(s[2])
        elif k == "expr":
            self.eval(s[1])
        else:
            raise Unsupported(k)

    @staticmethod
    def truth(v):
        if isinstance(v, Opt):
            return v.value != 0
        if isinstance(v, str):
            return num(v) != 0
        return bool(v)

    def eval(self, n):
        k = n[0]
        env = self.env
        if k == "num":
            return n[1]
        if k == "bool":
            return n[1]
        if k == "id":
            name = n[1]
            if name in self.vars:
                return self.vars[name]
            if name in D.LOGIC_FIELDS:
                return env.field(name)
            if name in VALUE:
                return name
            if name.startswith("Rando::"):
                return name[len("Rando::"):]
            if re.fullmatch(r"(GlitchType|HasProjectileAge)::\w+", name):
                return name.split("::")[1]   # (enum class values, as strings in the port)
            raise Unsupported(f"identifier {name}")
        if k == "un":
            if n[1] == "!":
                return not self.truth(self.eval(n[2]))
            if n[1] == "-":
                return -num(self.eval(n[2]))
            raise Unsupported(f"unary {n[1]}")
        if k == "cast":
            v = self.eval(n[2])
            return self.truth(v) if n[1] == "bool" else num(v)
        if k == "ternary":
            return self.eval(n[2]) if self.truth(self.eval(n[1])) else self.eval(n[3])
        if k == "bin":
            op = n[1]
            if op == "&&":
                return self.truth(self.eval(n[2])) and self.truth(self.eval(n[3]))
            if op == "||":
                return self.truth(self.eval(n[2])) or self.truth(self.eval(n[3]))
            a, b = num(self.eval(n[2])), num(self.eval(n[3]))
            if op in ("/", "%"):
                q = abs(a) // abs(b)
                q = q if (a >= 0) == (b >= 0) else -q
                return q if op == "/" else a - b * q
            return {"==": a == b, "!=": a != b, "<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b,
                    "+": a + b, "-": a - b, "*": a * b, "<<": a << b, ">>": a >> b, "&": a & b, "|": a | b,
                    "^": a ^ b}[op]
        if k == "index":
            obj, idx = n[1], self.eval(n[2])
            if obj[0] == "id":
                tname = {"RandoGetToEquipFlag": "equipFlagTable", "StaticData::RandoGetToRandInf": "randInfTable",
                         "RandoGetToDungeonScene": "dungeonSceneTable", "RandoGetToQuestItem": "questItemTable"
                         }.get(obj[1])
                if tname:
                    t = self.tables[tname]
                    fill = {"randInfTable": "RAND_INF_MAX", "dungeonSceneTable": "SCENE_ID_MAX"}.get(tname, 0)
                    return t.get(idx, fill)
            raise Unsupported("index")
        if k == "member":
            obj, arrow, name = n[1], n[2], n[3]
            if obj[0] == "id" and obj[1] == "mSaveContext" or \
                    (obj[0] == "call" and obj[1] == ("id", "GetSaveContext", obj[1][2])):
                return env.save(name)
            if obj[0] == "call" and obj[1][0] == "id" and obj[1][1] == "RegionTable" and name == "scene":
                return env.scene()
            raise Unsupported(f"member {name}")
        if k == "call":
            fn, args = n[1], n[2]
            if fn[0] == "id":
                name = fn[1]
                if name in D.LOGIC_METHODS:
                    vals = [self.eval(a) for a in args]
                    vals = [v.value != 0 if isinstance(v, Opt) else v for v in vals]
                    return env.method(name, vals)
                if name in ("LogicVal", "RandomizerGet"):
                    return num(self.eval(args[0]))
                raise Unsupported(f"function {name}")
            if fn[0] == "member":
                obj, arrow, name = fn[1], fn[2], fn[3]
                if obj[0] == "id" and obj[1] == "ctx":
                    if name in ("GetOption", "GetTrickOption"):
                        return env.option(self.eval(args[0]))
                    if name in ("GetDungeon", "GetTrial"):
                        return ("dungeon" if name == "GetDungeon" else "trial", self.eval(args[0]))
                    if name in ("GBKCondition", "GanonsSoulCondition", "WinCondition"):
                        return env.condition(name)
                    raise Unsupported(f"ctx->{name}")
                if obj[0] == "id" and obj[1].startswith("StaticData::") and name == "contains":
                    return self.eval(args[0]) in self.sets[obj[1][len("StaticData::"):]]
                o = self.eval(obj)
                if isinstance(o, Opt):
                    vals = [self.eval(a) for a in args]
                    return getattr(o, name)(*vals)
                if isinstance(o, tuple) and o[0] == "dungeon" and name in ("IsMQ", "IsVanilla"):
                    return env.bit("DM" if name == "IsMQ" else "DV", o[1])
                raise Unsupported(f"method {name}")
        raise Unsupported(k)


# ---- the Python side

class _MockSave:
    def __init__(self, env):
        object.__setattr__(self, "_env", env)

    def __getattr__(self, name):
        return self._env.save(name)


class _MockCtx:
    def __init__(self, env):
        self.env = env

    def GetOption(self, k):
        if not self.env.fixed and k in LG.SETTINGS or self.env.fixed:
            return self.env.option(k)
        return self.env.option(k)

    def GetTrickOption(self, k):
        return self.env.option(k)

    def GetDungeon(self, k):
        env = self.env
        return type("Dg", (), {"IsMQ": lambda s: env.bit("DM", k), "IsVanilla": lambda s: env.bit("DV", k)})()

    def GBKCondition(self):
        return self.env.condition("GBKCondition")

    def GanonsSoulCondition(self):
        return self.env.condition("GanonsSoulCondition")

    def WinCondition(self):
        return self.env.condition("WinCondition")


def py_run(method, args, env):
    L = LG.Logic.__new__(LG.Logic)
    L.ctx = _MockCtx(env)
    for f in D.LOGIC_FIELDS:
        setattr(L, f, env.field(f))
    L.mSaveContext = _MockSave(env)
    L.PlacedItem = lambda rc: "RG_NONE"
    depth = [0]
    for name in D.LOGIC_METHODS:
        if name == method:
            continue

        def mock(*a, _n=name):
            return env.method(_n, a)
        setattr(L, name, mock)
    real = getattr(LG.Logic, method)

    def wrapper(*a):
        if depth[0]:
            return env.method(method, a)
        depth[0] += 1
        try:
            return real(L, *a)
        finally:
            depth[0] -= 1
    setattr(L, method, wrapper)
    old = LG._scene_of
    LG._scene_of = lambda rr: env.scene()
    try:
        return L.__dict__[method](*args)
    finally:
        LG._scene_of = old


# ---- driving

def arg_values(t):
    if t == "bool":
        return [False, True]
    if t in ("uint8_t", "uint16_t", "uint32_t", "int"):
        return [0, 1, 2, 3, 4, 5, 6, 9]
    if t == "SceneID":
        return ["SCENE_SPIRIT_TEMPLE", "SCENE_FIRE_TEMPLE", "SCENE_WATER_TEMPLE", "SCENE_THIEVES_HIDEOUT"]
    if t == "RandomizerCheck":
        return ["RC_KF_SHOP_ITEM_1", "RC_KF_KOKIRI_SWORD_CHEST", "RC_MARKET_BAZAAR_ITEM_2"]
    if t in D.ENUMS:
        return sorted(n for n in D.ENUMS[t] if not n.endswith("_MAX"))
    raise Unsupported(f"argument type {t}")


def to_type(ret, v):
    """a C++ return value converted to the declared return type"""
    if ret == "bool":
        return Interp.truth(v)
    if ret in ("uint8_t", "int8_t"):
        return num(v) & 0xFF
    if ret in ("uint16_t", "int16_t"):
        return num(v) & 0xFFFF
    if ret in ("uint32_t", "int"):
        return num(v)
    return v


def same(a, b):
    if isinstance(a, Opt):
        a = a.value != 0
    if isinstance(b, LG.OptionValue):
        b = b.value != 0
    if isinstance(a, (bool, int)) and isinstance(b, (bool, int)):
        return int(a) == int(b)
    if isinstance(a, str) or isinstance(b, str):
        return num(a) == num(b)
    return a == b


def check_methods(seeds_random=60, seeds_fixed=40, verbose=print):
    methods, text = parse_methods()
    tables, sets = parse_tables(text)
    fails = []
    # tables
    py_tables = {"equipFlagTable": LG.RANDO_GET_TO_EQUIP_FLAG, "randInfTable": LG.RANDO_GET_TO_RAND_INF,
                 "dungeonSceneTable": LG.RANDO_GET_TO_DUNGEON_SCENE, "questItemTable": LG.RANDO_GET_TO_QUEST_ITEM,
                 "BottleRandomizerGetToItemID": LG.BOTTLE_RANDO_GET_TO_ITEM, "HookshotLookup": LG.HOOKSHOT_LOOKUP,
                 "OcarinaLookup": LG.OCARINA_LOOKUP}
    for k, v in py_tables.items():
        if tables[k] != v:
            fails.append(f"table {k} differs from logic.cpp")
    py_sets = {"restrictSpells": LG.RESTRICT_SPELLS, "restrictTrade": LG.RESTRICT_TRADE, "allowMasks": LG.ALLOW_MASKS,
               "allowBottleMaskTrade": LG.ALLOW_BOTTLE_MASK_TRADE}
    for k, v in py_sets.items():
        if sets.get(k) != v:
            fails.append(f"set {k} differs from logic.cpp")
    verbose(f"   logic.cpp tables (equip flags, rand inf, dungeon scenes, quest items, bottles, hookshot/ocarina "
            f"steps) and item-use sets: {len(py_tables) + len(py_sets) - sum(f.startswith(('table', 'set')) for f in fails)}"
            f" of {len(py_tables) + len(py_sets)} equal to logic.py's")
    checked, runs, skipped_runs, unparsed = [], 0, 0, []
    for name, (status, body, line) in sorted(methods.items()):
        if name in SKIP:
            continue
        if status != "ok":
            unparsed.append(f"{name} ({body})")
            continue
        if name not in D.LOGIC_METHODS:
            continue
        params = D.LOGIC_METHODS[name][1]
        try:
            values = [arg_values(t) for t, _, _ in params]
        except Unsupported as e:
            unparsed.append(f"{name} ({e})")
            continue
        # (every combination of the enum parameters; the bool/int ones drawn per run)
        enum_ix = [i for i, (t, _, _) in enumerate(params) if t in D.ENUMS or t in ("SceneID", "RandomizerCheck")]
        combos = list(itertools.product(*[values[i] for i in enum_ix])) if enum_ix else [()]
        bad = [0]

        def compare(combo, env, label):
            nonlocal runs, skipped_runs
            runs += 1
            try:
                want = to_type(D.LOGIC_METHODS[name][0], Interp(env, tables, sets, name, combo, params).run(body))
                want_kind = "value"
            except Assert:
                want, want_kind = None, "assert"
            except Unsupported:
                want, want_kind = None, "unsupported"
            try:
                got = py_run(name, combo, env)
                got_kind = "value"
            except LG.LogicError as e:
                got, got_kind = str(e), ("unported" if "not ported" in str(e) else "error")
            if want_kind == "assert" and got_kind == "error":
                return   # (SoH asserts (a default case): the port raises)
            if got_kind == "unported" or want_kind == "unsupported":
                skipped_runs += 1
                if env.fixed:
                    fails.append(f"{name}{combo}: under the fixed settings, C++ {want_kind}, python {got_kind} {got}")
                    bad[0] += 1
                return
            if want_kind != got_kind or not same(want, got):
                bad[0] += 1
                if bad[0] <= 3:
                    fails.append(f"{name}{combo} ({label}): C++ {want_kind} {want!r}, python {got_kind} {got!r}")

        for ecombo in combos:
            for fixed in (False, True):
                for seed in range(seeds_random if not fixed else seeds_fixed):
                    r = random.Random(hash((name, ecombo, seed, fixed)))
                    combo = tuple(ecombo[enum_ix.index(i)] if i in enum_ix else r.choice(v)
                                  for i, v in enumerate(values))
                    compare(combo, Env((name, combo, seed, fixed), fixed),
                            "fixed settings" if fixed else "random options")
                # (sparse: every call either side makes, alone true (all else false) and alone false)
                for seed in range(2):
                    r = random.Random(hash((name, ecombo, "sparse", seed, fixed)))
                    combo = tuple(ecombo[enum_ix.index(i)] if i in enum_ix else r.choice(v)
                                  for i, v in enumerate(values))
                    keys = set()
                    for default in (False, True):
                        env = SparseEnv(fixed, default, set())
                        for side in ("cpp", "py"):
                            try:
                                if side == "cpp":
                                    Interp(env, tables, sets, name, combo, params).run(body)
                                else:
                                    py_run(name, combo, env)
                            except (Assert, Unsupported, LG.LogicError):
                                pass
                        keys |= env.seen
                    for k in sorted(keys, key=repr):
                        for default in (False, True):
                            compare(combo, SparseEnv(fixed, default, {k}),
                                    f"only {k} {'false' if default else 'true'}{', fixed settings' if fixed else ''}")
        checked.append((name, len(combos), bad[0]))
    nbad = sum(1 for _, _, b in checked if b)
    verbose(f"   {len(checked)} Logic methods interpreted from logic.cpp and compared with logic.py: {runs} runs, "
            f"{nbad} methods differing; {skipped_runs} runs skipped (a branch the port leaves unported, e.g. "
            f"count bridges or GBK triggers, only reachable with random options)")
    verbose(f"   not interpreted (read by hand): {', '.join(sorted(SKIP & set(methods)))}"
            + (f"; unparsed: {', '.join(unparsed)}" if unparsed else ""))
    return fails, checked, unparsed


if __name__ == "__main__":
    fails, checked, unparsed = check_methods()
    for f in fails:
        print("  FAIL:", f)
    print("ok" if not fails else f"{len(fails)} failures")
