# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The native synth daemon (realtime/synth_process/daemon.py and native/synth/): where it is found, when it is used, and what
it renders offline, through the real daemon where it is built; nothing here opens the sound card.
"""

import numpy
import os
import tempfile
import unittest

from llamatron.exporters.built_in_wave import BuiltInTrack, read_wave
from llamatron.model.objects.built_in_sound import synth_spec
from llamatron.model.schema.file_format import SoundEngine, SoundSetting
from llamatron.realtime.synth_process import daemon, engine as engine_values
from llamatron.realtime.synth_process.daemon import offline_notes, render_offline

RATE = 44100
WAV = 'out.wav'
MIDDLE_C = 60
HARD = 110
ENGINES = (SoundEngine.BASIC, SoundEngine.SID, SoundEngine.POCKET, SoundEngine.FISHLINE, SoundEngine.DRUM)
BUILT = daemon.daemon_path() is not None


def track_of(*, engine, notes):
    track = BuiltInTrack(spec=synth_spec({SoundSetting.ENGINE: engine}))
    track.notes = notes
    track.scene_starts = [0.0]
    return track


class TestFindingTheDaemon(unittest.TestCase):

    def test_the_path_given_is_used_and_a_missing_one_is_none(self):
        with tempfile.NamedTemporaryFile() as program:
            self.assertEqual(daemon.daemon_path(environment={daemon.DAEMON_PATH: program.name}), program.name)
        self.assertIsNone(daemon.daemon_path(environment={daemon.DAEMON_PATH: program.name}))

    def test_the_python_engine_is_used_when_asked_for(self):
        with tempfile.NamedTemporaryFile() as program:
            given = {daemon.DAEMON_PATH: program.name}
            self.assertTrue(daemon.uses_daemon(environment=given))
            self.assertFalse(daemon.uses_daemon(environment={**given, daemon.PYTHON_SYNTH: daemon.SWITCHED_ON}))

    def test_a_track_becomes_the_daemons_notes_with_its_clip_starts_and_endings(self):
        track = track_of(engine=SoundEngine.BASIC, notes=[(0.5, MIDDLE_C, HARD), (1.0, MIDDLE_C, 0)])
        track.endings = [2.0]
        kinds = [note[1] for note in offline_notes(number=3, track=track)]
        self.assertEqual(kinds, [engine_values.SCENE_STARTED, engine_values.NOTE_ON, engine_values.NOTE_OFF, engine_values.ALL_OFF])


@unittest.skipUnless(BUILT, 'the synth daemon is not built')
class TestOfflineRender(unittest.TestCase):

    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.path = os.path.join(scratch.name, WAV)

    def rendered(self, *, tracks, seconds):
        render_offline(tracks=tracks, seconds=seconds, path=self.path, rate=RATE)
        rate, samples = read_wave(self.path)
        self.assertEqual(rate, RATE)
        return samples[:, 0]

    def test_every_engine_sounds_and_stays_under_the_ceiling(self):
        for engine in ENGINES:
            track = track_of(engine=engine, notes=[(0.0, MIDDLE_C, HARD), (0.4, MIDDLE_C, 0)])
            samples = self.rendered(tracks=[track], seconds=1.0)
            peak = float(numpy.max(numpy.abs(samples)))
            self.assertTrue(numpy.all(numpy.isfinite(samples)), engine)
            self.assertGreater(peak, 0.05, engine)
            self.assertLessEqual(peak, 0.98, engine)

    def test_a_note_begins_on_its_exact_sample(self):
        start = 0.25
        track = track_of(engine=SoundEngine.BASIC, notes=[(start, MIDDLE_C, HARD)])
        samples = self.rendered(tracks=[track], seconds=0.5)
        place = round(start * RATE)
        # A saw read from its phase of zero is exactly zero on its first sample, and sounds from the next.
        self.assertFalse(numpy.any(samples[:place]))
        self.assertTrue(numpy.all(samples[place + 1:place + 3]))

    def test_a_drum_renders_the_same_every_time(self):
        notes = [(0.0, MIDDLE_C, HARD), (0.25, MIDDLE_C + 2, HARD - 30)]
        drum = track_of(engine=SoundEngine.DRUM, notes=notes)
        once = self.rendered(tracks=[drum], seconds=0.5)
        again = self.rendered(tracks=[drum], seconds=0.5)
        self.assertTrue(numpy.array_equal(once, again))
