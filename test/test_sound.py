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
"""Sound says as tuples exactly what Note, Chord, Rest, Degree and Held say as objects, and the render makes only the tuples."""

import ast
import pathlib
import unittest
from fractions import Fraction

import llamatron
from llamatron.music.chord import Chord, ChordType
from llamatron.music.held import Held, phrase
from llamatron.music.midi import MAX_MIDI_NUMBER, MAX_VELOCITY, MIN_MIDI_NUMBER
from llamatron.music.note import FIRST_DEGREE, MAX_OCTAVE, MIN_OCTAVE, SEMITONES_ABOVE_C, Degree, Note, NoteName, Rest
from llamatron.music.scale import Scale, ScaleType
from llamatron.music.sound import CHORD, DEGREE, HELD, NOTE, PHRASE, REST, Sound
from llamatron.strings.errors import ERR_BAD_SOUND, ERR_NOT_A_POSITION
from llamatron.support.length import Length
from llamatron.support.rational import Rational

QUARTER = Fraction(1, 4)
EIGHTH = Fraction(1, 8)
THIRD = Fraction(1, 3)
# Lengths a note can have, with None for one that takes its clip's note_length.
LENGTHS = [None, QUARTER, THIRD, 2]
VELOCITIES = [None, 1, MAX_VELOCITY]
# How far a note is moved by half steps, both ways, past an octave and past the MIDI range.
HALF_STEPS = [-130, -13, -12, -1, 0, 1, 5, 12, 25, 130]
# The degrees, the scale notes moved and the half steps added that a pattern's steps ask a scale for.
DEGREES = range(FIRST_DEGREE, FIRST_DEGREE + 16)
SCALE_NOTES = [-9, -1, 0, 1, 7]
ADDED_HALF_STEPS = [-1, 0, 1, 60, 130]
ROOTS = [NoteName.C, NoteName.B_FLAT, NoteName.F_SHARP]
# The highest octave has no notes above G, so the roots stop an octave below it.
ROOT_OCTAVES = [MIN_OCTAVE, 4, MAX_OCTAVE - 1]
# Something that is no position of a clip.
NOT_A_POSITION = 'C4'
# The modules a render runs for every note, which make sounds and never the classes.
SOURCE = pathlib.Path(llamatron.__file__).parent
RENDER_MODULES = [
    *sorted((SOURCE / 'playback').glob('*.py')), *sorted((SOURCE / 'generators').glob('*.py')),
    SOURCE / 'grid' / 'positions.py', SOURCE / 'exporters' / 'timing.py',
]
THE_CLASSES = {Note.__name__, Rest.__name__, Chord.__name__, Degree.__name__, Held.__name__, phrase.__name__}
MSG_MAKES_OBJECTS = 'these modules of the render import the classes, where a render makes sounds:\n{places}'
MSG_PLACE = '{path}: {names}'
LIST_SEPARATOR = '\n'
NAME_SEPARATOR = ', '

C4 = Note(name=NoteName.C, octave_number=4, length=QUARTER)
E4 = Note(name=NoteName.E, octave_number=4, length=EIGHTH)
G4 = Note(name=NoteName.G, octave_number=4, length=QUARTER, velocity=90, glide=True)
C_MAJOR = Scale(root=Note(name=NoteName.C, octave_number=4, length=QUARTER), typ=ScaleType.MAJOR)


def every_note():
    """Return a note of every spelling in a low, a middle and a high octave, with every kind of length and velocity."""
    notes = []
    for place, name in enumerate(SEMITONES_ABOVE_C):
        for octave in (MIN_OCTAVE + 1, 5, MAX_OCTAVE - 1):
            length = LENGTHS[place % len(LENGTHS)]
            velocity = VELOCITIES[place % len(VELOCITIES)]
            notes.append(Note(name=name, octave_number=octave, length=length, velocity=velocity, glide=bool(place % 2)))
    return notes


