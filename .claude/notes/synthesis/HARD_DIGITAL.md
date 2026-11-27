# Hard Digital Synthesis: Noise, Bits, Glitch and Destruction

A chapter on the sounds that digital hardware and code make when they are harsh on purpose: shift-register noise,
clocked and pitched noise, one-line formula music, oscillators built from the bits of counters, cross-modulated
digital oscillators, phase distortion and the errors of phase accumulators and small tables, sample-and-hold and
divider chains, chaotic maps and automata played as audio, Walsh-function and fractal synthesis, the glitch techniques
of buffers and converters, circuit-bent toys written as algorithms, the harsh-noise wall, and the destroyer
distortions that end in folding, wrapping, masking, rectifying and collapsing the sample rate. Each section gives what
a musician hears, the exact algorithm with its constants, the open implementations that realise it with their
licences, the controls that make it playable, its cost per sample in a real-time callback that allocates nothing and
takes no lock, and its hazards.

Related chapters: `ENGINES_RESEARCH.md` (sections 10 to 12: the chip voices, bytebeat in brief, noise and glitch
voices), `QUALITY_RESEARCH.md` (section 1 on band-limited steps, section 5 on antiderivative anti-aliasing, section 6
on drive and bitcrushing, section 12 on numerical hygiene), `EFFECTS_RESEARCH.md` (section 11, stutter and beat
repeat), `MODULATORS_RESEARCH.md` (chaotic systems at control rate, the random looping shift register) and
`BITCRUSHING.md` (quantisation, dither, rate reduction and converter colour in depth; this chapter refers there rather
than repeating it).

Notation. `fs` is the output sample rate. Integer operators are written as in C and Rust: `>>` and `<<` shifts, `&`
and, `|` or, `^` exclusive or, `~` not, `%` remainder. `popcount(x)` counts the one bits of `x`, `parity(x)` is
`popcount(x) & 1`, `ctz(x)` counts trailing zero bits. A "word" is an unsigned integer of stated width; "u8", "u16",
"u32" name widths.

## 1. What Makes a Sound Hard and Digital

### 1.1 The ingredients

Harsh digital sound comes from a handful of properties of machines, each of which an analog circuit lacks:

- **Discrete amplitude.** A word of a few bits can hold only a few levels; small signals become staircases, and a
  signal below one step vanishes (`BITCRUSHING.md`).
- **Discrete time without a filter.** A value held for several output samples, or a rate that does not divide the
  output rate, puts images and aliases far from the harmonic series.
- **Wraparound.** Integer arithmetic does not clip; it wraps modulo `2^n`, so an overload becomes a jump from the top
  of the range to the bottom: a sawtooth-like tear rather than a flattened top.
- **Bit logic.** And, or, exclusive or and shifts act on the binary digits of numbers, not on their sizes; the result
  is self-similar, rhythmic and full of sum-and-difference products that no multiplication would make.
- **Deterministic pseudo-randomness.** Shift registers and congruential generators repeat exactly; a short one is a
  tone, a long one is noise, and the change between them is a control.
- **Clocks and dividers.** Pitches come from integer divisions of a fixed clock, so they are slightly and
  characteristically out of tune, more so as they rise.

What the ear calls harsh has measurable correlates: strong energy between about 2 and 5 kHz, where the ear canal
resonates and hearing is most sensitive; inharmonic partials (aliases) beating against harmonic ones; amplitude
fluctuation between about 20 and 150 Hz, which is heard as roughness; and a low crest factor (peak to RMS ratio), so
that a sound at a given peak level is much louder than music at the same peak.

### 1.2 Where aliasing belongs

The project's rule is that nothing aliases by accident and aliasing stays only where it is the instrument's own sound.
In a hard digital engine the line is drawn by asking where each part of the signal is defined:

| Zone | Example | Aliasing is | Treatment |
| --- | --- | --- | --- |
| Defined in discrete time at an internal rate | a bytebeat formula at 8 kHz, a shift register stepped by a clock, a map iterated per tick | the sound itself: the sequence of numbers is the instrument | none inside the zone |
| Conversion from the internal rate to `fs` | holding each internal value for `fs / f_internal` output samples | a choice: the hold's images are bright and harsh, a period converter's reconstruction filter would have removed them | three choices: plain hold, hold with band-limited steps, hold followed by a reconstruction low-pass |
| Continuous-time shaping | drive, folding, wrapping, rectifying a smooth signal | accidental: the curve makes harmonics above `fs / 2` that fold back | oversampling, antiderivative anti-aliasing, or both |

So a destroyer distortion anti-aliases its folding and wrapping, then collapses the sample rate without a filter,
because the collapse is its sound; and a shift register clocked at a pitch places each of its steps at the exact
fractional time with a band-limited step, because the register's sequence is the sound but the jitter of rounding its
steps to whole output samples is not.

### 1.3 Band-limited steps for piecewise-constant sources

Almost every source in this chapter is piecewise constant: it holds a level, then jumps. The general method of
`QUALITY_RESEARCH.md`, section 1.2, applies: at a jump of height `h` at fractional time `t` (0 to 1) after the previous
output sample, add `h` times the residual of a band-limited step to the samples around it. The two-sample polynomial
form used by `pichenettes/eurorack` (MIT), `stmlib/dsp/polyblep.h`, is:

```
this_sample  += h * (0.5 * t^2)            with t = phase_since_jump / increment, the jump's place in this sample
next_sample  += h * (-0.5 * (1 - t)^2)
```

(`ThisBlepSample(t) = 0.5 t^2`, `NextBlepSample(t) = -0.5 (1 - t)^2`, applied with the one-sample delay their code
uses.) Shay Green's `Blip_Buffer`, in Game_Music_Emu (LGPL-2.1-or-later), is the long-kernel alternative: each change
of a chip's output is added to an output buffer as a windowed-sinc step from a table of 32 phases, at a cost per
transition, not per sample. When a source makes more than about one transition per output sample, the per-transition
cost exceeds a per-sample method, and the source is better run at an oversampled rate and decimated (section 2.8).

## 2. Linear-Feedback Shift Registers

### 2.1 Principle and the two forms

A linear-feedback shift register (LFSR) holds `n` bits. At each clock it shifts by one place and feeds back, into the
vacated end, the exclusive or of chosen bits, the taps. Its state sequence is periodic; with taps that form a
primitive polynomial over GF(2), the period is `P = 2^n - 1`, every non-zero state visited once: a maximal-length
sequence or m-sequence. Its output bit is a pseudo-random binary sequence whose run lengths, balance and correlation
are those of a fair coin over one period.

Two equivalent forms:

```
Fibonacci (external xor), taps at bits a and b, shifting right, feeding the top bit:
    feedback = ((s >> a) ^ (s >> b)) & 1
    s = (s >> 1) | (feedback << (n - 1))
    out = s & 1

Galois (internal xor), branch-free, mask holding the polynomial's taps:
    lsb = s & 1
    s = (s >> 1) ^ (0u32.wrapping_sub(lsb) & mask)      // the mask is xor'd in only when lsb is 1
    out = lsb
```

The Galois form costs a shift, an and, a negation and an exclusive or: four integer operations a clock, no branch. The
Fibonacci form is how most chips are wired and is needed to reproduce their exact sequences and their output words
read from several bits (section 2.6). For more than two taps, `parity(s & taps)` gives the feedback in one popcount.

A register of all zeros never leaves zero (all ones, for a register that feeds back the exclusive nor). A seed of zero,
or a glitch that clears the register, silences it for good: the code checks for the stuck state and reseeds, as the
`VCVRack/Befaco` repository's `src/noise-plethora/plugins/P_LFSRNoise.hpp` (GPL-3.0-or-later) does with
`if (lfsr == 0) lfsr = 0xACE1`.

### 2.2 Maximal-length taps

Taps are given as the exponents of the feedback polynomial (Fibonacci form, bit numbers counted from 1 at the output
end). These are standard tables from the coding literature (Golomb, *Shift Register Sequences*, 1967; Peterson and
Weldon, *Error-Correcting Codes*, 1972):

| n | Period | Taps | n | Period | Taps |
| --- | --- | --- | --- | --- | --- |
| 3 | 7 | 3, 2 | 14 | 16383 | 14, 5, 3, 1 |
| 4 | 15 | 4, 3 | 15 | 32767 | 15, 14 |
| 5 | 31 | 5, 3 | 16 | 65535 | 16, 15, 13, 4 |
| 6 | 63 | 6, 5 | 17 | 131071 | 17, 14 |
| 7 | 127 | 7, 6 | 18 | 262143 | 18, 11 |
| 8 | 255 | 8, 6, 5, 4 | 19 | 524287 | 19, 6, 2, 1 |
| 9 | 511 | 9, 5 | 20 | 1048575 | 20, 17 |
| 10 | 1023 | 10, 7 | 23 | 8388607 | 23, 18 |
| 11 | 2047 | 11, 9 | 25 | 33554431 | 25, 22 |
| 12 | 4095 | 12, 6, 4, 1 | 31 | 2147483647 | 31, 28 |
| 13 | 8191 | 13, 4, 3, 1 | 32 | 4294967295 | 32, 22, 2, 1 |

As Galois masks for a right-shifting register (bit `k - 1` set for each tap `k`): 16 bits with taps 16, 14, 13, 11
is `0xB400`; 16, 15, 13, 4 is `0xD008`. The eight-entry table of `P_LFSRNoise.hpp` mixes maximal and non-maximal
16-bit masks (`0x002D, 0x0039, 0xD008, 0xB400, 0x6000, 0xD295, 0xB002, 0xE100`) so that one knob walks between long
hiss and short, tonal loops.

### 2.3 The spectrum of a clocked m-sequence

An m-sequence of period `P` clocked at `fc`, its bit mapped to ±1 and held between clocks (non-return-to-zero), has a
line spectrum:

```
lines at f_k = k * fc / P
power at k = 0:      1 / P^2                       (almost no DC once mapped to ±1)
power at k != 0:     ((P + 1) / P^2) * sinc^2(k / P)    with sinc(x) = sin(pi x) / (pi x)
```

All lines below `fc` are nearly equal (flat, white), the envelope falls as `sinc^2(f / fc)` with nulls at multiples of
`fc` and is 3 dB down at about `0.44 fc`. Two consequences shape every noise voice:

- **Brightness is the clock.** Moving `fc` from 100 Hz to 100 kHz moves the noise from a rumble of separate clicks to
  hiss; above the output rate, the register is stepped several times a sample.
- **Pitch is the period.** The lines are `fc / P` apart. For a long register they are far closer than hearing
  resolves, and the sound is noise; for a short one (`P` of 7 to 127) they are audible harmonics of a fundamental
  `fc / P`, a buzzy, metallic, reedy tone whose harmonics are all equal up to the sinc envelope.

