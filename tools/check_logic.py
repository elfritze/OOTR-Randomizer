"""Validate the SoH logic port (rando/logic):

    python tools/check_logic.py [--quick]

a. the generated files import; rules counted; every rule re-translated from its C++ text (0 untranslated), and the
   translation checked against a direct interpreter of the C++ AST with C++ semantics, on random environments
   (precedence, !, ?:, &&/||, conversions); Logic's methods match logic.h (names, parameters, defaults); every option
   read is fixed in logic.SETTINGS; the scene and enum names logic.py uses exist; Logic's methods interpreted from
   logic.cpp and compared with logic.py (tools/check_logic_cpp.py); item effects on a new save
b. with every progression item: the non-MQ locations of the region graph not reachable, each explained (an
   unexplained one fails); reachability monotone in items
c. the vanilla playthrough (every location's vanilla item, a new game): SoH's logic as is (not beatable: its
   pessimistic key counts for the Water and Spirit Temples, printed with the rule chain), then with one extra logical
   key for each of those two dungeons (must be beatable); spheres
d. spot checks of translated rules against the C++ (Deku Tree slingshot chest, Mido's house chests, Dampe's hookshot
   chest, Ice Cavern iron boots chest), evaluated on item sets
e. the World API (overrides, extra and removed locations) and its errors
Exit status 1 if a check fails."""
import argparse
import collections
import inspect
import os
import random
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from rando.logic import logic as LG          # noqa: E402
from rando.logic import search as S          # noqa: E402
from rando.logic import soh_data as D        # noqa: E402
from rando.logic import soh_regions as R     # noqa: E402
from rando.logic import translate as T       # noqa: E402

FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        print("  FAIL:", msg)
    return cond


def all_rules():
    for rr, r in R.REGIONS.items():
        for kind in ("events", "locations", "exits"):
            for name, (fn, cpp, wh) in r[kind]:
                yield f"{kind[:-1]} {rr} {name}", fn, cpp, wh
    for rr, ent in R.SPIRIT_LOGIC_DATA.items():
        for i, (fn, cpp, wh) in enumerate(ent[4:]):
            yield f"spirit {rr} {('childAccess', 'adultAccess', 'reverseAccess')[i]}", fn, cpp, wh


# ---- a. the C++ interpreter (C++ semantics) and the mock environment both sides read

class _Opt:
    def __init__(self, v):
        self.v = v

    def Is(self, x):
        return self.v == (D.ENUM_VALUE[x] if isinstance(x, str) else int(x))

    def IsNot(self, x):
        return not self.Is(x)

    def Get(self):
        return self.v

    def __bool__(self):
        return self.v != 0


class _Env:
    """deterministic pseudo-random answers to every call a rule makes, keyed by the call and its arguments"""
    INTS = [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 16, 24, 32, 48, 50, 64, 100, 200, 0xFFFF]

    BIAS = [0.05, 0.15, 0.3, 0.5, 0.7, 0.85, 0.95]   # (P(true) of a call, per environment)

    def __init__(self, seed):
        self.seed = seed
        self.p = self.BIAS[hash(("bias", seed)) % len(self.BIAS)]

    def h(self, *key):
        return hash((self.seed,) + key)

    def bit(self, *key):
        return (self.h(*key) % 10007) < self.p * 10007

    def num(self, *key):
        return self.INTS[self.h(*key) % len(self.INTS)]

    def logic_call(self, name, args):
        ret = D.LOGIC_METHODS[name][0]
        if T.type_kind(ret) == "bool":
            return self.bit("L", name, args)
        return self.num("L", name, args)

    def logic_field(self, name):
        if D.LOGIC_FIELDS[name] == "bool":
            return self.bit("F", name)
        return self.num("F", name)

    def option(self, name):
        return _Opt([0, 1, 2, 10][self.h("O", name) % 4])

    def free(self, name, args, fns):
        vals = [bool(f()) for f in fns]   # (every lambda evaluated, in order)
        if name in ("GetCheckPrice", "GetWalletCapacity"):
            return self.num("G", name, args)
        b = self.bit("G", name, args)
        return b != (sum(vals) % 2 == 1)


class _MockL:
    def __init__(self, env):
        object.__setattr__(self, "_env", env)

    def __getattr__(self, name):
        env = self._env
        if name in D.LOGIC_FIELDS:
            return env.logic_field(name)
        if name in D.LOGIC_METHODS:
            return lambda *a: env.logic_call(name, a)
        raise AttributeError(name)


class _MockC:
    def __init__(self, env):
        self.env = env

    def GetOption(self, k):
        return self.env.option(k)

    def GetTrickOption(self, k):
        return self.env.option(k)

    def GetDungeon(self, k):
        env = self.env
        return type("Dg", (), {"IsVanilla": lambda s: env.bit("DV", k), "IsMQ": lambda s: env.bit("DM", k)})()

    def GetTrial(self, k):
        env = self.env
        return type("Tr", (), {"IsSkipped": lambda s: env.bit("TS", k)})()


class _MockF:
    def __init__(self, env):
        self.env = env

    def __getattr__(self, name):
        env = self.env
        if name == "Region":
            return lambda rr: type("Rg", (), {"AnyAgeTime": lambda s, fn: env.free("Region.AnyAgeTime", (rr,),
                                                                                    [fn])})()
        if name not in D.FREE_FUNCTIONS:
            raise AttributeError(name)

        def f(*a):
            fns = [x for x in a if callable(x)]
            key = tuple(x for x in a if not callable(x))
            # (SpiritShared's default lambdas: the Python side gets Python defaults; mirror C++'s by count)
            return env.free(name, key, fns)
        return f


