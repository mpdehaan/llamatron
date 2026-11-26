# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""How General MIDI's channels are handed out to a song's tracks, which the General MIDI export and FluidSynth's playing share:
channel 10 for every drum track, and the other fifteen in turn for the rest, going round after the fifteenth."""

# The drum channel, 10 as people count it, and the melodic channels, as the bytes a MIDI message carries.
MIDI_CHANNELS = 16
DRUM_CHANNEL_BYTE = 9
MELODIC_CHANNEL_BYTES = [channel for channel in range(MIDI_CHANNELS) if channel != DRUM_CHANNEL_BYTE]


def general_midi_channels(drums):
    """Return the channel byte of each track, in order, given whether each is a drum track: the drum channel for a drum track,
    and the melodic channels in turn for the rest."""
    channels = []
    melodic = 0
    for drum in drums:
        if drum:
            channels.append(DRUM_CHANNEL_BYTE)
        else:
            channels.append(MELODIC_CHANNEL_BYTES[melodic % len(MELODIC_CHANNEL_BYTES)])
            melodic += 1
    return channels
