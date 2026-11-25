// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! What a place in a clip holds (the Python model/values/held.py and the kinds a clip's positions take): a note, a chord, a
//! rest, a degree, or a held sound, which starts here and lasts its own length while the next place starts after its
//! length; a held sound is a note, a chord, a degree or a phrase of places played one after another.

use crate::values::chord::Chord;
use crate::values::note::{checked_length, Degree, Note, Rest};
use crate::ValueError;
use llamatron_math::Number;

#[derive(Clone, Debug, PartialEq)]
pub enum Position {
    Note(Note),
    Chord(Chord),
    Rest(Rest),
    Degree(Degree),
    Held(Box<Held>),
}

#[derive(Clone, Debug, PartialEq)]
pub enum HeldSound {
    Note(Note),
    Chord(Chord),
    Degree(Degree),
    Phrase(Vec<Position>),
}

#[derive(Clone, Debug, PartialEq)]
pub struct Held {
    sound: HeldSound,
    length: Number,
}

impl Held {
    pub fn new(sound: HeldSound, length: Number) -> Result<Held, ValueError> {
        Ok(Held {
            sound,
            length: checked_length(length)?,
        })
    }

    pub fn get_sound(&self) -> &HeldSound {
        &self.sound
    }

    pub fn get_length(&self) -> Number {
        self.length
    }
}
