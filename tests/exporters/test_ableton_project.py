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

import collections
import contextlib
import gzip
import io
import os
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from fractions import Fraction
from pathlib import Path

from llamatron.music.chord import Chord
from llamatron.music.note import Degree, Note, NoteName, Rest
from llamatron.exporters.ableton_project import DEFAULT_TEMPLATE, AbletonProject, Attribute, ElementPath, Tag
from llamatron.music.scale import Scale, ScaleType
from llamatron.music.time_signature import TimeSignature
from llamatron.grid.clip import Clip
from llamatron.grid.clip_grid import ClipGrid
from llamatron.grid.clip_row import ClipRow
from llamatron.grid.clip_column import ClipColumn

QUARTER = 0.25
C4 = Note(name='C', octave_number=4, length=QUARTER)
D4 = Note(name='D', octave_number=4, length=QUARTER)
C_MAJOR = Scale(root=Note(name='C', octave_number=4), typ=ScaleType.MAJOR)
A_MINOR = Scale(root=Note(name='A', octave_number=3), typ=ScaleType.MINOR)
SHARED_ID_TAGS = re.compile(r'(Target|Targets\.\d+|Pointee)$')

# Names the tests give to their own things, and other values they use.
READ_BYTES = 'rb'
MY_SONG = 'my_song'
WARNING = 'warning'
WB = 'wb'
ENUMEVENT = 'EnumEvent'
# Time signatures the tests set, and how Live's main track encodes them: beats from 0, plus 99 for each doubling of the unit.
WALTZ = '3/4'
COMPOUND_DUPLE = '6/8'
COMMON_TIME_CODE = '201'
WALTZ_CODE = '200'
VERSE = 'Verse'
TRUE = 'true'
FALSE = 'false'
MELODY = 'Melody'
BASS = 'Bass'
AUDIOTRACK = 'AudioTrack'
PREHEARTRACK = 'PreHearTrack'
MY_RIFF = 'My Riff'
LOOP = 'Loop'
LOOPSTART = 'LoopStart'
LOOPEND = 'LoopEnd'
OUTMARKER = 'OutMarker'
HIDDENLOOPEND = 'HiddenLoopEnd'
CHORDS = 'Chords'
RIFF = 'Riff'
DISABLED = 'Disabled'
C4_2 = 'C4'
ELSEWHERE = 'elsewhere'
OUTPUT = 'output'
SONG = 'song'


def template_root():
    with open(DEFAULT_TEMPLATE, READ_BYTES) as file:
        return ET.fromstring(gzip.decompress(file.read()))


