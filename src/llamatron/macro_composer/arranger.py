# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The arranger: a song's picks and a style template made into a MacroComposer input, a whole song.

A style template lists a style's traits, each with its values and how common each is; a value of a trait a band plays holds
the bar it plays: a drum's hits, or a figure of notes written over chord one, which a Progression moves through the song's
chords. A song's picks say which template of the style it starts from, the picks it changes, its key, its tempo, its
sections with their chords and its form. The arranger decides nothing but the tune, and that only where the song gives none:
it then sketches one by rule from the style's melody habits and the song's seed (melody.py). What it writes is an input the
MacroComposer composes, so every choice can be read and changed there.
"""

import copy
from fractions import Fraction
import functools
import math
import os
import random
import zlib

from llamatron.composition import file_format, limits
from llamatron.composition.checks import in_whole_notes
from llamatron.composition.file_format import ChordSymbol, GeneratorKind, PatternSetting, Row, SceneSetting, Section, VelocitySetting
from llamatron.composition.generator_settings import FollowChordsSetting
from llamatron.composition.named_scale import scale_type_called
from llamatron.macro_composer import band, breaks, characters, drum_solo, interplay, joins, loudness, melody, notation, riffs as riffs_values, shaping, song_plan
from llamatron.macro_composer.breaks import cut_up
from llamatron.macro_composer.characters import character_of, held_to, label_of, level_of
from llamatron.macro_composer.interplay import UnderLead
from llamatron.macro_composer.joins import drum_tail, pieces_of_tail, with_tail
from llamatron.macro_composer.loudness import drum_levels, in_proportion, note_levels, scaled, spread, with_own
from llamatron.macro_composer.melody import has_hook, plan_as_asked, plan_with_hook_placed, plan_with_tag, sketched
from llamatron.macro_composer.notation import clamped, drum_rows
from llamatron.macro_composer.players import player_name
from llamatron.macro_composer.riffs import accent_bars, bars_of as riff_bars_of, bars_played, flattened_in, held_bar, line_of as riff_line_of, single, split_bars
from llamatron.macro_composer.shaping import is_compound
from llamatron.macro_composer.song_plan import SongPlan
from llamatron.support.safe_yaml import load_safely
from llamatron.user_strings import errors, labels, macro_composer as composer_text

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
# A line of a tag lasts so many bars, as a line of any melody does.
BARS_IN_A_TAG_LINE = 2
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
ACCIDENTAL_MARKS = {notation.SHARP: '#', notation.FLAT: 'b'}
# The chords track: its chords as the pattern editor's Chord row names them, and what a clip that follows it has first in its chain.
SCALE_TRIAD = 3
HOME_DEGREE = 1
NOTES_OF_A_SCALE_WITH_TRIADS = 7
THIRD_PLACE = 2
FIFTH_PLACE = 4
HOME_CHORDS = {(4, 7): ChordSymbol.MAJOR, (3, 7): ChordSymbol.MINOR, (3, 6): ChordSymbol.DIMINISHED, (4, 8): ChordSymbol.AUGMENTED}
FOLLOWS_THE_CHORDS = {GeneratorKind.FOLLOW_CHORDS: composer_text.MSG_FOLLOW_CHORDS_NAME}
# How the tune is delivered, where a song says: the settings of the one Phrasing its tune's clips then run.
TUNE_PHRASING = 'tune_phrasing'
# The song's own musicians, the settings of a Musician by the player whose clips it plays, in place of the one the player is given.
MUSICIANS = 'musicians'
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
# A song's tunes written by hand, each a pattern's data under its kind of section, which take the place of the tune that would be written.
OWN_TUNES = 'own_tunes'
# An intro's melody written by hand, a pattern's data under the name of the player who plays it, which takes the place of the
# hook that player would say in the intro.
OWN_INTRO = 'own_intro'
INTRO_KIND = 'intro'
# A song's solos written by hand: under each solo's number among the song's solos, counted from 1, a pattern's data under the
# name of the player who plays it, which takes the place of the solo that would be written.
OWN_SOLOS = 'own_solos'
# The notes written by hand for one part of an intro, by the part's number among the form's intros, from 1, and the player's name.
OWN_INTROS = 'own_intros'
SOLO_KIND = 'solo'
# The riffs a song has besides its first, in order: each a riff as the first is, with a name of its own, which its players play in
# its kinds of section in place of their usual parts; and the seed a riff of a name is written from.
MORE_RIFFS = 'more_riffs'
# A riff's notes written by hand: a pattern's data as its first player plays it, which its other players play in their own octaves.
RIFF_OWN = 'own'
MORE_RIFF_SEED = '{seed} riff {name}'
# The player a riff was written for, who plays its chords and in whose octave its notes are written, where that is not the first
# of the players who play it; and the name a riff's notes are drawn by, where that is not the riff's name, so that a riff
# renamed or copied keeps its notes.
RIFF_FOR = 'for'
RIFF_DRAWN_AS = 'drawn_as'
# Who plays the tune: a player's name for each kind of section, and one for the whole song, the player the genre gives the tune
# where neither says; NOBODY for a kind of section that has no tune.
TUNE_BY = 'tune_by'
TUNE_BY_SONG = 'tune_by_song'
NOBODY = 'nobody'
# A song's tunes of another take, each a pattern's data by its kind of section: the wizard's own, drawn again for that kind alone.
TAKEN_TUNES = 'taken_tunes'
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
        raise ValueError(errors.ERR_NO_STYLE_KIND.format(style[NAME], song[TEMPLATE], listed(templates)))
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
            raise ValueError(errors.ERR_NO_TRAIT_VALUE.format(trait, picks[trait], listed(values)))
    for trait, value in picks.items():
        for needed, wanted in values_of(style=style, trait=trait).get(value, {}).get(NEEDS, {}).items():
            if picks.get(needed) != wanted:
                raise ValueError(errors.ERR_PICK_NEEDS.format(trait, value, needed, wanted, picks.get(needed)))
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
    return drum_rows(drum=part[notation.DRUM], hits=part[notation.HITS], loud=part[notation.LOUD], soft=part[notation.SOFT], step_size=part[notation.STEP], accent=part.get(notation.ACCENT), ghost=part.get(notation.GHOST))


def uneven(*, pattern, by, dice):
    """A drum's pattern with hits that each differ a little in loudness, as a person's do."""
    return {**pattern, notation.VELOCITY: [None if loud is None else clamped(loud + dice.randint(-by, by)) for loud in pattern[notation.VELOCITY]]}


def leaning(*, pattern, profile, meter, dynamics):
    """A drum's pattern with the strokes on each beat louder or softer by the style's lean on that beat, as far as the drummer's dynamics say."""
    size = Fraction(pattern[notation.STEP_SIZE])
    beat = shaping.COMPOUND_BEAT if is_compound(meter) else shaping.SIMPLE_BEAT
    velocities = []
    for place, loud in enumerate(pattern[notation.VELOCITY]):
        count = ((place * size) % bar_length(meter)) / beat
        on_a_beat = loud is not None and count.denominator == 1
        velocities.append(clamped(loud + scaled(move=profile[int(count) % len(profile)], dynamics=dynamics)) if on_a_beat else loud)
    return {**pattern, notation.VELOCITY: velocities}


def drummer_role(roles):
    """The name of the role that plays the drums."""
    return next((role[ROLE] for role in roles if role.get(DRUMS)), DRUMS)


def loud_style(*, style, song, roles):
    """A style with each drum's four levels worked out, as the song has them: the kit's levels where the song gives its own, every
    piece moved in proportion, and each level as far from the normal one as the drummer's dynamics say."""
    drummer = drummer_role(roles)
    kit = drum_levels(style[LOUDNESS][DRUMS])
    chosen = with_own(levels=kit, own=song.get(LOUDNESS, {}).get(drummer))
    dynamics = song.get(DYNAMICS, {}).get(drummer, loudness.USUAL_DYNAMICS)
    return {**style, LOUDNESS: {piece: spread(levels=in_proportion(levels=drum_levels(given), kit=kit, chosen=chosen), dynamics=dynamics)
                                for piece, given in style[LOUDNESS].items()}}


def loud_role(*, role, song):
    """A player of notes as loud as the song has the player: the role with the song's levels and dynamics for it, where it gives any."""
    own = song.get(LOUDNESS, {}).get(role[ROLE])
    dynamics = song.get(DYNAMICS, {}).get(role[ROLE])
    if notation.VELOCITY not in role or (own is None and dynamics is None):
        return role
    levels = spread(levels=with_own(levels=note_levels(role[notation.VELOCITY]), own=own), dynamics=loudness.USUAL_DYNAMICS if dynamics is None else dynamics)
    return {**role, notation.VELOCITY: levels[loudness.NORMAL], LEVELS_OF_ROLE: {level: levels[level] for level in (notation.ACCENT, notation.SOFT, notation.GHOST)}}


