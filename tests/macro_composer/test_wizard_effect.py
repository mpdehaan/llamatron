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
holds that fill whoever drums. The choices known to change nothing are counted, by subgenre and kind, in
KNOWN_TO_CHANGE_NOTHING with the reason; a count that moves either way fails, so that a new dead choice is caught and a
fixed one is taken off the list.

Most choices are the same code whatever the subgenre, so each run checks every choice on one subgenre of each genre, the day's
own, taken in turn by the date, and every subgenre is checked within as many days as its genre has subgenres. A failure says
the day and the subgenre, and subgenre_of_the_day gives the same subgenre for that day again."""

import collections
import datetime
import json
import unittest

from llamatron.composition import generator_settings
from llamatron.composition.file_format import GeneratorKind, Row, Section
from llamatron.composition.generator_settings import MusicianSetting, PhrasingSetting
from llamatron.generators import musician, phrasing as phrasing_values
from llamatron.macro_composer import arranger, breaks, hook_writing, interplay, line_edits, loudness, melody, phrasing, riffs, song_plan, wizard_limits
from llamatron.macro_composer.wizard_choices import genre_names, WizardChoices
from llamatron.support import version

A_NAME = 'a_song'
NOTES_KEPT = 'notes'
WIZARD_CHOICES_KEPT = 'wizard'
A_SEED = 7
ANOTHER_SEED = 8
A_SOUND_OF_NO_STYLE = 105
A_LITTLE_FASTER = 7
FIRST_PLACE = 0
# The kinds of choice.
WAY = 'a way of playing'
BUSY = 'busy'
SOUND = 'sound'
PLAYER_OUT = 'a player left out'
BAND_SOUND = "the band's sounds"
PROGRESSION = 'progression'
FILLS = 'fills'
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
ANOTHER_NOTE = wizard_limits.USUAL_PIECE_NOTE + 7
BREAK_CUT = 'cut up'
MELODY_WAY = 'what every melody shares'
MELODY_CHARACTER_CHOICE = "the melodies' character"
MELODY_OF_KIND = "a kind of section's own melody"
PART_IN_KIND = 'what a player plays in a kind of section'
HOOK = 'hook'
PLAYER_ROW = 'player row'
NEW_HOOK = 'new hook'
HOOK_PLACEMENT = "the hook's place among its lines"
SECOND_HOOK_CHOICE = 'second hook'
NEW_SECOND_HOOK = 'new second hook'
SONG_PLAN = 'song plan'
CONTRAST = 'contrast'
PHRASING = 'phrasing'
PHRASING_WAY = 'how the lines breathe'
HOOK_BEHAVIOR = "the hook's behavior"
HOOK_GAUGE = "a gauge of the hook"
BODY_GAUGE = "a gauge of the chorus's body"
# A degree is changed among the first few of the scale, which every scale has.
DEGREES_TRIED = 5
HOOK_LINE = "the hook's notes written by hand"
OWN_TUNE = 'a tune written by hand'
OWN_SOLO_NOTES = 'a solo written by hand'
SOLO_TAKE = 'another take of a solo'
OWN_INTRO_NOTES = 'an intro melody written by hand'
INTRO_PART_MELODY = 'who says the hook in a part of the intro'
A_FADE = 'a fade'
A_FADE_LEVEL = 'the velocity of a fade'
A_FADE_OVER = 'the bars of a fade in'
INTRO_PART = 'a part of the intro added'
A_VELOCITY = 64
A_BAR = 1
TUNE_TAKE = 'another take of a tune'
OWN_RIFF = 'a riff written by hand'
TUNE_BY_SONG_CHOICE = 'who plays the tune in the song'
TUNE_PHRASING_CHOICE = 'how the tune is delivered'
PLAYER_MUSICIAN = "a player's musician"
A_LINE = "a line's own"
A_RIFF = 'the riff'
COMES_IN = 'where a player comes in'
REACTS_TO_ENERGY = 'how a player reacts'
DYNAMICS_OF_PLAYER = "a player's dynamics"
A_RIFF_SETTING = "a riff's setting"
A_LEVEL = "a player's loudness level"
A_STEP_OF_VELOCITY = 15
MIDDLE_VELOCITY = 64
START = 'a way of starting'
END = 'a way of ending'
FIRST_PLAYER = 'the first player'
SETUP_BARS = "the setup's bars"
DRUMS_ROLE = 'drums'
SECTION_OWN = "a section's own"
FORM_ANSWER = 'an answer of the form questions'
INTRO_HOOK = 'intro hook'
SECTION_SHAPE = "a section's shape"
KNOWN_TO_CHANGE_NOTHING = {
    # Arena rock's pre-chorus already sings at the top of the tune's range, so the shape that holds the second line back is the usual shape, at both pre-choruses.
    ('rock', 'arena rock'): {SECTION_SHAPE: 2},
    # Baroque pop's one line that would come early repeats an idea, which takes no early note of its own, and disco's does too.
    ('sixties_pop', 'baroque'): {PHRASING_WAY: 2},
    ('soul_funk', 'disco'): {PHRASING_WAY: 2},
    # Bubblegum's singer, whose Energy never falls, plays two neighbouring positions of the gauge alike.
    ('sixties_pop', 'bubblegum'): {BUSY: 1},
}
A_SECOND_PLACE = 1
NO_PLAN = 'with no plan'
SECTION_OWN_ANYWHERE = (('chords', '6 4 2 5'), ('chords', '1 4'), ('tempo', 61), ('tempo_end', 62), ('root', 'F#'), ('root', 'C'), ('type', 'minor'), ('type', 'major'))
# A value of each field a section can be given of its own.
SECTION_OWN_TRIED = (('rises', True), ('energy', 10), ('energy', 1), ('leaves', 'stops'), ('leaves', 'build'), ('leaves', 'drop-out'), ('leaves', 'a big fill'), ('leaves', 'a small fill'), ('leaves', 'nothing'),
                     ('chords', '6 4 2 5'), ('tempo', 61), ('tempo_end', 62), ('root', 'F#'), ('type', 'minor'), ('type', 'major'))
GUITARISTS = 'guitarists'
SEED = 'seed'
TEMPO = 'tempo'
SWING = 'swing'
VARIANT = 'variant'
SECTION_BARS = "a section's bars"
SECTION_KIND = "a section's kind"
FORM = 'form'
PLAYS_IN_SECTION = 'who plays in a section'
# How many choices of each kind change nothing, by genre and part, with the reason each is allowed for now.
# Rock and roll's planned song: its sections' Energies all ask for the hat in eighths, so choosing that cymbal is choosing what the plan already plays.
LABEL = '{subgenre}: {what}'

# The song each set of choices makes before a change, by the choices' data.
USUAL_SONGS = {}

def fresh(*, genre, subgenre):
    """Choices for a subgenre with a seed and its usual progression chosen, so that one choice alone differs from the next."""
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre)
    choices.set_seed(A_SEED)
    trait = choices.progression_trait()
    if trait is not None:
        choices.get_band().set_way(trait=trait, value=choices.get_band().get_way(trait))
    return choices
# Every value each setting of a Phrasing takes.
PHRASING_OFFERED_VALUES = {PhrasingSetting.LINE_BARS: generator_settings.LINES_IN_BARS, PhrasingSetting.BREATH: phrasing_values.BREATHS, PhrasingSetting.RISE_AND_FALL: phrasing_values.RISES, PhrasingSetting.NOTES: phrasing_values.JOINS}


def song_of(choices):
    """The music of the song some choices make: the set's data without its notes, which say who plays in words, and without
    the choices the song keeps, both of which differ where nothing that is heard does."""
    data = choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()
    song = {field: value for field, value in data[Section.SONGS][A_NAME].items() if field != WIZARD_CHOICES_KEPT}
    return {**{field: value for field, value in data.items() if field not in (NOTES_KEPT, Section.SONGS)}, Section.SONGS: song}


def nothing_first(made):
    """What is done before a choice that needs nothing done first."""


def plays_nowhere(*, choices, role):
    return not any(role in choices.section(place).plays() for place in range(len(choices.form_sections())))


def put_in(role):
    """Return what puts a player into the first section, where the player's choices are heard."""
    return lambda made: made.section(FIRST_PLACE).set_plays(role=role, on=True)


