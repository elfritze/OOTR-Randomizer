"""The remake's chest items (their actor names, as a chest's Drop__DropActor) and the SoH item (RG_*) each counts as in logic.

The game's dungeon items (Item_Dungeon_SmallKey, _BossKey, _Map, _Compass) are one actor for every dungeon: each counts for
the dungeon it is picked up in. The pool names each by its dungeon instead (Item_SmallKey_Forest: rando.dungeon_items, an
item of its own that works anywhere); generate writes the game's own actor where that one does the same (dungeon_form)."""
from . import dungeon_items as DI

# (actor: SoH item; amounts from each actor's PouchContentParam: BundleActorNum)
ITEMS = {
    "Item_Sword_Kokiri": "RG_KOKIRI_SWORD",
    "Item_Range_SlingShot": "RG_PROGRESSIVE_SLINGSHOT",
    "Item_Boomerang": "RG_BOOMERANG",
    "Item_BombBag_Small": "RG_PROGRESSIVE_BOMB_BAG",
    "Item_Hookshot": "RG_PROGRESSIVE_HOOKSHOT",
    "Item_Longshot": "RG_PROGRESSIVE_HOOKSHOT",
    "Item_Range_Bow": "RG_PROGRESSIVE_BOW",
    "Item_Hammer": "RG_MEGATON_HAMMER",
    "Item_HeavyBoot": "RG_IRON_BOOTS",
    "Item_HoverBoot": "RG_HOVER_BOOTS",
    "Item_GlassTruth": "RG_LENS_OF_TRUTH",
    "Item_Gauntlet_Goron": "RG_PROGRESSIVE_STRENGTH",   # (the Goron's Bracelet: Darunia's, in the pool with gifts)
    "Item_Gauntlet_Silver": "RG_PROGRESSIVE_STRENGTH",
    "Item_Gauntlet_Gold": "RG_PROGRESSIVE_STRENGTH",
    "Item_Shield_Mirror": "RG_MIRROR_SHIELD",
    "Item_Arrow_Ice": "RG_ICE_ARROWS",
    "TBox_Shield_Deku": "RG_DEKU_SHIELD",
    "TBox_Shield_Hylian": "RG_HYLIAN_SHIELD",
    "Obj_Heart_Piece": "RG_PIECE_OF_HEART",
    "TBox_Rupee_Green": "RG_GREEN_RUPEE",
    "TBox_Rupee_Blue": "RG_BLUE_RUPEE",
    "TBox_Rupee_Red": "RG_RED_RUPEE",
    "TBox_Rupee_Purple": "RG_PURPLE_RUPEE",
    "TBox_Rupee_Gold": "RG_HUGE_RUPEE",
    "Item_BombBundle_Small": "RG_BOMBS_5",
    "Item_BombchuBundle_Small": "RG_BOMBCHU_5",
    "TBox_ArrowBundle_Medium": "RG_ARROWS_5",
    "TBox_ArrowBundle_Large": "RG_ARROWS_10",
    "TBox_DekuNutBundle": "RG_DEKU_NUTS_5",   # (3 nuts: SoH has no smaller pack)
    "Item_DekuStickBundle_Small": "RG_DEKU_STICK_1",   # (3 sticks)
    "Tbox_MagicJar_Large": "RG_NONE",   # (a magic refill: nothing in logic)
    "Item_ScrubBusinessSeed": "RG_NONE",   # (the remake's own collectible, up to 30: nothing in SoH's logic)
    # (what NPCs give and what lies in the world: data/gifts.json)
    "Obj_Heart_Container": "RG_HEART_CONTAINER",
    "Item_BombBag_Medium": "RG_PROGRESSIVE_BOMB_BAG", "Item_BombBag_Large": "RG_PROGRESSIVE_BOMB_BAG",
    "Item_BulletBag_Medium": "RG_PROGRESSIVE_SLINGSHOT", "Item_BulletBag_Large": "RG_PROGRESSIVE_SLINGSHOT",
    "Item_Quiver_Medium": "RG_PROGRESSIVE_BOW", "Item_Quiver_Large": "RG_PROGRESSIVE_BOW",
    "Item_StickBag_Medium": "RG_PROGRESSIVE_STICK_UPGRADE", "Item_StickBag_Large": "RG_PROGRESSIVE_STICK_UPGRADE",
    "Item_NutBag_Medium": "RG_PROGRESSIVE_NUT_UPGRADE", "Item_NutBag_Large": "RG_PROGRESSIVE_NUT_UPGRADE",
    "Item_Wallet_Medium": "RG_PROGRESSIVE_WALLET", "Item_Wallet_Large": "RG_PROGRESSIVE_WALLET",
    "Item_Scale_Silver": "RG_PROGRESSIVE_SCALE", "Item_Scale_Gold": "RG_PROGRESSIVE_SCALE",
    "Item_Bottle": "RG_EMPTY_BOTTLE",
    "Item_Bottle_Milk": "RG_BOTTLE_WITH_MILK",
    "Item_AgonyStone": "RG_STONE_OF_AGONY",
    "Item_BombchuBundle_Medium": "RG_BOMBCHU_10", "Item_BombchuBundle_Large": "RG_BOMBCHU_20",
    "Obj_Armor_Zora": "RG_ZORA_TUNIC",
    # (the dungeon rewards, as their scenes' GetPouchContent windows give them: shuffled among themselves only)
    "Item_Stone_Forest": "RG_KOKIRI_EMERALD", "Item_Stone_Fire": "RG_GORON_RUBY", "Item_Stone_Water": "RG_ZORA_SAPPHIRE",
    "Item_Medal_Forest": "RG_FOREST_MEDALLION", "Item_Medal_Fire": "RG_FIRE_MEDALLION",
    "Item_Medal_Water": "RG_WATER_MEDALLION", "Item_Medal_Spirit": "RG_SPIRIT_MEDALLION",
    "Item_Medal_Shadow": "RG_SHADOW_MEDALLION", "Item_Medal_Light": "RG_LIGHT_MEDALLION",
    # (quest items: in the pool with settings shuffle_quest_items)
    "Item_ZeldaLetter": "RG_ZELDAS_LETTER", "Item_Arrow_Light": "RG_LIGHT_ARROWS",
    "Item_Arrow_Fire": "RG_FIRE_ARROWS",   # (with settings shuffle_lake_fire_arrows: the lake's sun spot)
    "Item_Token_Gold": "RG_GOLD_SKULLTULA_TOKEN",   # (with settings shuffle_tokens: the Gold Skulltulas' drops)
    "Item_Ocarina_Fairy": "RG_PROGRESSIVE_OCARINA",   # (with settings shuffle_fairy_ocarina; the Ocarina of Time stays)
    # (the Great Fairies' gifts: in the pool with settings shuffle_great_fairies)
    "Item_DinFire": "RG_DINS_FIRE", "Item_FaroreWind": "RG_FARORES_WIND", "Item_NayruLove": "RG_NAYRUS_LOVE",
    "Item_FairyBless_MP": "RG_PROGRESSIVE_MAGIC_METER", "Item_FairyBless_MPDouble": "RG_PROGRESSIVE_MAGIC_METER",
    "Item_FairyBless_DefenseDouble": "RG_DOUBLE_DEFENSE",
    # (the songs: the remake's song items, as chests, gifts and pickups give them, with Sheik's harp for a model)
    "Item_Melody_ZeldaLullaby": "RG_ZELDAS_LULLABY", "Item_Melody_EponaSong": "RG_EPONAS_SONG",
    "Item_Melody_SariaSong": "RG_SARIAS_SONG", "Item_Melody_SunSong": "RG_SUNS_SONG", "Item_Melody_TimeSong": "RG_SONG_OF_TIME",
    "Item_Melody_StormSong": "RG_SONG_OF_STORMS", "Item_Melody_ForestMinuet": "RG_MINUET_OF_FOREST",
    "Item_Melody_FireBolero": "RG_BOLERO_OF_FIRE", "Item_Melody_WaterSerenade": "RG_SERENADE_OF_WATER",
    "Item_Melody_SpiritRequiem": "RG_REQUIEM_OF_SPIRIT", "Item_Melody_ShadowNocturne": "RG_NOCTURNE_OF_SHADOW",
    "Item_Melody_LightPrelude": "RG_PRELUDE_OF_LIGHT",
}

