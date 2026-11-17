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
from llamatron.macro_composer import hook_kinds, line_edits, phrasing
from llamatron.macro_composer.song_plan import HIGHEST_ENERGY, LOWEST_ENERGY
from llamatron.macro_composer.melody import LINE_NOTES
from llamatron.macro_composer.phrasing import LINE_BREATH, LONGEST_BREATH, NO_BREATH
from llamatron.macro_composer.wizard_choices import (HOOK_PARTS, LINE_BREATHES, ONE_PLAYER_FIRST, PHRASING_OFFERED, USUAL_PIECE_NOTE, BAND_SOUNDS, GAUGED_STYLES, FEWEST_FILLS, FILLS_TRAITS, LEAST_BUSY, MOST_BUSY, MOST_FILLS, ONE_GUITARIST_COUNT,
                                                     USUAL_SOUNDS, WizardChoices, genre_names)

A_NAME = 'a_song'
NOTES_KEPT = 'notes'
WIZARD_CHOICES_KEPT = 'wizard'
A_SEED = 7
ANOTHER_SEED = 8
A_SOUND_OF_NO_STYLE = 105
A_LITTLE_FASTER = 7
FIRST_PLACE = 0
# A genre's subgenres are dealt to so many classes, which run side by side, so that none runs past the runner's limit for a class.
PARTS = 6
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
MELODY_SETTING = 'melody setting'
HOOK = 'hook'
PLAYER_ROW = 'player row'
NEW_HOOK = 'new hook'
SONG_PLAN = 'song plan'
CONTRAST = 'contrast'
PHRASING = 'phrasing'
PHRASING_WAY = 'how the lines breathe'
HOOK_PART = "a part of the hook's kind"
HOOK_LINE = "the hook's notes written by hand"
A_LINE = "a line's own"
A_RIFF = 'the riff'
COMES_IN = 'where a player comes in'
REACTS_TO_ENERGY = 'how a player reacts'
START = 'a way of starting'
END = 'a way of ending'
FIRST_PLAYER = 'the first player'
SETUP_BARS = "the setup's bars"
DRUMS_ROLE = 'drums'
SECTION_OWN = "a section's own"
FORM_ANSWER = 'an answer of the form questions'
INTRO_HOOK = 'intro hook'
SECTION_SHAPE = "a section's shape"
# Arena rock's pre-chorus already sings at the top of the tune's range, so the shape that holds the second line back is the usual shape, at both pre-choruses.
FIRST_PART = 0
# Baroque pop's joins never rise far enough for the plan's big fill, so the short fill a person may choose is the one already
# played; and its one line that would come early repeats an idea, which takes no early note of its own. Bubblegum's singer,
# whose Energy never falls, plays two neighbouring positions of the gauge alike.
SECOND_PART = 1
THIRD_PART = 2
KNOWN_TO_CHANGE_NOTHING = {('rock', FIRST_PART): {SECTION_SHAPE: 2}, ('sixties_pop', FIRST_PART): {FILLS: 1, PHRASING_WAY: 2}, ('sixties_pop', THIRD_PART): {BUSY: 1},
                           # Disco's one line that would come early repeats an idea, as baroque pop's does.
                           ('soul_funk', FIRST_PART): {PHRASING_WAY: 2},
                           # Funk's plan plays the short fill at every join but the biggest, which a level song never has.
                           ('soul_funk', SECOND_PART): {FILLS: 1}}
A_SECOND_PLACE = 1
NO_PLAN = 'with no plan'
SECTION_OWN_ANYWHERE = (('fades', True), ('chords', '6 4 2 5'), ('chords', '1 4'), ('tempo', 61), ('tempo_end', 62), ('root', 'F#'), ('root', 'C'), ('type', 'minor'), ('type', 'major'))
# A value of each field a section can be given of its own.
SECTION_OWN_TRIED = (('rises', True), ('energy', 10), ('energy', 1), ('leaves', 'stops'), ('leaves', 'build'), ('leaves', 'drop-out'), ('leaves', 'a big fill'), ('leaves', 'a small fill'), ('leaves', 'nothing'),
                     ('chords', '6 4 2 5'), ('tempo', 61), ('tempo_end', 62), ('root', 'F#'), ('type', 'minor'), ('type', 'major'))
