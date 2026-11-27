# Effects for a Real-Time Synthesizer

A chapter on the time-based, modulation, space, tone and lo-fi effects a synthesizer carries in its effect chain:
delay-line infrastructure, chorus, ensemble, flanger, phaser, tremolo and auto-pan, the rotary speaker, algorithmic
reverbs (Schroeder and Moorer, feedback delay networks, the Griesinger-Dattorro plate, the 1980s studio-reverb style),
the spring reverb, tape echo, telephone and radio colour, stutter and beat repeat, equalisers, a multiband "spectral"
band filter, and a wandering-delay "variance" effect. Each section gives what a musician hears, the principle, the
algorithm with its constants, the open implementations that realise it (with licences), the cost per sample, and the
hazards in an audio callback that must not allocate or lock. Tape saturation, wow and flutter are treated in
`TAPE.md`; delay lines, multi-tap delays and the bucket-brigade device at more length in `DELAYS.md`.

## 1. Delay-Line Infrastructure

Nearly every effect here is a delay line read in some way, so the line's quality decides theirs.

- **Storage.** A circular buffer of a power-of-two length, indexed with a mask, allocated when the effect is built.
  Single-precision storage is ample; 16-bit storage halves memory and is itself a colour (`pichenettes/eurorack`,
  `clouds/dsp/fx/` stores its reverb in 16 bits at 32 kHz).
