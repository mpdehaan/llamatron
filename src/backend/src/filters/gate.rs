// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The low-pass gate: one photoresistor that sets both loudness and cutoff, lit by a lamp, so that a note closes and
//! darkens at once, as a struck or plucked thing fades. It stands in either of two places of a voice: the Filter's, where
//! the Amp still follows it, or the Amp's, where it is the note's last stage and always closes when the note ends.
//!
//! Every gate is the same module. Its Trigger chooses what lights it: a flash at each note (Trigger), the lamp held while
//! the key is (Gate), or an envelope's level (Env 1, and on the Filter tab Env 2 and Env 3). Its own cell, the vactrol of
//! the Envelopes tab with the same Response, Memory, Age and Stability, answers a flash or a held lamp; an envelope
//! plugged in is smoothed by the cell's rise and fall, as on the hardware, where the envelope only lights the lamp.
//! VCA is loudness alone; Lowpass the cutoff alone through a resonant two-pole, so that a falling cutoff rings a pitch that
//! drops as the gate closes; Both loudness and a one-pole's cutoff together, the classic pluck. The Signal is the sound
//! coming in, a Ping alone (a short pulse each note, rung through the gate), or both; key tracking moves the open cutoff
//! with the note, so that a pinged gate plays in tune.

use crate::dsp::{flushed, HIGHEST_SHARE};
use crate::envelopes::{self, EnvelopeMemory, EnvelopePart, EnvelopeState, NoteTime};
use crate::protocol::values::{number, word};
use rmpv::Value;
use std::f64::consts::{LN_10, PI};

/// The cell's light as conductance: how sharply it opens with the lamp's brightness, its resistance lit and dark, and the
/// divider it makes the loudness with.
const CELL_POWER: f64 = 1.4;
const LIT_OHMS: f64 = 5000.0;
const DARK_OHMS: f64 = 1.0e7;
const DIVIDER_OHMS: f64 = 10000.0;
/// The two-pole's least and most resonance, as Q.
const LEAST_GATE_Q: f64 = 0.5;
const MOST_GATE_Q: f64 = 25.0;
/// How loud a ping strikes the gate, at full velocity.
const PING_LEVEL: f64 = 0.45;
const MIDDLE_C: f64 = 60.0;
const LOWEST_CUTOFF: f64 = 20.0;
/// A light too faint to be heard through the gate, -80 dB, at which a gate lit by an envelope has closed.
const DARK_LIGHT: f64 = 1e-4;
/// The cutoff worked out once every few samples, as the filters' is.
const COEFFICIENT_STEP: usize = 4;
/// The gate's type in a spec, in either place.
pub const LOW_PASS_GATE: &str = "low_pass_gate";

/// How the gate shapes the sound: loudness, cutoff, or both.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum GateMode {
    Vca,
    Lowpass,
    Both,
}

/// What lights the gate: its own cell, struck or held, or an envelope's level by its place.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum GateTrigger {
    Cell,
    Envelope(usize),
}

/// What the gate reads of its note at one sample: how many samples into the note, its pitch and level, and the cutoff
/// moved in octaves.
#[derive(Clone, Copy)]
pub struct GateNote {
    pub place: f64,
    pub pitch: f64,
    pub level: f64,
    pub octaves: f64,
}

/// What one voice's gate keeps: its filter's stages and coefficient, its cell, and the light an envelope has lit it to.
#[derive(Clone, Copy, Default)]
pub struct GateState {
    stages: [f64; 2],
    g: f64,
    countdown: usize,
    cell: EnvelopeState,
    light: f64,
}

/// A low-pass gate as a patch compiles it.
pub struct GatePart {
    pub mode: GateMode,
    pub trigger: GateTrigger,
    damping: f64,
    open: f64,
    key_track: f64,
    pub feeds_oscillator: bool,
    feeds_ping: bool,
    ping_samples: f64,
    rate: f64,
    /// The gate's own vactrol, answering a flash or a held lamp.
    cell: EnvelopePart,
    /// How far a sample moves the light toward a brighter or a dimmer envelope: the cell's rise and its fall.
    rise_share: f64,
    fall_share: f64,
}

