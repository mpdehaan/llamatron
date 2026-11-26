# LFOs

An LFO, a low-frequency oscillator, is a slow or fast wobble, as a player's
hand shaking the pitch for vibrato or turning a knob back and forth. The LFOs
tab holds four, each off until switched on; what each one moves is set in the
[Mod Matrix](MOD_MATRIX.md).

![The LFOs tab](../screenshots/synth_lfos.svg)

Shape is Sine, Triangle, Saw up, Saw down, Square, or Sample & Hold, a new
random value each cycle. Rate is how fast it cycles, from a slow sweep to a
buzz fast enough for chip vibrato and trills. Retrigger starts its cycle again
with each note, so that every note's vibrato starts the same way; Each scene
starts it again whenever a scene starts, so that a slow sweep lines up with
the song.

## How the LFOs Are Built

An instrument's LFOs are shared by all its notes, as on most synthesizers.
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
