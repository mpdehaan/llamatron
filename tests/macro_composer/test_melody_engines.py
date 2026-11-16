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

"""The melody engines: the row operations, the serial engine's row, forms, lengths and voices, and which engine a song's tune
is made by."""

import unittest

from llamatron.macro_composer import arranger, composer, melody, notation, operations
from llamatron.strings.errors import ERR_MELODY_NEEDS_RHYTHMS

MINOR = 'minor'
SEED = 9
OTHER_SEED = 10
GRID = 8
LINE_BARS = 2
# C E D G B A F as places in the notes of C major, and that row upside down and backwards.
ROW = [0, 2, 1, 4, 6, 5, 3]
ROW_UPSIDE_DOWN = [0, 5, 6, 3, 1, 2, 4]
ROW_BACKWARDS = [3, 5, 6, 4, 1, 2, 0]
ROW_MOVED_UP_TWO = [2, 4, 3, 6, 1, 0, 5]
ROW_BEGUN_TWO_LATER = [1, 4, 6, 5, 3, 0, 2]
NOTES_IN_SCALE = 7
NOTES_IN_OCTAVE = 12
CHORDS = [{notation.DEGREE: 1}]
HABITS = {
    melody.GRID: GRID, melody.LINE_BARS: LINE_BARS, melody.SPAN: 4, melody.HOME: {notation.DEGREE: 1},
    melody.LADDER: [{notation.DEGREE: degree} for degree in range(1, NOTES_IN_SCALE + 1)], melody.RHYTHMS: [], melody.ANSWER_RHYTHMS: [],
    melody.LENGTHS: [1, 1, 2, 1, 3, 2, 1],
}
# Three lines nobody has heard, then the first again, then the first varied.
PLAN = [{melody.LINE: 'a'}, {melody.LINE: 'b'}, {melody.LINE: 'c'}, {melody.LINE: 'a'}, {melody.LINE: 'a', melody.VARIED: True}]
NEW_LINES = 3
HIGH = 'high'
PENTATONIC = [{notation.DEGREE: degree} for degree in (1, 2, 3, 5, 6)]
# A line of two bars: a rest, six notes and a long last one.
RHYTHM = [{notation.REST: 2}, {notation.STEPS: 2}, {notation.STEPS: 2}, {notation.STEPS: 1}, {notation.STEPS: 1}, {notation.STEPS: 2}, {notation.STEPS: 2}, {notation.STEPS: 4}]
FAR = 5
LOUDNESS = [-12, 0, 8, -4, 16]
# Parts in four of each note's length that sound.
ARTICULATION = [4, 2, 1, 3]
VELOCITY = 80
CHORDS_VOICE = 'chords'
TOGETHER = 3
LOW = 'low'
ROCK = 'rock'
EXPERIMENTAL = 'experimental'
LEAD = 'lead'
THREE = 'three'
VERSE = 'verse'
BRITISH_INVASION = 'british invasion'
SERIAL_TRIO = 'serial trio'
CHORUS = 'chorus'
COMMON_TIME = '4/4'
# What the smart engine is measured over: a tendency is a matter of many tunes, never of one.
SEEDS = range(1, 41)
HALF = 0.5
SMART_CHORDS = [{notation.DEGREE: 1}, {notation.DEGREE: 4}, {notation.DEGREE: 5}, {notation.DEGREE: 1}]
LETTERS = 'abcd'
SONG_PLAN = [{melody.LINE: 'a'}, {melody.LINE: 'b'}, {melody.LINE: 'a', melody.VARIED: True}, {melody.LINE: 'c'}]
CHORUS_PLAN = [{melody.LINE: 'hook', melody.HOOK: True, melody.HIGHER: True}, {melody.LINE: 'hook', melody.HOOK: True, melody.HIGHER: True, melody.VARIED: True},
               {melody.LINE: 'hook', melody.HOOK: True, melody.HIGHER: True}, {melody.LINE: 'close'}]
FIRST_HOOK_SEED = 1
MOST_PITCHES_IN_A_FIGURE = 4
HEAD_UNITS = 4
HOOK_PLAN = [{melody.LINE: 'hook', melody.HIGHER: True}, {melody.LINE: 'hook', melody.HIGHER: True, melody.VARIED: True}, {melody.LINE: 'hook', melody.HIGHER: True}]


def pitch_of(note):
    """A note without its octave or its length: which note of the row it is."""
    return (note[notation.DEGREE], note.get(notation.ACCIDENTAL))


