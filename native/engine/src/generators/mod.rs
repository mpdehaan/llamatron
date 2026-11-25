// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The generators a clip's notes run through (the Python engine/generators/), a module a plugin.

pub mod arp;
pub mod chords;
pub mod guitarify;
pub mod timing;

use crate::clip::Clip;
use crate::error::Rendered;

/// A generator made for one step of a clip's chains.
pub enum Generator {
    Chords(chords::ChordsGenerator),
    Arp(arp::Arp),
    Guitarify(guitarify::Guitarify),
    Timing(timing::TimingGenerator),
    /// A generator whose settings change no notes in the chain.
    Unchanged,
}

impl Generator {
    pub fn generate(&mut self, clip: &Clip) -> Rendered<Clip> {
        match self {
            Generator::Chords(generator) => generator.generate(clip),
            Generator::Arp(generator) => generator.generate(clip),
            Generator::Guitarify(generator) => generator.generate(clip),
            Generator::Timing(generator) => generator.generate(clip),
            Generator::Unchanged => Ok(Clip {
                sounds: clip.resolved_sounds()?,
                ..clip.clone()
            }),
        }
    }

    /// The state the clip it made left it in, for the same track's next clip to carry on from.
    pub fn end_state(&self) -> Option<Vec<i64>> {
        match self {
            Generator::Chords(generator) => generator.end_state(),
            Generator::Arp(_) | Generator::Guitarify(_) | Generator::Timing(_) | Generator::Unchanged => None,
        }
    }
}