class ProjectTestCase(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = os.path.join(temporary.name, MY_SONG)
        self.song = ClipGrid()

    def export(self, **options):
        """Export and return what was printed."""
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            AbletonProject(directory=self.directory, grid=self.song, **options).export()
        return output.getvalue()

    def live_set(self):
        self.export()
        return self.read_set()

    def read_set(self):
        path = os.path.join(self.directory, 'my_song.als')
        with open(path, READ_BYTES) as file:
            return ET.fromstring(gzip.decompress(file.read())).find(Tag.LIVE_SET)

    def one_clip_set(self, clip):
        track = self.song.add_column(ClipColumn())
        scene = self.song.add_row(ClipRow())
        self.song.set_clip(row=scene, column=track, clip=clip)
        return self.live_set()

    def first_clip(self, live_set):
        slots = live_set.find('Tracks/MidiTrack/DeviceChain/MainSequencer/ClipSlotList')
        return slots[0].find('ClipSlot/Value/MidiClip')

    def clip_notes(self, clip):
        """Return (MIDI number, time, duration) for each note in a Live clip."""
        return sorted(
            (int(key_track.find(Tag.MIDI_KEY).get(Tag.VALUE)),
             float(event.get(Attribute.TIME)), float(event.get(Attribute.DURATION)))
            for key_track in clip.find('Notes/KeyTracks')
            for event in key_track.find(Tag.NOTES)
        )


class TestTemplate(unittest.TestCase):

    def test_default_template_is_from_live_12_and_has_a_clip_to_copy(self):
        root = template_root()
        self.assertTrue(root.get(Attribute.MINOR_VERSION).startswith('12.'))
        track = root.find('LiveSet/Tracks/MidiTrack')
        slots = track.find('DeviceChain/MainSequencer/ClipSlotList')
        self.assertIsNotNone(slots.find('.//MidiClip'))


class TestWriting(ProjectTestCase):

    def test_writes_gzipped_xml_named_after_the_directory(self):
        self.one_clip_set(Clip(notes=[C4]))
        self.assertEqual(os.listdir(self.directory), ['my_song.als'])
        with open(os.path.join(self.directory, 'my_song.als'), READ_BYTES) as file:
            data = gzip.decompress(file.read())
        self.assertTrue(data.startswith(b'<?xml version="1.0" encoding="UTF-8"?>\n<Ableton '))

    def test_keeps_the_template_version(self):
        self.one_clip_set(Clip(notes=[C4]))
        with open(os.path.join(self.directory, 'my_song.als'), READ_BYTES) as file:
            root = ET.fromstring(gzip.decompress(file.read()))
        self.assertEqual(root.attrib, template_root().attrib)

    def test_path_property(self):
        project = AbletonProject(directory='out/my_song', grid=self.song)
        self.assertEqual(project.path(), os.path.join('out/my_song', 'my_song.als'))

    def test_every_run_gives_the_same_file(self):
        self.one_clip_set(Clip(notes=[C4]))
        path = os.path.join(self.directory, 'my_song.als')
        with open(path, READ_BYTES) as file:
            first = file.read()
        os.remove(path)
        self.export()
        with open(path, READ_BYTES) as file:
            self.assertEqual(file.read(), first)


class TestExistingFiles(ProjectTestCase):

    def setUp(self):
        super().setUp()
        track = self.song.add_column(ClipColumn())
        self.song.set_clip(row=self.song.add_row(ClipRow()), column=track, clip=Clip(notes=[C4]))
        os.makedirs(self.directory)

    def write(self, filename):
        with open(os.path.join(self.directory, filename), WB) as file:
            file.write(b'keep me')

    def read(self, filename):
        with open(os.path.join(self.directory, filename), READ_BYTES) as file:
            return file.read()

    def test_existing_set_stops_with_a_warning_and_is_kept(self):
        self.write('my_song.als')
        output = self.export()
        self.assertIn('warning: stopping', output)
        self.assertEqual(self.read('my_song.als'), b'keep me')

    def test_other_files_are_kept_without_a_word(self):
        self.write('notes.txt')
        output = self.export()
        self.assertNotIn(WARNING, output)
        self.assertEqual(self.read('notes.txt'), b'keep me')
        self.assertEqual(sorted(os.listdir(self.directory)), ['my_song.als', 'notes.txt'])

    def test_no_warning_for_an_empty_directory(self):
        self.assertEqual(self.export(), '')


class TestTempo(ProjectTestCase):

    def tempo_values(self, live_set):
        main_track = live_set.find(Tag.MAIN_TRACK)
        tempo = main_track.find('DeviceChain/Mixer/Tempo')
        target = tempo.find(ElementPath.AUTOMATION_TARGET).get(Attribute.ID)
        events = [
            event.get(Tag.VALUE)
            for envelope in main_track.find('AutomationEnvelopes/Envelopes')
            if envelope.find('EnvelopeTarget/PointeeId').get(Tag.VALUE) == target
            for event in envelope.find('Automation/Events')
        ]
        return tempo.find(ElementPath.MANUAL).get(Tag.VALUE), events

    def test_song_tempo_sets_the_control_and_its_automation(self):
        self.song.set_tempo(95)
        self.song.add_column(ClipColumn())
        self.song.add_row(ClipRow())
        self.assertEqual(self.tempo_values(self.live_set()), ('95', ['95']))

    def test_other_automation_is_left_alone(self):
        self.song.set_tempo(95)
        self.song.add_column(ClipColumn())
        self.song.add_row(ClipRow())
        live_set = self.live_set()
        values = [event.get(Tag.VALUE) for event in live_set.find('MainTrack/AutomationEnvelopes').iter(ENUMEVENT)]
        self.assertEqual(values, [COMMON_TIME_CODE])

    def test_the_time_signature_sets_its_control_and_its_automation_as_one_number(self):
        self.song.set_time_signature(TimeSignature.from_text(WALTZ))
        self.song.add_column(ClipColumn())
        self.song.add_row(ClipRow())
        live_set = self.live_set()
        signature = live_set.find(Tag.MAIN_TRACK).find(ElementPath.TIME_SIGNATURE)
        self.assertEqual(signature.find(ElementPath.MANUAL).get(Tag.VALUE), WALTZ_CODE)
        values = [event.get(Tag.VALUE) for event in live_set.find('MainTrack/AutomationEnvelopes').iter(ENUMEVENT)]
        self.assertEqual(values, [WALTZ_CODE])

    def clip_signature(self, clip):
        """Return the clip's time signature in a Live set, as the pair of numbers Live writes."""
        self.song.set_time_signature(TimeSignature.from_text(WALTZ))
        track = self.song.add_column(ClipColumn())
        scene = self.song.add_row(ClipRow())
        self.song.set_clip(row=scene, column=track, clip=clip)
        element = self.first_clip(self.live_set())
        return (element.find(ElementPath.CLIP_SIGNATURE_BEATS).get(Tag.VALUE), element.find(ElementPath.CLIP_SIGNATURE_UNIT).get(Tag.VALUE))

    def test_a_clip_shows_the_song_time_signature(self):
        self.assertEqual(self.clip_signature(Clip(notes=[C4])), ('3', '4'))

    def test_a_clip_whose_pattern_has_its_own_time_signature_shows_that_one(self):
        self.assertEqual(self.clip_signature(Clip(notes=[C4], time_signature=TimeSignature.from_text(COMPOUND_DUPLE))), ('6', '8'))

    def test_rejects_tempos_live_cannot_use(self):
        self.song.add_column(ClipColumn())
        self.song.add_row(ClipRow())
        for tempo in [10, 19.9, 1000]:
            with self.subTest(tempo=tempo):
                self.song.set_tempo(tempo)
                with self.assertRaises(ValueError):
                    self.export()
        self.assertFalse(os.path.exists(os.path.join(self.directory, 'my_song.als')))

    def test_rejects_scene_tempos_live_cannot_use(self):
        self.song.add_column(ClipColumn())
        self.song.add_row(ClipRow(tempo=10))
        with self.assertRaises(ValueError):
            self.export()


class TestScenes(ProjectTestCase):

    def test_one_scene_per_song_scene_with_names_and_ids(self):
        self.song.add_column(ClipColumn())
        self.song.add_row(ClipRow(name=VERSE))
        self.song.add_row(ClipRow())
        scenes = self.live_set().find(Tag.SCENES)
        self.assertEqual(
            [(scene.get(Attribute.ID), scene.find(ElementPath.NAME).get(Tag.VALUE)) for scene in scenes],
            [('0', VERSE), ('1', '')],
        )

    def test_scene_tempo_is_only_enabled_when_set(self):
        self.song.set_tempo(100)
        self.song.add_column(ClipColumn())
        self.song.add_row(ClipRow(tempo=90))
        self.song.add_row(ClipRow())
        scenes = self.live_set().find(Tag.SCENES)
        self.assertEqual(
            [(scene.find(ElementPath.SCENE_TEMPO).get(Tag.VALUE), scene.find(ElementPath.TEMPO_ENABLED).get(Tag.VALUE))
             for scene in scenes],
            [('90', TRUE), ('100', FALSE)],
        )

    def test_can_have_more_scenes_than_the_template(self):
        self.song.add_column(ClipColumn())
        for _ in range(30):
            self.song.add_row(ClipRow())
        live_set = self.live_set()
        self.assertEqual(len(live_set.find(Tag.SCENES)), 30)

    def test_rejects_a_song_without_scenes_or_tracks(self):
        with self.assertRaises(ValueError):
            self.export()
        self.song.add_column(ClipColumn())
        with self.assertRaises(ValueError):
            self.export()


class TestTracks(ProjectTestCase):

    def setUp(self):
        super().setUp()
        self.first = self.song.add_column(ClipColumn(name=MELODY))
        self.second = self.song.add_column(ClipColumn())
        self.third = self.song.add_column(ClipColumn(name=BASS))
        self.scenes = [self.song.add_row(ClipRow()) for _ in range(3)]

    def test_one_midi_track_per_song_track_with_returns_kept_after_them(self):
        tags = [track.tag for track in self.live_set().find(Tag.TRACKS)]
        self.assertEqual(tags, [Tag.MIDI_TRACK] * 3 + [Tag.RETURN_TRACK] * 2)

    def test_track_names(self):
        tracks = self.live_set().find(Tag.TRACKS).findall(Tag.MIDI_TRACK)
        self.assertEqual(
            [(track.find('Name/EffectiveName').get(Tag.VALUE), track.find('Name/UserName').get(Tag.VALUE))
             for track in tracks],
            [(MELODY, MELODY), ('2-MIDI', ''), (BASS, BASS)],
        )

    def test_every_track_has_one_slot_per_scene_numbered_in_order(self):
        for track in self.live_set().find(Tag.TRACKS).findall(Tag.MIDI_TRACK):
            for path in ['DeviceChain/MainSequencer/ClipSlotList', 'DeviceChain/FreezeSequencer/ClipSlotList']:
                self.assertEqual([slot.get(Attribute.ID) for slot in track.find(path)], ['0', '1', '2'])

    def test_track_ids_are_unique(self):
        ids = [track.get(Attribute.ID) for track in self.live_set().find(Tag.TRACKS)]
        self.assertEqual(len(ids), len(set(ids)))

    def test_shared_ids_are_unique_and_below_the_next_id(self):
        live_set = self.live_set()
        ids = [
            int(element.get(Attribute.ID))
            for track in live_set.find(Tag.TRACKS).findall(Tag.MIDI_TRACK)
            for element in track.iter()
            if Attribute.ID in element.attrib and SHARED_ID_TAGS.search(element.tag)
        ]
        others = [
            int(element.get(Attribute.ID))
            for section in [live_set.find(Tag.MAIN_TRACK), live_set.find(PREHEARTRACK)]
            + live_set.find(Tag.TRACKS).findall(Tag.RETURN_TRACK)
            for element in section.iter()
            if Attribute.ID in element.attrib and SHARED_ID_TAGS.search(element.tag)
        ]
        repeated = [number for number, count in collections.Counter(ids + others).items() if count > 1]
        self.assertEqual(repeated, [])
        self.assertLess(max(ids + others), int(live_set.find(Tag.NEXT_POINTEE_ID).get(Tag.VALUE)))

    def test_no_clips_on_frozen_slots_and_only_filled_slots_have_clips(self):
        self.song.set_clip(row=self.scenes[1], column=self.second, clip=Clip(notes=[C4]))
        tracks = self.live_set().find(Tag.TRACKS).findall(Tag.MIDI_TRACK)
        filled = [
            [slot.find('ClipSlot/Value/MidiClip') is not None
             for slot in track.find('DeviceChain/MainSequencer/ClipSlotList')]
            for track in tracks
        ]
        self.assertEqual(filled, [
            [False, False, False], [False, True, False], [False, False, False],
        ])
        for track in tracks:
            self.assertIsNone(track.find('DeviceChain/FreezeSequencer').find('.//MidiClip'))

    def test_muted_tracks_start_switched_off(self):
        self.second.set_mute(True)
        tracks = self.live_set().find(Tag.TRACKS).findall(Tag.MIDI_TRACK)
        self.assertEqual(
            [track.find('DeviceChain/Mixer/Speaker/Manual').get(Tag.VALUE) for track in tracks],
            [TRUE, FALSE, TRUE],
        )

    def test_no_audio_tracks_are_left(self):
        self.assertEqual(self.live_set().find(Tag.TRACKS).findall(AUDIOTRACK), [])


class TestClips(ProjectTestCase):

    def test_name_and_times(self):
        clip = self.first_clip(self.one_clip_set(Clip(name=MY_RIFF, notes=[C4, D4])))
        self.assertEqual(clip.find(ElementPath.NAME).get(Tag.VALUE), MY_RIFF)
        self.assertEqual(clip.find(ElementPath.CURRENT_END).get(Tag.VALUE), '2')
        loop = clip.find(LOOP)
        self.assertEqual(
            {tag: loop.find(tag).get(Tag.VALUE) for tag in [LOOPSTART, LOOPEND, OUTMARKER, HIDDENLOOPEND]},
            {LOOPSTART: '0', LOOPEND: '2', OUTMARKER: '2', HIDDENLOOPEND: '2'},
        )

    def test_clip_without_a_name(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[C4])))
        self.assertEqual(clip.find(ElementPath.NAME).get(Tag.VALUE), '')

    def test_set_length_sets_the_loop(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[C4], length=2)))
        self.assertEqual(clip.find('Loop/LoopEnd').get(Tag.VALUE), '8')

    def test_empty_clip_still_gets_a_length(self):
        clip = self.first_clip(self.one_clip_set(Clip()))
        self.assertEqual(clip.find('Loop/LoopEnd').get(Tag.VALUE), '4')
        self.assertEqual(len(clip.find('Notes/KeyTracks')), 0)

    def test_clip_has_no_groove_so_notes_stay_on_their_times(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[C4])))
        self.assertEqual(clip.find('GrooveSettings/GrooveId').get(Tag.VALUE), '-1')

    def test_clip_follows_the_same_order_of_details_as_the_template(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[C4])))
        template_clip = template_root().find('LiveSet/Tracks/MidiTrack').find('.//MidiClip')
        self.assertEqual([child.tag for child in clip], [child.tag for child in template_clip])


