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

"""Track settings, the arpeggiator's offsets and octaves, and CC values with slides."""

import contextlib
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

from llamatron.composition.clip_slot import morph_style_name
from llamatron.composition.file_format import CC_ROWS, ClipSlotSetting, GeneratorKind, PatternSetting, Row, Section, TrackSetting
from llamatron.composition.generator_settings import ArpSetting, written_name
from llamatron.generators.arp import Arp, ChordOrder, OctaveJump, along_scale
from llamatron.music.chord import Chord
from llamatron.generators.blend import BlendMode
from llamatron.music.note import Note, NoteName, Rest
from llamatron.music.sound import Sound
from llamatron.exporters.ableton_project import AbletonProject
from llamatron.exporters.clip_tree import ClipTree
from llamatron.exporters.midi_messages import CONTROL_CHANGE_MESSAGE, NOTE_ON_MESSAGE
from llamatron.exporters.timing import SLIDE_STEP, control_events, timed_events
from llamatron.music.scale import Scale, ScaleType
from llamatron.grid.clip import Clip
from llamatron.grid.control import Control
from llamatron.composition.song_file_error import SongFileError
from rendering import as_setlist, dump_song_data, render_data, setlist_from_data, song_from_data
from llamatron.tui.document import Document

C_MAJOR = Scale(root=Note(name='C', octave_number=5), typ=ScaleType.MAJOR)

