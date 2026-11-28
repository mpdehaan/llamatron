// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Asheville's oscillators, after the classic three-oscillator ladder monosynth of the 1970s: three free-running
//! oscillators, each its footage, its wave and its tuning, mixed into a mixer that overloads as it is turned up and that
//! the output may be looped back into (Feedback), and a white noise source of its own in the mix. Each oscillator is also
//! a Mod Matrix source, Osc 1 to Osc 3, sounding or not, so that one can be an LFO or an audio-rate modulator of another. Model Classic switches each oscillator among the panel's six waves; Continuous sweeps one Shape from triangle
//! through saw and square to a narrow pulse, as the later models do. Drift wanders each oscillator's tuning slowly, its
//! own way, and Character sets how settled the instrument is: Warm, Cold Start (wandering further for its first half
//! minute, as if just switched on) or Worn (beating more and slipping flat high up). Ring is a mixer channel of its own,
//! Osc 1 times Osc 2, the clangorous sum and difference tones of a ring modulator; Snap pulls each oscillator's Tune
//! toward unison, fifths and octaves, after the detuning curve of Plaits' virtual-analog engine (Emilie Gillet, MIT).
//! Beyond the original, each oscillator has a Sub, a square one or two octaves under it, mixed in with it.
//!
//! Each wave is made from its oscillator's phase and smoothed at its jumps by a two-sample polyBLEP, after stmlib's
//! ThisBlepSample and NextBlepSample (stmlib/dsp/polyblep.h) and the variable-shape oscillator of Mutable Instruments'
//! Plaits (plaits/dsp/oscillator/variable_shape_oscillator.h), both by Emilie Gillet, MIT; the implementation here is our
//! own.

use crate::dsp::blep::{pulse, saw, triangle};
use crate::dsp::GOLDEN_GAMMA;
use crate::oscillators::{frequency_of, Moves, OscillatorState};
use crate::protocol::values::{list, number, truth, word};
use llamatron_names::spec;
use rmpv::Value;
use std::f64::consts::TAU;

/// What an oscillator takes where its spec names none: its shape and its level in the mix, each a share; and the
/// lowest of its subs, two octaves under it.
/// How many oscillators Asheville has, and the slow wanderings of each.
pub const OSCILLATOR_COUNT: usize = 3;
const WANDERINGS: usize = 2;
/// Half, a square's width and an even mix.
const HALF: f64 = 0.5;
/// Twice, by which a share from 0 to 1 becomes one from -1 to 1.
const TWICE: f64 = 2.0;
/// The smooth step's curve, three times the square less twice the cube.
const SMOOTH_SQUARE: f64 = 3.0;
const SMOOTH_CUBE: f64 = 2.0;
/// The thirds of the continuous Shape: triangle to saw, saw to square, square to narrow pulse.
const SHAPE_THIRDS: f64 = 3.0;
/// The xorshift's three shifts, its seed where its state is empty being the golden ratio's bits; and the shift and the
/// mantissa's bits by which its state becomes a number from -1 to 1.
const XORSHIFT_FIRST: u32 = 13;
const XORSHIFT_SECOND: u32 = 7;
const XORSHIFT_THIRD: u32 = 17;
const MANTISSA_SHIFT: u32 = 11;
const MANTISSA_BITS: u32 = 52;
/// How a note's random number from -1 to 1 becomes the seed of its noise.
const NOISE_SEED_SCALE: f64 = 1e9;
/// The slower wandering's share of Drift, and the faster's.
const SLOWER_WANDERING: f64 = 0.6;
const FASTER_WANDERING: f64 = 0.4;
/// A uniform draw's variance is a third, so the square root of three scales its spread to one.
const UNIFORM_VARIANCE_DIVISOR: f64 = 3.0;
const DEFAULT_SHAPE: f64 = 0.33;
const DEFAULT_MIX: f64 = 0.8;
const LOWEST_SUB: f64 = 2.0;

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
/// Drift at full: how far, in cents, each oscillator wanders, and the slow rates its two wanderings run at, each
/// oscillator a little faster or slower than the next; how far each sits off its tuning for good, as its parts put it;
/// and how much it jitters from cycle to cycle, in cents, and how fast that jitter moves.
const MOST_DRIFT_CENTS: f64 = 12.0;
const DRIFT_RATES: [f64; 2] = [0.071, 0.23];
const DRIFT_RATE_SPREAD: [f64; 2] = [0.13, 0.17];
const MOST_SPREAD_CENTS: f64 = 6.0;
const MOST_JITTER_CENTS: f64 = 0.6;
const JITTER_HERTZ: f64 = 30.0;
/// Cold Start's extra wandering, in cents, and how long it takes to settle, in seconds since the instrument began.
const COLD_CENTS: f64 = 25.0;
const COLD_SETTLING_SECONDS: f64 = 12.0;
/// Worn: each oscillator's fixed mistuning, in cents, and how much it slips flat a semitone above the slipping point.
const WORN_CENTS: [f64; 3] = [0.0, 3.5, -4.5];
const WORN_SLIP_FROM: f64 = 72.0;
const WORN_SLIP_CENTS: f64 = 0.6;
const CENTS: f64 = 100.0;
/// The slowest an oscillator that is not heard runs, as a Mod Matrix source alone it need not keep to hearing.
const SLOWEST_UNHEARD_HERTZ: f64 = 0.01;
/// The noise's level against an oscillator's at full Mix.
const NOISE_GAIN: f64 = 0.5;
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
    /// How many octaves under the oscillator its sub sounds, 0 for none.
    pub sub: u32,
    /// Where its Speed is an LFO's, the rate in hertz it runs at whatever the note, as a modulator; None where it plays
    /// the note at its Range.
    pub hertz: Option<f64>,
}

