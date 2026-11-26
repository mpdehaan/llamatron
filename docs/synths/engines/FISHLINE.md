# Fishline

Fishline is the acid bass: one voice of a saw, or the square a transistor
shapes from it, through the [acid gate](../ENVELOPES.md#acid-gate) with its
accents, a short sweep into the squelchy [diode filter](../FILTERS.md#diode)
and a pedal's gentle [drive](../EFFECTS.md#drive), sliding from a note into
the next where the pattern's Glide switch carries it, over its circuit's slide
time. A note at the acid gate's Accent at velocity or louder is accented: its
filter opens further and falls fast, it swells for a moment, and a run of
accents climbs higher.

![The Oscillators tab of Fishline](../../screenshots/synth_fishline.svg)

## Stock and Modded

The Acid gate and the Diode filter each have a Circuit, Stock or Modded, after
the modifications players made to the original machine, so a Modded envelope
can play through a Stock filter. Fishline slides into a glided note over its
Glide time in the Voice column, 60 ms by default as the original circuit's
fixed slide, and longer for a lazy line.

## How Fishline Is Built

Fishline follows Open303, an open emulation of the acid bass by Robin Schmidt,
whose constants were measured from the circuit; [Credits](../../CREDITS.md)
names it. Its saw is a plain rising ramp in band-limited tables of its own.
Its square is made from that saw as the transistor makes it: the saw through a
very steep curve, offset so that it switches a little off the middle, then
shifted half a cycle and played at half the saw's level. Because the curve's
edge takes a fixed time, the square sounds like a pulse on low notes and more
like a saw on high ones, as the original's does. The oscillator's output is
turned over and coupled into the filter through a high-pass, as the circuit
couples it, which shapes the low end. Tuning shifts the whole voice by
semitones.

Fishline's character is in the parts its engine chooses around that
oscillator: the acid gate's accent and its charging capacitor, the Diode
filter with a high-pass inside its feedback, so that its resonance sings
rather than booms, and its one voice, so that a glided step slides into the
next without starting the envelopes again. Any of those can be swapped, and any of them can be given
to another engine.
