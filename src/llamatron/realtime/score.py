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

"""The score: a song rendered for real-time playback, each clip's events counted from its scene's start.

The timeline lays a whole song end to end, which is what playing it from the top needs. The player
also launches one scene or one clip at a moment of its own choosing, so it needs each clip's events
relative to the scene they belong to, and it needs what the song says about launching: how long
each scene lasts, which clips loop, each clip's follow action and whether each scene launches
together. The score is all of that, read once from the song as it is when something is launched,
so that the player never asks the composition objects anything while it runs. A scene that
repeats is written out once per repeat by the renderer, as the export writes it, and the score
keeps those rows together as one scene, so that launching a scene plays all of its repeats.
"""

import bisect
import math
from typing import NamedTuple

from llamatron.composition.file_format import FollowAction
from llamatron.playback.song_renderer import SongRenderer
from llamatron.realtime.timeline import NOTE_OFF, NOTE_ON, Tag, clip_timeline, seconds_per_whole, sort_key
from llamatron.support.rational import Rational

NO_PLAY = 0
START_OF_SCENE = 0.0
# How close to a pass's start a moment may be and still count as that start, against rounding in the seconds.
PASS_TOLERANCE = 1e-9
FIRST_SCENE = 0


FIRST_ROW = 0


class Row(NamedTuple):
    """One written-out repeat of a scene: when it starts within the scene, in seconds, how long it lasts, and the seconds a whole note takes at its tempo."""

    start: float
    seconds: float
    whole: float


class Sounding(NamedTuple):
    """When one note of a clip starts and ends, in seconds from the scene's start, for the lights."""

    on: float
    off: float


class Heard(NamedTuple):
    """One note of a clip as the visualizer hears it: when it starts and ends, in seconds from the scene's start, its MIDI number and its velocity."""

    on: float
    off: float
    number: int
    velocity: int


