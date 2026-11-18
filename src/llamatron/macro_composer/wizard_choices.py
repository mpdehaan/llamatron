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
"""What the song wizard is told, and the song made from it.

A WizardChoices holds the choices of one run of the wizard: the genre, a style template; the subgenre, one of the template's
kinds; the key, the tempo and the form. Choosing a subgenre fills the rest in with what the subgenre usually has, so that a
person who chooses nothing more still gets a song that sounds right, and may then change anything. The choices are kept in
the song they made, as plain data, so that the wizard can start from them again; the seed that fixed every roll of the
dice is kept with them and never shown.
"""

import copy
import functools
import random
import zlib

from llamatron.composition.file_format import PatternSetting, Row, Section
from llamatron.composition.generator_settings import PHRASING_DEFAULTS, PhrasingSettings
from llamatron.composition.groove import FactoryGroove
from llamatron.composition import limits, naming
from llamatron.strings import labels as labels_text, macro_composer as composer_text, marks as marks_text, names as names_text
from llamatron.composition.setlist import Setlist
from llamatron.macro_composer.interplay import LEAST_BUSY as LEAST_BUSY_BESIDE, MOST_BUSY as MOST_BUSY_BESIDE, USUAL_BUSY as USUAL_BUSY_BESIDE, WAITS, WAYS as WAYS_BESIDE
from llamatron.macro_composer.characters import GAUGES as PLAYER_GAUGES, HIGHEST as HIGHEST_PLACE, LOWEST as LOWEST_PLACE, PRESET_PLACE, gauges_of, preset
from llamatron.macro_composer.arranger import (
    HABITS, ROLE_HABITS,
    ACCIDENTAL_MARKS, BY_SECTION, PATTERN, chord_of, fits_by_halves, shares_a_bar, COMMON_TIME, DEFAULT_PHRASE_BARS, DRUMS, DRUM_TRACKS, EACH_SECTION, FILLS_COME, FILL_EVERY, KIND, PARTS, PHRASE_BARS, QUIET_NOTES, MELODY_ENGINE, METER, PICKS, ROLE_SOUNDS, ROLE_TITLE, ROLE_TITLES, SOUNDS, WITHOUT_PIECES, PLAYER, PLAYERS, ROLE, ROLES, SOUND, TRAIT, VALUE, WITHOUT, bar_length, fits,
    BARS, CHORD_TRAIT, CHORD_TRAIT_FIELD, FORM, HELD, PLAYS, GENRE, KEY, NAME, ROOT, SCALE_TYPE, SECTIONS, SEED, STYLE, TEMPLATE, TEMPLATES, TEMPO, TITLE, TRAITS, TYPE, USUAL,
    BREAK, BREAK_CUT, HIGHEST_NOTE, KEPT_BESIDE_A_BREAK, LOWEST_NOTE, MELODY, NO_BREAK, PIECE_SOUNDS, PLAYED_DRUM, PLAYED_NOTE, PLAYED_SOUND,
    ANSWERS, BESIDE, BESIDE_BUSY, BESIDE_WAYS, FIGURE,
    arranged, forms_of, picked, player_of, section_of, share_in, share_of, style_in, style_named, style_names, values_of, variant_named, variants_of, VARIANT, VARIANT_SAYS,
)
from llamatron.macro_composer.composer import composed
from llamatron.macro_composer import hook_kinds, line_edits, phrasing, tune_fit
from llamatron.macro_composer.arranger import KICK as KICK_PIECE, MORE_RIFFS, NOBODY, OWN_TUNES, RIFF_OWN, TAKEN_TUNES, TUNE_BY, TUNE_BY_SONG, TUNE_PHRASING
from llamatron.macro_composer.players import BASS as BASS_PLAYER
from llamatron.macro_composer.notation import NONE as NO_HIT
from llamatron.macro_composer.arranger import CHORDS, DYNAMICS, EIGHTHS_IN_WHOLE, GROOVE, LOUDNESS as LOUDNESS_OF, NO_GROOVE, SCENE_SETTINGS, form_of
from llamatron.macro_composer.loudness import LEAST_DYNAMICS, LEVELS as LOUDNESS_LEVELS, MOST_DYNAMICS, USUAL_DYNAMICS, drum_levels, note_levels, with_own
from llamatron.macro_composer.melody import ANSWER, HOOK_KIND, HOOK_NOTES, LINE, LINE_NOTES
from llamatron.macro_composer.phrasing import LINE_BREATH, LINE_EARLY
from llamatron.macro_composer.riffs import (ACCENT_CHORDS, BAR_COUNTS, BETWEEN_WAYS, FIRST_TAKE as FIRST_RIFF_TAKE, IN_FULL, MOVES_WHOLE, MUTED_ROOTS, NOTES_WAYS, RIFF, RIFF_BAR_COUNT, RIFF_BARS,
                                            RIFF_BETWEEN, RIFF_KINDS, RIFF_LINE, RIFF_NOTES, RIFF_ROLES, RIFF_TAKE, RIFF_UNDER_TUNE, RIFF_WITH_CHORDS, SINGLE_NOTES, UNDER_TUNE_WAYS, WITH_CHORDS_WAYS,
                                            accent_bars, bars_of as riff_bars_of, flattened_in, line_of as riff_line_of)
from llamatron.macro_composer.joins import BUILD, DROP_OUT, FILL_OF_JOIN, LEAVES, STOPS, TAIL
from llamatron.macro_composer.song_plan import (
    BIG, BY_PLACE, FADED, FADES, UNFADED, SWELL_END, SWELL_START, PHRASING_WAYS, RISES, RISING, SCALE_OF_PLACE, SCENE_TEMPO, SCENE_TEMPO_END, SCENE_TEMPO_START, CONTRAST, ENERGY, FILL_SIZE, FILL_SIZES, HIGHEST_ENERGY, LOWEST_ENERGY, MEDIUM, NOT_AT_ALL, PHRASING, PLAN_OF_SONG, ROOT_OF_PLACE, SAID_OF_SECTION, SETUP, SMALL,
    REACTS, TEMPO_END_OF_PLACE, TEMPO_OF_PLACE, TYPE_OF_PLACE, USUAL_CONTRAST, SongPlan,
)
from llamatron.composition.song_file_error import SongFileError
from llamatron.macro_composer.breaks import LEAST_CUT, MOST_CUT, break_names
from llamatron.macro_composer.notation import ACCIDENTAL, DEGREE, FLAT, KIT, LINES, OCTAVE, REST, SHARP, STEPS, VELOCITY, LOWEST_VELOCITY, HIGHEST_VELOCITY
from llamatron.macro_composer.melody import ARTICULATION, CHROMATIC, DEFAULT_EVOLVE, DEFAULT_LENGTHS, ENGINE, LENGTHS, LOUDNESS, PARTS_OF_A_LENGTH, EVOLVE, HALF_STEPS, LEAPS, MOVE, NOTES_IN_OCTAVE, DEFAULT_GAUGES, EVOLVING, FIRST_HOOK_TAKE, GRID, HIGHEST_GAUGE, HOOK, HOOK_TAKE, LOWEST_GAUGE, ROTATE, ROTATIONS, SERIAL, SMART, STEP_WALK
from llamatron.music.note import ROOT_NAMES, SEMITONES_ABOVE_C
from llamatron.playback.song_renderer import SongRenderer
from llamatron.support.version import VERSION as A_VERSION
from llamatron.strings import errors

# The fields of the choices as a song keeps them.
SUBGENRE = 'subgenre'
# The ends of a style's usual tempos, in its template.
LOWEST = 'lowest'
HIGHEST = 'highest'
# The scale types a song may be made in, the plainest first, and the root each starts on until one is chosen.
MAJOR = 'major'
# The octave of a player whose style names none.
USUAL_OCTAVE = 4
MINOR = 'minor'
SCALE_TYPES = [MAJOR, MINOR]
USUAL_ROOTS = {MAJOR: 'C', MINOR: 'E'}
# How long a section that is one held chord lasts, in bars.
HELD_BARS = 1
# The seeds a run draws from: large enough that two runs seldom share one, small enough to read in a file.
# What a progression left to chance is drawn by, and how many times the subgenre's usual one counts.
PROGRESSION_SEED = 'progression {}'
USUAL_COUNTS = 2
FIRST_SEED = 1
LAST_SEED = 999999


def data_laid_over(*, under, over):
    """Plain data with other data laid over it: a mapping's fields are laid over field by field, and anything else is replaced."""
    if isinstance(under, dict) and isinstance(over, dict):
        return {**under, **{field: data_laid_over(under=under[field], over=value) if field in under else value for field, value in over.items()}}
    return over


@functools.cache
def style_of(genre):
    """Return a genre's style template, read once however often it is asked for; nothing changes it."""
    return style_named(genre)


def genre_names():
    """Return the genres there are, by the names their choices are kept under, in the order of their titles."""
    return sorted(style_names(), key=genre_title)


def genre_title(genre):
    """Return a genre's name as people read it."""
    return style_of(genre)[TITLE]


# How often a fill comes, by position: never, at the end of each section, every four bars, every two.
FEWEST_FILLS = 1
EACH_SECTION_FILLS = 2
MOST_FILLS = 4
FILLS_EVERY = {1: 0, 4: 2, 3: 4, 2: EACH_SECTION}
FILLS_KEPT = 'fills'
QUIET_NOTES_KEPT = 'quiet_notes'
# The drum break chosen, kept as its name or as NO_BREAK where a subgenre built on a break plays none, how far it is cut up,
# and the smart melody style's gauges that were moved.
BREAK_KEPT = 'break'
BREAK_CUT_KEPT = 'break_cut'
GAUGES_KEPT = 'melody_gauges'
MELODY_SETTINGS_KEPT = 'melody_settings'
HOOK_KEPT = 'hook'
HOOK_TAKE_KEPT = 'hook_take'
# What pieces of the kit sound as, kept as the song's picks hold them, and the note a piece first plays in a General MIDI sound.
PIECE_SOUNDS_KEPT = 'piece_sounds'
PLAYER_GAUGES_KEPT = 'player_gauges'
PLAYER_ROWS_KEPT = 'player_rows'
# The answers remembered until a choice changes.
PIECES_ANSWER = 'pieces'
QUIET_NOTES_ANSWER = 'quiet notes'
BARS_ANSWER = 'bars offered'
HOOK_ANSWER = 'hook notes'
HOOK_LINE_ANSWER = 'hook line'
HOOK_PART_ANSWER = 'hook part'
# How far a sharp or a flat moves a note, in half steps.
HALF_STEPS_OF_ACCIDENTAL = {SHARP: 1, FLAT: -1}
# What is kept of the player beside the tune: who answers, the one thing done in every section or None for the genre's plan, and how busy; and a section's own choice.
BESIDE_KEPT = 'beside'
BY = 'by'
WAY = 'way'
BUSY_BESIDE = 'busy'
# What a genre says of playing beside the tune.
INTERPLAY = 'interplay'
PLAN = 'plan'
BY_SUBGENRE = 'by_subgenre'
USUAL_PIECE_NOTE = 48
# The key a song keeps the kit's pieces that are switched off under.
PIECES_OFF_KEPT = 'pieces_off'
# One guitarist or two, and the key a template describes its one guitarist under, with the players and the way it names.
TWO_GUITARISTS = 2
ONE_GUITARIST_COUNT = 1
GUITARIST_COUNTS = (ONE_GUITARIST_COUNT, TWO_GUITARISTS)
GUITARISTS_KEPT = 'guitarists'
ONE_GUITARIST = 'one_guitarist'
CHORDS_PLAYER = 'chords'
SOLO_PLAYER = 'solo'
SOLO_WAY = 'way'
# The band's Sounds: every player's usual sound, or the nearest acoustic, electric or synthetic one.
USUAL_SOUNDS = 'usual'
ACOUSTIC = 'acoustic'
ELECTRIC = 'electric'
SYNTH = 'synth'
BAND_SOUNDS = (USUAL_SOUNDS, ACOUSTIC, ELECTRIC, SYNTH)
SOUNDS_KEPT = 'sounds'
BAND_SOUNDS_KEPT = 'band_sounds'
# The key a template keeps the sounds that stand in for a player under, by player and subgenre.
STAND_INS = 'stand_ins'
# General MIDI's families, eight sounds each, by their place; the last two, percussive sounds and sound effects, play no notes a part can use.
PIANOS = 0
ORGANS = 2
GUITARS = 3
BASSES = 4
STRINGS = 5
ENSEMBLES = 6
BRASS = 7
REEDS = 8
PIPES = 9
SYNTH_LEADS = 10
SYNTH_PADS = 11
# The nearest sound of each kind for a sound of a family, by General MIDI number: an acoustic band's guitar is a steel-string
# guitar, its bass an upright, its keyboard a piano; an electric band's keyboard is an electric piano; a synth band's guitar a saw lead.
NEAREST = {
    ACOUSTIC: {PIANOS: 1, ORGANS: 1, GUITARS: 26, BASSES: 33, SYNTH_LEADS: 74, SYNTH_PADS: 49},
    ELECTRIC: {PIANOS: 5, GUITARS: 28, BASSES: 34, SYNTH_LEADS: 30, SYNTH_PADS: 17},
    SYNTH: {PIANOS: 6, ORGANS: 90, GUITARS: 82, BASSES: 39, STRINGS: 51, ENSEMBLES: 55, BRASS: 63, REEDS: 81, PIPES: 83},
}
# The sounds that are already of each kind and so stay: acoustic pianos, guitars and bass; electric pianos, guitars and basses; synth basses and strings.
KEPT_BY = {
    ACOUSTIC: (1, 2, 3, 4, 25, 26, 33),
    ELECTRIC: (5, 6, 27, 28, 29, 30, 31, 32, 34, 35, 36, 37, 38),
    SYNTH: (39, 40, 51, 52, 55, 63, 64),
}


def family_of(sound):
    """Return the place of the General MIDI family a sound is in."""
    return (sound - limits.MIN_GM_SOUND) // limits.GM_FAMILY_SIZE


# The melody styles, and the key a song keeps the one chosen under.
MELODY_STYLES = (SMART, STEP_WALK, SERIAL, EVOLVING)
# The melody styles the seven gauges steer.
GAUGED_STYLES = (SMART,)
# A melody style's own settings, by the style, the usual style's under None: for the evolving style how far each new line moves
# up and how many notes later it starts, each a number with its lowest and highest; for the serial style whether the row is
# all twelve notes, whether a note may leap to any octave and whether a form of the row may start anywhere in it, each true or
# false with what it is where the genre does not say. How far a tune ranges is not one: it is the Range gauge of the player.
MELODY_SETTINGS_OF = {None: (), STEP_WALK: (), SMART: (), EVOLVING: (MOVE, ROTATE), SERIAL: (CHROMATIC, LEAPS, ROTATIONS)}
MELODY_NUMBERS = {MOVE: (0, 4), ROTATE: (0, 4)}
MELODY_SWITCHES = {CHROMATIC: False, LEAPS: False, ROTATIONS: True}
EVOLVE_SETTINGS = (MOVE, ROTATE)
# The rows of numbers the serial style deals to a player's notes in turn, each with the lowest and highest number of a cell
# and what a row is where the genre gives the player none, which plays as no row would: how many steps a note lasts, how
# much louder or softer than the player a note is, and how many quarters of a note's length sound.
PLAYER_ROWS = (LENGTHS, LOUDNESS, ARTICULATION)
ROW_LIMITS = {LENGTHS: (1, 8), LOUDNESS: (-16, 16), ARTICULATION: (1, PARTS_OF_A_LENGTH)}
ROWS_UNASKED = {LENGTHS: DEFAULT_LENGTHS, LOUDNESS: (0,) * len(DEFAULT_LENGTHS), ARTICULATION: (PARTS_OF_A_LENGTH,) * len(DEFAULT_LENGTHS)}
FEWEST_ROW_CELLS = 1
MOST_ROW_CELLS = 16
MELODY_STYLE = 'melody_style'
# The traits of the whole song the wizard offers: the chords, under either name a genre gives them, the feel and the drum fills.
PROGRESSION_TRAITS = ('chords', 'harmony')
FILLS_TRAITS = ('fills',)
# The key a song keeps its own sections under, and the letter the first section that differs from its kind's first is named with.
OWN_SECTIONS = 'own_sections'
PREVIEW_NAME = 'preview'
# The key of the answer kept of a kind of section's tune in the set the choices make.
TUNE_MADE_ANSWER = 'tune made'
# Which take of its tune each kind of section has, kept with the song's extras, the first take being the tune the choices write;
# the seed another take is drawn from; and the key of the answer kept of a take's pattern.
TUNE_TAKES = 'tune_takes'
FIRST_TUNE_TAKE = 0
TUNE_TAKE_SEED = '{seed} {kind} tune take {take}'
TUNE_TAKEN_ANSWER = 'tune taken'
# The name the band's settings that are one value each are counted under.
GENRE_SETTING = 'setting'
# What another genre gives up of what was chosen by hand, and what it keeps, each counted: the band's settings, the sections whose
# chords were written by hand, the form, the tunes of a later take, the riff, and the tunes whose notes were written by hand.
LOST_BAND_SETTINGS = 'band settings'
LOST_OWN_CHORDS = 'chords written by hand'
LOST_FORM = 'form'
LOST_TUNE_TAKES = 'tune takes'
LOST_RIFFS = 'riffs'
KEPT_OWN_TUNES = 'tunes written by hand'
KEPT_OWN_RIFFS = 'riffs written by hand'
# The extras of a song that are settings of one genre's band and song, which another genre gives up.
EXTRAS_OF_ONE_GENRE = (PLAN_OF_SONG, MELODY, GROOVE, DYNAMICS, LOUDNESS_OF, TUNE_BY, TUNE_BY_SONG)
STAGES_ANSWER = 'stages'
JOINS_ANSWER = 'joins'
SETUP_BARS_ANSWER = 'setup bars'
RIFF_ABLE_ANSWER = 'riff able'
# The name of the riff asked for to find who can play one in a kind of section.
TRIAL_RIFF = 'trial riff'
# Where a riff is played.
RIFF_IN_INTRO = 'in the intro'
RIFF_UNDER_VERSES = 'under the verses'
RIFF_INTRO_AND_VERSES = 'in the intro and under the verses'
RIFF_UNDER_CHORUSES = 'under the choruses'
RIFF_EVERYWHERE = 'everywhere'
RIFF_SAID_WAYS = (RIFF_INTRO_AND_VERSES, RIFF_IN_INTRO, RIFF_UNDER_VERSES, RIFF_UNDER_CHORUSES, RIFF_EVERYWHERE)
# A riff's settings, each with what may be chosen, the first what a riff has until another is chosen.
RIFF_SETTINGS = {RIFF_NOTES: NOTES_WAYS, RIFF_BAR_COUNT: tuple(reversed(BAR_COUNTS)), RIFF_BETWEEN: BETWEEN_WAYS, RIFF_UNDER_TUNE: UNDER_TUNE_WAYS, RIFF_WITH_CHORDS: WITH_CHORDS_WAYS}
assert (RIFF_SETTINGS[RIFF_NOTES][0], RIFF_SETTINGS[RIFF_BAR_COUNT][0], RIFF_SETTINGS[RIFF_BETWEEN][0]) == (SINGLE_NOTES, RIFF_BARS, MUTED_ROOTS)
assert (RIFF_SETTINGS[RIFF_UNDER_TUNE][0], RIFF_SETTINGS[RIFF_WITH_CHORDS][0]) == (IN_FULL, MOVES_WHOLE)
RIFF_SETTING_ANSWER = 'riff setting'
INTRO_KIND = 'intro'
REACTS_ANSWER = 'reacts'
DYNAMICS_ANSWER = 'dynamics'
# The swings a song may be played with, the lightest first of those of the eighths and then of the sixteenths, and the steps of
# a bar a genre written in triplets counts, which is swung as written and takes none.
SWINGS = (NO_GROOVE, FactoryGroove.EIGHTH_SWING_58, FactoryGroove.EIGHTH_SWING_66, FactoryGroove.SWING_54, FactoryGroove.SWING_58, FactoryGroove.SWING_62, FactoryGroove.SWING_66)
TRIPLET_GRID = 12
LEVELS_ANSWER = 'levels'
# How far a trial moves a level to hear whether the level is played at all.
LEVEL_TRIAL = 20
MIDDLE_VELOCITY = 64
# Where a player comes in and where a player lays out.
FROM_THE_START = 'from the start'
AFTER_THE_INTRO = 'after the intro'
IN_FIRST_CHORUS = 'in the first chorus'
AFTER_FIRST_VERSE = 'after the first verse'
IN_LAST_CHORUS = 'late, in the last chorus'
COMES_IN_WAYS = (FROM_THE_START, AFTER_THE_INTRO, AFTER_FIRST_VERSE, IN_FIRST_CHORUS, IN_LAST_CHORUS)
NEVER_LAYS_OUT = 'never'
IN_BREAKDOWNS = 'only in breakdowns'
WHEN_QUIET = 'whenever it is quiet'
CHORUS_KIND = 'chorus'
VERSE_KIND = 'verse'
# The kinds of section that are a breakdown, by the names the genres give them, and the Energy at or under which a section is quiet.
BREAKDOWN_KINDS = ('bridge', 'breakdown', 'strip', 'thin', 'drift')
QUIET_ENERGY = 4
ARRANGED_ANSWER = 'arranged'
LINES_ANSWER = 'lines'
# What a section's lines are given of their own, by the line's count, and what is said of a line.
LINES_OF_SECTION = 'lines'
# A pattern's octave row counts one octave higher than a picture of a line does.
PATTERN_OCTAVES_OVER_PICTURE = 1
LINE_PLAYER = 'player'
LINE_BREATHES = 'breathes'
LINE_IS_HOOK = 'hook'
LINE_OWN = 'own'
PLAY_OF_SCENE = 'play'
PART = 'part'
# What a section can be given of its own in any genre, with or without a plan.
OWN_WITHOUT_PLAN = (CHORDS, TEMPO_OF_PLACE, TEMPO_END_OF_PLACE, ROOT_OF_PLACE, TYPE_OF_PLACE, FADES)
# How a song starts: the sections before its first section with a tune, each stage a section of its own that can be changed like any other.
FULL_BAND = 'full band'
STRAIGHT_IN = 'straight in'
DRUMS_FIRST = 'drums first'
DRUM_FILL_IN = 'drum fill in'
ONE_PLAYER_FIRST = 'one player first'
LAYERS = 'layers'
STARTS = (FULL_BAND, STRAIGHT_IN, DRUMS_FIRST, DRUM_FILL_IN, ONE_PLAYER_FIRST, LAYERS)
# How a song ends: the sections after its last section with a tune.
HELD_CHORD = 'held chord'
HARD_STOP = 'hard stop'
SLOWS_DOWN = 'slows down'
STRIPS_DOWN = 'strips down'
ONE_PLAYER_ALONE = 'one player alone'
REPEAT_AND_FADE = 'repeat and fade'
OUTRO_THEN_CHORD = 'outro, then held chord'
ENDS = (HELD_CHORD, OUTRO_THEN_CHORD, HARD_STOP, SLOWS_DOWN, STRIPS_DOWN, ONE_PLAYER_ALONE, REPEAT_AND_FADE)
# The ways whose stages are played by some of the band, the first player first, and the ways with stages of the setup's length.
WAYS_WITH_FIRST_PLAYER = (ONE_PLAYER_FIRST, LAYERS, STRIPS_DOWN, ONE_PLAYER_ALONE)
WAYS_WITH_SETUP_BARS = (DRUMS_FIRST, DRUM_FILL_IN, ONE_PLAYER_FIRST, LAYERS, OUTRO_THEN_CHORD, SLOWS_DOWN, STRIPS_DOWN, ONE_PLAYER_ALONE, REPEAT_AND_FADE)
# A song that slows down ends at this share of its tempo.
SLOWED_TO = (2, 3)
OUTRO_KIND = 'outro'
START_KEPT = 'starts'
END_KEPT = 'ends'
FIRST_PLAYER_KEPT = 'first_player'
SETUP_BARS_KEPT = 'setup_bars'
# What each respect of the lines' breathing may be.
PHRASING_OFFERED = {phrasing.BREATH: tuple(phrasing.BREATHS), phrasing.LINE_LENGTHS: phrasing.LINE_LENGTH_WAYS, phrasing.EARLY_NOTES: tuple(range(phrasing.FEWEST_EARLY, phrasing.MOST_EARLY + 1))}
# What a section of the form is given of its own, kept with the section so that it moves, copies and goes with it.
OWN_OF_SECTION = 'own'
# How a section may leave, by the words a person chooses, each as the plan's join.
LEAVES_NOTHING = 'nothing'
LEAVES_SMALL_FILL = 'a small fill'
LEAVES_MEDIUM_FILL = 'a medium fill'
LEAVES_BIG_FILL = 'a big fill'
LEAVES_AS_JOIN = {
    LEAVES_SMALL_FILL: {FILL_SIZE: SMALL}, LEAVES_MEDIUM_FILL: {FILL_SIZE: MEDIUM}, LEAVES_BIG_FILL: {FILL_SIZE: BIG},
    STOPS: {TAIL: STOPS}, DROP_OUT: {TAIL: DROP_OUT}, BUILD: {TAIL: BUILD}, LEAVES_NOTHING: {},
}
SETUP_USUAL = 'when it helps'
# The questions a form is made from, the kinds of section they are about and the answers offered.
VERSES_FIRST = 'verses first'
PRE_CHORUSES = 'pre-choruses'
SOLOS = 'solos'
LAST_CHORUSES = 'last choruses'
VERSE_KIND = 'verse'
CHORUS_KIND = 'chorus'
PRE_CHORUS = 'pre-chorus'
BRIDGE = 'bridge'
SOLO = 'solo'
DRUM_SOLO_KIND = 'drum solo'
ENDING = 'ending'
NO = 'no'
YES = 'yes'
ONE = '1'
TWO = '2'
NONE_OF = '0'
BEFORE_EVERY = 'before every chorus'
BEFORE_FIRST_TWO = 'before the first 2 choruses'
YES_OR_NO = (NO, YES)
COUNTS_ONE_OR_TWO = (ONE, TWO)
SOLO_COUNTS = (NONE_OF, ONE, TWO)
PRE_CHORUS_ANSWERS = (NO, BEFORE_EVERY, BEFORE_FIRST_TWO)
# The shape of a section's lines: one of its kind's shapes by name, kept with the section, and what the field says of the kind's own.
SHAPE_OF_SECTION = 'shape'
SHAPES = 'shapes'
SHAPE_USUAL = 'usual'
INTRO = 'intro'
INTRO_HOOK = 'intro_hook'
BARS_IN_A_LINE = 2
HIGHER = 'higher'
VARIED = 'varied'
MARKS_TYPED = {'b': FLAT, '#': SHARP}
FIRST_DEGREE_OF_SCALE = 1
LAST_DEGREE_OF_SCALE = 7
PLAN_ANSWER = 'plan'
ENERGY_ANSWER = 'energies'
# The parts of a hook's kind and what each may be.
HOOK_PARTS = {hook_kinds.CONTOUR: hook_kinds.CONTOURS, hook_kinds.RHYTHM: tuple(hook_kinds.RHYTHMS), hook_kinds.DETAIL: hook_kinds.DETAILS}
# What a song file lays over the song's picks, as a song keeps it.
EXTRAS_KEPT = 'song'
STAGES_KEPT = 'stages'
FIRST_VARIANT_LETTER = 'a'
# How near a made section's length must be to the length asked, in seconds: far less than any bar lasts.
PART_OF_A_BAR = 0.01
# A section may be half or twice its kind's usual length.
HALF = 2
# How busy a player may be, and how busy each is until chosen: a little past the plainest, so that a song has turns and fills.
LEAST_BUSY = 1
MOST_BUSY = 4
USUAL_BUSY = 2
def own_copy_of(entry):
    """Return a section's entry sharing no list and no dictionary with the entry given."""
    return copy.deepcopy(entry)


