# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""One scale's page: its name, root and kind on one page, with its notes underneath.

It replaced the Scales page's two pickers in a row: left and right
step the root and the kind, and Enter opens the root keyboard or the pages of kinds.
"""

from rich.text import Text

from llamatron.composition import named_scale
from llamatron.composition.file_format import ScaleKind, Section
from llamatron.composition.named_scale import note_names
from llamatron.composition.naming import words
from llamatron.music import note
from llamatron.music.note import NoteName
from llamatron.music.scale import ScaleType
from llamatron.strings import help as help_text, labels, legends, messages
from llamatron.tui import drawing, keybindings
from llamatron.tui.components.keyboard import Keyboard
from llamatron.tui.dialogs.grid_choice_dialog import GridChoiceDialog, grouped_grid
from llamatron.tui.drawing import Style
from llamatron.tui.screens.shared.field import Field, NameField
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.shared import stepped
from llamatron.tui.screens.shared.shows_named_item import ShowsNamedItem


# The kinds of scale, in two pages of grouped columns, as the picker lays them out.
SCALE_PAGES = [
    (labels.MSG_SCALE_PAGE_COMMON, [
        [(labels.MSG_SCALE_GROUP_MODES, [
            ScaleKind.MAJOR, ScaleKind.IONIAN, ScaleKind.DORIAN, ScaleKind.PHRYGIAN, ScaleKind.LYDIAN, ScaleKind.MIXOLYDIAN,
            ScaleKind.MINOR, ScaleKind.AEOLIAN, ScaleKind.NATURAL_MINOR, ScaleKind.LOCRIAN,
        ])],
        [(labels.MSG_SCALE_GROUP_MINOR_AND_MAJOR, [ScaleKind.HARMONIC_MINOR, ScaleKind.MELODIC_MINOR, ScaleKind.HARMONIC_MAJOR]),
         (labels.MSG_SCALE_GROUP_SYMMETRIC, [
             ScaleKind.CHROMATIC, ScaleKind.WHOLE_TONE, ScaleKind.WHOLE_HALF_DIMINISHED, ScaleKind.HALF_WHOLE_DIMINISHED,
             ScaleKind.AUGMENTED,
         ])],
        [(labels.MSG_SCALE_GROUP_PENTATONIC_AND_BLUES, [
            ScaleKind.MAJOR_PENTATONIC, ScaleKind.MINOR_PENTATONIC, ScaleKind.BLUES, ScaleKind.MAJOR_BLUES, ScaleKind.EGYPTIAN,
        ])],
    ]),
    (labels.MSG_SCALE_PAGE_JAZZ_AND_WORLD, [
        [(labels.MSG_SCALE_GROUP_MELODIC_MINOR, [
            ScaleKind.MELODIC_MINOR, ScaleKind.DORIAN_FLAT2, ScaleKind.LYDIAN_AUGMENTED, ScaleKind.LYDIAN_DOMINANT,
            ScaleKind.MIXOLYDIAN_FLAT6, ScaleKind.LOCRIAN_NATURAL2, ScaleKind.ALTERED,
        ]),
         (labels.MSG_SCALE_GROUP_JAZZ, [ScaleKind.BEBOP_DOMINANT, ScaleKind.BEBOP_MAJOR, ScaleKind.PROMETHEUS])],
        [(labels.MSG_SCALE_GROUP_MIDDLE_EAST_AND_EUROPE, [
            ScaleKind.PHRYGIAN_DOMINANT, ScaleKind.DOUBLE_HARMONIC, ScaleKind.HUNGARIAN_MINOR, ScaleKind.HUNGARIAN_MAJOR,
            ScaleKind.UKRAINIAN_DORIAN, ScaleKind.PERSIAN, ScaleKind.NEAPOLITAN_MINOR, ScaleKind.NEAPOLITAN_MAJOR,
            ScaleKind.ENIGMATIC,
        ])],
        [(labels.MSG_SCALE_GROUP_EAST_ASIA, [ScaleKind.HIRAJOSHI, ScaleKind.IN_SEN, ScaleKind.IWATO, ScaleKind.KUMOI, ScaleKind.YO, ScaleKind.RYUKYU]),
         (labels.MSG_SCALE_GROUP_INDIA, [ScaleKind.TODI, ScaleKind.MARWA, ScaleKind.PURVI])],
    ]),
]
# The roots as a keyboard: each flat under the sharp it shares a key with.
ROOT_KEYBOARD = [
    [NoteName.C, NoteName.C_SHARP, NoteName.D, NoteName.D_SHARP, NoteName.E, NoteName.F,
     NoteName.F_SHARP, NoteName.G, NoteName.G_SHARP, NoteName.A, NoteName.A_SHARP, NoteName.B],
    [None, NoteName.D_FLAT, None, NoteName.E_FLAT, None, None,
     NoteName.G_FLAT, None, NoteName.A_FLAT, None, NoteName.B_FLAT, None],
]


def scale_label(kind):
    """Return a kind of scale as the picker shows it, shortened where the long name wouldn't fit."""
    return labels.MSG_SHORT_SCALE_NAMES.get(kind, words(kind))


