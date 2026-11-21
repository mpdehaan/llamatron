# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The musician: a clip played by a kind of section, round the tune, with a player's touch, and what a file refuses of one."""

import unittest

from llamatron.engine.generators import musician as musician_plugin
from llamatron.engine.generators.musician import generator as musician, schema
from llamatron.engine.generators.musician.model import MusicianSetting, MusicianSettings
from llamatron.engine.timing.timing import timed_events
from llamatron.math.rational import Rational
from llamatron.model.file.song_file_error import SongFileError
from llamatron.model.schema.file_format import ClipSlotSetting, PatternSetting, Row, SceneSetting, Section, SectionKind, TrackSetting
from llamatron.model.values import midi
from tests.engine.realizer import test_registers
from tests.engine.realizer.test_registers import pattern, song
from tests.support.rendering import render_song, setlist_from_data, song_from_data

BAND = 'band'
CHORDS = 'chords'
PART = 'part'
TUNE = 'tune'
CHANGES = 'changes'
PLAYER = 'player'
CHAIN = 'played'
RENAMED = 'singer'
NOT_AN_INSTRUMENT = 'kazoo'
# A name no Musician has, inside a kind of section's own settings.
NOT_A_SETTING = 'not_a_setting'
NOT_A_SECTION = 'coda'
NOT_A_FORM = 'backwards'
EIGHTH = Rational(1, 8)
SIXTEENTH = Rational(1, 16)
QUARTER = Rational(1, 4)
HALF = Rational(1, 2)
BAR = Rational(1)
EIGHTH_STEP = '1/8'
WHOLE_STEP = '1'
# The band's part: two bars of eighths, every note as loud as the next.
STEPS = 16
WRITTEN_VELOCITY = 80
# The tune sounds through the first half of each bar and rests through the second.
TUNE_ROWS = {Row.DEGREE: [5, 5, 5, 5, None, None, None, None] * 2}
# The chords the band follows, a bar each: the first and the fourth of the scale.
CHORD_DEGREES = [1, 4]
TRIAD = 3
START = 0
LENGTH = 1
MIDI = 2
VELOCITY = 3
A_SEED = 7
ANOTHER_SEED = 8


def band_data(*, settings, rows=None, section=None, tune=False, chords=False, drum=False):
    """Return a song's data whose band track plays two bars of eighths through a chain of one musician, beside a tune and a track of chords where asked."""
    part = pattern(STEPS, **{Row.VELOCITY: [WRITTEN_VELOCITY] * STEPS, **(rows or {})})
    part[PatternSetting.STEP_SIZE] = EIGHTH_STEP
    patterns = {PART: part}
    slots = {BAND: {ClipSlotSetting.PATTERN: PART, ClipSlotSetting.CHAINS: [CHAIN]}}
    tracks = [BAND]
    if tune:
        patterns[TUNE] = {**pattern(STEPS, **TUNE_ROWS), PatternSetting.STEP_SIZE: EIGHTH_STEP}
        slots[test_registers.LEAD] = {ClipSlotSetting.PATTERN: TUNE}
        tracks.append(test_registers.LEAD)
    if chords:
        patterns[CHANGES] = {**pattern(len(CHORD_DEGREES), **{Row.DEGREE: CHORD_DEGREES, Row.CHORD: [TRIAD] * len(CHORD_DEGREES)}), PatternSetting.STEP_SIZE: WHOLE_STEP}
        slots[CHORDS] = {ClipSlotSetting.PATTERN: CHANGES}
        tracks.append(CHORDS)
    scene = {SceneSetting.TRACKS: slots}
    if section is not None:
        scene[SceneSetting.SECTION] = section
    data = song(patterns=patterns, scenes=[scene], tracks=tracks)
    if drum:
        part[PatternSetting.DRUM] = True
        data[Section.TRACKS][BAND] = {TrackSetting.DRUM: True}
    data[musician_plugin.SECTION] = {PLAYER: settings}
    data[Section.CHAINS] = {CHAIN: [{musician_plugin.NAME: PLAYER}]}
    return data


