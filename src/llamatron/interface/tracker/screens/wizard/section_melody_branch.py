# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""A kind of section's melody in the wizard: the verse's, the chorus's, the bridge's.

A song has a melody for each kind of section its melody's player plays in. The panel holds what
is decided for that melody alone: how high it sits against the others and how busy it is, and
buttons to edit its notes in the pattern editor, to have it written again, and to hear it, alone
and with the band. The section that says the hook also holds how the hook is written, its
behavior and its gauges, since the hook is a part of that section's melody; which bars are the
hook and who else plays them is on the Hook panel (hooks_branch.py).
"""

from rich.text import Text

from llamatron.interface.tracker import drawing
from llamatron.interface.tracker.dialogs.confirm_dialog import ConfirmDialog
from llamatron.interface.tracker.drawing import Style
from llamatron.interface.tracker.screens.shared.field import Button, ChoiceField
from llamatron.interface.tracker.screens.wizard.branch import Branch
from llamatron.user_strings import labels, legends, messages
from llamatron.wizards.create_song import wizard_limits, wizard_names

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
        choices = self.get_choices()
        if choices.get_tunes().tune_is_own(self._kind):
            return labels.MSG_WIZARD_NOTES_EDITED
        player = choices.get_tunes().tune_player_in(self._kind)
        return choices.player(player).title() if player is not None else labels.MSG_WIZARD_NOBODY

    def fields(self):
        choices = self.get_choices()
        kind = self._kind
        fields = []
        if choices.get_hook().is_body_of_hook(kind):
            # The chorus that holds the hook is written around it: where the hook sits among its lines, and the gauges of the lines between.
            fields = [*self.placement_fields(), *(self.body_gauge_field(name) for name in choices.get_hook().body_gauges())]
        elif wizard_names.MELODY_HEIGHT in choices.section_melody_fields(kind):
            fields.append(self.own_field(field=wizard_names.MELODY_HEIGHT, label=labels.MSG_WIZARD_HEIGHT_LABEL, ways=choices.section_melody_ways_offered(kind=kind, field=wizard_names.MELODY_HEIGHT), usual=choices.genre_height_in(kind), origin=labels.MSG_WIZARD_USUAL_MELODY))
        if wizard_limits.MELODY_BUSY in choices.section_melody_fields(kind) and not choices.get_hook().is_body_of_hook(kind):
            fields.append(self.own_field(field=wizard_limits.MELODY_BUSY, label=labels.MSG_WIZARD_SECTION_BUSY_LABEL, ways=choices.section_melody_ways_offered(kind=kind, field=wizard_limits.MELODY_BUSY), usual=choices.get_melody_way(wizard_limits.MELODY_BUSY), origin=labels.MSG_WIZARD_FROM_SONG))
        return fields + self.hook_fields() + self.buttons()

    def says_the_hook(self):
        """Return whether this kind of section is the one that says the song's hook, in a song whose hook is written by its gauges."""
        choices = self.get_choices()
        return choices.get_hook().can_have_hook() and choices.get_hook().has_hook() and choices.get_hook().writes_hook() and not choices.get_hook().hook_is_own() and choices.get_hook().hook_kind() == self._kind

    def hook_fields(self):
        """Return the fields of how the hook is written, under a heading, in the section that says the hook: its behavior, the
        genre's said to be so, and the gauges that change a hook of that behavior."""
        if not self.says_the_hook():
            return []
        choices = self.get_choices()
        page = self.get_page()
        usual = choices.get_hook().genre_hook_behavior()
        values = list(wizard_names.BEHAVIORS)
        names = [labels.MSG_WIZARD_VALUE_FROM.format(value=value, origin=labels.MSG_WIZARD_USUAL_MELODY) if value == usual else value for value in values]
        now = choices.get_hook().get_hook_behavior()
        behavior = ChoiceField(page=page, label=labels.MSG_WIZARD_BEHAVIOR_LABEL, choices=values, names=names, current=now, shown=names[values.index(now)], set=page.choosing(choices.get_hook().set_hook_behavior))
        return [page.heading(label=labels.MSG_WIZARD_HOOK_HEADING, is_set=self.hook_is_set, starts_open=True), behavior, *(self.hook_gauge_field(name) for name in choices.get_hook().hook_gauges())]

    def hook_is_set(self):
        choices = self.get_choices()
        return choices.get_hook().get_hook_behavior() != choices.get_hook().genre_hook_behavior() or any(choices.get_hook().writing_gauge_is_moved(part=wizard_names.HOOK_WRITING, name=name) for name in choices.get_hook().hook_gauges())

    def hook_gauge_field(self, name):
        choices = self.get_choices()
        return self.writing_gauge_field(label=labels.MSG_WIZARD_HOOK_GAUGE_LABELS[name], position=choices.get_hook().get_hook_gauge(name), moved=choices.get_hook().writing_gauge_is_moved(part=wizard_names.HOOK_WRITING, name=name),
                                        set_position=lambda position: choices.get_hook().set_hook_gauge(name=name, position=position))

    def placement_fields(self):
        """Return the field of where the hook sits among the chorus's lines, the genre's own place said to be so, where the chorus has such places."""
        choices = self.get_choices()
        offered = choices.get_hook().hook_placements_offered()
        if not offered:
            return []
        usual = choices.get_hook().genre_hook_placement()
        names = [labels.MSG_WIZARD_VALUE_FROM.format(value=value, origin=labels.MSG_WIZARD_USUAL_MELODY) if value == usual else value for value in offered]
        now = choices.get_hook().get_hook_placement()
        return [ChoiceField(page=self.get_page(), label=labels.MSG_WIZARD_PLACEMENT_LABEL, choices=offered, names=names, current=now, shown=names[offered.index(now)],
                            set=self.get_page().choosing(choices.get_hook().set_hook_placement))]

    def body_gauge_field(self, name):
        choices = self.get_choices()
        return self.writing_gauge_field(label=labels.MSG_WIZARD_BODY_GAUGE_LABELS[name], position=choices.get_hook().get_body_gauge(name), moved=choices.get_hook().writing_gauge_is_moved(part=wizard_names.BODY_WRITING, name=name),
                                        set_position=lambda position: choices.get_hook().set_body_gauge(name=name, position=position))

    def own_field(self, *, field, label, ways, usual, origin):
        """Return a field of the kind's own melody: one list of the field's values in their order, the value the genre or the song
        gives said to be so, which gives the field back when picked; a value that makes the same song as that one is left out."""
        choices = self.get_choices()
        chosen = choices.get_section_melody(kind=self._kind, field=field)
        values = [value for value in wizard_limits.SECTION_MELODY_WAYS[field] if value == usual or value in ways]
        names = [labels.MSG_WIZARD_VALUE_FROM.format(value=value, origin=origin) if value == usual else value for value in values]
        now = chosen if chosen in values else usual
        return ChoiceField(page=self.get_page(), label=label, choices=values, names=names, current=now, shown=names[values.index(now)],
                           set=self.get_page().choosing(lambda value: choices.set_section_melody(kind=self._kind, field=field, value=None if value == usual else value)))

    def buttons(self):
        """Return the buttons that open the melody's notes in the pattern editor, that have the melody written again, and that
        hear it, alone and with the band, each reached with the arrows."""
        if self.get_choices().get_tunes().tune_player_in(self._kind) is None:
            return []
        page = self.get_page()
        choices = self.get_choices()
        kind = self._kind

        def give_back():
            question = messages.MSG_WIZARD_TUNE_GIVE_BACK_QUESTION.format(kind=kind)
            page.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_TUNE_GIVE_BACK_TITLE, messages=[question], starts_on_no=True),
                     then=page.choosing(lambda _: choices.get_tunes().set_tune_pattern(kind=kind, pattern=None)))
        # On notes edited by hand, the delete key on the button gives the notes back to the wizard, after a question.
        own = choices.get_tunes().tune_is_own(kind)
        return [Button(label=labels.MSG_WIZARD_EDIT_NOTES_BUTTON, enter=lambda: page.edit_tune(kind), enter_what=legends.MSG_WIZARD_EDIT_NOTES_WHAT, clear=give_back if own else None,
                       clear_what=legends.MSG_TUNE_USUAL_WHAT),
                Button(label=labels.MSG_WIZARD_REGENERATE_BUTTON, enter=self.regenerate, enter_what=legends.MSG_REGENERATE_WHAT),
                Button(label=labels.MSG_WIZARD_LISTEN_BUTTON, enter=lambda: page.listen_to(self.listens()), enter_what=legends.MSG_LISTEN_WHAT),
                Button(label=labels.MSG_WIZARD_LISTEN_BAND_BUTTON, enter=lambda: page.listen_to(self.heard_with_band()), enter_what=legends.MSG_LISTEN_WHAT)]

    def remarks(self, width):
        """Return the line under the buttons that says whose the melody's notes are: the wizard's, or edited by hand."""
        choices = self.get_choices()
        if not choices.is_ready() or choices.get_tunes().tune_player_in(self._kind) is None:
            return []
        return [Text(drawing.INDENT + (messages.MSG_WIZARD_NOTES_BY_HAND if choices.get_tunes().tune_is_own(self._kind) else messages.MSG_WIZARD_HOOK_MADE), style=Style.DIM)]

    def heard_with_band(self):
        """Return what Listen With Band plays: everybody in the first section of the kind."""
        return messages.MSG_WIZARD_SECTION_WITH_BAND.format(kind=self._kind), self.get_choices().get_tunes().tune_place(self._kind), None

    def regenerate(self):
        """Have the kind's melody written again, with nothing kept of the old one, after asking."""
        choices = self.get_choices()
        page = self.get_page()
        name = messages.MSG_WIZARD_MELODY_OF.format(kind=self._kind)

        def written(_):
            page.choosing(choices.get_tunes().new_tune_take)(self._kind)
            page.say(messages.MSG_WIZARD_REGENERATED.format(name=name))
        page.ask(dialog=ConfirmDialog(title=messages.MSG_WIZARD_REGENERATE_TITLE.format(name=name), messages=[messages.MSG_WIZARD_REGENERATE_SAYS.format(name=name)], starts_on_no=True), then=written)

    def listens_alone(self):
        return True

    def listens(self):
        """Listen plays the melody's player alone in the first section of the kind."""
        choices = self.get_choices()
        if choices.get_tunes().tune_place(self._kind) is None or choices.get_tunes().tune_player_in(self._kind) is None:
            return None
        return messages.MSG_WIZARD_MELODY_OF.format(kind=self._kind), choices.get_tunes().tune_place(self._kind), choices.get_tunes().tune_player_in(self._kind)
