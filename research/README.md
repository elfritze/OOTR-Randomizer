Research data for mapping the remake's chests to Shipwright (SoH) checks. Game data never leaves this PC: nothing here is
a game file, only facts read from it.

- chest_context.json: every remake chest (203, by placement Hash): map files, Gyaml (Obj_TBox_A_01 small, A_02 big,
  GlassTruth = invisible/lens, HrlCity_Shop = treasure chest game, NoBake = no difference to logic), vanilla Drop__DropActor,
  GetEventName, Dynamic params (DefaultDungeonRoomIndex = dungeon room, SpawnType = appears on a condition), position
  (metres), links to/from other actors, the AiGroups logic modules referencing it (room prefabs), the nearest notable actors.
- soh_chests.json: every SoH chest check (location_list.cpp): rc, quest (skip RCQUEST_MQ), scene, N64 actor params, name,
  vanilla item.
- mapping/<group>.json: results, one file per area group (see the schema in each).
- The game data itself: C:/Projects/ootremake-recomp/Longshot-Build/romfs, read with the rando package
  (rando.formats.zs.Codec, byml, sarc, evfl; rando.events.Events for event flows, rando.chests).
- SoH sources: C:/Projects/ootremake-recomp/Shipwright/soh/soh/Enhancements/randomizer (location_access/ for regions and
  rules, location_list.cpp for checks, logic.cpp for helpers).
