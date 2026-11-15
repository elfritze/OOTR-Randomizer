"""Gossip stone hints, as Ship of Harkinian makes them (3drando/hints.cpp, fill.cpp: CreateStoneHints, CalculateWotH,
CalculateBarren), on the remake's stones.

The remake's stones: Obj_GossipStone_A_01 actors whose Name is their rumor's label in EventFlowMsg/GossipStone.msbt
(GossipStone.bfevfl's EventTalkWithInstanceNameLabel says the message named as the stone): 37 labels, each on one stone
(GOSSIP_LOST_WOOD_02 on the stone the Lost Woods and Kokiri Forest maps both hold), in the child's and the adult's maps.
A hint replaces its stone's rumor in every language (the rumor's own leading tags kept: the stones' grey, their text size);
a junk hint keeps the game's rumor (already in every language). Each stone stands for one of SoH's stones in logic (STONES:
a hint's first copy goes on a stone reachable without the hinted item, as SoH places it).

Hint kinds (SoH's): way of the hero (an area holding an item the game cannot be beaten without), foolish (an area holding
no major item and nothing of the way), item (an item and its area: SoH's song, overworld and dungeon hints, and its named
and random item hints; SoH's per-location sentences are not ported: the area says where), always (SoH's always hints, of
the checks this randomizer shuffles: their own sentence), trial (the six trials' barrier), junk.

The stones say it whatever Link holds (Need nothing), while he wears the Mask of Truth (the game's own rule) or once he has
the Stone of Agony: talk_rule()."""
import collections

from . import items as I
from .formats import evfl_edit, msbt, sarc

GOSSIP_MSBT = "EventFlowMsg/GossipStone.msbt"
GOSSIP_FLOW = "Event/EventFlow/GossipStone.bfevfl.zs"
LOCATION_MSBT = "LocationMsg/Location.msbt"
POUCH_MSBT = "ActorMsg/PouchContent.msbt"
NPC_MSBT = "ActorMsg/Npc.msbt"
ENEMY_MSBT = "ActorMsg/Enemy.msbt"

# (stone label: (the map it stands in, the SoH stone whose logic it takes: same area, the nearest kind of access; the
#  remake has its grotto stones out in the open, so they take an open stone's))
STONES = {
    "GOSSIP_DEATH_MOUNTAIN_CRATER_01": ("DeathMountainCrater", "RC_DMC_GOSSIP_STONE"),
    "GOSSIP_DEATH_MOUNTAIN_CRATER_02": ("DeathMountainCrater", "RC_DMC_UPPER_GROTTO_GOSSIP_STONE"),
    "GOSSIP_DEATH_MOUNTAIN_TRAIL_01": ("KakarikoVillage", "RC_KAK_OPEN_GROTTO_GOSSIP_STONE"),
    "GOSSIP_DEATH_MOUNTAIN_TRAIL_02": ("DeathMountainTrail", "RC_DMT_GOSSIP_STONE"),
    "GOSSIP_HYRULE_CASTLE_03": ("DeathMountainTrail", "RC_DMT_GOSSIP_STONE"),
    "GOSSIP_DESERT_COLOSSUS_01": ("DesertColossus", "RC_COLOSSUS_GOSSIP_STONE"),
    "GOSSIP_DODONGO_CAVERN_01": ("DodongoCavern", "RC_DODONGOS_CAVERN_GOSSIP_STONE"),
    "GOSSIP_GERUDO_VALLEY_01": ("GerudoValley", "RC_GV_GOSSIP_STONE"),
    "GOSSIP_GORON_CITY_01": ("GoronCity", "RC_GC_MEDIGORON_GOSSIP_STONE"),   # (its rumor is of Medigoron)
    "GOSSIP_GORON_CITY_02": ("GoronCity", "RC_GC_MAZE_GOSSIP_STONE"),
    "GOSSIP_GRAVEYARD_01": ("Graveyard", "RC_GRAVEYARD_GOSSIP_STONE"),
    "GOSSIP_HYRULE_CASTLE_01": ("HyruleCastle", "RC_HC_MALON_GOSSIP_STONE"),
    "GOSSIP_HYRULE_CASTLE_02": ("HyruleCastle", "RC_HC_ROCK_WALL_GOSSIP_STONE"),
    "GOSSIP_HYRULE_FIELD_01": ("HyruleCastle", "RC_HC_MALON_GOSSIP_STONE"),
    "GOSSIP_HYRULE_FIELD_02": ("HyruleField", "RC_HF_OPEN_GROTTO_GOSSIP_STONE"),
    "GOSSIP_HYRULE_FIELD_03": ("HyruleField", "RC_HF_OPEN_GROTTO_GOSSIP_STONE"),
    "GOSSIP_HYRULE_FIELD_04": ("HyruleField", "RC_HF_OPEN_GROTTO_GOSSIP_STONE"),
    "GOSSIP_LAKE_HYLIA_01": ("LakeHylia", "RC_LH_LAB_GOSSIP_STONE"),
    "GOSSIP_LAKE_HYLIA_02": ("LakeHylia", "RC_LH_SOUTHWEST_GOSSIP_STONE"),
    "GOSSIP_LAKE_HYLIA_03": ("LakeHylia", "RC_LH_SOUTHEAST_GOSSIP_STONE"),
    "GOSSIP_HYRULE_MARKET_01": ("TimeTemple", "RC_TOT_LEFTMOST_GOSSIP_STONE"),   # (the four before the Temple of Time)
    "GOSSIP_HYRULE_MARKET_02": ("TimeTemple", "RC_TOT_LEFT_CENTER_GOSSIP_STONE"),
    "GOSSIP_HYRULE_MARKET_03": ("TimeTemple", "RC_TOT_RIGHT_CENTER_GOSSIP_STONE"),
    "GOSSIP_HYRULE_MARKET_04": ("TimeTemple", "RC_TOT_RIGHTMOST_GOSSIP_STONE"),
    "GOSSIP_KAKARIKO_VILLAGE_01": ("KakarikoVillage", "RC_KAK_OPEN_GROTTO_GOSSIP_STONE"),
    "GOSSIP_KOKIRI_FOREST_01": ("KokiriForest", "RC_KF_GOSSIP_STONE"),
    "GOSSIP_KOKIRI_FOREST_03": ("KokiriForest", "RC_KF_DEKU_TREE_LEFT_GOSSIP_STONE"),
    "GOSSIP_KOKIRI_FOREST_04": ("KokiriForest", "RC_KF_DEKU_TREE_RIGHT_GOSSIP_STONE"),
    "GOSSIP_KOKIRI_FOREST_02": ("SacredForestMeadow", "RC_SFM_SARIA_GOSSIP_STONE"),
    "GOSSIP_SACRED_FOREST_MEADOW_01": ("SacredForestMeadow", "RC_SFM_MAZE_LOWER_GOSSIP_STONE"),
    "GOSSIP_SACRED_FOREST_MEADOW_02": ("SacredForestMeadow", "RC_SFM_MAZE_UPPER_GOSSIP_STONE"),
    "GOSSIP_SACRED_FOREST_MEADOW_03": ("SacredForestMeadow", "RC_SFM_SARIA_GOSSIP_STONE"),
    "GOSSIP_LOST_WOOD_01": ("ZoraRiver", "RC_ZR_OPEN_GROTTO_GOSSIP_STONE"),
    "GOSSIP_LOST_WOOD_02": ("LostWood", "RC_LW_GOSSIP_STONE"),
    "GOSSIP_ZORA_DOMAIN_01": ("ZoraDomain", "RC_ZD_GOSSIP_STONE"),
    "GOSSIP_ZORA_FOUNTAIN_01": ("ZoraFountain", "RC_ZF_FAIRY_GOSSIP_STONE"),
    "GOSSIP_ZORA_FOUNTAIN_02": ("ZoraFountain", "RC_ZF_JABU_GOSSIP_STONE"),
    "GOSSIP_ZORA_RIVER_01": ("ZoraRiver", "RC_ZR_NEAR_GROTTOS_GOSSIP_STONE"),
    "GOSSIP_ZORA_RIVER_02": ("ZoraRiver", "RC_ZR_NEAR_GROTTOS_GOSSIP_STONE"),
    "GOSSIP_ZORA_RIVER_03": ("ZoraRiver", "RC_ZR_NEAR_DOMAIN_GOSSIP_STONE"),
}

