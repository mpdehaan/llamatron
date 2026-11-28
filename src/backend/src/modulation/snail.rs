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
//! along a straight line between its steps. A Snail starts on its path, as a circuit that has been on for ever, and no
//! note or playback starts it again.

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
/// How far a seed moves a start's RC node from its point on the path, in volts, so that every instrument's and slot's
/// path parts from every other's within a minute or so.
const START_SPREAD: f64 = 0.03;
/// Where a circuit has left its bounds, and so is restarted: its RC node, or a capacitor's charge, in volts.
const MOST_NODE: f64 = 12.0;
const MOST_CHARGE: f64 = 30.0;

/// One circuit's parts: its capacitors in farads, its resistors in ohms, its inverter's gain, the time a step of its
/// clock lasts, the swing of each output to scale to -1 to 1, and points on its path, where a Snail starts.
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
    /// About how long a trip between two switches of side takes as built, in seconds, which a lane's speed sets anew.
    trip: f64,
    swings: [f64; OUTPUTS_A_CIRCUIT],
    on_path: [State; START_POINTS],
}

/// How many points on its path each circuit keeps to start from, a seed choosing one.
const START_POINTS: usize = 8;

/// The three circuits' parts, from their schematic, with points on each one's path read from a long run of it at the
/// centre of its weighting: Slow, Slower (its resistors ten times Slow's) and Slowest (a
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
        trip: 21.0,
        swings: [2.8, 6.0, 6.0],
        on_path: [
            [-1.242177, -0.371047, -1.689325],
            [0.000358, -0.051473, 1.512818],
            [1.125370, 0.250402, -2.120033],
            [-0.188981, -0.117495, 2.921949],
            [-0.631885, 0.098892, -0.228576],
            [2.235216, 0.148050, 5.147469],
            [0.336633, -0.084734, 3.471256],
            [1.242181, 0.228178, 2.882414],
        ],
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
        trip: 120.0,
        swings: [7.0, 10.0, 10.0],
        on_path: [
            [1.534898, 0.945275, -0.604615],
            [-1.295600, -0.863962, 1.485174],
            [-1.525860, -0.430134, -3.893539],
            [0.045007, 0.595299, 0.713837],
            [2.300526, -0.307875, 8.294381],
            [-3.321185, -0.073884, 1.033318],
            [5.132371, 0.596950, 7.361499],
            [2.678240, -0.098530, 7.898496],
        ],
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
        trip: 1860.0,
        swings: [6.5, 10.0, 10.0],
        on_path: [
            [-0.149621, -0.103403, -4.237310],
            [-0.513506, -0.107979, -4.581427],
            [-0.609190, -0.153281, -4.352226],
            [-3.701842, -0.055305, -10.031194],
            [-0.507113, 0.655621, -10.529017],
            [2.046779, 0.818628, -7.797679],
            [3.970024, 0.797511, -5.217237],
            [4.989934, 0.911482, -4.738417],
        ],
    },
];

/// A value held within the op-amps' swing.
#[inline]
fn swung(value: f64) -> f64 {
    value.clamp(-SWING, SWING)
}

/// A circuit's state: the charge on its first capacitor, its RC node, and the charge on its second capacitor, in volts.
type State = [f64; STATE_VARIABLES];
/// A state's three variables, by their places: the first capacitor's charge, the RC node, the second's charge.
const STATE_VARIABLES: usize = 3;
const X_CHARGE: usize = 0;
const NODE: usize = 1;
const Y_CHARGE: usize = 2;
/// An output's place among a circuit's three: X, Y and Z.
const Z_OUTPUT: usize = 2;
/// The span of a weighting from -1 to 1, by which it becomes a share from 0 to 1.
const WEIGHTING_SPAN: f64 = 2.0;
/// RK4's halving of a step for its middle slopes, the weight of those two, and the sum of the four slopes' weights.
const RK4_HALVING: f64 = 2.0;
const RK4_MIDDLE_WEIGHT: f64 = 2.0;
const RK4_WEIGHTS: f64 = 6.0;

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
    let y = swung(state[Y_CHARGE]);
    Read {
        x,
        y,
        z: swung(-parts.gain * y),
        at_x: x - state[0],
        at_y: y - state[Y_CHARGE],
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
    /// How much faster than built its clock runs, so that a trip takes the seconds its lane's speed chooses.
    pace: f64,
    /// Which of its outputs something reads: all until told otherwise.
    heard: [bool; OUTPUTS_A_CIRCUIT],
}

