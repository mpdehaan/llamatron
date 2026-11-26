# Mod Matrix

The Mod Matrix says what moves what, as the patch cables of a modular
synthesizer do, laid out as a table. Its six slots are on the Mod Matrix tab.

![The Mod Matrix tab](../screenshots/synth_matrix.svg)

Each slot has a Source: an envelope, an LFO, the note's Velocity or Key, or a
Random value drawn for each note. A Via scales the source by a second one, so
that, for instance, an LFO moves the cutoff only as far as the note is loud.
Moves is what it moves, Pitch, Pulse width, Detune, Cutoff, Resonance or Amp,
and Amount how far, either way, as a share of what it moves. LFO 1 to Pitch is
vibrato, with a Square shape and a large Amount a chip trill; Velocity to
Cutoff makes harder notes brighter; Random to Detune makes each note a little
different.

## MIDI CC Sources

A knob on a controller, or a CC row of a pattern, can move the sound through
the matrix. The last entry of the Source and Via pickers is `MIDI CC`. Beside
each Source and Via stands a CC field: a dash where the slot reads anything
else, and the CC's number, from 0 to 127, where it reads a MIDI CC, 74 at
first. Right moves the cursor onto the number, where `[` and `]` step it and
ENTER types it. The CC's value, from 0 to 127, moves its destination from
nothing to the slot's full Amount. A track's CC rows reach its built-in
instrument as they reach any MIDI device, so a pattern whose CC row the track
sends as CC 74, with a slot reading CC 74 into Cutoff, opens and closes the
filter as it plays, live and in a WAV export alike. A CC starts at 0 until its
first message comes.

## How the Matrix Is Built

The routes every synth needs are wired in outside the matrix, as a
semi-modular synth's normalled connections are: Env 1 to the amp, Env 2 to the
cutoff through the filter's Env amount, Env 3 to the pitch through the
oscillator's Pitch env, and the key to the cutoff through Key track. So all
six slots stay free for movement of your own.

When an instrument is compiled, empty slots and slots of no amount are left
out, and each route keeps its source, its via, its destination and how far it
moves at the source's full value. Each sample, a voice reads only the sources
some route uses, multiplies each by its via, and adds what every route gives
each destination together, so that two routes to the cutoff add up. Pitch is
moved in semitones and the cutoff in octaves, so that a route sounds as wide
at a high note as at a low one.

## Planned

The agreed design has eight slots, the first two Gate to Env 1 and Gate to Env
2 by default, and each amount shown in its destination's own unit.
