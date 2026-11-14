"""The randomizer's settings, with their defaults."""

DEFAULTS = {
    "skip_intro": True,       # the new game's two opening movies not played (rando.patches.skip_intro)
    "shuffle_songs": True,    # the songs shuffled with the other items (off: each taught where the game teaches it)
}


def add_arguments(parser):
    parser.add_argument("--no-skip-intro", dest="skip_intro", action="store_false", default=DEFAULTS["skip_intro"],
                        help="play the new game's opening movies")
    parser.add_argument("--no-shuffle-songs", dest="shuffle_songs", action="store_false", default=DEFAULTS["shuffle_songs"],
                        help="leave each song where the game teaches it")
