"""Shops (SoH: Shopsanity): some of each shop's shelves sell an item of the pool, once.

The remake's 8 shops are SoH's 8 (Kokiri, the Market's bazaar, potion and Bombchu shops, Kakariko's bazaar and potion shop,
Zora's Domain, Goron City), each with 8 shelves: map actors Shop_* (Dynamic ShopItemIndex 1-7, the 8th with none: 0), each
the target of its shopkeeper's ForSale link, the shopkeeper's ShopParam GoodsList[ShopItemIndex] what it sells. The mask
shop is not one. A shelf's slot is the same in a shop's child and adult maps (and its other copies: the Kokiri shop's short
stock, Kakariko's and Zora's Domain's second adult maps): one check, one item, bought once in any of them.

A shuffled shelf, as the OotrR randomizer makes them (MIT; item_forms.build_pack, repeatable_adapter; seen in its game,
2026-11-13 and 14: the item shown with its name and price, bought once, "Sold Out" after it and after a reload):
* a new actor (Shop_Rando_<shop><n>) built on the arrows' shelf (Shop_ArrowBundle_01) with the item's model, name and
  pouch content (its PouchActor the item), its game parameters merged, our price;
* its own copy of the shelf's AI (AI/Shop_Item_Base.root.ainb) with nodes added (the ainb library): the purchase sets a
  saved flag (RandoShop_<RC>), and the shelf reads that flag as its sold out state (model hidden, the linked board shown);
  bought but the shop's own stock back (a reload), it deletes itself, so it is never sold twice;
* the shopkeeper sells that slot once (StockNum 1: the shop itself refuses a second sale on that visit), at the shelf's
  price (PriceOffset 0);
* a native Shop_Board_SoldOut behind it, linked to it (Reference), as the Kokiri shop's short stock has them.
The map keeps the shelf's Hash, place and links (Gyaml only), as for the other checks.

Which shelves: SoH's way (fill.cpp): N per shop (or a random number), taken in OoTR's order of SoH's item numbers (7, 5, 8,
6, 3, 1, 4, 2). Each remake slot is given a SoH number so that the shelves logic needs (the shields, the tunics, Deku nuts
and sticks, Bombchus: SoH's RG_BUY_ items its rules read) come last; the slots not shuffled keep their item, which logic
counts as SoH's RG_BUY_ item at that check, at the remake's price. The potion shop's bug shelf has its own condition and is
never shuffled (the 8th place). The Kokiri shop sells its whole stock from the start (as OotrR: SoH's logic sells it from
the start; the remake shows a short stock before the Deku Tree's second step).

Prices (SoH's choices): Vanilla (the remake's price of the shelf's own item), Cheap balanced, Balanced (SoH's tables),
Affordable (Balanced, lowered to the least of the wallet it needs). Logic counts a price by the remake's wallets (200, 500,
999: rando.logic's SoH capacities are 99, 200, 500), so logic_price() gives the SoH price needing the same wallet.

What a shelf may sell (items.allowed, kind "shop"): an Item_ actor (not a song, an ocarina, a bottle, a dungeon item, a
token or the ammunition bundles), a Heart Piece or Container, a rupee. Not the shields and tunics: the shop's flow treats
those names apart (DisplayShop: "already have one", a child refused a tunic); not tested yet for the others."""
import copy
import hashlib
import math
import os
import re
import struct
import uuid

from . import pickups
from .formats import byml, sarc

