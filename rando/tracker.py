"""The tracker's model: every check of the installed seed with where it is in the world, what Link holds (read from the
game's save), and which checks logic reaches with it.

    index = load_index(romfs)                  # (cached: positions of the maps' actors, map bounds, map outlines)
    model = Model(game_folder)                 # (the installed seed: rando.generate's Setup + placements.json)
    have = model.inventory(savefile.read(p))   # (Counter of SoH items, as logic counts them)
    states = model.states(have, marks)         # ({check id: "done" | "available" | "blocked"})

Nothing here writes in the game folder: the save is read, the marks and the cache live in %APPDATA%/HookshotRando."""
import collections
import json
import os
import random

from . import chests, generate, items as I, savefile
from .formats import byml, zs

APPDATA = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "HookshotRando")
INDEX_VERSION = 3

# (the areas as the tracker lists them: map folder: name; in the order of a playthrough's first steps)
AREAS = collections.OrderedDict((
    ("KokiriForest", "Kokiri Forest"), ("LostWood", "Lost Woods"), ("SacredForestMeadow", "Sacred Forest Meadow"),
    ("HyruleField", "Hyrule Field"), ("LonLonRanch", "Lon Lon Ranch"), ("LakeHylia", "Lake Hylia"),
    ("Market", "Market & Temple of Time"), ("HyruleCastle", "Hyrule Castle"),
    ("KakarikoVillage", "Kakariko Village"), ("Graveyard", "Graveyard"), ("DeathMountainTrail", "Death Mountain Trail"),
    ("DeathMountainCrater", "Death Mountain Crater"), ("GoronCity", "Goron City"), ("ZoraRiver", "Zora's River"),
    ("ZoraDomain", "Zora's Domain"), ("ZoraFountain", "Zora's Fountain"), ("GerudoValley", "Gerudo Valley"),
    ("GerudoFortress", "Gerudo's Fortress"), ("HountedWasteland", "Haunted Wasteland"),
    ("DesertColossus", "Desert Colossus"), ("GanonCastle", "Outside Ganon's Castle"),
    ("InsideTheDekuTree", "Deku Tree"), ("DodongoCavern", "Dodongo's Cavern"), ("InsideJabuJabuBelly", "Jabu-Jabu's Belly"),
    ("ForestTemple", "Forest Temple"), ("FireTemple", "Fire Temple"), ("WaterTemple", "Water Temple"),
    ("ShadowTemple", "Shadow Temple"), ("SpiritTemple", "Spirit Temple"), ("BottomOfTheWell", "Bottom of the Well"),
    ("IceCavern", "Ice Cavern"), ("GerudoTrainingGround", "Gerudo Training Ground"),
    ("InsideGanonCastle", "Ganon's Castle"),
))
DUNGEON_FOLDERS = set(I.DUNGEONS)
# (the remake keeps Lake Hylia and Lon Lon Ranch in Hyrule Field's map files, in its coordinates; the pause menu draws them
# on their own maps: the tracker lists them apart, by the check's area name)
AREA_OF_SOH = {"Lake Hylia": "LakeHylia", "Lon Lon Ranch": "LonLonRanch", "Temple of Time": "Market"}