def rhythm_of(line):
    """A line's rests and lengths, without its notes."""
    return [(notation.REST in note, note.get(notation.STEPS, note.get(notation.REST))) for note in line]


def starts_of(line):
    """The steps at which a line's notes begin."""
    starts = []
    at = 0
    for note in line:
        if notation.REST not in note:
            starts.append(at)
        at += note.get(notation.STEPS, note.get(notation.REST))
    return starts


def serial(*, seed=SEED, voice=None, **habits):
    return melody.Serial(habits={**HABITS, **habits}, chords=CHORDS, scale_type=MINOR, seed=seed, answers=False, voice=voice)


class TestRowOperations(unittest.TestCase):

    def test_a_row_backwards_upside_down_moved_and_begun_later(self):
        self.assertEqual(operations.backwards(ROW), ROW_BACKWARDS)
        self.assertEqual(operations.upside_down(row=ROW, size=NOTES_IN_SCALE), ROW_UPSIDE_DOWN)
        self.assertEqual(operations.moved(row=ROW, by=2, size=NOTES_IN_SCALE), ROW_MOVED_UP_TWO)
        self.assertEqual(operations.rotated(row=ROW, by=2), ROW_BEGUN_TWO_LATER)

    def test_every_operation_keeps_every_note_once_and_leaves_the_row_alone(self):
        kept = list(ROW)
        for made in (operations.backwards(ROW), operations.upside_down(row=ROW, size=NOTES_IN_SCALE), operations.moved(row=ROW, by=3, size=NOTES_IN_SCALE),
                     operations.rotated(row=ROW, by=3)):
            self.assertEqual(sorted(made), sorted(ROW))
        self.assertEqual(ROW, kept)

    def test_upside_down_twice_and_backwards_twice_are_the_row(self):
        self.assertEqual(operations.upside_down(row=operations.upside_down(row=ROW, size=NOTES_IN_SCALE), size=NOTES_IN_SCALE), ROW)
        self.assertEqual(operations.backwards(operations.backwards(ROW)), ROW)


class TestSerial(unittest.TestCase):

    def sounds(self, lines):
        return [note for line in lines for note in line if notation.REST not in note]

    def test_the_row_is_every_note_of_the_scale_once_and_all_twelve_when_chromatic(self):
        self.assertEqual(sorted(serial().row()), list(range(NOTES_IN_SCALE)))
        self.assertEqual(sorted(serial(**{melody.CHROMATIC: True}).row()), list(range(NOTES_IN_OCTAVE)))
        self.assertEqual(len({pitch_of(note) for note in melody.twelve_notes(MINOR)}), NOTES_IN_OCTAVE)

    def test_no_note_returns_until_the_others_have_sounded(self):
        for habits in ({}, {melody.CHROMATIC: True}, {melody.LEAPS: True}):
            engine = serial(**habits)
            size = len(engine.row())
            heard = [pitch_of(note) for note in self.sounds(engine.sketched(PLAN[:NEW_LINES]))]
            for start in range(0, len(heard) - size + 1, size):
                with self.subTest(habits=habits, start=start):
                    self.assertEqual(len(set(heard[start:start + size])), size)

    def test_a_form_begins_beside_the_note_the_form_before_ended_on(self):
        engine = serial()
        notes = engine.notes()
        places = [next(place for place, note in enumerate(notes) if pitch_of(note) == pitch) for pitch in
                  (pitch_of(note) for note in self.sounds(engine.sketched(PLAN[:NEW_LINES])))]
        for start in range(NOTES_IN_SCALE, len(places), NOTES_IN_SCALE):
            self.assertIn((places[start] - places[start - 1]) % NOTES_IN_SCALE, (1, NOTES_IN_SCALE - 1))

    def test_every_line_fills_its_bars_and_a_line_named_again_returns(self):
        lines = serial().sketched(PLAN)
        for line in lines:
            self.assertEqual(sum(note[notation.STEPS] for note in line), GRID * LINE_BARS)
        self.assertEqual(lines[3], lines[0])

    def test_a_varied_line_is_the_lines_notes_backwards_in_its_own_rhythm(self):
        lines = serial().sketched(PLAN)
        first, varied = lines[0], lines[4]
        self.assertEqual([note[notation.STEPS] for note in varied], [note[notation.STEPS] for note in first])
        self.assertEqual([pitch_of(note) for note in varied], [pitch_of(note) for note in reversed(first)])

    def test_the_lengths_are_a_row_read_forwards_and_then_backwards(self):
        engine = serial()
        count = len(HABITS[melody.LENGTHS])
        lengths = [engine.next_length() for _ in range(count * 2)]
        self.assertEqual(sorted(lengths[:count]), sorted(HABITS[melody.LENGTHS]))
        self.assertEqual(lengths[count:], list(reversed(lengths[:count])))

    def test_the_same_seed_gives_the_same_tune_and_another_seed_another_row(self):
        self.assertEqual(serial().sketched(PLAN), serial().sketched(PLAN))
        self.assertNotEqual(serial().row(), serial(seed=OTHER_SEED).row())

    def test_two_voices_share_the_row_and_read_it_differently(self):
        high, low = serial(voice=HIGH), serial(voice=LOW)
        self.assertEqual(high.row(), low.row())
        self.assertNotEqual(high.sketched(PLAN), low.sketched(PLAN))

    def test_with_leaps_a_note_may_take_any_octave_in_range_and_without_it_takes_the_nearest(self):
        near = self.sounds(serial().sketched(PLAN[:NEW_LINES]))
        thrown = self.sounds(serial(**{melody.LEAPS: True}).sketched(PLAN[:NEW_LINES]))
        self.assertEqual([pitch_of(note) for note in near][:NOTES_IN_SCALE], [pitch_of(note) for note in thrown][:NOTES_IN_SCALE])
        self.assertNotEqual([note.get(notation.OCTAVE, 0) for note in near], [note.get(notation.OCTAVE, 0) for note in thrown])