/// A sub's level against its oscillator's.
const SUB_LEVEL: f64 = 0.7;

/// Asheville's oscillators as a patch compiles them.
#[derive(Clone, Debug)]
pub struct Asheville {
    pub oscillators: [Oscillator; OSCILLATOR_COUNT],
    pub continuous: bool,
    pub character: Character,
    pub drift: f64,
    pub feedback: f64,
    /// The white noise's level in the mix, 0 for none.
    pub noise: f64,
    /// The ring modulator's level in the mix, Osc 1 times Osc 2, 0 for none.
    pub ring: f64,
    /// Whether each oscillator's Tune is pulled toward unison, fifths and octaves.
    pub snap: bool,
    /// What makes the instrument's oscillators a set of their own, seeded by the instrument: where each sits off its
    /// tuning, from -1 to 1 of the most, and where each of its two slow wanderings stands, in turns.
    pub spread: [f64; OSCILLATOR_COUNT],
    pub wander_phases: [[f64; WANDERINGS]; OSCILLATOR_COUNT],
}

/// The intervals Snap pulls a Tune toward, in cents either way: unison, a fifth, an octave, an octave and a fifth, two
/// octaves; and how near, in cents, a Tune must be to be pulled.
const SNAP_TARGETS: [f64; 5] = [0.0, 700.0, 1200.0, 1900.0, 2400.0];
const SNAP_REACH: f64 = 100.0;

/// A Tune pulled toward its nearest snapping interval, wholly at it and less so further away, along a smoothstep so that
/// the Tune never jumps.
// After the detuning curve of Plaits' VirtualAnalogEngine::ComputeDetuning (plaits/dsp/engine/virtual_analog_engine.cc,
// Emilie Gillet, MIT), which flattens its knob near those intervals; the implementation here is our own.
fn snapped(cents: f64) -> f64 {
    let sign = cents.signum();
    let size = cents.abs();
    let target = SNAP_TARGETS
        .iter()
        .copied()
        .min_by(|a, b| (size - a).abs().total_cmp(&(size - b).abs()))
        .unwrap_or(0.0);
    let away = (size - target) / SNAP_REACH;
    if away.abs() >= 1.0 {
        return cents;
    }
    let smooth = away.abs() * away.abs() * (SMOOTH_SQUARE - SMOOTH_CUBE * away.abs());
    sign * (target + away.signum() * smooth * SNAP_REACH)
}

/// A wave's name in a spec.
fn wave_named(name: &str) -> Wave {
    match name {
        spec::TRIANGLE => Wave::Triangle,
        spec::SHARK => Wave::SharkTooth,
        spec::REVERSE_SAW => Wave::ReverseSaw,
        spec::SQUARE => Wave::Square,
        spec::WIDE => Wave::WidePulse,
        spec::NARROW => Wave::NarrowPulse,
        _ => Wave::Saw,
    }
}

