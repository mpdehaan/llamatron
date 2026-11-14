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
"""The tracker's Euclidean mask: the Euclids page and editor, the track editor's + Euclid section, and the picker of named rhythms that H opens on Hits."""

from ui_testing import CLAVE, LEAD, UITest
from llamatron.composition.euclid import NAMED_RHYTHMS
from llamatron.composition.file_format import Section, EuclidPart, GeneratorKind, NamedRhythm
from llamatron.strings.labels import MSG_EUCLID_FIELD_LABELS, MSG_EUCLID_LABEL, MSG_EUCLID_PART_LABELS
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.keys import Key
from llamatron.tui.screens.euclid_editor import EuclidEditor
from llamatron.tui.screens.euclid_fields import drawn_rhythm
from llamatron.tui.screens.track_editor import TrackEditor
from llamatron.tui import keybindings

NEW_ONE = 'bell'
TRESILLO_HITS, TRESILLO_STEPS = NAMED_RHYTHMS[NamedRhythm.TRESILLO]


class TestEuclidAdded(UITest):

    async def test_a_new_one_is_the_tresillo(self):
        name = await self.add_generator(Section.EUCLIDS)
        mask = self.document.song().get_generator_settings(kind=GeneratorKind.EUCLID, name=name).get_euclid()
        self.assertEqual((mask.hits, mask.steps), (TRESILLO_HITS, TRESILLO_STEPS))


class TestEuclidEditor(UITest):

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_generator(section=Section.EUCLIDS)
        self.assertIsInstance(self.app.screen, EuclidEditor)

    def mask(self):
        return self.document.song().get_generator_settings(kind=GeneratorKind.EUCLID, name=CLAVE).get_euclid()

    async def test_rotate_steps_and_the_drawing_follows(self):
        await self.select_field(MSG_EUCLID_PART_LABELS[EuclidPart.ROTATE])
        await self.press(keybindings.EuclidEditor.MORE)
        self.assertEqual(self.mask().rotate, 1)
        self.assertIn(drawn_rhythm(hits=TRESILLO_HITS, steps=TRESILLO_STEPS, rotate=1), self.text())

    async def test_h_is_offered_on_hits_alone(self):
        await self.select_field(MSG_EUCLID_PART_LABELS[EuclidPart.STEPS])
        await self.press(keybindings.EuclidEditor.PICK_RHYTHM)
        self.assertIsInstance(self.app.screen, EuclidEditor)
        await self.select_field(MSG_EUCLID_PART_LABELS[EuclidPart.HITS])
        await self.press(keybindings.EuclidEditor.PICK_RHYTHM)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        self.assertEqual(len(self.app.screen.options), len(NAMED_RHYTHMS))


class TestTrackEuclidSection(UITest):

    async def test_the_track_takes_a_named_rhythm(self):
        self.app.screen.show_page(TrackEditor(holder=self.app.screen.holder, name=LEAD))
        await self.pilot.pause()
        await self.select_field(MSG_EUCLID_LABEL)
        await self.press(Key.ENTER)
        await self.select_field(MSG_EUCLID_FIELD_LABELS[EuclidPart.HITS])
        await self.press(keybindings.TrackEditor.PICK_RHYTHM, Key.DOWN, Key.ENTER)
        hits, steps = list(NAMED_RHYTHMS.values())[1]
        mask = self.document.song().get_track(LEAD).get_euclid()
        self.assertEqual((mask.hits, mask.steps), (hits, steps))
