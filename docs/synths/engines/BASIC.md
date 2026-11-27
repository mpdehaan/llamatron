# Basic

Basic is the plainest of the synths: one oscillator, a Square, Saw, Sine,
Triangle or Pulse wave, given a Detune in cents, a Fine from −10.0 to +10.0
cents in tenths, and a Level, through snappy ADSR envelopes and a ladder filter
each note's own. It is the quickest way to hear what one wave sounds like
through the filter and the envelopes; for several oscillators beating against
each other, the thick lead and the bass with weight, use
[Asheville](ASHEVILLE.md).

![The Oscillators tab of Basic](../../screenshots/synth_basic.svg)

## How Basic Is Built

Each oscillator works out its wave every sample from where it is in its
cycle. A naive saw or square holds harmonics far above what a sample rate can
carry, and they fold back down as harsh, out-of-tune whistles; so each jump of
the saw, the square and the pulse is smoothed over the four samples around it
by a polyBLEP, a small correction that takes away the folding, and each corner
of the triangle is rounded over the same four samples by its partner, a
polyBLAMP, while the sine needs nothing. The waves stay full and bright at every
pitch, with no octave tables and no change of tone from one octave to the
next, and they stay clean wherever the pitch goes, under glide, vibrato and
audio-rate FM. The pulse's width can move smoothly, as the Mod Matrix's Pulse
width moves it.

The oscillator's read speed is worked out from the pitch and the detune once,
and again only when something moves the pitch, so that a held note costs a few
operations a sample. The Mod Matrix's Detune moves the oscillator by its
Detune, so that a route can bend it away from the note and back.