class TestArrangement(ProjectTestCase):

    def setUp(self):
        super().setUp()
        self.melody = self.song.add_column(ClipColumn(name=MELODY))
        self.chords = self.song.add_column(ClipColumn(name=CHORDS))

    def clips(self, *, live_set, number=0):
        track = live_set.find(Tag.TRACKS).findall(Tag.MIDI_TRACK)[number]
        return list(track.find('DeviceChain/MainSequencer/ClipTimeable/ArrangerAutomation/Events'))

    def test_clips_play_one_after_another_from_the_start(self):
        for length in [1, 2, 0.5]:
            scene = self.song.add_row(ClipRow())
            self.song.set_clip(row=scene, column=self.melody, clip=Clip(name=RIFF, notes=[Note(name=NoteName.C, octave_number=4, length=length)]))
        clips = self.clips(live_set=self.live_set())
        self.assertEqual([clip.get(Attribute.TIME) for clip in clips], ['0', '4', '12'])
        self.assertEqual([clip.find(ElementPath.CURRENT_START).get(Tag.VALUE) for clip in clips], ['0', '4', '12'])
        self.assertEqual([clip.find(ElementPath.CURRENT_END).get(Tag.VALUE) for clip in clips], ['4', '12', '14'])

    def test_the_loop_is_relative_to_the_clip(self):
        self.song.add_row(ClipRow())
        scene = self.song.add_row(ClipRow())
        self.song.set_clip(row=self.song.get_rows()[0], column=self.melody, clip=Clip(notes=[Note(name=NoteName.C, octave_number=4, length=1)]))
        self.song.set_clip(row=scene, column=self.melody, clip=Clip(notes=[Note(name=NoteName.C, octave_number=4, length=1)]))
        clip = self.clips(live_set=self.live_set())[1]
        self.assertEqual(clip.find('Loop/LoopStart').get(Tag.VALUE), '0')
        self.assertEqual(clip.find('Loop/LoopEnd').get(Tag.VALUE), '4')

    def test_notes_are_relative_to_the_clip(self):
        self.song.add_row(ClipRow())
        scene = self.song.add_row(ClipRow())
        self.song.set_clip(row=self.song.get_rows()[0], column=self.melody, clip=Clip(notes=[Note(name=NoteName.C, octave_number=4, length=1)]))
        self.song.set_clip(row=scene, column=self.melody, clip=Clip(notes=[Rest(0.25), C4]))
        clip = self.clips(live_set=self.live_set())[1]
        self.assertEqual(self.clip_notes(clip), [(48, 1, 1)])

    def test_a_scene_lasts_as_long_as_its_longest_clip(self):
        first = self.song.add_row(ClipRow())
        second = self.song.add_row(ClipRow())
        self.song.set_clip(row=first, column=self.melody, clip=Clip(notes=[Note(name=NoteName.C, octave_number=4, length=1)]))
        self.song.set_clip(row=first, column=self.chords, clip=Clip(notes=[Note(name=NoteName.C, octave_number=3, length=2)]))
        self.song.set_clip(row=second, column=self.chords, clip=Clip(notes=[Note(name=NoteName.C, octave_number=3, length=1)]))
        live_set = self.live_set()
        self.assertEqual([clip.get(Attribute.TIME) for clip in self.clips(live_set=live_set, number=1)], ['0', '8'])
        self.assertEqual(self.clips(live_set=live_set, number=0)[0].find(ElementPath.CURRENT_END).get(Tag.VALUE), '4')

    def test_a_scene_with_no_clips_still_takes_up_time(self):
        self.song.add_row(ClipRow())
        scene = self.song.add_row(ClipRow())
        self.song.set_clip(row=scene, column=self.melody, clip=Clip(notes=[C4]))
        clips = self.clips(live_set=self.live_set())
        self.assertEqual([clip.get(Attribute.TIME) for clip in clips], ['4'])

    def test_clips_are_in_session_view_too(self):
        scene = self.song.add_row(ClipRow())
        self.song.set_clip(row=scene, column=self.melody, clip=Clip(name=RIFF, notes=[C4]))
        live_set = self.live_set()
        session = self.first_clip(live_set)
        arrangement = self.clips(live_set=live_set)[0]
        self.assertEqual(session.get(Attribute.TIME), '0')
        self.assertEqual(session.find(ElementPath.TAKE_ID).get(Tag.VALUE), self.template_session_take())
        self.assertEqual(session.find(ElementPath.NAME).get(Tag.VALUE), arrangement.find(ElementPath.NAME).get(Tag.VALUE))
        self.assertEqual(self.clip_notes(session), self.clip_notes(arrangement))

    def template_session_take(self):
        return template_root().find('LiveSet/Tracks/MidiTrack').find('.//MidiClip/TakeId').get(Tag.VALUE)

    def test_arrangement_clips_use_the_details_from_a_real_arrangement_clip(self):
        scene = self.song.add_row(ClipRow())
        self.song.set_clip(row=scene, column=self.melody, clip=Clip(notes=[C4]))
        clip = self.clips(live_set=self.live_set())[0]
        self.assertEqual(clip.find(ElementPath.TAKE_ID).get(Tag.VALUE), '1')
        self.assertEqual(clip.find('GrooveSettings/GrooveId').get(Tag.VALUE), '-1')
        self.assertEqual(clip.find(DISABLED).get(Tag.VALUE), FALSE)

    def tempo_events(self, live_set):
        main_track = live_set.find(Tag.MAIN_TRACK)
        target = main_track.find('DeviceChain/Mixer/Tempo/AutomationTarget').get(Attribute.ID)
        for envelope in main_track.find('AutomationEnvelopes/Envelopes'):
            if envelope.find('EnvelopeTarget/PointeeId').get(Tag.VALUE) == target:
                return list(envelope.find('Automation/Events'))
        return []

    def test_no_tempo_changes_when_no_scene_has_a_tempo(self):
        self.song.add_row(ClipRow())
        self.assertEqual(len(self.tempo_events(self.live_set())), 1)

    def test_scene_tempos_change_the_tempo_when_each_scene_starts(self):
        self.song.set_tempo(100)
        first = self.song.add_row(ClipRow(tempo=90))
        second = self.song.add_row(ClipRow())
        self.song.set_clip(row=first, column=self.melody, clip=Clip(notes=[Note(name=NoteName.C, octave_number=4, length=1)]))
        self.song.set_clip(row=second, column=self.melody, clip=Clip(notes=[Note(name=NoteName.C, octave_number=4, length=1)]))
        events = self.tempo_events(self.live_set())
        self.assertEqual(
            [(event.tag, event.get(Attribute.TIME), event.get(Tag.VALUE)) for event in events[1:]],
            [(Tag.FLOAT_EVENT, '0', '90'), (Tag.FLOAT_EVENT, '4', '100')],
        )
        self.assertEqual(events[0].get(Tag.VALUE), '100')
        ids = [event.get(Attribute.ID) for event in events]
        self.assertEqual(len(ids), len(set(ids)))


