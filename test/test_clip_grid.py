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

import unittest
from fractions import Fraction

from llamatron.music.chord import Chord, ChordType
from llamatron.composition.file_format import SongSetting
from llamatron.music.note import Note, NoteName, Rest
from llamatron.music.scale import Scale, ScaleType
from llamatron.music.time_signature import TimeSignature
from llamatron.grid.clip import Clip
from llamatron.grid.clip_grid import ClipGrid
from llamatron.grid.clip_row import ClipRow
from llamatron.grid.clip_column import ClipColumn

C_MAJOR = Scale(root=Note(name='C', octave_number=0, length=0.25), typ=ScaleType.MAJOR)
A_MINOR = Scale(root=Note(name='A', octave_number=0, length=0.25), typ=ScaleType.MINOR)
D_DORIAN = Scale(root=Note(name='D', octave_number=0, length=0.25), typ=ScaleType.DORIAN)

INVALID_TEMPOS = [0, -1, -0.5, 1, 9, 9.99, '120', True, float('nan'), float('inf')]

# Names the tests give to their own things, and other values they use.
INPUT = 'Input'
BASS = 'Bass'
VERSE = 'Verse'
RIFF = 'Riff'
A = 'A'
B = 'B'
SAME = 'Same'
NAN = 'nan'
INF = 'inf'
C4 = 'C4'
H4 = 'H4'
C_MAJOR_2 = 'C major'
CHORUS = 'Chorus'
LEAD = 'Lead'
C = 'C'
D = 'D'
OLD = 'Old'
NEW = 'New'


# Time signatures the tests use, as a file writes them.
COMMON_TIME = '4/4'
WALTZ = '3/4'


class TestTrackMute(unittest.TestCase):

    def test_tracks_are_not_muted_unless_asked(self):
        self.assertFalse(ClipColumn().get_mute())
        self.assertTrue(ClipColumn(name=INPUT, mute=True).get_mute())

    def test_mute_must_be_true_or_false(self):
        with self.assertRaises(ValueError):
            ClipColumn(mute=1)


class TestNamedParts(unittest.TestCase):

    def test_names_are_optional(self):
        self.assertIsNone(ClipColumn().get_name())
        self.assertIsNone(ClipRow().get_name())
        self.assertIsNone(Clip().get_name())

    def test_keep_their_names(self):
        self.assertEqual(ClipColumn(name=BASS).get_name(), BASS)
        self.assertEqual(ClipRow(name=VERSE).get_name(), VERSE)
        self.assertEqual(Clip(name=RIFF).get_name(), RIFF)

    def test_reject_invalid_names(self):
        for part in [ClipColumn, ClipRow, Clip]:
            with self.subTest(part=part.__name__):
                with self.assertRaises(ValueError):
                    part(name=120)

    def test_clips_get_a_unique_id_when_created(self):
        self.assertNotEqual(Clip(name=A).get_id(), Clip(name=A).get_id())

    def test_tracks_and_scenes_have_no_id_until_added(self):
        self.assertIsNone(ClipColumn().get_id())
        self.assertIsNone(ClipRow().get_id())

    def test_track_and_scene_ids_start_at_0_and_count_up_separately(self):
        song = ClipGrid()
        tracks = [song.add_column(ClipColumn(name=SAME)) for _ in range(3)]
        scenes = [song.add_row(ClipRow(name=SAME)) for _ in range(2)]
        self.assertEqual([track.get_id() for track in tracks], [0, 1, 2])
        self.assertEqual([scene.get_id() for scene in scenes], [0, 1])

    def test_ids_follow_the_order_added_not_created(self):
        song = ClipGrid()
        first_created = ClipColumn()
        second_created = ClipColumn()
        song.add_column(second_created)
        song.add_column(first_created)
        self.assertEqual(second_created.get_id(), 0)
        self.assertEqual(first_created.get_id(), 1)

    def test_each_song_counts_its_own_ids_from_0(self):
        for _ in range(2):
            song = ClipGrid()
            self.assertEqual(song.add_column(ClipColumn()).get_id(), 0)
            self.assertEqual(song.add_row(ClipRow()).get_id(), 0)

    def test_same_name_does_not_make_parts_equal(self):
        self.assertNotEqual(ClipColumn(name=A), ClipColumn(name=A))
        self.assertNotEqual(ClipRow(name=A), ClipRow(name=A))
        self.assertNotEqual(Clip(name=A), Clip(name=A))

    def test_names_can_be_edited(self):
        for part in [ClipColumn(name=A), ClipRow(name=A), Clip(name=A)]:
            with self.subTest(part=type(part).__name__):
                part.set_name(B)
                self.assertEqual(part.get_name(), B)
                part.set_name(None)
                self.assertIsNone(part.get_name())

    def test_edited_names_are_validated(self):
        for part in [ClipColumn(name=A), ClipRow(name=A), Clip(name=A)]:
            with self.subTest(part=type(part).__name__):
                with self.assertRaises(ValueError):
                    part.set_name(120)
                self.assertEqual(part.get_name(), A)

    def test_ids_cannot_be_edited(self):
        song = ClipGrid()
        for part in [song.add_column(ClipColumn()), song.add_row(ClipRow()), ClipColumn(), ClipRow(), Clip()]:
            with self.subTest(part=part):
                original = part.get_id()
                with self.assertRaises(AttributeError):
                    part.id = 1
                self.assertEqual(part.get_id(), original)

    def test_editing_other_fields_does_not_change_the_id(self):
        for part in [ClipColumn(name=A), ClipRow(name=A), Clip(name=A)]:
            with self.subTest(part=type(part).__name__):
                original = part.get_id()
                part.set_name(B)
                self.assertEqual(part.get_id(), original)




