// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Asheville's oscillators, after the classic three-oscillator ladder monosynth of the 1970s: three free-running
//! oscillators, each its footage, its wave and its tuning, mixed into a mixer that overloads as it is turned up and that
//! the output may be looped back into (Feedback); Osc 3 may leave the mix to be a Mod Matrix source instead (Osc 3 as
//! LFO). Model Classic switches each oscillator among the panel's six waves; Continuous sweeps one Shape from triangle
//! through saw and square to a narrow pulse, as the later models do. Drift wanders each oscillator's tuning slowly, its
//! own way, and Character sets how settled the instrument is: Warm, Cold Start (wandering further for its first half
//! minute, as if just switched on) or Worn (beating more and slipping flat high up).
//!
//! Each wave is made from its oscillator's phase and smoothed at its jumps by a two-sample polyBLEP, after stmlib's
//! ThisBlepSample and NextBlepSample (stmlib/dsp/polyblep.h) and the variable-shape oscillator of Mutable Instruments'
//! Plaits (plaits/dsp/oscillator/variable_shape_oscillator.h), both by Emilie Gillet, MIT; the implementation here is our
//! own.

use crate::protocol::values::{field, list, number, truth, word};
use crate::voice::oscillators::{frequency_of, Moves, OscillatorState};
use rmpv::Value;
use std::f64::consts::PI;

/// The waves of the panel: triangle, the shark tooth (between triangle and saw), saw, reverse saw (Osc 3's), square, and
/// the wide and narrow pulses.
#[derive(Clone, Copy, PartialEq, Debug)]
pub enum Wave {
    Triangle,
    SharkTooth,
    Saw,
    ReverseSaw,
    Square,
    WidePulse,
    NarrowPulse,
}

/// The wide and narrow pulses' widths, as shares of a cycle, the original panel's.
const WIDE_WIDTH: f64 = 0.32;
const NARROW_WIDTH: f64 = 0.16;
/// How far a pulse's width may be moved, never to nothing.
const NARROWEST: f64 = 0.02;
const WIDEST: f64 = 0.98;
/// Each oscillator's level at full Mix, so that three at full drive the mixer into its overload.
const MIX_GAIN: f64 = 0.5;
/// How hard the mixer's overload saturates, and how far Feedback's loop at full turns the output back into it.
const MIXER_PUSH: f64 = 1.2;
const MOST_FEEDBACK: f64 = 1.5;
/// Drift at full: how far, in cents, each oscillator wanders, and the slow rates its two wanderings run at.
const MOST_DRIFT_CENTS: f64 = 12.0;
const DRIFT_RATES: [f64; 2] = [0.071, 0.23];
/// Cold Start's extra wandering, in cents, and how long it takes to settle, in seconds since the instrument began.
const COLD_CENTS: f64 = 25.0;
const COLD_SETTLING_SECONDS: f64 = 12.0;
/// Worn: each oscillator's fixed mistuning, in cents, and how much it slips flat a semitone above the slipping point.
const WORN_CENTS: [f64; 3] = [0.0, 3.5, -4.5];
const WORN_SLIP_FROM: f64 = 72.0;
const WORN_SLIP_CENTS: f64 = 0.6;
const CENTS: f64 = 100.0;
/// The lowest and highest rate Osc 3 runs at as an LFO, which is never heard and so need not keep to hearing.
const SLOWEST_LFO_HERTZ: f64 = 0.01;
const MOST_STEP: f64 = 0.45;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Character {
    Warm,
    ColdStart,
    Worn,
}

/// One oscillator: its footage as semitones from the note, its wave or its continuous shape, its tuning in cents, its
/// level and whether it sounds.
#[derive(Clone, Copy, Debug)]
pub struct Oscillator {
    pub range: f64,
    pub wave: Wave,
    pub shape: f64,
    pub cents: f64,
    pub mix: f64,
    pub on: bool,
}

/// Asheville's oscillators as a patch compiles them.
#[derive(Clone, Debug)]
pub struct Asheville {
    pub oscillators: [Oscillator; 3],
    pub continuous: bool,
    pub character: Character,
    pub drift: f64,
    pub feedback: f64,
    pub osc3_lfo: bool,
}

/// A wave's name in a spec.
fn wave_named(name: &str) -> Wave {
    match name {
        "triangle" => Wave::Triangle,
        "shark" => Wave::SharkTooth,
        "reverse_saw" => Wave::ReverseSaw,
        "square" => Wave::Square,
        "wide" => Wave::WidePulse,
        "narrow" => Wave::NarrowPulse,
        _ => Wave::Saw,
    }
}

