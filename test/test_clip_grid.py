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

import unittest
from fractions import Fraction

from llamatron.chord import Chord, ChordType
from llamatron.note import Note, Rest
from llamatron.scale import Scale, ScaleType
from llamatron.clip_grid import Clip, Scene, ClipGrid, Track

C_MAJOR = Scale(Note('C', 0, 0.25), ScaleType.MAJOR)
A_MINOR = Scale(Note('A', 0, 0.25), ScaleType.MINOR)
D_DORIAN = Scale(Note('D', 0, 0.25), ScaleType.DORIAN)

INVALID_TEMPOS = [0, -1, -0.5, 1, 9, 9.99, '120', True, float('nan'), float('inf')]


class TestTrackMute(unittest.TestCase):

    def test_tracks_are_not_muted_unless_asked(self):
        self.assertFalse(Track().mute)
        self.assertTrue(Track('Input', mute=True).mute)

    def test_mute_must_be_true_or_false(self):
        with self.assertRaises(ValueError):
            Track(mute=1)


class TestNamedParts(unittest.TestCase):

    def test_names_are_optional(self):
        self.assertIsNone(Track().name)
        self.assertIsNone(Scene().name)
        self.assertIsNone(Clip().name)

    def test_keep_their_names(self):
        self.assertEqual(Track('Bass').name, 'Bass')
        self.assertEqual(Scene('Verse').name, 'Verse')
        self.assertEqual(Clip('Riff').name, 'Riff')

    def test_reject_invalid_names(self):
        for part in [Track, Scene, Clip]:
            with self.subTest(part=part.__name__):
                with self.assertRaises(ValueError):
                    part(120)

    def test_clips_get_a_unique_id_when_created(self):
        self.assertNotEqual(Clip('A').id, Clip('A').id)

    def test_tracks_and_scenes_have_no_id_until_added(self):
        self.assertIsNone(Track().id)
        self.assertIsNone(Scene().id)

    def test_track_and_scene_ids_start_at_0_and_count_up_separately(self):
        song = ClipGrid()
        tracks = [song.add_track(Track('Same')) for _ in range(3)]
        scenes = [song.add_scene(Scene('Same')) for _ in range(2)]
        self.assertEqual([track.id for track in tracks], [0, 1, 2])
        self.assertEqual([scene.id for scene in scenes], [0, 1])

    def test_ids_follow_the_order_added_not_created(self):
        song = ClipGrid()
        first_created, second_created = Track(), Track()
        song.add_track(second_created)
        song.add_track(first_created)
        self.assertEqual(second_created.id, 0)
        self.assertEqual(first_created.id, 1)

    def test_each_song_counts_its_own_ids_from_0(self):
        for _ in range(2):
            song = ClipGrid()
            self.assertEqual(song.add_track(Track()).id, 0)
            self.assertEqual(song.add_scene(Scene()).id, 0)

    def test_same_name_does_not_make_parts_equal(self):
        self.assertNotEqual(Track('A'), Track('A'))
        self.assertNotEqual(Scene('A'), Scene('A'))
        self.assertNotEqual(Clip('A'), Clip('A'))

    def test_names_can_be_edited(self):
        for part in [Track('A'), Scene('A'), Clip('A')]:
            with self.subTest(part=type(part).__name__):
                part.name = 'B'
                self.assertEqual(part.name, 'B')
                part.name = None
                self.assertIsNone(part.name)

    def test_edited_names_are_validated(self):
        for part in [Track('A'), Scene('A'), Clip('A')]:
            with self.subTest(part=type(part).__name__):
                with self.assertRaises(ValueError):
                    part.name = 120
                self.assertEqual(part.name, 'A')

    def test_ids_cannot_be_edited(self):
        song = ClipGrid()
        for part in [song.add_track(Track()), song.add_scene(Scene()), Track(), Scene(), Clip()]:
            with self.subTest(part=part):
                original = part.id
                with self.assertRaises(AttributeError):
                    part.id = 1
                self.assertEqual(part.id, original)

    def test_editing_other_fields_does_not_change_the_id(self):
        for part in [Track('A'), Scene('A'), Clip('A')]:
            with self.subTest(part=type(part).__name__):
                original = part.id
                part.name = 'B'
                self.assertEqual(part.id, original)