def voice_of(role):
    """How loud a player's part is: the velocity, and the player's other levels where the song gives any."""
    return {notation.VELOCITY: role[notation.VELOCITY], **role.get(LEVELS_OF_ROLE, {})}


def struck(*, levels, hits):
    """How loud a drum's part is: its normal and soft strokes, and its accent and ghost note where its hits have any."""
    return {notation.LOUD: levels[loudness.NORMAL], notation.SOFT: levels[notation.SOFT], **{level: levels[level] for level in (notation.ACCENT, notation.GHOST) if level in hits}}


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


@functools.cache
def bar_length(meter):
    return Fraction(meter)


@functools.cache
def step_of(*, meter, grid):
    return str(bar_length(meter) / grid)


def chord_of(entry):
    """A chord as written, as its degree and what else it says; a bar of two chords is its first, for whatever goes bar by bar."""
    if isinstance(entry, list):
        return chord_of(entry[0])
    return entry if isinstance(entry, dict) else {notation.DEGREE: entry}


def shares_a_bar(entry):
    """Whether an entry of a progression is two chords in one bar, each half of it."""
    return isinstance(entry, list)


def halves_of(chords):
    """Chords by the half bar: a bar of two chords as its two, and a bar of one as the one twice."""
    return [half for chord in chords for half in (chord if shares_a_bar(chord) else [chord, chord])]


def fits_by_halves(chords):
    """Whether chords written by the half bar are no more than a Progression holds; a longer run is played a chord a bar, each
    bar's first."""
    return len(chords) * HALVES_OF_A_BAR <= limits.MAX_PROGRESSION_CHORDS


def half_bar_of(meter):
    """Half a bar of a meter, as a time a Progression takes: a length in whole notes."""
    return str(Fraction(meter) / HALVES_OF_A_BAR)


