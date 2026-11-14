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
"""A CC row: a value from 0 to 127 on any step, one line of numbers, labelled with the CC number the lane sends.

The user dropped the bars drawn above the numbers on 2026-11-08, so a CC row is one line like
Velocity. The label says which CC number the lane sends on the tracks that play the pattern, like
CC 1 (74), or (off) for a lane that sends nothing on them, or (?) when the tracks disagree, and
plain CC 1 when no track plays the pattern yet.
"""

from llamatron.composition.file_format import CC_ROWS
from llamatron.tui.components.control_row import ControlRow
from llamatron.strings.labels import MSG_CC_ROW_LABEL
from llamatron.strings.marks import MSG_CC_LANE_OFF, MSG_CC_LANE_VARIES
from llamatron.tui import keybindings


class CcRow(ControlRow):
    """The same keys as a control row, with the lane's CC number in the label."""

    KEYS = keybindings.CcRow

    __slots__ = ()

    def lane(self):
        return CC_ROWS.index(self.name)

    def label(self):
        numbers = self.editor.document().cc_numbers_for_pattern(name=self.editor.item, lane=self.lane())
        if not numbers:
            return super().label()
        if len(numbers) > 1:
            number = MSG_CC_LANE_VARIES
        elif numbers[0] is None:
            number = MSG_CC_LANE_OFF
        else:
            number = str(numbers[0])
        return MSG_CC_ROW_LABEL.format(label=super().label(), number=number)