impl Circuit {
    /// A circuit started on its path, at the point its seed chooses, its RC node moved a little by the seed.
    fn seeded(parts: &'static Parts, seed: u64, trip_seconds: f64) -> Circuit {
        let mut random = Random::new(seed);
        let point = (random.next_u64() % START_POINTS as u64) as usize;
        let mut start = parts.on_path[point];
        start[1] += random.between(-START_SPREAD, START_SPREAD);
        let mut circuit = Circuit {
            parts,
            state: start,
            start,
            before: [0.0; OUTPUTS_A_CIRCUIT],
            after: [0.0; OUTPUTS_A_CIRCUIT],
            into_step: 0.0,
            pace: parts.trip / trip_seconds.max(f64::MIN_POSITIVE),
            heard: [true; OUTPUTS_A_CIRCUIT],
        };
        circuit.after = circuit.outputs();
        circuit.before = circuit.after;
        circuit
    }

    /// Its outputs now, each from -1 to 1.
    fn outputs(&self) -> [f64; OUTPUTS_A_CIRCUIT] {
        let Read { x, y, z, .. } = read(self.parts, &self.state);
        let swings = &self.parts.swings;
        [
            (x / swings[0]).clamp(-1.0, 1.0),
            (y / swings[1]).clamp(-1.0, 1.0),
            (z / swings[Z_OUTPUT]).clamp(-1.0, 1.0),
        ]
    }

    /// One step of its clock by RK4, at a weighting from -1 to 1: the knob's resistance across its range and a bias on
    /// the comparator, so that 0 is the circuit at its knob's centre and 1 keeps its Y above 0 the longest. A state that has left its bounds starts again.
    fn step(&mut self, weighting: f64) {
        let weighting = weighting.clamp(-1.0, 1.0);
        let parts = self.parts;
        let resistance = parts.fixed + parts.knob * (weighting + 1.0) / WEIGHTING_SPAN;
        let bias = if parts.knob > 0.0 { MOST_BIAS * weighting } else { 0.0 };
        let h = parts.step;
        let at = |state: &State, slope: &State, share: f64| -> State {
            [
                state[X_CHARGE] + share * slope[X_CHARGE],
                state[NODE] + share * slope[NODE],
                state[Y_CHARGE] + share * slope[Y_CHARGE],
            ]
        };
        let k1 = slopes(parts, &self.state, resistance, bias);
        let k2 = slopes(parts, &at(&self.state, &k1, h / RK4_HALVING), resistance, bias);
        let k3 = slopes(parts, &at(&self.state, &k2, h / RK4_HALVING), resistance, bias);
        let k4 = slopes(parts, &at(&self.state, &k3, h), resistance, bias);
        for place in 0..STATE_VARIABLES {
            self.state[place] += h / RK4_WEIGHTS * (k1[place] + RK4_MIDDLE_WEIGHT * k2[place] + RK4_MIDDLE_WEIGHT * k3[place] + k4[place]);
        }
        let escaped = self.state.iter().any(|value| !value.is_finite())
            || self.state[NODE].abs() > MOST_NODE
            || self.state[X_CHARGE].abs() > MOST_CHARGE
            || self.state[Y_CHARGE].abs() > MOST_CHARGE;
        if escaped {
            self.state = self.start;
        }
    }

    /// Move its clock on by some seconds, stepping where a step falls due at the weighting given, and write the outputs
    /// it is heard at, read along a straight line between its last two steps.
    #[inline]
    fn advance(&mut self, seconds: f64, weighting: f64, written: &mut [f64]) {
        self.into_step += seconds * self.pace / self.parts.step;
        while self.into_step >= 1.0 {
            self.step(weighting);
            self.before = self.after;
            self.after = self.outputs();
            self.into_step -= 1.0;
        }
        let share = self.into_step;
        for (place, value) in written.iter_mut().enumerate() {
            if self.heard[place] {
                *value = self.before[place] + (self.after[place] - self.before[place]) * share;
            }
        }
    }
}

/// A Snail: its three circuits and the weightings set for Slow and Slower, from -1 to 1.
pub struct Snail {
    circuits: Vec<Circuit>,
    pub weightings: [f64; WEIGHTED_COUNT],
    pub trips: [Option<f64>; CIRCUIT_COUNT],
}

