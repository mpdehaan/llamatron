# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The words real-time playback shares with the tracker, one half of its front door beside playback_service.py: FluidSynth's
port, the kinds of launch, and how many quarter notes a whole note holds, which the visualizer's beat follows."""

import os

# The MIDI port FluidSynth opens, named for this tracker alone, so that two trackers each find their own, and how
# every tracker's FluidSynth port starts, which the instrument editor leaves out of the ports it offers.
FLUIDSYNTH_PORT_PREFIX = 'llamatron FluidSynth'
FLUIDSYNTH_PORT = '{prefix} {pid}'.format(prefix=FLUIDSYNTH_PORT_PREFIX, pid=os.getpid())
# What a launch plays: a scene and every clip of it, one clip, or several clips of one scene together.
LAUNCH_SCENE = 'scene'
LAUNCH_CLIP = 'clip'
LAUNCH_CLIPS = 'clips'
# A whole note is four quarter notes, the beat the visualizer follows.
QUARTERS_PER_WHOLE = 4
