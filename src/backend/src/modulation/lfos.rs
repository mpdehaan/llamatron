// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The LFOs: an instrument has four, each a shape, a rate in hertz, whether a note starts its cycle again and whether each
//! scene does; their values over a chunk are worked out once before the voices read them. An LFO+ may also fade in after
//! each note, which each voice applies by its own age, and may follow the song's tempo, its cycle a division of the beat.
//! A Mod Matrix slot may move an LFO's rate by an LFO, another or itself: those routes are the bank's, read a sample at a
//! time as the LFOs advance. A slot may hold a Snail in place of an LFO (`snail`), its nine outputs worked out over the
//! chunk as the LFOs' are, its weightings moved by the bank's own sources.

use crate::dsp::blep::blep;
use crate::dsp::Random;
use crate::engine::MOST_FRAMES;
use crate::modulation::matrix::{BankSource, RateRoute, WeightRoute};
use crate::modulation::snail::{Snail, OUTPUT_COUNT, WEIGHTED_COUNT};
use crate::protocol::values::{number, word};
use crate::registry::{self, Named};
use rmpv::Value;
use std::f64::consts::PI;

pub const LFO_COUNT: usize = 4;
const HELD_VALUES: usize = 4096;
const HELD_SEED: u64 = 224;

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Shape {
    Sine,
    Triangle,
    SawUp,
    SawDown,
    Square,
    SampleAndHold,
    /// A random value each cycle, glided to along a cosine rather than stepped.
    SmoothRandom,
}

/// When an LFO's cycle starts again: at each note, at each scene, when playback starts from silence, or never, standing
/// still while playback is stopped and going on from there when it starts again.
#[derive(Clone, Copy, PartialEq, Eq)]
enum Restart {
    EachNote,
    EachScene,
    OnPlay,
    Never,
}

struct Lfo {
    shape: Shape,
    step: f64,
    /// The multiple of the note's frequency it runs at where it follows the key, as an FM modulator does.
    ratio: Option<f64>,
    restart: Restart,
    cycles: f64,
    /// How long its depth takes to rise after a note starts, in seconds; 0 for no fade.
    fade: f64,
    /// Where it follows the song's tempo, how many quarter notes a cycle lasts.
    quarters: Option<f64>,
}

/// The shape an LFO takes when its spec names none.
const SINE: &str = "sine";

/// Every LFO shape a spec may name, and what it is.
pub static SHAPES: &[Named<Shape>] = &[
    Named {
        name: SINE,
        value: Shape::Sine,
    },
    Named {
        name: "triangle",
        value: Shape::Triangle,
    },
    Named {
        name: "saw_up",
        value: Shape::SawUp,
    },
    Named {
        name: "saw_down",
        value: Shape::SawDown,
    },
    Named {
        name: "square",
        value: Shape::Square,
    },
    Named {
        name: "sample_and_hold",
        value: Shape::SampleAndHold,
    },
    Named {
        name: "smooth_random",
        value: Shape::SmoothRandom,
    },
];

/// An instrument's four LFOs, None for one that is off, and what each gave the chunk now playing.
pub struct LfoBank {
    lfos: Vec<Option<Lfo>>,
    /// The Snails, in the slots that hold one, each with its seed by its slot, and the outputs it gave each sample of
    /// the chunk now playing.
    snails: Vec<Option<Snail>>,
    pub snail_now: Vec<Vec<[f64; OUTPUT_COUNT]>>,
    /// The Mod Matrix's routes that move a Snail's weighting, and what each Snail gave the sample before, which those
    /// routes read.
    weight_routes: Vec<WeightRoute>,
    snail_last: [[f64; OUTPUT_COUNT]; LFO_COUNT],
    held: Vec<f64>,
    pub now: Vec<Vec<f64>>,
    /// The Mod Matrix's routes that move an LFO's rate by other LFOs, or by itself, and what each LFO gave the sample
    /// before, which those routes read.
    rate_routes: Vec<RateRoute>,
    last: [f64; LFO_COUNT],
    /// The sample rate, from which a tempo LFO's step is worked out whenever the tempo changes.
    rate: f64,
    /// How many players play the instrument now, and whether all have stopped, so that its LFOs stand still, costing
    /// nothing, until playback starts again.
    players: u32,
    stopped: bool,
}

