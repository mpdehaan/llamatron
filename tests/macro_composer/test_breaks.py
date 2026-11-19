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

"""Drum breaks: the breaks as written, a break cut up, a song that plays one, and the wizard's choice of a break and its cut."""

import random
import unittest

from llamatron.composition import limits
from llamatron.composition.file_format import InstrumentSetting, Section
from llamatron.macro_composer import arranger, breaks, characters, notation, wizard_limits
from llamatron.macro_composer.wizard_choices import WizardChoices
from llamatron.strings import errors, macro_composer as composer_text
from llamatron.support import version

ROCK = 'rock'
ROCK_KIND = 'british invasion'
BALLAD = 'six-eight ballad'
ELECTRONIC = 'electronic'
BUILT_ON_A_BREAK = 'big beat'
EXPERIMENTAL = 'experimental'
SONG_NAME = 'a_song'
KEY_ROOT = 'A'
MAJOR = 'major'
SEED = 5
OTHER_SEED = 6
SEEDS = range(1, 21)
NO_SUCH = 'polka break'
FORM = ['verse', 'chorus']
VERSE = 'verse'
# A break has at least this many kinds of drum, and a bar of one starts on a kick.
FEWEST_DRUMS = 3
A_CUT = 5
REFUSED_CUTS = (0, breaks.MOST_CUT + 1, True, 'far', 2.5)
PERCUSSION = 'percussion'
# The first drummer of the rock style plays with no fill and nothing added, so a part of theirs is the break and no more.
PLAINEST = 1
PHRASE = 4
COWBELL = 'cowbell'
A_SOUND = 106
A_NOTE = 53
RAW = 'raw'


def a_song(*, picks=None, template=ROCK_KIND, seed=SEED):
    return {arranger.NAME: SONG_NAME, arranger.TITLE: SONG_NAME, arranger.STYLE: ROCK, arranger.TEMPLATE: template, arranger.KEY: {arranger.ROOT: KEY_ROOT, arranger.TYPE: MAJOR},
            arranger.SEED: seed, arranger.FORM: list(FORM), arranger.PICKS: picks or {}, arranger.PLAYERS: {arranger.DRUMS: PLAINEST}, arranger.FILLS_COME: 0}


def slices_of(bars):
    return [breaks.sliced(bars=bars, slice_at=slice_at) for slice_at in range(breaks.SLICES)]


def wizard(*, genre=ROCK, subgenre=ROCK_KIND, seed=SEED):
    choices = WizardChoices()
    choices.set_genre(genre)
    choices.set_subgenre(subgenre)
    choices.set_seed(seed)
    return choices


def patterns_of(choices):
    return choices.made_setlist(name=SONG_NAME, version=version.VERSION).to_data()[Section.PATTERNS]


class TestBreaks(unittest.TestCase):
    """The breaks as written and a break cut up."""

    def test_every_break_is_a_bar_of_drums_the_kit_has_starting_on_a_kick_and_no_two_are_alike(self):
        self.assertGreaterEqual(len(breaks.break_names()), 6)
        for name, bars in breaks.BREAKS.items():
            with self.subTest(name=name):
                self.assertGreaterEqual(len(bars), FEWEST_DRUMS)
                self.assertEqual(bars[breaks.KICK][0], notation.LOUD)
                self.assertIn(notation.LOUD, bars[breaks.SNARE])
                for piece, hits in bars.items():
                    self.assertIn(piece, notation.KIT)
                    self.assertEqual(len(hits), breaks.STEPS_IN_BAR)
                    self.assertLessEqual(set(hits), {notation.LOUD, notation.SOFT, notation.NONE})
        written = list(breaks.BREAKS.values())
        for place, bars in enumerate(written):
            self.assertNotIn(bars, written[:place])

    def test_the_least_cut_is_the_break_as_written(self):
        for bars in breaks.BREAKS.values():
            self.assertEqual(breaks.cut_up(bars=bars, cut=breaks.LEAST_CUT, dice=random.Random(SEED)), bars)

    def test_each_further_cut_changes_one_slice_more_and_never_the_first_and_every_drum_is_cut_alike(self):
        for name, bars in breaks.BREAKS.items():
            for seed in SEEDS:
                for cut in range(breaks.LEAST_CUT, breaks.MOST_CUT + 1):
                    made = breaks.cut_up(bars=bars, cut=cut, dice=random.Random(seed))
                    changed = [place for place, (was, now) in enumerate(zip(slices_of(bars), slices_of(made))) if was != now]
                    with self.subTest(name=name, seed=seed, cut=cut):
                        self.assertEqual(len(changed), cut - breaks.LEAST_CUT)
                        self.assertNotIn(0, changed)
                        # A slice of the cut bar is a slice of the break, whole: what the drums played together stays together.
                        for now in slices_of(made):
                            self.assertIn(now, slices_of(bars))

    def test_the_same_dice_cut_the_same_way_and_other_dice_another(self):
        bars = breaks.BREAKS[breaks.TUMBLING]
        self.assertEqual(breaks.cut_up(bars=bars, cut=A_CUT, dice=random.Random(SEED)), breaks.cut_up(bars=bars, cut=A_CUT, dice=random.Random(SEED)))
        self.assertTrue(any(breaks.cut_up(bars=bars, cut=A_CUT, dice=random.Random(seed)) != breaks.cut_up(bars=bars, cut=A_CUT, dice=random.Random(SEED)) for seed in SEEDS))


