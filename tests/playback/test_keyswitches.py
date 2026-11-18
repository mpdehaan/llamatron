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
"""The Hocket: the tracks whose clips name it take turns at its source track's notes, one note each, left to right, the source playing its own pattern as ever."""
"""Keyswitches: an instrument's ten slots, a pattern's Keyswitch row, the notes a clip sends for them, and which exports carry them."""

import gzip
import tempfile
import unittest
import xml.etree.ElementTree as ET

from llamatron.composition import defaults, limits
from llamatron.composition.file_format import (
    FLUIDSYNTH_DEVICE, KEYSWITCH_SLOT_COUNT, KEYSWITCH_SLOTS, ClipSlotSetting, GeneratorKind, GrooveSetting, InstrumentSetting, KeyswitchSetting, PatternSetting,
    Row, SceneSetting, Section, SongSetting, TrackSetting,
)
from llamatron.composition.instrument import NO_KEYSWITCH, Instrument, Keyswitch
from llamatron.composition.invalid_value import InvalidValue
from llamatron.composition.pattern import Pattern
from llamatron.composition.song_file_error import SongFileError
from llamatron.exporters.ableton_project import AbletonProject
from llamatron.exporters.midi_arrangement import MidiGeneralMidi, MidiSong, MidiStems
from llamatron.exporters.midi_messages import NOTE_ON_MESSAGE
from llamatron.exporters.timing import keyswitch_events, timed_events
from llamatron.music import midi
from llamatron.playback.song_renderer import SongRenderer
from llamatron.realtime.score import Score
from llamatron.realtime.timeline import NOTE_ON, Route, song_timeline
from llamatron.support.rational import Rational
from tests.support.rendering import song_from_data
from tests.playback.test_registers import LEAD, pattern, song

TUNE = 'tune'
VIOLIN = 'violin'
PORT = 'a port'
SUSTAIN = 'sustain'
STACCATO = 'staccato'
SUSTAIN_SLOT = 0
STACCATO_SLOT = 1
UNMAPPED_SLOT = 2
SUSTAIN_NOTE = 24
STACCATO_NOTE = 25
# A keyswitch above the notes a tune plays, as some plugins place theirs.
HIGH_NOTE = 120
STEP = Rational(1, 4)
TEMPO = 120
LEAD_MILLISECONDS = 10
# Ten milliseconds at 120 quarter notes a minute, in whole notes: a whole note lasts two seconds.
LEAD_LENGTH = Rational(1, 200)
MILLISECONDS_PER_WHOLE_NOTE_AT_ONE_BEAT_A_MINUTE = 240_000
OCTAVE_UP = 12
ARP = 'up'
CHAIN = 'arpeggiated'
LATE = 'late'
LATE_PERCENT = 50
NAME = 'export'
A_DIRECTORY = '.'
WHERE = 'a test'
MIDI_KEY = 'MidiKey'
VALUE = 'Value'


def slots_written(**slots):
    """Return an instrument's keyswitches as a file holds them, from each slot's (name, note) by its number's name."""
    written = [None] * KEYSWITCH_SLOT_COUNT
    for slot, (name, note) in slots.items():
        written[int(slot.removeprefix('slot'))] = {KeyswitchSetting.NAME: name, KeyswitchSetting.NOTE: note}
    return written


def violin(*, lead=None, device=PORT, staccato=STACCATO_NOTE):
    """Return an instrument's data with sustain on slot 0 and staccato on slot 1, and nothing on the rest."""
    data = {InstrumentSetting.DEVICE: device, InstrumentSetting.KEYSWITCHES: slots_written(slot0=(SUSTAIN, SUSTAIN_NOTE), slot1=(STACCATO, staccato))}
    if lead is not None:
        data[InstrumentSetting.KEYSWITCH_LEAD] = lead
    return data


def switched(*, keyswitch, rows=None, repeat=1, instrument=None, track=None, clip=None, extra=None):
    """Return a song's data whose lead plays one pattern with a Keyswitch row, a step a quarter note, through the violin unless told otherwise."""
    steps = len(keyswitch)
    figure = pattern(steps, **{Row.KEYSWITCH: keyswitch, **(rows or {})})
    data = song(patterns={TUNE: figure}, scenes=[{SceneSetting.TRACKS: {LEAD: {ClipSlotSetting.PATTERN: TUNE, ClipSlotSetting.REPEAT: repeat, **(clip or {})}}}])
    data[SongSetting.TEMPO] = TEMPO
    data[Section.INSTRUMENTS] = {VIOLIN: violin() if instrument is None else instrument}
    data[Section.TRACKS][LEAD] = {TrackSetting.INSTRUMENT: VIOLIN, **(track or {})}
    data.update(extra or {})
    return data


