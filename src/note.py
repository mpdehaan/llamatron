from dataclasses import dataclass

# Semitones above C in the same octave number. Octave numbers change at C, so
# B# is a semitone above B in its octave (B#3 == C4) and Cb is a semitone below
# C (Cb4 == B3).
SEMITONES_ABOVE_C = {
    'B#': 12,
    'C': 0,
    'Cb': -1,
    'C#': 1,
    'Db': 1,
    'D': 2,
    'D#': 3,
    'Eb': 3,
    'E': 4,
    'Fb': 4,
    'E#': 5,
    'F': 5,
    'F#': 6,
    'Gb': 6,
    'G': 7,
    'G#': 8,
    'Ab': 8,
    'A': 9,
    'A#': 10,
    'Bb': 10,
    'B': 11,
}

MIN_OCTAVE = 0
MAX_OCTAVE = 10
MIN_MIDI_NUMBER = 0
MAX_MIDI_NUMBER = 127

# Spellings for notes worked out from a MIDI number, indexed by semitones above C.
SHARP_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FLAT_NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']


def _check_integer(n):
    # bool is a subclass of int, but half_step(True) is not a real step count.
    if type(n) is not int:
        raise ValueError(f'expected an integer, got {n!r}')


@dataclass(frozen=True, eq=False)
class Note:
    """A pitch, such as Note('C#', 4). Enharmonic spellings compare equal."""

    name: str
    octave_number: int

    def __post_init__(self):
        if not isinstance(self.name, str) or self.name not in SEMITONES_ABOVE_C:
            raise ValueError(f'invalid note name: {self.name!r}')
        # bool is a subclass of int, but Note('C', True) is not a real octave.
        if type(self.octave_number) is not int or not MIN_OCTAVE <= self.octave_number <= MAX_OCTAVE:
            raise ValueError(
                f'invalid octave: {self.octave_number!r} '
                f'(must be an integer from {MIN_OCTAVE} to {MAX_OCTAVE})'
            )
        if not MIN_MIDI_NUMBER <= self.midi_number <= MAX_MIDI_NUMBER:
            raise ValueError(
                f'{self.name}{self.octave_number} is outside the MIDI range: '
                f'its number would be {self.midi_number}'
            )

    @property
    def midi_number(self):
        """The MIDI note number, where C0 is 0."""
        return self.octave_number * 12 + SEMITONES_ABOVE_C[self.name]

    def half_step(self, n):
        """Return a new Note n half steps higher, or lower if n is negative.

        The result is spelled with flats if this note's name has a flat, and
        with sharps otherwise.
        """
        _check_integer(n)
        names = FLAT_NAMES if self.name.endswith('b') else SHARP_NAMES
        octave_number, semitones = divmod(self.midi_number + n, 12)
        return Note(names[semitones], octave_number)

    def whole_step(self, n):
        """Return a new Note n whole steps higher, or lower if n is negative."""
        _check_integer(n)
        return self.half_step(n * 2)

    def octave(self, n):
        """Return a new Note n octaves higher, or lower if n is negative.

        The result keeps this note's spelling.
        """
        _check_integer(n)
        return Note(self.name, self.octave_number + n)

    def to_chord(self, typ):
        """Return a new Chord of the given ChordType with this note as its root.

        The root keeps its spelling, and the other notes are spelled as
        half_step spells them.
        """
        # Imported here because src.chord imports Note from this module.
        from src.chord import Chord, ChordType

        if not isinstance(typ, ChordType):
            raise ValueError(f'expected a ChordType, got {typ!r}')
        return Chord([self, *(self.half_step(n) for n in typ.value)])

    def __eq__(self, other):
        if not isinstance(other, Note):
            return NotImplemented
        return self.midi_number == other.midi_number

    def __hash__(self):
        return hash(self.midi_number)
