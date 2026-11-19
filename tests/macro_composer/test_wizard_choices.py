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
"""The song wizard's choices: what a subgenre fills in, what each setter refuses, the choices kept and read back, and the song made."""

from fractions import Fraction
import random
import unittest

from llamatron.composition import limits
from llamatron.composition.file_format import Section
from llamatron.macro_composer import arranger, melody, notation, wizard_limits
from llamatron.macro_composer.arranger import arranged, share_in, style_named, style_names, values_of
from llamatron.macro_composer.wizard_choices import genre_names, genre_title, style_of, WizardChoices
from llamatron.music.note import NoteName
from llamatron.playback.song_renderer import SongRenderer
from llamatron.strings import errors, macro_composer as composer_text
from llamatron.support import version

A_NAME = 'made'
NOT_A_CHOICE = 'polka of the spheres'
AN_OFFER = 'an offer'
ANOTHER_OFFER = 'another offer'
A_SEED = 11
ANOTHER_SEED = 12
NOT_A_NUMBER = 'fast'
# How near the length said must be to the length made.
A_SECOND = 1
# A genre whose songs have tunes sketched from the seed, so that another seed is heard.
A_GENRE_WITH_TUNES = 'rock'
NO_SUCH_GAUGE = 'wobble'
A_GAUGE_IN_WORDS = 'high'
# The genres whose songs have a hook unless a person switches the hook off.
GENRES_WITH_A_HOOK = ('rock', 'sixties_pop', 'soul_funk')
# A player that genre always has.
A_BASS = 'bass'
ANOTHER_GENRE = 'blues'
A_GENRE_WITH_STYLES = 'rock'
A_SERIAL_GENRE = 'experimental'
ROLES_OF_STYLE = 'roles'
ROLE_OF_ENTRY = 'role'
HABITS_OF_ENTRY = 'habits'
SECTIONS_OF_STYLE = 'sections'
PLAN_OF_SECTION = 'plan'
HOOK_MARK = 'hook'
ANOTHER_ROOT = 'A'
NOTES_IN_AN_OCTAVE = 12
HARD_ROCK = 'hard rock'
DRUMS_ROLE = 'drums'
GUITAR_ROLE = 'guitar'
# The player left alone in an intro, and how many intros the song has, where the shortest intro cannot be made.
SHORT_INTRO_REFUSED = ((GUITAR_ROLE, 1), (DRUMS_ROLE, 2))
THE_INTRO = 0
A_SEED_OF_SHORT_DRUMS = 21


def chosen(*, genre=0, subgenre=0):
    choices = WizardChoices()
    choices.set_genre(genre_names()[genre])
    choices.set_subgenre(choices.subgenres()[subgenre])
    return choices


class TestWizardChoices(unittest.TestCase):

    def test_the_genres_are_every_style_template_in_the_order_of_their_titles(self):
        self.assertEqual(sorted(genre_names()), style_names())
        titles = [genre_title(genre) for genre in genre_names()]
        self.assertEqual(titles, sorted(titles))

    def test_nothing_is_chosen_at_first_and_no_song_can_be_made(self):
        choices = WizardChoices()
        self.assertIsNone(choices.get_genre())
        self.assertEqual(choices.subgenres(), [])
        self.assertEqual(choices.forms(), [])
        self.assertIsNone(choices.get_form())
        self.assertFalse(choices.is_ready())
        self.assertEqual(choices.to_data(), {})
        with self.assertRaises(ValueError):
            choices.made_setlist(name=A_NAME, version=version.VERSION)

    def test_a_genre_alone_is_not_enough_and_its_subgenres_are_sorted(self):
        choices = WizardChoices()
        choices.set_genre(genre_names()[0])
        self.assertFalse(choices.is_ready())
        self.assertTrue(choices.subgenres())
        self.assertEqual(choices.subgenres(), sorted(choices.subgenres()))

    def test_every_subgenre_of_every_genre_fills_in_the_rest_and_makes_a_song_that_keeps_the_choices(self):
        for place, genre in enumerate(genre_names()):
            for subgenre in range(len(chosen(genre=place).subgenres())):
                choices = chosen(genre=place, subgenre=subgenre)
                with self.subTest(genre=genre, subgenre=choices.get_subgenre()):
                    self.assertTrue(choices.is_ready())
                    self.assertIn(choices.get_scale_type(), wizard_limits.SCALE_TYPES)
                    self.assertEqual(choices.get_root(), wizard_limits.USUAL_ROOTS[choices.get_scale_type()])
                    self.assertEqual(choices.get_tempo(), choices.usual_tempo())
                    lowest, highest = choices.tempo_range()
                    self.assertLessEqual(lowest, highest)
                    self.assertEqual(choices.get_form(), choices.forms()[0])
                    self.assertTrue(choices.form_sections())
                    for section in range(len(choices.form_sections())):
                        self.assertGreater(choices.section_bars(section), 0)
                    setlist = choices.made_setlist(name=A_NAME, version=version.VERSION)
                    self.assertEqual(setlist.get_song_names(), [A_NAME])
                    song = setlist.get_song(A_NAME)
                    self.assertTrue(song.get_scenes())
                    self.assertEqual(int(song.get_tempo()), choices.get_tempo())
                    self.assertEqual(song.get_wizard_choices(), choices.to_data())
                    self.assertIsNotNone(choices.get_seed())
                    # Every pattern a clip plays is in the group named after the first track that plays it, and nothing is left in no group.
                    for name in setlist.get_pattern_names():
                        self.assertEqual(setlist.get_pattern(name).get_group(), setlist.first_track_playing(name), name)

    def test_another_genre_leaves_the_subgenre_to_be_chosen_again_and_the_same_genre_keeps_it(self):
        choices = chosen()
        subgenre = choices.get_subgenre()
        choices.set_genre(genre_names()[0])
        self.assertEqual(choices.get_subgenre(), subgenre)
        choices.set_genre(genre_names()[1])
        self.assertIsNone(choices.get_subgenre())
        self.assertFalse(choices.is_ready())

    def test_choosing_the_same_subgenre_again_keeps_what_was_changed(self):
        choices = chosen()
        choices.set_tempo(choices.get_tempo() + 1)
        tempo = choices.get_tempo()
        choices.set_subgenre(choices.get_subgenre())
        self.assertEqual(choices.get_tempo(), tempo)

    def test_each_setter_refuses_what_it_cannot_hold(self):
        choices = chosen()
        for setter, value in [
            (choices.set_genre, NOT_A_CHOICE), (choices.set_subgenre, NOT_A_CHOICE), (choices.set_root, NOT_A_CHOICE), (choices.set_scale_type, NOT_A_CHOICE),
            (choices.set_form, NOT_A_CHOICE), (choices.set_tempo, limits.MIN_TEMPO - 1), (choices.set_tempo, limits.MAX_TEMPO + 1), (choices.set_tempo, NOT_A_NUMBER), (choices.set_tempo, True),
            (choices.set_seed, NOT_A_NUMBER),
        ]:
            with self.subTest(setter=setter.__name__, value=value):
                before = choices.to_data()
                with self.assertRaises(ValueError):
                    setter(value)
                self.assertEqual(choices.to_data(), before)

    def test_any_tempo_the_tracker_plays_is_allowed_outside_the_usual_range_too(self):
        choices = chosen()
        _, highest = choices.tempo_range()
        choices.set_tempo(limits.MAX_TEMPO)
        self.assertGreater(choices.get_tempo(), highest)

    def test_the_choices_are_kept_as_data_and_read_back_the_same(self):
        choices = chosen(genre=1, subgenre=1)
        choices.set_root(NoteName.F_SHARP)
        choices.set_scale_type(wizard_limits.MINOR)
        choices.set_tempo(choices.get_tempo() + 3)
        choices.set_form(choices.forms()[-1])
        choices.set_seed(A_SEED)
        data = choices.to_data()
        self.assertEqual(WizardChoices.from_data(data).to_data(), data)

    def test_reading_leaves_out_what_no_longer_fits_and_keeps_the_rest(self):
        data = chosen().to_data()
        gone = WizardChoices.from_data({**data, wizard_limits.SUBGENRE: NOT_A_CHOICE})
        self.assertEqual(gone.get_genre(), data[arranger.GENRE])
        self.assertIsNone(gone.get_subgenre())
        self.assertEqual(WizardChoices.from_data(None).to_data(), {})
        self.assertEqual(WizardChoices.from_data({arranger.GENRE: NOT_A_CHOICE}).to_data(), {})

    def test_the_same_choices_and_seed_make_the_same_song_and_another_seed_another(self):
        def data_of(seed):
            choices = chosen(genre=genre_names().index(A_GENRE_WITH_TUNES))
            choices.set_seed(seed)
            return choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()
        self.assertEqual(data_of(A_SEED), data_of(A_SEED))
        other = data_of(ANOTHER_SEED)
        self.assertNotEqual({**data_of(A_SEED), Section.SONGS: None}[Section.PATTERNS], other[Section.PATTERNS])

    def test_a_seed_is_drawn_once_when_none_is_given_and_kept(self):
        choices = chosen()
        choices.draw_seed(dice=random.Random(A_SEED))
        seed = choices.get_seed()
        self.assertTrue(wizard_limits.FIRST_SEED <= seed <= wizard_limits.LAST_SEED)
        choices.made_setlist(name=A_NAME, version=version.VERSION)
        self.assertEqual(choices.get_seed(), seed)

    def test_a_scale_type_changes_the_songs_scale(self):
        choices = chosen()
        for kind in (wizard_limits.MAJOR, wizard_limits.MINOR):
            choices.set_scale_type(kind)
            setlist = choices.made_setlist(name=A_NAME, version=version.VERSION)
            scale = setlist.get_named_scale(setlist.get_song(A_NAME).get_scale_name())
            self.assertEqual(scale.to_data()[arranger.TYPE], kind)

    def test_a_forms_length_is_its_bars_at_the_tempo_and_the_meter(self):
        choices = chosen()
        bars = sum(choices.section_bars(place) for place in range(len(choices.form_sections())))
        seconds = choices.form_seconds()
        self.assertAlmostEqual(seconds, bars * float(Fraction(choices.meter())) * wizard_limits.QUARTERS_IN_WHOLE * wizard_limits.SECONDS_IN_MINUTE / choices.get_tempo())
        choices.set_tempo(choices.get_tempo() * 2)
        self.assertAlmostEqual(choices.form_seconds(), seconds / 2)

    def test_every_subgenre_has_a_meter_and_its_forms_from_the_shortest_to_the_longest(self):
        for place in range(len(genre_names())):
            for subgenre in range(len(chosen(genre=place).subgenres())):
                choices = chosen(genre=place, subgenre=subgenre)
                self.assertGreater(Fraction(choices.meter()), 0)
                lengths = [choices.form_seconds(form=form) for form in choices.forms_by_length()]
                self.assertEqual(lengths, sorted(lengths))
                self.assertEqual(sorted(choices.forms_by_length()), sorted(choices.forms()))

    def test_stepping_the_length_chooses_the_next_longer_or_shorter_form_and_stops_at_both_ends(self):
        choices = chosen(genre=genre_names().index(A_GENRE_WITH_TUNES))
        forms = choices.forms_by_length()
        self.assertGreater(len(forms), 2)
        for _ in forms:
            choices.step_length(-1)
        self.assertEqual(choices.get_form(), forms[0])
        choices.step_length(1)
        self.assertEqual(choices.get_form(), forms[1])
        for _ in forms:
            choices.step_length(1)
        self.assertEqual(choices.get_form(), forms[-1])

    def test_the_length_said_is_the_length_of_the_song_made_for_every_form_of_every_subgenre(self):
        for place in range(len(genre_names())):
            for subgenre in range(len(chosen(genre=place).subgenres())):
                choices = chosen(genre=place, subgenre=subgenre)
                choices.set_seed(A_SEED)
                for form in choices.forms():
                    choices.set_form(form)
                    song = choices.made_setlist(name=A_NAME, version=version.VERSION).get_song(A_NAME)
                    made = sum(float(scene.seconds) for scene in SongRenderer(song).estimate())
                    self.assertAlmostEqual(choices.form_seconds(), made, delta=A_SECOND, msg=(choices.get_subgenre(), form))


