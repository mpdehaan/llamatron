// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Scales and the scale types llamatron names (the Python model/values/scale.py): a scale runs upward from its root, and
//! each degree of it plays the note its shape gives, spelled as the root spells its half steps.

use crate::fundamentals::generated::enums::SCALE_TYPES;
use crate::fundamentals::generated::intervals::HALF_STEPS_PER_OCTAVE;
use crate::values::generated::note::FIRST_DEGREE;
use crate::values::note::Note;
use crate::ValueError;
use llamatron_math::Number;
use llamatron_names::file_format;
use llamatron_names::spec;
use llamatron_strings::errors;
use llamatron_strings::named;

/// A scale type, by the member it is.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct ScaleType {
    name: &'static str,
    shape: &'static [i64],
}

impl ScaleType {
    /// The scale type a file's name names, lowercase as a file writes it (`harmonic_minor`), aliases leading to their member.
    pub fn named(name: &str) -> Option<ScaleType> {
        let upper = name.to_ascii_uppercase();
        let (_, member, shape) = SCALE_TYPES.iter().find(|(known, _, _)| *known == upper)?;
        Some(ScaleType { name: member, shape })
    }

    /// Every name a file may write a scale type as, aliases included, in Python's order.
    pub fn file_names() -> Vec<String> {
        SCALE_TYPES.iter().map(|(name, _, _)| name.to_ascii_lowercase()).collect()
    }

    /// The name a file writes, lowercase, the member's own, so that an alias is written as its member.
    pub fn file_name(&self) -> String {
        self.name.to_ascii_lowercase()
    }

    pub fn get_shape(&self) -> &'static [i64] {
        self.shape
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Scale {
    root: Note,
    kind: ScaleType,
}

impl Scale {
    pub fn new(root: Note, kind: ScaleType) -> Scale {
        Scale { root, kind }
    }

    pub fn get_root(&self) -> &Note {
        &self.root
    }

    pub fn get_type(&self) -> ScaleType {
        self.kind
    }

    /// The note a degree of the scale plays, moved scale_notes along the scale and then by half steps.
    pub fn note_at(
        &self,
        degree: i64,
        scale_notes: i64,
        half_steps: i64,
        length: Option<Number>,
        velocity: Option<i64>,
        glide: bool,
    ) -> Result<Note, ValueError> {
        if degree < FIRST_DEGREE {
            return Err(ValueError(named(
                errors::ERR_BAD_DEGREE,
                &[(file_format::StatementPart::VALUE, degree.into()), (spec::LOWEST, FIRST_DEGREE.into())],
            )));
        }
        let shape = self.kind.get_shape();
        let place = degree - FIRST_DEGREE + scale_notes;
        let octaves = place.div_euclid(shape.len() as i64);
        let index = place.rem_euclid(shape.len() as i64) as usize;
        let (name, octave) = self.root.spelled_half_step(octaves * HALF_STEPS_PER_OCTAVE + shape[index] + half_steps);
        Note::new(name, octave, length, velocity, glide)
    }
}