def cpp_eval(n, env):
    """the value of a parsed C++ expression with C++ semantics, calls answered by env"""
    k = n[0]
    if k == "num":
        return n[1]
    if k == "bool":
        return n[1]
    if k == "id":
        return n[1][len("Rando::"):] if n[1].startswith("Rando::") else n[1]
    if k == "lambda":
        return lambda: cpp_eval(n[1], env)
    if k == "un":
        v = cpp_eval(n[2], env)
        if n[1] == "!":
            return not _cbool(v)
        if n[1] == "-":
            return -int(v)
        raise ValueError(n[1])
    if k == "cast":
        v = cpp_eval(n[2], env)
        return _cbool(v) if n[1] == "bool" else int(v)
    if k == "bin":
        op = n[1]
        if op == "&&":
            return _cbool(cpp_eval(n[2], env)) and _cbool(cpp_eval(n[3], env))
        if op == "||":
            return _cbool(cpp_eval(n[2], env)) or _cbool(cpp_eval(n[3], env))
        a, b = cpp_eval(n[2], env), cpp_eval(n[3], env)
        if isinstance(a, str) or isinstance(b, str):
            return {"==": a == b, "!=": a != b}[op]
        a, b = int(a), int(b)
        if op in ("/", "%"):
            q = abs(a) // abs(b)
            q = q if (a >= 0) == (b >= 0) else -q
            return q if op == "/" else a - b * q
        return {"==": a == b, "!=": a != b, "<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b, "+": a + b,
                "-": a - b, "*": a * b}[op]
    if k == "ternary":
        return cpp_eval(n[2], env) if _cbool(cpp_eval(n[1], env)) else cpp_eval(n[3], env)
    if k == "member":
        obj, name = n[1], n[3]
        if obj[0] == "id" and obj[1] == "logic":
            return env.logic_field(name)
        raise ValueError("member")
    if k == "index":
        return ("region", cpp_eval(n[2], env))
    if k == "call":
        fn, args = n[1], n[2]
        if fn[0] == "member":
            obj, name = fn[1], fn[3]
            if obj[0] == "id" and obj[1] == "logic":
                vals = tuple(_cargs(args, D.LOGIC_METHODS[name][1], env))
                return env.logic_call(name, vals)
            if obj[0] == "id" and obj[1] == "ctx":
                key = cpp_eval(args[0], env)
                if name in ("GetOption", "GetTrickOption"):
                    return env.option(key)
                return (name, key)
            o = cpp_eval(obj, env)
            if isinstance(o, _Opt):
                return getattr(o, name)(*[cpp_eval(a, env) for a in args])
            if isinstance(o, tuple) and o[0] == "GetDungeon":
                return env.bit("DV" if name == "IsVanilla" else "DM", o[1])
            if isinstance(o, tuple) and o[0] == "GetTrial":
                return env.bit("TS", o[1])
            if isinstance(o, tuple) and o[0] == "region":
                return env.free("Region.AnyAgeTime", (o[1],), [cpp_eval(args[0], env)])
            raise ValueError("method")
        if fn[0] == "id":
            params = D.FREE_FUNCTIONS[fn[1]][1]
            vals = list(_cargs(args, params, env))
            fns = [v for v in vals if callable(v)]
            key = tuple(v for v in vals if not callable(v))
            # (default lambdas C++ fills in: `[] { return false; }`, evaluated like the given ones)
            fns += [lambda: False for (t, _, d) in params[len(args):] if t == "ConditionFn" and d is not None]
            return env.free(fn[1], key, fns)
    raise ValueError(k)


def _cbool(v):
    return v.v != 0 if isinstance(v, _Opt) else bool(v)


def _cargs(args, params, env):
    for a, (t, _, _) in zip(args, params):
        v = cpp_eval(a, env)
        tk = T.type_kind(t)
        if tk == "bool":
            v = _cbool(v)
        elif tk == "int":
            v = int(v)
        yield v


