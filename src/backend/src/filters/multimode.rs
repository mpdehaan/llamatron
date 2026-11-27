// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Multimode filter: a state-variable filter of two integrators, low, band, high or notch, its Q from the resonance,
//! its band integrator saturating softly.

use super::ota::soft_limit;
use super::{FilterMode, FilterPart, FilterState};

impl FilterPart {
    /// The state-variable filter (two integrators), its damping the stored feedback, its output by the mode.
    #[inline]
    pub(super) fn state_variable(&self, state: &mut FilterState, input: f64) -> f64 {
        let g = state.g;
        let damping = state.feedback;
        let [first, second, _, _] = state.stages;
        let high = (input - (damping + g) * first - second) / (1.0 + damping * g + g * g);
        let band = g * high + first;
        let low = g * band + second;
        // The band integrator saturates softly, as the nonlinear-state filters of sst-filters' ResonanceWarp do: quiet
        // signals pass as before, and a loud, resonant peak is held round rather than ringing out of bounds.
        // After sst-filters' ResonanceWarp (Surge Synth Team, GPL-3.0-or-later); our own implementation.
        state.stages[0] = soft_limit(g * high + band);
        state.stages[1] = g * band + low;
        match self.mode {
            FilterMode::Low => low,
            FilterMode::Band => band * damping,
            FilterMode::High => high,
            FilterMode::Notch => input - band * damping,
        }
    }
}