/// What a slot holds when its spec names a type: a Snail; any other is an LFO.
const SNAIL_TYPE: &str = "snail";
/// The settings of a Snail's weightings, Slow's and Slower's, each a fraction from -1 to 1.
const WEIGHTINGS: [&str; WEIGHTED_COUNT] = ["slow", "slower"];

/// The seed of a slot's Snail, from its instrument's number and its slot's place, so that two Snails differ.
fn snail_seed(instrument: u64, place: usize) -> u64 {
    instrument.wrapping_mul(LFO_COUNT as u64).wrapping_add(place as u64)
}

/// A slot's Snail where its spec names one, seeded by an instrument's number.
fn snail_of(spec: &Value, instrument: u64, place: usize) -> Option<Snail> {
    if spec.is_nil() || word(spec, "type", "lfo") != SNAIL_TYPE {
        return None;
    }
    let weightings = std::array::from_fn(|circuit| number(spec, WEIGHTINGS[circuit], 0.0).clamp(-1.0, 1.0));
    let given = crate::protocol::values::field(spec, "seconds").and_then(Value::as_array);
    let trips = std::array::from_fn(|lane| given.and_then(|seconds| seconds.get(lane)).and_then(crate::protocol::values::as_number));
    Some(Snail::seeded(snail_seed(instrument, place), weightings, trips))
}

/// The tempo a song is taken to play at until it says, in quarter notes a minute.
const FIRST_TEMPO: f64 = 120.0;
const SECONDS_PER_MINUTE: f64 = 60.0;

impl LfoBank {
    /// The bank a spec's list of slots describes, at a sample rate.
    pub fn compiled(specs: &[Value], rate: f64) -> LfoBank {
        let mut random = Random::new(HELD_SEED);
        let held = (0..HELD_VALUES).map(|_| random.between(-1.0, 1.0)).collect();
        let lfos = (0..LFO_COUNT)
            .map(|place| {
                let spec = specs.get(place)?;
                if spec.is_nil() || word(spec, "type", "lfo") == SNAIL_TYPE {
                    return None;
                }
                let shape = registry::named(SHAPES, word(spec, "shape", SINE)).unwrap_or(Shape::Sine);
                let quarters = crate::protocol::values::field(spec, "quarters").and_then(crate::protocol::values::as_number);
                let step = match quarters {
                    Some(quarters) => tempo_step(FIRST_TEMPO, quarters, rate),
                    None => number(spec, "rate", 1.0) / rate,
                };
                Some(Lfo {
                    shape,
                    step,
                    fade: number(spec, "fade_in", 0.0).max(0.0),
                    quarters,
                    ratio: crate::protocol::values::field(spec, "key_ratio").and_then(crate::protocol::values::as_number),
                    restart: match word(spec, "restart", "on_play") {
                        "each_note" => Restart::EachNote,
                        "each_scene" => Restart::EachScene,
                        "never" => Restart::Never,
                        _ => Restart::OnPlay,
                    },
                    cycles: 0.0,
                })
            })
            .collect();
        let no_spec = Value::Nil;
        let snails: Vec<Option<Snail>> = (0..LFO_COUNT).map(|place| snail_of(specs.get(place).unwrap_or(&no_spec), 0, place)).collect();
        let snail_now = snails
            .iter()
            .map(|snail| {
                if snail.is_some() {
                    vec![[0.0; OUTPUT_COUNT]; MOST_FRAMES]
                } else {
                    Vec::new()
                }
            })
            .collect();
        LfoBank {
            lfos,
            snails,
            snail_now,
            weight_routes: Vec::new(),
            snail_last: [[0.0; OUTPUT_COUNT]; LFO_COUNT],
            held,
            now: (0..LFO_COUNT).map(|_| vec![0.0; MOST_FRAMES]).collect(),
            rate_routes: Vec::new(),
            last: [0.0; LFO_COUNT],
            rate,
            players: 0,
            stopped: false,
        }
    }

    /// Playback of the instrument started: from silence, every On play LFO starts its cycle from zero; while something
    /// already plays it, nothing restarts. A Snail never starts again: it goes on from where it stood.
    pub fn play_started(&mut self) {
        if self.players == 0 {
            for lfo in self.lfos.iter_mut().flatten() {
                if lfo.restart == Restart::OnPlay {
                    lfo.cycles = 0.0;
                }
            }
        }
        self.players += 1;
        self.stopped = false;
    }