- **Fractional reads.** A modulated delay must read between samples:
  - *Linear interpolation*: two reads, one multiply-add. It low-passes the signal slightly by an amount that depends on
    the fraction, so a modulated read gains a faint, moving dullness; fine for chorus at long delays.
  - *Cubic (Hermite or Lagrange third order)*: four reads, about ten operations; flat to well above 10 kHz. The usual
    choice for flangers and short modulated delays.
  - *First-order all-pass interpolation (Thiran)*: flat magnitude, but its state makes it unsuitable when the fraction
    jumps; good for fixed fractional tunings (a string's length) rather than modulation.
  - *Windowed sinc*: 8 to 32 taps from a precomputed table indexed by fraction; transparent, used where pitch-shifting
    reads must be clean (Surge's `sst-basic-blocks/dsp/SSESincDelayLine.h`, GPL-3.0-or-later; the rotary speaker of
    `sst-effects`).
- **Modulation and pitch.** Reading a delay whose time changes at a rate `dτ/dt` shifts pitch by the ratio
  `1 - dτ/dt`. A sinusoidal delay modulation of depth D seconds (peak) at frequency fm gives a peak pitch deviation
  ratio of `2π fm D`: 1 ms at 1 Hz is 0.0063, about 11 cents; 3 ms at 0.5 Hz is about 16 cents. This one formula sizes
  every chorus, vibrato and wandering delay.
- **Feedback safety.** A soft clip (tanh or rational) and a DC blocker inside every feedback loop keep a mis-set loop
  bounded; a gain ceiling below 1 (0.9 to 0.98) keeps feedback from running away.
- **Stereo.** A mono instrument's chain can stay mono until its first stereo effect; from there every effect processes
  two channels. Most stereo modulation effects are a mono delay line read at two modulated taps in antiphase or
  quadrature, so the second channel costs only a read.

## 2. Chorus

### 2.1 What it is

One voice is copied, the copy delayed by 5 to 30 ms and its delay swept slowly, then mixed back: the slight pitch and
timing difference makes one player sound like several. Depth of 1 to 5 ms, rate 0.1 to 3 Hz; slower and deeper is
lusher, faster is warble. Jon Dattorro's "Effect Design Part 2: Delay-line modulation and chorus" (JAES 1997) is the
foundational text: it covers the interpolation choices above, the "white chorus" with feedback, and a crucial detail,
that feedback taken from a fixed centre tap rather than from the modulated read keeps the feedback path from
compounding the pitch modulation into a seasick wobble.

### 2.2 Multi-voice choruses

- Two to eight voices, each a read of one delay line at its own base delay and LFO phase (evenly spaced phases, such
  as 0, 120 and 240 degrees for three), alternating left and right for stereo width.
- **Vital** (`mtytel/vital`, GPL-3.0): up to 16 voices in stereo pairs, each voice's delay a blend between two delay
  settings, an LFO per pair, a feedback path and a band-limiting filter on the wet signal.
- **Surge XT / sst-effects** (GPL-3.0-or-later): a multi-voice chorus with per-voice panning and sinc-interpolated
  reads.
- **Airwindows** (`airwindows/airwindows`, MIT): several small choruses and ensembles, readable and characterful.

### 2.3 The bucket-brigade character

The classic analog choruses of the 1970s and 1980s use a bucket-brigade device (BBD): a chain of capacitors passing a
sample along at a clock rate set by the modulation, so the delay is `N / (2 f_clock)`. Their sound comes from the
anti-alias and reconstruction filters around the chip (steep low-passes around 8 to 10 kHz, moving relative to the
clock), the clock's own aliasing at long delays, a compander's breathing, and a little noise. Holters and Parker ("A
combined model for a bucket brigade device and its input and output filters", DAFx 2018) give the efficient model:
the input and output filters expressed as parallel complex one-poles evaluated at the clock instants, the delay line
running at the clock rate. `chowdsp_utils`, module `chowdsp_dsp_utils/Delay/BBD` (GPL-3.0) realises it. Cost: a
handful of complex one-poles per clock tick plus bookkeeping, roughly 40 to 80 operations a sample for a stereo pair.

### 2.4 The string ensemble

The 1970s string machines run their divided-down saws through an "ensemble": three BBD lines whose delays are swept
by two LFOs mixed, a slow one near 0.6 Hz and a fast one near 6 Hz, at three phases 120 degrees apart, the three lines
summed into two outputs. The fast component gives shimmer, the slow one the wide drift. Cheap: one line, three reads.

### 2.5 Cost and hazards

A three-voice stereo chorus with cubic reads: about 3 x 12 operations a sample plus the LFOs (control rate). Hazards:
linear interpolation's moving dullness at short delays; modulating feedback paths; clicks if delay jumps when a tempo
or depth changes abruptly (smooth the delay target).

## 3. Flanger

A delay of 0.1 to 10 ms mixed with the dry sound makes a comb filter with notches at odd multiples of `1/(2τ)`;
sweeping τ sweeps the notches, the jet-plane whoosh. Feedback (positive or negative, up to ±0.95) sharpens the comb
into resonant peaks; negative feedback moves the peaks to odd harmonics of `1/(2τ)` and sounds hollower.

- **Through-zero flanging** imitates two tape machines, one passing the other: the dry path is itself delayed by a
  fixed offset (say 5 ms) and the wet delay sweeps from below to above it, so the comb passes through zero delay and
  the cancellation is total for an instant. Needs a delayed dry path, so it adds latency equal to the offset.
- **Interpolation matters more than in a chorus**: the comb's notches are deep only if both paths are equally bright,
  so cubic or sinc reads are the norm.
- **Open:** `sst-effects/Flanger.h` (GPL-3.0-or-later, read for this chapter): four combs a channel, LFO phases spread
  evenly, LFO shapes including a smoothed sample-and-hold, voices spaced in pitch so that the combs can form chords
  (an "arpeggio" mode that steps the comb pitches), feedback with high-frequency damping.
- **Cost:** 15 to 25 operations a sample a channel.

## 4. Phaser

A cascade of first-order all-pass filters shifts phase without changing level; mixed with the dry signal, the
frequencies where the cascade's phase reaches odd multiples of 180 degrees cancel. N stages give N/2 notches; sweeping
the all-passes' break frequency (exponentially, over two to four octaves, by an LFO at 0.05 to 5 Hz) sweeps them.
Feedback from the cascade's output to its input sharpens notches into peaks.

- **Spacing.** All stages at one frequency give harmonically unrelated, closely bunched notches (the classic four- and
  six-stage pedals). Spreading the stages' frequencies spreads the notches and sounds more like a flanger.
- **Analog character.** The pedal phasers use JFETs or OTAs as variable resistors; a JFET's resistance depends on its
  drain-source voltage, so loud signals shift the notches (a level-dependent wobble), and its control law is
  nonlinear, so the sweep lingers at one end. Modelled by warping the LFO and adding a small signal-dependent term to
  the break frequency.
- **Modulation-safe stages.** A one-pole all-pass in zero-delay form (`y = 2 lp(x) - x` with a TPT low-pass) stays
  smooth under fast sweeps.
- **Open:** `sst-effects/Phaser.h` (GPL-3.0-or-later, read for this chapter): stages are biquad all-passes whose
  centres are spread as `2^((i+1) 2/N)` around the centre, a sharpness control on Q, stereo LFO offset, feedback scaled
  by 0.95, and a tone low-pass and high-pass on the wet path; Vital's `src/synthesis/effects/phaser.cpp` (GPL-3.0);
  the Faust library's phaser functions (licence per function, noted in each).
- **Cost:** 4 to 12 stages of 3 to 5 operations, about 20 to 60 operations a sample a channel.

## 5. Tremolo and Auto-Pan

- **Tremolo.** Gain multiplied by `1 - depth (1 - lfo)/2` with an LFO from 0 to 1. Amplifier tremolos are not
  sinusoidal: the bias-modulated tube tremolo is slightly asymmetric; the optical tremolo lights a photocell, giving the
  vactrol's fast-on, slow-off shape, a softer, throbbing pulse (the cell model of `QUALITY_RESEARCH.md`, section 8).
- **Harmonic tremolo.** A crossover (around 500 Hz to 1 kHz) splits the signal; the low and high bands are amplitude
  modulated in antiphase and summed, giving a phasey, rotating pulse rather than a level change.
- **Auto-pan.** A mono source placed by an LFO with a constant-power law: `L = cos(θ)`, `R = sin(θ)`, θ swept over 0 to
  π/2; the quadrature oscillator gives both at once. Tempo-synced rates and a shape control (sine to square, with a
  slew so the square does not click).
- **Cost:** a few operations a sample.

## 6. The Rotary Speaker

### 6.1 What it is

A cabinet with a rotating horn for the treble and a rotating drum (a baffle in front of a downward-facing woofer) for
the bass, split by a passive crossover near 800 Hz. As each rotor turns, its sound comes closer and goes away
(Doppler pitch shift), points toward and away from the listener (amplitude and spectral modulation) and reflects off
the cabinet and room. Two speeds, slow ("chorale") and fast ("tremolo"); on switching, the light horn reaches its new
speed in about a second, the heavy drum in several seconds, and this acceleration, the sound sweeping up through
speeds, is the gesture players use. A tube amplifier in the cabinet is often overdriven.

### 6.2 The physics and its literature

Smith, Serafin, Abel and Berners ("Doppler simulation and the rotating loudspeaker", DAFx 2002) model each rotor as a
moving source read from a delay line whose length follows the source-to-microphone distance, with an angle-dependent
filter for the horn's directivity. Herrera, Hanson and Abel ("Discrete time emulation of the rotating loudspeaker",
AES 2009) refine the directivity as a time-varying FIR. The essential parts:

- **Crossover.** A second-order low-pass and high-pass near 800 Hz.
- **Doppler.** For a rotor of radius r spinning at angular velocity ω and a microphone at distance d, the path length
  is `sqrt(d² + r² - 2 d r cos(ω t))`; the delay is that over the speed of sound. Horn radius around 0.15 to 0.2 m.
- **Amplitude and directivity.** The horn is a directional source: level and brightness peak when it faces the
  microphone. The drum is a baffle, its modulation more amplitude than pitch.
- **Reflections.** Several delayed, filtered copies (cabinet walls) at their own Doppler phases thicken the sound.
- **Inertia.** Each rotor's speed approaches its target exponentially with separate time constants for speeding up and
  slowing down.
- **Two microphones** (left and right, at an angle) give the stereo spread; mono is their sum.

### 6.3 The open implementation read for this chapter

`setBfree` (`pantherb/setBfree`, `b_whirl/whirl.c`, GPL-2.0-or-later), the most complete open model:

| Rotor | Slow | Fast | Speed-up time constant | Slow-down time constant | Radius |
| --- | --- | --- | --- | --- | --- |
| Horn | 40.32 rpm | 423.36 rpm | 0.161 s | 0.321 s | 0.192 m |
| Drum | 36.0 rpm | 357.3 rpm | 4.127 s | 1.371 s | 0.220 m |

Microphone distance 0.42 m, speed of sound 340 m/s. The horn's path is shaped by a low-pass at 4.5 kHz and a low shelf
at 300 Hz (both cut 30 dB), the drum's by a high shelf at about 812 Hz cutting 39 dB, a crossover made of shaping
filters rather than a textbook split. Doppler is precomputed as tables of displacement against angle from the geometry;
each rotor writes into delay buffers at fractional positions (spacing plus displacement), with six reflection paths a
rotor (horn spacings 12, 18, 53, 50, 106 and 116 samples; drum 36, 39, 79, 86, 123 and 116), each with a first-order
filter, and a five-tap directivity response for the horn after the Smith et al. paper. Speed updates once a block by
`1 - exp(-1/(rate_blocks τ))`. A small leakage of the dry signal (0.15 x 0.7) reaches both outputs. Stereo comes from
the microphone angle and a width control.

`sst-effects/RotarySpeaker.h` (GPL-3.0-or-later, read for this chapter) is lighter: a mono sum through a selectable
drive with gain compensation, an 800 Hz split and a further 200 Hz split (the lowest band left unmodulated), the horn
band read from a sinc-interpolated delay with a base of 1.8 ms scaled by a Doppler amount and the left and right
distances from a quadrature LFO, horn tremolo of `(1 - a) + a dot` with `a = 0.6 tremolo`, the drum band amplitude
modulated, no inertia model (speed changes are smoothed only).

### 6.4 Cost

Horn: two fractional reads (left, right) with cubic or sinc interpolation, plus reflections; drum: two reads;
crossover and directivity filters; the drive. About 60 to 150 operations a sample for a stereo output, more with
reflections. The geometry can be tabulated by angle so that no `sqrt` or `cos` runs per sample.

## 7. Algorithmic Reverbs

### 7.1 Principles

Välimäki, Parker, Savioja, Smith and Abel, "Fifty years of artificial reverberation" (IEEE TASLP 2012) surveys the
field. A room's response has early reflections (sparse, the first 50 to 100 ms) and a late tail (dense, exponentially
decaying, frequency-dependent decay). An algorithmic reverb builds the late tail from recirculating delays and
all-passes whose echo density grows quickly, with a low-pass in each loop so that highs die first.

