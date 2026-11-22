# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""The render process: the player's side of real-time playback (a LocalPlayback, realtime/render_process/playback.py) in a process of its own,
apart from the tracker's screen, its player ticking on its own loop every PLAYER_TICK_SECONDS while anything plays, whatever the
screen is doing. The messages that cross between it and the tracker's side (realtime/render_process/playback_process.py) are named here: each a
tuple of its kind and what it carries.
"""

import functools
import os
import signal
import threading
import time

from llamatron.model.file.song_file_error import SongFileError
from llamatron.realtime.render_process.playback import LocalPlayback
from llamatron.realtime.render_process.set_changes import with_changes
from llamatron.realtime.sender_process import process as sender_process
from llamatron.realtime.sender_process.engine import MonotonicClock
from llamatron.realtime.sender_process.process import RealtimeMIDISenderProcess, SenderNotStarted

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


def run_playback(*, connection, lifeline, lead, recording):
    """The render process: a LocalPlayback on the real clock, its player ticking on its own loop, fed by the pipe.

    It leads a process group of its own, which the Realtime Sender Process it starts joins, so that the tracker can end both at
    once however they are stuck (playback_process.end_process_group); it ends, closing its sender, when the tracker's end of
    the pipe goes, as when the tracker itself ends; and a watcher ends it even while its loop is stuck, should the tracker be
    killed meanwhile (watch_lifeline)."""
    if hasattr(os, 'setpgrp'):
        os.setpgrp()
    threading.Thread(target=watch_lifeline, args=(lifeline,), daemon=True).start()
    sender_process.ask_to_be_urgent()
    render = RenderLoop(connection=connection, playback=LocalPlayback(
        make_sender=functools.partial(recording_sender, recording=recording), clock=MonotonicClock(), lead=lead, at_once=False,
    ))
    connection.send((READY,))
    render.run()


def watch_lifeline(lifeline):
    """Wait on the lifeline, the end of a pipe the tracker never writes to, and end the render process the moment the tracker's
    end goes, as it does however the tracker ends, killed outright included. Waiting on a pipe takes no time and never wakes, so
    the watcher costs nothing until then. It ends the render process alone, so that the Realtime Sender Process sees its own
    pipe go and closes as it always does, sending a note off for every note sounding."""
    try:
        lifeline.recv()
    except (EOFError, OSError):
        pass
    os.kill(os.getpid(), signal.SIGKILL)


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
                timeout = None
                if self._was_playing or self._waiting:
                    timeout = PLAYER_TICK_SECONDS
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
                problem = None
                if built.problem is not None:
                    problem = str(built.problem)
                self._connection.send((BUILT, wanted, problem))
        playing = self._playback.is_playing()
        if playing or self._was_playing:
            status = self._playback.status(at=time.monotonic(), since=self._since)
            self._since = None
            if playing:
                self._since = status.now
            self._connection.send((STATUS, status))
        self._was_playing = playing
