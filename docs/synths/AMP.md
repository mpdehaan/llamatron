# Amp

The Amp, or VCA, is the last part of every note before the instrument's
effects: it sets how loud the note sounds, opened by Env 1 as a key is
played and closed as Env 1 falls. Every voice has its own, as every voice of a
polysynth has its own VCA, and it always closes when its note ends, so that
no sound is left droning. It sits on the Amp tab, between the Filter and FX
tabs, in the order the sound flows: Oscillators, Filter, Amp, FX.

## Swappable Amps

An amp looks like the plainest part of a synthesizer, and on paper it only
turns the sound up and down. In a real instrument it is a circuit with a
character of its own. The discrete transistor amps of the classic monosynths
round off loud notes and leak a little of the sound when shut, part of those
instruments' warmth and drone. The chip amps of later polysynths and modular
synthesizers open along a steeper curve and saturate more softly. Here the
Amp's Type chooses the circuit, as an envelope's type chooses its shape, so
that an engine's oscillator and filter can be heard through another engine's
amp.

Each type saturates the signal itself, so that a loud note, a hot signal
coming from the filter and a high setting all push it alike, as on the
hardware. A quiet note passes through almost untouched.

Every type has a Response, how Env 1 opens it. At 0% the loudness follows the
envelope straight. Toward 100% it follows an exponential curve, so that a note
opens later and falls away faster, snappier and more percussive.

Each engine's preset chooses its Amp: Asheville starts on Transistor, the
others on Clean.

## Clean

A perfect amp, as the built-in synths have always had: at its defaults the
note comes out exactly as Env 1 shapes it. Its Character warms it. Turned up,
it rounds off and gently saturates the loudest moments, as warmer amps do,
leaving the quiet ones alone.

| Setting | Range | What it does |
| --- | --- | --- |
| Response | 0 to 100% | How Env 1 opens it, from linear to exponential. |
| Character | 0 to 100% | How warmly the loudest moments are rounded off; 0% is perfectly clean. |

## Transistor

The discrete amp of the classic monosynths. It warms and squashes the
loudest notes, its Drive pushing it harder, and its Bleed lets a little of the
sound through when it is shut, the faint drone under a held note's silence on
those instruments.

| Setting | Range | What it does |
| --- | --- | --- |
| Response | 0 to 100% | How Env 1 opens it, from linear to exponential. |
| Drive | 0 to 100% | How hard the loudest notes are pushed into saturation. |
| Bleed | 0 to 100% | How much leaks through when it is shut, at most 40 dB down. |

## OTA

The chip amp of the polysynths and modular synthesizers. It opens along a
steeper curve by default and saturates rounder than the Transistor, its Drive
pushing it harder.

| Setting | Range | What it does |
| --- | --- | --- |
| Response | 0 to 100% | How Env 1 opens it, from linear to exponential. |
| Drive | 0 to 100% | How hard the loudest notes are pushed into saturation. |

## Planned

The low-pass gate is to be an Amp type as well as a Filter type: a vactrol
that closes the sound and darkens it at once, as a struck or plucked thing
fades. Until then it is chosen on the Filter tab, where it is the note's amp
([Filters](FILTERS.md), "Low-pass Gate").

[Synths](../SYNTHS.md) lists every part of the built-in instruments.
