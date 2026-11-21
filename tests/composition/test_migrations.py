# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The migrations: each older layout of a set file moved to the layout written now, by version, or by shape where a file
records no version, with what moving it changed, and the rule that nothing outside the package reaches into it."""

import ast
import copy
from fractions import Fraction
import pathlib
import unittest

from llamatron.composition import file_format
from llamatron.composition.file_format import ClipSlotSetting, FileLayout, GeneratorKind, Section, SetlistSetting
from llamatron.composition.file_layout import as_object_layout
from llamatron.composition.migrations import migrated
from llamatron.composition.setlist import Setlist
from llamatron.composition.song_file_error import SongFileError
from llamatron.playback.song_renderer import SongRenderer
from llamatron.user_strings import names
from tests.support import song_testing
from tests.support.rendering import as_setlist, render_data
from tests.support.song_testing import clip, pat, pitches, with_parts

DATA = pathlib.Path(__file__).resolve().parent.parent / 'data' / 'migrations'
EXAMPLES = pathlib.Path(__file__).resolve().parent.parent.parent / 'examples'
SRC = pathlib.Path(__file__).resolve().parent.parent.parent / 'src' / 'llamatron'
MIGRATIONS = SRC / 'composition' / 'migrations'
STRUM_BEFORE_LISTS = DATA / 'strum_before_lists.yml'
STRUM_NOW = EXAMPLES / 'learning' / '13_classic_strum.yml'
OUT_OF_RANGE_BEFORE_LISTS = DATA / 'out_of_range_before_lists.yml'
# The chains of the strum demo before lists, each of which a generator of another kind came first with.
STRUM_RENAMES = [(FileLayout.CHAIN, 'verse', 'verse-2'), (FileLayout.CHAIN, 'harp roll', 'harp roll-2'), (FileLayout.CHAIN, 'chorus', 'chorus-2')]
# Versions from before each change of layout.
BEFORE_LIVE_OCTAVES = '1.0.24'
LIVE_OCTAVES_SINCE = '1.0.30'
BEFORE_NOTES = '1.0.100'
NOTES_SINCE = '1.0.155'
BEFORE_LISTS = '1.0.590'
FILE_STEM = 'old_tune'
SEED = 3
NOTES = 'Two lines\nof notes\n'
OCTAVE = 3
DRUM_OCTAVE = 1
MIDDLE_C = 60
LOW_C = 36
ONE_LINE = 'A tune'
NO_TEXT = ''
SHARED = 'shared'
# The names a module outside the package may import from it.
FRONT_DOOR = {'Conversion', 'migrated'}
PACKAGE = 'llamatron.composition.migrations'
# What a migration may import from outside its package: the naming rules, and how versions compare.
ALLOWED_TO_MIGRATIONS = ('llamatron.composition', 'llamatron.support.version')
SOURCE_FILES = '*.py'
UNTITLED = names.MSG_DEFAULT_SONG_NAME
HALF = Fraction(1, 2)
# A clip's single chain, as a file from before lists of chains held it.
OLD_CHAIN = FileLayout.CHAIN


def read_migrated(data, *, one_song_name=None):
    """Return the set some file data makes once moved by every migration due, and the Conversion."""
    moved, conversion = migrated(copy.deepcopy(data), one_song_name=one_song_name)
    return Setlist.from_data(data=as_object_layout(moved)), conversion


def played(path):
    """Return what every clip of a set file's first song plays, scene by scene and track by track, with a fixed seed."""
    setlist = Setlist.read_file(str(path))
    song = setlist.get_song(setlist.get_song_names()[0])
    grid = SongRenderer(song, seed=SEED).render()
    return [sorted(map(repr, grid.get_clip(row=row, column=column).get_sounds())) if grid.get_clip(row=row, column=column) else None
            for row in grid.get_rows() for column in grid.get_columns()]


def old_lead(**more):
    """Return a song's data in the layout before lists, with one track playing middle C as written in octave 3."""
    return with_parts(patterns={song_testing.X: pat([1, HALF], octave=[OCTAVE])}, scenes=[{Section.TRACKS: {song_testing.LEAD: {ClipSlotSetting.PATTERN: song_testing.X}}}], **more)


