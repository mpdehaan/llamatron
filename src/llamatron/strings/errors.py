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

"""Every error message the program raises or reports, as templates filled in with .format().

Each constant starts with ERR_, and a message lives here and nowhere else, so that wording can be
kept consistent and a string in test code is never mistaken for a data key. The groups are by
the module that raises them. The wording rules are in CLAUDE.md: a raised message is a lower-case
fragment with no full stop, because the place it happened is put in front of it; a bad value reads
"x must be ..., got value"; a wrong type reads "expected a Note, got value"; names are in
parentheses and only the value after "got" keeps its repr; lists are joined with commas.
"""


# music/chord.py
ERR_CHORD_NOT_A_LIST = 'expected a list of notes, got {value!r}'
ERR_NO_NOTES = 'a chord needs at least one note'
ERR_NOT_A_NOTE = 'expected a Note, got {value!r}'

# cli.py
ERR_ONLY_WITH_TO = '{options} only works with --to'
ERR_TO_NEEDS_SET = '--to needs a set file to write'
ERR_NOT_WITH_TO = '{options} does not work with --to, which exports instead of opening the tracker'
ERR_NEEDS_FORCE = '{path} holds values that cannot be used, pass --force to export with each one changed as listed above'
# The line printed on stderr when the command line or the tracker can't go on.
ERR_PRINTED = 'error: {problem}'

# grid/clip_grid.py
ERR_CLIP_GRID_NOT_A_POSITION = 'expected a Note, Chord, Rest, Degree or shorthand for one, got {value!r}'
ERR_INVALID_NAME = 'a name must be text, got {name!r}'
ERR_INVALID_TEMPO = 'tempo must be a number of at least {lowest}, got {tempo!r}'
ERR_NOT_A_SCALE = 'expected a Scale, got {scale!r}'
ERR_INVALID_LOOP = 'loop must be true or false, got {loop!r}'
ERR_INVALID_MUTE = 'mute must be true or false, got {mute!r}'
ERR_INVALID_DRUM = 'drum must be true or false, got {drum!r}'
ERR_INVALID_FLUIDSYNTH = 'whether a column plays through FluidSynth must be true or false, got {fluidsynth!r}'
ERR_INVALID_TIME = 'time must not be negative, got {time!r}'
ERR_INVALID_CONTROL_NUMBER = '{name} must be an integer from {lowest} to {highest}, got {value!r}'
ERR_INVALID_SLIDE = 'slide must be true or false, got {slide!r}'
ERR_NOT_CONTROLS = 'expected a list of Controls, got {value!r}'
ERR_NOT_NOTES = 'expected a list of notes, chords and rests, got {value!r}'
ERR_NO_LENGTH = '{position!r} has no length, and the clip has no note_length'
ERR_INVALID_SECTION = 'a section must start at 0 or later and end after it starts, got {start} to {end}'
ERR_INVALID_TIMES = 'times must be a positive integer, got {times!r}'
ERR_NOT_A_CLIP_COLUMN = 'expected a ClipColumn, got {value!r}'
ERR_COLUMN_IN_A_GRID = 'column is already in a grid: {column!r}'
ERR_NOT_A_CLIP_ROW = 'expected a ClipRow, got {value!r}'
ERR_ROW_IN_A_GRID = 'row is already in a grid: {row!r}'
ERR_NOT_A_CLIP = 'expected a Clip, got {value!r}'
ERR_COLUMN_NOT_IN_GRID = 'column is not in this grid: {column!r}'
ERR_ROW_NOT_IN_GRID = 'row is not in this grid: {row!r}'

# composition/clip_slot.py
ERR_CLIP_SLOT_EXPECTED_SETTINGS = 'expected clip settings, got {data!r}'
# How a cell is named in its messages: by its scene and its track.
ERR_CLIP_SLOT_WHERE = '{where}, track ({track})'
ERR_NO_GRAB_TRACK = 'grab_track: no track called ({name})'
ERR_GRABS_ITSELF = 'grab_track: a clip cannot grab from its own track'
ERR_BAD_REPEAT = 'repeat must be an integer from {lowest} to {highest}, got {value!r}'
ERR_LOOP_NOT_TRUE_OR_FALSE = 'loop must be true or false, got {value!r}'
ERR_LAUNCH_TOGETHER_NOT_TRUE_OR_FALSE = 'launch_together must be true or false, got {value!r}'
ERR_NEEDS_PATTERN = 'needs a pattern'
ERR_NOT_PATTERN_NAMES = 'patterns must be a list of at least 1 pattern name, got {value!r}'
ERR_PATTERN_AND_PATTERNS = 'a clip has pattern or patterns, not both'
ERR_PATTERNS_DRUMS_AND_NOTES = 'a drum pattern and a pattern of notes cannot share a clip'
ERR_CLIP_SLOT_NO_SUCH_PATTERN = 'no pattern called ({name})'
ERR_NO_SUCH_CHAIN = 'no chain called ({name})'
ERR_MAKE_A_CHAIN_FIRST = 'There are no chains yet. Make one on the Chains page first.'
ERR_NOT_CHAIN_NAMES = 'expected a list of chains by name, got {value!r}'
ERR_CHAIN_AND_CHAINS = 'chain and chains cannot both be given; chains holds them all'
ERR_MORPH_NEEDS_BOTH = 'a morph needs both morph_to and morph_style'
ERR_MORPH_TOO_FEW_REPEATS = 'a morph needs a repeat of {lowest} or more'
ERR_BAD_MORPH_STYLE = 'morph_style must be one of: {choices}, got {value!r}'
ERR_BAD_FOLLOW_ACTION = 'follow_action must be one of: {choices}, got {value!r}'
ERR_BAD_SECTION = 'section must be one of: {choices}, got {value!r}'
ERR_BAD_LIVE_RESPONSIVENESS = 'live_responsiveness must be one of: {choices}, got {value!r}'
ERR_MORPH_STYLE_WITHOUT_MORPH = 'morph_style needs a morph_to, since it only says how a morph goes'

# composition/chain.py
ERR_EXPECTED_LIST = 'expected a list of generators'
ERR_ONE_GENERATOR_PER_STEP = 'each step must be one generator, got {step!r}'
ERR_UNKNOWN_GENERATOR = 'unknown generator ({kind}), expected one of: {kinds}'
ERR_NO_SUCH_GENERATOR = 'no {kind} called ({name})'
ERR_CHAIN_NO_SUCH_STEP = 'no step {place} in a chain of {steps} steps'

# composition/checks.py
ERR_AT = '{where}: {problem}'
ERR_BAD_WRITTEN_LENGTH = 'expected an integer or a fraction such as 1/8, got {value!r}'
ERR_LENGTH_TOO_LONG = 'a length can be at most {most}, got {value!r}'
ERR_UNKNOWN_SETTING = 'unknown setting ({name}), expected one of: {allowed}'
ERR_EXPECTED_NUMBER = 'expected a number, got {value!r}'
ERR_EXPECTED_NUMBER_LIKE = 'expected a number such as 2 or 1/8, got {value!r}'
ERR_BAD_TIME = 'expected a length such as 1/8 or a count of bars such as 2 bars, got {value!r}'
ERR_LENGTH_NOT_POSITIVE = 'a length must be more than zero, got {value!r}'
ERR_CHECKS_BAD_OCTAVE = 'an octave must be an integer from {lowest} to {highest}, got {value!r}'

