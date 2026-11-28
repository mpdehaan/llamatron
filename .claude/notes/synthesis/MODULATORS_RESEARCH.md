# Modulators: Chaos, Function Generators, Shift Registers, Bouncing Balls and Swarms

A chapter on modulation sources beyond the periodic LFO: chaotic systems, slow jerk circuits, the function generator,
the random looping shift register, the bouncing ball, coupled oscillators, smooth random sources, envelope followers,
and the modulation matrix that routes them. Each section gives what a musician hears, the mathematics, a numerically
safe way to run it in a real-time callback (no allocation, no locks, bounded, deterministic), open implementations with
their licences, and the cost. Modulators run at control rate in most uses: once per block of 16 to 64 samples, with
linear interpolation between, which costs almost nothing per sample.

## 1. Integrating Continuous Systems Safely

A chaotic system is a set of ordinary differential equations `dX/dt = F(X)`. In a synthesizer:

- **Integrator.** Fourth-order Runge-Kutta (four evaluations of F a step) is the robust default; at a fixed step h, its
  error is small enough that the attractor keeps its shape. Explicit Euler is cheaper but distorts or destabilises
  stiff systems (Chua, the double pendulum) unless h is tiny. A step of about 0.005 to 0.01 time units suits Lorenz and
  Rössler.
- **Speed.** The musical rate is how many time units pass a second: `h * steps_per_second`. Run a fixed number of RK4
  steps per control block and scale h with the Speed control (within the stable range), or vary the number of steps
  per block for very high speeds.
- **Normalisation.** Each attractor's outputs are rescaled to ±1 by its known extents (Lorenz with the classic
  parameters: x and y within about ±20 and ±27, z from 0 to about 50).
- **Escape and reset.** After every step, if any state is not finite or exceeds a bound (several times the attractor's
  extent), the state is reset to the seed point. Parameter changes can push a system out of its basin; the reset keeps
  the output bounded whatever a person does.
- **Determinism.** The seed point and any noise come from a fixed seed, so that renders repeat exactly; the state is
  never restarted by a note unless asked.
- **Precision.** Double precision for the state; chaotic divergence amplifies rounding, which is harmless (the output
  is still on the attractor) but means two machines differ unless the arithmetic is identical; with the same code and
  no fused-multiply-add differences, results repeat.

## 2. The Chaotic Systems

| System | Equations | Classic parameters | Character |
| --- | --- | --- | --- |
| Lorenz (1963) | `x' = σ(y - x)`, `y' = x(ρ - z) - y`, `z' = xy - βz` | σ = 10, ρ = 28, β = 8/3 | two lobes, flips between them irregularly |
| Rössler (1976) | `x' = -y - z`, `y' = x + a y`, `z' = b + z(x - c)` | a = 0.2, b = 0.2, c = 5.7 | smooth spiral with occasional excursions out |
| Chua's circuit | `x' = α(y - x - h(x))`, `y' = x - y + z`, `z' = -β y` | α = 15.6, β = 28, `h(x) = m1 x + (m0 - m1)(|x + 1| - |x - 1|)/2`, m0 = -1.143, m1 = -0.714 | the electronic double scroll |
| Thomas (1999) | `x' = sin y - b x`, `y' = sin z - b y`, `z' = sin x - b z` | b ≈ 0.208186 | slow, symmetric, labyrinthine |
| Double pendulum | Lagrangian equations of two linked pendulums | equal masses and lengths, energy above the chaotic threshold | swings and sudden flips |
| Lotka-Volterra | `x' = αx - βxy`, `y' = δxy - γy` (two species) | any positive values | periodic, not chaotic: predator and prey cycles |

Notes:

- **A "Chaos" amount** that moves from a near loop to full chaos is most naturally a sweep of one parameter through a
  period-doubling route. In Rössler, c from about 2.5 (a single loop) through 3.5 (period two) and about 4.2 (period
  four) to 5.7 (chaos); in Lorenz, ρ near its periodic windows (around 100) gives loops, 28 full chaos, below about 24.7
  the motion settles to a fixed point. Rössler's route is the smoothest to map to a control.
