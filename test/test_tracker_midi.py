# llamatron: a Python language and framework for producing MIDI clips.
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

"""The tracker can write Mary Had a Little Lamb as MIDI, with an accompaniment.

These check that the song comes out, and leave timing and exact octaves free to improve.
"""

import glob
import gzip
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

import mido

from gate_conversion import to_gates

from llamatron.renderers.outputs import MIDI_KINDS, OutputKind
from llamatron.tui.document import Document, new_song
from test_tui_pages import UITest

NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FIRST_VERSE = 'E D C D E E E D D D E G G'.split()
SECOND_VERSE = 'E D C D E E E E D D E D C'.split()
DEGREES = {'C': 1, 'D': 2, 'E': 3, 'F': 4, 'G': 5, 'A': 6, 'B': 7}
Q, H, W = '1/4', '1/2', 1


def melody(names, durations):
    """Return a melody as a pattern from its notes and their lengths, with each length as a gate."""
    return to_gates({
        'steps': len(names),
        'degree': [DEGREES[name] for name in names],
        'duration': durations,
        'octave': [2] * len(names),
    })


def mary():
    """Return Mary Had a Little Lamb as a song, with its chords played by an arpeggiator."""
    data = new_song()
    data['tempo'] = 120
    data['patterns'] = {
        'first': melody(FIRST_VERSE, [Q, Q, Q, Q, Q, Q, H, Q, Q, H, Q, Q, H]),
        'second': melody(SECOND_VERSE, [Q, Q, Q, Q, Q, Q, Q, Q, Q, Q, Q, Q, W]),
        'chords': {
            'steps': 4, 'step_size': W, 'degree': [1, 1, 5, 1], 'octave': [1, 1, 0, 1],
            'chord': ['M', 'M', 7, 'M'],
        },
    }
    data['tracks'] = {'melody': {}, 'accompaniment': {}}
    data['arps'] = {'broken': {'step': '1/8', 'order': 'up_down'}}
    data['chains'] = {'broken_chords': [{'arp': 'broken'}]}
    data['scenes'] = [
        {'name': 'first', 'tracks': {
            'melody': {'pattern': 'first'}, 'accompaniment': {'pattern': 'chords', 'chain': 'broken_chords'},
        }},
        {'name': 'second', 'tracks': {
            'melody': {'pattern': 'second'}, 'accompaniment': {'pattern': 'chords', 'chain': 'broken_chords'},
        }},
    ]
    return data


def played(path):
    """Return the names of the notes in a MIDI file, in the order they start, ignoring octaves."""
    messages = [message for track in mido.MidiFile(path).tracks for message in track]
    return [NAMES[m.note % 12] for m in messages if m.type == 'note_on' and m.velocity > 0]


class InAFolder(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(temporary.name)
        self.document = Document(mary())


class TestMidiFiles(InAFolder):

    def setUp(self):
        super().setUp()
        directory = self.document.render('cliptree')
        self.files = sorted(glob.glob(os.path.join(directory, '*.mid')))

    def test_every_clip_gets_a_file(self):
        self.assertEqual(len(self.files), 4)

    def test_the_melody_is_mary_had_a_little_lamb(self):
        self.assertEqual(played(self.files[0]), FIRST_VERSE)
        self.assertEqual(played(self.files[2]), SECOND_VERSE)

    def test_the_accompaniment_plays_the_songs_chords(self):
        for path in [self.files[1], self.files[3]]:
            with self.subTest(path=path):
                notes = played(path)
                # The arpeggiator plays more notes than there are chords.
                self.assertGreater(len(notes), 4)
                self.assertLessEqual({'C', 'E', 'G', 'B', 'D', 'F'}, set(notes))

    def test_a_saved_song_renders_the_same_melody(self):
        self.document.save('mary.yml')
        directory = Document.load('mary.yml').render('cliptree')
        self.assertEqual(played(sorted(glob.glob(os.path.join(directory, '*.mid')))[0]), FIRST_VERSE)


class TestLiveSet(InAFolder):

    def test_both_tracks_hold_their_notes(self):
        self.document.render('ableton')
        with open(self.document.render_path('ableton'), 'rb') as file:
            live_set = ET.fromstring(gzip.decompress(file.read())).find('LiveSet')
        tracks = {
            track.find('Name/EffectiveName').get('Value'): {
                NAMES[int(key.get('Value')) % 12] for key in track.iter('MidiKey')
            }
            for track in live_set.find('Tracks').findall('MidiTrack')
        }
        self.assertLessEqual({'melody', 'accompaniment'}, set(tracks))
        self.assertLessEqual(set(FIRST_VERSE + SECOND_VERSE), tracks['melody'])
        self.assertLessEqual({'C', 'E', 'G', 'B', 'D', 'F'}, tracks['accompaniment'])


class TestTypedInTheUI(UITest):
    """Types a melody with the same keys a person would, and renders it from the Song page."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        data = new_song()
        data['tracks'] = {'melody': {}}
        data['scenes'] = [{'name': 'verse', 'tracks': {'melody': {'pattern': 'tune'}}}]
        self.document = Document(data)
        self.document.add_pattern('tune', steps=len(FIRST_VERSE))
        self.app.document = self.document

    async def test_typed_notes_come_out_as_midi(self):
        await self.press('p', 'enter')
        for name in FIRST_VERSE:
            await self.press(str(DEGREES[name]), 'right')
        # M asks which MIDI files to write, and the named clips give one file for the one clip.
        await self.press('tab', 'tab', 's', 'm', *(['down'] * MIDI_KINDS.index(OutputKind.CLIP_TREE)), 'enter')
        files = glob.glob(os.path.join(self.document.output_directory(), '*.mid'))
        self.assertEqual(len(files), 1)
        self.assertEqual(played(files[0]), FIRST_VERSE)



if __name__ == '__main__':
    unittest.main()