def scene_bars_of(choices):
    """How long each scene of the song made lasts, in bars."""
    song = choices.made_setlist(name=A_NAME, version=version.VERSION).get_song(A_NAME)
    seconds_in_a_bar = float(Fraction(choices.meter()) * wizard_limits.QUARTERS_IN_WHOLE * wizard_limits.SECONDS_IN_MINUTE / choices.get_tempo())
    return [round(float(scene.seconds) / seconds_in_a_bar) for scene in SongRenderer(song).estimate()]


class FormLengthsOfAGenre:
    """Every kind of section of every subgenre of one genre, at every length the wizard offers: a class a genre, since it makes a great many songs."""

    __slots__ = ()
    GENRE = None

    def test_every_kind_of_section_of_every_subgenre_plays_at_every_length_offered(self):
        for genre in (self.GENRE,):
            choices = WizardChoices()
            choices.set_genre(genre)
            for subgenre in choices.subgenres():
                choices.set_subgenre(subgenre)
                choices.set_seed(A_SEED)
                kinds = choices.section_kinds()
                wanted = []
                for kind in kinds:
                    choices.add_section(place=len(choices.form_sections()), kind=kind)
                    place = len(choices.form_sections()) - 1
                    wanted.append(choices.section_bars(place))
                # Every kind once at its usual length, then each at every other length offered, one song a length.
                with self.subTest(genre=genre, subgenre=subgenre):
                    self.assertEqual(scene_bars_of(choices)[-len(kinds):], wanted)
                first = len(choices.form_sections()) - len(kinds)
                for place in range(first, first + len(kinds)):
                    for bars in choices.bars_offered(place):
                        choices.set_section_bars(place=place, bars=bars)
                        with self.subTest(genre=genre, subgenre=subgenre, kind=kinds[place - first], bars=bars):
                            self.assertEqual(scene_bars_of(choices)[place], bars)


def lengths_class_for(genre):
    name = 'TestWizardFormLengthsOf{}'.format(''.join(word.capitalize() for word in genre.split('_')))
    return name, type(name, (FormLengthsOfAGenre, unittest.TestCase), {'GENRE': genre, '__slots__': ()})


for a_genre in genre_names():
    a_name, a_class = lengths_class_for(a_genre)
    globals()[a_name] = a_class
del a_class


class TestWizardForm(unittest.TestCase):
    """A form of the song's own: sections added, copied, removed, moved and changed."""

    def rock(self):
        choices = chosen(genre=genre_names().index(A_GENRE_WITH_TUNES))
        choices.set_seed(A_SEED)
        return choices

    def scene_bars(self, choices):
        return scene_bars_of(choices)

    def test_a_suggested_form_is_followed_until_a_section_changes_and_then_the_form_is_the_songs_own(self):
        choices = self.rock()
        suggested = choices.form_sections()
        self.assertFalse(choices.has_own_form())
        self.assertNotIn(wizard_limits.OWN_SECTIONS, choices.to_data())
        choices.copy_section(0)
        self.assertTrue(choices.has_own_form())
        self.assertEqual(choices.form_sections(), [suggested[0], *suggested])

    def test_choosing_a_suggested_form_again_puts_its_sections_back(self):
        choices = self.rock()
        suggested = choices.form_sections()
        choices.remove_section(0)
        choices.set_form(choices.get_form())
        self.assertFalse(choices.has_own_form())
        self.assertEqual(choices.form_sections(), suggested)

    def test_a_section_is_added_at_a_place_copied_after_itself_removed_and_moved(self):
        choices = self.rock()
        kinds = choices.section_kinds()
        before = choices.form_sections()
        choices.add_section(place=1, kind=kinds[-1])
        self.assertEqual(choices.form_sections(), [before[0], kinds[-1], *before[1:]])
        choices.copy_section(1)
        self.assertEqual(choices.form_sections(), [before[0], kinds[-1], kinds[-1], *before[1:]])
        choices.remove_section(1)
        choices.remove_section(1)
        self.assertEqual(choices.form_sections(), before)
        self.assertTrue(choices.move_section(place=0, offset=1))
        self.assertEqual(choices.form_sections(), [before[1], before[0], *before[2:]])

    def test_a_section_stops_at_both_ends_of_the_form(self):
        choices = self.rock()
        before = choices.form_sections()
        self.assertFalse(choices.move_section(place=0, offset=-1))
        self.assertFalse(choices.move_section(place=len(before) - 1, offset=1))
        self.assertEqual(choices.form_sections(), before)
        self.assertFalse(choices.has_own_form())

    def test_the_last_section_stays_and_a_place_or_a_kind_that_is_not_the_forms_is_refused(self):
        choices = self.rock()
        while len(choices.form_sections()) > 1:
            choices.remove_section(0)
        with self.assertRaisesRegex(ValueError, errors.ERR_WIZARD_LAST_SECTION):
            choices.remove_section(0)
        for refused in (lambda: choices.remove_section(1), lambda: choices.copy_section(-1), lambda: choices.add_section(place=5, kind=choices.section_kinds()[0]),
                        lambda: choices.add_section(place=0, kind=NOT_A_CHOICE), lambda: choices.set_section_kind(place=0, kind=NOT_A_CHOICE),
                        lambda: choices.set_section_bars(place=0, bars=NOT_A_NUMBER), lambda: choices.set_section_bars(place=0, bars=True)):
            with self.assertRaises(ValueError):
                refused()

    def test_a_section_made_longer_or_shorter_is_a_section_of_its_own_and_lasts_that_long_in_the_song(self):
        choices = self.rock()
        sections = choices.form_sections()
        place = 1
        usual = choices.section_bars(place)
        offered = choices.bars_offered(place)
        # A length is offered only where the genre's parts fill it: half the usual, the usual and twice that, at most.
        self.assertIn(usual, offered)
        self.assertGreater(len(offered), 1)
        self.assertLessEqual(set(offered), {usual // 2, usual, usual * 2})
        before = choices.form_seconds()
        choices.set_section_bars(place=place, bars=offered[-1])
        self.assertNotEqual(choices.form_sections()[place], sections[place])
        self.assertEqual([name for at, name in enumerate(choices.form_sections()) if at != place], [name for at, name in enumerate(sections) if at != place])
        self.assertGreater(choices.form_seconds(), before)
        self.assertEqual(self.scene_bars(choices)[place], offered[-1])
        choices.set_section_bars(place=place, bars=usual)
        self.assertEqual(choices.form_sections(), sections)

    def test_a_player_sits_a_section_out_or_joins_it_and_a_section_keeps_one_player(self):
        choices = self.rock()
        place = 1
        players = choices.section_plays(place)
        choices.set_section_plays(place=place, role=A_BASS, on=False)
        self.assertEqual(choices.section_plays(place), [role for role in choices.roles() if role in players and role != A_BASS])
        song = choices.made_setlist(name=A_NAME, version=version.VERSION).get_song(A_NAME)
        scene = song.get_scenes()[place]
        self.assertNotIn(A_BASS, [track for track in song.get_track_names() if scene.get_clip_slot(track) is not None])
        choices.set_section_plays(place=place, role=A_BASS, on=True)
        self.assertEqual(sorted(choices.section_plays(place)), sorted(players))
        for role in choices.section_plays(place)[1:]:
            choices.set_section_plays(place=place, role=role, on=False)
        with self.assertRaisesRegex(ValueError, errors.ERR_WIZARD_SECTION_NEEDS_PLAYER):
            choices.set_section_plays(place=place, role=choices.section_plays(place)[0], on=False)

    def test_another_kind_starts_the_section_as_the_genre_describes_that_kind(self):
        choices = self.rock()
        place = 1
        kind = [kind for kind in choices.section_kinds() if kind != choices.section_kind(place)][0]
        choices.set_section_plays(place=place, role=A_BASS, on=False)
        choices.set_section_kind(place=place, kind=kind)
        self.assertEqual(choices.section_kind(place), kind)
        self.assertEqual(choices.form_sections()[place], kind)

    def test_a_held_section_offers_no_lengths(self):
        choices = self.rock()
        held = [place for place in range(len(choices.form_sections())) if choices.section_is_held(place)]
        self.assertTrue(held)
        self.assertEqual(choices.bars_offered(held[0]), [])

    def test_a_section_offers_only_the_lengths_its_own_players_fill(self):
        """A guitar alone cannot time a short intro of hard rock, and drums alone cannot beside a second intro."""
        for role, intros in ((GUITAR_ROLE, 1), (DRUMS_ROLE, 2), (DRUMS_ROLE, 1), (A_BASS, 2)):
            choices = self.hard_rock()
            whole_band = choices.bars_offered(THE_INTRO)
            for another in range(intros - 1):
                choices.add_section(place=THE_INTRO + 1, kind=choices.section_kind(THE_INTRO))
            self.sit_out_all_but(choices=choices, role=role)
            alone = choices.bars_offered(THE_INTRO)
            self.assertLessEqual(set(alone), set(whole_band))
            if (role, intros) in SHORT_INTRO_REFUSED:
                self.assertNotIn(min(whole_band), alone)
            for bars in alone:
                choices.set_section_bars(place=THE_INTRO, bars=bars)
                choices.made_setlist(name=A_NAME, version=version.VERSION)

    def test_a_length_the_players_left_cannot_fill_gives_way_to_the_usual_length(self):
        choices = self.hard_rock()
        usual = choices.section_bars(THE_INTRO)
        choices.set_section_bars(place=THE_INTRO, bars=min(choices.bars_offered(THE_INTRO)))
        self.assertLess(choices.section_bars(THE_INTRO), usual)
        self.sit_out_all_but(choices=choices, role=GUITAR_ROLE)
        self.assertEqual(choices.section_bars(THE_INTRO), usual)
        choices.made_setlist(name=A_NAME, version=version.VERSION)

    def test_an_answer_found_by_making_the_song_is_kept_until_a_choice_changes(self):
        """The lengths offered are remembered, since a page asks at every key, and are worked out again after any change."""
        choices = self.hard_rock()
        first = choices.bars_offered(THE_INTRO)
        first.clear()
        self.assertTrue(choices.bars_offered(THE_INTRO))
        whole_band = choices.bars_offered(THE_INTRO)
        self.sit_out_all_but(choices=choices, role=GUITAR_ROLE)
        self.assertNotEqual(choices.bars_offered(THE_INTRO), whole_band)
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.bars_offered(THE_INTRO), choices.bars_offered(THE_INTRO))

    def hard_rock(self):
        choices = self.rock()
        choices.set_subgenre(HARD_ROCK)
        choices.set_seed(A_SEED_OF_SHORT_DRUMS)
        # The lengths a section's own players fill are a matter of the parts as the kind writes them: a planned song writes each section's drums whole.
        choices.set_song_plan(False)
        # And of the players' figures: the kind's riff, which lasts two bars whoever plays it, is taken away.
        for riff in choices.get_riffs().riff_names():
            choices.get_riffs().delete_riff(riff)
        return choices

    def sit_out_all_but(self, *, choices, role):
        for other in choices.section_plays(THE_INTRO):
            if other != role:
                choices.set_section_plays(place=THE_INTRO, role=other, on=False)

    def test_the_songs_own_form_is_kept_with_the_choices_and_makes_the_same_song(self):
        choices = self.rock()
        choices.add_section(place=1, kind=choices.section_kinds()[-2])
        choices.set_section_bars(place=2, bars=choices.bars_offered(2)[0])
        choices.set_section_plays(place=3, role=A_BASS, on=False)
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.to_data(), choices.to_data())
        self.assertEqual(again.form_sections(), choices.form_sections())
        self.assertEqual(again.made_setlist(name=A_NAME, version=version.VERSION).to_data(), choices.made_setlist(name=A_NAME, version=version.VERSION).to_data())

    def test_another_subgenre_goes_back_to_a_suggested_form(self):
        choices = self.rock()
        choices.copy_section(0)
        choices.set_subgenre(choices.subgenres()[1])
        self.assertFalse(choices.has_own_form())

    def test_kept_sections_that_no_longer_fit_are_dropped_and_the_rest_of_the_choices_kept(self):
        choices = self.rock()
        data = {**choices.to_data(), wizard_limits.OWN_SECTIONS: [{}]}
        again = WizardChoices.from_data(data)
        self.assertFalse(again.has_own_form())
        self.assertEqual(again.get_subgenre(), choices.get_subgenre())


