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
"""The MIDI import: what it reads, how it splits a file into voices, scenes and patterns, how it names them, and that what it makes plays as the file does.

The proof is the round trip: a MIDI file imported into a new set, played and exported again,
plays the same notes at the same tempos as the file, for every file in examples/midi/ and for
every example set exported as MIDI, or the import says what it had to change
(internal_tools/import_check.py prints the same as a report). The smaller tests build MIDI files of
their own in memory, so nothing is written.
"""

import glob
import os
import unittest

import mido

from llamatron.composition.file_format import ACCIDENTALS, ChordSymbol, ClipSlotSetting, PatternSetting, ScaleSetting, SceneSetting, Section, SongSetting, TrackSetting
from llamatron.composition.named_scale import NamedScale, scale_type_name
from llamatron.composition.naming import default_scale_name
from llamatron.composition.setlist import Setlist
from llamatron.exporters.midi_arrangement import MidiSong
from llamatron.importers.comparison import round_trip
from llamatron.importers.keys import Key, degree_of, key_of_notes, key_of_signature
from llamatron.importers.midi_import import ImportChoices, MidiImport, MidiImportProblem
from llamatron.importers.midi_reading import HeardNote, MidiPart, read_midi
from llamatron.importers.cutting import CONTROL_TOLERANCE
from llamatron.importers.voices import MOD_WHEEL, SUSTAIN, VOLUME, voices_of
from llamatron.importers.writing import add_imported
from llamatron.music.scale import ScaleType
from llamatron.playback.song_renderer import SongRenderer
from llamatron.strings.errors import ERR_MIDI_NO_NOTES
from llamatron.strings.importing import (
    MSG_DRUM_NAMES, MSG_UNNAMED_DRUM, MSG_WARN_CONTROLS_LEFT_OUT, MSG_WARN_CONTROLS_MOVED, MSG_WARN_CONTROLS_OFF, MSG_WARN_SWUNG, MSG_WARN_TEMPOS_MOVED,
)
from llamatron.support.rational import Rational
from llamatron.support.example_sets import BY_GENRE, OTHER, LEARNING, SET_FOLDERS, example_sets, folder_of_example

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_MIDI_FILES = os.path.join(ROOT, 'examples', 'midi', '*.mid')
# The longest example, nine minutes of stage themes, whose round trip alone takes about a minute.
LONGEST_EXAMPLE = 'incoming_message.yml'
CC_SWEEPS = os.path.join(ROOT, 'test', 'sample_sets', 'cc_sweeps.yml')
EXPRESSION = 11
REVERB = 91
FILTER = 74
# A recorded sweep sends a value every this many ticks, which falls on no step.
RECORDED_TICKS = 37
# How many ticks the recorded sweep takes to rise by one, so that it rises from 0 to 127 over a bar.
RECORDED_RISE = 15
COUNT_FIELD = '{count}'
SEED = 1
# The MIDI files these tests build count a quarter note as this many ticks, and a sixteenth as a quarter of it.
TICKS_PER_BEAT = 480
SIXTEENTH = TICKS_PER_BEAT // 4
SIXTEENTHS_IN_A_BAR = 16
VELOCITY = 100
DRUM_CHANNEL = 9
KICK = 36
SNARE = 38
UNNAMED_DRUM_NOTE = 20
MIDDLE_C = 60
C_MAJOR_TRIAD = (60, 64, 67)
C_MAJOR_SCALE = (60, 62, 64, 65, 67, 69, 71)
B_FLAT = 70
LOWEST_PITCH = 12
HIGHEST_PITCH = 127
QUARTER = Rational(1, 4)
SIXTEENTH_NOTE = Rational(1, 16)
SIXTEENTHS_IN_A_WHOLE_NOTE = 16
TEMPO = 120
FASTER = 150
LONGEST = 8
NO_HALF_STEPS = 0
# mido's names for the messages and meta messages these tests write.
NOTE_ON = 'note_on'
NOTE_OFF = 'note_off'
CONTROL_CHANGE = 'control_change'
SET_TEMPO = 'set_tempo'
KEY_SIGNATURE = 'key_signature'
TRACK_NAME = 'track_name'
WHERE = 'the test'
C_MAJOR = default_scale_name(root='C', kind=scale_type_name(ScaleType.MAJOR))
F_MAJOR = default_scale_name(root='F', kind=scale_type_name(ScaleType.MAJOR))


