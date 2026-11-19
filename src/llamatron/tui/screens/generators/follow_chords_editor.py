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

"""The Follow Chords editor: its name and the track whose chords it follows."""

from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.composition.generator_settings import FollowChordsSetting
from llamatron.strings import help as help_text, labels, legends, marks, messages
from llamatron.tui import keybindings
from llamatron.tui.screens.shared.field import ChoiceField, NameField
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.tui.text import sorted_names


class FollowChordsEditor(ShowsNamedItem, FieldPage):

    KEYS = keybindings.FollowChordsEditor
    HELP = help_text.HELP_FOLLOW_CHORDS_EDITOR
    SECTION = Section.FOLLOW_CHORDS
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_FOLLOW_CHORDS_LABEL)

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def follow_chords(self):
        return self.document().song().get_generator_settings(kind=GeneratorKind.FOLLOW_CHORDS, name=self.item)

    def store_chords_from(self, track):
        self.document().change(self.document().generator(section=Section.FOLLOW_CHORDS, name=self.item).set_setting, name=FollowChordsSetting.CHORDS_FROM, value=track)

    def tracks(self):
        """Return the tracks that can be followed: the current song's, sorted, and the one followed among them even when the song has no such track, so that it is seen and kept."""
        names = set(self.document().song().get_track_names())
        if self.follow_chords().get_chords_from() is not None:
            names.add(self.follow_chords().get_chords_from())
        return sorted_names(names)

    def fields(self):
        followed = self.follow_chords().get_chords_from()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            ChoiceField(
                page=self, label=labels.MSG_CHORDS_FROM_LABEL, choices=[marks.MSG_NONE_SHOWN, *self.tracks()], current=followed or marks.MSG_NONE_SHOWN,
                set=lambda choice: self.store_chords_from(None if choice == marks.MSG_NONE_SHOWN else choice), clear=lambda: self.store_chords_from(None), clear_what=legends.MSG_NO_TRACK_WHAT,
            ),
        ]