# (shop code, SoH's checks, the remake's folder, the shopkeeper's actor without its age, the remake slots in the order they
#  are shuffled: first the ones logic needs least)
SHOPS = (
    ("KF", "RC_KF_SHOP_ITEM_%d", "KokiriForest", "Npc_Kokiri_001_Shop", (0, 1, 4, 3, 5, 2, 7, 6)),
    ("MB", "RC_MARKET_BAZAAR_ITEM_%d", "Market", "Npc_Hylia_018_Shop", (0, 1, 2, 3, 4, 7, 5, 6)),
    ("MP", "RC_MARKET_POTION_SHOP_ITEM_%d", "Market", "Npc_Hylia_020_Shop", (2, 5, 1, 0, 3, 7, 4, 6)),
    ("MC", "RC_MARKET_BOMBCHU_SHOP_ITEM_%d", "Market", "Npc_Hylia_021_Shop", (0, 1, 2, 3, 5, 7, 6, 4)),
    ("KB", "RC_KAK_BAZAAR_ITEM_%d", "KakarikoVillage", "Npc_Hylia_018_Shop", (0, 1, 2, 3, 4, 7, 5, 6)),
    ("KP", "RC_KAK_POTION_SHOP_ITEM_%d", "KakarikoVillage", "Npc_Hylia_020_Shop", (2, 5, 1, 0, 3, 7, 4, 6)),
    ("ZD", "RC_ZD_SHOP_ITEM_%d", "ZoraDomain", "Npc_Zora_011_Shop", (0, 1, 2, 7, 6, 5, 4, 3)),
    ("GC", "RC_GC_SHOP_ITEM_%d", "GoronCity", "Npc_Goron_011_Shop", (0, 1, 2, 7, 6, 5, 4, 3)),
)
SOH_ORDER = (7, 5, 8, 6, 3, 1, 4, 2)   # (SoH's fill.cpp indices: shopsanity 1 takes item 7, 2 takes 7 and 5...)
MOST = 7   # (SoH: 8 only with no logic, one refill left in each shop)
# (the remake's shelves as SoH's shop items: what logic counts at a slot left as it is)
VANILLA_RG = {
    "Shop_Heart": "RG_BUY_HEART", "Shop_MagicJar_Small": "RG_BUY_GREEN_POTION",
    "Shop_DekuSeedBundle_01": "RG_BUY_DEKU_SEEDS_30", "Shop_DekuSeedBundle_02": "RG_BUY_DEKU_SEEDS_30",
    "Shop_DekuNutBundle_01": "RG_BUY_DEKU_NUTS_5", "Shop_DekuNutBundle_02": "RG_BUY_DEKU_NUTS_10",
    "Shop_DekuStick": "RG_BUY_DEKU_STICK_1", "Shop_DekuStickBundle_Medium": "RG_BUY_DEKU_STICK_1",
    "Shop_Weapon_Shield_Deku": "RG_BUY_DEKU_SHIELD", "Shop_Weapon_Shield_Hylian": "RG_BUY_HYLIAN_SHIELD",
    "Shop_Armor_Goron": "RG_BUY_GORON_TUNIC", "Shop_Armor_Zora": "RG_BUY_ZORA_TUNIC",
    "Shop_Bottle_RedPotion": "RG_BUY_RED_POTION_30", "Shop_Bottle_GreenPotion": "RG_BUY_GREEN_POTION",
    "Shop_Bottle_HalfMilk": "RG_BUY_RED_POTION_30",   # (SoH sells no milk: a bottle refill all the same)
    "Shop_Bottle_Fairy": "RG_BUY_FAIRYS_SPIRIT", "Shop_Bottle_BlueFire": "RG_BUY_BLUE_FIRE", "Shop_Bottle_Poe": "RG_BUY_POE",
    "Shop_Bottle_Bug": "RG_BUY_BOTTLE_BUG", "Shop_Bottle_Fish": "RG_BUY_FISH",
    "Shop_ArrowBundle_01": "RG_BUY_ARROWS_10", "Shop_ArrowBundle_02": "RG_BUY_ARROWS_30",
    "Shop_ArrowBundle_03": "RG_BUY_ARROWS_50",
    "Shop_BombBundle_01": "RG_BUY_BOMBS_525", "Shop_BombBundle_02": "RG_BUY_BOMBS_10", "Shop_BombBundle_03": "RG_BUY_BOMBS_20",
    "Shop_BombBundle_04": "RG_BUY_BOMBS_30",
    "Shop_BombchuBundle_01": "RG_BUY_BOMBCHUS_10", "Shop_BombchuBundle_02": "RG_BUY_BOMBCHUS_20",
    "Shop_BombchuBundle_03": "RG_BUY_BOMBCHUS_10", "Shop_BombchuBundle_04": "RG_BUY_BOMBCHUS_10",
    "Shop_BombchuBundle_05": "RG_BUY_BOMBCHUS_10", "Shop_BombchuBundle_06": "RG_BUY_BOMBCHUS_10",
    "Shop_BombchuBundle_07": "RG_BUY_BOMBCHUS_20", "Shop_BombchuBundle_08": "RG_BUY_BOMBCHUS_20",
}
# (each shelf by what it sells, for names a player can find)
SHELF_NAME = {
    "Shop_Heart": "Recovery Heart", "Shop_MagicJar_Small": "Magic Jar", "Shop_DekuSeedBundle_01": "Deku Seeds (30)",
    "Shop_DekuSeedBundle_02": "Deku Seeds (10)", "Shop_DekuNutBundle_01": "Deku Nuts (5)",
    "Shop_DekuNutBundle_02": "Deku Nuts (10)", "Shop_DekuStick": "Deku Stick", "Shop_DekuStickBundle_Medium": "Deku Sticks (5)",
    "Shop_Weapon_Shield_Deku": "Deku Shield", "Shop_Weapon_Shield_Hylian": "Hylian Shield", "Shop_Armor_Goron": "Goron Tunic",
    "Shop_Armor_Zora": "Zora Tunic", "Shop_Bottle_RedPotion": "Red Potion", "Shop_Bottle_GreenPotion": "Green Potion",
    "Shop_Bottle_HalfMilk": "Milk", "Shop_Bottle_Fairy": "Fairy", "Shop_Bottle_BlueFire": "Blue Fire", "Shop_Bottle_Poe": "Poe",
    "Shop_Bottle_Bug": "Bugs", "Shop_Bottle_Fish": "Fish", "Shop_ArrowBundle_01": "Arrows (10)",
    "Shop_ArrowBundle_02": "Arrows (30)", "Shop_ArrowBundle_03": "Arrows (50)", "Shop_BombBundle_01": "Bombs (5)",
    "Shop_BombBundle_02": "Bombs (10)", "Shop_BombBundle_03": "Bombs (20)", "Shop_BombBundle_04": "Bombs (30)",
    "Shop_BombchuBundle_01": "Bombchus (10)", "Shop_BombchuBundle_02": "Bombchus (20)", "Shop_BombchuBundle_03": "Bombchu (1)",
    "Shop_BombchuBundle_04": "Bombchus (3)", "Shop_BombchuBundle_05": "Bombchus (5)", "Shop_BombchuBundle_06": "Bombchus (8)",
    "Shop_BombchuBundle_07": "Bombchus (15)", "Shop_BombchuBundle_08": "Bombchus (30)",
}
assert set(SHELF_NAME) == set(VANILLA_RG)
# (what the pool gets for each shuffled shelf: SoH's extra rupees with shopsanity, 10 red, 10 purple, 6 huge for 32)
JUNK = ("TBox_Rupee_Red", "TBox_Rupee_Purple", "TBox_Rupee_Red", "TBox_Rupee_Purple", "TBox_Rupee_Gold")

