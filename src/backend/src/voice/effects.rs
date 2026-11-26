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
//! taps, each its own time and level, the last fed back through a darkening one-pole so the figure repeats softer.

use crate::dsp::{flushed, HIGHEST_SHARE};
use crate::protocol::values::{as_number, field, list, number, word};
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
/// MultiTap's longest time, in seconds: a bar of 4/4 at 60 quarter notes a minute.
const LONGEST_DELAY_SECONDS: f64 = 4.0;
/// MultiTap's most feedback, short of a repeat as loud as the last, so that it can never run away.
const MOST_FEEDBACK: f64 = 0.9;
/// MultiTap's taps, and the tempo its synced taps follow until the song says.
pub const TAP_COUNT: usize = 4;
const FIRST_TEMPO: f64 = 120.0;
const SECONDS_PER_MINUTE: f64 = 60.0;

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
    MultiTap(Box<MultiTap>),
}

/// When a tap of MultiTap sounds: a share of a quarter note that follows the song's tempo, or seconds of its own.
#[derive(Clone, Copy)]
enum TapTime {
    Quarters(f64),
    Seconds(f64),
}

/// MultiTap: the line it writes into, made ahead and never grown while it plays, where it writes next, each tap's time,
/// samples behind and level, the feedback from the last tap, and the one-pole darkening each repeat.
pub struct MultiTap {
    line: Vec<f32>,
    write: usize,
    times: [TapTime; TAP_COUNT],
    behind: [usize; TAP_COUNT],
    levels: [f64; TAP_COUNT],
    feedback: f64,
    tone: Shelf,
    rate: f64,
}

impl MultiTap {
    /// MultiTap from its spec: its taps, its feedback, its tone in hertz, at the song's tempo until told another.
    fn compiled(spec: &Value, rate: f64) -> MultiTap {
        let taps = list(spec, "taps");
        let mut times = [TapTime::Seconds(0.0); TAP_COUNT];
        let mut levels = [0.0; TAP_COUNT];
        for (place, tap) in taps.iter().take(TAP_COUNT).enumerate() {
            times[place] = match field(tap, "quarters").and_then(as_number) {
                Some(quarters) => TapTime::Quarters(quarters),
                None => TapTime::Seconds(number(tap, "seconds", 0.0)),
            };
            levels[place] = number(tap, "level", 0.0);
        }
        let length = (LONGEST_DELAY_SECONDS * rate) as usize + 1;
        let mut delay = MultiTap {
            line: vec![0.0; length],
            write: 0,
            times,
            behind: [0; TAP_COUNT],
            levels,
            feedback: number(spec, "feedback", 0.0).clamp(0.0, MOST_FEEDBACK),
            // A one-pole low pass is a shelf cutting everything over its cutoff fully: its own low half alone is read.
            tone: Shelf::new(0.0, number(spec, "tone", 6000.0), End::Over, rate),
            rate,
        };
        delay.set_tempo(FIRST_TEMPO);
        delay
    }

    /// The song's tempo now, in quarter notes a minute, which a synced tap's time follows.
    fn set_tempo(&mut self, tempo: f64) {
        let most = self.line.len() - 1;
        for (behind, time) in self.behind.iter_mut().zip(self.times) {
            let seconds = match time {
                TapTime::Quarters(quarters) => quarters * SECONDS_PER_MINUTE / tempo.max(1.0),
                TapTime::Seconds(seconds) => seconds,
            };
            *behind = ((seconds * self.rate).round() as usize).clamp(1, most);
        }
    }

    /// One sample: the four taps' sum, the last tap fed back darkened with the sample into the line.
    #[inline]
    fn process(&mut self, dry: f64) -> f64 {
        let length = self.line.len();
        let read = |behind: usize| self.line[(self.write + length - behind) % length] as f64;
        let mut wet = 0.0;
        for (behind, level) in self.behind.iter().zip(self.levels) {
            wet += read(*behind) * level;
        }
        let last = read(self.behind[TAP_COUNT - 1]);
        let fed = self.tone.low(last) * self.feedback;
        self.line[self.write] = flushed(dry + fed) as f32;
        self.write = (self.write + 1) % length;
        wet
    }

