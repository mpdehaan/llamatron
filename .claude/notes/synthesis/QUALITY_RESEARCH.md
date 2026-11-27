# Character and Quality in Virtual-Analog Building Blocks

A chapter on what separates a convincing digital model of an analog voice from a merely correct one: aliasing in
oscillators and shapers, the drift and imperfection that make analog oscillators sound alive, zero-delay-feedback
filters and their nonlinearities, oversampling, antiderivative anti-aliasing, envelopes, the low-pass gate and its
vactrol, the analog drum circuits, low-frequency oscillators and tone controls. Each section gives the principle, the
algorithm, the open implementations that realise it (with their licences), and the cost and hazards in a real-time
audio callback that must not allocate or lock. Costs are counted per sample per voice at 44.1 or 48 kHz unless stated.

Sources are papers (cited by author, title or a plain description of it, and year) and open code under licences
compatible with GPLv3. Where a paper's title names a commercial instrument, the title is paraphrased.

## 1. Aliasing in Oscillators

### 1.1 The problem

A sampled waveform holds only frequencies below half the sample rate. A naive sawtooth, computed as `2 * phase - 1`,
has harmonics falling as 1/n without end; every harmonic above Nyquist folds back to `fs - n f0`, `n f0 - fs` and so
on, landing at frequencies unrelated to the note. At 2 kHz fundamental and 48 kHz, the 13th harmonic (26 kHz) folds to
22 kHz and the 25th (50 kHz) to 2 kHz, at -28 dB; under vibrato the folded partials move in the opposite direction to
the pitch, the "inverse glide" that ears notice long before a spectrum shows it. A square has the same 1/n roll-off on
odd harmonics; a triangle's 1/n² roll-off makes its aliasing about 6 dB an octave smaller but still audible at high
notes; a sine has none.

### 1.2 Band-limited step correction (BLEP and its relatives)

The jump of a saw or square is the only part that holds energy far above Nyquist. Subtracting the difference between
a hard step and a band-limited step ("BLEP", Brandt, "Hard sync without aliasing", ICMC 2001) at each discontinuity
removes most aliasing. Three families:

- **PolyBLEP, two-point.** The residual is a piecewise second-order polynomial spanning one sample either side of the
  jump (Välimäki and Huovilainen, "Antialiasing oscillators in subtractive synthesis", IEEE Signal Processing Magazine
  2007). Very cheap: a compare, a few multiply-adds, only when the phase is within one increment of a jump. It
  suppresses aliasing by roughly 20 to 30 dB in the upper octaves, less near Nyquist; the residual's own spectrum also
  rolls off the top octave slightly. Open: `pichenettes/eurorack`, `stmlib/dsp/polyblep.h` (MIT), with the
  this-sample and next-sample split for jumps that fall between samples.
