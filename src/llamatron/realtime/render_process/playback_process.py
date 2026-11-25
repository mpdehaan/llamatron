# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later


"""The player's side of real-time playback in a process of its own, the render process, apart from the tracker's screen.

The render process (realtime/render_process/process.py) holds a LocalPlayback (realtime/render_process/playback.py): it builds the scores, its player
ticks on its own loop whatever the screen is doing, and it starts the Realtime Sender Process. The tracker holds a PlaybackProcess,
which answers the transport as a LocalPlayback does, through a pipe, and starts the render process the first time it needs it:

- The set crosses as the parts that changed since the last it sent, with each build and launch (realtime/render_process/set_changes.py), so an
  edit to a step sends little more than that step's values. The render process keeps its own copy, replacing what leads to a
  change rather than changing it, so that a score being built never sees the set change.
- Launches wait for their answer, which says whether the launch waits for the next bar, or why it could not play, as the
  transport's pages expect; every other command is sent and not waited for.
- What plays comes back as a Status after every tick while anything plays and once as it stops, and each score built as a
  notice; the tracker carries a status's elapsed times on to the moment it draws, by the system's monotonic clock, which both
  processes share, and keeps the visualizer's notes of the last second.
"""

import atexit
import collections
import multiprocessing
import os
import signal
import threading
import time

from llamatron.model.file.song_file_error import SongFileError
from llamatron.realtime.render_process import process as render_process
from llamatron.realtime.render_process.playback import Status
from llamatron.realtime.render_process.process import run_playback
from llamatron.realtime.render_process.score_builder import Built
from llamatron.realtime.render_process.set_changes import changed_items
from llamatron.realtime.sender_process import process as sender_process
from llamatron.realtime.sender_process.process import SenderNotStarted
from llamatron.realtime.synth_process.load import SharedLoad
from llamatron.user_strings import errors

# How long the tracker waits for the render process to start, for a launch's answer, and for it to close.
START_SECONDS = 15.0
ANSWER_SECONDS = 15.0
CLOSE_SECONDS = 1.0
# How many statuses the tracker keeps for the visualizer, about a second of them.
HEARD_STATUSES = 50
# How many built scores' notices the tracker keeps.
BUILT_KEPT = 8
# The status of a render process where nothing plays.
SILENT = Status(0.0, 0.0, False, (), frozenset(), frozenset(), {}, {}, {}, None, None, None, (), {})


class PlaybackNotStarted(SenderNotStarted):
    """The render process did not start or did not answer, so nothing can play, which a page tells as it tells a sender that did not start."""


