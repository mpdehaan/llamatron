# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What the editors say of a chord in words: the scale it is drawn from, its name there, its notes, and its
name in the clip's own scale when it borrows another. The pattern editor's status line, a progression's chord editor and the
Chord dialog all say it through here, so that a chord reads the same wherever it is edited."""

from llamatron.composition.chords import borrowed, root_name, spelled_chord
from llamatron.composition.naming import words
from llamatron.tui import drawing
from llamatron.user_strings import marks, messages


def scale_shown(scale):
    """Return a scale by its root and type, like C Harmonic Minor."""
    return marks.MSG_SCALE_NAMED.format(root=scale.get_root(), kind=words(scale.get_kind()).title())


def degree_shown(*, degree, accidental):
    """Return a degree as it is read out, a sharp or flat sign in front."""
    return marks.MSG_ACCIDENTAL_MARKS.get(accidental, drawing.NOTHING) + str(degree)


class ChordInWords:
    """One chord, in a scale that is known, said in words.

    scale is the NamedScale the chord plays under, the clip's own. single_note says a chord with no symbol is one note, as a
    pattern's step is, where a progression's chord with no quality is the scale's triad.
    """

    __slots__ = ('_scale', '_degree', '_accidental', '_kind', '_symbol', '_tensions', '_own_degree', '_single_note')

    def __init__(self, *, scale, degree, accidental=None, kind=None, symbol=None, tensions=None, own_degree=None, single_note=False):
        self._scale = scale
        self._degree = degree
        self._accidental = accidental
        self._kind = kind
        self._symbol = symbol
        self._tensions = tensions
        self._own_degree = own_degree
        self._single_note = single_note

    def is_one_note(self):
        return self._single_note and self._symbol is None

    def spelled(self, *, kind):
        return spelled_chord(scale=self._scale, degree=self._degree, accidental=self._accidental, kind=kind, symbol=self._symbol, tensions=self._tensions, own_degree=self._own_degree)

    def name(self):
        """Return the chord's short name, like A7(b9), or its one note's name."""
        if self.is_one_note():
            return root_name(scale=borrowed(scale=self._scale, kind=self._kind), degree=self._degree, accidental=self._accidental)
        return self.spelled(kind=self._kind).name

    def notes(self):
        """Return the names of the chord's notes from its root up, as one line."""
        if self.is_one_note():
            return self.name()
        return marks.MSG_NOTES_SEPARATOR.join(self.spelled(kind=self._kind).notes)

    def note_names(self):
        """Return the names of the chord's notes from its root up, or of its one note, or none when no scale is known."""
        if self._scale is None:
            return []
        if self.is_one_note():
            return [self.name()]
        return list(self.spelled(kind=self._kind).notes)

    def sentences(self):
        """Return what the Chord dialog says under its lists: the chord in its scale, the chord in the clip's own scale when it borrows another, and its notes."""
        if self._scale is None:
            return [messages.MSG_CHORD_NO_SCALE_KNOWN]
        degree = degree_shown(degree=self._degree, accidental=self._accidental)
        drawn_from = borrowed(scale=self._scale, kind=self._kind)
        if self.is_one_note():
            return [messages.MSG_NOTE_SENTENCE.format(scale=scale_shown(drawn_from), degree=degree, name=self.name())]
        lines = [messages.MSG_CHORD_SENTENCE.format(scale=scale_shown(drawn_from), degree=degree, name=self.spelled(kind=self._kind).long_name)]
        if self._kind is not None:
            lines.append(messages.MSG_CHORD_OWN_SENTENCE.format(scale=scale_shown(self._scale), name=self.spelled(kind=None).long_name))
        return [*lines, messages.MSG_CHORD_NOTES.format(notes=self.notes())]

    def resting(self, *, where):
        """Return what the status line says of the chord while the cursor rests on it, or nothing for one note or a scale that isn't known."""
        if self._scale is None or self.is_one_note():
            return drawing.NOTHING
        text = messages.MSG_CHORD_RESTING.format(
            where=where, scale=scale_shown(borrowed(scale=self._scale, kind=self._kind)), degree=degree_shown(degree=self._degree, accidental=self._accidental),
            name=self.spelled(kind=self._kind).long_name, notes=self.notes(),
        )
        if self._kind is not None:
            text += messages.MSG_CHORD_RESTING_OWN.format(scale=scale_shown(self._scale), name=self.spelled(kind=None).long_name)
        return text
