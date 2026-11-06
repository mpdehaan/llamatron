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

from llamatron.chord import Chord
from llamatron.note import Degree, Note, Rest
from llamatron.renderers.ableton_project import DEFAULT_TEMPLATE, AbletonProject
from llamatron.scale import Scale, ScaleType
from llamatron.song import Clip, Scene, Song, Track

QUARTER = 0.25
C4 = Note('C', 4, QUARTER)
D4 = Note('D', 4, QUARTER)
C_MAJOR = Scale(Note('C', 4), ScaleType.MAJOR)
A_MINOR = Scale(Note('A', 3), ScaleType.MINOR)
SHARED_ID_TAGS = re.compile(r'(Target|Targets\.\d+|Pointee)$')


def template_root():
    with open(DEFAULT_TEMPLATE, 'rb') as file:
        return ET.fromstring(gzip.decompress(file.read()))


class ProjectTestCase(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = os.path.join(temporary.name, 'my_song')
        self.song = Song()

    def render(self, **options):
        """Render and return what was printed."""
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            AbletonProject(self.directory, self.song, **options).render()
        return output.getvalue()

    def live_set(self):
        self.render()
        return self.read_set()

    def read_set(self):
        path = os.path.join(self.directory, 'my_song.als')
        with open(path, 'rb') as file:
            return ET.fromstring(gzip.decompress(file.read())).find('LiveSet')

    def one_clip_set(self, clip):
        track = self.song.add_track(Track())
        scene = self.song.add_scene(Scene())
        self.song.set_clip(scene, track, clip)
        return self.live_set()

    def first_clip(self, live_set):
        slots = live_set.find('Tracks/MidiTrack/DeviceChain/MainSequencer/ClipSlotList')
        return slots[0].find('ClipSlot/Value/MidiClip')

    def clip_notes(self, clip):
        """Return (MIDI number, time, duration) for each note in a Live clip."""
        return sorted(
            (int(key_track.find('MidiKey').get('Value')),
             float(event.get('Time')), float(event.get('Duration')))
            for key_track in clip.find('Notes/KeyTracks')
            for event in key_track.find('Notes')
        )


class TestTemplate(unittest.TestCase):

    def test_default_template_is_from_live_12_and_has_a_clip_to_copy(self):
        root = template_root()
        self.assertTrue(root.get('MinorVersion').startswith('12.'))
        track = root.find('LiveSet/Tracks/MidiTrack')
        slots = track.find('DeviceChain/MainSequencer/ClipSlotList')
        self.assertIsNotNone(slots.find('.//MidiClip'))


class TestWriting(ProjectTestCase):

    def test_writes_gzipped_xml_named_after_the_directory(self):
        self.one_clip_set(Clip(notes=[C4]))
        self.assertEqual(os.listdir(self.directory), ['my_song.als'])
        with open(os.path.join(self.directory, 'my_song.als'), 'rb') as file:
            data = gzip.decompress(file.read())
        self.assertTrue(data.startswith(b'<?xml version="1.0" encoding="UTF-8"?>\n<Ableton '))

    def test_keeps_the_template_version(self):
        self.one_clip_set(Clip(notes=[C4]))
        with open(os.path.join(self.directory, 'my_song.als'), 'rb') as file:
            root = ET.fromstring(gzip.decompress(file.read()))
        self.assertEqual(root.attrib, template_root().attrib)

    def test_path_property(self):
        project = AbletonProject('out/my_song', self.song)
        self.assertEqual(project.path, os.path.join('out/my_song', 'my_song.als'))

    def test_every_run_gives_the_same_file(self):
        self.one_clip_set(Clip(notes=[C4]))
        path = os.path.join(self.directory, 'my_song.als')
        with open(path, 'rb') as file:
            first = file.read()
        os.remove(path)
        self.render()
        with open(path, 'rb') as file:
            self.assertEqual(file.read(), first)


class TestExistingFiles(ProjectTestCase):

    def setUp(self):
        super().setUp()
        track = self.song.add_track(Track())
        self.song.set_clip(self.song.add_scene(Scene()), track, Clip(notes=[C4]))
        os.makedirs(self.directory)

    def write(self, filename):
        with open(os.path.join(self.directory, filename), 'wb') as file:
            file.write(b'keep me')

    def read(self, filename):
        with open(os.path.join(self.directory, filename), 'rb') as file:
            return file.read()

    def test_existing_set_stops_with_a_warning_and_is_kept(self):
        self.write('my_song.als')
        output = self.render()
        self.assertIn('warning: stopping', output)
        self.assertEqual(self.read('my_song.als'), b'keep me')

    def test_other_files_are_kept_and_warned_about(self):
        self.write('001-001.mid')
        output = self.render()
        self.assertIn('warning', output)
        self.assertIn('001-001.mid', output)
        self.assertEqual(self.read('001-001.mid'), b'keep me')
        self.assertEqual(sorted(os.listdir(self.directory)), ['001-001.mid', 'my_song.als'])

    def test_no_warning_for_an_empty_directory(self):
        self.assertEqual(self.render(), '')


class TestTempo(ProjectTestCase):

    def tempo_values(self, live_set):
        main_track = live_set.find('MainTrack')
        tempo = main_track.find('DeviceChain/Mixer/Tempo')
        target = tempo.find('AutomationTarget').get('Id')
        events = [
            event.get('Value')
            for envelope in main_track.find('AutomationEnvelopes/Envelopes')
            if envelope.find('EnvelopeTarget/PointeeId').get('Value') == target
            for event in envelope.find('Automation/Events')
        ]
        return tempo.find('Manual').get('Value'), events

    def test_song_tempo_sets_the_control_and_its_automation(self):
        self.song.tempo = 95
        self.song.add_track(Track())
        self.song.add_scene(Scene())
        self.assertEqual(self.tempo_values(self.live_set()), ('95', ['95']))

    def test_other_automation_is_left_alone(self):
        self.song.tempo = 95
        self.song.add_track(Track())
        self.song.add_scene(Scene())
        live_set = self.live_set()
        values = [event.get('Value') for event in live_set.find('MainTrack/AutomationEnvelopes').iter('EnumEvent')]
        self.assertEqual(values, ['201'])

    def test_rejects_tempos_live_cannot_use(self):
        self.song.add_track(Track())
        self.song.add_scene(Scene())
        for tempo in [10, 19.9, 1000]:
            with self.subTest(tempo=tempo):
                self.song.tempo = tempo
                with self.assertRaises(ValueError):
                    self.render()
        self.assertFalse(os.path.exists(os.path.join(self.directory, 'my_song.als')))

    def test_rejects_scene_tempos_live_cannot_use(self):
        self.song.add_track(Track())
        self.song.add_scene(Scene(tempo=10))
        with self.assertRaises(ValueError):
            self.render()


class TestScenes(ProjectTestCase):

    def test_one_scene_per_song_scene_with_names_and_ids(self):
        self.song.add_track(Track())
        self.song.add_scene(Scene('Verse'))
        self.song.add_scene(Scene())
        scenes = self.live_set().find('Scenes')
        self.assertEqual(
            [(scene.get('Id'), scene.find('Name').get('Value')) for scene in scenes],
            [('0', 'Verse'), ('1', '')],
        )

    def test_scene_tempo_is_only_enabled_when_set(self):
        self.song.tempo = 100
        self.song.add_track(Track())
        self.song.add_scene(Scene(tempo=90))
        self.song.add_scene(Scene())
        scenes = self.live_set().find('Scenes')
        self.assertEqual(
            [(scene.find('Tempo').get('Value'), scene.find('IsTempoEnabled').get('Value'))
             for scene in scenes],
            [('90', 'true'), ('100', 'false')],
        )

    def test_can_have_more_scenes_than_the_template(self):
        self.song.add_track(Track())
        for _ in range(30):
            self.song.add_scene(Scene())
        live_set = self.live_set()
        self.assertEqual(len(live_set.find('Scenes')), 30)

    def test_rejects_a_song_without_scenes_or_tracks(self):
        with self.assertRaises(ValueError):
            self.render()
        self.song.add_track(Track())
        with self.assertRaises(ValueError):
            self.render()


class TestTracks(ProjectTestCase):

    def setUp(self):
        super().setUp()
        self.first = self.song.add_track(Track('Melody'))
        self.second = self.song.add_track(Track())
        self.third = self.song.add_track(Track('Bass'))
        self.scenes = [self.song.add_scene(Scene()) for _ in range(3)]

    def test_one_midi_track_per_song_track_with_returns_kept_after_them(self):
        tags = [track.tag for track in self.live_set().find('Tracks')]
        self.assertEqual(tags, ['MidiTrack'] * 3 + ['ReturnTrack'] * 2)

    def test_track_names(self):
        tracks = self.live_set().find('Tracks').findall('MidiTrack')
        self.assertEqual(
            [(track.find('Name/EffectiveName').get('Value'), track.find('Name/UserName').get('Value'))
             for track in tracks],
            [('Melody', 'Melody'), ('2-MIDI', ''), ('Bass', 'Bass')],
        )

    def test_every_track_has_one_slot_per_scene_numbered_in_order(self):
        for track in self.live_set().find('Tracks').findall('MidiTrack'):
            for path in ['DeviceChain/MainSequencer/ClipSlotList', 'DeviceChain/FreezeSequencer/ClipSlotList']:
                self.assertEqual([slot.get('Id') for slot in track.find(path)], ['0', '1', '2'])

    def test_track_ids_are_unique(self):
        ids = [track.get('Id') for track in self.live_set().find('Tracks')]
        self.assertEqual(len(ids), len(set(ids)))

    def test_shared_ids_are_unique_and_below_the_next_id(self):
        live_set = self.live_set()
        ids = [
            int(element.get('Id'))
            for track in live_set.find('Tracks').findall('MidiTrack')
            for element in track.iter()
            if 'Id' in element.attrib and SHARED_ID_TAGS.search(element.tag)
        ]
        others = [
            int(element.get('Id'))
            for section in [live_set.find('MainTrack'), live_set.find('PreHearTrack')]
            + live_set.find('Tracks').findall('ReturnTrack')
            for element in section.iter()
            if 'Id' in element.attrib and SHARED_ID_TAGS.search(element.tag)
        ]
        repeated = [number for number, count in collections.Counter(ids + others).items() if count > 1]
        self.assertEqual(repeated, [])
        self.assertLess(max(ids + others), int(live_set.find('NextPointeeId').get('Value')))

    def test_no_clips_on_frozen_slots_and_only_filled_slots_have_clips(self):
        self.song.set_clip(self.scenes[1], self.second, Clip(notes=[C4]))
        tracks = self.live_set().find('Tracks').findall('MidiTrack')
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
        self.second.mute = True
        tracks = self.live_set().find('Tracks').findall('MidiTrack')
        self.assertEqual(
            [track.find('DeviceChain/Mixer/Speaker/Manual').get('Value') for track in tracks],
            ['true', 'false', 'true'],
        )

    def test_no_audio_tracks_are_left(self):
        self.assertEqual(self.live_set().find('Tracks').findall('AudioTrack'), [])


class TestClips(ProjectTestCase):

    def test_name_and_times(self):
        clip = self.first_clip(self.one_clip_set(Clip('My Riff', notes=[C4, D4])))
        self.assertEqual(clip.find('Name').get('Value'), 'My Riff')
        self.assertEqual(clip.find('CurrentEnd').get('Value'), '2')
        loop = clip.find('Loop')
        self.assertEqual(
            {tag: loop.find(tag).get('Value') for tag in ['LoopStart', 'LoopEnd', 'OutMarker', 'HiddenLoopEnd']},
            {'LoopStart': '0', 'LoopEnd': '2', 'OutMarker': '2', 'HiddenLoopEnd': '2'},
        )

    def test_clip_without_a_name(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[C4])))
        self.assertEqual(clip.find('Name').get('Value'), '')

    def test_set_length_sets_the_loop(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[C4], length=2)))
        self.assertEqual(clip.find('Loop/LoopEnd').get('Value'), '8')

    def test_empty_clip_still_gets_a_length(self):
        clip = self.first_clip(self.one_clip_set(Clip()))
        self.assertEqual(clip.find('Loop/LoopEnd').get('Value'), '4')
        self.assertEqual(len(clip.find('Notes/KeyTracks')), 0)

    def test_clip_has_no_groove_so_notes_stay_on_their_times(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[C4])))
        self.assertEqual(clip.find('GrooveSettings/GrooveId').get('Value'), '-1')

    def test_clip_follows_the_same_order_of_details_as_the_template(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[C4])))
        template_clip = template_root().find('LiveSet/Tracks/MidiTrack').find('.//MidiClip')
        self.assertEqual([child.tag for child in clip], [child.tag for child in template_clip])