def check_translation(seeds):
    print("a. generated code and translation")
    print(f"   soh_regions: commit {R.SOH_COMMIT}, {len(R.REGIONS)} vanilla regions, {R.RULE_COUNT} rules; "
          f"{len(R.MQ_EXITS_DROPPED)} exits into MQ regions dropped")
    n = bad = 0
    mismatch = 0
    for what, fn, cpp, wh in all_rules():
        n += 1
        try:
            py = T.cpp_to_py(cpp, wh)
            T.compile_rule(py, wh)
        except T.TranslateError as e:
            bad += 1
            print("   untranslated:", wh, e)
            continue
        ast = T.parse(cpp, wh)
        for seed in range(seeds):
            env = _Env((seed, wh))
            want = _cbool(cpp_eval(ast, env))
            got = fn(_MockL(env), _MockC(env), _MockF(env))
            if bool(got) != want:
                mismatch += 1
                if mismatch <= 5:
                    print(f"   MISMATCH {wh}: {cpp}\n      python: {T.cpp_to_py(cpp, wh)}\n      seed {seed}: "
                          f"C++ {want}, python {bool(got)}")
                break
    print(f"   {n} rules (regions' events/locations/exits + spiritLogicData) re-translated: {bad} untranslated; "
          f"checked against the C++ interpreter on {seeds} random environments each: {mismatch} mismatches")
    check(bad == 0, "untranslated rules")
    check(mismatch == 0, "translation differs from C++ semantics")
    # (the translator's errors)
    for expr, why in [("logic->Nope()", "unknown method"), ("RG_HOOKSHOT < RG_LONGSHOT", "enum order"),
                      ("[]{ bool x = true; return x; }", "lambda statements"), ("FOO_BAR", "unknown name"),
                      ("ctx->GetOption(RSK_FOREST) + 1", "option as number"), ("logic->CanUse(RE_GANON)",
                                                                                "argument enum type"),
                      ("logic->CanUse(RG_HOOKSHOT) ? ED_CLOSE : true", "ternary kinds"), ("1.5 > 1", "float")]:
        try:
            T.cpp_to_py(expr)
            check(False, f"translator accepted {expr!r} ({why})")
        except T.TranslateError:
            pass
    print("   translator rejects: unknown names/methods, enum ordering, lambda statements, options as numbers, "
          "wrong enum argument types, mixed ternaries, floats")


