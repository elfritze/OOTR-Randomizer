"""Character Changer: play adult Link as someone else (rando/playas_app.py), without the randomizer.

    python character_changer.py
    python character_changer.py <game folder> --list | --as <key> | --as link | --check

The packaged app (tools/build_exe.py) is CharacterChanger.exe and takes the same."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):   # (a game folder: the command line)
        if sys.stdout is None and os.name == "nt":   # (the packaged app has no console of its own: the one it ran from)
            import ctypes
            if ctypes.windll.kernel32.AttachConsole(-1):
                sys.stdout = sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace")
        from rando.playas import __main__ as cli
        cli.main()
    else:
        from rando import playas_app
        playas_app.main(sys.argv)