class TestArrangement(ProjectTestCase):

    def setUp(self):
        super().setUp()
        self.melody = self.song.add_track(Track('Melody'))
        self.chords = self.song.add_track(Track('Chords'))

    def clips(self, live_set, number=0):
        track = live_set.find('Tracks').findall('MidiTrack')[number]
        return list(track.find('DeviceChain/MainSequencer/ClipTimeable/ArrangerAutomation/Events'))

    def test_clips_play_one_after_another_from_the_start(self):
        for length in [1, 2, 0.5]:
            scene = self.song.add_scene(Scene())
            self.song.set_clip(scene, self.melody, Clip('Riff', notes=[Note('C', 4, length)]))
        clips = self.clips(self.live_set())
        self.assertEqual([clip.get('Time') for clip in clips], ['0', '4', '12'])
        self.assertEqual([clip.find('CurrentStart').get('Value') for clip in clips], ['0', '4', '12'])
        self.assertEqual([clip.find('CurrentEnd').get('Value') for clip in clips], ['4', '12', '14'])

    def test_the_loop_is_relative_to_the_clip(self):
        self.song.add_scene(Scene())
        scene = self.song.add_scene(Scene())
        self.song.set_clip(self.song.scenes[0], self.melody, Clip(notes=[Note('C', 4, 1)]))
        self.song.set_clip(scene, self.melody, Clip(notes=[Note('C', 4, 1)]))
        clip = self.clips(self.live_set())[1]
        self.assertEqual(clip.find('Loop/LoopStart').get('Value'), '0')
        self.assertEqual(clip.find('Loop/LoopEnd').get('Value'), '4')

    def test_notes_are_relative_to_the_clip(self):
        self.song.add_scene(Scene())
        scene = self.song.add_scene(Scene())
        self.song.set_clip(self.song.scenes[0], self.melody, Clip(notes=[Note('C', 4, 1)]))
        self.song.set_clip(scene, self.melody, Clip(notes=[Rest(0.25), C4]))
        clip = self.clips(self.live_set())[1]
        self.assertEqual(self.clip_notes(clip), [(48, 1, 1)])

    def test_a_scene_lasts_as_long_as_its_longest_clip(self):
        first = self.song.add_scene(Scene())
        second = self.song.add_scene(Scene())
        self.song.set_clip(first, self.melody, Clip(notes=[Note('C', 4, 1)]))
        self.song.set_clip(first, self.chords, Clip(notes=[Note('C', 3, 2)]))
        self.song.set_clip(second, self.chords, Clip(notes=[Note('C', 3, 1)]))
        live_set = self.live_set()
        self.assertEqual([clip.get('Time') for clip in self.clips(live_set, 1)], ['0', '8'])
        self.assertEqual(self.clips(live_set, 0)[0].find('CurrentEnd').get('Value'), '4')

    def test_a_scene_with_no_clips_still_takes_up_time(self):
        self.song.add_scene(Scene())
        scene = self.song.add_scene(Scene())
        self.song.set_clip(scene, self.melody, Clip(notes=[C4]))
        clips = self.clips(self.live_set())
        self.assertEqual([clip.get('Time') for clip in clips], ['4'])

    def test_clips_are_in_session_view_too(self):
        scene = self.song.add_scene(Scene())
        self.song.set_clip(scene, self.melody, Clip('Riff', notes=[C4]))
        live_set = self.live_set()
        session = self.first_clip(live_set)
        arrangement = self.clips(live_set)[0]
        self.assertEqual(session.get('Time'), '0')
        self.assertEqual(session.find('TakeId').get('Value'), self.template_session_take())
        self.assertEqual(session.find('Name').get('Value'), arrangement.find('Name').get('Value'))
        self.assertEqual(self.clip_notes(session), self.clip_notes(arrangement))

    def template_session_take(self):
        return template_root().find('LiveSet/Tracks/MidiTrack').find('.//MidiClip/TakeId').get('Value')

    def test_arrangement_clips_use_the_details_from_a_real_arrangement_clip(self):
        scene = self.song.add_scene(Scene())
        self.song.set_clip(scene, self.melody, Clip(notes=[C4]))
        clip = self.clips(self.live_set())[0]
        self.assertEqual(clip.find('TakeId').get('Value'), '1')
        self.assertEqual(clip.find('GrooveSettings/GrooveId').get('Value'), '-1')
        self.assertEqual(clip.find('Disabled').get('Value'), 'false')

    def tempo_events(self, live_set):
        main_track = live_set.find('MainTrack')
        target = main_track.find('DeviceChain/Mixer/Tempo/AutomationTarget').get('Id')
        for envelope in main_track.find('AutomationEnvelopes/Envelopes'):
            if envelope.find('EnvelopeTarget/PointeeId').get('Value') == target:
                return list(envelope.find('Automation/Events'))
        return []

    def test_no_tempo_changes_when_no_scene_has_a_tempo(self):
        self.song.add_scene(Scene())
        self.assertEqual(len(self.tempo_events(self.live_set())), 1)

    def test_scene_tempos_change_the_tempo_when_each_scene_starts(self):
        self.song.tempo = 100
        first = self.song.add_scene(Scene(tempo=90))
        second = self.song.add_scene(Scene())
        self.song.set_clip(first, self.melody, Clip(notes=[Note('C', 4, 1)]))
        self.song.set_clip(second, self.melody, Clip(notes=[Note('C', 4, 1)]))
        events = self.tempo_events(self.live_set())
        self.assertEqual(
            [(event.tag, event.get('Time'), event.get('Value')) for event in events[1:]],
            [('FloatEvent', '0', '90'), ('FloatEvent', '4', '100')],
        )
        self.assertEqual(events[0].get('Value'), '100')
        ids = [event.get('Id') for event in events]
        self.assertEqual(len(ids), len(set(ids)))


