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
"""The intro's melody in the wizard: who says the hook before anybody sings it, and that player's notes.

An intro has a melody only while a player is chosen to say the hook in it. The panel holds that
choice, and while somebody is chosen, buttons to edit the player's intro notes in the pattern
editor and to hear the intro, the player alone and with the band. The panel comes after the
other melodies', since the intro is made from the hook and the hook from the chorus.
"""

from rich.text import Text

from llamatron.macro_composer.wizard_choices import INTRO
from llamatron.strings import labels, legends, messages
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.drawing import INDENT, Style
from llamatron.tui.screens.shared.field import Button, ChoiceField
from llamatron.tui.screens.wizard.branch import Branch

# What the panel is remembered by, apart from a section of the form called intro.
INTRO_MELODY_KEY = 'melody of the intro'


class IntroMelodyBranch(Branch):
    """The melody of the intro."""

    __slots__ = ()

    def key(self):
        return INTRO_MELODY_KEY

    def name(self):
        return INTRO.capitalize()

    def summary(self):
        """Return whether the intro's notes were edited by hand, or who says the hook in the intro."""
        choices = self.choices()
        if choices.intro_is_own():
            return labels.MSG_WIZARD_NOTES_EDITED
        player = choices.get_intro_hook()
        return choices.role_title(player) if player is not None else labels.MSG_WIZARD_NOBODY

    def fields(self):
        choices = self.choices()
        page = self.page()
        titles = {choices.role_title(role): role for role in choices.intro_hook_players()}
        now = choices.get_intro_hook()
        player = ChoiceField(page=page, label=labels.MSG_WIZARD_INTRO_HOOK_LABEL, choices=[labels.MSG_WIZARD_NOBODY, *titles], current=labels.MSG_WIZARD_NOBODY if now is None else choices.role_title(now),
                             set=page.choosing(lambda title: choices.set_intro_hook(titles.get(title))))
        return [player, *self.buttons()]

    def buttons(self):
        """Return the buttons that open the intro's notes in the pattern editor and that hear the intro, the player alone and with
        the band, while somebody says the hook in the intro."""
        choices = self.choices()
        page = self.page()
        if choices.get_intro_hook() is None:
            return []

        def give_back():
            question = messages.MSG_WIZARD_TUNE_GIVE_BACK_QUESTION.format(kind=INTRO)
            page.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_TUNE_GIVE_BACK_TITLE, messages=[question], starts_on_no=True), then=page.choosing(lambda _: choices.set_intro_pattern(None)))
        # On notes edited by hand, the delete key on the button gives the notes back to the wizard, after a question.
        return [Button(label=labels.MSG_WIZARD_EDIT_NOTES_BUTTON, enter=page.edit_intro, enter_what=legends.MSG_WIZARD_EDIT_NOTES_WHAT, clear=give_back if choices.intro_is_own() else None,
                       clear_what=legends.MSG_TUNE_USUAL_WHAT),
                Button(label=labels.MSG_WIZARD_LISTEN_BUTTON, enter=lambda: page.listen_to(self.listens()), enter_what=legends.MSG_LISTEN_WHAT),
                Button(label=labels.MSG_WIZARD_LISTEN_BAND_BUTTON, enter=lambda: page.listen_to(self.heard_with_band()), enter_what=legends.MSG_LISTEN_WHAT)]

    def listens_alone(self):
        return True

    def listens(self):
        """Listen plays the intro's player alone in the intro."""
        choices = self.choices()
        if choices.intro_melody_place() is None:
            return None
        return messages.MSG_WIZARD_MELODY_OF.format(kind=INTRO), choices.intro_melody_place(), choices.get_intro_hook()

    def heard_with_band(self):
        """Return what Listen With Band plays: everybody in the intro."""
        return messages.MSG_WIZARD_SECTION_WITH_BAND.format(kind=INTRO), self.choices().intro_melody_place(), None

    def notes(self, width):
        """Return the line under the buttons that says whose the intro's notes are: the wizard's, or edited by hand."""
        choices = self.choices()
        if not choices.is_ready() or choices.get_intro_hook() is None:
            return []
        return [Text(INDENT + (messages.MSG_WIZARD_NOTES_BY_HAND if choices.intro_is_own() else messages.MSG_WIZARD_HOOK_MADE), style=Style.DIM)]