def progression_of(*, chords, every, meter=COMMON_TIME):
    """A list of chords as a Progression's settings; where a bar has two chords and nothing says how long a chord lasts, each
    chord lasts half a bar, so long as a Progression holds that many."""
    if not every and any(shares_a_bar(chord) for chord in chords) and fits_by_halves(chords):
        chords = halves_of(chords)
        every = half_bar_of(meter)
    made = {CHORDS: [chord_of(chord)[notation.DEGREE] for chord in chords]}
    marks = [ACCIDENTAL_MARKS.get(chord_of(chord).get(notation.ACCIDENTAL)) for chord in chords]
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
    if lasts > limits.MAX_STEP_SIZE or (any(marks) and home is None):
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
    return [_level_at(marks=marks, place=place) for place in range(marks[notation.STEPS])]


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
        finer += [hit] + [notation.NONE] * (to // len(hits) - 1)
    return finer


def laid_over(*, bar, more):
    """A bar with a decoration's hits wherever the bar has none."""
    return [added if hit == notation.NONE else hit for hit, added in zip(bar, more)]


def break_of(*, picks, meter):
    """The bar of the break the picks name, a drum's hits for each drum, or None where they name none or the meter is not
    the one a break is written in."""
    name = picks.get(BREAK, NO_BREAK)
    if name == NO_BREAK or meter != COMMON_TIME:
        return None
    if name not in breaks.BREAKS:
        raise ValueError(errors.ERR_NO_SUCH_BREAK.format(name, listed(breaks.BREAKS)))
    return breaks.BREAKS[name]


def cut_of(picks):
    """How far the picks cut their break up."""
    cut = picks.get(BREAK_CUT, breaks.LEAST_CUT)
    if isinstance(cut, bool) or not isinstance(cut, int) or not breaks.LEAST_CUT <= cut <= breaks.MOST_CUT:
        raise ValueError(errors.ERR_BREAK_CUT.format(breaks.LEAST_CUT, breaks.MOST_CUT, cut))
    return cut


def pieces_played(song):
    """What each remapped piece of a song's kit plays, as the drum's name or the note's number drum_rows takes, each checked."""
    played = {}
    for piece, sounds_as in song.get(PIECE_SOUNDS, {}).items():
        if set(sounds_as) == {PLAYED_DRUM} and sounds_as[PLAYED_DRUM] in notation.KIT:
            played[piece] = sounds_as[PLAYED_DRUM]
        elif set(sounds_as) == {PLAYED_SOUND, PLAYED_NOTE} and whole(value=sounds_as[PLAYED_SOUND], low=limits.MIN_GM_SOUND, high=limits.MAX_GM_SOUND) and whole(value=sounds_as[PLAYED_NOTE], low=LOWEST_NOTE, high=HIGHEST_NOTE):
            played[piece] = sounds_as[PLAYED_NOTE]
        else:
            raise ValueError(errors.ERR_PIECE_SOUND.format(piece, sounds_as))
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
    length = math.gcd(drummer.get(characters.FILL_EVERY, phrase_bars) or phrase_bars, section_bars)
    fill_every = length
    if over:
        # Bars given one by one are the whole section's.
        length = section_bars
    fill, silences = choice_that_fits(choices=drummer.get(characters.FILL), picks=picks)
    if not fill or own_fill:
        # The fill the song chose itself is played whatever the drummer would play, a song that chose none having none.
        fill, silences = values_of(style=style, trait=FILLS).get(picks.get(FILLS), {}).get(characters.FILL, {}), []
    if drummer.get(characters.FILL_EVERY) == 0:
        fill, silences = {}, []
    last_fill = {}
    if leaves is not None:
        # A planned section: the fill inside is the small one the section names, and the last bar's is the join's.
        length = section_bars
        fill_every = length
        fill, silences = fill_named(style=style, name=(inside or {}).get(FILL_INSIDE)), []
        last_fill = fill_named(style=style, name=leaves.get(joins.FILL_OF_JOIN))
    tail = (leaves or {}).get(joins.TAIL)
    inside_every = (inside or {}).get(FILL_INSIDE_EVERY) or length
    # A marker is a stroke or two laid over a phrase's last bar where no fill is played.
    marker = ((inside or {}).get(MARKER) or {}) if leaves is not None else {}
    marker_every = (inside or {}).get(MARKER_EVERY) or length
    adds, _ = choice_that_fits(choices=drummer.get(characters.ADDS), picks=picks)
    varied = []
    for variation in drummer.get(characters.VARIES, []):
        more, _ = choice_that_fits(choices=variation[CHOICES], picks=picks)
        varied.append((variation[BARS], more))
    parts = {}
    every = [bars, adds, fill, last_fill, marker, {piece: [notation.NONE] for piece in pieces_of_tail(tail)}] + [more for _, more in varied]
    every += [{piece: given} for piece, given_bars in over.items() for given in given_bars if given is not None]
    for piece in list(dict.fromkeys(piece for layer in every for piece in layer)):
        layers = [layer[piece] for layer in every if piece in layer]
        grid = math.lcm(*(len(layer) for layer in layers))
        plain = widened(hits=bars.get(piece, [notation.NONE]), to=grid)
        if piece in adds:
            plain = laid_over(bar=plain, more=widened(hits=adds[piece], to=grid))
        hits = []
        for bar in range(1, length + 1):
            if leaves is None and bar % fill_every == 0 and piece in fill:
                hits += widened(hits=fill[piece], to=grid)
            elif leaves is None and bar % fill_every == 0 and piece in silences:
                hits += [notation.NONE] * grid
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
                    played = drum_tail(piece=piece, plain=played, tail=tail, eighths=leaves.get(joins.TAIL_EIGHTHS, 0))
                elif leaves is not None and bar == length and piece in last_fill:
                    played = widened(hits=last_fill[piece], to=grid)
                elif leaves is not None and bar != length and bar % inside_every == 0 and piece in fill:
                    played = widened(hits=fill[piece], to=grid)
                elif bar != length and bar % marker_every == 0 and bar % inside_every != 0 and piece in marker:
                    played = laid_over(bar=played, more=widened(hits=marker[piece], to=grid))
                hits += played
        # A style as written says a drum's normal stroke alone, and a song's style all four levels.
        levels = drum_levels(style[LOUDNESS].get(piece, style[LOUDNESS][DRUMS]))
        parts[piece] = {notation.DRUM: (kit or {}).get(piece, piece), notation.STEP: step_of(meter=meter, grid=grid), **struck(levels=levels, hits=hits), notation.HITS: hits}
    return parts


def fill_named(*, style, name):
    """The fill of a name, each drum's hits, or no fill for no name or a name the style lacks."""
    return values_of(style=style, trait=FILLS).get(name, {}).get(characters.FILL, {})


def solo_parts(*, style, bars, seed, kit):
    """A drum solo's parts, a part for each piece of the kit that sounds in it."""
    parts = {}
    for piece, hits in drum_solo.solo_hits(bars=bars, seed=seed).items():
        # A style as written says a drum's normal stroke alone, and a song's style all four levels.
        levels = drum_levels(style[LOUDNESS].get(piece, style[LOUDNESS][DRUMS]))
        parts[piece] = {notation.DRUM: (kit or {}).get(piece, piece), notation.STEP: drum_solo.STEP, **struck(levels=levels, hits=hits), notation.HITS: hits}
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
    loud = style[LOUDNESS].get(drum, style[LOUDNESS][DRUMS])[loudness.NORMAL]
    return {notation.DRUM: played.get(drum, drum), notation.STEP: EIGHTH, notation.LOUD: loud, notation.SOFT: loud, notation.HITS: [notation.LOUD] + [notation.NONE] * (int(bar_length(meter) * EIGHTHS_IN_WHOLE) - 1)}


def lasts(note):
    """How many steps a note or a rest of a figure lasts."""
    return note.get(notation.REST, note.get(notation.STEPS, 0))


def with_ending(*, bar, ends):
    """A figure's bar whose last steps are a decoration's notes: what the bar played before them stays, a note they cut into shortened."""
    room = sum(lasts(note) for note in bar) - sum(lasts(note) for note in ends)
    kept = []
    for note in bar:
        if room <= 0:
            break
        length = min(lasts(note), room)
        kept.append({**note, (notation.REST if notation.REST in note else notation.STEPS): length})
        room -= length
    return kept + [dict(note) for note in ends]


def ending_fits(*, variation, grid, meter):
    """Whether a player's ending can be laid on a figure: it is written for the meter, or for any, and one of the two grids
    divides the other, so that the finer holds both."""
    if ENDS not in variation or variation.get(NEEDS, {}).get(METER, meter) != meter:
        return False
    return grid % variation[melody.GRID] == 0 or variation[melody.GRID] % grid == 0


def stretched(*, notes, by):
    """Notes written again on a grid so many times finer."""
    return [{**note, (notation.REST if notation.REST in note else notation.STEPS): lasts(note) * by} for note in notes]


def decorated_figure(*, bars, player, phrase_bars, meter):
    """A figure as a player plays it: a phrase of its bars, the bars the player varies ending in the player's own notes, on
    the finest grid of the figure's and the endings'. A player who varies nothing plays the figure as written, and an ending
    written for another meter, or on a grid that neither divides the figure's nor is divided by it, is left out."""
    grid = sum(lasts(note) for note in bars[0])
    fitting = [variation for variation in player.get(characters.VARIES, []) if ending_fits(variation=variation, grid=grid, meter=meter)]
    if not fitting or phrase_bars % len(bars):
        return [notation.copied_line(bar) for bar in bars]
    finest = max([grid] + [variation[melody.GRID] for variation in fitting])
    fitting = [variation for variation in fitting if finest % variation[melody.GRID] == 0]
    phrase = [stretched(notes=bars[count % len(bars)], by=finest // grid) for count in range(phrase_bars)]
    for variation in fitting:
        ends = stretched(notes=variation[ENDS], by=finest // variation[melody.GRID])
        for bar in variation[BARS]:
            phrase[bar - 1] = with_ending(bar=phrase[bar - 1], ends=ends)
    return phrase


def figure_part(*, entry, role, meter, player, phrase_bars):
    """A value's figure as a tune's part, as a player plays it; the figure's bars are its lines."""
    lines = decorated_figure(bars=entry[FIGURE], player=player, phrase_bars=phrase_bars, meter=meter)
    grid = sum(lasts(note) for note in lines[0])
    return {notation.STEP: step_of(meter=meter, grid=grid), notation.OCTAVE: role[notation.OCTAVE], **voice_of(role), notation.LINES: lines}


def held_part(*, role, meter, chord):
    """One bar of the home note or chord, held."""
    note = {notation.DEGREE: 1, notation.STEPS: int(bar_length(meter) * EIGHTHS_IN_WHOLE)}
    if chord:
        note[notation.CHORD] = HELD_CHORD
    return {notation.STEP: EIGHTH, notation.OCTAVE: role[notation.OCTAVE], **voice_of(role), notation.LINES: [[note]]}


def tune_part(*, lines, role, meter, grid):
    return {notation.STEP: step_of(meter=meter, grid=grid), notation.OCTAVE: role[notation.OCTAVE], **voice_of(role), notation.LINES: lines}


def habits_of(*, habits, player):
    """A style's melody habits as a player keeps them: a wider or narrower range, and the busier rhythms for a busy player."""
    kept = {**habits, **({melody.SPAN: player[melody.SPAN]} if melody.SPAN in player else {})}
    if player.get(characters.BUSY):
        kept[melody.RHYTHMS] = habits[melody.ANSWER_RHYTHMS]
    return kept


def way_beside(*, beside, role, place, tune, section):
    """What the player beside the tune does in the section at a place of the form, or None for any other player, for a section nobody has
    the tune in, and for a section whose own plan already has the player answer every line, which is played as the plan writes it."""
    if role[ROLE] != beside.get(ROLE) or tune is None or tune is role:
        return None
    way = beside[BESIDE_WAYS][place]
    if way not in interplay.WAYS:
        raise ValueError(errors.ERR_NO_SUCH_WAY_BESIDE.format(way))
    if way == interplay.ANSWERS and role[ROLE] in section[PLAYS] and any(entry.get(melody.ANSWER) for entry in section.get(PLAN, [])):
        return None
    return way


def line_letters(*, plans, answers):
    """The letters of the lines a lead plays through a song, or of those an answering instrument plays, each once, in the
    order the song first plays them."""
    letters = []
    for plan in plans:
        for entry in plan:
            if bool(entry.get(melody.ANSWER)) == answers and melody.LINE in entry and entry[melody.LINE] not in letters:
                letters.append(entry[melody.LINE])
    return letters


def band_said(*, style, song, roles):
    """Who plays, for the notes: each instrument's player by name, with what the style says of the player."""
    said = []
    for instrument, complexity in song.get(PLAYERS, {}).items():
        if any(role.get(PLAYER) == instrument for role in roles):
            level = level_of(character_of(complexity))
            if level is None:
                # A player whose gauges were set one by one is nobody's preset, and is named by the instrument alone.
                said.append(composer_text.MSG_PLAYED_BY_OWN.format(instrument))
                continue
            player = player_of(style=style, instrument=instrument, character=character_of(level))
            said.append(composer_text.MSG_PLAYED_BY.format(instrument, player_name(instrument=instrument, complexity=level), player.get(characters.SAYS, '')).strip())
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
    return named[0] if named else labels.MSG_GM_SOUNDS[number - limits.MIN_GM_SOUND].lower()


def section_of(*, name, style, song):
    """A section as the song describes it over what the style says of a section of its name."""
    of_song = song.get(SECTIONS, {}).get(name, {})
    kind = of_song.get(KIND, name)
    if kind not in style[SECTIONS] and not of_song:
        raise ValueError(errors.ERR_NO_SUCH_SECTION.format(name))
    section = {**style[SECTIONS].get(kind, {}), **of_song, KIND: kind}
    # The song's hooks: the main one placed among the lines of the kind of section that says it, and the tag sung in its kind,
    # by its singer, who then plays there.
    hooks = song.get(melody.HOOKS, {})
    main = hooks.get(melody.MAIN_HOOK, {})
    if main.get(melody.SUNG_IN) == kind and main.get(melody.PLACEMENT) and section.get(PLAN):
        section[PLAN] = plan_with_hook_placed(plan=section[PLAN], placement=main[melody.PLACEMENT])
    second = hooks.get(melody.SECOND_HOOK, {})
    if second.get(melody.SUNG_IN) == kind and not section.get(HELD):
        section[PLAN] = plan_with_tag(plan=section.get(PLAN, []), lines=section.get(BARS, BARS_IN_A_TAG_LINE) // BARS_IN_A_TAG_LINE)
        section[PLAYS] = list(dict.fromkeys([*section.get(PLAYS, []), second[melody.SUNG_BY]]))
    asks = song.get(melody.MELODY_ASKS)
    if asks and section.get(PLAN):
        # What the song asks of its melodies is laid over the plan: for the whole song, and for this kind of section.
        of_kind = asks.get(melody.BY_KIND, {}).get(kind, {})
        section[PLAN] = plan_as_asked(plan=section[PLAN], height=of_kind.get(melody.HEIGHT), busy=of_kind.get(melody.LINE_BUSY, asks.get(melody.LINE_BUSY)), repeats=asks.get(melody.REPEATS))
    return section


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
            raise ValueError(errors.ERR_NO_STYLE_FORM.format(style[NAME], given, song[TEMPLATE]))
        return named[0][SECTIONS]
    if not forms:
        raise ValueError(errors.ERR_NO_STYLE_FORMS.format(style[NAME]))
    if LENGTH in song:
        return min(forms, key=lambda form: abs(seconds_of(sections=form[SECTIONS], style=style, song=song, meter=meter, tempo=tempo) - song[LENGTH]))[SECTIONS]
    return max(forms, key=share_of)[SECTIONS]


def in_octaves_of(*, pattern, by, group):
    """A pattern's data with every note an octave or more higher or lower and in a player's group of patterns, as a second player
    plays a first player's riff."""
    moved = copy.deepcopy(pattern)
    if PatternSetting.GROUP in moved:
        moved[PatternSetting.GROUP] = group
    if by and Row.OCTAVE in moved:
        moved[Row.OCTAVE] = [None if octave is None else octave + by for octave in moved[Row.OCTAVE]]
    return moved


class SongRiff:
    """One riff of a song as the arranger places it: its name, None for the song's first; the riff as chosen; its notes, a line in
    eighths; how many bars it lasts; its bars apart, or None where it has one; and the players who play it, the first its chords."""

    __slots__ = ('name', 'riff', 'notes', 'count', 'split', 'players')

    def __init__(self, *, name, riff, notes, count, split, players):
        self.name = name
        self.riff = riff
        self.notes = notes
        self.count = count
        self.split = split
        self.players = players


class SectionInHand:
    """One section of the form while its scene is written: its place and name, what the song says of it, and who plays what so far."""

    __slots__ = ('count', 'name', 'section', 'scene_name', 'bars', 'chords', 'play', 'tune_role', 'here', 'chords_played')

    def __init__(self, *, count, name):
        self.count = count
        self.name = name
        self.section = None
        self.scene_name = None
        self.bars = None
        self.chords = None
        self.play = {}
        self.tune_role = None
        self.here = None
        self.chords_played = None



class Arrangement:
    """A song's picks arranged for its band: what the song and its style say of the whole song, the parts written from them, and the scenes of the form.

    Made from a style and a song's picks, it writes the drums, seats the pitched players and then writes each section of
    the form in turn, a section's parts named so that a section that returns plays the parts it played before. as_input()
    is everything written, as a MacroComposer input.
    """

    __slots__ = ('_beside', '_chains', '_chord_entry', '_drum_tracks', '_drum_traits', '_drummer', '_drums_of', '_extra', '_form', '_form_names', '_habits', '_has_a_hook', '_instruments', '_intros_met', '_levels', '_met', '_meter', '_more_scales', '_no_drums', '_notes', '_parts', '_phrase_bars', '_phrased', '_picks', '_pieces_off', '_pitched', '_plans', '_played', '_playing', '_progressions', '_riff_eighths', '_riffs', '_roles', '_same_tunes', '_scale', '_scale_type', '_shaped', '_solos_met', '_song', '_style', '_tempo', '_timing', '_tracks', '_under', '_without')

    def __init__(self, *, style, song):
        self._song = song
        self._style = style_in(style=style, template=song[TEMPLATE], variant=song.get(VARIANT))
        self._picks = picked(style=self._style, song=self._song)
        self._meter = str(self._picks.get(METER, COMMON_TIME))
        self._tempo = tempo_of(style=self._style, song=self._song, picks=self._picks)
        self._form_names = form_of(style=self._style, song=self._song, meter=self._meter, tempo=self._tempo)
        lift = 1 if self._song[KEY][ROOT] in LOW_ROOTS else 0
        self._roles = [loud_role(role={**role, notation.OCTAVE: role[notation.OCTAVE] + lift} if notation.OCTAVE in role else role, song=self._song) for role in self._style[ROLES]]
        self._style = loud_style(style=self._style, song=self._song, roles=self._roles)
        self._phrase_bars = self._style.get(PHRASE_BARS, DEFAULT_PHRASE_BARS)
        chord_trait = self._style.get(CHORD_TRAIT_FIELD, CHORD_TRAIT)
        self._chord_entry = values_of(style=self._style, trait=chord_trait)[self._picks[chord_trait]]
        self._scale_type = self._song[KEY].get(TYPE, self._chord_entry.get(SCALE_TYPE, MAJOR))
        self._scale = SCALE_NAME.format(self._song[KEY][ROOT], self._scale_type.capitalize())
        self._habits = self._style[MELODY] if melody.GRID in self._style[MELODY] else self._style[MELODY][self._meter]
        # A tune in a scale type the style gives notes of its own, a minor song its minor notes and home, takes those: the major
        # notes read in a minor scale rest on the scale's third and sound like the major key beside it.
        self._habits = {**self._habits, **self._habits.get(BY_SCALE_TYPE, {}).get(self._scale_type, {})}
        if self._song.get(song_plan.PLAN_OF_SONG) not in (None, False):
            # A song that asks for a plan has a section made for each place of its form, each saying what the plan worked out.
            def chords_of(section):
                return [chord_of(chord) for chord in section.get(CHORDS) or self._chord_entry.get(BY_SECTION, {}).get(section[KIND]) or self._chord_entry[PATTERN]]
            self._song = SongPlan(style=self._style, song=self._song, form_names=self._form_names, tempo=self._tempo, scale_type=self._scale_type, chords_of=chords_of).planned()
            self._form_names = self._song[FORM]
        self._levels = self._song.get(PLAYERS, {})
        self._without = self._song.get(WITHOUT, [])
        self._no_drums = any(role.get(DRUMS) and role[ROLE] in self._without for role in self._roles)
        self._pieces_off = self._song.get(WITHOUT_PIECES, [])
        self._played = pieces_played(self._song)
        self._playing = players_in(style=self._style, roles=self._roles, levels=self._levels, section={})
        self._drummer = next((self._playing[role[ROLE]] for role in self._roles if role.get(DRUMS)), {})
        self._drum_traits = [trait for role in self._roles for trait in role.get(DRUMS, [])] + [FILLS]
        # The song's riffs, where it has any: first the song's own, or the one its kind of music is built on, then each riff added
        # for kinds of section, by name; and how many eighths a bar of a riff lasts.
        self._riff_eighths = int(bar_length(self._meter) * EIGHTHS_IN_WHOLE)
        self._riffs = [self.riff_made(riff=self._song.get(riffs_values.RIFF, self._style.get(riffs_values.RIFF)) or {}, name=None, seed=self._song.get(SEED, 0))]
        for more in self._song.get(MORE_RIFFS, []):
            self._riffs.append(self.riff_made(riff=more, name=more[NAME], seed=zlib.crc32(MORE_RIFF_SEED.format(seed=self._song.get(SEED, 0), name=more.get(RIFF_DRAWN_AS, more[NAME])).encode())))
        self._parts = {}
        self._write_drums()
        self._seat_players()
        self._form = []
        self._notes = []
        self._met = {}
        self._same_tunes = {}
        # The scales of sections in a key or a scale of their own, by name.
        self._more_scales = {}
        self._plans = [section_of(name=name, style=self._style, song=self._song).get(PLAN, []) for name in self._form_names]
        # A song has a hook where the song or its style asks for one and a section of its form marks a line as one.
        self._has_a_hook = bool(self._song.get(melody.HOOK, self._style.get(melody.HOOK, False))) and any(has_hook(plan) for plan in self._plans)
        self._phrased = [composer_text.MSG_TUNE_PHRASING_NAME] if self._song.get(TUNE_PHRASING) is not None else []
        self._beside = self._song.get(BESIDE, {})
        self._under = UnderLead(busy=self._beside.get(BESIDE_BUSY, interplay.USUAL_BUSY), habits=self._habits, grid=self._habits[melody.GRID], scale_type=self._scale_type, seed=self._song.get(SEED, 0))
        self._solos_met = 0
        self._intros_met = 0
        for count, name in enumerate(self._form_names, start=1):
            self._write_section(count=count, name=name)

    def riff_made(self, *, riff, name, seed):
        """A riff of the song with its notes, its bars and the players of the band who play it: those of its players whose part is a figure."""
        notes = riff_line_of(riff=riff, seed=seed, eighths=self._riff_eighths, flattened=flattened_in(self._scale_type)) if riff.get(riffs_values.RIFF_ROLES) else []
        players = [role[ROLE] for role in self._roles if role[ROLE] in riff.get(riffs_values.RIFF_ROLES, []) and role[ROLE] not in self._without and not role.get(DRUMS)
                   and FIGURE in values_of(style=self._style, trait=role[TRAIT]).get(self._picks.get(role[TRAIT]), {})] if notes else []
        return SongRiff(name=name, riff=riff, notes=notes, count=riff_bars_of(line=notes, eighths=self._riff_eighths) or 1, split=split_bars(line=notes, eighths=self._riff_eighths), players=players)

    def chords_in(self, section, *, shared=False):
        """A section's chords, its last bar set up for what follows where the section says so."""
        bars = 1 if section.get(HELD) else section[BARS]
        written = section.get(CHORDS) or self._chord_entry.get(BY_SECTION, {}).get(section[KIND]) or self._chord_entry[PATTERN]
        # A bar of two chords is kept as its two for the progression, and is its first chord for whatever goes bar by bar.
        chords = [_bar_of_chords(chord=chord, shared=shared) for chord in written]
        if section.get(LAST_CHORD) is not None and not section.get(EVERY, self._chord_entry.get(EVERY)) and len(chords) <= bars:
            # The section's last bar is set up for what follows: the chords are written out a bar each, and the last bar takes the approach chord.
            chords = [chords[bar % len(chords)] for bar in range(bars - 1)] + [chord_of(section[LAST_CHORD])]
        return chords

    def riff_bars_in(self, section, *, riff):
        """Which bar of a riff each bar of a section plays, None where a riff that stays at home gives way to a held chord; nothing
        where the section has not the riff."""
        if not riff.players or section.get(HELD) or section[KIND] not in riff.riff.get(riffs_values.RIFF_KINDS, []) or section[BARS] % riff.count:
            return []
        stays = riff.riff.get(riffs_values.RIFF_WITH_CHORDS) == riffs_values.STAYS_HOME and riff.split is not None and not section.get(EVERY, self._chord_entry.get(EVERY))
        return bars_played(chords=self.chords_in(section), bars=section[BARS], count=riff.count, stays=stays)

    def riff_played(self, section, *, by=None, notes=None):
        """The first of the song's riffs that plays in a section, with which of its bars each bar of the section plays: the first a
        player plays where one is named, the first of one way of notes where a way is named; (None, []) where there is none."""
        for riff in self._riffs:
            if (by is None or by in riff.players) and (notes is None or riff.riff.get(riffs_values.RIFF_NOTES) == notes):
                bars = self.riff_bars_in(section, riff=riff)
                if bars:
                    return riff, bars
        return None, []

    def _write_drums(self):
        """Write the drums' parts, a set for each way the form's sections have the drummer play, and say which set each section plays."""
        drum_sets = {}
        usual_drummer = label_of(character_of(self._levels[DRUMS])) if DRUMS in self._levels else None
        self._drums_of = {}
        for name in self._form_names:
            section = section_of(name=name, style=self._style, song=self._song)
            if self._no_drums or section.get(HELD) or DRUMS not in section[PLAYS] or name in self._drums_of:
                continue
            character = character_in(levels=self._levels, instrument=DRUMS, section=section)
            level = None if character is None else label_of(character)
            changed = {trait: value for trait, value in section.get(PICKS, {}).items()
                       if trait in self._drum_traits and fits(entry=values_of(style=self._style, trait=trait)[value], picks=self._picks)}
            plays = player_of(style=self._style, instrument=DRUMS, character=character)
            if FILLS_COME in self._song:
                # The song says how often a fill comes, whatever the drummer would do: never, at the end of each section, or every so many bars.
                plays = {**plays, characters.FILL_EVERY: section[BARS] if self._song[FILLS_COME] == EACH_SECTION else self._song[FILLS_COME]}
            # A drum solo is written in four; in another meter the drummer plays the section alone as any other.
            drum_solo_here = bool(section.get(DRUM_SOLO)) and self._meter == COMMON_TIME
            leaves = section.get(joins.LEAVES)
            key = (level, tuple(sorted(changed.items())), math.gcd(plays.get(characters.FILL_EVERY, self._phrase_bars) or self._phrase_bars, section[BARS]))
            if leaves is not None:
                key = key + (section[BARS], frozen(leaves), section.get(FILL_INSIDE), section.get(FILL_INSIDE_EVERY), frozen(section.get(MARKER)), section.get(MARKER_EVERY))
            if drum_solo_here:
                key = (DRUM_SOLO, section[BARS])
            # Under a riff of chords on its accents the kick strikes each accent, bar by bar.
            kicked_riff, riff_here = self.riff_played(section, notes=riffs_values.ACCENT_CHORDS) if not drum_solo_here else (None, [])
            kick_bars = accent_bars(line=kicked_riff.notes, eighths=self._riff_eighths) if kicked_riff is not None else []
            over = {KICK: [None if bar is None else kick_bars[bar] for bar in riff_here]} if any(bar is not None for bar in riff_here) else None
            if over:
                key = key + (riffs_values.RIFF, kicked_riff.name, section[BARS], tuple(riff_here))
            if key not in drum_sets:
                if drum_solo_here:
                    made = solo_parts(style=self._style, bars=section[BARS], seed=self._song.get(SEED, 0), kit=self._played)
                else:
                    made = drum_parts(style=self._style, picks={**self._picks, **changed}, roles=self._roles, meter=self._meter, phrase_bars=self._phrase_bars, drummer=plays, section_bars=section[BARS], own_fill=FILLS in self._song.get(PICKS, {}), seed=self._song.get(SEED, 0), kit=self._played,
                                      leaves=leaves, inside={FILL_INSIDE: section.get(FILL_INSIDE), FILL_INSIDE_EVERY: section.get(FILL_INSIDE_EVERY), MARKER: section.get(MARKER), MARKER_EVERY: section.get(MARKER_EVERY)}, over=over)
                drum_sets[key] = {}
                for piece, part in made.items():
                    # A piece of the kit switched off is left out: its strokes are never moved to another piece.
                    if piece in self._pieces_off:
                        continue
                    if piece == SNARE and not self._song.get(QUIET_NOTES, True):
                        # The quiet notes switched off: the snare's soft strokes and ghost notes between the main ones are left out.
                        part = {**part, notation.HITS: [notation.NONE if hit in (notation.SOFT, notation.GHOST) else hit for hit in part[notation.HITS]]}
                    profile = self._style.get(BEAT_LOUDNESS)
                    is_uneven = plays.get(characters.UNEVEN) and not drum_solo_here
                    if (profile and not drum_solo_here) or is_uneven:
                        # A pattern written out, where each stroke's loudness is its own: the style's lean on each beat, then a person's unevenness on top.
                        pattern = drum_pattern(part)
                        if profile and not drum_solo_here:
                            pattern = leaning(pattern=pattern, profile=profile, meter=self._meter, dynamics=self._song.get(DYNAMICS, {}).get(drummer_role(self._roles), loudness.USUAL_DYNAMICS))
                        if is_uneven:
                            pattern = uneven(pattern=pattern, by=plays[characters.UNEVEN], dice=random.Random(DRUM_SEED.format(self._song.get(SEED, 0), piece, section[KIND])))
                        part = {RAW: pattern}
                    named = piece if leaves is None and not over and key[:2] == (usual_drummer, ()) and piece not in self._parts else composer_text.MSG_PART_OF_SECTION.format(piece, name if leaves is not None or over else section[KIND])
                    self._parts[named] = part
                    drum_sets[key][piece] = named
            self._drums_of[name] = drum_sets[key]
        self._drum_tracks = list(dict.fromkeys(piece for pieces in self._drums_of.values() for piece in pieces))
        self._timing = {piece: timing_generators(move=self._drummer.get(characters.TIMING, {}).get(piece, {})) for piece in self._drum_tracks}

    def _seat_players(self):
        """Give each pitched player of the band a track and a sound, and write what a player plays wherever the player plays: the figure and the held chord."""
        # The order of a made song's tracks: the muted chords track first, then the chords, the lead and the backing, the bass, and the drums last.
        self._tracks = {composer_text.MSG_CHORDS_TRACK: composer_text.MSG_CHORDS_INSTRUMENT}
        self._instruments = {DRUM_KIT: None, composer_text.MSG_CHORDS_INSTRUMENT: CHORDS_GUIDE_SOUND}
        self._progressions = {}
        self._chains = {}
        self._extra = {}
        self._shaped = []
        self._pitched = []
        for role in self._roles:
            if role.get(DRUMS) or role[ROLE] in self._without:
                continue
            entry = values_of(style=self._style, trait=role[TRAIT])[self._picks[role[TRAIT]]]
            if SOUND not in entry:
                continue
            sound = sound_of(style=self._style, song=self._song, role=role[ROLE], usual=entry[SOUND])
            self._instruments[sound] = self._style[SOUNDS].get(sound, self._song.get(ROLE_SOUNDS, {}).get(role[ROLE]))
            self._tracks[role[ROLE]] = sound
            self._pitched.append((role, entry))
            if FIGURE in entry:
                self._parts[role[ROLE]] = figure_part(entry=entry, role=role, meter=self._meter, player=self._playing[role[ROLE]], phrase_bars=self._phrase_bars)
                self._shaped.append(role[ROLE])
            self._parts[composer_text.MSG_PART_OF_SECTION.format(role[ROLE], HELD)] = held_part(role=role, meter=self._meter, chord=any(notation.CHORD in note for bar in entry.get(FIGURE, []) for note in bar))
            self._timing[role[ROLE]] = timing_generators(move=self._playing[role[ROLE]].get(characters.TIMING, {}))
            for generator in entry.get(GENERATORS, []):
                for kind, settings in generator.items():
                    self._extra.setdefault(SECTION_OF_KIND[kind], {})[role[ROLE]] = dict(settings)
            if role[ROLE] in self._extra.get(GUITARIFIES, {}):
                self._extra[GUITARIFIES][role[ROLE]].update(self._playing[role[ROLE]].get(characters.GUITARIFY_OF_PLAYER, {}))
        for track, moves in self._timing.items():
            self._chains[composer_text.MSG_TIMING_CHAIN.format(track)] = [{RUSH: track}, {DRAG: track}]
            self._extra.setdefault(RUSHES, {})[track] = moves[RUSH]
            self._extra.setdefault(DRAGS, {})[track] = moves[DRAG]
        self._tracks.update({piece: DRUM_KIT for piece in self._drum_tracks})

    def _write_section(self, *, count, name):
        """Write one section of the form as a scene: who plays in it and which part each plays, writing the parts the section is the first to play."""
        at = SectionInHand(count=count, name=name)
        at.section = section_of(name=at.name, style=self._style, song=self._song)
        self._met[at.name] = self._met.get(at.name, 0) + 1
        self._solos_met += at.section[KIND] == SOLO_KIND
        self._intros_met += at.section[KIND] == INTRO_KIND
        at.scene_name = at.name if self._met[at.name] == 1 else composer_text.MSG_REPEATED_SCENE.format(at.name, self._met[at.name])
        at.bars = 1 if at.section.get(HELD) else at.section[BARS]
        at.chords = self.chords_in(at.section)
        at.play = {}
        at.tune_role = None
        if at.section.get(HELD):
            self._hold(at)
        else:
            self._play_drums(at)
            at.here = players_in(style=self._style, roles=self._roles, levels=self._levels, section=at.section)
            self._write_chords(at)
            # The player who has the tune in the section, if any: a player of lines who answers nobody.
            at.tune_role = next((other for other, other_entry in self._pitched if FIGURE not in other_entry and not other.get(ANSWERS) and other[ROLE] in at.section[PLAYS]), None)
            for role, entry in self._pitched:
                self._give_part(at, role=role, entry=entry)
        # The tune goes to the player the song gives it to: for this kind of section, or else for the whole song. That player plays
        # the tune in place of the usual part, the player who had the tune rests, and with nobody the section has no tune.
        tune_by = self._song.get(TUNE_BY, {}).get(at.section[KIND], self._song.get(TUNE_BY_SONG))
        if at.tune_role is not None and at.tune_role[ROLE] in at.play and tune_by is not None and tune_by != at.tune_role[ROLE]:
            tune_played = at.play.pop(at.tune_role[ROLE])
            if tune_by != NOBODY and any(role[ROLE] == tune_by for role in self._roles):
                at.play[tune_by] = tune_played
        if not at.play:
            # Nothing of the song's picks plays in this section, as pads alone where the song has no chord part: it is left out.
            self._met[at.name] -= 1
            return
        at.play[composer_text.MSG_CHORDS_TRACK] = at.chords_played
        scene_settings = dict(at.section.get(SCENE_SETTINGS) or {})
        if at.section[KIND] in file_format.SECTION_KINDS:
            # A scene says what kind of section it is, where the kind is one a scene may be.
            scene_settings.setdefault(SECTION_OF_SCENE, at.section[KIND])
        if isinstance(scene_settings.get(SCALE), dict):
            # A section in a key or a scale of its own: the scale is named as the song's is and added to the set's.
            own_scale = scene_settings[SCALE]
            scene_settings[SCALE] = SCALE_NAME.format(own_scale[ROOT], own_scale[TYPE].capitalize())
            self._more_scales[scene_settings[SCALE]] = {ROOT: own_scale[ROOT], TYPE: own_scale[TYPE]}
        # A section that climbs or fades with no bars said does so across all of its bars.
        if VelocitySetting.IN_START in scene_settings:
            scene_settings.setdefault(VelocitySetting.IN_OVER, at.bars)
        if VelocitySetting.OUT_END in scene_settings:
            scene_settings.setdefault(VelocitySetting.OUT_OVER, at.bars)
        if SceneSetting.TEMPO_IN_END in scene_settings:
            # A section that moves to another tempo by its end ramps across all of its bars.
            scene_settings.setdefault(SceneSetting.TEMPO_IN_OVER, at.bars)
        self._form.append({SCENE: at.scene_name, BARS: at.bars, PLAY: at.play, **({SETTINGS_OF_SCENE: scene_settings} if scene_settings else {})})
        said_of_scene = composer_text.MSG_MADE_SCENE.format(at.count, at.scene_name, at.bars)
        self._notes.append(MADE_SCENE_SAID.format(said_of_scene, at.section[SAID_OF_SECTION]) if at.section.get(SAID_OF_SECTION) else said_of_scene)

    def _hold(self, at):
        """Write a section that is one held chord: a crash and a kick where the kit has them, each backing player holding the chord, and the chord on the chords track."""
        held = composer_text.MSG_PART_OF_SECTION.format(CRASH, HELD)
        if not self._no_drums and CRASH not in self._pieces_off:
            self._parts[held] = one_hit(style=self._style, meter=self._meter, drum=CRASH, played=self._played)
        if not self._no_drums and KICK not in self._pieces_off:
            self._parts[composer_text.MSG_PART_OF_SECTION.format(KICK, HELD)] = one_hit(style=self._style, meter=self._meter, drum=KICK, played=self._played)
        if not self._no_drums and CRASH not in self._pieces_off:
            if CRASH not in self._tracks:
                self._tracks[CRASH] = DRUM_KIT
                self._drum_tracks.append(CRASH)
            at.play[CRASH] = held
        if KICK in self._tracks:
            at.play[KICK] = {PART: composer_text.MSG_PART_OF_SECTION.format(KICK, HELD), ONCE: True}
        for role, entry in self._pitched:
            if FIGURE in entry and role[ROLE] in at.section.get(PLAYS, [role[ROLE]]):
                at.play[role[ROLE]] = {PART: composer_text.MSG_PART_OF_SECTION.format(role[ROLE], HELD), ONCE: True, CHAINS: [composer_text.MSG_FOLLOW_CHORDS_NAME]}
        # The held chord is on the chords track too, the home chord for a bar, and what holds it follows it there.
        self._chains[composer_text.MSG_FOLLOW_CHORDS_NAME] = [dict(FOLLOWS_THE_CHORDS)]
        at.chords_played = composer_text.MSG_PART_OF_SECTION.format(at.name, CHORDS)
        self._parts[at.chords_played] = {RAW: one_chord(self._meter)}
        at.chords_played = {PART: at.chords_played, ONCE: True}

    def _play_drums(self, at):
        """Have each piece of the kit play the part written for the section, with a crash on its first beat where the section starts with one."""
        for piece, part in self._drums_of.get(at.name, {}).items():
            at.play[piece] = {PART: part, CHAINS: [composer_text.MSG_TIMING_CHAIN.format(piece)]}
        if at.section.get(CRASH_START) and at.name in self._drums_of and CRASH not in self._pieces_off:
            start = composer_text.MSG_SECTION_START_PART.format(CRASH)
            self._parts[start] = one_hit(style=self._style, meter=self._meter, drum=CRASH, played=self._played)
            if CRASH not in self._tracks:
                self._tracks[CRASH] = DRUM_KIT
                self._drum_tracks.append(CRASH)
            at.play.setdefault(CRASH, {PART: start, ONCE: True})

    def _write_chords(self, at):
        """Write the section's chords on the chords track, a step a chord, which every clip that plays them follows."""
        progression = composer_text.MSG_PART_OF_SECTION.format(at.name, CHORDS)
        # The section's chords go on the chords track, written a step a chord, which every clip that plays them follows.
        section_progression = progression_of(chords=self.chords_in(at.section, shared=True), every=at.section.get(EVERY, self._chord_entry.get(EVERY)), meter=self._meter)
        own_scale = (at.section.get(SCENE_SETTINGS) or {}).get(SCALE)
        written_chords = chords_written(progression=section_progression, meter=self._meter, scale_type=own_scale[TYPE] if isinstance(own_scale, dict) else self._scale_type)
        if written_chords is None:
            self._progressions[progression] = section_progression
            self._chains[progression] = [{PROGRESSION: progression}]
            self._parts[progression] = {RAW: one_chord(self._meter)}
            at.chords_played = {PART: progression, CHAINS: [progression]}
        else:
            self._parts[progression] = {RAW: written_chords}
            at.chords_played = progression

    def _lines_of(self, at, *, role):
        """The lines a player of a tune plays in the section: those the section gives, or those sketched for the player."""
        given = at.section.get(LINES_GIVEN, {}).get(role[ROLE])
        return given or sketched(habits={**habits_of(habits=self._habits, player=at.here[role[ROLE]]), **role.get(HABITS, {}), **self._song.get(ROLE_HABITS, {}).get(role[ROLE], {}), **self._song.get(MELODY, {})}, plan=at.section[PLAN], chords=at.chords, scale_type=self._scale_type, seed=self._song.get(SEED, 0),
                                 answers=bool(role.get(ANSWERS)), engine=self._song.get(MELODY_ENGINE, role.get(melody.ENGINE)), voice=role.get(VOICE), letters=line_letters(plans=self._plans, answers=bool(role.get(ANSWERS))),
                                 hook=self._has_a_hook, hook_take=self._song.get(melody.HOOK_TAKE, melody.FIRST_HOOK_TAKE), tag_take=self._song.get(melody.HOOKS, {}).get(melody.SECOND_HOOK, {}).get(melody.TAG_TAKE, melody.FIRST_HOOK_TAKE))

    def _give_part(self, at, *, role, entry):
        """Give a pitched player the part the player plays in the section, writing the part where no section before wrote it: an answer beside the tune, a figure, or a tune."""
        way = way_beside(beside=self._beside, role=role, place=at.count - 1, tune=at.tune_role, section=at.section)
        if way == interplay.WAITS or (way is None and role[ROLE] not in at.section[PLAYS]):
            return
        if way is not None:
            self._play_beside(at, role=role, way=way)
            return
        if FIGURE in entry:
            self._play_figure(at, role=role, entry=entry)
            return
        self._play_tune(at, role=role)

    def _play_beside(self, at, *, role, way):
        """Have a player play beside the tune in one of the ways of playing under a lead, where the way leaves the player any notes."""
        # Fills and answers are drawn anew each time a section returns; the hook and a riff are the same every time.
        drawn_in = at.scene_name if way in interplay.DRAWN_ANEW else at.section.get(DRAWN_AS, at.name)
        part = composer_text.MSG_PART_BESIDE.format(drawn_in, role[ROLE], way)
        if part not in self._parts:
            lines = self._under.lines(way=way, tune=self._lines_of(at, role=at.tune_role), chords=at.chords, section=drawn_in)
            if not notation.is_silent(lines):
                self._parts[part] = tune_part(lines=lines, role=role, meter=self._meter, grid=self._habits[melody.GRID])
                self._shaped.append(part)
        if part in self._parts:
            at.play[role[ROLE]] = {PART: part, ONCE: True, CHAINS: [composer_text.MSG_TIMING_CHAIN.format(role[ROLE])]}

    def _play_figure(self, at, *, role, entry):
        """Have a backing player play the player's figure over the section's chords, or the song's riff where the section has one, or the figure with the band's last bar together."""
        chain = composer_text.MSG_PART_OF_SECTION.format(at.name, role[ROLE])
        self._chains[chain] = [dict(FOLLOWS_THE_CHORDS)] + [{kind: role[ROLE]} for generator in entry.get(GENERATORS, []) for kind in generator]
        if role.get(VOICE_LEADING):
            self._chains[chain].append({VOICE_LEADING_KIND: NEAR})
        self._chains[chain] += [{RUSH: role[ROLE]}, {DRAG: role[ROLE]}]
        figure = role[ROLE]
        entry_here = entry
        if FIGURE in entry.get(BY_SECTION, {}).get(at.section[KIND], {}):
            # The value's own figure for this kind of section, a part of its own, in place of the figure played elsewhere.
            entry_here = {**entry, FIGURE: entry[BY_SECTION][at.section[KIND]][FIGURE]}
            figure = composer_text.MSG_PART_OF_SECTION.format(role[ROLE], at.section[KIND])
            if figure not in self._parts:
                self._parts[figure] = figure_part(entry=entry_here, role=role, meter=self._meter, player=self._playing[role[ROLE]], phrase_bars=self._phrase_bars)
                self._shaped.append(figure)
        if at.here[role[ROLE]] != self._playing[role[ROLE]]:
            held_back = figure_part(entry=entry_here, role=role, meter=self._meter, player=at.here[role[ROLE]], phrase_bars=self._phrase_bars)
            # A player held back who plays the figure no differently plays the one part, so that no part is written twice.
            if held_back != self._parts[figure]:
                figure = composer_text.MSG_PART_AT_LEVEL.format(figure, label_of(character_in(levels=self._levels, instrument=role.get(PLAYER), section=at.section)))
                if figure not in self._parts:
                    self._parts[figure] = held_back
                    self._shaped.append(figure)
        riff, riff_here = self.riff_played(at.section, by=role[ROLE])
        if riff_here:
            # The song's riff takes the place of the player's figure here: moved by the chords and played as written, with none of the figure's
            # own generators. Its first player plays its chords, and a player under the first its notes alone.
            written_for = riff.riff.get(RIFF_FOR, riff.players[0])
            first = role[ROLE] == written_for
            riff_part = composer_text.MSG_PART_OF_SECTION.format(role[ROLE], riff.name or riffs_values.RIFF)
            if None in riff_here:
                # A riff that stays at home is written out for the whole section: the riff over the home chord, and every other chord held.
                riff_part = composer_text.MSG_PART_OF_SECTION.format(at.name, riff_part)
            if riff.riff.get(RIFF_OWN) is not None:
                # A riff written by hand is played as written, each player in the player's own octave.
                first_role = next(other for other in self._roles if other[ROLE] == written_for)
                self._parts.setdefault(riff_part, {RAW: in_octaves_of(pattern=riff.riff[RIFF_OWN], by=role[notation.OCTAVE] - first_role[notation.OCTAVE], group=role[ROLE])})
            elif riff_part not in self._parts:
                lines = [riff.notes] if None not in riff_here else [held_bar(eighths=self._riff_eighths, chord=first) if bar is None else riff.split[bar] for bar in riff_here]
                self._parts[riff_part] = {notation.STEP: EIGHTH, notation.OCTAVE: role[notation.OCTAVE], **voice_of(role), notation.LINES: [notation.copied_line(line if first else single(line)) for line in lines]}
                self._shaped.append(riff_part)
            riff_chain = composer_text.MSG_PART_OF_SECTION.format(chain, riffs_values.RIFF)
            self._chains[riff_chain] = [dict(FOLLOWS_THE_CHORDS), {RUSH: role[ROLE]}, {DRAG: role[ROLE]}]
            at.play[role[ROLE]] = {PART: riff_part, CHAINS: [riff_chain]}
            return
        leaves = at.section.get(joins.LEAVES) or {}
        if leaves.get(joins.TAIL) in (joins.DROP_OUT, joins.STOPS):
            # The band's last bar together: the figure is written out for the whole section, so that its last bar alone differs.
            whole_part = composer_text.MSG_PART_OF_SECTION.format(at.name, composer_text.MSG_PART_OF_SECTION.format(role[ROLE], leaves[joins.TAIL]))
            self._parts[whole_part] = {**self._parts[figure], notation.LINES: with_tail(bars=self._parts[figure][notation.LINES], count=at.bars, tail=leaves[joins.TAIL], eighths=leaves.get(joins.TAIL_EIGHTHS, 0))}
            self._shaped.append(whole_part)
            figure = whole_part
        at.play[role[ROLE]] = {PART: figure, CHAINS: [chain]}

    def _play_tune(self, at, *, role):
        """Have a player of lines play the section's tune: one written by hand, or the lines given or sketched for the player, the one part each time a tune returns note for note."""
        own_tune = (self._song.get(OWN_TUNES, {}).get(at.section[KIND]) or self._song.get(TAKEN_TUNES, {}).get(at.section[KIND])) if role is at.tune_role else None
        if at.section[KIND] == INTRO_KIND and self._song.get(OWN_INTRO, {}).get(role[ROLE]) is not None:
            own_tune = self._song[OWN_INTRO][role[ROLE]]
        own_solo = self._song.get(OWN_SOLOS, {}).get(self._solos_met, {}).get(role[ROLE]) if at.section[KIND] == SOLO_KIND else None
        if at.section[KIND] == INTRO_KIND and self._song.get(OWN_INTROS, {}).get(self._intros_met, {}).get(role[ROLE]) is not None:
            # One part of an intro keeps notes of its own, as one solo does, named for its scene.
            own_solo = self._song[OWN_INTROS][self._intros_met][role[ROLE]]
        if own_solo is not None:
            own_tune = own_solo
        if own_tune is not None:
            # A tune written by hand is played as written by every section of its kind, and nothing here writes one over it;
            # a solo written by hand is that one solo's alone.
            part = composer_text.MSG_OWN_TUNE_PART.format(kind=at.section[KIND] if own_solo is None else at.scene_name)
            self._parts.setdefault(part, {RAW: copy.deepcopy(own_tune)})
            # The notes keep the chains the player's written part would run: the tune's phrasing is the tune's player's alone.
            at.play[role[ROLE]] = {PART: part, ONCE: True, CHAINS: [composer_text.MSG_TIMING_CHAIN.format(role[ROLE]), *(self._phrased if role is at.tune_role else [])]}
            return
        part = composer_text.MSG_PART_OF_SECTION.format(at.name, role[ROLE])
        if part not in self._parts:
            lines = self._lines_of(at, role=role)
            if notation.is_silent(lines):
                return
            written = tune_part(lines=lines, role=role, meter=self._meter, grid=self._habits[melody.GRID])
            # A tune that returns note for note, as a chorus's, is the one part each time, where the song's sections are planned.
            same = self._same_tunes.get((role[ROLE], repr(written))) if DRAWN_AS in at.section else None
            if same is not None:
                part = same
            else:
                self._parts[part] = written
                self._shaped.append(part)
                self._same_tunes[(role[ROLE], repr(written))] = part
        if part in self._parts:
            at.play[role[ROLE]] = {PART: part, ONCE: True, CHAINS: [composer_text.MSG_TIMING_CHAIN.format(role[ROLE]), *(self._phrased if role is at.tune_role else [])]}

    def as_input(self):
        """Return the song as arranged, a MacroComposer input: its tracks, parts, generators, chains and the scenes of its form."""
        generators = {Section.FOLLOW_CHORDS: {composer_text.MSG_FOLLOW_CHORDS_NAME: {FollowChordsSetting.CHORDS_FROM: composer_text.MSG_CHORDS_TRACK}}, **self._extra}
        if self._phrased:
            # The tune is delivered as a player would deliver it, by one Phrasing every clip of the tune runs after its timing.
            generators[Section.PHRASINGS] = {composer_text.MSG_TUNE_PHRASING_NAME: dict(self._song[TUNE_PHRASING])}
            self._chains[composer_text.MSG_TUNE_PHRASING_NAME] = [{GeneratorKind.PHRASING: composer_text.MSG_TUNE_PHRASING_NAME}]
        if self._style[GENRE] not in band.GENRES_WITHOUT_MUSICIANS:
            # Each player's clips are played by the player's Musician, first in their chains, and every piece of the kit by the drummer's.
            usual_tune = next((role[ROLE] for role, entry in self._pitched if FIGURE not in entry and not role.get(ANSWERS)), None)
            tune_track = self._song.get(TUNE_BY_SONG, usual_tune)
            members = [band.BandMember(track=role[ROLE], player=role.get(PLAYER), backing=FIGURE in entry, answers=bool(role.get(ANSWERS)), sound=self._instruments.get(self._tracks[role[ROLE]])) for role, entry in self._pitched]
            musicians, musician_of = band.band_of(members=members, drummer=drummer_role(self._roles), drum_tracks=self._drum_tracks, tune_track=tune_track if tune_track in self._tracks else None, own=self._song.get(MUSICIANS, {}))
            heard = set()
            for scene in self._form:
                for track, clip in scene[PLAY].items():
                    if track in musician_of:
                        clip = {PART: clip} if isinstance(clip, str) else clip
                        scene[PLAY][track] = {**clip, CHAINS: [musician_of[track], *clip.get(CHAINS, [])]}
                        heard.add(musician_of[track])
            generators[Section.MUSICIANS] = {name: settings for name, settings in musicians.items() if name in heard}
            self._chains.update({name: [{GeneratorKind.MUSICIAN: name}] for name in heard})
        if self._progressions:
            generators[PROGRESSIONS] = self._progressions
        if any(role.get(VOICE_LEADING) for role, _ in self._pitched):
            generators[VOICE_LEADINGS] = {NEAR: dict(NEAR_VOICES)}
        said = '\n'.join(band_said(style=self._style, song=self._song, roles=self._roles) + [composer_text.MSG_MADE_PICK.format(trait, value) for trait, value in self._picks.items()])
        # A piece of the kit that sounds as a General MIDI sound is a track with an instrument of its own, and no drum track.
        own_sounds = {piece: sounds_as[PLAYED_SOUND] for piece, sounds_as in self._song.get(PIECE_SOUNDS, {}).items() if PLAYED_SOUND in sounds_as and piece in self._tracks}
        for piece, sound in own_sounds.items():
            self._instruments[composer_text.MSG_PIECE_INSTRUMENT.format(piece)] = sound
            self._tracks[piece] = composer_text.MSG_PIECE_INSTRUMENT.format(piece)
        given = {
            NAME: self._song[NAME], TITLE: self._song[TITLE], DESCRIPTION: self._song.get(DESCRIPTION, self._song[TITLE]), GENRE: self._style[GENRE], SUBGENRE: self._song[TEMPLATE], VARIANT: self._song.get(VARIANT),
            NOTES: composer_text.MSG_MADE_SONG_NOTES.format(title=self._song[TITLE], style=self._style[TITLE], template=self._song[TEMPLATE], picks=said, form='\n'.join(self._notes)),
            SCALES: {self._scale: {ROOT: self._song[KEY][ROOT], TYPE: self._scale_type}, **self._more_scales}, SCALE: self._scale, TEMPO: self._tempo,
            FEEL: self._style[FEEL], SHAPED: self._shaped, INSTRUMENTS: self._instruments, TRACKS: self._tracks, DRUM_TRACKS: [piece for piece in self._drum_tracks if piece not in own_sounds], MUTED_TRACKS: [composer_text.MSG_CHORDS_TRACK], GENERATORS: generators, CHAINS: self._chains,
            PARTS: self._parts, FORM: self._form,
        }
        groove = self._song.get(GROOVE, self._style.get(GROOVE))
        if groove and groove != NO_GROOVE:
            given[GROOVE] = groove
        if self._song.get(DYNAMICS):
            # How far the feel moves each track's notes: a player's own track, and for the drummer every piece of the kit.
            of_tracks = {role[ROLE]: self._song[DYNAMICS][role[ROLE]] for role in self._roles if role[ROLE] in self._song[DYNAMICS] and role[ROLE] in self._tracks}
            if drummer_role(self._roles) in self._song[DYNAMICS]:
                of_tracks.update({piece: self._song[DYNAMICS][drummer_role(self._roles)] for piece in self._drum_tracks})
            given[DYNAMICS] = of_tracks
        if self._meter != COMMON_TIME:
            given[TIME_SIGNATURE] = self._meter
        return given


def arranged(*, style, song):
    """A song's picks as a MacroComposer input."""
    return Arrangement(style=style, song=song).as_input()


def _level_at(*, marks, place):
    """Return how loud a decoration's drum hits at a step: an accent, loud, soft, a ghost note, or none."""
    return next((level for level in (notation.ACCENT, notation.LOUD, notation.SOFT, notation.GHOST) if place in marks.get(level, [])), notation.NONE)


def _bar_of_chords(*, chord, shared):
    """Return a written bar's chord, or its two chords where two share the bar and the progression keeps them."""
    if shared and shares_a_bar(chord):
        return [chord_of(half) for half in chord]
    return chord_of(chord)
