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

import contextlib
import io
import os
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

import mido

from llamatron.chord import Chord, ChordType
from llamatron.note import Note, Rest
from llamatron.renderers.clip_tree import TICKS_PER_BEAT, VELOCITY, ClipTree
from llamatron.song import Clip, Scene, ClipGrid, Track

C4 = Note('C', 4, 0.25)
D4 = Note('D', 4, 0.25)
E4 = Note('E', 4, 0.25)
G4 = Note('G', 4, 0.25)


def render(renderer):
    """Render and return what was printed."""
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        renderer.render()
    return output.getvalue()


def events(path):
    """Return a MIDI file's notes and end as (type, note, tick), with ticks from the start."""
    result = []
    tick = 0
    for message in mido.MidiFile(path).tracks[0]:
        tick += message.time
        if message.type in ('note_on', 'note_off'):
            result.append((message.type, message.note, tick))
        elif message.type == 'end_of_track':
            result.append(('end', None, tick))
    return result


def on(note, beat):
    return ('note_on', note, round(beat * TICKS_PER_BEAT))


def off(note, beat):
    return ('note_off', note, round(beat * TICKS_PER_BEAT))


def end(beat):
    return ('end', None, round(beat * TICKS_PER_BEAT))


class TestClipTreeFields(unittest.TestCase):

    def test_keeps_directory_and_song(self):
        song = ClipGrid()
        renderer = ClipTree('output', song)
        self.assertEqual(renderer.directory, 'output')
        self.assertIs(renderer.song, song)

    def test_directory_can_be_a_path(self):
        self.assertEqual(ClipTree(Path('output'), ClipGrid()).directory, Path('output'))

    def test_rejects_invalid_directories(self):
        for directory in ['', None, 1, ClipGrid()]:
            with self.subTest(directory=directory):
                with self.assertRaises(ValueError):
                    ClipTree(directory, ClipGrid())

    def test_rejects_invalid_songs(self):
        for song in [None, 'song', Track()]:
            with self.subTest(song=song):
                with self.assertRaises(ValueError):
                    ClipTree('output', song)

    def test_fields_can_be_edited(self):
        renderer = ClipTree('output', ClipGrid())
        other_song = ClipGrid()
        renderer.directory = 'elsewhere'
        renderer.song = other_song
        self.assertEqual(renderer.directory, 'elsewhere')
        self.assertIs(renderer.song, other_song)

    def test_edited_fields_are_validated(self):
        song = ClipGrid()
        renderer = ClipTree('output', song)
        with self.assertRaises(ValueError):
            renderer.directory = None
        with self.assertRaises(ValueError):
            renderer.song = None
        self.assertEqual(renderer.directory, 'output')
        self.assertIs(renderer.song, song)

    def test_creating_a_renderer_does_not_create_the_directory(self):
        with tempfile.TemporaryDirectory() as parent:
            directory = os.path.join(parent, 'output')
            ClipTree(directory, ClipGrid())
            self.assertFalse(os.path.exists(directory))