### 2.4 Short and non-maximal loops: the metallic tones

Chips made their "metallic" or "periodic" noise in two ways:

- **A short tap set.** A 15-bit register with feedback from bits 0 and 6 instead of 0 and 1 is not maximal: its states
  fall into several disjoint cycles, of 93 and of 31 steps among others, and which one plays depends on the state the
  register held when the mode changed. The 1983 home console's noise channel (`ENGINES_RESEARCH.md`, 10.1) has
  exactly this mode, and its tone is famously different from one switch to the next for this reason. A model holds
  the seed per note, so that the same note always lands in the same cycle.
- **A shortened register.** The handheld console writes the feedback into bit 6 as well as bit 14, so the register
  behaves as a 7-bit one of period 127.
- **One tap.** The 1980 four-channel sound generator used in home computers and consoles has a "periodic noise" mode
  in which the output bit alone is fed back: the register rotates, and a single one in 15 or 16 places makes a narrow
  pulse wave at `fc / 15` or `fc / 16`, a buzz a little below the clock's sixteenth.

Musically, the short loops are the bridge between noise and tone: a note-tracked loop of period 31 or 93 sounds like a
harsh, hollow square with an organ-like spread of equal harmonics, and stepping the tap set while a note holds jumps
between tone and noise without a change of pitch.

### 2.5 The chips' registers

| Machine (described generically) | Register | Feedback | Clock | Output |
| --- | --- | --- | --- | --- |
| 1977 home video console, two channels | 4-, 5- and 9-bit polynomial counters | maximal | about 31.4 kHz divided by a 5-bit value | the counters gate a divided clock (section 2.7) |
| 1979 8-bit home computer's four-channel chip | 4-, 5-, 9- and 17-bit counters | maximal | 1.79 MHz, run continuously | sampled by each channel's 8-bit divider (section 2.7) |
| 1978 general-purpose three-voice generator | 17 bits | bits 0 and 3 | master clock / 16, divided by a 5-bit period | one bit, combined with the tone by logic (section 5.4) |
| 1980 four-channel generator | 15 or 16 bits by variant | bits 0 and 1 (15-bit); bits 2 and 3 or 0 and 3 (16-bit) | master clock / 16, divided by 512, 1024, 2048 or the third tone's period | one bit; periodic mode feeds back the output bit |
| 1982 home computer's chip | 23 bits | bits 17 and 22 | the voice's accumulator bit 19 | 8 bits read from bits 22, 20, 16, 13, 11, 7, 4, 2 |
| 1983 home console | 15 bits | bits 0 and 1 (long); 0 and 6 (short) | CPU clock 1.79 MHz divided by one of 16 periods: 4, 8, 16, 32, 64, 96, 128, 160, 202, 254, 380, 508, 762, 1016, 2034, 4068 | one bit; the channel is silent while bit 0 is 1 |
| 1989 handheld console | 15 bits, or 7 | bits 0 and 1 | 524288 Hz / r / 2^(s + 1), with r = 0 read as 0.5 | one bit |

Open references: MAME's sound devices (`src/devices/sound/`, each file's licence in its header: the 1979 chip's, the
1978 generator's and the 1980 generator's BSD-3-Clause, the 1977 console's GPL-2.0-or-later); Game_Music_Emu
(LGPL-2.1-or-later) for the 1983 console and the handheld; reSID (GPL-2.0-or-later) for the 1982 chip. The 1978
generator's register, from MAME: `rng = (rng >> 1) | (((rng & 1) ^ ((rng >> 3) & 1)) << 16)`.

### 2.6 Words from several bits, and the converter

A register read one bit at a time gives a two-level signal. Reading several bits at once gives a multi-level noise
whose spectrum is still flat but whose waveform has more levels, and whose successive values are correlated, because
consecutive states are shifts of each other: reading the top 4 bits of a 16-bit register (`P_LFSRNoise.hpp`:
`quantized = lfsr >> 12; out = quantized / 7.5 - 1`) gives 16 levels in which each new value is half the last plus a
new top bit, a gently low-passed, grainy noise. The 1982 chip's eight scattered bits decorrelate the word; through its
uneven converter (`docs/synths/engines/SID.md`) the levels are a little unequal, which adds a faint, fixed colour.

### 2.7 Polynomial counters sampled by dividers

The 1977 console and the 1979 computer's chip make their famous buzzing, growling "engine" tones by letting short
polynomial counters run at one rate and sampling them at another. In the 1979 chip (MAME's implementation, BSD-3-
Clause) the 4-, 5-, 9- and 17-bit counters step at the master clock; each channel's divider, when it underflows,
updates the channel's output bit:

```
if (not_poly5_gate) or (poly5_bit == 1):
    if pure:          out ^= 1                      // a plain divided square
    elif use_poly4:   out = poly4_bit
    else:             out = poly17_bit (or poly9_bit)
```

Sampling a sequence of period `P` every `D` clocks visits it in steps of `D mod P`. When `gcd(D, P) = 1` every state
is visited and the result is again a (scrambled) sequence of period `P`, heard as a tone at `f_div / P`; when they share
a factor, a shorter sub-cycle plays. As the divider moves through its 256 values the timbre jumps irregularly between
pure tones, buzzes of 15 and 31 steps, and noises: the "distortion" settings of such chips are this. The 5-bit counter's
gate, letting a toggle through only when its bit is 1, gives the irregular 31-step rhythm inside a tone that is the
signature of these machines' lead and engine sounds.

The 1977 console's four-bit control register selects one of sixteen combinations (from MAME's GPL-2.0-or-later
implementation, after Ron Fries and Dan Boris): 0 and 11 hold the output high; 1 the 4-bit counter; 2 a divide by 31
gating the 4-bit counter; 3 the 5-bit counter gating the 4-bit; 4 and 5 a pure divide by 2; 6 and 10 a divide by 31,
pure or gating the 5-bit counter; 7 the 5-bit counter into a divide by 2; 8 the 9-bit counter (its white noise); 9 the
5-bit counter; 12 and 13 a divide by 6; 14 a divide by 93; 15 the 5-bit counter into a divide by 6. Its 5-bit frequency
register divides a clock of about 31.4 kHz by 1 to 32, so a channel offers only 32 pitches per mode, which is the cause
of that console's out-of-tune melodies: a model rounds each note to the nearest of the 32 and lets the error be heard.

### 2.8 Rendering a register at any clock

- **Clock below `fs`.** Keep a phase in clock periods; when it passes 1, step the register and add the change in
  output level as a band-limited step at its fractional time (section 1.3). Per sample: a phase add and compare; per
  step: the register step and the step residual. `pichenettes/eurorack`, `plaits/dsp/noise/clocked_noise.h` (MIT),
  does exactly this for held random values.
