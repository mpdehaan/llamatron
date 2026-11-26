# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""What the tracker uses of real-time playback, the other half of its front door beside realtime_names.py: the Realtime Sender
Process and the error of its not starting, the player's two ways of running, what a score is made from and what is launched,
the route of a track's events, the clock, FluidSynth, the ports this computer lists, and whether built-in sound may play here."""

from llamatron.realtime.devices.fluidsynth import FluidSynth, FluidSynthInstallation, installation, installed, is_disabled as fluidsynth_disabled, plays_in_daemon as fluidsynth_in_daemon
from llamatron.realtime.devices.ports import output_port_names
from llamatron.realtime.render_process.playback import LocalPlayback, PlayRequest, Wanted
from llamatron.realtime.render_process.playback_process import PlaybackProcess
from llamatron.realtime.render_process.timeline import Route
from llamatron.realtime.sender_process.engine import MonotonicClock
from llamatron.realtime.sender_process.process import RealtimeMIDISenderProcess, SenderNotStarted
from llamatron.realtime.sender_process.rust_sender import made_sender
from llamatron.realtime.synth_process.daemon import built_in_renderer
from llamatron.realtime.synth_process.process import synthesis_available

# Everything the tracker may take from here.
__all__ = [
    'built_in_renderer',
    'made_sender',
    'fluidsynth_disabled',
    'fluidsynth_in_daemon',
    'FluidSynth', 'FluidSynthInstallation', 'installation', 'installed', 'output_port_names', 'LocalPlayback', 'PlayRequest', 'Wanted',
    'PlaybackProcess', 'Route', 'MonotonicClock', 'RealtimeMIDISenderProcess', 'SenderNotStarted',
    'synthesis_available',
]