def every_position():
    """Return positions of every kind a clip can list, the nested ones included."""
    chord = Chord([C4, E4, G4])
    degree = Degree(number=3, length=EIGHTH, octave=1, scale_notes=2, half_steps=-1)
    return [
        *every_note(), Rest(QUARTER), Rest(THIRD), chord, Chord([C4, Note(name=NoteName.E, octave_number=4)]),
        degree, Degree(number=FIRST_DEGREE), Held(sound=C4, length=EIGHTH), Held(sound=chord, length=EIGHTH),
        Held(sound=degree, length=EIGHTH), Held(sound=phrase([C4, Rest(EIGHTH), chord, degree, Held(sound=E4, length=EIGHTH)]), length=EIGHTH),
    ]


def said(position):
    """Return everything a position says, since two notes of one pitch are equal whatever their spelling, velocity or glide."""
    if isinstance(position, Note):
        return (Note.__name__, position.get_name(), position.get_octave_number(), position.get_length(), position.get_velocity(), position.get_glide())
    if isinstance(position, Rest):
        return (Rest.__name__, position.get_length())
    if isinstance(position, Chord):
        return (Chord.__name__, [said(note) for note in position.get_notes()])
    if isinstance(position, Degree):
        return (Degree.__name__, position.get_number(), position.get_length(), position.get_octave(), position.get_scale_notes(), position.get_half_steps())
    sound = position.get_sound()
    return (Held.__name__, position.get_length(), [said(part) for part in sound] if isinstance(sound, tuple) else said(sound))


def problem(action):
    """Return the message of the ValueError an action raises, or None if it raises nothing."""
    try:
        action()
    except ValueError as error:
        return str(error)
    return None


class TestSoundsAndPositions(unittest.TestCase):

    def test_a_position_said_as_a_sound_and_back_is_the_same_position(self):
        for position in every_position():
            with self.subTest(position=position):
                back = Sound.position(Sound.of(position))
                self.assertEqual(back, position)
                self.assertEqual(said(back), said(Sound.position(Sound.of(back))))

    def test_a_note_keeps_its_spelling_its_octave_its_velocity_and_its_glide(self):
        for note in every_note():
            with self.subTest(note=note):
                back = Sound.position(Sound.of(note))
                self.assertEqual(
                    (back.get_name(), back.get_octave_number(), back.get_length(), back.get_velocity(), back.get_glide()),
                    (note.get_name(), note.get_octave_number(), note.get_length(), note.get_velocity(), note.get_glide()),
                )

    def test_every_length_of_a_sound_is_a_pair_and_of_a_position_a_rational(self):
        sound = Sound.of(Held(sound=Chord([C4, E4]), length=EIGHTH))
        self.assertEqual(Sound.length(sound), (1, 8))
        back = Sound.position(sound)
        self.assertIs(type(back.get_length()), Rational)
        self.assertIs(type(back.get_sound().get_notes()[0].get_length()), Rational)

    def test_each_kind_of_position_is_its_kind_of_sound(self):
        kinds = {
            NOTE: C4, REST: Rest(QUARTER), CHORD: Chord([C4, E4]), DEGREE: Degree(number=2),
            HELD: Held(sound=C4, length=EIGHTH), PHRASE: Held(sound=phrase([C4, E4]), length=EIGHTH),
        }
        for kind, position in kinds.items():
            with self.subTest(position=position):
                self.assertEqual(Sound.kind(Sound.of(position)), kind)

    def test_anything_else_is_refused(self):
        with self.assertRaises(ValueError) as refused:
            Sound.of(NOT_A_POSITION)
        self.assertEqual(str(refused.exception), ERR_NOT_A_POSITION.format(value=NOT_A_POSITION))

    def test_a_chord_lasts_as_long_as_its_longest_note_or_has_no_length_while_a_note_has_none(self):
        for chord in [Chord([C4, E4, G4]), Chord([E4, C4]), Chord([C4, Note(name=NoteName.E, octave_number=4)])]:
            with self.subTest(chord=chord):
                length = Sound.length(Sound.of(chord))
                self.assertEqual(None if length is None else Length.rational(length), chord.get_length())

    def test_a_rest_cannot_be_held(self):
        rest = Rest(Rational(1, 4))
        with self.assertRaises(ValueError) as refused:
            Sound.held(Sound.of(rest), Length.exact(EIGHTH))
        self.assertEqual(str(refused.exception), ERR_BAD_SOUND.format(value=rest))
        self.assertEqual(str(refused.exception), problem(lambda: Held(sound=rest, length=EIGHTH)))


