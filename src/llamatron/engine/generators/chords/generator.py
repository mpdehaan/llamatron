# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What a Chords generator does to a clip's notes: its Mode's generator, a progression or the chords another track plays, and
then its voicing, each run on what the one before made."""

from llamatron.engine.generators.base import ClipGenerator


class ChordsGenerator(ClipGenerator):
    """Runs a Chords generator's parts in order on a clip: what its Mode makes of the notes, then its voicing; a part it lacks is
    skipped, and with neither the clip's notes pass unchanged. The state the next clip carries on from is its voicing's."""

    __slots__ = ('_parts', '_voicing')

    def __init__(self, *, moving, voicing):
        """moving is the generator its Mode runs, or None in Voicing mode; voicing is its VoiceLeading, or None with voice leading off."""
        self._parts = []
        if moving is not None:
            self._parts.append(moving)
        if voicing is not None:
            self._parts.append(voicing)
        self._voicing = voicing

    def generate(self, clip):
        if not self._parts:
            return super().generate(clip)
        for part in self._parts:
            clip = part.generate(clip)
        return clip

    def end_state(self):
        if self._voicing is None:
            return None
        return self._voicing.end_state()

    def _generate(self, clip):
        return clip.resolved_sounds(), clip.get_length()