# composition/generator_settings.py
ERR_NEEDS_SETTING = 'needs {name}'
ERR_NOT_A_CHOICE = '{name} must be one of: {choices}, got {value!r}'
ERR_GENERATOR_NOT_INTEGER = '{name} must be an integer, got {value!r}'
ERR_GENERATOR_BAD_OCTAVE_RANGE = '{name} must be an integer from {lowest} to {highest}, got {value!r}'
ERR_GENERATOR_BAD_OFFSETS = '{problem}'
ERR_DRIFT_BAD_SCALE = 'must be the name of a scale, got {value!r}'
ERR_DRIFT_BAD_ROOT = 'must be one of: {roots}, got {value!r}'
ERR_ROOT_IN_BASS_NOT_TRUE_OR_FALSE = 'root_in_bass must be true or false, got {value!r}'
ERR_VOICE_LEADING_RANGE = 'lowest_octave must not be above highest_octave, got {lowest} and {highest}'
ERR_EUCLID_TOO_MANY_HITS = 'hits must not be more than steps, got {hits} and {steps}'
ERR_BAD_GUITAR_BAR = '{name} must be a list of 1 to {most} strokes, each one of: {choices}, got {value!r}'
ERR_BAD_GUITAR_ACCENTS = '{name} must be a list of at most {most} accents, each true or false, got {value!r}'
ERR_GUITARIFY_NOT_TRUE_OR_FALSE = '{name} must be true or false, got {{value!r}}'
ERR_BAD_STEP_ROW = '{name} must be a list of 1 to {most} steps, each true or false, got {value!r}'
ERR_BAD_GLIDE_AMOUNT = 'glide_amount must be a length from {least} to {most}, got {value!r}'
ERR_BAD_GM_SOUND = 'gm_sound must be an integer from {lowest} to {highest}, got {value!r}'
ERR_NOT_INVERSION = 'an inversion must be one of: {choices}'
ERR_INVERSION_ON_DRUMS = 'a drum pattern cannot hold inversions, since it has no chords'
ERR_NOT_TENSIONS = 'tensions must be a list of some of: {choices}, each once'
ERR_TENSION_ON_DRUMS = 'a drum pattern cannot hold tensions, since it has no chords'
ERR_NOT_KEYSWITCHES = 'keyswitches must be a list of some of: {choices}, each once'
ERR_NOT_CHORD_SCALE = 'a chord scale must be one of: {choices}'
ERR_CHORD_SCALE_ON_DRUMS = 'a drum pattern cannot hold a chord scale, since it has no scale'
ERR_BAD_PROGRESSION_CHORDS = 'chords must be a list of 1 to {most} degrees from {lowest} to {highest}, got {value!r}'
ERR_BAD_PROGRESSION_TENSIONS = '{name} must be a list as long as the chords, each a list of some of {choices} or nothing, got {value!r}'
ERR_BAD_PROGRESSION_ROW = '{name} must be a list as long as the chords, each {choices} or nothing, got {value!r}'
ERR_BAD_SHAPE_PERCENT = '{name} must be an integer from {lowest} to {highest}, got {value!r}'
ERR_BAD_SHAPE_THEN = '{name} must be one of: {choices}, got {value!r}'
ERR_GENERATOR_BAD_ADD = '{name} must be an integer from {lowest} to {highest}, got {value!r}'
ERR_GENERATOR_BAD_STEP_ADDS = 'must be a list of 1 to {most} adds, each an integer from {lowest} to {highest} or blank, got {value!r}'
ERR_GENERATOR_NOT_A_LIST = '{name} must be a list, got {value!r}'
ERR_GENERATOR_NO_SUCH_SETTING = 'unknown setting ({name}), expected one of: {names}'
ERR_NOT_SETTINGS = 'expected settings by name, got {value!r}'
ERR_NO_OFFSETS = 'has no offsets to change'
ERR_NO_SUCH_OFFSET = 'no offset step {step} in {count} steps of offsets'

# composition/setting.py
ERR_NEEDS_CHECK = '{kind} needs a check() method'

# composition/llama_data.py
ERR_NEEDS_TO_DATA = '{kind} needs a to_data() method'
ERR_NEEDS_FROM_DATA = '{kind} needs a from_data() class method'
# What a screen says when asked the way to something its cursor cannot reach, which a test or the tutorial asked for by name.
ERR_NO_SUCH_PLACE = '{screen} has no place for its cursor called ({target})'

# composition/named_scale.py
ERR_EXPECTED_ROOT_AND_TYPE = 'expected a root and a type, got {data!r}'
ERR_EXPECTED_ROOT_NOTE = 'expected a root note such as F or Bb, got {root!r}'
ERR_UNKNOWN_SCALE_TYPE = 'unknown scale type ({kind}), expected one of: {names}'

# composition/pattern.py
ERR_PATTERN_EXPECTED_SETTINGS = 'expected pattern settings'
ERR_BAD_SCALE_LENGTH = '{name} must be an integer from {lowest} to {highest}, got {value!r}'
ERR_BAD_STEPS = 'steps must be an integer of {lowest} or more, got {value!r}'
ERR_DRUM_NOT_TRUE_OR_FALSE = 'drum must be true or false, got {value!r}'
ERR_CLIP_NEEDS_A_PATTERN = 'a clip plays at least 1 pattern'
ERR_BAD_PATTERN_ORDER = 'pattern order must be one of: {choices}, got {value!r}'
ERR_BAD_DIRECTION = 'direction must be one of: {choices}, got {value!r}'
ERR_ROW_WRONG_LENGTH = '{row} must be a list of {steps} values, got {value!r}'
ERR_TOGGLE_IS_NULL = '{row} must be true or false, got null'
ERR_BAD_STEP_VALUE = '{row} {problem}, got {value!r}'
ERR_TIE_ON_A_NOTE = 'step {step} has both a note and a tie, but a tied step holds the note before it and cannot have its own'
ERR_NO_SUCH_ROW = 'no row called ({row})'
ERR_PATTERN_NO_SUCH_STEP = 'no step {step} in a pattern of {steps} steps'
ERR_PATTERN_NOT_AN_ORDER = 'expected every step of the pattern once, got {order!r}'
# What a step's value has to be on each kind of row, for ERR_BAD_STEP_VALUE.
ERR_NOT_NOTE_LETTER = 'in a drum pattern, must be a note letter from A to G'
ERR_NOT_DEGREE = 'must be a scale degree of {lowest} or more'
ERR_NOT_ACCIDENTAL = 'must be # or b'
ERR_NOT_GATE_MODIFIER = 'must be d for dotted or t for triplet'
ERR_CHORD_ON_DRUMS = 'is not used in a drum pattern'
ERR_REGISTER_NOTE_ON_DRUMS = 'cannot move notes in a drum pattern, so it can only be 0'
ERR_NOT_REGISTER_USE = 'must be 1 to add the register, -1 to subtract it, or 0'
ERR_RESTART_ON_FIRST_STEP = 'the first step cannot start the pattern over'
ERR_NOT_STATEMENT_CHOICE = 'must be one of: {choices}'
ERR_NOT_STATEMENT_VALUE = 'must be an integer from {lowest} to {highest} or one of: {choices}'
ERR_NOT_CHORD = 'must be one of: {symbols}'
ERR_NOT_IN_RANGE = 'must be an integer from {lowest} to {highest}'
ERR_PATTERN_NOT_TRUE_OR_FALSE = 'must be true or false'
# How the places of a gate, an octave or a step size in a pattern are named in messages.
ERR_WHERE_IN_ROW = '{where}, {row}'