# (a check's hint area: the remake's area (LocationMsg/Location.msbt's label, its name in each language) of its SoH check
#  by the check's name, as SoH's areas go (the Market's stones and the Temple of Time's are the Temple of Time's; Outside
#  Ganon's Castle is Ganondorf's Castle); a remake-only chest's map otherwise. Exact names first, then prefixes)
AREA_OF_RC = {
    "RC_SONG_FROM_IMPA": "HyruleCastle", "RC_SONG_FROM_MALON": "LonLonRanch", "RC_SONG_FROM_SARIA": "SacredForestMeadow",
    "RC_SONG_FROM_ROYAL_FAMILYS_TOMB": "Graveyard", "RC_SONG_FROM_OCARINA_OF_TIME": "HyruleField",
    "RC_SONG_FROM_WINDMILL": "KakarikoVillage", "RC_SHEIK_IN_FOREST": "SacredForestMeadow",
    "RC_SHEIK_IN_CRATER": "DeathMountainCrater", "RC_SHEIK_IN_ICE_CAVERN": "IceCavern",
    "RC_SHEIK_AT_COLOSSUS": "DesertColossus", "RC_SHEIK_IN_KAKARIKO": "KakarikoVillage", "RC_SHEIK_AT_TEMPLE": "TimeTemple",
    "RC_QUEEN_GOHMA": "InsideTheDekuTree", "RC_KING_DODONGO": "DodongoCavern", "RC_BARINADE": "InsideJabuJabuBelly",
    "RC_PHANTOM_GANON": "ForestTemple", "RC_VOLVAGIA": "FireTemple", "RC_MORPHA": "WaterTemple",
    "RC_TWINROVA": "SpiritTemple", "RC_BONGO_BONGO": "ShadowTemple",
    "REMAKE_BOWLING_BOMBCHUS": "Market",   # (the remake's bowling alley prize: in the market, as SoH's bowling prizes)
}
AREA_PREFIXES = (
    ("RC_KF_", "KokiriForest"), ("RC_LW_", "LostWood"), ("RC_DEKU_THEATER_", "LostWood"), ("RC_SFM_", "SacredForestMeadow"),
    ("RC_HF_", "HyruleField"), ("RC_LLR_", "LonLonRanch"), ("RC_MARKET_", "Market"), ("RC_TOT_", "TimeTemple"),
    ("RC_HC_", "HyruleCastle"), ("RC_OGC_", "GanonCastle"), ("RC_KAK_", "KakarikoVillage"), ("RC_GRAVEYARD_", "Graveyard"),
    ("RC_DMT_", "DeathMountainTrail"), ("RC_GC_", "GoronCity"), ("RC_DMC_", "DeathMountainCrater"),
    ("RC_ZR_", "ZoraRiver"), ("RC_ZD_", "ZoraDomain"), ("RC_ZF_", "ZoraFountain"), ("RC_LH_", "LakeHylia"),
    ("RC_GV_", "GerudoValley"), ("RC_GF_", "GerudoFortress"), ("RC_TH_", "GerudoFortress"),
    ("RC_WASTELAND_", "HountedWasteland"), ("RC_COLOSSUS_", "DesertColossus"),
    ("RC_DEKU_TREE_", "InsideTheDekuTree"), ("RC_DODONGOS_CAVERN_", "DodongoCavern"),
    ("RC_JABU_JABUS_BELLY_", "InsideJabuJabuBelly"), ("RC_FOREST_TEMPLE_", "ForestTemple"),
    ("RC_FIRE_TEMPLE_", "FireTemple"), ("RC_WATER_TEMPLE_", "WaterTemple"), ("RC_SPIRIT_TEMPLE_", "SpiritTemple"),
    ("RC_SHADOW_TEMPLE_", "ShadowTemple"), ("RC_BOTTOM_OF_THE_WELL_", "BottomOfTheWell"), ("RC_ICE_CAVERN_", "IceCavern"),
    ("RC_GERUDO_TRAINING_GROUND_", "GerudoTrainingGround"), ("RC_GANONS_CASTLE_", "InsideGanonCastle"),
    ("RC_GANONS_TOWER_", "InsideGanonCastle"),
)
DUNGEON_AREAS = {"InsideTheDekuTree", "DodongoCavern", "InsideJabuJabuBelly", "ForestTemple", "FireTemple", "WaterTemple",
                 "SpiritTemple", "ShadowTemple", "BottomOfTheWell", "IceCavern", "GerudoTrainingGround",
                 "InsideGanonCastle"}