def scale_notes(*, root, kind):
    """Return a scale's notes as one line, like D E F G A B C, spelled as the rest of the program spells them."""
    return drawing.SPACE.join(note_names(root=root, half_steps=ScaleType[kind.upper()].value))


def kind_pages():
    """Return the picker's pages of kinds, each a grid of places in SCALE_TYPE_NAMES under its headings."""
    return [(page, kinds_grid(columns)) for page, columns in SCALE_PAGES]


def kinds_grid(columns):
    """Return a page of the picker as a grid of places in SCALE_TYPE_NAMES under its headings, from its columns of groups."""
    return grouped_grid([headed_places(groups) for groups in columns])


def headed_places(groups):
    """Return a column of the picker as its headings, each with the places of its scale types in SCALE_TYPE_NAMES."""
    return [(heading, scale_type_places(names)) for heading, names in groups]


def scale_type_places(names):
    """Return where each scale type named is in SCALE_TYPE_NAMES."""
    return [named_scale.SCALE_TYPE_NAMES.index(name) for name in names]


def root_grid():
    """Return the keyboard as a grid of places in ROOT_NAMES, with None where a key has no flat."""
    return [root_places(row) for row in ROOT_KEYBOARD]


class ScalePage(ShowsNamedItem, FieldPage):
    """A scale's name, root and kind, with the notes they make underneath."""

    KEYS = keybindings.ScalePage

    HELP = help_text.HELP_SCALE_PAGE
    SECTION = Section.SCALES
    CRUMBS_BEFORE = (labels.Crumb.SCALES,)
    RENAME_PROMPT = messages.MSG_RENAME_SCALE_PROMPT

    def scale(self):
        return self.document().song().get_named_scale(self.item)

    def root(self):
        return self.scale().get_root()

    def kind(self):
        return self.scale().get_kind()

    def set_root(self, root):
        # A scale still named after its root and kind is renamed with them, so the page shows the scale under the name the change left.
        self.show_item(self.document().set_scale_root(name=self.item, root=root))

    def set_kind(self, kind):
        self.show_item(self.document().set_scale_kind(name=self.item, kind=kind))

    def step_root(self, offset):
        """Move the root up or down a half step, keeping flats flat and anything else sharp."""
        root = self.root()
        names = note.FLAT_NAMES if root in note.FLAT_NAMES and root not in note.SHARP_NAMES else note.SHARP_NAMES
        self.set_root(stepped(values=names, current=root, offset=offset))

    def pick_root(self):
        """Choose the root on a keyboard."""
        place = note.ROOT_NAMES.index(self.root())
        self.ask(dialog=GridChoiceDialog(title=messages.MSG_ROOT_TITLE, options=note.ROOT_NAMES, grid=root_grid(), current=place), then=lambda chosen: self.set_root(note.ROOT_NAMES[chosen]))

    def pick_kind(self):
        """Choose the kind from its pages, with the notes of the one under the cursor shown underneath."""
        root = self.root()
        kinds = [scale_label(text) for text in named_scale.SCALE_TYPE_NAMES]

        def notes(place):
            return messages.MSG_SCALE_NOTES_DETAIL.format(root=root, kind=kinds[place], notes=scale_notes(root=root, kind=named_scale.SCALE_TYPE_NAMES[place]))
        place = named_scale.SCALE_TYPE_NAMES.index(self.kind())
        dialog = GridChoiceDialog(title=messages.MSG_KIND_TITLE.format(root=root), options=kinds, grid=None, current=place, details=notes, pages=kind_pages())
        self.ask(dialog=dialog, then=lambda chosen: self.set_kind(named_scale.SCALE_TYPE_NAMES[chosen]))

    def fields(self):
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            Field(label=labels.MSG_ROOT_LABEL, value=self.root, adjust=self.step_root,
                  enter=self.pick_root, enter_what=legends.What.CHOOSE),
            Field(label=labels.MSG_KIND_LABEL, value=lambda: words(self.kind()), adjust=lambda d: self.set_kind(stepped(values=named_scale.SCALE_TYPE_NAMES, current=self.kind(), offset=d)),
                  enter=self.pick_kind, enter_what=legends.What.CHOOSE),
        ]

    def remarks(self, width):
        """Return the scale's notes and uses, then a keyboard with the scale's keys filled and the root bracketed."""
        uses = len(self.document().uses(section=Section.SCALES, name=self.item))
        keyboard = Keyboard(root=self.root(), half_steps=self.scale().get_half_steps())
        return [
            Text(drawing.INDENT + messages.MSG_SCALE_NOTES_DETAIL.format(root=self.root(), kind=scale_label(self.kind()), notes=scale_notes(root=self.root(), kind=self.kind())), style=Style.DIM),
            Text(messages.MSG_SCALE_USES_NOTE.format(count=uses), style=Style.DIM),
            Text(drawing.NOTHING),
            *[Text(line, no_wrap=True) for line in keyboard.lines()],
        ]


def root_places(row):
    """Return where each key of a row of the keyboard is in ROOT_NAMES, None where a key has no flat."""
    return [None if name is None else note.ROOT_NAMES.index(name) for name in row]
