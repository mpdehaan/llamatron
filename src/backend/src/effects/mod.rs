// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The effects an instrument's blocks hold, each applied to the instrument's mix a sample at a time, keeping what it
//! needs from one chunk to the next, and blended into what came before it by its Mix.
//!
//! Each effect is a module of its own: Bitcrush (`bitcrush`), Drive (`drive`), Bax (`bax`) and MultiTap (`multitap`,
//! with its Analog mode's device in `bucket_brigade`).

pub mod bax;
pub mod bitcrush;
pub mod bucket_brigade;
pub mod drive;
pub mod multitap;

use crate::effects::bax::Bax;
use crate::effects::bitcrush::Bitcrush;
use crate::effects::drive::{Curve, Drive};
use crate::effects::multitap::MultiTap;
use crate::protocol::values::{number, word};
use crate::registry::{self, Entry};
use llamatron_names::spec;
use rmpv::Value;

/// What an effect is, as its entry builds it.
pub enum Kind {
    Bitcrush(Box<Bitcrush>),
    Drive(Box<Drive>),
    Bax(Box<Bax>),
    MultiTap(Box<MultiTap>),
}

pub struct Effect {
    kind: Kind,
    mix: f64,
}

/// An instrument's effects in order, from their specs.
pub fn compiled(specs: &[Value], rate: f64) -> Vec<Effect> {
    let mut effects = Vec::new();
    for spec in specs {
        let mix = number(spec, spec::MIX, 1.0);
        // An empty block, or a name no registry holds, adds no effect.
        let Some(entry) = registry::find(REGISTRY, word(spec, spec::EFFECT, EMPTY)) else {
            continue;
        };
        effects.push(Effect {
            kind: (entry.build)(spec, rate),
            mix,
        });
    }
    effects
}

/// How an effect is built: from its spec, at a sample rate.
pub type Build = fn(&Value, f64) -> Kind;

/// An effect block's name when it holds none.
pub const EMPTY: &str = spec::NONE;

/// Every effect, by the name a spec gives it, the file that holds it, and how it is built.
pub static REGISTRY: &[Entry<Build>] = &[
    Entry {
        name: spec::BAX,
        file: "bax.rs",
        build: |spec, rate| Kind::Bax(Box::new(Bax::compiled(spec, rate))),
    },
    Entry {
        name: spec::BITCRUSH,
        file: "bitcrush.rs",
        build: |spec, rate| Kind::Bitcrush(Box::new(Bitcrush::compiled(spec, rate))),
    },
    Entry {
        name: spec::DRIVE,
        file: "drive.rs",
        build: |spec, _rate| {
            let curve = Curve::named(word(spec, spec::CURVE, spec::SOFT));
            Kind::Drive(Box::new(Drive::new(curve, number(spec, spec::AMOUNT, 0.0))))
        },
    },
    Entry {
        name: spec::MULTITAP,
        file: "multitap.rs",
        build: |spec, rate| Kind::MultiTap(Box::new(MultiTap::compiled(spec, rate))),
    },
];

/// The files of the effects' folder that are no effect of their own but a part one uses: MultiTap's Analog device.
pub const HELPERS: &[&str] = &["bucket_brigade.rs"];

/// What an effect with no memory of its own keeps sounding after its input falls silent: its oversampler's and filters'
/// settling, in samples.
const SHORT_TAIL_SAMPLES: usize = 4096;

impl Effect {
    /// How many samples the effect keeps sounding after its input falls silent.
    pub fn tail_samples(&self) -> usize {
        match &self.kind {
            Kind::MultiTap(delay) => delay.tail_samples(),
            _ => SHORT_TAIL_SAMPLES,
        }
    }

