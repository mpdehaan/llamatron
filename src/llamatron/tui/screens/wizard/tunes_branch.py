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
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.screens.shared.field import ChoiceField, Field
from llamatron.tui.screens.wizard.branch import Branch

# The choice that leaves a kind of section's tune to the song's player, which no player is named.
FROM_SONG = ''


class TunesBranch(Branch):
    """Who plays the song's tune, then a section for each kind of section that has a tune: the tune, whose notes ENTER edits in the pattern
    editor and Bksp gives back to the wizard, and who plays it there."""

    __slots__ = ()

    def name(self):
        return labels.MSG_WIZARD_TUNES_BRANCH

    def kinds(self):
        choices = self.choices()
        return choices.tune_kinds() if choices.is_ready() else []

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
        if not kinds:
            return []
        fields = [self.song_player_field()]
        for kind in kinds:
            fields.append(self.page().heading(label=self.heading_of(kind), is_set=lambda kind=kind: self.kind_is_set(kind)))
            if choices.tune_player_in(kind) is not None:
                fields.append(self.tune_field(kind))
            fields.append(self.player_field(kind))
        return fields

    def heading_of(self, kind):
        """Return the heading of a kind of section's part of the panel."""
        return labels.MSG_WIZARD_KIND_HEADING.format(kind=kind)

    def kind_is_set(self, kind):
        """Return whether anything of a kind of section was chosen here: its notes edited, another take, or a player of its own."""
        choices = self.choices()
        return choices.tune_is_own(kind) or choices.tune_take(kind) != FIRST_TUNE_TAKE or choices.tune_played_by_in(kind) is not None

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
        kinds = self.kinds()
        heading = self.page().heading_over_cursor()
        return next((kind for kind in kinds if self.heading_of(kind) == heading), kinds[0] if kinds else None)

    def on_a_tune(self):
        """Return whether the cursor is on a tune's row, where the tune's keys work."""
        return self.page().label_under_cursor() == labels.MSG_WIZARD_TUNE_ROW_LABEL

    def takes(self):
        """A new take writes another tune for the kind under the cursor alone, asking first where the tune was edited by hand."""
        kind = self.kind_under_cursor()
        if kind is None or not self.on_a_tune():
            return None
        choices = self.choices()
        page = self.page()

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
        if kind is None or self.choices().tune_player_in(kind) is None:
            return None
        return messages.MSG_WIZARD_LISTEN_TUNE, self.choices().tune_place(kind), self.choices().tune_player_in(kind)