def rendered(data):
    grid = SongRenderer(song_from_data(data)).render()
    row = grid.get_rows()[0]
    column = grid.get_columns()[0]
    return grid, grid.get_clip(row=row, column=column), grid.scale_at(row=row, column=column)


def sent(data):
    """Return the keyswitch notes a song's one clip sends, each (start, end, MIDI number), in time order."""
    _, clip, scale = rendered(data)
    _, length = timed_events(clip=clip, scale=scale)
    return [(event.start, event.end, event.midi_number) for event in keyswitch_events(clip=clip, clip_length=length)]


def notes_on(track):
    """Return a MIDI track's note ons, each (tick, note), in the order the file holds them."""
    now = 0
    found = []
    for message in track:
        now += message.time
        if message.type == NOTE_ON_MESSAGE:
            found.append((now, message.note))
    return found


class TestInstrumentKeyswitches(unittest.TestCase):

    def test_a_new_instrument_has_ten_empty_slots_and_writes_none(self):
        instrument = Instrument()
        self.assertEqual(instrument.get_keyswitches(), [NO_KEYSWITCH] * KEYSWITCH_SLOT_COUNT)
        self.assertFalse(instrument.has_keyswitches())
        self.assertNotIn(InstrumentSetting.KEYSWITCHES, instrument.to_data())

    def test_a_slot_keeps_its_name_and_note_through_a_file(self):
        instrument = Instrument()
        instrument.set_keyswitch(slot=STACCATO_SLOT, name=STACCATO, note=STACCATO_NOTE)
        again = Instrument.from_data(data=instrument.to_data(), where=WHERE)
        self.assertEqual(again.get_keyswitch(STACCATO_SLOT), Keyswitch(STACCATO, STACCATO_NOTE))
        self.assertEqual(again.get_keyswitch_notes(), {STACCATO_SLOT: STACCATO_NOTE})
        self.assertEqual(again.to_data(), instrument.to_data())

    def test_a_slot_may_have_a_name_and_no_note_or_a_note_and_no_name(self):
        instrument = Instrument()
        instrument.set_keyswitch(slot=SUSTAIN_SLOT, name=SUSTAIN)
        instrument.set_keyswitch(slot=STACCATO_SLOT, note=STACCATO_NOTE)
        self.assertEqual(instrument.get_keyswitch(SUSTAIN_SLOT), Keyswitch(SUSTAIN, None))
        self.assertEqual(instrument.get_keyswitch_notes(), {STACCATO_SLOT: STACCATO_NOTE})

    def test_emptying_the_last_slot_writes_no_keyswitches(self):
        instrument = Instrument()
        instrument.set_keyswitch(slot=SUSTAIN_SLOT, name=SUSTAIN, note=SUSTAIN_NOTE)
        instrument.set_keyswitch(slot=SUSTAIN_SLOT)
        self.assertEqual(instrument.to_data(), {})

    def test_a_copy_shares_nothing_with_the_instrument(self):
        instrument = Instrument.from_data(data=violin(lead=LEAD_MILLISECONDS), where=WHERE)
        copy = instrument.copy()
        copy.set_keyswitch(slot=SUSTAIN_SLOT)
        self.assertEqual(instrument.get_keyswitch(SUSTAIN_SLOT), Keyswitch(SUSTAIN, SUSTAIN_NOTE))
        self.assertEqual(copy.get_keyswitch_lead(), LEAD_MILLISECONDS)

    def test_what_a_slot_refuses(self):
        instrument = Instrument()
        for arguments in ({'slot': KEYSWITCH_SLOT_COUNT}, {'slot': SUSTAIN_SLOT, 'note': midi.MAX_MIDI_NUMBER + 1}, {'slot': SUSTAIN_SLOT, 'name': 'x' * (limits.MAX_NAME_LENGTH + 1)},
                          {'slot': SUSTAIN_SLOT, 'name': ''}, {'slot': SUSTAIN_SLOT, 'note': str(SUSTAIN_NOTE)}):
            with self.subTest(arguments=arguments), self.assertRaises(InvalidValue):
                instrument.set_keyswitch(**arguments)

    def test_what_a_file_refuses_of_keyswitches(self):
        for keyswitches in ([None], {}, [{}] * KEYSWITCH_SLOT_COUNT, slots_written(slot0=(SUSTAIN, midi.MAX_MIDI_NUMBER + 1)), [{'key': SUSTAIN}, *[None] * (KEYSWITCH_SLOT_COUNT - 1)]):
            with self.subTest(keyswitches=keyswitches), self.assertRaises((InvalidValue, SongFileError)):
                Instrument.from_data(data={InstrumentSetting.KEYSWITCHES: keyswitches}, where=WHERE)

    def test_the_lead_is_nothing_unless_set_and_held_to_its_limits(self):
        instrument = Instrument()
        self.assertEqual(instrument.get_keyswitch_lead(), 0)
        instrument.set_keyswitch_lead(LEAD_MILLISECONDS)
        self.assertEqual(instrument.to_data(), {InstrumentSetting.KEYSWITCH_LEAD: LEAD_MILLISECONDS})
        with self.assertRaises(InvalidValue):
            instrument.set_keyswitch_lead(limits.MAX_KEYSWITCH_LEAD + 1)


