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
"""One scale's page: its name, root and kind on one page, with its notes underneath.

It replaced the Scales page's two pickers in a row on 2026-11-07, as the user asked: left and right
step the root and the kind, and Enter opens the root keyboard or the pages of kinds.
"""

from rich.text import Text

from llamatron.composition.file_format import ScaleKind, Section
from llamatron.composition.named_scale import note_names, SCALE_TYPE_NAMES
from llamatron.music.note import FLAT_NAMES, NoteName, ROOT_NAMES, SHARP_NAMES
from llamatron.music.scale import ScaleType
from llamatron.tui.components.keyboard import Keyboard
from llamatron.tui.dialogs.grid_choice_dialog import GridChoiceDialog, grouped_grid
from llamatron.tui.drawing import INDENT, NOTHING, SPACE, Style
from llamatron.strings.help import HELP_SCALE_PAGE
from llamatron.tui.screens.field import Field, NameField
from llamatron.tui.screens.field_page import FieldPage
from llamatron.tui.screens.shared import stepped
from llamatron.composition.naming import words
from llamatron.strings.labels import (
    Crumb, MSG_KIND_LABEL, MSG_ROOT_LABEL, MSG_SHORT_SCALE_NAMES, MSG_SCALE_GROUP_EAST_ASIA, MSG_SCALE_GROUP_INDIA,
    MSG_SCALE_GROUP_JAZZ, MSG_SCALE_GROUP_MELODIC_MINOR, MSG_SCALE_GROUP_MIDDLE_EAST_AND_EUROPE, MSG_SCALE_GROUP_MINOR_AND_MAJOR,
    MSG_SCALE_GROUP_MODES, MSG_SCALE_GROUP_PENTATONIC_AND_BLUES, MSG_SCALE_GROUP_SYMMETRIC, MSG_SCALE_PAGE_COMMON,
    MSG_SCALE_PAGE_JAZZ_AND_WORLD,
)
from llamatron.strings.legends import What
from llamatron.tui.screens.shows_named_item import ShowsNamedItem
from llamatron.strings.messages import MSG_KIND_TITLE, MSG_RENAME_SCALE_PROMPT, MSG_ROOT_TITLE, MSG_SCALE_NOTES_DETAIL, MSG_SCALE_USES_NOTE
from llamatron.tui import keybindings


