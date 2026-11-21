# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The song wizard's limits and names: every number, list and name the wizard's choices are held to and kept under.

The wizard's choices and each part of them read these, and so do the wizard's pages, which show a gauge's ends and a
field's choices by the same names the choices check a value against. The module holds no behaviour.
"""

from llamatron.composition.file_format import SectionKind
from llamatron.composition.groove import FactoryGroove
from llamatron.macro_composer import arranger, joins as joins_values, melody as melody_writer, notation as tune_notation, phrasing, riffs as riffs_values, song_plan

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

# How often a fill comes, by position: never, at the end of each section, every four bars, every two.
FEWEST_FILLS = 1
EACH_SECTION_FILLS = 2
MOST_FILLS = 4
FILLS_EVERY = {1: 0, 4: 2, 3: 4, 2: arranger.EACH_SECTION}
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
# The melody styles whose lines are their own throughout, a chorus's body included.
ENGINES_OF_THEIR_OWN = (melody_writer.SERIAL, melody_writer.EVOLVING)
# What a song chose of how its hook and its chorus's body are written, over its genre's: a behavior and gauges.
WRITING_KEPT = 'melody_writing'
# What pieces of the kit sound as, kept as the song's picks hold them, and the note a piece first plays in a General MIDI sound.
PIECE_SOUNDS_KEPT = 'piece_sounds'
PLAYER_GAUGES_KEPT = 'player_gauges'
PLAYER_ROWS_KEPT = 'player_rows'
# The answers remembered until a choice changes.
QUIET_NOTES_ANSWER = 'quiet notes'
BARS_ANSWER = 'bars offered'
# How far a sharp or a flat moves a note, in half steps.
HALF_STEPS_OF_ACCIDENTAL = {tune_notation.SHARP: 1, tune_notation.FLAT: -1}
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

# The melody styles, and the key a song keeps the one chosen under.
MELODY_STYLES = (melody_writer.SMART, melody_writer.STEP_WALK, melody_writer.SERIAL, melody_writer.EVOLVING)
# The melody styles the seven gauges steer.
GAUGED_STYLES = (melody_writer.SMART,)
# A melody style's own settings, by the style, the usual style's under None: for the evolving style how far each new line moves
# up and how many notes later it starts, each a number with its lowest and highest; for the serial style whether the row is
# all twelve notes, whether a note may leap to any octave and whether a form of the row may start anywhere in it, each true or
# false with what it is where the genre does not say. How far a tune ranges is not one: it is the Range gauge of the player.
MELODY_SETTINGS_OF = {None: (), melody_writer.STEP_WALK: (), melody_writer.SMART: (), melody_writer.EVOLVING: (melody_writer.MOVE, melody_writer.ROTATE), melody_writer.SERIAL: (melody_writer.CHROMATIC, melody_writer.LEAPS, melody_writer.ROTATIONS)}
MELODY_NUMBERS = {melody_writer.MOVE: (0, 4), melody_writer.ROTATE: (0, 4)}
MELODY_SWITCHES = {melody_writer.CHROMATIC: False, melody_writer.LEAPS: False, melody_writer.ROTATIONS: True}
EVOLVE_SETTINGS = (melody_writer.MOVE, melody_writer.ROTATE)
# The rows of numbers the serial style deals to a player's notes in turn, each with the lowest and highest number of a cell
# and what a row is where the genre gives the player none, which plays as no row would: how many steps a note lasts, how
# much louder or softer than the player a note is, and how many quarters of a note's length sound.
PLAYER_ROWS = (melody_writer.LENGTHS, melody_writer.LOUDNESS, melody_writer.ARTICULATION)
ROW_LIMITS = {melody_writer.LENGTHS: (1, 8), melody_writer.LOUDNESS: (-16, 16), melody_writer.ARTICULATION: (1, melody_writer.PARTS_OF_A_LENGTH)}
ROWS_UNASKED = {melody_writer.LENGTHS: melody_writer.DEFAULT_LENGTHS, melody_writer.LOUDNESS: (0,) * len(melody_writer.DEFAULT_LENGTHS), melody_writer.ARTICULATION: (melody_writer.PARTS_OF_A_LENGTH,) * len(melody_writer.DEFAULT_LENGTHS)}
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
MELODY_HEARD_ANSWER = 'melody values heard'
# Which take of its tune each kind of section has, kept with the song's extras, the first take being the tune the choices write;
# the seed another take is drawn from; and the key of the answer kept of a take's pattern.
TUNE_TAKES = 'tune_takes'
FIRST_TUNE_TAKE = 0
TUNE_TAKE_SEED = '{seed} {kind} tune take {take}'
# Which take each solo is, by the solo's number among the song's solos, where a solo is not the first the choices write.
SOLO_TAKES = 'solo_takes'
SOLO_TAKE_SEED = '{seed} solo {number} take {take}'
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
MELODY_CHOSEN = 'melody_chosen'
# What a person chose of the song's hooks: where the main hook sits among its section's lines, and the second hook, where it is
# sung and which take it is.
HOOKS_CHOSEN = 'hooks_chosen'
# The kinds of section a second hook may be sung in, in the order offered: at the end of the section before the chorus, in the
# section after it, and in the song's last section.
EXTRAS_OF_ONE_GENRE = (song_plan.PLAN_OF_SONG, arranger.MELODY, arranger.GROOVE, arranger.DYNAMICS, arranger.LOUDNESS, arranger.TUNE_BY, arranger.TUNE_BY_SONG, MELODY_CHOSEN, HOOKS_CHOSEN)
SETUP_BARS_ANSWER = 'setup bars'
# What a song keeps of its riffs: the riffs, each with its name, the player it was written for and how it is drawn; the riffs each
# player knows, by player; and the riff each player plays in a kind of section, by kind and player.
RIFF_BOOK = 'riffs'
# A riff the genre gave the song, which goes when another subgenre is chosen unless its notes were written by hand.
RIFF_OF_GENRE = 'of_genre'
RIFFS_KNOWN = 'riffs_known'
RIFFS_PLAYED = 'riffs_played'
# The three together, which the riffs' part of the choices holds.
RIFFS_KEPT = (RIFF_BOOK, RIFFS_KNOWN, RIFFS_PLAYED)
# What a song says of its melodies, on the Melody panel for the whole song and on a kind of section's panel for the kind: how
# busy the melodies are, how wide they range, how much they repeat and their character; and by kind of section, how high the
# kind's melody sits and how busy it is, kept as MELODY_CHOSEN.
MELODY_BUSY = 'busy'
MELODY_SPARSE = 'sparse'
MELODY_MEDIUM = 'medium'
MELODY_BUSIEST = 'busy'
MELODY_RANGE = 'range'
MELODY_NARROW = 'narrow'
MELODY_WIDE = 'wide'
MELODY_CHARACTER = 'character'
# Each field of the whole song's melodies with what may be chosen and what a song has until one is: the genre's own.
MELODY_WAYS = {MELODY_BUSY: (MELODY_SPARSE, MELODY_MEDIUM, MELODY_BUSIEST), MELODY_RANGE: (MELODY_NARROW, MELODY_MEDIUM, MELODY_WIDE), melody_writer.REPEATS: melody_writer.REPEATS_WAYS}
USUAL_MELODY_WAYS = {MELODY_BUSY: MELODY_MEDIUM, MELODY_RANGE: MELODY_MEDIUM, melody_writer.REPEATS: melody_writer.REPEATS_SOME}
# Each field of one kind of section's melody with what may be chosen; nothing chosen leaves the height to the genre and the busyness to the song.
SECTION_MELODY_WAYS = {melody_writer.HEIGHT: melody_writer.HEIGHTS, MELODY_BUSY: MELODY_WAYS[MELODY_BUSY]}
# Where on the gauges' scale a line asked to be so busy stands.
MIDDLE_GAUGE = 4
BUSY_POSITIONS = {MELODY_SPARSE: melody_writer.LOWEST_GAUGE, MELODY_MEDIUM: MIDDLE_GAUGE, MELODY_BUSIEST: melody_writer.HIGHEST_GAUGE}
# How many places of the ladder a narrow or a wide range differs from the genre's, and the least a range may be.
SPAN_CHANGES = {MELODY_NARROW: -2, MELODY_WIDE: 2}
LEAST_SPAN = 2
# A melody's character: the engine that writes it and where the smart engine's gauges stand for it, over the genre's own.
SMOOTH = 'smooth'
BLUESY = 'bluesy'
ANGULAR = 'angular'
ATONAL = 'atonal'
CHARACTER_EVOLVING = 'evolving'
CHARACTERS = (SMOOTH, BLUESY, ANGULAR, ATONAL, CHARACTER_EVOLVING)
CHARACTER_ENGINES = {SMOOTH: melody_writer.SMART, BLUESY: melody_writer.SMART, ANGULAR: melody_writer.SMART, ATONAL: melody_writer.SERIAL, CHARACTER_EVOLVING: melody_writer.EVOLVING}
CHARACTER_GAUGES = {SMOOTH: {melody_writer.GAUGE_MOVES: 1, melody_writer.GAUGE_AFTER_LEAP: 1, melody_writer.GAUGE_PHRASE: 7, melody_writer.GAUGE_SURPRISE: 1}, ANGULAR: {melody_writer.GAUGE_MOVES: 7, melody_writer.GAUGE_AFTER_LEAP: 6, melody_writer.GAUGE_PHRASE: 2, melody_writer.GAUGE_SURPRISE: 6},
                    BLUESY: {melody_writer.GAUGE_STEPS: 2, melody_writer.GAUGE_LEANING: 6}}
# The degrees a bluesy melody is drawn from, the third and the seventh flattened over a scale that has them major, and its home.
BLUES_DEGREES = (1, 3, 4, 5, 7)
BLUES_HOME = 1

# What a player plays in a kind of section besides a riff: what the genre writes for the player, nothing, or the melody.
ACCOMPANIMENT = 'accompaniment'
RESTS_PART = 'rests'
MELODY_PART = 'melody'
# The name of the riff asked for to find who can play one in a kind of section.
TRIAL_RIFF = 'trial riff'
# A riff's settings, each with what may be chosen, the first what a riff has until another is chosen.
RIFF_SETTINGS = {riffs_values.RIFF_NOTES: riffs_values.NOTES_WAYS, riffs_values.RIFF_BAR_COUNT: tuple(reversed(riffs_values.BAR_COUNTS)), riffs_values.RIFF_BETWEEN: riffs_values.BETWEEN_WAYS, riffs_values.RIFF_UNDER_TUNE: riffs_values.UNDER_TUNE_WAYS, riffs_values.RIFF_WITH_CHORDS: riffs_values.WITH_CHORDS_WAYS}
assert (RIFF_SETTINGS[riffs_values.RIFF_NOTES][0], RIFF_SETTINGS[riffs_values.RIFF_BAR_COUNT][0], RIFF_SETTINGS[riffs_values.RIFF_BETWEEN][0]) == (riffs_values.SINGLE_NOTES, riffs_values.RIFF_BARS, riffs_values.MUTED_ROOTS)
assert (RIFF_SETTINGS[riffs_values.RIFF_UNDER_TUNE][0], RIFF_SETTINGS[riffs_values.RIFF_WITH_CHORDS][0]) == (riffs_values.IN_FULL, riffs_values.MOVES_WHOLE)
# The settings a new riff is asked for.
NEW_RIFF_SETTINGS = (riffs_values.RIFF_BAR_COUNT, riffs_values.RIFF_NOTES, riffs_values.RIFF_WITH_CHORDS, riffs_values.RIFF_BETWEEN)
INTRO_KIND = 'intro'
REACTS_ANSWER = 'reacts'
DYNAMICS_ANSWER = 'dynamics'
# The swings a song may be played with, the lightest first of those of the eighths and then of the sixteenths, and the steps of
# a bar a genre written in triplets counts, which is swung as written and takes none.
SWINGS = (arranger.NO_GROOVE, FactoryGroove.EIGHTH_SWING_58, FactoryGroove.EIGHTH_SWING_66, FactoryGroove.SWING_54, FactoryGroove.SWING_58, FactoryGroove.SWING_62, FactoryGroove.SWING_66)
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
OWN_WITHOUT_PLAN = (arranger.CHORDS, song_plan.TEMPO_OF_PLACE, song_plan.TEMPO_END_OF_PLACE, song_plan.ROOT_OF_PLACE, song_plan.TYPE_OF_PLACE)
# What a section that opens or closes the song says of its fade, with or without a plan.
FADE_OWN = (song_plan.FADES, song_plan.FADE_LEVEL, song_plan.FADE_OVER)
# The way a section fades: a section that opens the song fades in, one that closes the song fades out, and no other fades.
FADE_IN = 'in'
FADE_OUT = 'out'
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
SECOND_HOOK_KINDS = (SectionKind.PRE_CHORUS, SectionKind.POST_CHORUS, OUTRO_KIND)
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
    LEAVES_SMALL_FILL: {song_plan.FILL_SIZE: song_plan.SMALL}, LEAVES_MEDIUM_FILL: {song_plan.FILL_SIZE: song_plan.MEDIUM}, LEAVES_BIG_FILL: {song_plan.FILL_SIZE: song_plan.BIG},
    joins_values.STOPS: {joins_values.TAIL: joins_values.STOPS}, joins_values.DROP_OUT: {joins_values.TAIL: joins_values.DROP_OUT}, joins_values.BUILD: {joins_values.TAIL: joins_values.BUILD}, LEAVES_NOTHING: {},
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
MARKS_TYPED = {'b': tune_notation.FLAT, '#': tune_notation.SHARP}
FIRST_DEGREE_OF_SCALE = 1
LAST_DEGREE_OF_SCALE = 7
# The parts of a hook's kind and what each may be.
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

# Two chords typed with a dash between share a bar.
SHARES_A_BAR = '-'
CHORDS_IN_A_SHARED_BAR = 2

# A tempo counts quarter notes a minute.
QUARTERS_IN_WHOLE = 4
SECONDS_IN_MINUTE = 60
