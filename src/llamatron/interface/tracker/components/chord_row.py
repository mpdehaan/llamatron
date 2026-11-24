# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Chord row: a chord symbol on a note, picked from a grid or cycled through."""


from llamatron.interface.tracker import key_table, keybindings, scale_categories
from llamatron.interface.tracker.chord_text import ChordInWords
from llamatron.interface.tracker.components.keyboard import chord_keys, Keyboard
from llamatron.interface.tracker.components.pattern_row import PatternRow
from llamatron.interface.tracker.dialogs import chord_dialog
from llamatron.interface.tracker.dialogs.chord_dialog import ChordChoice, ChordDialog
from llamatron.interface.tracker.renderers import keyboard as keyboard_renderer
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import Row
from llamatron.user_strings import labels, marks, messages

def chord_text(value):
    return None if value is None else str(value)


def chord_value(text):
    """Return a chord symbol the way a file holds it, where the scale's chords are numbers."""
    return int(text) if text and text.isdigit() else text


# The rows the Chord dialog edits together, and the list it opens on from each.
OPENS_ON = {Row.CHORD: chord_dialog.QUALITY_LIST, Row.TENSION: chord_dialog.TENSION_LIST, Row.CHORD_SCALE: chord_dialog.SCALE_LIST}


def quality_names(symbols):
    """Return what the Chord dialog calls each chord symbol: the symbol and what it is, like "m7  minor seventh"."""
    return [marks.MSG_CHORD_SYMBOL_NAMED.format(symbol=symbol, name=labels.MSG_CHORD_NAMES[symbol]) for symbol in symbols]


def step_chord_in_words(*, editor, step, choice=None):
    """Return a step's chord in words, in the scale the pattern is known to play under, with a ChordChoice in place of the step's own when one is given."""
    current = step_choice(editor=editor, step=step) if choice is None else choice
    degree = editor.value(row=Row.DEGREE, step=step)
    return ChordInWords(
        # A step that grabs its note has no degree of its own, so its chord has no name.
        scale=editor.known_scale() if isinstance(degree, int) else None, degree=degree, accidental=editor.value(row=Row.ACCIDENTAL, step=step),
        kind=current.kind, symbol=current.quality, tensions=current.tensions, single_note=True,
    )


def step_keyboard(*, editor, step, choice):
    """Return the lines of a keyboard showing a step's chord in the pattern's scale, for the Chord dialog: the scale's keys in an
    outline's colour and the chord's filled. None where the scale isn't known for certain: a drum pattern,
    a pattern its uses play under more than one scale, or a step that grabs its note."""
    if editor.is_drum() or len(editor.document().scales_of_pattern(editor.item)) != 1:
        return None
    names = step_chord_in_words(editor=editor, step=step, choice=choice).note_names()
    if not names:
        return None
    scale = editor.known_scale()
    keyboard = Keyboard(root=scale.get_root(), half_steps=scale.get_half_steps(), chord=chord_keys(note_names=names, inversion=choice.inversion if choice.quality is not None else None))
    return keyboard_renderer.keyboard_lines(rows=keyboard.rows(), styles=keyboard_renderer.CHORD_KEY_STYLES)


def step_choice(*, editor, step):
    """Return a step's quality, tensions and scale type as a ChordChoice."""
    return ChordChoice(
        quality=chord_text(editor.value(row=Row.CHORD, step=step)), inversion=editor.value(row=Row.INVERSION, step=step), tensions=editor.value(row=Row.TENSION, step=step), kind=editor.value(row=Row.CHORD_SCALE, step=step),
    )


def pick_chord(*, editor, step, opens_on=chord_dialog.QUALITY_LIST):
    """Open the Chord dialog on a step of the pattern editor and store what it answers on the step's Chord, Tension and Scale rows:
    the Chord, Tension and Scale rows' Enter, and the roll's chord key. A single note takes no tensions and no inversion, and the Inversion row is stored with them. The editor underneath
    shows the chord as the choice moves, the roll its thin lines and the rows their cells."""
    def chosen(choice):
        editor.set_value(value=chord_value(choice.quality), row=Row.CHORD, step=step)
        editor.set_value(value=None if choice.quality is None else choice.tensions, row=Row.TENSION, step=step)
        editor.set_value(value=None if choice.quality is None else choice.inversion, row=Row.INVERSION, step=step)
        editor.set_value(value=choice.kind, row=Row.CHORD_SCALE, step=step)

    def moved(choice):
        # The chord is written as the choice moves, so that the editor underneath shows it, and written back when the dialog is cancelled; the whole is one undo step,
        # recorded when the dialog answers, or none when the step ends as it began.
        chosen(choice)
        editor.draw()

    dialog = ChordDialog(
        title=messages.MSG_CHORD_DIALOG_TITLE.format(where=messages.MSG_CHORD_OF_STEP.format(step=step + 1, pattern=editor.item)),
        qualities=[None, *file_format.CHORD_SYMBOLS], quality_names=[messages.MSG_QUALITY_SINGLE_NOTE, *quality_names(file_format.CHORD_SYMBOLS)], inversions=[None, *limits.INVERSIONS], categories=scale_categories.SCALE_CATEGORIES,
        current=step_choice(editor=editor, step=step), opens_on=opens_on, moved=moved,
        said=lambda choice: step_chord_in_words(editor=editor, step=step, choice=choice).sentences(),
        keyboard=lambda choice: step_keyboard(editor=editor, step=step, choice=choice),
    )
    editor.ask(dialog=dialog, then=chosen)


class ChordRow(PatternRow):
    """Enter opens the Chord dialog, Space or ] and [ step through the symbols, stopping at the first and the last, and Bksp clears."""

    KEYS = keybindings.ChordRow

    __slots__ = ()

    def keys(self):
        return [
            self.bind(self.KEYS.CHOOSE, action=self.pick),
            self.bind(self.KEYS.NEXT, action=lambda: self.cycle(key_table.STEP_FORWARD)),
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
        return [None, *[chord_value(symbol) for symbol in file_format.CHORD_SYMBOLS]]

    def cycle(self, offset):
        options = self.options()
        value = self.value()
        shown = [chord_text(option) for option in options]
        place = shown.index(chord_text(value)) if chord_text(value) in shown else 0
        # The choices stop at both ends and never go round, as a chord's quality, tensions and scale never do.
        self.set_value(options[max(min(place + offset, len(options) - 1), 0)])
