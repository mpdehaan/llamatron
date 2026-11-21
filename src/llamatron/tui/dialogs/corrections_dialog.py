# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Corrections dialog: lists the values of a set file that can't be used, each with the value that takes its place, and asks whether to open the set that way."""

from rich.text import Text

from llamatron.strings import messages
from llamatron.tui import drawing, keybindings
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.drawing import fit, Style, wrapped

# The most corrections listed, so that the dialog fits an 80 by 24 console with its sentences and its buttons. The rest are counted on one line.
MOST_SHOWN = 5


class CorrectionsDialog(ConfirmDialog):
    """Answers True to open the set with its values corrected. Anything else that closes it opens nothing.

    Each correction is one line, cut short with an ellipsis where it's wider than the dialog,
    and only the first few are listed, with a count of the rest, so that the dialog always fits.
    The sentences under them say what opening means: the composition may sound different, and
    the file stays as it is until the set is saved.
    """

    KEYS = keybindings.CorrectionsDialog

    def __init__(self, *, file, corrections):
        """file is the set file's name, and corrections the lines that describe each one."""
        super().__init__(title=messages.MSG_CORRECTIONS_TITLE, messages=[])
        self.file = file
        self.corrections = corrections

    def message_lines(self, width):
        shown = self.corrections[:MOST_SHOWN]
        more = len(self.corrections) - len(shown)
        lines = [*wrapped(text=messages.MSG_CORRECTIONS_INTRO.format(file=self.file), width=width), Text(drawing.NOTHING)]
        lines += [Text(fit(text=correction, width=width).rstrip()) for correction in shown]
        if more:
            lines.append(Text(messages.MSG_CORRECTIONS_MORE.format(count=more), style=Style.DIM))
        lines.append(Text(drawing.NOTHING))
        lines += wrapped(text=messages.MSG_CORRECTIONS_WARNING, width=width)
        lines += wrapped(text=messages.MSG_CORRECTIONS_QUESTION, width=width)
        return lines
