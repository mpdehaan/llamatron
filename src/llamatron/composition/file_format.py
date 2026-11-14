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

"""The names the set file format uses, and its fixed lists, shared by everything that reads or writes it.

Each group of names is a class of constants, like Row.DEGREE for 'degree', so that code names
what it means and a misspelled name fails at once. The values are the plain strings the file
holds.
"""


from llamatron.support.rational import Rational
from llamatron.music.chord import ChordType


class Section:
    """The sections of a set file that hold named objects, and a song's list of scenes.

    Scales, patterns, generators, chains and the songs belong to the set, and every song shares
    them. Tracks, registers and scenes belong to one song.
    """

    SCALES = 'scales'
    PATTERNS = 'patterns'
    TRACKS = 'tracks'
    ARPS = 'arps'
    AUTO_RATCHETS = 'auto_ratchets'
    DRIFTS = 'drifts'
    PROGRESSIONS = 'progressions'
    VOICE_LEADINGS = 'voice_leadings'
    STRUMS = 'strums'
    EUCLIDS = 'euclids'
    DENSITIES = 'densities'
    SWELLS = 'swells'
    ARTICULATES = 'articulates'
    GLIDES = 'glides'
    SHORTENS = 'shortens'
    RUSHES = 'rushes'
    DRAGS = 'drags'
    HOCKETS = 'hockets'
    CHAINS = 'chains'
    GROOVES = 'grooves'
    INSTRUMENTS = 'instruments'
    REGISTERS = 'registers'
    SONGS = 'songs'
    SCENES = 'scenes'


class SetlistSetting:
    """The set's own settings, at the top of a file: who wrote it, and how its patterns are read and shown."""

    VERSION = 'version'
    TITLE = 'title'
    AUTHOR = 'author'
    # One line saying what the set is, like the tune it plays, and then text of any length.
    DESCRIPTION = 'description'
    NOTES = 'notes'
    STEP_SIZE = 'step_size'
    DEFAULT_OCTAVE = 'default_octave'
    DEFAULT_DRUM_OCTAVE = 'default_drum_octave'
    OCTAVE_LABELS = 'octave_labels'
    DEFAULT_FOLLOW_ACTION = 'default_follow_action'
    REAL_TIME = 'real_time'
    # The visualizer mode Arrange's visualizer key shows first, unless a song names its own, and the modes left out of the key's list (the user's design).
    VISUALIZER = 'visualizer'
    HIDDEN_VISUALIZERS = 'hidden_visualizers'
    # The order the Generators page lists every generator in, each written as its kind and its name, the user's design.
    GENERATOR_ORDER = 'generator_order'
    PROTECTED = 'protected'


class SongSetting:
    """One song's own settings, at the top of its entry in the set's songs."""

    TEMPO = 'tempo'
    TIME_SIGNATURE = 'time_signature'
    ENTRY_SIZE = 'entry_size'
    SCALE = 'scale'
    SEED = 'seed'
    GROOVE = 'groove'
    # A short word or two saying what kind of music the song is, only for people to read (the user's design of 2026-11-11).
    GENRE = 'genre'
    # When an edit made while the song plays in real time is heard on what plays (the user's design).
    LIVE_RESPONSIVENESS = 'live_responsiveness'
    # The visualizer mode Arrange's visualizer key shows first for this song, over the set's (the user's design).
    VISUALIZER = 'visualizer'


class LiveResponsiveness:
    """When an edit made while the song plays is heard: at the next bar of what plays, at each playing clip's next pass, or at once."""

    NEXT_BAR = 'next_bar'
    CLIP_RESTART = 'clip_restart'
    ASAP = 'asap'


LIVE_RESPONSIVENESSES = [LiveResponsiveness.NEXT_BAR, LiveResponsiveness.CLIP_RESTART, LiveResponsiveness.ASAP]
# The visualizer modes a set or a song can name, by their names on the command line, in the order the visualizer key steps through them,
# kept here so that a set file is read without the visualizers; test/test_visualizers.py holds them to the modes.
VISUALIZER_NAMES = [
    'lava_lamp', 'spectrum', 'piano_roll', 'milkdrop', 'llamas', 'hypercube', 'fireworks', 'warpzone', 'pipes', 'plasma', 'maze', 'mystify',
    'laser_llama', 'mandelbrot', 'life', 'digital_rain', 'cycle',
]


def sensible_visualizer(value):
    """Return a visualizer setting made sensible: a mode's name as it is, and anything else, a mode taken out of the program among them, None.

    A visualizer setting is never refused, the user's rule, since modes come and go and no set should stop opening for one.
    """
    return value if isinstance(value, str) and value in VISUALIZER_NAMES else None


def sensible_hidden_visualizers(value):
    """Return hidden visualizers made sensible: the modes' names in the list, in the modes' order, leaving out anything else, or None for none."""
    names = value if isinstance(value, list) else []
    kept = [name for name in VISUALIZER_NAMES if name in names]
    return kept or None


class ScaleSetting:
    """A named scale's settings."""

    ROOT = 'root'
    TYPE = 'type'


class GrooveSetting:
    """A groove's settings: its cells and how long each is."""

    CELLS = 'cells'
    CELL_LENGTH = 'cell_length'