class TestClipLength(unittest.TestCase):

    def test_has_no_fixed_length_by_default(self):
        self.assertIsNone(Clip().get_length())

    def test_fixed_length_can_be_cleared(self):
        clip = Clip(length=4)
        clip.set_length(None)
        self.assertIsNone(clip.get_length())

    def test_takes_a_length(self):
        for length in [1, 16, 2.5, Fraction(1, 3)]:
            with self.subTest(length=length):
                self.assertEqual(Clip(length=length).get_length(), length)

    def test_rejects_invalid_lengths(self):
        for length in [0, -1, -0.5, Fraction(-1, 3), '4', True, float(NAN), float(INF)]:
            with self.subTest(length=length):
                with self.assertRaises(ValueError):
                    Clip(length=length)

    def test_can_be_edited_and_is_validated(self):
        clip = Clip()
        clip.set_length(8)
        self.assertEqual(clip.get_length(), 8)
        with self.assertRaises(ValueError):
            clip.set_length(0)
        self.assertEqual(clip.get_length(), 8)


class TestClipNotes(unittest.TestCase):

    def test_has_no_notes_by_default(self):
        self.assertEqual(Clip().get_notes(), [])

    def test_clips_do_not_share_a_default_list(self):
        Clip().get_notes().append(Note(name=NoteName.C, octave_number=4, length=0.25))
        self.assertEqual(Clip().get_notes(), [])

    def test_positions_can_be_notes_or_chords(self):
        chord = Note(name=NoteName.C, octave_number=4, length=0.25).to_chord(ChordType.MAJOR)
        self.assertEqual(Clip(notes=[Note(name=NoteName.C, octave_number=4, length=0.25), chord]).get_notes(), [Note(name=NoteName.C, octave_number=4, length=0.25), chord])

    def test_positions_can_be_rests(self):
        notes = [Note(name=NoteName.C, octave_number=4, length=0.25), Rest(0.25)]
        self.assertEqual(Clip(notes=notes).get_notes(), notes)

    def test_takes_a_tuple_and_stores_a_list(self):
        self.assertEqual(Clip(notes=(Note(name=NoteName.C, octave_number=4, length=0.25),)).get_notes(), [Note(name=NoteName.C, octave_number=4, length=0.25)])

    def test_clips_built_from_one_list_do_not_share_it(self):
        notes = [Note(name=NoteName.C, octave_number=4, length=0.25)]
        first = Clip(notes=notes)
        second = Clip(notes=notes)
        first.get_notes().append(Note(name=NoteName.D, octave_number=4, length=0.25))
        notes.append(Note(name=NoteName.E, octave_number=4, length=0.25))
        self.assertEqual(second.get_notes(), [Note(name=NoteName.C, octave_number=4, length=0.25)])

    def test_rejects_invalid_notes(self):
        for notes in [C4, Note(name=NoteName.C, octave_number=4, length=0.25), Chord([Note(name=NoteName.C, octave_number=4, length=0.25)]), [H4], [Note(name=NoteName.C, octave_number=4, length=0.25), 1.5], [None]]:
            with self.subTest(notes=notes):
                with self.assertRaises(ValueError):
                    Clip(notes=notes)

    def test_can_be_edited_and_is_validated(self):
        clip = Clip()
        clip.set_notes([Note(name=NoteName.C, octave_number=4, length=0.25)])
        self.assertEqual(clip.get_notes(), [Note(name=NoteName.C, octave_number=4, length=0.25)])
        with self.assertRaises(ValueError):
            clip.set_notes([H4])
        self.assertEqual(clip.get_notes(), [Note(name=NoteName.C, octave_number=4, length=0.25)])