# Upgrades the remake has as separate items, each setting its capacity outright (PouchActorInfo AfterExpansionMaxNum: a
# Medium bomb bag got after the Large one makes it 30 again). Logic counts each group as one progressive SoH item, so the fill
# places "one of the group" and the actors are chosen once the seed is made: the group's spots in playthrough order get its
# tiers in order (the earliest gets the Bow, the next quivers), the last tier for any spare. (generate.assign_tiers)
TIERS = (
    ("Item_BombBag_Small", "Item_BombBag_Medium", "Item_BombBag_Large"),
    ("Item_Range_SlingShot", "Item_BulletBag_Medium", "Item_BulletBag_Large"),
    ("Item_Range_Bow", "Item_Quiver_Medium", "Item_Quiver_Large"),
    ("Item_StickBag_Medium", "Item_StickBag_Large"),
    ("Item_NutBag_Medium", "Item_NutBag_Large"),
    ("Item_Wallet_Medium", "Item_Wallet_Large"),
    ("Item_Scale_Silver", "Item_Scale_Gold"),
    ("Item_FairyBless_MP", "Item_FairyBless_MPDouble"),   # (the magic meter, then its double)
)
TIER_OF = {a: g for g in TIERS for a in g}

# Where each item can go. A chest gives any item actor its Drop__DropActor names (proven for Item_*, Obj_Heart_Piece, the
# chests' own TBox_ rupees and ammunition); an NPC's gift event names Item_* and Obj_ pickups (rupees, Heart Pieces, shields,
# tunics: the game's own gifts); a loose spot holds an Obj_ pickup, or the pickup made for an Item_ (rando.pickups).
# Ammunition and the remake's small refills stay in chests (no gift or loose form of their bundles is known); dungeon items
# stay in chests (their keys are forward-filled there); a Heart Container stays loose or in a chest (no NPC gives one).
# (chest form: gift and loose forms)
OBJ_FORM = {"TBox_Rupee_Green": "Obj_Rupee_Green", "TBox_Rupee_Blue": "Obj_Rupee_Blue", "TBox_Rupee_Red": "Obj_Rupee_Red",
            "TBox_Rupee_Purple": "Obj_Rupee_Purple", "TBox_Rupee_Gold": "Obj_Rupee_Gold",
            "TBox_Shield_Deku": "Obj_Shield_Deku", "TBox_Shield_Hylian": "Obj_Shield_Hylian",
            "Item_Dungeon_SmallKey": "Obj_Dungeon_SmallKey",   # (a freestanding key: the game's loose key)
            "Item_Token_Gold": "Obj_Token_Gold"}   # (a token lying in the world, or a Gold Skulltula's own drop)