- **Schroeder (1962) and Moorer (1979).** Parallel feedback combs (each with a one-pole low-pass in its loop, Moorer's
  addition) followed by series all-passes. **Freeverb** (by Jezar, public domain): eight parallel low-pass
  combs at 1116, 1188, 1277, 1356, 1422, 1491, 1557 and 1617 samples (44.1 kHz), four series all-passes at 556, 441,
  341 and 225 with gain 0.5, the right channel's lengths 23 samples longer for decorrelation; room size sets the
  combs' feedback, damping their low-passes. Freeverb3 (GPL-2.0-or-later) extends it with many algorithms.
- **Feedback delay networks** (Jot and Chaigne, "Digital delay networks for designing artificial reverberators", AES
  1991; Stautner and Puckette 1982). N delay lines whose outputs mix through a lossless (orthogonal) matrix back into
  their inputs, each with an absorption filter set so that every line decays at the same rate in dB per second
  (`gain = 10^(-3 delay / T60)` at each frequency). A Hadamard or Householder matrix mixes N lines in `N log N` or `2N`
  operations. Mutually prime lengths avoid coincident echoes. Vital's reverb (`mtytel/vital`, GPL-3.0, read for this
  chapter) is a 16-line network with an all-pass in each line (feedback 0.6), lines modulated by a chorus LFO,
  low and high shelves in the loop, and a size control scaling lengths by powers of two.