/// Asheville's oscillators from a spec: each oscillator a map of range (semitones from the note), wave, shape (0 to 1),
/// cents, mix (0 to 1) and on.
pub fn compiled(spec: &Value) -> Asheville {
    let defaults = Oscillator {
        range: 0.0,
        wave: Wave::Saw,
        shape: 0.33,
        cents: 0.0,
        mix: 0.8,
        on: true,
    };
    let specs = list(spec, "oscillators");
    let oscillators = std::array::from_fn(|place| match specs.get(place) {
        Some(each) => Oscillator {
            range: number(each, "range", 0.0),
            wave: wave_named(word(each, "wave", "saw")),
            shape: number(each, "shape", 0.33).clamp(0.0, 1.0),
            cents: number(each, "cents", 0.0),
            mix: number(each, "mix", 0.8).clamp(0.0, 1.0),
            on: truth(each, "on", true),
        },
        None => defaults,
    });
    let character = match word(spec, "character", "warm") {
        "cold_start" => Character::ColdStart,
        "worn" => Character::Worn,
        _ => Character::Warm,
    };
    Asheville {
        oscillators,
        continuous: word(spec, "model", "classic") == "continuous",
        character,
        drift: number(spec, "drift", 0.0).clamp(0.0, 1.0),
        feedback: number(spec, "feedback", 0.0).clamp(0.0, 1.0),
        osc3_lfo: field(spec, "osc3_lfo").is_some() && truth(spec, "osc3_lfo", false),
    }
}

/// The polyBLEP's correction near a jump of two at a cycle's start, at a place in the cycle and a step a sample.
#[inline]
fn blep(place: f64, step: f64) -> f64 {
    if place < step {
        let t = place / step;
        2.0 * t - t * t - 1.0
    } else if place > 1.0 - step {
        let t = (place - 1.0) / step;
        t * t + 2.0 * t + 1.0
    } else {
        0.0
    }
}

#[inline]
fn saw(place: f64, step: f64) -> f64 {
    2.0 * place - 1.0 - blep(place, step)
}

#[inline]
fn pulse(place: f64, step: f64, width: f64) -> f64 {
    let level = if place < width { 1.0 } else { -1.0 };
    level + blep(place, step) - blep((place - width).rem_euclid(1.0), step)
}

#[inline]
fn triangle(place: f64) -> f64 {
    1.0 - 4.0 * (place - 0.5).abs()
}

/// One classic wave at a place in its cycle, its pulse widths moved by the Mod Matrix's Pulse width.
#[inline]
fn classic(wave: Wave, place: f64, step: f64, width_moved: f64) -> f64 {
    let width = |base: f64| (base + width_moved).clamp(NARROWEST, WIDEST);
    match wave {
        Wave::Triangle => triangle(place),
        Wave::SharkTooth => 0.5 * (triangle(place) + saw(place, step)),
        Wave::Saw => saw(place, step),
        Wave::ReverseSaw => -saw(place, step),
        Wave::Square => pulse(place, step, width(0.5)),
        Wave::WidePulse => pulse(place, step, width(WIDE_WIDTH)),
        Wave::NarrowPulse => pulse(place, step, width(NARROW_WIDTH)),
    }
}

/// The continuous Shape at a place: triangle at 0, saw at a third, square at two thirds and a narrow pulse at its top,
/// faded between each and the next.
#[inline]
fn continuous(shape: f64, place: f64, step: f64, width_moved: f64) -> f64 {
    let third = 1.0 / 3.0;
    if shape < third {
        let along = shape / third;
        triangle(place) * (1.0 - along) + saw(place, step) * along
    } else if shape < 2.0 * third {
        let along = (shape - third) / third;
        saw(place, step) * (1.0 - along) + pulse(place, step, (0.5 + width_moved).clamp(NARROWEST, WIDEST)) * along
    } else {
        let along = (shape - 2.0 * third) / third;
        let width = 0.5 + (NARROW_WIDTH - 0.5) * along + width_moved;
        pulse(place, step, width.clamp(NARROWEST, WIDEST))
    }
}

impl Asheville {
    /// Ready a voice's oscillators as a note begins: each at a phase of its own, as free-running oscillators never start
    /// a note together.
    pub fn begin(&self, state: &mut OscillatorState, random: f64) {
        let golden = 0.618_033_988_749_895;
        for (place, phase) in state.phases.iter_mut().enumerate() {
            *phase = ((random + 1.0) * golden * (place as f64 + 1.0)).fract();
        }
    }

    /// How far an oscillator wanders from its tuning at a moment, in cents: Drift's two slow wanderings, Cold Start's
    /// settling and Worn's mistuning and slip.
    fn wander(&self, place: usize, pitch: f64, seconds: f64, began: f64, random: f64) -> f64 {
        let offset = (random + 1.0) * (place as f64 + 1.0) * 2.3;
        let slow = |rate: f64, turn: f64| (2.0 * PI * (rate * (1.0 + 0.13 * place as f64) * seconds) + offset * turn).sin();
        let mut cents = self.drift * MOST_DRIFT_CENTS * (0.6 * slow(DRIFT_RATES[0], 1.0) + 0.4 * slow(DRIFT_RATES[1], 2.7));
        match self.character {
            Character::Warm => {}
            Character::ColdStart => cents += COLD_CENTS * (-began / COLD_SETTLING_SECONDS).exp() * slow(DRIFT_RATES[0], 4.1),
            Character::Worn => {
                cents += WORN_CENTS[place];
                if pitch > WORN_SLIP_FROM {
                    cents -= (pitch - WORN_SLIP_FROM) * WORN_SLIP_CENTS;
                }
            }
        }
        cents
    }

