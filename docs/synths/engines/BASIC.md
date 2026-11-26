# Basic

Basic is the plainest of the synths: up to three oscillators, each a Square,
Saw, Sine, Triangle or Pulse wave, or Off, given a Detune in cents and a
Level, through snappy ADSR envelopes and a ladder filter each note's own. Two
saws detuned a little apart are the classic thick lead; a square an octave
under a saw is a bass with weight.

![The Oscillators tab of Basic](../../screenshots/synth_basic.svg)

## How Basic Is Built

Each oscillator reads a wavetable, one cycle of its waveform, at the speed its
note's pitch asks, interpolating between the table's two nearest samples so
that a slow note is smooth. A naive saw or square holds harmonics far above
what a sample rate can carry, and they fold back down as harsh, out-of-tune
whistles; so each waveform has a table for every octave, each made from the
waveform's Fourier series with only the harmonics that stay under half the
sample rate at that octave's top note, turned into one cycle by an inverse
Fourier transform. A note reads the table of its octave. The pulse isn't a
table of its own: it is one saw less another shifted by the pulse's width, so
that its width can move smoothly, as the Mod Matrix's Pulse width moves it,
and stay as clean as the saw.

The read speeds of the three oscillators are worked out from the pitch and the
detune once, and again only when something moves the pitch, so that a held
note costs a table read and an addition per oscillator per sample. Detune
spreads by the Mod Matrix's Detune, so that a route can widen or narrow the
chorus of two oscillators.
