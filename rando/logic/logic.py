"""A port of SoH's Logic (soh/Enhancements/randomizer/logic.cpp, logic.h) and the settings context rules read (ctx->).

Functions keep SoH's names and arguments, so translated rules (rando.logic.translate) call them 1:1; enum values are
their SoH names as strings (numbers where SoH does arithmetic on them: soh_data.ENUM_VALUE). The save context is the
part of SoH's SaveContext the Logic reads and writes (inventory slots, upgrades bitfield, equipment, quest items,
dungeon items and keys, randomizer inf flags, health, magic), laid out as OoT's (soh_data.OOT).

The settings are fixed to the unmodified game (the mod does not change world rules). Every option any ported code
reads is in SETTINGS; reading one that is not is an error. All tricks are off (GetTrickOption is 0 for every trick),
no glitches, every dungeon vanilla (not MQ), no trial skipped.

SETTINGS (option: value: why)
  RSK_SELECTED_STARTING_AGE       RO_AGE_CHILD                    a new game starts as child
  RSK_FOREST                      RO_CLOSED_FOREST_ON             closed forest: Mido wants sword and shield
  RSK_DOOR_OF_TIME                RO_DOOROFTIME_CLOSED            Door of Time: 3 stones + Ocarina of Time + Song of Time
  RSK_ZORAS_FOUNTAIN              RO_ZF_CLOSED                    King Zora moves for Ruto's letter
  RSK_SLEEPING_WATERFALL          RO_WATERFALL_CLOSED             Zelda's Lullaby opens the waterfall
  RSK_JABU_OPEN                   RO_JABU_CLOSED                  Jabu-Jabu needs the fish
  RSK_GERUDO_FORTRESS             RO_GF_CARPENTERS_NORMAL         rescue all four carpenters
  RSK_RAINBOW_BRIDGE              RO_BRIDGE_VANILLA               Shadow + Spirit medallions and Light Arrows
  RSK_BRIDGE_OPTIONS              RO_BRIDGE_STANDARD_REWARD       (read only by non-vanilla bridges)
  RSK_RAINBOW_BRIDGE_*_COUNT      (not read: vanilla bridge)
  RSK_TRIAL_COUNT                 6                               all six of Ganon's trials (GetTrial(..)->IsSkipped() false)
  RSK_MEDALLION_LOCKED_TRIALS     RO_GENERIC_OFF                  trials open without medallions
  RSK_GANONS_BOSS_KEY             RO_GANON_BOSS_KEY_VANILLA       in its Ganon's Tower chest (GBK condition: none)
  RSK_GANONS_SOUL                 RO_GANONS_SOUL_STARTWITH        no Ganon's soul item in the game
  RSK_WINCON                      RO_WINCON_DEFEAT_GANON          the win is defeating Ganon (RC_GANON)
  RSK_KEYSANITY                   RO_DUNGEON_ITEM_LOC_VANILLA     small keys where the game has them
  RSK_BOSS_KEYSANITY              RO_DUNGEON_ITEM_LOC_VANILLA     boss keys where the game has them
  RSK_GERUDO_KEYS                 RO_GERUDO_KEYS_VANILLA          hideout keys from the guards
  RSK_SHUFFLE_MAPANDCOMPASS       RO_DUNGEON_ITEM_LOC_VANILLA
  RSK_SHUFFLE_DUNGEON_REWARDS     RO_DUNGEON_REWARDS_VANILLA      stones/medallions from their bosses
  RSK_SHUFFLE_SILVER              RO_SHUFFLE_SILVER_OFF           silver rupees are events, not items
  RSK_SHUFFLE_SWIM/GRAB/CLIMB/CRAWL/OPEN_CHEST/SPEAK                off: Link can swim, grab, climb, crawl, open chests
                                  RO_GENERIC_OFF / RO_OPEN_CHEST_OFF   and speak from the start (Logic::Reset grants
                                                                  RAND_INF_CAN_SWIM etc.)
  RSK_SHUFFLE_CHILD_WALLET        RO_GENERIC_OFF                  the starting 99-rupee wallet
  RSK_SHUFFLE_FISHING_POLE        RO_GENERIC_OFF                  the pond lends the rod
  RSK_SHUFFLE_OCARINA_BUTTONS     RO_GENERIC_OFF                  all ocarina buttons
  RSK_SHUFFLE_DEKU_STICK_BAG/NUT_BAG  RO_GENERIC_OFF              stick/nut capacity 1 from the start
  RSK_SHUFFLE_BEAN_SOULS          RO_GENERIC_OFF                  every bean patch usable
  RSK_SHUFFLE_BOSS_SOULS          RO_BOSS_SOULS_OFF               bosses always present
  RSK_LOCK_OVERWORLD_DOORS        RO_GENERIC_OFF                  no overworld door keys
  RSK_SHUFFLE_MASKS               RO_GENERIC_OFF                  masks borrowed from the mask shop
  RSK_SHUFFLE_ADULT_TRADE         RO_GENERIC_OFF                  the trade sequence as in the game
  RSK_SHUFFLE_WEIRD_EGG           RO_WEIRD_EGG_VANILLA            Malon gives the egg
  RSK_SHUFFLE_ZELDAS_LETTER       RO_GENERIC_OFF                  Zelda gives the letter
  RSK_SHUFFLE_GERUDO_MEMBERSHIP_CARD  RO_GENERIC_OFF
  RSK_SHUFFLE_SCARECROWS_SONG     RO_GENERIC_OFF                  Pierre's song taught at Lake Hylia
  RSK_SHUFFLE_CHEST_MINIGAME      RO_GENERIC_OFF                  the treasure chest game played as in the game
  RSK_SHUFFLE_SCRUBS              RO_SCRUBS_OFF
  RSK_SHUFFLE_POTS                RO_SHUFFLE_POTS_OFF
  RSK_SHUFFLE_DUNGEON_ENTRANCES   RO_DUNGEON_ENTRANCE_SHUFFLE_OFF  no entrance shuffle of any kind (all the
  RSK_SHUFFLE_BOSS_ENTRANCES      RO_BOSS_ROOM_ENTRANCE_SHUFFLE_OFF   entrance options below too)
  RSK_SHUFFLE_ENTRANCES, RSK_DECOUPLED_ENTRANCES, RSK_MIX_BOSS/DUNGEON/INTERIOR/OVERWORLD_ENTRANCES  RO_GENERIC_OFF
  RSK_SHOP_SHIELDS_AND_TUNICS_ONLY_REFILL  RO_GENERIC_OFF
  RSK_BOMBCHU_BAG                 RO_BOMBCHU_BAG_NONE             no bombchu bag item: chus are their own ammo, usable
                                                                  with a bomb bag (SoH's default and the game's)
  RSK_ENABLE_BOMBCHU_DROPS        RO_AMMO_DROPS_OFF               the game drops no bombchus (refills: shop, bowling,
                                                                  carpet merchant)
  RSK_INFINITE_UPGRADES           RO_INF_UPGRADES_OFF
  RSK_INCLUDE_TYCOON_WALLET       RO_GENERIC_OFF
  RSK_PROGRESSIVE_GORON_SWORD     RO_GENERIC_OFF                  Medigoron sells the Giant's Knife
  RSK_SKIP_EPONA_RACE             RO_GENERIC_DONT_SKIP            Epona needs the Ingo race
  RSK_SKIP_PLANTING_BEANS         RO_GENERIC_OFF                  beans planted as child
  RSK_EARLY_GRANNYS_SHOP          RO_GENERIC_OFF
  RSK_BIG_POE_COUNT               10                              ten big poes for the poe collector
  RSK_DAMAGE_MULTIPLIER           RO_DAMAGE_MULTIPLIER_DEFAULT    x1
  RSK_STARTING_HEARTS             2                               (index of NumOpts(1, 20)) three hearts
  RSK_NAYRUS_LOVE_USES            0                               Nayru's Love as in the game
  RSK_SKULLS_SUNS_SONG            RO_GENERIC_OFF                  night skulltulas need night, not Sun's Song
  RSK_BLUE_FIRE_ARROWS, RSK_SUNLIGHT_ARROWS, RSK_BUNNY_HOOD (MM speed), RSK_MASKS_AS_ADULT,
  RSK_SLINGBOW_BREAK_BEEHIVES, RSK_FISHSANITY_AGE_SPLIT          RO_GENERIC_OFF   (SoH enhancements the game lacks)
  RSK_STARTING_* (every starting item option)  off / 0            a new game starts with nothing (child, 3 hearts)
  RSK_NO_LOGIC                    RO_GENERIC_OFF
"""
from . import soh_data as D
from . import soh_regions as R


class LogicError(Exception):
    pass


EV = D.ENUM_VALUE          # (SoH enum name: value)
OOT = D.OOT
ITEM_ID = OOT["ItemID"]
SLOT = OOT["InventorySlot"]
SLOT_NAMES = {v: k for k, v in SLOT.items()}

# ---- settings

_OFF = "RO_GENERIC_OFF"
SETTINGS = {
    "RSK_SELECTED_STARTING_AGE": "RO_AGE_CHILD",
    "RSK_FOREST": "RO_CLOSED_FOREST_ON",
    "RSK_DOOR_OF_TIME": "RO_DOOROFTIME_CLOSED",
    "RSK_ZORAS_FOUNTAIN": "RO_ZF_CLOSED",
    "RSK_SLEEPING_WATERFALL": "RO_WATERFALL_CLOSED",
    "RSK_JABU_OPEN": "RO_JABU_CLOSED",
    "RSK_GERUDO_FORTRESS": "RO_GF_CARPENTERS_NORMAL",
    "RSK_RAINBOW_BRIDGE": "RO_BRIDGE_VANILLA",
    "RSK_BRIDGE_OPTIONS": "RO_BRIDGE_STANDARD_REWARD",
    "RSK_TRIAL_COUNT": 6,
    "RSK_MEDALLION_LOCKED_TRIALS": _OFF,
    "RSK_GANONS_BOSS_KEY": "RO_GANON_BOSS_KEY_VANILLA",
    "RSK_GANONS_SOUL": "RO_GANONS_SOUL_STARTWITH",
    "RSK_WINCON": "RO_WINCON_DEFEAT_GANON",
    "RSK_KEYSANITY": "RO_DUNGEON_ITEM_LOC_VANILLA",
    "RSK_BOSS_KEYSANITY": "RO_DUNGEON_ITEM_LOC_VANILLA",
    "RSK_GERUDO_KEYS": "RO_GERUDO_KEYS_VANILLA",
    "RSK_SHUFFLE_MAPANDCOMPASS": "RO_DUNGEON_ITEM_LOC_VANILLA",
    "RSK_SHUFFLE_DUNGEON_REWARDS": "RO_DUNGEON_REWARDS_VANILLA",
    "RSK_SHUFFLE_SILVER": "RO_SHUFFLE_SILVER_OFF",
    "RSK_SHUFFLE_SWIM": _OFF,
    "RSK_SHUFFLE_GRAB": _OFF,
    "RSK_SHUFFLE_CLIMB": _OFF,
    "RSK_SHUFFLE_CRAWL": _OFF,
    "RSK_SHUFFLE_OPEN_CHEST": "RO_OPEN_CHEST_OFF",
    "RSK_SHUFFLE_SPEAK": _OFF,
    "RSK_SHUFFLE_CHILD_WALLET": _OFF,
    "RSK_SHUFFLE_FISHING_POLE": _OFF,
    "RSK_SHUFFLE_OCARINA_BUTTONS": _OFF,
    "RSK_SHUFFLE_DEKU_STICK_BAG": _OFF,
    "RSK_SHUFFLE_DEKU_NUT_BAG": _OFF,
    "RSK_SHUFFLE_BEAN_SOULS": _OFF,
    "RSK_SHUFFLE_BOSS_SOULS": "RO_BOSS_SOULS_OFF",
    "RSK_LOCK_OVERWORLD_DOORS": _OFF,
    "RSK_SHUFFLE_MASKS": _OFF,
    "RSK_SHUFFLE_ADULT_TRADE": _OFF,
    "RSK_SHUFFLE_WEIRD_EGG": "RO_WEIRD_EGG_VANILLA",
    "RSK_SHUFFLE_ZELDAS_LETTER": _OFF,
    "RSK_SHUFFLE_GERUDO_MEMBERSHIP_CARD": _OFF,
    "RSK_SHUFFLE_SCARECROWS_SONG": _OFF,
    "RSK_SHUFFLE_CHEST_MINIGAME": _OFF,
    "RSK_SHUFFLE_SCRUBS": "RO_SCRUBS_OFF",
    "RSK_SHUFFLE_POTS": "RO_SHUFFLE_POTS_OFF",
    "RSK_SHUFFLE_DUNGEON_ENTRANCES": "RO_DUNGEON_ENTRANCE_SHUFFLE_OFF",
    "RSK_SHUFFLE_BOSS_ENTRANCES": "RO_BOSS_ROOM_ENTRANCE_SHUFFLE_OFF",
    "RSK_SHUFFLE_ENTRANCES": _OFF,
    "RSK_DECOUPLED_ENTRANCES": _OFF,
    "RSK_MIX_BOSS_ENTRANCES": _OFF,
    "RSK_MIX_DUNGEON_ENTRANCES": _OFF,
    "RSK_MIX_INTERIOR_ENTRANCES": _OFF,
    "RSK_MIX_OVERWORLD_ENTRANCES": _OFF,
    "RSK_SHOP_SHIELDS_AND_TUNICS_ONLY_REFILL": _OFF,
    "RSK_BOMBCHU_BAG": "RO_BOMBCHU_BAG_NONE",
    "RSK_ENABLE_BOMBCHU_DROPS": "RO_AMMO_DROPS_OFF",
    "RSK_INFINITE_UPGRADES": "RO_INF_UPGRADES_OFF",
    "RSK_INCLUDE_TYCOON_WALLET": _OFF,
    "RSK_PROGRESSIVE_GORON_SWORD": _OFF,
    "RSK_SKIP_EPONA_RACE": "RO_GENERIC_DONT_SKIP",
    "RSK_SKIP_PLANTING_BEANS": _OFF,
    "RSK_EARLY_GRANNYS_SHOP": _OFF,
    "RSK_BIG_POE_COUNT": 10,
    "RSK_DAMAGE_MULTIPLIER": "RO_DAMAGE_MULTIPLIER_DEFAULT",
    "RSK_STARTING_HEARTS": 2,
    "RSK_NAYRUS_LOVE_USES": 0,
    "RSK_SKULLS_SUNS_SONG": _OFF,
    "RSK_BLUE_FIRE_ARROWS": _OFF,
    "RSK_SUNLIGHT_ARROWS": _OFF,
    "RSK_BUNNY_HOOD": _OFF,
    "RSK_MASKS_AS_ADULT": _OFF,
    "RSK_SLINGBOW_BREAK_BEEHIVES": _OFF,
    "RSK_FISHSANITY_AGE_SPLIT": _OFF,
    "RSK_NO_LOGIC": _OFF,
    # (starting inventory: 3drando/starting_inventory.cpp reads these; all off / 0)
    "RSK_STARTING_ZELDAS_LETTER": _OFF,
    "RSK_STARTING_GERUDO_CARD": _OFF,
    "RSK_STARTING_OCARINA": "RO_STARTING_OCARINA_OFF",
    "RSK_STARTING_BIGGORON_SWORD": "RO_STARTING_BGS_OFF",
    "RSK_STARTING_BOTTLE_1": "RO_STARTING_BOTTLE_OFF",
    "RSK_STARTING_BOTTLE_2": "RO_STARTING_BOTTLE_OFF",
    "RSK_STARTING_BOTTLE_3": "RO_STARTING_BOTTLE_OFF",
    "RSK_STARTING_BOTTLE_4": "RO_STARTING_BOTTLE_OFF",
    **{k: 0 for k in (
        "RSK_STARTING_BOMB_BAG", "RSK_STARTING_BOW", "RSK_STARTING_SLINGSHOT", "RSK_STARTING_HOOKSHOT",
        "RSK_STARTING_BOMBCHU_BAG", "RSK_STARTING_MAGIC_METER", "RSK_STARTING_STRENGTH", "RSK_STARTING_SCALE",
        "RSK_STARTING_WALLET", "RSK_STARTING_SKULLTULA_TOKEN")},
    **{k: _OFF for k in (
        "RSK_STARTING_BOOMERANG", "RSK_STARTING_LENS_OF_TRUTH", "RSK_STARTING_MEGATON_HAMMER",
        "RSK_STARTING_IRON_BOOTS", "RSK_STARTING_HOVER_BOOTS", "RSK_STARTING_DINS_FIRE", "RSK_STARTING_FARORES_WIND",
        "RSK_STARTING_NAYRUS_LOVE", "RSK_STARTING_FIRE_ARROWS", "RSK_STARTING_ICE_ARROWS",
        "RSK_STARTING_LIGHT_ARROWS", "RSK_STARTING_HYLIAN_SHIELD", "RSK_STARTING_MIRROR_SHIELD",
        "RSK_STARTING_GORON_TUNIC", "RSK_STARTING_ZORA_TUNIC", "RSK_STARTING_STONE_OF_AGONY",
        "RSK_STARTING_WEIRD_EGG", "RSK_STARTING_SCARECROWS_SONG", "RSK_STARTING_KEATON_MASK",
        "RSK_STARTING_SKULL_MASK", "RSK_STARTING_SPOOKY_MASK", "RSK_STARTING_BUNNY_HOOD", "RSK_STARTING_GORON_MASK",
        "RSK_STARTING_ZORA_MASK", "RSK_STARTING_GERUDO_MASK", "RSK_STARTING_MASK_OF_TRUTH",
        "RSK_STARTING_CLAIM_CHECK", "RSK_STARTING_ZELDAS_LULLABY", "RSK_STARTING_EPONAS_SONG",
        "RSK_STARTING_SARIAS_SONG", "RSK_STARTING_SUNS_SONG", "RSK_STARTING_SONG_OF_TIME",
        "RSK_STARTING_SONG_OF_STORMS", "RSK_STARTING_MINUET_OF_FOREST", "RSK_STARTING_BOLERO_OF_FIRE",
        "RSK_STARTING_SERENADE_OF_WATER", "RSK_STARTING_REQUIEM_OF_SPIRIT", "RSK_STARTING_NOCTURNE_OF_SHADOW",
        "RSK_STARTING_PRELUDE_OF_LIGHT", "RSK_STARTING_KOKIRI_SWORD", "RSK_STARTING_BEANS",
        "RSK_STARTING_MASTER_SWORD", "RSK_STARTING_DEKU_SHIELD")},
}
# (SoH's Context: the trigger conditions it derives from the options; vanilla GBK / start-with soul: none)
GBK_CONDITION = "RO_CHECK_TRIGGER_NONE"
GANONS_SOUL_CONDITION = "RO_CHECK_TRIGGER_NONE"


def _value(v):
    return EV[v] if isinstance(v, str) else int(v)


class OptionValue:
    """SoH's OptionValue: Is/IsNot compare the numeric value, Get gives it, bool tests it"""
    __slots__ = ("value", "name")

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def Is(self, v):
        return self.value == _value(v)

    def IsNot(self, v):
        return self.value != _value(v)

    def Get(self):
        return self.value

    def __bool__(self):
        return self.value != 0

    def __repr__(self):
        return f"OptionValue({self.name}={self.value})"


class Dungeon:
    def __init__(self, key):
        self.key = key

    def IsVanilla(self):
        return True

    def IsMQ(self):
        return False


class Trial:
    def __init__(self, key):
        self.key = key

    def IsSkipped(self):
        return False


class Ctx:
    """the ctx-> rules read: options (SETTINGS), tricks (all off), dungeons (all vanilla), trials (none skipped)"""

    def __init__(self, settings=SETTINGS):
        self.options = {}
        for k, v in settings.items():
            if D.ENUM_OF.get(k) != "RandomizerSettingKey":
                raise LogicError(f"setting {k} is not a RandomizerSettingKey")
            if isinstance(v, str) and v not in EV:
                raise LogicError(f"setting {k}: unknown value {v}")
            self.options[k] = OptionValue(k, _value(v))
        self._trick = {}
        self._dungeons = {k: Dungeon(k) for k in D.ENUMS["DungeonKey"]}
        self._trials = {k: Trial(k) for k in D.ENUMS["TrialKey"] if k != "TK_MAX"}

    def GetOption(self, key):
        try:
            return self.options[key]
        except KeyError:
            raise LogicError(f"option {key} read but not fixed in logic.SETTINGS") from None

    def GetTrickOption(self, key):
        o = self._trick.get(key)
        if o is None:
            if D.ENUM_OF.get(key) != "RandomizerTrick":
                raise LogicError(f"unknown trick {key}")
            o = self._trick[key] = OptionValue(key, 0)
        return o

    def GetDungeon(self, key):
        return self._dungeons[key]

    def GetTrial(self, key):
        return self._trials[key]

    def GBKCondition(self):
        return GBK_CONDITION

    def GanonsSoulCondition(self):
        return GANONS_SOUL_CONDITION

    def WinCondition(self):
        return SETTINGS["RSK_WINCON"]


# ---- static tables of logic.cpp

EQUIP_FLAG = OOT["EquipmentFlag"]
QUEST = OOT["QuestItem"]
UPG = OOT["UpgradeType"]
DUNGEON_ITEM = OOT["DungeonItem"]
FULL_HEART_HEALTH = 16      # (z64save.h / SoH: health units per heart)

# logic.cpp equipFlagTable
RANDO_GET_TO_EQUIP_FLAG = {
    "RG_KOKIRI_SWORD": "EQUIP_FLAG_SWORD_KOKIRI", "RG_MASTER_SWORD": "EQUIP_FLAG_SWORD_MASTER",
    "RG_GIANTS_KNIFE": "EQUIP_FLAG_SWORD_BGS", "RG_BIGGORON_SWORD": "EQUIP_FLAG_SWORD_BGS",
    "RG_DEKU_SHIELD": "EQUIP_FLAG_SHIELD_DEKU", "RG_HYLIAN_SHIELD": "EQUIP_FLAG_SHIELD_HYLIAN",
    "RG_MIRROR_SHIELD": "EQUIP_FLAG_SHIELD_MIRROR", "RG_GORON_TUNIC": "EQUIP_FLAG_TUNIC_GORON",
    "RG_ZORA_TUNIC": "EQUIP_FLAG_TUNIC_ZORA", "RG_BUY_DEKU_SHIELD": "EQUIP_FLAG_SHIELD_DEKU",
    "RG_BUY_HYLIAN_SHIELD": "EQUIP_FLAG_SHIELD_HYLIAN", "RG_BUY_GORON_TUNIC": "EQUIP_FLAG_TUNIC_GORON",
    "RG_BUY_ZORA_TUNIC": "EQUIP_FLAG_TUNIC_ZORA", "RG_IRON_BOOTS": "EQUIP_FLAG_BOOTS_IRON",
    "RG_HOVER_BOOTS": "EQUIP_FLAG_BOOTS_HOVER",
}