TEMPLATE = "Shop_ArrowBundle_01"
PREFIX = "Shop_Rando_"
FLAG = "RandoShop_%s"
AI_MEMBER = "AI/Shop_Item_Base.root.ainb"
TOKEN = "Obj_Token_Gold"   # (its ActorGameDataSetting: NoRespawn, as OotrR's shelves have it)
SOLD_OUT = "Shop_Board_SoldOut"
BOARD_BACK = 0.25   # (the game's sold out boards stand about this far behind their shelf)
FROM_ITEM = ("ModelInfoRef", "AnimationRef", "ActorNameRef", "ASRef")
MODEL_KEYS = ("FmdbName", "ModelProjectName", "ModelAabbMax", "ModelAabbMin", "ModelVariationFmabName",
              "AnimationResources", "ASInfoAutoPlayMaterials", "ELinkUserName")
GPT = "GameParameterTableRef"
KOKIRI = "KokiriForest"
KOKIRI_FLAG = "Meet_DekuTree_IsAfter_Step02_Exp"   # (the Kokiri shop's full stock: after the Deku Tree's second step)
KOKIRI_SELLERS = ("Npc_Kokiri_001_Shop_Child", "Npc_Kokiri_001_Shop_Child_ShortStock", "Npc_Kokiri_001_Shop_Adult")
AGE_FLAG = "Sequence_IsChildhood"
SHOP_FOLDERS = sorted({s[2] for s in SHOPS})
PRICES = ("vanilla", "cheap_balanced", "balanced", "affordable")


def pack_path(actor):
    return "Pack/Actor/%s.pack.zs" % actor


def seller_base(gyaml):
    return re.sub(r"_(Child|Adult)(_ShortStock)?$", "", gyaml)


def shop_param_files(files):
    return sorted(k for k in files if k.startswith("Component/ShopParam/") and k.endswith(".bgyml"))


class Slot:
    """one shelf of a shop: rc (SoH's check), code (the shop's), slot (ShopItemIndex), shelf (the game's actor),
    copies [(map file, Hash)], sellers {shopkeeper actor}, price (the remake's), rg (SoH's RG_BUY_ item), order (its place
    in the shop's shuffling order: 0 first), folder"""

    def __init__(self, **kw):
        self.__dict__.update(kw)

    @property
    def name(self):
        return "%s: %s, the %s shelf" % (AREA[self.code], SHOP_NAME[self.code], SHELF_NAME[self.shelf])

    @property
    def number(self):
        return int(self.rc.rsplit("_", 1)[1])

    @property
    def actor(self):
        return "%s%s%d" % (PREFIX, self.code, self.number)

    @property
    def flag(self):
        return FLAG % self.rc


AREA = {"KF": "Kokiri Forest", "MB": "Market", "MP": "Market", "MC": "Market", "KB": "Kakariko Village",
        "KP": "Kakariko Village", "ZD": "Zora's Domain", "GC": "Goron City"}
SHOP_NAME = {"KF": "Kokiri Shop", "MB": "Bazaar", "MP": "Potion Shop", "MC": "Bombchu Shop", "KB": "Bazaar",
             "KP": "Potion Shop", "ZD": "Zora Shop", "GC": "Goron Shop"}


