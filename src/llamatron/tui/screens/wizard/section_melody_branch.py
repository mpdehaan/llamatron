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

"""A kind of section's melody in the wizard: the verse's, the chorus's, the bridge's.

A song has a melody for each kind of section its melody's player plays in. The panel holds what
is decided for that melody alone: how high it sits against the others and how busy it is, its
notes, which the pattern editor opens, and buttons to hear it, alone and with the band, and to
have it written again. The song's hooks have a panel of their own (hooks_branch.py).
"""

from llamatron.macro_composer.melody import HEIGHT
from llamatron.macro_composer.wizard_choices import MELODY_BUSY, SECTION_MELODY_WAYS
from llamatron.strings import labels, legends, messages
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.screens.shared.field import Button, ChoiceField, Field
from llamatron.tui.screens.wizard.branch import Branch

# What a panel of a kind's melody is remembered by, apart from a section of the form with the kind's name.
MELODY_KEY = 'melody of {kind}'


class SectionMelodyBranch(Branch):
    """The melody of one kind of section."""

    __slots__ = ('_kind',)

    def __init__(self, *, page, kind):
        super().__init__(page=page)
        self._kind = kind

    def key(self):
        return MELODY_KEY.format(kind=self._kind)

    def name(self):
        return self._kind.capitalize()

    def summary(self):
        """Return whether the melody was edited by hand, or who plays it."""
        choices = self.choices()
        if choices.tune_is_own(self._kind):
            return labels.MSG_WIZARD_NOTES_EDITED
        player = choices.tune_player_in(self._kind)
        return choices.role_title(player) if player is not None else labels.MSG_WIZARD_NOBODY

    def fields(self):
        choices = self.choices()
        kind = self._kind
        fields = []
        if HEIGHT in choices.section_melody_fields(kind):
            fields.append(self.own_field(field=HEIGHT, label=labels.MSG_WIZARD_HEIGHT_LABEL, ways=choices.section_melody_ways_offered(kind=kind, field=HEIGHT), usual=choices.genre_height_in(kind), origin=labels.MSG_WIZARD_USUAL_MELODY))
        if MELODY_BUSY in choices.section_melody_fields(kind):
            fields.append(self.own_field(field=MELODY_BUSY, label=labels.MSG_WIZARD_SECTION_BUSY_LABEL, ways=choices.section_melody_ways_offered(kind=kind, field=MELODY_BUSY), usual=choices.get_melody_way(MELODY_BUSY), origin=labels.MSG_WIZARD_FROM_SONG))
        if choices.tune_player_in(kind) is not None:
            fields.append(self.notes_field())
        return fields + self.buttons()

    def own_field(self, *, field, label, ways, usual, origin):
        """Return a field of the kind's own melody: one list of the field's values in their order, the value the genre or the song
        gives said to be so, which gives the field back when picked; a value that makes the same song as that one is left out."""
        choices = self.choices()
        chosen = choices.get_section_melody(kind=self._kind, field=field)
        values = [value for value in SECTION_MELODY_WAYS[field] if value == usual or value in ways]
        names = [labels.MSG_WIZARD_VALUE_FROM.format(value=value, origin=origin) if value == usual else value for value in values]
        now = chosen if chosen in values else usual
        return ChoiceField(page=self.page(), label=label, choices=values, names=names, current=now, shown=names[values.index(now)],
                           set=self.page().choosing(lambda value: choices.set_section_melody(kind=self._kind, field=field, value=None if value == usual else value)))

    def notes_field(self):
        """Return the row of the melody's notes: the wizard's until edited in the pattern editor, which ENTER opens; Bksp gives edited notes back to the wizard."""
        choices = self.choices()
        page = self.page()
        kind = self._kind
        own = choices.tune_is_own(kind)

        def give_back():
            question = messages.MSG_WIZARD_TUNE_GIVE_BACK_QUESTION.format(kind=kind)
            page.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_TUNE_GIVE_BACK_TITLE, messages=[question], starts_on_no=True),
                     then=page.choosing(lambda _: choices.set_tune_pattern(kind=kind, pattern=None)))
        return Field(label=labels.MSG_WIZARD_NOTES_LABEL, value=lambda: labels.MSG_WIZARD_NOTES_EDITED if own else labels.MSG_WIZARD_NOTES_WIZARD, enter=lambda: page.edit_tune(kind),
                     enter_what=legends.MSG_WIZARD_EDIT_NOTES_WHAT, clear=give_back if own else None, clear_what=legends.MSG_TUNE_USUAL_WHAT)

    def buttons(self):
        """Return the buttons that hear the melody, alone and with the band, and that have it written again, each reached with the arrows."""
        if self.choices().tune_player_in(self._kind) is None:
            return []
        page = self.page()
        return [Button(label=labels.MSG_WIZARD_LISTEN_BUTTON, enter=lambda: page.listen_to(self.listens()), enter_what=legends.MSG_LISTEN_WHAT),
                Button(label=labels.MSG_WIZARD_LISTEN_BAND_BUTTON, enter=lambda: page.listen_to(self.heard_with_band()), enter_what=legends.MSG_LISTEN_WHAT),
                Button(label=labels.MSG_WIZARD_REGENERATE_BUTTON, enter=self.regenerate, enter_what=legends.MSG_REGENERATE_WHAT)]

    def heard_with_band(self):
        """Return what Listen With Band plays: everybody in the first section of the kind."""
        return messages.MSG_WIZARD_SECTION_WITH_BAND.format(kind=self._kind), self.choices().tune_place(self._kind), None

    def regenerate(self):
        """Have the kind's melody written again, with nothing kept of the old one, after asking."""
        choices = self.choices()
        page = self.page()
        name = messages.MSG_WIZARD_MELODY_OF.format(kind=self._kind)

        def written(_):
            page.choosing(choices.new_tune_take)(self._kind)
            page.say(messages.MSG_WIZARD_REGENERATED.format(name=name))
        page.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_REGENERATE_TITLE.format(name=name), messages=[messages.MSG_WIZARD_REGENERATE_SAYS.format(name=name)], starts_on_no=True), then=written)

    def listens(self):
        """Listen plays the melody's player alone in the first section of the kind."""
        choices = self.choices()
        if choices.tune_place(self._kind) is None or choices.tune_player_in(self._kind) is None:
            return None
        return messages.MSG_WIZARD_MELODY_OF.format(kind=self._kind), choices.tune_place(self._kind), choices.tune_player_in(self._kind)
