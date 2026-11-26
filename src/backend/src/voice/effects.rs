// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The effects an instrument's blocks hold, each applied to the instrument's mix a sample at a time, keeping what it
//! needs from one chunk to the next, and blended into what came before it by its Mix.
//!
//! The bitcrusher holds each sample for as long as its rate gives, then rounds to its bits. Drive shapes the mix by a
//! curve: soft and warm saturate, warm leaning to one side for even harmonics, hard clips, fold folds back past full scale
//! and wrap wraps round, the last two the harsh digital sounds of cheap grooveboxes. Bax is a tone control after Peter
//! Baxandall's published circuit of 1952: a gentle shelf of 6 dB an octave under its bass turnover and another over its
//! treble turnover, each lifting or cutting by its own number of decibels.

use crate::dsp::HIGHEST_SHARE;
use crate::protocol::values::{number, word};
use crate::voice::blep;
use rmpv::Value;
use std::f64::consts::PI;

const MOST_GAIN: f64 = 20.0;
const MOST_FOLDING_GAIN: f64 = 4.0;
const WARM_LEAN: f64 = 0.3;
/// Where Bax's shelves turn over, in hertz, fixed as on a hi-fi tone control.
const BASS_TURNOVER_HERTZ: f64 = 100.0;
const TREBLE_TURNOVER_HERTZ: f64 = 10_000.0;
/// Decibels to a gain: twenty to a power of ten.
const DECIBELS_PER_DECADE: f64 = 20.0;

#[derive(Clone, Copy, PartialEq, Eq)]
enum Curve {
    Soft,
    Warm,
    Hard,
    Fold,
    Wrap,
}

enum Kind {
    Bitcrush {
        levels: f64,
        step: f64,
        phase: f64,
        held: f64,
        /// The input a sample before, from which a hold falling between samples takes its value.
        previous: f64,
        /// The share of a hold's step smoothing owed to the next sample.
        next: f64,
    },
    Drive {
        curve: Curve,
        gain: f64,
        scale: f64,
        offset: f64,
    },
    /// Two shelves, each the sound plus what lies past its turnover times its gain less one: the bass the share under a
    /// one-pole's cutoff, the treble the share over another's.
    Bax {
        bass: Shelf,
        treble: Shelf,
    },
}

/// One of Bax's shelves: how much it adds of what lies past its turnover (its gain less one, so that 0 dB adds nothing),
/// its one-pole's share for its turnover, and the one-pole's state.
struct Shelf {
    added: f64,
    share: f64,
    state: f64,
}

/// Which end a shelf lifts or cuts: what lies under its turnover, or over it.
#[derive(Clone, Copy, PartialEq, Eq)]
enum End {
    Under,
    Over,
}

impl Shelf {
    /// A shelf turning over at some hertz, lifting or cutting one end by some decibels. A cut moves the one-pole's cutoff
    /// by the cut's own gain, so that it is the exact mirror of a lift of as many decibels, as deep and turning at the same
    /// place, rather than a shallower cut.
    fn new(decibels: f64, hertz: f64, end: End, rate: f64) -> Shelf {
        let gain = 10f64.powf(decibels / DECIBELS_PER_DECADE);
        let cutoff = match (gain < 1.0, end) {
            (false, _) => hertz,
            (true, End::Under) => hertz / gain,
            (true, End::Over) => hertz * gain,
        };
        let g = (PI * cutoff.min(HIGHEST_SHARE * rate) / rate).tan();
        Shelf {
            added: gain - 1.0,
            share: g / (1.0 + g),
            state: 0.0,
        }
    }

    /// The sample's share under the turnover, through a zero-delay one-pole low pass.
    #[inline]
    fn low(&mut self, input: f64) -> f64 {
        let moved = (input - self.state) * self.share;
        let low = moved + self.state;
        self.state = low + moved;
        low
    }
}

pub struct Effect {
    kind: Kind,
    mix: f64,
}

/// An instrument's effects in order, from their specs.
pub fn compiled(specs: &[Value], rate: f64) -> Vec<Effect> {
    let mut effects = Vec::new();
    for spec in specs {
        let mix = number(spec, "mix", 1.0);
        let kind = match word(spec, "effect", "none") {
            "bitcrush" => bitcrush(spec, rate),
            "drive" => drive(spec),
            "bax" => Kind::Bax {
                bass: Shelf::new(number(spec, "bass", 0.0), BASS_TURNOVER_HERTZ, End::Under, rate),
                treble: Shelf::new(number(spec, "treble", 0.0), TREBLE_TURNOVER_HERTZ, End::Over, rate),
            },
            _ => continue,
        };
        effects.push(Effect { kind, mix });
    }
    effects
}

fn bitcrush(spec: &Value, rate: f64) -> Kind {
    let bits = number(spec, "bits", 16.0);
    let hold_rate = number(spec, "rate", 0.0);
    let levels = if bits < 16.0 { 2f64.powf(bits - 1.0) } else { 0.0 };
    let step = if hold_rate > 0.0 && hold_rate < rate { hold_rate / rate } else { 0.0 };
    Kind::Bitcrush {
        levels,
        step,
        phase: 0.0,
        held: 0.0,
        previous: 0.0,
        next: 0.0,
    }
}

