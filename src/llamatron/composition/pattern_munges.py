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

"""The munges of a pattern that work on its notes: joining and dividing them, moving them among the rests, and changing their pitches and loudness.

PatternMunges is the part of Pattern that holds these, each one edit of the whole pattern that
the pattern editor's Munge dialog offers. The munges that only reorder, copy or blank steps are
on Pattern itself.
"""

from llamatron.composition import limits
from llamatron.composition.file_format import ACCIDENTALS, PATTERN_ROWS, PITCH_ROWS, Row
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.row_descriptions import row_described, rows_where
from llamatron.music import midi
from llamatron.strings import errors
from llamatron.support.random_source import random_source
from llamatron.support.revised import notes_change

# What makes a step's note, which a rest holds none of: every row but the ones a rest keeps.
REST_ROWS = rows_where(lambda row: row.is_kept_by_a_rest())
SOUND_ROWS = [row for row in PATTERN_ROWS if row not in REST_ROWS]
# The octaves a chord may be moved by when voice leading may move one: none first, so that a tie keeps the octave written.
OCTAVE_SHIFTS = (0, -1, 1)
NO_SHIFT = (0,)
# What says how long a note lasts, which a note made of another's steps takes none of.
LENGTH_ROWS = (Row.GATE, Row.DOT, Row.TIE)


def blank_of(row):
    return row_described(row).blank()


def own_value(value):
    """Return a step's value as another step may hold it, a list copied."""
    return list(value) if isinstance(value, list) else value


