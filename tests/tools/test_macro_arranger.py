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

"""The MacroComposer's arranger (internal_tools/macro_composer/arranger.py and melody.py): a song's picks and a style template
made into a whole song, the picks checked against what each needs, and a tune sketched by rule when the song gives none."""

import os
import sys
import unittest

from llamatron.composition.setlist import Setlist
from llamatron.support.safe_yaml import load_safely
from llamatron.support.version import VERSION

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, 'internal_tools', 'macro_composer')
sys.path.insert(0, TOOLS)

import arranger  # noqa: E402
import composer  # noqa: E402
import melody  # noqa: E402
import notation  # noqa: E402
import players  # noqa: E402

FILE_ENCODING = 'utf-8'
STYLE_TEMPLATES = os.path.join(TOOLS, 'style_templates')
YAML = '.yml'
BLUES = 'blues'
SHUFFLE = 'shuffle'
SLOW_BLUES = 'slow blues'
NO_SUCH = 'polka'
SONG_NAME = 'a_song'
SONG_TITLE = 'A song'
KEY_ROOT = 'A'
LOW_ROOT = 'D'
MAJOR = 'major'
SEED = 5
OTHER_SEED = 6
INTRO = 'intro'
CHORUS = 'chorus'
SOLO = 'solo'
ENDING = 'ending'
FORM = [INTRO, CHORUS, CHORUS, SOLO, ENDING]
SECOND_CHORUS = 'chorus 2'
BASS = 'bass'
LEAD = 'lead'
ANSWERS = 'answers'
COMPING = 'comping'
DRUMS_TRAIT = 'drums'
TWELVE_EIGHT = '12/8'
SLOW_DRUMS = 'slow twelve-eight'
STABS = 'guitar stabs on the upbeats'
GUITARIFIES = 'guitarifies'
GUITARIFY = 'guitarify'
ROCK = 'rock'
ROCK_KIND = 'beat group'
KICK = 'kick'
SNARE = 'snare'
GUITAR = 'guitar'
METER = 'meter'
SIX_EIGHT = '6/8'
BALLAD = 'rock ballad'
OWN_CHORDS = [1, 1, 4, 4]
WHOLE = 100
A_SIXTH_BAR = 6
OWN_LINE = [{notation.DEGREE: 1, notation.STEPS: 12}, {notation.REST: 12}]
SILENT_LINE = [{notation.REST: 12}, {notation.REST: 12}]


def read(path):
    with open(path, encoding=FILE_ENCODING) as file:
        return load_safely(file)


def style_files():
    return sorted(os.path.join(STYLE_TEMPLATES, name) for name in os.listdir(STYLE_TEMPLATES) if name.endswith(YAML))


def a_song(*, template=SHUFFLE, picks=None, sections=None, seed=SEED):
    song = {arranger.NAME: SONG_NAME, arranger.TITLE: SONG_TITLE, arranger.STYLE: BLUES, arranger.TEMPLATE: template,
            arranger.KEY: {arranger.ROOT: KEY_ROOT, arranger.TYPE: MAJOR}, arranger.SEED: seed, arranger.FORM: list(FORM)}
    if picks:
        song[arranger.PICKS] = picks
    if sections:
        song[arranger.SECTIONS] = sections
    return song


def steps_in(line):
    return sum(note.get(notation.REST, note.get(notation.STEPS, 0)) for note in line)