class TrackSetting:
    """A track's settings."""

    DRUM = 'drum'
    MUTE = 'mute'
    TRANSPOSE = 'transpose'
    LOWEST_OCTAVE = 'lowest_octave'
    HIGHEST_OCTAVE = 'highest_octave'
    CC = 'cc'
    GROOVE = 'groove'
    INSTRUMENT = 'instrument'
    # The register each CC lane is bound to, which sends the register's value on the lane whenever it changes, and the register bound to the velocity.
    CC1_REGISTER = 'cc1_register'
    CC2_REGISTER = 'cc2_register'
    CC3_REGISTER = 'cc3_register'
    CC4_REGISTER = 'cc4_register'
    VELOCITY_REGISTER = 'velocity_register'
    # The chains every clip of the track runs, after the clip's and the scene's.
    CHAINS = 'chains'
    # How the track's chords are strummed, unless a clip strums its own way (the user's design of 2026-11-11).
    STRUM_DIRECTION = 'strum_direction'
    STRUM_SPREAD = 'strum_spread'
    STRUM_FADE = 'strum_fade'
    STRUM_LOOSE_TIMING = 'strum_loose_timing'
    STRUM_UPSTROKE_STRINGS = 'strum_upstroke_strings'
    # The Euclidean rhythm that masks every clip on the track: only a note starting on one of its hits plays (the user's design of 2026-11-11).
    EUCLID_HITS = 'euclid_hits'
    EUCLID_STEPS = 'euclid_steps'
    EUCLID_ROTATE = 'euclid_rotate'
    EUCLID_STEP = 'euclid_step'


class PatternSetting:
    """A pattern's settings, besides its rows."""

    STEPS = 'steps'
    STEP_SIZE = 'step_size'
    TIME_SIGNATURE = 'time_signature'
    ENTRY_SIZE = 'entry_size'
    DRUM = 'drum'
    DIRECTION = 'direction'


class Row:
    """A pattern's rows, each holding one value for every step, as in the pattern editor."""

    DEGREE = 'degree'
    GATE = 'gate'
    DOT = 'dot'
    ACCIDENTAL = 'accidental'
    OCTAVE = 'octave'
    CHORD = 'chord'
    # Which of a chord's notes is at the bottom: blank for root position, or how many of its lowest notes move up an octave.
    INVERSION = 'inversion'
    # The notes added on top of a step's chord, like a flat ninth: a list of tensions, or blank for none.
    TENSION = 'tension'
    # The scale type a step's degree and chord are drawn from, on the clip's root, or blank for the clip's own: a borrowed chord.
    CHORD_SCALE = 'chord_scale'
    VELOCITY = 'velocity'
    PROBABILITY = 'probability'
    GLIDE = 'glide'
    # A tied step plays nothing of its own and keeps the note before it sounding through the step.
    TIE = 'tie'
    RATCHET = 'ratchet'
    RATCHET_OFFSET = 'ratchet_offset'
    GRAB = 'grab'
    CC1 = 'cc1'
    CC2 = 'cc2'
    CC3 = 'cc3'
    CC4 = 'cc4'
    SLIDE = 'slide'
    # Whether each register's value moves the step's note along the scale.
    AX_NOTE = 'ax_note'
    BX_NOTE = 'bx_note'
    CX_NOTE = 'cx_note'
    DX_NOTE = 'dx_note'
    # Whether each register's value is added to the step's velocity.
    AX_VELOCITY = 'ax_velocity'
    BX_VELOCITY = 'bx_velocity'
    CX_VELOCITY = 'cx_velocity'
    DX_VELOCITY = 'dx_velocity'
    # How much the step adds to each register, which can be negative.
    AX_ADD = 'ax_add'
    BX_ADD = 'bx_add'
    CX_ADD = 'cx_add'
    DX_ADD = 'dx_add'
    # What the step sets each register to before anything adds to it, or blank to leave it.
    AX_SET = 'ax_set'
    BX_SET = 'bx_set'
    CX_SET = 'cx_set'
    DX_SET = 'dx_set'
    # How AX has to compare with each other register for the step's note to sound, or blank for no comparison.
    AX_BX = 'ax_bx'
    AX_CX = 'ax_cx'
    AX_DX = 'ax_dx'


class ClipSlotSetting:
    """What a scene's clip slot for a track can set."""

    NAME = 'name'
    PATTERN = 'pattern'
    # Only read, from a file saved before a clip held a list of chains: one chain's name, read as a list of one.
    CHAIN = 'chain'
    # The chains a clip runs, in order, before its scene's and its track's (the user's design of 2026-11-11).
    CHAINS = 'chains'
    # How the clip's chords are strummed, over its track's.
    STRUM_DIRECTION = 'strum_direction'
    STRUM_SPREAD = 'strum_spread'
    STRUM_FADE = 'strum_fade'
    STRUM_LOOSE_TIMING = 'strum_loose_timing'
    STRUM_UPSTROKE_STRINGS = 'strum_upstroke_strings'
    # How busy, how loud and how long its notes are over time, over its scene's (the user's design of 2026-11-11).
    DENSITY_START = 'density_start'
    DENSITY_END = 'density_end'
    DENSITY_OVER = 'density_over'
    DENSITY_THEN = 'density_then'
    SWELL_START = 'swell_start'
    SWELL_END = 'swell_end'
    SWELL_OVER = 'swell_over'
    SWELL_THEN = 'swell_then'
    ARTICULATE_START = 'articulate_start'
    ARTICULATE_END = 'articulate_end'
    ARTICULATE_OVER = 'articulate_over'
    ARTICULATE_THEN = 'articulate_then'
    LOOP = 'loop'
    REPEAT = 'repeat'
    DIRECTION = 'direction'
    MORPH_TO = 'morph_to'
    MORPH_STYLE = 'morph_style'
    GRAB_TRACK = 'grab_track'
    FOLLOW_ACTION = 'follow_action'
    # A scale of the clip's own, which wins over the scene's and the song's.
    SCALE = 'scale'


