// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The chords a finished clip plays, by when each starts, which a Follow Chords reads from the track it follows (the Python
//! engine/realizer/chord_source.py).

use crate::clip::Clip;
use crate::error::{RenderError, Rendered};
use crate::sound::{scale_sound, Sound};
use llamatron_math::Rational;
use llamatron_model::values::scale::Scale;

/// A chord as a follower hears it: its root's MIDI number, and its notes within an octave.
pub type HeardChord = (i64, Vec<i64>);

pub struct ChordSource {
    chords: Vec<(Rational, HeardChord)>,
}

impl ChordSource {
    /// The chords a clip starts, each note or chord a chord of its first note and its notes, the first at each time kept.
    pub fn of(clip: &Clip) -> Rendered<ChordSource> {
        let sounds = clip.resolved_sounds()?;
        let end = clip.total_length()?;
        let mut chords: Vec<(Rational, HeardChord)> = Vec::new();
        let mut start = Rational::ZERO;
        for sound in &sounds {
            place_chord(sound, start, end, clip.scale.as_ref(), &mut chords)?;
            start = start + sound.place();
        }
        chords.sort_by_key(|(time, _)| *time);
        Ok(ChordSource { chords })
    }

    /// The chord most recently started at or before a time, or None before the first; a chord goes on through the rests after it.
    pub fn chord_at(&self, time: Rational) -> Option<&HeardChord> {
        let started = self.chords.partition_point(|(start, _)| *start <= time);
        (started > 0).then(|| &self.chords[started - 1].1)
    }
}

fn place_chord(sound: &Sound, start: Rational, end: Rational, scale: Option<&Scale>, chords: &mut Vec<(Rational, HeardChord)>) -> Rendered<()> {
    match sound {
        Sound::Held { sound, .. } => place_chord(sound, start, end, scale, chords),
        Sound::Phrase { parts, .. } => {
            let mut start = start;
            for part in parts {
                place_chord(part, start, end, scale, chords)?;
                start = start + part.place();
            }
            Ok(())
        }
        Sound::Rest(_) => Ok(()),
        other => {
            if start < end && !chords.iter().any(|(time, _)| *time == start) {
                chords.push((start, chord_of(other, scale)?));
            }
            Ok(())
        }
    }
}

fn chord_of(sound: &Sound, scale: Option<&Scale>) -> Rendered<HeardChord> {
    let numbers: Vec<i64> = match sound {
        Sound::Note(note) => vec![note.midi],
        Sound::Chord { notes, .. } => notes.iter().map(|note| note.midi).collect(),
        Sound::Degree {
            number,
            octave,
            scale_notes,
            half_steps,
            ..
        } => {
            let scale = scale.ok_or_else(|| RenderError::Refused(format!("degree {number} needs a scale")))?;
            let note =
                scale_sound(scale, *number, *scale_notes, octave * 12 + half_steps, None, None, false).map_err(|problem| RenderError::Refused(problem.0))?;
            vec![note.midi]
        }
        _ => Vec::new(),
    };
    let mut within: Vec<i64> = numbers.iter().map(|number| number.rem_euclid(12)).collect();
    within.sort();
    within.dedup();
    Ok((numbers.first().copied().unwrap_or(0), within))
}
