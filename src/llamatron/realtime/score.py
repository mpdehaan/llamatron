# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The score: a song rendered for real-time playback, each clip's events counted from its scene's start.

The timeline lays a whole song end to end, which is what playing it from the top needs. The player
also launches one scene or one clip at a moment of its own choosing, so it needs each clip's events
relative to the scene they belong to, and it needs what the song says about launching: how long
each scene lasts, which clips loop, each clip's follow action and whether each scene launches
together. The score is all of that, read once from the song as it is when something is launched,
so that the player never asks the composition objects anything while it runs. A scene that
repeats is written out once per repeat by the Realizer, as the export writes it, and the score
keeps those rows together as one scene, so that launching a scene plays all of its repeats.
"""

import bisect
import math
from typing import NamedTuple

from llamatron.caching import memory
from llamatron.engine.realizer.song_realizer import SongRealizer
from llamatron.math.rational import Rational
from llamatron.model.schema.file_format import FollowAction
from llamatron.realtime import score_records, timeline
from llamatron.realtime.clip_notes import ClipNotes
from llamatron.realtime.timeline import clip_timeline, ClipTag, sort_key

NO_PLAY = 0
START_OF_SCENE = 0.0
# How close to a pass's start a moment may be and still count as that start, against rounding in the seconds.
PASS_TOLERANCE = 1e-9
FIRST_SCENE = 0


FIRST_ROW = 0


# Where the draws stand before any has drawn.
NO_DRAW_PLACES = {}


def first_of(moment):
    """Return when a moment of the draws' lights happens, the first of its two parts."""
    return moment[0]

class ScoreRow(NamedTuple):
    """One written-out repeat of a scene: when it starts within the scene, in seconds, how long it lasts, and its clock, which keeps its tempo and every change of tempo inside it."""

    start: float
    seconds: float
    clock: object


class Keeping(NamedTuple):
    """What a score keeps from and lets a later one keep: the set's data its song was copied from, and the earlier score it may
    take scenes and clips from, either of which may be None."""

    data: object
    earlier: object


# A score made to be kept from by none and keeping nothing.
NOT_KEEPING = Keeping(None, None)


