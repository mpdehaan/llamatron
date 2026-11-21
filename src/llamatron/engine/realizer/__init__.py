# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Realizer: playing a song's composition objects into finished clips, which the exporters and real-time playback then read.

SongRealizer is where it starts: it writes out each scene, and has each track's clip slot played by
a ClipSlotPlayer, which plays its patterns a pass at a time with a PatternPlayer. The other classes
here are the parts those share: the order steps play in, registers, grabs and morphing.
"""
