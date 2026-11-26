// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The generators a clip's notes run through (the Python engine/generators/), a module a plugin.

pub mod arp;
pub mod chords;
pub mod guitarify;
pub mod musician;
pub mod parts;
pub mod phrasing;
pub mod timing;

use crate::clip::Clip;
use llamatron_math::PythonRandom;

/// The state a generator leaves a clip in, for the same track's next clip in its run to carry on from: a voicing's last
/// chord, or where a random generator's draws had reached.
#[derive(Clone, Debug, PartialEq)]
pub enum GeneratorState {
    Voicing(Vec<i64>),
    Random(Box<PythonRandom>),
}
use crate::error::Rendered;

/// A generator made for one step of a clip's chains.
pub enum Generator {
    Chords(chords::ChordsGenerator),
    Arp(Box<arp::Arp>),
    Guitarify(guitarify::Guitarify),
    Timing(timing::TimingGenerator),
    Phrasing(phrasing::Phrasing),
    Musician(Box<musician::Musician>),
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
            Generator::Phrasing(generator) => generator.generate(clip),
            Generator::Musician(generator) => generator.generate(clip),
            Generator::Unchanged => Ok(Clip {
                sounds: clip.resolved_sounds()?,
                ..clip.clone()
            }),
        }
    }

    /// The state the clip it made left it in, for the same track's next clip to carry on from.
    pub fn end_state(&self) -> Option<GeneratorState> {
        match self {
            Generator::Chords(generator) => generator.end_state().map(GeneratorState::Voicing),
            Generator::Arp(generator) => generator.end_state(),
            Generator::Guitarify(_) | Generator::Timing(_) | Generator::Phrasing(_) | Generator::Musician(_) | Generator::Unchanged => None,
        }
    }
}