class TestStyleTemplates(unittest.TestCase):
    """Every style template shipped: its shares, its bars, what its values need and its templates' picks."""

    def test_every_traits_shares_add_to_a_hundred(self):
        for path in style_files():
            for trait, values in read(path)[arranger.TRAITS].items():
                if isinstance(values, list):
                    with self.subTest(path=path, trait=trait):
                        self.assertEqual(sum(value[arranger.SHARE] for value in values), WHOLE)

    def test_every_need_and_every_templates_pick_names_a_value(self):
        for path in style_files():
            style = read(path)
            for trait, values in style[arranger.TRAITS].items():
                for value in values if isinstance(values, list) else []:
                    for needed, wanted in value.get(arranger.NEEDS, {}).items():
                        with self.subTest(path=path, trait=trait, value=value[arranger.VALUE]):
                            self.assertIn(wanted, arranger.values_of(style=style, trait=needed))
            for name, picks in style[arranger.TEMPLATES].items():
                for trait, value in picks.items():
                    if arranger.values_of(style=style, trait=trait):
                        with self.subTest(path=path, template=name, trait=trait):
                            self.assertIn(value, arranger.values_of(style=style, trait=trait))

    def test_every_drum_of_a_bar_has_as_many_hits_and_every_bar_of_a_figure_as_many_steps(self):
        for path in style_files():
            for trait, values in read(path)[arranger.TRAITS].items():
                for value in values if isinstance(values, list) else []:
                    with self.subTest(path=path, trait=trait, value=value[arranger.VALUE]):
                        self.assertLessEqual(len({len(hits) for hits in value.get(arranger.BAR, {}).values()}), 1)
                        self.assertLessEqual(len({steps_in(bar) for bar in value.get(arranger.FIGURE, [])}), 1)

    def test_every_template_of_every_style_makes_a_song_that_loads(self):
        for path in style_files():
            style = read(path)
            for template in style[arranger.TEMPLATES]:
                song = {**a_song(template=template), arranger.STYLE: style[arranger.NAME], arranger.FORM: list(style[arranger.SECTIONS])}
                with self.subTest(path=path, template=template):
                    made = Setlist.from_data(data=composer.composed(given=arranger.arranged(style=style, song=song), version=VERSION))
                    self.assertEqual(len(made.get_songs()[0].get_scenes()), len(style[arranger.SECTIONS]))


class TestPicks(unittest.TestCase):

    def setUp(self):
        self.style = read(os.path.join(STYLE_TEMPLATES, BLUES + YAML))

    def test_a_song_takes_its_templates_picks_and_changes_the_ones_it_names(self):
        plain = arranger.picked(style=self.style, song=a_song())
        changed = arranger.picked(style=self.style, song=a_song(picks={COMPING: STABS}))
        self.assertEqual(plain[COMPING], self.style[arranger.TEMPLATES][SHUFFLE][COMPING])
        self.assertEqual(changed[COMPING], STABS)
        self.assertEqual(changed[BASS], plain[BASS])

    def test_a_trait_nobody_picked_takes_its_commonest_value_that_fits(self):
        picks = arranger.picked(style=self.style, song=a_song())
        fills = self.style[arranger.TRAITS][arranger.FILLS]
        self.assertEqual(picks[arranger.FILLS], max(fills, key=arranger.share_of)[arranger.VALUE])

    def test_a_pick_that_needs_another_meter_is_refused(self):
        with self.assertRaises(ValueError):
            arranger.picked(style=self.style, song=a_song(picks={DRUMS_TRAIT: SLOW_DRUMS}))

    def test_an_unknown_template_and_an_unknown_value_are_refused(self):
        with self.assertRaises(ValueError):
            arranger.picked(style=self.style, song=a_song(template=NO_SUCH))
        with self.assertRaises(ValueError):
            arranger.picked(style=self.style, song=a_song(picks={BASS: NO_SUCH}))