/// Asheville's oscillators from a spec: each oscillator a map of range (semitones from the note), wave, shape (0 to 1),
/// cents, mix (0 to 1) and on.
pub fn compiled(spec: &Value) -> Asheville {
    let defaults = Oscillator {
        range: 0.0,
        wave: Wave::Saw,
        shape: DEFAULT_SHAPE,
        cents: 0.0,
        mix: DEFAULT_MIX,
        on: true,
        sub: 0,
        hertz: None,
    };
    let specs = list(spec, spec::OSCILLATORS);
    let oscillators = std::array::from_fn(|place| match specs.get(place) {
        Some(each) => Oscillator {
            range: number(each, spec::RANGE, 0.0),
            wave: wave_named(word(each, spec::WAVE, spec::SAW)),
            shape: number(each, spec::SHAPE, DEFAULT_SHAPE).clamp(0.0, 1.0),
            cents: number(each, spec::CENTS, 0.0),
            mix: number(each, spec::MIX, DEFAULT_MIX).clamp(0.0, 1.0),
            on: truth(each, spec::ON, true),
            sub: number(each, spec::SUB, 0.0).clamp(0.0, LOWEST_SUB) as u32,
            hertz: crate::protocol::values::field(each, spec::HERTZ).and_then(crate::protocol::values::as_number),
        },
        None => defaults,
    });
    let character = match word(spec, spec::CHARACTER, spec::WARM) {
        spec::COLD_START => Character::ColdStart,
        spec::WORN => Character::Worn,
        _ => Character::Warm,
    };
    let mut asheville = Asheville {
        oscillators,
        continuous: word(spec, spec::MODEL, spec::CLASSIC) == spec::CONTINUOUS,
        character,
        drift: number(spec, spec::DRIFT, 0.0).clamp(0.0, 1.0),
        feedback: number(spec, spec::FEEDBACK, 0.0).clamp(0.0, 1.0),
        noise: number(spec, spec::NOISE, 0.0).clamp(0.0, 1.0),
        ring: number(spec, spec::RING, 0.0).clamp(0.0, 1.0),
        snap: truth(spec, spec::SNAP, false),
        spread: [0.0; OSCILLATOR_COUNT],
        wander_phases: [[0.0; WANDERINGS]; OSCILLATOR_COUNT],
    };
    // The instrument seeds its own set when it is placed; until then, the first set.
    asheville.seed(0);
    asheville
}

/// White noise from -1 to 1, a xorshift a sample, its state the voice's own.
#[inline]
fn white(state: &mut u64) -> f64 {
    if *state == 0 {
        *state = GOLDEN_GAMMA;
    }
    *state ^= *state << XORSHIFT_FIRST;
    *state ^= *state >> XORSHIFT_SECOND;
    *state ^= *state << XORSHIFT_THIRD;
    (*state >> MANTISSA_SHIFT) as f64 / (1u64 << MANTISSA_BITS) as f64 - 1.0
}

/// One classic wave at a place in its cycle, its pulse widths moved by the Mod Matrix's Pulse width.
#[inline]
fn classic(wave: Wave, place: f64, step: f64, width_moved: f64) -> f64 {
    let width = |base: f64| (base + width_moved).clamp(NARROWEST, WIDEST);
    match wave {
        Wave::Triangle => triangle(place, step),
        Wave::SharkTooth => HALF * (triangle(place, step) + saw(place, step)),
        Wave::Saw => saw(place, step),
        Wave::ReverseSaw => -saw(place, step),
        Wave::Square => pulse(place, step, width(HALF)),
        Wave::WidePulse => pulse(place, step, width(WIDE_WIDTH)),
        Wave::NarrowPulse => pulse(place, step, width(NARROW_WIDTH)),
    }
}

