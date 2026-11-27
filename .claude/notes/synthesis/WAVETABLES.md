# Wavetable Synthesis and the Stacked Saw

A chapter on the table oscillator in all its uses, and on the stacked, detuned saw that became the lead and pad of
dance music: how single-cycle tables and their frames are built, band-limited and read; how frames are morphed and
warped; how tables are generated from harmonics, formulas, drawings and recordings; integrated wavetables; tables as
LFO shapes, drum layers, chip and organ voices and waveshapers; and the stacked saw, from the published measurements
of a 1990s virtual-analog synthesizer's seven-saw oscillator to the denser stacks of later instruments and the unison
of open synthesizers. Each section gives what a musician hears, the principle, the algorithm with its formulas and
constants, the open implementations that realise it (with their licences and files), the cost in a real-time audio
callback that must not allocate or lock, and the hazards.

It builds on `QUALITY_RESEARCH.md` (section 1, oscillator aliasing; section 5, antiderivative anti-aliasing) and
`ENGINES_RESEARCH.md` (sections 2 and 3, unison and wavetables), and goes deeper than both. Sources are papers, cited
by author, title (paraphrased where a title names a product) and year, and open code under licences compatible with
GPLv3. Costs are counted per sample per voice at 44.1 or 48 kHz unless stated; an "operation" is a multiply, add,
compare or load.

Notation used throughout:

| Symbol | Meaning |
| --- | --- |
| `fs` | output sample rate |
| `f0` | the note's fundamental frequency |
| `N` | table length in samples, a power of two |
| `h` | harmonic number; `H` the highest harmonic a table holds |
| `inc` | phase increment in cycles per output sample, `f0 / fs` |
| `step` | read increment in table samples per output sample, `N * f0 / fs` |
| `nu` | a harmonic's frequency in cycles per table sample, `h / N` |

## 1. What a Wavetable Is

### 1.1 The single-cycle table oscillator

One period of a waveform is stored as `N` samples. A phase accumulator advances by `inc` each output sample and wraps
at one; the table is read at `phase * N`, interpolated between stored samples. The pitch is set entirely by `inc`, so
one stored cycle plays every note. Because one stored cycle repeats exactly, every partial is an exact harmonic of
`f0`: a single-cycle table can hold any harmonic spectrum, with any phases, and nothing else. Inharmonic partials
(bells, detuned stacks, noise) need either many tables, long multi-cycle loops (section 5.5) or another engine.

The cleanest accumulator is an unsigned 32-bit integer. It wraps by overflow, never drifts, and splits into an index
and a fraction by shifts:

```
phase   = phase.wrapping_add(inc_fixed)            // inc_fixed = round(inc * 2^32)
index   = phase >> (32 - log2(N))                  // for N = 2048, phase >> 21
frac    = (phase & ((1 << (32 - log2(N))) - 1)) as f32 * 2^-(32 - log2(N))
```

At 48 kHz a 32-bit increment resolves 48000 / 2^32 = 11 microhertz, far below any audible tuning error. Vital
(`mtytel/vital`, GPL-3.0, `src/synthesis/producers/synth_oscillator.cpp`) keeps its unison phases this way, as
`poly_int`, and reads the interpolation fraction from the low bits. A double-precision float phase in `[0, 1)` wrapped
by a subtraction is an equally good choice in a scalar Rust loop; a single-precision float phase is not, since at
phase near 1 its 24-bit mantissa resolves only `2^-24` of a cycle, a tuning error of about 0.003 Hz at 48 kHz that
grows into audible beating between unison voices meant to be exactly in tune.

### 1.2 Frames, position and the wavetable proper

A wavetable in the full sense is an ordered set of single cycles, "frames", typically 64 to 256 of 2048 samples each.
A position control picks a point along the frames; between two frames the oscillator interpolates (section 3). Moving
the position with an envelope or an LFO changes the timbre through the note, which is the wavetable synthesizer's
signature: a sound that evolves without a filter. A 1980s wavetable synthesizer stored short eight-bit cycles of about
a hundred samples, a few dozen to a table, and stepped from one cycle to the next without interpolating, so that a
swept position was heard as a staircase of timbres; a per-voice sample clock that followed the pitch meant its
harmonics never folded, and the steps' images were left to an analog filter. Later instruments interpolated.

### 1.3 Where tables serve an instrument

- **Oscillators**: any harmonic waveform, morphing through frames, with warps (sections 2 to 4).
- **LFO and envelope shapes**: drawn curves read at sub-audio rates (section 8.1).
- **Drum layers**: pitched bodies swept fast through mip levels, one-shot transients, noise (section 8.2).
- **Chip voices**: a console's or computer's wave memory and its uneven converter, kept as stepped as the chip was
  and no further (section 8.3).
- **Organ voices**: drawbar or divider sums held as one cycle (section 8.4).
- **Waveshaping by table**: a transfer curve, a folder, Chebyshev polynomials (section 8.5).
- **Stacked saws**: many reads of one saw table, or one long ensemble table (sections 9 to 13).

## 2. Table Construction

### 2.1 Table size

A table of `N` real samples holds harmonics 1 to `N/2 - 1` (bin `N/2`, the table's own Nyquist, is set to zero because
its phase is undefined). A note keeps every harmonic up to the output Nyquist only if `N/2 >= fs / (2 f0)`, that is `N
>= fs / f0`. A 2048-sample table is full-band down to 23.4 Hz at 48 kHz and 21.5 Hz at 44.1 kHz, below the lowest
musical bass note; 4096 reaches 11.7 Hz, useful only for sub-bass drones. Smaller tables (256, 512) are full-band only
above 190 Hz and 95 Hz and sound dull in the bass. 2048 is the common size for exchanged wavetable files and for both
Vital (`WaveFrame::kWaveformBits = 11`, `src/synthesis/lookups/wave_frame.h`) and Surge XT (`max_wtable_size = 4096`,
files usually 2048; `surge-synthesizer/surge`, GPL-3.0-or-later, `src/common/dsp/Wavetable.h`).

Memory at single precision: one 2048-sample cycle is 8 KB, which fits a CPU's first-level data cache (32 to 48 KB)
together with its neighbour frame and their neighbouring mip levels. 256 frames are 2 MB before mip levels.

### 2.2 Band-limited mip levels by FFT

A table read at a high pitch must not hold harmonics that land above `fs/2`. The standard remedy keeps, for each
waveform or frame, a set of mip levels, each holding only the harmonics that stay under Nyquist over a range of
fundamentals. Built by FFT:

1. Take the cycle's real FFT: `X[h]` for `h = 0 .. N/2`.
2. Set `X[0] = 0` (no offset) and `X[N/2] = 0`.
3. For level `l`, serving fundamentals up to `f_top(l)`, keep `h <= H(l) = floor(fs / (2 f_top(l)))` and zero the
   rest.
4. Inverse FFT; scale (section 2.6).

The level must be built for the top of its range: built for the bottom, its upper harmonics fold back as the note
rises through the range. Choosing the level from the highest pitch the oscillator will reach over the coming block,
including pitch modulation, an FM index's sideband reach or an arpeggio's highest step, keeps modulated notes clean.

**Levels per octave.** With one level an octave, a note at the bottom of its octave reads a table built for twice its
frequency, so its spectrum stops at `fs / 4`: 12 kHz at 48 kHz, 11 kHz at 44.1 kHz. A bright saw played just above a
level boundary is audibly duller than one just below the next boundary, and a slow glide steps in brightness once an
octave. The highest frequency present at a level's bottom is `fs / (2 r)` for `r` levels an octave spaced by
`2^(1/r)`:

| Levels per octave | Top of spectrum at a level's bottom, 48 kHz | 44.1 kHz | Memory (relative) |
| --- | --- | --- | --- |
| 1 | 12.0 kHz | 11.0 kHz | 1 |
| 2 | 17.0 kHz | 15.6 kHz | 2 |
| 3 | 19.0 kHz | 17.5 kHz | 3 |
| crossfaded pair of 1 an octave | rises from 12.0 kHz to 24 kHz as the note falls, smoothly | | 1, two reads |

**An allowance for inaudible aliases.** A harmonic at `F` between `fs/2` and `fs` folds to `fs - F`. If `fs - F` stays
above 20 kHz, the fold is inaudible on its own, so a level may keep harmonics up to `fs - 20 kHz` (28 kHz at 48 kHz,
24.1 kHz at 44.1 kHz) at its top note. At 48 kHz this widens a one-an-octave level's bottom from 12 to 14 kHz. The
folded energy is still there, though: a later nonlinearity (drive, a saturating filter) intermodulates it down into
hearing, so the allowance suits a clean path only.

**Halving lengths.** A level holding `H` harmonics needs only `2H + 2` samples or more. Surge XT halves the table
length at each level (`Wavetable::MipMapWT` in `src/common/dsp/Wavetable.cpp`), filtering each level from the one
above with a 63-tap half-band low-pass (`hrfilter`) and keeping every second sample, one level an octave; the levels
of a frame then cost `N + N/2 + N/4 + ... ~ 2N` samples. Halving keeps the ratio of table rate to highest harmonic
constant, so interpolation quality (section 2.5) is the same at every level. The half-band route needs no FFT but its
filter's transition band leaves the level's top harmonics slightly attenuated; the FFT route is exact. Full-length
levels (each `N` samples) cost `L * N` and read with better image suppression at the higher levels, since their few
harmonics are heavily oversampled.

Surge chooses its level from the read increment: it raises the level while `dt * pitch_mult_inv * 2^level < 0.5 *
1.8` (`wtbias = 1.8` in `WavetableOscillator::convolute`, `src/common/dsp/oscillators/WavetableOscillator.cpp`), and
its oscillators run at twice the output rate (`OSC_OVERSAMPLING = 2`, `src/common/globals.h`), so the bias lets some
energy land between the audio band and the oversampled Nyquist, where the decimation filter removes it.

### 2.3 Crossfading levels

Reading the two levels around the note and mixing them by the note's place within the octave turns the once-an-octave
step in brightness into a smooth slope:

```
octave   = log2(f_max / f_lowest)          // f_max: highest pitch this block
level    = floor(octave)
w        = octave - level
out      = (1 - w) * read(level, phase) + w * read(level + 1, phase)
```