# (where a gift is given, on its area's map: (area, x, z) from the giver's placed actor or the area's map icon in
# Banc/BancBasedResource/MapParam (Facility, EntranceAnchor); gifts given inside a building sit at its door's icon. Gifts not
# here (the Temple of Time, the royal tomb, the Ice Cavern) are listed beside the map)
GIFT_ANCHORS = {
    "RC_LW_SKULL_KID": ("LostWood", -34.0, -3.7),                       # Npc_SkullKid_Child (stump)
    "RC_LW_OCARINA_MEMORY_GAME": ("LostWood", 48.4, 15.9),              # OcarinaPoint_SkullKidSession
    "RC_LW_TARGET_IN_WOODS": ("LostWood", 41.1, -4.9),                  # NPC_Scrub_Deku_TargetPractice
    "RC_LW_DEKU_SCRUB_NEAR_BRIDGE": ("LostWood", 19.2, -51.2),          # Enemy_Scrub_Business (child)
    "RC_LW_DEKU_SCRUB_GROTTO_FRONT": ("LostWood", 7.3, -85.6),          # Enemy_Scrub_Business (grotto)
    "RC_DEKU_THEATER_SKULL_MASK": ("LostWood", 3.8, -47.5),             # Facility: the Deku Theater
    "RC_DEKU_THEATER_MASK_OF_TRUTH": ("LostWood", 3.8, -47.5),
    "RC_HF_DEKU_SCRUB_GROTTO": ("HyruleField", 25.1, 22.1),             # Enemy_Scrub_Business (grotto)
    "RC_SONG_FROM_OCARINA_OF_TIME": ("HyruleField", 15.5, 43.1),        # Obj_Ocarina_Time_A_01 (the moat)
    "RC_LLR_TALONS_CHICKENS": ("LonLonRanch", -53.6, 197.8),            # Facility: the cucco game
    "RC_SONG_FROM_MALON": ("LonLonRanch", -91.9, 245.4),                # Npc_Hylia_Malon_Child
    "RC_LH_CHILD_FISHING": ("LakeHylia", -97.9, 492.3),                 # Facility: the fishing pond
    "RC_LH_ADULT_FISHING": ("LakeHylia", -97.9, 492.3),
    "RC_LH_LAB_DIVE": ("LakeHylia", -174.6, 422.1),                     # Npc_Hylia_045 (the lab)
    "RC_MARKET_BOMBCHU_BOWLING_FIRST_PRIZE": ("Market", -25.0, 7.6),    # Facility: Bombchu Bowling
    "RC_MARKET_BOMBCHU_BOWLING_SECOND_PRIZE": ("Market", -25.0, 7.6),
    "REMAKE_BOWLING_BOMBCHUS": ("Market", -25.0, 7.6),
    "RC_MARKET_LOST_DOG": ("Market", 8.8, 0.7),                         # Animal_Dog_Richard_01
    "RC_MARKET_SHOOTING_GALLERY_REWARD": ("Market", -13.0, -18.9),      # Facility: the shooting gallery
    "RC_MARKET_10_BIG_POES": ("Market", 12.5, 57.0),                    # Facility: the Poe collector
    "RC_SONG_FROM_IMPA": ("HyruleCastle", 5.1, -233.4),                 # Npc_Hylia_Impa_Child (the garden)
    "RC_KAK_10_GOLD_SKULLTULA_REWARD": ("KakarikoVillage", -25.4, 75.6),  # Facility: House of Skulltula
    "RC_KAK_20_GOLD_SKULLTULA_REWARD": ("KakarikoVillage", -25.4, 75.6),
    "RC_KAK_30_GOLD_SKULLTULA_REWARD": ("KakarikoVillage", -25.4, 75.6),
    "RC_KAK_40_GOLD_SKULLTULA_REWARD": ("KakarikoVillage", -25.4, 75.6),
    "RC_KAK_50_GOLD_SKULLTULA_REWARD": ("KakarikoVillage", -25.4, 75.6),
    "RC_KAK_MAN_ON_ROOF": ("KakarikoVillage", -36.1, 30.2),             # Npc_Hylia_001_Child
    "RC_KAK_SHOOTING_GALLERY_REWARD": ("KakarikoVillage", -63.4, 62.8),  # Facility: the shooting gallery
    "RC_KAK_ANJU_AS_CHILD": ("KakarikoVillage", -10.3, 28.8),           # Animal_Cucco_CatchCucco
    "RC_SONG_FROM_WINDMILL": ("KakarikoVillage", 1.5, 43.9),            # OcarinaPoint_Kakariko_WindmillHouse
    "RC_SHEIK_IN_KAKARIKO": ("KakarikoVillage", -29.0, 44.2),           # by the well
    "RC_GRAVEYARD_DAMPE_GRAVEDIGGING_TOUR": ("Graveyard", -4.6, -1.8),  # Facility: the digging tour
    "RC_GC_ROLLING_GORON_AS_CHILD": ("GoronCity", -10.3, -16.5),        # Npc_Goron_006_Child
    "RC_DMC_DEKU_SCRUB": ("DeathMountainCrater", -23.0, 33.0),          # Enemy_Scrub_Business
    "RC_SHEIK_IN_CRATER": ("DeathMountainCrater", 18.6, 64.4),          # the way in from the trail
    "RC_ZR_FROGS_IN_THE_RAIN": ("ZoraRiver", 9.2, -54.8),               # OcarinaPoint_MiniGame_FrogTenors
    "RC_ZR_FROGS_OCARINA_GAME": ("ZoraRiver", 9.2, -54.8),
    "RC_ZD_DIVING_MINIGAME": ("ZoraDomain", 24.8, -6.8),                # Facility: the diving game
    "RC_ZD_KING_ZORA_THAWED": ("ZoraDomain", 66.1, 12.5),               # Npc_Zora_KingZora_adult
    "RC_SONG_FROM_SARIA": ("SacredForestMeadow", -2.2, -101.1),         # Npc_Kokiri_Saria_Child_SacredForestMeadow
    "RC_SHEIK_IN_FOREST": ("SacredForestMeadow", -6.9, -112.0),         # before the Forest Temple
    "RC_GF_HBA_1000_POINTS": ("GerudoFortress", 73.1, 41.2),            # Facility: horseback archery
    "RC_GF_HBA_1500_POINTS": ("GerudoFortress", 73.1, 41.2),
    "RC_SHEIK_AT_COLOSSUS": ("DesertColossus", -160.9, 10.3),           # before the Spirit Temple
}