- **Clock above `fs`.** Step the register `k = floor(phase)` times in the sample and output the mean of the levels it
  held, weighted by time: a box filter, which is a crude band-limit (its first null is at `fs`) but costs only the
  steps. For clocks of hundreds of kHz (the chips' raw rates) this is tens of steps a sample; a long-kernel step buffer
  (`Blip_Buffer`) is exact and costs per transition. For a register far faster than `fs` with a flat spectrum, the
  output is simply white noise and can be replaced by a fast generator, as `plaits/dsp/noise/clocked_noise.h`
  crossfades to raw noise once the clock exceeds a quarter of the sample rate (`raw_amount = clamp(4 (f - 0.25), 0, 1)`).
- **Jump-ahead.** Stepping an LFSR `k` times is multiplication by the `k`-th power of its companion matrix over GF(2);
  precomputed powers let a register skip whole blocks, for a seek or a reset to a known place, without stepping.
- **Precomputing.** A register of 15 to 17 bits has a period of at most 131071 steps; its whole output (or its words)
  can be tabulated when the instrument is built and read by an index, which is what the project's SID noise already
  does (`docs/synths/engines/SID.md`).

### 2.9 Controls, cost and hazards

- **Controls.** Clock (as a pitch, tracking the note: `fc = P * f_note` makes the loop's fundamental the note), Length
  or Taps (a stepped list from long to short loops), Bits read (1 to 8), Seed (which cycle a non-maximal tap set plays),
  and a Noise-to-tone morph that steps through tap sets ordered by period.
- **Cost.** Four integer operations a step; with a step residual about 10 operations a transition.
- **Hazards.** The stuck all-zero state; DC from a 0-and-1 output (map to ±1, or high-pass); seeds that differ between
  playback and export (seed from the instrument and the note); the loud, flat spectrum of a fast register (full-scale
  white noise is about 10 dB louder in perceived loudness than a sine at the same peak, so the level is set by RMS).

## 3. Clocked, Pitched and Sample-and-Hold Noise

### 3.1 Held random values

A new random value every clock period, held between: "sample-and-hold noise" or "clocked noise". Its spectrum is the
`sinc^2(f / fc)` envelope of section 2.3 but continuous (no lines), since the values do not repeat: a bright, burbling,
"computer" noise at low clocks and hiss at high ones. `plaits/dsp/noise/clocked_noise.h` (MIT) renders it at any clock
with a phase, a band-limited step at each new value, an optional sync that restarts the clock, and the crossfade to raw
noise above `fs / 4` described in 2.8.

### 3.2 Looping random sequences: pitched noise

A random sequence that restarts from the same seed every `L` clocks repeats, and so has a pitch `fc / L` with a timbre
fixed by the seed. `pichenettes/eurorack`, `braids/digital_oscillator.cc` (MIT), `RenderClockedNoise`, does this with a
linear congruential generator:

```
on each clock:
    rng = rng * 1664525 + 1013904223            // u32, wrapping
    cycle_phase += cycle_increment              // a second, slower phase sets the loop's length
    if cycle_phase wrapped: rng = seed           // restart the sequence: a repeating pattern, hence a pitch
    sample = (rng as u16) rounded down to one of num_steps levels, plus half a level
```

The loop length runs from a few clocks (a tone with a random wave shape, re-drawn each note from a new seed) to
thousands (noise with a faint periodicity, a "grain" that the ear locks onto). A second control quantises the values
to 2 to 64 levels, from a random square wave to a random staircase. Clock tracking the note makes it an oscillator
whose every note has its own random timbre: re-seeding per note is the musical "strike".

### 3.3 Filtered noise voices

`pichenettes/eurorack`, `plaits/dsp/engine/noise_engine.cc` (MIT), is a model of two clocked noises at frequencies in
a ratio `f1 / f0` (the second clock `clock_f * f1 / f0`), the first through a state-variable filter morphing from
low-pass to high-pass, and both through band-passes at `f0` and `f1`:

```
f0 = note frequency, f1 = f0 shifted by -24 to +24 semitones by a control, clock from note -24 to note 128
q  = 0.5 * 2^(morph * 120 / 12)                 // resonance up to self-ringing
gain = 1 / sqrt((0.5 + q) * 40 * f0)            // f0 normalised to the sample rate: keeps level steady as q and f0 move
```

The gain law is worth copying: a resonant band-pass on white noise passes power in proportion to its bandwidth, so the
level falls as `q` rises and as the centre falls; dividing by the square root of the product keeps loudness roughly
constant across the whole range. Two band-passes on two noise clocks make the whistling, wind-like and metallic
"twin peaks" textures that are much of the noise-synth vocabulary.

### 3.4 Dust and particles

- **Dust.** Impulses at random times, a mean `density` per second: each sample, with a uniform `u`, output a value if
  `u < density / fs`. SuperCollider's `Dust` and `Dust2` (`server/plugins/NoiseUGens.cpp`, GPL-2.0-or-later) scale the
  impulse by `u` itself (`u * 2 / thresh - 1` for the bipolar form), so impulse heights are random too.
- **Particles.** `pichenettes/eurorack`, `plaits/dsp/noise/particle.h` and `plaits/dsp/engine/particle_engine.cc`
  (MIT): six dust sources; each impulse retunes its own band-pass filter to a random pitch within `spread` semitones
  of the note, so each grain rings at its own pitch (rain on metal, ice, crackling fire):

```
density = (2^((timbre^2 * 72) / 12) * 261.6 / fs)^2 / 6     // from a few to thousands of impulses a second
spread  = 48 * harmonics^2 semitones                         // all at the note, to four octaves of scatter
q       = 0.5 + (2^((morph - 0.5) * 120 / 12))^2  for morph above one half, else 0.5
per impulse: f = min(2^(spread * u / 12) * f0, 0.25);  pre_gain = 0.5 / sqrt(q * f * sqrt(density))
```

  Below `morph = 0.5` the engine sends the summed impulses through an all-pass diffuser instead of sharp resonances.
  The pre-gain law again holds loudness steady across density and resonance.

### 3.5 Sample-and-hold of an oscillator: aliasing as a melody

Sampling a periodic signal of frequency `f` at a hold rate `fh` and holding produces, besides images, an alias at
`|f - k fh|` for the nearest integer `k`. When `fh` is close to a multiple of `f`, the alias is a slow tone, and moving
`fh` or `f` sweeps it up and down, often against the direction of the sweep: the "stroboscopic" melodies of a swept
rate reducer. A rate reducer played as an instrument (its rate tracking the note, the input a fixed oscillator) is this
effect. Aliasing here is the sound; the hold's own timing jitter is not, and is removed by placing each hold at its
exact fractional time (`QUALITY_RESEARCH.md`, 6.2; `plaits/dsp/fx/sample_rate_reducer.h`, MIT).

### 3.6 Clock division chains and integer pitch

- **Binary dividers.** A counter clocked at `fc` gives, at its bit `k`, a square wave at `fc / 2^(k + 1)`: the octave
  divider of organs and of sub-oscillators. Reading bits from a counter clocked at the note gives a stack of
  sub-octaves for free.
- **Divide by N.** A counter that reloads after `N` clocks and toggles an output divides by `2N`; dividers by 3, 5 and 7
  give the undertone series (a fifth below the octave, and so on), the material of subharmonic synthesis. Chains of
  dividers on one clock, combined by exclusive or or and, make rhythmic patterns that repeat after the least common
  multiple of their periods.
- **A master clock divided.** Divide-down organs took every note from one clock near 2 MHz divided by twelve integers;
  the top-octave divisors are 239 for the top C, then 253, 268, 284, 301, 319, 338, 358, 379, 402, 426 and 451 for the
  notes below it, each within a few cents of equal temperament, every octave below made by binary division.
- **Period quantisation.** A chip plays `f = C / (k N)` with an integer `N`, so a note's error is up to half a step of
  `N`: about `866 / N` cents. Low notes (large `N`) are nearly exact; high notes are audibly sharp or flat, which is part
  of the chip sound. A model computes `N = round(C / (k f))` and plays `C / (k N)`, with the clock `C` as a control.

### 3.7 Pink noise from bits

The Voss-McCartney generator makes approximately 1/f noise from `R` held random rows, updating on sample `n` the row
`ctz(n)` (row 0 every other sample, row 1 every fourth, and so on), and outputting their sum plus a white value. The
trailing-zero count is one instruction. The spectrum falls about 3 dB an octave over `R` octaves, with a gentle ripple.
Faust's `noises.lib` (LGPL-2.1-or-later with an exception) has the filter form `pink_noise` (a fourth-order IIR on white
noise) and this one, `pink_noise_vm(N)`.

## 4. Bytebeat and One-Line Formula Music

### 4.1 Principle

A counter `t` advances by one per sample at a fixed rate, classically 8000 Hz, and a short expression of `t` is
evaluated each sample; its low 8 bits, read as an unsigned byte, are the output:

```
out = ((expression(t) as i32) & 255) as f32 / 128.0 - 1.0
```

The form was found and popularised by Ville-Matias Heikkilä (viznut) in 2011 ("Algorithmic symphonies from one line of
code", and the paper "Discovering novel computer music techniques by exploring the space of short computer programs",
arXiv:1112.1368). Because 256 values of `t` make one cycle of the byte, the bare formula `t` is a sawtooth at
`8000 / 256 = 31.25 Hz`; `t * 2` is an octave higher; `t * 3` a fifth above that.

### 4.2 Canonical formulas

Short formulas are ideas more than works; they are given with their authors as credited in the 2011 discussion:

| Formula | Credited to | What it does |
| --- | --- | --- |
| `t*(((t>>12)\|(t>>8))&(63&(t>>4)))` | viznut | the first: a melody whose multiplier is built from slower bits of `t` |
| `t&t>>8` | viznut | an aural "munching squares", a self-similar rhythm |
| `(t*5&t>>7)\|(t*3&t>>10)` | viznut | two voices a sixth apart gated by slower bits |
| `t*(t>>9\|t>>13)&16` | Niklas Roy | a one-bit rhythm-melody |
| `(t\|t>>9)` and `t>>3&t>>11` | Adrien Risser; Robert | Sierpinski patterns, rhythm without pitch |
| `(t>>13\|t%24)&(t>>7\|t%19)` | Robert | remainders by 24 and 19 make periods off the binary grid |
| `(t*t*t)>>t` | Madgarden | noise-like |

The `VCVRack`-format module collection `clone45/voxglitch` (GPL-3.0), `src/modules/ByteBeat/ByteBeat.hpp`, holds nine
equations with three user variables `p1`, `p2`, `p3` and safe division, for example
`((t % (p1 + t % p2)) ^ (t >> (p3 >> 5))) * 2`, and runs `t` at a divided clock. greggman's `html5bytebeat` (MIT) is a
browser player and the usual reference for the community's formulas and their evaluation semantics.

### 4.3 Anatomy of a formula

- **`t * k`** is pitch: a sawtooth (after the `& 255`) at `k * 31.25 Hz`. A non-integer or slowly changing `k` gives a
  pitch that steps or glides.
- **`t >> n`** is time: `t >> 12` changes every 4096 samples (0.512 s at 8 kHz), `t >> 13` every 1.024 s. Using these as
  multipliers (`t * (t >> 11 & 7)`) makes a melody whose notes change every bar; using them as masks makes rhythm.
- **`&` with a slower term** gates: bits switch whole groups of the faster pattern on and off, the formula's
  rhythm section. `& 63` and similar limit a multiplier's range, choosing the melody's compass.
- **`|`** fills: it makes the Sierpinski self-similarity of `t | t >> 9`, and harmonics that rise with each set bit.
- **`^`** shuffles: it toggles bits by a slower pattern, giving chord-like sums and differences.
- **`%` by a non-power of two** breaks the binary grid: `t % 24` repeats every 24 samples, a pitch of 333 Hz at 8 kHz,
  unrelated to the octave ladder of the shifts.
- **The truncation to 8 bits** is the waveform: a large product wraps many times per cycle, which is why multiplications
  by large or growing terms become harsh and noisy.

### 4.4 Semantics, and why they matter

Formulas from the community were written for two evaluators with different rules, and a formula sounds right only under
the rules it was written for:

- **C style** (the original `putchar` loop): unsigned or signed 32-bit integers; division truncates; shifts by 32 or
  more and signed overflow are undefined.
- **Web-script style** (the browser players, ECMAScript): arithmetic in double-precision floats; the operands of `&`,
  `|`, `^`, `~`, `<<`, `>>` are converted by ToInt32 (truncate toward zero, then modulo `2^32` into the signed range);
  the shift count is taken modulo 32 (so `t >> 42` means `t >> 10`, which is why the formula `t*(t>>42|t>>12)` works);
  `/` gives a fraction, and division by zero gives an infinity that ToInt32 turns into 0. Most published formulas
  assume this style.

A Rust evaluator matches the web-script style with `f64` arithmetic, a ToInt32 written out (`x.trunc().rem_euclid(2^32)`
then reinterpreted as `i32`, since Rust's `as` saturates rather than wraps), and `wrapping_shl` and `wrapping_shr`,
whose shift counts are already taken modulo the width. Division and remainder by zero are defined as zero in an integer
evaluator, as `voxglitch`'s `div` and `mod` do. Both styles are bit-exact and deterministic: the same formula gives the
same samples on every machine, which is ideal for exports, provided no transcendental function from the platform's
mathematics library enters (section 15).

Variants: **signed bytebeat** reads the low byte as `i8` (centred, no DC); **floatbeat** lets the formula produce a
float from -1 to 1 directly, so `sin` and smooth curves become available.

### 4.5 Pitch, time and playing it as an instrument

In a bytebeat pitch and tempo are one: running the counter faster raises every pitch and speeds the song, as a tape
played fast. Three ways to make a formula playable from a keyboard:

- **Scale the clock with the note.** `t` advances by `inc = f_internal / fs` per output sample, with
  `f_internal = 8000 * 2^((note - reference) / 12)` and the reference the note at which the formula plays as written.
  The formula is evaluated whenever `floor(t)` changes. This keeps the formula's character exactly, tempo and all.
- **Two counters.** The formula is rewritten with a pitch counter `t` (advancing with the note) and a time counter `T`
  (advancing with the song's tempo, in bars), so `t * (T >> 11 & 7)` plays a melody at the song's tempo transposed by
  the note. This needs formulas written for it, or a substitution of `T` for the slow terms `t >> n` with `n` above a
  threshold, which an evaluator can do when it compiles the formula.
- **Reset per note.** `t = 0` (or a seed offset) at each note's start makes every note begin its pattern at the start,
  a percussive "strike"; without it the pattern runs free and each note enters it wherever it is.

Three variables like `voxglitch`'s `p1` to `p3`, each a control from 0 to 255 or a modulation target, turn a fixed
formula into a family of sounds.

### 4.6 Evaluating in the callback

- **Compile when the instrument is built.** Parse the expression once into postfix byte code over a fixed operand
  stack; the depth needed is known at compile time, so the stack is a fixed array (32 entries is ample for one-line
  formulas) and evaluation allocates nothing. A tree of boxed closures also works but costs a pointer chase per node.
- **Bound the work.** Reject formulas longer than a fixed number of operations (a few hundred), so that one sample's cost
  is bounded; there are no loops in the language, so the bound is the length.
- **Test at compile time.** Evaluate a few thousand samples on the building thread: a formula that is constant (silent
  after the DC blocker), or that never changes its output, is reported as silent.
- **Cost.** One dispatch per operation: about 10 to 60 operations per internal sample for typical formulas, evaluated
  only when `floor(t)` changes (for an 8 kHz rate at a 48 kHz output, one sample in six).

### 4.7 Converting the rate, and aliasing

A formula is defined at its internal rate: its own aliasing (multiplications wrapping past the byte) is the sound.
Converting to `fs` is a choice (section 1.2):

- **Plain hold.** Each value held for `fs / f_internal` output samples: the images of the hold, sinc-weighted copies of
  the spectrum around multiples of 8 kHz, make the familiar fizzing top. It is the sound of the formula played through a
  hold resampler.
- **The period converter.** A sound card of 2011 at 8 kHz had an analog reconstruction filter at about 3.5 kHz; the
  formulas as first heard were dull and buzzy, not fizzy. A steep low-pass at 0.45 times the internal rate reproduces it.
- **Band-limited hold.** Each change of value as a band-limited step: the formula's own digital content intact, no
  hold images. The cost is per change.

When the internal rate exceeds `fs` (a high note under the scaled clock: A4 is about 112 kHz if the reference sawtooth
`t` is tuned to it), several values fall in one output sample; average them (box filter) or run a short polyphase
decimator. Without that, the formula aliases a second time against `fs`, an accident rather than the sound.

### 4.8 Hazards

- **DC.** An unsigned byte output averages near 0.5: centre it (`/ 128 - 1`) and high-pass at about 10 to 20 Hz.
- **Loudness.** Many formulas are full-scale squares or noise: RMS near 0 dBFS. A level set by RMS, or a fixed lowering of
  about 10 to 12 dB relative to a sine engine, keeps them in line with other instruments.
- **Precision.** In the floating style, `t * t * t` exceeds the 53 bits of a double's exact integers once `t` passes about
  208000 (26 seconds at 8 kHz); the formula continues, rounded, identically on every machine. In an integer style it
  wraps.
- **Runaway pitch.** A formula with `t * (t >> 8)` rises without limit; after the 8-bit wrap it becomes noise, which is
  bounded but can be very bright; the engine's output low-pass and the project's pitch limits do not apply to a formula's
  content, so a loudness and brightness guard after it does.

## 5. Bit-Wise Oscillators

### 5.1 The phase counter as a source of bits

A digital oscillator's phase is a 32-bit accumulator `phase += increment` with `increment = f / fs * 2^32`, wrapping.
Its bits are already waveforms:

- the top bit is a square wave at `f`; bit `31 - k` a square at `f * 2^k` (octaves up, each with the aliasing of a
  naive square);
- the top byte `phase >> 24` is an 8-bit sawtooth;
- the top byte folded by the top bit (`b ^ (if top { 0xFF } else { 0 })`) is a triangle, as the 1982 chip does it;
- comparing the counter with a width gives a pulse.

### 5.2 Logic between two counters

With two phases `a` and `b` (frequencies `fa`, `fb`):

- **Exclusive or of the top bits** of two squares is their product with the sign flipped: `sign(sa * sb) = -(xa ^ xb)`
  in ±1 terms. This is exact ring modulation of two squares: sum and difference tones of every odd harmonic pair, the
  clangorous digital ring modulator of early machines (the 1982 chip's ring mode replaces its triangle's fold bit with
  the other voice's top bit, which is the same idea).
- **Exclusive or of whole words** (`(a ^ b) >> 24`) is not a product: each bit of the result toggles at the rate of the
  corresponding bits of either input, so the spectrum holds partials at sums and differences of the two fundamentals'
  octave multiples, with an irregular, "bit-crushed ring mod" brightness. `src/noise-plethora/plugins/P_BitShift.hpp` in
  `VCVRack/Befaco` (GPL-3.0-or-later) combines two sawtooths by exclusive or, the second at `f1 * (1 + 7 k)`, and notes
  that two squares give near-silence (their words are only all-ones or all-zeros), while sawtooths' changing bit patterns
  give the rich result.
- **And** of words keeps only common set bits: a sparse, gated sound whose level drops when the phases disagree; with the
  slower counter as a mask, the Sierpinski rhythms of bytebeat appear at audio rate.
- **Or** fills bits: a brighter, more constant, buzzier sound.
- **Phase multiplication** (`(a as u64 * b as u64) >> 32`, or the top halves multiplied) gives a chirping, swept
  timbre within each cycle of the slower phase.

### 5.3 Masks, thresholds and overflow in one oscillator

Surge XT's Alias oscillator (`surge-synthesizer/surge`, `src/common/dsp/oscillators/AliasOscillator.cpp`,
GPL-3.0-or-later), whose source opens "This oscillator is intentionally bad!", is a compact catalogue of bit tricks on
one 8-bit phase:

```
upper  = (phase >> 24) as u8
masked = upper ^ mask                                   // Mask: flips chosen bits of the ramp: a ramp cut into pieces
ramp:   result = masked, or 255 - upper when upper > threshold     // Threshold folds the ramp into a triangle
pulse:  result = if masked > threshold { 255 } else { 0 }          // Threshold is the width, Mask scrambles the edge
then:   result = (result as f32 * wrap) as u8            // Wrap 1 to 16: multiply and overflow the byte: hard tears
out     = (result as f32 - 127) / 255, optionally crushed to 1 to 8 bits
```

For the pulse it also multiplies the phase itself by Wrap before taking the byte, a hard sync for free. Its other
waves read bytes from tables (an 8-bit sine with a shaped variant, additive tables), so that the same mask and threshold
act on any 256-step wave. Every control here is a bit operation, each step of Mask a different, abrupt timbre: a
playable map of the 256 masks is the instrument.

`pichenettes/eurorack`, `braids/digital_oscillator.cc` (MIT), `RenderToy`, is a "circuit-bent toy" in one line:

```
held = (((phase >> 24) ^ (x << 1)) & !x) + (x >> 1)      // x: a byte from the Color control
```

evaluated only when a decimation counter reaches `512 - (timbre >> 6)` (a rate-reduced, held output), at four times
the output rate, and filtered by a 4-tap FIR before decimation. The exclusive or with `x << 1` toggles bits, the and
with `!x` removes them, and adding `x >> 1` offsets: one control walks through a family of broken square and ramp
shapes, and the decimation adds the toy's low, unfiltered sample rate.

### 5.4 Pulse trains, logic mixers and one-bit music

- **Logic mixing.** The 1978 general-purpose generator mixes tone and noise not by addition but by logic:
  `enabled = (tone | tone_off) & (noise | noise_off)` (MAME, BSD-3-Clause), so that with both enabled the noise chops
  the square: a pitched, gritty tone that is neither. The same generator's envelope, when repeated fast, is a sawtooth or
  triangle at audio rate: the "buzzer" bass of its music, a 4- or 5-bit staircase.
- **Pulse counting.** A pulse of width `w` from a counter compare; a pulse whose width is itself a slow counter makes the
  sweep of the classic chip leads.
- **One-bit music.** A speaker driven by one output bit can play several voices by narrow pulses: each voice emits a
  pulse of a few microseconds at its own frequency, and the speaker and ear integrate them (pulse frequency modulation);
  or the program alternates voices sample by sample (time multiplexing). The narrower the pulse, the more voices mix
  without one masking another, and the quieter each is. A model renders each voice's pulses as band-limited steps; the
  thin, buzzing, characterful result is all in the narrow pulses' flat spectrum.

### 5.5 Walsh functions

Walsh functions are the square-wave counterpart of sines: an orthogonal set of two-valued (±1) functions on `2^m`
steps, from which any stepped wave of `2^m` steps can be built exactly by a weighted sum. With `n` the top `m` bits of a
phase counter:

```
Hadamard (natural) order:   W_h(n) = (-1)^parity(h & n)
sequency order (by the number of sign changes s):
    g = s ^ (s >> 1)                      // Gray code of s
    h = bit_reverse_m(g)                  // reversed over m bits
    wal(s, n) = (-1)^parity(h & n)
check for m = 2: s = 1 gives + + - -, s = 2 gives + - - +, s = 3 gives + - + -
```

Each function is one and, one popcount and one sign: a Walsh bank of 16 to 64 terms is a few operations per term, far
cheaper than as many sines. Walsh synthesis was studied for music in the 1970s (B. A. Hutchins, "Experimental electronic
music devices employing Walsh functions", JAES 21, 1973; E. Insam, "Walsh functions in waveform synthesis", JAES 22,
1974; H. F. Harmuth, *Transmission of Information by Orthogonal Functions*, 1969). Its sound: with few terms, hollow
squares and staircases that morph in steps; moving the weights is "digital additive" synthesis whose changes are
abrupt and bright. Every term jumps only on the `2^m` grid of the phase, so a band-limited step per grid crossing (the
sum's change, at most `2^m` per cycle) removes the aliasing where it is unwanted; at low `m` and high notes the
grid's own aliasing is the chip-like sound.

### 5.6 Aliasing in bit oscillators

Every output of this section is piecewise constant, with jumps wherever any bit it uses changes. Three treatments:

- **Exact.** Find the jump times analytically (each bit of a phase changes at known fractional times) and add a
  band-limited step for each change of the output word. Exact, but the number of transitions grows with the number of
  bits used and the pitch.
- **Oversample and decimate.** Run the logic at 4 to 8 times `fs` and decimate through a short FIR: `RenderToy`'s four
  times oversampling with a 4-tap FIR (`kFIR4Coefficients`) is a cheap version, and a 16- to 32-tap half-band cascade
  a cleaner one.
- **Accept it.** At low pitches, with few bits, the aliasing is far above the harmonics that matter; at high pitches it
  is the chip's own sound. The code says which it chose, as the project's rules require.

## 6. Cross-Modulation of Digital Oscillators

Digital oscillators couple in ways that differ from analog cross-modulation because their states are integers:

- **Integer frequency modulation.** Adding one oscillator's output, scaled, to another's phase increment (FM) or phase
  (PM, `ENGINES_RESEARCH.md`, section 1). At low resolutions (an 8-bit modulator, a 16-bit increment) the modulation is
  stepped, and the carrier's pitch jumps between quantised values: a buzzing, granular FM.
- **Sync and reset by a bit.** One counter's top-bit edge resets another (hard sync), or a chosen lower bit does, so the
  reset happens at a multiple of the master frequency.
- **A loop of two.** One oscillator modulates the other's frequency while the second modulates the first's pulse width:
  at low rates (tens of hertz) a lurching, rhythmic growl; at audio rates a chaotic, cross-locked buzz. The
  `VCVRack/Befaco` repository has such a pair among its noise algorithms (GPL-3.0-or-later): a square at `10 + 50 k1^2`
  Hz frequency-modulated by a pulse at `10 + 200 k2` Hz, which pulse-width-modulates it back.
- **Feedback FM.** `y[n] = sin(phi[n] + beta * (y[n-1] + y[n-2]) / 2)`: below a `beta` of about 1 a brightening saw-like
  tone; above about 1.5 the loop becomes chaotic and the tone turns to noise. The two-sample average tames the
  period-two oscillation that a one-sample feedback falls into. Braids' `RenderChaoticFeedbackFm`
  (`braids/digital_oscillator.cc`, MIT) is a version driven into chaos on purpose.
- **Bit selection.** One oscillator's bits choose which of several waves, tables or registers the other plays: a
  sample-accurate wave sequencing at audio rate, glitchy and rhythmic.
- **Cross-ring by exclusive or.** Section 5.2.

Cost: one or two extra operations per sample over the oscillators themselves. Hazard: loops of two can lock into a
fixed state or DC; a seeded nudge on lock-up keeps them moving.

## 7. Phase Distortion, Accumulator Truncation and Small Tables

### 7.1 Phase distortion

A cosine read through a bent phase: the phase `phi` (0 to 1) is mapped by a piecewise-linear curve with a breakpoint
`d` (0 to 0.5) so that the first half of the cosine is read in `d` of the cycle and the second half in the rest:

```
phi' = phi / (2 d)                               for phi < d
phi' = 0.5 + (phi - d) / (2 (1 - d))             for phi >= d
out  = -cos(2 pi phi')
```

At `d = 0.5` a pure cosine; as `d` falls toward 0 the wave approaches a sawtooth. Other warps give a square (two
breakpoints) and a pulse. The "resonant" forms multiply a window (a falling ramp `1 - phi`, a triangle or a trapezoid) by
a cosine at a higher, freely moving ratio `r` reset at each cycle: `out = w(phi) * cos(2 pi r phi)`, a formant at `r`
times the note, related to hard sync and to VOSIM. These were the basis of a 1984 line of home-keyboard synthesizers.
The sharp corner of the warp and the reset of the resonant forms alias at high notes; a mip-mapped table of the warped
wave, or a band-limited correction at the reset (`QUALITY_RESEARCH.md`, 1.2), removes it. Cost: a division-free
piecewise map (precompute `1 / (2d)` and `1 / (2(1 - d))` at control rate) and a table read: about 8 operations.

### 7.2 Phase-accumulator truncation

A table oscillator with an `N`-bit accumulator addresses its table with only the top `M` bits; the discarded bits make
a periodic phase error and so spurious tones ("spurs"). The worst spur is about `-6.02 M` dB relative to the carrier
(H. T. Nicholas and H. Samueli, "An analysis of the output spectrum of direct digital frequency synthesizers in the
presence of phase-accumulator truncation", Frequency Control Symposium, 1987); the spurs' frequencies depend on the
discarded part of the increment, so they move unpredictably with pitch. Deliberately small `M` (5 to 8 bits) is a cheap
source of grit that changes from note to note. Dithering the phase with a small random value before truncation turns
the spurs into noise; leaving it undithered keeps the tonal, "whistling" artefacts that are the character.

### 7.3 Low-resolution wavetables

- **Length and bits.** A table of `L` steps and `B` bits: quantisation noise about `6.02 B + 1.76` dB below a full-scale
  sine; reading without interpolation adds noise falling about 6 dB per doubling of `L`, with linear interpolation about
  12 dB per doubling (F. R. Moore, "Table lookup noise for sinusoidal digital oscillators", Computer Music Journal 1(2),
  1977). The handheld console's 32 steps of 4 bits and the 8-bit, 256-step tables of early digital synthesizers are the
  references.
- **Variable-rate playback.** Early samplers played each voice's table at a clock proportional to its pitch, through a
  converter without much filtering: the hold's images move with the note (they sit at multiples of the voice's own
  rate), so the grit is harmonic-related and follows the melody, unlike a fixed-rate reducer whose aliases are fixed in
  frequency and sound inharmonic. A model holds each table step for its exact fractional duration at the voice's clock.
- **Lookup errors as timbre.** An index masked to fewer bits (`index & mask`) repeats part of the table; an index read
  past the end into the next table; interpolation across the boundary between two waves; an index whose bits are
  reordered (section 11). Each is a cheap, deterministic way to bend a table into new shapes.

## 8. Digital Ring Modulation, Dividers and Flip-Flops

- **Ring modulation as sign logic.** For signals in two's complement, the product's sign is the exclusive or of the
  signs; a one-bit ring modulator keeps only that: `out = if (x < 0) ^ (y < 0) { -1 } else { 1 }`, a hard, square
  version of the effect. Multiplying a signal by a square carrier (flipping its sign each half cycle of the carrier) is
  the "digital ring mod" of many chips and toys: the signal's sum and difference with every odd harmonic of the carrier.
- **Flip-flop "filters".** The 1979 computer's chip has a high-pass mode that is in fact a latch: one channel's output is
  exclusive-or'd with a flip-flop that samples it at another channel's rate (MAME, BSD-3-Clause). The result is a ring
  modulation of the two rates with a stroboscopic character.
- **Divider chains.** Section 3.6. Dividing a ring-modulated or noisy signal's zero crossings (a flip-flop toggling at
  each upward crossing) makes a square an octave below the input's apparent pitch, which tracks noisy and chaotic input
  erratically: the "octave fuzz" of digital toys.

## 9. Chaotic Maps, Automata and Number Sequences as Audio

### 9.1 Iterated maps at a clock

A map `x[k+1] = F(x[k])` iterated once per clock tick and held is a sound source: periodic orbits are tones at
`fc / period`, chaotic orbits noise with a structure. `MODULATORS_RESEARCH.md` covers continuous systems at control
rate; here the maps run at audio rate. SuperCollider's chaotic UGens (`server/plugins/ChaosUGens.cpp`, by Lance Putnam,
and `NoiseUGens.cpp`, GPL-2.0-or-later) give each a frequency `freq` at which it iterates and holds (`...N`), or
interpolates linearly (`...L`) or cubically (`...C`):

| Map | Iteration | Useful range | Sound |
| --- | --- | --- | --- |
| Logistic | `x = r x (1 - x)` | `r` 3.4 to 4.0 | period doubling: tones at `fc/2`, `fc/4`, `fc/8`, then noise at `r` above 3.5699; a clean tone at `fc/3` in the window near `r = 3.8284` |
| Hénon | `x' = 1 - a x^2 + y; y' = b x` | `a` 1.15 to 1.4, `b` 0.15 to 0.35 (classic 1.4, 0.3) | grainy noise with a faint pitch; `x` within about ±1.3 |
| Crackle | `y0 = abs(p y1 - y2 - 0.05)` | `p` 1.0 to 2.0 (`Crackle`) | from a buzz to crackling fire |
| Cusp | `x = a - b sqrt(abs(x))` | `a` 1, `b` 1.9 (defaults) | harsh periodic or chaotic buzz |
| Gingerbreadman | `x' = 1 - y + abs(x); y' = x` | initial point only | a fixed six-sided pattern or noise |
| Standard | `y = y + k sin x; x = x + y`, both modulo `2 pi` | `k` 0.5 to 2 | whistles to noise as `k` passes about 0.97 |
| Linear congruential | `x = (a x + c) mod m` | small `m` | short repeating patterns: pitched noise |
| Feedback sine | `x = sin(i y + f x); y = (a y + c) mod 2 pi` | `i`, `f` near 1 | a feedback-FM-like whistle to noise |

The logistic map is the most musical: its parameter `r` is a single "order to chaos" control, and clocked at a multiple
of the note (`fc = 4 f_note`, so that period four sounds the note), turning `r` up moves through the note's octave below,
two octaves below, a burst of subharmonics, and then noise, with windows of clear tone inside the chaos. The
`VCVRack/Befaco` repository's `P_LogisticNoise.hpp` and `P_HenonDust.hpp` (GPL-3.0-or-later) are short, readable
versions with escape resets.

### 9.2 Numerical hazards of maps

- **Absorbing points.** The logistic map at exactly 0 or 1 stays at 0 for good; a Hénon orbit can escape to infinity for
  `a` beyond its basin. After each iteration, a value outside its known range, or not finite, is reset to a seeded point
  inside it, as `P_LogisticNoise.hpp` does (`if x < 0 || x > 1 || !x.is_finite() { x = 0.5 + small seeded offset }`).
- **Collapse in binary floats.** The doubling map `x = 2x mod 1` and the tent map with slope exactly 2 lose one bit of
  the mantissa per iteration in binary floating point and reach 0 within about 53 iterations: a chaotic map that falls
  silent in a millisecond. Slopes slightly below 2, or an integer state (an LFSR is the integer form of this idea), avoid
  it.
- **Stuck orbits.** A periodic orbit of period one is DC, silent after the blocker; a voice detects a constant output
  over a block and nudges the state.
- **Determinism.** A map in `f64` repeats exactly on one machine and across machines with identical operations in
  identical order; Rust does not fuse multiply-adds unless asked, so this holds, but `sin` from the platform's library
  can differ by an ulp between platforms, and chaos amplifies an ulp into a different sound within milliseconds. A sine
  of the engine's own (a polynomial) keeps exports identical everywhere (section 15).

### 9.3 Digital feedback loops

A delay loop with gain above one and a bounded nonlinearity self-oscillates; the nonlinearity's kind decides the sound:

- **Clipping** in the loop: a squealing, pitched tone at the loop's delay, like a no-input mixer.
- **Wrapping** (integer overflow) in the loop: the loop cannot blow up, since wrap is bounded, but it becomes chaotic
  noise rather than a tone; a filter in the loop colours it.
- **Rate reduction or quantisation** in the loop: each pass degrades the signal further; the hold adds its own pitch.
- **Progressive degradation.** `src/noise-plethora/plugins/P_GlitchLoop.hpp` (`VCVRack/Befaco`, GPL-3.0-or-later)
  plays a buffer of noise in a loop, writing each sample back crushed, and losing a fraction of a bit per pass; when the
  depth reaches one bit it refills with fresh noise: a sound that decays in resolution rather than in level.

Hazards: a loop with rectification or asymmetric clipping builds DC, which saturates the loop and silences it; a DC
blocker inside the loop prevents that. Every loop has an escape check and reset (`QUALITY_RESEARCH.md`, section 12).

### 9.4 Cellular automata

An elementary cellular automaton is a row of cells, each 0 or 1, whose next state depends on itself and its two
neighbours by a rule numbered 0 to 255 (Wolfram's code: bit `4l + 2c + r` of the rule number is the new state for
neighbours `l`, `c`, `r`). A row of 64 cells fits a `u64`, and with wraparound neighbours (`rotate_left(1)` and
`rotate_right(1)`) several rules are a few operations for all 64 cells at once:

```
rule 90  (Sierpinski):       next = l ^ r
rule 30  (chaotic):          next = l ^ (c | r)
rule 150:                    next = l ^ c ^ r
rule 110 (complex):          next = (c ^ r) | (c & !l)
any rule, cell by cell:      next_i = (rule >> (4 l_i + 2 c_i + r_i)) & 1
```

Musical uses:

- **Rows as wavetables.** Each generation, mapped to ±1 or grouped into multi-level steps, is a wave of 64 steps played
  at the note's pitch; a new generation every few cycles makes a timbre that evolves by the rule: rule 90's nested
  triangles cycle, rule 30's rows are noise-like, rule 110's sit between.
- **Rows as amplitude masks.** The `VCVRack/Befaco` repository's `P_CellularSynth.hpp` (GPL-3.0-or-later) groups 32
  cells into eight groups of four and sets each of eight sawtooth harmonics' level by the count of live cells in its
  group (0, 0.25, 0.5, 0.75 or 1), stepping the rule and the generation rate by two controls.
- **Rows as rhythm.** One cell per step of a sequencer, a new generation each bar.
- **Two-dimensional automata** as grids of grain parameters (E. R. Miranda, "Granular synthesis of sounds by means of a
  cellular automaton", Leonardo 28(4), 1995): each cell's state sets a grain's frequency, so the grid's evolution is the
  sound's.

Cost: a generation is a handful of operations at control rate; reading a row as a table is a shift and a mask per
sample. Hazard: many rules die to all zeros or all ones (silence or DC); a seeded reseed on a dead or fixed row.

### 9.5 Collatz-like sequences

The Collatz rule (`n` even: `n / 2`; odd: `3n + 1`) gives "hailstone" sequences that rise and fall irregularly before
reaching the loop 4, 2, 1. As audio: the low bits of `n` per clock tick (`n & 255`), or its parity as a one-bit
signal, or its sequence of steps up and down as a melody. Each seed gives a different, unpredictable but repeatable
shape; when the sequence reaches 1, the next seed (`seed + 1`, or a seeded jump) starts, so the sound evolves through
neighbouring seeds. Variants with other multipliers (`5n + 1`) diverge for some seeds. Cost: a branch, a shift or a
multiply-add a tick. Hazard: overflow; cap `n` below `2^60` in a `u64`, and restart if exceeded.

### 9.6 Dynamic stochastic synthesis

Iannis Xenakis's GENDY (*Formalized Music*, 1992 edition; P. Hoffmann, "The new GENDYN program", Computer Music Journal
24(2), 2000; M. Serra, "Stochastic composition and stochastic timbre: GENDY3 by Iannis Xenakis", Perspectives of New
Music 31(1), 1993) builds each wave cycle from `N` breakpoints, each with an amplitude and a duration that take a random
walk between mirrors (reflecting barriers) from one cycle to the next, the steps drawn from a chosen distribution
(Cauchy, logistic, hyperbolic cosine, arcsine, exponential). Narrow walks hold a pitched, buzzing tone; wide ones
dissolve it into noise and glissandi. SuperCollider's `Gendy1` to `Gendy3` (`server/plugins/GendynUGens.cpp`, GPL-2.0-or-later) realise it. Cost: per
breakpoint, two random draws and two mirror reflections, linear interpolation between: about 10 to 20 operations per
sample for `N` of 8 to 16. Hazard: a duration walking to zero makes a cycle of no length; durations are bounded below.

### 9.7 Fractal synthesis

- **Weierstrass waves.** `W(t) = sum_k a^k cos(2 pi b^k f t)`, with `0 < a < 1` and `b > 1`; when `a b > 1` the curve is
  fractal, its graph's dimension `D = 2 + ln a / ln b`. As additive synthesis it is band-limited by stopping the sum
  where `b^k f` reaches `fs / 2`. With `b` irrational the partials are inharmonic and the sound has the same shape at
  every scale: a metallic, Shepard-like timbre whose pitch is ambiguous.
- **Midpoint displacement.** A wave cycle made by recursive subdivision: each midpoint displaced by a random amount
  scaled by `2^(-H level)`, `H` (0 to 1) setting roughness from noise to smooth. Each note's cycle drawn from its seed;
  built on a non-real-time thread as a table and played at pitch.
- **Fractal interpolation functions** (M. F. Barnsley, *Fractals Everywhere*, 1988): a few control points and a vertical
  scaling factor per segment define a self-affine curve through them; the factor is a roughness control from a
  piecewise-linear wave to a jagged, noisy one.
- **1/f noise.** Section 3.7.

## 10. Glitch Techniques

All rely on a capture buffer (`EFFECTS_RESEARCH.md`, section 11): a circular buffer always recording a few seconds,
allocated when the instrument is built, with triggers placed by the song's clock so that exports match playback.

### 10.1 Stutter, repeat and beat repeat

A slice of length `L` (1/4 to 1/64 of a beat, triplets included) marked at a quantised trigger is replayed from its
start for a duration, each repeat faded in and out over 1 to 5 ms with a raised cosine. Variations: each repeat shorter
than the last (a roll that accelerates into a buzz once `L` falls below about 20 ms, a tone at `1 / L`); each repeat read
slower or faster (a falling or rising pitch); a gate cutting each repeat to a share of its length; a decay per repeat.
A beat repeat adds a probability per bar and a choice of which beat is captured.

### 10.2 Reverse

The slice read backwards with cubic interpolation from its end; the crossfade at the switch matters more than for a
repeat, because the reversed attack arrives at full level. A "reverse echo" reads each repeat reversed.

### 10.3 Tape stop and spin-up

The read speed falls from 1 to 0 over a time `T` (50 ms to 2 s, often a beat or a bar), the read position integrating
the speed:

```
linear:       v(t) = 1 - t / T;            p(t) = t - t^2 / (2 T)
curved:       v(t) = (1 - t / T)^g, g 1 to 3 (g near 2 sounds like a heavy platter)
exponential:  v(t) = exp(-t / tau) until v < 0.01, then stop
```

Read with cubic interpolation; as the speed falls the content sinks below hearing, so the stop ends with a short fade
and the output is high-passed against the DC of a frozen read. Spin-up is the curve reversed, starting from silence or
from the stopped point.

### 10.4 Granular scramble

One bar captured, cut into `S` slices (8, 16 or 32); a permutation drawn by a seeded Fisher-Yates shuffle (seeded from
the instrument and the bar's index, so that every pass of the song scrambles alike) decides which slice plays in each
slot; each slice windowed with 1 to 3 ms fades. Controls: the share of slots replaced (0 keeps the bar whole), the
chance a slot repeats the previous slice or reverses its own, and the slice size. Cost: a read and a window a sample.

### 10.5 Dropping and squeezing whole cycles

- **Wave loss.** At each upward zero crossing a new cycle begins; drop `d` of every `n` cycles (in order, or at random
  with probability `d / n`), outputting silence for them: `WaveLoss` in sc3-plugins (`source/MCLDUGens/
  MCLDDistortionUGens.cpp`, by Dan Stowell; sc3-plugins is under the GNU GPL, its file headers saying version 2 or any
  later version). Cutting at zero crossings keeps the cuts nearly click-free while the sound stutters and thins.
- **Squiz.** The input written into a short buffer, which is read back at `ratio` times the speed, the write and read
  restarting together every `z` zero crossings (the same file's `Squiz`): each chunk of `z` cycles played faster and
  followed by silence, a pitch-raising grit like a sampler with no time-stretching.

### 10.6 Bit flips, stuck bits and byte swaps

Damage to the sample word, on its 16-bit two's-complement form `w = round(x * 32767)`:

- **Bit flips.** Each sample, bit `b` flipped with probability `p_b`: `w ^= 1 << b`. A flip of bit `b` changes the value
  by `2^b / 32768`: low bits add a fine grit like a failing converter, middle bits crackle, and bit 15, the sign, jumps
  by a whole full scale, a click as loud as anything can be. A "bit range" control (lowest and highest bit that may
  flip) and a probability from about `1e-5` to `1e-2` per sample make it playable; bit 15 is left out unless the level is
  guarded after.
- **Stuck bits.** `w & !(1 << b)` (stuck low) and `w | (1 << b)` (stuck high): a stuck high bit adds a DC offset and a
  square-like distortion that follows the signal; stuck low bits are a crude crush.
- **Shorted bits.** `w` with bit `j` replaced by `bit_j & bit_k` or `bit_j | bit_k`: the data-line short of a bent toy.
- **Byte swap.** `w = w.swap_bytes()`: the fine detail of the low byte becomes the coarse value, so quiet signals become
  loud noise and loud ones a scrambled buzz. It inverts dynamics, so it is a hazard at low input levels.
- **Mantissa masking.** On a 32-bit float, keeping only the top `k` of its 23 mantissa bits: `bits & (!0 << (23 - k))`
  (SuperCollider's `MantissaMask`, GPL-2.0-or-later). The quantisation is relative to the level, so it never gates to
  silence and stays smooth when quiet: a floating-point crush, gritty only on loud material.

### 10.7 Dropouts and buffer underruns

A failing audio device's sounds as algorithms, applied at block boundaries of `B` samples (64 to 2048) with a probability
per block:

- **Zero fill:** the block is silent, a dropout click at each end.
- **Repeat the last block:** the previous `B` samples again, possibly several times: a buzz at `fs / B` (93.75 Hz for
  512 samples at 48 kHz), the machine-gun stutter of an overloaded computer.
- **Stale data:** a block from one buffer length earlier, as a ring buffer read before it is refilled.
- **Hold:** the last sample held: a step to DC, which is always followed by a fade within a few milliseconds and a DC
  blocker, since a held DC wastes headroom and moves speakers.
- **A disc's skip:** a compact disc's audio is in sectors of 588 stereo frames (1/75 s); a skipping player repeats or
  jumps whole sectors, and its error concealment holds or interpolates over damaged ones, so skips quantised to 588
  frames at 44.1 kHz (or `fs / 75`) sound right.

Cost: under 10 operations a sample beyond the buffer read. All randomness is seeded by block index for repeatable
exports.

## 11. Circuit-Bent Toy Sounds as Algorithms

Circuit bending (the term is Reed Ghazala's) rewires cheap sound toys: talking toys, toy keyboards and sample-playing
drum toys. Each bend has a direct algorithmic form:

- **Clock bending.** The toy's clock sets both pitch and sample rate. Replacing it with a variable or modulated clock
  plays the sample ROM at another rate through a converter with no filter: the hold's images move with the clock, and an
  audio-rate modulation of the clock is frequency modulation of the playback, with its sidebands aliased. Model: a
  phase in ROM steps advanced by `clock / fs`, the value held for exact fractional durations, the clock modulated by an
  LFO, by an envelope or by the signal itself (a feedback "growl").
- **Address bending.** Bridging or cutting an address line forces a bit of the ROM index: `i | (1 << k)`, `i & !(1 << k)`,
  or two bits joined (`i` with bit `k` replaced by bit `j`). Samples play in pieces, out of order, or stuck in a short
  segment, rhythmically and deterministically. An index permutation by bit reordering (a bit-reverse of the low `m`
  bits) scrambles a sample into a stuttering noise that still keeps its envelope.
- **Data bending.** Bridging data lines combines sample bits by and or or (section 10.6): grit and distortion.
- **Crash loops.** A processor driven into an endless loop replays a short window of memory: a looped segment `[a, a + L)`
  of the ROM, `a` and `L` jumping at random when "bent" again.
- **Brownout.** A falling supply voltage slows the clock (pitch drops), lowers the level, adds noise, and finally resets
  the toy: a pitch-and-level envelope ending in a restart of the sample.
- **Body contact.** A finger across two points makes a resistance that wanders with pressure and moisture: a smooth random
  walk on the clock, a few hertz, which gives bent toys their wobbling, vocal quality.
- **Speech-toy bending.** The linear-predictive talking toys (`ENGINES_RESEARCH.md`, section 8) are bent by changing
  their frame rate (speech slowed or sped without pitch change, until frames smear), by freezing a frame (a sustained
  vowel-like drone), or by corrupting reflection coefficients (screeching, as poles near the unit circle). A
  coefficient of magnitude 1 or more makes the lattice unstable: a model clamps every `|k| <= 0.995`, whatever the bend.

`braids/digital_oscillator.cc`, `RenderToy` (section 5.3), is a compact toy model in this spirit. Sample sources for a
bent-toy engine must be the program's own (made by its own synthesis or drawn tables), since toy ROMs are copyrighted.

## 12. Harsh-Noise-Wall Textures

A harsh-noise wall is a sustained, dense, static mass of distorted noise in which change is slow and small: the music is
in the grain, the texture and the subtle movement inside an apparently unchanging sound. Its signal chain, as algorithms:

- **Sources.** Several noises together: white or clocked noise, brown noise (integrated white noise with a leak), a
  crackle or chaotic map, and a feedback loop (section 9.3), each with its own level.
- **Resonant movement.** Each source through one or two resonant band-pass or low-pass filters whose cutoffs take slow,
  seeded random walks (0.01 to 0.2 Hz), so the wall's colour drifts over tens of seconds.
- **Multi-stage distortion.** Two to four stages of heavy gain into clipping or folding, each with its own emphasis
  filter, so that the stages' intermodulation fills every gap in the spectrum; feedback from the last stage to the first,
  bounded by the clipper, adds roar.
- **Density control.** The fewer the gaps in time and frequency, the more "wall"; a compressor or simply the clipping
  holds the level flat.
- **Stereo.** Later, decorrelated noise seeds per channel give width; in mono, slow spectral motion stands in for it.

Hazards are the main design problem. The wall's crest factor is only 3 to 6 dB, against 12 to 20 dB for most music, so
at the same peak it is 10 dB or more louder; and its energy fills the 2 to 5 kHz region where hearing is most sensitive.
Exposure guidance (the United States NIOSH recommends 85 dBA for 8 hours, halving the time for each 3 dB more, so 15
minutes at 100 dBA) is reached quickly at monitoring levels. A wall engine sets its level by a loudness measure (RMS over
about 300 ms with a K-style weighting), not by peak; offers a tilt that lowers the top by 3 to 6 dB an octave; and keeps
a high-pass against subsonic rumble and a low-pass against sustained energy above 16 kHz, which tires listeners and
stresses tweeters without adding to the sound.

## 13. Destroyer Distortions

A destroyer takes any input to complete ruin by stages, each with a characteristic sound; their order is a large part
of the sound. `BITCRUSHING.md` treats folding, wrapping, rectifiers and bit operations as moderate colour; this section
gives them at destructive settings, with their antiderivatives, their order in a chain and their guards.

### 13.1 Extreme gain

Gain of +20 to +60 dB before the nonlinearity. At those gains every shaper becomes a square-wave maker, so the stages
after it are what distinguish destroyers. Points of craft:

- **Pre-emphasis.** A high-pass or mid-peak before the gain (`QUALITY_RESEARCH.md`, 6.1) keeps the bass from swamping
  the stage and makes the distortion bite in the upper mids; a matching low-pass after removes fizz.
- **The noise floor.** +60 dB lifts a -90 dB floor to -30 dB: denormal-flush noise, dither and reverb tails become a hiss
  bed. A gate before the gain (or a gain that follows the input's envelope) keeps silence silent.
- **Gain law.** A gain control in decibels with an exponential map, smoothed per sample (a one-pole of 5 to 20 ms), since
  a stepped 40 dB gain change is a click.

### 13.2 Folding

The signal, past a threshold, is reflected back rather than clipped, so higher gain adds more folds and more harmonics
instead of a flat top:

```
triangle fold, period 4, unit amplitude:
    u = ((x + 1) mod 4) - 1                      // u in [-1, 3), mod as Euclidean remainder
    fold(x) = if u < 1 { u } else { 2 - u }
sine fold:   fold(x) = sin(pi x / 2)
```

`mtytel/vital` (GPL-3.0-or-later), `src/synthesis/effects/distortion.cpp`, writes both from one modulo: `linearFold`
is `abs(mod(x * drive / 4 + 0.75) * -4 + 2) - 1` and `sinFold` is `sin1(mod(x * drive * -0.25 + 0.5))`, with
`sin1` a sine of one cycle per unit. Airwindows' Fracture (`airwindows/airwindows`, MIT) folds by
`sign(x) * sin(min(abs(x * density) * fracture, fracture))`, `fracture` from 1 to about 4 half-turns of pi, a fold whose
number of turns is a control. Folding aliases strongly: each fold adds a corner. Antiderivative anti-aliasing works well
because the folds' antiderivatives are simple:

```
triangle fold:  F(x) = u^2 / 2                     for u < 1
                F(x) = 2u - u^2 / 2 - 1            for u >= 1        (continuous, periodic, F = 0.5 at u = 1 and u = 3)
sine fold:      F(x) = -(2 / pi) cos(pi x / 2)
first-order ADAA:  y = (F(x[n]) - F(x[n-1])) / (x[n] - x[n-1]),  or fold((x[n] + x[n-1]) / 2) when they are close
```

With first-order ADAA and two times oversampling, a fold driven 20 dB past its threshold is clean to the ear; beyond
that, four times.

### 13.3 Wrapping

Two's-complement overflow: past full scale the signal jumps to the opposite extreme:

```
wrap(x) = x - 2 * round(x / 2)                     // in [-1, 1)
F(x)    = wrap(x)^2 / 2                            // its antiderivative: continuous, since wrap = ±1 at each jump
```

A gentle overload wraps the peaks into tearing, sawtooth-like spikes; heavy gain wraps many times a cycle, a noise-like
scream that keeps the input's rhythm. Wrapping is bounded by construction, which makes it safe inside feedback loops.
Float-to-integer conversion is not a wrap in Rust (`as` saturates), so a wrap is written out explicitly.

### 13.4 Bit masking and bit operations

On the signal as a 16-bit (or 8-bit) word `w`:

- **And with a mask** removes chosen bits: masking low bits is quantisation (`BITCRUSHING.md`); masking a middle or top
  bit while keeping lower ones gives a non-monotonic staircase, a harsh, gated distortion unlike any crush.
- **Exclusive or with a constant** flips bits: flipping the sign bit of an offset-binary word is an inversion of half the
  wave; flipping a middle bit adds a square wave locked to the signal's level crossings.
- **Shifts and rotations** of the word: a left shift is gain with wrap; a rotate moves the top bits into the bottom, a
  scrambling noise.
- **Anti-aliasing.** Each of these is a piecewise-constant function of the input level, so a table of its antiderivative
  over the word's codes (256 or 65536 entries, computed when the setting changes, off the audio thread) gives first-order
  ADAA by two table reads and a division; oversampling handles the rest. The staircase character stays, the aliasing of
  each step's corner does not.

### 13.5 Rectification

Half-wave `max(x, 0)` and full-wave `abs(x)`. Full-wave doubles the fundamental of a simple wave (an octave up, the
"octave fuzz"), half-wave adds even harmonics; both make DC, which a high-pass at 10 to 20 Hz removes after the stage,
and both have corners that alias (antiderivatives `x^2 / 2` for the positive part and `sign(x) x^2 / 2` for the absolute
value make ADAA easy). Rectification after a fold folds the wave's negative half up over the positive, doubling the
fold density.

### 13.6 Sample-rate collapse

A hold at a low rate, down to a few hundred hertz, where the alias becomes the whole sound. The details of rate
reduction, its jitter and its band-limited form are in `BITCRUSHING.md` and `QUALITY_RESEARCH.md` 6.2; points specific
to destruction:

- **Range.** The musically interesting collapse runs from about 8 kHz (gritty) through 2 kHz (shattered) to 200 Hz (a
  wash of aliases with only the input's rhythm left). `pichenettes/eurorack`, `braids/braids.cc` (MIT), offers the
  decimation factors 24, 12, 6, 4, 3, 2 and 1 with the masks `0xc000, 0xe000, 0xf000, 0xf800, 0xff00, 0xfff0, 0xffff`
  (2 to 16 bits), applied together at the output.
- **Softening.** Airwindows' DeRez2 (`airwindows/airwindows`, MIT) interpolates each held value toward its predecessor by
  the hold's fractional position, mixes the new hold with the previous by a `soften` share, and offers a companding curve
  `log(1 + 255 |x|) / log(256)` before quantisation, the shape of the 8-bit mu-law telephone codec, so that quiet
  passages keep resolution. Its quantiser subtracts the step in a `while` loop, whose cost grows with level over step: a
  floor division is the bounded form.
- **Tracking.** A collapse rate that tracks the note (a multiple of its frequency) keeps the aliases harmonic, a
  pitched, chip-like destruction; a fixed rate gives inharmonic, metallic aliases that do not follow the melody.
- **Csound's `fold`** opcode (LGPL-2.1-or-later) is the same hold under its traditional name, "artificial foldover".

### 13.7 Decimate-and-smash chains

The order of stages decides the sound:

| Order | Sound |
| --- | --- |
| gain, fold, then collapse | rich, harmonic folds turned into a field of aliases: the classic shattered lead |
| collapse, then gain and fold | the hold's steps are folded: square edges become folded squares, a buzzy, toy-like violence |
| gain, wrap, crush | tearing spikes quantised: harsh, gated, noisy |
| crush, then gain | each quantisation step amplified into a square: the input's level becomes a stepped pitch-like buzz |
| rectify, then fold | double-density folds, an octave-up roar |
| fold, rectify, collapse, wrap | total destruction: noise carrying only the input's envelope |

A destroyer chain is anti-aliased at its continuous stages (gain, fold, wrap, rectify, run at two to four times `fs`
with ADAA) and then decimated before the rate collapse and the bit operations, which run at `fs` and alias on purpose.

### 13.8 Loudness, DC and safety

- **Loudness compensation.** Every destroyer stage raises RMS; measured by an RMS follower (about 300 ms) before and after
  the chain, a compensating gain keeps the output within a few decibels of the input's loudness as controls move, so that
  turning the destruction up does not simply make it louder.
- **A ceiling.** A final peak limiter or a clean hard clip at about -1 dBFS; nothing a setting does can exceed it.
- **DC.** A blocker after every rectifying, asymmetric, masking or offset stage.
- **Zipper.** Stepped controls (bits, masks, fold count) are crossfaded between the outputs of the old and new setting
  over a few milliseconds, since a jump between bit depths is a click.
- **Silence.** A gate on the input (or the input's envelope applied after the chain) so that the chain's own noise does
  not play between notes.
- **Non-finite values.** A check after the chain that resets state and outputs silence for the block on a NaN or an
  infinity.

### 13.9 Cost

At two times oversampling: gain and emphasis about 8 operations, a fold or wrap with ADAA about 10, a two-times
half-band up and down about 30 to 40, the hold and the bit operations about 6, the loudness follower and limiter about
10: some 60 to 80 operations a sample, about 120 at four times oversampling.

## 14. Making It Playable

- **Pitch tracking.** Every clocked source (registers, held noise, maps, formulas, collapse rates) offers its clock as a
  multiple of the note's frequency, so that its pitch, its period's fundamental or its aliases follow the melody; and a
  free mode, for textures and drums.
- **Seeds.** Every random source seeded from the instrument and the note (and the bar, for glitch triggers), so that a
  part plays and exports identically; a Seed control chooses among sounds, and a "new seed per note" switch makes every
  note different but repeatable.
- **Density.** For dust, particles, flips, dropouts and scrambles, one density control on an exponential scale (events
  per second or probability per block), so that the useful sparse end is not crowded into the first few percent.
- **A single Harshness macro.** One control that moves several stages in a fixed order, each beginning where the last is
  well under way: more clock or bits first (brightness), then fold or wrap (density of harmonics), then rate collapse,
  then bit damage. The map is perceptual: equal steps of the control give roughly equal steps of change, and the
  loudness compensation of 13.8 keeps level constant across it. The untouched value is a usable, moderately harsh sound,
  not a clean one.
- **Velocity and envelopes.** Velocity mapped to harshness as well as level, as a player hits harder for more grit; an
  envelope on the clock (a falling chirp) turns any noise source into a percussive voice.
- **Discrete controls.** Tap sets, masks, rules and formulas are lists that step, each entry named by what it sounds like
  rather than by its number, and ordered from mild to wild.

## 15. Numerical Hygiene and Determinism for Bit Code

- **Integer arithmetic.** Rust panics on integer overflow in debug builds; bit code uses `wrapping_add`, `wrapping_mul`,
  `wrapping_shl` and `wrapping_shr` (whose shift count is taken modulo the width, matching the web-script semantics of
  4.4), and `checked_div` and `checked_rem` with zero for division by zero.
- **Float to integer.** `as` saturates and sends NaN to zero; a wrap or a two's-complement truncation is written out
  (`(x as i64) as i16` wraps for values within the range of `i64`, or `rem_euclid` for larger).
- **Denormals.** Integer sources have none; float feedback, filters and decays do. Flushing (setting the processor's
  flush-to-zero mode at the edge of the audio thread) or adding a tiny constant or seeded noise of about `1e-18` before
  recursive stages (Airwindows injects noise of about `1e-17` times its dither state) keeps the cost steady.
- **Cross-platform determinism.** Integer code is bit-exact everywhere. Float code is exact on one platform and across
  platforms as long as every operation is IEEE-specified (addition, multiplication, division, square root) and no
  library transcendental is used; a polynomial sine and exponential of the engine's own make chaotic and feedback sounds
  identical in every export.
- **Bounded work.** No loop whose count depends on the signal (the `while` quantiser of 13.6), on a formula (bounded at
  compile time, 4.6) or on a clock (registers clocked far above `fs` replaced by noise or a step buffer, 2.8).

## 16. Summary of Costs

Operations per sample per voice, approximate:

| Source or process | Cost |
| --- | --- |
| LFSR below `fs` with band-limited steps | 5 to 15 |
| LFSR above `fs`, box-averaged | 4 per step |
| Clocked or looping random noise with steps | 8 to 15 |
| Filtered noise, two clocks and three SVFs | 40 to 50 |
| Particles, six dusts and band-passes | 40 to 60 |
| Bytebeat at 8 kHz internal, 48 kHz output | 2 to 10 averaged (10 to 60 per evaluation) |
| Bit oscillator, two counters and logic | 5 to 10; 30 to 50 oversampled four times |
| Walsh bank, 16 terms | about 50 |
| Phase distortion | about 8 |
| Chaotic map at a clock | 5 to 20 per tick |
| Cellular automaton row as a table | 3 per sample, a few per generation |
| GENDY, 12 breakpoints | 10 to 20 |
| Glitch from a capture buffer | 10 to 20 |
| Bit damage on the word | 3 to 6 |
| Destroyer chain at two times oversampling | 60 to 80 |

## 17. Sources

Papers and books:

- V.-M. Heikkilä, "Discovering novel computer music techniques by exploring the space of short computer programs",
  arXiv:1112.1368, 2011; and the 2011 essays on one-line music in which the formulas of section 4.2 were collected.
- S. W. Golomb, *Shift Register Sequences*, 1967; W. W. Peterson and E. J. Weldon, *Error-Correcting Codes*, 1972.
- H. T. Nicholas and H. Samueli, phase-accumulator truncation in direct digital synthesis, Frequency Control Symposium,
  1987. F. R. Moore, "Table lookup noise for sinusoidal digital oscillators", Computer Music Journal 1(2), 1977.
- B. A. Hutchins, JAES 21, 1973, and E. Insam, JAES 22, 1974, on Walsh functions in music; H. F. Harmuth, 1969.
- I. Xenakis, *Formalized Music*, 1992; P. Hoffmann, Computer Music Journal 24(2), 2000; M. Serra, Perspectives of New
  Music 31(1), 1993.
- E. R. Miranda, Leonardo 28(4), 1995, on cellular-automaton granular synthesis. M. F. Barnsley, *Fractals Everywhere*,
  1988.

Open implementations read for this chapter, with their licences:

- `pichenettes/eurorack` (MIT): `plaits/dsp/noise/clocked_noise.h`, `plaits/dsp/noise/particle.h`,
  `plaits/dsp/engine/noise_engine.cc`, `plaits/dsp/engine/particle_engine.cc`, `braids/digital_oscillator.cc`
  (`RenderToy`, `RenderClockedNoise`, `RenderDigitalModulation`, the Morse-code `RenderQuestionMark`), `braids/braids.cc`
  (bit and rate reduction).
- `surge-synthesizer/surge` (GPL-3.0-or-later): `src/common/dsp/oscillators/AliasOscillator.cpp`.
- `mtytel/vital` (GPL-3.0-or-later): `src/synthesis/effects/distortion.cpp`.
- `VCVRack/Befaco` (GPL-3.0-or-later, its noise algorithms derived from GPL-3.0-or-later sources, the small
  microcontroller audio library they use under MIT): `src/noise-plethora/plugins/` (`P_LFSRNoise.hpp`, `P_BitShift.hpp`,
  `P_CellularSynth.hpp`, `P_LogisticNoise.hpp`, `P_HenonDust.hpp`, `P_GlitchLoop.hpp` and the cross-modulated pair).
- `clone45/voxglitch` (GPL-3.0): `src/modules/ByteBeat/ByteBeat.hpp`. greggman's `html5bytebeat` (MIT).
- `airwindows/airwindows` (MIT): DeRez2, BitGlitter, Fracture, Disintegrate.
- SuperCollider (its plugin files GPL-2.0-or-later, the project GPL-3.0): `server/plugins/NoiseUGens.cpp` (`Dust`, `Crackle`, `Logistic`, `MantissaMask`),
  `server/plugins/ChaosUGens.cpp` (the chaotic generators), `server/plugins/GendynUGens.cpp`. sc3-plugins (GNU GPL, version 2 or
  later): `source/MCLDUGens/MCLDDistortionUGens.cpp` (`WaveLoss`, `Squiz`).
- Faust libraries (`grame-cncm/faustlibraries`): `noises.lib` (LGPL-2.1-or-later with an exception), `aanl.lib`
  (antiderivative anti-aliased curves). Csound (LGPL-2.1-or-later): the `fold` opcode.
- MAME (`mamedev/mame`, each sound device's licence in its header: BSD-3-Clause for the 1978, 1979 and 1980 chips,
  GPL-2.0-or-later for the 1977 console). Game_Music_Emu and `Blip_Buffer` (LGPL-2.1-or-later). reSID
  (GPL-2.0-or-later).
