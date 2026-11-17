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

"""The arranger: a song's picks and a style template made into a MacroComposer input, a whole song.

A style template lists a style's traits, each with its values and how common each is; a value of a trait a band plays holds
the bar it plays: a drum's hits, or a figure of notes written over chord one, which a Progression moves through the song's
chords. A song's picks say which template of the style it starts from, the picks it changes, its key, its tempo, its
sections with their chords and its form. The arranger decides nothing but the tune, and that only where the song gives none:
it then sketches one by rule from the style's melody habits and the song's seed (melody.py). What it writes is an input the
MacroComposer composes, so every choice can be read and changed there.
"""

import math
import os
import random
from fractions import Fraction

from llamatron.macro_composer.breaks import BREAKS, LEAST_CUT, MOST_CUT, cut_up
from llamatron.macro_composer.characters import ADDS, BUSY, FILL, FILL_EVERY, GUITARIFY_OF_PLAYER, SAYS, TIMING, UNEVEN, VARIES, character_of, held_to, label_of, level_of
from llamatron.macro_composer import characters
from llamatron.macro_composer import drum_solo
from llamatron.macro_composer.interplay import ANSWERS as ANSWERS_EVERY_LINE, DRAWN_ANEW as WAYS_DRAWN_ANEW, USUAL_BUSY as USUAL_BESIDE_BUSY, WAITS, WAYS as WAYS_BESIDE, UnderLead
from llamatron.macro_composer.joins import DROP_OUT, FILL_OF_JOIN, LEAVES, STOPS, TAIL, TAIL_EIGHTHS, drum_tail, pieces_of_tail, with_tail
from llamatron.macro_composer.melody import ANSWER, ANSWER_RHYTHMS, ENGINE, FIRST_HOOK_TAKE, GRID, HOOK, HOOK_TAKE, LINE, RHYTHMS, SPAN, has_hook, sketched
from llamatron.macro_composer.loudness import NORMAL, USUAL_DYNAMICS, drum_levels, in_proportion, note_levels, scaled, spread, with_own
from llamatron.macro_composer.notation import ACCENT, ACCIDENTAL, DEGREE, DRUM, FLAT, GHOST, HITS, KIT, LINES, LOUD, NONE, OCTAVE, REST, SHARP, SOFT, STEP, STEPS, STEP_SIZE, VELOCITY, CHORD, clamped, drum_rows
from llamatron.macro_composer.players import player_name
from llamatron.macro_composer.riffs import (ACCENT_CHORDS, RIFF, RIFF_KINDS, RIFF_NOTES, RIFF_ROLES, RIFF_WITH_CHORDS, STAYS_HOME, accent_bars, bars_of as riff_bars_of, bars_played,
                                            flattened_in, held_bar, line_of as riff_line_of, single, split_bars)
from llamatron.macro_composer.shaping import COMPOUND_BEAT, SIMPLE_BEAT, is_compound
from llamatron.macro_composer.song_plan import PLAN_OF_SONG, SongPlan
from llamatron.support.safe_yaml import load_safely
from llamatron.composition.checks import in_whole_notes
from llamatron.composition.file_format import SECTION_KINDS, ChordSymbol, GeneratorKind, PatternSetting, Row, SceneSetting, Section
from llamatron.composition.generator_settings import FollowChordsSetting
from llamatron.composition.named_scale import scale_type_called
from llamatron.composition.limits import MAX_GM_SOUND, MAX_PROGRESSION_CHORDS, MAX_STEP_SIZE, MIN_GM_SOUND
from llamatron.strings.labels import MSG_GM_SOUNDS
from llamatron.strings.errors import ERR_NO_SUCH_WAY_BESIDE, ERR_PIECE_SOUND, ERR_BREAK_CUT, ERR_NO_STYLE_FORM, ERR_NO_SUCH_BREAK, ERR_NO_STYLE_FORMS, ERR_NO_STYLE_KIND, ERR_NO_SUCH_SECTION, ERR_NO_TRAIT_VALUE, ERR_PICK_NEEDS
from llamatron.strings.macro_composer import MSG_CHORDS_INSTRUMENT, MSG_CHORDS_TRACK, MSG_FOLLOW_CHORDS_NAME, MSG_PIECE_INSTRUMENT, MSG_MADE_PICK, MSG_MADE_SCENE, MSG_MADE_SONG_NOTES, MSG_PART_AT_LEVEL, MSG_PART_BESIDE, MSG_PART_OF_SECTION, MSG_PLAYED_BY, MSG_PLAYED_BY_OWN, MSG_REPEATED_SCENE, MSG_SECTION_START_PART, MSG_TIMING_CHAIN