# (the save's flag a gift sets once given: from each gift's notes in data/gifts.json, checked against a save; the song
# cutscenes' HavePlayedEvent.Dm_MelodyGet_* are added from the gifts' flows. Gifts without a sure one-time flag are left to
# the player's marks: the lab dive (HasDived is any dive), King Zora (CanGet... is before), the bowling and Poe prizes)
DONE_FLAGS = {
    "RC_LW_SKULL_KID": "Npc_SkullKid_Child_IsGetHeartPiece",
    "RC_LW_OCARINA_MEMORY_GAME": "Minigame_SkullKidSession_IsGetHeartPiece",
    "RC_LW_TARGET_IN_WOODS": "LostWood_HitTargetOfDekuScrub_FirstClear",
    "RC_LW_DEKU_SCRUB_NEAR_BRIDGE": "LostWood_Enemy_Scrub_Business_DekuStickPouch_01",
    "RC_LW_DEKU_SCRUB_GROTTO_FRONT": "Lostwood_Enemy_Scrub_Business_DekuNutsPouch_01",
    "RC_DEKU_THEATER_SKULL_MASK": "LostWood_ScrubForestStage_SkullMaskEventLaunched",
    "RC_DEKU_THEATER_MASK_OF_TRUTH": "LostWood_ScrubForestStage_TrueMaskEventLaunched",
    "RC_HF_DEKU_SCRUB_GROTTO": "HyruleField_Enemy_Scrub_Business_HeartPiece_01",
    "REMAKE_BOWLING_BOMBCHUS": "MiniGame_BombchuBowling_ClearFirstTime",
    "RC_MARKET_LOST_DOG": "SubEvent_FindRichard_GetHeartPiece",
    "RC_MARKET_SHOOTING_GALLERY_REWARD": "MiniGame_HitTarget_HrlCity_Get_BulletBag",
    "RC_LLR_TALONS_CHICKENS": "IsClear_Minigame_FindOutCucco",
    "RC_KAK_10_GOLD_SKULLTULA_REWARD": "KakarikoVillage_GatheringTokenGold_GetReward10",
    "RC_KAK_20_GOLD_SKULLTULA_REWARD": "KakarikoVillage_GatheringTokenGold_GetReward20",
    "RC_KAK_30_GOLD_SKULLTULA_REWARD": "KakarikoVillage_GatheringTokenGold_GetReward30",
    "RC_KAK_40_GOLD_SKULLTULA_REWARD": "KakarikoVillage_GatheringTokenGold_GetReward40",
    "RC_KAK_50_GOLD_SKULLTULA_REWARD": "KakarikoVillage_GatheringTokenGold_GetReward50",
    "RC_KAK_MAN_ON_ROOF": "Npc_Hylia_001_IsGetHeartPiece",
    "RC_KAK_SHOOTING_GALLERY_REWARD": "MiniGame_HitTarget_Kakariko_Get_Quiver",
    "RC_KAK_ANJU_AS_CHILD": "MiniGame_CatchCucco_IsCompleted",
    "RC_GRAVEYARD_DAMPE_GRAVEDIGGING_TOUR": "GraveYard_DiggingHoleTour_Drop_HeartPiece",
    "RC_GC_ROLLING_GORON_AS_CHILD": "GoronCity_GetBombBag_fromGoron006",
    "RC_DMC_DEKU_SCRUB": "DeathMountain_Enemy_Scrub_Business_HeartPiece_01",
    "RC_LH_CHILD_FISHING": "MiniGame_Fishing_GetHeartPiece",
    "RC_LH_ADULT_FISHING": "MiniGame_Fishing_GetGoldScale",
    "RC_GF_HBA_1000_POINTS": "MiniGame_HorsebackArchery_GotaHeart",
    "RC_GF_HBA_1500_POINTS": "MiniGame_HorseBackArchery_Get_Quiver",
    "RC_ZR_FROGS_IN_THE_RAIN": "MiniGame_FrogTenors_StormSong",
    "RC_ZR_FROGS_OCARINA_GAME": "MiniGame_FrogTenors_InsectRepellent",
    # (the checks of the newer settings: the scene's own played flag (saved for every scene), a fairy's once-flag)
    "RC_GC_DARUNIAS_JOY": "HavePlayedEvent.Dm_Goron_0030",   # (set by his scene and by the randomizer's two ways)
    "RC_QUEEN_GOHMA": "HavePlayedEvent.Dm_Kokiri_0130",
    "RC_KING_DODONGO": "HavePlayedEvent.Dm_DeathMtTrail_0025",
    "RC_BARINADE": "HavePlayedEvent.Dm_InsideJabu_Jabu_0030",
    "RC_PHANTOM_GANON": "HavePlayedEvent.Dm_Awake_Forest_Get",
    "RC_VOLVAGIA": "HavePlayedEvent.Dm_Awake_Fire_Get",
    "RC_MORPHA": "HavePlayedEvent.Dm_Awake_Water_Get",
    "RC_TWINROVA": "HavePlayedEvent.Dm_Awake_Spirit_Get",
    "RC_BONGO_BONGO": "HavePlayedEvent.Dm_Awake_Shadow_Get",
    "RC_GIFT_FROM_RAURU": "HavePlayedEvent.Dm_SageRoom_0005",
    "RC_HC_ZELDAS_LETTER": "HavePlayedEvent.Dm_HrlCastle_0050",
    "RC_TOT_LIGHT_ARROWS_CUTSCENE": "HavePlayedEvent.Dm_TimeTemple_0130",
    "RC_LW_GIFT_FROM_SARIA": "HavePlayedEvent.Dm_Kokiri_0155",
    "RC_HC_GREAT_FAIRY_REWARD": "RandoGreatFairy_Din", "RC_ZF_GREAT_FAIRY_REWARD": "RandoGreatFairy_Farore",
    "RC_COLOSSUS_GREAT_FAIRY_REWARD": "RandoGreatFairy_Nayru", "RC_DMT_GREAT_FAIRY_REWARD": "RandoGreatFairy_Power",
    "RC_DMC_GREAT_FAIRY_REWARD": "RandoGreatFairy_Wisdom", "RC_OGC_GREAT_FAIRY_REWARD": "RandoGreatFairy_Courage",
}
SONG_FLOW = "Dm_MelodyGet_"
# (items a check can hold that the game also gives elsewhere, or starts with: holding one says nothing about a check)
NOT_UNIQUE_PREFIXES = ("TBox_", "Tbox_", "Obj_Heart", "Item_Dungeon_", "Item_Bottle", "Item_ScrubBusinessSeed",
                       "Obj_Armor_", "Item_SmallKey_", "Item_BossKey_", "Item_Map_", "Item_Compass_")
