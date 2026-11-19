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
"""The Hocket editor: its name, the track whose notes it shares out, and its Restart."""

from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.composition.generator_settings import HocketSetting
from llamatron.strings import help as help_text, labels, legends, marks, messages
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.restart_field import restart_field
from llamatron.tui.screens.shared.field import ChoiceField, NameField
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.tui.text import sorted_names


class HocketEditor(ShowsNamedItem, FieldPage):

    KEYS = keybindings.HocketEditor
    HELP = help_text.HELP_HOCKET_EDITOR
    SECTION = Section.HOCKETS
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_HOCKET_LABEL)

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def hocket(self):
        return self.document().song().get_generator_settings(kind=GeneratorKind.HOCKET, name=self.item)

    def store_source(self, source):
        self.document().set_generator_setting(section=Section.HOCKETS, name=self.item, setting=HocketSetting.SOURCE, value=source)

    def sources(self):
        """Return the tracks the source can be: the current song's, sorted, and the Hocket's own source among them even when the song has no such track, so that it is seen and kept."""
        names = set(self.document().song().get_track_names())
        if self.hocket().get_source() is not None:
            names.add(self.hocket().get_source())
        return sorted_names(names)

    def fields(self):
        source = self.hocket().get_source()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            ChoiceField(
                page=self, label=labels.MSG_SOURCE_TRACK_LABEL, choices=[marks.MSG_NONE_SHOWN, *self.sources()], current=source or marks.MSG_NONE_SHOWN,
                set=lambda choice: self.store_source(None if choice == marks.MSG_NONE_SHOWN else choice), clear=lambda: self.store_source(None), clear_what=legends.MSG_NO_SOURCE_WHAT,
            ),
            restart_field(self),
        ]