def check_items():
    """ApplyItemEffect (not interpreted by check_logic_cpp): what each item does to a new save, against
    logic.cpp's cases"""
    print("   item effects (Logic::ApplyItemEffect) on a new game's save")

    def after(*items):
        L = LG.Logic()
        for rg in items:
            L.ApplyEffect(rg)
        return L
    H = "RG_PROGRESSIVE_HOOKSHOT"
    cases = [
        (after(), lambda L: not L.HasItem("RG_HOOKSHOT") and L.HasItem("RG_CLIMB") and L.HasItem("RG_POWER_BRACELET")
         and L.HasItem("RG_BRONZE_SCALE") and L.HasItem("RG_CHILD_WALLET") and L.HasItem("RG_STICKS")
         and L.HasItem("RG_NUTS") and L.HasItem("RG_OCARINA_A_BUTTON") and L.CanOpenLargeChest()
         and L.HasItem("RG_SPEAK_DEKU") and L.HasItem("RG_FISHING_POLE") and L.HasItem("RG_LOST_WOODS_BEAN_SOUL")
         and L.Health() == 48 and L.GetSmallKeyCount("SCENE_FIRE_TEMPLE") == 1 and not L.HasItem("RG_BOMB_BAG"),
         "new game: abilities, buttons, stick/nut capacity 1, wallet, souls; 3 hearts; 1 logical Fire Temple key"),
        (after(H), lambda L: L.HasItem("RG_HOOKSHOT") and not L.HasItem("RG_LONGSHOT"), "hookshot"),
        (after(H, H), lambda L: L.HasItem("RG_HOOKSHOT") and L.HasItem("RG_LONGSHOT"), "longshot"),
        (after(H, H, H), lambda L: L.HasItem("RG_LONGSHOT"), "a third hookshot stays longshot"),
        (after("RG_PROGRESSIVE_STRENGTH"), lambda L: L.HasItem("RG_GORONS_BRACELET")
         and not L.HasItem("RG_SILVER_GAUNTLETS"), "strength 1: Goron's Bracelet (Power Bracelet from the start)"),
        (after(*["RG_PROGRESSIVE_STRENGTH"] * 3), lambda L: L.HasItem("RG_GOLDEN_GAUNTLETS"), "strength 3: golden"),
        (after("RG_PROGRESSIVE_SCALE"), lambda L: L.HasItem("RG_SILVER_SCALE") and not L.HasItem("RG_GOLDEN_SCALE"),
         "scale 1: silver (bronze from the start)"),
        (after("RG_PROGRESSIVE_WALLET", "RG_PROGRESSIVE_WALLET"), lambda L: L.HasItem("RG_GIANT_WALLET")
         and not L.HasItem("RG_TYCOON_WALLET"), "wallets 2: giant (child wallet from the start)"),
        (after("RG_PROGRESSIVE_BOMB_BAG"), lambda L: L.HasItem("RG_BOMB_BAG") and L.CanUse("RG_BOMB_BAG")
         and L.CurrentInventory("ITEM_BOMB") == "ITEM_BOMB", "bomb bag"),
        (after("RG_PROGRESSIVE_BOW"), lambda L: L.HasItem("RG_FAIRY_BOW"), "bow"),
        (after("RG_PROGRESSIVE_SLINGSHOT"), lambda L: L.HasItem("RG_FAIRY_SLINGSHOT"), "slingshot"),
        (after("RG_PROGRESSIVE_OCARINA"), lambda L: L.HasItem("RG_FAIRY_OCARINA")
         and not L.HasItem("RG_OCARINA_OF_TIME"), "fairy ocarina"),
        (after("RG_PROGRESSIVE_OCARINA", "RG_PROGRESSIVE_OCARINA"), lambda L: L.HasItem("RG_OCARINA_OF_TIME"),
         "ocarina of time"),
        (after("RG_PROGRESSIVE_MAGIC_METER"), lambda L: L.HasItem("RG_MAGIC_SINGLE"), "magic"),
        (after("RG_FOREST_TEMPLE_SMALL_KEY", "RG_FOREST_TEMPLE_SMALL_KEY"), lambda L: L.SmallKeys(
            "SCENE_FOREST_TEMPLE", 2) and not L.SmallKeys("SCENE_FOREST_TEMPLE", 3), "small keys count"),
        (after("RG_FIRE_TEMPLE_SMALL_KEY"), lambda L: L.GetSmallKeyCount("SCENE_FIRE_TEMPLE") == 2,
         "Fire Temple keys add to the logical one"),
        (after("RG_WATER_TEMPLE_KEY_RING"), lambda L: L.GetSmallKeyCount("SCENE_WATER_TEMPLE") == 10, "key ring"),
        (after("RG_GERUDO_FORTRESS_SMALL_KEY"), lambda L: L.SmallKeys("SCENE_THIEVES_HIDEOUT", 1), "hideout key"),
        (after("RG_FOREST_TEMPLE_BOSS_KEY"), lambda L: L.HasItem("RG_FOREST_TEMPLE_BOSS_KEY"), "boss key"),
        (after(*["RG_GOLD_SKULLTULA_TOKEN"] * 50), lambda L: L.GetGSCount() == 50, "tokens"),
        (after("RG_HEART_CONTAINER", "RG_PIECE_OF_HEART"), lambda L: L.Health() == 48 + 16 + 4, "hearts"),
        (after("RG_EMPTY_BOTTLE"), lambda L: L.HasBottle() and L.BottleCount() == 1, "bottle"),
        (after(*["RG_EMPTY_BOTTLE"] * 5), lambda L: L.BottleCount() == 4, "a 5th bottle overwrites the 4th"),
        (after("RG_BOTTLE_WITH_BIG_POE"), lambda L: L.BigPoes == 1 and L.BottleCount() == 0,
         "big poe bottle: counted as a bottle once big poes can be emptied"),
        (after("RG_RUTOS_LETTER"), lambda L: L.HasItem("RG_RUTOS_LETTER") and not L.HasBottle(),
         "Ruto's letter: a flag, no bottle slot (as SoH)"),
        (after("RG_DEKU_SHIELD"), lambda L: not L.HasItem("RG_DEKU_SHIELD")
         and L.CheckRandoInf("RAND_INF_HAS_FOUND_DEKU_SHIELD"),
         "a found Deku Shield is not equipment in SoH's logic (shields burn: the shop's counts)"),
        (after("RG_BUY_DEKU_SHIELD"), lambda L: L.HasItem("RG_DEKU_SHIELD"), "bought Deku Shield"),
        (after("RG_HYLIAN_SHIELD"), lambda L: not L.HasItem("RG_HYLIAN_SHIELD"), "found Hylian Shield (as Deku)"),
        (after("RG_GORON_TUNIC"), lambda L: L.HasItem("RG_GORON_TUNIC"), "found Goron Tunic is equipment"),
        (after("RG_GIANTS_KNIFE"), lambda L: L.HasItem("RG_GIANTS_KNIFE") and not L.HasItem("RG_BIGGORON_SWORD"),
         "Giant's Knife"),
        (after("RG_BIGGORON_SWORD"), lambda L: L.HasItem("RG_BIGGORON_SWORD"), "Biggoron's Sword"),
        (after("RG_BUY_BOMBCHUS_10"), lambda L: L.Get("LOGIC_BUY_BOMBCHUS") and
         L.CurrentInventory("ITEM_BOMBCHU") == "ITEM_BOMBCHU", "bought bombchus: logic value + inventory"),
        (after("RG_MAGIC_BEAN"), lambda L: L.GetAmmo("ITEM_BEAN") == 1 and L.HasItem("RG_MAGIC_BEAN"), "a bean"),
        (after("RG_MAGIC_BEAN_PACK"), lambda L: L.GetAmmo("ITEM_BEAN") == 10, "bean pack"),
        (after("RG_ZELDAS_LULLABY"), lambda L: L.HasItem("RG_ZELDAS_LULLABY") and not L.CanUse("RG_ZELDAS_LULLABY"),
         "a song without an ocarina"),
        (after("RG_ZELDAS_LULLABY", "RG_PROGRESSIVE_OCARINA"), lambda L: L.CanUse("RG_ZELDAS_LULLABY"),
         "a song with an ocarina"),
        (after("RG_KOKIRI_EMERALD", "RG_FOREST_MEDALLION"), lambda L: L.StoneCount() == 1
         and L.MedallionCount() == 1, "dungeon rewards"),
        (after("RG_DOUBLE_DEFENSE"), lambda L: L.HasItem("RG_DOUBLE_DEFENSE") and L.EffectiveHealth() == 96,
         "double defense doubles effective health"),
    ]
    bad = 0
    for L, test, what in cases:
        if not check(test(L), f"item effect: {what}"):
            bad += 1
    print(f"   {len(cases)} item effect cases: {len(cases) - bad} as logic.cpp's ApplyItemEffect gives")
    # (every item can be applied: no item type falls through ApplyItemEffect)
    errs = []
    for rg, it in D.ITEMS.items():
        if it["type"] == "ITEMTYPE_SILVER":
            continue
        try:
            after(rg)
        except Exception as e:
            errs.append(f"{rg}: {e}")
    check(not errs, f"items that cannot be applied: {errs[:5]}")
    print(f"   all {sum(1 for i in D.ITEMS.values() if i['type'] != 'ITEMTYPE_SILVER')} non-silver-rupee items "
          f"apply without error")


