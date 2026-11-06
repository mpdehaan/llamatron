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

"""Track settings, the arpeggiator's offsets and octaves, and CC values with slides."""

import contextlib
import copy
import glob
import gzip
import io
import os
import tempfile
import unittest
import xml.etree.ElementTree as ET
from fractions import Fraction

import mido
import yaml

from llamatron.generators.arp import Arp, ChordOrder, OctaveJump, along_scale
from llamatron.chord import Chord
from llamatron.note import Note, Rest
from llamatron.renderers.ableton_project import AbletonProject
from llamatron.renderers.clip_tree import ClipTree
from llamatron.renderers.timing import SLIDE_STEP, control_events, timed_events
from llamatron.scale import Scale, ScaleType
from llamatron.song import Clip, Control
from llamatron.composition.song_file_error import SongFileError
from rendering import render_data
from llamatron.composition.song import Song
from llamatron.song_writer import dump_song
from llamatron.tui.document import Document

C_MAJOR = Scale(Note('C', 5), ScaleType.MAJOR)

SONG = """
tempo: 120
scale: main
scales:
  main: { root: C, type: major }
patterns:
  riff:
    steps: 4
    degree: [1, 3, ~, 5]
    duration: [1/4, 1/4, 1/4, 1/4]
    cc1: [0, ~, 100, 127]
    cc2: [20, 40, ~, ~]
    slide: [false, false, true, false]
  hit:
    steps: 2
    drum: true
    degree: [C, ~]
    duration: [1/4, 1/4]
  chord:
    steps: 1
    degree: [1]
    duration: [1]
    chord: [M]
tracks:
  lead: { cc: [1, 74, ~, ~] }
  kick: {}
scenes:
  - name: one
    tracks:
      lead: { pattern: riff }
      kick: { pattern: hit, loop: true }
"""


def song_data(**changes):
    data = yaml.safe_load(SONG)
    for key, value in changes.items():
        data[key] = value
    return data


def lead_clip(data):
    song = render_data(data)
    track = next(track for track in song.tracks if track.name == 'lead')
    return song.get_clip(song.scenes[0], track)


def pitches(clip):
    return [pitch for _, _, pitch, _ in sorted(timed_events(clip, clip.scale)[0])]


class TestTracks(unittest.TestCase):

    def test_tracks_are_named_objects(self):
        with self.assertRaises(SongFileError):
            Song.from_data(song_data(tracks=['lead', 'kick']))
        Song.from_data(song_data(tracks={'lead': {}, 'kick': None}))

    def test_transpose_moves_notes_along_the_scale(self):
        data = song_data()
        data['tracks']['lead']['transpose'] = 2
        # Degrees 1, 3 and 5 of C major become 3, 5 and 7: E, G and B.
        self.assertEqual(pitches(lead_clip(data)), [64, 67, 71])

    def test_transpose_never_moves_a_drum_pattern(self):
        data = song_data()
        data['tracks']['lead']['transpose'] = 3
        data['scenes'][0]['tracks']['lead'] = {'pattern': 'hit'}
        self.assertEqual(pitches(lead_clip(data)), [36])

    def test_a_drum_track_never_transposes(self):
        data = song_data()
        data['tracks']['lead'].update(transpose=3, drum=True)
        self.assertEqual(pitches(lead_clip(data)), [60, 64, 67])

    def test_bad_track_settings_are_refused(self):
        for settings in [{'transpose': 25}, {'transpose': 'up'}, {'drum': 'yes'}, {'cc': [1, 2, 3]}, {'cc': [128, None, None, None]}, {'colour': 'red'}]:
            data = song_data()
            data['tracks']['lead'] = settings
            with self.subTest(settings=settings), self.assertRaises(SongFileError):
                Song.from_data(data)

    def test_tracks_are_written_with_their_settings(self):
        data = song_data()
        data['tracks']['lead']['transpose'] = -2
        text = dump_song(data)
        self.assertIn('tracks:\n  lead: { cc: [1, 74, ~, ~], transpose: -2 }\n  kick: {}\n', text)
        self.assertEqual(yaml.safe_load(text), data)


class TestToggles(unittest.TestCase):

    def test_an_on_or_off_row_needs_true_or_false(self):
        data = song_data()
        data['patterns']['riff']['slide'] = [True, None, False, False]
        with self.assertRaises(SongFileError):
            Song.from_data(data)

    def test_saving_writes_off_as_false(self):
        document = Document(song_data())
        document.set_step_value('riff', 'glide', 0, True)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'song.yml')
            document.save(path)
            with open(path) as file:
                text = file.read()
        self.assertIn('glide: [true, false, false, false]', text)
        self.assertNotIn('grab', text)