# composition/register.py
ERR_REGISTER_EXPECTED_SETTINGS = 'expected register settings, got {data!r}'
ERR_BAD_VALUE = '{name} must be an integer from {lowest} to {highest}, got {value!r}'
ERR_BAD_BOUND_REGISTER = '{name} must be one of: {choices}, got {value!r}'
ERR_BAD_RESET_BEHAVIOR = '{name} must be one of: {choices}, got {value!r}'
ERR_RESET_EACH_SCENE_NOT_TRUE_OR_FALSE = 'reset_each_scene must be true or false, got {value!r}'
ERR_OUT_OF_ORDER = 'needs minimum ({minimum}) <= default ({default}) <= maximum ({maximum})'
ERR_REGISTER_NO_SUCH_SETTING = 'unknown register setting ({name}), expected one of: {names}'

# composition/scene.py
ERR_SCENE_EXPECTED_SETTINGS = 'expected scene settings'
ERR_NO_SUCH_TRACK = 'no track called ({track})'
ERR_SCENE_NO_SUCH_SCALE = 'no scale called ({scale})'
ERR_BAD_RAMP_BARS = 'a ramp\'s bars must be an integer from {lowest} to {highest}, got {value!r}'
ERR_BAD_RESET = 'reset must be a list of registers from: {names}, got {value!r}'
ERR_BAD_REGISTER_VALUES = '{name} must give registers from {names} an integer each from {lowest} to {highest}, got {value!r}'
ERR_TOO_MANY_STATEMENTS = '{name} must be a list of at most {most} statements, got {value!r}'
ERR_BAD_STATEMENT = '{name}: a statement must be a register, an operator and what the operator needs, got {value!r}'
ERR_STATEMENT_BAD_REGISTER = '{name}: register must be one of: {names}, got {value!r}'
ERR_STATEMENT_BAD_OPERATOR = '{name}: operator must be one of: {choices}, got {value!r}'
ERR_STATEMENT_BAD_COMPARISON = '{name}: comparison must be one of: {choices}, got {value!r}'
ERR_STATEMENT_BAD_NUMBER = '{name}: {part} must be a register or an integer from {lowest} to {highest}, got {value!r}'
ERR_STATEMENT_DIVIDES_BY_ZERO = '{name}: cannot divide by 0'
ERR_STATEMENT_EXTRA_PART = '{name}: ({operator}) takes no {part}, got {value!r}'
ERR_NO_SUCH_STATEMENT = 'no statement at place {place}, expected 0 to {most}'
ERR_NO_SUCH_REGISTER = 'unknown register ({name}), expected one of: {names}'
ERR_NO_CLIP_SLOT = 'no clip on track ({track})'
ERR_SCENE_NAME_NOT_TEXT = 'name must be text, got {value!r}'

# composition/setlist.py
ERR_CANT_READ = 'cannot read {path}: {reason}'
ERR_NOT_YAML = '{path} is not valid YAML: {problem}'
ERR_NOT_A_SETLIST = "expected the set's settings at the top of the file"
ERR_SONGS_NOT_NAMED = 'songs: expected songs by name, each with its settings'
# How a part of a song is placed in a message: the song, then the part, like song (one), scene entry 2.
ERR_WHERE_WITHIN = '{where}, {part}'

# composition/song.py
ERR_NOT_A_SONG = "expected a song's settings, got {value!r}"
ERR_NOT_TEXT = '{name} must be text, got {value!r}'
ERR_SONG_BAD_VERSION = 'version must be three integers separated by dots, such as 1.0.2, got {value!r}'
ERR_PROTECTED_NOT_TRUE_OR_FALSE = 'protected must be true or false, got {value!r}'
ERR_SONG_BAD_OCTAVE_LABELS = 'expected one of: {choices}, got {value!r}'
ERR_BAD_DEFAULT_FOLLOW_ACTION = 'default_follow_action must be one of: {choices}, got {value!r}'
ERR_SCALES_NOT_NAMED = 'scales: expected scales by name, each with a root and a type'
ERR_SONG_NO_SUCH_SCALE = 'scale: no scale called ({scale})'
ERR_SONG_NO_SUCH_GROOVE = 'groove: no groove called ({name})'
ERR_SONG_NO_SUCH_PREVIEW_INSTRUMENT = 'preview_instrument: no instrument called ({name})'
ERR_TRACKS_NOT_NAMED = 'tracks: expected tracks by name, each with its settings'
ERR_GENERATORS_NOT_NAMED = '{section}: expected settings by name'
ERR_SCENES_NOT_A_LIST = 'scenes: expected a list of scenes'
ERR_REGISTERS_NOT_NAMED = 'registers: expected registers from: {names}, each with its settings'
# How messages name an object in the file: a named one by its kind and name, and a scene by its place.
ERR_WHERE_NAMED = '{label} ({name})'
ERR_WHERE_SCENE_ENTRY = 'scene entry {number}'
ERR_SONG_NAME_NOT_TEXT = 'a name must be text, got {name!r}'
ERR_NAME_TAKEN = 'a {label} called ({name}) already exists'
ERR_NO_SUCH_ITEM = 'no {label} called ({name})'
ERR_NO_SUCH_SCENE = 'no scene at place {index} in {count} scenes'
ERR_SONG_BAD_SEED = 'seed must be an integer or none, got {value!r}'
ERR_SONG_BAD_WIZARD = 'wizard must be a mapping of settings, got {value!r}'

# composition/track.py
ERR_TRACK_EXPECTED_SETTINGS = 'expected track settings, got {data!r}'
# composition/groove.py
ERR_GROOVE_EXPECTED_SETTINGS = 'expected groove settings, got {data!r}'
ERR_BAD_GROOVE_CELLS = 'cells must be a list of {fewest} to {most} integers from {lowest} to {highest}, got {value!r}'
ERR_BAD_GROOVE_AMOUNT = 'a groove amount must be an integer from {lowest} to {highest}, got {value!r}'
ERR_NO_SUCH_GROOVE_CELL = 'no groove cell {step}, the groove has {count}'
ERR_FACTORY_GROOVE_NAME = 'a groove cannot be called ({name}), which is a factory groove, expected a name that is not one of: {names}'
ERR_GROOVE_NOT_NAME_OR_FALSE = 'groove must be the name of a groove or false, got {value!r}'
ERR_NO_SUCH_GROOVE = 'no groove called ({name})'
ERR_GROOVES_NOT_NAMED = 'grooves: expected grooves by name, each with its cells'