impl Snail {
    /// A Snail seeded by its instrument and its slot, its weightings set, each lane's trip lasting the seconds given, or
    /// as built where none is given.
    pub fn seeded(seed: u64, weightings: [f64; WEIGHTED_COUNT], trips: [Option<f64>; CIRCUIT_COUNT]) -> Snail {
        let circuits = CIRCUITS
            .iter()
            .enumerate()
            .map(|(place, parts)| {
                let trip = trips[place].unwrap_or(parts.trip);
                Circuit::seeded(parts, seed.wrapping_mul(CIRCUIT_COUNT as u64).wrapping_add(place as u64), trip)
            })
            .collect();
        Snail { circuits, weightings, trips }
    }

    /// Move every circuit on by a sample of some seconds, each weighted circuit at its weighting moved by what the Mod
    /// Matrix adds, and write its nine outputs.
    #[inline]
    pub fn advance(&mut self, seconds: f64, moved: [f64; WEIGHTED_COUNT], outputs: &mut [f64; OUTPUT_COUNT]) {
        for (place, circuit) in self.circuits.iter_mut().enumerate() {
            // A lane nothing reads is never stepped, costing nothing.
            if !circuit.heard.iter().any(|heard| *heard) {
                continue;
            }
            let weighting = if place < WEIGHTED_COUNT { self.weightings[place] + moved[place] } else { 0.0 };
            circuit.advance(seconds, weighting, &mut outputs[place * OUTPUTS_A_CIRCUIT..(place + 1) * OUTPUTS_A_CIRCUIT]);
        }
    }

    /// The same Snail seeded anew, hearing what it heard.
    pub fn reseeded(&self, seed: u64) -> Snail {
        let mut snail = Snail::seeded(seed, self.weightings, self.trips);
        for (fresh, old) in snail.circuits.iter_mut().zip(self.circuits.iter()) {
            fresh.heard = old.heard;
        }
        snail
    }

