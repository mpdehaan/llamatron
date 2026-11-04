import dataclasses
import unittest

from src.song import Clip, Scene, Song, Track

INVALID_TEMPOS = [0, -1, -0.5, '120', True, float('nan'), float('inf')]


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

    def test_tracks_and_scenes_get_unique_ids_even_with_the_same_name(self):
        parts = [Track('A'), Track('A'), Scene('A'), Scene('A')]
        self.assertEqual(len({part.id for part in parts}), 4)

    def test_same_name_does_not_make_parts_equal(self):
        self.assertNotEqual(Track('A'), Track('A'))
        self.assertNotEqual(Scene('A'), Scene('A'))
        self.assertNotEqual(Clip('A'), Clip('A'))

    def test_cannot_be_changed(self):
        for part in [Track('A'), Scene('A'), Clip('A')]:
            with self.subTest(part=type(part).__name__):
                with self.assertRaises(dataclasses.FrozenInstanceError):
                    part.name = 'B'


class TestTempos(unittest.TestCase):

    def test_song_defaults_to_120(self):
        self.assertEqual(Song().tempo, 120)

    def test_song_takes_a_tempo(self):
        self.assertEqual(Song(90).tempo, 90)
        self.assertEqual(Song(tempo=92.5).tempo, 92.5)

    def test_song_tempo_cannot_be_set_directly(self):
        with self.assertRaises(AttributeError):
            Song().tempo = -1

    def test_scene_and_clip_have_no_override_by_default(self):
        self.assertIsNone(Scene('Verse').tempo)
        self.assertIsNone(Clip('Riff').tempo)

    def test_scene_and_clip_can_override_the_tempo(self):
        self.assertEqual(Scene('Verse', tempo=90).tempo, 90)
        self.assertEqual(Clip('Riff', tempo=140).tempo, 140)

    def test_rejects_invalid_tempos(self):
        for tempo in INVALID_TEMPOS:
            with self.subTest(tempo=tempo):
                with self.assertRaises(ValueError):
                    Song(tempo)
                with self.assertRaises(ValueError):
                    Scene(tempo=tempo)
                with self.assertRaises(ValueError):
                    Clip(tempo=tempo)

    def test_song_rejects_none_as_a_tempo(self):
        with self.assertRaises(ValueError):
            Song(None)


class TestTempoAt(unittest.TestCase):

    def setUp(self):
        self.song = Song(120)
        self.track = self.song.add_track(Track())

    def test_uses_the_song_tempo_when_nothing_overrides_it(self):
        scene = self.song.add_scene(Scene())
        self.assertEqual(self.song.tempo_at(scene, self.track), 120)
        self.song.set_clip(scene, self.track, Clip())
        self.assertEqual(self.song.tempo_at(scene, self.track), 120)

    def test_scene_overrides_the_song(self):
        scene = self.song.add_scene(Scene(tempo=90))
        self.assertEqual(self.song.tempo_at(scene, self.track), 90)
        self.song.set_clip(scene, self.track, Clip())
        self.assertEqual(self.song.tempo_at(scene, self.track), 90)

    def test_clip_overrides_the_song(self):
        scene = self.song.add_scene(Scene())
        self.song.set_clip(scene, self.track, Clip(tempo=140))
        self.assertEqual(self.song.tempo_at(scene, self.track), 140)

    def test_clip_overrides_the_scene(self):
        scene = self.song.add_scene(Scene(tempo=90))
        self.song.set_clip(scene, self.track, Clip(tempo=140))
        self.assertEqual(self.song.tempo_at(scene, self.track), 140)

    def test_clip_override_only_affects_its_own_cell(self):
        scene = self.song.add_scene(Scene(tempo=90))
        other_track = self.song.add_track(Track())
        self.song.set_clip(scene, self.track, Clip(tempo=140))
        self.assertEqual(self.song.tempo_at(scene, other_track), 90)


class TestTracksAndScenes(unittest.TestCase):

    def test_new_song_is_empty(self):
        song = Song()
        self.assertEqual(song.tracks, [])
        self.assertEqual(song.scenes, [])

    def test_add_returns_the_object_and_keeps_order(self):
        song = Song()
        first_track, second_track = Track('A'), Track('B')
        first_scene, second_scene = Scene('A'), Scene('B')
        self.assertIs(song.add_track(first_track), first_track)
        self.assertIs(song.add_scene(first_scene), first_scene)
        song.add_track(second_track)
        song.add_scene(second_scene)
        self.assertEqual(song.tracks, [first_track, second_track])
        self.assertEqual(song.scenes, [first_scene, second_scene])

    def test_same_names_are_allowed(self):
        song = Song()
        song.add_track(Track('Bass'))
        song.add_track(Track('Bass'))
        song.add_scene(Scene('Verse'))
        song.add_scene(Scene('Verse'))
        self.assertEqual(len(song.tracks), 2)
        self.assertEqual(len(song.scenes), 2)

    def test_rejects_adding_the_same_object_twice(self):
        song = Song()
        track = song.add_track(Track())
        scene = song.add_scene(Scene())
        with self.assertRaises(ValueError):
            song.add_track(track)
        with self.assertRaises(ValueError):
            song.add_scene(scene)

    def test_rejects_the_wrong_type(self):
        song = Song()
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
        song = Song()
        song.add_track(Track())
        song.add_scene(Scene())
        song.tracks.clear()
        song.scenes.clear()
        self.assertEqual(len(song.tracks), 1)
        self.assertEqual(len(song.scenes), 1)


class TestClipGrid(unittest.TestCase):

    def setUp(self):
        self.song = Song()
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

    def test_removing_a_clip_empties_only_that_cell(self):
        other = self.song.set_clip(self.scene, self.other_track, Clip())
        self.song.set_clip(self.scene, self.track, Clip())
        self.song.remove_clip(self.scene, self.track)
        self.assertIsNone(self.song.get_clip(self.scene, self.track))
        self.assertIs(self.song.get_clip(self.scene, self.other_track), other)

    def test_removing_the_last_clip_in_a_scene_leaves_no_entry(self):
        self.song.set_clip(self.scene, self.track, Clip())
        self.song.remove_clip(self.scene, self.track)
        self.assertEqual(self.song._clips, {})

    def test_removing_from_an_empty_cell_does_nothing(self):
        self.song.remove_clip(self.scene, self.track)
        self.assertIsNone(self.song.get_clip(self.scene, self.track))

    def test_rejects_a_clip_of_the_wrong_type(self):
        for value in ['Riff', None, Track()]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.song.set_clip(self.scene, self.track, value)

    def test_rejects_scenes_and_tracks_from_outside_the_song(self):
        outside_scene, outside_track = Scene(), Track()
        calls = [
            lambda scene, track: self.song.set_clip(scene, track, Clip()),
            self.song.get_clip,
            self.song.remove_clip,
            self.song.tempo_at,
        ]
        for call in calls:
            with self.assertRaises(ValueError):
                call(outside_scene, self.track)
            with self.assertRaises(ValueError):
                call(self.scene, outside_track)

    def test_rejects_scene_and_track_in_the_wrong_order(self):
        with self.assertRaises(ValueError):
            self.song.get_clip(self.track, self.scene)

    def test_songs_do_not_share_clips(self):
        other_song = Song()
        other_song.add_track(self.track)
        other_song.add_scene(self.scene)
        self.song.set_clip(self.scene, self.track, Clip())
        self.assertIsNone(other_song.get_clip(self.scene, self.track))


if __name__ == '__main__':
    unittest.main()
