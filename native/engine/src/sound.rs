// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What a clip plays, as the render makes it (the Python model/values/sound.py and math/length.py): a rest, a note, a chord,
//! a degree, a sound held past its place, or a phrase of sounds played one after another from a held place. Every sound has
//! a length, the time until the next position of the clip starts, exact, or none for one that takes the clip's note length.
//! A chord's length is its longest note's.

use llamatron_math::{Number, Rational};
use llamatron_model::fundamentals::generated::intervals::HALF_STEPS_PER_OCTAVE;
use llamatron_model::schema::generated::midi::{MAX_MIDI_NUMBER, MIN_MIDI_NUMBER};
use llamatron_model::values::generated::note::{FLAT_NAMES, FLAT_SIGN, SHARP_NAMES};

/// The finest a float length is taken to: the nearest millionth of a whole note.
pub const FINEST_LENGTH: i128 = 1_000_000;

/// A number as an exact length: a rational or whole number as it is, a float, or a rational finer than a millionth, as the
/// nearest length no finer than FINEST_LENGTH, so that three twelfths make a quarter (the Python's Length.exact).
pub fn exact_length(value: Number) -> Rational {
    match value {
        Number::Exact(rational) if rational.denominator() <= FINEST_LENGTH => rational,
        Number::Whole(whole) => Rational::whole(whole),
        other => other.to_rational().limit_denominator(FINEST_LENGTH),
    }
}

/// A note's own parts.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct NoteSound {
    pub length: Option<Rational>,
    pub midi: i64,
    pub velocity: Option<i64>,
    pub glide: bool,
    pub name: &'static str,
}

#[derive(Clone, Debug, PartialEq)]
pub enum Sound {
    Rest(Rational),
    Note(NoteSound),
    Chord {
        length: Option<Rational>,
        notes: Vec<NoteSound>,
    },
    Degree {
        length: Option<Rational>,
        number: i64,
        octave: i64,
        scale_notes: i64,
        half_steps: i64,
    },
    Held {
        length: Rational,
        sound: Box<Sound>,
    },
    Phrase {
        length: Rational,
        parts: Vec<Sound>,
    },
}

impl Sound {
    /// A chord of notes, as long as its longest note, or of no length where any note has none.
    pub fn chord(notes: Vec<NoteSound>) -> Sound {
        let mut length: Option<Rational> = None;
        for note in &notes {
            let Some(own) = note.length else {
                length = None;
                break;
            };
            if length.is_none_or(|longest| longest < own) {
                length = Some(own);
            }
        }
        Sound::Chord { length, notes }
    }

    /// How long until the next position starts, or none for a sound that takes the clip's note length.
    pub fn length(&self) -> Option<Rational> {
        match self {
            Sound::Rest(length) => Some(*length),
            Sound::Note(note) => note.length,
            Sound::Chord { length, .. } | Sound::Degree { length, .. } => *length,
            Sound::Held { length, .. } | Sound::Phrase { length, .. } => Some(*length),
        }
    }

    /// The same sound with another length; a held sound and a phrase keep sounding as they did.
    pub fn with_length(&self, length: Option<Rational>) -> Sound {
        match self {
            Sound::Rest(_) => Sound::Rest(length.unwrap_or(Rational::ZERO)),
            Sound::Note(note) => Sound::Note(NoteSound { length, ..*note }),
            Sound::Chord { notes, .. } => Sound::Chord { length, notes: notes.clone() },
            Sound::Degree {
                number,
                octave,
                scale_notes,
                half_steps,
                ..
            } => Sound::Degree {
                length,
                number: *number,
                octave: *octave,
                scale_notes: *scale_notes,
                half_steps: *half_steps,
            },
            Sound::Held { sound, .. } => Sound::Held {
                length: length.unwrap_or(Rational::ZERO),
                sound: sound.clone(),
            },
            Sound::Phrase { parts, .. } => Sound::Phrase {
                length: length.unwrap_or(Rational::ZERO),
                parts: parts.clone(),
            },
        }
    }

    /// A note or chord with every note in it lasting a length.
    pub fn lasting(&self, length: Option<Rational>) -> Sound {
        match self {
            Sound::Chord { notes, .. } => Sound::Chord {
                length,
                notes: notes.iter().map(|note| NoteSound { length, ..*note }).collect(),
            },
            other => other.with_length(length),
        }
    }
}

impl NoteSound {
    /// The note moved a number of half steps, spelled with flats if its name has one and with sharps otherwise; None outside
    /// the MIDI range, where the Python raises.
    pub fn half_step(&self, steps: i64) -> Option<NoteSound> {
        let midi = self.midi + steps;
        if !(MIN_MIDI_NUMBER..=MAX_MIDI_NUMBER).contains(&midi) {
            return None;
        }
        let names = if self.name.ends_with(FLAT_SIGN) { FLAT_NAMES } else { SHARP_NAMES };
        Some(NoteSound {
            midi,
            name: names[midi.rem_euclid(HALF_STEPS_PER_OCTAVE) as usize],
            ..*self
        })
    }
}