def heard(data, *, seed=None):
    """Return each note the band plays as (start, length, pitch, velocity), times in whole notes, in time order."""
    grid = render_song(song_from_data(data), seed=seed)
    column = next(column for column in grid.get_columns() if column.get_name() == BAND)
    clip = grid.get_clip(row=grid.get_rows()[0], column=column)
    return sorted((start, end - start, pitch, velocity) for start, end, pitch, velocity in timed_events(clip=clip, scale=clip.get_scale())[0])


def starts(notes):
    return [note[START] for note in notes]


def plain(**settings):
    """Return the settings of a bassist, who gives way to nobody and plays its notes as written, with the settings given."""
    return {MusicianSetting.INSTRUMENT: schema.BASSIST, **settings}


def in_section(*, played=None, plays=None):
    own = {}
    if played is not None:
        own[schema.PLAYED] = played
    if plays is not None:
        own[schema.PLAYS] = plays
    return plain(**{MusicianSetting.BY_SECTION: {SectionKind.VERSE: own}})


class TestMusicianBySection(unittest.TestCase):

    def test_a_musician_with_nothing_set_plays_the_part_as_written(self):
        notes = heard(band_data(settings=plain()))
        self.assertEqual(starts(notes), [step * EIGHTH for step in range(STEPS)])
        self.assertEqual({note[VELOCITY] for note in notes}, {WRITTEN_VELOCITY})
        self.assertEqual({note[LENGTH] for note in notes}, {EIGHTH})

    def test_a_musician_who_does_not_play_a_kind_of_section_rests_there_and_plays_elsewhere(self):
        self.assertEqual(heard(band_data(settings=in_section(plays=False), section=SectionKind.VERSE)), [])
        self.assertEqual(len(heard(band_data(settings=in_section(plays=False), section=SectionKind.CHORUS))), STEPS)
        self.assertEqual(len(heard(band_data(settings=in_section(plays=False)))), STEPS)

    def test_softer_plays_every_note_softer(self):
        notes = heard(band_data(settings=in_section(played=schema.SOFTER), section=SectionKind.VERSE))
        self.assertEqual(len(notes), STEPS)
        self.assertEqual({note[VELOCITY] for note in notes}, {WRITTEN_VELOCITY - musician.SOFTER_DEPTH})

    def test_thinned_keeps_the_notes_on_the_beats(self):
        notes = heard(band_data(settings=in_section(played=schema.THINNED), section=SectionKind.VERSE))
        self.assertEqual(starts(notes), [beat * QUARTER for beat in range(8)])

    def test_head_only_plays_the_first_bar_of_every_two(self):
        notes = heard(band_data(settings=in_section(played=schema.HEAD_ONLY), section=SectionKind.VERSE))
        self.assertEqual(starts(notes), [step * EIGHTH for step in range(8)])

    def test_muted_plays_every_note_short_and_softer(self):
        notes = heard(band_data(settings=in_section(played=schema.MUTED), section=SectionKind.VERSE))
        self.assertEqual(len(notes), STEPS)
        self.assertEqual({note[LENGTH] for note in notes}, {SIXTEENTH})
        self.assertEqual({note[VELOCITY] for note in notes}, {WRITTEN_VELOCITY - musician.MUTED_DEPTH})

    def test_hits_plays_the_first_note_of_each_bar(self):
        notes = heard(band_data(settings=in_section(played=schema.HITS), section=SectionKind.VERSE))
        self.assertEqual(starts(notes), [0, BAR])


