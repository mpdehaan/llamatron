# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Where a built-in generator of the current song is: a track's, or a clip's on a track in a scene, by its kind."""

from typing import NamedTuple

# The scene a track's own built-in is in: none, since a track's built-ins serve every scene.
OF_THE_TRACK = None


class BuiltInPlace(NamedTuple):
    """A built-in generator of the current song: the track it is on, the place of the scene of the clip holding it, or
    OF_THE_TRACK for the track's own, and its kind, the name of its plugin."""

    track: str
    scene: object
    kind: str

    def is_the_tracks(self):
        """Return whether the built-in is the track's own, which serves every clip on it, rather than one clip's."""
        return self.scene is OF_THE_TRACK