class PlaybackProcess:
    """The tracker's side of the render process, answering the transport as a LocalPlayback does."""

    __slots__ = ('_recording', '_lead', '_lock', '_connection', '_lifeline', '_process', '_sent', '_latest', '_built', '_status', '_statuses', '_playing', '_ended',
                 '_load')

    def __init__(self, *, lead, recording=False):
        """lead is how far ahead of now a launch from silence starts; with recording, the Realtime Sender Process records what it would send, which close() hands back."""
        self._recording = recording
        self._lead = lead
        # Sending and starting are done from the screen's thread and from the thread that gets ready under the start screen.
        self._lock = threading.Lock()
        self._connection = None
        # The end of the lifeline the tracker holds and never writes to (render_process.watch_lifeline).
        self._lifeline = None
        self._process = None
        # The set's data as last sent, whose parts are compared by identity to find what changed, and as last taken.
        self._sent = {}
        self._latest = {}
        self._built = collections.OrderedDict()
        self._status = SILENT
        self._statuses = collections.deque(maxlen=HEARD_STATUSES)
        # What the render process's player plays a score of, as the tracker last told it.
        self._playing = None
        self._ended = False
        # Where the built-in synths' sender writes their load (synth_process/load.py), made with the process.
        self._load = None

    def start(self):
        """Start the render process, unless it was started, and wait until it is ready, raising PlaybackNotStarted when it is not."""
        with self._lock:
            if self._process is None:
                self._spawn()

    def _spawn(self):
        context = multiprocessing.get_context(sender_process.SPAWN)
        self._connection, far_end = context.Pipe()
        far_lifeline, self._lifeline = context.Pipe(duplex=False)
        self._load = SharedLoad(context=context)
        arguments = dict(connection=far_end, lifeline=far_lifeline, lead=self._lead, recording=self._recording, load=self._load)
        self._process = context.Process(target=run_playback, kwargs=arguments)
        with sender_process.real_standard_error():
            self._process.start()
        # However the tracker ends, the render process and its sender end too, before Python waits for its child processes.
        atexit.register(self.close)
        if not self._connection.poll(START_SECONDS) or self._connection.recv() != (render_process.READY,):
            self._process.terminate()
            self._process = None
            raise PlaybackNotStarted(errors.ERR_PLAYBACK_DID_NOT_START)

    def synth_load(self):
        """Return the built-in synths' last load report, or None where none has come."""
        if self._load is None:
            return None
        return self._load.read()

    def get_process_id(self):
        """Return the render process's id, or None before it starts, for a test that ends it as a crash would."""
        if self._process is None:
            return None
        return self._process.pid

    def is_ready(self):
        """Return whether the render process has started and nothing is starting it now, so that asking it something will not wait for it to start."""
        return self._process is not None and not self._lock.locked()

    def has_ended(self):
        """Return whether the render process ended without being closed, which is a bug the tracker shows."""
        if not self._ended and self._process is not None and not self._process.is_alive():
            self._ended = True
        return self._ended

    # The set and its scores.

    def take_set(self, data):
        """Take the set's data, which crosses as the items that changed with the next build or launch, the two that need it."""
        self._latest = data

    def build(self, wanted):
        self._send_set()
        self._send(render_process.BUILD, wanted)

    def built(self, wanted):
        self._receive()
        return self._built.get(wanted)

    def has_score(self, wanted):
        return self._playing == wanted

    # Playing.

    def launch(self, *, wanted, launch, ports):
        """Ask the render process to play what a launch names, and wait for its answer: whether it waits for the next bar, or
        SongFileError or SenderNotStarted with why it could not play."""
        self._send_set()
        self._send(render_process.LAUNCH, wanted, launch, ports)
        answer = self._answer()
        if answer[0] == render_process.REFUSED:
            _kind, kind, words = answer
            if kind == render_process.REFUSED_SONG:
                raise SongFileError(words)
            raise SenderNotStarted(words)
        _kind, waits, status = answer
        self._take_status(status)
        self._playing = wanted
        return waits

    def apply(self, *, wanted, responsiveness, scene_map, track_map):
        self._send(render_process.APPLY, wanted, responsiveness, scene_map, track_map)
        self._playing = wanted

    def use_ports(self, ports, *, renewed=()):
        self._send(render_process.PORTS, list(ports), list(renewed))

    def silence(self, *, ports, channels):
        self._tell(render_process.SILENCE, list(ports), list(channels))

    def stop_clip(self, track):
        self._tell(render_process.STOP_CLIP, track)

    def stop_all(self):
        self._tell(render_process.STOP_ALL)
        self._status = SILENT

    def forget(self):
        self._tell(render_process.FORGET)
        self._status = SILENT
        self._playing = None

    def close(self):
        """End the render process and its sender, returning what a recording sender sent, or None.

        The render process is asked first, so that every note sounding gets its note off, and given CLOSE_SECONDS to answer and
        end; then its whole process group, the sender among it, is ended outright, whatever state it is in, so that a stuck
        or hung process never keeps the tracker from quitting, Ctrl+C included."""
        if self._process is None:
            return None
        result = None
        if self._process.is_alive():
            result = self._ask_to_close()
        self._process.join(CLOSE_SECONDS)
        end_process_group(self._process)
        self._process.join(CLOSE_SECONDS)
        self._connection.close()
        # Only once the render process has ended, since its watcher ends it the moment the lifeline goes.
        self._lifeline.close()
        self._process = None
        return result

    def _ask_to_close(self):
        """Ask the render process to close, and return what its recording sender sent, or None when it does not answer in time."""
        self._send(render_process.CLOSE)
        deadline = time.monotonic() + CLOSE_SECONDS
        try:
            while self._connection.poll(max(deadline - time.monotonic(), 0.0)):
                message = self._connection.recv()
                if message[0] == render_process.CLOSED:
                    return message[1]
        except (BrokenPipeError, EOFError, OSError):
            return None
        return None

    def tick(self):
        """Take in what the render process has said since."""
        self._receive()

    # What plays, from the latest status, its elapsed times carried on to now.

    def is_playing(self):
        self._receive()
        return self._status.playing

    def playing_scenes(self):
        return list(self._status.scenes)

    def is_clip_playing(self, *, index, track):
        return (index, track) in self._status.clips

    def is_track_sounding(self, track):
        return track in self._status.sounding

    def scene_elapsed(self, index):
        return self._carried(self._status.scene_elapsed.get(index))

    def clip_elapsed(self, *, index, track):
        return self._carried(self._status.clip_elapsed.get((index, track)))

    def repeats_left(self, *, index, track):
        return self._status.repeats_left.get((index, track))

    def song_position(self):
        return self._carried(self._status.song_position)

    def song_seconds(self):
        return self._status.song_seconds

    def seconds_per_quarter(self):
        return self._status.seconds_per_quarter

    def heard(self, *, since):
        """Return the player's clock at the latest status and the notes heard since an earlier moment of it, from the statuses kept."""
        newer = [status for status in self._statuses if since is None or status.now > since]
        held = {}
        started = collections.defaultdict(list)
        for status in newer:
            for track, notes, _held in status.heard:
                started[track] += notes
        for track, _notes, notes in self._status.heard:
            held[track] = notes
        heard = [(track, started.get(track, []), held.get(track, [])) for track in {*started, *held}]
        return self._status.now, heard

    def draw_places(self, *, scene, seconds):
        """Return where every draw stands in the first scene that plays, as the latest status says."""
        return self._status.draw_places

    def get_player(self):
        """Return None: the player is in the render process."""
        return None

    # Underneath.

    def _carried(self, seconds):
        """Return a time the latest status gave, carried on to now by the system's monotonic clock, or None."""
        if seconds is None:
            return None
        return seconds + time.monotonic() - self._status.at

    def _send_set(self):
        """Send the set's items that changed since the last sent."""
        changes, removed = changed_items(before=self._sent, after=self._latest)
        if changes or removed:
            self._send(render_process.SET, changes, removed)
        self._sent = self._latest

    def _tell(self, *message):
        """Send a message that means nothing to a render process not yet started, which plays nothing: a stop, a forget or a silence, whose channels nothing sounds on."""
        if self._process is not None:
            self._send(*message)

    def _send(self, *message):
        """Send a message to the render process, starting it first where it has not started."""
        self.start()
        try:
            with self._lock:
                self._connection.send(message)
        except (BrokenPipeError, EOFError, OSError):
            self._ended = True

    def _receive(self):
        """Take every message waiting from the render process."""
        try:
            while self._connection is not None and self._connection.poll():
                self._take(self._connection.recv())
        except (BrokenPipeError, EOFError, OSError):
            self._ended = True

    def _answer(self):
        """Wait for the render process's answer to a launch or a close, taking what else it says meanwhile, and return it, or None when it never comes."""
        deadline = time.monotonic() + ANSWER_SECONDS
        try:
            while self._connection.poll(max(deadline - time.monotonic(), 0.0)):
                message = self._connection.recv()
                if message[0] in (render_process.LAUNCHED, render_process.REFUSED, render_process.CLOSED):
                    return message
                self._take(message)
        except (BrokenPipeError, EOFError, OSError):
            self._ended = True
        raise PlaybackNotStarted(errors.ERR_PLAYBACK_DID_NOT_ANSWER)

    def _take(self, message):
        if message[0] == render_process.STATUS:
            self._take_status(message[1])
        elif message[0] == render_process.BUILT:
            _kind, wanted, problem = message
            self._built[wanted] = Built(problem=problem)
            while len(self._built) > BUILT_KEPT:
                self._built.popitem(last=False)

    def _take_status(self, status):
        self._status = status
        self._statuses.append(status)


def end_process_group(process):
    """End a render process and every process it started, its Realtime Sender Process among them, which share its process group
    (render_process.run_playback), or the render process alone where the system has no process groups."""
    if not hasattr(os, 'killpg'):
        if process.is_alive():
            process.kill()
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        # The group has ended already, or the process never led one.
        return
