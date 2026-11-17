# Lost Woods

A randomizer for The Legend of Zelda: Ocarina of Time (Nintendo Switch 2) as [Longshot](https://git.magicbean.dev/MagicBeanDev/Longshot)
runs it. It is a RomFS mod: no change to Longshot, nothing to rebuild. You make it on your own PC from your own copy of
the game.

## Getting started

1. Download `LostWoods-1.0.zip` from the releases page and unzip it anywhere.
2. Run `LostWoods.exe` (nothing to install).
3. On the Generate page, choose Longshot's game folder (the one holding `romfs` and `mods`), pick a seed and press
   **Generate and install**. Start a new game to play it.

From source instead: Python 3.10 or newer, `python -m pip install zstandard ainb==0.2.17 texture2ddecoder`, then
`python gui.py`. `python tools/build_exe.py` builds the exe and the release zip.

## The window

- **Generate**: choose the game folder, the seed and the settings, then generate and install the seed (refused while the
  game runs), verify it, turn it on or off, open the spoiler log. Installing a seed first copies the one installed before
  to `<game folder>\rando-archive\<seed>-<time>`.
- **Settings**: every setting below, grouped by kind. The same seed and settings give the same game.
- **Character**: play adult Link as someone else (see below).
- **Tracker**: reads the game's save every few seconds and shows the seed's checks on each area's map, coloured by what
  logic reaches with what Link holds. The maps are the game's own pause-menu maps (dungeons floor by floor). A check is
  marked done by itself when the save shows it taken; chests of rupees and ammunition are marked by a click, or a whole
  area at once ("Mark area done").

## Settings

| Setting | Default |
|---|---|
| Shuffle songs | on |
| Shuffle gifts and prizes (36 NPC and minigame checks, Darunia's bracelet among them) | on |
| Shuffle freestanding Heart Pieces (and the bosses' Heart Containers, 22) | on |
| Shuffle Zelda's Letter and the Light Arrows | off |
| Shuffle the Fairy Ocarina | off |
| Shuffle the Ocarina of Time | off |
| Shuffle Great Fairies (Nayru's and Ganon's Castle's need the 500-rupee wallet in logic) | off |
| Shuffle Gold Skulltula tokens | off |
| Shuffle the Fire Arrows at Lake Hylia | off |
| Shopsanity: **Off** / 1-7 per shop / Random | Off |
| Shop prices: **Vanilla** / Cheap balanced / Balanced / Affordable | Vanilla |
| Shuffle dungeon rewards: **Vanilla** / End of dungeon | Vanilla |
| Maps and compasses: **Own dungeon** / Any dungeon / Overworld / Anywhere | Own dungeon |
| Small keys: **Own dungeon** / Any dungeon / Overworld / Anywhere | Own dungeon |
| Boss keys: **Own dungeon** / Any dungeon / Overworld / Anywhere | Own dungeon |
| Skip the opening movies | on |
| Skippable automatic dialogues | on |
| Skippable title demo and credits | on |
| Night Gold Skulltulas also by day | off |
| Gossip stone hints: No hints / **Need nothing** / Mask of Truth / Stone of Agony | Need nothing |
| Hint distribution: Useless / **Balanced** / Strong / Very strong | Balanced |

Off, a shuffle setting leaves those checks with the game's own item (logic counts it where it is).

## Character

The **Character** page dresses adult Link as one of 26 characters: Ganondorf, Phantom Ganon, Zelda, Sheik, Impa, Nabooru,
Ruto, Rauru, the Great Fairy, Malon, Talon, Ingo, townsfolk (the Bombchu Bowling lady, the Cucco Lady, Richard's lady,
the Happy Mask salesman, the Running Man, Shiro the carpenter, the Poe collector, a soldier) and monsters (Lizalfos,
Dinolfos, Wolfos, Stalfos, Stalchild, ReDead).

Choose one and press Apply whenever the game is closed. It builds a second mod beside the seed's (`mods\PlayAs<Name>`, a
few seconds, from the game's own files) and turns the last character off; "Link, as he is" turns it off. The seed, its
logic and your save are untouched. The character is worn as the Goron and Zora tunics, with its own cloth and voice; in
the Kokiri tunic Link is Link, and young Link is never changed. The window rebuilds the character by itself after a new
seed is installed or the seed is turned on or off.

Without the window: `LostWoods.exe character <game folder> --list`, `--as zelda`, `--as link`, `--check`.

## Command line

```
LostWoods.exe randomize "C:\Games\Longshot" --seed anything
LostWoods.exe character "C:\Games\Longshot" --as zelda
LostWoods.exe verify "C:\Games\Longshot\romfs" "C:\Games\Longshot\mods\HookshotRando"
```

From source, `python randomize.py ...` and `python -m rando.playas ...` do the same.

The mod goes to `<game folder>\mods\HookshotRando`, with `spoiler.txt` (where everything is, and a playthrough) and
`placements.json` beside its `romfs`. A new seed replaces the last one (kept in `rando-archive`). **Start a new game for
each seed**: a save keeps its chests opened. To play without the mod, rename the folder to start with `_`.

| Option | |
|---|---|
| `--seed TEXT` | The same seed gives the same game. Without it, a new random seed |
| `--no-<setting>` / `--<setting>` | Any on/off setting off (on by default) or on (off by default), e.g. `--no-skip-intro`, `--skulltulas-day-and-night` |
| `--gossip-stone-hints CHOICE` / `--hint-distribution CHOICE` | `none`, `need_nothing`, `mask_of_truth`, `stone_of_agony` / `useless`, `balanced`, `strong`, `very_strong` |
| `--shuffle-maps-compasses` / `--shuffle-small-keys` / `--shuffle-boss-keys PLACE` | `own_dungeon` (default), `any_dungeon`, `overworld` (not all three), `anywhere` |

## Sharing

Share the seed text, never a generated `mods\HookshotRando` or `mods\PlayAs<Name>`: those hold files made from the game.
Each player generates on their own copy; the same seed and settings give everyone the same game.

## What it does

- **Every one-time chest is randomized**: 180 locations, 32 of them chests only the remake has, each with glitchless
  logic built for the remake's rooms, doors and keys.
- **NPCs' and minigames' prizes** (36: the Skull Kid, the scrubs' upgrades, bowling, the shooting galleries, the House of
  Skulltula, fishing, the frogs, horseback archery, Dampe, the dog, Talon, Anju, King Zora, Darunia...) give the item
  placed there.
- **Songs are shuffled** (12): each song's cutscene gives the item placed there. A song found elsewhere shows Sheik's harp.
- **Items lying in the world** (the 14 loose Heart Pieces, the 8 bosses' Heart Containers and 2 freestanding keys) are
  the item placed there, lying where the old one was.
- **Zelda's Letter, the Light Arrows, the Fairy Ocarina, the Ocarina of Time, the Great Fairies' gifts and the Fire
  Arrows at Lake Hylia** can each join the pool. An ocarina found elsewhere is made playable on the next item get.
- **Gold Skulltula tokens can be shuffled**: each of the 100 Gold Skulltulas drops the item placed there, floating where
  it dies. A token found anywhere counts for the House of Skulltula.
- **Shops can sell items of the pool**: a number of shelves per shop, or random. A bought shelf shows "Sold Out"; the
  shelves logic needs (shields, tunics, Deku nuts and sticks, Bombchus) go last.
- **Dungeon rewards can be shuffled** among the 8 bosses and Rauru (a stone never behind the Door of Time).
- **Keys, boss keys, maps and compasses where you choose**: own dungeon, any dungeon, overworld or anywhere. Outside its
  dungeon an item is the dungeon's own, "Small Key (Forest Temple)", and works wherever it is found.
- **Gossip stone hints**: way of the hero, foolish areas, item hints, always hints, in all 16 languages, with the game's
  own names of areas and items.
- **Every seed can be finished**: each seed is played through by the logic from a new game before it is installed. No
  tricks or glitches are needed.
- **Upgrades come in order**: bags, quivers, wallets, scales, the Hookshot before the Longshot, the bracelet before the
  gauntlets.
- **Ammunition after its container**: bombs and Bombchus only where a bomb bag is needed to get there, arrows only where
  the Bow is.

### Fixes for the remake's story locks

Without these, a randomized seed can reach a dead end the original game never meets. They are always on.

- **Mido** keeps his post until he lets you pass, and the tunnel Kokiri lets you out after the Deku Tree, Zelda met or not.
- **King Zora** stays out of the way after the letter, whichever way you came into Zora's Domain.
- **Bombs open Dodongo's Cavern**: a bomb at the boulder plays the bomb flower's scene and breaks it.
- **Bombs without the Goron's Bracelet**: a bomb bag is enough; bomb flowers still need the bracelet.
- **Darunia's bracelet** after his quest has moved on: Saria's Song or a talk still gives his gift.
- **Back to child as soon as you are adult**, not only after the Forest Temple.
- **Zora's River** without its invisible walls: a child swims down past the boulders, as in the original.
- **Great Fairies in any order**: every fountain opens with Zelda's Lullaby.
- **The clock runs from the start**: night falls before Zelda is met.
- **The Water Temple's gate switch** is free of its invisible wall.
- **A starting quiver and seed bag**: the remake's Bow and Slingshot hold no ammunition by themselves.

Twelve chests new in the remake only ever hold junk (rupees, ammunition, seeds), so no seed depends on reaching them.
The Deku Tree's slingshot room can lock you in (its ladder drops only for the Slingshot or the Boomerang): the game
autosaves before the room, so load that save.

## How it is made

`rando/logic` is the world's logic in Python: regions, exits, events and item rules, with the remake's changes in
`data/locations.json` and `data/overrides.json` (built by `tools/build_locations.py` from the research in `research/`).
`tools/check_remake.py`, `tools/check_seeds.py` and `tools/verify_mod.py` check the logic, many seeds, and a generated mod
against the game's files; `tools/check_evfl.py` checks the event-flow writer against every event flow of the game. The
character builder lives in `rando/playas/`, and `tools/draw_character.py` draws a character as it is worn, without the
game.

## Credits

- [Longshot](https://git.magicbean.dev/MagicBeanDev/Longshot), which runs the game and loads its mods.
- The OotrR randomizer (MIT): several fixes and quality-of-life patches follow its approach, reimplemented here.
- The logic is a port of Ship of Harkinian's randomizer logic (its repository carries no license), adapted to the
  remake.
