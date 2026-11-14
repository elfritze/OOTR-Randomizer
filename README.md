# HookshotRando

A randomizer for The Legend of Zelda: Ocarina of Time (Nintendo Switch 2) as [Longshot](https://git.magicbean.dev/MagicBeanDev/Longshot)
runs it. It is a RomFS mod: no change to Longshot, nothing to rebuild. You make it from your own copy of the game.

## Use

You need Longshot's game folder (it holds `romfs` and `mods`) and Python 3.10 or newer with `zstandard`
(`python -m pip install zstandard`).

```
python randomize.py "C:\Games\Longshot" --seed anything
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
- **You start with the small quiver and the small seed bag**: in the remake the Bow and the Slingshot hold no ammunition
  by themselves (a Bow found away from its own chest showed 0/0), and shops and scrubs sell arrows and seeds only once
  you have the small quiver and bag, which the game hands out with its own Bow and Slingshot. The new game's opening gives
  both, silently (as the OotrR randomizer does); the bigger quivers and bags found later raise them to 40 and 50. Not
  yet confirmed in game.
- **Every seed can be finished**: the fill (SoH's way: dungeon items first, then assumed fill) is checked by playing the
  seed from a new game; a seed that fails is drawn again. No tricks or glitches are needed.
- **Keys, boss keys, maps and compasses stay in their own dungeon**: the remake has one key item for every dungeon, which
  counts for the dungeon it is picked up in.
- **Songs are shuffled** (12: Saria, Malon, Impa, the Royal Family's Tomb, the castle moat, the windmill and Sheik's six):
  each song's cutscene gives the item placed there, and the lesson's own silent add of the song is switched off (else the
  song would be learned as well). The windmill man gives once, then never again. A song found elsewhere shows Sheik's harp
  (the game has no model for songs). Playing a song got outside its own cutscene works (seen in game: Zelda's Lullaby from a
  Heart Piece spot opened Zora's Domain). `--no-shuffle-songs` leaves each song where it is.
- **Chest events**: the Navi lines and scenes made for a chest's own item are dropped when the item changes; the ones the
  story needs stay (Sheik's Serenade after the Ice Cavern's chest, Nabooru's capture, Dampe's race, Ruto's room).
- **Order**: the Longshot never before the Hookshot, the Golden Gauntlets never before the Silver ones, the Silver ones
  never before Darunia's bracelet (the remake has them as separate items).
- **Ammunition after its container**: bombs and Bombchus only where a bomb bag is needed to get there, arrows only where the
  Bow is (the game hands them out without one).
- **Bombs without the Goron's Bracelet**: the remake gives Link's own bombs the bomb flowers' lift grade, so without the
  bracelet he takes a bomb out and puts it back. The mod gives them the grade Bombchus have (nothing needed; found by the
  OotrR randomizer): a bomb bag is enough, as in SoH. Bomb flowers still need the bracelet.
- **Bombs open Dodongo's Cavern**: the remake's boulder over the entrance has no life, so bombs do nothing to it; only
  the bomb flower above breaks it, by a scene (its bomb flies to the boulder), and picking that flower needs the Goron's
  Bracelet. The trail's logic also watches for the player's bombs at the boulder, connected to nothing; the mod connects
  it and lets it set off the scene by itself (`patches.dc_bombs_set_off_flower`): a bomb dropped at the boulder plays the
  scene and breaks it (seen in game). The logic asks a child for the bomb bag there (Bombchus are not watched; the bomb
  flower's own way still works in two of its three areas, not yet seen with the mod, so the bracelet is not counted).
  Changing the boulder, or the flower's actor file, crashed the game.
- **Darunia's bracelet after his quest has moved on**: breaking that boulder moves Darunia's quest to "explore Dodongo's
  Cavern" from any step (seen in game), and beating King Dodongo moves it on too; past his dance's step, Saria's Song only
  makes him dance and talk, the bracelet's scene never comes. The game never gets there without the dance; a seed does
  (Saria's Song found only as an adult). His talk after the song now also adds the bracelet, silently
  (`patches.darunia_bracelet_after_quest`); after the dance it is had already. Not yet confirmed in game.
- **Back to child as soon as you are adult**: the remake's Master Sword takes Link back to child only once the Forest
  Temple is done (the Temple of Time's logic removes the sword's interaction until then; seen in game: no way back). The
  original game and SoH's logic let him go back at once, and a seed can need it (a child-only item for the Forest Temple).
  The mod disconnects that removal (`patches.free_time_travel`). Not yet confirmed in game.
- **Zora's River without its invisible walls**: the remake puts seven invisible walls in the river across the line of the
  two bomb boulders, so a child who came in upstream (the Lost Woods dive) and swims down is stopped there and held by the
  current. The mod makes them never appear (a condition each wall can never meet; their collision is baked into the map,
  so they are not deleted). Confirmed in game: a child swims down past the boulders, as in the original, so the logic
  keeps SoH's rule (with closed forest, the Lost Woods dive and this swim can be the way out of the forest).
- **Mido keeps his place until he lets you pass**: in the remake, once you have met Zelda, Mido moves away from the
  Deku Tree path, but his invisible wall stays until he has seen the Kokiri Sword and a shield. The game never meets that
  (Zelda comes after the Deku Tree); a seed can, and the way to the Deku Tree was then shut for good. The mod takes his
  "after Zelda" place out of his schedule (`patches.mido_keeps_blocking`): he stays at his post with the talk that lets you
  pass, and after the Kokiri Emerald he goes where the game puts him then. Seen in game.
- **King Zora stays out of the way after the letter**: the first time you enter Zora's Domain from Zora's River, its
  arrival scene sets the Ruto quest back to its start, whatever it was. The game always comes that way first; a seed
  can come in from Lake Hylia under water, show the letter, and then take the river's way in: King Zora went back to his
  seat for good, the letter gone. Showing him the letter now also marks the arrival scene as seen
  (`patches.zora_arrival_after_letter`), so it never comes after the letter (you skip it only if you came in another way).
- **Into Kokiri Forest from the bridge**: as a child, the Kokiri in the tunnel between the Lost Woods bridge and the village
  stands behind an invisible wall until you talk to him after the Kokiri Emerald, and it stops you going in as well as out.
  SoH lets the bridge always lead into the forest; here, as a child, it needs the Deku Tree beaten.
- **The Deku Tree's slingshot room can lock you in**, as in SoH's randomizer: its way out is a ladder its eye switch drops,
  and only the Slingshot and the Boomerang hit it (Bombchus do not). The game autosaves before the room: load that save.

Left as they are for now (`data/gifts.json` "excluded" has each one's reason): the Scarecrow's Song,
the stones and medallions, the Master Sword, the Light and Fire Arrows, the ocarinas, Zelda's Letter and the Weird Egg, the
adult trade items, the Gerudo keys and card, the Great Fairies (they charge rupees in the remake and would sell again),
Darunia's bracelet, the shops and repeatable prizes. King Zora's Zora Tunic shop gift stays: without a tunic, his later
talk makes the Zora shop give one free (an extra tunic, never needed by logic).

Left as they are: the 22 minigame chests filled again at each play (the treasure chest game's but its Heart Piece prize,
the Hall of Fallen Foes, Dampe's race rupees) and the ice-trap chests (they hold no item).

## Chests that only get junk (until confirmed in game)

These 12 chests are new in the remake, and the research could not tell how to get to them (`confidence: low` in
`data/locations.json`). Until someone finds the way in, every seed puts only junk in them (rupees, ammunition, the Scrub
seeds), so no seed can depend on one. Once a way in is confirmed, its rule goes into the table and the chest joins the
normal fill. (Rule of the code: `rando/generate.py`, `Setup`: remake-only chests with confidence `low`.)

| Chest | Where | What is not known / what to check |
|---|---|---|
| Lost Woods, under the bridge | Small chest (purple rupee) on a ledge about 9 m above the Deku Scrub that sells the stick upgrade, near the bridge between Kokiri Forest and Hyrule Field | How to get onto the ledge. Not found in game (2026-11-13): a seed that put the Silver Scale here could not be finished |
| Lon Lon Ranch tower | Small chest (Scrub seed) on an upper floor of the tower, about 11 m above the loose Heart Piece and the crates | How the upper floor is reached (ladder, crates, which age) |
| Jabu-Jabu's Belly, B1 room with Octoroks | Small chest (red rupee) on the far ledge by the room's four pots, across the water | How to cross the water to that ledge without tricks |
| Bottom of the Well, main room | Small chest (blue rupee) in a sunken trench on the east side, outside the bars of the Like-Like cage | Whether it is the old Like-Like chest moved, and whether the ladder by it is the only way out |
| Gerudo's Fortress grotto | Small chest (red rupee) in the fortress's only grotto, with flying pots and a Skulltula | Whether the grotto's hole is open (no cover found) and what it needs as adult |
| Gerudo Training Ground, Like-Like room | Small chest (Scrub seed) that falls when the eye switch above it is hit | That hitting the eye switch is all it takes |
| Gerudo Valley, Octorok grotto | Small chest (Scrub seed) under water past the Octoroks, in the grotto under the silver boulder | Whether the water needs a dive (Silver Scale) or Iron Boots |
| Goron City, secret hole: wrong answer | Small chest (green rupee) the sign puzzle makes appear for a wrong answer | How the puzzle works and whether this chest stays once the right one is out |
| Goron City, secret hole: right answer | Small chest (purple rupee) the sign puzzle makes appear for the right answer | What the puzzle asks (it reads the signs: is it always solvable?) |
| Goron City, maze | A 4th small chest (blue rupee) next to the center chest and the gossip stone, behind silver rocks | Whether the center chest's way in (bombs or the Silver Gauntlets) is the same |
| Kakariko windmill (adult copy) | The windmill-top chest's copy in the adult map (purple rupee), same place, separate chest | Whether opening it as a child also opens it as an adult, and how the top is reached |
| Water Temple, south-west lake floor | Big chest with the compass, by the central pillar, reached over hookshot targets a floor switch raises | Which water level it needs and whether the switch is always reachable |

## Not yet confirmed in game

The logic for these comes from reading the game's data, not from playing; each is set so that it cannot leave you stuck
(when unsure, it asks for more, not less). `research/mapping/*.json` has every chest's evidence and the full list.

- The Fire Temple's locked door in the lava geyser room, and the 5F chests by the scarecrow.
- The Spirit Temple's sun block room (chest from the sun blocks, doors from the silver rupees).
- Grottos changed by the remake: Hyrule Field's tektite grotto.
- Zora's River: whether an adult gets past the boulders without breaking them (SoH's rule).

## How it is made

`rando/logic` is SoH's logic (commit d4bf6528) translated to Python by `tools/port_soh_logic.py` and checked rule by rule;
`data/locations.json` and `data/overrides.json` are the remake's chests and its changes to SoH's map of the world,
built by `tools/build_locations.py` from the research in `research/`. `tools/check_remake.py`, `tools/check_seeds.py` and
`tools/verify_mod.py` check the logic, many seeds, and a generated mod against the game's files; `tools/check_evfl.py`
checks the event-flow writer (relocation tables, DICs, added events) against every event flow of the game.

Ship of Harkinian's repository carries no license; this port of its logic is derived from it.