class TestWizardOffers(unittest.TestCase):
    """What a page offers is kept until a choice changes, held through changes while a page says so, and never copied to a trial."""

    def setUp(self):
        self.choices = chosen(genre=genre_names().index(A_GENRE_WITH_TUNES))
        self.choices.set_seed(A_SEED)
        self.asked = 0

    def offer(self):
        def worked_out():
            self.asked += 1
            return self.asked
        return self.choices.offered(key=AN_OFFER, compute=worked_out)

    def change_something(self):
        self.choices.set_tempo(self.choices.get_tempo() + 1)

    def test_an_offer_is_worked_out_once_and_again_after_a_choice_changes(self):
        self.assertEqual([self.offer(), self.offer()], [1, 1])
        self.change_something()
        self.assertEqual([self.offer(), self.offer()], [2, 2])

    def test_a_held_offer_stays_through_a_change_and_is_worked_out_again_once_let_go(self):
        self.offer()
        self.choices.hold_offers()
        self.assertTrue(self.choices.holds_offers())
        self.change_something()
        self.assertEqual(self.offer(), 1)
        self.choices.release_offers()
        self.assertFalse(self.choices.holds_offers())
        self.assertEqual(self.offer(), 2)

    def test_a_value_changed_and_put_back_while_held_costs_nothing_when_let_go(self):
        self.offer()
        tempo = self.choices.get_tempo()
        self.choices.hold_offers()
        self.change_something()
        self.choices.set_tempo(tempo)
        self.choices.release_offers()
        self.assertEqual(self.offer(), 1)

    def test_an_offer_found_while_held_for_other_choices_is_forgotten_even_when_the_value_is_put_back(self):
        self.choices.offered(key=ANOTHER_OFFER, compute=lambda: None)
        tempo = self.choices.get_tempo()
        self.choices.hold_offers()
        self.change_something()
        self.assertEqual(self.offer(), 1)
        self.choices.set_tempo(tempo)
        self.choices.release_offers()
        self.assertEqual(self.offer(), 2)

    def test_an_offer_first_asked_for_while_held_is_worked_out(self):
        self.choices.hold_offers()
        self.assertEqual(self.offer(), 1)

    def test_what_a_song_is_made_from_is_never_held(self):
        self.choices.hold_offers()
        before = self.choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()
        self.change_something()
        self.assertNotEqual(self.choices.made_setlist(name=A_NAME, version=version.VERSION).to_data(), before)

    def test_a_question_answered_by_making_songs_holds_nothing_and_leaves_the_hold_as_it_was(self):
        self.choices.hold_offers()
        self.offer()
        role = self.choices.roles_in()[0]
        self.choices.has_dynamics(role)
        self.assertTrue(self.choices.holds_offers())
        self.assertEqual(self.offer(), 1)

    def test_the_patterns_asked_of_the_writer_are_the_patterns_of_the_set_made(self):
        made = self.choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.PATTERNS]
        self.assertEqual(sorted(self.choices._patterns_played()), sorted(made))


class TestWizardSongWays(unittest.TestCase):
    """What the whole song has a way of: its progression, its feel and its fills, and the melody style of its tunes."""

    def rock(self):
        choices = chosen(genre=genre_names().index(A_GENRE_WITH_TUNES))
        choices.set_seed(A_SEED)
        return choices

    def patterns(self, choices):
        return choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.PATTERNS]

    def test_nothing_of_the_song_is_offered_before_a_subgenre_is_chosen(self):
        choices = WizardChoices()
        self.assertIsNone(choices.song_trait(wizard_limits.PROGRESSION_TRAITS))
        self.assertEqual(choices.melody_styles(), [])

    def test_a_trait_a_player_owns_is_not_the_songs(self):
        for place in range(len(genre_names())):
            choices = chosen(genre=place)
            owned = {trait for role in choices.roles() for trait in choices.role_traits(role)}
            for traits in (wizard_limits.PROGRESSION_TRAITS, wizard_limits.FILLS_TRAITS):
                self.assertNotIn(choices.song_trait(traits), owned)

    def test_another_progression_changes_the_song(self):
        choices = self.rock()
        trait = choices.song_trait(wizard_limits.PROGRESSION_TRAITS)
        before = choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()
        choices.set_way(trait=trait, value=[way for way in choices.song_ways(trait) if way != choices.get_way(trait)][0])
        self.assertNotEqual(choices.made_setlist(name=A_NAME, version=version.VERSION).to_data(), before)

    def test_every_melody_style_offered_makes_a_song_and_another_style_changes_the_tunes(self):
        for place in range(len(genre_names())):
            choices = chosen(genre=place)
            choices.set_seed(A_SEED)
            usual = self.patterns(choices)
            made = []
            for style in choices.melody_styles():
                choices.set_melody(style)
                made.append(self.patterns(choices))
            if len(made) > 1:
                self.assertTrue(any(patterns != usual for patterns in made), genre_names()[place])

    def test_a_style_the_subgenre_cannot_use_is_not_offered_and_is_refused(self):
        refused = [(place, style) for place in range(len(genre_names())) for style in wizard_limits.MELODY_STYLES if style not in chosen(genre=place).melody_styles()]
        self.assertTrue(refused)
        place, style = refused[0]
        with self.assertRaises(ValueError):
            chosen(genre=place).set_melody(style)
        with self.assertRaises(ValueError):
            self.rock().set_melody(NOT_A_CHOICE)

    def test_the_melody_style_is_kept_with_the_choices_and_another_subgenre_goes_back_to_the_usual(self):
        choices = self.rock()
        self.assertNotIn(wizard_limits.MELODY_STYLE, choices.to_data())
        choices.set_melody(choices.melody_styles()[-1])
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.get_melody(), choices.get_melody())
        self.assertEqual(self.patterns(again), self.patterns(choices))
        choices.set_melody(None)
        self.assertIsNone(choices.get_melody())
        again.set_subgenre(again.subgenres()[1])
        self.assertIsNone(again.get_melody())