With both levels built for their own tops, nothing aliases and the top of the spectrum at any note lies between the
two levels' limits. The cost is a second read (double the memory traffic) and, if `w` is held per block, nothing else;
`w` must move smoothly (held per block and ramped, or per sample) or the brightness zips. The alternative, building
each level for the bottom of its octave and fading it out towards the top, keeps the full spectrum at the bottom but
lets the outgoing level alias, reduced by its weight, through the top part of each octave.

### 2.4 Exact band-limits per voice: spectra built per block

Vital keeps each frame as a spectrum and makes the time-domain cycle each voice reads afresh, by inverse FFT, every 7
ms (`kWavetableFadeTime = 0.007` in `synth_oscillator.cpp`), crossfading from the previous buffer to the new one over
that time. Its harmonic limit for the voice is `last_harmonic = N * 2^-(12 - log2(1 / inc))`, which simplifies to `1 /
(2 inc)`: exactly the harmonics under Nyquist for that voice's pitch at that moment, with no octave steps at all
(`computeSpectralWaveBufferPair`). Because the cycle is rebuilt per block, the same pass applies any spectral warp
(section 4.4) for free, and every voice is cut to its own pitch.

The cost is one 2048-point real inverse FFT per distinct buffer per block, about `(N/2) log2(N) * 5 = 56 000` floating
operations per 7 ms (336 samples at 48 kHz), so roughly 170 operations a sample per buffer, plus two buffers of `N +
3` samples per voice. Vital shares one buffer across a voice's unison stack unless frame spread or a spectral morph
differs per unison voice ("spectral unison"). In Rust, `rustfft` (MIT or Apache-2.0) runs a planned transform with
caller-supplied scratch (`process_with_scratch`), so a plan and buffers made when the instrument is compiled allow an
inverse transform in the callback without allocating. A fast upward glide may outrun one 7 ms block and alias briefly;
choosing the limit from the block's highest pitch, as in section 2.2, prevents it.

### 2.5 Interpolation orders and their image levels

Reading between stored samples is resampling; the interpolator is a continuous-time low-pass whose stopband sets how
much of each harmonic's images (at `k*N +- h` in table harmonics) survives and folds into the output. For a harmonic
at `nu = h / N` cycles per table sample, the table below gives the passband loss at `nu` and the level of the worst
first image relative to the harmonic itself, computed from each kernel's continuous Fourier transform:

| `nu` (table oversampling) | Linear: loss, image | 4-point Catmull-Rom: loss, image | 4-point Lagrange (cubic): loss, image | 8-point Hann-windowed sinc: loss, image |
| --- | --- | --- | --- | --- |
| 1/64 (32x) | 0.01 dB, -72 dB | 0.00 dB, -102 dB | 0.00 dB, -127 dB | 0.01 dB, -63 dB |
| 1/16 (8x) | 0.11 dB, -47 dB | 0.00 dB, -64 dB | 0.00 dB, -78 dB | 0.00 dB, -70 dB |
| 1/8 (4x) | 0.45 dB, -34 dB | 0.04 dB, -44 dB | 0.05 dB, -53 dB | 0.02 dB, -55 dB |
| 1/4 (2x) | 1.8 dB, -19 dB | 0.55 dB, -24 dB | 0.66 dB, -28 dB | 0.06 dB, -44 dB |
| 0.4 | 4.8 dB, -7 dB | 2.9 dB, -8 dB | 3.4 dB, -10 dB | 1.4 dB, -15 dB |

How this is heard depends on the waveform. A saw's harmonic `h` has level `1/h`, and it is present only while
`h f0 < fs/2`, so the worst case is the low note whose upper harmonics sit high in the table: a 30 Hz saw in a
2048-sample table at 48 kHz holds harmonic 800 at `nu = 0.39`, at -58 dB below the fundamental, with linear
interpolation dropping it a further 5 dB and leaving an image only 7 dB under it, at about -65 dB overall, folded to
an unrelated frequency. Summed over all harmonics the linear interpolator's images sit around -60 to -80 dB under a
bass saw's fundamental, inaudible under the saw itself but measurable; at higher levels, whose few harmonics are
heavily oversampled, linear is effectively perfect. The passband loss matters more than the images for the brightest
low notes: linear interpolation dulls the top octave of a full-band bass table by 2 to 5 dB.

Kernels, for a fraction `t` in `[0, 1)` between `y0` and `y1`, with neighbours `ym1` and `y2`:

```
linear:        y0 + t (y1 - y0)
Catmull-Rom:   y0 + 0.5 t (y1 - ym1 + t (2 ym1 - 5 y0 + 4 y1 - y2 + t (3 (y0 - y1) + y2 - ym1)))
cubic Lagrange: c1 = y1 - ym1/3 - y0/2 - y2/6;  c2 = (ym1 + y1)/2 - y0;  c3 = (y2 - ym1)/6 + (y0 - y1)/2
               y0 + t (c1 + t (c2 + t c3))
```

Linear costs two loads and two operations; the cubics four loads and about ten operations. Vital reads with a
Catmull-Rom matrix (`getCatmullInterpolationMatrix`, used by `interpolateBuffers`) and stores `N + 3` samples
(`kExtraValues = 3` in `wavetable.h`) so that the four-point read never wraps by a mask; the same guard samples suit a
Rust slice read `table[index .. index + 4]` with the index unmasked. Dexed's `msfa` sine (`asb2m10/dexed`,
`source/msfa/sin.h`, Apache-2.0, compatible with GPLv3) stores each value interleaved with the difference to the next
(`SIN_DELTA`), so a linear read is one load pair from one cache line and one multiply-add in fixed point, with a
1024-entry table. Odd-order Lagrange interpolators suppress images better than even orders and are the choice of
Franck and Välimäki for integrated tables (section 6).

### 2.6 Normalisation, offset and ringing

**Offset.** A table with a nonzero average puts a constant under the signal; it thumps when the amp envelope opens,
shifts a following saturator off centre, and integrates without limit in an integrated table (section 6). Setting
`X[0] = 0` before building removes it. Asymmetric waves (a narrow pulse) look shifted afterwards but sound the same.
LFO tables are the exception: a unipolar shape keeps its offset.

**One gain for every level.** Truncating a waveform's harmonics changes its peak (the Gibbs overshoot), so scaling
each mip level to its own peak gives each level a different loudness. A saw truncated to `K` harmonics, `sum sin(h
x)/h`, peaks at:

| Harmonics kept | 1 | 2 | 3 | 4 | 8 | 16 | 64 | 512 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Peak | 1.000 | 1.299 | 1.443 | 1.527 | 1.674 | 1.759 | 1.828 | 1.849 |
| Fundamental after peak scaling | 0 dB | -2.3 dB | -3.2 dB | -3.7 dB | -4.5 dB | -4.9 dB | -5.2 dB | -5.3 dB |

Scaled each to a peak of one, the top levels of a saw (one to four harmonics, notes above about 3 kHz at 48 kHz) play
2 to 5 dB louder than its bass, with a level step at each boundary that a glide or vibrato across it makes audible.
The remedy is one gain for all of a frame's levels, the one that brings the full-band level to its peak, so that each
harmonic keeps its amplitude in every level; the top levels then peak below one, which is correct. Vital normalises
each frame's time-domain cycle by its peak about zero (`WaveFrame::normalize`, `getMaxZeroOffset`) once, before the
per-block spectra, so its band-limited buffers keep each harmonic's level.

**Across frames.** Scaling every frame to the same peak makes a scan through very different frames change loudness,
since a peaky frame (a pulse) has less power than a square at the same peak; scaling to the same RMS keeps loudness
even but lets peaks vary, which the voice's headroom must absorb. A table of related frames, such as one resynthesised
from a recording, keeps its own relative levels under one gain for the whole table.

**Ringing.** Truncation makes ripples around a jump, nine percent of the jump on each side. The Lanczos sigma factor,
multiplying harmonic `h` of `K` by `sinc(h / (K + 1))`, smooths the ripple at the cost of rolling off the top
harmonics, and differently at each level, which reads as a brightness change between levels; the plain truncation is
the faithful band-limited wave and the usual choice.

### 2.7 Phase alignment of frames

Two frames with similar magnitude spectra but different harmonic phases (two cycles cut from a recording at
different points, or a saw and its time-reversed copy) partly cancel when crossfaded in time (section 3.1). Aligning
frames before use removes most of the cancellation:

- **Fundamental alignment**: rotate each frame circularly so that its fundamental's phase is the same, by shifting
  `-phi1 / (2 pi) * N` samples; the shape is kept.
- **Cross-correlation alignment**: rotate each frame to the shift that maximises its correlation with the previous
  frame, which follows a recording's own drift.
- **Phase replacement**: give every frame the harmonic phases of one reference frame (or zero phase, all cosines);
  the timbre is kept for steady sounds (the ear is nearly phase-deaf for a steady harmonic tone) but the waveform
  changes, and a pulse or saw so treated loses its jump and gains a large peak. Vital's phase modifier
  (`src/common/wavetable/phase_modifier.cpp`) offers harmonic, even/odd and clearing styles applied per frame.

## 3. Morphing Between Frames

### 3.1 Crossfade morphing

With position `p` between frame `a` and frame `a + 1`, `t = p - a`:

```
out = (1 - t) * read(frame a, phase) + t * read(frame a + 1, phase)
```

It is cheap (two reads, or four with mip crossfading) and exact at the frames. Between them each harmonic's complex
amplitude is the straight-line mix of the two, whose magnitude is

```
|(1 - t) A e^(i alpha) + t B e^(i beta)| = sqrt((1 - t)^2 A^2 + t^2 B^2 + 2 t (1 - t) A B cos(alpha - beta))
```

so a harmonic whose phase differs by half a cycle between the frames dips to `|(1 - t) A - t B|`, silent midway when
`A = B`: a crossfade between a saw and an inverted saw passes through silence. Phase-aligned frames (section 2.7)
avoid this. Surge XT's wavetable oscillator crossfades between neighbouring frames (`tableipol` in
`WavetableOscillator.cpp`).

### 3.2 Spectral morphing

Interpolating magnitudes and phases separately keeps the magnitude between the frames' magnitudes whatever their
phases. Vital's frequency-domain keyframe interpolation (`WaveSourceKeyframe::linearFrequencyInterpolate`,
`src/common/wavetable/wave_source.cpp`) interpolates the square roots of the magnitudes and squares the result, which
tracks loudness more evenly than straight magnitudes, and moves each phase along the shorter arc:

