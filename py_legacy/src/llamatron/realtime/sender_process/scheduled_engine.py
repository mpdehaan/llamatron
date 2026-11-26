# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The playback engine for a scheduled port, CoreMIDI on macOS: each event is handed to the port a little ahead of its moment,
stamped with it, so that the system delivers it on time however late the Realtime Sender Process wakes.

What is handed ahead can still be taken back, and what is heard is what the engine that sends each event as it comes would send.
Stopping a clip, stopping everything and an edit heard at once forget events the port may already hold: the engine flushes the
port, which takes back everything there still to come, hands back again what it keeps, and undoes, latest first, what handing the
forgotten events did to the notes it counts as sounding; the channels it silences on a stop are those of the events whose moments
have come, so that a stop silences exactly what has sounded. Ctrl+T forgets nothing, as the other engine forgets nothing: it silences now, and the notes handed to start later are
counted again once it has. One instant is uncertain: an event due within GUARD_SECONDS of a flush may have gone out or not. There
a note off is sent, kept or forgotten, since a second note off is harmless and a lost one leaves a note stuck; a note on forgotten
is ended with a note off, in case it went out; and any other event kept is taken to have gone out.
"""

from typing import NamedTuple

from llamatron.realtime.render_process import timeline
from llamatron.realtime.sender_process.engine import PlaybackEngine

# How far ahead of its moment each event is handed to the port. Under twenty busy processes for ten minutes the sender woke at
# worst about 10 ms late, so a tenth of a second leaves room many times over, and it bounds what a flush hands back again.
HORIZON_SECONDS = 0.1
# How near the moment of a flush an event's moment is uncertain to have gone out, CoreMIDI delivering within a tenth of a
# millisecond of its stamp.
GUARD_SECONDS = 0.001
# The kinds of forgotten event that are answered with a note off when their moments fall within the uncertain instant.
ENDED_AT_THE_INSTANT = (timeline.NOTE_ON, timeline.NOTE_OFF)


class Handed(NamedTuple):
    """An event handed to its port, with the tag that was sounding on its note before it, or None, to undo the handing."""

    event: object
    sounding_before: object


class ScheduledPlaybackEngine(PlaybackEngine):
    """Hands a timeline's events to scheduled outputs HORIZON_SECONDS ahead of their moments, and takes back what it forgets."""

    __slots__ = ('_handed', '_heard_channels')

    def __init__(self, *, clock, outputs):
        """outputs maps a port's name to its ScheduledOutput."""
        super().__init__(clock=clock, outputs=outputs)
        # The events handed to the ports whose moments may not have come, in the order they were handed.
        self._handed = []
        # The (port, channel) of every event let go of since everything last stopped, its moment long come.
        self._heard_channels = set()

    def next_action(self):
        due = self.next_due()
        if due is None:
            return None
        return due - HORIZON_SECONDS

    def spins(self):
        return False

    def send_due(self):
        """Hand the ports every event due within the horizon, and return how many were handed."""
        now = self.elapsed()
        if self._handed and self._handed[0].event.seconds < now - GUARD_SECONDS:
            self._let_go_before(now)
        return self._send_until(now + HORIZON_SECONDS)

    def handed(self):
        """Return the events handed to the ports whose moments may not have come."""
        return [handed.event for handed in self._handed]

    def forget(self, *, tag, after):
        super().forget(tag=tag, after=after)
        self._take_back(lambda event: event.tag == tag and event.seconds >= after)

    def stop_tag(self, tag):
        self._take_back(lambda event: event.tag == tag)
        super().stop_tag(tag)

    def stop_all(self):
        now = self.elapsed()
        self._let_go_before(now)
        self._channels_used = self._heard_channels | {(handed.event.port, handed.event.channel) for handed in self._handed if handed.event.seconds <= now}
        self._take_back(lambda event: True)
        self._heard_channels = set()
        super().stop_all()

    def silence(self, *, channels):
        super().silence(channels=channels)
        now = self.elapsed()
        silenced = set(channels)
        for handed in self._handed:
            if handed.event.seconds > now and (handed.event.port, handed.event.channel) in silenced:
                self._note_sounding(handed.event)

    def _send(self, event):
        self._handed.append(Handed(event, self._sounding.get((event.port, event.channel, event.number))))
        self._note_sounding(event)
        self._outputs[event.port].send_at(data=event.data(), at=self._started + event.seconds)

    def _let_go_before(self, now):
        """Let go of the handed events that have surely gone out, those due more than GUARD_SECONDS before now."""
        kept = []
        for handed in self._handed:
            if handed.event.seconds >= now - GUARD_SECONDS:
                kept.append(handed)
            else:
                self._heard_channels.add((handed.event.port, handed.event.channel))
        self._handed = kept

    def _take_back(self, drops):
        """Flush the ports holding a handed event that drops answers yes for, hand back again what is kept there, and undo, latest
        first, what handing the dropped events did."""
        now = self.elapsed()
        self._let_go_before(now)
        dropped = [handed for handed in self._handed if drops(handed.event)]
        if not dropped:
            return
        ports = {handed.event.port for handed in dropped}
        for port in ports:
            self._outputs[port].flush()
        self._handed = [handed for handed in self._handed if not drops(handed.event)]
        for handed in self._handed:
            event = handed.event
            if event.port in ports and (event.seconds > now + GUARD_SECONDS or event.kind == timeline.NOTE_OFF):
                self._outputs[event.port].send_at(data=event.data(), at=self._started + event.seconds)
        for handed in reversed(dropped):
            self._undo(handed=handed, now=now)

    def _undo(self, *, handed, now):
        """Undo what handing a dropped event did to the notes sounding, and send a note off for a note on or a note off of the
        uncertain instant."""
        event = handed.event
        key = (event.port, event.channel, event.number)
        if event.kind == timeline.NOTE_ON and self._sounding.get(key) == event.tag:
            self._restore_sounding(key=key, tag=handed.sounding_before)
        elif event.kind == timeline.NOTE_OFF and key not in self._sounding and event.seconds > now + GUARD_SECONDS:
            self._restore_sounding(key=key, tag=handed.sounding_before)
        if event.kind in ENDED_AT_THE_INSTANT and event.seconds <= now + GUARD_SECONDS:
            self._outputs[event.port].send([timeline.NOTE_OFF | event.channel, event.number, timeline.NO_VELOCITY])

    def _restore_sounding(self, *, key, tag):
        if tag is None:
            self._sounding.pop(key, None)
        else:
            self._sounding[key] = tag