class TestWizardSounds(unittest.TestCase):
    """The band's Sounds and a player's own sound, and what the players are called."""

    def rock(self):
        choices = chosen(genre=genre_names().index(A_GENRE_WITH_TUNES))
        choices.set_seed(A_SEED)
        return choices

    def sound_made(self, *, choices, role):
        setlist = choices.made_setlist(name=A_NAME, version=version.VERSION)
        return setlist.get_instrument(setlist.get_song(A_NAME).get_track(role).get_instrument_name()).get_gm_sound()

    def test_every_player_of_every_genre_has_a_title_and_no_two_players_in_a_band_share_one(self):
        for place in range(len(genre_names())):
            choices = chosen(genre=place)
            titles = [choices.role_title(role) for role in choices.roles()]
            self.assertEqual(len(set(titles)), len(titles), titles)

    def test_the_drums_have_no_sound_to_choose(self):
        choices = self.rock()
        drums = [role for role in choices.roles() if not choices.get_sounds().has_sound(role)]
        self.assertTrue(drums)
        with self.assertRaises(ValueError):
            choices.get_sounds().set_sound(role=drums[0], sound=1)

    def test_the_usual_sounds_change_nothing_and_each_other_kind_moves_a_player_and_is_made(self):
        choices = self.rock()
        usual = choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.INSTRUMENTS]
        self.assertEqual(choices.get_sounds().get_band_sounds(), wizard_limits.USUAL_SOUNDS)
        self.assertEqual(choices.get_sounds().get_sound(A_BASS), choices.get_sounds().usual_sound(A_BASS))
        any_moved = False
        for sounds in wizard_limits.BAND_SOUNDS[1:]:
            choices.get_sounds().set_band_sounds(sounds)
            moved = [role for role in choices.roles_in() if choices.get_sounds().has_sound(role) and choices.get_sounds().get_sound(role) != choices.get_sounds().usual_sound(role)]
            # A band already of the kind chosen, as an electric rock band, keeps its sounds and makes the same song.
            self.assertEqual(choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.INSTRUMENTS] != usual, bool(moved), sounds)
            any_moved = any_moved or bool(moved)
            for role in moved:
                self.assertEqual(self.sound_made(choices=choices, role=role), choices.get_sounds().get_sound(role))
        self.assertTrue(any_moved)

    def test_a_sound_already_of_the_kind_chosen_stays(self):
        choices = self.rock()
        for sounds in wizard_limits.BAND_SOUNDS[1:]:
            choices.get_sounds().set_band_sounds(sounds)
            for role in choices.roles_in():
                if choices.get_sounds().has_sound(role) and choices.get_sounds().usual_sound(role) in wizard_limits.KEPT_BY[sounds]:
                    self.assertEqual(choices.get_sounds().get_sound(role), choices.get_sounds().usual_sound(role))

    def test_every_kind_of_sounds_makes_a_song_that_plays_in_every_subgenre(self):
        for place in range(len(genre_names())):
            for subgenre in range(len(chosen(genre=place).subgenres())):
                choices = chosen(genre=place, subgenre=subgenre)
                choices.set_seed(A_SEED)
                for sounds in wizard_limits.BAND_SOUNDS[1:]:
                    choices.get_sounds().set_band_sounds(sounds)
                    with self.subTest(subgenre=choices.get_subgenre(), sounds=sounds):
                        SongRenderer(choices.made_setlist(name=A_NAME, version=version.VERSION).get_song(A_NAME)).render()

    def test_a_players_own_sound_overrides_the_bands_and_none_follows_the_band_again(self):
        choices = self.rock()
        choices.get_sounds().set_band_sounds(wizard_limits.BAND_SOUNDS[1])
        band = choices.get_sounds().get_sound(A_BASS)
        choices.get_sounds().set_sound(role=A_BASS, sound=limits.MAX_GM_SOUND)
        self.assertTrue(choices.get_sounds().has_own_sound(A_BASS))
        self.assertEqual(self.sound_made(choices=choices, role=A_BASS), limits.MAX_GM_SOUND)
        choices.get_sounds().set_band_sounds(wizard_limits.BAND_SOUNDS[2])
        self.assertEqual(choices.get_sounds().get_sound(A_BASS), limits.MAX_GM_SOUND)
        choices.get_sounds().set_band_sounds(wizard_limits.BAND_SOUNDS[1])
        choices.get_sounds().set_sound(role=A_BASS, sound=None)
        self.assertEqual(choices.get_sounds().get_sound(A_BASS), band)

    def test_a_sound_that_plays_no_notes_or_is_no_sound_is_refused(self):
        choices = self.rock()
        for refused in (0, limits.MAX_GM_SOUND + 1, True, NOT_A_NUMBER):
            with self.assertRaises(ValueError):
                choices.get_sounds().set_sound(role=A_BASS, sound=refused)
        with self.assertRaises(ValueError):
            choices.get_sounds().set_band_sounds(NOT_A_CHOICE)

    def test_the_genres_sounds_for_a_player_are_the_sounds_of_the_ways_the_player_plays(self):
        choices = self.rock()
        self.assertIn(choices.get_sounds().usual_sound(A_BASS), choices.get_sounds().genre_sounds(A_BASS))
        self.assertTrue(choices.get_sounds().sound_name(choices.get_sounds().usual_sound(A_BASS)))

    def test_the_sounds_are_kept_with_the_choices_and_another_subgenre_starts_afresh(self):
        choices = self.rock()
        self.assertNotIn(wizard_limits.SOUNDS_KEPT, choices.to_data())
        choices.get_sounds().set_band_sounds(wizard_limits.BAND_SOUNDS[-1])
        choices.get_sounds().set_sound(role=A_BASS, sound=limits.MAX_GM_SOUND)
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.to_data(), choices.to_data())
        self.assertEqual(again.get_sounds().get_sound(A_BASS), limits.MAX_GM_SOUND)
        again.set_subgenre(again.subgenres()[1])
        self.assertEqual(again.get_sounds().get_band_sounds(), wizard_limits.USUAL_SOUNDS)
        self.assertFalse(again.get_sounds().has_own_sound(A_BASS))


class TestWizardGuitarists(unittest.TestCase):
    """A band with one guitarist, who plays the chords and takes the solo."""

    def rock(self):
        choices = chosen(genre=genre_names().index(A_GENRE_WITH_TUNES))
        choices.set_seed(A_SEED)
        return choices

    def one(self, choices):
        return style_named(choices.get_genre())[wizard_limits.ONE_GUITARIST]

    def players_by_scene(self, choices):
        """Which tracks play in each scene of the song made, by the scene's name."""
        song = choices.made_setlist(name=A_NAME, version=version.VERSION).get_song(A_NAME)
        SongRenderer(song).render()
        return {scene.get_name(): [track for track in song.get_track_names() if scene.get_clip_slot(track) is not None] for scene in song.get_scenes()}

    def test_a_band_has_two_guitarists_until_one_is_chosen_and_a_genre_with_no_guitar_solo_offers_only_two(self):
        choices = self.rock()
        self.assertEqual(choices.get_guitarists(), wizard_limits.TWO_GUITARISTS)
        self.assertTrue(choices.offers_one_guitarist())
        without = [place for place in range(len(genre_names())) if not chosen(genre=place).offers_one_guitarist()]
        self.assertTrue(without)
        with self.assertRaises(ValueError):
            chosen(genre=without[0]).set_guitarists(wizard_limits.ONE_GUITARIST_COUNT)
        with self.assertRaises(ValueError):
            choices.set_guitarists(NOT_A_CHOICE)

    def test_one_guitarist_is_one_player_on_the_screen_who_takes_the_solo_on_the_guitar(self):
        choices = self.rock()
        one = self.one(choices)
        choices.set_guitarists(wizard_limits.ONE_GUITARIST_COUNT)
        self.assertNotIn(one[wizard_limits.SOLO_PLAYER], choices.roles_shown())
        self.assertEqual(choices.role_title(one[wizard_limits.CHORDS_PLAYER]), one[arranger.ROLE_TITLE])
        self.assertEqual(choices.get_way(one[wizard_limits.SOLO_PLAYER]), one[wizard_limits.SOLO_WAY])
        self.assertTrue(choices.role_is_in(one[wizard_limits.SOLO_PLAYER]))
        choices.set_guitarists(wizard_limits.TWO_GUITARISTS)
        self.assertIn(one[wizard_limits.SOLO_PLAYER], choices.roles_shown())

    def test_the_chords_stop_where_the_solo_plays_in_a_suggested_form_and_in_the_songs_own(self):
        for own in (False, True):
            choices = self.rock()
            one = self.one(choices)
            if own:
                choices.copy_section(0)
            both = [name for name, tracks in self.players_by_scene(choices).items() if one[wizard_limits.SOLO_PLAYER] in tracks and one[wizard_limits.CHORDS_PLAYER] in tracks]
            self.assertTrue(both)
            choices.set_guitarists(wizard_limits.ONE_GUITARIST_COUNT)
            scenes = self.players_by_scene(choices)
            self.assertTrue(any(one[wizard_limits.SOLO_PLAYER] in tracks for tracks in scenes.values()))
            self.assertTrue(any(one[wizard_limits.CHORDS_PLAYER] in tracks for tracks in scenes.values()))
            for name, tracks in scenes.items():
                self.assertFalse(one[wizard_limits.SOLO_PLAYER] in tracks and one[wizard_limits.CHORDS_PLAYER] in tracks, name)

    def test_one_guitarist_left_out_takes_the_solo_out_too(self):
        choices = self.rock()
        one = self.one(choices)
        choices.set_guitarists(wizard_limits.ONE_GUITARIST_COUNT)
        choices.set_role_in(role=one[wizard_limits.CHORDS_PLAYER], on=False)
        tracks = choices.made_setlist(name=A_NAME, version=version.VERSION).get_song(A_NAME).get_track_names()
        self.assertNotIn(one[wizard_limits.SOLO_PLAYER], tracks)
        self.assertNotIn(one[wizard_limits.CHORDS_PLAYER], tracks)

    def test_one_guitarist_is_kept_with_the_choices_and_another_subgenre_has_two_again(self):
        choices = self.rock()
        self.assertNotIn(wizard_limits.GUITARISTS_KEPT, choices.to_data())
        choices.set_guitarists(wizard_limits.ONE_GUITARIST_COUNT)
        again = WizardChoices.from_data(choices.to_data())
        self.assertTrue(again.has_one_guitarist())
        self.assertEqual(again.to_data(), choices.to_data())
        again.set_subgenre(again.subgenres()[1])
        self.assertFalse(again.has_one_guitarist())


FIRST_DEGREE = 1
MANY_RUNS = 30
A_FEW_RUNS = 4
GM_SOUND_KEY = 'gm_sound'
A_SOUND_OF_NO_STYLE = 110
EMPTY = ''
LEAD_ROLE = 'lead'