CHEST_ONLY = {"Item_BombBundle_Small", "Item_BombchuBundle_Small", "TBox_ArrowBundle_Medium", "TBox_ArrowBundle_Large",
              "TBox_DekuNutBundle", "Item_DekuStickBundle_Small", "Tbox_MagicJar_Large", "Item_ScrubBusinessSeed"}
NOT_GIFT = {"Obj_Heart_Container"}
NOT_CHEST = {"Obj_Armor_Zora"}
# (a shop's shelf, rando.shops: an Item_ actor but these, or one of SHOP_ALSO. Not the ocarinas (their get pose crashed in
#  chests), the songs, the bottles (the shop's own bottle display), the token, the ammunition bundles (CHEST_ONLY; a shop
#  refuses what the pouch is full of); the tunics and the Deku and Hylian Shields are TBox_/Obj_ actors, not taken)
NOT_SHOP = {"Item_Ocarina_Fairy", "Item_Ocarina_Time", "Item_Token_Gold"}
SHOP_ALSO = {"Obj_Heart_Piece", "Obj_Heart_Container", "TBox_Rupee_Green", "TBox_Rupee_Blue", "TBox_Rupee_Red",
             "TBox_Rupee_Purple", "TBox_Rupee_Gold"}   # (its chest form is not known: the remake's Zora Tunic only comes from King Zora and a shop)


# Checks giving their item by a silent pouch add (PouchSystemActor.EventTriggerAddOrRemovePouchContent: proven for Item_
# actors, the starting bags and Darunia's bracelet) or a cutscene's GetPouchContent window (the rewards' and Zelda's Light
# Arrows' way, known for Item_ actors only): an Item_ actor only, no song, no dungeon item.
LAKE_SUN = "RC_LH_SUN"   # (the Fire Arrows' spot: an Item_ made a pickup only, the scene's actor renamed to it)
POUCH_ADD_CHECKS = {"RC_GC_DARUNIAS_JOY", "RC_TOT_LIGHT_ARROWS_CUTSCENE", "RC_LW_GIFT_FROM_SARIA"}
# The dungeon rewards and the checks giving them (the bosses' and Rauru's scenes): each only with the other (SoH's End of
# Dungeon), when settings shuffle_dungeon_rewards puts them in the pool.
REWARDS = {"Item_Stone_Forest", "Item_Stone_Fire", "Item_Stone_Water", "Item_Medal_Forest", "Item_Medal_Fire",
           "Item_Medal_Water", "Item_Medal_Spirit", "Item_Medal_Shadow", "Item_Medal_Light"}
