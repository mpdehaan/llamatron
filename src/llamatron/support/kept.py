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


def kept_while(key_of):
    """Decorate a method that takes nothing but its object, so that its answer is kept while key_of(self) gives an equal key."""
    def decorate(method):
        name = method.__name__

        @functools.wraps(method)
        def kept(self):
            key = key_of(self)
            if key is None:
                return method(self)
            answers = getattr(self, KEPT)
            held = answers.get(name)
            if held is not None and held[0] == key:
                return held[1]
            answer = method(self)
            answers[name] = (key, answer)
            return answer
        return kept
    return decorate