/// The continuous Shape at a place: triangle at 0, saw at a third, square at two thirds and a narrow pulse at its top,
/// faded between each and the next.
#[inline]
fn continuous(shape: f64, place: f64, step: f64, width_moved: f64) -> f64 {
    let third = 1.0 / SHAPE_THIRDS;
    if shape < third {
        let along = shape / third;
        triangle(place, step) * (1.0 - along) + saw(place, step) * along
    } else if shape < TWICE * third {
        let along = (shape - third) / third;
        saw(place, step) * (1.0 - along) + pulse(place, step, (HALF + width_moved).clamp(NARROWEST, WIDEST)) * along
    } else {
        let along = (shape - TWICE * third) / third;
        let width = HALF + (NARROW_WIDTH - HALF) * along + width_moved;
        pulse(place, step, width.clamp(NARROWEST, WIDEST))
    }
}

impl Asheville {
    /// Ready a voice's oscillators as a note begins: each at a phase of its own, as free-running oscillators never start
    /// a note together.
    pub fn begin(&self, state: &mut OscillatorState, random: f64) {
        for (place, phase) in state.phases.iter_mut().enumerate() {
            *phase = super::free_phase(random, place);
            // A sub is its oscillator divided down, so that it switches only where its oscillator's cycle begins: it
            // starts where its own slower cycle stands when its oscillator's stands at this phase.
            let octaves_down = self.oscillators.get(place).map_or(0, |oscillator| oscillator.sub);
            state.sub_phases[place] = *phase / f64::from(1u32 << octaves_down);
        }
        state.noise_state = ((random + 1.0) * NOISE_SEED_SCALE) as u64 + 1;
        state.jitter_noise = state.noise_state.wrapping_mul(GOLDEN_GAMMA) | 1;
        state.jitter = [0.0; OSCILLATOR_COUNT];
    }

    /// Seed what makes the instrument's oscillators their own by a number, such as the instrument's: each one's spread
    /// and where its wanderings stand, each a draw of its own, so that no two oscillators wander together.
    pub fn seed(&mut self, number: u64) {
        let seed = f64::from_bits(number.wrapping_mul(GOLDEN_GAMMA) | 1);
        for place in 0..OSCILLATOR_COUNT {
            self.spread[place] = TWICE * super::free_phase(seed, place) - 1.0;
            // Each wandering's phase a draw past the spreads', the first's past every spread, the second's past those.
            let (first, second) = (place + OSCILLATOR_COUNT, place + OSCILLATOR_COUNT + OSCILLATOR_COUNT);
            self.wander_phases[place] = [super::free_phase(seed, first), super::free_phase(seed, second)];
        }
    }