class PatternMunges:
    """What a Pattern knows about munging its notes."""

    __slots__ = ()

    def _held(self, *, row, step):
        values = self._rows[row]
        return blank_of(row) if values is None else values[step]

    def _hold(self, *, row, step, value):
        """Put a value on a step with no check, for a value another step of this pattern already held."""
        if self._rows[row] is None:
            if value == blank_of(row):
                return
            self._rows[row] = [blank_of(row)] * self.get_steps()
        self._rows[row][step] = own_value(value)

    def _pitch(self, step):
        """Return what a step plays, apart from how long and how loud: its degree, octave, sharp or flat and chord."""
        return [own_value(self._held(row=row, step=step)) for row in PITCH_ROWS]

    def _written_notes(self):
        """Return the steps that hold a note of their own, leaving out a step that only grabs one."""
        return [step for step in range(self.get_steps()) if self._held(row=Row.DEGREE, step=step) is not None]

    @notes_change
    def join_repeated_notes(self):
        """Make one long note of each run of steps next to each other that play the same pitch: the first keeps the note, and each after it becomes a tie."""
        start = None
        for step in range(self.get_steps()):
            if self._held(row=Row.TIE, step=step):
                continue
            if self._held(row=Row.DEGREE, step=step) is None or self._held(row=Row.GRAB, step=step):
                start = None
            elif start is not None and self._pitch(step) == self._pitch(start):
                for row in SOUND_ROWS:
                    self._hold(row=row, step=step, value=blank_of(row))
                self._hold(row=Row.TIE, step=step, value=True)
                # The joined note lasts through its ties, whatever gate its first step had.
                self._hold(row=Row.GATE, step=start, value=blank_of(Row.GATE))
                self._hold(row=Row.DOT, step=start, value=blank_of(Row.DOT))
            else:
                start = step

    @notes_change
    def divide_long_notes(self, *, step_size):
        """Make a note of every step a long note covers, by its ties or its gate: each takes the first step's pitch, loudness and the rest, and lasts one step."""
        covering = self.covering_notes(step_size=step_size)
        for step, start in covering.items():
            if step == start:
                continue
            for row in SOUND_ROWS:
                self._hold(row=row, step=step, value=blank_of(row) if row in LENGTH_ROWS else self._held(row=row, step=start))
            self._hold(row=Row.GATE, step=start, value=blank_of(Row.GATE))
            self._hold(row=Row.DOT, step=start, value=blank_of(Row.DOT))

    def randomize_rhythm(self):
        """Move the notes earlier and later among the rests, at random: the notes keep their order and their lengths, and every rest is still there, somewhere else."""
        notes = []
        rests = []
        step = 0
        while step < self.get_steps():
            end = self.tied_end(step) if self.has_sound(step) else step + 1
            (notes if self.has_sound(step) else rests).append(list(range(step, end)))
            step = end
        is_note = [True] * len(notes) + [False] * len(rests)
        random_source(None).shuffle(is_note)
        notes_left = iter(notes)
        rests_left = iter(rests)
        self.rearrange([step for note in is_note for step in next(notes_left if note else rests_left)])

    @notes_change
    def _repitch(self, pitches):
        """Give the steps that hold a note new pitches, one each, in order."""
        for step, pitch in zip(self._written_notes(), pitches):
            for row, value in zip(PITCH_ROWS, pitch):
                self._hold(row=row, step=step, value=value)

    def randomize_pitches(self):
        """Shuffle which pitch each note plays, leaving the rhythm, the lengths and the loudness where they are."""
        pitches = [self._pitch(step) for step in self._written_notes()]
        random_source(None).shuffle(pitches)
        self._repitch(pitches)

    def reverse_pitches(self):
        """Play the pitches in backwards order on the same rhythm."""
        self._repitch([self._pitch(step) for step in reversed(self._written_notes())])

    def clear_every(self, every):
        """Make a rest of every so many steps, counting from the first: with 4, the fourth, the eighth and on."""
        if type(every) is not int or not limits.MIN_STEPS <= every <= self.get_steps():
            raise InvalidValue(errors.ERR_MUNGE_NUMBER_OUT_OF_RANGE.format(low=limits.MIN_STEPS, high=self.get_steps()))
        for step in range(every - 1, self.get_steps(), every):
            self.clear_sound(step)

    @notes_change
    def transpose(self, degrees):
        """Move every note so many degrees up the scale, or down for a negative number; a drum pattern, or a note that would pass under the lowest degree, refuses it all."""
        notes = self._written_notes()
        if self.is_drum():
            raise InvalidValue(errors.ERR_TRANSPOSE_DRUMS)
        if type(degrees) is not int or any(self._held(row=Row.DEGREE, step=step) + degrees < limits.MIN_DEGREE for step in notes):
            raise InvalidValue(errors.ERR_TRANSPOSE_TOO_LOW.format(lowest=limits.MIN_DEGREE))
        for step in notes:
            self._rows[Row.DEGREE][step] += degrees

    @notes_change
    def humanize_velocity(self, most):
        """Move each typed velocity by a random amount, at most so much up or down, kept to what a velocity may be; a blank velocity stays blank."""
        velocities = self._rows[Row.VELOCITY] or []
        for step, velocity in enumerate(velocities):
            if velocity is not None:
                moved = velocity + random_source(None).randint(-most, most)
                velocities[step] = min(max(moved, midi.MIN_VELOCITY), midi.MAX_VELOCITY)

    @notes_change
    def invert_melody(self, *, step, scale_size, default_octave):
        """Mirror every note around the pitch of a step's note, by degrees of a scale of so many notes: a note two degrees above ends two below.

        A note that leaves the scale's degrees is written in the octave it lands in, counted from
        the default octave where its step had none. Nothing changes when a drum pattern, a step
        with no note or an octave out of range refuses it.
        """
        if self.is_drum() or self._held(row=Row.DEGREE, step=step) is None:
            raise InvalidValue(errors.ERR_INVERT_NEEDS_A_NOTE)

        def octave_of(note):
            written = self._held(row=Row.OCTAVE, step=note)
            return default_octave if written is None else written

        def place(note):
            return octave_of(note) * scale_size + self._held(row=Row.DEGREE, step=note) - limits.MIN_DEGREE
        mirrored = {}
        for note in self._written_notes():
            octaves, degree = divmod(2 * place(step) - place(note) - octave_of(note) * scale_size, scale_size)
            if not limits.MIN_OCTAVE <= octave_of(note) + octaves <= limits.MAX_OCTAVE:
                raise InvalidValue(errors.ERR_INVERT_OUT_OF_RANGE)
            mirrored[note] = (degree + limits.MIN_DEGREE, octaves)
        for note, (degree, octaves) in mirrored.items():
            if octaves:
                self._hold(row=Row.OCTAVE, step=note, value=octave_of(note) + octaves)
            self._hold(row=Row.DEGREE, step=note, value=degree)

    def _chord_pitches(self, *, step, scale, default_octave):
        """Return a step's chord in root position as half steps, the root first and the notes above it in the order the chord is built, or an empty list for a step with no chord."""
        written = self._held(row=Row.OCTAVE, step=step)
        octave = default_octave if written is None else written
        root = (self._held(row=Row.DEGREE, step=step), octave, self._held(row=Row.ACCIDENTAL, step=step))
        inversion = self._held(row=Row.INVERSION, step=step)
        self._hold(row=Row.INVERSION, step=step, value=blank_of(Row.INVERSION))
        tones = self.chord_tones(step=step, octave=octave, scale=scale)
        self._hold(row=Row.INVERSION, step=step, value=inversion)
        return [half_steps_of(tone=tone, scale=scale) for tone in (root, *tones)] if tones else []

    @notes_change
    def apply_voice_leading(self, *, scale, default_octave, octaves=False):
        """Give every chord after the first the inversion that moves its notes the least from the chord before, and with octaves, the octave one lower or higher where that is nearer still; return how many chords were looked at.

        The first chord stays as written. A chord's Inversion cell is blanked where root position
        is nearest. The scale is the NamedScale the chords are measured in.
        """
        before = None
        chords = 0
        for step in self._written_notes():
            pitches = self._chord_pitches(step=step, scale=scale, default_octave=default_octave)
            if not pitches:
                continue
            chords += 1
            if before is None:
                before = sorted(inverted(pitches=pitches, inversion=self._held(row=Row.INVERSION, step=step) or 0))
                continue
            written = self._held(row=Row.OCTAVE, step=step)
            octave = default_octave if written is None else written
            choices = [
                (movement(pitches=voiced(pitches=pitches, inversion=inversion, shift=shift), before=before), place, inversion, shift)
                for place, (shift, inversion) in enumerate((shift, inversion) for shift in (OCTAVE_SHIFTS if octaves else NO_SHIFT) for inversion in (0, *limits.INVERSIONS))
                if inversion < len(pitches) and limits.MIN_OCTAVE <= octave + shift <= limits.MAX_OCTAVE
            ]
            _, _, inversion, shift = min(choices)
            self._hold(row=Row.INVERSION, step=step, value=inversion or blank_of(Row.INVERSION))
            if shift:
                self._hold(row=Row.OCTAVE, step=step, value=octave + shift)
            before = sorted(voiced(pitches=pitches, inversion=inversion, shift=shift))
        return chords


