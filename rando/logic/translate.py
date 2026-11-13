"""SoH logic rule expressions (C++) to Python.

A rule is a C++ expression as written in SoH's region files (location_access/*), e.g.
    logic->CanUse(RG_HOOKSHOT) && (logic->IsAdult || ctx->GetTrickOption(RT_X))
cpp_to_py(expr) gives the Python expression over three names, evaluated as `lambda L, C, F: <expr>`:
    L  the Logic (rando.logic.logic.Logic): logic->X
    C  the settings context (rando.logic.logic.Ctx): ctx->X
    F  the search's free functions (rando.logic.search): AnyAgeTime, SpiritShared, GetCheckPrice, ...
Enum constants (RG_*, RC_*, RR_*, LOGIC_*, RT_*, RSK_*, RO_*, ED_*, SCENE_*, ...) become strings.

The translation is typed (bool, int, enum, option, lambda) from SoH's own declarations (logic.h, location_access.h,
the enum headers; see soh_data), so a construct C++ would read differently than Python (an enum compared by order,
an option used as a number, a lambda with statements, an unknown name) is an error (TranslateError), never a guess."""
import re

from . import soh_data


class TranslateError(Exception):
    pass


# ---- tokens

_TOKEN = re.compile(r"""
    (?P<ws>\s+)
  | (?P<num>0[xX][0-9A-Fa-f]+[uUlL]*|\d+[uUlL]*(?![\w.]))
  | (?P<float>\d+\.\d*[fF]?|\d+[fF])
  | (?P<str>"(?:[^"\\]|\\.)*")
  | (?P<chr>'(?:[^'\\]|\\.)')
  | (?P<id>[A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)
  | (?P<op>->|&&|\|\||==|!=|<=|>=|<<|>>|::|[()\[\]{}!<>+\-*/%?:,;.&|^~=])
""", re.VERBOSE)


def strip_comments(text):
    """C++ text without // and /* */ comments (strings kept; a comment becomes spaces, newlines kept, so line numbers
    hold)."""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == '"' or c == "'":
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
            if j < 0:
                raise TranslateError("unterminated /* comment")
            out.append("".join(ch if ch == "\n" else " " for ch in text[i:j + 2]))
            i = j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def tokenize(text, line=1, where=None):
    """[(kind, value, line)] of C++ text (comments must be stripped)"""
    toks = []
    pos = 0
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            raise TranslateError(f"{_at(where, line)}: unexpected character {text[pos]!r}")
        kind = m.lastgroup
        val = m.group()
        if kind == "ws":
            line += val.count("\n")
        elif kind == "float":
            raise TranslateError(f"{_at(where, line)}: floating point literal {val!r} not supported")
        else:
            toks.append((kind, val, line))
        pos = m.end()
    return toks


def _at(where, line):
    if where is None:
        return f"line {line}"
    return f"{where}" if ":" in str(where) else f"{where}:{line}"


# ---- parser (C++ precedence)

_BINARY = {   # (precedence, higher binds tighter)
    "||": 1, "&&": 2, "|": 3, "^": 4, "&": 5, "==": 6, "!=": 6, "<": 7, "<=": 7, ">": 7, ">=": 7,
    "<<": 8, ">>": 8, "+": 9, "-": 9, "*": 10, "/": 10, "%": 10,
}
_CASTS = {"bool": "bool", "int": "int", "uint8_t": "int", "uint16_t": "int", "uint32_t": "int", "int8_t": "int",
          "int16_t": "int", "int32_t": "int"}


