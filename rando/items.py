"""The remake's chest items (their actor names, as a chest's Drop__DropActor) and the SoH item (RG_*) each counts as in logic.

A dungeon item (Item_Dungeon_SmallKey, _BossKey, _Map, _Compass) is one actor for every dungeon: it counts for the dungeon it
is picked up in. So it can only be shuffled within its own dungeon, and its SoH item depends on that dungeon (DUNGEONS)."""

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
}

# (remake map: SoH dungeon name, as in RG_<name>_SMALL_KEY)
DUNGEONS = {
    "InsideTheDekuTree": "DEKU_TREE", "DodongoCavern": "DODONGOS_CAVERN", "InsideJabuJabuBelly": "JABU_JABUS_BELLY",
    "ForestTemple": "FOREST_TEMPLE", "FireTemple": "FIRE_TEMPLE", "WaterTemple": "WATER_TEMPLE",
    "ShadowTemple": "SHADOW_TEMPLE", "SpiritTemple": "SPIRIT_TEMPLE", "BottomOfTheWell": "BOTTOM_OF_THE_WELL",
    "IceCavern": "ICE_CAVERN", "GerudoTrainingGround": "GERUDO_TRAINING_GROUND", "InsideGanonCastle": "GANONS_CASTLE",
}
DUNGEON_ITEMS = {"Item_Dungeon_SmallKey": "SMALL_KEY", "Item_Dungeon_BossKey": "BOSS_KEY", "Item_Dungeon_Map": "MAP",
                 "Item_Dungeon_Compass": "COMPASS"}

# Pairs where getting the second before the first is not known to work in the remake (two actors, not one progressive
# item): the fill keeps the second unreachable without the first.
ORDERED = (("Item_Hookshot", "Item_Longshot"), ("Item_Gauntlet_Silver", "Item_Gauntlet_Gold"))
# The same with the first from a check the randomizer leaves as it is (SoH counts these as one progressive item: had first,
# the second would count as the first in logic): Darunia's Goron's Bracelet before the Silver Gauntlets.
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
    if actor in DUNGEON_ITEMS:
        if remake_map not in DUNGEONS:
            raise ValueError("%s outside a dungeon (%s)" % (actor, remake_map))
        return "RG_%s_%s" % (DUNGEONS[remake_map], DUNGEON_ITEMS[actor])
    return ITEMS[actor]


def dungeon_bound(actor):
    return actor in DUNGEON_ITEMS