class TestClipLength(unittest.TestCase):

    def test_has_no_fixed_length_by_default(self):
        self.assertIsNone(Clip().length)

    def test_fixed_length_can_be_cleared(self):
        clip = Clip(length=4)
        clip.length = None
        self.assertIsNone(clip.length)

    def test_takes_a_length(self):
        for length in [1, 16, 2.5, Fraction(1, 3)]:
            with self.subTest(length=length):
                self.assertEqual(Clip(length=length).length, length)

    def test_rejects_invalid_lengths(self):
        for length in [0, -1, -0.5, Fraction(-1, 3), '4', True, float('nan'), float('inf')]:
            with self.subTest(length=length):
                with self.assertRaises(ValueError):
                    Clip(length=length)

    def test_can_be_edited_and_is_validated(self):
        clip = Clip()
        clip.length = 8
        self.assertEqual(clip.length, 8)
        with self.assertRaises(ValueError):
            clip.length = 0
        self.assertEqual(clip.length, 8)


class TestClipNotes(unittest.TestCase):

    def test_has_no_notes_by_default(self):
        self.assertEqual(Clip().notes, [])

    def test_clips_do_not_share_a_default_list(self):
        Clip().notes.append(Note('C', 4, 0.25))
        self.assertEqual(Clip().notes, [])

    def test_positions_can_be_notes_or_chords(self):
        chord = Note('C', 4, 0.25).to_chord(ChordType.MAJOR)
        self.assertEqual(Clip(notes=[Note('C', 4, 0.25), chord]).notes, [Note('C', 4, 0.25), chord])

    def test_positions_can_be_rests(self):
        notes = [Note('C', 4, 0.25), Rest(0.25)]
        self.assertEqual(Clip(notes=notes).notes, notes)

    def test_takes_a_tuple_and_stores_a_list(self):
        self.assertEqual(Clip(notes=(Note('C', 4, 0.25),)).notes, [Note('C', 4, 0.25)])

    def test_clips_built_from_one_list_do_not_share_it(self):
        notes = [Note('C', 4, 0.25)]
        first, second = Clip(notes=notes), Clip(notes=notes)
        first.notes.append(Note('D', 4, 0.25))
        notes.append(Note('E', 4, 0.25))
        self.assertEqual(second.notes, [Note('C', 4, 0.25)])

    def test_rejects_invalid_notes(self):
        for notes in ['C4', Note('C', 4, 0.25), Chord([Note('C', 4, 0.25)]), ['H4'], [Note('C', 4, 0.25), 1.5], [None]]:
            with self.subTest(notes=notes):
                with self.assertRaises(ValueError):
                    Clip(notes=notes)

    def test_can_be_edited_and_is_validated(self):
        clip = Clip()
        clip.notes = [Note('C', 4, 0.25)]
        self.assertEqual(clip.notes, [Note('C', 4, 0.25)])
        with self.assertRaises(ValueError):
            clip.notes = ['H4']
        self.assertEqual(clip.notes, [Note('C', 4, 0.25)])



class TestTempos(unittest.TestCase):

    def test_song_defaults_to_120(self):
        self.assertEqual(ClipGrid().tempo, 120)

    def test_song_takes_a_tempo(self):
        self.assertEqual(ClipGrid(90).tempo, 90)
        self.assertEqual(ClipGrid(tempo=92.5).tempo, 92.5)

    def test_tempos_can_be_edited(self):
        for part in [ClipGrid(), Scene()]:
            with self.subTest(part=type(part).__name__):
                part.tempo = 77
                self.assertEqual(part.tempo, 77)

    def test_edited_tempos_are_validated(self):
        for part in [ClipGrid(100), Scene(tempo=100)]:
            for tempo in INVALID_TEMPOS:
                with self.subTest(part=type(part).__name__, tempo=tempo):
                    with self.assertRaises(ValueError):
                        part.tempo = tempo
                    self.assertEqual(part.tempo, 100)

    def test_scene_override_can_be_cleared(self):
        scene = Scene(tempo=100)
        scene.tempo = None
        self.assertIsNone(scene.tempo)

    def test_song_tempo_cannot_be_cleared(self):
        song = ClipGrid(100)
        with self.assertRaises(ValueError):
            song.tempo = None
        self.assertEqual(song.tempo, 100)

    def test_scene_has_no_override_by_default(self):
        self.assertIsNone(Scene('Verse').tempo)

    def test_scene_can_override_the_tempo(self):
        self.assertEqual(Scene('Verse', tempo=90).tempo, 90)

    def test_clips_have_no_tempo(self):
        self.assertFalse(hasattr(Clip(), 'tempo'))
        with self.assertRaises(TypeError):
            Clip(tempo=140)

    def test_rejects_invalid_tempos(self):
        for tempo in INVALID_TEMPOS:
            with self.subTest(tempo=tempo):
                with self.assertRaises(ValueError):
                    ClipGrid(tempo)
                with self.assertRaises(ValueError):
                    Scene(tempo=tempo)

    def test_song_rejects_none_as_a_tempo(self):
        with self.assertRaises(ValueError):
            ClipGrid(None)