class TestKeyswitchRow(unittest.TestCase):

    def pattern(self, **rows):
        return Pattern.from_data(data=pattern(2, **rows), where=WHERE)

    def test_a_step_holds_its_slots_lowest_first_and_a_file_writes_a_list(self):
        made = self.pattern(**{Row.KEYSWITCH: [[STACCATO_SLOT, SUSTAIN_SLOT], None]})
        self.assertEqual(made.get_value(row=Row.KEYSWITCH, step=0), (SUSTAIN_SLOT, STACCATO_SLOT))
        self.assertIsNone(made.get_value(row=Row.KEYSWITCH, step=1))
        self.assertEqual(made.to_data()[Row.KEYSWITCH], [[SUSTAIN_SLOT, STACCATO_SLOT], None])
        self.assertTrue(made.sends_keyswitches())

    def test_a_pattern_with_no_keyswitch_writes_no_row(self):
        made = self.pattern()
        self.assertFalse(made.sends_keyswitches())
        self.assertNotIn(Row.KEYSWITCH, made.to_data())

    def test_every_slot_can_be_set_and_cleared(self):
        made = self.pattern()
        made.set_value(row=Row.KEYSWITCH, step=0, value=list(KEYSWITCH_SLOTS))
        self.assertEqual(made.get_value(row=Row.KEYSWITCH, step=0), KEYSWITCH_SLOTS)
        made.set_value(row=Row.KEYSWITCH, step=0, value=None)
        self.assertFalse(made.sends_keyswitches())

    def test_a_drum_pattern_takes_keyswitches(self):
        data = pattern(1, **{Row.KEYSWITCH: [[SUSTAIN_SLOT]]})
        data.update({PatternSetting.DRUM: True, Row.DEGREE: ['C']})
        self.assertTrue(Pattern.from_data(data=data, where=WHERE).sends_keyswitches())

    def test_what_a_step_refuses(self):
        made = self.pattern()
        for value in ([KEYSWITCH_SLOT_COUNT], [SUSTAIN_SLOT, SUSTAIN_SLOT], SUSTAIN_SLOT, [], [str(SUSTAIN_SLOT)], [True]):
            with self.subTest(value=value), self.assertRaises(InvalidValue):
                made.set_value(row=Row.KEYSWITCH, step=0, value=value)


