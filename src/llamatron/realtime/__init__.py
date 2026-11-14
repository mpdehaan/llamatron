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

"""Real-time playback: the timeline of MIDI events a rendered grid becomes, the score of a song with each clip's events from its scene's start, the player that launches scenes and clips as the follow actions say, the engine that sends the events on time, the ports they go out of, the Realtime Sender Process, which runs the engine apart from the tracker, and FluidSynth, which the tracker starts when something plays through it.

Imports composition (for the follow actions), exporters (for the note timing the exports use), grid, playback (for the render) and support.
"""
