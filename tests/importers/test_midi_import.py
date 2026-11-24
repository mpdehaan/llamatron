# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The MIDI import: what it reads, how it splits a file into voices, scenes and patterns, how it names them, and that what it makes plays as the file does.

The proof is the round trip: a MIDI file imported into a new set, played and exported again,
plays the same notes at the same tempos as the file, for every file in examples/midi/ and for
every example set exported as MIDI, or the import says what it had to change
(internal_tools/import_check.py prints the same as a report). The smaller tests build MIDI files of
their own in memory, so nothing is written.
"""

import glob
import mido
import os
import unittest

from llamatron.exporters.midi_arrangement import MidiSong
from llamatron.importers import cutting, phrase_cut, voices as voices_values
from llamatron.importers.comparison import round_trip
from llamatron.importers.keys import degree_of, drum_note_of, key_of_notes, key_of_signature, MusicalKey
from llamatron.importers.midi_import import ImportChoices, MidiImport, MidiImportProblem
from llamatron.importers.midi_reading import MidiPart, PartNote, read_midi
from llamatron.importers.voices import Played, Voice, voices_of
from llamatron.importers.writing import add_imported
from llamatron.math.rational import Rational
from llamatron.model.objects import naming
from llamatron.model.objects.named_scale import NamedScale, scale_type_name
from llamatron.model.objects.naming import default_scale_name
from llamatron.model.objects.setlist import Setlist
from llamatron.model.schema import file_format, limits
from llamatron.model.schema.file_format import Accidental, ChordSymbol, ClipSlotSetting, PatternSetting, Row, ScaleSetting, SceneSetting, Section, SongSetting, TrackSetting
from llamatron.model.values.scale import ScaleType
from llamatron.user_strings import errors, importing, labels
from tests.support.example_renders import example_setlist, first_song_grid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAMPLE_MIDI_FILES = os.path.join(ROOT, 'examples', 'midi', '*.mid')
CC_SWEEPS = os.path.join(ROOT, 'tests', 'data', 'sample_sets', 'cc_sweeps.yml')
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
# A voice a test makes, by name.
A_VOICE = 'voice'
MIDDLE_C = 60
C_MAJOR_TRIAD = (60, 64, 67)
C_MAJOR_SCALE = (60, 62, 64, 65, 67, 69, 71)
B_FLAT = 70
LOWEST_PITCH = 12
# The General MIDI kick, C in octave 3 as a drum pattern writes it, and the side stick a half step above.
KICK_PITCH = 36
KICK_LETTER = 'C'
KICK_OCTAVE = 3
HIGHEST_PITCH = 127
QUARTER = Rational(1, 4)
SIXTEENTH_NOTE = Rational(1, 16)
# Quarter notes in sixteenths, and the phrase the Import Wizard's cut asks for, in bars.
QUARTER_NOTE = 4
PHRASE_BARS = 8
SIXTEENTHS_IN_A_WHOLE_NOTE = 16
# A scene's tempo is held as a percentage of the song's.
PERCENT = 100
TEMPO = 120
FASTER = 150
LONGEST = 8
NO_HALF_STEPS = 0
# mido's names for the messages and meta messages these tests write.
NOTE_ON = 'note_on'
NOTE_OFF = 'note_off'
CONTROL_CHANGE = 'control_change'
PROGRAM_CHANGE = 'program_change'
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
    """Return an example set's first song as one MIDI file in memory, with a fixed seed, from the render the example's checks share."""
    return MidiSong(directory=os.curdir, grid=first_song_grid(path, seed=SEED), name=example_setlist(path).first_song_name()).midi_file()


class TestRoundTripOfTheSampleFiles(unittest.TestCase):
    """Anything imported plays back as the file plays it, or the import says what changed: each kind of file a class of its own, so that they run side by side."""

    def test_every_sample_midi_file_plays_back_the_same(self):
        paths = sorted(glob.glob(SAMPLE_MIDI_FILES))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(path=path):
                trip = round_trip(midi_file=mido.MidiFile(path), choices=ImportChoices(song_name=os.path.basename(path)))
                self.assertTrue(trip.comparison.is_same(), trip.comparison)


def check_round_trip(*, test, path):
    """An example set, exported as MIDI and imported, plays back the same, or the import says why."""
    trip = round_trip(midi_file=exported(path), choices=ImportChoices(song_name=os.path.basename(path)))
    test.assertTrue(trip.comparison.is_same() or trip.imported.warnings)


class TestRoundTripWithALongerLongestPattern(unittest.TestCase):

    def test_a_longer_longest_pattern_makes_fewer_scenes_and_still_plays_the_same(self):
        midi = mido.MidiFile(sorted(glob.glob(SAMPLE_MIDI_FILES))[0])
        short = round_trip(midi_file=midi, choices=ImportChoices(song_name='short', longest_pattern=LONGEST))
        long = round_trip(midi_file=midi, choices=ImportChoices(song_name='long'))
        self.assertTrue(short.comparison.is_same() and long.comparison.is_same())
        self.assertGreater(short.imported.scenes, long.imported.scenes)


class TestPlayedBetween(unittest.TestCase):

    def test_a_voice_gives_what_starts_from_one_time_up_to_another_and_not_at_it(self):
        starts = [0, 1, 2, 3, 5]
        voice = Voice(name=A_VOICE, drum=False, played=[Played(start, start + 1, (MIDDLE_C,), VELOCITY, None) for start in starts])
        self.assertEqual([played.start for played in voice.played_between(begin=1, end=3)], [1, 2])
        self.assertEqual([played.start for played in voice.played_between(begin=4, end=5)], [])
        self.assertEqual([played.start for played in voice.played_between(begin=0, end=6)], starts)


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
        self.assertEqual(str(raised.exception), errors.ERR_MIDI_NO_NOTES)


class TestKeys(unittest.TestCase):

    def test_a_drum_is_written_as_its_letter_its_sharp_and_its_octave(self):
        self.assertEqual(drum_note_of(KICK_PITCH), (KICK_LETTER, None, KICK_OCTAVE))
        self.assertEqual(drum_note_of(KICK_PITCH + 1), (KICK_LETTER, Accidental.SHARP, KICK_OCTAVE))

    def test_every_note_written_as_a_degree_plays_its_own_pitch(self):
        for key in (key_of_signature('C'), key_of_signature('F'), key_of_signature('Bbm'), key_of_signature('F#m'), key_of_signature('B')):
            scale = NamedScale.from_data(data={ScaleSetting.ROOT: key.root, ScaleSetting.TYPE: key.kind}, where=WHERE)
            for pitch in range(LOWEST_PITCH, HIGHEST_PITCH + 1):
                written = degree_of(pitch=pitch, key=key)
                if written is None:
                    continue
                degree, accidental, octave = written
                half_steps = file_format.ACCIDENTALS.get(accidental, NO_HALF_STEPS)
                with self.subTest(key=key, pitch=pitch):
                    note = scale.scale_at(octave).note_at(degree=degree, scale_notes=0, half_steps=half_steps, length=QUARTER)
                    self.assertEqual(note.get_midi_number(), pitch)

    def test_a_key_signature_is_a_major_or_minor_scale_with_a_root_a_scale_can_have(self):
        self.assertEqual(key_of_signature('Bbm'), MusicalKey(root='Bb', kind=scale_type_name(ScaleType.MINOR), flats=True))
        self.assertEqual(key_of_signature('Cb').root, 'B')
        self.assertTrue(key_of_signature('F').flats)
        self.assertFalse(key_of_signature('G').flats)

    def test_a_file_with_no_key_signature_is_in_the_key_its_notes_are_in(self):
        notes = [PartNote(Rational(place), Rational(place + 1), pitch, VELOCITY) for place, pitch in enumerate(C_MAJOR_SCALE + (MIDDLE_C, 67))]
        self.assertEqual(key_of_notes(notes), MusicalKey(root='C', kind=scale_type_name(ScaleType.MAJOR), flats=False))


class TestVoices(unittest.TestCase):

    def part(self, *, notes, channel=0):
        return MidiPart(name='keys', channel=channel, controls=[], notes=sorted(PartNote(Rational(start, SIXTEENTHS_IN_A_WHOLE_NOTE), Rational(start + length, SIXTEENTHS_IN_A_WHOLE_NOTE), pitch, VELOCITY) for start, length, pitch in notes))

    def test_drums_are_a_voice_for_each_sound_named_by_general_midi(self):
        part = self.part(notes=[(0, 1, KICK), (0, 1, SNARE), (1, 1, UNNAMED_DRUM_NOTE)], channel=DRUM_CHANNEL)
        voices = voices_of(part=part, chords=True, controls=True)
        self.assertEqual([voice.name for voice in voices], [importing.MSG_UNNAMED_DRUM.format(number=1), importing.MSG_DRUM_NAMES[KICK], importing.MSG_DRUM_NAMES[SNARE]])
        self.assertTrue(all(voice.drum for voice in voices))

    def test_a_slurred_line_on_an_instrument_of_one_note_is_one_voice_with_glide_and_a_keyboards_two_voices_stay_apart(self):
        # Each note held past the next note's start, one of them past the note after too.
        slurred = [(0, 6, 60), (4, 3, 62), (6, 5, 64), (8, 4, 65)]
        alto_sax = 66
        horn = self.part(notes=slurred)
        horn.program = alto_sax - limits.MIN_GM_SOUND
        voices = voices_of(part=horn, chords=True, controls=True)
        self.assertEqual(len(voices), 1)
        self.assertEqual([played.glide for played in voices[0].played], [True, True, True, False])
        self.assertEqual([played.end for played in voices[0].played[:-1]], [played.start for played in voices[0].played[1:]])
        self.assertEqual(len(voices_of(part=self.part(notes=slurred), chords=True, controls=True)), 2)

    def test_a_slurred_line_imported_says_how_many_notes_glide(self):
        notes = [(0, 5, 60), (4, 5, 62), (8, 5, 64), (12, 4, 65)]
        midi = midi_of(tracks=[('sax', 0, notes)])
        midi.tracks[1].insert(1, mido.Message(PROGRAM_CHANGE, channel=0, program=65))
        imported, _ = imported_into(setlist=Setlist.new(), midi=midi)
        self.assertEqual(imported.tracks, 1)
        self.assertIn(importing.MSG_WARN_GLIDED.format(count=3), imported.warnings)

    def test_notes_together_in_a_chord_symbols_shape_are_one_chord_when_asked(self):
        part = self.part(notes=[(0, 4, pitch) for pitch in C_MAJOR_TRIAD])
        chords = voices_of(part=part, chords=True, controls=True)
        self.assertEqual([[played.chord for played in voice.played] for voice in chords], [[ChordSymbol.MAJOR]])
        self.assertEqual(len(voices_of(part=part, chords=False, controls=True)), len(C_MAJOR_TRIAD))

    def test_a_chord_in_an_inversion_is_its_chord_with_the_inversion_written_from_its_root(self):
        second_inversion = (67, 72, 76)
        played = voices_of(part=self.part(notes=[(0, 4, pitch) for pitch in second_inversion]), chords=True, controls=True)[0].played[0]
        self.assertEqual((played.chord, played.inversion, played.root), (ChordSymbol.MAJOR, 2, MIDDLE_C))

    def test_an_inverted_chord_imported_plays_the_same_notes_as_the_file(self):
        first_inversion = (64, 67, 72)
        midi = midi_of(tracks=[('keys', 0, [(start, 4, pitch) for start in (0, 4) for pitch in first_inversion])])
        trip = round_trip(midi_file=midi, choices=ImportChoices(song_name='tune'))
        self.assertEqual([data[Row.INVERSION][0] for data in trip.imported.song.patterns.values()], [1])
        self.assertTrue(trip.comparison.is_same())

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

    def test_scenes_are_named_after_their_bars_when_the_ccs_need_a_finer_grid_than_the_notes(self):
        # Quarter notes over two bars, with a CC every sixty-fourth, which the scenes split on, and a key change at bar 2.
        notes = melody(pitches=C_MAJOR_SCALE[:4]) + melody(pitches=[65, 67, B_FLAT, 72], start=SIXTEENTHS_IN_A_BAR)
        sixty_fourth = SIXTEENTH // 4
        sweep = [(tick, EXPRESSION, tick // sixty_fourth % 128) for tick in range(0, 2 * SIXTEENTHS_IN_A_BAR * SIXTEENTH, sixty_fourth)]
        imported = self.assert_plays_the_same(midi_of(tracks=[('lead', 0, notes, sweep)], keys=((0, 'C'), (SIXTEENTHS_IN_A_BAR, 'F'))))
        names = [scene[SceneSetting.NAME] for scene in imported.song.song[Section.SCENES]]
        self.assertEqual(sorted(set(names)), [importing.MSG_SCENE_BAR.format(first=1), importing.MSG_SCENE_BAR.format(first=2)])

    def test_a_tempo_change_starts_a_scene_at_the_new_tempo(self):
        notes = melody(pitches=C_MAJOR_SCALE[:4] * 2)
        imported = self.assert_plays_the_same(midi_of(tracks=[('lead', 0, notes)], tempos=((0, TEMPO), (SIXTEENTHS_IN_A_BAR, FASTER))))
        # The last scene plays at its percentage of the song's tempo.
        self.assertEqual([scene.get(SceneSetting.TEMPO) for scene in imported.song.song[Section.SCENES]][-1], FASTER * PERCENT // TEMPO)
        self.assertFalse(imported.warnings)

    def test_a_tempo_change_under_a_held_note_is_moved_and_said(self):
        notes = [(12, 8, 60)] + melody(pitches=[62, 64, 65], start=20)
        imported = MidiImport(midi_file=midi_of(tracks=[('lead', 0, notes)], tempos=((0, TEMPO), (SIXTEENTHS_IN_A_BAR, FASTER)))).imported(
            setlist=Setlist.new(), choices=ImportChoices(song_name='tune'))
        self.assertIn(importing.MSG_WARN_TEMPOS_MOVED.format(count=1), imported.warnings)

    def test_notes_off_the_step_size_asked_for_are_moved_and_said(self):
        notes = melody(pitches=C_MAJOR_SCALE[:4], length=1, start=1)
        imported = MidiImport(midi_file=midi_of(tracks=[('lead', 0, notes)])).imported(
            setlist=Setlist.new(), choices=ImportChoices(song_name='tune', step_size=Rational(1, 8)))
        self.assertIn(importing.MSG_WARN_SWUNG.format(count=2), imported.warnings)


def played(ticks, *, length=SIXTEENTH):
    """Return a mido file of one part playing middle C at each tick, as a person plays, a little either side of the beat."""
    midi = mido.MidiFile(type=1, ticks_per_beat=TICKS_PER_BEAT)
    midi.tracks.append(track_of(timed=[(0, mido.MetaMessage(SET_TEMPO, tempo=mido.bpm2tempo(TEMPO)))]))
    timed = [(0, mido.MetaMessage(TRACK_NAME, name=A_VOICE))]
    for tick in ticks:
        timed.append((tick, mido.Message(NOTE_ON, channel=0, note=MIDDLE_C, velocity=VELOCITY)))
        timed.append((tick + length, mido.Message(NOTE_OFF, channel=0, note=MIDDLE_C)))
    midi.tracks.append(track_of(timed=timed))
    return midi


class TestQuantizing(unittest.TestCase):
    """A file played by hand is put on the longest grid nearly all its notes start near, and one played too freely for any on the
    finest step allowed; a score's notes, all on a grid, are moved by nothing (TestScenesAndPatterns)."""

    def step_size_of(self, midi, **choices):
        return MidiImport(midi_file=midi).imported(setlist=Setlist.new(), choices=ImportChoices(song_name='tune', **choices))

    def test_eighths_played_a_little_early_and_late_are_put_on_eighths(self):
        eighth = TICKS_PER_BEAT // 2
        strays = [6, -5, 4, 0, -6, 3, 5, -4]
        imported = self.step_size_of(played([eighth * (place + 1) + stray for place, stray in enumerate(strays)]))
        self.assertEqual(imported.step_size, Rational(1, 8))
        self.assertEqual(imported.moved, sum(1 for stray in strays if stray))

    def test_thirty_seconds_played_by_hand_keep_their_own_grid(self):
        thirty_second = TICKS_PER_BEAT // 8
        strays = [3, -2, 0, 2, -3, 1, 0, -1]
        imported = self.step_size_of(played([thirty_second * (place + 4) + stray for place, stray in enumerate(strays)], length=thirty_second // 2))
        self.assertEqual(imported.step_size, Rational(1, 32))

    def test_notes_played_too_freely_for_any_grid_go_on_the_finest_step_allowed(self):
        free = [101, 263, 397, 589, 701, 853, 977, 1123]
        self.assertEqual(self.step_size_of(played(free)).step_size, cutting.FINEST_STEP_SIZE)
        self.assertEqual(self.step_size_of(played(free), finest_step=SIXTEENTH_NOTE).step_size, SIXTEENTH_NOTE)


def phrase(*, pitches, bars, start_bar):
    """Return a tune of quarter notes from a bar on, the pitches round and round for so many bars."""
    count = bars * SIXTEENTHS_IN_A_BAR // QUARTER_NOTE
    return melody(pitches=[pitches[place % len(pitches)] for place in range(count)], start=start_bar * SIXTEENTHS_IN_A_BAR)


class TestPhrasesAndSections(unittest.TestCase):
    """The Import Wizard's cut, asked for by a longest pattern in bars: phrases of that many bars, each a pattern every phrase
    alike shares, gathered into sections, and figures that keep returning made patterns of their own; each checked to play the
    same as its file."""

    def imported(self, tracks, **choices):
        trip = round_trip(midi_file=midi_of(tracks=tracks), choices=ImportChoices(song_name='tune', longest_bars=PHRASE_BARS, **choices))
        self.assertTrue(trip.comparison.is_same(), trip.comparison)
        return trip.imported

    def lists(self, imported):
        """Return each scene's clip of the lead as the list of patterns it plays."""
        lists = []
        for scene in imported.song.song[Section.SCENES]:
            clip = scene[SceneSetting.TRACKS]['lead']
            lists.append(clip.get(ClipSlotSetting.PATTERNS, [clip.get(ClipSlotSetting.PATTERN)]))
        return lists

    def test_a_refrain_that_returns_starts_a_section_and_plays_the_patterns_it_played_before(self):
        refrain = phrase(pitches=[60, 62, 64, 65, 67], bars=PHRASE_BARS, start_bar=0)
        verse = phrase(pitches=[69, 67, 65], bars=PHRASE_BARS, start_bar=PHRASE_BARS)
        again = phrase(pitches=[60, 62, 64, 65, 67], bars=PHRASE_BARS, start_bar=2 * PHRASE_BARS)
        lists = self.lists(self.imported([('lead', 0, refrain + verse + again)]))
        self.assertEqual(len(lists), 3)
        self.assertEqual(lists[2], lists[0])

    def test_a_section_holds_at_most_four_phrases(self):
        notes = []
        for place in range(phrase_cut.MOST_PHRASES_A_SECTION + 1):
            # Each phrase a run of its own, no bar of it heard anywhere else.
            notes += phrase(pitches=list(range(40 + place, 72 + place)), bars=PHRASE_BARS, start_bar=place * PHRASE_BARS)
        lists = self.lists(self.imported([('lead', 0, notes)]))
        self.assertEqual([len(listed) for listed in lists], [phrase_cut.MOST_PHRASES_A_SECTION, 1])

    def test_a_figure_that_keeps_returning_inside_other_phrases_is_a_pattern_of_its_own(self):
        figure = [64, 67]
        notes = []
        for place in range(3):
            notes += phrase(pitches=figure, bars=2, start_bar=place * PHRASE_BARS)
            notes += phrase(pitches=[60 + place, 62, 65 + place], bars=PHRASE_BARS - 2, start_bar=place * PHRASE_BARS + 2)
        lists = self.lists(self.imported([('lead', 0, notes)]))
        first_pieces = [listed for listed in lists[0]]
        self.assertGreater(len(first_pieces), 3)
        self.assertEqual(sum(listed.count(first_pieces[0]) for listed in lists), 3)

    def test_a_chord_held_across_phrase_lines_is_tied_on_and_no_pattern_passes_the_longest(self):
        # A pad's chord held for twenty bars under a tune, which no scene may start inside, so the phrases are one clip's list.
        held_bars = 20
        pad = [(0, held_bars * SIXTEENTHS_IN_A_BAR, pitch) for pitch in C_MAJOR_TRIAD]
        tune = phrase(pitches=list(C_MAJOR_SCALE), bars=held_bars + 4, start_bar=0)
        imported = self.imported([('lead', 0, tune), ('pad', 1, pad)])
        self.assertEqual(len(imported.song.song[Section.SCENES]), 1)
        for data in imported.song.patterns.values():
            self.assertLessEqual(data[PatternSetting.STEPS], PHRASE_BARS * SIXTEENTHS_IN_A_BAR)


class TestInstruments(unittest.TestCase):
    """Every imported track plays through an instrument named after the General MIDI sound its channel's program sets, a piano
    where the file sets none, played through FluidSynth; a drum track through the drums instrument."""

    def test_each_track_gets_its_sounds_instrument_a_piano_by_default_and_drums_their_own(self):
        midi = midi_of(tracks=[('lead', 0, melody(pitches=[60, 62])), ('organ', 1, melody(pitches=[48, 50])), ('kit', DRUM_CHANNEL, melody(pitches=[KICK]))])
        program_of_the_organ = 16
        midi.tracks[2].insert(1, mido.Message(PROGRAM_CHANGE, channel=1, program=program_of_the_organ))
        setlist = Setlist.new()
        _, song = imported_into(setlist=setlist, midi=midi)
        organ_name = labels.MSG_GM_SOUNDS[program_of_the_organ]
        instruments = {track: song.get_track(track).get_instrument_name() for track in song.get_track_names()}
        self.assertEqual(instruments['lead'], naming.suggested_word(labels.MSG_GM_SOUNDS[0]))
        self.assertEqual(instruments['organ'], naming.suggested_word(organ_name))
        self.assertEqual(instruments[importing.MSG_DRUM_NAMES[KICK]], importing.MSG_DRUMS_INSTRUMENT)
        organ = setlist.get_item(section=Section.INSTRUMENTS, name=instruments['organ'])
        self.assertEqual(organ.get_gm_sound(), program_of_the_organ + limits.MIN_GM_SOUND)
        self.assertEqual(organ.get_device(), file_format.FLUIDSYNTH_DEVICE)


class TestTheWizardsNames(unittest.TestCase):
    """The Import Wizard numbers its scenes, S01, with the letter of each section's material, gives each scene a numbered scale,
    or each run of scenes in one key one scale, and groups patterns by the letter of the sections they are heard in."""

    def refrain_verse_refrain(self, **choices):
        refrain = phrase(pitches=[60, 62, 64, 65, 67], bars=PHRASE_BARS, start_bar=0)
        verse = phrase(pitches=[69, 67, 65], bars=PHRASE_BARS, start_bar=PHRASE_BARS)
        again = phrase(pitches=[60, 62, 64, 65, 67], bars=PHRASE_BARS, start_bar=2 * PHRASE_BARS)
        trip = round_trip(midi_file=midi_of(tracks=[('lead', 0, refrain + verse + again)]), choices=ImportChoices(
            song_name='tune', longest_bars=PHRASE_BARS, numbered=True, **choices))
        self.assertTrue(trip.comparison.is_same(), trip.comparison)
        return trip.imported.song

    def test_scenes_are_numbered_and_lettered_by_their_material(self):
        song = self.refrain_verse_refrain()
        names = [scene[SceneSetting.NAME] for scene in song.song[Section.SCENES]]
        self.assertEqual([name.split(',')[0] for name in names], ['S01 A', 'S02 B', 'S03 A'])

    def test_every_scene_has_a_numbered_scale_of_its_own_unless_runs_of_one_key_share_one(self):
        apart = [scene[SceneSetting.SCALE] for scene in self.refrain_verse_refrain().song[Section.SCENES]]
        shared = [scene[SceneSetting.SCALE] for scene in self.refrain_verse_refrain(scale_per_scene=False).song[Section.SCENES]]
        self.assertEqual([name.split('_')[0] for name in apart], ['S01', 'S02', 'S03'])
        self.assertEqual(len(set(shared)), 1)

    def test_patterns_are_grouped_by_the_letter_of_their_sections(self):
        song = self.refrain_verse_refrain()
        self.assertEqual(sorted({data[PatternSetting.GROUP] for data in song.patterns.values()}), ['A', 'B'])


class TestControls(unittest.TestCase):
    """The CCs the import brings in: the mod wheel, volume and sustain first, in that order, then the most sent others, on a part's first track, each at the value the file holds at every moment."""

    def test_a_set_that_sweeps_every_cc_the_import_takes_plays_back_exactly(self):
        trip = round_trip(midi_file=exported(CC_SWEEPS), choices=ImportChoices(song_name='sweeps'))
        self.assertTrue(trip.comparison.is_same(), trip.comparison)
        self.assertEqual([(difference.number, difference.largest) for difference in trip.comparison.controls], [(voices_values.MOD_WHEEL, 0), (voices_values.VOLUME, 0), (voices_values.SUSTAIN, 0), (voices_values.VOLUME, 0), (FILTER, 0)])
        tracks = trip.imported.song.song[Section.TRACKS]
        self.assertEqual([settings.get(TrackSetting.CC) for settings in tracks.values()], [[voices_values.MOD_WHEEL, voices_values.VOLUME, voices_values.SUSTAIN, None], [voices_values.VOLUME, FILTER, None, None]])

    def test_the_mod_wheel_volume_and_sustain_come_first_and_the_most_sent_others_fill_the_lanes(self):
        controls = [(0, voices_values.SUSTAIN, 127), (0, EXPRESSION, 90), (SIXTEENTH * 4, EXPRESSION, 80), (0, voices_values.MOD_WHEEL, 10), (0, voices_values.VOLUME, 100), (0, REVERB, 40)]
        imported = MidiImport(midi_file=midi_of(tracks=[('lead', 0, melody(pitches=C_MAJOR_SCALE[:4]), controls)])).imported(
            setlist=Setlist.new(), choices=ImportChoices(song_name='tune'))
        self.assertEqual(imported.song.song[Section.TRACKS]['lead'][TrackSetting.CC], [voices_values.MOD_WHEEL, voices_values.VOLUME, voices_values.SUSTAIN, EXPRESSION])
        self.assertIn(importing.MSG_WARN_CONTROLS_LEFT_OUT.format(count=1, numbers=REVERB), imported.warnings)

    def test_with_import_ccs_off_none_come_in_and_the_dialog_says_so(self):
        controls = [(0, voices_values.MOD_WHEEL, 10), (SIXTEENTH * 4, voices_values.MOD_WHEEL, 20)]
        imported = MidiImport(midi_file=midi_of(tracks=[('lead', 0, melody(pitches=C_MAJOR_SCALE[:4]), controls)])).imported(
            setlist=Setlist.new(), choices=ImportChoices(song_name='tune', controls=False))
        self.assertNotIn(TrackSetting.CC, imported.song.song[Section.TRACKS]['lead'])
        self.assertIn(importing.MSG_WARN_CONTROLS_OFF.format(count=2, numbers=voices_values.MOD_WHEEL), imported.warnings)

    def test_a_parts_ccs_go_to_its_first_track_alone(self):
        notes = [(0, 4, pitch) for pitch in C_MAJOR_TRIAD]
        imported = MidiImport(midi_file=midi_of(tracks=[('keys', 0, notes, [(0, voices_values.MOD_WHEEL, 64)])])).imported(
            setlist=Setlist.new(), choices=ImportChoices(song_name='tune', chords=False))
        lanes = [settings.get(TrackSetting.CC) for settings in imported.song.song[Section.TRACKS].values()]
        self.assertEqual(lanes, [[voices_values.MOD_WHEEL, None, None, None], None, None])

    def test_a_recorded_sweep_comes_within_the_tolerance_and_the_import_says_it_moved(self):
        controls = [(tick, voices_values.MOD_WHEEL, tick // RECORDED_RISE) for tick in range(0, SIXTEENTH * SIXTEENTHS_IN_A_BAR, RECORDED_TICKS)]
        trip = round_trip(midi_file=midi_of(tracks=[('lead', 0, melody(pitches=C_MAJOR_SCALE[:4]), controls)]), choices=ImportChoices(song_name='tune'))
        largest, _ = trip.comparison.largest_control_difference()
        self.assertLessEqual(largest, cutting.CONTROL_TOLERANCE)
        self.assertTrue(any(importing.MSG_WARN_CONTROLS_MOVED.split(COUNT_FIELD)[1] in warning for warning in trip.imported.warnings))


class TestNames(unittest.TestCase):
    """What the import names."""

    def setUp(self):
        self.midi = midi_of(tracks=[('lead', 0, melody(pitches=C_MAJOR_SCALE[:4]))])

    def test_a_pattern_is_named_after_its_track_with_the_next_number(self):
        setlist = Setlist.new()
        setlist.copy_item(section=Section.PATTERNS, name=setlist.get_item_names(Section.PATTERNS)[0], new='lead-1')
        imported, _ = imported_into(setlist=setlist, midi=self.midi)
        self.assertEqual(list(imported.song.patterns), ['lead-2'])

    def test_an_imported_pattern_is_in_the_group_named_after_its_track(self):
        setlist = Setlist.new()
        imported, _ = imported_into(setlist=setlist, midi=self.midi)
        for name in imported.song.patterns:
            self.assertEqual(setlist.get_pattern(name).get_group(), setlist.first_track_playing(name))
            self.assertIsNotNone(setlist.get_pattern(name).get_group())

    def test_a_second_import_is_a_second_song_with_names_of_its_own(self):
        setlist = Setlist.new()
        imported_into(setlist=setlist, midi=self.midi)
        imported, _ = imported_into(setlist=setlist, midi=self.midi)
        self.assertEqual(imported.song.name, 'tune-2')
        self.assertEqual(list(imported.song.patterns), ['lead-2'])

    def test_without_unique_names_a_pattern_the_set_has_exactly_is_shared(self):
        setlist = Setlist.new()
        imported_into(setlist=setlist, midi=self.midi)
        imported, song = imported_into(setlist=setlist, midi=self.midi, unique_names=False)
        self.assertEqual(imported.song.patterns, {})
        self.assertEqual(imported.song.shared, 1)
        self.assertEqual(song.get_scenes()[0].get_clip_slot('lead').get_pattern_name(), 'lead-1')

    def test_a_scale_is_reused_only_while_it_is_named_after_its_root_and_kind(self):
        # A new set's scale is named by its number, a name that says nothing of its notes, so the import adds its own.
        setlist = Setlist.new()
        imported, _ = imported_into(setlist=setlist, midi=self.midi)
        self.assertEqual(list(imported.song.scales), [C_MAJOR])
        # The scale that import added is named after its notes, so the next import uses it, until a person renames it.
        imported, _ = imported_into(setlist=setlist, midi=self.midi)
        self.assertEqual(imported.song.scales, {})
        setlist.rename_item(section=Section.SCALES, old=C_MAJOR, new='main')
        imported, _ = imported_into(setlist=setlist, midi=self.midi)
        self.assertEqual(list(imported.song.scales), [C_MAJOR])


if __name__ == '__main__':
    unittest.main()
