# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A method's answer cached on its object until what the answer was worked out from changes.

A page of the song wizard asks the same questions of the choices many times a key, and some answers, such as the style
template laid over by the subgenre, take long to work out. A method written under @cached_while(key_of) works its answer out
once and returns the same object again while key_of(self) gives an equal key, so that the second call costs the key alone.
The key holds everything the answer depends on; a key of None caches nothing. The answer is shared between callers, so a cached
method returns something no caller changes: a tuple, a string, or a dictionary every caller only reads. The object caches its
answers in a dictionary it names CACHED, declared in its __slots__ and made empty in its constructor, and forget_cached drops them.

A method given said, what an answer says as a value that compares, has its cached answer worked out again while the tests check
every remembered answer (Memory.check_every_answer), so that a key that leaves something out fails a test, as a Memory's does:
at the first call after anything in the set changed or the tests pressed a key (Memory.check_round), since a page asks the same
answer dozens of times a key and working each out again every time made the tracker's tests several times slower. cached_for_life caches a method's answers for as long as the object lives, by its arguments alone, for an
object nothing changes once it is made.
"""

import functools

from llamatron.caching.memory import Memory, stale_answer

# The attribute an object caches its answers in, by the method's name.
CACHED = '_cached'
# What an answer not yet worked out is, apart from every answer, None included.
MISSING = object()
# The key of an object whose cached answers hold for as long as it lives.
FOR_LIFE = True


def cached_while(key_of, *, said=None):
    """Decorate a method so that its answer for each set of arguments is cached while key_of(self) gives an equal key: the
    arguments, by keyword, are part of what an answer is cached by, and must be hashable. said, where given, turns an answer
    into what the tests compare with the answer worked out again."""
    def decorate(method):
        name = method.__name__

        @functools.wraps(method)
        def cached(self, **named):
            key = key_of(self)
            if key is None:
                return method(self, **named)
            answers = getattr(self, CACHED)
            held = answers.get(name)
            if held is None or held[0] != key:
                # The key, the answers by the keywords asked with, and the check round each answer was last checked in.
                held = (key, {}, {})
                answers[name] = held
            # The keywords asked with, in any order, as one key.
            asked = frozendict(named)
            found = held[1].get(asked, MISSING)
            if found is MISSING:
                found = method(self, **named)
                held[1][asked] = found
            elif said is not None and Memory.checks_by_default() and _due_for_check(rounds=held[2], asked=asked):
                again = said(method(self, **named))
                if again != said(found):
                    raise stale_answer(key=(name, asked), cached=said(found), again=again)
            return found
        return cached
    return decorate


def as_is(answer):
    """Return an answer as it is, for cached_while's said where the answer is plain data that compares as it stands."""
    return answer


def cached_for_life(method):
    """Decorate a method of an object nothing changes once it is made, so that its answer for each set of arguments is cached
    for as long as the object lives."""
    return cached_while(lambda holder: FOR_LIFE)(method)


def forget_cached(holder):
    """Drop every answer an object has cached, for an object that knows it has changed in a way no key shows."""
    getattr(holder, CACHED).clear()


def _due_for_check(*, rounds, asked):
    """Return whether a cached answer is to be checked now, the first time it is asked in this check round (Memory.check_round),
    noting that it was."""
    round_now = Memory.check_round()
    if rounds.get(asked) == round_now:
        return False
    rounds[asked] = round_now
    return True
