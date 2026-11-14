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

"""ScaleKind names every scale type the way the file spells it, so it has to match ScaleType exactly."""

import unittest

from llamatron.composition.file_format import ScaleKind
from llamatron.music.scale import ScaleType


def scale_kind_names():
    """Return the kinds ScaleKind defines, by constant name."""
    return {name: value for name, value in vars(ScaleKind).items() if not name.startswith('_')}


class TestScaleKinds(unittest.TestCase):

    def test_every_scale_type_has_a_kind_and_nothing_else_does(self):
        expected = {name: name.lower() for name in ScaleType.__members__}
        self.assertEqual(scale_kind_names(), expected)