def midi_of(*, tracks, tempos=((0, TEMPO),), keys=()):
    """Return a mido file of type 1 holding tracks, each a name, a channel, notes as (start, length, MIDI number) in sixteenths and, if given, CC messages as (tick, CC number, value), with tempo changes and key signatures as (sixteenth, value)."""
    conductor = [(at * SIXTEENTH, mido.MetaMessage(SET_TEMPO, tempo=mido.bpm2tempo(bpm))) for at, bpm in tempos]
    conductor += [(at * SIXTEENTH, mido.MetaMessage(KEY_SIGNATURE, key=key)) for at, key in keys]
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    midi.tracks.append(track_of(timed=conductor))
    for name, channel, notes, *controls in tracks:
        timed = [(0, mido.MetaMessage(TRACK_NAME, name=name))]
        timed += [(tick, mido.Message(CONTROL_CHANGE, channel=channel, control=number, value=value)) for tick, number, value in (controls[0] if controls else [])]
        for start, length, pitch in notes:
            timed.append(((start + length) * SIXTEENTH, mido.Message(NOTE_OFF, channel=channel, note=pitch)))
            timed.append((start * SIXTEENTH, mido.Message(NOTE_ON, channel=channel, note=pitch, velocity=VELOCITY)))
        midi.tracks.append(track_of(timed=timed))
    return midi


def track_of(*, timed):
    """Return a mido track of messages at ticks, in time order, note offs before note ons at one tick, each message's time the gap before it."""
    track = mido.MidiTrack()
    now = 0
    for tick, message in sorted(timed, key=lambda pair: (pair[0], pair[1].type != NOTE_OFF)):
        track.append(message.copy(time=tick - now))
        now = tick
    return track


def melody(*, pitches, length=4, start=0):
    """Return notes one after another, each length sixteenths long, from a start."""
    return [(start + place * length, length, pitch) for place, pitch in enumerate(pitches)]


def imported_into(*, setlist, midi, **choices):
    """Return what importing a mido file into a set makes, with the choices given, and the song once added."""
    imported = MidiImport(midi_file=midi).imported(setlist=setlist, choices=ImportChoices(song_name='tune', **choices))
    return imported, add_imported(setlist=setlist, imported=imported.song)


def exported(path):
    """Return an example set's first song as one MIDI file in memory, with a fixed seed."""
    setlist = Setlist.read_file(path)
    name = setlist.first_song_name()
    return MidiSong(directory=os.curdir, grid=SongRenderer(setlist.get_song(name), seed=SEED).render(), name=name).midi_file()


class TestRoundTripOfTheSampleFiles(unittest.TestCase):
    """Anything imported plays back as the file plays it, or the import says what changed: each kind of file a class of its own, so that they run side by side."""

    def test_every_sample_midi_file_plays_back_the_same(self):
        paths = sorted(glob.glob(SAMPLE_MIDI_FILES))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(path=path):
                trip = round_trip(midi_file=mido.MidiFile(path), choices=ImportChoices(song_name=os.path.basename(path)))
                self.assertTrue(trip.comparison.is_same(), trip.comparison)


def check_round_trips(*, test, paths):
    """Check that every example set at the paths, exported as MIDI and imported, plays back the same or the import says why."""
    for path in paths:
        with test.subTest(path=path):
            trip = round_trip(midi_file=exported(path), choices=ImportChoices(song_name=os.path.basename(path)))
            test.assertTrue(trip.comparison.is_same() or trip.imported.warnings)


def examples_in(folder):
    """Return the example sets of one folder of examples/, leaving out the longest, which has a class of its own, since it alone takes about a minute."""
    return [path for path in example_sets(root=ROOT) if folder_of_example(path) == folder and os.path.basename(path) != LONGEST_EXAMPLE]


# The round trip of every example, one class for each folder of examples/, so that the classes run side by side within the suite's time for a class.
class TestRoundTripOfTheShowcase(unittest.TestCase):

    def test_every_learning_demo_plays_back_the_same_or_the_import_says_why(self):
        check_round_trips(test=self, paths=examples_in(LEARNING))


class TestRoundTripOfTheAdvancedDemos(unittest.TestCase):

    def test_every_other_demo_plays_back_the_same_or_the_import_says_why(self):
        check_round_trips(test=self, paths=examples_in(OTHER))


class TestRoundTripOfTheHomages(unittest.TestCase):

    def test_every_homage_plays_back_the_same_or_the_import_says_why(self):
        check_round_trips(test=self, paths=examples_in(BY_GENRE))


