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
is decided for that melody alone: how high it sits against the others and how busy it is, and
buttons to edit its notes in the pattern editor, to have it written again, and to hear it, alone
and with the band. The section that says the hook also holds how the hook is written, its
behavior and its gauges, since the hook is a part of that section's melody; which bars are the
hook and who else plays them is on the Hook panel (hooks_branch.py).
"""

from rich.text import Text


from llamatron.macro_composer import hook_writing
from llamatron.macro_composer.melody import HEIGHT
from llamatron.macro_composer.wizard_choices import MELODY_BUSY, SECTION_MELODY_WAYS
from llamatron.strings import labels, legends, messages
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.drawing import INDENT, Style
from llamatron.tui.screens.shared.field import Button, ChoiceField
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
        if choices.is_body_of_hook(kind):
            # The chorus that holds the hook is written around it: where the hook sits among its lines, and the gauges of the lines between.
            fields = [*self.placement_fields(), *(self.body_gauge_field(name) for name in choices.body_gauges())]
        elif HEIGHT in choices.section_melody_fields(kind):
            fields.append(self.own_field(field=HEIGHT, label=labels.MSG_WIZARD_HEIGHT_LABEL, ways=choices.section_melody_ways_offered(kind=kind, field=HEIGHT), usual=choices.genre_height_in(kind), origin=labels.MSG_WIZARD_USUAL_MELODY))
        if MELODY_BUSY in choices.section_melody_fields(kind) and not choices.is_body_of_hook(kind):
            fields.append(self.own_field(field=MELODY_BUSY, label=labels.MSG_WIZARD_SECTION_BUSY_LABEL, ways=choices.section_melody_ways_offered(kind=kind, field=MELODY_BUSY), usual=choices.get_melody_way(MELODY_BUSY), origin=labels.MSG_WIZARD_FROM_SONG))
        return fields + self.hook_fields() + self.buttons()

    def says_the_hook(self):
        """Return whether this kind of section is the one that says the song's hook, in a song whose hook is written by its gauges."""
        choices = self.choices()
        return choices.can_have_hook() and choices.has_hook() and choices.writes_hook() and not choices.hook_is_own() and choices.hook_kind() == self._kind

    def hook_fields(self):
        """Return the fields of how the hook is written, under a heading, in the section that says the hook: its behavior, the
        genre's said to be so, and the gauges that change a hook of that behavior."""
        if not self.says_the_hook():
            return []
        choices = self.choices()
        page = self.page()
        usual = choices.genre_hook_behavior()
        values = list(hook_writing.BEHAVIORS)
        names = [labels.MSG_WIZARD_VALUE_FROM.format(value=value, origin=labels.MSG_WIZARD_USUAL_MELODY) if value == usual else value for value in values]
        now = choices.get_hook_behavior()
        behavior = ChoiceField(page=page, label=labels.MSG_WIZARD_BEHAVIOR_LABEL, choices=values, names=names, current=now, shown=names[values.index(now)], set=page.choosing(choices.set_hook_behavior))
        return [page.heading(label=labels.MSG_WIZARD_HOOK_HEADING, is_set=self.hook_is_set, starts_open=True), behavior, *(self.hook_gauge_field(name) for name in choices.hook_gauges())]

    def hook_is_set(self):
        choices = self.choices()
        return choices.get_hook_behavior() != choices.genre_hook_behavior() or any(choices.writing_gauge_is_moved(part=hook_writing.HOOK_WRITING, name=name) for name in choices.hook_gauges())

    def hook_gauge_field(self, name):
        choices = self.choices()
        return self.writing_gauge_field(label=labels.MSG_WIZARD_HOOK_GAUGE_LABELS[name], position=choices.get_hook_gauge(name), moved=choices.writing_gauge_is_moved(part=hook_writing.HOOK_WRITING, name=name),
                                        set_position=lambda position: choices.set_hook_gauge(name=name, position=position))

    def placement_fields(self):
        """Return the field of where the hook sits among the chorus's lines, the genre's own place said to be so, where the chorus has such places."""
        choices = self.choices()
        offered = choices.hook_placements_offered()
        if not offered:
            return []
        usual = choices.genre_hook_placement()
        names = [labels.MSG_WIZARD_VALUE_FROM.format(value=value, origin=labels.MSG_WIZARD_USUAL_MELODY) if value == usual else value for value in offered]
        now = choices.get_hook_placement()
        return [ChoiceField(page=self.page(), label=labels.MSG_WIZARD_PLACEMENT_LABEL, choices=offered, names=names, current=now, shown=names[offered.index(now)],
                            set=self.page().choosing(choices.set_hook_placement))]

    def body_gauge_field(self, name):
        choices = self.choices()
        return self.writing_gauge_field(label=labels.MSG_WIZARD_BODY_GAUGE_LABELS[name], position=choices.get_body_gauge(name), moved=choices.writing_gauge_is_moved(part=hook_writing.BODY_WRITING, name=name),
                                        set_position=lambda position: choices.set_body_gauge(name=name, position=position))

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

    def buttons(self):
        """Return the buttons that open the melody's notes in the pattern editor, that have the melody written again, and that
        hear it, alone and with the band, each reached with the arrows."""
        if self.choices().tune_player_in(self._kind) is None:
            return []
        page = self.page()
        choices = self.choices()
        kind = self._kind

        def give_back():
            question = messages.MSG_WIZARD_TUNE_GIVE_BACK_QUESTION.format(kind=kind)
            page.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_TUNE_GIVE_BACK_TITLE, messages=[question], starts_on_no=True),
                     then=page.choosing(lambda _: choices.set_tune_pattern(kind=kind, pattern=None)))
        # On notes edited by hand, the delete key on the button gives the notes back to the wizard, after a question.
        own = choices.tune_is_own(kind)
        return [Button(label=labels.MSG_WIZARD_EDIT_NOTES_BUTTON, enter=lambda: page.edit_tune(kind), enter_what=legends.MSG_WIZARD_EDIT_NOTES_WHAT, clear=give_back if own else None,
                       clear_what=legends.MSG_TUNE_USUAL_WHAT),
                Button(label=labels.MSG_WIZARD_REGENERATE_BUTTON, enter=self.regenerate, enter_what=legends.MSG_REGENERATE_WHAT),
                Button(label=labels.MSG_WIZARD_LISTEN_BUTTON, enter=lambda: page.listen_to(self.listens()), enter_what=legends.MSG_LISTEN_WHAT),
                Button(label=labels.MSG_WIZARD_LISTEN_BAND_BUTTON, enter=lambda: page.listen_to(self.heard_with_band()), enter_what=legends.MSG_LISTEN_WHAT)]

    def notes(self, width):
        """Return the line under the buttons that says whose the melody's notes are: the wizard's, or edited by hand."""
        choices = self.choices()
        if not choices.is_ready() or choices.tune_player_in(self._kind) is None:
            return []
        return [Text(INDENT + (messages.MSG_WIZARD_NOTES_BY_HAND if choices.tune_is_own(self._kind) else messages.MSG_WIZARD_HOOK_MADE), style=Style.DIM)]

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

    def listens_alone(self):
        return True

    def listens(self):
        """Listen plays the melody's player alone in the first section of the kind."""
        choices = self.choices()
        if choices.tune_place(self._kind) is None or choices.tune_player_in(self._kind) is None:
            return None
        return messages.MSG_WIZARD_MELODY_OF.format(kind=self._kind), choices.tune_place(self._kind), choices.tune_player_in(self._kind)
