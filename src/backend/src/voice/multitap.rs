// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! MultiTap: a digital delay read at four taps, each its own time, level and switch, one of them fed back through a low
//! cut and a darkening low pass so that the figure repeats softer and thinner.
//!
//! The line is a power of two long, so that a read wraps by a mask rather than a division, and every read is a 4-point
//! Hermite interpolation, exact where a time falls on a whole sample. A changed time, as a synced tap's is when the tempo
//! moves, never jumps: Fade crossfades from the old read head to the new over half the delay, held between 10 and 500 ms,
//! and Glide slews the read time so that the echoes bend in pitch, as tape does. The crossfade's timing follows Surge's
//! sst-effects Delay.h (the Surge Synth Team, GPL-3.0-or-later); the implementation here is our own.

use crate::dsp::{flushed, HIGHEST_SHARE};
use crate::protocol::values::{as_number, field, list, number, truth, word};
use crate::voice::bucket_brigade::{BucketBrigade, Design};
use rmpv::Value;
use std::f64::consts::PI;

/// The taps, and the longest time a tap reaches, in seconds: a bar of 4/4 at 60 quarter notes a minute.
pub const TAP_COUNT: usize = 4;
const LONGEST_DELAY_SECONDS: f64 = 4.0;
/// The most feedback, short of a repeat as loud as the last, so that it can never run away.
const MOST_FEEDBACK: f64 = 0.9;
/// The tempo synced taps follow until the song says, and seconds to a minute.
const FIRST_TEMPO: f64 = 120.0;
const SECONDS_PER_MINUTE: f64 = 60.0;
/// The shortest time a tap reads, in samples: the interpolation reads one sample newer than its own.
const SHORTEST_DELAY: f64 = 2.0;
/// A Fade lasts half the delay, held between these, in seconds; a change under half a sample is no change.
const SHORTEST_FADE_SECONDS: f64 = 0.01;
const LONGEST_FADE_SECONDS: f64 = 0.5;
const SMALLEST_CHANGE: f64 = 0.5;
/// How long a Glide takes to cover most of a change, in seconds: its one-pole's time constant.
const GLIDE_SECONDS: f64 = 0.15;

/// When a tap sounds: a share of a quarter note that follows the song's tempo, or seconds of its own.
#[derive(Clone, Copy)]
enum TapTime {
    Quarters(f64),
    Seconds(f64),
}

/// How a changed time is reached: by crossfading to a new read head, or by sliding the read head there.
#[derive(Clone, Copy, PartialEq, Eq)]
enum Change {
    Fade,
    Glide,
}

/// One tap: its time, whether it sounds, its level, where it reads now in samples behind the write head, and while a
/// Fade runs, where it read before, how far the fade has come and how far a sample moves it, with a change that came
/// while it ran.
#[derive(Clone, Copy)]
struct Tap {
    time: TapTime,
    on: bool,
    level: f64,
    behind: f64,
    target: f64,
    from: f64,
    fade: f64,
    fade_step: f64,
    waiting: Option<f64>,
}

/// A one-pole low pass in its zero-delay form, its share of the way to the input a sample.
#[derive(Clone, Copy)]
struct OnePole {
    share: f64,
    state: f64,
}

impl OnePole {
    /// A one-pole with its cutoff at some hertz.
    fn new(hertz: f64, rate: f64) -> OnePole {
        let g = (PI * hertz.min(HIGHEST_SHARE * rate) / rate).tan();
        OnePole {
            share: g / (1.0 + g),
            state: 0.0,
        }
    }

    /// The sample's share under the cutoff.
    #[inline]
    fn low(&mut self, input: f64) -> f64 {
        let moved = (input - self.state) * self.share;
        let low = moved + self.state;
        self.state = low + moved;
        low
    }
}

/// MultiTap: the line, made ahead and never grown while it plays, its mask and where it writes next; the taps; which tap
/// feeds back and how much; the loop's darkening low pass and its low cut; and how a changed time is reached.
pub struct MultiTap {
    line: Vec<f32>,
    mask: usize,
    write: usize,
    taps: [Tap; TAP_COUNT],
    feedback_from: usize,
    feedback: f64,
    tone: OnePole,
    low_cut: OnePole,
    change: Change,
    glide_share: f64,
    rate: f64,
    analog: Option<Box<BucketBrigade>>,
    looped: f64,
}