REWARD_CHECKS = {"RC_QUEEN_GOHMA", "RC_KING_DODONGO", "RC_BARINADE", "RC_PHANTOM_GANON", "RC_VOLVAGIA", "RC_MORPHA",
                 "RC_TWINROVA", "RC_BONGO_BONGO", "RC_GIFT_FROM_RAURU"}


# The ocarinas are the accessory Link plays, not an item he holds up: their packs have no Item_EventObject_Base parent, get
# pose or animation, so the item get pose of chests and NPCs' gifts crashed the game (OotrR issue #15: the rolling Goron,
# a chest; its item_forms.OCARINAS). The game hands them out only in its two scenes, by the get display without a pose:
# there, and lying in the world (a pickup's own get), only.
OCARINAS = {"Item_Ocarina_Fairy", "Item_Ocarina_Time"}
OCARINA_CHECKS = {"RC_LW_GIFT_FROM_SARIA", "RC_HF_OCARINA_OF_TIME_ITEM"}


def fits(actor, location_id, kind):
    """allowed(), and what a check giving by a silent add can give"""
    if not allowed(actor, kind):
        return False
    if actor in OCARINAS:
        return kind in ("loose", "skulltula") or location_id in OCARINA_CHECKS
    if (actor in REWARDS) != (location_id in REWARD_CHECKS):
        return False
    if location_id == LAKE_SUN:   # (our pickup in its place, as the sun's scene plays it: rando.patches.lake_sun)
        return actor.startswith("Item_") and not dungeon_bound(actor)
    if location_id in POUCH_ADD_CHECKS:
        given = form(actor, kind)
        return given.startswith("Item_") and not given.startswith("Item_Melody_") and not dungeon_bound(actor)
    return True


def allowed(actor, kind):
    """can this item (as the pool names it: its chest form) go in a location of this kind ("chest", "gift", "loose",
    "skulltula": a Gold Skulltula's drop, a pickup built on the token as a loose one; "shop": a shelf, rando.shops)?"""
    if kind == "skulltula":
        kind = "loose"
    if kind == "chest":
        return actor not in NOT_CHEST
    if dungeon_bound(actor):   # (in chests and lying in the world: a gift may not end in the get flow crediting it)
        return kind == "loose"
    if kind == "shop":
        return actor in SHOP_ALSO or (actor.startswith("Item_") and actor not in CHEST_ONLY and actor not in NOT_SHOP and
                                      not actor.startswith(("Item_Melody_", "Item_Bottle")))
    if actor in CHEST_ONLY:
        return False
    if kind == "gift":
        return actor not in NOT_GIFT
    return kind == "loose"


def form(actor, kind):
    """the actor a location of this kind is written with for the item (a chest's TBox_ rupee is an Obj_ rupee elsewhere)"""
    if not allowed(actor, kind):
        raise ValueError("%s cannot go in a %s" % (actor, kind))
    return actor if kind in ("chest", "shop") else OBJ_FORM.get(actor, actor)


def canonical(actor):
    """the pool's name for an item a gift or loose spot gives (its chest form)"""
    back = {v: k for k, v in OBJ_FORM.items()}
    return back.get(actor, actor)

# (remake map: SoH dungeon name, as in RG_<name>_SMALL_KEY)
DUNGEONS = {
    "InsideTheDekuTree": "DEKU_TREE", "DodongoCavern": "DODONGOS_CAVERN", "InsideJabuJabuBelly": "JABU_JABUS_BELLY",
    "ForestTemple": "FOREST_TEMPLE", "FireTemple": "FIRE_TEMPLE", "WaterTemple": "WATER_TEMPLE",
    "ShadowTemple": "SHADOW_TEMPLE", "SpiritTemple": "SPIRIT_TEMPLE", "BottomOfTheWell": "BOTTOM_OF_THE_WELL",
    "IceCavern": "ICE_CAVERN", "GerudoTrainingGround": "GERUDO_TRAINING_GROUND", "InsideGanonCastle": "GANONS_CASTLE",
}
DUNGEON_ITEMS = {"Item_Dungeon_SmallKey": "SMALL_KEY", "Item_Dungeon_BossKey": "BOSS_KEY", "Item_Dungeon_Map": "MAP",
                 "Item_Dungeon_Compass": "COMPASS"}
