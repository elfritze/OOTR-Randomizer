"""Each dungeon's saved state (DungeonInfo.<dungeon>: SmallKeyNum, IsGetBossKey, IsGetMap, IsGetCompass) in every save slot,
newest first: what tools/make_dungeon_item_test.py's chests should change. Read only.

    python tools/read_dungeon_info.py <game folder> [dungeon...]"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from rando import dungeon_items as D, savefile  # noqa: E402


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    game = sys.argv[1]
    dungeons = sys.argv[2:] or ["ForestTemple"]
    for mtime, path in savefile.find_saves(game):
        s = savefile.read(path)
        parts = []
        for d in dungeons:
            keys = s["int"].get(savefile.murmur3("DungeonInfo.%s.SmallKeyNum" % d))
            flags = {f: s["bool"].get(savefile.murmur3("DungeonInfo.%s.%s" % (d, f)))
                     for f in ("IsGetBossKey", "IsGetMap", "IsGetCompass")}
            parts.append("%s keys %s %s" % (d, keys, " ".join("%s=%s" % (k[5:], v) for k, v in flags.items())))
        print(time.ctime(mtime), os.path.basename(os.path.dirname(path)), " | ".join(parts))


if __name__ == "__main__":
    main()
