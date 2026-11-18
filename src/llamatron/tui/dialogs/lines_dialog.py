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

"""The Lines dialog: the lines of one section of the song wizard's song, one row a line, each line's breath, early note and notes changed by hand.

Up and Down move between the lines. [ and ] make the breath after the cursor's line shorter and longer, in eighths, and
Space has a note of the line come an eighth early or not: both only on a line that is a new idea of the tune, since a
line that says an idea again is that idea's line. Enter opens the line's notes in the Tune dialog, Bksp gives the line
back to the wizard, L plays the section's tune as the lines stand, and Esc closes. Every change is made at once, through the functions the dialog is given, and a
change the song cannot be made with is said under the lines and left out.
"""

from rich.text import Text

from llamatron.macro_composer import line_edits
from llamatron.macro_composer.melody import LINE_NOTES
from llamatron.macro_composer.phrasing import LINE_BREATH, LINE_EARLY, LONGEST_BREATH, NO_BREATH, SHORT_BREATH
from llamatron.macro_composer.wizard_choices import LINE_BREATHES, LINE_IS_HOOK, LINE_OWN, LINE_PLAYER
from llamatron.strings import labels, marks
from llamatron.tui.dialogs.dialog import Dialog
from llamatron.tui.dialogs.tune_dialog import TuneDialog
from llamatron.tui.drawing import NOTHING, Style, cursor_mark
from llamatron.tui.key_table import STEP_BACK, STEP_FORWARD, cursor_moved
from llamatron.tui import keybindings

# A step is two cells wide where the lines fit so, and one where they are long.
WIDE_STEP = 2
NARROW_STEP = 1
# The cells beside a line's picture: the cursor's mark, the number, the gaps and the longest player's name.
ROOM_BESIDE = 28