# (what only a big chest gives: the big chests' flow, Dm_SY_Treasurebox, hands the dungeon's map, compass and boss key
#  with its own steps (EventGetDungeonMap / Compass / BossKey, by EventQueryTreasureBoxIsDungeonCommonItemInside); the
#  small chests' flow, Dm_SY_TreasureboxSmall, knows only the small key: from a small chest those three showed and were
#  never had (2026-11-14: the Shadow Temple's boss key, from its Falling Spikes Lower Chest; its boss door stayed shut)
BIG_CHEST_ONLY = {"Item_Dungeon_BossKey", "Item_Dungeon_Map", "Item_Dungeon_Compass"}

# Pairs where getting the second before the first is not known to work in the remake (two actors, not one progressive
# item): the fill keeps the second unreachable without the first.
ORDERED = (("Item_Hookshot", "Item_Longshot"), ("Item_Gauntlet_Goron", "Item_Gauntlet_Silver"),
           ("Item_Gauntlet_Silver", "Item_Gauntlet_Gold"))
# The same with the first from a check the randomizer leaves as it is (SoH counts these as one progressive item: had first,
# the second would count as the first in logic): Darunia's Goron's Bracelet before the Silver Gauntlets, when gifts are not
# shuffled (shuffled, the bracelet is in the pool: ORDERED).
ORDERED_FIXED = (("RC_GC_DARUNIAS_JOY", "Item_Gauntlet_Silver"),)

# Ammunition the game gives without the container it goes in (its PouchContentParam's SmallBagActor): a chest's bombs before
# any bomb bag left Link unable to use them (seen in game, 2026-11-12). Each is placed only where the container (from
# anywhere: the chest's bag, the rolling Goron's) is needed to get to it. (actor: the SoH item that is its container)
NEEDS_CONTAINER = {
    "Item_BombBundle_Small": "RG_PROGRESSIVE_BOMB_BAG",
    "Item_BombchuBundle_Small": "RG_PROGRESSIVE_BOMB_BAG",   # (Bombchus count against the bomb bag too: MaxNumGameData Bomb)
    "TBox_ArrowBundle_Medium": "RG_PROGRESSIVE_BOW",
    "TBox_ArrowBundle_Large": "RG_PROGRESSIVE_BOW",
}

# Chests that get one of a few items, for a room a player without them would be locked in. (location: the items, one of them
# drawn for it.) None now. The Deku Tree's slingshot room had one (Slingshot or Boomerang: its way out is a ladder its eye
# switch drops, InsideTheDekuTree_Level_Room_C_Prefab), but the remake autosaves before that room, so a player locked in
# loads that save; SoH's and OoTR's randomizers put anything there too. Dropped at the user's request (2026-11-12).
ONE_OF = {}


def soh_item(actor, remake_map):
    """the SoH item a chest's actor counts as, picked up in this map"""
    own = DI.parse(actor)
    if own:
        return "RG_%s_%s" % (DUNGEONS[own[1]], DUNGEON_ITEMS[own[0]])
    if actor in DUNGEON_ITEMS:
        if remake_map not in DUNGEONS:
            raise ValueError("%s outside a dungeon (%s)" % (actor, remake_map))
        return "RG_%s_%s" % (DUNGEONS[remake_map], DUNGEON_ITEMS[actor])
    return ITEMS[actor]


def dungeon_bound(actor):
    return actor in DUNGEON_ITEMS or DI.parse(actor) is not None


def dungeon_item(actor, remake_map=None):
    """(the game's actor, dungeon) of a dungeon item: an own one wherever it is, the game's one by the map it is in; or
    None"""
    own = DI.parse(actor)
    if own:
        return own
    if actor in DUNGEON_ITEMS and remake_map in DUNGEONS:
        return actor, remake_map
    return None


def own_actor(actor, remake_map):
    """the pool's name of the dungeon item a location of this map holds as the game has it"""
    return DI.actor_name(actor, remake_map) if actor in DUNGEON_ITEMS else actor


def loose_form(actor, remake_map):
    """the actor a loose spot of this map is written with for a pool item: a dungeon's small key lying in its own dungeon
    is the game's loose key; any other dungeon item, its own item (a pickup is made of it)"""
    own = DI.parse(actor)
    if own and own == ("Item_Dungeon_SmallKey", remake_map):
        return OBJ_FORM["Item_Dungeon_SmallKey"]
    return form(actor, "loose")


def dungeon_form(actor, remake_map, small_chest):
    """the actor a chest of this map is written with for a pool item: a dungeon's own item is the game's one in that
    dungeon's chests (a small key in any; the map, compass and boss key in a big chest: the small chests' flow never gives
    those), and its own item anywhere else"""
    own = DI.parse(actor)
    if own and own[1] == remake_map and (own[0] == "Item_Dungeon_SmallKey" or not small_chest):
        return own[0]
    return actor