NOT_UNIQUE_WORDS = ("Bundle", "Rupee")

# (equipment the save names by its equipped form: IsGet.<name> -> the pool's actor)
SAVE_ALIASES = {
    "Weapon_Sword_Kokiri": "Item_Sword_Kokiri", "Weapon_Range_SlingShot": "Item_Range_SlingShot",
    "Weapon_Range_Bow": "Item_Range_Bow", "Weapon_Shield_Deku": "TBox_Shield_Deku",
    "Weapon_Shield_Hylian": "TBox_Shield_Hylian", "Weapon_Shield_Mirror": "Item_Shield_Mirror",
    "Armor_Adult_HoverBoot": "Item_HoverBoot", "Armor_Adult_HeavyBoot": "Item_HeavyBoot",
    "Armor_GlassTruth": "Item_GlassTruth", "Armor_Child_GlassTruth": "Item_GlassTruth",
    "Armor_Adult_GlassTruth": "Item_GlassTruth", "Armor_Adult_Zora": "Obj_Armor_Zora",
}
# (items logic needs that no chest gives in this randomizer: the save's name -> SoH item)
SAVE_EXTRA = {
    "Item_Ocarina_Fairy": "RG_PROGRESSIVE_OCARINA", "Item_Ocarina_Time": "RG_PROGRESSIVE_OCARINA",
    "Item_ZeldaLetter": "RG_ZELDAS_LETTER", "Item_Bottle_Letter": "RG_RUTOS_LETTER",
    "Item_Stone_Forest": "RG_KOKIRI_EMERALD", "Item_Stone_Fire": "RG_GORON_RUBY", "Item_Stone_Water": "RG_ZORA_SAPPHIRE",
    "Item_Medal_Forest": "RG_FOREST_MEDALLION", "Item_Medal_Fire": "RG_FIRE_MEDALLION",
    "Item_Medal_Water": "RG_WATER_MEDALLION", "Item_Medal_Spirit": "RG_SPIRIT_MEDALLION",
    "Item_Medal_Shadow": "RG_SHADOW_MEDALLION", "Item_Medal_Light": "RG_LIGHT_MEDALLION",
    "Item_DinFire": "RG_DINS_FIRE", "Item_FaroreWind": "RG_FARORES_WIND", "Item_NayruLove": "RG_NAYRUS_LOVE",
    "Item_FairyBless_MP": "RG_PROGRESSIVE_MAGIC_METER", "Item_FairyBless_MP2": "RG_PROGRESSIVE_MAGIC_METER",
    "Item_Arrow_Fire": "RG_FIRE_ARROWS", "Item_Arrow_Light": "RG_LIGHT_ARROWS",
    "Weapon_Sword_Master": "RG_MASTER_SWORD", "Weapon_Sword_Biggoron": "RG_BIGGORON_SWORD",
    "Armor_Child_Gauntlet_Goron": "RG_PROGRESSIVE_STRENGTH", "Armor_Adult_Goron": "RG_GORON_TUNIC",
    "Item_MagicBean": "RG_MAGIC_BEAN", "Item_GerudoCard": "RG_GERUDO_MEMBERSHIP_CARD", "Item_WeirdEgg": "RG_WEIRD_EGG",
    "Item_DekuStick": "RG_DEKU_STICK_1", "Item_DekuNut": "RG_DEKU_NUTS_5", "Item_Melody_ScarecrowSong": "RG_SCARECROWS_SONG",
    "Item_Bottle_BlueFire": "RG_EMPTY_BOTTLE", "Item_Bottle_Bug": "RG_EMPTY_BOTTLE", "Item_Bottle_Fish": "RG_EMPTY_BOTTLE",
    "Item_Bottle_Fairy": "RG_EMPTY_BOTTLE",
}


