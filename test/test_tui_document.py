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

import os
import tempfile
import unittest
from fractions import Fraction

import yaml

from llamatron.composition.clip_slot import morph_style_name
from llamatron.composition.defaults import DEFAULT_DRUM_OCTAVE, DEFAULT_OCTAVE, DEFAULT_STEP_SIZE, DEFAULT_TEMPO, FIRST_NUMBER
from llamatron.composition.file_format import (
    SetlistSetting,
    Accidental, OctaveLabels, ClipSlotSetting, ChordSymbol, Direction, GeneratorKind, PatternSetting, Row, SceneSetting, Section,
)
from llamatron.composition.generator_settings import ArpSetting, AutoRatchetSetting, written_name
from llamatron.composition.named_scale import scale_type_name
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.song_file_error import SongFileError
from llamatron.strings.errors import ERR_FILE_PROTECTED, ERR_SAVE_BEFORE_EXPORT
from rendering import render_song
from llamatron.generators.arp import ChordOrder
from llamatron.generators.blend import BlendMode
from llamatron.music.note import Note, NoteName
from llamatron.exporters.exports import ExportKind, export_name
from llamatron.music.scale import ScaleType
from llamatron.composition.limits import MAX_OCTAVE, MIN_OCTAVE
from llamatron.composition.setlist import DEFAULT_SCALE, STARTER_DEGREE, STARTER_PATTERN_STEPS, STARTER_STEPS_PER_BEAT, Setlist, new_setlist
from llamatron.strings.names import MSG_DEFAULT_SONG_NAME, MSG_NEW_PATTERN_NAME, MSG_NEW_TRACK_NAME
from llamatron.tui.document import Document
from llamatron.tui.document_parts.pattern_edits import NEW_PATTERN_STEPS
from llamatron.composition.naming import copy_name, unique_name
from llamatron.tui.text import clock
from llamatron.tui.uses import grabbers, uses_of
from llamatron.support.example_sets import example_sets

# A setting from an early version of the format, which a new song must not write.
OLD_LENGTH_SETTING = 'default_length'
A_VELOCITY = 100
# A four-step pattern the flip and swap test rearranges, with a gap in one row.
FLIPPED_PATTERN_STEPS = 4
FLIPPED_PATTERN_ROWS = {Row.DEGREE: [1, 2, 3, 4], Row.VELOCITY: [10, None, 30, 40]}

# Names the tests give to their own things, and other values they use.
A = 'a'
B = 'b'
UNUSED = 'unused'
LEAD = 'lead'
BASS = 'bass'
UP = 'up'
ROLLS = 'rolls'
NAMED = 'named'
QUARTER = '1/4'
# Time signatures the tests use, and how many sixteenths a bar of 3/4 holds.
WALTZ = '3/4'
SEVEN_EIGHT = '7/8'
WALTZ_SIXTEENTHS = 12
HALF = '1/2'
EIGHTH = '1/8'
ONE = 'one'
TWO = 'two'
THREE = 'three'
THE_SONG = 'song untitled'
NEW = 'new'
UNTITLED = 'untitled'
TUNE = 'tune'
# A tempo no test set starts with, to see which file a change reached.
OTHER_TEMPO = 99
WRITE_TEXT = 'w'
ANOTHER = 'another'
P = 'p'
T = 't'
S = 's'
EVERY_CLIP_LOOPS = 'every clip loops'
# The file a test saves its set as, so that it can export, and what the untitled song's exports are then named.
SET_FILE = 'my_set.yml'
EXPORT = 'my_set_untitled'
LIVE_SET = EXPORT + '.als'
KEEP_ME = 'keep me'
C = 'c'
EVERY_CLIP = 'every clip'
CHAIN_NAMED = 'chain named'
X = 'x'
TOP = 'top'
OTHER = 'other'
D_MINOR_NOTES = 'D minor'
D_MAJOR = 'D Major'
D_MINOR = 'D Minor'
MAIN = 'main'
C_MAJOR_COPY = 'C Major 2'
C_MAJOR = 'C major'
A_COPY = 'a 2'
A_COPY_2 = 'a 3'
A_3 = 'a 3'
A_4 = 'a 4'
VERSE_1 = 'verse 1'
VERSE_2 = 'verse 2'
VERSE_3 = 'verse 3'
BASS_COPY = 'bass 2'
A_2 = 'a 2'
TWO_COPY = 'two 2'
ALL = 'all'
F2 = 'F2'
A3 = 'A3'
F4 = 'F4'
A5 = 'A5'
C4 = 'C4'
D = 'd'
PICK = 'Pick'
D_E_F_G_A_B_C = 'D E F G A B C'
A_C_D_E_G = 'A C D E G'
WHOLE_HALF_DIM = 'whole half dim'
BEBOP_DOM = 'bebop dom'
NATURAL_MINOR = 'natural minor'
NATURAL_MINOR_2 = 'natural_minor'
ONE_2 = 'ONE'
TWO_2 = 'TWO'


def add_pattern_with_rows(*, document, name, steps, rows):
    """Add a pattern through the document and fill its rows, given as {row: [value per step]}."""
    document.add_pattern(name=name, steps=steps)
    for row, values in rows.items():
        for step, value in enumerate(values):
            document.set_step_value(name=name, row=row, step=step, value=value)


def root_and_kind(*, document, name):
    """Return a named scale's root and type as the file writes them."""
    scale = document.song().get_named_scale(name)
    return scale.get_root(), scale.get_kind()


def song_with_things():
    """Return a document with a little of everything."""
    data = new_setlist()
    song = data[Section.SONGS][MSG_DEFAULT_SONG_NAME]
    data[Section.PATTERNS] = {
        A: {PatternSetting.STEPS: 2, PatternSetting.STEP_SIZE: QUARTER, Row.DEGREE: [1, 3]},
        B: {PatternSetting.STEPS: 1, PatternSetting.STEP_SIZE: HALF, Row.DEGREE: [5]},
        UNUSED: {PatternSetting.STEPS: 1, PatternSetting.STEP_SIZE: QUARTER},
    }
    song[Section.TRACKS] = {LEAD: {}, BASS: {}}
    data[Section.ARPS] = {UP: {ArpSetting.STEP: EIGHTH, ArpSetting.ORDER: written_name(ChordOrder.UP)}}
    data[Section.AUTO_RATCHETS] = {ROLLS: {AutoRatchetSetting.COUNTS: [2]}}
    data[Section.CHAINS] = {
        NAMED: [{GeneratorKind.ARP: UP}, {GeneratorKind.AUTO_RATCHET: ROLLS}],
    }
    song[Section.SCENES] = [
        {SceneSetting.NAME: ONE, SceneSetting.REPEAT: 2, SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.CHAIN: NAMED}}},
        {SceneSetting.NAME: TWO, SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: A, ClipSlotSetting.REPEAT: 2, ClipSlotSetting.MORPH_TO: B, ClipSlotSetting.MORPH_STYLE: morph_style_name(BlendMode.LEFT)}, BASS: {ClipSlotSetting.PATTERN: B}}},
        {SceneSetting.NAME: THREE, SceneSetting.SCALE: DEFAULT_SCALE, SceneSetting.TRACKS: {BASS: {ClipSlotSetting.PATTERN: B}}},
    ]
    return Document(setlist=Setlist.from_data(data=data))


