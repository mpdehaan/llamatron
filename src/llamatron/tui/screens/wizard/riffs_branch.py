# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The wizard's Riffs panel: the song's riffs, listed under the player each was written for.

A riff is a figure of a bar or two that a player repeats in place of the accompaniment. The panel
is a list as the tracker's lists are: a heading for each player a riff can be written for, the
player's riffs under it and a row that adds one. A riff exists here whether or not anybody plays
it yet: who knows it is chosen on Riff Assign, and where it is played on Section Players.
"""

import functools

from llamatron.composition.checks import listed
from llamatron.strings import labels, legends, marks, messages
from llamatron.tui import drawing
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.dialogs.new_riff_dialog import NewRiffDialog
from llamatron.tui.screens.shared.field import Field
from llamatron.tui.screens.wizard.branch import Branch


class RiffsBranch(Branch):
    """A heading for each player a riff can be written for, with the player's riffs and a row that adds one."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_RIFFS_BRANCH

    def summary(self):
        """Return how many riffs the song has, or None where no player of the band can play one."""
        choices = self.get_choices()
        if not choices.is_ready() or not choices.get_riffs().riff_instruments():
            return None
        return str(len(choices.get_riffs().riff_names()))

    def fields(self):
        choices = self.get_choices()
        if not choices.is_ready():
            return []
        fields = []
        for role in choices.get_riffs().riff_instruments():
            riffs = choices.get_riffs().riffs_for(role)
            fields.append(self.player_heading(role=role, count=len(riffs), columns=labels.MSG_WIZARD_RIFF_COLUMNS))
            fields += [self.riff_field(riff) for riff in riffs]
            fields.append(Field(label=marks.MSG_ADD_ROW_MARK, value=lambda: drawing.NOTHING, enter=functools.partial(self.add_riff, role), enter_what=legends.What.ADD))
        return fields

    def player_heading(self, *, role, count, columns):
        """Return a player's heading: how many it holds while closed, and the columns' names while open."""
        page = self.get_page()
        title = self.get_choices().player(role).title()
        return page.heading(label=title, is_set=lambda: bool(count), said=lambda: columns if title in page.app.open_field_sections and count else marks.MSG_WIZARD_COUNT_SHOWN.format(count=count))

    def riff_field(self, riff):
        """Return a riff's row: its bars and the kinds of section it is used in, marked when its notes were edited; ENTER opens its
        notes in the pattern editor, and Bksp deletes it after asking."""
        choices = self.get_choices()

        def shown():
            row = marks.MSG_WIZARD_RIFF_ROW.format(bars=choices.get_riffs().riff_bar_count(riff), used=listed(choices.get_riffs().riff_kinds_used(riff)))
            return marks.MSG_WIZARD_TUNE_EDITED.format(name=row.rstrip()) if choices.get_riffs().riff_is_edited(riff) else row
        return Field(label=riff, value=shown, enter=lambda: self.get_page().edit_riff(riff), enter_what=legends.MSG_WIZARD_EDIT_NOTES_WHAT, clear=lambda: self.delete(riff), clear_what=legends.What.DELETE)

    def role_under_cursor(self):
        """Return the player whose heading the cursor is on or under, or None."""
        choices = self.get_choices()
        heading = self.get_page().heading_over_cursor()
        return next((role for role in choices.get_riffs().riff_instruments() if choices.player(role).title() == heading), None)

    def riff_under_cursor(self):
        """Return the riff whose row the cursor is on, or None."""
        label = self.get_page().label_under_cursor()
        return label if label in self.get_choices().get_riffs().riff_names() else None

    def field_keys(self):
        """Return the list's keys where the cursor is: A adds a riff for the player of the heading, and on a riff N renames, C copies and R regenerates."""
        page = self.get_page()
        keys = [page.bind(page.KEYS.ADD, action=lambda: self.add_riff(self.role_under_cursor()))] if self.role_under_cursor() is not None else []
        riff = self.riff_under_cursor()
        if riff is not None:
            keys += [page.bind(page.KEYS.RENAME_RIFF, action=lambda: self.rename(riff)), page.bind(page.KEYS.COPY, action=lambda: self.copy_riff(riff)),
                     page.bind(page.KEYS.REGENERATE, action=lambda: self.regenerate(riff))]
        return keys

    def add_riff(self, role):
        """Ask how a new riff for a player is drawn, write it, and put the cursor on it."""
        choices = self.get_choices()
        page = self.get_page()
        title = choices.player(role).title()

        def written(settings):
            if settings is None:
                return
            try:
                riff = page.choosing(lambda asked: choices.get_riffs().add_riff(role=role, settings=asked))(settings)
            except ValueError as problem:
                page.refuse(str(problem))
                return
            self.show(role=role, riff=riff)
            page.say(messages.MSG_WIZARD_RIFF_WRITTEN.format(riff=riff, player=title))
        page.ask(dialog=NewRiffDialog(player=title), then=written)

    def show(self, *, role, riff):
        """Open a player's heading and put the cursor on a riff under it."""
        page = self.get_page()
        page.app.open_field_sections.add(self.get_choices().player(role).title())
        page.go_to_field(riff)

    def rename(self, riff):
        choices = self.get_choices()
        page = self.get_page()

        def renamed(name):
            page.choosing(lambda new: choices.get_riffs().rename_riff(riff=riff, name=new))(name)
            page.go_to_field(name)
        page.ask_name(title=messages.MSG_WIZARD_RIFF_RENAME_PROMPT, value=riff, taken=choices.get_riffs().riff_names(), then=renamed)

    def copy_riff(self, riff):
        """Ask which player the copy is for, the riff's own first, and copy the riff: a copy for another player keeps the notes in that player's octave."""
        choices = self.get_choices()
        page = self.get_page()
        players = choices.get_riffs().riff_instruments()

        def copied(place):
            role = players[place]
            made = page.choosing(lambda player: choices.get_riffs().copy_riff(riff=riff, role=player))(role)
            self.show(role=role, riff=made)
            page.say(messages.MSG_WIZARD_RIFF_COPIED.format(riff=riff, copy=made, player=choices.player(role).title()))
        page.ask(dialog=ChoiceDialog(title=labels.MSG_WIZARD_COPY_RIFF_TITLE.format(riff=riff), options=[choices.player(role).title() for role in players], current=players.index(choices.get_riffs().riff_written_for(riff))), then=copied)

    def regenerate(self, riff):
        """Have other notes written for a riff, with nothing kept of the old ones, after asking."""
        choices = self.get_choices()
        page = self.get_page()

        def written(_):
            page.choosing(choices.get_riffs().regenerate_riff)(riff)
            page.say(messages.MSG_WIZARD_REGENERATED.format(name=riff))
        page.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_REGENERATE_TITLE.format(name=riff), messages=[messages.MSG_WIZARD_REGENERATE_SAYS.format(name=riff)], starts_on_no=True), then=written)

    def delete(self, riff):
        """Ask before deleting a riff, saying where it is used; whoever played it then plays the accompaniment again."""
        choices = self.get_choices()
        page = self.get_page()
        used = choices.get_riffs().riff_kinds_used(riff)

        def deleted(_):
            page.choosing(choices.get_riffs().delete_riff)(riff)
            page.say(messages.MSG_WIZARD_RIFF_DELETED.format(riff=riff))
        said = [messages.MSG_WIZARD_RIFF_USED_IN.format(kinds=listed(used))] if used else []
        page.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_DELETE_RIFF_TITLE.format(riff=riff), messages=said, starts_on_no=True, deletes=True), then=deleted)

    def listens(self):
        """Listen plays the riff under the cursor alone, in the sound of the player it was written for, played anywhere or not."""
        riff = self.riff_under_cursor()
        if riff is None:
            return None
        try:
            setlist, name, index, track, _ = self.get_choices().get_riffs().riff_heard(riff)
        except ValueError:
            return None
        return riff, index, track, (setlist, name)
