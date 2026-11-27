# Chip Tables: the Measured and Derived Data of Three Sound Chips

The numbers that make three classic sound chips sound as they do, where each number comes from (measured on real
chips, read from die photographs, or derived from a circuit), which open project holds it and under which licence,
and how each is rendered at a host sample rate in a real-time callback that neither allocates nor locks. The three
chips are:

- **The 1982 home computer's sound chip**, in its first revision and its later one: three voices, each a 24-bit
  phase accumulator read as a saw, a folded triangle, a compared pulse or a shift register's noise, through a
  resistor-ladder converter, an envelope with a rate counter, and an analog multimode filter.
- **The 1989 handheld console's sound unit**: two pulse channels (the first with a pitch sweep), a wave channel of 32
  four-bit samples, a noise channel from a 15-bit or 7-bit shift register, four-bit envelopes and a high-pass
  capacitor at the output.
- **The 1983 home console's sound unit**: two pulse channels with four duty cycles and sweeps, a stepped four-bit
  triangle, a noise channel with two modes and a period table, a sample channel, and a nonlinear resistor mixer
  followed by output filters.

`HARD_DIGITAL.md` (2.5 to 2.8) gives the registers in the context of noise synthesis, `ENGINES_RESEARCH.md` (10) the
voices in outline, and `WAVETABLES.md` (2, 8.3) the mip-mapped tables these chips' cycles are built into. This
chapter holds the exact data and the methods that are specific to the chips.

Contents:

1. Sources and their licences
2. Which aliasing belongs to the chip
3. Band-limiting a chip at the host rate
4. The 1982 home computer's sound chip
5. The 1989 handheld console
6. The 1983 home console
7. Building chip tables off the callback
8. Measuring a chip model
9. Hazards at a glance
10. References

## 1. Sources and Their Licences

A chip's behaviour is a fact; the code and the prose that describe it are works under a licence. A program under
GPL-3.0-or-later may take code from a project whose licence is compatible with GPLv3, crediting it; it must not take
code from a project under GPL-2.0-only, which cannot be combined with GPLv3 code. Numbers measured on hardware
(a period table, a filter corner) can be checked against several independent sources, and where a GPL-2.0-only
project is the only one to hold a number, the number is verified elsewhere before use.

| Project or document | Licence | Compatible with GPLv3 | What it holds |
| --- | --- | --- | --- |
| reSID, Dag Lem (`daglem/reSID`; the copy in VICE; `libsidplayfp/resid`) | GPL-2.0-or-later | yes | the 1982 chip: cycle-exact digital part, ladder DAC model, sampled combined waveforms, envelope tables, transistor-level filter for each revision, output stage |
| reSIDfp in libresidfp (`libsidplayfp/libresidfp`), Leandro Nini and Antti Lankila | GPL-2.0-or-later | yes | the 1982 chip: parametric combined-waveform model fitted to new samplings, DAC with leakage and saturation, filter op-amp models, noise write-back |
| combined-waveforms (`libsidplayfp/combined-waveforms`) | GPL-2.0-or-later | yes | the samplings of many chips and the Monte Carlo fitting tools behind reSIDfp's parameters |
| SID-Article (`libsidplayfp/SID-Article`) | CC0-1.0 | yes | a written description of the 1982 chip's internals |
| libsidplayfp's transistor-level simulation of the chip | MIT | yes | a transistor-level simulation of the chip's digital part, from die photographs |
| VICE | GPL-2.0-or-later | yes | carries reSID, and its own faster chip model |
| SameBoy, Lior Halphon (`LIJI32/SameBoy`) | MIT (Expat) | yes | the 1989 handheld: every channel, per-model quirks, wave memory at power-on, the high-pass, and a band-limited step synthesiser |
| Pan Docs (`gbdev/pandocs`) | CC0-1.0 | yes | the handheld's registers, clocks, DAC, mixer and high-pass, in prose and formulas |
| mGBA, Jeffrey Pfau | MPL-2.0 | yes (MPL 2.0 permits GPL as a secondary licence) | the handheld's sound unit |
| Gambatte, Sindre Aamås | GPL-2.0-only | **no** | the handheld's sound unit; not to be read for implementation |
| Game_Music_Emu and Blip_Buffer, Shay Green (`libgme/game-music-emu`) | LGPL-2.1-or-later | yes | band-limited step synthesis; both consoles' sound units |
| Mesen2, Sour (`SourMesen/Mesen2`) | GPL-3.0 | yes | the 1983 console: channels, period, length and frame tables (NTSC and PAL), mixer |
| Nestopia UE (`0ldsk00l/nestopia`) | GPL-2.0-or-later | yes | the 1983 console's sound unit |
| FCEUX (`TASEmulators/fceux`) | GPL-2.0-or-later | yes | the 1983 console's sound unit |
| the 1983 console's developer community wiki, and blargg's reference notes it cites | no licence stated | facts only | the mixer formulas and their table forms, the output filters, every channel's tables |
| MAME | per file (BSD-3-Clause or GPL-2.0-or-later) | per file | other chips (`HARD_DIGITAL.md`, 2.5) |

Where a fact appears only in a source with no stated licence, the number is cited and the code is written from the
number, or taken from a compatible project that holds the same number (Mesen2 holds every table of the 1983 console;
Pan Docs, under CC0, every formula of the handheld).

## 2. Which Aliasing Belongs to the Chip

Each of these chips runs at a clock of one to four megahertz and drives an analog output. Inside the chip, nothing
folds into the audio band: a waveform changes level on clock edges a microsecond or less apart, and the steps of a
four-bit staircase are real steps in the analog signal. Their spectrum is the staircase's spectrum, harmonics that
continue far above hearing, softened only by the output's analog filters. An emulation that produces samples at
44.1 or 48 kHz must band-limit that staircase: every component above half the host rate that is not removed folds
back to an unrelated frequency, an alias the chip never made.

| Feature | The chip's own sound, kept | Made only by a naive emulation, removed |
| --- | --- | --- |
| Four-bit staircases (the handheld's wave, the console's triangle) | the steps' images at 32 k ± h times the fundamental, up to half the host rate | the same images above half the rate folded down |
| Pulses at the chip's duty cycles | every harmonic of the pulse | folded harmonics, heard as rough inharmonic tones on high notes |
| Pitch quantised to a period register | the detuning of each note, several cents to tens of cents at the top | none: the quantisation is in the chip |
| A converter's uneven steps (the 1982 chip's ladder) | the bent saw and the extra harmonics the unevenness adds | aliases of those harmonics |
| Noise clocked by a shift register | the spectrum of a zero-order-held random sequence at the register's clock, with its nulls at multiples of the clock | aliasing of the held steps when the clock is near or above the host rate |
| The console's triangle at ultrasonic periods | an inaudible ultrasonic tone and the level it rests at | a loud alias of that ultrasonic tone |
| The console's sample channel and digitised playback | the staircase at the sample rate, and the one-bit delta encoding's noise | folding of the staircase's images |
| Envelope and volume steps | each step of level, and on the handheld the step of offset it makes (5.4) | none |

Every chip feature therefore renders at the host rate as a band-limited version of a staircase or of a periodic
cycle. The only aliasing that a faithful emulation keeps is aliasing that the chip itself produced in its digital
domain before the converter. None of the three chips samples its own waveforms at an audio rate in a way that folds:
the 1982 chip's accumulator at about 1 MHz adds a timing jitter of up to one microsecond to its edges, a part in a
thousand of a 1 kHz cycle and inaudible, and the sample channel of the 1983 console plays its stored bits at its own
rate, whose staircase is real and whose images are kept as steps.