    /// Shape a chunk of the instrument's mix in place.
    pub fn apply(&mut self, buffer: &mut [f32]) {
        let mix = self.mix;
        match &mut self.kind {
            Kind::Bitcrush(crusher) => {
                for sample in buffer.iter_mut() {
                    let dry = *sample as f64;
                    let wet = crusher.process(dry);
                    *sample = (dry + (wet - dry) * mix) as f32;
                }
            }
            Kind::Drive(drive) => {
                for sample in buffer.iter_mut() {
                    *sample = drive.process(*sample as f64, mix) as f32;
                }
            }
            Kind::MultiTap(delay) => {
                // Echoes add to the sound rather than replace it: the sound stays whole and Mix sets how loud they come in.
                for sample in buffer.iter_mut() {
                    let dry = *sample as f64;
                    let wet = delay.process(dry);
                    *sample = (dry + wet * mix) as f32;
                }
            }
            Kind::Bax(bax) => {
                for sample in buffer.iter_mut() {
                    let dry = *sample as f64;
                    let wet = bax.process(dry);
                    *sample = (dry + (wet - dry) * mix) as f32;
                }
            }
        }
    }

    /// Back to rest.
    pub fn reset(&mut self) {
        match &mut self.kind {
            Kind::Bitcrush(crusher) => crusher.reset(),
            Kind::Bax(bax) => bax.reset(),
            Kind::MultiTap(delay) => delay.reset(),
            Kind::Drive(drive) => drive.reset(),
        }
    }