class TestTempoAt(unittest.TestCase):

    def setUp(self):
        self.song = ClipGrid(120)

    def test_uses_the_song_tempo_when_the_scene_has_none(self):
        scene = self.song.add_scene(Scene())
        self.assertEqual(self.song.tempo_at(scene), 120)

    def test_scene_overrides_the_song(self):
        scene = self.song.add_scene(Scene(tempo=90))
        self.assertEqual(self.song.tempo_at(scene), 90)

    def test_scene_override_only_affects_that_scene(self):
        self.song.add_scene(Scene(tempo=90))
        other_scene = self.song.add_scene(Scene())
        self.assertEqual(self.song.tempo_at(other_scene), 120)

    def test_follows_edits(self):
        scene = self.song.add_scene(Scene())
        self.song.tempo = 100
        self.assertEqual(self.song.tempo_at(scene), 100)
        scene.tempo = 90
        self.assertEqual(self.song.tempo_at(scene), 90)
        scene.tempo = None
        self.assertEqual(self.song.tempo_at(scene), 100)

    def test_rejects_scenes_from_outside_the_song(self):
        for scene in [Scene(), None, 'Verse']:
            with self.subTest(scene=scene):
                with self.assertRaises(ValueError):
                    self.song.tempo_at(scene)


class TestScales(unittest.TestCase):

    def test_no_scale_by_default(self):
        self.assertIsNone(ClipGrid().scale)
        self.assertIsNone(Scene().scale)
        self.assertIsNone(Clip().scale)

    def test_take_a_scale(self):
        self.assertIs(ClipGrid(scale=C_MAJOR).scale, C_MAJOR)
        self.assertIs(Scene(scale=C_MAJOR).scale, C_MAJOR)
        self.assertIs(Clip(scale=C_MAJOR).scale, C_MAJOR)

    def test_scales_can_be_edited_and_cleared(self):
        for part in [ClipGrid(), Scene(), Clip()]:
            with self.subTest(part=type(part).__name__):
                part.scale = C_MAJOR
                self.assertIs(part.scale, C_MAJOR)
                part.scale = None
                self.assertIsNone(part.scale)

    def test_rejects_invalid_scales(self):
        for scale in ['C major', ScaleType.MAJOR, Note('C', 4, 0.25), 1]:
            for make in [ClipGrid, Scene, Clip]:
                with self.subTest(part=make.__name__, scale=scale):
                    with self.assertRaises(ValueError):
                        make(scale=scale)
                    part = make(scale=C_MAJOR)
                    with self.assertRaises(ValueError):
                        part.scale = scale
                    self.assertIs(part.scale, C_MAJOR)