## 3. Band-Limiting a Chip at the Host Rate

Three methods are in use. They differ in what they need from the signal: a fixed periodic cycle, a list of level
changes with their times, or a few known discontinuities per cycle.

### 3.1 Mip-mapped tables of one cycle

A fixed cycle (a duty pulse, 32 steps of wave memory, the 32-step triangle, the 1982 chip's saw and triangle through
its converter, a combined waveform) is built into band-limited levels by one forward transform at full table length
and an inverse transform per level, each keeping the harmonics under half the host rate at the top of its range
(`WAVETABLES.md`, 2.2). The staircase is sampled into the table at a whole number of table samples per step (2048 /
32 = 64), so the forward transform sees exactly the staircase the chip makes, and the steps' images are kept up to
each level's limit and no further.

Two points matter for chips in particular:

- **One gain for a waveform's levels.** A level scaled to its own peak changes the waveform's loudness with the
  note. Measured on the build that scales each octave level to its own peak (2048 samples, levels an octave apart
  from 8 Hz, 48 kHz), the fundamental's level relative to the lowest level, which keeps every harmonic, is:

  | Cycle | 32 to 4096 Hz (levels 2 to 8) | 4 to 8 kHz | above 8 kHz |
  | --- | --- | --- | --- |
  | pulse of 12.5 % duty | -0.6 to -1.0 dB | +5.4 dB | +11.1 dB |
  | pulse of 25 % duty | -0.9 to -1.1 dB | -0.2 dB | +4.4 dB |
  | pulse of 50 % duty, or 32 steps of square | -1.4 to -1.5 dB | -2.1 dB | -2.1 dB |
  | 32 steps of four-bit triangle, rounded from the ideal shape | -0.1 to +0.7 dB | +2.1 dB | +2.2 dB |
  | saw | -0.1 to -1.4 dB | +1.6 dB | +3.9 dB |

  Inside the usual melodic range the error is a near-constant offset with steps of a few tenths of a decibel at each
  boundary; at the top, where a pulse sweep, an arpeggio or a high lead reaches, the narrow pulse jumps by up to
  11 dB. With one gain per waveform, taken from the level holding all harmonics, each harmonic keeps its amplitude in
  every level and the top levels peak below one, which is the chip's own behaviour: a narrow pulse heard as a lone
  fundamental is quiet. The same gain also keeps the chip's relative loudness between waveforms: on the handheld a
  12.5 % pulse has about 3.6 dB less power than a 50 % one at the same volume setting, and it should.
- **Levels per octave.** A level built for the top of its octave leaves a note at the bottom of the octave with no
  harmonic above a quarter of the host rate (`WAVETABLES.md`, 2.2). For a chip, whose brightness is its identity, two
  levels an octave (top of spectrum at a level's bottom 17 kHz at 48 kHz) or a crossfade between neighbouring levels
  keep the staircase's upper images through each octave.

A lowest level whose harmonic limit exceeds half the table length keeps all `N/2 - 1` harmonics and no Gibbs ripple,
so it is the natural reference for the waveform's single gain.

Tables suit any periodic cycle that does not change with a continuous control. A pulse whose width sweeps
continuously (the 1982 chip's 12-bit width) needs either a table per width, or a method that places the edges
(3.3). The four fixed duties of the two consoles, and a wave memory that a program rewrites only at moments, are
tables.

### 3.2 Band-limited steps

Blip_Buffer (Shay Green, LGPL-2.1-or-later, in Game_Music_Emu) and SameBoy's own synthesiser (MIT, "loosely based on"
the same author's band-limited synthesis notes) treat the chip's output as a sequence of level changes at exact
times. Each change `delta` at time `t` (in output samples, fractional) adds `delta` times a band-limited step to an
accumulation buffer; the output is the running sum. Because the chip's output is piecewise constant, this is exact:
the band-limited signal is the staircase convolved with a low-pass kernel, and the staircase is the sum of its steps.

SameBoy's kernel (`Core/apu.c`, `band_limited_init`):

```
WIDTH  = 64           // taps of each step's impulse
PHASES = 256          // sub-sample positions
master[i], i in 0 .. WIDTH*PHASES:
    window = a0 - a1 cos(2 pi i / M) + a2 cos(4 pi i / M)     // exact Blackman: a0 = 7938/18608,
                                                             // a1 = 9240/18608, a2 = 1430/18608
    angle  = (i - M/2) * pi / PHASES * 15/16                 // cutoff at 15/16 of half the host rate
    master[i] = sinc(angle) * window,  then normalised to sum 1
steps[phase][k] = sum over j in 0 .. PHASES of master[k*PHASES - phase + j]   // one tap = a box of PHASES sub-samples
steps[phase][WIDTH/2] += 1.0 - sum_k steps[phase][k]                           // every phase sums exactly to 1
```

Each change adds `delta * steps[phase][k]` to `buffer[(pos + delay + k) mod 128]`; reading a sample adds
`buffer[pos]` to the running output and clears the slot. The correction at the centre tap makes every step reach
exactly `delta`, so the running sum never drifts; without it, rounding in fixed point makes the output walk away by
a little at every change. Blip_Buffer integrates the same way and adds a leaky integrator (its `bass_freq`, 16 Hz by
default) so that any residual offset decays. Blip_Buffer's quality settings are 8, 12 and 16 taps (`blip_med_quality`,
`blip_good_quality`, `blip_high_quality`), with 64 or 256 phases (`BLIP_PHASE_BITS` 6 or 8), and a treble shelf
(`blip_eq_t`) that shapes the kernel's top octave, usable to imitate the chip's output low-pass.

For a real-time callback:

- The kernel is a fixed array, built once; the accumulation buffer is a fixed ring of at least twice the width per
  voice. Nothing is allocated per note.
- The output is delayed by half the kernel (32 samples at 64 taps, under a millisecond), the same for every voice, so
  it can be absorbed by starting a voice that many samples early or simply accepted.
- The cost is per level change: `WIDTH` multiply-adds. A 50 % pulse at 1 kHz makes 2000 changes a second, about 2.7
  multiply-adds a sample with 64 taps; a 32-step wave at 2 kHz makes up to 64 000, about 85 a sample; a noise register
  clocked at 100 kHz, 133 a sample. With 16 taps, a quarter of that.
- A change of volume or envelope is simply another level change, so the envelope's steps come out band-limited too.
- A static nonlinearity applied to the levels before they become steps (the 1983 console's mixer, 6.7; a converter
  table) commutes with the method: the nonlinearity of a staircase is another staircase, so applying it to each level
  and band-limiting the result's changes is exact and costs nothing at audio rate.

### 3.3 PolyBLEP and its relatives

A two-sample polynomial correction at each discontinuity (`QUALITY_RESEARCH.md`, 1) costs a few operations per edge,
needs no buffer and no delay, and suppresses aliasing by 20 to 30 dB in the upper octaves. It suits a few edges a
cycle whose times are known: a pulse of any width, including one that moves every sample, a hard-sync reset, the
edges of a noise register clocked well below the host rate. Its suppression is too weak for a bright 32-step
staircase at high notes, whose many small steps each need a correction and whose sum of residual aliases is heard as
a haze; there the table or the long step kernel is better. A wider kernel with the same per-edge structure (the
four-sample BLEP, or the one-sample-delayed form the sync code of Plaits uses) sits between the two.

### 3.4 Noise at a clock near or above the host rate

A register clocked at `f_c` gives a held random sequence whose spectrum is flat up to near `f_c` and falls to a null
at `f_c` (the sinc of the hold). When `f_c` is far below the host rate, each change is a step to band-limit. When `f_c`
is near or above it, many register states fall inside one output sample:

- **Box averaging.** The register is stepped as many times as its clock falls in the sample, and the output is the
  time-weighted mean of the levels held. This is a first-order band-limit (a box filter, first null at the host
  rate), exact in its average, and costs one register step per clock (`HARD_DIGITAL.md`, 2.8).
- **Steps.** Every change into the step buffer; exact, but costly at hundreds of kilohertz.
- **Crossfade to white.** Once the clock is above a quarter of the host rate, the band-limited result is
  indistinguishable from white noise at the same power, and Plaits' clocked noise crossfades to raw noise there.
- **Precomputed run.** The register's sequence is tabulated once; any of the above then reads it by index.

Reading one tabulated value per output sample while skipping the states in between (a sample-and-hold of the
register at the host rate) is neither: it aliases the hold's whole spectrum and, at high clocks, plays a decimated
sequence whose period and colour are not the chip's.

### 3.5 Choosing per source

| Source | Method that renders it exactly | Cheaper method and what it loses |
| --- | --- | --- |
| Fixed duty pulse, 32-step wave, 32-step triangle | mip-mapped table, two levels an octave or crossfaded | one level an octave: duller at each octave's bottom |
| Saw and triangle through an uneven converter | mip-mapped table of the converted cycle | none |
| Pulse of continuous width | polyBLEP at both edges; or steps | a table per width (memory) |
| Combined waveform without pulse | table | none |
| Combined waveform with pulse | table read only while the pulse is high, the gate's edges corrected by BLEP; or a table per width | the product of two band-limited signals reaches twice their bandwidth: the table is read one level higher, or the voice oversampled twice |
| Shift-register noise | steps at low clocks, box averaging at high clocks | sample-and-hold: aliasing and a wrong period |
| Envelope, volume and mixer levels | steps, or a ramp of one or two samples | an unsmoothed multiply: a click at each level change |
| Sample channel | steps | linear interpolation: images of the staircase fold |

## 4. The 1982 Home Computer's Sound Chip

### 4.1 Oscillator

Each voice is a 24-bit accumulator advanced by a 16-bit frequency word every clock: the output frequency is
`F * f_clock / 2^24`, with `f_clock` 985 248 Hz on PAL machines and 1 022 727 Hz on NTSC ones, giving a resolution of
0.059 Hz and a top of 3.85 kHz. The waveform generator reads the accumulator's top 12 bits (reSID `wave.h`,
`wave.cc`; reSIDfp `WaveformCalculator.cpp`):