class RenderTestCase(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = temporary.name
        self.song = ClipGrid()
        self.renderer = ClipTree(self.directory, self.song)

    def path(self, filename):
        return os.path.join(self.directory, filename)

    def files(self):
        return sorted(os.listdir(self.directory))


class TestFileNames(RenderTestCase):

    def test_one_file_per_filled_slot_named_scene_then_track(self):
        tracks = [self.song.add_track(Track()) for _ in range(3)]
        scenes = [self.song.add_scene(Scene()) for _ in range(2)]
        self.song.set_clip(scenes[0], tracks[0], Clip())
        self.song.set_clip(scenes[0], tracks[2], Clip())
        self.song.set_clip(scenes[1], tracks[1], Clip())
        render(self.renderer)
        self.assertEqual(self.files(), ['001-001.mid', '001-003.mid', '002-002.mid'])

    def render_clip_named(self, name):
        track = self.song.add_track(Track())
        scene = self.song.add_scene(Scene())
        self.song.set_clip(scene, track, Clip(name))
        render(self.renderer)
        return self.files()

    def test_name_ends_with_the_clip_name(self):
        self.assertEqual(self.render_clip_named('Riff'), ['001-001-Riff.mid'])

    def test_spaces_in_the_clip_name_become_underscores(self):
        self.assertEqual(
            self.render_clip_named('Big  Bass Line'),
            ['001-001-Big__Bass_Line.mid'],
        )

    def test_ids_are_zero_padded_to_three_digits(self):
        tracks = [self.song.add_track(Track()) for _ in range(12)]
        scenes = [self.song.add_scene(Scene()) for _ in range(3)]
        self.song.set_clip(scenes[2], tracks[11], Clip())
        render(self.renderer)
        self.assertEqual(self.files(), ['003-012.mid'])

    def test_ids_past_three_digits_still_work(self):
        track = self.song.add_track(Track())
        for _ in range(1000):
            scene = self.song.add_scene(Scene())
        self.song.set_clip(scene, track, Clip())
        render(self.renderer)
        self.assertEqual(self.files(), ['1000-001.mid'])
        self.song.set_clip(self.song.add_scene(Scene()), track, Clip())
        os.remove(self.path('1000-001.mid'))
        render(self.renderer)
        self.assertIn('1001-001.mid', self.files())

    def test_clip_without_a_name_has_no_last_part(self):
        self.assertEqual(self.render_clip_named(None), ['001-001.mid'])

    def test_clip_with_an_empty_name_has_no_last_part(self):
        self.assertEqual(self.render_clip_named(''), ['001-001.mid'])

    def test_slashes_in_the_clip_name_cannot_leave_the_directory(self):
        self.assertEqual(
            self.render_clip_named('../up/and\\out'),
            ['001-001-.._up_and_out.mid'],
        )

    def test_clips_with_the_same_name_get_different_files(self):
        tracks = [self.song.add_track(Track()) for _ in range(2)]
        scene = self.song.add_scene(Scene())
        for track in tracks:
            self.song.set_clip(scene, track, Clip('Riff'))
        render(self.renderer)
        self.assertEqual(self.files(), ['001-001-Riff.mid', '001-002-Riff.mid'])

    def test_track_and_scene_names_are_not_used(self):
        track = self.song.add_track(Track('Bass/Lead'))
        scene = self.song.add_scene(Scene('Verse: 1'))
        self.song.set_clip(scene, track, Clip('Riff'))
        render(self.renderer)
        self.assertEqual(self.files(), ['001-001-Riff.mid'])

    def test_empty_song_writes_nothing(self):
        self.song.add_track(Track())
        self.song.add_scene(Scene())
        render(self.renderer)
        self.assertEqual(self.files(), [])

    def test_creates_a_missing_directory(self):
        nested = self.path(os.path.join('a', 'b'))
        track = self.song.add_track(Track())
        scene = self.song.add_scene(Scene())
        self.song.set_clip(scene, track, Clip())
        render(ClipTree(nested, self.song))
        self.assertEqual(os.listdir(nested), ['001-001.mid'])

    def test_accepts_a_path_object(self):
        track = self.song.add_track(Track())
        scene = self.song.add_scene(Scene())
        self.song.set_clip(scene, track, Clip())
        render(ClipTree(Path(self.directory), self.song))
        self.assertEqual(self.files(), ['001-001.mid'])


class TestFileContents(RenderTestCase):

    def setUp(self):
        super().setUp()
        self.track = self.song.add_track(Track())
        self.scene = self.song.add_scene(Scene())

    def render_clip(self, clip):
        self.song.set_clip(self.scene, self.track, clip)
        render(self.renderer)
        return self.path('001-001.mid')

    def tempo(self, path):
        return next(m.tempo for m in mido.MidiFile(path).tracks[0] if m.type == 'set_tempo')

    def test_notes_play_one_after_another(self):
        path = self.render_clip(Clip(notes=[C4, D4]))
        self.assertEqual(events(path), [
            on(48, 0), off(48, 1), on(50, 1), off(50, 2), end(2),
        ])

    def test_chord_notes_start_and_stop_together(self):
        path = self.render_clip(Clip(notes=[Chord([C4, E4, G4])]))
        self.assertEqual(events(path), [
            on(48, 0), on(52, 0), on(55, 0),
            off(48, 1), off(52, 1), off(55, 1),
            end(1),
        ])

    def test_positions_can_mix_notes_and_chords(self):
        path = self.render_clip(Clip(notes=[C4, Chord([D4, G4]), E4]))
        self.assertEqual(events(path), [
            on(48, 0), off(48, 1),
            on(50, 1), on(55, 1), off(50, 2), off(55, 2),
            on(52, 2), off(52, 3),
            end(3),
        ])

    def test_chord_from_note_to_chord(self):
        path = self.render_clip(Clip(notes=[C4.to_chord(ChordType.MAJOR)]))
        self.assertEqual([e[1] for e in events(path) if e[0] == 'note_on'], [48, 52, 55])

    def test_chord_with_a_repeated_pitch_plays_it_once(self):
        path = self.render_clip(Clip(notes=[Chord([C4, Note('B#', 3, 0.25)])]))
        self.assertEqual(events(path), [on(48, 0), off(48, 1), end(1)])

    def test_notes_use_a_fixed_velocity(self):
        path = self.render_clip(Clip(notes=[C4]))
        message = next(m for m in mido.MidiFile(path).tracks[0] if m.type == 'note_on')
        self.assertEqual(message.velocity, VELOCITY)

    def test_each_note_uses_its_own_length(self):
        path = self.render_clip(Clip(notes=[Note('C', 4, 0.5), Note('D', 4, 0.125)]))
        self.assertEqual(events(path), [
            on(48, 0), off(48, 2), on(50, 2), off(50, 2.5), end(2.5),
        ])

    def test_lengths_are_fractions_of_a_whole_note(self):
        cases = [(1, 4), (0.5, 2), (0.25, 1), (0.125, 0.5), (2, 8)]
        for length, beats in cases:
            with self.subTest(length=length):
                directory = self.path(str(length))
                self.song.set_clip(self.scene, self.track, Clip(notes=[Note('C', 4, length)]))
                render(ClipTree(directory, self.song))
                self.assertEqual(
                    events(os.path.join(directory, '001-001.mid')),
                    [on(48, 0), off(48, beats), end(beats)],
                )

    def test_length_can_be_a_triplet_fraction(self):
        triplet = Fraction(1, 12)
        notes = [Note('C', 4, triplet), Note('D', 4, triplet), Note('E', 4, triplet)]
        self.assertEqual(events(self.render_clip(Clip(notes=notes))), [
            ('note_on', 48, 0), ('note_off', 48, 160),
            ('note_on', 50, 160), ('note_off', 50, 320),
            ('note_on', 52, 320), ('note_off', 52, 480),
            ('end', None, 480),
        ])

    def test_rest_adds_silence_between_notes(self):
        path = self.render_clip(Clip(notes=[C4, Rest(0.5), D4]))
        self.assertEqual(events(path), [
            on(48, 0), off(48, 1), on(50, 3), off(50, 4), end(4),
        ])

    def test_rest_can_start_a_clip(self):
        path = self.render_clip(Clip(notes=[Rest(0.25), C4]))
        self.assertEqual(events(path), [on(48, 1), off(48, 2), end(2)])

    def test_rest_can_end_a_clip(self):
        path = self.render_clip(Clip(notes=[C4, Rest(0.25)]))
        self.assertEqual(events(path), [on(48, 0), off(48, 1), end(2)])

    def test_clip_of_only_rests_is_silent(self):
        self.assertEqual(events(self.render_clip(Clip(notes=[Rest(1)]))), [end(4)])

    def test_same_pitch_can_repeat(self):
        path = self.render_clip(Clip(notes=[C4, C4]))
        self.assertEqual(events(path), [
            on(48, 0), off(48, 1), on(48, 1), off(48, 2), end(2),
        ])

    def test_chord_notes_can_have_different_lengths(self):
        chord = Chord([Note('C', 4, 0.5), Note('G', 4, 0.25)])
        path = self.render_clip(Clip(notes=[chord, D4]))
        self.assertEqual(events(path), [
            on(48, 0), on(55, 0), off(55, 1), off(48, 2),
            on(50, 2), off(50, 3),
            end(3),
        ])

    def test_chord_with_a_repeated_pitch_uses_the_longest_length(self):
        chord = Chord([Note('C', 4, 0.25), Note('B#', 3, 0.5)])
        path = self.render_clip(Clip(notes=[chord]))
        self.assertEqual(events(path), [on(48, 0), off(48, 2), end(2)])

    def test_longer_length_adds_silence(self):
        path = self.render_clip(Clip(notes=[C4], length=1))
        self.assertEqual(events(path), [on(48, 0), off(48, 1), end(4)])

    def test_shorter_length_cuts_off_notes(self):
        path = self.render_clip(Clip(notes=[C4, D4, E4], length=0.375))
        self.assertEqual(events(path), [
            on(48, 0), off(48, 1), on(50, 1), off(50, 1.5), end(1.5),
        ])

    def test_length_at_a_position_boundary_drops_later_notes(self):
        path = self.render_clip(Clip(notes=[C4, D4], length=0.25))
        self.assertEqual(events(path), [on(48, 0), off(48, 1), end(1)])

    def test_clip_without_notes_is_empty(self):
        self.assertEqual(events(self.render_clip(Clip())), [end(0)])

    def test_clip_without_notes_can_still_have_a_length(self):
        self.assertEqual(events(self.render_clip(Clip(length=1))), [end(4)])

    def test_uses_the_song_tempo_by_default(self):
        self.assertEqual(self.tempo(self.render_clip(Clip())), mido.bpm2tempo(120))

    def test_uses_the_scene_tempo_over_the_song(self):
        self.scene.tempo = 90
        self.assertEqual(self.tempo(self.render_clip(Clip())), mido.bpm2tempo(90))

    def test_minimum_tempo_can_be_written(self):
        self.song.tempo = 10
        self.assertEqual(self.tempo(self.render_clip(Clip())), mido.bpm2tempo(10))

    def track_name(self, filename):
        messages = mido.MidiFile(self.path(filename)).tracks[0]
        names = [message.name for message in messages if message.type == 'track_name']
        self.assertEqual(len(names), 1)
        return names[0]

    def test_track_name_is_the_file_name_without_the_extension(self):
        self.render_clip(Clip('My Riff', notes=[C4]))
        self.assertEqual(self.track_name('001-001-My_Riff.mid'), '001-001-My_Riff')

    def test_clip_without_a_name_uses_the_scene_and_track(self):
        self.render_clip(Clip(notes=[C4]))
        self.assertEqual(self.track_name('001-001.mid'), '001-001')

    def test_track_name_with_other_characters_can_still_be_saved(self):
        self.song.set_clip(self.scene, self.track, Clip('Caf\u00e9 \u6771', notes=[C4]))
        render(self.renderer)
        self.assertEqual(self.files(), ['001-001-Caf\u00e9_\u6771.mid'])
        self.assertEqual(self.track_name('001-001-Caf\u00e9_\u6771.mid'), '001-001-Caf\u00e9_?')

    def test_file_has_the_expected_resolution_and_format(self):
        midi_file = mido.MidiFile(self.render_clip(Clip()))
        self.assertEqual(midi_file.ticks_per_beat, TICKS_PER_BEAT)
        self.assertEqual(midi_file.type, 0)
        self.assertEqual(len(midi_file.tracks), 1)

    def test_invalid_item_added_to_a_list_writes_nothing(self):
        other_track = self.song.add_track(Track())
        self.song.set_clip(self.scene, other_track, Clip(notes=[C4]))
        clip = self.song.set_clip(self.scene, self.track, Clip())
        clip.notes.append('C4')
        with self.assertRaises(ValueError):
            self.renderer.render()
        self.assertEqual(self.files(), [])


class TestExistingNamedFiles(RenderTestCase):

    def test_matching_named_file_stops_with_a_warning(self):
        track = self.song.add_track(Track())
        scene = self.song.add_scene(Scene())
        self.song.set_clip(scene, track, Clip('My Riff', notes=[C4]))
        with open(self.path('001-001-My_Riff.mid'), 'wb') as file:
            file.write(b'keep me')
        output = render(self.renderer)
        self.assertIn('warning: stopping', output)
        with open(self.path('001-001-My_Riff.mid'), 'rb') as file:
            self.assertEqual(file.read(), b'keep me')


class TestExistingFiles(RenderTestCase):

    def setUp(self):
        super().setUp()
        self.track = self.song.add_track(Track())
        self.scene = self.song.add_scene(Scene())
        self.song.set_clip(self.scene, self.track, Clip(notes=[C4]))

    def write(self, filename, content=b'keep me'):
        with open(self.path(filename), 'wb') as file:
            file.write(content)

    def read(self, filename):
        with open(self.path(filename), 'rb') as file:
            return file.read()

    def test_no_warning_for_an_empty_directory(self):
        self.assertEqual(render(self.renderer), '')

    def test_unrelated_files_are_kept_and_warned_about(self):
        self.write('notes.txt')
        output = render(self.renderer)
        self.assertEqual(self.read('notes.txt'), b'keep me')
        self.assertIn('warning', output)
        self.assertIn('notes.txt', output)
        self.assertEqual(self.files(), ['001-001.mid', 'notes.txt'])

    def test_stale_files_from_removed_clips_are_kept_and_warned_about(self):
        self.write('006-006.mid')
        output = render(self.renderer)
        self.assertEqual(self.read('006-006.mid'), b'keep me')
        self.assertIn('006-006.mid', output)
        self.assertEqual(self.files(), ['001-001.mid', '006-006.mid'])

    def test_matching_file_stops_with_a_warning_and_is_kept(self):
        self.write('001-001.mid')
        output = render(self.renderer)
        self.assertEqual(self.read('001-001.mid'), b'keep me')
        self.assertIn('warning: stopping', output)
        self.assertIn('001-001.mid', output)

    def test_matching_file_stops_every_other_file_from_being_written(self):
        other_track = self.song.add_track(Track())
        self.song.set_clip(self.scene, other_track, Clip(notes=[C4]))
        self.write('001-002.mid')
        render(self.renderer)
        self.assertEqual(self.files(), ['001-002.mid'])

    def test_warning_lists_every_matching_file(self):
        other_track = self.song.add_track(Track())
        self.song.set_clip(self.scene, other_track, Clip(notes=[C4]))
        self.write('001-001.mid')
        self.write('001-002.mid')
        output = render(self.renderer)
        self.assertIn('001-001.mid, 001-002.mid', output)

    def test_rendering_twice_stops_and_keeps_the_first_files(self):
        render(self.renderer)
        first = self.read('001-001.mid')
        self.song.get_clip(self.scene, self.track).length = 8
        output = render(self.renderer)
        self.assertEqual(self.read('001-001.mid'), first)
        self.assertIn('warning: stopping', output)


if __name__ == '__main__':
    unittest.main()
