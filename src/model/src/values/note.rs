// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Notes, rests and degrees (the Python model/values/note.py): the immutable sounds a clip is made of.
//!
//! A note is a spelled pitch, `C#4`, with a length in whole notes or none (the clip's note length then applies), a velocity
//! or none, and whether it glides into the next; enharmonic spellings compare equal, as do notes whatever their velocity or
//! glide, by their MIDI number and length alone. A degree is a place in whatever scale applies when it is played.

use crate::fundamentals::generated::intervals::HALF_STEPS_PER_OCTAVE;
use crate::schema::generated::midi::{MAX_MIDI_NUMBER, MAX_VELOCITY, MIN_MIDI_NUMBER, MIN_VELOCITY};
use crate::values::generated::note::{FIRST_DEGREE, FLAT_NAMES, FLAT_SIGN, MAX_OCTAVE, MIN_OCTAVE, SEMITONES_ABOVE_C, SHARP_NAMES};
use crate::ValueError;
use llamatron_math::Number;
use llamatron_names::file_format;
use llamatron_names::fill;
use llamatron_names::spec;
use llamatron_names::words;
use llamatron_strings::errors;
use llamatron_strings::{named, Value};

/// A number as Python's repr writes it, for a message.
pub fn number_value(number: &Number) -> Value {
    match number {
        Number::Whole(whole) => Value::Whole(*whole as i64),
        Number::Float(float) => Value::Float(*float),
        Number::Exact(rational) => Value::Text(format!("Rational({}, {})", rational.numerator(), rational.denominator())),
    }
}

/// Check that a length is a finite number of whole notes above zero.
pub fn checked_length(length: Number) -> Result<Number, ValueError> {
    if length.is_finite() && length > Number::Whole(0) {
        return Ok(length);
    }
    Err(ValueError(named(errors::ERR_BAD_LENGTH, &[(fill::VALUE, number_value(&length))])))
}

/// The half steps a spelling is above C, or None for a name the program does not know.
pub fn semitones_above_c(name: &str) -> Option<i64> {
    SEMITONES_ABOVE_C.iter().find(|(known, _)| *known == name).map(|(_, semitones)| *semitones)
}

/// The static spelling a name is, so that a note holds no text of its own.
fn known_name(name: &str) -> Option<&'static str> {
    SEMITONES_ABOVE_C.iter().find(|(known, _)| *known == name).map(|(known, _)| *known)
}

/// A silence of a length.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Rest {
    length: Number,
}

impl Rest {
    pub fn new(length: Number) -> Result<Rest, ValueError> {
        Ok(Rest {
            length: checked_length(length)?,
        })
    }

    pub fn get_length(&self) -> Number {
        self.length
    }
}

/// A place in whichever scale applies when it is played: numbered from 1, the root, past the top of the scale, moved by
/// octaves, scale notes and half steps, and with a length or none.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Degree {
    number: i64,
    length: Option<Number>,
    octave: i64,
    scale_notes: i64,
    half_steps: i64,
}

impl Degree {
    pub fn new(number: i64, length: Option<Number>, octave: i64, scale_notes: i64, half_steps: i64) -> Result<Degree, ValueError> {
        if number < FIRST_DEGREE {
            return Err(ValueError(named(
                errors::ERR_BAD_DEGREE,
                &[(file_format::StatementPart::VALUE, number.into()), (spec::LOWEST, FIRST_DEGREE.into())],
            )));
        }
        let length = length.map(checked_length).transpose()?;
        Ok(Degree {
            number,
            length,
            octave,
            scale_notes,
            half_steps,
        })
    }

    pub fn get_number(&self) -> i64 {
        self.number
    }

    pub fn get_length(&self) -> Option<Number> {
        self.length
    }

    pub fn get_octave(&self) -> i64 {
        self.octave
    }

    pub fn get_scale_notes(&self) -> i64 {
        self.scale_notes
    }

    pub fn get_half_steps(&self) -> i64 {
        self.half_steps
    }

    pub fn with_length(&self, length: Option<Number>) -> Result<Degree, ValueError> {
        Degree::new(self.number, length, self.octave, self.scale_notes, self.half_steps)
    }

    /// The note this degree plays in a scale, spelled as the root spells its half steps.
    pub fn to_note(&self, scale: &crate::values::scale::Scale) -> Result<Note, ValueError> {
        scale.note_at(
            self.number,
            self.scale_notes,
            self.octave * HALF_STEPS_PER_OCTAVE + self.half_steps,
            self.length,
            None,
            false,
        )
    }
}

/// A spelled pitch with a length, a velocity and a glide.
#[derive(Clone, Copy, Debug)]
pub struct Note {
    name: &'static str,
    octave_number: i64,
    length: Option<Number>,
    velocity: Option<i64>,
    glide: bool,
    midi_number: i64,
}

impl PartialEq for Note {
    /// By pitch and length alone, as Python's Note compares.
    fn eq(&self, other: &Note) -> bool {
        self.midi_number == other.midi_number && self.length == other.length
    }
}

