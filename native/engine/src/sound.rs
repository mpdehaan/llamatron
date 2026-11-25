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
use llamatron_model::values::generated::note::{FLAT_NAMES, FLAT_SIGN, MAX_OCTAVE, MIN_OCTAVE, NOTE_NAMES, SHARP_NAMES};
use llamatron_model::values::note::semitones_above_c;
use llamatron_model::values::note::Note;

/// A note that would leave the MIDI range or the octaves, which the Python raises as a ValueError and a caller may catch.
#[derive(Clone, Debug, PartialEq)]
pub struct OutOfRange(pub String);

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
    /// The note a name and an octave spell, or what a Note says is wrong with one outside the octaves or the MIDI range.
    pub fn named_note(name: &str, octave: i64, length: Option<Rational>, velocity: Option<i64>, glide: bool) -> Result<NoteSound, OutOfRange> {
        let semitones = semitones_above_c(name).ok_or_else(|| OutOfRange(format!("no note called {name}")))?;
        let midi = octave * HALF_STEPS_PER_OCTAVE + semitones;
        if (MIN_OCTAVE..=MAX_OCTAVE).contains(&octave) && (MIN_MIDI_NUMBER..=MAX_MIDI_NUMBER).contains(&midi) {
            return Ok(NoteSound {
                length,
                midi,
                velocity,
                glide,
                name: spelled(name),
            });
        }
        let refusal = Note::new(name, octave, None, velocity, glide)
            .err()
            .map(|problem| problem.0)
            .unwrap_or_default();
        Err(OutOfRange(refusal))
    }

    /// A chord of a root and the notes some half steps above it, or what is wrong where one leaves the MIDI range.
    pub fn chord_above(root: NoteSound, half_steps: &[i64]) -> Result<Sound, OutOfRange> {
        let mut notes = vec![root];
        for above in half_steps {
            notes.push(
                root.half_step(*above)
                    .ok_or_else(|| OutOfRange(format!("a note {above} half steps above {} leaves the MIDI range", root.midi)))?,
            );
        }
        Ok(Sound::chord(notes))
    }

    /// A note, chord or degree held past its place: the next position starts after length while the sound lasts its own.
    pub fn held(sound: Sound, length: Rational) -> Sound {
        Sound::Held {
            length,
            sound: Box::new(sound),
        }
    }

    /// Sounds played one after another from a held place, while the next position starts after length.
    pub fn phrase(parts: Vec<Sound>, length: Rational) -> Sound {
        Sound::Phrase { length, parts }
    }

    pub fn is_rest(&self) -> bool {
        matches!(self, Sound::Rest(_))
    }

    /// The length a render's sound always has.
    pub fn place(&self) -> Rational {
        self.length().unwrap_or(Rational::ZERO)
    }

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

/// A note name as one of the names the program spells with, for a sound to keep.
fn spelled(name: &str) -> &'static str {
    NOTE_NAMES.iter().copied().find(|known| *known == name).unwrap_or("C")
}

/// The note a degree of a scale plays, as the render makes it (the Python Scale.sound_at): its root's MIDI number, moved by
/// the scale's steps, some scale notes and half steps, spelled with flats where the root is; or what is wrong with a note
/// outside the MIDI range.
pub fn scale_sound(
    scale: &llamatron_model::values::scale::Scale,
    degree: i64,
    scale_notes: i64,
    half_steps: i64,
    length: Option<Rational>,
    velocity: Option<i64>,
    glide: bool,
) -> Result<NoteSound, OutOfRange> {
    let steps = scale.get_type().get_shape();
    let size = steps.len() as i64;
    let moved = degree - llamatron_model::values::generated::note::FIRST_DEGREE + scale_notes;
    let (octaves, index) = (moved.div_euclid(size), moved.rem_euclid(size));
    let root = scale.get_root();
    let midi = root.get_midi_number() + octaves * HALF_STEPS_PER_OCTAVE + steps[index as usize] + half_steps;
    if !(MIN_MIDI_NUMBER..=MAX_MIDI_NUMBER).contains(&midi) {
        return Err(OutOfRange(format!("degree {degree} of the scale leaves the MIDI range")));
    }
    let names = if root.get_name().ends_with(FLAT_SIGN) { FLAT_NAMES } else { SHARP_NAMES };
    Ok(NoteSound {
        length,
        midi,
        velocity,
        glide,
        name: names[midi.rem_euclid(HALF_STEPS_PER_OCTAVE) as usize],
    })
}
