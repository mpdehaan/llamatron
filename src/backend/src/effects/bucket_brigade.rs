// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! MultiTap's Analog mode: a model of a bucket-brigade delay, a chain of stages that a clock passes the sound along, read
//! at four of its stages as a multi-tap device is.
//!
//! One clock moves the whole chain, so that every tap's time is a share of the longest tap's, and a tempo change, or the
//! slow wow and fast flutter of the clock, bends every echo together. The fewer the stages (more Darkness), the slower
//! the clock runs for the same time, and the darker and grainier the echoes. The sound is compressed going in and
//! expanded coming out, so that the hiss inside breathes with it, and each stage it enters saturates softly.

use crate::dsp::{flushed, Random};
use crate::dsp::{DECIBELS_A_DECADE, DECIBEL_BASE};
use std::f64::consts::TAU;

/// The most and fewest stages, at Darkness 0% and 100%; and the most clock ticks a host sample may hold at the stages
/// chosen, so that a short delay never costs more than this.
const MOST_STAGES: f64 = 8192.0;
const FEWEST_STAGES: f64 = 512.0;
const MOST_TICKS_PER_SAMPLE: f64 = 2.0;
/// The poles of each of the device's filters, its input's and its output's, as the circuit's anti-aliasing filters
/// have; the phases of its clock, each moving the charge one stage; the shortest chain it is built of; the spare places
/// of its line; a quarter of the shortest tick the clock may reach, under which a tick never falls; and the share of the
/// stages' rate under which its filters stay.
const POLES: usize = 4;
const CLOCK_PHASES: f64 = 2.0;
const SHORTEST_CHAIN: f64 = 16.0;
const LINE_SPARE: usize = 2;
const TICK_FLOOR_DIVISOR: f64 = 4.0;
const FILTER_SHARE: f64 = 0.45;
/// How often, in samples, the clock's rate, its wow and flutter and the filters' stepping are worked out again.
const CONTROL_SAMPLES: usize = 32;
/// How long a change of time takes to slide most of the way, in seconds: the device's clock glides.
const GLIDE_SECONDS: f64 = 0.3;
/// Wow and flutter at 100%: the most each bends the pitch, as a share, and how fast each moves, in hertz.
const MOST_WOW_PITCH: f64 = 0.01;
const WOW_HERTZ: f64 = 0.6;
const MOST_FLUTTER_PITCH: f64 = 0.02;
const FLUTTER_HERTZ: f64 = 8.0;
/// How much of the wow is a slow random wander rather than a steady swing, and how fast the wander reverts to the middle.
const WANDER_SHARE: f64 = 0.4;
const WANDER_HERTZ: f64 = 0.3;
/// The hiss inside the device at Noise 1% and 100%, in decibels under full scale.
const QUIETEST_HISS_DECIBELS: f64 = -80.0;
const LOUDEST_HISS_DECIBELS: f64 = -50.0;
/// The compander's envelope time, in seconds, and the quietest level it divides by, so that silence is never boosted
/// past 40 dB.
const COMPANDER_SECONDS: f64 = 0.01;
const QUIETEST_LEVEL: f64 = 1e-4;
/// How far under full scale the compressed sound runs through the stages, so that a loud sound saturates them only
/// gently; the expander gives it back.
const HEADROOM: f64 = 0.35;
/// How much Drive at 100% pushes each stage, and leans it to one side for even harmonics.
const MOST_DRIVE_PUSH: f64 = 3.0;
const MOST_DRIVE_LEAN: f64 = 0.25;
/// The high pass that keeps the leaning saturation's offset out of the echoes, in hertz.
const DC_HERTZ: f64 = 10.0;