def scan(romfs, codec, read=None):
    """[Slot] of the 8 shops, 64, read from the maps and the shopkeepers' packs (read(rel): the file as the mod has it)"""
    read = read or (lambda rel: codec.read(os.path.join(romfs, *rel.split("/"))))
    by_shop = {(s[2], s[3]): s for s in SHOPS}
    found = {}   # ((code, slot) -> {"shelf", "copies", "sellers"})
    for folder in SHOP_FOLDERS:
        d = os.path.join(romfs, "Banc", folder)
        for f in sorted(os.listdir(d)):
            if not f.endswith(".bcett.byml.zs"):
                continue
            rel = "Banc/%s/%s" % (folder, f)
            root, _ = byml.read(read(rel))
            actors = root.get("Actors", [])
            by_hash = {int(a["Hash"]): a for a in actors if "Hash" in a}
            for a in actors:
                links = [l for l in a.get("Links", []) if l.get("Name") == "ForSale"]
                if not links:
                    continue
                shop = by_shop.get((folder, seller_base(a["Gyaml"])))
                if shop is None:
                    continue   # (the mask shop)
                for link in links:
                    shelf = by_hash[int(link["Dst"])]
                    slot = (shelf.get("Dynamic") or {}).get("ShopItemIndex", 0)
                    e = found.setdefault((shop[0], slot), {"shelf": shelf["Gyaml"], "copies": [], "sellers": set(),
                                                           "presence": set()})
                    if e["shelf"] != shelf["Gyaml"]:
                        raise ValueError("%s slot %d: %s and %s" % (shop[0], slot, e["shelf"], shelf["Gyaml"]))
                    e["copies"].append((rel, int(shelf["Hash"])))
                    e["sellers"].add(a["Gyaml"])
                    p = shelf.get("Presence")
                    if p and p.get("FlagName") != KOKIRI_FLAG:
                        e["presence"].add(p["FlagName"])
    if len(found) != 8 * len(SHOPS):
        raise ValueError("shops: %d shelves found, %d expected" % (len(found), 8 * len(SHOPS)))
    goods = {}   # (seller -> GoodsList, from its pack's first ShopParam)
    rows = {r["__RowId"]: r for r in byml.read(read(pickups.POUCH_ACTOR_INFO))[0]}
    slots = []
    for code, rc_form, folder, _, order in SHOPS:
        if sorted(order) != list(range(8)):
            raise ValueError("%s: order %s" % (code, order))
        for pos, slot in enumerate(order):
            e = found[(code, slot)]
            offset = 0
            for seller in sorted(e["sellers"]):
                if seller not in goods:
                    files = sarc.read(read(pack_path(seller)))
                    goods[seller] = byml.read(files[shop_param_files(files)[-1]])[0]["GoodsList"]
                good = goods[seller][slot]
                if not good["Actor"].endswith("/%s.engine__actor__ActorParam.gyml" % e["shelf"]):
                    raise ValueError("%s slot %d: %s sells %s, the map %s" % (code, slot, seller, good["Actor"], e["shelf"]))
                offset = min(offset, good.get("PriceOffset", 0))
            slots.append(Slot(rc=rc_form % SOH_ORDER[pos], code=code, slot=slot, shelf=e["shelf"],
                              copies=sorted(e["copies"]), sellers=sorted(e["sellers"]), folder=folder,
                              price=rows[e["shelf"]]["BuyingPrice"] + offset, rg=VANILLA_RG[e["shelf"]], order=pos,
                              conditional=bool(e["presence"])))
    for s in slots:
        if s.conditional and s.order < MOST:
            raise ValueError("%s: a shelf under its own condition would be shuffled" % s.rc)
    return slots


def count_for(choice, rng):
    """how many shelves of a shop a setting shuffles"""
    if choice == "off":
        return 0
    if choice == "random":
        return rng.randint(1, MOST)
    return int(choice)


# (SoH's price tables, shops.cpp: a beta distribution's cumulative probabilities, prices in steps of 5)
BALANCED = (
    0.005326994, 0.014908518, 0.027114719, 0.041315285, 0.057136304, 0.074325887, 0.092667151, 0.112002061, 0.132198214,
    0.153125390, 0.174696150, 0.196810540, 0.219388148, 0.242361379, 0.265657012, 0.289205134, 0.312970402, 0.336877590,
    0.360881110, 0.384932772, 0.408976198, 0.432982176, 0.456902494, 0.480686053, 0.504313389, 0.527746488, 0.550938554,
    0.573856910, 0.596465330, 0.618736235, 0.640646600, 0.662162782, 0.683240432, 0.703859801, 0.724001242, 0.743631336,
    0.762722631, 0.781259986, 0.799198449, 0.816521905, 0.833208595, 0.849243398, 0.864579161, 0.879211177, 0.893112051,
    0.906263928, 0.918639420, 0.930222611, 0.940985829, 0.950914731, 0.959992180, 0.968187000, 0.975495390, 0.981884488,
    0.987344345, 0.991851853, 0.995389113, 0.997937921, 0.999481947, 1.000000000)
CHEAP = (0.097500187, 0.190002748, 0.277509301, 0.360018376, 0.437522571, 0.510021715, 0.577520272, 0.640029304,
         0.697527584, 0.750024535, 0.797518749, 0.840011707, 0.877508776, 0.910010904, 0.937504342, 0.960004661,
         0.977502132, 0.989998967, 0.997500116, 1.000000000)
LEAST = 5   # (no free shelf: a price of 0 was never seen in the remake's shops)
WALLETS = (200, 500, 999)   # (the remake's: Link's own, then Item_Wallet_Medium's and Item_Wallet_Large's)
SOH_WALLETS = (99, 200, 500)   # (rando.logic's GetWalletCapacity for the same three)


def _table(rng, table):
    r = rng.random()
    return next((i * 5 for i, p in enumerate(table) if r < p), 150)


def price_for(slot, choice, rng):
    """a shuffled shelf's price (rupees, as the game asks it)"""
    if choice == "vanilla":
        return max(LEAST, slot.price)
    if choice == "cheap_balanced":
        return max(LEAST, _table(rng, CHEAP))
    p = max(LEAST, _table(rng, BALANCED))
    if choice == "affordable":   # (SoH's Affordable: the least price needing the same wallet)
        return LEAST if p <= WALLETS[0] else WALLETS[0] + 5 if p <= WALLETS[1] else WALLETS[1] + 5
    return p


