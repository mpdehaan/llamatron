// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Mod Matrix: six slots, each a source, an optional via that scales it, a destination and an amount. The normalled
//! routes live outside it (Env1 to the amp, Env2 to the cutoff through the Env amount, the key through Key track), so
//! that its slots stay free. Empty slots and those of no amount are left out when it is compiled.

use crate::modulation::lfos::LFO_COUNT;
use crate::modulation::snail::{OUTPUT_COUNT, WEIGHTED_COUNT};
use crate::oscillators::OWN_OSCILLATORS;
use crate::protocol::values::{number, word};
use crate::registry::{self, Named};
use rmpv::Value;

/// What a matrix slot reads.
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Source {
    Env1,
    Env2,
    Env3,
    Lfo(usize),
    /// One of a Snail's nine outputs, by its slot's place and the output's.
    Snail(usize, usize),
    Velocity,
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
        matches!(self, Source::Lfo(_) | Source::Snail(..) | Source::Random | Source::Oscillator | Source::Osc(_))
    }
}

/// What a matrix slot moves.
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Destination {
    Pitch,
    PulseWidth,
    /// Every oscillator's Detune, in cents.
    Detune,
    /// Every oscillator's Fine, in cents: the tuning moved by tenths of a cent.
    Fine,
    /// The SID's Interval: how far its second oscillator stands from the note, in semitones.
    Interval,
    /// A Snail's weighting of a circuit, by the Snail's place and the circuit's, moved through the newest note.
    Weight(usize, usize),
    /// One of Asheville's oscillators alone, by its place: its pitch, its pulse width, its Detune and its Fine.
    OscPitch(usize),
    OscWidth(usize),
    OscDetune(usize),
    OscFine(usize),
    Cutoff,
    Resonance,
    Amp,
}

/// How many octaves an LFO's rate moves at a route's full amount, up or down.
const RATE_OCTAVES: f64 = 2.0;
/// The destinations that move an LFO's rate, by the LFO's place.
pub const RATE_DESTINATIONS: [&str; LFO_COUNT] = ["lfo1_rate", "lfo2_rate", "lfo3_rate", "lfo4_rate"];
/// The LFO sources, by their places.
const LFO_SOURCES: [&str; LFO_COUNT] = ["lfo1", "lfo2", "lfo3", "lfo4"];
/// The destinations that move a Snail's weightings, Slow's and Slower's, by the Snail's place.
pub const WEIGHT_DESTINATIONS: [[&str; WEIGHTED_COUNT]; LFO_COUNT] = [
    ["lfo1_slow", "lfo1_slower"],
    ["lfo2_slow", "lfo2_slower"],
    ["lfo3_slow", "lfo3_slower"],
    ["lfo4_slow", "lfo4_slower"],
];

/// A source of the whole instrument rather than of a note, which the modulators read themselves: an LFO by its place,
/// one of a Snail's outputs by its slot's place and the output's, or a MIDI CC by its number.
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum BankSource {
    Lfo(usize),
    Snail(usize, usize),
    Control(u8),
}

/// A bank source by its name, or None for a source of a note, such as an envelope.
fn bank_source(name: &str) -> Option<BankSource> {
    if let Some(number) = control_named(name) {
        return Some(BankSource::Control(number));
    }
    match source_named(name)? {
        Source::Lfo(place) => Some(BankSource::Lfo(place)),
        Source::Snail(slot, output) => Some(BankSource::Snail(slot, output)),
        _ => None,
    }
}

/// A Mod Matrix route that moves a Snail's weighting: what it reads, what scales it or None, the Snail and the circuit
/// it weights, and how far it moves the weighting at its source's full value.
#[derive(Clone, Copy)]
pub struct WeightRoute {
    pub(crate) source: BankSource,
    pub(crate) via: Option<BankSource>,
    pub(crate) slot: usize,
    pub(crate) circuit: usize,
    pub(crate) reach: f64,
    pub(crate) offset: f64,
}

