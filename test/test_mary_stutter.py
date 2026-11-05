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
import demo.mary_stutter
from src.renderers.clip_tree import ClipTree

MELODY_FILES = ['001-001.mid', '002-001.mid']
CHORD_FILES = ['001-002.mid', '002-002.mid']


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


def expected_from(original):
    """Return the notes of the original with every fourth one chopped into four."""
    result = []
    for index, (note, start, end) in enumerate(original):
        if index % 4 == 3:
            part = (end - start) // 4
            result += [(note, start + part * i, start + part * (i + 1)) for i in range(4)]
        else:
            result.append((note, start, end))
    return result


class TestMaryStutterDemo(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.original = render(demo.mary.build_song(), os.path.join(temporary.name, 'mary'))
        self.changed = render(demo.mary_stutter.build_song(), os.path.join(temporary.name, 'new'))

    def test_chords_are_untouched(self):
        for filename in CHORD_FILES:
            with self.subTest(filename=filename):
                self.assertEqual(self.changed[filename].tracks[0], self.original[filename].tracks[0])

    def test_every_fourth_melody_note_is_chopped_into_four(self):
        for filename in MELODY_FILES:
            with self.subTest(filename=filename):
                self.assertEqual(
                    notes_played(self.changed[filename]),
                    expected_from(notes_played(self.original[filename])),
                )

    def test_clips_stay_four_measures_long(self):
        for filename, midi_file in self.changed.items():
            with self.subTest(filename=filename):
                self.assertAlmostEqual(midi_file.length, 8)


if __name__ == '__main__':
    unittest.main()
