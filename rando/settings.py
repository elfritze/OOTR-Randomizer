"""The randomizer's settings, with their defaults, and how a window or a command line shows them.

Grouped as Ship of Harkinian's randomizer groups its own (Shuffle Items, Shuffle Dungeon Items, Timesavers...), with only what
this randomizer does; the rest of SoH's choices are shown fixed (FIXED), with the reason. A setting is on/off, or one of its
choices (Option.choices: ((value, label), ...), the value a string)."""
import collections

Option = collections.namedtuple("Option", "key section label help default seen choices", defaults=(None,))

SECTIONS = collections.OrderedDict((
    ("shuffle", ("Shuffle items", "Which checks hold a random item (Ship of Harkinian: Shuffle Items).")),
    ("dungeon", ("Dungeon items", "Where each dungeon's maps, compasses and keys may be (Ship of Harkinian: Shuffle "
                 "Dungeon Items). Outside its own dungeon, or in a small chest, an item is the dungeon's own: \"Small "
                 "Key (Forest Temple)\" works wherever it is found. These go in chests only.")),
    ("timesavers", ("Timesavers", "Less waiting; no check changes (Ship of Harkinian: Timesavers).")),
    ("world", ("World", "How the world behaves; no check changes.")),
    ("hints", ("Hints", "What the gossip stones say (Ship of Harkinian: Hints).")),
))

# (where a dungeon item may go: SoH's Own Dungeon, Any Dungeon, Overworld, Anywhere)
PLACES = (("own_dungeon", "Own dungeon"), ("any_dungeon", "Any dungeon"), ("overworld", "Overworld"),
          ("anywhere", "Anywhere"))