def check_declarations():
    print("   Logic vs logic.h, free functions vs location_access.h, settings, names")
    used_methods, used_free, used_opts, used_tricks = set(), set(), set(), set()
    for what, fn, cpp, wh in all_rules():
        used_methods |= set(re.findall(r"logic->(\w+)\(", cpp))
        used_free |= {f for f in re.findall(r"(?<![>.\w])(\w+)\(", cpp) if f in D.FREE_FUNCTIONS}
        used_opts |= set(re.findall(r"(?<![A-Za-z0-9_])RSK_\w+", cpp))
        used_tricks |= set(re.findall(r"(?<![A-Za-z0-9_])RT_\w+", cpp))

    def cdefault(d):
        if d is None:
            return inspect.Parameter.empty
        return {"true": True, "false": False}.get(d, int(d) if re.fullmatch(r"\d+", d) else d)
    for name, (ret, params) in D.LOGIC_METHODS.items():
        if not hasattr(LG.Logic, name):
            check(name not in used_methods, f"Logic.{name} (logic.h, used by rules) not ported")
            continue
        sig = inspect.signature(getattr(LG.Logic, name))
        ps = list(sig.parameters.values())[1:]
        check([p.name for p in ps] == [p[1] for p in params],
              f"Logic.{name} parameters {[p.name for p in ps]} vs logic.h {[p[1] for p in params]}")
        for p, (t, pn, d) in zip(ps, params):
            check(p.default == cdefault(d), f"Logic.{name}({pn}) default {p.default!r} vs logic.h {d!r}")
    for f in used_free:
        check(hasattr(S._Search, f), f"free function {f} (rules) not ported")
        ps = list(inspect.signature(getattr(S._Search, f)).parameters.values())[1:]
        check([p.name for p in ps] == [p[1] for p in D.FREE_FUNCTIONS[f][1]], f"{f} parameters")
    print(f"   {len(used_methods)} Logic methods and {len(used_free)} free functions used by rules: all ported, "
          f"signatures and defaults as declared")
    src = open(LG.__file__, encoding="utf-8").read() + open(S.__file__, encoding="utf-8").read()
    used_opts |= set(re.findall(r'"(RSK_\w+)"', src))
    missing = sorted(o for o in used_opts if o not in LG.SETTINGS)
    check(not missing, f"options read but not fixed: {missing}")
    check(all(t in D.ENUM_OF for t in used_tricks), "unknown trick names")
    print(f"   {len(used_opts)} options read (rules + logic.py + search.py): all fixed in SETTINGS; "
          f"{len(used_tricks)} tricks read, all off")
    names = set(re.findall(r'"((?:SCENE|RG|RE|LOGIC|RAND_INF|ED|RC|RR|RO|RSK|RT|ITEM|SLOT|UPG|QUEST|DUNGEON|EQUIP_FLAG|'
                           r'OBJECT_GI)_\w+)"', src))
    oot = {n for e in ("ItemID", "InventorySlot", "UpgradeType", "QuestItem", "DungeonItem", "EquipmentFlag")
           for n in D.OOT[e]}
    unknown = sorted(n for n in names if n not in D.ENUM_OF and n not in oot and not n.startswith("OBJECT_GI")
                     and n not in ("RR_NONE", "LOGIC_X", "RC_X", "RR_A", "RR_B", "RR_Y"))   # (docstring examples)
    check(not unknown, f"names in logic.py/search.py not in SoH's enums: {unknown}")
    print(f"   {len(names)} enum names written in logic.py/search.py: all exist in SoH's / OoT's enums")


# ---- b. everything

def all_items():
    items = collections.Counter()
    for rg, it in D.ITEMS.items():
        if not it["advancement"] or it["type"] in ("ITEMTYPE_SILVER", "ITEMTYPE_EVENT"):
            continue
        items[rg] = 1
    gen = {"RG_PROGRESSIVE_HOOKSHOT": 2, "RG_PROGRESSIVE_STRENGTH": 3, "RG_PROGRESSIVE_BOMB_BAG": 3,
           "RG_PROGRESSIVE_BOW": 3, "RG_PROGRESSIVE_SLINGSHOT": 3, "RG_PROGRESSIVE_WALLET": 2,
           "RG_PROGRESSIVE_SCALE": 2, "RG_PROGRESSIVE_NUT_UPGRADE": 2, "RG_PROGRESSIVE_STICK_UPGRADE": 2,
           "RG_PROGRESSIVE_OCARINA": 2, "RG_PROGRESSIVE_MAGIC_METER": 2, "RG_PROGRESSIVE_GORONSWORD": 2,
           "RG_GOLD_SKULLTULA_TOKEN": 100, "RG_HEART_CONTAINER": 17, "RG_EMPTY_BOTTLE": 4, "RG_MAGIC_BEAN": 10,
           "RG_TRIFORCE_PIECE": 0}
    for rg, it in D.ITEMS.items():
        if it["type"] in ("ITEMTYPE_SMALLKEY", "ITEMTYPE_FORTRESS_SMALLKEY") and "KEY_RING" not in rg:
            gen[rg] = 10
    gen.update({rg: 0 for rg in items if rg.startswith("RG_BOTTLE_WITH_")})   # (4 empty bottles)
    items.update({k: v - items[k] for k, v in gen.items()})
    return +items