class TestSerialRows(unittest.TestCase):
    """What the serial engine does with a row besides its four forms: rotation, loudness, articulation and chords."""

    def sounds(self, lines):
        return [note for line in lines for note in line if notation.REST not in note]

    def test_a_form_may_begin_anywhere_in_the_row_and_without_rotations_begins_at_an_end(self):
        row = serial(**{melody.ROTATIONS: False}).row()
        forms = {tuple(form(row=row, size=NOTES_IN_SCALE)) for form in melody.FORMS}
        for rotations, every_form_is_one_of_the_four in ((False, True), (True, False)):
            heard = self.sounds(serial(**{melody.ROTATIONS: rotations}).sketched(PLAN[:NEW_LINES]))
            notes = serial().notes()
            places = [next(place for place, note in enumerate(notes) if pitch_of(note) == pitch_of(sound)) for sound in heard]
            groups = [places[start:start + NOTES_IN_SCALE] for start in range(0, len(places) - NOTES_IN_SCALE + 1, NOTES_IN_SCALE)]
            unmoved = [tuple(operations.moved(row=group, by=by, size=NOTES_IN_SCALE)) for group in groups for by in range(NOTES_IN_SCALE)]
            found = [any(candidate in forms for candidate in unmoved[count * NOTES_IN_SCALE:(count + 1) * NOTES_IN_SCALE]) for count in range(len(groups))]
            with self.subTest(rotations=rotations):
                self.assertEqual(all(found), every_form_is_one_of_the_four)

    def test_a_row_of_loudness_is_read_forwards_and_then_backwards_and_changes_how_loud_each_note_is(self):
        heard = self.sounds(serial(**{melody.LOUDNESS: LOUDNESS}).sketched(PLAN[:NEW_LINES]))
        count = len(LOUDNESS)
        self.assertEqual([note[notation.LOUDER] for note in heard[:count * 2]], LOUDNESS + list(reversed(LOUDNESS)))
        self.assertNotIn(notation.LOUDER, self.sounds(serial().sketched(PLAN[:NEW_LINES]))[0])
        rows = notation.tune_rows(lines=[[{notation.DEGREE: 1, notation.STEPS: 1, notation.LOUDER: LOUDNESS[0]}, {notation.DEGREE: 2, notation.STEPS: 1}]],
                                  octave=4, velocity=VELOCITY, step_size=notation.DEFAULT_STEP_SIZE)
        self.assertEqual(rows[notation.VELOCITY], [VELOCITY + LOUDNESS[0], VELOCITY])

    def test_a_row_of_articulation_cuts_notes_short_and_leaves_every_note_where_it_was(self):
        plain = serial().sketched(PLAN[:NEW_LINES])
        cut = serial(**{melody.ARTICULATION: ARTICULATION}).sketched(PLAN[:NEW_LINES])
        self.assertEqual([pitch_of(note) for note in self.sounds(cut)], [pitch_of(note) for note in self.sounds(plain)])
        for whole, short in zip(plain, cut):
            self.assertEqual(starts_of(short), starts_of(whole))
            self.assertEqual(sum(note.get(notation.STEPS, note.get(notation.REST)) for note in short), GRID * LINE_BARS)
        self.assertTrue(any(notation.REST in note for line in cut for note in line))
        self.assertTrue(all(note[notation.STEPS] >= 1 for note in self.sounds(cut)))

    def test_voices_of_one_name_that_each_take_one_of_three_notes_play_chords_of_the_rows_neighbours(self):
        parts = [self.sounds(serial(voice=CHORDS_VOICE, **{melody.TOGETHER: TOGETHER, melody.TAKES: takes}).sketched(PLAN[:NEW_LINES])) for takes in range(TOGETHER)]
        alone = self.sounds(serial(voice=CHORDS_VOICE).sketched(PLAN[:NEW_LINES]))
        self.assertEqual([note[notation.STEPS] for note in parts[0]], [note[notation.STEPS] for note in parts[1]])
        self.assertEqual(len({pitch_of(note) for note in next(zip(*parts))}), TOGETHER)
        for count, chord in enumerate(zip(*parts)):
            # A chord that reaches from the end of one form into the next may hold one note twice.
            self.assertGreaterEqual(len({pitch_of(note) for note in chord}), TOGETHER - 1)
            if (count + 1) * TOGETHER <= len(alone):
                self.assertEqual([pitch_of(note) for note in chord], [pitch_of(note) for note in alone[count * TOGETHER:(count + 1) * TOGETHER]])


