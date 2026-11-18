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

"""The wizard's Tunes panel: the tune of each kind of section, a real pattern that the pattern editor opens.

A tune is written by the wizard's choices until a person edits its notes. From then on the pattern is
the person's own: every section of the kind plays it as written, and no choice of the wizard writes
over it until the person gives the wizard's notes back.
"""

from llamatron.macro_composer.arranger import NOBODY
from llamatron.macro_composer.wizard_choices import FIRST_TUNE_TAKE
from llamatron.strings import labels, legends, marks, messages
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.drawing import NOTHING
from llamatron.tui.screens.shared.field import ChoiceField, Field
from llamatron.tui.screens.wizard.branch import Branch

# The choice that leaves a kind of section's tune to the song's player, which no player is named.
FROM_SONG = ''

# The Add Riff picker's first choices, a riff the wizard writes and a riff with no notes yet, which the riffs already in the song follow.
NEW_RIFF_PLACE = 0
BLANK_RIFF_PLACE = 1
RIFFS_TO_WRITE = (labels.MSG_WIZARD_NEW_RIFF, labels.MSG_WIZARD_BLANK_RIFF)


class TunesBranch(Branch):
    """Who plays the song's tune, then a section for each kind of section that has a tune: the tune, whose notes ENTER edits in the pattern
    editor and Bksp gives back to the wizard, and who plays it there."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_TUNES_BRANCH

    def kinds(self):
        """Return the kinds of section that have a tune."""
        choices = self.choices()
        return choices.tune_kinds() if choices.is_ready() else []

    def headed_kinds(self):
        """Return the kinds of section the panel has a heading for: every kind of the form, since any may take a riff."""
        return self.choices().riff_kinds_offered()

    def summary(self):
        """Return how many tunes the song has and how many of them were edited by hand, or None for a song with no tune."""
        kinds = self.kinds()
        if not kinds:
            return None
        edited = len([kind for kind in kinds if self.choices().tune_is_own(kind)])
        return marks.MSG_WIZARD_TUNES_SHOWN.format(count=len(kinds), edited=edited)

    def fields(self):
        """Who plays the song's tune, then for each kind of section its tune, unless nobody plays it there, and who plays it."""
        choices = self.choices()
        kinds = self.kinds()
        fields = [self.song_player_field()] if kinds else []
        fields += self.hook_line_fields()
        for kind in self.headed_kinds():
            fields.append(self.page().heading(label=self.heading_of(kind), is_set=lambda kind=kind: self.kind_is_set(kind)))
            if kind in kinds:
                if choices.tune_player_in(kind) is not None:
                    fields.append(self.tune_field(kind))
                fields.append(self.player_field(kind))
            fields += [self.riff_field(kind=kind, riff=riff) for riff in choices.riffs_in(kind)]
            if choices.riff_players_free(kind):
                fields.append(Field(label=labels.MSG_WIZARD_ADD_RIFF_LABEL, value=lambda: NOTHING, enter=lambda kind=kind: self.add_riff(kind), enter_what=legends.What.ADD))
        return fields

    def hook_line_fields(self):
        """Return the field that says which line of the tune is the hook line, the line a listener goes away humming, or none: shown
        where the song can have a hook."""
        choices = self.choices()
        place = choices.hook_line_place()
        if place is None:
            return []
        line = labels.MSG_WIZARD_HOOK_LINE_SHOWN.format(kind=place[0], line=place[1])
        return [ChoiceField(page=self.page(), label=labels.MSG_WIZARD_HOOK_LINE_LABEL, choices=[marks.MSG_NONE_SHOWN, line], current=line if choices.has_hook() else marks.MSG_NONE_SHOWN,
                            set=self.page().choosing(lambda shown: choices.set_hook(shown == line)))]

    def riff_field(self, *, kind, riff):
        """Return the row of a riff in a kind of section: its name, then who plays it; Bksp takes the riff out of the kind after asking."""
        choices = self.choices()
        page = self.page()

        def shown():
            players = self.players_shown(choices.riff_players_of(riff))
            if choices.added_riff_is_own(riff):
                return marks.MSG_WIZARD_TUNE_EDITED.format(name=players)
            take = choices.riff_take_of(riff)
            return marks.MSG_WIZARD_TUNE_TAKE_SHOWN.format(name=players, take=take + 1) if take else players

        def remove():
            question = messages.MSG_WIZARD_RIFF_REMOVE_QUESTION.format(riff=riff, kind=kind)
            page.ask(dialog=ConfirmDialog(title=messages.MSG_DELETE_TITLE, messages=[question]), then=page.choosing(lambda _: choices.remove_riff(kind=kind, riff=riff)))
        return Field(label=riff, value=shown, enter=lambda: page.edit_riff(riff), enter_what=legends.MSG_WIZARD_EDIT_NOTES_WHAT, clear=remove, clear_what=legends.What.DELETE)

    def players_shown(self, players):
        """Return players as a riff's row and the picker name them: each by the name on the Band panel, joined."""
        return labels.MSG_WIZARD_RIFF_PLAYERS_JOIN.join(self.choices().role_title(role) for role in players)

    def add_riff(self, kind):
        """Add a riff to a kind of section in two steps: a new riff, a blank riff to write by hand or one already in the song, then,
        for a new or a blank riff, who plays it, one of the players free in the kind or two of them together. A blank riff opens in
        the pattern editor at once."""
        choices = self.choices()
        page = self.page()
        free = choices.riff_players_free(kind)
        again = [riff for riff in choices.added_riffs() if kind not in choices.riff_kinds_of(riff) and set(choices.riff_players_of(riff)) <= set(free)]
        groups = [[role] for role in free] + [[one, other] for place, one in enumerate(free) for other in free[place + 1:]]

        def added(riff):
            page.say(messages.MSG_WIZARD_RIFF_ADDED.format(riff=riff, kind=kind))

        def with_players(*, place, blank):
            def add(players):
                riff = choices.add_riff(kind=kind, players=players)
                if blank:
                    choices.set_riff_pattern(riff=riff, pattern=choices.blank_riff_pattern(riff))
                return riff
            try:
                riff = page.choosing(add)(groups[place])
            except ValueError as problem:
                page.refuse(str(problem))
                return
            added(riff)
            if blank:
                # The picker is still closing: the editor opens once the wizard's page is on top again.
                page.call_later(page.edit_riff, riff)

        def chosen(place):
            if place in (NEW_RIFF_PLACE, BLANK_RIFF_PLACE):
                page.ask(dialog=ChoiceDialog(title=labels.MSG_WIZARD_RIFF_PLAYERS_TITLE, options=[self.players_shown(group) for group in groups]),
                         then=lambda players: with_players(place=players, blank=place == BLANK_RIFF_PLACE))
                return
            try:
                added(page.choosing(lambda riff: choices.add_riff(kind=kind, riff=riff))(again[place - len(RIFFS_TO_WRITE)]))
            except ValueError as problem:
                page.refuse(str(problem))
        page.ask(dialog=ChoiceDialog(title=labels.MSG_WIZARD_ADD_RIFF_TITLE.format(kind=kind), options=[*RIFFS_TO_WRITE, *again]), then=chosen)

    def heading_of(self, kind):
        """Return the heading of a kind of section's part of the panel."""
        return labels.MSG_WIZARD_KIND_HEADING.format(kind=kind)

    def kind_is_set(self, kind):
        """Return whether anything of a kind of section was chosen here: its notes edited, another take, or a player of its own."""
        choices = self.choices()
        return bool(choices.tune_is_own(kind) or choices.tune_take(kind) != FIRST_TUNE_TAKE or choices.tune_played_by_in(kind) is not None or choices.riffs_in(kind))

    def song_player_field(self):
        choices = self.choices()
        offered = choices.tune_players_offered()
        return ChoiceField(page=self.page(), label=labels.MSG_WIZARD_TUNE_LABEL, choices=offered, names=[choices.role_title(role) for role in offered],
                           current=choices.tune_played_by(), shown=choices.role_title(choices.tune_played_by()), set=self.page().choosing(choices.set_tune_played_by))

    def player_field(self, kind):
        """Return the field of who plays a kind of section's tune: the song's player until another is chosen, a player of the band, or nobody."""
        choices = self.choices()
        offered = choices.tune_players_offered()
        own = choices.tune_played_by_in(kind)
        from_song = marks.MSG_WIZARD_FROM_SONG_SHOWN.format(value=choices.role_title(choices.tune_played_by()))
        names = {FROM_SONG: from_song, NOBODY: labels.MSG_WIZARD_NOBODY, **{role: choices.role_title(role) for role in offered}}
        return ChoiceField(page=self.page(), label=labels.MSG_WIZARD_PLAYED_BY_LABEL, choices=list(names), names=list(names.values()),
                           current=own or FROM_SONG, shown=names[own or FROM_SONG],
                           set=self.page().choosing(lambda role: choices.set_tune_played_by_in(kind=kind, role=None if role == FROM_SONG else role)))

    def tune_field(self, kind):
        choices = self.choices()
        page = self.page()
        own = choices.tune_is_own(kind)

        def shown():
            name = choices.tune_pattern_name(kind) or marks.MSG_WIZARD_NO_TUNE_SHOWN
            if own:
                return marks.MSG_WIZARD_TUNE_EDITED.format(name=name)
            take = choices.tune_take(kind)
            return marks.MSG_WIZARD_TUNE_TAKE_SHOWN.format(name=name, take=take + 1) if take else name

        def give_back():
            question = messages.MSG_WIZARD_TUNE_GIVE_BACK_QUESTION.format(kind=kind)
            page.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_TUNE_GIVE_BACK_TITLE, messages=[question], starts_on_no=True),
                     then=page.choosing(lambda _: choices.set_tune_pattern(kind=kind, pattern=None)))
        return Field(label=labels.MSG_WIZARD_TUNE_ROW_LABEL, value=shown, enter=lambda: page.edit_tune(kind), enter_what=legends.MSG_WIZARD_EDIT_NOTES_WHAT,
                     clear=give_back if own else None, clear_what=legends.MSG_TUNE_USUAL_WHAT)

    def kind_under_cursor(self):
        """Return the kind of section whose tune the cursor is on, the first where the cursor is in the tree, or None for a song with no tune."""
        kinds = self.headed_kinds()
        heading = self.page().heading_over_cursor()
        return next((kind for kind in kinds if self.heading_of(kind) == heading), kinds[0] if kinds else None)

    def riff_under_cursor(self):
        """Return the riff whose row the cursor is on, or None."""
        kind = self.kind_under_cursor()
        label = self.page().label_under_cursor()
        return label if kind is not None and label in self.choices().riffs_in(kind) else None

    def on_a_tune(self):
        """Return whether the cursor is on a tune's row, where the tune's keys work."""
        return self.page().label_under_cursor() == labels.MSG_WIZARD_TUNE_ROW_LABEL

    def takes(self):
        """A new take writes another tune for the kind under the cursor alone, asking first where the tune was edited by hand."""
        kind = self.kind_under_cursor()
        choices = self.choices()
        page = self.page()
        riff = self.riff_under_cursor()
        if riff is not None:
            def take_riff(_=None):
                page.choosing(choices.new_riff_take_of)(riff)
                page.say(messages.MSG_WIZARD_RIFF_TAKEN.format(take=choices.riff_take_of(riff) + 1, riff=riff))

            def ask_or_take_riff():
                if not choices.added_riff_is_own(riff):
                    take_riff()
                    return
                question = messages.MSG_WIZARD_RIFF_TAKE_QUESTION.format(riff=riff)
                page.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_TUNE_TAKE_TITLE, messages=[question], starts_on_no=True), then=take_riff)
            return ask_or_take_riff
        if kind is None or not self.on_a_tune():
            return None

        def take(_=None):
            page.choosing(lambda kind: choices.new_tune_take(kind))(kind)
            page.say(messages.MSG_WIZARD_TUNE_TAKEN.format(take=choices.tune_take(kind) + 1, kind=kind))

        def ask_or_take():
            if not choices.tune_is_own(kind):
                take()
                return
            question = messages.MSG_WIZARD_TUNE_TAKE_QUESTION.format(kind=kind)
            page.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_TUNE_TAKE_TITLE, messages=[question], starts_on_no=True), then=take)
        return ask_or_take

    def listens(self):
        """Listen plays the tune's player alone in the first section of the kind under the cursor."""
        kind = self.kind_under_cursor()
        riff = self.riff_under_cursor()
        if riff is not None:
            return messages.MSG_WIZARD_LISTEN_ADDED_RIFF.format(riff=riff), self.choices().riff_place(kind), self.choices().riff_players_of(riff)[0]
        if kind is None or kind not in self.kinds() or self.choices().tune_player_in(kind) is None:
            return None
        return messages.MSG_WIZARD_LISTEN_TUNE, self.choices().tune_place(kind), self.choices().tune_player_in(kind)
