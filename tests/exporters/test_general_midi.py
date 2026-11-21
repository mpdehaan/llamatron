# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The General MIDI export: one MIDI file with drums on channel 10, every other track on a channel of its own, and each track's instrument's General MIDI sound sent first as a program change."""

import mido
import unittest

from llamatron.exporters import midi_arrangement, midi_messages
from llamatron.exporters.midi_arrangement import MidiGeneralMidi
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.objects.instrument import Instrument
from llamatron.model.schema import limits
from llamatron.model.schema.file_format import ClipSlotSetting, InstrumentSetting, PatternSetting, Row, SceneSetting, Section, TrackSetting
from llamatron.playback.song_renderer import SongRenderer
from tests.playback.test_registers import pattern, song
from tests.support.rendering import setlist_from_data, song_from_data

TUNE = 'tune'
BEAT = 'beat'
PIANO = 'piano'
KIT = 'kit'
QUIET = 'quiet'
FLUTE = 21
SNARE_NOTE = 'D'
DRUM_OCTAVE = 3
NAME = 'export'
NOTE_ON = 'note_on'


def data_with(*, tracks, instruments):
    """Return a song's data whose tracks, each (name, drum, muted, instrument), play a note each in one scene."""
    figure = pattern(1)
    drums = {PatternSetting.STEPS: 1, PatternSetting.DRUM: True, Row.DEGREE: [SNARE_NOTE], Row.OCTAVE: [DRUM_OCTAVE]}
    data = song(patterns={TUNE: figure, BEAT: drums}, scenes=[{SceneSetting.TRACKS: {
        name: {ClipSlotSetting.PATTERN: BEAT if drum else TUNE} for name, drum, _, _ in tracks}}], tracks=[name for name, _, _, _ in tracks])
    for name, drum, muted, instrument in tracks:
        settings = data[Section.TRACKS][name]
        if drum:
            settings[TrackSetting.DRUM] = True
        if muted:
            settings[TrackSetting.MUTE] = True
        if instrument:
            settings[TrackSetting.INSTRUMENT] = instrument
    data[Section.INSTRUMENTS] = instruments
    return data


def exported(data):
    """Return the General MIDI file a song's data exports, as mido reads it, without its tempo track."""
    grid = SongRenderer(song_from_data(data)).render()
    return MidiGeneralMidi(directory='.', grid=grid, name=NAME).midi_file().tracks[1:]


def channels(track):
    return {message.channel for message in track if message.type == NOTE_ON}


def programs(track):
    return [message.program for message in track if message.type == midi_messages.PROGRAM_CHANGE_MESSAGE]


class TestGeneralMidi(unittest.TestCase):

    def test_each_track_takes_its_instruments_sound_and_drums_play_on_channel_10(self):
        tracks = exported(data_with(tracks=[('lead', False, False, PIANO), ('drums', True, False, KIT)],
                                    instruments={PIANO: {InstrumentSetting.GM_SOUND: FLUTE}, KIT: {InstrumentSetting.GM_SOUND: limits.MIN_GM_SOUND}}))
        self.assertEqual(programs(tracks[0]), [FLUTE - limits.MIN_GM_SOUND])
        self.assertEqual(channels(tracks[0]), {midi_arrangement.MELODIC_CHANNEL_BYTES[0]})
        self.assertEqual(programs(tracks[1]), [], 'a drum track plays the kit channel 10 has, so it sends no program')
        self.assertEqual(channels(tracks[1]), {midi_arrangement.DRUM_CHANNEL_BYTE})

    def test_a_track_with_no_sound_sends_no_program(self):
        tracks = exported(data_with(tracks=[('lead', False, False, QUIET), ('pad', False, False, None)], instruments={QUIET: {}}))
        self.assertEqual([programs(track) for track in tracks], [[], []])
        self.assertEqual([channels(track) for track in tracks], [{midi_arrangement.MELODIC_CHANNEL_BYTES[0]}, {midi_arrangement.MELODIC_CHANNEL_BYTES[1]}])

    def test_a_muted_track_is_left_out_and_takes_no_channel(self):
        tracks = exported(data_with(tracks=[('ghost SILENT', False, True, None), ('lead', False, False, None)], instruments={}))
        self.assertEqual([track.name for track in tracks], ['lead'])
        self.assertEqual(channels(tracks[0]), {midi_arrangement.MELODIC_CHANNEL_BYTES[0]})

    def test_the_channels_go_round_again_after_the_fifteenth_melodic_track(self):
        many = [('track {number}'.format(number=number), False, False, None) for number in range(len(midi_arrangement.MELODIC_CHANNEL_BYTES) + 1)]
        tracks = exported(data_with(tracks=many, instruments={}))
        self.assertEqual(channels(tracks[-1]), {midi_arrangement.MELODIC_CHANNEL_BYTES[0]})
        self.assertNotIn({midi_arrangement.DRUM_CHANNEL_BYTE}, [channels(track) for track in tracks])

    def test_the_file_reads_back_as_a_multi_track_file(self):
        grid = SongRenderer(song_from_data(data_with(tracks=[('lead', False, False, None)], instruments={}))).render()
        self.assertIsInstance(MidiGeneralMidi(directory='.', grid=grid, name=NAME).midi_file(), mido.MidiFile)


class TestTheInstrumentsSound(unittest.TestCase):

    def test_it_is_written_and_read_back(self):
        instrument = Instrument(gm_sound=FLUTE)
        self.assertEqual(Instrument.from_data(data=instrument.to_data(), where=None).get_gm_sound(), FLUTE)
        self.assertEqual(instrument.copy().get_gm_sound(), FLUTE)

    def test_none_is_left_out_of_the_file(self):
        self.assertNotIn(InstrumentSetting.GM_SOUND, Instrument().to_data())

    def test_a_sound_past_either_end_is_refused(self):
        for sound in (limits.MIN_GM_SOUND - 1, limits.MAX_GM_SOUND + 1):
            with self.subTest(sound=sound), self.assertRaises(SongFileError):
                setlist_from_data(data_with(tracks=[('lead', False, False, PIANO)], instruments={PIANO: {InstrumentSetting.GM_SOUND: sound}}))