# composition/instrument.py
ERR_INSTRUMENT_EXPECTED_SETTINGS = 'expected instrument settings, got {data!r}'
ERR_DEVICE_NOT_TEXT = 'device must be the name of a MIDI output port, got {value!r}'
ERR_BAD_CHANNEL = 'channel must be an integer from {lowest} to {highest}, got {value!r}'
ERR_BAD_DEFAULT_VELOCITY = 'default_velocity must be an integer from {lowest} to {highest}, got {value!r}'
ERR_BAD_ACCENT = 'accent must be an integer from {lowest} to {highest}, got {value!r}'
ERR_BAD_KEYSWITCH_LEAD = 'keyswitch_lead must be an integer from {lowest} to {highest}, got {value!r}'
ERR_BAD_KEYSWITCHES = 'keyswitches must be a list of {count} slots, each blank or a name and a note, got {value!r}'
ERR_BAD_KEYSWITCH_NAME = 'a keyswitch name must be text of at most {most} characters, got {value!r}'
ERR_BAD_KEYSWITCH_NOTE = 'a keyswitch note must be an integer from {lowest} to {highest}, got {value!r}'
ERR_BAD_KEYSWITCH_SLOT = 'a keyswitch slot must be an integer from {lowest} to {highest}, got {value!r}'
ERR_INSTRUMENTS_NOT_NAMED = 'instruments: expected instruments by name, each with its settings'
ERR_NO_SUCH_INSTRUMENT = 'no instrument called ({name})'
ERR_REAL_TIME_NOT_TRUE_OR_FALSE = 'real_time must be true or false, got {value!r}'
# grid/clip.py
ERR_NOT_A_GROOVE = 'expected a Groove, got {value!r}'
ERR_TRACK_NOT_TRUE_OR_FALSE = '{name} must be true or false, got {value!r}'
ERR_BAD_TRANSPOSE = 'transpose must be an integer from -{most} to {most}, got {value!r}'
ERR_BAD_TRACK_OCTAVE = '{name} must be an integer from {lowest} to {highest}, got {value!r}'
ERR_OCTAVE_RANGE_BACKWARDS = 'lowest_octave must not be above highest_octave, got {lowest!r} and {highest!r}'
ERR_BAD_CC_NUMBERS = 'cc must be a list of {lanes} CC numbers from {lowest} to {highest}, with ~ for a lane that sends nothing, got {value!r}'
ERR_NO_SUCH_LANE = 'no CC lane {lane}, expected one from 0 to {last}'

# generators/arp.py
ERR_ARP_NOT_AN_ORDER = 'expected a ChordOrder, got {value!r}'
ERR_ARP_BAD_SEED = 'seed must be an integer or none, got {value!r}'
ERR_NOT_A_JUMP = 'expected an OctaveJump, got {value!r}'
ERR_ARP_BAD_OCTAVE_RANGE = 'octave range must be an integer from {lowest} to {highest}, got {value!r}'
ERR_ARP_BAD_OFFSETS = 'offsets must be a list of {lowest} to {highest} steps, got {value!r}'
ERR_BAD_OFFSET = 'an offset must be an integer from -{most} to {most}, or None for a silent step, got {value!r}'

# generators/auto_ratchet.py
ERR_AUTO_RATCHET_NOT_A_LIST = 'expected a list of counts, got {value!r}'
ERR_BAD_COUNT = 'a count must be a positive integer, got {value!r}'


# generators/blend.py, and exporters/timing.py for the scale
ERR_NOT_A_MODE = 'expected a BlendMode, got {value!r}'
ERR_BAD_AMOUNT = 'amount must be from {lowest} to {highest}, got {value!r}'
ERR_DEGREE_NEEDS_SCALE = '{degree!r} needs a scale, and none is set'
ERR_LENGTHS_DIFFER = 'the clips must be the same length, but they last {first} and {second}'

# music/sound.py
ERR_NOT_A_POSITION = 'expected a Note, Chord, Rest, Degree or Held, got {value!r}'

# music/held.py
ERR_BAD_SOUND = 'expected a Note, Chord or a phrase of them, got {value!r}'
ERR_BAD_PHRASE_PART = 'a held phrase holds Notes, Chords, Rests, Degrees and Held, got {value!r}'

# music/note.py
ERR_NOT_AN_INTEGER = 'expected an integer, got {value!r}'
ERR_BAD_LENGTH = 'a length must be a positive fraction of a whole note, got {value!r}'
ERR_BAD_DEGREE = 'a degree must be an integer of {lowest} or more, got {value!r}'
ERR_BAD_VELOCITY = 'velocity must be an integer from {lowest} to {highest}, got {value!r}'
ERR_BAD_GLIDE = 'glide must be true or false, got {value!r}'
ERR_BAD_NOTE_NAME = 'unknown note name ({value})'
ERR_NOTE_BAD_OCTAVE = 'an octave must be an integer from {lowest} to {highest}, got {value!r}'
ERR_OUTSIDE_MIDI = '{name}{octave} is outside the MIDI range: its number would be {number}'
ERR_NOT_A_CHORD_TYPE = 'expected a ChordType, got {value!r}'

# playback/clip_slot_player.py
# How messages name a cell: by its scene's number and its track.
ERR_CLIP_SLOT_PLAYER_WHERE = 'scene {scene}, track ({track})'
ERR_CANT_PLAY = '{where}: {problem}'

# playback/pattern_player.py
# How messages name a pattern, and what goes wrong while playing one.
ERR_WHERE_PATTERN = 'pattern ({name})'
ERR_PATTERN_PLAYER_NO_SUCH_PATTERN = '{where}: no pattern called ({name})'
ERR_NO_SCALE = '{where}: it uses scale degrees, but scene {scene} and the song have no scale'

# playback/song_renderer.py
ERR_RENDERER_EVERY_CLIP_LOOPS = '{scene}: every clip loops, so the scene needs at least one non-looping clip'
ERR_CIRCULAR_FOLLOW = '{scene}: the tracks follow each other\'s chords in a circle ({loop}), so take FollowChords off one of these clips'
ERR_CIRCULAR_GRAB = '{scene}: the grabs go round in a circle ({loop}), so remove the grab track from one of these clips'
# How messages name the chain a generator is used in.
ERR_WHERE_CHAIN = 'chain ({chain}), {kind}'

# support/rational.py
ERR_CANT_MAKE = 'expected an integer, a fraction, a float or text such as 5/16, got {value!r}'
ERR_DIVIDE_BY_ZERO = 'division by zero'

