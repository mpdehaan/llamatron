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
"""The Chord row: a chord symbol on a note, picked from a grid or cycled through."""

from llamatron.composition.file_format import CHORD_SYMBOLS, Row

from llamatron.tui.components.pattern_row import PatternRow
from llamatron.tui.key_table import STEP_FORWARD
from llamatron.tui.chord_text import ChordInWords
from llamatron.tui.scale_categories import SCALE_CATEGORIES
from llamatron.tui.dialogs.chord_dialog import QUALITY_LIST, SCALE_LIST, TENSION_LIST, ChordChoice, ChordDialog
from llamatron.strings.labels import MSG_CHORD_NAMES
from llamatron.strings.marks import MSG_CHORD_SYMBOL_NAMED
from llamatron.strings.messages import MSG_CHORD_DIALOG_TITLE, MSG_CHORD_OF_STEP, MSG_QUALITY_SINGLE_NOTE
from llamatron.tui import keybindings

def chord_text(value):
    return None if value is None else str(value)


def chord_value(text):
    """Return a chord symbol the way a file holds it, where the scale's chords are numbers."""
    return int(text) if text and text.isdigit() else text


# The rows the Chord dialog edits together, and the list it opens on from each.
OPENS_ON = {Row.CHORD: QUALITY_LIST, Row.TENSION: TENSION_LIST, Row.CHORD_SCALE: SCALE_LIST}


def quality_names(symbols):
    """Return what the Chord dialog calls each chord symbol: the symbol and what it is, like "m7  minor seventh"."""
    return [MSG_CHORD_SYMBOL_NAMED.format(symbol=symbol, name=MSG_CHORD_NAMES[symbol]) for symbol in symbols]


def step_chord_in_words(*, editor, step, choice=None):
    """Return a step's chord in words, in the scale the pattern is known to play under, with a ChordChoice in place of the step's own when one is given."""
    current = step_choice(editor=editor, step=step) if choice is None else choice
    degree = editor.value(row=Row.DEGREE, step=step)
    return ChordInWords(
        # A step that grabs its note has no degree of its own, so its chord has no name.
        scale=editor.known_scale() if isinstance(degree, int) else None, degree=degree, accidental=editor.value(row=Row.ACCIDENTAL, step=step),
        kind=current.kind, symbol=current.quality, tensions=current.tensions, single_note=True,
    )


def step_choice(*, editor, step):
    """Return a step's quality, tensions and scale type as a ChordChoice."""
    return ChordChoice(
        quality=chord_text(editor.value(row=Row.CHORD, step=step)), tensions=editor.value(row=Row.TENSION, step=step), kind=editor.value(row=Row.CHORD_SCALE, step=step),
    )


def pick_chord(*, editor, step, opens_on=QUALITY_LIST):
    """Open the Chord dialog on a step of the pattern editor and store what it answers on the step's Chord, Tension and Scale rows:
    the Chord, Tension and Scale rows' Enter, and the roll's chord key. A single note takes no tensions. The editor underneath
    shows the chord as the choice moves (the user's design), the roll its thin lines and the rows their cells."""
    def chosen(choice):
        editor.set_value(value=chord_value(choice.quality), row=Row.CHORD, step=step)
        editor.set_value(value=None if choice.quality is None else choice.tensions, row=Row.TENSION, step=step)
        editor.set_value(value=choice.kind, row=Row.CHORD_SCALE, step=step)

    def moved(choice):
        # The chord is written as the choice moves, so that the editor underneath shows it, and written back when the dialog is cancelled; the whole is one undo step,
        # recorded when the dialog answers, or none when the step ends as it began.
        chosen(choice)
        editor.draw()

    dialog = ChordDialog(
        title=MSG_CHORD_DIALOG_TITLE.format(where=MSG_CHORD_OF_STEP.format(step=step + 1, pattern=editor.item)),
        qualities=[None, *CHORD_SYMBOLS], quality_names=[MSG_QUALITY_SINGLE_NOTE, *quality_names(CHORD_SYMBOLS)], categories=SCALE_CATEGORIES,
        current=step_choice(editor=editor, step=step), opens_on=opens_on, moved=moved,
        said=lambda choice: step_chord_in_words(editor=editor, step=step, choice=choice).sentences(),
    )
    editor.ask(dialog=dialog, then=chosen)


class ChordRow(PatternRow):
    """Enter opens the Chord dialog, Space or ] and [ cycle through the symbols, and Bksp clears."""

    KEYS = keybindings.ChordRow

    __slots__ = ()

    def keys(self):
        return [
            self.bind(self.KEYS.CHOOSE, action=self.pick),
            self.bind(self.KEYS.NEXT, action=lambda: self.cycle(STEP_FORWARD)),
            *self.adjust_keys(),
            self.bind(self.KEYS.CLEAR, action=lambda: self.set_value(None)),
        ]

    def pick(self):
        pick_chord(editor=self.editor, step=self.editor.step, opens_on=OPENS_ON[self.name])

    def nudge(self, offset):
        """[ and ] step through the choices, as they step a number on the other rows."""
        self.cycle(offset)

    def options(self):
        """Return the values the row steps through, nothing first, each as the pattern holds it."""
        return [None, *[chord_value(symbol) for symbol in CHORD_SYMBOLS]]

    def cycle(self, offset):
        options = self.options()
        value = self.value()
        shown = [chord_text(option) for option in options]
        place = shown.index(chord_text(value)) if chord_text(value) in shown else 0
        self.set_value(options[(place + offset) % len(options)])
