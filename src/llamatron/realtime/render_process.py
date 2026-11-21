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


"""The render process: the player's side of real-time playback (a LocalPlayback, realtime/playback.py) in a process of its own,
apart from the tracker's screen, its player ticking on its own loop every PLAYER_TICK_SECONDS while anything plays, whatever the
screen is doing. The messages that cross between it and the tracker's side (realtime/playback_process.py) are named here: each a
tuple of its kind and what it carries.
"""

import functools
import os
import time

from llamatron.composition.song_file_error import SongFileError
from llamatron.realtime import sender_process
from llamatron.realtime.engine import MonotonicClock
from llamatron.realtime.playback import LocalPlayback
from llamatron.realtime.sender_process import RealtimeMIDISenderProcess, SenderNotStarted
from llamatron.realtime.set_changes import with_changes

# What the tracker tells the render process.
SET = 'set'
BUILD = 'build'
LAUNCH = 'launch'
APPLY = 'apply'
PORTS = 'ports'
SILENCE = 'silence'
STOP_CLIP = 'stop clip'
STOP_ALL = 'stop all'
FORGET = 'forget'
CLOSE = 'close'
# What the render process tells the tracker.
READY = 'ready'
STATUS = 'status'
BUILT = 'built'
LAUNCHED = 'launched'
REFUSED = 'refused'
CLOSED = 'closed'
# Why a launch was refused: a song that cannot be played, or a Realtime Sender Process that did not start.
REFUSED_SONG = 'song'
REFUSED_SENDER = 'sender'
# How often the render process's player plans ahead and sends a status while anything plays.
PLAYER_TICK_SECONDS = 0.02


def recording_sender(ports, *, recording):
    return RealtimeMIDISenderProcess(ports=ports, recording=recording)


def run_playback(*, connection, lead, recording):
    """The render process: a LocalPlayback on the real clock, its player ticking on its own loop, fed by the pipe.

    It leads a process group of its own, which the Realtime Sender Process it starts joins, so that the tracker can end both at
    once however they are stuck (playback_process.end_process_group); and it ends, closing its sender, when the tracker's end of
    the pipe goes, as when the tracker itself ends."""
    if hasattr(os, 'setpgrp'):
        os.setpgrp()
    sender_process.ask_to_be_urgent()
    render = RenderLoop(connection=connection, playback=LocalPlayback(
        make_sender=functools.partial(recording_sender, recording=recording), clock=MonotonicClock(), lead=lead, at_once=False,
    ))
    connection.send((READY,))
    render.run()


class RenderLoop:
    """The render process's loop: it takes the tracker's messages, ticks the player, and tells the tracker what plays and what is built."""

    __slots__ = ('_connection', '_playback', '_data', '_waiting', '_since', '_was_playing', '_closed')

    def __init__(self, *, connection, playback):
        self._connection = connection
        self._playback = playback
        self._data = {}
        # The scores asked for and not yet told of, and where the visualizer's notes were last read up to.
        self._waiting = []
        self._since = None
        self._was_playing = False
        self._closed = None

    def run(self):
        try:
            while self._closed is None:
                timeout = PLAYER_TICK_SECONDS if self._was_playing or self._waiting else None
                if self._connection.poll(timeout):
                    self._take_waiting()
                if self._closed is None:
                    self._playback.tick()
                    self._tell()
        except (BrokenPipeError, EOFError, OSError):
            self._playback.close()
            return
        self._connection.send((CLOSED, self._closed[0]))

    def _take_waiting(self):
        """Do what every message waiting from the tracker says, in order, until one closes the process."""
        while self._closed is None and self._connection.poll():
            self._take(self._connection.recv())

    def _take(self, message):
        """Do what a message from the tracker says."""
        kind, *rest = message
        if kind == SET:
            changes, removed = rest
            self._data = with_changes(data=self._data, changes=changes, removed=removed)
            self._playback.take_set(self._data)
        elif kind == BUILD:
            self._playback.take_set(self._data)
            self._playback.build(rest[0])
            self._waiting.append(rest[0])
        elif kind == LAUNCH:
            self._launch(wanted=rest[0], launch=rest[1], ports=rest[2])
        elif kind == CLOSE:
            self._closed = (self._playback.close(),)
        else:
            self._command(kind=kind, rest=rest)

    def _command(self, *, kind, rest):
        """Do one of the commands that need no answer."""
        if kind == APPLY:
            wanted, responsiveness, scene_map, track_map = rest
            self._playback.apply(wanted=wanted, responsiveness=responsiveness, scene_map=scene_map, track_map=track_map)
        elif kind == PORTS:
            try:
                self._playback.use_ports(rest[0], renewed=rest[1])
            except SenderNotStarted:
                # Getting ready ahead may fail; the first launch tries again and says why.
                return
        elif kind == SILENCE:
            self._playback.silence(ports=rest[0], channels=rest[1])
        elif kind == STOP_CLIP:
            self._playback.stop_clip(rest[0])
        elif kind == STOP_ALL:
            self._playback.stop_all()
        elif kind == FORGET:
            self._playback.forget()

    def _launch(self, *, wanted, launch, ports):
        """Launch, and answer whether the launch waits for the next bar, with what plays then, or why it could not play."""
        try:
            self._playback.take_set(self._data)
            waits = self._playback.launch(wanted=wanted, launch=launch, ports=ports)
        except SongFileError as problem:
            self._connection.send((REFUSED, REFUSED_SONG, str(problem)))
            return
        except SenderNotStarted as problem:
            self._connection.send((REFUSED, REFUSED_SENDER, str(problem)))
            return
        status = self._playback.status(at=time.monotonic(), since=None)
        self._since = status.now
        self._was_playing = status.playing
        self._connection.send((LAUNCHED, waits, status))

    def _tell(self):
        """Tell the tracker of each score built since, and what plays, while anything plays and once as it stops."""
        for wanted in list(self._waiting):
            built = self._playback.built(wanted)
            if built is not None:
                self._waiting.remove(wanted)
                self._connection.send((BUILT, wanted, None if built.problem is None else str(built.problem)))
        playing = self._playback.is_playing()
        if playing or self._was_playing:
            status = self._playback.status(at=time.monotonic(), since=self._since)
            self._since = status.now if playing else None
            self._connection.send((STATUS, status))
        self._was_playing = playing