def under_each_drummer(*, choices, role, first):
    """Return what to do first for a choice that says what the drummer would do unasked: nothing more, then each other drummer."""
    others = [level for level in range(wizard_limits.LEAST_BUSY, wizard_limits.MOST_BUSY + 1) if level != choices.player(role).get_busy()] if choices.player(role).get_busy() is not None else []
    return [first] + [lambda made, level=level: (first(made), made.player(role).set_busy(level=level)) for level in others]


def first_degree_changed(pattern):
    """Return a pattern's data with the degree of its first note another, as a person writing the tune by hand might make it."""
    degrees = list(pattern[Row.DEGREE])
    step = next(place for place, degree in enumerate(degrees) if degree is not None)
    degrees[step] = degrees[step] % DEGREES_TRIED + 1
    return {**pattern, Row.DEGREE: degrees}


def first_sounding_step(line):
    """The step a line's first note starts on, after any rest the line opens with."""
    step = 0
    for note in line:
        if not line_edits.is_rest(note):
            return step
        step += line_edits.length_of(note)
    return step


def far_end(position):
    """The end of a gauge's scale farther from a position."""
    middle = (hook_writing.LOWEST + hook_writing.HIGHEST) / 2
    return hook_writing.LOWEST if position > middle else hook_writing.HIGHEST