    /// A playback of the instrument stopped; once none plays it, its LFOs stand still.
    pub fn play_stopped(&mut self) {
        self.players = self.players.saturating_sub(1);
        if self.players == 0 {
            self.stopped = true;
        }
    }

    /// The song's tempo now, in quarter notes a minute, which every LFO following it takes its step from.
    pub fn set_tempo(&mut self, tempo: f64) {
        let rate = self.rate;
        for lfo in self.lfos.iter_mut().flatten() {
            if let Some(quarters) = lfo.quarters {
                lfo.step = tempo_step(tempo, quarters, rate);
            }
        }
    }

    /// How long each LFO's depth takes to rise after a note starts, in seconds, 0 for those that do not fade in.
    pub fn fades(&self) -> [f64; LFO_COUNT] {
        std::array::from_fn(|place| self.lfos.get(place).and_then(Option::as_ref).map_or(0.0, |lfo| lfo.fade))
    }

    /// Whether any LFO is on and moving: none stands still while playback is stopped.
    pub fn is_on(&self) -> bool {
        !self.stopped && (self.lfos.iter().any(Option::is_some) || self.snails.iter().any(Option::is_some))
    }

    /// Seed every Snail by its instrument's number, so that two instruments' Snails wander differently.
    pub fn seed(&mut self, instrument: u64) {
        for (place, snail) in self.snails.iter_mut().enumerate() {
            if let Some(snail) = snail.as_mut() {
                *snail = Snail::seeded(snail_seed(instrument, place), snail.weightings, snail.trips);
            }
        }
    }

    /// The bank with the Mod Matrix's routes that move its Snails' weightings.
    pub fn with_weight_routes(mut self, routes: Vec<WeightRoute>) -> LfoBank {
        self.weight_routes = routes;
        self
    }

    /// The bank with the Mod Matrix's routes that move its LFOs' rates.
    pub fn with_rate_routes(mut self, routes: Vec<RateRoute>) -> LfoBank {
        self.rate_routes = routes;
        self
    }

    /// Work out what the LFOs and Snails give the chunk ahead, the Snails' weightings moved by the instrument's CCs, as
    /// their last messages left them from 0 to 1, and by what the newest note's routes move them by.
    pub fn advance(&mut self, frames: usize, controls: &[f64], noted: &[[f64; WEIGHTED_COUNT]; LFO_COUNT]) {
        let frames = frames.min(MOST_FRAMES);
        if !self.rate_routes.is_empty() {
            self.advance_moving_rates(frames);
        } else {
            self.advance_lfos(frames);
        }
        if self.snails.iter().any(Option::is_some) {
            self.advance_snails(frames, controls, noted);
        }
    }

    /// Work out the chunk ahead of the LFOs whose rates nothing moves.
    fn advance_lfos(&mut self, frames: usize) {
        for (lfo, values) in self.lfos.iter_mut().zip(self.now.iter_mut()) {
            // A Key LFO follows each note's own pitch, so each voice works out its own (key_lfo_value).
            let Some(lfo) = lfo.as_mut().filter(|lfo| lfo.ratio.is_none()) else {
                continue;
            };
            for value in values.iter_mut().take(frames) {
                *value = shaped(lfo.shape, lfo.cycles, lfo.step, &self.held);
                lfo.cycles = (lfo.cycles + lfo.step) % HELD_VALUES as f64;
            }
        }
    }

    /// Work out the chunk ahead where LFOs move each other's rates: a sample at a time, every LFO together, each rate
    /// moved by octaves from what its sources gave the sample before, so that the order of the LFOs never matters.
    // Each sample is written into every LFO's own buffer at once, so the sample's index is the plain way to reach them.
    #[allow(clippy::needless_range_loop)]
    fn advance_moving_rates(&mut self, frames: usize) {
        let LfoBank {
            lfos,
            held,
            now,
            rate_routes,
            last,
            ..
        } = self;
        for sample in 0..frames {
            let mut octaves = [0.0; LFO_COUNT];
            for route in rate_routes.iter() {
                let mut value = last[route.source] * route.reach + route.offset;
                if let Some(via) = route.via {
                    value *= last[via];
                }
                octaves[route.target] += value;
            }
            for (place, lfo) in lfos.iter_mut().enumerate() {
                // A Key LFO follows each note's own pitch, so each voice works out its own (key_lfo_value).
                let Some(lfo) = lfo.as_mut().filter(|lfo| lfo.ratio.is_none()) else {
                    continue;
                };
                let step = lfo.step * octaves[place].exp2();
                let value = shaped(lfo.shape, lfo.cycles, step, held);
                now[place][sample] = value;
                last[place] = value;
                lfo.cycles = (lfo.cycles + step) % HELD_VALUES as f64;
            }
        }
    }

