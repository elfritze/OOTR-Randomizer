"""HookshotRando's window (generate and install a seed, and the tracker).

    python gui.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rando import gui  # noqa: E402

if __name__ == "__main__":
    gui.main(sys.argv)