// The input and output filters of a bucket-brigade device as sums of complex one-poles, residues and poles in radians a
// second at their cutoffs below, after Holters and Parker, "A Combined Model for a Bucket Brigade Device and its Input
// and Output Filters" (DAFx-18), as chowdsp_utils (Jatin Chowdhury, GPL-3.0) gives them in its BBD filter bank. Each
// filter is evaluated at the clock's exact tick times between the host's samples, so that it also does the change of
// rate. Our implementation re-derives the tick-time stepping from the paper's sums, and holds each host sample steady
// over its length going in, as the output holds each stage, so that the input's gain is the same wherever a tick falls.
const INPUT_CUTOFF: f64 = 9900.0;
const OUTPUT_CUTOFF: f64 = 9500.0;
const INPUT_RESIDUES: [(f64, f64); POLES] = [
    (-10329.2715, -329.848),
    (-10329.2715, 329.848),
    (366.990557, -1811.4318),
    (366.990557, 1811.4318),
];
const INPUT_POLES: [(f64, f64); POLES] = [(-55482.0, -25082.0), (-55482.0, 25082.0), (-26292.0, -59437.0), (-26292.0, 59437.0)];
const OUTPUT_RESIDUES: [(f64, f64); POLES] = [(-11256.0, -99566.0), (-11256.0, 99566.0), (-13802.0, -24606.0), (-13802.0, 24606.0)];
const OUTPUT_POLES: [(f64, f64); POLES] = [(-51468.0, -21437.0), (-51468.0, 21437.0), (-26276.0, -59699.0), (-26276.0, 59699.0)];

/// A complex number, as the filters' one-poles need.
#[derive(Clone, Copy, Default)]
struct Complex {
    re: f64,
    im: f64,
}

impl Complex {
    fn of((re, im): (f64, f64)) -> Complex {
        Complex { re, im }
    }

    #[inline]
    fn times(self, other: Complex) -> Complex {
        Complex {
            re: self.re * other.re - self.im * other.im,
            im: self.re * other.im + self.im * other.re,
        }
    }

    #[inline]
    fn scaled(self, by: f64) -> Complex {
        Complex {
            re: self.re * by,
            im: self.im * by,
        }
    }

    #[inline]
    fn plus(self, other: Complex) -> Complex {
        Complex {
            re: self.re + other.re,
            im: self.im + other.im,
        }
    }

    fn over(self, other: Complex) -> Complex {
        let size = other.re * other.re + other.im * other.im;
        Complex {
            re: (self.re * other.re + self.im * other.im) / size,
            im: (self.im * other.re - self.re * other.im) / size,
        }
    }

    /// e to the power of the number.
    fn exp(self) -> Complex {
        let size = self.re.exp();
        Complex {
            re: size * self.im.cos(),
            im: size * self.im.sin(),
        }
    }
}

/// One of the device's filters: its poles and residues moved to its cutoff, each pole's step over one host sample, and
/// each residue over its pole, and the filter's gain at no frequency.
struct Filter {
    poles: [Complex; POLES],
    residues: [Complex; POLES],
    sample_step: [Complex; POLES],
    unstep: [Complex; POLES],
    ratios: [Complex; POLES],
    still_gain: f64,
}

impl Filter {
    /// A filter from its residues and poles, moved from its own cutoff to another, at the host's rate.
    fn new(residues: [(f64, f64); POLES], poles: [(f64, f64); POLES], own_cutoff: f64, cutoff: f64, rate: f64) -> Filter {
        let factor = cutoff / own_cutoff;
        let poles = poles.map(|pole| Complex::of(pole).scaled(factor));
        let residues = residues.map(|residue| Complex::of(residue).scaled(factor));
        let period = 1.0 / rate;
        let still_gain = -(0..POLES).map(|place| residues[place].over(poles[place]).re).sum::<f64>();
        Filter {
            sample_step: poles.map(|pole| pole.scaled(period).exp()),
            unstep: poles.map(|pole| pole.scaled(-period).exp()),
            poles,
            residues,
            ratios: std::array::from_fn(|place| residues[place].over(poles[place])),
            still_gain,
        }
    }