class SceneSetting:
    """A scene's settings, and the clip slots it holds for its tracks."""

    NAME = 'name'
    REPEAT = 'repeat'
    SCALE = 'scale'
    TEMPO = 'tempo'
    TEMPO_START = 'tempo_start'
    TEMPO_END = 'tempo_end'
    RESET = 'reset'
    GROOVE = 'groove'
    LAUNCH_TOGETHER = 'launch_together'
    # The chains every clip of the scene runs, after the clip's own.
    CHAINS = 'chains'
    # How busy, how loud and how long its clips' notes are over the scene (the user's design of 2026-11-11).
    DENSITY_START = 'density_start'
    DENSITY_END = 'density_end'
    DENSITY_OVER = 'density_over'
    DENSITY_THEN = 'density_then'
    SWELL_START = 'swell_start'
    SWELL_END = 'swell_end'
    SWELL_OVER = 'swell_over'
    SWELL_THEN = 'swell_then'
    ARTICULATE_START = 'articulate_start'
    ARTICULATE_END = 'articulate_end'
    ARTICULATE_OVER = 'articulate_over'
    ARTICULATE_THEN = 'articulate_then'
    TRACKS = 'tracks'


class RegisterName:
    """The song's four registers, whose names are fixed."""

    AX = 'AX'
    BX = 'BX'
    CX = 'CX'
    DX = 'DX'


class RegisterUse:
    """What a step does with a register on a +Note or +Vel row: adds the register's value, subtracts it, or neither. A file holds the number."""

    ADD = 1
    SUBTRACT = -1
    OFF = 0


# The uses a key cycles through on a +Note or +Vel row, after off: add, then subtract.
REGISTER_USES = [RegisterUse.ADD, RegisterUse.SUBTRACT]


class Comparison:
    """How AX has to compare with another register on a condition row for the step's note to sound: less, more or the same."""

    LESS = '<'
    MORE = '>'
    SAME = '='


# The comparisons a key cycles through on a condition row, after blank.
COMPARISONS = [Comparison.LESS, Comparison.MORE, Comparison.SAME]


class RegisterSetting:
    """A register's settings."""

    DEFAULT = 'default'
    MINIMUM = 'minimum'
    MAXIMUM = 'maximum'
    # Only read, from a file saved before at_limit came: true reads as overflow.
    WRAP = 'wrap'
    AT_LIMIT = 'at_limit'
    RESET_EACH_SCENE = 'reset_each_scene'
    # The most a step may add to the register or take from it, so that entry stays short.
    ALLOWED_INC_MAX = 'allowed_inc_max'


class AtLimit:
    """What a register does when an add would take it past its minimum or maximum (the user's design of 2026-11-11)."""

    # Stop at the end it reached.
    STOP = 'stop'
    # Go back to the register's default.
    RESET = 'reset'
    # Land exactly on the other end, past either end, as wrap did.
    OVERFLOW = 'overflow'
    # Land on the minimum past the maximum, and stop at the minimum below it.
    OVERFLOW_RIGHT = 'overflow_right'
    # Land on the maximum past the minimum, and stop at the maximum above it.
    OVERFLOW_LEFT = 'overflow_left'
    # Land on a random value from the minimum to the maximum.
    PICK_RANDOM = 'pick_random'


AT_LIMITS = [AtLimit.STOP, AtLimit.RESET, AtLimit.OVERFLOW, AtLimit.OVERFLOW_RIGHT, AtLimit.OVERFLOW_LEFT, AtLimit.PICK_RANDOM]


class Direction:
    """The orders a pattern's steps can play in, with the Cirklon's names for them."""

    FORWARD = 'forward'
    REVERSE_A = 'reverse_a'
    REVERSE_B = 'reverse_b'
    ALTERNATE = 'alternate'
    PENDULUM = 'pendulum'
    RANDOM = 'random'
    BROWNIAN = 'brownian'
    EITHERWAY = 'eitherway'


class GeneratorKind:
    """The kinds of generator a chain step can name."""

    ARP = 'arp'
    AUTO_RATCHET = 'auto_ratchet'
    DRIFT = 'drift'
    PROGRESSION = 'progression'
    VOICE_LEADING = 'voice_leading'
    STRUM = 'strum'
    EUCLID = 'euclid'
    DENSITY = 'density'
    SWELL = 'swell'
    ARTICULATE = 'articulate'
    GLIDE = 'glide'
    SHORTEN = 'shorten'
    RUSH = 'rush'
    DRAG = 'drag'
    HOCKET = 'hocket'