class TestEvolving(unittest.TestCase):
    """Repeats that evolve: one phrase, and a running amount added with every new line."""

    def engine(self, **evolve):
        habits = {**HABITS, melody.LADDER: PENTATONIC, melody.RHYTHMS: [RHYTHM], melody.ANSWER_RHYTHMS: [RHYTHM], melody.EVOLVE: evolve}
        return melody.Evolving(habits=habits, chords=CHORDS, scale_type=MINOR, seed=SEED, answers=False)

    def places(self, *, engine, line):
        return [engine.place_of(note) for note in line if notation.REST not in note]

    def test_every_new_line_is_the_first_phrase_moved_one_more_place_in_the_same_rhythm(self):
        engine = self.engine(**{melody.MOVE: 1})
        lines = engine.sketched(PLAN[:NEW_LINES])
        first = self.places(engine=engine, line=lines[0])
        for count, line in enumerate(lines):
            self.assertEqual(rhythm_of(line), rhythm_of(lines[0]))
            self.assertEqual(self.places(engine=engine, line=line), [engine.round_the_range(place + count) for place in first])

    def test_a_note_moved_past_the_top_of_the_range_comes_round_to_the_bottom(self):
        engine = self.engine(**{melody.MOVE: FAR})
        lines = engine.sketched(PLAN[:NEW_LINES])
        first = self.places(engine=engine, line=lines[0])
        reach = max(HABITS[melody.SPAN] * 2, max(first) - min(first))
        for line in lines:
            places = self.places(engine=engine, line=line)
            self.assertLessEqual(max(places) - min(places), reach + 1)
            self.assertEqual(places, [engine.round_the_range(place) for place in places])
        self.assertTrue(any(later < earlier for earlier, later in zip(first, self.places(engine=engine, line=lines[1]))))

    def test_a_phrase_begun_later_keeps_its_notes_and_its_rhythm(self):
        engine = self.engine(**{melody.MOVE: 0, melody.ROTATE: 1})
        lines = engine.sketched(PLAN[:NEW_LINES])
        first = self.places(engine=engine, line=lines[0])
        self.assertEqual(self.places(engine=engine, line=lines[1]), operations.rotated(row=first, by=1))
        self.assertEqual(self.places(engine=engine, line=lines[2]), operations.rotated(row=first, by=2))

    def test_a_line_named_again_returns_and_a_varied_line_begins_one_note_later(self):
        engine = self.engine(**{melody.MOVE: 1})
        lines = engine.sketched(PLAN)
        self.assertEqual(lines[3], lines[0])
        self.assertEqual(self.places(engine=engine, line=lines[4]), operations.rotated(row=self.places(engine=engine, line=lines[0]), by=1))


