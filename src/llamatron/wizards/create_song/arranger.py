# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The arranger: a song's picks and a style template made into a song wizard input, a whole song.

A style template lists a style's traits, each with its values and how common each is; a value of a trait a band plays holds
the bar it plays: a drum's hits, or a figure of notes written over chord one, which a Progression moves through the song's
chords. A song's picks say which template of the style it starts from, the picks it changes, its key, its tempo, its
sections with their chords and its form. The arranger decides nothing but the tune, and that only where the song gives none:
it then sketches one by rule from the style's melody habits and the song's seed (melody.py). What it writes is an input the
song wizard composes, so every choice can be read and changed there.
"""

import copy
from fractions import Fraction
import functools
import math
import os
import random
import zlib

from llamatron.engine.generators import chords as chords_plugin, musician as musician_plugin, phrasing as phrasing_plugin
from llamatron.engine.generators.chords import model as chords_model
from llamatron.engine.generators.chords.model import ChordsSetting
from llamatron.model.file.checks import in_whole_notes
from llamatron.model.file.safe_yaml import load_safely
from llamatron.model.objects.named_scale import scale_type_called
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import ChordSymbol, PatternSetting, Row, SceneSetting, VelocitySetting
from llamatron.music_theory.fundamentals import chord_shapes
from llamatron.user_strings import errors, labels, song_wizard as wizard_text
from llamatron.wizards.create_song import band, breaks, characters, drum_solo, interplay, joins, loudness, melody, notation, riffs as riffs_values, shaping, song_plan, wizard_names
from llamatron.wizards.create_song.characters import character_of, held_to, label_of, level_of
from llamatron.wizards.create_song.heavy_riffs import flattened_in
from llamatron.wizards.create_song.interplay import UnderLead
from llamatron.wizards.create_song.joins import with_tail
from llamatron.wizards.create_song.loudness import drum_levels, in_proportion, note_levels, scaled, spread, with_own
from llamatron.wizards.create_song.melody import has_hook, plan_as_asked, plan_with_hook_placed, plan_with_tag, sketched
from llamatron.wizards.create_song.notation import clamped, drum_rows
from llamatron.wizards.create_song.players import player_name
from llamatron.wizards.create_song.riffs import accent_bars, bars_of as riff_bars_of, bars_played, held_bar, line_of as riff_line_of, single, split_bars
from llamatron.wizards.create_song.scene_changes import as_percentages
from llamatron.wizards.create_song.shaping import is_compound
from llamatron.wizards.create_song.song_plan import SongPlan

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
# What the song wizard's input names.
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
ACCIDENTALS = 'accidentals'
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
HOME_CHORDS = {chord_shapes.MAJOR: ChordSymbol.MAJOR, chord_shapes.MINOR: ChordSymbol.MINOR, chord_shapes.DIMINISHED: ChordSymbol.DIMINISHED, chord_shapes.AUGMENTED: ChordSymbol.AUGMENTED}
FOLLOWS_THE_CHORDS = {chords_plugin.NAME: wizard_text.MSG_FOLLOW_CHORDS_NAME}
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
# The Timing generator a track's rush and drag are written in, its section, and its parts' settings, rush_steps and the like.
TIMING = 'timing'
TIMINGS = 'timings'
RAW = 'raw'
AMOUNT = 'amount'
GENERATOR_STEPS = 'steps'
PART_SETTING = '{part}_{setting}'
GUITARIFIES = 'guitarifies'
# The set's section that holds each kind of generator a value may bring.
SECTION_OF_KIND = {'guitarify': 'guitarifies', 'arp': 'arps'}
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
    """Return names as one line of text, in order, with a comma between."""
    words = [str(name) for name in names]
    return ', '.join(sorted(words))


def values_of(*, style, trait):
    return {entry[VALUE]: entry for entry in style[TRAITS][trait]} if isinstance(style[TRAITS].get(trait), list) else {}


def fits(*, entry, picks):
    """Return whether a value fits the picks: every trait it needs, of those picked, is picked the way it needs."""
    needs = entry.get(NEEDS, {})
    for trait, wanted in needs.items():
        if trait in picks and picks[trait] != wanted:
            return False
    return True


def picked(*, style, song):
    """Return every trait's pick: the song's own, else its template's, else the commonest value that fits what is picked."""
    templates = style[TEMPLATES]
    if song[TEMPLATE] not in templates:
        raise ValueError(errors.ERR_NO_STYLE_KIND.format(style[NAME], song[TEMPLATE], listed(templates)))
    picks = dict(templates[song[TEMPLATE]])
    picks.update(song.get(PICKS, {}))
    for trait in style[TRAITS]:
        values = values_of(style=style, trait=trait)
        if not values:
            continue
        if trait not in picks:
            picks[trait] = _commonest_fitting(values=values, picks=picks)
        if picks[trait] not in values:
            raise ValueError(errors.ERR_NO_TRAIT_VALUE.format(trait, picks[trait], listed(values)))
    _refuse_unmet_needs(style=style, picks=picks)
    return picks


def _commonest_fitting(*, values, picks):
    """Return the commonest of a trait's values that fits the picks."""
    fitting = [entry for entry in values.values() if fits(entry=entry, picks=picks)]
    commonest = max(fitting, key=share_of)
    return commonest[VALUE]


def _refuse_unmet_needs(*, style, picks):
    """Refuse picks where a value picked needs another trait picked a way it is not."""
    for trait, value in picks.items():
        ways = values_of(style=style, trait=trait)
        entry = ways.get(value, {})
        for needed, wanted in entry.get(NEEDS, {}).items():
            if picks.get(needed) != wanted:
                raise ValueError(errors.ERR_PICK_NEEDS.format(trait, value, needed, wanted, picks.get(needed)))


def style_names():
    """Return the names of the style templates there are."""
    names = []
    for name in os.listdir(STYLE_TEMPLATES):
        if name.endswith(STYLE_SUFFIX):
            names.append(name[:-len(STYLE_SUFFIX)])
    return sorted(names)


def style_named(name):
    """A style template, read from its file."""
    with open(os.path.join(STYLE_TEMPLATES, name + STYLE_SUFFIX), encoding=FILE_ENCODING) as file:
        return load_safely(file)


def player_of(*, style, instrument, character):
    """Return what a style says of an instrument's player of a character, or nothing."""
    players = style.get(PLAYERS, {})
    return characters.player_of(levels=players.get(instrument, {}), character=character)


def players_in(*, style, roles, levels, section):
    """Return each role's player in a section: the song's, held to the complexity the section allows the instrument."""
    players = {}
    for role in roles:
        instrument = role.get(PLAYER)
        character = character_in(levels=levels, instrument=instrument, section=section)
        players[role[ROLE]] = player_of(style=style, instrument=instrument, character=character)
    return players


def character_in(*, levels, instrument, section):
    """Return the character an instrument's player plays with in a section, or nothing where the song names no player for the
    instrument: the song's, a level or the places of its gauges, held to the level the section allows the instrument."""
    levels_here = section.get(LEVELS_HERE, {})
    here = levels_here.get(instrument)
    if here is not None:
        return character_of(here)
    if instrument not in levels:
        return None
    allowed = section.get(ALLOWS, {})
    return held_to(character=character_of(levels[instrument]), allowed=allowed.get(instrument))


def timing_generators(*, move):
    """A track's Timing generator: its Rush and its Drag each moving every step by the amount the player gives, a part the player
    gives none doing nothing, there to be changed."""
    settings = {}
    for part in (RUSH, DRAG):
        if part in move:
            settings[PART_SETTING.format(part=part, setting=GENERATOR_STEPS)] = [True]
            settings[PART_SETTING.format(part=part, setting=AMOUNT)] = move[part]
    return settings


def drum_pattern(part):
    """Return a drum's part as a pattern."""
    return drum_rows(
        drum=part[notation.DRUM],
        hits=part[notation.HITS],
        loud=part[notation.LOUD],
        soft=part[wizard_names.SOFT],
        step_size=part[notation.STEP],
        accent=part.get(wizard_names.ACCENT),
        ghost=part.get(wizard_names.GHOST),
    )


def uneven(*, pattern, by, dice):
    """A drum's pattern with hits that each differ a little in loudness, as a person's do."""
    return {**pattern, notation.VELOCITY: [None if loud is None else clamped(loud + dice.randint(-by, by)) for loud in pattern[notation.VELOCITY]]}


def leaning(*, pattern, profile, meter, dynamics):
    """Return a drum's pattern with the strokes on each beat louder or softer by the style's lean on that beat, as far as the
    drummer's dynamics say."""
    size = Fraction(pattern[notation.STEP_SIZE])
    beat = shaping.SIMPLE_BEAT
    if is_compound(meter):
        beat = shaping.COMPOUND_BEAT
    velocities = []
    for place, loud in enumerate(pattern[notation.VELOCITY]):
        count = ((place * size) % bar_length(meter)) / beat
        if loud is not None and count.denominator == 1:
            move = scaled(move=profile[int(count) % len(profile)], dynamics=dynamics)
            loud = clamped(loud + move)
        velocities.append(loud)
    leaned = dict(pattern)
    leaned[notation.VELOCITY] = velocities
    return leaned


def drummer_role(roles):
    """Return the name of the role that plays the drums."""
    for role in roles:
        if role.get(DRUMS):
            return role[ROLE]
    return DRUMS


def loud_style(*, style, song, roles):
    """Return a style with each drum's four levels worked out, as the song has them: the kit's levels where the song gives its
    own, every piece moved in proportion, and each level as far from the normal one as the drummer's dynamics say."""
    drummer = drummer_role(roles)
    written = style[LOUDNESS]
    kit = drum_levels(written[DRUMS])
    song_loudness = song.get(LOUDNESS, {})
    chosen = with_own(levels=kit, own=song_loudness.get(drummer))
    song_dynamics = song.get(DYNAMICS, {})
    dynamics = song_dynamics.get(drummer, loudness.USUAL_DYNAMICS)
    pieces = {}
    for piece, given in written.items():
        moved = in_proportion(levels=drum_levels(given), kit=kit, chosen=chosen)
        pieces[piece] = spread(levels=moved, dynamics=dynamics)
    loud = dict(style)
    loud[LOUDNESS] = pieces
    return loud


