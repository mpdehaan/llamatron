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
"""The wizard's Hooks panel: the song's main hook and its second hook.

The main hook is the line of the chorus that returns, the few notes a listener goes away
with, and it owns the song's highest note. The panel says where it is sung, where it sits
among its section's lines, who plays it in the intro and what kind of figure it is. A second
hook is a short tag, written unlike the main hook and under its top, sung in another kind of
section. The picture under the fields is the main hook's notes.
"""

from rich.text import Text

from llamatron.macro_composer.wizard_choices import HOOK_PARTS
from llamatron.strings import labels, legends, messages
from llamatron.tui.drawing import INDENT, Style
from llamatron.tui.screens.shared.field import Button, ChoiceField, Field, Toggle
from llamatron.tui.screens.wizard.branch import Branch
from llamatron.tui.screens.wizard.hook_picture import picture_of


class HooksBranch(Branch):
    """The song's hooks: the main one, and a second where the song has one."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_HOOKS_BRANCH

    def summary(self):
        """Return the kind of section that sings the main hook, or None for a song that can have no hook."""
        choices = self.choices()
        place = choices.hook_line_place() if choices.is_ready() else None
        if place is None:
            return None
        return place[0] if choices.has_hook() else labels.MSG_WIZARD_NOBODY

    def fields(self):
        choices = self.choices()
        page = self.page()
        if not choices.is_ready() or not choices.can_have_hook():
            return []
        fields = [page.heading(label=labels.MSG_WIZARD_MAIN_HOOK_HEADING, is_set=self.main_is_set, starts_open=True), *self.main_fields()]
        if choices.has_hook() and (choices.second_hook_kinds() or choices.has_second_hook()):
            fields += [page.heading(label=labels.MSG_WIZARD_SECOND_HOOK_HEADING, is_set=choices.has_second_hook, starts_open=True), *self.second_fields()]
        return fields + self.buttons()

    def main_is_set(self):
        choices = self.choices()
        parts = choices.hook_parts() if choices.has_song_plan() else []
        return choices.get_intro_hook() is not None or choices.get_hook_placement() != choices.genre_hook_placement() or any(choices.hook_part_is_chosen(part) for part in parts)

    def main_fields(self):
        """Return the main hook's fields: where it is sung, where it sits among the lines, who plays it in the intro, and the parts
        of its kind; a genre whose songs have no hook unless asked has the switch that asks first."""
        choices = self.choices()
        page = self.page()
        switch = [] if choices.usual_hook() and choices.has_hook() else [Toggle(label=labels.MSG_WIZARD_MAIN_HOOK_LABEL, on=choices.has_hook(), set=page.choosing(choices.set_hook))]
        if not choices.has_hook():
            return switch
        sung_in = Field(label=labels.MSG_WIZARD_SUNG_IN_LABEL, value=lambda: choices.hook_line_place()[0])
        fields = [*switch, sung_in, *self.placement_fields(), *self.intro_hook_fields()]
        if choices.hook_is_own():
            # A hook written by hand in a song made before melodies were patterns is the person's, and Bksp gives the wizard's back.
            return [*fields, Field(label=labels.MSG_WIZARD_HOOK_NOTES_LABEL, value=lambda: labels.MSG_WIZARD_HOOK_NOTES_OWN, clear=lambda: page.choosing(lambda nothing: choices.set_hook_line(None))(None),
                                   clear_what=legends.MSG_TUNE_USUAL_WHAT)]
        return fields + ([self.part_field(part) for part in choices.hook_parts()] if choices.has_song_plan() else [])

    def placement_fields(self):
        """Return the field of where the hook sits among its chorus's lines, the genre's own place said to be so, where the chorus has such places."""
        choices = self.choices()
        offered = choices.hook_placements_offered()
        if not offered:
            return []
        usual = choices.genre_hook_placement()
        names = [labels.MSG_WIZARD_VALUE_FROM.format(value=value, origin=labels.MSG_WIZARD_USUAL_MELODY) if value == usual else value for value in offered]
        now = choices.get_hook_placement()
        return [ChoiceField(page=self.page(), label=labels.MSG_WIZARD_PLACEMENT_LABEL, choices=offered, names=names, current=now, shown=names[offered.index(now)],
                            set=self.page().choosing(choices.set_hook_placement))]

    def intro_hook_fields(self):
        """Return the field of who plays the hook in the intro, before anybody sings it, where somebody can."""
        choices = self.choices()
        players = choices.intro_hook_players()
        if not players:
            return []
        titles = {choices.role_title(role): role for role in players}
        now = choices.get_intro_hook()
        return [ChoiceField(page=self.page(), label=labels.MSG_WIZARD_INTRO_HOOK_LABEL, choices=[labels.MSG_WIZARD_NOBODY, *titles], current=labels.MSG_WIZARD_NOBODY if now is None else choices.role_title(now),
                            set=self.page().choosing(lambda title: choices.set_intro_hook(titles.get(title))))]

    def part_field(self, part):
        """Return the field of one part of the hook's kind, its contour, its rhythm or its odd detail: the wizard's pick, said to be so, or the one
        chosen from the list, whose first entry gives the part back to the wizard."""
        choices = self.choices()
        now = choices.hook_kind()[part]
        chosen = choices.hook_part_is_chosen(part)
        return ChoiceField(page=self.page(), label=labels.MSG_WIZARD_HOOK_PART_LABELS[part], choices=[labels.MSG_WIZARD_PICK, *HOOK_PARTS[part]], current=now if chosen else labels.MSG_WIZARD_PICK,
                           shown=now if chosen else labels.MSG_WIZARD_PICK_SHOWN.format(value=now),
                           set=self.page().choosing(lambda value: choices.set_hook_part(part=part, value=None if value == labels.MSG_WIZARD_PICK else value)))

    def second_fields(self):
        """Return the second hook's fields: its switch, and while the song has one, the kind of section that sings it."""
        choices = self.choices()
        page = self.page()
        kinds = choices.second_hook_kinds()
        switch = Toggle(label=labels.MSG_WIZARD_SECOND_HOOK_LABEL, on=choices.has_second_hook(), set=page.choosing(lambda on: choices.set_second_hook(kinds[0] if on else None)))
        if not choices.has_second_hook():
            return [switch]
        return [switch, ChoiceField(page=page, label=labels.MSG_WIZARD_SECOND_SUNG_IN_LABEL, choices=kinds, current=choices.get_second_hook_kind(), set=page.choosing(choices.set_second_hook))]

    def buttons(self):
        """Return the buttons that hear the hook under the cursor's heading and that have each hook made again."""
        choices = self.choices()
        page = self.page()
        if not choices.has_hook():
            return []
        buttons = [Button(label=labels.MSG_WIZARD_LISTEN_BUTTON, enter=lambda: page.listen_to(self.listens()), enter_what=legends.MSG_LISTEN_WHAT)]
        if not choices.hook_is_own():
            buttons.append(Button(label=labels.MSG_WIZARD_NEW_MAIN_HOOK_BUTTON, enter=lambda: page.choosing(lambda nothing: choices.new_hook())(None), enter_what=legends.MSG_WIZARD_NEW_HOOK_WHAT))
        if choices.has_second_hook():
            buttons.append(Button(label=labels.MSG_WIZARD_NEW_SECOND_HOOK_BUTTON, enter=lambda: page.choosing(lambda nothing: choices.new_second_hook())(None), enter_what=legends.MSG_WIZARD_NEW_HOOK_WHAT))
        return buttons

    def on_second_hook(self):
        """Return whether the cursor is on or under the second hook's heading."""
        return self.page().in_fields and self.page().heading_over_cursor() == labels.MSG_WIZARD_SECOND_HOOK_HEADING

    def listens(self):
        """Listen plays the melody's player alone in the first section that sings the hook under the cursor's heading: the main hook's, unless the cursor is on the second hook."""
        choices = self.choices()
        if not choices.is_ready() or not choices.can_have_hook() or not choices.has_hook() or choices.tune_player() is None:
            return None
        if self.on_second_hook() and choices.has_second_hook():
            return messages.MSG_WIZARD_LISTEN_SECOND_HOOK, choices.second_hook_scene(), choices.tune_player()
        return messages.MSG_WIZARD_LISTEN_HOOK, choices.hook_scene(), choices.tune_player()

    def notes(self, width):
        """Return the picture of the main hook, while the song has one."""
        choices = self.choices()
        hook = choices.hook_notes() if choices.is_ready() and choices.can_have_hook() else None
        if hook is None:
            return []
        made = (messages.MSG_WIZARD_HOOK_OWN if choices.hook_is_own() else messages.MSG_WIZARD_HOOK_MADE).format(player=choices.role_title(choices.tune_player()))
        return [*(Text(INDENT + line) for line in picture_of(hook=hook, width=width)), Text(INDENT + made, style=Style.DIM)]
