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

"""What a track has played, for another track's grab steps to take notes from."""

from llamatron.renderers.timing import timed_events


class GrabSource:
    """The notes a finished clip starts, by when they start, like the Cirklon's note grab."""

    def __init__(self, clip):
        self._onsets = _notes_by_start(clip)
        self._times = sorted(self._onsets)

    def note_at(self, time):
        """Return the MIDI number of the note most recently started at or before a time, or None.

        A chord gives its lowest note. Chords are built upward from the root, so that's the root
        for now, but inversions would need to change this.
        """
        latest = self._latest_start_by(time)
        return None if latest is None else min(self._onsets[latest])

    def _latest_start_by(self, time):
        """Return the latest time a note starts at or before a time, or None if none has started."""
        started = [moment for moment in self._times if moment <= time]
        return started[-1] if started else None


def _notes_by_start(clip):
    """Return the MIDI numbers of the notes a clip plays, grouped by when they start."""
    events, _ = timed_events(clip, clip.scale)
    notes = {}
    for start, _, number, _ in events:
        notes.setdefault(start, set()).add(number)
    return notes
