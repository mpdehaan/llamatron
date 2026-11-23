# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The demos in examples/ build, export and save, and the generator that wrote them matches its sources.

The demos are the sets in examples/ whose names end in _demo, each holding one song, and docs/DEMOS.md describes
them. TestDemos deliberately doesn't check what they play, so that they can be edited freely.
TestDemoSources instead runs tests/data/demo_sources/make_demos.py into a temporary folder, and checks
what it writes against the source data kept beside it, so nothing here uses the network.
"""

import collections
from fractions import Fraction
import glob
import importlib.util
import os
import pathlib
import tempfile
import unittest
import yaml

from llamatron.engine.timing.timing import timed_events
from llamatron.interface.tracker import drawing
from llamatron.model.file.example_sets import example_sets
from llamatron.model.file.setlist_reader import set_file_data
from llamatron.model.schema.file_format import Section, SetlistSetting, TrackSetting
from tests.support.rendering import is_demo, render_file

PATHS = sorted(path for path in example_sets() if is_demo(path))
# Demos written by hand, rather than first written by tests/data/demo_sources/make_demos.py.
HAND_WRITTEN = ['28_draws.yml', '26_accents.yml', '27_pattern_lists.yml', '13_acid_articulate.yml', '21_guitarify.yml', '22_follow_chords.yml', '23_phrasing.yml', '24_musician.yml', '12_acid_glide.yml', '07_blues_chords.yml', '14_bolero_swell.yml', '06_chord_progression_generator.yml', 'edm_density.yml', '09_groove.yml', '01_hello_world.yml', '19_look_ma_no_notes.yml', '03_mary_keychange.yml', '20_registers.yml', '08_tie.yml', '05_voice_leading.yml',
                # Written by Claude directly, not by make_demos.py.
                'uk_butler.yml', 'eats_cats.yml', 'aunt_clara.yml', 'come_on_down.yml', 'three_hour_tour.yml', 'meeting_the_eye.yml', 'tumbleweeds.yml', 'when_to_hold_em.yml', 'loud_complaint.yml', 'bad_pelican.yml', 'why_say_it_again.yml', 'gain_distance_pedestrian.yml', 'intersection_pact.yml', 'toccata_and_funk.yml', 'trooping_trolls.yml', 'not_so_simple.yml', 'got_some_strings.yml', 'south_florida_squad.yml', 'magic_colored_smoke.yml', 'beach_flick.yml', 'jungle_alarm_clock.yml', 'the_bucket.yml', 'three_chord_joy.yml', 'can_can_cant_stop.yml', 'lagos_fugue.yml', 'going_home_slow.yml', 'turkish_surf.yml', 'night_on_synth_mountain.yml', 'moonlight_feedback.yml', 'house_entertainer.yml', 'bop_invention.yml', 'chipped_jazz.yml', 'zap_swing_kapow.yml', 'tripped_went_to_hospital.yml', 'dangerous_to_go_alone.yml', 'in_another_castle.yml', 'roll_d20.yml', 'percussion_fish.yml', 'rick_rolling.yml', 'peanut_buttercup.yml', 'bless_the_rains.yml', 'goodnight_world.yml', 'spot_over_there.yml', 'know_your_slang.yml', 'green_men.yml', 'training_montage.yml', 'sax_reindeer.yml', 'spy_hunting.yml', 'phoenix_foundation.yml', 'forgot_your_name.yml', 'tropical_51.yml', 'not_painless.yml', 'mysterious_spooky.yml', 'strange_woodworking.yml', 'get_the_traps_egon.yml', 'sandworm.yml', 'aliens_counting.yml', 'angry_shark.yml', 'very_large_mammals.yml', 'four_wheels_g.yml', 'microwave_snacks.yml', 'nomore_nomore.yml', 'fang_removal.yml', 'not_werewolves.yml', 'annandale.yml', 'volcano.yml', 'incoming_message.yml', 'the_mineral.yml', 'not_star_trek.yml']
SOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, 'data', 'demo_sources')

# Names the tests give to their own things, and other values they use.
SILENT = 'SILENT'
MAKE_DEMOS = 'make_demos'
# The pages that describe the demos, one for each genre.
DEMO_PAGES = os.path.join('docs', 'demos')
DEMO_PAGE_FILES = '*.md'
NOTHING = ''
# Every set the generator writes, in whichever folder of its output.
WRITTEN_SETS = os.path.join('**', '*.yml')
PAD = 'pad'
BASS = 'bass'
VOICE = 'voice'
SILENT_MELODY = 'SILENT melody'


def names():
    return sorted(os.path.basename(path) for path in PATHS)


class TemporaryFolderTest(unittest.TestCase):
    """A test with an empty folder of its own, removed when it's done."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = temporary.name


