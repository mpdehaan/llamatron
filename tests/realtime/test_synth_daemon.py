# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The native synth daemon (realtime/synth_process/daemon.py and native/synth/): where it is found, when it is used, and what
it renders offline, through the real daemon where it is built; nothing here opens the sound card.
"""

import multiprocessing
import numpy
import os
import tempfile
import unittest

from llamatron.exporters.built_in_wave import BuiltInTrack, read_wave
from llamatron.model.objects import engine_presets, sound_parts
from llamatron.model.objects.built_in_sound import ENVELOPE_PARTS, synth_spec
from llamatron.model.schema.file_format import FilterType, GateInput, GateMode, OscillatorType, PartSetting, SoundEngine, SoundPart, SoundSetting
from llamatron.realtime.synth_process import daemon, engine as engine_values
from llamatron.realtime.synth_process.daemon import offline_notes, render_offline
from llamatron.realtime.synth_process.load import LoadReport, SharedLoad

RATE = 44100
WAV = 'out.wav'
MIDDLE_C = 60
HARD = 110
SPAWN = 'spawn'
QUIETEST = 0.01
CEILING = 0.98
LFO_SHAPES = ('sine', 'triangle', 'saw_up', 'saw_down', 'square', 'sample_and_hold')
DRIVE_CURVES = ('soft', 'warm', 'hard', 'fold', 'wrap')
ENGINES = (SoundEngine.BASIC, SoundEngine.SID, SoundEngine.POCKET, SoundEngine.FISHLINE, SoundEngine.DRUM)
BUILT = daemon.daemon_path() is not None


def track_of(*, engine, notes):
    track = BuiltInTrack(spec=synth_spec({SoundSetting.ENGINE: engine}))
    track.notes = notes
    track.scene_starts = [0.0]
    return track


def sound_with(*, part, kind):
    """Return a stored Basic sound whose one part is of a type, its other parts the preset's."""
    sound = {SoundSetting.ENGINE: SoundEngine.BASIC}
    if part in ENVELOPE_PARTS:
        envelopes = [dict(engine_presets.preset_part(engine=SoundEngine.BASIC, part=each)) for each in ENVELOPE_PARTS]
        envelopes[ENVELOPE_PARTS.index(part)] = {PartSetting.TYPE: kind}
        sound[SoundSetting.ENVELOPES] = envelopes
    else:
        sound[part] = {PartSetting.TYPE: kind}
    return sound


def variants_as_tracks(variants):
    tracks = []
    for variant in variants:
        sound = {SoundSetting.ENGINE: SoundEngine.BASIC}
        sound.update(variant)
        track = BuiltInTrack(spec=synth_spec(sound))
        track.notes = [(0.0, MIDDLE_C, HARD), (0.5, MIDDLE_C, 0)]
        tracks.append(track)
    return tracks


def lfo_and_effect_tracks():
    """Return a Basic voice for each LFO shape, routed to the cutoff, and for each drive curve and the bitcrusher."""
    tracks = []
    for shape in LFO_SHAPES:
        spec = synth_spec({SoundSetting.ENGINE: SoundEngine.BASIC})
        spec['lfos'] = [{'shape': shape, 'rate': 5.0, 'retrigger': True, 'each_scene': False}]
        spec['matrix'] = [{'source': 'lfo1', 'via': 'none', 'destination': 'cutoff', 'amount': 0.5}]
        tracks.append(BuiltInTrack(spec=spec))
    for effect in [{'effect': 'drive', 'curve': curve, 'amount': 0.5, 'mix': 1.0} for curve in DRIVE_CURVES] + [{'effect': 'bitcrush', 'bits': 4, 'rate': 8000, 'mix': 1.0}]:
        spec = synth_spec({SoundSetting.ENGINE: SoundEngine.BASIC})
        spec['effects'] = [effect]
        tracks.append(BuiltInTrack(spec=spec))
    for track in tracks:
        track.notes = [(0.0, MIDDLE_C, HARD), (0.5, MIDDLE_C, 0)]
    return tracks


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


class TestSharedLoad(unittest.TestCase):

    def test_a_report_written_in_one_process_is_read_in_another_and_none_before_the_first(self):
        busy = 0.25
        voices = 7
        context = multiprocessing.get_context(SPAWN)
        shared = SharedLoad(context=context)
        self.assertIsNone(shared.read())
        child = context.Process(target=write_report, kwargs=dict(shared=shared, report={'load': busy, 'peak': busy, 'voices': voices, 'dropouts': 0, 'late_notes': 0}))
        child.start()
        child.join()
        self.assertEqual(shared.read(), LoadReport(load=busy, peak=busy, voices=voices, dropouts=0, late_notes=0))


def write_report(*, shared, report):
    shared.write(report)


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

    def test_every_type_of_every_part_sounds_and_stays_under_the_ceiling(self):
        # One of everything: each part's every type in a Basic voice, the rest of the voice the preset's.
        for part, types in sound_parts.TYPES.items():
            for kind in types:
                if kind == OscillatorType.DRUM:
                    continue
                with self.subTest(part=part, kind=kind):
                    track = BuiltInTrack(spec=synth_spec(sound_with(part=part, kind=kind)))
                    track.notes = [(0.0, MIDDLE_C, HARD), (0.5, MIDDLE_C, 0)]
                    samples = self.rendered(tracks=[track], seconds=1.5)
                    peak = float(numpy.max(numpy.abs(samples)))
                    self.assertTrue(numpy.all(numpy.isfinite(samples)))
                    self.assertGreater(peak, QUIETEST)
                    self.assertLessEqual(peak, CEILING)

    def test_every_gate_mode_and_input_and_every_lfo_shape_and_effect_sounds(self):
        variants = []
        for mode in (GateMode.VCA, GateMode.LOWPASS, GateMode.BOTH):
            for given in (GateInput.OSCILLATOR, GateInput.PING, GateInput.BOTH):
                variants.append({SoundPart.FILTER: {PartSetting.TYPE: FilterType.LOW_PASS_GATE, PartSetting.GATE_MODE: mode, PartSetting.INPUT: given}})
        for track in (variants_as_tracks(variants) + lfo_and_effect_tracks()):
            with self.subTest(spec=track.spec):
                samples = self.rendered(tracks=[track], seconds=1.5)
                self.assertTrue(numpy.all(numpy.isfinite(samples)))
                self.assertGreater(float(numpy.max(numpy.abs(samples))), QUIETEST)

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