# logic.cpp randInfTable (StaticData::RandoGetToRandInf)
RANDO_GET_TO_RAND_INF = {
    "RG_BRONZE_SCALE": "RAND_INF_CAN_SWIM", "RG_POWER_BRACELET": "RAND_INF_CAN_GRAB",
    "RG_ZELDAS_LETTER": "RAND_INF_ZELDAS_LETTER", "RG_CLIMB": "RAND_INF_CAN_CLIMB", "RG_CRAWL": "RAND_INF_CAN_CRAWL",
    "RG_OPEN_CHEST": "RAND_INF_CAN_OPEN_CHEST", "RG_CHILD_WALLET": "RAND_INF_HAS_WALLET",
    "RG_QUIVER_INF": "RAND_INF_HAS_INFINITE_QUIVER", "RG_BOMB_BAG_INF": "RAND_INF_HAS_INFINITE_BOMB_BAG",
    "RG_BULLET_BAG_INF": "RAND_INF_HAS_INFINITE_BULLET_BAG", "RG_STICK_UPGRADE_INF":
        "RAND_INF_HAS_INFINITE_STICK_UPGRADE", "RG_NUT_UPGRADE_INF": "RAND_INF_HAS_INFINITE_NUT_UPGRADE",
    "RG_MAGIC_INF": "RAND_INF_HAS_INFINITE_MAGIC_METER", "RG_BOMBCHU_INF": "RAND_INF_HAS_INFINITE_BOMBCHUS",
    "RG_WALLET_INF": "RAND_INF_HAS_INFINITE_MONEY", "RG_WEIRD_EGG": "RAND_INF_WEIRD_EGG",
    "RG_COJIRO": "RAND_INF_ADULT_TRADES_HAS_COJIRO", "RG_ODD_MUSHROOM": "RAND_INF_ADULT_TRADES_HAS_ODD_MUSHROOM",
    "RG_ODD_POTION": "RAND_INF_ADULT_TRADES_HAS_ODD_POTION", "RG_POACHERS_SAW": "RAND_INF_ADULT_TRADES_HAS_SAW",
    "RG_BROKEN_SWORD": "RAND_INF_ADULT_TRADES_HAS_SWORD_BROKEN",
    "RG_PRESCRIPTION": "RAND_INF_ADULT_TRADES_HAS_PRESCRIPTION", "RG_EYEBALL_FROG": "RAND_INF_ADULT_TRADES_HAS_FROG",
    "RG_EYEDROPS": "RAND_INF_ADULT_TRADES_HAS_EYEDROPS", "RG_CLAIM_CHECK": "RAND_INF_ADULT_TRADES_HAS_CLAIM_CHECK",
    "RG_RUTOS_LETTER": "RAND_INF_OBTAINED_RUTOS_LETTER",
    "RG_DEATH_MOUNTAIN_CRATER_BEAN_SOUL": "RAND_INF_DEATH_MOUNTAIN_CRATER_BEAN_SOUL",
    "RG_DEATH_MOUNTAIN_TRAIL_BEAN_SOUL": "RAND_INF_DEATH_MOUNTAIN_TRAIL_BEAN_SOUL",
    "RG_DESERT_COLOSSUS_BEAN_SOUL": "RAND_INF_DESERT_COLOSSUS_BEAN_SOUL",
    "RG_GERUDO_VALLEY_BEAN_SOUL": "RAND_INF_GERUDO_VALLEY_BEAN_SOUL",
    "RG_GRAVEYARD_BEAN_SOUL": "RAND_INF_GRAVEYARD_BEAN_SOUL",
    "RG_KOKIRI_FOREST_BEAN_SOUL": "RAND_INF_KOKIRI_FOREST_BEAN_SOUL",
    "RG_LAKE_HYLIA_BEAN_SOUL": "RAND_INF_LAKE_HYLIA_BEAN_SOUL",
    "RG_LOST_WOODS_BRIDGE_BEAN_SOUL": "RAND_INF_LOST_WOODS_BRIDGE_BEAN_SOUL",
    "RG_LOST_WOODS_BEAN_SOUL": "RAND_INF_LOST_WOODS_BEAN_SOUL",
    "RG_ZORAS_RIVER_BEAN_SOUL": "RAND_INF_ZORAS_RIVER_BEAN_SOUL",
    "RG_GOHMA_SOUL": "RAND_INF_GOHMA_SOUL", "RG_KING_DODONGO_SOUL": "RAND_INF_KING_DODONGO_SOUL",
    "RG_BARINADE_SOUL": "RAND_INF_BARINADE_SOUL", "RG_PHANTOM_GANON_SOUL": "RAND_INF_PHANTOM_GANON_SOUL",
    "RG_VOLVAGIA_SOUL": "RAND_INF_VOLVAGIA_SOUL", "RG_MORPHA_SOUL": "RAND_INF_MORPHA_SOUL",
    "RG_BONGO_BONGO_SOUL": "RAND_INF_BONGO_BONGO_SOUL", "RG_TWINROVA_SOUL": "RAND_INF_TWINROVA_SOUL",
    "RG_GANON_SOUL": "RAND_INF_GANON_SOUL",
    "RG_OCARINA_A_BUTTON": "RAND_INF_HAS_OCARINA_A", "RG_OCARINA_C_UP_BUTTON": "RAND_INF_HAS_OCARINA_C_UP",
    "RG_OCARINA_C_DOWN_BUTTON": "RAND_INF_HAS_OCARINA_C_DOWN", "RG_OCARINA_C_LEFT_BUTTON": "RAND_INF_HAS_OCARINA_C_LEFT",
    "RG_OCARINA_C_RIGHT_BUTTON": "RAND_INF_HAS_OCARINA_C_RIGHT",
    "RG_KEATON_MASK": "RAND_INF_CHILD_TRADES_HAS_MASK_KEATON", "RG_SKULL_MASK": "RAND_INF_CHILD_TRADES_HAS_MASK_SKULL",
    "RG_SPOOKY_MASK": "RAND_INF_CHILD_TRADES_HAS_MASK_SPOOKY", "RG_BUNNY_HOOD": "RAND_INF_CHILD_TRADES_HAS_MASK_BUNNY",
    "RG_GORON_MASK": "RAND_INF_CHILD_TRADES_HAS_MASK_GORON", "RG_ZORA_MASK": "RAND_INF_CHILD_TRADES_HAS_MASK_ZORA",
    "RG_GERUDO_MASK": "RAND_INF_CHILD_TRADES_HAS_MASK_GERUDO",
    "RG_MASK_OF_TRUTH": "RAND_INF_CHILD_TRADES_HAS_MASK_TRUTH",
    "RG_SKELETON_KEY": "RAND_INF_HAS_SKELETON_KEY", "RG_GREG_RUPEE": "RAND_INF_GREG_FOUND",
    "RG_SPEAK_DEKU": "RAND_INF_CAN_SPEAK_DEKU", "RG_SPEAK_GERUDO": "RAND_INF_CAN_SPEAK_GERUDO",
    "RG_SPEAK_GORON": "RAND_INF_CAN_SPEAK_GORON", "RG_SPEAK_HYLIAN": "RAND_INF_CAN_SPEAK_HYLIAN",
    "RG_SPEAK_KOKIRI": "RAND_INF_CAN_SPEAK_KOKIRI", "RG_SPEAK_ZORA": "RAND_INF_CAN_SPEAK_ZORA",
    "RG_FISHING_POLE": "RAND_INF_FISHING_POLE_FOUND", "RG_SCARECROWS_SONG": "RAND_INF_HAS_SCARECROWS_SONG",
    "RG_ROCS_FEATHER": "RAND_INF_OBTAINED_ROCS_FEATHER",
    "RG_GUARD_HOUSE_KEY": "RAND_INF_GUARD_HOUSE_KEY_OBTAINED", "RG_MARKET_BAZAAR_KEY":
        "RAND_INF_MARKET_BAZAAR_KEY_OBTAINED", "RG_MARKET_POTION_SHOP_KEY": "RAND_INF_MARKET_POTION_SHOP_KEY_OBTAINED",
    "RG_MASK_SHOP_KEY": "RAND_INF_MASK_SHOP_KEY_OBTAINED",
    "RG_MARKET_SHOOTING_GALLERY_KEY": "RAND_INF_MARKET_SHOOTING_GALLERY_KEY_OBTAINED",
    "RG_BOMBCHU_BOWLING_KEY": "RAND_INF_BOMBCHU_BOWLING_KEY_OBTAINED",
    "RG_TREASURE_CHEST_GAME_BUILDING_KEY": "RAND_INF_TREASURE_CHEST_GAME_BUILDING_KEY_OBTAINED",
    "RG_BOMBCHU_SHOP_KEY": "RAND_INF_BOMBCHU_SHOP_KEY_OBTAINED",
    "RG_RICHARDS_HOUSE_KEY": "RAND_INF_RICHARDS_HOUSE_KEY_OBTAINED",
    "RG_ALLEY_HOUSE_KEY": "RAND_INF_ALLEY_HOUSE_KEY_OBTAINED", "RG_KAK_BAZAAR_KEY": "RAND_INF_KAK_BAZAAR_KEY_OBTAINED",
    "RG_KAK_POTION_SHOP_KEY": "RAND_INF_KAK_POTION_SHOP_KEY_OBTAINED",
    "RG_BOSS_HOUSE_KEY": "RAND_INF_BOSS_HOUSE_KEY_OBTAINED",
    "RG_GRANNYS_POTION_SHOP_KEY": "RAND_INF_GRANNYS_POTION_SHOP_KEY_OBTAINED",
    "RG_SKULLTULA_HOUSE_KEY": "RAND_INF_SKULLTULA_HOUSE_KEY_OBTAINED",
    "RG_IMPAS_HOUSE_KEY": "RAND_INF_IMPAS_HOUSE_KEY_OBTAINED", "RG_WINDMILL_KEY": "RAND_INF_WINDMILL_KEY_OBTAINED",
    "RG_KAK_SHOOTING_GALLERY_KEY": "RAND_INF_KAK_SHOOTING_GALLERY_KEY_OBTAINED",
    "RG_DAMPES_HUT_KEY": "RAND_INF_DAMPES_HUT_KEY_OBTAINED", "RG_TALONS_HOUSE_KEY": "RAND_INF_TALONS_HOUSE_KEY_OBTAINED",
    "RG_STABLES_KEY": "RAND_INF_STABLES_KEY_OBTAINED", "RG_BACK_TOWER_KEY": "RAND_INF_BACK_TOWER_KEY_OBTAINED",
    "RG_HYLIA_LAB_KEY": "RAND_INF_HYLIA_LAB_KEY_OBTAINED", "RG_FISHING_HOLE_KEY": "RAND_INF_FISHING_HOLE_KEY_OBTAINED",
}

# logic.cpp dungeonSceneTable (RandoGetToDungeonScene)
RANDO_GET_TO_DUNGEON_SCENE = {
    "RG_FOREST_TEMPLE_SMALL_KEY": "SCENE_FOREST_TEMPLE", "RG_FIRE_TEMPLE_SMALL_KEY": "SCENE_FIRE_TEMPLE",
    "RG_WATER_TEMPLE_SMALL_KEY": "SCENE_WATER_TEMPLE", "RG_SPIRIT_TEMPLE_SMALL_KEY": "SCENE_SPIRIT_TEMPLE",
    "RG_SHADOW_TEMPLE_SMALL_KEY": "SCENE_SHADOW_TEMPLE", "RG_BOTTOM_OF_THE_WELL_SMALL_KEY": "SCENE_BOTTOM_OF_THE_WELL",
    "RG_GERUDO_TRAINING_GROUND_SMALL_KEY": "SCENE_GERUDO_TRAINING_GROUND",
    "RG_GERUDO_FORTRESS_SMALL_KEY": "SCENE_THIEVES_HIDEOUT", "RG_GANONS_CASTLE_SMALL_KEY": "SCENE_INSIDE_GANONS_CASTLE",
    "RG_FOREST_TEMPLE_KEY_RING": "SCENE_FOREST_TEMPLE", "RG_FIRE_TEMPLE_KEY_RING": "SCENE_FIRE_TEMPLE",
    "RG_WATER_TEMPLE_KEY_RING": "SCENE_WATER_TEMPLE", "RG_SPIRIT_TEMPLE_KEY_RING": "SCENE_SPIRIT_TEMPLE",
    "RG_SHADOW_TEMPLE_KEY_RING": "SCENE_SHADOW_TEMPLE", "RG_BOTTOM_OF_THE_WELL_KEY_RING": "SCENE_BOTTOM_OF_THE_WELL",
    "RG_GERUDO_TRAINING_GROUND_KEY_RING": "SCENE_GERUDO_TRAINING_GROUND",
    "RG_GERUDO_FORTRESS_KEY_RING": "SCENE_THIEVES_HIDEOUT", "RG_GANONS_CASTLE_KEY_RING": "SCENE_INSIDE_GANONS_CASTLE",
    "RG_FOREST_TEMPLE_BOSS_KEY": "SCENE_FOREST_TEMPLE", "RG_FIRE_TEMPLE_BOSS_KEY": "SCENE_FIRE_TEMPLE",
    "RG_WATER_TEMPLE_BOSS_KEY": "SCENE_WATER_TEMPLE", "RG_SPIRIT_TEMPLE_BOSS_KEY": "SCENE_SPIRIT_TEMPLE",
    "RG_SHADOW_TEMPLE_BOSS_KEY": "SCENE_SHADOW_TEMPLE", "RG_GANONS_CASTLE_BOSS_KEY": "SCENE_INSIDE_GANONS_CASTLE",
    "RG_DEKU_TREE_MAP": "SCENE_DEKU_TREE", "RG_DODONGOS_CAVERN_MAP": "SCENE_DODONGOS_CAVERN",
    "RG_JABU_JABUS_BELLY_MAP": "SCENE_JABU_JABU", "RG_FOREST_TEMPLE_MAP": "SCENE_FOREST_TEMPLE",
    "RG_FIRE_TEMPLE_MAP": "SCENE_FIRE_TEMPLE", "RG_WATER_TEMPLE_MAP": "SCENE_WATER_TEMPLE",
    "RG_SPIRIT_TEMPLE_MAP": "SCENE_SPIRIT_TEMPLE", "RG_SHADOW_TEMPLE_MAP": "SCENE_SHADOW_TEMPLE",
    "RG_BOTTOM_OF_THE_WELL_MAP": "SCENE_BOTTOM_OF_THE_WELL", "RG_ICE_CAVERN_MAP": "SCENE_ICE_CAVERN",
    "RG_DEKU_TREE_COMPASS": "SCENE_DEKU_TREE", "RG_DODONGOS_CAVERN_COMPASS": "SCENE_DODONGOS_CAVERN",
    "RG_JABU_JABUS_BELLY_COMPASS": "SCENE_JABU_JABU", "RG_FOREST_TEMPLE_COMPASS": "SCENE_FOREST_TEMPLE",
    "RG_FIRE_TEMPLE_COMPASS": "SCENE_FIRE_TEMPLE", "RG_WATER_TEMPLE_COMPASS": "SCENE_WATER_TEMPLE",
    "RG_SPIRIT_TEMPLE_COMPASS": "SCENE_SPIRIT_TEMPLE", "RG_SHADOW_TEMPLE_COMPASS": "SCENE_SHADOW_TEMPLE",
    "RG_BOTTOM_OF_THE_WELL_COMPASS": "SCENE_BOTTOM_OF_THE_WELL", "RG_ICE_CAVERN_COMPASS": "SCENE_ICE_CAVERN",
    "RG_TREASURE_GAME_SMALL_KEY": "SCENE_TREASURE_BOX_SHOP", "RG_TREASURE_GAME_KEY_RING": "SCENE_TREASURE_BOX_SHOP",
}

# logic.cpp questItemTable (RandoGetToQuestItem)
RANDO_GET_TO_QUEST_ITEM = {
    "RG_FOREST_MEDALLION": "QUEST_MEDALLION_FOREST", "RG_FIRE_MEDALLION": "QUEST_MEDALLION_FIRE",
    "RG_WATER_MEDALLION": "QUEST_MEDALLION_WATER", "RG_SPIRIT_MEDALLION": "QUEST_MEDALLION_SPIRIT",
    "RG_SHADOW_MEDALLION": "QUEST_MEDALLION_SHADOW", "RG_LIGHT_MEDALLION": "QUEST_MEDALLION_LIGHT",
    "RG_MINUET_OF_FOREST": "QUEST_SONG_MINUET", "RG_BOLERO_OF_FIRE": "QUEST_SONG_BOLERO",
    "RG_SERENADE_OF_WATER": "QUEST_SONG_SERENADE", "RG_REQUIEM_OF_SPIRIT": "QUEST_SONG_REQUIEM",
    "RG_NOCTURNE_OF_SHADOW": "QUEST_SONG_NOCTURNE", "RG_PRELUDE_OF_LIGHT": "QUEST_SONG_PRELUDE",
    "RG_ZELDAS_LULLABY": "QUEST_SONG_LULLABY", "RG_EPONAS_SONG": "QUEST_SONG_EPONA", "RG_SARIAS_SONG": "QUEST_SONG_SARIA",
    "RG_SUNS_SONG": "QUEST_SONG_SUN", "RG_SONG_OF_TIME": "QUEST_SONG_TIME", "RG_SONG_OF_STORMS": "QUEST_SONG_STORMS",
    "RG_KOKIRI_EMERALD": "QUEST_KOKIRI_EMERALD", "RG_GORON_RUBY": "QUEST_GORON_RUBY",
    "RG_ZORA_SAPPHIRE": "QUEST_ZORA_SAPPHIRE", "RG_STONE_OF_AGONY": "QUEST_STONE_OF_AGONY",
    "RG_GERUDO_MEMBERSHIP_CARD": "QUEST_GERUDO_CARD",
}

# logic.cpp BottleRandomizerGetToItemID
BOTTLE_RANDO_GET_TO_ITEM = {
    "RG_BOTTLE_WITH_RED_POTION": "ITEM_POTION_RED", "RG_BOTTLE_WITH_GREEN_POTION": "ITEM_POTION_GREEN",
    "RG_BOTTLE_WITH_BLUE_POTION": "ITEM_POTION_BLUE", "RG_BOTTLE_WITH_FAIRY": "ITEM_FAIRY",
    "RG_BOTTLE_WITH_FISH": "ITEM_FISH", "RG_BOTTLE_WITH_BLUE_FIRE": "ITEM_BLUE_FIRE", "RG_BOTTLE_WITH_BUGS": "ITEM_BUG",
    "RG_BOTTLE_WITH_POE": "ITEM_POE", "RG_BOTTLE_WITH_BIG_POE": "ITEM_BIG_POE",
}
HOOKSHOT_LOOKUP = ["ITEM_NONE", "ITEM_HOOKSHOT", "ITEM_LONGSHOT"]
OCARINA_LOOKUP = ["ITEM_NONE", "ITEM_OCARINA_FAIRY", "ITEM_OCARINA_TIME"]

# logic.cpp StaticData::restrictSpells / restrictTrade / allowMasks / allowBottleMaskTrade
RESTRICT_SPELLS = {"RG_FARORES_WIND", "RG_DINS_FIRE", "RG_NAYRUS_LOVE"}
RESTRICT_TRADE = {"RG_POCKET_EGG", "RG_COJIRO", "RG_ODD_MUSHROOM", "RG_ODD_POTION", "RG_POACHERS_SAW",
                  "RG_BROKEN_SWORD", "RG_PRESCRIPTION", "RG_EYEBALL_FROG", "RG_EYEDROPS", "RG_CLAIM_CHECK"}
ALLOW_MASKS = {"RG_KEATON_MASK", "RG_SKULL_MASK", "RG_SPOOKY_MASK", "RG_BUNNY_HOOD", "RG_GORON_MASK", "RG_ZORA_MASK",
               "RG_GERUDO_MASK", "RG_MASK_OF_TRUTH", "RG_WEIRD_EGG", "RG_ZELDAS_LETTER"}
ALLOW_BOTTLE_MASK_TRADE = ALLOW_MASKS | RESTRICT_TRADE | {
    "RG_EMPTY_BOTTLE", "RG_BOTTLE_WITH_MILK", "RG_BOTTLE_WITH_RED_POTION", "RG_BOTTLE_WITH_GREEN_POTION",
    "RG_BOTTLE_WITH_BLUE_POTION", "RG_BOTTLE_WITH_FAIRY", "RG_BOTTLE_WITH_FISH", "RG_BOTTLE_WITH_BLUE_FIRE",
    "RG_BOTTLE_WITH_BUGS", "RG_BOTTLE_WITH_POE", "RG_RUTOS_LETTER", "RG_BOTTLE_WITH_BIG_POE"}

# (EnemyDistance values: a switch (distance) with fallthrough runs every case at or after `distance`; the ports
#  write it `if d <= ED[case]` per case, in order)
ED = D.ENUMS["EnemyDistance"]


def _scene_of(rr):
    if rr == "RR_NONE":
        return "SCENE_ID_MAX"   # (areaTable[RR_NONE]: "Invalid Region", SCENE_ID_MAX)
    return R.REGIONS[rr]["scene"]


# ---- the save context

class SaveContext:
    """the SaveContext fields the Logic touches (Logic::InitSaveContext values)"""

    def __init__(self):
        self.items = ["ITEM_NONE"] * 24          # (inventory.items by InventorySlot, SLOT_STICK..SLOT_TRADE_CHILD)
        self.ammo = [0] * 16
        self.equipment = 0
        self.upgrades = 0
        self.questItems = 0
        self.dungeonItems = {}                   # (scene: bits)
        self.dungeonKeys = {}                    # (scene: count)
        self.gsTokens = 0
        self.healthCapacity = 0x30
        self.health = 0x30
        self.magicLevel = 0
        self.isMagicAcquired = 0
        self.isDoubleMagicAcquired = 0
        self.isDoubleDefenseAcquired = 0
        self.bgsFlag = 0
        self.randomizerInf = set()
        self.eventChkInf = set()
        self.triforcePiecesCollected = 0
        self.linkAge = 0
        # (sceneFlags: all 0 but SCENE_WATER_TEMPLE swch 0x40000000; only BeanPlanted and the small key door counts
        #  read them, see there)
        self.sceneSwch = {"SCENE_WATER_TEMPLE": 0x40000000}


