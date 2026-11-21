# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A sketch of a tune, made by rule from a style's melody habits, a section's chords and a seed.

The sketch is a starting tune for a person to improve: correct, singable and in the style's scale. A section is
cut into lines; the style's plan says which line each is (a letter, so that a line returns), whether it is varied, and whether
the lead or the answering instrument plays it. A line takes one of the style's rhythm cells and walks the style's ladder of
notes by step, landing its long notes on the notes of the chord under them. The same seed gives the same tune.
"""

import copy
import math
import random

from llamatron.macro_composer import hook_kinds, hook_writing, notation, phrasing
from llamatron.macro_composer.operations import backwards, moved, rotated, upside_down
from llamatron.macro_composer.phrasing import breathed, ended_early, is_shorter
from llamatron.strings import errors

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
# A line that is its section's hook: a short figure said, then said again with another ending.
HOOK = 'hook'
# What a line's notes are seeded by: the song's seed, whether it answers, the line's letter, and its place when it is varied.
LINE_SEED = '{} {} {} {}'
# A song's hooks: the main one, which a kind of section's plan places among its lines, and a second, a short tag sung in
# another kind of section. A song says of the main hook where it sits among its section's lines, and of the second where it is
# sung, who sings it and which take it is.
HOOKS = 'hooks'
MAIN_HOOK = 'main'
SECOND_HOOK = 'second'
PLACEMENT = 'placement'
SUNG_IN = 'sung_in'
SUNG_BY = 'sung_by'
TAG_TAKE = 'take'
FIRST_LINES = 'first lines'
LAST_LINE = 'last line'
FIRST_AND_LAST = 'first and last'
PLACEMENTS = (FIRST_LINES, LAST_LINE, FIRST_AND_LAST)
# Which of a section's four lines are the hook under each placement.
PLACED = {FIRST_LINES: (True, True, True, False), LAST_LINE: (False, False, False, True), FIRST_AND_LAST: (True, False, False, True)}
# A line that is the song's second hook, its tag.
TAG = 'tag'
TAG_LINE = 'tag'
# The lines that lead to a hook or stand between two statements of it, and the line that closes after it.
TOWARD_LINE = 'toward'
TURN_LINE = 'turn'
CLOSE_LINE = 'close'
TAG_SEED = '{} tag {}'
# A tag's top sits this far under the lowest place the main hook's top may sit, so that the main hook keeps the song's top.
TAG_BELOW = 2
# The rhythms a tag may take, each short and choppy against a hook's long note.
TAG_RHYTHMS = (hook_kinds.EIGHTHS_WITH_A_GAP, hook_kinds.THREE_THREE_TWO, hook_kinds.AFTER_ONE)
# A line of a chorus's body, which is no hook: the line before a hook leads to it, and the section's last line closes.
BODY = 'body'
LEADS_TO_HOOK = 'leads_to_hook'
CLOSES = 'closes'
# Where among the nearest rhythms a song's first hook starts, a number of the song's own.
WRITING_SEED = '{} hook writing'
# The silence a written hook's answer ends in, in units of its bar, where the bar has the room.
ANSWER_BREATH = 2
# A last note of this many units or more is held whole: the note is the room.
HELD_UNITS = 4
# A shorter line of a chorus's body ends in this many eighths more silence than its Space gauge gives.
SHORTER_LINE_BREATH = 1
# A song's later takes of its hook each have dice of their own, so that a new hook leaves every other line as it was.
HOOK_TAKE = 'hook_take'
FIRST_HOOK_TAKE = 0
HOOK_TAKE_SEED = '{} hook take {}'
HIGHER = 'higher'
# A line that sits lower than the song's lines do, as a verse under its chorus.
LOWER = 'lower'
# How busy a line is asked to be, a place on the gauges' scale, over what the writer would choose: the line takes a rhythm of
# about so many notes.
LINE_BUSY = 'busy'
# What a song asks of its melodies over its style's plans: how much a section's lines repeat, how busy every line is, and, by
# kind of section, how high the section's lines sit and how busy they are.
MELODY_ASKS = 'melody_asks'
REPEATS = 'repeats'
REPEATS_A_LITTLE = 'a little'
REPEATS_SOME = 'some'
REPEATS_A_LOT = 'a lot'
REPEATS_WAYS = (REPEATS_A_LITTLE, REPEATS_SOME, REPEATS_A_LOT)
BY_KIND = 'by_kind'
HEIGHT = 'height'
LOW = 'low'
MIDDLE = 'middle'
HIGH = 'high'
HEIGHTS = (LOW, MIDDLE, HIGH)
# The letter of a line that repeats no other line of its section.
LINE_OF_ITS_OWN = '{letter} {place}'
# How many of a style's rhythms a line asked to be so busy chooses among: the nearest.
BUSY_DECK = 2
# A habit a planned song asks for: the tune's lines breathe.
BREATHES = 'breathes'
# The hook's line written out by hand, note by note: where the habits hold one, the hook is that line and no other.
HOOK_NOTES = 'hook_notes'
# A line of a section's plan written out by hand.
LINE_NOTES = 'written'
BREATH_SEED = '{} breath {} {}'
# The degrees an ending left open rests on.
OPEN_DEGREES = (2, 6)
# The engines a tune is made by, and the habits the serial one reads besides.
ENGINE = 'engine'
STEP_WALK = 'step walk'
SERIAL = 'serial'
EVOLVING = 'evolving'
SMART = 'smart'
# The smart engine's seven gauges, each from 1 to 8, and where each stands until a style or a song says: how often a tune leaps,
# whether its steps fall or rise, whether the note after a leap comes back or carries on, how strongly a phrase arches, whether
# a note that leans is resolved or left hanging, how long its notes are, and how often it breaks its own tendencies.
GAUGE_MOVES = 'moves'
GAUGE_STEPS = 'steps'
GAUGE_AFTER_LEAP = 'after_leap'
GAUGE_PHRASE = 'phrase'
GAUGE_LEANING = 'leaning'
GAUGE_NOTES = 'notes'
GAUGE_SURPRISE = 'surprise'
LOWEST_GAUGE = 1
HIGHEST_GAUGE = 8
DEFAULT_GAUGES = {GAUGE_MOVES: 2, GAUGE_STEPS: 3, GAUGE_AFTER_LEAP: 2, GAUGE_PHRASE: 6, GAUGE_LEANING: 3, GAUGE_NOTES: 4, GAUGE_SURPRISE: 3}
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
ALL_DEGREES = ({notation.DEGREE: 1}, {notation.DEGREE: 2}, {notation.DEGREE: 3}, {notation.DEGREE: 4}, {notation.DEGREE: 5}, {notation.DEGREE: 6}, {notation.DEGREE: 7})
# A form begins one place above or below the note the form before it ended on.
BESIDE = (1, -1)
PITCH_FIELDS = (notation.DEGREE, notation.ACCIDENTAL, notation.OCTAVE)
VOICE_SEED = '{} {}'
ROW_SEED = 'row {}'
STREAM_SEED = 'stream {} {}'
# The half steps of each scale type's notes above its root.
MAJOR = 'major'
MINOR = 'minor'
HALF_STEPS = {
    MAJOR: (0, 2, 4, 5, 7, 9, 11), MINOR: (0, 2, 3, 5, 7, 8, 10), 'dorian': (0, 2, 3, 5, 7, 9, 10), 'mixolydian': (0, 2, 4, 5, 7, 9, 10),
}
HALF_STEPS_OF_MARK = {notation.SHARP: 1, notation.FLAT: -1}
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
    return HALF_STEPS[scale_type][(note[notation.DEGREE] - 1) % NOTES_IN_SCALE] + HALF_STEPS_OF_MARK.get(note.get(notation.ACCIDENTAL), 0)


def ladder_of(*, notes, scale_type):
    """The style's notes over three octaves, lowest first, each with its octave and its half steps above the root."""
    rungs = []
    for octave in OCTAVES_OF_LADDER:
        for note in notes:
            rung = dict(note)
            if octave:
                rung[notation.OCTAVE] = octave
            rungs.append((octave * NOTES_IN_OCTAVE + half_steps_of(note=note, scale_type=scale_type), rung))
    return sorted(rungs, key=height_of)


