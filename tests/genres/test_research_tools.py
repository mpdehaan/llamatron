# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""The research tools of internal_tools/analysis_and_generation/, one quick check of each tool's main path: the chord files' readers, the corpus layer, the corpus fetcher's refusal of a member that climbs out of its folder, the genre analysis, the MIDI cleaning, two drum grooves compared, and the genre measures. A research tool fails loudly when it is run, so one check each is enough (.claude/TESTING.md)."""

from corpus import chord_files
from measuring.hearing.cleaning import KICK, tidied
from measuring.hearing.performance import Performance, performance_of, PlayedNote, PlayedTrack
from measuring.hearing.profile import profile_of_performance
from measuring.measures.comparing import groove_gap, SAME
from measuring.measures.drum_patterns import GROOVES
from measuring.measures.registry import MEASURES
from measuring.measures.traits import BassMotion, Trait, TRAITS
from measuring.strings import GrooveName
import os
from pathlib import Path
import sys
import tempfile
import unittest

from llamatron.composition.setlist import Setlist

C = 0
G = 7
BILLBOARD = '''# title: Made Up
# artist: Nobody
# metre: 4/4
# tonic: G

0.0\tsilence
0.3\tA, intro, | G:maj | G:maj |, (guitar)
5.4\tB, verse, | G:maj | C:maj | D:maj | E:min |, (voice
15.8\tC, solo, | C:maj | Bb:maj | G:maj | G:maj |, (guitar)
'''


class TestBillboard(unittest.TestCase):

    def test_a_song_is_read_as_its_tonic_sections_and_bars(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'salami_chords.txt'
            path.write_text(BILLBOARD)
            tonic, sections, bars = chord_files.billboard_song(path)
        self.assertEqual(tonic, G)
        self.assertEqual(sections, ['intro', 'verse', 'solo'])
        self.assertEqual(bars[3], ['IV'])
        self.assertEqual(bars[-3], ['bIII'])


TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, 'internal_tools', 'analysis_and_generation')
sys.path.insert(0, TOOLS)
from corpus.piece import CorpusNote, Piece  # noqa: E402


DRUM_PART = 'kit'
BEATS = 4


class TestReading(unittest.TestCase):

    def test_a_piece_becomes_the_analyzers_notes_part_by_part_with_drums_apart(self):
        notes = (CorpusNote(start=0, length=1, pitch=60), CorpusNote(start=1, length=1, pitch=62), CorpusNote(start=0, length=0.5, pitch=36, part=DRUM_PART))
        performance = Piece(source='lakh-clean', identity='made up', notes=notes, drum_parts=frozenset({DRUM_PART})).performance()
        self.assertEqual(len(performance.tracks), 2)
        self.assertEqual([track.drum for track in performance.tracks], [False, True])
        self.assertEqual(float(performance.length), BEATS)


TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, 'internal_tools', 'analysis_and_generation')
sys.path.insert(0, TOOLS)
import fetch_corpus  # noqa: E402

TOP = 'essen-folksong-collection-main'
CLIMBING = TOP + '/../../etc/passwd.krn'
ABSOLUTE = '/etc/passwd.krn'
README = TOP + '/README.txt'


class TestFetchCorpus(unittest.TestCase):

    def test_a_member_climbing_out_or_absolute_is_refused(self):
        self.assertIsNone(fetch_corpus.safe_member_path(CLIMBING))
        self.assertIsNone(fetch_corpus.safe_member_path(ABSOLUTE))
        self.assertIsNone(fetch_corpus.safe_member_path(TOP))


BEATS = 4
TEMPO = 120
METER = '4/4'
VELOCITY = 100
C = 60
C_MAJOR_SCALE = (60, 62, 64, 65, 67, 69, 71, 72)
SNARE = 38
HAT = 42
BASS_NOTE = 36
SONG = 'test'
# The traits the analyzer cannot yet measure from notes: form, since how to split a song is not known, and solos, which it cannot yet find.
UNMEASURED_TRAITS = (Trait.FORM, Trait.SOLOS)


def note(*, start, length=0.5, pitch=C, velocity=VELOCITY):
    return PlayedNote(start=start, end=start + length, pitch=pitch, velocity=velocity)


def track(*, name, notes, drum=False, sound=None):
    return PlayedTrack(name=name, drum=drum, sound=sound, notes=tuple(sorted(notes, key=lambda each: (each.start, each.pitch))))


def performance(*, tracks, bars):
    return Performance(tracks=tuple(tracks), tempo=TEMPO, meter=METER, beats_per_bar=BEATS, length=bars * BEATS)


def scale_tune(bars):
    """Return a lead walking up and down the C major scale in eighths, a rest at the end of each bar."""
    notes = []
    for bar in range(bars):
        pitches = C_MAJOR_SCALE[:4] + tuple(reversed(C_MAJOR_SCALE[:3])) if bar % 2 == 0 else C_MAJOR_SCALE[3:7] + tuple(reversed(C_MAJOR_SCALE[4:7]))
        for place, pitch in enumerate(pitches):
            notes.append(note(start=bar * BEATS + place * 0.5, pitch=pitch))
    return notes