- **Nested all-pass loops (Griesinger, Dattorro).** A loop ("tank") of all-passes and delays fed by a diffuser; output
  taps read from many points of the tank. See 7.2.

### 7.2 The Griesinger-Dattorro plate

Jon Dattorro, "Effect Design Part 1: Reverberator and other filters" (JAES 1997), publishes a plate-class reverb in
the style of the 1980s studio reverberators, at a 29761 Hz design rate; its lengths scale by `fs / 29761`. Structure:

1. **Pre-delay**, then a one-pole **bandwidth** low-pass (coefficient 0.9995).
2. **Input diffusers**: four all-passes in series, 142 and 107 samples at coefficient 0.75, 379 and 277 at 0.625.
3. **The tank**, two halves in a figure-of-eight, each half's end feeding the other's start:
   - left: a *modulated* all-pass of 672 samples (decay diffusion 1, coefficient -0.70, its length swept by up to 16
     samples at about 1 Hz), a delay of 4453, a one-pole **damping** low-pass (coefficient 0.0005), a gain of *decay*
     (0.5 default), an all-pass of 1800 (decay diffusion 2, coefficient `clamp(decay + 0.15, 0.25, 0.5)`), a delay of
     3720, a gain of decay;
   - right: the same with 908, 4217, 2656 and 3163.