    /// How far an oscillator wanders from its tuning at a moment, in cents: Drift's spread, its two slow wanderings on
    /// the instrument's own clock, so that they run on across notes, and its fast jitter; Cold Start's settling and Worn's
    /// mistuning and slip.
    fn wander(&self, place: usize, pitch: f64, clock: f64, began: f64, jitter: f64) -> f64 {
        let slow = |which: usize| {
            let rate = DRIFT_RATES[which] * (1.0 + DRIFT_RATE_SPREAD[which] * place as f64);
            (TAU * (rate * clock + self.wander_phases[place][which])).sin()
        };
        let wandering = MOST_DRIFT_CENTS * (SLOWER_WANDERING * slow(0) + FASTER_WANDERING * slow(1));
        let spread = MOST_SPREAD_CENTS * self.spread[place];
        let mut cents = self.drift * (wandering + spread + MOST_JITTER_CENTS * jitter);
        match self.character {
            Character::Warm => {}
            Character::ColdStart => cents += COLD_CENTS * (-began / COLD_SETTLING_SECONDS).exp() * slow(0),
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
    /// voice's drift read from when the note began and the voice's own random number, both kept in its state. Each
    /// oscillator's value is kept in the state's sides, from -1 to 1, for the Mod Matrix's Osc 1 to Osc 3 sources.
    #[inline]
    pub fn sample(&self, state: &mut OscillatorState, pitch: f64, seconds: f64, moves: Moves, rate: f64) -> f64 {
        let began = state.began;
        let clock = began + seconds;
        // The jitter: white noise low-passed near JITTER_HERTZ, scaled so that its spread is one; a uniform draw's
        // spread is 1/sqrt(3), and a one-pole of coefficient p keeps sqrt(p/2) of it.
        let pull = (TAU * JITTER_HERTZ / rate).min(1.0);
        let jitter_scale = UNIFORM_VARIANCE_DIVISOR.sqrt() / (pull / TWICE).sqrt();
        if self.drift > 0.0 {
            for jitter in state.jitter.iter_mut() {
                *jitter += pull * (jitter_scale * white(&mut state.jitter_noise) - *jitter);
            }
        }
        let mut mix = 0.0;
        // Every oscillator runs, sounding or not, so that each can be read by the Mod Matrix.
        for (place, oscillator) in self.oscillators.iter().enumerate() {
            let wandered = self.wander(place, pitch, clock, began, state.jitter[place]);
            let tune = if self.snap { snapped(oscillator.cents) } else { oscillator.cents };
            let tuned = pitch + oscillator.range + (tune + wandered) / CENTS + moves.pitch + moves.osc_pitch[place];
            let frequency = if let Some(hertz) = oscillator.hertz {
                // At an LFO's Speed it runs at its own rate whatever the note; heard, it keeps to hearing's bottom.
                if oscillator.on {
                    hertz.max(frequency_of(crate::oscillators::LOWEST_PITCH))
                } else {
                    hertz.max(SLOWEST_UNHEARD_HERTZ)
                }
            } else if oscillator.on {
                frequency_of(tuned)
            } else {
                // Not heard, it may run below hearing, as an LFO; it keeps under half the rate.
                super::unclamped_frequency_of(tuned).max(SLOWEST_UNHEARD_HERTZ)
            };
            let step = (frequency / rate).min(MOST_STEP);
            let at = state.phases[place];
            let width = moves.width + moves.osc_width[place];
            let value = if self.continuous {
                continuous(oscillator.shape, at, step, width)
            } else {
                classic(oscillator.wave, at, step, width)
            };
            state.phases[place] = (at + step).fract();
            state.sides[place] = value;
            if !oscillator.on {
                continue;
            }
            mix += value * oscillator.mix * MIX_GAIN;
            if oscillator.sub > 0 {
                // The sub runs at a half or a quarter of its oscillator's step, so that it keeps under it, in step.
                let sub_step = step / f64::from(1 << oscillator.sub);
                let sub_at = state.sub_phases[place];
                mix += pulse(sub_at, sub_step, HALF) * oscillator.mix * MIX_GAIN * SUB_LEVEL;
                state.sub_phases[place] = (sub_at + sub_step).fract();
            }
        }
        if self.noise > 0.0 {
            mix += white(&mut state.noise_state) * self.noise * NOISE_GAIN;
        }
        // The ring modulator hears Osc 1 and Osc 2 whether or not they sound in the mix themselves.
        mix += state.sides[0] * state.sides[1] * self.ring * MIX_GAIN;
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
    use crate::dsp::testing::{HALF_SECOND, RATE, SECOND};

    /// Middle C, the note the tests play; Osc 3's place, the one the tests swing; and a tenth of a second of samples.
    const MIDDLE_C: f64 = 60.0;
    const OSC3: usize = 2;
    const TENTH_SECOND: usize = 4800;

    /// An oscillator switched off is silent in the mix but still runs, so the Mod Matrix can read it; noise alone sounds.
    #[test]
    fn an_oscillator_off_still_runs_for_the_matrix_and_noise_sounds() {
        let four_octaves_down = -48;
        let oscillator = |on: bool| Value::Map(vec![(spec::ON.into(), on.into()), (spec::RANGE.into(), four_octaves_down.into())]);
        let spec = Value::Map(vec![(
            spec::OSCILLATORS.into(),
            Value::Array(vec![oscillator(false), oscillator(false), oscillator(false)]),
        )]);
        let asheville = compiled(&spec);
        let mut state = OscillatorState::default();
        let mut sides = Vec::new();
        for place in 0..SECOND {
            let out = asheville.sample(&mut state, MIDDLE_C, place as f64 / RATE, Moves::default(), RATE);
            assert_eq!(out, 0.0, "nothing heard");
            sides.push(state.sides[OSC3]);
        }
        let (lowest, highest) = sides.iter().fold((f64::MAX, f64::MIN), |(low, high), side| (low.min(*side), high.max(*side)));
        assert!(highest - lowest > 1.0, "Osc 3 swings for the matrix");
        let noisy = Value::Map(vec![
            (
                spec::OSCILLATORS.into(),
                Value::Array(vec![oscillator(false), oscillator(false), oscillator(false)]),
            ),
            (spec::NOISE.into(), 1.0.into()),
        ]);
        let asheville = compiled(&noisy);
        let most = (0..TENTH_SECOND)
            .map(|place| asheville.sample(&mut state, MIDDLE_C, place as f64 / RATE, Moves::default(), RATE).abs())
            .fold(0.0, f64::max);
        let heard = 0.1;
        assert!(most > heard, "{most}");
    }

    /// Ring alone, Osc 1 times Osc 2 with both out of the mix, still sounds; Snap pulls a Tune near a fifth onto it and
    /// leaves one far from every interval alone.
    #[test]
    fn ring_sounds_alone_and_snap_pulls_toward_fifths() {
        let off = || Value::Map(vec![(spec::ON.into(), false.into())]);
        let spec = Value::Map(vec![
            (spec::OSCILLATORS.into(), Value::Array(vec![off(), off(), off()])),
            (spec::RING.into(), 1.0.into()),
        ]);
        let asheville = compiled(&spec);
        let mut state = OscillatorState::default();
        let most = (0..TENTH_SECOND)
            .map(|place| asheville.sample(&mut state, MIDDLE_C, place as f64 / RATE, Moves::default(), RATE).abs())
            .fold(0.0, f64::max);
        let heard = 0.05;
        assert!(most > heard, "{most}");
        let (near_fifth, fifth, far) = (690.0, 700.0, 350.0);
        let pulled_within = 3.0;
        assert!((snapped(near_fifth) - fifth).abs() < pulled_within);
        assert!((snapped(-near_fifth) + fifth).abs() < pulled_within);
        assert_eq!(snapped(far), far);
    }

    /// An oscillator at an LFO's Speed runs at its own rate whatever the note: two notes an octave apart swing it alike.
    #[test]
    fn an_oscillator_at_an_lfo_speed_ignores_the_note() {
        let swings = |pitch: f64| {
            let lfo_hertz = 2.0;
            let lfo = Value::Map(vec![(spec::ON.into(), false.into()), (spec::HERTZ.into(), lfo_hertz.into())]);
            let off = Value::Map(vec![(spec::ON.into(), false.into())]);
            let spec = Value::Map(vec![(spec::OSCILLATORS.into(), Value::Array(vec![off.clone(), off, lfo]))]);
            let asheville = compiled(&spec);
            let mut state = OscillatorState::default();
            (0..HALF_SECOND)
                .map(|place| {
                    asheville.sample(&mut state, pitch, place as f64 / RATE, Moves::default(), RATE);
                    state.sides[OSC3]
                })
                .collect::<Vec<_>>()
        };
        let (low, high) = (48.0, 60.0);
        assert_eq!(swings(low), swings(high));
    }

    /// A sub is its oscillator divided down: as a note starts, a sub one or two octaves under stands where its oscillator's
    /// phase puts it, so that it switches only where its oscillator's cycle begins.
    #[test]
    fn a_sub_starts_locked_to_its_oscillator() {
        let oscillator = |sub: i64| {
            Value::Map(vec![
                (spec::WAVE.into(), spec::SAW.into()),
                (spec::MIX.into(), 1.0.into()),
                (spec::SUB.into(), sub.into()),
            ])
        };
        let (one_octave_sub, two_octave_sub) = (1, 2);
        let spec = Value::Map(vec![(
            spec::OSCILLATORS.into(),
            Value::Array(vec![oscillator(one_octave_sub), oscillator(two_octave_sub), oscillator(0)]),
        )]);
        let asheville = compiled(&spec);
        let mut state = OscillatorState::default();
        let random = 0.3;
        asheville.begin(&mut state, random);
        let (first, second): (usize, usize) = (0, 1);
        for place in [first, second] {
            let octaves_down = asheville.oscillators[place].sub;
            let divided = state.sub_phases[place] * f64::from(1u32 << octaves_down);
            let tolerance = 1e-12;
            assert!((divided - state.phases[place]).abs() < tolerance, "oscillator {place}");
        }
    }
}
