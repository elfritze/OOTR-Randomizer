"""Copy some files of a freshly generated mod into an installed one, with their resource size table entries, and nothing else:
for a fix to a seed being played, without regenerating it over the player's install (which may hold hand-made rescues).

    python tools/install_files.py <game folder> <new mod folder> <backup folder> <romfs path>...

Refuses while the game runs. Every file replaced, and the size table, are copied to the backup folder first; each file is
written beside its place then moved over it (never truncated in place); the size table is rebuilt and checked to differ
from the installed one only in the entries of the files given."""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rando.formats import restbl, zs  # noqa: E402
from rando.mod import RSTB  # noqa: E402

GAME_EXES = ("longshot.exe", "hookshot.exe")


def game_running():
    out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
    return [e for e in GAME_EXES if e in out]


def replace(path, data):
    tmp = path + ".new"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


def main(game, new_mod, backup, rels):
    if game_running():
        raise SystemExit("the game is running: close it first")
    codec = zs.Codec(os.path.join(game, "romfs"))
    inst = os.path.join(game, "mods", "HookshotRando")
    rst_rel = os.path.join("romfs", *RSTB.split("/"))
    for rel in list(rels) + [RSTB]:
        src = os.path.join(inst, "romfs", *rel.split("/"))
        if os.path.exists(src):
            dst = os.path.join(backup, "romfs", *rel.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
    old_raw = open(os.path.join(inst, rst_rel), "rb").read()
    old = restbl.Table(codec.read(os.path.join(inst, rst_rel)))
    new = restbl.Table(codec.read(os.path.join(new_mod, rst_rel)))
    table = restbl.Table(codec.read(os.path.join(inst, rst_rel)))
    keys = [restbl.Table.key(rel) for rel in rels]
    for key in keys:
        table.set(key, new.get(key))
    packed = codec.compress_like(table.write(), old_raw)
    check = restbl.Table(codec.decompress(packed, os.path.basename(rst_rel)))
    expected = restbl.Table(codec.read(os.path.join(inst, rst_rel)))
    for key in keys:
        if new.get(key) is None:
            raise SystemExit("%s: not in the new mod's size table" % key)
        expected.set(key, new.get(key))
    changed = [h for h in set(old.crc) | set(check.crc) if old.crc.get(h) != check.crc.get(h)] + \
        [n for n in set(old.names) | set(check.names) if old.names.get(n) != check.names.get(n)]
    if check.crc != expected.crc or check.names != expected.names or len(changed) > len(keys):
        raise SystemExit("the size table would change more than the files given: %r" % changed)
    for rel in rels:
        src = os.path.join(new_mod, "romfs", *rel.split("/"))
        dst = os.path.join(inst, "romfs", *rel.split("/"))
        if not os.path.exists(src):   # (the new mod leaves that file as the game has it: the installed copy goes)
            if os.path.exists(dst):
                os.remove(dst)
                print("removed", rel, "(the game's own is used)")
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        replace(dst, open(src, "rb").read())
        print("installed", rel)
    replace(os.path.join(inst, rst_rel), packed)
    for key in keys:
        print("size entry %s: %s -> %s" % (key, old.get(key), check.get(key)))


if __name__ == "__main__":
    if len(sys.argv) < 5:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