def every_choice(choices):
    """Yield (kind, what, change, firsts) for every choice the wizard offers on some choices: change makes it on fresh ones, and
    each of firsts is something done before it, and before the song it is held against; the choice is live when it changes
    the song after any of them."""
    drummer = None
    for role in choices.get_band().roles_in():
        first = put_in(role) if plays_nowhere(choices=choices, role=role) else nothing_first
        for trait in choices.player(role).traits():
            for way in choices.player(role).ways(trait=trait):
                if way != choices.get_band().get_way(trait):
                    yield WAY, (trait, way), lambda made, trait=trait, way=way: made.get_band().set_way(trait=trait, value=way), [first]
        if choices.get_sounds().has_sound(role):
            yield SOUND, role, lambda made, role=role: made.get_sounds().set_sound(role=role, sound=A_SOUND_OF_NO_STYLE), [first]
        else:
            drummer = role
            for position in range(wizard_limits.FEWEST_FILLS, wizard_limits.MOST_FILLS + 1):
                if position != choices.get_kit().get_fills():
                    yield FILLS_COME, position, lambda made, position=position: made.get_kit().set_fills(position), under_each_drummer(choices=choices, role=role, first=first)
            for piece in choices.get_kit().pieces()[1:]:
                yield KIT_PIECE, piece, lambda made, piece=piece: made.get_kit().set_piece_on(piece=piece, on=False), [first]
            if choices.get_kit().has_quiet_notes():
                yield QUIET_NOTES, False, lambda made: made.get_kit().set_quiet_notes(False), [first]
            for piece in choices.get_kit().pieces():
                # A piece sounds as another drum of the kit or as a General MIDI sound, and in such a sound on a note of its own.
                yield PIECE_SOUND, (piece, ANOTHER_DRUM[piece == ANOTHER_DRUM[0]]), lambda made, piece=piece: made.get_kit().set_piece_sound(piece=piece, sound=ANOTHER_DRUM[piece == ANOTHER_DRUM[0]]), [first]
                yield PIECE_SOUND, (piece, A_SOUND_OF_NO_STYLE), lambda made, piece=piece: made.get_kit().set_piece_sound(piece=piece, sound=A_SOUND_OF_NO_STYLE), [first]
                in_a_sound = both(first=first, then=lambda made, piece=piece: made.get_kit().set_piece_sound(piece=piece, sound=A_SOUND_OF_NO_STYLE))
                yield PIECE_NOTE, (piece, ANOTHER_NOTE), lambda made, piece=piece: made.get_kit().set_piece_note(piece=piece, note=ANOTHER_NOTE), [in_a_sound]
            for name in [None, *choices.get_kit().breaks()] if choices.get_kit().breaks() else []:
                if name != choices.get_kit().get_break():
                    yield BREAK, name, lambda made, name=name: made.get_kit().set_break(name), [first]
            if choices.get_kit().breaks():
                # How far a break is cut up is held under a break, the subgenre's own or the first there is.
                with_break = first if choices.get_kit().get_break() is not None else both(first=first, then=lambda made: made.get_kit().set_break(made.get_kit().breaks()[0]))
                for cut in range(breaks.LEAST_CUT, breaks.MOST_CUT + 1):
                    if cut != choices.get_kit().get_break_cut():
                        yield BREAK_CUT, cut, lambda made, cut=cut: made.get_kit().set_break_cut(cut), [with_break]
        if len(choices.get_band().roles_in()) > 1:
            yield PLAYER_OUT, role, lambda made, role=role: made.player(role).set_in(on=False), [first]
        if role in choices.get_band().roles_shown():
            on = role not in choices.section(FIRST_PLACE).plays()
            if on or len(choices.section(FIRST_PLACE).plays()) > 1:
                yield PLAYS_IN_SECTION, (role, on), lambda made, role=role, on=on: made.section(FIRST_PLACE).set_plays(role=role, on=on), [nothing_first]
    for sounds in wizard_limits.BAND_SOUNDS:
        # A band already of a family is not changed by choosing the family, which is no dead choice.
        if sounds != wizard_limits.USUAL_SOUNDS and any(choices.get_sounds().has_sound(role) and band_sound_differs(choices=choices, role=role, sounds=sounds) for role in choices.get_band().roles_in()):
            yield BAND_SOUND, sounds, lambda made, sounds=sounds: made.get_sounds().set_band_sounds(sounds), [nothing_first]
    for kind, trait in ((PROGRESSION, choices.progression_trait()), (FILLS, choices.get_band().song_trait(wizard_limits.FILLS_TRAITS))):
        firsts = [nothing_first]
        if kind == FILLS and drummer is not None:
            firsts = under_each_drummer(choices=choices, role=drummer, first=put_in(drummer) if plays_nowhere(choices=choices, role=drummer) else nothing_first)
        for way in (choices.get_band().song_ways(trait) if trait is not None else []):
            if way != choices.get_band().get_way(trait):
                yield kind, way, lambda made, trait=trait, way=way: made.get_band().set_way(trait=trait, value=way), firsts
    if choices.get_band().answered_by() is not None:
        # Who answers the tune, the one thing the answering player does in every section, each section's own, and how busy the fills are.
        yield ANSWERED_BY, None, lambda made: made.get_band().set_answered_by(None), [nothing_first]
        for way in choices.get_band().ways_beside():
            another = interplay.FILLS if way == interplay.WAITS else interplay.WAITS
            yield ROLE_PLAN, way, lambda made, way=way: made.get_band().set_role_plan(way), [lambda made, another=another: made.get_band().set_role_plan(another)]
        kinds_seen = set()
        for place, label in enumerate(choices.section_labels()):
            kind = choices.section(place).kind()
            if not choices.get_band().section_has_role(place) or kind in kinds_seen:
                continue
            kinds_seen.add(kind)
            for way in choices.get_band().ways_beside():
                if way != choices.get_band().section_role(place):
                    yield SECTION_ROLE, (label, way), lambda made, place=place, way=way: made.get_band().set_section_role(place=place, way=way), [nothing_first]
        def answering(made):
            made.get_band().set_role_plan(interplay.ANSWERS)

        def filling(made):
            # A genre whose own plan writes the answers plays them as written, so how busy is heard in the fills there.
            made.get_band().set_role_plan(interplay.FILLS)
        for busy in range(interplay.LEAST_BUSY, interplay.MOST_BUSY + 1):
            if busy != choices.get_band().get_fills_busy():
                yield FILLS_BUSY, busy, lambda made, busy=busy: made.get_band().set_fills_busy(busy), [answering, filling]
    # What every melody of the song shares: each other value of how busy, how wide and how repeated, and each character offered.
    for field in choices.melody_fields():
        for value in choices.melody_ways_offered(field):
            if value != choices.get_melody_way(field):
                yield MELODY_WAY, (field, value), lambda made, field=field, value=value: made.set_melody_way(field=field, value=value), [nothing_first]
    for character in choices.melody_characters_offered():
        yield MELODY_CHARACTER_CHOICE, character, lambda made, character=character: made.set_melody_character(character), [nothing_first]
    # A kind of section's own melody: each height but the genre's, and each way of busy but the song's.
    for kind in choices.get_tunes().tune_kinds():
        for field in choices.section_melody_fields(kind):
            for value in choices.section_melody_ways_offered(kind=kind, field=field):
                if value != choices.get_section_melody(kind=kind, field=field):
                    yield MELODY_OF_KIND, (kind, field, value), lambda made, kind=kind, field=field, value=value: made.set_section_melody(kind=kind, field=field, value=value), [nothing_first]
    # A player's rows show under the serial style, and each row with every cell moved to the far end of its range is held against the genre's own.
    for character in (None, *(offered for offered in choices.melody_characters_offered() if offered == wizard_limits.ATONAL)):
        chosen = choices if character is None else fresh_with_character(choices=choices, character=character)
        first = nothing_first if character is None else (lambda made, character=character: made.set_melody_character(character))
        for role in chosen.get_band().roles_in():
            for name in chosen.player(role).rows():
                row = far_row(choices=chosen, role=role, name=name)
                yield PLAYER_ROW, (character, role, name), lambda made, role=role, name=name, row=row: made.player(role).set_row(name=name, values=row), [first]
    if choices.get_hook().can_have_hook():
        yield HOOK, not choices.get_hook().has_hook(), lambda made: made.get_hook().set_hook(not made.get_hook().has_hook()), [nothing_first]
    if choices.get_hook().can_have_hook() and choices.get_hook().has_hook():
        yield NEW_HOOK, choices.get_hook().get_hook_take() + 1, lambda made: made.get_hook().new_hook(), [nothing_first]
        for placement in choices.get_hook().hook_placements_offered():
            if placement != choices.get_hook().get_hook_placement():
                yield HOOK_PLACEMENT, placement, lambda made, placement=placement: made.get_hook().set_hook_placement(placement), [nothing_first]
        for kind in choices.get_hook().second_hook_kinds():
            yield SECOND_HOOK_CHOICE, kind, lambda made, kind=kind: made.get_hook().set_second_hook(kind), [nothing_first]
            yield NEW_SECOND_HOOK, kind, lambda made: made.get_hook().new_second_hook(), [lambda made, kind=kind: made.get_hook().set_second_hook(kind)]
    if choices.can_have_song_plan():
        # A planned song, and under a plan its contrast, its phrasing and each part of the hook's kind.
        def planned(made):
            made.set_song_plan(True)
        yield SONG_PLAN, False, lambda made: made.set_song_plan(False), [nothing_first]
        for contrast in (song_plan.LOWEST_ENERGY, song_plan.HIGHEST_ENERGY):
            yield CONTRAST, contrast, lambda made, contrast=contrast: made.set_contrast(contrast), [planned]
        under_plan = fresh_with_plan(choices)
        if under_plan.counts_in_four():
            yield PHRASING, False, lambda made: made.set_phrasing(False), [planned]
            for name, offered in wizard_limits.PHRASING_OFFERED.items():
                for value in offered:
                    if value != phrasing.USUAL_WAYS[name]:
                        yield PHRASING_WAY, (name, value), lambda made, name=name, value=value: made.set_phrasing_way(name=name, value=value), [planned]
    if choices.get_hook().writes_hook():
        # How the hook is written: every other behavior, and each gauge of the song's behavior moved to the end of its scale farther away.
        for behavior in hook_writing.BEHAVIORS:
            if behavior != choices.get_hook().get_hook_behavior():
                yield HOOK_BEHAVIOR, behavior, lambda made, behavior=behavior: made.get_hook().set_hook_behavior(behavior), [nothing_first]
        for name in choices.get_hook().hook_gauges():
            position = far_end(choices.get_hook().get_hook_gauge(name))
            yield HOOK_GAUGE, (name, position), lambda made, name=name, position=position: made.get_hook().set_hook_gauge(name=name, position=position), [nothing_first]
        for name in choices.get_hook().body_gauges():
            position = far_end(choices.get_hook().get_body_gauge(name))
            yield BODY_GAUGE, (name, position), lambda made, name=name, position=position: made.get_hook().set_body_gauge(name=name, position=position), [nothing_first]
    if choices.get_hook().can_have_hook() and choices.get_hook().has_hook() and choices.get_hook().hook_line() is not None:
        # The hook's notes written by hand: its first note, which a rest may come before, moved a note of the scale up.
        yield HOOK_LINE, 'first note up', lambda made: made.get_hook().set_hook_line(line_edits.moved(line=made.get_hook().hook_line(), step=first_sounding_step(made.get_hook().hook_line()), by=1)), [nothing_first]
    if choices.can_have_song_plan():
        # What a section of a planned song is given of its own, each held under a plan: the second section, which a section follows.
        under_plan = fresh_with_plan(choices)

        def planned_first(made):
            made.set_song_plan(True)
        for role in under_plan.intro_hook_players():
            yield INTRO_HOOK, role, lambda made, role=role: made.set_intro_hook(role), [planned_first]

            def said_first(made, role=role):
                made.set_song_plan(True)
                made.set_intro_hook(role)
            yield OWN_INTRO_NOTES, role, lambda made: made.set_intro_pattern(pattern=first_degree_changed(made.intro_pattern())), [said_first]
            for place in under_plan.intro_parts():
                yield INTRO_PART_MELODY, (place, role), lambda made, place=place, role=role: made.set_intro_melody(place=place, role=role), [planned_first]
        for place in range(len(under_plan.section_labels())):
            for shape in under_plan.section(place).shapes():
                yield SECTION_SHAPE, (place, shape), lambda made, place=place, shape=shape: made.section(place).set_own(field='shape', value=shape), [planned_first]
        for field, value in SECTION_OWN_TRIED:
            if field in under_plan.section(A_SECOND_PLACE).own_fields() and value != under_plan.section(A_SECOND_PLACE).from_plan(field=field):
                yield SECTION_OWN, (field, value), lambda made, field=field, value=value: made.section(A_SECOND_PLACE).set_own(field=field, value=value), [planned_first]
    # A fade, with or without a plan: a section that opens the song fades in and one that closes it fades out, each from or to a
    # velocity, and a fade in over its bars.
    for place in range(len(choices.section_labels())):
        if choices.section(place).fade_way() is None:
            continue

        def fades_first(made, place=place):
            made.section(place).set_own(field=song_plan.FADES, value=True)
        yield A_FADE, place, fades_first, [nothing_first]
        yield A_FADE_LEVEL, place, lambda made, place=place: made.section(place).set_own(field=song_plan.FADE_LEVEL, value=A_VELOCITY), [fades_first]
        if choices.section(place).fade_way() == wizard_limits.FADE_IN and choices.section(place).bars() > A_BAR:
            yield A_FADE_OVER, place, lambda made, place=place: made.section(place).set_own(field=song_plan.FADE_OVER, value=A_BAR), [fades_first]
    if choices.intro_parts():
        yield INTRO_PART, None, lambda made: made.add_intro_part(), [nothing_first]
    for field, value in SECTION_OWN_ANYWHERE:
        # What a section of any genre can be given of its own, held with no plan, on the second section where it takes any.
        if field in without_plan(choices).section(A_SECOND_PLACE).own_fields() and value != without_plan(choices).section(A_SECOND_PLACE).from_plan(field=field):
            yield SECTION_OWN, (field, value, NO_PLAN), lambda made, field=field, value=value: made.section(A_SECOND_PLACE).set_own(field=field, value=value), [switch_plan_off]
    # A tune written by hand, for each kind of section that has one: its first note another degree.
    for kind in choices.get_tunes().tune_kinds():
        if choices.get_tunes().tune_pattern(kind) is not None:
            yield OWN_TUNE, kind, lambda made, kind=kind: made.get_tunes().set_tune_pattern(kind=kind, pattern=first_degree_changed(made.get_tunes().tune_pattern(kind))), [nothing_first]
        for place in choices.get_solos().solo_places():
            yield SOLO_TAKE, place, lambda made, place=place: made.get_solos().new_solo_take(place), [nothing_first]
            yield OWN_SOLO_NOTES, place, lambda made, place=place: made.get_solos().set_solo_pattern(place=place, pattern=first_degree_changed(made.get_solos().solo_pattern(place))), [nothing_first]
    # Who plays the tune: each other player for the song, and for each kind of section each other player and nobody.
    # A song with no tune, as some electronic kinds, offers neither.
    for role in choices.get_tunes().tune_players_offered() if choices.get_tunes().tune_kinds() else []:
        if role != choices.get_tunes().tune_played_by():
            yield TUNE_BY_SONG_CHOICE, role, lambda made, role=role: made.get_tunes().set_tune_played_by(role), [nothing_first]
    # What each player plays in each kind of section: each part offered but the one the player has. A riff is written for the
    # first player who can have one and known by every such player, so that it is among what each is offered.
    def with_a_riff(made):
        riff = made.get_riffs().add_riff(role=made.get_riffs().riff_instruments()[0])
        for role in made.get_riffs().riff_instruments()[1:]:
            made.get_riffs().give_riff(role=role, riff=riff)
    staged = WizardChoices.from_data(choices.to_data())
    if staged.get_riffs().riff_instruments():
        with_a_riff(staged)
    for kind in staged.section_player_kinds():
        for role in staged.section_players(kind):
            for part in staged.section_parts_offered(kind=kind, role=role):
                if part != staged.section_part(kind=kind, role=role):
                    yield PART_IN_KIND, (kind, role, part), lambda made, kind=kind, role=role, part=part: made.set_section_part(kind=kind, role=role, part=part), [with_a_riff if staged.get_riffs().riff_instruments() else nothing_first]
    if choices.get_tunes().tune_kinds():
        # The tune delivered with no Phrasing, and with each setting of a Phrasing moved from what one starts with.
        yield TUNE_PHRASING_CHOICE, False, lambda made: made.set_tune_phrasing(False), [nothing_first]
        for setting, offered in PHRASING_OFFERED_VALUES.items():
            for value in offered:
                if value != generator_settings.PHRASING_DEFAULTS[setting]:
                    yield TUNE_PHRASING_CHOICE, (setting, value), lambda made, setting=setting, value=value: made.set_tune_phrasing({setting: value}), [nothing_first]
    if choices.get_band().has_musicians():
        # A player's Musician of the person's own, for each player whose clips run one: the loudest.
        setlist, name = choices.made_for_listening()
        for role in choices.get_band().roles_in():
            if setlist.get_song(name).has_generator(kind=GeneratorKind.MUSICIAN, name=choices.player(role).musician_name()):
                yield PLAYER_MUSICIAN, role, lambda made, role=role: made.player(role).set_musician(settings={MusicianSetting.LOUDNESS: musician.LOUDEST}), [nothing_first]
    # A riff played by the player it was written for in the first kind of section that takes it: its notes written by hand, written
    # again, drawn each other way, and the riff deleted.
    for role in choices.get_riffs().riff_instruments()[:1]:
        staged = WizardChoices.from_data(choices.to_data())
        riff = staged.get_riffs().add_riff(role=role)
        kind = next((kind for kind in staged.section_player_kinds() if riff in staged.section_parts_offered(kind=kind, role=role)), None)
        if kind is None:
            continue

        def played(made, role=role, kind=kind, settings=None):
            made.set_section_part(kind=kind, role=role, part=made.get_riffs().add_riff(role=role, settings=settings))
        yield OWN_RIFF, kind, lambda made, riff=riff, role=role: made.get_riffs().set_riff_pattern(riff=riff, pattern=first_degree_changed(riff_pattern_of(choices=made, riff=riff))), [played]
        yield A_RIFF, 'regenerated', lambda made, riff=riff: made.get_riffs().regenerate_riff(riff), [played]
        yield A_RIFF, 'deleted', lambda made, riff=riff: made.get_riffs().delete_riff(riff), [played]
        for field in (riffs.RIFF_BAR_COUNT, riffs.RIFF_NOTES):
            other = wizard_limits.RIFF_SETTINGS[field][1]
            yield A_RIFF_SETTING, (field, other), lambda made, role=role, kind=kind, field=field, other=other: played(made, role=role, kind=kind, settings={field: other}), [nothing_first]
    # Another take of a tune, for each kind of section that has one.
    for kind in choices.get_tunes().tune_kinds():
        yield TUNE_TAKE, kind, lambda made, kind=kind: made.get_tunes().new_tune_take(kind), [nothing_first]
    # A section's lines, one by one: the first line that breathes of the first section with a tune, its breath, its early note either way and its notes moved.
    for place in range(len(choices.section_labels())):
        lines = choices.section(place).lines()
        line = next((count for count, said in enumerate(lines) if said[wizard_limits.LINE_BREATHES]), None)
        if line is None:
            continue
        for breath in (phrasing.NO_BREATH, phrasing.LONGEST_BREATH - 1):
            yield A_LINE, (phrasing.LINE_BREATH, breath), lambda made, place=place, line=line, breath=breath: made.section(place).set_line(line=line, field=phrasing.LINE_BREATH, value=breath), [nothing_first]
        yield A_LINE, melody.LINE_NOTES, lambda made, place=place, line=line: made.section(place).set_line(line=line, field=melody.LINE_NOTES, value=first_note_moved(made.section(place).lines()[line][melody.LINE_NOTES])), [nothing_first]
        break
    # A player as a person: each other way of coming in and of laying out, and Reacts at either end.
    for role in choices.get_band().roles_in():
        for way in choices.comes_in_offered(role):
            if way != choices.get_comes_in(role) and comes_in_works(choices=choices, role=role, way=way):
                yield COMES_IN, (role, way), lambda made, role=role, way=way: made.set_comes_in(role=role, way=way), [nothing_first]
        if choices.reacts(role):
            # A player who reacts is heard to at one end of the gauge at least: an even player may play as the band does where the band is never held back.
            yield REACTS_TO_ENERGY, role, lambda made, role=role: set_reacts_where_heard(made=made, role=role), [nothing_first]
        # How loud a player is: the player's dynamics at either end, and each level the song plays, moved.
        if choices.player(role).has_dynamics():
            for dynamics in (loudness.LEAST_DYNAMICS, loudness.MOST_DYNAMICS):
                yield DYNAMICS_OF_PLAYER, (role, dynamics), lambda made, role=role, dynamics=dynamics: made.player(role).set_dynamics(dynamics=dynamics), [nothing_first]
        for level in choices.player(role).loudness_levels_offered():
            yield A_LEVEL, (role, level), lambda made, role=role, level=level: made.player(role).set_loudness_level(level=level, number=another_velocity(made.player(role).loudness_levels()[level])), [nothing_first]
    # How the song starts and ends: each way but the one the song has, another first player under layers, and another length of a stage.
    for way in choices.starts():
        if way != choices.get_start():
            yield START, way, lambda made, way=way: made.set_start(way), [nothing_first]
    for way in choices.ends():
        if way != choices.get_end():
            yield END, way, lambda made, way=way: made.set_end(way), [nothing_first]
    if wizard_limits.ONE_PLAYER_FIRST in choices.starts():
        # What the stages offer is asked of choices that start with one player, since a length is offered only where that player fills it.
        staged = WizardChoices.from_data(choices.to_data())
        one_player_first(staged)
        for role in staged.first_players():
            if role != staged.get_first_player() and role != DRUMS_ROLE:
                yield FIRST_PLAYER, role, lambda made, role=role: made.set_first_player(role), [one_player_first]
        for bars in staged.setup_bars_offered():
            if bars != staged.get_setup_bars():
                yield SETUP_BARS, bars, lambda made, bars=bars: made.set_setup_bars(bars), [one_player_first]
    for name, offered, usual in choices.form_questions():
        # Each answer of each question a form is made from, held against the form the usual answers make.
        for answer in offered:
            if answer != usual:
                yield FORM_ANSWER, (name, answer), lambda made, name=name, answer=answer: made.set_form_from_answers({name: answer}), [lambda made: made.set_form_from_answers({})]
    if choices.get_band().offers_one_guitarist():
        yield GUITARISTS, wizard_limits.ONE_GUITARIST_COUNT, lambda made: made.get_band().set_guitarists(wizard_limits.ONE_GUITARIST_COUNT), [nothing_first]
    yield SEED, ANOTHER_SEED, lambda made: made.set_seed(ANOTHER_SEED), [nothing_first]
    yield TEMPO, A_LITTLE_FASTER, lambda made: made.set_tempo(made.get_tempo() + A_LITTLE_FASTER), [nothing_first]
    for variant in choices.variants():
        if variant != choices.get_variant():
            yield VARIANT, variant, lambda made, variant=variant: made.set_variant(variant), [nothing_first]
    if choices.has_swing():
        for swing in choices.swings():
            if swing != choices.get_swing():
                yield SWING, swing, lambda made, swing=swing: made.set_swing(swing), [nothing_first]
    for bars in choices.section(FIRST_PLACE).bars_offered():
        if bars != choices.section(FIRST_PLACE).bars():
            yield SECTION_BARS, bars, lambda made, bars=bars: made.section(FIRST_PLACE).set_bars(bars=bars), [nothing_first]
    for kind in choices.section_kinds():
        if kind != choices.section(FIRST_PLACE).kind():
            yield SECTION_KIND, kind, lambda made, kind=kind: made.section(FIRST_PLACE).set_kind(kind=kind), [nothing_first]
    for form in choices.forms():
        if form != choices.get_form():
            yield FORM, form, lambda made, form=form: made.set_form(form), [nothing_first]