def _map_files(romfs):
    return chests.map_files(romfs)


def _area_bounds(romfs):
    """{banc name ("KokiriForest_Child"): (min x, min z, max x, max z)} from each map's GameBancParam"""
    out = {}
    d = os.path.join(romfs, "Banc", "GameBancParam")
    for f in os.listdir(d):
        if not f.endswith(".bgyml"):
            continue
        try:
            doc = byml.read(open(os.path.join(d, f), "rb").read())[0]
        except (OSError, ValueError):
            continue
        hm = doc.get("HeightMapParam") or {}
        lo, hi = hm.get("BoundingBoxMin"), hm.get("BoundingBoxMax")
        if not lo:
            lo, hi = doc.get("WorldAabbMin"), doc.get("WorldAabbMax")
        if lo and hi:
            out[f.split(".")[0]] = (lo["X"], lo["Z"], hi["X"], hi["Z"])
    return out


def build_index(romfs, codec=None, log=print):
    """{"actors": {hash: [folder, age, x, y, z, gyaml]}, "by_gyaml": {gyaml: [[folder, age, x, z]...]},
    "outline": {folder/age: [[x, z]...]}, "bounds": {banc: [..]}}"""
    codec = codec or zs.Codec(romfs)
    actors, by_gyaml, outline = {}, collections.defaultdict(list), collections.defaultdict(list)
    rng = random.Random(1)
    for rel in _map_files(romfs):
        parts = rel.split("/")
        folder, name = parts[1], parts[2]
        age = "Adult" if "_Adult" in name else "Child" if "_Child" in name else "All"
        try:
            root, _ = byml.read(codec.read(os.path.join(romfs, *parts)))
        except (OSError, ValueError):
            continue
        key = "%s/%s" % (folder, age)
        for a in root.get("Actors", []):
            t = a.get("Translate")
            if not t:
                continue
            g = a.get("Gyaml", "")
            h = str(int(a.get("Hash", 0)))
            actors.setdefault(h, [folder, age, round(t[0], 2), round(t[1], 2), round(t[2], 2), g])
            if g.startswith(("Npc_", "Obj_TBox", "Enemy_")) or len(by_gyaml[g]) < 2:
                by_gyaml[g].append([folder, age, round(t[0], 1), round(t[2], 1)])
            if not g.startswith(("Area", "FldObj_AirWall", "EventRequest", "StartPos", "Dm_", "Rail")) and \
                    (len(outline[key]) < 2500 or rng.random() < 0.15):
                outline[key].append([round(t[0], 1), round(t[2], 1)])
    index = {"version": INDEX_VERSION, "actors": actors, "by_gyaml": dict(by_gyaml), "outline": dict(outline),
             "bounds": _area_bounds(romfs)}
    log("tracker index: %d actors in %d maps" % (len(actors), len(outline)))
    return index