class _Parser:
    def __init__(self, toks, where):
        self.toks = toks
        self.i = 0
        self.where = where

    def peek(self, k=0):
        j = self.i + k
        return self.toks[j] if j < len(self.toks) else ("eof", "", self.toks[-1][2] if self.toks else 0)

    def err(self, msg, tok=None):
        tok = tok or self.peek()
        raise TranslateError(f"{_at(self.where, tok[2])}: {msg}")

    def take(self, val=None, kind=None):
        tok = self.peek()
        if (val is not None and tok[1] != val) or (kind is not None and tok[0] != kind) or tok[0] == "eof":
            self.err(f"expected {val or kind!r}, found {tok[1] or 'end'!r}")
        self.i += 1
        return tok

    def at(self, val):
        tok = self.peek()
        return tok[0] in ("op", "id") and tok[1] == val

    def expr(self):
        cond = self.binary(1)
        if self.at("?"):
            tok = self.take("?")
            a = self.expr()
            self.take(":")
            b = self.expr()
            return ("ternary", cond, a, b, tok[2])
        return cond

    def binary(self, minprec):
        left = self.unary()
        while True:
            tok = self.peek()
            prec = _BINARY.get(tok[1]) if tok[0] == "op" else None
            if prec is None or prec < minprec:
                return left
            self.i += 1
            right = self.binary(prec + 1)
            left = ("bin", tok[1], left, right, tok[2])

    def unary(self):
        tok = self.peek()
        if tok[0] == "op" and tok[1] in ("!", "-", "+", "~"):
            self.i += 1
            return ("un", tok[1], self.unary(), tok[2])
        if tok[0] == "op" and tok[1] == "(" and self.peek(1)[0] == "id" and self.peek(1)[1] in _CASTS \
                and self.peek(2)[1] == ")":
            ctype = self.peek(1)[1]
            self.i += 3
            return ("cast", _CASTS[ctype], self.unary(), tok[2])
        if tok[0] == "id" and tok[1] == "static_cast":
            self.err("static_cast not supported")
        return self.postfix(self.primary())

    def primary(self):
        tok = self.peek()
        if tok[0] == "num":
            self.i += 1
            return ("num", int(tok[1].rstrip("uUlL"), 0), tok[2])
        if tok[0] == "id":
            self.i += 1
            if tok[1] in ("true", "false"):
                return ("bool", tok[1] == "true", tok[2])
            return ("id", tok[1], tok[2])
        if tok[0] == "op" and tok[1] == "(":
            self.i += 1
            e = self.expr()
            self.take(")")
            return e
        if tok[0] == "op" and tok[1] == "[":
            return self.lambda_()
        self.err(f"unexpected {tok[1] or 'end'!r}")

    def lambda_(self):
        tok = self.take("[")
        if not self.at("]"):
            self.err("lambda captures not supported")
        self.take("]")
        if self.at("("):
            self.take("(")
            if not self.at(")"):
                self.err("lambda parameters not supported")
            self.take(")")
        self.take("{")
        if not self.at("return"):
            self.err("lambda body must be a single `return <expr>;` (statements not supported)")
        self.take("return")
        body = self.expr()
        self.take(";")
        if not self.at("}"):
            self.err("lambda body must be a single `return <expr>;` (more statements found)")
        self.take("}")
        return ("lambda", body, tok[2])

    def postfix(self, node):
        while True:
            tok = self.peek()
            if tok[0] != "op":
                return node
            if tok[1] == "(":
                self.i += 1
                args = []
                if not self.at(")"):
                    args.append(self.expr())
                    while self.at(","):
                        self.take(",")
                        args.append(self.expr())
                self.take(")")
                node = ("call", node, args, tok[2])
            elif tok[1] in ("->", "."):
                self.i += 1
                name = self.take(kind="id")
                node = ("member", node, tok[1], name[1], tok[2])
            elif tok[1] == "[":
                self.i += 1
                idx = self.expr()
                self.take("]")
                node = ("index", node, idx, tok[2])
            else:
                return node


def parse(text, where=None, line=1):
    """the AST of one C++ expression"""
    toks = tokenize(strip_comments(text), line, where)
    if not toks:
        raise TranslateError(f"{_at(where, line)}: empty expression")
    p = _Parser(toks, where)
    e = p.expr()
    if p.peek()[0] != "eof":
        p.err(f"unexpected {p.peek()[1]!r} after the expression")
    return e


# ---- typed emitter

# (kinds: "bool", "int", "logic" (and/or/ternary of truthy values: Python and/or yield an operand, so it is truthy,
#  not necessarily a bool), "enum:<EnumType>", "opt" (an OptionValue), "fn" (a lambda), "dungeon", "trial", "region")

_CPP_TYPES = {
    "bool": "bool", "uint8_t": "int", "uint16_t": "int", "uint32_t": "int", "int8_t": "int", "int16_t": "int",
    "int32_t": "int", "int": "int", "ConditionFn": "fn",
}

# Python precedence of emitted forms (higher binds tighter)
_PY_PREC = {"if": 1, "or": 2, "and": 3, "not": 4, "cmp": 5, "|": 6, "^": 7, "&": 8, "<<": 9, ">>": 9, "+": 10,
            "-": 10, "*": 11, "//": 11, "%": 11, "neg": 12, "atom": 20}
