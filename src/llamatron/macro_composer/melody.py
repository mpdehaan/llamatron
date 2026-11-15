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

"""A sketch of a tune, made by rule from a style's melody habits, a section's chords and a seed.

The sketch is a starting tune for a person to improve: correct, singable and in the style's scale, never a hook. A section is
cut into lines; the style's plan says which line each is (a letter, so that a line returns), whether it is varied, and whether
the lead or the answering instrument plays it. A line takes one of the style's rhythm cells and walks the style's ladder of
notes by step, landing its long notes on the notes of the chord under them. The same seed gives the same tune.
"""

import random

from llamatron.macro_composer.operations import backwards, moved, rotated, upside_down
from llamatron.macro_composer.notation import ACCIDENTAL, ARRIVAL, DEGREE, ENDING, FLAT, LOUDER, OCTAVE, REST, SHARP, STEPS, STRESS

# The fields of a style's melody habits.
GRID = 'grid'
LINE_BARS = 'line_bars'
LADDER = 'ladder'
RHYTHMS = 'rhythms'
ANSWER_RHYTHMS = 'answer_rhythms'
HOME = 'home'
SPAN = 'span'
# The fields of a plan's line.
LINE = 'line'
VARIED = 'varied'
ANSWER = 'answer'
# What a line's notes are seeded by: the song's seed, whether it answers, the line's letter, and its place when it is varied.
LINE_SEED = '{} {} {} {}'
HIGHER = 'higher'
# The engines a tune is made by, and the habits the serial one reads besides.
ENGINE = 'engine'
STEP_WALK = 'step walk'
SERIAL = 'serial'
EVOLVING = 'evolving'
# What each new line of the evolving engine adds to the running amount: places moved up the ladder, and notes begun later.
EVOLVE = 'evolve'
MOVE = 'move'
ROTATE = 'rotate'
DEFAULT_EVOLVE = {MOVE: 1, ROTATE: 0}
ROW = 'row'
LENGTHS = 'lengths'
CHROMATIC = 'chromatic'
LEAPS = 'leaps'
ROTATIONS = 'rotations'
# A voice's rows of loudness, each an amount louder or softer than the voice, and of articulation, each how many parts in four of a
# note's length sound.
LOUDNESS = 'loudness'
ARTICULATION = 'articulation'
PARTS_OF_A_LENGTH = 4
# How many notes of the row sound together as a chord, and which of them a voice takes.
TOGETHER = 'together'
TAKES = 'takes'
DEFAULT_LENGTHS = (1, 1, 2, 2, 3, 4, 1)
ALL_DEGREES = ({DEGREE: 1}, {DEGREE: 2}, {DEGREE: 3}, {DEGREE: 4}, {DEGREE: 5}, {DEGREE: 6}, {DEGREE: 7})
# A form begins one place above or below the note the form before it ended on.
BESIDE = (1, -1)
PITCH_FIELDS = (DEGREE, ACCIDENTAL, OCTAVE)
VOICE_SEED = '{} {}'
ROW_SEED = 'row {}'
STREAM_SEED = 'stream {} {}'
# The half steps of each scale type's notes above its root.
MAJOR = 'major'
MINOR = 'minor'
HALF_STEPS = {
    MAJOR: (0, 2, 4, 5, 7, 9, 11), MINOR: (0, 2, 3, 5, 7, 8, 10), 'dorian': (0, 2, 3, 5, 7, 9, 10), 'mixolydian': (0, 2, 4, 5, 7, 9, 10),
}
HALF_STEPS_OF_MARK = {SHARP: 1, FLAT: -1}
NOTES_IN_OCTAVE = 12
NOTES_IN_SCALE = 7
OCTAVES_OF_LADDER = (-1, 0, 1)
# A long note lasts at least this share of a bar, and lands on a note of the chord.
LONG_SHARE = 4
# How far a line may move from one note to the next along the ladder, likeliest first, and how much a higher line starts up.
MOVES = (-1, 1, -1, 1, 0, -2, 2)
HIGHER_BY = 2
VARIED_NOTES = 2
THIRD = 2
FIFTH = 4
MAJOR_THIRD = 4
PERFECT_FIFTH = 7


