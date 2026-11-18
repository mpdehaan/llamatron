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
"""Every choice the song wizard can keep is one a person can make on the wizard's page.

A choice built in `WizardChoices` and never put on the page is a feature nobody can reach, which happened to a player's own
gauges. So every method of `WizardChoices` that changes a choice must be called somewhere in the wizard's screens, but for the
few listed here with the reason each has no field.
"""

import inspect
import pathlib
import re
import unittest

from llamatron.macro_composer.wizard_choices import WizardChoices
from llamatron.tui.screens import wizard

SETTER_START = 'set_'
# What changes a choice without being named a setter.
OTHER_CHANGES = ('add_section', 'copy_section', 'remove_section', 'move_section', 'new_hook')
# Changes with no field of their own: the sections a song kept are taken back one by one through the other setters, and
# the seed is never shown, since every run of the wizard draws a new one when it starts; and a song file's own picks, the song
# plan among them, are given by a file alone until the wizard's pages for them are built.
# A riff's notes are written in the pattern editor; its notes as one line are kept from songs made before that, and are given
# back from the page with the riff's pattern.
NOT_ON_THE_PAGE = ('set_own_sections', 'set_seed', 'set_song_extras', 'set_riff_line')
A_CALL = r'\.{name}\b'
SOURCE_FILES = '*.py'


def changes():
    """Return the name of every public method of the wizard's choices that changes a choice."""
    names = [name for name, _ in inspect.getmembers(WizardChoices, inspect.isfunction)]
    return [name for name in names if name.startswith(SETTER_START) or name in OTHER_CHANGES]


def wizard_screens_source():
    """Return the source of every module of the wizard's screens, joined."""
    folder = pathlib.Path(wizard.__file__).parent
    return ''.join(path.read_text() for path in sorted(folder.glob(SOURCE_FILES)))


class TestWizardShowsEveryChoice(unittest.TestCase):

    def test_every_change_of_the_wizards_choices_is_made_from_the_wizards_screens(self):
        source = wizard_screens_source()
        missing = [name for name in changes() if name not in NOT_ON_THE_PAGE and not re.search(A_CALL.format(name=name), source)]
        self.assertEqual(missing, [])

    def test_the_exceptions_are_real_and_are_not_on_the_page(self):
        source = wizard_screens_source()
        for name in NOT_ON_THE_PAGE:
            self.assertIn(name, changes())
            self.assertIsNone(re.search(A_CALL.format(name=name), source))