class Logic:
    def __init__(self, ctx=None):
        self.ctx = ctx or Ctx()
        self.Bottles = 0
        self.NumBottles = 0
        self.IsChild = False
        self.IsAdult = False
        self.BigPoes = 0
        self.BaseHearts = 0
        self.AtDay = False
        self.AtNight = False
        self.CurrentRegionKey = "RR_NONE"
        self.CurrentCheckKey = "RC_UNKNOWN_CHECK"
        self.CalculatingAvailableChecks = False
        self.ACProcessUndiscoveredExits = False
        self.mSaveContext = None
        self.inLogic = set()
        self.PlacedItem = lambda rc: "RG_NONE"   # (the item placed at a location: set by the search)
        self.Reset()

    # ---- HasItem / ItemUseAllowed / CanUse

    def HasItem(self, itemName):
        ctx = self.ctx
        i = itemName
        if i == "RG_FAIRY_OCARINA":
            return self.CheckInventory("ITEM_OCARINA_FAIRY", False)
        if i == "RG_OCARINA_OF_TIME":
            return self.CheckInventory("ITEM_OCARINA_TIME", True)
        if i in _HAS_EXACT:
            return self.CheckInventory(_HAS_EXACT[i], True)
        if i == "RG_HOOKSHOT":
            return self.CheckInventory("ITEM_HOOKSHOT", False)
        if i in ("RG_PROGRESSIVE_STICK_UPGRADE", "RG_STICKS"):
            return bool(self.CurrentUpgrade("UPG_STICKS"))
        if i in ("RG_PROGRESSIVE_BOMBCHU_BAG", "RG_BOMBCHU_5", "RG_BOMBCHU_10", "RG_BOMBCHU_20"):
            return (self.BombchusEnabled() and (self.Get("LOGIC_BUY_BOMBCHUS") or self.Get("LOGIC_COULD_PLAY_BOWLING")
                                                or self.Get("LOGIC_CARPET_MERCHANT"))) \
                or self.CheckInventory("ITEM_BOMBCHU", True)
        if i in ("RG_PROGRESSIVE_NUT_UPGRADE", "RG_NUTS"):
            return bool(self.CurrentUpgrade("UPG_NUTS"))
        if i == "RG_MAGIC_BEAN":
            return self.GetAmmo("ITEM_BEAN") > 0 or self.CheckInventory("ITEM_BEAN", True)
        if i in ("RG_KOKIRI_SWORD", "RG_DEKU_SHIELD", "RG_GORON_TUNIC", "RG_ZORA_TUNIC", "RG_HYLIAN_SHIELD",
                 "RG_MIRROR_SHIELD", "RG_MASTER_SWORD", "RG_IRON_BOOTS", "RG_HOVER_BOOTS"):
            return self.CheckEquipment(RANDO_GET_TO_EQUIP_FLAG[i])
        if i in ("RG_PROGRESSIVE_GORONSWORD", "RG_GIANTS_KNIFE"):
            # (progressive leaves Medigoron replacing broken knives, so the first one has to be found)
            return self.CheckEquipment("EQUIP_FLAG_SWORD_BGS") or \
                (not ctx.GetOption("RSK_PROGRESSIVE_GORON_SWORD") and self.Get("LOGIC_MEDIGORON"))
        if i == "RG_BIGGORON_SWORD":
            return self.CheckEquipment("EQUIP_FLAG_SWORD_BGS") and bool(self.mSaveContext.bgsFlag)
        if i == "RG_GORONS_BRACELET":
            return bool(self.CurrentUpgrade("UPG_STRENGTH"))
        if i == "RG_SILVER_GAUNTLETS":
            return self.CurrentUpgrade("UPG_STRENGTH") >= 2
        if i == "RG_GOLDEN_GAUNTLETS":
            return self.CurrentUpgrade("UPG_STRENGTH") >= 3
        if i in ("RG_PROGRESSIVE_BOMB_BAG", "RG_BOMB_BAG"):
            return bool(self.CurrentUpgrade("UPG_BOMB_BAG"))
        if i == "RG_MAGIC_SINGLE":
            return self.GetSaveContext().magicLevel >= 1 or bool(self.GetSaveContext().isMagicAcquired)
        if i in _HAS_QUEST:
            return self.CheckQuestItem(RANDO_GET_TO_QUEST_ITEM[i])
        if i == "RG_DOUBLE_DEFENSE":
            return bool(self.GetSaveContext().isDoubleDefenseAcquired)
        if i == "RG_KEATON_MASK":
            return self.CheckRandoInf("RAND_INF_CHILD_TRADES_HAS_MASK_KEATON") or \
                (not ctx.GetOption("RSK_SHUFFLE_MASKS") and self.Get("LOGIC_CAN_BORROW_MASKS"))
        if i == "RG_SKULL_MASK":
            return self.CheckRandoInf("RAND_INF_CHILD_TRADES_HAS_MASK_SKULL") or \
                (not ctx.GetOption("RSK_SHUFFLE_MASKS") and self.Get("LOGIC_CAN_BORROW_MASKS")
                 and self.Get("LOGIC_SOLD_KEATON_MASK"))
        if i == "RG_SPOOKY_MASK":
            return self.CheckRandoInf("RAND_INF_CHILD_TRADES_HAS_MASK_SPOOKY") or \
                (not ctx.GetOption("RSK_SHUFFLE_MASKS") and self.Get("LOGIC_CAN_BORROW_MASKS")
                 and self.Get("LOGIC_SOLD_SKULL_MASK"))
        if i == "RG_BUNNY_HOOD":
            return self.CheckRandoInf("RAND_INF_CHILD_TRADES_HAS_MASK_BUNNY") or \
                (not ctx.GetOption("RSK_SHUFFLE_MASKS") and self.Get("LOGIC_CAN_BORROW_MASKS")
                 and self.Get("LOGIC_SOLD_SPOOKY_MASK"))
        if i == "RG_MASK_OF_TRUTH":
            return self.CheckRandoInf("RAND_INF_CHILD_TRADES_HAS_MASK_TRUTH") or \
                (not ctx.GetOption("RSK_SHUFFLE_MASKS") and self.Get("LOGIC_CAN_BORROW_MASKS")
                 and self.Get("LOGIC_SOLD_KEATON_MASK") and self.Get("LOGIC_SOLD_SKULL_MASK")
                 and self.Get("LOGIC_SOLD_SPOOKY_MASK") and self.Get("LOGIC_SOLD_BUNNY_HOOD"))
        if i in _HAS_RAND_INF:
            return self.CheckRandoInf(RANDO_GET_TO_RAND_INF[i])
        if i in _BOSS_SOULS:
            return not ctx.GetOption("RSK_SHUFFLE_BOSS_SOULS") or self.CheckRandoInf(RANDO_GET_TO_RAND_INF[i])
        if i == "RG_GANON_SOUL":
            return ctx.GetOption("RSK_GANONS_SOUL").Is("RO_GANONS_SOUL_STARTWITH") or \
                self.CheckRandoInf(RANDO_GET_TO_RAND_INF[i])
        if i in _OVERWORLD_KEYS:
            return not ctx.GetOption("RSK_LOCK_OVERWORLD_DOORS") or self.HasItem("RG_SKELETON_KEY") or \
                self.CheckRandoInf(RANDO_GET_TO_RAND_INF[i])
        if i in _BOSS_KEYS:
            return self.CheckDungeonItem("DUNGEON_KEY_BOSS", RANDO_GET_TO_DUNGEON_SCENE[i])
        if i in _MAPS:
            return self.CheckDungeonItem("DUNGEON_MAP", RANDO_GET_TO_DUNGEON_SCENE[i])
        if i in _COMPASSES:
            return self.CheckDungeonItem("DUNGEON_COMPASS", RANDO_GET_TO_DUNGEON_SCENE[i])
        if i == "RG_ADULT_WALLET":
            return self.CurrentUpgrade("UPG_WALLET") >= 1
        if i == "RG_GIANT_WALLET":
            return self.CurrentUpgrade("UPG_WALLET") >= 2
        if i == "RG_TYCOON_WALLET":
            return self.CurrentUpgrade("UPG_WALLET") >= 3
        if i == "RG_SILVER_SCALE":
            return self.CurrentUpgrade("UPG_SCALE") >= 1
        if i == "RG_GOLDEN_SCALE":
            return self.CurrentUpgrade("UPG_SCALE") >= 2
        if i in _SILVER_RUPEES:
            if not ctx.GetOption("RSK_SHUFFLE_SILVER"):
                # (LOGIC_SHADOW_SILVER_BLADES + (itemName - RG_SHADOW_SILVER_BLADES))
                return self.Get(_SILVER_LOGIC[i])
            if ctx.GetOption("RSK_SHUFFLE_SILVER").Is("RO_SHUFFLE_SILVER_STARTWITH"):
                return True
            raise LogicError("shuffled silver rupees are not ported (SilverFieldFromSaveContext)")
        if i == "RG_POCKET_EGG":
            return self.CheckRandoInf("RAND_INF_ADULT_TRADES_HAS_POCKET_EGG") or \
                self.CheckRandoInf("RAND_INF_ADULT_TRADES_HAS_POCKET_CUCCO")
        if i in _BOTTLES:
            return self.HasBottle()
        # (SoH: SPDLOG_ERROR + assert(false), return false; an unported case here is a port bug: say so)
        raise LogicError(f"HasItem: missing case for {itemName}")

    def ItemUseAllowed(self, itemName):
        """(based on sRestrictionFlags in z_parameter.c)"""
        if itemName in ("RG_KOKIRI_SWORD", "RG_MASTER_SWORD", "RG_PROGRESSIVE_GORONSWORD", "RG_GIANTS_KNIFE",
                        "RG_BIGGORON_SWORD"):
            return self.BAllowed()
        if itemName in _USE_ALWAYS:
            return True
        # (hacky fix for underwater sections TODO this properly with a flag in regions)
        if self.CurrentRegionKey == "RR_LH_LAB_UNDERWATER":
            return itemName in ("RG_HOOKSHOT", "RG_LONGSHOT")
        scene = _scene_of(self.CurrentRegionKey)
        if scene in _SCENES_ANY:
            return True
        if scene in _SCENES_NO_FW:
            return not (itemName == "RG_FARORES_WIND")
        if scene in ("SCENE_GANONS_TOWER_COLLAPSE_INTERIOR", "SCENE_INSIDE_GANONS_CASTLE_COLLAPSE",
                     "SCENE_GANONS_TOWER_COLLAPSE_EXTERIOR"):
            return not (itemName in ("RG_FARORES_WIND", "RG_FAIRY_OCARINA", "RG_OCARINA_OF_TIME"))
        if scene == "SCENE_CASTLE_COURTYARD_ZELDA":
            return not (itemName in RESTRICT_SPELLS or itemName in ("RG_FAIRY_OCARINA", "RG_OCARINA_OF_TIME"))
        if scene in _SCENES_BOSS:
            return not (itemName in RESTRICT_TRADE or itemName in ("RG_FARORES_WIND", "RG_FAIRY_OCARINA",
                                                                    "RG_OCARINA_OF_TIME"))
        if scene == "SCENE_WINDMILL_AND_DAMPES_GRAVE":
            return not (itemName in RESTRICT_SPELLS)
        if scene == "SCENE_MARKET_GUARD_HOUSE":
            return not (itemName in RESTRICT_SPELLS or itemName in ("RG_HOOKSHOT", "RG_LONGSHOT"))
        if scene in _SCENES_TOWN:
            return itemName in ALLOW_BOTTLE_MASK_TRADE or itemName in ("RG_FAIRY_OCARINA", "RG_OCARINA_OF_TIME")
        if scene == "SCENE_TREASURE_BOX_SHOP":
            return itemName in ALLOW_BOTTLE_MASK_TRADE or itemName == "RG_LENS_OF_TRUTH"
        if scene == "SCENE_POTION_SHOP_GRANNY":
            return itemName in ALLOW_BOTTLE_MASK_TRADE
        if scene in ("SCENE_SHOOTING_GALLERY", "SCENE_CASTLE_COURTYARD_GUARDS_DAY",
                     "SCENE_CASTLE_COURTYARD_GUARDS_NIGHT", "SCENE_BOMBCHU_BOWLING_ALLEY"):
            return itemName in ALLOW_MASKS
        if scene == "SCENE_FISHING_POND":
            return itemName == "RG_FISHING_POLE"
        return True   # (SoH: SPDLOG_INFO, return true)

    def BAllowed(self):
        if self.CurrentRegionKey == "RR_LH_LAB_UNDERWATER":
            return False
        return _scene_of(self.CurrentRegionKey) not in _SCENES_NO_B

    def CanUse(self, itemName):
        if not self.HasItem(itemName):
            return False
        if not self.ItemUseAllowed(itemName):
            return False
        i = itemName
        if i == "RG_MAGIC_SINGLE":
            return True   # (AmmoCanDrop || (HasBottle() && Get(LOGIC_BUY_MAGIC_POTION)))
        if i in ("RG_DINS_FIRE", "RG_FARORES_WIND", "RG_LENS_OF_TRUTH"):
            return self.CanUse("RG_MAGIC_SINGLE")
        if i == "RG_NAYRUS_LOVE":
            if self.ctx.GetOption("RSK_NAYRUS_LOVE_USES").Get() > 0:
                return False
            return self.CanUse("RG_MAGIC_SINGLE")
        if i in ("RG_FIRE_ARROWS", "RG_ICE_ARROWS", "RG_LIGHT_ARROWS"):
            return self.CanUse("RG_MAGIC_SINGLE") and self.CanUse("RG_FAIRY_BOW")
        if i in _ADULT_ITEMS:
            return self.IsAdult
        if i in ("RG_FAIRY_SLINGSHOT", "RG_BOOMERANG", "RG_KOKIRI_SWORD", "RG_DEKU_SHIELD", "RG_WEIRD_EGG",
                 "RG_RUTOS_LETTER", "RG_MAGIC_BEAN", "RG_CRAWL"):
            return self.IsChild
        if i == "RG_NUTS":
            return self.Get("LOGIC_NUT_ACCESS")
        if i == "RG_STICKS":
            return self.IsChild and self.Get("LOGIC_STICK_ACCESS")
        if i in ("RG_PROGRESSIVE_BOMB_BAG", "RG_BOMB_BAG"):
            # (AmmoCanDrop || Get(LOGIC_BUY_BOMB)): true in SoH. (The remake's bombs need the Goron's Bracelet's lift grade;
            # HookshotRando's mod gives them the free grade, rando.patches.free_bomb_lift, so the bag alone is enough, as in SoH.)
            return True
        if i in ("RG_PROGRESSIVE_BOMBCHU_BAG", "RG_BOMBCHU_5", "RG_BOMBCHU_10", "RG_BOMBCHU_20"):
            return self.BombchuRefill() and self.BombchusEnabled()
        if i in ("RG_SKULL_MASK", "RG_MASK_OF_TRUTH", "RG_BUNNY_HOOD"):
            return self.IsChild or bool(self.ctx.GetOption("RSK_MASKS_AS_ADULT"))
        H = self.HasItem
        if i in ("RG_ZELDAS_LULLABY", "RG_EPONAS_SONG", "RG_PRELUDE_OF_LIGHT"):
            return self.CanUse("RG_FAIRY_OCARINA") and H("RG_OCARINA_C_LEFT_BUTTON") and \
                H("RG_OCARINA_C_RIGHT_BUTTON") and H("RG_OCARINA_C_UP_BUTTON")
        if i == "RG_SARIAS_SONG":
            return self.CanUse("RG_FAIRY_OCARINA") and H("RG_OCARINA_C_LEFT_BUTTON") and \
                H("RG_OCARINA_C_RIGHT_BUTTON") and H("RG_OCARINA_C_DOWN_BUTTON")
        if i == "RG_SUNS_SONG":
            return self.CanUse("RG_FAIRY_OCARINA") and H("RG_OCARINA_C_RIGHT_BUTTON") and \
                H("RG_OCARINA_C_UP_BUTTON") and H("RG_OCARINA_C_DOWN_BUTTON")
        if i in ("RG_SONG_OF_TIME", "RG_BOLERO_OF_FIRE", "RG_REQUIEM_OF_SPIRIT"):
            return self.CanUse("RG_FAIRY_OCARINA") and H("RG_OCARINA_A_BUTTON") and \
                H("RG_OCARINA_C_RIGHT_BUTTON") and H("RG_OCARINA_C_DOWN_BUTTON")
        if i == "RG_SONG_OF_STORMS":
            # (SoH checks HasItem, not CanUse, of the ocarina here)
            return H("RG_FAIRY_OCARINA") and H("RG_OCARINA_A_BUTTON") and H("RG_OCARINA_C_UP_BUTTON") and \
                H("RG_OCARINA_C_DOWN_BUTTON")
        if i == "RG_MINUET_OF_FOREST":
            return self.CanUse("RG_FAIRY_OCARINA") and H("RG_OCARINA_A_BUTTON") and \
                H("RG_OCARINA_C_LEFT_BUTTON") and H("RG_OCARINA_C_RIGHT_BUTTON") and H("RG_OCARINA_C_UP_BUTTON")
        if i in ("RG_SERENADE_OF_WATER", "RG_NOCTURNE_OF_SHADOW"):
            return self.CanUse("RG_FAIRY_OCARINA") and H("RG_OCARINA_A_BUTTON") and \
                H("RG_OCARINA_C_LEFT_BUTTON") and H("RG_OCARINA_C_RIGHT_BUTTON") and H("RG_OCARINA_C_DOWN_BUTTON")
        if i == "RG_FISHING_POLE":
            return H("RG_CHILD_WALLET")   # (as long as you have enough rupees)
        if i == "RG_BOTTLE_WITH_BUGS":
            return self.Get("LOGIC_BUG_ACCESS")
        if i == "RG_BOTTLE_WITH_FISH":
            return self.Get("LOGIC_FISH_ACCESS")
        if i == "RG_BOTTLE_WITH_BLUE_FIRE":
            return self.Get("LOGIC_BLUE_FIRE_ACCESS")
        if i == "RG_BOTTLE_WITH_FAIRY":
            return self.Get("LOGIC_FAIRY_ACCESS")
        if i in ("RG_FAIRY_OCARINA", "RG_OCARINA_OF_TIME"):
            return True
        return True   # (SoH default: SPDLOG_INFO "using HasItem is a minor Optimisation", return true)

    def HasProjectile(self, age):
        # (age: HasProjectileAge::Adult/Child/Both/Either as "Adult" etc.)
        return self.HasExplosives() or \
            (age == "Child" and (self.CanUse("RG_FAIRY_SLINGSHOT") or self.CanUse("RG_BOOMERANG"))) or \
            (age == "Adult" and (self.CanUse("RG_HOOKSHOT") or self.CanUse("RG_FAIRY_BOW"))) or \
            (age == "Both" and (self.CanUse("RG_FAIRY_SLINGSHOT") or self.CanUse("RG_BOOMERANG"))
             and (self.CanUse("RG_HOOKSHOT") or self.CanUse("RG_FAIRY_BOW"))) or \
            (age == "Either" and (self.CanUse("RG_FAIRY_SLINGSHOT") or self.CanUse("RG_BOOMERANG")
                                  or self.CanUse("RG_HOOKSHOT") or self.CanUse("RG_FAIRY_BOW")))

    # ---- movement tech (all need tricks: off)

    def CanGroundJump(self, hasBombflower=False):
        return bool(self.ctx.GetTrickOption("RT_GROUND_JUMP")) and self.CanStandingShield() and \
            (self.CanUse("RG_BOMB_BAG") or (hasBombflower and self.HasItem("RG_GORONS_BRACELET")))

    def CanGroundJumpslash(self, hasBombflower=False):
        return bool(self.ctx.GetTrickOption("RT_GROUND_JUMP_HARD")) and self.CanStandingShield() and \
            self.CanJumpslash() and (self.CanUse("RG_BOMB_BAG") or (hasBombflower and self.HasItem("RG_GORONS_BRACELET")))

    def CanMidairGroundJump(self, hasBombflower=False):
        return bool(self.ctx.GetTrickOption("RT_GROUND_JUMP_HARD")) and self.CanStandingShield() and \
            self.CanUse("RG_HOVER_BOOTS") and \
            (self.CanUse("RG_BOMB_BAG") or (hasBombflower and self.HasItem("RG_GORONS_BRACELET")))

    def CanMegajump(self, needsBunny=False, hasBombflower=False):
        T = self.ctx.GetTrickOption
        return bool(T("RT_DAMAGE_BOOST_SIMPLE")) and self.TakeDamage("DAMAGE_NO_FAIRY") and \
            (self.BunnyHood() or (not needsBunny and bool(T("RT_HOVER_BOOST_SIMPLE")) and self.CanUse("RG_HOVER_BOOTS"))) \
            and (self.HasExplosives() or (hasBombflower and self.HasItem("RG_GORONS_BRACELET")))

    def CanBunnyMegaJumpslash(self, hasBombflower=False):
        return bool(self.ctx.GetTrickOption("RT_DAMAGE_BOOST_SIMPLE")) and self.TakeDamage("DAMAGE_NO_FAIRY") and \
            self.BunnyHood() and self.CanUse("RG_HOVER_BOOTS") and self.CanJumpslash() and \
            (self.HasExplosives() or (hasBombflower and self.HasItem("RG_GORONS_BRACELET")))

    def CanMegadive(self, fallDamage=True, hasBombflower=False):
        return bool(self.ctx.GetTrickOption("RT_DAMAGE_BOOST_SIMPLE")) and \
            (self.HasExplosives() or (hasBombflower and self.HasItem("RG_GORONS_BRACELET"))) and \
            (self.EffectiveHealth() > 16 or self.CanUse("RG_NAYRUS_LOVE") or
             (self.EffectiveHealth() > 8 and (fallDamage or self.CanUse("RG_BOTTLE_WITH_FAIRY"))))

    def CanMidairDamageBoost(self, hasBombflower=False):
        return bool(self.ctx.GetTrickOption("RT_DAMAGE_BOOST_SIMPLE")) and self.CanJumpslash() and \
            self.TakeDamage("DAMAGE_NO_FAIRY") and \
            (self.CanUse("RG_BOMBCHU_5") or (self.CanStandingShield() and
                                            (self.CanUse("RG_BOMB_BAG") or
                                             (hasBombflower and self.HasItem("RG_GORONS_BRACELET")))))

    def CanOpenUnderwaterChest(self):
        return bool(self.ctx.GetTrickOption("RT_OPEN_UNDERWATER_CHEST")) and self.CanUse("RG_IRON_BOOTS") and \
            self.CanUse("RG_HOOKSHOT") and self.HasItem("RG_OPEN_CHEST")

    def CanOpenLargeChest(self):
        return self.CheckRandoInf("RAND_INF_CAN_OPEN_LARGE_CHEST")

    def CanEquipSwap(self, itemName):
        if not self.HasItem(itemName):
            return False
        if self.CanDoGlitch("EquipSwapDins") or self.CanDoGlitch("EquipSwap"):
            return True
        return False

    def CanDoGlitch(self, glitch):
        # (SoH: every glitch case ends in `&& false`)
        return False

    # ---- enemies

    def CanKillEnemy(self, enemy, distance="ED_CLOSE", wallOrFloor=True, quantity=1, timer=False, inWater=False):
        U = self.CanUse
        d = ED[distance]
        e = enemy
        if e in ("RE_GERUDO_GUARD", "RE_BREAK_ROOM_GUARD"):
            return False
        if e == "RE_GOLD_SKULLTULA":
            killed = False
            # (switch fallthrough: each case adds its weapons and falls to the farther ones)
            if d <= ED["ED_CLOSE"]:
                killed = U("RG_MEGATON_HAMMER")   # (hammer jumpslash cannot damage these, but hammer swing can)
            if d <= ED["ED_SHORT_JUMPSLASH"]:
                killed = killed or U("RG_KOKIRI_SWORD")
            if d <= ED["ED_MASTER_SWORD_JUMPSLASH"]:
                killed = killed or U("RG_MASTER_SWORD")
            if d <= ED["ED_LONG_JUMPSLASH"]:
                killed = killed or U("RG_BIGGORON_SWORD") or U("RG_STICKS")
            if d <= ED["ED_BOMB_THROW"]:
                killed = killed or U("RG_BOMB_BAG")
            if d <= ED["ED_BOOMERANG"]:
                killed = killed or U("RG_BOOMERANG") or U("RG_DINS_FIRE")
            if d <= ED["ED_HOOKSHOT"]:
                killed = killed or U("RG_HOOKSHOT")
            if d <= ED["ED_LONGSHOT"]:
                killed = killed or U("RG_LONGSHOT") or (wallOrFloor and U("RG_BOMBCHU_5"))
            if d <= ED["ED_FAR"]:
                killed = killed or U("RG_FAIRY_SLINGSHOT") or U("RG_FAIRY_BOW")
            return killed
        if e in ("RE_GOHMA_LARVA", "RE_MAD_SCRUB", "RE_DEKU_BABA", "RE_POE"):
            return self.CanAttack()
        if e == "RE_BIG_SKULLTULA":
            killed = False
            if d <= ED["ED_CLOSE"]:
                killed = U("RG_MEGATON_HAMMER")
            if d <= ED["ED_SHORT_JUMPSLASH"]:
                killed = killed or U("RG_KOKIRI_SWORD")
            if d <= ED["ED_MASTER_SWORD_JUMPSLASH"]:
                killed = killed or U("RG_MASTER_SWORD")
            if d <= ED["ED_LONG_JUMPSLASH"]:
                killed = killed or U("RG_BIGGORON_SWORD") or U("RG_STICKS")
            if d <= ED["ED_BOMB_THROW"]:
                killed = killed or U("RG_BOMB_BAG") or U("RG_DINS_FIRE")
            if d <= ED["ED_HOOKSHOT"]:   # (case ED_BOOMERANG: case ED_HOOKSHOT:)
                killed = killed or U("RG_HOOKSHOT") or (wallOrFloor and U("RG_BOMBCHU_5"))
            if d <= ED["ED_LONGSHOT"]:
                killed = killed or U("RG_LONGSHOT")
            if d <= ED["ED_FAR"]:
                killed = killed or U("RG_FAIRY_SLINGSHOT") or U("RG_FAIRY_BOW")
            return killed
        if e == "RE_DODONGO":
            return self.CanUseSword() or U("RG_MEGATON_HAMMER") or (quantity <= 5 and U("RG_STICKS")) or \
                self.HasExplosives() or U("RG_FAIRY_SLINGSHOT") or U("RG_FAIRY_BOW")
        if e == "RE_LIZALFOS":
            return self.CanJumpslash() or self.HasExplosives() or U("RG_FAIRY_SLINGSHOT") or U("RG_FAIRY_BOW")
        if e in ("RE_KEESE", "RE_FIRE_KEESE", "RE_GUAY"):
            killed = False
            if d <= ED["ED_SHORT_JUMPSLASH"]:   # (case ED_CLOSE: case ED_SHORT_JUMPSLASH:)
                killed = U("RG_MEGATON_HAMMER") or U("RG_KOKIRI_SWORD")
            if d <= ED["ED_MASTER_SWORD_JUMPSLASH"]:
                killed = killed or U("RG_MASTER_SWORD")
            if d <= ED["ED_LONG_JUMPSLASH"]:
                killed = killed or U("RG_BIGGORON_SWORD") or U("RG_STICKS")
            if d <= ED["ED_BOMB_THROW"]:
                killed = killed or (not inWater and U("RG_BOMB_BAG")) or (e == "RE_GUAY" and U("RG_DINS_FIRE"))
            if d <= ED["ED_BOOMERANG"]:
                killed = killed or U("RG_BOOMERANG")
            if d <= ED["ED_HOOKSHOT"]:
                killed = killed or U("RG_HOOKSHOT") or (wallOrFloor and U("RG_BOMBCHU_5"))
            if d <= ED["ED_LONGSHOT"]:
                killed = killed or U("RG_LONGSHOT")
            if d <= ED["ED_FAR"]:
                killed = killed or U("RG_FAIRY_SLINGSHOT") or U("RG_FAIRY_BOW")
            return killed
        if e == "RE_BLUE_BUBBLE":
            return self.BlastOrSmash() or U("RG_FAIRY_BOW") or \
                ((self.CanJumpslashExceptHammer() or U("RG_FAIRY_SLINGSHOT")) and
                 (U("RG_NUTS") or self.HookshotOrBoomerang() or self.CanStandingShield()))
        if e == "RE_DEAD_HAND":
            return self.CanUseSword() or (U("RG_STICKS") and bool(self.ctx.GetTrickOption("RT_BOTW_CHILD_DEADHAND")))
        if e == "RE_WITHERED_DEKU_BABA":
            return self.CanUseSword() or U("RG_BOOMERANG")
        if e in ("RE_LIKE_LIKE", "RE_FLOORMASTER"):
            return self.CanDamage()
        if e == "RE_STALFOS":
            killed = False
            if d <= ED["ED_SHORT_JUMPSLASH"]:
                killed = U("RG_MEGATON_HAMMER") or U("RG_KOKIRI_SWORD")
            if d <= ED["ED_MASTER_SWORD_JUMPSLASH"]:
                killed = killed or U("RG_MASTER_SWORD")
            if d <= ED["ED_LONG_JUMPSLASH"]:
                killed = killed or U("RG_BIGGORON_SWORD") or (quantity <= 1 and U("RG_STICKS"))
            if d <= ED["ED_BOMB_THROW"]:
                killed = killed or (quantity <= 2 and not timer and not inWater and
                                    (U("RG_NUTS") or self.HookshotOrBoomerang()) and U("RG_BOMB_BAG"))
            if d <= ED["ED_HOOKSHOT"]:   # (case ED_BOOMERANG: case ED_HOOKSHOT:)
                killed = killed or (wallOrFloor and U("RG_BOMBCHU_5"))
            if d <= ED["ED_FAR"]:   # (case ED_LONGSHOT: case ED_FAR:)
                killed = killed or U("RG_FAIRY_BOW")
            return killed
        if e == "RE_IRON_KNUCKLE":
            return self.CanUseSword() or U("RG_MEGATON_HAMMER") or self.HasExplosives()
        if e == "RE_FLARE_DANCER":
            return U("RG_MEGATON_HAMMER") or U("RG_HOOKSHOT") or \
                (self.HasExplosives() and (self.CanJumpslashExceptHammer() or U("RG_FAIRY_BOW") or
                                           U("RG_FAIRY_SLINGSHOT") or U("RG_BOOMERANG")))
        if e in ("RE_WOLFOS", "RE_WHITE_WOLFOS", "RE_WALLMASTER"):
            return self.CanJumpslash() or U("RG_FAIRY_BOW") or U("RG_FAIRY_SLINGSHOT") or U("RG_BOMBCHU_5") or \
                U("RG_DINS_FIRE") or (U("RG_BOMB_BAG") and (U("RG_NUTS") or U("RG_HOOKSHOT") or U("RG_BOOMERANG")))
        if e == "RE_GERUDO_WARRIOR":
            return self.CanJumpslash() or U("RG_FAIRY_BOW") or \
                (bool(self.ctx.GetTrickOption("RT_GF_WARRIOR_WITH_DIFFICULT_WEAPON")) and
                 (U("RG_FAIRY_SLINGSHOT") or U("RG_BOMBCHU_5")))
        if e in ("RE_GIBDO", "RE_REDEAD"):
            return self.CanJumpslash() or U("RG_DINS_FIRE")
        if e == "RE_MEG":
            return U("RG_FAIRY_BOW") or U("RG_HOOKSHOT") or self.HasExplosives()
        if e == "RE_ARMOS":
            return self.BlastOrSmash() or U("RG_MASTER_SWORD") or U("RG_BIGGORON_SWORD") or U("RG_STICKS") or \
                U("RG_FAIRY_BOW") or ((U("RG_NUTS") or U("RG_HOOKSHOT") or U("RG_BOOMERANG")) and
                                      (U("RG_KOKIRI_SWORD") or U("RG_FAIRY_SLINGSHOT")))
        if e == "RE_GREEN_BUBBLE":
            return self.CanJumpslash() or U("RG_FAIRY_BOW") or U("RG_FAIRY_SLINGSHOT") or self.HasExplosives()
        if e == "RE_DINOLFOS":
            return self.CanJumpslash() or U("RG_FAIRY_BOW") or U("RG_FAIRY_SLINGSHOT") or \
                (not timer and U("RG_BOMBCHU_5"))
        if e == "RE_TORCH_SLUG":
            return self.CanJumpslash() or self.HasExplosives() or U("RG_FAIRY_BOW")
        if e == "RE_FREEZARD":
            return U("RG_MASTER_SWORD") or U("RG_BIGGORON_SWORD") or U("RG_MEGATON_HAMMER") or U("RG_STICKS") or \
                self.HasExplosives() or U("RG_HOOKSHOT") or U("RG_DINS_FIRE") or U("RG_FIRE_ARROWS")
        if e == "RE_SHELL_BLADE":
            return self.CanJumpslash() or self.HasExplosives() or U("RG_HOOKSHOT") or U("RG_FAIRY_BOW") or \
                U("RG_DINS_FIRE")
        if e == "RE_SPIKE":
            return U("RG_MASTER_SWORD") or U("RG_BIGGORON_SWORD") or U("RG_MEGATON_HAMMER") or U("RG_STICKS") or \
                self.HasExplosives() or U("RG_HOOKSHOT") or U("RG_FAIRY_BOW") or U("RG_DINS_FIRE")
        if e == "RE_STINGER":
            killed = False
            if d <= ED["ED_SHORT_JUMPSLASH"]:
                killed = U("RG_MEGATON_HAMMER") or U("RG_KOKIRI_SWORD")
            if d <= ED["ED_MASTER_SWORD_JUMPSLASH"]:
                killed = killed or U("RG_MASTER_SWORD")
            if d <= ED["ED_LONG_JUMPSLASH"]:
                killed = killed or U("RG_BIGGORON_SWORD") or U("RG_STICKS")
            if d <= ED["ED_BOMB_THROW"]:
                killed = killed or (not inWater and U("RG_BOMB_BAG"))
            if d <= ED["ED_HOOKSHOT"]:   # (case ED_BOOMERANG: case ED_HOOKSHOT:)
                killed = killed or U("RG_HOOKSHOT") or (wallOrFloor and U("RG_BOMBCHU_5"))
            if d <= ED["ED_LONGSHOT"]:
                killed = killed or U("RG_LONGSHOT")
            if d <= ED["ED_FAR"]:
                killed = killed or U("RG_FAIRY_SLINGSHOT") or U("RG_FAIRY_BOW")
            return killed
        if e == "RE_BIG_OCTO":
            return U("RG_KOKIRI_SWORD") or U("RG_STICKS") or U("RG_MASTER_SWORD")
        if e == "RE_GOHMA":
            return self.HasItem("RG_GOHMA_SOUL") and self.CanJumpslash() and \
                (U("RG_NUTS") or U("RG_FAIRY_SLINGSHOT") or U("RG_FAIRY_BOW") or self.HookshotOrBoomerang())
        if e == "RE_KING_DODONGO":
            return self.HasItem("RG_KING_DODONGO_SOUL") and self.CanJumpslash() and \
                (U("RG_BOMB_BAG") or self.HasItem("RG_GORONS_BRACELET") or
                 (bool(self.ctx.GetTrickOption("RT_DC_DODONGO_CHU")) and self.IsAdult and U("RG_BOMBCHU_5")))
        if e == "RE_BARINADE":
            return self.HasItem("RG_BARINADE_SOUL") and U("RG_BOOMERANG") and \
                (self.CanJumpslashExceptHammer() or
                 (bool(self.ctx.GetTrickOption("RT_JABU_BARINADE_POTS")) and self.HasItem("RG_POWER_BRACELET")))
        if e == "RE_PHANTOM_GANON":
            return self.HasItem("RG_PHANTOM_GANON_SOUL") and self.CanUseSword() and \
                (U("RG_HOOKSHOT") or U("RG_FAIRY_BOW") or U("RG_FAIRY_SLINGSHOT"))
        if e == "RE_VOLVAGIA":
            return self.HasItem("RG_VOLVAGIA_SOUL") and U("RG_MEGATON_HAMMER")
        if e == "RE_MORPHA":
            return self.HasItem("RG_MORPHA_SOUL") and \
                (U("RG_HOOKSHOT") or (bool(self.ctx.GetTrickOption("RT_WATER_MORPHA_WITHOUT_HOOKSHOT")) and
                                      self.HasItem("RG_BRONZE_SCALE"))) and \
                (self.CanUseSword() or U("RG_MEGATON_HAMMER"))
        if e == "RE_BONGO_BONGO":
            return self.HasItem("RG_BONGO_BONGO_SOUL") and \
                (U("RG_LENS_OF_TRUTH") or bool(self.ctx.GetTrickOption("RT_LENS_BONGO"))) and self.CanUseSword() and \
                (U("RG_HOOKSHOT") or U("RG_FAIRY_BOW") or U("RG_FAIRY_SLINGSHOT") or
                 bool(self.ctx.GetTrickOption("RT_SHADOW_BONGO")))
        if e == "RE_TWINROVA":
            return self.HasItem("RG_TWINROVA_SOUL") and U("RG_MIRROR_SHIELD") and \
                (self.CanUseSword() or U("RG_MEGATON_HAMMER"))
        if e == "RE_GANONDORF":
            return self.HasItem("RG_GANON_SOUL") and U("RG_LIGHT_ARROWS") and self.CanUseSword()
        if e == "RE_GANON":
            return self.HasItem("RG_GANON_SOUL") and U("RG_MASTER_SWORD")
        if e == "RE_DARK_LINK":
            return self.CanUseSword() or \
                (U("RG_BOOMERANG") and (U("RG_FAIRY_BOW") or U("RG_STICKS") or U("RG_MEGATON_HAMMER") or
                                        self.HasExplosives())) or \
                (U("RG_NUTS") and (U("RG_STICKS") or U("RG_MEGATON_HAMMER")))
        if e == "RE_ANUBIS":
            return self.HasFireSource()
        if e == "RE_BEAMOS":
            return self.HasExplosives()
        if e == "RE_PURPLE_LEEVER":
            return U("RG_MASTER_SWORD") or U("RG_BIGGORON_SWORD")
        if e == "RE_TENTACLE":
            return U("RG_BOOMERANG")
        if e == "RE_BARI":
            return self.HookshotOrBoomerang() or U("RG_FAIRY_BOW") or self.HasExplosives() or \
                U("RG_MEGATON_HAMMER") or U("RG_STICKS") or U("RG_DINS_FIRE") or \
                (self.TakeDamage() and self.CanUseSword())
        if e == "RE_SHABOM":
            return U("RG_BOOMERANG") or U("RG_NUTS") or self.CanJumpslash() or U("RG_DINS_FIRE") or \
                U("RG_ICE_ARROWS") or self.EffectiveHealth() > quantity * 4
        if e == "RE_OCTOROK":
            return self.CanReflectNuts() or self.HookshotOrBoomerang() or U("RG_FAIRY_BOW") or \
                U("RG_FAIRY_SLINGSHOT") or U("RG_BOMB_BAG") or (wallOrFloor and U("RG_BOMBCHU_5"))
        if e == "RE_WALLTULA":
            killed = False
            if d <= ED["ED_SHORT_JUMPSLASH"]:
                killed = U("RG_KOKIRI_SWORD")
            if d <= ED["ED_MASTER_SWORD_JUMPSLASH"]:
                killed = killed or U("RG_MASTER_SWORD")
            if d <= ED["ED_LONG_JUMPSLASH"]:
                killed = killed or U("RG_BIGGORON_SWORD") or U("RG_STICKS")
            if d <= ED["ED_BOMB_THROW"]:
                killed = killed or (not inWater and U("RG_BOMB_BAG")) or U("RG_DINS_FIRE")
            if d <= ED["ED_BOOMERANG"]:
                killed = killed or U("RG_BOOMERANG")
            if d <= ED["ED_HOOKSHOT"]:
                killed = killed or U("RG_HOOKSHOT") or U("RG_BOMBCHU_5") or U("RG_MEGATON_HAMMER")
            if d <= ED["ED_LONGSHOT"]:
                killed = killed or U("RG_LONGSHOT")
            if d <= ED["ED_FAR"]:
                killed = killed or U("RG_FAIRY_SLINGSHOT") or U("RG_FAIRY_BOW")
            return killed
        raise LogicError(f"CanKillEnemy reached default for {enemy}")

    def CanPassEnemy(self, enemy, distance="ED_CLOSE", wallOrFloor=True):
        if self.CanKillEnemy(enemy, distance, wallOrFloor):
            return True
        e = enemy
        if e in _PASS_ALWAYS:
            return True
        if e == "RE_GERUDO_GUARD":
            return bool(self.ctx.GetTrickOption("RT_PASS_GUARDS_WITH_NOTHING")) or \
                self.HasItem("RG_GERUDO_MEMBERSHIP_CARD") or self.CanUse("RG_FAIRY_BOW") or self.CanUse("RG_HOOKSHOT")
        if e == "RE_BREAK_ROOM_GUARD":
            return self.HasItem("RG_GERUDO_MEMBERSHIP_CARD") or self.CanUse("RG_FAIRY_BOW") or \
                self.CanUse("RG_HOOKSHOT")
        if e == "RE_BIG_SKULLTULA":
            return self.CanUse("RG_NUTS") or self.CanUse("RG_BOOMERANG") or \
                (bool(self.ctx.GetTrickOption("RT_BIG_SKULLTULA_PAUSE_LIFT")) and wallOrFloor and
                 distance == "ED_CLOSE")
        if e == "RE_LIKE_LIKE":
            return self.CanUse("RG_HOOKSHOT") or self.CanUse("RG_BOOMERANG")
        if e in ("RE_GIBDO", "RE_REDEAD"):
            return True   # (you can move slowly to avoid getting screamed at)
        if e in ("RE_IRON_KNUCKLE", "RE_BIG_OCTO", "RE_WALLTULA"):
            return False
        if e == "RE_GREEN_BUBBLE":
            return self.TakeDamage() or self.CanUse("RG_NUTS") or self.CanUse("RG_BOOMERANG") or \
                self.CanUse("RG_HOOKSHOT")
        raise LogicError(f"CanPassEnemy reached default for {enemy}")

    def CanAvoidEnemy(self, enemy, distance="ED_CLOSE", grounded=False, quantity=1):
        if self.CanKillEnemy(enemy, distance, True, quantity):
            return True
        e = enemy
        if e in _AVOID_ALWAYS:
            return True
        U = self.CanUse
        if e == "RE_BEAMOS":
            if not grounded:
                return True
            d = ED[distance]
            avoided = False
            if d <= ED["ED_BOMB_THROW"]:   # (ED_CLOSE .. ED_BOMB_THROW: melee can stun but means getting close)
                avoided = U("RG_DINS_FIRE") or U("RG_NUTS")
            if d <= ED["ED_BOOMERANG"]:
                avoided = avoided or U("RG_BOOMERANG")
            if d <= ED["ED_HOOKSHOT"]:
                avoided = avoided or U("RG_HOOKSHOT")
            if d <= ED["ED_LONGSHOT"]:
                avoided = avoided or U("RG_LONGSHOT")
            if d <= ED["ED_FAR"]:
                avoided = avoided or U("RG_FAIRY_SLINGSHOT") or U("RG_FAIRY_BOW")
            return avoided
        if e == "RE_MAD_SCRUB":
            return not grounded or U("RG_NUTS")
        if e in ("RE_KEESE", "RE_FIRE_KEESE", "RE_GUAY"):
            return U("RG_NUTS") or U("RG_SKULL_MASK")
        if e == "RE_BLUE_BUBBLE":
            return not grounded or U("RG_NUTS") or self.HookshotOrBoomerang() or self.CanStandingShield()
        if e == "RE_TORCH_SLUG":
            return not grounded or U("RG_NUTS") or U("RG_HOOKSHOT") or U("RG_DINS_FIRE")
        raise LogicError(f"CanAvoidEnemy reached default for {enemy}")

    def CanGetEnemyDrop(self, enemy, distance="ED_CLOSE", aboveLink=False):
        if not self.CanKillEnemy(enemy, distance):
            return False
        d = ED[distance]
        if d <= ED["ED_MASTER_SWORD_JUMPSLASH"]:
            return True
        if enemy == "RE_GOLD_SKULLTULA":
            drop = False
            if d <= ED["ED_BOOMERANG"]:   # (ED_CLOSE .. ED_BOOMERANG)
                drop = drop or self.CanUse("RG_BOOMERANG")
            if d <= ED["ED_HOOKSHOT"]:
                drop = drop or self.CanUse("RG_HOOKSHOT")
            if d <= ED["ED_LONGSHOT"]:
                drop = drop or self.CanUse("RG_LONGSHOT")
            return drop   # (ED_FAR: break)
        if enemy in ("RE_KEESE", "RE_FIRE_KEESE", "RE_GUAY"):
            return True
        return aboveLink or (d <= ED["ED_BOOMERANG"] and self.CanUse("RG_BOOMERANG"))

    # ---- misc helpers

    def CanBreakMudWalls(self):
        return self.BlastOrSmash() or (bool(self.ctx.GetTrickOption("RT_BLUE_FIRE_MUD_WALLS")) and self.BlueFire())

    def CanGetDekuBabaSticks(self):
        return self.CanUseSword() or self.CanUse("RG_BOOMERANG")

    def CanGetDekuBabaNuts(self):
        return self.CanJumpslash() or self.CanUse("RG_FAIRY_SLINGSHOT") or self.CanUse("RG_FAIRY_BOW") or \
            self.HasExplosives() or self.CanUse("RG_DINS_FIRE")

    def CanHitEyeTargets(self):
        return self.CanUse("RG_FAIRY_BOW") or self.CanUse("RG_FAIRY_SLINGSHOT")

    def CanDetonateBombFlowers(self):
        return self.CanUse("RG_FAIRY_BOW") or self.HasExplosives() or self.CanUse("RG_DINS_FIRE")

    def CanDetonateUprightBombFlower(self):
        return self.CanDetonateBombFlowers() or self.HasItem("RG_GORONS_BRACELET") or \
            (bool(self.ctx.GetTrickOption("RT_BLUE_FIRE_MUD_WALLS")) and self.CanUse("RG_BOTTLE_WITH_BLUE_FIRE") and
             (self.EffectiveHealth() > 8 or self.CanUse("RG_NAYRUS_LOVE")))

    def BeanPlanted(self, beanEvent):
        # (rely on Get, rest is to track bean being planted out of logic)
        if self.Get(beanEvent):
            return True
        # (if we don't have the bean soul, the bean isn't really planted)
        soul = _BEAN_SOUL_OF_EVENT[beanEvent]
        if not self.HasItem(soul):
            return False
        # (SoH reads the patch's scene switch flag from the save context (gPlayState is null while generating):
        #  the logic save context has all scene flags 0 (InitSaveContext; no bean patch is in the Water Temple, the
        #  one scene with a set flag), so the bean is not planted)
        return False

    def CanMeleeRecoilHover(self, req):
        if not (self.CanUse("RG_HOVER_BOOTS") and bool(self.ctx.GetTrickOption("RT_HOVER_BOOST_SIMPLE"))):
            return False
        can = False
        if req == "RECOIL_SWORD":
            can = self.CanJumpslash()
        elif req in ("RECOIL_SWORD_AND_SHIELD", "RECOIL_HAMMER"):
            if req == "RECOIL_SWORD_AND_SHIELD":
                can = self.CanJumpslash() and self.CanStandingShield()
            can = can or self.CanUse("RG_MEGATON_HAMMER")
        elif req == "RECOIL_HAMMER_AND_SHIELD":
            can = self.CanUse("RG_MEGATON_HAMMER") and self.CanStandingShield()
        return can

    def CanRecoilHoverFromActor(self, req):
        if not (self.CanUse("RG_HOVER_BOOTS") and bool(self.ctx.GetTrickOption("RT_HOVER_BOOST_SIMPLE"))):
            return False
        can = False
        if req == "ARECOIL_LONG_AND_SHIELD":
            can = (self.CanUse("RG_STICKS") or self.CanUse("RG_BIGGORON_SWORD")) and self.CanStandingShield()
        elif req in ("ARECOIL_SHORT", "ARECOIL_MASTER", "ARECOIL_LONG"):
            if req == "ARECOIL_SHORT":
                can = self.CanUse("RG_MEGATON_HAMMER") or self.CanUse("RG_KOKIRI_SWORD")
            if req in ("ARECOIL_SHORT", "ARECOIL_MASTER"):
                can = can or self.CanUse("RG_MASTER_SWORD")
            can = can or self.CanUse("RG_STICKS") or self.CanUse("RG_BIGGORON_SWORD")
        return can

    def CanRecoilHover(self, req, bombFlower=False):
        if not (self.CanUse("RG_HOVER_BOOTS") and bool(self.ctx.GetTrickOption("RT_HOVER_BOOST_SIMPLE"))):
            return False
        if req == "RECOIL_SWORD":
            if self.CanJumpslash():
                return True
        elif req in ("RECOIL_SWORD_AND_SHIELD", "RECOIL_HAMMER"):
            if req == "RECOIL_SWORD_AND_SHIELD" and self.CanJumpslash() and self.CanStandingShield():
                return True
            if self.CanUse("RG_MEGATON_HAMMER"):
                return True
        elif req == "RECOIL_HAMMER_AND_SHIELD":
            if self.CanUse("RG_MEGATON_HAMMER") and self.CanStandingShield():
                return True
        if bool(self.ctx.GetTrickOption("RT_DAMAGE_BOOST_SIMPLE")) and self.TakeDamage("DAMAGE_NO_FAIRY") and \
                (self.HasExplosives() or (bombFlower and self.HasItem("RG_GORONS_BRACELET"))):
            return True
        return False

    def CanBombRecoilHover(self, bombFlower=False):
        T = self.ctx.GetTrickOption
        return bool(T("RT_DAMAGE_BOOST_SIMPLE")) and bool(T("RT_HOVER_BOOST_SIMPLE")) and \
            self.CanUse("RG_HOVER_BOOTS") and self.HasExplosives() and self.TakeDamage("DAMAGE_NO_FAIRY")

    def Water3FCentralToHighEmblem(self):
        T = self.ctx.GetTrickOption
        if self.ctx.GetDungeon("WATER_TEMPLE").IsMQ():
            return self.CanUse("RG_HOOKSHOT") or (self.IsAdult and self.CanUse("RG_HOVER_BOOTS")) or \
                ((self.IsAdult or self.BunnyHood()) and bool(T("RT_WATER_HIGH_EMBLEM_JUMP"))) or \
                self.CanMegajump() or self.CanMidairGroundJump()
        return (self.IsAdult and self.CanUse("RG_HOVER_BOOTS")) or self.CanMidairGroundJump() or \
            self.CanMegajump() or ((self.Get("LOGIC_WATER_SCARECROW") and self.CanUse("RG_HOOKSHOT")) or
                                   ((self.IsAdult or self.BunnyHood()) and bool(T("RT_WATER_HIGH_EMBLEM_JUMP"))))

    def WaterRisingTargetTo3FCentral(self):
        return self.CanUse("RG_LONGSHOT") or self.CanRecoilHover("RECOIL_HAMMER") or self.CanMegajump(True)

    def WaterLevel(self, level):
        G = self.Get
        if level == "WL_LOW":
            return G("LOGIC_WATER_LOW") or \
                (G("LOGIC_WATER_COULD_LOW_FROM_HIGH") and (G("LOGIC_WATER_COULD_HIGH_FROM_MID") or
                                                         G("LOGIC_WATER_HIGH")) and self.CanUse("RG_ZELDAS_LULLABY"))
        if level == "WL_LOW_OR_MID":
            return G("LOGIC_WATER_LOW") or G("LOGIC_WATER_MIDDLE") or \
                ((G("LOGIC_WATER_COULD_LOW_FROM_HIGH") or G("LOGIC_WATER_LOW")) and self.CanUse("RG_ZELDAS_LULLABY"))
        if level == "WL_MID":
            return G("LOGIC_WATER_MIDDLE") or (G("LOGIC_WATER_LOW") and G("LOGIC_WATER_COULD_MIDDLE")) or \
                ((G("LOGIC_WATER_COULD_LOW_FROM_HIGH") or G("LOGIC_WATER_COULD_LOW")) and
                 G("LOGIC_WATER_COULD_MIDDLE") and self.CanUse("RG_ZELDAS_LULLABY"))
        if level == "WL_HIGH":
            return G("LOGIC_WATER_HIGH") or (G("LOGIC_WATER_COULD_HIGH_FROM_MID") and G("LOGIC_WATER_COULD_MIDDLE"))
        if level == "WL_HIGH_OR_MID":
            return G("LOGIC_WATER_MIDDLE") or G("LOGIC_WATER_HIGH") or G("LOGIC_WATER_COULD_MIDDLE")
        raise LogicError(f"WaterLevel: missing case for {level}")

    def BottleCount(self):
        count = 0
        for slot in range(SLOT["SLOT_BOTTLE_1"], SLOT["SLOT_BOTTLE_4"] + 1):
            item = self.GetSaveContext().items[slot]
            if item == "ITEM_LETTER_RUTO":
                if self.Get("LOGIC_DELIVER_RUTOS_LETTER"):
                    count += 1
            elif item == "ITEM_BIG_POE":
                if self.Get("LOGIC_CAN_EMPTY_BIG_POES"):
                    count += 1
            elif item == "ITEM_NONE":
                pass
            else:
                count += 1
        return count

    def OcarinaButtons(self):
        H = self.HasItem
        return H("RG_OCARINA_A_BUTTON") + H("RG_OCARINA_C_LEFT_BUTTON") + H("RG_OCARINA_C_RIGHT_BUTTON") + \
            H("RG_OCARINA_C_UP_BUTTON") + H("RG_OCARINA_C_DOWN_BUTTON")

    def HasBottle(self):
        return self.BottleCount() >= 1

    def CanUseSword(self):
        return self.CanUse("RG_KOKIRI_SWORD") or self.CanUse("RG_MASTER_SWORD") or self.CanUse("RG_BIGGORON_SWORD")

    def CanJumpslashExceptHammer(self):
        return self.CanUse("RG_STICKS") or self.CanUseSword()

    def CanJumpslash(self):
        return self.CanJumpslashExceptHammer() or self.CanUse("RG_MEGATON_HAMMER")

    def CanClearStalagmite(self):
        return self.CanJumpslash() or self.HasExplosives() or self.CanUse("RG_GIANTS_KNIFE") or \
            (bool(self.ctx.GetTrickOption("RT_ICE_STALAGMITE_HOOKSHOT")) and self.CanUse("RG_HOOKSHOT"))

    def CanHitSwitch(self, distance="ED_CLOSE", inWater=False):
        U = self.CanUse
        d = ED[distance]
        hit = False
        if d <= ED["ED_SHORT_JUMPSLASH"]:   # (case ED_CLOSE: case ED_SHORT_JUMPSLASH:)
            hit = U("RG_KOKIRI_SWORD") or U("RG_MEGATON_HAMMER") or U("RG_GIANTS_KNIFE")
        if d <= ED["ED_MASTER_SWORD_JUMPSLASH"]:
            hit = hit or U("RG_MASTER_SWORD")
        if d <= ED["ED_LONG_JUMPSLASH"]:
            hit = hit or U("RG_BIGGORON_SWORD") or U("RG_STICKS")
        if d <= ED["ED_BOMB_THROW"]:
            hit = hit or (not inWater and U("RG_BOMB_BAG"))
        if d <= ED["ED_BOOMERANG"]:
            hit = hit or U("RG_BOOMERANG")
        if d <= ED["ED_HOOKSHOT"]:
            hit = hit or U("RG_HOOKSHOT") or U("RG_BOMBCHU_5")
        if d <= ED["ED_LONGSHOT"]:
            hit = hit or U("RG_LONGSHOT")
        if d <= ED["ED_FAR"]:
            hit = hit or U("RG_FAIRY_SLINGSHOT") or U("RG_FAIRY_BOW")
        return hit

    def CanDamage(self):
        return self.CanUse("RG_FAIRY_SLINGSHOT") or self.CanJumpslash() or self.HasExplosives() or \
            self.CanUse("RG_DINS_FIRE") or self.CanUse("RG_FAIRY_BOW")

    def CanAttack(self):
        return self.CanDamage() or self.CanUse("RG_BOOMERANG") or self.CanUse("RG_HOOKSHOT")

    def BombchusEnabled(self):
        if self.ctx.GetOption("RSK_BOMBCHU_BAG").IsNot("RO_BOMBCHU_BAG_NONE"):
            return self.CheckInventory("ITEM_BOMBCHU", True)
        return self.HasItem("RG_BOMB_BAG")

    def ShopItemNotForSale(self, loc):
        if self.ctx.GetOption("RSK_SHOP_SHIELDS_AND_TUNICS_ONLY_REFILL").IsNot("RO_GENERIC_ON") or \
                D.LOCATIONS[loc]["type"] != "RCTYPE_SHOP":
            return False
        # (ctx->GetItemLocation(loc)->GetPlacedRandomizerGet(): the search sets PlacedItem)
        placed_item = self.PlacedItem(loc)
        return {"RG_BUY_DEKU_SHIELD": not self.CheckRandoInf("RAND_INF_HAS_FOUND_DEKU_SHIELD"),
                "RG_BUY_HYLIAN_SHIELD": not self.CheckRandoInf("RAND_INF_HAS_FOUND_HYLIAN_SHIELD"),
                "RG_BUY_GORON_TUNIC": not self.CheckRandoInf("RAND_INF_HAS_FOUND_GORON_TUNIC"),
                "RG_BUY_ZORA_TUNIC": not self.CheckRandoInf("RAND_INF_HAS_FOUND_ZORA_TUNIC")}.get(placed_item, False)

    def BombchuRefill(self):
        return self.Get("LOGIC_BUY_BOMBCHUS") or self.Get("LOGIC_COULD_PLAY_BOWLING") or \
            self.Get("LOGIC_CARPET_MERCHANT") or self.ctx.GetOption("RSK_ENABLE_BOMBCHU_DROPS").Is("RO_AMMO_DROPS_ON")

    def HookshotOrBoomerang(self):
        return self.CanUse("RG_HOOKSHOT") or self.CanUse("RG_BOOMERANG")

    def ScarecrowsSong(self):
        return (self.HasItem("RG_SCARECROWS_SONG") and self.HasItem("RG_FAIRY_OCARINA") and
                self.OcarinaButtons() >= 2) or \
            (not self.ctx.GetOption("RSK_SHUFFLE_SCARECROWS_SONG") and self.Get("LOGIC_CHILD_SCARECROW") and
             self.Get("LOGIC_ADULT_SCARECROW"))

    def BlueFire(self):
        return self.CanUse("RG_BOTTLE_WITH_BLUE_FIRE") or \
            (bool(self.ctx.GetOption("RSK_BLUE_FIRE_ARROWS")) and self.CanUse("RG_ICE_ARROWS"))

    def CanBreakPots(self, distance="ED_CLOSE", wallOrFloor=True, inWater=False):
        U = self.CanUse
        d = ED[distance]
        hit = False
        if d <= ED["ED_CLOSE"]:
            hit = self.HasItem("RG_POWER_BRACELET")
        if d <= ED["ED_SHORT_JUMPSLASH"]:
            hit = hit or U("RG_KOKIRI_SWORD") or U("RG_MEGATON_HAMMER") or U("RG_GIANTS_KNIFE")
        if d <= ED["ED_MASTER_SWORD_JUMPSLASH"]:
            hit = hit or U("RG_MASTER_SWORD")
        if d <= ED["ED_LONG_JUMPSLASH"]:
            hit = hit or U("RG_BIGGORON_SWORD") or U("RG_STICKS")
        if d <= ED["ED_BOMB_THROW"]:
            hit = hit or (not inWater and U("RG_BOMB_BAG"))
        if d <= ED["ED_BOOMERANG"]:
            hit = hit or U("RG_BOOMERANG")
        if d <= ED["ED_HOOKSHOT"]:
            hit = hit or U("RG_HOOKSHOT")
        if d <= ED["ED_LONGSHOT"]:
            hit = hit or U("RG_LONGSHOT")
        if d <= ED["ED_FAR"]:
            hit = hit or U("RG_FAIRY_SLINGSHOT") or U("RG_FAIRY_BOW")
        return hit or (wallOrFloor and U("RG_BOMBCHU_5"))

    def CanBreakCrates(self):
        return True

    def CanBreakSmallCrates(self):
        return self.CanJumpslash() or self.HasExplosives() or self.HasItem("RG_POWER_BRACELET")

    def CanBreakRocks(self):
        return self.BlastOrSmash() or self.HasItem("RG_POWER_BRACELET")

    def CanBonkTrees(self):
        return True

    def CanRead(self):
        return True

    def HasExplosives(self):
        return self.CanUse("RG_BOMB_BAG") or self.CanUse("RG_BOMBCHU_5")

    def BlastOrSmash(self):
        return self.HasExplosives() or self.CanUse("RG_MEGATON_HAMMER")

    def CanSpawnSoilSkull(self, bean):
        return self.IsChild and self.CanUse("RG_BOTTLE_WITH_BUGS") and self.HasItem(bean)

    def CanReflectNuts(self):
        return self.CanUse("RG_DEKU_SHIELD") or (self.IsAdult and self.HasItem("RG_HYLIAN_SHIELD"))

    def CanCutShrubs(self):
        U = self.CanUse
        return U("RG_KOKIRI_SWORD") or U("RG_BOOMERANG") or self.HasExplosives() or U("RG_MASTER_SWORD") or \
            U("RG_MEGATON_HAMMER") or U("RG_BIGGORON_SWORD") or U("RG_GIANTS_KNIFE") or \
            self.HasItem("RG_GORONS_BRACELET")

    def CanStunDeku(self):
        return self.CanAttack() or self.CanUse("RG_NUTS") or self.CanReflectNuts()

    def CallGossipFairyExceptSuns(self):
        return self.CanUse("RG_ZELDAS_LULLABY") or self.CanUse("RG_EPONAS_SONG") or self.CanUse("RG_SONG_OF_TIME")

    def CallGossipFairy(self):
        return self.CallGossipFairyExceptSuns() or self.CanUse("RG_SUNS_SONG")

    def Health(self):
        return self.GetSaveContext().healthCapacity

    def EffectiveHealth(self):
        Multiplier = self.ctx.GetOption("RSK_DAMAGE_MULTIPLIER").Get()
        if Multiplier >= EV["RO_DAMAGE_MULTIPLIER_OHKO"]:
            return 1
        health = self.Health() << (1 + self.HasItem("RG_DOUBLE_DEFENSE"))
        return ((health + (1 << Multiplier) - 1) >> Multiplier) & 0xFFFF

    def DungeonCount(self):
        if self.CalculatingAvailableChecks:
            raise LogicError("DungeonCount while CalculatingAvailableChecks is not ported")
        G = self.Get
        return G("LOGIC_DEKU_TREE_CLEAR") + G("LOGIC_DODONGOS_CAVERN_CLEAR") + G("LOGIC_JABU_JABUS_BELLY_CLEAR") + \
            G("LOGIC_FOREST_TEMPLE_CLEAR") + G("LOGIC_FIRE_TEMPLE_CLEAR") + G("LOGIC_WATER_TEMPLE_CLEAR") + \
            G("LOGIC_SPIRIT_TEMPLE_CLEAR") + G("LOGIC_SHADOW_TEMPLE_CLEAR")

    def StoneCount(self):
        H = self.HasItem
        return H("RG_KOKIRI_EMERALD") + H("RG_GORON_RUBY") + H("RG_ZORA_SAPPHIRE")

    def MedallionCount(self):
        H = self.HasItem
        return H("RG_FOREST_MEDALLION") + H("RG_FIRE_MEDALLION") + H("RG_WATER_MEDALLION") + \
            H("RG_SPIRIT_MEDALLION") + H("RG_SHADOW_MEDALLION") + H("RG_LIGHT_MEDALLION")

    def FireTimer(self):
        if self.CanUse("RG_GORON_TUNIC"):
            return 0xFFFF
        return self.Health() // 2 if self.ctx.GetTrickOption("RT_FEWER_TUNIC_REQUIREMENTS") else 0

    def WaterTimer(self):
        if self.CanUse("RG_ZORA_TUNIC"):
            return 0xFFFF
        return self.Health() // 2 if self.ctx.GetTrickOption("RT_FEWER_TUNIC_REQUIREMENTS") else 0

    def TakeDamage(self, allowance="DAMAGE_ANY"):
        return (self.CanUse("RG_BOTTLE_WITH_FAIRY") and allowance != "DAMAGE_NO_FAIRY") or \
            self.EffectiveHealth() > 8 or self.CanUse("RG_NAYRUS_LOVE")

    def CanVoid(self):
        if self.HasItem("RG_BOTTLE_WITH_FAIRY"):
            return True
        if self.ctx.GetOption("RSK_DAMAGE_MULTIPLIER").Is("RO_DAMAGE_MULTIPLIER_OHKO"):
            return False
        return self.Health() > (FULL_HEART_HEALTH >> (1 if self.HasItem("RG_DOUBLE_DEFENSE") else 0))

    def CanOpenBombGrotto(self):
        return self.BlastOrSmash() and \
            (self.HasItem("RG_STONE_OF_AGONY") or bool(self.ctx.GetTrickOption("RT_GROTTOS_WITHOUT_AGONY")))

    def CanOpenStormsGrotto(self):
        return self.CanUse("RG_SONG_OF_STORMS") and \
            (self.HasItem("RG_STONE_OF_AGONY") or bool(self.ctx.GetTrickOption("RT_GROTTOS_WITHOUT_AGONY")))

    def CanGetNightTimeGS(self):
        return self.AtNight and (self.CanUse("RG_SUNS_SONG") or not self.ctx.GetOption("RSK_SKULLS_SUNS_SONG"))

    def CanBreakUpperBeehives(self):
        return self.HookshotOrBoomerang() or \
            (bool(self.ctx.GetTrickOption("RT_BOMBCHU_BEEHIVES")) and self.CanUse("RG_BOMBCHU_5")) or \
            (bool(self.ctx.GetOption("RSK_SLINGBOW_BREAK_BEEHIVES")) and
             (self.CanUse("RG_FAIRY_BOW") or self.CanUse("RG_FAIRY_SLINGSHOT")))

    def CanBreakLowerBeehives(self):
        return self.CanBreakUpperBeehives() or self.CanUse("RG_BOMB_BAG")

    def HasFireSource(self):
        return self.CanUse("RG_DINS_FIRE") or self.CanUse("RG_FIRE_ARROWS")

    def HasFireSourceWithTorch(self):
        return self.HasFireSource() or self.CanUse("RG_STICKS")

    def SunlightArrows(self):
        return bool(self.ctx.GetOption("RSK_SUNLIGHT_ARROWS")) and self.CanUse("RG_LIGHT_ARROWS")

    def BunnyHood(self):
        return bool(self.ctx.GetOption("RSK_BUNNY_HOOD")) and self.CanUse("RG_BUNNY_HOOD")

    def BunnyHovers(self):
        return self.CanUse("RG_HOVER_BOOTS") and self.BunnyHood()

    def CanStandingShield(self):
        return self.CanUse("RG_MIRROR_SHIELD") or (self.IsAdult and self.HasItem("RG_HYLIAN_SHIELD")) or \
            self.CanUse("RG_DEKU_SHIELD")

    def CanShield(self):
        return self.CanUse("RG_MIRROR_SHIELD") or self.HasItem("RG_HYLIAN_SHIELD") or self.CanUse("RG_DEKU_SHIELD")

    def CanUseProjectile(self):
        return self.HasExplosives() or self.CanUse("RG_FAIRY_BOW") or self.CanUse("RG_HOOKSHOT") or \
            self.CanUse("RG_FAIRY_SLINGSHOT") or self.CanUse("RG_BOOMERANG")

    def CanBuildRainbowBridge(self):
        O = self.ctx.GetOption
        H = self.HasItem
        b = O("RSK_RAINBOW_BRIDGE")
        if b.Is("RO_BRIDGE_ALWAYS_OPEN"):
            return True
        if b.Is("RO_BRIDGE_VANILLA"):
            return H("RG_SHADOW_MEDALLION") and H("RG_SPIRIT_MEDALLION") and self.CanUse("RG_LIGHT_ARROWS")
        if b.Is("RO_BRIDGE_GREG"):
            return H("RG_GREG_RUPEE")
        # (the count bridges read RSK_RAINBOW_BRIDGE_*_COUNT, which SETTINGS does not fix: the bridge is vanilla)
        raise LogicError(f"CanBuildRainbowBridge: bridge {b} is not ported (vanilla settings)")

    def CanTriggerGBK(self):
        if self.ctx.GBKCondition() == "RO_CHECK_TRIGGER_NONE":
            return False   # (switch default)
        raise LogicError("CanTriggerGBK: GBK trigger conditions are not ported")

    def CanTriggerGanonsSoul(self):
        if self.ctx.GanonsSoulCondition() == "RO_CHECK_TRIGGER_NONE":
            return False
        raise LogicError("CanTriggerGanonsSoul: trigger conditions are not ported")

    def CanTriggerWincon(self):
        if self.ctx.WinCondition() == "RO_WINCON_DEFEAT_GANON":
            return False   # (switch default: the win is RC_GANON's Triforce)
        raise LogicError("CanTriggerWincon: trigger win conditions are not ported")

    def SmallKeys(self, scene, requiredAmount):
        if self.HasItem("RG_SKELETON_KEY"):
            return True
        return self.GetSmallKeyCount(scene) >= requiredAmount

    # ---- save context access

    def GetSaveContext(self):
        if self.mSaveContext is None:
            self.NewSaveContext()
        return self.mSaveContext

    def NewSaveContext(self):
        self.mSaveContext = SaveContext()

    def InventorySlot(self, item):
        return SLOT[OOT["gItemSlots"][ITEM_ID[item]]]

    def CurrentUpgrade(self, upgrade):
        u = UPG[upgrade]
        return (self.mSaveContext.upgrades & OOT["gUpgradeMasks"][u]) >> OOT["gUpgradeShifts"][u]

    def CurrentInventory(self, item):
        return self.mSaveContext.items[self.InventorySlot(item)]

    def SetUpgrade(self, upgrade, level):
        u = UPG[upgrade]
        sc = self.mSaveContext
        sc.upgrades &= OOT["gUpgradeNegMasks"][u]
        sc.upgrades |= (level & 0xFF) << OOT["gUpgradeShifts"][u]   # (uint8_t level)
        sc.upgrades &= 0xFFFFFFFF

    def CheckInventory(self, item, exact):
        current = self.mSaveContext.items[self.InventorySlot(item)]
        return (current == item) if exact else (current != "ITEM_NONE")

    def SetInventory(self, itemSlot, item):
        self.mSaveContext.items[self.InventorySlot(itemSlot)] = item

    def CheckEquipment(self, item):
        return bool(EQUIP_FLAG[item] & self.mSaveContext.equipment)   # (item: an EQUIP_FLAG_*)

    def CheckQuestItem(self, item):
        return bool((1 << QUEST[item]) & self.mSaveContext.questItems)

    def SetQuestItem(self, item, state):
        if not state:
            self.mSaveContext.questItems &= ~(1 << QUEST[item])
        else:
            self.mSaveContext.questItems |= (1 << QUEST[item])

    def GetSmallKeyCount(self, sceneId):
        # (dungeon.cpp GetSceneTotalSmallKeys: held keys + key doors opened (scene switch flags at the dungeon's door
        #  flags); the logic save context has no door opened: the Water Temple's one set flag, 0x40000000 (bit 30),
        #  is not one of its door flags (1, 2, 5, 6, 9, 21))
        k = self.mSaveContext.dungeonKeys.get(sceneId, 0)
        return 0 if k == -1 else k

    def SetSmallKeyCount(self, dungeonIndex, count):
        c = count & 0xFF   # (uint8_t count stored in an int8_t)
        self.mSaveContext.dungeonKeys[dungeonIndex] = c - 256 if c >= 128 else c

    def CheckDungeonItem(self, item, dungeonIndex):
        return bool(self.mSaveContext.dungeonItems.get(dungeonIndex, 0) & (1 << DUNGEON_ITEM[item]))

    def SetDungeonItem(self, item, dungeonIndex, state):
        cur = self.mSaveContext.dungeonItems.get(dungeonIndex, 0)
        bit = 1 << DUNGEON_ITEM[item]
        self.mSaveContext.dungeonItems[dungeonIndex] = (cur | bit) if state else (cur & ~bit)

    def CheckRandoInf(self, flag):
        return flag in self.mSaveContext.randomizerInf

    def SetRandoInf(self, flag, state):
        if state:
            self.mSaveContext.randomizerInf.add(flag)
        else:
            self.mSaveContext.randomizerInf.discard(flag)

    def CheckEventChkInf(self, flag):
        return flag in self.mSaveContext.eventChkInf

    def SetEventChkInf(self, flag, state):
        if state:
            self.mSaveContext.eventChkInf.add(flag)
        else:
            self.mSaveContext.eventChkInf.discard(flag)

    def GetGSCount(self):
        return self.mSaveContext.gsTokens & 0xFF

    def GetTriforcePieceCount(self):
        return self.mSaveContext.triforcePiecesCollected

    def GetAmmo(self, item):
        return self.mSaveContext.ammo[SLOT[OOT["gItemSlots"][ITEM_ID[item]]]]

    def SetAmmo(self, item, count):
        self.mSaveContext.ammo[SLOT[OOT["gItemSlots"][ITEM_ID[item]]]] = count & 0xFF   # (uint8_t)

    def Get(self, logicVal):
        return logicVal in self.inLogic

    def Set(self, logicVal, remove):
        # (logic.h names the parameter `remove`, logic.cpp `value`: it is the value set)
        if remove:
            self.inLogic.add(logicVal)
        else:
            self.inLogic.discard(logicVal)

    def IsFireLoopLocked(self):
        k = self.ctx.GetOption("RSK_KEYSANITY")
        return k.Is("RO_DUNGEON_ITEM_LOC_ANYWHERE") or k.Is("RO_DUNGEON_ITEM_LOC_OVERWORLD") or \
            k.Is("RO_DUNGEON_ITEM_LOC_ANY_DUNGEON")

    def ReachScarecrow(self):
        return self.ScarecrowsSong() and self.CanUse("RG_HOOKSHOT")

    def ReachDistantScarecrow(self):
        return self.ScarecrowsSong() and self.CanUse("RG_LONGSHOT")

    def CanClimbLadder(self):
        return self.HasItem("RG_CLIMB") or \
            (bool(self.ctx.GetTrickOption("RT_HOOKSHOT_LADDERS")) and self.CanUse("RG_HOOKSHOT"))

    def CanClimbHighLadder(self):
        return self.HasItem("RG_CLIMB") or \
            (bool(self.ctx.GetTrickOption("RT_HOOKSHOT_LADDERS")) and self.CanUse("RG_LONGSHOT"))

    def SummonEpona(self):
        return self.IsAdult and self.Get("LOGIC_FREED_EPONA") and self.CanUse("RG_EPONAS_SONG")

    def IsReverseAccessPossible(self):
        O = self.ctx.GetOption
        return not O("RSK_SHUFFLE_BOSS_ENTRANCES").Is("RO_BOSS_ROOM_ENTRANCE_SHUFFLE_OFF") and \
            ((bool(O("RSK_DECOUPLED_ENTRANCES")) and
              O("RSK_SHUFFLE_BOSS_ENTRANCES").Is("RO_BOSS_ROOM_ENTRANCE_SHUFFLE_FULL")) or
             (bool(O("RSK_MIX_BOSS_ENTRANCES")) and
              (bool(O("RSK_MIX_OVERWORLD_ENTRANCES")) or bool(O("RSK_MIX_INTERIOR_ENTRANCES")))))

    def DMCUpperToPots(self):
        return self.CanUse("RG_HOVER_BOOTS") or self.BunnyHood() or \
            (self.IsAdult and (self.Get("LOGIC_DMC_BOULDER") or bool(self.ctx.GetTrickOption("RT_DMC_BOULDER_SKIP"))))

    def DMCPotsToPad(self):
        return self.CanUse("RG_HOVER_BOOTS") or (self.BunnyHood() and (self.IsAdult or self.HasItem("RG_CLIMB"))) or \
            self.CanUse("RG_HOOKSHOT") or self.CanMegajump() or \
            (self.IsAdult and ((self.CanShield() and bool(self.ctx.GetTrickOption("RT_DMC_BOLERO_JUMP")) and
                                self.HasItem("RG_POWER_BRACELET")) or
                               (self.HasItem("RG_CLIMB") and self.CanMidairDamageBoost())))

    def DMCPadToPots(self):
        return (self.CanUse("RG_HOVER_BOOTS") and (self.IsAdult or self.HasItem("RG_CLIMB"))) or \
            self.CanUse("RG_HOOKSHOT") or (self.IsAdult and self.BunnyHood() and self.HasItem("RG_CLIMB"))

    def DMCUpperToPad(self):
        return (self.TakeDamage() and bool(self.ctx.GetTrickOption("RT_UNINTUITIVE_JUMPS")) and
                ((self.IsAdult and self.ReachDistantScarecrow()) or
                 (((self.IsAdult and self.CanMegajump(True)) or self.CanBombRecoilHover() or
                   self.CanBunnyMegaJumpslash()) and self.EffectiveHealth() > 24))) or self.CanMegajump(True)

    def DMCHoverToPoH(self):
        return (bool(self.ctx.GetTrickOption("RT_DMC_HOVER_BEAN_POH")) and self.CanUse("RG_HOVER_BOOTS")) or \
            self.CanMegajump() or \
            (self.IsAdult and (self.CanMidairDamageBoost() or
                               (self.CanUse("RG_BOMB_BAG") and self.CanUse("RG_BOMBCHU_5") and
                                self.CanStandingShield())))

    def DMCPadToFarPlatform(self):
        return (self.IsAdult and (self.ReachDistantScarecrow() or self.CanBombRecoilHover())) or \
            self.CanMegajump(True)

    def ForestMQNEToNWViaWell(self):
        return (((self.HasItem("RG_CLIMB") and (self.Get("LOGIC_FOREST_DRAINED_WELL") or
                                                self.HasItem("RG_BRONZE_SCALE"))) or
                 (self.IsAdult and self.CanUse("RG_HOOKSHOT")) or self.CanUse("RG_LONGSHOT")) and
                (self.Get("LOGIC_FOREST_DRAINED_WELL") or (self.CanUse("RG_IRON_BOOTS") and self.WaterTimer() >= 16))) \
            or (self.HasItem("RG_GOLDEN_SCALE") and self.HasItem("RG_CLIMB") and self.WaterTimer() >= 16)

    def ForestMQNWToNEViaWell(self):
        return self.HasItem("RG_CLIMB") and \
            (self.Get("LOGIC_FOREST_DRAINED_WELL") or
             (self.WaterTimer() >= 16 and
              (self.HasItem("RG_GOLDEN_SCALE") or
               (self.HasItem("RG_BRONZE_SCALE") and
                (self.CanUse("RG_IRON_BOOTS") or self.CanUse("RG_LONGSHOT") or
                 (bool(self.ctx.GetTrickOption("RT_FOREST_WELL_SWIM")) and self.CanUse("RG_HOOKSHOT")))))))

    def SpiritExplosiveKeyLogic(self):
        return self.SmallKeys("SCENE_SPIRIT_TEMPLE", 1 if self.HasExplosives() else 2)

    def SpiritWestToSkull(self):
        return (self.IsAdult and (bool(self.ctx.GetTrickOption("RT_SPIRIT_STATUE_JUMP")) or self.BunnyHood())) or \
            self.CanUse("RG_HOVER_BOOTS") or self.ReachScarecrow() or self.CanMegajump()

    def SpiritSunBlockSouthLedge(self):
        return self.HasItem("RG_POWER_BRACELET") or self.IsAdult or self.CanKillEnemy("RE_BEAMOS") or \
            self.BunnyHovers() or \
            (self.CanUse("RG_HOOKSHOT") and
             (self.HasFireSource() or
              (self.Get("LOGIC_SPIRIT_SUN_BLOCK_TORCH") and
               (self.CanUse("RG_STICKS") or (bool(self.ctx.GetTrickOption("RT_SPIRIT_SUN_CHEST")) and
                                             self.CanUse("RG_FAIRY_BOW"))))))

    def SpiritEastToSwitch(self):
        return (self.IsAdult and (bool(self.ctx.GetTrickOption("RT_SPIRIT_STATUE_JUMP")) or self.BunnyHood())) or \
            self.CanUse("RG_HOVER_BOOTS") or \
            ((self.CanUse("RG_ZELDAS_LULLABY") and self.CanUse("RG_HOOKSHOT")) or self.CanMegajump())

    def MQSpiritWestToPots(self):
        return (self.IsAdult and (bool(self.ctx.GetTrickOption("RT_SPIRIT_STATUE_JUMP")) or self.BunnyHood())) or \
            self.CanUse("RG_HOVER_BOOTS") or self.CanUse("RG_SONG_OF_TIME")

    def MQSpiritStatueToSunBlock(self):
        return (self.IsAdult or bool(self.ctx.GetTrickOption("RT_SPIRIT_MQ_SUN_BLOCK_SOT")) or
                self.CanUse("RG_SONG_OF_TIME") or self.CanUse("RG_HOVER_BOOTS") or self.BunnyHood()) and \
            self.HasItem("RG_POWER_BRACELET")

    def MQSpiritStatueSouthDoor(self):
        return self.HasFireSource() or \
            (bool(self.ctx.GetTrickOption("RT_SPIRIT_MQ_FROZEN_EYE")) and self.CanUse("RG_FAIRY_BOW") and
             self.CanUse("RG_SONG_OF_TIME") and (self.HasItem("RG_CLIMB") or self.CanUse("RG_HOOKSHOT")))

    def MQSpirit4KeyColossus(self):
        return self.CanAvoidEnemy("RE_BEAMOS", "ED_CLOSE", True, 4) and self.CanUse("RG_SONG_OF_TIME") and \
            self.CanJumpslash() and (self.HasItem("RG_POWER_BRACELET") or self.SunlightArrows()) and \
            (bool(self.ctx.GetTrickOption("RT_LENS_SPIRIT_MQ")) or self.CanUse("RG_LENS_OF_TRUTH")) and \
            self.CanKillEnemy("RE_IRON_KNUCKLE") and self.CanUse("RG_HOOKSHOT")

    def MQSpirit4KeyWestHand(self):
        return self.CanUse("RG_LONGSHOT") and self.MQSpirit4KeyColossus()

    def CouldMQSpirit4KeyWestHand(self):
        return self.CanAvoidEnemy("RE_BEAMOS", "ED_CLOSE", True, 4) and self.CanUse("RG_SONG_OF_TIME") and \
            (self.HasItem("RG_MASTER_SWORD") or self.HasItem("RG_BIGGORON_SWORD") or
             self.HasItem("RG_MEGATON_HAMMER")) and \
            (self.HasItem("RG_POWER_BRACELET") or self.SunlightArrows()) and \
            (bool(self.ctx.GetTrickOption("RT_LENS_SPIRIT_MQ")) or self.CanUse("RG_LENS_OF_TRUTH")) and \
            self.HasItem("RG_LONGSHOT")

    def OuterWestHandLogic(self):
        return self.HasExplosives() and (self.HasItem("RG_CLIMB") or self.CanUse("RG_LONGSHOT")) and \
            self.HasItem("RG_POWER_BRACELET") and \
            self.SmallKeys("SCENE_SPIRIT_TEMPLE", 3 if self.HasItem("RG_LONGSHOT") else 5)

    def OuterWestHandMQLogic(self):
        return self.MQSpiritStatueToSunBlock() and \
            self.SmallKeys("SCENE_SPIRIT_TEMPLE", 4 if self.CouldMQSpirit4KeyWestHand() else 7)

    def SpiritHandToArch(self):
        if not ((self.CanJumpslash() and self.CanMegajump(True) and self.EffectiveHealth() > 24) or
                self.CanBunnyMegaJumpslash()):
            return False
        if self.ctx.GetDungeon("SPIRIT_TEMPLE").IsMQ():
            return self.CanHitSwitch() and self.OuterWestHandMQLogic() and \
                (self.HasItem("RG_CLIMB") or self.CanUse("RG_LONGSHOT")) and self.HasItem("RG_POWER_BRACELET")
        return self.OuterWestHandLogic()

    def StatueRoomMQKeyLogic(self):
        return self.SmallKeys("SCENE_SPIRIT_TEMPLE",
                              6 if (self.IsChild and self.Get("LOGIC_REVERSE_SPIRIT_CHILD") and self.CanHitSwitch() and
                                    (self.HasItem("RG_CLIMB") or self.CanUse("RG_LONGSHOT"))) else 7)

    # ---- items

    def gi_entry(self, rg):
        """(Item::GetGIEntry) the GetItemEntry fields ApplyItemEffect reads (itemId, objectId, modIndex) of the item
        rg gives now: a progressive item resolves to the item it would give (infinite upgrades, tycoon wallet off,
        no bombchu bag)"""
        it = D.ITEMS[rg]
        actual = "RG_NONE"
        sc = self.GetSaveContext()
        if rg == "RG_PROGRESSIVE_STICK_UPGRADE":
            lvl = self.CurrentUpgrade("UPG_STICKS")
            if lvl == 0 and self.ctx.GetOption("RSK_SHUFFLE_DEKU_STICK_BAG"):
                actual = "RG_DEKU_STICK_BAG"
            elif lvl in (0, 1):
                actual = "RG_DEKU_STICK_CAPACITY_20"
            elif lvl in (2, 3, 4):
                actual = "RG_DEKU_STICK_CAPACITY_30"
        elif rg == "RG_PROGRESSIVE_NUT_UPGRADE":
            lvl = self.CurrentUpgrade("UPG_NUTS")
            if lvl == 0 and self.ctx.GetOption("RSK_SHUFFLE_DEKU_NUT_BAG"):
                actual = "RG_DEKU_NUT_BAG"
            elif lvl in (0, 1):
                actual = "RG_DEKU_NUT_CAPACITY_30"
            elif lvl in (2, 3, 4):
                actual = "RG_DEKU_NUT_CAPACITY_40"
        elif rg == "RG_PROGRESSIVE_BOMB_BAG":
            actual = {0: "RG_BOMB_BAG", 1: "RG_BIG_BOMB_BAG", 2: "RG_BIGGEST_BOMB_BAG", 3: "RG_BIGGEST_BOMB_BAG",
                      4: "RG_BIGGEST_BOMB_BAG"}.get(self.CurrentUpgrade("UPG_BOMB_BAG"), "RG_NONE")
        elif rg == "RG_PROGRESSIVE_BOW":
            actual = {0: "RG_FAIRY_BOW", 1: "RG_BIG_QUIVER", 2: "RG_BIGGEST_QUIVER", 3: "RG_BIGGEST_QUIVER",
                      4: "RG_BIGGEST_QUIVER"}.get(self.CurrentUpgrade("UPG_QUIVER"), "RG_NONE")
        elif rg == "RG_PROGRESSIVE_SLINGSHOT":
            actual = {0: "RG_FAIRY_SLINGSHOT", 1: "RG_BIG_BULLET_BAG", 2: "RG_BIGGEST_BULLET_BAG",
                      3: "RG_BIGGEST_BULLET_BAG", 4: "RG_BIGGEST_BULLET_BAG"}.get(
                self.CurrentUpgrade("UPG_BULLET_BAG"), "RG_NONE")
        elif rg == "RG_PROGRESSIVE_OCARINA":
            actual = {"ITEM_NONE": "RG_FAIRY_OCARINA", "ITEM_OCARINA_FAIRY": "RG_OCARINA_OF_TIME",
                      "ITEM_OCARINA_TIME": "RG_OCARINA_OF_TIME"}.get(self.CurrentInventory("ITEM_OCARINA_FAIRY"),
                                                                     "RG_NONE")
        elif rg == "RG_PROGRESSIVE_HOOKSHOT":
            actual = {"ITEM_NONE": "RG_HOOKSHOT", "ITEM_HOOKSHOT": "RG_LONGSHOT",
                      "ITEM_LONGSHOT": "RG_LONGSHOT"}.get(self.CurrentInventory("ITEM_HOOKSHOT"), "RG_NONE")
        elif rg == "RG_PROGRESSIVE_STRENGTH":
            if not self.CheckRandoInf("RAND_INF_CAN_GRAB"):
                actual = "RG_POWER_BRACELET"
            else:
                actual = {0: "RG_GORONS_BRACELET", 1: "RG_SILVER_GAUNTLETS", 2: "RG_GOLDEN_GAUNTLETS",
                          3: "RG_GOLDEN_GAUNTLETS"}.get(self.CurrentUpgrade("UPG_STRENGTH"), "RG_NONE")
        elif rg == "RG_PROGRESSIVE_WALLET":
            if not self.CheckRandoInf("RAND_INF_HAS_WALLET"):
                actual = "RG_CHILD_WALLET"
            else:
                actual = {0: "RG_ADULT_WALLET", 1: "RG_GIANT_WALLET", 2: "RG_GIANT_WALLET", 3: "RG_GIANT_WALLET",
                          4: "RG_GIANT_WALLET"}.get(self.CurrentUpgrade("UPG_WALLET"), "RG_NONE")
        elif rg == "RG_PROGRESSIVE_SCALE":
            if not self.CheckRandoInf("RAND_INF_CAN_SWIM"):
                actual = "RG_BRONZE_SCALE"
            else:
                actual = {0: "RG_SILVER_SCALE", 1: "RG_GOLDEN_SCALE", 2: "RG_GOLDEN_SCALE"}.get(
                    self.CurrentUpgrade("UPG_SCALE"), "RG_NONE")
        elif rg == "RG_PROGRESSIVE_MAGIC_METER":
            actual = {0: "RG_MAGIC_SINGLE", 1: "RG_MAGIC_DOUBLE", 2: "RG_MAGIC_DOUBLE", 3: "RG_MAGIC_DOUBLE"}.get(
                sc.magicLevel, "RG_NONE")
        elif rg == "RG_PROGRESSIVE_GORONSWORD":
            actual = "RG_BIGGORON_SWORD" if self.CheckEquipment("EQUIP_FLAG_SWORD_BGS") else "RG_GIANTS_KNIFE"
        elif rg == "RG_PROGRESSIVE_BOMBCHU_BAG":
            actual = "RG_NONE"   # (RSK_BOMBCHU_BAG none)
        has_gi = "itemId" in it and it["itemId"] != "RG_PROGRESSIVE_BOMBCHU_BAG"
        if has_gi and actual == "RG_NONE":
            return it["itemId"], it["objectId"], it["modIndex"]
        if actual == "RG_NONE" and not has_gi:
            a = D.ITEMS["RG_NONE"]
            return a["itemId"], a["objectId"], a["modIndex"]
        a = D.ITEMS[actual]
        if "itemId" not in a:
            raise LogicError(f"GetGIEntry: {rg} resolves to {actual}, which has no GetItemEntry")
        return a["itemId"], a["objectId"], a["modIndex"]

    def _real_gi_is(self, rg, inf):
        itemId, _, modIndex = self.gi_entry(rg)
        return itemId == inf and modIndex == "MOD_RANDOMIZER"

    def ApplyItemEffect(self, item, state):
        """(item: the RG_* of SoH's Item&)"""
        randoGet = item
        it = D.ITEMS[randoGet]
        sc = self.mSaveContext
        objectId = self.gi_entry(randoGet)[1]
        if objectId == "OBJECT_GI_STICK":
            self.SetInventory("ITEM_STICK", "ITEM_STICK" if state else "ITEM_NONE")
        if objectId == "OBJECT_GI_NUTS":
            self.SetInventory("ITEM_NUT", "ITEM_NUT" if state else "ITEM_NONE")
        t = it["type"]
        step = 1 if state else -1
        if t == "ITEMTYPE_ITEM":
            r = randoGet
            if r in ("RG_STONE_OF_AGONY", "RG_GERUDO_MEMBERSHIP_CARD"):
                self.SetQuestItem(RANDO_GET_TO_QUEST_ITEM[r], state)
            elif r == "RG_WEIRD_EGG":
                self.SetRandoInf("RAND_INF_WEIRD_EGG", state)
            elif r == "RG_ZELDAS_LETTER":
                self.SetRandoInf("RAND_INF_ZELDAS_LETTER", state)
            elif r == "RG_DOUBLE_DEFENSE":
                sc.isDoubleDefenseAcquired = int(state)
            elif r == "RG_POCKET_EGG":
                self.SetRandoInf("RAND_INF_ADULT_TRADES_HAS_POCKET_EGG", state)
            elif r in _ADULT_TRADE:
                # (randoGet - RG_COJIRO + RAND_INF_ADULT_TRADES_HAS_COJIRO: the same order, see _ADULT_TRADE)
                self.SetRandoInf(_ADULT_TRADE[r], state)
            elif r == "RG_CLIMB":
                self.SetRandoInf("RAND_INF_CAN_CLIMB", state)
            elif r == "RG_CRAWL":
                self.SetRandoInf("RAND_INF_CAN_CRAWL", state)
            elif r == "RG_OPEN_CHEST":
                if self.ctx.GetOption("RSK_SHUFFLE_OPEN_CHEST").Is("RO_OPEN_CHEST_PROGRESSIVE"):
                    if (self.CheckRandoInf("RAND_INF_CAN_OPEN_CHEST") if state
                            else self.CheckRandoInf("RAND_INF_CAN_OPEN_LARGE_CHEST")):
                        self.SetRandoInf("RAND_INF_CAN_OPEN_LARGE_CHEST", state)
                    else:
                        self.SetRandoInf("RAND_INF_CAN_OPEN_CHEST", state)
                else:
                    self.SetRandoInf("RAND_INF_CAN_OPEN_CHEST", state)
                    self.SetRandoInf("RAND_INF_CAN_OPEN_LARGE_CHEST", state)
            elif r == "RG_PROGRESSIVE_HOOKSHOT":
                i = 0
                while i < 3:
                    if self.CurrentInventory("ITEM_HOOKSHOT") == HOOKSHOT_LOOKUP[i]:
                        break
                    i += 1
                n = min(max(i + step, 0), 2)
                self.SetInventory("ITEM_HOOKSHOT", HOOKSHOT_LOOKUP[n])
            elif r == "RG_PROGRESSIVE_STRENGTH":
                lvl = self.CurrentUpgrade("UPG_STRENGTH")
                if not self.CheckRandoInf("RAND_INF_CAN_GRAB") and state:
                    self.SetRandoInf("RAND_INF_CAN_GRAB", True)
                elif lvl == 0 and not state:
                    self.SetRandoInf("RAND_INF_CAN_GRAB", False)
                else:
                    self.SetUpgrade("UPG_STRENGTH", lvl + step)
            elif r in ("RG_PROGRESSIVE_BOMB_BAG", "RG_PROGRESSIVE_BOW", "RG_PROGRESSIVE_SLINGSHOT",
                       "RG_PROGRESSIVE_NUT_UPGRADE", "RG_PROGRESSIVE_STICK_UPGRADE"):
                inf, upg, item = _PROGRESSIVE_BAGS[r]
                if self._real_gi_is(r, inf):
                    self.SetRandoInf(RANDO_GET_TO_RAND_INF[inf], True)
                else:
                    lvl = self.CurrentUpgrade(upg)
                    if (lvl == 0 and state) or (lvl == 1 and not state):
                        self.SetInventory(item, item if state else "ITEM_NONE")
                    self.SetUpgrade(upg, lvl + step)
            elif r == "RG_PROGRESSIVE_WALLET":
                if self._real_gi_is(r, "RG_WALLET_INF"):
                    self.SetRandoInf("RAND_INF_HAS_INFINITE_MONEY", True)
                else:
                    lvl = self.CurrentUpgrade("UPG_WALLET")
                    if not self.CheckRandoInf("RAND_INF_HAS_WALLET") and state:
                        self.SetRandoInf("RAND_INF_HAS_WALLET", True)
                    elif lvl == 0 and not state:
                        self.SetRandoInf("RAND_INF_HAS_WALLET", False)
                    else:
                        self.SetUpgrade("UPG_WALLET", lvl + step)
            elif r == "RG_PROGRESSIVE_SCALE":
                lvl = self.CurrentUpgrade("UPG_SCALE")
                if not self.CheckRandoInf("RAND_INF_CAN_SWIM") and state:
                    self.SetRandoInf("RAND_INF_CAN_SWIM", True)
                elif lvl == 0 and not state:
                    self.SetRandoInf("RAND_INF_CAN_SWIM", False)
                else:
                    self.SetUpgrade("UPG_SCALE", lvl + step)
            elif r == "RG_PROGRESSIVE_BOMBCHU_BAG":
                if self._real_gi_is(r, "RG_BOMBCHU_INF"):
                    self.SetRandoInf("RAND_INF_HAS_INFINITE_BOMBCHUS", True)
                else:
                    self.SetInventory("ITEM_BOMBCHU", "ITEM_BOMBCHU" if state else "ITEM_NONE")
            elif r == "RG_PROGRESSIVE_GORONSWORD":
                if (self.CheckEquipment("EQUIP_FLAG_SWORD_BGS") if state else sc.bgsFlag):
                    sc.bgsFlag = int(state)
                elif state:
                    sc.equipment |= EQUIP_FLAG["EQUIP_FLAG_SWORD_BGS"]
                else:
                    sc.equipment &= ~EQUIP_FLAG["EQUIP_FLAG_SWORD_BGS"]
            elif r == "RG_PROGRESSIVE_MAGIC_METER":
                if self._real_gi_is(r, "RG_MAGIC_INF"):
                    self.SetRandoInf("RAND_INF_HAS_INFINITE_MAGIC_METER", True)
                else:
                    sc.magicLevel += step
            elif r == "RG_PROGRESSIVE_OCARINA":
                i = 0
                while i < 3:
                    if self.CurrentInventory("ITEM_OCARINA_FAIRY") == OCARINA_LOOKUP[i]:
                        break
                    i += 1
                i = min(max(i + step, 0), 2)
                self.SetInventory("ITEM_OCARINA_FAIRY", OCARINA_LOOKUP[i])
            elif r == "RG_HEART_CONTAINER":
                sc.healthCapacity = (sc.healthCapacity + 16 * step) & 0xFFFF
            elif r == "RG_PIECE_OF_HEART":
                sc.healthCapacity = (sc.healthCapacity + 4 * step) & 0xFFFF
            elif r in ("RG_BOOMERANG", "RG_LENS_OF_TRUTH", "RG_MEGATON_HAMMER", "RG_DINS_FIRE", "RG_FARORES_WIND",
                       "RG_NAYRUS_LOVE", "RG_FIRE_ARROWS", "RG_ICE_ARROWS", "RG_LIGHT_ARROWS"):
                item_id = self.gi_entry(r)[0]
                self.SetInventory(item_id, item_id if state else "ITEM_NONE")
            elif r in ("RG_MAGIC_BEAN", "RG_MAGIC_BEAN_PACK"):
                change = 1 if r == "RG_MAGIC_BEAN" else 10
                self.SetAmmo("ITEM_BEAN", self.GetAmmo("ITEM_BEAN") + change * step)
            elif r in _BOTTLE_ITEMS:
                # (the first empty of bottles 1-3, else bottle 4, which it overwrites; not undone by state false)
                slot = SLOT["SLOT_BOTTLE_1"]
                while slot != SLOT["SLOT_BOTTLE_4"]:
                    if sc.items[slot] == "ITEM_NONE":
                        break
                    slot += 1
                item_id = self.gi_entry(r)[0]
                if r in BOTTLE_RANDO_GET_TO_ITEM:
                    item_id = BOTTLE_RANDO_GET_TO_ITEM[r]
                if r == "RG_BOTTLE_WITH_BIG_POE":
                    self.BigPoes += 1
                sc.items[slot] = item_id
            elif r == "RG_RUTOS_LETTER":
                self.SetRandoInf("RAND_INF_OBTAINED_RUTOS_LETTER", state)
            elif r in _RAND_INF_ITEMS:
                self.SetRandoInf(RANDO_GET_TO_RAND_INF[r], state)
            elif r == "RG_TRIFORCE_PIECE":
                sc.triforcePiecesCollected += step
            elif r in ("RG_BOMBCHU_5", "RG_BOMBCHU_10", "RG_BOMBCHU_20"):
                if self.ctx.GetOption("RSK_BOMBCHU_BAG").Is("RO_BOMBCHU_BAG_NONE"):
                    self.SetInventory("ITEM_BOMBCHU", "ITEM_BOMBCHU" if state else "ITEM_NONE")
            # (default: break)
        elif t == "ITEMTYPE_EQUIP":
            r = randoGet
            # (finding a non-shop shield/tunic unlocks its matching shop copy when that gate is enabled)
            if r == "RG_DEKU_SHIELD":
                self.SetRandoInf("RAND_INF_HAS_FOUND_DEKU_SHIELD", state)
            elif r == "RG_HYLIAN_SHIELD":
                self.SetRandoInf("RAND_INF_HAS_FOUND_HYLIAN_SHIELD", state)
            elif r == "RG_GORON_TUNIC":
                self.SetRandoInf("RAND_INF_HAS_FOUND_GORON_TUNIC", state)
            elif r == "RG_ZORA_TUNIC":
                self.SetRandoInf("RAND_INF_HAS_FOUND_ZORA_TUNIC", state)
            if r in ("RG_DEKU_SHIELD", "RG_HYLIAN_SHIELD"):
                return
            flag = RANDO_GET_TO_EQUIP_FLAG.get(r)
            equipId = EQUIP_FLAG[flag] if flag else 0
            if not state:
                sc.equipment &= ~equipId
                if flag == "EQUIP_FLAG_SWORD_BGS" and r != "RG_GIANTS_KNIFE":
                    sc.bgsFlag = 0
            else:
                sc.equipment |= equipId
                if flag == "EQUIP_FLAG_SWORD_BGS" and r != "RG_GIANTS_KNIFE":
                    sc.bgsFlag = 1
        elif t in ("ITEMTYPE_DUNGEONREWARD", "ITEMTYPE_SONG"):
            self.SetQuestItem(RANDO_GET_TO_QUEST_ITEM[randoGet], state)
        elif t == "ITEMTYPE_MAP":
            self.SetDungeonItem("DUNGEON_MAP", RANDO_GET_TO_DUNGEON_SCENE[randoGet], state)
        elif t == "ITEMTYPE_COMPASS":
            self.SetDungeonItem("DUNGEON_COMPASS", RANDO_GET_TO_DUNGEON_SCENE[randoGet], state)
        elif t == "ITEMTYPE_BOSSKEY":
            self.SetDungeonItem("DUNGEON_KEY_BOSS", RANDO_GET_TO_DUNGEON_SCENE[randoGet], state)
        elif t == "ITEMTYPE_SILVER":
            raise LogicError(f"silver rupee items are not ported ({randoGet}): RSK_SHUFFLE_SILVER is off")
        elif t in ("ITEMTYPE_FORTRESS_SMALLKEY", "ITEMTYPE_SMALLKEY"):
            keyring = EV["RG_FOREST_TEMPLE_KEY_RING"] <= EV[randoGet] <= EV["RG_TREASURE_GAME_KEY_RING"]
            scene = RANDO_GET_TO_DUNGEON_SCENE[randoGet]
            count = self.GetSmallKeyCount(scene)
            if not state:
                count = 0 if keyring else count - 1
            else:
                count = 10 if keyring else count + 1
            self.SetSmallKeyCount(scene, count)
        elif t == "ITEMTYPE_TOKEN":
            sc.gsTokens += step
        elif t == "ITEMTYPE_EVENT":
            pass
        elif t in ("ITEMTYPE_DROP", "ITEMTYPE_REFILL", "ITEMTYPE_SHOP"):
            r = randoGet
            if r in ("RG_BUY_HYLIAN_SHIELD", "RG_BUY_DEKU_SHIELD", "RG_BUY_GORON_TUNIC", "RG_BUY_ZORA_TUNIC"):
                equipId = EQUIP_FLAG[RANDO_GET_TO_EQUIP_FLAG[r]]
                if not state:
                    sc.equipment &= ~equipId
                else:
                    sc.equipment |= equipId
            if r in ("RG_DEKU_NUTS_5", "RG_DEKU_NUTS_10", "RG_BUY_DEKU_NUTS_5", "RG_BUY_DEKU_NUTS_10"):
                self.SetInventory("ITEM_NUT", "ITEM_NUT" if state else "ITEM_NONE")
            elif r in ("RG_DEKU_STICK_1", "RG_BUY_DEKU_STICK_1"):
                self.SetInventory("ITEM_STICK", "ITEM_STICK" if state else "ITEM_NONE")
            elif r in ("RG_BUY_BOMBCHUS_10", "RG_BUY_BOMBCHUS_20"):
                if self.ctx.GetOption("RSK_BOMBCHU_BAG").Is("RO_BOMBCHU_BAG_NONE"):
                    self.SetInventory("ITEM_BOMBCHU", "ITEM_BOMBCHU" if state else "ITEM_NONE")
        else:
            raise LogicError(f"ApplyItemEffect: item type {t} of {randoGet}")

    def ApplyEffect(self, randoGet):
        """(Item::ApplyEffect) the item's effect, and its logic value set"""
        if not self.CalculatingAvailableChecks:
            self.ApplyItemEffect(randoGet, True)
        self.Set(D.ITEMS[randoGet]["logicVal"], True)

    def Reset(self, resetSaveContext=True):
        ctx = self.ctx
        if resetSaveContext:
            self.NewSaveContext()
        self.inLogic = set()
        if resetSaveContext:
            ocBtnShuffle = ctx.GetOption("RSK_SHUFFLE_OCARINA_BUTTONS").Is(True)
            for f in ("RAND_INF_HAS_OCARINA_A", "RAND_INF_HAS_OCARINA_C_UP", "RAND_INF_HAS_OCARINA_C_DOWN",
                      "RAND_INF_HAS_OCARINA_C_LEFT", "RAND_INF_HAS_OCARINA_C_RIGHT"):
                self.SetRandoInf(f, not ocBtnShuffle)
            self.SetUpgrade("UPG_STICKS", 0 if ctx.GetOption("RSK_SHUFFLE_DEKU_STICK_BAG").Is(True) else 1)
            self.SetUpgrade("UPG_NUTS", 0 if ctx.GetOption("RSK_SHUFFLE_DEKU_NUT_BAG").Is(True) else 1)
            if ctx.GetOption("RSK_SHUFFLE_SWIM").Is(False):
                self.SetRandoInf("RAND_INF_CAN_SWIM", True)
            if ctx.GetOption("RSK_SHUFFLE_GRAB").Is(False):
                self.SetRandoInf("RAND_INF_CAN_GRAB", True)
            if ctx.GetOption("RSK_SHUFFLE_CLIMB").Is(False):
                self.SetRandoInf("RAND_INF_CAN_CLIMB", True)
            if ctx.GetOption("RSK_SHUFFLE_CRAWL").Is(False):
                self.SetRandoInf("RAND_INF_CAN_CRAWL", True)
            if ctx.GetOption("RSK_SHUFFLE_OPEN_CHEST").Is(False):
                self.SetRandoInf("RAND_INF_CAN_OPEN_CHEST", True)
                self.SetRandoInf("RAND_INF_CAN_OPEN_LARGE_CHEST", True)
            if ctx.GetOption("RSK_SHUFFLE_SPEAK").Is(False):
                for f in ("RAND_INF_CAN_SPEAK_DEKU", "RAND_INF_CAN_SPEAK_GERUDO", "RAND_INF_CAN_SPEAK_GORON",
                          "RAND_INF_CAN_SPEAK_HYLIAN", "RAND_INF_CAN_SPEAK_KOKIRI", "RAND_INF_CAN_SPEAK_ZORA"):
                    self.SetRandoInf(f, True)
            if ctx.GetOption("RSK_SHUFFLE_CHILD_WALLET").Is(False):
                self.SetRandoInf("RAND_INF_HAS_WALLET", True)
            if ctx.GetOption("RSK_SHUFFLE_FISHING_POLE").Is(False):
                self.SetRandoInf("RAND_INF_FISHING_POLE_FOUND", True)
            if ctx.GetOption("RSK_SHUFFLE_BEAN_SOULS").Is(False):
                for soul in _BEAN_SOUL_OF_EVENT.values():   # (beanPatches' soulRandInf: every bean soul)
                    self.SetRandoInf(RANDO_GET_TO_RAND_INF[soul], True)
            # (if not keysanity, start with 1 logical key to account for automatically unlocking the basement door
            #  in vanilla FiT)
            if not self.IsFireLoopLocked() and ctx.GetDungeon("FIRE_TEMPLE").IsVanilla():
                self.SetSmallKeyCount("SCENE_FIRE_TEMPLE", 1)
        self.Bottles = 0
        self.NumBottles = 0
        self.IsChild = False
        self.IsAdult = False
        self.BigPoes = 0
        self.BaseHearts = ctx.GetOption("RSK_STARTING_HEARTS").Get() + 1
        self.AtDay = False
        self.AtNight = False
        if resetSaveContext:
            sc = self.GetSaveContext()
            sc.linkAge = int(not ctx.GetOption("RSK_SELECTED_STARTING_AGE").Get())
            sc.healthCapacity = self.BaseHearts * FULL_HEART_HEALTH
            sc.health = sc.healthCapacity
        self.CalculatingAvailableChecks = False