# The kinds of scale, in two pages of grouped columns, as the picker lays them out.
SCALE_PAGES = [
    (MSG_SCALE_PAGE_COMMON, [
        [(MSG_SCALE_GROUP_MODES, [
            ScaleKind.MAJOR, ScaleKind.IONIAN, ScaleKind.DORIAN, ScaleKind.PHRYGIAN, ScaleKind.LYDIAN, ScaleKind.MIXOLYDIAN,
            ScaleKind.MINOR, ScaleKind.AEOLIAN, ScaleKind.NATURAL_MINOR, ScaleKind.LOCRIAN,
        ])],
        [(MSG_SCALE_GROUP_MINOR_AND_MAJOR, [ScaleKind.HARMONIC_MINOR, ScaleKind.MELODIC_MINOR, ScaleKind.HARMONIC_MAJOR]),
         (MSG_SCALE_GROUP_SYMMETRIC, [
             ScaleKind.CHROMATIC, ScaleKind.WHOLE_TONE, ScaleKind.WHOLE_HALF_DIMINISHED, ScaleKind.HALF_WHOLE_DIMINISHED,
             ScaleKind.AUGMENTED,
         ])],
        [(MSG_SCALE_GROUP_PENTATONIC_AND_BLUES, [
            ScaleKind.MAJOR_PENTATONIC, ScaleKind.MINOR_PENTATONIC, ScaleKind.BLUES, ScaleKind.MAJOR_BLUES, ScaleKind.EGYPTIAN,
        ])],
    ]),
    (MSG_SCALE_PAGE_JAZZ_AND_WORLD, [
        [(MSG_SCALE_GROUP_MELODIC_MINOR, [
            ScaleKind.MELODIC_MINOR, ScaleKind.DORIAN_FLAT2, ScaleKind.LYDIAN_AUGMENTED, ScaleKind.LYDIAN_DOMINANT,
            ScaleKind.MIXOLYDIAN_FLAT6, ScaleKind.LOCRIAN_NATURAL2, ScaleKind.ALTERED,
        ]),
         (MSG_SCALE_GROUP_JAZZ, [ScaleKind.BEBOP_DOMINANT, ScaleKind.BEBOP_MAJOR, ScaleKind.PROMETHEUS])],
        [(MSG_SCALE_GROUP_MIDDLE_EAST_AND_EUROPE, [
            ScaleKind.PHRYGIAN_DOMINANT, ScaleKind.DOUBLE_HARMONIC, ScaleKind.HUNGARIAN_MINOR, ScaleKind.HUNGARIAN_MAJOR,
            ScaleKind.UKRAINIAN_DORIAN, ScaleKind.PERSIAN, ScaleKind.NEAPOLITAN_MINOR, ScaleKind.NEAPOLITAN_MAJOR,
            ScaleKind.ENIGMATIC,
        ])],
        [(MSG_SCALE_GROUP_EAST_ASIA, [ScaleKind.HIRAJOSHI, ScaleKind.IN_SEN, ScaleKind.IWATO, ScaleKind.KUMOI, ScaleKind.YO, ScaleKind.RYUKYU]),
         (MSG_SCALE_GROUP_INDIA, [ScaleKind.TODI, ScaleKind.MARWA, ScaleKind.PURVI])],
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
    return MSG_SHORT_SCALE_NAMES.get(kind, words(kind))


def scale_notes(*, root, kind):
    """Return a scale's notes as one line, like D E F G A B C, spelled as the rest of the program spells them."""
    return SPACE.join(note_names(root=root, half_steps=ScaleType[kind.upper()].value))


def kind_pages():
    """Return the picker's pages of kinds, each a grid of places in SCALE_TYPE_NAMES under its headings."""
    return [
        (page, grouped_grid([[(heading, [SCALE_TYPE_NAMES.index(name) for name in names]) for heading, names in groups] for groups in columns]))
        for page, columns in SCALE_PAGES
    ]


def root_grid():
    """Return the keyboard as a grid of places in ROOT_NAMES, with None where a key has no flat."""
    return [[None if name is None else ROOT_NAMES.index(name) for name in row] for row in ROOT_KEYBOARD]


class ScalePage(ShowsNamedItem, FieldPage):
    """A scale's name, root and kind, with the notes they make underneath."""

    KEYS = keybindings.ScalePage

    HELP = HELP_SCALE_PAGE
    SECTION = Section.SCALES
    CRUMBS_BEFORE = (Crumb.SCALES,)
    RENAME_PROMPT = MSG_RENAME_SCALE_PROMPT

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

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
        names = FLAT_NAMES if root in FLAT_NAMES and root not in SHARP_NAMES else SHARP_NAMES
        self.set_root(stepped(values=names, current=root, offset=offset))

    def pick_root(self):
        """Choose the root on a keyboard."""
        place = ROOT_NAMES.index(self.root())
        self.ask(dialog=GridChoiceDialog(title=MSG_ROOT_TITLE, options=ROOT_NAMES, grid=root_grid(), current=place), then=lambda chosen: self.set_root(ROOT_NAMES[chosen]))

    def pick_kind(self):
        """Choose the kind from its pages, with the notes of the one under the cursor shown underneath."""
        root = self.root()
        kinds = [scale_label(text) for text in SCALE_TYPE_NAMES]

        def notes(place):
            return MSG_SCALE_NOTES_DETAIL.format(root=root, kind=kinds[place], notes=scale_notes(root=root, kind=SCALE_TYPE_NAMES[place]))
        place = SCALE_TYPE_NAMES.index(self.kind())
        dialog = GridChoiceDialog(title=MSG_KIND_TITLE.format(root=root), options=kinds, grid=None, current=place, details=notes, pages=kind_pages())
        self.ask(dialog=dialog, then=lambda chosen: self.set_kind(SCALE_TYPE_NAMES[chosen]))

    def fields(self):
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            Field(label=MSG_ROOT_LABEL, value=self.root, adjust=self.step_root,
                  enter=self.pick_root, enter_what=What.CHOOSE),
            Field(label=MSG_KIND_LABEL, value=lambda: words(self.kind()), adjust=lambda d: self.set_kind(stepped(values=SCALE_TYPE_NAMES, current=self.kind(), offset=d)),
                  enter=self.pick_kind, enter_what=What.CHOOSE),
        ]

    def notes(self, width):
        """Return the scale's notes and uses, then a keyboard with the scale's keys filled and the root bracketed."""
        uses = len(self.document().uses(section=Section.SCALES, name=self.item))
        keyboard = Keyboard(root=self.root(), half_steps=self.scale().get_half_steps())
        return [
            Text(INDENT + MSG_SCALE_NOTES_DETAIL.format(root=self.root(), kind=scale_label(self.kind()), notes=scale_notes(root=self.root(), kind=self.kind())), style=Style.DIM),
            Text(MSG_SCALE_USES_NOTE.format(count=uses), style=Style.DIM),
            Text(NOTHING),
            *[Text(line, no_wrap=True) for line in keyboard.lines()],
        ]