class TestScaleAt(unittest.TestCase):

    def setUp(self):
        self.song = ClipGrid(scale=C_MAJOR)
        self.track = self.song.add_track(Track())

    def test_none_when_nothing_has_a_scale(self):
        song = ClipGrid()
        track = song.add_track(Track())
        scene = song.add_scene(Scene())
        self.assertIsNone(song.scale_at(scene, track))
        song.set_clip(scene, track, Clip())
        self.assertIsNone(song.scale_at(scene, track))

    def test_uses_the_song_scale_when_nothing_overrides_it(self):
        scene = self.song.add_scene(Scene())
        self.assertIs(self.song.scale_at(scene, self.track), C_MAJOR)
        self.song.set_clip(scene, self.track, Clip())
        self.assertIs(self.song.scale_at(scene, self.track), C_MAJOR)

    def test_scene_overrides_the_song(self):
        scene = self.song.add_scene(Scene(scale=A_MINOR))
        self.assertIs(self.song.scale_at(scene, self.track), A_MINOR)
        self.song.set_clip(scene, self.track, Clip())
        self.assertIs(self.song.scale_at(scene, self.track), A_MINOR)

    def test_clip_overrides_the_song(self):
        scene = self.song.add_scene(Scene())
        self.song.set_clip(scene, self.track, Clip(scale=D_DORIAN))
        self.assertIs(self.song.scale_at(scene, self.track), D_DORIAN)

    def test_clip_overrides_the_scene(self):
        scene = self.song.add_scene(Scene(scale=A_MINOR))
        self.song.set_clip(scene, self.track, Clip(scale=D_DORIAN))
        self.assertIs(self.song.scale_at(scene, self.track), D_DORIAN)

    def test_clip_override_only_affects_its_own_cell(self):
        scene = self.song.add_scene(Scene(scale=A_MINOR))
        other_track = self.song.add_track(Track())
        self.song.set_clip(scene, self.track, Clip(scale=D_DORIAN))
        self.assertIs(self.song.scale_at(scene, other_track), A_MINOR)

    def test_scene_without_a_clip_override_does_not_affect_other_scenes(self):
        scene = self.song.add_scene(Scene(scale=A_MINOR))
        other_scene = self.song.add_scene(Scene())
        self.assertIs(self.song.scale_at(scene, self.track), A_MINOR)
        self.assertIs(self.song.scale_at(other_scene, self.track), C_MAJOR)

    def test_scale_and_tempo_overrides_are_independent(self):
        scene = self.song.add_scene(Scene(tempo=90))
        self.song.set_clip(scene, self.track, Clip(scale=D_DORIAN))
        self.assertIs(self.song.scale_at(scene, self.track), D_DORIAN)
        self.assertEqual(self.song.tempo_at(scene), 90)

    def test_follows_edits(self):
        scene = self.song.add_scene(Scene())
        clip = self.song.set_clip(scene, self.track, Clip())
        self.song.scale = A_MINOR
        self.assertIs(self.song.scale_at(scene, self.track), A_MINOR)
        scene.scale = D_DORIAN
        self.assertIs(self.song.scale_at(scene, self.track), D_DORIAN)
        clip.scale = C_MAJOR
        self.assertIs(self.song.scale_at(scene, self.track), C_MAJOR)
        clip.scale = None
        self.assertIs(self.song.scale_at(scene, self.track), D_DORIAN)

    def test_rejects_scenes_and_tracks_from_outside_the_song(self):
        scene = self.song.add_scene(Scene())
        with self.assertRaises(ValueError):
            self.song.scale_at(Scene(), self.track)
        with self.assertRaises(ValueError):
            self.song.scale_at(scene, Track())


class TestTracksAndScenes(unittest.TestCase):

    def test_new_song_is_empty(self):
        song = ClipGrid()
        self.assertEqual(song.tracks, [])
        self.assertEqual(song.scenes, [])

    def test_add_returns_the_object_and_keeps_order(self):
        song = ClipGrid()
        first_track, second_track = Track('A'), Track('B')
        first_scene, second_scene = Scene('A'), Scene('B')
        self.assertIs(song.add_track(first_track), first_track)
        self.assertIs(song.add_scene(first_scene), first_scene)
        song.add_track(second_track)
        song.add_scene(second_scene)
        self.assertEqual(song.tracks, [first_track, second_track])
        self.assertEqual(song.scenes, [first_scene, second_scene])

    def test_same_names_are_allowed(self):
        song = ClipGrid()
        song.add_track(Track('Bass'))
        song.add_track(Track('Bass'))
        song.add_scene(Scene('Verse'))
        song.add_scene(Scene('Verse'))
        self.assertEqual(len(song.tracks), 2)
        self.assertEqual(len(song.scenes), 2)

    def test_rejects_adding_the_same_object_twice(self):
        song = ClipGrid()
        track = song.add_track(Track())
        scene = song.add_scene(Scene())
        with self.assertRaises(ValueError):
            song.add_track(track)
        with self.assertRaises(ValueError):
            song.add_scene(scene)

    def test_rejects_the_wrong_type(self):
        song = ClipGrid()
        for value in ['Bass', None, Clip()]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    song.add_track(value)
                with self.assertRaises(ValueError):
                    song.add_scene(value)
        with self.assertRaises(ValueError):
            song.add_track(Scene())
        with self.assertRaises(ValueError):
            song.add_scene(Track())

    def test_changing_the_returned_lists_does_not_change_the_song(self):
        song = ClipGrid()
        song.add_track(Track())
        song.add_scene(Scene())
        song.tracks.clear()
        song.scenes.clear()
        self.assertEqual(len(song.tracks), 1)
        self.assertEqual(len(song.scenes), 1)


