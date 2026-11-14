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
"""Revisions: how anything that changes says so, so that work done from it can be kept until it does.

Everything a set file stores carries a revision, a number that moves whenever the object changes.
An answer worked out from some objects is kept with their revisions (support/memory.py), and is
good for as long as none of them has moved, which is how the tracker avoids working anything out
again when nothing it came from has changed, and how playback will know which clips to make again.

Every revision comes from one clock, so no two are ever the same: a new object, or a copy, starts
with a revision nothing has had, and a change gives the object another. So when an answer was
worked out from "the pattern called bass" and another pattern now has that name, the revision
differs just as it would had the pattern been edited, and nothing has to tell the two cases apart.
"""

import functools


class RevisionClock:
    """Hands out revisions, each one higher than the last."""

    __slots__ = ('_latest',)

    def __init__(self):
        self._latest = 0

    def next(self):
        self._latest += 1
        return self._latest

    def latest(self):
        return self._latest


# The one clock every revision comes from, so that no two objects ever share one.
_CLOCK = RevisionClock()


def latest_revision():
    """Return the last revision handed out, which moves whenever anything at all changes or is made."""
    return _CLOCK.latest()


class Revised:
    """Something that changes and says so.

    A subclass calls note_change() in its constructor and writes every method that changes it
    under @notes_change, which test/test_revisions.py checks, so that revision() is different
    after every change.
    """

    __slots__ = ('_revision',)

    def revision(self):
        """Return this object's revision: a number no other object has, different after every change to this one."""
        return self._revision

    def note_change(self):
        """Note that this object changed, or was just made, by taking a new revision."""
        self._revision = _CLOCK.next()


def notes_change(method):
    """Mark a method as one that changes its object, whose revision moves each time the method is called.

    Every method of a Revised class that changes the object is written under @notes_change, which
    says so where the method is defined and which test/test_revisions.py checks. The revision
    moves before the method runs, so a method that refuses its value has moved it for nothing,
    which costs only an answer worked out again.
    """
    @functools.wraps(method)
    def changing(self, *arguments, **named):
        self.note_change()
        return method(self, *arguments, **named)
    return changing


class ChangeMark(Revised):
    """A revision with no data of its own, for a group of things that change together and have no one object to carry theirs."""

    __slots__ = ()

    def __init__(self):
        self.note_change()
