// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Music theory's fundamentals (the Python music_theory/fundamentals/): intervals, the scale and chord shapes, generated from
//! the Python, and voice leading.

pub mod generated;
pub mod voice_leading;

use generated::chord_shapes::ROLES_BY_HALF_STEPS;
use generated::intervals::HALF_STEPS_PER_OCTAVE;

/// What a chord's note some half steps above its root is to the chord: root, third or fifth, or None.
pub fn role_of(half_steps: i64) -> Option<&'static str> {
    let place = half_steps.rem_euclid(HALF_STEPS_PER_OCTAVE);
    ROLES_BY_HALF_STEPS.iter().find(|(steps, _)| *steps == place).map(|(_, role)| *role)
}
