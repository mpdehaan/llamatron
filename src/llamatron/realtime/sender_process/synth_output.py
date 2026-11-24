# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A built-in port of the Realtime Sender Process: the notes the engine sends it go to the Synthesis Process rather than to
MIDI, each stamped with its moment, sixteen built-in instruments a port, one a channel.

The Synthesis Process plays a note its delay after the moment it is given, so this port gives each the moment less that delay,
and the sender starts its timeline that delay later for every port: MIDI and built-in sound then land together, each event at
the moment the engine stamps it with, and a flush takes back exactly what a CoreMIDI port would, the notes not yet heard.
"""

import time

from llamatron.realtime import realtime_names
from llamatron.realtime.render_process import timeline
from llamatron.realtime.sender_process import engine as sender_engine
from llamatron.realtime.sender_process.outputs import ScheduledOutput
from llamatron.realtime.synth_process import engine as synth_engine

# The controllers that end every note of a channel: all sound off cuts at once, all notes off releases.
ENDING_CONTROLS = (sender_engine.ALL_NOTES_OFF, sender_engine.ALL_SOUND_OFF)


class SynthOutput(ScheduledOutput):
    """A built-in port: its group of sixteen instruments of one Synthesis Process, which several ports share."""

    __slots__ = ('_synthesis', '_first')

    def __init__(self, *, synthesis, group):
        self._synthesis = synthesis
        self._first = group * realtime_names.INSTRUMENTS_PER_PORT

    def set_sound(self, *, channel, spec):
        """Give the instrument on a channel its sound, compiled by the Synthesis Process before its next note."""
        self._synthesis.set_instrument(number=self._first + channel, spec=spec)

    def send(self, data):
        self.send_at(data=data, at=time.perf_counter())

    def send_at(self, *, data, at):
        note = synth_note(data=data, when=at - self._synthesis.delay, first=self._first)
        if note is not None:
            self._synthesis.notes([note])

    def flush(self):
        """Take back every note of the port's instruments not yet heard."""
        self._synthesis.forget(first=self._first, last=self._first + realtime_names.INSTRUMENTS_PER_PORT - 1,
                               after=time.perf_counter() - self._synthesis.delay)

    def close(self):
        self._synthesis.close()


def synth_note(*, data, when, first):
    """Return a MIDI message as the Synthesis Process takes a note, (seconds, kind, instrument, pitch, velocity), or None for
    a message the built-in instruments do not play, such as a program change."""
    kind = data[0] & timeline.KIND_MASK
    instrument = first + (data[0] & timeline.CHANNEL_MASK)
    if kind == timeline.NOTE_ON and data[2] > timeline.NO_VELOCITY:
        return (when, synth_engine.NOTE_ON, instrument, data[1], data[2])
    if kind in (timeline.NOTE_ON, timeline.NOTE_OFF):
        return (when, synth_engine.NOTE_OFF, instrument, data[1], 0)
    if kind == timeline.CONTROL_CHANGE and data[1] in ENDING_CONTROLS:
        return (when, synth_engine.ALL_OFF, instrument, 0, 0)
    if kind == timeline.CONTROL_CHANGE and data[1] == timeline.SCENE_STARTED:
        return (when, synth_engine.SCENE_STARTED, instrument, 0, 0)
    return None