def loud_role(*, role, song):
    """Return a player of notes as loud as the song has the player: the role with the song's levels and dynamics for it, where
    it gives any."""
    song_loudness = song.get(LOUDNESS, {})
    own = song_loudness.get(role[ROLE])
    song_dynamics = song.get(DYNAMICS, {})
    dynamics = song_dynamics.get(role[ROLE])
    if notation.VELOCITY not in role or (own is None and dynamics is None):
        return role
    if dynamics is None:
        dynamics = loudness.USUAL_DYNAMICS
    chosen = with_own(levels=note_levels(role[notation.VELOCITY]), own=own)
    levels = spread(levels=chosen, dynamics=dynamics)
    loud = dict(role)
    loud[notation.VELOCITY] = levels[wizard_names.NORMAL]
    loud[LEVELS_OF_ROLE] = {level: levels[level] for level in (wizard_names.ACCENT, wizard_names.SOFT, wizard_names.GHOST)}
    return loud


def voice_of(role):
    """How loud a player's part is: the velocity, and the player's other levels where the song gives any."""
    return {notation.VELOCITY: role[notation.VELOCITY], **role.get(LEVELS_OF_ROLE, {})}


def struck(*, levels, hits):
    """Return how loud a drum's part is: its normal and soft strokes, and its accent and ghost note where its hits have any."""
    struck_levels = {notation.LOUD: levels[wizard_names.NORMAL], wizard_names.SOFT: levels[wizard_names.SOFT]}
    for level in (wizard_names.ACCENT, wizard_names.GHOST):
        if level in hits:
            struck_levels[level] = levels[level]
    return struck_levels


def share_of(entry):
    return entry[SHARE]


def share_in(*, style, entry, template):
    """Return how common a value is in one of a style's templates: its share in the template's family where the style has
    families and the value says how common it is in each, or its share in the style as a whole; a value that says how common
    it is in the template itself is that common."""
    by_template = entry.get(BY, {})
    if template in by_template:
        return by_template[template]
    families = style.get(FAMILIES, {})
    by_family = entry.get(BY_FAMILY, {})
    return by_family.get(families.get(template), entry[SHARE])


def said_over(*, usual, own):
    """What a style says with one template's own words laid over it: a dictionary's entries one by one, anything else replaced whole."""
    if not isinstance(usual, dict) or not isinstance(own, dict):
        return own
    return {**usual, **{key: said_over(usual=usual[key], own=value) if key in usual else value for key, value in own.items()}}


STYLES_IN_TEMPLATES = {}


def variants_of(*, style, template):
    """Return the kinds of song a style's template holds, the commonest first, or none."""
    variants = style.get(VARIANTS, {})
    return sorted(variants.get(template, []), key=share_of, reverse=True)


def variant_named(*, style, template, variant):
    """Return one kind of song of a template by its name, or None for a name the template has no kind of, as a song saved
    before the kind was renamed."""
    for entry in variants_of(style=style, template=template):
        if entry[NAME] == variant:
            return entry
    return None


def style_in(*, style, template, variant=None):
    """Return a style as one of its templates has it: what the style says by_subgenre for the template laid over the style,
    and then what the song's kind says laid over that, worked out once. A style that says nothing of the template or the
    kind, or one already so laid over, is returned as it is."""
    subgenres = style.get(BY_SUBGENRE, {})
    own = subgenres.get(template)
    kind = variant_named(style=style, template=template, variant=variant)
    if not own and kind is None:
        return style
    kind_name = None
    if kind is not None:
        kind_name = variant
    key = (style[NAME], template, kind_name)
    if key not in STYLES_IN_TEMPLATES:
        STYLES_IN_TEMPLATES[key] = _laid_over_style(style=style, own=own, kind=kind)
    return STYLES_IN_TEMPLATES[key]


def _laid_over_style(*, style, own, kind):
    """Return a style with what it says of a template laid over it, and then what a kind of song says."""
    laid = style
    if own:
        usual = {name: value for name, value in style.items() if name != BY_SUBGENRE}
        laid = said_over(usual=usual, own=own)
    if kind is not None:
        laid = said_over(usual=laid, own=kind.get(STYLE, {}))
    return dict(laid)


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
    """Return a list of chords as a Progression's settings; where a bar has two chords and nothing says how long a chord
    lasts, each chord lasts half a bar, so long as a Progression holds that many."""
    if not every and _shares_any_bar(chords) and fits_by_halves(chords):
        chords = halves_of(chords)
        every = half_bar_of(meter)
    degrees = []
    marks = []
    for chord in chords:
        parsed = chord_of(chord)
        degrees.append(parsed[notation.DEGREE])
        marks.append(ACCIDENTAL_MARKS.get(parsed.get(notation.ACCIDENTAL)))
    made = {wizard_names.ARRANGER_CHORDS: degrees}
    if any(marks):
        made[ACCIDENTALS] = marks
    if every:
        made[EVERY] = every
    return made


def _shares_any_bar(chords):
    """Return whether any of the chords is two that share a bar."""
    for chord in chords:
        if shares_a_bar(chord):
            return True
    return False


def home_chord_of(scale_type):
    """The chord symbol of the chord a scale type builds on its first note, or nothing where its third and fifth name no plain chord or it has not seven notes."""
    shape = scale_type_called(scale_type).value
    if len(shape) != NOTES_OF_A_SCALE_WITH_TRIADS:
        return None
    return HOME_CHORDS.get((shape[THIRD_PLACE], shape[FIFTH_PLACE]))


def chords_written(*, progression, meter, scale_type):
    """Return a progression's chords as a pattern of the chords track, a step a chord, each a triad of the scale on its degree;
    a chord on a degree with a sharp or a flat is the scale's home chord moved there, as a Progression plays it. Nothing where
    a chord lasts longer than a step can, or such a chord's kind cannot be named: the chords track then makes its chords with
    the Progression."""
    bar = Fraction(meter)
    lasts = bar
    if EVERY in progression:
        length = in_whole_notes(time=progression[EVERY], bar=bar)
        lasts = Fraction(str(length))
    degrees = progression[wizard_names.ARRANGER_CHORDS]
    marks = progression.get(ACCIDENTALS) or [None] * len(degrees)
    home = home_chord_of(scale_type)
    if lasts > limits.MAX_STEP_SIZE or (any(marks) and home is None):
        return None
    chords = []
    for mark in marks:
        if mark is None:
            chords.append(SCALE_TRIAD)
        else:
            chords.append(home)
    written = {PatternSetting.STEPS: len(degrees), PatternSetting.STEP_SIZE: str(lasts), Row.DEGREE: list(degrees), Row.CHORD: chords}
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
    cut = picks.get(BREAK_CUT, wizard_names.LEAST_CUT)
    if isinstance(cut, bool) or not isinstance(cut, int) or not wizard_names.LEAST_CUT <= cut <= wizard_names.MOST_CUT:
        raise ValueError(errors.ERR_BREAK_CUT.format(wizard_names.LEAST_CUT, wizard_names.MOST_CUT, cut))
    return cut


def pieces_played(song):
    """Return what each remapped piece of a song's kit plays, as the drum's name or the note's number drum_rows takes, each checked."""
    played = {}
    piece_sounds = song.get(PIECE_SOUNDS, {})
    for piece, sounds_as in piece_sounds.items():
        if _plays_another_drum(sounds_as):
            played[piece] = sounds_as[PLAYED_DRUM]
        elif _plays_a_sound_on_a_note(sounds_as):
            played[piece] = sounds_as[PLAYED_NOTE]
        else:
            raise ValueError(errors.ERR_PIECE_SOUND.format(piece, sounds_as))
    return played


def _plays_another_drum(sounds_as):
    """Return whether a piece of the kit is played as another drum of the kit."""
    return set(sounds_as) == {PLAYED_DRUM} and sounds_as[PLAYED_DRUM] in wizard_names.NOTATION_KIT


def _plays_a_sound_on_a_note(sounds_as):
    """Return whether a piece of the kit is played as a General MIDI sound on a note, each in range."""
    if set(sounds_as) != {PLAYED_SOUND, PLAYED_NOTE}:
        return False
    if not whole(value=sounds_as[PLAYED_SOUND], low=limits.MIN_GM_SOUND, high=limits.MAX_GM_SOUND):
        return False
    return whole(value=sounds_as[PLAYED_NOTE], low=LOWEST_NOTE, high=HIGHEST_NOTE)


def whole(*, value, low, high):
    """Whether a value is an integer within a range."""
    return not isinstance(value, bool) and isinstance(value, int) and low <= value <= high



def fill_named(*, style, name):
    """Return the fill of a name, each drum's hits, or no fill for no name or a name the style lacks."""
    fills = values_of(style=style, trait=FILLS)
    fill = fills.get(name, {})
    return fill.get(characters.FILL, {})


def solo_parts(*, style, bars, seed, kit):
    """Return a drum solo's parts, a part for each piece of the kit that sounds in it."""
    written = style[LOUDNESS]
    kit = kit or {}
    solo = drum_solo.solo_hits(bars=bars, seed=seed)
    parts = {}
    for piece, hits in solo.items():
        # A style as written says a drum's normal stroke alone, and a song's style all four levels.
        levels = drum_levels(written.get(piece, written[DRUMS]))
        part = {notation.DRUM: kit.get(piece, piece), notation.STEP: drum_solo.STEP}
        part.update(struck(levels=levels, hits=hits))
        part[notation.HITS] = hits
        parts[piece] = part
    return parts


def frozen(value):
    """Return plain data as something that can be a key."""
    if isinstance(value, dict):
        pairs = [(name, frozen(inner)) for name, inner in value.items()]
        return tuple(sorted(pairs))
    if isinstance(value, list):
        values = [frozen(inner) for inner in value]
        return tuple(values)
    return value


def one_hit(*, style, meter, drum, played):
    """Return one bar in which a piece of the kit is hit once, on the first beat, as the drum or the note the song has the piece play."""
    written = style[LOUDNESS]
    levels = written.get(drum, written[DRUMS])
    loud = levels[wizard_names.NORMAL]
    eighths = int(bar_length(meter) * EIGHTHS_IN_WHOLE)
    hits = [notation.LOUD] + [notation.NONE] * (eighths - 1)
    return {notation.DRUM: played.get(drum, drum), notation.STEP: EIGHTH, notation.LOUD: loud, wizard_names.SOFT: loud, notation.HITS: hits}