EXPLAIN = [   # (why a non-MQ location is out of reach with every item: (pattern on "RC type", reason))
    (r"^(RC_GANONS_BOSS_KEY|RC_GANON_SOUL|RC_WINCON) ", "Root's trigger checks: Ganon's Boss Key vanilla, Ganon's soul "
     "start-with, win = defeat Ganon, so no trigger condition (CanTriggerGBK/GanonsSoul/Wincon false)"),
    (r" RCTYPE_NL(CRATE|TREE)$", "\"no logic\" crates/trees: SoH pools them only with RSK_NO_LOGIC; their rules are false "
     "or need an age that never is in that region"),
    (r"^RC_LH_ADULT_(FISH_\d+|LOACH) ", "the pond's adult fish: separate checks only with RSK_FISHSANITY_AGE_SPLIT (off: "
     "one set of fish checks for both ages)"),
    (r"^RC_MARKET_TREASURE_CHEST_GAME_SHOPKEEPER ", "its item exists only with RSK_SHUFFLE_CHEST_MINIGAME (off: the "
     "game is played as in the game, its chests are the checks)"),
]


def check_monotone(w, n):
    """more items never reach less (SoH's logic is monotone in items: a violation would point at the port)"""
    rnd = random.Random(7)
    items = sorted(all_items().elements())
    worse = 0
    for _ in range(n):
        k = rnd.randrange(len(items))
        sub = collections.Counter(rnd.sample(items, k))
        more = sub + collections.Counter(rnd.sample(items, min(len(items), 15)))
        a, b = w.reachable(sub), w.reachable(more)
        if not a <= b:
            worse += 1
            print("   non-monotone:", sorted(a - b)[:5])
    check(worse == 0, "reachability not monotone in items")
    print(f"   monotone: {n} random item sets, each plus 15 more items, never reach less")


def explain(rc):
    key = f"{rc} {D.LOCATIONS[rc]['type']}"
    for pat, why in EXPLAIN:
        if re.search(pat, key):
            return why
    return None


def check_everything(w):
    print("b. every progression item")
    items = all_items()
    reach = w.reachable(items)
    nonmq = {rc for rc in w.location_ids if D.LOCATIONS[rc]["quest"] != "RCQUEST_MQ"}
    missing = sorted(nonmq - reach)
    print(f"   {sum(items.values())} items ({len(items)} kinds): {len(reach)} of {len(nonmq)} non-MQ graph locations "
          f"reachable; not reachable: {len(missing)}")
    groups = collections.defaultdict(list)
    for rc in missing:
        groups[explain(rc)].append(rc)
    for why, rcs in groups.items():
        check(why is not None, f"unexplained unreachable locations: {rcs}")
        print(f"   {len(rcs)}: {why or 'UNEXPLAINED'}")
    s = S._Search(w, items, None)
    s.run()
    for rc in missing:
        regs = [(rr, cpp) for rr, r in w.regions.items() for l, fn, cpp, wh in r.locations if l == rc]
        acc = ["".join(str(int(getattr(s.access[rr], a))) for a in ("childDay", "childNight", "adultDay",
                                                                      "adultNight")) for rr, _ in regs]
        print(f"   - {rc} [{D.LOCATIONS[rc]['type']}]")
        for (rr, cpp), a in zip(regs, acc):
            print(f"       {rr} (access cd/cn/ad/an {a}): {cpp}")
    ages = (s.access["RR_ROOT"].Child(), s.access["RR_ROOT"].Adult())
    check(ages == (True, True), "both ages reachable with everything")
    print("   both ages reach Root (child start, adult through the Door of Time)")
    out_of_graph = sorted(rc for rc, loc in D.LOCATIONS.items() if loc["quest"] != "RCQUEST_MQ"
                          and rc not in w.location_ids)
    by_type = collections.Counter(D.LOCATIONS[rc]["type"] for rc in out_of_graph)
    print(f"   non-MQ locations of the location tables in no region: {len(out_of_graph)} ({dict(by_type)})")
    return missing


# ---- c. vanilla playthrough

