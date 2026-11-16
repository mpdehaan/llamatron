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
"""Every choice the song wizard offers changes the song that is made: a choice that changes nothing is a field
that lies. Each choice of each subgenre is made alone on fresh choices and the song arranged from it is held against the song
arranged without it. Three kinds of choice are held in a way of their own. A gauge, a player's Busy, is held position against
position, each to make a song no other position makes. A choice about a player who plays in no section, as ambient's
drummer, is made with the player put into the first section, where the choice is heard. And a choice that says what the
drummer would do unasked, a fill or how often fills come, is live when it changes the song under any drummer, since it
holds that fill whoever drums. The choices known to change nothing are counted, by genre and kind, in
KNOWN_TO_CHANGE_NOTHING with the reason; a count that moves either way fails, so that a new dead choice is caught and a
fixed one is taken off the list."""

import collections
import json
import unittest

from llamatron.composition.file_format import Section
from llamatron.macro_composer import interplay
from llamatron.macro_composer.breaks import LEAST_CUT, MOST_CUT
from llamatron.macro_composer.melody import HIGHEST_GAUGE, LOWEST_GAUGE
from llamatron.support.version import VERSION
from llamatron.macro_composer.wizard_choices import (USUAL_PIECE_NOTE, BAND_SOUNDS, GAUGED_STYLES, FEWEST_FILLS, FILLS_TRAITS, LEAST_BUSY, MOST_BUSY, MOST_FILLS, ONE_GUITARIST_COUNT,
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
BREAK = 'break'
PIECE_SOUND = 'kit piece sound'
PIECE_NOTE = 'kit piece note'
ANSWERED_BY = 'answered by'
ROLE_PLAN = 'role'
SECTION_ROLE = "a section's role"
FILLS_BUSY = 'fills busy'
# Two drums of the kit, the second for the piece that is the first, and a note that is not the usual one.
ANOTHER_DRUM = ('cowbell', 'claves')
ANOTHER_NOTE = USUAL_PIECE_NOTE + 7
BREAK_CUT = 'cut up'
MELODY_GAUGE = 'melody gauge'
HOOK = 'hook'
GUITARISTS = 'guitarists'
SEED = 'seed'
TEMPO = 'tempo'
SECTION_BARS = "a section's bars"
SECTION_KIND = "a section's kind"
FORM = 'form'
PLAYS_IN_SECTION = 'who plays in a section'
# How many choices of each kind change nothing, by genre and half, with the reason each is allowed for now: none is.
FIRST_HALF = 0
SECOND_HALF = 1
KNOWN_TO_CHANGE_NOTHING = {}
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


def nothing_first(made):
    """What is done before a choice that needs nothing done first."""


def plays_nowhere(*, choices, role):
    return not any(role in choices.section_plays(place) for place in range(len(choices.form_sections())))


def put_in(role):
    """Return what puts a player into the first section, where the player's choices are heard."""
    return lambda made: made.set_section_plays(place=FIRST_PLACE, role=role, on=True)


def under_each_drummer(*, choices, role, first):
    """Return what to do first for a choice that says what the drummer would do unasked: nothing more, then each other drummer."""
    others = [level for level in range(LEAST_BUSY, MOST_BUSY + 1) if level != choices.get_busy(role)] if choices.get_busy(role) is not None else []
    return [first] + [lambda made, level=level: (first(made), made.set_busy(role=role, level=level)) for level in others]


def every_choice(choices):
    """Yield (kind, what, change, firsts) for every choice the wizard offers on some choices: change makes it on fresh ones, and
    each of firsts is something done before it, and before the song it is held against; the choice is live when it changes
    the song after any of them."""
    drummer = None
    for role in choices.roles_in():
        first = put_in(role) if plays_nowhere(choices=choices, role=role) else nothing_first
        for trait in choices.role_traits(role):
            for way in choices.ways(role=role, trait=trait):
                if way != choices.get_way(trait):
                    yield WAY, (trait, way), lambda made, trait=trait, way=way: made.set_way(trait=trait, value=way), [first]
        if choices.has_sound(role):
            yield SOUND, role, lambda made, role=role: made.set_sound(role=role, sound=A_SOUND_OF_NO_STYLE), [first]
        else:
            drummer = role
            for position in range(FEWEST_FILLS, MOST_FILLS + 1):
                if position != choices.get_fills():
                    yield FILLS_COME, position, lambda made, position=position: made.set_fills(position), under_each_drummer(choices=choices, role=role, first=first)
            for piece in choices.pieces()[1:]:
                yield KIT_PIECE, piece, lambda made, piece=piece: made.set_piece_on(piece=piece, on=False), [first]
            if choices.has_quiet_notes():
                yield QUIET_NOTES, False, lambda made: made.set_quiet_notes(False), [first]
            for piece in choices.pieces():
                # A piece sounds as another drum of the kit or as a General MIDI sound, and in such a sound on a note of its own.
                yield PIECE_SOUND, (piece, ANOTHER_DRUM[piece == ANOTHER_DRUM[0]]), lambda made, piece=piece: made.set_piece_sound(piece=piece, sound=ANOTHER_DRUM[piece == ANOTHER_DRUM[0]]), [first]
                yield PIECE_SOUND, (piece, A_SOUND_OF_NO_STYLE), lambda made, piece=piece: made.set_piece_sound(piece=piece, sound=A_SOUND_OF_NO_STYLE), [first]
                in_a_sound = both(first=first, then=lambda made, piece=piece: made.set_piece_sound(piece=piece, sound=A_SOUND_OF_NO_STYLE))
                yield PIECE_NOTE, (piece, ANOTHER_NOTE), lambda made, piece=piece: made.set_piece_note(piece=piece, note=ANOTHER_NOTE), [in_a_sound]
            for name in [None, *choices.breaks()] if choices.breaks() else []:
                if name != choices.get_break():
                    yield BREAK, name, lambda made, name=name: made.set_break(name), [first]
            if choices.breaks():
                # How far a break is cut up is held under a break, the subgenre's own or the first there is.
                with_break = first if choices.get_break() is not None else both(first=first, then=lambda made: made.set_break(made.breaks()[0]))
                for cut in range(LEAST_CUT, MOST_CUT + 1):
                    if cut != choices.get_break_cut():
                        yield BREAK_CUT, cut, lambda made, cut=cut: made.set_break_cut(cut), [with_break]
        if len(choices.roles_in()) > 1:
            yield PLAYER_OUT, role, lambda made, role=role: made.set_role_in(role=role, on=False), [first]
        if role in choices.roles_shown():
            on = role not in choices.section_plays(FIRST_PLACE)
            if on or len(choices.section_plays(FIRST_PLACE)) > 1:
                yield PLAYS_IN_SECTION, (role, on), lambda made, role=role, on=on: made.set_section_plays(place=FIRST_PLACE, role=role, on=on), [nothing_first]
    for sounds in BAND_SOUNDS:
        # A band already of a family is not changed by choosing the family, which is no dead choice.
        if sounds != USUAL_SOUNDS and any(choices.has_sound(role) and band_sound_differs(choices=choices, role=role, sounds=sounds) for role in choices.roles_in()):
            yield BAND_SOUND, sounds, lambda made, sounds=sounds: made.set_band_sounds(sounds), [nothing_first]
    for kind, trait in ((PROGRESSION, choices.progression_trait()), (FILLS, choices.song_trait(FILLS_TRAITS))):
        firsts = [nothing_first]
        if kind == FILLS and drummer is not None:
            firsts = under_each_drummer(choices=choices, role=drummer, first=put_in(drummer) if plays_nowhere(choices=choices, role=drummer) else nothing_first)
        for way in (choices.song_ways(trait) if trait is not None else []):
            if way != choices.get_way(trait):
                yield kind, way, lambda made, trait=trait, way=way: made.set_way(trait=trait, value=way), firsts
    if choices.answered_by() is not None:
        # Who answers the tune, the one thing the answering player does in every section, each section's own, and how busy the fills are.
        yield ANSWERED_BY, None, lambda made: made.set_answered_by(None), [nothing_first]
        for way in choices.ways_beside():
            another = interplay.FILLS if way == interplay.WAITS else interplay.WAITS
            yield ROLE_PLAN, way, lambda made, way=way: made.set_role_plan(way), [lambda made, another=another: made.set_role_plan(another)]
        kinds_seen = set()
        for place, label in enumerate(choices.section_labels()):
            kind = choices.section_kind(place)
            if not choices.section_has_role(place) or kind in kinds_seen:
                continue
            kinds_seen.add(kind)
            for way in choices.ways_beside():
                if way != choices.section_role(place):
                    yield SECTION_ROLE, (label, way), lambda made, place=place, way=way: made.set_section_role(place=place, way=way), [nothing_first]
        def answering(made):
            made.set_role_plan(interplay.ANSWERS)

        def filling(made):
            # A genre whose own plan writes the answers plays them as written, so how busy is heard in the fills there.
            made.set_role_plan(interplay.FILLS)
        for busy in range(interplay.LEAST_BUSY, interplay.MOST_BUSY + 1):
            if busy != choices.get_fills_busy():
                yield FILLS_BUSY, busy, lambda made, busy=busy: made.set_fills_busy(busy), [answering, filling]
    for style in choices.melody_styles():
        yield MELODY, style, lambda made, style=style: made.set_melody(style), [nothing_first]
    for style in GAUGED_STYLES:
        if style not in choices.melody_styles():
            continue
        # A gauged melody style's gauges show once the style is chosen, and each position of each is held against the genre's own.
        chosen = fresh_with_melody(choices=choices, style=style)
        for name in chosen.gauges():
            for position in range(LOWEST_GAUGE, HIGHEST_GAUGE + 1):
                if position != chosen.get_gauge(name):
                    yield MELODY_GAUGE, (style, name, position), lambda made, name=name, position=position: made.set_gauge(name=name, position=position), [lambda made, style=style: made.set_melody(style)]
    if choices.can_have_hook():
        yield HOOK, not choices.has_hook(), lambda made: made.set_hook(not made.has_hook()), [nothing_first]
    if choices.offers_one_guitarist():
        yield GUITARISTS, ONE_GUITARIST_COUNT, lambda made: made.set_guitarists(ONE_GUITARIST_COUNT), [nothing_first]
    yield SEED, ANOTHER_SEED, lambda made: made.set_seed(ANOTHER_SEED), [nothing_first]
    yield TEMPO, A_LITTLE_FASTER, lambda made: made.set_tempo(made.get_tempo() + A_LITTLE_FASTER), [nothing_first]
    for bars in choices.bars_offered(FIRST_PLACE):
        if bars != choices.section_bars(FIRST_PLACE):
            yield SECTION_BARS, bars, lambda made, bars=bars: made.set_section_bars(place=FIRST_PLACE, bars=bars), [nothing_first]
    for kind in choices.section_kinds():
        if kind != choices.section_kind(FIRST_PLACE):
            yield SECTION_KIND, kind, lambda made, kind=kind: made.set_section_kind(place=FIRST_PLACE, kind=kind), [nothing_first]
    for form in choices.forms():
        if form != choices.get_form():
            yield FORM, form, lambda made, form=form: made.set_form(form), [nothing_first]


def both(*, first, then):
    """Return one thing done first made of two, in order."""
    def done(made):
        first(made)
        then(made)
    return done


def fresh_with_melody(*, choices, style):
    """Return choices like some others with a melody style chosen, to read its gauges from."""
    chosen = WizardChoices.from_data(choices.to_data())
    chosen.set_melody(style)
    return chosen


def busy_gauges(choices):
    """Yield (role, first) for each player whose Busy gauge the wizard shows."""
    for role in choices.roles_in():
        if choices.has_busy(role) and choices.get_busy(role) is not None:
            yield role, put_in(role) if plays_nowhere(choices=choices, role=role) else nothing_first


def changes(*, genre, subgenre, change, firsts):
    """Return whether a choice changes the song after any of the things done first."""
    for first in firsts:
        usual = fresh(genre=genre, subgenre=subgenre)
        first(usual)
        made = fresh(genre=genre, subgenre=subgenre)
        first(made)
        change(made)
        if song_of(made) != song_of(usual):
            return True
    return False


def positions_alike(*, genre, subgenre, role, first):
    """Return how many positions of a player's Busy gauge make a song another position makes."""
    songs = set()
    for level in range(LEAST_BUSY, MOST_BUSY + 1):
        made = fresh(genre=genre, subgenre=subgenre)
        first(made)
        made.set_busy(role=role, level=level)
        songs.add(json.dumps(song_of(made), sort_keys=True, default=str))
    return MOST_BUSY + 1 - LEAST_BUSY - len(songs)


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
            for kind, what, change, firsts in every_choice(fresh(genre=self.GENRE, subgenre=subgenre)):
                tried += 1
                if not changes(genre=self.GENRE, subgenre=subgenre, change=change, firsts=firsts):
                    nothing[kind].append(LABEL.format(subgenre=subgenre, what=what))
            for role, first in busy_gauges(fresh(genre=self.GENRE, subgenre=subgenre)):
                tried += 1
                alike = positions_alike(genre=self.GENRE, subgenre=subgenre, role=role, first=first)
                nothing[BUSY].extend([LABEL.format(subgenre=subgenre, what=role)] * alike)
        self.assertGreater(tried, 0)
        found = {kind: len(labels) for kind, labels in nothing.items() if labels}
        self.assertEqual(found, KNOWN_TO_CHANGE_NOTHING.get((self.GENRE, self.HALF), {}), dict(nothing))


def class_for(*, genre, half):
    name = 'TestEveryChoiceOf{}Half{}'.format(''.join(word.capitalize() for word in genre.split('_')), half + 1)
    return name, type(name, (EveryChoiceOfAGenre, unittest.TestCase), {'GENRE': genre, 'HALF': half, '__slots__': ()})


for a_genre in genre_names():
    for a_half in range(HALVES):
        a_name, a_class = class_for(genre=a_genre, half=a_half)
        globals()[a_name] = a_class
del a_class
