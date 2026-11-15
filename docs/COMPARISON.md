# Our randomizer vs OotrR (2026-11-14)

OotrR = github.com/Mozencaz/OotrR, app 0.5.2 / generator 0.8.0, ~24k lines of Python (pulled 2026-11-14, `d5dfd39`).
Ours = this folder (HookshotRando, working name). Both make a RomFS mod for the Switch 2 remake from the player's own
copy, both target Hookshot/Longshot, both were built with Claude Code.

## In one paragraph

OotrR is **wider**: many more things can be shuffled (skulltulas, shops, pots, fairies, dungeon rewards, keys, enemy
"souls"), it has a polished app (presets, auto-tracker reading the save and the game's memory, an in-game overlay,
signed auto-updates, portable builds) and a working **Archipelago** multiworld. We are **deeper** on the remake itself:
our logic is Ship of Harkinian's (finer, with time of day and per-room regions), every remake chest was researched one by
one, songs are shuffled, and we fixed story locks of the remake that OotrR does not handle at all — and that can
make *their* seeds impossible to finish (the Master Sword / Forest Temple lock, King Zora, the Dodongo's Cavern
boulder, Darunia, Zora's River's walls).

## What OotrR does that we don't

| Area | OotrR | Us |
|---|---|---|
| Gold Skulltulas | 100 tokens shuffled (off/dungeons/overworld/all) | not shuffled |
| Shops | 64 stalls, 1-4 items per shop, price 10, bought once | not shuffled |
| Pots, crates, beehives, bushes, rocks | shuffled, reward on the first pickup only, then vanilla loot | no |
| Dungeon rewards | 3 stones + 6 medallions shuffled | vanilla |
| Great Fairies, quest rewards | Din/Farore/Nayru, magic, defense; ocarinas, Zelda's Letter, Light Arrows, Biggoron Sword | vanilla |
| Business scrubs | the 4 one-time remake scrubs | the scrubs' upgrades (as gifts) |
| Keys | key rings per dungeon, keys anywhere, boss keys anywhere, maps/compasses start-with/removed | keys stay in their dungeon |
| Enemy souls | 46 souls / 845 enemies (bosses, regional, all) | no |
| Starting inventory, item pool | start items, plentiful/balanced/scarce/minimal pools, presets, AP YAML import/export | 2 settings |
| Cutscenes | skippable intro and ~40 presentation cutscenes (with state "replay"), fast chests, auto dialogues skippable | skip of the two opening movies |
| Other QoL | open Kokiri Forest, Kokiri shop full from the start, night skulltulas always present, ocarina tutorial fix, Deku Tree emerald white-screen fix, Kokiri Sword chest cutscene skip, **Turbo A** (keyboard key remap) | none of these |
| Tracker | reads `progress.sav` every 2 s (structural save decoder), live game memory on Windows (Longshot/Hookshot and yuzu forks), accessibility per check, keys/souls views, manual fallback, **in-game overlay** HUD (Ctrl+Shift+O); per-chest saved flags added so chests can be tracked; save bound to the seed by a marker | none yet (being built tonight) |
| Archipelago | apworld built from the user's game, `.aprmk` patch, own WebSocket client, items received in game through watchers added to the game's main AI sequence + a memory write, foreign items shown as an "Archipelago medallion" model with real names, texts in 16 languages | none yet |
| Install | reads the `.nup` directly (emulators too), uninstalls the previous seed to an archive, refuses on a conflict with another mod, atomic staging | writes into Longshot's mods folder, replaces the last seed |
| App | Tk app with sidebar, presets, spoiler viewer (by zone/sphere), help; PyInstaller portable builds; **Ed25519-signed auto-updater**; CI | CLI + (tonight) a themed window |
| Tests | ~45 unit-test files, static verify of the output, deterministic cross-platform RNG | verify_mod, check_seeds, check_evfl, check_remake |

## What we do that OotrR doesn't

| Area | Us | OotrR |
|---|---|---|
| Songs | the 12 songs shuffled (lesson silent adds switched off, windmill man gives once, songs found elsewhere show Sheik's harp, **confirmed playable**) | songs never shuffled |
| Logic | Ship of Harkinian's logic, ported rule by rule (time of day, per-room regions, events), checked against SoH's C++ | Archipelago OoT 7.0 logic (coarser), no tricks |
| Remake chest table | every remake chest mapped with evidence and confidence (research/mapping), unknown ones junk-only | automatic matching (exact/group/area/junk) by geometry |
| **Back to child before the Forest Temple** | `free_time_travel`: the remake disables the Master Sword until the Forest Temple's sage; fixed (seen in game) | **not handled** — their logic (AP) assumes free time travel, so a seed needing a child item for the Forest Temple can dead-lock |
| **Dodongo's Cavern boulder** | bombs set off the boulder's own scene (`dc_bombs_set_off_flower`, seen in game); logic: bomb bag | **not handled** — AP logic says explosives open it; in the remake only the bracelet does |
| **King Zora** | the river's arrival scene no longer resets Ruto's quest after the letter | not handled |
| **Darunia's bracelet** | given after his quest has moved on (cavern broken early, King Dodongo first) | not handled (they keep the bracelet a fixed tier) |
| **Zora's River** | the 7 invisible walls at the boulders removed (seen in game): a child swims down as in N64 | not handled |
| Kokiri tunnel kid | logic knows his wall blocks the bridge way in until the Emerald | — |
| Mido | after-Zelda row removed (seen in game) | `keep_mido_at_post` (same idea) |
| Bombs without the bracelet, starting quiver/seed bag | yes | yes (both) |
| Loose items | made as real pickups of the item, raised on boss Heart Container spots | `Obj_Rando_*` from the gold-token template (same idea) |
| Look | dark "Hyrule at night" theme, DPI-aware | light parchment theme |
| Map tracker | being built (they have no map: a list only) | — |

## Takeaways

1. **Their missing story fixes are our edge.** Their seeds can be unfinishable for the same reasons ours were (we found
   each one by playing). Worth telling them? Their logic would also need SoH's rules to benefit.
2. **Their breadth is the gap to close**: skulltulas, shops, dungeon rewards, keys, cutscene skips and an auto-tracker
   are what players expect from a modern randomizer.
3. **Their techniques we can reuse** (reading their code is fine): the save decoder (`tracker/save_reader.py`), live
   memory offsets (`tracker/live_memory.py`), per-chest saved flags (`patching/chest_flags.py`), the Archipelago item
   delivery through `Sequence/MainUpdate.module.ainb` watchers (`patching/ap_mailbox.py`), MSBT text editing
   (`formats/msbt.py`), skip windows for cutscenes.
4. **Lessons we learned that they may hit**: never edit an existing actor's ActorParam (crashed the game four times for
   us); logic modules and event flows can be edited safely in place.