/// Where a slot's destination is a Snail's weighting, the Snail's place and the circuit's.
fn weight_destination(slot: &Value) -> Option<(usize, usize)> {
    let destination = word(slot, "destination", "none");
    WEIGHT_DESTINATIONS
        .iter()
        .enumerate()
        .find_map(|(place, names)| names.iter().position(|name| *name == destination).map(|circuit| (place, circuit)))
}

/// Whether a slot reads only the whole instrument's sources, as its source and its via, so that the bank moves its
/// destination itself rather than through a note.
fn reads_only_bank_sources(slot: &Value) -> bool {
    let via = word(slot, "via", "none");
    bank_source(word(slot, "source", "none")).is_some() && (via == "none" || bank_source(via).is_some())
}

/// The matrix's routes that move a Snail's weighting from the whole instrument's sources; one reading a note's source
/// moves it through the newest note instead (ModMatrix, Destination::Weight).
pub fn weight_routes(slots: &[Value]) -> Vec<WeightRoute> {
    let mut routes = Vec::new();
    for slot in slots {
        let amount = number(slot, "amount", 0.0);
        let Some((place, circuit)) = weight_destination(slot) else { continue };
        if !reads_only_bank_sources(slot) {
            continue;
        }
        let Some(source) = bank_source(word(slot, "source", "none")) else { continue };
        let via = match word(slot, "via", "none") {
            "none" => None,
            name => match bank_source(name) {
                Some(via) => Some(via),
                None => continue,
            },
        };
        if amount == 0.0 {
            continue;
        }
        let unipolar = word(slot, "polarity", "bipolar") == "unipolar";
        let (reach, offset) = if unipolar { (amount / 2.0, amount / 2.0) } else { (amount, 0.0) };
        routes.push(WeightRoute {
            source,
            via,
            slot: place,
            circuit,
            reach,
            offset,
        });
    }
    routes
}

