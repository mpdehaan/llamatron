# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The song's hook in the wizard, and its second hook.

The hook is the line of the chorus that returns, the few notes a listener goes away with, and
it owns the song's highest note. The hook is a part of its section's melody, never a thing
beside it: the panel says where it is sung and which bars of that section are the hook, and
its picture is the whole section's notes with the hook's bars in a
frame. The notes are edited as the section's, and how the hook is written, its behavior and its
gauges, is on that section's panel (section_melody_branch.py). A second hook is a short tag,
written unlike the hook and under its top, sung in another kind of section.
"""

import functools

from llamatron.interface.forms.nodes import Button, ChoiceField, Field, Toggle
from llamatron.interface.forms.remarks import dim_remark, remark
from llamatron.interface.tracker.dialogs.confirm_dialog import ConfirmDialog
from llamatron.interface.tracker.screens.wizard.branch import Branch
from llamatron.interface.tracker.screens.wizard.hook_picture import picture_of
from llamatron.user_strings import labels, legends, messages


def _indented(lines):
    """Return lines of a picture, each indented as the panel's notes are."""
    indented = []
    for line in lines:
        indented.append(remark(line))
    return indented


class HooksBranch(Branch):
    """The song's hooks: the main one, and a second where the song has one."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_HOOKS_BRANCH

    def summary(self):
        """Return the kind of section that sings the main hook, or None for a song that can have no hook."""
        choices = self.get_choices()
        if not choices.is_ready():
            return None
        hook = self._hook()
        place = hook.hook_line_place()
        if place is None:
            return None
        if not hook.has_hook():
            return labels.MSG_WIZARD_NOBODY
        kind, _ = place
        return kind

    def fields(self):
        if not self._offers_hooks():
            return []
        page = self.get_page()
        hook = self._hook()
        fields = [page.heading(label=labels.MSG_WIZARD_MAIN_HOOK_HEADING, is_set=self.main_is_set, starts_open=True)]
        fields += self.main_fields()
        offers_second = hook.second_hook_kinds() or hook.has_second_hook()
        if hook.has_hook() and offers_second:
            fields.append(page.heading(label=labels.MSG_WIZARD_SECOND_HOOK_HEADING, is_set=hook.has_second_hook, starts_open=True))
            fields += self.second_fields()
        return fields + self.buttons()

    def main_is_set(self):
        return False

    def main_fields(self):
        """Return the main hook's fields: where it is sung and which bars of that section are the hook; a genre whose songs have
        no hook unless asked has the switch that asks first."""
        page = self.get_page()
        hook = self._hook()
        fields = []
        if not (hook.usual_hook() and hook.has_hook()):
            fields.append(Toggle(label=labels.MSG_WIZARD_MAIN_HOOK_LABEL, on=hook.has_hook(), set=page.choosing(hook.set_hook)))
        if not hook.has_hook():
            return fields
        fields.append(Field(label=labels.MSG_WIZARD_SUNG_IN_LABEL, value=self._sung_in))
        fields += self.bars_fields()
        if hook.hook_is_own():
            # A hook written by hand in a song made before melodies were patterns is the person's, and Bksp gives the wizard's back.
            give_back = page.choosing(self._give_hook_back)
            fields.append(Field(label=labels.MSG_WIZARD_HOOK_NOTES_LABEL, value=lambda: labels.MSG_WIZARD_HOOK_NOTES_OWN,
                                clear=functools.partial(give_back, None), clear_what=legends.MSG_TUNE_USUAL_WHAT))
        return fields

    def _sung_in(self):
        """Return the kind of section the main hook is sung in."""
        kind, _ = self._hook().hook_line_place()
        return kind

    def _give_hook_back(self, nothing):
        """Give the wizard's hook back in place of one written by hand."""
        self._hook().set_hook_line(None)

    def bars_fields(self):
        """Return the field that says which bars of its section are the hook."""
        bars = self._hook().hook_bars()
        if bars is None:
            return []
        first, last = bars
        shown = labels.MSG_WIZARD_HOOK_BARS.format(first=first, last=last)
        return [Field(label=labels.MSG_WIZARD_HOOK_BARS_LABEL, value=lambda: shown)]

    def second_fields(self):
        """Return the second hook's fields: its switch, and while the song has one, the kind of section that sings it."""
        page = self.get_page()
        hook = self._hook()
        switch = Toggle(label=labels.MSG_WIZARD_SECOND_HOOK_LABEL, on=hook.has_second_hook(), set=page.choosing(self._switch_second_hook))
        if not hook.has_second_hook():
            return [switch]
        sung_in = ChoiceField(page=page, label=labels.MSG_WIZARD_SECOND_SUNG_IN_LABEL, choices=hook.second_hook_kinds(),
                              current=hook.get_second_hook_kind(), set=page.choosing(hook.set_second_hook))
        return [switch, sung_in]

    def _switch_second_hook(self, on):
        """Give the song a second hook, sung in the first kind of section offered, or take it away."""
        hook = self._hook()
        kind = None
        if on:
            kind = hook.second_hook_kinds()[0]
        hook.set_second_hook(kind)

    def buttons(self):
        """Return the buttons that hear the hook under the cursor's heading and that have each hook made again."""
        choices = self.get_choices()
        page = self.get_page()
        hook = self._hook()
        if not hook.has_hook():
            return []
        tunes = choices.get_tunes()
        kind = hook.hook_kind()
        buttons = []
        if tunes.tune_player_in(kind) is not None:
            # The hook's notes are its section's: the editor opens on the whole section.
            label = labels.MSG_WIZARD_EDIT_KIND_NOTES_BUTTON.format(kind=kind.capitalize())
            buttons.append(Button(label=label, enter=functools.partial(page.edit_tune, kind), enter_what=legends.MSG_WIZARD_EDIT_NOTES_WHAT))
        if not hook.hook_is_own() and not tunes.tune_is_own(kind):
            # Notes written by hand are never written over by another hook.
            buttons.append(Button(label=labels.MSG_WIZARD_REGENERATE_BUTTON, enter=self.regenerate, enter_what=legends.MSG_REGENERATE_WHAT))
        buttons.append(Button(label=labels.MSG_LISTEN_LABEL, key_name=legends.KeyName.L, enter=self._listen, enter_what=legends.MSG_LISTEN_WHAT))
        buttons.append(Button(label=labels.MSG_WIZARD_LISTEN_BAND_BUTTON, enter=self._listen_with_band, enter_what=legends.MSG_LISTEN_WHAT))
        if hook.has_second_hook():
            new_second = functools.partial(page.choosing(self._new_second_hook), None)
            buttons.append(Button(label=labels.MSG_WIZARD_NEW_SECOND_HOOK_BUTTON, enter=new_second, enter_what=legends.MSG_WIZARD_NEW_HOOK_WHAT))
        return buttons

    def _listen(self):
        self.get_page().listen_to(self.listens())

    def _listen_with_band(self):
        self.get_page().listen_to(self.heard_with_band())

    def _new_second_hook(self, nothing):
        self._hook().new_second_hook()

    def regenerate(self):
        """Have another hook written, with the behavior and the gauges as they stand, after asking."""
        page = self.get_page()
        name = messages.MSG_WIZARD_HOOK_NAME
        dialog = ConfirmDialog(title=messages.MSG_WIZARD_REGENERATE_TITLE.format(name=name), messages=[messages.MSG_WIZARD_REGENERATE_SAYS.format(name=name)],
                               starts_on_no=True)
        page.ask(dialog=dialog, then=self._write_new_hook)

    def _write_new_hook(self, _):
        """Have another hook written, and say so."""
        page = self.get_page()
        write = page.choosing(self._new_hook)
        write(None)
        page.say(messages.MSG_WIZARD_REGENERATED.format(name=messages.MSG_WIZARD_HOOK_NAME))

    def _new_hook(self, nothing):
        self._hook().new_hook()

    def on_second_hook(self):
        """Return whether the cursor is on or under the second hook's heading."""
        page = self.get_page()
        return page.in_fields and page.heading_over_cursor() == labels.MSG_WIZARD_SECOND_HOOK_HEADING

    def heard_with_band(self):
        """Return what Listen With Band plays: everybody in the first section that sings the hook under the cursor's heading."""
        heard = self.listens()
        if heard is None:
            return None
        _, place, _ = heard
        section = self.get_choices().section(place)
        return messages.MSG_WIZARD_SECTION_WITH_BAND.format(kind=section.kind()), place, None

    def listens_alone(self):
        return True

    def listens(self):
        """Listen plays the melody's player in the first section that sings the hook under the cursor's heading: the main hook's,
        unless the cursor is on the second hook. The player is whoever plays the melody in that kind of section, which the song
        may give to another player than the genre's; a section nobody plays the melody in has nothing to listen to."""
        if not self._offers_hooks():
            return None
        hook = self._hook()
        if not hook.has_hook():
            return None
        second = self.on_second_hook() and hook.has_second_hook()
        scene = hook.hook_scene()
        said = messages.MSG_WIZARD_LISTEN_HOOK
        if second:
            scene = hook.second_hook_scene()
            said = messages.MSG_WIZARD_LISTEN_SECOND_HOOK
        if scene is None:
            return None
        choices = self.get_choices()
        section = choices.section(scene)
        tunes = choices.get_tunes()
        player = tunes.tune_player_in(section.kind())
        if player is None:
            return None
        return said, scene, player

    def remarks(self, width):
        """Return the picture of the main hook, while the song has one: the notes of the whole section that says the hook, as
        they stand, with the hook's bars in a frame, under which bars those are and whose the notes are. Where the section's
        notes cannot be drawn so, the hook's own two bars are drawn alone."""
        if not self._offers_hooks():
            return []
        hook = self._hook()
        notes = hook.hook_notes()
        kind = hook.hook_kind()
        section = hook.hook_section_notes()
        bars = hook.hook_bars()
        if notes is None and section is None:
            return []
        made = dim_remark(self._whose_notes(kind))
        if notes is not None and (section is None or bars is None or hook.hook_is_own()):
            return [*_indented(picture_of(hook=notes, width=width)), made]
        first, last = bars
        said = dim_remark(messages.MSG_WIZARD_HOOK_IS_BARS.format(first=first, last=last, kind=kind))
        # The two lines that say which bars and whose notes come first, so that a tall picture never pushes them off the page.
        return [said, made, *_indented(picture_of(hook=section, width=width, lit=bars))]

    def _whose_notes(self, kind):
        """Return whose the hook's notes are: written by hand as the hook, written by hand in the section, or the wizard's."""
        tunes = self.get_choices().get_tunes()
        if self._hook().hook_is_own():
            return messages.MSG_WIZARD_HOOK_OWN
        if tunes.tune_is_own(kind):
            return messages.MSG_WIZARD_NOTES_BY_HAND
        return messages.MSG_WIZARD_HOOK_MADE

    def _hook(self):
        """Return the choices of the song's hooks."""
        choices = self.get_choices()
        return choices.get_hook()

    def _offers_hooks(self):
        """Return whether the song is ready and can have a hook."""
        choices = self.get_choices()
        return choices.is_ready() and self._hook().can_have_hook()
