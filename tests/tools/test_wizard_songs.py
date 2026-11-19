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

"""internal_tools/wizard_songs.py prints a line for the song every choice of the song wizard makes, each song as a short hash."""

import contextlib
import importlib.util
import io
import itertools
import pathlib
import unittest

from tests.macro_composer.test_wizard_effect import every_choice, fresh

SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / 'internal_tools' / 'wizard_songs.py'
MODULE_NAME = 'wizard_songs_report'
A_GENRE = 'rock'
A_SUBGENRE = 'arena rock'
NOT_A_GENRE = 'polka'
A_FEW = 3
A_FAILURE = 1
ANOTHER_TEMPO = 1


def tool():
    spec = importlib.util.spec_from_file_location(MODULE_NAME, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def a_few_choices():
    return list(itertools.islice(every_choice(fresh(genre=A_GENRE, subgenre=A_SUBGENRE)), A_FEW))


class TestWizardSongs(unittest.TestCase):

    def test_the_same_choices_make_the_same_hash_and_other_choices_another(self):
        module = tool()
        usual = fresh(genre=A_GENRE, subgenre=A_SUBGENRE)
        other = fresh(genre=A_GENRE, subgenre=A_SUBGENRE)
        other.set_tempo(other.get_tempo() + ANOTHER_TEMPO)
        self.assertEqual(module.digest_of(usual), module.digest_of(fresh(genre=A_GENRE, subgenre=A_SUBGENRE)))
        self.assertNotEqual(module.digest_of(usual), module.digest_of(other))
        self.assertEqual(len(module.digest_of(usual)), module.HASH_LENGTH)

    def test_a_song_that_cannot_be_made_says_so_in_its_line(self):
        module = tool()
        self.assertTrue(module.digest_of(module.WizardChoices()).startswith(module.MSG_FAILED.split()[0]))

    def test_each_choice_is_a_line_naming_the_genre_the_subgenre_and_the_choice(self):
        module = tool()
        choices = a_few_choices()
        lines = module.lines_of_subgenre(genre=A_GENRE, subgenre=A_SUBGENRE, choices=choices)
        self.assertEqual(len(lines), sum(len(firsts) for _, _, _, firsts in choices))
        for line in lines:
            self.assertTrue(line.startswith(A_GENRE))
            self.assertIn(A_SUBGENRE, line)
        self.assertIn(str(choices[0][0]), lines[0])
        self.assertEqual(lines, module.lines_of_subgenre(genre=A_GENRE, subgenre=A_SUBGENRE, choices=a_few_choices()))

    def test_a_genre_that_is_not_one_is_refused(self):
        refused = io.StringIO()
        with contextlib.redirect_stderr(refused):
            self.assertEqual(tool().main(arguments=[NOT_A_GENRE]), A_FAILURE)
        self.assertIn(NOT_A_GENRE, refused.getvalue())