class TestNotes(ProjectTestCase):

    def test_lengths_become_beats(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[C4, Note(name=NoteName.D, octave_number=4, length=0.5), Note(name=NoteName.E, octave_number=4, length=0.125)])))
        self.assertEqual(self.clip_notes(clip), [(48, 0, 1), (50, 1, 2), (52, 3, 0.5)])

    def test_notes_are_grouped_by_pitch_in_order(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[D4, C4, D4])))
        key_tracks = clip.find('Notes/KeyTracks')
        self.assertEqual([track.find(Tag.MIDI_KEY).get(Tag.VALUE) for track in key_tracks], ['48', '50'])
        self.assertEqual([track.get(Attribute.ID) for track in key_tracks], ['0', '1'])
        self.assertEqual([event.get(Attribute.TIME) for event in key_tracks[1].find(Tag.NOTES)], ['0', '2'])

    def test_note_event_details(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[C4])))
        event = clip.find('Notes/KeyTracks/KeyTrack/Notes/MidiNoteEvent')
        self.assertEqual(event.attrib, {
            Attribute.TIME: '0', Attribute.DURATION: '1', Attribute.VELOCITY: '127', Attribute.OFF_VELOCITY: '64', Attribute.NOTE_ID: '1',
        })
        self.assertEqual(clip.find('Notes/NoteIdGenerator/NextId').get(Tag.VALUE), '2')

    def test_note_ids_are_unique_within_a_clip(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[C4, D4, C4, D4])))
        ids = [event.get(Attribute.NOTE_ID) for event in clip.iter(Tag.MIDI_NOTE_EVENT)]
        self.assertEqual(sorted(ids), ['1', '2', '3', '4'])
        self.assertEqual(clip.find('Notes/NoteIdGenerator/NextId').get(Tag.VALUE), '5')

    def test_rests_move_later_notes(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[Rest(0.5), C4])))
        self.assertEqual(self.clip_notes(clip), [(48, 2, 1)])
        self.assertEqual(clip.find('Loop/LoopEnd').get(Tag.VALUE), '3')

    def test_chords_start_together(self):
        chord = Chord([C4, Note(name=NoteName.E, octave_number=4, length=0.5)])
        clip = self.first_clip(self.one_clip_set(Clip(notes=[chord])))
        self.assertEqual(self.clip_notes(clip), [(48, 0, 1), (52, 0, 2)])

    def test_triplets_keep_their_timing(self):
        third = Note(name=NoteName.C, octave_number=4, length=Fraction(1, 12))
        clip = self.first_clip(self.one_clip_set(Clip(notes=[third, third, third])))
        for (_, time, duration), start in zip(self.clip_notes(clip), [0, 1 / 3, 2 / 3]):
            self.assertAlmostEqual(time, start)
            self.assertAlmostEqual(duration, 1 / 3)

    def test_notes_are_cut_at_the_end_of_the_clip(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[Note(name=NoteName.C, octave_number=4, length=1)], length=0.5)))
        self.assertEqual(self.clip_notes(clip), [(48, 0, 2)])

    def test_note_length_is_used(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[C4_2], note_length=0.5)))
        self.assertEqual(self.clip_notes(clip), [(48, 0, 2)])

    def test_degrees_use_the_scale_at_export(self):
        track = self.song.add_column(ClipColumn())
        scene = self.song.add_row(ClipRow(scale=A_MINOR))
        self.song.set_clip(row=scene, column=track, clip=Clip(notes=[Degree(number=3, length=QUARTER)]))
        clip = self.first_clip(self.live_set())
        self.assertEqual(self.clip_notes(clip), [(48, 0, 1)])

    def test_one_clip_can_use_different_scales_in_different_scenes(self):
        track = self.song.add_column(ClipColumn())
        major = self.song.add_row(ClipRow(scale=C_MAJOR))
        minor = self.song.add_row(ClipRow(scale=A_MINOR))
        clip = Clip(notes=[Degree(number=1, length=QUARTER)])
        self.song.set_clip(row=major, column=track, clip=clip)
        self.song.set_clip(row=minor, column=track, clip=clip)
        slots = self.live_set().find('Tracks/MidiTrack/DeviceChain/MainSequencer/ClipSlotList')
        played = [
            self.clip_notes(slot.find('ClipSlot/Value/MidiClip'))[0][0] for slot in slots
        ]
        self.assertEqual(played, [48, 45])

    def test_invalid_clips_write_nothing(self):
        track = self.song.add_column(ClipColumn())
        scene = self.song.add_row(ClipRow())
        self.song.set_clip(row=scene, column=track, clip=Clip(notes=[Degree(number=1, length=QUARTER)]))
        with self.assertRaises(ValueError):
            self.export()
        self.assertEqual(os.listdir(self.directory), [])