class TestNotes(ProjectTestCase):

    def test_lengths_become_beats(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[C4, Note('D', 4, 0.5), Note('E', 4, 0.125)])))
        self.assertEqual(self.clip_notes(clip), [(48, 0, 1), (50, 1, 2), (52, 3, 0.5)])

    def test_notes_are_grouped_by_pitch_in_order(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[D4, C4, D4])))
        key_tracks = clip.find('Notes/KeyTracks')
        self.assertEqual([track.find('MidiKey').get('Value') for track in key_tracks], ['48', '50'])
        self.assertEqual([track.get('Id') for track in key_tracks], ['0', '1'])
        self.assertEqual([event.get('Time') for event in key_tracks[1].find('Notes')], ['0', '2'])

    def test_note_event_details(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[C4])))
        event = clip.find('Notes/KeyTracks/KeyTrack/Notes/MidiNoteEvent')
        self.assertEqual(event.attrib, {
            'Time': '0', 'Duration': '1', 'Velocity': '127', 'OffVelocity': '64', 'NoteId': '1',
        })
        self.assertEqual(clip.find('Notes/NoteIdGenerator/NextId').get('Value'), '2')

    def test_note_ids_are_unique_within_a_clip(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[C4, D4, C4, D4])))
        ids = [event.get('NoteId') for event in clip.iter('MidiNoteEvent')]
        self.assertEqual(sorted(ids), ['1', '2', '3', '4'])
        self.assertEqual(clip.find('Notes/NoteIdGenerator/NextId').get('Value'), '5')

    def test_rests_move_later_notes(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[Rest(0.5), C4])))
        self.assertEqual(self.clip_notes(clip), [(48, 2, 1)])
        self.assertEqual(clip.find('Loop/LoopEnd').get('Value'), '3')

    def test_chords_start_together(self):
        chord = Chord([C4, Note('E', 4, 0.5)])
        clip = self.first_clip(self.one_clip_set(Clip(notes=[chord])))
        self.assertEqual(self.clip_notes(clip), [(48, 0, 1), (52, 0, 2)])

    def test_triplets_keep_their_timing(self):
        third = Note('C', 4, Fraction(1, 12))
        clip = self.first_clip(self.one_clip_set(Clip(notes=[third, third, third])))
        for (_, time, duration), start in zip(self.clip_notes(clip), [0, 1 / 3, 2 / 3]):
            self.assertAlmostEqual(time, start)
            self.assertAlmostEqual(duration, 1 / 3)

    def test_notes_are_cut_at_the_end_of_the_clip(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=[Note('C', 4, 1)], length=0.5)))
        self.assertEqual(self.clip_notes(clip), [(48, 0, 2)])

    def test_note_length_is_used(self):
        clip = self.first_clip(self.one_clip_set(Clip(notes=['C4'], note_length=0.5)))
        self.assertEqual(self.clip_notes(clip), [(48, 0, 2)])

    def test_degrees_use_the_scale_at_render(self):
        track = self.song.add_track(Track())
        scene = self.song.add_scene(Scene(scale=A_MINOR))
        self.song.set_clip(scene, track, Clip(notes=[Degree(3, QUARTER)]))
        clip = self.first_clip(self.live_set())
        self.assertEqual(self.clip_notes(clip), [(48, 0, 1)])

    def test_one_clip_can_use_different_scales_in_different_scenes(self):
        track = self.song.add_track(Track())
        major = self.song.add_scene(Scene(scale=C_MAJOR))
        minor = self.song.add_scene(Scene(scale=A_MINOR))
        clip = Clip(notes=[Degree(1, QUARTER)])
        self.song.set_clip(major, track, clip)
        self.song.set_clip(minor, track, clip)
        slots = self.live_set().find('Tracks/MidiTrack/DeviceChain/MainSequencer/ClipSlotList')
        played = [
            self.clip_notes(slot.find('ClipSlot/Value/MidiClip'))[0][0] for slot in slots
        ]
        self.assertEqual(played, [48, 45])

    def test_invalid_clips_write_nothing(self):
        track = self.song.add_track(Track())
        scene = self.song.add_scene(Scene())
        self.song.set_clip(scene, track, Clip(notes=[Degree(1, QUARTER)]))
        with self.assertRaises(ValueError):
            self.render()
        self.assertEqual(os.listdir(self.directory), [])