- **Lotka-Volterra** with two species is a family of closed orbits, never chaotic; four competing species
  (Vano, Wildenberg, Anderson, Noel and Sprott, "Chaos in low-dimensional Lotka-Volterra models of competition",
  Nonlinearity 2006) give chaos. Two-species predator and prey is still a useful, gently lopsided cycle.
- **The double pendulum** is stiff at high energy (fast flips); RK4 with a small step, and a little damping to keep
  energy from creeping upward numerically, keeps it well behaved.
- **Others kept for later**: Sprott's jerk systems, Aizawa, Halvorsen, Dadras, the logistic map `x → r x (1 - x)` and
  Hénon map (discrete, so clocked rather than integrated), the Duffing oscillator (driven, so its drive frequency is a
  musical rate), and the rungler (an 8-bit shift register clocked by one oscillator with its input from another, its
  top three bits a DAC that modulates both: a stepped, semi-repeating pattern).

Cost: RK4 is four evaluations of three equations, about 60 to 100 operations a step; at one or two steps per 32-sample
block, about 3 to 6 operations a sample.

## 3. Slow Jerk Circuits

A jerk system is a single third-order equation `x''' = J(x, x', x'')`, the simplest form of chaos and the easiest to
build as an analog circuit of three integrators and one nonlinearity. Sprott ("Some simple chaotic jerk functions",
American Journal of Physics 1997) found `x''' = -A x'' + x'² - x` chaotic at A = 2.017. Sprott ("A new class of
chaotic circuit", Physics Letters A 266, 2000, 19-23) gives the family `x''' = -A x'' - x' + G(x)` with
piecewise-linear G, among them `G(x) = -B x + C sgn(x)`: a two-lobed attractor that circulates around one centre,
then the other, switching between them at irregular times. Very slow motion, from tens of seconds to tens of minutes
a cycle, is the same circuit with large capacitors and resistors.

### 3.1 The Circuit

Four op-amp stages. Stage 1 is an inverting integrator (capacitor `Cx`) whose output is `x`. From `x`, a resistor
`Rxw` charges a passive node `w`, held by a capacitor `Cw` to ground. From `w`, a path of resistance `K` returns to
stage 1's summing input, and a resistor `Rwy` feeds stage 2, an inverting integrator (`Cy`) whose output is `y`.
Stage 3 inverts `y` with gain `g = Rf/Ri`, giving `z = -g y`. Stage 4 is a comparator, open loop against ground,
whose output `Q` sits at one rail while `z < 0` and at the other while `z > 0`. Both `z` (through `Rzi`) and `Q`
(through `Rq`) return to stage 1. With a knob as a variable resistor inside `K`, the fastest version below at the
knob's lowest is `y''' + 0.6 y'' + y' + y = 0.2128 Q(y)`: Sprott's form with `A ≈ 0.6` and `G(Y) = -B Y + C sgn(Y)`.

Three versions, the slower made by scaling the resistors:

| Version | Cx | Cw | Cy | K (fixed + knob) | Rxw | Rwy | Rzi | Rq | g | B |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Slow | 2 µF | 50 µF | 1 µF | 100k + 10k | 100k | 100k | 1M | 4.7M | 1 | 1.00 to 1.15 |
| Slower | 2 µF | 50 µF | 1 µF | 1M + 100k | 1M | 1M | 6.8M | 14.7M | 1 | 1.47 to 1.70 |
| Slowest | 2 µF | 40 µF | 1 µF | 10M, no knob | 10M | 10M | 68M | 100M | 1.5 | 1.97 |

The knob raises B. A larger g in the slowest version (2.2, then 3.3) shortens its cycle and then makes it periodic.

### 3.2 The Equations

The state is the charge voltage on `Cx` (`Vcx`), the node `w`, and the charge voltage on `Cy` (`Vcy`). The op-amps'
outputs saturate, and while one is at its rail its summing node leaves virtual ground: the integrator's output is the
charge clipped, and the summing node carries the difference.

```
sat(v) = clamp(v, -10, +10)                 # the linear stages' swing, in volts
x = sat(Vcx);  vx = x - Vcx                 # vx is 0 unless stage 1 is at a rail
y = sat(Vcy);  vy = y - Vcy
z = sat(-g y)
Q = +11.38 if z < 0 else -10.64             # the comparator's rails, as measured on one build
K = Kfixed + Kknob * knob                   # knob from 0 to 1

dVcx/dt = -[ (z - vx)/Rzi + (Q + bias - vx)/Rq + (w - vx)/K ] / Cx
dw/dt   =  [ (x - w)/Rxw + (vx - w)/K - (w - vy)/Rwy ] / Cw
dVcy/dt = -(w - vy) / (Rwy Cy)
```

The saturation is part of the instrument, not a nicety. Without it only the fastest version stays bounded: the
slower two are linearly more unstable (their larger B) and run off to infinity, the rails holding them in the
circuit. The middle version spends about 4% of its time at a rail and the slowest about 32%, the slowest's `z` coming
out squarish, with long flat tops. A model that only slows the fastest version down cannot sound like the others.

The outputs are `x`, `y` and `z` (`-y`, clipped, where g is 1). Their ranges, to divide by for -1 to +1:

| Version | x | y | z |
| --- | --- | --- | --- |
| Slow | ±2.8 | ±6.0 | ±6.0 |
| Slower | ±7 | ±10 | ±10 |
| Slowest | ±6.5 | ±10 | ±10 |

### 3.3 Behaviour

Simulated by RK4 over 10⁵ to 10⁷ seconds, a cycle being the mean time between two switches of lobe:

- **Slow**: a cycle of about 21 seconds; time on a lobe irregular, from 3.5 to 19 seconds between the 10th and 90th
  percentiles; two starts a hair apart part ways with an e-folding time of about 8 seconds; never at a rail.
- **Slower**: about 106 to 134 seconds across its knob, chaotic for most of it, one or several turns a visit; at the
  knob's top it locks into a periodic 65-second cycle. Its fine behaviour depends on the rails: at ±10.5 to ±10.8 V
  it turns periodic, so it differs from one built unit to the next.
- **Slowest**: about 31 minutes, chaotic.

**The knob weights the lobes only weakly.** In the fastest version the share of time on the upper lobe moves from
about 54% to 56% across the knob, and that little comes only from the comparator's unequal rails; in the middle
version the knob mostly changes the time a visit takes. Outside the knob's range the circuit sticks on one lobe or
turns periodic, so the knob is clamped to its range.

**A bias on the comparator's rails** weights the lobes strongly: an offset added to `Q` (one resistor into stage 1's
summing node) of -1.5 V to +1.5 V moves the upper lobe's share from 36% to 67% in the fastest version, 47% to 75% in
the middle one and 37% to 84% in the slowest, every version staying chaotic at every bias (two starts a hair apart
always parting) and its cycle near its own: the fastest 18 to 21 seconds, the middle 111 to 133, the slowest 31 to
39 minutes. At a bias of zero the circuit is exactly the one above.