- **Higher-order polyBLEP and integrated polynomial interpolation.** Residuals of third or fourth order spanning two
  samples either side (Välimäki, Pekonen and Nam, "Perceptually informed synthesis of bandlimited classical waveforms
  using integrated polynomial interpolation", JASA 2012). About 10 to 15 dB better than two-point at the cost of a
  two-sample delay (the correction needs the next jump in advance) and roughly double the arithmetic near a jump.
- **MinBLEP and tabulated BLEPs.** A minimum-phase band-limited step tabulated at high oversampling (Brandt 2001),
  added into a short circular buffer at every jump. Suppression of 60 dB or more; cost is a table read and add of 16 to
  64 taps per jump (not per sample), so cost grows with pitch. Hard sync and arbitrary jump sizes are natural.
- **Elliptic BLEP.** A newer design (Geraint Luff, talk at an audio developers' conference, 2024; code
  `Signalsmith-Audio/elliptic-blep`, MIT) derives the step residual from an elliptic low-pass's impulse response, so
  the correction is a small bank of complex one-poles excited at each jump rather than a table: very high suppression
  at a fixed per-sample cost. Surge's `sst-basic-blocks` (`dsp/EllipticBlepOscillators.h`, GPL-3.0-or-later) carries a
  realisation.

### 1.3 Integrated and differentiated waveforms

- **DPW, differentiated polynomial waveforms** (Välimäki, "Discrete-time synthesis of the sawtooth waveform with
  reduced aliasing", IEEE SPL 2005; Välimäki, Nam, Smith and Abel, "Alias-suppressed oscillators based on
  differentiated polynomial waveforms", IEEE TASLP 2010). Generate the saw's integral (a parabola, order 2) or a higher
  polynomial, then differentiate N-1 times with first differences and rescale by `fs / (4 f0)` for order 2. The
  integral has harmonics falling faster, so less folds; differentiation restores the shape. Order 2 matches two-point
  polyBLEP; order 3 or 4 beats it. Cost is constant per sample and branch-free, which suits SIMD, but the scale factor
  explodes at very low frequencies (precision loss in single precision below ~20 Hz) and fast pitch modulation needs
  care because the differentiator assumes a constant f0. Open: `sst-basic-blocks`, `dsp/DPWSawPulseOscillator.h`
  (GPL-3.0-or-later).
- **BLAMP for corners.** A triangle, a clipped wave or a hard-synced triangle has slope discontinuities. The
  band-limited ramp residual, the integral of the BLEP, corrects them the same way (Esqueda, Välimäki and Bilbao,
  "Rounding corners with BLAMP", DAFx 2016). The correction is scaled by the change of slope times the phase
  increment. Needed for synced triangles and for any wavefolder or clipper applied to an oscillator.

### 1.4 Wavetables and their mip levels

A table oscillator holds each waveform band-limited for a range of fundamentals. With one table an octave, a note at
the bottom of its octave lacks the top octave of harmonics it could have had (audibly duller), or the table is built
for the bottom and aliases at the top. Two remedies: tables a third or half an octave apart (memory grows 3 or 2 times,
still small for 2048-point tables), or crossfading between the two neighbouring mip levels by position within the
octave (two reads a sample). Linear interpolation in a 2048-point table images at about -80 dB for typical content;
cubic Hermite costs four reads and moves images lower, which matters only for very low notes read from short tables.
Higher-order integrated wavetables (Franck and Välimäki, "Higher-order integrated wavetable and sampling synthesis",
JAES 2013) apply the DPW idea to arbitrary tables and allow one table for all pitches. Open: Surge's wavetable
oscillator and Vital's (`mtytel/vital`, GPL-3.0) build mip levels by FFT, zeroing bins above the level's limit.

### 1.5 Costs at a glance

| Method | Per sample, per oscillator | Suppression (upper octaves) | Latency |
| --- | --- | --- | --- |
| Naive | 1 to 2 operations | none | 0 |
| Two-point polyBLEP | ~6 operations, ~15 near a jump | 20 to 30 dB | 0 or 1 sample |
| Fourth-order polyBLEP | ~10, ~30 near a jump | 35 to 45 dB | 2 samples |
| DPW order 3 | ~12, branch-free | 35 to 40 dB | 1 to 2 samples |
| MinBLEP (32 taps) | ~3, plus 32 adds per jump | 60 dB+ | 0 (minimum phase) |
| Elliptic BLEP | ~20 fixed | 80 dB+ | small |
| Mip-mapped table | 2 to 4 reads | set by table design | 0 |

## 2. Analog Drift and Imperfection

What makes several analog oscillators sound alive is not one wobble but several independent imperfections, each at
its own timescale:

1. **Static offset at power-up and per voice.** Each oscillator, and in a polyphonic instrument each voice card, sits a
   few cents from nominal. Drawn once per instrument (or once per voice allocation) from a normal distribution of
   standard deviation 1 to 5 cents.
2. **Thermal drift.** A slow random wander of a few cents over tens of seconds to minutes, larger after switch-on.
   Model: white noise through a one-pole low-pass of very low cutoff, rescaled by the inverse square root of the
   coefficient so that its variance is independent of the coefficient. `sst-basic-blocks`, `dsp/
   OscillatorDriftUnisonCharacter.h` (`DriftLFO`, GPL-3.0-or-later) does exactly this, coefficient 1e-5 a sample and
   scale `1/sqrt(1e-5)`, evaluated at block rate. Independent per oscillator; correlated slightly across oscillators of
   one instrument (a shared component of perhaps a third) since they share a power supply and case temperature.
3. **Cycle-to-cycle jitter.** The exponential converter and the comparator that resets the core add noise to each
   period: a white perturbation of the phase increment of 0.01 to 0.1 % per cycle, drawn at each wrap. Inaudible
   alone; it decorrelates two oscillators tuned in unison so that their beating is never perfectly periodic.
4. **High-note slip.** The exponential converter's bulk emitter resistance makes the top octaves go flat, by a few cents
   at 2 kHz and tens of cents at 8 kHz on a poorly trimmed circuit. Model: subtract `c * f^2` (in cents, f in kHz) or
   use a soft knee in the pitch-to-frequency map.
5. **Saw reset and curvature.** A real saw core discharges its capacitor in a fraction of a microsecond to a few
   microseconds, so the fall is a short ramp, not a jump; and the ramp itself bends slightly because the charging
   current source is imperfect. The finite reset softens the very top harmonics; the curvature adds a little even
   harmonic content. Both are cheap to imitate inside a BLEP oscillator: a reset of finite width is a BLAMP pair
   instead of a BLEP, and curvature is a gentle polynomial on the phase.
6. **Pulse width wander and DC.** Comparator thresholds drift, so a square is never exactly 50 %; output coupling
   capacitors make a one-pole high-pass of a few hertz, which tilts flat tops of low squares.
7. **Free-running phase.** Analog oscillators are never reset by a key; each note starts at whatever phase the
   oscillator is at, so the attack of each note differs. A digital oscillator that starts every note at phase zero
   sounds mechanically identical note to note; starting at a random or free-running phase is the cheap cure.

Cost: drift and jitter are control-rate or once-per-cycle operations; the per-sample cost is nil beyond the phase
increment. The hazard is seeding: for bit-identical offline renders, each random source needs a deterministic seed
derived from the instrument and note, never from a clock.

## 3. Zero-Delay-Feedback Filters

### 3.1 The topology-preserving transform

Vadim Zavalishin, "The Art of VA Filter Design" (revision 2.1.2, 2018), the standard text. An analog filter's block
diagram is kept, and each integrator is replaced by a trapezoidal (bilinear) integrator. The instantaneous loop this
creates is solved algebraically each sample rather than broken with a unit delay. The cutoff is prewarped with
`g = tan(pi fc / fs)`. The one-pole low-pass becomes:

```
v = (x - s) * g / (1 + g);   y = v + s;   s = y + v;
```

Benefits: exact analog magnitude at the cutoff, correct resonance at all cutoffs, and stability under fast modulation,
since the state is the integrator's own and has a physical meaning. The cost of a one-pole is three multiply-adds.

### 3.2 The linear state-variable filter

Andrew Simper's "Linear trapezoidal integrated state variable filter" (2013, freely published technical paper) gives
the most-used form: with `g = tan(pi fc/fs)`, `k = 1/Q`, `a1 = 1/(1 + g(g + k))`, `a2 = g a1`, `a3 = g a2`, each sample
computes `v3 = x - ic2`, `v1 = a1 ic1 + a2 v3`, `v2 = ic2 + a2 ic1 + a3 v3`, updates `ic1 = 2 v1 - ic1`,
`ic2 = 2 v2 - ic2`, and outputs low = v2, band = v1, high = x - k v1 - v2, notch = low + high, peak = low - high, and
the bell and shelf responses as mixes. About ten multiply-adds; the same coefficients serve every mode, so a morphing
multimode is a mix of three outputs. `sst-filters` (GPL-3.0-or-later) holds a realisation and a cascade of them for
steeper slopes.

### 3.3 Solving the nonlinear loop

Real filters saturate: transistor pairs in a ladder, OTAs in a cascade, diodes, an op-amp's rails. Once a
nonlinearity sits inside the zero-delay loop, the loop equation has no closed-form solution. Three levels of rigour:

- **Linearisation at the previous output.** Replace each `tanh(u)` by `u * tanh(u_prev)/u_prev`, a gain worked out
  from the last sample; the loop is then linear and solved as in 3.1. Published by Teemu Voipio (2012) as a cheap
  nonlinear zero-delay method; Zavalishin's book treats the same idea. Cheap (one extra tanh or rational approximation
  per stage) and stable, but the saturation lags a sample, so at high cutoff and high drive the tone differs from the
  true solution and self-oscillation amplitude is slightly off.
- **Newton-Raphson.** Write the loop as `F(y) = 0` and iterate `y -= F(y)/F'(y)`, starting from the previous sample's
  solution. One or two iterations suffice at audio signals because the starting guess is close. Each iteration costs
  one evaluation of each nonlinearity and its derivative (for tanh, `1 - tanh²` is free once tanh is known). Zavalishin
  (chapter 6) derives the ladder and the SVF this way. Cost is two to three times the linearised form.
- **Explicit numerical integration with oversampling.** The ladder's differential equations integrated by fourth-order
  Runge-Kutta at a high internal rate (Stilson and Smith's analysis of the transistor ladder, ICMC 1996; the
  "RK simulation" in `sst-filters/VintageLadders.h`, GPL-3.0-or-later). Accurate, but needs 2 to 4 times
  oversampling and four derivative evaluations a step: the most expensive.

### 3.4 The transistor ladder

Four one-pole stages in series, the fourth stage's output fed back negatively with gain k (0 to 4, self-oscillation at
4 in the linear model). Character comes from:

