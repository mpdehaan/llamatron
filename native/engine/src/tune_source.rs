// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! When a finished clip sounds, which a musician reads from the track that carries the tune, to play round it (the Python
//! engine/realizer/tune_source.py): each stretch from when a note starts to when it stops, a held one past its place.

use crate::clip::Clip;
use crate::error::Rendered;
use crate::sound::Sound;
use llamatron_math::Rational;

pub struct TuneSource {
    stretches: Vec<(Rational, Rational)>,
}

impl TuneSource {
    pub fn of(clip: &Clip) -> Rendered<TuneSource> {
        let mut stretches = Vec::new();
        let mut start = Rational::ZERO;
        for sound in clip.resolved_sounds()? {
            place_stretch(&sound, start, &mut stretches);
            start = start + sound.place();
        }
        stretches.sort();
        Ok(TuneSource { stretches })
    }

    /// Whether a note of the clip sounds at a time: one has started at or before it and not stopped.
    pub fn sounds_at(&self, time: Rational) -> bool {
        let started = self.stretches.partition_point(|(start, _)| *start <= time);
        started > 0 && time < self.stretches[started - 1].1
    }
}

fn place_stretch(sound: &Sound, start: Rational, stretches: &mut Vec<(Rational, Rational)>) {
    match sound {
        Sound::Held { sound, .. } => place_stretch(sound, start, stretches),
        Sound::Phrase { parts, .. } => {
            let mut start = start;
            for part in parts {
                place_stretch(part, start, stretches);
                start = start + part.place();
            }
        }
        Sound::Rest(_) => {}
        other => stretches.push((start, start + other.place())),
    }
}