/// A Mod Matrix route that moves an LFO's rate: the LFO it reads, an LFO scaling it or None, the LFO it moves, and how
/// many octaves it moves at its source's full value. Only an LFO moves a rate, since the LFOs are the instrument's, not a
/// note's.
#[derive(Clone, Copy)]
pub struct RateRoute {
    pub(crate) source: usize,
    pub(crate) via: Option<usize>,
    pub(crate) target: usize,
    pub(crate) reach: f64,
    pub(crate) offset: f64,
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

/// Every Mod Matrix source a spec may name, besides a CC by its number: what each is.
pub static SOURCES: &[Named<Source>] = &[
    Named {
        name: "env1",
        value: Source::Env1,
    },
    Named {
        name: "env2",
        value: Source::Env2,
    },
    Named {
        name: "env3",
        value: Source::Env3,
    },
    Named {
        name: "lfo1",
        value: Source::Lfo(0),
    },
    Named {
        name: "lfo2",
        value: Source::Lfo(1),
    },
    Named {
        name: "lfo3",
        value: Source::Lfo(2),
    },
    Named {
        name: "lfo4",
        value: Source::Lfo(3),
    },
    Named {
        name: "lfo1_slow_x",
        value: Source::Snail(0, 0),
    },
    Named {
        name: "lfo1_slow_y",
        value: Source::Snail(0, 1),
    },
    Named {
        name: "lfo1_slow_z",
        value: Source::Snail(0, 2),
    },
    Named {
        name: "lfo1_slower_x",
        value: Source::Snail(0, 3),
    },
    Named {
        name: "lfo1_slower_y",
        value: Source::Snail(0, 4),
    },
    Named {
        name: "lfo1_slower_z",
        value: Source::Snail(0, 5),
    },
    Named {
        name: "lfo1_slowest_x",
        value: Source::Snail(0, 6),
    },
    Named {
        name: "lfo1_slowest_y",
        value: Source::Snail(0, 7),
    },
    Named {
        name: "lfo1_slowest_z",
        value: Source::Snail(0, 8),
    },
    Named {
        name: "lfo2_slow_x",
        value: Source::Snail(1, 0),
    },
    Named {
        name: "lfo2_slow_y",
        value: Source::Snail(1, 1),
    },
    Named {
        name: "lfo2_slow_z",
        value: Source::Snail(1, 2),
    },
    Named {
        name: "lfo2_slower_x",
        value: Source::Snail(1, 3),
    },
    Named {
        name: "lfo2_slower_y",
        value: Source::Snail(1, 4),
    },
    Named {
        name: "lfo2_slower_z",
        value: Source::Snail(1, 5),
    },
    Named {
        name: "lfo2_slowest_x",
        value: Source::Snail(1, 6),
    },
    Named {
        name: "lfo2_slowest_y",
        value: Source::Snail(1, 7),
    },
    Named {
        name: "lfo2_slowest_z",
        value: Source::Snail(1, 8),
    },
    Named {
        name: "lfo3_slow_x",
        value: Source::Snail(2, 0),
    },
    Named {
        name: "lfo3_slow_y",
        value: Source::Snail(2, 1),
    },
    Named {
        name: "lfo3_slow_z",
        value: Source::Snail(2, 2),
    },
    Named {
        name: "lfo3_slower_x",
        value: Source::Snail(2, 3),
    },
    Named {
        name: "lfo3_slower_y",
        value: Source::Snail(2, 4),
    },
    Named {
        name: "lfo3_slower_z",
        value: Source::Snail(2, 5),
    },
    Named {
        name: "lfo3_slowest_x",
        value: Source::Snail(2, 6),
    },
    Named {
        name: "lfo3_slowest_y",
        value: Source::Snail(2, 7),
    },
    Named {
        name: "lfo3_slowest_z",
        value: Source::Snail(2, 8),
    },
    Named {
        name: "lfo4_slow_x",
        value: Source::Snail(3, 0),
    },
    Named {
        name: "lfo4_slow_y",
        value: Source::Snail(3, 1),
    },
    Named {
        name: "lfo4_slow_z",
        value: Source::Snail(3, 2),
    },
    Named {
        name: "lfo4_slower_x",
        value: Source::Snail(3, 3),
    },
    Named {
        name: "lfo4_slower_y",
        value: Source::Snail(3, 4),
    },
    Named {
        name: "lfo4_slower_z",
        value: Source::Snail(3, 5),
    },
    Named {
        name: "lfo4_slowest_x",
        value: Source::Snail(3, 6),
    },
    Named {
        name: "lfo4_slowest_y",
        value: Source::Snail(3, 7),
    },
    Named {
        name: "lfo4_slowest_z",
        value: Source::Snail(3, 8),
    },
    Named {
        name: "velocity",
        value: Source::Velocity,
    },
    Named {
        name: "random",
        value: Source::Random,
    },
    Named {
        name: "osc",
        value: Source::Oscillator,
    },
    Named {
        name: "osc1",
        value: Source::Osc(0),
    },
    Named {
        name: "osc2",
        value: Source::Osc(1),
    },
    Named {
        name: "osc3",
        value: Source::Osc(2),
    },
];

/// How far Detune and Fine move every oscillator's tuning at their source's full value, in cents: a semitone, and a
/// tenth of one.
const DETUNE_REACH_CENTS: f64 = 100.0;
const FINE_REACH_CENTS: f64 = 10.0;

/// Every Mod Matrix destination a spec may name, besides an LFO's rate: what each is, and how far it moves at its
/// source's full value.
pub static DESTINATIONS: &[Named<(Destination, f64)>] = &[
    Named {
        name: "pitch",
        value: (Destination::Pitch, 24.0),
    },
    Named {
        name: "pulse_width",
        value: (Destination::PulseWidth, 0.4),
    },
    Named {
        name: "detune",
        value: (Destination::Detune, DETUNE_REACH_CENTS),
    },
    Named {
        name: "fine",
        value: (Destination::Fine, FINE_REACH_CENTS),
    },
    Named {
        name: "interval",
        value: (Destination::Interval, 24.0),
    },
    Named {
        name: "osc1_pitch",
        value: (Destination::OscPitch(0), 24.0),
    },
    Named {
        name: "osc1_pulse_width",
        value: (Destination::OscWidth(0), 0.4),
    },
    Named {
        name: "osc1_detune",
        value: (Destination::OscDetune(0), DETUNE_REACH_CENTS),
    },
    Named {
        name: "osc1_fine",
        value: (Destination::OscFine(0), FINE_REACH_CENTS),
    },
    Named {
        name: "osc2_pitch",
        value: (Destination::OscPitch(1), 24.0),
    },
    Named {
        name: "osc2_pulse_width",
        value: (Destination::OscWidth(1), 0.4),
    },
    Named {
        name: "osc2_detune",
        value: (Destination::OscDetune(1), DETUNE_REACH_CENTS),
    },
    Named {
        name: "osc2_fine",
        value: (Destination::OscFine(1), FINE_REACH_CENTS),
    },
    Named {
        name: "osc3_pitch",
        value: (Destination::OscPitch(2), 24.0),
    },
    Named {
        name: "osc3_pulse_width",
        value: (Destination::OscWidth(2), 0.4),
    },
    Named {
        name: "osc3_detune",
        value: (Destination::OscDetune(2), DETUNE_REACH_CENTS),
    },
    Named {
        name: "osc3_fine",
        value: (Destination::OscFine(2), FINE_REACH_CENTS),
    },
    Named {
        name: "cutoff",
        value: (Destination::Cutoff, 6.0),
    },
    Named {
        name: "resonance",
        value: (Destination::Resonance, 1.0),
    },
    Named {
        name: "amp",
        value: (Destination::Amp, 1.0),
    },
];

/// A source by name, from its registry.
fn source_named(name: &str) -> Option<Source> {
    registry::named(SOURCES, name)
}

/// A destination by name, and how far it moves at its source's full value, from its registry.
fn destination_named(name: &str) -> Option<(Destination, f64)> {
    registry::named(DESTINATIONS, name)
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
    /// Each Snail's outputs, by its slot, those the matrix reads.
    pub snails: [[f64; OUTPUT_COUNT]; LFO_COUNT],
    pub velocity: f64,
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
            Source::Snail(slot, output) => self.snails[slot][output],
            Source::Velocity => self.velocity,
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
    pub fine: f64,
    pub interval: f64,
    /// What each of Asheville's oscillators alone is moved by: its pitch in semitones, its Detune and Fine in cents,
    /// and its pulse width.
    pub osc_pitch: [f64; OWN_OSCILLATORS],
    pub osc_cents: [f64; OWN_OSCILLATORS],
    pub osc_width: [f64; OWN_OSCILLATORS],
    /// What each Snail's weightings are moved by, Slow's and Slower's.
    pub weights: [[f64; WEIGHTED_COUNT]; LFO_COUNT],
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
            // A Snail's weighting read from a note's source is moved by the newest note; from the instrument's own
            // sources, by the bank (weight_routes).
            let weighting = weight_destination(slot).filter(|_| !reads_only_bank_sources(slot));
            let Some((destination, range)) = weighting
                .map(|(place, circuit)| (Destination::Weight(place, circuit), 1.0))
                .or_else(|| destination_named(word(slot, "destination", "none")))
            else {
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

    /// Whether any route moves a Snail's weighting through a note.
    pub fn moves_weights(&self) -> bool {
        self.routes.iter().any(|route| matches!(route.destination, Destination::Weight(..)))
    }

    /// Whether any route reads a source, so that a voice works out only what is read.
    pub fn uses(&self, source: Source) -> bool {
        self.routes.iter().any(|route| route.source == source || route.via == Some(source))
    }

    /// Every Snail output a route reads, by its slot and its place, each once, so that a voice copies only those.
    pub fn snail_outputs_read(&self) -> Vec<(usize, usize)> {
        let mut read = Vec::new();
        for route in &self.routes {
            for source in [Some(route.source), route.via].into_iter().flatten() {
                if let Source::Snail(slot, output) = source {
                    if !read.contains(&(slot, output)) {
                        read.push((slot, output));
                    }
                }
            }
        }
        read
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
                Destination::Fine => moved.fine += value,
                Destination::Interval => moved.interval += value,
                Destination::Weight(slot, circuit) => moved.weights[slot][circuit] += value,
                Destination::OscPitch(place) => moved.osc_pitch[place] += value,
                Destination::OscWidth(place) => moved.osc_width[place] += value,
                Destination::OscDetune(place) | Destination::OscFine(place) => moved.osc_cents[place] += value,
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
}
