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
"""A pattern's notes as a piano roll handles them: each note by the steps it covers, through ties or a gate.

The rows of a pattern hold a note on one step, a gate that says how long the note sounds, and
ties on the steps after it. A piano roll shows one bar for all of that, and its edits are in
terms of the bar: draw a note of some length, drag its end, cut it, erase it. PatternNotes is
the part of Pattern that knows how a bar is made of rows, so that anything can place and reshape
notes on a pattern with no tracker and no document: the piano roll does, and a wizard or a
generator that writes steps can.

How many steps a gate reaches depends on how long a step is, and a pattern's step size is bound
late: a pattern with none of its own takes the set's. So every method here that reads a gate as
steps takes step_size, the length of one step in whole notes, from whoever knows the set
(Setlist.get_pattern_step_size). Methods that take start mean the step a note starts on, which
covering_notes() finds from any step the note covers.

Every change is made through the pattern's own set_value and clear_sound, which check their
values and move the pattern's revision, so nothing here is written under @notes_change.
"""

from llamatron.composition.checks import fraction_text, written_length
from llamatron.composition.chords import borrowed, chord_half_steps
from llamatron.composition.file_format import ACCIDENTAL_CYCLE, ACCIDENTALS, FIXED_CHORDS, GATE_MODIFIERS, SCALE_CHORDS, Row
from llamatron.composition.limits import MAX_GATE, MIN_DEGREE
from llamatron.music.midi import HALF_STEPS_PER_OCTAVE
from llamatron.support.rational import Rational

# What a note's second half keeps of it when the piano roll's knife splits it: its pitch, chord and velocity.
SPLIT_ROWS = (Row.DEGREE, Row.ACCIDENTAL, Row.OCTAVE, Row.CHORD, Row.VELOCITY)
# A note covers at least the step it's on.
ONE_STEP = 1


def whole_steps_up(*, length, step_size):
    """Return how many whole steps a length takes, counting a part of a step as one, as a gate's reach is drawn."""
    steps = length / step_size
    whole = steps.numerator // steps.denominator
    return whole if whole * steps.denominator == steps.numerator else whole + 1