class TestDemos(TemporaryFolderTest):

    def test_there_are_demos(self):
        self.assertGreaterEqual(len(PATHS), 10)

    def test_every_demo_has_a_title_a_description_of_what_it_plays_and_notes_on_what_it_shows(self):
        for path in PATHS:
            with open(path) as file:
                data = yaml.safe_load(file)
            with self.subTest(path=path):
                self.assertTrue(data.get(SetlistSetting.TITLE))
                self.assertTrue(data.get(SetlistSetting.DESCRIPTION))
                self.assertNotIn(drawing.LINE_BREAK, data.get(SetlistSetting.DESCRIPTION).strip())
                self.assertIn('When changing this demo:', data.get(SetlistSetting.NOTES, ''))

    def test_every_demo_is_described_on_a_genre_page_and_nothing_else_is(self):
        # Each demo has a section on its genre's page in docs/demos/, where its description lives.
        text = NOTHING.join(path.read_text() for path in sorted(pathlib.Path(DEMO_PAGES).glob(DEMO_PAGE_FILES)))
        for name in names():
            with self.subTest(name=name):
                self.assertIn(f'`{name}`', text)
        words = [os.path.basename(word.strip('`.,')) for word in text.split() if word.startswith('`')]
        mentioned = {word for word in words if is_demo(word)}
        self.assertEqual(mentioned - set(names()), set())

    def test_muted_tracks_and_only_those_are_named_silent(self):
        for path in PATHS:
            songs = set_file_data(path)[0][Section.SONGS]
            for song in songs.values():
                for name, settings in song[Section.TRACKS].items():
                    with self.subTest(path=path, track=name):
                        self.assertEqual(bool(settings.get(TrackSetting.MUTE)), SILENT in name)


def load_generator():
    """Import make_demos.py from tests/data/demo_sources, which isn't a package."""
    spec = importlib.util.spec_from_file_location(MAKE_DEMOS, os.path.join(SOURCES, 'make_demos.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def onsets(*, song, scene, track_name):
    """Return (start, MIDI number) for each note a track plays in a scene, in whole notes."""
    track = next(track for track in song.get_columns() if track.get_name() == track_name)
    clip = song.get_clip(row=scene, column=track)
    if clip is None:
        return []
    return [(Fraction(event[0]), event[2]) for event in timed_events(clip=clip, scale=clip.get_scale())[0]]


class TestDemoSources(unittest.TestCase):
    """The generator writes demos that build, and that play what its sources say."""

    @classmethod
    def setUpClass(cls):
        temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temporary.cleanup)
        cls.folder = temporary.name
        cls.generator = load_generator()
        cls.generator.main(output=cls.folder)

    def written(self):
        """Return each demo the generator wrote, by its file name, with where it went."""
        return {os.path.basename(path): path for path in glob.glob(os.path.join(self.folder, WRITTEN_SETS), recursive=True)}

    def made(self, name):
        return render_file(self.written()[name])

    def test_it_writes_every_demo_and_each_one_builds(self):
        written = sorted(self.written())
        self.assertEqual(sorted(written + HAND_WRITTEN), names())
        for name in written:
            with self.subTest(name=name):
                self.made(name)

    def test_the_entertainer_plays_the_notes_of_its_midi_file(self):
        song = self.made('entertainer.yml')
        played = collections.Counter()
        # The scenes are laid end to end, eight bars each but for the four-bar Intro and Bridge.
        for scene, start in zip(song.get_rows(), song.row_starts()):
            for track in song.get_columns():
                for time, number in onsets(song=song, scene=scene, track_name=track.get_name()):
                    played[(start + time, number)] += 1
        source = collections.Counter(
            (time, number) for hand in (1, 2) for time, number, _, _ in self.generator.entertainer_notes(hand)
        )
        self.assertEqual(sum((played - source).values()), 0)
        # A fourth note sounding at once in one hand has no voice to go to, and that happens 19 times.
        self.assertEqual(sum((source - played).values()), 19)

    def test_the_hocketing_voices_add_up_to_the_melody(self):
        song = self.made('17_hocket_shanty.yml')
        for scene in song.get_rows():
            voices = [track.get_name() for track in song.get_columns() if track.get_name().startswith(VOICE)]
            playing = [name for name in voices if onsets(song=song, scene=scene, track_name=name)]
            if len(playing) < len(voices):
                continue
            with self.subTest(scene=scene.get_name()):
                together = sorted(note for name in voices for note in onsets(song=song, scene=scene, track_name=name))
                self.assertEqual(together, sorted(onsets(song=song, scene=scene, track_name=SILENT_MELODY)))

    def test_the_arrangement_bass_plays_the_pad_roots_an_octave_down(self):
        song = self.made('18_arrangement_shanty.yml')
        scene = song.get_rows()[2]
        pad = onsets(song=song, scene=scene, track_name=PAD)
        roots = {time: min(number for start, number in pad if start == time) for time, _ in pad}
        for time, number in onsets(song=song, scene=scene, track_name=BASS):
            latest = max(start for start in roots if start <= time)
            self.assertEqual(number, roots[latest] - 12)


if __name__ == '__main__':
    unittest.main()
