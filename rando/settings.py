"""The randomizer's settings, with their defaults, and how a window or a command line shows them.

Grouped as Ship of Harkinian's randomizer groups its own (Shuffle Items, Shuffle Dungeon Items, Timesavers...), with only what
this randomizer does; the rest of SoH's choices are shown fixed (FIXED), with the reason. Every setting is on/off."""
import collections

Option = collections.namedtuple("Option", "key section label help default seen")

SECTIONS = collections.OrderedDict((
    ("shuffle", ("Shuffle items", "Which checks hold a random item (Ship of Harkinian: Shuffle Items).")),
    ("timesavers", ("Timesavers", "Less waiting; no check changes (Ship of Harkinian: Timesavers).")),
    ("world", ("World", "How the world behaves; no check changes.")),
))

OPTIONS = (
    Option("shuffle_songs", "shuffle", "Shuffle songs",
           "The 12 songs are placed with the other items (SoH: Shuffle Songs, anywhere). Off: each song is taught where "
           "the game teaches it.", True, True),
    Option("shuffle_gifts", "shuffle", "Shuffle gifts and prizes",
           "What NPCs give and minigames award (Skull Kid, the frogs, the shooting galleries, Dampe, the Gorons, scrubs "
           "selling a Heart Piece...): 35 checks. Off: each gives what the game gives.", True, True),
    Option("shuffle_freestanding", "shuffle", "Shuffle freestanding Heart Pieces",
           "Heart Pieces lying in the world and the bosses' Heart Containers (22 checks; SoH: Shuffle Freestanding). "
           "Off: they stay Heart Pieces and Containers.", True, True),
    Option("skip_intro", "timesavers", "Skip the opening movies",
           "A new game starts in Kokiri Forest without the two opening movies.", True, True),
    Option("fast_chests", "timesavers", "Fast chests",
           "Chests open without their cutscene: the lid opens and Link holds the item up (SoH: Fast Chests; the OotrR "
           "randomizer's patch).", True, False),
    Option("skip_auto_dialogues", "timesavers", "Skippable automatic dialogues",
           "The 12 sequences a quest step starts by itself (Navi's lines, minigames' rules) can be skipped with +.",
           True, False),
    Option("skip_title_and_credits", "timesavers", "Skippable title demo and credits",
           "The title screen's demo and the end credits can be skipped.", True, False),
    Option("skulltulas_day_and_night", "world", "Night Gold Skulltulas also by day",
           "The 30 Gold Skulltulas that only come out at night are there day and night.", False, False),
)
BY_KEY = {o.key: o for o in OPTIONS}
DEFAULTS = {o.key: o.default for o in OPTIONS}
# (settings of older seeds: their missing keys mean what the randomizer did then)
LEGACY = {"shuffle_gifts": True, "shuffle_freestanding": True, "fast_chests": False, "skip_auto_dialogues": False,
          "skip_title_and_credits": False, "skulltulas_day_and_night": False}

# (Ship of Harkinian's other choices, shown as this randomizer has them: (section, label, value, why))
FIXED = (
    ("dungeon", "Maps and compasses", "Own dungeon", "The remake has one map and one compass item for every dungeon."),
    ("dungeon", "Small keys", "Own dungeon", "The remake's small key is one item for every dungeon: a key found in "
     "another dungeon would open that one."),
    ("dungeon", "Boss keys", "Own dungeon", "As small keys."),
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
)
FIXED_SECTIONS = collections.OrderedDict((
    ("dungeon", "Dungeon items"), ("world", "Logic and world"), ("fixes", "Always on"),
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
        if not isinstance(v, bool):
            raise ValueError("setting %s is not on/off: %r" % (k, v))
        out[k] = v
    return out


def summary(chosen):
    """short lines for a window: each section's settings that are on"""
    s = normalized(chosen)
    lines = []
    for key, (title, _) in SECTIONS.items():
        on = [o.label for o in OPTIONS if o.section == key and s[o.key]]
        lines.append("%s: %s" % (title, ", ".join(on) if on else "none"))
    return lines


def add_arguments(parser):
    for o in OPTIONS:
        flag = o.key.replace("_", "-")
        if o.default:
            parser.add_argument("--no-" + flag, dest=o.key, action="store_false", default=True, help="off: " + o.label)
        else:
            parser.add_argument("--" + flag, dest=o.key, action="store_true", default=False, help=o.label)