# The fields of a style template.
NAME = 'name'
TITLE = 'title'
GENRE = 'genre'
SUBGENRE = 'subgenre'
FEEL = 'feel'
# The song's groove: a swing a subgenre is played with, by the name of one of the grooves every set has, or none.
GROOVE = 'groove'
NO_GROOVE = 'none'
TEMPLATES = 'templates'
TRAITS = 'traits'
ROLES = 'roles'
SOUNDS = 'sounds'
SECTIONS = 'sections'
MELODY = 'melody'
LOUDNESS = 'loudness'
# The fields of a trait's value.
VALUE = 'value'
SHARE = 'share'
NEEDS = 'needs'
BAR = 'bar'
FIGURE = 'figure'
SOUND = 'sound'
# The sounds a song chooses for its players itself, each a General MIDI number by the player's name.
ROLE_SOUNDS = 'role_sounds'
# The pieces of the drum kit a song switches off.
WITHOUT_PIECES = 'without_pieces'
# What a song has pieces of the kit sound as, by piece: another drum of the kit (played_drum), or a General MIDI sound on one
# note (sound and note), which makes the piece a track with an instrument of its own, since the drum channel plays only the kit.
PIECE_SOUNDS = 'piece_sounds'
# The player beside the tune: who, how busy, and what the player does in each section of the form, in the form's order.
BESIDE = 'beside'
BESIDE_BUSY = 'busy'
BESIDE_WAYS = 'ways'
PLAYED_DRUM = 'drum'
PLAYED_SOUND = 'sound'
PLAYED_NOTE = 'note'
LOWEST_NOTE = 0
HIGHEST_NOTE = 127
# A style's melody habits for one scale type, in place of its usual ones.
BY_SCALE_TYPE = 'by_scale_type'
# How often a song has a fill come: 0 for never, each section, or every so many bars; and whether the snare's quiet notes are played.
FILLS_COME = 'fills_come'
EACH_SECTION = 'each section'
QUIET_NOTES = 'quiet_notes'
SNARE = 'snare'
ROLE_TITLE = 'title'
ROLE_TITLES = 'titles'
GENERATORS = 'generators'
PATTERN = 'pattern'
EVERY = 'every'
HALVES_OF_A_BAR = 2
SCALE_TYPE = 'scale_type'
# The fields of a role.
ROLE = 'role'
TRAIT = 'trait'
DRUMS = 'drums'
TUNE = 'tune'
ANSWERS = 'answers'
VOICE_LEADING = 'voice_leading'
# The fields of a section.
BARS = 'bars'
PLAYS = 'plays'
PLAN = 'plan'
CHORDS = 'chords'
HELD = 'held'
LINES_GIVEN = 'tunes'
# The fields of a song's picks.
STYLE = 'style'
TEMPLATE = 'template'
PICKS = 'picks'
# The roles a song leaves out of its band, by name.
WITHOUT = 'without'
KEY = 'key'
ROOT = 'root'
TYPE = 'type'
TEMPO = 'tempo'
SEED = 'seed'
FORM = 'form'
DESCRIPTION = 'description'
# The traits the arranger reads by name.
METER = 'meter'
CHORD_TRAIT = 'chords'
CHORD_TRAIT_FIELD = 'chord_trait'
FILLS = 'fills'
PHRASE_BARS = 'phrase_bars'
USUAL = 'usual'
# What the MacroComposer's input names.
NOTES = 'notes'
SCALES = 'scales'
SCALE = 'scale'
TIME_SIGNATURE = 'time_signature'
SHAPED = 'shaped'
INSTRUMENTS = 'instruments'
TRACKS = 'tracks'
DRUM_TRACKS = 'drum_tracks'
CHAINS = 'chains'
PARTS = 'parts'
SCENE = 'scene'
PLAY = 'play'
PART = 'part'
ONCE = 'once'
PROGRESSIONS = 'progressions'
PROGRESSION = 'progression'
ACCIDENTALS = 'accidentals'
VOICE_LEADINGS = 'voice_leadings'
NEAR = 'near'
DRUM_KIT = 'drum kit'
CRASH = 'crash'
KICK = 'kick'
COMMON_TIME = '4/4'
ACCIDENTAL_MARKS = {SHARP: '#', FLAT: 'b'}
# The chords track: its chords as the pattern editor's Chord row names them, and what a clip that follows it has first in its chain.
SCALE_TRIAD = 3
HOME_DEGREE = 1
NOTES_OF_A_SCALE_WITH_TRIADS = 7
THIRD_PLACE = 2
FIFTH_PLACE = 4
HOME_CHORDS = {(4, 7): ChordSymbol.MAJOR, (3, 7): ChordSymbol.MINOR, (3, 6): ChordSymbol.DIMINISHED, (4, 8): ChordSymbol.AUGMENTED}
FOLLOWS_THE_CHORDS = {GeneratorKind.FOLLOW_CHORDS: MSG_FOLLOW_CHORDS_NAME}
MUTED_TRACKS = 'muted_tracks'
# The General MIDI sound of the chords track's instrument, a piano, heard only when a person unmutes the track.
CHORDS_GUIDE_SOUND = 1
NEAR_VOICES = {'lowest_octave': 3, 'highest_octave': 5}
DEFAULT_PHRASE_BARS = 4
EIGHTH = '1/8'
EIGHTHS_IN_WHOLE = 8
KIND = 'kind'
# The fields of a player: a role says which instrument's player plays it, a song gives each instrument's complexity, and a
# style says, for each instrument and complexity, what that player picks and how the player keeps time.
PLAYER = 'player'
PLAYERS = 'players'
CHOICES = 'choices'
SILENCES = 'silences'
ALLOWS = 'intensity'
CRASH_START = 'crash'
ENDS = 'ends'
# A song's pick of the engine its tunes are made by, and a role's own voice and habits for it.
MELODY_ENGINE = 'melody_engine'
VOICE = 'voice'
HABITS = 'habits'
# A song's own habits for a player, by the player's role, which come over the genre's for that player.
ROLE_HABITS = 'role_habits'
STYLE_TEMPLATES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'style_templates')
STYLE_SUFFIX = '.yml'
# A scale's name from its root and type, and what a drum's uneven hits are seeded by: the song's seed, the drum and the section.
SCALE_NAME = '{} {}'
DRUM_SEED = '{} {} {}'
FILE_ENCODING = 'utf-8'
FORMS = 'forms'
LENGTH = 'length'
SECONDS_IN_A_MINUTE = 60
BEATS_IN_A_WHOLE = 4
# A song's pick of a drum break, which takes the place of every way the drums are played but the percussion's, the pick that
# says a subgenre built on a break plays none, how far the break is cut up, and what the cutting of a bar is seeded by.
BREAK = 'break'
NO_BREAK = 'none'
BREAK_CUT = 'break_cut'
KEPT_BESIDE_A_BREAK = 'percussion'
CUT_SEED = 'cut {} {}'
RUSH = 'rush'
DRAG = 'drag'
RUSHES = 'rushes'
DRAGS = 'drags'
RAW = 'raw'
AMOUNT = 'amount'
GENERATOR_STEPS = 'steps'
GUITARIFIES = 'guitarifies'
# The set's section that holds each kind of generator a value may bring.
SECTION_OF_KIND = {'guitarify': 'guitarifies', 'arp': 'arps', 'strum': 'strums'}
VOICE_LEADING_KIND = 'voice_leading'
HELD_CHORD = '3'
MAJOR = 'major'
BY_SECTION = 'by_section'
FAMILIES = 'families'
BY_FAMILY = 'by_family'
# How common a value is in a template, by the template's name, in place of its share in the family or the style: a share of 0 is offered last and never drawn by chance.
BY = 'by'
# What a style says differently for one of its templates, laid over the style: a section's bars, the plan's numbers and the like.
BY_SUBGENRE = 'by_subgenre'
# The kinds of song a subgenre holds, each drawn whole: a name, how common it is, a line that says what it is, and what the kind
# says differently from its subgenre, laid over the style as the subgenre's own words are. A song names its kind as its variant.
VARIANTS = 'variants'
VARIANT = 'variant'
VARIANT_SAYS = 'says'
# How far a song's players' levels lie from their normal ones, by the player's name, from 0 to 10; a song's own levels for a
# player are under the style's word for loudness.
DYNAMICS = 'dynamics'
# A style's lean on each beat of the bar: how much louder or softer the drums' strokes on the beat are, beat by beat.
BEAT_LOUDNESS = 'beat_loudness'
# A player of notes' accent, soft and ghost velocities, where the song gives the player levels or dynamics of its own.
LEVELS_OF_ROLE = 'levels'
# The keys whose home note is the lowest of an octave: a band written for the middle of its range plays an octave up in them.
LOW_ROOTS = ('C', 'C#', 'Db', 'D', 'D#', 'Eb')
# What a planned section says of itself (song_plan.py): each instrument's level in the section, in place of the song's; the
# scene's own settings; what the section is called where a part is the same each time its kind comes; what is said of the
# section in the song's notes; that the drummer plays it alone, as a solo; and the small fill inside it with how many bars apart it comes.
LEVELS_HERE = 'levels'
SCENE_SETTINGS = 'settings'
SECTION_OF_SCENE = SceneSetting.SECTION
DRAWN_AS = 'drawn_as'
SAID_OF_SECTION = 'said'
DRUM_SOLO = 'drum_solo'
FILL_INSIDE = 'fill_inside'
FILL_INSIDE_EVERY = 'fill_inside_every'
MARKER = 'marker'
MARKER_EVERY = 'marker_every'
MADE_SCENE_SAID = '{} {}'
LAST_CHORD = 'last_chord'
SETTINGS_OF_SCENE = 'settings'



def listed(names):
    return ', '.join(sorted(str(name) for name in names))


def values_of(*, style, trait):
    return {entry[VALUE]: entry for entry in style[TRAITS][trait]} if isinstance(style[TRAITS].get(trait), list) else {}


def fits(*, entry, picks):
    return all(picks.get(trait) == wanted for trait, wanted in entry.get(NEEDS, {}).items() if trait in picks)


def picked(*, style, song):
    """Every trait's pick: the song's own, else its template's, else the commonest value that fits what is picked."""
    templates = style[TEMPLATES]
    if song[TEMPLATE] not in templates:
        raise ValueError(ERR_NO_STYLE_KIND.format(style[NAME], song[TEMPLATE], listed(templates)))
    picks = {**templates[song[TEMPLATE]]}
    picks.update(song.get(PICKS, {}))
    for trait in style[TRAITS]:
        values = values_of(style=style, trait=trait)
        if not values:
            continue
        if trait not in picks:
            fitting = [entry for entry in values.values() if fits(entry=entry, picks=picks)]
            picks[trait] = max(fitting, key=share_of)[VALUE]
        if picks[trait] not in values:
            raise ValueError(ERR_NO_TRAIT_VALUE.format(trait, picks[trait], listed(values)))
    for trait, value in picks.items():
        for needed, wanted in values_of(style=style, trait=trait).get(value, {}).get(NEEDS, {}).items():
            if picks.get(needed) != wanted:
                raise ValueError(ERR_PICK_NEEDS.format(trait, value, needed, wanted, picks.get(needed)))
    return picks


def style_names():
    """The names of the style templates there are."""
    return sorted(name[:-len(STYLE_SUFFIX)] for name in os.listdir(STYLE_TEMPLATES) if name.endswith(STYLE_SUFFIX))


def style_named(name):
    """A style template, read from its file."""
    with open(os.path.join(STYLE_TEMPLATES, name + STYLE_SUFFIX), encoding=FILE_ENCODING) as file:
        return load_safely(file)


def player_of(*, style, instrument, character):
    """What a style says of an instrument's player of a character, or nothing."""
    return characters.player_of(levels=style.get(PLAYERS, {}).get(instrument, {}), character=character)


def players_in(*, style, roles, levels, section):
    """Each role's player in a section: the song's, held to the complexity the section allows the instrument."""
    return {role[ROLE]: player_of(style=style, instrument=role.get(PLAYER), character=character_in(levels=levels, instrument=role.get(PLAYER), section=section)) for role in roles}


def character_in(*, levels, instrument, section):
    """The character an instrument's player plays with in a section, or nothing where the song names no player for the instrument: the
    song's, a level or the places of its gauges, held to the level the section allows the instrument."""
    here = section.get(LEVELS_HERE, {}).get(instrument)
    if here is not None:
        return character_of(here)
    if instrument not in levels:
        return None
    return held_to(character=character_of(levels[instrument]), allowed=section.get(ALLOWS, {}).get(instrument))


def timing_generators(*, move):
    """A track's Rush and Drag: every step moved by the amount the player gives, or neither doing anything, there to be changed."""
    return {kind: ({GENERATOR_STEPS: [True], AMOUNT: move[kind]} if kind in move else {GENERATOR_STEPS: [False]}) for kind in (RUSH, DRAG)}


def drum_pattern(part):
    """A drum's part as a pattern."""
    return drum_rows(drum=part[DRUM], hits=part[HITS], loud=part[LOUD], soft=part[SOFT], step_size=part[STEP], accent=part.get(ACCENT), ghost=part.get(GHOST))


