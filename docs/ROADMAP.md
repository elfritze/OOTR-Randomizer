# What to do next, by priority (2026-11-14)

Order: what can leave a seed unfinishable first, then what players expect from a randomizer, then the app.

## P0: seeds that always finish

1. **Confirm in game what is built but not seen**: the starting quiver and seed bag (new game), the King Zora rescue and
   arrival fix, Darunia's bracelet after his quest moved on, the windmill man giving once, the bomb flower route at the
   Dodongo's Cavern boulder (bracelet), Sheik leaving after the Hookshot. Each is one line in README's "not yet confirmed".
2. **Hunt the remake's other story locks before players find them.** Every lock we hit was the same kind: the remake ties
   something to a story step the original did not (Mido, the tunnel kid, King Zora's arrival scene, the boulder setting
   the Goron quest, Darunia's dance, the Master Sword before the Forest Temple). Build an audit: list every logic module
   node that deletes or hides an actor (`Logic_Delete`, `Presence`) on a quest flag, and every event that sets a quest step
   unconditionally (`TriggerChallengeSetStep`, `EventExecuteProgressChallengeStep`), and check each against SoH's logic.
   This is the highest-value work: one missed lock is one dead seed.
3. **Per-check saved flags** (chests write none: checked on every save we have, 2026-11-14: the game's GameDataList
   registers a Bool64bitKey for all 180 chests, never set). Design, all pieces found (OotrR's chest_flags.py): a Bool per
   chest registered in `GameData/GameDataList` (template: a Bool with SaveFileIndex 0, ResetTypeValue 8; MetaData sizes
   grow 8 bytes each; older saves get the default); the chest's Dynamic `GetEventName` -> a new EventSetting row
   `RandoChest_<hash>` (copy of its event's row, new entry point); that entry, added to the chest flowchart, sets the flag
   then runs the original entry as a local subflow; a GameAnalyzedEventInfo row copied from the original's. Left to
   build: entry points in `evfl_edit.FlowEdit` (DIC + entries array); and the BYML writer gives GameDataList back 8 bytes
   shorter (same contents, another root offset): make it byte-exact before writing that file. Then the tracker reads
   `RandoCheck.<hash>` (and Archipelago sends them).
4. ~~Install safety~~: done 2026-11-14, `generate.archive_installed` (`<game>/rando-archive`).

## P1: what players expect

5. **Gold Skulltula tokens**: done 2026-11-15 (settings shuffle_tokens, `data/skulltulas.json`; to see in game: a
   drop other than a token, and the rule notes there: night-only flags, child access, the 11 closed ones).
6. **Dungeon rewards** (End of Dungeon done 2026-11-15, to see in game; Anywhere left), **Great Fairies** (done 2026-11-15:
   a once-flag each, the wallet for 300 and 500 rupees; to see in game), **quest rewards** (stones/medallions, magic/Din/Farore/Nayru, ocarinas, Zelda's Letter).
7. **Cutscene skips and fast chests**: fast chests, skippable step-started dialogues, title demo and credits done
   2026-11-14 (settings; to see in game). Left: OotrR's skip windows in cutscene flows (the native
   `EventTriggerSkipAcceptStart/SkipEnd`; never on mechanism cutscenes or talks) and area presentations (their name frame
   stays on screen when skipped without OotrR's flow fix), **open forest**, the Kokiri shop full from the start, starting
   items (SoH's Starting Inventory: pool swap + logic start).
8. **Shops and scrubs** (one-time buys). **Keys anywhere** done 2026-11-15 (`rando/dungeon_items.py`, seen in game;
   settings own / any dungeon / overworld / anywhere, chests and loose spots; the two freestanding keys are checks).
   Left: dungeon items as gifts (a gift not ending in ActionGuide credits at the next item get), key rings; to see in
   game: a dungeon item's pickup, a new pickup at a freestanding key's spot.
9. **Settings and presets**: a Settings page in SoH's groups done 2026-11-14 (shuffle songs / gifts / freestanding,
   timesavers, world; SoH's other choices shown fixed). Left: presets, a **spoiler page** in the app.
10. **Hints** from the gossip stones (neither randomizer has them: a real edge): done 2026-11-14 (`rando/hints.py`;
    SoH's kinds and distributions, all 16 languages; to see in game). Left: SoH's per-check sentences for item hints
    (now by area), its static hints (altar, Ganondorf, Sheik, Saria, Frogs...), hint clarity (obscure/ambiguous).
11. **Entrance shuffle** (neither has it; large).

## P2: the app

12. **Tracker**: done 2026-11-14: the game's map textures, calibrated by `Game/MapCaptureInfo` (dungeons per floor), and
    checks marked done from the save (loose keys, gift flags, song cutscenes, unique items held, dungeon items). Left:
    automatic marks for chests of rupees and ammunition once step 3 exists, an overlay over the game.
13. **Archipelago**: test the apworld in Archipelago, then patches, item receiving, client (`docs/ARCHIPELAGO.md`).
    Its dungeon items: each dungeon's own item (`items.own_actor`), written as the game's where that one works
    (`items.dungeon_form`).
14. **Packaging**: a portable exe (PyInstaller), signed updates, a public repository under the new name.
15. **Rename everywhere** once "Lost Woods" (or another) is chosen: the repository, the mod folder (needs a migration of an
    installed seed), the README.
16. **Tests**: unit tests for the formats (AINB, EVFL, SARC, save) and the patches' guards; they exist as tools today.

## Name ideas (the window says "Lost Woods" for now)

- **Lost Woods**: the forest that sends you anywhere; short, evocative, ties to randomness. (Chosen for the window.)
- **Kaepora**: the owl who tells you where to go next (fits a tracker and hints).
- **Song of Storms**: what shakes everything up.
- **Gossip Stone**: hints-first identity.
- **Timeshift**: young and adult Link, shuffled.