class TestTempos(unittest.TestCase):

    def test_song_defaults_to_120(self):
        self.assertEqual(ClipGrid().get_tempo(), 120)

    def test_the_grid_has_a_time_signature_and_a_clip_can_have_its_own(self):
        self.assertEqual(ClipGrid().get_time_signature(), TimeSignature.from_text(COMMON_TIME))
        grid = ClipGrid(time_signature=TimeSignature.from_text(WALTZ))
        self.assertEqual(grid.get_time_signature().to_text(), WALTZ)
        grid.set_time_signature(TimeSignature.from_text(COMMON_TIME))
        self.assertEqual(grid.get_time_signature().to_text(), COMMON_TIME)
        with self.assertRaises(ValueError):
            grid.set_time_signature(WALTZ)
        with self.assertRaises(ValueError):
            grid.set_time_signature(None)
        clip = Clip()
        self.assertIsNone(clip.get_time_signature())
        clip.set_time_signature(TimeSignature.from_text(WALTZ))
        self.assertEqual(clip.get_time_signature().to_text(), WALTZ)
        clip.set_time_signature(None)
        self.assertIsNone(clip.get_time_signature())
        with self.assertRaises(ValueError):
            Clip(time_signature=WALTZ)

    def test_song_takes_a_tempo(self):
        self.assertEqual(ClipGrid(tempo=90).get_tempo(), 90)
        self.assertEqual(ClipGrid(tempo=92.5).get_tempo(), 92.5)

    def test_tempos_can_be_edited(self):
        for part in [ClipGrid(), ClipRow()]:
            with self.subTest(part=type(part).__name__):
                part.set_tempo(77)
                self.assertEqual(part.get_tempo(), 77)

    def test_edited_tempos_are_validated(self):
        for part in [ClipGrid(tempo=100), ClipRow(tempo=100)]:
            for tempo in INVALID_TEMPOS:
                with self.subTest(part=type(part).__name__, tempo=tempo):
                    with self.assertRaises(ValueError):
                        part.set_tempo(tempo)
                    self.assertEqual(part.get_tempo(), 100)

    def test_scene_override_can_be_cleared(self):
        scene = ClipRow(tempo=100)
        scene.set_tempo(None)
        self.assertIsNone(scene.get_tempo())

    def test_song_tempo_cannot_be_cleared(self):
        song = ClipGrid(tempo=100)
        with self.assertRaises(ValueError):
            song.set_tempo(None)
        self.assertEqual(song.get_tempo(), 100)

    def test_scene_has_no_override_by_default(self):
        self.assertIsNone(ClipRow(name=VERSE).get_tempo())

    def test_scene_can_override_the_tempo(self):
        self.assertEqual(ClipRow(name=VERSE, tempo=90).get_tempo(), 90)

    def test_clips_have_no_tempo(self):
        self.assertFalse(hasattr(Clip(), SongSetting.TEMPO))
        with self.assertRaises(TypeError):
            Clip(tempo=140)

    def test_rejects_invalid_tempos(self):
        for tempo in INVALID_TEMPOS:
            with self.subTest(tempo=tempo):
                with self.assertRaises(ValueError):
                    ClipGrid(tempo=tempo)
                with self.assertRaises(ValueError):
                    ClipRow(tempo=tempo)

    def test_song_rejects_none_as_a_tempo(self):
        with self.assertRaises(ValueError):
            ClipGrid(tempo=None)