SONG_CHECKS = {rc for rc in AREA_OF_RC if rc.startswith(("RC_SONG_", "RC_SHEIK_"))}


def area_of(loc_id, remake_map=None):
    """a check's hint area (a Location.msbt label), or None (no area: never hinted)"""
    if loc_id in AREA_OF_RC:
        return AREA_OF_RC[loc_id]
    for prefix, area in AREA_PREFIXES:
        if loc_id.startswith(prefix):
            return area
    return remake_map


# (SoH's distributions (3drando/hints.cpp:153-211): per kind (weight, copies); the fixed counts are 0 in all of them.
#  Always and trial hints come first, in alwaysCopies / trialCopies copies; junk last, with its weight)
DISTRIBUTIONS = {
    "useless": {"always": 0, "trial": 0, "junk": 1, "kinds": ()},
    "balanced": {"always": 1, "trial": 1, "junk": 6, "kinds": (
        ("woth", 7, 1), ("foolish", 4, 1), ("song", 2, 1), ("overworld", 4, 1), ("dungeon", 3, 1),
        ("named_item", 10, 1), ("random", 12, 1))},
    "strong": {"always": 2, "trial": 1, "junk": 0, "kinds": (
        ("woth", 12, 2), ("foolish", 12, 1), ("song", 4, 1), ("overworld", 6, 1), ("dungeon", 6, 1),
        ("named_item", 8, 1), ("random", 8, 1))},
    "very_strong": {"always": 2, "trial": 1, "junk": 0, "kinds": (
        ("woth", 15, 2), ("foolish", 15, 1), ("song", 2, 1), ("overworld", 7, 1), ("dungeon", 7, 1),
        ("named_item", 5, 1))},
}
# (SoH's always hints (3drando/hints.cpp:302-317) of the checks this randomizer shuffles; each its own sentence. Their
#  conditions all hold with the fixed settings: 10 Big Poes, fewer than 2 stones and 5 medallions and no tokens asked)
ALWAYS = {
    "RC_MARKET_10_BIG_POES": ("poes", {}),
    "RC_SONG_FROM_OCARINA_OF_TIME": ("oot_song", {}),
    "RC_SHEIK_IN_KAKARIKO": ("sheik", {"place": "KakarikoVillage"}),
    "RC_KAK_30_GOLD_SKULLTULA_REWARD": ("skulltulas", {"n": 30}),
    "RC_KAK_40_GOLD_SKULLTULA_REWARD": ("skulltulas", {"n": 40}),
    "RC_KAK_50_GOLD_SKULLTULA_REWARD": ("skulltulas", {"n": 50}),
    "RC_ZR_FROGS_OCARINA_GAME": ("frogs", {"place": "ZoraRiver"}),
}
TRIAL_AREA = "InsideGanonCastle"


class Hint(dict):
    """{"kind": woth / foolish / item / always / trial / junk, "area": Location label, "location": check id, "item": actor,
    "sentence": always's sentence, "args": its other values}: what placements.json keeps"""


def _is_dungeon_item(actor, loc):
    """a dungeon's item in that dungeon (SoH hints none of these; one placed elsewhere is hinted as any item)"""
    own = I.dungeon_item(actor, loc.map)
    return own is not None and own[1] == loc.map


