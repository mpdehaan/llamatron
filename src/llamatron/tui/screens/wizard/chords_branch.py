# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The wizard's Chords branch, under Composition: the chord progression the song is built on, with its numerals and its chords in the song's key."""

from rich.text import Text

from llamatron.model.objects.named_scale import NamedScale
from llamatron.model.values.chords import root_name
from llamatron.model.values.progressions import quality_of, roman_numeral
from llamatron.tui import drawing
from llamatron.tui.drawing import Style
from llamatron.tui.screens.shared.field import ChoiceField
from llamatron.tui.screens.wizard import song_ways_branch
from llamatron.tui.screens.wizard.song_ways_branch import SongWaysBranch
from llamatron.user_strings import labels, marks, messages


class ChordsBranch(SongWaysBranch):
    """The song's Progression, each shown with its numerals, and under the field the chords each kind of section plays in the
    song's key; a section's own chords are to come."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_CHORDS_BRANCH

    def traits(self):
        return []

    def offers_progressions(self):
        """Return whether the subgenre has more than one progression, since one is nothing to choose."""
        choices = self.get_choices()
        trait = choices.progression_trait() if choices.is_ready() else None
        return trait is not None and len(choices.get_band().song_ways(trait)) >= song_ways_branch.A_CHOICE

    def progression(self):
        """Return the progression chosen, or the word for one left to chance."""
        choices = self.get_choices()
        return labels.MSG_WIZARD_ANY_PROGRESSION if choices.has_any_progression() else choices.get_band().get_way(choices.progression_trait())

    def set_progression(self, progression):
        choices = self.get_choices()
        if progression == labels.MSG_WIZARD_ANY_PROGRESSION:
            choices.set_any_progression()
        else:
            choices.get_band().set_way(trait=choices.progression_trait(), value=progression)

    def scale(self):
        """Return the song's scale, which numerals and chord names are spelled in."""
        return NamedScale(root=self.get_choices().get_root(), kind=self.get_choices().get_scale_type())

    def numerals(self, chords):
        """Return chords, each a degree and its sharp or flat, as Roman numerals in the song's scale."""
        scale = self.scale()
        return marks.MSG_NUMERALS_SEPARATOR.join(roman_numeral(scale=scale, degree=degree, accidental=accidental) for degree, accidental in chords)

    def chord_names(self, chords):
        """Return chords as their names in the song's key, as the song plays them."""
        scale = self.scale()
        return marks.MSG_WIZARD_CHORD_SEPARATOR.join(
            root_name(scale=scale, degree=degree, accidental=accidental) + marks.MSG_WIZARD_CHORD_SUFFIXES[quality_of(scale=scale, degree=degree, accidental=accidental)] for degree, accidental in chords)

    def shown(self, progression):
        """Return a progression as the field and its list show it: its name, its numerals where it is written as degrees, and the scale type it was written for where that is not the song's."""
        if progression == labels.MSG_WIZARD_ANY_PROGRESSION:
            return progression
        choices = self.get_choices()
        degrees = choices.progression_degrees(progression)
        shown = marks.MSG_WIZARD_PROGRESSION_SHOWN.format(name=progression, numerals=self.numerals(degrees)) if degrees else progression
        # A progression written for the other of major and minor says so: its borrowed chords were not meant for the song's scale.
        written_for = choices.progression_scale_type(progression)
        return shown if written_for == choices.get_scale_type() else marks.MSG_WIZARD_PROGRESSION_FOR.format(progression=shown, scale=labels.MSG_WIZARD_SCALE_TYPE_NAMES[written_for])

    def summary(self):
        return self.shown(self.progression()) if self.offers_progressions() else None

    def fields(self):
        if not self.offers_progressions():
            return []
        choices = self.get_choices()
        # The first choice, the one a song starts with, leaves the progression to chance: each run takes one of the subgenre's.
        offered = [labels.MSG_WIZARD_ANY_PROGRESSION, *choices.get_band().song_ways(choices.progression_trait())]
        return [ChoiceField(page=self.get_page(), label=labels.MSG_WIZARD_PROGRESSION_LABEL, choices=offered, names=[self.shown(progression) for progression in offered],
                            current=self.progression(), shown=self.shown(self.progression()), set=self.get_page().choosing(self.set_progression))]

    def remarks(self, width):
        """Return the chords each kind of section plays in the song's key, under the key's name; that they are drawn later while
        the progression is left to chance; or that there is nothing to choose."""
        if not self.offers_progressions():
            return super().remarks(width)
        choices = self.get_choices()
        if choices.has_any_progression():
            return [Text(), Text(drawing.INDENT + messages.MSG_WIZARD_CHORDS_DRAWN_LATER, style=Style.DIM)]
        sections = choices.progression_chords(self.progression())
        if not sections:
            return []
        longest = max(len(kind) for kind, _ in sections)
        key = marks.MSG_WIZARD_CHORDS_KEY.format(root=choices.get_root(), scale=labels.MSG_WIZARD_SCALE_TYPE_NAMES[choices.get_scale_type()])
        return [Text(), Text(drawing.INDENT + key, style=Style.DIM),
                *(Text(drawing.INDENT + marks.MSG_WIZARD_CHORDS_LINE.format(kind=kind, width=longest, chords=self.chord_names(chords))) for kind, chords in sections)]