class TestRoundTripOfTheLongestExample(unittest.TestCase):

    def test_the_longest_example_plays_back_the_same_or_the_import_says_why(self):
        check_round_trips(test=self, paths=[path for path in example_sets(root=ROOT) if os.path.basename(path) == LONGEST_EXAMPLE])

    def test_every_example_is_in_one_round_trip_class(self):
        checked = [path for folder in SET_FOLDERS for path in examples_in(folder)] + [path for path in example_sets(root=ROOT) if os.path.basename(path) == LONGEST_EXAMPLE]
        self.assertEqual(sorted(checked), sorted(example_sets(root=ROOT)))


class TestRoundTripWithALongerLongestPattern(unittest.TestCase):

    def test_a_longer_longest_pattern_makes_fewer_scenes_and_still_plays_the_same(self):
        midi = mido.MidiFile(sorted(glob.glob(SAMPLE_MIDI_FILES))[0])
        short = round_trip(midi_file=midi, choices=ImportChoices(song_name='short', longest_pattern=LONGEST))
        long = round_trip(midi_file=midi, choices=ImportChoices(song_name='long'))
        self.assertTrue(short.comparison.is_same() and long.comparison.is_same())
        self.assertGreater(short.imported.scenes, long.imported.scenes)


class TestMidiReading(unittest.TestCase):

    def test_each_channel_of_a_track_is_a_part_named_after_the_track(self):
        midi = midi_of(tracks=[('piano:', 0, melody(pitches=[MIDDLE_C]))])
        midi.tracks[1].insert(1, mido.Message(NOTE_ON, channel=1, note=MIDDLE_C, velocity=VELOCITY))
        midi.tracks[1].insert(2, mido.Message(NOTE_ON, channel=1, note=MIDDLE_C, velocity=0, time=SIXTEENTH))
        parts = read_midi(midi).parts
        self.assertEqual([(part.name, part.channel) for part in parts], [('piano', 0), ('piano', 1)])

    def test_a_note_never_ended_lasts_to_the_end_of_its_track_and_is_counted(self):
        midi = midi_of(tracks=[('lead', 0, melody(pitches=[MIDDLE_C]))])
        midi.tracks[1].insert(1, mido.Message(NOTE_ON, note=MIDDLE_C + 2, velocity=VELOCITY))
        contents = read_midi(midi)
        self.assertEqual(contents.unended, 1)
        self.assertEqual(contents.note_count(), 2)

    def test_a_file_with_no_notes_is_refused(self):
        with self.assertRaises(MidiImportProblem) as raised:
            MidiImport(midi_file=midi_of(tracks=[]))
        self.assertEqual(str(raised.exception), ERR_MIDI_NO_NOTES)


class TestKeys(unittest.TestCase):

    def test_every_note_written_as_a_degree_plays_its_own_pitch(self):
        for key in (key_of_signature('C'), key_of_signature('F'), key_of_signature('Bbm'), key_of_signature('F#m'), key_of_signature('B')):
            scale = NamedScale.from_data(data={ScaleSetting.ROOT: key.root, ScaleSetting.TYPE: key.kind}, where=WHERE)
            for pitch in range(LOWEST_PITCH, HIGHEST_PITCH + 1):
                written = degree_of(pitch=pitch, key=key)
                if written is None:
                    continue
                degree, accidental, octave = written
                half_steps = ACCIDENTALS.get(accidental, NO_HALF_STEPS)
                with self.subTest(key=key, pitch=pitch):
                    note = scale.scale_at(octave).note_at(degree=degree, scale_notes=0, half_steps=half_steps, length=QUARTER)
                    self.assertEqual(note.get_midi_number(), pitch)

    def test_a_key_signature_is_a_major_or_minor_scale_with_a_root_a_scale_can_have(self):
        self.assertEqual(key_of_signature('Bbm'), Key(root='Bb', kind=scale_type_name(ScaleType.MINOR), flats=True))
        self.assertEqual(key_of_signature('Cb').root, 'B')
        self.assertTrue(key_of_signature('F').flats)
        self.assertFalse(key_of_signature('G').flats)

    def test_a_file_with_no_key_signature_is_in_the_key_its_notes_are_in(self):
        notes = [HeardNote(Rational(place), Rational(place + 1), pitch, VELOCITY) for place, pitch in enumerate(C_MAJOR_SCALE + (MIDDLE_C, 67))]
        self.assertEqual(key_of_notes(notes), Key(root='C', kind=scale_type_name(ScaleType.MAJOR), flats=False))