def half_steps_of(*, tone, scale):
    """Return a note, given as a degree, an octave and an accidental, as half steps in a scale."""
    degree, octave, accidental = tone
    steps = scale.get_half_steps()
    octaves_up, place = divmod(degree - limits.MIN_DEGREE, len(steps))
    return (octave + octaves_up) * midi.HALF_STEPS_PER_OCTAVE + steps[place] + ACCIDENTALS.get(accidental, 0)


def inverted(*, pitches, inversion):
    """Return a chord's pitches as an inversion plays them: so many of its first notes an octave up, never all of them."""
    moved = min(inversion, len(pitches) - 1)
    return [pitch + midi.HALF_STEPS_PER_OCTAVE if place < moved else pitch for place, pitch in enumerate(pitches)]


def voiced(*, pitches, inversion, shift):
    """Return a chord's pitches in an inversion, moved so many octaves."""
    return [pitch + shift * midi.HALF_STEPS_PER_OCTAVE for pitch in inverted(pitches=pitches, inversion=inversion)]


def movement(*, pitches, before):
    """Return how far a voicing's notes are from the chord before: lowest to lowest when both have as many notes, and otherwise each note to the nearest of the chord before."""
    now = sorted(pitches)
    if len(now) == len(before):
        return sum(abs(pitch - other) for pitch, other in zip(now, before))
    return sum(min(abs(pitch - other) for other in before) for pitch in now)