def first_note_moved(notes):
    """A line with its first note that sounds two places of the scale higher."""
    step = sum(line_edits.length_of(note) for note in notes[:next(count for count, note in enumerate(notes) if not line_edits.is_rest(note))])
    return line_edits.moved(line=notes, step=step, by=2)


def comes_in_works(*, choices, role, way):
    """Whether a player can come in a way: a way that would leave a section with nobody is refused, and is no choice to try."""
    trial = WizardChoices.from_data(choices.to_data())
    try:
        trial.set_comes_in(role=role, way=way)
    except ValueError:
        return False
    return True


def another_velocity(velocity):
    """A velocity well apart from one."""
    return velocity - A_STEP_OF_VELOCITY if velocity > MIDDLE_VELOCITY else velocity + A_STEP_OF_VELOCITY


def set_reacts_where_heard(*, made, role):
    """Have a player react at the end of the gauge where the song is not the song the band's own reacting makes."""
    usual = made.made_for_listening()[0].to_data()[Section.PATTERNS]
    for reacts in (song_plan.LOWEST_ENERGY, song_plan.HIGHEST_ENERGY):
        made.set_reacts(role=role, reacts=reacts)
        if made.made_for_listening()[0].to_data()[Section.PATTERNS] != usual:
            return


def one_player_first(made):
    made.set_start(wizard_limits.ONE_PLAYER_FIRST)