fn checked_velocity(velocity: Option<i64>) -> Result<Option<i64>, ValueError> {
    match velocity {
        Some(value) if !(MIN_VELOCITY..=MAX_VELOCITY).contains(&value) => Err(ValueError(named(
            errors::ERR_BAD_VELOCITY,
            &[
                (file_format::StatementPart::VALUE, value.into()),
                (spec::LOWEST, MIN_VELOCITY.into()),
                (spec::HIGHEST, MAX_VELOCITY.into()),
            ],
        ))),
        _ => Ok(velocity),
    }
}

impl Note {
    pub fn new(name: &str, octave_number: i64, length: Option<Number>, velocity: Option<i64>, glide: bool) -> Result<Note, ValueError> {
        let length = length.map(checked_length).transpose()?;
        let velocity = checked_velocity(velocity)?;
        let Some(name) = known_name(name) else {
            return Err(ValueError(named(errors::ERR_BAD_NOTE_NAME, &[(fill::VALUE, name.into())])));
        };
        if !(MIN_OCTAVE..=MAX_OCTAVE).contains(&octave_number) {
            return Err(ValueError(named(
                errors::ERR_NOTE_BAD_OCTAVE,
                &[
                    (file_format::StatementPart::VALUE, octave_number.into()),
                    (spec::LOWEST, MIN_OCTAVE.into()),
                    (spec::HIGHEST, MAX_OCTAVE.into()),
                ],
            )));
        }
        let midi_number = octave_number * HALF_STEPS_PER_OCTAVE + semitones_above_c(name).unwrap_or(0);
        if !(MIN_MIDI_NUMBER..=MAX_MIDI_NUMBER).contains(&midi_number) {
            return Err(ValueError(named(
                errors::ERR_OUTSIDE_MIDI,
                &[
                    (file_format::FileLayout::NAME, name.into()),
                    (file_format::Row::OCTAVE, octave_number.into()),
                    (words::NUMBER, midi_number.into()),
                ],
            )));
        }
        Ok(Note {
            name,
            octave_number,
            length,
            velocity,
            glide,
            midi_number,
        })
    }

    /// The note of a MIDI number, spelled with sharps, or flats where asked.
    pub fn of_midi(midi_number: i64, flats: bool, length: Option<Number>) -> Result<Note, ValueError> {
        let names = if flats { FLAT_NAMES } else { SHARP_NAMES };
        let octave = midi_number.div_euclid(HALF_STEPS_PER_OCTAVE);
        Note::new(names[midi_number.rem_euclid(HALF_STEPS_PER_OCTAVE) as usize], octave, length, None, false)
    }

    pub fn get_name(&self) -> &'static str {
        self.name
    }

    pub fn get_octave_number(&self) -> i64 {
        self.octave_number
    }

    pub fn get_length(&self) -> Option<Number> {
        self.length
    }

    pub fn get_velocity(&self) -> Option<i64> {
        self.velocity
    }

    pub fn get_glide(&self) -> bool {
        self.glide
    }

    pub fn get_midi_number(&self) -> i64 {
        self.midi_number
    }

    /// The name and octave of the note some half steps away, spelled with flats if this note's name has one, else sharps.
    pub fn spelled_half_step(&self, steps: i64) -> (&'static str, i64) {
        let names = if self.name.ends_with(FLAT_SIGN) { FLAT_NAMES } else { SHARP_NAMES };
        let moved = self.midi_number + steps;
        (names[moved.rem_euclid(HALF_STEPS_PER_OCTAVE) as usize], moved.div_euclid(HALF_STEPS_PER_OCTAVE))
    }

    /// The note some half steps higher, or lower for a negative count, spelled as spelled_half_step spells it.
    pub fn half_step(&self, steps: i64) -> Result<Note, ValueError> {
        let (name, octave_number) = self.spelled_half_step(steps);
        let midi_number = self.midi_number + steps;
        if !(MIN_MIDI_NUMBER..=MAX_MIDI_NUMBER).contains(&midi_number) {
            return Note::new(name, octave_number, self.length, self.velocity, self.glide);
        }
        Ok(Note {
            name,
            octave_number,
            midi_number,
            ..*self
        })
    }

    pub fn with_length(&self, length: Option<Number>) -> Result<Note, ValueError> {
        Ok(Note {
            length: length.map(checked_length).transpose()?,
            ..*self
        })
    }

    pub fn with_velocity(&self, velocity: Option<i64>) -> Result<Note, ValueError> {
        Ok(Note {
            velocity: checked_velocity(velocity)?,
            ..*self
        })
    }

    pub fn with_glide(&self) -> Note {
        Note { glide: true, ..*self }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_note_keeps_its_spelling_and_steps_in_its_own_accidentals() {
        let d_flat = Note::new("Db", 4, None, None, false).unwrap();
        assert_eq!(d_flat.get_midi_number(), 49);
        assert_eq!(d_flat.half_step(2).unwrap().get_name(), "Eb");
        assert_eq!(Note::new("C#", 4, None, None, false).unwrap(), d_flat);
        let b_sharp = Note::new("B#", 3, None, None, false).unwrap();
        assert_eq!(b_sharp.get_midi_number(), 48);
        assert!(Note::new("H", 4, None, None, false).is_err());
        assert!(Rest::new(Number::Whole(0)).is_err());
    }
}