def height_of(rung):
    return rung[0]


def chord_notes(*, chord, scale_type):
    """The pitch classes of the chord on a degree of the scale; a chord with a sharp or flat is a major chord."""
    if notation.ACCIDENTAL in chord:
        root = half_steps_of(note=chord, scale_type=scale_type)
        return {root % NOTES_IN_OCTAVE, (root + MAJOR_THIRD) % NOTES_IN_OCTAVE, (root + PERFECT_FIFTH) % NOTES_IN_OCTAVE}
    steps = HALF_STEPS[scale_type]
    return {steps[(chord[notation.DEGREE] - 1 + more) % NOTES_IN_SCALE] for more in (0, THIRD, FIFTH)}


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
        if notation.REST in cell:
            notes.append({notation.REST: cell[notation.REST]})
            at += cell[notation.REST]
            continue
        place = max(low, min(high, place + (dice.choice(MOVES) if notes and any(notation.REST not in note for note in notes) else 0)))
        if cell[notation.STEPS] * LONG_SHARE >= grid:
            place = nearest_chord_rung(ladder=ladder, place=place, wanted=chord_notes(chord=chords[(at // grid) % len(chords)], scale_type=scale_type))
        notes.append({**ladder[place][1], notation.STEPS: cell[notation.STEPS]})
        at += cell[notation.STEPS]
    return notes


def stressed(notes):
    """A line with its longest note marked as the arrival and its last as the ending."""
    sounds = [note for note in notes if notation.REST not in note]
    if len(sounds) > 1:
        longest = max(sounds, key=steps_of)
        if longest is not sounds[-1]:
            longest[notation.STRESS] = notation.ARRIVAL
        sounds[-1][notation.STRESS] = notation.ENDING
    return notes


def steps_of(note):
    return note[notation.STEPS]


def home_place(*, ladder, home):
    """Where on the ladder the home note of the middle octave is."""
    for place, (_, rung) in enumerate(ladder):
        if rung[notation.DEGREE] == home[notation.DEGREE] and rung.get(notation.ACCIDENTAL) == home.get(notation.ACCIDENTAL) and notation.OCTAVE not in rung:
            return place
    return len(ladder) // 2


def silent_line(*, grid, bars):
    return [{notation.REST: grid}] * bars


class StepWalk:
    """The first melody engine: a singable tune that takes one of the style's rhythm cells for a line and walks the style's ladder
    of notes by step, landing its long notes on the chord. A section's plan says which line returns and which is varied.

    Another engine is a subclass that makes a new line, and varies a line it has made, its own way."""

    __slots__ = ('_habits', '_chords', '_scale_type', '_seed', '_answers', '_grid', '_ladder', '_home', '_low', '_high', '_letters')

    def __init__(self, *, habits, chords, scale_type, seed, answers, voice=None, letters=()):
        self._habits = habits
        self._chords = chords
        self._scale_type = scale_type
        self._seed = seed if voice is None else VOICE_SEED.format(seed, voice)
        self._answers = answers
        # The letters of every line of the song this engine's player plays, in the order the song first plays them.
        self._letters = list(letters)
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

    def get_ladder(self):
        """The notes the engine walks, lowest first, each with its half steps above the root."""
        return self._ladder

    def get_home(self):
        """The place on the ladder a tune sits around."""
        return self._home

    def get_seed(self):
        """What the engine draws each line's dice from."""
        return self._seed

    def held_under(self, *, highest, made):
        """What makes a line, run with the engine's top place lowered to the one given."""
        kept = self._high
        self._high = max(self._low, min(kept, highest))
        try:
            return made()
        finally:
            self._high = kept

    def new_line(self, *, entry, under, dice):
        """A line nobody has heard yet."""
        rhythms = self._habits[ANSWER_RHYTHMS] if self._answers else self._habits[RHYTHMS]
        start = self._home + (HIGHER_BY if entry.get(HIGHER) else -HIGHER_BY if entry.get(LOWER) else 0) + dice.choice((0, 0, 1, -1, 2))
        if LINE_BUSY in entry:
            # A line asked to be so busy takes one of the style's few rhythms nearest that many notes, so that the lines are not all one rhythm.
            ordered = sorted(rhythms, key=sounds_in)
            place = round(share_of_gauge(entry[LINE_BUSY]) * (len(ordered) - 1))
            first = max(0, min(place - BUSY_DECK // 2, len(ordered) - BUSY_DECK))
            rhythms = ordered[first:first + BUSY_DECK]
        return line_of(rhythm=dice.choice(rhythms), ladder=self._ladder, start=self.within(start), low=self._low, high=self._high, chords=under,
                       grid=self._grid, scale_type=self._scale_type, dice=dice)

    def varied_line(self, *, line, dice, entry=None, under=None):
        """A line heard before, changed a little: its last notes moved."""
        sounds = [note for note in line if notation.REST not in note]
        for note in sounds[-VARIED_NOTES:]:
            rung = self._ladder[self.within(self._home + dice.choice(MOVES))][1]
            for field in PITCH_FIELDS + (notation.STRESS,):
                note.pop(field, None)
            note.update(rung)
        return line

    def body_breath(self, *, entry, count, line):
        """The breath of a line of a chorus's body, in eighths, where a writer has one to give; None leaves the breath to the song's ways."""
        return None

    def finished(self, *, line, entry, under):
        """A new line after its breath, for a writer that has something to say of where the line then ends."""
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
            if entry.get(LINE_NOTES):
                # A line written by hand is the line, and the idea its letter names from here on.
                known[letter] = copy.deepcopy(entry[LINE_NOTES])
                lines.append(copy.deepcopy(entry[LINE_NOTES]))
                continue
            dice = random.Random(LINE_SEED.format(self._seed, self._answers, letter, len(lines) if entry.get(VARIED) else ''))
            if letter in known and not entry.get(VARIED):
                lines.append([dict(note) for note in known[letter]])
                continue
            if letter in known:
                lines.append(stressed(self.varied_line(line=[dict(note) for note in known[letter]], dice=dice, entry=entry, under=under)))
                continue
            made = self.new_line(entry=entry, under=under, dice=dice)
            breathes = bool(self._habits.get(BREATHES))
            of_body = self.body_breath(entry=entry, count=count, line=made)
            if (breathes or phrasing.LINE_BREATH in entry or phrasing.LINE_EARLY in entry or of_body is not None) and not entry.get(HOOK) and not entry.get(TAG):
                # A line of a chorus's body ends in the silence its Space gauge gives, a shorter line in a little more, unless the line says its own breath.
                # The breath is drawn apart from the line, so that a line is the same notes whether it breathes or not.
                made = breathed(line=made, grid=self._grid, count=count, dice=random.Random(BREATH_SEED.format(self._seed, self._answers, letter)),
                                ways=self._habits[BREATHES] if isinstance(self._habits.get(BREATHES), dict) else None, breath=entry.get(phrasing.LINE_BREATH, of_body),
                                early=entry.get(phrasing.LINE_EARLY, None if breathes else False))
                made = self.finished(line=made, entry=entry, under=under)
            made = stressed(made)
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

    def __init__(self, *, habits, chords, scale_type, seed, answers, voice=None, letters=()):
        super().__init__(habits=habits, chords=chords, scale_type=scale_type, seed=seed, answers=answers, voice=voice, letters=letters)
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
                note[notation.LOUDER] = there_and_back(values=self._habits[LOUDNESS], at=self._sounded)
            sounds = length
            if self._habits.get(ARTICULATION):
                sounds = max(1, length * there_and_back(values=self._habits[ARTICULATION], at=self._sounded) // PARTS_OF_A_LENGTH)
            self._sounded += 1
            notes.append({**note, notation.STEPS: sounds})
            if sounds < length:
                notes.append({notation.REST: length - sounds})
            at += length
        return notes

    def varied_line(self, *, line, dice, entry=None, under=None):
        sounds = [note for note in line if notation.REST not in note]
        pitches = [pitch_of(note) for note in reversed(sounds)]
        for note, pitch in zip(sounds, pitches):
            for field in PITCH_FIELDS + (notation.STRESS,):
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

    def __init__(self, *, habits, chords, scale_type, seed, answers, voice=None, letters=()):
        super().__init__(habits=habits, chords=chords, scale_type=scale_type, seed=seed, answers=answers, voice=voice, letters=letters)
        self._phrase = None
        self._made = 0

    def place_of(self, note):
        """Where on the ladder a note is."""
        for place, (_, rung) in enumerate(self._ladder):
            if same_note(one=rung, other=note) and rung.get(notation.OCTAVE, 0) == note.get(notation.OCTAVE, 0):
                return place
        return self._home

    def round_the_range(self, place):
        return self._low + (place - self._low) % (self._high - self._low + 1)

    def new_line(self, *, entry, under, dice):
        if self._phrase is None:
            self._phrase = super().new_line(entry=entry, under=under, dice=dice)
            # A long note that landed on the chord may lie a place outside the range, which then reaches as far as the phrase does.
            places = [self.place_of(note) for note in self._phrase if notation.REST not in note]
            self._low = min([self._low] + places)
            self._high = max([self._high] + places)
            return [dict(note) for note in self._phrase]
        self._made += 1
        adds = {**DEFAULT_EVOLVE, **self._habits.get(EVOLVE, {})}
        sounds = [note for note in self._phrase if notation.REST not in note]
        places = [self.round_the_range(self.place_of(note) + self._made * adds[MOVE]) for note in sounds]
        places = rotated(row=places, by=self._made * adds[ROTATE])
        return self.with_places(line=self._phrase, places=places)

    def with_places(self, *, line, places):
        """A line's rhythm with the notes at the places given, one for each of its sounds."""
        made = []
        left = list(places)
        for note in line:
            made.append(dict(note) if notation.REST in note else {**self._ladder[left.pop(0)][1], notation.STEPS: note[notation.STEPS]})
        return made

    def varied_line(self, *, line, dice, entry=None, under=None):
        places = [self.place_of(note) for note in line if notation.REST not in note]
        return self.with_places(line=line, places=rotated(row=places, by=1))


# What the smart engine weighs a move by. A move is so many places along the ladder: none repeats the note, one is a step, two
# a skip, three a leap. A step is the norm, and the others are weighed against it.
SMART_MOVES = (-3, -2, -1, 0, 1, 2, 3)
STEP_SIZE = 1
REPEAT_WEIGHT = 0.45
SKIP_SHARE = 0.9
LEAP_SHARE = 0.45
# A leap is likelier upward, a step that follows a step the same way is likelier still, and a move after a leap that comes back
# is likelier than one that carries on, by as much as the gauge says.
LEAP_UP_FAVOUR = 1.5
STEP_ON_FAVOUR = 1.4
RETURN_FAVOUR = 4.0
# How hard a phrase's shape pulls a note toward it: the places away a note may be before its weight falls to a third or so, at
# the gauge's lowest and highest.
LOOSEST_PULL = 6.0
TIGHTEST_PULL = 0.9
# The shapes a line may take, each the height it aims at through the line, from 0 at its start to 1 at its end, as a share of
# the line's reach: an arch, a climb, a tumble down from the top, and a dip.
SHAPE_ARCH = 'arch'
SHAPE_CLIMB = 'climb'
SHAPE_TUMBLE = 'tumble'
SHAPE_DIP = 'dip'
# How much of the range a line's shape reaches over, the share of the tendencies broken at the highest Surprise, the share by
# which a landing note's wish for the chord is weakened at the highest Leaning, and how much more a note off the chord wants the chord's note beside it.
REACH_SHARE = 0.75
MOST_SURPRISE = 0.25
MOST_HANGING = 0.6
RESOLVE_FAVOUR = 3.0
# How much more a note that lands wants a note of the chord, at the lowest Leaning.
CHORD_FAVOUR = 6.0
# A line marked higher sits this share of the range above the others.
HIGHER_SHARE = 0.5
# The fewest rhythms the lines of a song are dealt from, where a style has as many.
SMALLEST_DECK = 3
# A varied line keeps this share of its notes, its head, so that it is known again.
HEAD_SHARE = 0.5
RHYTHM_SEED = 'rhythms {} {}'
# What every shape and every move weighs at the least, so that none is ever impossible, and how much more an arch weighs
# at the highest Phrase.
LEAST_SHAPE = 0.2
DIP_WEIGHT = 0.1
ARCH_FAVOUR = 2
LEAST_STEP = 0.25
LEAST_LEAP = 0.03
# A leap's weight at the highest Moves, and how slowly it grows from the lowest, so that low positions keep leaps rare.
MOST_LEAP = 2
LEAP_CURVE = 1.5
# How much of a move's weight is lost when it carries on after a leap, at the lowest After leap.
CARRY_ON_LOSS = 0.8
SKIP_SIZE = 2
SHAPE_SEED = 'shape {} {} {}'
GAUGE_SEED = '{} gauges {}'


def share_of_gauge(position):
    """A gauge's position as a share from 0, its lowest, to 1, its highest."""
    return (position - LOWEST_GAUGE) / (HIGHEST_GAUGE - LOWEST_GAUGE)


def sounds_in(rhythm):
    return sum(1 for cell in rhythm if notation.REST not in cell)


def shape_height(*, shape, through):
    """The height a shape aims at so far through a line, from -1 to 1 of the line's reach."""
    if shape == SHAPE_ARCH:
        return math.sin(math.pi * through)
    if shape == SHAPE_CLIMB:
        return 2 * through - 1
    if shape == SHAPE_TUMBLE:
        return 1 - 2 * through
    return -math.sin(math.pi * through)


class Smart(StepWalk):
    """The smart engine: a tune that follows what a listener expects. Most moves are steps, steps mostly fall and leaps mostly
    rise, a step tends to carry on, a leap is followed by a move back, each line has a shape, a note off the chord leans toward
    the chord's note beside it, and long notes land on the chord. Seven gauges say how strongly, set by the style and changed
    by a song. A line marked higher, as a chorus's, sits higher, and each line of a song is dealt a rhythm of its own while
    the style's last, so that a chorus is unlike its verse; a varied line keeps its head, so that a hook is known when it returns."""

    __slots__ = ('_gauges', '_song_seed')

    def __init__(self, *, habits, chords, scale_type, seed, answers, voice=None, letters=()):
        super().__init__(habits=habits, chords=chords, scale_type=scale_type, seed=seed, answers=answers, voice=voice, letters=letters)
        self._gauges = {**DEFAULT_GAUGES, **habits.get(SMART, {})}
        # A line's notes are drawn by the seed and where the gauges stand, so that a gauge moved one position is always heard:
        # a small change of the chances alone would often turn no draw. The rhythms dealt and each line's shape go by the
        # song's seed alone, so that a gauge moved keeps them.
        self._song_seed = self._seed
        self._seed = GAUGE_SEED.format(self._seed, [self._gauges[name] for name in DEFAULT_GAUGES])

    def gauge(self, name):
        return share_of_gauge(self._gauges[name])

    def rhythm_for(self, *, entry, dice):
        """A line's rhythm, dealt from the style's so that the song's lines differ: the rhythms nearest the length of note the
        Notes gauge asks for are the deck, shuffled once for the song, and each line takes the next by its place among the
        song's lines, so a chorus's hook has a rhythm no line of the verse before it has while the deck lasts. A line the
        song's list does not name draws one."""
        rhythms = sorted(self._habits[ANSWER_RHYTHMS] if self._answers else self._habits[RHYTHMS], key=sounds_in)
        if not rhythms:
            raise ValueError(errors.ERR_MELODY_NEEDS_RHYTHMS)
        asked = entry.get(LINE_BUSY)
        wanted = (self.gauge(GAUGE_NOTES) if asked is None else share_of_gauge(asked)) * (len(rhythms) - 1)
        nearest = sorted(range(len(rhythms)), key=lambda place: (abs(place - wanted), place))
        # A line asked to be so busy chooses among the few rhythms nearest, so that what was asked is heard.
        deck = [rhythms[place] for place in nearest[:max(SMALLEST_DECK, len(rhythms) - 1) if asked is None else BUSY_DECK]]
        random.Random(RHYTHM_SEED.format(self._song_seed, self._answers)).shuffle(deck)
        letter = entry.get(LINE)
        if letter not in self._letters:
            return dice.choice(deck)
        return deck[self._letters.index(letter) % len(deck)]

    def shape_for(self, *, entry, dice):
        """A line's shape: an arch as often as the Phrase gauge says, else a climb or a tumble as the Steps gauge leans, or a dip."""
        arch = self.gauge(GAUGE_PHRASE)
        rise = self.gauge(GAUGE_STEPS)
        weights = {SHAPE_ARCH: LEAST_SHAPE + ARCH_FAVOUR * arch, SHAPE_CLIMB: LEAST_SHAPE + rise * (1 - arch), SHAPE_TUMBLE: LEAST_SHAPE + (1 - rise) * (1 - arch), SHAPE_DIP: DIP_WEIGHT}
        return dice.choices(list(weights), weights=list(weights.values()))[0]

    def centre(self, entry):
        """The place a line's shape turns about: the home note, or higher by a share of the range for a line marked higher."""
        lift = round(self._habits[SPAN] * HIGHER_SHARE)
        return self.within(self._home + (lift if entry.get(HIGHER) else -lift if entry.get(LOWER) else 0))

    def in_chord(self, *, place, chord):
        return self._ladder[place][0] % NOTES_IN_OCTAVE in chord_notes(chord=chord, scale_type=self._scale_type)

    def weight(self, *, move, place, before, aim, chord, lands):
        """How likely a move is from a place, after the move before it, toward the height the line's shape aims at; a note
        that lands, a long one or a line's last, wants a note of the chord, the less so the more the Leaning gauge leaves hanging."""
        to = place + move
        if not self._low <= to <= self._high:
            return 0
        size = abs(move)
        leaps = self.gauge(GAUGE_MOVES)
        rise = self.gauge(GAUGE_STEPS)
        if size == 0:
            weight = REPEAT_WEIGHT
        elif size == STEP_SIZE:
            weight = (LEAST_STEP + rise) if move > 0 else (LEAST_STEP + 1 - rise)
            if before == move:
                weight *= STEP_ON_FAVOUR
        else:
            weight = (LEAST_LEAP + MOST_LEAP * leaps ** LEAP_CURVE) * (SKIP_SHARE if size == SKIP_SIZE else LEAP_SHARE) * (LEAP_UP_FAVOUR if move > 0 else 1)
        if before is not None and abs(before) > STEP_SIZE and move:
            carries_on = (move > 0) == (before > 0)
            back = 1 - self.gauge(GAUGE_AFTER_LEAP)
            weight *= (1 - back * CARRY_ON_LOSS) if carries_on else (1 + back * (RETURN_FAVOUR - 1))
        if not self.in_chord(place=place, chord=chord) and size == STEP_SIZE and self.in_chord(place=to, chord=chord):
            weight *= 1 + (1 - self.gauge(GAUGE_LEANING)) * (RESOLVE_FAVOUR - 1)
        if lands and self.in_chord(place=to, chord=chord):
            weight *= 1 + (1 - self.gauge(GAUGE_LEANING) * MOST_HANGING) * (CHORD_FAVOUR - 1)
        pull = LOOSEST_PULL + self.gauge(GAUGE_PHRASE) * (TIGHTEST_PULL - LOOSEST_PULL)
        return weight * math.exp(-abs(to - aim) / pull)

    def next_place(self, *, place, before, aim, chord, lands, dice):
        """The place of a line's next note, and the move that reached it."""
        allowed = [move for move in SMART_MOVES if self._low <= place + move <= self._high]
        if dice.random() < self.gauge(GAUGE_SURPRISE) * MOST_SURPRISE:
            move = dice.choice(allowed)
        else:
            weights = [self.weight(move=move, place=place, before=before, aim=aim, chord=chord, lands=lands) for move in allowed]
            move = dice.choices(allowed, weights=weights)[0]
        return place + move, move

    def walked(self, *, rhythm, centre, shape, under, dice, kept=()):
        """A line on a rhythm: the notes kept from a line heard before, then a note for each sound left, chosen by the tendencies."""
        reach = max(1, round(self._habits[SPAN] * REACH_SHARE))
        sounds = sounds_in(rhythm)
        notes = []
        place = None
        before = None
        at = 0
        heard = 0
        for cell in rhythm:
            if notation.REST in cell:
                notes.append({notation.REST: cell[notation.REST]})
                at += cell[notation.REST]
                continue
            chord = under[(at // self._grid) % len(under)]
            through = heard / max(1, sounds - 1)
            aim = centre + reach * shape_height(shape=shape, through=through)
            lands = cell[notation.STEPS] * LONG_SHARE >= self._grid or heard == sounds - 1
            if heard < len(kept):
                place = kept[heard]
            elif place is None:
                place = self.within(nearest_chord_rung(ladder=self._ladder, place=self.within(round(aim)), wanted=chord_notes(chord=chord, scale_type=self._scale_type)))
            else:
                place, before = self.next_place(place=place, before=before, aim=aim, chord=chord, lands=lands, dice=dice)
            notes.append({**self._ladder[place][1], notation.STEPS: cell[notation.STEPS]})
            at += cell[notation.STEPS]
            heard += 1
        return notes

    def new_line(self, *, entry, under, dice):
        shapes = random.Random(SHAPE_SEED.format(self._song_seed, self._answers, entry.get(LINE, '')))
        return self.walked(rhythm=self.rhythm_for(entry=entry, dice=dice), centre=self.centre(entry), shape=self.shape_for(entry=entry, dice=shapes), under=under, dice=dice)

    def place_of(self, note):
        """Where on the ladder a note of a line is."""
        for place, (_, rung) in enumerate(self._ladder):
            if all(rung.get(field) == note.get(field) for field in PITCH_FIELDS):
                return place
        return self._home

    def varied_line(self, *, line, dice, entry=None, under=None):
        """A line heard before, changed: its head kept note for note, on its own rhythm, and its tail walked anew about the
        line's own middle, falling to its close."""
        rhythm = [{notation.REST: note[notation.REST]} if notation.REST in note else {notation.STEPS: note[notation.STEPS]} for note in line]
        places = [self.place_of(note) for note in line if notation.REST not in note]
        kept = places[:max(1, round(len(places) * HEAD_SHARE))]
        centre = self.within(round(sum(places) / len(places))) if places else self._home
        return self.walked(rhythm=rhythm, centre=centre, shape=SHAPE_TUMBLE, under=self._chords, dice=dice, kept=kept)


# A hook's peak, the long note its figure reaches, sits at least this share of the range above the home note, and every line
# that is neither a hook nor marked higher stays below that, so that the hook's top is the song's.
HOOK_FLOOR_SHARE = 0.5
# The same share for a written hook, at the bottom and at the top of its Height gauge.
LOWEST_FLOOR_SHARE = 0.25
HIGHEST_FLOOR_SHARE = 0.75
# The places a melody under the hook always has to move in, about a fourth.
VERSE_ROOM = 4
# A hook's figure fills a bar: short notes through this share of it, then one long note to the bar's end.
HOOK_HEAD_SHARE = 0.5
# The bar is counted in this many units where it divides so, the short notes each lasting 1 to 3 of them, 2 to 4 notes in all.
HOOK_UNITS = 8
LONGEST_SHORT_NOTE = 3
FEWEST_SHORT_NOTES = 2
MOST_SHORT_NOTES = 4
# How many of the figures nearest the Notes gauge a hook's rhythm is drawn from.
HOOK_DECK = 3
# The ways a figure's short notes reach its peak: one note repeated and a leap up, a climb by step, the peak first and a fall
# away from it, and a turn about the notes under it.
REACH_REPEATED = 'repeated'
REACH_CLIMB = 'climb'
REACH_DIP = 'dip'
REACH_TURN = 'turn'
REACHES = (REACH_REPEATED, REACH_CLIMB, REACH_DIP, REACH_TURN)
LEAPS_INTO_PEAK = (2, 3)
FARTHEST_CLIMB = 3
FARTHEST_DIP = 2
# The answer to a hook's figure turns about a place this far under the peak.
ANSWER_BELOW = 2


def short_note_figures(units):
    """Every way of filling some units with 2 to 4 short notes of 1 to 3 units each, the busiest first."""
    figures = []

    def filled(*, so_far, left):
        if left == 0 and FEWEST_SHORT_NOTES <= len(so_far) <= MOST_SHORT_NOTES:
            figures.append(tuple(so_far))
        if left > 0 and len(so_far) < MOST_SHORT_NOTES:
            for length in range(1, min(LONGEST_SHORT_NOTE, left) + 1):
                filled(so_far=[*so_far, length], left=left - length)

    filled(so_far=[], left=units)
    return sorted(figures, key=lambda figure: (-len(figure), figure))


class Hooks(Smart):
    """What makes a song's hook: a figure of one bar, a few short notes reaching one long note that is the top of the song, said
    in the first bar of a line and each second bar after, the bars between answering it lower, walked as the smart engine
    walks. Its rhythm could be clapped, it has few pitches, and it comes back the same. A varied hook keeps all of it but its
    last note, which rises."""

    __slots__ = ('_take',)

    def set_take(self, take):
        """Say which take of the song's hook is made."""
        self._take = take

    def written(self):
        """The hook as a behavior and gauges write it (hook_writing.py), where the habits say so and the bar is counted in
        eighths: the behavior, the gauges, and the bar's lengths and depths; else None."""
        if hook_writing.HOOK_WRITING not in self._habits or self._grid % hook_writing.UNITS:
            return None
        behavior, gauges = hook_writing.hook_ways(self._habits)
        order = random.Random(WRITING_SEED.format(self._song_seed)).randrange(hook_writing.RHYTHM_DECK)
        return behavior, gauges, hook_writing.bar_of(behavior=behavior, gauges=gauges, order=order, take=getattr(self, '_take', FIRST_HOOK_TAKE))

    def peak(self, chord):
        """Where a written hook's top sits over a chord: the note of the chord nearest the hook's floor and no lower."""
        floor = self.hook_floor()
        return self.chord_place(chord=chord, lowest=floor, highest=self._high, toward=floor)

    def with_breath(self, *, lengths, unit):
        """A bar's lengths as a rhythm that leaves room for whoever fills between the lines. A long last note is the room, held
        whole, since the band fills under it. Otherwise the bar ends in a breath of two units where it can: a silence the bar
        opens with is moved to its end, the last note is cut short, and then every silence inside the bar is moved to its end.
        No note is left out."""
        lengths = list(lengths)
        last = max(place for place, length in enumerate(lengths) if length > 0)
        if lengths[last] >= HELD_UNITS:
            return [{notation.REST: -length * unit} if length < 0 else {notation.STEPS: length * unit} for length in lengths]
        if lengths[0] < 0 and lengths[-1] > 0:
            lengths = lengths[1:] + lengths[:1]
        last = max(place for place, length in enumerate(lengths) if length > 0)
        short = ANSWER_BREATH + sum(lengths[last + 1:])
        if short > 0 and lengths[last] > 1:
            cut = min(short, lengths[last] - 1)
            lengths[last:last + 1] = [lengths[last] - cut, -cut]
            short -= cut
        if short > 0:
            lengths = [length for length in lengths if length > 0] + [sum(length for length in lengths if length < 0)]
        return [{notation.REST: -length * unit} if length < 0 else {notation.STEPS: length * unit} for length in lengths if length]

    def written_line(self, *, under, dice):
        """A written hook: its bar in the first bar of the line and each second bar after, its last note on a note of the chord,
        and an answer in the bars between, lower, ending in a breath. The Catchiness gauge says how near the answer is to the
        hook: on a plainer rhythm, on the hook's rhythm, or the hook's own notes a place lower."""
        _, gauges, (lengths, depths) = self.written()
        peak = self.peak(under[0])
        unit = self._grid // hook_writing.UNITS
        places = [self.within(peak - depth) for depth in depths]
        places[-1] = self.chord_place(chord=under[0], lowest=max(self._low, peak - hook_writing.DEEPEST), highest=peak, toward=places[-1])
        catchiness = gauges[hook_writing.CATCHINESS]
        answer = self.with_breath(lengths=lengths if catchiness >= hook_writing.SAME_RHYTHM_FROM else hook_writing.plainer(lengths), unit=unit)
        notes = []
        for bar, chord in enumerate(under):
            if not bar % 2:
                sounding = iter(places)
                notes.extend({notation.REST: -length * unit} if length < 0 else {**self._ladder[next(sounding)][1], notation.STEPS: length * unit} for length in lengths)
                continue
            if catchiness >= hook_writing.SAME_NOTES_FROM:
                lower = [self.within(place - 1) for place in places]
                lower[-1] = self.chord_place(chord=chord, lowest=max(self._low, peak - hook_writing.DEEPEST - 1), highest=max(self._low, peak - 1), toward=lower[-1])
                sounding = iter(lower)
                notes.extend(dict(cell) if notation.REST in cell else {**self._ladder[next(sounding)][1], notation.STEPS: cell[notation.STEPS]} for cell in answer)
                continue
            notes.extend(self.held_under(highest=peak - 1, made=lambda: self.walked(rhythm=answer, centre=self.within(peak - ANSWER_BELOW), shape=SHAPE_TUMBLE, under=[chord], dice=dice)))
        return notes

    def open_place(self, *, lowest, highest, toward):
        """The place nearest one wanted whose note leaves an ending open, or the place wanted where none is near."""
        places = [place for place in range(max(self._low, lowest), min(self._high, highest) + 1) if self._ladder[place][1][notation.DEGREE] in OPEN_DEGREES]
        return min(places, key=lambda place: (abs(place - toward), -place)) if places else toward

    def hook_floor(self):
        """The lowest place a hook's peak may sit: a share of the range above the home note, which a written hook's Height gauge
        moves, so that every other line, held under it, makes room as the hook is set lower."""
        written = self.written()
        if written is None:
            return self.within(self._home + round(self._habits[SPAN] * HOOK_FLOOR_SHARE))
        share = LOWEST_FLOOR_SHARE + hook_writing.share(written[1][hook_writing.HEIGHT]) * (HIGHEST_FLOOR_SHARE - LOWEST_FLOOR_SHARE)
        # However low the hook is set, the melodies under it keep room to move.
        return self.within(max(self._home + round(self._habits[SPAN] * share), self._low + VERSE_ROOM))

    def chord_place(self, *, chord, lowest, highest, toward):
        """The place of the chord's note nearest a place wanted, between two places, or the place wanted where the chord has none there."""
        places = [place for place in range(max(self._low, lowest), min(self._high, highest) + 1) if self.in_chord(place=place, chord=chord)]
        if not places:
            return self.within(max(lowest, min(highest, toward)))
        return min(places, key=lambda place: (abs(place - toward), -place))

    def hook_rhythm(self, dice):
        """A hook's bar: the lengths of its short notes, of its long one and of the unit they are counted in. The Notes gauge says how few the short notes are."""
        unit = self._grid // HOOK_UNITS if self._grid % HOOK_UNITS == 0 else 1
        head = max(FEWEST_SHORT_NOTES, round(self._grid * HOOK_HEAD_SHARE / unit))
        figures = short_note_figures(head)
        wanted = self.gauge(GAUGE_NOTES) * (len(figures) - 1)
        nearest = sorted(range(len(figures)), key=lambda place: (abs(place - wanted), place))[:HOOK_DECK]
        figure = figures[dice.choice(nearest)]
        return [length * unit for length in figure], self._grid - head * unit, unit

    def reached(self, *, count, peak, dice):
        """The places of a figure's short notes, which reach the peak one of four ways."""
        reach = dice.choice(REACHES)
        if reach == REACH_REPEATED:
            return [self.within(peak - dice.choice(LEAPS_INTO_PEAK))] * count
        if reach == REACH_CLIMB:
            return [self.within(peak - min(count - place, FARTHEST_CLIMB)) for place in range(count)]
        if reach == REACH_DIP:
            return [self.within(peak - min(place, FARTHEST_DIP)) for place in range(count)]
        return [self.within(peak - 1 - (count - 1 - place) % 2) for place in range(count)]

    def answer_bar(self, *, short, long, unit, peak, chord, dice):
        """The bar after a hook's figure: the figure's short notes in the opposite order and a long note that leaves a breath, falling from under the peak to a note of the chord."""
        rhythm = [{notation.STEPS: length} for length in reversed(short)]
        rhythm += [{notation.STEPS: long - unit}, {notation.REST: unit}] if long > unit else [{notation.STEPS: long}]
        highest = self._high
        self._high = max(self._low, peak - 1)
        try:
            return self.walked(rhythm=rhythm, centre=self.within(peak - ANSWER_BELOW), shape=SHAPE_TUMBLE, under=[chord], dice=dice)
        finally:
            self._high = highest

    def hook_line(self, *, under, dice):
        """A hook: the figure, ending on the peak, in the first bar of the line and each second bar after, and an answer to it in the bars between."""
        if self._habits.get(HOOK_NOTES):
            return copy.deepcopy(self._habits[HOOK_NOTES])
        if self.written() is not None:
            return self.written_line(under=under, dice=dice)
        floor = self.hook_floor()
        peak = self.chord_place(chord=under[0], lowest=floor, highest=self._high, toward=floor + 1)
        short, long, unit = self.hook_rhythm(dice)
        head = self.reached(count=len(short), peak=peak, dice=dice)
        notes = []
        for bar, chord in enumerate(under):
            if bar % 2:
                notes.extend(self.answer_bar(short=short, long=long, unit=unit, peak=peak, chord=chord, dice=dice))
                continue
            notes.extend({**self._ladder[place][1], notation.STEPS: length} for place, length in zip(head, short))
            ending = peak if bar == 0 else self.chord_place(chord=chord, lowest=floor, highest=self._high, toward=peak)
            notes.append({**self._ladder[ending][1], notation.STEPS: long})
        return notes

    def varied_hook(self, *, line, under):
        """A hook heard before with its last note risen to a note of the chord at or above its peak."""
        sounds = [note for note in line if notation.REST not in note]
        peak = max(self.place_of(note) for note in sounds)
        ending = self.chord_place(chord=under[-1], lowest=peak, highest=self._high, toward=peak + 1)
        for field in PITCH_FIELDS + (notation.STRESS,):
            sounds[-1].pop(field, None)
        sounds[-1].update(self._ladder[ending][1])
        return line


class Tags(Hooks):
    """What makes a song's second hook, its tag: one bar of a few short notes on one pitch and its neighbour, said the same in
    every bar of its line, under the main hook's top and unlike the main hook in rhythm, so that the two are never mistaken."""

    __slots__ = ('_tag_take',)

    def set_tag_take(self, take):
        self._tag_take = take

    def tag_rhythm(self):
        """The tag's bar of lengths: the next of the choppy rhythms that the main hook does not have, each take another."""
        written = self.written()
        taken = tuple(written[2][0]) if written is not None else None
        free = [name for name in TAG_RHYTHMS if hook_kinds.RHYTHMS[name] != taken]
        order = random.Random(TAG_SEED.format(self._song_seed, 'rhythms')).sample(free, len(free))
        return hook_kinds.RHYTHMS[order[self._tag_take % len(order)]]

    def tag_line(self, *, under):
        """A tag: its bar in every bar of the line, the last note of each bar cut for a breath."""
        unit = self._grid // hook_kinds.UNITS
        lengths = self.tag_rhythm()
        top = self.chord_place(chord=under[0], lowest=self._low, highest=max(self._low, self.hook_floor() - TAG_BELOW), toward=self.hook_floor() - TAG_BELOW)
        # The main hook chants where its behavior is a chant, and the tag then rocks between two notes; under any other hook the tag chants.
        written = self.written()
        chants = written is not None and written[0] == hook_writing.CHANT
        contour = hook_kinds.ROCKING if chants else hook_kinds.CHANT
        depths = iter(hook_kinds.depths_of(contour=contour, count=sum(1 for length in lengths if length > 0)))
        last = max(place for place, length in enumerate(lengths) if length > 0)
        bar = []
        for place, length in enumerate(lengths):
            if length < 0:
                bar.append({notation.REST: -length * unit})
                continue
            note = self._ladder[self.within(top - next(depths))][1]
            if place == last and length > 1:
                bar += [{**note, notation.STEPS: (length - 1) * unit}, {notation.REST: unit}]
            else:
                bar.append({**note, notation.STEPS: length * unit})
        return [copy.deepcopy(cell) for _ in under for cell in bar]


class Bodies(Hooks):
    """What makes the body of a chorus, its lines that are no hook: each on the hook's rhythm or a plainer form of it, never a
    rhythm more striking than the hook's, and always under the hook's floor. The line before a hook climbs and ends open, so
    that the hook is wanted; the section's last line falls and ends on the home note. Five gauges say the rest."""

    __slots__ = ()

    def can_write(self):
        return hook_writing.BODY_WRITING in self._habits and self.written() is not None

    def ceiling(self, gauges):
        """The highest place a line of the body reaches: under the hook's floor, and lower the lower the Lift gauge stands."""
        return max(self._low, self.hook_floor() - 1 - round((1 - hook_writing.share(gauges[hook_writing.LIFT])) * hook_writing.LIFT_ROOM))

    def body_rhythm(self, *, bars, gauges):
        """A line's rhythm: the hook's bar in as many of its bars as the Sameness gauge says, and a plainer form of it in the rest."""
        lengths = self.written()[2][0]
        unit = self._grid // hook_writing.UNITS
        same = round(hook_writing.share(gauges[hook_writing.SAMENESS]) * bars)
        rhythm = []
        for bar in range(bars):
            rhythm += [{notation.REST: -length * unit} if length < 0 else {notation.STEPS: length * unit} for length in (lengths if bar < same else hook_writing.plainer(lengths))]
        return rhythm

    def breath(self):
        """The silence a line of the body ends in, in eighths of a bar, as the Space gauge says."""
        return round(hook_writing.share(hook_writing.body_ways(self._habits)[hook_writing.SPACE]) * hook_writing.MOST_SPACE)

    def home_under(self, *, highest, toward):
        """Where a section comes to rest: the note of the home chord nearest a place wanted and no higher than a place."""
        places = [place for place in range(self._low, max(self._low, highest) + 1) if self.in_chord(place=place, chord=HOME_CHORD)]
        return min(places, key=lambda place: (abs(place - toward), place)) if places else self.within(min(highest, toward))

    def leading_place(self, *, highest, toward):
        """Where a line that leads into the hook ends: the nearest note that asks for more, no higher than a place."""
        places = [place for place in range(self._low, min(self._high, highest) + 1) if self._ladder[place][1][notation.DEGREE] in LEADING_DEGREES and notation.ACCIDENTAL not in self._ladder[place][1]]
        return min(places, key=lambda place: (abs(place - toward), -place)) if places else self.open_place(lowest=self._low, highest=highest, toward=toward)

    def unsettled_place(self, *, chord, highest, toward):
        """The place nearest one wanted that is no note of the chord, an open note of the scale before any other, so that an
        ending left open is never the ending a settled line would have."""
        places = [place for place in range(self._low, min(self._high, highest) + 1) if not self.in_chord(place=place, chord=chord)]
        if not places:
            return self.open_place(lowest=self._low, highest=highest, toward=toward)
        return min(places, key=lambda place: (self._ladder[place][1][notation.DEGREE] not in OPEN_DEGREES, abs(place - toward), -place))

    def ended(self, *, line, entry, under, gauges, answers=False):
        """A line of the body with its last note where the line's place asks: open before a hook, a note of the home chord at the
        section's close, and otherwise settled on a note of the chord or left open as the Resolve gauge says; a line that answers settles."""
        sounds = [note for note in line if notation.REST not in note]
        highest = self.ceiling(gauges)
        now = min(self.place_of(sounds[-1]), highest)
        if entry.get(LEADS_TO_HOOK):
            place = self.leading_place(highest=highest, toward=now)
        elif entry.get(CLOSES):
            place = self.home_under(highest=highest, toward=now)
        elif answers or gauges[hook_writing.RESOLVE] >= hook_writing.SETTLED_FROM:
            place = self.held_under(highest=highest, made=lambda: self.chord_place(chord=under[-1], lowest=self._low, highest=highest, toward=now))
        else:
            place = self.unsettled_place(chord=under[-1], highest=highest, toward=now)
        for field in PITCH_FIELDS + (notation.STRESS,):
            sounds[-1].pop(field, None)
        sounds[-1].update(self._ladder[place][1])
        return line

    def body_line(self, *, entry, under, dice):
        """A line of the body nobody has heard yet: it climbs before a hook, falls at the section's close, and arches otherwise."""
        gauges = hook_writing.body_ways(self._habits)
        highest = self.ceiling(gauges)
        shape = SHAPE_CLIMB if entry.get(LEADS_TO_HOOK) else SHAPE_TUMBLE if entry.get(CLOSES) else SHAPE_ARCH
        line = self.held_between(lowest=highest - BODY_DEPTH, highest=highest, made=lambda: self.walked(rhythm=self.body_rhythm(bars=len(under), gauges=gauges), centre=self.within(highest - BODY_BELOW), shape=shape, under=under, dice=dice))
        return self.ended(line=self.reaching(line=line, highest=highest), entry=entry, under=under, gauges=gauges)

    def reaching(self, *, line, highest):
        """A line moved up whole until its highest note is the highest place the body reaches, so that the Lift gauge is heard in
        every line; a line already there is left."""
        sounds = [note for note in line if notation.REST not in note]
        up = highest - max(self.place_of(note) for note in sounds)
        if up <= 0:
            return line
        for note in sounds:
            place = self.place_of(note) + up
            for field in PITCH_FIELDS:
                note.pop(field, None)
            note.update(self._ladder[place][1])
        return line

    def held_between(self, *, lowest, highest, made):
        """What makes a line, run with the lowest and the highest place the writer reaches set to two places."""
        kept = self._low
        self._low = max(kept, min(lowest, self._high))
        try:
            return self.held_under(highest=highest, made=made)
        finally:
            self._low = kept

    def varied_body(self, *, line, entry, under, dice):
        """A line of the body heard before: high on the Call and answer gauge it answers, the same notes with a settled ending;
        low on it the line's tail is walked anew."""
        gauges = hook_writing.body_ways(self._habits)
        if gauges[hook_writing.CALL_AND_ANSWER] >= hook_writing.ANSWERS_FROM:
            return self.ended(line=line, entry=entry, under=under, gauges=gauges, answers=True)
        again = self.held_between(lowest=self.ceiling(gauges) - BODY_DEPTH, highest=self.ceiling(gauges), made=lambda: self.varied_line(line=line, dice=dice, entry=entry, under=under))
        return self.ended(line=again, entry=entry, under=under, gauges=gauges)


# A line of a chorus's body turns about a place this far under the highest place it reaches.
BODY_BELOW = 1
# A line of the body goes no lower than this far under the highest place it reaches, so that a chorus stays above its verse.
BODY_DEPTH = 4
TONIC = 1
HOME_CHORD = {notation.DEGREE: TONIC}
# The notes a line that leads into the hook may end on: each asks for more.
LEADING_DEGREES = (2, 5, 6, 7)


def can_tag(grid):
    """Whether a tag can be written on a bar counted in so many steps: its rhythms are of eight units."""
    return grid % hook_kinds.UNITS == 0


class Hooked(StepWalk):
    """A writer with a hook: a line the plan marks as its section's hook is the hook maker's, a line marked as the song's tag is
    the tag maker's, and every other line is the writer's, any engine's, held under the lowest place the hook's top may sit
    unless the line is marked higher, so that the hook's long note is the top of the song."""

    __slots__ = ('_writer', '_hooks', '_take_seed', '_tags', '_bodies')

    def __init__(self, *, writer, habits, chords, scale_type, seed, answers, voice=None, letters=(), hook_take=FIRST_HOOK_TAKE, tag_take=FIRST_HOOK_TAKE):
        super().__init__(habits=habits, chords=chords, scale_type=scale_type, seed=seed, answers=answers, voice=voice, letters=letters)
        self._writer = writer(habits=habits, chords=chords, scale_type=scale_type, seed=seed, answers=answers, voice=voice, letters=letters)
        self._hooks = Hooks(habits=habits, chords=chords, scale_type=scale_type, seed=seed, answers=answers, voice=voice, letters=letters)
        self._hooks.set_take(hook_take)
        self._tags = Tags(habits=habits, chords=chords, scale_type=scale_type, seed=seed, answers=answers, voice=voice, letters=letters)
        self._tags.set_take(hook_take)
        self._tags.set_tag_take(tag_take)
        self._bodies = Bodies(habits=habits, chords=chords, scale_type=scale_type, seed=seed, answers=answers, voice=voice, letters=letters)
        self._bodies.set_take(hook_take)
        # Each line's dice are drawn as the writer draws them, so that a line the writer makes is the line the writer would make alone, lowered.
        self._seed = self._writer.get_seed()
        # The first take of the hook is rolled with its line's dice, as every song made before takes could be asked for; a later take with dice of its own.
        self._take_seed = None if hook_take == FIRST_HOOK_TAKE else HOOK_TAKE_SEED.format(seed, hook_take)

    def under_the_hook(self, *, entry, made):
        if entry.get(HIGHER):
            return made()
        return self._writer.held_under(highest=self._hooks.hook_floor() - 1, made=made)

    def sketched(self, plan):
        """A section's tune, the lines of a chorus's body marked as such where the body is written by its gauges: each line that
        is no hook, in a section with a hook, with whether a hook follows it and whether it closes the section."""
        if not self._bodies.can_write() or not has_hook(plan) or isinstance(self._writer, WRITERS_OF_THEIR_OWN) or self._answers:
            return super().sketched(plan)
        marked = []
        for place, entry in enumerate(plan):
            entry = dict(entry)
            if not (entry.get(HOOK) or entry.get(TAG) or entry.get(LINE_NOTES) or entry.get(ANSWER)):
                entry[BODY] = True
                if place + 1 < len(plan) and plan[place + 1].get(HOOK):
                    entry[LEADS_TO_HOOK] = True
                elif place + 1 == len(plan):
                    entry[CLOSES] = True
            marked.append(entry)
        return super().sketched(marked)

    def body_breath(self, *, entry, count, line):
        """A line of a chorus's body ends in the silence its Space gauge gives, a shorter line in a little more, and never in
        so much that fewer than half of its notes are left."""
        if not entry.get(BODY):
            return None
        ways = self._habits[BREATHES] if isinstance(self._habits.get(BREATHES), dict) else {}
        shorter = is_shorter(count=count, lengths=ways.get(phrasing.LINE_LENGTHS, phrasing.USUAL_WAYS[phrasing.LINE_LENGTHS]))
        eighth = self._grid // phrasing.EIGHTHS_IN_BAR
        least = (sounds_in(line) + 1) // 2
        wanted = self._bodies.breath() + (SHORTER_LINE_BREATH if shorter else phrasing.NO_BREATH)
        return next((breath for breath in range(wanted, phrasing.NO_BREATH, -1) if sounds_in(ended_early(line=line, breath=breath * eighth)) >= least), phrasing.NO_BREATH)

    def finished(self, *, line, entry, under):
        """A line of a chorus's body ends where its place asks after its breath too, since the breath may take the line's last note."""
        return self._bodies.ended(line=line, entry=entry, under=under, gauges=hook_writing.body_ways(self._habits)) if entry.get(BODY) else line

    def new_line(self, *, entry, under, dice):
        if entry.get(TAG) and can_tag(self._grid):
            return self._tags.tag_line(under=under)
        if entry.get(BODY):
            return self._bodies.body_line(entry=entry, under=under, dice=dice)
        if entry.get(HOOK):
            return self._hooks.hook_line(under=under, dice=dice if self._take_seed is None else random.Random(self._take_seed))
        return self.under_the_hook(entry=entry, made=lambda: self._writer.new_line(entry=entry, under=under, dice=dice))

    def varied_line(self, *, line, dice, entry=None, under=None):
        if (entry or {}).get(TAG):
            # A tag comes back the same every time.
            return line
        if (entry or {}).get(HOOK):
            return self._hooks.varied_hook(line=line, under=under)
        if (entry or {}).get(BODY):
            return self._bodies.varied_body(line=line, entry=entry, under=under, dice=dice)
        return self.under_the_hook(entry=entry or {}, made=lambda: self._writer.varied_line(line=line, dice=dice, entry=entry, under=under))


def same_note(*, one, other):
    return one[notation.DEGREE] == other[notation.DEGREE] and one.get(notation.ACCIDENTAL) == other.get(notation.ACCIDENTAL)


def twelve_notes(scale_type):
    """All twelve notes within an octave, each written as a note of the scale or as the scale note below it, sharpened."""
    steps = HALF_STEPS[scale_type]
    notes = []
    for half_steps in range(NOTES_IN_OCTAVE):
        if half_steps in steps:
            notes.append({notation.DEGREE: steps.index(half_steps) + 1})
        else:
            notes.append({notation.DEGREE: steps.index(half_steps - 1) + 1, notation.ACCIDENTAL: notation.SHARP})
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
# The writers whose lines are their own throughout, a chorus's body included: a row or an evolving idea is the whole of the tune.
WRITERS_OF_THEIR_OWN = (Serial, Evolving)
FORMS = (row_as_written, row_backwards, row_upside_down, row_upside_down_and_backwards)
ENGINES = {STEP_WALK: StepWalk, SERIAL: Serial, EVOLVING: Evolving, SMART: Smart}


# The lines of each melody asked for, and how many are kept before all are forgotten, so that they cannot pile up for ever.
LINES_KEPT = {}
MOST_LINES_KEPT = 5000


def sketched(*, habits, plan, chords, scale_type, seed, answers, engine=None, voice=None, letters=(), hook=False, hook_take=FIRST_HOOK_TAKE, tag_take=FIRST_HOOK_TAKE):
    """A section's tune as lines, written by the engine named, else the one the habits name, else the step walk; in a song
    with a hook, the lines a plan marks as a hook are the hook maker's and the writer keeps under them in every section. The
    letters are those of every line of the song the player plays, for an engine that tells a song's lines apart."""
    # The lines follow from what is asked and from nothing else, and the wizard makes a great many songs that differ in one
    # choice and share most of their melodies, so the lines of each asking are written once and kept; each asker gets lines
    # of its own to change.
    key = repr((habits, plan, chords, scale_type, seed, answers, engine, voice, letters, hook, hook_take, tag_take))
    if key not in LINES_KEPT:
        if len(LINES_KEPT) >= MOST_LINES_KEPT:
            LINES_KEPT.clear()
        writer = ENGINES[engine or habits.get(ENGINE, STEP_WALK)]
        given = dict(habits=habits, chords=chords, scale_type=scale_type, seed=seed, answers=answers, voice=voice, letters=letters)
        made_by = Hooked(writer=writer, hook_take=hook_take, tag_take=tag_take, **given) if hook else writer(**given)
        LINES_KEPT[key] = made_by.sketched(plan)
    return copy.deepcopy(LINES_KEPT[key])


def plan_as_asked(*, plan, height=None, busy=None, repeats=None):
    """A section's plan as a song asks for its melody: every line sitting high, in the middle or low; every line so busy; and
    the lines that are no hook repeating a lot, each then the section's first line with the last varied, or a little, each then
    a line of its own. What is not asked is left as the plan has it."""
    firsts = {}
    first_places = {}
    lasts = {}
    for place, entry in enumerate(plan):
        if not entry.get(HOOK):
            firsts.setdefault(bool(entry.get(ANSWER)), entry.get(LINE, str(place)))
            first_places.setdefault(bool(entry.get(ANSWER)), place)
            lasts[bool(entry.get(ANSWER))] = place
    asked = []
    for place, entry in enumerate(plan):
        entry = dict(entry)
        if height is not None:
            entry.pop(HIGHER, None)
            entry.pop(LOWER, None)
            if height != MIDDLE:
                entry[HIGHER if height == HIGH else LOWER] = True
        if busy is not None:
            entry[LINE_BUSY] = busy
        if not entry.get(HOOK) and not entry.get(LINE_NOTES) and repeats in (REPEATS_A_LITTLE, REPEATS_A_LOT):
            entry.pop(VARIED, None)
            answers = bool(entry.get(ANSWER))
            if repeats == REPEATS_A_LOT:
                entry[LINE] = firsts[answers]
                if place == lasts[answers] and place != first_places[answers]:
                    entry[VARIED] = True
            else:
                entry[LINE] = LINE_OF_ITS_OWN.format(letter=entry.get(LINE, str(place)), place=place)
        asked.append(entry)
    return asked


def placement_of(plan):
    """Where the hook sits among a section's four lines, by name, or None for a plan of another shape."""
    marked = tuple(bool(entry.get(HOOK)) for entry in plan)
    return next((name for name, places in PLACED.items() if places == marked), None)


def plan_with_hook_placed(*, plan, placement):
    """A section's plan of four lines with its hook moved to another place among them: said first three times and closed, led
    to by three plainer lines, or said first and last with two plainer lines between. The lines that are no hook are plain,
    never lifted, so that the hook keeps the top. A plan of another shape is left as it is."""
    if placement_of(plan) in (None, placement) or placement not in PLACED:
        return plan
    hook = notation.without_fields(entry=next(entry for entry in plan if entry.get(HOOK)), fields=(VARIED,))
    plain = {field: hook[field] for field in (ANSWER,) if field in hook}
    if placement == FIRST_LINES:
        return [dict(hook), {**hook, VARIED: True}, dict(hook), {**plain, LINE: CLOSE_LINE}]
    if placement == LAST_LINE:
        return [{**plain, LINE: TOWARD_LINE}, {**plain, LINE: TOWARD_LINE, VARIED: True}, {**plain, LINE: TURN_LINE}, dict(hook)]
    return [dict(hook), {**plain, LINE: TOWARD_LINE}, {**plain, LINE: TOWARD_LINE, VARIED: True}, dict(hook)]


def plan_with_tag(*, plan, lines):
    """A section's plan with the song's tag in it: the last line of a plan that has lines, the lines before it kept, or, in a
    section with no lines of its own, so many lines of the tag."""
    tag = {LINE: TAG_LINE, TAG: True}
    if not plan:
        return [dict(tag) for _ in range(max(lines, 1))]
    return [*plan[:-1], {**{field: plan[-1][field] for field in (ANSWER,) if field in plan[-1]}, **tag}]


def has_hook(plan):
    """Whether any line of a section's plan is marked as the section's hook."""
    return any(entry.get(HOOK) for entry in plan)


def pitch_of(note):
    """Return a note's pitch alone: its fields that say the pitch, in PITCH_FIELDS' order."""
    return {field: note[field] for field in PITCH_FIELDS if field in note}
