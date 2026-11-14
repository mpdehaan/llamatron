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
"""What a clip plays, as plain data: every note, chord, rest, degree and held sound a render makes is a tuple.

Note, Chord, Rest, Degree and Held are classes, and each one a render made was an object that
checked itself. A render makes thousands, so here each is a tuple with the same contents, and
Sound is a class of static methods that builds, reads and copies such tuples, checking nothing
that the pattern or the classes checked already. The classes stay what a test or a tool builds
a clip from and reads a clip as: Sound.of turns one into its tuple and Sound.position turns a
tuple back, so the two say the same thing.

Every sound starts with its kind and its length, the time until the next position of the clip
starts, as a pair of whole numbers (support/length.py), or None for a note, degree or chord
that takes the clip's note_length:

    a rest      (REST, length)
    a note      (NOTE, length, MIDI number, velocity, glide, name)
    a chord     (CHORD, length, notes), whose length is its longest note's, kept here
    a degree    (DEGREE, length, number, octave, scale notes, half steps)
    a held      (HELD, length, sound), a note, chord or degree that sounds for its own length
    a phrase    (PHRASE, length, parts), sounds played one after another from a held place
"""

from llamatron.music.chord import Chord
from llamatron.music.held import Held, is_phrase, phrase
from llamatron.music.midi import HALF_STEPS_PER_OCTAVE, MAX_MIDI_NUMBER, MIN_MIDI_NUMBER
from llamatron.music.note import FLAT_NAMES, FLAT_SIGN, MAX_OCTAVE, MIN_OCTAVE, SEMITONES_ABOVE_C, SHARP_NAMES, Degree, Note, Rest
from llamatron.strings.errors import ERR_BAD_SOUND, ERR_NOT_A_POSITION
from llamatron.support.length import Length

# The kinds of sound, the first thing in every tuple.
REST = 0
NOTE = 1
CHORD = 2
DEGREE = 3
HELD = 4
PHRASE = 5
# Where every sound keeps its kind and its length.
KIND = 0
LENGTH = 1
# Where a note keeps the rest.
MIDI = 2
VELOCITY = 3
GLIDE = 4
NAME = 5
# Where a chord keeps its notes, a held its sound and a phrase its parts.
NOTES = 2
HELD_SOUND = 2
PARTS = 2
# Where a degree keeps the rest.
NUMBER = 2
OCTAVE = 3
SCALE_NOTES = 4
HALF_STEPS = 5