```
saw      = acc >> 12                                          // 12 bits
triangle = ((acc ^ (msb ? 0xFFFFFF : 0)) >> 11) & 0xFFE       // folded by the top bit, the lowest bit 0
         // ring modulation replaces msb by msb XOR (NOT the sync source's msb)
pulse    = (acc >> 12) >= pulse_width ? 0xFFF : 0x000          // a comparator, 12-bit width
noise    = 8 bits of the shift register into output bits 11..4 (4.4)
```

Hard sync resets the accumulator to zero when the sync source's top bit rises. reSIDfp keeps a special case verified
by sampling: a source that is itself reset on the same cycle as its top bit rises does not reset its destination.

### 4.2 The waveform converter

Each 12-bit output word drives a converter built as an R-2R ladder (reSID `dac.h`; reSIDfp `Dac.cpp`):

```
         n  n-1      2   1   0    ground
         |   |       |   |   |      |    termination: only in the later revision
        2R  2R      2R  2R  2R     2R
         |   |       |   |   |      |
   out --R---R--...--R---R--    ---
```

- **First revision:** the ratio `2R/R` is about 2.20 and the termination at bit 0 is missing. **Later revision:**
  `2R/R` = 2.00 and terminated, so its converter is linear.
- Each bit's contribution is worked out by parallel substitution down the ladder (the tail below the bit) and source
  transformation up to the output; any word's output is the sum of its bits' contributions (superposition). reSID
  scales the full word to `2^bits - 1`; reSIDfp divides each bit by the sum of all.
- The first revision's bit weights, in units of the ideal least significant bit (full scale 4095): 2.1, 3.0, 5.3,
  10.0, 19.3, 37.4, 72.4, 140.4, 272.1, 527.5, 1022.7, 1982.8. The lower bits run together, and the eleven lower bits
  sum to 2112.2, more than the top bit's 1982.8: stepping from `0x7FF` to `0x800` **falls** by 129 least significant
  bits. The saw therefore dips at the middle of its rise, and the triangle at its top and bottom quarters, a fixed
  non-monotonic glitch that adds a faint upper harmonic series and is part of that revision's grainy tone.
- reSID's comment records that on real chips the output for bit 0 equals the output for bit 1. The ladder with
  `2R/R` = 2.20 gives 2.1 and 3.0, not equal; the ratio fits the higher bits' errors, and the lowest bits' equality is
  an observation the model approximates rather than reproduces. A test that bit 0 and bit 1 come out alike holds only
  if something else (such as leakage) dominates them.
- **Leakage** (reSIDfp): a switched-off bit still contributes `leakage` times its weight, 0.0075 in the first
  revision and 0.0035 in the later. Since `out(w) = L * sum(all) + (1 - L) * sum(on)`, leakage alone is an offset and a
  gain, an affine map that changes nothing audible once the cycle's offset is removed and its level set. It matters
  only together with a nonlinearity after it.
- **Saturation** (reSIDfp, first revision only, applied to the waveform converter): `y = 1.1 x - 0.11 x^3` on the
  normalised output, described by its authors as a rough model of the two source followers at the converter's and
  the volume multiplier's outputs. It bows the saw's top slightly.
- **The zero level.** The voice's output is `(wave_dac(word) - wave_dac(zero)) * env_dac(envelope)`, with `zero` at
  `0x380` on the first revision (reSID `voice.cc`, measured; reSIDfp makes it adjustable from `0x380` to `0x580`) and
  `0x800` on the later. On the first revision every waveform therefore carries an offset that the envelope multiplies:
  the soft thump at note-on and the audible volume-register "click" that programs exploited to play samples. A model
  that removes each cycle's average, then multiplies by the envelope, drops that thump on purpose.
- **The envelope converter** is an 8-bit ladder of the same build, so the envelope's 256 levels are uneven in the
  first revision in the same way (reSID `envelope.cc`, `DAC<8>(2.20, false)`; reSIDfp `envDAC`).

### 4.3 Combined waveforms

Selecting two or more waveforms at once connects their outputs to the same 12 output lines. Each line is pulled low by
any selected waveform whose bit is 0, so the result is close to a bitwise AND, and neighbouring lines pull each other
down further through the shared wiring. The notes of the combined-waveforms project record what the die shows:
selecting the triangle grounds the output's lowest bit; selecting the saw disables the triangle's fold, so saw plus
triangle is the saw ANDed with itself shifted left by one (`saw & (saw << 1)`); selecting the pulse interconnects all
bits; in the later revision the upper eight selectors of saw plus triangle have double resistance; and on the first
revision the saw's top output bit is wired to the accumulator's top bit, so a low output pulls the accumulator's top
bit down (the "top bit write-back").

