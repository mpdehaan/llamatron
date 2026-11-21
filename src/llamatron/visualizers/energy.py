# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""How lively a visualizer mode is, from the notes it hears: a level that follows what was struck gently, never jumping, and falls away in silence."""

# The most a level or what it moves toward can be.
FULL = 1.0
RESTING = 0.0


class Energy:
    """A level from RESTING to FULL that every note heard pushes up and silence lets fall.

    A note raises what the level moves toward, by its loudness; the level follows no faster than
    its rise allows, so that nothing flashes, and what it moves toward dies away each second.
    """

    __slots__ = ('_level', '_target', '_per_note', '_rise_per_second', '_kept_per_second')

    def __init__(self, *, per_note, rise_per_second, kept_per_second):
        self._level = RESTING
        self._target = RESTING
        self._per_note = per_note
        self._rise_per_second = rise_per_second
        self._kept_per_second = kept_per_second

    def get_level(self):
        return self._level

    def strike(self, loudness):
        """Take a note heard, as loud as loudness, from nothing to FULL."""
        self._target = min(self._target + self._per_note * loudness, FULL)

    def settle(self, seconds):
        """Move the level toward what the notes struck over some seconds, and let that die away."""
        rise = self._rise_per_second * seconds
        self._level += max(-rise, min(rise, self._target - self._level))
        self._target *= self._kept_per_second ** seconds