GUITARISTS = 'guitarists'
SEED = 'seed'
TEMPO = 'tempo'
SECTION_BARS = "a section's bars"
SECTION_KIND = "a section's kind"
FORM = 'form'
PLAYS_IN_SECTION = 'who plays in a section'
# How many choices of each kind change nothing, by genre and part, with the reason each is allowed for now.
# Rock and roll's planned song: its sections' Energies all ask for the hat in eighths, so choosing that cymbal is choosing what the plan already plays.
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
    # A melody style's own settings show once the style is chosen, the usual style's with none chosen, and every other value of each is held against the genre's own.
    for style in (None, *choices.melody_styles()):
        chosen = choices if style is None else fresh_with_melody(choices=choices, style=style)
        first = nothing_first if style is None else (lambda made, style=style: made.set_melody(style))
        for name in chosen.melody_settings() if choices.melody_styles() else []:
            for value in other_melody_values(choices=chosen, name=name):
                yield MELODY_SETTING, (style, name, value), lambda made, name=name, value=value: made.set_melody_setting(name=name, value=value), [first]
    # A player's rows show under the serial style, and each row with every cell moved to the far end of its range is held against the genre's own.
    for style in (None, *choices.melody_styles()):
        chosen = choices if style is None else fresh_with_melody(choices=choices, style=style)
        first = nothing_first if style is None else (lambda made, style=style: made.set_melody(style))
        for role in chosen.roles_in():
            for name in chosen.player_rows(role):
                row = far_row(choices=chosen, role=role, name=name)
                yield PLAYER_ROW, (style, role, name), lambda made, role=role, name=name, row=row: made.set_player_row(role=role, name=name, values=row), [first]
    if choices.can_have_hook():
        yield HOOK, not choices.has_hook(), lambda made: made.set_hook(not made.has_hook()), [nothing_first]
    if choices.can_have_hook() and choices.has_hook():
        yield NEW_HOOK, choices.get_hook_take() + 1, lambda made: made.new_hook(), [nothing_first]
    if choices.can_have_song_plan():
        # A planned song, and under a plan its contrast, its phrasing and each part of the hook's kind.
        def planned(made):
            made.set_song_plan(True)
        yield SONG_PLAN, False, lambda made: made.set_song_plan(False), [nothing_first]
        for contrast in (LOWEST_ENERGY, HIGHEST_ENERGY):
            yield CONTRAST, contrast, lambda made, contrast=contrast: made.set_contrast(contrast), [planned]
        under_plan = fresh_with_plan(choices)
        if under_plan.counts_in_four():
            yield PHRASING, False, lambda made: made.set_phrasing(False), [planned]
            for name, offered in PHRASING_OFFERED.items():
                for value in offered:
                    if value != phrasing.USUAL_WAYS[name]:
                        yield PHRASING_WAY, (name, value), lambda made, name=name, value=value: made.set_phrasing_way(name=name, value=value), [planned]
        if choices.can_have_hook() and choices.has_hook() and under_plan.counts_in_four():
            for part, offered in HOOK_PARTS.items():
                for value in offered:
                    if value != under_plan.hook_kind()[part]:
                        # A long note has neither a rhythm nor a detail to choose, so those are held under another contour.
                        first = planned if part == hook_kinds.CONTOUR else both(first=planned, then=lambda made: made.set_hook_part(part=hook_kinds.CONTOUR, value=hook_kinds.CHANT))
                        yield HOOK_PART, (part, value), lambda made, part=part, value=value: made.set_hook_part(part=part, value=value), [first]
    if choices.can_have_hook() and choices.has_hook() and choices.hook_line() is not None:
        # The hook's notes written by hand: its first note moved a note of the scale up.
        yield HOOK_LINE, 'first note up', lambda made: made.set_hook_line(line_edits.moved(line=made.hook_line(), step=0, by=1)), [nothing_first]
    if choices.can_have_song_plan():
        # What a section of a planned song is given of its own, each held under a plan: the second section, which a section follows.
        under_plan = fresh_with_plan(choices)

        def planned_first(made):
            made.set_song_plan(True)
        for role in under_plan.intro_hook_players():
            yield INTRO_HOOK, role, lambda made, role=role: made.set_intro_hook(role), [planned_first]
        for place in range(len(under_plan.section_labels())):
            for shape in under_plan.section_shapes(place):
                yield SECTION_SHAPE, (place, shape), lambda made, place=place, shape=shape: made.set_section_own(place=place, field='shape', value=shape), [planned_first]
        for field, value in SECTION_OWN_TRIED:
            if field in under_plan.section_own_fields(A_SECOND_PLACE) and value != under_plan.section_from_plan(place=A_SECOND_PLACE, field=field):
                yield SECTION_OWN, (field, value), lambda made, field=field, value=value: made.set_section_own(place=A_SECOND_PLACE, field=field, value=value), [planned_first]
    for field, value in SECTION_OWN_ANYWHERE:
        # What a section of any genre can be given of its own, held with no plan, on the second section where it takes any.
        if field in without_plan(choices).section_own_fields(A_SECOND_PLACE) and value != without_plan(choices).section_from_plan(place=A_SECOND_PLACE, field=field):
            yield SECTION_OWN, (field, value, NO_PLAN), lambda made, field=field, value=value: made.set_section_own(place=A_SECOND_PLACE, field=field, value=value), [switch_plan_off]
    # A section's lines, one by one: the first line that breathes of the first section with a tune, its breath, its early note either way and its notes moved.
    for place in range(len(choices.section_labels())):
        lines = choices.section_lines(place)
        line = next((count for count, said in enumerate(lines) if said[LINE_BREATHES]), None)
        if line is None:
            continue
        for breath in (NO_BREATH, LONGEST_BREATH - 1):
            yield A_LINE, (LINE_BREATH, breath), lambda made, place=place, line=line, breath=breath: made.set_section_line(place=place, line=line, field=LINE_BREATH, value=breath), [nothing_first]
        yield A_LINE, LINE_NOTES, lambda made, place=place, line=line: made.set_section_line(place=place, line=line, field=LINE_NOTES, value=first_note_moved(made.section_lines(place)[line][LINE_NOTES])), [nothing_first]
        break
    # A player as a person: each other way of coming in and of laying out, and Reacts at either end.
    for role in choices.roles_in():
        for way in choices.comes_in_offered(role):
            if way != choices.get_comes_in(role) and comes_in_works(choices=choices, role=role, way=way):
                yield COMES_IN, (role, way), lambda made, role=role, way=way: made.set_comes_in(role=role, way=way), [nothing_first]
        if choices.reacts(role):
            # A player who reacts is heard to at one end of the gauge at least: an even player may play as the band does where the band is never held back.
            yield REACTS_TO_ENERGY, role, lambda made, role=role: set_reacts_where_heard(made=made, role=role), [nothing_first]
    # The riff: given to the first players who can play one, played in each other place, made again, and its first note moved by hand.
    if choices.riff_players_offered():
        players = choices.riff_players_offered()[-1]
        with_riff = lambda made, players=players: made.set_riff(players=players)
        yield A_RIFF, tuple(players), with_riff, [nothing_first]
        staged = WizardChoices.from_data(choices.to_data())
        with_riff(staged)
        for said in staged.riff_said_offered():
            if said != staged.get_riff_said():
                yield A_RIFF, said, lambda made, players=players, said=said: made.set_riff(players=players, said=said), [with_riff]
        yield A_RIFF, 'another take', lambda made: made.new_riff(), [with_riff]
        yield A_RIFF, 'notes by hand', lambda made: made.set_riff_line(first_note_moved(made.riff_line())), [with_riff]
    # How the song starts and ends: each way but the one the song has, another first player under layers, and another length of a stage.
    for way in choices.starts():
        if way != choices.get_start():
            yield START, way, lambda made, way=way: made.set_start(way), [nothing_first]
    for way in choices.ends():
        if way != choices.get_end():
            yield END, way, lambda made, way=way: made.set_end(way), [nothing_first]
    if ONE_PLAYER_FIRST in choices.starts():
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