def lasts(note):
    """How many steps a note or a rest of a figure lasts."""
    return note.get(notation.REST, note.get(notation.STEPS, 0))


def with_ending(*, bar, ends):
    """Return a figure's bar whose last steps are a decoration's notes: what the bar played before them stays, a note they cut
    into shortened."""
    room = _length_of(bar) - _length_of(ends)
    kept = []
    for note in bar:
        if room <= 0:
            break
        length = min(lasts(note), room)
        kept.append(_lasting(note=note, length=length))
        room -= length
    for note in ends:
        kept.append(dict(note))
    return kept


def _length_of(notes):
    """Return how many steps notes last together."""
    total = 0
    for note in notes:
        total += lasts(note)
    return total


def _lasting(*, note, length):
    """Return a copy of a note or a rest lasting a length."""
    lasting = dict(note)
    if notation.REST in note:
        lasting[notation.REST] = length
    else:
        lasting[notation.STEPS] = length
    return lasting


def ending_fits(*, variation, grid, meter):
    """Return whether a player's ending can be laid on a figure: it is written for the meter, or for any, and one of the two
    grids divides the other, so that the finer holds both."""
    needs = variation.get(NEEDS, {})
    if ENDS not in variation or needs.get(METER, meter) != meter:
        return False
    return grid % variation[melody.GRID] == 0 or variation[melody.GRID] % grid == 0


def stretched(*, notes, by):
    """Notes written again on a grid so many times finer."""
    return [{**note, (notation.REST if notation.REST in note else notation.STEPS): lasts(note) * by} for note in notes]