# exporters/ableton_project.py
ERR_BAD_TEMPLATE = 'template must be the path of a Live set, got {value!r}'
ERR_FILE_EXISTS = 'warning: stopping without writing anything, because {path} already exists'
ERR_NOT_LIVE_12 = '{template} was not saved by Live 12: {attributes}'
ERR_EMPTY_SONG = 'a Live set needs at least one scene and one track'
ERR_BAD_TEMPO = 'Live needs a tempo from {lowest} to {highest}, got {value!r}'
ERR_NO_MIDI_TRACK = '{template} needs a MIDI track to copy'
ERR_NO_CLIP = ('the first MIDI track in {template} needs a clip in it, because Live '
               'requires many details in a clip that are copied from there')

# exporters/exporter.py
ERR_FILES_EXIST = 'warning: stopping without writing anything, because {directory} already contains: {files}'
ERR_BAD_DIRECTORY = 'directory must be a path, got {value!r}'
ERR_NOT_A_GRID = 'expected a ClipGrid, got {value!r}'
ERR_NEEDS_EXPORT = '{kind} needs an export() method'
ERR_NEEDS_FILES = '{kind} needs to say which files it writes, as WritesOneFile or WritesManyFiles'

# exporters/timing.py
ERR_TIMING_NOT_A_POSITION = 'expected a Note, Chord or Rest, got {value!r}'

# music/scale.py
ERR_NOT_A_SCALE_TYPE = 'expected a ScaleType, got {value!r}'

# music/time_signature.py
ERR_BAD_TIME_SIGNATURE = 'time signature must be beats over a note value such as 6/8, with {lowest} to {highest} beats over one of: {units}, got {value!r}'
ERR_NOT_A_TIME_SIGNATURE = 'expected a TimeSignature, got {value!r}'

# tui/screens/arrange/arrange_page.py
# The mark beside a scene on the Arrange grid. The full explanation is the loop errors dialog.
ERR_ADD_A_PATTERN_FIRST = 'Add a pattern first, on the Patterns page.'
# Deleting the last scene or track is refused in a dialog.
ERR_LAST_SCENE_SHOWN = 'A song needs at least one scene, so the last one cannot be deleted.'
ERR_LAST_TRACK_SHOWN = 'A song needs at least one track, so the last one cannot be deleted.'
# A scene or track with clips, which can't be deleted while the song plays, since its clips may be playing.
ERR_SCENE_PLAYING_SHOWN = 'A scene with clips cannot be deleted while the song plays. Stop it first, with Space on the corner or Ctrl+T.'
ERR_TRACK_PLAYING_SHOWN = 'A track with clips cannot be deleted while the song plays. Stop it first, with Space on the corner or Ctrl+T.'
ERR_NO_PATTERNS_TITLE = 'No patterns'
ERR_NO_OTHER_TRACKS_TITLE = 'No other tracks'
ERR_ADD_ANOTHER_TRACK = 'Add another track to grab notes from, on the Tracks page.'

# tui/screens/set/main_page.py
ERR_NO_INSTRUMENTS_TITLE = 'No instruments'
ERR_ADD_INSTRUMENT_FIRST = 'Add an instrument first, on the Instruments page, and give a track it.'
# tui/transport.py: why nothing plays.
ERR_CANT_PLAY_TITLE = 'Cannot play'
ERR_REAL_TIME_OFF = 'Turn Real Time on first, with T on the main screen.'
ERR_NO_TRACK_HAS_AN_INSTRUMENT = 'No track has an instrument. Choose one at the bottom of a track editor, from Arrange.'
ERR_NO_TRACK_HAS_A_DEVICE = 'No track plays through an instrument with a device. Choose a device for an instrument on the Instruments page.'
ERR_DEVICE_NOT_CONNECTED = 'The device of instrument ({instrument}), ({device}), is not connected. Choose another on the Instruments page.'
# tui/silent_instruments.py: the warning when a set opens whose tracks play through instruments that cannot sound here.
ERR_SILENT_INSTRUMENTS_TITLE = 'Silent instruments'
ERR_FLUIDSYNTH_WILL_NOT_SOUND = 'Since FluidSynth is not installed, instruments using FluidSynth will not sound. Run sh user_scripts/install_fluidsynth.sh in the llamatron folder to install it.'
ERR_DEVICE_WILL_NOT_SOUND = 'The device of instrument ({instrument}), ({device}), is not connected, so it will not sound. The set keeps it, and the Instruments page can choose another.'
ERR_FLUIDSYNTH_NOT_INSTALLED = 'Some tracks play through FluidSynth, which is not installed. Run sh user_scripts/install_fluidsynth.sh in the llamatron folder to install it.'
# tui/pattern_preview.py: why Listen cannot play a pattern through the song's Preview instrument, on the status line.
ERR_NOT_A_NOTE_NAME = 'note must be a letter from A to G, # or b where wanted, and an octave, such as C3, got {text}'
ERR_NOTHING_TO_TRY_A_SOUND_WITH = 'to listen, install FluidSynth or set the Preview instrument on the Song page'
ERR_PREVIEW_INSTRUMENT_HAS_NO_DEVICE = 'preview instrument ({name}) has no device, so nothing plays'
ERR_PREVIEW_DEVICE_NOT_CONNECTED = 'the device of preview instrument ({name}), ({device}), is not connected, so nothing plays'
ERR_PREVIEW_FLUIDSYNTH_NOT_INSTALLED = 'preview instrument ({name}) plays through FluidSynth, which is not installed, so nothing plays'
ERR_CIRCULAR_GRAB_TITLE = 'Circular grab'
ERR_GRAB_CIRCLE = 'Grabbing from ({track}) would go round in a circle: {circle}.'
ERR_REMOVE_OTHER_GRAB = 'Remove the grab from another clip in this scene first.'
# The dialog that lists the scenes in which every clip loops, when exporting or when a loop is turned on.
ERR_LOOP_SCENES_TITLE = 'Scene loop errors'
ERR_LOOP_SCENES_INTRO = 'The following scenes have too many loops and need at least one non-looping clip:'

# tui/document.py
ERR_NOTHING_TO_EXPORT = 'there is nothing to export yet, because the song needs a track and a scene'
ERR_LAST_SONG = 'the set needs at least one song'
ERR_FILE_PROTECTED = '{path} is protected, so it cannot be written over'
ERR_SAVE_BEFORE_EXPORT = 'the set has to be saved before it is exported, because the exports are named after its file and written beside it'