def switch_plan_off(made):
    if made.can_have_song_plan():
        made.set_song_plan(False)


def without_plan(choices):
    """Choices as some are, with no song plan."""
    plain = WizardChoices.from_data(choices.to_data())
    switch_plan_off(plain)
    return plain


def fresh_with_plan(choices):
    """Choices as some are, with a song plan."""
    planned = WizardChoices.from_data(choices.to_data())
    planned.set_song_plan(True)
    return planned


def both(*, first, then):
    """Return one thing done first made of two, in order."""
    def done(made):
        first(made)
        then(made)
    return done


def far_row(*, choices, role, name):
    """A player's row with every cell at the end of its range the cell is further from."""
    lowest, highest = choices.get_band().row_limits(name)
    return [lowest if value - lowest > highest - value else highest for value in choices.player(role).get_row(name=name)]


def fresh_with_character(*, choices, character):
    """Return choices like some others with a character chosen for the melodies, to read what shows under it from."""
    chosen = WizardChoices.from_data(choices.to_data())
    chosen.set_melody_character(character)
    return chosen


def riff_pattern_of(*, choices, riff):
    """Return a riff's notes as the player the riff was written for plays them."""
    setlist, _, _, _, pattern = choices.get_riffs().riff_heard(riff)
    return setlist.get_pattern(pattern).to_data()