impl GatePart {
    /// A gate from its spec, or None for a spec of another type.
    pub fn compiled(spec: &Value, rate: f64) -> Option<GatePart> {
        if word(spec, "type", "none") != LOW_PASS_GATE {
            return None;
        }
        let mode = match word(spec, "mode", "both") {
            "vca" => GateMode::Vca,
            "lowpass" => GateMode::Lowpass,
            _ => GateMode::Both,
        };
        let trigger_word = word(spec, "trigger", "trigger");
        let trigger = match trigger_word {
            "env1" => GateTrigger::Envelope(0),
            "env2" => GateTrigger::Envelope(1),
            "env3" => GateTrigger::Envelope(2),
            _ => GateTrigger::Cell,
        };
        let signal = word(spec, "signal", "oscillator");
        let resonance = number(spec, "resonance", 0.0).clamp(0.0, 1.0);
        let response = number(spec, "response", envelopes::SLOW_RESPONSE);
        let age = number(spec, "age", 0.0);
        let (rise, fall) = envelopes::vactrol::cell_times(response, age);
        Some(GatePart {
            mode,
            trigger,
            damping: 1.0 / (LEAST_GATE_Q + resonance * (MOST_GATE_Q - LEAST_GATE_Q)),
            open: number(spec, "open", 8000.0),
            key_track: number(spec, "key_track", 0.0),
            feeds_oscillator: signal != "ping",
            feeds_ping: signal != "oscillator",
            ping_samples: number(spec, "ping_time", 0.001) * rate,
            rate,
            cell: envelopes::compiled(&cell_spec(spec, trigger_word == "gate"), 0.0),
            rise_share: 1.0 - (-1.0 / (rise * rate)).exp(),
            fall_share: 1.0 - (-LN_10 / (fall * rate)).exp(),
        })
    }

    /// Whether an envelope, by its place, lights this gate, so that the voice works it out.
    pub fn reads_envelope(&self, place: usize) -> bool {
        self.trigger == GateTrigger::Envelope(place)
    }

    /// Start a note on the gate: its cell struck from what the instrument's gate remembers, its filter left as it was.
    pub fn start(&self, state: &mut GateState, memory: &mut EnvelopeMemory, velocity: f64, seconds: f64) {
        if self.trigger == GateTrigger::Cell {
            let (cell, ..) = self.cell.start(memory, velocity, seconds);
            state.cell = cell;
        }
        state.light = 0.0;
    }

    /// The gate's light at a time into its note: its cell's, or the lighting envelope's level smoothed by the cell, the
    /// envelopes' levels given with velocity.
    #[inline]
    pub fn light(&self, state: &mut GateState, note: NoteTime, envelopes: &[f64; 3]) -> f64 {
        match self.trigger {
            GateTrigger::Cell => self.cell.level(&mut state.cell, note, None),
            GateTrigger::Envelope(place) => {
                let target = envelopes[place];
                let share = if target > state.light { self.rise_share } else { self.fall_share };
                state.light += (target - state.light) * share;
                state.light
            }
        }
    }

    /// Whether the gate has closed for good: its own cell gone dark, or its envelope done and its light faded after it.
    pub fn is_done(&self, state: &GateState, envelope_done: bool) -> bool {
        match self.trigger {
            GateTrigger::Cell => state.cell.done,
            GateTrigger::Envelope(_) => envelope_done && state.light < DARK_LIGHT,
        }
    }

    /// One sample through the gate: the sound coming in, the light from 0 to about 1, and the note.
    #[inline]
    pub fn process(&self, state: &mut GateState, input: f64, light: f64, note: GateNote) -> f64 {
        let mut source = if self.feeds_oscillator { input } else { 0.0 };
        if self.feeds_ping && note.place >= 0.0 && note.place < self.ping_samples {
            source += PING_LEVEL * note.level;
        }
        let conductance = light.max(0.0).powf(CELL_POWER) / LIT_OHMS + 1.0 / DARK_OHMS;
        if self.mode == GateMode::Vca {
            return source * gain(conductance);
        }
        if state.countdown == 0 {
            let opened = self.open * 2f64.powf(self.key_track * (note.pitch - MIDDLE_C) / 12.0);
            let cutoff = (opened * conductance * LIT_OHMS * 2f64.powf(note.octaves)).clamp(LOWEST_CUTOFF, HIGHEST_SHARE * self.rate);
            state.g = (PI * cutoff / self.rate).tan();
            state.countdown = COEFFICIENT_STEP;
        }
        state.countdown -= 1;
        let g = state.g;
        let out = if self.mode == GateMode::Both {
            let share = g / (1.0 + g);
            let moved = (source - state.stages[0]) * share;
            let out = moved + state.stages[0];
            state.stages[0] = out + moved;
            out * gain(conductance)
        } else {
            let [first, second] = state.stages;
            let high = (source - (self.damping + g) * first - second) / (1.0 + self.damping * g + g * g);
            let band = g * high + first;
            let low = g * band + second;
            state.stages[0] = g * high + band;
            state.stages[1] = g * band + low;
            low
        };
        for stage in state.stages.iter_mut() {
            *stage = flushed(*stage);
        }
        out
    }
}

