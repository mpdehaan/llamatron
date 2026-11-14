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

"""The player: launches a score's scenes and clips, and sends each clip's events to a sender as its moment comes.

The user's design of 2026-11-09 and 2026-11-10, Live's words where Live has them, the clip's
setting shown as Advance on the clip page. A scene launched by hand plays every clip of it. A scene
is done when every clip launched in it that doesn't loop has finished its repeats, and then each
clip of the scene whose Advance is "With Scene", looping or not, sends a start to the clip directly
below it, an empty slot counting as "With Scene". A clip whose Advance is "Next" sends its start the
moment its own repeats end, whatever the rest of its scene is doing. "Off" sends nothing, so the
track falls silent. What a start does depends on the scene it reaches: with that scene's Launch
together on, the whole scene launches at once and everything still playing in the scene above
stops, loops included; with it off, the one clip starts on its own, cutting only what its track
played, and the rest wait for their own starts. A clip launched by hand plays on its own, whatever
its scene says, and a clip stopped by hand, or cut by another clip launched on its track, never
finished, so it sends no start. A looping clip never finishes on its own: it loops until something
is launched on its track or everything stops, so it doesn't hold its scene, and a scene whose every
clip loops is never done, so the song waits there for the human. So with the defaults every example
played from the top sends exactly what its export holds, which test/test_realtime.py holds the
player to. Until 2026-11-10 one looping clip held its scene, and the user changed that when the
registers demo never left its first scene.

A launch by hand while anything plays is always at the next bar of the song's time signature, as
Live's default quantization is, the bars counted from the start of the earliest clip playing, and
what plays goes on until then; a clip or scene shorter than a bar hands over at its end. With
nothing playing, a launch is at once. The starts that follow actions send are at the scene's end,
which is where the export has the next scene start.

Everything is decided ahead of time: the player keeps the moments to come in a heap and, on every
tick, expands the ones due within the next LOOKAHEAD_SECONDS into events queued with the sender, so
that the sender, which may be in another process, never waits for the tracker. At one time the
follow actions' work comes before a launch by hand, so that the human's launch is what plays. The
sender is anything with the engine's methods: start, add, drop, stop_tag and stop_all. The player
reads nothing but the score and a clock that gives the sender's seconds, so the tests drive it on a
stepped clock with no time passing.
"""

import heapq
from typing import NamedTuple

from llamatron.composition.file_format import FollowAction, LiveResponsiveness
from llamatron.realtime.engine import BEFORE_EVERYTHING
from llamatron.realtime.timeline import NOTE_OFF, NO_VELOCITY, Playing, Tag
from llamatron.support.rational import Rational

# How far ahead moments are turned into queued events. A tick comes many times a second, so a moment is never missed, and half a second
# ahead leaves an edit made while playing room to change a scene's end, where every clip already queues all its notes as it starts.
LOOKAHEAD_SECONDS = 0.5
# The kinds of moment the heap holds, in the order they run at one time: a clip's and a scene's done checks and the launches their follow actions send, then the launches by hand.
CLIP_DONE = 0
SCENE_DONE = 1
LAUNCH_SCENE = 2
LAUNCH_CLIPS = 3
SCENE_BY_HAND = 4
CLIP_BY_HAND = 5
FIRST_SCENE = 0
NO_BARS = 0
ONE_BAR = 1
# A whole note is four quarter notes, the beat the visualizer follows.
QUARTERS_PER_WHOLE = 4
# How soon after now an edit made while playing is heard at its quickest, so that its notes are queued before they're due.
LIVE_LATENCY_SECONDS = 0.05
# How far apart two moments may be and still count as one, against rounding in the seconds.
SAME_MOMENT_SECONDS = 1e-6


class Moment(NamedTuple):
    """Something to do at a time: in heap order by time, then kind, then a count so that two alike keep the order they were planned in."""

    time: float
    kind: int
    count: int
    scene: int
    tracks: tuple
    # Whether a clip launched by hand is to loop forever, for a listening page.
    forever: bool


class Play:
    """One launch of one clip on its track: when it starts and ends on the sender's clock, its tag, and how it was launched and ended."""

    __slots__ = ('scene', 'track', 'start', 'end', 'tag', 'alone', 'loops', 'cut', 'done', 'preview')

    def __init__(self, *, scene, track, start, end, tag, alone, loops, preview=False):
        self.scene = scene
        self.track = track
        self.start = start
        self.end = end
        self.tag = tag
        self.alone = alone
        self.loops = loops
        # Cut short by a stop or by another clip on its track, so it never finished and sends no start.
        self.cut = False
        # Its scene's follow actions have fired, so a later check of the scene leaves it out.
        self.done = False
        # Played again and again by hand, as a listening page plays a clip, rather than looping by its clip's Loop, so that an edit to the Loop leaves it looping.
        self.preview = preview

    def is_running(self, now):
        return self.start <= now < self.end