def set_reacts_where_heard(*, made, role):
    """Have a player react at the end of the gauge where the song is not the song the band's own reacting makes."""
    usual = made.made_for_listening()[0].to_data()[Section.PATTERNS]
    for reacts in (LOWEST_ENERGY, HIGHEST_ENERGY):
        made.set_reacts(role=role, reacts=reacts)
        if made.made_for_listening()[0].to_data()[Section.PATTERNS] != usual:
            return


def one_player_first(made):
    made.set_start(ONE_PLAYER_FIRST)


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
    lowest, highest = choices.row_limits(name)
    return [lowest if value - lowest > highest - value else highest for value in choices.get_player_row(role=role, name=name)]


def other_melody_values(*, choices, name):
    """Return every value a melody setting may take but the one it has."""
    now = choices.get_melody_setting(name)
    if choices.melody_setting_is_switch(name):
        return [not now]
    lowest, highest = choices.melody_setting_range(name)
    return [value for value in range(lowest, highest + 1) if value != now]


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
    PART = None

    def test_every_choice_changes_the_song_but_those_known_not_to(self):
        subgenres = fresh(genre=self.GENRE, subgenre=WizardChoices.from_data({'genre': self.GENRE}).subgenres()[0]).subgenres()
        nothing = collections.defaultdict(list)
        tried = 0
        for subgenre in subgenres[self.PART::PARTS]:
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
        self.assertEqual(found, KNOWN_TO_CHANGE_NOTHING.get((self.GENRE, self.PART), {}), dict(nothing))


def class_for(*, genre, half):
    name = 'TestEveryChoiceOf{}Part{}'.format(''.join(word.capitalize() for word in genre.split('_')), half + 1)
    return name, type(name, (EveryChoiceOfAGenre, unittest.TestCase), {'GENRE': genre, 'PART': half, '__slots__': ()})


for a_genre in genre_names():
    # A genre with fewer kinds than parts has a class for each kind and no empty one.
    for a_half in range(min(PARTS, len(WizardChoices.from_data({'genre': a_genre}).subgenres()))):
        a_name, a_class = class_for(genre=a_genre, half=a_half)
        globals()[a_name] = a_class
del a_class