class TestWizardKit(unittest.TestCase):
    """The drum kit's pieces, each switched on or off."""

    def rock(self):
        choices = chosen(genre=genre_names().index(A_GENRE_WITH_TUNES))
        choices.set_seed(A_SEED)
        return choices

    def tracks(self, choices):
        song = choices.made_setlist(name=A_NAME, version=version.VERSION).get_song(A_NAME)
        SongRenderer(song).render()
        return song.get_track_names()

    def test_the_pieces_are_the_drum_tracks_of_the_song_and_all_are_on(self):
        choices = self.rock()
        pieces = choices.get_kit().pieces()
        self.assertTrue(pieces)
        self.assertTrue(all(choices.get_kit().piece_is_on(piece) for piece in pieces))
        self.assertLessEqual(set(pieces), set(self.tracks(choices)))
        self.assertEqual(WizardChoices().get_kit().pieces(), [])

    def test_every_piece_of_every_subgenre_switched_off_is_left_out_and_the_song_plays(self):
        for place in range(len(genre_names())):
            for subgenre in range(len(chosen(genre=place).subgenres())):
                choices = chosen(genre=place, subgenre=subgenre)
                choices.set_seed(A_SEED)
                pieces = choices.get_kit().pieces()
                for piece in pieces[1:]:
                    choices.get_kit().set_piece_on(piece=piece, on=False)
                    with self.subTest(subgenre=choices.get_subgenre(), piece=piece):
                        self.assertNotIn(piece, self.tracks(choices))
                    choices.get_kit().set_piece_on(piece=piece, on=True)

    def test_the_other_pieces_play_as_they_did(self):
        choices = self.rock()
        before = choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.PATTERNS]
        choices.get_kit().set_piece_on(piece=choices.get_kit().pieces()[-1], on=False)
        after = choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.PATTERNS]
        self.assertLess(len(after), len(before))
        for name, pattern in after.items():
            self.assertEqual(pattern, before[name], name)

    def test_the_last_piece_stays_on_and_a_piece_the_kit_has_not_is_refused(self):
        choices = self.rock()
        pieces = choices.get_kit().pieces()
        for piece in pieces[1:]:
            choices.get_kit().set_piece_on(piece=piece, on=False)
        with self.assertRaisesRegex(ValueError, errors.ERR_WIZARD_LAST_PIECE):
            choices.get_kit().set_piece_on(piece=pieces[0], on=False)
        with self.assertRaises(ValueError):
            choices.get_kit().set_piece_on(piece=NOT_A_CHOICE, on=False)

    def test_the_pieces_switched_off_are_kept_with_the_choices_and_another_subgenre_has_them_all(self):
        choices = self.rock()
        self.assertNotIn(wizard_limits.PIECES_OFF_KEPT, choices.to_data())
        piece = choices.get_kit().pieces()[-1]
        choices.get_kit().set_piece_on(piece=piece, on=False)
        again = WizardChoices.from_data(choices.to_data())
        self.assertFalse(again.get_kit().piece_is_on(piece))
        self.assertEqual(again.to_data(), choices.to_data())
        again.set_subgenre(again.subgenres()[1])
        self.assertTrue(all(again.get_kit().piece_is_on(name) for name in again.get_kit().pieces()))


class TestWizardFillsAndQuietNotes(unittest.TestCase):
    """How often the drummer plays a fill, and the snare's quiet notes."""

    def rock(self):
        choices = chosen(genre=genre_names().index(A_GENRE_WITH_TUNES))
        choices.set_seed(A_SEED)
        return choices

    def patterns(self, choices):
        return choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.PATTERNS]

    def with_quiet_notes(self):
        """Choices whose snare has quiet notes: the first groove of any genre that has them."""
        for place in range(len(genre_names())):
            choices = chosen(genre=place)
            choices.set_seed(A_SEED)
            for role in choices.roles():
                if not choices.get_sounds().has_sound(role):
                    for trait in choices.role_traits(role):
                        for way in choices.ways(role=role, trait=trait):
                            choices.set_way(trait=trait, value=way)
                            if choices.get_kit().has_quiet_notes():
                                return choices
        raise AssertionError('no groove has quiet notes')

    def test_the_drummer_decides_how_often_until_a_position_is_chosen_and_the_song_is_then_the_same(self):
        choices = self.rock()
        self.assertIn(choices.get_kit().get_fills(), range(wizard_limits.FEWEST_FILLS, wizard_limits.MOST_FILLS + 1))
        self.assertNotIn(wizard_limits.FILLS_KEPT, choices.to_data())

    def test_every_position_makes_a_song_that_plays_in_every_subgenre_and_the_positions_differ(self):
        for place in range(len(genre_names())):
            for subgenre in range(len(chosen(genre=place).subgenres())):
                choices = chosen(genre=place, subgenre=subgenre)
                choices.set_seed(A_SEED)
                for position in range(wizard_limits.FEWEST_FILLS, wizard_limits.MOST_FILLS + 1):
                    choices.get_kit().set_fills(position)
                    with self.subTest(subgenre=choices.get_subgenre(), position=position):
                        SongRenderer(choices.made_setlist(name=A_NAME, version=version.VERSION).get_song(A_NAME)).render()
        choices = self.rock()
        made = []
        for position in range(wizard_limits.FEWEST_FILLS, wizard_limits.MOST_FILLS + 1):
            choices.get_kit().set_fills(position)
            made.append(self.patterns(choices))
        self.assertNotEqual(made[0], made[-1])
        self.assertNotEqual(made[1], made[-1])

    def test_a_position_that_is_not_one_is_refused(self):
        for refused in (wizard_limits.FEWEST_FILLS - 1, wizard_limits.MOST_FILLS + 1, True, NOT_A_NUMBER):
            with self.assertRaises(ValueError):
                self.rock().get_kit().set_fills(refused)
        with self.assertRaises(ValueError):
            self.rock().get_kit().set_quiet_notes(NOT_A_NUMBER)

    def test_quiet_notes_switched_off_change_the_song_and_switched_on_again_give_it_back(self):
        choices = self.with_quiet_notes()
        before = self.patterns(choices)
        choices.get_kit().set_quiet_notes(False)
        after = self.patterns(choices)
        self.assertNotEqual(after, before)
        # The groove still has them to switch on again.
        self.assertTrue(choices.get_kit().has_quiet_notes())
        choices.get_kit().set_quiet_notes(True)
        self.assertEqual(self.patterns(choices), before)

    def test_a_groove_with_no_quiet_notes_has_none_to_switch_off(self):
        self.assertTrue(any(not chosen(genre=place).get_kit().has_quiet_notes() for place in range(len(genre_names()))))
        self.assertFalse(WizardChoices().get_kit().has_quiet_notes())

    def test_both_are_kept_with_the_choices_and_another_subgenre_starts_afresh(self):
        choices = self.with_quiet_notes()
        self.assertNotIn(wizard_limits.QUIET_NOTES_KEPT, choices.to_data())
        choices.get_kit().set_quiet_notes(False)
        choices.get_kit().set_fills(wizard_limits.MOST_FILLS)
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.to_data(), choices.to_data())
        self.assertFalse(again.get_kit().plays_quiet_notes())
        self.assertEqual(again.get_kit().get_fills(), wizard_limits.MOST_FILLS)
        again.set_subgenre([name for name in again.subgenres() if name != again.get_subgenre()][0])
        self.assertTrue(again.get_kit().plays_quiet_notes())


class TestWizardMelodySettings(unittest.TestCase):
    """A melody style's own settings: shown for the style in use, set by the genre until changed, heard, kept and refused."""

    def rock(self, *, style=None):
        choices = chosen(genre=genre_names().index(A_GENRE_WITH_TUNES))
        choices.set_seed(A_SEED)
        if style is not None:
            choices.set_melody(style)
        return choices

    def patterns(self, choices):
        return choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.PATTERNS]

    def another_value(self, *, choices, name):
        """A value of a setting other than the one it has."""
        now = choices.get_melody_setting(name)
        if choices.melody_setting_is_switch(name):
            return not now
        lowest, highest = choices.melody_setting_range(name)
        return lowest if now != lowest else highest

    def styles(self):
        """The usual style, under no name, and each style the subgenre can be asked for."""
        return [None, *self.rock().melody_styles()]

    def test_each_style_shows_its_own_settings_and_the_usual_style_its_range(self):
        self.assertGreater(len(self.styles()), 1)
        for style in self.styles():
            self.assertEqual(self.rock(style=style).melody_settings(), list(wizard_limits.MELODY_SETTINGS_OF[style]))
        self.assertEqual(WizardChoices().melody_settings(), [])

    def test_a_setting_is_the_genres_until_changed_and_every_setting_changes_the_song_and_is_kept(self):
        for style in self.styles():
            for name in self.rock(style=style).melody_settings():
                choices = self.rock(style=style)
                before = self.patterns(choices)
                self.assertNotIn(wizard_limits.MELODY_SETTINGS_KEPT, choices.to_data())
                value = self.another_value(choices=choices, name=name)
                choices.set_melody_setting(name=name, value=value)
                self.assertEqual(choices.get_melody_setting(name), value)
                self.assertNotEqual(self.patterns(choices), before, (style, name))
                again = WizardChoices.from_data(choices.to_data())
                self.assertEqual(again.get_melody_setting(name), value)
                self.assertEqual(self.patterns(again), self.patterns(choices))

    def test_the_usual_style_has_no_settings_of_its_own_since_a_tunes_range_is_its_players_gauge(self):
        self.assertEqual(self.rock().melody_settings(), [])
        self.assertTrue(self.rock(style=melody.EVOLVING).melody_settings())

    def test_a_setting_of_another_style_is_kept_and_says_nothing(self):
        choices = self.rock(style=melody.SERIAL)
        choices.set_melody_setting(name=melody.LEAPS, value=True)
        choices.set_melody(melody.SMART)
        self.assertEqual(self.patterns(choices), self.patterns(self.rock(style=melody.SMART)))
        choices.set_melody(melody.SERIAL)
        self.assertTrue(choices.get_melody_setting(melody.LEAPS))

    def test_a_setting_the_style_has_not_and_a_value_out_of_range_are_refused(self):
        choices = self.rock(style=melody.SERIAL)
        for refused in (lambda: choices.set_melody_setting(name=melody.MOVE, value=A_SECOND), lambda: choices.set_melody_setting(name=NO_SUCH_GAUGE, value=True),
                        lambda: choices.set_melody_setting(name=melody.LEAPS, value=A_SECOND)):
            with self.assertRaises(ValueError):
                refused()
        evolving = self.rock(style=melody.EVOLVING)
        lowest, highest = evolving.melody_setting_range(melody.MOVE)
        for value in (lowest - 1, highest + 1, True, NOT_A_NUMBER):
            with self.assertRaises(ValueError):
                evolving.set_melody_setting(name=melody.MOVE, value=value)

    def test_a_new_genre_forgets_the_settings(self):
        choices = self.rock(style=melody.EVOLVING)
        choices.set_melody_setting(name=melody.MOVE, value=self.another_value(choices=choices, name=melody.MOVE))
        choices.set_genre(ANOTHER_GENRE)
        self.assertNotIn(wizard_limits.MELODY_SETTINGS_KEPT, choices.to_data())


