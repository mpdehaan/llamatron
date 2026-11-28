// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Snail: three slow chaotic circuits, Slow, Slower and Slowest, about 20 seconds, 2 minutes and 30 minutes a cycle,
//! each wandering around two lobes and switching between them at irregular times; each gives its X, Y and Z, and Slow
//! and Slower each take a weighting of which lobe they linger around. Never restarted by a note.
//!
//! Each circuit is the jerk circuit of Sprott ("A new class of chaotic circuit", Physics Letters A 266, 2000): two
//! op-amp integrators and a passive RC node, an inverter and a comparator, with the op-amps' rails modelled, since the
//! slower two are held by them (`.claude/notes/synthesis/MODULATORS_RESEARCH.md`, section 3). Each is stepped by RK4 on a
//! clock of its own, never the sample rate's or a chunk's, so that a chaotic path is the same in every render, and read
//! along a straight line between its steps.

use crate::dsp::Random;

/// The circuits of a Snail, and the outputs of each.
pub const CIRCUIT_COUNT: usize = 3;
pub const OUTPUTS_A_CIRCUIT: usize = 3;
/// Every output of a Snail: X, Y and Z of Slow, of Slower and of Slowest, in that order.
pub const OUTPUT_COUNT: usize = CIRCUIT_COUNT * OUTPUTS_A_CIRCUIT;
/// The circuits that take a weighting, Slow and Slower.
pub const WEIGHTED_COUNT: usize = 2;

/// The linear stages' swing and the comparator's two rails, in volts, the rails as measured on one build.
const SWING: f64 = 10.0;
const HIGH_RAIL: f64 = 11.38;
const LOW_RAIL: f64 = -10.64;
/// How far a full weighting shifts the comparator's rails, in volts: enough to move the share of time on a lobe from
/// about a third to about two thirds while every circuit stays chaotic.
const MOST_BIAS: f64 = 1.5;
/// The start's spread on the RC node, in volts, and the seed of each slot's circuits.
const START_SPREAD: f64 = 0.03;
/// Where a circuit has left its bounds, and so is restarted: its RC node, or a capacitor's charge, in volts.
const MOST_NODE: f64 = 12.0;
const MOST_CHARGE: f64 = 30.0;

/// One circuit's parts: its capacitors in farads, its resistors in ohms, its inverter's gain, the time a step of its
/// clock lasts, how long it runs before it is first heard, and the swing of each output to scale to -1 to 1.
struct Parts {
    cx: f64,
    cw: f64,
    cy: f64,
    /// The fixed part of the resistance from the RC node back to the first integrator, and the knob's part of it.
    fixed: f64,
    knob: f64,
    rxw: f64,
    rwy: f64,
    rzi: f64,
    rq: f64,
    gain: f64,
    step: f64,
    warm_up: f64,
    swings: [f64; OUTPUTS_A_CIRCUIT],
}

/// The three circuits' parts, from their schematic: Slow, Slower (its resistors ten times Slow's) and Slowest (a
/// hundred times, with no knob, a smaller RC capacitor and an inverter's gain of 1.5).
const CIRCUITS: [Parts; CIRCUIT_COUNT] = [
    Parts {
        cx: 2e-6,
        cw: 50e-6,
        cy: 1e-6,
        fixed: 100e3,
        knob: 10e3,
        rxw: 100e3,
        rwy: 100e3,
        rzi: 1e6,
        rq: 4.7e6,
        gain: 1.0,
        step: 0.0025,
        warm_up: 120.0,
        swings: [2.8, 6.0, 6.0],
    },
    Parts {
        cx: 2e-6,
        cw: 50e-6,
        cy: 1e-6,
        fixed: 1e6,
        knob: 100e3,
        rxw: 1e6,
        rwy: 1e6,
        rzi: 6.8e6,
        rq: 14.7e6,
        gain: 1.0,
        step: 0.025,
        warm_up: 600.0,
        swings: [7.0, 10.0, 10.0],
    },
    Parts {
        cx: 2e-6,
        cw: 40e-6,
        cy: 1e-6,
        fixed: 10e6,
        knob: 0.0,
        rxw: 10e6,
        rwy: 10e6,
        rzi: 68e6,
        rq: 100e6,
        gain: 1.5,
        step: 0.25,
        warm_up: 7200.0,
        swings: [6.5, 10.0, 10.0],
    },
];