class Score:
    """What the player knows about a song: each scene's length and launch settings, and each clip's events from its scene's start."""

    __slots__ = ('_tracks', '_scene_seconds', '_scene_starts', '_rows', '_events', '_loops', '_follow_actions', '_launches_together', '_repeats', '_clip_seconds', '_notes', '_bar', '_draw_lights', '_realizer', '_routes', '_taken_tracks')

    def __init__(self, *, song, routes, seed=None, keeping=None, takes=None):
        """Render a song and read it into the score. routes maps a track's name to its Route, and a track with none has no events, since it has nothing to play through.

        keeping, a Keeping, holds the set's data the song was copied from (Setlist.kept_data), which lets a later score take from
        this one the scenes an edit cannot change, and the earlier score, of the same seed and routes, that gives this one those
        scenes (score_records.py).
        takes gives clips new random choices, by (the scene's place in the song, the track), as SongRealizer's does.
        """
        data, earlier = keeping or NOT_KEEPING
        if earlier is not None and earlier._routes != routes:
            earlier = None
        realizer = SongRealizer(song, seed=seed, looping_scenes_go_round=True, data=data, takes=takes)
        grid = realizer.render(after=None if earlier is None else earlier._realizer)
        reused = realizer.get_reused_scene_count()
        self._realizer = realizer
        # The tracks of each scene whose events were taken from the earlier score, clip by clip.
        self._taken_tracks = []
        self._routes = dict(routes)
        setlist = song.get_setlist()
        self._tracks = list(song.get_track_names())
        # How long a bar is in whole notes, by the song's time signature, which a launch by hand waits for.
        self._bar = float(song.get_time_signature().bar_length())
        rows = grid.get_rows()
        written = realizer.get_scenes()
        self._scene_seconds = []
        self._scene_starts = []
        self._rows = []
        self._events = {}
        self._loops = {}
        self._follow_actions = {}
        self._launches_together = []
        self._repeats = {}
        self._clip_seconds = {}
        # Each clip's notes as they sound, made the first time the lights, the visualizer or a cut asks.
        self._notes = {}
        # Each scene's moments at which a draw drew, in seconds from the scene's start, with where every draw then stood.
        self._draw_lights = []
        song_start = START_OF_SCENE
        for index, scene in enumerate(song.get_scenes()):
            scene_rows = [place for place, written_scene in enumerate(written) if written_scene.get_scene() is scene]
            self._launches_together.append(scene.launches_together())
            self._scene_starts.append(song_start)
            scene_start = START_OF_SCENE
            self._rows.append([])
            self._draw_lights.append([])
            for track in self._tracks:
                self._events[(index, track)] = []
                clip_slot = scene.get_clip_slot(track) if scene.has_clip_slot(track) else None
                # A looping clip that a step of its pattern can stop is a clip that ends, as an export has it.
                self._loops[(index, track)] = clip_slot is not None and realizer.fills_its_scene(scene=scene, track=track)
                # An empty slot is done when its scene is done and counts as "With Scene", so the track below starts as the export has it start.
                self._follow_actions[(index, track)] = FollowAction.WITH_SCENE if clip_slot is None else setlist.follow_action_of(clip_slot)
                self._repeats[(index, track)] = None if clip_slot is None or clip_slot.loops() else clip_slot.get_repeat()
            if scene_rows and scene_rows[-1] < reused:
                self._scene_seconds.append(score_records.take_scene(into=self._records(), earlier=earlier._records(), index=index, tracks=self._tracks))
                self._taken_tracks.append(set())
                song_start += self._scene_seconds[-1]
                continue
            # The tracks whose clips the render took from the earlier score's in every repeat of the scene, whose events are taken too.
            kept = set() if earlier is None else realizer.kept_tracks([written[place] for place in scene_rows])
            self._taken_tracks.append(kept)
            for place in scene_rows:
                row = rows[place]
                clock = grid.clock_of(row)
                row_seconds = clock.seconds_at(grid.row_length(row))
                self._rows[index].append(ScoreRow(scene_start, row_seconds, clock))
                if song.uses_draws():
                    self._draw_lights[index] += [(scene_start + clock.seconds_at(time), places) for time, places in realizer.get_timeline(written[place]).get_draw_moments()]
                for track in grid.get_columns():
                    name = track.get_name()
                    clip = grid.get_clip(row=row, column=track)
                    route = routes.get(name)
                    if clip is None:
                        continue
                    self._clip_seconds[(index, len(self._rows[index]) - 1, name)] = clock.seconds_at(clip.total_length())
                    if route is None or track.get_mute() or name in kept:
                        continue
                    # Each row's events are put in time order by where they fall in the row, and the rows follow one another, so
                    # that a clip's events are in time order across every repeat of its scene, as the player reads them.
                    self._events[(index, name)].extend(sorted(clip_timeline(clip=clip, scale=grid.scale_at(row=row, column=track), route=route, tag=ClipTag(index, name),
                                                                            scene_start=Rational(0), scene_seconds=scene_start, clock=clock), key=sort_key))
                scene_start += row_seconds
            for track in kept:
                self._events[(index, track)] = earlier._events[(index, track)]
            self._scene_seconds.append(scene_start)
            song_start += scene_start
        if realizer.has_taken_anything() and memory.Memory.checks_by_default():
            score_records.check(kept=self._records(), again=Score(song=song, routes=routes, seed=seed, takes=takes)._records())

    def get_reused_scene_count(self):
        """Return how many written scenes, from the first, the score took from an earlier one rather than rendering them."""
        return self._realizer.get_reused_scene_count()

    def get_taken_tracks(self, scene):
        """Return the tracks whose events in a scene were taken from the earlier score, their clips kept in every repeat; empty for a scene taken whole."""
        return self._taken_tracks[scene]

    def get_kept_clip_count(self):
        """Return how many clips after the scenes taken whole the score took from an earlier one, track by track."""
        return self._realizer.get_kept_clip_count()

    def _records(self):
        return score_records.Records(events=self._events, scene_seconds=self._scene_seconds, clip_seconds=self._clip_seconds, draw_lights=self._draw_lights, rows=self._rows)

    def draw_places_at(self, *, scene, seconds):
        """Return where every draw stood a number of seconds into a scene, by name, the place of each one's last slot: none before the scene's first draw."""
        moments = self._draw_lights[scene]
        found = bisect.bisect_right(moments, seconds, key=first_of)
        return moments[found - 1][1] if found else NO_DRAW_PLACES

    def get_tracks(self):
        return list(self._tracks)

    def scene_count(self):
        return len(self._scene_seconds)

    def get_scene_seconds(self, scene):
        """Return how long a scene lasts, all of its repeats together, in seconds."""
        return self._scene_seconds[scene]

    def get_scene_start(self, scene):
        """Return when a scene starts when the song plays from the top, in seconds, for the clock."""
        return self._scene_starts[scene]

    def song_seconds(self):
        return sum(self._scene_seconds)

    def launches_together(self, scene):
        return self._launches_together[scene]

    def get_follow_action(self, *, scene, track):
        return self._follow_actions[(scene, track)]

    def loops(self, *, scene, track):
        return self._loops[(scene, track)]

    def clip_end(self, *, scene, track):
        """Return when a clip's own repeats end, in seconds from its scene's start, on the scene's first play, or None for a looping clip or an empty slot."""
        if self._loops[(scene, track)]:
            return None
        return self._clip_seconds.get((scene, FIRST_ROW, track))

    def get_events(self, *, scene, track):
        """Return a clip's events in time order, counted from its scene's start, tagged with play 0."""
        return list(self._events[(scene, track)])

    def clip_events(self, *, scene, track):
        """Return a clip's events, each at its seconds from the scene's start and untagged, which a play places and tags as it sends them."""
        return self._events[(scene, track)]

    def clip_notes(self, *, scene, track):
        """Return a clip's notes as they sound, a ClipNotes, for the lights, the visualizer and a cut."""
        key = (scene, track)
        if key not in self._notes:
            self._notes[key] = ClipNotes(self._events[key])
        return self._notes[key]

    def events_from(self, *, scene, track, start, tag, after):
        """Return a clip's events played from a moment, start, tagged with tag, leaving out those before after and the note offs of notes that started before it, for a clip whose notes change while it plays."""
        events = []
        started_before = set()
        for event in self._events[(scene, track)]:
            seconds = start + event.seconds
            key = (event.port, event.channel, event.number)
            if seconds < after:
                if event.kind == timeline.NOTE_ON:
                    started_before.add(key)
                elif event.kind == timeline.NOTE_OFF:
                    started_before.discard(key)
                continue
            if event.kind == timeline.NOTE_OFF and key in started_before:
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
                return whole + row.clock.whole_at(max(elapsed - row.start, START_OF_SCENE))
            whole += row.clock.whole_at(row.seconds)
        return whole

    def seconds_at(self, *, scene, whole):
        """Return the moment in seconds from a scene's start that is so many whole notes into it, the other way round from whole_at."""
        counted = 0.0
        for row in self._rows[scene]:
            row_whole = row.clock.whole_at(row.seconds)
            if whole <= counted + row_whole or row is self._rows[scene][-1]:
                return row.start + row.clock.seconds_at(whole - counted)
            counted += row_whole
        return START_OF_SCENE

    def bar_seconds(self, *, scene, elapsed):
        """Return how long a bar of the song's time signature lasts, in seconds, at a moment of a scene counted from the scene's start, at the tempo of that moment."""
        return self._bar * self.seconds_per_whole(scene=scene, elapsed=elapsed)

    def seconds_per_whole(self, *, scene, elapsed):
        """Return how long a whole note lasts at a moment of a scene counted from the scene's start, in seconds."""
        _, row = self.row_at(scene=scene, elapsed=elapsed)
        return row.clock.seconds_per_whole_at(elapsed - row.start)

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