class TestWizardPlayerRows(unittest.TestCase):
    """The rows of numbers the serial style deals to a player's notes: shown while the style is in use, a player's own, kept and made into the song."""

    def serial(self):
        choices = chosen(genre=genre_names().index(A_GENRE_WITH_STYLES))
        choices.set_melody(melody.SERIAL)
        choices.set_seed(wizard_limits.FIRST_SEED)
        return choices

    def a_player(self, choices):
        return next(role for role in choices.roles_in() if choices.player_rows(role))

    def parts(self, choices):
        return arranged(style=style_of(choices.get_genre()), song=choices.song_picks(A_NAME))[arranger.PARTS]

    def moved(self, *, choices, name, row):
        """A row with every cell at the end of its range the cell is further from."""
        lowest, highest = choices.row_limits(name)
        return [lowest if value - lowest > highest - value else highest for value in row]

    def test_rows_show_only_under_the_serial_style_and_only_for_a_player_of_lines(self):
        choices = self.serial()
        with_rows = [role for role in choices.roles_in() if choices.player_rows(role)]
        self.assertTrue(with_rows)
        self.assertLess(len(with_rows), len(choices.roles_in()))
        for role in with_rows:
            self.assertEqual(choices.player_rows(role), list(wizard_limits.PLAYER_ROWS))
        choices.set_melody(None)
        for role in choices.roles_in():
            self.assertEqual(choices.player_rows(role), [])

    def test_a_row_is_the_genres_until_changed_and_each_row_changed_changes_the_song(self):
        choices = self.serial()
        role = self.a_player(choices)
        for name in wizard_limits.PLAYER_ROWS:
            before = self.parts(choices)
            usual = choices.get_player_row(role=role, name=name)
            self.assertEqual(usual, choices.genre_row(role=role, name=name))
            self.assertFalse(choices.player_row_is_own(role=role, name=name))
            changed = self.moved(choices=choices, name=name, row=usual)
            choices.set_player_row(role=role, name=name, values=changed)
            self.assertTrue(choices.player_row_is_own(role=role, name=name))
            self.assertEqual(choices.get_player_row(role=role, name=name), changed)
            self.assertNotEqual(self.parts(choices), before, name)
            again = WizardChoices.from_data(choices.to_data())
            self.assertEqual(again.get_player_row(role=role, name=name), changed)
            self.assertEqual(self.parts(again), self.parts(choices))
            # The genre's own row given back is no row of the player's, and the song is as it was.
            choices.set_player_row(role=role, name=name, values=usual)
            self.assertFalse(choices.player_row_is_own(role=role, name=name))
            self.assertEqual(self.parts(choices), before)
            self.assertNotIn(wizard_limits.PLAYER_ROWS_KEPT, choices.to_data())

    def test_a_row_changes_only_its_players_parts(self):
        choices = self.serial()
        role = self.a_player(choices)
        before = self.parts(choices)
        choices.set_player_row(role=role, name=melody.LENGTHS, values=self.moved(choices=choices, name=melody.LENGTHS, row=choices.get_player_row(role=role, name=melody.LENGTHS)))
        after = self.parts(choices)
        # A part that changed is a tune player's: the player's own, or the part of a player of lines who plays the tune along.
        with_rows = [other for other in choices.roles_in() if choices.player_rows(other)]
        for part in before:
            if before[part] != after[part]:
                self.assertTrue(any(other in part for other in with_rows), part)

    def test_a_row_out_of_range_too_long_or_of_another_style_is_refused(self):
        choices = self.serial()
        role = self.a_player(choices)
        lowest, highest = choices.row_limits(melody.LENGTHS)
        for values in ([], [lowest] * (wizard_limits.MOST_ROW_CELLS + 1), [lowest - 1], [highest + 1], [True], [NOT_A_NUMBER], NOT_A_NUMBER):
            with self.assertRaises(ValueError):
                choices.set_player_row(role=role, name=melody.LENGTHS, values=values)
        with self.assertRaises(ValueError):
            choices.set_player_row(role=role, name=NO_SUCH_GAUGE, values=[lowest])
        choices.set_player_row(role=role, name=melody.LENGTHS, values=[lowest] * wizard_limits.MOST_ROW_CELLS)
        choices.set_player_row(role=role, name=melody.LENGTHS, values=[highest])
        choices.set_melody(None)
        with self.assertRaises(ValueError):
            choices.get_player_row(role=role, name=melody.LENGTHS)

    def test_a_row_kept_says_nothing_under_another_style_and_a_new_genre_forgets_the_rows(self):
        choices = self.serial()
        role = self.a_player(choices)
        choices.set_player_row(role=role, name=melody.LENGTHS, values=[choices.row_limits(melody.LENGTHS)[1]])
        choices.set_melody(None)
        plain = self.serial()
        plain.set_melody(None)
        self.assertEqual(self.parts(choices), self.parts(plain))
        choices.set_genre(ANOTHER_GENRE)
        self.assertNotIn(wizard_limits.PLAYER_ROWS_KEPT, choices.to_data())

    def test_the_genres_own_rows_are_those_its_players_are_written_with(self):
        choices = chosen(genre=genre_names().index(A_SERIAL_GENRE))
        role = self.a_player(choices)
        written = next(entry for entry in style_of(A_SERIAL_GENRE)[ROLES_OF_STYLE] if entry[ROLE_OF_ENTRY] == role)[HABITS_OF_ENTRY]
        self.assertEqual(choices.get_player_row(role=role, name=melody.LENGTHS), written[melody.LENGTHS])


class TestWizardMelodyGauges(unittest.TestCase):
    """The smart melody style's gauges: shown once the style is chosen, set by the genre, moved, kept and refused."""

    def rock(self):
        choices = chosen(genre=genre_names().index(A_GENRE_WITH_TUNES))
        choices.set_seed(A_SEED)
        return choices

    def patterns(self, choices):
        return choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.PATTERNS]

    def test_a_song_has_a_hook_where_the_genre_says_until_switched_and_the_switch_is_kept(self):
        choices = self.rock()
        self.assertTrue(choices.get_hook().can_have_hook())
        self.assertTrue(choices.get_hook().usual_hook())
        self.assertTrue(choices.get_hook().has_hook())
        with_hook = self.patterns(choices)
        choices.get_hook().set_hook(False)
        self.assertFalse(choices.get_hook().has_hook())
        self.assertNotEqual(self.patterns(choices), with_hook)
        again = WizardChoices.from_data(choices.to_data())
        self.assertFalse(again.get_hook().has_hook())
        self.assertEqual(self.patterns(again), self.patterns(choices))
        choices.get_hook().set_hook(True)
        self.assertEqual(self.patterns(choices), with_hook)
        self.assertNotIn(wizard_limits.HOOK_KEPT, choices.to_data())

    def test_the_hooks_notes_are_read_from_the_song_as_chosen_and_follow_every_choice(self):
        choices = self.rock()
        steps, steps_in_bar, notes = choices.get_hook().hook_notes()
        self.assertEqual(steps % steps_in_bar, 0)
        self.assertTrue(notes)
        for start, length, pitch in notes:
            self.assertGreaterEqual(start, 0)
            self.assertLessEqual(start + length, steps)
            self.assertIn((pitch - choices.root_half_steps()) % NOTES_IN_AN_OCTAVE, choices.scale_half_steps())
        self.assertEqual(WizardChoices.from_data(choices.to_data()).get_hook().hook_notes(), choices.get_hook().hook_notes())
        choices.set_root(ANOTHER_ROOT)
        self.assertNotEqual(choices.get_hook().hook_notes()[2], notes)
        choices.set_seed(ANOTHER_SEED)
        self.assertNotEqual(choices.get_hook().hook_notes(), (steps, steps_in_bar, notes))

    def test_a_new_hook_changes_the_hook_and_no_other_part_and_is_kept(self):
        choices = self.rock()
        before = arranged(style=style_of(choices.get_genre()), song=choices.song_picks(A_NAME))[arranger.PARTS]
        first = choices.get_hook().hook_notes()
        choices.get_hook().new_hook()
        self.assertEqual(choices.get_hook().get_hook_take(), 1)
        self.assertNotEqual(choices.get_hook().hook_notes(), first)
        after = arranged(style=style_of(choices.get_genre()), song=choices.song_picks(A_NAME))[arranger.PARTS]
        changed = [part for part in before if before[part] != after[part]]
        self.assertTrue(changed)
        # Only parts of the sections that have the hook change: the tune's, and any player's who plays the hook with the tune.
        sections = style_of(choices.get_genre())[SECTIONS_OF_STYLE]
        with_hook = [kind for kind in sections if any(entry.get(HOOK_MARK) for entry in sections[kind].get(PLAN_OF_SECTION, []))]
        for part in changed:
            self.assertTrue(any(part.startswith(kind) for kind in with_hook), part)
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.get_hook().get_hook_take(), 1)
        self.assertEqual(again.get_hook().hook_notes(), choices.get_hook().hook_notes())

    def test_a_new_hook_is_refused_without_a_hook_and_a_new_genre_goes_back_to_the_first_take(self):
        choices = self.rock()
        choices.get_hook().new_hook()
        choices.get_hook().set_hook(False)
        with self.assertRaises(ValueError):
            choices.get_hook().new_hook()
        choices.set_genre(ANOTHER_GENRE)
        self.assertEqual(choices.get_hook().get_hook_take(), 0)
        # A take kept that is no take is left out, as any kept choice that no longer holds is.
        for take in (-1, True, NOT_A_NUMBER):
            self.assertEqual(WizardChoices.from_data({**self.rock().to_data(), wizard_limits.HOOK_TAKE_KEPT: take}).get_hook().get_hook_take(), 0)

    def test_a_song_with_no_hook_has_no_hook_notes(self):
        choices = self.rock()
        choices.get_hook().set_hook(False)
        self.assertIsNone(choices.get_hook().hook_notes())
        for genre in genre_names():
            other = chosen(genre=genre_names().index(genre))
            if not other.get_hook().can_have_hook():
                self.assertIsNone(other.get_hook().hook_notes(), genre)

    def test_a_genre_whose_sections_mark_a_hook_has_none_until_asked_and_a_genre_with_none_refuses(self):
        for genre in genre_names():
            choices = chosen(genre=genre_names().index(genre))
            if not choices.get_hook().can_have_hook():
                self.assertFalse(choices.get_hook().has_hook(), genre)
                with self.assertRaises(ValueError):
                    choices.get_hook().set_hook(True)
            self.assertEqual(choices.get_hook().usual_hook(), genre in GENRES_WITH_A_HOOK, genre)

    def test_the_gauges_show_only_while_the_melody_style_is_smart(self):
        choices = self.rock()
        self.assertEqual(choices.gauges(), [])
        choices.set_melody(melody.SMART)
        self.assertEqual(choices.gauges(), list(melody.DEFAULT_GAUGES))
        choices.set_melody(None)
        self.assertEqual(choices.gauges(), [])

    def test_a_gauge_stands_where_the_genre_sets_it_until_moved(self):
        choices = self.rock()
        choices.set_melody(melody.SMART)
        style = style_of(A_GENRE_WITH_TUNES)[arranger.MELODY]
        own = (style if melody.GRID in style else style[choices.meter()])[melody.SMART]
        for name in choices.gauges():
            self.assertEqual(choices.get_gauge(name), own.get(name, melody.DEFAULT_GAUGES[name]))
            self.assertIn(choices.get_gauge(name), range(melody.LOWEST_GAUGE, melody.HIGHEST_GAUGE + 1))

    def test_a_gauge_set_where_it_stands_makes_the_same_song_and_a_moved_one_another_and_is_kept(self):
        choices = self.rock()
        choices.set_melody(melody.SMART)
        usual = self.patterns(choices)
        name = choices.gauges()[0]
        choices.set_gauge(name=name, position=choices.get_gauge(name))
        self.assertEqual(self.patterns(choices), usual)
        choices.set_gauge(name=name, position=melody.HIGHEST_GAUGE)
        self.assertNotEqual(self.patterns(choices), usual)
        again = WizardChoices.from_data(choices.to_data())
        self.assertEqual(again.get_gauge(name), melody.HIGHEST_GAUGE)
        self.assertEqual(self.patterns(again), self.patterns(choices))

    def test_a_gauge_there_is_none_of_and_a_position_out_of_range_are_refused(self):
        choices = self.rock()
        choices.set_melody(melody.SMART)
        name = choices.gauges()[0]
        for refused_name, position in ((NO_SUCH_GAUGE, melody.LOWEST_GAUGE), (name, melody.LOWEST_GAUGE - 1), (name, melody.HIGHEST_GAUGE + 1), (name, True), (name, A_GAUGE_IN_WORDS)):
            with self.assertRaises(ValueError) as refused:
                choices.set_gauge(name=refused_name, position=position)
            self.assertEqual(str(refused.exception), errors.ERR_WIZARD_GAUGE.format(name=refused_name, low=melody.LOWEST_GAUGE, high=melody.HIGHEST_GAUGE, value=position))


