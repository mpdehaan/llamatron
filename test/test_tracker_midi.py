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

from rendering import bare_document

from llamatron.composition.file_format import (
    ClipSlotSetting, GeneratorKind, PatternSetting, Row, SceneSetting, Section, SongSetting,
)
from llamatron.composition.generator_settings import ArpSetting, written_name
from llamatron.generators.arp import ChordOrder
from llamatron.music.note import NoteName
from llamatron.exporters.midi_messages import NOTE_ON_MESSAGE
from llamatron.exporters.exports import EXPORT_KINDS, ExportKind
from llamatron.composition.setlist import Setlist, new_setlist
from llamatron.strings.names import MSG_DEFAULT_SONG_NAME
from llamatron.tui.document import Document
from test_tui_pages import UITest
from llamatron.tui.keys import Key
from llamatron.tui import keybindings

NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
FIRST_VERSE = 'E D C D E E E D D D E G G'.split()
SECOND_VERSE = 'E D C D E E E E D D E D C'.split()
DEGREES = {'C': 1, 'D': 2, 'E': 3, 'F': 4, 'G': 5, 'A': 6, 'B': 7}
# The song typed into the UI: one track, one pattern and one scene.
MELODY = 'melody'
TUNE = 'tune'
VERSE = 'verse'
MARY_FILE = 'mary.yml'
FIRST_SCENE = 0
Q = '1/4'
H = '1/2'
W = 1

# Names the tests give to their own things, and other values they use.
DURATION = 'duration'
FIRST = 'first'
SECOND = 'second'
CHORDS = 'chords'
ACCOMPANIMENT = 'accompaniment'
BROKEN = 'broken'
BROKEN_CHORDS = 'broken_chords'
EIGHTH = '1/8'
READ_BYTES = 'rb'
LIVESET = 'LiveSet'
VALUE = 'Value'
MIDITRACK = 'MidiTrack'
MIDIKEY = 'MidiKey'
TRACKS = 'Tracks'


def melody(*, names, durations):
    """Return a melody as a pattern from its notes and their lengths, with each length as a gate."""
    return to_gates(old={
        PatternSetting.STEPS: len(names),
        Row.DEGREE: [DEGREES[name] for name in names],
        DURATION: durations,
        Row.OCTAVE: [4] * len(names),
    })


def mary():
    """Return Mary Had a Little Lamb as a set of one song, with its chords played by an arpeggiator."""
    data = new_setlist()
    song = data[Section.SONGS][MSG_DEFAULT_SONG_NAME]
    song[SongSetting.TEMPO] = 120
    data[Section.PATTERNS] = {
        FIRST: melody(names=FIRST_VERSE, durations=[Q, Q, Q, Q, Q, Q, H, Q, Q, H, Q, Q, H]),
        SECOND: melody(names=SECOND_VERSE, durations=[Q, Q, Q, Q, Q, Q, Q, Q, Q, Q, Q, Q, W]),
        CHORDS: {
            PatternSetting.STEPS: 4, PatternSetting.STEP_SIZE: W, Row.DEGREE: [1, 1, 5, 1], Row.OCTAVE: [3, 3, 2, 3],
            Row.CHORD: ['M', 'M', 7, 'M'],
        },
    }
    song[Section.TRACKS] = {MELODY: {}, ACCOMPANIMENT: {}}
    data[Section.ARPS] = {BROKEN: {ArpSetting.STEP: EIGHTH, ArpSetting.ORDER: written_name(ChordOrder.UP_DOWN)}}
    data[Section.CHAINS] = {BROKEN_CHORDS: [{GeneratorKind.ARP: BROKEN}]}
    song[Section.SCENES] = [
        {SceneSetting.NAME: FIRST, SceneSetting.TRACKS: {
            MELODY: {ClipSlotSetting.PATTERN: FIRST}, ACCOMPANIMENT: {ClipSlotSetting.PATTERN: CHORDS, ClipSlotSetting.CHAIN: BROKEN_CHORDS},
        }},
        {SceneSetting.NAME: SECOND, SceneSetting.TRACKS: {
            MELODY: {ClipSlotSetting.PATTERN: SECOND}, ACCOMPANIMENT: {ClipSlotSetting.PATTERN: CHORDS, ClipSlotSetting.CHAIN: BROKEN_CHORDS},
        }},
    ]
    return data


def played(path):
    """Return the names of the notes in a MIDI file, in the order they start, ignoring octaves."""
    messages = [message for track in mido.MidiFile(path).tracks for message in track]
    return [NAMES[m.note % 12] for m in messages if m.type == NOTE_ON_MESSAGE and m.velocity > 0]


class InAFolder(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(temporary.name)
        self.document = Document(setlist=Setlist.from_data(data=mary()))
        # Exports are named after the set's file and written beside it, so the set is saved first.
        self.document.save(path=MARY_FILE)


class TestMidiFiles(InAFolder):

    def setUp(self):
        super().setUp()
        self.files = sorted(glob.glob(self.document.export(ExportKind.CLIP_TREE)))

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
                self.assertLessEqual({NoteName.C, NoteName.E, NoteName.G, NoteName.B, NoteName.D, NoteName.F}, set(notes))

    def test_a_saved_song_exports_the_same_melody(self):
        self.assertEqual(played(sorted(glob.glob(Document.load(MARY_FILE).export(ExportKind.CLIP_TREE)))[0]), FIRST_VERSE)


class TestLiveSet(InAFolder):

    def test_both_tracks_hold_their_notes(self):
        with open(self.document.export(ExportKind.ABLETON), READ_BYTES) as file:
            live_set = ET.fromstring(gzip.decompress(file.read())).find(LIVESET)
        tracks = {
            track.find('Name/EffectiveName').get(VALUE): {
                NAMES[int(key.get(VALUE)) % 12] for key in track.iter(MIDIKEY)
            }
            for track in live_set.find(TRACKS).findall(MIDITRACK)
        }
        self.assertLessEqual({MELODY, ACCOMPANIMENT}, set(tracks))
        self.assertLessEqual(set(FIRST_VERSE + SECOND_VERSE), tracks[MELODY])
        self.assertLessEqual({NoteName.C, NoteName.E, NoteName.G, NoteName.B, NoteName.D, NoteName.F}, tracks[ACCOMPANIMENT])


class TestTypedInTheUI(UITest):
    """Types a melody with the same keys a person would, and exports it from the pattern editor."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.document = bare_document()
        self.document.save(path=MARY_FILE)
        self.document.add_track(MELODY)
        self.document.add_pattern(name=TUNE, steps=len(FIRST_VERSE))
        self.document.add_scene(index=FIRST_SCENE, name=VERSE)
        self.document.add_clip_slot(index=FIRST_SCENE, track=MELODY, pattern=TUNE)
        self.app.set_document(self.document)

    async def test_typed_notes_come_out_as_midi(self):
        await self.press(keybindings.MainPage.PATTERNS, Key.ENTER, keybindings.PatternEditor.TO_EDITOR)
        for name in FIRST_VERSE:
            await self.press(str(DEGREES[name]), Key.RIGHT)
        # X asks what to export from any page, and the clips kind gives one file for the one clip.
        await self.press(keybindings.PatternEditor.EXPORT, *([Key.DOWN] * EXPORT_KINDS.index(ExportKind.CLIP_TREE)), Key.ENTER, Key.ENTER)
        files = glob.glob(self.document.export_path(ExportKind.CLIP_TREE))
        self.assertEqual(len(files), 1)
        self.assertEqual(played(files[0]), FIRST_VERSE)


if __name__ == '__main__':
    unittest.main()
