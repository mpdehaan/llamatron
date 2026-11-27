// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The SID chip's ADSR: its rate table, its sixteen-level sustain and its counter's bugs.

use super::*;

pub fn sid_adsr(spec: &Value) -> EnvelopePart {
    let rate = |name: &str, default: f64| SID_PERIODS[(number(spec, name, default) as usize).min(15)] / SID_CLOCK;
    let attack_step = rate("attack", 0.0);
    let sustain = number(spec, "sustain", 10.0).clamp(0.0, 15.0) * SID_SUSTAIN_STEP;
    let rise = SID_TOP * attack_step;
    let mut held = vec![(0.0, 0.0)];
    for (time, level) in sid_fall(SID_TOP, sustain, rate("decay", 9.0)) {
        held.push((rise + time, level));
    }
    EnvelopePart::SidAdsr {
        held,
        release_step: rate("release", 9.0),
    }
}

/// The SID chip's fall from a counter level to a floor, as (seconds, level) points, one straight segment for each division
/// of its exponential counter, each slower.
pub(super) fn sid_fall(start: f64, floor: f64, step: f64) -> Vec<(f64, f64)> {
    let mut points = vec![(0.0, start)];
    let mut level = start;
    for (below, division) in SID_DIVISIONS {
        let lowest = below.max(floor);
        if level <= lowest {
            continue;
        }
        let time = points.last().map(|point| point.0).unwrap_or(0.0) + (level - lowest) * step * division;
        points.push((time, lowest));
        level = lowest;
        if level <= floor {
            break;
        }
    }
    points
}

/// A level read along (time, level) points, held at the last.
pub(super) fn along(points: &[(f64, f64)], time: f64) -> f64 {
    if time <= points[0].0 {
        return points[0].1;
    }
    for pair in points.windows(2) {
        let (start, end) = (pair[0], pair[1]);
        if time <= end.0 {
            let span = (end.0 - start.0).max(1e-12);
            return start.1 + (end.1 - start.1) * (time - start.0) / span;
        }
    }
    points[points.len() - 1].1
}

pub(super) fn sid_level(held: &[(f64, f64)], release_step: f64, state: &mut EnvelopeState, note: NoteTime) -> f64 {
    let mut counter = along(held, note.age);
    if let Some(released) = note.released {
        let from = *state.released_from.get_or_insert_with(|| along(held, released).floor());
        if note.age >= released {
            counter = along(&sid_fall(from, 0.0, release_step), note.age - released);
            if counter < 1.0 {
                state.done = true;
            }
        }
    }
    counter.floor() / SID_TOP
}
