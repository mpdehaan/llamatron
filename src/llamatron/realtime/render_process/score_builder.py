# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Scores built off the screen's thread, so that a launch plays a score made ahead and an edit made while playing renders without
holding up the keys.

A ScoreBuilder builds one score at a time in a thread of its own. A request names what the score is built from, its key, and a
function that builds it, which works on a copy of the set made on the screen's thread, so nothing it reads changes while it renders,
and is handed the last score built, from which a score of the same song after an edit takes the scenes the edit cannot change.
A newer request replaces one not yet started, so a render that a newer edit overtook is never done. The tests make one that builds
at once, in the request, so that what they press is heard at the moment it would be.
"""

import functools
import threading

from llamatron.model.file.song_file_error import SongFileError


class Built:
    """What a request came to: the score, or the problem that kept it from being made."""

    __slots__ = ('score', 'problem')

    def __init__(self, *, score=None, problem=None):
        self.score = score
        self.problem = problem


class ScoreBuilder:
    """Builds the newest score asked for, off the screen's thread or, for the tests, at once."""

    __slots__ = ('_at_once', '_lock', '_waiting', '_built', '_wake', '_thread', '_last')

    def __init__(self, *, at_once=False):
        self._at_once = at_once
        self._lock = threading.Lock()
        # The request not yet started, as (key, build), and the last one finished, as (key, Built).
        self._waiting = None
        self._built = None
        self._wake = threading.Event()
        self._thread = None
        # The last score built, which only the thread that builds reads and replaces.
        self._last = None

    def request(self, *, key, build):
        """Ask for a score built from what key names, by build(earlier=), earlier being the last score built or None, replacing a request not yet started."""
        if self._at_once:
            self._built = (key, self._made(build))
            return
        with self._lock:
            self._waiting = (key, build)
        if self._thread is None:
            self._thread = threading.Thread(target=self._work, daemon=True)
            self._thread.start()
        self._wake.set()

    def built(self, key):
        """Return what the request for a key came to, a Built, or None while it is not done or was never asked."""
        with self._lock:
            if self._built is not None and self._built[0] == key:
                return self._built[1]
        return None

    def _work(self):
        while True:
            self._wake.wait()
            with self._lock:
                waiting = self._waiting
                self._waiting = None
                self._wake.clear()
            if waiting is None:
                continue
            key, build = waiting
            result = self._made(build)
            with self._lock:
                self._built = (key, result)


    def _made(self, build):
        """Return what a request came to, handing it the last score built, and keep the score it made for the next."""
        result = made(functools.partial(build, earlier=self._last))
        if result.score is not None:
            self._last = result.score
        return result


def made(build):
    """Return what building a score came to: the score, or the problem of a song that cannot be played."""
    try:
        return Built(score=build())
    except (SongFileError, ValueError) as problem:
        return Built(problem=problem)
