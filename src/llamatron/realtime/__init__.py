# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Real-time playback: the timeline of MIDI events a rendered grid becomes, the score of a song with each clip's events from its scene's start, the player that launches scenes and clips as the follow actions say, the engine that sends the events on time, the ports they go out of, the Realtime Sender Process, which runs the engine apart from the tracker, and FluidSynth, which the tracker starts when something plays through it.

Imports composition (for the follow actions), exporters (for the note timing the exports use), grid, playback (for the render) and support.
"""