class TestSongWithABreak(unittest.TestCase):
    """A song whose picks name a break: the arranger plays the break in place of the kick's, the snare's and the cymbal's ways."""

    @classmethod
    def setUpClass(cls):
        cls.style = arranger.style_named(ROCK)

    def parts(self, song):
        return arranger.arranged(style=self.style, song=song)[arranger.PARTS]

    def bars_of(self, *, song, piece):
        """A drum's part over a phrase as bars of sixteen hits, from a drummer who adds nothing and plays no fill."""
        picks = arranger.picked(style=self.style, song=song)
        parts = arranger.drum_parts(style=self.style, picks=picks, roles=self.style[arranger.ROLES], meter=arranger.COMMON_TIME, phrase_bars=PHRASE,
                                    drummer={characters.FILL_EVERY: 0}, section_bars=PHRASE, seed=song[arranger.SEED])
        hits = arranger.widened(hits=parts[piece][notation.HITS], to=PHRASE * breaks.STEPS_IN_BAR)
        return [hits[start:start + breaks.STEPS_IN_BAR] for start in range(0, len(hits), breaks.STEPS_IN_BAR)]

    def test_a_song_with_no_break_plays_as_ever(self):
        self.assertEqual(self.parts(a_song()), self.parts(a_song(picks={arranger.BREAK: arranger.NO_BREAK})))

    def test_each_break_is_the_first_bar_of_the_drums_and_no_two_make_the_same_song(self):
        made = []
        for name, bars in breaks.BREAKS.items():
            song = a_song(picks={arranger.BREAK: name})
            for piece, hits in bars.items():
                with self.subTest(name=name, piece=piece):
                    self.assertEqual(self.bars_of(song=song, piece=piece)[0], hits)
            self.assertNotIn(self.parts(song), made)
            made.append(self.parts(song))

    def test_uncut_every_bar_is_the_break_and_cut_the_later_bars_of_a_phrase_are_cut_each_its_own_way(self):
        bars = breaks.BREAKS[breaks.TUMBLING]
        uncut = self.bars_of(song=a_song(picks={arranger.BREAK: breaks.TUMBLING}), piece=breaks.KICK)
        self.assertEqual(uncut, [bars[breaks.KICK]] * len(uncut))
        song = a_song(picks={arranger.BREAK: breaks.TUMBLING, arranger.BREAK_CUT: breaks.MOST_CUT})
        snare = self.bars_of(song=song, piece=breaks.SNARE)
        self.assertEqual(len(snare), PHRASE)
        self.assertEqual(snare[0], bars[breaks.SNARE])
        self.assertNotIn(bars[breaks.SNARE], snare[1:])
        self.assertGreater(len({tuple(bar) for bar in snare}), 2)

    def test_a_cut_goes_by_the_songs_seed(self):
        picks = {arranger.BREAK: breaks.ROLLING, arranger.BREAK_CUT: A_CUT}
        self.assertEqual(self.parts(a_song(picks=picks)), self.parts(a_song(picks=picks)))
        self.assertNotEqual(self.parts(a_song(picks=picks))[breaks.SNARE], self.parts(a_song(picks=picks, seed=OTHER_SEED))[breaks.SNARE])

    def test_a_break_leaves_the_percussion_and_drops_what_only_the_other_ways_played(self):
        with_percussion = next(value for value, entry in arranger.values_of(style=self.style, trait=PERCUSSION).items() if entry.get(arranger.BAR))
        piece = next(iter(arranger.values_of(style=self.style, trait=PERCUSSION)[with_percussion][arranger.BAR]))
        parts = self.parts(a_song(picks={arranger.BREAK: breaks.LAZY, PERCUSSION: with_percussion}))
        self.assertEqual(set(parts) & set(notation.KIT), {piece, *breaks.BREAKS[breaks.LAZY]})

    def test_a_break_is_not_played_in_another_meter(self):
        self.assertEqual(self.parts(a_song(template=BALLAD)), self.parts(a_song(template=BALLAD, picks={arranger.BREAK: breaks.TUMBLING})))

    def test_a_break_and_a_cut_there_is_none_of_are_refused(self):
        with self.assertRaises(ValueError) as refused:
            self.parts(a_song(picks={arranger.BREAK: NO_SUCH}))
        self.assertEqual(str(refused.exception), errors.ERR_NO_SUCH_BREAK.format(NO_SUCH, arranger.listed(breaks.BREAKS)))
        for cut in REFUSED_CUTS:
            with self.assertRaises(ValueError) as refused:
                self.parts(a_song(picks={arranger.BREAK: breaks.TUMBLING, arranger.BREAK_CUT: cut}))
            self.assertEqual(str(refused.exception), errors.ERR_BREAK_CUT.format(breaks.LEAST_CUT, breaks.MOST_CUT, cut))


