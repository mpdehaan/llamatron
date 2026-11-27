# Digital Degradation: Bit Crushing, Rate Reduction, Converters and Folding

A chapter on the effects that make a sound worse on purpose, in the particular ways digital audio fails: lowering the
sample rate, lowering the resolution, switching, inverting and rearranging the bits of each sample, companding, the
converters of early samplers and their nonlinear ladders, folding, wrapping and rectifying, table waveshapers that use
the signal as an address, and the wavetable oscillators whose digital roughness is their charm. Each section gives what
is heard, the principle, the algorithm with its formulas and constants, the open implementations that realise it (each
named with its licence and file), the cost per sample, and the hazards in an audio callback that must not allocate or
lock. It builds on `QUALITY_RESEARCH.md`, sections 4 (oversampling), 5 (antiderivative anti-aliasing) and 6.2
(bitcrushing), which it does not repeat; the telephone codec of `EFFECTS_RESEARCH.md`, section 10, is treated here at
more length. Hardware is described generically. Costs are counted per sample per channel at 44.1 or 48 kHz unless stated.

## 1. The Path Through a Digital Degrader

Every degrader, hardware or software, is some subset of one chain. Naming each stage keeps clear which part makes which
sound, and which part's aliasing is the point.

1. **Input gain and protection.** A preamp lifts the signal toward the converter's full scale; a diode pair or an
   op-amp's rails clip it softly before the converter, so that an overdriven input saturates rather than wrapping.
2. **Anti-alias filter (often absent).** A low-pass at half the sampling clock. A degrader usually omits it, or fixes it
   at the top rate, so that the clock's aliasing of the input is heard.
3. **Sample and hold.** At each tick of the clock the input is captured and held. The clock may be far below the host's
   rate, may wander, and may be set continuously.
4. **Quantiser (the analog-to-digital converter).** The held voltage becomes an integer code of N bits, by rounding or
   truncation, in one of several number formats (section 3.2), linearly or through a companding curve (section 5).
5. **Code manipulation.** Bits are masked, forced, inverted, reordered; the code may address a table (section 6.4).
6. **Digital-to-analog converter.** The code becomes a level through a resistor ladder or a current array, whose bit
   weights are never quite exact (section 5.3).
7. **Zero-order hold.** The level stays until the next tick: a staircase.
8. **Reconstruction filter (often absent or fixed).** A low-pass that rounds the steps.
9. **Tone filter.** An analog filter after the converter, low, band or high pass, shapes what comes out.
10. **Mix.** The degraded sound is mixed with the untouched input, by one crossfading control or by two separate gains.

Stages 3 to 8 run at the clock's rate. Everything they do aliases about the clock, and that aliasing is the effect's
sound. A software model must make sure that the only aliasing heard is the clock's own: none from the host's rate
against the steps of the hold, and none from the analog stages (1, 9) run naively at the host's rate. The anti-aliasing
choices are gathered in section 9.

## 2. Sample-Rate Reduction

### 2.1 What it does to the spectrum

Sampling a signal at a clock `fc` makes each component at `f` appear also at every `|f - k·fc|`. Without an
anti-alias filter, every component above `fc/2` folds back down: a 5 kHz partial clocked at 7 kHz is heard at 2 kHz. A
held staircase also carries the images of everything below `fc/2` at `k·fc ± f`, weighted by the hold's response,

```
H(f) = sinc(f / fc) · e^(-jπ f / fc),    sinc(u) = sin(πu) / (πu)
```

which is 1 at DC, -3.92 dB at `fc/2`, -13.5 dB at the first image's peak near `1.5·fc`, and zero at each multiple of
`fc`. Two things follow that a musician hears:

- **Inharmonic tones.** The aliases are not harmonics of the note unless `fc` is a whole multiple of the note's
  frequency (section 2.6); for most settings they are bell-like or ring-modulated tones that move against the melody.
- **The sweep.** As `fc` falls, each alias at `k·fc - f` falls with it while its mirror at `f - k·fc` rises: a sweep of
  the clock is heard as clusters of tones moving in opposite directions, the "whammy" or "flange" that hardware
  crushers are loved for. At very low clocks (a few hundred hertz) only the aliases remain and the note's pitch is lost
  in difference tones.

### 2.2 Whole-sample holds and their jitter

The simplest hold changes its value only on host samples:

- **A fixed integer period.** Hold every `N` samples, `N = round(fs / fc)`; for instance `downSample` in Faust's
  `basics.lib` (LGPL-2.1 with the Faust exception, which leaves the generated code's licence free): `hold = time %
  int(SR/freq) == 0`. Only the rates `fs/N` exist: at 48 kHz, 24, 16, 12, 9.6, 8 kHz, then ever closer. A slow sweep
  near the top of the range steps audibly between them.
- **A carried remainder.** The distortion in Vital's open source release (`src/synthesis/effects/distortion.cpp`,
  GPL-3.0-or-later), its down-sample mode, counts samples and, when the count passes the period, subtracts the period
  and keeps the remainder. The average rate is exact, but each hold still lands on a whole sample: the period
  alternates between `floor(fs/fc)` and `ceil(fs/fc)` samples. That periodic timing error is phase modulation of the
  held signal, which spreads every alias into a family of sidebands: a second, unintended roughness, and pitch that
  drifts out of tune with the setting.

Both are cheap (an add and a compare per sample) and both are honest models of a converter clocked by dividing a
master clock, which a few cheap devices were. Neither is the sound of an analog clock set by a knob.

### 2.3 Fractional holds with band-limited steps

The analog clock ticks between host samples. A model that keeps the tick's exact time, and band-limits each step of the
staircase where it falls, has neither the jitter of 2.2 nor a second aliasing of the staircase against the host's rate.
`pichenettes/eurorack`, `plaits/dsp/fx/sample_rate_reducer.h` (MIT) does both in a few operations:

```
phase += fc / fs                         // the clock's phase, in ticks
if phase >= 1:
    phase -= 1
    t = phase / (fc / fs)                // how far past the tick this sample lies, 0..1
    new = previous_in + (in - previous_in) * (1 - t)   // the input at the tick, by linear interpolation
    jump = new - held
    this += jump * blep_this(t)          // the polyBLEP residual for this sample
    next += jump * blep_next(t)          // and for the next
    held = new
next += held
out = this                               // one sample of delay
```

with the two-sample polynomial BLEP residuals (`stmlib/dsp/polyblep.h`, MIT):

```
blep_this(t) = 0.5·t² ,   blep_next(t) = -0.5·(1 - t)²     (t measured as above)
```

The output is one sample late. Any rate stays in tune, a sweep is continuous, and only the clock's own aliasing
remains. Cost: an add and a compare every sample; on a tick, a division (or a multiply by a reciprocal kept at control
rate), a lerp and two short polynomials. llamatron's Bitcrush uses this design.

The linear interpolation of the input at the tick is itself a mild, time-varying low-pass of the input (up to about
-2 dB at 10 kHz at a 48 kHz host, for a tick half-way between samples); a cubic Hermite read of the last four inputs is the better choice where the input is bright.

### 2.4 Smoothed and reconstructed holds

Between the raw staircase and a clean decimator lie several open designs, each with a sound of its own:

- **A softened hold.** Airwindows' DeRez2 (`plugins/LinuxVST/src/DeRez2/DeRez2Proc.cpp`, MIT) moves the output only
  part way to each new held value, `out = out·(1 - soften) + held·soften` with `soften = (1 + rate)/2`, so that the
  lower the rate, the more each step is smeared: a one-pole at the clock. It also mixes a "hard" blend of the last dry
  sample into the steps.
- **A curve through the holds.** Airwindows' DeRez3 (`plugins/LinuxVST/src/DeRez3/DeRez3Proc.cpp`, MIT) keeps the
  last three held values and draws a quadratic Bezier between their midpoints, read at the clock's phase: in effect a
  quadratic B-spline reconstruction, whose response falls as `sinc³`, so the images are nearly gone and the aliases of
  the input remain. It is the sound of a low-rate sampler with a good output filter.
- **Tracking filters.** A low-pass before the hold at about `0.45·fc` removes the input's aliasing; a low-pass after it
  at the same frequency removes the images. With both, the effect is a clean band-limit: the sound of a good low-rate
  converter, dull but undistorted. With only the output filter, the input's aliasing is kept but the steps' buzz is
  rounded, which many early samplers sounded like. Each filter is one or two zero-delay-feedback sections
  (`QUALITY_RESEARCH.md`, section 3), whose cutoff follows the clock; about 12 to 25 operations a sample each.
- **The hold's droop.** A real zero-order hold rolls the top off by its `sinc` (2.1); a fractional hold in software
  already has it, because it is a hold.

A continuous blend between raw and reconstructed (a crossfade of the stepped and the filtered signal, or the softening
amount of DeRez2) gives a musician one knob from "gritty" to "dusty".

### 2.5 Clock jitter and drift

A real clock's ticks wander. A tick displaced by `δ` seconds captures `x(t + δ) ≈ x(t) + x'(t)·δ`, so the error is
the signal's slope times the displacement: jitter is noise that rises with the input's brightness and level. Two kinds
matter:

- **Random jitter**, independent each tick, a grainy roughness on bright material. Model: add `σ·n` to each tick's
  period, `n` from a seeded generator, `σ` a few percent of the period at most.
- **Slow drift**, a low-frequency wander of the clock, heard as the aliases gliding. Model: a smooth random source
  (`MODULATORS_RESEARCH.md`) on the clock's rate.

With the fractional hold of 2.3 a jittered tick is placed exactly; nothing else changes. Seeding the generator from the
instrument keeps renders identical. A stereo converter has one clock for both channels: jitter must be the same on each,
or the image smears.

### 2.6 Rates that follow the note

If a periodic input of fundamental `f0` is clocked at `fc = N·f0` for a whole `N`, every alias `|k·f0 - m·N·f0|` is
itself a multiple of `f0`: the aliasing becomes harmonic distortion, bright but in tune. Ratios such as `fc = (N/2)·f0`
put the aliases on half-harmonics, a sub-octave. A crusher whose clock follows the note, as a multiple set in semitones
above it, turns the effect from noise into timbre. The voice effects of Surge XT (`sst-effects`,
`include/sst/voice-effects/distortion/BitCrusher.h`, GPL-3.0-or-later) offer this as key tracking: the rate parameter
becomes an offset in semitones added to the note's pitch. After a polyphonic mix there is no single note; a
per-instrument effect can follow the newest note or the lowest, which suits a bass or a lead.

## 3. Quantisation

### 3.1 Rounding, truncation and where zero sits

For a signal `x` in `[-1, 1)` and `N` bits, the step is `q = 2 / 2^N`. The common quantisers differ in where the zero
of the signal falls:

| Quantiser | Formula | Zero in | Low-level behaviour |
| --- | --- | --- | --- |
| Mid-tread rounding | `q·round(x/q)` | a level | silence stays silent; quiet signals gate to zero below `q/2` |
| Mid-riser | `q·(floor(x/q) + 1/2)` | a boundary | no zero level: silence becomes an idle buzz between `±q/2` if any noise is present |
| Two's complement truncation | `q·floor(x/q)` | a level | error always negative: a DC offset of `-q/2`, asymmetric distortion |
| Sign-magnitude truncation | `q·trunc(x/q)` (toward zero) | a level two steps wide | a dead zone of `±q`: a "gated" crush that drops quiet tails to silence early |

The open crushers each pick one, and the choice is audible: Vital's (`distortion.cpp`, GPL-3.0-or-later) rounds,
`round(x/step)·step`; Surge XT's voice-effect crusher (`BitCrusher.h`, GPL-3.0-or-later) truncates toward zero with a
"zero point" control adding an offset before the truncation, which slides the dead zone and the asymmetry; Faust's
`ba.bitcrusher` (`basics.lib`, LGPL-2.1 with exception) rounds with the scaler `2^N - 1`, so that `±1` are levels,
an odd number of levels with zero among them; Airwindows' crushers (DeRez2, BitGlitter, MIT) truncate toward zero by
repeated subtraction of the step, which is exact but costs a loop whose length grows with the level over the step (a
floor is the constant-time equivalent).

A fractional bit depth, `2^(b-1)` levels for a real `b`, lets a knob sweep smoothly; the step widths then change
continuously, and the error pattern moves with them, a sound of its own. Crossfading between the neighbouring whole
depths keeps each staircase exact.

### 3.2 Number formats and what a bit means in each

A converter's code is an integer, and what it means to switch a bit depends on the format. For eight bits:

| Format | Code for a level | Inverting every bit gives | Inverting the top bit gives |
| --- | --- | --- | --- |
| Offset binary | `u = floor((x + 1)·128)`, `0..255`, mid-scale `128` | `255 - u`: the exact mirror, the polarity inverted | the level moved by half the range and wrapped round: a wrap at zero |
| Two's complement | `s = u - 128 = u XOR 0x80`, `-128..127` | `-s - 1`: the polarity inverted, one step off | `s XOR 0x80`: the offset-binary code read as signed, the same half-range wrap |
| Sign-magnitude | a sign bit and a 7-bit size | the size inverted: loud becomes quiet, quiet loud | the polarity inverted, exactly |
| Ones' complement | negative values as `NOT` of the positive | the polarity inverted | wraps, with two zeros |

Parallel converters joined directly, a converter's output pins wired to a converter's inputs, as cheap hardware does,
almost always use offset binary, and the musical results in section 4 assume it. Inverting the top bit in offset binary
is identical to reinterpreting the code as two's complement, which is why "wrapping" and "two's-complement overflow" are
one sound.

### 3.3 Gating and the quiet end

Below one step, a quantised signal is silence (mid-tread) or a square wave of one step (mid-riser, or any quantiser
after a DC offset). As a note decays, an undithered crusher first adds harsh odd harmonics that follow the note, then
breaks it into a buzzing pulse wave, then cuts it to silence: the "gated" quality of a low-bit crush. Some hardware
offers this as a noise gate deliberately: the lowest codes forced to zero so that the hiss between notes vanishes. A
gate on the code is one compare, `if |s| < threshold { s = 0 }`; with hysteresis, two thresholds and a state, to stop
it chattering.

### 3.4 Dither and noise shaping

Dither decorrelates the quantisation error from the signal (Lipshitz, Wannamaker and Vanderkooy, 1992): triangular
(TPDF) noise of `±1` step peak, the sum of two independent uniform noises each `±q/2`, added before rounding, makes the
error's first two moments independent of the signal. The crushed sound then becomes the signal plus a steady hiss at
about `-6.02·N - 1.76 + 4.77 dB` relative to full-scale sine, and low-level detail survives below one step instead of
gating. Faust's `misceffects.lib`, `dither` and `dither_shaped` (MIT), are the plainest open realisations:

```
dither(nbits):   y = round((x + d)·S) / S,   S = 2^(nbits-1),   d = (u1 + u2)·0.5/S
dither_shaped:   u = x - c1·e[n-1] - c2·e[n-2];  y = Q(u + d);  e = y - u
                 first order c1 = -1, c2 = 0;  second order c1 = -2, c2 = 1
```

The error feedback gives a noise transfer function `(1 - z^-1)^K`, rising `6K` dB an octave, pushing the hiss toward
the top. At eight bits the dither itself is loud (about -45 dB below a full-scale sine), so a crusher usually leaves
it out: the correlated,
gating distortion is wanted. A dither amount, from none to full TPDF, is a useful colour: "broken converter" to "tired
converter". Subtractive dither (the same noise subtracted after the converter) removes the hiss while keeping the
linearising effect; a software crusher can do this exactly, since it knows its noise.

## 4. Bit Manipulation

### 4.1 A code is a sum of square waves of the input

Write the offset-binary code `u` of the input as its bits, `u = Σ 2^k · b_k(u)` for `k = 0..7`, where

```
b_k(u) = floor(u / 2^k) mod 2
```

As the input rises from the bottom of the range to the top, `b_k` is a square wave of the input's amplitude, period
`2^(k+1)` codes: the top bit `b_7` is low for the lower half of the range and high for the upper (one period over the
whole range), `b_6` flips twice as often, down to `b_0`, which flips every code. The converter's transfer curve, a
straight staircase, is the weighted sum of these eight square waves. Every bit operation changes one term:

- **Muting a bit** (forcing it to 0, `u AND NOT 2^k`) removes its square wave: the curve drops by `2^k` codes wherever
  that bit was set, so it becomes a sawtooth-like curve with `2^(7-k)` downward jumps.
- **Forcing a bit on** (`u OR 2^k`) adds the same curve plus a constant `2^k`: after AC coupling, identical to muting it,
  except for the DC.
- **Inverting a bit** (`u XOR 2^k`) replaces `b_k` by `1 - b_k`: the curve gains a square wave of `±2^k`, jumping up
  and down by `2·2^k` alternately, a shuffled staircase whose local order runs backwards inside each block of `2^(k+1)`
  codes.

The size of each jump sets the strength of the distortion. The lowest three bits shift the curve by at most 7 codes in
256, a fine grit that follows the signal, close to a lower bit depth (with a DC offset, since muting truncates); the top
three move it by 32 to 128 codes, harsh, loud, ring-modulated sounds. In offset binary, four settings are worth knowing
by name:

| Setting | Transfer curve | Heard as |
| --- | --- | --- |
| Top bit muted | the upper half folded onto the lower: `u mod 128`, a two-tooth sawtooth of the input, its centre half the peak level below zero | a wrapped, octave-up buzz with strong DC |
| Top bit inverted | the two halves swapped: `(u + 128) mod 256`, a wrap at zero | a harsh square-like wrap, every zero crossing a full-scale jump |
| Every bit inverted | `255 - u`: the exact mirror | the sound with its polarity inverted, otherwise untouched; mixed with the dry sound it cancels |
| Every bit muted | a constant | silence |

The third row has a use: an inverted wet sound against the dry one cancels everything the crush did
not change, leaving only the distortion, a "difference" sound.

### 4.2 Masks, constants and bit rearrangements

- **A mask with a constant.** `u AND m` for an 8-bit constant `m` mutes a chosen set of bits at once; some hardware sets
  it by one knob through all 256 values, which sweeps through dissimilar curves rather than a smooth progression.
  Masked before a table waveshaper (section 6.4), it skips ranges of the table.
- **XOR with a constant** inverts a set of bits; **XOR of two signals** is a digital ring modulation. The XOR mode of
  `pichenettes/eurorack`, `warps/dsp/modulator.cc` (MIT), converts both inputs to 16-bit integers, `x1 ^ x2`, and
  crossfades it with their sum; it runs at six times the rate (`kOversampling = 6`) with a halfband resampler on each
  side, because the result is full of jumps.
- **Bit reversal** (`b_k` moved to `b_(7-k)`) makes the finest bit the most significant: the curve becomes nearly
  random, close to white noise for any input with movement, silence-tracking.
- **Nibble swap** (the low four bits exchanged with the high four, `((u & 0x0F) << 4) | (u >> 4)`): the fine grain of
  the input becomes the coarse shape, a radical, noisy distortion full of high partials.
- **Gray code** (`u XOR (u >> 1)`) and **rotation** (`(u << r) | (u >> (8 - r))`) give further curves of the same
  family, each a fixed permutation of the 256 levels.

### 4.3 The whole converter as one table

Every operation of sections 3.2 to 4.2 maps each of the 256 codes to one output level. However many switches, masks and
inversions are set, the converter's whole transfer is one 256-entry table:

```
level[c] = dac( ((c AND keep) XOR invert) )      for c = 0..255
```

where `keep` holds a 1 for each bit that passes or is inverted and `invert` a 1 for each inverted bit, and `dac` is the
converter's output for a code, ideal or with the ladder's errors of section 5.3. The table is rebuilt only when a
setting changes, at control rate, into a fixed array: no allocation. In the callback, a held sample costs one multiply,
one floor, one saturating conversion and one read.

The same table gives the curve's antiderivative cheaply, should the curve ever be run where its jumps would alias
against the host (section 9): with prefix sums `P[c] = Σ_(j<c) level[j]` (also rebuilt at control rate), the
antiderivative at a real code position `v` is `P[floor(v)] + level[floor(v)]·frac(v)`, two reads and a multiply-add,
and first-order antiderivative anti-aliasing (`QUALITY_RESEARCH.md`, section 5.1) follows. This generalises section
5.3 of that chapter's quantiser row to any 8-bit curve.

### 4.4 Level, DC and loudness

- **DC.** Muting or forcing bits in offset binary moves the curve's centre; muting the top bit alone puts the output's
  centre half its peak level off zero. Hardware is AC-coupled at its output by a capacitor. A model needs a DC blocker on the
  degraded path, a one-pole high-pass at 5 to 20 Hz (`y = x - x[n-1] + R·y[n-1]`, `R = 1 - 2π·fc/fs`), after the
  converter and before the mix, or the Dry and Wet sum carries an offset.
- **Level.** Muting the lower bits barely changes the level; muting the upper ones lowers it, inverting them raises the
  crest factor to that of a square wave. A compensation gain worked out from the table (the inverse of its RMS over a
  full-scale ramp, or of `Σ` of the passed weights over `255`) keeps the level roughly steady across settings; it is
  computed when the table is rebuilt.
- **Loudness hazards.** An inverted top bit turns every zero crossing into a full-scale jump: a quiet sine becomes a
  full-scale square. The wet path needs a safety limiter, and a setting change is best crossfaded (section 10).

## 5. Companding Converters and Early Sampler DACs

### 5.1 Mu-law and A-law

A companding converter spends its codes where the signal is quiet: the step grows with the level, so the error follows
the signal at a roughly constant ratio (about 38 dB for 8-bit mu-law), and quiet passages keep their detail while loud
ones carry a grainy, level-following distortion. The ITU-T G.711 curves (1972) are

```
mu-law:  y = sign(x) · ln(1 + μ|x|) / ln(1 + μ),         μ = 255
A-law:   y = sign(x) · A|x| / (1 + ln A)                 for |x| < 1/A
         y = sign(x) · (1 + ln(A|x|)) / (1 + ln A)       for 1/A ≤ |x| ≤ 1,     A = 87.6
```

In the codec itself the curves are segmented: a sign bit, three bits of segment (exponent) and four of step (mantissa),
eight segments each doubling the step of the one below. `pichenettes/eurorack`, `clouds/dsp/mu_law.h` and `mu_law.cc`
(MIT), implement the segmented encoder by comparisons and the decoder by a 256-entry table; that module stores its
low-fidelity grain buffer as 8-bit mu-law codes, at half the rate, through a filtered 2:1 resampler. Airwindows' DeRez2
(MIT) uses the continuous mu-law curve around its truncation for a softer crush; Faust's `ba.mulaw_bitcrusher`
(`basics.lib`) compresses, quantises and expands. Bit operations on a companded code are a different instrument from
those on a linear code (section 4): muting a segment bit moves a level by whole octaves of loudness, while the mantissa
bits are a fine grain at every level.

### 5.2 Floating-point and gain-ranging converters

Several 1980s instruments extended a 12-bit converter's range with a gain stage switched in octave steps: a mantissa of
10 to 12 bits and an exponent of 2 or 3 bits, `y = m · 2^(e - E)`. The step is fine near silence and coarse at full
scale, a staircase companding in 6 dB segments. The quantisation error follows the level as in mu-law but with an
audible change of grain at each segment boundary, and the gain stage's own switching adds a small glitch where a note
crosses one. Dexed (`source/engine/EngineMkI.cpp`, GPL-3.0-or-later) models related arithmetic for an early FM
operator: a sine read from a 10-bit log table, the envelope added in the log domain, an exponential table and a right
shift by the exponent, with the sign carried separately: sign-magnitude, log-domain quantisation, whose grain is part of
that instrument's sound.

### 5.3 The ladder's errors

A real converter's bit weights are never exactly `2^k`. Model the output as

```
dac(u) = Σ_k 2^k · (1 + ε_k) · b_k(u),     ε_k seeded, |ε_k| of 0.1% to 2% (larger for the upper bits)
```

so that each code's level is off by a fixed amount that depends on which bits it holds. Two named errors follow:

- **Differential nonlinearity (DNL):** uneven step sizes, worst at the **major carry**, the step from `0111 1111` to
  `1000 0000`, where every bit changes and their errors add. In offset binary this sits at the zero crossing: a small
  jump or flat step there gives crossover distortion on every quiet signal, the dirt of a cheap converter at low level.
- **Integral nonlinearity (INL):** a bow of the whole curve, a gentle even- or odd-order distortion.

Two dynamic effects add to these: a **glitch** at each major-carry transition (a spike while the switches settle, a few
hundred nanoseconds, modelled as a short impulse proportional to the number of bits that change), and the **slew** of
the output amplifier, which rounds large steps. Because the errors are a property of each code, the model costs nothing
per sample beyond the table of section 4.3: the `ε_k` are drawn once from the instrument's seed when the table is
built, so every render is the same and two instruments differ like two units.

### 5.4 The character of early sampler converters

From published descriptions of 8-bit and 12-bit samplers and drum machines of the late 1970s to the early 1990s:

- **Rates.** 8 to 42 kHz, often 26 to 32 kHz for 12-bit instruments, and 8 to 16 kHz for 8-bit companded drum samples.
- **Input filters.** Often fixed at the top rate, or switchable in a few steps; sampling at a reduced rate through the
  fixed filter kept the input's aliasing.
- **Playback by changing the clock.** Many played each voice by varying its own DAC clock with the pitch: a note played
  higher plays its samples faster, so the images and the hold's droop move with the pitch, and a low note is dull and
  stepped. Others played at a fixed rate with drop-sample or linear resampling, whose errors are aliasing of the
  sample's own spectrum against the fixed rate, worse for upward transposition.
- **Output filters.** Some had tracking multi-pole filters per voice (a steep, smooth top); some a fixed filter, so that
  low notes kept their images, the "crunch" of pitched-down drums; some none at all.
- **The 12-bit grain.** 72 dB of range in principle, much less in practice after the analog stages; quantisation that
  gates quiet tails; companding in some to stretch 8 or 12 bits.

A converter emulation is therefore a choice of five independent things: bits and format, companding or not, the
ladder's errors, the input filter (none, fixed, tracking) and the output filter (none, fixed, tracking), each cheap.

## 6. Waveshaping in the Digital Domain

### 6.1 Folding

A folder reflects the part of the signal past a threshold back toward zero, as many times as needed. It brightens
strongly but keeps the level bounded, and as the gain into it rises the partials sweep up through the spectrum, a
"talking" timbre. Its slope stays large however hard it is driven, so it aliases far more than a saturator at the same
gain (Faust's `aanl.lib` notes this). The forms in open code:

- **Triangle fold**, periodic in the input with period `4t` for threshold `t`: Vital's `linearFold`
  (`distortion.cpp`, GPL-3.0-or-later), `y = |4·mod(x·g/4 + 3/4, 1) - 2| - 1`, reproduced in Surge XT's
  `sst-waveshapers`, `include/sst/waveshapers/Wavefolders.h` (GPL-3.0-or-later), as `LINFOLD`.
- **Sine fold**, `y = sin(π·x·g/2)` or a sine of the wrapped input: Vital's `sinFold`; Surge XT's `SINUS` shaper with
  its fold option reads a 1024-entry sine table with the index wrapped by a power-of-two mask.
- **Threshold mirror with decay.** Faust's `aanl.lib`, `triangleFold1`, `triangleFold2`, `sineFold1` and `sineFold2`
  (David Braun, MIT): the input passes unchanged inside `±t`; beyond, it reflects, and each reflection scales the
  excess by `r`, so that with `r < 1` each fold is `1/r` wider than the last and the output moves more slowly as the
  input grows, a gentler, more analog fold. Their first and second antiderivatives are in closed form for any number of
  folds; with `r = 1` the fold geometry is `k + p = (|x| - t)/(2t)`, `k` the number of completed reflections, `p` the
  place in the current one, `s = (-1)^k`, and

  ```
  f(x)  = x                                   inside ±t
        = sign(x)·s·t·(1 - 2p)                outside
  F1(x) = x²/2                                inside
        = t²/2 + 2t²·s·p·(1 - p)              outside   (with g = 1 for r = 1)
  ```

  which drops straight into first-order ADAA.
- **Piecewise-linear folds with closed-form antiderivatives.** `sst-waveshapers`, `Wavefolders.h`, `FolderADAA<pts>`
  (GPL-3.0-or-later), builds any folder from a list of break points, works out each segment's slope and the intercepts
  that keep the antiderivative continuous, and evaluates the curve and its antiderivative together, so that a single
  fold (`{-10, -0.7, 0.7, 10} → {-1, 1, -1, 1}`), a double fold, or a measured circuit curve all get ADAA for the same
  cost. Its fourteen-point table after a published model of a classic West Coast timbre circuit (Esqueda, Pöntynen,
  Välimäki and Parker, DAFx 2017) is the same idea applied to a real folder.
- **Circuit folders.** `chowdsp_utils`, `modules/dsp/chowdsp_waveshapers/Waveshapers/chowdsp_WestCoastWavefolder.h`
  (GPL-3.0), sums five folding cells, each `G·x - B·sign(x)` past its threshold, with a linear term, and tabulates the
  curve and both antiderivatives for second-order ADAA; it notes that signals below about -6 dB pass untouched and most
  of the folding happens between -6 and +12 dB.
- **A tabulated fold with a central bump.** `pichenettes/eurorack`, `plaits/resources/lookup_tables.py` (MIT): a
  windowed many-cycle sine blended into an arctangent at the ends, read by Hermite interpolation
  (`plaits/dsp/engine/waveshaping_engine.cc`); `warps/resources/lookup_tables.py` builds Warps' bipolar fold the same way.

A folder with a plain gain control, the gain before a fixed threshold, is the most direct interface; at a gain of 1 a
signal within full scale passes untouched, so the control's lowest setting leaves the sound alone. Folding before a
quantiser folds the continuous signal; folding the code after it folds the staircase, and the steps fold with it.

### 6.2 Wrapping

A wrap sends whatever passes full scale round to the other side: `y = mod(x + 1, 2) - 1`, the sound of two's-complement
overflow (an adder that is not saturated) and of inverting a converter's top bit (section 3.2). Each wrap is a
full-scale jump, so it aliases like a sawtooth; its antiderivative is in `QUALITY_RESEARCH.md`, section 5.3.

### 6.3 Rectifiers and zero-crossing tricks

- **Full-wave rectification** (`|x|`) doubles a sine's frequency: an octave up with even harmonics and DC, the "octave
  fuzz". Half-wave (`max(x, 0)`) keeps the fundamental and adds even harmonics. `sst-waveshapers`, `Rectifiers.h`
  (GPL-3.0-or-later), gives both with ADAA, noting that the antiderivative of a rectifier is `F²/2` for the half-wave and
  `sign(x)·x²/2` for the full; a DC blocker must follow.
- **Octave down.** A flip-flop toggled at every rising zero crossing divides the frequency by two. Gating the signal by
  the flip-flop (keeping every other positive half-cycle, or every other whole cycle) gives a distorted octave down
  that keeps the input's waveform; the flip-flop's square wave alone, scaled by the input's envelope, is a clean sub
  octave. A divider by three, gating two of every three half-cycles, gives a coarse fifth below with heavy distortion.
- **Tracking oscillators.** The time between rising zero crossings measures the period; a sawtooth or square at that
  period, or a multiple of it, restarted at each crossing, is a synthesizer that follows the input, monophonic and best
  on bass. The measurement needs a low-pass before the detector (about twice the expected fundamental) and hysteresis
  (two thresholds, a few percent of full scale apart), or noise and harmonics make it chatter; fractional crossing times,
  by linear interpolation between the two samples around the crossing, keep the pitch exact, and the generated waves
  need BLEP corrections at their jumps (`QUALITY_RESEARCH.md`, section 1.2).

All are cheap: a compare, a state bit and a few multiplies a sample, plus the follower and the generated wave.

### 6.4 Table waveshapers: the signal as an address

A table waveshaper reads a stored curve at the position given by the input: `y = T[index(x)]`. With 8-bit conversion
before it, the code itself is the address into a 256-entry table, and the table can hold anything: a straight line (the
identity, a clean pass), Chebyshev polynomials (`T_n(cos θ) = cos(nθ)`, so a full-scale sine comes out as its `n`-th
harmonic, `T3 = 4x³ - 3x` an octave and a fifth up), folds, steps, wraps, the bit permutations of section 4.2, or
seeded random values. Because the shape is chosen per entry, a bank of a few hundred tables can range from subtle to
destroyed, ordered so that the next table is a more extreme version of the last.

- **Addressing.** The input is scaled by a gain and offset into `0..255` (or a table's length), clamped at the ends:
  driven past them, the output sticks at the end values and the sound brickwalls into a square-like sustain. A tone
  control before the table, tilting the spectrum dark or bright, changes how the table is swept: bass-heavy material
  sweeps it slowly and evenly, bright material jumps across it.
- **Interpolation.** Read without interpolation, the curve is a staircase of 256 levels through the table, an 8-bit
  quantiser with arbitrary levels (section 4.3 applies). With linear interpolation, `pichenettes/eurorack`,
  `plaits/dsp/engine/waveshaping_engine.cc` (MIT), reads a 256-entry 16-bit table at `127·x + 128`, interpolates
  between neighbours, and crossfades between two adjacent tables by a shape control, then folds the result.
- **Seeded noise tables.** `sst-waveshapers`, `Fuzzes.h` (GPL-3.0-or-later), fills 1024-entry tables with the identity
  plus seeded uniform noise, spread evenly, or concentrated near zero by `e^(-20x²)`, or near the ends by `x⁴`, from
  a portable fixed linear congruential generator (multiplier 48271, modulus `2^31 - 1`, seed 2112) so that the tables
  are identical on every platform: a fuzz whose roughness is a property of the curve, not of time.
- **Morphing.** Crossfading the outputs of two tables read at the same address moves between them; quantising the
  crossfade to a few steps gives a stepped morph (section 7).
- **Pre and post.** Quantising before the table changes which entries are reached (a 3-bit input visits only eight);
  quantising after it crushes the shaped result; a mask before it skips ranges of the table.
- **Taming by pitch.** Every table with corners aliases on high notes. Plaits' waveshaping engine reduces the shaping
  amount as the fundamental rises (its `Tame(f0, slope, ...)` estimates how rich the spectrum is from the pitch), a cheap
  way to keep a synthesizer voice clean; an effect after a polyphonic mix cannot know the pitch, and relies on running
  the table at the clock's rate (where its aliasing is intended) or on ADAA by prefix sums (section 4.3).

Cost: a multiply-add for the address, a floor and conversion, one or two reads, a lerp: 6 to 10 operations.

### 6.5 Where a shaper sits

A shaper inside the clocked stages (between the hold and the DAC) runs once per tick, on held values: its harmonics
alias about the clock, which is the sound of hardware that shapes in its digital domain, and its steps are smoothed by
the hold's BLEP with everything else. A shaper outside (before the hold, or after the converter) runs at the host's
rate: it must be anti-aliased there, by ADAA, by oversampling or both, as llamatron's Drive is (`QUALITY_RESEARCH.md`,
sections 4 and 5). Placing the folder of a crusher inside the clocked stages gives the hardware's interaction between
clock and fold (low clocks fold coarse, stepped values); placing it before them gives a clean fold that the clock then
samples.

## 7. Wavetable Oscillators with Digital Character

Single-cycle wavetable oscillators of the late 1980s and the 2000s are loved for a roughness that is entirely digital.
Its causes, each reproducible:

- **8-bit waves.** Quantising a single-cycle wave leaves an error that repeats with the wave: it adds harmonics, not
  hiss. A static 8-bit wave is bright and buzzy but clean; only when the wave or the pitch moves does the error become a
  shimmer.
- **Drop-sample reading.** Reading `T[floor(phase·L)]` without interpolation at the host rate is a hold of the table's
  values at the table's own rate `L·f0`, re-sampled at the host's: the staircase's jumps alias, and the hold lands on
  whole samples (the jitter of section 2.2). The sound is a gritty, inharmonic fizz that rises with pitch; high notes
  alias heavily. A model that keeps it on purpose can read drop-sample at a virtual DAC rate and then apply the
  fractional hold of section 2.3 at that rate, so the grit is the chosen converter's and not the host's.
- **Variable-rate playback.** Some instruments clock their DAC at `L·f0`, so every note has exactly `L` steps a cycle:
  the steps are harmonic (images at `k·L·f0 ± n·f0`) and a fixed output filter lets them through for low notes. This is
  a cleaner, more "in tune" grit than fixed-rate drop-sample reading.
- **Tables arranged in a cube.** Waves addressed by two or three coordinates (wave, bank, set), each moved by a slider
  and a control voltage. Crossfading between neighbours on each axis is the morph; disabling the crossfade, or quantising
  it, makes it stepped. `pichenettes/eurorack`, `plaits/dsp/engine/wavetable_engine.cc` (MIT), arranges 8 by 8 waves in
  each of several banks, reads each 128-sample wave by Hermite interpolation, and blends across three axes (eight reads a
  sample); a "quantisation" amount, rising over the upper part of one control, replaces each coordinate's fractional
  part by `clamp(16·(frac - 0.5), -0.5, 0.5) + 0.5`, a crossfade squeezed into a sixteenth of each step, so the morph
  goes from smooth to stepped continuously. The coordinates are smoothed by one-poles whose coefficient follows the
  pitch, so that a stepped morph clicks less on low notes.
- **Integrated tables.** Plaits stores each wave integrated and differentiates the interpolated output (dividing by the
  phase increment), a cheap way to reduce aliasing: the differentiation is a first-order DPW (`QUALITY_RESEARCH.md`,
  section 1.3). A deliberately rough oscillator skips it.
- **The input as the phase.** Driving an external signal through the table, addressed by the signal instead of a phase
  ramp, makes the oscillator a table waveshaper (section 6.4); a sine in, scaled by an envelope, sweeps through the
  table's harmonics as the envelope rises.
- **Through-zero frequency modulation.** A phase increment that may go negative (the phase running backwards), which
  keeps FM sidebands symmetric and the carrier in tune; needs a phase that wraps in both directions.

Cost: drop-sample, one read; linear, two reads and a lerp; a three-axis Hermite morph, eight four-point reads, about 60
operations.

## 8. Filters and Mixing After the Converter

### 8.1 The tone filter

A crusher's analog filter is usually a 12 dB an octave multimode filter, low, band and high pass, with a resonance that
on many units is gentle, closer to an equaliser's Q than a synthesizer's whistle. A zero-delay-feedback state-variable
filter (`QUALITY_RESEARCH.md`, section 3.2; A. Simper's technical paper on the linear trapezoidal state-variable filter,
2013; used by Surge XT's voice-effect crusher, `BitCrusher.h`, GPL-3.0-or-later, with low, high and band pass) gives all
three outputs from one update:

```
g = tan(π·fc/fs),  k = 1/Q,  a1 = 1/(1 + g(g + k)),  a2 = g·a1,  a3 = g·a2
v3 = x - ic2;  v1 = a1·ic1 + a2·v3;  v2 = ic2 + a2·ic1 + a3·v3
ic1 = 2·v1 - ic1;  ic2 = 2·v2 - ic2
low = v2,  band = v1,  high = x - k·v1 - v2
```

about 12 operations a sample, the coefficients at control rate, the cutoff smoothed. A range of about 20 Hz to 15 kHz
covers the useful settings; keeping `fc` under `0.45·fs` keeps `tan` sane. A resonance range of Q from 0.5 to about 4
is the gentle character; a soft saturation of the band-pass state (`tanh` or a rational limiter) adds the analog edge
without risking runaway. Placed after the converter, the low-pass tames the clock's aliasing and the high-pass thins the
crush into a fizz; the filter usually acts on the degraded path only.

### 8.2 Dry and wet

A single Mix crossfades, `y = dry·(1 - m) + wet·m`, which loses level in the middle and offers no way to have both at
full. Two separate amounts, `y = a·dry + b·wet`, each from silence to unity, let the crushed sound sit under the clean
one at any balance (parallel distortion), and let the clean sound be taken away entirely. Airwindows' DeRez3 (MIT) maps
one knob to two ramps, so that its middle is both at full, "so it can be on tracks without cutting back the dry channel";
two controls do the same without the compromise. Each gain is smoothed (a one-pole of about 10 ms) and an audio taper
(the square of the setting, or decibels from -60 to 0 with silence at the bottom) makes the low part of the travel
useful. Because the wet path is delayed (one sample by the hold's BLEP, plus any oversampling's latency), the dry path
must be delayed to match, or the parallel sum combs; with all bits inverted (section 4.1) and the two aligned, the sum
cancels except for the distortion, a striking effect when it is wanted and a nuisance when it is not.

## 9. Anti-Aliasing Choices, Summarised

| Stage | Where it aliases | Intended? | Treatment |
| --- | --- | --- | --- |
| Input gain and clip | against the host rate | no | ADAA, at 2x if hard (`QUALITY_RESEARCH.md`, sections 4 and 5) |
| The clock's sampling of the input | about the clock | yes: the sound | kept; an optional tracking pre-filter for a clean setting |
| The hold's steps | against the host rate | no | fractional hold with polyBLEP steps (section 2.3) |
| Quantiser, bits, tables, folds inside the clocked stages | about the clock | yes: the sound | kept; their steps ride the hold's BLEP |
| The same stages run at the host rate (no reduction) | against the host rate | no | ADAA by prefix-sum tables (section 4.3) or closed forms (6.1), or keep a clock always below the host rate |
| Shapers outside the clocked stages | against the host rate | no | ADAA, 2x or both |
| Tracking oscillators, sub-octave squares | against the host rate | no | BLEP at each jump |
| Clock jitter | none: it is noise | yes | seeded |

The practical rule: a degrader's own aliasing is the aliasing about its clock, and the model's job is to make that the
only aliasing heard. A clock that never reaches the host's rate (a top rate of about 30 kHz at a 44.1 or 48 kHz host)
keeps every clocked stage in the clock's domain, and the problem of the fifth row never arises.

## 10. Real-Time Concerns in Rust

- **No allocation.** The converter's table, its prefix sums and the bit masks are fixed arrays (`[f32; 256]`) inside
  the effect, rebuilt in place when a setting changes. Rebuilding 256 entries costs about a microsecond: once per block
  at most, never per sample.
- **Conversion to a code.** In Rust, `f32 as u8` and `f64 as i32` saturate at the type's limits and turn NaN into 0,
  so a code is always in range without undefined behaviour: `((x + 1.0) * 128.0).floor() as i32`, clamped to `0..=255`,
  then `as usize` for the read. A clamp before the conversion makes the edge behaviour explicit (the top code reached
  at `1 - 1/128`).
- **Bit operations are cheap and branch-free.** `(code & keep) ^ invert` on a `u8`; masks precomputed from the
  switches. A rebuilt table makes even these unnecessary in the hot loop.
- **Per-tick work.** Everything between the hold and the DAC runs only on a tick; at a clock of a few kilohertz that is
  a small fraction of samples. The per-sample floor is the phase add, the BLEP bookkeeping, the DC blocker, the filter
  and the mix.
- **Changing a curve while a note sounds.** A switch flip replaces the whole transfer curve at once: the next held value
  jumps. The BLEP removes the step's aliasing but not its audibility as a click. Keeping the previous table and
  crossfading the two curves' outputs over 5 to 20 ms (both read on each tick during the fade) makes a switch change
  smooth; a fold amount, a gain or a rate is smoothed by a one-pole on its value.
- **Denormals.** The filter's states and the DC blocker's decay into denormals after the sound stops; flush them as the
  rest of the callback does (`QUALITY_RESEARCH.md`, section 12).
- **Guards.** The wet path has no loop that can run away (unless a feedback path is added), but the bit and table
  stages can produce full-scale squares from quiet input: a soft limiter on the wet output, and a check that the output
  is finite, reset to silence if not.
- **Seeding.** Jitter, dither, ladder errors and noise tables draw from generators seeded from the instrument (and the
  note, where per-note), so renders are identical. A fixed generator such as the Park and Miller minimal standard
  (`48271`, `2^31 - 1`) or an xorshift is portable; the platform's default generators are not guaranteed to be.
- **Stereo.** A stereo converter has one clock, one set of switches and two signal paths: share the phase, the tick
  times, the jitter and the table; keep two holds, two BLEP states, two filters and two DC blockers. A mono effect
  written with that split becomes stereo by duplicating the per-channel state only.
- **Latency.** The fractional hold delays by one sample; a 2x drive stage adds its halfband's delay (a dozen samples).
  The dry path is delayed to match before it is summed with the wet (section 8.2).
- **Reset.** Clear the phase, the holds, the BLEP carry, the filter and DC-blocker states, the drive's oversampler and
  the crossfade, so that a restarted instrument begins in silence.

## 11. Costs per Sample

Operation counts per channel; times on a current desktop core are of the order of 0.3 to 0.5 ns an operation for this
kind of scalar code.

| Stage | Every sample | Per tick | Notes |
| --- | --- | --- | --- |
| Drive with ADAA at 2x | about 60 to 80 (halfband up and down, two ADAA evaluations) | | as llamatron's Drive |
| Fractional hold with polyBLEP | 4 | about 12 | Plaits' design |
| Jitter | | 3 (a seeded noise draw and a multiply) | |
| Fold (closed form, with ADAA) | | 10 to 20 | inside the clocked stages it needs no ADAA |
| Converter table read (bits, format, ladder errors, companding) | | 5 | the table rebuilt at control rate |
| Table waveshaper (one table, linear) | | 8 | two tables and a crossfade, 14 |
| Tracking reconstruction filter | 12 to 25 | | optional |
| DC blocker | 3 | | |
| State-variable tone filter | 12 | | coefficients at control rate |
| Dry and wet with smoothing | 6 | | plus the dry path's delay line, 2 |
| Safety limiter | 4 to 8 | | a rational soft clip |

A full crusher of this kind, with a 2x drive, a fractional hold, an 8-bit converter table with bit switches, a fold, a
tone filter and separate dry and wet, costs about 100 to 130 operations a sample at most clock settings, of which the
drive's oversampling is half: roughly 40 to 70 ns a sample per channel, well inside a per-instrument budget.

## 12. Open Projects Consulted

| Project | Licence | What was read |
| --- | --- | --- |
| `pichenettes/eurorack` | MIT | `plaits/dsp/fx/sample_rate_reducer.h` (fractional hold with polyBLEP); `plaits/dsp/engine/waveshaping_engine.cc` and `plaits/resources/lookup_tables.py` (256-entry tables addressed by the signal, crossfaded, a Hermite-read fold, pitch-dependent taming); `plaits/dsp/engine/wavetable_engine.cc` (a wave cube with Hermite reads, stepped morph, integrated tables); `clouds/dsp/mu_law.h`, `mu_law.cc` and `granular_processor.cc` (segmented mu-law, 8-bit companded low-fidelity buffers at half rate); `warps/dsp/modulator.cc`, `modulator.h` and `resources/lookup_tables.py` (XOR of two 16-bit signals, a tabulated fold, 6x oversampling) |
| Surge XT, `sst-effects` | GPL-3.0-or-later | `include/sst/voice-effects/distortion/BitCrusher.h`: whole-sample hold with a carried phase, truncation toward zero with a zero-point offset, key-tracked rate and cutoff, a state-variable filter in three modes |
| Surge XT, `sst-waveshapers` | GPL-3.0-or-later | `Wavefolders.h` (piecewise-linear folders with closed-form ADAA, a fourteen-point model of a classic timbre circuit's folder, a linear fold after Vital's), `Effects.h` (a 16-level digital shaper, a table sine fold), `Rectifiers.h` (half- and full-wave with ADAA), `Fuzzes.h` (seeded noise tables), `ADAA.h` (the first-order ADAA helper with a tolerance fallback) |
| Vital (its open source release) | GPL-3.0-or-later | `src/synthesis/effects/distortion.cpp`: soft and hard clip, linear and sine fold, a rounding bit crush, and a whole-sample down-sampler with a carried remainder |
| Airwindows, Chris Johnson | MIT | `DeRez2Proc.cpp` (softened hold, mu-law around truncation), `DeRez3Proc.cpp` (Bezier reconstruction of held points, one knob for two ramps of dry and wet), `BitGlitterProc.cpp` (two crushers at rates a golden ratio apart, a sine soft clip), `BitShiftGainProc.cpp` (gain by powers of two only, bit-exact) |
| Faust libraries | MIT for the functions named; LGPL-2.1 with the Faust exception for `basics.lib` | `aanl.lib`: `triangleFold1/2`, `sineFold1/2` (closed-form ADAA folds with decay), `ADAA1`, `ADAA2`, the hard clip; `misceffects.lib`: `dither`, `dither_shaped`; `basics.lib`: `bitcrusher`, `mulaw_bitcrusher`, `downSample`, `downSampleCV` |
| `chowdsp_utils` | GPL-3.0 | `chowdsp_WestCoastWavefolder.h`: five folding cells, tabulated curve and antiderivatives for second-order ADAA |
| Dexed | GPL-3.0-or-later | `source/engine/EngineMkI.cpp`: log-sine and exponential tables of 10 bits, sign-magnitude operator arithmetic |

Not read: the crushers of Calf, LSP, x42 and VCV Rack's modules; no claims here rest on them. Not verified: the
operation counts and nanosecond figures, which are estimates from the code's arithmetic, not timings; the converter
rates and filter arrangements of early samplers, which are from published descriptions and vary between models.

## 13. References

- ITU-T Recommendation G.711, pulse code modulation of voice frequencies, 1972.
- S. P. Lipshitz, R. A. Wannamaker and J. Vanderkooy, "Quantization and dither: a theoretical survey", Journal of the
  Audio Engineering Society, vol. 40, no. 5, 1992.
- R. A. Wannamaker, "Psychoacoustically optimal noise shaping", Journal of the Audio Engineering Society, vol. 40,
  no. 7/8, 1992.
- B. Widrow and I. Kollár, "Quantization Noise: Roundoff Error in Digital Computation, Signal Processing, Control, and
  Communications", 2008.
- W. Kester (ed.), "Data Conversion Handbook", 2005 (converter architectures, DNL and INL, glitch energy, the zero-order
  hold).
- T. Stilson and J. O. Smith III, "Alias-free digital synthesis of classic analog waveforms", International Computer
  Music Conference, 1996.
- V. Välimäki, J. Pekonen and J. Nam, "Perceptually informed synthesis of bandlimited classical waveforms using
  integrated polynomial interpolation", Journal of the Acoustical Society of America, 2012.
- J. Parker, V. Zavalishin and E. Le Bihan, "Reducing the aliasing of nonlinear waveshaping using continuous-time
  convolution", DAFx, 2016.
- S. Bilbao, F. Esqueda, J. Parker and V. Välimäki, "Antiderivative antialiasing for memoryless nonlinearities", IEEE
  Signal Processing Letters, 2017.
- F. Esqueda, H. Pöntynen, V. Välimäki and J. Parker, a virtual analog model of a classic West Coast timbre circuit's
  wavefolder, DAFx, 2017.
- F. Esqueda, H. Pöntynen, J. Parker and S. Bilbao, "Virtual analog models of two classic wavefolder circuits" (title
  paraphrased), Applied Sciences, 2017.
- C. Kahles, F. Esqueda and V. Välimäki, "Oversampling for nonlinear waveshaping: choosing the right filters", Journal
  of the Audio Engineering Society, 2019.
- A. Simper, technical paper on the linear trapezoidal integrated state-variable filter, 2013.
- V. Zavalishin, "The Art of VA Filter Design", 2012 and later revisions.