def logic_price(price):
    """the price as rando.logic counts it: the SoH price needing the wallet the remake needs for it"""
    for remake, soh in zip(WALLETS, SOH_WALLETS):
        if price <= remake:
            return min(price, soh)
    raise ValueError("price %d: more than the largest wallet" % price)


# ---- the shelf's AI (OotrR's repeatable_adapter.instrument_shop_ai, MIT, seen in game)

def _guid(text):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "hookshot-rando/" + text))


def _default(name, value):
    return {"Name": name, "Default Value": value, "Node Index": -1, "Output Index": 0, "Flags": ["Uses Default"]}


def _retarget(value, old, new):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "Node Index" and item == old:
                value[key] = new
            else:
                _retarget(item, old, new)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            if item == old and isinstance(item, int) and not isinstance(item, bool):
                value[i] = new
            else:
                _retarget(item, old, new)


def _refers(value, index):
    if isinstance(value, dict):
        return value.get("Node Index") == index or any(_refers(v, index) for v in value.values())
    if isinstance(value, list):
        return any(_refers(v, index) for v in value)
    return False


def _as_command(node):
    values = list(node.get("Properties", {}).get("String", []))
    values += node.get("Parameters", {}).get("Inputs", {}).get("String", [])
    return next((p.get("Default Value") for p in values if p["Name"] == "ASCommand"), None)


def shop_ai(raw, flag, filename):
    """the shelf's AI, bought once: the purchase (its two branches: Link's get pose, Rotate_GetDemo, and the put in the
    pouch) also sets flag; every reader of the native QueryShopItemIsSoldOut reads flag instead; once bought, the shelf
    only hides while the shop's own stock says sold out, and deletes itself if that stock came back"""
    try:
        import ainb
    except ImportError as e:
        raise ValueError("Shopsanity needs the ainb library: python -m pip install ainb==0.2.17") from e
    script = ainb.AINB.from_binary(raw)
    original = script.as_dict()

    def build(document):   # (ainb 0.2.17 drops this graph's blackboard in as_dict(): put back, no node refers to it)
        result = ainb.AINB.from_dict(document)
        result.blackboard = script.blackboard
        return result.to_binary()
    if build(original) != script.to_binary():
        raise ValueError("the shelf's AI does not write back as it was")
    document = copy.deepcopy(original)
    if document["Version"] != 0x408:
        raise ValueError("the shelf's AI: version %#x" % document["Version"])
    nodes = document["Nodes"]

    def only(name):
        found = [n for n in nodes if n["Name"] == name]
        if len(found) != 1:
            raise ValueError("the shelf's AI: %d %s" % (len(found), name))
        return found[0]
    put = only("ExecuteShopItemPutInPouch")["Node Index"]
    sold_out = only("QueryShopItemIsSoldOut")["Node Index"]
    template = only("QueryGetNonStructGameDataBool")

    def parent_of(index):
        found = [n for n in nodes if any(p["Node Index"] == index for p in n.get("Plugs", {}).get("Child", []))]
        if len(found) != 1 or found[0]["Node Type"] != "Element_Simultaneous":
            raise ValueError("the shelf's AI: a purchase step without its simultaneous parent")
        return found[0]
    demo = [n["Node Index"] for n in nodes if n["Name"] == "ExecuteASPlay" and _as_command(n) == "Rotate_GetDemo"]
    if len(demo) != 1:
        raise ValueError("the shelf's AI: %d get poses" % len(demo))
    parents = [parent_of(demo[0]), parent_of(put)]
    setter_index, query_index = len(nodes), len(nodes) + 1
    setter = {"Node Type": "UserDefined", "Node Index": setter_index, "Name": "OneShotSetNonStructGameDataBool",
              "GUID": _guid(flag + "/bought"), "Flags": [], "Queries": [], "Attachments": [],
              "Properties": {"Bool": [{"Name": "ExecuteEveryFrame", "Default Value": False, "Flags": []}]},
              "Parameters": {"Inputs": {"Int": [_default("GameDataIndex", -1)], "Bool": [_default("Value", True)],
                                        "String": [_default("GameDataFullName", flag)]}, "Outputs": {}},
              "XLink Actions": [], "Plugs": {}}
    readers = [n for n in nodes if n["Node Index"] != sold_out
               and (sold_out in n.get("Queries", []) or _refers(n.get("Parameters"), sold_out))]
    if not readers:
        raise ValueError("the shelf's AI: nothing reads its sold out state")
    for node in readers:
        for part in ("Queries", "Parameters", "Plugs"):
            _retarget(node.get(part, {} if part != "Queries" else []), sold_out, query_index)
    query = copy.deepcopy(template)
    query.update({"Node Index": query_index, "GUID": _guid(flag + "/sold-out"), "Queries": [], "Plugs": {}})
    query["Parameters"]["Inputs"]["String"] = [_default("GameDataFullName", flag)]
    for parent in parents:
        parent["Plugs"]["Child"].append({"Node Index": setter_index, "Name": ""})
    selectors = [n for n in readers if n["Node Type"] == "Element_BoolSelector"]
    if len(selectors) != 1:
        raise ValueError("the shelf's AI: %d sold out selectors" % len(selectors))
    selector = selectors[0]
    branch = next((p for p in selector["Plugs"].get("Child", []) if p["Name"] == "True"), None)
    if branch is None or nodes[branch["Node Index"]]["Name"] != "OneShotGameModelControllerSetVisible":
        raise ValueError("the shelf's AI: its sold out branch is not the one known")
    put_parent = parents[1]
    put_parent["Plugs"]["Child"] = [p for p in put_parent["Plugs"]["Child"] if p["Node Index"] != selector["Node Index"]]
    delete_index, native_index = len(nodes) + 2, len(nodes) + 3
    delete = {"Node Type": "UserDefined", "Node Index": delete_index, "Name": "OneShotGenericDeleteThisActor",
              "GUID": _guid(flag + "/delete"), "Flags": [], "Queries": [], "Attachments": [],
              "Properties": {"Bool": [{"Name": "ExecuteEveryFrame", "Default Value": False, "Flags": []},
                                      {"Name": "IsFade", "Default Value": False, "Flags": []}]},
              "Parameters": {"Inputs": {}, "Outputs": {}}, "XLink Actions": [], "Plugs": {}}
    native = copy.deepcopy(selector)
    native.update({"Node Index": native_index, "GUID": _guid(flag + "/native-sold-out"), "Queries": [sold_out],
                   "Attachments": [], "Flags": [], "XLink Actions": []})
    native["Parameters"] = {"Inputs": {"Bool": [{"Name": "Input", "Default Value": False, "Node Index": sold_out,
                                                 "Output Index": 0, "Flags": []}]}, "Outputs": {}}
    native["Plugs"] = {"Generic": [{"Node Index": sold_out, "Name": "Input", "Unknown 1": 0, "Unknown 2": 0}],
                       "Child": [{"Node Index": branch["Node Index"], "Name": "True"},
                                 {"Node Index": delete_index, "Name": "False"}]}
    branch["Node Index"] = native_index
    nodes.extend([setter, query, delete, native])
    document["Filename"] = filename
    binary = build(document)
    back = ainb.AINB.from_binary(binary).as_dict()
    if back != document or back["Commands"] != original["Commands"]:
        raise ValueError("the shelf's new AI does not read back as written")
    return binary