    /// Hear only the outputs something reads, by their places among the nine, so that a lane none of whose outputs is
    /// read is never stepped and an output nobody reads is never worked out.
    pub fn hear_only(&mut self, read: &[usize]) {
        for (place, circuit) in self.circuits.iter_mut().enumerate() {
            circuit.heard = std::array::from_fn(|output| read.contains(&(place * OUTPUTS_A_CIRCUIT + output)));
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
        let mut circuit = Circuit::seeded(&CIRCUITS[place], seed, CIRCUITS[place].trip);
        let reads = (seconds / READ_EVERY) as usize;
        (0..reads)
            .map(|_| {
                let mut three = [0.0; OUTPUTS_A_CIRCUIT];
                circuit.advance(READ_EVERY, weighting, &mut three);
                three[1] > 0.0
            })
            .collect()
    }

    /// The share of reads on the upper lobe, where Y is above 0, and the mean time between two switches of lobe, in seconds.
    fn share_and_cycle(on_upper: &[bool]) -> (f64, f64) {
        let upper = on_upper.iter().filter(|upper| **upper).count() as f64 / on_upper.len() as f64;
        let pair = 2;
        let switches = on_upper.windows(pair).filter(|pair| pair[0] != pair[1]).count().max(1) as f64;
        // A cycle is two switches, one to each side.
        let switches_a_cycle = 2.0;
        let cycle = switches_a_cycle * on_upper.len() as f64 * READ_EVERY / switches;
        (upper, cycle)
    }

    /// Slow switches lobes about every 20 seconds a cycle, its outputs within -1 to 1, and a stronger weighting keeps it
    /// longer on one lobe; two starts a hair apart part ways, as chaos does.
    #[test]
    fn slow_wanders_between_its_lobes_about_every_twenty_seconds() {
        let (seconds, seed) = (4000.0, 7);
        let (centre, cycle) = share_and_cycle(&lobes(0, seed, 0.0, seconds));
        let (shortest_cycle, longest_cycle) = (15.0, 30.0);
        assert!((shortest_cycle..longest_cycle).contains(&cycle), "cycle {cycle}");
        let (low, _) = share_and_cycle(&lobes(0, seed, -1.0, seconds));
        let (high, _) = share_and_cycle(&lobes(0, seed, 1.0, seconds));
        let (leaned, ten_minutes) = (0.05, 600.0);
        assert!(low < centre - leaned && high > centre + leaned, "{low} {centre} {high}");
        assert_ne!(lobes(0, seed, 0.0, ten_minutes), lobes(0, seed + 1, 0.0, ten_minutes));
    }

    /// Slower and Slowest stay chaotic and bounded at their own slower cycles, held by the op-amps' rails.
    #[test]
    fn slower_and_slowest_keep_their_own_slow_cycles() {
        let seed = 7;
        let (slower_place, slowest_place) = (1, 2);
        let (slower_heard, shortest_slower, longest_slower) = (6000.0, 80.0, 180.0);
        let (slowest_heard, shortest_slowest) = (30000.0, 900.0);
        let (_, slower) = share_and_cycle(&lobes(slower_place, seed, 0.0, slower_heard));
        assert!((shortest_slower..longest_slower).contains(&slower), "slower {slower}");
        let (_, slowest) = share_and_cycle(&lobes(slowest_place, seed, 0.0, slowest_heard));
        assert!(slowest > shortest_slowest, "slowest {slowest}");
    }

    /// A Snail reads the same whatever the size of the samples it is moved by, since its clock is its own.
    #[test]
    fn a_snail_follows_its_own_clock_whatever_the_sample_rate() {
        let heard = 30.0;
        let path = |rate: f64| {
            let seed = 3;
            let mut snail = Snail::seeded(seed, [0.0, 0.0], [None; CIRCUIT_COUNT]);
            let mut outputs = [0.0; OUTPUT_COUNT];
            for _ in 0..(heard * rate) as usize {
                snail.advance(1.0 / rate, [0.0, 0.0], &mut outputs);
            }
            outputs[1]
        };
        let (one_rate, other_rate, near) = (44_100.0, 48_000.0, 0.02);
        assert!((path(one_rate) - path(other_rate)).abs() < near);
    }

    /// A Snail's outputs move by fine, unrounded amounts from one sample to the next, never standing still for a step
    /// of its clock and never jumping, so that whatever it moves follows it smoothly.
    #[test]
    fn a_snails_outputs_move_finely_and_smoothly() {
        let rate = 48_000.0;
        let (heard_seconds, seed) = (5.0, 5);
        let heard = (heard_seconds * rate) as usize;
        let most_change = 1e-4;
        let mut snail = Snail::seeded(seed, [0.0, 0.0], [None; CIRCUIT_COUNT]);
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
        let (nine, tenths) = (9, 10);
        assert!(moved_samples > heard * nine / tenths, "Slow X moved on {moved_samples} of {heard} samples");
    }

    /// A Snail hearing one output works it out exactly as one hearing all, and leaves the lanes nothing reads unstepped.
    #[test]
    fn a_snail_works_out_only_what_is_read() {
        let (rate, seconds, slow_x) = (48_000.0, 2.0, 0);
        let run = |snail: &mut Snail| {
            let mut outputs = [0.0; OUTPUT_COUNT];
            for _ in 0..(rate * seconds) as usize {
                snail.advance(1.0 / rate, [0.0, 0.0], &mut outputs);
            }
            outputs
        };
        let seed = 9;
        let everything = run(&mut Snail::seeded(seed, [0.0, 0.0], [None; CIRCUIT_COUNT]));
        let mut one = Snail::seeded(seed, [0.0, 0.0], [None; CIRCUIT_COUNT]);
        one.hear_only(&[slow_x]);
        let alone = run(&mut one);
        assert_eq!(alone[slow_x], everything[slow_x]);
        assert!(alone.iter().skip(1).all(|output| *output == 0.0), "only Slow X is worked out");
        assert!(
            one.circuits[1..].iter().all(|circuit| circuit.state == circuit.start),
            "the unread lanes never step"
        );
        let reseeded = one.reseeded(seed);
        assert!(reseeded.circuits[1].heard.iter().all(|heard| !heard), "a reseeded Snail hears what it heard");
    }

    /// A lane's speed sets how long its trips take: Slow at its fast 7 seconds switches sides about three times as
    /// often as at its built 21.
    #[test]
    fn a_lanes_speed_sets_how_long_its_trips_take() {
        let (seconds, seed, fast) = (2000.0, 7, 7.0);
        let path = |trip: f64| {
            let mut circuit = Circuit::seeded(&CIRCUITS[0], seed, trip);
            let reads = (seconds / READ_EVERY) as usize;
            (0..reads)
                .map(|_| {
                    let mut three = [0.0; OUTPUTS_A_CIRCUIT];
                    circuit.advance(READ_EVERY, 0.0, &mut three);
                    three[1] > 0.0
                })
                .collect::<Vec<_>>()
        };
        let (_, built) = share_and_cycle(&path(CIRCUITS[0].trip));
        let (_, quick) = share_and_cycle(&path(fast));
        let ratio = built / quick;
        let (least, most) = (2.0, 4.5);
        assert!((least..most).contains(&ratio), "built {built} quick {quick}");
    }
}