class TestArpOffsets(unittest.TestCase):

    def arp(self, chord, **settings):
        clip = Clip(notes=[chord], scale=C_MAJOR)
        return Arp(Fraction(1, 4), **settings).generate(clip).notes

    def test_offsets_move_notes_along_the_scale_and_a_blank_step_is_silent(self):
        chord = Chord([Note('C', 5, 1), Note('E', 5, 1), Note('G', 5, 1)])
        notes = self.arp(chord, offsets=[0, None, 1, 7])
        self.assertEqual(notes[0], Note('C', 5, Fraction(1, 4)))
        self.assertEqual(notes[1], Rest(Fraction(1, 4)))
        # The silent step didn't use up E, which plays next, one note higher.
        self.assertEqual(notes[2], Note('F', 5, Fraction(1, 4)))
        self.assertEqual(notes[3], Note('G', 6, Fraction(1, 4)))

    def test_offsets_start_again_with_each_chord(self):
        chord = Chord([Note('C', 5, Fraction(1, 2)), Note('E', 5, Fraction(1, 2))])
        clip = Clip(notes=[chord, chord], scale=C_MAJOR)
        notes = Arp(Fraction(1, 4), offsets=[2, None, 0]).generate(clip).notes
        self.assertEqual(notes, [Note('E', 5, Fraction(1, 4)), Rest(Fraction(1, 4))] * 2)

    def test_octave_range_and_jump(self):
        chord = Chord([Note('C', 5, Fraction(3, 2)), Note('E', 5, Fraction(3, 2))])
        after_chord = [note.midi_number for note in self.arp(chord, octave_range=2)][:4]
        after_each = [note.midi_number for note in self.arp(chord, octave_range=2, octave_jump=OctaveJump.AFTER_EACH_NOTE)][:4]
        self.assertEqual(after_chord, [60, 64, 72, 76])
        self.assertEqual(after_each, [60, 72, 64, 76])
        down = [note.midi_number for note in self.arp(chord, octave_range=2, order=ChordOrder.DOWN)][:4]
        self.assertEqual(down, [76, 72, 64, 60])

    def test_a_single_note_makes_a_melody_only_with_offsets_or_a_range(self):
        note = Note('C', 5, Fraction(1, 2))
        self.assertEqual(self.arp(note), [note])
        self.assertEqual(self.arp(note, offsets=[0, 2]), [Note('C', 5, Fraction(1, 4)), Note('E', 5, Fraction(1, 4))])

    def test_without_a_scale_offsets_are_half_steps(self):
        self.assertEqual(along_scale(Note('C', 5, 1), 2, None), Note('D', 5, 1))
        self.assertEqual(along_scale(Note('C', 5, 1), 2, C_MAJOR), Note('E', 5, 1))
        self.assertEqual(along_scale(Note('C#', 5, 1), 1, C_MAJOR), Note('D#', 5, 1))

    def test_the_file_settings(self):
        data = song_data(arps={'up': {'step': '1/8', 'octave_range': 2, 'octave_jump': 'after_each_note', 'offsets': [0, None, 2]}}, chains={'x': [{'arp': 'up'}]})
        data['scenes'][0]['tracks']['lead'] = {'pattern': 'chord', 'chain': 'x'}
        # C3 C4 E3 E4 G3 G4, with a silent second step, and the third two notes up the scale.
        self.assertEqual(pitches(lead_clip(data))[:4], [60, 76, 64, 79])

    def test_bad_file_settings_are_refused(self):
        for settings in [
            {'octave_range': 5}, {'octave_range': 0}, {'octave_jump': 2}, {'octave_jump': 'sideways'},
            {'offsets': []}, {'offsets': [0] * 17}, {'offsets': [25]}, {'offsets': 'up'},
        ]:
            data = song_data(arps={'up': {'step': '1/8', **settings}}, chains={'x': [{'arp': 'up'}]})
            data['scenes'][0]['tracks']['lead'] = {'pattern': 'chord', 'chain': 'x'}
            with self.subTest(settings=settings), self.assertRaises(SongFileError):
                lead_clip(data)