- **Per-stage saturation.** Huovilainen ("Non-linear digital implementation of the classic transistor ladder filter",
  DAFx 2004) places a tanh at the input of each stage, `y_i += g (tanh(y_{i-1}) - tanh(y_i))`, with the feedback
  through a tanh as well, run at 2x with a half-sample delay compensation in the feedback. D'Angelo and Välimäki
  ("An improved virtual analog model of the classic ladder filter", ICASSP 2013, and "Generalized ladder filter",
  IEEE TASLP 2014) derive from the differential pair that each stage computes `tanh` of its input minus `tanh` of its
  output, scaled by the thermal voltage `2 Vt` (about 52 mV); solved implicitly this reproduces the measured change of
  cutoff with level, the soft compression of a loud input, and a self-oscillation that is a slightly squared sine.
- **Bass loss.** Resonance subtracts the low end because the feedback is in phase at DC: passband gain is `1/(1+k)`.
  Circuits partially compensate (some later designs add `k * x` back at the input); without any compensation, high
  resonance thins the sound by up to 14 dB at the top of the range.
- **Resonance tuning.** In the discrete model the resonant peak sits slightly below the cutoff at high cutoffs and its
  feedback threshold rises; Huovilainen and later models give polynomial corrections in `fc/fs` for both, so that the
  filter self-oscillates at the requested pitch and the resonance control feels the same across the range.
