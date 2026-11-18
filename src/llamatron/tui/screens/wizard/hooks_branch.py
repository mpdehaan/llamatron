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
it owns the song's highest note. The hook is a part of its section's melody, never a thing
beside it: the panel says where it is sung and which bars of that section are the hook, and
its picture is the whole section's notes with the hook's bars in a
frame. The notes are edited as the section's, and how the hook is written, its behavior and its
gauges, is on that section's panel (section_melody_branch.py). A second hook is a short tag,
written unlike the hook and under its top, sung in another kind of section.
"""

from rich.text import Text

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
        return False

    def main_fields(self):
        """Return the main hook's fields: where it is sung and which bars of that section are the hook;
        a genre whose songs have no hook unless asked has the switch that asks first."""
        choices = self.choices()
        page = self.page()
        switch = [] if choices.usual_hook() and choices.has_hook() else [Toggle(label=labels.MSG_WIZARD_MAIN_HOOK_LABEL, on=choices.has_hook(), set=page.choosing(choices.set_hook))]
        if not choices.has_hook():
            return switch
        sung_in = Field(label=labels.MSG_WIZARD_SUNG_IN_LABEL, value=lambda: choices.hook_line_place()[0])
        fields = [*switch, sung_in, *self.bars_fields()]
        if choices.hook_is_own():
            # A hook written by hand in a song made before melodies were patterns is the person's, and Bksp gives the wizard's back.
            return [*fields, Field(label=labels.MSG_WIZARD_HOOK_NOTES_LABEL, value=lambda: labels.MSG_WIZARD_HOOK_NOTES_OWN, clear=lambda: page.choosing(lambda nothing: choices.set_hook_line(None))(None),
                                   clear_what=legends.MSG_TUNE_USUAL_WHAT)]
        return fields

    def bars_fields(self):
        """Return the field that says which bars of its section are the hook."""
        bars = self.choices().hook_bars()
        return [] if bars is None else [Field(label=labels.MSG_WIZARD_HOOK_BARS_LABEL, value=lambda: labels.MSG_WIZARD_HOOK_BARS.format(first=bars[0], last=bars[1]))]

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
        kind = choices.hook_kind()
        buttons = []
        if choices.tune_player_in(kind) is not None:
            # The hook's notes are its section's: the editor opens on the whole section.
            buttons.append(Button(label=labels.MSG_WIZARD_EDIT_KIND_NOTES_BUTTON.format(kind=kind.capitalize()), enter=lambda: page.edit_tune(kind), enter_what=legends.MSG_WIZARD_EDIT_NOTES_WHAT))
        if not choices.hook_is_own() and not choices.tune_is_own(kind):
            # Notes written by hand are never written over by another hook.
            buttons.append(Button(label=labels.MSG_WIZARD_REGENERATE_BUTTON, enter=self.regenerate, enter_what=legends.MSG_REGENERATE_WHAT))
        buttons.append(Button(label=labels.MSG_WIZARD_LISTEN_BUTTON, enter=lambda: page.listen_to(self.listens()), enter_what=legends.MSG_LISTEN_WHAT))
        buttons.append(Button(label=labels.MSG_WIZARD_LISTEN_BAND_BUTTON, enter=lambda: page.listen_to(self.heard_with_band()), enter_what=legends.MSG_LISTEN_WHAT))
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

    def heard_with_band(self):
        """Return what Listen With Band plays: everybody in the first section that sings the hook under the cursor's heading."""
        heard = self.listens()
        return None if heard is None else (messages.MSG_WIZARD_SECTION_WITH_BAND.format(kind=self.choices().section_kind(heard[1])), heard[1], None)

    def listens_alone(self):
        return True

    def listens(self):
        """Listen plays the melody's player in the first section that sings the hook under the cursor's heading: the main hook's,
        unless the cursor is on the second hook. The player is whoever plays the melody in that kind of section, which the song
        may give to another player than the genre's; a section nobody plays the melody in has nothing to listen to."""
        choices = self.choices()
        if not choices.is_ready() or not choices.can_have_hook() or not choices.has_hook():
            return None
        second = self.on_second_hook() and choices.has_second_hook()
        scene = choices.second_hook_scene() if second else choices.hook_scene()
        player = None if scene is None else choices.tune_player_in(choices.section_kind(scene))
        if player is None:
            return None
        return (messages.MSG_WIZARD_LISTEN_SECOND_HOOK if second else messages.MSG_WIZARD_LISTEN_HOOK), scene, player

    def notes(self, width):
        """Return the picture of the main hook, while the song has one: the notes of the whole section that says the hook, as they
        stand, with the hook's bars in a frame, under which bars those are and whose the notes are. Where the section's notes cannot
        be drawn so, the hook's own two bars are drawn alone."""
        choices = self.choices()
        if not choices.is_ready() or not choices.can_have_hook():
            return []
        hook = choices.hook_notes()
        kind = choices.hook_kind()
        section = choices.hook_section_notes()
        bars = choices.hook_bars()
        if hook is None and section is None:
            return []
        if choices.hook_is_own():
            made = messages.MSG_WIZARD_HOOK_OWN
        else:
            made = messages.MSG_WIZARD_NOTES_BY_HAND if choices.tune_is_own(kind) else messages.MSG_WIZARD_HOOK_MADE
        if hook is not None and (section is None or bars is None or choices.hook_is_own()):
            return [*(Text(INDENT + line) for line in picture_of(hook=hook, width=width)), Text(INDENT + made, style=Style.DIM)]
        said = messages.MSG_WIZARD_HOOK_IS_BARS.format(first=bars[0], last=bars[1], kind=kind)
        # The two lines that say which bars and whose notes come first, so that a tall picture never pushes them off the page.
        return [Text(INDENT + said, style=Style.DIM), Text(INDENT + made, style=Style.DIM), *(Text(INDENT + line) for line in picture_of(hook=section, width=width, lit=bars))]
