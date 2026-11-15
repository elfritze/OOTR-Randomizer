# HookshotRando

A randomizer for The Legend of Zelda: Ocarina of Time (Nintendo Switch 2) as [Longshot](https://git.magicbean.dev/MagicBeanDev/Longshot)
runs it. It is a RomFS mod: no change to Longshot, nothing to rebuild. You make it from your own copy of the game.

## The window

`python gui.py` opens the app (public name in progress: **Lost Woods**): choose the game folder, the seed and the settings,
generate and install the seed (refused while the game runs), verify it, turn it on or off, open the spoiler log; the
**Tracker** page reads the game's save every few seconds and shows the seed's checks on each area's map, coloured by what
logic reaches with what Link holds. With `python -m pip install texture2ddecoder` the maps are the game's own pause-menu
maps (dungeons floor by floor), placed by the camera the game captured them with (`Game/MapCaptureInfo`, see
`rando/maptex.py`); without it, each area is drawn from its placed objects. Checks inside buildings and grottos, which the
remake builds away from the drawn map, are listed under it. A check is marked done by itself when the save shows it taken:
a loose item's own key, a gift's one-time flag or song cutscene, an item held that only that check gives, a dungeon's map,
compass, boss key and (all of its) small keys. The save keeps no flag of an opened chest, so chests of rupees and ammunition
are marked by a click, or all of an area's at once ("Mark area done"). Comparison with the OotrR
randomizer: `docs/COMPARISON.md`; Archipelago plan: `docs/ARCHIPELAGO.md`; what comes next: `docs/ROADMAP.md`.

The **Settings** page groups the settings as Ship of Harkinian's randomizer does (`rando/settings.py`), with only what this
randomizer does; SoH's other choices are shown fixed, with why. Installing a seed first copies the one installed before
(the whole mod folder) to `<game folder>\rando-archive\<seed>-<time>`.

| Setting | Default | Seen in game |
|---|---|---|
| Shuffle songs | on | yes |
| Shuffle gifts and prizes (36 NPC and minigame checks, Darunia's bracelet among them) | on | yes (Darunia: not yet) |
| Shuffle freestanding Heart Pieces (and bosses' Heart Containers, 22) | on | yes |
| Shuffle Zelda's Letter and the Light Arrows (her two scenes give the item placed there) | off | not yet |
| Shuffle the Fairy Ocarina (Saria's gift; an ocarina found elsewhere made playable, OotrR's fix) | off | not yet |
| Shuffle Great Fairies (their 6 gifts in the pool; Nayru's and Ganon's Castle's need the 500-rupee wallet) | off | not yet |
| Shuffle Gold Skulltula tokens (the 100 skulltulas drop the item placed there; the tokens in the pool) | off | not yet |
| Shuffle dungeon rewards: **Vanilla** / End of dungeon (the 9 stones and medallions among the 8 bosses and Rauru) | Vanilla | not yet |
| Maps and compasses: **Own dungeon** / Any dungeon / Overworld / Anywhere | Own dungeon | yes (own items) |
| Small keys: **Own dungeon** / Any dungeon / Overworld / Anywhere | Own dungeon | yes (own items) |
| Boss keys (Ganon's Castle's too): **Own dungeon** / Any dungeon / Overworld / Anywhere | Own dungeon | yes (own items) |
| Skip the opening movies | on | yes |
| Fast chests: retired for now (`rando/qol.py` kept): small chests crashed the game as they opened (seed 7cc65105, 2026-11-15) | off | crashed |
| Skippable automatic dialogues: the 12 step-started sequences (Navi, minigame rules) skip with + | on | not yet |
| Skippable title demo and credits | on | not yet |
| Night Gold Skulltulas also by day (30) | off | not yet |
| Gossip stone hints: No hints / **Need nothing** / Mask of Truth / Stone of Agony | Need nothing | not yet |
| Hint distribution: Useless / **Balanced** / Strong / Very strong | Balanced | not yet |

Off, a shuffle setting leaves those checks with the game's own item (logic counts it where it is). The quality-of-life
settings follow the OotrR randomizer's patches (MIT), reimplemented on this project's formats (`rando/formats/evfl_edit.py`
writes any change to a flowchart and reads it back).

Gossip stone hints (`rando/hints.py`) follow SoH's: its distributions (way of the hero, foolish areas, item hints, its
always hints of the checks shuffled here, the trials' barrier, junk), the way of the hero worked out as SoH does (the
playthrough pared down, then each check the game cannot be beaten without), a hint's first copy on a stone reachable
without its item. Each of the remake's 37 stones says its rumor by its own name (`GOSSIP_<AREA>_NN` in
`EventFlowMsg/GossipStone.msbt`), so a hint replaces that message in all 16 languages, with the game's own names of
areas (`LocationMsg/Location.msbt`) and items in red; a junk hint keeps the stone's rumor. The spoiler lists every stone.
Need nothing and Stone of Agony change the stones' talk (`GossipStone.bfevfl`); Mask of Truth is the game's own rule.

## Use

You need Longshot's game folder (it holds `romfs` and `mods`) and Python 3.10 or newer with `zstandard`
(`python -m pip install zstandard`).

```
python randomize.py "C:\Games\Longshot" --seed anything
```

The mod goes to `<game folder>\mods\HookshotRando`, with `spoiler.txt` (where everything is, and a playthrough) and
`placements.json` beside its `romfs`. A new seed replaces the last one (kept in `rando-archive`). **Start a new game for each seed**: a save keeps
its chests opened. To play without the mod, rename the folder to start with `_`.

| Option | |
|---|---|
| `--seed TEXT` | The same seed gives the same game. Without it, a new random seed |
| `--no-skip-intro` | Play the new game's two opening movies (skipped by default) |
| `--no-<setting>` / `--<setting>` | Any setting of the table above off (on by default) or on (off by default), e.g. `--no-fast-chests`, `--skulltulas-day-and-night` |
| `--gossip-stone-hints CHOICE` / `--hint-distribution CHOICE` | `none`, `need_nothing`, `mask_of_truth`, `stone_of_agony` / `useless`, `balanced`, `strong`, `very_strong` |
| `--shuffle-maps-compasses` / `--shuffle-small-keys` / `--shuffle-boss-keys PLACE` | `own_dungeon` (default), `any_dungeon`, `overworld` (not all three), `anywhere` |

## Sharing

Share this folder (the code), never a generated `mods\HookshotRando`: that holds files made from the game. Each player runs
`randomize.py` on their own copy; the same seed text gives everyone the same game.

## What it does

- **Every one-time chest is randomized**: 180 locations (148 of SoH's checks, 32 chests only the remake has), each with
  the logic of Ship of Harkinian's randomizer, adapted where the remake changed a room, a door or a key.
- **NPCs' and minigames' prizes** (36: the Skull Kid, the scrubs' upgrades, bowling, the shooting galleries, the House of
  Skulltula, fishing, the frogs, horseback archery, Dampe, the dog, Talon, Anju, King Zora, Darunia...) give the item placed
  there: `data/gifts.json` names each event parameter that says what is given.
- **Zelda's Letter and the Light Arrows can be shuffled**: her garden scene gives its item by the get event NPCs use
  (any item), her Temple of Time scene by its get window (an `Item_` actor only, as Darunia). The letter, found
  anywhere, is what Kakariko's guard takes to open the gate (his own flow checks the pouch). Not yet seen in game.
- **The Fairy Ocarina can be shuffled**: Saria's bridge scene adds the item placed there and shows its window (an
  `Item_` actor only). An ocarina found away from her bridge never got its action guide (OotrR saw it unplayable):
  OotrR's fix, rewritten here, runs that guide (once: the game shows it once) on the first item get with the Fairy
  Ocarina held. The ocarina never goes in a chest or an NPC's hands: it has no get pose (OotrR: those crashed the
  game), so it lies in the world (a pickup; OotrR's are built on the token, ours on the Fire Arrows: to see) or stays
  Saria's. The Ocarina of Time stays at the moat (its scene teaches the Song of Time, Link playing along). To see:
  the Fairy Ocarina got after the Ocarina of Time (a downgrade?). Not yet seen in game.
- **Great Fairies can be shuffled**: each fairy's gift event gives the item placed there, and her "had it?" switch
  (IsGet of her own item: with another item there she would sell it again on every visit) asks a saved flag of her own
  instead (`rando/gamedata.py` adds it to the game's data list), set just before her gift. She still asks the game's
  price (Din 25, the mountain's 50, Farore 100, the crater's 200, Nayru 300, the castle's 500): logic asks the 500-rupee
  wallet for the last two (as you saw: four fairies with the 200-rupee wallet, then 300 and 500). The magic meter and
  its double are one progressive item, given in order. Not yet seen in game.
- **Gold Skulltula tokens can be shuffled** (SoH's Tokensanity, all): the remake's 100 Gold Skulltulas are mapped one
  to one to SoH's checks in `data/skulltulas.json` (from the maps: positions, room indices, night and bean-soil flags,
  the chests around; 83 sure, 10 likely, 7 by elimination). Each drops the item placed there through its own
  `Drop__DropActor` (an instance parameter of the skulltula; its drop table gives the token otherwise), as a pickup built
  on the token (OotrR's way: the token's AI saves the skulltula once its drop is got, it floats where the skulltula
  died and is caught by hookshot or boomerang as SoH counts). The 11 not sure (matched by elimination, or moved in the
  remake) get junk only. A token found anywhere counts for the House of Skulltula. Not yet seen in game.
- **Dungeon rewards can be shuffled** (SoH's End of Dungeon): the 3 spiritual stones and 6 medallions among the 8 bosses
  and Rauru, placed first by logic (a stone never behind the Door of Time). Each reward's scene gives it by its
  GetPouchContent window's `ActorName` (the Jabu-Jabu and Zora's Fountain scenes both, and the `.110` twins); the scene
  itself still shows the game's own reward. No event of the game asks for a stone or a medallion by name (only these
  scenes name them); the remake's own story checks are not yet traced. Not yet seen in game.
- **The Goron's Bracelet is in the pool** (with gifts shuffled): Darunia's dance scene and the two ways the randomizer adds
  for him (Saria's Song past his dance, his talk) give the item placed at his check, his line naming it; he gives an item
  only (no rupee, song or dungeon item: a silent pouch add is proven for those). The bracelet, the Silver and the Golden
  Gauntlets come in that order (the fill keeps each unreachable without the one before). Not yet seen in game.
- **Items lying in the world** (the 14 loose Heart Pieces, the 8 bosses' Heart Containers and 2 freestanding keys) are the item placed there,
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
- **Keys, boss keys, maps and compasses where you choose** (SoH's Shuffle Dungeon Items: own dungeon, any dungeon,
  overworld, anywhere; not all three in the overworld: 65 items for about 60 places outside the dungeons). The
  game's key is one item for every dungeon, counting for the dungeon it is picked up in; elsewhere, or as a map, compass
  or boss key in a small chest (whose flow never gives those), the dungeon gets an item of its own, "Small Key (Forest
  Temple)", its dungeon's name coloured in the get message. It is credited as soon as its get ends (seen in game: two
  Forest Temple small keys, its boss key and map and the Fire Temple's compass from Kokiri Forest's chests). In chests and
  lying in the world (a pickup made of it; not yet seen in game), never as an NPC's gift (a gift may not end in the get
  flow that credits it). The Shadow Temple's and Bottom of the Well's freestanding keys are checks too. Logic counts the keys the same wherever they are: SoH unlocks the Fire Temple's boss key loop door itself when
  keys stay home and not otherwise, but the remake's door is always locked (`fill.soh_options`).
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
  (Saria's Song found only as an adult). Now, while Darunia has not given his gift (HavePlayedEvent.Dm_Goron_0030, set
  then): Saria's Song played to him past that step adds the bracelet before his dance, and talking to him with Saria's
  Song adds it and he says "Ya gotta play that song again for me sometime!" (`patches.darunia_bracelet_after_quest`). No
  "you got" window: check the gear screen. Seen in game 2026-11-14 (talk). The guard asks whether the gift was given, not
  whether the bracelet is had, so the gift can go in the item pool. The window was tried every way in his talk (the
  medallions' window, the House of Skulltula's item scene, with and without his line before): it never shows there and
  the talk waits for ever; to try later with InitTalk (the talk camera, Link joining) before it. Note for event edits: a
  flag switch's case 0 is TRUE, case 1 FALSE (`patches.IS_TRUE`/`IS_FALSE`).
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
