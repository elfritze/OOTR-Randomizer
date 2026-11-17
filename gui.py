"""HookshotRando's window (generate and install a seed, the character, and the tracker).

    python gui.py
    python gui.py randomize <game folder> [options]     (as randomize.py)
    python gui.py character <game folder> [options]     (as python -m rando.playas)
    python gui.py verify <romfs> <mod folder>           (as tools/verify_mod.py)

The packaged app (tools/build_exe.py) takes the same: LostWoods.exe, LostWoods.exe randomize ..."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_command(argv):
    """a command line instead of the window: True if argv named one"""
    if len(argv) < 2 or argv[1] not in ("randomize", "character", "verify"):
        return False
    command = argv[1]
    sys.argv = [argv[0]] + argv[2:]
    if sys.stdout is None and os.name == "nt":   # (the packaged app has no console of its own: the one it ran from)
        import ctypes
        if ctypes.windll.kernel32.AttachConsole(-1):
            sys.stdout = sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace")
    if command == "randomize":
        import randomize
        randomize.main()
    elif command == "verify":
        import runpy
        runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tools", "verify_mod.py"),
                       run_name="__main__")
    else:
        from rando.playas import __main__ as playas_cli
        playas_cli.main()
    return True


if __name__ == "__main__":
    if not run_command(sys.argv):
        from rando import gui
        gui.main(sys.argv)