def smart_habits(**gauges):
    """A real style's habits with the smart engine's gauges set, the others where they stand until a style says."""
    style = arranger.style_named(ROCK)
    return {**style[arranger.MELODY][COMMON_TIME], melody.SMART: {**melody.DEFAULT_GAUGES, **gauges}}


def smart_lines(*, seed, habits=None, plan=None, letters=()):
    return melody.sketched(habits=habits or smart_habits(), plan=plan or SONG_PLAN, chords=SMART_CHORDS, scale_type=melody.MAJOR, seed=seed, answers=False,
                           engine=melody.SMART, letters=letters)


def places_of(*, line, habits):
    """The places on the ladder of a line's notes."""
    ladder = melody.ladder_of(notes=habits[melody.LADDER], scale_type=melody.MAJOR)
    rungs = [rung for _, rung in ladder]
    return [rungs.index({field: note[field] for field in melody.PITCH_FIELDS if field in note}) for note in line if notation.REST not in note]


def moves_of(*, lines, habits):
    """Every move from one note to the next inside each line."""
    moves = []
    for line in lines:
        places = places_of(line=line, habits=habits)
        moves += [after - before for before, after in zip(places, places[1:])]
    return moves


def share(*, of, among):
    return len(of) / max(1, len(among))


def hooks_song(seed, *, writer=melody.SMART):
    """A verse and a chorus of one song with a hook, its other lines by the writer named, and the habits they were made by."""
    habits = smart_habits()
    letters = [entry[melody.LINE] for entry in SONG_PLAN + CHORUS_PLAN]
    made = [melody.sketched(habits=habits, plan=plan, chords=SMART_CHORDS, scale_type=melody.MAJOR, seed=seed, answers=False, engine=writer, letters=letters, hook=True) for plan in (SONG_PLAN, CHORUS_PLAN)]
    return made[0], made[1], habits


def first_bar(*, line, grid):
    """The notes of a line that fill its first bar."""
    notes = []
    for note in line:
        if sum(length for _, length in rhythm_of(notes)) == grid:
            break
        notes.append(note)
    return notes