class LinesDialog(Dialog):
    """Answers with nothing: its changes are made as its keys are pressed."""

    KEYS = keybindings.LinesDialog

    def __init__(self, *, title, lines, set_line, steps_in_bar, pitch_of_place, title_of_player, notes_title, listen, stop_listening):
        super().__init__()
        self.title = title
        # The section's lines as the song has them now, asked again after every change (WizardChoices.section_lines).
        self.lines_now = lines
        # Gives the cursor's line a value for a field, or gives the field back with None; returns what went wrong, or None.
        self.set_line = set_line
        self.steps_in_bar = steps_in_bar
        self.pitch_of_place = pitch_of_place
        self.title_of_player = title_of_player
        self.notes_title = notes_title
        # Plays the section's tune as the lines now stand, and returns what went wrong, or None.
        self.listen = listen
        self.stop_listening = stop_listening
        self.place = 0
        self.problem = None

    def line(self):
        return self.lines_now()[self.place]

    def keys(self):
        line = self.line()
        result = [self.bind(self.KEYS.CLOSE, action=self.close), self.bind(self.KEYS.MOVE, action=self.move, wants_key=True), self.bind(self.KEYS.LISTEN, action=self.hear)]
        if line[LINE_BREATHES]:
            result += [self.bind(self.KEYS.SHORTER, action=lambda: self.breathe(STEP_BACK)), self.bind(self.KEYS.LONGER, action=lambda: self.breathe(STEP_FORWARD)),
                       self.bind(self.KEYS.EARLY, action=self.flip_early)]
        if line[LINE_NOTES] is not None:
            result.append(self.bind(self.KEYS.EDIT, action=self.edit_notes))
        if line[LINE_OWN]:
            result.append(self.bind(self.KEYS.USUAL, action=self.put_back))
        return result

    def close(self):
        """Close the dialog, and stop what it was playing."""
        self.stop_listening()
        self.dismiss(None)

    def hear(self):
        self.problem = self.listen()

    def move(self, name):
        self.place = cursor_moved(place=self.place, name=name, count=len(self.lines_now()))
        self.problem = None

    def change(self, *, field, value):
        self.problem = self.set_line(line=self.place, field=field, value=value)

    def breathe(self, direction):
        """Make the breath after the cursor's line an eighth longer or shorter, from the usual breath where the line has none of its own."""
        now = self.line()[LINE_OWN].get(LINE_BREATH, SHORT_BREATH)
        self.change(field=LINE_BREATH, value=max(min(now + direction, LONGEST_BREATH), NO_BREATH))

    def flip_early(self):
        self.change(field=LINE_EARLY, value=not self.line()[LINE_OWN].get(LINE_EARLY, False))

    def put_back(self):
        for field in list(self.line()[LINE_OWN]):
            self.change(field=field, value=None)

    def edit_notes(self):
        """Open the cursor's line in the Tune dialog, over this one, and keep the line it answers with as the line's own notes."""
        line = self.line()
        place = self.place
        usual = line[LINE_NOTES]

        def kept(edited):
            if edited is not None and edited != line_edits.tidied(usual):
                self.problem = self.set_line(line=place, field=LINE_NOTES, value=edited)
            self.draw()
        self.app.push_screen(TuneDialog(title=self.notes_title.format(line=place + 1), line=usual, steps_in_bar=self.steps_in_bar, pitch_of_place=self.pitch_of_place, usual=usual), kept)

    # Drawing.

    def step_width(self, width):
        longest = max((line_edits.steps_of(line[LINE_NOTES]) for line in self.lines_now() if line[LINE_NOTES] is not None), default=0)
        return WIDE_STEP if longest * WIDE_STEP + ROOM_BESIDE <= width else NARROW_STEP

    def cells_of(self, *, notes, step):
        """Return a line's picture, one row whatever its pitches: filled where a note sounds, a gap at each note's end, between bar lines."""
        cells = []
        for note in notes:
            length = line_edits.length_of(note) * step
            cells += [marks.MSG_WIZARD_HOOK_GAP] * length if line_edits.is_rest(note) else [marks.MSG_WIZARD_HOOK_CELL] * (length - 1) + [marks.MSG_WIZARD_HOOK_GAP]
        size = self.steps_in_bar * step
        return marks.MSG_WIZARD_HOOK_BAR_LINE + marks.MSG_WIZARD_HOOK_BAR_LINE.join(''.join(cells[at:at + size]) for at in range(0, len(cells), size)) + marks.MSG_WIZARD_HOOK_BAR_LINE

    def row_line(self, *, count, line, step):
        cells = marks.MSG_LINES_SILENT if line[LINE_NOTES] is None else self.cells_of(notes=line[LINE_NOTES], step=step)
        player = NOTHING if line[LINE_NOTES] is None else self.title_of_player(line[LINE_PLAYER])
        row = Text(cursor_mark(count == self.place) + marks.MSG_LINES_ROW.format(number=count + 1, cells=cells, player=player), no_wrap=True)
        row.stylize(Style.BOLD if line[LINE_OWN] else Style.PLAIN)
        return row

    def field_lines(self):
        """Return what the cursor's line is and its three values, each the line's own or said to be the melody's."""
        line = self.line()
        if line[LINE_NOTES] is None:
            return [Text(marks.MSG_LINES_SILENT, style=Style.DIM)]
        own = line[LINE_OWN]
        said = (marks.MSG_LINES_HOOK_SAID if line[LINE_IS_HOOK] else marks.MSG_LINES_LINE_SAID).format(number=self.place + 1, player=self.title_of_player(line[LINE_PLAYER]))
        from_above = marks.MSG_LINES_FROM_MELODY if line[LINE_BREATHES] else marks.MSG_LINES_SAME_IDEA
        breath = marks.MSG_LINES_BREATH_OWN.format(eighths=own[LINE_BREATH]) if LINE_BREATH in own else from_above
        early = (labels.MSG_LINES_YES if own[LINE_EARLY] else labels.MSG_LINES_NO) if LINE_EARLY in own else from_above
        notes = labels.MSG_WIZARD_HOOK_NOTES_OWN if LINE_NOTES in own else labels.MSG_WIZARD_HOOK_NOTES_WIZARD
        values = [(labels.MSG_LINES_NOTES_LABEL, notes)] if LINE_NOTES in own else [(labels.MSG_LINES_BREATH_LABEL, breath), (labels.MSG_LINES_EARLY_LABEL, early), (labels.MSG_LINES_NOTES_LABEL, notes)]
        return [Text(said, style=Style.BOLD), *[Text(marks.MSG_LINES_FIELD.format(label=label, value=value)) for label, value in values]]

    def lines(self, width):
        step = self.step_width(width)
        problem = [Text(NOTHING), Text(self.problem, style=Style.REFUSAL)] if self.problem else []
        return [*[self.row_line(count=count, line=line, step=step) for count, line in enumerate(self.lines_now())], Text(NOTHING), *self.field_lines(), *problem]
