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
"""A method's answer kept on its object until what the answer was worked out from changes.

A page of the song wizard asks the same questions of the choices many times a key, and some answers, such as the style
template laid over by the subgenre, take long to work out. A method written under @kept_while(key_of) works its answer out
once and returns the same object again while key_of(self) gives an equal key, so that the second call costs the key alone.
The key holds everything the answer depends on; a key of None keeps nothing. The answer is shared between callers, so a kept
method returns something no caller changes: a tuple, a string, or a dictionary every caller only reads. The object keeps its
answers in a dictionary it names KEPT, declared in its __slots__ and made empty in its constructor.
"""

import functools

# The attribute an object keeps its answers in, by the method's name.
KEPT = '_kept'
# What an answer not yet worked out is, apart from every answer, None included.
MISSING = object()


def kept_while(key_of):
    """Decorate a method so that its answer for each set of arguments is kept while key_of(self) gives an equal key: the
    arguments, by keyword, are part of what an answer is kept by, and must be hashable."""
    def decorate(method):
        name = method.__name__

        @functools.wraps(method)
        def kept(self, **named):
            key = key_of(self)
            if key is None:
                return method(self, **named)
            answers = getattr(self, KEPT)
            held = answers.get(name)
            if held is None or held[0] != key:
                held = (key, {})
                answers[name] = held
            asked = tuple(sorted(named.items())) if named else ()
            found = held[1].get(asked, MISSING)
            if found is MISSING:
                found = method(self, **named)
                held[1][asked] = found
            return found
        return kept
    return decorate