class TestWizardBreak(unittest.TestCase):
    """The wizard's choice of a break and of how far it is cut up."""

    def drums(self, choices):
        return next(role for role in choices.roles() if not choices.has_sound(role))

    def test_a_song_in_common_time_with_drums_is_offered_every_break_and_starts_with_none(self):
        choices = wizard()
        self.assertEqual(choices.breaks(), breaks.break_names())
        self.assertIsNone(choices.get_break())
        self.assertEqual(choices.get_break_cut(), breaks.LEAST_CUT)

    def test_no_break_is_offered_before_a_subgenre_in_another_meter_or_to_a_band_with_no_drums(self):
        self.assertEqual(WizardChoices().breaks(), [])
        self.assertEqual(wizard(subgenre=BALLAD).breaks(), [])
        without_drums = WizardChoices()
        without_drums.set_genre(EXPERIMENTAL)
        without_drums.set_subgenre(without_drums.subgenres()[0])
        self.assertEqual(without_drums.breaks(), [])

    def test_a_subgenre_built_on_a_break_starts_with_its_own_and_none_can_be_chosen(self):
        choices = wizard(genre=ELECTRONIC, subgenre=BUILT_ON_A_BREAK)
        own = choices.get_break()
        self.assertIn(own, breaks.break_names())
        with_break = patterns_of(choices)
        choices.set_break(None)
        self.assertIsNone(choices.get_break())
        self.assertNotEqual(patterns_of(choices), with_break)
        again = WizardChoices.from_data(choices.to_data())
        self.assertIsNone(again.get_break())
        self.assertEqual(patterns_of(again), patterns_of(choices))

    def test_a_break_takes_the_place_of_every_way_of_the_drums_but_the_percussions(self):
        choices = wizard()
        drums = self.drums(choices)
        before = choices.role_traits(drums)
        self.assertGreater(len(before), 1)
        choices.set_break(breaks.TUMBLING)
        self.assertEqual(choices.role_traits(drums), [trait for trait in before if trait == PERCUSSION])
        choices.set_break(None)
        self.assertEqual(choices.role_traits(drums), before)

    def test_every_break_and_every_cut_makes_a_song_of_its_own_and_both_are_kept(self):
        made = [patterns_of(wizard())]
        for name in breaks.break_names():
            for cut in range(breaks.LEAST_CUT, breaks.MOST_CUT + 1):
                choices = wizard()
                choices.set_break(name)
                choices.set_break_cut(cut)
                with self.subTest(name=name, cut=cut):
                    self.assertNotIn(patterns_of(choices), made)
                made.append(patterns_of(choices))
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.get_break(), name)
        self.assertEqual(again.get_break_cut(), cut)
        self.assertEqual(patterns_of(again), patterns_of(choices))

    def test_a_break_there_is_none_of_and_a_cut_out_of_range_are_refused(self):
        choices = wizard()
        with self.assertRaises(ValueError) as refused:
            choices.set_break(NO_SUCH)
        self.assertEqual(str(refused.exception), errors.ERR_WIZARD_NO_SUCH_BREAK.format(value=NO_SUCH))
        for cut in REFUSED_CUTS:
            with self.assertRaises(ValueError) as refused:
                choices.set_break_cut(cut)
            self.assertEqual(str(refused.exception), errors.ERR_WIZARD_BREAK_CUT.format(low=breaks.LEAST_CUT, high=breaks.MOST_CUT, value=cut))
        with self.assertRaises(ValueError):
            wizard(subgenre=BALLAD).set_break(breaks.TUMBLING)

    def test_a_kept_break_that_no_longer_fits_is_left_out(self):
        kept = wizard()
        kept.set_break(breaks.TUMBLING)
        data = {**kept.to_data(), 'break': NO_SUCH}
        self.assertIsNone(WizardChoices.from_data(data).get_break())