class TestSoundsAreMadeAsTheClassesMakeThem(unittest.TestCase):
    """Each way the render makes or copies a sound gives what the class gives, and refuses what the class refuses in the same words."""

    def test_a_note_from_its_name_and_octave(self):
        for name in SEMITONES_ABOVE_C:
            for octave in range(MIN_OCTAVE - 1, MAX_OCTAVE + 2):
                with self.subTest(name=name, octave=octave):
                    expected = problem(lambda: Note(name=name, octave_number=octave, length=QUARTER, velocity=64, glide=True))
                    found = problem(lambda: Sound.named_note(name=name, octave=octave, length=Length.exact(QUARTER), velocity=64, glide=True))
                    self.assertEqual(found, expected)
                    if expected is None:
                        made = Sound.position(Sound.named_note(name=name, octave=octave, length=Length.exact(QUARTER), velocity=64, glide=True))
                        self.assertEqual(said(made), said(Note(name=name, octave_number=octave, length=QUARTER, velocity=64, glide=True)))

    def test_a_note_moved_by_half_steps(self):
        for note in every_note():
            for steps in HALF_STEPS:
                with self.subTest(note=note, steps=steps):
                    expected = problem(lambda: note.half_step(steps))
                    self.assertEqual(problem(lambda: Sound.half_step(Sound.of(note), steps)), expected)
                    if expected is None:
                        self.assertEqual(said(Sound.position(Sound.half_step(Sound.of(note), steps))), said(note.half_step(steps)))

    def test_a_chord_above_a_root(self):
        for root in [C4, G4, Note(name=NoteName.E_FLAT, octave_number=3, length=EIGHTH, velocity=20)]:
            for chord_type in ChordType:
                with self.subTest(root=root, chord_type=chord_type):
                    made = Sound.position(Sound.chord_above(Sound.of(root), chord_type.value))
                    self.assertEqual(said(made), said(root.to_chord(chord_type)))

    def test_a_note_or_a_degree_with_another_length(self):
        length = Length.exact(THIRD)
        for position in [C4, G4, Rest(QUARTER), Degree(number=3, octave=1, scale_notes=2, half_steps=1)]:
            with self.subTest(position=position):
                made = Sound.position(Sound.with_length(Sound.of(position), length))
                expected = Rest(THIRD) if isinstance(position, Rest) else position.with_length(THIRD)
                self.assertEqual(said(made), said(expected))

    def test_a_held_sound_with_another_length_moves_its_place_and_sounds_on(self):
        held = Held(sound=C4, length=EIGHTH)
        made = Sound.position(Sound.with_length(Sound.of(held), Length.exact(THIRD)))
        self.assertEqual(said(made), said(Held(sound=C4, length=THIRD)))

    def test_every_note_of_a_chord_lasting_a_length(self):
        made = Sound.position(Sound.lasting(Sound.of(Chord([C4, E4, G4])), Length.exact(THIRD)))
        self.assertEqual(said(made), said(Chord([note.with_length(THIRD) for note in (C4, E4, G4)])))
        self.assertEqual(said(Sound.position(Sound.lasting(Sound.of(G4), Length.exact(THIRD)))), said(G4.with_length(THIRD)))

    def test_a_degree_settled_in_a_scale(self):
        for degree in [Degree(number=1, length=QUARTER), Degree(number=9, length=EIGHTH, octave=-1, scale_notes=3, half_steps=1)]:
            with self.subTest(degree=degree):
                self.assertEqual(said(Sound.position(Sound.settled(Sound.of(degree), C_MAJOR))), said(degree.to_note(C_MAJOR)))