impl MultiTap {
    /// MultiTap from its spec: its taps, its feedback and where from, its tone and low cut in hertz, and how a time
    /// changes, at the song's tempo until told another.
    pub fn compiled(spec: &Value, rate: f64) -> MultiTap {
        let mut taps = [Tap {
            time: TapTime::Seconds(0.0),
            on: true,
            level: 0.0,
            behind: SHORTEST_DELAY,
            target: SHORTEST_DELAY,
            from: SHORTEST_DELAY,
            fade: 1.0,
            fade_step: 0.0,
            waiting: None,
        }; TAP_COUNT];
        for (tap, given) in taps.iter_mut().zip(list(spec, "taps")) {
            tap.time = match field(given, "quarters").and_then(as_number) {
                Some(quarters) => TapTime::Quarters(quarters),
                None => TapTime::Seconds(number(given, "seconds", 0.0)),
            };
            tap.level = number(given, "level", 0.0);
            tap.on = truth(given, "on", true);
        }
        let length = ((LONGEST_DELAY_SECONDS * rate) as usize + 4).next_power_of_two();
        let change = if word(spec, "time_change", "fade") == "glide" {
            Change::Glide
        } else {
            Change::Fade
        };
        let mut delay = MultiTap {
            line: vec![0.0; length],
            mask: length - 1,
            write: 0,
            taps,
            feedback_from: (number(spec, "feedback_from", TAP_COUNT as f64) as usize).clamp(1, TAP_COUNT) - 1,
            feedback: number(spec, "feedback", 0.0).clamp(0.0, MOST_FEEDBACK),
            tone: OnePole::new(number(spec, "tone", 6000.0), rate),
            low_cut: OnePole::new(number(spec, "low_cut", 80.0), rate),
            change,
            glide_share: 1.0 - (-1.0 / (GLIDE_SECONDS * rate)).exp(),
            rate,
            analog: None,
            looped: 0.0,
        };
        // The first times are reached at once: nothing has been written to fade from yet.
        let first = delay.targets(FIRST_TEMPO);
        for (tap, target) in delay.taps.iter_mut().zip(first) {
            tap.behind = target;
            tap.target = target;
            tap.from = target;
        }
        if word(spec, "mode", "digital") == "analog" {
            delay.analog = Some(Box::new(delay.bucket_brigade(spec)));
        }
        delay
    }

    /// The Analog mode's device: every tap's time a share of the longest, as taps along one chain on one clock are, a
    /// tap switched off silent, and the device's own settings.
    fn bucket_brigade(&self, spec: &Value) -> BucketBrigade {
        let longest = self.taps.iter().map(|tap| tap.target).fold(SHORTEST_DELAY, f64::max);
        let design = Design {
            shares: self.taps.map(|tap| tap.target / longest),
            levels: self.taps.map(|tap| if tap.on { tap.level } else { 0.0 }),
            feedback_from: Some(self.feedback_from).filter(|tap| self.taps[*tap].on),
            darkness: number(spec, "darkness", 0.35),
            noise: number(spec, "noise", 0.15),
            drive: number(spec, "drive", 0.3),
            wow: number(spec, "wow", 0.1),
            flutter: number(spec, "flutter", 0.05),
        };
        BucketBrigade::new(&design, longest / self.rate, self.rate)
    }

    /// Each tap's time in samples at a tempo, held between the shortest the interpolation reads and the line's length.
    fn targets(&self, tempo: f64) -> [f64; TAP_COUNT] {
        let longest = (self.line.len() - 4) as f64;
        std::array::from_fn(|place| {
            let seconds = match self.taps[place].time {
                TapTime::Quarters(quarters) => quarters * SECONDS_PER_MINUTE / tempo.max(1.0),
                TapTime::Seconds(seconds) => seconds,
            };
            (seconds * self.rate).clamp(SHORTEST_DELAY, longest)
        })
    }

    /// The song's tempo now, in quarter notes a minute: each synced tap moves to its new time, by Fade or Glide.
    pub fn set_tempo(&mut self, tempo: f64) {
        let targets = self.targets(tempo);
        if let Some(device) = &mut self.analog {
            let longest = targets.iter().copied().fold(SHORTEST_DELAY, f64::max);
            device.set_longest(longest / self.rate);
            return;
        }
        let (change, rate) = (self.change, self.rate);
        for (tap, target) in self.taps.iter_mut().zip(targets) {
            if (target - tap.target).abs() < SMALLEST_CHANGE {
                continue;
            }
            match change {
                Change::Glide => tap.target = target,
                Change::Fade if tap.fade < 1.0 => tap.waiting = Some(target),
                Change::Fade => start_fade(tap, target, rate),
            }
        }
    }

    /// The line's sample a whole number of samples behind the write head.
    #[inline]
    fn at(&self, behind: usize) -> f64 {
        self.line[self.write.wrapping_sub(behind) & self.mask] as f64
    }

