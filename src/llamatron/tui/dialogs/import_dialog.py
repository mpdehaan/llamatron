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
"""The import dialog: what a MIDI file holds, the import's few choices as fields, what the import would make, and Import and Cancel, the user's design of 2026-11-10.

It is a dialog of fields over the file picker, not a page. Up and Down move between the fields
and the row of buttons; on a field [ and ] step its value, Space or Enter flips a toggle and
Enter renames the song; on the buttons Left and Right choose and Enter presses; I imports from
anywhere and Esc cancels. Each change works the import out again in memory, so that the line of
what it makes, and anything it would have to change, is always for the choices shown. Nothing
is added to the set until Import, which dismisses the dialog with what the import made.
"""

from rich.text import Text

from llamatron.composition.checks import fraction_text
from llamatron.composition.naming import copy_name, default_scale_name
from llamatron.importers.midi_import import LONGEST_PATTERN_CHOICES, ImportChoices
from llamatron.strings.importing import (
    MSG_IMPORT_AS_CHORDS, MSG_IMPORT_AS_TRACKS, MSG_IMPORT_AUTO_STEP, MSG_IMPORT_BUTTONS, MSG_IMPORT_CHORDS, MSG_IMPORT_CONTROLS, MSG_IMPORT_FOUND,
    MSG_IMPORT_KEYS_JOIN, MSG_IMPORT_LONGEST, MSG_IMPORT_MAKES, MSG_IMPORT_MAKES_LONG, MSG_IMPORT_MORE_KEYS, MSG_IMPORT_SHARED,
    MSG_IMPORT_SONG_NAME, MSG_IMPORT_SONG_PROMPT, MSG_IMPORT_STEP_SIZE, MSG_IMPORT_STEPS, MSG_IMPORT_TITLE, MSG_IMPORT_UNIQUE_NAMES,
)
from llamatron.strings.marks import MSG_CONFIRM_BUTTON_GAP, MSG_TOGGLE_ON
from llamatron.support.rational import Rational
from llamatron.tui.dialogs.dialog import Dialog
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.drawing import NOTHING, SPACE, Style, cursor_mark, padded, wrapped
from llamatron.tui.key_table import STEP_BACK, STEP_FORWARD, cursor_moved
from llamatron.tui import keybindings

# The rows the cursor moves over: the fields in the order drawn, then the buttons.
SONG_NAME = 0
LONGEST = 1
UNIQUE_NAMES = 2
CHORDS = 3
CONTROLS = 4
STEP_SIZE = 5
BUTTONS = 6
ROWS = 7
LABELS = (MSG_IMPORT_SONG_NAME, MSG_IMPORT_LONGEST, MSG_IMPORT_UNIQUE_NAMES, MSG_IMPORT_CHORDS, MSG_IMPORT_CONTROLS, MSG_IMPORT_STEP_SIZE)
LABEL_WIDTH = max(len(label) for label in LABELS) + 2
# The buttons, in the order drawn, and the binding whose key each shows.
IMPORT_BUTTON = 0
CANCEL_BUTTON = 1
BUTTON_BINDINGS = (keybindings.ImportDialog.IMPORT, keybindings.Dialog.CANCEL)
# The step sizes the Step size field steps through, auto first, as the user decided: auto, then 1/32 to 1/4.
STEP_SIZES = (None, Rational(1, 32), Rational(1, 16), Rational(1, 8), Rational(1, 4))
# How many keys the found line names before it counts the rest.
KEYS_NAMED = 2


def dimmed(lines):
    """Return lines of text drawn dim, as what the dialog only tells is."""
    for line in lines:
        line.stylize(Style.DIM)
    return lines


