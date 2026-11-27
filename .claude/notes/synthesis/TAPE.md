# Magnetic Tape and Its Machines

A chapter on how analog tape records and plays sound, what it does to the sound, and how open implementations model it
in real time: the physics, the algorithms, their costs, and the details that matter for a per-instrument effect run a
sample at a time in an audio callback that must not allocate or lock. Machines are described generically. Open projects
are named with their licences; papers are cited by author, title and year.

## 1. The Path Through a Tape Machine

A recording passes through three physical stages and two electrical ones:

1. **Record amplifier and record equalisation.** The signal is boosted in the treble (pre-emphasis) to make up for losses
   to come, and a strong ultrasonic **bias** current, typically 40 to 150 kHz and several times the signal's amplitude,
   is added to it.
2. **Record head and tape magnetisation.** The head's gap fringes a field into the moving oxide. The oxide's
   magnetisation follows the field through a **hysteresis loop**: the material remembers where it has been, saturates
   at its limit, and on its own would leave a dead zone around zero. The bias sweeps the particles round many minor loops
   for each audio cycle, which linearises the low-level transfer (anhysteretic recording).
3. **Transport.** The capstan and pinch roller pull the tape at a nominal speed; every imperfection of their roundness,
   of the motors, of the reels and of the tape's own elasticity becomes a change of speed, heard as **wow and flutter**.
4. **Play head.** The play head senses the rate of change of the recorded flux. Its output is shaped by **loss effects**
   that depend on recorded wavelength, so on tape speed: spacing loss, gap loss, thickness loss, and at long wavelengths
   the **head bump** of the contour effect.
5. **Playback equalisation.** An integrator turning over at the standard's time constant undoes the head's rising
   response, and with the record equalisation leaves the chain nominally flat. Noise recorded onto the tape passes
   through this equalisation too, which gives tape hiss its colour.

A model that keeps this order keeps the relationships that make tape sound like tape: the treble saturating before the
bass (because pre-emphasis sits before the nonlinearity), hiss rising in the treble (because it is added between the
emphasis and the de-emphasis), and every frequency effect moving with the speed (because each is a function of
wavelength, `λ = v / f`).

## 2. Wavelength, the Variable Behind Everything

The recorded wavelength is the tape speed divided by the frequency. At 10 kHz:

| Speed (inches per second) | Wavelength at 10 kHz | Typical use |
| --- | --- | --- |
| 30 | 76 µm | multitrack studio mastering |
| 15 | 38 µm | studio multitrack and mastering |
| 7.5 | 19 µm | semi-professional and home reel-to-reel |
| 3.75 | 9.5 µm | home reel-to-reel, long play |
| 1.875 | 4.8 µm | compact cassette |
| 0.9375 | 2.4 µm | dictation microcassette (one speed of two) |

Every short-wavelength loss is a function of a physical length divided by λ, so halving the speed doubles every loss in
decibels at a given frequency, or equivalently moves every loss curve down an octave. This single fact is why a speed
control must move the treble roll-off, the head bump, the high-frequency headroom and the noise together.

## 3. Hysteresis and Saturation

### 3.1 The Jiles-Atherton Model

D. C. Jiles and D. L. Atherton, "Theory of ferromagnetic hysteresis", Journal of Magnetism and Magnetic Materials 61,
1986, describe magnetisation `M` under field `H` by an anhysteretic curve and a pinning term:

- Effective field `He = H + α M`, and `Q = He / a`.
- Anhysteretic magnetisation `Man = Ms L(Q)`, with the Langevin function `L(x) = coth(x) - 1/x` (series `x/3` near zero).
- The differential equation, in the time-domain form used by M. Holters and U. Zölzer, "Circuit simulation with
  inductors and transformers based on the Jiles-Atherton model of magnetization", DAFx 2016, and by J. Chowdhury,
  "Real-time physical modelling for analog tape machines", DAFx 2019:

```
dM/dt = [ (1-c) δM (Man - M) / ((1-c) δ k - α (Man - M))  +  c (Ms/a) L'(Q) ] · dH/dt
        / [ 1 - c α (Ms/a) L'(Q) ]
```