### 3.4 Running It in Real Time

- **A fixed clock.** A chaotic system magnifies any difference, so the circuit is stepped on a time grid of its own,
  never the sample rate's or a chunk's: otherwise real-time playback and an export would part ways within minutes.
  RK4 at 2.5 ms for the fastest, 25 ms for the middle and 250 ms for the slowest (results unchanged from 1 to 50 ms
  in the fastest); each sample reads a straight line between grid points, so nothing it moves steps. The system is
  not stiff, so no implicit method is needed; it is dissipative, so symplectic methods do not apply. Over minutes no
  integrator, nor the circuit, follows one exact path: what is kept is the statistics and the bounds.
- **The same on every computer.** f64 and plain `+ - × /`, `min` and `max` only, never a fused multiply-add or a
  reordering, so that IEEE arithmetic gives the same bits everywhere. A setting moved by modulation is read at grid
  times.
- **Seeding.** Start from `(0, w0, 0)`, `w0` drawn in ±0.03 V from the instrument's, the slot's and the circuit's
  seed, then run two to six cycles of warm-up so the circuit starts on its attractor rather than in the slowest
  version's half-hour spiral outward (under a millisecond).
- **Starting mid-song**: step forward from the song's start, about 12 ms for ten minutes of the fastest version.
- **Guard**: with the rails, `|x|, |y| ≤ 10` and `|w| ≲ 1.5`. A value not finite, `|w| > 12` or `|Vc| > 30` restarts
  the circuit from its seed with a counter mixed in. `K` never falls below its fixed part.