    /// Each pole's e to the pole times some share of a host sample.
    fn stepped(&self, samples: f64, rate: f64) -> [Complex; POLES] {
        self.poles.map(|pole| pole.scaled(samples / rate).exp())
    }
}

/// A clock tick's weights of a filter's poles: what they are at the next tick, and what one tick multiplies them by.
#[derive(Clone, Copy, Default)]
struct Weights {
    now: [Complex; POLES],
    tick: [Complex; POLES],
}

impl Weights {
    #[inline]
    fn advance(&mut self) {
        for (now, tick) in self.now.iter_mut().zip(self.tick) {
            *now = now.times(tick);
        }
    }

    #[inline]
    fn rescale(&mut self, by: &[Complex; POLES]) {
        for (now, by) in self.now.iter_mut().zip(by) {
            *now = now.times(*by);
        }
    }
}

/// An output filter's state, the stage's last value it holds, and what the ticks of this sample add to it.
#[derive(Clone, Copy, Default)]
struct Output {
    state: [Complex; POLES],
    added: [Complex; POLES],
    held: f64,
}

impl Output {
    /// A new value from the chain at a tick: the step from the last one, weighted.
    #[inline]
    fn take(&mut self, value: f64, weights: &[Complex; POLES]) {
        let step = value - self.held;
        self.held = value;
        for (added, weight) in self.added.iter_mut().zip(weights) {
            *added = added.plus(weight.scaled(step));
        }
    }

    /// The filter's output at the end of the sample.
    #[inline]
    fn end_sample(&mut self, filter: &Filter) -> f64 {
        let mut sum = filter.still_gain * self.held;
        for ((state, added), step) in self.state.iter_mut().zip(&mut self.added).zip(filter.sample_step) {
            *state = state.times(step).plus(*added);
            *added = Complex::default();
            sum += state.re;
        }
        flushed(sum)
    }
}

/// A one-pole that follows a signal's level, for the compander.
#[derive(Clone, Copy)]
struct Level {
    share: f64,
    level: f64,
}

impl Level {
    #[inline]
    fn follow(&mut self, signal: f64) -> f64 {
        self.level += (signal.abs() - self.level) * self.share;
        self.level = flushed(self.level);
        self.level.max(QUIETEST_LEVEL)
    }
}

/// What the Analog mode is made from: its taps' times as shares of the longest and their levels, the tap fed back, and
/// its own settings.
pub struct Design {
    pub shares: [f64; POLES],
    pub levels: [f64; POLES],
    pub feedback_from: Option<usize>,
    pub darkness: f64,
    pub noise: f64,
    pub drive: f64,
    pub wow: f64,
    pub flutter: f64,
}

/// The device: its stages, made ahead, where the clock writes next and each tap's stages behind it; the clock's place in
/// the host's sample, its ticks' length and parity; the longest time now and where it glides to; the filters and
/// their weights; the compander; the saturation; the hiss; the wow and flutter.
pub struct BucketBrigade {
    stages: Vec<f32>,
    mask: usize,
    count: usize,
    write: usize,
    behind: [usize; POLES],
    levels: [f64; POLES],
    feedback_from: Option<usize>,
    clock: f64,
    tick_samples: f64,
    writing: bool,
    longest: f64,
    target: f64,
    heard_tempo: bool,
    input_filter: Filter,
    output_filter: Filter,
    input_state: [Complex; POLES],
    input_held: [Complex; POLES],
    input_now: f64,
    input_weights: Weights,
    output_weights: Weights,
    wet: Output,
    fed: Output,
    compressor: Level,
    wet_expander: Level,
    fed_expander: Level,
    push: f64,
    lean: f64,
    lean_offset: f64,
    hiss: f64,
    random: Random,
    wow_depth: f64,
    flutter_depth: f64,
    wow_phase: f64,
    flutter_phase: f64,
    wander: f64,
    countdown: usize,
    dc_share: f64,
    dc_state: f64,
    gain: f64,
    rate: f64,
}