def half_steps_of(*, note, scale_type):
    """A note of the scale, with its sharp or flat, as half steps above the scale's root."""
    return HALF_STEPS[scale_type][(note[DEGREE] - 1) % NOTES_IN_SCALE] + HALF_STEPS_OF_MARK.get(note.get(ACCIDENTAL), 0)


def ladder_of(*, notes, scale_type):
    """The style's notes over three octaves, lowest first, each with its octave and its half steps above the root."""
    rungs = []
    for octave in OCTAVES_OF_LADDER:
        for note in notes:
            rung = dict(note)
            if octave:
                rung[OCTAVE] = octave
            rungs.append((octave * NOTES_IN_OCTAVE + half_steps_of(note=note, scale_type=scale_type), rung))
    return sorted(rungs, key=height_of)


def height_of(rung):
    return rung[0]


def chord_notes(*, chord, scale_type):
    """The pitch classes of the chord on a degree of the scale; a chord with a sharp or flat is a major chord."""
    if ACCIDENTAL in chord:
        root = half_steps_of(note=chord, scale_type=scale_type)
        return {root % NOTES_IN_OCTAVE, (root + MAJOR_THIRD) % NOTES_IN_OCTAVE, (root + PERFECT_FIFTH) % NOTES_IN_OCTAVE}
    steps = HALF_STEPS[scale_type]
    return {steps[(chord[DEGREE] - 1 + more) % NOTES_IN_SCALE] for more in (0, THIRD, FIFTH)}


def nearest_chord_rung(*, ladder, place, wanted):
    """The place on the ladder nearest a place whose note is in the chord, or the place itself when none is near."""
    for away in (0, -1, 1):
        if 0 <= place + away < len(ladder) and ladder[place + away][0] % NOTES_IN_OCTAVE in wanted:
            return place + away
    return place