# The step sizes the editor offers, shortest first. Any other length can be typed.
STEP_SIZE_CHOICES = ['1/64', '1/32', '1/16', '1/8', '1/4', '1/2', '1']
# A time setting written in bars, like 2 bars, which the song's time signature turns into a length.
ONE_BAR_WRITTEN = '1 bar'
BARS_WRITTEN = '{count} bars'
# Every time setting chooses from one list (the user's rule of 2026-11-11): Step, Every and Over,
# and the Harmonizer's Delay. Each value is as a file writes it: a length in whole notes, each
# triplet after its straight value and then the dotted one, then bars.
TIME_CHOICES = [
    '1/64', '1/32', '1/16', '1/24', '3/32', '1/8', '1/12', '3/16', '1/4', '1/6', '1/2',
    ONE_BAR_WRITTEN, '2 bars', '4 bars', '8 bars', '16 bars',
]
# The time signatures the Song page steps through with left and right; Enter types any other.
TIME_SIGNATURE_CHOICES = ['2/4', '3/4', '4/4', '5/4', '6/8', '7/8', '9/8', '12/8']
# The plain gate lengths that + and - step through, shortest first. The Dot row makes any of
# them dotted or a triplet, and any other length can be typed.
GATE_LENGTH_CHOICES = ['1/64', '1/32', '1/16', '1/8', '1/4', '1/2', '1', '2', '4']


class GateModifier:
    """What a step's Dot row can do to its gate: make it dotted or a triplet."""

    DOTTED = 'd'
    TRIPLET = 't'


# How much each gate modifier changes a gate: dotted is half as long again, and a triplet two thirds as long.
GATE_MODIFIERS = {GateModifier.DOTTED: Rational(3, 2), GateModifier.TRIPLET: Rational(2, 3)}


class Accidental:
    """The accidentals a step can have."""

    SHARP = '#'
    FLAT = 'b'


class InstrumentSetting:
    """An instrument's settings: the MIDI output port it plays through and the channel, 1 to 16."""

    DEVICE = 'device'
    CHANNEL = 'channel'
    # The General MIDI sound a General MIDI export gives the instrument's tracks, numbered 1 to 128 as people number them (the user's design of 2026-11-11).
    GM_SOUND = 'gm_sound'


# The Device an instrument names to play through FluidSynth, the software synthesizer the tracker starts, rather than
# through a MIDI port: its star can never begin a port's name, so it can't be mistaken for one (the user's design of 2026-11-11).
FLUIDSYNTH_DEVICE = '*FluidSynth'


class FollowAction:
    """What a clip does in real-time playback when it finishes, which no export reads: Live's word for the same thing, shown as Advance on the clip page (the user's design of 2026-11-10)."""

    # The clip sends a start to the clip directly below it when the whole scene is done: when every clip of the scene that doesn't loop has finished.
    WITH_SCENE = 'with_scene'
    # The clip sends a start to the clip directly below it the moment its own repeats end, whatever the rest of the scene is doing.
    NEXT = 'next'
    # The clip sends nothing down, so the track falls silent until something launches it again.
    OFF = 'off'


FOLLOW_ACTION_CHOICES = [FollowAction.WITH_SCENE, FollowAction.NEXT, FollowAction.OFF]


class OctaveLabels:
    """How the tracker numbers octaves on screen, which the song's octave_labels setting chooses."""

    LIVE = 'live'
    LLAMATRON = 'llamatron'


# The choices of octave labels, in the order the Song page offers them.
OCTAVE_LABEL_CHOICES = [OctaveLabels.LIVE, OctaveLabels.LLAMATRON]
# Song files number octaves from C0, MIDI note 0, so MIDI note 60 is C5. Live labels that same note
# C3, two octaves lower, and the tracker shows Live's labels unless the song asks for its own.
LIVE_OCTAVE_OFFSET = 2
# How far below the file's numbering each choice of labels is.
OCTAVE_LABEL_OFFSETS = {OctaveLabels.LIVE: LIVE_OCTAVE_OFFSET, OctaveLabels.LLAMATRON: 0}
# Files saved before this version numbered octaves as Live labels them, and are moved up when read.
LLAMATRON_OCTAVES_SINCE = '1.0.30'
# Files saved before this version held one song at the top level, with no songs section, and are
# read as a set holding that one song.
SETLISTS_SINCE = '1.0.39'
# Files saved before this version held the long text under description, which is now notes, and a
# description is one line saying what the set is (the user's design of 2026-11-10).
NOTES_SINCE = '1.0.155'