class TestTempoAt(unittest.TestCase):

    def setUp(self):
        self.song = ClipGrid(tempo=120)

    def test_uses_the_song_tempo_when_the_scene_has_none(self):
        scene = self.song.add_row(ClipRow())
        self.assertEqual(self.song.tempo_at(scene), 120)

    def test_scene_overrides_the_song(self):
        scene = self.song.add_row(ClipRow(tempo=90))
        self.assertEqual(self.song.tempo_at(scene), 90)

    def test_scene_override_only_affects_that_scene(self):
        self.song.add_row(ClipRow(tempo=90))
        other_scene = self.song.add_row(ClipRow())
        self.assertEqual(self.song.tempo_at(other_scene), 120)

    def test_follows_edits(self):
        scene = self.song.add_row(ClipRow())
        self.song.set_tempo(100)
        self.assertEqual(self.song.tempo_at(scene), 100)
        scene.set_tempo(90)
        self.assertEqual(self.song.tempo_at(scene), 90)
        scene.set_tempo(None)
        self.assertEqual(self.song.tempo_at(scene), 100)

    def test_rejects_scenes_from_outside_the_song(self):
        for scene in [ClipRow(), None, VERSE]:
            with self.subTest(scene=scene):
                with self.assertRaises(ValueError):
                    self.song.tempo_at(scene)


class TestScales(unittest.TestCase):

    def test_no_scale_by_default(self):
        self.assertIsNone(ClipGrid().get_scale())
        self.assertIsNone(ClipRow().get_scale())
        self.assertIsNone(Clip().get_scale())

    def test_take_a_scale(self):
        self.assertIs(ClipGrid(scale=C_MAJOR).get_scale(), C_MAJOR)
        self.assertIs(ClipRow(scale=C_MAJOR).get_scale(), C_MAJOR)
        self.assertIs(Clip(scale=C_MAJOR).get_scale(), C_MAJOR)

    def test_scales_can_be_edited_and_cleared(self):
        for part in [ClipGrid(), ClipRow(), Clip()]:
            with self.subTest(part=type(part).__name__):
                part.set_scale(C_MAJOR)
                self.assertIs(part.get_scale(), C_MAJOR)
                part.set_scale(None)
                self.assertIsNone(part.get_scale())

    def test_rejects_invalid_scales(self):
        for scale in [C_MAJOR_2, ScaleType.MAJOR, Note(name=NoteName.C, octave_number=4, length=0.25), 1]:
            for make in [ClipGrid, ClipRow, Clip]:
                with self.subTest(part=make.__name__, scale=scale):
                    with self.assertRaises(ValueError):
                        make(scale=scale)
                    part = make(scale=C_MAJOR)
                    with self.assertRaises(ValueError):
                        part.set_scale(scale)
                    self.assertIs(part.get_scale(), C_MAJOR)


