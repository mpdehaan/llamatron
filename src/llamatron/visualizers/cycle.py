# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Cycle, a visualizer mode of modes: each of the other modes in turn, moving on every CYCLE_SECONDS, the user's design of 2026-11-10.

It shows each mode from the start, fresh, and says which is showing, so that the page shows the
name for a while each time it moves on, as it does when the key changes the mode. The order is
shuffled once when the program starts (CYCLE_ORDER), so that every run, and so every recording,
goes through the modes in an order of its own, and keeps that order for the whole run, the
user's ask.
"""

import random

from llamatron.visualizers.digital_rain import DigitalRain
from llamatron.visualizers.fireworks import Fireworks
from llamatron.visualizers.heard import SILENCE
from llamatron.visualizers.hypercube import Hypercube
from llamatron.visualizers.laser_llama import LaserLlama
from llamatron.visualizers.lava_lamp import LavaLamp
from llamatron.visualizers.life import Life
from llamatron.visualizers.llamas import Llamas
from llamatron.visualizers.mandelbrot import Mandelbrot
from llamatron.visualizers.maze import Maze
from llamatron.visualizers.milkdrop import Milkdrop
from llamatron.visualizers.mystify import Mystify
from llamatron.visualizers.piano_roll import PianoRoll
from llamatron.visualizers.pipes import Pipes
from llamatron.visualizers.plasma import Plasma
from llamatron.visualizers.spectrum import Spectrum
from llamatron.visualizers.warpzone import WarpZone
from llamatron.visualizers.visualizer import Visualizer
from llamatron.strings.visualizers import MSG_CYCLE

# How long each mode shows before the next, hard-coded for now as the user asked, and the modes it goes through.
CYCLE_SECONDS = 15.0
CYCLED = (
    LavaLamp, PianoRoll, Spectrum, Milkdrop, Llamas, Hypercube, Fireworks, WarpZone, Pipes, Plasma, Maze, Mystify, LaserLlama, Mandelbrot, Life, DigitalRain,
)


def shuffled(*, modes, chooser):
    """Return the modes once each, in an order chooser shuffles."""
    order = list(modes)
    chooser.shuffle(order)
    return tuple(order)


# The order Cycle shows the modes in, shuffled once as the program starts, from Python's own unseeded stream.
CYCLE_ORDER = shuffled(modes=CYCLED, chooser=random.Random())


class Cycle(Visualizer):
    """Each of the other modes in turn, in CYCLE_ORDER, every CYCLE_SECONDS."""

    __slots__ = ('_order', '_place', '_showing', '_since')

    NAME = MSG_CYCLE
    OPTION = 'cycle'

    def __init__(self, *, hidden=()):
        """Go through CYCLE_ORDER, leaving out the modes named in hidden, the ones the set hides, unless that leaves none."""
        super().__init__()
        self._order = [mode for mode in CYCLE_ORDER if mode.OPTION not in hidden] or list(CYCLE_ORDER)
        self._place = 0
        self._showing = self._order[0]()
        self._since = None

    @classmethod
    def made_for(cls, *, hidden=()):
        return cls(hidden=hidden)

    def order(self):
        """Return the modes it goes through, in turn."""
        return list(self._order)

    def shown_name(self):
        return self._showing.shown_name()

    def showing(self):
        """Return the mode showing now."""
        return self._showing

    def frame(self, *, width, height, now, heard=SILENCE):
        if self._since is None:
            self._since = now
        if now - self._since >= CYCLE_SECONDS:
            self._place = (self._place + 1) % len(self._order)
            self._showing = self._order[self._place]()
            self._since = now
        return self._showing.frame(width=width, height=height, now=now, heard=heard)
