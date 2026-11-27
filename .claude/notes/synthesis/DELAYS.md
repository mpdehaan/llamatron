# Delay Lines

How digital delay effects work: the line and its reads, moving delay times, feedback structures, and the
bucket-brigade device and its models. Research from published papers and open-source code only.

## The Line

A delay line is a circular buffer written once a sample and read at one or more places behind the write position.
Each read is a tap; a tap's distance behind the write head is its delay in samples.

- **Wrapping.** Reading `write - delay` must wrap at the buffer's end. A remainder (`%`) on an arbitrary length is an
  integer division per read, slow in a per-sample loop. Two common remedies: a power-of-two length with a bit mask, or
  writing every sample twice into a buffer of double length, so that a read of up to the line's length never wraps
  (Airwindows' PurestEcho, MIT, does the latter).
- **Memory.** A line long enough for its longest time is allocated before playback, never in the audio callback: at
  48 kHz, four seconds is 192,000 floats, about 750 kB per line.
- **Several taps.** Taps share one line, so a four-tap delay costs one write and four reads; summing the taps' outputs
  is the wet signal.

## Reading Between Samples

A delay time that is not a whole number of samples needs interpolation. Static times can read whole samples; any
moving time must not, or it steps by whole samples: zipper noise and grainy pitch.

| Method | Cost a read | Character |
| --- | --- | --- |
| None (whole samples) | 1 read | exact for static times; steps audibly when the time moves |
| Linear | 2 reads, 1 multiply-add | smooth, but its high-frequency loss varies with the fraction, so brightness flutters under modulation |
| 4-point Hermite or Lagrange 3rd order | 4 reads, ~12 to 15 flops | flat enough and stable under modulation: the usual choice |
| Thiran all-pass (1st order) | 1 read, recursive | flat magnitude, but clicks under fast change (documented in chowdsp_utils and Faust) |
| Windowed sinc (8 to 16 points) | 8 to 16 multiply-adds | nearly ideal; used by tables of precomputed kernels |

Open references: chowdsp_utils, `chowdsp_dsp_utils/Delay/chowdsp_DelayInterpolation.h` (GPLv3: None, Linear,
Lagrange 3rd and 5th, Thiran, Blackman-windowed sinc); Faust `delays.lib` (LGPL with an exception for compiled
programs: `fdelaylti` and `fdelayltv`, Lagrange of order N, the second robust when the time changes fast, and
`fdelay1a` to `fdelay4a`, Thiran all-passes). Theory: Laakso, Välimäki, Karjalainen and Laine, "Splitting the Unit
Delay", IEEE Signal Processing Magazine, 1996; J. O. Smith, *Physical Audio Signal Processing*.

## Changing a Delay Time

When a delay time changes, as when a tempo-synced tap follows a new tempo, an abrupt jump of the read position
clicks, and with feedback the click circulates. Two clean answers, both in open code:

- **Glide (tape style).** The read time slews to the new value, by a one-pole lag or a linear ramp of tens to hundreds
  of milliseconds. The read head moves through the stored sound faster or slower than real time, so the echoes bend in
  pitch while it moves: the swoop of tape echoes and bucket-brigade delays, musical when performed. Needs fractional
  reads.
- **Crossfade (clean).** A second read head starts at the new time and the two are crossfaded. The material is
  correlated, so the fade's gains are linear. No pitch change, no click. Surge's `sst-effects` (`Delay.h`, GPLv3) fades
  over half the delay time clamped to 10 to 500 ms, ignores a new change while a fade runs, and ignores changes of
  under half a sample. Faust's `sdelay` crossfades likewise.

Vital (`delay.cpp`, GPLv3) smooths its delay time exponentially and ramps its parameters linearly across each block.

## Feedback

Feeding a tap's output back into the line makes repeats, each quieter by the feedback gain.

- **Which tap feeds back** sets the period of the repeats. Feeding back from the longest tap repeats the whole figure
  of taps; from a shorter tap, the figure overlaps itself in a polyrhythm. Multi-head tape echoes let each head feed
  back by its own amount; the summed loop gain must then stay below one.
- **Loop filters.** A low pass in the loop darkens each repeat further than the last, as a tape or analog echo does;
  a high pass thins them, so low notes do not build a mud of echoes, and doubles as the DC blocker any nonlinearity in
  the loop needs. Surge uses a two-pole low pass and high pass at Q 0.707; Vital a band pass built from two one-poles.
- **Saturation in the loop.** A bounded curve (tanh, a soft clip) on the fed-back signal makes repeats warmer and
  grittier as they recirculate and lets feedback reach or pass unity without running away: the loop settles into a
  singing, self-sustaining tone. Asymmetric curves add DC, so a DC blocker follows them. Vital uses `hardTanh` in its
  loop; Surge offers soft, tanh and hard clipping, and inverted feedback.
- **Freeze.** With the input muted, feedback exactly one and the loop filters bypassed, the line repeats its contents
  unchanged, a small looper.
- **Diffusion.** Short Schroeder all-passes (3 to 20 ms, gain 0.5 to 0.7) in the loop smear each repeat a little more,
  so echoes melt into a reverb-like tail; high gains ring metallically.

## Around the Echoes

- **Mixing.** A delay's wet signal is usually added to an unchanged dry signal; a crossfade between dry and wet
  instead lowers the dry sound as the echoes rise, which suits insert effects that replace the sound more than echoes
  that add to it.
- **Ducking.** An envelope follower on the dry input (attack ~5 ms, release ~200 ms) lowers the wet signal while the
  dry plays, so long echoes fill the gaps without masking the line.
- **Modulation.** Slow drift (wow, 0.1 to 2 Hz, partly random) and a small fast wobble (flutter, ~5 to 12 Hz) on the
  read time, scaled as a fraction of each tap's time so that every tap bends by the same pitch ratio, as on tape.
  Small depths (0.1 to 0.3% of the time) blur repeats so they stop ringing as a comb filter; deep ones chorus.
- **Reverse.** Two read heads moving backwards through windows as long as the tap's time, crossfaded with triangular
  or Hann windows, give backwards swells; window edges are audible.
- **Rhythmic tap patterns.** Taps spaced evenly, dotted or in triplets follow the beat; geometric spacing accelerates or
  decelerates like a bouncing ball; gaps shrinking by the golden ratio (0.618) give an unrhythmic shimmer; Airwindows'
  PurestEcho places four taps at 1/4, 2/4, 3/4 and 1 of one time, its output trimmed by 1/(1 + sum of tap levels).

## The Bucket-Brigade Device

A bucket-brigade device (BBD) is an analog delay chip: a chain of N capacitor stages (commonly 512 to 4096) through
which a two-phase clock passes charge one stage each half cycle. Its delay is N / (2 f_clock): a 4096-stage chip
clocked at 10 kHz delays 205 ms.

- **Bandwidth follows the clock.** The signal is sampled at the clock rate, so its bandwidth is below f_clock / 2.
  Fixed anti-aliasing and reconstruction low passes around the chip are sized for the shortest delay; at long delays
  the clock falls toward them, so the treble falls, aliasing grit appears, and the clock leaks through as a whine:
  longer means darker and grainier.
- **Companding.** Hiss and charge loss are hidden by a 2:1 compander around the chip, compressing before and
  expanding after, so the remaining noise breathes with the signal and transients pump slightly.
- **Saturation.** The chip's limited charge range saturates softly and somewhat asymmetrically; in feedback this makes
  the warm, decaying self-oscillation of analog echoes.
- **Time changes bend pitch.** Changing the clock re-reads the stored samples at a new speed, so every repeat bends in
  pitch: inherent to the device.
- **Limited time.** Stage count and how low the clock can go before it sounds broken bound the delay, usually to a few
  hundred milliseconds; chained chips go longer at more noise.
- **Fixed taps.** Multi-tap chips bring out several stages of one line, so their taps share one clock: a clock change
  or wobble bends every tap together and keeps their rhythm, as the fixed heads of a multi-head tape echo share one
  tape speed. A digital model clocked for the longest tap places each other tap at bucket N · t_i / t_longest.

### Digital Models

- **Variable-rate line with combined filters.** Holters and Parker, "A Combined Model for a Bucket Brigade Device and
  its Input and Output Filters" (DAFx-18), fold the anti-aliasing and reconstruction filters into the rate conversion
  between the host's fixed rate and the chip's varying clock, removing a separate interpolation stage. chowdsp_utils
  implements it (`Delay/BBD/chowdsp_BBDDelayLine.h` and `chowdsp_BBDFilterBank.h`, GPLv3): a clock phase accumulator,
  even ticks writing a bucket through the input filter bank, odd ticks reading one into the output bank; each bank four
  complex one-pole sections (fourth order), coefficients evaluated at the exact tick times; no nonlinearity, noise or
  companding. Cost: both banks update every host sample (~16 real multiply-adds each) and each clock tick adds a
  complex rotation per section (~24 flops) and a bucket access, ticks per host sample being 2 f_clock / f_s: about
  60 to 100 flops a sample at echo times, 150 to 250 at the shortest delays. Because the output filter is linear and
  the taps share one clock, several taps' bucket values can be weighted and summed into one output bank, so a
  multi-tap model costs about one tap.
- **The complete circuit.** Raffel and Smith, "Practical Modeling of Bucket-Brigade Device Circuits" (DAFx-10), model
  a whole echo unit by analysis and measurement; J.-P. Cimalando's port of Raffel's echo code (MIT-style notice)
  shows the chain: a one-pole envelope follower dividing the input (compressor), a fifth-order Butterworth
  anti-aliasing filter, a bucket line advanced by a phase accumulator and read linearly at each tick, a cubic
  waveshaper and noise near -60 dB, third- and second-order reconstruction filters, an expander, and regeneration.
  About 60 to 80 flops a sample plus the ticks.
- **A fixed line with time-dependent filtering.** A cheaper approximation keeps an ordinary fractional delay line and
  lowers a loop and output low pass as the time grows (f_c ≈ k · N / (2 t)), adds noise scaled by time, saturation and
  a compander: about 30 to 40 flops, losing the true aliasing grit and exact bandwidth behaviour.

## Open Implementations Read

| Project | Licence | What it shows |
| --- | --- | --- |
| chowdsp_utils (`chowdsp_dsp_utils`) | GPLv3 (core modules BSD) | interpolation choices; the BBD line and filter banks |
| Surge XT, sst-effects `Delay.h` | GPLv3 | sinc taps; glide or crossfade time changes; loop filters; clip modes; LFO depth in semitones |
| Vital `delay.cpp` | GPLv3 | smoothed time, block ramps, ping-pong modes, band-pass loop, hard tanh |
| Airwindows PurestEcho | MIT | four fixed-fraction taps, double-written buffer, linear reads |
| Faust `delays.lib` | LGPL with exception | Lagrange and Thiran fractional delays, crossfading delay, multi-tap sinc |
| Raffel's echo code (Cimalando's port) | MIT-style | the complete BBD echo circuit |