**Sampled tables (reSID).** reSID holds, for each revision, four tables of 4096 entries: saw plus triangle, pulse plus
triangle, pulse plus saw, and all three (`wave*__ST`, `wave*_P_T`, `wave*_PS_`, `wave*PST`, as `.dat` files converted
by `samp2src.pl`). Each was sampled from the third voice's oscillator read-back register with the frequency word at
`0x1000`, so that the top 12 accumulator bits advance by one each clock and 4096 clocks give one entry per accumulator
value. The read-back register is 8 bits wide, so the lowest 4 bits of each entry are lost; the tables store `value <<
4`. Combinations with pulse are the table value ANDed with the pulse's 0 or `0xFFF`; pulse plus triangle under ring
modulation indexes with the substituted top bit. The combined-waveforms project notes that the old samplings of the
first revision's combinations with saw are affected by the top bit write-back, so that their second half mirrors the
first; newer samplings avoid it.

**Parametric model (reSIDfp `WaveformCalculator.cpp`).** reSIDfp computes the tables instead, from a model fitted by
Monte Carlo search to samplings of several chips (the combined-waveforms project). For a base word (`tri` for pulse
plus triangle, `saw` for pulse plus saw, `saw & (saw << 1)` for saw plus triangle and for all three), each set bit is
weakened by its zero neighbours:

```
bit[i] = (word >> i) & 1;  bit[11] *= topbit
distance[12 +- k] = distFunc(distance1 or distance2, k)     // below and above the bit
for each bit sb:
    pulldown[sb] = (sum over cb != sb of (1 - bit[cb]) * distance[sb - cb + 12] - pulsestrength)
                   / (sum over cb != sb of distance[sb - cb + 12])
out bit sb = bit[sb] and (1 - pulldown[sb]) > threshold
distFunc: exponential d^-k, linear 1 / (1 + k d), or quadratic 1 / (1 + k^2 d)
```

The parameters (`distFunc, threshold, topbit, pulsestrength, distance1, distance2`), for the "average" chips:

| Revision, combination | Distance | Threshold | Top bit | Pulse strength | Distance 1 | Distance 2 |
| --- | --- | --- | --- | --- | --- | --- |
| first, saw plus triangle | exponential | 0.79111582 | 1.06053483 | 0 | 1.97922957 | 2.67848182 |
| first, pulse plus triangle | linear | 0.941692829 | 1 | 1.80072665 | 0.033124879 | 0.232303441 |
| first, pulse plus saw | linear | 1.09394681 | 1.42332006 | 3.44251633 | 0.0797301158 | 0.102444135 |
| first, all three | linear | 1.53609717 | 0.0391017497 | 1.67601228 | 1.44580793 | 1.42448807 |
| later, saw plus triangle | exponential | 0.853578329 | 1.09615636 | 0 | 1.8819375 | 6.80794907 |
| later, pulse plus triangle | exponential | 0.929835618 | 1 | 1.12836814 | 1.10453653 | 1.48065746 |
| later, pulse plus saw | quadratic | 0.911938608 | 0.996440411 | 1.2278074 | 0.000117214302 | 0.18948476 |
| later, all three | exponential | 0.938004673 | 1.04827631 | 1.21178246 | 0.915959001 | 1.42698038 |

reSIDfp also holds "weak" and "strong" sets from other chips, since combined waveforms vary from chip to chip and
with temperature; the fitted error for each set is stated beside it in the source. The result is a 4096-entry 12-bit
table per combination, built once and cached; every bit of resolution is kept, unlike the 8-bit samplings.