# ---- case tables of the switches above (logic.cpp)

_HAS_EXACT = {"RG_DINS_FIRE": "ITEM_DINS_FIRE", "RG_FARORES_WIND": "ITEM_FARORES_WIND",
              "RG_NAYRUS_LOVE": "ITEM_NAYRUS_LOVE", "RG_LENS_OF_TRUTH": "ITEM_LENS", "RG_FAIRY_BOW": "ITEM_BOW",
              "RG_MEGATON_HAMMER": "ITEM_HAMMER", "RG_LONGSHOT": "ITEM_LONGSHOT", "RG_FIRE_ARROWS": "ITEM_ARROW_FIRE",
              "RG_ICE_ARROWS": "ITEM_ARROW_ICE", "RG_LIGHT_ARROWS": "ITEM_ARROW_LIGHT",
              "RG_FAIRY_SLINGSHOT": "ITEM_SLINGSHOT", "RG_BOOMERANG": "ITEM_BOOMERANG"}
_HAS_QUEST = {"RG_ZELDAS_LULLABY", "RG_EPONAS_SONG", "RG_SARIAS_SONG", "RG_SUNS_SONG", "RG_SONG_OF_TIME",
              "RG_SONG_OF_STORMS", "RG_MINUET_OF_FOREST", "RG_BOLERO_OF_FIRE", "RG_SERENADE_OF_WATER",
              "RG_REQUIEM_OF_SPIRIT", "RG_NOCTURNE_OF_SHADOW", "RG_PRELUDE_OF_LIGHT", "RG_KOKIRI_EMERALD",
              "RG_GORON_RUBY", "RG_ZORA_SAPPHIRE", "RG_FOREST_MEDALLION", "RG_FIRE_MEDALLION", "RG_WATER_MEDALLION",
              "RG_SPIRIT_MEDALLION", "RG_SHADOW_MEDALLION", "RG_LIGHT_MEDALLION", "RG_STONE_OF_AGONY",
              "RG_GERUDO_MEMBERSHIP_CARD"}