impl BucketBrigade {
    /// The device for a design whose longest tap lasts some seconds, at the host's rate.
    pub fn new(design: &Design, longest: f64, rate: f64) -> BucketBrigade {
        let wanted = MOST_STAGES * (FEWEST_STAGES / MOST_STAGES).powf(design.darkness.clamp(0.0, 1.0));
        let affordable = longest * rate * MOST_TICKS_PER_SAMPLE / CLOCK_PHASES;
        let count = wanted.min(affordable).max(FEWEST_STAGES.min(affordable)).max(SHORTEST_CHAIN) as usize;
        let length = (count + LINE_SPARE).next_power_of_two();
        let behind = design.shares.map(|share| ((share * count as f64).round() as usize).clamp(1, count));
        let hiss = if design.noise <= 0.0 {
            0.0
        } else {
            let decibels = QUIETEST_HISS_DECIBELS + (LOUDEST_HISS_DECIBELS - QUIETEST_HISS_DECIBELS) * design.noise.min(1.0);
            DECIBEL_BASE.powf(decibels / DECIBELS_A_DECADE)
        };
        let follow = 1.0 - (-1.0 / (COMPANDER_SECONDS * rate)).exp();
        let level = Level {
            share: follow,
            level: QUIETEST_LEVEL,
        };
        let push = 1.0 + MOST_DRIVE_PUSH * design.drive.clamp(0.0, 1.0);
        let lean = MOST_DRIVE_LEAN * design.drive.clamp(0.0, 1.0);
        let (input_filter, output_filter) = filters(count, longest, rate);
        let gain = 1.0 / (input_filter.still_gain * output_filter.still_gain);
        let mut device = BucketBrigade {
            stages: vec![0.0; length],
            mask: length - 1,
            count,
            write: 0,
            behind,
            levels: design.levels,
            feedback_from: design.feedback_from,
            clock: 0.0,
            tick_samples: 1.0,
            writing: true,
            longest,
            target: longest,
            heard_tempo: false,
            input_filter,
            output_filter,
            input_state: [Complex::default(); POLES],
            input_held: [Complex::default(); POLES],
            input_now: 0.0,
            input_weights: Weights::default(),
            output_weights: Weights::default(),
            wet: Output::default(),
            fed: Output::default(),
            compressor: level,
            wet_expander: level,
            fed_expander: level,
            push,
            lean,
            lean_offset: lean.tanh(),
            hiss,
            random: Random::new(count as u64),
            wow_depth: design.wow.clamp(0.0, 1.0) * MOST_WOW_PITCH / (TAU * WOW_HERTZ),
            flutter_depth: design.flutter.clamp(0.0, 1.0) * MOST_FLUTTER_PITCH / (TAU * FLUTTER_HERTZ),
            wow_phase: 0.0,
            flutter_phase: 0.0,
            wander: 0.0,
            countdown: 0,
            dc_share: 1.0 - (-TAU * DC_HERTZ / rate).exp(),
            dc_state: 0.0,
            gain,
            rate,
        };
        device.control();
        device
    }

    /// The longest tap's new time, in seconds, as a tempo change gives it: the clock glides there, bending every echo
    /// together, except at the first tempo heard, which is taken at once since nothing has played yet.
    pub fn set_longest(&mut self, seconds: f64) {
        self.target = seconds;
        if !self.heard_tempo {
            self.heard_tempo = true;
            self.longest = seconds;
        }
        let (input_filter, output_filter) = filters(self.count, seconds, self.rate);
        self.input_filter = input_filter;
        self.output_filter = output_filter;
        self.gain = 1.0 / (self.input_filter.still_gain * self.output_filter.still_gain);
        self.control();
    }

