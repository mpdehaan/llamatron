# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""The passes a render has played whose notes follow from a key alone, kept so that a pass played again is not worked out again.

Most passes of most songs play a pattern no step of which reads or changes anything that carries from pass to pass: no register,
no draw, no statement, no probability under 100 and no grab, in a clip that hears no drift and binds no register to its velocity.
Such a pass is decided by its pattern and its revision, the steps in the order they play, the step size, the pattern's length and
what the clip's player settles notes by (PatternPlayer.pass_context), so those are its key, and a render remembers it under them.
A machine-tight kick plays the same pass hundreds of times in a song: across the examples, four passes in five came out like an
earlier one. A render in the render process hands its memory on to the next render of the song, so an edit to one pattern leaves
every other pattern's passes remembered. Nothing is let go: memory is cheap beside speed, and a pass kept under a pattern's older
revision is never found again, since every edit gives the pattern a new one.

It also holds what each pattern's player gathers of a pattern's steps (pattern_player.PlayedPattern), once a render rather than once
a clip, which a render cannot change but the next may, since the song's draws can change between renders.

While the tests check every remembered answer (Memory.checks_by_default), a pass found in the memory is worked out again and
compared, and a difference raises StaleAnswer, so a key that leaves out something a pass reads fails the tests.
"""

from llamatron.caching.memory import Memory, stale_answer


class PassMemory:
    """The passes the renders of a song have played, by key, and what this render has gathered of each pattern's steps."""

    __slots__ = ('_cached', '_played_patterns', '_checking')

    def __init__(self, *, earlier=None):
        """earlier is the PassMemory of the render before, of the same song, whose passes this one goes on keeping, or None."""
        self._cached = {} if earlier is None else earlier.get_kept()
        self._played_patterns = {}
        self._checking = Memory.checks_by_default()

    def get_kept(self):
        """Return the passes kept, by key, for the next render to take from."""
        return self._cached

    def get_played_patterns(self):
        """Return what this render's players have gathered of each pattern's steps, by the pattern's name, for them to share."""
        return self._played_patterns

    def is_checking(self):
        return self._checking

    def recall(self, key):
        """Return a copy of the pass kept under a key, or None; the caller may change the copy."""
        kept = self._cached.get(key)
        return None if kept is None else kept.copied()

    def keep(self, *, key, played, remembered):
        """Keep a pass played under its key, a copy, so that what the caller changes of it is not kept; remembered is the pass the
        memory gave for the key while checking, held to the pass worked out again."""
        if remembered is not None and fingerprint(remembered) != fingerprint(played):
            raise stale_answer(key=key, cached=fingerprint(remembered), again=fingerprint(played))
        self._cached[key] = played.copied()


def fingerprint(played):
    """Return what a pass plays, as values that compare: its sounds, its CC values, its ties, its length, its keyswitches and whether
    it ended its clip."""
    clip = played.clip
    return (tuple(clip.get_sounds()), repr(clip.get_controls()), played.tied_from_before, played.length, repr(played.keyswitches), played.done)