def decorated_figure(*, bars, player, phrase_bars, meter):
    """Return a figure as a player plays it: a phrase of its bars, the bars the player varies ending in the player's own notes,
    on the finest grid of the figure's and the endings'. A player who varies nothing plays the figure as written, and an
    ending written for another meter, or on a grid that neither divides the figure's nor is divided by it, is left out."""
    grid = _length_of(bars[0])
    variations = player.get(characters.VARIES, [])
    fitting = [variation for variation in variations if ending_fits(variation=variation, grid=grid, meter=meter)]
    if not fitting or phrase_bars % len(bars):
        return [notation.copied_line(bar) for bar in bars]
    grids = [grid]
    for variation in fitting:
        grids.append(variation[melody.GRID])
    finest = max(grids)
    fitting = [variation for variation in fitting if finest % variation[melody.GRID] == 0]
    phrase = []
    for count in range(phrase_bars):
        phrase.append(stretched(notes=bars[count % len(bars)], by=finest // grid))
    for variation in fitting:
        ends = stretched(notes=variation[ENDS], by=finest // variation[melody.GRID])
        for bar in variation[BARS]:
            phrase[bar - 1] = with_ending(bar=phrase[bar - 1], ends=ends)
    return phrase


def figure_part(*, entry, role, meter, player, phrase_bars):
    """Return a value's figure as a tune's part, as a player plays it; the figure's bars are its lines."""
    lines = decorated_figure(bars=entry[FIGURE], player=player, phrase_bars=phrase_bars, meter=meter)
    grid = _length_of(lines[0])
    part = {notation.STEP: step_of(meter=meter, grid=grid), notation.OCTAVE: role[notation.OCTAVE]}
    part.update(voice_of(role))
    part[notation.LINES] = lines
    return part


def held_part(*, role, meter, chord):
    """One bar of the home note or chord, held."""
    note = {notation.DEGREE: 1, notation.STEPS: int(bar_length(meter) * EIGHTHS_IN_WHOLE)}
    if chord:
        note[notation.CHORD] = HELD_CHORD
    return {notation.STEP: EIGHTH, notation.OCTAVE: role[notation.OCTAVE], **voice_of(role), notation.LINES: [[note]]}


def tune_part(*, lines, role, meter, grid):
    return {notation.STEP: step_of(meter=meter, grid=grid), notation.OCTAVE: role[notation.OCTAVE], **voice_of(role), notation.LINES: lines}


def habits_of(*, habits, player):
    """Return a style's melody habits as a player keeps them: a wider or narrower range, and the busier rhythms for a busy player."""
    kept = dict(habits)
    if melody.SPAN in player:
        kept[melody.SPAN] = player[melody.SPAN]
    if player.get(characters.BUSY):
        kept[melody.RHYTHMS] = habits[melody.ANSWER_RHYTHMS]
    return kept


def way_beside(*, beside, role, place, tune, section):
    """Return what the player beside the tune does in the section at a place of the form, or None for any other player, for a
    section nobody has the tune in, and for a section whose own plan already has the player answer every line, which is
    played as the plan writes it."""
    if role[ROLE] != beside.get(ROLE) or tune is None or tune is role:
        return None
    way = beside[BESIDE_WAYS][place]
    if way not in interplay.WAYS:
        raise ValueError(errors.ERR_NO_SUCH_WAY_BESIDE.format(way))
    if way == interplay.ANSWERS and role[ROLE] in section[PLAYS] and _plan_answers(section):
        return None
    return way


def _plan_answers(section):
    """Return whether a section's own plan has a line answered."""
    for entry in section.get(PLAN, []):
        if entry.get(melody.ANSWER):
            return True
    return False


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
    """Return who plays, for the notes: each instrument's player by name, with what the style says of the player."""
    played = set()
    for role in roles:
        played.add(role.get(PLAYER))
    said = []
    for instrument, complexity in song.get(PLAYERS, {}).items():
        if instrument in played:
            said.append(_player_said(style=style, instrument=instrument, complexity=complexity))
    return said


def _player_said(*, style, instrument, complexity):
    """Return what the notes say of an instrument's player: the player's name and what the style says of the player."""
    character = character_of(complexity)
    level = level_of(character)
    if level is None:
        # A player whose gauges were set one by one is nobody's preset, and is named by the instrument alone.
        return wizard_text.MSG_PLAYED_BY_OWN.format(instrument)
    player = player_of(style=style, instrument=instrument, character=character_of(level))
    name = player_name(instrument=instrument, complexity=level)
    said = wizard_text.MSG_PLAYED_BY.format(instrument, name, player.get(characters.SAYS, ''))
    return said.strip()


def sound_of(*, style, song, role, usual):
    """Return the name of the sound a player plays with: the song's own choice for the player, a General MIDI number, called by
    the style's name for that number where the style has one and by General MIDI's otherwise; or the sound the way of playing has."""
    role_sounds = song.get(ROLE_SOUNDS, {})
    number = role_sounds.get(role)
    if number is None:
        return usual
    named = [name for name, of_style in style[SOUNDS].items() if of_style == number]
    if usual in named:
        return usual
    if named:
        return named[0]
    general_midi = labels.MSG_GM_SOUNDS[number - limits.MIN_GM_SOUND]
    return general_midi.lower()


def section_of(*, name, style, song):
    """Return a section as the song describes it over what the style says of a section of its name, with the song's hooks
    placed and what it asks of its melodies laid over its plan."""
    sections_of_song = song.get(SECTIONS, {})
    of_song = sections_of_song.get(name, {})
    kind = of_song.get(KIND, name)
    kinds = style[SECTIONS]
    if kind not in kinds and not of_song:
        raise ValueError(errors.ERR_NO_SUCH_SECTION.format(name))
    section = dict(kinds.get(kind, {}))
    section.update(of_song)
    section[KIND] = kind
    _place_hooks(section=section, song=song)
    _lay_asks_over(section=section, song=song)
    return section


def _place_hooks(*, section, song):
    """Place the song's hooks in a section: the main one among the lines of the kind of section that says it, and the tag sung
    in its kind, by its singer, who then plays there."""
    kind = section[KIND]
    hooks = song.get(melody.HOOKS, {})
    main = hooks.get(melody.MAIN_HOOK, {})
    if main.get(melody.SUNG_IN) == kind and main.get(melody.PLACEMENT) and section.get(PLAN):
        section[PLAN] = plan_with_hook_placed(plan=section[PLAN], placement=main[melody.PLACEMENT])
    second = hooks.get(melody.SECOND_HOOK, {})
    if second.get(melody.SUNG_IN) == kind and not section.get(HELD):
        lines = section.get(BARS, BARS_IN_A_TAG_LINE) // BARS_IN_A_TAG_LINE
        section[PLAN] = plan_with_tag(plan=section.get(PLAN, []), lines=lines)
        players = [*section.get(PLAYS, []), second[melody.SUNG_BY]]
        section[PLAYS] = list(dict.fromkeys(players))


def _lay_asks_over(*, section, song):
    """Lay what the song asks of its melodies over a section's plan: for the whole song, and for its kind of section."""
    asks = song.get(melody.MELODY_ASKS)
    if not asks or not section.get(PLAN):
        return
    by_kind = asks.get(melody.BY_KIND, {})
    of_kind = by_kind.get(section[KIND], {})
    busy = of_kind.get(melody.LINE_BUSY, asks.get(melody.LINE_BUSY))
    section[PLAN] = plan_as_asked(plan=section[PLAN], height=of_kind.get(wizard_names.MELODY_HEIGHT), busy=busy, repeats=asks.get(melody.REPEATS))


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


def _section_chords(section, *, entry):
    """Return the chords a section plays: its own, else the progression's for its kind, else the progression's pattern."""
    by_section = entry.get(BY_SECTION, {})
    written = section.get(wizard_names.ARRANGER_CHORDS) or by_section.get(section[KIND]) or entry[PATTERN]
    return [chord_of(chord) for chord in written]


def _without_quiet_notes(hits):
    """Return a snare's hits with the soft strokes and ghost notes between the main ones left out."""
    kept = []
    for hit in hits:
        if hit in (wizard_names.SOFT, wizard_names.GHOST):
            kept.append(notation.NONE)
        else:
            kept.append(hit)
    return kept


def _figure_has_chords(entry):
    """Return whether a way of playing's figure plays a chord anywhere."""
    for bar in entry.get(FIGURE, []):
        for note in bar:
            if notation.CHORD in note:
                return True
    return False


def _with_chain_first(*, clip, chain):
    """Return a clip that runs a chain first, before its own."""
    if isinstance(clip, str):
        clip = {PART: clip}
    chained = dict(clip)
    chained[CHAINS] = [chain, *clip.get(CHAINS, [])]
    return chained


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
    is everything written, as a song wizard input.
    """

    __slots__ = ('_beside', '_chains', '_chord_entry', '_drum_tracks', '_drum_traits', '_drummer', '_drums_of', '_extra', '_form', '_form_names', '_habits', '_has_a_hook', '_instruments', '_intros_met', '_levels', '_met', '_meter', '_more_scales', '_no_drums', '_notes', '_parts', '_phrase_bars', '_phrased', '_picks', '_pieces_off', '_pitched', '_plans', '_played', '_playing', '_progressions', '_riff_eighths', '_riffs', '_roles', '_same_tunes', '_scale', '_scale_type', '_shaped', '_solos_met', '_song', '_style', '_tempo', '_timing', '_tracks', '_under', '_without')

    def __init__(self, *, style, song):
        self._song = song
        self._style = style_in(style=style, template=song[TEMPLATE], variant=song.get(VARIANT))
        self._read_style()
        self._plan_song()
        self._read_band()
        self._read_riffs()
        self._parts = {}
        self._write_drums()
        self._seat_players()
        self._read_form()
        for count, name in enumerate(self._form_names, start=1):
            self._write_section(count=count, name=name)

    def _read_style(self):
        """Read what the style and the song's picks say of the whole song: the meter, the tempo, the form, the band's roles as
        loud as the song has them, how long a phrase is, the chords, the key and the tune's habits."""
        self._picks = picked(style=self._style, song=self._song)
        self._meter = str(self._picks.get(METER, COMMON_TIME))
        self._tempo = tempo_of(style=self._style, song=self._song, picks=self._picks)
        self._form_names = form_of(style=self._style, song=self._song, meter=self._meter, tempo=self._tempo)
        self._roles = self._loud_roles()
        self._style = loud_style(style=self._style, song=self._song, roles=self._roles)
        self._phrase_bars = self._style.get(PHRASE_BARS, DEFAULT_PHRASE_BARS)
        chord_trait = self._style.get(CHORD_TRAIT_FIELD, CHORD_TRAIT)
        chord_ways = values_of(style=self._style, trait=chord_trait)
        self._chord_entry = chord_ways[self._picks[chord_trait]]
        key = self._song[KEY]
        self._scale_type = key.get(TYPE, self._chord_entry.get(SCALE_TYPE, MAJOR))
        self._scale = SCALE_NAME.format(key[ROOT], self._scale_type.capitalize())
        self._habits = self._habits_in_scale()

    def _loud_roles(self):
        """Return the band's roles as loud as the song has them, each an octave up in a song whose root sits low."""
        lift = 0
        if self._song[KEY][ROOT] in LOW_ROOTS:
            lift = 1
        roles = []
        for role in self._style[ROLES]:
            if notation.OCTAVE in role:
                role = dict(role)
                role[notation.OCTAVE] = role[notation.OCTAVE] + lift
            roles.append(loud_role(role=role, song=self._song))
        return roles

    def _habits_in_scale(self):
        """Return the tune's habits in the song's meter, with what the style says of its scale type laid over them: a minor song
        takes its minor notes and home, since the major notes read in a minor scale rest on the scale's third and sound like the
        major key beside it."""
        written = self._style[MELODY]
        habits = written
        if melody.GRID not in written:
            habits = written[self._meter]
        by_scale_type = habits.get(BY_SCALE_TYPE, {})
        laid = dict(habits)
        laid.update(by_scale_type.get(self._scale_type, {}))
        return laid

    def _plan_song(self):
        """Plan a song that asks for a plan: a section made for each place of its form, each saying what the plan worked out."""
        if self._song.get(song_plan.PLAN_OF_SONG) in (None, False):
            return
        chords_of = functools.partial(_section_chords, entry=self._chord_entry)
        plan = SongPlan(style=self._style, song=self._song, form_names=self._form_names, tempo=self._tempo, scale_type=self._scale_type, chords_of=chords_of)
        self._song = plan.planned()
        self._form_names = self._song[FORM]

    def _read_band(self):
        """Read the song's band: each instrument's player, who is left out, the kit's pieces left out and what each plays as,
        each player at the song's level, the drummer and the traits the drums have."""
        self._levels = self._song.get(PLAYERS, {})
        self._without = self._song.get(WITHOUT, [])
        self._pieces_off = self._song.get(WITHOUT_PIECES, [])
        self._played = pieces_played(self._song)
        self._playing = players_in(style=self._style, roles=self._roles, levels=self._levels, section={})
        self._no_drums = False
        self._drummer = {}
        self._drum_traits = []
        for role in self._roles:
            if role.get(DRUMS):
                self._no_drums = self._no_drums or role[ROLE] in self._without
                if not self._drummer:
                    self._drummer = self._playing[role[ROLE]]
            self._drum_traits.extend(role.get(DRUMS, []))
        self._drum_traits.append(FILLS)

    def _read_riffs(self):
        """Read the song's riffs, where it has any: first the song's own, or the one its kind of music is built on, then each
        riff added for kinds of section, by name, each drawn from a seed of its own; and how many eighths a bar of a riff lasts."""
        self._riff_eighths = int(bar_length(self._meter) * EIGHTHS_IN_WHOLE)
        seed = self._song.get(SEED, 0)
        first = self._song.get(riffs_values.RIFF, self._style.get(riffs_values.RIFF)) or {}
        self._riffs = [self.riff_made(riff=first, name=None, seed=seed)]
        for more in self._song.get(MORE_RIFFS, []):
            seed_text = MORE_RIFF_SEED.format(seed=seed, name=more.get(RIFF_DRAWN_AS, more[NAME]))
            more_seed = zlib.crc32(seed_text.encode())
            self._riffs.append(self.riff_made(riff=more, name=more[NAME], seed=more_seed))

    def _read_form(self):
        """Read what the form's sections are written from: each section's plan of lines, whether the song has a hook, the tune's
        phrasing and the player beside the tune; and start the form, its notes and what each section has met so far."""
        self._form = []
        self._notes = []
        self._met = {}
        self._same_tunes = {}
        # The scales of sections in a key or a scale of their own, by name.
        self._more_scales = {}
        self._plans = []
        for name in self._form_names:
            section = section_of(name=name, style=self._style, song=self._song)
            self._plans.append(section.get(PLAN, []))
        self._has_a_hook = self._asks_for_hook() and self._form_marks_a_hook()
        self._phrased = []
        if self._song.get(TUNE_PHRASING) is not None:
            self._phrased = [wizard_text.MSG_TUNE_PHRASING_NAME]
        self._beside = self._song.get(BESIDE, {})
        busy = self._beside.get(BESIDE_BUSY, interplay.USUAL_BUSY)
        self._under = UnderLead(busy=busy, habits=self._habits, grid=self._habits[melody.GRID], scale_type=self._scale_type, seed=self._song.get(SEED, 0))
        self._solos_met = 0
        self._intros_met = 0

    def _asks_for_hook(self):
        """Return whether the song, or its style, asks for a hook."""
        return bool(self._song.get(melody.HOOK, self._style.get(melody.HOOK, False)))

    def _form_marks_a_hook(self):
        """Return whether a section of the form marks a line of its plan as the hook."""
        for plan in self._plans:
            if has_hook(plan):
                return True
        return False

    def _drumming(self):
        """Return what every section's drums are written from."""
        # Imported here, since the drums are written with this module's helpers.
        from llamatron.wizards.create_song.drum_writing import SongDrumming
        own_fill = FILLS in self._song.get(PICKS, {})
        return SongDrumming(style=self._style, roles=self._roles, meter=self._meter, phrase_bars=self._phrase_bars, seed=self._song.get(SEED, 0), kit=self._played, own_fill=own_fill)

    def riff_made(self, *, riff, name, seed):
        """Return a riff of the song with its notes, its bars and the players of the band who play it."""
        notes = []
        if riff.get(riffs_values.RIFF_ROLES):
            notes = riff_line_of(riff=riff, seed=seed, eighths=self._riff_eighths, flattened=flattened_in(self._scale_type))
        players = []
        if notes:
            players = self._riff_players(riff)
        count = riff_bars_of(line=notes, eighths=self._riff_eighths) or 1
        split = split_bars(line=notes, eighths=self._riff_eighths)
        return SongRiff(name=name, riff=riff, notes=notes, count=count, split=split, players=players)

    def _riff_players(self, riff):
        """Return the players of the band who play a riff: those of its players in the band, not the drummer, whose part is a figure."""
        named = riff.get(riffs_values.RIFF_ROLES, [])
        players = []
        for role in self._roles:
            if role[ROLE] not in named or role[ROLE] in self._without or role.get(DRUMS):
                continue
            ways = values_of(style=self._style, trait=role[TRAIT])
            way = ways.get(self._picks.get(role[TRAIT]), {})
            if FIGURE in way:
                players.append(role[ROLE])
        return players

    def chords_in(self, section, *, shared=False):
        """Return a section's chords, its last bar set up for what follows where the section says so."""
        if section.get(HELD):
            bars = 1
        else:
            bars = section[BARS]
        by_section = self._chord_entry.get(BY_SECTION, {})
        written = section.get(wizard_names.ARRANGER_CHORDS) or by_section.get(section[KIND]) or self._chord_entry[PATTERN]
        # A bar of two chords is kept as its two for the progression, and is its first chord for whatever goes bar by bar.
        chords = [_bar_of_chords(chord=chord, shared=shared) for chord in written]
        every = section.get(EVERY, self._chord_entry.get(EVERY))
        if section.get(LAST_CHORD) is not None and not every and len(chords) <= bars:
            # The section's last bar is set up for what follows: the chords are written out a bar each, and the last bar takes the approach chord.
            chords = [chords[bar % len(chords)] for bar in range(bars - 1)]
            chords.append(chord_of(section[LAST_CHORD]))
        return chords

    def riff_bars_in(self, section, *, riff):
        """Return which bar of a riff each bar of a section plays, None where a riff that stays at home gives way to a held chord;
        nothing where the section has not the riff."""
        kinds = riff.riff.get(riffs_values.RIFF_KINDS, [])
        if not riff.players or section.get(HELD) or section[KIND] not in kinds or section[BARS] % riff.count:
            return []
        every = section.get(EVERY, self._chord_entry.get(EVERY))
        stays = riff.riff.get(wizard_names.RIFF_WITH_CHORDS) == wizard_names.STAYS_HOME and riff.split is not None and not every
        chords = self.chords_in(section)
        return bars_played(chords=chords, bars=section[BARS], count=riff.count, stays=stays)

    def riff_played(self, section, *, by=None, notes=None):
        """The first of the song's riffs that plays in a section, with which of its bars each bar of the section plays: the first a
        player plays where one is named, the first of one way of notes where a way is named; (None, []) where there is none."""
        for riff in self._riffs:
            if (by is None or by in riff.players) and (notes is None or riff.riff.get(wizard_names.RIFF_NOTES) == notes):
                bars = self.riff_bars_in(section, riff=riff)
                if bars:
                    return riff, bars
        return None, []

    def _write_drums(self):
        """Write the drums' parts, a set for each way the form's sections have the drummer play, and say which set each section plays."""
        drum_sets = {}
        self._drums_of = {}
        for name in self._form_names:
            section = section_of(name=name, style=self._style, song=self._song)
            if self._no_drums or section.get(HELD) or DRUMS not in section[PLAYS] or name in self._drums_of:
                continue
            self._drums_of[name] = self._drum_set(name=name, section=section, drum_sets=drum_sets)
        self._drum_tracks = []
        for pieces in self._drums_of.values():
            for piece in pieces:
                if piece not in self._drum_tracks:
                    self._drum_tracks.append(piece)
        timings = self._drummer.get(characters.TIMING, {})
        self._timing = {piece: timing_generators(move=timings.get(piece, {})) for piece in self._drum_tracks}

    def _drum_set(self, *, name, section, drum_sets):
        """Return the drum set a section plays, by piece, writing it where no section before asked for the same set."""
        character = character_in(levels=self._levels, instrument=DRUMS, section=section)
        level = None
        if character is not None:
            level = label_of(character)
        changed = self._drum_picks_in(section)
        plays = self._drummer_in(section=section, character=character)
        # A drum solo is written in four; in another meter the drummer plays the section alone as any other.
        solo = bool(section.get(DRUM_SOLO)) and self._meter == COMMON_TIME
        over, riff_key = self._kicked_riff_in(section=section, solo=solo)
        phrase = plays.get(characters.FILL_EVERY, self._phrase_bars) or self._phrase_bars
        key = (level, tuple(sorted(changed.items())), math.gcd(phrase, section[BARS]))
        key = self._drum_set_key(key=key, section=section, solo=solo, riff_key=riff_key)
        if key not in drum_sets:
            made = self._written_drums(section=section, changed=changed, plays=plays, solo=solo, over=over)
            leaves = section.get(wizard_names.JOINS_LEAVES)
            plain = leaves is None and not over and key[:2] == (self._usual_drummer(), ())
            named_by = section[KIND]
            if leaves is not None or over:
                named_by = name
            drum_sets[key] = self._named_drum_parts(section=section, made=made, plays=plays, plain=plain, named_by=named_by)
        return drum_sets[key]

    def _usual_drummer(self):
        """Return the level of the song's drummer, or None where the song names none."""
        if DRUMS not in self._levels:
            return None
        return label_of(character_of(self._levels[DRUMS]))

    def _drum_picks_in(self, section):
        """Return the picks of the drums a section changes, each where it fits the song's picks."""
        changed = {}
        for trait, value in section.get(PICKS, {}).items():
            if trait not in self._drum_traits:
                continue
            ways = values_of(style=self._style, trait=trait)
            if fits(entry=ways[value], picks=self._picks):
                changed[trait] = value
        return changed

    def _drummer_in(self, *, section, character):
        """Return how the drummer plays in a section: as the drummer of the character plays, with a fill as often as the song says
        where it says, never, at the end of each section, or every so many bars."""
        plays = player_of(style=self._style, instrument=DRUMS, character=character)
        if FILLS_COME not in self._song:
            return plays
        every = self._song[FILLS_COME]
        if every == EACH_SECTION:
            every = section[BARS]
        plays = dict(plays)
        plays[characters.FILL_EVERY] = every
        return plays

    def _kicked_riff_in(self, *, section, solo):
        """Return the kick's own bars where a riff of chords on its accents plays in a section, the kick striking each accent bar
        by bar, and what tells the section's set apart for it; or two Nones."""
        if solo:
            return None, None
        riff, riff_here = self.riff_played(section, notes=wizard_names.ACCENT_CHORDS)
        if riff is None:
            return None, None
        kick_bars = accent_bars(line=riff.notes, eighths=self._riff_eighths)
        kicked = []
        any_kicked = False
        for bar in riff_here:
            if bar is None:
                kicked.append(None)
            else:
                kicked.append(kick_bars[bar])
                any_kicked = True
        if not any_kicked:
            return None, None
        return {KICK: kicked}, (riffs_values.RIFF, riff.name, section[BARS], tuple(riff_here))

    def _drum_set_key(self, *, key, section, solo, riff_key):
        """Return what tells a section's drum set apart from another's: the drummer, the picks changed and the phrase; and for a
        planned section how it leaves and the fills and marker inside; a drum solo by its bars alone; and a riff the kick follows."""
        leaves = section.get(wizard_names.JOINS_LEAVES)
        if leaves is not None:
            key = key + (section[BARS], frozen(leaves), section.get(FILL_INSIDE), section.get(FILL_INSIDE_EVERY), frozen(section.get(MARKER)), section.get(MARKER_EVERY))
        if solo:
            key = (DRUM_SOLO, section[BARS])
        if riff_key is not None:
            key = key + riff_key
        return key

    def _written_drums(self, *, section, changed, plays, solo, over):
        """Return the parts of the kit a section plays, by piece: a drum solo's, or the section's drums."""
        # Imported here, since the drums are written with this module's helpers.
        from llamatron.wizards.create_song.drum_writing import SectionDrums, SectionToDrum
        if solo:
            return solo_parts(style=self._style, bars=section[BARS], seed=self._song.get(SEED, 0), kit=self._played)
        inside = {FILL_INSIDE: section.get(FILL_INSIDE), FILL_INSIDE_EVERY: section.get(FILL_INSIDE_EVERY), MARKER: section.get(MARKER), MARKER_EVERY: section.get(MARKER_EVERY)}
        picks = dict(self._picks)
        picks.update(changed)
        asked = SectionToDrum(picks=picks, drummer=plays, bars=section[BARS], leaves=section.get(wizard_names.JOINS_LEAVES), inside=inside, over=over)
        drums = SectionDrums(drumming=self._drumming(), asked=asked)
        return drums.parts()

    def _named_drum_parts(self, *, section, made, plays, plain, named_by):
        """Return the parts of a drum set by piece, each dressed and kept under its name: the piece's own where the set is plain
        and the piece has no part yet, else the piece's in the section; a piece of the kit switched off is left out, its strokes
        never moved to another piece."""
        solo = bool(section.get(DRUM_SOLO)) and self._meter == COMMON_TIME
        named = {}
        for piece, part in made.items():
            if piece in self._pieces_off:
                continue
            part = self._dressed_drum_part(piece=piece, part=part, plays=plays, solo=solo, kind=section[KIND])
            part_name = wizard_text.MSG_PART_OF_SECTION.format(piece, named_by)
            if plain and piece not in self._parts:
                part_name = piece
            self._parts[part_name] = part
            named[piece] = part_name
        return named

    def _dressed_drum_part(self, *, piece, part, plays, solo, kind):
        """Return a drum's part as the song plays it: the snare's quiet notes left out where the song says, and, where each stroke's
        loudness is its own, a pattern written out with the style's lean on each beat and then a person's unevenness on top."""
        if piece == SNARE and not self._song.get(QUIET_NOTES, True):
            part = dict(part)
            part[notation.HITS] = _without_quiet_notes(part[notation.HITS])
        profile = self._style.get(BEAT_LOUDNESS)
        leans = profile and not solo
        is_uneven = plays.get(characters.UNEVEN) and not solo
        if not leans and not is_uneven:
            return part
        pattern = drum_pattern(part)
        if leans:
            dynamics = self._song.get(DYNAMICS, {})
            drummer_dynamics = dynamics.get(drummer_role(self._roles), loudness.USUAL_DYNAMICS)
            pattern = leaning(pattern=pattern, profile=profile, meter=self._meter, dynamics=drummer_dynamics)
        if is_uneven:
            dice = random.Random(DRUM_SEED.format(self._song.get(SEED, 0), piece, kind))
            pattern = uneven(pattern=pattern, by=plays[characters.UNEVEN], dice=dice)
        return {RAW: pattern}

    def _seat_players(self):
        """Give each pitched player of the band a track and a sound, and write what a player plays wherever the player plays:
        the figure and the held chord."""
        # The order of a made song's tracks: the muted chords track first, then the chords, the lead and the backing, the bass, and the drums last.
        self._tracks = {wizard_text.MSG_CHORDS_TRACK: wizard_text.MSG_CHORDS_INSTRUMENT}
        self._instruments = {DRUM_KIT: None, wizard_text.MSG_CHORDS_INSTRUMENT: CHORDS_GUIDE_SOUND}
        self._progressions = {}
        self._chains = {}
        self._extra = {}
        self._shaped = []
        self._pitched = []
        for role in self._roles:
            if role.get(DRUMS) or role[ROLE] in self._without:
                continue
            ways = values_of(style=self._style, trait=role[TRAIT])
            entry = ways[self._picks[role[TRAIT]]]
            if SOUND in entry:
                self._seat(role=role, entry=entry)
        for track, settings in self._timing.items():
            self._time_track(track=track, settings=settings)
        for piece in self._drum_tracks:
            self._tracks[piece] = DRUM_KIT

    def _seat(self, *, role, entry):
        """Give one pitched player a track and a sound, its figure and its held chord, its timing and its way's generators."""
        name = role[ROLE]
        song_sounds = self._song.get(ROLE_SOUNDS, {})
        sound = sound_of(style=self._style, song=self._song, role=name, usual=entry[SOUND])
        self._instruments[sound] = self._style[SOUNDS].get(sound, song_sounds.get(name))
        self._tracks[name] = sound
        self._pitched.append((role, entry))
        player = self._playing[name]
        if FIGURE in entry:
            self._parts[name] = figure_part(entry=entry, role=role, meter=self._meter, player=player, phrase_bars=self._phrase_bars)
            self._shaped.append(name)
        held = wizard_text.MSG_PART_OF_SECTION.format(name, HELD)
        self._parts[held] = held_part(role=role, meter=self._meter, chord=_figure_has_chords(entry))
        self._timing[name] = timing_generators(move=player.get(characters.TIMING, {}))
        self._add_generators(role=role, entry=entry)

    def _add_generators(self, *, role, entry):
        """Give a player the generators its way of playing runs, a Guitarify with the player's own settings laid over it."""
        name = role[ROLE]
        for generator in entry.get(GENERATORS, []):
            for kind, settings in generator.items():
                of_kind = self._extra.setdefault(SECTION_OF_KIND[kind], {})
                of_kind[name] = dict(settings)
        guitarifies = self._extra.get(GUITARIFIES, {})
        if name in guitarifies:
            player = self._playing[name]
            guitarifies[name].update(player.get(characters.GUITARIFY_OF_PLAYER, {}))

    def _time_track(self, *, track, settings):
        """Give a track the chain that rushes and drags it, through a Timing generator of the track's name."""
        self._chains[wizard_text.MSG_TIMING_CHAIN.format(track)] = [{TIMING: track}]
        timings = self._extra.setdefault(TIMINGS, {})
        timings[track] = settings

    def _write_section(self, *, count, name):
        """Write one section of the form as a scene: who plays in it and which part each plays, writing the parts the section is
        the first to play. A section in which nothing of the song's picks plays, as pads alone where the song has no chord part,
        is left out."""
        at = self._section_in_hand(count=count, name=name)
        if at.section.get(HELD):
            self._hold(at)
        else:
            self._play_through(at)
        self._give_tune_away(at)
        if not at.play:
            self._met[at.name] -= 1
            return
        at.play[wizard_text.MSG_CHORDS_TRACK] = at.chords_played
        scene = {SCENE: at.scene_name, BARS: at.bars, PLAY: at.play}
        settings = self._scene_settings_of(at)
        if settings:
            scene[SETTINGS_OF_SCENE] = settings
        self._form.append(scene)
        self._notes.append(self._said_of_scene(at))

    def _section_in_hand(self, *, count, name):
        """Return a section of the form taken in hand: its scene's name, numbered from the second time it comes, its bars and its
        chords, counting the solos and the intros met so far."""
        at = SectionInHand(count=count, name=name)
        at.section = section_of(name=name, style=self._style, song=self._song)
        self._met[name] = self._met.get(name, 0) + 1
        if at.section[KIND] == SOLO_KIND:
            self._solos_met += 1
        if at.section[KIND] == INTRO_KIND:
            self._intros_met += 1
        at.scene_name = name
        if self._met[name] > 1:
            at.scene_name = wizard_text.MSG_REPEATED_SCENE.format(name, self._met[name])
        if at.section.get(HELD):
            at.bars = 1
        else:
            at.bars = at.section[BARS]
        at.chords = self.chords_in(at.section)
        return at

    def _play_through(self, at):
        """Write a section the band plays through: the drums, the chords, and each pitched player's part, knowing who has the tune."""
        self._play_drums(at)
        at.here = players_in(style=self._style, roles=self._roles, levels=self._levels, section=at.section)
        self._write_chords(at)
        at.tune_role = self._tune_role_in(at.section)
        for role, entry in self._pitched:
            self._give_part(at, role=role, entry=entry)

    def _tune_role_in(self, section):
        """Return the player who has the tune in a section, if any: a player of lines who answers nobody and plays there."""
        for role, entry in self._pitched:
            if FIGURE not in entry and not role.get(ANSWERS) and role[ROLE] in section[PLAYS]:
                return role
        return None

    def _give_tune_away(self, at):
        """Give the section's tune to the player the song gives it to: for this kind of section, or else for the whole song. That
        player plays the tune in place of the usual part, the player who had the tune rests, and with nobody the section has no tune."""
        tune_by_kind = self._song.get(TUNE_BY, {})
        tune_by = tune_by_kind.get(at.section[KIND], self._song.get(TUNE_BY_SONG))
        role = at.tune_role
        if role is None or role[ROLE] not in at.play or tune_by is None or tune_by == role[ROLE]:
            return
        tune_played = at.play.pop(role[ROLE])
        if tune_by != NOBODY and self._has_role(tune_by):
            at.play[tune_by] = tune_played

    def _has_role(self, name):
        """Return whether the band has a role of a name."""
        for role in self._roles:
            if role[ROLE] == name:
                return True
        return False

    def _scene_settings_of(self, at):
        """Return the settings of a section's scene: what the section says, with the kind of section it is, a key or a scale of
        its own named and added to the set's, and a climb, a fade or a change of tempo taking all its bars where it says no bars."""
        settings = dict(at.section.get(SCENE_SETTINGS) or {})
        if at.section[KIND] in file_format.SECTION_KINDS:
            # A scene says what kind of section it is, where the kind is one a scene may be.
            settings.setdefault(SECTION_OF_SCENE, at.section[KIND])
        if isinstance(settings.get(SCALE), dict):
            # A section in a key or a scale of its own: the scale is named as the song's is and added to the set's.
            own_scale = settings[SCALE]
            settings[SCALE] = SCALE_NAME.format(own_scale[ROOT], own_scale[TYPE].capitalize())
            self._more_scales[settings[SCALE]] = {ROOT: own_scale[ROOT], TYPE: own_scale[TYPE]}
        if VelocitySetting.IN_START in settings:
            settings.setdefault(VelocitySetting.IN_OVER, at.bars)
        if VelocitySetting.OUT_END in settings:
            settings.setdefault(VelocitySetting.OUT_OVER, at.bars)
        if SceneSetting.TEMPO_IN_END in settings:
            settings.setdefault(SceneSetting.TEMPO_IN_OVER, at.bars)
        return as_percentages(settings=settings, song_tempo=self._tempo)

    def _said_of_scene(self, at):
        """Return what the notes say of a section's scene: its count, its name and its bars, and what the plan said of it."""
        said = wizard_text.MSG_MADE_SCENE.format(at.count, at.scene_name, at.bars)
        if not at.section.get(SAID_OF_SECTION):
            return said
        return MADE_SCENE_SAID.format(said, at.section[SAID_OF_SECTION])

    def _hold(self, at):
        """Write a section that is one held chord: a crash and a kick where the kit has them, each backing player holding the chord, and the chord on the chords track."""
        held = wizard_text.MSG_PART_OF_SECTION.format(CRASH, HELD)
        if not self._no_drums and CRASH not in self._pieces_off:
            self._parts[held] = one_hit(style=self._style, meter=self._meter, drum=CRASH, played=self._played)
        if not self._no_drums and KICK not in self._pieces_off:
            self._parts[wizard_text.MSG_PART_OF_SECTION.format(KICK, HELD)] = one_hit(style=self._style, meter=self._meter, drum=KICK, played=self._played)
        if not self._no_drums and CRASH not in self._pieces_off:
            if CRASH not in self._tracks:
                self._tracks[CRASH] = DRUM_KIT
                self._drum_tracks.append(CRASH)
            at.play[CRASH] = held
        if KICK in self._tracks:
            at.play[KICK] = {PART: wizard_text.MSG_PART_OF_SECTION.format(KICK, HELD), ONCE: True}
        for role, entry in self._pitched:
            if FIGURE in entry and role[ROLE] in at.section.get(PLAYS, [role[ROLE]]):
                at.play[role[ROLE]] = {PART: wizard_text.MSG_PART_OF_SECTION.format(role[ROLE], HELD), ONCE: True, CHAINS: [wizard_text.MSG_FOLLOW_CHORDS_NAME]}
        # The held chord is on the chords track too, the home chord for a bar, and what holds it follows it there.
        self._chains[wizard_text.MSG_FOLLOW_CHORDS_NAME] = [dict(FOLLOWS_THE_CHORDS)]
        at.chords_played = wizard_text.MSG_PART_OF_SECTION.format(at.name, wizard_names.ARRANGER_CHORDS)
        self._parts[at.chords_played] = {RAW: one_chord(self._meter)}
        at.chords_played = {PART: at.chords_played, ONCE: True}

    def _play_drums(self, at):
        """Have each piece of the kit play the part written for the section, with a crash on its first beat where the section starts with one."""
        drum_set = self._drums_of.get(at.name, {})
        for piece, part in drum_set.items():
            at.play[piece] = {PART: part, CHAINS: [wizard_text.MSG_TIMING_CHAIN.format(piece)]}
        if at.section.get(CRASH_START) and at.name in self._drums_of and CRASH not in self._pieces_off:
            start = wizard_text.MSG_SECTION_START_PART.format(CRASH)
            self._parts[start] = one_hit(style=self._style, meter=self._meter, drum=CRASH, played=self._played)
            if CRASH not in self._tracks:
                self._tracks[CRASH] = DRUM_KIT
                self._drum_tracks.append(CRASH)
            at.play.setdefault(CRASH, {PART: start, ONCE: True})

    def _write_chords(self, at):
        """Write the section's chords on the chords track, a step a chord, which every clip that plays them follows; chords no
        step can hold are made by a Progression."""
        progression = wizard_text.MSG_PART_OF_SECTION.format(at.name, wizard_names.ARRANGER_CHORDS)
        every = at.section.get(EVERY, self._chord_entry.get(EVERY))
        chords = self.chords_in(at.section, shared=True)
        section_progression = progression_of(chords=chords, every=every, meter=self._meter)
        scene_settings = at.section.get(SCENE_SETTINGS) or {}
        own_scale = scene_settings.get(SCALE)
        scale_type = self._scale_type
        if isinstance(own_scale, dict):
            scale_type = own_scale[TYPE]
        written = chords_written(progression=section_progression, meter=self._meter, scale_type=scale_type)
        if written is not None:
            self._parts[progression] = {RAW: written}
            at.chords_played = progression
            return
        self._progressions[progression] = section_progression
        self._chains[progression] = [{chords_plugin.NAME: progression}]
        self._parts[progression] = {RAW: one_chord(self._meter)}
        at.chords_played = {PART: progression, CHAINS: [progression]}

    def _lines_of(self, at, *, role):
        """Return the lines a player of a tune plays in the section: those the section gives, or those sketched for the player."""
        given_lines = at.section.get(LINES_GIVEN, {})
        given = given_lines.get(role[ROLE])
        if given:
            return given
        answers = bool(role.get(ANSWERS))
        hooks = self._song.get(melody.HOOKS, {})
        second_hook = hooks.get(melody.SECOND_HOOK, {})
        return sketched(
            habits=self._habits_of_player(at=at, role=role),
            plan=at.section[PLAN],
            chords=at.chords,
            scale_type=self._scale_type,
            seed=self._song.get(SEED, 0),
            answers=answers,
            engine=self._song.get(MELODY_ENGINE, role.get(melody.ENGINE)),
            voice=role.get(VOICE),
            letters=line_letters(plans=self._plans, answers=answers),
            hook=self._has_a_hook,
            hook_take=self._song.get(melody.HOOK_TAKE, melody.FIRST_HOOK_TAKE),
            tag_take=second_hook.get(melody.TAG_TAKE, melody.FIRST_HOOK_TAKE),
        )

    def _habits_of_player(self, *, at, role):
        """Return the tune's habits as a player keeps them in a section, with the role's own, the song's for the role and the
        song's for its melodies laid over them."""
        habits = habits_of(habits=self._habits, player=at.here[role[ROLE]])
        habits.update(role.get(HABITS, {}))
        role_habits = self._song.get(ROLE_HABITS, {})
        habits.update(role_habits.get(role[ROLE], {}))
        habits.update(self._song.get(MELODY, {}))
        return habits

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
        part = wizard_text.MSG_PART_BESIDE.format(drawn_in, role[ROLE], way)
        if part not in self._parts:
            lines = self._under.lines(way=way, tune=self._lines_of(at, role=at.tune_role), chords=at.chords, section=drawn_in)
            if not notation.is_silent(lines):
                self._parts[part] = tune_part(lines=lines, role=role, meter=self._meter, grid=self._habits[melody.GRID])
                self._shaped.append(part)
        if part in self._parts:
            at.play[role[ROLE]] = {PART: part, ONCE: True, CHAINS: [wizard_text.MSG_TIMING_CHAIN.format(role[ROLE])]}

    def _play_figure(self, at, *, role, entry):
        """Have a backing player play the player's figure over the section's chords, or the song's riff where the section has one,
        or the figure with the band's last bar together."""
        chain = self._figure_chain(at=at, role=role, entry=entry)
        figure, entry_here = self._figure_of_kind(at=at, role=role, entry=entry)
        figure = self._figure_held_back(at=at, role=role, entry=entry_here, figure=figure)
        riff, riff_here = self.riff_played(at.section, by=role[ROLE])
        if riff_here:
            self._play_riff(at=at, role=role, riff=riff, riff_here=riff_here, chain=chain)
            return
        figure = self._figure_with_tail(at=at, role=role, figure=figure)
        at.play[role[ROLE]] = {PART: figure, CHAINS: [chain]}

    def _figure_chain(self, *, at, role, entry):
        """Return the chain a player's figure runs in the section, made here: following the chords, the way's generators, voice
        leading where the player leads its voices, then rushed and dragged."""
        name = role[ROLE]
        chain = wizard_text.MSG_PART_OF_SECTION.format(at.name, name)
        links = [dict(FOLLOWS_THE_CHORDS)]
        for generator in entry.get(GENERATORS, []):
            for kind in generator:
                links.append({kind: name})
        if role.get(VOICE_LEADING):
            links.append({chords_plugin.NAME: NEAR})
        links.append({TIMING: name})
        self._chains[chain] = links
        return chain

    def _figure_of_kind(self, *, at, role, entry):
        """Return the part of a player's figure for the section and the way played: the way's own figure for this kind of section,
        a part of its own, in place of the figure played elsewhere."""
        by_section = entry.get(BY_SECTION, {})
        of_kind = by_section.get(at.section[KIND], {})
        if FIGURE not in of_kind:
            return role[ROLE], entry
        entry_here = dict(entry)
        entry_here[FIGURE] = of_kind[FIGURE]
        figure = wizard_text.MSG_PART_OF_SECTION.format(role[ROLE], at.section[KIND])
        if figure not in self._parts:
            self._parts[figure] = figure_part(entry=entry_here, role=role, meter=self._meter, player=self._playing[role[ROLE]], phrase_bars=self._phrase_bars)
            self._shaped.append(figure)
        return figure, entry_here

    def _figure_held_back(self, *, at, role, entry, figure):
        """Return the part of a player held back in the section to a lower level, a part of its own; a player held back who plays
        the figure no differently plays the one part, so that no part is written twice."""
        here = at.here[role[ROLE]]
        if here == self._playing[role[ROLE]]:
            return figure
        held_back = figure_part(entry=entry, role=role, meter=self._meter, player=here, phrase_bars=self._phrase_bars)
        if held_back == self._parts[figure]:
            return figure
        character = character_in(levels=self._levels, instrument=role.get(PLAYER), section=at.section)
        figure = wizard_text.MSG_PART_AT_LEVEL.format(figure, label_of(character))
        if figure not in self._parts:
            self._parts[figure] = held_back
            self._shaped.append(figure)
        return figure

    def _play_riff(self, *, at, role, riff, riff_here, chain):
        """Have a player play the song's riff in place of the figure: moved by the chords and played as written, with none of the
        figure's own generators. Its first player plays its chords, and a player under the first its notes alone."""
        written_for = riff.riff.get(RIFF_FOR, riff.players[0])
        first = role[ROLE] == written_for
        riff_part = wizard_text.MSG_PART_OF_SECTION.format(role[ROLE], riff.name or riffs_values.RIFF)
        if None in riff_here:
            # A riff that stays at home is written out for the whole section: the riff over the home chord, and every other chord held.
            riff_part = wizard_text.MSG_PART_OF_SECTION.format(at.name, riff_part)
        if riff.riff.get(RIFF_OWN) is not None:
            # A riff written by hand is played as written, each player in the player's own octave.
            self._parts.setdefault(riff_part, self._riff_written_by_hand(role=role, riff=riff, written_for=written_for))
        elif riff_part not in self._parts:
            self._parts[riff_part] = self._riff_drawn(role=role, riff=riff, riff_here=riff_here, first=first)
            self._shaped.append(riff_part)
        riff_chain = wizard_text.MSG_PART_OF_SECTION.format(chain, riffs_values.RIFF)
        self._chains[riff_chain] = [dict(FOLLOWS_THE_CHORDS), {TIMING: role[ROLE]}]
        at.play[role[ROLE]] = {PART: riff_part, CHAINS: [riff_chain]}

    def _riff_written_by_hand(self, *, role, riff, written_for):
        """Return a riff written by hand as a player plays it, in the player's own octave."""
        first_role = None
        for other in self._roles:
            if other[ROLE] == written_for:
                first_role = other
                break
        octaves = role[notation.OCTAVE] - first_role[notation.OCTAVE]
        return {RAW: in_octaves_of(pattern=riff.riff[RIFF_OWN], by=octaves, group=role[ROLE])}

    def _riff_drawn(self, *, role, riff, riff_here, first):
        """Return a riff drawn from the seed as a player plays it: its first player its chords, others its notes alone, and a riff
        that stays at home held over every chord but the home one."""
        if None not in riff_here:
            lines = [riff.notes]
        else:
            lines = []
            for bar in riff_here:
                if bar is None:
                    lines.append(held_bar(eighths=self._riff_eighths, chord=first))
                else:
                    lines.append(riff.split[bar])
        copied = []
        for line in lines:
            if not first:
                line = single(line)
            copied.append(notation.copied_line(line))
        part = {notation.STEP: EIGHTH, notation.OCTAVE: role[notation.OCTAVE]}
        part.update(voice_of(role))
        part[notation.LINES] = copied
        return part

    def _figure_with_tail(self, *, at, role, figure):
        """Return the part of a figure as the band's last bar together: written out for the whole section where it leaves with a
        drop-out or a stop, so that its last bar alone differs."""
        leaves = at.section.get(wizard_names.JOINS_LEAVES) or {}
        tail = leaves.get(joins.TAIL)
        if tail not in (joins.DROP_OUT, joins.STOPS):
            return figure
        whole_part = wizard_text.MSG_PART_OF_SECTION.format(at.name, wizard_text.MSG_PART_OF_SECTION.format(role[ROLE], tail))
        written = self._parts[figure]
        part = dict(written)
        part[notation.LINES] = with_tail(bars=written[notation.LINES], count=at.bars, tail=tail, eighths=leaves.get(joins.TAIL_EIGHTHS, 0))
        self._parts[whole_part] = part
        self._shaped.append(whole_part)
        return whole_part

    def _play_tune(self, at, *, role):
        """Have a player of lines play the section's tune: one written by hand, or the lines given or sketched for the player, the
        one part each time a tune returns note for note."""
        chains = [wizard_text.MSG_TIMING_CHAIN.format(role[ROLE])]
        if role is at.tune_role:
            # The tune's phrasing is the tune's player's alone.
            chains.extend(self._phrased)
        part, own = self._own_tune_part(at=at, role=role)
        if own is not None:
            # A tune written by hand is played as written by every section of its kind, and nothing here writes one over it; a
            # solo written by hand is that one solo's alone. The notes keep the chains the player's written part would run.
            self._parts.setdefault(part, {RAW: copy.deepcopy(own)})
            at.play[role[ROLE]] = {PART: part, ONCE: True, CHAINS: chains}
            return
        part = self._tune_written(at=at, role=role)
        if part is not None:
            at.play[role[ROLE]] = {PART: part, ONCE: True, CHAINS: chains}

    def _own_tune_part(self, *, at, role):
        """Return the name of the part and the notes of a tune written by hand that a player plays in the section, or two Nones:
        a solo's or a part of the intro's own notes, named for its scene, else the kind's own or taken tune for the tune's player."""
        own_solo = self._own_solo_notes(at=at, role=role)
        if own_solo is not None:
            return wizard_text.MSG_OWN_TUNE_PART.format(kind=at.scene_name), own_solo
        own = self._own_tune_notes(at=at, role=role)
        if own is not None:
            return wizard_text.MSG_OWN_TUNE_PART.format(kind=at.section[KIND]), own
        return None, None

    def _own_tune_notes(self, *, at, role):
        """Return the notes of the kind's tune written by hand or taken, for the tune's player, or of the intro the player has of
        its own for every part, or None."""
        kind = at.section[KIND]
        notes = None
        if role is at.tune_role:
            own_tunes = self._song.get(OWN_TUNES, {})
            taken = self._song.get(TAKEN_TUNES, {})
            notes = own_tunes.get(kind) or taken.get(kind)
        own_intro = self._song.get(OWN_INTRO, {})
        if kind == INTRO_KIND and own_intro.get(role[ROLE]) is not None:
            notes = own_intro[role[ROLE]]
        return notes

    def _own_solo_notes(self, *, at, role):
        """Return the notes a player has of its own for this one solo, or this one part of the intro, or None."""
        kind = at.section[KIND]
        notes = None
        if kind == SOLO_KIND:
            own_solos = self._song.get(OWN_SOLOS, {})
            of_solo = own_solos.get(self._solos_met, {})
            notes = of_solo.get(role[ROLE])
        if kind == INTRO_KIND:
            own_intros = self._song.get(OWN_INTROS, {})
            of_part = own_intros.get(self._intros_met, {})
            if of_part.get(role[ROLE]) is not None:
                # One part of an intro keeps notes of its own, as one solo does, named for its scene.
                notes = of_part[role[ROLE]]
        return notes

    def _tune_written(self, *, at, role):
        """Return the part of the tune a player plays in the section, writing it where no section wrote it before, or None where
        the player's lines are silent; a tune that returns note for note, as a chorus's, is the one part each time, where the
        song's sections are planned."""
        part = wizard_text.MSG_PART_OF_SECTION.format(at.name, role[ROLE])
        if part in self._parts:
            return part
        lines = self._lines_of(at, role=role)
        if notation.is_silent(lines):
            return None
        written = tune_part(lines=lines, role=role, meter=self._meter, grid=self._habits[melody.GRID])
        same = (role[ROLE], repr(written))
        if DRAWN_AS in at.section and same in self._same_tunes:
            return self._same_tunes[same]
        self._parts[part] = written
        self._shaped.append(part)
        self._same_tunes[same] = part
        return part

    def as_input(self):
        """Return the song as arranged, a song wizard input: its tracks, parts, generators, chains and the scenes of its form."""
        generators = self._generators()
        said = self._said_of_band()
        own_sounds = self._kit_sounds_as_instruments()
        notes = wizard_text.MSG_MADE_SONG_NOTES.format(title=self._song[TITLE], style=self._style[TITLE], template=self._song[TEMPLATE], picks=said, form='\n'.join(self._notes))
        scales = {self._scale: {ROOT: self._song[KEY][ROOT], TYPE: self._scale_type}}
        scales.update(self._more_scales)
        drum_tracks = [piece for piece in self._drum_tracks if piece not in own_sounds]
        given = {
            NAME: self._song[NAME],
            TITLE: self._song[TITLE],
            DESCRIPTION: self._song.get(DESCRIPTION, self._song[TITLE]),
            GENRE: self._style[GENRE],
            SUBGENRE: self._song[TEMPLATE],
            VARIANT: self._song.get(VARIANT),
            NOTES: notes,
            SCALES: scales,
            SCALE: self._scale,
            TEMPO: self._tempo,
            FEEL: self._style[FEEL],
            SHAPED: self._shaped,
            INSTRUMENTS: self._instruments,
            TRACKS: self._tracks,
            DRUM_TRACKS: drum_tracks,
            MUTED_TRACKS: [wizard_text.MSG_CHORDS_TRACK],
            GENERATORS: generators,
            CHAINS: self._chains,
            PARTS: self._parts,
            FORM: self._form,
        }
        self._add_song_wide(given)
        return given

    def _generators(self):
        """Return the generators the song's clips run, by section: what follows the chords, the players' ways' own, the tune's
        phrasing and the players' Musicians; what follows the chords, the progressions and the voice leading are Chords generators."""
        chords = {wizard_text.MSG_FOLLOW_CHORDS_NAME: {ChordsSetting.MODE: chords_model.FOLLOW_PROGRESSION, ChordsSetting.CHORDS_FROM: wizard_text.MSG_CHORDS_TRACK}}
        for name, progression in self._progressions.items():
            chords[name] = {ChordsSetting.MODE: chords_model.PROGRESSION, **progression}
        if self._leads_voices():
            chords[NEAR] = dict(NEAR_VOICES)
        generators = {chords_plugin.SECTION: chords}
        generators.update(self._extra)
        if self._phrased:
            # The tune is delivered as a player would deliver it, by one Phrasing every clip of the tune runs after its timing.
            generators[phrasing_plugin.SECTION] = {wizard_text.MSG_TUNE_PHRASING_NAME: dict(self._song[TUNE_PHRASING])}
            self._chains[wizard_text.MSG_TUNE_PHRASING_NAME] = [{phrasing_plugin.NAME: wizard_text.MSG_TUNE_PHRASING_NAME}]
        if self._style[GENRE] not in band.GENRES_WITHOUT_MUSICIANS:
            generators[musician_plugin.SECTION] = self._musicians_heard()
        return generators

    def _musicians_heard(self):
        """Return the Musicians the song's clips run, by name: each player's clips are played by the player's Musician, first in
        their chains, and every piece of the kit by the drummer's; a Musician nobody's clips run is left out."""
        tune_track = self._tune_track()
        musicians, musician_of = band.band_of(members=self._band_members(), drummer=drummer_role(self._roles), drum_tracks=self._drum_tracks,
                                              tune_track=tune_track, own=self._song.get(MUSICIANS, {}))
        heard = set()
        for scene in self._form:
            for track, clip in scene[PLAY].items():
                if track in musician_of:
                    scene[PLAY][track] = _with_chain_first(clip=clip, chain=musician_of[track])
                    heard.add(musician_of[track])
        for name in heard:
            self._chains[name] = [{musician_plugin.NAME: name}]
        return {name: settings for name, settings in musicians.items() if name in heard}

    def _band_members(self):
        """Return each pitched player as a member of the band, for the Musicians."""
        members = []
        for role, entry in self._pitched:
            sound = self._instruments.get(self._tracks[role[ROLE]])
            members.append(band.BandMember(track=role[ROLE], player=role.get(PLAYER), backing=FIGURE in entry, answers=bool(role.get(ANSWERS)), sound=sound))
        return members

    def _tune_track(self):
        """Return the track that has the tune: the song's own choice, or the first player of lines who answers nobody; None where
        the song has no such track."""
        usual = None
        for role, entry in self._pitched:
            if FIGURE not in entry and not role.get(ANSWERS):
                usual = role[ROLE]
                break
        tune_track = self._song.get(TUNE_BY_SONG, usual)
        if tune_track in self._tracks:
            return tune_track
        return None

    def _leads_voices(self):
        """Return whether any pitched player leads its voices."""
        for role, _ in self._pitched:
            if role.get(VOICE_LEADING):
                return True
        return False

    def _said_of_band(self):
        """Return what the notes say of the band and of each pick, a line each."""
        said = band_said(style=self._style, song=self._song, roles=self._roles)
        for trait, value in self._picks.items():
            said.append(wizard_text.MSG_MADE_PICK.format(trait, value))
        return '\n'.join(said)

    def _kit_sounds_as_instruments(self):
        """Give each piece of the kit that sounds as a General MIDI sound a track with an instrument of its own, and return those
        pieces' sounds, by piece: such a piece has no drum track."""
        own_sounds = {}
        for piece, sounds_as in self._song.get(PIECE_SOUNDS, {}).items():
            if PLAYED_SOUND in sounds_as and piece in self._tracks:
                own_sounds[piece] = sounds_as[PLAYED_SOUND]
        for piece, sound in own_sounds.items():
            instrument = wizard_text.MSG_PIECE_INSTRUMENT.format(piece)
            self._instruments[instrument] = sound
            self._tracks[piece] = instrument
        return own_sounds

    def _add_song_wide(self, given):
        """Add what holds for the whole song where it says: its groove, how far the feel moves each track's notes, and its meter."""
        groove = self._song.get(GROOVE, self._style.get(GROOVE))
        if groove and groove != NO_GROOVE:
            given[GROOVE] = groove
        if self._song.get(DYNAMICS):
            given[DYNAMICS] = self._dynamics_of_tracks()
        if self._meter != COMMON_TIME:
            given[TIME_SIGNATURE] = self._meter

    def _dynamics_of_tracks(self):
        """Return how far the feel moves each track's notes: a player's own track, and for the drummer every piece of the kit."""
        dynamics = self._song[DYNAMICS]
        of_tracks = {}
        for role in self._roles:
            if role[ROLE] in dynamics and role[ROLE] in self._tracks:
                of_tracks[role[ROLE]] = dynamics[role[ROLE]]
        drummer = drummer_role(self._roles)
        if drummer in dynamics:
            for piece in self._drum_tracks:
                of_tracks[piece] = dynamics[drummer]
        return of_tracks


def arranged(*, style, song):
    """A song's picks as a song wizard input."""
    return Arrangement(style=style, song=song).as_input()


def _level_at(*, marks, place):
    """Return how loud a decoration's drum hits at a step: an accent, loud, soft, a ghost note, or none."""
    for level in (wizard_names.ACCENT, notation.LOUD, wizard_names.SOFT, wizard_names.GHOST):
        if place in marks.get(level, []):
            return level
    return notation.NONE


def _bar_of_chords(*, chord, shared):
    """Return a written bar's chord, or its two chords where two share the bar and the progression keeps them."""
    if shared and shares_a_bar(chord):
        return [chord_of(half) for half in chord]
    return chord_of(chord)
