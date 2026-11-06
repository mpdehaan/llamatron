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

"""The CC values of a clip that morphs into another pattern."""

from dataclasses import replace


def morph_controls(source, target, start, end):
    """Return the CC values of a morph: the target's from start to end, and the source's elsewhere.

    Each side's values carry across the edges, so a lane holds what it would hold there.
    """
    def in_effect(clip, time):
        latest = {}
        for item in clip.controls:
            if item.time <= time:
                latest[item.number] = item
        return latest

    if end <= start:
        return list(source.controls)
    result = [item for item in source.controls if item.time < start]
    result += [replace(item, time=start) for item in in_effect(target, start).values() if item.time < start]
    result += [item for item in target.controls if start <= item.time < end]
    if end < source.total_length():
        result += [replace(item, time=end) for item in in_effect(source, end).values() if item.time < end]
        result += [item for item in source.controls if item.time >= end]
    return result