/// A value held within the op-amps' swing.
#[inline]
fn swung(value: f64) -> f64 {
    value.clamp(-SWING, SWING)
}

/// A circuit's state: the charge on its first capacitor, its RC node, and the charge on its second capacitor, in volts.
type State = [f64; 3];

/// What a state gives at its outputs, X, Y and Z, in volts, and the summing nodes' voltages where an op-amp is at a rail.
struct Read {
    x: f64,
    y: f64,
    z: f64,
    at_x: f64,
    at_y: f64,
}

/// A state's outputs: each integrator's output its charge held within the swing, its summing node off ground by the
/// difference while it is held, and Z the inverted Y.
#[inline]
fn read(parts: &Parts, state: &State) -> Read {
    let x = swung(state[0]);
    let y = swung(state[2]);
    Read {
        x,
        y,
        z: swung(-parts.gain * y),
        at_x: x - state[0],
        at_y: y - state[2],
    }
}

/// How fast a state changes, by Kirchhoff's current law at the circuit's three nodes, with the knob's resistance and the
/// bias on the comparator's rails.
// Plain arithmetic only, never a fused multiply-add, so that the path is the same bits on every computer.
#[inline]
fn slopes(parts: &Parts, state: &State, resistance: f64, bias: f64) -> State {
    let Read { x, z, at_x, at_y, .. } = read(parts, state);
    let w = state[1];
    let rail = if z < 0.0 { HIGH_RAIL } else { LOW_RAIL } + bias;
    let into_x = (z - at_x) / parts.rzi + (rail - at_x) / parts.rq + (w - at_x) / resistance;
    let into_w = (x - w) / parts.rxw + (at_x - w) / resistance - (w - at_y) / parts.rwy;
    [-into_x / parts.cx, into_w / parts.cw, -(w - at_y) / (parts.rwy * parts.cy)]
}

/// One circuit of a Snail: its parts, its state, where it started, the outputs of its last two steps, how far its clock
/// has gone into the step now, and its weighting from -1 to 1.
struct Circuit {
    parts: &'static Parts,
    state: State,
    start: State,
    before: [f64; OUTPUTS_A_CIRCUIT],
    after: [f64; OUTPUTS_A_CIRCUIT],
    into_step: f64,
}

impl Circuit {
    /// A circuit started from a seeded point near rest and run at its weighting until it is on its attractor, so that a
    /// weighting set is heard from the first note.
    fn seeded(parts: &'static Parts, seed: u64, weighting: f64) -> Circuit {
        let mut random = Random::new(seed);
        let start = [0.0, random.between(-START_SPREAD, START_SPREAD), 0.0];
        let mut circuit = Circuit {
            parts,
            state: start,
            start,
            before: [0.0; OUTPUTS_A_CIRCUIT],
            after: [0.0; OUTPUTS_A_CIRCUIT],
            into_step: 0.0,
        };
        let steps = (parts.warm_up / parts.step) as usize;
        for _ in 0..steps {
            circuit.step(weighting);
        }
        circuit.start = circuit.state;
        circuit.restart();
        circuit
    }

    /// Back to where it was first heard.
    fn restart(&mut self) {
        self.state = self.start;
        self.after = self.outputs();
        self.before = self.after;
        self.into_step = 0.0;
    }

    /// Its outputs now, each from -1 to 1.
    fn outputs(&self) -> [f64; OUTPUTS_A_CIRCUIT] {
        let Read { x, y, z, .. } = read(self.parts, &self.state);
        let swings = &self.parts.swings;
        [
            (x / swings[0]).clamp(-1.0, 1.0),
            (y / swings[1]).clamp(-1.0, 1.0),
            (z / swings[2]).clamp(-1.0, 1.0),
        ]
    }