    /// The work done every few samples: the glide, the wow and flutter, the clock's tick length, and the filters' weights
    /// at the next tick worked out afresh, so that no error builds up in their stepping.
    fn control(&mut self) {
        let period = CONTROL_SAMPLES as f64 / self.rate;
        let glide = 1.0 - (-period / GLIDE_SECONDS).exp();
        self.longest += (self.target - self.longest) * glide;
        self.wow_phase = (self.wow_phase + TAU * WOW_HERTZ * period) % TAU;
        self.flutter_phase = (self.flutter_phase + TAU * FLUTTER_HERTZ * period) % TAU;
        // A mean-reverting random walk whose spread stays about one half.
        let revert = TAU * WANDER_HERTZ;
        self.wander += -revert * self.wander * period + revert.sqrt() * period.sqrt() * self.random.normal();
        let swing = (1.0 - WANDER_SHARE) * self.wow_phase.sin() + WANDER_SHARE * self.wander;
        let seconds = self.longest + self.wow_depth * swing + self.flutter_depth * self.flutter_phase.sin();
        let tick_samples = seconds * self.rate / (CLOCK_PHASES * self.count as f64);
        self.tick_samples = tick_samples.max(1.0 / (CLOCK_PHASES * MOST_TICKS_PER_SAMPLE * TICK_FLOOR_DIVISOR));
        let next = self.clock;
        let rate = self.rate;
        let input_now = self.input_filter.stepped(next, rate);
        let output_now = self.output_filter.stepped(1.0 - next, rate);
        for place in 0..POLES {
            self.input_weights.now[place] = input_now[place];
            let ratio = self.output_filter.residues[place].over(self.output_filter.poles[place]);
            self.output_weights.now[place] = ratio.times(output_now[place]);
        }
        self.input_weights.tick = self.input_filter.stepped(self.tick_samples, rate);
        self.output_weights.tick = self.output_filter.stepped(-self.tick_samples, rate);
        self.countdown = CONTROL_SAMPLES;
    }

    /// One stage's new value: the filtered input, saturated, with the device's hiss.
    #[inline]
    fn stage_value(&mut self) -> f64 {
        let mut filtered = self.input_filter.still_gain * self.input_now;
        for (weight, state) in self.input_weights.now.iter().zip(&self.input_held) {
            filtered += weight.times(*state).re;
        }
        let saturated = ((self.push * filtered + self.lean).tanh() - self.lean_offset) / self.push;
        let hiss = if self.hiss > 0.0 { self.hiss * self.random.normal() } else { 0.0 };
        saturated + hiss
    }

    /// One sample in, the echoes and the fed-back tap out: the clock's ticks in this sample write the chain and read its
    /// taps, then the filters and the compander finish the sample.
    #[inline]
    pub fn process(&mut self, input: f64) -> (f64, f64) {
        if self.countdown == 0 {
            self.control();
        }
        self.countdown -= 1;
        // The sample is held over its length: each one-pole moves from where it is toward its residue over its pole
        // times the sample.
        let compressed = HEADROOM * input / self.compressor.follow(input).sqrt();
        self.input_now = compressed;
        for ((held, state), ratio) in self.input_held.iter_mut().zip(&self.input_state).zip(self.input_filter.ratios) {
            *held = state.plus(ratio.scaled(compressed));
        }
        while self.clock < 1.0 {
            if self.writing {
                let value = self.stage_value();
                self.stages[self.write] = value as f32;
                self.write = (self.write + 1) & self.mask;
            } else {
                let last = self.write.wrapping_sub(1);
                let mut wet = 0.0;
                for (behind, level) in self.behind.iter().zip(self.levels) {
                    wet += self.stages[last.wrapping_sub(*behind) & self.mask] as f64 * level;
                }
                let fed = match self.feedback_from {
                    Some(tap) => self.stages[last.wrapping_sub(self.behind[tap]) & self.mask] as f64,
                    None => 0.0,
                };
                self.wet.take(wet, &self.output_weights.now);
                self.fed.take(fed, &self.output_weights.now);
            }
            self.writing = !self.writing;
            self.clock += self.tick_samples;
            self.input_weights.advance();
            self.output_weights.advance();
        }
        self.clock -= 1.0;
        // The weights were for times measured from this sample; the next sample's times are one sample nearer.
        self.input_weights.rescale(&self.input_filter.unstep);
        self.output_weights.rescale(&self.output_filter.sample_step);
        for (((state, held), step), ratio) in self
            .input_state
            .iter_mut()
            .zip(self.input_held)
            .zip(self.input_filter.sample_step)
            .zip(self.input_filter.ratios)
        {
            *state = held.times(step).plus(ratio.scaled(-compressed));
            state.re = flushed(state.re);
            state.im = flushed(state.im);
        }
        let wet = self.wet.end_sample(&self.output_filter) * self.gain;
        let fed = self.fed.end_sample(&self.output_filter) * self.gain;
        let restored = HEADROOM * HEADROOM;
        let wet = wet * self.wet_expander.follow(wet) / restored;
        let fed = fed * self.fed_expander.follow(fed) / restored;
        self.dc_state = flushed(self.dc_state + (wet - self.dc_state) * self.dc_share);
        (wet - self.dc_state, fed)
    }

