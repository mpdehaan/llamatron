# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A CC row: a value from 0 to 127 on any step, one line of numbers, labelled with the CC number the lane sends.

The bars once drawn above the numbers were dropped, so a CC row is one line like
Velocity. The label says which CC number the lane sends on the tracks that play the pattern, like
CC 1 (74), or (off) for a lane that sends nothing on them, or (?) when the tracks disagree, and
plain CC 1 when no track plays the pattern yet.
"""

from llamatron.model.schema import file_format
from llamatron.tui import keybindings
from llamatron.tui.components.control_row import ControlRow
from llamatron.user_strings import labels, marks


class CcRow(ControlRow):
    """The same keys as a control row, with the lane's CC number in the label."""

    KEYS = keybindings.CcRow

    __slots__ = ()

    def lane(self):
        return file_format.CC_ROWS.index(self.name)

    def label(self):
        numbers = self.editor.document().cc_numbers_for_pattern(name=self.editor.item, lane=self.lane())
        if not numbers:
            return super().label()
        if len(numbers) > 1:
            number = marks.MSG_CC_LANE_VARIES
        elif numbers[0] is None:
            number = marks.MSG_CC_LANE_OFF
        else:
            number = str(numbers[0])
        return labels.MSG_CC_ROW_LABEL.format(label=super().label(), number=number)