SONG = """
tempo: 120
scale: main
scales:
  main: { root: C, type: major }
patterns:
  riff:
    steps: 4
    step_size: 1/4
    degree: [1, 3, ~, 5]
    cc1: [0, ~, 100, 127]
    cc2: [20, 40, ~, ~]
    slide: [false, false, true, false]
  hit:
    steps: 2
    drum: true
    step_size: 1/4
    degree: [C, ~]
  chord:
    steps: 1
    step_size: 1
    degree: [1]
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

# Names the tests give to their own things, and other values they use.
LEAD = 'lead'
HIT = 'hit'
UP = 'up'
YES = 'yes'
COLOUR = 'colour'
RED = 'red'
KICK = 'kick'
RIFF = 'riff'
X = 'x'
SIDEWAYS = 'sideways'
EIGHTH = '1/8'
OTHER = 'other'
QUARTER = '1/4'
# What the clip files are named under, and the first scene's first track's file.
EXPORT = 'song'
FIRST_CLIP_FILES = EXPORT + '_clip_s_001-*t_001-*.mid'
LOUD = 'loud'
ID = 'Id'
VALUE = 'Value'
SET = 'set'
TIME = 'Time'
FLOATEVENT = 'FloatEvent'
POINTEEID = 'PointeeId'


def song_data(**changes):
    data = yaml.safe_load(SONG)
    for key, value in changes.items():
        data[key] = value
    return data


def lead_clip(data):
    song = render_data(data)
    track = next(track for track in song.get_columns() if track.get_name() == LEAD)
    return song.get_clip(row=song.get_rows()[0], column=track)


def pitches(clip):
    return [pitch for _, _, pitch, _ in sorted(timed_events(clip=clip, scale=clip.get_scale())[0])]


class TestTracks(unittest.TestCase):

    def test_tracks_are_named_objects(self):
        with self.assertRaises(SongFileError):
            song_from_data(song_data(tracks=[LEAD, KICK]))
        song_from_data(song_data(tracks={LEAD: {}, KICK: None}))

    def test_transpose_moves_notes_along_the_scale(self):
        data = song_data()
        data[Section.TRACKS][LEAD][TrackSetting.TRANSPOSE] = 2
        # Degrees 1, 3 and 5 of C major become 3, 5 and 7: E, G and B.
        self.assertEqual(pitches(lead_clip(data)), [64, 67, 71])

    def test_transpose_never_moves_a_drum_pattern(self):
        data = song_data()
        data[Section.TRACKS][LEAD][TrackSetting.TRANSPOSE] = 3
        data[Section.SCENES][0][Section.TRACKS][LEAD] = {ClipSlotSetting.PATTERN: HIT}
        self.assertEqual(pitches(lead_clip(data)), [36])

    def test_a_drum_track_never_transposes(self):
        data = song_data()
        data[Section.TRACKS][LEAD].update(transpose=3, drum=True)
        self.assertEqual(pitches(lead_clip(data)), [60, 64, 67])

    def test_bad_track_settings_are_refused(self):
        for settings in [{TrackSetting.TRANSPOSE: 25}, {TrackSetting.TRANSPOSE: UP}, {PatternSetting.DRUM: YES}, {TrackSetting.CC: [1, 2, 3]}, {TrackSetting.CC: [128, None, None, None]}, {COLOUR: RED}]:
            data = song_data()
            data[Section.TRACKS][LEAD] = settings
            with self.subTest(settings=settings), self.assertRaises(SongFileError):
                song_from_data(data)

    def test_tracks_are_written_with_their_settings(self):
        data = song_data()
        data[Section.TRACKS][LEAD][TrackSetting.TRANSPOSE] = -2
        text = dump_song_data(data)
        self.assertIn('    tracks:\n      lead: { cc: [1, 74, ~, ~], transpose: -2 }\n      kick: {}\n', text)
        self.assertEqual(yaml.safe_load(text), as_setlist(data))


class TestToggles(unittest.TestCase):

    def test_an_on_or_off_row_needs_true_or_false(self):
        data = song_data()
        data[Section.PATTERNS][RIFF][Row.SLIDE] = [True, None, False, False]
        with self.assertRaises(SongFileError):
            song_from_data(data)

    def test_saving_writes_off_as_false(self):
        document = Document(setlist=setlist_from_data(song_data()))
        document.set_step_value(name=RIFF, row=Row.GLIDE, step=0, value=True)
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'song.yml')
            document.save(path=path)
            with open(path) as file:
                text = file.read()
        self.assertIn('glide: [true, false, false, false]', text)
        self.assertNotIn(Row.GRAB, text)


class TestArpOffsets(unittest.TestCase):

    def arp(self, chord, **settings):
        clip = Clip(notes=[chord], scale=C_MAJOR)
        return Arp(step=Fraction(1, 4), **settings).generate(clip).get_notes()

    def test_offsets_move_notes_along_the_scale_and_a_blank_step_is_silent(self):
        chord = Chord([Note(name=NoteName.C, octave_number=5, length=1), Note(name=NoteName.E, octave_number=5, length=1), Note(name=NoteName.G, octave_number=5, length=1)])
        notes = self.arp(chord, offsets=[0, None, 1, 7])
        self.assertEqual(notes[0], Note(name=NoteName.C, octave_number=5, length=Fraction(1, 4)))
        self.assertEqual(notes[1], Rest(Fraction(1, 4)))
        # The silent step didn't use up E, which plays next, one note higher.
        self.assertEqual(notes[2], Note(name=NoteName.F, octave_number=5, length=Fraction(1, 4)))
        self.assertEqual(notes[3], Note(name=NoteName.G, octave_number=6, length=Fraction(1, 4)))

    def test_offsets_start_again_with_each_chord(self):
        chord = Chord([Note(name=NoteName.C, octave_number=5, length=Fraction(1, 2)), Note(name=NoteName.E, octave_number=5, length=Fraction(1, 2))])
        clip = Clip(notes=[chord, chord], scale=C_MAJOR)
        notes = Arp(step=Fraction(1, 4), offsets=[2, None, 0]).generate(clip).get_notes()
        self.assertEqual(notes, [Note(name=NoteName.E, octave_number=5, length=Fraction(1, 4)), Rest(Fraction(1, 4))] * 2)

    def test_octave_range_and_jump(self):
        chord = Chord([Note(name=NoteName.C, octave_number=5, length=Fraction(3, 2)), Note(name=NoteName.E, octave_number=5, length=Fraction(3, 2))])
        after_chord = [note.get_midi_number() for note in self.arp(chord, octave_range=2)][:4]
        after_each = [note.get_midi_number() for note in self.arp(chord, octave_range=2, octave_jump=OctaveJump.AFTER_EACH_NOTE)][:4]
        self.assertEqual(after_chord, [60, 64, 72, 76])
        self.assertEqual(after_each, [60, 72, 64, 76])
        down = [note.get_midi_number() for note in self.arp(chord, octave_range=2, order=ChordOrder.DOWN)][:4]
        self.assertEqual(down, [76, 72, 64, 60])

    def test_a_single_note_makes_a_melody_only_with_offsets_or_a_range(self):
        note = Note(name=NoteName.C, octave_number=5, length=Fraction(1, 2))
        self.assertEqual(self.arp(note), [note])
        self.assertEqual(self.arp(note, offsets=[0, 2]), [Note(name=NoteName.C, octave_number=5, length=Fraction(1, 4)), Note(name=NoteName.E, octave_number=5, length=Fraction(1, 4))])

    def test_without_a_scale_offsets_are_half_steps(self):
        self.assertEqual(self.moved(note=Note(name=NoteName.C, octave_number=5, length=1), steps=2, scale=None), Note(name=NoteName.D, octave_number=5, length=1))
        self.assertEqual(self.moved(note=Note(name=NoteName.C, octave_number=5, length=1), steps=2, scale=C_MAJOR), Note(name=NoteName.E, octave_number=5, length=1))
        self.assertEqual(self.moved(note=Note(name=NoteName.C_SHARP, octave_number=5, length=1), steps=1, scale=C_MAJOR), Note(name=NoteName.D_SHARP, octave_number=5, length=1))

    def moved(self, *, note, steps, scale):
        """Return a Note moved along a scale by the arpeggiator's along_scale, which works on sounds."""
        return Sound.position(along_scale(note=Sound.of(note), steps=steps, scale=scale))

    def test_the_file_settings(self):
        data = song_data(arps={UP: {ArpSetting.STEP: EIGHTH, ArpSetting.OCTAVE_RANGE: 2, ArpSetting.OCTAVE_JUMP: written_name(OctaveJump.AFTER_EACH_NOTE), ArpSetting.OFFSETS: [0, None, 2]}}, chains={X: [{GeneratorKind.ARP: UP}]})
        data[Section.SCENES][0][Section.TRACKS][LEAD] = {ClipSlotSetting.PATTERN: Row.CHORD, ClipSlotSetting.CHAIN: X}
        # C3 C4 E3 E4 G3 G4, with a silent second step, and the third two notes up the scale.
        self.assertEqual(pitches(lead_clip(data))[:4], [60, 76, 64, 79])

    def test_bad_file_settings_are_refused(self):
        for settings in [
            {ArpSetting.OCTAVE_RANGE: 5}, {ArpSetting.OCTAVE_RANGE: 0}, {ArpSetting.OCTAVE_JUMP: 2}, {ArpSetting.OCTAVE_JUMP: SIDEWAYS},
            {ArpSetting.OFFSETS: []}, {ArpSetting.OFFSETS: [0] * 17}, {ArpSetting.OFFSETS: [25]}, {ArpSetting.OFFSETS: UP},
        ]:
            data = song_data(arps={UP: {ArpSetting.STEP: EIGHTH, **settings}}, chains={X: [{GeneratorKind.ARP: UP}]})
            data[Section.SCENES][0][Section.TRACKS][LEAD] = {ClipSlotSetting.PATTERN: Row.CHORD, ClipSlotSetting.CHAIN: X}
            with self.subTest(settings=settings), self.assertRaises(SongFileError):
                lead_clip(data)


