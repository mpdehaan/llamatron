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
"""The wizard's Chords branch, under Composition: the chord progression the song is built on, with its numerals and its chords in the song's key."""

from rich.text import Text

from llamatron.composition.chords import root_name
from llamatron.composition.named_scale import NamedScale
from llamatron.composition.progressions import quality_of, roman_numeral
from llamatron.strings.labels import MSG_WIZARD_ANY_PROGRESSION, MSG_WIZARD_CHORDS_BRANCH, MSG_WIZARD_PROGRESSION_LABEL, MSG_WIZARD_SCALE_TYPE_NAMES
from llamatron.strings.marks import MSG_NUMERALS_SEPARATOR, MSG_WIZARD_CHORD_SEPARATOR, MSG_WIZARD_CHORD_SUFFIXES, MSG_WIZARD_CHORDS_KEY, MSG_WIZARD_CHORDS_LINE, MSG_WIZARD_PROGRESSION_FOR, MSG_WIZARD_PROGRESSION_SHOWN
from llamatron.strings.messages import MSG_WIZARD_CHORDS_DRAWN_LATER
from llamatron.tui.drawing import INDENT, Style
from llamatron.tui.screens.shared.field import ChoiceField
from llamatron.tui.screens.wizard.song_ways_branch import A_CHOICE, SongWaysBranch


class ChordsBranch(SongWaysBranch):
    """The song's Progression, each shown with its numerals, and under the field the chords each kind of section plays in the
    song's key; a section's own chords are to come."""

    __slots__ = ()

    def name(self):
        return MSG_WIZARD_CHORDS_BRANCH

    def traits(self):
        return []

    def offers_progressions(self):
        """Return whether the subgenre has more than one progression, since one is nothing to choose."""
        choices = self.choices()
        trait = choices.progression_trait() if choices.is_ready() else None
        return trait is not None and len(choices.song_ways(trait)) >= A_CHOICE

    def progression(self):
        """Return the progression chosen, or the word for one left to chance."""
        choices = self.choices()
        return MSG_WIZARD_ANY_PROGRESSION if choices.has_any_progression() else choices.get_way(choices.progression_trait())

    def set_progression(self, progression):
        choices = self.choices()
        if progression == MSG_WIZARD_ANY_PROGRESSION:
            choices.set_any_progression()
        else:
            choices.set_way(trait=choices.progression_trait(), value=progression)

    def scale(self):
        """Return the song's scale, which numerals and chord names are spelled in."""
        return NamedScale(root=self.choices().get_root(), kind=self.choices().get_scale_type())

    def numerals(self, chords):
        """Return chords, each a degree and its sharp or flat, as Roman numerals in the song's scale."""
        scale = self.scale()
        return MSG_NUMERALS_SEPARATOR.join(roman_numeral(scale=scale, degree=degree, accidental=accidental) for degree, accidental in chords)

    def chord_names(self, chords):
        """Return chords as their names in the song's key, as the song plays them."""
        scale = self.scale()
        return MSG_WIZARD_CHORD_SEPARATOR.join(
            root_name(scale=scale, degree=degree, accidental=accidental) + MSG_WIZARD_CHORD_SUFFIXES[quality_of(scale=scale, degree=degree, accidental=accidental)] for degree, accidental in chords)

    def shown(self, progression):
        """Return a progression as the field and its list show it: its name, its numerals where it is written as degrees, and the scale type it was written for where that is not the song's."""
        if progression == MSG_WIZARD_ANY_PROGRESSION:
            return progression
        choices = self.choices()
        degrees = choices.progression_degrees(progression)
        shown = MSG_WIZARD_PROGRESSION_SHOWN.format(name=progression, numerals=self.numerals(degrees)) if degrees else progression
        # A progression written for the other of major and minor says so: its borrowed chords were not meant for the song's scale.
        written_for = choices.progression_scale_type(progression)
        return shown if written_for == choices.get_scale_type() else MSG_WIZARD_PROGRESSION_FOR.format(progression=shown, scale=MSG_WIZARD_SCALE_TYPE_NAMES[written_for])

    def summary(self):
        return self.shown(self.progression()) if self.offers_progressions() else None

    def fields(self):
        if not self.offers_progressions():
            return []
        choices = self.choices()
        # The first choice, the one a song starts with, leaves the progression to chance: each run takes one of the subgenre's.
        offered = [MSG_WIZARD_ANY_PROGRESSION, *choices.song_ways(choices.progression_trait())]
        return [ChoiceField(page=self.page(), label=MSG_WIZARD_PROGRESSION_LABEL, choices=offered, names=[self.shown(progression) for progression in offered],
                            current=self.progression(), shown=self.shown(self.progression()), set=self.page().choosing(self.set_progression))]

    def notes(self, width):
        """Return the chords each kind of section plays in the song's key, under the key's name; that they are drawn later while
        the progression is left to chance; or that there is nothing to choose."""
        if not self.offers_progressions():
            return super().notes(width)
        choices = self.choices()
        if choices.has_any_progression():
            return [Text(), Text(INDENT + MSG_WIZARD_CHORDS_DRAWN_LATER, style=Style.DIM)]
        sections = choices.progression_chords(self.progression())
        if not sections:
            return []
        longest = max(len(kind) for kind, _ in sections)
        key = MSG_WIZARD_CHORDS_KEY.format(root=choices.get_root(), scale=MSG_WIZARD_SCALE_TYPE_NAMES[choices.get_scale_type()])
        return [Text(), Text(INDENT + key, style=Style.DIM),
                *(Text(INDENT + MSG_WIZARD_CHORDS_LINE.format(kind=kind, width=longest, chords=self.chord_names(chords))) for kind, chords in sections)]
