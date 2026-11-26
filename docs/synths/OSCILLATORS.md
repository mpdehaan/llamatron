# Oscillators

The Oscillators tab, the first of a built-in instrument's sound, holds the raw
tone: what the filter, the envelopes and the effects then shape. It is where
the engines differ most, and its Type chooses which oscillator it holds, so an
engine's oscillator can be given to another engine's envelopes and filter.
Each engine's page says how its oscillator is made.

Its Voice column, at the left, is the same for every engine, and is described
at the end of this page.

## Basic

![The Oscillators tab of Basic](../screenshots/synth_basic.svg)

[Basic](engines/BASIC.md) describes it.

## SID

![The Oscillators tab of SID](../screenshots/synth_sid.svg)

[SID](engines/SID.md) describes it.

## Pocket

![The Oscillators tab of Pocket](../screenshots/synth_pocket.svg)

[Pocket](engines/POCKET.md) describes it.

## Fishline

![The Oscillators tab of Fishline](../screenshots/synth_fishline.svg)

[Fishline](engines/FISHLINE.md) describes it.

## MechaDrum

![The Oscillators tab of MechaDrum](../screenshots/synth_mechadrum.svg)

[MechaDrum](engines/MECHADRUM.md) describes it.

## Voice Column

The Oscillators tab's Voice column holds what is the whole instrument's:
Volume; Voices, how many notes sound at once; Glide, on unless switched off,
whether the instrument slides into a glided step; Glide time, how long a note
takes to slide; and Filter,
Per note, each note its own filter as on a polysynth, or Shared, one filter
moved by the newest note, as on a paraphonic synth.

An instrument of one voice slides only where two notes overlap: a note that
starts while the last is still held slides to its pitch over the Glide time,
its envelopes going on, as a monosynth plays legato: a slid note restarts
neither its amp envelope nor its filter's, on every engine. With Glide off, every
note is struck afresh and the pattern's glided steps are ignored. Notes that
only touch,
one ending as the next starts, never slide; each is struck afresh. A step's
Glide switch on the pattern is what makes a note run into the next, so the
pattern says which notes slide and Glide time says how fast. An instrument of
several voices plays an overlapping note on a voice of its own.