class TestWizardMinorTunes(unittest.TestCase):
    """A minor song's tune is made of the style's minor notes, where the style gives some, and a major song's of its usual ones."""

    def degrees_sung(self, choices):
        """Return the scale degrees of every tune of the song the choices make: the lead's part in each section."""
        style = style_of(choices.get_genre())
        parts = arranged(style=style, song=choices.song_picks(A_NAME))[arranger.PARTS]
        tunes = [part for name, part in parts.items() if name.endswith(composer_text.MSG_PART_OF_SECTION.format(EMPTY, LEAD_ROLE)) and notation.LINES in part]
        return {note[notation.DEGREE] for part in tunes for line in part[notation.LINES] for note in line if notation.DEGREE in note}

    def habits(self, choices):
        habits = style_of(choices.get_genre())[arranger.MELODY]
        return habits if melody.GRID in habits else habits[choices.meter()]

    def test_every_subgenre_of_a_style_with_minor_notes_sings_the_notes_of_its_scale_type(self):
        checked = set()
        for place, genre in enumerate(genre_names()):
            for subgenre in range(len(chosen(genre=place).subgenres())):
                choices = chosen(genre=place, subgenre=subgenre)
                choices.set_seed(A_SEED)
                habits = self.habits(choices)
                if arranger.BY_SCALE_TYPE not in habits:
                    continue
                own = habits[arranger.BY_SCALE_TYPE].get(choices.get_scale_type(), habits)
                checked.add(choices.get_scale_type())
                with self.subTest(subgenre=choices.get_subgenre()):
                    self.assertLessEqual(self.degrees_sung(choices), {note[notation.DEGREE] for note in own[melody.LADDER]})
        self.assertGreater(len(checked), 1)

    def test_the_minor_notes_differ_from_the_usual_ones_and_rest_on_the_first(self):
        choices = chosen(genre=genre_names().index(A_GENRE_WITH_TUNES))
        minor = self.habits(choices)[arranger.BY_SCALE_TYPE][wizard_limits.MINOR]
        self.assertNotEqual(minor[melody.LADDER], self.habits(choices)[melody.LADDER])
        self.assertEqual(minor[melody.HOME][notation.DEGREE], FIRST_DEGREE)


class TestWizardStandIns(unittest.TestCase):
    """A sound that stands in for a player by subgenre, as for a singer: the player stays, and the sound alone is chosen."""

    def test_every_stand_in_is_a_sound_of_its_style_for_a_player_and_a_subgenre_of_the_style(self):
        found = False
        for place, genre in enumerate(genre_names()):
            style = style_of(genre)
            choices = chosen(genre=place)
            for role, by_subgenre in style.get(wizard_limits.STAND_INS, {}).items():
                found = True
                self.assertIn(role, choices.roles())
                self.assertLessEqual(set(by_subgenre), set(choices.subgenres()))
                self.assertLessEqual(set(by_subgenre.values()), set(style[arranger.SOUNDS]))
        self.assertTrue(found)

    def test_the_player_plays_the_stand_in_in_the_song_made_and_keeps_one_way_and_a_sound_chosen_wins(self):
        genre = genre_names().index(A_GENRE_WITH_TUNES)
        style = style_of(A_GENRE_WITH_TUNES)
        for role, by_subgenre in style[wizard_limits.STAND_INS].items():
            for subgenre, sound in by_subgenre.items():
                choices = chosen(genre=genre, subgenre=chosen(genre=genre).subgenres().index(subgenre))
                choices.set_seed(A_SEED)
                number = style[arranger.SOUNDS][sound]
                with self.subTest(subgenre=subgenre):
                    self.assertEqual(choices.get_sounds().get_sound(role), number)
                    self.assertFalse(choices.get_sounds().has_own_sound(role))
                    self.assertEqual(len(choices.ways(role=role, trait=role)), 1)
                    self.assertIn(number, choices.get_sounds().genre_sounds(role))
                    self.assertIn(number, self.sounds_made(choices))
        choices.get_sounds().set_sound(role=role, sound=A_SOUND_OF_NO_STYLE)
        self.assertIn(A_SOUND_OF_NO_STYLE, self.sounds_made(choices))

    def sounds_made(self, choices):
        instruments = choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.INSTRUMENTS]
        return {instrument.get(GM_SOUND_KEY) for instrument in instruments.values()}


class TestWizardProgressionByChance(unittest.TestCase):
    """A progression nobody chose is drawn by the seed from the subgenre's, so that two runs differ in their chords."""

    def rock(self):
        return chosen(genre=genre_names().index(A_GENRE_WITH_TUNES))

    def drawn(self, choices):
        return choices.song_picks(A_NAME)[arranger.PICKS][choices.progression_trait()]

    def test_a_song_starts_with_its_progression_left_to_chance_and_runs_draw_different_ones(self):
        choices = self.rock()
        self.assertTrue(choices.has_any_progression())
        drawn = set()
        for seed in range(A_SEED, A_SEED + MANY_RUNS):
            choices.set_seed(seed)
            drawn.add(self.drawn(choices))
            self.assertEqual(self.drawn(choices), self.drawn(choices))
        self.assertGreater(len(drawn), 1)
        self.assertLessEqual(drawn, set(choices.song_ways(choices.progression_trait())))

    def test_with_no_seed_nothing_is_drawn_and_the_subgenres_usual_one_is_played(self):
        choices = self.rock()
        self.assertEqual(choices.progressions_by_chance(), [])
        self.assertNotIn(choices.progression_trait(), choices.song_picks(A_NAME)[arranger.PICKS])

    def test_a_progression_chosen_is_played_on_every_run_until_it_is_left_to_chance_again(self):
        choices = self.rock()
        trait = choices.progression_trait()
        wanted = choices.song_ways(trait)[-1]
        choices.set_way(trait=trait, value=wanted)
        self.assertFalse(choices.has_any_progression())
        for seed in range(A_SEED, A_SEED + MANY_RUNS):
            choices.set_seed(seed)
            self.assertEqual(self.drawn(choices), wanted)
        self.assertFalse(WizardChoices.from_data(choices.to_data()).has_any_progression())
        choices.set_any_progression()
        self.assertTrue(choices.has_any_progression())

    def test_only_progressions_written_for_the_songs_scale_type_are_drawn_where_the_style_has_one(self):
        for place, genre in enumerate(genre_names()):
            for subgenre in range(len(chosen(genre=place).subgenres())):
                choices = chosen(genre=place, subgenre=subgenre)
                trait = choices.progression_trait()
                if trait is None:
                    continue
                entries = values_of(style=style_of(genre), trait=trait)
                suited = {way for way in choices.song_ways(trait) if entries[way].get(arranger.SCALE_TYPE, wizard_limits.MAJOR) == choices.get_scale_type()}
                # A progression the subgenre's harmonic family never uses is drawn by no seed, and is chosen by hand.
                suited = {way for way in suited if share_in(style=style_of(genre), entry=entries[way], template=choices.get_subgenre())} or suited
                for seed in range(A_SEED, A_SEED + MANY_RUNS):
                    choices.set_seed(seed)
                    with self.subTest(subgenre=choices.get_subgenre(), seed=seed):
                        self.assertEqual(sorted(choices.progressions_by_chance()), sorted(suited or choices.song_ways(trait)))

    def test_every_draw_of_every_subgenre_makes_a_song_that_plays(self):
        for place in range(len(genre_names())):
            for subgenre in range(len(chosen(genre=place).subgenres())):
                choices = chosen(genre=place, subgenre=subgenre)
                for seed in range(A_SEED, A_SEED + A_FEW_RUNS):
                    choices.set_seed(seed)
                    with self.subTest(subgenre=choices.get_subgenre(), seed=seed):
                        SongRenderer(choices.made_setlist(name=A_NAME, version=version.VERSION).get_song(A_NAME)).render()


