# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Corrections dialog: lists the values of a set file that can't be used, each with the value that takes its place, and asks whether to open the set that way."""

from llamatron.interface.forms.dialogs import blank, said, said_in_passing, said_on_one_line
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.dialogs.confirm_dialog import ConfirmDialog
from llamatron.user_strings import messages

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

    def paragraphs(self):
        """Return what opening the set changes: a sentence, each correction on a line of its own, the rest counted in passing,
        and what opening means."""
        shown = self.corrections[:MOST_SHOWN]
        more = len(self.corrections) - len(shown)
        paragraphs = [said(messages.MSG_CORRECTIONS_INTRO.format(file=self.file)), blank(), *[said_on_one_line(correction) for correction in shown]]
        if more:
            paragraphs.append(said_in_passing(messages.MSG_CORRECTIONS_MORE.format(count=more)))
        return [*paragraphs, blank(), said(messages.MSG_CORRECTIONS_WARNING)]
