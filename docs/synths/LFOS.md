# LFOs

An LFO, a low-frequency oscillator, is a slow or fast wobble, as a player's
hand shaking the pitch for vibrato or turning a knob back and forth. The
Modulators tab holds four modulators, each off until switched on, and each
with a Type: LFO, the plain one, or LFO+, the same with more choices. What
each one moves is set in the [Mod Matrix](MOD_MATRIX.md).

![The Modulators tab](../screenshots/synth_lfos.svg)

Shape is Sine, Triangle, Saw up, Saw down, Square, or Sample & Hold, a new
random value each cycle. Speed chooses how fast a span the Rate covers, as the
range switch of a modular synthesizer's LFO does, and Rate, from 0 to 100%,
sweeps across it, each step a like change in octaves, its hertz shown beside
it, such as `74% (5.0 Hz)`:

| Speed | Rate's span | For |
| --- | --- | --- |
| Low | 0.01 Hz to 1 Hz | slow sweeps, a cycle of up to 100 seconds |
| Medium | 0.1 Hz to 20 Hz | vibrato, wobble and tremolo |
| High | 1 Hz to 100 Hz | trills, flutter, wobble turning to buzz |
| Very High | 20 Hz to 5 kHz | audio rate, for analog-style FM |

At Very High the LFO is fast enough to be heard as a tone of its own, so an
LFO routed to the pitch through the Mod Matrix makes the bright, clangorous
sidebands of analog FM, and to the cutoff or the amp, filter FM and AM. Its
Key switch, shown only at Very High, makes the Rate a ratio to each note's own
frequency, from 1:4 to 8:1, so that the modulation stays in tune across the
keyboard as an FM modulator does: 1:1 and 2:1 sound harmonic, 3:2 hollow, odd
ratios metallic. With Key off any rate can be set. At audio rate the saws and
the square are band-limited so that they do not alias, and however far an LFO
moves the pitch, no oscillator plays below MIDI's lowest note or above about
20 kHz. Retrigger starts its cycle again
with each note, so that every note's vibrato starts the same way; Each scene
starts it again whenever a scene starts, so that a slow sweep lines up with
the song.

## LFO+

An LFO+ is an LFO with three more choices, kept apart so that the plain LFO
stays simple. Its Shape adds Smooth random, a new random value each cycle
glided to rather than stepped, for a wandering drift where Sample & Hold
jumps. Its Speed adds Tempo, where the Rate becomes a division of the beat,
from 4/1 to 1/32, dotted or triplet, such as `1/8 dotted`, so that a wobble
or a tremolo stays in time with the song through every change of tempo and
every tempo ramp. And Fade in, from off to 10 seconds, raises the LFO's depth
after each note starts, as a violinist's vibrato grows into a held note: each
note fades in from its own start, so that short notes stay plain and long ones
bloom. Set back to LFO, a slot plays as a plain LFO but keeps what its LFO+
was set to.

## How the LFOs Are Built

An instrument's LFOs are shared by all its notes, as on most synthesizers,
except a Key LFO, which each note runs at its own ratio to its own pitch.
Each LFO keeps one running count of the cycles it has turned, and the shapes
are read straight from where in its cycle it is: a sine from the angle, a
triangle and saws from straight lines, a square from which half of the cycle
it is in. The values for a whole chunk of sound are worked out once, before
any voice is played, so that four LFOs cost the same however many notes read
them.

Sample & Hold doesn't draw a random number as it goes: when the instrument is
compiled, a long row of random values is drawn from a fixed seed, and each
cycle of the LFO reads the next one. So a Sample & Hold line is random to the
ear and yet the same at every playing, live and in a WAV export, and Retrigger
brings it back to the same place in the row.