def check_vanilla(w):
    print("c. vanilla playthrough (every location's vanilla item, a new game)")
    v = S.vanilla_items()
    placed = {rc: rg for rc, rg in v.items() if rc in w.location_ids}
    print(f"   {len(v)} non-MQ locations with a vanilla item, {len(placed)} in the region graph")
    final, spheres = w.collect(collections.Counter(), placed)
    beat = w.can_beat(final)
    print(f"   SoH logic as is: {len(spheres)} spheres, {sum(map(len, spheres))} locations collected; can_beat {beat}")
    got_keys = {k[3:]: final[k] for k in ("RG_WATER_TEMPLE_SMALL_KEY", "RG_SPIRIT_TEMPLE_SMALL_KEY")}
    print(f"   keys collected: {got_keys} (vanilla has 6 Water, 5 Spirit)")
    if not beat:
        # (SoH's own key logic with the vanilla key layout, not the port: the chains below are its rules)
        print("   stops at the Water Temple: SoH gates the door to Dark Link (and so the Longshot) at 5 keys "
              "(water_temple.cpp:557); 4 are reachable before it (torches, central pillar, cracked wall, dragon "
              "chests); the other 2 need the Longshot or Hover Boots (water_temple.cpp:141 central bow target; the "
              "river chest is past Dark Link); Hover Boots are in the Shadow Temple, behind Nocturne, behind the "
              "Water Medallion (kakariko.cpp:17)")
        print("   then at the Spirit Temple: SoH gates the child throne door (to the Silver Gauntlets) at 3 keys "
              "(spirit_temple.cpp:356, quantum key logic); child reaches 2 (early torches, sun block chests); the "
              "other 3 are on the adult side, which needs the Silver Gauntlets (spirit_temple.cpp:34)")
    allowance = collections.Counter({"RG_WATER_TEMPLE_SMALL_KEY": 1, "RG_SPIRIT_TEMPLE_SMALL_KEY": 1})
    final2, spheres2 = w.collect(allowance, placed)
    beat2 = w.can_beat(final2)
    print(f"   with one extra logical Water Temple key and one Spirit Temple key: {len(spheres2)} spheres, "
          f"{sum(map(len, spheres2))} locations, can_beat {beat2}")
    check(beat2, "vanilla playthrough not beatable even with the key allowance")
    left = sorted(rc for rc in placed if rc not in set().union(*spheres2)
                  and S.item_info()[placed[rc]]["progression"])
    print(f"   progression items not collected then: {len(left)}: " +
          ", ".join(f"{rc}={placed[rc][3:]}" for rc in left))
    junk = {rg for rg, i in S.item_info().items() if not i["progression"]}
    for i, sp in enumerate(spheres2[:6]):
        prog = sorted(collections.Counter(placed[l] for l in sp if placed[l] not in junk).items())
        print(f"   sphere {i}: {len(sp)} locations; progression: " +
              ", ".join(f"{k[3:]}" + (f" x{n}" if n > 1 else "") for k, n in prog))
    for i, sp in enumerate(spheres2):
        if any(placed[l] in ("RG_TRIFORCE",) for l in sp):
            print(f"   the Triforce (RC_GANON) in sphere {i}")
    return beat, beat2, spheres, spheres2


# ---- d. spot checks

SPOT = ["RC_DEKU_TREE_SLINGSHOT_CHEST", "RC_KF_MIDOS_TOP_LEFT_CHEST", "RC_KF_MIDOS_TOP_RIGHT_CHEST",
        "RC_KF_MIDOS_BOTTOM_LEFT_CHEST", "RC_KF_MIDOS_BOTTOM_RIGHT_CHEST", "RC_GRAVEYARD_HOOKSHOT_CHEST",
        "RC_ICE_CAVERN_IRON_BOOTS_CHEST"]


def check_spots(w):
    print("d. spot checks (the region's C++ rule, its translation, where it sits)")
    for rc in SPOT:
        hits = [(rr, cpp, wh, fn) for rr, r in R.REGIONS.items() for l, (fn, cpp, wh) in r["locations"] if l == rc]
        check(hits, f"{rc} not in the graph")
        for rr, cpp, wh, fn in hits:
            print(f"   {rc} in {rr} ({wh}):\n      C++:    {cpp}\n      python: {T.cpp_to_py(cpp)}")
    reach0 = w.reachable(collections.Counter())
    for rc in SPOT[1:5]:
        check(rc in reach0, f"{rc} (Mido's house, rule HasItem(RG_OPEN_CHEST)) not reachable at the start")
    check("RC_DEKU_TREE_SLINGSHOT_CHEST" not in reach0, "Deku Tree slingshot chest reachable with nothing")
    sword_shield = collections.Counter({"RG_KOKIRI_SWORD": 1, "RG_BUY_DEKU_SHIELD": 1})
    check("RC_DEKU_TREE_SLINGSHOT_CHEST" in w.reachable(sword_shield),
          "Deku Tree slingshot chest not reachable with sword + shield (Mido moves, shield reflects the scrub's nut)")
    check("RC_DEKU_TREE_SLINGSHOT_CHEST" not in w.reachable(collections.Counter({"RG_KOKIRI_SWORD": 1})),
          "Deku Tree slingshot chest reachable without a shield (closed forest: Mido)")
    print("   Mido's chests reachable at the start; the slingshot chest with Kokiri Sword + Deku Shield, not with the "
          "sword alone")
    # (Dampe: adult at the graveyard (Door of Time: 3 stones, Ocarina of Time, Song of Time), Power Bracelet (start))
    # (closed forest: child leaves Kokiri Forest after the Deku Tree, so Gohma's slingshot too)
    adult = collections.Counter({"RG_KOKIRI_SWORD": 1, "RG_BUY_DEKU_SHIELD": 1, "RG_PROGRESSIVE_SLINGSHOT": 1,
                                 "RG_KOKIRI_EMERALD": 1,
                                 "RG_GORON_RUBY": 1, "RG_ZORA_SAPPHIRE": 1, "RG_PROGRESSIVE_OCARINA": 2,
                                 "RG_SONG_OF_TIME": 1})
    r = w.reachable(adult)
    check("RC_GRAVEYARD_HOOKSHOT_CHEST" in r, "Dampe's hookshot chest not reachable as adult")
    check("RC_TOT_MASTER_SWORD" in r, "Master Sword not reachable with the Door of Time requirements")
    r2 = w.reachable(adult - collections.Counter({"RG_SONG_OF_TIME": 1}))
    check("RC_GRAVEYARD_HOOKSHOT_CHEST" not in r2, "Dampe's hookshot chest reachable as child only")
    print("   Dampe's hookshot chest reachable with the Deku Tree's and the Door of Time's items (sword, shield, "
          "slingshot, 3 stones, Ocarina of Time, Song of Time), not without the Song of Time")
    ice = adult + collections.Counter({"RG_PROGRESSIVE_STRENGTH": 1, "RG_PROGRESSIVE_BOMB_BAG": 1,
                                       "RG_EMPTY_BOTTLE": 1, "RG_ZELDAS_LULLABY": 1, "RG_PROGRESSIVE_HOOKSHOT": 1,
                                       "RG_PROGRESSIVE_SCALE": 1, "RG_RUTOS_LETTER": 1})
    r3 = w.reachable(ice)
    check("RC_ICE_CAVERN_IRON_BOOTS_CHEST" in r3, "Ice Cavern iron boots chest not reachable")
    r4 = w.reachable(ice - collections.Counter({"RG_EMPTY_BOTTLE": 1}))
    check("RC_ICE_CAVERN_IRON_BOOTS_CHEST" not in r4, "Ice Cavern iron boots chest reachable without blue fire")
    print("   Ice Cavern iron boots chest reachable as adult with a bottle (blue fire), not without one")