def make(world, locs, fixed, placed, closed, distribution, rng, info=None, log=None):
    """{stone label: Hint} for every stone. world, locs, fixed, placed, closed: as fill takes them (placed: {location id:
    actor}). SoH's order: always hints, trial hints, then its weighted draw of the kinds until every stone holds one."""
    from .logic.search import item_info
    info = info or item_info()
    d = DISTRIBUTIONS[distribution]
    by_id = {l.id: l for l in locs}
    rg_of = {lid: I.soh_item(a, by_id[lid].map) for lid, a in placed.items()}
    every = {**fixed, **{lid: rg for lid, rg in rg_of.items() if rg != "RG_NONE"}}

    def beatable_without(gone):
        have, _ = world.collect(collections.Counter(), {k: v for k, v in every.items() if k not in gone})
        return world.can_beat(have)

    have_all, spheres = world.collect(collections.Counter(), every)
    if not world.can_beat(have_all):
        raise ValueError("hints: the seed is not beatable")
    progression = {rg for rg, i in info.items() if i.get("progression")}
    major = {rg for rg, i in info.items() if i.get("major")}
    # (hintable: a shuffled check in logic, with an area, not holding its own dungeon's key, map or compass)
    hintable = [l for l in locs if l.id not in closed and not _is_dungeon_item(placed[l.id], l) and
                area_of(l.id, l.map) is not None]
    hintable_ids = {l.id for l in hintable}
    # (the way of the hero: the playthrough pared down (latest sphere first, each shuffled check whose item logic needs
    #  left out while the game stays beatable), then of what is left, each check the game cannot be beaten without)
    order = [lid for sphere in spheres for lid in sorted(sphere, key=str)
             if lid in rg_of and rg_of[lid] in progression]
    gone = set()
    for lid in reversed(order):
        if beatable_without(gone | {lid}):
            gone.add(lid)
    woth = [lid for lid in order if lid not in gone and lid in hintable_ids and not beatable_without({lid})]
    woth_set = set(woth)
    # (foolish: an area none of whose checks, shuffled or as the game has them, holds a major item or one of the way)
    area_items = collections.defaultdict(list)
    for l in locs:
        a = area_of(l.id, l.map)
        if a:
            area_items[a].append((l.id, rg_of[l.id]))
    for rc, rg in fixed.items():
        a = area_of(rc)
        if a and rc in world.location_ids:
            area_items[a].append((rc, rg))
    barren = {a for a, its in area_items.items() if not any(rg in major or lid in woth_set for lid, rg in its)}
    if log:
        log("hints: %d checks on the way of the hero, %d foolish areas" % (len(woth), len(barren)))

    stones = {}
    empty = sorted(STONES)
    hinted = set()
    reach_cache = {}

    def reachable_stones(lid):
        rg = every.get(lid)
        key = lid if rg in progression else None
        if key not in reach_cache:
            have, _ = world.collect(collections.Counter(), {k: v for k, v in every.items() if k != key})
            reach = world.reachable(have)
            reach_cache[key] = {s for s, (_, rc) in STONES.items() if rc in reach}
        return reach_cache[key]

    def place(hint, lid, copies):
        """SoH's CreateHint: the first copy on a stone reachable without the hinted check's item, the others anywhere"""
        if copies == 0 or len(empty) < copies:
            return False
        first = [s for s in empty if s in reachable_stones(lid)] if lid else list(empty)
        if not first:
            return False
        s = rng.choice(first)
        chosen = [s]
        rest = [x for x in empty if x != s]
        chosen += rng.sample(rest, copies - 1)
        for x in chosen:
            stones[x] = Hint(hint)
            empty.remove(x)
        return True

    def item_hint(lid):
        l = by_id[lid]
        return {"kind": "item", "area": area_of(lid, l.map), "location": lid, "item": placed[lid]}

    for rc, (sentence, args) in ALWAYS.items():
        if d["always"] and rc in hintable_ids and rc not in hinted:
            if place({"kind": "always", "location": rc, "item": placed[rc], "sentence": sentence, "args": args,
                      "area": area_of(rc)}, rc, d["always"]):
                hinted.add(rc)
    if d["trial"] and world.ctx.GetOption("RSK_TRIAL_COUNT").Is(6):   # (all six: SoH's one "barrier" hint)
        for _ in range(d["trial"]):
            if empty:
                s = rng.choice(empty)
                stones[s] = Hint({"kind": "trial", "area": TRIAL_AREA})
                empty.remove(s)

    def pool(kind):
        ids = [l.id for l in hintable if l.id not in hinted]
        if kind == "woth":
            return [i for i in ids if i in woth_set]
        if kind == "foolish":
            return [i for i in ids if area_of(i, by_id[i].map) in barren]
        if kind == "song":
            return [i for i in ids if i in SONG_CHECKS]
        if kind == "overworld":
            return [i for i in ids if area_of(i, by_id[i].map) not in DUNGEON_AREAS]
        if kind == "dungeon":
            return [i for i in ids if area_of(i, by_id[i].map) in DUNGEON_AREAS]
        if kind == "named_item":
            return [i for i in ids if rg_of[i] in major]
        return ids

    weights = {k: [w, c] for k, w, c in d["kinds"]}
    junk_weight = d["junk"]
    while empty:
        total = sum(w for w, _ in weights.values()) + junk_weight
        if total == 0:
            break
        roll = rng.randint(1, total)
        kind = "junk"
        for k, (w, _) in weights.items():
            if roll <= w:
                kind = k
                break
            roll -= w
        if kind == "junk":
            s = rng.choice(empty)
            stones[s] = Hint({"kind": "junk"})
            empty.remove(s)
            continue
        w, copies = weights[kind]
        candidates = pool(kind)
        rng.shuffle(candidates)
        done = False
        for lid in candidates:
            if kind == "woth":
                hint = {"kind": "woth", "area": area_of(lid, by_id[lid].map), "location": lid}
            elif kind == "foolish":
                hint = {"kind": "foolish", "area": area_of(lid, by_id[lid].map), "location": lid}
            else:
                hint = item_hint(lid)
            if place(hint, lid, copies):
                done = True
                if kind == "foolish":   # (the whole area is hinted: no other hint names it as foolish or its items)
                    hinted.update(i for i in hintable_ids if area_of(i, by_id[i].map) == hint["area"])
                else:
                    hinted.add(lid)
                break
            if len(empty) < copies:
                break
        if not done:
            weights[kind][0] = 0
    for s in list(empty):
        stones[s] = Hint({"kind": "junk"})
        empty.remove(s)
    return stones