    /// Back to rest: the chain, the filters and the compander silent.
    pub fn reset(&mut self) {
        self.stages.fill(0.0);
        self.input_state = [Complex::default(); POLES];
        self.wet = Output::default();
        self.fed = Output::default();
        for level in [&mut self.compressor, &mut self.wet_expander, &mut self.fed_expander] {
            level.level = QUIETEST_LEVEL;
        }
        self.dc_state = 0.0;
    }
}

/// The device's input and output filters for its stages and longest time: tuned to the device's own rate of stages, as
/// the circuit's filters are sized to its clock, but never above their own cutoffs, so that fewer stages are darker.
fn filters(count: usize, longest: f64, rate: f64) -> (Filter, Filter) {
    let stage_rate = count as f64 / longest.max(1.0 / rate);
    let limit = FILTER_SHARE * stage_rate;
    let input = Filter::new(INPUT_RESIDUES, INPUT_POLES, INPUT_CUTOFF, INPUT_CUTOFF.min(limit), rate);
    let output = Filter::new(OUTPUT_RESIDUES, OUTPUT_POLES, OUTPUT_CUTOFF, OUTPUT_CUTOFF.min(limit), rate);
    (input, output)
}

#[cfg(test)]
mod tests {
    use super::*;

    use crate::dsp::testing::{sine, HALF_SECOND, RATE, SECOND};

    /// The taps' shares of the longest time, a quarter apart, the first alone heard; the level of the tones tried; the
    /// longest time tried, in seconds; and a click's length, a millisecond.
    const TAP_SHARES: [f64; POLES] = [0.25, 0.5, 0.75, 1.0];
    const FIRST_TAP_ALONE: [f64; POLES] = [1.0, 0.0, 0.0, 0.0];
    const TONE_LEVEL: f64 = 0.5;
    const LONGEST: f64 = 0.4;
    const CLICK_SAMPLES: usize = 48;

    /// A device's design of a Darkness, its first tap alone heard, with no noise, drive, wow or flutter.
    fn design(darkness: f64) -> Design {
        Design {
            shares: TAP_SHARES,
            levels: FIRST_TAP_ALONE,
            feedback_from: None,
            darkness,
            noise: 0.0,
            drive: 0.0,
            wow: 0.0,
            flutter: 0.0,
        }
    }

    /// The level of a steady sine at some hertz through the device, once it has settled, against the sine's own.
    fn through(device: &mut BucketBrigade, hertz: f64, amplitude: f64) -> f64 {
        let mut loudest: f64 = 0.0;
        for place in 0..SECOND {
            let (wet, _) = device.process(sine(hertz, amplitude, place));
            if place > HALF_SECOND {
                loudest = loudest.max(wet.abs());
            }
        }
        loudest / amplitude
    }

