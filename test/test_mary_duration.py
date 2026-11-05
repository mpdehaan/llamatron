# noose6: a Python language and framework for producing MIDI clips.
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

import os
import tempfile
import unittest

import mido

import demo.mary
import demo.mary_duration
from src.renderers.clip_tree import ClipTree

MELODY_FILES = ['000-000.mid', '001-000.mid']
CHORD_FILES = ['000-001.mid', '001-001.mid']


def render(song, directory):
    ClipTree(directory, song).render()
    return {
        filename: mido.MidiFile(os.path.join(directory, filename))
        for filename in os.listdir(directory)
    }


def notes_played(midi_file):
    """Return (note, start tick, end tick) for each note in a file."""
    tick = 0
    started = {}
    result = []
    for message in midi_file.tracks[0]:
        tick += message.time
        if message.type == 'note_on':
            started[message.note] = tick
        elif message.type == 'note_off':
            result.append((message.note, started[message.note], tick))
    return result


class TestMaryDurationDemo(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.original = render(demo.mary.build_song(), os.path.join(temporary.name, 'mary'))
        self.changed = render(demo.mary_duration.build_song(), os.path.join(temporary.name, 'new'))

    def test_chords_are_untouched(self):
        for filename in CHORD_FILES:
            with self.subTest(filename=filename):
                self.assertEqual(self.changed[filename].tracks[0], self.original[filename].tracks[0])

    def test_melody_plays_the_same_notes_at_the_same_times(self):
        for filename in MELODY_FILES:
            with self.subTest(filename=filename):
                self.assertEqual(
                    [(note, start) for note, start, _ in notes_played(self.changed[filename])],
                    [(note, start) for note, start, _ in notes_played(self.original[filename])],
                )

    def test_every_other_melody_note_is_half_as_long(self):
        for filename in MELODY_FILES:
            before = notes_played(self.original[filename])
            after = notes_played(self.changed[filename])
            for index, (old, new) in enumerate(zip(before, after)):
                with self.subTest(filename=filename, index=index):
                    old_length = old[2] - old[1]
                    expected = old_length // 2 if index % 2 == 0 else old_length
                    self.assertEqual(new[2] - new[1], expected)

    def test_clips_stay_four_measures_long(self):
        for filename, midi_file in self.changed.items():
            with self.subTest(filename=filename):
                self.assertAlmostEqual(midi_file.length, 8)


if __name__ == '__main__':
    unittest.main()