    /// The line read a fractional number of samples behind the write head, by 4-point Hermite interpolation: exact on a
    /// whole sample, smooth between, and steady as the time moves.
    #[inline]
    fn read(&self, behind: f64) -> f64 {
        let whole = behind.floor();
        let t = behind - whole;
        let whole = whole as usize;
        let (newer, x0, x1, older) = (self.at(whole - 1), self.at(whole), self.at(whole + 1), self.at(whole + 2));
        let c1 = 0.5 * (x1 - newer);
        let c2 = newer - 2.5 * x0 + 2.0 * x1 - 0.5 * older;
        let c3 = 0.5 * (older - newer) + 1.5 * (x0 - x1);
        ((c3 * t + c2) * t + c1) * t + x0
    }

    /// A tap's sound now: its read head, or the crossfade from its old one while a Fade runs.
    #[inline]
    fn tap_out(&self, tap: &Tap) -> f64 {
        if tap.fade < 1.0 {
            self.read(tap.from) * (1.0 - tap.fade) + self.read(tap.behind) * tap.fade
        } else {
            self.read(tap.behind)
        }
    }

    /// One sample: the sounding taps' sum; the chosen tap, if it sounds, fed back through the low cut and the tone with
    /// the sample into the line; and each tap's read head moved on toward its time.
    #[inline]
    pub fn process(&mut self, dry: f64) -> f64 {
        if let Some(device) = &mut self.analog {
            let (wet, fed) = device.process(dry + self.looped);
            let darkened = self.tone.low(fed);
            self.looped = flushed((darkened - self.low_cut.low(darkened)) * self.feedback);
            return wet;
        }
        let mut wet = 0.0;
        let mut fed = 0.0;
        for (place, tap) in self.taps.iter().enumerate() {
            if !tap.on {
                continue;
            }
            let out = self.tap_out(tap);
            wet += out * tap.level;
            if place == self.feedback_from {
                fed = out;
            }
        }
        let darkened = self.tone.low(fed);
        let thinned = darkened - self.low_cut.low(darkened);
        self.line[self.write] = flushed(dry + thinned * self.feedback) as f32;
        self.write = (self.write + 1) & self.mask;
        let (change, glide_share, rate) = (self.change, self.glide_share, self.rate);
        for tap in self.taps.iter_mut() {
            match change {
                Change::Glide => tap.behind += (tap.target - tap.behind) * glide_share,
                Change::Fade if tap.fade < 1.0 => {
                    tap.fade = (tap.fade + tap.fade_step).min(1.0);
                    if tap.fade >= 1.0 {
                        tap.from = tap.behind;
                        if let Some(waiting) = tap.waiting.take() {
                            start_fade(tap, waiting, rate);
                        }
                    }
                }
                Change::Fade => {}
            }
        }
        wet
    }

    /// Back to rest: the line and the loop's filters silent.
    pub fn reset(&mut self) {
        self.line.fill(0.0);
        self.looped = 0.0;
        if let Some(device) = &mut self.analog {
            device.reset();
        }
        self.tone.state = 0.0;
        self.low_cut.state = 0.0;
    }
}

/// Start a tap's crossfade from where it reads now to a new time, over half the new delay, held between 10 and 500 ms.
fn start_fade(tap: &mut Tap, target: f64, rate: f64) {
    let seconds = (0.5 * target / rate).clamp(SHORTEST_FADE_SECONDS, LONGEST_FADE_SECONDS);
    tap.from = tap.behind;
    tap.behind = target;
    tap.target = target;
    tap.fade = 0.0;
    tap.fade_step = 1.0 / (seconds * rate);
}

#[cfg(test)]
mod tests {
    use super::*;

    const RATE: f64 = 48_000.0;

    /// MultiTap of four synced taps at their levels and switches, with feedback from a tap, its Low Cut at the bottom.
    fn multitap(feedback: f64, change: &str, on: [bool; TAP_COUNT], feedback_from: i64) -> MultiTap {
        let levels = [0.7, 0.5, 0.35, 0.25];
        let quarters = [0.5, 1.0, 1.5, 2.0];
        let taps = (0..TAP_COUNT)
            .map(|place| {
                Value::Map(vec![
                    ("quarters".into(), quarters[place].into()),
                    ("level".into(), levels[place].into()),
                    ("on".into(), on[place].into()),
                ])
            })
            .collect();
        let spec = Value::Map(vec![
            ("taps".into(), Value::Array(taps)),
            ("feedback".into(), feedback.into()),
            ("feedback_from".into(), feedback_from.into()),
            ("tone".into(), 18_000.0.into()),
            ("low_cut".into(), 20.0.into()),
            ("time_change".into(), change.into()),
        ]);
        MultiTap::compiled(&spec, RATE)
    }