class TestMusicianTouch(unittest.TestCase):

    def test_a_sparse_player_keeps_the_halves_of_the_bar_and_a_light_one_the_beats(self):
        self.assertEqual(starts(heard(band_data(settings=plain(**{MusicianSetting.ACTIVITY: schema.SPARSE})))), [half * HALF for half in range(4)])
        self.assertEqual(starts(heard(band_data(settings=plain(**{MusicianSetting.ACTIVITY: schema.LIGHT})))), [beat * QUARTER for beat in range(8)])

    def test_a_busy_player_leaves_eighths_alone_and_a_very_busy_one_strikes_each_twice(self):
        self.assertEqual(len(heard(band_data(settings=plain(**{MusicianSetting.ACTIVITY: schema.BUSY})))), STEPS)
        notes = heard(band_data(settings=plain(**{MusicianSetting.ACTIVITY: schema.VERY_BUSY})))
        self.assertEqual(starts(notes), [step * SIXTEENTH for step in range(STEPS * 2)])

    def test_loudness_moves_every_note_by_steps(self):
        notes = heard(band_data(settings=plain(**{MusicianSetting.LOUDNESS: 2})))
        self.assertEqual({note[VELOCITY] for note in notes}, {WRITTEN_VELOCITY + 2 * musician.LOUDNESS_STEP})
        notes = heard(band_data(settings=plain(**{MusicianSetting.LOUDNESS: schema.QUIETEST})))
        self.assertEqual({note[VELOCITY] for note in notes}, {WRITTEN_VELOCITY + schema.QUIETEST * musician.LOUDNESS_STEP})

    def test_a_loose_player_wanders_within_reach_and_the_same_seed_plays_the_same(self):
        data = band_data(settings=plain(**{MusicianSetting.LOOSENESS: schema.LOOSEST}))
        notes = heard(data, seed=A_SEED)
        reach = schema.LOOSEST * musician.LOOSENESS_STEP
        self.assertGreater(len({note[VELOCITY] for note in notes}), 1)
        self.assertTrue(all(abs(note[VELOCITY] - WRITTEN_VELOCITY) <= reach for note in notes))
        self.assertEqual(notes, heard(data, seed=A_SEED))
        self.assertNotEqual(notes, heard(data, seed=ANOTHER_SEED))

    def test_accents_lean_on_the_downbeat_the_backbeat_or_the_offbeats(self):
        def leaned(accents):
            return [note[START] for note in heard(band_data(settings=plain(**{MusicianSetting.ACCENTS: accents}))) if note[VELOCITY] == WRITTEN_VELOCITY + musician.ACCENT_DEPTH]
        self.assertEqual(leaned(schema.DOWNBEAT), [0, BAR])
        self.assertEqual(leaned(schema.BACKBEAT), [QUARTER, 3 * QUARTER, BAR + QUARTER, BAR + 3 * QUARTER])
        self.assertEqual(leaned(schema.OFFBEATS), [EIGHTH + beat * QUARTER for beat in range(8)])

    def test_short_notes_stay_short_and_held_notes_reach_the_next(self):
        on_beats = {Row.DEGREE: [1, None] * (STEPS // 2)}
        self.assertEqual({note[LENGTH] for note in heard(band_data(settings=plain(), rows=on_beats))}, {EIGHTH})
        held = heard(band_data(settings=plain(**{MusicianSetting.NOTES: schema.HELD_NOTES}), rows=on_beats))
        self.assertEqual({note[LENGTH] for note in held[:-1]}, {QUARTER})
        quarters = {Row.DEGREE: [1, None] * (STEPS // 2), Row.TIE: [False, True] * (STEPS // 2)}
        short = heard(band_data(settings=plain(**{MusicianSetting.NOTES: schema.SHORT_NOTES}), rows=quarters))
        self.assertEqual({note[LENGTH] for note in short}, {musician.SHORT_NOTE})

    def test_an_organ_holds_its_notes_unasked_and_a_horn_section_plays_them_short(self):
        on_beats = {Row.DEGREE: [1, None] * (STEPS // 2), Row.OCTAVE: [4, None] * (STEPS // 2)}
        organ = heard(band_data(settings={MusicianSetting.INSTRUMENT: schema.BACKING_ORGAN}, rows=on_beats))
        self.assertEqual({note[LENGTH] for note in organ[:-1]}, {QUARTER})
        as_written = heard(band_data(settings={MusicianSetting.INSTRUMENT: schema.BACKING_ORGAN, MusicianSetting.NOTES: schema.AS_WRITTEN}, rows=on_beats))
        self.assertEqual({note[LENGTH] for note in as_written}, {EIGHTH})

    def test_range_moves_the_part_an_octave_inside_the_instrument(self):
        piano = {MusicianSetting.INSTRUMENT: schema.BACKING_PIANO}
        written = heard(band_data(settings=piano))
        high = heard(band_data(settings={**piano, MusicianSetting.RANGE: schema.HIGH}))
        low = heard(band_data(settings={**piano, MusicianSetting.RANGE: schema.LOW}))
        self.assertEqual([note[MIDI] for note in high], [note[MIDI] + midi.HALF_STEPS_PER_OCTAVE for note in written])
        self.assertEqual([note[MIDI] for note in low], [note[MIDI] - midi.HALF_STEPS_PER_OCTAVE for note in written])
        lowest = musician.MUSICIANS[schema.LEAD_GUITARIST].LOWEST
        guitar = heard(band_data(settings={MusicianSetting.INSTRUMENT: schema.LEAD_GUITARIST, MusicianSetting.RANGE: schema.LOW}))
        self.assertTrue(all(note[MIDI] >= lowest for note in guitar))


class TestMusicianRoundTheBand(unittest.TestCase):

    def test_a_player_in_the_gaps_is_silent_while_the_tune_sounds(self):
        notes = heard(band_data(settings=plain(**{MusicianSetting.TUNE_FROM: test_registers.LEAD, MusicianSetting.GIVES_WAY: schema.IN_THE_GAPS}), tune=True))
        self.assertEqual(starts(notes), [bar * BAR + HALF + step * EIGHTH for bar in range(2) for step in range(4)])

    def test_a_lead_guitarist_plays_in_the_gaps_unasked_and_a_bassist_gives_way_to_nobody(self):
        guitar = heard(band_data(settings={MusicianSetting.INSTRUMENT: schema.LEAD_GUITARIST, MusicianSetting.TUNE_FROM: test_registers.LEAD}, rows={Row.OCTAVE: [5] * STEPS}, tune=True))
        self.assertEqual(len(guitar), STEPS // 2)
        self.assertEqual(len(heard(band_data(settings=plain(**{MusicianSetting.TUNE_FROM: test_registers.LEAD}), tune=True))), STEPS)

    def test_giving_way_a_little_is_softer_under_the_tune_and_a_lot_also_leaves_the_beats_alone(self):
        little = heard(band_data(settings=plain(**{MusicianSetting.TUNE_FROM: test_registers.LEAD, MusicianSetting.GIVES_WAY: schema.GIVES_WAY_SOME}), tune=True))
        self.assertEqual(len(little), STEPS)
        under = [note[VELOCITY] for note in little if note[START] - (note[START] // BAR) * BAR < HALF]
        clear = [note[VELOCITY] for note in little if note[START] - (note[START] // BAR) * BAR >= HALF]
        self.assertEqual(set(under), {WRITTEN_VELOCITY - musician.SOFTER_UNDER_TUNE[schema.GIVES_WAY_SOME]})
        self.assertEqual(set(clear), {WRITTEN_VELOCITY})
        lot = heard(band_data(settings=plain(**{MusicianSetting.TUNE_FROM: test_registers.LEAD, MusicianSetting.GIVES_WAY: schema.GIVES_WAY_OFTEN}), tune=True))
        self.assertEqual(starts(lot)[:6], [0, QUARTER, HALF, HALF + EIGHTH, HALF + QUARTER, HALF + QUARTER + EIGHTH])

    def test_with_no_tune_track_named_nobody_gives_way(self):
        notes = heard(band_data(settings=plain(**{MusicianSetting.GIVES_WAY: schema.IN_THE_GAPS}), tune=True))
        self.assertEqual(len(notes), STEPS)

    def test_the_notes_follow_the_chords_of_the_track_named(self):
        alone = heard(band_data(settings=plain(), chords=True))
        followed = heard(band_data(settings=plain(**{MusicianSetting.CHORDS_FROM: CHORDS}), chords=True))
        self.assertEqual([note[MIDI] for note in followed[:8]], [note[MIDI] for note in alone[:8]])
        self.assertEqual(len({note[MIDI] for note in followed[8:]}), 1)
        self.assertNotEqual(followed[8][MIDI], alone[8][MIDI])

    def test_a_drummers_notes_follow_no_chords(self):
        settings = {MusicianSetting.INSTRUMENT: schema.DRUMMER, MusicianSetting.CHORDS_FROM: CHORDS}
        notes = heard(band_data(settings=settings, chords=True, drum=True, rows={Row.DEGREE: ['C'] * STEPS}))
        self.assertEqual(len({note[MIDI] for note in notes}), 1)
        self.assertEqual(len(notes), STEPS)

    def test_renaming_the_tune_track_is_followed(self):
        setlist = setlist_from_data(band_data(settings=plain(**{MusicianSetting.TUNE_FROM: test_registers.LEAD, MusicianSetting.CHORDS_FROM: CHORDS}), tune=True, chords=True))
        made = setlist.get_songs()[0]
        made.rename_item(section=Section.TRACKS, old=test_registers.LEAD, new=RENAMED)
        settings = made.get_generator_settings(kind=musician_plugin.NAME, name=PLAYER)
        self.assertEqual(settings.get_tune_from(), RENAMED)
        self.assertEqual(settings.get_chords_from(), CHORDS)


class TestMusicianSettings(unittest.TestCase):

    def test_a_file_refuses_an_instrument_or_a_form_nobody_knows(self):
        for settings in (
            {MusicianSetting.INSTRUMENT: NOT_AN_INSTRUMENT},
            plain(**{MusicianSetting.BY_SECTION: {SectionKind.VERSE: {schema.PLAYED: NOT_A_FORM}}}), plain(**{MusicianSetting.BY_SECTION: {SectionKind.VERSE: {schema.PLAYS: NOT_A_FORM}}}),
            plain(**{MusicianSetting.LOUDNESS: schema.LOUDEST + 1}), plain(**{MusicianSetting.LOOSENESS: schema.TIGHT - 1}),
        ):
            with self.subTest(settings=settings), self.assertRaises(SongFileError):
                setlist_from_data(band_data(settings=settings))

    def test_a_kind_of_section_or_a_setting_of_one_nobody_knows_is_passed_over_and_never_written_again(self):
        # As a file saved before one was taken away, or by a later version, may hold them: the set opens and what is known stays.
        by_section = {SectionKind.VERSE: {schema.PLAYED: schema.SOFTER, NOT_A_SETTING: 1}, NOT_A_SECTION: {schema.PLAYED: schema.MUTED}}
        setlist = setlist_from_data(band_data(settings=plain(**{MusicianSetting.BY_SECTION: by_section})))
        settings = setlist.get_songs()[0].get_generator_settings(kind=musician_plugin.NAME, name=PLAYER)
        self.assertEqual(settings.to_data()[MusicianSetting.BY_SECTION], {SectionKind.VERSE: {schema.PLAYED: schema.SOFTER}})

    def test_a_section_setting_back_to_what_a_section_does_unasked_is_left_out(self):
        settings = MusicianSettings.new()
        settings.set_section_own(section=SectionKind.VERSE, name=schema.PLAYED, value=schema.HITS)
        self.assertEqual(settings.get_for(section=SectionKind.VERSE, name=schema.PLAYED), schema.HITS)
        self.assertEqual(settings.get_for(section=SectionKind.CHORUS, name=schema.PLAYED), schema.WHOLE)
        settings.set_section_own(section=SectionKind.VERSE, name=schema.PLAYED, value=None)
        self.assertEqual(settings.to_data(), {})

    def test_every_instrument_has_a_musician_who_plays_a_part(self):
        for instrument in schema.INSTRUMENTS:
            with self.subTest(instrument=instrument):
                self.assertTrue(heard(band_data(settings={MusicianSetting.INSTRUMENT: instrument}, rows={Row.OCTAVE: [4] * STEPS})))
