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
"""The song wizard's choices: what a subgenre fills in, what each setter refuses, the choices kept and read back, and the song made."""

"""Every choice the song wizard offers changes the song that is made, the user's rule: a choice that changes nothing is a field
that lies. Each choice of each subgenre is made alone on fresh choices and the song arranged from it is held against the song
arranged without it. The choices known to change nothing are counted, by genre and kind, in KNOWN_TO_CHANGE_NOTHING with the
reason; a count that moves either way fails, so that a new dead choice is caught and a fixed one is taken off the list."""

import collections
import unittest

from llamatron.composition.file_format import Section
from llamatron.support.version import VERSION
from llamatron.macro_composer.wizard_choices import (BAND_SOUNDS, FEWEST_FILLS, FILLS_TRAITS, LEAST_BUSY, MOST_BUSY, MOST_FILLS, ONE_GUITARIST_COUNT,
                                                     USUAL_SOUNDS, WizardChoices, genre_names)

A_NAME = 'a_song'
NOTES_KEPT = 'notes'
WIZARD_CHOICES_KEPT = 'wizard'
A_SEED = 7
ANOTHER_SEED = 8
A_SOUND_OF_NO_STYLE = 105
A_LITTLE_FASTER = 7
FIRST_PLACE = 0
HALVES = 2
# The kinds of choice.
WAY = 'a way of playing'
BUSY = 'busy'
SOUND = 'sound'
PLAYER_OUT = 'a player left out'
BAND_SOUND = "the band's sounds"
PROGRESSION = 'progression'
FILLS = 'fills'
MELODY = 'melody'
FILLS_COME = 'fills come'
KIT_PIECE = 'a piece of the kit'
QUIET_NOTES = 'quiet notes'
GUITARISTS = 'guitarists'
SEED = 'seed'
TEMPO = 'tempo'
SECTION_BARS = "a section's bars"
SECTION_KIND = "a section's kind"
FORM = 'form'
# How many choices of each kind change nothing, by genre, and why each is allowed for now:
# - busy: two positions of the Busy gauge that a style writes the same way for a player; the templates are to gain a way for each.
# - a way of playing, busy and fills come in electronic: ambient's form gives the drums no section, so nothing of the drums is heard.
# - fills: the fill chosen is the one the drummer plays unasked.
# - fills come, elsewhere: the position chosen brings fills as often as the drummer does unasked in that subgenre's sections.
FIRST_HALF = 0
SECOND_HALF = 1
KNOWN_TO_CHANGE_NOTHING = {
    ('blues', FIRST_HALF): {BUSY: 3},
    ('blues', SECOND_HALF): {BUSY: 3},
    ('electronic', FIRST_HALF): {BUSY: 19, WAY: 21, FILLS_COME: 3, FILLS: 8},
    ('electronic', SECOND_HALF): {BUSY: 25, FILLS: 7},
    ('rock', FIRST_HALF): {BUSY: 5},
    ('rock', SECOND_HALF): {BUSY: 3, FILLS_COME: 1},
    ('sixties_pop', FIRST_HALF): {BUSY: 4, FILLS_COME: 1},
    ('sixties_pop', SECOND_HALF): {BUSY: 3},
    ('soul_funk', FIRST_HALF): {BUSY: 5, FILLS_COME: 1},
    ('soul_funk', SECOND_HALF): {BUSY: 3},
}
LABEL = '{subgenre}: {what}'


def fresh(*, genre, subgenre):
    """Choices for a subgenre with a seed and its usual progression chosen, so that one choice alone differs from the next."""
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre)
    choices.set_seed(A_SEED)
    trait = choices.progression_trait()
    if trait is not None:
        choices.set_way(trait=trait, value=choices.get_way(trait))
    return choices


def song_of(choices):
    """The music of the song some choices make: the set's data without its notes, which say who plays in words, and without
    the choices the song keeps, both of which differ where nothing that is heard does."""
    data = choices.made_setlist(name=A_NAME, version=VERSION).to_data()
    song = {field: value for field, value in data[Section.SONGS][A_NAME].items() if field != WIZARD_CHOICES_KEPT}
    return {**{field: value for field, value in data.items() if field not in (NOTES_KEPT, Section.SONGS)}, Section.SONGS: song}


