# SID

SID is one voice of an 8-bit sound chip: a Triangle, Saw, Pulse or Noise wave,
a pulse whose width can sweep, Ring or Sync from a second oscillator an
Interval away, and an Arpeggio of semitones stepped very fast, through the
chip's own [SID ADSR](../ENVELOPES.md#sid-adsr) envelope. It is the sound of
fast arpeggiated chords, buzzy sync leads and swept pulse basses.

![The Oscillators tab of SID](../../screenshots/synth_sid.svg)

## How SID Is Built

The triangle and saw are read from band-limited wavetables, as Basic's are,
and the pulse is one saw less another shifted by its width. PWM speed sweeps
the width up and down at a steady rate, bouncing back at its narrowest and its
widest, as players sweep the chip's width by hand in its programs.

Noise is the chip's own: a shift register of many bits, its feedback taken
from two of its bits by exclusive or and fed back in at the top as the
register shifts, and its output an eight-bit word read from scattered bits of
the register. The register is shifted once for each step of the note's cycle,
so that the noise is pitched by the note, from a low rumble to a high hiss.
The register's run of values is worked out once, when the program first needs
it, and stepped through after.

Modulation brings in a second oscillator an Interval above. Ring flips the
sign of the wave whenever the second oscillator is in its second half, the
chip's ring modulation, a bell-like clang. Sync restarts the wave each time
the second oscillator completes its cycle, so that the wave is read at its own
pitch inside the second oscillator's, the tearing lead of hard sync. The
Arpeggio steps through its semitones at the speed the chip's programs ran,
once a frame of a television picture, which is how one chip voice plays a
whole chord.