# The registers, in the order the Registers page and the pattern editor show them.
REGISTER_NAMES = [RegisterName.AX, RegisterName.BX, RegisterName.CX, RegisterName.DX]
# Each register's rows in a pattern: whether it moves the note, whether it changes the velocity,
# and how much a step adds to it.
REGISTER_NOTE_ROWS = {
    RegisterName.AX: Row.AX_NOTE, RegisterName.BX: Row.BX_NOTE, RegisterName.CX: Row.CX_NOTE, RegisterName.DX: Row.DX_NOTE,
}
REGISTER_VELOCITY_ROWS = {
    RegisterName.AX: Row.AX_VELOCITY, RegisterName.BX: Row.BX_VELOCITY,
    RegisterName.CX: Row.CX_VELOCITY, RegisterName.DX: Row.DX_VELOCITY,
}
REGISTER_ADD_ROWS = {
    RegisterName.AX: Row.AX_ADD, RegisterName.BX: Row.BX_ADD, RegisterName.CX: Row.CX_ADD, RegisterName.DX: Row.DX_ADD,
}
# What a step sets each register to, which comes before what it adds.
REGISTER_SET_ROWS = {
    RegisterName.AX: Row.AX_SET, RegisterName.BX: Row.BX_SET, RegisterName.CX: Row.CX_SET, RegisterName.DX: Row.DX_SET,
}
# The register a condition row tests, and the condition row comparing it with each of the others.
TESTED_REGISTER = RegisterName.AX
CONDITION_ROWS = {RegisterName.BX: Row.AX_BX, RegisterName.CX: Row.AX_CX, RegisterName.DX: Row.AX_DX}

PATTERN_ROWS = [
    Row.DEGREE, Row.GATE, Row.DOT, Row.ACCIDENTAL, Row.OCTAVE, Row.CHORD, Row.INVERSION, Row.TENSION, Row.CHORD_SCALE, Row.VELOCITY, Row.PROBABILITY, Row.GLIDE,
    Row.TIE, Row.RATCHET, Row.RATCHET_OFFSET, Row.GRAB,
    Row.CC1, Row.CC2, Row.CC3, Row.CC4, Row.SLIDE,
    *REGISTER_NOTE_ROWS.values(), *REGISTER_VELOCITY_ROWS.values(), *REGISTER_ADD_ROWS.values(),
    *REGISTER_SET_ROWS.values(), *CONDITION_ROWS.values(),
]
# A pattern's CC lanes, whose numbers each track sets for itself.
CC_ROWS = (Row.CC1, Row.CC2, Row.CC3, Row.CC4)
# The track's setting that binds each CC lane to a register, in the order of the lanes.
CC_REGISTER_SETTINGS = (TrackSetting.CC1_REGISTER, TrackSetting.CC2_REGISTER, TrackSetting.CC3_REGISTER, TrackSetting.CC4_REGISTER)
FORWARD = Direction.FORWARD
DIRECTIONS = [
    Direction.FORWARD, Direction.REVERSE_A, Direction.REVERSE_B, Direction.ALTERNATE, Direction.PENDULUM,
    Direction.RANDOM, Direction.BROWNIAN, Direction.EITHERWAY,
]
NOTE_LETTERS = 'ABCDEFG'
# How many half steps each accidental moves a note.
ACCIDENTALS = {Accidental.SHARP: 1, Accidental.FLAT: -1}
# The order the pattern editor's #/b row and the piano roll's . key step through: natural, sharp, flat.
ACCIDENTAL_CYCLE = [None, Accidental.SHARP, Accidental.FLAT]

class ChordSymbol:
    """The chord symbols a step's Chord row can hold, as a file writes them.

    Named symbols, like M or dom7, are exact half steps from the step's note, so they can leave
    the scale. Plain numbers stack every other note of the scale from the step's degree, so they
    follow the scale, which is why dominants are written dom7 rather than 7.
    """

    MAJOR = 'M'
    MINOR = 'm'
    DIMINISHED = 'dim'
    AUGMENTED = 'aug'
    SUS2 = 'sus2'
    SUS4 = 'sus4'
    POWER = 'pow'
    MAJOR6 = 'M6'
    MINOR6 = 'm6'
    DOMINANT7 = 'dom7'
    MAJOR7 = 'M7'
    MINOR7 = 'm7'
    MINOR_MAJOR7 = 'mM7'
    DIMINISHED7 = 'dim7'
    HALF_DIMINISHED7 = 'm7b5'
    AUGMENTED7 = 'aug7'
    AUGMENTED_MAJOR7 = 'augM7'
    DOMINANT7_SUS4 = '7sus4'
    DOMINANT9 = 'dom9'
    MAJOR9 = 'M9'
    MINOR9 = 'm9'
    ADD9 = 'add9'
    MINOR_ADD9 = 'madd9'
    DOMINANT11 = 'dom11'
    MAJOR11 = 'M11'
    MINOR11 = 'm11'
    DOMINANT13 = 'dom13'
    MAJOR13 = 'M13'
    MINOR13 = 'm13'
    SCALE_FIFTH = '5'
    SCALE_TRIAD = '3'
    SCALE_SEVENTH = '7'
    SCALE_NINTH = '9'
    SCALE_ELEVENTH = '11'
    SCALE_THIRTEENTH = '13'