# tui/screens/shared/list_page.py
ERR_CANT_DELETE_TITLE = 'Cannot delete'
# tui/screens/arrange/arrange_page.py: + under a cell's chains with no chain in the set to add.
ERR_NO_CHAINS_TO_ADD = 'the set has no chains to add: make one on the Chains page'
ERR_STILL_USED = '{what} is still used, so change these first:'
# After the first few lines of a list in a dialog, how many more there are.
ERR_AND_MORE = '... and {count} more'
ERR_EMPTY_NAME = 'a name cannot be empty'
ERR_NAME_IN_USE = 'the name ({name}) is already in use'
ERR_NAME_EMPTY_OR_IN_USE = 'that name is empty or already in use'
ERR_GROUP_COPY_NAME_TOO_LONG = 'the copy ({name}) would be longer than {most} characters'
ERR_TYPED_NOT_AN_INTEGER = '({text}) is not an integer'
ERR_TYPED_NOT_A_TIME_SIGNATURE = '({text}) is not a time signature such as 6/8, with {lowest} to {highest} beats over one of: {units}'
ERR_CANNOT_DIVIDE_BY_ZERO = 'cannot divide by 0'
ERR_OUT_OF_RANGE = '{number} must be from {low} to {high}'

# tui/screens/set/song_page.py, tui/screens/set/file_page.py and tui/screens/shared/everywhere.py
ERR_ADD_A_SCALE_FIRST = 'add a scale first, on the Scales page'
ERR_CANT_SAVE_TITLE = 'Cannot save'
ERR_CANT_SAVE = '{path}: {error}'
ERR_CANT_EXPORT_TITLE = 'Cannot export'
ERR_CANT_OPEN_TITLE = 'Cannot open'
# The Songs page, when the last song's deletion is refused.
ERR_LAST_SONG_SHOWN = 'the set needs at least one song, so the last one cannot be deleted'
ERR_NOTHING_TO_ADD_TITLE = 'Nothing to add'
ERR_BAD_COUNTS = 'counts must be integers of 1 or more, separated by spaces'

# tui/screens/pattern/pattern_editor.py and the rows in tui/components/
ERR_NOT_A_LENGTH = '({text}) is not an integer or a fraction such as 1/8'
ERR_LENGTH_OUT_OF_RANGE = 'a length must be more than 0 and at most {most}'
ERR_ROW_OUT_OF_RANGE = '{row} must be from {low} to {high}'
ERR_ADD_PAST_ALLOWED = '{row} adds more than {most} either way, the Allowed Inc Max of {register} in a song that plays it'
ERR_AT_ALLOWED_INC_MAX = '{register} adds at most {most} either way: its Allowed Inc Max on the Registers page'
# The munge dialog's refusals, when the cursor leaves nothing to rearrange.
ERR_NOTHING_AFTER = 'there are no steps after this one to reverse'
ERR_NOTHING_BEFORE = 'there are no steps before this one to reverse'
ERR_NOTHING_TO_PIVOT = 'there are no other steps to pivot around this one'
ERR_ONE_STEP = 'a pattern of one step cannot be rearranged'
ERR_MUNGE_TOO_MANY_STEPS = 'the pattern would have {steps} steps, and {most} is the most'
ERR_PATTERN_CANNOT_INTERLEAVE = 'a pattern takes steps only from one of its kind, drum or not, and holds no more steps than a pattern may'
ERR_INTERLEAVE_DRUM_MISMATCH = 'a drum pattern and a pattern of notes cannot be combined'
ERR_MUNGE_NUMBER_OUT_OF_RANGE = 'the number must be from {low} to {high}'
ERR_INVERT_NEEDS_A_NOTE = 'the melody is inverted around a note, on a pattern of notes'
ERR_INVERT_OUT_OF_RANGE = 'a note would leave the octaves a pattern may hold'
ERR_MUNGE_NO_SCALE = 'the pattern has no scale'
ERR_VOICE_LEADING_NEEDS_CHORDS = 'voice leading needs at least 2 chords'
ERR_NOTHING_TO_CROP = 'there are no steps after this one to remove'
ERR_SPLIT_OUT_OF_RANGE = 'steps in each new pattern must be from {low} to {high}'
ERR_ROLL_OUT_OF_RANGE = 'steps to roll must be from {low} to {high}'
ERR_NO_OTHER_PATTERNS = 'there are no other patterns to load'
# The Degree gauge stops at the scale's ends, and says where the octave is changed.
ERR_TOP_OF_SCALE = 'top of {scale}: change the octave on the Octave row'
ERR_BOTTOM_OF_SCALE = 'bottom of {scale}: change the octave on the Octave row'
# The piano roll.
ERR_NO_NOTE_HERE = 'no note under the cursor'
ERR_NOTHING_TO_SPLIT = 'the knife splits a note at one of its held steps'
ERR_NO_NOTE_ON_STEP = 'no note on this step'
ERR_NO_ROOM_AFTER = 'no room after the note'
ERR_NOTE_IS_ONE_STEP = 'the drag stops at one step'
ERR_STEPS_OUT_OF_RANGE = 'steps must be from {low} to {high}'

# support/memory.py
ERR_STALE_ANSWER = 'the answer kept for {key} is stale: kept {kept!r}, and worked out again {again!r}'

# tui/history.py
ERR_CHANGED_SNAPSHOT = 'a snapshot the undo history shares was changed after the history kept it'

# tui/document_parts/undo.py
ERR_STALE_DATA = 'the data the set keeps is stale: kept {kept!r}, and built again {again!r}'
ERR_WRONG_RESTORE = 'the set restored from a snapshot differs from the set read afresh from it: restored {restored!r}, and read afresh {afresh!r}'

# support/version.py
ERR_BAD_VERSION_TEXT = 'a version must be three integers separated by dots, such as 1.0.2, got {value!r}'
# realtime/outputs.py
ERR_NO_MIDI_LIBRARY = 'python-rtmidi is not installed, so no MIDI port can be opened'
ERR_SENDER_DID_NOT_START = 'the Realtime Sender Process did not start: a MIDI port could not be opened'
# exporters/wave_level.py and exporters/wave_fluidsynth.py: the WAV export through FluidSynth.
ERR_NOT_16_BIT_WAVE = '{path}: expected a 16-bit PCM WAV file, got {bits}-bit samples'
ERR_WAV_NEEDS_FLUIDSYNTH = 'the WAV export plays the song through FluidSynth, which is not installed: run sh user_scripts/install_fluidsynth.sh'
ERR_NO_FLUIDSYNTH_TRACKS = 'no track plays through an instrument whose Device is *FluidSynth, so the WAV export would be silent: choose *FluidSynth on the Instruments page'
ERR_FLUIDSYNTH_RENDER_FAILED = 'FluidSynth could not write the WAV file: {problem}'
# realtime/fluidsynth.py
ERR_FLUIDSYNTH_DID_NOT_START = 'FluidSynth did not start: its MIDI port did not appear within {seconds} seconds'
ERR_FLUIDSYNTH_ENDED = 'FluidSynth ended as it started, with exit code {code}'

# cli.py and tui/launch.py: launching the tracker to play on its own.
ERR_RECORDING_SONG_LOOPS = 'every clip loops in {scenes}, so playing the song would wait there forever: turn Loop off on one clip to record it'
ERR_LAUNCH_NEEDS_SET = 'the launch options need a set file to play'
ERR_BATCH_VIDEO_NEEDS_VISUALIZER = '--batch-video needs --visualizer to name the mode the video shows'
ERR_NO_SUCH_MIDI_PORT = 'no MIDI output port called ({name})'

