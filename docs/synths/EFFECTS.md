# Effects

The FX tab holds two effects, each empty until chosen, applied in order to the
whole instrument's sound after its voices are added together. Each has a Mix,
how much of the effect is heard against the sound that went into it.

![The FX tab](../screenshots/synth_effects.svg)

## Drive

Drive shapes the sound by a curve, as an overdriven amplifier or a pedal does,
by its Amount. Soft and Warm saturate, rounding the peaks off smoothly; Warm
leans to one side first, so that the two halves of the wave are rounded
differently and even harmonics are added, as a tube's are. Leaning a sound and
then taking the lean's own level away again keeps silence silent, and the
curve is scaled so that it reaches full on one side and stays under it on the
other. Hard clips the peaks flat. Fold folds the wave back on itself past full
scale, and Wrap wraps it round to the other side, the harsh digital sounds of
cheap grooveboxes.

## Bitcrush

Bitcrush makes a sound lo-fi, as early samplers and game consoles were. Rate
holds each sample for as long as a lower sample rate would, so that high notes
alias into metallic tones; Bits rounds each sample to fewer bits, which adds a
gritty hiss that follows the sound.

## Planned

The agreed effects, by kind: Drive and Bitcrush for dirt, Bitcrush gaining a
gentle drive, a rate that can follow the note and its top bits as switches;
Legend and Spring for space; Chorus, Flanger, Phaser, Tremolo and Auto-pan,
and Rotary for motion; Tape, Tape Echo, Phone and Stutter for lo-fi and
glitch; and EQ and Filter for tone. The planned effects go in four FX blocks,
each with its own tab and presets.

Tape's wow is to be a moving read of a delay line: the sound is written into a
delay line as tape is written by a record head, and read back from a point
that drifts slowly back and forth, as a stretched tape's speed wavers, so that
the pitch bends a little and back. Since a delay line is read after the sound
has been written, the instrument's notes are started early by the delay's
length, so that the effect costs no lateness. Tape Echo shares the same code,
read at a fixed distance and fed back into itself for repeats.
