# Synthesis Engines: Algorithms and Open Implementations

A chapter on the sound-generating engines of a software instrument beyond the subtractive voice: frequency and phase
modulation, stacked unison and chord voices, wavetables, additive and West Coast oscillators, organs (tonewheel and
transistor combo), string machines and synth brass, formant choirs and linear-predictive speech, physical models
(plucked, struck, bowed and blown), the piano, chip voices, bytebeat, noise and glitch voices, analog and digital drum
machines, and drones. Each section gives what a musician hears, the principle and algorithm, the open implementations
that realise it (with their licences), the cost per voice per sample in a real-time callback, and its hazards. The
analog building blocks (oscillator anti-aliasing, filters, envelopes, the low-pass gate, the analog drum circuits) are
in `QUALITY_RESEARCH.md`; the effects in `EFFECTS_RESEARCH.md`.

## 1. Frequency and Phase Modulation

### 1.1 Principle

John Chowning, "The synthesis of complex audio spectra by means of frequency modulation" (JAES 1973). A carrier
sine's phase is modulated by another sine (the modulator): `y = sin(ωc t + I sin(ωm t))`. The spectrum has partials at
`ωc ± k ωm` with amplitudes given by Bessel functions `J_k(I)`; the modulation index I sets brightness, the
carrier-to-modulator ratio sets harmonicity (integer ratios harmonic, irrational ratios bell-like and metallic). An
envelope on I makes the brightness evolve as a struck or blown sound's does, which is the whole art of FM. In
practice instruments use **phase modulation** (adding the modulator to the carrier's phase rather than its
frequency), which is equivalent for sinusoids, keeps the carrier's pitch exact under DC in the modulator, and lets
operators be chained without drift.

### 1.2 Operators and algorithms

An operator is a sine oscillator with its own envelope and output level, a frequency ratio or fixed frequency, and
velocity and key scaling of its level. Four or six operators are wired by an **algorithm**: which modulate which, which
are carriers summed to the output, and which one feeds back into itself. The classic 1980s six-operator instruments
offered 32 algorithms; four-operator ones eight.

### 1.3 Feedback

An operator modulating its own phase with its previous output produces, as feedback rises, a saw-like then noisy
spectrum. A one-sample feedback loop oscillates at half the sample rate when strong; the open reconstruction of the
1980s six-operator instrument averages the last two outputs before feeding back, which places a zero at Nyquist and
tames it. In `asb2m10/dexed`, `source/msfa/fm_op_kernel.cc` (Apache-2.0, from the MSFA project,
read for this chapter): `scaled_fb = (y0 + y) >> (fb_shift + 1)`; `y0 = y`; `y = sin(phase + scaled_fb)`, with the
output scaled by a gain interpolated linearly across each block.

### 1.4 Fixed-point and log-domain detail