class TestArranged(unittest.TestCase):

    def setUp(self):
        self.style = read(os.path.join(STYLE_TEMPLATES, BLUES + YAML))

    def test_the_form_becomes_scenes_and_a_section_played_again_is_numbered(self):
        given = arranger.arranged(style=self.style, song=a_song())
        self.assertEqual([scene[composer.SCENE] for scene in given[composer.FORM]], [INTRO, CHORUS, SECOND_CHORUS, SOLO, ENDING])
        self.assertEqual(given[composer.FORM][1][composer.BARS], self.style[arranger.SECTIONS][CHORUS][arranger.BARS])

    def test_the_bass_and_the_chords_are_written_over_chord_one_and_run_through_the_sections_progression(self):
        given = arranger.arranged(style=self.style, song=a_song())
        chain = given[composer.FORM][1][composer.PLAY][BASS][composer.CHAINS][0]
        progression = given[composer.CHAINS][chain][0][arranger.PROGRESSION]
        pattern = arranger.values_of(style=self.style, trait=arranger.CHORD_TRAIT)[self.style[arranger.TEMPLATES][SHUFFLE][arranger.CHORD_TRAIT]][arranger.PATTERN]
        self.assertEqual(given[composer.GENERATORS][arranger.PROGRESSIONS][progression][arranger.CHORDS], pattern)

    def test_a_sections_own_chords_replace_the_styles(self):
        given = arranger.arranged(style=self.style, song=a_song(sections={SOLO: {arranger.CHORDS: OWN_CHORDS}}))
        self.assertEqual(given[composer.GENERATORS][arranger.PROGRESSIONS][arranger.MSG_SECTION_PART.format(SOLO, arranger.CHORDS)][arranger.CHORDS], OWN_CHORDS)

    def test_a_strummed_guitar_brings_its_guitarify(self):
        given = arranger.arranged(style=self.style, song=a_song(picks={COMPING: STABS}))
        self.assertIn(COMPING, given[composer.GENERATORS][GUITARIFIES])
        chain = given[composer.FORM][1][composer.PLAY][COMPING][composer.CHAINS][0]
        self.assertIn({GUITARIFY: COMPING}, given[composer.CHAINS][chain])

    def test_a_drums_phrase_ends_in_the_fill(self):
        given = arranger.arranged(style=self.style, song=a_song())
        fill = arranger.values_of(style=self.style, trait=arranger.FILLS)[arranger.picked(style=self.style, song=a_song())[arranger.FILLS]][arranger.FILL]
        for drum, hits in fill.items():
            self.assertEqual(given[composer.PARTS][drum][notation.HITS][-len(hits):], hits)

    def test_the_chords_come_first_and_the_drums_last(self):
        given = arranger.arranged(style=self.style, song=a_song())
        tracks = list(given[composer.TRACKS])
        drums = given[composer.DRUM_TRACKS]
        self.assertEqual(tracks[0], COMPING)
        self.assertEqual(tracks[-len(drums):], drums)
        self.assertLess(tracks.index(LEAD), tracks.index(BASS))

    def test_a_key_low_in_the_octave_lifts_the_band_an_octave(self):
        low = {**a_song(), arranger.KEY: {arranger.ROOT: LOW_ROOT, arranger.TYPE: MAJOR}}
        self.assertEqual(arranger.arranged(style=self.style, song=low)[composer.PARTS][BASS][notation.OCTAVE],
                         arranger.arranged(style=self.style, song=a_song())[composer.PARTS][BASS][notation.OCTAVE] + 1)

    def test_a_song_in_twelve_eight_says_its_time_signature(self):
        self.assertEqual(arranger.arranged(style=self.style, song=a_song(template=SLOW_BLUES))[composer.TIME_SIGNATURE], TWELVE_EIGHT)
        self.assertNotIn(composer.TIME_SIGNATURE, arranger.arranged(style=self.style, song=a_song()))

    def test_a_tune_the_song_gives_is_kept_and_none_is_sketched_in_its_place(self):
        lines = [OWN_LINE, SILENT_LINE] * 3
        given = arranger.arranged(style=self.style, song=a_song(sections={CHORUS: {arranger.LINES_GIVEN: {LEAD: lines}}}))
        self.assertEqual(given[composer.PARTS][arranger.MSG_SECTION_PART.format(CHORUS, LEAD)][notation.LINES], lines)


