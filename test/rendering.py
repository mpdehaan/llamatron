# llamatron: a Python language and framework for producing MIDI clips.
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

"""Helpers that tests share for turning song data or a song file into finished clips."""

import os

from llamatron.composition.song import Song
from llamatron.playback.song_renderer import SongRenderer

# How the demos in examples/ are named.
DEMO_ENDING = '_demo.yml'


def render_data(data):
    """Return the ClipGrid of finished clips that a song file's data renders into."""
    return SongRenderer(Song.from_data(data)).render()


def render_file(path):
    """Return the ClipGrid of finished clips that a song file renders into."""
    return SongRenderer(Song.read_file(path)).render()


def estimate_data(data):
    """Return how long each scene of a song file's data lasts, as SongRenderer.estimate() gives it."""
    return SongRenderer(Song.from_data(data)).estimate()


def is_demo(path):
    """Return whether a song in examples/ is a demo, which teaches one feature: its name ends in _demo."""
    return os.path.basename(path).endswith(DEMO_ENDING)
