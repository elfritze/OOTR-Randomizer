"""python -m rando.playas <game folder> [--list | --as <character> | --check | --build <folder>]  (see build.py)"""
import argparse
import sys

from . import CHARACTERS, GROUPS, Problem, build, current, install, outdated


def main():
    ap = argparse.ArgumentParser(prog="python -m rando.playas", description="Adult Link dressed as another character.")
    ap.add_argument("game", help="Longshot's game folder (with romfs and mods)")
    ap.add_argument("--as", dest="who", choices=["link"] + sorted(CHARACTERS), help="install this character's mod "
                    "(link: turn every character's mod off)")
    ap.add_argument("--list", action="store_true", help="the characters, and which is on")
    ap.add_argument("--check", action="store_true", help="whether the mod that is on needs building again (a new seed)")
    ap.add_argument("--build", metavar="FOLDER", help="with --as: build the mod there, install nothing")
    ap.add_argument("--taller", type=float, default=1.0, metavar="FACTOR", help="the character's mesh this many times "
                    "the size that fits Link's skeleton (joints and hands are then off: about 10 cm at 1.1)")
    a = ap.parse_args()
    try:
        on = current(a.game)
        if a.list:
            for group, _ in GROUPS:
                print(group)
                for key, c in CHARACTERS.items():
                    if c.group == group:
                        print("  %-14s %s%s" % (key, c.label, "   (on)" if key == on else ""))
        elif a.check:
            why = outdated(a.game)
            print("no character's mod is on" if on is None else
                  "build %s again: %s" % (on, why) if why else "%s: its size table is current" % on)
        elif a.who and a.build:
            build(a.game, a.who, a.build, taller=a.taller)
        elif a.who:
            install(a.game, a.who, taller=a.taller)
        else:
            ap.print_help()
    except Problem as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