    /// The song's tempo now, in quarter notes a minute, which a synced delay's taps follow.
    pub fn set_tempo(&mut self, tempo: f64) {
        if let Kind::MultiTap(delay) = &mut self.kind {
            delay.set_tempo(tempo);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dsp::testing::{self, SECOND, TENTH_SECOND};
    use crate::dsp::{DECIBELS_A_DECADE, DECIBEL_BASE};
    use crate::engine::{FIRST_TEMPO, SECONDS_A_MINUTE};

    /// The tone the tests crush, in hertz; a click's echo's length in quarter notes; and how near a level counts as
    /// exact.
    const TONE_HERTZ: f64 = 220.0;
    const ECHO_QUARTERS: f64 = 0.5;
    const EXACT: f64 = 1e-6;
    /// Two neighbouring samples, a rise read from.
    const PAIR: usize = 2;

    fn effect(pairs: &[(&str, Value)]) -> Effect {
        let spec = Value::Map(pairs.iter().map(|(key, value)| (Value::from(*key), value.clone())).collect());
        compiled(&[spec], RATE).remove(0)
    }

    const RATE: f64 = testing::RATE;

    /// A tenth of a second of the tests' tone at an amplitude.
    fn sine(amplitude: f64) -> Vec<f32> {
        (0..TENTH_SECOND).map(|place| testing::sine(TONE_HERTZ, amplitude, place) as f32).collect()
    }

    /// MultiTap keeps the sound whole and adds its echoes by Mix: a click comes through at full level, and its first echo
    /// at the tap's level times the Mix.
    #[test]
    fn multitap_adds_its_echoes_under_the_whole_sound() {
        let mix = 0.35;
        let level = 0.7;
        let tap = Value::Map(vec![(spec::QUARTERS.into(), ECHO_QUARTERS.into()), (spec::LEVEL.into(), level.into())]);
        let mut delay = effect(&[
            (spec::EFFECT, spec::MULTITAP.into()),
            (spec::TAPS, Value::Array(vec![tap])),
            (spec::MIX, mix.into()),
        ]);
        let mut buffer = vec![0.0f32; RATE as usize];
        buffer[0] = 1.0;
        delay.apply(&mut buffer);
        let echo = (ECHO_QUARTERS * SECONDS_A_MINUTE / FIRST_TEMPO * RATE).round() as usize;
        assert_eq!(buffer[0], 1.0);
        assert!((buffer[echo] as f64 - level * mix).abs() < EXACT, "{}", buffer[echo]);
    }

    /// Bitcrush's Bits gives a converter's codes, two to the bits: one bit gives two levels, three bits eight.
    #[test]
    fn bitcrush_bits_give_two_to_the_bits_levels() {
        let one_bit_and_three = [(1.0, 2), (3.0, 8)];
        for (bits, codes) in one_bit_and_three {
            let mut crush = effect(&[(spec::EFFECT, spec::BITCRUSH.into()), (spec::BITS, bits.into())]);
            let mut buffer = sine(1.0);
            crush.apply(&mut buffer);
            let mut levels: Vec<i64> = buffer.iter().map(|sample| (*sample as f64 / EXACT).round() as i64).collect();
            levels.sort();
            levels.dedup();
            assert_eq!(levels.len(), codes, "{bits} bits");
        }
    }

    /// Dither keeps a quiet sound: at 8 bits a sine 56 dB down rounds to silence without it, and with it comes through
    /// under a hiss, its shape still there when the hiss is averaged away against the sine.
    #[test]
    fn bitcrush_dither_keeps_a_quiet_sound() {
        let (quiet_decibels, bits) = (-56.0, 8.0);
        let quiet = DECIBEL_BASE.powf(quiet_decibels / DECIBELS_A_DECADE);
        let heard = |dither: bool| {
            let mut crush = effect(&[(spec::EFFECT, spec::BITCRUSH.into()), (spec::BITS, bits.into()), (spec::DITHER, dither.into())]);
            let mut buffer = sine(quiet);
            let original = buffer.clone();
            crush.apply(&mut buffer);
            let along: f64 = buffer.iter().zip(&original).map(|(out, sine)| *out as f64 * *sine as f64).sum();
            let energy: f64 = original.iter().map(|sine| *sine as f64 * *sine as f64).sum();
            along / energy
        };
        assert_eq!(heard(false), 0.0, "rounded to silence");
        let kept = heard(true);
        let near = 0.2;
        assert!((kept - 1.0).abs() < near, "the sine comes through: {kept}");
    }

    /// Bitcrush's Rate holds at its own rate even where it does not divide the sample rate: a ramp held at 7000 Hz
    /// changes very nearly 7000 times a second, its holds evenly spread, not jumping between whole samples.
    #[test]
    fn bitcrush_rate_holds_at_its_own_rate() {
        let hold_rate = 7_000.0;
        let uncrushed_bits = 16.0;
        let mut crush = effect(&[
            (spec::EFFECT, spec::BITCRUSH.into()),
            (spec::BITS, uncrushed_bits.into()),
            (spec::RATE, hold_rate.into()),
        ]);
        let mut buffer: Vec<f32> = (0..SECOND).map(|place| place as f32 / SECOND as f32).collect();
        crush.apply(&mut buffer);
        // Each hold is a step up, smoothed over two samples: count each run of rising samples once.
        let flat = 1e-7;
        let rises: Vec<bool> = buffer.windows(PAIR).map(|pair| (pair[1] - pair[0]) as f64 > flat).collect();
        let steps = rises.windows(PAIR).filter(|pair| pair[1] && !pair[0]).count();
        let share_off = 0.02;
        assert!((steps as f64 - hold_rate).abs() < hold_rate * share_off, "{steps}");
        // And each step of the ramp is as high as the next, as a hold every 1/7000 s makes it; holds landing only on
        // whole samples, six or seven apart, would make steps a seventh apart.
        // A step is smoothed over two samples, one of which may be nearly flat, so rises fewer than two flat samples apart
        // are one step.
        let mut heights = Vec::new();
        let (mut height, mut flats) = (0.0, 0);
        let (settled, stretch) = (TENTH_SECOND, SECOND - TENTH_SECOND - TENTH_SECOND);
        for pair in buffer.windows(PAIR).skip(settled).take(stretch) {
            let rise = (pair[1] - pair[0]) as f64;
            if rise > flat {
                height += rise;
                flats = 0;
            } else {
                flats += 1;
                if flats >= PAIR && height > 0.0 {
                    heights.push(height);
                    height = 0.0;
                }
            }
        }
        // The first and last steps are cut by the stretch's ends.
        let whole = &heights[1..heights.len() - 1];
        let (lowest, highest) = whole.iter().fold((f64::MAX, f64::MIN), |(low, high), each| (low.min(*each), high.max(*each)));
        let even = 1.05;
        assert!(highest / lowest < even, "{highest} against {lowest}");
    }
}
