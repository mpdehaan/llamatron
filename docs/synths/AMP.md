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

## Low-pass Gate

A vactrol in the amp's place, the note's last stage: one light-sensitive cell
that closes the sound and darkens it at once, as a struck or plucked thing
fades, the classic pluck and bonk of modular synthesizers. It is the same
gate as the Filter tab's ([Filters](FILTERS.md#low-pass-gate)), with the same
settings, but here it always closes when its note ends: its Trigger is
Trigger, a short flash at each note; Gate, lit while the note is held; or Env
1, whose level it follows through its cell. Its Mode adds VCA, the loudness
alone.

| Setting | Range | What it does |
| --- | --- | --- |
| Trigger | Trigger, Gate, Env 1 | What lights the cell. |
| Trigger time | 0.5 to 50 ms | How long the flash lasts, with Trigger. |
| Mode | VCA, Lowpass, Both | Loudness alone, the cutoff alone, or both together. |
| Signal | Oscillator, Ping, Both | The sound coming in, a short pulse each note, or both. |
| Ping time | 0.5 to 20 ms | How long the ping lasts, with a Ping. |
| Resonance | 0 to 100% | How much the Lowpass mode rings. |
| Open | 100 Hz to 16 kHz | The cutoff fully lit. |
| Key track | 0 to 100% | How far the cutoff follows the note. |
| Response | 0 to 100% | How fast the cell is, from fast to lazy. |
| Memory | 0 to 100% | How much of the last glow carries into the next note. |
| Age | 0 to 100% | An old cell: dimmer and slower. |
| Stability | 0 to 100% | How alike each note is. |

[Synths](../SYNTHS.md) lists every part of the built-in instruments.