# Two chords typed with a dash between share a bar.
SHARES_A_BAR = '-'
CHORDS_IN_A_SHARED_BAR = 2


def chords_from_text(text):
    """Return chords typed as degrees with a space between, a flat or a sharp before a degree, such as 6 4 1 b7, two chords that share a bar joined by a dash, such as 1-5, as the arranger reads them."""
    def chord_typed(word):
        mark = word[0] if word and word[0] in MARKS_TYPED else None
        number = word[1:] if mark else word
        if not number.isdigit() or not FIRST_DEGREE_OF_SCALE <= int(number) <= LAST_DEGREE_OF_SCALE:
            raise ValueError(errors.ERR_WIZARD_CHORDS.format(value=text))
        return {DEGREE: int(number), ACCIDENTAL: MARKS_TYPED[mark]} if mark else int(number)
    chords = []
    for word in str(text).split():
        # Two chords joined by a dash share a bar, each half of it.
        halves = word.split(SHARES_A_BAR)
        if len(halves) > CHORDS_IN_A_SHARED_BAR:
            raise ValueError(errors.ERR_WIZARD_CHORDS.format(value=text))
        chords.append(chord_typed(word) if len(halves) == 1 else [chord_typed(half) for half in halves])
    if not chords:
        raise ValueError(errors.ERR_WIZARD_CHORDS.format(value=text))
    if any(shares_a_bar(chord) for chord in chords) and not fits_by_halves(chords):
        raise ValueError(errors.ERR_WIZARD_CHORDS_SHARED.format(most=limits.MAX_PROGRESSION_CHORDS // CHORDS_IN_A_SHARED_BAR, value=text))
    return chords


def chords_as_text(chords):
    """Return chords as they are typed."""
    marks = {accidental: mark for mark, accidental in MARKS_TYPED.items()}

    def typed(chord):
        return marks.get(chord_of(chord).get(ACCIDENTAL), '') + str(chord_of(chord)[DEGREE])
    return ' '.join(SHARES_A_BAR.join(typed(half) for half in chord) if shares_a_bar(chord) else typed(chord) for chord in chords)


@functools.cache
def melody_works(*, genre, subgenre, style, variant=None):
    """Return whether a subgenre's tunes can be sketched by a melody style, found by making a song, once: a genre whose tunes
    are written as rows, with no rhythms to walk, takes only the style it was written for."""
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre)
    choices.take_variant(variant)
    choices.set_seed(FIRST_SEED)
    try:
        Setlist.from_data(data=composed(given=arranged(style=style_of(genre), song={**choices.song_picks(subgenre), MELODY_ENGINE: style}), version=A_VERSION))
    except (ValueError, IndexError, KeyError, SongFileError):
        return False
    return True


@functools.cache
def melody_is_usual(*, genre, subgenre, style, variant=None):
    """Return whether a melody style sketches a subgenre's tunes just as the genre does unasked, found by making both, once:
    such a style is the usual one under its own name, and is nothing to choose."""
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre)
    choices.take_variant(variant)
    choices.set_seed(FIRST_SEED)
    song = choices.song_picks(subgenre)
    return arranged(style=style_of(genre), song={**song, MELODY_ENGINE: style})[PARTS] == arranged(style=style_of(genre), song=song)[PARTS]


@functools.cache
def hook_matters(*, genre, subgenre, form, variant=None):
    """Return whether a hook changes a subgenre's song in a form, found by making the song with one and without, once: where
    nobody carries a tune in the sections that mark a hook, a hook is nothing to choose."""
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre)
    choices.take_variant(variant)
    choices.set_form(form)
    choices.set_seed(FIRST_SEED)
    song = choices.song_picks(subgenre)
    return arranged(style=style_of(genre), song={**song, HOOK: True})[PARTS] != arranged(style=style_of(genre), song={**song, HOOK: False})[PARTS]


@functools.cache
def bars_work(*, genre, subgenre, kind, bars, plays=None, variant=None):
    """Return whether a subgenre's parts can fill a section of a kind at a length, found by making one and measuring it, once:
    some parts are written over several bars and divide only some lengths, and some, as a chorus of twelve bars, last as long
    as they are written whatever is asked. Given the section's players, only their parts are asked, since a part that sits
    out cannot time the section."""
    style = style_in(style=style_of(genre), template=subgenre, variant=variant)
    song = {NAME: kind, TITLE: kind, STYLE: genre, TEMPLATE: subgenre, VARIANT: variant, KEY: {ROOT: USUAL_ROOTS[MAJOR], TYPE: MAJOR}, SEED: FIRST_SEED,
            FORM: [kind], SECTIONS: {kind: {KIND: kind, BARS: bars, **({} if plays is None else {PLAYS: list(plays)})}}}
    try:
        given = arranged(style=style, song=song)
        made = Setlist.from_data(data=composed(given=given, version=A_VERSION)).get_song(kind)
        seconds = sum(float(scene.seconds) for scene in SongRenderer(made).estimate())
    except (ValueError, SongFileError):
        return False
    wanted = float(bars * bar_length(str(picked(style=style, song=song).get(METER, COMMON_TIME))) * QUARTERS_IN_WHOLE * SECONDS_IN_MINUTE / made.get_tempo())
    return abs(seconds - wanted) < PART_OF_A_BAR


# A tempo counts quarter notes a minute.
QUARTERS_IN_WHOLE = 4
SECONDS_IN_MINUTE = 60