# ---- the hints' words, in each of the game's languages (by a Mals archive's region, else its language) ----

PHRASES = {
    "en": {"woth": "They say that {area} is on the way of the hero.",
           "foolish": "They say that plundering {area} is a foolish choice.",
           "found_at": "They say that {item} can be found at {area}.",
           "hoards": "They say that {area} hoards {item}.",
           "trial": "They say that {area} is protected by a powerful barrier.",
           "poes": "They say that ghost hunters will be rewarded with {item}.",
           "oot_song": "They say that the {oot} teaches {item}.",
           "sheik": "They say that {sheik} teaches {item} in {place}.",
           "skulltulas": "They say that slaying {n} Gold Skulltulas reveals {item}.",
           "frogs": "They say that the final reward from the frogs of {place} is {item}."},
    "fr": {"woth": "On raconte que {area} est sur la voie du héros.",
           "foolish": "On raconte que fouiller {area} serait insensé.",
           "found_at": "On raconte que {item} se trouve du côté de {area}.",
           "hoards": "On raconte que {area} recèle {item}.",
           "trial": "On raconte que {area} est protégé par une puissante barrière.",
           "poes": "On raconte que les chasseurs de fantômes recevront {item}.",
           "oot_song": "On raconte que l'{oot} enseigne {item}.",
           "sheik": "On raconte que {sheik} enseigne {item} du côté de {place}.",
           "skulltulas": "On raconte que vaincre {n} Skulltulas d'or révèle {item}.",
           "frogs": "On raconte que la dernière récompense des grenouilles de {place} est {item}."},
    "USfr": {"skulltulas": "On raconte que vaincre {n} Skulltulas dorées révèle {item}."},
    "es": {"woth": "Dicen que {area} está en el camino del héroe.",
           "foolish": "Dicen que saquear {area} es una insensatez.",
           "found_at": "Dicen que {item} se encuentra por {area}.",
           "hoards": "Dicen que {area} guarda {item}.",
           "trial": "Dicen que {area} está protegido por una poderosa barrera.",
           "poes": "Dicen que los cazadores de fantasmas recibirán {item}.",
           "oot_song": "Dicen que la {oot} enseña {item}.",
           "sheik": "Dicen que {sheik} enseña {item} en {place}.",
           "skulltulas": "Dicen que derrotar a {n} Skulltulas doradas revela {item}.",
           "frogs": "Dicen que el premio final de las ranas de {place} es {item}."},
    "de": {"woth": "Man sagt, {area} liege auf dem Weg des Helden.",
           "foolish": "Man sagt, es sei töricht, {area} zu plündern.",
           "found_at": "Man sagt, {item} sei bei {area} zu finden.",
           "hoards": "Man sagt, {area} berge {item}.",
           "trial": "Man sagt, {area} werde von einer mächtigen Barriere geschützt.",
           "poes": "Man sagt, Geisterjäger würden mit {item} belohnt.",
           "oot_song": "Man sagt, die {oot} lehre {item}.",
           "sheik": "Man sagt, {sheik} lehre {item} bei {place}.",
           "skulltulas": "Man sagt, wer {n} Goldene Skulltulas besiegt, erhalte {item}.",
           "frogs": "Man sagt, die letzte Belohnung der Frösche am {place} sei {item}."},
    "it": {"woth": "Si dice che {area} sia sulla via dell'eroe.",
           "foolish": "Si dice che saccheggiare {area} sia una scelta sciocca.",
           "found_at": "Si dice che {item} si trovi presso {area}.",
           "hoards": "Si dice che {area} custodisca {item}.",
           "trial": "Si dice che {area} sia protetto da una potente barriera.",
           "poes": "Si dice che i cacciatori di spettri saranno ricompensati con {item}.",
           "oot_song": "Si dice che l'{oot} insegni {item}.",
           "sheik": "Si dice che {sheik} insegni {item} presso {place}.",
           "skulltulas": "Si dice che sconfiggere {n} Aracnule d'oro riveli {item}.",
           "frogs": "Si dice che l'ultima ricompensa delle rane di {place} sia {item}."},
    "pt": {"woth": "Dizem que {area} está no caminho do herói.",
           "foolish": "Dizem que saquear {area} é uma escolha tola.",
           "found_at": "Dizem que {item} pode ser encontrado em {area}.",
           "hoards": "Dizem que {area} guarda {item}.",
           "trial": "Dizem que {area} está protegido por uma barreira poderosa.",
           "poes": "Dizem que caçadores de fantasmas serão recompensados com {item}.",
           "oot_song": "Dizem que a {oot} ensina {item}.",
           "sheik": "Dizem que {sheik} ensina {item} em {place}.",
           "skulltulas": "Dizem que derrotar {n} Cranítulas de ouro revela {item}.",
           "frogs": "Dizem que a recompensa final das rãs de {place} é {item}."},
    "nl": {"woth": "Men zegt dat {area} op het pad van de held ligt.",
           "foolish": "Men zegt dat het dwaas is om {area} te plunderen.",
           "found_at": "Men zegt dat {item} te vinden is in {area}.",
           "hoards": "Men zegt dat {area} {item} verbergt.",
           "trial": "Men zegt dat {area} door een machtige barrière wordt beschermd.",
           "poes": "Men zegt dat spokenjagers beloond worden met {item}.",
           "oot_song": "Men zegt dat de {oot} {item} leert.",
           "sheik": "Men zegt dat {sheik} {item} leert in {place}.",
           "skulltulas": "Men zegt dat wie {n} Gouden Skulltula's verslaat, {item} krijgt.",
           "frogs": "Men zegt dat de laatste beloning van de kikkers van {place} {item} is."},
    # (Polish and Russian: names stay in the nominative after a colon, as the game gives them)
    "pl": {"woth": "Mówią, że to miejsce leży na drodze bohatera: {area}.",
           "foolish": "Mówią, że to miejsce nie jest warte zachodu: {area}.",
           "found_at": "Mówią, że ten przedmiot: {item}, można znaleźć tutaj: {area}.",
           "hoards": "Mówią, że ten przedmiot: {item}, można znaleźć tutaj: {area}.",
           "trial": "Mówią, że potężna bariera chroni to miejsce: {area}.",
           "poes": "Mówią, że łowcy duchów otrzymają nagrodę: {item}.",
           "oot_song": "Mówią, że {oot} uczy pieśni: {item}.",
           "sheik": "Mówią, że {sheik} uczy tutaj ({place}) pieśni: {item}.",
           "skulltulas": "Mówią, że pokonanie {n} złotych czaszników daje nagrodę: {item}.",
           "frogs": "Mówią, że ostatnia nagroda żab z tego miejsca ({place}) to: {item}."},
    "ru": {"woth": "Говорят, что это место на пути героя: {area}.",
           "foolish": "Говорят, что грабить это место — глупая затея: {area}.",
           "found_at": "Говорят, что предмет «{item}» можно найти здесь: {area}.",
           "hoards": "Говорят, что предмет «{item}» можно найти здесь: {area}.",
           "trial": "Говорят, что это место защищено могучим барьером: {area}.",
           "poes": "Говорят, что охотников на призраков ждёт награда: {item}.",
           "oot_song": "Говорят, что {oot} учит мелодии: {item}.",
           "sheik": "Говорят, что {sheik} учит здесь ({place}) мелодии: {item}.",
           "skulltulas": "Говорят, что за {n} золотых черепауков дают награду: {item}.",
           "frogs": "Говорят, что последняя награда лягушек ({place}) — это {item}."},
    "ja": {"woth": "うわさでは、{area}は 勇者の道に あるらしい。",
           "foolish": "うわさでは、{area}を 探すのは 愚かな選択らしい。",
           "found_at": "うわさでは、{item}は {area}で 見つかるらしい。",
           "hoards": "うわさでは、{item}は {area}で 見つかるらしい。",
           "trial": "うわさでは、{area}は 強力な結界に 守られているらしい。",
           "poes": "うわさでは、幽霊ハンターには {item}が 与えられるらしい。",
           "oot_song": "うわさでは、{oot}は {item}を 教えてくれるらしい。",
           "sheik": "うわさでは、{sheik}が {place}で {item}を 教えてくれるらしい。",
           "skulltulas": "うわさでは、{gs}を {n}匹 倒すと {item}が もらえるらしい。",
           "frogs": "うわさでは、{place}の カエルたちの 最後のごほうびは {item}らしい。"},
    "ko": {"woth": "소문에 의하면 {area}은(는) 용사의 길에 있다고 한다.",
           "foolish": "소문에 의하면 {area}을(를) 뒤지는 건 어리석은 선택이라고 한다.",
           "found_at": "소문에 의하면 {item}은(는) {area}에서 찾을 수 있다고 한다.",
           "hoards": "소문에 의하면 {item}은(는) {area}에서 찾을 수 있다고 한다.",
           "trial": "소문에 의하면 {area}은(는) 강력한 결계로 지켜지고 있다고 한다.",
           "poes": "소문에 의하면 유령 사냥꾼은 {item}을(를) 받는다고 한다.",
           "oot_song": "소문에 의하면 {oot}이(가) {item}을(를) 가르쳐 준다고 한다.",
           "sheik": "소문에 의하면 {sheik}이(가) {place}에서 {item}을(를) 가르쳐 준다고 한다.",
           "skulltulas": "소문에 의하면 {gs}을(를) {n}마리 쓰러뜨리면 {item}을(를) 받는다고 한다.",
           "frogs": "소문에 의하면 {place} 개구리들의 마지막 보상은 {item}(이)라고 한다."},
    "CNzh": {"woth": "据说{area}位于勇者之路上。",
             "foolish": "据说搜刮{area}是愚蠢的选择。",
             "found_at": "据说在{area}可以找到{item}。",
             "hoards": "据说在{area}可以找到{item}。",
             "trial": "据说{area}被强大的结界保护着。",
             "poes": "据说幽灵猎人会得到{item}作为奖励。",
             "oot_song": "据说{oot}能教会{item}。",
             "sheik": "据说{sheik}会在{place}传授{item}。",
             "skulltulas": "据说打倒{n}只{gs}能得到{item}。",
             "frogs": "据说{place}青蛙们的最后奖励是{item}。"},
    "TWzh": {"woth": "據說{area}位於勇者之路上。",
             "foolish": "據說搜刮{area}是愚蠢的選擇。",
             "found_at": "據說在{area}可以找到{item}。",
             "hoards": "據說在{area}可以找到{item}。",
             "trial": "據說{area}被強大的結界保護著。",
             "poes": "據說幽靈獵人會得到{item}作為獎勵。",
             "oot_song": "據說{oot}能教會{item}。",
             "sheik": "據說{sheik}會在{place}傳授{item}。",
             "skulltulas": "據說打倒{n}隻{gs}能得到{item}。",
             "frogs": "據說{place}青蛙們的最後獎勵是{item}。"},
}
# (line width in characters, as the game's own rumors run: by language; Chinese and Japanese break anywhere)
WIDTH = {"ru": 50, "ja": 24, "ko": 30, "CNzh": 18, "TWzh": 18}
NO_SPACES = {"ja", "CNzh", "TWzh"}
LINES_PER_PAGE = 2
PAGE = b"\x0e\x00\x00\x04\x00\x00\x00"   # (a new page of the box, as the game's long rumors have)
# (names the sentences take from the game: (placeholder, message file, label))
GAME_NAMES = (("oot", POUCH_MSBT, "Item_Ocarina_Time_Name"), ("sheik", NPC_MSBT, "Npc_Hylia_Sheik_Adult_Name"),
              ("gs", ENEMY_MSBT, "Enemy_Skulltula_Gold_Name"))


