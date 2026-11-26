# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What every part of the song wizard's choices is: the choices of one thing of the song, such as its drum kit."""

import functools


def cached_until_choices_change(method):
    """Decorate a method of the song wizard's choices, or of a part of them, whose answer is found by making the song, so that the
    answer is worked out once while the choices stand as they are and worked out again once anything a song keeps of them
    changes: a page asks the same thing at every key, and making a song each time made the keys slow. The answer is kept by the
    method's name, by which part asked (a section by its place) and by the arguments, so it is shared and no caller changes it."""
    name = method.__qualname__

    @functools.wraps(method)
    def kept(self, *arguments, **named):
        choices, asker = self.answers_kept_by()
        key = (name, asker, arguments, frozendict(named))
        return choices.remembered(key=key, compute=lambda: method(self, *arguments, **named))
    return kept


def chosen_only(held):
    """Return what was chosen of held values: every one but those that are None."""
    return {field: value for field, value in held.items() if value is not None}


def add_counted(counted, *, kind, held):
    """Add each of held's settings to counted under its kind and its name, and a setting held by name under each inner name,
    so that two sets of choices can be compared setting by setting."""
    for name, value in held.items():
        if isinstance(value, dict):
            for inner, each in value.items():
                counted[(kind, name, inner)] = each
        else:
            counted[(kind, name)] = value


class SavedChoices:
    """What a song file saved of the song wizard's choices, read back value by value to restore them.

    A song saved by an older version, or edited by hand, may hold a value no longer allowed, or a value of the wrong kind:
    each value is read as what it should be, nothing where it is not, and a setter that refuses a value leaves it out."""

    __slots__ = ('_data',)

    def __init__(self, data):
        self._data = data or {}

    def value(self, field):
        """Return the value saved under a field, or None where nothing is."""
        return self._data.get(field)

    def mapping(self, field):
        """Return the values saved under a field by name, or none where they are not saved by name."""
        return self.as_mapping(self._data.get(field))

    def listing(self, field):
        """Return the values saved under a field as a list, or none where they are not a list."""
        values = self._data.get(field)
        if isinstance(values, list):
            return values
        return []

    @staticmethod
    def as_mapping(values):
        """Return values saved by name, or none where they are not saved by name."""
        if isinstance(values, dict):
            return values
        return {}

    @staticmethod
    def apply(setter, *arguments, **named):
        """Restore a saved value through its setter, leaving it out where the setter refuses it."""
        try:
            setter(*arguments, **named)
        except (TypeError, ValueError):
            pass


class ChoicesPart:
    """One part of the song wizard's choices: what was chosen of one thing of the song, held by the part itself.

    A part is reached through the choices it belongs to, as get_kit() reaches the drum kit's, and it asks those choices
    only for what every part shares: the style, the band and the song as chosen so far. Each part can say what a song keeps
    of it (to_data), take that back (read), go back to what the subgenre gives (reset), and say what it adds to the song's
    picks.
    """

    __slots__ = ('_choices',)

    def __init__(self, *, choices):
        self._choices = choices

    def answers_kept_by(self):
        """Return the choices that keep this part's answers, and which part asked: one of its kind is the only one."""
        return self._choices, None