def uneven(*, pattern, by, dice):
    """A drum's pattern with hits that each differ a little in loudness, as a person's do."""
    return {**pattern, VELOCITY: [None if loud is None else clamped(loud + dice.randint(-by, by)) for loud in pattern[VELOCITY]]}


def leaning(*, pattern, profile, meter, dynamics):
    """A drum's pattern with the strokes on each beat louder or softer by the style's lean on that beat, as far as the drummer's dynamics say."""
    size = Fraction(pattern[STEP_SIZE])
    beat = COMPOUND_BEAT if is_compound(meter) else SIMPLE_BEAT
    velocities = []
    for place, loud in enumerate(pattern[VELOCITY]):
        count = ((place * size) % bar_length(meter)) / beat
        on_a_beat = loud is not None and count.denominator == 1
        velocities.append(clamped(loud + scaled(move=profile[int(count) % len(profile)], dynamics=dynamics)) if on_a_beat else loud)
    return {**pattern, VELOCITY: velocities}


def drummer_role(roles):
    """The name of the role that plays the drums."""
    return next((role[ROLE] for role in roles if role.get(DRUMS)), DRUMS)


def loud_style(*, style, song, roles):
    """A style with each drum's four levels worked out, as the song has them: the kit's levels where the song gives its own, every
    piece moved in proportion, and each level as far from the normal one as the drummer's dynamics say."""
    drummer = drummer_role(roles)
    kit = drum_levels(style[LOUDNESS][DRUMS])
    chosen = with_own(levels=kit, own=song.get(LOUDNESS, {}).get(drummer))
    dynamics = song.get(DYNAMICS, {}).get(drummer, USUAL_DYNAMICS)
    return {**style, LOUDNESS: {piece: spread(levels=in_proportion(levels=drum_levels(given), kit=kit, chosen=chosen), dynamics=dynamics)
                                for piece, given in style[LOUDNESS].items()}}


def loud_role(*, role, song):
    """A player of notes as loud as the song has the player: the role with the song's levels and dynamics for it, where it gives any."""
    own = song.get(LOUDNESS, {}).get(role[ROLE])
    dynamics = song.get(DYNAMICS, {}).get(role[ROLE])
    if VELOCITY not in role or (own is None and dynamics is None):
        return role
    levels = spread(levels=with_own(levels=note_levels(role[VELOCITY]), own=own), dynamics=USUAL_DYNAMICS if dynamics is None else dynamics)
    return {**role, VELOCITY: levels[NORMAL], LEVELS_OF_ROLE: {level: levels[level] for level in (ACCENT, SOFT, GHOST)}}


def voice_of(role):
    """How loud a player's part is: the velocity, and the player's other levels where the song gives any."""
    return {VELOCITY: role[VELOCITY], **role.get(LEVELS_OF_ROLE, {})}


def struck(*, levels, hits):
    """How loud a drum's part is: its normal and soft strokes, and its accent and ghost note where its hits have any."""
    return {LOUD: levels[NORMAL], SOFT: levels[SOFT], **{level: levels[level] for level in (ACCENT, GHOST) if level in hits}}


def share_of(entry):
    return entry[SHARE]


def share_in(*, style, entry, template):
    """How common a value is in one of a style's templates: its share in the template's family where the style has families and the
    value says how common it is in each, or its share in the style as a whole; a value that says how common it is in the template itself is that common."""
    if template in entry.get(BY, {}):
        return entry[BY][template]
    family = style.get(FAMILIES, {}).get(template)
    return entry.get(BY_FAMILY, {}).get(family, entry[SHARE])


def said_over(*, usual, own):
    """What a style says with one template's own words laid over it: a dictionary's entries one by one, anything else replaced whole."""
    if not isinstance(usual, dict) or not isinstance(own, dict):
        return own
    return {**usual, **{key: said_over(usual=usual[key], own=value) if key in usual else value for key, value in own.items()}}


STYLES_IN_TEMPLATES = {}


def variants_of(*, style, template):
    """The kinds of song a style's template holds, the commonest first, or none."""
    return sorted(style.get(VARIANTS, {}).get(template, []), key=share_of, reverse=True)


def variant_named(*, style, template, variant):
    """One kind of song of a template by its name, or None for a name the template has no kind of, as a song kept before the kind was renamed."""
    return next((entry for entry in variants_of(style=style, template=template) if entry[NAME] == variant), None)


def style_in(*, style, template, variant=None):
    """A style as one of its templates has it: what the style says by_subgenre for the template laid over the style, and then what
    the song's kind says laid over that, worked out once. A style that says nothing of the template or the kind, or one already so
    laid over, is returned as it is."""
    own = style.get(BY_SUBGENRE, {}).get(template)
    kind = variant_named(style=style, template=template, variant=variant)
    if not own and kind is None:
        return style
    key = (style[NAME], template, variant if kind is not None else None)
    if key not in STYLES_IN_TEMPLATES:
        laid = said_over(usual={name: value for name, value in style.items() if name != BY_SUBGENRE}, own=own) if own else style
        STYLES_IN_TEMPLATES[key] = {**(said_over(usual=laid, own=kind.get(STYLE, {})) if kind is not None else laid)}
    return STYLES_IN_TEMPLATES[key]


def bar_length(meter):
    return Fraction(meter)


def step_of(*, meter, grid):
    return str(bar_length(meter) / grid)


def chord_of(entry):
    """A chord as written, as its degree and what else it says; a bar of two chords is its first, for whatever goes bar by bar."""
    if isinstance(entry, list):
        return chord_of(entry[0])
    return entry if isinstance(entry, dict) else {DEGREE: entry}


def shares_a_bar(entry):
    """Whether an entry of a progression is two chords in one bar, each half of it."""
    return isinstance(entry, list)


def halves_of(chords):
    """Chords by the half bar: a bar of two chords as its two, and a bar of one as the one twice."""
    return [half for chord in chords for half in (chord if shares_a_bar(chord) else [chord, chord])]


def fits_by_halves(chords):
    """Whether chords written by the half bar are no more than a Progression holds; a longer run is played a chord a bar, each
    bar's first."""
    return len(chords) * HALVES_OF_A_BAR <= MAX_PROGRESSION_CHORDS


def half_bar_of(meter):
    """Half a bar of a meter, as a time a Progression takes: a length in whole notes."""
    return str(Fraction(meter) / HALVES_OF_A_BAR)


def progression_of(*, chords, every, meter=COMMON_TIME):
    """A list of chords as a Progression's settings; where a bar has two chords and nothing says how long a chord lasts, each
    chord lasts half a bar, so long as a Progression holds that many."""
    if not every and any(shares_a_bar(chord) for chord in chords) and fits_by_halves(chords):
        chords = halves_of(chords)
        every = half_bar_of(meter)
    made = {CHORDS: [chord_of(chord)[DEGREE] for chord in chords]}
    marks = [ACCIDENTAL_MARKS.get(chord_of(chord).get(ACCIDENTAL)) for chord in chords]
    if any(marks):
        made[ACCIDENTALS] = marks
    if every:
        made[EVERY] = every
    return made


def home_chord_of(scale_type):
    """The chord symbol of the chord a scale type builds on its first note, or nothing where its third and fifth name no plain chord or it has not seven notes."""
    shape = scale_type_called(scale_type).value
    if len(shape) != NOTES_OF_A_SCALE_WITH_TRIADS:
        return None
    return HOME_CHORDS.get((shape[THIRD_PLACE], shape[FIFTH_PLACE]))


def chords_written(*, progression, meter, scale_type):
    """A progression's chords as a pattern of the chords track, a step a chord, each a triad of the scale on its degree; a chord
    on a degree with a sharp or a flat is the scale's home chord moved there, as a Progression plays it. Nothing where a chord
    lasts longer than a step can, or such a chord's kind cannot be named: the chords track then makes its chords with the
    Progression."""
    bar = Fraction(meter)
    lasts = Fraction(str(in_whole_notes(time=progression[EVERY], bar=bar))) if EVERY in progression else bar
    marks = progression.get(ACCIDENTALS) or [None] * len(progression[CHORDS])
    home = home_chord_of(scale_type)
    if lasts > MAX_STEP_SIZE or (any(marks) and home is None):
        return None
    written = {
        PatternSetting.STEPS: len(progression[CHORDS]), PatternSetting.STEP_SIZE: str(lasts), Row.DEGREE: list(progression[CHORDS]),
        Row.CHORD: [SCALE_TRIAD if mark is None else home for mark in marks],
    }
    if any(marks):
        written[Row.ACCIDENTAL] = list(marks)
    return written


def one_chord(meter):
    """The home chord for a bar, as a pattern of the chords track that a Progression moves."""
    return {PatternSetting.STEPS: 1, PatternSetting.STEP_SIZE: str(Fraction(meter)), Row.DEGREE: [HOME_DEGREE], Row.CHORD: [SCALE_TRIAD]}


def hits_of(marks):
    """A decoration's drum as hits: it says how many steps its bar has and which are accents, loud, soft and ghost notes."""
    return [next((level for level in (ACCENT, LOUD, SOFT, GHOST) if place in marks.get(level, [])), NONE) for place in range(marks[STEPS])]