class TestLists(unittest.TestCase):

    def test_a_file_before_lists_reads_as_the_file_written_now_and_plays_the_same(self):
        old = Setlist.read_file(str(STRUM_BEFORE_LISTS))
        self.assertTrue(old.get_conversion().has_moved())
        self.assertEqual(old.get_conversion().get_renames(), STRUM_RENAMES)
        self.assertEqual(played(STRUM_BEFORE_LISTS), played(STRUM_NOW))

    def test_a_file_written_now_is_not_moved(self):
        now = Setlist.read_file(str(STRUM_NOW))
        self.assertFalse(now.get_conversion().has_moved())
        self.assertEqual(now.get_conversion().get_renames(), [])

    def test_a_file_with_no_version_is_moved_when_it_has_the_old_shape_and_not_when_it_has_the_new(self):
        old = as_setlist(old_lead())
        old.pop(SetlistSetting.VERSION, None)
        _, conversion = read_migrated(old)
        self.assertTrue(conversion.has_moved())
        moved, _ = migrated(copy.deepcopy(old))
        _, again = migrated(copy.deepcopy(moved))
        self.assertFalse(again.has_moved())

    def test_a_clips_single_chain_becomes_a_list_of_one(self):
        data = as_setlist(old_lead(arps={SHARED: {}}, chains={song_testing.X: [{GeneratorKind.ARP: SHARED}]}))
        data[Section.SONGS][UNTITLED][Section.SCENES][0][Section.TRACKS][song_testing.LEAD][OLD_CHAIN] = song_testing.X
        setlist, _ = read_migrated(data)
        song = setlist.get_song(UNTITLED)
        self.assertEqual(song.get_scenes()[0].get_clip_slot(song_testing.LEAD).get_chain_names(), [song_testing.X])

    def test_two_generators_of_different_kinds_with_one_name_are_told_apart_and_their_chain_follows(self):
        data = as_setlist(old_lead(arps={SHARED: {}}, auto_ratchets={SHARED: {'counts': [2]}}, chains={song_testing.X: [{GeneratorKind.ARP: SHARED}, {GeneratorKind.AUTO_RATCHET: SHARED}]}))
        setlist, conversion = read_migrated(data)
        renamed = SHARED + '-2'
        self.assertEqual(conversion.get_renames(), [(GeneratorKind.AUTO_RATCHET, SHARED, renamed)])
        self.assertEqual([tuple(step) for step in setlist.get_chain(song_testing.X).get_steps()], [(GeneratorKind.ARP, SHARED), (GeneratorKind.AUTO_RATCHET, renamed)])

    def test_an_old_file_with_values_out_of_range_is_moved_then_corrected(self):
        setlist, corrections = Setlist.read_file_corrected(str(OUT_OF_RANGE_BEFORE_LISTS))
        self.assertTrue(setlist.get_conversion().has_moved())
        self.assertTrue(corrections)
        with self.assertRaises(SongFileError):
            Setlist.read_file(str(OUT_OF_RANGE_BEFORE_LISTS))


class TestOlderLayouts(unittest.TestCase):

    def test_a_file_saved_before_the_numbering_changed_has_its_octaves_moved_up(self):
        # Older files numbered octaves as Live labels them, two lower, so an old 3 and a new 5 are both middle C.
        data = as_setlist(old_lead())
        data.update({SetlistSetting.DEFAULT_OCTAVE: OCTAVE, SetlistSetting.DEFAULT_DRUM_OCTAVE: DRUM_OCTAVE, SetlistSetting.VERSION: BEFORE_LIVE_OCTAVES})
        setlist, _ = read_migrated(data)
        song = setlist.get_song(UNTITLED)
        self.assertEqual((song.get_default_octave(), song.get_default_drum_octave()), (OCTAVE + file_format.LIVE_OCTAVE_OFFSET, DRUM_OCTAVE + file_format.LIVE_OCTAVE_OFFSET))
        self.assertEqual(pitches(clip(song=render_data(setlist.to_data()), scene=1, track=song_testing.LEAD)), [MIDDLE_C])

    def test_a_file_saved_since_the_numbering_changed_or_without_a_version_keeps_its_octaves(self):
        for saved in [LIVE_OCTAVES_SINCE, BEFORE_LISTS, None]:
            with self.subTest(version=saved):
                data = as_setlist(old_lead())
                if saved is not None:
                    data[SetlistSetting.VERSION] = saved
                setlist, _ = read_migrated(data)
                self.assertEqual(pitches(clip(song=render_data(setlist.to_data()), scene=1, track=song_testing.LEAD)), [LOW_C])

    def test_a_file_from_before_notes_existed_holds_its_long_text_under_description_which_reads_as_notes(self):
        old, _ = read_migrated({SetlistSetting.VERSION: BEFORE_NOTES, SetlistSetting.DESCRIPTION: NOTES, Section.SONGS: {}})
        self.assertEqual((old.get_notes(), old.get_description()), (NOTES, NO_TEXT))
        new, _ = read_migrated({SetlistSetting.VERSION: NOTES_SINCE, SetlistSetting.DESCRIPTION: ONE_LINE, Section.SONGS: {}})
        self.assertEqual((new.get_notes(), new.get_description()), (NO_TEXT, ONE_LINE))

    def test_a_file_from_before_sets_holds_one_song_named_after_the_file(self):
        setlist, conversion = read_migrated(old_lead(), one_song_name=FILE_STEM)
        self.assertTrue(conversion.has_moved())
        self.assertEqual(setlist.get_song_names(), [FILE_STEM])


class TestMigrationsStayApart(unittest.TestCase):

    def test_nothing_outside_the_package_imports_more_of_it_than_the_front_door(self):
        found = []
        for path in sorted(SRC.rglob(SOURCE_FILES)):
            if MIGRATIONS in path.parents:
                continue
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith(PACKAGE):
                    if node.module != PACKAGE or {alias.name for alias in node.names} - FRONT_DOOR:
                        found.append(str(path.relative_to(SRC)))
        self.assertEqual(found, [])

    def test_a_migration_knows_nothing_of_the_objects_or_the_reader(self):
        found = []
        for path in sorted(MIGRATIONS.glob(SOURCE_FILES)):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith('llamatron.') and not node.module.startswith(PACKAGE):
                    if node.module not in ALLOWED_TO_MIGRATIONS:
                        found.append((path.name, node.module))
        self.assertEqual(found, [])


if __name__ == '__main__':
    unittest.main()
