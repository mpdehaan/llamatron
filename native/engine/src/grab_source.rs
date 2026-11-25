// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What a track has played, for another track's grab steps to take notes from, as a step sequencer's note grab does (the Python
//! engine/realizer/grab_source.py): the note each position of a finished clip starts, a chord's its root, its first note as
//! built, by when it starts on the grid.

use crate::clip::Clip;
use crate::error::{RenderError, Rendered};
use crate::sound::{scale_sound, Sound};
use llamatron_math::Rational;
use llamatron_model::values::scale::Scale;

pub struct GrabSource {
    onsets: Vec<(Rational, i64)>,
}

impl GrabSource {
    pub fn of(clip: &Clip) -> Rendered<GrabSource> {
        let end = clip.total_length()?;
        let mut onsets = Vec::new();
        let mut start = Rational::ZERO;
        for sound in clip.resolved_sounds()? {
            place_root(&sound, start, end, clip.scale.as_ref(), &mut onsets)?;
            start = start + sound.place();
        }
        onsets.sort_by_key(|(time, _)| *time);
        Ok(GrabSource { onsets })
    }

    /// The MIDI number of the note most recently started at or before a time, or None before the first.
    pub fn note_at(&self, time: Rational) -> Option<i64> {
        let started = self.onsets.partition_point(|(start, _)| *start <= time);
        (started > 0).then(|| self.onsets[started - 1].1)
    }
}

fn place_root(sound: &Sound, start: Rational, end: Rational, scale: Option<&Scale>, onsets: &mut Vec<(Rational, i64)>) -> Rendered<()> {
    match sound {
        Sound::Held { sound, .. } => place_root(sound, start, end, scale, onsets),
        Sound::Phrase { parts, .. } => {
            let mut start = start;
            for part in parts {
                place_root(part, start, end, scale, onsets)?;
                start = start + part.place();
            }
            Ok(())
        }
        Sound::Rest(_) => Ok(()),
        other => {
            if start < end && !onsets.iter().any(|(time, _)| *time == start) {
                onsets.push((start, root(other, scale)?));
            }
            Ok(())
        }
    }
}

fn root(sound: &Sound, scale: Option<&Scale>) -> Rendered<i64> {
    match sound {
        Sound::Note(note) => Ok(note.midi),
        Sound::Chord { notes, .. } => Ok(notes.first().map(|note| note.midi).unwrap_or(0)),
        Sound::Degree {
            number,
            octave,
            scale_notes,
            half_steps,
            ..
        } => {
            let scale = scale.ok_or_else(|| RenderError::Refused(format!("degree {number} needs a scale")))?;
            scale_sound(scale, *number, *scale_notes, octave * 12 + half_steps, None, None, false)
                .map(|note| note.midi)
                .map_err(|problem| RenderError::Refused(problem.0))
        }
        _ => Ok(0),
    }
}