def language(archive):
    """("USen.Product.110.sarc.zs") -> (region key, language key)"""
    region = archive.split(".")[0]
    return region, region if region in ("CNzh", "TWzh") else region[2:]


def phrase(archive, key):
    region, lang = language(archive)
    return PHRASES.get(region, {}).get(key) or PHRASES[lang][key]


def item_name_label(actor, labels):
    """the PouchContent label naming an item actor (its own, else its pouch form's: Item_Range_Bow -> Weapon_Range_Bow)"""
    base = actor.split("_", 1)[1] if actor.split("_", 1)[0] in ("Item", "Obj", "TBox", "Tbox") else actor
    for c in (actor, "Item_" + base, "Obj_" + base, "Weapon_" + base, "Armor_Adult_" + base, "Armor_Child_" + base,
              "Armor_" + base, "Armor_Adult_" + base.replace("Armor_", "", 1)):
        if c + "_Name" in labels:
            return c + "_Name"
    return None


class Names:
    """the names a language's hints need, from its Mals archive (an empty one: the English archive's)"""
    def __init__(self, files, english=None):
        self.files, self.english = files, english
        self._cache = {}

    def _msbt(self, rel):
        if rel not in self._cache:
            self._cache[rel] = msbt.read(self.files[rel])
        return self._cache[rel]

    def text(self, rel, label):
        t = self._msbt(rel).text(label) if label else None
        if (not t or not t.strip()) and self.english is not None:
            return self.english.text(rel, label)
        return t

    def area(self, key):
        return self.text(LOCATION_MSBT, key)

    def item(self, actor):
        return self.text(POUCH_MSBT, item_name_label(actor, self._msbt(POUCH_MSBT).labels))


