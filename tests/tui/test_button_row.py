# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests of the row of boxed buttons the dialogs draw."""

import unittest

from llamatron.strings import messages
from llamatron.tui.components import button_row as button_row_values
from llamatron.tui.components.button_row import button_row
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.drawing import Box, Style
from llamatron.tui.status_line import StatusLine

SAID = 'cannot delete a track while the song plays'
WIDTH = 60
BUTTONS = [('Q', 'Quit without saving'), ('S', 'Save, then Quit'), ('ESC', 'CANCEL')]


class TestButtonRow(unittest.TestCase):

    def test_each_button_is_boxed_the_selected_one_double_lined(self):
        lines = [line.plain for line in button_row(buttons=BUTTONS, selected=1)]
        self.assertEqual(len(lines), button_row_values.ROW_LINES)
        self.assertEqual(len({len(line) for line in lines}), 1)
        self.assertEqual(lines[0].count(Box.DOUBLE_TOP_LEFT), 1)
        self.assertEqual(lines[0].count(Box.TOP_LEFT), 2)
        self.assertLess(lines[1].index(BUTTONS[0][1]), lines[1].index(Box.DOUBLE_BAR))
        for key, label in BUTTONS:
            self.assertIn(label, lines[1])


class TestRefusalsAndDeletes(unittest.TestCase):
    """A refusal on the status line is amber and a question about deleting has a red title."""

    def test_the_status_line_knows_a_refusal_until_cleared(self):
        line = StatusLine()
        line.say(SAID)
        self.assertFalse(line.is_refusal())
        line.say(SAID, refusal=True)
        self.assertTrue(line.is_refusal())
        line.clear()
        self.assertFalse(line.is_refusal())

    def test_a_delete_question_has_a_red_title(self):
        self.assertEqual(ConfirmDialog(title=messages.MSG_DELETE_TITLE, messages=[SAID]).heading(WIDTH).style, Style.DELETE_TITLE)
        self.assertEqual(ConfirmDialog(title=SAID, messages=[SAID]).heading(WIDTH).style, Style.BOLD)