    /// Work out the chunk ahead of the Snails, a sample at a time, every Snail together: each weighting moved by what
    /// its routes read, an LFO's value at the sample or a Snail's output at the sample before, so that the order of the
    /// slots never matters.
    fn advance_snails(&mut self, frames: usize, controls: &[f64], noted: &[[f64; WEIGHTED_COUNT]; LFO_COUNT]) {
        let seconds = 1.0 / self.rate;
        let LfoBank {
            snails,
            snail_now,
            weight_routes,
            snail_last,
            now,
            ..
        } = self;
        let read = |source: BankSource, sample: usize, last: &[[f64; OUTPUT_COUNT]; LFO_COUNT]| match source {
            BankSource::Lfo(place) => now[place][sample],
            BankSource::Snail(slot, output) => last[slot][output],
            BankSource::Control(number) => controls.get(number as usize).copied().unwrap_or(0.0),
        };
        for sample in 0..frames {
            let mut moved = *noted;
            for route in weight_routes.iter() {
                let mut value = read(route.source, sample, snail_last) * route.reach + route.offset;
                if let Some(via) = route.via {
                    value *= read(via, sample, snail_last);
                }
                moved[route.slot][route.circuit] += value;
            }
            for (place, snail) in snails.iter_mut().enumerate() {
                let Some(snail) = snail.as_mut() else { continue };
                snail.advance(seconds, moved[place], &mut snail_now[place][sample]);
            }
            for (place, outputs) in snail_now.iter().enumerate() {
                if let Some(outputs) = outputs.get(sample) {
                    snail_last[place] = *outputs;
                }
            }
        }
    }

    /// The multiple of the note's frequency an LFO runs at where it follows the key, or None where it has a rate of its own.
    pub fn ratio(&self, place: usize) -> Option<f64> {
        self.lfos.get(place)?.as_ref()?.ratio
    }

    /// A Key LFO's value at a voice's own phase, moved on by a step of the note's frequency times its ratio over the rate.
    pub fn key_lfo_value(&self, place: usize, cycles: &mut f64, step: f64) -> f64 {
        let Some(Some(lfo)) = self.lfos.get(place) else { return 0.0 };
        let value = shaped(lfo.shape, *cycles, step, &self.held);
        *cycles = (*cycles + step) % HELD_VALUES as f64;
        value
    }

    /// Start again every LFO that retriggers, as a note begins.
    pub fn note_on(&mut self) {
        for lfo in self.lfos.iter_mut().flatten() {
            if lfo.restart == Restart::EachNote {
                lfo.cycles = 0.0;
            }
        }
    }

    /// Start again every LFO that restarts each scene.
    pub fn scene_started(&mut self) {
        for lfo in self.lfos.iter_mut().flatten() {
            if lfo.restart == Restart::EachScene {
                lfo.cycles = 0.0;
            }
        }
    }
}

/// The cycles a sample of an LFO lasting some quarter notes a cycle moves on at a tempo.
fn tempo_step(tempo: f64, quarters: f64, rate: f64) -> f64 {
    tempo.max(1.0) / SECONDS_PER_MINUTE / quarters.max(f64::MIN_POSITIVE) / rate
}

/// How far an LFO fading in over some seconds has risen at an age into its note, from 0 to 1 along an S curve, so that
/// the depth eases in and settles without a corner.
#[inline]
pub fn faded_in(age: f64, fade: f64) -> f64 {
    if fade <= 0.0 || age >= fade {
        return 1.0;
    }
    let x = (age / fade).max(0.0);
    x * x * (3.0 - 2.0 * x)
}

