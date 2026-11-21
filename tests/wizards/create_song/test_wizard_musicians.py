# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The musicians of a song the wizard makes: which musician each player of the band is, the Musician every clip of a player runs first, and a player's Musician of the person's own."""

import unittest

from llamatron.engine.generators.musician import generator as musician
from llamatron.engine.generators.musician.settings import MusicianSetting
from llamatron.model.schema.file_format import ClipSlotSetting, GeneratorKind, Section
from llamatron.wizards.create_song import band, players
from llamatron.wizards.create_song.wizard_choices import WizardChoices

A_GENRE = 'rock'
A_SUBGENRE = 'arena rock'
A_GENRE_OF_MACHINES = 'electronic'
A_SEED = 7
A_TRACK = 'keys'
THE_TUNE = 'lead'
THE_BASS = 'bass'
THE_DRUMS = 'drums'
NOT_A_FORM = 'backwards'
NOT_A_SETTING = 'hat size'
# A General MIDI sound's number in each family, and one of no family that names a musician.
A_PIANO = 1
AN_ORGAN = 17
A_GUITAR = 26
SOME_STRINGS = 49
A_CHOIR = 53
A_TRUMPET = 57
A_SYNTH_PAD = 90
A_KALIMBA = 109


def chosen(*, genre=A_GENRE, subgenre=A_SUBGENRE):
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre or choices.subgenres()[0])
    choices.set_seed(A_SEED)
    return choices


def member(*, player=players.KEYS, backing=True, answers=False, sound=None):
    return band.BandMember(track=A_TRACK, player=player, backing=backing, answers=answers, sound=sound)


def made_song(choices):
    setlist, name = choices.made_for_listening()
    return setlist.get_song(name)


class TestBand(unittest.TestCase):

    def test_a_backing_player_is_the_musician_of_the_sound_played(self):
        for sound, instrument in (
            (A_PIANO, musician.BACKING_PIANO), (AN_ORGAN, musician.BACKING_ORGAN), (A_GUITAR, musician.RHYTHM_GUITARIST), (SOME_STRINGS, musician.STRING_SECTION),
            (A_CHOIR, musician.BACKUP_SINGERS), (A_TRUMPET, musician.HORN_SECTION), (A_SYNTH_PAD, musician.BACKING_SYNTH),
        ):
            with self.subTest(sound=sound):
                self.assertEqual(band.instrument_of(member(sound=sound)), instrument)

    def test_a_player_of_lines_is_the_lead_of_the_sound_played(self):
        for sound, instrument in ((A_PIANO, musician.LEAD_PIANO), (AN_ORGAN, musician.LEAD_ORGAN), (A_GUITAR, musician.LEAD_GUITARIST), (A_SYNTH_PAD, musician.LEAD_SYNTH)):
            with self.subTest(sound=sound):
                self.assertEqual(band.instrument_of(member(backing=False, sound=sound)), instrument)

    def test_a_sound_that_names_no_musician_leaves_it_to_the_players_instrument_in_the_band(self):
        self.assertEqual(band.instrument_of(member(player=players.KEYS, sound=A_KALIMBA)), musician.BACKING_PIANO)
        self.assertEqual(band.instrument_of(member(player=players.RHYTHM, sound=None)), musician.RHYTHM_GUITARIST)
        self.assertEqual(band.instrument_of(member(player=players.SESSION, sound=A_KALIMBA)), musician.BACKING_SYNTH)
        self.assertEqual(band.instrument_of(member(player=players.LEAD, backing=False, sound=A_KALIMBA)), musician.LEAD_GUITARIST)
        self.assertEqual(band.instrument_of(member(player=players.SESSION, backing=False, sound=A_KALIMBA)), musician.LEAD_SYNTH)

    def test_the_bass_player_is_a_bassist_and_a_player_who_answers_is_an_answering_player(self):
        self.assertEqual(band.instrument_of(member(player=players.BASS, sound=AN_ORGAN)), musician.BASSIST)
        self.assertEqual(band.instrument_of(member(player=players.SESSION, backing=False, answers=True, sound=A_GUITAR)), musician.ANSWERING_PLAYER)

    def test_a_player_of_lines_gives_way_to_nobody_and_plays_the_notes_as_written(self):
        self.assertEqual(band.usual_musician(member(backing=False, sound=AN_ORGAN)),
                         {MusicianSetting.INSTRUMENT: musician.LEAD_ORGAN, MusicianSetting.GIVES_WAY: musician.NO_GIVING_WAY, MusicianSetting.NOTES: musician.AS_WRITTEN})
        self.assertEqual(band.usual_musician(member(backing=False, answers=True, sound=A_GUITAR)), {MusicianSetting.INSTRUMENT: musician.ANSWERING_PLAYER, MusicianSetting.GIVES_WAY: musician.GIVES_WAY_SOME})

    def test_a_backing_player_keeps_the_instruments_habits_but_for_the_horns_short_notes(self):
        self.assertEqual(band.usual_musician(member(sound=AN_ORGAN)), {MusicianSetting.INSTRUMENT: musician.BACKING_ORGAN})
        self.assertEqual(band.usual_musician(member(sound=A_TRUMPET)), {MusicianSetting.INSTRUMENT: musician.HORN_SECTION, MusicianSetting.NOTES: musician.AS_WRITTEN})

    def test_everyone_hears_the_tune_but_its_own_player_and_the_drummer_plays_every_piece(self):
        members = [band.BandMember(track=THE_TUNE, player=players.LEAD, backing=False, answers=False, sound=A_GUITAR), member(sound=AN_ORGAN)]
        musicians, of_track = band.band_of(members=members, drummer=THE_DRUMS, drum_tracks=['kick', 'snare'], tune_track=THE_TUNE, own={})
        self.assertNotIn(MusicianSetting.TUNE_FROM, musicians[band.musician_name(THE_TUNE)])
        self.assertEqual(musicians[band.musician_name(A_TRACK)][MusicianSetting.TUNE_FROM], THE_TUNE)
        self.assertEqual(musicians[band.musician_name(THE_DRUMS)], {MusicianSetting.INSTRUMENT: musician.DRUMMER, MusicianSetting.TUNE_FROM: THE_TUNE})
        self.assertEqual({of_track['kick'], of_track['snare']}, {band.musician_name(THE_DRUMS)})

    def test_a_songs_own_musician_takes_the_usual_ones_place_and_still_hears_the_tune(self):
        own = {A_TRACK: {MusicianSetting.INSTRUMENT: musician.BACKING_PIANO, MusicianSetting.LOUDNESS: musician.LOUDEST}}
        musicians, _ = band.band_of(members=[member(sound=AN_ORGAN)], drummer=None, drum_tracks=[], tune_track=THE_TUNE, own=own)
        self.assertEqual(musicians[band.musician_name(A_TRACK)], {**own[A_TRACK], MusicianSetting.TUNE_FROM: THE_TUNE})