    /// One step of its clock by RK4, at a weighting from -1 to 1: the knob's resistance across its range and a bias on
    /// the comparator, so that 0 is the circuit at its knob's centre and 1 keeps its Y above 0 the longest. A state that has left its bounds starts again.
    fn step(&mut self, weighting: f64) {
        let weighting = weighting.clamp(-1.0, 1.0);
        let parts = self.parts;
        let resistance = parts.fixed + parts.knob * (weighting + 1.0) / 2.0;
        let bias = if parts.knob > 0.0 { MOST_BIAS * weighting } else { 0.0 };
        let h = parts.step;
        let at =
            |state: &State, slope: &State, share: f64| -> State { [state[0] + share * slope[0], state[1] + share * slope[1], state[2] + share * slope[2]] };
        let k1 = slopes(parts, &self.state, resistance, bias);
        let k2 = slopes(parts, &at(&self.state, &k1, h / 2.0), resistance, bias);
        let k3 = slopes(parts, &at(&self.state, &k2, h / 2.0), resistance, bias);
        let k4 = slopes(parts, &at(&self.state, &k3, h), resistance, bias);
        for place in 0..3 {
            self.state[place] += h / 6.0 * (k1[place] + 2.0 * k2[place] + 2.0 * k3[place] + k4[place]);
        }
        let escaped = self.state.iter().any(|value| !value.is_finite())
            || self.state[1].abs() > MOST_NODE
            || self.state[0].abs() > MOST_CHARGE
            || self.state[2].abs() > MOST_CHARGE;
        if escaped {
            self.state = self.start;
        }
    }

    /// Move its clock on by some seconds, stepping where a step falls due at the weighting given, and give its outputs
    /// there, read along a straight line between its last two steps.
    #[inline]
    fn advance(&mut self, seconds: f64, weighting: f64) -> [f64; OUTPUTS_A_CIRCUIT] {
        self.into_step += seconds / self.parts.step;
        while self.into_step >= 1.0 {
            self.step(weighting);
            self.before = self.after;
            self.after = self.outputs();
            self.into_step -= 1.0;
        }
        let share = self.into_step;
        std::array::from_fn(|place| self.before[place] + (self.after[place] - self.before[place]) * share)
    }
}

/// A Snail: its three circuits and the weightings set for Slow and Slower, from -1 to 1.
pub struct Snail {
    circuits: Vec<Circuit>,
    pub weightings: [f64; WEIGHTED_COUNT],
}

impl Snail {
    /// A Snail seeded by its instrument and its slot, its weightings set.
    pub fn seeded(seed: u64, weightings: [f64; WEIGHTED_COUNT]) -> Snail {
        let circuits = CIRCUITS
            .iter()
            .enumerate()
            .map(|(place, parts)| {
                let weighting = weightings.get(place).copied().unwrap_or(0.0);
                Circuit::seeded(parts, seed.wrapping_mul(CIRCUIT_COUNT as u64).wrapping_add(place as u64), weighting)
            })
            .collect();
        Snail { circuits, weightings }
    }

    /// Every circuit back to where it was first heard, as playback starts from silence.
    pub fn restart(&mut self) {
        for circuit in &mut self.circuits {
            circuit.restart();
        }
    }