class ImportDialog(Dialog):
    """Asks how to import one MIDI file, and answers with what the import made, or nothing when cancelled."""

    KEYS = keybindings.ImportDialog

    def __init__(self, *, midi_import, setlist, song_name):
        super().__init__()
        self.title = MSG_IMPORT_TITLE
        self.midi_import = midi_import
        self.setlist = setlist
        taken = set(setlist.get_song_names())
        self.choices = ImportChoices(song_name=song_name if song_name not in taken else copy_name(name=song_name, taken=taken))
        self.row = SONG_NAME
        self.button = IMPORT_BUTTON
        # What the import makes for each set of choices tried, worked out once each.
        self._made = {}

    def keys(self):
        bound = [self.bind(self.KEYS.CANCEL, action=lambda: self.dismiss(None)), self.bind(self.KEYS.SELECT, action=self.move, wants_key=True)]
        if self.row == SONG_NAME:
            bound.append(self.bind(self.KEYS.RENAME, action=self.rename))
        elif self.row in (LONGEST, STEP_SIZE):
            bound += [self.bind(self.KEYS.LESS, action=lambda: self.step(STEP_BACK)), self.bind(self.KEYS.MORE, action=lambda: self.step(STEP_FORWARD))]
        elif self.row in (UNIQUE_NAMES, CHORDS, CONTROLS):
            bound.append(self.bind(self.KEYS.TOGGLE, action=self.toggle))
        else:
            bound += [self.bind(self.KEYS.CHOOSE_BUTTON, action=self.choose_button, wants_key=True), self.bind(self.KEYS.PRESS, action=self.press)]
        bound.append(self.bind(self.KEYS.IMPORT, action=self.import_now))
        return self.in_order(bound)

    def made(self):
        """Return what the import makes with the choices as they are now."""
        choices = self.choices
        key = (choices.song_name, choices.longest_pattern, choices.unique_names, choices.chords, choices.controls, choices.step_size)
        if key not in self._made:
            self._made[key] = self.midi_import.imported(setlist=self.setlist, choices=choices)
        return self._made[key]

    def move(self, name):
        self.row = cursor_moved(place=self.row, name=name, count=ROWS)

    def choose_button(self, name):
        self.button = cursor_moved(place=self.button, name=name, count=len(MSG_IMPORT_BUTTONS))

    def step(self, direction):
        """Step the Longest pattern or the Step size field through its choices, stopping at either end."""
        if self.row == LONGEST:
            place = LONGEST_PATTERN_CHOICES.index(self.choices.longest_pattern)
            self.choices.longest_pattern = LONGEST_PATTERN_CHOICES[max(0, min(place + direction, len(LONGEST_PATTERN_CHOICES) - 1))]
        else:
            place = STEP_SIZES.index(self.choices.step_size)
            self.choices.step_size = STEP_SIZES[max(0, min(place + direction, len(STEP_SIZES) - 1))]

    def toggle(self):
        if self.row == UNIQUE_NAMES:
            self.choices.unique_names = not self.choices.unique_names
        elif self.row == CONTROLS:
            self.choices.controls = not self.choices.controls
        else:
            self.choices.chords = not self.choices.chords

    def rename(self):
        """Ask for the song's name, keeping the old one when the answer is empty."""
        def renamed(text):
            if text and text.strip():
                self.choices.song_name = text.strip()
                self.draw()
        self.app.push_screen(PromptDialog(title=MSG_IMPORT_SONG_PROMPT, value=self.choices.song_name), renamed)

    def press(self):
        if self.button == IMPORT_BUTTON:
            self.import_now()
        else:
            self.dismiss(None)

    def import_now(self):
        self.dismiss(self.made())

    def values(self):
        """Return each field's value as shown."""
        made = self.made()
        choices = self.choices
        return (
            made.song.name, MSG_IMPORT_STEPS.format(count=choices.longest_pattern), MSG_TOGGLE_ON if choices.unique_names else NOTHING,
            MSG_IMPORT_AS_CHORDS if choices.chords else MSG_IMPORT_AS_TRACKS, MSG_TOGGLE_ON if choices.controls else NOTHING,
            MSG_IMPORT_AUTO_STEP.format(size=fraction_text(made.step_size)) if choices.step_size is None else fraction_text(choices.step_size),
        )

    def found_text(self):
        """Return the line of what the file holds, each key named once, in the order first heard."""
        found = self.midi_import.found()
        names = list(dict.fromkeys(default_scale_name(root=key.root, kind=key.kind) for key in found.keys))
        keys = MSG_IMPORT_KEYS_JOIN.join(names) if len(names) <= KEYS_NAMED else MSG_IMPORT_MORE_KEYS.format(first=names[0], count=len(names) - 1)
        return MSG_IMPORT_FOUND.format(tracks=found.tracks, bars=found.bars, time_signature=found.time_signature, tempo=found.tempo, keys=keys)

    def makes_text(self):
        """Return the line of what the import makes."""
        made = self.made()
        if made.long_patterns:
            return MSG_IMPORT_MAKES_LONG.format(
                tracks=made.tracks, patterns=made.patterns, long=made.long_patterns, longest=self.choices.longest_pattern, scenes=made.scenes,
            )
        return MSG_IMPORT_MAKES.format(tracks=made.tracks, patterns=made.patterns, scenes=made.scenes)

    def lines(self, width):
        made = self.made()
        lines = [*dimmed(wrapped(text=self.found_text(), width=width)), Text(NOTHING)]
        for row, (label, value) in enumerate(zip(LABELS, self.values())):
            line = Text(cursor_mark(row == self.row) + label.ljust(LABEL_WIDTH))
            line.append(value, style=Style.BOLD if row == self.row else Style.PLAIN)
            lines.append(line)
        lines.append(Text(NOTHING))
        lines += wrapped(text=self.makes_text(), width=width)
        if made.song.shared:
            lines.append(Text(MSG_IMPORT_SHARED.format(count=made.song.shared), style=Style.DIM))
        for warning in made.warnings:
            lines += dimmed(wrapped(text=warning, width=width))
        lines += [Text(NOTHING), self.buttons_line()]
        return lines

    def buttons_line(self):
        """Return Import and Cancel side by side, each its key reversed and then its name, the selected one marked when the cursor is on the buttons."""
        line = Text(no_wrap=True)
        for place, (label, binding) in enumerate(zip(MSG_IMPORT_BUTTONS, BUTTON_BINDINGS)):
            selected = self.row == BUTTONS and place == self.button
            _, key_name, _ = binding
            line.append(cursor_mark(selected))
            line.append(padded(key_name), style=Style.REVERSE)
            line.append(SPACE)
            line.append(label, style=Style.BOLD if selected else Style.PLAIN)
            line.append(MSG_CONFIRM_BUTTON_GAP)
        return line