def segments(template, values, red):
    """the sentence as [(text, red?)]: each {name} its value, red when in `red`"""
    out, rest = [], template
    while "{" in rest:
        before, _, after = rest.partition("{")
        name, _, rest = after.partition("}")
        out.append((before, False))
        out.append((str(values[name]), name in red))
    out.append((rest, False))
    return [(t, r) for t, r in out if t]


NO_LINE_START = set("。、，．！？）」』…・ー：；")   # (Chinese and Japanese: never the first character of a line)


def layout(segs, width, no_spaces):
    """[[(text, red?)] per line]: words wrapped at width. A word is what spaces part, its pieces of either colour kept
    together (a name and the full stop after it); in Chinese and Japanese each character, punctuation kept with the one
    before it"""
    words, word = [], []
    for text, red in segs:
        if no_spaces:
            for ch in text:
                if ch in NO_LINE_START and words:
                    words[-1].append((ch, red))
                else:
                    words.append([(ch, red)])
        else:
            for i, part in enumerate(text.split(" ")):
                if i:   # (a space ends the word)
                    if word:
                        words.append(word)
                    word = []
                if part:
                    word.append((part, red))
    if word:
        words.append(word)
    lines, line, n = [], [], 0
    for w in words:
        size = sum(len(t) for t, _ in w)
        gap = 0 if no_spaces or not line else 1
        if line and n + gap + size > width:
            while no_spaces and line and line[-1][0] == " ":   # (no space at a line's end, nor at its start)
                line.pop()
            lines.append(line)
            line, n, gap = [], 0, 0
        if no_spaces and not line and w[0][0] == " ":
            continue
        if gap:
            line.append((" ", line[-1][1] and w[0][1]))   # (the space red only between two red pieces)
        line += w
        n += gap + size
    if line:
        lines.append(line)
    return lines


def korean_particles(segs):
    """Korean: each "은(는)", "을(를)", "이(가)", "(이)라고" after a name, the form its last syllable takes (a closing
    consonant: the first)"""
    pairs = (("은(는)", "은", "는"), ("을(를)", "을", "를"), ("이(가)", "이", "가"), ("(이)라고", "이라고", "라고"))
    out = list(segs)
    for i in range(1, len(out)):
        text, red = out[i]
        prev = out[i - 1][0]
        for both, closed, open_ in pairs:
            if text.startswith(both) and prev:
                ch = ord(prev[-1])
                if 0xAC00 <= ch <= 0xD7A3:
                    form = closed if (ch - 0xAC00) % 28 else open_
                    out[i] = (form + text[len(both):], red)
                break
    return out


