# HookshotRando

A randomizer for The Legend of Zelda: Ocarina of Time (Nintendo Switch 2) as [Hookshot](https://github.com/NotRexed/Hookshot)
runs it. It is a RomFS mod: no change to Hookshot, nothing to rebuild. You make it from your own copy of the game.

## Use

You need Hookshot's game folder (it holds `romfs` and `mods`) and Python 3.10 or newer with `zstandard`
(`python -m pip install zstandard`).

```
python randomize.py "C:\Games\Hookshot" --seed anything
```

The mod goes to `<game folder>\mods\HookshotRando`, with `spoiler.txt` (where everything is, and a playthrough) and
`placements.json` beside its `romfs`. A new seed replaces the last one. **Start a new game for each seed**: a save keeps
its chests opened. To play without the mod, rename the folder to start with `_`.

| Option | |
|---|---|
| `--seed TEXT` | The same seed gives the same game. Without it, a new random seed |
| `--no-skip-intro` | Play the new game's two opening movies (skipped by default) |

## Sharing

Share this folder (the code), never a generated `mods\HookshotRando`: that holds files made from the game. Each player runs
`randomize.py` on their own copy; the same seed text gives everyone the same game.

## What it does

- **Every one-time chest is randomized**: 180 locations (148 of SoH's checks, 32 chests only the remake has), each with
  the logic of Ship of Harkinian's randomizer, adapted where the remake changed a room, a door or a key.
- **NPCs' and minigames' prizes** (35: the Skull Kid, the scrubs' upgrades, bowling, the shooting galleries, the House of
  Skulltula, fishing, the frogs, horseback archery, Dampe, the dog, Talon, Anju, King Zora...) give the item placed there:
  `data/gifts.json` names each event parameter that says what is given.
- **Items lying in the world** (the 14 loose Heart Pieces and the 8 bosses' Heart Containers) are the item placed there,
  lying where the old one was: a pickup made for each item as the remake made its own loose Fire Arrows.
- **Upgrades come in order**: the remake's bags, quivers, wallets and scales are separate items, each setting its capacity
  outright; the earliest of each kind in the playthrough is the first tier (the Bow before the quivers, the Slingshot
  before the bullet bags, the small bomb bag before the bigger ones).
- **Every seed can be finished**: the fill (SoH's way: dungeon items first, then assumed fill) is checked by playing the
  seed from a new game; a seed that fails is drawn again. No tricks or glitches are needed.
- **Keys, boss keys, maps and compasses stay in their own dungeon**: the remake has one key item for every dungeon, which
  counts for the dungeon it is picked up in.
- **Songs** in chests show Sheik's harp (the game has no model for them).
- **Chest events**: the Navi lines and scenes made for a chest's own item are dropped when the item changes; the ones the
  story needs stay (Sheik's Serenade after the Ice Cavern's chest, Nabooru's capture, Dampe's race, Ruto's room).
- **Order**: the Longshot never before the Hookshot, the Golden Gauntlets never before the Silver ones, the Silver ones
  never before Darunia's bracelet (the remake has them as separate items).
- **Ammunition after its container**: bombs and Bombchus only where a bomb bag is needed to get there, arrows only where the
  Bow is (the game hands them out without one).
- **Bombs need the Goron's Bracelet** in the remake (Bombchus do not): the logic counts bombs only once Link has it.
- **The Deku Tree's slingshot room can lock you in**, as in SoH's randomizer: its way out is a ladder its eye switch drops,
  and only the Slingshot and the Boomerang hit it (Bombchus do not). The game autosaves before the room: load that save.

Left as they are for now (`data/gifts.json` "excluded" has each one's reason): the songs (pending a test of the lessons),
the stones and medallions, the Master Sword, the Light and Fire Arrows, the ocarinas, Zelda's Letter and the Weird Egg, the
adult trade items, the Gerudo keys and card, the Great Fairies (they charge rupees in the remake and would sell again),
Darunia's bracelet, the shops and repeatable prizes. King Zora's Zora Tunic shop gift stays: without a tunic, his later
talk makes the Zora shop give one free (an extra tunic, never needed by logic).

Left as they are: the 22 minigame chests filled again at each play (the treasure chest game's but its Heart Piece prize,
the Hall of Fallen Foes, Dampe's race rupees) and the ice-trap chests (they hold no item).

## Not yet confirmed in game

The logic for these comes from reading the game's data, not from playing; each is set so that it cannot leave you stuck
(when unsure, it asks for more, not less). `research/mapping/*.json` has every chest's evidence and the full list.

- Jabu-Jabu's B1 room with Octoroks: a remake chest on the pots' ledge. Its way in is unknown, so it only gets junk.
- The Fire Temple's locked door in the lava geyser room, and the 5F chests by the scarecrow.
- The Water Temple's south-west compass room and its water level.
- The Spirit Temple's sun block room (chest from the sun blocks, doors from the silver rupees).
- Grottos changed by the remake: Hyrule Field's tektite grotto, Gerudo Fortress's, the Lost Woods' under-bridge ledge.

## How it is made

`rando/logic` is SoH's logic (commit d4bf6528) translated to Python by `tools/port_soh_logic.py` and checked rule by rule;
`data/locations.json` and `data/overrides.json` are the remake's chests and its changes to SoH's map of the world,
built by `tools/build_locations.py` from the research in `research/`. `tools/check_remake.py`, `tools/check_seeds.py` and
`tools/verify_mod.py` check the logic, many seeds, and a generated mod against the game's files.

Ship of Harkinian's repository carries no license; this port of its logic is derived from it.