The same code keeps phase in 24-bit fixed point, reads a 1024-entry sine table storing value and delta pairs for
one-multiply interpolation, and works out each operator's gain from envelope and level in a logarithmic domain,
converted once a block by an exponential table, so that envelopes behave as the hardware's did (linear in decibels).
The original's envelopes have four rates and four levels per operator, their rates scaled by key. `pichenettes/
eurorack`, `plaits/dsp/fm/` (MIT) is a second, compact reading of the same six-operator voice with its algorithms,
envelopes and LFO, written for a small processor.

### 1.5 Aliasing

FM's bandwidth is about `2 (I fm + fm)` (Carson's rule). A high index on a high note puts energy above Nyquist and it
folds. Remedies: limit the index by key (scale index down above a pitch), run the operators at 2x for bright patches,
or accept it, since the original hardware aliased too and its character includes it.

### 1.6 Two- and four-operator FM and FM drums

- **Two-operator** voices (one modulator, one carrier, modulator feedback) already give electric pianos, basses and
  bells; the index from an envelope and velocity. `plaits/dsp/engine/fm_engine` (MIT) is a two-operator voice with
  feedback.
- **FM drums.** Kick: a sine with a fast exponential pitch drop and a short index burst for the click. Snare: a carrier
  near 180 to 250 Hz modulated at an inharmonic ratio with a fast-decaying index, plus noise. Hats and cymbals: high
  inharmonic ratios (such as 1:1.4 and 1:3.1) and high index, through a high-pass. Toms: like the kick with less drop.
  `pichenettes/eurorack`, `plaits/dsp/drums/synthetic_bass_drum.h` and `synthetic_snare_drum.h` (MIT) are compact
  digital drum voices of this kind.

### 1.7 Cost

A table-read operator with linear interpolation: about 6 operations; six operators and the algorithm's sums about 50 a
voice a sample, envelopes at block rate. Exponential gain conversion once a block.

## 2. Unison and Chord Voices

### 2.1 The stacked-saw lead

Many saws detuned around a note: the dance-music lead of the late 1990s and after. Adam Szabo's bachelor's thesis
(2010) measured the stacked-saw oscillator of a late-1990s virtual-analog synthesizer and published:

- seven saws, one at pitch and three pairs detuned symmetrically;
- a detune control mapped nonlinearly (an eleventh-order polynomial fit), slow at first and spreading fast near the
  top;
- a mix control setting the centre saw's level as `-0.55366 x + 0.99785` and the side saws' as
  `-0.73764 x² + 1.2841 x + 0.044372`;
- a high-pass at the fundamental to remove the sub-fundamental mud of aliasing in the original;
- free-running random phases at each note, so that no two notes start alike.

### 2.2 Unison in general

N voices of any waveform, detuned over a spread (linearly in cents, or by a curve that keeps the inner voices close),
panned across the stereo field when stereo exists, each with its own drift. Level normalisation of about `1/sqrt(N)`
keeps loudness even as N changes. Surge XT's oscillators (GPL-3.0-or-later) and Vital (GPL-3.0) both offer unison with
spread and stereo controls. Cost scales with N: seven polyBLEP saws are about 50 operations a voice.

### 2.3 Chord voices

One note plays a chord: a set of intervals above (and below) the played pitch, each a voice of the oscillator. Interval
sets: power chord (0, 7, 12), major (0, 4, 7), minor (0, 3, 7), sus2 and sus4, sevenths, sixths, ninths, stacked fourths
and fifths, octave stacks. Inversions and spread keep a chord from muddying in low registers (drop the third an octave
below a pitch, or open the voicing). `plaits/dsp/chords/chord_bank.cc` (MIT) holds a bank of chords with inversion
control and a voicing scheme that keeps voices within a span. Cost: the oscillator's cost times the chord's size.

## 3. Wavetable Synthesis

A wavetable is a sequence of single-cycle frames; a position control scans through them. Each frame needs mip levels
(`QUALITY_RESEARCH.md`, section 1.4); reading between frames interpolates linearly in the time domain (cheap; can
cancel partials whose phases differ between frames) or blends spectra (phase-aligned frames avoid the cancellation).
Vital (`mtytel/vital`, GPL-3.0) generates frames from wave, spectral and line sources and offers phase and spectral
"warps" (bending the phase read, shifting or stretching spectra) applied per sample or by table regeneration. Surge
XT's wavetable oscillator (GPL-3.0-or-later) uses band-limited tables per octave with interpolation between frames. Cost:
four table reads (two frames, two adjacent samples) and lerps, about 10 operations a voice; frame regeneration for
spectral warps is block-rate work.

## 4. Additive and West Coast Oscillators

### 4.1 Additive harmonic banks

A sum of sines at harmonics (or stretched partials), their levels from a few macro controls: a spectral centroid
(where the energy peaks), a width (how many partials around it), odd against even balance, and a tilt. Cheap sines come
from rotating phasors: each partial a complex number multiplied by its fixed rotation each sample (four multiplies and
two adds), renormalised occasionally, or from a Chebyshev recurrence `sin((n+1)x) = 2 cos x sin(nx) - sin((n-1)x)`,
which computes all harmonics of one fundamental with one multiply-add each. Partials above Nyquist are skipped.
`plaits/dsp/engine/additive_engine.h` (MIT) sums up to 24 or more harmonics with bump-shaped amplitude profiles.
Cost: 2 to 6 operations a partial; 32 partials about 100 a voice.

### 4.2 Complex oscillator, through-zero FM and wavefolding

The West Coast complex oscillator pairs a modulation oscillator and a principal one with linear FM, timbre by
wavefolding and a symmetry control. **Through-zero FM** lets the instantaneous frequency of the principal oscillator go
negative (the phase runs backward), so deep linear FM keeps its pitch centre instead of going flat; in a phase
accumulator this only needs the increment to be allowed to be negative and the waveform read to handle backward
wraps (with BLEP corrections whose sign follows the direction). **Wavefolding** reflects a sine past thresholds
several times: the multi-stage folders of 1970s West Coast instruments; Esqueda, Pöntynen, Parker and Bilbao ("Virtual
analog models of two classic wavefolder circuits", Applied Sciences 2017) give circuit models and their ADAA forms.
`chowdsp_waveshapers` has a West Coast folder model (GPL-3.0). Cost: a sine, a folder with ADAA (about 15
operations), 2x oversampling for deep folds.

## 5. Organs

### 5.1 The tonewheel organ

A motor drives 91 toothed wheels past electromagnetic pickups, each producing a near-sine at a pitch set by its gear
ratio (approximations of equal temperament, so slightly off in a fixed, characteristic way). Each key closes nine
contacts on nine busbars, one per drawbar footage: 16', 5 1/3', 8', 4', 2 2/3', 2', 1 3/5', 1 1/3' and 1' (the
fundamental's sub-octave, fifth, unison, octave, twelfth, fifteenth, seventeenth, nineteenth and twenty-second).
Drawbars set each footage's level in nine steps of about 3 dB. Character:

- **Foldback.** The wheels run out at both ends: the highest footages of the top keys fold back an octave, and the
  lowest wheels of the 16' are reused, so the timbre changes slightly across the keyboard.
- **Leakage and crosstalk.** Neighbouring wheels leak into each pickup at -40 to -60 dB, a faint halo of other pitches
  that is part of the sound.
- **Wheel waveform.** Not pure sines: the low wheels carry a little of their harmonics, the high wheels are nearly pure.
- **Key click.** The nine contacts close at slightly different moments and bounce, so each note starts with a short
  burst of broadband noise and switching transients; players value it, and a level control is usual.
- **Percussion.** A single-triggered (only when all keys were up) decaying copy of the second or third harmonic, fast
  (a few hundred milliseconds) or slow (about a second or more), normal or soft; enabling it steals the 1' drawbar on
  the original.
- **Vibrato and chorus scanner.** A mechanical scanner sweeps across taps of an LC delay line (about a millisecond in
  all) at about 7 Hz, three depths of vibrato, and chorus modes mixing the vibrato with the dry signal.
- **Preamp.** A tube preamplifier and the rotary speaker's amplifier, often driven (`EFFECTS_RESEARCH.md`, section 6).

`setBfree` (`pantherb/setBfree`, GPL-2.0-or-later) models all of this: a tone generator of the 91 wheels with their
gear ratios, crosstalk and per-wheel harmonics, nine busbars, key click, percussion, the scanner vibrato as an
interpolated delay, an overdrive, and the rotary speaker. Implementation note: run all 91 wheels (or the subset in use)
as one oscillator bank, each wheel once regardless of how many keys use it, then sum each key's nine contributions
through the drawbar gains into the busbars. Cost: about 91 table-read sines (about 300 operations) for the whole
instrument plus a few operations per sounding key-footage; full polyphony is nearly free beyond the bank.

### 5.2 The transistor combo organs

The 1960s combo organs are divide-down designs: twelve top-octave oscillators (one per pitch class), each divided by
flip-flops into the lower octaves, so every C on the keyboard is phase-locked to every other. The divided square waves
pass through RC filter networks ("tabs" or "stops": flute, reed, string, brass) that shape their spectra; keying is a
simple switch, with a little click. The British combo organ's reedy brightness and the Italian one's thinner, buzzier
voice come from their different filter networks and waveforms (the Italian design adds sharper pulse shapes). Vibrato
is a pitch LFO of about 5 to 7 Hz applied to the top oscillators, so it moves every note together. Implementation: twelve
band-limited oscillators (or one master and exact ratios), octave-divided waveforms generated by reading each at
power-of-two speeds from one phase (so phase lock is exact), per-tab fixed filters on the sum (one filter per tab
for the whole instrument, since keying is linear). Cost: tiny per note; the filters are per instrument.

## 6. String Machines and Synth Brass

### 6.1 String machine

The 1970s string ensembles: divide-down oscillators (as 5.2) giving phase-locked saw-like waves at 8' and 4', a gentle
attack and release envelope per key or for the whole keyboard (paraphonic), a fixed formant filter (a broad peak
around 1 to 2 kHz and a high cut), and the ensemble chorus (`EFFECTS_RESEARCH.md`, section 2.4), which is the sound.
The phase lock between octaves (every key's 4' locked to its 8') is what makes a played chord sound "organ-like"
before the ensemble thickens it.

### 6.2 Synth brass

The bright, stabbing brass of early-1980s keyboard anthems: two saws detuned a few cents, a low-pass filter whose
envelope has an attack slightly slower than the amplifier's (20 to 80 ms) and a strong amount, so each note "blooms"
open; little resonance; a pitch envelope starting 20 to 50 cents flat and rising over 30 to 80 ms (the lip settling);
slight vibrato after onset. A stab is the same with a short decay and no sustain. The vintage brass ensemble keyboards
add a divide-down source, a formant-style fixed filter and a "growl" (fast modulation at onset).

### 6.3 Physical brass

A lip-reed model: the lips as a mass-spring resonator driven by mouth pressure, the bore as a delay-line waveguide, the
bell as a high-pass reflection filter. Perry Cook's Synthesis ToolKit (`thestk/stk`, a permissive MIT-style licence)
has `Brass` built this way; it is sensitive to its parameters and needs tuning per register.

## 7. Choirs and Formant Voices

### 7.1 Formants

The vocal tract shapes a glottal source with resonances (formants). Peterson and Barney ("Control methods used in a
study of the vowels", JASA 1952) give average adult male formants, for example:

| Vowel | F1 | F2 | F3 |
| --- | --- | --- | --- |
| /i/ (beet) | 270 | 2290 | 3010 |
| /ɛ/ (bet) | 530 | 1840 | 2480 |
| /a/ (father) | 730 | 1090 | 2440 |
| /ɔ/ (bought) | 570 | 840 | 2410 |
| /u/ (boot) | 300 | 870 | 2240 |

Women's and children's formants are about 15 to 25 % higher. Bandwidths of about 60 to 120 Hz for F1 to F3. Sung vowels
shift toward an "ah" with a singer's formant (a cluster near 2.5 to 3 kHz) in trained voices.

### 7.2 Synthesis forms

- **Parallel band-pass bank**: the source through three to five band-passes at the formants, summed with their levels.
  Robust under modulation; each band an SVF (`QUALITY_RESEARCH.md`, 3.2).
- **Cascade**: formant resonators in series (Klatt, "Software for a cascade/parallel formant synthesizer", JASA 1980),
  which gives correct relative levels automatically for vowels.
- **FOF** (Rodet, the CHANT project, 1984): each glottal period triggers a grain per formant, a decaying sinusoid at the
  formant's frequency; elegant for singing, costlier with many grains.
- **Source.** A band-limited saw or pulse, or a glottal pulse model (Rosenberg's polynomial pulse, or the
  Liljencrants-Fant model) whose spectrum falls at about 12 dB an octave; a little aspiration noise; vibrato of 5 to 6
  Hz and a few tens of cents, with jitter.
- **Choir.** Several voices (4 to 8) each detuned a few cents with its own vibrato rate and phase and slight formant
  variation, through a chorus; or one voice through an ensemble effect.
- **Open:** Vital's formant filter (`mtytel/vital`, `src/synthesis/filters/formant_filter.cpp`, GPL-3.0) morphs
  between vowel sets; `plaits/dsp/speech/naive_speech_synth.h` (MIT) is a compact formant speech voice.

Cost: three to five SVFs and a source, 40 to 60 operations a voice.

## 8. Linear-Predictive Speech: the Talking-Toy Voice

### 8.1 Principle

The late-1970s talking toys used linear predictive coding: speech stored as frames of a tenth-order all-pole filter's
reflection coefficients, an energy and a pitch, played 40 frames a second (25 ms each) at an 8 kHz rate. A voiced frame
excites the filter with a periodic pulse at its pitch; an unvoiced frame (pitch zero) with noise. The coefficients are
quantised coarsely (energy about 4 bits, pitch about 6, the first two reflection coefficients 5 bits each, the next
five 4 bits and the last three 3 bits), which, with the 8 kHz rate and the lattice's fixed-point arithmetic, gives the
voice its buzzy, robotic character.

### 8.2 The lattice filter

A tenth-order all-pole lattice runs from the excitation `e10` down: `e_{i-1} = e_i - k_i s_{i-1}`, then the states
update upward `s_i = s_{i-1} + k_i e_{i-1}`, with `s_0 = e_0` the output. It is stable whenever every `|k_i| < 1`, so
interpolating reflection coefficients between frames is always safe, which is why the format used them.

### 8.3 The open implementations read for this chapter

`pichenettes/eurorack`, `plaits/dsp/speech/lpc_speech_synth.cc` (MIT): a ten-coefficient lattice at an internal 8 kHz;
the voiced excitation is a short tabulated pulse (signed 8-bit, read 32 entries a sample) restarted at each period with
a BLEP correction where the restart falls between samples; unvoiced noise is a random sign times the noise energy; the
excitation is scaled by 1.5 and the output clamped to ±2. Frames are blended linearly when interpolation is on, with
coefficients stored as integers and divided by their scales (32768 for k1 and k2, 128 for the rest). Pitch is
`(base + deviation * prosody) * shift`, clamped at the internal Nyquist. Talkie (`ArminJo/Talkie`, GPL-3.0) is a
library that plays the toy chips' original bitstreams with their coefficient tables.

### 8.4 Frames from formant targets

Frames need not come from recorded speech. From formant targets (frequencies F and bandwidths B for each of five
formants), each formant gives a pole pair at radius `r = exp(-π B / fs)` and angle `θ = 2π F / fs`; multiplying the
five second-order factors gives the tenth-order polynomial; the step-down (backward Levinson) recursion turns it into
reflection coefficients. Quantising those to the toy's bit widths reproduces its character; consonants are short
unvoiced or mixed frames with high-frequency targets (an "s" is noise with energy above 4 kHz, which at 8 kHz must be
folded to the top of the band).

### 8.5 Cost

A ten-stage lattice at 8 kHz is about 20 operations a sample of the internal rate; resampling to the output rate
(a polyphase filter or simple linear interpolation for lo-fi) dominates. Under 20 operations a voice a sample in all.

## 9. Physical Models

### 9.1 Plucked strings: Karplus-Strong

Karplus and Strong ("Digital synthesis of plucked-string and drum timbres", CMJ 1983): a delay line of length N filled
with noise, its output averaged with the previous sample and fed back; the averaging low-pass makes high partials
decay first, as a string's do. Jaffe and Smith ("Extensions of the Karplus-Strong plucked-string algorithm", CMJ 1983)
add:

- **tuning** by a first-order all-pass for the fractional part of the delay;
- **decay stretching** for low notes (a weighted average with weight away from one half);
- **pick position** by a comb on the excitation (`1 - z^-βN`, β the relative pluck point);
- **dynamic level** by a low-pass on the excitation (soft plucks duller);
- **stiffness** by all-pass dispersion in the loop (the slightly stretched partials of steel strings and pianos).

Commuted synthesis (Smith, 1993; Karjalainen, Välimäki and Jánosy, 1993) folds the instrument body's impulse response
into the excitation, so a short recorded or synthesized body response replaces the noise burst. `plaits/dsp/
physical_modelling/string.h` (MIT) adds dispersion, a damping filter and an optional curved-bridge nonlinearity (the
sitar-like buzz) to the loop. Karplus and Strong's drum variant flips the sign of each recirculated sample at random
with probability one half: a noisy, pitched drum. Cost: under 10 operations a voice a sample.

### 9.2 Modal synthesis: struck bars, membranes, bells

A struck object rings at its modes, each a damped sinusoid; a bank of two-pole resonators (or SVF band-passes) at the
mode frequencies, excited by a short mallet pulse, reproduces it. Mode ratios:

| Object | Mode ratios to the fundamental |
| --- | --- |
| Free-free bar (glockenspiel) | 1, 2.756, 5.404, 8.933 |
| Tuned marimba bar | about 1, 4, 10 (undercut to tune the overtones) |
| Circular membrane | 1, 1.594, 2.136, 2.296, 2.653, 2.918, 3.156 |
| Church bell (by name) | hum 0.5, prime 1, tierce 1.2, quint 1.5, nominal 2, then higher |

Higher modes decay faster. The strike position weights each mode by its shape at that point (a cosine for a string or
bar), and the mallet's hardness is the excitation's width: a raised-cosine pulse of 0.5 to 5 ms, narrower being
brighter. `pichenettes/eurorack`, `rings/dsp/resonator.cc` (MIT, read for this chapter): up to 64 SVF band-pass modes,
partial frequencies stretched by a "stiffness" increment that itself decays from mode to mode (so a negative
stiffness gives compressed, bell-like spacing and a positive one stretched, piano-like), a Q that falls mode by mode by
a loss factor set by brightness and structure, and a cosine amplitude per mode from the strike position. Cost: about 5
operations a mode; 32 modes about 160 a voice, or rendered once per hit for drums.

### 9.3 Bowed strings

A digital waveguide (two delay lines either side of the bow point, reflecting at the bridge and nut) with the bow as a
nonlinear friction junction: the string's velocity at the bow relative to the bow's velocity determines the friction
force through a hyperbolic or exponential curve, giving the stick-slip motion (Smith, "Physical Audio Signal
Processing", online book, CCRMA). Bow pressure and velocity set whether the note speaks, squeaks or crunches. STK's
`Bowed` (`thestk/stk`, MIT-style) and `elements/dsp/` of `pichenettes/eurorack` (MIT, its exciter's bow mode) realise it.
Cost: 20 to 40 operations a voice.

### 9.4 Blown pipes

A flute: a jet delay (the air jet crossing the embouchure), a cubic nonlinearity `x - x³` at the jet, a bore delay
line with a low-pass reflection, breath noise modulated by pressure; overblowing jumps registers. A clarinet: a reed
table (a clipped linear reflection coefficient against pressure difference) at the mouthpiece of a cylindrical bore,
giving odd harmonics. STK's `Flute` and `Clarinet` (MIT-style), and the blow mode of `pichenettes/eurorack`,
`elements/dsp/exciter.h` (MIT). Cost: 20 to 30 operations a voice.

### 9.5 The piano

The hardest common instrument. Its sound comes from: inharmonic partials `f_n = n f0 sqrt(1 + B n²)` with an
inharmonicity coefficient B of about 1e-4 in the mid range, larger in the bass and top; two or three strings per note
detuned by a cent or so, giving beating and a two-stage decay (prompt and aftersound) as the strings couple at the
bridge; a felt hammer whose contact time shortens and stiffness rises with velocity, so loud notes are brighter (a
nonlinear spring force `F = K x^p`, p about 2.5, after Stulov and others); the soundboard's response; sympathetic
resonance with the dampers up. Approaches: additive or modal banks per note with inharmonic partials and velocity-
dependent spectra (moderate cost, controllable); waveguides with dispersion all-passes and a commuted soundboard
(Bank, Välimäki and colleagues, 2000s, "Physics-based sound synthesis of the piano"); the Faust physical modelling
library includes a commuted piano model (licence noted per function). Cost: 40 to 200 operations a voice.

## 10. Chip Voices

### 10.1 The 1983 home console's audio

Two pulse channels (duty 12.5, 25, 50 or 75 %, from an 11-bit period timer and an 8-step sequencer), a triangle of 32
four-bit steps (a staircase, never quite a triangle, with its own aliasing and a gentle "buzz"), a noise channel from a
15-bit linear feedback shift register (feedback from bits 0 and 1 for long noise, bits 0 and 6 for the short, tonal
"metallic" loop), and a sample channel. Each channel's frequency is a timer of the CPU clock, so pitches are quantised
and notes slightly out of tune in a characteristic way. Shay Green's Blip_Buffer and Nes_Snd_Emu, in Game_Music_Emu
(LGPL-2.1-or-later), synthesise such channels by **band-limited step synthesis**: every change of the chip's output
level is added to the output buffer as a band-limited step from a table, so the square waves and staircases are free
of aliasing that the chip would not have made, at a cost per transition rather than per sample.

### 10.2 The 1982 home computer's sound chip

Three voices, each a 24-bit phase accumulator whose top bits make the saw directly and the triangle by folding, a pulse
by comparison with a 12-bit width, noise from a 23-bit shift register (feedback from bits 17 and 22) clocked by the
accumulator's bit 19; combined waveforms (two selected at once) come out as a bitwise AND with analog loading effects,
best reproduced from measured tables. Ring modulation replaces the triangle's fold bit with the other voice's top bit;
sync resets the accumulator. The ADSR uses a rate counter with a piecewise-exponential decay approximation and a
well-known delay bug when a rate changes. Its multimode 12 dB filter is analog and nonlinear, its cutoff curve and
distortion different between the chip's two main revisions. reSID and reSIDfp (GPL-2.0-or-later) are the reference
open emulations: exact waveform generation, measured combined-waveform tables, the ADSR's counters, and a nonlinear
model of each revision's filter.

### 10.3 The handheld console's audio

Two pulse channels (with a sweep on the first), a wave channel playing 32 four-bit samples from wave memory, and a noise
channel from a 15-bit or 7-bit shift register; volume envelopes of 16 steps. The open Game_Music_Emu (LGPL-2.1-or-
later) includes an emulation of this unit with the same band-limited step synthesis.

### 10.4 Cost

A chip voice is a counter or a phase and a table: a few operations, plus the band-limited step cost per transition
(about 16 to 32 adds), which grows with pitch. Chip "arpeggios" (cycling through chord notes at 50 or 60 Hz) are a frame
counter.

## 11. Bytebeat

A one-line integer formula of a counter `t` (incremented at 8 kHz, or at a rate scaled to give a pitch), its low 8 bits
the output: `t * ((t >> 12 | t >> 8) & 63 & t >> 4)` and the like. Bit operations, shifts and multiplications produce
rhythmic, self-similar, harsh music; no anti-aliasing is wanted. Implementation: an interpreter for a small expression
language compiled when the instrument is built (a stack machine or a tree of closures with no allocation when run),
evaluated once per internal sample, held or interpolated to the output rate. Cost: a few to tens of integer operations a
sample. Hazard: division and modulo by zero must be defined (as zero), and shifts must be masked to the integer width.

## 12. Noise and Glitch Voices

- **Telephone tones.** DTMF: each key two sines, a low group (697, 770, 852, 941 Hz) and a high group (1209, 1336,
  1477, 1633 Hz); dial tone 350 and 440 Hz; ring-back 440 and 480 Hz with a cadence; busy 480 and 620 Hz.
- **Modem handshake.** A sequence of answer tones (a 2100 Hz tone with phase reversals), frequency-shift keyed carriers
  (pairs such as 1070/1270 Hz and 2025/2225 Hz for the early low-speed standard), then bursts of noise-like
  wide-band phase-modulated training signals; synthesised as tones and filtered noise switched by a timeline.
- **Bit-crushed and shift-register noise.** Shift registers of various lengths and tap sets give noises from hiss to
  pitched buzz; clocking them at note pitch makes them tonal.
- **Spread oscillator banks.** Many oscillators whose frequencies spread from a detuned unison through harmonic ratios
  to inharmonic "metal" ratios by one control, a cheap way to move from thick to clangorous.

## 13. Drum Machines

The analog drum circuits are in `QUALITY_RESEARCH.md`, section 9. Engine-level points:

- **The 1980 analog machine.** Bridged-T bass drum with long decays, two-resonator snare with noise, six-square metal
  for hats and cymbal, cowbell of two squares, clap of retriggered noise, toms and congas as resonators, rim shot, claves
  and maracas (a very short high resonator, and gated high-passed noise). `pichenettes/eurorack`, `plaits/dsp/drums/`
  (MIT) realises the bass drum, snare and hats.
- **The 1983 analog-and-sample machine.** A punchier bass drum (an oscillator with a fast pitch drop and a waveshaper
  rounding a triangle toward a sine, plus a click and noise), a noisier snare (two oscillators with pitch drop and more,
  longer noise with a "snappy" level), toms with noise; its hats and cymbals were 6-bit samples on the original, so a
  synthesised version uses the six-square metal with a brighter band-pass, or filtered noise with metallic resonances.
- **Accent.** Both machines have a global accent that raises level and brightness of accented steps; in a model,
  velocity or an accent flag scales excitation and opens the tone filters.
- **Rendering.** A hit can be synthesised in full when its note arrives, on another thread, and cached for replay; the
  callback then mixes stored samples. Seeding each hit's noise from its identity keeps renders bit-identical.

## 14. Drones

Held tones that move slowly: several oscillators at just-intonation intervals (octaves, fifths, a natural seventh),
each with its own very slow drift and beating (detunes of 0.05 to 0.5 Hz, so beats arrive every few seconds); slowly
moving filters or comb resonators (a comb whose delay drifts sweeps a harmonic series through the drone); amplitude
"breathing" from very slow random LFOs; chaotic modulators (`MODULATORS_RESEARCH.md`) driving the slow parameters so
that the motion never repeats. Cost depends on the oscillator count; four to eight oscillators and two filters, about
50 to 100 operations.
