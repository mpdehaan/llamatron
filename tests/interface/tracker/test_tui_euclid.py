# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The tracker's Euclidean mask: the Euclids page and editor, the track editor's + Euclid section, and the picker of named rhythms that H opens on Hits."""

from llamatron.engine.generators import euclid as euclid_plugin
from llamatron.engine.generators.euclid import strings as euclid_strings
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.arrange.track_editor import TrackEditor
from llamatron.interface.tracker.screens.generators.euclid_editor import EuclidEditor
from llamatron.interface.tracker.screens.generators.euclid_fields import drawn_rhythm
from llamatron.model.objects import euclid
from llamatron.model.schema.file_format import EuclidPart, NamedRhythm
from llamatron.user_strings import labels
from tests.support import ui_testing
from tests.support.ui_testing import UITest

NEW_ONE = 'bell'
TRESILLO_HITS, TRESILLO_STEPS = euclid.NAMED_RHYTHMS[NamedRhythm.TRESILLO]


class TestEuclidAdded(UITest):

    async def test_a_new_one_is_the_tresillo(self):
        name = await self.add_generator(euclid_plugin.SECTION)
        mask = self.document.get_setlist().get_generator_settings(kind=euclid_plugin.NAME, name=name).get_euclid()
        self.assertEqual((mask.hits, mask.steps), (TRESILLO_HITS, TRESILLO_STEPS))


class TestEuclidEditor(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=euclid_plugin.SECTION)
        self.assertIsInstance(self.app.screen, EuclidEditor)

    def mask(self):
        return self.document.get_setlist().get_generator_settings(kind=euclid_plugin.NAME, name=ui_testing.CLAVE).get_euclid()

    async def test_rotate_steps_and_the_drawing_follows(self):
        await self.select_field(labels.MSG_EUCLID_PART_LABELS[EuclidPart.ROTATE])
        await self.press(keybindings.EuclidEditor.MORE)
        self.assertEqual(self.mask().rotate, 1)
        self.assertIn(drawn_rhythm(hits=TRESILLO_HITS, steps=TRESILLO_STEPS, rotate=1), self.text())

    async def test_h_is_offered_on_hits_alone(self):
        await self.select_field(labels.MSG_EUCLID_PART_LABELS[EuclidPart.STEPS])
        await self.press(keybindings.EuclidEditor.PICK_RHYTHM)
        self.assertIsInstance(self.app.screen, EuclidEditor)
        await self.select_field(labels.MSG_EUCLID_PART_LABELS[EuclidPart.HITS])
        await self.press(keybindings.EuclidEditor.PICK_RHYTHM)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(len(self.app.screen.options), len(euclid.NAMED_RHYTHMS))


class TestTrackEuclidSection(UITest):

    async def test_the_track_takes_a_named_rhythm(self):
        self.app.screen.show_page(TrackEditor(holder=self.app.screen.holder, name=ui_testing.LEAD))
        await self.pilot.pause()
        await self.select_field(euclid_strings.MSG_LABEL)
        await self.press(Key.ENTER)
        await self.select_field(labels.MSG_EUCLID_FIELD_LABELS[EuclidPart.HITS])
        await self.press(keybindings.TrackEditor.PICK_RHYTHM, Key.DOWN, Key.ENTER)
        hits, steps = list(euclid.NAMED_RHYTHMS.values())[1]
        mask = self.document.song().get_track(ui_testing.LEAD).get_euclid()
        self.assertEqual((mask.hits, mask.steps), (hits, steps))