class Score:
    """What the player knows about a song: each scene's length and launch settings, and each clip's events from its scene's start."""

    __slots__ = ('_tracks', '_scene_seconds', '_scene_starts', '_rows', '_events', '_loops', '_follow_actions', '_launches_together', '_repeats', '_clip_seconds', '_sounding', '_heard', '_bar')

    def __init__(self, *, song, routes, seed=None):
        """Render a song and read it into the score. routes maps a track's name to its Route, and a track with none has no events, since it has nothing to play through."""
        renderer = SongRenderer(song, seed=seed, looping_scenes_go_round=True)
        grid = renderer.render()
        setlist = song.get_setlist()
        self._tracks = list(song.get_track_names())
        # How long a bar is in whole notes, by the song's time signature, which a launch by hand waits for.
        self._bar = float(song.get_time_signature().bar_length())
        rows = grid.get_rows()
        written = renderer.get_scenes()
        self._scene_seconds = []
        self._scene_starts = []
        self._rows = []
        self._events = {}
        self._loops = {}
        self._follow_actions = {}
        self._launches_together = []
        self._repeats = {}
        self._clip_seconds = {}
        self._sounding = {}
        # Each clip's notes with their numbers and velocities, the times they start and the longest of them, worked out the first time the visualizer asks.
        self._heard = {}
        song_start = START_OF_SCENE
        for index, scene in enumerate(song.get_scenes()):
            scene_rows = [place for place, written_scene in enumerate(written) if written_scene.get_scene() is scene]
            self._launches_together.append(scene.launches_together())
            self._scene_starts.append(song_start)
            scene_start = START_OF_SCENE
            self._rows.append([])
            for track in self._tracks:
                self._events[(index, track)] = []
                clip_slot = scene.get_clip_slot(track) if scene.has_clip_slot(track) else None
                self._loops[(index, track)] = clip_slot is not None and clip_slot.loops()
                # An empty slot is done when its scene is done and counts as "With Scene", so the track below starts as the export has it start.
                self._follow_actions[(index, track)] = FollowAction.WITH_SCENE if clip_slot is None else setlist.follow_action_of(clip_slot)
                self._repeats[(index, track)] = None if clip_slot is None or clip_slot.loops() else clip_slot.get_repeat()
            for place in scene_rows:
                row = rows[place]
                whole = seconds_per_whole(grid.tempo_at(row))
                row_seconds = float(grid.row_length(row)) * whole
                self._rows[index].append(Row(scene_start, row_seconds, whole))
                for track in grid.get_columns():
                    name = track.get_name()
                    clip = grid.get_clip(row=row, column=track)
                    route = routes.get(name)
                    if clip is None:
                        continue
                    self._clip_seconds[(index, len(self._rows[index]) - 1, name)] = float(clip.total_length()) * whole
                    if route is None or track.get_mute():
                        continue
                    self._events[(index, name)].extend(clip_timeline(clip=clip, scale=grid.scale_at(row=row, column=track), route=route, tag=Tag(index, name),
                                                                     scene_start=Rational(0), scene_seconds=scene_start, whole=whole))
                scene_start += row_seconds
            for track in self._tracks:
                self._events[(index, track)].sort(key=sort_key)
            self._scene_seconds.append(scene_start)
            song_start += scene_start

    def tracks(self):
        return list(self._tracks)

    def scene_count(self):
        return len(self._scene_seconds)

    def scene_seconds(self, scene):
        """Return how long a scene lasts, all of its repeats together, in seconds."""
        return self._scene_seconds[scene]

    def scene_start(self, scene):
        """Return when a scene starts when the song plays from the top, in seconds, for the clock."""
        return self._scene_starts[scene]

    def song_seconds(self):
        return sum(self._scene_seconds)

    def launches_together(self, scene):
        return self._launches_together[scene]

    def follow_action(self, *, scene, track):
        return self._follow_actions[(scene, track)]

    def loops(self, *, scene, track):
        return self._loops[(scene, track)]

    def clip_end(self, *, scene, track):
        """Return when a clip's own repeats end, in seconds from its scene's start, on the scene's first play, or None for a looping clip or an empty slot."""
        if self._loops[(scene, track)]:
            return None
        return self._clip_seconds.get((scene, FIRST_ROW, track))

    def events(self, *, scene, track):
        """Return a clip's events in time order, counted from its scene's start, tagged with play 0."""
        return list(self._events[(scene, track)])

    def played_events(self, *, scene, track, start, play):
        """Return a clip's events moved to start at a moment, tagged with the number of this play of the clip."""
        tag = Tag(scene, track, play)
        return [event._replace(seconds=start + event.seconds, tag=tag) for event in self._events[(scene, track)]]

    def sounding(self, *, scene, track):
        """Return when each note of a clip sounds, from the scene's start, in the order the notes start."""
        key = (scene, track)
        if key not in self._sounding:
            self._sounding[key] = self._note_spans(self._events[key])
        return self._sounding[key]

    def heard(self, *, scene, track, since, until):
        """Return the notes of a clip the visualizer hears between two moments counted from the scene's start: those that started after since and by until, and those still sounding at until, each a Heard.

        Only notes that have started are heard, so the visualizer never knows what is coming.
        """
        key = (scene, track)
        if key not in self._heard:
            notes = self._heard_notes(self._events[key])
            self._heard[key] = (notes, [note.on for note in notes], max((note.off - note.on for note in notes), default=0.0))
        notes, starts, longest = self._heard[key]
        last = bisect.bisect_right(starts, until)
        first_started = bisect.bisect_right(starts, since)
        earliest_held = bisect.bisect_left(starts, until - longest)
        started = notes[first_started:last]
        held = [note for note in notes[min(earliest_held, first_started):first_started] if note.off > until]
        return started, held

    @staticmethod
    def _heard_notes(events):
        """Return each note on with its note off, number and velocity, in the order the notes start."""
        notes = []
        open_notes = {}
        for event in events:
            key = (event.port, event.channel, event.number)
            if event.kind == NOTE_ON:
                open_notes[key] = (event.seconds, event.value)
            elif event.kind == NOTE_OFF and key in open_notes:
                on, velocity = open_notes.pop(key)
                notes.append(Heard(on, event.seconds, event.number, velocity))
        notes.sort()
        return notes

    def is_sounding(self, *, scene, track, elapsed):
        """Return whether a note of a clip sounds at a moment counted from the scene's start."""
        for span in self.sounding(scene=scene, track=track):
            if span.on > elapsed:
                return False
            if span.off > elapsed:
                return True
        return False

    def events_from(self, *, scene, track, start, tag, after):
        """Return a clip's events played from a moment, start, tagged with tag, leaving out those before after and the note offs of notes that started before it, for a clip whose notes change while it plays."""
        events = []
        started_before = set()
        for event in self._events[(scene, track)]:
            seconds = start + event.seconds
            key = (event.port, event.channel, event.number)
            if seconds < after:
                if event.kind == NOTE_ON:
                    started_before.add(key)
                elif event.kind == NOTE_OFF:
                    started_before.discard(key)
                continue
            if event.kind == NOTE_OFF and key in started_before:
                started_before.discard(key)
                continue
            events.append(event._replace(seconds=seconds, tag=tag))
        return events

    def next_pass_start(self, *, scene, track, elapsed):
        """Return when a clip next starts a pass of its pattern, in seconds from its scene's start, at or after a moment, or None for a slot with no clip."""
        place, row = self.row_at(scene=scene, elapsed=elapsed)
        clip_seconds = self._clip_seconds.get((scene, place, track))
        if not clip_seconds:
            return None
        repeat = self._repeats[(scene, track)]
        pass_seconds = clip_seconds / repeat if repeat else clip_seconds
        passes = math.ceil(max(elapsed - row.start, START_OF_SCENE) / pass_seconds - PASS_TOLERANCE)
        at = row.start + passes * pass_seconds
        return min(at, row.start + row.seconds)

    def whole_at(self, *, scene, elapsed):
        """Return how far into a scene a moment is in whole notes, counting each of its rows at its own tempo, so that a moment keeps its place in the music when the tempo changes."""
        whole = 0.0
        for row in self._rows[scene]:
            if elapsed <= row.start + row.seconds or row is self._rows[scene][-1]:
                return whole + max(elapsed - row.start, START_OF_SCENE) / row.whole
            whole += row.seconds / row.whole
        return whole

    def seconds_at(self, *, scene, whole):
        """Return the moment in seconds from a scene's start that is so many whole notes into it, the other way round from whole_at."""
        counted = 0.0
        for row in self._rows[scene]:
            row_whole = row.seconds / row.whole
            if whole <= counted + row_whole or row is self._rows[scene][-1]:
                return row.start + (whole - counted) * row.whole
            counted += row_whole
        return START_OF_SCENE

    def sounding_across(self, *, scene, track, elapsed):
        """Return the (port, channel, number) of every note of a clip that has started and not ended at a moment, for cutting the clip there."""
        notes = set()
        for event in self._events[(scene, track)]:
            if event.seconds >= elapsed:
                break
            key = (event.port, event.channel, event.number)
            if event.kind == NOTE_ON:
                notes.add(key)
            elif event.kind == NOTE_OFF:
                notes.discard(key)
        return sorted(notes)

    def bar_seconds(self, *, scene, elapsed):
        """Return how long a bar of the song's time signature lasts, in seconds, at a moment of a scene counted from the scene's start, at that row's tempo."""
        _, row = self.row_at(scene=scene, elapsed=elapsed)
        return self._bar * row.whole

    def row_at(self, *, scene, elapsed):
        """Return the scene's row playing at a moment counted from the scene's start, and its place among the scene's rows."""
        rows = self._rows[scene]
        place = max(bisect.bisect_right([row.start for row in rows], elapsed) - 1, 0)
        return place, rows[place]

    def clip_elapsed(self, *, scene, track, elapsed):
        """Return how far into a clip's play a moment counted from the scene's start is, in seconds, for the clip's bar on Arrange.

        The clip's play is its play in the scene's row at that moment, all of the clip's repeats
        together, as its bar on Arrange measures it. A looping clip's play is as long as the
        scene's row and starts over when it ends, since the player loops it until something else
        is launched on its track. None for a slot with no clip.
        """
        place, row = self.row_at(scene=scene, elapsed=elapsed)
        clip_seconds = self._clip_seconds.get((scene, place, track))
        if not clip_seconds:
            return None
        into_row = max(elapsed - row.start, 0.0)
        if self._loops[(scene, track)]:
            return into_row % clip_seconds
        return min(into_row, clip_seconds)

    def repeats_left(self, *, scene, track, elapsed):
        """Return how many of a clip's repeats are still to play at a moment counted from the scene's start, or None for a clip that loops or has none."""
        repeat = self._repeats[(scene, track)]
        if repeat is None:
            return None
        place, row = self.row_at(scene=scene, elapsed=elapsed)
        clip_seconds = self._clip_seconds.get((scene, place, track))
        if not clip_seconds:
            return None
        played = int((elapsed - row.start) // (clip_seconds / repeat))
        return max(repeat - played, NO_PLAY)

    @staticmethod
    def _note_spans(events):
        """Return when each note on's note sounds until its note off, in the order the notes start."""
        spans = []
        open_notes = {}
        for event in events:
            key = (event.port, event.channel, event.number)
            if event.kind == NOTE_ON:
                open_notes[key] = event.seconds
            elif event.kind == NOTE_OFF and key in open_notes:
                spans.append(Sounding(open_notes.pop(key), event.seconds))
        spans.sort()
        return spans
