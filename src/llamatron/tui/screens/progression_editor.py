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
"""The Progression editor page: one progression's name, how long each chord lasts, and its chords, which Enter opens in the chord editor."""

from llamatron.composition.file_format import ONE_BAR_WRITTEN, GeneratorKind, Section
from llamatron.composition.generator_settings import ProgressionSetting
from llamatron.composition.progressions import roman_numeral
from llamatron.strings.help import HELP_PROGRESSION_EDITOR
from llamatron.strings.labels import Crumb, MSG_CHORDS_LABEL, MSG_EVERY_LABEL, MSG_PROGRESSION_LABEL
from llamatron.strings.legends import What
from llamatron.strings.marks import MSG_NUMERALS_SEPARATOR
from llamatron.strings.messages import MSG_RENAME_GENERATOR_PROMPT
from llamatron.tui import keybindings
from llamatron.tui.screens.restart_field import restart_field
from llamatron.tui.screens.chords_editor import ChordsEditor
from llamatron.tui.screens.field import Field, NameField
from llamatron.tui.screens.field_page import FieldPage
from llamatron.tui.screens.shows_named_item import ShowsNamedItem
from llamatron.tui.screens.time_field import time_field


def numerals_text(*, progression, scale):
    """Return a progression's chords as numerals in a scale, like I V vi IV, as its editor and its list page show them."""
    return MSG_NUMERALS_SEPARATOR.join(
        roman_numeral(scale=scale, degree=degree, accidental=accidental) for degree, accidental in zip(progression.get_chords(), progression.get_accidentals()))


def song_scale(song):
    """Return a song's scale, or None when it has none."""
    name = song.get_scale_name()
    return None if name is None else song.get_named_scale(name)


class ProgressionEditor(ShowsNamedItem, FieldPage):

    KEYS = keybindings.ProgressionEditor
    HELP = HELP_PROGRESSION_EDITOR
    SECTION = Section.PROGRESSIONS
    CRUMBS_BEFORE = (Crumb.GENERATORS,)
    RENAME_PROMPT = MSG_RENAME_GENERATOR_PROMPT.format(label=MSG_PROGRESSION_LABEL)

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def progression(self):
        return self.document().song().get_generator_settings(kind=GeneratorKind.PROGRESSION, name=self.item)

    def fields(self):
        progression = self.progression()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            time_field(
                page=self, label=MSG_EVERY_LABEL, written=progression.get_every(), first=ONE_BAR_WRITTEN,
                store=lambda value: self.document().set_generator_setting(section=Section.PROGRESSIONS, name=self.item, setting=ProgressionSetting.EVERY, value=value),
            ),
            Field(label=MSG_CHORDS_LABEL, value=lambda: numerals_text(progression=progression, scale=song_scale(self.document().song())), adjust=None,
                  enter=lambda: self.show_page(ChordsEditor(holder=self.holder, name=self.item)), enter_what=What.EDIT),
            restart_field(self),
        ]