```
m      = ((1 - t) sqrt|A| + t sqrt|B|)^2
dphi   = arg(conj(A) * B)                   // shorter arc, in (-pi, pi]
phi    = arg(A) + t * dphi                  // arg(B) when |A| = 0
X      = m * e^(i phi)
```

A cubic version through four keyframes (`cubicFrequencyInterpolate`) smooths the path through several frames. Spectral
morphing costs an inverse FFT per new cycle, so it is done when the table is built (to make in-between frames) or per
block (section 2.4), never per sample. It sounds smoother through very different frames and keeps loudness better;
its weakness is that a jump in the waveform (a saw's edge) moves continuously in time as the phases rotate, which
reads as a brief chorus-like smear during a fast sweep.

### 3.3 Frame count and in-between frames

A table of a few keyframes is usually expanded, when built, to 64 or 256 frames by spectral or time interpolation, so
that the oscillator's per-sample morph is only a crossfade between near-identical neighbours, where cancellation
cannot arise. Vital renders its keyframes into 257 frames (`kNumOscillatorWaveFrames`) and, in the oscillator, takes
the integer frame per 7 ms buffer, the crossfade between successive buffers doing the interpolation in time
(`wave_index = toInt(clamp(frame, ...))` in `setFourierWaveBuffers`). Memory grows with frames times levels; building
in-between frames is block or build-time work.

### 3.4 Audio-rate position modulation and its aliasing

Modulating the position `t(n)` at audio rate turns the crossfade into amplitude modulation of the difference between
frames:

```
out = read(a) + t(n) * (read(a + 1) - read(a))
```

The difference wave's harmonics gain sidebands at `h f0 +- f_mod` and its multiples (a sine modulator gives
first-order sidebands only; a jumping modulator, many). A level cut for `f0` alone lets the upper sidebands of its top
harmonics cross Nyquist; the safe level is chosen for `H f0 + f_mod` (for a modulator with harmonics, its highest
significant one). A position that jumps between frames without crossfading (nearest-frame reading) puts a step into
the output at every frame change, a zipper that becomes a buzz at audio rate; the 1980s stepped sound is this, and is
wanted only as that instrument's character. Vital's per-buffer frame choice limits frame modulation to its 7 ms buffer
rate, crossfaded, so fast frame modulation there is smoothed rather than aliased.

### 3.5 Stepped scanning as a sound

Reading the nearest frame, with no interpolation, and moving the position by an envelope gives the staircase sweep of
the early wavetable instruments. Kept deliberately, the steps are smoothed over a millisecond or two (a short
crossfade at each frame change) to keep the timbral staircase without the click.

## 4. Warps

A warp changes the waveform as it is read: by moving the read phase (phase warps), by reshaping the read value
(amplitude warps), or by changing the spectrum before the cycle is made (spectral warps).

### 4.1 Phase warps

Each maps the phase `x` in `[0, 1)` to a read phase `x'`. Vital's distortion types (`synth_oscillator.cpp`,
`syncPhase`, `quantizePhase`, `bendPhase`, `squeezePhase`, `pulseWidthPhase`, with `halfSinWindow` and
`pulseWidthWindow`) give the standard set:

- **Sync**: `x' = frac(r x)`, `r` from 1 to 16 (`kMaxSync = 16`). The table restarts `r` times a cycle, like a hard-
  synced oscillator; the formant moves with `r` while the pitch stays. The table must be band-limited for `r f0`,
  since it is read `r` times faster; Vital multiplies the voice's increment by the sync ratio when it chooses its
  harmonic limit (`frequency_mult` in `setFourierWaveBuffers`). The restart itself is a jump the table cannot
  band-limit; a BLEP of size `table(0) - table(at reset)` at the reset (`QUALITY_RESEARCH.md`, 1.2) corrects it.
- **Formant (windowed sync)**: sync multiplied by a half-sine window, `sin(pi x)` over the cycle, so the output
  returns to zero at each true cycle's end and the reset is continuous: a vocal, resonant sweep with far less aliasing
  than raw sync.
- **Bend**: a cubic phase map through `(0, 0)` and `(1, 1)` whose middle slope is set by the amount, crowding the
  cycle towards one end; harmonics brighten smoothly. Vital's form, with `d` the amount and `u = x + 1/2` (its phase
  is centred): `u' = u^3 + (3d + 2(d - d^2)) (u^2 - u^3) + (3d - 2(d - d^2)) (u - 2u^2 + u^3)`.
- **Squeeze**: a piecewise-linear map with a pivot that compresses the first part of each half-cycle and stretches
  the rest.
- **Pulse width**: `x' = min(x / w, 1)` with the output held at zero after `x = w`: the cycle plays in the first `w`
  of the period and is silent after, a "pulse width" for any table. The end of the played part is a jump unless the
  table ends at zero.
- **Quantize**: `x' = floor(q x) / q`: a staircase phase, a sample-and-hold of the cycle, deliberately aliasing,
  a bit-reduced character.
- **Mirror**: `x' = 1 - |2x - 1|`: the cycle plays forward then backward, giving a wave symmetric about its middle (a
  cosine series, even about the centre); its content doubles, so the table is band-limited for `2 f0`, and the turn
  is a corner (a slope reversal) unless the table's ends are flat.