_CMP = ("==", "!=", "<", "<=", ">", ">=")


def type_kind(cpp_type, where="?"):
    t = cpp_type.replace("const", "").replace("&", "").strip()
    if t in _CPP_TYPES:
        return _CPP_TYPES[t]
    if t in soh_data.ENUM_TYPES:
        return "enum:" + t
    raise TranslateError(f"{where}: unknown C++ type {cpp_type!r}")


class _Emitter:
    def __init__(self, where):
        self.where = where

    def err(self, node, msg):
        raise TranslateError(f"{_at(self.where, node[-1])}: {msg}")

    # each emit returns (python text, kind, precedence)

    def emit(self, n):
        k = n[0]
        if k == "num":
            return str(n[1]), "int", _PY_PREC["atom"]
        if k == "bool":
            return ("True" if n[1] else "False"), "bool", _PY_PREC["atom"]
        if k == "id":
            return self.ident(n)
        if k == "lambda":
            body = self.as_bool(n[1])
            return f"(lambda: {body})", "fn", _PY_PREC["atom"]
        if k == "un":
            return self.unary(n)
        if k == "cast":
            if n[1] == "bool":
                return f"bool({self.as_bool(n[2])})", "bool", _PY_PREC["atom"]
            return f"int({self.as_int(n[2])})", "int", _PY_PREC["atom"]
        if k == "bin":
            return self.binary(n)
        if k == "ternary":
            return self.ternary(n)
        if k == "call":
            return self.call(n)
        if k == "member":
            return self.member(n)
        if k == "index":
            return self.index(n)
        self.err(n, f"unsupported construct {k}")

    def index(self, n):
        """areaTable[RR_X] (only as the object of .AnyAgeTime)"""
        obj, idx = n[1], n[2]
        if obj[0] == "id" and obj[1] == "areaTable":
            t, k, _ = self.emit(idx)
            if k != "enum:RandomizerRegion":
                self.err(n, f"areaTable index of {k}")
            return f"F.Region({t})", "region", _PY_PREC["atom"]
        self.err(n, "indexing not supported")

    def ident(self, n):
        name = n[1]
        if name.startswith("Rando::"):
            name = name[len("Rando::"):]
        if name in soh_data.ENUM_OF:
            return repr(name), "enum:" + soh_data.ENUM_OF[name], _PY_PREC["atom"]
        if name in ("logic", "ctx"):
            self.err(n, f"bare {name!r}")
        self.err(n, f"unknown identifier {n[1]!r}")

    def paren(self, text, prec, need):
        return text if prec >= need else f"({text})"

    def as_bool(self, n):
        """text usable where C++ converts to bool (Python truthiness is the same for bool, int, option, and/or)"""
        text, kind, prec = self.emit(n)
        if kind.startswith("enum:") or kind in ("fn", "dungeon", "trial", "region"):
            self.err(n, f"{kind} used as a condition")
        return text

    def bool_operand(self, n, need):
        text, kind, prec = self.emit(n)
        if kind.startswith("enum:") or kind in ("fn", "dungeon", "trial", "region"):
            self.err(n, f"{kind} used as a condition")
        return self.paren(text, prec, need)

    def as_int(self, n, need=_PY_PREC["atom"]):
        """text usable where C++ uses an integer (bool promotes; and/or results are made real bools)"""
        text, kind, prec = self.emit(n)
        if kind in ("int", "bool"):
            return self.paren(text, prec, need)
        if kind == "logic":
            return f"bool({text})"
        if kind == "opt":
            self.err(n, "option used as a number without .Get()")
        self.err(n, f"{kind} used as a number")

    def unary(self, n):
        op = n[1]
        if op == "!":
            return f"not {self.bool_operand(n[2], _PY_PREC['not'])}", "bool", _PY_PREC["not"]
        if op == "-":
            return f"-{self.as_int(n[2], _PY_PREC['neg'])}", "int", _PY_PREC["neg"]
        self.err(n, f"unary {op!r} not supported")

    def binary(self, n):
        op, a, b = n[1], n[2], n[3]
        if op in ("&&", "||"):
            py = "and" if op == "&&" else "or"
            prec = _PY_PREC[py]
            # (a chain of the same operator needs no parentheses: Python's and/or are left-associative too)
            left = self.bool_operand(a, prec)
            right = self.bool_operand(b, prec + 1)
            return f"{left} {py} {right}", "logic", prec
        if op in ("==", "!="):
            prec = _PY_PREC["cmp"]
            ta, ka, pa = self.emit(a)
            tb, kb, pb = self.emit(b)
            if ka.startswith("enum:") or kb.startswith("enum:"):
                if ka != kb:
                    self.err(n, f"{op} between {ka} and {kb}")
                return f"{self.paren(ta, pa, prec + 1)} {op} {self.paren(tb, pb, prec + 1)}", "bool", prec
            return f"{self.as_int(a, prec + 1)} {op} {self.as_int(b, prec + 1)}", "bool", prec
        if op in ("<", "<=", ">", ">="):
            prec = _PY_PREC["cmp"]
            return f"{self.as_int(a, prec + 1)} {op} {self.as_int(b, prec + 1)}", "bool", prec
        if op in ("+", "-", "*", "/", "%"):
            py = "//" if op == "/" else op
            prec = _PY_PREC[py]
            if op in ("/", "%"):
                # (C++ integer / and % truncate toward zero, Python's floor: equal for non-negative operands only)
                text = f"_cdiv({self.as_int(a)}, {self.as_int(b)})" if op == "/" else \
                    f"_cmod({self.as_int(a)}, {self.as_int(b)})"
                return text, "int", _PY_PREC["atom"]
            return f"{self.as_int(a, prec)} {py} {self.as_int(b, prec + 1)}", "int", prec
        self.err(n, f"operator {op!r} not supported")

    def ternary(self, n):
        cond = self.bool_operand(n[1], _PY_PREC["if"] + 1)
        ta, ka, pa = self.emit(n[2])
        tb, kb, pb = self.emit(n[3])
        prec = _PY_PREC["if"]
        if ka.startswith("enum:") or kb.startswith("enum:"):
            if ka != kb:
                self.err(n, f"ternary arms of different kinds {ka} and {kb}")
            kind = ka
        elif ka in ("int", "bool", "logic", "opt") and kb in ("int", "bool", "logic", "opt"):
            if "opt" in (ka, kb):
                self.err(n, "ternary arm is an option (ambiguous: bool or number)")
            kind = "int" if "int" in (ka, kb) else ("bool" if ka == kb == "bool" else "logic")
        else:
            self.err(n, f"ternary arms of kinds {ka} and {kb}")
        return f"{self.paren(ta, pa, prec + 1)} if {cond} else {self.paren(tb, pb, prec)}", kind, prec

    # ---- calls and members

    def member(self, n):
        obj, arrow, name = n[1], n[2], n[3]
        if obj[0] == "id" and obj[1] == "logic" and arrow == "->":
            if name in soh_data.LOGIC_FIELDS:
                return f"L.{name}", type_kind(soh_data.LOGIC_FIELDS[name]), _PY_PREC["atom"]
            if name in soh_data.LOGIC_METHODS:
                self.err(n, f"logic->{name} used without a call")
            self.err(n, f"unknown Logic member logic->{name}")
        self.err(n, f"member access {arrow}{name} not supported here")

    def args(self, n, params, args, fname):
        """emitted arguments checked against the C++ parameters ([(kind, name, has_default)])"""
        if len(args) > len(params):
            self.err(n, f"{fname}: {len(args)} arguments, takes at most {len(params)}")
        need = sum(1 for p in params if not p[2])
        if len(args) < need:
            self.err(n, f"{fname}: {len(args)} arguments, needs at least {need}")
        out = []
        for a, (kind, pname, _) in zip(args, params):
            if kind == "bool":
                # (C++ converts the argument to bool: an option or an and/or result becomes a real bool)
                text, k, _ = self.emit(a)
                out.append(text if k == "bool" else f"bool({self.as_bool(a)})")
            elif kind == "int":
                out.append(self.as_int(a, 0))
            elif kind == "fn":
                text, k, _ = self.emit(a)
                if k != "fn":
                    self.err(a, f"{fname}: argument {pname} must be a lambda, found {k}")
                out.append(text)
            elif kind.startswith("enum:"):
                text, k, _ = self.emit(a)
                if k != kind:
                    self.err(a, f"{fname}: argument {pname} must be {kind[5:]}, found {k}")
                out.append(text)
            else:
                self.err(a, f"{fname}: parameter kind {kind}")
        return ", ".join(out)

    def call(self, n):
        fn, args = n[1], n[2]
        atom = _PY_PREC["atom"]
        if fn[0] == "member":
            obj, arrow, name = fn[1], fn[2], fn[3]
            if obj[0] == "id" and obj[1] == "logic" and arrow == "->":
                if name not in soh_data.LOGIC_METHODS:
                    self.err(n, f"unknown Logic method logic->{name}")
                ret, params = soh_data.LOGIC_METHODS[name]
                params = [(type_kind(t, self.where), pn, d is not None) for t, pn, d in params]
                return f"L.{name}({self.args(n, params, args, 'logic->' + name)})", type_kind(ret), atom
            if obj[0] == "id" and obj[1] == "ctx" and arrow == "->":
                return self.ctx_call(n, name, args)
            # (methods on a value: options, dungeons, trials, regions)
            text, kind, _ = self.emit(obj)
            if kind == "opt" and arrow == ".":
                if name in ("Is", "IsNot"):
                    if len(args) != 1:
                        self.err(n, f".{name} takes one argument")
                    t, k, _ = self.emit(args[0])
                    if k.startswith("enum:"):
                        if not k[5:].startswith("RandoOption"):
                            self.err(n, f".{name} of {k} (needs an RO_* option value)")
                    elif k not in ("int", "bool"):
                        self.err(n, f".{name} of {k}")
                    return f"{text}.{name}({t})", "bool", atom
                if name == "Get" and not args:
                    return f"{text}.Get()", "int", atom
                self.err(n, f"option method .{name} not supported")
            if kind == "dungeon" and arrow == "->" and name in ("IsVanilla", "IsMQ") and not args:
                return f"{text}.{name}()", "bool", atom
            if kind == "trial" and arrow == "->" and name == "IsSkipped" and not args:
                return f"{text}.IsSkipped()", "bool", atom
            if kind == "region" and arrow == "." and name == "AnyAgeTime":
                params = [("fn", "condition", False)]
                return f"{text}.AnyAgeTime({self.args(n, params, args, 'AnyAgeTime')})", "bool", atom
            self.err(n, f"method {arrow}{name} on {kind} not supported")
        if fn[0] == "id":
            name = fn[1]
            if name not in soh_data.FREE_FUNCTIONS:
                self.err(n, f"unknown function {name}")
            ret, params = soh_data.FREE_FUNCTIONS[name]
            params = [(type_kind(t, self.where), pn, d is not None) for t, pn, d in params]
            return f"F.{name}({self.args(n, params, args, name)})", type_kind(ret), atom
        if fn[0] == "index":
            self.err(n, "call on an indexed value not supported")
        self.err(n, "call of an expression not supported")

    def ctx_call(self, n, name, args):
        atom = _PY_PREC["atom"]
        one = {"GetOption": ("RandomizerSettingKey", "opt"), "GetTrickOption": ("RandomizerTrick", "opt"),
               "GetDungeon": ("DungeonKey", "dungeon"), "GetTrial": ("TrialKey", "trial")}
        if name not in one:
            self.err(n, f"unknown context method ctx->{name}")
        etype, kind = one[name]
        if len(args) != 1:
            self.err(n, f"ctx->{name} takes one argument")
        t, k, _ = self.emit(args[0])
        if k != "enum:" + etype:
            self.err(n, f"ctx->{name} of {k}, needs {etype}")
        return f"C.{name}({t})", kind, atom


def translate_ast(ast, where=None):
    """(python text, kind) of a parsed expression"""
    e = _Emitter(where)
    text, kind, _ = e.emit(ast)
    return text, kind


def cpp_to_py(expr, where=None, line=1):
    """the Python expression (over L, C, F; see the module doc) of one SoH C++ rule expression, which must be a
    condition (bool-like). TranslateError on anything not handled."""
    ast = parse(expr, where, line)
    e = _Emitter(where)
    text = e.as_bool(ast)
    return text


def _cdiv(a, b):
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def _cmod(a, b):
    return a - b * _cdiv(a, b)


def compile_rule(py, where="<rule>"):
    """the function (L, C, F) -> value of a translated expression"""
    code = compile(f"lambda L, C, F: {py}", str(where), "eval")
    return eval(code, {"_cdiv": _cdiv, "_cmod": _cmod, "__builtins__": {"bool": bool, "int": int}})