# The named chord symbols, in the order the editor offers them, and the chords they make.
FIXED_CHORDS = {
    ChordSymbol.MAJOR: ChordType.MAJOR, ChordSymbol.MINOR: ChordType.MINOR,
    ChordSymbol.DIMINISHED: ChordType.DIMINISHED, ChordSymbol.AUGMENTED: ChordType.AUGMENTED,
    ChordSymbol.SUS2: ChordType.SUS2, ChordSymbol.SUS4: ChordType.SUS4, ChordSymbol.POWER: ChordType.POWER,
    ChordSymbol.MAJOR6: ChordType.MAJOR6, ChordSymbol.MINOR6: ChordType.MINOR6,
    ChordSymbol.DOMINANT7: ChordType.DOMINANT7, ChordSymbol.MAJOR7: ChordType.MAJOR7, ChordSymbol.MINOR7: ChordType.MINOR7,
    ChordSymbol.MINOR_MAJOR7: ChordType.MINOR_MAJOR7, ChordSymbol.DIMINISHED7: ChordType.DIMINISHED7,
    ChordSymbol.HALF_DIMINISHED7: ChordType.HALF_DIMINISHED7, ChordSymbol.AUGMENTED7: ChordType.AUGMENTED7,
    ChordSymbol.AUGMENTED_MAJOR7: ChordType.AUGMENTED_MAJOR7, ChordSymbol.DOMINANT7_SUS4: ChordType.DOMINANT7_SUS4,
    ChordSymbol.DOMINANT9: ChordType.DOMINANT9, ChordSymbol.MAJOR9: ChordType.MAJOR9, ChordSymbol.MINOR9: ChordType.MINOR9,
    ChordSymbol.ADD9: ChordType.ADD9, ChordSymbol.MINOR_ADD9: ChordType.MINOR_ADD9,
    ChordSymbol.DOMINANT11: ChordType.DOMINANT11, ChordSymbol.MAJOR11: ChordType.MAJOR11, ChordSymbol.MINOR11: ChordType.MINOR11,
    ChordSymbol.DOMINANT13: ChordType.DOMINANT13, ChordSymbol.MAJOR13: ChordType.MAJOR13, ChordSymbol.MINOR13: ChordType.MINOR13,
}
# The chord symbols that stack notes of the scale, and how many scale degrees above the step's
# degree each of their notes is. A scale fifth is the root and the fifth, and each of the others
# adds every other scale note above the root.
SCALE_CHORDS = {
    ChordSymbol.SCALE_FIFTH: (0, 4),
    ChordSymbol.SCALE_TRIAD: (0, 2, 4),
    ChordSymbol.SCALE_SEVENTH: (0, 2, 4, 6),
    ChordSymbol.SCALE_NINTH: (0, 2, 4, 6, 8),
    ChordSymbol.SCALE_ELEVENTH: (0, 2, 4, 6, 8, 10),
    ChordSymbol.SCALE_THIRTEENTH: (0, 2, 4, 6, 8, 10, 12),
}
CHORD_SYMBOLS = [*FIXED_CHORDS, *SCALE_CHORDS]


class Tension:
    """The notes a chord can have added on top, as a file writes them: each a ninth, an eleventh or a thirteenth, plain, flat or sharp."""

    FLAT_NINTH = 'b9'
    NINTH = '9'
    SHARP_NINTH = '#9'
    ELEVENTH = '11'
    SHARP_ELEVENTH = '#11'
    FLAT_THIRTEENTH = 'b13'
    THIRTEENTH = '13'


# Each tension's half steps above the chord's root, in the order the editor offers them, which is from lowest to highest.
TENSIONS = {
    Tension.FLAT_NINTH: 13, Tension.NINTH: 14, Tension.SHARP_NINTH: 15, Tension.ELEVENTH: 17, Tension.SHARP_ELEVENTH: 18,
    Tension.FLAT_THIRTEENTH: 20, Tension.THIRTEENTH: 21,
}

# The generators that a chain step can use by name, and the section of a file that names them.
NAMED_GENERATORS = {
    GeneratorKind.ARP: Section.ARPS, GeneratorKind.AUTO_RATCHET: Section.AUTO_RATCHETS, GeneratorKind.DRIFT: Section.DRIFTS,
    GeneratorKind.PROGRESSION: Section.PROGRESSIONS, GeneratorKind.VOICE_LEADING: Section.VOICE_LEADINGS,
    GeneratorKind.STRUM: Section.STRUMS, GeneratorKind.EUCLID: Section.EUCLIDS,
    GeneratorKind.DENSITY: Section.DENSITIES, GeneratorKind.SWELL: Section.SWELLS, GeneratorKind.ARTICULATE: Section.ARTICULATES,
    GeneratorKind.GLIDE: Section.GLIDES, GeneratorKind.SHORTEN: Section.SHORTENS, GeneratorKind.RUSH: Section.RUSHES, GeneratorKind.DRAG: Section.DRAGS,
    GeneratorKind.HOCKET: Section.HOCKETS,
}


class DriftDirection:
    """How a drift's position moves between its versions A and B, one step a trigger, always starting at A."""

    # A to B, then staying at B.
    FORWARD = 'forward'
    # A to B, then starting again at A.
    LOOP = 'loop'
    # A to B and back, forever.
    PENDULUM = 'pendulum'
    # A random walk between A and B, a step either way each trigger.
    BROWNIAN = 'brownian'


DRIFT_DIRECTIONS = [DriftDirection.FORWARD, DriftDirection.LOOP, DriftDirection.PENDULUM, DriftDirection.BROWNIAN]