**With noise.** Any combination including noise drives the shift register's bits through the output lines (the
write-back), so the register fills with zeros within a few shifts and the output falls silent until the register is
reset; reSID and reSIDfp both model it. reSID's noise-plus-pulse approximations are `noise < 0xF00 ? 0 : noise &
(noise << 1) & (noise << 2)` for the first revision and `noise < 0xFC0 ? noise & (noise << 1) : 0xFC0` for the later.

**Rendering.** A combination without pulse is a fixed cycle: its table goes through the converter (4.2) and into
mip-mapped levels like the saw. A combination with pulse is the table gated by the pulse; see 3.5.

### 4.4 Noise

A 23-bit shift register; the new bit 0 is `bit 22 XOR bit 17`, shifted in from the bottom (reSID `wave.h`,
`clock_shift_register`):

```
bit0 = ((sr >> 22) ^ (sr >> 17)) & 1
sr   = ((sr << 1) | bit0) & 0x7FFFFF
out  = bit 20 -> 11, bit 18 -> 10, bit 14 -> 9, bit 11 -> 8, bit 9 -> 7, bit 5 -> 6, bit 2 -> 5, bit 0 -> 4
reset value 0x7FFFFF
```

- **Clock.** The register shifts once each time accumulator bit 19 rises, which happens every `2^20` added to the
  accumulator, so **16 times per cycle of the voice's tone**. The noise is pitched by the frequency word: its
  register clock is 16 times the tone, from under 1 Hz to about 62 kHz.
- **Bit numbering.** reSID 1.0 corrected "the output and feedback topology" from die photographs. Older emulators
  and the documents drawn from them read bits 22, 20, 16, 13, 11, 7, 4 and 2, which is the same pattern two places
  higher; the die-derived reading above is reSID 1.0's, and reSIDfp's, which stores the register in reverse order
  (its `set_noise_output`: bit 20 of the chip in its bit 2, and so on).
- **Period.** The taps give a maximal sequence of `2^23 - 1` = 8 388 607 shifts. A tabulated run of 32 768 shifts
  repeats after 2048 tone cycles, under five seconds at 440 Hz; a run long enough not to be heard as a loop is a
  few hundred thousand entries (one byte each suffices, the eight output bits).
- **Test bit and write-back.** Holding the test bit resets the accumulator, and after a time (about 0x8000 cycles on
  the first revision, 0x950000 on the later, reSID `wave.cc`) the register's floating bits turn high, which is how a
  program restarts silenced noise. reSIDfp models the two-phase shift and the write-back through combined
  waveforms exactly (combined-waveforms notes, "Noise writeback").
- **Converter.** The 8 bits land in output bits 11 to 4, so the noise goes through the uneven upper converter like the
  other waveforms.

The noise is a held sequence clocked at 16 times the tone; it is band-limited as in 3.4. For notes above about
1.5 kHz its clock passes half of a 48 kHz host rate, and above 3 kHz the rate itself, where averaging, or the
crossfade to white noise, takes over.

### 4.5 Envelope

The envelope is an 8-bit counter moved by a 15-bit rate counter and, while falling, an exponential divider (reSID
`envelope.h`, `envelope.cc`):

| Setting | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Rate period, clocks | 9 | 32 | 63 | 95 | 149 | 220 | 267 | 313 | 392 | 977 | 1954 | 3126 | 3907 | 11720 | 19532 | 31251 |
| Attack, 0 to 255 | 2 ms | 8 ms | 16 ms | 24 ms | 38 ms | 56 ms | 68 ms | 80 ms | 100 ms | 250 ms | 500 ms | 800 ms | 1 s | 3 s | 5 s | 8 s |

- The periods are the attack times times 1 MHz / 256, rounded up by one. reSIDfp implements the rate counter as a
  15-bit LFSR, as on the die, and compares it with the LFSR state reached after that many steps (its `adsrtable`:
  `0x007F, 0x3000, 0x1E00, 0x0660, 0x0182, 0x5573, 0x000E, 0x3805, 0x2424, 0x2220, 0x090C, 0x0ECD, 0x010E, 0x23F7,
  0x5237, 0x64A8`); the two descriptions give the same periods.
- The attack is linear. Decay and release step the counter down once every `rate period * exponential period`
  clocks, the exponential period set when the counter reaches `0xFF`: 1, `0x5D`: 2, `0x36`: 4, `0x1A`: 8, `0x0E`: 16,
  `0x06`: 30, `0x00`: 1. Decay and release times are three times the attack's: 6 ms to 24 s.
- Sustain levels are `0x11 * s`: the counter's top and bottom nibbles are compared with the 4-bit sustain.
- **The rate counter is never reset.** A gate or a rate change while the counter is above the new period lets it run
  round its 15-bit range first: up to 32 767 clocks, about 33 ms, before the envelope moves. This is the well-known
  delay that makes note starts uneven unless a program works around it, and reSID and reSIDfp both model it.
- The envelope's output goes through its own uneven converter (4.2).

### 4.6 Filter

A two-integrator-loop state-variable filter giving low-pass, band-pass and high-pass at 12 dB an octave, any of them
mixed, with a 4-bit resonance and an 11-bit cutoff. The two revisions differ completely in their analog build.

**First revision** (reSID `filter.h`, `filter.cc`; reSIDfp `FilterModelConfig` for it):

- Integrating capacitors of 470 pF on most boards (2200 pF on an early board, 330 pF in one unusual case; reSIDfp's
  `CAPS2200`, `CAPS470`, `CAPS330`).
- The cutoff resistor is an NMOS transistor used as a voltage-controlled resistor, its gate driven by the 11-bit
  cutoff word through another uneven ladder converter (`2R/R` = 2.20, unterminated), offset and scaled (reSID: 6.65 V
  plus 2.63 V times the converter's output; reSIDfp: 7.15 V and 2.63 V). The transistor's conduction follows a model
  with `Vdd` = 12.18 V, `Vth` = 1.31 V, `u Cox` = 20 uA/V^2, `W/L` = 9 for the control transistor and 1/115 for the
  "snake" transistor, thermal voltage 26 mV.
- The minimum cutoff, measured, is about 220 Hz, from which reSID derives the snake's resistance of about 1.5 Mohm.
  The cutoff rises slowly over the lower third of the word and steeply above, the curve varying from chip to chip by
  an octave or more; a model built from the transistor equations reproduces the shape, a spline of measured points
  one chip's.
- The op-amps are NMOS inverters with a measured transfer curve, the same in both projects: `(0.81, 10.31), (2.40,
  10.31), (2.60, 10.30), (2.80, 10.26), (3.00, 10.04), (3.20, 9.58), (3.50, 8.69), (4.00, 6.89), (4.40, 5.21),
  (4.54, 4.54)` (the working point), `(4.80, 3.00), (4.90, 2.30), (5.00, 1.88), (5.20, 1.58), (5.60, 1.33), (6.00,
  1.21), (7.00, 1.02), (8.50, 0.89), (10.00, 0.81)` volts in and out (reSID's full list has 33 points). Their low gain
  is why the filter distorts and why resonance cannot reach very high Q.
- Resonance: from die photographs, `1/Q ~ (~res & 0xF) / 8` with ideal parts, so Q from 0.533 to 8, and unbounded at
  15; with the real op-amps' low gain, setting 0 gives about Q 0.8 to 1.0.
- The voice's signal is about 1.5 V riding on about 5 V into the filter.

**Later revision** (reSID 1.0's filter of that revision; reSIDfp `FilterModelConfig` for it):

- Integrating capacitors of 22 nF, a linear cutoff control: reSID 1.0's interim model is `w0 = 2 pi * 12500 *
  (fc + 1) / 2048`, a cutoff from 6 Hz to 12.5 kHz in equal steps.
- A measured op-amp curve with a far higher gain: `(1.30, 8.91), (4.76, 8.91), (4.80, 8.25), (4.81, 6.10), (4.815,
  4.05), (4.82, 2.27), (4.83, 1.55), (4.90, 1.34), (5.00, 1.30), (8.91, 1.30)`, `Vdd` 9.09 V, `Vth` 0.80 V,
  `u Cox` 100 uA/V^2 in reSIDfp.
- Resonance by two resistor ladders, the feedback gain for setting `s` (reSIDfp's `resGain`): 1.4, 1.28263, 1.17471,
  1.07869, 1, 0.916168, 0.83908, 0.770492, 0.7, 0.641317, 0.587356, 0.539344, 0.5, 0.458084, 0.41954, 0.385246.

**The output stage** of the computer (reSID `extfilt.h`; reSIDfp `ExternalFilter.cpp`): a first-order low-pass of
10 kohm and 1 nF, 15.9 kHz, and a first-order high-pass of 10 uF into the load, 1.6 Hz into 10 kohm, modelled at 16 Hz
(a 1 kohm load) so that the signal settles; reSIDfp makes the load adjustable, 1.6 to 15.9 Hz.

**In a callback.** reSIDfp builds its op-amp and transistor tables (tens of thousands of entries) when the chip model
is chosen, in four threads; a synth engine builds them when the instrument is compiled, never per note. Both
emulators run the filter at the chip's 1 MHz clock; at audio rates a high resonance needs the filter oversampled or
solved implicitly (`QUALITY_RESEARCH.md`, 3), and its nonlinearity belongs inside the loop, at the integrators'
op-amps.

## 5. The 1989 Handheld Console

### 5.1 Clocks and pitch

The master clock is 4 194 304 Hz. The pulse channels' period dividers count up from an 11-bit value `x` at
1 048 576 Hz and step an 8-step duty sequence; the wave channel's counts at 2 097 152 Hz and steps 32 samples (Pan Docs
`Audio_Registers.md`):

```
pulse frequency = 131072 / (2048 - x)       64 Hz (x = 0) up to 131 kHz
wave  frequency =  65536 / (2048 - x)       32 Hz (x = 0) up to 65.5 kHz
```

So the wave channel reaches an octave lower than the pulses and, for the same note, has half the register steps
below it: its tuning is coarser. A note is played at the nearest register value. The error in cents of the nearest
register value for each equal-tempered note:

| Note | A2, 110 Hz | A4, 440 Hz | A5, 880 Hz | A6, 1760 Hz | E7, 2637 Hz | A7, 3520 Hz | C8, 4186 Hz |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Pulse | 0.6 | 0.6 | 0.6 | 11.0 | 10.3 | 11.0 | 17.3 |
| Wave | 0.6 | 0.6 | 11.0 | 11.0 | 10.3 | 35.1 | 37.6 |

Below 64 Hz no pulse note exists; below 32 Hz no wave note. A model that clamps the register at its end plays every
lower note at the lowest pitch.

### 5.2 Pulse channels

The duty sequences, one bit per step (SameBoy `Core/apu.c`, `duties`):

| Duty | Sequence |
| --- | --- |
| 12.5 % | 0 0 0 0 0 0 0 1 |
| 25 % | 1 0 0 0 0 0 0 1 |
| 50 % | 1 0 0 0 0 1 1 1 |
| 75 % | 0 1 1 1 1 1 1 0 |

The 75 % duty is the 25 % inverted and sounds the same; the phase of each sequence matters only when two channels
play together or the duty changes mid-note (Pan Docs). A high step outputs the channel's 4-bit volume, a low step 0.

### 5.3 Wave channel

32 four-bit samples in 16 bytes, high nibble first, read in turn; a 2-bit output level plays them at 100 %, 50 %
(shifted right once), 25 % (twice) or mutes them. The shift acts on the digital value, so a quieter setting also moves
the waveform's centre towards 0 and coarsens it to 3 or 2 bits (Pan Docs `Audio_details.md`).

**Contents at power-on.** On the first model and its pocket-sized revision, wave memory holds a pattern that differs
from unit to unit; SameBoy approximates it with random bytes, ORed together for even bytes and ANDed for odd ones (two
draws on the pocket-sized revision, three on the first), so that even bytes lean to set bits and odd ones to clear
bits (its power-on code). On the colour model the start-up program writes alternating `0x00` and `0xFF` bytes: the
samples 0, 0, 15, 15 repeated eight times, a square three octaves above the channel's note, which is what a program
that plays the wave channel without loading it hears. The earliest colour revision leaves wave memory as it powered up (Pan Docs
`Power_Up_Sequence.md`).

A program that rewrites wave memory during a note changes the waveform at that moment; each shape it writes is a
separate table, and the switch is a real step in the output (`WAVETABLES.md`, 8.3).

### 5.4 Converter, mixer and the offset of volume

Each channel has a 4-bit converter, linear, with a **negative** slope: digital 0 gives analog +1 and digital 15 gives
-1; a converter switched off fades to analog 0, the level of digital 7.5 (Pan Docs). The four analog outputs are added
into left and right as the routing register says, then scaled by the master volume (0 to 7, read as 1 to 8). SameBoy
writes each channel as `(15 - 2 v) * (master + 1)`.

Because a pulse alternates between 0 and its volume `v`, never between `-v` and `+v`, its average is `v` times the
duty: every step of the envelope moves the channel's offset, and the high-pass (5.5) turns that offset step into a
small soft tick on each envelope step and a thump at note-on. A model that plays the pulse as `+v` and `-v` loses
these; one that keeps the 0-to-`v` levels and the high-pass keeps them.

### 5.5 High-pass capacitor

When any channel's converter is on, a capacitor couples the output and removes its offset (Pan Docs, from blargg's
measurements):

```
// applied at 4 194 304 Hz
out = in - capacitor
capacitor = in - out * charge          // charge = 0.999958 on the first model,
                                       // 0.998943 on the pocket-sized and colour models