_HAS_RAND_INF = {"RG_POWER_BRACELET", "RG_CHILD_WALLET", "RG_FISHING_POLE", "RG_SCARECROWS_SONG", "RG_BRONZE_SCALE",
                 "RG_CLIMB", "RG_CRAWL", "RG_OPEN_CHEST", "RG_ZELDAS_LETTER", "RG_WEIRD_EGG", "RG_GREG_RUPEE",
                 "RG_COJIRO", "RG_ODD_MUSHROOM", "RG_ODD_POTION", "RG_POACHERS_SAW", "RG_BROKEN_SWORD",
                 "RG_PRESCRIPTION", "RG_EYEBALL_FROG", "RG_EYEDROPS", "RG_CLAIM_CHECK", "RG_SPEAK_DEKU",
                 "RG_SPEAK_GERUDO", "RG_SPEAK_GORON", "RG_SPEAK_HYLIAN", "RG_SPEAK_KOKIRI", "RG_SPEAK_ZORA",
                 "RG_OCARINA_A_BUTTON", "RG_OCARINA_C_LEFT_BUTTON", "RG_OCARINA_C_RIGHT_BUTTON",
                 "RG_OCARINA_C_DOWN_BUTTON", "RG_OCARINA_C_UP_BUTTON", "RG_DEATH_MOUNTAIN_CRATER_BEAN_SOUL",
                 "RG_DEATH_MOUNTAIN_TRAIL_BEAN_SOUL", "RG_DESERT_COLOSSUS_BEAN_SOUL", "RG_GERUDO_VALLEY_BEAN_SOUL",
                 "RG_GRAVEYARD_BEAN_SOUL", "RG_KOKIRI_FOREST_BEAN_SOUL", "RG_LAKE_HYLIA_BEAN_SOUL",
                 "RG_LOST_WOODS_BRIDGE_BEAN_SOUL", "RG_LOST_WOODS_BEAN_SOUL", "RG_ZORAS_RIVER_BEAN_SOUL",
                 "RG_SKELETON_KEY", "RG_RUTOS_LETTER"}
