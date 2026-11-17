# Archipelago plan

Goal: "Lost Woods" seeds playable in an Archipelago multiworld, as OotrR's "OoT Remake" game already is.

## Built (2026-11-14)

- `rando/archipelago.py`: **stable ids** for every check (249) and pool item (68 kinds), from a SHA-256 of the name, in their
  own range; `python -m rando.archipelago <romfs> <out.apworld>` builds **`lost_woods.apworld`**:
  - `lost_woods/__init__.py`: the `World` (one region; each location's rule asks our own logic whether its check is
    reached with the player's items, cached per item set);
  - `lost_woods/rando/`, `lost_woods/data/`: the randomizer and its tables, so the logic is exactly the one solo seeds use
    (with the remake's changes); `lw.reach()` also collects what the game gives unshuffled (shops, prizes left as
    they are), as `generate.Setup` does;
  - the item pool: one item per location, the vanilla contents (as the solo fill's pool).
- Checked without Archipelago (not installed here): the package loads with stand-in classes, 249 locations, 249 items,
  7 checks reachable from nothing (the tracker agrees), 27 with sword + shield + slingshot + bomb bag; it runs without
  `zstandard`.

## Not yet tested

Nothing has run inside Archipelago. First step tomorrow: install Archipelago (0.6.x), drop the apworld in
`custom_worlds`, generate a solo multiworld with a YAML (`game: Ocarina of Time Remake (Lost Woods)`), fix what breaks.

## Still to do, in order

1. **Apworld completeness**: options (songs shuffled, intro skip) as Archipelago options; junk-only chests
   (`generate.Setup.closed`) as excluded locations; the solo fill's constraints (dungeon items in their dungeon, ammunition
   after its container, ORDERED pairs, tier order) as `pre_fill`/item rules; `generate_output` writing a patch file
   (`.aplw`: placements of this world, with foreign items marked).
2. **Install from a patch**: the app builds the mod from the patch instead of its own fill (`generate.generate` with given
   placements); a foreign item needs an in-game form: OotrR shows an "Archipelago medallion" (a model copy with its own
   textures) with the item's and player's names in its texts (MSBT, 16 languages). Simplest first form: an existing
   neutral model (a gold rupee?) named by its text.
3. **Knowing what was checked** (also what the tracker needs): today opening a chest writes no flag of its own (OotrR's
   save tests); OotrR gives each chest a saved flag by cloning its `EventSetting` row (`RandoChest_<hash>`: the row's entry
   point sets the flag then runs the original). Gifts have their NPC's own flags; loose items their Bool64bitKey. Read from
   the save (`rando/savefile.py`), and live from the game's memory (OotrR: ReadProcessMemory on longshot.exe, guest base
   0x100000000000, GameData at 0x84C9E180).
4. **Receiving items in game**: the game never re-reads files in a session, so each receivable item is baked in at build
   time. OotrR adds, per item, a watcher to `Sequence/MainUpdate.module.ainb` (Recv flag set -> request event
   `RandoAP_<key>` -> reset), the event giving the item with the get pose and setting a Got flag; the client sets Recv in
   memory. We now know logic modules take in-place edits safely, but adding nodes to an AINB is new work (OotrR uses the
   `ainb` package for it). Alternative to study: Longshot's control bridge (Longshot #58 streams game state), if it can
   write GameData flags.
5. **Client**: Archipelago's WebSocket protocol (Connect, LocationChecks, ReceivedItems, StatusUpdate on Ganon's defeat),
   in the app's window (a page beside the tracker), sending checks from step 3 and setting Recv flags for step 4.

## Things learned that apply here

- Never edit an existing actor's ActorParam (four crashes); logic modules, AI files and event flows take in-place edits.
- New flags in saves need registering in GameDataList (OotrR: `tracking_metadata.add_saved_flags`, the save grows 8
  bytes per flag) and a new game.