class TestVoices(unittest.TestCase):

    def part(self, *, notes, channel=0):
        return MidiPart(name='keys', channel=channel, controls=[], notes=sorted(HeardNote(Rational(start, SIXTEENTHS_IN_A_WHOLE_NOTE), Rational(start + length, SIXTEENTHS_IN_A_WHOLE_NOTE), pitch, VELOCITY) for start, length, pitch in notes))

    def test_drums_are_a_voice_for_each_sound_named_by_general_midi(self):
        part = self.part(notes=[(0, 1, KICK), (0, 1, SNARE), (1, 1, UNNAMED_DRUM_NOTE)], channel=DRUM_CHANNEL)
        voices = voices_of(part=part, chords=True, controls=True)
        self.assertEqual([voice.name for voice in voices], [MSG_UNNAMED_DRUM.format(number=1), MSG_DRUM_NAMES[KICK], MSG_DRUM_NAMES[SNARE]])
        self.assertTrue(all(voice.drum for voice in voices))

    def test_notes_together_in_a_chord_symbols_shape_are_one_chord_when_asked(self):
        part = self.part(notes=[(0, 4, pitch) for pitch in C_MAJOR_TRIAD])
        chords = voices_of(part=part, chords=True, controls=True)
        self.assertEqual([[played.chord for played in voice.played] for voice in chords], [[ChordSymbol.MAJOR]])
        self.assertEqual(len(voices_of(part=part, chords=False, controls=True)), len(C_MAJOR_TRIAD))

    def test_no_voice_plays_two_notes_at_once_and_none_is_left_out(self):
        part = self.part(notes=[(0, 8, 60), (2, 2, 64), (4, 8, 67), (6, 4, 72), (8, 2, 62)])
        voices = voices_of(part=part, chords=True, controls=True)
        for voice in voices:
            for before, after in zip(voice.played, voice.played[1:]):
                self.assertLessEqual(before.end, after.start)
        self.assertEqual(sum(len(voice.played) for voice in voices), len(part.notes))

    def test_a_part_that_plays_both_hands_is_split_and_one_hand_is_not(self):
        both = self.part(notes=[(start, 4, pitch) for start in range(0, 16, 4) for pitch in (36, 76)])
        one = self.part(notes=[(start, 4, pitch) for start in range(0, 16, 4) for pitch in (48, 64)])
        self.assertEqual([voice.name for voice in voices_of(part=both, chords=True, controls=True)], ['keys treble', 'keys bass'])
        self.assertEqual(len(voices_of(part=one, chords=True, controls=True)), 2)
        self.assertTrue(all(voice.name.startswith('keys ') and 'treble' not in voice.name for voice in voices_of(part=one, chords=True, controls=True)))