_BOSS_SOULS = {"RG_GOHMA_SOUL", "RG_KING_DODONGO_SOUL", "RG_BARINADE_SOUL", "RG_PHANTOM_GANON_SOUL",
               "RG_VOLVAGIA_SOUL", "RG_MORPHA_SOUL", "RG_BONGO_BONGO_SOUL", "RG_TWINROVA_SOUL"}
_OVERWORLD_KEYS = {"RG_GUARD_HOUSE_KEY", "RG_MARKET_BAZAAR_KEY", "RG_MARKET_POTION_SHOP_KEY", "RG_MASK_SHOP_KEY",
                   "RG_MARKET_SHOOTING_GALLERY_KEY", "RG_BOMBCHU_BOWLING_KEY", "RG_TREASURE_CHEST_GAME_BUILDING_KEY",
                   "RG_BOMBCHU_SHOP_KEY", "RG_RICHARDS_HOUSE_KEY", "RG_ALLEY_HOUSE_KEY", "RG_KAK_BAZAAR_KEY",
                   "RG_KAK_POTION_SHOP_KEY", "RG_BOSS_HOUSE_KEY", "RG_GRANNYS_POTION_SHOP_KEY",
                   "RG_SKULLTULA_HOUSE_KEY", "RG_IMPAS_HOUSE_KEY", "RG_WINDMILL_KEY", "RG_KAK_SHOOTING_GALLERY_KEY",
                   "RG_DAMPES_HUT_KEY", "RG_TALONS_HOUSE_KEY", "RG_STABLES_KEY", "RG_BACK_TOWER_KEY",
                   "RG_HYLIA_LAB_KEY", "RG_FISHING_HOLE_KEY"}