- **Remap**: any monotonic curve, drawn or a power law, `x' = (e^(p x) - 1)/(e^p - 1)` (Vital's `powerScale`),
  stretching one part of the cycle.
- **Horizontal skew**: Surge XT moves its read rate through the cycle by `rate = 1 + s * 4 x (x - 1)(2x - 1) *
  sqrt(27/4)` (`WavetableOscillator::convolute`), a smooth cubic that hurries one half and lingers in the other.

Every phase warp speeds the read through part of the cycle, so the local read rate exceeds `f0` and the band-limited
table aliases there. The worst local speed-up `s_max = max dx'/dx` sets the needed level: a table cut for
`s_max * f0` stays clean. For bend and remap at strong settings `s_max` reaches 3 to 10, so the warp costs brightness
in the low levels it forces, or aliasing where it is ignored. Warps with corners (squeeze, mirror, pulse width) add
slope discontinuities that only BLAMP or oversampling removes.

### 4.2 Phase distortion

The phase-distortion synthesizers of the mid-1980s read a cosine through a piecewise-linear phase with a knee at `d`:

```
x' = 0.5 x / d                      for x < d
x' = 0.5 + 0.5 (x - d) / (1 - d)    for x >= d
out = -cos(2 pi x')
```

At `d = 0.5` it is a cosine; as `d` falls the first half-cycle shortens and the wave approaches a saw, with brightness
rising as about `1/d` harmonics. Other maps give square-like, pulse-like and resonant shapes (a windowed, sped-up
cosine as in the formant warp). Read from a sine table, the cosine itself never aliases, but the warped wave's
harmonics extend to roughly `f0 / d`; the knee is a slope discontinuity of size `0.5/d - 0.5/(1 - d)`, which a BLAMP
corrects, or `d` is held above `f0 / (fs/2)` times a margin so that the brightest setting stays under Nyquist.
Enveloping `d` gives the instrument's filter-like sweep without a filter.

### 4.3 FM, PM and ring modulation of a table

Phase modulation of a table reads `table(x + I * m(n))` with `m` another oscillator. Harmonic `h` of the table then
has instantaneous frequency `h (f0 + I f_m cos(...))`, so the table level must be chosen for `f0 + I f_m` (the
carrier's greatest instantaneous rate) rather than `f0`, and the sidebands of the top harmonics, about `(I + 1) f_m`
either side by Carson's rule, still need room under Nyquist; a high index on a bright table aliases whatever level is
chosen, and oversampling is the remedy. Vital scales its FM phase offset by a fixed depth (`kFmPhaseMult`,
`kMaxFmModulation = 48`) and offers FM from either other oscillator or the sample. Ring modulation multiplies the
table's output by another oscillator, `out * lerp(1, m(n), amount)` (Vital's `rmWindow`), adding sidebands `h f0 +-
f_m` with no phase effect. Cost: one more read and a multiply-add.

### 4.4 Spectral warps

Applied to a frame's spectrum before the cycle is made, at build time or per block (section 2.4). Vital's set
(`src/synthesis/producers/spectral_morph.h`):

- **Formant shift ("vocode")**: harmonic `h` takes the magnitude the spectrum had at `h * s`, interpolated, keeping
  the harmonics where they are: the spectral envelope (the formants) stretches or shrinks while the pitch holds, the
  table's answer to a vowel shift. With `s > 1` the upper harmonics fall silent; Vital limits the last harmonic to `N
  / (2 s)` (`evenOddVocodeMorph`), with an even/odd variant.
- **Harmonic stretch and inharmonic stretch**: move partial `h` towards `h^k` or a stretched series. A single cycle
  holds only exact harmonics, so the stretched partials are rounded to the nearest bin and the effect is a spectral
  remapping rather than true inharmonicity; true stretched partials need a long loop table (section 5.5).
- **Smear**: each harmonic's magnitude is mixed with a running value carried up the spectrum,
  `a <- lerp(A[h], a, smear)`, `a <- a (h + 0.25)/h` (`smearMorph`): peaks spread upward, a softened, blurred timbre.
- **Spectral low-pass and high-pass**: harmonics above or below a cutoff are zeroed, the edge harmonic scaled by the
  cutoff's fraction (`lowPassMorph`, `highPassMorph`): a brick-wall filter that tracks the note exactly, with no
  resonance and no phase shift.
- **Phase dispersion**: each harmonic's phase is turned by an amount growing with the square of its distance from a
  centre harmonic (`phaseMorph`, `kCenterMorph = 24`): the timbre barely changes when steady, but the waveform's
  energy spreads in time, softening a jump's attack and lowering the peak; in unison it decorrelates the voices'
  waveforms.
- **Random amplitudes**: each harmonic's magnitude moved towards a stored random value (`kRandomAmplitudeStages =
  16`), a "shimmer" when the amount moves.
- **Skew across frames**: each harmonic is taken from a different frame, the offset growing with `log2(h)`
  (`wavetableSkewMorph`, `kSkewScale = 16`): the upper harmonics run ahead or behind through the table.
- **Shepard**: harmonics faded between `h` and `2h` across the amount, so that a rising amount sounds like an endless
  climb (`shepardMorph`).

What the spectral warps share is exact band-limiting: whatever they do, the cycle is built with no harmonic over the
limit, so they never alias. Their cost is the FFT, never the sample loop.

### 4.5 Amplitude warps

A curve applied to the read value: Surge XT's vertical skew and saturation,
`x <- x - a x^2 + a` then `x <- clamp(x (1 - c) + c x^3, -1, 1)` (`distort_level` in `WavetableOscillator.cpp`), or
any waveshaper. These generate new harmonics after the band-limiting, so they alias as a waveshaper does
(`QUALITY_RESEARCH.md`, sections 4 to 6). Applied to the stored cycle at build time instead, and band-limited
afterwards, the same curve does not alias, but then it cannot move per sample.

### 4.6 Pulse-width modulation from one saw table

The difference of a saw and the same saw delayed by `w` of a cycle is a pulse of width `w`:

```
pulse(x, w) = saw(x) - saw(frac(x + w))   // rising saw, -1 to 1: -2w, then 2 - 2w for a cycle's last w
```

The difference is already free of offset, with a height of two; adding `2w - 1` moves it to levels of -1 and 1 at the
cost of an offset that changes with the width. Both reads are band-limited, so the pulse is too, at every width, and
the width can move per sample without aliasing. Cost: two reads and three operations. The same identity with two
different tables gives "two-oscillator" shapes from one phase.

## 5. Generating Tables

### 5.1 Additive

A table from harmonic amplitudes `A[h]` and phases `phi[h]`, by inverse FFT of `X[h] = A[h] e^(i phi[h]) * N / 2`:

| Wave | `A[h]` | Harmonics | Phase |
| --- | --- | --- | --- |
| Saw (rising ramp from -1 to 1) | `2 / (pi h)` | all | negative sine phase: `2x - 1 = -(2/pi) sum sin(2 pi h x)/h` |
| Square | `4 / (pi h)` | odd | sine phase |
| Triangle | `8 / (pi h)^2` | odd | alternating sign, sine phase |
| Pulse of width `w`, levels -1 and 1 | `(4 / (pi h)) |sin(pi h w)|` | all, nulls where `h w` is whole | cosine phase about the pulse centre |
| Organ drawbars | each drawbar's level at its harmonic | see section 8.4 | free, usually zero |

Additive construction is exact and always band-limited by construction: the table simply holds no harmonic above the
level's limit. Changing amplitudes live (an additive "drawbar" or a harmonic slider bank) rebuilds the table off the
callback and swaps it (section 7.3), or, if it must move per sample, becomes an additive oscillator bank
(`ENGINES_RESEARCH.md`, 4.1) instead.

### 5.2 Formulas

A waveform written as a function of phase (a polynomial, a sum of shaped sines, a piecewise expression) is sampled at
several times the table length, filtered and decimated, or sampled at `N` and band-limited by FFT. Sampling a formula
with a jump straight at `N` points leaves the jump's harmonics above `N/2` folded into the table itself, which no
later mip level removes; sampling at 8 or 16 times `N` and keeping only the FFT bins up to `N/2` gives a clean table.
Surge XT evaluates scripted wavetables per frame (`WavetableScriptEvaluator`, `src/common/dsp/`), with the frame index
as a variable so that one expression gives a morphing table.

### 5.3 Drawn curves

A drawn cycle is a list of points with a curvature per segment. Vital's line source (`wave_line_source.cpp`) and its
warp modifier shape segments with the power curve `(e^(p u) - 1)/(e^p - 1)` (`highResPowerScale` in
`wave_warp_modifier.cpp`), `p = 0` a straight line. The drawing is rendered at the table length, converted to a
spectrum, and band-limited as any table; a drawn vertical step is a jump with a saw's harmonics, and a drawn corner a
triangle's. Smoothing the drawing (a few samples of moving average, or the Lanczos factor) trades edge brightness for
less ringing. The same drawn shapes serve as LFO and envelope curves without band-limiting (section 8.1).

### 5.4 From analysis of a sample

Turning a recording into a wavetable:

1. **Find the period.** Autocorrelation or the difference function of YIN (de Cheveigné and Kawahara, "YIN, a
   fundamental frequency estimator for speech and music", JASA 2002). Vital's pitch detector
   (`src/common/wavetable/pitch_detector.cpp`) searches periods from 300 samples up, scoring each by the squared
   difference between successive periods plus a small penalty on a change of average (`kDcDeltaErrorMultiplier =
   0.015`), then refines in tenths of a sample.
2. **Cut cycles.** One cycle (or the average of several) at each of a series of points through the sound, each cut
   starting at the same feature (an upward zero crossing of the fundamental, or the shift that best correlates with
   the previous cycle) so that the frames are phase-aligned.
3. **Resample each cycle to `N` samples.** A period of non-integer length is resampled with a windowed-sinc
   interpolator or by taking the DFT of the cycle over its exact length; linear resampling dulls and aliases.
4. **Band-limit and normalise** as any table, one gain for the whole table.

Vital's file source offers the ways a recording's slices become frames (`file_source.cpp`): blending successive
windows ("wave blend"), splicing at the detected pitch ("pitch splice"), and frequency- or time-domain interpolation
between slices. Fitting a few wavetables and their time-varying weights to a recorded instrument's harmonic analysis,
so that a small number of frames reproduces a tone's evolution, is the subject of Horner, Beauchamp and Haken,
"Methods for multiple wavetable synthesis of musical instrument tones" (JAES 1993), which finds the frames by search
and the weights by least squares. A table made from a sample keeps its timbre only within an octave or so of the
recorded pitch, because the formants move with the pitch (section 4.4's formant shift corrects this per note).

### 5.5 Long tables: the bandwidth-of-harmonics method

Paul Nasca's PADsynth algorithm, implemented in ZynAddSubFX (`zynaddsubfx/zynaddsubfx`, GPL-2.0-or-later,
`src/Params/PADnoteParameters.cpp`), builds one long table (`2^16` to `2^18` samples) whose spectrum gives each
harmonic a bandwidth instead of a single frequency:

```
for each harmonic h with amplitude A[h]:
    bw_hz   = (2^(bw_cents / 1200) - 1) * f_base * h^scale        // scale ~ 1: higher harmonics wider
    for each bin k of the long table:
        x   = (k * fs / L - h * f_base) / bw_hz
        S[k] += A[h] * exp(-x^2) / bw_hz                         // a Gaussian profile per harmonic
phases[k] = uniform random in [0, 2 pi)                           // seeded
table      = inverse FFT of S[k] e^(i phases[k]), scaled to a peak of one
```

Read as a looping table at `f / f_base` times its rate, it sounds like an ensemble: each harmonic is a narrow band of
noise, the result of many slightly detuned voices, with no beating pattern that repeats faster than the loop (5.9 s
for `2^18` samples at 44.1 kHz). It is the precomputed answer to a dense stack: one read a sample gives the sound of
dozens of voices (section 13). Its costs are memory (1 MB a table at single precision, and a table per octave or two
to keep formants and band-limits right) and fixed character: the bandwidth, the harmonic weights and the beating are
frozen into the table and change only by rebuilding it, off the callback. Starting each note at a seeded random point
in the loop keeps notes from sounding alike.

## 6. Integrated Wavetables

**Principle.** Store the `K`-th running integral of the cycle; read it at the output times; take the `K`-th difference
of the reads and scale. The read-and-difference is equivalent to reading the original table through a box filter (for
`K = 1`) or a B-spline of order `K` (for higher `K`) whose width is exactly one output sample in output time, whatever
the pitch: a time-varying anti-aliasing filter that widens in table time as the pitch rises, with nulls at multiples
of `fs`. One table serves every pitch with no mip levels.

Geiger introduced the first-order form ("Table lookup oscillators using generic integrated wavetables", DAFx 2006),
after the differentiated polynomial waveforms (`QUALITY_RESEARCH.md`, 1.3); Franck and Välimäki extended it to higher
orders ("Higher-order integrated wavetable synthesis", DAFx 2012; "Higher-order integrated wavetable and sampling
synthesis", JAES 2013).

**Algorithm.**

1. Remove the cycle's average: `s0[n] = s[n] - mean(s)`. Integration has infinite gain at zero frequency, so any
   offset ramps without end.
2. For `k = 1 .. K`: `s_k[n] = sum_{l <= n} s_(k-1)[l] + c_k`, choosing `c_k = -mean` of the running sum so that each
   integral is itself free of offset and therefore periodic with the cycle's period (Franck and Välimäki, equations 8
   and 9).
3. At run time read `s_K` at each output time with an interpolator of adequate order, then apply a `K`-th order
   difference and scale by `step^-K` (the read increment in table samples to the power `-K`):

```
K = 1:  y[n] = (S1(x_n) - S1(x_(n-1))) / step
K = 2:  y[n] = (S2(x_n) - 2 S2(x_(n-1)) + S2(x_(n-2))) / step^2
```

**Findings** (the 2012 paper, a 1245 Hz saw from a 1024-sample table at 44.1 kHz):

- `K = 1` with nearest-sample reading (Geiger's scheme) reduces aliasing markedly against a plain table read.
- `K = 2` with nearest-sample reading is worse than `K = 1`: the images of the read itself dominate. Raising `K`
  pays only with a matching interpolator: `K = 2` with linear, `K = 3` with linear, `K = 4` needs cubic Lagrange
  (order 3), and orders 5 and 6 with cubic Lagrange improve further. The rate of decay of the dominant alias grows
  with `K`.
- A cascade of first differences (the maximally flat differentiator, `h[k] = (-1)^k C(K, k)`) dulls the top octave,
  more with each order; minimax differentiators (designed for the band up to `0.9 pi`) keep the harmonics' amplitudes
  but pass more aliasing.
- **Precision**: the differentiator's large high-frequency gain amplifies quantisation of the integrated table. A
  third-order table quantised to 24 bits already shows extra high-frequency noise, and a fifth-order one at 24 bits is
  worse than a fourth-order one. In practice the integrated tables and the differencing are kept in double precision,
  which single-precision tables (a 24-bit mantissa) cannot replace above `K = 2`.

**Cost and hazards.** A read of the integrated table (two or four loads), `K + 1` taps of difference, a multiply by
`step^-K`, and `K` samples of history: about 10 to 25 operations, constant with pitch, and `K / 2` samples of delay.
At very low pitch `step` is small and the difference subtracts nearly equal large numbers: the error grows as
`step^-K`, so below a few hertz the oscillator falls back to a direct read. A pitch that changes within the
difference's span breaks the equality with a box filter (the scaling assumes one `step` for all `K` samples); smooth
pitch is fine, a pitch jump (hard sync, a reset) leaves a short spike unless the history is reset with the phase.
Integrated tables suit one-table-for-all-pitches oscillators and long sample loops (sampling synthesis), where mip
levels would multiply memory.

## 7. Real-Time Cost, Memory and Building Off the Callback

### 7.1 Cost per read

| Read | Loads | Operations | Notes |
| --- | --- | --- | --- |
| Linear, one level | 2 | ~7 with phase update | the default for 2048-sample tables |
| Linear, two levels crossfaded | 4 | ~11 | smooth brightness across octaves |
| Linear, two frames | 4 | ~11 | crossfade morph |
| Linear, two frames by two levels | 8 | ~19 | both |
| Cubic (Catmull-Rom or Lagrange), one level | 4 | ~14 | low bass notes, short tables |
| Integrated table, `K = 3`, linear read | 2 | ~15 | no levels; double precision |
| Per-block spectrum (section 2.4) | 2 to 4 | ~7 to 14, plus ~170 a buffer for the FFT | exact band-limits, spectral warps free |
| PolyBLEP saw (for comparison) | 0 | ~6, ~15 near a jump | saw, square and pulse only |

A table read is cheap in arithmetic but costs a dependent load whose address depends on the phase. Reads of the same
cycle by many voices (unison) share cache lines and are fast; reads of many different frames and levels at once
contend for the cache. On processors where vector gathers are slow, an oscillator vectorised across unison voices
(four or eight phases in one register) spends most of its time on the gathers, while a polyBLEP saw vectorises fully
with a branchless correction (compute it for every lane and select by the phase test). For plain saws and pulses the
computed wave is therefore often faster than the table; tables pay for themselves when the waveform is arbitrary.

### 7.2 Memory

| Holding | Size at single precision |
| --- | --- |
| One cycle of 2048 | 8 KB |
| One cycle with halved levels (`~2N`) | 16 KB |
| One cycle with 12 full-length levels | 96 KB |
| 256 frames, halved levels | 4 MB |
| 256 frames, 12 full-length levels | 24 MB |
| One long ensemble table of `2^18` | 1 MB per level |

A table shared by every voice of an instrument (behind one reference-counted pointer) is built once per instrument,
not per voice or note.

### 7.3 Building tables off the callback

Every FFT, allocation and table build belongs to another thread: when an instrument is compiled, when a setting that
shapes a table changes, or when a recording is analysed. The audio thread receives a finished table and never frees
one:

1. A worker builds the new tables (all levels, all frames) into fresh memory.
2. It sends a pointer to the finished set through a lock-free single-producer, single-consumer queue, or swaps it in
   as part of a whole new patch.
3. The callback takes the new pointer at a block boundary. Voices already sounding either keep the old set until
   their note ends (no change mid-note) or crossfade to the new one over a block or two (a setting that sweeps).
4. The old set is not dropped in the callback: dropping the last reference to a vector frees memory, which takes the
   allocator's lock. The callback sends the old pointer back through a return queue, and a non-audio thread drops it.

A setting that sweeps continuously (a formant shift, a spectral warp's amount) cannot wait for rebuilds; either the
oscillator builds per block in the callback with preplanned FFTs and preallocated buffers (section 2.4), or the
setting is quantised to a set of prebuilt tables crossfaded by the setting's value.

## 8. Tables Across the Instrument

### 8.1 LFO and envelope shapes

An LFO table holds a drawn or computed shape of 256 to 2048 points, read by phase. At LFO rates (under about 20 Hz)
nothing aliases and linear interpolation is ample; the table needs no levels and keeps its offset (a unipolar shape).
The hazards are the shape's own jumps (a square or saw, a drawn step), which click when they move an amplitude or a
cutoff: a one-pole slew of 1 to 5 ms on the output, or a smoothing of the drawing, removes the click while keeping the
shape (`QUALITY_RESEARCH.md`, 10). An LFO run at audio rate is an oscillator and then needs band-limiting like one:
levels chosen by its rate, or BLEP on its jumps. Envelope segments drawn as power curves (section 5.3) are the same
table idea read once instead of looping.

### 8.2 Drum layers

- **Pitched bodies.** A kick's or tom's body is a sine or a near-sine (a second harmonic of a few percent adds the
  knock of an overdriven bridged-T circuit). Read from a table and swept from 1 to 2 kHz down to 40 to 60 Hz in tens
  of milliseconds, it crosses several levels per hit; the level is chosen per block from the highest pitch in the
  block, which for a falling sweep is the block's start, so nothing aliases.
- **Timbre by scanning.** A frame position moved by the drum's envelope (bright frames at the strike, dull ones as it
  decays) gives a darkening decay without a filter, cheaper than a resonant filter per hit.
- **One-shot transients.** A click or a noise burst stored as a short non-looping table, read once. A one-shot read
  above its recorded pitch needs its own band-limited copies (Surge XT filters sample-type tables across frame
  boundaries in `MipMapWT` for exactly this) or an integrated table (section 6).
- **Noise tables.** A long looped table of noise (`2^15` to `2^17` samples), read at a variable speed, gives pitched
  or coloured noise; read faster than its own rate it needs levels like any table, or it aliases into a grainy hiss.
  A seeded generator remains the plain choice for white noise.
- **Metal.** Cymbals and bells are inharmonic and cannot live in one cycle; modal resonators, ring-modulated squares
  or long tables (section 5.5) serve instead.

### 8.3 Chip voices

A chip's wave memory, such as 32 steps of four bits, is a table whose zero-order-hold steps are part of the sound. The
faithful rendering keeps the steps' harmonics as far as each note's Nyquist allows, and no further: the FFT of the
stepped cycle at the full table length, then levels as usual. The chip's uneven converter (an R-2R ladder whose
resistors are mismatched, as in the 1982 home computer's sound chip) is modelled when the stepped cycle is computed,
before band-limiting, so its unevenness is kept and its aliasing is not (`ENGINES_RESEARCH.md`, 10). A program that
rewrites the wave memory mid-note (a common trick on the 1989 handheld console) needs one table per rewritten shape,
prebuilt, and a switch at the rewrite's moment; the switch itself is a step in the waveform the chip also made, and
is kept. A chip whose oscillator really aliased, such as a fixed-rate sample playback, is modelled by its own rate and
the aliasing called out as that instrument's character.

### 8.4 Organ voices

- **Transistor combo organs** derive every octave from a top-octave generator by dividers, so their footages are
  exact octaves of one another in fixed phase. A sum of footages at one key is therefore exactly one periodic cycle,
  and one table per registration (rebuilt when a tab changes) reproduces it: a square or pulse per footage, summed,
  band-limited (`ENGINES_RESEARCH.md`, 5.2).
- **Tonewheel organs** are subtler. The drawbars sit at 16', 5 1/3', 8', 4', 2 2/3', 2', 1 3/5', 1 1/3' and 1', which
  are harmonics 1, 3, 2, 4, 6, 8, 10, 12 and 16 of the 16' pitch; a table built at the 16' pitch holds them all. But a
  tonewheel organ takes each drawbar's tone from the nearest equal-tempered wheel, so the 2 2/3' is a tempered
  twelfth (`2^(19/12) = 2.9966`, not 3) and the 1 3/5' a tempered seventeenth (`2^(28/12) = 5.0397`, not 5). Against
  the exact harmonics a table holds, these beat: at A 440 the 2 2/3' drawbar beats against an exact third harmonic
  about 1.5 times a second. The slow shimmer this gives a held chord is part of the organ's sound, and a single-cycle
  table removes it; nine free sines per note, or a table for the octave-related drawbars (16', 8', 4', 2', 1') plus
  separate tempered sines for the others, keep it. The wheels' fixed phases (they turn on one shaft) are otherwise
  well represented by a table's fixed phases.

### 8.5 Waveshaping by table

A transfer curve `y = g(x)` stored as a table over `[-1, 1]` (1024 to 4096 points) and read by the signal's value:

- **Chebyshev waveshaping.** With `T_k(cos theta) = cos(k theta)`, a shaper `g(x) = sum a_k T_k(x)` driven by a
  full-scale cosine produces exactly harmonic `k` at level `a_k`: a harmonic spectrum chosen at will from one sine (Le
  Brun, "Digital waveshaping synthesis", JAES 1979; Arfib, "Digital synthesis of complex spectra by means of
  multiplication of nonlinear distorted sine waves", JAES 1979). Driving it below full scale (the "distortion index")
  darkens the result smoothly, a brightness control with no filter. Since an order-`K` polynomial on a sine of `f0`
  gives harmonics only up to `K f0`, the shaper is alias-free when `K f0 < fs/2`: per note, a polynomial truncated to
  `K = floor(fs / (2 f0))` is a "level" of the shaper.
- **Arbitrary curves.** Saturators and folders drawn as tables alias like any nonlinearity. Antiderivative
  anti-aliasing works by table: store `G(x)`, the antiderivative of `g`, beside `g`, and output
  `(G(x_n) - G(x_(n-1))) / (x_n - x_(n-1))`, falling back to `g((x_n + x_(n-1))/2)` when the difference is tiny
  (`QUALITY_RESEARCH.md`, 5). The table of `G` needs double precision or a careful offset, since `G` grows like the
  integral.
- **Interpolation.** A shaper table read linearly is a piecewise-linear curve, whose corners add a little harmonic
  content of their own; cubic reading or a fine table (4096 points) keeps a smooth curve smooth.

## 9. The Stacked Saw

### 9.1 What a musician hears

Several saws at nearly the same pitch, a few cents apart, summed: the stacked saw, and, with more voices and layers,
the dense stacked saw. It is the trance pad, the anthem lead, the wall of sound under a breakdown. What
the ear hears depends on how far apart the saws are. Two tones under about 15 to 20 Hz apart are heard as one pitch
beating at their difference frequency; wider, the beating becomes roughness; wider still, past a critical bandwidth,
two separate tones. A saw's harmonic `h` of two voices detuned by `c` cents is apart by `h f0 (2^(c/1200) - 1)` Hz, so
in one stack the low harmonics beat slowly while the high ones are rough: the fundamental swells and fades gently, the
upper spectrum shimmers. With seven or more voices at unrelated offsets, the beating patterns overlap into a
continuous motion with no clear period, the ensemble effect of a string section, which is why this oscillator was
described from the start as suited to string-type sounds.

### 9.2 Szabo's measurements

Adam Szabo's bachelor's thesis (a study of how to emulate the stacked-saw oscillator of a late-1990s virtual-analog
synthesizer, KTH Royal Institute of Technology, 2010) recorded the oscillator at 44.1 kHz and measured, with a
131072-point FFT and an oscilloscope, four aspects: detune, mix, shape and phase.

**Seven saws.** One centre saw at the note, not moved by the detune control, and six side saws, three below and three
above. At full detune on C5 (523.357 Hz) the side saws stood at:

| Saw | Frequency | Ratio to centre | Offset | Cents |
| --- | --- | --- | --- | --- |
| 1 | 465.776 Hz | 0.88998 | -0.11002313 | -201.8 |
| 2 | 490.446 Hz | 0.93712 | -0.06288439 | -112.4 |
| 3 | 513.139 Hz | 0.98048 | -0.01952356 | -34.1 |
| 4 (centre) | 523.357 Hz | 1 | 0 | 0 |
| 5 | 533.778 Hz | 1.01991 | +0.01991221 | +34.1 |
| 6 | 555.892 Hz | 1.06217 | +0.06216538 | +104.4 |
| 7 | 579.593 Hz | 1.10745 | +0.10745242 | +176.7 |

Each side saw's frequency is `f0 * (1 + offset_i * D(x))`, with `x` the detune control from 0 to 1 and `D` its curve.
Two features of the offsets matter. They are not evenly spaced: the inner, middle and outer pairs stand in the ratio
about 1 : 3.2 : 5.6, not 1 : 2 : 3, so the inner pair hugs the centre while the outer pair is far out. And they are
nearly symmetric as ratios, `1 - 0.110` and `1 + 0.107`, which in cents is 202 down and 177 up, since a symmetric
ratio offset is asymmetric in cents; the small difference between 0.110 and 0.107 is the instrument's own. Because
each offset is a fixed ratio of `f0`, the detune is the same in cents at every pitch, and the beating rates scale with
the note: low notes beat slowly, high notes fast.

**The detune curve.** Sampled at every eighth of the control's 128 steps, the curve `D(x)` (as a share of full detune)
was:

| Control | 0 | 7 | 15 | 23 | 31 | 39 | 47 | 55 | 63 | 71 | 79 | 87 | 95 | 103 | 111 | 119 | 127 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `D` | 0 | .0097 | .0220 | .0340 | .0468 | .0591 | .0715 | .0839 | .0967 | .1215 | .1471 | .1935 | .2434 | .2934 | .3433 | .3928 | 1 |

That is, a gentle straight line to the middle of the control (about 0.0015 a step), a steeper one above it (about
0.0053 a step), and a leap over the last eight steps from 0.39 to 1. The thesis fitted an eleventh-order polynomial
through the points:

```
D(x) = 10028.7312891634 x^11 - 50818.8652045924 x^10 + 111363.4808729368 x^9 - 138150.6761080548 x^8
     + 106649.6679158292 x^7 - 53046.9642751875 x^6 + 17019.9518580080 x^5 - 3425.0836591318 x^4
     + 404.2703938388 x^3 - 24.1878824391 x^2 + 0.6717417634 x + 0.0030115596
```

The fit's constant term leaves a residual detune of about 0.6 cents on the outer pair at `x = 0`, an artefact of
fitting, not of the instrument. A piecewise-linear table through the measured points is as accurate and cheaper; it
also avoids the polynomial's wiggles between points, which an eleventh-order fit has. Each pair's offset in cents
through the curve (the mean of its two sides where they differ):

| Detune control `x` | 0.10 | 0.25 | 0.50 | 0.75 | 0.90 | 1.00 |
| --- | --- | --- | --- | --- | --- | --- |
| Inner pair | +-0.6 | +-1.6 | +-3.4 | +-8.3 | +-12.1 | +-34.1 |
| Middle pair | +-1.8 | +-5.0 | +-10.6 | +-26.2 | +-38.3 | -112, +104 |
| Outer pair | +-3.1 | +-8.8 | +-18.5 | +-45.6 | +-66.7 | -202, +177 |

The musically useful range is the lower two thirds of the control, where the outer saws stay within about 20 cents of
the note; the top
eighth leaps to an interval wider than a whole tone, a special effect.

**The mix law.** One mix control raises the side saws and, contrary to the instrument's manual, lowers the centre:

```
centre(m) = -0.55366 m + 0.99785
side(m)   = -0.73764 m^2 + 1.2841 m + 0.044372          // each of the six
```

At `m = 0.75` (control 95) the centre and side saws are equal (0.583 and 0.593); at full mix the side saws (0.591)
exceed the centre (0.444). If the seven saws are uncorrelated (detuned, random phases), their summed power, `centre^2
+ 6 side^2`, rises from 1.00 at `m = 0` to 1.56 at `m = 0.75` (+3.9 dB) and 1.51 at full mix (+3.6 dB), so the law
holds loudness within 4 dB while the texture thickens sevenfold. Equal-level side saws are fine; the thesis found them
equal.

**Shape and the high-pass.** The saws are plain digital saws that alias, not band-limited ones: their folded harmonics
add a bright, airy noise floor to the sound. Below the fundamental, where folded components would sound unnatural, the
spectrum is clean, and the fundamentals of the seven saws grow progressively louder from the lowest saw to the
highest: the evidence of a high-pass filter that tracks the pitch, set at the fundamental, after the mix. The filter
also bends the single saw's ramp into the curved shape seen on an oscilloscope. Its order was not measured. A one-pole
high-pass at `f0` passes the fundamental at -3.0 dB, the second harmonic at -1.0 dB and the third at -0.5 dB; a
two-pole Butterworth at `f0` gives -3.0, -0.3 and -0.05 dB and cuts the sub-fundamental region twice as steeply (-12.3
dB at half the fundamental against -7.0 dB).

**Phase.** Every note begins with a random phase for each saw; the saws run freely through the note. Played
repeatedly with a small detune, the same note looks different each time. Resetting every saw to the same phase instead
gives a loud first cycle (seven saws in step) and a flanging sweep as they drift apart, the same on every note; fixed
but unequal phases remove the loud cycle but still repeat. The thesis found phase modulated through the note (by an
LFO) worse than a fixed random start.

**What the thesis concluded.** The four marks of the sound are the random phases, the detune curve, the mix law that
lowers the centre, and the aliasing kept above the fundamental with the noise below it removed.

### 9.3 Shore's listening study

Alex Shore's research project (an analysis of the same oscillator and its relation to pads in trance music, BA
project report, University of Huddersfield, 2013) built an emulation from Szabo's figures and compared it with the
instrument in listening tests, varying one aspect at a time: the detune doubled, halved or made linear; three, five or
nine saws in place of seven; no filter, a 6 dB and a 12 dB an octave high-pass. A further test with eleven experienced
listeners compared the curved detune with a linear one at five settings. The detune curve made the largest difference:
with a linear control the low and middle settings were already rough and wide, while the curve allowed the very small,
gradual spreads that give smooth pads; the conclusion was that the detune curve is the most important element of the
sound; the other changes made smaller differences. Random phase was left out of the tests, since it changes only how
each note begins, which matters little to sustained chords.

### 9.4 A later reconstruction

A reconstruction of the oscillator's arithmetic, published in 2026 on an independent synthesizer builder's research
blog from the instrument's observed behaviour, describes: 24-bit phase accumulators wrapping by overflow, with the a
worked example at 88.2 kHz, twice a common output rate; each side saw's increment as the centre's plus a detune
proportional to the pitch (so detune constant in cents, as Szabo found), formed from the pitch times the detune
setting and a fixed coefficient per saw, +128, +408 and +704 on one side and -128, -412 and -720 on the other (ratios
1 : 3.2 : 5.5, matching Szabo's 1 : 3.2 : 5.6, and slightly asymmetric as he measured); the detune control as a
piecewise-linear table of segments steepening towards the top (matching the measured points); the mix as a linear
control of the side saws with the centre at a fixed level, the measured fall of the centre then coming from a
normalisation after the oscillator; smoothing of mix and detune over a few steps; and a high-pass at the output. It
supports reading Szabo's curves as two or three straight segments and his mix law as the product of a linear control
and a later gain.

### 9.5 Why it sounds as it does

- **The detune curve's fine low end** allows a stack spread over a few cents, where every harmonic beats slowly: the
  smooth, lush pad. The same controls on a linear scale jump straight into roughness.
- **Uneven spacing** (1 : 3.2 : 5.6) means the pairs' beating rates are unrelated, so the stack never realigns on a
  short period (section 12.2): the motion is continuous rather than pulsing.
- **The mix law** keeps loudness nearly constant while letting the side saws dominate, so the centre pitch is masked
  by the moving voices at high mix: the sound stops being a saw with chorus and becomes a mass.
- **Free-running random phases** make every note's attack different, and with small detune give every note a slightly
  different static tone colour (section 12.3), the organic variation a performer hears as life.
- **Aliasing** adds an inharmonic, bright haze in the upper spectrum that sounds like air or breath, and **the
  high-pass** removes the part of it that would sound broken (below the fundamental) and thins the fundamental itself
  by about 3 dB, which keeps a chord of stacks from booming.

### 9.6 Building it

Per voice, at note-on and per sample:

```
note-on:
    seed      = mix(instrument_seed, note_number, note_count)          // every render the same
    phase[i]  = uniform(seed, i) in [0, 1)  for i in 0..7              // free-running from a random start
    D         = detune_curve(x)                                         // piecewise-linear through the measured points
    inc[i]    = f0 / fs * (1 + offset[i] * D)                           // offsets as in 9.2
    g_centre  = -0.55366 m + 0.99785
    g_side    = -0.73764 m^2 + 1.2841 m + 0.044372
    hp        = high-pass coefficients at f0 (one-pole or two-pole), worked out per block
per sample:
    sum = g_centre * saw(phase[3]) + g_side * sum_{i != 3} saw(phase[i])
    advance every phase by its inc
    out = hp(sum)
```

The choice of `saw` decides the character. Naive saws reproduce the measured aliasing, which changes with pitch and
becomes harsh and clearly inharmonic above about 1 kHz at 44.1 kHz; it is the instrument's own sound and is called out
as such where it is kept. PolyBLEP saws leave a residue 20 to 30 dB down in the upper octaves (`QUALITY_RESEARCH.md`,
1.2), a mild haze; fully band-limited saws (tables or minBLEP) are clean, and a little noise or a soft saturation
after the sum restores some air if wanted. Running naive saws at twice the output rate and decimating, as the
reconstruction's worked example at 88.2 kHz suggests, keeps a milder, more musical aliasing. Pitch modulation
(vibrato, glide) updates the seven increments by multiplying one ratio, never seven exponentials: each `inc[i]` is
`f0_inc * ratio[i]` with the ratios fixed until the detune moves. The high-pass coefficients follow `f0` per block;
for a one-pole, `a = exp(-2 pi f0 / fs)`, `y = a (y + x - x_prev)`.

## 10. Denser Stacks

### 10.1 More voices

Later instruments stack 9, 16 or more saws (a 2000s virtual-analog synthesizer's nine-saw oscillator; Vital's 16
unison voices, `kMaxUnison = 16`; Surge XT's up to 16 per oscillator; ZynAddSubFX's up to 64 for some voice types).
More voices make the texture denser and the beating less distinct, approaching the noise-band sound of section 5.5,
and cost proportionally more (section 13). Past about 9 voices the gain is density, not width, and the extra voices
are better spent on layers.

### 10.2 Octave, sub and chord layers

Vital's stack styles multiply each unison pair's frequency (`kStackMultipliers`): the centre pair an octave or two
down ("center drop octave"), alternate pairs an octave up ("octave"), stacks of 1, 1.5 (a tempered fifth, 1.4983) and
2 ("power chord"), a major or minor triad with the octave, the harmonic series 1 to 8, or the odd series 1 to 15. An
undetuned sub-octave saw or square under the stack gives weight without beating in the bass; an octave-up layer
brightens without more roughness. Chord stacks turn one note into a chord of detuned stacks, the "one-finger chord"
lead.

### 10.3 Stereo spread and mono compatibility

Each unison voice is panned: Surge's `UnisonSetup::panLaw` (`sst-basic-blocks`, GPL-3.0-or-later,
`include/sst/basic-blocks/dsp/OscillatorDriftUnisonCharacter.h`) places voice `v` at `d = |v - mid| / mid`, with its
sign alternating, and sets `L = 1 - d`, `R = 1 + d`, all times `1 / sqrt(N)`. Vital sends the sharp and flat voice of
each pair to opposite sides and blends between the stereo stack and its centre with an equal-power fade of the
"stereo spread" setting (`blend_stereo_multiply_`, `futils::equalPowerFade`).

Pan by gain alone is mono-compatible: the mono sum contains every voice, at levels set by the pan law. A linear law
(`L + R` constant) keeps the mono balance of centre and side voices exactly; an equal-power law (`cos`, `sin`) keeps
the stereo loudness but in mono raises the centre voice 3 dB over the hard-panned ones. Stereo made by delaying or
phase-inverting one side comb-filters or cancels in mono and is avoided for stacks. Detuned voices hard-panned make
the bass beat differently in each ear, which on loudspeakers smears the low end; keeping the stack's lowest octave
near the centre (the centre voice or a sub undetuned and central, or the stack high-passed and a mono bass under it)
keeps the bass solid.

### 10.4 Per-voice drift and vibrato

- **Drift**: a slow random walk per voice. Surge's `DriftLFO` (same file) filters white noise with a one-pole,
  `y <- y (1 - a) + a u`, `a = 0.00001`, `u` uniform in `[-1, 1]`, and scales by `1/sqrt(a) = 316.23`, giving a
  wandering value of roughly unit size with a corner near `a fs / (2 pi)`, 0.08 Hz at 48 kHz, multiplied by a drift
  amount in cents. It uses the C library's unseeded generator; a seeded generator per voice keeps every render the
  same. A few cents of drift per voice makes a stack's motion irregular even with even spacing.
- **Vibrato per voice**: ZynAddSubFX (`src/Synth/ADnote.cpp`, `setupVoiceUnison`, `compute_unison_freq_rap`) gives
  every unison voice its own slow triangle, `pos` bouncing between -1 and 1 at a period of `0.25 * 2^((1 - speed) 4)`
  seconds (0.25 to 4 s), each voice's period randomly 0.5 to 2 times that and its direction random, the triangle
  softened to `1.5 (pos - pos^3 / 3)`; the voices' fixed offsets shrink by the vibrato's share, `1 + (offset - 1)(1 -
  vib)`, so the total spread stays put while part of it moves. The result is an ensemble whose voices each wander,
  closer to a real section than fixed detune.

### 10.5 Phase inversion

ZynAddSubFX can invert the polarity of some unison voices (`Unison_invert_phase`: none, random, or every `k`-th). An
inverted voice sounds the same alone, but in a stack it changes which harmonics cancel when voices pass through phase
alignment; at small detune it thins the bass, since the fundamentals partly cancel. It is a colour, and its mono sum
is a stronger version of the stereo sound's cancellation.

### 10.6 Chorus on top

A chorus (`EFFECTS_RESEARCH.md`, chorus and ensemble) adds pitch-modulated delayed copies of the whole stack: each
copy multiplies the apparent voice count, and its delay modulation gives every harmonic a slow vibrato proportional to
its frequency. Two- or three-voice ensemble choruses with unrelated LFO rates over a seven-saw stack are the standard
trance-pad sound; the chorus's stereo width also comes from decorrelation rather than panning, so it is less
mono-compatible than pan spread.

### 10.7 Spread through a table

With a wavetable as the stack's waveform, each unison voice may read a different frame (Vital's frame spread,
`kUnisonFrameSpread`: voice `v` reads `frame + v / (pairs - 1) * spread`) or a different spectral warp amount: the
voices then differ in timbre as well as pitch, a richer, less saw-like ensemble. It costs a buffer per distinct voice
in Vital's design, or extra reads in a direct design.

## 11. Unison in Open Synthesizers

**Vital** (`mtytel/vital`, GPL-3.0; `src/synthesis/producers/synth_oscillator.cpp`,
`src/common/synth_parameters.cpp`):

- Up to 16 voices in sharp and flat pairs. Voice pair `i` stands at `t = (2i + b) / (N - 1)`, `b = 1` for an even
  count (so no voice sits at the centre), and its offset is
  `cents = range * detune * (e^(p t) - 1) / (e^p - 1)` (`setPhaseIncMults`, `futils::powerScale`), the sharp voice up
  and the flat voice down by the same ratio. Defaults: detune 4.47 (stored on a square-law scale), range 2,
  so the outermost voices sit about 9 cents from the note; the controls reach 480 cents. The power `p` (default 1.5,
  from -5 to 5) pulls the inner voices towards the centre: at `p = 1.5` a voice a third of the way out stands at 0.19
  of the full spread instead of 0.33.
- Blend: the centre voice's level is `lerp(1, 0.4, blend)` and the detuned voices' `lerp(0.6, 0, (1 - blend)^2)`
  (`kCenterLowAmplitude = 0.4`, `kDetunedHighAmplitude = 0.6`, `setAmplitude`), both scaled by one over the square
  root of their summed powers, so loudness holds as blend and voice count change. Default blend 0.8.
- Phase randomisation: at each note, every voice's phase is a random fraction of a cycle times the "phase
  randomization" amount (default 1, `reset`); at 0 every voice starts together, for a hard, flanging attack.
- Stack styles (section 10.2), frame spread and spectral unison (section 10.7), stereo spread (section 10.3).
- Cost: the per-block spectrum is shared across the stack unless spread per voice, so the per-sample work is a
  four-point read per voice per sample, vectorised across voices.

**Surge XT** (`surge-synthesizer/surge`, GPL-3.0-or-later; `src/common/dsp/oscillators/ClassicOscillator.cpp`,
`WavetableOscillator.cpp`, `OscillatorCommonFunctions.h`; `sst-basic-blocks` as above):

- Up to 16 voices for its classic and wavetable oscillators. `UnisonSetup` spreads detune linearly:
  `detune(v) = 2 v / (N - 1) - 1`, from -1 to 1, times the detune amount; attenuation `1 / sqrt(N)`.
- Pan law as section 10.3; `DriftLFO` drift per voice; a "character" filter (`CharacterFilter`) after the
  oscillator, a gentle one-pole tilt around 5 kHz, warm (a low-pass) or bright (a high boost), chosen per patch.
- The classic oscillator builds its waves from band-limited impulses (windowed-sinc steps placed at each corner and
  jump), and the wavetable oscillator places a band-limited step for every change between table samples
  (`convolute`), both at twice the output rate; random start phases per unison voice.

**ZynAddSubFX** (`zynaddsubfx/zynaddsubfx`, GPL-2.0-or-later; `src/Synth/ADnote.cpp`):

- Up to 64 voices; the spread in cents, `unison_spread`; offsets evenly spaced from -1 to 1 and then jittered by up to
  one step at random, `step + uniform(-1, 1) / (N - 1)`, and renormalised to span -1 to 1 again: an uneven, per-note
  random spacing.
- Per-voice vibrato and phase inversion (sections 10.4 and 10.5); stereo spread by voice.
- Its PADsynth (section 5.5) is the long-table alternative to unison.

**Dexed** (`asb2m10/dexed`, GPL-3.0, with Google's `msfa` engine under Apache-2.0) models a six-operator FM
synthesizer of 1983. It has no unison stack: thickness comes from the operators' fine detune and from layering, and
its sine is the interleaved value-and-difference table of section 2.5.

## 12. Detune Distributions and Phase

### 12.1 Distributions

For `N` voices with normalised positions `t` from -1 to 1:

| Distribution | Offsets | Character |
| --- | --- | --- |
| Linear | `t_v = 2v/(N - 1) - 1` (Surge) | even; strongly periodic beating |
| Power | `t' = (e^(p t) - 1)/(e^p - 1)` on each side (Vital, `p = 1.5`) | inner voices close, a smooth core with wide edges |
| Measured stacked saw | fixed shape `+-0.0195, +-0.0629, +-0.110` (scaled by the curve) | 1 : 3.2 : 5.6, unrelated beats |
| Jittered | linear plus `uniform(-1, 1)/(N - 1)`, renormalised (ZynAddSubFX) | uneven, different every note |
| Drifting | any of the above plus a slow random walk per voice | uneven and moving |

The detune amount itself wants a curve with fine resolution at small values, as the measured stacked saw's control
shows: a square-law or two-segment control serves well, since musical pads live in the first 10 to 20 cents.

### 12.2 Periodic realignment

With linear spacing every voice is `k Delta` from the centre, so all pairwise beat frequencies are multiples of
`Delta` (in hertz, for harmonic `h`, of `h Delta`), and the whole stack returns to its starting alignment every
`1 / Delta` seconds: a regular pulsing or "whoosh" at the spacing frequency. At A 440 with 5 cents between neighbours,
`Delta = 440 (2^(5/1200) - 1) = 1.27 Hz`, and the stack pulses about every 0.8 s. Uneven spacing (the measured shape,
a power curve, jitter, drift) makes the beat frequencies incommensurate, so the stack never quite realigns and the
motion is continuous, which is much of why the measured oscillator sounds smooth.

### 12.3 Phase at note-on: random, reset, free-running

- **Random at note-on** (the measured oscillator, Vital's default): each voice starts at a random phase. With
  detune, the attack differs every note. At very small detune the stack is nearly a fixed sum, and the sum of `N` saws
  at random phases is itself a periodic wave whose harmonic `h` has amplitude `|sum_v e^(i h theta_v)| / h`, a random
  number for each harmonic: each note gets a different, nearly static comb of tone colour and a different loudness
  (its expected power is `N` times one saw's, but with a wide spread). This note-to-note variation is part of the
  sound, and the reason a stack at zero detune sounds unlike a single saw.
- **Reset to equal phases**: every voice starts in step, a peak `N` times one saw's on the first cycle, then a
  flanging sweep as the voices drift apart, the same on every note: punchy, used for plucks and basses.
- **Free-running**: phases carry on from the last note on the same voice, as analog oscillators do. Statistically
  like random at note-on, but repeatable only if the whole history is.

The randomness is seeded from the instrument and the note (its number and its count since the instrument started),
so that every render of a set is the same; a generator such as SplitMix64 or xorshift, seeded per note, gives `N`
phases in a few operations at note-on and nothing per sample.

## 13. The Cost of a Stack, and Its Loudness

### 13.1 Per voice per sample for `N` saws

| Method | Per saw | `N = 7` | `N = 16` | Memory | Notes |
| --- | --- | --- | --- | --- | --- |
| Naive saw | ~3 | ~25 | ~50 | none | aliasing kept on purpose only |
| Two-point polyBLEP | ~6 (15 near a jump) | ~55 | ~120 | none | vectorises across voices; residue -20 to -30 dB |
| Mip-mapped table, linear | ~7 + 2 loads | ~55 | ~120 | 16 KB a waveform | clean; one level for the whole stack (chosen for the highest voice) |
| Mip-mapped table, crossfaded levels | ~11 + 4 loads | ~85 | ~190 | 16 KB | smooth brightness |
| Per-block spectrum, shared (Vital) | ~14 + 4 loads, plus ~170 a block-shared buffer | ~270 | ~400 | 2 buffers a voice | exact limits, warps free |
| One long ensemble table (section 5.5) | ~10 for the whole stack | ~10 | ~10 | 1 MB a level | fixed beating; rebuild to change |
| A few long tables at offsets | ~10 a table | ~30 for three | ~30 | 1 MB each | the sound of dozens of voices |

Add the mix (one multiply-add per voice), the high-pass (4 to 10) and the pan (2 per voice in stereo). Choosing the
table level once for the stack from its highest voice (the centre times `1 + max offset`) costs nothing per voice; the
sharpest voice then sets a limit a little low for the others, a loss of at most a few percent of bandwidth at the
measured detunes.

**Denser stacks from a few tables.** A long ensemble table already holds a band of partials around each harmonic. Two
or three such tables read at seeded different start points and very slightly different rates (a cent apart) overlap
into a denser, less static ensemble; combined with three or five real saws carrying the near detunes (the audible
beating), they give a stack that sounds like twenty or more voices for the cost of about eight. The real saws keep the
motion responsive to the detune control; the tables supply density.

### 13.2 Loudness growth with voice count

Detuned voices are uncorrelated over time, so their powers add: `N` equal voices are `10 log10 N` dB louder than one
(7 voices +8.5 dB, 16 voices +12.0 dB), and a gain of `1 / sqrt(N)` keeps loudness constant as the count changes
(Surge's `attenuation`, Vital's summed-power normalisation). The peaks do not follow the power: at moments of
alignment (a reset, or the random alignments of a long note) the sum can approach `N` times one voice, `20 log10 N` dB
(7 voices +16.9 dB), and at zero detune with reset phases it does. A stack therefore needs headroom after it, or a
soft saturation that is part of the sound, rather than a gain set for the peak. Per-note loudness also varies at small
detune (section 12.3); a slow automatic gain is never applied, since the variation is musical.

## 14. Hazards at a Glance

| Hazard | Cause | Remedy |
| --- | --- | --- |
| Dull notes just above a level boundary | one level an octave built for its top | two or three levels an octave, or crossfaded levels |
| Brightness or level step at a boundary | mip levels scaled each to its own peak | one gain for all of a frame's levels |
| Alias under pitch modulation | level chosen for `f0` alone | choose for the block's highest pitch, FM reach, arpeggio step |
| Images in bass notes | linear reads of a full-band table | cubic reads, longer tables, or oversampled tables |
| Partials vanish mid-morph | crossfading frames out of phase | phase-aligned frames, spectral morphing |
| Zipper on frame sweeps | nearest-frame reads | crossfade frames; ramp the position |
| Alias from phase warps | local read speed-up above one | choose the level for `s_max * f0`; BLEP or BLAMP the jumps and corners |
| Thump on note start | table offset | remove bin 0 (but keep an LFO's offset) |
| Noise from integrated tables | differentiator gain on rounding | double precision; fall back at very low pitch |
| Click on table swap | a new table mid-note | swap at note start or crossfade over a block |
| Callback frees memory | dropping the last reference to an old table | return old tables to another thread to drop |
| Periodic pulsing of a stack | linear detune spacing | uneven spacing, jitter or drift |
| Identical attacks | phases reset | seeded random phases per note |
| Loudness grows with voices | powers add | `1 / sqrt(N)` gain; headroom for peaks |
| Mushy or wobbling bass | detuned voices in the low octave, hard-panned | keep the lowest octave central and undetuned; high-pass the stack |
| Mono cancellation | stereo by delay or inversion | stereo by pan only |
| Tempered-drawbar shimmer lost | exact harmonics in one organ table | tempered drawbars as separate sines |

## 15. References

Papers and theses:

- Szabo, A. A bachelor's thesis on emulating the stacked-saw oscillator of a late-1990s virtual-analog synthesizer.
  KTH Royal Institute of Technology, 2010.
- Shore, A. An analysis of the same oscillator and its relation to pads in trance music. BA project report,
  University of Huddersfield, 2013.
- Franck, A., and Välimäki, V. "Higher-order integrated wavetable synthesis". DAFx, 2012.
- Franck, A., and Välimäki, V. "Higher-order integrated wavetable and sampling synthesis". JAES 61(9), 2013.
- Geiger, G. "Table lookup oscillators using generic integrated wavetables". DAFx, 2006.
- Välimäki, V., and Huovilainen, A. "Antialiasing oscillators in subtractive synthesis". IEEE Signal Processing
  Magazine, 2007.
- Välimäki, V., Nam, J., Smith, J. O., and Abel, J. S. "Alias-suppressed oscillators based on differentiated
  polynomial waveforms". IEEE TASLP, 2010.
- Horner, A., Beauchamp, J., and Haken, L. "Methods for multiple wavetable synthesis of musical instrument tones".
  JAES, 1993.
- Le Brun, M. "Digital waveshaping synthesis". JAES, 1979.
- Arfib, D. "Digital synthesis of complex spectra by means of multiplication of nonlinear distorted sine waves".
  JAES, 1979.
- de Cheveigné, A., and Kawahara, H. "YIN, a fundamental frequency estimator for speech and music". JASA, 2002.
- Nasca, O. P. The PADsynth algorithm, described with its implementation in ZynAddSubFX.

Open code read for this chapter:

| Project | Licence | Files |
| --- | --- | --- |
| Vital (`mtytel/vital`) | GPL-3.0 | `src/synthesis/producers/synth_oscillator.cpp` and `.h`, `src/synthesis/producers/spectral_morph.h`, `src/synthesis/lookups/wavetable.h`, `wave_frame.cpp`, `src/common/wavetable/wave_source.cpp`, `wave_warp_modifier.cpp`, `phase_modifier.cpp`, `file_source.cpp`, `pitch_detector.cpp`, `src/common/synth_parameters.cpp`, `src/synthesis/framework/futils.h` |
| Surge XT (`surge-synthesizer/surge`) | GPL-3.0-or-later | `src/common/dsp/Wavetable.cpp` and `.h`, `src/common/dsp/oscillators/WavetableOscillator.cpp`, `ClassicOscillator.cpp`, `OscillatorCommonFunctions.h`, `src/common/globals.h` |
| sst-basic-blocks (`surge-synthesizer/sst-basic-blocks`) | GPL-3.0-or-later | `include/sst/basic-blocks/dsp/OscillatorDriftUnisonCharacter.h` |
| ZynAddSubFX (`zynaddsubfx/zynaddsubfx`) | GPL-2.0-or-later | `src/Synth/ADnote.cpp`, `src/Params/PADnoteParameters.cpp` |
| Dexed (`asb2m10/dexed`), its `msfa` engine | GPL-3.0; `msfa` Apache-2.0 | `source/msfa/sin.h`, `sin.cc` |
| stmlib and Plaits (`pichenettes/eurorack`) | MIT | `stmlib/dsp/polyblep.h` (for the BLEP corrections cited) |
