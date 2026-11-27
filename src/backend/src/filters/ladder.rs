// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The transistor ladder as its circuit behaves: four stages, each a pair of transistors whose current is the difference
//! of two hyperbolic tangents, the tanh of what drives the stage and the tanh of the stage's own voltage, charging a
//! capacitor; the input pair taking the input less the feedback from the last stage. Levels are in units of twice the
//! thermal voltage, the scale the transistors' tanh works in.
//!
//! The four stages are integrated by the trapezoidal rule at eight times the rate when driven, four when not,, and the implicit equations that rule
//! gives are solved by Newton's method each sample, in closed form: the stages' Jacobian is cyclic bidiagonal, each
//! stage depending on itself and the stage before, the first on the last, so that one pass down the stages and one
//! division solve it, with no matrix. Two or three passes meet to a billionth, never more than four.
//!
//! What makes one ladder sound like a unit of its own is kept: each stage's capacitor a little off its value and each
//! transistor pair a little off balance, the offsets giving the even harmonics a perfectly matched ladder lacks, both
//! seeded by the instrument, so that an instrument always sounds like the same unit and two instruments differ; and the
//! thermal voltage wandering slowly, seeded by the note, moving the cutoff and the tanh's scale together, so that a held
//! note breathes. The feedback stops just short of the point where the loop would oscillate on its own.
//!
//! Resonance thins the bass, by 1/(1 + k) of the passband, as the circuit does; Bass compensation gives a share of it
//! back at the output, so that at its full the passband holds its level while Drive alone decides the grit.
// The stage equations after D'Angelo and Välimäki (ICASSP 2013) and Huovilainen (DAFx 2004), both published papers; the
// closed-form Newton solve and the implementation are our own.

use crate::dsp::oversample::Halfband;
use crate::dsp::{flushed, HIGHEST_SHARE};
use std::f64::consts::PI;

/// The ladder's stages.
pub const STAGES: usize = 4;
/// How many halfbands the stages run behind, each doubling the rate: three, eight times the rate, when Drive pushes
/// the input pair hard enough to make harmonics far up; two, four times, when only the Resonance saturates the loop.
const HALFBANDS: usize = 3;
const UNDRIVEN_HALFBANDS: usize = 2;

/// The loop's gain at full Resonance: just under four, where the small-signal loop would oscillate on its own, so
/// that the peak rings strongly when excited and always dies away.
const MOST_FEEDBACK: f64 = 3.9;
/// Newton's method stops once no stage moves by more than this, some 140 dB under full scale, and never takes more
/// passes than this.
const CLOSE_ENOUGH: f64 = 1e-7;
const MOST_PASSES: usize = 4;
/// A full-scale sample at Drive 0 in units of twice the thermal voltage: low enough that a sound at a moderate level
/// keeps a strong resonant peak, the input pair only starting to hold it down as the sound grows loud, as a ladder fed
/// from a mixer at an ordinary setting does.
const FULL_SCALE: f64 = 0.35;
/// The input level Drive at full reaches, in the same units: a fierce, square-edged growl that still stays clean at
/// eight times the rate; Drive's knob climbs to it exponentially, so that each step of the knob sounds as large as the
/// last.
const MOST_DRIVEN_LEVEL: f64 = 17.9;
/// How the knob's turn is bent before it climbs, under one so that the grit comes on sooner in the knob's travel.
const DRIVE_BEND: f64 = 0.75;
/// The output's coupling capacitor, whose corner keeps the transistors' offsets from leaving a steady level.
const COUPLING_HERTZ: f64 = 5.0;
/// How far each stage's capacitor is off its value, and each pair's offset, at most, as shares.
const CAPACITOR_TOLERANCE: f64 = 0.015;
const LEAST_OFFSET: f64 = 0.02;
const MOST_OFFSET: f64 = 0.06;
/// The thermal voltage's slow wander: how far it strays as a share, how quickly, and the cutoff the exponential
/// converter is centred on, from which a stray moves a higher cutoff more.
const DRIFT_DEPTH: f64 = 0.001;
const DRIFT_HERTZ: f64 = 0.05;
const CONVERTER_CENTRE_HERTZ: f64 = 500.0;
/// The lowest cutoff the converter reaches.
const LOWEST_CUTOFF: f64 = 20.0;