class TestKitPieceSounds(unittest.TestCase):
    """A piece of the kit that sounds as another drum, or as a General MIDI sound on one note."""

    @classmethod
    def setUpClass(cls):
        cls.style = arranger.style_named(ROCK)

    def made(self, sounds):
        return arranger.arranged(style=self.style, song={**a_song(), arranger.PIECE_SOUNDS: sounds})

    def rows(self, *, made, piece):
        part = made[arranger.PARTS][piece]
        return part.get(RAW, part)

    def notes(self, *, made, piece):
        """The MIDI notes a piece's part plays."""
        rows = self.rows(made=made, piece=piece)
        marks = rows.get(notation.ACCIDENTAL) or [None] * rows[notation.STEPS]
        return {notation.NOTE_NAMES.index(name) + (1 if mark else 0) + octave * notation.NOTES_IN_OCTAVE for name, mark, octave in zip(rows[notation.DEGREE], marks, rows[notation.OCTAVE]) if name is not None}

    def test_a_piece_sounds_as_another_drum_of_the_kit_on_the_drum_kit_still(self):
        usual = self.made({})
        made = self.made({breaks.KICK: {arranger.PLAYED_DRUM: COWBELL}})
        self.assertEqual(self.notes(made=usual, piece=breaks.KICK), {notation.KIT[breaks.KICK]})
        self.assertEqual(self.notes(made=made, piece=breaks.KICK), {notation.KIT[COWBELL]})
        self.assertEqual(made[arranger.TRACKS], usual[arranger.TRACKS])
        self.assertEqual(made[arranger.DRUM_TRACKS], usual[arranger.DRUM_TRACKS])
        self.assertEqual(self.rows(made=made, piece=breaks.SNARE), self.rows(made=usual, piece=breaks.SNARE))

    def test_a_piece_in_a_general_midi_sound_plays_its_note_on_a_track_with_an_instrument_of_its_own(self):
        usual = self.made({})
        made = self.made({breaks.KICK: {arranger.PLAYED_SOUND: A_SOUND, arranger.PLAYED_NOTE: A_NOTE}})
        self.assertEqual(self.notes(made=made, piece=breaks.KICK), {A_NOTE})
        instrument = made[arranger.TRACKS][breaks.KICK]
        self.assertEqual(instrument, composer_text.MSG_PIECE_INSTRUMENT.format(breaks.KICK))
        self.assertEqual(made[arranger.INSTRUMENTS][instrument], A_SOUND)
        self.assertNotIn(breaks.KICK, made[arranger.DRUM_TRACKS])
        self.assertEqual([piece for piece in usual[arranger.DRUM_TRACKS] if piece != breaks.KICK], made[arranger.DRUM_TRACKS])
        # The hits fall where they fell: only what sounds has changed.
        self.assertEqual(self.rows(made=made, piece=breaks.KICK)[notation.VELOCITY], self.rows(made=usual, piece=breaks.KICK)[notation.VELOCITY])

    def test_a_sound_that_is_neither_is_refused(self):
        for sounds_as in ({arranger.PLAYED_DRUM: NO_SUCH}, {arranger.PLAYED_SOUND: A_SOUND}, {arranger.PLAYED_SOUND: 0, arranger.PLAYED_NOTE: A_NOTE},
                          {arranger.PLAYED_SOUND: A_SOUND, arranger.PLAYED_NOTE: arranger.HIGHEST_NOTE + 1}, {}):
            with self.assertRaises(ValueError) as refused:
                self.made({breaks.KICK: sounds_as})
            self.assertEqual(str(refused.exception), errors.ERR_PIECE_SOUND.format(breaks.KICK, sounds_as))

    def test_the_wizard_keeps_a_pieces_sound_and_note_and_gives_the_piece_its_drum_back(self):
        choices = wizard()
        usual = patterns_of(choices)
        self.assertIn(breaks.KICK, choices.pieces())
        self.assertIsNone(choices.piece_sound(breaks.KICK))
        choices.set_piece_sound(piece=breaks.KICK, sound=COWBELL)
        self.assertEqual(choices.piece_sound(breaks.KICK), COWBELL)
        self.assertIsNone(choices.piece_note(breaks.KICK))
        as_drum = patterns_of(choices)
        self.assertNotEqual(as_drum, usual)
        choices.set_piece_sound(piece=breaks.KICK, sound=A_SOUND)
        self.assertEqual((choices.piece_sound(breaks.KICK), choices.piece_note(breaks.KICK)), (A_SOUND, wizard_limits.USUAL_PIECE_NOTE))
        choices.set_piece_note(piece=breaks.KICK, note=A_NOTE)
        self.assertNotIn(patterns_of(choices), (usual, as_drum))
        # A piece in a sound of its own is still a piece of the kit, listed and switched on and off.
        self.assertIn(breaks.KICK, choices.pieces())
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual((again.piece_sound(breaks.KICK), again.piece_note(breaks.KICK)), (A_SOUND, A_NOTE))
        self.assertEqual(patterns_of(again), patterns_of(choices))
        data = again.made_setlist(name=SONG_NAME, version=version.VERSION).to_data()
        self.assertEqual(data[Section.INSTRUMENTS][composer_text.MSG_PIECE_INSTRUMENT.format(breaks.KICK)][InstrumentSetting.GM_SOUND], A_SOUND)
        # Another sound keeps the note chosen, and the piece's own name gives it its drum back.
        choices.set_piece_sound(piece=breaks.KICK, sound=A_SOUND + 1)
        self.assertEqual(choices.piece_note(breaks.KICK), A_NOTE)
        choices.set_piece_sound(piece=breaks.KICK, sound=None)
        self.assertEqual(patterns_of(choices), usual)

    def test_the_wizard_refuses_what_is_no_piece_no_sound_and_no_note(self):
        choices = wizard()
        with self.assertRaises(ValueError) as refused:
            choices.set_piece_sound(piece=NO_SUCH, sound=COWBELL)
        self.assertEqual(str(refused.exception), errors.ERR_WIZARD_NO_SUCH_PIECE.format(value=NO_SUCH))
        for sound in (NO_SUCH, 0, limits.MAX_GM_SOUND + 1, True, 2.5):
            with self.assertRaises(ValueError) as refused:
                choices.set_piece_sound(piece=breaks.KICK, sound=sound)
            self.assertEqual(str(refused.exception), errors.ERR_WIZARD_PIECE_SOUND.format(value=sound))
        with self.assertRaises(ValueError) as refused:
            choices.set_piece_note(piece=breaks.KICK, note=A_NOTE)
        self.assertEqual(str(refused.exception), errors.ERR_WIZARD_PIECE_HAS_NO_NOTE.format(value=breaks.KICK))
        choices.set_piece_sound(piece=breaks.KICK, sound=A_SOUND)
        for note in (arranger.LOWEST_NOTE - 1, arranger.HIGHEST_NOTE + 1, True, NO_SUCH):
            with self.assertRaises(ValueError) as refused:
                choices.set_piece_note(piece=breaks.KICK, note=note)
            self.assertEqual(str(refused.exception), errors.ERR_WIZARD_PIECE_NOTE.format(low=arranger.LOWEST_NOTE, high=arranger.HIGHEST_NOTE, value=note))