class TestClipGrid(unittest.TestCase):

    def test_rejects_scenes_and_tracks_from_outside_the_song(self):
        outside_scene, outside_track = Scene(), Track()
        calls = [
            lambda scene, track: self.song.set_clip(scene, track, Clip()),
            self.song.get_clip,
        ]
        for call in calls:
            with self.assertRaises(ValueError):
                call(outside_scene, self.track)
            with self.assertRaises(ValueError):
                call(self.scene, outside_track)

    def setUp(self):
        self.song = ClipGrid()
        self.track = self.song.add_track(Track('Bass'))
        self.other_track = self.song.add_track(Track('Bass'))
        self.scene = self.song.add_scene(Scene('Verse'))
        self.other_scene = self.song.add_scene(Scene('Verse'))

    def test_cells_start_empty(self):
        self.assertIsNone(self.song.get_clip(self.scene, self.track))

    def test_stores_and_returns_a_clip(self):
        clip = Clip('Riff')
        self.assertIs(self.song.set_clip(self.scene, self.track, clip), clip)
        self.assertIs(self.song.get_clip(self.scene, self.track), clip)

    def test_each_cell_is_separate_even_when_names_match(self):
        clips = {
            (self.scene, self.track): Clip('A'),
            (self.scene, self.other_track): Clip('B'),
            (self.other_scene, self.track): Clip('C'),
            (self.other_scene, self.other_track): Clip('D'),
        }
        for (scene, track), clip in clips.items():
            self.song.set_clip(scene, track, clip)
        for (scene, track), clip in clips.items():
            with self.subTest(clip=clip.name):
                self.assertIs(self.song.get_clip(scene, track), clip)

    def test_setting_a_filled_cell_replaces_the_clip(self):
        self.song.set_clip(self.scene, self.track, Clip('Old'))
        new = self.song.set_clip(self.scene, self.track, Clip('New'))
        self.assertIs(self.song.get_clip(self.scene, self.track), new)

    def test_storage_is_nested_by_scene_id_then_track_id(self):
        clip = self.song.set_clip(self.scene, self.track, Clip())
        self.assertEqual(self.song._clips, {self.scene.id: {self.track.id: clip}})

    def test_rejects_a_clip_of_the_wrong_type(self):
        for value in ['Riff', None, Track()]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.song.set_clip(self.scene, self.track, value)

    def test_rejects_scene_and_track_in_the_wrong_order(self):
        with self.assertRaises(ValueError):
            self.song.get_clip(self.track, self.scene)

    def test_renaming_does_not_affect_the_grid(self):
        clip = self.song.set_clip(self.scene, self.track, Clip())
        self.scene.name = 'Chorus'
        self.track.name = 'Lead'
        self.assertIs(self.song.get_clip(self.scene, self.track), clip)

    def test_tracks_and_scenes_can_only_join_one_song(self):
        other_song = ClipGrid()
        with self.assertRaises(ValueError):
            other_song.add_track(self.track)
        with self.assertRaises(ValueError):
            other_song.add_scene(self.scene)
        self.assertEqual(other_song.tracks, [])
        self.assertEqual(other_song.scenes, [])

    def test_songs_with_the_same_ids_do_not_share_clips(self):
        other_song = ClipGrid()
        other_track = other_song.add_track(Track())
        other_scene = other_song.add_scene(Scene())
        self.assertEqual((other_scene.id, other_track.id), (self.scene.id, self.track.id))
        self.song.set_clip(self.scene, self.track, Clip())
        self.assertIsNone(other_song.get_clip(other_scene, other_track))

    def test_rejects_a_scene_or_track_from_another_song_with_the_same_id(self):
        other_song = ClipGrid()
        other_track = other_song.add_track(Track())
        other_scene = other_song.add_scene(Scene())
        with self.assertRaises(ValueError):
            self.song.get_clip(other_scene, self.track)
        with self.assertRaises(ValueError):
            self.song.get_clip(self.scene, other_track)


if __name__ == '__main__':
    unittest.main()