class TestScenesAndPatterns(unittest.TestCase):
    """Where the song splits into scenes and which pattern each clip repeats, each checked to play the same as its file."""

    def assert_plays_the_same(self, midi, **choices):
        trip = round_trip(midi_file=midi, choices=ImportChoices(song_name='tune', **choices))
        self.assertTrue(trip.comparison.is_same(), trip.comparison)
        return trip.imported

    def test_a_bar_played_again_and_again_is_one_pattern_repeated(self):
        riff = [note for bar in range(8) for note in melody(pitches=[48, 55, 52, 55], start=bar * SIXTEENTHS_IN_A_BAR)]
        imported = self.assert_plays_the_same(midi_of(tracks=[('bass', 0, riff)]))
        self.assertEqual(imported.patterns, 1)

    def test_no_scene_splits_through_a_held_note(self):
        notes = melody(pitches=[60, 62, 64]) + [(12, 8, 65)] + melody(pitches=[67, 69, 71, 72, 74, 76], start=20)
        imported = self.assert_plays_the_same(midi_of(tracks=[('lead', 0, notes)]), longest_pattern=LONGEST)
        starts = [scene_start for scene_start in self.scene_starts(imported)]
        self.assertNotIn(SIXTEENTHS_IN_A_BAR, starts)

    def scene_starts(self, imported):
        """Return the sixteenth each scene starts at, counting its repeats."""
        starts = []
        now = 0
        song = imported.song.song
        for scene in song[Section.SCENES]:
            starts.append(now)
            clip = next(iter(scene[SceneSetting.TRACKS].values()))
            pattern = imported.song.patterns.get(clip[ClipSlotSetting.PATTERN])
            sixteenths = pattern[PatternSetting.STEPS] * Rational(pattern.get(PatternSetting.STEP_SIZE, SIXTEENTH_NOTE)) * SIXTEENTHS_IN_A_WHOLE_NOTE
            now += int(sixteenths) * clip.get(ClipSlotSetting.REPEAT, 1) * scene.get(SceneSetting.REPEAT, 1)
        return starts

    def test_patterns_keep_within_the_longest_pattern_where_the_song_can_split(self):
        notes = melody(pitches=[60 + place % 12 for place in range(32)])
        imported = self.assert_plays_the_same(midi_of(tracks=[('lead', 0, notes)]), longest_pattern=LONGEST)
        self.assertEqual(imported.long_patterns, 0)
        self.assertTrue(all(data[PatternSetting.STEPS] <= LONGEST for data in imported.song.patterns.values()))

    def test_a_key_change_starts_a_scene_in_the_new_key(self):
        notes = melody(pitches=C_MAJOR_SCALE[:4]) + melody(pitches=[65, 67, B_FLAT, 72], start=SIXTEENTHS_IN_A_BAR)
        imported = self.assert_plays_the_same(midi_of(tracks=[('lead', 0, notes)], keys=((0, 'C'), (SIXTEENTHS_IN_A_BAR, 'F'))))
        scales = [scene.get(SceneSetting.SCALE) for scene in imported.song.song[Section.SCENES]]
        self.assertIn(F_MAJOR, scales)
        self.assertEqual(imported.song.song[SongSetting.SCALE], C_MAJOR)

    def test_a_tempo_change_starts_a_scene_at_the_new_tempo(self):
        notes = melody(pitches=C_MAJOR_SCALE[:4] * 2)
        imported = self.assert_plays_the_same(midi_of(tracks=[('lead', 0, notes)], tempos=((0, TEMPO), (SIXTEENTHS_IN_A_BAR, FASTER))))
        self.assertEqual([scene.get(SceneSetting.TEMPO) for scene in imported.song.song[Section.SCENES]][-1], FASTER)
        self.assertFalse(imported.warnings)

    def test_a_tempo_change_under_a_held_note_is_moved_and_said(self):
        notes = [(12, 8, 60)] + melody(pitches=[62, 64, 65], start=20)
        imported = MidiImport(midi_file=midi_of(tracks=[('lead', 0, notes)], tempos=((0, TEMPO), (SIXTEENTHS_IN_A_BAR, FASTER)))).imported(
            setlist=Setlist.new(), choices=ImportChoices(song_name='tune'))
        self.assertIn(MSG_WARN_TEMPOS_MOVED.format(count=1), imported.warnings)

    def test_notes_off_the_step_size_asked_for_are_moved_and_said(self):
        notes = melody(pitches=C_MAJOR_SCALE[:4], length=1, start=1)
        imported = MidiImport(midi_file=midi_of(tracks=[('lead', 0, notes)])).imported(
            setlist=Setlist.new(), choices=ImportChoices(song_name='tune', step_size=Rational(1, 8)))
        self.assertIn(MSG_WARN_SWUNG.format(count=2), imported.warnings)


