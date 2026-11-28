// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The vactrol: a lamp lighting a photoresistor, its rise and fall slowed by the cell's memory and age, every strike
//! a little its own.

use super::*;
use llamatron_names::spec;

/// What a vactrol takes where its spec names none: its cell's rise and fall and a strike's width, in seconds, and its
/// memory's share.
const DEFAULT_RISE: f64 = 0.012;
const DEFAULT_FALL: f64 = 0.25;
const DEFAULT_STRIKE_WIDTH: f64 = 0.002;
const DEFAULT_MEMORY: f64 = 0.3;

/// A cell's rise and fall in seconds at a Response from 0 (fast) to 1 (lazy), each moving evenly in its logarithm between
/// the two cells it lies between, and slowed by its Age, as an old cell is.
pub fn cell_times(response: f64, age: f64) -> (f64, f64) {
    let response = response.clamp(0.0, 1.0);
    let after = CELLS.iter().position(|cell| cell.0 >= response).unwrap_or(CELLS.len() - 1).max(1);
    let (from, to) = (CELLS[after - 1], CELLS[after]);
    let along = (response - from.0) / (to.0 - from.0);
    let between = |low: f64, high: f64| low * (high / low).powf(along);
    let rise = between(from.1, to.1).max(SHORTEST_ATTACK) * (1.0 + AGE_SLOWER_RISE * age);
    let fall = between(from.2, to.2).max(SHORTEST_CELL_FALL) * (1.0 + AGE_LONGER_FALL * age);
    (rise, fall)
}

pub fn vactrol(spec: &Value) -> EnvelopePart {
    let age = number(spec, spec::AGE, 0.0);
    let light = 1.0 - AGE_DIMMING * age;
    let (rise, fall) = match spec_number(spec, spec::RESPONSE) {
        Some(response) => cell_times(response, age),
        None => (
            number(spec, spec::RISE, DEFAULT_RISE).max(SHORTEST_ATTACK) * (1.0 + AGE_SLOWER_RISE * age),
            number(spec, spec::FALL, DEFAULT_FALL).max(SHORTEST_CELL_FALL) * (1.0 + AGE_LONGER_FALL * age),
        ),
    };
    let unstable = 1.0 - number(spec, "stability", 1.0);
    let gated = word(spec, spec::DRIVE, spec::STRIKE) != spec::STRIKE;
    let width = number(spec, spec::STRIKE_WIDTH, DEFAULT_STRIKE_WIDTH);
    let full = if gated {
        1.0
    } else {
        1.0 - (-width / (rise * light.powf(-RISE_POWER))).exp()
    };
    EnvelopePart::Vactrol {
        rise,
        fall,
        gated,
        width,
        memory: (number(spec, spec::MEMORY, DEFAULT_MEMORY) * (1.0 + AGE_MORE_MEMORY * age)).min(1.0),
        light,
        unstable: (
            FALL_SPREAD * unstable + AGE_SPREAD * age,
            RISE_SPREAD * unstable + AGE_RISE_SPREAD * age,
            LIGHT_SPREAD * unstable + AGE_SPREAD * age,
        ),
        drift: DRIFT * unstable,
        full,
    }
}

pub(super) fn vactrol_level(state: &mut EnvelopeState, note: NoteTime, gated: bool, width: f64, full: f64) -> f64 {
    let lit = if gated { note.released.unwrap_or(f64::INFINITY) } else { width };
    let rising = |age: f64| state.drive + (state.start_level - state.drive) * (-age.min(lit) / state.rise).exp();
    let level = if note.age < lit {
        rising(note.age)
    } else {
        let peak = rising(lit);
        let out = fallen_scaled(peak, note.age - lit, state.hyperbola, full);
        if out < SILENT {
            state.done = true;
        }
        out
    };
    (level / full).min(MOST_LIGHT)
}

/// The cell's conductance a time after its light went off: the hyperbolic fall, and a slow leak under its tail.
pub(super) fn fallen(level: f64, seconds: f64, hyperbola: f64) -> f64 {
    level / (1.0 + hyperbola * level * seconds) * (-seconds / LEAK_SECONDS).exp()
}

/// The fall of a light that a strike lit only to a share of full (full, 1 when held), worked out on the light as it is
/// heard, scaled up to full: the hyperbola falls faster the brighter the cell, so a strike's small real light must fall at
/// the speed its heard level gives, reaching a tenth at its Fall time whatever its Trigger time.
pub(super) fn fallen_scaled(level: f64, seconds: f64, hyperbola: f64, full: f64) -> f64 {
    fallen(level / full, seconds, hyperbola) * full
}

/// Three standard normals for a vactrol's hit by its number, the same every playing: splitmix64 through Box-Muller.
pub(super) fn hit_normals(hit: u64) -> (f64, f64, f64) {
    let (first, second) = uniforms(hit * 2 + 1);
    let (third, fourth) = uniforms(hit * 2 + 2);
    let radius = (-2.0 * first.ln()).sqrt();
    let angle = 2.0 * std::f64::consts::PI * second;
    (
        radius * angle.cos(),
        radius * angle.sin(),
        (-2.0 * third.ln()).sqrt() * (2.0 * std::f64::consts::PI * fourth).cos(),
    )
}

pub(super) fn uniforms(number: u64) -> (f64, f64) {
    let mix = |step: u64| {
        let mut value = step.wrapping_mul(0x9E37_79B9_7F4A_7C15);
        value = (value ^ (value >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        value = (value ^ (value >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        value ^= value >> 31;
        (value as f64 + 1.0) / (u64::MAX as f64 + 2.0)
    };
    (mix(number), mix(number.wrapping_add(0x9E37_79B9_7F4A_7C15)))
}

/// The room's warmth from -1 to 1 at a time: slow, smooth and the same every playing.
pub(super) fn room_warmth(seconds: f64) -> f64 {
    WARMTH
        .iter()
        .map(|(period, weight, phase)| weight * (2.0 * std::f64::consts::PI * seconds / period + phase).sin())
        .sum()
}