    /// The echoes of a click, each loud sample after the click's own and where it falls.
    fn echoes(delay: &mut MultiTap, seconds: f64) -> Vec<(usize, f64)> {
        let samples = (seconds * RATE) as usize;
        (0..samples)
            .map(|place| delay.process(if place == 0 { 1.0 } else { 0.0 }))
            .enumerate()
            .filter(|(_, sample)| sample.abs() > 0.01)
            .collect()
    }

    fn beat(quarters: f64, tempo: f64) -> usize {
        (quarters * SECONDS_PER_MINUTE / tempo * RATE).round() as usize
    }

    /// A click comes back at each tap's time, an eighth, a quarter, a dotted quarter and a half note at 120, at the tap's
    /// level, exactly on its sample; a tap switched off is silent.
    #[test]
    fn each_tap_echoes_on_its_beat_and_a_tap_off_is_silent() {
        let all = [true; TAP_COUNT];
        let mut delay = multitap(0.0, "fade", all, 4);
        let expected: Vec<(usize, f64)> = [(0.5, 0.7), (1.0, 0.5), (1.5, 0.35), (2.0, 0.25)]
            .iter()
            .map(|(quarters, level)| (beat(*quarters, FIRST_TEMPO), *level))
            .collect();
        let heard = echoes(&mut delay, 1.2);
        assert_eq!(heard.len(), expected.len());
        for ((place, level), (at, want)) in heard.iter().zip(&expected) {
            assert_eq!(place, at);
            assert!((level - want).abs() < 1e-6, "{level} against {want}");
        }
        let mut second_off = multitap(0.0, "fade", [true, false, true, true], 4);
        let heard = echoes(&mut second_off, 1.2);
        assert!(heard.iter().all(|(place, _)| *place != beat(1.0, FIRST_TEMPO)));
    }

    /// The loudest sample of a millisecond's burst's echoes around a place, a burst rather than a click so that the
    /// loop's filters smoothing one sample do not count.
    fn heard_around(delay: &mut MultiTap, place: usize) -> f64 {
        let burst = (RATE / 1000.0) as usize;
        let out: Vec<f64> = (0..place + 2 * burst).map(|at| delay.process(if at < burst { 1.0 } else { 0.0 })).collect();
        out[place..].iter().fold(0.0, |most, sample| most.max(sample.abs()))
    }

    /// Feedback repeats from the tap chosen: from the dotted quarter, the quarter tap comes again a dotted quarter later,
    /// at its level times the feedback; a tap switched off feeds nothing back.
    #[test]
    fn feedback_comes_from_the_tap_chosen() {
        let feedback = 0.5;
        let again = beat(1.5, FIRST_TEMPO) + beat(1.0, FIRST_TEMPO);
        let mut delay = multitap(feedback, "fade", [true; TAP_COUNT], 3);
        let repeat = heard_around(&mut delay, again);
        assert!((repeat - 0.5 * feedback).abs() < 0.03, "{repeat}");
        let mut silent_source = multitap(feedback, "fade", [true, true, false, true], 3);
        assert!(heard_around(&mut silent_source, again) < 0.01);
    }

    /// A tempo change never jumps a read head: a steady tone through a tap stays free of clicks as the tempo halves, by
    /// Fade and by Glide alike, where an abrupt jump would leave a step between two samples.
    #[test]
    fn a_tempo_change_moves_the_taps_without_a_click() {
        for change in ["fade", "glide"] {
            let mut delay = multitap(0.0, change, [true, false, false, false], 4);
            let hertz = 110.0;
            let tone = |place: usize| (2.0 * PI * hertz * place as f64 / RATE).sin();
            let settle = RATE as usize;
            for place in 0..settle {
                delay.process(tone(place));
            }
            let mut last = delay.process(tone(settle));
            delay.set_tempo(FIRST_TEMPO / 2.0);
            let mut largest_step: f64 = 0.0;
            for place in settle + 1..settle + RATE as usize {
                let out = delay.process(tone(place));
                largest_step = largest_step.max((out - last).abs());
                last = out;
            }
            // A sine of this pitch at this level moves at most this far between samples; a jump would move much further.
            let steepest = 0.7 * 2.0 * PI * hertz / RATE;
            assert!(largest_step < steepest * 1.5, "{change}: {largest_step}");
        }
    }
}
