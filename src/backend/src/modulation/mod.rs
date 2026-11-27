// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The LFOs and the mod matrix.
//!
//! An instrument has four LFOs, each a shape, a rate in hertz, whether a note starts its cycle again and whether each scene
//! does; their values over a chunk are worked out once before the voices read them. An LFO+ may also fade in after each
//! note, which each voice applies by its own age, and may follow the song's tempo, its cycle a division of the beat. The matrix has six slots, each a
//! source, an optional via that scales it, a destination and an amount; the normalled routes live outside it (Env1 to the
//! amp, Env2 to the cutoff through the Env amount, Env3 to pitch through Pitch env, the key through Key track), so that its
//! slots stay free. Empty slots and those of no amount are left out when it is compiled. A slot may also move an LFO's
//! rate by an LFO, another or itself: those routes are the bank's, read a sample at a time as the LFOs advance.

use crate::dsp::blep::blep;
use crate::dsp::Random;
use crate::protocol::values::{number, word};
use rmpv::Value;
use std::f64::consts::PI;

pub const LFO_COUNT: usize = 4;
pub const MOST_FRAMES: usize = 8192;
const HELD_VALUES: usize = 4096;
const HELD_SEED: u64 = 224;

#[derive(Clone, Copy, PartialEq, Eq)]
enum Shape {
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

/// An instrument's four LFOs, None for one that is off, and what each gave the chunk now playing.
pub struct LfoBank {
    lfos: Vec<Option<Lfo>>,
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

/// The tempo a song is taken to play at until it says, in quarter notes a minute.
const FIRST_TEMPO: f64 = 120.0;
const SECONDS_PER_MINUTE: f64 = 60.0;

impl LfoBank {
    pub fn compiled(specs: &[Value], rate: f64) -> LfoBank {
        let mut random = Random::new(HELD_SEED);
        let held = (0..HELD_VALUES).map(|_| random.between(-1.0, 1.0)).collect();
        let lfos = (0..LFO_COUNT)
            .map(|place| {
                let spec = specs.get(place)?;
                if spec.is_nil() {
                    return None;
                }
                let shape = match word(spec, "shape", "sine") {
                    "triangle" => Shape::Triangle,
                    "saw_up" => Shape::SawUp,
                    "saw_down" => Shape::SawDown,
                    "square" => Shape::Square,
                    "sample_and_hold" => Shape::SampleAndHold,
                    "smooth_random" => Shape::SmoothRandom,
                    _ => Shape::Sine,
                };
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
        LfoBank {
            lfos,
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
    /// already plays it, nothing restarts.
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
        !self.stopped && self.lfos.iter().any(Option::is_some)
    }

    /// The bank with the Mod Matrix's routes that move its LFOs' rates.
    pub fn with_rate_routes(mut self, routes: Vec<RateRoute>) -> LfoBank {
        self.rate_routes = routes;
        self
    }

    /// Work out what the LFOs give the chunk ahead.
    pub fn advance(&mut self, frames: usize) {
        let frames = frames.min(MOST_FRAMES);
        if !self.rate_routes.is_empty() {
            self.advance_moving_rates(frames);
            return;
        }
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

/// What a matrix slot reads.
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Source {
    Env1,
    Env2,
    Env3,
    Lfo(usize),
    Velocity,
    Key,
    Random,
    /// The voice's own oscillator, as it sounded a sample before: an audio-rate source, for FM and AM from the voice itself.
    Oscillator,
    /// One of Asheville's oscillators by its place, sounding or not, from -1 to 1: an LFO at a low Range, or an
    /// audio-rate modulator of another.
    Osc(usize),
    /// A MIDI CC, by its place among the CCs the matrix reads, its number kept in the matrix's list of them.
    Control(usize),
}

impl Source {
    /// Whether the source swings from -1 to 1, as an LFO does, rather than rising from 0 to 1, as an envelope does.
    pub fn is_bipolar(self) -> bool {
        matches!(self, Source::Lfo(_) | Source::Key | Source::Random | Source::Oscillator | Source::Osc(_))
    }
}

/// What a matrix slot moves.
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Destination {
    Pitch,
    PulseWidth,
    Detune,
    Cutoff,
    Resonance,
    Amp,
}

/// How many octaves an LFO's rate moves at a route's full amount, up or down.
const RATE_OCTAVES: f64 = 2.0;
/// The destinations that move an LFO's rate, by the LFO's place.
const RATE_DESTINATIONS: [&str; LFO_COUNT] = ["lfo1_rate", "lfo2_rate", "lfo3_rate", "lfo4_rate"];
/// The LFO sources, by their places.
const LFO_SOURCES: [&str; LFO_COUNT] = ["lfo1", "lfo2", "lfo3", "lfo4"];

/// A Mod Matrix route that moves an LFO's rate: the LFO it reads, an LFO scaling it or None, the LFO it moves, and how
/// many octaves it moves at its source's full value. Only an LFO moves a rate, since the LFOs are the instrument's, not a
/// note's.
#[derive(Clone, Copy)]
pub struct RateRoute {
    source: usize,
    via: Option<usize>,
    target: usize,
    reach: f64,
    offset: f64,
}

/// The matrix's routes that move an LFO's rate, from its slots; a route whose source or via is not an LFO moves none.
pub fn rate_routes(slots: &[Value]) -> Vec<RateRoute> {
    let lfo_place = |name: &str| LFO_SOURCES.iter().position(|each| *each == name);
    let mut routes = Vec::new();
    for slot in slots {
        let amount = number(slot, "amount", 0.0);
        let Some(target) = RATE_DESTINATIONS.iter().position(|each| *each == word(slot, "destination", "none")) else {
            continue;
        };
        let Some(source) = lfo_place(word(slot, "source", "none")) else { continue };
        let via = match word(slot, "via", "none") {
            "none" => None,
            name => match lfo_place(name) {
                Some(place) => Some(place),
                None => continue,
            },
        };
        if amount == 0.0 {
            continue;
        }
        // A Unipolar route moves the rate from its own to the amount's octaves, never below, as a matrix route does.
        let reach = amount * RATE_OCTAVES;
        let unipolar = word(slot, "polarity", "bipolar") == "unipolar";
        let (reach, offset) = if unipolar { (reach / 2.0, reach / 2.0) } else { (reach, 0.0) };
        routes.push(RateRoute {
            source,
            via,
            target,
            reach,
            offset,
        });
    }
    routes
}

/// What a CC source is called in a sound: `cc` and its number, such as `cc74`.
const CONTROL_PREFIX: &str = "cc";
/// The highest CC number.
const HIGHEST_CONTROL: u8 = 127;
/// The most CCs the matrix reads, one a slot at most.
pub const MOST_CONTROLS: usize = 8;

/// The CC number a source names, such as 74 for `cc74`, or None for any other source.
fn control_named(name: &str) -> Option<u8> {
    name.strip_prefix(CONTROL_PREFIX)?
        .parse::<u8>()
        .ok()
        .filter(|number| *number <= HIGHEST_CONTROL)
}

fn source_named(name: &str) -> Option<Source> {
    Some(match name {
        "env1" => Source::Env1,
        "env2" => Source::Env2,
        "env3" => Source::Env3,
        "lfo1" => Source::Lfo(0),
        "lfo2" => Source::Lfo(1),
        "lfo3" => Source::Lfo(2),
        "lfo4" => Source::Lfo(3),
        "velocity" => Source::Velocity,
        "key" => Source::Key,
        "random" => Source::Random,
        "osc" => Source::Oscillator,
        "osc1" => Source::Osc(0),
        "osc2" => Source::Osc(1),
        "osc3" => Source::Osc(2),
        _ => return None,
    })
}

/// A destination by name, and how far it moves at its source's full value.
fn destination_named(name: &str) -> Option<(Destination, f64)> {
    Some(match name {
        "pitch" => (Destination::Pitch, 24.0),
        "pulse_width" => (Destination::PulseWidth, 0.4),
        "detune" => (Destination::Detune, 1.0),
        "cutoff" => (Destination::Cutoff, 6.0),
        "resonance" => (Destination::Resonance, 1.0),
        "amp" => (Destination::Amp, 1.0),
        _ => return None,
    })
}

/// One route of the matrix: its source, its via or None, its destination and how far it moves.
#[derive(Clone, Copy)]
pub struct Route {
    pub source: Source,
    pub via: Option<Source>,
    pub destination: Destination,
    pub reach: f64,
    /// What a Unipolar route adds to its source times its reach, moving a source of -1 to 1 into 0 to 1; 0 for a
    /// Bipolar route or a source that is 0 to 1 already.
    pub offset: f64,
}

/// What the matrix's sources hold at one sample.
#[derive(Clone, Copy, Default)]
pub struct Sources {
    pub envelopes: [f64; 3],
    pub lfos: [f64; LFO_COUNT],
    pub velocity: f64,
    pub key: f64,
    pub random: f64,
    /// The voice's oscillator a sample before, from -1 to 1.
    pub oscillator: f64,
    /// Asheville's three oscillators a sample before.
    pub oscs: [f64; 3],
    /// The value of each CC the matrix reads, from 0 to 1, in the order of the matrix's list of them.
    pub controls: [f64; MOST_CONTROLS],
}

impl Sources {
    #[inline]
    fn read(&self, source: Source) -> f64 {
        match source {
            Source::Env1 => self.envelopes[0],
            Source::Env2 => self.envelopes[1],
            Source::Env3 => self.envelopes[2],
            Source::Lfo(place) => self.lfos[place],
            Source::Velocity => self.velocity,
            Source::Key => self.key,
            Source::Random => self.random,
            Source::Oscillator => self.oscillator,
            Source::Osc(place) => self.oscs[place],
            Source::Control(place) => self.controls[place],
        }
    }
}

/// What the matrix moves at one sample, each destination's sum.
#[derive(Clone, Copy, Default)]
pub struct Moved {
    pub pitch: f64,
    pub pulse_width: f64,
    pub detune: f64,
    pub cutoff: f64,
    pub resonance: f64,
    pub amp: f64,
}

/// The matrix's routes, and the CC numbers its routes read, each once, in the order Source::Control counts them.
pub struct ModMatrix {
    pub routes: Vec<Route>,
    pub controls: Vec<u8>,
}

impl ModMatrix {
    pub fn compiled(slots: &[Value]) -> ModMatrix {
        let mut routes = Vec::new();
        let mut controls: Vec<u8> = Vec::new();
        // A CC source takes the place of its number among the CCs read, added the first time a route reads it.
        let mut named = |name: &str| -> Option<Source> {
            let Some(number) = control_named(name) else { return source_named(name) };
            let place = match controls.iter().position(|each| *each == number) {
                Some(place) => place,
                None if controls.len() < MOST_CONTROLS => {
                    controls.push(number);
                    controls.len() - 1
                }
                None => return None,
            };
            Some(Source::Control(place))
        };
        for slot in slots {
            let amount = number(slot, "amount", 0.0);
            if amount == 0.0 {
                continue;
            }
            let Some(source) = named(word(slot, "source", "none")) else { continue };
            let Some((destination, range)) = destination_named(word(slot, "destination", "none")) else {
                continue;
            };
            let via = named(word(slot, "via", "none"));
            // A Unipolar route moves its destination from 0 to the amount: a source of -1 to 1 is halved and lifted.
            let unipolar = word(slot, "polarity", "bipolar") == "unipolar" && source.is_bipolar();
            let reach = amount * range;
            let (reach, offset) = if unipolar { (reach / 2.0, reach / 2.0) } else { (reach, 0.0) };
            routes.push(Route {
                source,
                via,
                destination,
                reach,
                offset,
            });
        }
        ModMatrix { routes, controls }
    }

    /// Whether any route reads a source, so that a voice works out only what is read.
    pub fn uses(&self, source: Source) -> bool {
        self.routes.iter().any(|route| route.source == source || route.via == Some(source))
    }

    #[inline]
    pub fn moved(&self, sources: &Sources) -> Moved {
        let mut moved = Moved::default();
        for route in &self.routes {
            let mut value = sources.read(route.source) * route.reach + route.offset;
            if let Some(via) = route.via {
                value *= sources.read(via);
            }
            match route.destination {
                Destination::Pitch => moved.pitch += value,
                Destination::PulseWidth => moved.pulse_width += value,
                Destination::Detune => moved.detune += value,
                Destination::Cutoff => moved.cutoff += value,
                Destination::Resonance => moved.resonance += value,
                Destination::Amp => moved.amp += value,
            }
        }
        moved
    }
}

#[cfg(test)]
mod tests {
    use super::*;

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
                bank.advance(frames);
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
            lfos.advance(MOST_FRAMES);
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
            lfos.advance(RATE as usize / 8);
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
        lfos.advance(MOST_FRAMES);
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

    /// A Unipolar route moves its destination from 0 to the amount, a Bipolar one from minus it to plus it: an LFO at its
    /// lowest moves a Unipolar route's pitch not at all.
    #[test]
    fn a_unipolar_route_moves_from_nothing_to_its_amount() {
        let route = |polarity: &str| {
            ModMatrix::compiled(&[Value::Map(vec![
                ("source".into(), "lfo1".into()),
                ("destination".into(), "pitch".into()),
                ("amount".into(), 50.0.into()),
                ("polarity".into(), polarity.into()),
            ])])
        };
        let mut sources = Sources::default();
        sources.lfos[0] = -1.0;
        assert!(route("unipolar").moved(&sources).pitch.abs() < 1e-12);
        assert!(route("bipolar").moved(&sources).pitch < 0.0);
        sources.lfos[0] = 1.0;
        assert!((route("unipolar").moved(&sources).pitch - route("bipolar").moved(&sources).pitch).abs() < 1e-12);
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
}