/// Past this the rational tanh has reached one, to the precision a sample holds.
const TANH_END: f64 = 4.97;

/// The hyperbolic tangent by its continued fraction's [7/6] rational, within a few millionths of the true value and
/// held at one past TANH_END; several times cheaper than the library's, which the ladder calls dozens of times a sample.
// The continued fraction of tanh, a textbook result (Lambert); the rational's coefficients are its convergent.
#[inline]
fn fast_tanh(x: f64) -> f64 {
    if x.abs() >= TANH_END {
        return 1f64.copysign(x);
    }
    let square = x * x;
    let top = x * (135_135.0 + square * (17_325.0 + square * (378.0 + square)));
    let bottom = 135_135.0 + square * (62_370.0 + square * (3_150.0 + square * 28.0));
    top / bottom
}

/// A seeded xorshift's next draw, from -1 to 1.
#[inline]
fn draw(state: &mut u64) -> f64 {
    if *state == 0 {
        *state = 0x2545_F491_4F6C_DD1D;
    }
    *state ^= *state << 13;
    *state ^= *state >> 7;
    *state ^= *state << 17;
    (*state >> 11) as f64 / (1u64 << 52) as f64 - 1.0
}

/// The parts of one ladder that are its own: each stage's capacitor's share of its value and each pair's offset.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct LadderUnit {
    pub capacitors: [f64; STAGES],
    pub offsets: [f64; STAGES],
    /// Each offset's own tanh, worked out once, which each stage's curve takes away so that it passes through nothing.
    rests: [f64; STAGES],
}

impl LadderUnit {
    /// A unit seeded by a number, such as the instrument's, so that the same number always makes the same unit.
    pub fn seeded(seed: u64) -> LadderUnit {
        let mut state = seed.wrapping_mul(0x9E37_79B9_7F4A_7C15) | 1;
        let capacitors = std::array::from_fn(|_| 1.0 + CAPACITOR_TOLERANCE * draw(&mut state));
        let offsets = std::array::from_fn(|_| {
            let size = LEAST_OFFSET + (MOST_OFFSET - LEAST_OFFSET) * (draw(&mut state) + 1.0) / 2.0;
            size.copysign(draw(&mut state))
        });
        let rests = offsets.map(fast_tanh);
        LadderUnit { capacitors, offsets, rests }
    }

    /// A unit of perfectly matched parts, which no circuit is: for the tests that hear what the spread adds.
    #[cfg(test)]
    pub fn matched() -> LadderUnit {
        LadderUnit {
            capacitors: [1.0; STAGES],
            offsets: [0.0; STAGES],
            rests: [0.0; STAGES],
        }
    }
}

/// A Ladder's own settings, shared by every note: its unit, Drive and Bass compensation from 0 to 1, the stage read,
/// 1 to 4, and how many halfbands it runs behind, decided once so that its delay never changes mid-note.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct LadderSettings {
    pub unit: LadderUnit,
    pub drive: f64,
    pub compensation: f64,
    pub poles: usize,
    halfbands: usize,
}

impl LadderSettings {
    /// A Ladder's settings, its unit the default until the instrument seeds its own.
    pub fn new(drive: f64, compensation: f64, poles: usize) -> LadderSettings {
        let drive = drive.clamp(0.0, 1.0);
        LadderSettings {
            unit: LadderUnit::default(),
            drive,
            compensation: compensation.clamp(0.0, 1.0),
            poles: poles.clamp(1, STAGES),
            halfbands: if drive > 0.0 { HALFBANDS } else { UNDRIVEN_HALFBANDS },
        }
    }

    /// How many times the rate the stages run at.
    fn fast(&self) -> f64 {
        (1usize << self.halfbands) as f64
    }
}

impl Default for LadderUnit {
    fn default() -> Self {
        LadderUnit::seeded(0)
    }
}