class TestKeyswitchesPlayed(unittest.TestCase):

    def test_a_steps_slots_send_their_notes_for_as_long_as_the_note_is_written(self):
        self.assertEqual(sent(switched(keyswitch=[[SUSTAIN_SLOT], None, [SUSTAIN_SLOT, STACCATO_SLOT], None])), [
            (0 * STEP, 1 * STEP, SUSTAIN_NOTE), (2 * STEP, 3 * STEP, SUSTAIN_NOTE), (2 * STEP, 3 * STEP, STACCATO_NOTE),
        ])

    def test_a_gate_longer_than_a_step_holds_the_keyswitch_as_long(self):
        data = switched(keyswitch=[[STACCATO_SLOT], None, None, None], rows={Row.GATE: ['1/2', None, None, None], Row.DEGREE: [1, None, None, None]})
        self.assertEqual(sent(data), [(0 * STEP, 2 * STEP, STACCATO_NOTE)])

    def test_a_tie_holds_the_keyswitch_with_its_note(self):
        data = switched(keyswitch=[[STACCATO_SLOT], None, None, None], rows={Row.TIE: [False, True, True, False], Row.DEGREE: [1, None, None, 1]})
        self.assertEqual(sent(data), [(0 * STEP, 3 * STEP, STACCATO_NOTE)])

    def test_a_tie_at_the_start_of_the_next_pass_holds_the_keyswitch_on(self):
        data = switched(keyswitch=[None, [STACCATO_SLOT]], rows={Row.TIE: [True, False], Row.DEGREE: [None, 1]}, repeat=2)
        self.assertEqual(sent(data), [(1 * STEP, 3 * STEP, STACCATO_NOTE), (3 * STEP, 4 * STEP, STACCATO_NOTE)])

    def test_a_step_with_no_note_sends_none(self):
        data = switched(keyswitch=[[STACCATO_SLOT], [STACCATO_SLOT]], rows={Row.DEGREE: [None, 1]})
        self.assertEqual(sent(data), [(1 * STEP, 2 * STEP, STACCATO_NOTE)])

    def test_each_repeat_sends_them_again(self):
        self.assertEqual(sent(switched(keyswitch=[[SUSTAIN_SLOT]], repeat=3)), [(place * STEP, (place + 1) * STEP, SUSTAIN_NOTE) for place in range(3)])

    def test_a_slot_with_no_note_in_the_map_sends_nothing(self):
        self.assertEqual(sent(switched(keyswitch=[[UNMAPPED_SLOT, STACCATO_SLOT]])), [(0 * STEP, 1 * STEP, STACCATO_NOTE)])

    def test_a_track_with_no_instrument_sends_none(self):
        data = switched(keyswitch=[[SUSTAIN_SLOT]])
        del data[Section.TRACKS][LEAD][TrackSetting.INSTRUMENT]
        self.assertEqual(sent(data), [])

    def test_an_instrument_through_fluidsynth_sends_none(self):
        self.assertEqual(sent(switched(keyswitch=[[SUSTAIN_SLOT]], instrument=violin(device=FLUIDSYNTH_DEVICE))), [])

    def test_the_tracks_transpose_leaves_a_keyswitch_where_the_map_wrote_it(self):
        plain = rendered(switched(keyswitch=[[SUSTAIN_SLOT]]))
        moved = rendered(switched(keyswitch=[[SUSTAIN_SLOT]], track={TrackSetting.TRANSPOSE: OCTAVE_UP}))
        self.assertEqual(sent(switched(keyswitch=[[SUSTAIN_SLOT]], track={TrackSetting.TRANSPOSE: OCTAVE_UP})), [(0 * STEP, 1 * STEP, SUSTAIN_NOTE)])
        self.assertNotEqual(self.pitches(plain), self.pitches(moved))

    def pitches(self, render):
        _, clip, scale = render
        return [event.midi_number for event in timed_events(clip=clip, scale=scale)[0]]

    def test_a_generator_changes_the_notes_and_leaves_the_keyswitches(self):
        chained = {Section.ARPS: {ARP: {}}, Section.CHAINS: {CHAIN: [{GeneratorKind.ARP: ARP}]}}
        rows = {Row.CHORD: ['M', None], Row.DEGREE: [1, None]}
        plain = switched(keyswitch=[[STACCATO_SLOT], None], rows=rows)
        arpeggiated = switched(keyswitch=[[STACCATO_SLOT], None], rows=rows, clip={ClipSlotSetting.CHAINS: [CHAIN]}, extra=chained)
        self.assertNotEqual(timed_events(clip=rendered(plain)[1], scale=rendered(plain)[2])[0], timed_events(clip=rendered(arpeggiated)[1], scale=rendered(arpeggiated)[2])[0])
        self.assertEqual(sent(arpeggiated), sent(plain))
        self.assertEqual(sent(plain), [(0 * STEP, 1 * STEP, STACCATO_NOTE)])

    def test_a_groove_moves_a_keyswitch_with_its_note(self):
        grooved = {Section.GROOVES: {LATE: {GrooveSetting.CELLS: [0, LATE_PERCENT], GrooveSetting.CELL_LENGTH: '1/4'}}}
        data = switched(keyswitch=[[SUSTAIN_SLOT], [STACCATO_SLOT]], track={TrackSetting.GROOVE: LATE}, extra=grooved)
        _, clip, scale = rendered(data)
        starts = [event.start for event in timed_events(clip=clip, scale=scale)[0]]
        self.assertGreater(starts[1], 1 * STEP)
        self.assertEqual([start for start, _, _ in sent(data)], starts)

    def test_every_keyswitch_has_the_one_velocity(self):
        _, clip, scale = rendered(switched(keyswitch=[[SUSTAIN_SLOT]], rows={Row.VELOCITY: [1]}))
        _, length = timed_events(clip=clip, scale=scale)
        self.assertEqual([event.velocity for event in keyswitch_events(clip=clip, clip_length=length)], [defaults.KEYSWITCH_VELOCITY])

    def test_a_lead_sends_each_keyswitch_early_but_never_before_the_clip(self):
        self.assertEqual(LEAD_LENGTH, Rational(LEAD_MILLISECONDS * TEMPO, MILLISECONDS_PER_WHOLE_NOTE_AT_ONE_BEAT_A_MINUTE))
        data = switched(keyswitch=[[SUSTAIN_SLOT], [STACCATO_SLOT]], instrument=violin(lead=LEAD_MILLISECONDS))
        self.assertEqual(sent(data), [(0 * STEP, 1 * STEP, SUSTAIN_NOTE), (1 * STEP - LEAD_LENGTH, 2 * STEP, STACCATO_NOTE)])

    def test_a_lead_cuts_a_keyswitch_where_the_same_one_starts_again(self):
        data = switched(keyswitch=[[SUSTAIN_SLOT], [SUSTAIN_SLOT]], instrument=violin(lead=LEAD_MILLISECONDS))
        self.assertEqual(sent(data), [(0 * STEP, 1 * STEP - LEAD_LENGTH, SUSTAIN_NOTE), (1 * STEP - LEAD_LENGTH, 2 * STEP, SUSTAIN_NOTE)])

    def test_a_clips_music_never_holds_a_keyswitch(self):
        _, clip, scale = rendered(switched(keyswitch=[[SUSTAIN_SLOT, STACCATO_SLOT]]))
        self.assertEqual(len(timed_events(clip=clip, scale=scale)[0]), 1)