OPTIONS = (
    Option("shuffle_songs", "shuffle", "Shuffle songs",
           "The 12 songs are placed with the other items (SoH: Shuffle Songs, anywhere). Off: each song is taught where "
           "the game teaches it.", True, True),
    Option("shuffle_gifts", "shuffle", "Shuffle gifts and prizes",
           "What NPCs give and minigames award (Skull Kid, the frogs, the shooting galleries, Dampe, the Gorons, scrubs "
           "selling a Heart Piece, Darunia's Goron's Bracelet...): 36 checks. Off: each gives what the game gives.", True, True),
    Option("shuffle_freestanding", "shuffle", "Shuffle freestanding Heart Pieces",
           "Heart Pieces lying in the world and the bosses' Heart Containers (22 checks; SoH: Shuffle Freestanding). "
           "Off: they stay Heart Pieces and Containers.", True, True),
    Option("shuffle_maps_compasses", "dungeon", "Maps and compasses",
           "Own dungeon: in their dungeon, as the game has them. Any dungeon: in any dungeon. Overworld: outside the "
           "dungeons. Anywhere: any chest.", "own_dungeon", False, PLACES),
    Option("shuffle_small_keys", "dungeon", "Small keys",
           "As maps and compasses (SoH: Small Key Shuffle). Logic counts each dungeon's keys wherever they are. "
           "Overworld for all three kinds at once is refused: 65 items, more than the chests and loose spots outside "
           "the dungeons.", "own_dungeon", False, PLACES),
    Option("shuffle_boss_keys", "dungeon", "Boss keys",
           "As maps and compasses (SoH: Boss Key Shuffle), Ganon's Castle's boss key with the others.",
           "own_dungeon", False, PLACES),
    Option("shuffle_quest_items", "shuffle", "Shuffle Zelda's Letter and the Light Arrows",
           "Zelda's Letter (her scene in the castle garden) and the Light Arrows (her scene in the Temple of Time) are "
           "placed with the other items; their scenes give the item placed there. The letter, wherever found, opens "
           "Kakariko's gate.", False, False),
    Option("shuffle_fairy_ocarina", "shuffle", "Shuffle the Fairy Ocarina",
           "Saria's gift on the Lost Woods bridge is placed with the other items; she gives the item placed there. An "
           "ocarina found elsewhere is made playable on the next item get (OotrR's fix). The Ocarina of Time stays at "
           "the castle moat (its scene teaches the Song of Time).", False, False),
    Option("shuffle_great_fairies", "shuffle", "Shuffle Great Fairies",
           "The 6 Great Fairies' gifts (Din's Fire, Farore's Wind, Nayru's Love, magic, double magic, double defense) are "
           "placed with the other items, each fairy giving the item placed there once. They still ask their rupees "
           "(25 to 500): Nayru's and the one outside Ganon's Castle (300, 500) need the 500-rupee wallet in logic.",
           False, False),
    Option("shuffle_tokens", "shuffle", "Shuffle Gold Skulltula tokens",
           "The 100 Gold Skulltulas drop the item placed there (SoH: Tokensanity, all), floating where each dies as its "
           "token does; the 100 tokens go with the other items. The House of Skulltula counts tokens wherever found.",
           False, False),
    Option("shuffle_dungeon_rewards", "shuffle", "Shuffle dungeon rewards",
           "The 3 spiritual stones and 6 medallions (SoH: Shuffle Dungeon Rewards): Vanilla, each from its own boss; End "
           "of dungeon, shuffled among the 8 bosses and Rauru. The scenes still show the game's own reward; the item got "
           "is the one placed.", "vanilla", False, (("vanilla", "Vanilla"), ("end_of_dungeon", "End of dungeon"))),
    Option("shuffle_shops", "shuffle", "Shopsanity",
           "Shelves of the 8 shops sell items of the pool, each once (SoH: Shopsanity): that many per shop, or a random "
           "number. The shelves logic needs (shields, tunics, Deku nuts and sticks, Bombchus) go last; the others keep "
           "their item. The Kokiri shop sells its whole stock from the start. A bought shelf shows \"Sold Out\" (the OotrR "
           "randomizer's way).", "off", False,
           (("off", "Off"),) + tuple((str(n), str(n)) for n in range(1, 8)) + (("random", "Random"),)),
    Option("shop_prices", "shuffle", "Shop prices",
           "What a shuffled shelf costs (SoH: Shopsanity Prices): Vanilla, the price of what the shelf sold; Cheap "
           "balanced and Balanced, SoH's random prices (about 30 and 125 rupees on average); Affordable, Balanced "
           "lowered to the least of the wallet it needs. Logic counts the remake's wallets (200, 500, 999 rupees).",
           "vanilla", False,
           (("vanilla", "Vanilla"), ("cheap_balanced", "Cheap balanced"), ("balanced", "Balanced"),
            ("affordable", "Affordable"))),
    Option("skip_intro", "timesavers", "Skip the opening movies",
           "A new game starts in Kokiri Forest without the two opening movies.", True, True),
    Option("skip_auto_dialogues", "timesavers", "Skippable automatic dialogues",
           "The 12 sequences a quest step starts by itself (Navi's lines, minigames' rules) can be skipped with +.",
           True, False),
    Option("skip_title_and_credits", "timesavers", "Skippable title demo and credits",
           "The title screen's demo and the end credits can be skipped.", True, False),
    Option("skulltulas_day_and_night", "world", "Night Gold Skulltulas also by day",
           "The 30 Gold Skulltulas that only come out at night are there day and night.", False, False),
    Option("gossip_stone_hints", "hints", "Gossip stone hints",
           "Gossip stones tell where items are (SoH: Gossip Stone Hints). Need nothing: any stone talks. Mask of Truth: "
           "only while Link wears it, as in the game. Stone of Agony: once Link has it. No hints: the game's rumors.",
           "need_nothing", False,
           (("none", "No hints"), ("need_nothing", "Need nothing"), ("mask_of_truth", "Mask of Truth"),
            ("stone_of_agony", "Stone of Agony"))),
    Option("hint_distribution", "hints", "Hint distribution",
           "How useful the hints are (SoH: Hint Distribution): Useless is jokes only; Balanced mixes the way of the "
           "hero, foolish areas, items and some junk; Strong and Very strong give more of the useful kinds.",
           "balanced", False,
           (("useless", "Useless"), ("balanced", "Balanced"), ("strong", "Strong"), ("very_strong", "Very strong"))),
)
BY_KEY = {o.key: o for o in OPTIONS}
DEFAULTS = {o.key: o.default for o in OPTIONS}
# (settings taken out, each at the one value it now has whatever a settings file says: fast_chests, the small chests'
#  quick flow (qol.fast_chests), crashed the game as soon as a small chest was opened (seed 7cc65105, Goron City's maze,
#  2026-11-15; the same seed without it opened them))
RETIRED = {"fast_chests": False}
DEFAULTS.update(RETIRED)
# (settings of older seeds: their missing keys mean what the randomizer did then)
LEGACY = {"shuffle_gifts": True, "shuffle_freestanding": True, "fast_chests": False, "skip_auto_dialogues": False,
          "skip_title_and_credits": False, "skulltulas_day_and_night": False, "gossip_stone_hints": "none"}