class TestScaleAt(unittest.TestCase):

    def setUp(self):
        self.song = ClipGrid(scale=C_MAJOR)
        self.track = self.song.add_column(ClipColumn())

    def test_none_when_nothing_has_a_scale(self):
        song = ClipGrid()
        track = song.add_column(ClipColumn())
        scene = song.add_row(ClipRow())
        self.assertIsNone(song.scale_at(row=scene, column=track))
        song.set_clip(row=scene, column=track, clip=Clip())
        self.assertIsNone(song.scale_at(row=scene, column=track))

    def test_uses_the_song_scale_when_nothing_overrides_it(self):
        scene = self.song.add_row(ClipRow())
        self.assertIs(self.song.scale_at(row=scene, column=self.track), C_MAJOR)
        self.song.set_clip(row=scene, column=self.track, clip=Clip())
        self.assertIs(self.song.scale_at(row=scene, column=self.track), C_MAJOR)

    def test_scene_overrides_the_song(self):
        scene = self.song.add_row(ClipRow(scale=A_MINOR))
        self.assertIs(self.song.scale_at(row=scene, column=self.track), A_MINOR)
        self.song.set_clip(row=scene, column=self.track, clip=Clip())
        self.assertIs(self.song.scale_at(row=scene, column=self.track), A_MINOR)

    def test_clip_overrides_the_song(self):
        scene = self.song.add_row(ClipRow())
        self.song.set_clip(row=scene, column=self.track, clip=Clip(scale=D_DORIAN))
        self.assertIs(self.song.scale_at(row=scene, column=self.track), D_DORIAN)

    def test_clip_overrides_the_scene(self):
        scene = self.song.add_row(ClipRow(scale=A_MINOR))
        self.song.set_clip(row=scene, column=self.track, clip=Clip(scale=D_DORIAN))
        self.assertIs(self.song.scale_at(row=scene, column=self.track), D_DORIAN)

    def test_clip_override_only_affects_its_own_cell(self):
        scene = self.song.add_row(ClipRow(scale=A_MINOR))
        other_track = self.song.add_column(ClipColumn())
        self.song.set_clip(row=scene, column=self.track, clip=Clip(scale=D_DORIAN))
        self.assertIs(self.song.scale_at(row=scene, column=other_track), A_MINOR)

    def test_scene_without_a_clip_override_does_not_affect_other_scenes(self):
        scene = self.song.add_row(ClipRow(scale=A_MINOR))
        other_scene = self.song.add_row(ClipRow())
        self.assertIs(self.song.scale_at(row=scene, column=self.track), A_MINOR)
        self.assertIs(self.song.scale_at(row=other_scene, column=self.track), C_MAJOR)

    def test_scale_and_tempo_overrides_are_independent(self):
        scene = self.song.add_row(ClipRow(tempo=90))
        self.song.set_clip(row=scene, column=self.track, clip=Clip(scale=D_DORIAN))
        self.assertIs(self.song.scale_at(row=scene, column=self.track), D_DORIAN)
        self.assertEqual(self.song.tempo_at(scene), 90)

    def test_follows_edits(self):
        scene = self.song.add_row(ClipRow())
        clip = self.song.set_clip(row=scene, column=self.track, clip=Clip())
        self.song.set_scale(A_MINOR)
        self.assertIs(self.song.scale_at(row=scene, column=self.track), A_MINOR)
        scene.set_scale(D_DORIAN)
        self.assertIs(self.song.scale_at(row=scene, column=self.track), D_DORIAN)
        clip.set_scale(C_MAJOR)
        self.assertIs(self.song.scale_at(row=scene, column=self.track), C_MAJOR)
        clip.set_scale(None)
        self.assertIs(self.song.scale_at(row=scene, column=self.track), D_DORIAN)

    def test_rejects_scenes_and_tracks_from_outside_the_song(self):
        scene = self.song.add_row(ClipRow())
        with self.assertRaises(ValueError):
            self.song.scale_at(row=ClipRow(), column=self.track)
        with self.assertRaises(ValueError):
            self.song.scale_at(row=scene, column=ClipColumn())


class TestTracksAndScenes(unittest.TestCase):

    def test_new_song_is_empty(self):
        song = ClipGrid()
        self.assertEqual(song.get_columns(), [])
        self.assertEqual(song.get_rows(), [])

    def test_add_returns_the_object_and_keeps_order(self):
        song = ClipGrid()
        first_track = ClipColumn(name=A)
        second_track = ClipColumn(name=B)
        first_scene = ClipRow(name=A)
        second_scene = ClipRow(name=B)
        self.assertIs(song.add_column(first_track), first_track)
        self.assertIs(song.add_row(first_scene), first_scene)
        song.add_column(second_track)
        song.add_row(second_scene)
        self.assertEqual(song.get_columns(), [first_track, second_track])
        self.assertEqual(song.get_rows(), [first_scene, second_scene])

    def test_same_names_are_allowed(self):
        song = ClipGrid()
        song.add_column(ClipColumn(name=BASS))
        song.add_column(ClipColumn(name=BASS))
        song.add_row(ClipRow(name=VERSE))
        song.add_row(ClipRow(name=VERSE))
        self.assertEqual(len(song.get_columns()), 2)
        self.assertEqual(len(song.get_rows()), 2)

    def test_rejects_adding_the_same_object_twice(self):
        song = ClipGrid()
        track = song.add_column(ClipColumn())
        scene = song.add_row(ClipRow())
        with self.assertRaises(ValueError):
            song.add_column(track)
        with self.assertRaises(ValueError):
            song.add_row(scene)

    def test_rejects_the_wrong_type(self):
        song = ClipGrid()
        for value in [BASS, None, Clip()]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    song.add_column(value)
                with self.assertRaises(ValueError):
                    song.add_row(value)
        with self.assertRaises(ValueError):
            song.add_column(ClipRow())
        with self.assertRaises(ValueError):
            song.add_row(ClipColumn())

    def test_changing_the_returned_lists_does_not_change_the_song(self):
        song = ClipGrid()
        song.add_column(ClipColumn())
        song.add_row(ClipRow())
        song.get_columns().clear()
        song.get_rows().clear()
        self.assertEqual(len(song.get_columns()), 1)
        self.assertEqual(len(song.get_rows()), 1)