class TestKeyswitchesExported(unittest.TestCase):

    def grid(self, *, staccato=STACCATO_NOTE):
        return rendered(switched(keyswitch=[[STACCATO_SLOT], None], instrument=violin(staccato=staccato)))[0]

    def test_the_midi_file_sends_a_keyswitch_before_its_note_even_from_above_it(self):
        for staccato in (STACCATO_NOTE, HIGH_NOTE):
            with self.subTest(staccato=staccato):
                track = MidiSong(directory=A_DIRECTORY, grid=self.grid(staccato=staccato), name=NAME).midi_file().tracks[1]
                first, second = notes_on(track)[:2]
                self.assertEqual(first, (0, staccato))
                self.assertEqual(second[0], 0)

    def test_the_stems_carry_keyswitches(self):
        grid = self.grid()
        stems = MidiStems(directory=A_DIRECTORY, grid=grid, name=NAME)
        self.assertIn(STACCATO_NOTE, [note for _, note in notes_on(stems.midi_file(grid.get_columns()[0]).tracks[-1])])

    def test_the_general_midi_file_leaves_keyswitches_out(self):
        tracks = MidiGeneralMidi(directory=A_DIRECTORY, grid=self.grid(), name=NAME).midi_file().tracks[1:]
        self.assertNotIn(STACCATO_NOTE, [note for track in tracks for _, note in notes_on(track)])

    def test_the_live_set_holds_a_keyswitch_in_its_clip(self):
        with tempfile.TemporaryDirectory() as directory:
            project = AbletonProject(directory=directory, grid=self.grid(), name=NAME)
            project.export()
            with gzip.open(project.path()) as file:
                root = ET.fromstring(file.read())
        self.assertIn(str(STACCATO_NOTE), [key.get(VALUE) for key in root.iter(MIDI_KEY)])


class TestKeyswitchesInRealTime(unittest.TestCase):

    def timeline(self, route):
        grid = rendered(switched(keyswitch=[[STACCATO_SLOT], None]))[0]
        return song_timeline(grid=grid, routes={LEAD: route})

    def test_a_midi_port_is_sent_the_keyswitch_before_its_note(self):
        ons = [event for event in self.timeline(Route(PORT, 0)) if event.kind == NOTE_ON]
        self.assertEqual((ons[0].number, ons[0].switch, ons[0].value), (STACCATO_NOTE, True, defaults.KEYSWITCH_VELOCITY))
        self.assertFalse(ons[1].switch)
        self.assertEqual(ons[0].whole, ons[1].whole)

    def test_fluidsynth_is_sent_none(self):
        self.assertFalse([event for event in self.timeline(Route(PORT, 0, None, keyswitches=False)) if event.switch])

    def test_the_lights_and_the_visualizers_pass_a_keyswitch_by(self):
        events = self.timeline(Route(PORT, 0))
        self.assertEqual(len(Score._heard_notes(events)), len([event for event in events if event.kind == NOTE_ON and not event.switch]))
        self.assertEqual(len(Score._note_spans(events)), len(Score._heard_notes(events)))


if __name__ == '__main__':
    unittest.main()