/// What one note's ladder keeps: the stages' voltages and the integrators' states, its coefficients, the halfbands up
/// to four times the rate and back, the coupling capacitor, and the thermal voltage's wander and its seeded noise.
#[derive(Clone, Copy, Debug, Default)]
pub struct LadderState {
    voltages: [f64; STAGES],
    /// The stages' voltages a step before, from which the next step's are first guessed.
    earlier: [f64; STAGES],
    integrators: [f64; STAGES],
    gains: [f64; STAGES],
    feedback: f64,
    compensation: f64,
    halfbands: [Halfband; HALFBANDS],
    coupled_in: f64,
    coupled_out: f64,
    drift: f64,
    noise: u64,
}

impl LadderState {
    /// Seed the thermal voltage's wander from the note's own random number, from -1 to 1.
    pub fn seed(&mut self, random: f64) {
        self.noise = ((random + 1.0) * 1e9) as u64 + 1;
    }

    /// Work the coefficients out for a cutoff in hertz, a Resonance and a Bass compensation from 0 to 1, at a rate,
    /// moving the thermal voltage's wander on by the samples since the last time.
    pub fn prepare(&mut self, settings: &LadderSettings, cutoff: f64, resonance: f64, rate: f64, samples: usize) {
        let pull = 2.0 * PI * DRIFT_HERTZ * samples as f64 / rate;
        // Low-passed white noise, scaled so that it strays about DRIFT_DEPTH: its spread is the noise's times
        // sqrt(pull / 2), and a uniform draw's spread is 1/sqrt(3).
        let scale = DRIFT_DEPTH * 3f64.sqrt() / (pull / 2.0).sqrt();
        self.drift += pull * (scale * draw(&mut self.noise) - self.drift);
        let octaves_moved = self.drift * (cutoff.max(LOWEST_CUTOFF) / CONVERTER_CENTRE_HERTZ).log2();
        let cutoff = (cutoff * 2f64.powf(octaves_moved)).clamp(LOWEST_CUTOFF, HIGHEST_SHARE * rate);
        let fast = settings.fast() * rate;
        for (gain, capacitor) in self.gains.iter_mut().zip(settings.unit.capacitors) {
            *gain = (PI * cutoff / fast).tan() / capacitor;
        }
        self.feedback = MOST_FEEDBACK * resonance.clamp(0.0, 1.0);
        self.compensation = settings.compensation;
    }

    /// One sample through the ladder at the rate, by its settings: four times
    /// the rate through two halfbands, then the coupling capacitor.
    #[inline]
    pub fn process(&mut self, settings: &LadderSettings, input: f64, rate: f64) -> f64 {
        let drive_gain = (MOST_DRIVEN_LEVEL / FULL_SCALE).powf(settings.drive.powf(DRIVE_BEND));
        // The tanh's scale moves with the thermal voltage, as the cutoff does.
        let thermal = 1.0 + self.drift;
        let fed = input * FULL_SCALE * drive_gain / thermal;
        let tap = settings.poles - 1;
        let out = self.oversampled(0, settings, fed, tap);
        // The level held as Drive rises by the square root of its gain, as a player sets a driven filter's level.
        // Bass compensation gives back what the Resonance thins, 1/(1 + k) of the passband, at the output, so that Drive
        // alone decides how hard the input pair is pushed.
        let given_back = 1.0 + self.compensation * self.feedback;
        let level = thermal * given_back / (FULL_SCALE * drive_gain.sqrt());
        self.coupled(out * level, rate)
    }

    /// A sample made two by a halfband, each made more by the next or stepped at the last, then made one again.
    // Recursion over a fixed few halfbands keeps one path; it unrolls into a fixed chain.
    #[inline]
    fn oversampled(&mut self, halfband: usize, settings: &LadderSettings, input: f64, tap: usize) -> f64 {
        let (first, second) = self.halfbands[halfband].up(input);
        let (first, second) = if halfband + 1 < settings.halfbands {
            (
                self.oversampled(halfband + 1, settings, first, tap),
                self.oversampled(halfband + 1, settings, second, tap),
            )
        } else {
            let unit = &settings.unit;
            (self.step(unit, first, tap), self.step(unit, second, tap))
        };
        self.halfbands[halfband].down(first, second)
    }

