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
"""How two drum grooves are compared, which is how the analyzer names the groove a kit plays: a groove matches itself, a
shuffle is far from a rock beat, and a rock beat with one more kick is nearer a rock beat than a house beat is."""

import unittest

from llamatron.genres.measures.comparing import SAME, groove_gap
from llamatron.genres.measures.drum_patterns import GROOVES
from llamatron.strings.genres import GrooveName

GROOVES_BY_NAME = {groove.name: groove for groove in GROOVES}
FAR = 0.1


class TestComparing(unittest.TestCase):

    def test_a_groove_matches_itself_and_a_shuffle_differs_from_a_rock_beat(self):
        rock = GROOVES_BY_NAME[GrooveName.ROCK_BEAT]
        self.assertEqual(groove_gap(mine=rock, theirs=rock), SAME)
        self.assertGreater(groove_gap(mine=GROOVES_BY_NAME[GrooveName.SHUFFLE], theirs=rock), FAR)
        self.assertLess(groove_gap(mine=GROOVES_BY_NAME[GrooveName.ROCK_AND_OF_THREE], theirs=rock), groove_gap(mine=GROOVES_BY_NAME[GrooveName.HOUSE], theirs=rock))


if __name__ == '__main__':
    unittest.main()