class TestPlayers(unittest.TestCase):
    """The imaginary players: a file gives a complexity, people see a name, and each style says who the player is."""

    def setUp(self):
        self.style = read(os.path.join(STYLE_TEMPLATES, ROCK + YAML))

    def song(self, *, levels=None, picks=None, template=ROCK_KIND):
        song = {**a_song(template=template, picks=picks), arranger.STYLE: ROCK, arranger.FORM: ['intro', 'verse', 'chorus', 'ending']}
        if levels:
            song[arranger.PLAYERS] = levels
        return song

    def test_every_instrument_has_a_player_of_its_own_name_at_every_complexity(self):
        names = [players.player_name(instrument=instrument, complexity=complexity) for instrument in players.INSTRUMENTS
                 if instrument != players.SESSION for complexity in players.COMPLEXITIES]
        self.assertEqual(len(names), len(set(names)))
        for complexity in players.COMPLEXITIES:
            self.assertTrue(players.player_name(instrument=players.SESSION, complexity=complexity).endswith(players.FAMILIES[complexity]))

    def test_every_style_says_who_a_player_is_only_for_complexities_and_values_there_are(self):
        for path in style_files():
            style = read(path)
            for instrument, levels in style.get(arranger.PLAYERS, {}).items():
                self.assertIn(instrument, players.INSTRUMENTS)
                for complexity, player in levels.items():
                    with self.subTest(path=path, instrument=instrument, complexity=complexity):
                        self.assertIn(complexity, players.COMPLEXITIES)
                        for trait, value in player.get(arranger.PICKS, {}).items():
                            self.assertIn(value, arranger.values_of(style=style, trait=trait))

    def test_a_player_makes_the_players_picks_and_the_songs_own_pick_still_wins(self):
        plain = arranger.picked(style=self.style, song=self.song(levels={players.DRUMS: players.PLAIN}))
        wild = arranger.picked(style=self.style, song=self.song(levels={players.DRUMS: players.ADVANCED}))
        own = self.style[arranger.TEMPLATES][ROCK_KIND][KICK]
        kept = arranger.picked(style=self.style, song=self.song(levels={players.DRUMS: players.ADVANCED}, picks={KICK: own}))
        self.assertEqual(plain[KICK], self.style[arranger.PLAYERS][players.DRUMS][players.PLAIN][arranger.PICKS][KICK])
        self.assertNotEqual(plain[KICK], wild[KICK])
        self.assertEqual(kept[KICK], own)

    def test_a_players_pick_that_does_not_fit_the_meter_is_passed_over(self):
        picks = arranger.picked(style=self.style, song=self.song(levels={players.DRUMS: players.PLAIN}, template=BALLAD))
        self.assertEqual(picks[METER], SIX_EIGHT)
        self.assertEqual(picks[KICK], self.style[arranger.TEMPLATES][BALLAD][KICK])

    def test_every_track_has_a_rush_and_a_drag_that_do_nothing_until_a_player_moves_them(self):
        given = arranger.arranged(style=self.style, song=self.song())
        generators = given[composer.GENERATORS]
        for track in given[composer.TRACKS]:
            if track in generators[arranger.RUSHES]:
                self.assertEqual(generators[arranger.RUSHES][track], {arranger.GENERATOR_STEPS: [False]})
                self.assertEqual(given[composer.CHAINS][arranger.MSG_TIMING_CHAIN.format(track)], [{arranger.RUSH: track}, {arranger.DRAG: track}])
        self.assertIn(SNARE, generators[arranger.DRAGS])
        late = arranger.arranged(style=self.style, song=self.song(levels={players.DRUMS: players.TASTEFUL}))
        drag = self.style[arranger.PLAYERS][players.DRUMS][players.TASTEFUL][arranger.TIMING][SNARE][arranger.DRAG]
        self.assertEqual(late[composer.GENERATORS][arranger.DRAGS][SNARE], {arranger.GENERATOR_STEPS: [True], arranger.AMOUNT: drag})

    def test_a_players_drum_hits_are_uneven_by_no_more_than_the_player_says_and_the_same_for_a_seed(self):
        level = players.WILD
        by = self.style[arranger.PLAYERS][players.DRUMS][level][arranger.UNEVEN]
        one = arranger.arranged(style=self.style, song=self.song(levels={players.DRUMS: level}))
        again = arranger.arranged(style=self.style, song=self.song(levels={players.DRUMS: level}))
        loud = self.style[arranger.LOUDNESS][SNARE]
        heard = [velocity for velocity in one[composer.PARTS][SNARE][arranger.RAW][notation.VELOCITY] if velocity is not None]
        self.assertEqual(one[composer.PARTS][SNARE], again[composer.PARTS][SNARE])
        self.assertGreater(len(set(heard)), 1)
        self.assertTrue(all(abs(velocity - loud) <= by for velocity in heard))

    def test_a_guitarist_changes_the_guitarify_and_the_notes_name_the_band(self):
        level = players.TASTEFUL
        given = arranger.arranged(style=self.style, song=self.song(levels={players.RHYTHM: level, players.DRUMS: players.ADVANCED}))
        wanted = self.style[arranger.PLAYERS][players.RHYTHM][level][arranger.GUITARIFY_OF_PLAYER]
        for setting, value in wanted.items():
            self.assertEqual(given[composer.GENERATORS][arranger.GUITARIFIES][GUITAR][setting], value)
        self.assertIn(players.player_name(instrument=players.DRUMS, complexity=players.ADVANCED), given[composer.NOTES])
        self.assertIn(players.player_name(instrument=players.RHYTHM, complexity=level), given[composer.NOTES])


