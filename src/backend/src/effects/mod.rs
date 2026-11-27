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
//! treble turnover, each lifting or cutting by its own number of decibels. MultiTap is a digital delay read at four
//! taps, in a module of its own (`multitap`).

pub mod bucket_brigade;
pub mod drive;
pub mod multitap;

use crate::dsp::blep;
use crate::dsp::{flushed, HIGHEST_SHARE};
use crate::effects::drive::{Curve, Drive};
use crate::effects::multitap::MultiTap;
use crate::protocol::values::{number, truth, word};
use rmpv::Value;
use std::f64::consts::PI;

/// Where Bax's shelves turn over, in hertz, fixed as on a hi-fi tone control.
const BASS_TURNOVER_HERTZ: f64 = 100.0;
const TREBLE_TURNOVER_HERTZ: f64 = 10_000.0;
/// Decibels to a gain: twenty to a power of ten.
const DECIBELS_PER_DECADE: f64 = 20.0;
enum Kind {
    Bitcrush {
        levels: f64,
        /// Whether triangular noise of one code each way is added before the rounding, and its seeded state.
        dither: bool,
        noise: u64,
        step: f64,
        phase: f64,
        held: f64,
        /// The input a sample before, from which a hold falling between samples takes its value.
        previous: f64,
        /// The share of a hold's step smoothing owed to the next sample.
        next: f64,
    },
    Drive(Box<Drive>),
    /// Two shelves one after the other, the bass's and the treble's.
    Bax {
        bass: Shelf,
        treble: Shelf,
    },
    MultiTap(Box<MultiTap>),
}

/// One of Bax's shelves: a first-order filter's two feed-forward coefficients and its feedback, with its last input
/// and output.
struct Shelf {
    forward: f64,
    forward_last: f64,
    back: f64,
    last_in: f64,
    last_out: f64,
}

/// Which end a shelf lifts or cuts: what lies under its turnover, or over it.
#[derive(Clone, Copy, PartialEq, Eq)]
enum End {
    Under,
    Over,
}

/// The circuit's squared gain at some hertz: one end lifted or cut by a gain, turning over at a cutoff, as a gentle
/// shelf of 6 dB an octave.
fn circuit_power(hertz: f64, gain: f64, cutoff: f64, end: End) -> f64 {
    let ratio = hertz / cutoff;
    // The shelf is 1 + (gain - 1) times the share past the turnover: s/(s + c) over it, c/(s + c) under it.
    let (real, imaginary) = match end {
        End::Over => (ratio * ratio, ratio),
        End::Under => (1.0, -ratio),
    };
    let size = 1.0 + ratio * ratio;
    let (past_real, past_imaginary) = (real / size, imaginary / size);
    let response_real = 1.0 + (gain - 1.0) * past_real;
    let response_imaginary = (gain - 1.0) * past_imaginary;
    response_real * response_real + response_imaginary * response_imaginary
}

impl Shelf {
    /// A shelf turning over at some hertz, lifting or cutting one end by some decibels. A cut moves the turnover by the
    /// cut's own gain, so that it is the exact mirror of a lift of as many decibels, as deep and turning at the same
    /// place, rather than a shallower cut.
    // The filter's level is matched to the circuit's at the bottom of the band, at the turnover and at the top, rather
    // than warped by the bilinear transform, which would squeeze the circuit's whole treble into the band and lift too
    // much near its top: after Vicanek, "Matched One-Pole Digital Shelving Filters" (2016). The design's working is our
    // own: a first-order filter's squared level is (B0 + B1 cos w)/(A0 + A1 cos w), and the three levels make a
    // quadratic for its feedback whose roots multiply to one, the stable one taken.
    fn new(decibels: f64, hertz: f64, end: End, rate: f64) -> Shelf {
        let gain = 10f64.powf(decibels / DECIBELS_PER_DECADE);
        let cutoff = match (gain < 1.0, end) {
            (false, _) => hertz,
            (true, End::Under) => hertz / gain,
            (true, End::Over) => hertz * gain,
        };
        let matched = cutoff.min(HIGHEST_SHARE * rate);
        let bottom = circuit_power(0.0, gain, cutoff, end);
        let top = circuit_power(rate / 2.0, gain, cutoff, end);
        let middle = circuit_power(matched, gain, cutoff, end);
        let cosine = (2.0 * PI * matched / rate).cos();
        let (low_share, high_share) = ((1.0 + cosine) / 2.0, (1.0 - cosine) / 2.0);
        let outer = bottom * low_share + top * high_share - middle;
        let inner = 2.0 * (bottom * low_share - top * high_share - middle * cosine);
        let back = if outer.abs() < 1e-12 {
            0.0
        } else {
            let root = (inner * inner - 4.0 * outer * outer).max(0.0).sqrt();
            let first = (-inner + root) / (2.0 * outer);
            if first.abs() <= 1.0 {
                first
            } else {
                1.0 / first
            }
        };
        let at_bottom = bottom.sqrt() * (1.0 + back);
        let at_top = top.sqrt() * (1.0 - back);
        Shelf {
            forward: (at_bottom + at_top) / 2.0,
            forward_last: (at_bottom - at_top) / 2.0,
            back,
            last_in: 0.0,
            last_out: 0.0,
        }
    }

