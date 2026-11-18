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

"""The wizard's Tunes panel: the tune of each kind of section, a real pattern that the pattern editor opens.

A tune is written by the wizard's choices until a person edits its notes. From then on the pattern is
the person's own: every section of the kind plays it as written, and no choice of the wizard writes
over it until the person gives the wizard's notes back.
"""

from llamatron.strings import labels, legends, marks, messages
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.screens.shared.field import Field
from llamatron.tui.screens.wizard.branch import Branch


class TunesBranch(Branch):
    """A row for each kind of section that has a tune: ENTER edits the tune's notes in the pattern editor, and Bksp gives an edited tune back to the wizard."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_TUNES_BRANCH

    def kinds(self):
        choices = self.choices()
        return choices.tune_kinds() if choices.is_ready() else []

    def summary(self):
        """Return how many tunes the song has and how many of them were edited by hand, or None for a song with no tune."""
        kinds = self.kinds()
        if not kinds:
            return None
        edited = len([kind for kind in kinds if self.choices().tune_is_own(kind)])
        return marks.MSG_WIZARD_TUNES_SHOWN.format(count=len(kinds), edited=edited)

    def fields(self):
        return [self.tune_field(kind) for kind in self.kinds()]

    def tune_field(self, kind):
        choices = self.choices()
        page = self.page()
        own = choices.tune_is_own(kind)

        def shown():
            name = choices.tune_pattern_name(kind) or marks.MSG_WIZARD_NO_TUNE_SHOWN
            return marks.MSG_WIZARD_TUNE_EDITED.format(name=name) if own else name

        def give_back():
            question = messages.MSG_WIZARD_TUNE_GIVE_BACK_QUESTION.format(kind=kind)
            page.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_TUNE_GIVE_BACK_TITLE, messages=[question], starts_on_no=True),
                     then=page.choosing(lambda _: choices.set_tune_pattern(kind=kind, pattern=None)))
        return Field(label=labels.MSG_WIZARD_TUNE_LABEL.format(kind=kind), value=shown, enter=lambda: page.edit_tune(kind), enter_what=legends.MSG_WIZARD_EDIT_NOTES_WHAT,
                     clear=give_back if own else None, clear_what=legends.MSG_TUNE_USUAL_WHAT)

    def listens(self):
        """Listen plays the tune's player alone in the first section of the kind under the cursor."""
        choices = self.choices()
        kinds = self.kinds()
        if not kinds:
            return None
        label = self.page().label_under_cursor()
        kind = next((kind for kind in kinds if labels.MSG_WIZARD_TUNE_LABEL.format(kind=kind) == label), kinds[0])
        return messages.MSG_WIZARD_LISTEN_TUNE, choices.tune_place(kind), choices.tune_player()
