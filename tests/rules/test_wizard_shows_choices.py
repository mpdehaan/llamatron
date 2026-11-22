# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Every choice the song wizard can keep is one a person can make on the wizard's page.

A choice built in `WizardChoices` and never put on the page is a feature nobody can reach, which happened to a player's own
gauges. So every method of `WizardChoices`, and of each part of the choices, that changes a choice must be called somewhere in
the wizard's screens, but for the few listed here with the reason each has no field.
"""

import inspect
import pathlib
import re
import unittest

from llamatron.interface.tracker.screens import wizard
from llamatron.interface.tracker.screens.shared import kit_fields, section_fade, section_own_fields
from llamatron.wizards.create_song.band_choices import BandChoices
from llamatron.wizards.create_song.form_choices import FormChoices
from llamatron.wizards.create_song.guitarist_choices import GuitaristChoices
from llamatron.wizards.create_song.hook_choices import HookChoices
from llamatron.wizards.create_song.interplay_choices import InterplayChoices
from llamatron.wizards.create_song.kit_choices import KitChoices
from llamatron.wizards.create_song.melody_choices import MelodyChoices
from llamatron.wizards.create_song.melody_ways import MelodyWays
from llamatron.wizards.create_song.player_choices import PlayerChoices
from llamatron.wizards.create_song.player_loudness import PlayerLoudness
from llamatron.wizards.create_song.player_sections import PlayerSections
from llamatron.wizards.create_song.riff_choices import RiffChoices
from llamatron.wizards.create_song.section_choices import SectionChoices
from llamatron.wizards.create_song.section_lines import SectionLines
from llamatron.wizards.create_song.section_melody import SectionMelody
from llamatron.wizards.create_song.solo_choices import SoloChoices
from llamatron.wizards.create_song.sound_choices import SoundChoices
from llamatron.wizards.create_song.tune_choices import TuneChoices
from llamatron.wizards.create_song.wizard_choices import WizardChoices

SETTER_START = 'set_'
# The choices and every part of them.
CHOICES_CLASSES = (WizardChoices, GuitaristChoices, MelodyChoices, MelodyWays, SectionMelody, SectionLines, PlayerLoudness, PlayerSections, BandChoices, InterplayChoices, FormChoices, PlayerChoices, KitChoices, HookChoices, RiffChoices, SoundChoices, SoloChoices, TuneChoices)
# What changes a choice without being named a setter.
OTHER_CHANGES = ('add_section', 'new_hook', 'new_second_hook')
# What changes one section of the form without being named a setter: its names are common words, so a call is looked for on a section.
SECTION_CHANGES = ('copy', 'move', 'remove')
# Changes with no field of their own: the sections a song kept are taken back one by one through the other setters, and
# the seed is never shown, since every run of the wizard draws a new one when it starts; and a song file's own picks, the song
# plan among them, are given by a file alone until the wizard's pages for them are built.
# A riff's notes are written in the pattern editor; its notes as one line are kept from songs made before that, and are given
# back from the page with the riff's pattern.
# How a written tune's lines breathe is the wizard's own; a song kept from before the Phrasing generator still holds what was chosen.
# The last four are the writing methods and their gauges, which the Melody panel's Character chooses among, and a kind of section's own
# player of the melody, which Section Players chooses through what each player plays there.
# Who says the hook in every part of an intro at once is kept from songs made before an intro had parts; the Intro panel sets each part's.
# One thing laid over the song's picks under a name is set by a part of the choices, whose own setters the pages call, and so
# are the sections a player plays in, which the player's Comes in and Lays out set.
NOT_ON_THE_PAGE = ('set_extra', 'set_plays_of', 'set_intro_hook', 'set_own_sections', 'set_seed', 'set_song_extras', 'set_phrasing', 'set_phrasing_way', 'set_style', 'set_style_gauge', 'set_setting', 'set_tune_played_by_in')
A_CALL = r'\.{name}\b'
# A section's change is called on a section asked for by its place, or on one held under the name section.
A_CALL_ON_A_SECTION = r'(\.section\([^)]*\)|\bsection|\._section\(\))\.{name}\b'
SOURCE_FILES = '*.py'
# The modules of shared fields the wizard's panels show: the drum kit's, a section's fade and what a section is given of its own.
SHARED_FIELDS = (kit_fields, section_fade, section_own_fields)


def changes():
    """Return the name of every public method of the wizard's choices, and of each part of them, that changes a choice."""
    names = sorted({name for choices_class in CHOICES_CLASSES for name, _ in inspect.getmembers(choices_class, inspect.isfunction)})
    return [name for name in names if name.startswith(SETTER_START) or name in OTHER_CHANGES]


def wizard_screens_source():
    """Return the source of every module of the wizard's screens, and of the shared fields they show, joined."""
    folder = pathlib.Path(wizard.__file__).parent
    sources = [path.read_text() for path in sorted(folder.glob(SOURCE_FILES))]
    for module in SHARED_FIELDS:
        sources.append(pathlib.Path(module.__file__).read_text())
    return ''.join(sources)


def section_changes():
    """Return the name of every public method of one section of the form that changes it."""
    names = sorted(name for name, _ in inspect.getmembers(SectionChoices, inspect.isfunction))
    return [name for name in names if name.startswith(SETTER_START) or name in SECTION_CHANGES]


class TestWizardShowsEveryChoice(unittest.TestCase):

    def test_every_change_of_the_wizards_choices_is_made_from_the_wizards_screens(self):
        source = wizard_screens_source()
        missing = [name for name in changes() if name not in NOT_ON_THE_PAGE and not re.search(A_CALL.format(name=name), source)]
        self.assertEqual(missing, [])

    def test_every_change_of_a_section_is_made_from_the_wizards_screens(self):
        source = wizard_screens_source()
        missing = [name for name in section_changes() if not re.search(A_CALL_ON_A_SECTION.format(name=name), source)]
        self.assertEqual(missing, [])
        self.assertTrue(set(SECTION_CHANGES) <= set(section_changes()))

    def test_the_exceptions_are_real_and_are_not_on_the_page(self):
        source = wizard_screens_source()
        for name in NOT_ON_THE_PAGE:
            self.assertIn(name, changes())
            self.assertIsNone(re.search(A_CALL.format(name=name), source))
