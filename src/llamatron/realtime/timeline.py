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

"""The timeline: a rendered grid as one time-ordered list of MIDI events across every track, with absolute times.

Real-time playback renders a song the way the exporters do and then only schedules: everything that makes
the music, probability, directions, arps, registers, grabs, morphs, ties, glides and grooves, has happened
in the grid, so the timeline is read from the same note timing the MIDI export writes (exporters/timing.py),
and test/test_realtime.py holds it to the export, tick for tick. Each event carries the whole-note time it
came from, for that comparison, the seconds it plays at, the port and channel of its track's route, and a
tag naming the scene and track it belongs to, so that one clip's events can be dropped or stopped.
"""

from typing import NamedTuple

from llamatron.exporters.timing import control_events, timed_events
from llamatron.support.rational import Rational

# What a tempo counts, quarter notes per minute, and the seconds in a minute.
QUARTERS_PER_WHOLE = 4
SECONDS_PER_MINUTE = 60
# The three kinds of event the timeline holds, as the status byte without its channel.
NOTE_ON = 0x90
NOTE_OFF = 0x80
CONTROL_CHANGE = 0xB0
# A program change, which only FluidSynth's routes send, at the start of each clip, choosing the track's General MIDI sound.
PROGRAM_CHANGE = 0xC0
CHANNEL_MASK = 0x0F
KIND_MASK = 0xF0
NO_VELOCITY = 0
# Where a sound event's order is settled when two fall at the same instant: note offs first, so that a repeated pitch is never cut by the off of the note before.
OFFS_FIRST = 0
ONS_AFTER = 1
FIRST_AT_AN_INSTANT = (NOTE_OFF, PROGRAM_CHANGE)


class Route(NamedTuple):
    """Where a track's events go: the name of an output port and a MIDI channel, from 0, and the program to choose first, from 0, or None to send none."""

    port: str
    channel: int
    program: int = None


class Tag(NamedTuple):
    """Which clip an event belongs to: the scene's place in the song, from 0, the track's name, and which play of that clip, since the player can launch one clip again and again."""

    scene: int
    track: str
    play: int = 0


class Playing(NamedTuple):
    """One event of the timeline: when, in whole notes from the song's start and in seconds, where, what, and whose."""

    whole: Rational
    seconds: float
    port: str
    channel: int
    kind: int
    number: int
    value: int
    tag: Tag

    def data(self):
        """Return the event's bytes: two for a program change, which has no value, and three for the rest."""
        if self.kind == PROGRAM_CHANGE:
            return [self.kind | self.channel, self.number]
        return [self.kind | self.channel, self.number, self.value]


def seconds_per_whole(tempo):
    """Return how long a whole note lasts, in seconds, at a tempo in quarter notes per minute."""
    return QUARTERS_PER_WHOLE * SECONDS_PER_MINUTE / tempo


def sort_key(event):
    """Return what the timeline is ordered by: time, with note offs and program changes before note ons at the same instant."""
    return (event.whole, OFFS_FIRST if event.kind in FIRST_AT_AN_INSTANT else ONS_AFTER)


def song_timeline(*, grid, routes):
    """Return a rendered grid's events in time order, the scenes laid end to end as the MIDI export lays them.

    routes maps a track's name to its Route, and a track with no route is left out, since a track with
    no instrument has nothing to play through. Muted tracks are left out too, as the export leaves them.
    """
    events = []
    scene_seconds = 0.0
    for place, (scene, scene_start) in enumerate(zip(grid.get_rows(), grid.row_starts())):
        whole = seconds_per_whole(grid.tempo_at(scene))
        for track in grid.get_columns():
            route = routes.get(track.get_name())
            clip = grid.get_clip(row=scene, column=track)
            if route is None or clip is None or track.get_mute():
                continue
            tag = Tag(place, track.get_name())
            events.extend(clip_timeline(clip=clip, scale=grid.scale_at(row=scene, column=track), route=route, tag=tag,
                                        scene_start=scene_start, scene_seconds=scene_seconds, whole=whole))
        scene_seconds += float(grid.row_length(scene)) * whole
    return sorted(events, key=sort_key)


def clip_timeline(*, clip, scale, route, tag, scene_start, scene_seconds, whole):
    """Return one clip's notes and CC values as events, placed at its scene's start, in no particular order, after the route's program change when it has one."""
    events = []

    def at(time, kind, number, value):
        return Playing(scene_start + time, scene_seconds + float(time) * whole, route.port, route.channel, kind, number, value, tag)
    if route.program is not None:
        events.append(at(Rational(0), PROGRAM_CHANGE, route.program, NO_VELOCITY))
    notes, clip_length = timed_events(clip=clip, scale=scale)
    for note in notes:
        if note.end > note.start:
            events.append(at(note.start, NOTE_ON, note.midi_number, note.velocity))
            events.append(at(note.end, NOTE_OFF, note.midi_number, NO_VELOCITY))
    for control in control_events(clip=clip, length=clip_length):
        events.append(at(control.time, CONTROL_CHANGE, control.number, control.value))
    return events