class TestControls(unittest.TestCase):
    """The CCs the import brings in: the mod wheel, volume and sustain first, in that order, then the most sent others, on a part's first track, each at the value the file holds at every moment."""

    def test_a_set_that_sweeps_every_cc_the_import_takes_plays_back_exactly(self):
        trip = round_trip(midi_file=exported(CC_SWEEPS), choices=ImportChoices(song_name='sweeps'))
        self.assertTrue(trip.comparison.is_same(), trip.comparison)
        self.assertEqual([(difference.number, difference.largest) for difference in trip.comparison.controls], [(MOD_WHEEL, 0), (VOLUME, 0), (SUSTAIN, 0), (VOLUME, 0), (FILTER, 0)])
        tracks = trip.imported.song.song[Section.TRACKS]
        self.assertEqual([settings.get(TrackSetting.CC) for settings in tracks.values()], [[MOD_WHEEL, VOLUME, SUSTAIN, None], [VOLUME, FILTER, None, None]])

    def test_the_mod_wheel_volume_and_sustain_come_first_and_the_most_sent_others_fill_the_lanes(self):
        controls = [(0, SUSTAIN, 127), (0, EXPRESSION, 90), (SIXTEENTH * 4, EXPRESSION, 80), (0, MOD_WHEEL, 10), (0, VOLUME, 100), (0, REVERB, 40)]
        imported = MidiImport(midi_file=midi_of(tracks=[('lead', 0, melody(pitches=C_MAJOR_SCALE[:4]), controls)])).imported(
            setlist=Setlist.new(), choices=ImportChoices(song_name='tune'))
        self.assertEqual(imported.song.song[Section.TRACKS]['lead'][TrackSetting.CC], [MOD_WHEEL, VOLUME, SUSTAIN, EXPRESSION])
        self.assertIn(MSG_WARN_CONTROLS_LEFT_OUT.format(count=1, numbers=REVERB), imported.warnings)

    def test_with_import_ccs_off_none_come_in_and_the_dialog_says_so(self):
        controls = [(0, MOD_WHEEL, 10), (SIXTEENTH * 4, MOD_WHEEL, 20)]
        imported = MidiImport(midi_file=midi_of(tracks=[('lead', 0, melody(pitches=C_MAJOR_SCALE[:4]), controls)])).imported(
            setlist=Setlist.new(), choices=ImportChoices(song_name='tune', controls=False))
        self.assertNotIn(TrackSetting.CC, imported.song.song[Section.TRACKS]['lead'])
        self.assertIn(MSG_WARN_CONTROLS_OFF.format(count=2, numbers=MOD_WHEEL), imported.warnings)

    def test_a_parts_ccs_go_to_its_first_track_alone(self):
        notes = [(0, 4, pitch) for pitch in C_MAJOR_TRIAD]
        imported = MidiImport(midi_file=midi_of(tracks=[('keys', 0, notes, [(0, MOD_WHEEL, 64)])])).imported(
            setlist=Setlist.new(), choices=ImportChoices(song_name='tune', chords=False))
        lanes = [settings.get(TrackSetting.CC) for settings in imported.song.song[Section.TRACKS].values()]
        self.assertEqual(lanes, [[MOD_WHEEL, None, None, None], None, None])

    def test_a_recorded_sweep_comes_within_the_tolerance_and_the_import_says_it_moved(self):
        controls = [(tick, MOD_WHEEL, tick // RECORDED_RISE) for tick in range(0, SIXTEENTH * SIXTEENTHS_IN_A_BAR, RECORDED_TICKS)]
        trip = round_trip(midi_file=midi_of(tracks=[('lead', 0, melody(pitches=C_MAJOR_SCALE[:4]), controls)]), choices=ImportChoices(song_name='tune'))
        largest, _ = trip.comparison.largest_control_difference()
        self.assertLessEqual(largest, CONTROL_TOLERANCE)
        self.assertTrue(any(MSG_WARN_CONTROLS_MOVED.split(COUNT_FIELD)[1] in warning for warning in trip.imported.warnings))


class TestNames(unittest.TestCase):
    """What the import names, the user's rules of 2026-11-10."""

    def setUp(self):
        self.midi = midi_of(tracks=[('lead', 0, melody(pitches=C_MAJOR_SCALE[:4]))])

    def test_a_pattern_is_named_after_its_track_with_the_first_number_free(self):
        setlist = Setlist.new()
        setlist.copy_item(section=Section.PATTERNS, name=setlist.get_item_names(Section.PATTERNS)[0], new='lead 1')
        imported, _ = imported_into(setlist=setlist, midi=self.midi)
        self.assertEqual(list(imported.song.patterns), ['lead 2'])

    def test_a_second_import_is_a_second_song_with_names_of_its_own(self):
        setlist = Setlist.new()
        imported_into(setlist=setlist, midi=self.midi)
        imported, _ = imported_into(setlist=setlist, midi=self.midi)
        self.assertEqual(imported.song.name, 'tune 2')
        self.assertEqual(list(imported.song.patterns), ['lead 2'])

    def test_without_unique_names_a_pattern_the_set_has_exactly_is_shared(self):
        setlist = Setlist.new()
        imported_into(setlist=setlist, midi=self.midi)
        imported, song = imported_into(setlist=setlist, midi=self.midi, unique_names=False)
        self.assertEqual(imported.song.patterns, {})
        self.assertEqual(imported.song.shared, 1)
        self.assertEqual(song.get_scenes()[0].get_clip_slot('lead').get_pattern_name(), 'lead 1')

    def test_a_scale_is_reused_only_while_it_is_named_after_its_root_and_kind(self):
        setlist = Setlist.new()
        imported, _ = imported_into(setlist=setlist, midi=self.midi)
        self.assertEqual(imported.song.scales, {})
        setlist.rename_item(section=Section.SCALES, old=C_MAJOR, new='main')
        imported, _ = imported_into(setlist=setlist, midi=self.midi)
        self.assertEqual(list(imported.song.scales), [C_MAJOR])


if __name__ == '__main__':
    unittest.main()
