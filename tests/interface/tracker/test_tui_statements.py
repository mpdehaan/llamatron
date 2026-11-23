# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Conditional Execution on the pages: the table of statements about the draws on a chain's, a generator's, a scene's, a clip's and a track's page, and a scene's and a clip's sets and adds."""

from llamatron.engine.generators import timing as timing_plugin
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.choice_dialog import ChoiceDialog
from llamatron.interface.tracker.keys import Key
from llamatron.interface.tracker.screens.arrange.scene_page import ScenePage
from llamatron.interface.tracker.screens.generators.chain_editor import ChainEditor
from llamatron.interface.tracker.screens.generators.chain_statements_page import ChainStatementsPage
from llamatron.interface.tracker.screens.shared import statements
from llamatron.interface.tracker.screens.shared.field import Cells
from llamatron.model.objects import conditions
from llamatron.model.schema import limits
from llamatron.model.schema.file_format import DrawName, Operator, StatementPart
from llamatron.user_strings import errors, labels, marks
from tests.support import ui_testing
from tests.support.ui_testing import UITest

AD = DrawName.AD
BD = DrawName.BD
# What the tests type.
THREE = '3'
NOTHING_TO_DIVIDE_BY = '0'


def line_label(*, table, line):
    """Return the label of a line of a page's table, which is blank and as long as the line's place on the page."""
    return labels.MSG_STATEMENT_LINE_LABEL * (table * limits.MAX_STATEMENTS + line + 1)


class StatementsTest(UITest):
    """What every test of a table shares: reaching a line, and writing AD % 3 = 0 on it by pressing keys."""

    async def to_line(self, *, table=statements.FIRST_TABLE, line=0):
        await self.select_field(line_label(table=table, line=line))
        self.assertIsInstance(self.app.screen.field(), Cells)

    async def choose(self, option):
        """Open the picker of the cell under the cursor and choose an option."""
        await self.press(Key.ENTER)
        self.assertIsInstance(self.app.screen, ChoiceDialog)
        await self.pick(option)

    async def write_every_third(self, **where):
        """Write AD % 3 = 0 on a line: the draw, the operator, and the number typed."""
        await self.to_line(**where)
        await self.choose(AD)
        await self.press(Key.RIGHT)
        await self.choose(Operator.REMAINDER)
        await self.press(Key.RIGHT)
        await self.choose(labels.MSG_STATEMENT_NUMBER_CHOICE)
        self.app.screen.value = THREE
        await self.press(Key.ENTER)

    def every_third(self):
        return {
            StatementPart.REGISTER: AD, StatementPart.OPERATOR: Operator.REMAINDER, StatementPart.VALUE: int(THREE),
            StatementPart.COMPARISON: Operator.SAME, StatementPart.AGAINST: 0,
        }


class TestChainStatementsPage(StatementsTest):
    """A chain's statements, on the page the chain's editor opens."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.open_chain(ui_testing.NAMED)
        self.assertIsInstance(self.app.screen, ChainEditor)
        self.chain = self.app.screen.item
        await self.press(keybindings.ChainEditor.WHEN)
        self.assertIsInstance(self.app.screen, ChainStatementsPage)

    def table(self):
        return self.document.get_setlist().get_chain(self.chain).get_bypass_when()

    async def test_a_line_starts_ignored_and_a_draw_makes_it_a_statement(self):
        self.assertEqual(self.table(), [])
        self.assertIn(labels.MSG_STATEMENT_IGNORED, self.text())
        await self.to_line()
        await self.choose(BD)
        self.assertEqual(self.table(), [conditions.new_statement(BD)])

    async def test_a_sum_is_written_cell_by_cell(self):
        await self.write_every_third()
        self.assertEqual(self.table(), [self.every_third()])

    async def test_odd_takes_no_number_and_the_cursor_stops_on_the_operator(self):
        await self.write_every_third()
        await self.press(Key.LEFT)
        await self.choose(Operator.ODD)
        self.assertEqual(self.table(), [{StatementPart.REGISTER: AD, StatementPart.OPERATOR: Operator.ODD}])
        await self.press(Key.RIGHT, Key.RIGHT)
        self.assertEqual(len(self.app.screen.field().cells), 2)
        self.assertEqual(self.app.screen.cell, 1)

    async def test_a_draw_stands_for_a_number(self):
        await self.write_every_third()
        await self.choose(BD)
        self.assertEqual(self.table()[0][StatementPart.VALUE], BD)
        await self.press(Key.RIGHT, Key.RIGHT)
        await self.choose(DrawName.CD)
        self.assertEqual(self.table()[0][StatementPart.AGAINST], DrawName.CD)

    async def test_dividing_by_a_typed_zero_is_refused(self):
        await self.write_every_third()
        await self.choose(labels.MSG_STATEMENT_NUMBER_CHOICE)
        self.app.screen.value = NOTHING_TO_DIVIDE_BY
        await self.press(Key.ENTER)
        self.assertIn(errors.ERR_CANNOT_DIVIDE_BY_ZERO, self.text())
        self.assertEqual(self.table(), [self.every_third()])

    async def test_clearing_and_choosing_ignored_both_remove_the_statement(self):
        await self.write_every_third()
        await self.press(Key.BACKSPACE)
        self.assertEqual(self.table(), [])
        await self.write_every_third()
        await self.press(Key.LEFT, Key.LEFT)
        await self.choose(labels.MSG_STATEMENT_IGNORED)
        self.assertEqual(self.table(), [])

    async def test_a_line_past_the_last_statement_writes_the_next_one(self):
        await self.to_line(line=2)
        await self.choose(AD)
        await self.to_line(line=3)
        await self.choose(BD)
        self.assertEqual([statement[StatementPart.REGISTER] for statement in self.table()], [AD, BD])

    async def test_the_heading_never_says_set(self):
        await self.write_every_third()
        self.assertNotIn(marks.MSG_SECTION_SET, self.text())


class TestStatementsOnOtherPages(StatementsTest):
    """The same table on a generator's page and a scene's."""

    async def test_a_generator(self):
        await self.open_generator(section=timing_plugin.SECTION)
        await self.write_every_third()
        settings = self.document.get_setlist().get_generator_settings(kind=timing_plugin.NAME, name=ui_testing.LOOSE)
        self.assertEqual(settings.get_bypass_when(), [self.every_third()])

    async def test_a_scene(self):
        await self.press(keybindings.MainPage.ARRANGE, Key.ENTER)
        self.assertIsInstance(self.app.screen, ScenePage)
        await self.write_every_third()
        scene = self.document.song().get_scenes()[0]
        self.assertEqual(scene.get_bypass_when(), [self.every_third()])

