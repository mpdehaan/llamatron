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

"""Where random numbers come from: a generator reseeded from a seed, or the program's own stream when there's none."""

import random


def random_source(seed):
    """Return what draws random numbers for a seed.

    With a seed it's a generator seeded from that alone, so the same seed always draws the same
    numbers and a render can be repeated. With none it's Python's own random module, which the
    system seeds once when the program starts, so every render is a new take.
    """
    return random if seed is None else random.Random(seed)
