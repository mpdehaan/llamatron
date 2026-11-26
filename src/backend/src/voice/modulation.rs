// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The LFOs and the mod matrix.
//!
//! An instrument has four LFOs, each a shape, a rate in hertz, whether a note starts its cycle again and whether each scene
//! does; their values over a chunk are worked out once before the voices read them. The matrix has six slots, each a
//! source, an optional via that scales it, a destination and an amount; the normalled routes live outside it (Env1 to the
//! amp, Env2 to the cutoff through the Env amount, Env3 to pitch through Pitch env, the key through Key track), so that its
//! slots stay free. Empty slots and those of no amount are left out when it is compiled.

use crate::dsp::Random;
use crate::protocol::values::{number, truth, word};
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
}

struct Lfo {
    shape: Shape,
    step: f64,
    /// The multiple of the note's frequency it runs at where it follows the key, as an FM modulator does.
    ratio: Option<f64>,
    retrigger: bool,
    each_scene: bool,
    cycles: f64,
}

/// An instrument's four LFOs, None for one that is off, and what each gave the chunk now playing.
pub struct LfoBank {
    lfos: Vec<Option<Lfo>>,
    held: Vec<f64>,
    pub now: Vec<Vec<f64>>,
}

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
                    _ => Shape::Sine,
                };
                Some(Lfo {
                    shape,
                    step: number(spec, "rate", 1.0) / rate,
                    ratio: crate::protocol::values::field(spec, "key_ratio").and_then(crate::protocol::values::as_number),
                    retrigger: truth(spec, "retrigger", false),
                    each_scene: truth(spec, "each_scene", false),
                    cycles: 0.0,
                })
            })
            .collect();
        LfoBank {
            lfos,
            held,
            now: (0..LFO_COUNT).map(|_| vec![0.0; MOST_FRAMES]).collect(),
        }
    }

    pub fn is_on(&self) -> bool {
        self.lfos.iter().any(Option::is_some)
    }

    /// Work out what the LFOs give the chunk ahead.
    pub fn advance(&mut self, frames: usize) {
        let frames = frames.min(MOST_FRAMES);
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
            if lfo.retrigger {
                lfo.cycles = 0.0;
            }
        }
    }

    /// Start again every LFO that restarts each scene.
    pub fn scene_started(&mut self) {
        for lfo in self.lfos.iter_mut().flatten() {
            if lfo.each_scene {
                lfo.cycles = 0.0;
            }
        }
    }
}

/// A shape's value at a place in its cycles, its steps of step cycles a sample. The saws' and the square's jumps are
/// smoothed by a two-sample polyBLEP, so that at audio rate they do not alias; at an LFO's slow rates the smoothing spans
/// a vanishing share of a cycle and changes nothing heard.
// The polyBLEP residual after stmlib's ThisBlepSample and NextBlepSample (stmlib/dsp/polyblep.h, Emilie Gillet, MIT),
// in its two-sided polynomial form; the implementation here is our own.
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
    }
}

/// The polyBLEP's correction near a jump of two at the cycle's start, at a place in the cycle and a step a sample.
#[inline]
fn blep(place: f64, step: f64) -> f64 {
    if step <= 0.0 || step >= 0.5 {
        return 0.0;
    }
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
    /// A MIDI CC, by its place among the CCs the matrix reads, its number kept in the matrix's list of them.
    Control(usize),
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
            routes.push(Route {
                source,
                via,
                destination,
                reach: amount * range,
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
            let mut value = sources.read(route.source) * route.reach;
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