def whole_steps_down(*, length, step_size):
    """Return how many whole steps fit in a length, at least one, as an entry size is placed in ties."""
    steps = length / step_size
    return max(steps.numerator // steps.denominator, ONE_STEP)


class PatternNotes:
    """What a Pattern knows about its notes as bars: where each starts and ends, and how to draw, lengthen, shorten and cut one."""

    __slots__ = ()

    # Reading the notes.

    def holding_note(self, step):
        """Return the step of the note sounding through a step by ties: the step itself when it has a note, or the note the ties before it lead back to, or None."""
        self._check_step(step)
        while self.get_value(row=Row.DEGREE, step=step) is None:
            if not self.get_value(row=Row.TIE, step=step):
                return None
            step -= 1
            if step < 0:
                return None
        return step

    def tied_end(self, step):
        """Return the step after the last tie following a note's step, which is the step after the note when nothing ties to it."""
        self._check_step(step)
        end = step + 1
        while end < self.get_steps() and self.get_value(row=Row.TIE, step=end):
            end += 1
        return end

    def gate_length(self, step):
        """Return how long a step's note sounds by its gate and Dot row, in whole notes, or None when the gate is blank, which is one step."""
        self._check_step(step)
        gate = self.get_value(row=Row.GATE, step=step)
        if gate is None:
            return None
        length = written_length(value=gate, most=MAX_GATE)
        modifier = self.get_value(row=Row.DOT, step=step)
        return length if modifier is None else length * GATE_MODIFIERS[modifier]

    def note_span(self, *, step, step_size):
        """Return how many steps the note on a step covers on a piano roll: its ties, or its gate rounded up to whole steps, and any ties right after that."""
        end = self.tied_end(step)
        gate = self.gate_length(step)
        if gate is not None:
            reach = step + max(whole_steps_up(length=gate, step_size=step_size), ONE_STEP)
            end = max(end, min(reach, self.get_steps()))
            # A tie after the gate's reach holds the note on, as ties right after it do.
            while end < self.get_steps() and self.get_value(row=Row.TIE, step=end):
                end += 1
        return end - step

    def covering_notes(self, *, step_size):
        """Return the step of the note sounding through each step on a piano roll, by step, leaving out steps nothing covers.

        A note covers its own step, the steps tied to it, or the steps its gate reaches into, up to
        the next note, so a later note always shows over an earlier one's gate.
        """
        covering = {}
        for start in self.get_note_steps():
            for step in range(start, min(start + self.note_span(step=start, step_size=step_size), self.get_steps())):
                if step != start and self.has_sound(step):
                    break
                covering[step] = start
        return covering

    def partial_cell(self, *, step, step_size):
        """Return what part of a note's last cell its gate fills, when the gate ends inside a step, or None when the cell is full, so that a roll's bar ends where the sound does."""
        gate = self.gate_length(step)
        if gate is None:
            return None
        steps = gate / step_size
        whole = steps.numerator // steps.denominator
        if whole * steps.denominator == steps.numerator or whole + 1 != self.note_span(step=step, step_size=step_size):
            return None
        return Rational(steps.numerator - whole * steps.denominator, steps.denominator)

    def chord_tones(self, *, step, octave, scale):
        """Return the notes a step's chord adds above its own note, each as a degree, an octave and an accidental, for a piano roll's ghosts.

        A scale chord's tones are scale degrees above the step's, whatever the scale. A named
        chord's are half steps from the note, so they're placed in scale, the NamedScale the
        pattern plays under, and with a scale of None, which is a pattern whose scale isn't known,
        there are none. The octave is the step's, or the pattern's default when the step has none,
        which the caller knows.
        """
        symbol = self.get_value(row=Row.CHORD, step=step)
        degree = self.get_value(row=Row.DEGREE, step=step)
        if symbol is None or degree is None or self.is_drum():
            return []
        accidental = self.get_value(row=Row.ACCIDENTAL, step=step)
        symbol = str(symbol)
        tensions = self.get_value(row=Row.TENSION, step=step)
        kind = self.get_value(row=Row.CHORD_SCALE, step=step)
        if scale is not None and (tensions or kind):
            tones = _tones_leaving_the_scale(scale=scale, degree=degree, octave=octave, accidental=accidental, symbol=symbol, tensions=tensions, kind=kind)
        elif symbol in SCALE_CHORDS:
            tones = [(degree + above, octave, accidental) for above in SCALE_CHORDS[symbol] if above]
        elif scale is None:
            return []
        else:
            tones = [scale.degree_above(degree=degree, octave=octave, accidental=accidental, half_steps=half_steps) for half_steps in FIXED_CHORDS[symbol].value]
            tones = [tone for tone in tones if tone is not None]
        return _inverted_tones(root=(degree, octave, accidental), tones=tones, inversion=self.get_value(row=Row.INVERSION, step=step))

    # Changing the notes.

    def place_note(self, *, step, degree, octave, covered, gate=None, accidental=None):
        """Put a note on a step and tie the covered - 1 steps after it to it, as the piano roll places a note.

        Whatever the steps it covers held goes, so placing inside a held note cuts that note off
        where the new one starts, and what the old note held beyond the new one carries on as a
        note of its own at the old pitch, the user's decision of 2026-11-08, so that drawing a
        note never silences anything to its right. The gate is only for an entry size shorter
        than a step.
        """
        self._check_step(step)
        end = step + covered
        if end < self.get_steps() and self.get_value(row=Row.TIE, step=end):
            self.split_note(end)
        self.clear_sound(step)
        self.set_value(row=Row.DEGREE, step=step, value=degree)
        self.set_value(row=Row.OCTAVE, step=step, value=octave)
        self.set_value(row=Row.GATE, step=step, value=gate)
        self.set_value(row=Row.ACCIDENTAL, step=step, value=accidental)
        for later in range(step + 1, min(step + covered, self.get_steps())):
            self.clear_sound(later)
            self.set_value(row=Row.TIE, step=later, value=True)

    def draw_note(self, *, step, degree, octave, length, step_size, accidental=None):
        """Draw a note of a length on a step: in ties for each whole step it covers, or as a gate when it's shorter than a step, cutting the note it lands in.

        The length is in whole notes, like the entry size the piano roll draws with. On the step of a
        chord, the chord's root moves to the note and nothing else of the step changes (the user's
        rule): the chord, its tensions, scale and inversion and the note's length are kept, and
        erasing the note is what removes them.
        """
        if self.starts_chord(step):
            self.move_root(step=step, degree=degree, octave=octave, accidental=accidental)
            return
        self.cut_gate_before(step=step, step_size=step_size)
        if length < step_size:
            self.place_note(step=step, degree=degree, octave=octave, accidental=accidental, covered=ONE_STEP, gate=fraction_text(length))
        else:
            self.place_note(step=step, degree=degree, octave=octave, accidental=accidental, covered=whole_steps_down(length=length, step_size=step_size))

    def starts_chord(self, step):
        """Return whether a step holds a note of its own with a chord on it."""
        self._check_step(step)
        return self.get_value(row=Row.DEGREE, step=step) is not None and self.get_value(row=Row.CHORD, step=step) is not None

    def move_root(self, *, step, degree, octave, accidental=None):
        """Move a step's note to another pitch, leaving everything else of the step as it is."""
        self.set_value(row=Row.DEGREE, step=step, value=degree)
        self.set_value(row=Row.OCTAVE, step=step, value=octave)
        self.set_value(row=Row.ACCIDENTAL, step=step, value=accidental)

    def cut_gate_before(self, *, step, step_size):
        """Shorten the gate of the note reaching over a step so that it ends where the step starts, as a note drawn there cuts it, and return whether a gate was cut.

        A note that reaches the step by ties alone is left to place_note, which cuts the ties.
        """
        start = self.covering_notes(step_size=step_size).get(step)
        if start is None or start == step:
            return False
        gate = self.gate_length(start)
        if gate is None or start + whole_steps_up(length=gate, step_size=step_size) <= step:
            return False
        self.set_value(row=Row.GATE, step=start, value=fraction_text(step_size * (step - start)))
        self.set_value(row=Row.DOT, step=start, value=None)
        return True

    def split_note(self, step):
        """Make a tied step the start of a note of its own, at the pitch of the note it held, as the roll's knife does, and return whether it did.

        The ties after the step then hold the new note, so one long note becomes two that read as
        `█████│█████`.
        """
        start = self.holding_note(step)
        if start is None or start == step:
            return False
        for row in SPLIT_ROWS:
            self.set_value(row=row, step=step, value=self.get_value(row=row, step=start))
        self.set_value(row=Row.TIE, step=step, value=False)
        return True

    def lengthen_note(self, *, start, step_size):
        """Drag the end of the note starting on a step one step later, and return whether there was room.

        A note shorter than a step becomes a whole one first. Otherwise a step is tied on after
        its ties or its gate's reach, unless the pattern ends there or the next note starts.
        """
        gate = self.gate_length(start)
        if gate is not None and gate < step_size:
            self.set_value(row=Row.GATE, step=start, value=None)
            self.set_value(row=Row.DOT, step=start, value=None)
            return True
        end = start + self.note_span(step=start, step_size=step_size)
        if end >= self.get_steps() or self.has_sound(end):
            return False
        self.set_value(row=Row.TIE, step=end, value=True)
        return True

    def shorten_note(self, *, start, step_size):
        """Take the last tie off the note starting on a step, or a step off its gate when it has no ties, and return whether it could: a note of one step stays."""
        last = start + self.note_span(step=start, step_size=step_size) - 1
        if last > start and self.get_value(row=Row.TIE, step=last):
            self.set_value(row=Row.TIE, step=last, value=False)
            return True
        written = self.get_value(row=Row.GATE, step=start)
        if written is None:
            return False
        gate = written_length(value=written, most=MAX_GATE)
        if gate <= step_size:
            return False
        shorter = gate - step_size
        self.set_value(row=Row.GATE, step=start, value=None if shorter == step_size else fraction_text(shorter))
        return True

    def cycle_accidental(self, start):
        """Move the note starting on a step on to the next of natural, sharp and flat."""
        current = self.get_value(row=Row.ACCIDENTAL, step=start)
        following = ACCIDENTAL_CYCLE[(ACCIDENTAL_CYCLE.index(current) + 1) % len(ACCIDENTAL_CYCLE)]
        self.set_value(row=Row.ACCIDENTAL, step=start, value=following)


def _tones_leaving_the_scale(*, scale, degree, octave, accidental, symbol, tensions, kind):
    """Return the tones of a chord with tensions or a borrowed scale type, each placed in the scale the roll draws.

    The chord is worked out in the scale it borrows, as half steps from that scale's first note, and each note is then
    placed among the roll's own scale's degrees, sharpened or flattened where it lies between two. A borrowed root that
    is not the note the roll draws on the step is a tone too, so that the roll shows where the chord really sits.
    """
    source = borrowed(scale=scale, kind=kind)
    steps = source.get_half_steps()
    octaves_up, place = divmod(degree - MIN_DEGREE, len(steps))
    root = octaves_up * HALF_STEPS_PER_OCTAVE + steps[place] + ACCIDENTALS.get(accidental, 0)
    above = list(chord_half_steps(scale=source, degree=degree, symbol=symbol, tensions=tensions))
    own_steps = scale.get_half_steps()
    own_octaves_up, own_place = divmod(degree - MIN_DEGREE, len(own_steps))
    if root != own_octaves_up * HALF_STEPS_PER_OCTAVE + own_steps[own_place] + ACCIDENTALS.get(accidental, 0):
        above.insert(0, 0)
    tones = [scale.degree_above(degree=MIN_DEGREE, octave=octave, accidental=None, half_steps=root + half_steps) for half_steps in above]
    return [tone for tone in tones if tone is not None]


def _inverted_tones(*, root, tones, inversion):
    """Return a chord's tones above its root as an inversion plays them: its lowest notes, the root first, an octave up, the root among them drawn as a ghost where it sounds.

    A chord is built upward from its root, so its lowest notes are the first ones; never all of them move.
    """
    if not inversion:
        return tones
    notes = [root, *tones]
    moved = min(inversion, len(notes) - 1)
    if not moved:
        return tones
    lifted = [(degree, octave + 1, accidental) for degree, octave, accidental in notes[:moved]]
    return [*notes[moved:], *lifted]