class TestTemplates(ProjectTestCase):

    def write_template(self, change):
        root = template_root()
        change(root)
        path = os.path.join(os.path.dirname(self.directory), 'other.als')
        data = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root)
        with open(path, WB) as file:
            file.write(gzip.compress(data))
        return path

    def setUp(self):
        super().setUp()
        self.song.add_column(ClipColumn())
        self.song.add_row(ClipRow())

    def test_rejects_a_template_from_another_version(self):
        template = self.write_template(lambda root: root.set(Attribute.MINOR_VERSION, '11.0_11300'))
        with self.assertRaises(ValueError):
            self.export(template=template)

    def test_rejects_a_template_without_a_midi_track(self):
        def remove_midi_tracks(root):
            tracks = root.find('LiveSet/Tracks')
            for track in tracks.findall(Tag.MIDI_TRACK):
                tracks.remove(track)
        with self.assertRaises(ValueError):
            self.export(template=self.write_template(remove_midi_tracks))

    def test_missing_template_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.export(template=os.path.join(self.directory, 'missing.als'))


class TestFields(unittest.TestCase):

    def test_keeps_its_values(self):
        song = ClipGrid()
        project = AbletonProject(directory=OUTPUT, grid=song, template='other.als')
        self.assertEqual(project.get_directory(), OUTPUT)
        self.assertIs(project.get_grid(), song)
        self.assertEqual(project.get_template(), 'other.als')

    def test_template_defaults_to_the_one_installed_with_the_code(self):
        self.assertEqual(AbletonProject(directory=OUTPUT, grid=ClipGrid()).get_template(), DEFAULT_TEMPLATE)
        self.assertIsInstance(DEFAULT_TEMPLATE, Path)

    def test_rejects_invalid_values(self):
        for directory in ['', None, 1]:
            with self.subTest(directory=directory):
                with self.assertRaises(ValueError):
                    AbletonProject(directory=directory, grid=ClipGrid())
        for song in [None, SONG, ClipColumn()]:
            with self.subTest(song=song):
                with self.assertRaises(ValueError):
                    AbletonProject(directory=OUTPUT, grid=song)
        for template in ['', None, 1]:
            with self.subTest(template=template):
                with self.assertRaises(ValueError):
                    AbletonProject(directory=OUTPUT, grid=ClipGrid(), template=template)

    def test_fields_can_be_edited_and_are_validated(self):
        project = AbletonProject(directory=OUTPUT, grid=ClipGrid())
        project.set_directory(ELSEWHERE)
        self.assertEqual(project.get_directory(), ELSEWHERE)
        with self.assertRaises(ValueError):
            project.set_directory(None)
        self.assertEqual(project.get_directory(), ELSEWHERE)

    def test_creating_it_does_not_create_the_directory(self):
        with tempfile.TemporaryDirectory() as parent:
            directory = os.path.join(parent, OUTPUT)
            AbletonProject(directory=directory, grid=ClipGrid())
            self.assertFalse(os.path.exists(directory))


class TestFileName(unittest.TestCase):

    def test_the_name_sets_the_file_name(self):
        with tempfile.TemporaryDirectory() as directory:
            project = AbletonProject(directory=directory, grid=ClipGrid(), name='tune-007')
            self.assertEqual(os.path.basename(project.path()), 'tune-007.als')


if __name__ == '__main__':
    unittest.main()
