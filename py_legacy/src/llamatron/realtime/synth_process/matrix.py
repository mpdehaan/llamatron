# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""A built-in voice's mod matrix: six slots, each a source, a Via that scales it, a destination and a signed amount, routing
what moves to what is moved (.claude/notes/synthesis/MOD_MATRIX.md).

The sources are the three envelopes, the four LFOs, the note's velocity and key, and a random value drawn at each note; the
destinations are pitch, pulse width, detune spread, cutoff, resonance and amp, each in its own unit, an amount of 100% moving
it its whole range. The normalled routes live outside the matrix, so that its slots stay free: Env1 to the amp, Env2 to the
cutoff through the filter's Env amount, Env3 to pitch through the oscillators' Pitch env, the key to the cutoff through Key
track. The slots are compiled once into routes, the empty ones and those of no amount left out, and each chunk sums every
route into its destination, an array a sample or a number for the note. Speed rules this module, as it does the engine (the
user's yes).
"""

NONE = 'none'
ENV1 = 'env1'
ENV2 = 'env2'
ENV3 = 'env3'
LFO1 = 'lfo1'
LFO2 = 'lfo2'
LFO3 = 'lfo3'
LFO4 = 'lfo4'
VELOCITY = 'velocity'
KEY = 'key'
RANDOM = 'random'
PITCH = 'pitch'
PULSE_WIDTH = 'pulse_width'
DETUNE = 'detune'
CUTOFF = 'cutoff'
RESONANCE = 'resonance'
AMP = 'amp'
ENVELOPE_SOURCES = (ENV1, ENV2, ENV3)
LFO_SOURCES = (LFO1, LFO2, LFO3, LFO4)
# How far each destination moves at full amount, either way: two octaves of pitch, two fifths of a pulse's cycle, the
# oscillators' detune doubled or gone, six octaves of cutoff, the whole of resonance, and the amp doubled or silenced.
RANGES = {PITCH: 24.0, PULSE_WIDTH: 0.4, DETUNE: 1.0, CUTOFF: 6.0, RESONANCE: 1.0, AMP: 1.0}


class ModMatrix:
    """The matrix's routes, each (source, via or None, destination, how far it moves at the source's full value)."""

    __slots__ = ('routes', 'destinations')

    def __init__(self, slots=()):
        self.routes = []
        for slot in slots:
            source = slot['source']
            amount = slot['amount']
            if source == NONE or slot['destination'] == NONE or not amount:
                continue
            via = slot.get('via', NONE)
            self.routes.append((source, None if via == NONE else via, slot['destination'], amount * RANGES[slot['destination']]))
        self.destinations = frozenset(route[2] for route in self.routes)

    def uses(self, source):
        """Return whether any route reads a source, so that a voice works out only what is read."""
        return any(route[0] == source or route[1] == source for route in self.routes)

    def moved(self, sources):
        """Return what the routes give each destination they move, from the sources, each an array over the chunk or a number
        for the note: a dict of destination to an array or a number."""
        moved = {}
        for source, via, destination, reach in self.routes:
            value = sources[source] * reach
            if via is not None:
                value = value * sources[via]
            if destination in moved:
                moved[destination] = moved[destination] + value
            else:
                moved[destination] = value
        return moved


# What a patch with no slots holds.
NO_MATRIX = ModMatrix()