class TestTemplates(ProjectTestCase):

    def write_template(self, change):
        root = template_root()
        change(root)
        path = os.path.join(os.path.dirname(self.directory), 'other.als')
        data = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root)
        with open(path, 'wb') as file:
            file.write(gzip.compress(data))
        return path

    def setUp(self):
        super().setUp()
        self.song.add_track(Track())
        self.song.add_scene(Scene())

    def test_rejects_a_template_from_another_version(self):
        template = self.write_template(lambda root: root.set('MinorVersion', '11.0_11300'))
        with self.assertRaises(ValueError):
            self.render(template=template)

    def test_rejects_a_template_without_a_midi_track(self):
        def remove_midi_tracks(root):
            tracks = root.find('LiveSet/Tracks')
            for track in tracks.findall('MidiTrack'):
                tracks.remove(track)
        with self.assertRaises(ValueError):
            self.render(template=self.write_template(remove_midi_tracks))

    def test_missing_template_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.render(template=os.path.join(self.directory, 'missing.als'))


class TestFields(unittest.TestCase):

    def test_keeps_its_values(self):
        song = Song()
        project = AbletonProject('output', song, template='other.als')
        self.assertEqual(project.directory, 'output')
        self.assertIs(project.song, song)
        self.assertEqual(project.template, 'other.als')

    def test_template_defaults_to_the_one_installed_with_the_code(self):
        self.assertEqual(AbletonProject('output', Song()).template, DEFAULT_TEMPLATE)
        self.assertIsInstance(DEFAULT_TEMPLATE, Path)

    def test_rejects_invalid_values(self):
        for directory in ['', None, 1]:
            with self.subTest(directory=directory):
                with self.assertRaises(ValueError):
                    AbletonProject(directory, Song())
        for song in [None, 'song', Track()]:
            with self.subTest(song=song):
                with self.assertRaises(ValueError):
                    AbletonProject('output', song)
        for template in ['', None, 1]:
            with self.subTest(template=template):
                with self.assertRaises(ValueError):
                    AbletonProject('output', Song(), template=template)

    def test_fields_can_be_edited_and_are_validated(self):
        project = AbletonProject('output', Song())
        project.directory = 'elsewhere'
        self.assertEqual(project.directory, 'elsewhere')
        with self.assertRaises(ValueError):
            project.directory = None
        self.assertEqual(project.directory, 'elsewhere')

    def test_creating_it_does_not_create_the_directory(self):
        with tempfile.TemporaryDirectory() as parent:
            directory = os.path.join(parent, 'output')
            AbletonProject(directory, Song())
            self.assertFalse(os.path.exists(directory))


class TestFileName(unittest.TestCase):

    def test_the_name_sets_the_file_name(self):
        with tempfile.TemporaryDirectory() as directory:
            project = AbletonProject(directory, Song(), name='tune-007')
            self.assertEqual(os.path.basename(project.path), 'tune-007.als')


if __name__ == '__main__':
    unittest.main()