_BOSS_KEYS = {"RG_FOREST_TEMPLE_BOSS_KEY", "RG_FIRE_TEMPLE_BOSS_KEY", "RG_WATER_TEMPLE_BOSS_KEY",
              "RG_SPIRIT_TEMPLE_BOSS_KEY", "RG_SHADOW_TEMPLE_BOSS_KEY", "RG_GANONS_CASTLE_BOSS_KEY"}
_MAPS = {"RG_DEKU_TREE_MAP", "RG_DODONGOS_CAVERN_MAP", "RG_JABU_JABUS_BELLY_MAP", "RG_FOREST_TEMPLE_MAP",
         "RG_FIRE_TEMPLE_MAP", "RG_WATER_TEMPLE_MAP", "RG_SPIRIT_TEMPLE_MAP", "RG_SHADOW_TEMPLE_MAP",
         "RG_BOTTOM_OF_THE_WELL_MAP", "RG_ICE_CAVERN_MAP"}
_COMPASSES = {m.replace("_MAP", "_COMPASS") for m in _MAPS}
_SILVER_ORDER = ["RG_SHADOW_SILVER_BLADES", "RG_SHADOW_SILVER_PIT", "RG_SHADOW_SILVER_SPIKES",
                 "RG_SPIRIT_SILVER_CHILD", "RG_SPIRIT_SILVER_SUN", "RG_SPIRIT_SILVER_BOULDERS", "RG_BOTW_SILVER",
                 "RG_ICE_CAVERN_SILVER_BLADES", "RG_ICE_CAVERN_SILVER_BLOCK", "RG_GTG_SILVER_SLOPE",
                 "RG_GTG_SILVER_LAVA", "RG_GTG_SILVER_WATER", "RG_GANONS_CASTLE_SILVER_LIGHT",
                 "RG_GANONS_CASTLE_SILVER_FOREST", "RG_GANONS_CASTLE_SILVER_FIRE", "RG_GANONS_CASTLE_SILVER_SPIRIT",
                 "RG_DODONGOS_CAVERN_MQ_SILVER", "RG_SHADOW_MQ_SILVER_INVISIBLE_BLADES", "RG_SPIRIT_MQ_SILVER_LOBBY",
                 "RG_SPIRIT_MQ_SILVER_BIG_WALL", "RG_GANONS_CASTLE_MQ_SILVER_WATER",
                 "RG_GANONS_CASTLE_MQ_SILVER_SHADOW"]