fn drive(spec: &Value) -> Kind {
    let curve = match word(spec, "curve", "soft") {
        "warm" => Curve::Warm,
        "hard" => Curve::Hard,
        "fold" => Curve::Fold,
        "wrap" => Curve::Wrap,
        _ => Curve::Soft,
    };
    let most = if matches!(curve, Curve::Fold | Curve::Wrap) {
        MOST_FOLDING_GAIN
    } else {
        MOST_GAIN
    };
    let gain = 1.0 + number(spec, "amount", 0.0) * most;
    let mut offset = 0.0;
    let mut scale = 1.0 / gain.tanh();
    if curve == Curve::Warm {
        // Leaning before the curve and taking the lean's own level away again leaves silence silent; the scale is the larger of
        // the two extremes, so that the curve reaches full scale on one side and stays under it on the other.
        offset = WARM_LEAN.tanh();
        scale = 1.0 / ((gain + WARM_LEAN).tanh() - offset).max(offset - (WARM_LEAN - gain).tanh());
    }
    Kind::Drive { curve, gain, scale, offset }
}

impl Effect {
    /// Shape a chunk of the instrument's mix in place.
    pub fn apply(&mut self, buffer: &mut [f32]) {
        let mix = self.mix;
        match &mut self.kind {
            Kind::Bitcrush {
                levels,
                step,
                phase,
                held,
                previous,
                next,
            } => {
                for sample in buffer.iter_mut() {
                    let dry = *sample as f64;
                    let mut wet = dry;
                    if *step > 0.0 {
                        // The hold falls where its rate puts it, between samples, taking the input as it was at that
                        // moment, and its step is smoothed over this sample and the next, so that any Rate stays in tune.
                        // After Plaits' SampleRateReducer (plaits/dsp/fx/sample_rate_reducer.h, Emilie Gillet, MIT); our
                        // own implementation.
                        let mut this = *next;
                        *next = 0.0;
                        *phase += *step;
                        if *phase >= 1.0 {
                            *phase -= 1.0;
                            let after = *phase / *step;
                            let fresh = *previous + (dry - *previous) * (1.0 - after);
                            let jump = fresh - *held;
                            this += jump * blep::this_sample(after);
                            *next += jump * blep::next_sample(after);
                            *held = fresh;
                        }
                        *next += *held;
                        *previous = dry;
                        wet = this;
                    }
                    if *levels > 0.0 {
                        wet = (wet * *levels).round() / *levels;
                    }
                    *sample = (dry + (wet - dry) * mix) as f32;
                }
            }
            Kind::Drive { curve, gain, scale, offset } => {
                for sample in buffer.iter_mut() {
                    let dry = *sample as f64;
                    let driven = dry * *gain;
                    let wet = match curve {
                        Curve::Soft => driven.tanh() * *scale,
                        Curve::Warm => ((driven + WARM_LEAN).tanh() - *offset) * *scale,
                        Curve::Hard => driven.clamp(-1.0, 1.0),
                        Curve::Fold => (driven * PI / 2.0).sin(),
                        Curve::Wrap => (driven + 1.0).rem_euclid(2.0) - 1.0,
                    };
                    *sample = (dry + (wet - dry) * mix) as f32;
                }
            }
            Kind::Bax { bass, treble } => {
                for sample in buffer.iter_mut() {
                    let dry = *sample as f64;
                    let under = bass.low(dry);
                    let over = dry - treble.low(dry);
                    let wet = dry + bass.added * under + treble.added * over;
                    *sample = (dry + (wet - dry) * mix) as f32;
                }
            }
        }
    }