class NamedProgression:
    """The named progressions the chord editor's H offers, each a key the tracker's words name."""

    POP = 'pop'
    FIFTIES = 'fifties'
    SAD_POP = 'sad_pop'
    EPIC = 'epic'
    HOPEFUL = 'hopeful'
    ROCK = 'rock'
    MIXOLYDIAN_ROCK = 'mixolydian_rock'
    POWER_BALLAD = 'power_ballad'
    GRUNGE = 'grunge'
    PUNK = 'punk'
    ROYAL_ROAD = 'royal_road'
    HIP_HOP_LOOP = 'hip_hop_loop'
    TWELVE_BAR_BLUES = 'twelve_bar_blues'
    QUICK_CHANGE_BLUES = 'quick_change_blues'
    EIGHT_BAR_BLUES = 'eight_bar_blues'
    JAZZ_TURNAROUND = 'jazz_turnaround'
    LONG_TURNAROUND = 'long_turnaround'
    CIRCLE_OF_FIFTHS = 'circle_of_fifths'
    RHYTHM_CHANGES = 'rhythm_changes'
    FOLK = 'folk'
    GOSPEL = 'gospel'
    PACHELBEL = 'pachelbel'
    ANDALUSIAN = 'andalusian'
    MINOR = 'minor'


class StrumDirection:
    """The order a chord's notes sound in when strummed: down is low to high, as a pick moves on a downstroke, up the reverse; by the beat follows a hand that moves down on the beats and up between them; down up alternates chord by chord; off strums nothing, for a clip that won't take its track's strum."""

    BY_THE_BEAT = 'by_the_beat'
    DOWN = 'down'
    UP = 'up'
    DOWN_UP = 'down_up'
    OFF = 'off'


STRUM_DIRECTIONS = [StrumDirection.BY_THE_BEAT, StrumDirection.DOWN, StrumDirection.UP, StrumDirection.DOWN_UP, StrumDirection.OFF]


class StrumSpread:
    """How far apart a strum's strings sound, each a number of milliseconds whatever the tempo, since a hand doesn't slow down with the song."""

    TIGHT = 'tight'
    CRISP = 'crisp'
    NORMAL = 'normal'
    LOOSE = 'loose'
    RAKE = 'rake'
    HARP = 'harp'


STRUM_SPREADS = [StrumSpread.TIGHT, StrumSpread.CRISP, StrumSpread.NORMAL, StrumSpread.LOOSE, StrumSpread.RAKE, StrumSpread.HARP]


class UpstrokeStrings:
    """Which of a chord's notes an upstroke catches: all of them, or only the top three or four, as a hand often does."""

    ALL = 'all'
    TOP_3 = 'top_3'
    TOP_4 = 'top_4'


UPSTROKE_STRINGS = [UpstrokeStrings.ALL, UpstrokeStrings.TOP_3, UpstrokeStrings.TOP_4]


class StrumPart:
    """A strum's settings as a Strum generator names them, and as a track or a clip names them after strum_."""

    DIRECTION = 'direction'
    SPREAD = 'spread'
    FADE = 'fade'
    LOOSE_TIMING = 'loose_timing'
    UPSTROKE_STRINGS = 'upstroke_strings'


STRUM_PARTS = [StrumPart.DIRECTION, StrumPart.SPREAD, StrumPart.FADE, StrumPart.LOOSE_TIMING, StrumPart.UPSTROKE_STRINGS]
STRUM_SETTING = 'strum_{part}'


def strum_setting(part):
    """Return a track's or a clip's setting of one part of its strum, like strum_spread."""
    return STRUM_SETTING.format(part=part)


class EuclidPart:
    """A Euclidean rhythm's settings as a Euclid generator names them, and as a track names them after euclid_."""

    HITS = 'hits'
    STEPS = 'steps'
    ROTATE = 'rotate'
    STEP = 'step'


EUCLID_PARTS = [EuclidPart.HITS, EuclidPart.STEPS, EuclidPart.ROTATE, EuclidPart.STEP]
EUCLID_SETTING = 'euclid_{part}'


def euclid_setting(part):
    """Return a track's setting of one part of its Euclidean mask, like euclid_hits."""
    return EUCLID_SETTING.format(part=part)


class NamedRhythm:
    """The named Euclidean rhythms the Hits field's H offers, each a key the tracker's words name."""

    TRESILLO = 'tresillo'
    CINQUILLO = 'cinquillo'
    KHAFIF_E_RAMAL = 'khafif_e_ramal'
    AKSAK = 'aksak'
    VENDA = 'venda'
    BEMBE = 'bembe'
    SAMBA = 'samba'
    BOSSA_NOVA = 'bossa_nova'


class Restart:
    """When a generator starts over: with every clip, as it always has; the first time each scene plays, carrying on through its repeats; or never, running along the song from its top (the user's design of 2026-11-11)."""

    EVERY_CLIP = 'every_clip'
    ON_NEW_SCENE = 'on_new_scene'
    WHOLE_SONG = 'whole_song'


RESTARTS = [Restart.EVERY_CLIP, Restart.ON_NEW_SCENE, Restart.WHOLE_SONG]
# Every generator's setting of when it starts over.
GENERATOR_RESTART = 'restart'


class Quality:
    """What a triad is, by the half steps from its root to its third and its fifth, as a progression's chords show it."""

    MAJOR = 'major'
    MINOR = 'minor'
    DIMINISHED = 'diminished'
    AUGMENTED = 'augmented'


class Shape:
    """The three ways a scene, a clip or a generator shapes notes over time, each a percentage ramping from a start to an end: how many notes play, how loud and how long."""

    DENSITY = 'density'
    SWELL = 'swell'
    ARTICULATE = 'articulate'