def every_choice(choices):
    """Yield (kind, what, change) for every choice the wizard offers on some choices, change being what makes it on fresh ones."""
    for role in choices.roles_in():
        for trait in choices.role_traits(role):
            for way in choices.ways(role=role, trait=trait):
                if way != choices.get_way(trait):
                    yield WAY, (trait, way), lambda made, trait=trait, way=way: made.set_way(trait=trait, value=way)
        if choices.has_busy(role) and choices.get_busy(role) is not None:
            for level in range(LEAST_BUSY, MOST_BUSY + 1):
                if level != choices.get_busy(role):
                    yield BUSY, (role, level), lambda made, role=role, level=level: made.set_busy(role=role, level=level)
        if choices.has_sound(role):
            yield SOUND, role, lambda made, role=role: made.set_sound(role=role, sound=A_SOUND_OF_NO_STYLE)
        else:
            for position in range(FEWEST_FILLS, MOST_FILLS + 1):
                if position != choices.get_fills():
                    yield FILLS_COME, position, lambda made, position=position: made.set_fills(position)
            for piece in choices.pieces()[1:]:
                yield KIT_PIECE, piece, lambda made, piece=piece: made.set_piece_on(piece=piece, on=False)
            if choices.has_quiet_notes():
                yield QUIET_NOTES, False, lambda made: made.set_quiet_notes(False)
        if len(choices.roles_in()) > 1:
            yield PLAYER_OUT, role, lambda made, role=role: made.set_role_in(role=role, on=False)
    for sounds in BAND_SOUNDS:
        # A band already of a family is not changed by choosing the family, which is no dead choice.
        if sounds != USUAL_SOUNDS and any(choices.has_sound(role) and band_sound_differs(choices=choices, role=role, sounds=sounds) for role in choices.roles_in()):
            yield BAND_SOUND, sounds, lambda made, sounds=sounds: made.set_band_sounds(sounds)
    for kind, trait in ((PROGRESSION, choices.progression_trait()), (FILLS, choices.song_trait(FILLS_TRAITS))):
        for way in (choices.song_ways(trait) if trait is not None else []):
            if way != choices.get_way(trait):
                yield kind, way, lambda made, trait=trait, way=way: made.set_way(trait=trait, value=way)
    for style in choices.melody_styles():
        yield MELODY, style, lambda made, style=style: made.set_melody(style)
    if choices.offers_one_guitarist():
        yield GUITARISTS, ONE_GUITARIST_COUNT, lambda made: made.set_guitarists(ONE_GUITARIST_COUNT)
    yield SEED, ANOTHER_SEED, lambda made: made.set_seed(ANOTHER_SEED)
    yield TEMPO, A_LITTLE_FASTER, lambda made: made.set_tempo(made.get_tempo() + A_LITTLE_FASTER)
    for bars in choices.bars_offered(FIRST_PLACE):
        if bars != choices.section_bars(FIRST_PLACE):
            yield SECTION_BARS, bars, lambda made, bars=bars: made.set_section_bars(place=FIRST_PLACE, bars=bars)
    for kind in choices.section_kinds():
        if kind != choices.section_kind(FIRST_PLACE):
            yield SECTION_KIND, kind, lambda made, kind=kind: made.set_section_kind(place=FIRST_PLACE, kind=kind)
    for form in choices.forms():
        if form != choices.get_form():
            yield FORM, form, lambda made, form=form: made.set_form(form)


def band_sound_differs(*, choices, role, sounds):
    other = WizardChoices.from_data(choices.to_data())
    other.set_band_sounds(sounds)
    return other.get_sound(role) != choices.get_sound(role)


class EveryChoiceOfAGenre:
    """Every choice of half the subgenres of one genre: a class for each half of each genre, since the whole takes long and the
    classes run side by side."""

    GENRE = None
    HALF = None

    def test_every_choice_changes_the_song_but_those_known_not_to(self):
        subgenres = fresh(genre=self.GENRE, subgenre=WizardChoices.from_data({'genre': self.GENRE}).subgenres()[0]).subgenres()
        nothing = collections.defaultdict(list)
        tried = 0
        for subgenre in subgenres[self.HALF::HALVES]:
            usual = song_of(fresh(genre=self.GENRE, subgenre=subgenre))
            for kind, what, change in every_choice(fresh(genre=self.GENRE, subgenre=subgenre)):
                made = fresh(genre=self.GENRE, subgenre=subgenre)
                change(made)
                tried += 1
                if song_of(made) == usual:
                    nothing[kind].append(LABEL.format(subgenre=subgenre, what=what))
        self.assertGreater(tried, 0)
        found = {kind: len(labels) for kind, labels in nothing.items()}
        self.assertEqual(found, KNOWN_TO_CHANGE_NOTHING.get((self.GENRE, self.HALF), {}), dict(nothing))


def class_for(*, genre, half):
    name = 'TestEveryChoiceOf{}Half{}'.format(''.join(word.capitalize() for word in genre.split('_')), half + 1)
    return name, type(name, (EveryChoiceOfAGenre, unittest.TestCase), {'GENRE': genre, 'HALF': half, '__slots__': ()})


for a_genre in genre_names():
    for a_half in range(HALVES):
        a_name, a_class = class_for(genre=a_genre, half=a_half)
        globals()[a_name] = a_class
del a_class