    /// A low tone comes through the first tap near its own level, and a bright one is cut, the more so with more
    /// Darkness: the device's filters follow its clock.
    #[test]
    fn low_tones_pass_and_darkness_darkens() {
        let (bass, near_its_level, treble, darker) = (200.0, 0.15, 3000.0, 0.5);
        let mut bright = BucketBrigade::new(&design(0.0), LONGEST, RATE);
        let low = through(&mut bright, bass, TONE_LEVEL);
        assert!((low - 1.0).abs() < near_its_level, "{low}");
        let mut bright = BucketBrigade::new(&design(0.0), LONGEST, RATE);
        let mut dark = BucketBrigade::new(&design(1.0), LONGEST, RATE);
        let (open, shut) = (through(&mut bright, treble, TONE_LEVEL), through(&mut dark, treble, TONE_LEVEL));
        assert!(shut < open * darker, "{shut} against {open}");
    }

    /// A click comes back at the tap's share of the longest time, near its moment.
    #[test]
    fn a_click_comes_back_at_its_taps_time() {
        let mut device = BucketBrigade::new(&design(0.0), LONGEST, RATE);
        let heard: Vec<f64> = (0..SECOND)
            .map(|place| device.process(if place < CLICK_SAMPLES { TONE_LEVEL } else { 0.0 }).0)
            .collect();
        let loudest = heard
            .iter()
            .enumerate()
            .max_by(|one, other| one.1.abs().total_cmp(&other.1.abs()))
            .map(|(place, _)| place)
            .unwrap_or(0);
        let first_share = TAP_SHARES[0];
        let near_its_moment = 0.01;
        let expected = first_share * LONGEST * RATE;
        assert!((loudest as f64 - expected).abs() < near_its_moment * RATE, "{loudest} against {expected}");
    }

    /// A tempo change glides the clock: the echo of a steady tone bends in pitch for a while and settles, and the
    /// device's output never jumps between two samples further than it moved before the change.
    #[test]
    fn a_new_time_glides_without_a_jump() {
        let (hertz, longer, grown) = (220.0, 0.6, 1.2);
        let mut device = BucketBrigade::new(&design(0.0), LONGEST, RATE);
        device.set_longest(LONGEST);
        let tone = |place: usize| sine(hertz, TONE_LEVEL, place);
        let settle = SECOND;
        let mut last = 0.0;
        let mut steady_step: f64 = 0.0;
        for place in 0..settle {
            let out = device.process(tone(place)).0;
            if place > HALF_SECOND {
                steady_step = steady_step.max((out - last).abs());
            }
            last = out;
        }
        device.set_longest(longer);
        let mut largest_step: f64 = 0.0;
        for place in settle..settle + SECOND {
            let out = device.process(tone(place)).0;
            largest_step = largest_step.max((out - last).abs());
            last = out;
        }
        // Gliding a sixth longer lowers the pitch by at most a sixth, so the steps between samples shrink rather than grow.
        assert!(largest_step < steady_step * grown, "{largest_step} against {steady_step}");
    }

    /// The hiss falls away in silence, as a compander makes it: with no sound in, it stays under the quietest it may be.
    #[test]
    fn the_hiss_falls_away_in_silence() {
        let mut noisy = design(0.0);
        noisy.noise = 1.0;
        let short = 0.2;
        let mut device = BucketBrigade::new(&noisy, short, RATE);
        let mut quiet_level: f64 = 0.0;
        for _ in 0..SECOND {
            quiet_level = quiet_level.max(device.process(0.0).0.abs());
        }
        let loudest_hiss = DECIBEL_BASE.powf(LOUDEST_HISS_DECIBELS / DECIBELS_A_DECADE);
        assert!(quiet_level < loudest_hiss, "{quiet_level}");
    }
}