- **Cost**: about 50 ns an RK4 step, so about 25 µs a second of sound per instrument for all three circuits.

### 3.5 Open Implementations

An open derivation of the fastest version from its schematic is published without a licence, so only its ideas are
used. A port to the open VCV Rack platform (CC0-1.0) holds that engine, its two slower versions being the fastest
slowed by fixed factors rather than their own circuits.

## 4. The Function Generator

A function generator produces rise-and-fall shapes: a ramp up over a rise time, down over a fall time, looping (an
LFO), once per trigger (an attack-decay envelope), or held while a gate is high (attack-release). Its controls:

- **Rate and Slope.** The period, and the share of it spent rising (0 % a falling saw, 50 % a triangle, 100 % a rising
  saw).
- **Shape (bend).** Each segment curved from logarithmic through linear to exponential: a waveshaper on the segment's
  phase, such as `(exp(k p) - 1)/(exp(k) - 1)` with k from negative to positive.
- **Smoothness.** One way a low-pass (rounding toward a sine), the other a wavefolder (adding harmonics): one control
  spanning dull to bright.
- **Several related outputs.** Four outputs with different shapes, phases (each shifted by a share of the cycle) or
  frequency ratios (each a ratio of the base rate), spread by one control, so one module gives a family of related
  modulations.
- **At audio rate** the same generator is an oscillator; its slope and shape changes must narrow at high frequencies
  to keep the corners from aliasing (BLAMP corrections or a limit on slope sharpness by frequency).

`pichenettes/eurorack`, `tides2/` (MIT) is a complete open function generator of this kind, with ramp generation,
shaping, output relations and its audio-rate anti-aliasing. Cost: a phase, a shaping curve or table read per output,
about 10 to 20 operations an output, at control or audio rate.

## 5. The Random Looping Shift Register

A shift register of 8 or 16 bits rotates one place at each clock; the bit that falls off the end comes back in at the
start, possibly flipped. A "Change" control is the probability of flipping: at zero the pattern loops exactly (a fixed
melody or rhythm of the register's length); at one half it is random; at one the bit always flips, so the loop
inverts each pass and repeats every two lengths. Between, the loop evolves slowly, keeping most of its shape. The
output is the register's top bits as a number (a DAC), scaled to a modulation range, and individual bits or bit
combinations as gates. The open-hardware random looping sequencer of the 2010s made this the popular way to generate
"almost repeating" melodies.

A related idea in `pichenettes/eurorack`, `marbles/random/random_sequence.h` (MIT): a loop of stored random values
replayed with a "déjà vu" probability of replacing each with a fresh draw, and the loop length chosen separately; and
`marbles/random/lag_processor.cc` for smoothing the steps. Cost: a few integer operations per clock.

## 6. The Bouncing Ball

A ball dropped from height h with a coefficient of restitution e (0 to 1) bounces with heights `h e^(2k)` and intervals
`t_k = t_0 e^k`, the first interval `t_0 = 2 sqrt(2 h / g)`; it comes to rest after a total time `t_0 / (1 - e)`. As a
modulator: a trigger at each bounce (an accelerating ratchet), the ball's height as a continuous output (a falling,
rhythmic sweep), and the bounce number as a step value. Controls are the drop height (sets the first interval, best
expressed directly as a time or a tempo division), the restitution (how quickly the bounces shrink and speed up), and
gravity as a scaling. It restarts at each note. Exact in closed form: the time of the k-th bounce is
`t_0 (1 - e^k)/(1 - e)`, so no integration is needed and the result does not depend on block boundaries. Cost: a
comparison and a few multiplies per block.

