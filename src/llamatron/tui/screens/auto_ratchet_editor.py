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

"""The Auto ratchet editor page."""

from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.composition.generator_settings import AutoRatchetSetting
from llamatron.tui.dialogs.prompt_dialog import PromptDialog
from llamatron.tui.drawing import SPACE
from llamatron.strings.help import HELP_AUTO_RATCHET_EDITOR
from llamatron.tui.screens.restart_field import restart_field
from llamatron.tui.screens.field import Field, NameField
from llamatron.tui.screens.field_page import FieldPage
from llamatron.tui.screens.shared import counts_text
from llamatron.strings.errors import ERR_BAD_COUNTS
from llamatron.strings.labels import Crumb, MSG_AUTO_RATCHET_LABEL, MSG_COUNTS_LABEL
from llamatron.strings.messages import MSG_RENAME_GENERATOR_PROMPT
from llamatron.tui.screens.shows_named_item import ShowsNamedItem
from llamatron.tui import keybindings


COUNT_SEPARATOR = ','


class AutoRatchetEditor(ShowsNamedItem, FieldPage):

    KEYS = keybindings.AutoRatchetEditor
    HELP = HELP_AUTO_RATCHET_EDITOR
    SECTION = Section.AUTO_RATCHETS
    CRUMBS_BEFORE = (Crumb.GENERATORS,)
    RENAME_PROMPT = MSG_RENAME_GENERATOR_PROMPT.format(label=MSG_AUTO_RATCHET_LABEL)

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def counts(self):
        return self.document().song().get_generator_settings(kind=GeneratorKind.AUTO_RATCHET, name=self.item).get_counts()

    def ask_counts(self):
        def answered(text):
            parts = text.replace(COUNT_SEPARATOR, SPACE).split()
            if not parts or not all(part.isdigit() and int(part) >= 1 for part in parts):
                self.refuse(ERR_BAD_COUNTS)
                return
            self.document().set_generator_setting(section=Section.AUTO_RATCHETS, name=self.item, setting=AutoRatchetSetting.COUNTS, value=[int(part) for part in parts])
        self.ask(dialog=PromptDialog(title=MSG_COUNTS_LABEL, value=counts_text(self.counts())), then=answered)

    def fields(self):
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            Field(label=MSG_COUNTS_LABEL, value=lambda: counts_text(self.counts()), adjust=None, enter=self.ask_counts),
            restart_field(self),
        ]