    /// Back to rest: the line silent.
    fn reset(&mut self) {
        self.line.fill(0.0);
        self.tone.state = 0.0;
    }
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
            Kind::MultiTap(delay) => {
                // The echoes alone are the effect's sound: Mix blends them in under the sound that went in.
                for sample in buffer.iter_mut() {
                    let dry = *sample as f64;
                    let wet = delay.process(dry);
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
            Kind::MultiTap(delay) => delay.reset(),
            Kind::Drive { .. } => {}
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

    /// MultiTap spec of four synced taps at their levels, with feedback, heard alone at full Mix.
    fn multitap(feedback: f64) -> Effect {
        let tap = |quarters: f64, level: f64| Value::Map(vec![("quarters".into(), quarters.into()), ("level".into(), level.into())]);
        let taps = Value::Array(vec![tap(0.5, 0.7), tap(1.0, 0.5), tap(1.5, 0.35), tap(2.0, 0.25)]);
        let spec = Value::Map(vec![
            ("effect".into(), "multitap".into()),
            ("taps".into(), taps),
            ("feedback".into(), feedback.into()),
            ("tone".into(), 18_000.0.into()),
            ("mix".into(), 1.0.into()),
        ]);
        compiled(&[spec], RATE).remove(0)
    }

    /// A click through MultiTap at 120 comes back at each tap's time, an eighth, a quarter, a dotted quarter and a half
    /// note, at the tap's level; at 60 every echo comes twice as late.
    #[test]
    fn multitap_echoes_each_tap_on_its_beat() {
        let echoes_of = |tempo: f64| {
            let mut delay = multitap(0.0);
            delay.set_tempo(tempo);
            let samples = (2.5 * RATE) as usize;
            let mut buffer = vec![0.0f32; samples];
            buffer[0] = 1.0;
            for chunk in buffer.chunks_mut(512) {
                delay.apply(chunk);
            }
            let loud: Vec<(usize, f32)> = buffer
                .iter()
                .enumerate()
                .filter(|(_, sample)| sample.abs() > 0.01)
                .map(|(place, sample)| (place, *sample))
                .collect();
            loud
        };
        let beat = |quarters: f64, tempo: f64| (quarters * 60.0 / tempo * RATE).round() as usize;
        let at_120 = echoes_of(120.0);
        let expected: Vec<(usize, f32)> = [(0.5, 0.7), (1.0, 0.5), (1.5, 0.35), (2.0, 0.25)]
            .iter()
            .map(|(quarters, level)| (beat(*quarters, 120.0), *level as f32))
            .collect();
        assert_eq!(at_120, expected);
        let at_60 = echoes_of(60.0);
        assert_eq!(at_60.first().map(|(place, _)| *place), Some(beat(0.5, 60.0)));
    }

    /// Feedback brings the last tap's echo back as the figure again, softer: the first tap is heard again a half note
    /// and an eighth after a burst, at its level times the feedback.
    #[test]
    fn multitap_feedback_repeats_the_figure_softer() {
        let feedback = 0.5;
        let mut delay = multitap(feedback);
        let samples = (2.0 * RATE) as usize;
        let mut buffer = vec![0.0f32; samples];
        // A millisecond's burst rather than a click, so that the darkening Tone's smoothing of one sample does not count.
        let burst = (RATE / 1000.0) as usize;
        buffer[..burst].fill(1.0);
        delay.apply(&mut buffer);
        let again = (2.5 * 60.0 / 120.0 * RATE).round() as usize;
        let heard = buffer[again..again + burst].iter().fold(0.0f32, |most, sample| most.max(sample.abs()));
        assert!((heard as f64 - 0.7 * feedback).abs() < 0.08, "{heard}");
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
