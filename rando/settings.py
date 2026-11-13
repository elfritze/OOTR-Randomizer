"""The randomizer's settings, with their defaults."""

DEFAULTS = {
    "skip_intro": True,       # the new game's two opening movies not played (rando.patches.skip_intro)
}


def add_arguments(parser):
    parser.add_argument("--no-skip-intro", dest="skip_intro", action="store_false", default=DEFAULTS["skip_intro"],
                        help="play the new game's opening movies")