def rock_drums(bars):
    notes = []
    for bar in range(bars):
        start = bar * BEATS
        notes += [note(start=start, pitch=KICK), note(start=start + 2, pitch=KICK), note(start=start + 1, pitch=SNARE), note(start=start + 3, pitch=SNARE)]
        notes += [note(start=start + place * 0.5, pitch=HAT) for place in range(8)]
    return notes


def root_bass(bars):
    return [note(start=bar * BEATS + beat, length=1, pitch=BASS_NOTE) for bar in range(bars) for beat in range(BEATS)]


class TestAnalysis(unittest.TestCase):

    def test_a_song_written_note_by_note_is_measured_in_every_trait(self):
        song = performance(tracks=[track(name='a', notes=rock_drums(8), drum=True), track(name='b', notes=root_bass(8)), track(name='c', notes=scale_tune(8))], bars=8)
        profile = profile_of_performance(performance=song, name=SONG)
        for trait in TRAITS:
            if trait not in UNMEASURED_TRAITS:
                self.assertIsNotNone(profile.trait(trait), trait)
        self.assertEqual(profile.trait(Trait.BASS).motion, BassMotion.ROOTS)
        self.assertGreater(profile.trait(Trait.HOOK).strength, 0.5)
        self.assertTrue(profile.trait(Trait.DRUMS).main().has_backbeat())


BEATS_PER_BAR = 4
BARS = 16
VELOCITY = 90
LEAD_PROGRAM = 81
SCALE = (60, 62, 64, 65, 67, 69, 71, 72)
HAT = 42
LEAD = 'lead'
DRUMS = 'Drums'


def cleaned_note(*, start, pitch, length=0.5):
    return PlayedNote(start=start, end=start + length, pitch=pitch, velocity=VELOCITY)


def melody(*, name=LEAD, sound=LEAD_PROGRAM):
    return PlayedTrack(name=name, drum=False, sound=sound, notes=tuple(cleaned_note(start=float(beat), pitch=SCALE[beat % len(SCALE)]) for beat in range(BARS * BEATS_PER_BAR)))


def tidy(*tracks):
    return tidied(tracks=tracks, beats_per_bar=BEATS_PER_BAR)


class TestTidying(unittest.TestCase):
    __slots__ = ()

    def test_a_clean_song_is_left_as_it_is_with_no_doubts(self):
        kit = PlayedTrack(name=DRUMS, drum=True, sound=None, notes=tuple(cleaned_note(start=float(beat), pitch=(KICK, HAT)[beat % 2]) for beat in range(BARS * BEATS_PER_BAR)))
        tracks, doubts = tidy(melody(), kit)
        self.assertEqual(doubts, ())
        self.assertEqual([len(track.notes) for track in tracks], [len(melody().notes), len(kit.notes)])


GROOVES_BY_NAME = {groove.name: groove for groove in GROOVES}
FAR = 0.1


class TestComparing(unittest.TestCase):

    def test_a_groove_matches_itself_and_a_shuffle_differs_from_a_rock_beat(self):
        rock = GROOVES_BY_NAME[GrooveName.ROCK_BEAT]
        self.assertEqual(groove_gap(mine=rock, theirs=rock), SAME)
        self.assertGreater(groove_gap(mine=GROOVES_BY_NAME[GrooveName.SHUFFLE], theirs=rock), FAR)
        self.assertLess(groove_gap(mine=GROOVES_BY_NAME[GrooveName.ROCK_AND_OF_THREE], theirs=rock), groove_gap(mine=GROOVES_BY_NAME[GrooveName.HOUSE], theirs=rock))


DEMO = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, 'examples', 'by_genre', 'rock', 'green_men.yml')
SEED = 1


def demo_performance():
    setlist = Setlist.read_file(DEMO)
    return performance_of(setlist.get_song(setlist.get_song_names()[0]), seed=SEED)


def out_of_bounds(*, subject):
    """Return the names of the measures whose value in a subject lies outside its unit's bounds."""
    found = []
    for each in MEASURES:
        value = each.of(subject)
        bounds = each.bounds()
        if bounds is None or value is None:
            continue
        values = value if isinstance(value, tuple) else (value,)
        if any(not bounds[0] <= one <= bounds[1] for one in values):
            found.append(each.name())
    return found


class TestReadingMeasures(unittest.TestCase):

    def test_a_song_keeps_every_measure_within_its_units_bounds(self):
        profile = profile_of_performance(performance=demo_performance(), name='demo')
        self.assertEqual(out_of_bounds(subject=profile), [])


if __name__ == '__main__':
    unittest.main()