class TestControls(unittest.TestCase):

    def test_cc_rows_become_the_tracks_cc_numbers_even_on_rests(self):
        controls = lead_clip(song_data()).get_controls()
        self.assertEqual([(item.get_time(), item.get_number(), item.get_value(), item.get_slide()) for item in controls], [
            (0, 1, 0, False), (0, 74, 20, False), (Fraction(1, 4), 74, 40, False),
            (Fraction(1, 2), 1, 100, True), (Fraction(3, 4), 1, 127, False),
        ])

    def test_cc_rows_of_blanks_play_the_same_as_no_cc_rows(self):
        # A pattern with no CC value on any step skips its CC rows as it plays, whether it holds the rows or not.
        blank = song_data()
        without = song_data()
        steps = blank[Section.PATTERNS][RIFF][PatternSetting.STEPS]
        for row in CC_ROWS:
            blank[Section.PATTERNS][RIFF][row] = [None] * steps
            without[Section.PATTERNS][RIFF].pop(row, None)
        self.assertEqual(lead_clip(blank).get_controls(), [])
        self.assertEqual(lead_clip(without).get_controls(), [])
        self.assertEqual(pitches(lead_clip(blank)), pitches(lead_clip(without)))
        self.assertEqual(pitches(lead_clip(blank)), pitches(lead_clip(song_data())))

    def test_a_lane_with_no_number_sends_nothing(self):
        data = song_data()
        data[Section.TRACKS][LEAD][TrackSetting.CC] = [None, 74, None, None]
        self.assertEqual({item.get_number() for item in lead_clip(data).get_controls()}, {74})

    def test_values_repeat_with_the_clip_and_a_ratchet_does_not_repeat_them(self):
        data = song_data()
        data[Section.PATTERNS][RIFF][Row.RATCHET] = [4, None, None, None]
        data[Section.SCENES][0][Section.TRACKS][LEAD][ClipSlotSetting.REPEAT] = 2
        controls = [item for item in lead_clip(data).get_controls() if item.get_number() == 1]
        self.assertEqual([item.get_time() for item in controls], [0, Fraction(1, 2), Fraction(3, 4), 1, Fraction(3, 2), Fraction(7, 4)])

    def test_a_morph_uses_the_targets_values_where_the_target_plays(self):
        data = song_data()
        data[Section.PATTERNS][OTHER] = {PatternSetting.STEPS: 4, PatternSetting.STEP_SIZE: QUARTER, Row.DEGREE: [1, 1, 1, 1], Row.CC1: [9, 9, 9, 9]}
        data[Section.SCENES][0][Section.TRACKS][LEAD] = {ClipSlotSetting.PATTERN: RIFF, ClipSlotSetting.REPEAT: 2, ClipSlotSetting.MORPH_TO: OTHER, ClipSlotSetting.MORPH_STYLE: morph_style_name(BlendMode.LEFT)}
        second = [item.get_value() for item in lead_clip(data).get_controls() if item.get_number() == 1 and item.get_time() >= 1]
        self.assertEqual(set(second), {9})

    def test_bad_values_are_refused(self):
        for value in [128, -1, LOUD, True]:
            data = song_data()
            data[Section.PATTERNS][RIFF][Row.CC1] = [value, None, None, None]
            with self.subTest(value=value), self.assertRaises(SongFileError):
                song_from_data(data)

    def test_a_slide_ramps_in_steps_in_midi(self):
        clip = Clip(notes=[Rest(1)], controls=[Control(time=Fraction(0), number=1, value=0, slide=True), Control(time=Fraction(1, 4), number=1, value=64)])
        events = control_events(clip=clip, length=Fraction(1))
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
            ClipTree(directory=self.folder, grid=self.song, name=EXPORT).export()
        path = sorted(glob.glob(os.path.join(self.folder, FIRST_CLIP_FILES)))[0]
        messages = [message for message in mido.MidiFile(path).tracks[0] if not message.is_meta]
        self.assertEqual(messages[0].type, CONTROL_CHANGE_MESSAGE)
        self.assertEqual((messages[0].control, messages[0].value), (1, 0))
        self.assertEqual(messages[2].type, NOTE_ON_MESSAGE)
        values = [message.value for message in messages if message.type == CONTROL_CHANGE_MESSAGE and message.control == 1]
        self.assertEqual(values[:2], [0, 100])
        self.assertEqual(values[-1], 127)
        self.assertGreater(len(values), 4)

    def live_envelopes(self):
        with contextlib.redirect_stdout(io.StringIO()):
            AbletonProject(directory=os.path.join(self.folder, SET), grid=self.song).export()
        with gzip.open(os.path.join(self.folder, SET, 'set.als')) as file:
            root = ET.fromstring(file.read())
        track = root.find('LiveSet/Tracks/MidiTrack')
        targets = {item.get(ID): item.tag for item in track.find('DeviceChain/MainSequencer/MidiControllers')}
        clip = track.find('DeviceChain/MainSequencer/ClipSlotList').find('.//MidiClip')
        return root, targets, clip.find('Envelopes/Envelopes')

    def test_live_envelopes_point_at_the_tracks_controllers(self):
        _, targets, envelopes = self.live_envelopes()
        found = [targets[envelope.find('EnvelopeTarget/PointeeId').get(VALUE)] for envelope in envelopes]
        # CC 1 is the mod wheel, after pitch bend and channel pressure.
        self.assertEqual(found, ['ControllerTargets.3', 'ControllerTargets.76'])

    def test_a_value_holds_until_the_next_unless_it_slides(self):
        _, _, envelopes = self.live_envelopes()
        points = [(event.get(TIME), event.get(VALUE)) for event in envelopes[0].iter(FLOATEVENT)]
        self.assertEqual(points, [('-63072000', '0'), ('0', '0'), ('2', '0'), ('2', '100'), ('3', '127')])

    def test_every_envelope_id_is_used_once_in_the_set(self):
        root, _, _ = self.live_envelopes()
        pointees = [item.get(VALUE) for item in root.iter(POINTEEID)]
        targets = {item.get(ID) for item in root.iter() if item.tag.startswith('ControllerTargets.')}
        for pointee in pointees:
            if pointee in targets:
                owners = [item for item in root.iter() if item.get(ID) == pointee and item.tag.startswith('ControllerTargets.')]
                self.assertEqual(len(owners), 1)


if __name__ == '__main__':
    unittest.main()