class EveryPlayerOfAGenre:
    """Every player of every subgenre of one genre, put in, left out, played each way and made busier: a class for each genre,
    since the whole takes long and the classes run side by side."""

    GENRE = None

    def test_every_player_of_every_subgenre_can_be_put_in_or_left_out_played_each_way_and_made_busier(self):
        place = genre_names().index(self.GENRE)
        for subgenre in range(len(chosen(genre=place).subgenres())):
            choices = chosen(genre=place, subgenre=subgenre)
            choices.set_seed(A_SEED)
            for role in choices.roles():
                with self.subTest(subgenre=choices.get_subgenre(), role=role):
                    self.try_a_player(choices=choices, role=role)

    def try_a_player(self, *, choices, role):
        was_in = choices.role_is_in(role)
        # Every player of every subgenre has a way of playing written, so each can be put in.
        self.assertTrue(choices.role_can_play(role))
        choices.set_role_in(role=role, on=True)
        for trait in choices.role_traits(role):
            usual = choices.get_way(trait)
            self.assertIn(usual, choices.ways(role=role, trait=trait))
            for way in choices.ways(role=role, trait=trait):
                choices.set_way(trait=trait, value=way)
                choices.made_setlist(name=A_NAME, version=version.VERSION)
            choices.set_way(trait=trait, value=usual)
        if choices.has_busy(role):
            for level in (wizard_limits.LEAST_BUSY, wizard_limits.MOST_BUSY, wizard_limits.USUAL_BUSY):
                choices.set_busy(role=role, level=level)
                choices.made_setlist(name=A_NAME, version=version.VERSION)
        if len(choices.roles_in()) > 1:
            choices.set_role_in(role=role, on=False)
            self.assertFalse(choices.role_is_in(role))
            choices.made_setlist(name=A_NAME, version=version.VERSION)
        choices.set_role_in(role=role, on=was_in or len(choices.roles_in()) < 1)


class EverySongWayOfAGenre:
    """Every way of every trait of the whole song, in every subgenre of one genre, makes a song that plays: a class for each
    genre, since the whole takes long and the classes run side by side."""

    GENRE = None

    def test_every_way_of_every_song_trait_of_every_subgenre_makes_a_song_that_plays(self):
        place = genre_names().index(self.GENRE)
        for subgenre in range(len(chosen(genre=place).subgenres())):
            choices = chosen(genre=place, subgenre=subgenre)
            choices.set_seed(A_SEED)
            for traits in (wizard_limits.PROGRESSION_TRAITS, wizard_limits.FILLS_TRAITS):
                trait = choices.song_trait(traits)
                for way in (choices.song_ways(trait) if trait else []):
                    with self.subTest(subgenre=choices.get_subgenre(), trait=trait, way=way):
                        choices.set_way(trait=trait, value=way)
                        self.assertEqual(choices.get_way(trait), way)
                        SongRenderer(choices.made_setlist(name=A_NAME, version=version.VERSION).get_song(A_NAME)).render()


class TestEverySongWayOfBlues(EverySongWayOfAGenre, unittest.TestCase):
    GENRE = 'blues'


class TestEverySongWayOfElectronic(EverySongWayOfAGenre, unittest.TestCase):
    GENRE = 'electronic'


class TestEverySongWayOfExperimental(EverySongWayOfAGenre, unittest.TestCase):
    GENRE = 'experimental'


class TestEverySongWayOfRock(EverySongWayOfAGenre, unittest.TestCase):
    GENRE = 'rock'


class TestEverySongWayOfSixtiesPop(EverySongWayOfAGenre, unittest.TestCase):
    GENRE = 'sixties_pop'


class TestEverySongWayOfSoulFunk(EverySongWayOfAGenre, unittest.TestCase):
    GENRE = 'soul_funk'


class TestEveryPlayerOfBlues(EveryPlayerOfAGenre, unittest.TestCase):
    GENRE = 'blues'


class TestEveryPlayerOfElectronic(EveryPlayerOfAGenre, unittest.TestCase):
    GENRE = 'electronic'


class TestEveryPlayerOfExperimental(EveryPlayerOfAGenre, unittest.TestCase):
    GENRE = 'experimental'


class TestEveryPlayerOfRock(EveryPlayerOfAGenre, unittest.TestCase):
    GENRE = 'rock'


class TestEveryPlayerOfSixtiesPop(EveryPlayerOfAGenre, unittest.TestCase):
    GENRE = 'sixties_pop'


class TestEveryPlayerOfSoulFunk(EveryPlayerOfAGenre, unittest.TestCase):
    GENRE = 'soul_funk'


class TestEveryGenreHasItsPlayersTested(unittest.TestCase):

    def test_every_genre_has_a_class_that_tries_its_players(self):
        tried = sorted(tests.GENRE for tests in EveryPlayerOfAGenre.__subclasses__())
        self.assertEqual(tried, sorted(genre_names()))

    def test_every_genre_has_a_class_that_tries_its_song_ways(self):
        tried = sorted(tests.GENRE for tests in EverySongWayOfAGenre.__subclasses__())
        self.assertEqual(tried, sorted(genre_names()))


class TestWizardBand(unittest.TestCase):
    """The band of the wizard's choices: who is in, how each plays and how busy each is."""

    def rock(self):
        choices = chosen(genre=genre_names().index(A_GENRE_WITH_TUNES))
        choices.set_seed(A_SEED)
        return choices

    def tracks_of(self, choices):
        setlist = choices.made_setlist(name=A_NAME, version=version.VERSION)
        return setlist.get_song(A_NAME).get_track_names()

    def test_no_band_is_known_before_a_subgenre_is_chosen(self):
        choices = WizardChoices()
        self.assertEqual(choices.roles(), [])
        with self.assertRaises(ValueError):
            choices.set_role_in(role=NOT_A_CHOICE, on=True)

    def test_a_player_left_out_has_no_track_and_the_drums_left_out_leave_no_drum_track(self):
        choices = self.rock()
        whole = self.tracks_of(choices)
        choices.set_role_in(role=A_BASS, on=False)
        self.assertEqual(self.tracks_of(choices), [track for track in whole if track != A_BASS])
        choices.set_role_in(role=A_BASS, on=True)
        self.assertEqual(self.tracks_of(choices), whole)
        choices.set_role_in(role=arranger.DRUMS, on=False)
        left = self.tracks_of(choices)
        self.assertEqual(left, [track for track in whole if track in choices.roles() or track == composer_text.MSG_CHORDS_TRACK])

    def test_the_last_player_cannot_be_left_out(self):
        choices = self.rock()
        last = choices.roles_in()[-1]
        for role in choices.roles_in()[:-1]:
            choices.set_role_in(role=role, on=False)
        with self.assertRaises(ValueError):
            choices.set_role_in(role=last, on=False)
        self.assertEqual(choices.roles_in(), [last])

    def test_a_player_who_usually_sits_out_comes_in_playing_a_way_that_sounds(self):
        rock = genre_names().index(A_GENRE_WITH_TUNES)
        every = [chosen(genre=rock, subgenre=place) for place in range(len(chosen(genre=rock).subgenres()))]
        choices = next(choices for choices in every if len(choices.roles_in()) < len(choices.roles()))
        choices.set_seed(A_SEED)
        out = [role for role in choices.roles() if not choices.role_is_in(role)]
        choices.set_role_in(role=out[0], on=True)
        self.assertTrue(choices.role_is_in(out[0]))
        self.assertIn(out[0], self.tracks_of(choices))

    def test_each_player_starts_a_little_busy_and_busier_players_change_the_song(self):
        choices = self.rock()
        self.assertEqual(choices.get_busy(arranger.DRUMS), wizard_limits.USUAL_BUSY)
        usual = choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.PATTERNS]
        choices.set_busy(role=arranger.DRUMS, level=wizard_limits.MOST_BUSY)
        self.assertNotEqual(choices.made_setlist(name=A_NAME, version=version.VERSION).to_data()[Section.PATTERNS], usual)
        for level in (wizard_limits.LEAST_BUSY - 1, wizard_limits.MOST_BUSY + 1, NOT_A_NUMBER, True):
            with self.assertRaises(ValueError):
                choices.set_busy(role=arranger.DRUMS, level=level)
        self.assertEqual(choices.get_busy(arranger.DRUMS), wizard_limits.MOST_BUSY)

    def test_a_way_of_playing_that_is_not_the_traits_is_refused(self):
        choices = self.rock()
        trait = choices.role_traits(A_BASS)[0]
        before = choices.to_data()
        with self.assertRaises(ValueError):
            choices.set_way(trait=trait, value=NOT_A_CHOICE)
        self.assertEqual(choices.to_data(), before)

    def test_the_band_is_kept_with_the_choices_and_another_subgenre_starts_a_band_afresh(self):
        choices = self.rock()
        trait = choices.role_traits(A_BASS)[0]
        choices.set_way(trait=trait, value=choices.ways(role=A_BASS, trait=trait)[-1])
        choices.set_busy(role=A_BASS, level=wizard_limits.MOST_BUSY)
        choices.set_role_in(role=choices.roles_in()[0], on=False)
        data = choices.to_data()
        again = WizardChoices.from_data(data)
        self.assertEqual(again.to_data(), data)
        self.assertEqual(again.made_setlist(name=A_NAME, version=version.VERSION).to_data(), choices.made_setlist(name=A_NAME, version=version.VERSION).to_data())
        choices.set_subgenre(choices.subgenres()[-1])
        self.assertEqual(choices.get_busy(A_BASS), wizard_limits.USUAL_BUSY)
        self.assertNotIn(arranger.WITHOUT, choices.to_data())

    def test_choices_kept_before_the_band_could_be_chosen_name_no_levels_and_make_the_same_song(self):
        choices = self.rock()
        old = {field: value for field, value in choices.to_data().items() if field != arranger.PLAYERS}
        again = WizardChoices.from_data(old)
        self.assertIsNone(again.get_busy(arranger.DRUMS))
        self.assertEqual(again.to_data(), old)