where `δ = sign(dH/dt)`, `δM` is 1 when `δ` and `Man - M` agree in sign and 0 otherwise, and
`L'(x) = 1/x² - coth²(x) + 1` (one third near zero). The parameters are `Ms` (saturation magnetisation: the ceiling),
`a` (the anhysteretic curve's width: how soon it bends, so effectively the drive), `α` (interdomain coupling), `k`
(coercivity: the loop's width) and `c` (reversibility: the share of the change that is reversible, which narrows the
loop as it rises).

What is heard: a soft, mostly odd-harmonic saturation whose curve depends on the direction the signal is travelling,
so that the transfer is a loop rather than a line. That memory adds a small level- and frequency-dependent phase lag and
a gentle low-level softening, and is the difference between "tape" and a static soft clipper. It is most audible on
low-frequency, high-level material, where the loop is traversed slowly and widely.

### 3.2 Discretisation and Solvers

The equation is driven by `H` and its derivative, so the derivative must be estimated from samples. The DAFx 2019 paper
uses the trapezoidal rule, `Ḣ[n] = 2 (H[n] - H[n-1]) / T - Ḣ[n-1]`; the current CHOW Tape Model source (AnalogTapeModel,
GPL-3.0, `Plugin/Source/Processors/Hysteresis/HysteresisOps.h`) uses an alpha-transform with `α = 0.75`,
`Ḣ[n] = ((1 + α) / T) (H[n] - H[n-1]) - α Ḣ[n-1]`, which damps the trapezoid's tendency to ring at the Nyquist
frequency. The paper notes the trapezoid makes the system unstable for input at Nyquist without oversampling.

The solvers in that source (`HysteresisProcessing.h`), each per oversampled sample:

| Solver | Evaluations of dM/dt | Notes |
| --- | --- | --- |
| RK2 (midpoint) | 2 | explicit; half-step values of H and Ḣ by averaging; the plugin's default mode |
| RK4 | 4 | explicit; the DAFx 2019 paper's solver |
| Newton-Raphson, 4 iterations | 1 + 4 × (function and its derivative) | implicit trapezoidal, step `T/1.9` in the code |
| Newton-Raphson, 8 iterations | 1 + 8 × (function and its derivative) | the most accurate and costly |
| State transition network | a small neural network | trained per bias width (JSON models in the source); after J. Parker, F. Esqueda and A. Bergner, "Modelling of nonlinear state-space systems using a deep neural network", DAFx 2019 |

Each evaluation of `dM/dt` costs one hyperbolic tangent (for `coth`), three or four divisions and some twenty-five
multiplications. On a current desktop core in double precision that is roughly 50 to 80 cycles. The paper replaces
`tanh` by a Gaussian continued fraction, `x / (1 + x²/(3 + x²/(5 + x²/7)))`, to save time; a rational approximation of
this kind is accurate to about 1e-4 over the useful range and costs a division and a handful of multiplications.

Safeguards in that source, each needed in any implementation:

- The input is clipped before the solver (±8 for RK2, ±10 for RK4, ±12.5 for Newton-Raphson, ±20 for the network),
  because the explicit solvers diverge on large steps.
- After each sample, a result that is not a number or exceeds an upper limit resets `M` and `Ḣ` to zero, so one bad
  sample cannot poison the state forever.
- A DC blocker follows, since the loop's memory can leave a small offset.
- Makeup gain is computed from the saturation and width settings, so that changing the character does not change the
  level drastically: `(1 + 0.6 width) / (0.5 + 1.5 (1 - sat))`.

The mapping from musical controls to the model in that source (`cook`): `Ms = 0.5 + 1.5 (1 - sat)`,
`a = Ms / (0.01 + 6 drive)`, `c = sqrt(1 - width) - 0.01`, `k = 0.47875`, `α = 1.6e-3`. The control named "bias" there
sets the loop width `c` rather than injecting a bias tone; the earlier mode that did inject a real bias sine needs very
high oversampling (the paper used 16 times, since the modelled machine biased at 55 kHz).

### 3.3 A Cheaper Jiles-Atherton

The Faust libraries' `hysteresis.lib` (Thomas Mandolini, with Bart Brouns; LGPL-2.1-only, whose section 3 allows use
under GPL version 2 or later, so it can be combined with GPL-3.0 code) takes a lighter route in `ja_hysteresis`:

- `tanh` stands in for the Langevin function, and `1 - tanh²` for its derivative: one transcendental a step.
- The update is a forward-Euler step in `dH` rather than `dt`: `dM = dM/dH · (H_target - H_prev)`, so no time derivative
  is estimated at all and the Nyquist instability of the trapezoid does not arise.
- The difference from the anhysteretic curve is soft-clamped, `diff / (1 + 3 |diff|)`, and the pinning denominator is
  kept off zero by a small constant, which makes the explicit step stable without clipping the input.
- Four substeps a sample, at H values interpolated by a cubic Hermite (Catmull-Rom tangents) between the last two
  samples: a cheap form of oversampling for the state, though the output is still at the base rate, so it does not
  remove the aliasing of the output's harmonics.
- `M` is clamped to ±1, a 7 Hz second-order high pass removes DC, and the gain is normalised by the small-signal slope
  `c Ms / a`.

Cost: four `tanh` and four divisions a sample, about 120 to 200 cycles at the base rate.

### 3.4 Memoryless Saturation and Aliasing

Where the loop's memory is not wanted, a static curve with antiderivative antialiasing gives most of tape's saturation
for little cost. First-order antiderivative antialiasing (J. Parker, V. Zavalishin and E. Le Bihan, "Reducing the
aliasing of nonlinear waveshaping using continuous-time convolution", DAFx 2016; S. Bilbao, F. Esqueda, J. Parker and
V. Välimäki, "Antiderivative antialiasing for memoryless nonlinearities", IEEE Signal Processing Letters, 2017) outputs
`(F(x[n]) - F(x[n-1])) / (x[n] - x[n-1])`, where `F` is the curve's antiderivative, falling back to `f` at the midpoint
when the two inputs are within a small epsilon. For `tanh`, `F(x) = ln(cosh(x))`, computed for large `|x|` as
`|x| - ln 2 + ln(1 + e^(-2|x|))` to avoid overflow. It adds half a sample of delay and costs one logarithm and one
exponential more than the bare curve; about 20 dB of aliasing reduction on bright material. The Faust `aanl.lib`
(Dario Sanfilippo, MIT) holds general first- and second-order forms.

The alternative is oversampling: two times with a linear-phase halfband (a windowed-sinc interpolator and decimator run
as two polyphase branches) costs some 25 to 50 multiply-adds a sample in and out, and doubles the nonlinearity's cost.
Two times is enough for gentle tape saturation, whose harmonics fall away quickly; the RK solvers above are usually run
at two times as well.

### 3.5 A Cheap "Tiny Hysteresis"

Airwindows (Chris Johnson, MIT) uses a simpler memory term in ToTape9 (its `ToTape9Proc.cpp`): an accumulator of `x |x|`, clamped to ±0.011449 and leaking by
0.999 a sample, is added back to the signal scaled by `0.012 (1 - |x|)²`. It costs a few operations, makes the curve
depend slightly on the signal's recent history, and is audible mainly as a faint low-level thickening rather than a
true loop.

### 3.6 Bias as a Musical Variable

On a real machine the bias level is set at alignment:

