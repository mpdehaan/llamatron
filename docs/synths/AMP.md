# Amp

The Amp is the last part of every note before the instrument's effects: it is
how loud the note sounds, opened by Env 1 as a key is played and closed as it
fades. Every voice has its own, as every voice of a polysynth has its own VCA,
and it always closes when its note ends, so no sound is left droning. Its Type
is the circuit it follows, on the Amp tab, between the Filter and FX tabs, in
the order the sound flows: Oscillators, Filter, Amp, FX.

| Type | What it is |
| --- | --- |
| Clean | A perfect amp. Character, turned up, rounds off and gently saturates the loudest moments, as warmer amps do, whether a note is loud or the sound coming in is hot. |
| Transistor | The discrete amp of the classic monosynths: it warms and squashes the loudest notes, Drive pushing it harder, and Bleed lets a little of the sound leak through when it is shut, part of those synths' drone. |
| OTA | The chip amp of the polysynths and modular synthesizers: it opens along a steeper curve and saturates rounder, Drive pushing it harder. |

Each has a Response, how Env 1 opens it: at 0% the loudness follows the
envelope straight, and toward 100% it follows an exponential curve, so a note
opens later and falls away faster, snappier and more percussive.

Each engine's preset chooses its Amp: Asheville starts on Transistor, the
others on Clean.

[Synths](../SYNTHS.md) lists every part of the built-in instruments.