# (Ship of Harkinian's other choices, shown as this randomizer has them: (section, label, value, why))
FIXED = (
    ("world", "Logic", "Glitchless", "Ship of Harkinian's logic, with the remake's differences."),
    ("world", "Starting age", "Child", ""),
    ("world", "Entrances", "Not shuffled", ""),
    ("fixes", "Story locks the remake adds", "Always fixed",
     "Mido, the forest's tunnel kid, King Zora's arrival, Darunia's bracelet, the Master Sword before the Forest "
     "Temple, Zora's River's walls, the boulder over Dodongo's Cavern: without these, seeds can end in a dead end."),
    ("fixes", "Bombs without the Goron's Bracelet", "Always", "The remake asks for the bracelet to pull a bomb; a seed "
     "can give the bomb bag first."),
    ("fixes", "Starting quiver and seed bag", "Always", "The remake's bow and slingshot hold no ammunition by "
     "themselves."),
    ("fixes", "The clock from the start", "Always", "The remake holds the time at 15:00 until Impa's send-off from the "
     "castle: no night (night-only Gold Skulltulas, Dampe) before Zelda, which SoH's logic does not wait for."),
    ("hints", "Hint clarity", "Clear", "Items and places by the names the game gives them, in the game's language."),
    ("hints", "Item hints", "By area", "SoH names the exact check (\"the frogs' final reward\") only for its always "
     "hints; its other item hints here say the area, as its named-item hints do."),
    ("hints", "Other hints", "Off", "The Temple of Time altar, Ganondorf, Sheik, Saria and the other NPC hints of SoH "
     "are not in this version. A junk hint keeps the stone's own rumor."),
)
FIXED += (
    ("off", "Fast chests", "Off", "Small chests opened without their cutscene crashed the game (seen in game): off "
     "until fixed."),
)
FIXED_SECTIONS = collections.OrderedDict((
    ("world", "Logic and world"), ("fixes", "Always on"), ("hints", "Hint details"), ("off", "Off for now"),
))


def normalized(chosen, legacy=False):
    """the settings as generate takes them: every key, missing ones at their default (legacy: at what older versions
    did), unknown ones refused"""
    unknown = set(chosen) - set(DEFAULTS)
    if unknown:
        raise ValueError("unknown settings: %s" % ", ".join(sorted(unknown)))
    out = dict(DEFAULTS)
    if legacy:
        out.update(LEGACY)
    for k, v in chosen.items():
        if k in RETIRED:
            continue
        o = BY_KEY[k]
        if o.choices:
            if v not in dict(o.choices):
                raise ValueError("setting %s: %r is not one of %s" % (k, v, ", ".join(c for c, _ in o.choices)))
        elif not isinstance(v, bool):
            raise ValueError("setting %s is not on/off: %r" % (k, v))
        out[k] = v
    if all(out[k] == "overworld" for k in ("shuffle_maps_compasses", "shuffle_small_keys", "shuffle_boss_keys")):
        raise ValueError("maps and compasses, small keys and boss keys cannot all be in the overworld: 65 items for "
                         "about 60 places outside the dungeons; choose another place for one of them")
    return out


def choice_label(key, value):
    return dict(BY_KEY[key].choices)[value]


def summary(chosen):
    """short lines for a window: each section's settings that are on (a choice: its label and value)"""
    s = normalized(chosen)
    lines = []
    for key, (title, _) in SECTIONS.items():
        on = [("%s (%s)" % (o.label, choice_label(o.key, s[o.key]).lower())) if o.choices else o.label
              for o in OPTIONS if o.section == key and (o.choices or s[o.key])]
        lines.append("%s: %s" % (title, ", ".join(on) if on else "none"))
    return lines


def add_arguments(parser):
    for o in OPTIONS:
        flag = o.key.replace("_", "-")
        if o.choices:
            parser.add_argument("--" + flag, dest=o.key, choices=[c for c, _ in o.choices], default=o.default,
                                help="%s (default %s)" % (o.label, o.default))
        elif o.default:
            parser.add_argument("--no-" + flag, dest=o.key, action="store_false", default=True, help="off: " + o.label)
        else:
            parser.add_argument("--" + flag, dest=o.key, action="store_true", default=False, help=o.label)
