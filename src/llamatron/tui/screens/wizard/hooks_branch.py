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
"""The song's hook in the wizard, and its second hook.

The hook is the line of the chorus that returns, the few notes a listener goes away with, and
it owns the song's highest note. The panel says where it is sung, who plays it in the intro,
and how it is written: a behavior, the kind of figure it is, and a few gauges, each the
genre's until moved. A second hook is a short tag, written unlike the hook and under its top,
sung in another kind of section. The picture under the fields is the hook's notes.
"""

from rich.text import Text

from llamatron.macro_composer import hook_writing
from llamatron.strings import labels, legends, messages
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
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
        moved = any(choices.writing_gauge_is_moved(part=hook_writing.HOOK_WRITING, name=name) for name in choices.hook_gauges())
        return choices.get_intro_hook() is not None or moved or (choices.writes_hook() and choices.get_hook_behavior() != choices.genre_hook_behavior())

    def main_fields(self):
        """Return the main hook's fields: where it is sung, who plays it in the intro, and how it is written, its behavior and its
        gauges; a genre whose songs have no hook unless asked has the switch that asks first."""
        choices = self.choices()
        page = self.page()
        switch = [] if choices.usual_hook() and choices.has_hook() else [Toggle(label=labels.MSG_WIZARD_MAIN_HOOK_LABEL, on=choices.has_hook(), set=page.choosing(choices.set_hook))]
        if not choices.has_hook():
            return switch
        sung_in = Field(label=labels.MSG_WIZARD_SUNG_IN_LABEL, value=lambda: choices.hook_line_place()[0])
        fields = [*switch, sung_in, *self.intro_hook_fields()]
        if choices.hook_is_own():
            # A hook written by hand in a song made before melodies were patterns is the person's, and Bksp gives the wizard's back.
            return [*fields, Field(label=labels.MSG_WIZARD_HOOK_NOTES_LABEL, value=lambda: labels.MSG_WIZARD_HOOK_NOTES_OWN, clear=lambda: page.choosing(lambda nothing: choices.set_hook_line(None))(None),
                                   clear_what=legends.MSG_TUNE_USUAL_WHAT)]
        return fields + self.writing_fields()

    def writing_fields(self):
        """Return the fields of how the hook is written: its behavior, the genre's said to be so, and the gauges that change a hook of that behavior."""
        choices = self.choices()
        page = self.page()
        if not choices.writes_hook():
            return []
        usual = choices.genre_hook_behavior()
        values = list(hook_writing.BEHAVIORS)
        names = [labels.MSG_WIZARD_VALUE_FROM.format(value=value, origin=labels.MSG_WIZARD_USUAL_MELODY) if value == usual else value for value in values]
        now = choices.get_hook_behavior()
        behavior = ChoiceField(page=page, label=labels.MSG_WIZARD_BEHAVIOR_LABEL, choices=values, names=names, current=now, shown=names[values.index(now)], set=page.choosing(choices.set_hook_behavior))
        return [behavior, *(self.gauge_field(name) for name in choices.hook_gauges())]

    def gauge_field(self, name):
        choices = self.choices()
        return self.writing_gauge_field(label=labels.MSG_WIZARD_HOOK_GAUGE_LABELS[name], position=choices.get_hook_gauge(name), moved=choices.writing_gauge_is_moved(part=hook_writing.HOOK_WRITING, name=name),
                                        set_position=lambda position: choices.set_hook_gauge(name=name, position=position))

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
            buttons.append(Button(label=labels.MSG_WIZARD_REGENERATE_BUTTON, enter=self.regenerate, enter_what=legends.MSG_REGENERATE_WHAT))
        if choices.has_second_hook():
            buttons.append(Button(label=labels.MSG_WIZARD_NEW_SECOND_HOOK_BUTTON, enter=lambda: page.choosing(lambda nothing: choices.new_second_hook())(None), enter_what=legends.MSG_WIZARD_NEW_HOOK_WHAT))
        return buttons

    def regenerate(self):
        """Have another hook written, with the behavior and the gauges as they stand, after asking."""
        choices = self.choices()
        page = self.page()
        name = messages.MSG_WIZARD_HOOK_NAME

        def written(_):
            page.choosing(lambda nothing: choices.new_hook())(None)
            page.say(messages.MSG_WIZARD_REGENERATED.format(name=name))
        page.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_REGENERATE_TITLE.format(name=name), messages=[messages.MSG_WIZARD_REGENERATE_SAYS.format(name=name)], starts_on_no=True), then=written)

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