- **Noise floor.** A circuit at full resonance rings up from its own noise; a digital model at zero input stays silent
  unless a tiny noise (about -120 dB) is injected.

Cost, per sample: linearised, about 30 operations plus 5 rational tanh approximations; Newton with two iterations,
about 80; at 2x oversampling, double, plus the resampler.

### 3.5 The diode ladder

The 1980s acid bass machine and several 1970s synthesizers use diode pairs instead of transistor pairs, and their
stages are not buffered from each other: each capacitor's current depends on its neighbours, so the four poles
interact, the first stage typically with half the capacitance. The linear transfer function is not four identical
poles; the resonance is lower and broader and the filter stops short of strong self-oscillation; a high-pass in the
feedback loop (around 100 to 200 Hz) keeps the bass from booming. Sources: Zavalishin's chapter on the diode ladder;
Will Pirkle's application note on a virtual-analog diode ladder (2013); `sst-filters/DiodeLadder.h` (GPL-3.0-or-later);
Vital's `src/synthesis/filters/diode_filter.cpp` (GPL-3.0); Open303 by Robin Schmidt (MIT), which fits the acid
machine's measured response with tuned coefficients, a feedback high-pass and post-filter all-pass, high-pass and notch
for the circuit's coupling.

### 3.6 OTA cascades, Sallen-Key and state-variable characters

- **OTA cascade.** Four buffered OTA-C one-poles: like the transistor ladder, but each stage's saturation is at its
  input differential (tanh of input minus feedback), with a softer, rounder drive, and the cascade of the 1980s
  polysynth chips. Model as the ladder with saturation only at stage inputs and a different scaling.
- **Sallen-Key two-pole with a high-pass in the loop.** The screaming two-pole of 1970s semi-modular monosynths;
  `sst-filters`' Sallen-Key header (GPL-3.0-or-later, after Odin 2 by TheWaveWarden, GPL-3.0-or-later, after Will
  Pirkle's design) solves it in zero-delay form with a saturator on the loop.
- **Saturating SVF.** Clipping the band-pass integrator's state (`sst-filters/ResonanceWarp.h`, GPL-3.0-or-later)
  holds a loud resonant peak round. An alternative character, of the 1970s two-pole SVF polysynths, saturates the
  feedback path through a tanh so that resonance compresses with level.

### 3.7 Coefficient computation

`tan()` is the expensive part of a modulated filter. Options: recompute every 4 to 16 samples and linearly interpolate
`g` between (inaudible as steps at 48 kHz); a rational approximation of `tan(pi x)` accurate to 0.1 % up to 0.45 fs;
or tabulate `g` against pitch in cents (one read and lerp). The resonance threshold and loop gain normalisation
`1/(1 + g(g+k))` should be computed together. Audio-rate filter FM needs per-sample coefficients, so a cheap `tan` is
then essential.

## 4. Oversampling

A nonlinearity inside a filter loop, or a driven shaper, generates harmonics above Nyquist. Oversampling runs the
nonlinear part at a multiple of the rate and filters before returning.