/// A shape's value at a place in its cycles, its steps of step cycles a sample. The saws' and the square's jumps are
/// smoothed by a two-sample polyBLEP, so that at audio rate they do not alias; at an LFO's slow rates the smoothing spans
/// a vanishing share of a cycle and changes nothing heard.
// The polyBLEP of voice/blep.rs, after stmlib's (Emilie Gillet, MIT).
#[inline]
fn shaped(shape: Shape, cycles: f64, step: f64, held: &[f64]) -> f64 {
    let place = cycles.fract();
    match shape {
        Shape::Sine => (2.0 * PI * place).sin(),
        Shape::Triangle => 1.0 - 4.0 * (place - 0.5).abs(),
        Shape::SawUp => 2.0 * place - 1.0 - blep(place, step),
        Shape::SawDown => 1.0 - 2.0 * place + blep(place, step),
        Shape::Square => {
            let level = if place < 0.5 { 1.0 } else { -1.0 };
            level + blep(place, step) - blep((place + 0.5).fract(), step)
        }
        Shape::SampleAndHold => held[cycles as usize % HELD_VALUES],
        Shape::SmoothRandom => {
            let from = held[cycles as usize % HELD_VALUES];
            let to = held[(cycles as usize + 1) % HELD_VALUES];
            from + (to - from) * (1.0 - (PI * place).cos()) / 2.0
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::modulation::matrix::rate_routes;

    const RATE: f64 = 48_000.0;

    fn bank(pairs: &[(&str, Value)]) -> LfoBank {
        let spec = Value::Map(pairs.iter().map(|(key, value)| (Value::from(*key), value.clone())).collect());
        LfoBank::compiled(&[spec], RATE)
    }

    /// The cycles an LFO's values start again in a chunk: each rise through zero.
    fn rises(values: &[f64]) -> usize {
        values.windows(2).filter(|pair| pair[0] < 0.0 && pair[1] >= 0.0).count()
    }

    /// A slot moving an LFO's rate by another LFO doubles it at half the Amount while its source stays at the top: a
    /// slow square held high doubles a 10 Hz sine's cycles. A slot reading anything but an LFO moves no rate.
    #[test]
    fn an_lfo_moves_another_lfos_rate() {
        let lfo = |shape: &str, hertz: f64| Value::Map(vec![("shape".into(), shape.into()), ("rate".into(), hertz.into())]);
        let slot = |source: &str, amount: f64| {
            Value::Map(vec![
                ("source".into(), source.into()),
                ("destination".into(), "lfo1_rate".into()),
                ("amount".into(), amount.into()),
            ])
        };
        let cycles = |slots: Vec<Value>| {
            // The square at half a hertz holds at its top for its first second, the whole of the half second read.
            let specs = [lfo("sine", 10.0), lfo("square", 0.5)];
            let mut bank = LfoBank::compiled(&specs, RATE).with_rate_routes(rate_routes(&slots));
            let half_second = (RATE / 2.0) as usize;
            let mut rises_seen = 0;
            let mut done = 0;
            while done < half_second {
                let frames = MOST_FRAMES.min(half_second - done);
                bank.advance(frames, &[], &[[0.0; WEIGHTED_COUNT]; LFO_COUNT]);
                rises_seen += rises(&bank.now[0][..frames]);
                done += frames;
            }
            rises_seen
        };
        let one_octave = 0.5;
        let cycles_of_10_hertz_in_half_a_second = 5;
        let still = cycles(Vec::new());
        let doubled = cycles(vec![slot("lfo2", one_octave)]);
        assert!((still as i64 - cycles_of_10_hertz_in_half_a_second).abs() <= 1, "{still}");
        assert!((doubled as i64 - 2 * still as i64).abs() <= 1, "{doubled} against {still}");
        assert_eq!(cycles(vec![slot("velocity", one_octave)]), still);
    }

    /// A Smooth random LFO glides between its random values: no sample jumps as Sample & Hold's steps do.
    #[test]
    fn smooth_random_glides_where_sample_and_hold_steps() {
        let most_jump = |shape: &str| {
            let mut lfos = bank(&[("shape", shape.into()), ("rate", 10.0.into())]);
            lfos.advance(MOST_FRAMES, &[], &[[0.0; WEIGHTED_COUNT]; LFO_COUNT]);
            lfos.now[0]
                .windows(2)
                .take(MOST_FRAMES - 1)
                .map(|pair| (pair[1] - pair[0]).abs())
                .fold(0.0, f64::max)
        };
        let gliding_step = 0.01;
        assert!(most_jump("smooth_random") < gliding_step, "{}", most_jump("smooth_random"));
        assert!(most_jump("sample_and_hold") > gliding_step);
    }

    /// An LFO following the tempo runs a cycle a division of the beat: a quarter note at 120 is two cycles a second,
    /// and doubling the tempo doubles it.
    #[test]
    fn a_tempo_lfo_follows_the_song_tempo() {
        let quarter = 1.0;
        let mut lfos = bank(&[("shape", "saw_up".into()), ("quarters", quarter.into())]);
        let cycles_in = |lfos: &mut LfoBank| {
            let before = lfos.lfos[0].as_ref().expect("an LFO").cycles;
            lfos.advance(RATE as usize / 8, &[], &[[0.0; WEIGHTED_COUNT]; LFO_COUNT]);
            lfos.lfos[0].as_ref().expect("an LFO").cycles - before
        };
        let eighth_second = 1.0 / 8.0;
        let at_120 = cycles_in(&mut lfos);
        assert!((at_120 - 2.0 * eighth_second).abs() < 1e-6, "{at_120}");
        lfos.set_tempo(240.0);
        let at_240 = cycles_in(&mut lfos);
        assert!((at_240 - 2.0 * at_120).abs() < 1e-6, "{at_240}");
    }

    /// An On play LFO stands still while playback is stopped and starts from zero when it starts from silence; a Never one
    /// goes on from where it stood; a second player starting while one plays restarts nothing.
    #[test]
    fn on_play_starts_from_zero_and_never_goes_on() {
        let mut lfos = LfoBank::compiled(
            &[
                Value::Map(vec![("restart".into(), "on_play".into()), ("rate".into(), 1.0.into())]),
                Value::Map(vec![("restart".into(), "never".into()), ("rate".into(), 1.0.into())]),
            ],
            RATE,
        );
        let cycles = |lfos: &LfoBank, place: usize| lfos.lfos[place].as_ref().expect("an LFO").cycles;
        lfos.play_started();
        lfos.advance(MOST_FRAMES, &[], &[[0.0; WEIGHTED_COUNT]; LFO_COUNT]);
        let reached = cycles(&lfos, 1);
        lfos.play_started();
        assert!(cycles(&lfos, 0) > 0.0, "a second start while playing restarts nothing");
        lfos.play_stopped();
        lfos.play_stopped();
        assert!(!lfos.is_on(), "stopped, it stands still");
        lfos.play_started();
        assert_eq!(cycles(&lfos, 0), 0.0);
        assert_eq!(cycles(&lfos, 1), reached);
    }

    /// Fade in rises from nothing at the note's start to full at its time, smoothly, and is full at once with no fade.
    #[test]
    fn fade_in_eases_from_nothing_to_full() {
        let fade = 2.0;
        assert_eq!(faded_in(0.0, fade), 0.0);
        assert!((faded_in(fade / 2.0, fade) - 0.5).abs() < 1e-12);
        assert_eq!(faded_in(fade, fade), 1.0);
        assert_eq!(faded_in(0.0, 0.0), 1.0);
        assert!(bank(&[("fade_in", fade.into())]).fades()[0] == fade);
    }

    /// A Mod Matrix route from an LFO to a Snail's Slow weighting moves the path Slow takes, leaning it the whole time
    /// where the route is Unipolar.
    #[test]
    fn an_lfo_routed_to_a_snails_weighting_moves_its_path() {
        let heard_seconds = 60.0;
        let specs = [Value::Map(vec![("type".into(), "snail".into())]), Value::Map(vec![("rate".into(), 0.5.into())])];
        let route = Value::Map(vec![
            ("source".into(), "lfo2".into()),
            ("destination".into(), "lfo1_slow".into()),
            ("amount".into(), 1.0.into()),
            ("polarity".into(), "unipolar".into()),
        ]);
        let slow_y = |slots: &[Value]| {
            let mut bank = LfoBank::compiled(&specs, RATE).with_weight_routes(crate::modulation::matrix::weight_routes(slots));
            let mut path = Vec::new();
            for _ in 0..(heard_seconds * RATE / MOST_FRAMES as f64) as usize {
                bank.advance(MOST_FRAMES, &[], &[[0.0; WEIGHTED_COUNT]; LFO_COUNT]);
                path.push(bank.snail_now[0][0][1]);
            }
            path
        };
        assert_ne!(slow_y(&[]), slow_y(&[route]));
    }
}