// at another rate: charge_rate = charge ^ (4194304 / rate)
```

The capacitor is a one-pole low-pass with pole `charge`, so the output is a first-order high-pass with corner
`(1 - charge) * 4194304 / (2 pi)`: **28.0 Hz** for 0.999958, and 706 Hz for 0.998943. At 48 kHz, 0.999958 becomes
0.996337; at 44.1 kHz, 0.996013. A 706 Hz high-pass would thin every bass note audibly, and SameBoy, the most
carefully measured of the open emulators, applies 0.999958 for every model in its accurate mode
(`highpass_rate = pow(0.999958, clock_rate / sample_rate)`); the second figure is reported and not confirmed elsewhere.
When every converter is off, the capacitor is disconnected and the output is 0. A later compatible model mixes
digitally and inverts the wave channel (Pan Docs; SameBoy `update_sample_internal`).

### 5.6 Noise channel

A 15-bit shift register, set to 0 when the channel is triggered (Pan Docs; SameBoy `lfsr_feedback`,
`shift_lfsr_with_feedback`):

```
new = NOT(bit0 XOR bit1)               // XNOR
lfsr >>= 1
bit 14 = new, and, in the short mode, bit 6 = new as well     // SameBoy's masks 0x4000 and 0x4040
output = bit 0 ? volume : 0            // SameBoy writes lfsr & 1 as the sample
clock  = 262144 / (r * 2^s) Hz, r = 0 read as 0.5; s of 14 or 15 stops the clock
```

- The long mode repeats every 32 767 shifts, the short every 127; both are half ones. XNOR from all zeros is the
  same sequence as XOR from all ones, inverted.
- The clock runs from 4.6 Hz (r = 7, s = 13) to 524 288 Hz (r = 0, s = 0), on a grid of 8 divisors times 14 shifts;
  the noise's pitch is chosen from this grid, not from the pulse's period register.
- Switching to the short mode when the low 7 bits are all ones locks the register at ones and silences the channel
  until it is retriggered.

### 5.7 Envelope, sweep and length

- **Envelope:** 4-bit volume, ticked at 64 Hz; every `pace` ticks (1 to 7) it moves one step up or down, and a pace of
  0 holds it. The initial volume and direction set to zero switch the converter off.
- **Sweep (first pulse channel):** ticked at 128 Hz; every `pace` ticks the period becomes `L +- (L >> step)`. In
  addition, a result above `0x7FF` switches the channel off, and the check runs even when the pace is 0 (Pan Docs);
  a period of 0 never changes. A later compatible model reads a pace of 0 as 8.
- **Length:** 64 steps (256 for the wave channel) at 256 Hz.

### 5.8 Rendering

The pulses and the wave are fixed cycles at a quantised frequency: tables, or steps (SameBoy's 64-tap kernel). The
noise is a held two-level sequence on the clock grid: steps at low clocks, averaging at high ones (3.4). The levels
are the channel's digital values through the negative-slope converter, the master volume, and the high-pass of 5.5,
which in a callback is one multiply-add a sample with its coefficient worked out once for the host rate.

## 6. The 1983 Home Console

### 6.1 Clocks and pitch

The CPU clock is 1 789 773 Hz on NTSC consoles (21.477272 MHz / 12) and 1 662 607 Hz on PAL ones (26.601712 MHz /
16). With an 11-bit timer value `t`:

```
pulse frequency    = f_cpu / (16 (t + 1))      54.6 Hz (t = 2047) up to 12.4 kHz (t = 8); t < 8 mutes the channel
triangle frequency = f_cpu / (32 (t + 1))      27.3 Hz up to 55.9 kHz (t = 0)
```

The worst tuning error of the nearest timer value for each note, on NTSC pulses, in cents: 0.1 at A1 and A2, 1.6 from
A3 to A5, 12.0 at A6, 14.5 at C7, 17.2 at E7, 17.9 at C8. The triangle, an octave lower for the same `t`, has the
same error one octave down.

### 6.2 Pulse channels

The duty sequences, read in order (Mesen2 holds the same sequences, its sequencer counting the other way):

| Duty | Sequence |
| --- | --- |
| 12.5 % | 0 1 0 0 0 0 0 0 |
| 25 % | 0 1 1 0 0 0 0 0 |
| 50 % | 0 1 1 1 1 0 0 0 |
| 25 % negated | 1 0 0 1 1 1 1 1 |

- Volume is a 4-bit constant or the envelope: a 4-bit decay clocked by a divider of period `V + 1` at each quarter
  frame, looping if the length counter's halt flag is set.
- **Sweep:** a divider of period `P + 1` clocked at each half frame; the change is `t >> shift`; the first pulse
  channel subtracts by ones' complement (`t - c - 1`), the second by two's complement (`t - c`), so the two channels
  sweep down to slightly different notes. The channel is muted while `t < 8` or while the target period exceeds
  `0x7FF` in the adding direction, whether or not the sweep is enabled (Mesen2 `SquareChannel.h`).

### 6.3 Triangle

A 32-step sequence of a 4-bit level, no volume control, gated by a length counter and a 7-bit linear counter:

```
15 14 13 12 11 10 9 8 7 6 5 4 3 2 1 0  0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15
```

Its exact Fourier series, as the held staircase it is, against the ideal triangle:

| Harmonic | 1 | 3 | 5 | 7 | 31 | 33 | 63 | 65 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Staircase, dB | 0 | -19.3 | -28.7 | -35.3 | -29.8 | -30.4 | -36.0 | -36.3 |
| Ideal triangle, dB | 0 | -19.1 | -28.0 | -33.8 | -59.7 | -60.7 | -72.0 | -72.5 |

The pairs at 32 k +- 1 are the steps' images, about 30 dB below the fundamental and 30 dB above where a smooth
triangle would have anything: they are the triangle's slight buzz, the chip's own, kept up to half the host rate and
no further. The energy above the 16th harmonic totals -25.4 dB. A triangle rounded to 32 four-bit steps from the ideal
shape at the sample instants, rather than this sequence, repeats two levels and misses others, and comes out with its
third harmonic at -16 dB, audibly squarer.

- When the length or linear counter reaches zero the sequencer stops where it is, so the output holds that level: a
  constant offset, and a click when the high-pass at the output (6.8) takes it away.
- At `t` of 0 or 1 the triangle runs at 56 or 28 kHz, an ultrasonic tone that programs use to park it. Game_Music_Emu
  stops the sequencer below a period of 3, and Mesen2 offers to silence it below 2, since rendered naively the
  ultrasonic tone folds into a loud alias. The chip's sound there is silence, or the average level.

### 6.4 Noise

A 15-bit register loaded with 1 at power-on (Mesen2 `NoiseChannel.h`; Game_Music_Emu's noise oscillator):

```
feedback = bit0 XOR (mode ? bit6 : bit1)
sr = (sr >> 1) | (feedback << 14)
output muted while bit 0 is 1, else the 4-bit volume
```

- The long mode repeats every 32 767 shifts. The short mode, from the power-on state, repeats every **93** shifts, a
  buzzing tone; 31 of the 32 767 possible states lie on a cycle of 31 instead, so a program that switches modes at the
  right moment can get the shorter loop.
- Timer periods in CPU clocks (Mesen2, both regions):

  | Index | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
  | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
  | NTSC | 4 | 8 | 16 | 32 | 64 | 96 | 128 | 160 | 202 | 254 | 380 | 508 | 762 | 1016 | 2034 | 4068 |
  | PAL | 4 | 8 | 14 | 30 | 60 | 88 | 118 | 148 | 188 | 236 | 354 | 472 | 708 | 944 | 1890 | 3778 |

  The register clock is `f_cpu / period`: 447 kHz down to 440 Hz on NTSC. Sixteen settings is all the noise has:
  its pitch comes from this table, and in the short mode the 93-step loop sounds a tone at `f_cpu / (period * 93)`,
  from 4.8 kHz down to 4.7 Hz.

### 6.5 Sample channel

The sample channel reads one bit at a time from memory and moves a 7-bit counter up or down by 2, clamped to 0 to
127; a program may also load the counter directly, which is how loud drum samples and the "volume" trick of 6.7 are
played. Its bit rate in CPU clocks per bit (Mesen2; Game_Music_Emu):

| Index | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NTSC | 428 | 380 | 340 | 320 | 286 | 254 | 226 | 214 | 190 | 160 | 142 | 128 | 106 | 84 | 72 | 54 |
| PAL | 398 | 354 | 316 | 298 | 276 | 236 | 210 | 198 | 176 | 148 | 132 | 118 | 98 | 78 | 66 | 50 |

On NTSC that is 4.18 kHz to 33.1 kHz. The one-bit delta encoding's slope limit and grain are the channel's sound; the
staircase it makes at its bit rate is band-limited at the host rate as steps.

### 6.6 Length counter, frame counter and envelope clock

The length counter's table, indexed by the 5-bit value written (Mesen2 `ApuLengthCounter.h`):

```
10 254 20 2 40 4 80 6 160 8 60 10 14 12 26 14 12 16 24 18 48 20 96 22 192 24 72 26 16 28 32 30
```

The frame counter clocks envelopes and the triangle's linear counter at each quarter frame and the length counters
and sweeps at each half. Its steps, in CPU clocks from the start (Mesen2 `ApuFrameCounter.h`): four-step mode 7457,
14913, 22371, 29829 on NTSC and 8313, 16627, 24939, 33253 on PAL; five-step mode 7457, 14913, 22371, 29829, 37281 on
NTSC and 8313, 16627, 24939, 33253, 41565 on PAL. The quarter frame is about 240 Hz on NTSC and 200 Hz on PAL, the
envelope's clock.

### 6.7 Mixer

The channels' converters share resistor networks, so the output is not their sum (the developer community's wiki,
after blargg's reference notes; Mesen2's sound mixer):

```
pulse_out = 95.88 / (8128 / (pulse1 + pulse2) + 100)                            // 0 when both are 0
tnd_out   = 159.79 / (1 / (triangle / 8227 + noise / 12241 + dmc / 22638) + 100)  // 0 when all are 0
output    = pulse_out + tnd_out                                                  // 0.0 to about 1.0
```

with pulses, triangle and noise from 0 to 15 and the sample channel from 0 to 127. Mesen2 writes the second group in
units of the sample channel, `dmc + 2.7516713261 * triangle + 1.8493587125 * noise` over 22638 (the ratios 22638 /
8227 and 22638 / 12241).

**Table forms.** A 31-entry and a 203-entry table, the second indexed by a weighted sum that approximates the second
group within 4 %, with numerators adjusted to keep the full range:

```
pulse_table[n] = 95.52 / (8128 / n + 100)        n = pulse1 + pulse2, 0 to 30
tnd_table[n]   = 163.67 / (24329 / n + 100)      n = 3 triangle + 2 noise + dmc, 0 to 202
```

**A linear form**, for the wave channels' small part of the curve: `0.00752 (pulse1 + pulse2)` and `0.00851 triangle +
0.00494 noise + 0.00335 dmc`. Game_Music_Emu's linear mode uses gains of 0.1128 / 15 per pulse, 0.12765 / 15 for the
triangle, 0.0741 / 15 for the noise and 0.42545 / 127 for the sample channel.

What the curve does, worked out from the exact formulas:

- One pulse at 15 gives 0.1494; both at 15 give 0.2585, 1.26 dB less than twice one. Two pulses compress each other
  slightly, and play intermodulation products of their two pitches, quietly.
- The triangle alone swings 0.2464 from 0 to 15. With the sample counter held at 64 it swings 0.1550, 4.0 dB less;
  at 127, 0.1071, 7.2 dB less. Holding the sample channel's level high turns the triangle and noise down, a trick
  programs used as a volume control.

In a single-channel model, the curve for that channel alone is a fixed 16-entry mapping of its levels (or 128 for the
sample channel), folded into the levels before they are band-limited (3.2), so it costs nothing per sample. Two
channels of one group share the curve and must be mixed by it, as levels, before band-limiting.

### 6.8 Output filters

On the front-loading export model, the circuit after the converters amounts to a first-order high-pass at 90 Hz and a
first-order low-pass at 14 kHz, with a second-order low-pass far above hearing that emulation can omit (the
developer community's wiki, from blargg's measurements and an analysis matching analog parts to them). Older editions
of the same reference, and several emulators, add a second first-order high-pass at 440 Hz. The original domestic
model specifies only a first-order high-pass at 37 Hz before its RF modulator. Each is a matched one-pole at the host
rate, `a = exp(-2 pi f_c / f_s)`, worked out once.

## 7. Building Chip Tables Off the Callback

- **Once, when the instrument is compiled.** Every table here is a function of the chip's revision and the host rate:
  the converter's 4096 levels, the combined waveforms' 4096 entries, the mip levels of each cycle, the noise run, the
  step kernel, the filter's op-amp tables. None depends on the note. They are built where allocation is allowed,
  shared by reference between voices and instruments (an `Arc` keyed by what they were built from), and never rebuilt
  in the callback.
- **Integer chip state, float output.** The registers, accumulators and counters are integers of their real widths
  (`u32` masked to 23, 15 or 24 bits), stepped exactly; only the converter's output is a float. The chip's arithmetic
  is then the chip's, with no drift.
- **Normalisation per waveform, by the chip's own scale.** A chip's waveforms share one converter, so their relative
  levels are the chip's: a 12.5 % pulse at volume 15 is quieter than a 50 % one, a 25 % output level on the wave
  channel is a quarter. One gain per chip (its converter's full scale) keeps that; one gain per waveform, taken from
  the level holding every harmonic, at least keeps each waveform even across the keyboard; a gain per mip level does
  neither (3.1).
- **Offsets.** Each cycle's average is taken out before band-limiting (`X[0] = 0`), and where a chip's offset steps
  are part of its sound (5.4, 6.3), the high-pass that removes them is modelled instead, after the steps.
- **Memory.** A 2048-sample table of 32-bit floats is 8 KiB; twelve octave levels are 96 KiB a cycle, two an octave
  192 KiB. Shared by reference, the chips' cycles (four duties, a few shapes of wave memory, the 32-step triangle, two
  revisions' saw, triangle and four combinations) stay within a few megabytes.
- **Seeds.** Each register starts where the chip's does: `0x7FFFFF` for the 1982 chip's noise, 0 for the handheld's,
  1 for the 1983 console's. A run tabulated from that start and stepped by an index seeded from the note keeps every
  render identical.

## 8. Measuring a Chip Model

Each of the following measures one property against a number in this chapter:

- **Level across the keyboard:** the fundamental's level of each cycle played at a note in every mip level, within a
  tenth of a decibel of the full-band level.
- **No folded components:** the spectrum of a high note (a 4 kHz narrow pulse, a 3 kHz 32-step wave, the triangle at
  2 kHz) holds no component more than 90 dB below the fundamental at a frequency that is not a harmonic.
- **Images kept:** the 32-step triangle's 31st and 33rd harmonics within half a decibel of -29.8 and -30.4 dB at a
  note low enough for them to lie under half the host rate.
- **Tuning:** each note's measured frequency equals the register formula's for the nearest register value
  (`131072 / (2048 - x)`, `65536 / (2048 - x)`, `f_cpu / (16 (t + 1))`), and notes below a channel's lowest pitch are
  reported or refused rather than silently clamped.
- **Registers:** each noise register's run has the period of its chip (8 388 607; 32 767 and 127; 32 767 and 93),
  and its first values match those an emulator gives from the same start.
- **Converter:** the 1982 chip's first-revision converter falls at `0x7FF` to `0x800` by 129 parts in 4095; the later
  revision's is linear to a part in a million.
- **Clock of the 1982 chip's noise:** 16 register shifts per cycle of the voice's tone.
- **Envelope:** the 1982 chip's attack at setting 0 reaching 255 in `255 * 9` clocks; decay times three times the
  attack's; the sustain levels `0x11 * s`.
- **Mixer:** the formulas' values at the points in 6.7.
- **High-pass:** the handheld's output corner at 28 Hz, the console's at 90 Hz.

## 9. Hazards at a Glance

| Symptom | Cause | Remedy |
| --- | --- | --- |
| High notes 2 to 11 dB louder, a level step per octave | mip levels scaled each to its own peak | one gain per waveform |
| Notes dull just above each octave boundary | one mip level an octave, built for its top | two levels an octave, or crossfaded |
| Rough inharmonic tones on high notes | staircases or pulses not band-limited | tables or band-limited steps |
| Noise that loops audibly, or changes colour with pitch | a short tabulated run read by a sample-and-hold | a long run, averaging per sample, or steps |
| Noise two octaves off the chip's | the register clocked at a multiple other than 16 per tone cycle | 16 per cycle (the 1982 chip); the noise clock grid (handheld); the period table (1983 console) |
| Bass notes all at one pitch | the period register clamped at its end | the channel's true lowest pitch, and the wave channel's octave lower range |
| A thin, dry chip sound | offsets removed and no high-pass after the steps | levels as the chip makes them, then the chip's high-pass |
| A loud whine where the console's triangle should be silent | the ultrasonic triangle aliased | silence it, or hold its average, below a period of 2 or 3 |
| Pulses louder together than on the chip, the triangle unaffected by the sample channel | a linear mixer | the mixer's formulas or tables |
| A test of the converter that passes for the wrong reason | an affine leakage term dominating the lowest bits | test the ladder's weights without leakage |
| An emulator's tables used under an incompatible licence | GPL-2.0-only source (Gambatte) | the same numbers from a compatible source (SameBoy, Pan Docs, mGBA) |

## 10. References

Open code read for this chapter:

| Project | Licence | Files |
| --- | --- | --- |
| reSID (`daglem/reSID`), Dag Lem | GPL-2.0-or-later | `src/dac.h`, `src/wave.h`, `src/wave.cc`, `src/envelope.h`, `src/envelope.cc`, `src/filter.h`, `src/filter.cc`, `src/extfilt.h`, `src/voice.cc`, `src/samp2src.pl`, `src/NEWS` |
| reSID 1.0 as kept by libsidplayfp (`libsidplayfp/resid`) | GPL-2.0-or-later | `filter.h`, and the header of the later revision's filter |
| libresidfp (`libsidplayfp/libresidfp`), Leandro Nini, Antti Lankila | GPL-2.0-or-later | `src/WaveformCalculator.cpp`, `src/WaveformGenerator.cpp` and `.h`, `src/Dac.cpp`, `src/SID.cpp`, `src/EnvelopeGenerator.cpp`, `src/FilterModelConfig` files of both revisions, `src/ExternalFilter.cpp` |
| combined-waveforms (`libsidplayfp/combined-waveforms`) | GPL-2.0-or-later | `README.md` (the waveform selector and noise write-back notes), `src/combined.cpp` |
| SameBoy (`LIJI32/SameBoy`), Lior Halphon | MIT (Expat) | `Core/apu.c` (duties, noise, high-pass, band-limited steps), `Core/apu.h`, and the core's power-on code (wave memory at power-on) |
| Game_Music_Emu (`libgme/game-music-emu`), Shay Green | LGPL-2.1-or-later | `gme/Blip_Buffer.cpp` and `.h`, and its oscillator and sound-unit modules for both consoles |
| Mesen2 (`SourMesen/Mesen2`) | GPL-3.0 | the APU channel sources `SquareChannel.h`, `TriangleChannel.h`, `NoiseChannel.h`, `DeltaModulationChannel.cpp`, `ApuLengthCounter.h`, `ApuFrameCounter.h`, and its sound mixer |
| Nestopia UE, FCEUX | GPL-2.0-or-later | licence headers checked; same tables as Mesen2 |
| mGBA | MPL-2.0 | licence header checked |
| Gambatte | GPL-2.0-only | licence header checked; not read further |

Documents:

- Pan Docs (`gbdev/pandocs`, CC0-1.0): `src/Audio.md`, `src/Audio_Registers.md`, `src/Audio_details.md` (which
  includes blargg's measured high-pass and quirks), `src/Power_Up_Sequence.md`.
- The 1983 console's developer community wiki, its pages on the APU's mixer, pulse, triangle, noise, sample channel,
  length counter and frame counter, and blargg's reference notes on that unit, which it cites.
- Lem, D. The reSID release notes for version 1.0, on die-photograph analysis of the noise register's topology, the
  converters and the filter.
- Nini, L., and Mueller, D. The internals documentation and transistor-level schematics of the 1982 chip
  (`libsidplayfp/SID_schematics`), and the SID-Article (CC0-1.0).
- Green, S. Notes on band-limited sound synthesis, the basis of Blip_Buffer and of SameBoy's synthesiser.
