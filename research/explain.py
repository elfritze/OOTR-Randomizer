import sys, json
sys.path.insert(0, r"C:\Projects\ootremake-recomp\HookshotRando")
from rando.formats import zs
from rando.events import Events
R = r"C:\Projects\ootremake-recomp\Hookshot-Build\romfs"
E = Events(R, zs.Codec(R))
# (skip pure presentation: camera, animation, sound, waits, fades)
NOISE = ("Camera", "PlayAS", "Wait", "Sound", "Fade", "LookAt", "Effect", "Particle", "Rumble", "Turn", "Move", "Anim", "Xlink", "BGM", "Letterbox", "Emit")
for name in sys.argv[1:]:
    loc = E.locate(name)
    print("=====", name, "->", loc)
    if not loc: continue
    for depth, flow, kind, actor, act, params in E.walk(*loc, max_depth=int(__import__("os").environ.get("DEPTH", "3"))):
        if kind != "call" and any(n in act for n in NOISE): continue
        p = json.dumps(params, ensure_ascii=False, default=str) if params else ""
        print("  " * depth + "%s %s.%s %s" % (kind, actor, act, p[:300]) + ("   [%s]" % flow if depth else ""))
