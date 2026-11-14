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
"""The General MIDI export, the user's design of 2026-11-11: one MIDI file with drums on channel 10, every other track on a channel of its own, and each track's instrument's General MIDI sound sent first as a program change."""

import unittest

import mido

from llamatron.composition.file_format import ClipSlotSetting, InstrumentSetting, PatternSetting, Row, SceneSetting, Section, TrackSetting
from llamatron.composition.instrument import Instrument
from llamatron.composition.limits import MAX_GM_SOUND, MIN_GM_SOUND
from llamatron.composition.song_file_error import SongFileError
from llamatron.exporters.midi_arrangement import DRUM_CHANNEL_BYTE, MELODIC_CHANNEL_BYTES, MidiGeneralMidi
from llamatron.exporters.midi_messages import PROGRAM_CHANGE_MESSAGE
from llamatron.playback.song_renderer import SongRenderer
from rendering import song_from_data, setlist_from_data
from test_registers import pattern, song

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
    return [message.program for message in track if message.type == PROGRAM_CHANGE_MESSAGE]


class TestGeneralMidi(unittest.TestCase):

    def test_each_track_takes_its_instruments_sound_and_drums_play_on_channel_10(self):
        tracks = exported(data_with(tracks=[('lead', False, False, PIANO), ('drums', True, False, KIT)],
                                    instruments={PIANO: {InstrumentSetting.GM_SOUND: FLUTE}, KIT: {InstrumentSetting.GM_SOUND: MIN_GM_SOUND}}))
        self.assertEqual(programs(tracks[0]), [FLUTE - MIN_GM_SOUND])
        self.assertEqual(channels(tracks[0]), {MELODIC_CHANNEL_BYTES[0]})
        self.assertEqual(programs(tracks[1]), [], 'a drum track plays the kit channel 10 has, so it sends no program')
        self.assertEqual(channels(tracks[1]), {DRUM_CHANNEL_BYTE})

    def test_a_track_with_no_sound_sends_no_program(self):
        tracks = exported(data_with(tracks=[('lead', False, False, QUIET), ('pad', False, False, None)], instruments={QUIET: {}}))
        self.assertEqual([programs(track) for track in tracks], [[], []])
        self.assertEqual([channels(track) for track in tracks], [{MELODIC_CHANNEL_BYTES[0]}, {MELODIC_CHANNEL_BYTES[1]}])

    def test_a_muted_track_is_left_out_and_takes_no_channel(self):
        tracks = exported(data_with(tracks=[('ghost SILENT', False, True, None), ('lead', False, False, None)], instruments={}))
        self.assertEqual([track.name for track in tracks], ['lead'])
        self.assertEqual(channels(tracks[0]), {MELODIC_CHANNEL_BYTES[0]})

    def test_the_channels_go_round_again_after_the_fifteenth_melodic_track(self):
        many = [('track {number}'.format(number=number), False, False, None) for number in range(len(MELODIC_CHANNEL_BYTES) + 1)]
        tracks = exported(data_with(tracks=many, instruments={}))
        self.assertEqual(channels(tracks[-1]), {MELODIC_CHANNEL_BYTES[0]})
        self.assertNotIn({DRUM_CHANNEL_BYTE}, [channels(track) for track in tracks])

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
        for sound in (MIN_GM_SOUND - 1, MAX_GM_SOUND + 1):
            with self.subTest(sound=sound), self.assertRaises(SongFileError):
                setlist_from_data(data_with(tracks=[('lead', False, False, PIANO)], instruments={PIANO: {InstrumentSetting.GM_SOUND: sound}}))
