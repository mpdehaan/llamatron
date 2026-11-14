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
"""A memory of answers, each kept until something it was worked out from changes.

The tracker asks the same questions over and over as it draws: which scale a pattern plays under,
which notes cover each step, what uses a scale. An answer is asked for through remembered(), with
a key naming the question, the things the answer is worked out from, and the function that works
it out. The answer is kept with the revisions of those things (support/revised.py) and returned
until one of them has moved, so an edit to one pattern leaves what is known about everything else
alone.

The danger is an answer that leaves out something it was worked out from, which would go on being
returned after that thing changed. So a memory can check itself, which the tests turn on for every
memory (Memory.check_every_answer): a kept answer is worked out again the first time it's returned
after anything at all has changed, and a difference raises StaleAnswer.
"""

from typing import NamedTuple

from llamatron.strings.errors import ERR_STALE_ANSWER
from llamatron.support.revised import latest_revision

# How many answers a memory keeps before it forgets them all, so that keys naming things long gone can't pile up for ever.
MAX_ANSWERS = 20000


class StaleAnswer(Exception):
    """Something kept differs from the same thing worked out again: what it was worked out from changed without the keeper knowing.

    A memory raises it for an answer whose on left something out. The document raises it, when
    its memory checks, for data an object kept past a change, for a snapshot that was changed
    after the undo history kept it, and for an undo that put back something other than what
    loading the snapshot would.
    """


class Kept(NamedTuple):
    """An answer, and the revisions of what it was worked out from."""

    revisions: tuple
    answer: object


class Memory:
    """Answers by key, each kept until one of the things it was worked out from has a new revision."""

    __slots__ = ('_kept', '_checks', '_checked')

    # Whether a new memory checks every answer unless told otherwise, which the tests turn on.
    _checks_by_default = False

    @classmethod
    def check_every_answer(cls, *, checks=True):
        """Make every memory made from now on check its answers, for the tests: test/ui_testing.py and test/rendering.py call this.

        A test of what happens without the checks turns them off for the memories it makes, and on again after.
        """
        cls._checks_by_default = checks

    def __init__(self, *, checks=None):
        self._kept = {}
        self._checks = Memory._checks_by_default if checks is None else checks
        # For each key, the latest revision anywhere when its answer was last worked out, so that a check is made once per change and not on every ask.
        self._checked = {}

    def remembered(self, *, key, on, compute):
        """Return the answer to the question key names, worked out by compute unless it's kept and nothing in on has changed since.

        on lists everything the answer is worked out from, each with a revision(). Leaving one
        out keeps a wrong answer after that thing changes, which checking finds.
        """
        # This is asked hundreds of times for every key press, so the revisions are gathered here rather than through a function.
        revisions = tuple([thing.revision() for thing in on])
        kept = self._kept.get(key)
        if kept is not None and kept.revisions == revisions:
            if self._checks:
                self._check(key=key, kept=kept, compute=compute)
            return kept.answer
        answer = compute()
        if len(self._kept) >= MAX_ANSWERS:
            self.forget()
        self._kept[key] = Kept(revisions=revisions, answer=answer)
        if self._checks:
            self._checked[key] = latest_revision()
        return answer

    def checks(self):
        """Return whether this memory checks its answers, which is how the document knows to check what it shares too."""
        return self._checks

    def forget(self):
        """Drop every answer, as opening another set does."""
        self._kept.clear()
        self._checked.clear()

    def count(self):
        """Return how many answers are kept."""
        return len(self._kept)

    def _check(self, *, key, kept, compute):
        """Work a kept answer out again if anything anywhere has changed since it was last worked out, and raise StaleAnswer if it differs."""
        if self._checked.get(key) == latest_revision():
            return
        again = compute()
        self._checked[key] = latest_revision()
        if again != kept.answer:
            raise StaleAnswer(ERR_STALE_ANSWER.format(key=key, kept=kept.answer, again=again))