# ---- the shelves

def _work(file):
    return pickups._work(file)


def _table_components(files, f):
    """a parameter table's components with its $parent chain's that the pack holds (OotrR's _table_components)"""
    chain = []
    while f and f in files:
        doc, _ = byml.read(files[f])
        chain.append(doc)
        parent = doc.get("$parent")
        f = parent[len("Work/"):-len(".gyml")] + ".bgyml" if isinstance(parent, str) and parent.startswith("Work/") else None
    out = {}
    for doc in reversed(chain):
        out.update(doc.get("Components", {}))
    return out


class Builder:
    """the shuffled shelves of a seed: packs (mod.add), rows (in made's tables, written by made.finish()), flags"""

    def __init__(self, romfs, codec, mod, made):
        self.romfs, self.codec, self.mod, self.made = romfs, codec, mod, made
        self.template = sarc.read(mod.read(pack_path(TEMPLATE)))
        token = sarc.read(mod.read(pack_path(TOKEN)))
        self.setting = pickups._components(token, "Actor/%s.engine__actor__ActorParam.bgyml" % TOKEN).get(
            "ActorGameDataSetting")
        if not isinstance(self.setting, str) or "NoRespawn" not in self.setting:
            raise ValueError("the token's NoRespawn setting is not found")
        self.flags = []
        self.built = {}

    def shelf(self, slot, item, price):
        """the new shelf actor selling item at price, for slot"""
        name = slot.actor
        if name in self.built:
            raise ValueError("%s twice" % name)
        template, param_file = self.template, "Actor/%s.engine__actor__ActorParam.bgyml" % TEMPLATE
        source = sarc.read(self.mod.read(pack_path(item)))
        src = pickups._components(source, "Actor/%s.engine__actor__ActorParam.bgyml" % item)
        files = {k: v for k, v in template.items() if k != param_file}
        doc, version = byml.read(template[param_file])
        e = byml.endian(template[param_file])
        doc = copy.deepcopy(doc)
        comps = doc.setdefault("Components", {})
        inherited = pickups._components(template, param_file)
        for key in FROM_ITEM:   # (what it is and how it looks: the item's; how it behaves: the shelf's)
            if src.get(key):
                comps[key] = src[key]
                for f in pickups._refs_in(source, pickups._ref_file(src[key])):
                    files.setdefault(f, source[f])
        pouch_ref = src.get("PouchContentRef")
        if not pouch_ref or pickups._ref_file(pouch_ref) not in source:
            raise ValueError("%s: no pouch content" % item)
        for f in pickups._refs_in(source, pickups._ref_file(pouch_ref)):
            files.setdefault(f, source[f])
        pouch_file = "Component/PouchContentParam/%s.game__component__PouchContentParam.bgyml" % name
        files[pouch_file] = byml.write({"$parent": _work(pickups._ref_file(pouch_ref)), "DefaultAutoGet": True,
                                        "PouchActor": "Work/Actor/%s.engine__actor__ActorParam.gyml" % item}, version, e)
        comps["PouchContentRef"] = "?" + pouch_file
        # (game parameters: the shelf's table with the item's own parts it lacks (capacities, abilities, equipment), and
        #  the price)
        table_ref = comps.get(GPT) or inherited.get(GPT)
        table_file = pickups._ref_file(table_ref)
        if table_file not in files:
            raise ValueError("the shelf's parameter table is not in its pack")
        table, tv = byml.read(files[table_file])
        table = copy.deepcopy(table)
        mine = _table_components(files, table_file)
        theirs = _table_components(source, pickups._ref_file(src[GPT])) if src.get(GPT) else {}
        added = {k: v for k, v in theirs.items() if k not in mine}
        table.setdefault("Components", {}).update(added)
        for ref in added.values():
            if isinstance(ref, str) and ref.startswith("?"):
                for f in pickups._refs_in(source, ref[1:]):
                    files.setdefault(f, source[f])
        price_file = "GameParameter/PriceParam/%s.game__pouchcontent__PriceParam.bgyml" % name
        files[price_file] = byml.write({"BuyingPrice": price, "SellingPrice": 1}, version, e)
        table["Components"]["PriceParam"] = "?" + price_file
        new_table = "GameParameter/GameParameterTable/%s.engine__actor__GameParameterTable.bgyml" % name
        files[new_table] = byml.write(table, tv, byml.endian(files[table_file]))
        comps[GPT] = "?" + new_table
        comps["ActorGameDataSetting"] = self.setting   # (a shared resource, as OotrR's shelves name it)
        if AI_MEMBER not in files:
            raise ValueError("the shelf's AI is not in its pack")
        root = name + ".root"
        files["AI/%s.ainb" % root] = shop_ai(files[AI_MEMBER], slot.flag, root)
        info = "AI/AIInfo/%s.engine__actor__AIInfo.bgyml" % name
        files[info] = byml.write({"RootAIRef": "Work/AI/Root/%s.ain" % root}, version, e)
        comps["AIInfoRef"] = "?" + info
        files["Actor/%s.engine__actor__ActorParam.bgyml" % name] = byml.write(doc, version, e)
        self.mod.add(pack_path(name), sarc.write(files), like=pack_path(TEMPLATE))

        # (the tables: the shelf's rows with the item's model and name; in the pouch, the item's row at our price)
        m = self.made
        base, own = m._row(pickups.ACTOR_INFO, TEMPLATE), m._row(pickups.ACTOR_INFO, item)
        row = copy.deepcopy(base)
        row["ActorName"] = own.get("ActorName", item)
        for k in MODEL_KEYS:
            if k in own:
                row[k] = copy.deepcopy(own[k])
            else:
                row.pop(k, None)
        for k in ("InstanceHeapSize", "PreActorRenderInfoHeapSize"):
            if k in own or k in base:
                row[k] = max(base.get(k, 0), own.get(k, 0))
        row["__RowId"] = name
        m._add(pickups.ACTOR_INFO, row)
        g = copy.deepcopy(m._row(pickups.GAME_ACTOR_INFO, TEMPLATE))
        try:
            own_g = m._row(pickups.GAME_ACTOR_INFO, item)
        except ValueError:
            own_g = {}
        if "ModelVariationAnims" in own_g:
            g["ModelVariationAnims"] = copy.deepcopy(own_g["ModelVariationAnims"])
        g["__RowId"] = name
        m._add(pickups.GAME_ACTOR_INFO, g)
        try:
            p = copy.deepcopy(m._row(pickups.POUCH_ACTOR_INFO, item))
        except ValueError:
            p = copy.deepcopy(m._row(pickups.POUCH_ACTOR_INFO, TEMPLATE))
        p["BuyingPrice"], p["SellingPrice"] = price, 1
        p["__RowId"] = name
        m._add(pickups.POUCH_ACTOR_INFO, p)
        self.flags.append(slot.flag)
        self.built[name] = (slot, item, price)
        return name

    def finish(self):
        """the flags: before mod.finish (the dungeon items' Builder writes the same data list: run after it)"""
        from . import gamedata
        if self.flags:
            self.mod.write(gamedata.GAME_DATA, gamedata.with_bools(self.mod.read(gamedata.GAME_DATA), self.flags))


