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

import functools
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


def _marked_names(values, *, usual, origin):
    """Return the names a list of values is shown by: each value as it is, but the value the genre or the song gives, said to
    be so."""
    names = []
    for value in values:
        if value == usual:
            names.append(labels.MSG_WIZARD_VALUE_FROM.format(value=value, origin=origin))
        else:
            names.append(value)
    return names


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
        tunes = self._tunes()
        if tunes.tune_is_own(self._kind):
            return labels.MSG_WIZARD_NOTES_EDITED
        role = tunes.tune_player_in(self._kind)
        if role is None:
            return labels.MSG_WIZARD_NOBODY
        player = self.get_choices().player(role)
        return player.title()

    def fields(self):
        hook = self._hook()
        fields = []
        if hook.is_body_of_hook(self._kind):
            # The chorus that holds the hook is written around it: where the hook sits among its lines, and the gauges of the
            # lines between.
            fields += self.placement_fields()
            for name in hook.body_gauges():
                fields.append(self.body_gauge_field(name))
        else:
            fields += self._own_melody_fields()
        return fields + self.hook_fields() + self.buttons()

    def _own_melody_fields(self):
        """Return the fields of the kind's own melody the subgenre hears: how high it sits, against the genre's, and how busy
        it is, against the song's."""
        choices = self.get_choices()
        own = self._own_melody()
        offered = own.fields()
        fields = []
        if wizard_names.MELODY_HEIGHT in offered:
            usual = choices.genre_height_in(self._kind)
            fields.append(self.own_field(field=wizard_names.MELODY_HEIGHT, label=labels.MSG_WIZARD_HEIGHT_LABEL,
                                         ways=own.ways_offered(wizard_names.MELODY_HEIGHT), usual=usual, origin=labels.MSG_WIZARD_USUAL_MELODY))
        if wizard_limits.MELODY_BUSY in offered:
            song_ways = choices.melody_ways()
            usual = song_ways.get_way(wizard_limits.MELODY_BUSY)
            fields.append(self.own_field(field=wizard_limits.MELODY_BUSY, label=labels.MSG_WIZARD_SECTION_BUSY_LABEL,
                                         ways=own.ways_offered(wizard_limits.MELODY_BUSY), usual=usual, origin=labels.MSG_WIZARD_FROM_SONG))
        return fields

    def says_the_hook(self):
        """Return whether this kind of section is the one that says the song's hook, in a song whose hook is written by its
        gauges."""
        hook = self._hook()
        written_by_gauges = hook.can_have_hook() and hook.has_hook() and hook.writes_hook() and not hook.hook_is_own()
        return written_by_gauges and hook.hook_kind() == self._kind

    def hook_fields(self):
        """Return the fields of how the hook is written, under a heading, in the section that says the hook: its behavior, the
        genre's said to be so, and the gauges that change a hook of that behavior."""
        if not self.says_the_hook():
            return []
        page = self.get_page()
        hook = self._hook()
        values = list(wizard_names.BEHAVIORS)
        names = _marked_names(values, usual=hook.genre_hook_behavior(), origin=labels.MSG_WIZARD_USUAL_MELODY)
        behavior = self._marked_choice(label=labels.MSG_WIZARD_BEHAVIOR_LABEL, values=values, names=names, now=hook.get_hook_behavior(),
                                       set=page.choosing(hook.set_hook_behavior))
        fields = [page.heading(label=labels.MSG_WIZARD_HOOK_HEADING, is_set=self.hook_is_set, starts_open=True), behavior]
        for name in hook.hook_gauges():
            fields.append(self.hook_gauge_field(name))
        return fields

    def _marked_choice(self, *, label, values, names, now, set):
        """Return a field chosen from a list of values in their order, shown by the names given."""
        return ChoiceField(page=self.get_page(), label=label, choices=values, names=names, current=now, shown=names[values.index(now)], set=set)

    def hook_is_set(self):
        hook = self._hook()
        if hook.get_hook_behavior() != hook.genre_hook_behavior():
            return True
        for name in hook.hook_gauges():
            if hook.writing_gauge_is_moved(part=wizard_names.HOOK_WRITING, name=name):
                return True
        return False

    def hook_gauge_field(self, name):
        hook = self._hook()
        moved = hook.writing_gauge_is_moved(part=wizard_names.HOOK_WRITING, name=name)
        return self.writing_gauge_field(label=labels.MSG_WIZARD_HOOK_GAUGE_LABELS[name], position=hook.get_hook_gauge(name), moved=moved,
                                        set_position=functools.partial(self._set_hook_gauge, name=name))

    def _set_hook_gauge(self, position, *, name):
        self._hook().set_hook_gauge(name=name, position=position)

    def placement_fields(self):
        """Return the field of where the hook sits among the chorus's lines, the genre's own place said to be so, where the
        chorus has such places."""
        page = self.get_page()
        hook = self._hook()
        offered = hook.hook_placements_offered()
        if not offered:
            return []
        names = _marked_names(offered, usual=hook.genre_hook_placement(), origin=labels.MSG_WIZARD_USUAL_MELODY)
        return [self._marked_choice(label=labels.MSG_WIZARD_PLACEMENT_LABEL, values=offered, names=names, now=hook.get_hook_placement(),
                                    set=page.choosing(hook.set_hook_placement))]

    def body_gauge_field(self, name):
        hook = self._hook()
        moved = hook.writing_gauge_is_moved(part=wizard_names.BODY_WRITING, name=name)
        return self.writing_gauge_field(label=labels.MSG_WIZARD_BODY_GAUGE_LABELS[name], position=hook.get_body_gauge(name), moved=moved,
                                        set_position=functools.partial(self._set_body_gauge, name=name))

    def _set_body_gauge(self, position, *, name):
        self._hook().set_body_gauge(name=name, position=position)

    def own_field(self, *, field, label, ways, usual, origin):
        """Return a field of the kind's own melody: one list of the field's values in their order, the value the genre or the
        song gives said to be so, which gives the field back when picked; a value that makes the same song as that one is left
        out."""
        chosen = self._own_melody().get_way(field)
        values = []
        for value in wizard_limits.SECTION_MELODY_WAYS[field]:
            if value == usual or value in ways:
                values.append(value)
        now = usual
        if chosen in values:
            now = chosen
        page = self.get_page()
        choose = page.choosing(functools.partial(self._set_way, field=field, usual=usual))
        names = _marked_names(values, usual=usual, origin=origin)
        return self._marked_choice(label=label, values=values, names=names, now=now, set=choose)

    def _set_way(self, value, *, field, usual):
        """Give the kind's melody a way of its own, or give the field back where the value picked is the usual one."""
        if value == usual:
            value = None
        self._own_melody().set_way(field=field, value=value)

    def buttons(self):
        """Return the buttons that open the melody's notes in the pattern editor, that have the melody written again, and that
        hear it, alone and with the band, each reached with the arrows."""
        tunes = self._tunes()
        if tunes.tune_player_in(self._kind) is None:
            return []
        page = self.get_page()
        # On notes edited by hand, the delete key on the button gives the notes back to the wizard, after a question.
        give_back = None
        if tunes.tune_is_own(self._kind):
            give_back = self._ask_to_give_back
        edit = functools.partial(page.edit_tune, self._kind)
        return [
            Button(label=labels.MSG_WIZARD_EDIT_NOTES_BUTTON, enter=edit, enter_what=legends.MSG_WIZARD_EDIT_NOTES_WHAT, clear=give_back,
                   clear_what=legends.MSG_TUNE_USUAL_WHAT),
            Button(label=labels.MSG_WIZARD_REGENERATE_BUTTON, enter=self.regenerate, enter_what=legends.MSG_REGENERATE_WHAT),
            Button(label=labels.MSG_WIZARD_LISTEN_BUTTON, enter=self._listen, enter_what=legends.MSG_LISTEN_WHAT),
            Button(label=labels.MSG_WIZARD_LISTEN_BAND_BUTTON, enter=self._listen_with_band, enter_what=legends.MSG_LISTEN_WHAT),
        ]

    def _ask_to_give_back(self):
        """Ask whether the notes edited by hand go back to the wizard's, and give them back on yes."""
        page = self.get_page()
        question = messages.MSG_WIZARD_TUNE_GIVE_BACK_QUESTION.format(kind=self._kind)
        dialog = ConfirmDialog(title=messages.MSG_WIZARD_TUNE_GIVE_BACK_TITLE, messages=[question], starts_on_no=True)
        page.ask(dialog=dialog, then=page.choosing(self._give_back))

    def _give_back(self, _):
        self._tunes().set_tune_pattern(kind=self._kind, pattern=None)

    def _listen(self):
        self.get_page().listen_to(self.listens())

    def _listen_with_band(self):
        self.get_page().listen_to(self.heard_with_band())

    def remarks(self, width):
        """Return the line under the buttons that says whose the melody's notes are: the wizard's, or edited by hand."""
        choices = self.get_choices()
        tunes = self._tunes()
        if not choices.is_ready() or tunes.tune_player_in(self._kind) is None:
            return []
        whose = messages.MSG_WIZARD_HOOK_MADE
        if tunes.tune_is_own(self._kind):
            whose = messages.MSG_WIZARD_NOTES_BY_HAND
        return [Text(drawing.INDENT + whose, style=Style.DIM)]

    def heard_with_band(self):
        """Return what Listen With Band plays: everybody in the first section of the kind."""
        place = self._tunes().tune_place(self._kind)
        return messages.MSG_WIZARD_SECTION_WITH_BAND.format(kind=self._kind), place, None

    def regenerate(self):
        """Have the kind's melody written again, with nothing kept of the old one, after asking."""
        page = self.get_page()
        name = messages.MSG_WIZARD_MELODY_OF.format(kind=self._kind)
        dialog = ConfirmDialog(title=messages.MSG_WIZARD_REGENERATE_TITLE.format(name=name), messages=[messages.MSG_WIZARD_REGENERATE_SAYS.format(name=name)],
                               starts_on_no=True)
        page.ask(dialog=dialog, then=functools.partial(self._write_again, name=name))

    def _write_again(self, _, *, name):
        """Have the kind's melody written again, and say so."""
        page = self.get_page()
        write = page.choosing(self._tunes().new_tune_take)
        write(self._kind)
        page.say(messages.MSG_WIZARD_REGENERATED.format(name=name))

    def listens_alone(self):
        return True

    def listens(self):
        """Listen plays the melody's player alone in the first section of the kind."""
        tunes = self._tunes()
        place = tunes.tune_place(self._kind)
        player = tunes.tune_player_in(self._kind)
        if place is None or player is None:
            return None
        return messages.MSG_WIZARD_MELODY_OF.format(kind=self._kind), place, player

    def _hook(self):
        """Return the choices of the song's hooks."""
        choices = self.get_choices()
        return choices.get_hook()

    def _tunes(self):
        """Return the choices of the song's tunes."""
        choices = self.get_choices()
        return choices.get_tunes()

    def _own_melody(self):
        """Return what the kind of section was given of its own melody."""
        ways = self.get_choices().melody_ways()
        return ways.of_kind(self._kind)
