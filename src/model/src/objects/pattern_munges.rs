// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The munges of a pattern that work on its notes (the Python pattern_munges.py): joining and dividing them, moving them
//! among the rests, changing their pitches and loudness, and shuffling the steps. Each is one edit of the whole pattern, as
//! the pattern editor's Munge dialog offers; the munges that only reorder, copy or blank steps are on Pattern itself.

use super::{blank, Pattern, REST_ROWS};
use crate::file::data::Data;
use crate::schema::checking::InvalidValue;
use crate::schema::generated::file_format::{PATTERN_ROWS, PITCH_ROWS};
use crate::schema::generated::limits::{MAX_OCTAVE, MIN_DEGREE, MIN_OCTAVE, MIN_STEPS};
use crate::schema::generated::midi::{MAX_VELOCITY, MIN_VELOCITY};
use llamatron_math::python_random::PythonRandom;
use llamatron_names::file_format;
use llamatron_strings::{errors, named};
use std::collections::BTreeMap;

/// The rows the munges read and write by name.
const DEGREE: &str = "degree";
const OCTAVE: &str = "octave";
const TIE: &str = "tie";
const GRAB: &str = "grab";
const GATE: &str = "gate";
const DOT: &str = "dot";
const VELOCITY: &str = "velocity";
/// What says how long a note lasts, which a note made of another's steps takes none of.
const LENGTH_ROWS: [&str; 3] = [GATE, DOT, TIE];

impl Pattern {
    /// A step's value on a row, the row's blank where the pattern holds none of it.
    fn held(&self, row: &str, step: usize) -> Data {
        match Self::place_of(row).and_then(|place| self.rows[place].as_ref()) {
            Some(values) => values.get(step).cloned().unwrap_or_else(|| blank(row)),
            None => blank(row),
        }
    }

    /// Put a value on a step with no check, for a value another step of this pattern already held; a blank on a row the
    /// pattern holds none of leaves it so.
    fn hold(&mut self, row: &str, step: usize, value: Data) {
        let unheld = Self::place_of(row).is_some_and(|place| self.rows[place].is_none());
        if unheld && value == blank(row) {
            return;
        }
        if let Some(values) = self.row_mut(row) {
            values[step] = value;
        }
    }

    /// Whether a step's value on a row is on, as Python reads a value as true.
    fn is_on(&self, row: &str, step: usize) -> bool {
        super::truthy(&self.held(row, step))
    }