_SILVER_RUPEES = set(_SILVER_ORDER)
_LOGIC_BY_VALUE = {v: k for k, v in D.ENUMS["LogicVal"].items()}
_RG_BY_VALUE = {v: k for k, v in D.ENUMS["RandomizerGet"].items()}
# (LOGIC_SHADOW_SILVER_BLADES + (itemName - RG_SHADOW_SILVER_BLADES))
_SILVER_LOGIC = {rg: _LOGIC_BY_VALUE[EV["LOGIC_SHADOW_SILVER_BLADES"] + EV[rg] - EV["RG_SHADOW_SILVER_BLADES"]]
                 for rg in _SILVER_ORDER}
_BOTTLES = {"RG_BOTTLE_WITH_BIG_POE", "RG_BOTTLE_WITH_BLUE_FIRE", "RG_BOTTLE_WITH_BLUE_POTION",
            "RG_BOTTLE_WITH_BUGS", "RG_BOTTLE_WITH_FAIRY", "RG_BOTTLE_WITH_FISH", "RG_BOTTLE_WITH_GREEN_POTION",
            "RG_BOTTLE_WITH_MILK", "RG_BOTTLE_WITH_POE", "RG_BOTTLE_WITH_RED_POTION", "RG_EMPTY_BOTTLE"}
_BOTTLE_ITEMS = _BOTTLES
_USE_ALWAYS = {"RG_DEKU_SHIELD", "RG_HYLIAN_SHIELD", "RG_MIRROR_SHIELD", "RG_GORON_TUNIC", "RG_ZORA_TUNIC",
               "RG_IRON_BOOTS", "RG_HOVER_BOOTS", "RG_MAGIC_SINGLE", "RG_SILVER_GAUNTLETS", "RG_GOLDEN_GAUNTLETS",
               "RG_ZELDAS_LULLABY", "RG_EPONAS_SONG", "RG_PRELUDE_OF_LIGHT", "RG_SARIAS_SONG", "RG_SONG_OF_TIME",
               "RG_BOLERO_OF_FIRE", "RG_REQUIEM_OF_SPIRIT", "RG_SONG_OF_STORMS", "RG_MINUET_OF_FOREST",
               "RG_SERENADE_OF_WATER", "RG_NOCTURNE_OF_SHADOW", "RG_CRAWL"}
_SCENES_ANY = {"SCENE_DEKU_TREE", "SCENE_DODONGOS_CAVERN", "SCENE_JABU_JABU", "SCENE_FOREST_TEMPLE",
               "SCENE_FIRE_TEMPLE", "SCENE_WATER_TEMPLE", "SCENE_SPIRIT_TEMPLE", "SCENE_SHADOW_TEMPLE",
               "SCENE_BOTTOM_OF_THE_WELL", "SCENE_ICE_CAVERN", "SCENE_ID_MAX"}
_SCENES_NO_FW = {"SCENE_HYRULE_FIELD", "SCENE_GANONS_TOWER", "SCENE_GERUDO_TRAINING_GROUND", "SCENE_THIEVES_HIDEOUT",
                 "SCENE_INSIDE_GANONS_CASTLE", "SCENE_GREAT_FAIRYS_FOUNTAIN_MAGIC", "SCENE_FAIRYS_FOUNTAIN",
                 "SCENE_GREAT_FAIRYS_FOUNTAIN_SPELLS", "SCENE_GROTTOS", "SCENE_GRAVE_WITH_FAIRYS_FOUNTAIN",
                 "SCENE_REDEAD_GRAVE", "SCENE_ROYAL_FAMILYS_TOMB", "SCENE_KAKARIKO_VILLAGE", "SCENE_GRAVEYARD",
                 "SCENE_ZORAS_RIVER", "SCENE_KOKIRI_FOREST", "SCENE_SACRED_FOREST_MEADOW", "SCENE_LAKE_HYLIA",
                 "SCENE_ZORAS_DOMAIN", "SCENE_ZORAS_FOUNTAIN", "SCENE_GERUDO_VALLEY", "SCENE_LOST_WOODS",
                 "SCENE_DESERT_COLOSSUS", "SCENE_GERUDOS_FORTRESS", "SCENE_HAUNTED_WASTELAND", "SCENE_HYRULE_CASTLE",
                 "SCENE_DEATH_MOUNTAIN_TRAIL", "SCENE_DEATH_MOUNTAIN_CRATER", "SCENE_GORON_CITY",
                 "SCENE_LON_LON_RANCH", "SCENE_OUTSIDE_GANONS_CASTLE"}
_SCENES_BOSS = {"SCENE_DEKU_TREE_BOSS", "SCENE_DODONGOS_CAVERN_BOSS", "SCENE_JABU_JABU_BOSS",
                "SCENE_FOREST_TEMPLE_BOSS", "SCENE_FIRE_TEMPLE_BOSS", "SCENE_WATER_TEMPLE_BOSS",
                "SCENE_SPIRIT_TEMPLE_BOSS", "SCENE_SHADOW_TEMPLE_BOSS", "SCENE_GANONDORF_BOSS", "SCENE_GANON_BOSS"}
_SCENES_TOWN = {"SCENE_MARKET_ENTRANCE_DAY", "SCENE_MARKET_ENTRANCE_NIGHT", "SCENE_MARKET_ENTRANCE_RUINS",
                "SCENE_BACK_ALLEY_DAY", "SCENE_BACK_ALLEY_NIGHT", "SCENE_MARKET_DAY", "SCENE_MARKET_NIGHT",
                "SCENE_MARKET_RUINS", "SCENE_TEMPLE_OF_TIME_EXTERIOR_DAY", "SCENE_TEMPLE_OF_TIME_EXTERIOR_NIGHT",
                "SCENE_TEMPLE_OF_TIME_EXTERIOR_RUINS", "SCENE_KNOW_IT_ALL_BROS_HOUSE", "SCENE_TWINS_HOUSE",
                "SCENE_MIDOS_HOUSE", "SCENE_SARIAS_HOUSE", "SCENE_KAKARIKO_CENTER_GUEST_HOUSE",
                "SCENE_BACK_ALLEY_HOUSE", "SCENE_BAZAAR", "SCENE_KOKIRI_SHOP", "SCENE_GORON_SHOP", "SCENE_ZORA_SHOP",
                "SCENE_POTION_SHOP_KAKARIKO", "SCENE_BOMBCHU_SHOP", "SCENE_HAPPY_MASK_SHOP", "SCENE_LINKS_HOUSE",
                "SCENE_DOG_LADY_HOUSE", "SCENE_STABLE", "SCENE_IMPAS_HOUSE", "SCENE_LAKESIDE_LABORATORY",
                "SCENE_CARPENTERS_TENT", "SCENE_GRAVEKEEPERS_HUT", "SCENE_TEMPLE_OF_TIME", "SCENE_LON_LON_BUILDINGS",
                "SCENE_HOUSE_OF_SKULLTULA"}
_SCENES_NO_B = {"SCENE_TREASURE_BOX_SHOP", "SCENE_KNOW_IT_ALL_BROS_HOUSE", "SCENE_TWINS_HOUSE", "SCENE_MIDOS_HOUSE",
                "SCENE_SARIAS_HOUSE", "SCENE_KAKARIKO_CENTER_GUEST_HOUSE", "SCENE_BACK_ALLEY_HOUSE", "SCENE_BAZAAR",
                "SCENE_KOKIRI_SHOP", "SCENE_GORON_SHOP", "SCENE_ZORA_SHOP", "SCENE_POTION_SHOP_KAKARIKO",
                "SCENE_BOMBCHU_SHOP", "SCENE_HAPPY_MASK_SHOP", "SCENE_LINKS_HOUSE", "SCENE_DOG_LADY_HOUSE",
                "SCENE_STABLE", "SCENE_IMPAS_HOUSE", "SCENE_LAKESIDE_LABORATORY", "SCENE_CARPENTERS_TENT",
                "SCENE_GRAVEKEEPERS_HUT", "SCENE_SHOOTING_GALLERY", "SCENE_BOMBCHU_BOWLING_ALLEY",
                "SCENE_POTION_SHOP_GRANNY", "SCENE_CASTLE_COURTYARD_GUARDS_DAY", "SCENE_CASTLE_COURTYARD_GUARDS_NIGHT",
                "SCENE_FISHING_POND"}
_ADULT_ITEMS = {"RG_FAIRY_BOW", "RG_MEGATON_HAMMER", "RG_IRON_BOOTS", "RG_HOVER_BOOTS", "RG_HOOKSHOT",
                "RG_LONGSHOT", "RG_GORON_TUNIC", "RG_ZORA_TUNIC", "RG_MIRROR_SHIELD", "RG_MASTER_SWORD",
                "RG_PROGRESSIVE_GORONSWORD", "RG_GIANTS_KNIFE", "RG_BIGGORON_SWORD", "RG_SILVER_GAUNTLETS",
                "RG_GOLDEN_GAUNTLETS", "RG_POCKET_EGG", "RG_COJIRO", "RG_ODD_MUSHROOM", "RG_ODD_POTION",
                "RG_POACHERS_SAW", "RG_BROKEN_SWORD", "RG_PRESCRIPTION", "RG_EYEBALL_FROG", "RG_EYEDROPS",
                "RG_CLAIM_CHECK"}
_PASS_ALWAYS = {"RE_GOLD_SKULLTULA", "RE_GOHMA_LARVA", "RE_LIZALFOS", "RE_DODONGO", "RE_MAD_SCRUB", "RE_KEESE",
                "RE_FIRE_KEESE", "RE_BLUE_BUBBLE", "RE_DEAD_HAND", "RE_DEKU_BABA", "RE_WITHERED_DEKU_BABA",
                "RE_STALFOS", "RE_FLARE_DANCER", "RE_WOLFOS", "RE_WHITE_WOLFOS", "RE_FLOORMASTER", "RE_MEG",
                "RE_ARMOS", "RE_FREEZARD", "RE_SPIKE", "RE_DARK_LINK", "RE_ANUBIS", "RE_WALLMASTER",
                "RE_PURPLE_LEEVER", "RE_OCTOROK"}
_AVOID_ALWAYS = {"RE_GOLD_SKULLTULA", "RE_GOHMA_LARVA", "RE_LIZALFOS", "RE_DODONGO", "RE_BIG_SKULLTULA",
                 "RE_DEAD_HAND", "RE_DEKU_BABA", "RE_WITHERED_DEKU_BABA", "RE_LIKE_LIKE", "RE_STALFOS",
                 "RE_IRON_KNUCKLE", "RE_FLARE_DANCER", "RE_WOLFOS", "RE_WHITE_WOLFOS", "RE_FLOORMASTER", "RE_REDEAD",
                 "RE_MEG", "RE_ARMOS", "RE_GREEN_BUBBLE", "RE_FREEZARD", "RE_SHELL_BLADE", "RE_SPIKE", "RE_BIG_OCTO",
                 "RE_GIBDO", "RE_DARK_LINK", "RE_WALLMASTER", "RE_ANUBIS", "RE_PURPLE_LEEVER", "RE_WALLTULA"}
# (ApplyItemEffect: randoGet - RG_COJIRO + RAND_INF_ADULT_TRADES_HAS_COJIRO)
_RAND_INF_BY_VALUE = {v: k for k, v in D.ENUMS["RandomizerInf"].items()}
_ADULT_TRADE = {_r: _RAND_INF_BY_VALUE[EV[_r] - EV["RG_COJIRO"] + EV["RAND_INF_ADULT_TRADES_HAS_COJIRO"]]
                for _r in ("RG_COJIRO", "RG_ODD_MUSHROOM", "RG_ODD_POTION", "RG_POACHERS_SAW", "RG_BROKEN_SWORD",
                           "RG_PRESCRIPTION", "RG_EYEBALL_FROG", "RG_EYEDROPS", "RG_CLAIM_CHECK")}
_RAND_INF_ITEMS = {
    "RG_DEATH_MOUNTAIN_CRATER_BEAN_SOUL", "RG_DEATH_MOUNTAIN_TRAIL_BEAN_SOUL", "RG_DESERT_COLOSSUS_BEAN_SOUL",
    "RG_GERUDO_VALLEY_BEAN_SOUL", "RG_GRAVEYARD_BEAN_SOUL", "RG_KOKIRI_FOREST_BEAN_SOUL", "RG_LAKE_HYLIA_BEAN_SOUL",
    "RG_LOST_WOODS_BRIDGE_BEAN_SOUL", "RG_LOST_WOODS_BEAN_SOUL", "RG_ZORAS_RIVER_BEAN_SOUL", "RG_GOHMA_SOUL",
    "RG_KING_DODONGO_SOUL", "RG_BARINADE_SOUL", "RG_PHANTOM_GANON_SOUL", "RG_VOLVAGIA_SOUL", "RG_MORPHA_SOUL",
    "RG_BONGO_BONGO_SOUL", "RG_TWINROVA_SOUL", "RG_GANON_SOUL", "RG_OCARINA_A_BUTTON", "RG_OCARINA_C_UP_BUTTON",
    "RG_OCARINA_C_DOWN_BUTTON", "RG_OCARINA_C_LEFT_BUTTON", "RG_OCARINA_C_RIGHT_BUTTON", "RG_KEATON_MASK",
    "RG_SKULL_MASK", "RG_SPOOKY_MASK", "RG_BUNNY_HOOD", "RG_GORON_MASK", "RG_ZORA_MASK", "RG_GERUDO_MASK",
    "RG_MASK_OF_TRUTH", "RG_GREG_RUPEE", "RG_SPEAK_DEKU", "RG_SPEAK_GERUDO", "RG_SPEAK_GORON", "RG_SPEAK_HYLIAN",
    "RG_SPEAK_KOKIRI", "RG_SPEAK_ZORA", "RG_FISHING_POLE", "RG_SCARECROWS_SONG"} | _OVERWORLD_KEYS
_PROGRESSIVE_BAGS = {
    "RG_PROGRESSIVE_BOMB_BAG": ("RG_BOMB_BAG_INF", "UPG_BOMB_BAG", "ITEM_BOMB"),
    "RG_PROGRESSIVE_BOW": ("RG_QUIVER_INF", "UPG_QUIVER", "ITEM_BOW"),
    "RG_PROGRESSIVE_SLINGSHOT": ("RG_BULLET_BAG_INF", "UPG_BULLET_BAG", "ITEM_SLINGSHOT"),
    "RG_PROGRESSIVE_NUT_UPGRADE": ("RG_NUT_UPGRADE_INF", "UPG_NUTS", "ITEM_NUT"),
    "RG_PROGRESSIVE_STICK_UPGRADE": ("RG_STICK_UPGRADE_INF", "UPG_STICKS", "ITEM_STICK"),
}
# (BeanPlanted: beanEvent - LOGIC_PLANT_DEATH_MOUNTAIN_CRATER_BEAN + RG_DEATH_MOUNTAIN_CRATER_BEAN_SOUL)
_BEAN_SOUL_OF_EVENT = {}
for _ev, _v in D.ENUMS["LogicVal"].items():
    _off = _v - EV["LOGIC_PLANT_DEATH_MOUNTAIN_CRATER_BEAN"]
    if 0 <= _off < 10:
        _BEAN_SOUL_OF_EVENT[_ev] = _RG_BY_VALUE[EV["RG_DEATH_MOUNTAIN_CRATER_BEAN_SOUL"] + _off]