class TestSketchedTune(unittest.TestCase):

    def setUp(self):
        self.style = read(os.path.join(STYLE_TEMPLATES, BLUES + YAML))
        self.habits = self.style[arranger.MELODY]
        self.plan = self.style[arranger.SECTIONS][CHORUS][arranger.PLAN]
        self.chords = [arranger.chord_of(chord) for chord in arranger.values_of(style=self.style, trait=arranger.CHORD_TRAIT)['twelve bar'][arranger.PATTERN]]

    def sketch(self, *, seed=SEED, answers=False):
        return melody.sketched(habits=self.habits, plan=self.plan, chords=self.chords, scale_type=MAJOR, seed=seed, answers=answers)

    def test_every_line_fills_its_bars(self):
        for line in self.sketch() + self.sketch(answers=True):
            self.assertEqual(steps_in(line), self.habits[melody.GRID] * self.habits[melody.LINE_BARS])

    def test_the_same_seed_gives_the_same_tune_and_another_seed_another(self):
        self.assertEqual(self.sketch(), self.sketch())
        self.assertNotEqual(self.sketch(), self.sketch(seed=OTHER_SEED))

    def test_a_line_of_the_plan_returns_and_the_lead_rests_where_the_answer_plays(self):
        lead = self.sketch()
        answers = self.sketch(answers=True)
        self.assertEqual(lead[0], lead[2])
        for count, entry in enumerate(self.plan):
            silent = lead if entry.get(melody.ANSWER) else answers
            self.assertTrue(all(notation.REST in note for note in silent[count]))

    def test_every_note_is_one_of_the_styles_notes(self):
        allowed = {(note[notation.DEGREE], note.get(notation.ACCIDENTAL)) for note in self.habits[melody.LADDER]}
        for line in self.sketch() + self.sketch(answers=True):
            for note in line:
                if notation.REST not in note:
                    self.assertIn((note[notation.DEGREE], note.get(notation.ACCIDENTAL)), allowed)

    def test_a_long_note_lands_on_a_note_of_the_chord_when_one_is_near(self):
        ladder = melody.ladder_of(notes=self.habits[melody.LADDER], scale_type=MAJOR)
        home = melody.home_place(ladder=ladder, home=self.habits[melody.HOME])
        wanted = melody.chord_notes(chord={notation.DEGREE: 1}, scale_type=MAJOR)
        place = melody.nearest_chord_rung(ladder=ladder, place=home + 1, wanted=wanted)
        self.assertIn(ladder[place][0] % melody.NOTES_IN_OCTAVE, wanted)


if __name__ == '__main__':
    unittest.main()
