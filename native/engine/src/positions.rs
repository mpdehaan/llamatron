// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Arithmetic on the positions a clip lists (the Python engine/clips/positions.py): cutting positions to a length and taking
//! pieces out of them, which sections, repeats and generators need.

use crate::sound::{NoteSound, Sound};
use llamatron_math::Rational;

/// A position that lasts no longer than a length.
pub fn cut_position(position: &Sound, length: Rational) -> Sound {
    if position.place() <= length {
        return position.clone();
    }
    match position {
        Sound::Chord { notes, .. } => Sound::chord(notes.iter().map(|note| cut_note(note, length)).collect()),
        other => other.with_length(Some(length)),
    }
}

fn cut_note(note: &NoteSound, length: Rational) -> NoteSound {
    if note.length.is_some_and(|own| own <= length) {
        return *note;
    }
    NoteSound { length: Some(length), ..*note }
}

/// Positions that last exactly a length, cutting notes off or adding a final rest.
pub fn fit_to_length(positions: &[Sound], length: Rational) -> Vec<Sound> {
    let mut result = Vec::new();
    let mut remaining = length;
    for position in positions {
        if remaining <= Rational::ZERO {
            break;
        }
        result.push(cut_position(position, remaining));
        remaining = remaining - position.place().min(remaining);
    }
    if remaining > Rational::ZERO {
        result.push(Sound::Rest(remaining));
    }
    result
}

/// The part of a position that starts offset into it and lasts length; the whole position is the position itself.
pub fn piece_of(position: &Sound, offset: Rational, length: Rational) -> Sound {
    let own = position.place();
    if offset == Rational::ZERO && own <= length {
        return position.clone();
    }
    match position {
        Sound::Rest(_) => Sound::Rest(length),
        Sound::Held { .. } | Sound::Phrase { .. } => match sound_from(position, offset) {
            None => Sound::Rest(length),
            Some(Sound::Held { sound, .. }) => Sound::Held {
                length: (own - offset).min(length),
                sound,
            },
            Some(Sound::Phrase { parts, .. }) => Sound::Phrase {
                length: (own - offset).min(length),
                parts,
            },
            Some(_) => Sound::Rest(length),
        },
        Sound::Chord { notes, .. } => {
            let pieces: Vec<NoteSound> = notes
                .iter()
                .filter(|note| offset < note.length.unwrap_or(Rational::ZERO))
                .map(|note| note_piece(note, offset, length))
                .collect();
            if pieces.is_empty() {
                return Sound::Rest(length);
            }
            Sound::chord(pieces)
        }
        other => other.with_length(Some((own - offset).min(length))),
    }
}

fn note_piece(note: &NoteSound, offset: Rational, length: Rational) -> NoteSound {
    let own = note.length.unwrap_or(Rational::ZERO);
    if offset == Rational::ZERO && own <= length {
        return *note;
    }
    NoteSound {
        length: Some((own - offset).min(length)),
        ..*note
    }
}

/// What is left of a held sound or phrase from offset into it, with its length still the held place's, or None if it's over.
pub fn sound_from(held: &Sound, offset: Rational) -> Option<Sound> {
    match held {
        Sound::Held { length, sound } => {
            let longest = notes_of(sound)
                .iter()
                .map(|note| note.length.unwrap_or(Rational::ZERO))
                .filter(|own| offset < *own)
                .max()?;
            let piece = piece_of(sound, offset, longest - offset);
            if piece.is_rest() {
                return None;
            }
            Some(Sound::Held {
                length: *length,
                sound: Box::new(piece),
            })
        }
        Sound::Phrase { length, parts } => {
            let mut kept = Vec::new();
            let mut start = Rational::ZERO;
            for part in parts {
                let end = start + part.place();
                if offset < end {
                    if offset > start {
                        kept.push(piece_of(part, offset - start, end - offset));
                    } else {
                        kept.push(part.clone());
                    }
                }
                start = end;
            }
            if kept.is_empty() {
                return None;
            }
            Some(Sound::Phrase { length: *length, parts: kept })
        }
        _ => None,
    }
}

/// The notes of a note or chord.
pub fn notes_of(sound: &Sound) -> Vec<NoteSound> {
    match sound {
        Sound::Note(note) => vec![*note],
        Sound::Chord { notes, .. } => notes.clone(),
        _ => Vec::new(),
    }
}