- **How much.** For tanh-type saturation in a filter, 2x removes most audible aliasing (tanh's harmonics fall fast);
  hard clipping and folding need 4x to 8x, or ADAA (section 5) combined with 2x.
- **Linear-phase FIR halfband.** Every other coefficient zero; a 2x stage costs about half the nonzero taps per output
  sample in each direction. 24 to 48 taps give 80 to 100 dB rejection with a transition from 0.4 to 0.6 of the base
  Nyquist. Latency of half the length, constant group delay: harmless outside a feedback loop.
- **Polyphase IIR halfband.** Two parallel chains of first-order all-passes in `z^-2`, one delayed a sample, averaged.
  Laurent de Soras's `hiir` library (WTFPL, compatible) designs coefficients for any rejection; 4 to 6 coefficients a
  chain give 70 to 100 dB at a transition of 0.04 to 0.1. Cost: roughly 8 to 12 multiply-adds per base-rate sample per
  direction, about a third of an equivalent FIR, and latency of about one to three samples, but the phase is not
  linear (inaudible for a filter's output). `sst-filters/HalfRateFilter.h` (GPL-3.0-or-later) is a SIMD realisation in
  this family.
- **Where to oversample.** Only the nonlinear parts: in a ladder, the four stages and their loop; the oscillator can
  run at base rate with BLEP correction and be upsampled into the filter. Upsampling by zero-stuffing plus the halfband
  is enough.
- **Turning it off.** Oversampling can follow the drive and resonance settings: a clean, low-resonance filter gains
  nothing from it.

## 5. Antiderivative Anti-Aliasing (ADAA)

### 5.1 First order

For a memoryless shaper `y = f(x)`, the continuous-time output averaged over each sample period, assuming `x` moves
linearly between samples, is

```
y[n] = (F(x[n]) - F(x[n-1])) / (x[n] - x[n-1])
```

where `F` is the antiderivative of `f` (Parker, Zavalishin and Le Bivic, "Reducing the aliasing of nonlinear
waveshaping using continuous-time convolution", DAFx 2016; Bilbao, Esqueda, Parker and Välimäki, "Antiderivative
antialiasing for memoryless nonlinearities", IEEE SPL 2017). It is a rectangular low-pass on the continuous output:
about 6 dB an octave of extra roll-off on aliases, often worth 2x to 4x of oversampling. When `|x[n] - x[n-1]|` is
below about 1e-5 (single precision) or 1e-9 (double), the division is ill-conditioned; the fallback is
`f((x[n] + x[n-1]) / 2)`. It adds half a sample of delay and a gentle high-frequency droop (the sinc of the
rectangle), about -3.9 dB at Nyquist, which a matched pre-emphasis can offset.

### 5.2 Second order

The second antiderivative gives a triangular kernel, better suppression (12 dB an octave) at the cost of one sample
of delay and a more delicate fallback with two ill-conditioned cases.

### 5.3 Antiderivatives of common curves

| Curve | f(x) | F(x) |
| --- | --- | --- |
| Hard clip at ±1 | `clamp(x)` | `x²/2` inside, `|x| - 1/2` outside |
| tanh | `tanh x` | `ln cosh x`, evaluated as `|x| + ln(1 + e^{-2|x|}) - ln 2` to avoid overflow |
| Rational soft limit | `x(27 + x²)/(27 + 9x²)` | `x²/18 + (4/3) ln(x² + 3)`, from `f = x/9 + 24x/(9x² + 27)` |
| Sine fold | `sin(a x)` | `-cos(a x)/a` |
| Wrap to ±1 | sawtooth of x, period 2 | piecewise `(x - 2k)²/2` on each period, made continuous by adding `k` periods' worth (each period integrates to zero) |
| Quantiser (step size q) | `q round(x/q)` | piecewise linear: `q m x - q² m²/2 + const` on step m, continuous across steps |
| Half-wave rectifier | `max(x, 0)` | `max(x, 0)²/2` |

`chowdsp_utils` (`chowdsp_waveshapers`, GPL-3.0) realises first- and second-order ADAA for tanh, hard clip, sine clip,
soft clip and a full-wave rectifier, with a tabulated option for any curve: `F` (and `F2`) are tabulated once over a
range and read with linear interpolation, which makes arbitrary user curves cheap.

### 5.4 ADAA in feedback and with memory

ADAA's half-sample delay inside a feedback loop detunes and can destabilise the loop. Holters ("Antiderivative
antialiasing for stateful systems", DAFx 2019) extends the idea to systems with state, but the resulting equations are
far more involved; in practice filter loops are oversampled and memoryless shapers outside loops use ADAA, optionally
together with 2x oversampling.

### 5.5 Cost

First-order ADAA costs one evaluation of `F` per sample (instead of `f`), a subtraction and a division (or a
reciprocal), and a branch for the fallback: about two to three times the bare shaper. With `ln cosh`, the `ln` and
`exp` dominate; a tabulated `F` brings it down to two reads and a lerp.

## 6. Distortion, Bitcrushing and Their Character

### 6.1 Drive

- **Symmetry and even harmonics.** A symmetric curve makes odd harmonics only; biasing the input (adding a constant
  before a symmetric curve) makes even harmonics as a single-ended tube or a transistor stage does. The bias produces DC
  that a high-pass (a one-pole DC blocker around 5 to 20 Hz) must remove after the curve, never before.
- **Emphasis.** Pedal and amplifier circuits filter before and after the clipping stage: a high-pass or mid-bump before
  (only the upper mids distort strongly, keeping the bass clean), a low-pass after (rounding fizz). A first-order tilt
  before and its inverse after is a cheap and very effective way to give a single curve a "pedal" voice.
- **Dynamic bias and sag.** In tube circuits the bias point shifts with signal level (grid conduction charges coupling
  capacitors), so loud passages become more asymmetric and slightly compressed, recovering over tens of milliseconds.
  Model: an envelope follower of the input level adding to the bias.
- **Open code.** Airwindows (`airwindows/airwindows`, MIT) holds dozens of small, readable saturation, console and
  tape-flavoured algorithms; `chowdsp_waveshapers` (GPL-3.0) the ADAA curves; `sst-effects` (GPL-3.0-or-later) Surge's
  distortion and waveshaper sets.

### 6.2 Bitcrushing

A bitcrusher combines two degradations:

- **Rate reduction.** A sample-and-hold at a lower rate. The intended sound is the aliasing of the low rate. But a hold
  that only changes on whole base-rate samples jitters when the low rate does not divide the base rate, and its steps
  alias a second time against the base rate. Placing each hold at its fractional time and smoothing the step with a
  BLEP removes both artefacts: `pichenettes/eurorack`, `plaits/dsp/fx/sample_rate_reducer.h` (MIT).
- **Quantisation.** Rounding to fewer bits. At low signal levels, undithered quantisation is not noise but
  distortion that follows the signal and gates to silence as the signal fades below one step. Adding triangular
  (TPDF) dither of one step before rounding turns it into steady hiss, the sound of a converter rather than of a broken
  one. The rounding steps are themselves discontinuities and alias; first-order ADAA of the staircase (section 5.3)
  tames that without changing the stepped character.
- **Converter colour.** Early samplers had no anti-alias filter before their low-rate converters (more aliasing at the
  input), a zero-order hold at the output (a sinc droop, about -4 dB at the low rate's Nyquist) and an analog
  reconstruction low-pass that rounded the steps; 8-bit telephone-style companders (mu-law, A-law) made quantisation
  noise follow the signal level. Each is a filter or a curve and cheap.

## 7. Envelopes

- **The analog contour.** An analog envelope charges a capacitor through a resistor toward a target: each segment is
  `level += (target - level) * coefficient`, an exponential approach. Attack typically aims past full scale (a target of
  1.2 to 1.5 times the peak) and switches to decay when it reaches the peak, giving the slightly convex, fast-finishing
  attack of the hardware; decay and release approach their targets asymptotically, so a "time" is defined to a
  fraction (to -60 dB, or to 1/e). The coefficient for a time T to reach a fraction r is `1 - r^(1/(T fs))`.
- **Retriggering.** An analog envelope restarts its attack from wherever it is, never from zero; a digital envelope
  that resets clicks. Legato modes skip the attack altogether.
- **Clicks.** An attack or release under about 1 ms on a low note produces a click; a minimum slew of 0.5 to 2 ms on the
  amplitude path, or a short raised-cosine fade at note end, avoids it without softening percussive attacks noticeably.
- **Curve controls.** Many instruments expose a curve between linear and exponential per segment; a closed-form curve
  `(exp(c t) - 1)/(exp(c) - 1)` over a normalised segment time is exact and cheap enough evaluated per sample.
- **Closed form versus recursion.** A recursive one-pole is cheapest (one multiply-add) but its result depends on where
  a chunk boundary falls only through rounding; a closed-form envelope (level as a function of time since note-on)
  is independent of chunking by construction and is the choice when offline exports and live playback must match
  exactly. `sst-basic-blocks/modulators/ADSREnvelope.h` (GPL-3.0-or-later) has both an analog (RC) mode and a digital
  mode with curve controls.

## 8. The Low-Pass Gate and the Vactrol

The West Coast low-pass gate is a resistive-opto-isolator circuit: a lamp or LED lights a cadmium-sulfide photocell
whose resistance sets both the gain and the cutoff of a passive or OTA-based two-pole low-pass. Its sound, the
"bongo" or "plonk", comes from the cell:

- **Asymmetric, history-dependent response.** The cell's resistance falls quickly when lit (a few milliseconds) and
  rises slowly when dark (tens to hundreds of milliseconds), and the recovery slows further the longer and brighter the
  cell was lit: a fast strike decays faster than a long-held note. Parker and D'Angelo ("A digital model of a West
  Coast low-pass gate", DAFx 2013) measure the cell and model it as a one-pole whose time constant depends on the
  current state and the direction of change, followed by a nonlinear map from cell state to resistance (roughly a power
  law), then derive the circuit's filter from its components with the resistance as a time-varying parameter.
- **Gain and cutoff together.** As the gate closes, the cutoff falls and the level falls with it, so the end of a note
  is darker as well as quieter, as a plucked or struck object's is. The circuit's own resonance is low; in "lowpass"
  mode a bridged resonance adds a small peak.
- **Implementation.** Per sample: the cell's state update (one-pole with two coefficients chosen by sign), the
  resistance map (a power or exponential, tabulable), the filter coefficient (from the resistance, through `tan` or a
  table) and a two-pole zero-delay low-pass. About 25 operations; with a table for the resistance-to-coefficient map,
  under 20. Open: `pichenettes/eurorack`, `streams/vactrol.cc` (MIT), a light-history model with separate rise and fall
  and a nonlinear decay; and `pichenettes/eurorack`, `plaits/dsp/fx/low_pass_gate.h` (MIT), a compact gate whose
  filter and VCA follow one control.
- **Ageing.** An older cell is slower and less consistent: longer fall, greater dependence on history, and a random
  variation of the light-to-resistance curve from strike to strike of a few percent.

## 9. The Analog Drum Circuits

### 9.1 The bridged-T bass drum

The 1980 analog drum machine's bass drum is a bridged-T network, an active resonator that rings when struck by a short
pulse, with a feedback path that sets decay and a slight upward pitch shift at the strike as the network's operating
point moves. Werner, Abel and Smith ("A physically-informed, circuit-bendable, digital model of a 1980 drum
machine's bass drum circuit", DAFx 2014) model it from the schematic. `pichenettes/eurorack`, `plaits/dsp/drums/
analog_bass_drum.h` (MIT) realises a compact version, read for this chapter:

- a 1 ms excitation pulse of height `3 + 7 accent`, decaying with about a 0.2 ms time constant, high-passed and passed
  through a diode-like asymmetric clip (`0.7x/(1+|x|)` on negative values, doubled first);
- a 6 ms pulse, low-passed, that raises the resonator's frequency at the attack by up to 1.7 times the attack-FM amount
  (the pitch "thump");
- a self-FM path: the resonator's own low-pass output through the diode clip raises the frequency while the drum is
  loud, so the sweep follows the drum's motion rather than a fixed envelope;
- a state-variable band-pass resonator whose Q grows exponentially with decay (`1500 * 2^(80 decay / 12)` scaled), its
  input scaled by `1/f0` so that level stays even across tuning;
- a tone control mixing some of the raw pulse (the click) and a one-pole low-pass at a multiple of the fundamental.

Because the hit is a resonator rung by a pulse, two hits in quick succession interact naturally (the second adds to the
first's ringing), which a sample or a sine-with-envelope cannot do.

### 9.2 The snare

The same machine's snare is two bridged-T resonators (about 180 and 330 Hz on the original) plus high-passed noise
through a VCA ("snappy"). `plaits/dsp/drums/analog_snare_drum.h` (MIT) uses five resonant modes at ratios 1.00, 2.00,
3.18, 4.16 and 5.62 of the fundamental (only the first two below about two thirds of the tone control, the others
fading in above for a more acoustic shell), a 1 ms pulse excitation, half-wave rectified noise through a band-pass at
about 16 times the fundamental with its own decaying envelope, and a soft clip on the shell. The 1983 machine's snare
is brighter and noisier: a pair of triangle-ish oscillators with a pitch drop plus a stronger, longer noise.

### 9.3 Hats and cymbals: six squares

The 1980 machine makes its metal from six square-wave oscillators at inharmonic frequencies summed and band-passed,
then gated by a VCA. `plaits/dsp/drums/hi_hat.h` (MIT) gives the ratios 1.0, 1.304, 1.466, 1.787, 1.932 and 2.536 of a
nominal 414 Hz (run at twice f0), summed and scaled to ±1; a state-variable band-pass whose cutoff follows the tone
control (Q 1, or 3 to 6 when resonant); a two-stage exponential envelope that switches to a faster decay below half
level (the choked tail); an asymmetric VCA (positive half amplified four times, negative a tenth, soft clipped) that
imitates the original's transistor VCA; and a high-pass at the band-pass's cutoff. A cymbal uses the same six squares
through two band-pass paths with different decays (Werner, Abel and Smith's physically-informed cymbal model, ICMC
2014). Naive squares at these frequencies alias audibly only at high tuning; since a hit can be rendered once on
another thread and kept, a 4x render and decimation costs nothing in the callback.

### 9.4 Clap, cowbell, rim and toms

- **Clap.** Filtered noise (band-pass about 1 kHz, Q around 1 to 2) gated by a sawtooth envelope that retriggers three
  or four times about 8 to 12 ms apart, followed by a longer exponential tail of the same noise, the "reverb".
- **Cowbell.** Two square waves at about 540 and 800 Hz through a band-pass around 2.6 kHz, with a short attack burst
  and a two-stage decay.
- **Rim shot.** A very short, high-Q resonator around 1.7 kHz struck with a pulse, plus a touch of noise; a bridged-T
  with almost no decay.
- **Toms and congas.** Bridged-T resonators like the bass drum, at higher pitches, with a small pitch drop and some
  noise for the toms.
- **The synth tom.** The late-1970s drum synthesizers: a sine or triangle oscillator with a long exponential pitch
  sweep (down for the "pew", up rarely), noise mixed in through a filter, a sample-and-hold option that steps the pitch.

### 9.5 Cost

A resonator-based drum costs 10 to 30 operations a sample while it sounds; at a handful of simultaneous hits this is
negligible. Rendering each hit once on another thread and caching it removes even that from the callback, at the
price of losing the hit-to-hit interaction of a continuously running resonator.

## 10. Low-Frequency Oscillators

- **Discontinuous shapes.** A square or saw LFO jumping instantly clicks when it moves amplitude or a cutoff. A slew of
  1 to 5 ms (one-pole) on the LFO output, or a polyBLEP at audio-rate LFO speeds, removes the click while keeping the
  shape at musical rates.
- **Random shapes.** Sample-and-hold (steps), smoothed random (steps through a two-pole low-pass, or cosine
  interpolation between successive random targets, which keeps the target values reached), and random walk (bounded
  integrated noise). Each needs a seeded generator.
- **Per-voice phase and tempo.** Free-running, note-restarted and bar-locked phases; tempo sync derives the rate from
  the tempo and a division and should reset at a known musical point so that exports and live playback agree.
- **Control rate.** Evaluating LFOs once per block of 16 to 64 samples with linear interpolation is inaudible for
  rates under about 20 Hz and saves most of the cost; audio-rate modulation needs per-sample evaluation.
- **Quadrature outputs.** A sine and cosine pair (a rotating phasor `[c, s] = [c cos w - s sin w, s cos w + c sin w]`,
  renormalised occasionally) gives two outputs 90 degrees apart for stereo effects and for rotary or auto-pan motion at
  two multiplications a sample. `sst-basic-blocks/dsp/QuadratureOscillators.h` (GPL-3.0-or-later).

## 11. The Baxandall Tone Control

Peter Baxandall's 1952 circuit places bass and treble networks in the feedback of an inverting amplifier. Its response
is not two independent first-order shelves: the turnover frequencies move with the knob (more boost moves the shelf's
midpoint outward), and the two networks interact slightly in the mids. A faithful digital model derives the circuit's
transfer function by nodal analysis as a function of the two potentiometer positions (second or third order) and maps
it with the bilinear transform with prewarping at the turnover; or builds it as a wave digital filter (`chowdsp_wdf`,
by Jatin Chowdhury, BSD-3-Clause), which keeps the circuit's components as parameters. A cheaper and still natural
approximation uses first-order shelves whose turnover frequency is a function of gain, matching the measured curves at
a few points.

High shelves near Nyquist suffer the bilinear transform's cramping: the response is forced to its Nyquist value too
early. Martin Vicanek's matched designs ("Matched second order digital filters", 2016, with first-order companions in the
same series of notes) match the analog magnitude at Nyquist and keep a treble shelf at 10 kHz true at 48 kHz.

## 12. Numerical Hygiene in the Callback

- **Denormals.** Decaying states in feedback loops fall into subnormal numbers, which are slow on many processors.
  Flush-to-zero flags, or adding and subtracting a tiny constant, or zeroing states below 1e-20, avoid the slowdown.
- **Precision.** Single precision is enough for most audio paths; phases, very low cutoffs (where `g` is tiny and
  `1 - g` loses digits), long feedback delays and DPW scale factors benefit from double.
- **Parameter smoothing.** Every parameter a person moves while a sound plays (cutoff, level, mix, feedback) needs a
  smoother (a one-pole of 5 to 20 ms, or a linear ramp across the block) to avoid zipper noise.
- **Allocation.** Delay lines, tables and oversampling buffers are sized when an instrument is built; the callback
  only reads and writes them.
- **Seeds.** Every random source (noise, drift, jitter, random LFOs) is seeded deterministically from what it belongs
  to, so that a rendered file is bit-identical across runs.