class TestAScalesSoundIsItsNote(unittest.TestCase):
    """Scale.sound_at works a note out without making one, so every answer is held to Scale.note_at's, on both sides of the MIDI range."""

    def test_every_degree_of_every_scale_type_inside_and_outside_the_midi_range(self):
        inside = 0
        outside = 0
        for scale_type in ScaleType:
            for root_name in ROOTS:
                for root_octave in ROOT_OCTAVES:
                    scale = Scale(root=Note(name=root_name, octave_number=root_octave, length=QUARTER), typ=scale_type)
                    for degree in DEGREES:
                        for scale_notes in SCALE_NOTES:
                            for half_steps in ADDED_HALF_STEPS:
                                settings = dict(degree=degree, scale_notes=scale_notes, half_steps=half_steps, velocity=64, glide=True)
                                expected = problem(lambda: scale.note_at(length=EIGHTH, **settings))
                                found = problem(lambda: scale.sound_at(length=Length.exact(EIGHTH), **settings))
                                self.assertEqual(found, expected, (scale, settings))
                                if expected is None:
                                    inside += 1
                                    sound = scale.sound_at(length=Length.exact(EIGHTH), **settings)
                                    self.assertEqual(said(Sound.position(sound)), said(scale.note_at(length=EIGHTH, **settings)), (scale, settings))
                                else:
                                    outside += 1
        # Both sides are tested: notes that fit, and notes the MIDI range has no number for.
        self.assertGreater(inside, 0)
        self.assertGreater(outside, 0)

    def test_a_note_with_no_length_yet_and_no_velocity(self):
        sound = C_MAJOR.sound_at(degree=3, scale_notes=0, half_steps=0, length=None)
        self.assertEqual(said(Sound.position(sound)), said(C_MAJOR.note_at(degree=3, scale_notes=0, half_steps=0, length=None)))

    def test_the_ends_of_the_midi_range_are_notes(self):
        lowest = Scale(root=Note(name=NoteName.C, octave_number=MIN_OCTAVE, length=QUARTER), typ=ScaleType.MAJOR)
        self.assertEqual(Sound.position(lowest.sound_at(degree=FIRST_DEGREE, scale_notes=0, half_steps=0, length=(1, 4))).get_midi_number(), MIN_MIDI_NUMBER)
        highest = lowest.sound_at(degree=FIRST_DEGREE, scale_notes=0, half_steps=MAX_MIDI_NUMBER, length=(1, 4))
        self.assertEqual(Sound.position(highest).get_midi_number(), MAX_MIDI_NUMBER)


class TestTheRenderMakesSounds(unittest.TestCase):
    """The rule: what plays a song, the generators and the exporters' timing work on sounds, and import none of the classes."""

    def test_no_module_of_the_render_imports_a_class_of_position(self):
        places = []
        for path in RENDER_MODULES:
            imported = set()
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom):
                    imported |= {alias.name for alias in node.names}
            found = sorted(imported & THE_CLASSES)
            if found:
                places.append(MSG_PLACE.format(path=path.relative_to(SOURCE), names=NAME_SEPARATOR.join(found)))
        self.assertEqual(places, [], MSG_MAKES_OBJECTS.format(places=LIST_SEPARATOR.join(places)))

    def test_the_rule_reads_modules_that_exist(self):
        self.assertGreater(len(RENDER_MODULES), 4)
        for path in RENDER_MODULES:
            with self.subTest(path=path):
                self.assertTrue(path.exists())


if __name__ == '__main__':
    unittest.main()