    /// The output through its coupling capacitor, which takes away any steady level.
    #[inline]
    fn coupled(&mut self, input: f64, rate: f64) -> f64 {
        let pole = 1.0 - 2.0 * PI * COUPLING_HERTZ / rate;
        let out = input - self.coupled_in + pole * self.coupled_out;
        self.coupled_in = input;
        self.coupled_out = flushed(out);
        self.coupled_out
    }

    /// One step at the fast rate: the stages' voltages solved by Newton's method, the integrators moved on, and
    /// the voltage of the stage asked for.
    #[inline]
    fn step(&mut self, unit: &LadderUnit, input: f64, tap: usize) -> f64 {
        // The first guess runs on in a straight line from the last two steps, so that one or two passes meet.
        let mut voltages: [f64; STAGES] = std::array::from_fn(|stage| 2.0 * self.voltages[stage] - self.earlier[stage]);
        for _ in 0..MOST_PASSES {
            let moved = self.newton_pass(unit, input, &voltages);
            let mut most: f64 = 0.0;
            for (voltage, by) in voltages.iter_mut().zip(moved) {
                *voltage += by;
                most = most.max(by.abs());
            }
            if most < CLOSE_ENOUGH {
                break;
            }
        }
        for (integrator, voltage) in self.integrators.iter_mut().zip(voltages) {
            *integrator = flushed(2.0 * voltage - *integrator);
        }
        self.earlier = self.voltages;
        self.voltages = voltages;
        voltages[tap]
    }

    /// One pass of Newton's method: how far each stage's voltage moves towards the trapezoidal rule's solution. Stage i
    /// wants v_i = s_i + g_i (tanh(u_i) - tanh(v_i)), where u_0 is the input less k v_3 and u_i is v_(i-1), each with its
    /// pair's offset, less the offset's own tanh. The Jacobian's diagonal is a_i = 1 + g_i sech²(v_i), the stage before enters stage i by b_i = g_i
    /// sech²(u_i), and the last enters the first by c = g_0 k sech²(u_0); each move is written as alpha_i + beta_i times
    /// the first's, which the first's own equation then settles.
    #[inline]
    fn newton_pass(&self, unit: &LadderUnit, input: f64, voltages: &[f64; STAGES]) -> [f64; STAGES] {
        let mut wanted = [0.0; STAGES];
        let mut diagonal = [0.0; STAGES];
        let mut coupling = [0.0; STAGES];
        for stage in 0..STAGES {
            let driving = if stage == 0 {
                input - self.feedback * voltages[STAGES - 1]
            } else {
                voltages[stage - 1]
            };
            // A pair off balance bends its curve to one side, tanh(u + o) - tanh(o), which passes through nothing at
            // rest, so that silence stays silent and only a sound gains the even harmonics.
            let offset = unit.offsets[stage];
            let driving_tanh = fast_tanh(driving + offset);
            let rest_tanh = unit.rests[stage];
            let own_tanh = fast_tanh(voltages[stage]);
            let gain = self.gains[stage];
            wanted[stage] = self.integrators[stage] + gain * (driving_tanh - rest_tanh - own_tanh) - voltages[stage];
            diagonal[stage] = 1.0 + gain * (1.0 - own_tanh * own_tanh);
            coupling[stage] = gain * (1.0 - driving_tanh * driving_tanh);
        }
        let from_last = coupling[0] * self.feedback;
        let (mut alpha, mut beta) = ([0.0; STAGES], [0.0; STAGES]);
        beta[0] = 1.0;
        for stage in 1..STAGES {
            alpha[stage] = (wanted[stage] + coupling[stage] * alpha[stage - 1]) / diagonal[stage];
            beta[stage] = coupling[stage] * beta[stage - 1] / diagonal[stage];
        }
        let last = STAGES - 1;
        let first = (wanted[0] - from_last * alpha[last]) / (diagonal[0] + from_last * beta[last]);
        std::array::from_fn(|stage| alpha[stage] + beta[stage] * first)
    }
}
