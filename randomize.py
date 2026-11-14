"""HookshotRando: a chest randomizer for The Legend of Zelda: Ocarina of Time (Switch 2) as Longshot runs it, made as a RomFS mod
from your own copy of the game.

    python randomize.py <game folder> [--seed TEXT] [--no-skip-intro]

<game folder> is Longshot's (it holds romfs and mods). The mod is written to <game folder>/mods/HookshotRando, with its
spoiler log beside its romfs folder. A new seed replaces the last one: start a new game for it."""
import argparse
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rando import generate, settings  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("game", help="Longshot's game folder (with romfs and mods)")
    p.add_argument("--seed", default=None, help="any text; the same seed and settings give the same game (default: a new one)")
    settings.add_arguments(p)
    a = p.parse_args()
    romfs = os.path.join(a.game, "romfs")
    if not os.path.isfile(os.path.join(romfs, "Pack", "ZsDic.pack.zs")):
        raise SystemExit("%s has no game romfs" % a.game)
    seed = a.seed or secrets.token_hex(4)
    chosen = {k: getattr(a, k) for k in settings.DEFAULTS}
    generate.generate(romfs, os.path.join(a.game, "mods"), seed, chosen)


if __name__ == "__main__":
    main()