SHAPES = [Shape.DENSITY, Shape.SWELL, Shape.ARTICULATE]


class ShapePart:
    """What each shape has: its start and end percentages, how long one ramp lasts (over), and what follows it (then)."""

    START = 'start'
    END = 'end'
    OVER = 'over'
    THEN = 'then'


SHAPE_PARTS = [ShapePart.START, ShapePart.END, ShapePart.OVER, ShapePart.THEN]


class ShapeThen:
    """What a shape does once one ramp is over and the clip goes on: stays at its end, starts again, or ramps back."""

    HOLD = 'hold'
    REPEAT = 'repeat'
    BOUNCE = 'bounce'


SHAPE_THENS = [ShapeThen.HOLD, ShapeThen.REPEAT, ShapeThen.BOUNCE]


class DriftVersion:
    """A drift's two versions, which its settings are named after."""

    A = 'a'
    B = 'b'


DRIFT_VERSIONS = [DriftVersion.A, DriftVersion.B]


class DriftValue:
    """What each version of a drift sets, as the file names it after the version's letter, like a_velocity."""

    AX_ADD = 'ax_add'
    BX_ADD = 'bx_add'
    CX_ADD = 'cx_add'
    DX_ADD = 'dx_add'
    VELOCITY = 'velocity'
    PROBABILITY = 'probability'
    DEGREE = 'degree'
    DEGREE_RANDOM = 'degree_random'
    SCALE = 'scale'
    SCALE_PROBABILITY = 'scale_probability'
    ROOT = 'root'
    ROOT_PROBABILITY = 'root_probability'


class ScaleKind:
    """Each scale type's name as the file and the scale pickers spell it, aliases included: ScaleType's member names in lower case, which test_scale_kinds.py checks."""

    MAJOR = 'major'
    IONIAN = 'ionian'
    DORIAN = 'dorian'
    PHRYGIAN = 'phrygian'
    LYDIAN = 'lydian'
    MIXOLYDIAN = 'mixolydian'
    MINOR = 'minor'
    AEOLIAN = 'aeolian'
    NATURAL_MINOR = 'natural_minor'
    LOCRIAN = 'locrian'
    HARMONIC_MINOR = 'harmonic_minor'
    MELODIC_MINOR = 'melodic_minor'
    HARMONIC_MAJOR = 'harmonic_major'
    MAJOR_PENTATONIC = 'major_pentatonic'
    MINOR_PENTATONIC = 'minor_pentatonic'
    BLUES = 'blues'
    MAJOR_BLUES = 'major_blues'
    CHROMATIC = 'chromatic'
    WHOLE_TONE = 'whole_tone'
    WHOLE_HALF_DIMINISHED = 'whole_half_diminished'
    HALF_WHOLE_DIMINISHED = 'half_whole_diminished'
    AUGMENTED = 'augmented'
    DORIAN_FLAT2 = 'dorian_flat2'
    LYDIAN_AUGMENTED = 'lydian_augmented'
    LYDIAN_DOMINANT = 'lydian_dominant'
    MIXOLYDIAN_FLAT6 = 'mixolydian_flat6'
    LOCRIAN_NATURAL2 = 'locrian_natural2'
    ALTERED = 'altered'
    BEBOP_DOMINANT = 'bebop_dominant'
    BEBOP_MAJOR = 'bebop_major'
    PROMETHEUS = 'prometheus'
    PHRYGIAN_DOMINANT = 'phrygian_dominant'
    DOUBLE_HARMONIC = 'double_harmonic'
    HUNGARIAN_MINOR = 'hungarian_minor'
    HUNGARIAN_MAJOR = 'hungarian_major'
    UKRAINIAN_DORIAN = 'ukrainian_dorian'
    PERSIAN = 'persian'
    NEAPOLITAN_MINOR = 'neapolitan_minor'
    NEAPOLITAN_MAJOR = 'neapolitan_major'
    ENIGMATIC = 'enigmatic'
    EGYPTIAN = 'egyptian'
    HIRAJOSHI = 'hirajoshi'
    IN_SEN = 'in_sen'
    IWATO = 'iwato'
    KUMOI = 'kumoi'
    YO = 'yo'
    RYUKYU = 'ryukyu'
    TODI = 'todi'
    MARWA = 'marwa'
    PURVI = 'purvi'


# How a scene's or a clip's setting of one part of a shape is named, like density_start.
SHAPE_SETTING = '{shape}_{part}'


def shape_setting(*, shape, part):
    """Return a scene's or a clip's setting of one part of a shape, like density_start."""
    return SHAPE_SETTING.format(shape=shape, part=part)


def sensible_generator_order(value):
    """Return a generator order made sensible: each entry a one-key map of a generator's kind to its name, anything else left
    out, never refused, since the order only says how the Generators page lists them; None for none."""
    entries = value if isinstance(value, list) else []
    kept = [dict(entry) for entry in entries if is_generator_entry(entry)]
    return kept or None


def is_generator_entry(entry):
    """Return whether an entry of a generator order is a one-key map of a generator's kind to a name."""
    if not isinstance(entry, dict) or len(entry) != 1:
        return False
    kind, name = next(iter(entry.items()))
    return kind in NAMED_GENERATORS and isinstance(name, str)