def without_version(data):
    """Return a song's data without the version it was saved with, which moves with every release of the program."""
    return {key: value for key, value in data.items() if key != SetlistSetting.VERSION}


class TestNewSong(unittest.TestCase):

    def test_starts_with_a_pattern_of_the_root_on_each_beat_that_its_first_track_plays(self):
        document = Document()
        first_pattern = MSG_NEW_PATTERN_NAME.format(number=FIRST_NUMBER)
        first_track = MSG_NEW_TRACK_NAME.format(number=FIRST_NUMBER)
        self.assertEqual(document.song().get_pattern_names(), [first_pattern])
        pattern = document.song().get_pattern(first_pattern)
        self.assertEqual(pattern.get_steps(), STARTER_PATTERN_STEPS)
        on_beats = [step for step in range(STARTER_PATTERN_STEPS) if document.step_value(name=first_pattern, row=Row.DEGREE, step=step) == STARTER_DEGREE]
        self.assertEqual(on_beats, list(range(0, STARTER_PATTERN_STEPS, STARTER_STEPS_PER_BEAT)))
        self.assertTrue(all(document.step_value(name=first_pattern, row=Row.GATE, step=step) is None for step in range(STARTER_PATTERN_STEPS)))
        self.assertEqual(document.song().get_track_names(), [first_track])
        self.assertEqual(document.clip_slot(index=0, track=first_track).get_pattern_name(), first_pattern)
        self.assertEqual(len(uses_of(setlist=document.setlist(), section=Section.PATTERNS, name=first_pattern)), 1)
        self.assertIn(first_track, uses_of(setlist=document.setlist(), section=Section.PATTERNS, name=first_pattern)[0])

    def test_the_starter_pattern_plays_four_notes_of_the_root_and_can_be_deleted_once_its_clip_is(self):
        document = Document()
        first_pattern = MSG_NEW_PATTERN_NAME.format(number=FIRST_NUMBER)
        first_track = MSG_NEW_TRACK_NAME.format(number=FIRST_NUMBER)
        grid = render_song(document.song())
        clip = grid.get_clip(row=grid.get_rows()[0], column=grid.get_columns()[0])
        notes = [note for note in clip.resolved_notes() if isinstance(note, Note)]
        self.assertEqual(len(notes), STARTER_PATTERN_STEPS // STARTER_STEPS_PER_BEAT)
        self.assertEqual({note.get_midi_number() for note in notes}, {Note(name=NoteName.C, octave_number=DEFAULT_OCTAVE).get_midi_number()})
        document.delete_clip_slot(index=0, track=first_track)
        self.assertEqual(uses_of(setlist=document.setlist(), section=Section.PATTERNS, name=first_pattern), [])
        document.delete_named(section=Section.PATTERNS, name=first_pattern)
        self.assertEqual(document.song().get_pattern_names(), [])

    def test_has_a_c_major_scale_that_can_be_deleted(self):
        document = Document()
        self.assertEqual(document.song().get_scale_name(), DEFAULT_SCALE)
        self.assertEqual(document.song().get_scale_names(), [DEFAULT_SCALE])
        self.assertEqual(root_and_kind(document=document, name=DEFAULT_SCALE), (NoteName.C, scale_type_name(ScaleType.MAJOR)))
        self.assertEqual(uses_of(setlist=document.setlist(), section=Section.SCALES, name=DEFAULT_SCALE), [THE_SONG])
        document.set_scale_name(None)
        self.assertEqual(uses_of(setlist=document.setlist(), section=Section.SCALES, name=DEFAULT_SCALE), [])
        document.delete_named(section=Section.SCALES, name=DEFAULT_SCALE)
        self.assertEqual(document.song().get_scale_names(), [])

    def test_has_the_song_defaults(self):
        song = Document().song()
        self.assertEqual(song.get_step_size(), Fraction(DEFAULT_STEP_SIZE))
        self.assertNotIn(OLD_LENGTH_SETTING, song.to_data())
        self.assertEqual(song.get_default_octave(), DEFAULT_OCTAVE)
        self.assertEqual(song.get_default_drum_octave(), DEFAULT_DRUM_OCTAVE)

    def test_starts_with_nothing_unsaved(self):
        self.assertFalse(Document().is_dirty())

    def test_a_new_pattern_is_one_bar_of_the_song_time_signature(self):
        document = Document()
        document.add_pattern(name=A)
        self.assertEqual(document.song().get_pattern(A).get_steps(), NEW_PATTERN_STEPS)
        document.set_time_signature(WALTZ)
        document.add_pattern(name=B)
        self.assertEqual(document.song().get_pattern(B).get_steps(), WALTZ_SIXTEENTHS)

    def test_a_new_pattern_falls_back_to_sixteen_steps_when_a_bar_is_not_whole_steps(self):
        document = Document()
        document.set_time_signature(SEVEN_EIGHT)
        document.set_default_step_size(QUARTER)
        document.add_pattern(name=A)
        self.assertEqual(document.song().get_pattern(A).get_steps(), NEW_PATTERN_STEPS)
        document.add_pattern(name=B, steps=1)
        self.assertEqual(document.song().get_pattern(B).get_steps(), 1)


class TestSaving(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = temporary.name

    def test_every_example_saves_and_loads_the_same(self):
        for path in example_sets():
            document = Document.load(path)
            target = os.path.join(self.folder, os.path.basename(path))
            document.save(path=target)
            with open(path) as first, open(target) as second:
                original = yaml.safe_load(first)
                saved = yaml.safe_load(second)
            # Saving writes out the song settings that a file left to their defaults.
            with self.subTest(path=path):
                self.assertEqual(without_version({key: saved[key] for key in original}), without_version(original))

    def test_only_writes_when_asked(self):
        path = os.path.join(self.folder, 'x.yml')
        document = Document(path=path)
        document.add_track(LEAD)
        self.assertFalse(os.path.exists(path))
        self.assertTrue(document.is_dirty())
        document.save()
        self.assertTrue(os.path.exists(path))
        self.assertFalse(document.is_dirty())

    def test_rows_with_nothing_in_them_are_not_written(self):
        document = song_with_things()
        document.set_step_value(name=A, row=Row.VELOCITY, step=0, value=90)
        document.set_step_value(name=A, row=Row.VELOCITY, step=0, value=None)
        path = os.path.join(self.folder, 'x.yml')
        document.save(path=path)
        with open(path) as file:
            self.assertNotIn(Row.VELOCITY, yaml.safe_load(file)[Section.PATTERNS][A])
        self.assertIsNotNone(document.song().get_pattern(A).get_row(Row.VELOCITY))

    def test_makes_folders(self):
        path = os.path.join(self.folder, NEW, 'x.yml')
        Document().save(path=path)
        self.assertTrue(os.path.exists(path))

    def test_a_bad_file_raises(self):
        path = os.path.join(self.folder, 'bad.yml')
        with open(path, WRITE_TEXT) as file:
            file.write('tempo: fast\n')
        with self.assertRaises(SongFileError):
            Document.load(path)

    def test_a_file_that_leaves_out_settings_gets_their_defaults(self):
        for text in ['', 'tempo: 90\n']:
            path = os.path.join(self.folder, 'short.yml')
            with open(path, WRITE_TEXT) as file:
                file.write(text)
            document = Document.load(path)
            with self.subTest(text=text):
                self.assertEqual((document.song().get_track_names(), document.song().get_scenes()), ([], []))
                self.assertEqual(document.song().get_tempo(), 90 if text else DEFAULT_TEMPO)

    def test_a_protected_set_is_never_written_over_and_a_copy_of_it_is_not_protected(self):
        path = os.path.join(self.folder, 'demo.yml')
        copy = os.path.join(self.folder, 'copy.yml')
        document = Document(path=path)
        self.assertFalse(document.setlist().is_protected())
        document.set_protected(True)
        # Protecting a set that has no file yet still lets it be saved the first time.
        document.save()
        self.assertTrue(Document.load(path).setlist().is_protected())
        document.set_tempo(OTHER_TEMPO)
        self.assertTrue(document.file_is_protected())
        with self.assertRaises(SongFileError) as raised:
            document.save()
        self.assertIn(ERR_FILE_PROTECTED.format(path=path), str(raised.exception))
        self.assertNotEqual(Document.load(path).song().get_tempo(), OTHER_TEMPO)
        document.save_as(copy)
        saved = Document.load(copy)
        self.assertEqual(saved.song().get_tempo(), OTHER_TEMPO)
        self.assertFalse(saved.setlist().is_protected())
        self.assertFalse(document.file_is_protected())

    def test_the_name_comes_from_the_file(self):
        self.assertEqual(Document().get_name(), UNTITLED)
        self.assertEqual(Document(path='a/b/tune.yml').get_name(), TUNE)

    def test_exports_go_beside_the_file_named_after_the_set_and_the_song(self):
        document = Document(path='a/b/tune.yml')
        self.assertTrue(document.can_export())
        self.assertEqual(document.export_directory(), 'a/b')
        self.assertEqual(document.export_name(), export_name(setlist=TUNE, song=MSG_DEFAULT_SONG_NAME))
        self.assertEqual(document.export_path(ExportKind.ABLETON), os.path.join('a/b', 'tune_untitled.als'))

    def test_an_unsaved_set_cannot_export(self):
        self.assertFalse(Document().can_export())
        self.assertIsNone(Document().export_directory())
        with self.assertRaises(SongFileError) as caught:
            song_with_things().export(ExportKind.ABLETON)
        self.assertEqual(str(caught.exception), ERR_SAVE_BEFORE_EXPORT)


class TestRendering(unittest.TestCase):

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        previous = os.getcwd()
        self.addCleanup(os.chdir, previous)
        os.chdir(temporary.name)

    def document(self):
        """Return a saved document with a little of everything, since only a saved set can export."""
        document = song_with_things()
        document.save(path=SET_FILE)
        return document

    def test_nothing_is_written_until_asked(self):
        document = self.document()
        document.add_track(ANOTHER)
        self.assertEqual(os.listdir(), [SET_FILE])

    def test_ableton_and_clip_tree(self):
        document = self.document()
        self.assertFalse(document.export_exists(ExportKind.ABLETON))
        self.assertEqual(document.export(ExportKind.ABLETON), LIVE_SET)
        self.assertTrue(os.path.exists(LIVE_SET))
        self.assertTrue(document.export_exists(ExportKind.ABLETON))
        self.assertFalse(document.export_exists(ExportKind.CLIP_TREE))
        document.export(ExportKind.CLIP_TREE)
        self.assertTrue(document.export_exists(ExportKind.CLIP_TREE))
        self.assertIn(EXPORT + '_clip_s_001-one_1-t_001-lead.mid', os.listdir())
        self.assertTrue(all(name.startswith(EXPORT) or name == SET_FILE for name in os.listdir()))

    def test_replaces_its_own_output_and_keeps_everything_else(self):
        document = self.document()
        document.export(ExportKind.CLIP_TREE)
        with open(KEEP_ME, WRITE_TEXT) as file:
            file.write(KEEP_ME)
        document.export(ExportKind.CLIP_TREE)
        self.assertTrue(os.path.exists(KEEP_ME))
        self.assertTrue(os.path.exists(SET_FILE))

    def test_every_clip_looping_is_an_error(self):
        document = Document()
        document.save(path=SET_FILE)
        document.add_pattern(name=P, steps=1)
        document.add_track(T)
        document.add_scene(index=0, name=S)
        document.add_clip_slot(index=0, track=T, pattern=P)
        document.set_clip_slot_setting(index=0, track=T, setting=ClipSlotSetting.LOOP, value=True)
        with self.assertRaises(SongFileError) as caught:
            document.export(ExportKind.ABLETON)
        self.assertIn(EVERY_CLIP_LOOPS, str(caught.exception))

    def test_nothing_to_export(self):
        # A set from an empty file gets an empty song, unlike a new set, whose song starts with a track and a scene.
        with self.assertRaises(SongFileError):
            Document(setlist=Setlist.from_data(data={})).export(ExportKind.ABLETON)


class TestDurations(unittest.TestCase):

    def test_clock(self):
        self.assertEqual(clock(0), '0:00')
        self.assertEqual(clock(65), '1:05')
        self.assertEqual(clock(Fraction(599, 2)), '5:00')
        self.assertEqual(clock(None), '--:--')

    def test_pattern(self):
        self.assertEqual(song_with_things().lengths().pattern_seconds(A), 1)

    def test_a_new_pattern_uses_the_song_step_size(self):
        document = song_with_things()
        document.add_pattern(name=C, steps=1)
        document.set_step_value(name=C, row=Row.DEGREE, step=0, value=1)
        self.assertEqual(document.lengths().pattern_length(C), Fraction(1, 16))

    def test_clip_scene_and_song(self):
        document = song_with_things()
        self.assertEqual(document.lengths().clip_seconds(index=1, track=LEAD), 2)
        self.assertEqual(document.lengths().scene_seconds(0), 2)
        self.assertEqual(document.lengths().scene_seconds(1), 2)
        self.assertEqual(document.lengths().song_seconds(), 2 + 2 + 1)

    def test_a_change_updates_the_times(self):
        document = song_with_things()
        document.set_step_size(name=B, step_size='1')
        self.assertEqual(document.lengths().scene_seconds(2), 2)
        document.set_step_size(name=B, step_size=None)
        self.assertEqual(document.lengths().pattern_length(B), Fraction(1, 16))

    def test_a_scene_that_cannot_work_is_unknown_without_affecting_others(self):
        document = song_with_things()
        document.set_clip_slot_setting(index=2, track=BASS, setting=ClipSlotSetting.LOOP, value=True)
        self.assertIsNone(document.lengths().scene_seconds(2))
        self.assertIn(EVERY_CLIP, document.lengths().scene_problem(2))
        self.assertEqual(document.lengths().scene_seconds(1), 2)
        self.assertIsNone(document.lengths().song_seconds())


class TestUses(unittest.TestCase):

    def test_pattern(self):
        uses = uses_of(setlist=song_with_things().setlist(), section=Section.PATTERNS, name=B)
        self.assertIn('song untitled, scene 2 (two), track lead', uses)
        self.assertIn('song untitled, scene 3 (three), track bass', uses)
        self.assertEqual(uses_of(setlist=song_with_things().setlist(), section=Section.PATTERNS, name=UNUSED), [])

    def test_a_morph_target_counts_as_a_use(self):
        document = song_with_things()
        document.add_clip_slot(index=0, track=BASS, pattern=A)
        document.set_clip_slot_setting(index=0, track=BASS, setting=ClipSlotSetting.REPEAT, value=2)
        document.set_clip_slot_morph_target(index=0, track=BASS, pattern=UNUSED)
        self.assertEqual(uses_of(setlist=document.setlist(), section=Section.PATTERNS, name=UNUSED), ['song untitled, scene 1 (one), track bass'])

    def test_track_clips_are_counted_separately(self):
        self.assertEqual(song_with_things().song().track_clip_count(BASS), 2)

    def test_chain(self):
        document = song_with_things()
        self.assertEqual(uses_of(setlist=document.setlist(), section=Section.CHAINS, name=NAMED), ['song untitled, scene 1 (one), track lead'])

    def test_arp(self):
        self.assertEqual(uses_of(setlist=song_with_things().setlist(), section=Section.ARPS, name=UP), [CHAIN_NAMED])

    def test_auto_ratchet(self):
        self.assertEqual(uses_of(setlist=song_with_things().setlist(), section=Section.AUTO_RATCHETS, name=ROLLS), [CHAIN_NAMED])

    def test_what_the_document_remembers_about_a_pattern_follows_every_change_and_the_revision_moves_with_it(self):
        # The pattern editor asks the same questions for every row and cell, so the answers are kept until the set changes: a scene's scale, picking a song and an undo each move the revision and change the answer.
        document = Document()
        starter = MSG_NEW_PATTERN_NAME.format(number=FIRST_NUMBER)
        revision = document.revision()
        self.assertEqual(document.pattern_scale(starter), DEFAULT_SCALE)
        self.assertEqual(document.pattern_scale(starter), DEFAULT_SCALE)
        self.assertEqual(document.revision(), revision)
        document.add_scale(name=NAMED, root=NoteName.A, kind=scale_type_name(ScaleType.MINOR))
        self.assertGreater(document.revision(), revision)
        document.set_scene_scale(index=0, name=NAMED)
        document.record_edit()
        self.assertEqual(document.pattern_scale(starter), NAMED)
        self.assertEqual(document.scales_of_pattern(starter), [NAMED])
        self.assertEqual(document.degree_limit(starter), document.scale_size(NAMED))
        before = document.revision()
        document.select_song(MSG_DEFAULT_SONG_NAME)
        self.assertGreater(document.revision(), before)
        before = document.revision()
        document.undo()
        self.assertGreater(document.revision(), before)
        self.assertEqual(document.pattern_scale(starter), DEFAULT_SCALE)
        # The notes a pattern's steps cover are remembered the same way, and follow a note placed through the document.
        covering = document.covering_notes(starter)
        self.assertIs(document.covering_notes(starter), covering)
        document.set_step_value(name=starter, row=Row.DEGREE, step=1, value=STARTER_DEGREE)
        self.assertEqual(document.covering_notes(starter)[1], 1)

    def test_a_change_inside_a_pattern_keeps_what_was_worked_out_from_everything_else(self):
        document = song_with_things()
        uses = document.uses(section=Section.PATTERNS, name=A)
        scales = document.scales_of_pattern(A)
        covering_other = document.covering_notes(B)
        covering = document.covering_notes(A)
        outside = document.outside_patterns().revision()
        whole = document.revision()
        document.set_step_value(name=A, row=Row.VELOCITY, step=0, value=A_VELOCITY)
        # The document changed, and so did the pattern, but nothing outside the patterns: what uses the pattern, its scales and another pattern's notes are the answers already worked out.
        self.assertGreater(document.revision(), whole)
        self.assertEqual(document.outside_patterns().revision(), outside)
        self.assertIs(document.uses(section=Section.PATTERNS, name=A), uses)
        self.assertIs(document.scales_of_pattern(A), scales)
        self.assertIs(document.covering_notes(B), covering_other)
        self.assertIsNot(document.covering_notes(A), covering)

    def test_a_change_outside_the_patterns_works_those_answers_out_again(self):
        document = song_with_things()
        uses = document.uses(section=Section.PATTERNS, name=A)
        covering = document.covering_notes(A)
        outside = document.outside_patterns().revision()
        document.set_scene_name(index=0, name=NEW)
        self.assertGreater(document.outside_patterns().revision(), outside)
        self.assertIsNot(document.uses(section=Section.PATTERNS, name=A), uses)
        self.assertNotEqual(document.uses(section=Section.PATTERNS, name=A), uses)
        # The pattern itself did not change, so its notes are still the answer worked out before.
        self.assertIs(document.covering_notes(A), covering)

    def test_the_sets_step_size_changes_the_notes_a_pattern_covers(self):
        document = song_with_things()
        covering = document.covering_notes(A)
        document.set_default_step_size(EIGHTH)
        self.assertIsNot(document.covering_notes(A), covering)

    def test_a_pattern_loaded_over_another_is_another_pattern_to_what_is_remembered(self):
        document = song_with_things()
        covering = document.covering_notes(A)
        document.load_over(name=A, other=B)
        self.assertIsNot(document.covering_notes(A), covering)
        self.assertEqual(document.covering_notes(A), document.covering_notes(B))

    def test_scale(self):
        self.assertEqual(uses_of(setlist=song_with_things().setlist(), section=Section.SCALES, name=DEFAULT_SCALE), [THE_SONG, 'song untitled, scene 3 (three)'])


class TestStepSizes(unittest.TestCase):

    def test_a_new_pattern_is_empty_steps_of_the_song_step_size(self):
        document = Document()
        document.set_default_step_size(EIGHTH)
        document.add_pattern(name=P, steps=4)
        self.assertEqual(document.lengths().pattern_length(P), Fraction(1, 2))
        self.assertEqual(document.song().get_pattern(P).to_data(), {PatternSetting.STEPS: 4})

    def test_added_and_inserted_steps_are_empty_steps(self):
        document = Document()
        document.add_pattern(name=P, steps=1)
        document.set_steps(name=P, steps=3)
        document.insert_step(name=P, step=0)
        self.assertEqual(document.song().get_pattern(P).to_data(), {PatternSetting.STEPS: 4})
        self.assertEqual(document.lengths().pattern_length(P), Fraction(1, 4))

    def test_a_pattern_can_have_its_own_step_size(self):
        document = Document()
        document.add_pattern(name=P, steps=4)
        document.set_step_size(name=P, step_size=EIGHTH)
        self.assertEqual(document.lengths().pattern_length(P), Fraction(1, 2))
        document.set_step_size(name=P, step_size=None)
        self.assertIsNone(document.song().get_pattern(P).get_step_size())

    def test_a_pattern_with_no_rows_counts_the_song_step_size(self):
        document = song_with_things()
        document.add_pattern(name=X, steps=2)
        self.assertEqual(document.lengths().pattern_length(X), Fraction(1, 8))
        document.set_steps(name=X, steps=3)
        self.assertEqual(document.lengths().pattern_length(X), Fraction(3, 16))


class TestRenaming(unittest.TestCase):

    def test_pattern_updates_everything(self):
        document = song_with_things()
        document.rename_named(section=Section.PATTERNS, old=B, new=NEW)
        self.assertEqual(document.song().get_pattern_names(), [A, NEW, UNUSED])
        self.assertEqual(document.clip_slot(index=1, track=LEAD).get_morph_target(), NEW)
        self.assertEqual(document.clip_slot(index=2, track=BASS).get_pattern_name(), NEW)
        render_song(document.song())

    def test_pattern_updates_morph_to(self):
        document = song_with_things()
        document.add_clip_slot(index=0, track=BASS, pattern=A)
        document.set_clip_slot_setting(index=0, track=BASS, setting=ClipSlotSetting.REPEAT, value=2)
        document.set_clip_slot_morph_target(index=0, track=BASS, pattern=UNUSED)
        document.rename_named(section=Section.PATTERNS, old=UNUSED, new=NEW)
        self.assertEqual(document.clip_slot(index=0, track=BASS).get_morph_target(), NEW)

    def test_renaming_or_deleting_a_track_updates_grabs_from_it(self):
        document = song_with_things()
        document.add_clip_slot(index=0, track=BASS, pattern=A)
        document.set_clip_slot_setting(index=0, track=BASS, setting=ClipSlotSetting.GRAB_TRACK, value=LEAD)
        document.rename_named(section=Section.TRACKS, old=LEAD, new=TOP)
        self.assertEqual(document.clip_slot(index=0, track=BASS).get_grab_track(), TOP)
        self.assertEqual(grabbers(song=document.song(), song_name=document.current_song_name(), track=TOP), ['song untitled, scene 1 (one), track bass'])
        document.delete_named(section=Section.TRACKS, name=TOP)
        self.assertEqual(document.clip_slot(index=0, track=BASS).to_data(), {ClipSlotSetting.PATTERN: A})

    def test_finding_a_grab_circle(self):
        document = song_with_things()
        document.add_clip_slot(index=0, track=BASS, pattern=A)
        document.set_clip_slot_setting(index=0, track=BASS, setting=ClipSlotSetting.GRAB_TRACK, value=LEAD)
        self.assertEqual(document.grab_circle(index=0, track=LEAD, other=BASS), [LEAD, BASS, LEAD])
        self.assertIsNone(document.grab_circle(index=0, track=BASS, other=LEAD))

    def test_track_updates_everything(self):
        document = song_with_things()
        document.rename_named(section=Section.TRACKS, old=LEAD, new=NEW)
        self.assertEqual(document.song().get_track_names(), [NEW, BASS])
        render_song(document.song())

    def test_chain_updates_everything(self):
        document = song_with_things()
        document.rename_named(section=Section.CHAINS, old=NAMED, new=OTHER)
        self.assertEqual(document.clip_slot(index=0, track=LEAD).get_chain_names(), [OTHER])

    def test_arp_updates_chains(self):
        document = song_with_things()
        document.rename_named(section=Section.ARPS, old=UP, new=NEW)
        self.assertEqual(document.song().get_chain(NAMED).get_steps(), [(GeneratorKind.ARP, NEW), (GeneratorKind.AUTO_RATCHET, ROLLS)])

    def test_auto_ratchet_updates_chains(self):
        document = song_with_things()
        document.rename_named(section=Section.AUTO_RATCHETS, old=ROLLS, new=NEW)
        self.assertEqual(document.song().get_chain(NAMED).get_steps(), [(GeneratorKind.ARP, UP), (GeneratorKind.AUTO_RATCHET, NEW)])

    def test_changing_a_scale_keeps_its_name(self):
        document = song_with_things()
        document.change_scale(name=DEFAULT_SCALE, root=NoteName.D, kind=scale_type_name(ScaleType.MINOR))
        self.assertEqual(document.song().get_scale_name(), DEFAULT_SCALE)
        self.assertEqual(document.scale_notes_text(DEFAULT_SCALE), D_MINOR_NOTES)
        render_song(document.song())

    def test_setting_a_scales_root_and_kind_changes_what_uses_it_and_renames_a_default_name(self):
        document = song_with_things()
        self.assertEqual(document.set_scale_root(name=DEFAULT_SCALE, root=NoteName.D), D_MAJOR)
        self.assertEqual(document.set_scale_kind(name=D_MAJOR, kind=scale_type_name(ScaleType.MINOR)), D_MINOR)
        self.assertEqual(document.song().get_scale_names(), [D_MINOR])
        self.assertEqual(document.song().get_scale_name(), D_MINOR)
        self.assertEqual(document.scale_notes_text(D_MINOR), D_MINOR_NOTES)
        with self.assertRaises(InvalidValue):
            document.set_scale_root(name=D_MINOR, root=NEW)
        with self.assertRaises(InvalidValue):
            document.set_scale_kind(name=D_MINOR, kind=NEW)
        render_song(document.song())

    def test_a_scale_with_its_own_name_keeps_it_when_its_notes_change(self):
        document = song_with_things()
        document.rename_named(section=Section.SCALES, old=DEFAULT_SCALE, new=MAIN)
        self.assertEqual(document.set_scale_root(name=MAIN, root=NoteName.D), MAIN)
        self.assertEqual(document.song().get_scale_names(), [MAIN])

    def test_a_default_name_stays_when_the_new_one_is_taken(self):
        document = song_with_things()
        document.add_scale(name=D_MAJOR, root=NoteName.D, kind=scale_type_name(ScaleType.MAJOR))
        self.assertEqual(document.set_scale_root(name=DEFAULT_SCALE, root=NoteName.D), DEFAULT_SCALE)
        self.assertEqual(document.song().get_scale_names(), [DEFAULT_SCALE, D_MAJOR])

    def test_renaming_a_scale_updates_everything(self):
        document = song_with_things()
        document.rename_named(section=Section.SCALES, old=DEFAULT_SCALE, new=MAIN)
        self.assertEqual(document.song().get_scale_name(), MAIN)
        self.assertEqual(document.song().get_scenes()[2].get_scale_name(), MAIN)
        self.assertEqual(document.song().get_scale_names(), [MAIN])
        render_song(document.song())

    def test_a_scale_can_be_copied_with_the_same_notes(self):
        document = song_with_things()
        self.assertEqual(document.copy_named(section=Section.SCALES, name=DEFAULT_SCALE), C_MAJOR_COPY)
        self.assertEqual(document.scale_notes_text(C_MAJOR_COPY), C_MAJOR)


class TestLists(unittest.TestCase):

    def test_moving_and_sorting(self):
        document = song_with_things()
        self.assertTrue(document.move_named(section=Section.PATTERNS, place=0, offset=1))
        self.assertEqual(document.song().get_pattern_names(), [B, A, UNUSED])
        self.assertFalse(document.move_named(section=Section.PATTERNS, place=0, offset=-1))
        document.sort_named(Section.PATTERNS)
        self.assertEqual(document.song().get_pattern_names(), [A, B, UNUSED])

    def test_copying_makes_separate_data(self):
        document = song_with_things()
        new = document.copy_named(section=Section.PATTERNS, name=A)
        self.assertEqual(new, A_COPY)
        document.set_step_value(name=new, row=Row.DEGREE, step=0, value=7)
        self.assertEqual(document.step_value(name=A, row=Row.DEGREE, step=0), 1)
        self.assertEqual(document.copy_named(section=Section.PATTERNS, name=A), A_COPY_2)

    def test_inserting_a_track_puts_it_before_the_place_with_no_clips(self):
        document = song_with_things()
        document.insert_track(name=NEW, place=1)
        self.assertEqual(document.song().get_track_names(), [LEAD, NEW, BASS])
        self.assertIsNone(document.clip_slot(index=2, track=NEW))
        document.insert_track(name=TOP, place=0)
        self.assertEqual(document.song().get_track_names(), [TOP, LEAD, NEW, BASS])

    def test_copying_a_track_copies_its_clips(self):
        document = song_with_things()
        document.copy_named(section=Section.TRACKS, name=BASS)
        self.assertEqual(document.song().get_track_names(), [LEAD, BASS, BASS_COPY])
        self.assertEqual(document.clip_slot(index=2, track=BASS_COPY).to_data(), {ClipSlotSetting.PATTERN: B})

    def test_unique_name(self):
        self.assertEqual(unique_name(base=A, taken=[B]), A)
        self.assertEqual(unique_name(base=A, taken=[A, A_2]), A_3)

    def test_a_copy_takes_the_first_free_number_counting_up_from_one_the_name_ends_in(self):
        self.assertEqual(copy_name(name=A, taken=[A]), A_2)
        self.assertEqual(copy_name(name=A, taken=[A, A_2]), A_3)
        self.assertEqual(copy_name(name=A_2, taken=[A, A_2]), A_3)
        self.assertEqual(copy_name(name=A_2, taken=[A_2, A_3]), A_4)
        self.assertEqual(copy_name(name=VERSE_1, taken=[VERSE_1]), VERSE_2)
        self.assertEqual(copy_name(name=VERSE_1, taken=[VERSE_1, VERSE_2]), VERSE_3)


class TestScenes(unittest.TestCase):

    def setUp(self):
        self.document = song_with_things()

    def names(self):
        return [scene.get_name() for scene in self.document.song().get_scenes()]

    def test_moving_a_scene(self):
        self.document.move_scene(index=0, offset=1)
        self.assertEqual(self.names(), [TWO, ONE, THREE])

    def test_deleting_a_scene(self):
        self.document.delete_scene(1)
        self.assertEqual(self.names(), [ONE, THREE])

    def test_adding_a_scene(self):
        self.document.add_scene(index=0, name=NEW)
        self.assertEqual(self.names(), [NEW, ONE, TWO, THREE])

    def test_copying_a_scene(self):
        self.document.copy_scene(1)
        self.assertEqual(self.names(), [ONE, TWO, TWO_COPY, THREE])

    def test_repeats(self):
        self.document.set_scene_repeat(index=1, repeat=3)
        self.assertEqual(self.document.song().get_scenes()[1].get_repeat(), 3)
        self.document.set_scene_repeat(index=0, repeat=1)
        self.assertNotIn(SceneSetting.REPEAT, self.document.song().get_scenes()[0].to_data())

    def test_the_result_still_builds(self):
        self.document.move_scene(index=0, offset=1)
        self.document.copy_scene(0)
        self.document.delete_scene(1)
        self.document.set_scene_repeat(index=0, repeat=4)
        render_song(self.document.song())


class TestPatternSteps(unittest.TestCase):

    def test_shortening_counts_what_would_be_lost(self):
        document = song_with_things()
        self.assertEqual(document.steps_with_anything_past(name=A, steps=1), 1)
        self.assertEqual(document.steps_with_anything_past(name=A, steps=2), 0)

    def test_an_empty_step_is_not_something_to_lose(self):
        document = song_with_things()
        document.set_steps(name=A, steps=4)
        self.assertEqual(document.steps_with_anything_past(name=A, steps=2), 0)
        document.set_step_value(name=A, row=Row.DEGREE, step=3, value=1)
        self.assertEqual(document.steps_with_anything_past(name=A, steps=2), 1)

    def test_setting_steps_keeps_rows_the_right_length(self):
        document = song_with_things()
        document.set_steps(name=A, steps=4)
        self.assertEqual(document.song().get_pattern(A).get_row(Row.DEGREE), [1, 3, None, None])
        document.set_step_value(name=A, row=Row.GATE, step=0, value=HALF)
        document.set_steps(name=A, steps=1)
        self.assertEqual(document.song().get_pattern(A).get_row(Row.DEGREE), [1])
        self.assertEqual(document.song().get_pattern(A).get_row(Row.GATE), [HALF])

    def test_a_notes_span_is_its_ties_or_its_gate_in_whole_steps_and_the_ties_after(self):
        document = song_with_things()
        document.set_steps(name=A, steps=6)
        self.assertEqual(document.note_span(name=A, step=0), 1)
        document.set_step_value(name=A, row=Row.GATE, step=1, value='3/8')
        self.assertEqual(document.note_span(name=A, step=1), 2)
        document.set_step_value(name=A, row=Row.TIE, step=3, value=True)
        self.assertEqual(document.note_span(name=A, step=1), 3)
        self.assertEqual(document.covering_notes(A), {0: 0, 1: 1, 2: 1, 3: 1})
        # A later note always shows over an earlier one's gate.
        document.set_step_value(name=A, row=Row.GATE, step=0, value='1')
        self.assertEqual(document.covering_notes(A)[0], 0)
        self.assertEqual(document.covering_notes(A)[1], 1)

    def test_placing_by_entry_size(self):
        document = song_with_things()
        document.set_steps(name=A, steps=4)
        document.place_note(name=A, step=2, degree=4, octave=3)
        self.assertEqual(document.song().get_pattern(A).get_row(Row.DEGREE), [1, 3, 4, None])
        self.assertIsNone(document.song().get_pattern(A).get_row(Row.TIE))
        document.set_pattern_entry_size(name=A, entry_size=HALF)
        document.place_note(name=A, step=1, degree=2, octave=3)
        self.assertEqual(document.song().get_pattern(A).get_row(Row.DEGREE), [1, 2, None, None])
        self.assertEqual(document.song().get_pattern(A).get_row(Row.TIE), [False, False, True, False])
        document.set_pattern_entry_size(name=A, entry_size=EIGHTH)
        document.place_note(name=A, step=3, degree=5, octave=3)
        self.assertEqual(document.step_value(name=A, row=Row.GATE, step=3), EIGHTH)

    def test_lengthening_shortening_and_the_accidental(self):
        document = song_with_things()
        document.set_steps(name=A, steps=4)
        self.assertTrue(document.lengthen_note(name=A, step=1))
        self.assertEqual(document.song().get_pattern(A).get_row(Row.TIE), [False, False, True, False])
        self.assertTrue(document.lengthen_note(name=A, step=2))
        self.assertFalse(document.lengthen_note(name=A, step=1))
        self.assertFalse(document.lengthen_note(name=A, step=0))
        self.assertTrue(document.shorten_note(name=A, step=3))
        self.assertEqual(document.song().get_pattern(A).get_row(Row.TIE), [False, False, True, False])
        self.assertTrue(document.shorten_note(name=A, step=1))
        self.assertFalse(document.shorten_note(name=A, step=1))
        # A's steps are quarter notes, so a half-note gate shortened by a step is one step, which is written blank.
        document.set_step_value(name=A, row=Row.GATE, step=0, value=HALF)
        self.assertTrue(document.shorten_note(name=A, step=0))
        self.assertIsNone(document.step_value(name=A, row=Row.GATE, step=0))
        document.set_step_value(name=A, row=Row.GATE, step=0, value='3/4')
        self.assertTrue(document.shorten_note(name=A, step=0))
        self.assertEqual(document.step_value(name=A, row=Row.GATE, step=0), HALF)
        self.assertTrue(document.cycle_accidental(name=A, step=0))
        self.assertEqual(document.step_value(name=A, row=Row.ACCIDENTAL, step=0), Accidental.SHARP)
        self.assertFalse(document.cycle_accidental(name=A, step=3))
        self.assertTrue(document.split_note(name=A, step=1) is False)

    def test_a_note_that_cannot_be_reshaped_leaves_the_set_unchanged_and_saved(self):
        document = song_with_things()
        document.set_steps(name=A, steps=2)
        document.forget_history()
        saved = Document(setlist=Setlist.from_data(data=document.setlist().to_data()))
        before = saved.revision()
        # A has a note on each of its two steps: neither has room after it, is longer than a step, or holds a tie to split.
        self.assertFalse(saved.lengthen_note(name=A, step=0))
        self.assertFalse(saved.lengthen_note(name=A, step=1))
        self.assertFalse(saved.shorten_note(name=A, step=0))
        self.assertFalse(saved.split_note(name=A, step=1))
        self.assertFalse(saved.is_dirty())
        self.assertEqual(saved.revision(), before)
        self.assertFalse(saved.record_edit())
        # One that can be is a change inside the pattern alone.
        saved.set_steps(name=A, steps=3)
        saved.record_edit()
        outside = saved.outside_patterns().revision()
        self.assertTrue(saved.lengthen_note(name=A, step=1))
        self.assertTrue(saved.is_dirty())
        self.assertEqual(saved.outside_patterns().revision(), outside)
        self.assertTrue(saved.record_edit())

    def test_the_octave_range_of_the_one_track_that_plays_a_pattern(self):
        document = song_with_things()
        self.assertEqual(document.pattern_octave_range(A), (MIN_OCTAVE, MAX_OCTAVE))
        document.set_track_lowest_octave(name=LEAD, octave=2)
        self.assertEqual(document.pattern_octave_range(A), (2, MAX_OCTAVE))
        # B is played by the bass and morphed to by the lead, which counts as a use, and nothing plays the unused pattern.
        self.assertIsNone(document.pattern_octave_range(B))
        self.assertIsNone(document.pattern_octave_range(UNUSED))
        document.add_clip_slot(index=0, track=BASS, pattern=A)
        self.assertIsNone(document.pattern_octave_range(A))

    def test_insert_and_remove(self):
        document = song_with_things()
        document.insert_step(name=A, step=1)
        self.assertEqual(document.song().get_pattern(A).get_row(Row.DEGREE), [1, None, 3])
        self.assertEqual(document.song().get_pattern(A).get_steps(), 3)
        document.remove_step(name=A, step=0)
        self.assertEqual(document.song().get_pattern(A).get_row(Row.DEGREE), [None, 3])

    def test_changing_type_clears_notes_and_keeps_timing(self):
        document = song_with_things()
        document.set_step_value(name=A, row=Row.CHORD, step=0, value=ChordSymbol.MAJOR)
        document.set_drum(name=A, drum=True)
        pattern = document.song().get_pattern(A)
        self.assertTrue(pattern.is_drum())
        self.assertIsNone(pattern.get_row(Row.DEGREE))
        self.assertIsNone(pattern.get_row(Row.CHORD))
        self.assertEqual((pattern.get_steps(), pattern.get_step_size()), (2, Fraction(1, 4)))

    def test_forward_is_not_written(self):
        document = song_with_things()
        document.set_direction(name=A, direction=Direction.PENDULUM)
        self.assertEqual(document.song().get_pattern(A).get_direction(), Direction.PENDULUM)
        document.set_direction(name=A, direction=Direction.FORWARD)
        self.assertNotIn(PatternSetting.DIRECTION, document.song().get_pattern(A).to_data())

    def test_flip_and_swap_move_every_row(self):
        document = song_with_things()
        add_pattern_with_rows(document=document, name=X, steps=FLIPPED_PATTERN_STEPS, rows=FLIPPED_PATTERN_ROWS)
        document.reverse_after(name=X, step=0)
        self.assertEqual(document.song().get_pattern(X).get_row(Row.DEGREE), [1, 4, 3, 2])
        self.assertEqual(document.song().get_pattern(X).get_row(Row.VELOCITY), [10, 40, 30, None])
        self.assertEqual(document.pivot_around(name=X, step=1), 2)
        self.assertEqual(document.song().get_pattern(X).get_row(Row.DEGREE), [3, 2, 4, 1])
        self.assertTrue(document.is_dirty())

    def test_load_over_copies_everything_and_stays_separate(self):
        document = song_with_things()
        document.load_over(name=UNUSED, other=A)
        self.assertEqual(document.song().get_pattern(UNUSED).to_data(), document.song().get_pattern(A).to_data())
        document.set_step_value(name=UNUSED, row=Row.DEGREE, step=0, value=7)
        self.assertEqual(document.step_value(name=A, row=Row.DEGREE, step=0), 1)

    def test_degree_limit_uses_the_biggest_scale_this_pattern_can_play_in(self):
        document = song_with_things()
        self.assertEqual(document.degree_limit(UNUSED), 7)
        document.set_scale_name(None)
        self.assertEqual(document.degree_limit(UNUSED), 7)
        document.add_scale(name=ALL, root=NoteName.C, kind=scale_type_name(ScaleType.CHROMATIC))
        document.set_scene_scale(index=0, name=ALL)
        self.assertEqual(document.degree_limit(A), 12)
        self.assertEqual(document.degree_limit(UNUSED), 7)

    def test_note_names(self):
        document = song_with_things()
        document.add_scale(name=MAIN, root=NoteName.F, kind=scale_type_name(ScaleType.MAJOR))
        document.set_scale_name(MAIN)
        document.set_step_value(name=A, row=Row.OCTAVE, step=0, value=4)
        self.assertEqual(document.note_name(name=A, step=0), F2)
        self.assertEqual(document.note_name(name=A, step=1), A3)
        document.set_step_value(name=A, row=Row.ACCIDENTAL, step=1, value=Accidental.FLAT)
        self.assertEqual(document.note_name(name=A, step=1), 'G#3')

    def test_note_names_follow_the_octave_labels(self):
        document = song_with_things()
        document.add_scale(name=MAIN, root=NoteName.F, kind=scale_type_name(ScaleType.MAJOR))
        document.set_scale_name(MAIN)
        document.set_step_value(name=A, row=Row.OCTAVE, step=0, value=4)
        document.set_octave_labels(OctaveLabels.LLAMATRON)
        self.assertEqual(document.note_name(name=A, step=0), F4)
        self.assertEqual(document.note_name(name=A, step=1), A5)
        document.set_octave_labels(OctaveLabels.LIVE)
        self.assertEqual(document.note_name(name=A, step=0), F2)

    def test_note_name_past_the_top_of_the_scale_wraps_up(self):
        document = song_with_things()
        document.set_step_value(name=A, row=Row.DEGREE, step=0, value=8)
        self.assertEqual(document.note_name(name=A, step=0), C4)

    def test_note_name_for_a_drum(self):
        document = song_with_things()
        document.add_pattern(name=D, steps=1)
        document.set_drum(name=D, drum=True)
        document.set_step_value(name=D, row=Row.DEGREE, step=0, value=NoteName.F)
        document.set_step_value(name=D, row=Row.ACCIDENTAL, step=0, value=Accidental.SHARP)
        self.assertEqual(document.note_name(name=D, step=0), 'F#1')

    def test_note_name_without_a_scale(self):
        document = song_with_things()
        document.set_scale_name(None)
        self.assertIsNone(document.note_name(name=A, step=0))


class TestPickerLayouts(unittest.TestCase):
    """Every chord, scale and root has exactly one place in its picker."""

    def test_every_chord_has_a_name_and_every_named_chord_a_short_name(self):
        from llamatron.composition.file_format import CHORD_SYMBOLS, FIXED_CHORDS
        from llamatron.strings.labels import MSG_CHORD_NAMES
        from llamatron.strings.marks import MSG_CHORD_SUFFIXES
        self.assertEqual(set(MSG_CHORD_NAMES), set(CHORD_SYMBOLS))
        self.assertEqual(set(MSG_CHORD_SUFFIXES), set(FIXED_CHORDS))

    def test_scale_pages_hold_every_kind_once_except_melodic_minor(self):
        from llamatron.composition.named_scale import SCALE_TYPE_NAMES
        from llamatron.tui.screens.scale_page import SCALE_PAGES
        flat = [kind for _, columns in SCALE_PAGES for groups in columns for _, kinds in groups for kind in kinds]
        flat.remove(scale_type_name(ScaleType.MELODIC_MINOR))
        self.assertEqual(sorted(flat), sorted(SCALE_TYPE_NAMES))

    def test_a_paged_grid_opens_on_the_page_of_the_current_option(self):
        from llamatron.tui.dialogs.grid_choice_dialog import GridChoiceDialog
        dialog = GridChoiceDialog(title=PICK, options=[A, B, C], grid=None, current=2, pages=[(ONE_2, [[0, 1]]), (TWO_2, [[1, 2]])])
        self.assertEqual(dialog.page, 1)
        self.assertEqual(dialog.where(), (0, 1))
        self.assertEqual(GridChoiceDialog(title=PICK, options=[A, B, C], grid=None, current=1, pages=[(ONE_2, [[0, 1]]), (TWO_2, [[1, 2]])]).page, 0)

    def test_the_keyboard_holds_every_root_once(self):
        from llamatron.music.note import ROOT_NAMES
        from llamatron.tui.screens.scale_page import ROOT_KEYBOARD
        flat = [name for row in ROOT_KEYBOARD for name in row if name]
        self.assertEqual(sorted(flat), sorted(ROOT_NAMES))

    def test_scale_notes(self):
        from llamatron.tui.screens.scale_page import scale_label, scale_notes
        self.assertEqual(scale_notes(root=NoteName.D, kind=scale_type_name(ScaleType.DORIAN)), D_E_F_G_A_B_C)
        self.assertEqual(scale_notes(root=NoteName.A, kind=scale_type_name(ScaleType.MINOR_PENTATONIC)), A_C_D_E_G)
        self.assertEqual(scale_label(scale_type_name(ScaleType.WHOLE_HALF_DIMINISHED)), WHOLE_HALF_DIM)
        self.assertEqual(scale_label(scale_type_name(ScaleType.BEBOP_DOMINANT)), BEBOP_DOM)
        self.assertEqual(scale_label(NATURAL_MINOR_2), NATURAL_MINOR)

if __name__ == '__main__':
    unittest.main()
