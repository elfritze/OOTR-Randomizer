# Things to check in game

The logic for these comes from reading the game's data, not from playing it. Each is already set so it cannot leave
you stuck (when unsure, the logic asks for more, not less). What you find tells whether a rule can be relaxed or a
chest renamed. The evidence for each is in research/mapping/<group>.json.

## Overworld

- [ ] Mido's house: which corner pair holds the green-rupee chest as you enter, and what does SoH/N64 call each of the 4 corners? (Only names change; logic is the same.)
- [ ] LW under the bridge: is the purple chest on the 9 m ledge above the stick-upgrade scrub reachable as child without items? Can you walk from the Kokiri bridge to that scrub without the Longshot?
- [ ] LLR tower: how is the upper-floor chest (above the crawlspace Heart Piece) reached, and by which age?
- [ ] Kakariko windmill: how is the chest near the top of the windmill (adult) reached: ladder, hookshot, or the rotating platform?
- [ ] SFM upper grotto (bomb it open): does reaching the chest require playing the Song of Time at the 4 blocks?
- [ ] Graveyard Heart Piece grave: is the big chest visible without playing the Sun's Song?
- [ ] Hyrule Field tektite grotto (west of the Market) and Kak redead grotto (east field near Kakariko): confirm both open with the Song of Storms.
- [ ] Gerudo Fortress grotto: is it an open hole for adult (no song)?
- [ ] GV octorok grotto: is the chest underwater (iron boots) or wadable past the octoroks?
- [ ] Goron City secret hole: what opens its two chests (reading/answering the 6 signs?), and can both be taken?
- [ ] Goron City maze: confirm which of the two blue-rupee chests is reachable with bombs only, and whether the 4th needs the silver gauntlets.
- [ ] Hall of Fallen Foes: which interval-room chest sets appear in the 3-, 5- and 10-battle gauntlets, and do they appear after a real boss win only once or every run?
- [ ] Lake Hylia grotto: can the 4 timed candles be lit with Deku sticks?

## Deku Tree, Dodongo's Cavern, Jabu-Jabu, Bottom of the Well, Ice Cavern