- **Under-bias**: more distortion at low and middle levels (the dead-zone crossover distortion of unbiased recording
  shows through), more treble, a brighter and grittier sound.
- **Correct bias**: commonly set to the peak of sensitivity at a mid frequency, then increased by a set amount ("over-
  biasing" by 2 to 4 dB at 10 kHz at 15 ips is a common studio practice), trading a little treble for the least
  distortion.
- **Over-bias**: lower distortion, less treble, and lower high-frequency headroom; duller and smoother.

Two ways to model it without simulating the ultrasonic tone: change the loop width (as in the CHOW source, where less
bias means a wider, more coercive loop); or, as ToTape9 does, use slew-rate limiters. ToTape9's over-bias is a chain of
nine slew limiters whose thresholds grow by the golden ratio, which rounds off fast transients (less treble); its
under-bias makes the signal "stick" near its previous values, with a strength `bias⁴ / 4`, which models the dead zone.

## 4. The Play Head: Loss Effects and Head Bump

### 4.1 Wallace's Loss Terms

For a sinusoidal recording of wave number `k = 2π f / v`, the play voltage carries three frequency-dependent factors
(R. L. Wallace Jr., the reproduction of magnetically recorded signals, 1951; H. N. Bertram, "Theory of Magnetic
Recording", 1994; J. Kadis, "The Science of Sound Recording", 2012):

- **Spacing loss** `e^(-k d)`, for head-to-tape spacing `d`: 54.6 dB per wavelength of spacing. It is the largest and
  most variable loss; dust, oxide shed, a worn pressure pad, a crinkled tape or a dirty head all raise `d`.
- **Thickness loss** `(1 - e^(-k δ)) / (k δ)`, for coating thickness `δ`: deep layers of the oxide contribute less at
  short wavelengths.
- **Gap loss** `sin(k g / 2) / (k g / 2)`, for play gap `g`: a sinc whose first null falls where the wavelength equals
  the gap. Play gaps are around 1 to 5 µm, so the null sits above the audio band at studio speeds and comes near it only
  at the slowest speeds.

Spacing loss at 10 kHz for 1 µm of spacing, from `54.6 d / λ`:

| Speed | Loss at 10 kHz from 1 µm spacing |
| --- | --- |
| 30 ips | 0.7 dB |
| 15 ips | 1.4 dB |
| 7.5 ips | 2.9 dB |
| 3.75 ips | 5.7 dB |
| 1.875 ips | 11.5 dB |

This table is the physical reason a cassette is so sensitive to wear and dirt: the same speck that a studio machine
shrugs off takes 10 dB from a cassette's treble. A single "age" or "wear" quantity expressed as microns of spacing
therefore produces the right speed dependence by itself.

A real machine is aligned so that its record equalisation makes the overall response flat at a low reference level up to
its rated limit; a model that applies the full physical losses without the compensating record boost comes out far too
dull. Modelled losses are best understood as what remains after alignment: the rated roll-off of the speed, plus any
extra spacing from wear.

### 4.2 Realising the Losses as a Filter

The CHOW source (`Loss_Effects/LossFilter.cpp`) samples the product of the three terms on a frequency grid, takes its
inverse DFT to a linear-phase FIR of order 64 at 44.1 kHz (scaled with the rate), and crossfades between two filters
over 1024 samples when a parameter changes. Its defaults are small (spacing 0.1 µm, thickness 0.1 µm, gap 1 µm), which
keeps it near flat. A 64-tap FIR costs about 64 multiply-adds a sample and adds 32 samples of latency.

Because the spacing term is an exponential in frequency (a straight line in decibels against linear frequency), and the
other two are smooth, the whole product is well matched by a low-order minimum-phase IIR: one or two one-pole or
second-order low-pass sections fitted at a few frequencies, about 5 to 20 operations a sample, without latency.
Coefficients depend only on the settings, so they are computed once when the effect is made; a smoothly varying loss (a
dropout, a crinkle) moves only one section's cutoff, recomputed at a control rate of one update per 16 to 64 samples.

### 4.3 Head Bump

At long wavelengths, comparable to the length of the play head's contact face and its shields, the head picks up flux
from beyond its gap, and the low-frequency response ripples: a broad lift (the head bump), a dip below it, and smaller
ripples above. The bump is a function of wavelength, so its frequency scales with speed. Typical published magnitudes:
a lift of about 1 to 3 dB, centred roughly at 25 to 40 Hz at 7.5 ips, 40 to 70 Hz at 15 ips and 60 to 120 Hz at
30 ips, with the dip half an octave to an octave below. The exact frequencies depend on the head's geometry; these
figures are approximate and best tuned by ear. If `L` is an effective contact length, the bump sits near `f ≈ v / L`;
an `L` of about 6 mm puts it at 60 Hz at 15 ips.

How the open projects draw it:

- The CHOW source uses a peaking biquad of Q 2 at `f = v / (500 g)` with gain `max(1.5 (1000 - |f - 100|) / 1000, 1)`:
  a heuristic tied to the gap setting rather than to the head's length, which places the bump high unless the gap is
  set large.
- Airwindows ToTape9 feeds a saturating integrator (`b += x · drive; b -= b³ · 0.0618`) through two cascaded band-pass
  biquads tuned between 25 and 200 Hz (the second at 0.9375 of the first's frequency, Q 0.618), and mixes the result
  back in. The integrator's cubic term makes the bump compress at high levels, which tape also does.

A practical drawing is a peaking filter at the speed's bump frequency plus a gentle second-order high pass below the
dip, both computed once from the speed: about 10 to 15 operations a sample.

## 5. Equalisation Standards and Their Time Constants

Equalisation is specified by playback time constants; the corner frequency is `1 / (2π τ)`.

| Use | High-frequency τ | Corner | Low-frequency τ |
| --- | --- | --- | --- |
| 30 ips, the international studio curve | 17.5 µs | 9.1 kHz | none |
| 15 ips, international (IEC) | 35 µs | 4.5 kHz | none |
| 15 ips and 7.5 ips, North American | 50 µs | 3.2 kHz | 3180 µs (50 Hz) |
| 7.5 ips, international | 70 µs | 2.3 kHz | none |
| 3.75 ips | 90 µs | 1.8 kHz | 3180 µs |
| Cassette, ferric (Type I) | 120 µs | 1.3 kHz | 3180 µs |
| Cassette, chrome and metal (Type II, IV) | 70 µs | 2.3 kHz | 3180 µs |

Two consequences matter for a model:

- **High-frequency headroom.** The record side boosts the treble above the corner by up to the inverse of the playback
  cut, so a treble-heavy signal reaches the oxide's limit sooner. The maximum output level at 10 kHz is often 10 dB or
  more below that at 400 Hz on a ferric cassette, a few decibels below at 15 ips. A pre-emphasis shelf before the
  saturator and its exact inverse after reproduces this: flat at low level, the treble compressing first as level
  rises. The CHOW source does the same with a pair of mirrored shelves around its hysteresis (`ToneControl.cpp`,
  transition at 500 Hz by default).
- **The colour of hiss**, below.

## 6. Noise

### 6.1 Hiss

Tape noise comes from the random size and placement of the magnetic particles. Recorded flux noise is roughly white;
the play head differentiates it (+6 dB per octave) and the playback integrator cancels that below its corner but not
above it, so hiss at the output is flat below the corner and rises about 6 dB per octave above it, until the play
losses bring it down. Its spectrum therefore follows the equalisation standard: a ferric cassette's 120 µs corner gives
its bright, airy hiss from 1.3 kHz up; 15 ips at 35 µs rises only above 4.5 kHz.

A faithful and cheap realisation: Gaussian or uniform white noise through a first-order high shelf turning over at the
standard's corner, added between the saturator and the playback losses, so that the loss filters, the head bump and any
dropout shape the hiss as they shape the music. Cost: a random number (an xorshift and a conversion), one shelf, one
add: about 8 to 12 operations.

Typical unweighted signal-to-noise ratios relative to the reference operating level, without companding noise
reduction, as a guide to levels: a studio machine at 15 or 30 ips about 60 to 68 dB on wide tracks; 7.5 ips about 55 to
62 dB; a good cassette deck 50 to 56 dB on ferric tape; a cheap portable 42 to 50 dB. Narrower tracks are noisier, by
about 3 dB for each halving of the width. The reference operating level sits well below the clipping point (on the
order of 8 to 12 dB below the 3% distortion point for studio tape, fewer for cassette), so in a digital model the noise
floor relative to full scale is the ratio above plus that headroom.

### 6.2 Modulation Noise

Tape also adds noise that rides on the signal: particle clumping and surface roughness (asperities) modulate the
recorded level and the head-tape contact, so a loud sustained tone carries a halo of noise in sidebands around it.
Scrape flutter (6.3) adds to it. It is modelled as the signal multiplied by `1 + n(t)`, with `n` a low-level band-limited
noise, or as noise scaled by an envelope follower of the signal. The CHOW source's Degrade stage offers the second form:
uniform noise multiplied by a level detector's output, its envelope time set from 20 ms to 5 s.

### 6.3 Generation Loss

Each dub onto another tape adds that tape's noise (powers add: two equal generations are 3 dB noisier), applies its
losses again (decibels add), compounds its saturation, and adds an independent set of speed errors (deviations add in
power: two equal generations about 1.4 times the wow). The rule of thumb in studios was that each generation cost
about 3 dB of signal-to-noise and a little treble, which is why masters were copied as few times as possible.

## 7. Wow and Flutter

### 7.1 Definitions and Measurement

Wow and flutter are periodic and random variations of tape speed, heard as variations of pitch. Conventionally wow is
the slow part (below roughly 4 Hz, some definitions say 6 or 10) and flutter the fast part (up to about 100 to 200 Hz).
The international measuring standard (IEC 60386, also DIN 45507 and AES6) reads a 3150 Hz test tone through a weighting
filter that peaks at 4 Hz, where the ear is most sensitive to pitch modulation, and reports a weighted peak or a
weighted root-mean-square figure. Weighted RMS reads roughly half the weighted peak for the same machine, so figures
must be compared in the same convention.

Typical weighted figures as published for working machines in good order:

| Machine | Weighted wow and flutter |
| --- | --- |
| Studio reel-to-reel, 30 or 15 ips | 0.02 to 0.07% |
| Home or semi-professional reel-to-reel, 7.5 ips | 0.04 to 0.1% |
| Home reel-to-reel, 3.75 ips | 0.08 to 0.2% |
| Good home cassette deck | 0.03 to 0.1% |
| Cheap or portable cassette player | 0.15 to 0.4% |
| Worn portable, failing belt or stretched tape | 0.5 to several % |

The threshold of audibility for slow wow on sustained piano tones is commonly given as around 0.1 to 0.2% peak;
flutter in the 4 to 10 Hz region is heard as a vibrato-like warble; above about 20 Hz it is heard less as pitch and more
as roughness or a loss of clarity.

### 7.2 Mechanical Sources and Their Rates

Each rotating part contributes a component at its own rotation rate, `f = v / (π D)` for a part of diameter `D` in
contact with tape moving at `v`, plus harmonics when it is out of round in more than one way:

- **Capstan** eccentricity: the main periodic flutter. A 2.4 mm capstan at 1.875 ips turns about 6.3 times a second; on
  a reel machine with a 25 mm capstan, 15 ips gives about 4.8 Hz, 30 ips about 9.5 Hz. Direct-drive studio capstans are
  usually larger and very round, so their component is small.
- **Pinch roller** eccentricity or a flat spot: slower, at the roller's rate (a 10 mm roller at 1.875 ips turns about
  1.5 times a second), often with a sharp, once-per-turn character from a flat or a groove.
- **Flywheel and belt** (cassette): belt stretch, slip and joins add slow, irregular wow and once-per-belt-turn bumps.
- **Reels and tape pack**: the reel turns at a rate set by the pack radius, which changes over the length of the tape
  (a cassette's hub runs from about 0.3 to 0.8 turns a second); an eccentric or unevenly wound pack, or back-tension
  that varies, adds wow at that slowly changing rate.
- **Motor cogging and servo hunting**: tones at the motor's pole rate and a slow hunting of the speed servo.
- **Drift**: a slow random wander of the mean speed from temperature, supply voltage and tension, over seconds.
- **Scrape flutter**: the tape stretched between guides and heads vibrates lengthwise like a string, excited by
  stick-slip friction at the heads, at about 1 to 5 kHz. The speed variation is tiny (a 0.05% deviation at 3 kHz is a
  delay excursion of about 25 ns), so it is heard not as pitch but as sidebands: modulation noise, a fine fuzz around
  tones. Studio machines add a scrape-flutter idler between the heads to damp it.

In a stereo or multitrack machine every track passes the same capstan at the same moment, so wow and flutter are nearly
identical across channels; only azimuth and tape skew separate them (section 10). Decorrelated wow between channels is a
creative widening, not a property of real tape.

### 7.3 Speed Variation as a Time-Varying Delay

A playback speed ratio `r(t) = 1 + ε(t)` reads the recording at time `τ(t) = ∫ r dt`, which an effect realises as a delay
line read `d(t)` samples behind the write point, with `ε(t) = -d'(t)`: a growing delay lowers the pitch, a shrinking one
raises it. For a sinusoidal component of delay amplitude `A` seconds at rate `f`, the peak speed deviation is
`2π f A`; conversely a target peak deviation `p` at rate `f` needs `A = p / (2π f)`:

| Peak deviation | Rate | Delay amplitude | At 48 kHz |
| --- | --- | --- | --- |
| 0.05% | 0.5 Hz | 0.16 ms | 7.6 samples |
| 0.1% | 5 Hz | 0.032 ms | 1.5 samples |
| 0.5% | 8 Hz | 0.10 ms | 4.8 samples |
| 2% | 0.5 Hz | 6.4 ms | 306 samples |
| 3% | 0.3 Hz | 15.9 ms | 764 samples |

Three consequences:

- The same delay depth at a slower rate is a smaller pitch change; specifying wow by delay depth (as both open projects
  below do) makes the heard depth change when the rate changes. Specifying it as a pitch deviation and computing the
  delay amplitude keeps the heard depth fixed as the rate moves.
- A delay cannot be negative, so the modulation is centred on a base delay at least as large as the largest excursion,
  plus the interpolator's look-ahead. The effect's latency is that base delay: well under a millisecond for studio
  flutter, 15 to 30 ms for extreme wow. The line's length is fixed by the largest supported excursion, so it is
  allocated once when the effect is made.
- Generating a speed signal and integrating it gives a delay that random components would make drift without bound (a
  random walk); generating the delay directly from bounded components (sines, low-passed noise, an Ornstein-Uhlenbeck
  process), or integrating through a leak, keeps it bounded. The heard pitch is then the derivative, so delay noise
  should be smooth (low-passed) to avoid harsh pitch jitter.

### 7.4 How the Open Projects Generate It

**CHOW Tape Model** (`Plugin/Source/Processors/Timing_Effects/`, GPL-3.0):

- Flutter: a fixed periodic waveform measured from a consumer reel machine of the 1960s by recording a train of 1000
  pulses and playing it back (after the method of S. Arnardottir, J. S. Abel and J. O. Smith III, a digital model of a
  tape echo unit, AES 125th Convention, 2008). Three cosines at the fundamental and its second and third harmonics,
  relative amplitudes 230 : 80 : 99 with phase offsets 0, 13π/4 and -π/10, plus a DC offset of 350 that keeps the delay
  positive; the rate control maps to `0.1 · 1000^rate` Hz (0.1 to 100 Hz), the depth to `sqrt(depth³ · 81/625)`.
- Wow: one cosine at `4.5^rate - 1` Hz (0 to 3.5 Hz) plus an Ornstein-Uhlenbeck process for variance, its depth
  `depth³`, its maximum excursion 1000 samples. The rate is raised each block by `1 + u^1.25 · drift` for a uniform `u`,
  so drift only ever speeds the wow up, by a random amount each block.
- The Ornstein-Uhlenbeck process (in `OHProcess.h`, credited to ZetaCarinaeModules by Michael Hampton, GPL-3.0):
  `y += sqrt(T) · σ · n`, then `y += θ (μ - y) T`, with `n` normal, damping `θ = 20 amount + 1`, mean `μ = amount`,
  and a 10 Hz low pass on the result. Mean-reverting noise of this kind is the natural model for drift: it wanders but
  is pulled back, and its correlation time is `1/θ`.
- Depth changes are smoothed multiplicatively over 50 ms; the read is a third-order Lagrange interpolated delay; a 15 Hz
  DC blocker follows.

**Airwindows Flutter2 and ToTape9** (MIT): a single sine of delay whose phase increment is multiplied, at the start of
each cycle, by a fresh random factor between 0.24 and 0.98. Each wobble is therefore a different length, which makes
the modulation irregular and organic, nearer to a worn transport than a steady vibrato, at the cost of one random number
per cycle. Depth is `A⁴ · 90` samples at 44.1 kHz (capped near 500), the rate `0.02 · B³` radians a sample; the read is
linear interpolation in a 1000-sample ring. ToTape9 chooses each channel's new factor from two candidates, the one that
keeps it nearer the other channel, so the two sides wander together without being identical. IronOxide5 (MIT) ties its
flutter's randomness to its speed control, `0.04 + 0.11 / sqrt(ips)`, so slower tape wobbles more.

### 7.5 A Physically Composed Modulation

The mechanical sources of 7.2 suggest building the delay from named parts, each with a rate tied to the speed and a
depth tied to the machine's condition:

- Capstan: a fundamental at `v / (π D)` with a second and third harmonic (the CHOW ratios are one measured example).
- Pinch roller: a slower component, optionally a narrow raised-cosine pulse once a turn for a flat spot.
- Reel: a sine at the slowly changing reel rate.
- Drift: an Ornstein-Uhlenbeck process with a correlation time of seconds.
- Irregularity: the per-cycle random rate of Flutter2 applied to the wow components.
- Scrape: band-pass noise around 1 to 5 kHz at a very small depth, or the same noise applied as amplitude modulation,
  since its effect is sidebands rather than pitch.

Sines are produced without calling `sin` by a rotating phasor (a complex multiply per sample, renormalised every few
hundred samples) or a second-order resonator, about 4 to 6 operations each; harmonics come from the phasor's powers. Slow
random parts are generated at a control rate and interpolated. Altogether 20 to 40 operations a sample.

Character at the extremes: the "seasick" sound is wow of 1 to 3% peak at 0.3 to 1.5 Hz with irregular cycle lengths; a
"stretched" or slipping tape is asymmetric, slowing gradually and catching up suddenly (a skewed or sawtooth-like delay
shape); a "chewed" tape adds sudden speed jerks, crinkle and dropouts together (section 8).

### 7.6 Interpolating the Delay

A modulated delay needs a fractional read every sample. The choices, after T. I. Laakso, V. Välimäki, M. Karjalainen and
U. K. Laine, "Splitting the unit delay", IEEE Signal Processing Magazine, 1996; J. Dattorro, "Effect design, part 2:
delay-line modulation and chorus", Journal of the Audio Engineering Society, 1997; and J. O. Smith III, "Physical Audio
Signal Processing", online book, on interpolated delay lines:

- **Linear** (2 taps, about 3 operations): its response depends on the fraction. At a fraction of one half the
  magnitude is `cos(π f / fs)`: at 48 kHz, -0.5 dB at 5 kHz, -2.0 dB at 10 kHz, -5.1 dB at 15 kHz; at a whole-sample
  fraction it is flat. As the delay is modulated the fraction sweeps, so the treble is amplitude-modulated at the wow
  rate, heard as a pulsing dullness. Acceptable for deep, slow lo-fi wow where dullness is wanted anyway; poor for
  subtle studio flutter, which sweeps the fraction through its whole range many times a second.
- **All-pass** (first order, 1 multiply and state): flat in magnitude, so no treble pulsing, but it has internal state,
  so a quickly changing delay produces transients, and its phase delay is accurate only at low frequencies. Dattorro
  recommends it for slow chorus; it suits slow wow, not fast flutter or jumps.
- **Cubic**, third-order Lagrange or Catmull-Rom Hermite (4 taps, about 12 to 16 operations): at a half-sample fraction,
  -0.04 dB at 5 kHz, -0.5 dB at 10 kHz, -2.5 dB at 15 kHz at 48 kHz (both forms agree there and differ slightly
  elsewhere). Stateless, so safe for any modulation. The CHOW source uses third-order Lagrange; it is the usual
  compromise.
- **Windowed sinc** (8 to 32 taps from a table of fractional phases, 20 to 70 operations): near flat to 18 kHz or more
  and clean for any modulation; the reference choice when the treble must be untouched, and costly per instrument.
- **Oversampled read**: interpolating a line kept at twice the rate improves any of the above, at the cost of the
  oversampler.

Zipper noise comes not from the interpolation but from the delay signal itself: a delay that changes in steps (updated
per block) produces clicks and a buzz at the block rate. The delay must change every sample along a smooth curve; when a
control's target changes, the depth is smoothed over tens of milliseconds (the CHOW source uses 50 ms). Aliasing from
pitch modulation is negligible at these depths: a 3% upward excursion moves content at 20 kHz to 20.6 kHz, still below
half of 44.1 or 48 kHz.

## 8. Dropouts, Crinkle and Wear

### 8.1 Dropouts

A dropout is a brief loss of head-to-tape contact or of oxide: a speck of debris, a shed patch, a crease. Physically it
is a sudden increase in spacing `d` for a few to a few hundred milliseconds, so by the spacing-loss law it removes the
treble much more than the bass: a gentle dip in level with a deep, momentary dulling, recovering as the spot passes. The
deeper the spacing and the slower the tape, the more it dulls (section 4.1). Total oxide loss gives a full mute.

A model: an event generator draws gaps between events from an exponential distribution (a Poisson process, rate set by
the condition of the tape), each event a duration (5 to 300 ms) and a depth in microns of extra spacing; a smooth
envelope (a raised cosine or a pair of one-poles, 2 to 10 ms attack and release) carries the spacing, which sets a
one-pole low-pass's cutoff and a broadband gain dip from the spacing-loss law. The coefficient is recomputed at a control
rate. Cost: about 10 to 15 operations a sample, nearly nothing between events.

### 8.2 Crinkle ("Chew")

The CHOW source's Chew stage (`Chew/ChewProcessor.cpp`, `Chew/Dropout.h`) alternates dry and crinkled stretches whose
lengths are drawn at random (the frequency control shortening the dry gaps, a variance control spreading them). During a
crinkled stretch it applies a power-law expander, `sign(x) |x|^(1 + p)` with `p` drawn afresh every 64 samples between
`depth` and `3 depth`, which pushes quiet passages down as a loss of contact does, and a low pass falling from 22 kHz
toward 5 kHz by the depth. The mix is smoothed over 10 ms and the power over 5 ms so the transitions do not click. The
power law needs a `pow` a sample while crinkled (about 40 to 60 cycles), which can be replaced by a cheaper expander
(a gain from an envelope follower) at little audible difference.

### 8.3 Degrade

The CHOW source's Degrade stage adds uniform white noise, a one-pole low pass at `200 · 100^(1 - amount)` Hz with a
random wander of its cutoff, and a level cut of up to 24 dB with a random wander, recomputed every short block; together
they mimic an old, demagnetised, duller tape. Expressed physically, the same is a larger fixed spacing (section 4.1),
a lower output level from demagnetisation and more noise relative to the signal.

## 9. A Second Generation

Dubbing a recording to a second tape runs it through a second complete record-and-play chain: a second emphasis,
saturation, noise, losses, head bump and set of speed errors, with independent random states. The straightforward model
repeats the chain, doubling its cost.

Two time-varying delays in series, `y(t) = x(t - d₂(t) - d₁(t - d₂(t)))`, equal a single delay of `d₁(t) + d₂(t)` to
within the change of `d₁` over `d₂`, which is negligible when the delays are milliseconds and their modulation is slow.
A second generation's wow can therefore be added to the first's in one delay line, saving a line and an interpolated read.
Placing both generations' nonlinear and linear stages before or after that single line changes the sound inaudibly,
since a slow delay commutes with the static stages to the same approximation. The saturation, losses, head bump and noise
of the second pass are cheap (section 11) and keep their own settings: a dub is often made at a different speed or on a
different machine, such as a studio master copied to cassette.

## 10. Azimuth and Stereo

Azimuth error is a tilt `θ` of the play gap from perpendicular to the tape. Two effects follow, both functions of
wavelength:

- **Within a track**, the gap reads a smeared wavefront: an azimuth loss `sin(π w tanθ / λ) / (π w tanθ / λ)` for track
  width `w`, a treble loss that is large on wide tracks at slow speeds.
- **Between tracks**, the gap's ends meet the recorded wavefront at different times: an interchannel delay of
  `Δt = s · tanθ / v`, where `s` is the distance between the tracks' centres. Summed to mono, the two channels comb-
  filter, which is why azimuth errors are heard as a phasey, collapsing top end on cassettes.

The CHOW source (`Loss_Effects/AzimuthProc.cpp`) delays one channel by a smoothed fractional delay computed from the tape
width and the angle; its expression for the delay in samples multiplies the distance by the speed, where the physics
divides by it, so its result should be checked before the formula is reused. Tape skew and a weave of the tape across
the head make the interchannel delay and the azimuth loss wander slowly, which a small low-passed random term
reproduces. These belong to a stereo implementation; a mono path has only the within-track loss.

## 11. Costs in a Per-Instrument Callback

Rough costs per output sample, in double precision on a current desktop core, mono, at 48 kHz. Cycles are estimates
from operation counts, not measurements; one percent of one 3 GHz core is about 625 cycles a sample at 48 kHz.

| Stage | Cheap form | Cycles | Full form | Cycles |
| --- | --- | --- | --- | --- |
| Input and output gain | multiply | 2 | smoothed gain | 4 |
| Record emphasis and inverse | two one-pole shelves | 10 | two biquad shelves | 20 |
| Saturation | rational soft curve with first-order antiderivative antialiasing | 30 to 50 | Jiles-Atherton RK2 at 2× with halfband in and out | 300 to 400 |
| Saturation, alternatives | Faust-style tanh Jiles-Atherton, 4 substeps | 120 to 200 | Newton-Raphson, 8 iterations, at 2× | 1200 to 1600 |
| Hiss | white noise through one shelf | 10 | plus modulation noise from an envelope | 20 |
| Wow and flutter generator | two phasors and a slow random | 15 | capstan harmonics, roller, reel, drift, irregular cycles, scrape | 40 |
| Delay read | linear | 5 | cubic Lagrange or Hermite | 15 |
| Delay read, best | | | windowed sinc, 16 taps | 50 |
| Dropouts and crinkle | event generator, one-pole, gain | 10 | plus power-law expander when crinkled | 60 |
| Play losses | one or two IIR sections | 10 to 20 | 64-tap linear-phase FIR | 70 |
| Head bump | one peaking biquad | 10 | peak and high pass | 20 |
| DC blocker | one-pole high pass | 4 | | |
| Second generation | emphasis, saturation, noise, losses, bump, its wow in the shared line | +70 | the full chain again | ×2 |

A cheap chain totals about 120 to 150 cycles (about 0.2% of a core per instrument), a full one with the RK2 hysteresis
about 500 to 650 (about 1%), and a full one with Newton-Raphson several percent. The audio callback's constraints shape
the implementation regardless of the choice:

- **Nothing allocated in the callback.** The delay line's length is fixed by the deepest supported excursion plus the
  interpolator's taps (for 3% at 0.3 Hz, about 800 samples at 48 kHz; a few thousand samples leaves room), and the
  oversampler's rings and all filter states are made with the effect.
- **Coefficients computed when the effect is made.** Speed, standard, head bump, loss fit and saturation constants
  depend only on settings; per-sample work reads them. Time-varying coefficients (a dropout's cutoff) update at a
  control rate with interpolation.
- **Deterministic randomness.** Noise, drift, irregular cycles and dropouts draw from a seeded generator, so the same
  settings and seed render the same output, which offline exports and their comparisons need; a fresh seed per instance
  keeps several instruments from wobbling in lockstep.
- **Safety.** The hysteresis solver's not-a-number and limit guards (section 3.2), denormal flushing in the long-decaying
  filter states, and a clamp on the delay read so that it can never leave the line.
- **Smoothing.** Any setting that moves the delay or a gain is ramped per sample; a block-rate step is audible.

## 12. Character Summaries by Machine

How the stages combine, as a listener hears them:

- **Studio machine at 30 ips**: extended, very flat treble; head bump high (around 100 Hz) and small; the least hiss;
  saturation only near the very top, gentle and mostly third harmonic; flutter barely measurable. The cleanest tape
  sound, a subtle firming of the low end and softening of peaks.
- **Studio machine at 15 ips**: the classic recording sound: a fuller bump in the 40 to 70 Hz region, treble flat to
  about 20 kHz at low level but compressing earlier on loud cymbals and sibilance, a faint hiss above 4.5 kHz, flutter
  around 0.03 to 0.05%.
- **7.5 ips**: softer treble (rolling off from about 15 kHz), earlier high-frequency saturation, the bump lower (25 to
  40 Hz), more hiss and slightly more flutter: warmer and rounder.
- **Cassette, good deck, ferric tape**: treble that saturates early (loud highs smear and dull), bright hiss from
  1.3 kHz, a low-ish bump, flutter around 0.05 to 0.1% with audible slow wow on sustained tones.
- **Portable or worn cassette**: all of the above worse, plus spacing loss from a worn pressure pad (dull, unstable
  treble), wow of 0.3 to 1%, irregular wobble, dropouts and occasional crinkle: lo-fi.
- **Seasick, dying transport**: wow of 1 to 3% with irregular cycles and lurches, heavy dulling, dropouts, chew.
- **Second generation**: everything compounds: more hiss, duller, more saturated, a more complex, less periodic wobble
  from two transports at once.

## 13. Open Projects Consulted

| Project | Licence | What it models (verified by reading its source) |
| --- | --- | --- |
| CHOW Tape Model (AnalogTapeModel), Jatin Chowdhury | GPL-3.0 | input filters, a compression stage, emphasis shelves around Jiles-Atherton hysteresis (RK2, RK4, Newton-Raphson 4 and 8, a state transition network, an older mode with a real bias tone), chew, degrade, wow (cosine plus Ornstein-Uhlenbeck, drift) and flutter (three measured harmonics) in a Lagrange-interpolated delay, loss FIR with head bump, azimuth |
| Surge XT, its Tape effect | GPL-3.0-or-later | a port of the CHOW stages: emphasis, hysteresis, loss filter, chew, degrade; no wow or flutter in that effect (`src/common/dsp/effects/chowdsp/`) |
| Airwindows, Chris Johnson | MIT | ToTape9: an emphasis pair, randomised-cycle flutter, slew-chain bias, tiny hysteresis, slew-dependent averaging around a sine-series saturator, saturating head bump, clipper; Flutter2; IronOxide5 with speed-dependent tapering and flutter; and many related tape processes (ToTape5 to 8, Tape, TapeHack, TapeBias, TapeDust, FromTape) not read in full |
| Faust libraries | `hysteresis.lib` LGPL-2.1-only; `aanl.lib` parts MIT | a tanh-based Jiles-Atherton with four Hermite-interpolated substeps; first- and second-order antiderivative antialiasing |
| ZetaCarinaeModules, Michael Hampton | GPL-3.0 | the Ornstein-Uhlenbeck process the CHOW source adapts (credited in its comments; not read directly) |
| Vital (its open source release) | GPL-3.0 | no tape stage: its effects folder holds compressor, delay, distortion, phaser and reverb |

Not verified: the Airwindows processes listed but not read; measured timings of the CHOW solvers (the costs above are
from operation counts); the head bump frequencies, which vary with head geometry and are given as typical ranges.

## 14. References

- D. C. Jiles and D. L. Atherton, "Theory of ferromagnetic hysteresis", Journal of Magnetism and Magnetic Materials,
  vol. 61, 1986.
- D. C. Jiles, J. B. Thoelke and M. K. Devine, "Numerical determination of hysteresis parameters for the modeling of
  magnetic properties using the theory of ferromagnetic hysteresis", IEEE Transactions on Magnetics, vol. 28, 1992.
- M. Holters and U. Zölzer, "Circuit simulation with inductors and transformers based on the Jiles-Atherton model of
  magnetization", DAFx, 2016.
- J. Chowdhury, "Real-time physical modelling for analog tape machines", DAFx, 2019.
- J. Parker, F. Esqueda and A. Bergner, "Modelling of nonlinear state-space systems using a deep neural network", DAFx,
  2019.
- J. Parker, V. Zavalishin and E. Le Bihan, "Reducing the aliasing of nonlinear waveshaping using continuous-time
  convolution", DAFx, 2016.
- S. Bilbao, F. Esqueda, J. Parker and V. Välimäki, "Antiderivative antialiasing for memoryless nonlinearities", IEEE
  Signal Processing Letters, 2017.
- S. Arnardottir, J. S. Abel and J. O. Smith III, a digital model of a tape echo unit, Audio Engineering Society 125th
  Convention, 2008.
- T. I. Laakso, V. Välimäki, M. Karjalainen and U. K. Laine, "Splitting the unit delay", IEEE Signal Processing
  Magazine, 1996.
- J. Dattorro, "Effect design, part 2: delay-line modulation and chorus", Journal of the Audio Engineering Society, 1997.
- J. O. Smith III, "Physical Audio Signal Processing", online book, Center for Computer Research in Music and Acoustics.
- R. L. Wallace Jr., the reproduction of magnetically recorded signals, 1951.
- H. N. Bertram, "Theory of Magnetic Recording", 1994.
- M. Camras, "Magnetic Recording Handbook", 1987.
- J. Kadis, "The Science of Sound Recording", 2012.
- H. S. Wall, "Analytic Theory of Continued Fractions", 1948 (the continued fraction for tanh).