class TestControls(unittest.TestCase):

    def test_cc_rows_become_the_tracks_cc_numbers_even_on_rests(self):
        controls = lead_clip(song_data()).controls
        self.assertEqual([(item.time, item.number, item.value, item.slide) for item in controls], [
            (0, 1, 0, False), (0, 74, 20, False), (Fraction(1, 4), 74, 40, False),
            (Fraction(1, 2), 1, 100, True), (Fraction(3, 4), 1, 127, False),
        ])

    def test_a_lane_with_no_number_sends_nothing(self):
        data = song_data()
        data['tracks']['lead']['cc'] = [None, 74, None, None]
        self.assertEqual({item.number for item in lead_clip(data).controls}, {74})

    def test_values_repeat_with_the_clip_and_a_ratchet_does_not_repeat_them(self):
        data = song_data()
        data['patterns']['riff']['ratchet'] = [4, None, None, None]
        data['scenes'][0]['tracks']['lead']['repeat'] = 2
        controls = [item for item in lead_clip(data).controls if item.number == 1]
        self.assertEqual([item.time for item in controls], [0, Fraction(1, 2), Fraction(3, 4), 1, Fraction(3, 2), Fraction(7, 4)])

    def test_rhythm_from_takes_the_cc_rows_from_the_rhythm(self):
        data = song_data()
        data['scenes'][0]['tracks']['lead'] = {'pattern': 'chord', 'rhythm_from': 'riff'}
        self.assertEqual(len(lead_clip(data).controls), 5)

    def test_a_morph_uses_the_targets_values_where_the_target_plays(self):
        data = song_data()
        data['patterns']['other'] = {'steps': 4, 'degree': [1, 1, 1, 1], 'duration': ['1/4'] * 4, 'cc1': [9, 9, 9, 9]}
        data['scenes'][0]['tracks']['lead'] = {'pattern': 'riff', 'repeat': 2, 'morph_to': 'other', 'morph_style': 'left'}
        second = [item.value for item in lead_clip(data).controls if item.number == 1 and item.time >= 1]
        self.assertEqual(set(second), {9})

    def test_bad_values_are_refused(self):
        for value in [128, -1, 'loud', True]:
            data = song_data()
            data['patterns']['riff']['cc1'] = [value, None, None, None]
            with self.subTest(value=value), self.assertRaises(SongFileError):
                Song.from_data(data)

    def test_a_slide_ramps_in_steps_in_midi(self):
        clip = Clip(notes=[Rest(1)], controls=[Control(Fraction(0), 1, 0, True), Control(Fraction(1, 4), 1, 64)])
        events = control_events(clip, Fraction(1))
        self.assertEqual(events[0], (0, 1, 0))
        self.assertEqual(events[-1], (Fraction(1, 4), 1, 64))
        self.assertEqual(len(events), 1 + int(Fraction(1, 4) / SLIDE_STEP))
        self.assertEqual([value for _, _, value in events], sorted(value for _, _, value in events))


class TestRenderingControls(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = temporary.name
        self.song = render_data(song_data())

    def test_midi_files_send_control_changes_before_the_note(self):
        with contextlib.redirect_stdout(io.StringIO()):
            ClipTree(self.folder, self.song).render()
        path = sorted(glob.glob(os.path.join(self.folder, '001-001*.mid')))[0]
        messages = [message for message in mido.MidiFile(path).tracks[0] if not message.is_meta]
        self.assertEqual(messages[0].type, 'control_change')
        self.assertEqual((messages[0].control, messages[0].value), (1, 0))
        self.assertEqual(messages[2].type, 'note_on')
        values = [message.value for message in messages if message.type == 'control_change' and message.control == 1]
        self.assertEqual(values[:2], [0, 100])
        self.assertEqual(values[-1], 127)
        self.assertGreater(len(values), 4)

    def live_envelopes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            AbletonProject(os.path.join(self.folder, 'set'), self.song).render()
        with gzip.open(os.path.join(self.folder, 'set', 'set.als')) as file:
            root = ET.fromstring(file.read())
        track = root.find('LiveSet/Tracks/MidiTrack')
        targets = {item.get('Id'): item.tag for item in track.find('DeviceChain/MainSequencer/MidiControllers')}
        clip = track.find('DeviceChain/MainSequencer/ClipSlotList').find('.//MidiClip')
        return root, targets, clip.find('Envelopes/Envelopes')

    def test_live_envelopes_point_at_the_tracks_controllers(self):
        _, targets, envelopes = self.live_envelopes()
        found = [targets[envelope.find('EnvelopeTarget/PointeeId').get('Value')] for envelope in envelopes]
        # CC 1 is the mod wheel, after pitch bend and channel pressure.
        self.assertEqual(found, ['ControllerTargets.3', 'ControllerTargets.76'])

    def test_a_value_holds_until_the_next_unless_it_slides(self):
        _, _, envelopes = self.live_envelopes()
        points = [(event.get('Time'), event.get('Value')) for event in envelopes[0].iter('FloatEvent')]
        self.assertEqual(points, [('-63072000', '0'), ('0', '0'), ('2', '0'), ('2', '100'), ('3', '127')])

    def test_every_envelope_id_is_used_once_in_the_set(self):
        root, _, _ = self.live_envelopes()
        pointees = [item.get('Value') for item in root.iter('PointeeId')]
        targets = {item.get('Id') for item in root.iter() if item.tag.startswith('ControllerTargets.')}
        for pointee in pointees:
            if pointee in targets:
                owners = [item for item in root.iter() if item.get('Id') == pointee and item.tag.startswith('ControllerTargets.')]
                self.assertEqual(len(owners), 1)


if __name__ == '__main__':
    unittest.main()