class TestWizardMusicians(unittest.TestCase):

    def test_every_clip_of_a_player_runs_the_players_musician_first(self):
        choices = chosen()
        self.assertTrue(choices.get_band().has_musicians())
        song = made_song(choices)
        drum_tracks = {track for track in song.get_track_names() if song.get_track(track).is_drum()}
        seen = set()
        for scene in song.get_scenes():
            for track in song.get_track_names():
                if not scene.has_clip_slot(track) or song.get_track(track).is_muted():
                    continue
                chains = scene.get_clip_slot(track).to_data().get(ClipSlotSetting.CHAINS, [])
                wanted = choices.player(THE_DRUMS if track in drum_tracks else track).musician_name()
                first = song.get_setlist().get_chain(chains[0]).get_steps()[0]
                self.assertEqual((first.kind, first.name), (GeneratorKind.MUSICIAN, wanted), (scene.get_name(), track))
                seen.add(wanted)
        for name in seen:
            self.assertTrue(song.has_generator(kind=GeneratorKind.MUSICIAN, name=name))
        self.assertIn(choices.player(THE_BASS).musician_name(), seen)
        self.assertIn(choices.player(THE_DRUMS).musician_name(), seen)

    def test_a_song_of_machines_has_no_musicians(self):
        choices = chosen(genre=A_GENRE_OF_MACHINES, subgenre=None)
        self.assertFalse(choices.get_band().has_musicians())
        setlist, _ = choices.made_for_listening()
        self.assertFalse(setlist.to_data().get(Section.MUSICIANS))

    def test_a_players_own_musician_is_kept_and_played_until_the_player_is_given_back_the_usual_one(self):
        choices = chosen()
        self.assertIsNone(choices.player(THE_BASS).get_musician())
        usual = made_song(choices).get_generator_settings(kind=GeneratorKind.MUSICIAN, name=choices.player(THE_BASS).musician_name()).to_data()
        own = {MusicianSetting.INSTRUMENT: musician.BASSIST, MusicianSetting.LOUDNESS: musician.LOUDEST}
        choices.player(THE_BASS).set_musician(settings={**own, MusicianSetting.TUNE_FROM: A_TRACK, MusicianSetting.CHORDS_FROM: A_TRACK})
        self.assertEqual(choices.player(THE_BASS).get_musician(), own)
        self.assertEqual(WizardChoices.from_data(choices.to_data()).player(THE_BASS).get_musician(), own)
        made = made_song(choices).get_generator_settings(kind=GeneratorKind.MUSICIAN, name=choices.player(THE_BASS).musician_name())
        self.assertEqual(made.get_own(MusicianSetting.LOUDNESS), musician.LOUDEST)
        self.assertEqual(made.get_tune_from(), usual.get(MusicianSetting.TUNE_FROM))
        self.assertIsNone(made.get_chords_from())
        choices.player(THE_BASS).set_musician(settings=None)
        self.assertIsNone(choices.player(THE_BASS).get_musician())
        self.assertEqual(made_song(choices).get_generator_settings(kind=GeneratorKind.MUSICIAN, name=choices.player(THE_BASS).musician_name()).to_data(), usual)

    def test_settings_no_musician_has_are_refused_and_nothing_changes(self):
        choices = chosen()
        for wrong in ({MusicianSetting.ACTIVITY: NOT_A_FORM}, {NOT_A_SETTING: musician.BUSY}):
            with self.assertRaises(ValueError):
                choices.player(THE_BASS).set_musician(settings=wrong)
        self.assertIsNone(choices.player(THE_BASS).get_musician())
