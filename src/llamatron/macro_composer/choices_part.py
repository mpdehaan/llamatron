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

"""What every part of the song wizard's choices is: the choices of one thing of the song, such as its drum kit."""

import functools


def kept_until_choices_change(method):
    """Decorate a method of the song wizard's choices, or of a part of them, whose answer is found by making the song, so that the
    answer is worked out once while the choices stand as they are and worked out again once anything a song keeps of them
    changes: a page asks the same thing at every key, and making a song each time made the keys slow. The answer is kept by the
    method's name, by which part asked (a section by its place) and by the arguments, so it is shared and no caller changes it."""
    name = method.__qualname__

    @functools.wraps(method)
    def kept(self, *arguments, **named):
        choices, asker = self.answers_kept_by()
        key = (name, asker, arguments, tuple(sorted(named.items())))
        return choices.remembered(key=key, compute=lambda: method(self, *arguments, **named))
    return kept


def set_each_kept(kept):
    """Give kept values back through their setters, each a setter and the arguments of every call to it, leaving out what a
    setter refuses: a song kept by an older version, or edited by hand, may hold a value no longer allowed."""
    for setter, every in kept:
        for named in every:
            try:
                setter(**named)
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