4. **Output taps**, seven a side, scaled by 0.6. Left: +266 and +2974 from the right half's first delay, -1913 from
   its second all-pass, +1996 from its second delay, -1990 from the left half's first delay, -187 from its second
   all-pass, -1066 from its second delay. Right: the mirror image, +353 and +3627 from the left half's first delay,
   -1228 from its second all-pass, +2673 from its second delay, -2111 from the right half's first delay, -335 from its
   second all-pass, -121 from its second delay.

The modulated all-passes smear the tank's modes so that no metallic ring builds up, and give the faint chorus of the
style. `pichenettes/eurorack`, `clouds/dsp/fx/reverb.h` (MIT, read for this chapter) realises the same Griesinger
topology at 32 kHz with its own lengths (input all-passes 113, 162, 241 and 399; tank all-passes 1653, 2038, 1913 and
1663; delays 3411 and 4782), a single diffusion coefficient (0.625), two slow LFOs (0.5 and 0.3 Hz) modulating the
first diffuser and one tank delay, and 16-bit storage. Dattorro's paper also discusses the centre-tap feedback chorus
of 2.1. Cost: about 12 delay reads and writes, 8 all-passes, two one-poles, 14 output taps: about 60 operations a
sample for a stereo output, under 100 KB of memory at 48 kHz.

### 7.3 The 1980s studio-reverb "random hall"

The digital reverberators of the 1980s kept their tanks small (memory was dear) and hid it with **random modulation
of delay lengths**: each tank delay's read point wanders smoothly and independently, so the modes never settle and the
tail sounds larger and lusher, at the price of slight pitch movement. Freeverb3's "progenitor" algorithms
(GPL-2.0-or-later) reconstruct this family: nested all-pass tanks with randomised modulation, bass and treble
multipliers of the decay time, and a crossover so that the low end decays at its own rate. The modulation source is a
smoothed random value per delay, at 0.5 to 2 Hz with depth of a few samples to tens of samples.

### 7.4 Frequency-dependent decay

A one-pole damping filter gives highs a shorter decay than lows but not independently set. A first-order shelf in the
loop (or a two-band split with separate loop gains) lets "bass multiplier" and "treble multiplier" set the decay of
each band as a ratio of the mid decay, the control the studio reverbs offered.

### 7.5 Hazards