def _f32(v):
    return struct.unpack("<f", struct.pack("<f", v))[0]


def board_hash(slot, rel, h):
    return int.from_bytes(hashlib.sha256(("%s/sold-out/%s/%d" % (slot.rc, rel, h)).encode()).digest()[:8], "little")


def add_board(actors, shelf, ident):
    """a Shop_Board_SoldOut behind the shelf, linked to it (Reference), with its Presence; None when one is linked already
    (the Kokiri shop's short stock)"""
    boards = {int(a["Hash"]) for a in actors if a.get("Gyaml") == SOLD_OUT}
    if any(l.get("Name") == "Reference" and int(l.get("Dst", 0)) in boards for l in shelf.get("Links", [])):
        return None
    if ident in {int(a["Hash"]) for a in actors if "Hash" in a}:
        raise ValueError("a sold out board's Hash is taken")
    rotate = list(shelf.get("Rotate", [0.0, 0.0, 0.0]))
    x, y, z = shelf["Translate"]
    yaw = rotate[1]
    board = {"Gyaml": SOLD_OUT, "Hash": byml.U64(ident),
             "Translate": [_f32(x - math.sin(yaw) * BOARD_BACK), y, _f32(z - math.cos(yaw) * BOARD_BACK)]}
    if "Rotate" in shelf:
        board["Rotate"] = rotate
    if "SRTHash" in shelf:
        board["SRTHash"] = shelf["SRTHash"]
    if "Presence" in shelf:
        board["Presence"] = copy.deepcopy(shelf["Presence"])
    shelf.setdefault("Links", []).append({"Dst": byml.U64(ident), "Gyaml": "Reference", "Name": "Reference",
                                          "Src": shelf["Hash"]})
    actors.append(board)
    return board