def _index_path(romfs):
    stamp = os.path.getmtime(os.path.join(romfs, "Pack", "ZsDic.pack.zs"))
    return os.path.join(APPDATA, "cache", "index-%d-%d.json" % (INDEX_VERSION, int(stamp)))


def load_index(romfs, log=print):
    path = _index_path(romfs)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        pass
    index = build_index(romfs, log=log)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f)
    return index


class Check:
    __slots__ = ("id", "name", "area", "folder", "kind", "item", "rg", "pos", "y", "age", "hashes", "flag")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


class Model:
    """the installed seed of a game folder, its checks with positions, and logic"""

    def __init__(self, game_folder, log=print):
        self.game = game_folder
        self.romfs = os.path.join(game_folder, "romfs")
        mod = None
        for name in (generate.MOD_NAME, "_" + generate.MOD_NAME):
            if os.path.isfile(os.path.join(game_folder, "mods", name, "placements.json")):
                mod = os.path.join(game_folder, "mods", name)
                break
        if not mod:
            raise FileNotFoundError("no seed installed in %s" % game_folder)
        with open(os.path.join(mod, "placements.json"), encoding="utf-8") as f:
            self.plan = json.load(f)
        self.seed = self.plan.get("seed", "?")
        codec = zs.Codec(self.romfs)
        self.index = load_index(self.romfs, log=log)
        from . import settings as rando_settings
        # (an older seed's placements.json lacks the newer settings: they mean what the randomizer did then)
        self.settings = rando_settings.normalized(self.plan.get("settings", {}), legacy=True)
        self.setup = generate.Setup(self.romfs, codec, settings=self.settings)
        self.world = self.setup.world
        self.checks = self._checks()

    def _checks(self):
        s, plan, idx = self.setup, self.plan, self.index
        by_hash = {str(l.hash): l for l in s.locs if l.hash is not None}
        gifts = {c["id"]: c for c in s.gifts["checks"]}
        loose_of = {str(a["hash"]): c["id"] for c in s.gifts["checks"] if c["kind"] == "loose" for a in c["loose"]}
        placed = {}
        for h, v in plan.get("chests", {}).items():
            if h in by_hash:
                placed[by_hash[h].id] = v["item"]
        placed.update(plan.get("gifts", {}))
        for h, a in plan.get("loose", {}).items():
            if h in loose_of:
                placed[loose_of[h]] = a
        from .pickups import DROP_PREFIX
        for h, a in plan.get("skulltulas", {}).items():   # (a skulltula's drop: the pickup made of the item; none: a token)
            if h in by_hash:
                placed[by_hash[h].id] = a[len(DROP_PREFIX):] if a.startswith(DROP_PREFIX) else a
        out = []
        for l in s.locs:
            item = placed.get(l.id, l.vanilla)
            pos = folder = age = y = None
            hashes = []
            flows = [e.get("flow", "") for e in gifts.get(l.id, {}).get("edits", [])]
            if l.hash is not None and str(l.hash) in idx["actors"]:
                folder, age, x, y, z, _ = idx["actors"][str(l.hash)]
                pos = (x, z)
                if l.kind == "skulltula":   # (killed and its drop got: the token's AI saves the skulltula's own key)
                    hashes = [l.hash]
            elif l.kind == "loose":
                hashes = [int(a["hash"]) for a in gifts[l.id]["loose"]]
                for a in gifts[l.id]["loose"]:
                    if str(a["hash"]) in idx["actors"]:
                        folder, age, x, y, z, _ = idx["actors"][str(a["hash"])]
                        pos = (x, z)
                        break
            elif l.kind == "gift" and l.id in GIFT_ANCHORS:
                folder, x, z = GIFT_ANCHORS[l.id]
                pos, age = (x, z), "All"
            elif l.kind == "gift":
                for fl in flows:
                    hit = idx["by_gyaml"].get(fl)
                    if hit:
                        folder, age, x, z = hit[0]
                        pos = (x, z)
                        break
            area_name = l.name.split(":")[0]
            if folder in (None, "HyruleField"):
                folder = next((key for prefix, key in AREA_OF_SOH.items() if area_name.startswith(prefix)), folder)
            if folder is None:
                folder = next((f for f, n in AREAS.items() if n.split(" &")[0].lower() in area_name.lower()), None)
            try:
                rg = I.soh_item(I.canonical(item), l.map)
            except (KeyError, ValueError):
                rg = "RG_NONE"
            flag = DONE_FLAGS.get(l.id) or next(
                ("HavePlayedEvent." + fl for fl in flows if fl.startswith(SONG_FLOW)), None)
            out.append(Check(id=l.id, name=l.name, area=area_name, folder=folder, kind=l.kind, item=item, rg=rg,
                             pos=pos, y=y, age=age, hashes=hashes, flag=flag))
        return out

    def collected(self, save):
        """{check id: why} of the checks the save shows taken: a loose item's own key, a gift's one-time flag, a song's
        cutscene; an item held that only this check gives (the save keeps no flag of an opened chest); a dungeon's map,
        compass and boss key, and its small keys when all of them are had"""
        bools, keys64 = save["bool"], save["bool64"]
        out = {}
        for c in self.checks:
            if c.hashes and any(h in keys64 for h in c.hashes):
                out[c.id] = "picked up"
            elif c.flag and bools.get(savefile.murmur3(c.flag)):
                out[c.id] = "given"
        holders = collections.defaultdict(list)
        for c in self.checks:
            holders[I.canonical(c.item)].append(c)
        aliases = collections.defaultdict(list)
        for alias, actor in SAVE_ALIASES.items():
            aliases[actor].append(alias)
        for actor, cs in holders.items():
            if len(cs) != 1 or actor.startswith(NOT_UNIQUE_PREFIXES) or any(w in actor for w in NOT_UNIQUE_WORDS):
                continue
            if any(savefile.is_get(save, name) for name in [actor] + aliases[actor]):
                out.setdefault(cs[0].id, "item held")
        fixed_keys = collections.Counter(rg for rg in self.setup.fixed.values() if rg.endswith("_SMALL_KEY"))
        keys = collections.defaultdict(list)
        for c in self.checks:
            own = I.dungeon_item(I.canonical(c.item), c.folder)   # (the game's one in its dungeon, or one of its own)
            if own is None:
                continue
            actor, folder = own
            base = "DungeonInfo.%s." % folder
            kind = I.DUNGEON_ITEMS[actor]
            if kind == "SMALL_KEY":
                keys[folder].append(c)
            elif bools.get(savefile.murmur3(base + {"MAP": "IsGetMap", "COMPASS": "IsGetCompass",
                                                    "BOSS_KEY": "IsGetBossKey"}[kind])):
                out.setdefault(c.id, "dungeon item")
        for folder, cs in keys.items():
            got = save["int"].get(savefile.murmur3("DungeonInfo.%s.SmallKeyTotalNum" % folder), 0)
            if got and got >= len(cs) + fixed_keys["RG_%s_SMALL_KEY" % I.DUNGEONS[folder]]:
                for c in cs:
                    out.setdefault(c.id, "all keys had")
        return out

    def inventory(self, save):
        """Counter of SoH items Link holds, from the save's IsGet flags and dungeon keys"""
        have = collections.Counter()
        names = set(I.ITEMS) | set(SAVE_ALIASES) | set(SAVE_EXTRA) | {a for g in I.TIERS for a in g}
        for name in names:
            if not savefile.is_get(save, name):
                continue
            actor = SAVE_ALIASES.get(name, name)
            if name in SAVE_EXTRA:
                rg = SAVE_EXTRA[name]
            else:
                try:
                    rg = I.soh_item(actor, None)
                except (KeyError, ValueError):
                    continue
            if rg and rg != "RG_NONE":
                have[rg] += 1
        # (an equipped-name alias and the item's own name are one item)
        for alias, actor in SAVE_ALIASES.items():
            if savefile.is_get(save, alias) and savefile.is_get(save, actor):
                try:
                    have[I.soh_item(actor, None)] -= 1
                except (KeyError, ValueError):
                    pass
        for folder, dungeon in I.DUNGEONS.items():
            base = "DungeonInfo.%s." % folder
            total = save["int"].get(savefile.murmur3(base + "SmallKeyTotalNum"))
            if total is None:
                total = save["int"].get(savefile.murmur3(base + "SmallKeyNum"), 0)
            if total:
                have["RG_%s_SMALL_KEY" % dungeon] += total
            if save["bool"].get(savefile.murmur3(base + "IsGetBossKey")):
                have["RG_%s_BOSS_KEY" % dungeon] += 1
        from .logic import soh_data
        return collections.Counter({k: v for k, v in have.items() if v > 0 and k in soh_data.ENUM_VALUE})

    def reachable(self, have):
        """the checks logic reaches with these items, the shops' purchases (RG_BUY_*: the Deku Shield the logic asks a
        child to show Mido...) bought as their shops come in reach, as the fill counts them"""
        buys = {rc: rg for rc, rg in self.setup.fixed.items() if rg.startswith("RG_BUY_")}
        final, _ = self.world.collect(collections.Counter(have), buys)
        return self.world.reachable(final)

    def states(self, have, marks, taken=()):
        """{check id: state}; taken: the checks the save shows done (collected())"""
        reach = self.reachable(have)
        out = {}
        for c in self.checks:
            if c.id in marks or c.id in taken:
                out[c.id] = "done"
            elif c.id in self.setup.closed and c.id not in reach:
                out[c.id] = "unknown"
            else:
                out[c.id] = "available" if c.id in reach else "blocked"
        return out


def marks_path(seed):
    return os.path.join(APPDATA, "tracker", "%s.json" % "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in seed))


def load_marks(seed):
    try:
        with open(marks_path(seed), encoding="utf-8") as f:
            return set(json.load(f).get("done", []))
    except (OSError, ValueError):
        return set()


def save_marks(seed, marks):
    os.makedirs(os.path.dirname(marks_path(seed)), exist_ok=True)
    with open(marks_path(seed), "w", encoding="utf-8") as f:
        json.dump({"done": sorted(marks)}, f, indent=1)