def busy_gauges(choices):
    """Yield (role, first) for each player whose Busy gauge the wizard shows."""
    for role in choices.get_band().roles_in():
        if choices.player(role).has_busy() and choices.player(role).get_busy() is not None:
            yield role, put_in(role) if plays_nowhere(choices=choices, role=role) else nothing_first


def changes(*, genre, subgenre, change, firsts):
    """Return whether a choice changes the song after any of the things done first."""
    for first in firsts:
        usual = fresh(genre=genre, subgenre=subgenre)
        first(usual)
        made = fresh(genre=genre, subgenre=subgenre)
        first(made)
        change(made)
        if song_of(made) != usual_song_of(usual):
            return True
    return False


def usual_song_of(usual):
    """The song the choices before a change make, made once for the choices as they stand: nearly every choice of a subgenre is
    held against the same one."""
    key = json.dumps(usual.to_data(), sort_keys=True, default=str)
    if key not in USUAL_SONGS:
        USUAL_SONGS[key] = song_of(usual)
    return USUAL_SONGS[key]


def positions_alike(*, genre, subgenre, role, first):
    """Return how many positions of a player's Busy gauge make a song another position makes."""
    songs = set()
    for level in range(wizard_limits.LEAST_BUSY, wizard_limits.MOST_BUSY + 1):
        made = fresh(genre=genre, subgenre=subgenre)
        first(made)
        made.player(role).set_busy(level=level)
        songs.add(json.dumps(song_of(made), sort_keys=True, default=str))
    return wizard_limits.MOST_BUSY + 1 - wizard_limits.LEAST_BUSY - len(songs)