    /// The rows that make a step's note, which a rest holds none of.
    fn sound_rows() -> impl Iterator<Item = &'static str> {
        PATTERN_ROWS.iter().copied().filter(|row| !REST_ROWS.contains(row))
    }

    /// What a step plays, apart from how long and how loud: its degree, octave, sharp or flat and chord.
    fn pitch(&self, step: usize) -> Vec<Data> {
        PITCH_ROWS.iter().map(|row| self.held(row, step)).collect()
    }

    /// The steps that hold a note of their own, leaving out a step that only grabs one.
    fn written_notes(&self) -> Vec<usize> {
        (0..self.steps as usize).filter(|step| !self.held(DEGREE, *step).is_null()).collect()
    }

    /// Give the steps that hold a note new pitches, one each, in order.
    fn repitch(&mut self, pitches: Vec<Vec<Data>>) {
        for (step, pitch) in self.written_notes().into_iter().zip(pitches) {
            for (row, value) in PITCH_ROWS.iter().zip(pitch) {
                self.hold(row, step, value);
            }
        }
    }

    /// The step after the last tie following a note's step, which is the step after the note when nothing ties to it.
    pub fn tied_end(&self, step: usize) -> usize {
        let mut end = step + 1;
        while end < self.steps as usize && self.is_on(TIE, end) {
            end += 1;
        }
        end
    }

    /// Make one long note of each run of steps next to each other that play the same pitch: the first keeps the note, and
    /// each after it becomes a tie.
    pub fn join_repeated_notes(&mut self) {
        let mut start: Option<usize> = None;
        for step in 0..self.steps as usize {
            if self.is_on(TIE, step) {
                continue;
            }
            if self.held(DEGREE, step).is_null() || self.is_on(GRAB, step) {
                start = None;
            } else if let Some(first) = start.filter(|first| self.pitch(step) == self.pitch(*first)) {
                for row in Self::sound_rows() {
                    self.hold(row, step, blank(row));
                }
                self.hold(TIE, step, Data::Bool(true));
                // The joined note lasts through its ties, whatever gate its first step had.
                self.hold(GATE, first, blank(GATE));
                self.hold(DOT, first, blank(DOT));
            } else {
                start = Some(step);
            }
        }
    }

    /// Make a note of every step a long note covers, by its ties or its gate, given the note covering each step: each
    /// takes the first step's pitch, loudness and the rest, and lasts one step.
    pub fn divide_long_notes(&mut self, covering: &BTreeMap<usize, usize>) {
        for (&step, &start) in covering {
            if step == start {
                continue;
            }
            for row in Self::sound_rows() {
                let value = if LENGTH_ROWS.contains(&row) { blank(row) } else { self.held(row, start) };
                self.hold(row, step, value);
            }
            self.hold(GATE, start, blank(GATE));
            self.hold(DOT, start, blank(DOT));
        }
    }

    /// Move the notes earlier and later among the rests, at random: the notes keep their order and their lengths, and every
    /// rest is still there, somewhere else.
    pub fn randomize_rhythm(&mut self, random: &mut PythonRandom) -> Result<(), InvalidValue> {
        let (mut notes, mut rests) = (Vec::new(), Vec::new());
        let mut step = 0;
        while step < self.steps as usize {
            let end = if self.has_sound(step) { self.tied_end(step) } else { step + 1 };
            if self.has_sound(step) {
                notes.push((step..end).collect::<Vec<_>>());
            } else {
                rests.push((step..end).collect::<Vec<_>>());
            }
            step = end;
        }
        let mut is_note: Vec<bool> = std::iter::repeat_n(true, notes.len()).chain(std::iter::repeat_n(false, rests.len())).collect();
        random.shuffle(&mut is_note);
        let (mut notes_left, mut rests_left) = (notes.into_iter(), rests.into_iter());
        let mut order = Vec::new();
        for note in is_note {
            let steps = if note { notes_left.next() } else { rests_left.next() };
            order.extend(steps.unwrap_or_default());
        }
        self.rearrange(&order)
    }

    /// Shuffle which pitch each note plays, leaving the rhythm, the lengths and the loudness where they are.
    pub fn randomize_pitches(&mut self, random: &mut PythonRandom) {
        let mut pitches: Vec<Vec<Data>> = self.written_notes().into_iter().map(|step| self.pitch(step)).collect();
        random.shuffle(&mut pitches);
        self.repitch(pitches);
    }

    /// Play the pitches in backwards order on the same rhythm.
    pub fn reverse_pitches(&mut self) {
        let pitches = self.written_notes().into_iter().rev().map(|step| self.pitch(step)).collect();
        self.repitch(pitches);
    }

    /// Make a rest of every so many steps, counting from the first: with 4, the fourth, the eighth and on.
    pub fn clear_every(&mut self, every: i64) -> Result<(), InvalidValue> {
        if !(MIN_STEPS..=self.steps as i64).contains(&every) {
            return Err(InvalidValue::new(named(
                errors::ERR_MUNGE_NUMBER_OUT_OF_RANGE,
                &[
                    (file_format::FilterMode::LOW, MIN_STEPS.into()),
                    (file_format::FilterMode::HIGH, (self.steps as i64).into()),
                ],
            )));
        }
        for step in (every as usize - 1..self.steps as usize).step_by(every as usize) {
            self.clear_sound(step)?;
        }
        Ok(())
    }

    /// Move each typed velocity by a random amount, at most so much up or down, kept to what a velocity may be; a blank
    /// velocity stays blank.
    pub fn humanize_velocity(&mut self, most: i64, random: &mut PythonRandom) {
        let Some(place) = Self::place_of(VELOCITY) else { return };
        let Some(velocities) = self.rows[place].as_mut() else { return };
        for velocity in velocities.iter_mut() {
            if let Data::Whole(held) = velocity {
                let moved = *held + random.randint(-(most as i128), most as i128);
                *velocity = Data::Whole(moved.clamp(MIN_VELOCITY as i128, MAX_VELOCITY as i128));
            }
        }
    }

    /// Mirror every note around the pitch of a step's note, by degrees of a scale of so many notes: a note two degrees
    /// above ends two below. A note that leaves the scale's degrees is written in the octave it lands in, counted from the
    /// default octave where its step had none; nothing changes when a drum pattern, a step with no note or an octave out
    /// of range refuses it.
    pub fn invert_melody(&mut self, step: usize, scale_size: i64, default_octave: i64) -> Result<(), InvalidValue> {
        if self.is_drum() || self.held(DEGREE, step).is_null() {
            return Err(InvalidValue::new(errors::ERR_INVERT_NEEDS_A_NOTE.to_string()));
        }
        let octave_of = |pattern: &Pattern, note: usize| pattern.held(OCTAVE, note).as_whole().map_or(default_octave, |octave| octave as i64);
        let place =
            |pattern: &Pattern, note: usize| octave_of(pattern, note) * scale_size + pattern.held(DEGREE, note).as_whole().unwrap_or(0) as i64 - MIN_DEGREE;
        let mut mirrored = Vec::new();
        for note in self.written_notes() {
            let moved = 2 * place(self, step) - place(self, note) - octave_of(self, note) * scale_size;
            let (octaves, degree) = (moved.div_euclid(scale_size), moved.rem_euclid(scale_size));
            if !(MIN_OCTAVE..=MAX_OCTAVE).contains(&(octave_of(self, note) + octaves)) {
                return Err(InvalidValue::new(errors::ERR_INVERT_OUT_OF_RANGE.to_string()));
            }
            mirrored.push((note, degree + MIN_DEGREE, octaves));
        }
        for (note, degree, octaves) in mirrored {
            if octaves != 0 {
                let octave = octave_of(self, note) + octaves;
                self.hold(OCTAVE, note, Data::Whole(octave as i128));
            }
            self.hold(DEGREE, note, Data::Whole(degree as i128));
        }
        Ok(())
    }

    /// Put the steps in a random order.
    pub fn shuffle(&mut self, random: &mut PythonRandom) -> Result<(), InvalidValue> {
        let mut order: Vec<usize> = (0..self.steps as usize).collect();
        random.shuffle(&mut order);
        self.rearrange(&order)
    }

    /// Put a step and every step after it in a random order among themselves.
    pub fn shuffle_from(&mut self, step: usize, random: &mut PythonRandom) -> Result<(), InvalidValue> {
        self.check_step(step as i128)?;
        self.shuffle_part(step, self.steps as usize - 1, random)
    }

    /// Put a step and every step before it in a random order among themselves.
    pub fn shuffle_through(&mut self, step: usize, random: &mut PythonRandom) -> Result<(), InvalidValue> {
        self.check_step(step as i128)?;
        self.shuffle_part(0, step, random)
    }

    /// Put the steps from one to another in a random order among themselves.
    fn shuffle_part(&mut self, first: usize, last: usize, random: &mut PythonRandom) -> Result<(), InvalidValue> {
        let mut order: Vec<usize> = (0..self.steps as usize).collect();
        random.shuffle(&mut order[first..=last]);
        self.rearrange(&order)
    }
}