    /// Back to rest.
    pub fn reset(&mut self) {
        match &mut self.kind {
            Kind::Bitcrush {
                phase, held, previous, next, ..
            } => {
                *phase = 0.0;
                *held = 0.0;
                *previous = 0.0;
                *next = 0.0;
            }
            Kind::Bax { bass, treble } => {
                bass.state = 0.0;
                treble.state = 0.0;
            }
            Kind::Drive { .. } => {}
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn effect(pairs: &[(&str, Value)]) -> Effect {
        let spec = Value::Map(pairs.iter().map(|(key, value)| (Value::from(*key), value.clone())).collect());
        compiled(&[spec], RATE).remove(0)
    }

    const RATE: f64 = 48_000.0;

    fn sine(amplitude: f64) -> Vec<f32> {
        (0..4800)
            .map(|place| (amplitude * (2.0 * PI * 220.0 * place as f64 / RATE).sin()) as f32)
            .collect()
    }

    /// Every Drive curve keeps a loud sine within full scale, and each curve shapes it its own way.
    #[test]
    fn every_drive_curve_stays_in_bounds_and_shapes_its_own_way() {
        let loud = 0.9;
        let mut shapes = Vec::new();
        for curve in ["soft", "warm", "hard", "fold", "wrap"] {
            let mut drive = effect(&[("effect", "drive".into()), ("curve", curve.into()), ("amount", 0.8.into())]);
            let mut buffer = sine(loud);
            drive.apply(&mut buffer);
            assert!(buffer.iter().all(|sample| sample.abs() <= 1.0 + 1e-6), "{curve}");
            shapes.push(buffer);
        }
        for (place, shape) in shapes.iter().enumerate() {
            for other in &shapes[place + 1..] {
                assert_ne!(shape, other);
            }
        }
    }

    /// The level of a steady sine at some hertz through a Bax, once its shelves have settled, against the sine's own.
    fn through_bax(bass: f64, treble: f64, hertz: f64) -> f64 {
        let mut bax = effect(&[("effect", "bax".into()), ("bass", bass.into()), ("treble", treble.into())]);
        let samples = 48_000;
        let mut buffer: Vec<f32> = (0..samples)
            .map(|place| (0.5 * (2.0 * PI * hertz * place as f64 / RATE).sin()) as f32)
            .collect();
        let before: f64 = buffer[samples / 2..].iter().map(|sample| (*sample as f64).powi(2)).sum();
        bax.apply(&mut buffer);
        let after: f64 = buffer[samples / 2..].iter().map(|sample| (*sample as f64).powi(2)).sum();
        DECIBELS_PER_DECADE / 2.0 * (after / before).log10()
    }

    /// Bax at 0 dB leaves the sound as it is; its Bass lifts a low note by its decibels and leaves a high one nearly
    /// alone, and its Treble the other way round, cutting as well as lifting.
    #[test]
    fn bax_lifts_and_cuts_each_end_by_its_decibels() {
        let (low_note, middle, high_note) = (30.0, 1000.0, 18_000.0);
        let (lift, cut, near) = (12.0, -12.0, 1.5);
        assert!(through_bax(0.0, 0.0, middle).abs() < 0.01);
        assert!(
            (through_bax(lift, 0.0, low_note) - lift).abs() < near * 2.0,
            "{}",
            through_bax(lift, 0.0, low_note)
        );
        assert!(through_bax(lift, 0.0, high_note).abs() < near);
        assert!(
            (through_bax(0.0, cut, high_note) - cut).abs() < near * 2.0,
            "{}",
            through_bax(0.0, cut, high_note)
        );
        assert!(through_bax(0.0, cut, low_note).abs() < near);
    }

    /// Bitcrush's Bits leaves only a few levels: three bits give at most nine.
    #[test]
    fn bitcrush_bits_leave_few_levels() {
        let mut crush = effect(&[("effect", "bitcrush".into()), ("bits", 3.0.into())]);
        let mut buffer = sine(1.0);
        crush.apply(&mut buffer);
        let mut levels: Vec<i64> = buffer.iter().map(|sample| (*sample as f64 * 1e6).round() as i64).collect();
        levels.sort();
        levels.dedup();
        assert!(levels.len() <= 9, "{}", levels.len());
    }

    /// Bitcrush's Rate holds at its own rate even where it does not divide the sample rate: a ramp held at 7000 Hz
    /// changes very nearly 7000 times a second, its holds evenly spread, not jumping between whole samples.
    #[test]
    fn bitcrush_rate_holds_at_its_own_rate() {
        let hold_rate = 7_000.0;
        let mut crush = effect(&[("effect", "bitcrush".into()), ("bits", 16.0.into()), ("rate", hold_rate.into())]);
        let mut buffer: Vec<f32> = (0..48_000).map(|place| place as f32 / 48_000.0).collect();
        crush.apply(&mut buffer);
        // Each hold is a step up, smoothed over two samples: count each run of rising samples once.
        let flat = 1e-7;
        let rises: Vec<bool> = buffer.windows(2).map(|pair| (pair[1] - pair[0]) as f64 > flat).collect();
        let steps = rises.windows(2).filter(|pair| pair[1] && !pair[0]).count();
        assert!((steps as f64 - hold_rate).abs() < hold_rate * 0.02, "{steps}");
        // And each step of the ramp is as high as the next, as a hold every 1/7000 s makes it; holds landing only on
        // whole samples, six or seven apart, would make steps a seventh apart.
        // A step is smoothed over two samples, one of which may be nearly flat, so rises fewer than two flat samples apart
        // are one step.
        let mut heights = Vec::new();
        let (mut height, mut flats) = (0.0, 0);
        for pair in buffer.windows(2).skip(4800).take(38_400) {
            let rise = (pair[1] - pair[0]) as f64;
            if rise > flat {
                height += rise;
                flats = 0;
            } else {
                flats += 1;
                if flats >= 2 && height > 0.0 {
                    heights.push(height);
                    height = 0.0;
                }
            }
        }
        // The first and last steps are cut by the stretch's ends.
        let whole = &heights[1..heights.len() - 1];
        let (lowest, highest) = whole.iter().fold((f64::MAX, f64::MIN), |(low, high), each| (low.min(*each), high.max(*each)));
        assert!(highest / lowest < 1.05, "{highest} against {lowest}");
    }
}