# ---- e. API

def check_api():
    print("e. World API")
    w = S.World(extra_locations={"REMAKE_KF_NEW_CHEST": ("RR_KOKIRI_FOREST", "logic->CanUse(RG_KOKIRI_SWORD)")},
                rule_overrides={("location", "RC_KF_MIDOS_TOP_LEFT_CHEST"): "logic->CanUse(RG_KOKIRI_SWORD)",
                                ("exit", "RR_KF_LINKS_HOUSE", "RR_KF_LINKS_PORCH"): "true",
                                ("event", "RR_KOKIRI_FOREST", "LOGIC_SHOWED_MIDO_SWORD_AND_SHIELD"): "true",
                                ("location_region", "RC_KF_KOKIRI_SWORD_CHEST"): "RR_KF_LINKS_HOUSE"},
                removed_locations=["RC_KF_MIDOS_TOP_RIGHT_CHEST"])
    r = w.reachable(collections.Counter())
    check("REMAKE_KF_NEW_CHEST" not in r, "extra location rule ignored")
    check("REMAKE_KF_NEW_CHEST" in w.reachable(collections.Counter({"RG_KOKIRI_SWORD": 1})), "extra location")
    check("RC_KF_MIDOS_TOP_LEFT_CHEST" not in r, "location override ignored")
    check("RC_KF_MIDOS_TOP_RIGHT_CHEST" not in w.location_ids, "removed location still there")
    check("RC_KF_KOKIRI_SWORD_CHEST" in r, "location_region override")
    check("RC_DEKU_TREE_MAP_CHEST" in r, "event override (Mido moved) ignored")
    errors = 0
    for kw in [dict(rule_overrides={("location", "RC_NOPE"): "true"}),
               dict(rule_overrides={("exit", "RR_KOKIRI_FOREST", "RR_GANONS_CASTLE_LOBBY"): "true"}),
               dict(rule_overrides={("event", "RR_KOKIRI_FOREST", "LOGIC_NOPE"): "true"}),
               dict(rule_overrides={("location_region", "RC_KF_MIDOS_TOP_LEFT_CHEST"): "RR_NOPE"}),
               dict(rule_overrides={("location_region", "RC_DEKU_TREE_LOBBY_LOWER_HEART"): "RR_DEKU_TREE_COMPASS_ROOM"}),
               dict(rule_overrides={("location", "RC_KF_MIDOS_TOP_LEFT_CHEST"): "logic->Nope()"}),
               dict(removed_locations=["RC_NOPE"]),
               dict(extra_locations={"RC_KF_MIDOS_TOP_LEFT_CHEST": ("RR_KOKIRI_FOREST", "true")})]:
        try:
            S.World(**kw)
        except (S.WorldError, T.TranslateError):
            errors += 1
    check(errors == 8, f"bad overrides rejected: {errors} of 8")
    print("   extra location, location/exit/event/location_region overrides, removed location: applied; "
          f"{errors} of 8 bad ones rejected (unknown location/exit/event/region, a location in two regions moved "
          "without its rule, untranslatable rule, extra id colliding)")
    info = S.item_info()
    prog = sum(1 for i in info.values() if i["progression"])
    major = sum(1 for i in info.values() if i["major"])
    print(f"   item_info: {len(info)} items, {prog} progression, {major} major (hints); vanilla_items: "
          f"{len(S.vanilla_items())} locations")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="fewer random environments per rule")
    args = ap.parse_args()
    check_translation(4 if args.quick else 24)
    check_declarations()
    print("   Logic methods vs logic.cpp (tools/check_logic_cpp.py)")
    sys.path.insert(0, HERE)
    import check_logic_cpp
    fails, checked, unparsed = check_logic_cpp.check_methods(*((10, 6) if args.quick else (60, 40)))
    for f in fails:
        check(False, f)
    check_items()
    w = S.World()
    check_everything(w)
    check_monotone(w, 10 if args.quick else 60)
    check_vanilla(w)
    check_spots(w)
    check_api()
    print()
    print("FAILED: " + "; ".join(FAILS) if FAILS else "all checks passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
