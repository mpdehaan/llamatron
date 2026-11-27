# The Transistor Ladder

The four-pole transistor ladder low pass: its circuit, the equations a model solves, how they are solved in real time,
what makes one unit differ from another, and what each choice costs. The general survey of zero-delay-feedback filters
is in `QUALITY_RESEARCH.md`; this chapter is the ladder's own.

## The Circuit

Four stages stand in a column, each a differential pair of transistors with a capacitor across its collectors. A pair
passes a current that is the hyperbolic tangent of the voltage across its bases, in units of twice the thermal voltage
V_t = kT/q (about 26 mV at room temperature), so that small signals pass linearly and large ones saturate smoothly. Each
stage's capacitor is charged by the difference between the current its pair drives and the current the stage above
draws back, which gives each stage the equation, with v_i its voltage in those units:

    dv_i/dt = ω_i (tanh(u_i) − tanh(v_i))

where u_0 = x − k·v_3 for the input pair, the input less the feedback from the last stage, and u_i = v_(i−1) for the
others. ω_i = 2π f_c / c_i, where c_i is the stage's capacitor as a share of its nominal value. The feedback gain k is
set by the Resonance pot, linearly; small-signal analysis of four equal poles gives oscillation at k = 4, where the
loop's phase reaches 180° at the cutoff and its gain one. Equations after Huovilainen's paper at DAFx 2004 and D'Angelo and
Välimäki's at ICASSP 2013.

The cutoff is set through an exponential converter: f_c ∝ exp(V_cv / V_t). Since V_t is proportional to temperature,
it drifts by about 1/300 per kelvin, 0.33%; the same drift moves the tanh's scale, so a warm unit is slightly brighter
and slightly cleaner together.

## Passband and Resonance

In the passband each stage passes its input whole, so the loop subtracts k of the output from the input: the passband
gain is 1/(1 + k), 13.4 dB down at k = 3.68. The original circuit makes none of it up, which is why a resonant ladder
sounds thin. Making it up at the output by (1 + c·k), c from 0 to 1, restores the passband exactly in small signal
without changing how hard the input pair is driven; adding c·k·x at the summing node instead, as some later ladders
do, does the same in small signal but pushes the input pair (1 + c·k) times harder, so that the saturation thickens as
Resonance rises, beyond what Drive alone asks for.

Driven hard, the real ladder loses its resonance: the saturating pairs lower the loop's effective gain. A model whose
stages saturate as the circuit's do reproduces this without any rule of its own.

## Discretisation

Each stage is integrated by the trapezoidal rule, prewarped so that the cutoff lands where it is set: with
g_i = tan(π f_c / f_s) / c_i at the running rate f_s, each stage keeps a state s_i, its voltage is

    v_i = s_i + g_i (tanh(u_i) − tanh(v_i))

and after the sample is solved the state moves on as s_i ← 2v_i − s_i. Because u_0 depends on v_3, the four equations
are implicit and coupled: they are solved together each sample.

## Newton's Method in Closed Form

The residual of stage i is G_i = v_i − s_i − g_i (tanh(u_i) − tanh(v_i)). Its Jacobian is cyclic bidiagonal: stage i
depends on itself and the stage before, and the first on the last. With sech²(x) = 1 − tanh²(x):

    a_i = 1 + g_i sech²(v_i)              the diagonal
    b_i = g_i sech²(u_i)                  the stage before entering stage i, for i = 1..3
    c   = g_0 k sech²(u_0)                the last stage entering the first

Writing r = −G, Newton's step Δ solves a_0 Δ_0 + c Δ_3 = r_0 and a_i Δ_i − b_i Δ_(i−1) = r_i. Express each Δ_i as
α_i + β_i Δ_0, with α_0 = 0 and β_0 = 1:

    α_i = (r_i + b_i α_(i−1)) / a_i
    β_i = b_i β_(i−1) / a_i
    Δ_0 = (r_0 − c α_3) / (a_0 + c β_3)
    Δ_i = α_i + β_i Δ_0

One pass costs eight tanh, four divisions for the α and β, and one for Δ_0, with no matrix. Started from the straight
line through the last two steps' voltages, 2v(n−1) − v(n−2), the method meets to a ten-millionth (about 140 dB under
full scale) in one or two passes; four are the most it is given, which bounds the worst case for real time.

## Tanh in Rational Form

The model calls tanh dozens of times a sample. The continued fraction of tanh gives the rational

    tanh(x) ≈ x (135135 + 17325 x² + 378 x⁴ + x⁶) / (135135 + 62370 x² + 3150 x⁴ + 28 x⁶)

within a few millionths for |x| < 4.97, past which tanh is one to a sample's precision; it is several times cheaper
than a library tanh. Newton's method needs the derivative only roughly, so 1 − t² from the rational's t serves.

## A Unit of Its Own

No two ladders are matched. Two spreads matter to the sound:

- The capacitors' tolerance, commonly ±2 to 5%, spreads the four poles, softening the knee and moving the resonant
  peak. A spread of ±1.5% keeps the filter recognisably itself.
- Each pair's base-emitter mismatch of 1 to 3 mV is an offset o_i of 0.02 to 0.06 in units of 2V_t. An offset bends a
  pair's curve to one side, which adds even harmonics, the ones a perfectly matched model lacks. Written as
  tanh(u + o) − tanh(o), the curve still passes through zero at rest, so that silence stays silent; tanh(o) is worked
  out once per unit. Written as tanh(u + o) alone, the circuit settles at a standing voltage, which a coupling
  capacitor would remove only slowly and never exactly.

Both are seeded by the instrument, so that an instrument always sounds like the same unit and two instruments differ.

## Drift

V_t wanders with temperature. A seeded, low-passed white noise at about 0.05 Hz, scaled to stray about 0.1%, moves the
tanh's scale by (1 + d) and the cutoff, through the exponential converter, by d·log₂(f_c / f_centre) octaves, so that
a cutoff far above the converter's centre moves more. Low-passed white noise of spread σ through a one-pole of
coefficient p has spread σ·sqrt(p/2), from which the noise's scale is set. It is seeded by the note.

## Oversampling, Drive and Aliasing

The input pair, pushed by Drive, makes harmonics far above the note, and a saturated loop makes more. The stages run at
four times the rate through two halfbands, and at eight once Drive is set, since Drive is what reaches the highest
harmonics. Measured on a 5 kHz sine at 0.9 of full scale, Resonance 60%, cutoff 9 kHz, the stray energy between the
harmonics against the harmonics' own:

| Drive's top gain | Drive 25% | Drive 50% | Drive 100% |
| --- | --- | --- | --- |
| x16 | −61 dB | −45 dB | −35 dB |
| x10 | −63 dB | −54 dB | −40 dB |
| x6 | −63 dB | −63 dB | −49 dB |

At full Drive the input pair is a square wave; only a higher rate or a lower top gain cleans it further. A top gain
of ten keeps the familiar range of a driven filter.

The level after a driven filter is held by the square root of the input gain, as a player sets the level of a
driven filter, never by dividing inside the loop, which would change how the loop saturates. A coupling capacitor at
about 5 Hz follows the output, as the circuit's does.

## Self-Oscillation

The circuit oscillates past k = 4 into a slightly squared sine. A model may stop just short: at k = 3.9 an impulse's
ringing dies within two seconds at every cutoff, with full Drive, while the peak still rings strongly when the sound
excites it.

## Cost

Per voice, per sample, at 48 kHz, on a recent laptop core: about 350 ns undriven at 4x and about 700 ns driven at
8x, against about 100 ns for a linearised one-pass ladder; each step is the Newton passes, the halfbands a small part.