# importers/midi_import.py
ERR_MIDI_NO_NOTES = 'the MIDI file plays no notes'

# tui/screens/set/importing.py
ERR_CANT_IMPORT_TITLE = 'Cannot import'
ERR_CANT_READ_MIDI = 'The file {file} cannot be read as MIDI: {problem}.'

# macro_composer/arranger.py
ERR_NO_STYLE_KIND = 'the style ({}) has no template called ({}); it has: {}'
ERR_NO_TRAIT_VALUE = 'the trait ({}) has no value called ({}); it has: {}'
ERR_PICK_NEEDS = 'the pick {} = {} needs {} = {}, and the song picks {}'
ERR_NO_STYLE_FORM = 'the style ({}) has no form called ({}) for the kind ({})'
ERR_MELODY_NEEDS_RHYTHMS = 'the smart melody style needs a style that has rhythms'
ERR_NO_SUCH_WAY_BESIDE = 'no way of playing beside the tune called ({})'
ERR_PIECE_SOUND = 'the sound of the kit piece ({}) must be a drum of the kit, or a General MIDI sound with a note, got {!r}'
ERR_NO_SUCH_BREAK = 'there is no drum break called ({}), expected one of: {}'
ERR_BREAK_CUT = 'break_cut must be an integer from {} to {}, got {!r}'
ERR_NO_STYLE_FORMS = 'the song gives no form and the style ({}) suggests none'
ERR_NO_SUCH_SECTION = 'the form names the section ({}), which neither the song nor the style describes'

# macro_composer/composer.py
ERR_NO_CLIP_FITS = 'scene ({}) lasts {} bars, which no part it plays divides evenly'

# macro_composer/decomposer.py
ERR_ONE_SONG = 'a MacroComposer input holds one song, and the set holds {}'

# macro_composer/notation.py
ERR_NOT_A_TUNE = 'the pattern cannot be written as a tune'
ERR_NOT_A_BAR = 'the pattern cannot be written as a drum bar'