class Player:
    """Launches scenes and clips of a score through a sender, following the follow actions and Launch together."""

    __slots__ = ('_score', '_sender', '_now', '_plays', '_moments', '_count', '_play_count')

    def __init__(self, *, score, sender, now):
        """now is a function returning the sender's seconds, the clock the events' seconds are on."""
        self._score = score
        self._sender = sender
        self._now = now
        # Every play launched and not yet over: running, queued ahead within the lookahead, or ended and waiting for a tick to forget it.
        self._plays = []
        self._moments = []
        self._count = 0
        self._play_count = 0

    def score(self):
        return self._score

    def sender(self):
        return self._sender

    def set_score(self, score):
        """Take a score rendered afresh, which the next launch plays from; what plays already keeps its events."""
        self._score = score

    # Edits made while playing, the user's design: what plays takes the new score from a moment the song's Live response says.

    def update_score(self, *, score, responsiveness, scene_map, track_map):
        """Take a score rendered afresh after an edit, and change what plays to it: each clip from the moment responsiveness says, keeping its place in the music.

        scene_map and track_map give each scene's place and track's name in the new score by its old
        ones, None for one that has gone, so that inserting a scene above a playing one or renaming
        its track changes nothing that plays. A clip that hasn't started is queued afresh; one playing
        ends the notes sounding across the moment and takes the new notes from it; the moments when its
        scene and its repeats end are planned again, so that a clip made to loop goes on looping.
        """
        old = self._score
        now = self._now()
        bar = self.next_bar()
        self._score = score
        for play in list(self._plays):
            old_scene = play.scene
            old_track = play.track
            new_scene = scene_map.get(old_scene)
            new_track = track_map.get(old_track)
            if play.end <= now:
                if new_scene is not None and new_track is not None:
                    play.scene = new_scene
                    play.track = new_track
                continue
            at = self._switch_time(play=play, score=old, responsiveness=responsiveness, now=now, bar=bar)
            if new_scene is None or new_track is None:
                self._cut(play=play, at=max(at, now), score=old)
                continue
            if play.start >= at:
                self._sender.drop(tag=play.tag, after=BEFORE_EVERYTHING)
                start = play.start
            elif at >= play.end:
                # The edit is heard only from the play's end, where whether it loops still decides what comes next.
                play.scene = new_scene
                play.track = new_track
                play.loops = play.preview or score.loops(scene=new_scene, track=new_track)
                continue
            else:
                self._sender.drop(tag=play.tag, after=at)
                self._end_notes_across(play=play, at=at, score=old, scene=old_scene, track=old_track)
                whole = old.whole_at(scene=old_scene, elapsed=at - play.start)
                start = at - score.seconds_at(scene=new_scene, whole=whole)
            play.scene = new_scene
            play.track = new_track
            play.start = start
            play.loops = play.preview or score.loops(scene=new_scene, track=new_track)
            if not play.cut:
                play.end = start + score.scene_seconds(new_scene)
            self._sender.add(score.events_from(scene=new_scene, track=new_track, start=start, tag=play.tag, after=max(at, start)))
        self._moments = [moment._replace(scene=scene_map[moment.scene], tracks=tuple(track_map[track] for track in moment.tracks if track_map.get(track) is not None))
                         for moment in self._moments if scene_map.get(moment.scene) is not None]
        heapq.heapify(self._moments)
        self._plan_ends_again(now)

    def _switch_time(self, *, play, score, responsiveness, now, bar):
        """Return when an edit is heard on a play: at once, at the next bar of what plays (bar, worked out before the new score came), or at the play's next pass by the old score, never before LIVE_LATENCY_SECONDS from now."""
        soonest = now + LIVE_LATENCY_SECONDS
        if responsiveness == LiveResponsiveness.NEXT_BAR:
            at = bar
        elif responsiveness == LiveResponsiveness.CLIP_RESTART and play.start < now:
            into = score.next_pass_start(scene=play.scene, track=play.track, elapsed=now - play.start)
            at = None if into is None else play.start + into
        else:
            at = soonest
        return soonest if at is None else max(at, soonest)

    def _end_notes_across(self, *, play, at, score, scene, track):
        """Send a note off at a moment for every note of a play, by the score it was queued from, that started before it and sounds across it."""
        notes = score.sounding_across(scene=scene, track=track, elapsed=at - play.start)
        self._sender.add([Playing(Rational(0), at, port, channel, NOTE_OFF, number, NO_VELOCITY, play.tag) for port, channel, number in notes])

    def _plan_ends_again(self, now):
        """Plan again when each playing clip's scene and repeats end, by the score as it is now, forgetting the ends planned by the score before."""
        self._moments = [moment for moment in self._moments if moment.kind not in (SCENE_DONE, CLIP_DONE) or moment.time <= now]
        heapq.heapify(self._moments)
        planned = set()
        for play in self._plays:
            if play.end <= now or play.cut or play.done:
                continue
            key = (round(play.end / SAME_MOMENT_SECONDS), play.scene)
            if key not in planned:
                planned.add(key)
                self._plan(time=play.end, kind=SCENE_DONE, scene=play.scene)
            clip_end = self._score.clip_end(scene=play.scene, track=play.track)
            if clip_end is not None and self._score.follow_action(scene=play.scene, track=play.track) == FollowAction.NEXT and play.start + clip_end > now:
                self._plan(time=play.start + clip_end, kind=CLIP_DONE, scene=play.scene, tracks=(play.track,))

    # Launching and stopping, by hand.

    def play_song(self):
        """Play the song from its first scene, with the follow actions taking it on from there. Return when it starts: now, or the next bar of what plays."""
        return self.play_scene(FIRST_SCENE)

    def play_scene(self, scene):
        """Launch every clip of a scene, whatever its clips' settings say, in place of everything playing. Return when it starts: now, or the next bar of what plays."""
        at = self.next_bar()
        if at is None:
            at = self._now()
        self._plan(time=at, kind=SCENE_BY_HAND, scene=scene)
        self.tick()
        return at

    def play_clip(self, *, scene, track, forever=False):
        """Launch one clip on its own, cutting whatever its track plays. With forever, it loops as a looping clip does, which a listening page wants. Return when it starts."""
        at = self.next_bar()
        if at is None:
            at = self._now()
        self._plan(time=at, kind=CLIP_BY_HAND, scene=scene, tracks=(track,), forever=forever)
        self.tick()
        return at

    def stop_clip(self, track):
        """Cut what a track is playing now, leaving the other tracks, and what is queued ahead on this one, alone."""
        play = self.running_on(track)
        if play is not None:
            self._cut(play=play, at=self._now())

    def stop_all(self):
        """Stop every clip and forget every moment to come, silencing every channel used."""
        self._sender.stop_all()
        self._plays = []
        self._moments = []

    def next_bar(self):
        """Return when the next bar starts, counted from the start of the earliest clip playing, or that clip's end if it comes first, or None when nothing plays."""
        now = self._now()
        running = self.running_plays()
        if not running:
            return None
        first = min(running, key=lambda play: play.start)
        elapsed = now - first.start
        bar = self._score.bar_seconds(scene=first.scene, elapsed=elapsed)
        bars_done = int(elapsed // bar) if bar > NO_BARS else NO_BARS
        at = first.start + (bars_done + ONE_BAR) * bar if bar > NO_BARS else first.end
        return min(at, first.end)

    def tick(self):
        """Turn every moment due within the lookahead into queued events and further moments, in time order, and forget the plays that are over."""
        now = self._now()
        horizon = now + LOOKAHEAD_SECONDS
        while self._moments and self._moments[0].time <= horizon:
            moment = heapq.heappop(self._moments)
            if moment.kind == CLIP_DONE:
                self._clip_done(scene=moment.scene, track=moment.tracks[0], at=moment.time)
            elif moment.kind == SCENE_DONE:
                self._scene_done(scene=moment.scene, at=moment.time)
            elif moment.kind == LAUNCH_SCENE:
                self._launch_scene(scene=moment.scene, at=moment.time)
            elif moment.kind == LAUNCH_CLIPS:
                for track in moment.tracks:
                    self._start_play(scene=moment.scene, track=track, at=moment.time, alone=True)
            elif moment.kind == SCENE_BY_HAND:
                self._stop_everything_at(moment.time)
                self._launch_scene(scene=moment.scene, at=moment.time)
            else:
                for track in moment.tracks:
                    self._start_play(scene=moment.scene, track=track, at=moment.time, alone=True, forever=moment.forever, preview=moment.forever)
        self._plays = [play for play in self._plays if play.end > now or not (play.done or play.cut)]

    # What is playing, for the lights.

    def is_playing(self):
        """Return whether anything plays now or is still to come: a play not over, or a moment that can still launch or end one."""
        now = self._now()
        return any(play.end > now for play in self._plays) or any(self._can_act(moment) for moment in self._moments)

    def _can_act(self, moment):
        """Return whether a moment can still do something: a launch can, and a check of a scene's or a clip's end can while a play of it is neither cut nor done."""
        if moment.kind not in (SCENE_DONE, CLIP_DONE):
            return True
        return any(play.scene == moment.scene and not play.cut and not play.done and play.start < moment.time for play in self._plays)

    def running_plays(self):
        now = self._now()
        return [play for play in self._plays if play.is_running(now)]

    def running_on(self, track):
        """Return the play running on a track now, or None."""
        for play in self.running_plays():
            if play.track == track:
                return play
        return None

    def heard(self, *, since):
        """Return the clock's time now, and for each track with a clip running, the notes that started after since and those still sounding, as the score's Heard notes, for the visualizer; with since None, those sounding now alone."""
        now = self._now()
        since = now if since is None else since
        heard = []
        for play in self.running_plays():
            started, held = self._score.heard(scene=play.scene, track=play.track, since=since - play.start, until=now - play.start)
            if started or held:
                heard.append((play.track, started, held))
        return now, heard

    def seconds_per_quarter(self):
        """Return how long a quarter note lasts now, at the tempo of the earliest scene playing, or None when nothing plays."""
        scenes = self.playing_scenes()
        if not scenes:
            return None
        _, row = self._score.row_at(scene=scenes[0], elapsed=self.scene_elapsed(scenes[0]))
        return row.whole / QUARTERS_PER_WHOLE

    def playing_scenes(self):
        """Return the scenes with a clip playing now, in order."""
        return sorted({play.scene for play in self.running_plays()})

    def is_clip_playing(self, *, scene, track):
        play = self.running_on(track)
        return play is not None and play.scene == scene

    def is_track_sounding(self, track):
        """Return whether a note sounds on a track now, read from the score rather than the sender, which may be in another process."""
        play = self.running_on(track)
        return play is not None and self._score.is_sounding(scene=play.scene, track=track, elapsed=self._now() - play.start)

    def scene_elapsed(self, scene):
        """Return how far into a scene its earliest running clip is, in seconds, or None when none plays."""
        starts = [play.start for play in self.running_plays() if play.scene == scene]
        return None if not starts else self._now() - min(starts)

    def clip_elapsed(self, *, scene, track):
        """Return how far into its play a clip is, in seconds, or None when the clip isn't playing."""
        play = self.running_on(track)
        if play is None or play.scene != scene:
            return None
        return self._score.clip_elapsed(scene=scene, track=track, elapsed=self._now() - play.start)

    def repeats_left(self, *, scene, track):
        """Return how many repeats a playing clip has left, or None when the clip isn't playing, loops, or has none."""
        play = self.running_on(track)
        if play is None or play.scene != scene:
            return None
        return self._score.repeats_left(scene=scene, track=track, elapsed=self._now() - play.start)

    def song_position(self):
        """Return where the song is, in seconds from its top, by the earliest scene playing, or None when nothing plays."""
        scenes = self.playing_scenes()
        if not scenes:
            return None
        return self._score.scene_start(scenes[0]) + self.scene_elapsed(scenes[0])

    # The plan.

    def _plan(self, *, time, kind, scene, tracks=(), forever=False):
        self._count += 1
        heapq.heappush(self._moments, Moment(time, kind, self._count, scene, tuple(tracks), forever))

    def _launch_scene(self, *, scene, at):
        for track in self._score.tracks():
            self._start_play(scene=scene, track=track, at=at, alone=False)
        self._plan(time=at + self._score.scene_seconds(scene), kind=SCENE_DONE, scene=scene)

    def _start_play(self, *, scene, track, at, alone, forever=False, preview=False):
        """Queue one clip's events from a moment on its track, cutting what the track plays then, and cut where a play already queued ahead on the track starts."""
        next_start = None
        for old in self._plays_on(track):
            if old.start == at:
                self._drop(old)
            elif old.start < at < old.end:
                self._cut(play=old, at=at)
            elif old.start > at:
                next_start = old.start if next_start is None else min(next_start, old.start)
        self._play_count += 1
        end = at + self._score.scene_seconds(scene)
        loops = forever or self._score.loops(scene=scene, track=track)
        play = Play(scene=scene, track=track, start=at, end=end, tag=Tag(scene, track, self._play_count), alone=alone, loops=loops, preview=preview)
        self._plays.append(play)
        self._sender.add(self._score.played_events(scene=scene, track=track, start=at, play=self._play_count))
        if next_start is not None and next_start < end:
            self._cut(play=play, at=next_start)
        # A clip launched with its scene is checked by the scene's own moment; one launched alone, or played again to loop, needs a moment of its own.
        if alone or forever:
            self._plan(time=end, kind=SCENE_DONE, scene=scene)
        # A clip whose Advance is "Next" sends its start the moment its own repeats end.
        clip_end = self._score.clip_end(scene=scene, track=track)
        if clip_end is not None and self._score.follow_action(scene=scene, track=track) == FollowAction.NEXT:
            self._plan(time=at + clip_end, kind=CLIP_DONE, scene=scene, tracks=(track,))

    def _clip_done(self, *, scene, track, at):
        """When a clip whose Advance is "Next" ends its repeats at a moment, uncut and not yet done, send its start to the clip below."""
        for play in self._plays:
            if play.scene == scene and play.track == track and play.start < at <= play.end and not play.cut and not play.done:
                play.done = True
                self._send_starts(scene=scene, at=at, tracks=[track])
                return

    def _scene_done(self, *, scene, at):
        """When a scene launched at a moment comes to its end, send the starts its clips' follow actions say to send, and play its looping clips again.

        The scene's seconds are those of its longest clip that doesn't loop, so at its end every
        such clip has finished, and the scene is done unless every clip of it loops, in which case
        it waits for the human. The loops play again first, so that the scene below, launched at
        the same moment, cuts them where it starts, and they go on where it doesn't; a loop whose
        start has no scene below to go to ends with the scene, as Live stops a clip whose follow
        action finds nothing, so the song ends when the export does.
        """
        plays = [play for play in self._plays if play.scene == scene and play.start < at and not play.cut and not play.done]
        if not plays or any(play.end > at for play in plays):
            return
        for play in plays:
            play.done = True
        done = not all(play.loops for play in plays)
        last_scene = scene + 1 >= self._score.scene_count()
        for play in plays:
            if play.loops and not (done and last_scene and self._score.follow_action(scene=scene, track=play.track) != FollowAction.OFF):
                self._start_play(scene=scene, track=play.track, at=at, alone=play.alone, forever=True, preview=play.preview)
        if done:
            starts = [play.track for play in plays if self._score.follow_action(scene=scene, track=play.track) != FollowAction.OFF]
            self._send_starts(scene=scene, at=at, tracks=starts)

    def _send_starts(self, *, scene, at, tracks):
        """Send a start from each track's clip in a scene to the clip directly below it: the whole scene below when it launches together, and the clips alone otherwise, each planned once."""
        below = scene + 1
        if not tracks or below >= self._score.scene_count():
            return
        if self._score.launches_together(below):
            if not self._is_planned(time=at, kind=LAUNCH_SCENE, scene=below):
                self._plan(time=at, kind=LAUNCH_SCENE, scene=below)
        else:
            new = [track for track in tracks if not self._is_planned(time=at, kind=LAUNCH_CLIPS, scene=below, track=track)]
            if new:
                self._plan(time=at, kind=LAUNCH_CLIPS, scene=below, tracks=new)

    def _is_planned(self, *, time, kind, scene, track=None):
        return any(moment.time == time and moment.kind == kind and moment.scene == scene and (track is None or track in moment.tracks) for moment in self._moments)

    def _stop_everything_at(self, at):
        """End every play at a moment, now or ahead, and forget every moment to come, for a scene launched by hand."""
        for play in list(self._plays):
            if play.start >= at:
                self._drop(play)
            elif play.end > at:
                self._cut(play=play, at=at)
        self._moments = []

    def _plays_on(self, track):
        return [play for play in self._plays if play.track == track]

    def _drop(self, play):
        """Forget a play that hasn't started, and its queued events."""
        self._sender.drop(tag=play.tag, after=BEFORE_EVERYTHING)
        self._plays.remove(play)

    def _cut(self, *, play, at, score=None):
        """End a play at a moment: now, by stopping its tag, or later, by dropping its events from then and ending the notes sounding across it, by the score it was queued from."""
        score = self._score if score is None else score
        if at <= self._now():
            self._sender.stop_tag(play.tag)
        else:
            self._sender.drop(tag=play.tag, after=at)
            notes = score.sounding_across(scene=play.scene, track=play.track, elapsed=at - play.start)
            self._sender.add([Playing(Rational(0), at, port, channel, NOTE_OFF, number, NO_VELOCITY, play.tag) for port, channel, number in notes])
        play.end = min(play.end, at)
        play.cut = True