    /// Move every circuit on by a sample of some seconds, each weighted circuit at its weighting moved by what the Mod
    /// Matrix adds, and write its nine outputs.
    #[inline]
    pub fn advance(&mut self, seconds: f64, moved: [f64; WEIGHTED_COUNT], outputs: &mut [f64; OUTPUT_COUNT]) {
        for (place, circuit) in self.circuits.iter_mut().enumerate() {
            let weighting = if place < WEIGHTED_COUNT { self.weightings[place] + moved[place] } else { 0.0 };
            let three = circuit.advance(seconds, weighting);
            outputs[place * OUTPUTS_A_CIRCUIT..(place + 1) * OUTPUTS_A_CIRCUIT].copy_from_slice(&three);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// How often a circuit's path is read, in seconds, and how long each is heard for in the tests.
    const READ_EVERY: f64 = 0.01;

    /// The lobe a circuit is on at each read, by the sign of its Y, over some seconds at a weighting.
    fn lobes(place: usize, seed: u64, weighting: f64, seconds: f64) -> Vec<bool> {
        let mut circuit = Circuit::seeded(&CIRCUITS[place], seed, weighting);
        let reads = (seconds / READ_EVERY) as usize;
        (0..reads).map(|_| circuit.advance(READ_EVERY, weighting)[1] > 0.0).collect()
    }

    /// The share of reads on the upper lobe, where Y is above 0, and the mean time between two switches of lobe, in seconds.
    fn share_and_cycle(on_upper: &[bool]) -> (f64, f64) {
        let upper = on_upper.iter().filter(|upper| **upper).count() as f64 / on_upper.len() as f64;
        let switches = on_upper.windows(2).filter(|pair| pair[0] != pair[1]).count().max(1) as f64;
        let cycle = 2.0 * on_upper.len() as f64 * READ_EVERY / switches;
        (upper, cycle)
    }

    /// Slow switches lobes about every 20 seconds a cycle, its outputs within -1 to 1, and a stronger weighting keeps it
    /// longer on one lobe; two starts a hair apart part ways, as chaos does.
    #[test]
    fn slow_wanders_between_its_lobes_about_every_twenty_seconds() {
        let (seconds, seed) = (4000.0, 7);
        let (centre, cycle) = share_and_cycle(&lobes(0, seed, 0.0, seconds));
        assert!((15.0..30.0).contains(&cycle), "cycle {cycle}");
        let (low, _) = share_and_cycle(&lobes(0, seed, -1.0, seconds));
        let (high, _) = share_and_cycle(&lobes(0, seed, 1.0, seconds));
        assert!(low < centre - 0.05 && high > centre + 0.05, "{low} {centre} {high}");
        assert_ne!(lobes(0, seed, 0.0, 600.0), lobes(0, seed + 1, 0.0, 600.0));
    }

    /// Slower and Slowest stay chaotic and bounded at their own slower cycles, held by the op-amps' rails.
    #[test]
    fn slower_and_slowest_keep_their_own_slow_cycles() {
        let seed = 7;
        let (_, slower) = share_and_cycle(&lobes(1, seed, 0.0, 6000.0));
        assert!((80.0..180.0).contains(&slower), "slower {slower}");
        let (_, slowest) = share_and_cycle(&lobes(2, seed, 0.0, 30000.0));
        assert!(slowest > 900.0, "slowest {slowest}");
    }

    /// A Snail reads the same whatever the size of the samples it is moved by, since its clock is its own.
    #[test]
    fn a_snail_follows_its_own_clock_whatever_the_sample_rate() {
        let heard = 30.0;
        let path = |rate: f64| {
            let mut snail = Snail::seeded(3, [0.0, 0.0]);
            let mut outputs = [0.0; OUTPUT_COUNT];
            for _ in 0..(heard * rate) as usize {
                snail.advance(1.0 / rate, [0.0, 0.0], &mut outputs);
            }
            outputs[1]
        };
        assert!((path(44_100.0) - path(48_000.0)).abs() < 0.02);
    }

    /// A Snail's outputs move by fine, unrounded amounts from one sample to the next, never standing still for a step
    /// of its clock and never jumping, so that whatever it moves follows it smoothly.
    #[test]
    fn a_snails_outputs_move_finely_and_smoothly() {
        let rate = 48_000.0;
        let heard = (5.0 * rate) as usize;
        let most_change = 1e-4;
        let mut snail = Snail::seeded(5, [0.0, 0.0]);
        let mut outputs = [0.0; OUTPUT_COUNT];
        snail.advance(1.0 / rate, [0.0, 0.0], &mut outputs);
        let mut last = outputs[0];
        let mut moved_samples = 0;
        for _ in 0..heard {
            snail.advance(1.0 / rate, [0.0, 0.0], &mut outputs);
            let change = (outputs[0] - last).abs();
            assert!(change < most_change, "Slow X jumped by {change}");
            if change > 0.0 {
                moved_samples += 1;
            }
            last = outputs[0];
        }
        assert!(moved_samples > heard * 9 / 10, "Slow X moved on {moved_samples} of {heard} samples");
    }
}
