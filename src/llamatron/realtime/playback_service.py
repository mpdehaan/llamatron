# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What the tracker uses of real-time playback, the other half of its front door beside realtime_names.py: the Realtime Sender
Process and the error of its not starting, the player's two ways of running, what a score is made from and what is launched,
the route of a track's events, the clock, FluidSynth, and the ports this computer lists."""

from llamatron.realtime.devices.fluidsynth import FluidSynth, FluidSynthInstallation, installation, installed
from llamatron.realtime.devices.ports import output_port_names
from llamatron.realtime.render_process.playback import LocalPlayback, PlayRequest, Wanted
from llamatron.realtime.render_process.playback_process import PlaybackProcess
from llamatron.realtime.render_process.timeline import Route
from llamatron.realtime.sender_process.engine import MonotonicClock
from llamatron.realtime.sender_process.process import RealtimeMIDISenderProcess, SenderNotStarted

# Everything the tracker may take from here.
__all__ = [
    'FluidSynth', 'FluidSynthInstallation', 'installation', 'installed', 'output_port_names', 'LocalPlayback', 'PlayRequest', 'Wanted',
    'PlaybackProcess', 'Route', 'MonotonicClock', 'RealtimeMIDISenderProcess', 'SenderNotStarted',
]