def choice_that_fits(*, choices, picks):
    """The first of a decoration's choices that fits the song's picks, as each drum's hits, or nothing."""
    for choice in choices or []:
        if fits(entry=choice, picks=picks):
            return {piece: hits_of(marks) for piece, marks in choice[BAR].items()}, choice.get(SILENCES, [])
    return {}, []


def widened(*, hits, to):
    """A bar's hits on a finer grid."""
    finer = []
    for hit in hits:
        finer += [hit] + [NONE] * (to // len(hits) - 1)
    return finer


def laid_over(*, bar, more):
    """A bar with a decoration's hits wherever the bar has none."""
    return [added if hit == NONE else hit for hit, added in zip(bar, more)]


def break_of(*, picks, meter):
    """The bar of the break the picks name, a drum's hits for each drum, or None where they name none or the meter is not
    the one a break is written in."""
    name = picks.get(BREAK, NO_BREAK)
    if name == NO_BREAK or meter != COMMON_TIME:
        return None
    if name not in BREAKS:
        raise ValueError(ERR_NO_SUCH_BREAK.format(name, listed(BREAKS)))
    return BREAKS[name]


def cut_of(picks):
    """How far the picks cut their break up."""
    cut = picks.get(BREAK_CUT, LEAST_CUT)
    if isinstance(cut, bool) or not isinstance(cut, int) or not LEAST_CUT <= cut <= MOST_CUT:
        raise ValueError(ERR_BREAK_CUT.format(LEAST_CUT, MOST_CUT, cut))
    return cut


def pieces_played(song):
    """What each remapped piece of a song's kit plays, as the drum's name or the note's number drum_rows takes, each checked."""
    played = {}
    for piece, sounds_as in song.get(PIECE_SOUNDS, {}).items():
        if set(sounds_as) == {PLAYED_DRUM} and sounds_as[PLAYED_DRUM] in KIT:
            played[piece] = sounds_as[PLAYED_DRUM]
        elif set(sounds_as) == {PLAYED_SOUND, PLAYED_NOTE} and whole(value=sounds_as[PLAYED_SOUND], low=MIN_GM_SOUND, high=MAX_GM_SOUND) and whole(value=sounds_as[PLAYED_NOTE], low=LOWEST_NOTE, high=HIGHEST_NOTE):
            played[piece] = sounds_as[PLAYED_NOTE]
        else:
            raise ValueError(ERR_PIECE_SOUND.format(piece, sounds_as))
    return played


def whole(*, value, low, high):
    """Whether a value is an integer within a range."""
    return not isinstance(value, bool) and isinstance(value, int) and low <= value <= high


def drum_parts(*, style, picks, roles, meter, phrase_bars, drummer, section_bars, own_fill=False, seed=0, kit=None, leaves=None, inside=None, over=None):
    """Each drum the picks play, as a part some bars long: the kind's own bar, decorated as the drummer decorates it, a bar of
    the bars of each phrase that the drummer varies each a little different, and its last bar the fill. A drummer who says nothing plays the kind's bar
    and the song's fill at the end of every phrase. Where the picks name a break, the break's bar is the kind's, in place of
    every way but the percussion's, and each bar of a phrase after the first is the break cut up, its own way, by the seed.

    A section that says what it leaves with is written out whole: its last bar is the join's fill under the join's tail, and
    the small fill inside comes only as often as the section says.

    over gives a piece bars of its own, bar by bar of the section and round again, as a kick that follows a riff: such a bar
    is played as given, in place of the kind's bar and all the drummer adds to it, and a bar given as None is the kind's."""
    bars = {}
    over = over or {}
    played_break = break_of(picks=picks, meter=meter)
    for role in roles:
        if role.get(DRUMS):
            for trait in role[DRUMS]:
                if played_break is None or trait == KEPT_BESIDE_A_BREAK:
                    bars.update(values_of(style=style, trait=trait)[picks[trait]].get(BAR, {}))
    cut_bars = {}
    if played_break is not None:
        bars.update(played_break)
        cut = cut_of(picks)
        for count in range(1, phrase_bars):
            cut_bars[count] = cut_up(bars=played_break, cut=cut, dice=random.Random(CUT_SEED.format(seed, count)))
    # A section always ends on the fill, so that it hands over to the next: the part is no longer than divides the section.
    length = math.gcd(drummer.get(FILL_EVERY, phrase_bars) or phrase_bars, section_bars)
    fill_every = length
    if over:
        # Bars given one by one are the whole section's.
        length = section_bars
    fill, silences = choice_that_fits(choices=drummer.get(FILL), picks=picks)
    if not fill or own_fill:
        # The fill the song chose itself is played whatever the drummer would play, a song that chose none having none.
        fill, silences = values_of(style=style, trait=FILLS).get(picks.get(FILLS), {}).get(FILL, {}), []
    if drummer.get(FILL_EVERY) == 0:
        fill, silences = {}, []
    last_fill = {}
    if leaves is not None:
        # A planned section: the fill inside is the small one the section names, and the last bar's is the join's.
        length = section_bars
        fill_every = length
        fill, silences = fill_named(style=style, name=(inside or {}).get(FILL_INSIDE)), []
        last_fill = fill_named(style=style, name=leaves.get(FILL_OF_JOIN))
    tail = (leaves or {}).get(TAIL)
    inside_every = (inside or {}).get(FILL_INSIDE_EVERY) or length
    # A marker is a stroke or two laid over a phrase's last bar where no fill is played.
    marker = ((inside or {}).get(MARKER) or {}) if leaves is not None else {}
    marker_every = (inside or {}).get(MARKER_EVERY) or length
    adds, _ = choice_that_fits(choices=drummer.get(ADDS), picks=picks)
    varied = []
    for variation in drummer.get(VARIES, []):
        more, _ = choice_that_fits(choices=variation[CHOICES], picks=picks)
        varied.append((variation[BARS], more))
    parts = {}
    every = [bars, adds, fill, last_fill, marker, {piece: [NONE] for piece in pieces_of_tail(tail)}] + [more for _, more in varied]
    every += [{piece: given} for piece, given_bars in over.items() for given in given_bars if given is not None]
    for piece in list(dict.fromkeys(piece for layer in every for piece in layer)):
        layers = [layer[piece] for layer in every if piece in layer]
        grid = math.lcm(*(len(layer) for layer in layers))
        plain = widened(hits=bars.get(piece, [NONE]), to=grid)
        if piece in adds:
            plain = laid_over(bar=plain, more=widened(hits=adds[piece], to=grid))
        hits = []
        for bar in range(1, length + 1):
            if leaves is None and bar % fill_every == 0 and piece in fill:
                hits += widened(hits=fill[piece], to=grid)
            elif leaves is None and bar % fill_every == 0 and piece in silences:
                hits += [NONE] * grid
            else:
                played = plain
                own = over[piece][(bar - 1) % len(over[piece])] if piece in over else None
                if own is not None:
                    played = widened(hits=own, to=grid)
                elif piece in cut_bars.get((bar - 1) % phrase_bars, {}):
                    played = widened(hits=cut_bars[(bar - 1) % phrase_bars][piece], to=grid)
                    if piece in adds:
                        played = laid_over(bar=played, more=widened(hits=adds[piece], to=grid))
                for which, more in varied if own is None else []:
                    if piece in more and (bar - 1) % phrase_bars + 1 in which:
                        played = laid_over(bar=played, more=widened(hits=more[piece], to=grid))
                if leaves is not None and bar == length and tail is not None:
                    played = drum_tail(piece=piece, plain=played, tail=tail, eighths=leaves.get(TAIL_EIGHTHS, 0))
                elif leaves is not None and bar == length and piece in last_fill:
                    played = widened(hits=last_fill[piece], to=grid)
                elif leaves is not None and bar != length and bar % inside_every == 0 and piece in fill:
                    played = widened(hits=fill[piece], to=grid)
                elif bar != length and bar % marker_every == 0 and bar % inside_every != 0 and piece in marker:
                    played = laid_over(bar=played, more=widened(hits=marker[piece], to=grid))
                hits += played
        # A style as written says a drum's normal stroke alone, and a song's style all four levels.
        levels = drum_levels(style[LOUDNESS].get(piece, style[LOUDNESS][DRUMS]))
        parts[piece] = {DRUM: (kit or {}).get(piece, piece), STEP: step_of(meter=meter, grid=grid), **struck(levels=levels, hits=hits), HITS: hits}
    return parts


def fill_named(*, style, name):
    """The fill of a name, each drum's hits, or no fill for no name or a name the style lacks."""
    return values_of(style=style, trait=FILLS).get(name, {}).get(FILL, {})


def solo_parts(*, style, bars, seed, kit):
    """A drum solo's parts, a part for each piece of the kit that sounds in it."""
    parts = {}
    for piece, hits in drum_solo.solo_hits(bars=bars, seed=seed).items():
        # A style as written says a drum's normal stroke alone, and a song's style all four levels.
        levels = drum_levels(style[LOUDNESS].get(piece, style[LOUDNESS][DRUMS]))
        parts[piece] = {DRUM: (kit or {}).get(piece, piece), STEP: drum_solo.STEP, **struck(levels=levels, hits=hits), HITS: hits}
    return parts


def frozen(value):
    """Plain data as something that can be a key."""
    if isinstance(value, dict):
        return tuple(sorted((name, frozen(inner)) for name, inner in value.items()))
    if isinstance(value, list):
        return tuple(frozen(inner) for inner in value)
    return value


def one_hit(*, style, meter, drum, played):
    """One bar in which a piece of the kit is hit once, on the first beat, as the drum or the note the song has the piece play."""
    loud = style[LOUDNESS].get(drum, style[LOUDNESS][DRUMS])[NORMAL]
    return {DRUM: played.get(drum, drum), STEP: EIGHTH, LOUD: loud, SOFT: loud, HITS: [LOUD] + [NONE] * (int(bar_length(meter) * EIGHTHS_IN_WHOLE) - 1)}


def lasts(note):
    """How many steps a note or a rest of a figure lasts."""
    return note.get(REST, note.get(STEPS, 0))


def with_ending(*, bar, ends):
    """A figure's bar whose last steps are a decoration's notes: what the bar played before them stays, a note they cut into shortened."""
    room = sum(lasts(note) for note in bar) - sum(lasts(note) for note in ends)
    kept = []
    for note in bar:
        if room <= 0:
            break
        length = min(lasts(note), room)
        kept.append({**note, (REST if REST in note else STEPS): length})
        room -= length
    return kept + [dict(note) for note in ends]


def ending_fits(*, variation, grid, meter):
    """Whether a player's ending can be laid on a figure: it is written for the meter, or for any, and one of the two grids
    divides the other, so that the finer holds both."""
    if ENDS not in variation or variation.get(NEEDS, {}).get(METER, meter) != meter:
        return False
    return grid % variation[GRID] == 0 or variation[GRID] % grid == 0


def stretched(*, notes, by):
    """Notes written again on a grid so many times finer."""
    return [{**note, (REST if REST in note else STEPS): lasts(note) * by} for note in notes]


def decorated_figure(*, bars, player, phrase_bars, meter):
    """A figure as a player plays it: a phrase of its bars, the bars the player varies ending in the player's own notes, on
    the finest grid of the figure's and the endings'. A player who varies nothing plays the figure as written, and an ending
    written for another meter, or on a grid that neither divides the figure's nor is divided by it, is left out."""
    grid = sum(lasts(note) for note in bars[0])
    fitting = [variation for variation in player.get(VARIES, []) if ending_fits(variation=variation, grid=grid, meter=meter)]
    if not fitting or phrase_bars % len(bars):
        return [[dict(note) for note in bar] for bar in bars]
    finest = max([grid] + [variation[GRID] for variation in fitting])
    fitting = [variation for variation in fitting if finest % variation[GRID] == 0]
    phrase = [stretched(notes=bars[count % len(bars)], by=finest // grid) for count in range(phrase_bars)]
    for variation in fitting:
        ends = stretched(notes=variation[ENDS], by=finest // variation[GRID])
        for bar in variation[BARS]:
            phrase[bar - 1] = with_ending(bar=phrase[bar - 1], ends=ends)
    return phrase


def figure_part(*, entry, role, meter, player, phrase_bars):
    """A value's figure as a tune's part, as a player plays it; the figure's bars are its lines."""
    lines = decorated_figure(bars=entry[FIGURE], player=player, phrase_bars=phrase_bars, meter=meter)
    grid = sum(lasts(note) for note in lines[0])
    return {STEP: step_of(meter=meter, grid=grid), OCTAVE: role[OCTAVE], **voice_of(role), LINES: lines}


def held_part(*, role, meter, chord):
    """One bar of the home note or chord, held."""
    note = {DEGREE: 1, STEPS: int(bar_length(meter) * EIGHTHS_IN_WHOLE)}
    if chord:
        note[CHORD] = HELD_CHORD
    return {STEP: EIGHTH, OCTAVE: role[OCTAVE], **voice_of(role), LINES: [[note]]}


def tune_part(*, lines, role, meter, grid):
    return {STEP: step_of(meter=meter, grid=grid), OCTAVE: role[OCTAVE], **voice_of(role), LINES: lines}


def habits_of(*, habits, player):
    """A style's melody habits as a player keeps them: a wider or narrower range, and the busier rhythms for a busy player."""
    kept = {**habits, **({SPAN: player[SPAN]} if SPAN in player else {})}
    if player.get(BUSY):
        kept[RHYTHMS] = habits[ANSWER_RHYTHMS]
    return kept


def way_beside(*, beside, role, place, tune, section):
    """What the player beside the tune does in the section at a place of the form, or None for any other player, for a section nobody has
    the tune in, and for a section whose own plan already has the player answer every line, which is played as the plan writes it."""
    if role[ROLE] != beside.get(ROLE) or tune is None or tune is role:
        return None
    way = beside[BESIDE_WAYS][place]
    if way not in WAYS_BESIDE:
        raise ValueError(ERR_NO_SUCH_WAY_BESIDE.format(way))
    if way == ANSWERS_EVERY_LINE and role[ROLE] in section[PLAYS] and any(entry.get(ANSWER) for entry in section.get(PLAN, [])):
        return None
    return way


def line_letters(*, plans, answers):
    """The letters of the lines a lead plays through a song, or of those an answering instrument plays, each once, in the
    order the song first plays them."""
    letters = []
    for plan in plans:
        for entry in plan:
            if bool(entry.get(ANSWER)) == answers and LINE in entry and entry[LINE] not in letters:
                letters.append(entry[LINE])
    return letters


def band_said(*, style, song, roles):
    """Who plays, for the notes: each instrument's player by name, with what the style says of the player."""
    said = []
    for instrument, complexity in song.get(PLAYERS, {}).items():
        if any(role.get(PLAYER) == instrument for role in roles):
            level = level_of(character_of(complexity))
            if level is None:
                # A player whose gauges were set one by one is nobody's preset, and is named by the instrument alone.
                said.append(MSG_PLAYED_BY_OWN.format(instrument))
                continue
            player = player_of(style=style, instrument=instrument, character=character_of(level))
            said.append(MSG_PLAYED_BY.format(instrument, player_name(instrument=instrument, complexity=level), player.get(SAYS, '')).strip())
    return said


def sound_of(*, style, song, role, usual):
    """The name of the sound a player plays with: the song's own choice for the player, a General MIDI number, called by the
    style's name for that number where the style has one and by General MIDI's otherwise; or the sound the way of playing has."""
    number = song.get(ROLE_SOUNDS, {}).get(role)
    if number is None:
        return usual
    named = [name for name, of_style in style[SOUNDS].items() if of_style == number]
    if usual in named:
        return usual
    return named[0] if named else MSG_GM_SOUNDS[number - MIN_GM_SOUND].lower()


def section_of(*, name, style, song):
    """A section as the song describes it over what the style says of a section of its name."""
    of_song = song.get(SECTIONS, {}).get(name, {})
    kind = of_song.get(KIND, name)
    if kind not in style[SECTIONS] and not of_song:
        raise ValueError(ERR_NO_SUCH_SECTION.format(name))
    return {**style[SECTIONS].get(kind, {}), **of_song, KIND: kind}


def tempo_of(*, style, song, picks):
    return song.get(TEMPO, picks.get(TEMPO, style[TRAITS][TEMPO][USUAL]))


def forms_of(*, style, song):
    """The forms a style suggests for the song's kind, each with how common it is, or the style's usual ones."""
    forms = style.get(FORMS, {})
    return forms.get(song[TEMPLATE]) or forms.get(USUAL, [])


def seconds_of(*, sections, style, song, meter, tempo):
    """How long a form lasts: its sections' bars at the song's tempo."""
    bars = 0
    for name in sections:
        section = section_of(name=name, style=style, song=song)
        bars += 1 if section.get(HELD) else section[BARS]
    return float(bars * bar_length(meter) * BEATS_IN_A_WHOLE * SECONDS_IN_A_MINUTE / tempo)


def form_of(*, style, song, meter, tempo):
    """The sections a song plays, in order. A song may list them; or name one of the forms its style suggests for its kind;
    or say how long it should last, in seconds, and take the suggested form that comes nearest, a longer form being one written
    with more themes and changes and never the same form repeated; or say nothing and take the commonest."""
    given = song.get(FORM)
    if isinstance(given, list):
        return given
    forms = forms_of(style=style, song=song)
    if given is not None:
        named = [form for form in forms if form[NAME] == given]
        if not named:
            raise ValueError(ERR_NO_STYLE_FORM.format(style[NAME], given, song[TEMPLATE]))
        return named[0][SECTIONS]
    if not forms:
        raise ValueError(ERR_NO_STYLE_FORMS.format(style[NAME]))
    if LENGTH in song:
        return min(forms, key=lambda form: abs(seconds_of(sections=form[SECTIONS], style=style, song=song, meter=meter, tempo=tempo) - song[LENGTH]))[SECTIONS]
    return max(forms, key=share_of)[SECTIONS]


def arranged(*, style, song):
    """A song's picks as a MacroComposer input."""
    style = style_in(style=style, template=song[TEMPLATE], variant=song.get(VARIANT))
    picks = picked(style=style, song=song)
    meter = str(picks.get(METER, COMMON_TIME))
    tempo = tempo_of(style=style, song=song, picks=picks)
    form_names = form_of(style=style, song=song, meter=meter, tempo=tempo)
    lift = 1 if song[KEY][ROOT] in LOW_ROOTS else 0
    roles = [loud_role(role={**role, OCTAVE: role[OCTAVE] + lift} if OCTAVE in role else role, song=song) for role in style[ROLES]]
    style = loud_style(style=style, song=song, roles=roles)
    phrase_bars = style.get(PHRASE_BARS, DEFAULT_PHRASE_BARS)
    chord_trait = style.get(CHORD_TRAIT_FIELD, CHORD_TRAIT)
    chord_entry = values_of(style=style, trait=chord_trait)[picks[chord_trait]]
    scale_type = song[KEY].get(TYPE, chord_entry.get(SCALE_TYPE, MAJOR))
    scale = SCALE_NAME.format(song[KEY][ROOT], scale_type.capitalize())
    habits = style[MELODY] if GRID in style[MELODY] else style[MELODY][meter]
    # A tune in a scale type the style gives notes of its own, a minor song its minor notes and home, takes those: the major
    # notes read in a minor scale rest on the scale's third and sound like the major key beside it.
    habits = {**habits, **habits.get(BY_SCALE_TYPE, {}).get(scale_type, {})}
    if song.get(PLAN_OF_SONG) not in (None, False):
        # A song that asks for a plan has a section made for each place of its form, each saying what the plan worked out.
        def chords_of(section):
            return [chord_of(chord) for chord in section.get(CHORDS) or chord_entry.get(BY_SECTION, {}).get(section[KIND]) or chord_entry[PATTERN]]
        song = SongPlan(style=style, song=song, form_names=form_names, tempo=tempo, scale_type=scale_type, chords_of=chords_of).planned()
        form_names = song[FORM]
    levels = song.get(PLAYERS, {})
    without = song.get(WITHOUT, [])
    no_drums = any(role.get(DRUMS) and role[ROLE] in without for role in roles)
    pieces_off = song.get(WITHOUT_PIECES, [])
    played = pieces_played(song)
    playing = players_in(style=style, roles=roles, levels=levels, section={})
    drummer = next((playing[role[ROLE]] for role in roles if role.get(DRUMS)), {})
    drum_traits = [trait for role in roles for trait in role.get(DRUMS, [])] + [FILLS]
    # The song's riff, where it has one: the song's own, or the one its kind of music is built on, how many eighths a bar of
    # it lasts, its notes and its bars.
    riff = song.get(RIFF, style.get(RIFF)) or {}
    riff_eighths = int(bar_length(meter) * EIGHTHS_IN_WHOLE)
    riff_notes = riff_line_of(riff=riff, seed=song.get(SEED, 0), eighths=riff_eighths, flattened=flattened_in(scale_type)) if riff.get(RIFF_ROLES) else []
    riff_count = riff_bars_of(line=riff_notes, eighths=riff_eighths) or 1
    riff_split = split_bars(line=riff_notes, eighths=riff_eighths)
    riff_players = [role[ROLE] for role in roles if role[ROLE] in riff.get(RIFF_ROLES, []) and role[ROLE] not in without and not role.get(DRUMS)
                    and FIGURE in values_of(style=style, trait=role[TRAIT]).get(picks.get(role[TRAIT]), {})] if riff_notes else []

    def chords_in(section, *, shared=False):
        """A section's chords, its last bar set up for what follows where the section says so."""
        bars = 1 if section.get(HELD) else section[BARS]
        written = section.get(CHORDS) or chord_entry.get(BY_SECTION, {}).get(section[KIND]) or chord_entry[PATTERN]
        # A bar of two chords is kept as its two for the progression, and is its first chord for whatever goes bar by bar.
        chords = [[chord_of(half) for half in chord] if shared and shares_a_bar(chord) else chord_of(chord) for chord in written]
        if section.get(LAST_CHORD) is not None and not section.get(EVERY, chord_entry.get(EVERY)) and len(chords) <= bars:
            # The section's last bar is set up for what follows: the chords are written out a bar each, and the last bar takes the approach chord.
            chords = [chords[bar % len(chords)] for bar in range(bars - 1)] + [chord_of(section[LAST_CHORD])]
        return chords

    def riff_bars_in(section):
        """Which bar of the riff each bar of a section plays, None where a riff that stays at home gives way to a held chord; nothing
        where the section has no riff."""
        if not riff_players or section.get(HELD) or section[KIND] not in riff.get(RIFF_KINDS, []) or section[BARS] % riff_count:
            return []
        stays = riff.get(RIFF_WITH_CHORDS) == STAYS_HOME and riff_split is not None and not section.get(EVERY, chord_entry.get(EVERY))
        return bars_played(chords=chords_in(section), bars=section[BARS], count=riff_count, stays=stays)
    parts = {}
    drum_sets = {}
    usual_drummer = label_of(character_of(levels[DRUMS])) if DRUMS in levels else None
    drums_of = {}
    for name in form_names:
        section = section_of(name=name, style=style, song=song)
        if no_drums or section.get(HELD) or DRUMS not in section[PLAYS] or name in drums_of:
            continue
        character = character_in(levels=levels, instrument=DRUMS, section=section)
        level = None if character is None else label_of(character)
        changed = {trait: value for trait, value in section.get(PICKS, {}).items()
                   if trait in drum_traits and fits(entry=values_of(style=style, trait=trait)[value], picks=picks)}
        plays = player_of(style=style, instrument=DRUMS, character=character)
        if FILLS_COME in song:
            # The song says how often a fill comes, whatever the drummer would do: never, at the end of each section, or every so many bars.
            plays = {**plays, FILL_EVERY: section[BARS] if song[FILLS_COME] == EACH_SECTION else song[FILLS_COME]}
        # A drum solo is written in four; in another meter the drummer plays the section alone as any other.
        drum_solo_here = bool(section.get(DRUM_SOLO)) and meter == COMMON_TIME
        leaves = section.get(LEAVES)
        key = (level, tuple(sorted(changed.items())), math.gcd(plays.get(FILL_EVERY, phrase_bars) or phrase_bars, section[BARS]))
        if leaves is not None:
            key = key + (section[BARS], frozen(leaves), section.get(FILL_INSIDE), section.get(FILL_INSIDE_EVERY), frozen(section.get(MARKER)), section.get(MARKER_EVERY))
        if drum_solo_here:
            key = (DRUM_SOLO, section[BARS])
        # Under a riff of chords on its accents the kick strikes each accent, bar by bar.
        riff_here = riff_bars_in(section) if riff.get(RIFF_NOTES) == ACCENT_CHORDS and not drum_solo_here else []
        kick_bars = accent_bars(line=riff_notes, eighths=riff_eighths)
        over = {KICK: [None if bar is None else kick_bars[bar] for bar in riff_here]} if any(bar is not None for bar in riff_here) else None
        if over:
            key = key + (RIFF, section[BARS], tuple(riff_here))
        if key not in drum_sets:
            if drum_solo_here:
                made = solo_parts(style=style, bars=section[BARS], seed=song.get(SEED, 0), kit=played)
            else:
                made = drum_parts(style=style, picks={**picks, **changed}, roles=roles, meter=meter, phrase_bars=phrase_bars, drummer=plays, section_bars=section[BARS], own_fill=FILLS in song.get(PICKS, {}), seed=song.get(SEED, 0), kit=played,
                                  leaves=leaves, inside={FILL_INSIDE: section.get(FILL_INSIDE), FILL_INSIDE_EVERY: section.get(FILL_INSIDE_EVERY), MARKER: section.get(MARKER), MARKER_EVERY: section.get(MARKER_EVERY)}, over=over)
            drum_sets[key] = {}
            for piece, part in made.items():
                # A piece of the kit switched off is left out: its strokes are never moved to another piece.
                if piece in pieces_off:
                    continue
                if piece == SNARE and not song.get(QUIET_NOTES, True):
                    # The quiet notes switched off: the snare's soft strokes and ghost notes between the main ones are left out.
                    part = {**part, HITS: [NONE if hit in (SOFT, GHOST) else hit for hit in part[HITS]]}
                profile = style.get(BEAT_LOUDNESS)
                is_uneven = plays.get(UNEVEN) and not drum_solo_here
                if (profile and not drum_solo_here) or is_uneven:
                    # A pattern written out, where each stroke's loudness is its own: the style's lean on each beat, then a person's unevenness on top.
                    pattern = drum_pattern(part)
                    if profile and not drum_solo_here:
                        pattern = leaning(pattern=pattern, profile=profile, meter=meter, dynamics=song.get(DYNAMICS, {}).get(drummer_role(roles), USUAL_DYNAMICS))
                    if is_uneven:
                        pattern = uneven(pattern=pattern, by=plays[UNEVEN], dice=random.Random(DRUM_SEED.format(song.get(SEED, 0), piece, section[KIND])))
                    part = {RAW: pattern}
                named = piece if leaves is None and not over and key[:2] == (usual_drummer, ()) and piece not in parts else MSG_PART_OF_SECTION.format(piece, name if leaves is not None or over else section[KIND])
                parts[named] = part
                drum_sets[key][piece] = named
        drums_of[name] = drum_sets[key]
    drum_tracks = list(dict.fromkeys(piece for pieces in drums_of.values() for piece in pieces))
    timing = {piece: timing_generators(move=drummer.get(TIMING, {}).get(piece, {})) for piece in drum_tracks}
    # The order of a made song's tracks: the muted chords track first, then the chords, the lead and the backing, the bass, and the drums last.
    tracks = {MSG_CHORDS_TRACK: MSG_CHORDS_INSTRUMENT}
    instruments = {DRUM_KIT: None, MSG_CHORDS_INSTRUMENT: CHORDS_GUIDE_SOUND}
    progressions = {}
    chains = {}
    extra = {}
    shaped = []
    pitched = []
    for role in roles:
        if role.get(DRUMS) or role[ROLE] in without:
            continue
        entry = values_of(style=style, trait=role[TRAIT])[picks[role[TRAIT]]]
        if SOUND not in entry:
            continue
        sound = sound_of(style=style, song=song, role=role[ROLE], usual=entry[SOUND])
        instruments[sound] = style[SOUNDS].get(sound, song.get(ROLE_SOUNDS, {}).get(role[ROLE]))
        tracks[role[ROLE]] = sound
        pitched.append((role, entry))
        if FIGURE in entry:
            parts[role[ROLE]] = figure_part(entry=entry, role=role, meter=meter, player=playing[role[ROLE]], phrase_bars=phrase_bars)
            shaped.append(role[ROLE])
        parts[MSG_PART_OF_SECTION.format(role[ROLE], HELD)] = held_part(role=role, meter=meter, chord=any(CHORD in note for bar in entry.get(FIGURE, []) for note in bar))
        timing[role[ROLE]] = timing_generators(move=playing[role[ROLE]].get(TIMING, {}))
        for generator in entry.get(GENERATORS, []):
            for kind, settings in generator.items():
                extra.setdefault(SECTION_OF_KIND[kind], {})[role[ROLE]] = dict(settings)
        if role[ROLE] in extra.get(GUITARIFIES, {}):
            extra[GUITARIFIES][role[ROLE]].update(playing[role[ROLE]].get(GUITARIFY_OF_PLAYER, {}))
    for track, moves in timing.items():
        chains[MSG_TIMING_CHAIN.format(track)] = [{RUSH: track}, {DRAG: track}]
        extra.setdefault(RUSHES, {})[track] = moves[RUSH]
        extra.setdefault(DRAGS, {})[track] = moves[DRAG]
    tracks.update({piece: DRUM_KIT for piece in drum_tracks})
    form = []
    notes = []
    met = {}
    same_tunes = {}
    # The scales of sections in a key or a scale of their own, by name.
    more_scales = {}
    plans = [section_of(name=name, style=style, song=song).get(PLAN, []) for name in form_names]
    # A song has a hook where the song or its style asks for one and a section of its form marks a line as one.
    has_a_hook = bool(song.get(HOOK, style.get(HOOK, False))) and any(has_hook(plan) for plan in plans)
    beside = song.get(BESIDE, {})
    under = UnderLead(busy=beside.get(BESIDE_BUSY, USUAL_BESIDE_BUSY), habits=habits, grid=habits[GRID], scale_type=scale_type, seed=song.get(SEED, 0))
    for count, name in enumerate(form_names, start=1):
        section = section_of(name=name, style=style, song=song)
        met[name] = met.get(name, 0) + 1
        scene_name = name if met[name] == 1 else MSG_REPEATED_SCENE.format(name, met[name])
        bars = 1 if section.get(HELD) else section[BARS]
        chords = chords_in(section)
        play = {}
        if section.get(HELD):
            held = MSG_PART_OF_SECTION.format(CRASH, HELD)
            if not no_drums and CRASH not in pieces_off:
                parts[held] = one_hit(style=style, meter=meter, drum=CRASH, played=played)
            if not no_drums and KICK not in pieces_off:
                parts[MSG_PART_OF_SECTION.format(KICK, HELD)] = one_hit(style=style, meter=meter, drum=KICK, played=played)
            if not no_drums and CRASH not in pieces_off:
                if CRASH not in tracks:
                    tracks[CRASH] = DRUM_KIT
                    drum_tracks.append(CRASH)
                play[CRASH] = held
            if KICK in tracks:
                play[KICK] = {PART: MSG_PART_OF_SECTION.format(KICK, HELD), ONCE: True}
            for role, entry in pitched:
                if FIGURE in entry and role[ROLE] in section.get(PLAYS, [role[ROLE]]):
                    play[role[ROLE]] = {PART: MSG_PART_OF_SECTION.format(role[ROLE], HELD), ONCE: True}
        else:
            for piece, part in drums_of.get(name, {}).items():
                play[piece] = {PART: part, CHAINS: [MSG_TIMING_CHAIN.format(piece)]}
            if section.get(CRASH_START) and name in drums_of and CRASH not in pieces_off:
                start = MSG_SECTION_START_PART.format(CRASH)
                parts[start] = one_hit(style=style, meter=meter, drum=CRASH, played=played)
                if CRASH not in tracks:
                    tracks[CRASH] = DRUM_KIT
                    drum_tracks.append(CRASH)
                play.setdefault(CRASH, {PART: start, ONCE: True})
            here = players_in(style=style, roles=roles, levels=levels, section=section)
            progression = MSG_PART_OF_SECTION.format(name, CHORDS)
            # The section's chords go on the chords track, written a step a chord, which every clip that plays them follows.
            section_progression = progression_of(chords=chords_in(section, shared=True), every=section.get(EVERY, chord_entry.get(EVERY)), meter=meter)
            own_scale = (section.get(SCENE_SETTINGS) or {}).get(SCALE)
            written_chords = chords_written(progression=section_progression, meter=meter, scale_type=own_scale[TYPE] if isinstance(own_scale, dict) else scale_type)
            if written_chords is None:
                progressions[progression] = section_progression
                chains[progression] = [{PROGRESSION: progression}]
                parts[progression] = {RAW: one_chord(meter)}
                chords_played = {PART: progression, CHAINS: [progression]}
            else:
                parts[progression] = {RAW: written_chords}
                chords_played = progression

            def lines_of(role, *, section=section, chords=chords, here=here):
                """The lines a player of a tune plays in the section: those the section gives, or those sketched for the player."""
                given = section.get(LINES_GIVEN, {}).get(role[ROLE])
                return given or sketched(habits={**habits_of(habits=habits, player=here[role[ROLE]]), **role.get(HABITS, {}), **song.get(ROLE_HABITS, {}).get(role[ROLE], {}), **song.get(MELODY, {})}, plan=section[PLAN], chords=chords, scale_type=scale_type, seed=song.get(SEED, 0),
                                         answers=bool(role.get(ANSWERS)), engine=song.get(MELODY_ENGINE, role.get(ENGINE)), voice=role.get(VOICE), letters=line_letters(plans=plans, answers=bool(role.get(ANSWERS))),
                                         hook=has_a_hook, hook_take=song.get(HOOK_TAKE, FIRST_HOOK_TAKE))
            # The player who has the tune in the section, if any: a player of lines who answers nobody.
            tune_role = next((other for other, other_entry in pitched if FIGURE not in other_entry and not other.get(ANSWERS) and other[ROLE] in section[PLAYS]), None)
            for role, entry in pitched:
                way = way_beside(beside=beside, role=role, place=count - 1, tune=tune_role, section=section)
                if way == WAITS or (way is None and role[ROLE] not in section[PLAYS]):
                    continue
                if way is not None:
                    # Fills and answers are drawn anew each time a section returns; the hook and a riff are the same every time.
                    drawn_in = scene_name if way in WAYS_DRAWN_ANEW else section.get(DRAWN_AS, name)
                    part = MSG_PART_BESIDE.format(drawn_in, role[ROLE], way)
                    if part not in parts:
                        lines = under.lines(way=way, tune=lines_of(tune_role), chords=chords, section=drawn_in)
                        if not all(all(REST in note for note in line) for line in lines):
                            parts[part] = tune_part(lines=lines, role=role, meter=meter, grid=habits[GRID])
                            shaped.append(part)
                    if part in parts:
                        play[role[ROLE]] = {PART: part, ONCE: True, CHAINS: [MSG_TIMING_CHAIN.format(role[ROLE])]}
                    continue
                if FIGURE in entry:
                    chain = MSG_PART_OF_SECTION.format(name, role[ROLE])
                    chains[chain] = [dict(FOLLOWS_THE_CHORDS)] + [{kind: role[ROLE]} for generator in entry.get(GENERATORS, []) for kind in generator]
                    if role.get(VOICE_LEADING):
                        chains[chain].append({VOICE_LEADING_KIND: NEAR})
                    chains[chain] += [{RUSH: role[ROLE]}, {DRAG: role[ROLE]}]
                    figure = role[ROLE]
                    entry_here = entry
                    if FIGURE in entry.get(BY_SECTION, {}).get(section[KIND], {}):
                        # The value's own figure for this kind of section, a part of its own, in place of the figure played elsewhere.
                        entry_here = {**entry, FIGURE: entry[BY_SECTION][section[KIND]][FIGURE]}
                        figure = MSG_PART_OF_SECTION.format(role[ROLE], section[KIND])
                        if figure not in parts:
                            parts[figure] = figure_part(entry=entry_here, role=role, meter=meter, player=playing[role[ROLE]], phrase_bars=phrase_bars)
                            shaped.append(figure)
                    if here[role[ROLE]] != playing[role[ROLE]]:
                        held_back = figure_part(entry=entry_here, role=role, meter=meter, player=here[role[ROLE]], phrase_bars=phrase_bars)
                        # A player held back who plays the figure no differently plays the one part, so that no part is written twice.
                        if held_back != parts[figure]:
                            figure = MSG_PART_AT_LEVEL.format(figure, label_of(character_in(levels=levels, instrument=role.get(PLAYER), section=section)))
                            if figure not in parts:
                                parts[figure] = held_back
                                shaped.append(figure)
                    riff_here = riff_bars_in(section) if role[ROLE] in riff_players else []
                    if riff_here:
                        # The song's riff takes the place of the player's figure here: moved by the chords and played as written, with none of the figure's
                        # own generators. Its first player plays its chords, and a player under the first its notes alone.
                        first = role[ROLE] == riff_players[0]
                        riff_part = MSG_PART_OF_SECTION.format(role[ROLE], RIFF)
                        if None in riff_here:
                            # A riff that stays at home is written out for the whole section: the riff over the home chord, and every other chord held.
                            riff_part = MSG_PART_OF_SECTION.format(name, riff_part)
                        if riff_part not in parts:
                            lines = [riff_notes] if None not in riff_here else [held_bar(eighths=riff_eighths, chord=first) if bar is None else riff_split[bar] for bar in riff_here]
                            parts[riff_part] = {STEP: EIGHTH, OCTAVE: role[OCTAVE], **voice_of(role), LINES: [[dict(note) for note in (line if first else single(line))] for line in lines]}
                            shaped.append(riff_part)
                        riff_chain = MSG_PART_OF_SECTION.format(chain, RIFF)
                        chains[riff_chain] = [dict(FOLLOWS_THE_CHORDS), {RUSH: role[ROLE]}, {DRAG: role[ROLE]}]
                        play[role[ROLE]] = {PART: riff_part, CHAINS: [riff_chain]}
                        continue
                    leaves = section.get(LEAVES) or {}
                    if leaves.get(TAIL) in (DROP_OUT, STOPS):
                        # The band's last bar together: the figure is written out for the whole section, so that its last bar alone differs.
                        whole_part = MSG_PART_OF_SECTION.format(name, MSG_PART_OF_SECTION.format(role[ROLE], leaves[TAIL]))
                        parts[whole_part] = {**parts[figure], LINES: with_tail(bars=parts[figure][LINES], count=bars, tail=leaves[TAIL], eighths=leaves.get(TAIL_EIGHTHS, 0))}
                        shaped.append(whole_part)
                        figure = whole_part
                    play[role[ROLE]] = {PART: figure, CHAINS: [chain]}
                    continue
                part = MSG_PART_OF_SECTION.format(name, role[ROLE])
                if part not in parts:
                    lines = lines_of(role)
                    if all(all(REST in note for note in line) for line in lines):
                        continue
                    written = tune_part(lines=lines, role=role, meter=meter, grid=habits[GRID])
                    # A tune that returns note for note, as a chorus's, is the one part each time, where the song's sections are planned.
                    same = same_tunes.get((role[ROLE], repr(written))) if DRAWN_AS in section else None
                    if same is not None:
                        part = same
                    else:
                        parts[part] = written
                        shaped.append(part)
                        same_tunes[(role[ROLE], repr(written))] = part
                if part in parts:
                    play[role[ROLE]] = {PART: part, ONCE: True, CHAINS: [MSG_TIMING_CHAIN.format(role[ROLE])]}
        if not play:
            # Nothing of the song's picks plays in this section, as pads alone where the song has no chord part: it is left out.
            met[name] -= 1
            continue
        if not section.get(HELD):
            # A section that only holds a chord has it written out in its parts, and nothing there follows the chords track.
            play[MSG_CHORDS_TRACK] = chords_played
        scene_settings = dict(section.get(SCENE_SETTINGS) or {})
        if section[KIND] in SECTION_KINDS:
            # A scene says what kind of section it is, where the kind is one a scene may be.
            scene_settings.setdefault(SECTION_OF_SCENE, section[KIND])
        if isinstance(scene_settings.get(SCALE), dict):
            # A section in a key or a scale of its own: the scale is named as the song's is and added to the set's.
            own_scale = scene_settings[SCALE]
            scene_settings[SCALE] = SCALE_NAME.format(own_scale[ROOT], own_scale[TYPE].capitalize())
            more_scales[scene_settings[SCALE]] = {ROOT: own_scale[ROOT], TYPE: own_scale[TYPE]}
        form.append({SCENE: scene_name, BARS: bars, PLAY: play, **({SETTINGS_OF_SCENE: scene_settings} if scene_settings else {})})
        said_of_scene = MSG_MADE_SCENE.format(count, scene_name, bars)
        notes.append(MADE_SCENE_SAID.format(said_of_scene, section[SAID_OF_SECTION]) if section.get(SAID_OF_SECTION) else said_of_scene)
    generators = {Section.FOLLOW_CHORDS: {MSG_FOLLOW_CHORDS_NAME: {FollowChordsSetting.CHORDS_FROM: MSG_CHORDS_TRACK}}, **extra}
    if progressions:
        generators[PROGRESSIONS] = progressions
    if any(role.get(VOICE_LEADING) for role, _ in pitched):
        generators[VOICE_LEADINGS] = {NEAR: dict(NEAR_VOICES)}
    said = '\n'.join(band_said(style=style, song=song, roles=roles) + [MSG_MADE_PICK.format(trait, value) for trait, value in picks.items()])
    # A piece of the kit that sounds as a General MIDI sound is a track with an instrument of its own, and no drum track.
    own_sounds = {piece: sounds_as[PLAYED_SOUND] for piece, sounds_as in song.get(PIECE_SOUNDS, {}).items() if PLAYED_SOUND in sounds_as and piece in tracks}
    for piece, sound in own_sounds.items():
        instruments[MSG_PIECE_INSTRUMENT.format(piece)] = sound
        tracks[piece] = MSG_PIECE_INSTRUMENT.format(piece)
    given = {
        NAME: song[NAME], TITLE: song[TITLE], DESCRIPTION: song.get(DESCRIPTION, song[TITLE]), GENRE: style[GENRE], SUBGENRE: song[TEMPLATE], VARIANT: song.get(VARIANT),
        NOTES: MSG_MADE_SONG_NOTES.format(title=song[TITLE], style=style[TITLE], template=song[TEMPLATE], picks=said, form='\n'.join(notes)),
        SCALES: {scale: {ROOT: song[KEY][ROOT], TYPE: scale_type}, **more_scales}, SCALE: scale, TEMPO: tempo,
        FEEL: style[FEEL], SHAPED: shaped, INSTRUMENTS: instruments, TRACKS: tracks, DRUM_TRACKS: [piece for piece in drum_tracks if piece not in own_sounds], MUTED_TRACKS: [MSG_CHORDS_TRACK], GENERATORS: generators, CHAINS: chains,
        PARTS: parts, FORM: form,
    }
    groove = song.get(GROOVE, style.get(GROOVE))
    if groove and groove != NO_GROOVE:
        given[GROOVE] = groove
    if song.get(DYNAMICS):
        # How far the feel moves each track's notes: a player's own track, and for the drummer every piece of the kit.
        of_tracks = {role[ROLE]: song[DYNAMICS][role[ROLE]] for role in roles if role[ROLE] in song[DYNAMICS] and role[ROLE] in tracks}
        if drummer_role(roles) in song[DYNAMICS]:
            of_tracks.update({piece: song[DYNAMICS][drummer_role(roles)] for piece in drum_tracks})
        given[DYNAMICS] = of_tracks
    if meter != COMMON_TIME:
        given[TIME_SIGNATURE] = meter
    return given