## 7. Coupled Oscillators: the Kuramoto Model

N oscillators with natural frequencies `ω_i` pull each other into step:
`dθ_i/dt = ω_i + (K/N) Σ_j sin(θ_j - θ_i)` (Kuramoto, 1975). Below a critical coupling (for a spread of natural
frequencies with density g, `K_c = 2 / (π g(0))`) they drift independently; above it a growing share locks together;
the order parameter `r e^{iψ} = (1/N) Σ e^{iθ_j}` measures how synchronised they are (0 none, 1 all). Moving K slowly
across `K_c` makes four slow LFOs drift into step and back out. The mean-field form is cheap: compute `r` and `ψ` once a
step, then `dθ_i/dt = ω_i + K r sin(ψ - θ_i)`, so N oscillators cost O(N), not O(N²). Euler integration at control rate
is adequate because the dynamics are slow and smooth. Outputs are `sin θ_i` (or other shapes of each phase) and `r`.
Cost: a few operations per oscillator per block.

## 8. Smooth Random, Noise and Followers

- **Smoothed random.** New random targets at a rate, approached through a one- or two-pole smoother (`marbles/random/
  lag_processor.cc`, MIT), or interpolated by a cosine; a two-pole smoother keeps the derivative continuous, so the
  modulation never kinks.
- **Pink and brown noise.** Pink (1/f) noise by the Voss-McCartney algorithm (several random generators updated at
  octave-spaced rates and summed) or by filtering white noise with a few one-poles (Paul Kellett's published
  coefficients); brown by integrating white noise with a slight leak. As slow modulators, they wander naturally.
  `sst-basic-blocks/dsp/PinkNoise.h` and `CorrelatedNoise.h` (GPL-3.0-or-later).
- **Envelope followers.** A rectifier (absolute value or square) and a one-pole with separate attack and release
  coefficients (`|x| > y ? attack : release`), or an RMS follower over a window; outputs a level from the audio for
  ducking, auto-wah and "envelope to anything".
- **Slew limiters.** A maximum rate of change in each direction, the analog "lag" or "portamento" processor, turning
  steps into ramps.

## 9. The Modulation Matrix

A list of routes, each a source, an optional scaling "via" source, a destination and an amount. Practical points for
a callback:

- **Compiled routes.** Routes are resolved to indices into a source array and a destination array when the instrument
  is built, empty routes dropped, so the run-time loop is a flat list of multiply-adds.
- **Rates.** Sources evaluated at control rate (LFOs, envelopes, modulators) and sources at audio rate (oscillators
  used as modulators) are separated: control-rate routes are summed once a block and interpolated, audio-rate routes
  per sample only where present.
- **Units.** Each destination has a natural unit (pitch in semitones, cutoff in octaves, levels in decibels or linear,
  times in octaves of their value) so that one amount scale feels even across destinations.
- **Smoothing.** Destinations that click when stepped (levels, pan, delay times) take a smoother after the summation.
- **Per-voice and global.** A note's own sources (its envelopes, velocity, key) are per voice; global sources (an
  LFO shared by the instrument, a chaotic modulator) are computed once and read by every voice.
- `sst-basic-blocks/mod-matrix/` (GPL-3.0-or-later) is an open, header-only matrix designed for real-time use, with
  compile-time-sized storage and per-voice and monophonic routing.