# The song wizard's choices (macro_composer/wizard_choices.py).
ERR_WIZARD_NO_SUCH_GENRE = 'genre must be one of the genres, got {value!r}'
ERR_WIZARD_NO_SUCH_SUBGENRE = 'subgenre must be one of the genre, got {value!r}'
ERR_WIZARD_NO_SUCH_VARIANT = 'variant must be one of: {choices}, got {value!r}'
ERR_WIZARD_NO_SUCH_ROOT = 'key must be a note name, got {value!r}'
ERR_WIZARD_NO_SUCH_SCALE_TYPE = 'scale type must be one the wizard offers, got {value!r}'
ERR_WIZARD_TEMPO = 'tempo must be an integer from {low} to {high}, got {value!r}'
ERR_WIZARD_NO_SUCH_FORM = 'form must be one the subgenre suggests, got {value!r}'
ERR_WIZARD_NOT_READY = 'the wizard needs a genre and a subgenre first'
ERR_WIZARD_CANNOT_LISTEN = 'cannot listen: FluidSynth is not installed'
ERR_WIZARD_NOTHING_TO_LISTEN_TO = 'cannot listen: the song as chosen cannot be made'
ERR_WIZARD_SWITCH = 'expected true or false, got {value!r}'
ERR_WIZARD_FORM_ANSWER = 'the form has no answer {value!r} for ({name})'
ERR_WIZARD_NO_FORM_QUESTIONS = 'the subgenre has no verse and chorus to make a form of'
ERR_WIZARD_INTRO_HOOK = 'nobody called {value!r} can say the hook in the intro'
ERR_WIZARD_HOOK_PLACEMENT = 'the hook cannot be placed at {value!r} in this song'
ERR_WIZARD_SECOND_HOOK = 'a second hook cannot be sung in {value!r} in this song'
ERR_WIZARD_PHRASING = 'phrasing has no {name} of {value!r}'
ERR_WIZARD_CHORDS = 'chords must be degrees from 1 to 7 with a space between, such as 6 4 1 b7, two that share a bar joined by a dash, such as 1-5, got {value!r}'
ERR_WIZARD_PART_NO_MELODY = 'part {number} has no melody: choose a player in Melody under Part {number}'
ERR_WIZARD_NO_PART = 'the intro has no part'
ERR_WIZARD_SECTION_OWN = 'a section cannot take {value!r} for its {field}'
ERR_WIZARD_SECTION_OWN_UNMADE = 'the song cannot be made with {value!r} for the section\'s {field}: {problem}'
ERR_WIZARD_GENRE_HAS_NO_PLAN = 'the genre has no song plan yet'
ERR_WIZARD_NO_SONG_PLAN = 'the song has no song plan: switch Song plan on first'
ERR_WIZARD_CONTRAST = 'contrast must be an integer from {low} to {high}, got {value!r}'
ERR_WIZARD_RIFF = 'the song has no such riff to play, got {value!r}'
ERR_WIZARD_RIFF_UNMADE = 'the song cannot be made with the riff {value!r}: {problem}'
ERR_WIZARD_REACTS = 'reacts must be an integer from {low} to {high} for a player of a planned song, got {value!r}'
ERR_WIZARD_CHORDS_SHARED = 'chords with two that share a bar must be {most} bars or fewer, got {value!r}'
ERR_WIZARD_SWING = 'swing must be one of: {choices}, for a song in four not written in triplets, got {value!r}'
ERR_WIZARD_DYNAMICS = 'dynamics must be an integer from {low} to {high} for a player in the band, got {value!r}'
ERR_WIZARD_LOUDNESS = 'a loudness level must be ghost, soft, normal or accent, with an integer from {low} to {high}, for a player in the band, got {value!r}'
ERR_WIZARD_COMES_IN = 'the player cannot come in ({value})'
ERR_WIZARD_LAYS_OUT = 'the player cannot lay out ({value})'
ERR_WIZARD_PLAYS_UNMADE = 'the player cannot play there: {problem}'
ERR_WIZARD_HOOK_BEHAVIOR = 'the hook behavior must be one of: {choices}, got {value!r}'
ERR_WIZARD_WRITING_GAUGE = 'the gauge ({name}) must be an integer from {low} to {high}, got {value!r}'
ERR_WIZARD_START = 'a song cannot start with ({value})'
ERR_WIZARD_END = 'a song cannot end with ({value})'
ERR_WIZARD_FIRST_PLAYER = 'the song cannot start with the player ({value})'
ERR_WIZARD_SETUP_BARS = 'the setup cannot last ({value}) bars'
ERR_WIZARD_START_UNMADE = 'the song cannot be made that way: {problem}'
ERR_WIZARD_HOOK_LINE = 'the hook cannot be these notes: {problem}'
ERR_NOT_WHILE_DRAFTING = 'cannot do this while editing notes for the wizard: ESC goes back to the wizard'
ERR_BAD_BY_SECTION = 'by_section must be settings by kind of section, each one of: {choices}, got {value!r}'
ERR_MUSICIAN_PLAYS_NOT_TRUE_OR_FALSE = 'plays must be true or false, got {value!r}'
ERR_WIZARD_PLAYER_PLAYS_NOTHING = 'the player plays in no section of the song'
ERR_WIZARD_MUSICIAN = 'a player must be a musician as the Musician page makes one, got {value!r}: {problem}'
ERR_WIZARD_TUNE_PHRASING = 'phrasing must be the settings of a Phrasing, got {value!r}: {problem}'
ERR_WIZARD_NO_SUCH_RIFF = 'no riff called {value!r}'
ERR_WIZARD_NO_RIFF_TO_GIVE = 'the player knows every riff of the song'
ERR_WIZARD_RIFF_NAME_TAKEN = 'a riff is already called ({name})'
ERR_WIZARD_RIFF_FITS_NOWHERE = 'no section of the song can play the riff ({riff})'
ERR_WIZARD_SECTION_PART = 'the player ({player}) cannot play {value!r} in the kind of section ({kind})'
ERR_WIZARD_MELODY_WAY = 'the melody field {field!r} cannot be {value!r}'
ERR_WIZARD_NO_SUCH_TUNE_PLAYER = 'no player of the band who can play the tune is called {value!r}'
ERR_WIZARD_NO_TUNE_IN = 'no section of the kind {value!r} has a tune'
ERR_WIZARD_TUNE_PATTERN = 'the tune cannot be this pattern: {problem}'
ERR_WIZARD_EXTRAS = 'the picks of a song file must be a mapping, got {value!r}'
# macro_composer/wizard_file.py
ERR_SONG_FILE_NOT_A_MAPPING = '{path}: a song file must be a mapping of choices'
ERR_SONG_FILE_NOT_READY = '{path}: a song file needs a genre and a subgenre that exist'
ERR_SONG_FILE_FORM_ENTRY = '{path}: form entry {place} must be a kind of section or a mapping with a kind, got {value!r}'
ERR_SONG_FILE_FORM = '{path}: the form could not be used: each kind must be one the subgenre plays, with bars and players it can have'
ERR_WIZARD_ONLY_ALONE = '--wizard cannot be given with a set or with --to'
ERR_ONLY_WITH_WIZARD = '{options} can only be given with --wizard'
ERR_WIZARD_SEED = 'seed must be an integer, got {value!r}'
ERR_WIZARD_NO_SUCH_PLAYER = 'player must be one of the genre, got {value!r}'
ERR_WIZARD_NO_SUCH_WAY = '{trait} must be a way of playing that fits the other choices, got {value!r}'
ERR_WIZARD_NO_WAY = 'no way of playing fits the other choices for ({value})'
ERR_WIZARD_BUSY = 'busy must be an integer from {low} to {high}, got {value!r}'
ERR_WIZARD_NO_SUCH_ANSWERER = 'no player called ({value}) can answer the tune'
ERR_WIZARD_NO_SUCH_WAY_BESIDE = 'no way of playing beside the tune called ({value})'
ERR_WIZARD_SECTION_HAS_NO_ROLE = 'nobody answers the tune in section {value}'
ERR_WIZARD_FILLS_BUSY = 'fills busy must be an integer from {low} to {high}, got {value!r}'
ERR_WIZARD_PLAYER_GAUGE = 'a gauge of a player must be an integer from {low} to {high}, got {value!r}'
ERR_WIZARD_NO_SUCH_PLAYER_GAUGE = 'the player has no gauge called ({value})'
ERR_WIZARD_LAST_PLAYER = 'a band needs one player'
ERR_WIZARD_FILLS = 'fills must be an integer from 1 to 4, got {value!r}'
ERR_WIZARD_QUIET_NOTES = 'quiet notes must be true or false, got {value!r}'
ERR_WIZARD_NO_SUCH_PIECE = 'piece must be a piece of the kit the drums play, got {value!r}'
ERR_WIZARD_LAST_PIECE = 'a kit needs one piece: leave the drums out of the band for no drums'
ERR_WIZARD_GUITARISTS = 'guitarists must be 2, or 1 where the band can have one, got {value!r}'
ERR_WIZARD_BAND_SOUNDS = 'sounds must be one of: usual, acoustic, electric, synth, got {value!r}'
ERR_WIZARD_SOUND = 'sound must be a General MIDI sound, an integer from {low} to {high}, got {value!r}'
ERR_WIZARD_NO_SUCH_MELODY = 'melody must be a melody style the subgenre can use, got {value!r}'
ERR_WIZARD_NO_HOOK = 'no section of the genre has a hook'
ERR_WIZARD_HOOK_TAKE = 'hook take must be an integer of 0 or more, got {value!r}'
ERR_WIZARD_NO_SUCH_ROW = 'row must be a row the player is dealt, got {value!r}'
ERR_WIZARD_ROW = '{name} must be {fewest} to {most} integers from {low} to {high}, got {value!r}'
ERR_WIZARD_NO_SUCH_BREAK = 'break must be a drum break the subgenre can play, got {value!r}'
ERR_WIZARD_BREAK_CUT = 'cut up must be an integer from {low} to {high}, got {value!r}'
ERR_WIZARD_PIECE_SOUND = 'a kit piece sounds as a drum of the kit or a General MIDI sound, got {value!r}'
ERR_WIZARD_PIECE_NOTE = 'note must be an integer from {low} to {high}, got {value!r}'
ERR_WIZARD_PIECE_HAS_NO_NOTE = 'the kit piece ({value}) plays a drum, which has no note to choose'
ERR_WIZARD_NO_SUCH_MELODY_SETTING = 'the melody style has no setting called ({value})'
ERR_WIZARD_MELODY_SWITCH = 'the melody setting ({name}) must be true or false, got {value!r}'
ERR_WIZARD_MELODY_NUMBER = 'the melody setting ({name}) must be an integer from {low} to {high}, got {value!r}'
ERR_WIZARD_GAUGE = 'the melody gauge ({name}) must be an integer from {low} to {high}, got {value!r}'
ERR_WIZARD_NO_SUCH_SECTION = 'section must be a place in the form, got {value!r}'
ERR_WIZARD_NO_SUCH_SECTION_KIND = 'section must be a kind the genre has, got {value!r}'
ERR_WIZARD_LAST_SECTION = 'a form needs one section'
ERR_WIZARD_SECTION_BARS = 'bars must be a length the section can have, got {value!r}'
ERR_WIZARD_SECTION_NEEDS_PLAYER = 'a section needs one player'
ERR_WIZARD_BAD_SECTIONS = 'sections must be a list of sections of the genre, got {value!r}'

# tui/screens/wizard/wizard_page.py and the branches beside it
ERR_WIZARD_CHOOSE_GENRE = 'choose a genre first'
ERR_WIZARD_CHOOSE_GENRE_AND_SUBGENRE = 'choose a genre and a subgenre first'