class WizardChoices:
    """The choices of one run of the song wizard."""

    __slots__ = ('_extras', '_stages', '_hook_take', '_rows', '_genre', '_subgenre', '_root', '_scale_type', '_tempo', '_form', '_seed', '_ways', '_levels', '_own_gauges', '_beside', '_without', '_sections', '_melody', '_hook', '_sounds', '_band_sounds', '_guitarists', '_pieces_off', '_break', '_break_cut', '_gauges', '_piece_sounds', '_fills', '_quiet_notes', '_melody_settings', '_answers', '_answers_of', '_picks_kept', '_variant')

    def __init__(self):
        # Answers found by making the song, each kept until a choice changes.
        self._answers = {}
        self._answers_of = None
        # Every trait's pick, kept with what it was worked out from, since every field of every panel asks for it.
        self._picks_kept = None
        self._genre = None
        self._subgenre = None
        # The kind of song the subgenre makes, where the subgenre holds several.
        self._variant = None
        self._root = None
        self._scale_type = None
        self._tempo = None
        self._form = None
        self._seed = None
        # The band: each trait's way of playing where one was chosen, how busy each instrument's player is, and the players left out.
        self._ways = {}
        self._levels = {}
        self._own_gauges = {}
        self._rows = {}
        self._beside = None
        self._without = []
        # The form's sections once a person has changed them, each its kind and what it changes of the kind; None while a suggested form is followed.
        self._sections = None
        # The melody style chosen for the song's tunes, or None for the one the genre gives each player.
        self._melody = None
        # Whether the song has a hook, or None while the genre says.
        self._hook = None
        self._hook_take = FIRST_HOOK_TAKE
        # The sounds chosen: the band's, one of BAND_SOUNDS, which every player follows, and each player's own General MIDI sound, which overrides it.
        self._band_sounds = USUAL_SOUNDS
        self._sounds = {}
        # How many guitarists the band has: two, one for the chords and one for the solo, or one who plays both.
        self._guitarists = TWO_GUITARISTS
        # The pieces of the drum kit switched off.
        self._pieces_off = []
        # How often a fill comes, a position from FEWEST_FILLS to MOST_FILLS, or None while the drummer decides; and whether the snare's quiet notes are played.
        self._fills = None
        self._quiet_notes = True
        self._break = None
        self._break_cut = None
        self._gauges = {}
        self._melody_settings = {}
        self._piece_sounds = {}
        # What a song file lays over the song's picks: the song's plan, and anything a section is given, as its chords or a tune.
        self._extras = {}
        # How the song starts and ends, as chosen: the ways, the first player and the setup's bars.
        self._stages = {}

    # Reading and keeping the choices.

    @classmethod
    def from_data(cls, data):
        """Return the choices a song kept, leaving out whatever no longer fits, as a genre renamed since: what is left out is chosen again."""
        choices = cls()
        setters = [(GENRE, choices.set_genre), (SUBGENRE, choices.set_subgenre), (VARIANT, choices.take_variant), (ROOT, choices.set_root), (TYPE, choices.set_scale_type), (TEMPO, choices.set_tempo), (FORM, choices.set_form), (SEED, choices.set_seed)]
        for field, setter in setters:
            if (data or {}).get(field) is not None:
                try:
                    setter(data[field])
                except (TypeError, ValueError):
                    pass
        if choices.is_ready():
            choices._read_band(data)
        return choices

    def _read_band(self, data):
        """Take the band a song kept, each part through its setter, leaving out what no longer fits. A song kept before the
        band could be chosen names no levels, and is read as having none, so that the same choices still make the same song."""
        self._levels = {}
        self._own_gauges = {}
        self._rows = {}
        # A song kept before answering could be chosen keeps to what was made then.
        self._beside = None
        # And a song kept has the riff it kept, or none: the riff its kind of music gives a new song is no part of it.
        self._extras.pop(RIFF, None)
        kept = [(self.set_way, [dict(trait=trait, value=value) for trait, value in (data.get(PICKS) or {}).items()]),
                (self._set_level, [dict(player=player, level=level) for player, level in (data.get(PLAYERS) or {}).items()]),
                (self._set_kept_player_gauge, [dict(player=player, gauge=gauge, place=place) for player, places in (data.get(PLAYER_GAUGES_KEPT) or {}).items() for gauge, place in places.items()]),
                (self.set_role_in, [dict(role=role, on=False) for role in data.get(WITHOUT) or []]),
                (self.set_piece_on, [dict(piece=piece, on=False) for piece in data.get(PIECES_OFF_KEPT) or []]),
                (self._set_kept_fills, [dict(position=data[FILLS_KEPT])] if data.get(FILLS_KEPT) is not None else []),
                (self._set_kept_quiet_notes, [dict(on=False)] if data.get(QUIET_NOTES_KEPT) is False else []),
                (self._set_kept_break, [dict(name=data[BREAK_KEPT])] if data.get(BREAK_KEPT) else []),
                (self._set_kept_piece_sound, [dict(piece=piece, sounds_as=sounds_as) for piece, sounds_as in (data.get(PIECE_SOUNDS_KEPT) or {}).items()]),
                (self._set_kept_break_cut, [dict(position=data[BREAK_CUT_KEPT])] if data.get(BREAK_CUT_KEPT) is not None else []),
                (self._set_kept_guitarists, [dict(count=data[GUITARISTS_KEPT])] if data.get(GUITARISTS_KEPT) else []),
                (self._set_kept_band_sounds, [dict(sounds=data[BAND_SOUNDS_KEPT])] if data.get(BAND_SOUNDS_KEPT) else []),
                (self.set_sound, [dict(role=role, sound=sound) for role, sound in (data.get(SOUNDS_KEPT) or {}).items()]),
                (self._set_kept_beside, [dict(kept=data[BESIDE_KEPT])] if isinstance(data.get(BESIDE_KEPT), dict) else []),
                (self.set_own_sections, [dict(sections=data[OWN_SECTIONS])] if data.get(OWN_SECTIONS) else []),
                (self._set_kept_melody, [dict(style=data[MELODY_STYLE])] if data.get(MELODY_STYLE) else []),
                (self._set_kept_hook, [dict(on=data[HOOK_KEPT])] if isinstance(data.get(HOOK_KEPT), bool) else []),
                (self._set_kept_hook_take, [dict(take=data[HOOK_TAKE_KEPT])] if data.get(HOOK_TAKE_KEPT) else []),
                (self.set_gauge, [dict(name=name, position=position) for name, position in (data.get(GAUGES_KEPT) or {}).items()]),
                (self._set_kept_player_row, [dict(role=role, name=name, values=values) for role, rows in (data.get(PLAYER_ROWS_KEPT) or {}).items() for name, values in rows.items()]
                 if isinstance(data.get(PLAYER_ROWS_KEPT), dict) and all(isinstance(rows, dict) for rows in data[PLAYER_ROWS_KEPT].values()) else []),
                (self._set_kept_melody_setting, [dict(name=name, value=value) for name, value in (data.get(MELODY_SETTINGS_KEPT) or {}).items()]),
                (self._set_kept_extras, [dict(extras=data[EXTRAS_KEPT])] if data.get(EXTRAS_KEPT) else []),
                (self._set_kept_stages, [dict(stages=data[STAGES_KEPT])] if isinstance(data.get(STAGES_KEPT), dict) else [])]
        for setter, every in kept:
            for named in every:
                try:
                    setter(**named)
                except (TypeError, ValueError):
                    pass

    def to_data(self):
        """Return the choices made, as plain data a song keeps."""
        held = {GENRE: self._genre, SUBGENRE: self._subgenre, VARIANT: self._variant, ROOT: self._root, TYPE: self._scale_type, TEMPO: self._tempo, FORM: self._form, SEED: self._seed,
                PICKS: dict(self._ways) or None, PLAYERS: dict(self._levels) or None, WITHOUT: list(self._without) or None,
                PLAYER_GAUGES_KEPT: {player: dict(places) for player, places in self._own_gauges.items() if places} or None,
                PLAYER_ROWS_KEPT: {role: {name: list(row) for name, row in rows.items()} for role, rows in self._rows.items() if rows} or None,
                BESIDE_KEPT: dict(self._beside) if self._beside is not None else None,
                OWN_SECTIONS: [own_copy_of(entry) for entry in self._sections] if self._sections is not None else None,
                MELODY_STYLE: self._melody, HOOK_KEPT: self._hook, HOOK_TAKE_KEPT: self._hook_take or None, SOUNDS_KEPT: dict(self._sounds) or None,
                BAND_SOUNDS_KEPT: self._band_sounds if self._band_sounds != USUAL_SOUNDS else None,
                GUITARISTS_KEPT: self._guitarists if self._guitarists != TWO_GUITARISTS else None,
                PIECES_OFF_KEPT: list(self._pieces_off) or None, FILLS_KEPT: self._fills, QUIET_NOTES_KEPT: None if self._quiet_notes else False,
                BREAK_KEPT: self._break, BREAK_CUT_KEPT: self._break_cut, GAUGES_KEPT: dict(self._gauges) or None, MELODY_SETTINGS_KEPT: dict(self._melody_settings) or None,
                PIECE_SOUNDS_KEPT: {piece: dict(sounds_as) for piece, sounds_as in self._piece_sounds.items()} or None,
                EXTRAS_KEPT: copy.deepcopy(self._extras) or None, STAGES_KEPT: dict(self._stages) or None}
        return {field: value for field, value in held.items() if value is not None}

    # The genre and the subgenre, which everything else follows.

    def get_genre(self):
        return self._genre

    def set_genre(self, genre):
        """Choose a genre, which leaves the subgenre to be chosen again, since each genre has its own."""
        if genre not in style_names():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_GENRE.format(value=genre))
        if genre != self._genre:
            self._genre = genre
            self._subgenre = None
            self._variant = None
            self._form = None
            self._sections = None
            self._stages = {}
            self._melody = None
            self._hook = None
            self._hook_take = FIRST_HOOK_TAKE
            # A plan is one genre's: its energies and its joins are the genre's own.
            self._extras.pop(PLAN_OF_SONG, None)
            self._extras.pop(MELODY, None)
            self._extras.pop(RIFF, None)
            self._extras.pop(GROOVE, None)
            # A player's loudness is one genre's player's.
            self._extras.pop(DYNAMICS, None)
            self._extras.pop(LOUDNESS_OF, None)
            self._extras.pop(TUNE_TAKES, None)
            # A riff whose notes were written by hand is the person's own, which no genre gives up: its players play it again wherever
            # a band has them and a form has its kinds of section.
            own_riffs = [entry for entry in self._extras.pop(MORE_RIFFS, []) if entry.get(RIFF_OWN) is not None]
            if own_riffs:
                self._extras[MORE_RIFFS] = own_riffs
            self._extras.pop(TUNE_BY, None)
            self._extras.pop(TUNE_BY_SONG, None)
            self._forget_band()

    def lost_with_genre(self):
        """Return what choosing another genre would give up of what was chosen by hand and what it would keep, each a dictionary of
        counts by kind that leaves out a kind counting nothing. Before a subgenre is chosen nothing has been chosen to lose."""
        if self._genre is None or self._subgenre is None:
            return {}, {}
        usual = WizardChoices()
        usual.set_genre(self._genre)
        usual.set_subgenre(self._subgenre)
        if self._variant != usual._variant:
            usual.set_variant(self._variant)
        own = self._band_as_counted()
        untouched = usual._band_as_counted()
        settings = sum(1 for name in own.keys() | untouched.keys() if own.get(name) != untouched.get(name))
        settings += sum(1 for name in EXTRAS_OF_ONE_GENRE if self._extras.get(name))
        lost = {LOST_BAND_SETTINGS: settings,
                LOST_OWN_CHORDS: sum(1 for entry in self._entries() if entry.get(OWN_OF_SECTION, {}).get(CHORDS)),
                LOST_FORM: int(self._sections is not None or self._form != usual._form),
                LOST_TUNE_TAKES: len(self._extras.get(TUNE_TAKES, {})) + int(self._hook_take != FIRST_HOOK_TAKE),
                LOST_RIFFS: int(bool(self._extras.get(RIFF))) + len([entry for entry in self._extras.get(MORE_RIFFS, []) if entry.get(RIFF_OWN) is None])}
        kept = {KEPT_OWN_TUNES: len(self._extras.get(OWN_TUNES, {})), KEPT_OWN_RIFFS: len([entry for entry in self._extras.get(MORE_RIFFS, []) if entry.get(RIFF_OWN) is not None])}
        return {kind: count for kind, count in lost.items() if count}, {kind: count for kind, count in kept.items() if count}

    def _band_as_counted(self):
        """Return every setting of the band another genre forgets, each under a name of its own, so that two bands can be compared
        setting by setting."""
        by_name = {(GENRE_SETTING, name): value for name, value in (
            (BESIDE_KEPT, self._beside), (WITHOUT, sorted(self._without)), (BAND_SOUNDS_KEPT, self._band_sounds), (GUITARISTS_KEPT, self._guitarists),
            (PIECES_OFF_KEPT, sorted(self._pieces_off)), (FILLS_KEPT, self._fills), (QUIET_NOTES_KEPT, self._quiet_notes), (BREAK_KEPT, self._break),
            (BREAK_CUT_KEPT, self._break_cut), (MELODY_STYLE, self._melody), (HOOK_KEPT, self._hook))}
        for kept_as, held in ((PICKS, self._ways), (PLAYERS, self._levels), (PLAYER_GAUGES_KEPT, self._own_gauges), (PLAYER_ROWS_KEPT, self._rows), (SOUNDS_KEPT, self._sounds),
                              (GAUGES_KEPT, self._gauges), (MELODY_SETTINGS_KEPT, self._melody_settings), (PIECE_SOUNDS_KEPT, self._piece_sounds), (STAGES_KEPT, self._stages)):
            for name, value in held.items():
                if isinstance(value, dict):
                    by_name.update({(kept_as, name, inner): each for inner, each in value.items()})
                else:
                    by_name[(kept_as, name)] = value
        return by_name

    def subgenres(self):
        """Return the chosen genre's subgenres, sorted by name, or none before a genre is chosen."""
        return sorted(self._style()[TEMPLATES]) if self._genre else []

    def get_subgenre(self):
        return self._subgenre

    def set_subgenre(self, subgenre):
        """Choose a subgenre of the genre, and take its usual tempo, scale and form, which a person may then change."""
        if subgenre not in self.subgenres():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SUBGENRE.format(value=subgenre))
        if subgenre != self._subgenre:
            self._subgenre = subgenre
            # The commonest kind of song the subgenre holds, which a person may change.
            self._variant = next(iter(self.variants()), None)
            self._take_usual_of_subgenre()

    def variants(self):
        """Return the kinds of song the subgenre holds, by name, the commonest first, or none where the subgenre is one kind."""
        if self._subgenre is None:
            return []
        return [entry[NAME] for entry in variants_of(style=style_of(self._genre), template=self._subgenre)]

    def get_variant(self):
        return self._variant

    def variant_says(self, *, variant=None):
        """Return the line that says what a kind of song is, the chosen kind unless one is named, or None."""
        entry = variant_named(style=style_of(self._genre), template=self._subgenre, variant=variant or self._variant) if self._subgenre else None
        return entry.get(VARIANT_SAYS) if entry else None

    def set_variant(self, variant):
        """Choose the kind of song the subgenre makes, and take the kind's usual tempo, scale, form and band, as choosing a subgenre does."""
        if variant not in self.variants():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_VARIANT.format(choices=', '.join(self.variants()), value=variant))
        if variant != self._variant:
            self._variant = variant
            self._take_usual_of_subgenre()

    def take_variant(self, variant):
        """Choose a kind of song a kept song or a check names, where the subgenre has that kind; none leaves the subgenre's commonest."""
        if variant is not None:
            self.set_variant(variant)

    def _take_usual_of_subgenre(self):
        """Take what the subgenre and its kind of song usually have, leaving behind whatever was chosen for another."""
        self._forget_band()
        self._tempo = self.usual_tempo()
        self._scale_type = self.usual_scale_type()
        self._root = USUAL_ROOTS[self._scale_type]
        self._form = None
        self._sections = None
        self._stages = {}
        self._melody = None
        self._hook = None
        self._hook_take = FIRST_HOOK_TAKE
        self._levels = {player: USUAL_BUSY for player in self._style().get(PLAYERS, {})}
        self._own_gauges = {}
        self._rows = {}
        self._beside = self._usual_beside()
        # A swing chosen was chosen beside another subgenre's or kind's own.
        self._extras.pop(GROOVE, None)
        self._take_riff_of_genre()

    def is_ready(self):
        """Return whether a song can be made: a genre and a subgenre are chosen, and the rest has its usual values."""
        return self._subgenre is not None

    # What the subgenre usually has.

    def _picks(self):
        """Return every trait's pick: the ways of playing chosen, and the subgenre's for the rest. The picks are worked out once
        for a genre, a subgenre and the ways chosen, and a caller never changes what is returned."""
        of = (self._genre, self._subgenre, self._variant, repr(self._ways))
        if self._picks_kept is None or self._picks_kept[0] != of:
            self._picks_kept = (of, self._picks_with(self._ways))
        return self._picks_kept[1]

    def usual_tempo(self):
        style = self._style()
        return self._picks().get(TEMPO, style[TRAITS][TEMPO][USUAL])

    def tempo_range(self):
        """Return the lowest and the highest tempo the genre usually has, which is said beside the tempo and never enforced."""
        tempos = self._style()[TRAITS][TEMPO]
        return tempos[LOWEST], tempos[HIGHEST]

    def usual_scale_type(self):
        """Return the scale type the subgenre's chords are usually in, or major where its chords say nothing of one."""
        style = self._style()
        trait = style.get(CHORD_TRAIT_FIELD, CHORD_TRAIT)
        entry = values_of(style=style, trait=trait).get(self._picks().get(trait), {})
        usual = entry.get(SCALE_TYPE, MAJOR)
        return usual if usual in SCALE_TYPES else MAJOR

    # The key and the tempo.

    def get_root(self):
        return self._root

    def set_root(self, root):
        if root not in ROOT_NAMES:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_ROOT.format(value=root))
        self._root = root

    def get_scale_type(self):
        return self._scale_type

    def set_scale_type(self, scale_type):
        if scale_type not in SCALE_TYPES:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SCALE_TYPE.format(value=scale_type))
        self._scale_type = scale_type

    def get_tempo(self):
        return self._tempo

    def set_tempo(self, tempo):
        """Set the tempo to any the tracker plays; the genre's usual range is advice."""
        if isinstance(tempo, bool) or not isinstance(tempo, int) or not limits.MIN_TEMPO <= tempo <= limits.MAX_TEMPO:
            raise ValueError(errors.ERR_WIZARD_TEMPO.format(low=limits.MIN_TEMPO, high=limits.MAX_TEMPO, value=tempo))
        self._tempo = tempo

    # The swing.

    def has_swing(self):
        """Return whether the song can be swung: a subgenre in four whose bars are not written in triplets, which swing already."""
        if not self.is_ready() or self.meter() != COMMON_TIME:
            return False
        habits = self._style().get(MELODY, {})
        return (habits if GRID in habits else habits.get(COMMON_TIME, {})).get(GRID) != TRIPLET_GRID

    def swings(self):
        return list(SWINGS)

    def swing_of_genre(self):
        """Return the swing the subgenre is usually played with, or none."""
        return self._style().get(GROOVE, NO_GROOVE) if self.has_swing() else NO_GROOVE

    def get_swing(self):
        return self._extras.get(GROOVE, self.swing_of_genre())

    def set_swing(self, swing):
        """Say the swing the song is played with, one of the grooves every set has or none; the subgenre's own is kept as the subgenre's."""
        if not self.has_swing() or swing not in SWINGS:
            raise ValueError(errors.ERR_WIZARD_SWING.format(choices=', '.join(SWINGS), value=swing))
        self._extras.pop(GROOVE, None)
        if swing != self.swing_of_genre():
            self._extras[GROOVE] = swing
        self._answers = {}

    # The form.

    def _forms(self):
        return forms_of(style=self._style(), song={TEMPLATE: self._subgenre}) if self.is_ready() else []

    def forms(self):
        """Return the names of the forms the subgenre suggests, the commonest first."""
        return [form[NAME] for form in sorted(self._forms(), key=share_of, reverse=True)]

    def get_form(self):
        """Return the form chosen, or the commonest of the subgenre's until one is, or None before a subgenre is chosen."""
        if self._form is not None:
            return self._form
        forms = self.forms()
        return forms[0] if forms else None

    def form_section_count(self, form):
        """Return how many sections a suggested form has."""
        return len(next((form_[SECTIONS] for form_ in self._forms() if form_[NAME] == form), []))

    def set_form(self, form):
        """Choose one of the forms the subgenre suggests, which puts its sections in place of any a person changed. How the song was
        chosen to start and to end is kept, with who starts alone and how long a stage lasts, where the new form can start and end so."""
        if form not in self.forms():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_FORM.format(value=form))
        start = self.get_start() if START_KEPT in self._stages else None
        end = self.get_end() if END_KEPT in self._stages else None
        kept = {field: value for field, value in self._stages.items() if field not in (START_KEPT, END_KEPT)}
        self._form = form
        self._sections = None
        self._stages = {}
        self._answers = {}
        for way, offered, set_way in ((start, self.starts, self.set_start), (end, self.ends, self.set_end)):
            if way is not None and way in offered():
                self._stages.update(kept)
                try:
                    set_way(way)
                except ValueError:
                    # A way the new form cannot be made with is given up, and the form starts or ends as it usually does.
                    pass
        if START_KEPT not in self._stages and END_KEPT not in self._stages:
            self._stages = {}

    # The form's sections, which follow the form chosen until a person changes one; the form is then the song's own.

    def has_own_form(self):
        """Return whether a person has changed the form's sections, so that the form is no longer one the subgenre suggests."""
        return self._sections is not None

    def _entries(self):
        """Return the sections in order, each its kind and what it changes of the kind: the song's own, or the chosen form's."""
        if self._sections is not None:
            return self._sections
        chosen = self.get_form()
        return [{KIND: kind} for kind in next((form[SECTIONS] for form in self._forms() if form[NAME] == chosen), [])]

    def _own_entries(self):
        """Return the song's own sections to change, starting them from the chosen form the first time."""
        if self._sections is None:
            self._sections = [dict(entry) for entry in self._entries()]
        return self._sections

    def _entry(self, place):
        entries = self._entries()
        if isinstance(place, bool) or not isinstance(place, int) or not 0 <= place < len(entries):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SECTION.format(value=place))
        return entries[place]

    def form_sections(self):
        """Return the sections of the form in the order they play, by name. A section is named after its kind, and one that
        differs from the first of its kind, in its bars or its players, gets a letter after the name, since sections of one
        name are the same section played again."""
        names = []
        seen = {}
        for entry in self._entries():
            own = (entry.get(BARS), tuple(entry[PLAYS]) if PLAYS in entry else None)
            if not self.has_song_plan() and self._own_without_plan(entry):
                # A section with chords, a tempo, a key or a scale of its own is a section of its own, where no plan makes one for each place.
                own = (*own, repr(sorted(self._own_without_plan(entry).items(), key=str)))
            # The kind as the genre describes it comes first, so that an unchanged section keeps the kind's plain name.
            variants = seen.setdefault(entry[KIND], [(None, None)])
            if own not in variants:
                variants.append(own)
            place = variants.index(own)
            names.append(entry[KIND] if not place else marks_text.MSG_WIZARD_SECTION_VARIANT.format(kind=entry[KIND], letter=chr(ord(FIRST_VARIANT_LETTER) + place)))
        return names

    def section_labels(self):
        """Return what each section is shown as, in order: its kind, and where the form has several of a kind, the kind with
        a dash and the section's count among them, as the tracker numbers every name it makes."""
        kinds = [entry[KIND] for entry in self._entries()]
        counts = {}
        labels = []
        for kind in kinds:
            counts[kind] = counts.get(kind, 0) + 1
            labels.append(kind if kinds.count(kind) == 1 else marks_text.MSG_WIZARD_SECTION_NUMBERED.format(kind=kind, number=counts[kind]))
        return labels

    def _song_sections(self):
        """Return the song's own sections as the arranger reads them, by name: each its kind and what it changes, with the chords and the scene's
        tempo, key and scale a section was given where no plan lays those out by place."""
        return {name: {**{field: value for field, value in entry.items() if field != OWN_OF_SECTION}, **self._as_section(entry)} for name, entry in zip(self.form_sections(), self._entries())}

    def _plan_with_lines(self, *, kind, plan, lines):
        """A section's plan of lines with what each line was given of its own laid over it: its notes, its breath and whether a note comes early."""
        usual = self._style()[SECTIONS][kind].get(PLAN, []) if plan is None else plan
        return [{**entry, **(lines.get(count) or {})} for count, entry in enumerate(copy.deepcopy(usual))]

    def _own_without_plan(self, entry):
        """What a section was given of its own that a song with no plan can still take: chords, a tempo, the tempo at its end, a key and a scale."""
        return {field: value for field, value in entry.get(OWN_OF_SECTION, {}).items() if field in OWN_WITHOUT_PLAN or field == LINES_OF_SECTION}

    def _as_section(self, entry):
        if self.has_song_plan():
            return {}
        own = self._own_without_plan(entry)
        settings = {}
        if TEMPO_END_OF_PLACE in own:
            settings.update({SCENE_TEMPO_START: own.get(TEMPO_OF_PLACE, self._tempo), SCENE_TEMPO_END: own[TEMPO_END_OF_PLACE]})
        elif TEMPO_OF_PLACE in own:
            settings[SCENE_TEMPO] = own[TEMPO_OF_PLACE]
        if ROOT_OF_PLACE in own or TYPE_OF_PLACE in own:
            settings[SCALE_OF_PLACE] = {ROOT_OF_PLACE: own.get(ROOT_OF_PLACE, self._root), TYPE_OF_PLACE: own.get(TYPE_OF_PLACE, self._scale_type)}
        if own.get(FADES):
            settings.update({SWELL_START: UNFADED, SWELL_END: FADED})
        if own.get(LINES_OF_SECTION):
            return {PLAN: self._plan_with_lines(kind=entry[KIND], plan=None, lines=own[LINES_OF_SECTION]), **({CHORDS: copy.deepcopy(own[CHORDS])} if CHORDS in own else {}), **({SCENE_SETTINGS: settings} if settings else {})}
        return {**({CHORDS: copy.deepcopy(own[CHORDS])} if CHORDS in own else {}), **({SCENE_SETTINGS: settings} if settings else {})}

    def _section(self, place):
        """Return a section as it will be played: its kind as the genre describes it, with what the section changes."""
        entry = self._entry(place)
        return section_of(name=entry[KIND], style=self._style(), song={SECTIONS: {entry[KIND]: entry}})

    def section_kinds(self):
        """Return the kinds of section the subgenre can play, in the genre's order: a kind nobody of the subgenre's band plays
        in, which would make no section at all, is left out, as is one whose parts do not fill its own length."""
        if not self.is_ready():
            return []
        sections = self._style()[SECTIONS]
        return [kind for kind, section in sections.items()
                if bars_work(genre=self._genre, subgenre=self._subgenre, variant=self._variant, kind=kind, bars=HELD_BARS if section.get(HELD) else section[BARS])]

    def section_kind(self, place):
        return self._entry(place)[KIND]

    def section_is_held(self, place):
        """Return whether a section is one held chord, which lasts a bar whatever is said."""
        return bool(self._section(place).get(HELD))

    def section_bars(self, place):
        section = self._section(place)
        return HELD_BARS if section.get(HELD) else section[BARS]

    def section_plays(self, place):
        """Return who plays in a section, by the names the genre gives its players."""
        return list(self._section(place).get(PLAYS, []))

    def section_usually_plays(self, place):
        """Return who plays in a section of its kind as the genre has the kind."""
        return list(self._usual(place).get(PLAYS, []))

    def add_section(self, *, place, kind):
        """Put a new section of a kind before a place in the form, as the genre describes the kind."""
        if kind not in self.section_kinds():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SECTION_KIND.format(value=kind))
        if isinstance(place, bool) or not isinstance(place, int) or not 0 <= place <= len(self._entries()):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SECTION.format(value=place))
        self._own_entries().insert(place, {KIND: kind})

    def copy_section(self, place):
        """Put a copy of a section straight after it."""
        entry = own_copy_of(self._entry(place))
        self._own_entries().insert(place + 1, entry)

    def remove_section(self, place):
        self._entry(place)
        if len(self._entries()) == 1:
            raise ValueError(errors.ERR_WIZARD_LAST_SECTION)
        del self._own_entries()[place]

    def move_section(self, *, place, offset):
        """Move a section earlier or later in the form, and return whether it moved, which it cannot past either end."""
        self._entry(place)
        moved = place + offset
        if not 0 <= moved < len(self._entries()):
            return False
        entries = self._own_entries()
        entries.insert(moved, entries.pop(place))
        return True

    def set_section_kind(self, *, place, kind):
        """Make a section another kind, as the genre describes that kind: what the section changed of its old kind is dropped."""
        self._entry(place)
        if kind not in self.section_kinds():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_SECTION_KIND.format(value=kind))
        self._own_entries()[place] = {KIND: kind}

    def _usual(self, place):
        return self._style()[SECTIONS][self._entry(place)[KIND]]

    def bars_offered(self, place):
        """Return the lengths a section may have, in bars: half its kind's usual length, the usual and twice that, leaving out
        any the genre's parts cannot fill, and nothing for a held section."""
        return list(self._remembered(key=(BARS_ANSWER, place), compute=lambda: self._bars_offered(place)))

    def _bars_offered(self, place):
        if self.section_is_held(place):
            return []
        usual = self._usual(place)[BARS]
        lengths = sorted({usual // HALF, usual, usual * HALF, self.section_bars(place)} - {0})
        return [bars for bars in lengths if bars == usual or self._bars_fit(place=place, bars=bars)]

    def _bars_fit(self, *, place, bars):
        """Return whether the players of a section can fill the section at a length: on their own, and then in this song, where
        a part may be written differently beside another section of the kind."""
        if not bars_work(genre=self._genre, subgenre=self._subgenre, variant=self._variant, kind=self._entry(place)[KIND], bars=bars, plays=tuple(self.section_plays(place))):
            return False
        trial = copy.deepcopy(self)
        trial._answers = {}
        trial._own_entries()[place][BARS] = bars
        try:
            trial.made_setlist(name=self._entry(place)[KIND], version=A_VERSION)
        except (ValueError, SongFileError):
            return False
        return True

    def set_section_bars(self, *, place, bars):
        if isinstance(bars, bool) or not isinstance(bars, int) or bars not in self.bars_offered(place):
            raise ValueError(errors.ERR_WIZARD_SECTION_BARS.format(value=bars))
        entry = self._own_entries()[place]
        entry.pop(BARS, None)
        if bars != self._usual(place)[BARS]:
            entry[BARS] = bars

    def set_section_plays(self, *, place, role, on):
        """Have a player play in a section or sit it out. A section keeps one player, and a length its players can fill."""
        self._role(role)
        plays = [name for name in self.roles() if (name in self.section_plays(place) or (on and name == role)) and (on or name != role)]
        if not plays:
            raise ValueError(errors.ERR_WIZARD_SECTION_NEEDS_PLAYER)
        entry = self._own_entries()[place]
        entry.pop(PLAYS, None)
        if sorted(plays) != sorted(self._usual(place).get(PLAYS, [])):
            entry[PLAYS] = plays
        # A length the players left cannot fill gives way to the kind's usual length.
        if BARS in entry and not self._bars_fit(place=place, bars=entry[BARS]):
            del entry[BARS]

    def set_own_sections(self, *, sections):
        """Take a form's sections a song kept, each through the setters, or none of them where one no longer fits."""
        kept = self._sections
        self._sections = []
        try:
            for place, entry in enumerate(sections):
                self.add_section(place=place, kind=entry[KIND])
                if BARS in entry:
                    self.set_section_bars(place=place, bars=entry[BARS])
                for role in self.roles():
                    if PLAYS in entry and (role in entry[PLAYS]) != (role in self.section_plays(place)) and role in entry[PLAYS]:
                        self.set_section_plays(place=place, role=role, on=True)
                for role in self.roles():
                    if PLAYS in entry and role not in entry[PLAYS] and role in self.section_plays(place):
                        self.set_section_plays(place=place, role=role, on=False)
                if BESIDE_KEPT in entry:
                    # What the answering player does in the section is kept as chosen, and is used wherever somebody answers there.
                    if entry[BESIDE_KEPT] not in WAYS_BESIDE:
                        raise ValueError(errors.ERR_WIZARD_NO_SUCH_WAY_BESIDE.format(value=entry[BESIDE_KEPT]))
                    self._sections[place][BESIDE_KEPT] = entry[BESIDE_KEPT]
                if entry.get(OWN_OF_SECTION):
                    self._sections[place][OWN_OF_SECTION] = {field: self._checked_own(field=field, value=value) for field, value in entry[OWN_OF_SECTION].items()}
            if not self._sections:
                raise ValueError(errors.ERR_WIZARD_LAST_SECTION)
        except (KeyError, TypeError, ValueError):
            self._sections = kept
            raise ValueError(errors.ERR_WIZARD_BAD_SECTIONS.format(value=sections)) from None

    # How the song starts and ends: stages before the first section with a tune and after the last, each a section of its own.

    def _drums_role(self):
        return next((role for role in self.roles() if self._role(role).get(DRUMS) and self.role_is_in(role)), None)

    def _usual_form_kinds(self):
        return next((form[SECTIONS] for form in self._forms() if form[NAME] == self.get_form()), [])

    def _intro_kind(self):
        """The kind of section a song of the subgenre opens with: the first of its form's, where that kind has no tune."""
        kinds = self._usual_form_kinds()
        sections = self._style()[SECTIONS]
        if not kinds or sections[kinds[0]].get(HELD):
            return None
        # A kind with a tune opens the song only where the form plays the kind once, at its start: one played again later is the song's body.
        return kinds[0] if not sections[kinds[0]].get(PLAN) or kinds.count(kinds[0]) == 1 else None

    def _ending_kind(self):
        """The kind of section that is one held chord, where the subgenre has one."""
        return next((kind for kind in self.section_kinds() if self._style()[SECTIONS][kind].get(HELD)), None)

    def _outro_kind(self):
        """The kind of section played after the last tune: the genre's outro where it has one, else its intro again."""
        return OUTRO_KIND if OUTRO_KIND in self.section_kinds() else self._intro_kind()

    def _stage_players(self, kind):
        """Who plays in a kind of section, the first player first and the rest in the band's order."""
        plays = [role for role in self.roles() if role in self._style()[SECTIONS][kind].get(PLAYS, []) and self.role_is_in(role)]
        first = self.get_first_player()
        return [first, *(role for role in plays if role != first)] if first in plays else plays

    def first_players(self):
        """Return who can start the song alone: the players of its opening kind of section."""
        kind = self._intro_kind()
        return [] if kind is None else [role for role in self.roles() if role in self._style()[SECTIONS][kind].get(PLAYS, []) and self.role_is_in(role)]

    def get_first_player(self):
        """Return who starts the song alone and is left alone at its end: the one chosen, or the first of the opening's players who is not the drummer."""
        offered = self.first_players()
        if self._stages.get(FIRST_PLAYER_KEPT) in offered:
            return self._stages[FIRST_PLAYER_KEPT]
        return next((role for role in offered if role != self._drums_role()), offered[0] if offered else None)

    def _setup_bars_possible(self):
        """How long a stage could last, in bars: half the opening kind's length, the length and twice it."""
        kind = self._intro_kind()
        if kind is None:
            return []
        usual = self._style()[SECTIONS][kind][BARS]
        return sorted({usual // HALF, usual, usual * HALF} - {0})

    def setup_bars_offered(self):
        """Return how long a stage of a start or an ending may last, in bars: of the lengths a stage could last, those the song as it starts and ends can be made with."""
        return list(self._remembered(key=SETUP_BARS_ANSWER, compute=lambda: [bars for bars in self._setup_bars_possible() if bars == self.get_setup_bars() or self._setup_bars_work(bars)]))

    def _setup_bars_work(self, bars):
        trial = copy.deepcopy(self)
        trial._answers = {}
        try:
            trial._restaged(change=lambda: trial._stages.update({SETUP_BARS_KEPT: bars}))
        except ValueError:
            return False
        return True

    def get_setup_bars(self):
        possible = self._setup_bars_possible()
        kept = self._stages.get(SETUP_BARS_KEPT)
        return kept if kept in possible else (self._style()[SECTIONS][self._intro_kind()][BARS] if possible else None)

    def _stage(self, *, kind, plays=None, own=None):
        """One stage: a section of a kind, played by some of its players for the setup's bars, with what the stage is given of its own."""
        usual = self._style()[SECTIONS][kind]
        entry = {KIND: kind}
        if plays is not None and sorted(plays) != sorted(usual.get(PLAYS, [])):
            entry[PLAYS] = [role for role in self.roles() if role in plays]
        if not usual.get(HELD) and self.get_setup_bars() != usual[BARS]:
            entry[BARS] = self.get_setup_bars()
        if own:
            entry[OWN_OF_SECTION] = dict(own)
        return entry

    def _start_stages(self, way):
        """The sections a way of starting puts before the song's first tune, or None where the subgenre cannot start that way."""
        kind = self._intro_kind()
        drums = self._drums_role()
        if kind is None:
            return None
        players = self._stage_players(kind)
        whole = {KIND: kind}
        if way == FULL_BAND:
            return [whole]
        if way == STRAIGHT_IN:
            return []
        if way == DRUMS_FIRST and drums in players and len(players) > 1:
            return [self._stage(kind=kind, plays=[drums]), whole]
        if way == DRUM_FILL_IN and drums in players and self.has_song_plan():
            return [self._stage(kind=kind, plays=[drums], own={LEAVES: LEAVES_BIG_FILL})]
        if way == ONE_PLAYER_FIRST and len(players) > 1 and players[0] != drums:
            return [self._stage(kind=kind, plays=players[:1]), whole]
        if way == LAYERS and len(players) > 2:
            return [self._stage(kind=kind, plays=players[:count]) for count in range(1, len(players) + 1)]
        return None

    def _end_stages(self, way):
        """The sections a way of ending puts after the song's last tune, or None where the subgenre cannot end that way."""
        held = self._ending_kind()
        outro = self._outro_kind()
        chord = [{KIND: held}] if held is not None else []
        if way == HELD_CHORD and held is not None:
            return chord
        if way == HARD_STOP:
            return []
        if outro is None:
            return None
        players = self._stage_players(outro)
        if way == OUTRO_THEN_CHORD and held is not None:
            return [self._stage(kind=outro), *chord]
        if way == SLOWS_DOWN:
            return [self._stage(kind=outro, own={TEMPO_END_OF_PLACE: max(self._tempo * SLOWED_TO[0] // SLOWED_TO[1], limits.MIN_TEMPO)}), *chord]
        if way == STRIPS_DOWN and len(players) > 2:
            return [*(self._stage(kind=outro, plays=players[:count]) for count in range(len(players) - 1, 0, -1)), *chord]
        if way == ONE_PLAYER_ALONE and len(players) > 1:
            return [self._stage(kind=outro, plays=players[:1]), *chord]
        if way == REPEAT_AND_FADE:
            return [self._stage(kind=outro, own={FADES: True})]
        return None

    def starts(self):
        """Return the ways the song can start, the plainest first."""
        return [way for way in STARTS if self._start_stages(way) is not None] if self.is_ready() else []

    def ends(self):
        """Return the ways the song can end."""
        return [way for way in ENDS if self._end_stages(way) is not None] if self.is_ready() else []

    def _head(self):
        """How many sections open the song before its first tune: those the way of starting kept made, while they stand as made, else the sections of the opening kind."""
        kept = self._start_stages(self._stages.get(START_KEPT)) if START_KEPT in self._stages else None
        entries = self._entries()
        if kept is not None and entries[:len(kept)] == kept:
            return len(kept)
        count = 0
        while count < len(entries) - 1 and entries[count][KIND] == self._intro_kind():
            count += 1
        return count

    def _tail(self):
        """How many sections close the song after its last tune: those the way of ending kept made, while they stand as made, else the held chord and the outro before it."""
        kept = self._end_stages(self._stages.get(END_KEPT)) if END_KEPT in self._stages else None
        entries = self._entries()
        if kept is not None and (not kept or entries[-len(kept):] == kept):
            return len(kept)
        count = 0
        closing = (self._ending_kind(), OUTRO_KIND)
        while count < len(entries) - 1 and entries[len(entries) - 1 - count][KIND] in closing:
            count += 1
        return count

    def get_start(self):
        """Return the way the song starts, or None where its opening sections are a person's own."""
        entries = self._entries()
        head = entries[:self._head()]
        kept = self._stages.get(START_KEPT)
        if kept in self.starts() and self._start_stages(kept) == head:
            return kept
        return next((way for way in self.starts() if self._start_stages(way) == head), None)

    def get_end(self):
        """Return the way the song ends, or None where its closing sections are a person's own."""
        entries = self._entries()
        tail = entries[len(entries) - self._tail():]
        kept = self._stages.get(END_KEPT)
        if kept in self.ends() and self._end_stages(kept) == tail:
            return kept
        return next((way for way in self.ends() if self._end_stages(way) == tail), None)

    def _restaged(self, *, change, start=None, end=None):
        """Change how the song starts or ends: the sections between stay, and the stages are made again. A song that cannot then be made is as it was."""
        before = (copy.deepcopy(self._sections), dict(self._stages))
        entries = [own_copy_of(entry) for entry in self._entries()]
        head, tail = self._head(), self._tail()
        start = self.get_start() if start is None else start
        end = self.get_end() if end is None else end
        body = entries[head:len(entries) - tail]
        try:
            change()
            opening = entries[:head] if start is None else self._start_stages(start)
            closing = entries[len(entries) - tail:] if end is None else self._end_stages(end)
            if opening is None or closing is None or not body:
                raise ValueError(errors.ERR_WIZARD_START_UNMADE.format(problem=start if opening is None else end))
            self._sections = [*(own_copy_of(entry) for entry in opening), *body, *(own_copy_of(entry) for entry in closing)]
            if start is not None:
                self._stages[START_KEPT] = start
            if end is not None:
                self._stages[END_KEPT] = end
            self._answers = {}
            self.made_setlist(name=PREVIEW_NAME, version=A_VERSION)
        except (ValueError, KeyError, IndexError, SongFileError) as problem:
            self._sections, self._stages = before
            self._answers = {}
            raise ValueError(errors.ERR_WIZARD_START_UNMADE.format(problem=problem)) from None

    def set_start(self, way):
        if way not in self.starts():
            raise ValueError(errors.ERR_WIZARD_START.format(value=way))
        self._restaged(change=lambda: None, start=way)

    def set_end(self, way):
        if way not in self.ends():
            raise ValueError(errors.ERR_WIZARD_END.format(value=way))
        self._restaged(change=lambda: None, end=way)

    def set_first_player(self, role):
        if role not in self.first_players():
            raise ValueError(errors.ERR_WIZARD_FIRST_PLAYER.format(value=role))
        self._restaged(change=lambda: self._stages.update({FIRST_PLAYER_KEPT: role}))

    def set_setup_bars(self, bars):
        if isinstance(bars, bool) or bars not in self.setup_bars_offered():
            raise ValueError(errors.ERR_WIZARD_SETUP_BARS.format(value=bars))
        self._restaged(change=lambda: self._stages.update({SETUP_BARS_KEPT: bars}))

    # A form made from a few answers, each question asked only where the subgenre can play the kind of section it is about.

    def form_questions(self):
        """Return the questions a form is made from, in order, each its name, the answers offered and the usual answer."""
        kinds = self.section_kinds()
        questions = [(VERSES_FIRST, COUNTS_ONE_OR_TWO, ONE)]
        if PRE_CHORUS in kinds:
            questions.append((PRE_CHORUSES, PRE_CHORUS_ANSWERS, NO))
        if BRIDGE in kinds:
            questions.append((BRIDGE, YES_OR_NO, YES))
        if SOLO in kinds:
            questions.append((SOLOS, SOLO_COUNTS, ONE))
        if DRUM_SOLO_KIND in kinds:
            questions.append((DRUM_SOLO_KIND, YES_OR_NO, NO))
        return [*questions, (LAST_CHORUSES, COUNTS_ONE_OR_TWO, TWO)] if CHORUS_KIND in kinds and VERSE_KIND in kinds else []

    def form_of_answers(self, answers):
        """Return the kinds of section, in order, of the form some answers ask for: a question left out takes its usual answer."""
        asked = {name: (offered, usual) for name, offered, usual in self.form_questions()}
        if not asked:
            raise ValueError(errors.ERR_WIZARD_NO_FORM_QUESTIONS)
        given = {}
        for name, (offered, usual) in asked.items():
            given[name] = answers.get(name, usual)
            if given[name] not in offered:
                raise ValueError(errors.ERR_WIZARD_FORM_ANSWER.format(name=name, value=given[name]))
        unknown = [name for name in answers if name not in asked]
        if unknown:
            raise ValueError(errors.ERR_WIZARD_FORM_ANSWER.format(name=unknown[0], value=answers[unknown[0]]))
        kinds = self.section_kinds()
        before = given.get(PRE_CHORUSES, NO)
        solos = SOLO_COUNTS.index(given.get(SOLOS, NONE_OF))

        def chorus(count):
            """A chorus, with a pre-chorus before it where the answers ask for one before this chorus."""
            return ([PRE_CHORUS] if before == BEFORE_EVERY or (before == BEFORE_FIRST_TWO and count <= 2) else []) + [CHORUS_KIND]
        form = [INTRO] if INTRO in kinds else []
        form += [VERSE_KIND] * COUNTS_ONE_OR_TWO.index(given[VERSES_FIRST]) + [VERSE_KIND] + chorus(1) + [VERSE_KIND] + chorus(2)
        # The middle of the song: a first solo, the bridge, the drummer alone, and the solo that leads back to the last choruses.
        form += [SOLO] if solos == 2 else []
        form += [BRIDGE] if given.get(BRIDGE) == YES else []
        form += [DRUM_SOLO_KIND] if given.get(DRUM_SOLO_KIND) == YES else []
        form += [SOLO] if solos else []
        form += chorus(3) + [CHORUS_KIND] * COUNTS_ONE_OR_TWO.index(given[LAST_CHORUSES])
        return form + ([ENDING] if ENDING in kinds else [])

    def set_form_from_answers(self, answers):
        """Make the form some answers ask for the song's own, in place of its sections, or leave the form as it was where the answers are refused."""
        self.set_own_sections(sections=[{KIND: kind} for kind in self.form_of_answers(answers)])
        self._answers = {}

    # The band: who plays, how each plays and how busy each is.

    def _forget_band(self):
        self._ways = {}
        self._levels = {}
        self._own_gauges = {}
        self._rows = {}
        self._beside = None
        self._without = []
        self._sounds = {}
        self._band_sounds = USUAL_SOUNDS
        self._guitarists = TWO_GUITARISTS
        self._pieces_off = []
        self._fills = None
        self._quiet_notes = True
        self._break = None
        self._break_cut = None
        self._gauges = {}
        self._melody_settings = {}
        self._piece_sounds = {}

    def _style(self):
        """Return the genre's style template as the subgenre chosen has it."""
        return style_in(style=style_of(self._genre), template=self._subgenre, variant=self._variant)

    def _role(self, role):
        found = next((entry for entry in self._style()[ROLES] if entry[ROLE] == role), None) if self.is_ready() else None
        if found is None:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_PLAYER.format(value=role))
        return found

    def roles(self):
        """Return the players the genre's band may have, by name, in the genre's order."""
        return [entry[ROLE] for entry in self._style()[ROLES]] if self.is_ready() else []

    def role_traits(self, role):
        """Return what is chosen about how a player plays: the one way of a player of notes, or each part of the drums."""
        entry = self._role(role)
        if not entry.get(DRUMS):
            return [entry[TRAIT]]
        # A break takes the place of every way the drums are played but the percussion's.
        return [trait for trait in entry[DRUMS] if self.get_break() is None or trait == KEPT_BESIDE_A_BREAK]

    def _has_sound(self, *, trait, value):
        return SOUND in values_of(style=self._style(), trait=trait)[value]

    def role_is_in(self, role):
        """Return whether a player is in the band: not left out, and, for a player of notes, playing in a way that sounds."""
        entry = self._role(role)
        return role not in self._without and (bool(entry.get(DRUMS)) or self._has_sound(trait=entry[TRAIT], value=self.get_way(entry[TRAIT])))

    def role_can_play(self, role):
        """Return whether a player can be in the band at all: the drums always, and a player of notes where a way of playing that sounds fits the subgenre."""
        entry = self._role(role)
        return bool(entry.get(DRUMS)) or self.role_is_in(role) or bool(self.ways(role=role, trait=entry[TRAIT]))

    def role_title(self, role):
        """Return what a player is called on the screen: the clearer name the genre gives the player, which may follow how the
        player plays, as a lead that is a singer or a lead guitar; or the player's name where the genre gives no other."""
        entry = self._role(role)
        if self.has_one_guitarist() and role == self._one_guitarist()[CHORDS_PLAYER]:
            return self._one_guitarist()[ROLE_TITLE]
        traits = self.role_traits(role)
        by_way = entry.get(ROLE_TITLES, {})
        way = self.get_way(traits[0]) if len(traits) == 1 else None
        return by_way.get(way, entry.get(ROLE_TITLE, role))

    # The drum kit's pieces, each switched on or off: a stroke on a piece that is off is left out, never
    # moved to another piece.

    def remembered(self, *, key, compute):
        """Return an answer a page works out from these choices, kept until a choice changes."""
        return self._remembered(key=key, compute=compute)

    def _remembered(self, *, key, compute):
        """Return an answer that is found by making the song, worked out once for the choices as they stand: a page asks the
        same thing at every key, and making a song each time made the keys slow. Everything a song keeps of the choices says
        whether they changed."""
        state = repr(self.to_data())
        if state != self._answers_of:
            self._answers = {}
            self._answers_of = state
        if key not in self._answers:
            self._answers[key] = compute()
        return self._answers[key]

    def pieces(self):
        """Return the pieces of the kit the drums play in the song as chosen, in the order the song has them, on or off."""
        return list(self._remembered(key=PIECES_ANSWER, compute=self._pieces))

    def _pieces(self):
        if not self.is_ready():
            return []
        song = {**self.song_picks(self._subgenre), WITHOUT_PIECES: [], PIECE_SOUNDS: {}}
        return list(arranged(style=self._style(), song=song)[DRUM_TRACKS])

    def piece_is_on(self, piece):
        return piece not in self._pieces_off

    def set_piece_on(self, *, piece, on):
        """Switch a piece of the kit on or off. The last piece stays on: a band with no drums leaves the drums out."""
        if piece not in self.pieces():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_PIECE.format(value=piece))
        if on:
            if piece in self._pieces_off:
                self._pieces_off.remove(piece)
            return
        if [name for name in self.pieces() if self.piece_is_on(name)] == [piece]:
            raise ValueError(errors.ERR_WIZARD_LAST_PIECE)
        if piece not in self._pieces_off:
            self._pieces_off.append(piece)

    # How often the drummer plays a fill, and the snare's quiet notes.

    def _drummer(self):
        """Return what the genre says of its drummer at the level the drums are busy."""
        drums = next((role for role in self.roles() if not self.has_sound(role)), None)
        return player_of(style=self._style(), instrument=DRUMS, character=self._character(DRUMS)) if drums else {}

    def get_fills(self):
        """Return how often a fill comes, from FEWEST_FILLS, never, to MOST_FILLS: the position chosen, or the one nearest to
        what the drummer does at the level the drums are busy."""
        if self._fills is not None:
            return self._fills
        every = self._drummer().get(FILL_EVERY, self._style().get(PHRASE_BARS, DEFAULT_PHRASE_BARS))
        if every == 0:
            return FEWEST_FILLS
        return next((position for position, bars in FILLS_EVERY.items() if isinstance(bars, int) and 0 < every <= bars), EACH_SECTION_FILLS)

    def set_fills(self, position):
        if isinstance(position, bool) or not isinstance(position, int) or not FEWEST_FILLS <= position <= MOST_FILLS:
            raise ValueError(errors.ERR_WIZARD_FILLS.format(value=position))
        self._fills = position

    def _set_kept_fills(self, *, position):
        self.set_fills(position)

    # What a piece of the kit sounds as: its own drum, another drum of the kit, or a General MIDI sound on one note.

    def kit_drums(self):
        """Return the drums of the kit a piece may sound as."""
        return list(KIT)

    def piece_sound(self, piece):
        """Return what a piece of the kit sounds as: None for its own drum, the name of another drum of the kit, or a General MIDI sound's number."""
        sounds_as = self._piece_sounds.get(piece, {})
        return sounds_as.get(PLAYED_DRUM, sounds_as.get(PLAYED_SOUND))

    def piece_note(self, piece):
        """Return the MIDI note a piece plays in its General MIDI sound, or None for a piece that sounds as a drum."""
        return self._piece_sounds.get(piece, {}).get(PLAYED_NOTE)

    def set_piece_sound(self, *, piece, sound):
        """Have a piece of the kit sound as another drum of the kit, by name, or as a General MIDI sound, by number, on the note the
        piece had or the usual one; or None, as its own drum again."""
        if piece not in self.pieces():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_PIECE.format(value=piece))
        if sound is None or sound == piece:
            self._piece_sounds.pop(piece, None)
        elif isinstance(sound, str) and sound in KIT:
            self._piece_sounds[piece] = {PLAYED_DRUM: sound}
        elif not isinstance(sound, (bool, str)) and isinstance(sound, int) and limits.MIN_GM_SOUND <= sound <= limits.MAX_GM_SOUND:
            self._piece_sounds[piece] = {PLAYED_SOUND: sound, PLAYED_NOTE: self.piece_note(piece) or USUAL_PIECE_NOTE}
        else:
            raise ValueError(errors.ERR_WIZARD_PIECE_SOUND.format(value=sound))

    def set_piece_note(self, *, piece, note):
        """Choose the note a piece plays in its General MIDI sound."""
        if self.piece_note(piece) is None:
            raise ValueError(errors.ERR_WIZARD_PIECE_HAS_NO_NOTE.format(value=piece))
        if isinstance(note, bool) or not isinstance(note, int) or not LOWEST_NOTE <= note <= HIGHEST_NOTE:
            raise ValueError(errors.ERR_WIZARD_PIECE_NOTE.format(low=LOWEST_NOTE, high=HIGHEST_NOTE, value=note))
        self._piece_sounds[piece][PLAYED_NOTE] = note

    def _set_kept_piece_sound(self, *, piece, sounds_as):
        self.set_piece_sound(piece=piece, sound=sounds_as.get(PLAYED_DRUM, sounds_as.get(PLAYED_SOUND)))
        if PLAYED_NOTE in sounds_as:
            self.set_piece_note(piece=piece, note=sounds_as[PLAYED_NOTE])

    # The drum break: a bar of drums played as one thing, in place of the kick's, the snare's and the cymbal's own ways.

    def breaks(self):
        """Return the drum breaks the song may play: every break where the band has drums and the meter is the one a break
        is written in, and none otherwise."""
        if not self.is_ready() or self.meter() != COMMON_TIME or not any(not self.has_sound(role) for role in self.roles()):
            return []
        return break_names()

    def get_break(self):
        """Return the break the drums play, the one chosen or the subgenre's own, or None where they play none."""
        if not self.breaks():
            return None
        name = self._break if self._break is not None else self._picks().get(BREAK, NO_BREAK)
        return None if name == NO_BREAK else name

    def set_break(self, name):
        """Choose the break the drums play, or None for none."""
        if name is not None and name not in self.breaks():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_BREAK.format(value=name))
        self._break = NO_BREAK if name is None else name

    def _set_kept_break(self, *, name):
        self.set_break(None if name == NO_BREAK else name)

    def get_break_cut(self):
        """Return how far the break is cut up, from LEAST_CUT, as written, to MOST_CUT."""
        return self._break_cut if self._break_cut is not None else self._picks().get(BREAK_CUT, LEAST_CUT)

    def set_break_cut(self, position):
        if isinstance(position, bool) or not isinstance(position, int) or not LEAST_CUT <= position <= MOST_CUT:
            raise ValueError(errors.ERR_WIZARD_BREAK_CUT.format(low=LEAST_CUT, high=MOST_CUT, value=position))
        self._break_cut = position

    def _set_kept_break_cut(self, *, position):
        self.set_break_cut(position)

    def _break_picks(self):
        """Return the song's picks of a break and its cut, where either was chosen."""
        return {**({BREAK: self._break} if self._break is not None else {}), **({BREAK_CUT: self._break_cut} if self._break_cut is not None else {})}

    # The smart melody style's gauges, shown while the song's tunes are sketched by it.

    def gauges(self):
        """Return the names of the smart melody style's gauges while the song's tunes are sketched by it or by the hooks style, and none otherwise."""
        return list(DEFAULT_GAUGES) if self._melody in GAUGED_STYLES else []

    def get_gauge(self, name):
        """Return where a gauge stands, from LOWEST_GAUGE to HIGHEST_GAUGE: where it was moved to, else where the genre sets it."""
        if name in self._gauges:
            return self._gauges[name]
        habits = self._style()[MELODY]
        habits = habits if GRID in habits else habits[self.meter()]
        return habits.get(SMART, {}).get(name, DEFAULT_GAUGES[name])

    def set_gauge(self, *, name, position):
        if name not in DEFAULT_GAUGES or isinstance(position, bool) or not isinstance(position, int) or not LOWEST_GAUGE <= position <= HIGHEST_GAUGE:
            raise ValueError(errors.ERR_WIZARD_GAUGE.format(name=name, low=LOWEST_GAUGE, high=HIGHEST_GAUGE, value=position))
        self._gauges[name] = position

    def _melody_habits(self):
        """Return the genre's melody habits for the song's meter."""
        habits = self._style()[MELODY]
        return habits if GRID in habits else habits[self.meter()]

    def melody_settings(self):
        """Return the names of the settings the song's melody style has of its own, the usual style's while none is chosen."""
        return list(MELODY_SETTINGS_OF[self._melody]) if self.is_ready() else []

    def melody_setting_range(self, name):
        """Return the lowest and highest a melody setting that is a number may be."""
        return MELODY_NUMBERS[name]

    def melody_setting_is_switch(self, name):
        return name in MELODY_SWITCHES

    def get_melody_setting(self, name):
        """Return a melody setting: what it was set to, else what the genre's habits say, else what the style does unasked."""
        if name in self._melody_settings:
            return self._melody_settings[name]
        habits = self._melody_habits()
        if name in MELODY_SWITCHES:
            return bool(habits.get(name, MELODY_SWITCHES[name]))
        return {**DEFAULT_EVOLVE, **habits.get(EVOLVE, {})}[name]

    def set_melody_setting(self, *, name, value):
        """Set a setting of the song's melody style, refusing one the style does not have."""
        if name not in self.melody_settings():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_MELODY_SETTING.format(value=name))
        self._set_kept_melody_setting(name=name, value=value)

    def _set_kept_melody_setting(self, *, name, value):
        if name in MELODY_SWITCHES:
            if not isinstance(value, bool):
                raise ValueError(errors.ERR_WIZARD_MELODY_SWITCH.format(name=name, value=value))
        elif name in MELODY_NUMBERS:
            low, high = MELODY_NUMBERS[name]
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise ValueError(errors.ERR_WIZARD_MELODY_NUMBER.format(name=name, low=low, high=high, value=value))
        else:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_MELODY_SETTING.format(value=name))
        self._melody_settings[name] = value

    # The serial style's rows of numbers, a player's own.

    def player_rows(self, role):
        """Return the rows of numbers a player's notes are dealt, by name, while the song's tunes are written in the serial style
        and the player plays lines of the tune in some section of the form; none otherwise."""
        if not self.is_ready() or (self._melody or self.genre_melody()) != SERIAL or not self.has_sound(role) or not self._plays_lines(role):
            return []
        # A player who plays in no section of the song's form is dealt nothing, so has no row to change.
        if not any(role in self.section_plays(place) for place in range(len(self._entries()))):
            return []
        return list(PLAYER_ROWS)

    def genre_row(self, *, role, name):
        """Return a player's row as the genre gives it, or the row that plays as none would."""
        habits = {**self._melody_habits(), **self._role(role).get(HABITS, {})}
        return list(habits.get(name) or ROWS_UNASKED[name])

    def get_player_row(self, *, role, name):
        """Return a player's row as the song will deal it: the player's own, or the genre's for the player."""
        if name not in self.player_rows(role):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_ROW.format(value=name))
        return list(self._rows.get(role, {}).get(name) or self.genre_row(role=role, name=name))

    def player_row_is_own(self, *, role, name):
        """Return whether a player's row was changed from the genre's."""
        return name in self._rows.get(role, {})

    def row_limits(self, name):
        """Return the lowest and the highest number a cell of a row can hold."""
        return ROW_LIMITS[name]

    def set_player_row(self, *, role, name, values):
        """Give a player a row of the player's own; the genre's own row given back is no row of the player's."""
        if name not in self.player_rows(role):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_ROW.format(value=name))
        low, high = ROW_LIMITS[name]
        if not isinstance(values, (list, tuple)) or not FEWEST_ROW_CELLS <= len(values) <= MOST_ROW_CELLS or any(
                isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high for value in values):
            raise ValueError(errors.ERR_WIZARD_ROW.format(name=name, low=low, high=high, fewest=FEWEST_ROW_CELLS, most=MOST_ROW_CELLS, value=values))
        if list(values) == self.genre_row(role=role, name=name):
            self.clear_player_row(role=role, name=name)
        else:
            self._rows.setdefault(role, {})[name] = list(values)

    def clear_player_row(self, *, role, name):
        """Give a player's row back to the genre."""
        self._rows.get(role, {}).pop(name, None)
        if not self._rows.get(role):
            self._rows.pop(role, None)

    def _set_kept_player_row(self, *, role, name, values):
        self.set_player_row(role=role, name=name, values=values)

    def _song_role_habits(self):
        """The rows the song's players have of their own, for the players the rows are dealt to."""
        return {role: {name: list(row) for name, row in rows.items() if name in self.player_rows(role)} for role, rows in self._rows.items() if self.role_is_in(role) and self.player_rows(role)}

    def _song_melody(self):
        """Return what the song says of its melody over the genre's habits: the smart style's gauges where one was moved, and
        the settings set of the style in use; a setting of another style is kept and says nothing."""
        said = {}
        if self._melody in GAUGED_STYLES and self._gauges:
            said[SMART] = {**{name: self.get_gauge(name) for name in DEFAULT_GAUGES}, **self._gauges}
        own = {name: value for name, value in self._melody_settings.items() if name in MELODY_SETTINGS_OF[self._melody]}
        evolve = {name: value for name, value in own.items() if name in EVOLVE_SETTINGS}
        if evolve:
            said[EVOLVE] = {**DEFAULT_EVOLVE, **self._melody_habits().get(EVOLVE, {}), **evolve}
        said.update({name: value for name, value in own.items() if name not in EVOLVE_SETTINGS})
        return said

    def _set_kept_quiet_notes(self, *, on):
        self.set_quiet_notes(on)

    def has_quiet_notes(self):
        """Return whether the snare of the song as chosen has quiet notes, soft strokes between the main ones, to switch off."""
        return self._remembered(key=QUIET_NOTES_ANSWER, compute=self._has_quiet_notes)

    def _has_quiet_notes(self):
        if not self.is_ready():
            return False
        song = {name: value for name, value in self.song_picks(self._subgenre).items() if name != QUIET_NOTES}
        style = self._style()
        # Found by arranging the song both ways, since a drummer's unevenness has made numbers of the strokes by then.
        return arranged(style=style, song=song)[PARTS] != arranged(style=style, song={**song, QUIET_NOTES: False})[PARTS]

    def plays_quiet_notes(self):
        return self._quiet_notes

    def set_quiet_notes(self, on):
        if not isinstance(on, bool):
            raise ValueError(errors.ERR_WIZARD_QUIET_NOTES.format(value=on))
        self._quiet_notes = on

    # One guitarist or two: a band whose one guitarist plays the chords and takes the solo, the chords
    # stopping where the solo plays, shown as one player.

    def _one_guitarist(self):
        return self._style().get(ONE_GUITARIST) if self.is_ready() else None

    def offers_one_guitarist(self):
        """Return whether the band can have one guitarist: the genre says which two players the one would be, and the solo can be a guitar's."""
        one = self._one_guitarist()
        return bool(one) and self.role_can_play(one[CHORDS_PLAYER]) and one[SOLO_WAY] in self.ways(role=one[SOLO_PLAYER], trait=self._role(one[SOLO_PLAYER])[TRAIT])

    def get_guitarists(self):
        return self._guitarists

    def has_one_guitarist(self):
        return self._guitarists == ONE_GUITARIST_COUNT

    def set_guitarists(self, count):
        """Choose two guitarists or one. One guitarist takes the solo on the guitar, whatever took it before."""
        if isinstance(count, bool) or count not in GUITARIST_COUNTS or (count == ONE_GUITARIST_COUNT and not self.offers_one_guitarist()):
            raise ValueError(errors.ERR_WIZARD_GUITARISTS.format(value=count))
        self._guitarists = count
        if count == ONE_GUITARIST_COUNT:
            one = self._one_guitarist()
            if one[SOLO_PLAYER] in self._without:
                self._without.remove(one[SOLO_PLAYER])
            self._ways[self._role(one[SOLO_PLAYER])[TRAIT]] = one[SOLO_WAY]

    def _set_kept_guitarists(self, *, count):
        self.set_guitarists(count)

    def roles_shown(self):
        """Return the players the screen shows: every player, but for the player of the solo where one guitarist plays both."""
        hidden = self._one_guitarist()[SOLO_PLAYER] if self.has_one_guitarist() else None
        return [role for role in self.roles() if role != hidden]

    def _song_without(self):
        """Return the players the song leaves out: those left out, and with them the solo of one guitarist who is left out."""
        without = list(self._without)
        if self.has_one_guitarist():
            one = self._one_guitarist()
            if one[CHORDS_PLAYER] in without and one[SOLO_PLAYER] not in without:
                without.append(one[SOLO_PLAYER])
        return without

    def _plays_of_one_guitarist(self, plays):
        """Return who plays in a section where one guitarist plays both parts: the chords stop where the solo plays."""
        one = self._one_guitarist()
        if self.has_one_guitarist() and one[SOLO_PLAYER] in plays and one[CHORDS_PLAYER] in plays:
            return [role for role in plays if role != one[CHORDS_PLAYER]]
        return None

    def _sections_of_song(self):
        """Return the sections the song describes itself, by name: its own form's, each with its kind and what it changes; and,
        for one guitarist, each section the solo plays in with the chords left out."""
        if self.has_own_form():
            sections = self._song_sections()
            for place, name in enumerate(self.form_sections()):
                plays = self._plays_of_one_guitarist(self.section_plays(place))
                if plays is not None:
                    sections[name][PLAYS] = plays
            return sections
        sections = {}
        for kind in set(self.form_sections()):
            plays = self._plays_of_one_guitarist(list(self._style()[SECTIONS][kind].get(PLAYS, [])))
            if plays is not None:
                sections[kind] = {KIND: kind, PLAYS: plays}
        return sections

    # A player's sound: the one the player's way of playing has, moved by the band's Sounds, unless the player has a sound of its own.

    def has_sound(self, role):
        """Return whether a player's sound can be chosen: a player of notes, never the drums, whose kit the grooves are written for."""
        return not self._role(role).get(DRUMS)

    def usual_sound(self, role):
        """Return the General MIDI sound a player usually plays with: what the genre has stand in for the player in the subgenre,
        as it does for a singer, whose voice General MIDI plays poorly, or the sound of the player's way."""
        style = self._style()
        stands_in = style.get(STAND_INS, {}).get(role, {}).get(self._subgenre)
        return style[SOUNDS][stands_in] if stands_in else self._way_sound(role)

    def _way_sound(self, role):
        """Return the General MIDI sound a player's way of playing has, which the arranger gives the player unless the song says another."""
        style = self._style()
        entry = values_of(style=style, trait=self._role(role)[TRAIT])[self.get_way(self._role(role)[TRAIT])]
        return style[SOUNDS][entry[SOUND]]

    def get_band_sounds(self):
        return self._band_sounds

    def set_band_sounds(self, sounds):
        if sounds not in BAND_SOUNDS:
            raise ValueError(errors.ERR_WIZARD_BAND_SOUNDS.format(value=sounds))
        self._band_sounds = sounds

    def _set_kept_band_sounds(self, *, sounds):
        self.set_band_sounds(sounds)

    def band_sound(self, role):
        """Return the sound the band's Sounds gives a player: the usual one, or the nearest of the family chosen, a sound
        already of that family staying as it is."""
        usual = self.usual_sound(role)
        if self._band_sounds == USUAL_SOUNDS or usual in KEPT_BY[self._band_sounds]:
            return usual
        return NEAREST[self._band_sounds].get(family_of(usual), usual)

    def has_own_sound(self, role):
        return role in self._sounds

    def get_sound(self, role):
        """Return the General MIDI sound a player plays with: the player's own, or the band's."""
        return self._sounds.get(role, self.band_sound(role)) if role in self._sounds else self.band_sound(role)

    def set_sound(self, *, role, sound):
        """Give a player a sound of its own, any General MIDI sound; or None, to follow the band's again."""
        if not self.has_sound(role):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_PLAYER.format(value=role))
        if sound is None:
            self._sounds.pop(role, None)
            return
        if isinstance(sound, bool) or not isinstance(sound, int) or not limits.MIN_GM_SOUND <= sound <= limits.MAX_GM_SOUND:
            raise ValueError(errors.ERR_WIZARD_SOUND.format(low=limits.MIN_GM_SOUND, high=limits.MAX_GM_SOUND, value=sound))
        self._sounds[role] = sound

    # What a sound is tried with: a run of the song's scale from its root, in the player's octave.

    def root_half_steps(self):
        """Return the song's root as half steps above C, within an octave."""
        return SEMITONES_ABOVE_C[self._root] % NOTES_IN_OCTAVE

    def scale_half_steps(self):
        """Return the notes of the song's scale as half steps above its root, the major scale's where the melody engines know none for the scale type."""
        return HALF_STEPS.get(self._scale_type, HALF_STEPS[MAJOR])

    def role_octave(self, role):
        """Return the octave a player plays in."""
        return self._role(role).get(OCTAVE, USUAL_OCTAVE)

    def genre_sounds(self, role):
        """Return the genre's own sounds that suit a player, each a General MIDI number: the sounds of the ways the player can play."""
        style = self._style()
        found = []
        for entry in values_of(style=style, trait=self._role(role)[TRAIT]).values():
            if SOUND in entry and style[SOUNDS][entry[SOUND]] not in found:
                found.append(style[SOUNDS][entry[SOUND]])
        for stands_in in style.get(STAND_INS, {}).get(role, {}).values():
            if style[SOUNDS][stands_in] not in found:
                found.append(style[SOUNDS][stands_in])
        return found

    def sound_name(self, sound):
        """Return what a General MIDI sound is called: by the genre where the genre names it, or by General MIDI."""
        named = [name for name, number in self._style()[SOUNDS].items() if number == sound]
        return named[0] if named else labels_text.MSG_GM_SOUNDS[sound - limits.MIN_GM_SOUND]

    def _song_sounds(self):
        """Return the sounds the song chooses itself, by player: each player in the band whose sound is not its way's usual one."""
        return {role: self.get_sound(role) for role in self.roles_in() if self.has_sound(role) and self.role_can_play(role) and self.get_sound(role) != self._way_sound(role)}

    def roles_in(self):
        return [role for role in self.roles() if self.role_is_in(role)]

    def set_role_in(self, *, role, on):
        """Put a player in the band or leave the player out. A player whose usual way is to sit out comes in playing the commonest way that fits."""
        entry = self._role(role)
        if not on:
            if self.roles_in() == [role]:
                raise ValueError(errors.ERR_WIZARD_LAST_PLAYER)
            if role not in self._without:
                self._without.append(role)
            return
        if role in self._without:
            self._without.remove(role)
        if not entry.get(DRUMS) and not self._has_sound(trait=entry[TRAIT], value=self.get_way(entry[TRAIT])):
            ways = self.ways(role=role, trait=entry[TRAIT])
            if not ways:
                raise ValueError(errors.ERR_WIZARD_NO_WAY.format(value=role))
            self._ways[entry[TRAIT]] = ways[0]

    def _picks_with(self, ways):
        return picked(style=self._style(), song={TEMPLATE: self._subgenre, PICKS: ways})

    def _works(self, *, trait, value):
        """Return whether a way of playing can be chosen beside the other picks, some ways needing a meter or a feel."""
        try:
            self._picks_with({**self._ways, trait: value})
        except ValueError:
            return False
        return True

    def ways(self, *, role, trait):
        """Return the ways a player may play a trait beside the other picks, the commonest first; for a player of notes, only ways that sound."""
        style = self._style()
        drums = bool(self._role(role).get(DRUMS))
        picks = self._picks()
        entries = [entry for entry in sorted(values_of(style=style, trait=trait).values(), key=share_of, reverse=True) if (drums or SOUND in entry) and fits(entry=entry, picks=picks)]
        return [entry[VALUE] for entry in entries if self._works(trait=trait, value=entry[VALUE])]

    # What the whole song has a way of: its chords, its feel and its drum fills, each a trait of the genre no one player owns.

    def song_trait(self, traits):
        """Return the first of some traits the genre has that no player owns, as chords under either name a genre gives them, or None."""
        if not self.is_ready():
            return None
        of_players = {trait for role in self.roles() for trait in self.role_traits(role)}
        return next((trait for trait in traits if trait not in of_players and isinstance(self._style()[TRAITS].get(trait), list)), None)

    def song_ways(self, trait):
        """Return the ways a trait of the whole song may go beside the other picks, the commonest first."""
        entries = sorted(values_of(style=self._style(), trait=trait).values(), key=self._share, reverse=True)
        return [entry[VALUE] for entry in entries if self._works(trait=trait, value=entry[VALUE])]

    def _share(self, entry):
        """Return how common a value is in the subgenre chosen."""
        return share_in(style=self._style(), entry=entry, template=self._subgenre)

    # The melody style, which every tune of the song is sketched by.

    def melody_styles(self):
        """Return the melody styles the subgenre's tunes can be sketched by, leaving out any that makes no song of it."""
        if not self.is_ready():
            return []
        return [style for style in MELODY_STYLES if melody_works(genre=self._genre, subgenre=self._subgenre, variant=self._variant, style=style)
                and not melody_is_usual(genre=self._genre, subgenre=self._subgenre, variant=self._variant, style=style)]

    def genre_melody(self):
        """Return the melody style the genre's own tunes are sketched by, which a song takes while none is chosen."""
        return self._melody_habits().get(ENGINE, STEP_WALK)

    def get_melody(self):
        """Return the melody style chosen, or None while each player's tunes are sketched as the genre says."""
        return self._melody

    def set_melody(self, style):
        if style is not None and style not in self.melody_styles():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_MELODY.format(value=style))
        self._melody = style

    def _set_kept_melody(self, *, style):
        self.set_melody(style)

    # The hook, which a song has or has not, apart from the melody style that writes its other lines.

    def can_have_hook(self):
        """Return whether a hook can be made at all: a section of the song's form marks a line as its hook, and, in a form of
        the subgenre's own, a player carries a tune there."""
        if not self.is_ready() or not any(entry.get(HOOK) for place in range(len(self._entries())) for entry in self._section(place).get(PLAN, [])):
            return False
        return self.has_own_form() or hook_matters(genre=self._genre, subgenre=self._subgenre, variant=self._variant, form=self.get_form())

    def hook_line_place(self):
        """Return where the song's hook line is while the song can have one: the kind of section that says it first and which of
        that kind's lines it is, counted from 1. None where the song can have no hook."""
        if not self.can_have_hook():
            return None
        sections = self._style()[SECTIONS]
        for kind in self.section_kinds_in_form():
            for count, entry in enumerate(sections[kind].get(PLAN, [])):
                if entry.get(HOOK):
                    return kind, count + 1
        return None

    def usual_hook(self):
        """Return whether the genre's songs have a hook unless a person says otherwise."""
        return self.can_have_hook() and bool(self._style().get(HOOK, False))

    def has_hook(self):
        return self.usual_hook() if self._hook is None else self._hook

    def hook_notes(self):
        """Return the hook as the song's tune player first plays it: how many steps the hook line lasts, how many steps a bar
        has, and each note as where it starts, how many steps it lasts and its MIDI note. None while the song has no hook.
        Found by arranging the song, and kept until a choice changes."""
        return self._remembered(key=HOOK_ANSWER, compute=self._hook_notes)

    def _hook_part(self):
        """The part of the tune's player in the first kind of section that says the hook, and which of its lines is the hook; nothing where nobody says one."""
        return self._remembered(key=HOOK_PART_ANSWER, compute=self._found_hook_part)

    def _found_hook_part(self):
        player = self.tune_player()
        if not self.can_have_hook() or not self.has_hook() or player is None:
            return None, None
        sections = self._style()[SECTIONS]
        kind = next(kind for kind in self.section_kinds_in_form() if any(entry.get(HOOK) for entry in sections[kind].get(PLAN, [])))
        line = next(place for place, entry in enumerate(sections[kind][PLAN]) if entry.get(HOOK))
        part = arranged(style=self._style(), song=self.song_picks(kind))[PARTS].get(composer_text.MSG_PART_OF_SECTION.format(kind, player))
        return (None, None) if part is None or LINES not in part else (part, line)

    def _hook_notes(self):
        part, line = self._hook_part()
        if part is None:
            return None
        scale = self.scale_half_steps()
        lowest = part[OCTAVE] * NOTES_IN_OCTAVE + self.root_half_steps()
        notes = []
        at = 0
        for note in part[LINES][line]:
            length = note.get(STEPS, note.get(REST))
            if REST not in note:
                octaves, place = divmod(note[DEGREE] - 1, len(scale))
                notes.append((at, length, lowest + scale[place] + (octaves + note.get(OCTAVE, 0)) * NOTES_IN_OCTAVE + HALF_STEPS_OF_ACCIDENTAL.get(note.get(ACCIDENTAL), 0)))
            at += length
        return at, self._melody_habits()[GRID], notes

    def set_hook(self, on):
        if on and not self.can_have_hook():
            raise ValueError(errors.ERR_WIZARD_NO_HOOK)
        self._hook = None if bool(on) == self.usual_hook() else bool(on)

    def _set_kept_hook(self, *, on):
        self.set_hook(on)

    def get_hook_take(self):
        """Return which take of the hook the song has: the first, or a later one asked for with a new hook."""
        return self._hook_take

    def new_hook(self):
        """Have another hook made, every other line of the song left as it was."""
        if not self.can_have_hook() or not self.has_hook():
            raise ValueError(errors.ERR_WIZARD_NO_HOOK)
        self._hook_take += 1

    def _set_kept_hook_take(self, *, take):
        if isinstance(take, bool) or not isinstance(take, int) or take < FIRST_HOOK_TAKE:
            raise ValueError(errors.ERR_WIZARD_HOOK_TAKE.format(value=take))
        self._hook_take = take

    def get_way(self, trait):
        return self._picks()[trait]

    def set_way(self, *, trait, value):
        if not self.is_ready() or value not in values_of(style=self._style(), trait=trait) or not self._works(trait=trait, value=value):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_WAY.format(trait=trait, value=value))
        self._ways[trait] = value

    def has_busy(self, role):
        """Return whether a player's busyness can be chosen: the genre says how the player's instrument is played at each level."""
        return self._role(role).get(PLAYER) in self._style().get(PLAYERS, {})

    def get_busy(self, role):
        """Return how busy a player is, from LEAST_BUSY to MOST_BUSY, or None where the song names no level."""
        return self._levels.get(self._role(role).get(PLAYER))

    def set_busy(self, *, role, level):
        """Choose how busy a player is. Players of one instrument, as a lead and a solo, share the level."""
        if not self.has_busy(role):
            raise ValueError(errors.ERR_WIZARD_BUSY.format(low=LEAST_BUSY, high=MOST_BUSY, value=level))
        self._set_level(player=self._role(role)[PLAYER], level=level)

    def _set_level(self, *, player, level):
        if isinstance(level, bool) or not isinstance(level, int) or level not in self._style().get(PLAYERS, {}).get(player, {}):
            raise ValueError(errors.ERR_WIZARD_BUSY.format(low=LEAST_BUSY, high=MOST_BUSY, value=level))
        self._levels[player] = level
        # A preset chosen puts every gauge of the player back where the preset has it.
        self._own_gauges.pop(player, None)

    # How loud a player is: four named levels, a ghost note, a soft note, a normal note and an accent, and the player's dynamics,
    # how far the levels lie from the normal one.

    def _levels_of_style(self, role):
        """The four levels the genre gives a player: the whole kit's for the drummer, and a player of notes' from the player's velocity."""
        entry = self._role(role)
        if entry.get(DRUMS):
            return drum_levels(self._style()[LOUDNESS_OF][DRUMS])
        return note_levels(entry[VELOCITY])

    def has_loudness(self, role):
        """Return whether a player has levels to choose: a player in the band who drums or plays notes at a velocity."""
        return self.is_ready() and role in self.roles() and self.role_is_in(role) and (bool(self._role(role).get(DRUMS)) or VELOCITY in self._role(role))

    def loudness_levels(self, role):
        """Return a player's four levels by name, the genre's with the song's own in their places; the drummer's are the whole kit's,
        which every piece of the kit follows in proportion."""
        return with_own(levels=self._levels_of_style(role), own=self._extras.get(LOUDNESS_OF, {}).get(role))

    def loudness_level_is_own(self, *, role, level):
        return level in self._extras.get(LOUDNESS_OF, {}).get(role, {})

    def loudness_levels_offered(self, role):
        """Return the levels of a player that the song plays, from the quietest up: a level no note of the player's is played at is
        not offered. Found by making the song with each level moved, and kept until a choice changes."""
        if not self.has_loudness(role):
            return []
        return self._remembered(key=(LEVELS_ANSWER, role), compute=lambda: self._levels_heard(role))

    def _parts_arranged(self):
        """The patterns of the song as made, which leaves out a part no section plays."""
        return self.made_for_listening()[0].to_data()[Section.PATTERNS]

    def _levels_heard(self, role):
        plain = self._parts_as_written(role)
        heard = []
        for level in LOUDNESS_LEVELS:
            trial = copy.deepcopy(self)
            trial._answers = {}
            now = trial.loudness_levels(role)[level]
            trial._extras.setdefault(LOUDNESS_OF, {}).setdefault(role, {})[level] = now - LEVEL_TRIAL if now > MIDDLE_VELOCITY else now + LEVEL_TRIAL
            # The player's dynamics as written, so that a level is heard apart from the normal one.
            trial._extras.get(DYNAMICS, {}).pop(role, None)
            if trial._parts_arranged() != plain:
                heard.append(level)
        return heard

    def _parts_as_written(self, role):
        """The song's parts with a player's dynamics as the genre writes them."""
        trial = copy.deepcopy(self)
        trial._answers = {}
        trial._extras.get(DYNAMICS, {}).pop(role, None)
        return trial._parts_arranged()

    def set_loudness_level(self, *, role, level, number):
        """Give a player a level of the song's own, a velocity, or give the level back to the genre with None."""
        is_number = number is None or (isinstance(number, int) and not isinstance(number, bool) and LOWEST_VELOCITY <= number <= HIGHEST_VELOCITY)
        if not self.has_loudness(role) or level not in LOUDNESS_LEVELS or not is_number:
            raise ValueError(errors.ERR_WIZARD_LOUDNESS.format(low=LOWEST_VELOCITY, high=HIGHEST_VELOCITY, value=(role, level, number)))
        own = self._extras.setdefault(LOUDNESS_OF, {}).setdefault(role, {})
        own.pop(level, None)
        if number is not None and number != self._levels_of_style(role)[level]:
            own[level] = number
        if not own:
            del self._extras[LOUDNESS_OF][role]
        if not self._extras[LOUDNESS_OF]:
            del self._extras[LOUDNESS_OF]
        self._answers = {}

    def has_dynamics(self, role):
        """Return whether a player's dynamics are heard: whether the song differs with the player's notes all alike and at their widest,
        found by making the song both ways and kept until a choice changes."""
        if not self.has_loudness(role):
            return False
        return self._remembered(key=(DYNAMICS_ANSWER, role), compute=lambda: self._dynamics_are_heard(role))

    def _dynamics_are_heard(self, role):
        made = []
        for dynamics in (LEAST_DYNAMICS, MOST_DYNAMICS):
            trial = copy.deepcopy(self)
            trial._answers = {}
            trial._extras.setdefault(DYNAMICS, {})[role] = dynamics
            made.append(trial.made_for_listening()[0].to_data()[Section.PATTERNS])
        return made[0] != made[1]

    def get_dynamics(self, role):
        return self._extras.get(DYNAMICS, {}).get(role, USUAL_DYNAMICS)

    def set_dynamics(self, *, role, dynamics):
        """Say how far a player's loud and soft notes lie from the player's normal ones: not at all at the least, as the genre writes them
        in the middle, and twice as far at the most."""
        if not self.has_loudness(role) or isinstance(dynamics, bool) or not isinstance(dynamics, int) or not LEAST_DYNAMICS <= dynamics <= MOST_DYNAMICS:
            raise ValueError(errors.ERR_WIZARD_DYNAMICS.format(low=LEAST_DYNAMICS, high=MOST_DYNAMICS, value=dynamics))
        of_players = self._extras.setdefault(DYNAMICS, {})
        of_players.pop(role, None)
        if dynamics != USUAL_DYNAMICS:
            of_players[role] = dynamics
        if not of_players:
            del self._extras[DYNAMICS]
        self._answers = {}

    # The player beside the tune: who answers the player who has the tune, and what the answering player does in each section.

    def _interplay(self):
        """Return what the genre says of playing beside the tune: a plan of what is done in each kind of section, with a plan of its own for some subgenres, and how busy."""
        return self._style().get(INTERPLAY, {}) if self.is_ready() else {}

    def _usual_answerer(self):
        """Return the player the genre has answer the tune, where the player can play in the subgenre, or None."""
        role = next((entry[ROLE] for entry in self._style()[ROLES] if entry.get(ANSWERS)), None) if self.is_ready() else None
        return role if role is not None and role in self.roles_shown() and self.role_can_play(role) else None

    def tune_player(self):
        """Return the player who has the tune: the first player of lines who answers nobody and is in the band, or None."""
        return next((role for role in self.roles_in() if self.has_sound(role) and not self._role(role).get(ANSWERS) and self._plays_lines(role)), None)

    def _plays_lines(self, role):
        entry = self._role(role)
        return FIGURE not in values_of(style=self._style(), trait=entry[TRAIT])[self.get_way(entry[TRAIT])]

    def answerers(self):
        """Return the players who may answer the tune, by name: the genre's answering player while in the band, and none where the song keeps to
        what was made before answering could be chosen."""
        usual = self._usual_answerer()
        return [] if self._beside is None or usual is None or not self.role_is_in(usual) else [usual]

    def answered_by(self):
        """Return the player who answers the tune, or None where nobody does."""
        return self._beside[BY] if self._beside is not None and self._beside[BY] in self.answerers() and self.role_is_in(self._beside[BY]) else None

    def set_answered_by(self, role):
        """Choose who answers the tune, or nobody with None."""
        if role is not None and role not in self.answerers():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_ANSWERER.format(value=role))
        if self._beside is None:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_ANSWERER.format(value=role))
        self._beside[BY] = role

    def ways_beside(self):
        """Return what a player beside the tune may do in a section, in order."""
        return list(WAYS_BESIDE)

    def get_role_plan(self):
        """Return the one thing the answering player does in every section, or None where the player goes by the genre's plan, section by section."""
        return self._beside[WAY] if self._beside is not None else None

    def set_role_plan(self, way):
        """Have the answering player do one thing in every section, or go by the genre's plan with None. Either drops what single sections were given."""
        if self.answered_by() is None or (way is not None and way not in WAYS_BESIDE):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_WAY_BESIDE.format(value=way))
        self._beside[WAY] = way
        if self._sections is not None:
            for entry in self._sections:
                entry.pop(BESIDE_KEPT, None)

    def section_has_role(self, place):
        """Return whether the answering player has something to choose in a section: somebody answers, and the tune's player plays in the section."""
        return self.answered_by() is not None and not self.section_is_held(place) and self.tune_player() in self.section_plays(place)

    def planned_role(self, place):
        """Return what the plan has the answering player do in a section: the one thing chosen for every section, or what the genre's plan
        says of the section's kind, the subgenre's own plan first, and waiting where the plan says nothing."""
        if self._beside[WAY] is not None:
            return self._beside[WAY]
        interplay = self._interplay()
        kind = self._entry(place)[KIND]
        plan = {**interplay.get(PLAN, {}), **interplay.get(BY_SUBGENRE, {}).get(self._subgenre, {})}
        return plan.get(kind, WAITS)

    def section_role_is_own(self, place):
        """Return whether a section was given a role of its own, apart from the plan."""
        return BESIDE_KEPT in self._entry(place)

    def section_role(self, place):
        """Return what the answering player does in a section: the section's own choice, or the plan's."""
        if not self.section_has_role(place):
            raise ValueError(errors.ERR_WIZARD_SECTION_HAS_NO_ROLE.format(value=place))
        return self._entry(place).get(BESIDE_KEPT, self.planned_role(place))

    def set_section_role(self, *, place, way):
        """Choose what the answering player does in one section, or give the section back to the plan with None."""
        if not self.section_has_role(place):
            raise ValueError(errors.ERR_WIZARD_SECTION_HAS_NO_ROLE.format(value=place))
        if way is not None and way not in WAYS_BESIDE:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_WAY_BESIDE.format(value=way))
        if way is None and not self.section_role_is_own(place):
            return
        entry = self._own_entries()[place]
        entry.pop(BESIDE_KEPT, None)
        if way is not None:
            entry[BESIDE_KEPT] = way

    def has_fills_busy(self):
        """Return whether how busy the answering player is can be chosen: somebody answers."""
        return self.answered_by() is not None

    def get_fills_busy(self):
        return self._beside[BUSY_BESIDE]

    def set_fills_busy(self, busy):
        if not self.has_fills_busy() or isinstance(busy, bool) or not isinstance(busy, int) or not LEAST_BUSY_BESIDE <= busy <= MOST_BUSY_BESIDE:
            raise ValueError(errors.ERR_WIZARD_FILLS_BUSY.format(low=LEAST_BUSY_BESIDE, high=MOST_BUSY_BESIDE, value=busy))
        self._beside[BUSY_BESIDE] = busy

    def _usual_beside(self):
        """Return how a new song starts: answered by the genre's answering player, going by the genre's plan, as busy as the genre says."""
        return {BY: self._usual_answerer(), WAY: None, BUSY_BESIDE: self._interplay().get(BUSY_BESIDE, USUAL_BUSY_BESIDE)}

    def _song_beside(self):
        """Return the song's player beside the tune, with what the player does in each section of the form in order, or nothing for a song that
        keeps to what was made before answering could be chosen, and for a genre nobody answers in."""
        usual = self._usual_answerer()
        if self._beside is None or usual is None or not self.role_is_in(usual):
            return {}
        answered = self.answered_by() is not None
        ways = [self.section_role(place) if answered and self.section_has_role(place) else WAITS for place in range(len(self._entries()))]
        return {BESIDE: {ROLE: usual, BESIDE_BUSY: self._beside[BUSY_BESIDE], BESIDE_WAYS: ways}}

    def _set_kept_beside(self, *, kept):
        usual = self._usual_beside()
        by = kept.get(BY)
        way = kept.get(WAY)
        busy = kept.get(BUSY_BESIDE, usual[BUSY_BESIDE])
        # Who answers is kept as chosen even where the player cannot answer now, as the solo's player hidden by one guitarist, and answers again once the player can.
        if (by is not None and by not in self.roles()) or (way is not None and way not in WAYS_BESIDE):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_ANSWERER.format(value=by))
        if isinstance(busy, bool) or not isinstance(busy, int) or not LEAST_BUSY_BESIDE <= busy <= MOST_BUSY_BESIDE:
            raise ValueError(errors.ERR_WIZARD_FILLS_BUSY.format(low=LEAST_BUSY_BESIDE, high=MOST_BUSY_BESIDE, value=busy))
        self._beside = {BY: by, WAY: way, BUSY_BESIDE: busy}

    # A player's gauges: where each stands, the preset's place until moved.

    def _character(self, player):
        """Return the character of an instrument's player: the preset's, with the gauges moved, or None where the song names no player."""
        if player not in self._levels:
            return None
        return {**preset(self._levels[player]), **self._own_gauges.get(player, {})}

    def _players(self):
        """Return each instrument's player for the song: a level, or the places of every gauge where one was moved."""
        return {player: self._character(player) if self._own_gauges.get(player) else level for player, level in self._levels.items()}

    def player_gauges(self, role):
        """Return the gauges a player has: those the genre's levels of the player's instrument say anything by."""
        if not self.has_busy(role):
            return []
        return gauges_of(self._style()[PLAYERS][self._role(role)[PLAYER]])

    def get_player_gauge(self, *, role, gauge):
        """Return where a gauge of a player stands, from the lowest place to the highest."""
        if gauge not in self.player_gauges(role):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_PLAYER_GAUGE.format(value=gauge))
        return self._character(self._role(role)[PLAYER])[gauge]

    def set_player_gauge(self, *, role, gauge, place):
        """Move a gauge of a player. Players of one instrument, as a lead and a solo, share their gauges."""
        if gauge not in self.player_gauges(role):
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_PLAYER_GAUGE.format(value=gauge))
        self._set_kept_player_gauge(player=self._role(role)[PLAYER], gauge=gauge, place=place)

    def _set_kept_player_gauge(self, *, player, gauge, place):
        if isinstance(place, bool) or not isinstance(place, int) or not LOWEST_PLACE <= place <= HIGHEST_PLACE or gauge not in PLAYER_GAUGES or player not in self._levels:
            raise ValueError(errors.ERR_WIZARD_PLAYER_GAUGE.format(low=LOWEST_PLACE, high=HIGHEST_PLACE, value=place))
        own = self._own_gauges.setdefault(player, {})
        own[gauge] = place
        if place == PRESET_PLACE[self._levels[player]]:
            # A gauge moved back to the preset's place is the preset's again.
            del own[gauge]

    def player_preset(self, role):
        """Return the level of the preset a player is, or None for a player whose gauges were moved from it."""
        player = self._role(role).get(PLAYER)
        return None if self._own_gauges.get(player) else self._levels.get(player)

    # The meter and the length, which follow from the subgenre, the tempo and the form.

    def meter(self):
        """Return the meter the subgenre is played in."""
        return str(self._picks().get(METER, COMMON_TIME))

    def form_seconds(self, *, form=None):
        """Return how long the song lasts at the tempo chosen, in seconds; or how long a suggested form would, when one is named."""
        if form is None:
            bars = sum(self.section_bars(place) for place in range(len(self._entries())))
        else:
            style = self._style()
            kinds = next((form_[SECTIONS] for form_ in self._forms() if form_[NAME] == form), [])
            bars = sum(HELD_BARS if style[SECTIONS][kind].get(HELD) else style[SECTIONS][kind][BARS] for kind in kinds)
        return float(bars * bar_length(self.meter()) * QUARTERS_IN_WHOLE * SECONDS_IN_MINUTE / self._tempo)

    def forms_by_length(self):
        """Return the forms' names from the shortest to the longest, forms of one length in the order they are suggested."""
        return sorted(self.forms(), key=lambda form: self.form_seconds(form=form))

    def step_length(self, offset):
        """Choose the next longer form, or the next shorter, stopping at the longest and the shortest: the song's length
        follows its sections, so a length is chosen by choosing a form."""
        forms = self.forms_by_length()
        place = forms.index(self.get_form()) + offset
        if 0 <= place < len(forms):
            self.set_form(forms[place])

    # The seed, which fixes every roll of the dice and is never shown.

    def get_seed(self):
        return self._seed

    def set_seed(self, seed):
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError(errors.ERR_WIZARD_SEED.format(value=seed))
        self._seed = seed

    def draw_seed(self, *, dice=None):
        """Draw a new seed at random, for a song from scratch or a new take."""
        self._seed = (dice or random.Random()).randint(FIRST_SEED, LAST_SEED)

    # The song.

    # The progression left to chance: a song whose progression nobody chose takes one of the subgenre's by the
    # seed, so that two runs differ in more than their tunes.

    def progression_trait(self):
        return self.song_trait(PROGRESSION_TRAITS)

    def has_any_progression(self):
        """Return whether the progression is left to chance: no progression was chosen."""
        return self.progression_trait() is not None and self.progression_trait() not in self._ways

    def set_any_progression(self):
        """Leave the progression to chance again."""
        self._ways.pop(self.progression_trait(), None)

    def progression_chords(self, progression):
        """Return a progression's chords for each kind of section the song's form plays, in the form's order, each chord its
        degree and its sharp or flat as a set file writes one; a section played as one held chord is left out. Nothing for a
        progression written another way than as degrees."""
        entry = values_of(style=self._style(), trait=self.progression_trait())[progression]
        if PATTERN not in entry:
            return []
        chords = {}
        for place, kind in enumerate(self.section_kinds_in_form()):
            if kind not in chords and not self.section_is_held(place):
                written = entry.get(BY_SECTION, {}).get(kind) or entry[PATTERN]
                chords[kind] = [(chord_of(chord)[DEGREE], ACCIDENTAL_MARKS.get(chord_of(chord).get(ACCIDENTAL))) for chord in written]
        return list(chords.items())

    def progression_scale_type(self, progression):
        """Return the scale type a progression's chords were written for, major where the genre does not say."""
        return values_of(style=self._style(), trait=self.progression_trait())[progression].get(SCALE_TYPE, MAJOR)

    def progression_degrees(self, progression):
        """Return the chords a progression is known by, its first written, each a degree and its sharp or flat; or nothing."""
        entry = values_of(style=self._style(), trait=self.progression_trait())[progression]
        return [(chord_of(chord)[DEGREE], ACCIDENTAL_MARKS.get(chord_of(chord).get(ACCIDENTAL))) for chord in entry.get(PATTERN, [])]

    def section_kinds_in_form(self):
        """Return the kind of each section of the song's form, in order."""
        return [self.section_kind(place) for place in range(len(self.section_labels()))]

    def progressions_by_chance(self):
        """Return the progressions the song may take, in the order the seed draws them: a commoner one likelier to come first, the
        subgenre's usual one counted twice. With no seed, or a progression chosen, there is nothing to draw."""
        trait = self.progression_trait()
        if not self.has_any_progression() or self._seed is None:
            return []
        usual = self._picks()[trait]
        entries = values_of(style=self._style(), trait=trait)
        left = self.song_ways(trait)
        # A progression written for the other of major and minor is left to be chosen by hand: its chords were not meant for the song's scale.
        suited = [way for way in left if entries[way].get(SCALE_TYPE, MAJOR) == self._scale_type]
        left = suited or left
        # A progression the subgenre's family never uses is left to be chosen by hand too.
        left = [way for way in left if self._share(entries[way])] or left
        dice = random.Random(PROGRESSION_SEED.format(self._seed))
        drawn = []
        while left:
            weights = [self._share(entries[way]) * (USUAL_COUNTS if way == usual else 1) or 1 for way in left]
            drawn.append(dice.choices(left, weights=weights)[0])
            left.remove(drawn[-1])
        return drawn

    def song_picks(self, name, *, progression=None):
        """Return the choices as a song's picks, which the arranger makes a song of: with a progression left to chance, the one
        given, or the first the seed draws."""
        drawn = [progression] if progression else self.progressions_by_chance()[:1]
        if drawn:
            return {**self._song_picks(name), PICKS: {**self._ways, **self._break_picks(), self.progression_trait(): drawn[0]}}
        return self._song_picks(name)

    def _song_picks(self, name):
        picks = data_laid_over(under=self._picks_chosen(name), over=self._extras_with_sections())
        # The takes are kept as numbers; the arranger is handed the tune each number draws.
        picks.pop(TUNE_TAKES, None)
        taken = self._taken_tunes()
        delivery = self.tune_phrasing()
        picks.pop(TUNE_PHRASING, None)
        if delivery is not None:
            picks[TUNE_PHRASING] = delivery
        return {**picks, TAKEN_TUNES: taken} if taken else picks

    def _extras_with_sections(self):
        """The song's extras, the plan in them holding what each section of the form was given of its own, by place."""
        if not self.has_song_plan():
            return self._extras
        plan = self._extras[PLAN_OF_SONG] if isinstance(self._extras.get(PLAN_OF_SONG), dict) else {}
        if not (any(entry.get(OWN_OF_SECTION) for entry in self._entries()) or self._intro_hook_kept() is not None):
            # A song planned because its genre plans every song asks for the plan as one that was switched on does.
            return {**self._extras, PLAN_OF_SONG: plan}
        given = list(plan.get(BY_PLACE) or [])
        by_place = []
        for place, entry in enumerate(self._entries()):
            own = dict(entry.get(OWN_OF_SECTION) or {})
            if LEAVES in own:
                own[LEAVES] = dict(LEAVES_AS_JOIN[own[LEAVES]])
            if SHAPE_OF_SECTION in own:
                # A shape the kind no longer has, as after the section was made another kind, is left as the kind's own.
                shape = self._style()[SECTIONS][entry[KIND]].get(SHAPES, {}).get(own.pop(SHAPE_OF_SECTION))
                if shape is not None:
                    own[PLAN] = copy.deepcopy(shape)
            own.update(self._intro_hook_at(place))
            if own.get(LINES_OF_SECTION):
                own[PLAN] = self._plan_with_lines(kind=entry[KIND], plan=own.get(PLAN), lines=own[LINES_OF_SECTION])
            own.pop(LINES_OF_SECTION, None)
            by_place.append({**((given[place] or {}) if place < len(given) else {}), **own})
        return {**self._extras, PLAN_OF_SONG: {**plan, BY_PLACE: by_place}}

    # The hook said in the intro, before anybody sings it, by the player who answers the tune or the tune's own player.

    def intro_hook_players(self):
        """Return the players who can say the hook in the intro: the tune's player and the player who answers the tune, where the song has a hook, a plan and an intro the band plays."""
        if not self.has_song_plan() or not self.can_have_hook() or not self.has_hook() or not self.counts_in_four() or not self._intro_places():
            return []
        return [role for role in (self.answered_by(), self.tune_player()) if role is not None]

    def _intro_places(self):
        return [place for place, entry in enumerate(self._entries()) if entry[KIND] == INTRO and not self.section_is_held(place)]

    def get_intro_hook(self):
        """Return who says the hook in the intro, or None for nobody."""
        role = self._intro_hook_kept()
        return role if role in self.intro_hook_players() else None

    def _intro_hook_kept(self):
        """Who was chosen to say the hook in the intro, while that player is still one who could: asked while the song is made, so it makes no song to answer."""
        role = self._extras.get(PLAN_OF_SONG, {}).get(INTRO_HOOK) if isinstance(self._extras.get(PLAN_OF_SONG), dict) else None
        able = role is not None and self.can_have_hook() and self.has_hook() and role in (self.answered_by(), self.tune_player())
        return role if able else None

    def set_intro_hook(self, role):
        if role is not None and role not in self.intro_hook_players():
            raise ValueError(errors.ERR_WIZARD_INTRO_HOOK.format(value=role))
        self._plan().pop(INTRO_HOOK, None)
        if role is not None:
            self._plan()[INTRO_HOOK] = role
        self._answers = {}

    def _intro_hook_at(self, place):
        """What an intro is given so that somebody says the hook in it: a line of the hook for each two bars, as answers where the answering player says them, and the player among those who play."""
        role = self._intro_hook_kept()
        if role is None or place not in self._intro_places():
            return {}
        answers = {ANSWER: True} if role == self.answered_by() else {}
        lines = [{LINE: HOOK, HOOK: True, HIGHER: True, **answers, **({VARIED: True} if count % 2 else {})} for count in range(max(self.section_bars(place) // BARS_IN_A_LINE, 1))]
        return {PLAN: lines, PLAYS: list(dict.fromkeys([*self.section_plays(place), role]))}

    # What a section of a planned song is given of its own, over the plan and the song: each is None until given, and None gives it back.

    def section_own_fields(self, place):
        """Return the fields a section can be given of its own, in the order shown: none without a plan, and no join for the last section or a held one."""
        if not self.is_ready() or self.section_is_held(place):
            return []
        if not self.has_song_plan():
            return list(OWN_WITHOUT_PLAN)
        joins = self._remembered(key=JOINS_ANSWER, compute=lambda: self._song_plan().joins())
        leaves = [LEAVES, SETUP] if place < len(joins) and joins[place] is not None else []
        shape = [SHAPE_OF_SECTION] if self.section_shapes(place) else []
        rises = [RISES] if place < len(joins) and joins[place] is not None else []
        return [ENERGY, *shape, *rises, FADES, *leaves, CHORDS, TEMPO_OF_PLACE, TEMPO_END_OF_PLACE, ROOT_OF_PLACE, TYPE_OF_PLACE]

    def section_shapes(self, place):
        """Return the shapes a section's lines may take besides its kind's own, by name."""
        return list(self._usual(place).get(SHAPES, {}))

    def section_own(self, *, place, field):
        """Return what a section was given of its own for a field, or None."""
        return copy.deepcopy(self._entry(place).get(OWN_OF_SECTION, {}).get(field))

    def section_from_plan(self, *, place, field):
        """Return what a section takes for a field where it is given nothing: the plan's Energy and join, the progression's chords, the song's tempo and key."""
        if field == CHORDS:
            return chords_as_text(self._chords_at(place))
        if field in (TEMPO_OF_PLACE, TEMPO_END_OF_PLACE):
            return self.section_own(place=place, field=TEMPO_OF_PLACE) or self._tempo
        if field in (ROOT_OF_PLACE, TYPE_OF_PLACE):
            return self._root if field == ROOT_OF_PLACE else self._scale_type
        if field == FADES:
            return False
        self._plan()
        if field == ENERGY:
            return self.energies()[place]
        if field == LEAVES:
            join = self._remembered(key=JOINS_ANSWER, compute=lambda: self._song_plan().joins())[place] or {}
            if join.get(TAIL):
                return join[TAIL]
            # A fill is said by its size, as it is chosen.
            fills = self._style()[PLAN_OF_SONG].get(FILL_SIZES, {})
            return next((way for way, given in LEAVES_AS_JOIN.items() if FILL_SIZE in given and fills.get(given[FILL_SIZE]) == join.get(FILL_OF_JOIN)), LEAVES_NOTHING)
        if field == SETUP:
            return SETUP_USUAL
        if field == SHAPE_OF_SECTION:
            # A solo after the song's first is a stage, which takes the next of its kind's shapes.
            return self._remembered(key=STAGES_ANSWER, compute=lambda: self._song_plan().shapes())[place] or SHAPE_USUAL
        if field == RISES:
            return self._entry(place)[KIND] in self._style()[PLAN_OF_SONG].get(RISING, [])
        if field == CHORDS:
            return chords_as_text(self._song_plan().chords_at(place))
        if field in (TEMPO_OF_PLACE, TEMPO_END_OF_PLACE):
            return self.section_own(place=place, field=TEMPO_OF_PLACE) or self._tempo
        return self._root if field == ROOT_OF_PLACE else self._scale_type

    def _chords_at(self, place):
        """The chords a section plays where it is given none: its kind's own, the progression's for the kind, or the progression's."""
        style = self._style()
        picks = picked(style=style, song=self.song_picks(PREVIEW_NAME))
        entry = values_of(style=style, trait=self.progression_trait())[picks[self.progression_trait()]]
        kind = self._entry(place)[KIND]
        return [chord_of(chord) for chord in style[SECTIONS][kind].get(CHORDS) or entry.get(BY_SECTION, {}).get(kind) or entry[PATTERN]]

    def _checked_own(self, *, field, value):
        if field == ENERGY and not isinstance(value, bool) and isinstance(value, int) and LOWEST_ENERGY <= value <= HIGHEST_ENERGY:
            return value
        if field == LEAVES and value in LEAVES_AS_JOIN:
            return value
        if field == SETUP and value == NOT_AT_ALL:
            return value
        if field in (RISES, FADES) and isinstance(value, bool):
            return value
        if field == LINES_OF_SECTION and isinstance(value, dict):
            return {int(count): self._checked_line_own(given) for count, given in value.items() if given}
        if field == SHAPE_OF_SECTION and isinstance(value, str):
            return value
        if field == CHORDS:
            return chords_from_text(chords_as_text(value) if isinstance(value, list) else value)
        if field in (TEMPO_OF_PLACE, TEMPO_END_OF_PLACE) and not isinstance(value, bool) and isinstance(value, int) and limits.MIN_TEMPO <= value <= limits.MAX_TEMPO:
            return value
        if field == ROOT_OF_PLACE and value in ROOT_NAMES:
            return value
        if field == TYPE_OF_PLACE and value in SCALE_TYPES:
            return value
        raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=field, value=value))

    def _checked_line_own(self, given):
        """What one line of a section was given of its own, checked: notes written by hand, a breath in eighths and whether a note comes early."""
        if not isinstance(given, dict) or not set(given) <= {LINE_NOTES, LINE_BREATH, LINE_EARLY}:
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=LINES_OF_SECTION, value=given))
        checked = {}
        if LINE_NOTES in given:
            checked[LINE_NOTES] = self._checked_line(line=given[LINE_NOTES], steps=line_edits.steps_of(given[LINE_NOTES]) if isinstance(given[LINE_NOTES], list) and all(isinstance(note, dict) for note in given[LINE_NOTES]) else 0)
        if LINE_BREATH in given:
            if isinstance(given[LINE_BREATH], bool) or not isinstance(given[LINE_BREATH], int) or not phrasing.NO_BREATH <= given[LINE_BREATH] <= phrasing.LONGEST_BREATH:
                raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=LINE_BREATH, value=given[LINE_BREATH]))
            checked[LINE_BREATH] = given[LINE_BREATH]
        if LINE_EARLY in given:
            if not isinstance(given[LINE_EARLY], bool):
                raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=LINE_EARLY, value=given[LINE_EARLY]))
            checked[LINE_EARLY] = given[LINE_EARLY]
        return checked

    # A section's lines, one by one: who plays each, its notes as the song has them, and what the line is given of its own.

    def _made_form(self):
        """The song arranged as the choices stand: its parts and its form, kept until a choice changes."""
        return self._remembered(key=ARRANGED_ANSWER, compute=lambda: arranged(style=self._style(), song=self.song_picks(PREVIEW_NAME)))

    def _plan_at(self, place):
        """The plan of lines a section is played by, with what its lines were given."""
        if self.has_song_plan():
            by_place = self._extras_with_sections().get(PLAN_OF_SONG, {}).get(BY_PLACE) or []
            given = by_place[place].get(PLAN) if place < len(by_place) and by_place[place] else None
            if given is not None:
                return given
        return self._plan_with_lines(kind=self._entry(place)[KIND], plan=None, lines=self._entry(place).get(OWN_OF_SECTION, {}).get(LINES_OF_SECTION, {}))

    def tune_steps_in_bar(self):
        """Return how many steps a bar of the tune has."""
        return self._melody_habits()[GRID]

    def section_lines(self, place):
        """Return a section's lines in order, each a mapping: who plays the line, its notes (line_edits.py) or None where nobody of the band plays the line,
        whether its breath and early note can be set (a new idea of the tune in a song in four, not the hook), and what the line was given of its own."""
        self._entry(place)
        return self._remembered(key=(LINES_ANSWER, place), compute=lambda: self._section_lines(place))

    def _section_lines(self, place):
        made = self._made_form()
        scene = made[FORM][place]
        own = self._entry(place).get(OWN_OF_SECTION, {}).get(LINES_OF_SECTION, {})
        seen = set()
        lines = []
        for count, entry in enumerate(self._plan_at(place)):
            player = self.answered_by() if entry.get(ANSWER) else self.tune_player()
            part = made[PARTS].get((scene.get(PLAY_OF_SCENE, {}).get(player) or {}).get(PART))
            notes = copy.deepcopy(part[LINES][count]) if part is not None and LINES in part and count < len(part[LINES]) else None
            letter = (bool(entry.get(ANSWER)), entry.get(LINE, str(count)))
            new = letter not in seen
            seen.add(letter)
            breathes = new and notes is not None and not entry.get(HOOK) and self.counts_in_four() and LINE_NOTES not in (own.get(count) or {})
            lines.append({LINE_PLAYER: player, LINE_NOTES: notes, LINE_BREATHES: breathes, LINE_IS_HOOK: bool(entry.get(HOOK)), LINE_OWN: copy.deepcopy(own.get(count) or {})})
        return lines

    def set_section_line(self, *, place, line, field, value):
        """Give one line of a section its own notes, breath or early note, or give the field back with None. What the song cannot then be made with is refused."""
        lines = self.section_lines(place)
        if isinstance(line, bool) or not isinstance(line, int) or not 0 <= line < len(lines) or field not in (LINE_NOTES, LINE_BREATH, LINE_EARLY):
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=field, value=line))
        if field == LINE_NOTES and value is not None and (lines[line][LINE_NOTES] is None or not isinstance(value, list) or line_edits.steps_of(self._checked_line(line=value, steps=line_edits.steps_of(lines[line][LINE_NOTES]))) == 0):
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=field, value=value))
        own = {count: dict(given) for count, given in (self._entry(place).get(OWN_OF_SECTION, {}).get(LINES_OF_SECTION) or {}).items()}
        given = own.setdefault(line, {})
        given.pop(field, None)
        if value is not None:
            given[field] = value
        own = {count: given for count, given in own.items() if given}
        self._set_own(place=place, field=LINES_OF_SECTION, value=own or None)

    def set_section_own(self, *, place, field, value):
        """Give a section something of its own, or give the field back with None. What the song cannot then be made with is refused, and nothing changes."""
        if field not in OWN_WITHOUT_PLAN:
            self._plan()
        self._set_own(place=place, field=field, value=value)

    def _set_own(self, *, place, field, value):
        self._entry(place)
        checked = None if value is None else self._checked_own(field=field, value=value)
        if field == SHAPE_OF_SECTION and checked is not None and checked not in self.section_shapes(place):
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN.format(field=field, value=value))
        before = copy.deepcopy(self._sections)
        entry = self._own_entries()[place]
        own = entry.setdefault(OWN_OF_SECTION, {})
        own.pop(field, None)
        if checked is not None:
            own[field] = checked
        if not own:
            del entry[OWN_OF_SECTION]
        self._answers = {}
        try:
            self.made_setlist(name=PREVIEW_NAME, version=A_VERSION)
        except (ValueError, KeyError, IndexError, SongFileError) as problem:
            self._sections = before
            self._answers = {}
            raise ValueError(errors.ERR_WIZARD_SECTION_OWN_UNMADE.format(field=field, value=value, problem=problem)) from None

    def _picks_chosen(self, name):
        return {NAME: name, TITLE: name, STYLE: self._genre, TEMPLATE: self._subgenre, VARIANT: self._variant, KEY: {ROOT: self._root, TYPE: self._scale_type}, TEMPO: self._tempo, FORM: self.form_sections() if self.has_own_form() else self.get_form(), SEED: self._seed,
                PICKS: {**self._ways, **self._break_picks()}, PLAYERS: self._players(), WITHOUT: self._song_without(), **self._song_beside(),
                **({SECTIONS: self._sections_of_song()} if self._sections_of_song() else {}),
                **({MELODY_ENGINE: self._melody} if self._melody is not None else {}),
                **({HOOK: self._hook} if self._hook is not None else {}),
                **({HOOK_TAKE: self._hook_take} if self._hook_take else {}),
                **({MELODY: self._song_melody()} if self._song_melody() else {}),
                **({ROLE_HABITS: self._song_role_habits()} if self._song_role_habits() else {}),
                **({ROLE_SOUNDS: self._song_sounds()} if self._song_sounds() else {}),
                **({WITHOUT_PIECES: list(self._pieces_off)} if self._pieces_off else {}),
                **({PIECE_SOUNDS: {piece: dict(sounds_as) for piece, sounds_as in self._piece_sounds.items()}} if self._piece_sounds else {}),
                **({FILLS_COME: FILLS_EVERY[self._fills]} if self._fills is not None else {}),
                **({} if self._quiet_notes else {QUIET_NOTES: False})}

    def set_song_extras(self, extras):
        """Lay a song file's own picks over what the choices make: the song's plan, and whatever a section is given."""
        if not isinstance(extras, dict):
            raise ValueError(errors.ERR_WIZARD_EXTRAS.format(value=extras))
        self._extras = copy.deepcopy(extras)
        self._answers = {}

    # The song plan, which a song made on the wizard's page asks for with a switch, and its settings.

    def has_song_plan(self):
        """Return whether the song is planned section by section (song_plan.py): a genre that says how its songs are planned plans every
        song until the plan is switched off."""
        kept = self._extras.get(PLAN_OF_SONG)
        return self.can_have_song_plan() if kept is None else kept is not False

    def can_have_song_plan(self):
        """Return whether the genre says how a song of its own is planned."""
        return self.is_ready() and PLAN_OF_SONG in self._style()

    def set_song_plan(self, on):
        if not isinstance(on, bool):
            raise ValueError(errors.ERR_WIZARD_SWITCH.format(value=on))
        if on and not self.can_have_song_plan():
            raise ValueError(errors.ERR_WIZARD_GENRE_HAS_NO_PLAN)
        if on and not isinstance(self._extras.get(PLAN_OF_SONG), dict):
            self._extras[PLAN_OF_SONG] = {}
        if not on:
            self._extras[PLAN_OF_SONG] = False
            # What the plan alone reads of the melody goes with the plan; a hook written by hand stays.
            kept = {field: value for field, value in self._extras.pop(MELODY, {}).items() if field == HOOK_NOTES}
            if kept:
                self._extras[MELODY] = kept
        self._answers = {}

    def _plan(self):
        if not self.has_song_plan():
            raise ValueError(errors.ERR_WIZARD_NO_SONG_PLAN)
        if not isinstance(self._extras.get(PLAN_OF_SONG), dict):
            self._extras[PLAN_OF_SONG] = {}
        return self._extras[PLAN_OF_SONG]

    def get_contrast(self):
        return self._plan().get(CONTRAST, USUAL_CONTRAST)

    def set_contrast(self, contrast):
        if isinstance(contrast, bool) or not isinstance(contrast, int) or not LOWEST_ENERGY <= contrast <= HIGHEST_ENERGY:
            raise ValueError(errors.ERR_WIZARD_CONTRAST.format(low=LOWEST_ENERGY, high=HIGHEST_ENERGY, value=contrast))
        self._plan()[CONTRAST] = contrast
        self._answers = {}

    # A player, as a person in the band: how strongly the player answers to Energy, where the player comes in and where the player lays out.

    def reacts(self, role):
        """Return whether a player answers to Energy more or less than the band: a player of a planned song whose playing the plan holds back or lets go,
        which is found by making the song with the player even and dramatic, and kept until a choice changes."""
        if not (self.has_song_plan() and self.role_is_in(role) and PLAYER in self._role(role)):
            return False
        return self._remembered(key=(REACTS_ANSWER, self._role(role)[PLAYER]), compute=lambda: self._reacts_is_heard(role))

    def _reacts_is_heard(self, role):
        made = []
        for reacts in (LOWEST_ENERGY, HIGHEST_ENERGY):
            trial = copy.deepcopy(self)
            trial._answers = {}
            trial._plan()[REACTS] = {**(trial._plan().get(REACTS) or {}), self._role(role)[PLAYER]: reacts}
            made.append(trial.made_for_listening()[0].to_data()[Section.PATTERNS])
        return made[0] != made[1]

    def get_reacts(self, role):
        return (self._plan().get(REACTS) or {}).get(self._role(role)[PLAYER], USUAL_CONTRAST)

    def set_reacts(self, *, role, reacts):
        """Have a player answer to Energy evenly, at the lowest, or dramatically, at the highest. Two players who are one person, as a singer who also plays, answer alike."""
        if not self.reacts(role) or isinstance(reacts, bool) or not isinstance(reacts, int) or not LOWEST_ENERGY <= reacts <= HIGHEST_ENERGY:
            raise ValueError(errors.ERR_WIZARD_REACTS.format(low=LOWEST_ENERGY, high=HIGHEST_ENERGY, value=reacts))
        kept = dict(self._plan().get(REACTS) or {})
        kept.pop(self._role(role)[PLAYER], None)
        if reacts != USUAL_CONTRAST:
            kept[self._role(role)[PLAYER]] = reacts
        self._plan().pop(REACTS, None)
        if kept:
            self._plan()[REACTS] = kept
        self._answers = {}

    def _comes_in_places(self):
        """Where each way of coming in puts a player's first section, for the ways the form has a place for, in the order they are offered."""
        kinds = self.section_kinds_in_form()
        intro = self._intro_kind()
        after_intro = next((place for place, kind in enumerate(kinds) if kind != intro), None)
        choruses = [place for place, kind in enumerate(kinds) if kind == CHORUS_KIND]
        verse = next((place for place, kind in enumerate(kinds) if kind == VERSE_KIND), None)
        found = {FROM_THE_START: 0, AFTER_THE_INTRO: after_intro, IN_FIRST_CHORUS: choruses[0] if choruses else None,
                 AFTER_FIRST_VERSE: verse + 1 if verse is not None and verse + 1 < len(kinds) else None, IN_LAST_CHORUS: choruses[-1] if len(choruses) > 1 else None}
        places = {}
        for way in COMES_IN_WAYS:
            if found[way] is not None and found[way] not in places.values():
                places[way] = found[way]
        return places

    def comes_in_offered(self, role):
        """Return the ways a player may come in, where the song has sections and the player is in the band."""
        return list(self._comes_in_places()) if self.is_ready() and self.role_is_in(role) else []

    def _first_place(self, role):
        return next((place for place in range(len(self._entries())) if role in self.section_plays(place)), None)

    def get_comes_in(self, role):
        """Return the way a player comes in, or None where the player's first section is none of the ways' or the player plays nowhere."""
        first = self._first_place(role)
        return next((way for way, place in self._comes_in_places().items() if place == first), None)

    def _usually_plays(self, *, place, role):
        return role in self._usual(place).get(PLAYS, [])

    def _quiet_places(self):
        """The places of the form a player who lays out when it is quiet sits out: those of a low Energy in a planned song."""
        return [place for place, energy in enumerate(self.energies()) if energy <= QUIET_ENERGY] if self.has_song_plan() else []

    def _breakdown_places(self):
        return [place for place, kind in enumerate(self.section_kinds_in_form()) if kind in BREAKDOWN_KINDS]

    def _laid_out(self, *, role, way, first):
        """Which sections a player plays under a way of laying out, from the player's first section on: never is every section the genre gives the player any part in."""
        out = {NEVER_LAYS_OUT: [], IN_BREAKDOWNS: self._breakdown_places(), WHEN_QUIET: self._quiet_places()}[way]
        return [place for place in range(first, len(self._entries())) if place == first or (place not in out and (not self.section_is_held(place) or self._usually_plays(place=place, role=role)))]

    def lays_out_offered(self, role):
        """Return the ways a player may lay out: never, only in the breakdowns where the form has one, and whenever it is quiet in a planned song with a quiet section."""
        if not self.comes_in_offered(role) or self._first_place(role) is None:
            return []
        return [NEVER_LAYS_OUT, *([IN_BREAKDOWNS] if self._breakdown_places() else []), *([WHEN_QUIET] if self._quiet_places() else [])]

    def get_lays_out(self, role):
        """Return the way a player lays out, or None where the sections the player plays are none of the ways'."""
        first = self._first_place(role)
        plays = [place for place in range(len(self._entries())) if role in self.section_plays(place)]
        return next((way for way in self.lays_out_offered(role) if self._laid_out(role=role, way=way, first=first) == plays), None)

    def set_comes_in(self, *, role, way):
        """Have a player come in at a place of the form and sit out every section before it; the sections after are left as they are."""
        if way not in self.comes_in_offered(role):
            raise ValueError(errors.ERR_WIZARD_COMES_IN.format(value=way))
        first = self._comes_in_places()[way]
        plays = [place for place in range(first, len(self._entries())) if place == first or role in self.section_plays(place)]
        self._set_plays_of(role=role, plays=plays)

    def set_lays_out(self, *, role, way):
        """Have a player lay out never, only in the breakdowns, or whenever it is quiet, from the player's first section on."""
        if way not in self.lays_out_offered(role):
            raise ValueError(errors.ERR_WIZARD_LAYS_OUT.format(value=way))
        self._set_plays_of(role=role, plays=self._laid_out(role=role, way=way, first=self._first_place(role)))

    def _set_plays_of(self, *, role, plays):
        """Have a player play in the sections at these places and no others; a section that would be left with nobody, or a song that cannot then be made, is refused."""
        kept = copy.deepcopy((self._sections, self._stages))
        try:
            for place in range(len(self._entries())):
                if (place in plays) != (role in self.section_plays(place)):
                    self.set_section_plays(place=place, role=role, on=place in plays)
            self._answers = {}
            self.made_for_listening()
        except (ValueError, SongFileError) as problem:
            self._sections, self._stages = kept
            self._answers = {}
            raise ValueError(errors.ERR_WIZARD_PLAYS_UNMADE.format(problem=problem)) from None

    # How the tune is delivered: one Phrasing generator on the tune's clips, with its own settings where they were changed.

    def tune_phrasing(self):
        """Return the settings of the Phrasing the tune's clips run, each given only where it is not what a Phrasing starts with, or
        None where the tune is played as written, with no Phrasing."""
        kept = self._extras.get(TUNE_PHRASING, {})
        return None if kept is False else dict(kept)

    def set_tune_phrasing(self, settings):
        """Say how the tune is delivered: a Phrasing's settings by name, None for a Phrasing as one starts, or False for no
        Phrasing. Settings no Phrasing has, or values a setting cannot take, are refused."""
        if settings is False:
            self._extras[TUNE_PHRASING] = False
        else:
            try:
                given = {name: value for name, value in dict(settings or {}).items() if value != PHRASING_DEFAULTS.get(name, value) or name not in PHRASING_DEFAULTS}
                kept = PhrasingSettings.from_data(data=given, where=composer_text.MSG_TUNE_PHRASING_NAME).to_data()
            except (SongFileError, TypeError, ValueError) as problem:
                raise ValueError(errors.ERR_WIZARD_TUNE_PHRASING.format(value=settings, problem=problem)) from None
            self._extras.pop(TUNE_PHRASING, None)
            if kept:
                self._extras[TUNE_PHRASING] = kept
        self._answers = {}

    def has_phrasing(self):
        """Return whether the tune's lines breathe."""
        return bool(self._plan().get(PHRASING, True))

    def set_phrasing(self, on):
        if not isinstance(on, bool):
            raise ValueError(errors.ERR_WIZARD_SWITCH.format(value=on))
        self._plan()[PHRASING] = on
        self._answers = {}

    def phrasing_way(self, name):
        """Return how the lines breathe in one respect: how long the breaths are, which lines are the shorter, or how many lines in four have a note come early."""
        return self._plan().get(PHRASING_WAYS, {}).get(name, phrasing.USUAL_WAYS[name])

    def set_phrasing_way(self, *, name, value):
        offered = PHRASING_OFFERED.get(name)
        if offered is None or isinstance(value, bool) or value not in offered:
            raise ValueError(errors.ERR_WIZARD_PHRASING.format(name=name, value=value))
        ways = self._plan().setdefault(PHRASING_WAYS, {})
        ways.pop(name, None)
        if value != phrasing.USUAL_WAYS[name]:
            ways[name] = value
        if not ways:
            del self._plan()[PHRASING_WAYS]
        self._answers = {}

    def hook_kind(self):
        """Return the kind of the song's hook, its contour, its rhythm and its odd detail by the fields of hook_kinds.py: the
        take's, with whatever part was chosen over it."""
        self._plan()
        return {**hook_kinds.kind_of(seed=self._seed, take=self._hook_take), **self._extras.get(MELODY, {}).get(HOOK_KIND, {})}

    def hook_parts(self):
        """Return the parts of the hook's kind that can be chosen now: the contour, and under any contour but the long note, which is one
        held note with neither, the rhythm and the odd detail."""
        if not self.counts_in_four():
            return []
        return [part for part in HOOK_PARTS if part == hook_kinds.CONTOUR or self.hook_kind()[hook_kinds.CONTOUR] != hook_kinds.LONG_NOTE]

    def counts_in_four(self):
        """Return whether the song is in four with a tune written in eighths, where a hook is of a kind and a tune's lines breathe: both
        are written for a bar of eight eighths, which a shuffle's bar of triplets is not."""
        in_four = str(picked(style=self._style(), song=self.song_picks(PREVIEW_NAME)).get(METER, COMMON_TIME)) == COMMON_TIME
        return in_four and not self._melody_habits()[GRID] % phrasing.EIGHTHS_IN_BAR

    def hook_part_is_chosen(self, part):
        return part in self._extras.get(MELODY, {}).get(HOOK_KIND, {})

    # The hook's notes, the wizard's until a person writes them by hand.

    def hook_line(self):
        """Return the hook's line as the song has it, a list of notes and rests each so many steps long (line_edits.py), or None while the song has no hook."""
        if self.hook_notes() is None:
            return None
        return self._remembered(key=HOOK_LINE_ANSWER, compute=lambda: copy.deepcopy(self._hook_part()[0][LINES][self._hook_part()[1]]))

    def hook_is_own(self):
        """Return whether the hook's notes were written by hand."""
        return bool(self._extras.get(MELODY, {}).get(HOOK_NOTES))

    def pitch_of_place(self, place):
        """Return the MIDI note at a place of the song's scale as the tune's player plays it (line_edits.place_of), for a picture of a line."""
        scale = self.scale_half_steps()
        octaves, degree = divmod(place, len(scale))
        return self._hook_part()[0][OCTAVE] * NOTES_IN_OCTAVE + self.root_half_steps() + scale[degree] + octaves * NOTES_IN_OCTAVE

    def set_hook_line(self, line):
        """Write the hook's notes by hand, or give the hook back to the wizard with None. A line that is not as long as the hook's, or that the
        song cannot be made with, is refused and nothing changes."""
        if self.hook_line() is None:
            raise ValueError(errors.ERR_WIZARD_NO_HOOK)
        before = copy.deepcopy(self._extras.get(MELODY))
        if line is None:
            self._extras.get(MELODY, {}).pop(HOOK_NOTES, None)
            if not self._extras.get(MELODY, True):
                del self._extras[MELODY]
        else:
            self._extras.setdefault(MELODY, {})[HOOK_NOTES] = self._checked_line(line=line, steps=line_edits.steps_of(self.hook_line()))
        self._answers = {}
        try:
            self.made_for_listening()
        except Exception as problem:
            self._extras.pop(MELODY, None)
            if before is not None:
                self._extras[MELODY] = before
            self._answers = {}
            raise ValueError(errors.ERR_WIZARD_HOOK_LINE.format(problem=problem)) from problem

    # The tunes: one for each kind of section the tune's player plays in. A tune is written by the choices until a person edits its
    # pattern by hand; from then on the pattern is the person's own, and no choice writes over it.

    def tune_kinds(self):
        """Return each kind of section the song has a tune in, once, in the form's order: the kinds whose sections the tune's player plays in."""
        player = self.tune_player()
        kinds = []
        for place, kind in enumerate(self.section_kinds_in_form()):
            if kind not in kinds and player is not None and player in self.section_plays(place) and not self.section_is_held(place):
                kinds.append(kind)
        return kinds

    def tune_place(self, kind):
        """Return the place in the form of the first section of a kind the tune's player plays in, or None."""
        player = self.tune_player()
        places = range(len(self.section_labels()))
        return next((place for place in places if self.section_kind(place) == kind and player in self.section_plays(place) and not self.section_is_held(place)), None)

    def tune_is_own(self, kind):
        """Return whether a kind of section's tune was written by hand, so that nothing the wizard chooses writes over it."""
        return kind in self._extras.get(OWN_TUNES, {})

    def tune_pattern_name(self, kind):
        """Return the name of the pattern that holds a kind of section's tune in the set the choices make, or None where the set has none."""
        return self._tune_in_made(kind)[0]

    def tune_pattern(self, kind):
        """Return a kind of section's tune as a pattern's data: the person's own, or the tune the choices write as they stand. None where no tune is made."""
        own = self._extras.get(OWN_TUNES, {}).get(kind)
        return copy.deepcopy(own if own is not None else self._tune_in_made(kind)[1])

    def _tune_in_made(self, kind):
        """The name and the data of the pattern the tune's player plays in the first section of a kind, in the set the choices make,
        found once for the choices as they stand, since a page asks at every key and the answer means making the song."""
        return self._remembered(key=(TUNE_MADE_ANSWER, kind), compute=lambda: self._found_tune_in_made(kind))

    def _found_tune_in_made(self, kind):
        place = self.tune_place(kind)
        if place is None:
            raise ValueError(errors.ERR_WIZARD_NO_TUNE_IN.format(value=kind))
        player = self.tune_player_in(kind)
        if player is None:
            return None, None
        setlist, name = self.made_for_listening()
        scenes = setlist.get_song(name).get_scenes()
        slot = scenes[place].get_clip_slot(player) if place < len(scenes) and scenes[place].has_clip_slot(player) else None
        if slot is None:
            return None, None
        return slot.get_pattern_name(), setlist.get_pattern(slot.get_pattern_name()).to_data()

    # Who plays the tune: one player for the song, and another, or nobody, for a kind of section. The player given the tune plays it
    # in place of the usual part there, and the player who had it rests.

    def tune_players_offered(self):
        """Return the players who may be given the tune, by name: every player of notes in the band but the bass."""
        return [role for role in self.roles_in() if self.has_sound(role) and self._role(role).get(PLAYER) != BASS_PLAYER]

    def tune_played_by(self):
        """Return the player who plays the tune in the song: the one chosen while in the band, or else the player the genre gives the tune."""
        chosen = self._extras.get(TUNE_BY_SONG)
        return chosen if chosen in self.tune_players_offered() else self.tune_player()

    def set_tune_played_by(self, role):
        """Give the song's tune to a player, or back to the player the genre gives it with None."""
        if role is not None and role not in self.tune_players_offered():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_TUNE_PLAYER.format(value=role))
        if role is None or role == self.tune_player():
            self._extras.pop(TUNE_BY_SONG, None)
        else:
            self._extras[TUNE_BY_SONG] = role
        self._answers = {}

    def tune_played_by_in(self, kind):
        """Return what a kind of section says of who plays its tune: a player's name, NOBODY, or None where the kind goes by the song."""
        chosen = self._extras.get(TUNE_BY, {}).get(kind)
        return chosen if chosen == NOBODY or chosen in self.tune_players_offered() else None

    def tune_player_in(self, kind):
        """Return the player who plays the tune in a kind of section, or None where nobody does."""
        chosen = self.tune_played_by_in(kind)
        if chosen == NOBODY:
            return None
        return chosen or self.tune_played_by()

    def set_tune_played_by_in(self, *, kind, role):
        """Give a kind of section's tune to a player, to nobody with NOBODY, or back to the song's player with None."""
        if self.tune_place(kind) is None:
            raise ValueError(errors.ERR_WIZARD_NO_TUNE_IN.format(value=kind))
        if role is not None and role != NOBODY and role not in self.tune_players_offered():
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_TUNE_PLAYER.format(value=role))
        by = self._extras.setdefault(TUNE_BY, {})
        if role is None:
            by.pop(kind, None)
        else:
            by[kind] = role
        if not by:
            del self._extras[TUNE_BY]
        self._answers = {}

    # A tune written by hand and the chords under it: when the chords change, the tune can be fitted to them.

    def own_tune_chords(self):
        """Return, for each kind of section whose tune was written by hand, the chords its first section hears, so that a change of
        chords under such a tune can be told. A kind whose chords cannot be told is left out."""
        heard = {}
        for kind in self._extras.get(OWN_TUNES, {}):
            try:
                place = self.tune_place(kind)
                if place is not None:
                    heard[kind] = copy.deepcopy(self.section_own(place=place, field=CHORDS) or (self._song_plan().chords_at(place) if self.has_song_plan() else self._chords_at(place)))
            except (ValueError, KeyError, IndexError, SongFileError):
                continue
        return heard

    def fit_tune(self, kind):
        """Fit a kind of section's tune, written by hand, to the chords its section now hears: each long note that is no note of its
        chord moves to the nearest note of the chord, and short notes stay (tune_fit.py)."""
        chords = self.own_tune_chords().get(kind)
        if chords is None:
            raise ValueError(errors.ERR_WIZARD_NO_TUNE_IN.format(value=kind))
        own = self._extras[OWN_TUNES][kind]
        self.set_tune_pattern(kind=kind, pattern=tune_fit.fitted(pattern=own, chords=chords, bar=bar_length(self.meter())))

    def tune_take(self, kind):
        """Return which take of its tune a kind of section has: the first, the tune the choices write, or a later one asked for."""
        return self._extras.get(TUNE_TAKES, {}).get(kind, FIRST_TUNE_TAKE)

    def new_tune_take(self, kind):
        """Have another tune written for a kind of section, the rest of the song left as it was. Notes written by hand for the kind
        are given up for it."""
        if self.tune_place(kind) is None:
            raise ValueError(errors.ERR_WIZARD_NO_TUNE_IN.format(value=kind))
        self._extras.setdefault(TUNE_TAKES, {})[kind] = self.tune_take(kind) + 1
        own = self._extras.get(OWN_TUNES, {})
        own.pop(kind, None)
        if not own:
            self._extras.pop(OWN_TUNES, None)
        self._answers = {}

    def _taken_tunes(self):
        """The pattern of each kind of section whose tune is a later take and not written by hand, by kind."""
        takes = self._extras.get(TUNE_TAKES, {})
        own = self._extras.get(OWN_TUNES, {})
        taken = {}
        for kind in sorted(takes):
            if kind not in own and takes[kind] != FIRST_TUNE_TAKE:
                pattern = self._remembered(key=(TUNE_TAKEN_ANSWER, kind), compute=lambda kind=kind: self._tune_taken(kind=kind, take=takes[kind]))
                if pattern is not None:
                    taken[kind] = pattern
        return taken

    def _tune_taken(self, *, kind, take):
        """The tune another take draws for a kind of section: the kind's tune in the song these choices would make from a seed of
        the take's own, with the same chords and no tune of another take or written by hand, or None where that song has none."""
        other = WizardChoices.from_data(self.to_data())
        other._extras.pop(TUNE_TAKES, None)
        other._extras.pop(OWN_TUNES, None)
        trait = self.progression_trait()
        drawn = self.progressions_by_chance()[:1]
        if trait is not None and drawn:
            other.set_way(trait=trait, value=drawn[0])
        other.set_seed(zlib.crc32(TUNE_TAKE_SEED.format(seed=self._seed, kind=kind, take=take).encode()) % (LAST_SEED + 1))
        try:
            return other._found_tune_in_made(kind)[1]
        except (ValueError, IndexError, KeyError, SongFileError):
            return None

    def set_tune_pattern(self, *, kind, pattern):
        """Keep a pattern's data as a kind of section's own tune, or forget the person's own with None, so that the choices write the
        tune again. A kind with no tune, and a pattern the song cannot be made with, are refused and nothing changes."""
        if self.tune_place(kind) is None:
            raise ValueError(errors.ERR_WIZARD_NO_TUNE_IN.format(value=kind))
        before = copy.deepcopy(self._extras.get(OWN_TUNES))
        own = self._extras.setdefault(OWN_TUNES, {})
        if pattern is None:
            own.pop(kind, None)
        else:
            own[kind] = copy.deepcopy(pattern)
        if not own:
            del self._extras[OWN_TUNES]
        self._answers = {}
        try:
            self.made_for_listening()
        except Exception as problem:
            self._extras.pop(OWN_TUNES, None)
            if before is not None:
                self._extras[OWN_TUNES] = before
            self._answers = {}
            raise ValueError(errors.ERR_WIZARD_TUNE_PATTERN.format(problem=problem)) from problem

    # The riff, the song's second hook: two bars of single notes a rhythm player repeats while the chords move them.

    def riff_players_offered(self):
        """Return who may play a riff, each a list of players: every player of a figure in the band alone, then the first two together, as a guitar and a bass play one in unison."""
        if not self.is_ready():
            return []
        able = self._remembered(key=RIFF_ABLE_ANSWER, compute=self._riff_able)
        # Together: the first player and the lowest, as a guitar and a bass play a riff in unison.
        lowest = min(able, key=lambda role: self._role(role).get(OCTAVE, 0)) if able else None
        return [[role] for role in able] + ([[able[0], lowest]] if able and lowest != able[0] else [])

    def _riff_able(self):
        """The players who can play a riff: those whose part in the song is a figure, found by asking for a riff from everybody everywhere."""
        trial = copy.deepcopy(self)
        trial._answers = {}
        trial._extras[RIFF] = {RIFF_ROLES: self.roles_in(), RIFF_KINDS: self.section_kinds()}
        try:
            parts = arranged(style=self._style(), song=trial.song_picks(PREVIEW_NAME))[PARTS]
        except (ValueError, KeyError, SongFileError):
            return []
        return [role for role in self.roles_in() if composer_text.MSG_PART_OF_SECTION.format(role, RIFF) in parts]

    def _take_riff_of_genre(self):
        """Give the song the riff its kind of music is built on, where the subgenre has one and its players can play it; a person may
        then change the riff or take it away. Any riff of another subgenre is left behind."""
        self._extras.pop(RIFF, None)
        self._answers = {}
        usual = self._style().get(RIFF)
        if not usual:
            return
        players = [role for role in usual.get(RIFF_ROLES, []) if role in self.roles_in()]
        offered = self.riff_said_offered()
        said = next((way for way in (RIFF_INTRO_AND_VERSES, RIFF_UNDER_VERSES) if way in offered), None)
        if players in self.riff_players_offered() and said is not None:
            settings = {field: usual[field] for field, ways in RIFF_SETTINGS.items() if usual.get(field) in ways[1:]}
            self._extras[RIFF] = {**settings, RIFF_ROLES: players, RIFF_KINDS: self._riff_kinds(said)}

    def _riff(self):
        kept = self._extras.get(RIFF) or {}
        return kept if kept.get(RIFF_ROLES) in self.riff_players_offered() else {}

    def has_riff(self):
        return bool(self._riff())

    def get_riff_players(self):
        """Return who plays the riff, or an empty list while the song has none."""
        return list(self._riff().get(RIFF_ROLES, []))

    def riff_said_offered(self):
        """Return where a riff may be played, for the places the form has: the intro, under the verses, both, under the choruses, and everywhere."""
        kinds = self.section_kinds_in_form()
        return [way for way in RIFF_SAID_WAYS if all(any(kind in kinds for kind in group) for group in self._riff_kind_groups(way))] if self.is_ready() else []

    def _riff_kind_groups(self, way):
        """The kinds of section a way of saying the riff names, in groups: the form has to have a kind of each group for the way to be offered."""
        opening = (self._intro_kind() or INTRO_KIND, OUTRO_KIND)
        return {RIFF_IN_INTRO: [opening], RIFF_UNDER_VERSES: [(VERSE_KIND,)], RIFF_INTRO_AND_VERSES: [opening, (VERSE_KIND,)], RIFF_UNDER_CHORUSES: [(CHORUS_KIND,)],
                RIFF_EVERYWHERE: [tuple(self.section_kinds())]}[way]

    def _riff_kinds(self, way):
        return [kind for group in self._riff_kind_groups(way) for kind in group]

    def get_riff_said(self):
        """Return where the riff is played, or None while the song has none."""
        kinds = self._riff().get(RIFF_KINDS)
        return next((way for way in self.riff_said_offered() if self._riff_kinds(way) == kinds), None)

    def set_riff(self, *, players, said=None):
        """Give the song a riff played by these players, said where asked or in the intro and under the verses, or take the riff away with no players. A riff the
        song cannot be made with is refused."""
        before = copy.deepcopy(self._extras.get(RIFF))
        if not players:
            self._extras.pop(RIFF, None)
            self._answers = {}
            return
        offered = self.riff_said_offered()
        said = said or self.get_riff_said() or next((way for way in (RIFF_INTRO_AND_VERSES, RIFF_UNDER_VERSES) if way in offered), offered[0] if offered else None)
        if list(players) not in self.riff_players_offered() or said not in offered:
            raise ValueError(errors.ERR_WIZARD_RIFF.format(value=(players, said)))
        self._extras[RIFF] = {**(before or {}), RIFF_ROLES: list(players), RIFF_KINDS: self._riff_kinds(said)}
        self._riff_or_back(before=before, value=(players, said))

    def _riff_or_back(self, *, before, value):
        self._answers = {}
        try:
            self.made_for_listening()
        except (ValueError, KeyError, SongFileError) as problem:
            self._extras.pop(RIFF, None)
            if before is not None:
                self._extras[RIFF] = before
            self._answers = {}
            raise ValueError(errors.ERR_WIZARD_RIFF_UNMADE.format(value=value, problem=problem)) from None

    # The riffs added for kinds of section, besides the song's first: each has a name and its players, who play it in its kinds of
    # section in place of their usual parts. A player plays one thing in a section, so a riff's players are neither the tune's
    # player there nor the players of another riff there.

    def _more_riffs(self):
        """The riffs added whose players are all in the band: a riff of a player who is out waits, unseen, for the player to come back."""
        band = set(self.roles_in()) if self.is_ready() else set()
        return [entry for entry in self._extras.get(MORE_RIFFS, []) if set(entry[RIFF_ROLES]) <= band]

    def _more_riff(self, riff):
        found = next((entry for entry in self._more_riffs() if entry[NAME] == riff), None)
        if found is None:
            raise ValueError(errors.ERR_WIZARD_NO_SUCH_RIFF.format(value=riff))
        return found

    def riff_kinds_offered(self):
        """Return the kinds of section a riff may be added for: each kind the song's form has, once, in the form's order, but for a
        kind whose every section is one held chord."""
        if not self.is_ready():
            return []
        return [kind for kind in dict.fromkeys(self.section_kinds_in_form()) if self.riff_place(kind) is not None]

    def added_riffs(self):
        """Return the names of the riffs added, in the order they were."""
        return [entry[NAME] for entry in self._more_riffs()]

    def riffs_in(self, kind):
        """Return the names of the riffs added that play in a kind of section, in the order they were added."""
        return [entry[NAME] for entry in self._more_riffs() if kind in entry[RIFF_KINDS]]

    def riff_players_of(self, riff):
        """Return who plays a riff that was added, the first its chords where it has any."""
        return list(self._more_riff(riff)[RIFF_ROLES])

    def riff_kinds_of(self, riff):
        """Return the kinds of section a riff that was added plays in."""
        return list(self._more_riff(riff)[RIFF_KINDS])

    def riff_take_of(self, riff):
        """Return which take of its notes a riff that was added has."""
        return self._more_riff(riff).get(RIFF_TAKE, FIRST_RIFF_TAKE)

    def riff_place(self, kind):
        """Return the place in the form of the first section of a kind that is played and not one held chord, where a riff of the kind is heard, or None."""
        places = range(len(self.section_labels()))
        return next((place for place in places if self.section_kind(place) == kind and not self.section_is_held(place)), None)

    def riff_players_free(self, kind):
        """Return the players who may take a riff in a kind of section, by name: the players whose part is a figure and who play in
        the kind's first section, but for the player of the kind's tune and the players who already have a riff there."""
        place = self.riff_place(kind) if self.is_ready() and kind in self.section_kinds_in_form() else None
        if place is None:
            return []
        busy = {self.tune_player_in(kind)} if self.tune_place(kind) is not None else set()
        first = self._riff()
        if kind in first.get(RIFF_KINDS, []):
            busy |= set(first[RIFF_ROLES])
        for entry in self._more_riffs():
            if kind in entry[RIFF_KINDS]:
                busy |= set(entry[RIFF_ROLES])
        return [role for role in self._remembered(key=(RIFF_ABLE_ANSWER, kind), compute=lambda: self._riff_able_in(kind)) if role not in busy]

    def _riff_able_in(self, kind):
        """The players a riff would be heard from in a kind of section, found by asking for one there from every player of a figure
        with no other riff in the song: a player who sits the kind out, or whose sections there a riff's bars do not fill, has none."""
        able = self._remembered(key=RIFF_ABLE_ANSWER, compute=self._riff_able)
        trial = copy.deepcopy(self)
        trial._answers = {}
        trial._extras.pop(RIFF, None)
        trial._extras[MORE_RIFFS] = [{NAME: TRIAL_RIFF, RIFF_ROLES: able, RIFF_KINDS: [kind]}]
        try:
            parts = arranged(style=self._style(), song=trial.song_picks(PREVIEW_NAME))[PARTS]
        except (ValueError, KeyError, SongFileError):
            return []
        return [role for role in able if composer_text.MSG_PART_OF_SECTION.format(role, TRIAL_RIFF) in parts]

    def add_riff(self, *, kind, players=None, riff=None):
        """Add a riff to a kind of section and return its name: a new riff for these players, or with a riff's name one already
        added, which its own players then play in this kind as well. Players who are not free there are refused, as is a riff
        the song cannot be made with."""
        free = self.riff_players_free(kind)
        before = copy.deepcopy(self._extras.get(MORE_RIFFS, []))
        if riff is not None:
            entry = self._more_riff(riff)
            if kind in entry[RIFF_KINDS] or not set(entry[RIFF_ROLES]) <= set(free):
                raise ValueError(errors.ERR_WIZARD_RIFF.format(value=(riff, kind)))
            entry[RIFF_KINDS].append(kind)
        else:
            players = list(players or [])
            if not players or len(set(players)) != len(players) or not set(players) <= set(free):
                raise ValueError(errors.ERR_WIZARD_RIFF.format(value=(players, kind)))
            riff = naming.new_name(word=names_text.MSG_NEW_RIFF_WORD, taken=[entry[NAME] for entry in self._extras.get(MORE_RIFFS, [])])
            self._extras.setdefault(MORE_RIFFS, []).append({NAME: riff, RIFF_ROLES: players, RIFF_KINDS: [kind]})
        self._more_riffs_or_back(before=before, value=(riff, kind))
        return riff

    def riffs_of_player(self, role):
        """Return the riffs that were added which a player plays, by name, in the order they were added."""
        return [entry[NAME] for entry in self._more_riffs() if role in entry[RIFF_ROLES]]

    def riff_takers(self, *, riff, leaving):
        """Return the players who could take a riff over from a player who leaves the band: each player free of the tune and of
        any other riff in every kind of section the riff plays in."""
        entry = self._more_riff(riff)
        takers = None
        for kind in entry[RIFF_KINDS]:
            free = [role for role in self.riff_players_free(kind) if role != leaving]
            takers = free if takers is None else [role for role in takers if role in free]
        return takers or []

    def give_riff(self, *, riff, leaving, taker):
        """Give a player's place in a riff to another player, who must be one of the riff's takers. A riff the song cannot then be
        made with is refused and nothing changes."""
        if taker not in self.riff_takers(riff=riff, leaving=leaving) or leaving not in self.riff_players_of(riff):
            raise ValueError(errors.ERR_WIZARD_RIFF.format(value=(riff, taker)))
        before = copy.deepcopy(self._extras.get(MORE_RIFFS, []))
        entry = self._more_riff(riff)
        entry[RIFF_ROLES] = [taker if role == leaving else role for role in entry[RIFF_ROLES]]
        self._more_riffs_or_back(before=before, value=(riff, taker))

    def drop_riff(self, riff):
        """Take a riff that was added out of the song, from every kind of section."""
        for kind in self.riff_kinds_of(riff):
            self.remove_riff(kind=kind, riff=riff)

    def remove_riff(self, *, kind, riff):
        """Take a riff out of a kind of section; a riff left with no kind of section is gone."""
        entry = self._more_riff(riff)
        if kind not in entry[RIFF_KINDS]:
            raise ValueError(errors.ERR_WIZARD_RIFF.format(value=(riff, kind)))
        entry[RIFF_KINDS].remove(kind)
        if not entry[RIFF_KINDS]:
            self._extras[MORE_RIFFS].remove(entry)
        if not self._extras[MORE_RIFFS]:
            del self._extras[MORE_RIFFS]
        self._answers = {}

    def new_riff_take_of(self, riff):
        """Have other notes written for a riff that was added, its players and its kinds of section left as they were."""
        entry = self._more_riff(riff)
        entry[RIFF_TAKE] = entry.get(RIFF_TAKE, FIRST_RIFF_TAKE) + 1
        entry.pop(RIFF_OWN, None)
        self._answers = {}

    def riff_pattern_name(self, riff):
        """Return the name of the pattern a riff that was added is played from by its first player, in the set the choices make."""
        return composer_text.MSG_PART_OF_SECTION.format(self.riff_players_of(riff)[0], riff)

    def riff_pattern(self, riff):
        """Return the data of the pattern a riff's first player plays, or None where the riff is not heard in the song."""
        name = self.riff_pattern_name(riff)
        setlist, _ = self.made_for_listening()
        return setlist.get_pattern(name).to_data() if setlist.has_pattern(name) else None

    def added_riff_is_own(self, riff):
        """Return whether a riff's notes were written by hand, so that only a new take writes over them."""
        return self._more_riff(riff).get(RIFF_OWN) is not None

    def set_riff_pattern(self, *, riff, pattern):
        """Keep a pattern's data as a riff's own notes, as its first player plays them, or forget the person's own with None. A
        pattern the song cannot be made with is refused and nothing changes."""
        entry = self._more_riff(riff)
        before = copy.deepcopy(self._extras.get(MORE_RIFFS, []))
        if pattern is None:
            entry.pop(RIFF_OWN, None)
        else:
            entry[RIFF_OWN] = copy.deepcopy(pattern)
        self._more_riffs_or_back(before=before, value=riff)

    def blank_riff_pattern(self, riff):
        """Return a riff's pattern with no note in it, as long as the riff the wizard wrote, to write by hand."""
        made = self.riff_pattern(riff)
        return {field: made[field] for field in (PatternSetting.STEPS, PatternSetting.STEP_SIZE, PatternSetting.GROUP) if field in made}

    def _more_riffs_or_back(self, *, before, value):
        self._answers = {}
        try:
            self.made_for_listening()
        except Exception as problem:
            # A pattern written by hand can fail in any way a set's data can, as a tune's can.
            self._extras.pop(MORE_RIFFS, None)
            if before:
                self._extras[MORE_RIFFS] = before
            self._answers = {}
            raise ValueError(errors.ERR_WIZARD_RIFF_UNMADE.format(value=value, problem=problem)) from None

    def riff_steps_in_bar(self):
        """Return how many steps, eighths, a bar of the riff has."""
        return int(bar_length(self.meter()) * EIGHTHS_IN_WHOLE)

    def riff_line(self):
        """Return the riff's notes, a line of two bars in eighths (line_edits.py), or None while the song has no riff."""
        if not self.has_riff():
            return None
        riff = self._riff()
        return riff_line_of(riff=copy.deepcopy(riff), seed=self._seed or 0, eighths=self.riff_steps_in_bar(), flattened=flattened_in(self._scale_type))

    def riff_kick(self):
        """Return the steps of the riff where the kick strikes with it, for a picture: the accents of a riff of chords, while the song's
        kick is played. None for any other riff."""
        if not self.has_riff() or self.get_riff_setting(RIFF_NOTES) != ACCENT_CHORDS or KICK_PIECE not in self.pieces() or not self.piece_is_on(KICK_PIECE):
            return None
        hits = [hit for bar in accent_bars(line=self.riff_line(), eighths=self.riff_steps_in_bar()) for hit in bar]
        return [step for step, hit in enumerate(hits) if hit != NO_HIT]

    # A riff's settings: how its notes are drawn, how many bars it has, what lies between its accents, what it does under the
    # tune and what it does as the chords change.

    def get_riff_setting(self, field):
        """Return a setting of the riff, the usual one until another is chosen."""
        return self._riff().get(field, RIFF_SETTINGS[field][0])

    def riff_settings_offered(self):
        """Return the riff's settings that are heard, in the order shown: how the notes are drawn; for chords on the accents, how many
        bars, what lies between and, with two bars, what the riff does under the tune; and what it does as the chords change.
        Notes written by hand are drawn no way, so only what the riff does with the chords is offered then."""
        if not self.has_riff():
            return []
        fields = [RIFF_WITH_CHORDS]
        if not self.riff_is_own():
            heavy = self.get_riff_setting(RIFF_NOTES) == ACCENT_CHORDS
            two_bars = self.get_riff_setting(RIFF_BAR_COUNT) == RIFF_BARS
            fields = [RIFF_NOTES, *([RIFF_BAR_COUNT, RIFF_BETWEEN] if heavy else []), *([RIFF_UNDER_TUNE] if heavy and two_bars else []), RIFF_WITH_CHORDS]
        return [field for field in fields if self._remembered(key=(RIFF_SETTING_ANSWER, field), compute=lambda field=field: self._riff_setting_is_heard(field))]

    def _riff_setting_is_heard(self, field):
        """Whether the song differs with a setting of the riff the other way, found by making the song both ways."""
        made = []
        for value in RIFF_SETTINGS[field]:
            trial = copy.deepcopy(self)
            trial._answers = {}
            trial._extras[RIFF] = {**self._riff(), field: value}
            try:
                # The patterns alone, since the set also keeps the choices, which differ whatever is heard.
                made.append(trial.made_for_listening()[0].to_data()[Section.PATTERNS])
            except (ValueError, KeyError, SongFileError):
                return False
        return made[0] != made[1]

    def set_riff_setting(self, *, field, value):
        """Choose a setting of the riff. What is no setting, and a riff the song cannot be made with, is refused."""
        if not self.has_riff():
            raise ValueError(errors.ERR_WIZARD_NO_RIFF)
        if field not in RIFF_SETTINGS or value not in RIFF_SETTINGS[field]:
            raise ValueError(errors.ERR_WIZARD_RIFF.format(value=(field, value)))
        before = copy.deepcopy(self._extras[RIFF])
        self._extras[RIFF].pop(field, None)
        if value != RIFF_SETTINGS[field][0]:
            self._extras[RIFF][field] = value
        self._riff_or_back(before=before, value=(field, value))

    def riff_notes(self):
        """Return the riff for a picture, as hook_notes gives the hook: how many steps it lasts, how many a bar has, and each note as where it starts, how many
        steps it lasts and its MIDI note. None while the song has no riff."""
        line = self.riff_line()
        if line is None:
            return None
        own = self._riff().get(RIFF_OWN)
        if own is not None:
            return own[PatternSetting.STEPS], self.riff_steps_in_bar(), self._notes_of_pattern(own)
        notes = []
        at = 0
        for note in line:
            if not line_edits.is_rest(note):
                notes.append((at, line_edits.length_of(note), self.riff_pitch_of_place(line_edits.place_of(note))))
            at += line_edits.length_of(note)
        return at, self.riff_steps_in_bar(), notes

    def riff_scene(self):
        """Return the place in the form of the first section that plays the riff, or None."""
        kinds = self._riff().get(RIFF_KINDS, [])
        return next((place for place, kind in enumerate(self.section_kinds_in_form()) if kind in kinds and not self.section_is_held(place)), None)

    def riff_is_own(self):
        """Return whether the riff's notes were written by hand: as a pattern, or as a line in a song made before patterns were."""
        return bool(self._riff().get(RIFF_LINE)) or self._riff().get(RIFF_OWN) is not None

    def _notes_of_pattern(self, pattern):
        """The notes of a pattern for a picture: each as the step it starts on, how many steps it lasts and its MIDI note."""
        scale = self.scale_half_steps()
        degrees = pattern.get(Row.DEGREE) or []
        octaves = pattern.get(Row.OCTAVE) or [None] * len(degrees)
        ties = pattern.get(Row.TIE) or [False] * len(degrees)
        notes = []
        for place, degree in enumerate(degrees):
            if degree is not None and octaves[place] is not None:
                held = tune_fit.steps_held(ties=ties, degrees=degrees, place=place)
                notes.append((place, held, (octaves[place] - PATTERN_OCTAVES_OVER_PICTURE) * NOTES_IN_OCTAVE + self.root_half_steps() + scale[(degree - 1) % len(scale)]))
        return notes

    def song_riff_pattern_name(self):
        """Return the name of the pattern the riff's first player plays it from, in the set the choices make, or None where the riff is not heard."""
        place = self.riff_scene()
        if place is None:
            return None
        setlist, name = self.made_for_listening()
        scene = setlist.get_song(name).get_scenes()[place]
        player = self.get_riff_players()[0]
        return scene.get_clip_slot(player).get_pattern_name() if scene.has_clip_slot(player) else None

    def set_song_riff_pattern(self, pattern):
        """Keep a pattern's data as the riff's own notes, as its first player plays them, or give the riff back to the wizard with
        None. A pattern the song cannot be made with is refused and nothing changes."""
        if not self.has_riff():
            raise ValueError(errors.ERR_WIZARD_NO_RIFF)
        before = copy.deepcopy(self._extras[RIFF])
        self._extras[RIFF].pop(RIFF_LINE, None)
        self._extras[RIFF].pop(RIFF_OWN, None)
        if pattern is not None:
            self._extras[RIFF][RIFF_OWN] = copy.deepcopy(pattern)
        self._answers = {}
        try:
            self.made_for_listening()
        except Exception as problem:
            # A pattern written by hand can fail in any way a set's data can.
            self._extras[RIFF] = before
            self._answers = {}
            raise ValueError(errors.ERR_WIZARD_RIFF_UNMADE.format(value=RIFF, problem=problem)) from None

    def riff_pitch_of_place(self, place):
        """Return the MIDI note at a place of the song's scale as the riff's first player plays it, for a picture of the riff."""
        scale = self.scale_half_steps()
        octaves, degree = divmod(place, len(scale))
        return self._role(self.get_riff_players()[0])[OCTAVE] * NOTES_IN_OCTAVE + self.root_half_steps() + scale[degree] + octaves * NOTES_IN_OCTAVE

    def new_riff(self):
        """Have another riff made, the rest of the song left as it was; notes written by hand give way to the new riff."""
        if not self.has_riff():
            raise ValueError(errors.ERR_WIZARD_NO_RIFF)
        riff = self._extras[RIFF]
        riff.pop(RIFF_LINE, None)
        riff.pop(RIFF_OWN, None)
        riff[RIFF_TAKE] = riff.get(RIFF_TAKE, FIRST_RIFF_TAKE) + 1
        self._answers = {}

    def set_riff_line(self, line):
        """Write the riff's notes by hand, or give the riff back to the wizard with None. A line that is not as long as the riff, or that the song cannot be made with, is refused."""
        if not self.has_riff():
            raise ValueError(errors.ERR_WIZARD_NO_RIFF)
        before = copy.deepcopy(self._extras[RIFF])
        if line is None:
            self._extras[RIFF].pop(RIFF_LINE, None)
        else:
            self._extras[RIFF][RIFF_LINE] = self._checked_line(line=line, steps=riff_bars_of(line=self.riff_line(), eighths=self.riff_steps_in_bar()) * self.riff_steps_in_bar())
        self._riff_or_back(before=before, value=line)

    def _checked_line(self, *, line, steps):
        """A line written by hand, checked: notes of a degree of the scale and rests, each a whole number of steps, as long as the line it stands for, with a note in it."""
        if not isinstance(line, list) or not all(isinstance(note, dict) for note in line):
            raise ValueError(errors.ERR_WIZARD_HOOK_LINE.format(problem=line))
        for note in line:
            length = note.get(REST, note.get(STEPS))
            degree = note.get(DEGREE, line_edits.FIRST_DEGREE)
            numbers = [length, degree, note.get(OCTAVE, 0)]
            if any(isinstance(number, bool) or not isinstance(number, int) for number in numbers) or length < 1 or not line_edits.FIRST_DEGREE <= degree <= line_edits.NOTES_IN_SCALE:
                raise ValueError(errors.ERR_WIZARD_HOOK_LINE.format(problem=note))
            if REST not in note and not line_edits.LOWEST_PLACE <= line_edits.place_of(note) <= line_edits.HIGHEST_PLACE:
                raise ValueError(errors.ERR_WIZARD_HOOK_LINE.format(problem=note))
        if line_edits.steps_of(line) != steps or all(REST in note for note in line):
            raise ValueError(errors.ERR_WIZARD_HOOK_LINE.format(problem=line))
        return copy.deepcopy(line)

    def set_hook_part(self, *, part, value):
        """Choose the hook's contour, rhythm or odd detail, or give the part back to the take with None."""
        self._plan()
        offered = HOOK_PARTS.get(part)
        if offered is None or (value is not None and value not in offered):
            raise ValueError(errors.ERR_WIZARD_HOOK_PART.format(part=part, value=value))
        chosen = self._extras.setdefault(MELODY, {}).setdefault(HOOK_KIND, {})
        chosen.pop(part, None)
        if value is not None:
            chosen[part] = value
        self._answers = {}

    def _song_plan(self):
        """The plan of the song as the choices stand."""
        song = self.song_picks(PREVIEW_NAME)
        style = self._style()
        picks = picked(style=style, song=song)
        chord_entry = values_of(style=style, trait=self.progression_trait())[picks[self.progression_trait()]]

        def chords_of(section):
            return [chord_of(chord) for chord in section.get(CHORDS) or chord_entry.get(BY_SECTION, {}).get(section[KIND]) or chord_entry[PATTERN]]
        return SongPlan(style=style, song=song, form_names=song[FORM] if isinstance(song[FORM], list) else form_of(style=style, song=song, meter=str(picks.get(METER, COMMON_TIME)), tempo=self._tempo),
                        tempo=self._tempo, scale_type=self._scale_type, chords_of=chords_of)

    def energies(self):
        """Return the Energy of each section of the form, in order, as the plan works them out."""
        self._plan()
        return self._remembered(key=ENERGY_ANSWER, compute=lambda: self._song_plan().energies())

    def _said_of_sections(self):
        planned = self._song_plan().planned()
        return [planned[SECTIONS][name][SAID_OF_SECTION] for name in planned[FORM]]

    def said_of_sections(self):
        """Return what the plan says of each section of the form, in order: its Energy, how it leaves and, once, the hook's kind."""
        self._plan()
        return self._remembered(key=PLAN_ANSWER, compute=self._said_of_sections)

    # What a panel listens to: the song made as the choices stand, and where in it the hook, the tune and a section are.

    def made_for_listening(self):
        """Return the set these choices make, to be heard and thrown away, with its one song's name."""
        return self.made_setlist(name=PREVIEW_NAME, version=A_VERSION), PREVIEW_NAME

    def hook_scene(self):
        """Return the place in the form of the first section that says the hook, or None."""
        sections = self._style()[SECTIONS]
        return next((place for place, kind in enumerate(self.section_kinds_in_form()) if any(entry.get(HOOK) for entry in sections[kind].get(PLAN, []))), None)

    def tune_scene(self):
        """Return the place in the form of the first section the tune's player plays in, or None."""
        player = self.tune_player()
        return next((place for place in range(len(self.section_labels())) if player in self.section_plays(place) and not self.section_is_held(place)), None)

    def get_song_extras(self):
        return copy.deepcopy(self._extras)

    def _set_kept_extras(self, *, extras):
        self.set_song_extras(extras)

    def _set_kept_stages(self, *, stages):
        """Take how a song starts and ends as a song kept it: the sections are the song's already, so only what was chosen is kept, where it is still offered."""
        kept = {field: value for field, value in stages.items() if field in (START_KEPT, END_KEPT, FIRST_PLAYER_KEPT, SETUP_BARS_KEPT)}
        self._stages = {field: value for field, value in kept.items() if isinstance(value, (str, int)) and not isinstance(value, bool)}

    def made_setlist(self, *, name, version):
        """Return a set holding the one song these choices make, under a name, with all the song uses, the song keeping the choices.

        A run that has no seed yet draws one first, so that the same choices make the same song again.
        """
        if not self.is_ready():
            raise ValueError(errors.ERR_WIZARD_NOT_READY)
        if self._seed is None:
            self.draw_seed()
        made = None
        # A progression drawn by chance that makes no song of these choices, as one too long for a section's bars, gives way to the next drawn.
        for progression in self.progressions_by_chance()[:-1]:
            try:
                made = Setlist.from_data(data=composed(given=arranged(style=self._style(), song=self.song_picks(name, progression=progression)), version=version))
                break
            except (ValueError, IndexError, KeyError, SongFileError):
                made = None
        if made is None:
            last = self.progressions_by_chance()[-1:]
            given = arranged(style=self._style(), song=self.song_picks(name, progression=last[0] if last else None))
            made = Setlist.from_data(data=composed(given=given, version=version))
        made.get_item(section=Section.SONGS, name=name).set_wizard_choices(self.to_data())
        # A part written for a section that leaves the part out is played by nothing, and would be left behind in the open set.
        made.remove_unused()
        # Each pattern goes in the group named after the track that plays it.
        made.group_patterns_by_track(made.get_item(section=Section.SONGS, name=name))
        return made
