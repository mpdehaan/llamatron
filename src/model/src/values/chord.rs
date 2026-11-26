// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Chords and the chord types llamatron names (the Python model/values/chord.py): a chord is notes sounded together, equal to
//! another of the same pitches and lengths in any order; a chord type is a shape, its notes above the root in half steps.

use crate::fundamentals::generated::enums::CHORD_TYPES;
use crate::values::note::Note;
use crate::ValueError;
use llamatron_math::Number;
use llamatron_strings::errors;

/// A chord type by the name of the member it is, an alias such as a second name for one shape read as that member.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct ChordType {
    name: &'static str,
    shape: &'static [i64],
}

impl ChordType {
    /// The chord type a member's name names, as Python's ChordType[name] finds it, aliases leading to their member.
    pub fn named(name: &str) -> Option<ChordType> {
        let (_, member, shape) = CHORD_TYPES.iter().find(|(known, _, _)| *known == name)?;
        Some(ChordType { name: member, shape })
    }

    /// Every chord type, in the order Python lists its members, aliases left out.
    pub fn all() -> Vec<ChordType> {
        CHORD_TYPES
            .iter()
            .filter(|(name, member, _)| name == member)
            .map(|(_, member, shape)| ChordType { name: member, shape })
            .collect()
    }

    pub fn get_name(&self) -> &'static str {
        self.name
    }

    pub fn get_shape(&self) -> &'static [i64] {
        self.shape
    }
}

#[derive(Clone, Debug)]
pub struct Chord {
    notes: Vec<Note>,
}

impl Chord {
    pub fn new(notes: Vec<Note>) -> Result<Chord, ValueError> {
        if notes.is_empty() {
            return Err(ValueError(errors::ERR_NO_NOTES.to_string()));
        }
        Ok(Chord { notes })
    }

    /// A chord of a type on a root, the root keeping its spelling and the others spelled as half_step spells them.
    pub fn of_type(root: &Note, kind: ChordType) -> Result<Chord, ValueError> {
        let mut notes = vec![*root];
        for steps in kind.get_shape() {
            notes.push(root.half_step(*steps)?);
        }
        Chord::new(notes)
    }

    /// The notes, in the order the chord was built in.
    pub fn get_notes(&self) -> &[Note] {
        &self.notes
    }

    /// The longest note's length, or None if any note has none yet.
    pub fn get_length(&self) -> Option<Number> {
        let mut longest: Option<Number> = None;
        for note in &self.notes {
            let length = note.get_length()?;
            if longest.is_none_or(|most| length > most) {
                longest = Some(length);
            }
        }
        longest
    }

    fn sorted_pitches_and_lengths(&self) -> Vec<(i64, bool, llamatron_math::Rational)> {
        let mut ordered: Vec<(i64, bool, llamatron_math::Rational)> = self
            .notes
            .iter()
            .map(|note| {
                (
                    note.get_midi_number(),
                    note.get_length().is_none(),
                    note.get_length().map(|length| length.to_rational()).unwrap_or_default(),
                )
            })
            .collect();
        ordered.sort();
        ordered
    }
}

impl PartialEq for Chord {
    fn eq(&self, other: &Chord) -> bool {
        self.sorted_pitches_and_lengths() == other.sorted_pitches_and_lengths()
    }
}