def render(hint, archive, names, vanilla):
    """a hint's message bytes for one language: the rumor's own leading tags (vanilla: its message), then the sentence,
    areas and items in red, wrapped and paged; None for junk (the rumor stays)"""
    kind = hint["kind"]
    if kind == "junk":
        return None
    region, lang = language(archive)
    values = {}
    if kind == "woth" or kind == "foolish" or kind == "trial":
        key = kind
        values["area"] = names.area(hint["area"])
    elif kind == "item":
        key = "hoards" if hint["area"] in DUNGEON_AREAS else "found_at"
        values.update(area=names.area(hint["area"]), item=names.item(hint["item"]))
    elif kind == "always":
        key = hint["sentence"]
        values["item"] = names.item(hint["item"])
        for k, v in (hint.get("args") or {}).items():
            values[k] = names.area(v) if k == "place" else v
        for k, rel, label in GAME_NAMES:
            values[k] = names.text(rel, label)
    else:
        raise ValueError("hint kind %r" % kind)
    if any(v is None or v == "" for v in values.values()):
        raise ValueError("%s: a name is missing for %r" % (archive, hint))
    lead, color = msbt.leading_tags(vanilla)
    segs = segments(phrase(archive, key), values, {"area", "item", "place"})
    if lang == "ko":
        segs = korean_particles(segs)
    lines = layout(segs, WIDTH.get(region, WIDTH.get(lang, 60)), lang in NO_SPACES)
    out = bytearray(lead)
    red_on = False
    for i, line in enumerate(lines):
        if i:
            out += PAGE if i % LINES_PER_PAGE == 0 else b"\n"
        for tok, red in line:
            if red != red_on:
                out += msbt.COLOR_TAG + (msbt.RED if red else color).to_bytes(2, "little")
                red_on = red
            out += tok.encode("utf-8")
    if red_on:
        out += msbt.COLOR_TAG + color.to_bytes(2, "little")
    return bytes(out)


def english(hint, english_names, vanilla=b""):
    """a hint's English text, tags left out (the spoiler's)"""
    raw = render(hint, "USen.Product.110.sarc.zs", english_names, vanilla)
    if raw is None:
        return "(the game's rumor)"
    return msbt.Msbt(b"", {"x": 0}, [raw + b"\0"], 1, {}).text("x").replace("\n", " ")


ENGLISH = "USen.Product.110.sarc.zs"


def with_hints(archive, files, english_names, stones):
    """an archive's files ({name: bytes}) with the stones' rumors replaced by their hints"""
    files = dict(files)
    names = Names(files, english_names)
    m = msbt.read(files[GOSSIP_MSBT])
    for label, hint in sorted(stones.items()):
        vanilla = m.get(label)
        if vanilla is None:
            raise ValueError("%s: no rumor %s" % (archive, label))
        raw = render(hint, archive, names, vanilla[:-1])
        if raw is not None:
            m.set(label, raw)
    files[GOSSIP_MSBT] = m.write()
    return files


def message_files(romfs, mod, stones):
    """{Mals archive rel: its files with the stones' rumors replaced by their hints} (built on the mod's archives)"""
    from .patches import MALS, mals_archives
    english_names = Names(sarc.read(mod.read("%s/%s" % (MALS, ENGLISH))))
    return {"%s/%s" % (MALS, f): with_hints(f, sarc.read(mod.read("%s/%s" % (MALS, f))), english_names, stones)
            for f in mals_archives(romfs)}


# ---- what a stone asks of Link before it tells its rumor (GossipStone.bfevfl, entry Talk) ----
# The game's: Event112 (PouchSystemActor EventQueryIsExistInPouch Armor_Child_Mask_Truth: had, case 0) -> Event25 (worn) ->
# Event6 (/InitTalk_GossipStone) -> Event90 (HaveTalked_MaskTruth_GossipStone: the mask's first time, case 1, says
# Talk_03 "Now there's a mask I haven't seen..." and Talk_10) -> Event89 (Talk_12 "Allow me to let you in on a little
# secret...") -> Event18 (the rumor) -> ...; without the mask, Navi's lines (Event39). Need nothing: Talk starts at Event6
# and Event6 goes to Event89 (no word of the mask). Stone of Agony: Talk starts at a new switch, the stone had? -> Event6
# (then Event89), else Navi's lines (Event39) as without the mask. Mask of Truth: the game's.
TALK_HAD_MASK, TALK_INIT, TALK_SECRET, TALK_NAVI = "Event112", "Event6", "Event89", "Event39"
AGONY = "Item_AgonyStone"
AGONY_EVENT = "RandoHasAgonyStone"


def talk_rule(data, rule):
    """GossipStone.bfevfl with the stones talking as the setting says (None: the game's own rule, no change)"""
    if rule in ("none", "mask_of_truth"):
        return None
    edit = evfl_edit.FlowEdit(data)
    flow = edit.flow
    first = flow["events"][flow["entries"]["Talk"]]
    init = edit.event(TALK_INIT)
    if first["name"] != TALK_HAD_MASK or (first.get("params") or {}).get("Actor") != "Armor_Child_Mask_Truth" or \
            init["type"] != "subflow" or init.get("entry") != "InitTalk_GossipStone" or \
            edit.event(TALK_SECRET)["params"].get("MessageId") != "EventFlowMsg/GossipStone:Talk_12":
        raise ValueError("%s: the stones' talk is not the one known" % GOSSIP_FLOW)
    edit.set_next(TALK_INIT, TALK_SECRET)
    if rule == "need_nothing":
        edit.set_entry("Talk", TALK_INIT)
    elif rule == "stone_of_agony":
        edit.add_event({"name": AGONY_EVENT, "type": "switch", "actor": "PouchSystemActor",
                        "query": "EventQueryIsExistInPouch", "params": {"Actor": AGONY, "Num": 1},
                        "cases": {0: TALK_INIT, 1: TALK_NAVI}})
        edit.set_entry("Talk", AGONY_EVENT)
    else:
        raise ValueError("gossip stone rule %r" % rule)
    return edit.apply()


def write(romfs, mod, stones, rule):
    """the hints into the mod: the message archives, and the stones' talk"""
    for rel, files in message_files(romfs, mod, stones).items():
        from .patches import MALS_DATA_ALIGNMENT
        mod.write(rel, sarc.write(files, data_alignment=MALS_DATA_ALIGNMENT))
    data = talk_rule(mod.read(GOSSIP_FLOW), rule)
    if data is not None:
        mod.write(GOSSIP_FLOW, data)