def line_of(*, rhythm, ladder, start, low, high, chords, grid, scale_type, dice):
    """One line: a rhythm cell with a note for each of its sounds, as the notes a tune's line is written in."""
    place = start
    notes = []
    at = 0
    for cell in rhythm:
        if REST in cell:
            notes.append({REST: cell[REST]})
            at += cell[REST]
            continue
        place = max(low, min(high, place + (dice.choice(MOVES) if notes and any(REST not in note for note in notes) else 0)))
        if cell[STEPS] * LONG_SHARE >= grid:
            place = nearest_chord_rung(ladder=ladder, place=place, wanted=chord_notes(chord=chords[(at // grid) % len(chords)], scale_type=scale_type))
        notes.append({**ladder[place][1], STEPS: cell[STEPS]})
        at += cell[STEPS]
    return notes


def stressed(notes):
    """A line with its longest note marked as the arrival and its last as the ending."""
    sounds = [note for note in notes if REST not in note]
    if len(sounds) > 1:
        longest = max(sounds, key=steps_of)
        if longest is not sounds[-1]:
            longest[STRESS] = ARRIVAL
        sounds[-1][STRESS] = ENDING
    return notes


def steps_of(note):
    return note[STEPS]


def home_place(*, ladder, home):
    """Where on the ladder the home note of the middle octave is."""
    for place, (_, rung) in enumerate(ladder):
        if rung[DEGREE] == home[DEGREE] and rung.get(ACCIDENTAL) == home.get(ACCIDENTAL) and OCTAVE not in rung:
            return place
    return len(ladder) // 2


def silent_line(*, grid, bars):
    return [{REST: grid}] * bars


class StepWalk:
    """The first melody engine: a singable tune that takes one of the style's rhythm cells for a line and walks the style's ladder
    of notes by step, landing its long notes on the chord. A section's plan says which line returns and which is varied.

    Another engine is a subclass that makes a new line, and varies a line it has made, its own way."""

    __slots__ = ('_habits', '_chords', '_scale_type', '_seed', '_answers', '_grid', '_ladder', '_home', '_low', '_high')

    def __init__(self, *, habits, chords, scale_type, seed, answers, voice=None):
        self._habits = habits
        self._chords = chords
        self._scale_type = scale_type
        self._seed = seed if voice is None else VOICE_SEED.format(seed, voice)
        self._answers = answers
        self._grid = habits[GRID]
        self._ladder = ladder_of(notes=self.notes(), scale_type=scale_type)
        self._home = home_place(ladder=self._ladder, home=habits[HOME])
        self._low = max(0, self._home - habits[SPAN])
        self._high = min(len(self._ladder) - 1, self._home + habits[SPAN])

    def notes(self):
        """The notes the engine draws on, within one octave."""
        return self._habits[LADDER]

    def within(self, place):
        return max(self._low, min(self._high, place))

    def new_line(self, *, entry, under, dice):
        """A line nobody has heard yet."""
        rhythms = self._habits[ANSWER_RHYTHMS] if self._answers else self._habits[RHYTHMS]
        start = self._home + (HIGHER_BY if entry.get(HIGHER) else 0) + dice.choice((0, 0, 1, -1, 2))
        return line_of(rhythm=dice.choice(rhythms), ladder=self._ladder, start=self.within(start), low=self._low, high=self._high, chords=under,
                       grid=self._grid, scale_type=self._scale_type, dice=dice)

    def varied_line(self, *, line, dice):
        """A line heard before, changed a little: its last notes moved."""
        sounds = [note for note in line if REST not in note]
        for note in sounds[-VARIED_NOTES:]:
            rung = self._ladder[self.within(self._home + dice.choice(MOVES))][1]
            for field in PITCH_FIELDS + (STRESS,):
                note.pop(field, None)
            note.update(rung)
        return line

    def sketched(self, plan):
        """A section's tune as lines: the lead's, or the answering instrument's; a line that isn't its own is silent."""
        bars = self._habits[LINE_BARS]
        known = {}
        lines = []
        for count, entry in enumerate(plan):
            under = [self._chords[(count * bars + bar) % len(self._chords)] for bar in range(bars)]
            if bool(entry.get(ANSWER)) != self._answers:
                lines.append(silent_line(grid=self._grid, bars=bars))
                continue
            letter = entry.get(LINE, str(count))
            dice = random.Random(LINE_SEED.format(self._seed, self._answers, letter, len(lines) if entry.get(VARIED) else ''))
            if letter in known and not entry.get(VARIED):
                lines.append([dict(note) for note in known[letter]])
                continue
            if letter in known:
                lines.append(stressed(self.varied_line(line=[dict(note) for note in known[letter]], dice=dice)))
                continue
            made = stressed(self.new_line(entry=entry, under=under, dice=dice))
            known[letter] = made
            lines.append([dict(note) for note in made])
        return lines


class Serial(StepWalk):
    """The serial engine: every note of the song's scale once, in an order the seed draws, is the row, and every line is made of
    the row and its forms: backwards, upside down, upside down and backwards, each moved to start beside the note the last form
    ended on. No note returns until the others have sounded. The lengths of the notes are a row of their own, read forwards and
    then backwards. Every voice of a song shares the row and reads it its own way. A varied line is the line's notes backwards
    in its own rhythm. With the habit chromatic the row is all twelve notes; with leaps each note may take any octave in range.
    A form may begin anywhere in the row and go round (rotations, usual). A voice may have a row of loudness and a row of
    articulation, read as the lengths are. Voices with one name that each take one of so many notes together play chords of
    neighbouring notes of the row."""

    __slots__ = ('_row', '_form', '_at', '_lengths', '_length_at', '_place', '_stream', '_sounded')

    def __init__(self, *, habits, chords, scale_type, seed, answers, voice=None):
        super().__init__(habits=habits, chords=chords, scale_type=scale_type, seed=seed, answers=answers, voice=voice)
        self._row = list(range(len(self.notes())))
        random.Random(ROW_SEED.format(seed)).shuffle(self._row)
        self._stream = random.Random(STREAM_SEED.format(self._seed, answers))
        self._form = self._stream.choice(FORMS)(row=self._row, size=len(self._row))
        self._at = 0
        self._lengths = list(habits.get(LENGTHS, DEFAULT_LENGTHS))
        self._stream.shuffle(self._lengths)
        self._length_at = 0
        self._sounded = 0
        self._place = self._home

    def notes(self):
        if self._habits.get(CHROMATIC):
            return twelve_notes(self._scale_type)
        return self._habits.get(ROW, ALL_DEGREES)

    def row(self):
        """The row, as places in the engine's notes."""
        return list(self._row)

    def next_note(self):
        """The next note of the form being read, placed in an octave; when a form ends, another begins beside its last note."""
        if self._at == len(self._form):
            form = self._stream.choice(FORMS)(row=self._row, size=len(self._row))
            if self._habits.get(ROTATIONS, True):
                form = rotated(row=form, by=self._stream.randrange(len(form)))
            beside = (self._form[-1] + self._stream.choice(BESIDE)) % len(self._row)
            self._form = moved(row=form, by=beside - form[0], size=len(self._row))
            self._at = 0
        wanted = self.notes()[self._form[self._at]]
        self._at += 1
        places = [place for place in range(self._low, self._high + 1) if same_note(one=self._ladder[place][1], other=wanted)]
        if not places:
            places = [place for place in range(len(self._ladder)) if same_note(one=self._ladder[place][1], other=wanted)]
        self._place = self._stream.choice(places) if self._habits.get(LEAPS) else min(places, key=lambda place: abs(place - self._place))
        return dict(self._ladder[self._place][1])

    def next_length(self):
        """The next length of the row of lengths, which is read forwards and then backwards."""
        self._length_at += 1
        return there_and_back(values=self._lengths, at=self._length_at - 1)

    def next_sound(self):
        """The next note this voice plays: the next of the row, or, where so many notes sound together as a chord, the one
        of them this voice takes; every voice of the chord reads the same notes, so that together they are the chord."""
        together = [self.next_note() for _ in range(self._habits.get(TOGETHER, 1))]
        return together[self._habits.get(TAKES, 0)]

    def new_line(self, *, entry, under, dice):
        """Notes of the row in the row of lengths, each as loud as the row of loudness says, where there is one, and sounding
        for as much of its length as the row of articulation says, the rest of the length silent."""
        whole = self._grid * self._habits[LINE_BARS]
        notes = []
        at = 0
        while at < whole:
            length = min(self.next_length(), whole - at)
            note = self.next_sound()
            if self._habits.get(LOUDNESS):
                note[LOUDER] = there_and_back(values=self._habits[LOUDNESS], at=self._sounded)
            sounds = length
            if self._habits.get(ARTICULATION):
                sounds = max(1, length * there_and_back(values=self._habits[ARTICULATION], at=self._sounded) // PARTS_OF_A_LENGTH)
            self._sounded += 1
            notes.append({**note, STEPS: sounds})
            if sounds < length:
                notes.append({REST: length - sounds})
            at += length
        return notes

    def varied_line(self, *, line, dice):
        sounds = [note for note in line if REST not in note]
        pitches = [{field: note[field] for field in PITCH_FIELDS if field in note} for note in reversed(sounds)]
        for note, pitch in zip(sounds, pitches):
            for field in PITCH_FIELDS + (STRESS,):
                note.pop(field, None)
            note.update(pitch)
        return line


def there_and_back(*, values, at):
    """A row of values read forwards and then backwards, over and over: the value at a count."""
    turn, place = divmod(at, len(values))
    return values[place if turn % 2 == 0 else len(values) - 1 - place]


class Evolving(StepWalk):
    """The engine of repeats that evolve, after the principle of registers, written out as plain patterns with no register set
    up: the first line is a step walk's, and every new line after it is that same phrase with a running amount added, which
    grows with each line: its notes moved so many places up the ladder, going round at the top of the range, and the phrase
    begun so many notes later. A varied line is the line begun one note later. The habit evolve says how much each line adds."""

    __slots__ = ('_phrase', '_made')

    def __init__(self, *, habits, chords, scale_type, seed, answers, voice=None):
        super().__init__(habits=habits, chords=chords, scale_type=scale_type, seed=seed, answers=answers, voice=voice)
        self._phrase = None
        self._made = 0

    def place_of(self, note):
        """Where on the ladder a note is."""
        for place, (_, rung) in enumerate(self._ladder):
            if same_note(one=rung, other=note) and rung.get(OCTAVE, 0) == note.get(OCTAVE, 0):
                return place
        return self._home

    def round_the_range(self, place):
        return self._low + (place - self._low) % (self._high - self._low + 1)

    def new_line(self, *, entry, under, dice):
        if self._phrase is None:
            self._phrase = super().new_line(entry=entry, under=under, dice=dice)
            # A long note that landed on the chord may lie a place outside the range, which then reaches as far as the phrase does.
            places = [self.place_of(note) for note in self._phrase if REST not in note]
            self._low = min([self._low] + places)
            self._high = max([self._high] + places)
            return [dict(note) for note in self._phrase]
        self._made += 1
        adds = {**DEFAULT_EVOLVE, **self._habits.get(EVOLVE, {})}
        sounds = [note for note in self._phrase if REST not in note]
        places = [self.round_the_range(self.place_of(note) + self._made * adds[MOVE]) for note in sounds]
        places = rotated(row=places, by=self._made * adds[ROTATE])
        return self.with_places(line=self._phrase, places=places)

    def with_places(self, *, line, places):
        """A line's rhythm with the notes at the places given, one for each of its sounds."""
        made = []
        left = list(places)
        for note in line:
            made.append(dict(note) if REST in note else {**self._ladder[left.pop(0)][1], STEPS: note[STEPS]})
        return made

    def varied_line(self, *, line, dice):
        places = [self.place_of(note) for note in line if REST not in note]
        return self.with_places(line=line, places=rotated(row=places, by=1))


def same_note(*, one, other):
    return one[DEGREE] == other[DEGREE] and one.get(ACCIDENTAL) == other.get(ACCIDENTAL)


def twelve_notes(scale_type):
    """All twelve notes within an octave, each written as a note of the scale or as the scale note below it, sharpened."""
    steps = HALF_STEPS[scale_type]
    notes = []
    for half_steps in range(NOTES_IN_OCTAVE):
        if half_steps in steps:
            notes.append({DEGREE: steps.index(half_steps) + 1})
        else:
            notes.append({DEGREE: steps.index(half_steps - 1) + 1, ACCIDENTAL: SHARP})
    return notes


def as_written(row):
    return list(row)


def row_upside_down(*, row, size):
    return upside_down(row=row, size=size)


def row_backwards(*, row, size):
    return backwards(row)


def row_upside_down_and_backwards(*, row, size):
    return backwards(upside_down(row=row, size=size))


def row_as_written(*, row, size):
    return as_written(row)


# The four forms of a row.
FORMS = (row_as_written, row_backwards, row_upside_down, row_upside_down_and_backwards)
ENGINES = {STEP_WALK: StepWalk, SERIAL: Serial, EVOLVING: Evolving}


def sketched(*, habits, plan, chords, scale_type, seed, answers, engine=None, voice=None):
    """A section's tune as lines, made by the engine named, else the one the habits name, else the step walk."""
    made_by = ENGINES[engine or habits.get(ENGINE, STEP_WALK)]
    return made_by(habits=habits, chords=chords, scale_type=scale_type, seed=seed, answers=answers, voice=voice).sketched(plan)