    /// One sample of the three oscillators through the mixer: the note at a pitch, seconds into it, moved as given, its
    /// voice's drift read from when the note began and the voice's own random number, both kept in its state. Osc 3 as LFO leaves the mix and is kept in the state's side, from -1
    /// to 1, for the Mod Matrix's Osc 3 source.
    #[inline]
    pub fn sample(&self, state: &mut OscillatorState, pitch: f64, seconds: f64, moves: Moves, rate: f64) -> f64 {
        let (began, random) = (state.began, state.random);
        let mut mix = 0.0;
        for (place, oscillator) in self.oscillators.iter().enumerate() {
            let lfo = place == 2 && self.osc3_lfo;
            if !oscillator.on && !lfo {
                continue;
            }
            let wandered = self.wander(place, pitch, seconds, began, random);
            let tuned = pitch + oscillator.range + (oscillator.cents + wandered) / CENTS + moves.pitch;
            let frequency = if lfo {
                // Osc 3 as an LFO is never heard, so it may run below hearing; it keeps under half the rate.
                (440.0 * 2f64.powf((tuned - 69.0) / 12.0)).max(SLOWEST_LFO_HERTZ)
            } else {
                frequency_of(tuned)
            };
            let step = (frequency / rate).min(MOST_STEP);
            let at = state.phases[place];
            let value = if self.continuous {
                continuous(oscillator.shape, at, step, moves.width)
            } else {
                classic(oscillator.wave, at, step, moves.width)
            };
            state.phases[place] = (at + step).fract();
            if lfo {
                state.side = value;
            } else {
                mix += value * oscillator.mix * MIX_GAIN;
            }
        }
        // The mixer overloads softly as it is turned up; Feedback loops the last output back into it, as the classic
        // patch of the output into the external input does.
        let fed = mix + self.feedback * MOST_FEEDBACK * state.last_out;
        let out = (fed * MIXER_PUSH).tanh() / MIXER_PUSH;
        state.last_out = out;
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A spec's three oscillators, waves, Model and Character come through compiled, and a note sounds within bounds.
    #[test]
    fn asheville_compiles_its_panel_and_sounds_within_bounds() {
        let oscillator = |range: i64, wave: &str| Value::Map(vec![("range".into(), range.into()), ("wave".into(), wave.into()), ("mix".into(), 1.0.into())]);
        let spec = Value::Map(vec![
            (
                "oscillators".into(),
                Value::Array(vec![oscillator(0, "saw"), oscillator(-12, "shark"), oscillator(-24, "reverse_saw")]),
            ),
            ("model".into(), "classic".into()),
            ("character".into(), "worn".into()),
            ("feedback".into(), 1.0.into()),
        ]);
        let asheville = compiled(&spec);
        assert_eq!(asheville.oscillators[1].wave, Wave::SharkTooth);
        assert_eq!(asheville.oscillators[2].range, -24.0);
        assert_eq!(asheville.character, Character::Worn);
        let mut state = OscillatorState::default();
        asheville.begin(&mut state, 0.3);
        let rate = 48_000.0;
        let most = (0..4800)
            .map(|place| asheville.sample(&mut state, 48.0, place as f64 / rate, Moves::default(), rate).abs())
            .fold(0.0, f64::max);
        assert!(most > 0.1 && most < 1.0, "{most}");
    }

    /// Osc 3 as LFO leaves the mix: silenced alone, the voice is silent, while Osc 3 still moves the side the matrix reads.
    #[test]
    fn osc3_as_lfo_leaves_the_mix_and_feeds_the_matrix() {
        let oscillator = |on: bool| Value::Map(vec![("on".into(), on.into()), ("range".into(), (-48).into())]);
        let spec = Value::Map(vec![
            ("oscillators".into(), Value::Array(vec![oscillator(false), oscillator(false), oscillator(true)])),
            ("osc3_lfo".into(), true.into()),
        ]);
        let asheville = compiled(&spec);
        let mut state = OscillatorState::default();
        let rate = 48_000.0;
        let mut sides = Vec::new();
        for place in 0..48_000 {
            let out = asheville.sample(&mut state, 60.0, place as f64 / rate, Moves::default(), rate);
            assert_eq!(out, 0.0, "nothing heard");
            sides.push(state.side);
        }
        let (lowest, highest) = sides.iter().fold((f64::MAX, f64::MIN), |(low, high), side| (low.min(*side), high.max(*side)));
        assert!(highest - lowest > 1.0, "Osc 3 swings the side");
    }
}
