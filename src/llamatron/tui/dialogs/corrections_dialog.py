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
"""The Corrections dialog: lists the values of a set file that can't be used, each with the value that takes its place, and asks whether to open the set that way."""

from rich.text import Text

from llamatron.strings.messages import MSG_CORRECTIONS_INTRO, MSG_CORRECTIONS_MORE, MSG_CORRECTIONS_QUESTION, MSG_CORRECTIONS_TITLE, MSG_CORRECTIONS_WARNING
from llamatron.tui import keybindings
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.drawing import NOTHING, Style, fit, wrapped

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
        super().__init__(title=MSG_CORRECTIONS_TITLE, messages=[])
        self.file = file
        self.corrections = corrections

    def message_lines(self, width):
        shown = self.corrections[:MOST_SHOWN]
        more = len(self.corrections) - len(shown)
        lines = [*wrapped(text=MSG_CORRECTIONS_INTRO.format(file=self.file), width=width), Text(NOTHING)]
        lines += [Text(fit(text=correction, width=width).rstrip()) for correction in shown]
        if more:
            lines.append(Text(MSG_CORRECTIONS_MORE.format(count=more), style=Style.DIM))
        lines.append(Text(NOTHING))
        lines += wrapped(text=MSG_CORRECTIONS_WARNING, width=width)
        lines += wrapped(text=MSG_CORRECTIONS_QUESTION, width=width)
        return lines