/// The gate's own cell as the Envelopes tab's vactrol would be: struck by a flash as long as its Trigger time, or held.
fn cell_spec(spec: &Value, held: bool) -> Value {
    let drive = if held { "gate" } else { "strike" };
    Value::Map(vec![
        ("type".into(), "vactrol".into()),
        ("drive".into(), drive.into()),
        ("strike_width".into(), number(spec, "trigger_time", 0.002).into()),
        ("response".into(), number(spec, "response", envelopes::SLOW_RESPONSE).into()),
        ("memory".into(), number(spec, "memory", 0.3).into()),
        ("age".into(), number(spec, "age", 0.0).into()),
        ("stability".into(), number(spec, "stability", 1.0).into()),
    ])
}

/// The loudness a conductance gives through the divider, 1 at full light.
fn gain(conductance: f64) -> f64 {
    let full = DIVIDER_OHMS / (DIVIDER_OHMS + 2.0 * LIT_OHMS);
    DIVIDER_OHMS / (DIVIDER_OHMS + 2.0 / conductance) / full
}

#[cfg(test)]
mod tests {
    use super::*;

    const RATE: f64 = 48_000.0;

    fn gate(pairs: &[(&str, Value)]) -> GatePart {
        let mut all = vec![("type".into(), LOW_PASS_GATE.into())];
        all.extend(pairs.iter().map(|(key, value)| (Value::from(*key), value.clone())));
        GatePart::compiled(&Value::Map(all), RATE).expect("a low-pass gate")
    }

    /// A gate on its own Trigger flashes its cell at the note, opens, then closes for good by itself, with no envelope.
    #[test]
    fn a_gate_on_its_own_trigger_opens_then_closes() {
        let struck = gate(&[("trigger", "trigger".into()), ("mode", "vca".into())]);
        let (mut state, mut memory) = (GateState::default(), EnvelopeMemory::default());
        struck.start(&mut state, &mut memory, 1.0, 0.0);
        let no_envelopes = [0.0; 3];
        let mut loudest: f64 = 0.0;
        // A slow cell's hyperbolic fall takes several seconds to go fully dark.
        let seconds = 12.0;
        for sample in 0..(seconds * RATE) as usize {
            let note = NoteTime {
                age: sample as f64 / RATE,
                released: None,
            };
            loudest = loudest.max(struck.light(&mut state, note, &no_envelopes));
        }
        assert!(loudest > 0.5, "{loudest}");
        assert!(struck.is_done(&state, false), "closed by itself");
    }

    /// A gate lit by an envelope follows it smoothed by its cell: it lags a sudden rise, and closes only once the envelope
    /// is done and its light has faded after it.
    #[test]
    fn a_gate_lit_by_an_envelope_follows_it_smoothed() {
        let lit = gate(&[("trigger", "env1".into()), ("response", 1.0.into())]);
        let mut state = GateState::default();
        let note = NoteTime { age: 0.0, released: None };
        let full = [1.0, 0.0, 0.0];
        let first = lit.light(&mut state, note, &full);
        assert!(first > 0.0 && first < 0.1, "{first}");
        for _ in 0..RATE as usize {
            lit.light(&mut state, note, &full);
        }
        assert!(!lit.is_done(&state, true), "still lit as the envelope ends");
        let dark = [0.0; 3];
        for _ in 0..(5.0 * RATE) as usize {
            lit.light(&mut state, note, &dark);
        }
        assert!(lit.is_done(&state, true));
        assert!(lit.reads_envelope(0) && !lit.reads_envelope(1));
    }

    /// In VCA mode the gate only sets loudness: a steady signal comes out in proportion, unfiltered, louder with more light.
    #[test]
    fn a_vca_gate_sets_loudness_alone() {
        let vca = gate(&[("mode", "vca".into())]);
        let mut state = GateState::default();
        let note = GateNote {
            place: 1_000.0,
            pitch: 60.0,
            level: 1.0,
            octaves: 0.0,
        };
        let (dim, bright, signal) = (0.2, 1.0, 0.5);
        let quiet = vca.process(&mut state, signal, dim, note);
        let loud = vca.process(&mut state, signal, bright, note);
        assert!((loud - signal).abs() < 1e-3, "{loud}");
        assert!(quiet > 0.0 && quiet < loud);
    }
}
