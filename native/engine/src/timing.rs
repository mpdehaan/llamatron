// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A clip's notes as they play (the Python engine/timing/timing.py, clip_ticks.py and sounding.py): when each starts and ends,
//! in whole notes from the clip's start, its MIDI number and velocity. This is where a degree finally becomes a note. A note
//! that glides into a different one runs on into it a little, and every note is cut at the clip's end.

use crate::clip::Clip;
use crate::error::{RenderError, Rendered};
use crate::sound::{scale_sound, NoteSound, Sound};
use llamatron_math::Rational;
use llamatron_model::schema::generated::midi::MAX_VELOCITY;
use llamatron_model::values::scale::Scale;

/// How far a gliding note runs on into the next.
fn glide_overlap() -> Rational {
    Rational::new(1, 128)
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct NoteEvent {
    pub start: Rational,
    pub end: Rational,
    pub midi_number: i64,
    pub velocity: i64,
}

/// A clip's notes as NoteEvents, and the clip's total length.
pub fn timed_events(clip: &Clip, scale: Option<&Scale>) -> Rendered<(Vec<NoteEvent>, Rational)> {
    let positions = clip.resolved_sounds()?;
    let clip_length = match clip.length {
        Some(length) => length,
        None => positions.iter().fold(Rational::ZERO, |total, position| total + position.place()),
    };
    let mut slots = Vec::new();
    let mut start = Rational::ZERO;
    for position in &positions {
        place(position, start, scale, &mut slots)?;
        start = start + position.place();
    }
    // A stable sort keeps positions that start together in the clip's order.
    slots.sort_by_key(|(start, _)| *start);
    let mut timed = Vec::new();
    for (place, (slot_start, notes)) in slots.iter().enumerate() {
        if notes.is_empty() {
            continue;
        }
        let following = slots.get(place + 1).map(|(_, notes)| notes.as_slice()).unwrap_or(&[]);
        // The clip's groove moves each note's start and keeps its gate, so that a delayed note ends later too.
        let mut onset = match &clip.groove {
            Some(groove) => groove.moved(*slot_start),
            None => *slot_start,
        };
        // A clip's rushes and drags move its notes on top of the groove, never before the clip's start.
        if let Some(nudge) = &clip.nudge {
            onset = (onset + nudge.moved(*slot_start)).max(Rational::ZERO);
        }
        let start = onset.min(clip_length);
        for (midi_number, note) in notes {
            let mut end = onset + note.length.unwrap_or(Rational::ZERO);
            if note.glide && !following.is_empty() && !following.iter().any(|(midi, _)| midi == midi_number) {
                end = end + glide_overlap();
            }
            let end = end.min(clip_length);
            if end > start {
                timed.push(NoteEvent {
                    start,
                    end,
                    midi_number: *midi_number,
                    velocity: note.velocity.unwrap_or(MAX_VELOCITY),
                });
            }
        }
    }
    Ok((timed, clip_length))
}

type Slot = (Rational, Vec<(i64, NoteSound)>);

/// Add the slots a position sounds from a start, everything a held sound holds included.
fn place(position: &Sound, start: Rational, scale: Option<&Scale>, slots: &mut Vec<Slot>) -> Rendered<()> {
    match position {
        Sound::Held { sound, .. } => place(sound, start, scale, slots),
        Sound::Phrase { parts, .. } => {
            let mut start = start;
            for part in parts {
                place(part, start, scale, slots)?;
                start = start + part.place();
            }
            Ok(())
        }
        other => {
            slots.push((start, sounding_notes(&settled(other, scale)?)));
            Ok(())
        }
    }
}

/// A degree as the note its scale plays; anything else as it is.
fn settled(position: &Sound, scale: Option<&Scale>) -> Rendered<Sound> {
    let Sound::Degree {
        length,
        number,
        octave,
        scale_notes,
        half_steps,
    } = position
    else {
        return Ok(position.clone());
    };
    let scale = scale.ok_or_else(|| RenderError::Refused(format!("degree {number} needs a scale")))?;
    let note = scale_sound(scale, *number, *scale_notes, octave * 12 + half_steps, *length, None, false).map_err(|problem| RenderError::Refused(problem.0))?;
    Ok(Sound::Note(note))
}

/// The notes one position sounds by MIDI number, in the order it holds them, keeping the longest of any pitch in the place of
/// its first.
fn sounding_notes(position: &Sound) -> Vec<(i64, NoteSound)> {
    match position {
        Sound::Note(note) => vec![(note.midi, *note)],
        Sound::Chord { notes, .. } => {
            let mut found: Vec<(i64, NoteSound)> = Vec::new();
            for note in notes {
                match found.iter_mut().find(|(midi, _)| *midi == note.midi) {
                    Some(kept) if kept.1.length < note.length => kept.1 = *note,
                    Some(_) => {}
                    None => found.push((note.midi, *note)),
                }
            }
            found
        }
        _ => Vec::new(),
    }
}