class Sound:
    """Builds, reads and copies sounds held as tuples. Nothing here makes an object but Sound.position, which is for whoever wants the classes."""

    __slots__ = ()

    @staticmethod
    def rest(length):
        return (REST, length)

    @staticmethod
    def note(*, length, midi, velocity, glide, name):
        """Return a note from values that are already checked: a MIDI number in range and the name that spells it."""
        return (NOTE, length, midi, velocity, glide, name)

    @staticmethod
    def named_note(*, name, octave, length, velocity, glide):
        """Return the note a name and an octave spell, or raise what a Note would for one outside the octaves or the MIDI range."""
        midi = octave * HALF_STEPS_PER_OCTAVE + SEMITONES_ABOVE_C[name]
        if MIN_OCTAVE <= octave <= MAX_OCTAVE and MIN_MIDI_NUMBER <= midi <= MAX_MIDI_NUMBER:
            return (NOTE, length, midi, velocity, glide, name)
        # The class says what is wrong with the note, in the words it always has.
        return Sound.of(Note(name=name, octave_number=octave, length=_as_number(length), velocity=velocity, glide=glide))

    @staticmethod
    def chord(notes):
        """Return a chord of notes, which lasts as long as its longest note, or has no length yet if any note has none."""
        notes = tuple(notes)
        length = None
        for note in notes:
            own = note[LENGTH]
            if own is None:
                length = None
                break
            if length is None or Length.less(length, own):
                length = own
        return (CHORD, length, notes)

    @staticmethod
    def held(sound, length):
        """Return a note, chord or degree held past its place: the next position starts after length while the sound lasts its own."""
        if sound[KIND] not in HOLDABLE:
            raise ValueError(ERR_BAD_SOUND.format(value=Sound.position(sound)))
        return (HELD, length, sound)

    @staticmethod
    def phrase(parts, length):
        """Return sounds played one after another from a held place, while the next position starts after length."""
        return (PHRASE, length, tuple(parts))

    @staticmethod
    def of(position):
        """Return the sound a Note, Chord, Rest, Degree or Held says, with every length as a pair."""
        kind = type(position)
        if kind is Note:
            return (NOTE, _as_pair(position.get_length()), position.get_midi_number(), position.get_velocity(), position.get_glide(), position.get_name())
        if kind is Rest:
            return (REST, Length.exact(position.get_length()))
        if kind is Chord:
            return Sound.chord([Sound.of(note) for note in position.get_notes()])
        if kind is Degree:
            return (
                DEGREE, _as_pair(position.get_length()), position.get_number(), position.get_octave(),
                position.get_scale_notes(), position.get_half_steps(),
            )
        if kind is Held:
            held = position.get_sound()
            length = Length.exact(position.get_length())
            if is_phrase(held):
                return (PHRASE, length, tuple([Sound.of(part) for part in held]))
            return (HELD, length, Sound.of(held))
        raise ValueError(ERR_NOT_A_POSITION.format(value=position))

    @staticmethod
    def position(sound):
        """Return a sound as the Note, Chord, Rest, Degree or Held that says the same, with every length as a Rational."""
        kind = sound[KIND]
        if kind == NOTE:
            name = sound[NAME]
            octave = (sound[MIDI] - SEMITONES_ABOVE_C[name]) // HALF_STEPS_PER_OCTAVE
            return Note(name=name, octave_number=octave, length=_as_number(sound[LENGTH]), velocity=sound[VELOCITY], glide=sound[GLIDE])
        if kind == REST:
            return Rest(Length.rational(sound[LENGTH]))
        if kind == CHORD:
            return Chord([Sound.position(note) for note in sound[NOTES]])
        if kind == DEGREE:
            return Degree(
                number=sound[NUMBER], length=_as_number(sound[LENGTH]), octave=sound[OCTAVE],
                scale_notes=sound[SCALE_NOTES], half_steps=sound[HALF_STEPS],
            )
        if kind == PHRASE:
            return Held(sound=phrase(Sound.position(part) for part in sound[PARTS]), length=Length.rational(sound[LENGTH]))
        return Held(sound=Sound.position(sound[HELD_SOUND]), length=Length.rational(sound[LENGTH]))

    @staticmethod
    def kind(sound):
        """Return which kind of sound a tuple is: REST, NOTE, CHORD, DEGREE, HELD or PHRASE."""
        return sound[KIND]

    @staticmethod
    def length(sound):
        """Return how long until the next position starts, as a pair, or None for one that takes the clip's note_length."""
        return sound[LENGTH]

    @staticmethod
    def with_length(sound, length):
        """Return a rest, note, degree, held sound or phrase with another length, keeping everything else.

        A held sound and a phrase have their place moved and go on sounding as they did.
        """
        kind = sound[KIND]
        if kind == NOTE:
            return (NOTE, length, sound[MIDI], sound[VELOCITY], sound[GLIDE], sound[NAME])
        if kind == REST:
            return (REST, length)
        if kind == DEGREE:
            return (DEGREE, length, sound[NUMBER], sound[OCTAVE], sound[SCALE_NOTES], sound[HALF_STEPS])
        # A held sound and a phrase keep what they hold, which is in the same place in both.
        return (kind, length, sound[HELD_SOUND])

    @staticmethod
    def lasting(played, length):
        """Return a note or chord with every note in it lasting length."""
        if played[KIND] == CHORD:
            return (CHORD, length, tuple([Sound.with_length(note, length) for note in played[NOTES]]))
        return Sound.with_length(played, length)

    @staticmethod
    def half_step(note, steps):
        """Return a note moved a number of half steps, spelled with flats if its name has a flat and with sharps otherwise.

        A note moved outside the MIDI range raises what Note.half_step does.
        """
        midi = note[MIDI] + steps
        if MIN_MIDI_NUMBER <= midi <= MAX_MIDI_NUMBER:
            names = FLAT_NAMES if note[NAME].endswith(FLAT_SIGN) else SHARP_NAMES
            return (NOTE, note[LENGTH], midi, note[VELOCITY], note[GLIDE], names[midi % HALF_STEPS_PER_OCTAVE])
        return Sound.of(Sound.position(note).half_step(steps))

    @staticmethod
    def inverted(chord, inversion):
        """Return a chord with its lowest notes, as many as its inversion says but never all of them, moved up an octave; anything but a chord, or no inversion, as it is.

        A note that would leave the MIDI range stays where it is.
        """
        if not inversion or chord[KIND] != CHORD:
            return chord
        notes = list(chord[NOTES])
        lowest = sorted(range(len(notes)), key=lambda place: notes[place][MIDI])[:min(inversion, len(notes) - 1)]
        for place in lowest:
            try:
                notes[place] = Sound.half_step(notes[place], HALF_STEPS_PER_OCTAVE)
            except ValueError:
                pass
        return Sound.chord(notes)

    @staticmethod
    def chord_above(root, half_steps):
        """Return the chord a root note makes with the notes some half steps above it, each spelled as half_step spells it."""
        return Sound.chord([root, *[Sound.half_step(root, above) for above in half_steps]])

    @staticmethod
    def settled(sound, scale):
        """Return the note a degree plays in a scale, which is the note the Degree class would give."""
        return scale.sound_at(
            degree=sound[NUMBER], scale_notes=sound[SCALE_NOTES], length=sound[LENGTH],
            half_steps=sound[OCTAVE] * HALF_STEPS_PER_OCTAVE + sound[HALF_STEPS],
        )


# What can be held past its place: a note, a chord or a degree, as the Held class allows.
HOLDABLE = (NOTE, CHORD, DEGREE)


def _as_pair(length):
    """Return a note's or degree's length as a pair, or None for one that has none yet."""
    return None if length is None else Length.exact(length)


def _as_number(length):
    """Return a pair as the Rational a class takes, or None for a length that isn't there yet."""
    return None if length is None else Length.rational(length)