class TestHooks(unittest.TestCase):
    """What makes a hook, held on every seed: a figure of one bar that returns the same, whose long last note is the top of the song."""

    def test_a_hook_is_a_bar_of_few_short_notes_and_one_long_note_and_returns_the_same(self):
        for seed in SEEDS:
            _, chorus, habits = hooks_song(seed)
            grid = habits[melody.GRID]
            figure = first_bar(line=chorus[0], grid=grid)
            self.assertLessEqual(len(figure), melody.MOST_SHORT_NOTES + 1)
            self.assertGreaterEqual(figure[-1][notation.STEPS] * 2, grid)
            self.assertEqual(chorus[0], chorus[2])
            self.assertEqual(first_bar(line=chorus[1], grid=grid), figure)

    def test_the_hooks_long_note_is_the_top_of_the_song_and_on_the_chord(self):
        for seed in SEEDS:
            verse, chorus, habits = hooks_song(seed)
            grid = habits[melody.GRID]
            figure = places_of(line=first_bar(line=chorus[0], grid=grid), habits=habits)
            peak = figure[-1]
            self.assertEqual(peak, max(place for line in chorus[:1] for place in places_of(line=line, habits=habits)))
            self.assertLess(max(place for line in verse for place in places_of(line=line, habits=habits)), peak)
            ladder = melody.ladder_of(notes=habits[melody.LADDER], scale_type=melody.MAJOR)
            self.assertIn(ladder[peak][0] % melody.NOTES_IN_OCTAVE, melody.chord_notes(chord=SMART_CHORDS[0], scale_type=melody.MAJOR))

    def test_a_varied_hook_changes_only_its_last_note_which_ends_no_lower_than_the_peak(self):
        for seed in SEEDS:
            _, chorus, habits = hooks_song(seed)
            self.assertEqual(rhythm_of(chorus[1]), rhythm_of(chorus[0]))
            first = places_of(line=chorus[0], habits=habits)
            varied = places_of(line=chorus[1], habits=habits)
            self.assertEqual(varied[:-1], first[:-1])
            self.assertGreaterEqual(varied[-1], max(first))

    def test_a_hooks_figure_has_few_pitches(self):
        for seed in SEEDS:
            _, chorus, habits = hooks_song(seed)
            figure = first_bar(line=chorus[0], grid=habits[melody.GRID])
            self.assertLessEqual(len(set(places_of(line=figure, habits=habits))), MOST_PITCHES_IN_A_FIGURE)

    def test_the_hook_is_the_same_whoever_writes_the_other_lines_but_for_what_the_gauges_seed(self):
        for writer in melody.ENGINES:
            for seed in SEEDS:
                _, chorus, habits = hooks_song(seed, writer=writer)
                grid = habits[melody.GRID]
                figure = first_bar(line=chorus[0], grid=grid)
                self.assertLessEqual(len(figure), melody.MOST_SHORT_NOTES + 1, writer)
                self.assertGreaterEqual(figure[-1][notation.STEPS] * 2, grid, writer)
                self.assertEqual(chorus[0], chorus[2], writer)

    def test_without_a_hook_the_writer_writes_alone_and_with_one_keeps_under_it_in_every_section(self):
        letters = [entry[melody.LINE] for entry in SONG_PLAN + CHORUS_PLAN]
        for writer in melody.ENGINES:
            given = dict(habits=smart_habits(), chords=SMART_CHORDS, scale_type=melody.MAJOR, seed=FIRST_HOOK_SEED, answers=False, engine=writer, letters=letters)
            alone = melody.sketched(plan=CHORUS_PLAN, **given)
            self.assertEqual(melody.sketched(plan=CHORUS_PLAN, hook=False, **given), alone)
            self.assertNotEqual(melody.sketched(plan=CHORUS_PLAN, hook=True, **given), alone, writer)
        self.assertFalse(melody.has_hook(SONG_PLAN))
        self.assertTrue(melody.has_hook(CHORUS_PLAN))

    def test_the_same_seed_makes_the_same_hook_and_another_seed_another(self):
        self.assertEqual(hooks_song(FIRST_HOOK_SEED)[1], hooks_song(FIRST_HOOK_SEED)[1])
        self.assertGreater(len({str(hooks_song(seed)[1][0]) for seed in SEEDS}), len(SEEDS) // 2)

    def test_the_figures_of_short_notes_fill_their_units_with_two_to_four_notes(self):
        figures = melody.short_note_figures(HEAD_UNITS)
        self.assertIn((1, 1, 2), figures)
        self.assertTrue(all(sum(figure) == HEAD_UNITS and melody.FEWEST_SHORT_NOTES <= len(figure) <= melody.MOST_SHORT_NOTES for figure in figures))
        self.assertEqual(len(figures), len(set(figures)))


class TestSmart(unittest.TestCase):
    """The smart engine's tendencies and gauges, each measured over many seeds, since one tune proves nothing of a tendency."""

    def moves(self, **gauges):
        habits = smart_habits(**gauges)
        return [move for seed in SEEDS for move in moves_of(lines=smart_lines(seed=seed, habits=habits), habits=habits)]

    def test_most_moves_are_steps_and_steps_mostly_fall_and_leaps_mostly_rise(self):
        moves = self.moves()
        steps = [move for move in moves if abs(move) == melody.STEP_SIZE]
        leaps = [move for move in moves if abs(move) > melody.STEP_SIZE]
        self.assertGreater(len(steps), len(moves) / 2)
        self.assertGreater(len(steps), 2 * len(leaps))
        self.assertGreater(share(of=[move for move in steps if move < 0], among=steps), HALF)
        self.assertGreater(share(of=[move for move in leaps if move > 0], among=leaps), HALF)

    def test_the_moves_gauge_brings_leaps(self):
        few = self.moves(**{melody.GAUGE_MOVES: melody.LOWEST_GAUGE})
        many = self.moves(**{melody.GAUGE_MOVES: melody.HIGHEST_GAUGE})
        leaps = lambda moves: share(of=[move for move in moves if abs(move) > melody.STEP_SIZE], among=moves)
        self.assertGreater(leaps(many), 2 * leaps(few))

    def test_the_steps_gauge_turns_steps_from_falling_to_rising(self):
        rising = lambda moves: share(of=[move for move in moves if move == melody.STEP_SIZE], among=[move for move in moves if abs(move) == melody.STEP_SIZE])
        self.assertLess(rising(self.moves(**{melody.GAUGE_STEPS: melody.LOWEST_GAUGE})), HALF)
        self.assertGreater(rising(self.moves(**{melody.GAUGE_STEPS: melody.HIGHEST_GAUGE})), HALF)

    def after_leaps(self, position):
        """The share of moves after a leap that come back the other way."""
        habits = smart_habits(**{melody.GAUGE_AFTER_LEAP: position, melody.GAUGE_MOVES: melody.HIGHEST_GAUGE, melody.GAUGE_PHRASE: melody.LOWEST_GAUGE})
        back = []
        for seed in SEEDS:
            for line in smart_lines(seed=seed, habits=habits):
                places = places_of(line=line, habits=habits)
                moves = [after - before for before, after in zip(places, places[1:])]
                back += [(after > 0) != (before > 0) for before, after in zip(moves, moves[1:]) if abs(before) > melody.STEP_SIZE and after]
        return share(of=[came for came in back if came], among=back)

    def test_the_after_leap_gauge_says_whether_a_leap_is_followed_back(self):
        self.assertGreater(self.after_leaps(melody.LOWEST_GAUGE), self.after_leaps(melody.HIGHEST_GAUGE))
        self.assertGreater(self.after_leaps(melody.LOWEST_GAUGE), HALF)

    def reach(self, position):
        """How far, on average, a line's highest note stands above its first and last."""
        habits = smart_habits(**{melody.GAUGE_PHRASE: position})
        heights = []
        for seed in SEEDS:
            for line in smart_lines(seed=seed, habits=habits, plan=[{melody.LINE: letter} for letter in LETTERS]):
                places = places_of(line=line, habits=habits)
                heights.append(max(places) - (places[0] + places[-1]) / 2)
        return sum(heights) / len(heights)

    def test_the_phrase_gauge_arches_a_line(self):
        self.assertGreater(self.reach(melody.HIGHEST_GAUGE), self.reach(melody.LOWEST_GAUGE))

    def off_the_chord(self, position):
        """The share of lines that end on a note the chord under them does not hold."""
        habits = smart_habits(**{melody.GAUGE_LEANING: position})
        wanted = melody.chord_notes(chord=SMART_CHORDS[0], scale_type=melody.MAJOR)
        ends = []
        for seed in SEEDS:
            for line in smart_lines(seed=seed, habits=habits):
                last = [note for note in line if notation.REST not in note][-1]
                ends.append(melody.half_steps_of(note=last, scale_type=melody.MAJOR) % NOTES_IN_OCTAVE not in wanted)
        return share(of=[hangs for hangs in ends if hangs], among=ends)

    def test_the_leaning_gauge_leaves_a_lines_last_note_hanging(self):
        self.assertGreater(self.off_the_chord(melody.HIGHEST_GAUGE), self.off_the_chord(melody.LOWEST_GAUGE))

    def notes_in_a_line(self, position):
        habits = smart_habits(**{melody.GAUGE_NOTES: position})
        counts = [len(places_of(line=line, habits=habits)) for seed in SEEDS for line in smart_lines(seed=seed, habits=habits)]
        return sum(counts) / len(counts)

    def test_the_notes_gauge_goes_from_long_notes_to_short(self):
        self.assertGreater(self.notes_in_a_line(melody.HIGHEST_GAUGE), self.notes_in_a_line(melody.LOWEST_GAUGE))

    def test_the_surprise_gauge_breaks_the_tendencies(self):
        expected = self.moves(**{melody.GAUGE_SURPRISE: melody.LOWEST_GAUGE})
        surprising = self.moves(**{melody.GAUGE_SURPRISE: melody.HIGHEST_GAUGE})
        leaps = lambda moves: share(of=[move for move in moves if abs(move) > melody.STEP_SIZE], among=moves)
        self.assertGreater(leaps(surprising), leaps(expected))

    def test_a_chorus_is_unlike_its_verse_in_rhythm_and_higher_in_every_style_with_both(self):
        for name in arranger.style_names():
            style = arranger.style_named(name)
            sections = style[arranger.SECTIONS]
            if not sections.get(VERSE, {}).get(arranger.PLAN) or not sections.get(CHORUS, {}).get(arranger.PLAN):
                continue
            habits = style[arranger.MELODY] if melody.GRID in style[arranger.MELODY] else style[arranger.MELODY][COMMON_TIME]
            if not habits[melody.RHYTHMS]:
                continue
            letters = arranger.line_letters(plans=[sections[VERSE][arranger.PLAN], sections[CHORUS][arranger.PLAN]], answers=False)
            higher = any(entry.get(melody.HIGHER) for entry in sections[CHORUS][arranger.PLAN])
            verse_heights = []
            chorus_heights = []
            for seed in SEEDS:
                verse = smart_lines(seed=seed, habits=habits, plan=sections[VERSE][arranger.PLAN], letters=letters)
                chorus = smart_lines(seed=seed, habits=habits, plan=sections[CHORUS][arranger.PLAN], letters=letters)
                with self.subTest(style=name, seed=seed):
                    self.assertNotIn(rhythm_of(chorus[0]), [rhythm_of(line) for line in verse])
                verse_heights += [place for line in verse for place in places_of(line=line, habits=habits)]
                chorus_heights += [place for line in chorus for place in places_of(line=line, habits=habits)]
            if higher:
                with self.subTest(style=name):
                    self.assertGreater(sum(chorus_heights) / len(chorus_heights), sum(verse_heights) / len(verse_heights))

    def test_a_hook_returns_note_for_note_and_varied_keeps_its_head_and_its_rhythm(self):
        habits = smart_habits()
        for seed in SEEDS:
            hook, varied, again = smart_lines(seed=seed, habits=habits, plan=HOOK_PLAN)
            head = len(places_of(line=hook, habits=habits)) // 2
            self.assertEqual(again, hook)
            self.assertEqual(rhythm_of(varied), rhythm_of(hook))
            self.assertEqual(places_of(line=varied, habits=habits)[:head], places_of(line=hook, habits=habits)[:head])

    def test_every_line_fills_its_bars_and_stays_in_range_and_the_same_seed_gives_the_same_tune(self):
        habits = smart_habits()
        home = melody.home_place(ladder=melody.ladder_of(notes=habits[melody.LADDER], scale_type=melody.MAJOR), home=habits[melody.HOME])
        for seed in SEEDS:
            lines = smart_lines(seed=seed, habits=habits)
            self.assertEqual(lines, smart_lines(seed=seed, habits=habits))
            for line in lines:
                self.assertEqual(sum(note.get(notation.REST, note.get(notation.STEPS)) for note in line), habits[melody.GRID] * habits[melody.LINE_BARS])
                for place in places_of(line=line, habits=habits):
                    self.assertLessEqual(abs(place - home), habits[melody.SPAN])
        self.assertNotEqual(smart_lines(seed=SEED), smart_lines(seed=OTHER_SEED))

    def test_a_style_with_no_rhythms_is_refused(self):
        with self.assertRaises(ValueError) as refused:
            melody.sketched(habits=HABITS, plan=PLAN, chords=CHORDS, scale_type=melody.MAJOR, seed=SEED, answers=False, engine=melody.SMART)
        self.assertEqual(str(refused.exception), ERR_MELODY_NEEDS_RHYTHMS)


class TestEngineChosen(unittest.TestCase):

    def lead(self, song):
        made = arranger.arranged(style=arranger.style_named(song[arranger.STYLE]), song=song)
        return [part for name, part in made[composer.PARTS].items() if notation.LINES in part and name.endswith(LEAD)]

    def song(self, **more):
        return {arranger.NAME: 'a_song', arranger.TITLE: 'A song', arranger.STYLE: ROCK, arranger.TEMPLATE: BRITISH_INVASION, arranger.KEY: {arranger.ROOT: 'D'},
                arranger.SEED: SEED, arranger.FORM: [VERSE], **more}

    def test_a_song_picks_the_engine_its_tunes_are_made_by_and_the_step_walk_is_usual(self):
        usual = self.lead(self.song())
        self.assertEqual(usual, self.lead(self.song(**{arranger.MELODY_ENGINE: melody.STEP_WALK})))
        self.assertNotEqual(usual, self.lead(self.song(**{arranger.MELODY_ENGINE: melody.SERIAL})))

    def test_a_style_may_name_its_engine_and_every_voice_plays_the_row(self):
        style = arranger.style_named(EXPERIMENTAL)
        song = {**self.song(), arranger.STYLE: EXPERIMENTAL, arranger.TEMPLATE: SERIAL_TRIO, arranger.FORM: [THREE]}
        made = arranger.arranged(style=style, song=song)
        self.assertEqual(style[arranger.MELODY][melody.ENGINE], melody.SERIAL)
        voices = [part for name, part in made[composer.PARTS].items() if name.startswith(THREE)]
        self.assertEqual(len(voices), len(style[arranger.SECTIONS][THREE][arranger.PLAYS]))
        for voice in voices:
            heard = [pitch_of(note) for line in voice[notation.LINES] for note in line if notation.REST not in note][:NOTES_IN_SCALE]
            self.assertEqual(len(set(heard)), NOTES_IN_SCALE)

