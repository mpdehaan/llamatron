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
notes, which the pattern editor opens, and buttons to hear it and to have it written again. The
panel of the kind that says the song's hook line also holds the hook.
"""

from rich.text import Text

from llamatron.macro_composer.melody import HEIGHT
from llamatron.macro_composer.wizard_choices import HOOK_PARTS, MELODY_BUSY
from llamatron.strings import labels, legends, messages
from llamatron.tui.dialogs.confirm_dialog import ConfirmDialog
from llamatron.tui.drawing import INDENT, NOTHING, Style
from llamatron.tui.screens.shared.field import Button, ChoiceField, Field, Toggle
from llamatron.tui.screens.wizard.branch import Branch
from llamatron.tui.screens.wizard.hook_picture import picture_of

# What a panel of a kind's melody is remembered by, apart from a section of the form with the kind's name.
MELODY_KEY = 'melody of {kind}'
# The choice that leaves a field to the genre or to the song, which is no value's name.
NOT_CHOSEN = ''


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

    def says_the_hook(self):
        """Return whether this kind of section is the one that says the song's hook line."""
        place = self.choices().hook_line_place()
        return place is not None and place[0] == self._kind

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
        if self.says_the_hook():
            fields += self.hook_fields()
        return fields + self.buttons()

    def own_field(self, *, field, label, ways, usual, origin):
        """Return a field of the kind's own melody: what the genre or the song gives until a value is chosen, said to be so, and the
        list's first entry gives the field back."""
        choices = self.choices()
        chosen = choices.get_section_melody(kind=self._kind, field=field)
        return ChoiceField(page=self.page(), label=label, choices=[NOT_CHOSEN, *ways], names=[origin, *ways], current=chosen or NOT_CHOSEN,
                           shown=chosen or labels.MSG_WIZARD_VALUE_FROM.format(value=usual, origin=origin),
                           set=self.page().choosing(lambda value: choices.set_section_melody(kind=self._kind, field=field, value=value or None)))

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
        """Return the buttons that hear the melody and that have it written again."""
        if self.choices().tune_player_in(self._kind) is None:
            return []
        page = self.page()
        enter = legends.KeyName.ENTER
        return [Button(label=labels.MSG_WIZARD_LISTEN_BUTTON, key_name=enter, enter=lambda: page.listen_to(self.listens()), enter_what=legends.MSG_LISTEN_WHAT),
                Button(label=labels.MSG_WIZARD_REGENERATE_BUTTON, key_name=enter, enter=self.regenerate, enter_what=legends.MSG_REGENERATE_WHAT)]

    def regenerate(self):
        """Have the kind's melody written again, with nothing kept of the old one, after asking."""
        choices = self.choices()
        page = self.page()
        name = messages.MSG_WIZARD_MELODY_OF.format(kind=self._kind)

        def written(_):
            page.choosing(choices.new_tune_take)(self._kind)
            page.say(messages.MSG_WIZARD_REGENERATED.format(name=name))
        page.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_REGENERATE_TITLE.format(name=name), messages=[messages.MSG_WIZARD_REGENERATE_SAYS.format(name=name)], starts_on_no=True), then=written)

    def field_keys(self):
        page = self.page()
        return [page.bind(page.KEYS.REGENERATE, action=self.regenerate)] if self.choices().tune_player_in(self._kind) is not None else []

    def listens(self):
        """Listen plays the melody's player alone in the first section of the kind."""
        choices = self.choices()
        if choices.tune_place(self._kind) is None or choices.tune_player_in(self._kind) is None:
            return None
        return messages.MSG_WIZARD_MELODY_OF.format(kind=self._kind), choices.tune_place(self._kind), choices.tune_player_in(self._kind)

    # The hook, on the panel of the kind that says it.

    def hook_fields(self):
        """Return the hook's fields: the Hook line switch, and while the song has a hook, who says it in the intro, the parts of its kind
        under a heading, and the row that makes another."""
        choices = self.choices()
        page = self.page()
        if not choices.can_have_hook():
            return []
        switch = Toggle(label=labels.MSG_WIZARD_HOOK_LINE_LABEL, on=choices.has_hook(), set=page.choosing(choices.set_hook))
        if not choices.has_hook():
            return [switch]
        said = self.intro_hook_fields()
        if choices.hook_is_own():
            # A hook written by hand in a song made before melodies were patterns is the person's, and Bksp gives the wizard's back.
            return [switch, *said, Field(label=labels.MSG_WIZARD_HOOK_NOTES_LABEL, value=lambda: labels.MSG_WIZARD_HOOK_NOTES_OWN, clear=lambda: page.choosing(lambda nothing: choices.set_hook_line(None))(None),
                                         clear_what=legends.MSG_TUNE_USUAL_WHAT)]
        parts = [self.part_field(part) for part in choices.hook_parts()] if choices.has_song_plan() else []
        details = [page.heading(label=labels.MSG_WIZARD_GROUP_HOOK, is_set=lambda: any(choices.hook_part_is_chosen(part) for part in choices.hook_parts())), *parts] if parts else []
        # Another hook is a row among the hook's fields, since the panel's buttons are the melody's.
        new_hook = Field(label=labels.MSG_WIZARD_NEW_HOOK_BUTTON, value=lambda: NOTHING, enter=lambda: page.choosing(lambda nothing: choices.new_hook())(None), enter_what=legends.MSG_WIZARD_NEW_HOOK_WHAT)
        return [switch, *said, new_hook, *details]

    def intro_hook_fields(self):
        """Return the field of who says the hook in the intro, before anybody sings it, where somebody can."""
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

    def notes(self, width):
        """Return the picture of the hook, on the panel of the kind that says it, while the song has one."""
        choices = self.choices()
        hook = choices.hook_notes() if self.says_the_hook() and choices.can_have_hook() else None
        if hook is None:
            return []
        made = (messages.MSG_WIZARD_HOOK_OWN if choices.hook_is_own() else messages.MSG_WIZARD_HOOK_MADE).format(player=choices.role_title(choices.tune_player()))
        return [*(Text(INDENT + line) for line in picture_of(hook=hook, width=width)), Text(INDENT + made, style=Style.DIM)]
