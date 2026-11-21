# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""The player's side of real-time playback: the scores, the player and the sender, apart from the tracker's pages.

The transport (interface/tracker/transport.py) knows the document: the set, the routes, what stops a song from playing, the seeds and how
to find a scene or a track again after an edit. What it asks of the player's side goes through a few commands, each naming
what a score is made from (Wanted): take the set's data, build a score ahead, launch, hand an edit's score to the player,
stop, silence; and a few questions, what plays and what is heard, for the lights and the visualizer. LocalPlayback answers
them in the tracker's own process, the player ticking on the tracker's timer, as the tests run it on a stepped clock.
"""

import functools
from typing import NamedTuple

from llamatron.model.objects.setlist import Setlist
from llamatron.realtime.render_process.player import Player
from llamatron.realtime.render_process.score import Keeping, Score
from llamatron.realtime.render_process.score_builder import ScoreBuilder

# What a launch plays: a scene and every clip of it, one clip, or several clips of one scene together.
LAUNCH_SCENE = 'scene'
LAUNCH_CLIP = 'clip'
LAUNCH_CLIPS = 'clips'


class Wanted(NamedTuple):
    """What a score is made from: the set's revision, the song's name, each track's Route as (track, Route) in order, and the seed of the play's random parts."""

    revision: int
    song_name: str
    routes: tuple
    seed: int


class PlayRequest(NamedTuple):
    """What a page asks to play: what kind of launch, the scene, the tracks of a launch of clips, and whether it plays again and again."""

    kind: str
    scene: int
    tracks: tuple = ()
    forever: bool = False


class Status(NamedTuple):
    """What plays, as the player's side tells the tracker in a status message, for the lights, the visualizer and the Draws page.

    at is the system's monotonic clock when it was read, which every process shares, so that the tracker carries the elapsed
    times on to the moment it draws; now is the player's own clock then. heard holds what the visualizer hears since the
    status before, as Player.heard gives it.
    """

    at: float
    now: float
    playing: bool
    scenes: tuple
    clips: frozenset
    sounding: frozenset
    scene_elapsed: dict
    clip_elapsed: dict
    repeats_left: dict
    song_position: float
    song_seconds: float
    seconds_per_quarter: float
    heard: tuple
    draw_places: dict


class LocalPlayback:
    """The scores, the player and the sender in the tracker's own process."""

    __slots__ = ('_make_sender', '_clock', '_lead', '_builder', '_data', '_sender', '_ports', '_zero', '_player', '_playing', '_takes', '_asked')

    def __init__(self, *, make_sender, clock, lead, at_once):
        """make_sender(ports) makes the sender, clock tells the time, lead is how far ahead of now a launch from silence starts,
        and at_once builds every score in its request, as the tests want, rather than off the screen's thread."""
        self._make_sender = make_sender
        self._clock = clock
        self._lead = lead
        self._builder = ScoreBuilder(at_once=at_once)
        self._data = None
        self._sender = None
        self._ports = None
        self._zero = None
        self._player = None
        # What the player's score was made from.
        self._playing = None
        # The play's takes, by (scene, track): a clip launched by hand, and a looping clip's next lap, plays another take, new
        # random choices of its own, for as long as the play lasts (SongRealizer's takes).
        self._takes = {}
        # The last score asked to be built, which a looping clip's next take is built as, so that an edit waiting to be heard is
        # built with it rather than replaced by it.
        self._asked = None

    def start(self):
        """Nothing to start: the player's side is in this process."""

    def has_ended(self):
        """Return False: the player's side in this process ends only with it."""
        return False

    def is_ready(self):
        """Return True: the player's side in this process is ready as soon as it is made."""
        return True

    # The set and its scores.

    def take_set(self, data):
        """Take the set's data as its objects keep it (Setlist.kept_data), which every score after is made from."""
        self._data = data

    def build(self, wanted):
        """Ask for a score to be built ahead, off the screen's thread, from the set's data as it is now, with the play's takes."""
        takes = self._takes_for(wanted)
        self._asked = wanted
        self._builder.request(key=_key_of(wanted=wanted, takes=takes), build=functools.partial(score_of, wanted=wanted, data=self._data, takes=takes))

    def built(self, wanted):
        """Return what building a score came to, a Built, or None while it is not done or was never asked."""
        return self._builder.built(_key_of(wanted=wanted, takes=self._takes_for(wanted)))

    def _takes_for(self, wanted):
        """Return the takes a score of what is wanted plays: the play's, for the seed that plays, and none for a play to come."""
        return self._takes if self._playing is not None and wanted.seed == self._playing.seed else {}

    def _retake(self, keys):
        """Give each (scene, track) its next take, for the rest of the play."""
        for key in keys:
            self._takes[key] = self._takes.get(key, 0) + 1

    def has_score(self, wanted):
        """Return whether the player's score was made from what is wanted."""
        return self._player is not None and self._playing == wanted

    # Playing.

    def launch(self, *, wanted, launch, ports):
        """Play what a launch names, through a sender on the ports, on a score made from what is wanted: the one built ahead
        when there is one, else rendered now, raising SongFileError for a song that cannot be played. Return whether it waits
        for the next bar of what plays, rather than starting at once."""
        sender = self.use_ports(ports)
        if self.has_score(wanted) and self._player.is_playing():
            # A launch by hand while the play goes on plays another take of what it launches, rendered now with everything else kept.
            self._retake(keys=self._launched(launch))
            self._player.set_score(score_of(wanted=wanted, data=self._data, earlier=self._player.get_score(), takes=dict(self._takes)))
        elif not self.has_score(wanted):
            if self._playing is None or wanted.seed != self._playing.seed:
                self._takes = {}
            built = self.built(wanted)
            score = built.score if built is not None and built.score is not None else score_of(wanted=wanted, data=self._data, earlier=None)
            if self._player is None or self._player.get_sender() is not sender:
                self._player = Player(score=score, sender=sender, now=self._now, lead=self._lead)
            else:
                self._player.set_score(score)
            self._playing = wanted
        if launch.kind == LAUNCH_SCENE:
            at = self._player.play_scene(launch.scene)
        elif launch.kind == LAUNCH_CLIP:
            at = self._player.play_clip(scene=launch.scene, track=launch.tracks[0], forever=launch.forever)
        else:
            at = self._player.play_clips(scene=launch.scene, tracks=list(launch.tracks), forever=launch.forever)
        return at > self._now() + self._lead

    def _launched(self, launch):
        """Return the (scene, track) of every clip a launch plays: every track of a scene, or the tracks named."""
        if launch.kind == LAUNCH_SCENE:
            return [(launch.scene, track) for track in self._player.get_score().get_tracks()]
        return [(launch.scene, track) for track in launch.tracks]

    def apply(self, *, wanted, responsiveness, scene_map, track_map):
        """Hand the score built for an edit to the player, which takes it from the moment the song's Live response says."""
        self._player.update_score(score=self.built(wanted).score, responsiveness=responsiveness, scene_map=scene_map, track_map=track_map)
        self._playing = wanted

    def use_ports(self, ports, *, renewed=()):
        """Return the sender, started on the ports, starting another when the ports it opened aren't these, or when a port
        among renewed, FluidSynth's after FluidSynth started again, is new though named the same."""
        if self._sender is not None and set(renewed) & set(self._ports):
            self._ports = [port for port in self._ports if port not in renewed]
        if self._sender is not None and set(ports) - set(self._ports):
            self.stop_all()
            self._sender.close()
            self._sender = None
            self._player = None
        if self._sender is None:
            self._ports = list(ports)
            self._zero = self._clock.now()
            self._sender = self._make_sender(self._ports)
            self._sender.start(at=self._zero)
        return self._sender

    def silence(self, *, ports, channels):
        """Send note offs, all notes off and all sound off on the channels, through a sender on the ports."""
        self.use_ports(ports).silence(channels=channels)

    def stop_clip(self, track):
        if self._player is not None:
            self._player.stop_clip(track)

    def stop_all(self):
        if self._player is not None:
            self._player.stop_all()

    def forget(self):
        """Stop everything and forget the score, as another set is opened; the sender stays for the next play."""
        self.stop_all()
        self._player = None

    def close(self):
        """Stop everything and end the sender, as the tracker quits, returning what a recording sender sent, or None."""
        self.stop_all()
        sent = None
        if self._sender is not None:
            sent = self._sender.close()
            self._sender = None
        self._player = None
        return sent

    def tick(self):
        """Plan ahead and send what falls due; ask for another take of each looping clip that started a lap, built off the
        thread, and hand the player that score once built, which the clip's next lap plays, or the take there is if not yet."""
        if self._player is None:
            return
        self._player.tick()
        laps = self._player.take_laps()
        if laps:
            self._retake(keys=laps)
            self.build(self._playing if self._asked is None else self._asked)
        built = self.built(self._playing) if self._takes else None
        if built is not None and built.score is not None and built.score is not self._player.get_score():
            self._player.set_score(built.score)

    # What plays, for the lights and the visualizer.

    def is_playing(self):
        return self._player is not None and self._player.is_playing()

    def playing_scenes(self):
        return [] if self._player is None else self._player.playing_scenes()

    def is_clip_playing(self, *, index, track):
        return self._player is not None and self._player.is_clip_playing(scene=index, track=track)

    def is_track_sounding(self, track):
        return self._player is not None and self._player.is_track_sounding(track)

    def scene_elapsed(self, index):
        return None if self._player is None else self._player.scene_elapsed(index)

    def clip_elapsed(self, *, index, track):
        return None if self._player is None else self._player.clip_elapsed(scene=index, track=track)

    def repeats_left(self, *, index, track):
        return None if self._player is None else self._player.repeats_left(scene=index, track=track)

    def song_position(self):
        return None if self._player is None else self._player.song_position()

    def song_seconds(self):
        return None if self._player is None else self._player.get_score().song_seconds()

    def seconds_per_quarter(self):
        return None if self._player is None else self._player.seconds_per_quarter()

    def heard(self, *, since):
        """Return the clock's time now and, for each track with a clip running, the notes heard since an earlier time (Player.heard)."""
        return self._player.heard(since=since)

    def draw_places(self, *, scene, seconds):
        """Return where every draw stands a time into a scene of what plays, by name."""
        return self._player.get_score().draw_places_at(scene=scene, seconds=seconds)

    def status(self, *, at, since):
        """Return what plays now as a Status, read at a moment of the system's monotonic clock, with what is heard after since,
        a moment of the player's clock, or what sounds now alone with since None."""
        if not self.is_playing():
            return Status(at, 0.0, False, (), frozenset(), frozenset(), {}, {}, {}, None, None, None, (), {})
        now, heard = self._player.heard(since=since)
        scenes = tuple(self.playing_scenes())
        plays = [(play.scene, play.track) for play in self._player.running_plays()]
        first = None if not scenes else self.scene_elapsed(scenes[0])
        return Status(
            at, now, True, scenes, frozenset(plays), frozenset(track for _scene, track in plays if self.is_track_sounding(track)),
            {scene: self.scene_elapsed(scene) for scene in scenes}, {play: self.clip_elapsed(index=play[0], track=play[1]) for play in plays},
            {play: self.repeats_left(index=play[0], track=play[1]) for play in plays}, self.song_position(), self.song_seconds(),
            self.seconds_per_quarter(), tuple(heard), {} if first is None else self.draw_places(scene=scenes[0], seconds=first),
        )

    def get_player(self):
        """Return the player, for the tests."""
        return self._player

    def _now(self):
        return self._clock.now() - self._zero


def _key_of(*, wanted, takes):
    """Return what a score is built and found by: what is wanted and the takes it plays."""
    return (wanted, frozenset(takes.items()))


def score_of(*, wanted, data, earlier, takes=None):
    """Return the score of a song made from the set's data: from a copy of the set, so that nothing the render reads changes
    while it renders, and from the earlier score where an edit leaves scenes or clips of it as they were."""
    song = Setlist.from_data(data=data).get_song(wanted.song_name)
    return Score(song=song, routes=dict(wanted.routes), seed=wanted.seed, keeping=Keeping(data, earlier), takes=takes)
