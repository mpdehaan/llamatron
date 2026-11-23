# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""One scale's page as a presenter: its name, root and kind, each a field, and what is said under them, its notes and how many
things use it. The root and the kind step through their lists; Enter opens a picker the tracker gives it, the root keyboard
or the pages of kinds."""

from llamatron.interface.forms.nodes import Field, NameField, stepped
from llamatron.interface.forms.text import counted, in_a_sentence
from llamatron.model.objects.naming import words
from llamatron.model.schema.file_format import Section
from llamatron.model.values import note, scale as scale_values
from llamatron.model.values.scale import ScaleType
from llamatron.user_strings import labels, legends, messages

# Between the notes of a scale as one line.
NOTE_GAP = ' '


class ScalePresenter:
    """What the Scale page shows and does for one of the set's scales, by name. Its page does what only the tracker can:
    show_item(name) shows the page under the name a change gives the scale, since one named after its root and kind is renamed
    with them, rename() renames it, and pick_root() and pick_kind() open the tracker's pickers."""

    __slots__ = ('_page', '_document', '_name')

    def __init__(self, *, page, document, name):
        self._page = page
        self._document = document
        self._name = name

    def scale(self):
        return self._document.song().get_setlist().get_named_scale(self._name)

    def root(self):
        return self.scale().get_root()

    def kind(self):
        return self.scale().get_kind()

    def form(self):
        """Return the page's form: the scale's name, its root and its kind."""
        return [
            NameField(value=lambda: self._name, rename=self._page.rename),
            Field(label=labels.MSG_ROOT_LABEL, value=self.root, adjust=self.step_root, enter=self._page.pick_root, enter_what=legends.What.CHOOSE),
            Field(label=labels.MSG_KIND_LABEL, value=lambda: words(self.kind()), adjust=self.step_kind, enter=self._page.pick_kind, enter_what=legends.What.CHOOSE),
        ]

    def set_root(self, root):
        self._page.show_item(self._document.set_scale_root(name=self._name, root=root))

    def set_kind(self, kind):
        self._page.show_item(self._document.set_scale_kind(name=self._name, kind=kind))

    def step_root(self, offset):
        """Move the root up or down a half step, keeping flats flat and anything else sharp."""
        root = self.root()
        names = note.FLAT_NAMES if root in note.FLAT_NAMES and root not in note.SHARP_NAMES else note.SHARP_NAMES
        self.set_root(stepped(values=names, current=root, offset=offset))

    def step_kind(self, offset):
        """Move to the kind before or after in the list of every kind."""
        self.set_kind(stepped(values=scale_values.SCALE_TYPE_NAMES, current=self.kind(), offset=offset))

    def notes_line(self):
        """Return the scale's notes as one line under the fields, like D Dorian: D E F G A B C."""
        return messages.MSG_SCALE_NOTES_DETAIL.format(root=self.root(), kind=scale_label(self.kind()), notes=scale_notes(root=self.root(), kind=self.kind()))

    def uses_line(self):
        """Return how many songs, scenes and clips of the set use the scale, each counted in words, or that nothing does."""
        setlist = self._document.get_setlist()
        counts = (
            (len(setlist.songs_naming(section=Section.SCALES, name=self._name)), messages.MSG_SONGS_COUNTED),
            (len(setlist.scenes_naming(section=Section.SCALES, name=self._name)), messages.MSG_SCENES_COUNTED),
            (len(setlist.clip_slots_naming(section=Section.SCALES, name=self._name)), messages.MSG_CLIPS_COUNTED),
        )
        parts = [counted(count=count, words=words) for count, words in counts if count]
        if not parts:
            return messages.MSG_SCALE_UNUSED_NOTE
        return messages.MSG_SCALE_USES_NOTE.format(uses=in_a_sentence(parts))


def scale_label(kind):
    """Return a kind of scale as the picker shows it, shortened where the long name wouldn't fit."""
    return labels.MSG_SHORT_SCALE_NAMES.get(kind, words(kind))


def scale_notes(*, root, kind):
    """Return a scale's notes as one line, like D E F G A B C, spelled as the rest of the program spells them."""
    return NOTE_GAP.join(scale_values.note_names(root=root, half_steps=ScaleType[kind.upper()].value))