def band_sound_differs(*, choices, role, sounds):
    other = WizardChoices.from_data(choices.to_data())
    other.get_sounds().set_band_sounds(sounds)
    return other.get_sounds().get_sound(role) != choices.get_sounds().get_sound(role)


def subgenres_of(genre):
    return fresh(genre=genre, subgenre=WizardChoices.from_data({arranger.GENRE: genre}).subgenres()[0]).subgenres()


def subgenre_of_the_day(*, genre, day):
    """Return the subgenre of a genre whose every choice is checked on a day: each in turn, by the day's number."""
    subgenres = subgenres_of(genre)
    return subgenres[day.toordinal() % len(subgenres)]


class EveryChoiceOfAGenre:
    """Every choice of the day's subgenre of one genre: a class for each genre, which run side by side."""

    GENRE = None

    def test_every_choice_changes_the_song_but_those_known_not_to(self):
        subgenre = subgenre_of_the_day(genre=self.GENRE, day=datetime.date.today())
        nothing = collections.defaultdict(list)
        tried = 0
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
        self.assertEqual(found, KNOWN_TO_CHANGE_NOTHING.get((self.GENRE, subgenre), {}), dict(nothing))


class TestTheSubgenreOfTheDay(unittest.TestCase):

    def test_every_subgenre_comes_in_turn_and_a_day_gives_one_subgenre_every_time(self):
        start = datetime.date(2026, 1, 1)
        for genre in genre_names():
            subgenres = subgenres_of(genre)
            with self.subTest(genre=genre):
                days = [start + datetime.timedelta(days=offset) for offset in range(len(subgenres))]
                self.assertEqual(sorted(subgenre_of_the_day(genre=genre, day=day) for day in days), sorted(subgenres))
                self.assertEqual(subgenre_of_the_day(genre=genre, day=start), subgenre_of_the_day(genre=genre, day=start))

    def test_every_dead_choice_known_is_of_a_subgenre_that_exists(self):
        for genre, subgenre in KNOWN_TO_CHANGE_NOTHING:
            self.assertIn(subgenre, subgenres_of(genre))


def class_for(genre):
    name = 'TestEveryChoiceOf{}'.format(''.join(word.capitalize() for word in genre.split('_')))
    return name, type(name, (EveryChoiceOfAGenre, unittest.TestCase), {'GENRE': genre, '__slots__': ()})


for a_genre in genre_names():
    a_name, a_class = class_for(a_genre)
    globals()[a_name] = a_class
del a_class
