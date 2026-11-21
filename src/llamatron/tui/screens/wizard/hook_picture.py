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


def picture_of(*, hook, width, lit=None):
    """Return the lines of a hook's picture: a row for each note it plays, the highest first, each note drawn as long as it
    lasts with a gap at its end so that a note played twice shows as two, a line between bars, and a floor under the rows.
    lit, the first and the last of the bars that are the hook, counted from 1, in a picture of the hook's whole section,
    draws a frame's top over those bars and its bottom under them. A picture wider than the room is drawn as several, one
    under another, each of as many bars as fit."""
    steps, steps_in_bar, notes = hook
    step = WIDE_STEP if steps * WIDE_STEP + ROOM_BESIDE <= width else NARROW_STEP
    pitches = sorted({pitch for _, _, pitch in notes}, reverse=True)
    names = {pitch: note_shown(pitch) for pitch in pitches}
    longest = max(len(name) for name in names.values())
    bars = steps // steps_in_bar
    bar_cells = steps_in_bar * step
    before = longest + len(marks.MSG_WIZARD_HOOK_GAP)
    room = min(bars, max(1, (width - before - 1) // (bar_cells + 1)))
    # As few pictures as the room allows, each of as near the same number of bars as can be: eight bars in room for seven are
    # drawn four and four.
    fit = -(-bars // -(-bars // room))
    rows = {pitch: row_bars(notes=notes, pitch=pitch, steps=steps, steps_in_bar=steps_in_bar, step=step) for pitch in pitches}
    drawn = []
    for first in range(0, bars, fit):
        count = min(fit, bars - first)
        shown = lit_within(lit=lit, first=first + 1, last=first + count)
        frame = None if shown is None else frame_of(lit=shown, bar_cells=bar_cells, before=before)
        if lit is not None:
            drawn.append(frame[0] if frame else '')
        # A picture of several keeps only the rows whose note sounds among its bars.
        sounding = [pitch for pitch in pitches if fit == bars or sounds_in(rows[pitch][first:first + count])]
        drawn += [marks.MSG_WIZARD_HOOK_ROW.format(name=names[pitch], width=longest, cells=between_bar_lines(rows[pitch][first:first + count])) for pitch in sounding]
        floor = marks.MSG_WIZARD_HOOK_FLOOR_BAR.join([marks.MSG_WIZARD_HOOK_FLOOR * bar_cells] * count)
        drawn.append(marks.MSG_WIZARD_HOOK_ROW.format(name=marks.MSG_WIZARD_HOOK_GAP, width=longest, cells=marks.MSG_WIZARD_HOOK_FLOOR_BAR + floor + marks.MSG_WIZARD_HOOK_FLOOR_BAR))
        if lit is not None:
            drawn.append(frame[1] if frame else '')
    return drawn


def lit_within(*, lit, first, last):
    """Return the lit bars that fall among the bars first to last, counted from the first of those as 1, or None where none do."""
    if lit is None or lit[1] < first or lit[0] > last:
        return None
    return max(lit[0], first) - first + 1, min(lit[1], last) - first + 1


def frame_of(*, lit, bar_cells, before):
    """Return the top and the bottom of the frame around the lit bars: each from the bar line before the first of the bars to
    the bar line after the last, before being the cells a row has ahead of its first bar line."""
    first, last = lit
    # A bar is its cells and the bar line ahead of them.
    inside = (last - first + 1) * (bar_cells + 1) - 1
    indent = marks.MSG_WIZARD_HOOK_GAP * (before + (first - 1) * (bar_cells + 1))
    return (indent + marks.MSG_WIZARD_HOOK_FRAME_TOP.format(name=marks.MSG_WIZARD_HOOK_FRAME_NAME, width=inside),
            indent + marks.MSG_WIZARD_HOOK_FRAME_BOTTOM.format(rule=marks.MSG_WIZARD_HOOK_FRAME_RULE * inside))


def row_bars(*, notes, pitch, steps, steps_in_bar, step):
    """Return one note's row of the picture, bar by bar: its cells filled where the hook plays the note."""
    cells = [marks.MSG_WIZARD_HOOK_GAP] * (steps * step)
    for start, length, played in notes:
        if played == pitch:
            # The last cell of a note stays empty where the note has more than one, so that the next note stands apart.
            filled = max(length * step - 1, 1)
            cells[start * step:start * step + filled] = [marks.MSG_WIZARD_HOOK_CELL] * filled
    return [''.join(cells[bar * steps_in_bar * step:(bar + 1) * steps_in_bar * step]) for bar in range(steps // steps_in_bar)]


def between_bar_lines(bars):
    return marks.MSG_WIZARD_HOOK_BAR_LINE + marks.MSG_WIZARD_HOOK_BAR_LINE.join(bars) + marks.MSG_WIZARD_HOOK_BAR_LINE


def row_cells(*, notes, pitch, steps, steps_in_bar, step):
    """Return one note's row of the picture: its cells filled where the hook plays the note, between bar lines."""
    return between_bar_lines(row_bars(notes=notes, pitch=pitch, steps=steps, steps_in_bar=steps_in_bar, step=step))


def sounds_in(bars):
    """Return whether a note's row sounds in any of the bars drawn."""
    return any(marks.MSG_WIZARD_HOOK_CELL in bar for bar in bars)
