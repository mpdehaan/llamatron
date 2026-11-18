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

"""The picture of a hook: a row for each note it plays, drawn as long as each note lasts."""

from llamatron.strings import marks
from llamatron.tui.note_names import note_shown

# A step of the picture is two cells wide where the hook fits so, and one where it is long.
WIDE_STEP = 2
NARROW_STEP = 1
# The cells the picture leaves for a note's name and its edges.
ROOM_BESIDE = 8


def picture_of(*, hook, width):
    """Return the lines of a hook's picture: a row for each note it plays, the highest first, each note drawn as long as it
    lasts with a gap at its end so that a note played twice shows as two, a line between bars, and a floor under the rows."""
    steps, steps_in_bar, notes = hook
    step = WIDE_STEP if steps * WIDE_STEP + ROOM_BESIDE <= width else NARROW_STEP
    pitches = sorted({pitch for _, _, pitch in notes}, reverse=True)
    names = {pitch: note_shown(pitch) for pitch in pitches}
    longest = max(len(name) for name in names.values())
    lines = [marks.MSG_WIZARD_HOOK_ROW.format(name=names[pitch], width=longest, cells=row_cells(notes=notes, pitch=pitch, steps=steps, steps_in_bar=steps_in_bar, step=step)) for pitch in pitches]
    floor = marks.MSG_WIZARD_HOOK_FLOOR_BAR.join([marks.MSG_WIZARD_HOOK_FLOOR * (steps_in_bar * step)] * (steps // steps_in_bar))
    return [*lines, marks.MSG_WIZARD_HOOK_ROW.format(name=marks.MSG_WIZARD_HOOK_GAP, width=longest, cells=marks.MSG_WIZARD_HOOK_FLOOR_BAR + floor + marks.MSG_WIZARD_HOOK_FLOOR_BAR)]


def row_cells(*, notes, pitch, steps, steps_in_bar, step):
    """Return one note's row of the picture: its cells filled where the hook plays the note, between bar lines."""
    cells = [marks.MSG_WIZARD_HOOK_GAP] * (steps * step)
    for start, length, played in notes:
        if played == pitch:
            # The last cell of a note stays empty where the note has more than one, so that the next note stands apart.
            filled = max(length * step - 1, 1)
            cells[start * step:start * step + filled] = [marks.MSG_WIZARD_HOOK_CELL] * filled
    bars = [''.join(cells[bar * steps_in_bar * step:(bar + 1) * steps_in_bar * step]) for bar in range(steps // steps_in_bar)]
    return marks.MSG_WIZARD_HOOK_BAR_LINE + marks.MSG_WIZARD_HOOK_BAR_LINE.join(bars) + marks.MSG_WIZARD_HOOK_BAR_LINE