- Feedback gain at or above one in any loop (keep a ceiling, compute gains from T60 and the loop's length).
- Denormals in the tank as the tail dies (flush).
- Mono compatibility: left and right taps must not cancel when summed.
- A "freeze" mode (decay at one, input muted) must still be bounded by the loop's soft clip.

## 8. Spring Reverb

### 8.1 What it is

A spring tank: a transducer twists one end of one to three helical springs, a pickup at the other end reads them. The
spring is strongly dispersive: in the band below a transition frequency of a few kilohertz, group delay rises with
frequency, so each echo of a click arrives as a chirp, and repeated round trips give the dripping, "boing" sound of
surf guitar and dub. Kicking the tank makes a crash.

### 8.2 The model

Välimäki, Parker and Abel ("Parametric spring reverberation effect", JAES 2010) and Parker ("Efficient dispersion
generation structures for spring reverb emulation", EURASIP Journal on Advances in Signal Processing, 2011) build the
dispersion from **stretched all-passes**: first-order all-passes with each unit delay replaced by `z^-K`,
`H(z) = (a + z^-K)/(1 + a z^-K)`, cascaded tens to a hundred times. The cascade's group delay rises across each of its
K bands, giving the chirp; a feedback delay supplies the round trips; a low-pass at 4 to 5 kHz the transducers' limit;
a modulated delay length slight irregularity. The high-frequency part of the response is a separate, weaker chirp
path.

### 8.3 The open implementation read for this chapter

Surge XT's spring reverb by Jatin Chowdhury (`surge-synthesizer/surge`, `src/common/dsp/effects/chowdsp/
spring_reverb/`, GPL-3.0-or-later):

- Input mixed with the delayed feedback, `input - g * delayed`, through a fast tanh, then a 40 Hz DC blocker.
- One feedback delay of `1000 + 0.099 size fs` samples; feedback gain `0.001^(delay / (T60 fs))`, so it decays 60 dB in
  T60, with `T60 = 0.5 s * 9^(0.95 decay - 0.7 (1 - size²))` (about 0.5 to 4.5 s).
- A cascade of all-passes in four-lane vectors, gains alternating `g, -g, g, -g` with `g = 0.5 - 0.4 spin`, each of
  `0.35 ms + 3 ms size`: the dispersion, its strength set by "spin".
- A reflection network skewed by `0.95 reflections²`.
- A state-variable damping low-pass from 18 kHz down to 4 kHz.
- **Shake**: a half-cycle sine burst of 0.5 to 1 ms (longer with size), amplitude 2, written into the input: the tank
  being knocked.
- **Chaos**: each parameter update picks a random delay offset up to 7 % of the delay, smoothed over 50 ms and scaled
  by chaos cubed.

Cost: a dozen to a few dozen all-passes (each 2 to 3 operations, vectorisable four at a time), one delay, a tanh, a
low-pass: about 60 to 120 operations a sample a channel. A stereo spring is two decorrelated instances.

## 9. Tape Echo

A tape loop passing a record head, then one to four playback heads, then an erase head; the echo time is the head
spacing over the tape speed, so changing the speed changes every head's time together and the echoes glide in pitch,
the dub gesture. Each pass through the loop adds tape saturation, head-bump, high-frequency loss and wow and flutter.
The read is a delay line whose read distance is the head spacing divided by a smoothed speed; the speed's smoothing
(tens to hundreds of milliseconds, the motor's inertia) sets the glide. Feedback runs through the tape model and a
tone filter. The saturation, loss filters and wow and flutter are in `TAPE.md`; the multi-head tap structure is a multi-tap
delay (`DELAYS.md`).

## 10. Telephone, Radio and Small-Speaker Colour

- **Band limit.** A narrowband telephone channel passes about 300 to 3400 Hz; a fourth-order band-pass (two high-pass
  and two low-pass sections) gives the steep edges that make the effect read instantly.
- **Small transducers.** A peak of 4 to 8 dB around 1 to 2 kHz (the earpiece's resonance), and a soft, asymmetric clip
  (the carbon microphone's nonlinearity) driven by level.
- **Codec.** Downsampling to 8 kHz with a hold, and 8-bit mu-law or A-law companding (the ITU G.711 curves:
  `y = sign(x) ln(1 + μ|x|)/ln(1 + μ)` with μ = 255), so quantisation noise follows the level.
- **Line.** Hum at 50 or 60 Hz and its harmonics, faint noise, occasional dropouts.
- **Radio variants.** AM radio: a band-pass of 100 Hz to 5 kHz, light compression; walkie-talkie: 300 Hz to 3 kHz,
  heavy clipping, a squelch noise burst at note end.
- **Cost:** a few biquads and a curve: 20 to 40 operations a sample.

## 11. Stutter and Beat Repeat

A captured slice of the recent sound replayed in rhythm: the glitch fills of electronic music.

- **Capture.** A circular buffer always records (a few seconds, allocated at build time). On a trigger quantised to
  the song's grid, a slice of a chosen length (1/4 to 1/64 of a beat, or triplet) is marked.
- **Repeat.** The slice is replayed from its start for the stutter's duration; each repeat gets a short fade-in and
  fade-out (1 to 5 ms raised cosine) so the joins do not click; the slice length may shrink each repeat (a roll that
  accelerates) or its pitch fall (each repeat read slower), or a gate may cut each repeat short.
- **Reverse and pitch.** Reading backward or at another speed needs fractional reads (cubic).
- **Determinism.** Triggers placed by the song's clock, not by wall time, so exports match playback.
- **Cost:** one or two reads a sample with a window: under 20 operations.

## 12. Equalisers

- **Biquad sections.** The peaking, shelving, low-pass and high-pass designs of Robert Bristow-Johnson's freely
  published "Audio EQ Cookbook" are the common reference. Cost: five multiply-adds a band a channel. Near Nyquist the
  bilinear transform cramps the response (a high bell at 12 kHz narrows and its gain is wrong); Martin Vicanek's
  "Matched second order digital filters" (2016) matches the analog magnitude across the band, including at Nyquist, at
  the same running cost (only the coefficient formulas change).
- **Modulated EQ.** A biquad's direct form misbehaves when its coefficients move quickly; the trapezoidal SVF (Simper
  2013; `QUALITY_RESEARCH.md`, section 3.2) produces bells and shelves as mixes of its outputs and stays smooth under
  modulation, so an EQ whose frequencies move from a modulator uses it.
- **Crossovers.** Linkwitz-Riley fourth-order splits (two cascaded Butterworth second-order sections) sum to an
  all-pass, flat in magnitude, which a multiband effect needs. `sst-filters/LinkwitzRiley.h` (GPL-3.0-or-later).
- **Tilt.** A single control that raises one end and lowers the other around a pivot (first-order shelves, opposite
  gains): a broad tone control.
- **Open:** `sst-effects`, `include/sst/voice-effects/eq/` (GPL-3.0-or-later): a parametric N-band, a six-band
  graphic, a morphing EQ and a tilt EQ.

## 13. Filter as an Effect

Any voice filter (`QUALITY_RESEARCH.md`, section 3) placed after the voices, with its cutoff moved by an LFO, a
tempo-synced envelope, or an envelope follower of the input (auto-wah: a follower with fast attack, 50 to 200 ms
release, moving a resonant band-pass or low-pass over two to three octaves). One shared filter on the summed signal
costs one filter, not one per voice, but sweeps all notes together.

## 14. The Spectral Band Filter

### 14.1 What it is

A bank of band-pass filters splits the sound into bands, each band's level set and moved independently, then sums
them: a graphic EQ whose sliders move, a fixed-filter bank of the kind 1970s studios used for formant shifting, and the
analysis half of a vocoder. Moving the band levels in patterns (a tilt sweeping, odd bands against even, a spectral
"comb" walking up) gives motion without pitch change.

### 14.2 Designs

- **Parallel band-passes.** Each band a second-order (or cascaded fourth-order) band-pass at its centre, constant Q.
  The sum is not flat: there are ripples between bands, and the phase of neighbouring bands differs, so with all
  levels at unity the sound is coloured. Acceptable as an effect; Q of about 2 to 4 for third-octave bands, 1.4 for
  octave bands.
- **Crossover trees.** Successive Linkwitz-Riley splits give bands whose sum is an all-pass: unity levels reproduce the
  input exactly in magnitude, so the effect is transparent at rest. Each split costs two second-order sections a path;
  N bands need N - 1 splits plus all-pass phase compensation of the earlier bands so that every band arrives with the
  same phase.
- **Multirate banks.** Low bands are filtered at a decimated rate (half, a quarter), since a band-pass at 100 Hz does
  not need 48 kHz; this saves most of the cost of many bands. `pichenettes/eurorack`, `warps/dsp/filter_bank.cc` (MIT,
  read for this chapter): 20 bands, groups of bands at decimation factors with their own sample-rate converters, each
  band a cascade of state-variable passes, and per-band delay lines compensating group delay so the bands sum aligned.
- **Short-time Fourier transform.** Exact and flexible (any number of bands), but adds a frame of latency (10 to 40 ms)
  and costs an FFT a hop; a filter bank suits a synthesizer's chain better.
- **Open:** Surge XT's vocoder (GPL-3.0-or-later) runs up to 20 biquad bands in SIMD; the Faust standard library's
  filter banks (Julius O. Smith's `mth_octave_filterbank` among them; licence per function, mostly MIT-style).

### 14.3 Band levels and smoothing

Each band's gain needs a smoother (5 to 20 ms) to avoid zipper noise as it moves; gains in decibels interpolated in
the log domain sound even. Pattern generators over the bands (a moving peak, a tilt, a random walk per band) are
control-rate work.

### 14.4 Cost

Twelve parallel second-order bands: about 60 operations a sample; with multirate decimation of the lower half, about
40. A crossover tree of 8 bands with phase compensation: about 100.

## 15. Variance: a Wandering Short Delay and a Recovering Low-Pass Gate

### 15.1 What it is

A subtle, lo-fi undercurrent: the sound passed through a short delay whose time wanders at random, so its pitch drifts
irregularly by a few cents, then through a low-pass gate whose opening follows the sound's own envelope, so that the
softened, slightly blurred tone brightens again on each attack. It belongs with worn tape and old samplers, but its
wander is random rather than periodic.

### 15.2 The wander

- **Delay range.** A base of 5 to 20 ms keeps the delay from reading as an echo; depth of 0.1 to 2 ms keeps it subtle.
  By the formula of section 1, a wander of 1 ms changing over about 0.3 s moves pitch by roughly 0.3 % (5 cents).
- **The random source.** New random targets arrive at random times, as a Poisson process whose mean rate is the "Rate"
  (0.1 to 10 a second: rare to nervous), each a value drawn uniformly or from a normal distribution within the depth.
  The delay approaches each target through a smoother whose time is the "Damp": a critically damped two-pole (two
  one-poles in series) makes each wander an S-curve with no overshoot; a very long damp turns the wander into a slow
  drift no longer heard as pitch. Pitch deviation is the derivative of the delay, so a two-pole smoother keeps pitch
  itself continuous, where a one-pole would jump pitch at each new target.
- **Alternatives.** Smoothed noise (white noise through a two-pole low-pass), or a sum of two or three slow sines at
  unrelated rates (cheaper, but periodic over long times); the Poisson-target form gives the most musical "event"
  character.

### 15.3 The recovery low-pass gate

An envelope follower of the dry input (fast attack, 1 to 5 ms; release 50 to 300 ms) drives the cutoff of a one- or
two-pole low-pass from a dark floor (800 Hz to 2 kHz) up to fully open, scaled by "LPG"; through the vactrol model
(`QUALITY_RESEARCH.md`, section 8) the opening has the cell's fast-on, slow-off shape and its level-dependence. Loud
attacks come through bright; tails and quiet notes are soft and slightly smeared.

### 15.4 Cost

One delay read with cubic interpolation, a two-pole smoother at control rate, an envelope follower, a one- or two-pole
filter with coefficients from a table: about 30 operations a sample.

## 16. Summary of Costs

| Effect | Operations a sample (stereo out) | Memory at 48 kHz |
| --- | --- | --- |
| Chorus, 3 voices, cubic | 40 to 60 | a few KB |
| BBD chorus model | 80 to 160 | a few KB |
| Flanger, 4 combs a channel | 30 to 50 | under 4 KB |
| Phaser, 8 stages | 40 to 80 | none |
| Tremolo, auto-pan | under 10 | none |
| Rotary speaker | 60 to 150 | under 64 KB |
| Freeverb-style | about 50 | about 100 KB |
| Dattorro plate | about 60 | under 100 KB |
| 16-line FDN | 100 to 200 | 200 KB to 1 MB |
| Spring | 120 to 240 | under 200 KB |
| Telephone | 20 to 40 | none |
| Stutter | under 20 | about 1 MB for several seconds |
| Parametric EQ, 4 bands | 40 | none |
| Spectral band filter, 12 bands | 80 to 120 | small |
| Variance | about 30 | under 8 KB |