def never(rel):
    """a Presence never met in this map (as the Zora's River walls': the age the map is not for)"""
    return {"FlagName": AGE_FLAG, "IsCheckLazy": False, "IsNegation": "_Child_" in rel}


def write(romfs, codec, mod, shelves):
    """shelves: [(Slot, new actor)]: the maps (each copy's Gyaml, its sold out board), the shopkeepers (that slot sold once,
    at the shelf's price), and the Kokiri shop open from the start. Returns the files written."""
    written = []
    by_map = {}
    for slot, actor in shelves:
        for rel, h in slot.copies:
            by_map.setdefault(rel, []).append((slot, h, actor))
    kokiri_maps = sorted({rel for rel in by_map if rel.startswith("Banc/%s/" % KOKIRI)} |
                         ({"Banc/KokiriForest/KokiriForest_Child_Static.bcett.byml.zs",
                           "Banc/KokiriForest/KokiriForest_Child_Dynamic.bcett.byml.zs",
                           "Banc/KokiriForest/KokiriForest_Adult_Dynamic.bcett.byml.zs"} if shelves else set()))
    for rel in sorted(set(by_map) | set(kokiri_maps)):
        raw = mod.read(rel)
        root, version = byml.read(raw)
        actors = root["Actors"]
        by_hash = {int(a["Hash"]): a for a in actors if "Hash" in a}
        for slot, h, actor in by_map.get(rel, ()):
            a = by_hash.get(h)
            if a is None or a.get("Gyaml") != slot.shelf:
                raise ValueError("%s: %d is not %s" % (rel, h, slot.shelf))
            a["Gyaml"] = actor
            add_board(actors, a, board_hash(slot, rel, h))
        if rel in kokiri_maps:   # (the full stock always, the short stock and its boards never: OotrR's open_kokiri_shop)
            for a in actors:
                p = a.get("Presence")
                if not isinstance(p, dict) or p.get("FlagName") != KOKIRI_FLAG:
                    continue
                if not (a.get("Gyaml", "").startswith(("Shop_", "Npc_Kokiri_001_Shop"))):
                    continue
                if p.get("IsNegation"):
                    a["Presence"] = never(rel)
                else:
                    del a["Presence"]
        mod.write(rel, byml.write(root, version, byml.endian(raw)))
        written.append(rel)
    # (the shopkeepers: each shuffled slot sold once, at the shelf's own price)
    per_seller = {}
    for slot, _ in shelves:
        for seller in slot.sellers:
            per_seller.setdefault(seller, {})[slot.slot] = slot.shelf
    if shelves:
        for seller in KOKIRI_SELLERS:
            per_seller.setdefault(seller, {})
    for seller, slots in sorted(per_seller.items()):
        rel = pack_path(seller)
        files = sarc.read(mod.read(rel))
        changed = set()
        for f in shop_param_files(files):
            doc, version = byml.read(files[f])
            goods = doc.get("GoodsList", [])
            for i, shelf in slots.items():
                if i < len(goods) and goods[i].get("Actor", "").endswith("/%s.engine__actor__ActorParam.gyml" % shelf):
                    goods[i]["StockNum"] = 1
                    if "PriceOffset" in goods[i]:
                        goods[i]["PriceOffset"] = 0
                    if goods[i].get("ConditionalPriceOffsetList"):
                        goods[i]["ConditionalPriceOffsetList"] = []
                    changed.add(i)
            if seller in KOKIRI_SELLERS:   # (OotrR's release_kokiri_shop_goods: no good waits for the Deku Tree)
                for good in goods:
                    r = good.get("Release")
                    if isinstance(r, dict) and r.get("ReleaseGameData") == KOKIRI_FLAG:
                        r["IsCheckReleaseGameData"], r["ReleaseGameData"] = False, ""
            files[f] = byml.write(doc, version, byml.endian(files[f]))
        if set(slots) - changed:
            raise ValueError("%s: goods of slots %s not found" % (seller, sorted(set(slots) - changed)))
        mod.write(rel, sarc.write(files))
        written.append(rel)
    return written