- [ ] Jabu B1 jiggly room (room 13, Octoroks + swaying floor): can a child reach the pots ledge with the small chest (red rupee) without hover boots? If yes, its rule can be relaxed (and SoH's B1_JIGGLY->B1_JIGGLY_POTS exit too).
- [ ] Bottom of the Well, east trench chest (blue rupee, below floor level just outside the Like-Like cage bars): can it be reached from the main room without the lens, and is it clearly the Like-Like chest's replacement?
- [ ] Bottom of the Well: is the key chest the one through the fake wall on the right side near the front (N64 calls it 'right bottom'), and the rupee chest the front-left one?
- [ ] Deku Tree basement: does stepping on the floor switch by the webbed chest light the candle and burn the web by itself, or must Link bring fire?
- [ ] Deku Tree slingshot room: can the side-chest ledge be climbed by vines, or only by the ladder dropped by shooting the eye switch?
- [ ] Dodongo's Cavern stairs room: can the ladder to the new chest (south end, y~116) be climbed from the room floor before the stairs fall?
- [ ] Bottom of the Well room 11 (the balcony above Dead Hand): does its chest really need the lens (fake wall), and is it reached from the room before Dead Hand without climbing?

## Forest, Fire and Water Temples

- [ ] Fire Temple lava-geyser room (past the big lava room's second locked door): is there another locked door on the far wall at bridge level, and does it lead up to the ledge where you push the block onto the fire pillar? (decides the key-4 rule)
- [ ] Fire Temple boulder maze: is the big chest (map) in a side room off the maze's lower floor, and the Goron cell with a key on the raised upper part? (Boulder Maze Lower vs Upper)
- [ ] Fire Temple flame maze: is there a Goron cell with a small key (opened by a floor switch) inside the flame maze itself, where N64 had the compass room?
- [ ] Fire Temple top room with three chests on one pedestal: are they reached by stepping on the timed switch and hookshotting, and is Pierre still needed to get up there from the boulder maze?
- [ ] Forest Temple east courtyard: is the big map chest on the raised island in the pond (hookshot target nearby), and is N64's Blue Bubble map room between the courtyards' upper levels really gone?
- [ ] Forest Temple west courtyard: does the floor switch on the high ledge next to the Blue Bubble drain the well? Can the lobby's east door be opened from the lobby, or only by the floor switch on the courtyard side?
- [ ] Forest Temple falling-ceiling room: what does its chest give (no item is set for it in the map data)?
- [ ] Forest Temple basement: what reaches the arrow chest and opens the boss corridor now (pivoting floor, frozen eye switch): still the bracelet?
- [ ] Water Temple south-west room with the big compass chest: at what water level is it reachable, and are the hookshot targets raised by the floor switch needed?
- [ ] Water Temple: is there any chest in the river room, and is the small key in the room the river drops into (underwater switch, gate)?
- [ ] Water Temple: is the room behind the east tower's cracked wall chest-less (3 Shell Blades)?

## Shadow and Spirit Temples

- [ ] Shadow falling-spikes room: is there only one chest on top (the small key) and one on the floor, and is the top one there from the start (no switch)?
- [ ] Shadow: is the door from the huge pit's upper ledge into the invisible-scythe (Like Like) room unlocked? Is the door into the room before Bongo Bongo's door (after the boat) unlocked too?
- [ ] Shadow: does the door into the boss-key room (wooden spike walls, off the invisible-maze hub) need a small key, and does it lock you in until the 2 ReDeads are dead?
- [ ] Shadow wind hint room (2 ReDeads after the fan tunnel): can the invisible chest be opened without Lens of Truth? (SoH asks no Lens.)
- [ ] Spirit sun block room (child 2F): does the key chest appear by pushing the sun blocks into the light, with no torch to light? Do the doors out (to the Skulltula stairs and to the stairs back to the statue room) open only after the 5 silver rupees?
- [ ] Spirit topmost chest (behind the bombable wall near the big mirror): does it need the Mirror Shield, or only turning the two mirrors?
- [ ] Spirit: confirm the child climb room has one chest (bombchus), and that the 2F mirror room's second chest is a trap with no item.
- [ ] Desert Colossus Silver Gauntlets chest (overworld group): if its item is changed, chests.event_for drops SageOfSpirit_NaboorIsTakenAway (the Nabooru kidnapping cutscene Dm_DesertColossus_0030 and challenge step 07). Does the kidnapping still happen? SoH's LOGIC_SPIRIT_NABOORU_KIDNAPPED event depends on it: it lets a child without Gerudo speech into Spirit's child crawlspace.

## Gerudo Training Ground and Ganon's Castle

- [ ] GTG lobby: the eye switch above the entrance drops the RIGHT chest (blue rupee) and the LEFT one is an invisible lens chest; confirm that left/right (from the entrance) is right, and what the invisible one gives.
- [ ] GTG Like-Like room (behind the silver block): is the invisible key chest there before the Like Likes are killed? Is the bomb chest there from the start? (If the key chest only appears on clear, its rule needs logic->CanKillEnemy(RE_LIKE_LIKE).)
- [ ] GTG Like-Like room: of the red-rupee (appears on clear), bomb (always there) and seed (eye switch) chests, which two are the N64 ones? Only matters for naming.
- [ ] GTG Maze Path Third / Maze Right Side (Obj_TBox_A_06): with a bow in the inventory, does the chest give the red rupee or the arrows? Does writing a different Drop__DropActor still get replaced by arrows?
- [ ] Ganon's Castle light trial: does the door from the 6-chest room into the triforce room open only after killing the invisible Skulltula + Keese (no key)?
- [ ] Ganon's Castle spirit trial: does the seed chest in the second room appear when the 2 torch slugs die, and can the crystal switch that opens the next door be hit without bombchus?
- [ ] GTG heavy-block room: the door behind the silver block is opened by an invisible eye switch (Obj_EyeSwitch_GlassTruth_A_02 above it). Can it be shot from the near side, and is there still N64's way to open it from the upper ledge? (affects RR_GERUDO_TRAINING_GROUND_BEHIND_HEAVY_BLOCK -> LIKE_LIKE_ROOM)