class TestClipGrid(unittest.TestCase):

    def test_rejects_rows_and_columns_from_outside_the_grid(self):
        outside_row = ClipRow()
        outside_column = ClipColumn()
        calls = [
            lambda row, column: self.song.set_clip(row=row, column=column, clip=Clip()),
            self.song.get_clip,
        ]
        for call in calls:
            with self.assertRaises(ValueError):
                call(row=outside_row, column=self.track)
            with self.assertRaises(ValueError):
                call(row=self.scene, column=outside_column)

    def setUp(self):
        self.song = ClipGrid()
        self.track = self.song.add_column(ClipColumn(name=BASS))
        self.other_track = self.song.add_column(ClipColumn(name=BASS))
        self.scene = self.song.add_row(ClipRow(name=VERSE))
        self.other_scene = self.song.add_row(ClipRow(name=VERSE))

    def test_cells_start_empty(self):
        self.assertIsNone(self.song.get_clip(row=self.scene, column=self.track))

    def test_stores_and_returns_a_clip(self):
        clip = Clip(name=RIFF)
        self.assertIs(self.song.set_clip(row=self.scene, column=self.track, clip=clip), clip)
        self.assertIs(self.song.get_clip(row=self.scene, column=self.track), clip)

    def test_each_cell_is_separate_even_when_names_match(self):
        clips = {
            (self.scene, self.track): Clip(name=A),
            (self.scene, self.other_track): Clip(name=B),
            (self.other_scene, self.track): Clip(name=C),
            (self.other_scene, self.other_track): Clip(name=D),
        }
        for (scene, track), clip in clips.items():
            self.song.set_clip(row=scene, column=track, clip=clip)
        for (scene, track), clip in clips.items():
            with self.subTest(clip=clip.get_name()):
                self.assertIs(self.song.get_clip(row=scene, column=track), clip)

    def test_setting_a_filled_cell_replaces_the_clip(self):
        self.song.set_clip(row=self.scene, column=self.track, clip=Clip(name=OLD))
        new = self.song.set_clip(row=self.scene, column=self.track, clip=Clip(name=NEW))
        self.assertIs(self.song.get_clip(row=self.scene, column=self.track), new)

    def test_storage_is_nested_by_scene_id_then_track_id(self):
        clip = self.song.set_clip(row=self.scene, column=self.track, clip=Clip())
        self.assertEqual(self.song._clips, {self.scene.get_id(): {self.track.get_id(): clip}})

    def test_rejects_a_clip_of_the_wrong_type(self):
        for value in [RIFF, None, ClipColumn()]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.song.set_clip(row=self.scene, column=self.track, clip=value)

    def test_rejects_scene_and_track_in_the_wrong_order(self):
        with self.assertRaises(ValueError):
            self.song.get_clip(row=self.track, column=self.scene)

    def test_renaming_does_not_affect_the_grid(self):
        clip = self.song.set_clip(row=self.scene, column=self.track, clip=Clip())
        self.scene.set_name(CHORUS)
        self.track.set_name(LEAD)
        self.assertIs(self.song.get_clip(row=self.scene, column=self.track), clip)

    def test_tracks_and_scenes_can_only_join_one_song(self):
        other_song = ClipGrid()
        with self.assertRaises(ValueError):
            other_song.add_column(self.track)
        with self.assertRaises(ValueError):
            other_song.add_row(self.scene)
        self.assertEqual(other_song.get_columns(), [])
        self.assertEqual(other_song.get_rows(), [])

    def test_songs_with_the_same_ids_do_not_share_clips(self):
        other_song = ClipGrid()
        other_track = other_song.add_column(ClipColumn())
        other_scene = other_song.add_row(ClipRow())
        self.assertEqual((other_scene.get_id(), other_track.get_id()), (self.scene.get_id(), self.track.get_id()))
        self.song.set_clip(row=self.scene, column=self.track, clip=Clip())
        self.assertIsNone(other_song.get_clip(row=other_scene, column=other_track))

    def test_rejects_a_scene_or_track_from_another_song_with_the_same_id(self):
        other_song = ClipGrid()
        other_track = other_song.add_column(ClipColumn())
        other_scene = other_song.add_row(ClipRow())
        with self.assertRaises(ValueError):
            self.song.get_clip(row=other_scene, column=self.track)
        with self.assertRaises(ValueError):
            self.song.get_clip(row=self.scene, column=other_track)


if __name__ == '__main__':
    unittest.main()