    /// One sample through the shelf.
    #[inline]
    fn process(&mut self, input: f64) -> f64 {
        let out = self.forward * input + self.forward_last * self.last_in - self.back * self.last_out;
        self.last_in = input;
        self.last_out = flushed(out);
        out
    }

    /// Back to rest.
    fn reset(&mut self) {
        self.last_in = 0.0;
        self.last_out = 0.0;
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
            "multitap" => Kind::MultiTap(Box::new(MultiTap::compiled(spec, rate))),
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

/// Where Bitcrush's dither starts, the same every playing.
const DITHER_SEED: u64 = 0x9E37_79B9_7F4A_7C15;

/// Triangular noise from -1 to 1, the sum of two uniform draws, from a seeded xorshift.
#[inline]
fn dither_noise(state: &mut u64) -> f64 {
    let mut draw = || {
        *state ^= *state << 13;
        *state ^= *state >> 7;
        *state ^= *state << 17;
        (*state >> 11) as f64 / (1u64 << 53) as f64
    };
    draw() + draw() - 1.0
}

fn bitcrush(spec: &Value, rate: f64) -> Kind {
    let bits = number(spec, "bits", 16.0);
    let dither = truth(spec, "dither", false);
    let hold_rate = number(spec, "rate", 0.0);
    let levels = if bits < 16.0 { 2f64.powf(bits - 1.0) } else { 0.0 };
    let step = if hold_rate > 0.0 && hold_rate < rate { hold_rate / rate } else { 0.0 };
    Kind::Bitcrush {
        levels,
        dither,
        noise: DITHER_SEED,
        step,
        phase: 0.0,
        held: 0.0,
        previous: 0.0,
        next: 0.0,
    }
}

fn drive(spec: &Value) -> Kind {
    let curve = Curve::named(word(spec, "curve", "soft"));
    Kind::Drive(Box::new(Drive::new(curve, number(spec, "amount", 0.0))))
}

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
            Kind::Bitcrush {
                levels,
                dither,
                noise,
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
                        // A converter of n bits has 2^n codes, two's complement, from -2^(n-1) to 2^(n-1) - 1, so that
                        // silence stays silent and one bit gives two levels.
                        // Dither adds triangular noise of one code each way before the rounding, so that a quiet sound
                        // sinks into a soft hiss rather than into silence or a buzz that follows it.
                        let shaken = if *dither { wet * *levels + dither_noise(noise) } else { wet * *levels };
                        wet = shaken.round().clamp(-*levels, *levels - 1.0) / *levels;
                    }
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
            Kind::Bax { bass, treble } => {
                for sample in buffer.iter_mut() {
                    let dry = *sample as f64;
                    let wet = treble.process(bass.process(dry));
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
                bass.reset();
                treble.reset();
            }
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

    /// A band-limited curve rings a little past full scale where it clips or jumps, as any band-limited square or saw
    /// does, by at most about 9% at a jump of the whole range.
    const BAND_LIMITED_FULL_SCALE: f32 = 1.1;

    /// Every Drive curve keeps a loud sine at full scale, give or take a band-limited clip's ripple, and each curve
    /// shapes it its own way.
    #[test]
    fn every_drive_curve_stays_in_bounds_and_shapes_its_own_way() {
        let loud = 0.9;
        let mut shapes = Vec::new();
        for curve in ["soft", "warm", "hard", "fold", "wrap"] {
            let mut drive = effect(&[("effect", "drive".into()), ("curve", curve.into()), ("amount", 0.8.into())]);
            let mut buffer = sine(loud);
            drive.apply(&mut buffer);
            let most = buffer.iter().fold(0.0f32, |most, sample| most.max(sample.abs()));
            assert!(most <= BAND_LIMITED_FULL_SCALE, "{curve}: {most}");
            shapes.push(buffer);
        }
        for (place, shape) in shapes.iter().enumerate() {
            for other in &shapes[place + 1..] {
                assert_ne!(shape, other);
            }
        }
    }

    /// MultiTap keeps the sound whole and adds its echoes by Mix: a click comes through at full level, and its first echo
    /// at the tap's level times the Mix.
    #[test]
    fn multitap_adds_its_echoes_under_the_whole_sound() {
        let mix = 0.35;
        let level = 0.7;
        let tap = Value::Map(vec![("quarters".into(), 0.5.into()), ("level".into(), level.into())]);
        let mut delay = effect(&[("effect", "multitap".into()), ("taps", Value::Array(vec![tap])), ("mix", mix.into())]);
        let mut buffer = vec![0.0f32; RATE as usize];
        buffer[0] = 1.0;
        delay.apply(&mut buffer);
        let echo = (0.5 * 60.0 / 120.0 * RATE).round() as usize;
        assert_eq!(buffer[0], 1.0);
        assert!((buffer[echo] as f64 - level * mix).abs() < 1e-6, "{}", buffer[echo]);
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

    /// Bax's shelves follow the circuit's own level across the band, to within a third of a decibel at their deepest,
    /// lifting or cutting either end, even near the top of the band, where a warped design strays by three quarters.
    #[test]
    fn bax_follows_the_circuits_level_to_the_top_of_the_band() {
        let near = 0.35;
        for decibels in [15.0, 6.0, -6.0, -15.0] {
            for hertz in [200.0, 2_000.0, 5_000.0, 10_000.0, 15_000.0, 20_000.0] {
                let gain = 10f64.powf(decibels / DECIBELS_PER_DECADE);
                let cutoff = if gain < 1.0 { TREBLE_TURNOVER_HERTZ * gain } else { TREBLE_TURNOVER_HERTZ };
                let circuit = 10.0 * circuit_power(hertz, gain, cutoff, End::Over).log10();
                let heard = through_bax(0.0, decibels, hertz);
                assert!((heard - circuit).abs() < near, "treble {decibels} at {hertz}: {heard} against {circuit}");
            }
            for hertz in [30.0, 100.0, 400.0, 2_000.0] {
                let gain = 10f64.powf(decibels / DECIBELS_PER_DECADE);
                let cutoff = if gain < 1.0 { BASS_TURNOVER_HERTZ / gain } else { BASS_TURNOVER_HERTZ };
                let circuit = 10.0 * circuit_power(hertz, gain, cutoff, End::Under).log10();
                let heard = through_bax(decibels, 0.0, hertz);
                assert!((heard - circuit).abs() < near, "bass {decibels} at {hertz}: {heard} against {circuit}");
            }
        }
    }

    /// Bitcrush's Bits gives a converter's codes, two to the bits: one bit gives two levels, three bits eight.
    #[test]
    fn bitcrush_bits_give_two_to_the_bits_levels() {
        for (bits, codes) in [(1.0, 2), (3.0, 8)] {
            let mut crush = effect(&[("effect", "bitcrush".into()), ("bits", bits.into())]);
            let mut buffer = sine(1.0);
            crush.apply(&mut buffer);
            let mut levels: Vec<i64> = buffer.iter().map(|sample| (*sample as f64 * 1e6).round() as i64).collect();
            levels.sort();
            levels.dedup();
            assert_eq!(levels.len(), codes, "{bits} bits");
        }
    }

    /// Dither keeps a quiet sound: at 8 bits a sine 56 dB down rounds to silence without it, and with it comes through
    /// under a hiss, its shape still there when the hiss is averaged away against the sine.
    #[test]
    fn bitcrush_dither_keeps_a_quiet_sound() {
        let quiet = 10f64.powf(-56.0 / 20.0);
        let heard = |dither: bool| {
            let mut crush = effect(&[("effect", "bitcrush".into()), ("bits", 8.0.into()), ("dither", dither.into())]);
            let mut buffer = sine(quiet);
            let original = buffer.clone();
            crush.apply(&mut buffer);
            let along: f64 = buffer.iter().zip(&original).map(|(out, sine)| *out as f64 * *sine as f64).sum();
            let energy: f64 = original.iter().map(|sine| (*sine as f64).powi(2)).sum();
            along / energy
        };
        assert_eq!(heard(false), 0.0, "rounded to silence");
        let kept = heard(true);
        assert!((kept - 1.0).abs() < 0.2, "the sine comes through: {kept}");
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
