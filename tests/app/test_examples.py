# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Every example song loads, plays and renders to every kind of output."""

import contextlib
import io
import os
import tempfile
import unittest

from llamatron.exporters.exports import ExportKind, make_exporter
from llamatron.model.file import example_sets as example_sets_values
from llamatron.model.file.example_sets import example_sets, folder_of_example, genre_folder
from llamatron.model.file.setlist_reader import set_file_data
from llamatron.model.schema import generator_plugins
from llamatron.model.schema.file_format import Section
from tests.support import rendering
from tests.support.example_renders import example_setlist, first_song_grid
from tests.support.rendering import is_demo
from tests.support.song_testing import pitches

SONG = 'song'
# Every song in examples/, including the demos, which test_demos.py checks more closely.
EXAMPLE_PATHS = example_sets()
GENRE_WITH_A_SPACE = 'TV theme'
FOLDER_OF_GENRE_WITH_A_SPACE = 'tv_theme'
GENRE_WITH_A_HYPHEN = 'Hip-Hop'
FOLDER_OF_GENRE_WITH_A_HYPHEN = 'hip_hop'
GENRE_OF_ONE_WORD = 'Rock'
FOLDER_OF_GENRE_OF_ONE_WORD = 'rock'
# The songs that are meant to sound good, rather than to teach one feature.
SONG_PATHS = [path for path in EXAMPLE_PATHS if not is_demo(path)]
LOWEST_PIANO_KEY = 21
HIGHEST_PIANO_KEY = 108
# Every kind of output an example exports to.
EXPORTED_KINDS = (ExportKind.ABLETON, ExportKind.MIDI_FILE, ExportKind.STEMS, ExportKind.CLIP_TREE, ExportKind.GENERAL_MIDI)
# What an exporter prints when it has to leave something out, which a demo never does.
WARNING = 'warning'


class TestExamples(unittest.TestCase):
    """What holds of the examples together. What holds of each example alone is checked once a class, with one reading and one
    render of the example (tests/app/test_every_example.py), by the functions below."""

    paths = EXAMPLE_PATHS
    songs = SONG_PATHS

    def test_the_pieces_are_the_sets_besides_the_demos(self):
        self.assertEqual([os.path.basename(path) for path in self.songs], sorted(rendering.PIECES))

    def test_a_genres_folder_is_lower_case_with_underscores_for_spaces_and_hyphens(self):
        self.assertEqual(genre_folder(GENRE_WITH_A_SPACE), FOLDER_OF_GENRE_WITH_A_SPACE)
        self.assertEqual(genre_folder(GENRE_WITH_A_HYPHEN), FOLDER_OF_GENRE_WITH_A_HYPHEN)
        self.assertEqual(genre_folder(GENRE_OF_ONE_WORD), FOLDER_OF_GENRE_OF_ONE_WORD)

    def test_every_generator_is_used(self):
        used = set()
        for path in self.paths:
            for chain in (set_file_data(path)[0].get(Section.CHAINS) or {}).values():
                used |= {next(iter(step)) for step in chain}
            used |= built_ins_used(example_setlist(path))
        self.assertEqual(set(generator_plugins.plugins()) - used, set())

    def test_tempo_keeps_rising_through_minimal_techno(self):
        song = first_song_grid('examples/by_genre/electronic/minimal_techno.yml')
        tempos = [scene.get_tempo() or song.get_tempo() for scene in song.get_rows()]
        self.assertEqual(tempos, sorted(tempos))
        self.assertGreater(tempos[-1], tempos[0])


def check_homage_folder(*, test, path):
    """A homage is in the folder of its one genre."""
    if folder_of_example(path) != example_sets_values.BY_GENRE:
        return
    genres = example_setlist(path).get_genres()
    test.assertEqual(len(genres), 1)
    test.assertEqual(os.path.basename(os.path.dirname(path)), genre_folder(genres[0]))


def check_clips_fit(*, test, path):
    """Every clip lasts as long as its scene, and every note is on a piano's keys."""
    song = first_song_grid(path)
    for scene in song.get_rows():
        clips = [song.get_clip(row=scene, column=t) for t in song.get_columns() if song.get_clip(row=scene, column=t)]
        test.assertEqual(len({c.total_length() for c in clips}), 1)
        for each in clips:
            found = pitches(each)
            if found:
                with test.subTest(scene=scene.get_name()):
                    test.assertGreaterEqual(min(found), LOWEST_PIANO_KEY)
                    test.assertLessEqual(max(found), HIGHEST_PIANO_KEY)


def check_exports(*, test, path):
    """The example's first song exports to every kind of output, as the command line exports it, and a demo with no warning."""
    grid = first_song_grid(path)
    for kind in EXPORTED_KINDS:
        with tempfile.TemporaryDirectory() as parent, test.subTest(to=kind):
            out = os.path.join(parent, SONG)
            printed = io.StringIO()
            with contextlib.redirect_stdout(printed):
                make_exporter(kind=kind, directory=out, name=SONG, grid=grid).export()
            test.assertTrue(os.listdir(out))
            if is_demo(path):
                test.assertNotIn(WARNING, printed.getvalue())


def check_sounds(*, test, path):
    """Every track that plays can be heard out of the box: through FluidSynth with a sound, and a drum part on a drum track, as General MIDI's channel 10 plays it."""
    setlist = example_setlist(path)
    test.assertTrue(setlist.is_real_time())
    for song in setlist.get_songs():
        for name in song.get_track_names():
            track = song.get_track(name)
            patterns = {scene.get_clip_slot(name).get_pattern_name() for scene in song.get_scenes() if scene.get_clip_slot(name) is not None}
            with test.subTest(track=name):
                if patterns and all(setlist.get_pattern(pattern).is_drum() for pattern in patterns):
                    test.assertTrue(track.is_drum())
                if track.is_muted():
                    continue
                test.assertIsNotNone(track.get_instrument_name())
                instrument = setlist.get_instrument(track.get_instrument_name())
                test.assertTrue(instrument.uses_fluidsynth())
                if not track.is_drum():
                    test.assertIsNotNone(instrument.get_gm_sound())


def built_ins_used(setlist):
    """Return the kinds of the built-in generators that any clip or track of a set has switched on."""
    used = set()
    for song in setlist.get_songs():
        for name in song.get_track_names():
            used |= set(song.get_track(name).built_ins_on())
            for scene in song.get_scenes():
                clip_slot = scene.get_clip_slot(name)
                if clip_slot is not None:
                    used |= set(clip_slot.built_ins_on())
    return used
