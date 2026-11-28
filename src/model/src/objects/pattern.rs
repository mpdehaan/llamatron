// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! A pattern as a set stores it (the Python model/objects/pattern.py): its count of steps, its settings, and its rows, each a
//! list of a value a step, kept as each row's kind keeps them (model/schema/row_descriptions.py) and written back leaving out
//! the rows with nothing in them, so that files stay short.

#[path = "pattern_munges.rs"]
mod munges;
use crate::file::data::Data;
use crate::objects::holder::{in_table, passed_over, Holder};
use crate::objects::step_checks::check_step;
use crate::schema::checking::plain_data;
use crate::schema::checking::InvalidValue;
use crate::schema::generated::file_format::{PatternSetting, Row, CC_ROWS, CHORD_ROWS, PATTERN_ROWS, PITCH_ROWS, STATEMENT_OF_ROW};
use crate::schema::generated::limits::{MAX_STEPS, MIN_STEPS};
use crate::schema::generated::rows::{RowKind, ROWS, ROW_DESCRIPTIONS};
use crate::schema::generated::settings::{Plain, PATTERN};
use llamatron_names::file_format;
use llamatron_names::fill;
use llamatron_names::spec;
use llamatron_names::words;
use llamatron_strings::errors;
use llamatron_strings::named;

#[derive(Clone, Debug, PartialEq)]
pub struct Pattern {
    steps: i128,
    settings: Holder,
    rows: Vec<Option<Vec<Data>>>,
}

fn kind_of(row: &str) -> RowKind {
    ROWS.iter().find(|(name, _)| *name == row).map(|(_, kind)| *kind).unwrap_or(RowKind::Plain)
}

/// The number a message gives the first step.
const FIRST_STEP_NUMBER: i64 = 1;

/// Whether a value is what Python takes as true.
fn truthy(value: &Data) -> bool {
    !matches!(value, Data::Null | Data::Bool(false)) && *value != Data::Whole(0) && *value != Data::Float(0.0) && *value != Data::text("")
}

/// A step's chosen set as a pattern keeps it: the chosen in the choices' order, or nothing where none is chosen.
fn in_order(chosen: &Data, choices: &[Plain]) -> Data {
    let items = chosen.as_list().unwrap_or(&[]);
    let ordered: Vec<Data> = choices.iter().map(plain_data).filter(|choice| items.contains(choice)).collect();
    if ordered.is_empty() {
        return Data::Null;
    }
    Data::List(ordered)
}

/// A row's values as the pattern keeps them.
fn read_row(row: &str, values: &[Data]) -> Vec<Data> {
    match kind_of(row) {
        RowKind::ChosenSet(choices) => values
            .iter()
            .map(|value| if value.is_null() { Data::Null } else { in_order(value, choices) })
            .collect(),
        _ => values.to_vec(),
    }
}

/// What a step holds on a row when nothing is set, as the row's description says: off on an on or off row, 0 on a row
/// whose blank is 0, and nothing otherwise.
fn blank(row: &str) -> Data {
    match ROW_DESCRIPTIONS.iter().find(|description| description.name == row) {
        Some(description) => plain_data(&description.blank),
        None if matches!(kind_of(row), RowKind::Toggle) => Data::Bool(false),
        None => Data::Null,
    }
}

/// Whether a row has any step that isn't its blank, which is what makes it worth writing.
fn holds_something(row: &str, values: &[Data]) -> bool {
    let blank = blank(row);
    values.iter().any(|value| !value.is_null() && *value != blank)
}

/// A row as a file writes it: an on or off row as true and false.
fn written_row(row: &str, values: &[Data]) -> Vec<Data> {
    match kind_of(row) {
        RowKind::Toggle => values.iter().map(|value| Data::Bool(truthy(value))).collect(),
        _ => values.to_vec(),
    }
}

impl Pattern {
    /// A pattern from a file's data, its steps checked and its settings, and each row a list of a value a step.
    pub fn from_data(data: &Data) -> Result<Pattern, InvalidValue> {
        if !matches!(data, Data::Map(_)) {
            return Err(InvalidValue::new(errors::ERR_PATTERN_EXPECTED_SETTINGS.to_string()));
        }
        let data = passed_over(data, &|name| {
            name == PatternSetting::STEPS || in_table(PATTERN, name) || PATTERN_ROWS.contains(&name)
        });
        let steps = data
            .get(PatternSetting::STEPS)
            .and_then(Data::as_whole)
            .filter(|steps| *steps >= MIN_STEPS as i128);
        let Some(steps) = steps else {
            let found = data.get(PatternSetting::STEPS).cloned().unwrap_or(Data::Null);
            return Err(InvalidValue::new(named(
                errors::ERR_BAD_STEPS,
                &[(spec::LOWEST, MIN_STEPS.into()), (file_format::StatementPart::VALUE, (&found).into())],
            )));
        };
        let settings = Holder::read(PATTERN, &data, None, &[])?;
        let drum = settings.get(PatternSetting::DRUM).is_some_and(truthy);
        let mut rows = Vec::with_capacity(PATTERN_ROWS.len());
        for row in PATTERN_ROWS {
            let values = match data.get(row) {
                None | Some(Data::Null) => None,
                Some(Data::List(values)) if values.len() as i128 == steps => {
                    for value in values {
                        check_step(row, value, drum).map_err(|problem| problem.within(row))?;
                    }
                    Some(read_row(row, values))
                }
                Some(found) => {
                    return Err(InvalidValue::new(named(
                        errors::ERR_ROW_WRONG_LENGTH,
                        &[
                            (words::ROW, (*row).into()),
                            (file_format::PatternSetting::STEPS, (steps as i64).into()),
                            (file_format::StatementPart::VALUE, found.into()),
                        ],
                    )));
                }
            };
            rows.push(values);
        }
        let pattern = Pattern { steps, settings, rows };
        pattern.checked_ties()?;
        Ok(pattern)
    }

    /// Refuse a tie on a step that has a note or grabs one, since a tied step plays nothing of its own.
    fn checked_ties(&self) -> Result<(), InvalidValue> {
        let Some(ties) = self.row(Row::TIE) else { return Ok(()) };
        for (step, tie) in ties.iter().enumerate() {
            if truthy(tie) && self.has_sound(step) {
                let shown = step as i64 + FIRST_STEP_NUMBER;
                return Err(InvalidValue::new(named(errors::ERR_TIE_ON_A_NOTE, &[(fill::STEP, shown.into())])));
            }
        }
        Ok(())
    }

    pub fn get_steps(&self) -> i128 {
        self.steps
    }

    pub fn is_drum(&self) -> bool {
        self.settings.get(PatternSetting::DRUM).is_some_and(truthy)
    }

    pub fn get_written(&self, name: &str) -> Option<&Data> {
        self.settings.get(name)
    }

    /// A row's values, or None for a row the pattern doesn't have.
    /// Whether a step plays something: a degree, or a grab.
    pub fn has_sound(&self, step: usize) -> bool {
        let at = |row: &str| self.row(row).and_then(|values| values.get(step)).filter(|value| !value.is_null());
        at(file_format::Row::DEGREE).is_some() || matches!(at(file_format::Row::GRAB), Some(Data::Bool(true)))
    }

    /// Whether a step plays a note, holds one with a tie or sends a CC value.
    pub fn holds_anything(&self, step: usize) -> bool {
        let at = |row: &str| self.row(row).and_then(|values| values.get(step)).filter(|value| !value.is_null());
        self.has_sound(step) || matches!(at(file_format::Row::TIE), Some(Data::Bool(true))) || CC_ROWS.iter().any(|row| at(row).is_some())
    }

    /// How many steps from a place onward hold anything, which shortening the pattern there would lose.
    pub fn steps_with_anything_from(&self, start: usize) -> usize {
        (start..self.get_steps().max(0) as usize).filter(|step| self.holds_anything(*step)).count()
    }

    /// Whether any step plays something.
    pub fn has_note_steps(&self) -> bool {
        (0..self.get_steps().max(0) as usize).any(|step| self.has_sound(step))
    }

    pub fn row(&self, row: &str) -> Option<&[Data]> {
        let place = PATTERN_ROWS.iter().position(|name| *name == row)?;
        self.rows[place].as_deref()
    }

    /// Its steps, its settings and its rows, leaving out rows with nothing in them.
    pub fn to_data(&self) -> Data {
        let mut pairs = vec![(Data::text(PatternSetting::STEPS), Data::Whole(self.steps))];
        pairs.extend(self.settings.written());
        for (row, values) in PATTERN_ROWS.iter().zip(&self.rows) {
            if let Some(values) = values.as_ref().filter(|values| holds_something(row, values)) {
                pairs.push((Data::text(row), Data::List(written_row(row, values))));
            }
        }
        Data::Map(pairs)
    }
}

/// What a rest may still hold, which erasing a step's note leaves: its CC values, its slide and the draws' rows (the Python's
/// pattern_munges.REST_ROWS).
const REST_ROWS: [&str; 44] = [
    "cc1",
    "cc2",
    "cc3",
    "cc4",
    "slide",
    "ad_note",
    "bd_note",
    "cd_note",
    "dd_note",
    "ed_note",
    "fd_note",
    "gd_note",
    "hd_note",
    "ad_velocity",
    "bd_velocity",
    "cd_velocity",
    "dd_velocity",
    "ed_velocity",
    "fd_velocity",
    "gd_velocity",
    "hd_velocity",
    "ad_reset",
    "bd_reset",
    "cd_reset",
    "dd_reset",
    "ed_reset",
    "fd_reset",
    "gd_reset",
    "hd_reset",
    "stop_c1",
    "stop_c2",
    "stop_c3",
    "stop_c4",
    "stop_c5",
    "restart_c1",
    "restart_c2",
    "restart_c3",
    "restart_c4",
    "restart_c5",
    "mute_c1",
    "mute_c2",
    "mute_c3",
    "mute_c4",
    "mute_c5",
];
/// The rows that mean something else in a drum pattern than in another, which making a pattern a drum pattern or not clears
/// (the Python's pattern.NOTE_ROWS).
const NOTE_ROWS: [&str; 18] = [
    "degree",
    "accidental",
    "chord",
    "inversion",
    "double",
    "omit",
    "bass",
    "bass_octave",
    "tension",
    "chord_scale",
    "ad_note",
    "bd_note",
    "cd_note",
    "dd_note",
    "ed_note",
    "fd_note",
    "gd_note",
    "hd_note",
];
const RESTART_ROWS: [&str; 5] = ["restart_c1", "restart_c2", "restart_c3", "restart_c4", "restart_c5"];
const TIE: &str = file_format::Row::TIE;
const VELOCITY: &str = file_format::TrackSetting::VELOCITY;

/// A step's value as a step of its own may hold it: a list is a copy, so that two steps never share one.
fn own_step_value(value: &Data) -> Data {
    value.clone()
}

impl Pattern {
    /// A row's place among the rows, which every row has.
    fn place_of(row: &str) -> Option<usize> {
        PATTERN_ROWS.iter().position(|name| *name == row)
    }

    /// A row's values as held, made blank first where no step used it.
    fn row_mut(&mut self, row: &str) -> Option<&mut Vec<Data>> {
        let place = Self::place_of(row)?;
        let steps = self.steps as usize;
        Some(self.rows[place].get_or_insert_with(|| vec![blank(row); steps]))
    }

    /// Refuse a step the pattern does not have.
    fn check_step(&self, step: i128) -> Result<(), InvalidValue> {
        if step < 0 || step >= self.steps {
            return Err(InvalidValue::new(named(
                errors::ERR_PATTERN_NO_SUCH_STEP,
                &[
                    (words::STEP, (step as i64).into()),
                    (file_format::PatternSetting::STEPS, (self.steps as i64).into()),
                ],
            )));
        }
        Ok(())
    }

    /// Set one step's value on a row, where None makes the step blank there.
    pub fn set_value(&mut self, row: &str, step: usize, value: Option<Data>) -> Result<(), InvalidValue> {
        self.check_step(step as i128)?;
        let kept = match value {
            None => blank(row),
            Some(value) => match kind_of(row) {
                RowKind::ChosenSet(choices) => in_order(&value, choices),
                _ => value,
            },
        };
        if let Some(values) = self.row_mut(row) {
            values[step] = kept;
        }
        Ok(())
    }

    /// Empty a step of its note, keeping only what a rest can hold, and the ties on the steps right after it, which held
    /// that note.
    pub fn clear_sound(&mut self, step: usize) -> Result<(), InvalidValue> {
        self.check_step(step as i128)?;
        for (row, values) in PATTERN_ROWS.iter().zip(self.rows.iter_mut()) {
            if let Some(values) = values.as_mut().filter(|_| !REST_ROWS.contains(row)) {
                values[step] = blank(row);
            }
        }
        if let Some(Some(ties)) = Self::place_of(TIE).map(|place| &mut self.rows[place]) {
            let mut later = step + 1;
            while later < ties.len() && truthy(&ties[later]) {
                ties[later] = blank(TIE);
                later += 1;
            }
        }
        Ok(())
    }

    /// Change how many steps it has, cutting steps off the end or adding empty ones.
    pub fn set_steps(&mut self, steps: i128) -> Result<(), InvalidValue> {
        if steps < MIN_STEPS as i128 {
            return Err(InvalidValue::new(named(
                errors::ERR_BAD_STEPS,
                &[(spec::LOWEST, MIN_STEPS.into()), (file_format::StatementPart::VALUE, (steps as i64).into())],
            )));
        }
        for (row, values) in PATTERN_ROWS.iter().zip(self.rows.iter_mut()) {
            if let Some(values) = values.as_mut() {
                values.resize(steps as usize, blank(row));
            }
        }
        self.steps = steps;
        Ok(())
    }

    /// Put an empty step before a step, or at the end where step is the number of steps.
    pub fn insert_step(&mut self, step: usize) -> Result<(), InvalidValue> {
        if step as i128 > self.steps {
            return Err(InvalidValue::new(named(
                errors::ERR_PATTERN_NO_SUCH_STEP,
                &[
                    (words::STEP, (step as i64).into()),
                    (file_format::PatternSetting::STEPS, (self.steps as i64).into()),
                ],
            )));
        }
        for (row, values) in PATTERN_ROWS.iter().zip(self.rows.iter_mut()) {
            if let Some(values) = values.as_mut() {
                values.insert(step, blank(row));
            }
        }
        self.steps += 1;
        Ok(())
    }

    /// Take a step out, which a pattern with only one step cannot do.
    pub fn remove_step(&mut self, step: usize) -> Result<(), InvalidValue> {
        self.check_step(step as i128)?;
        if self.steps <= MIN_STEPS as i128 {
            return Err(InvalidValue::new(named(
                errors::ERR_BAD_STEPS,
                &[
                    (spec::LOWEST, MIN_STEPS.into()),
                    (file_format::StatementPart::VALUE, ((self.steps - 1) as i64).into()),
                ],
            )));
        }
        for values in self.rows.iter_mut().flatten() {
            values.remove(step);
        }
        self.steps -= 1;
        Ok(())
    }

    /// Write one of its settings, or take it out of the file with None.
    pub fn set_written(&mut self, name: &str, value: Option<Data>) {
        self.settings.put(name, value);
    }

    /// Make it a drum pattern or not, which clears the notes, since they mean something else in each; a drum's notes are of
    /// no scale.
    pub fn set_drum(&mut self, drum: bool) {
        for row in NOTE_ROWS {
            if let Some(place) = Self::place_of(row) {
                self.rows[place] = None;
            }
        }
        self.settings.put(PatternSetting::DRUM, drum.then_some(Data::Bool(true)));
        if drum {
            self.settings.put(PatternSetting::SCALE_LENGTH, None);
        }
    }

    /// Put the steps in a new order, given as the old place of each new step, every value of a step moving together.
    pub fn rearrange(&mut self, order: &[usize]) -> Result<(), InvalidValue> {
        let mut sorted = order.to_vec();
        sorted.sort_unstable();
        if sorted != (0..self.steps as usize).collect::<Vec<_>>() {
            return Err(InvalidValue::new(named(
                errors::ERR_PATTERN_NOT_AN_ORDER,
                &[(words::ORDER, format!("{order:?}").as_str().into())],
            )));
        }
        self.take_steps(order)
    }

    /// Make the pattern of its own steps in a new order, a step coming more than once where it is given more than once: the
    /// pattern is then as long as the order. The first step never starts the pattern over, since it would never get past it.
    pub fn take_steps(&mut self, order: &[usize]) -> Result<(), InvalidValue> {
        if order.is_empty() || order.len() > MAX_STEPS as usize || order.iter().any(|step| *step as i128 >= self.steps) {
            return Err(InvalidValue::new(named(
                errors::ERR_PATTERN_NOT_AN_ORDER,
                &[(words::ORDER, format!("{order:?}").as_str().into())],
            )));
        }
        for values in self.rows.iter_mut().flatten() {
            *values = order.iter().map(|step| own_step_value(&values[*step])).collect();
        }
        self.steps = order.len() as i128;
        for row in RESTART_ROWS {
            if let Some(Some(values)) = Self::place_of(row).map(|place| &mut self.rows[place]) {
                values[0] = blank(row);
            }
        }
        Ok(())
    }

    /// Blank every step of some rows.
    pub fn clear_rows(&mut self, rows: &[&str]) {
        let steps = self.steps as usize;
        for row in rows {
            if let Some(Some(values)) = Self::place_of(row).map(|place| &mut self.rows[place]) {
                *values = vec![blank(row); steps];
            }
        }
    }

    /// Put a step of another pattern after each of its own, so that it is twice as long, the other's steps read round and
    /// round; the other is not changed.
    pub fn interleave(&mut self, other: &Pattern) -> Result<(), InvalidValue> {
        if self.steps * 2 > MAX_STEPS as i128 || other.is_drum() != self.is_drum() {
            return Err(InvalidValue::new(errors::ERR_PATTERN_CANNOT_INTERLEAVE.to_string()));
        }
        let steps = self.steps as usize;
        for (place, row) in PATTERN_ROWS.iter().enumerate() {
            if self.rows[place].is_none() && other.rows[place].is_none() {
                continue;
            }
            let own = self.rows[place].clone().unwrap_or_else(|| vec![blank(row); steps]);
            let others = other.rows[place].clone().unwrap_or_else(|| vec![blank(row); other.steps as usize]);
            let mut woven = Vec::with_capacity(steps * 2);
            for (step, value) in own.iter().enumerate() {
                woven.push(value.clone());
                woven.push(own_step_value(&others[step % others.len()]));
            }
            self.rows[place] = Some(woven);
        }
        self.steps *= 2;
        Ok(())
    }

    /// Add another pattern's steps after its own last, or before the step at a place, 0 for before its first; the other is
    /// not changed.
    pub fn splice(&mut self, other: &Pattern, at: Option<usize>) -> Result<(), InvalidValue> {
        let at = at.unwrap_or(self.steps as usize);
        if at as i128 > self.steps {
            return Err(InvalidValue::new(named(
                errors::ERR_PATTERN_NO_SUCH_STEP,
                &[
                    (words::STEP, (at as i64).into()),
                    (file_format::PatternSetting::STEPS, (self.steps as i64).into()),
                ],
            )));
        }
        if self.steps + other.steps > MAX_STEPS as i128 || other.is_drum() != self.is_drum() {
            return Err(InvalidValue::new(errors::ERR_PATTERN_CANNOT_INTERLEAVE.to_string()));
        }
        let steps = self.steps as usize;
        for (place, row) in PATTERN_ROWS.iter().enumerate() {
            if self.rows[place].is_none() && other.rows[place].is_none() {
                continue;
            }
            let own = self.rows[place].clone().unwrap_or_else(|| vec![blank(row); steps]);
            let others = other.rows[place].clone().unwrap_or_else(|| vec![blank(row); other.steps as usize]);
            let mut spliced = own[..at].to_vec();
            spliced.extend(others.iter().map(own_step_value));
            spliced.extend(own[at..].iter().cloned());
            self.rows[place] = Some(spliced);
        }
        self.steps += other.steps;
        Ok(())
    }

    /// Fill the blank steps between two values of each of some rows from a straight line between the two; with notes_only,
    /// a step that plays nothing is left blank, though it still counts along the line.
    pub fn smooth_rows(&mut self, rows: &[&str], notes_only: bool) {
        let sounding: Vec<bool> = (0..self.steps as usize).map(|step| self.has_sound(step)).collect();
        for row in rows {
            let Some(Some(values)) = Self::place_of(row).map(|place| &mut self.rows[place]) else {
                continue;
            };
            let given: Vec<usize> = values.iter().enumerate().filter(|(_, value)| !value.is_null()).map(|(step, _)| step).collect();
            for pair in given.windows(2) {
                let (start, end) = (pair[0], pair[1]);
                let (from, to) = (number(&values[start]), number(&values[end]));
                for step in start + 1..end {
                    if notes_only && !sounding[step] {
                        continue;
                    }
                    let along = from + (to - from) * (step - start) as f64 / (end - start) as f64;
                    values[step] = Data::Whole((along + 0.5).floor() as i128);
                }
            }
        }
    }

    /// Fill the blank steps between two values of each CC row.
    pub fn smooth_ccs(&mut self) {
        self.smooth_rows(CC_ROWS, false);
    }

    /// Fill the blank velocities between two typed ones, on the steps that play a note.
    pub fn smooth_velocity(&mut self) {
        self.smooth_rows(&[VELOCITY], true);
    }

    /// Blank everything a step holds but which notes it plays: its degree, octave, sharp or flat and chord stay.
    pub fn clear_all_but_pitch(&mut self) {
        let rows: Vec<&str> = PATTERN_ROWS.iter().copied().filter(|row| !PITCH_ROWS.contains(row)).collect();
        self.clear_rows(&rows);
    }

    /// Blank every step's chord, with its tensions, borrowed scale and inversion, leaving the note each chord was built on.
    pub fn clear_chords(&mut self) {
        self.clear_rows(CHORD_ROWS);
    }

    /// Blank every step's statements about the draws.
    pub fn clear_statements(&mut self) {
        let rows: Vec<&str> = STATEMENT_OF_ROW.iter().map(|(row, _)| *row).collect();
        self.clear_rows(&rows);
    }

    /// The order of its steps, for the rearranging munges.
    fn every_step(&self) -> Vec<usize> {
        (0..self.steps as usize).collect()
    }

    /// Add its steps again after the last, backwards, so that it plays forward and then back and is twice as long.
    pub fn mirror(&mut self) -> Result<(), InvalidValue> {
        let mut order = self.every_step();
        order.extend(self.every_step().into_iter().rev());
        self.take_steps(&order)
    }

    /// Add a copy of the steps from first through last after the last step.
    pub fn repeat_at_end(&mut self, first: usize, last: usize) -> Result<(), InvalidValue> {
        self.check_step(first as i128)?;
        self.check_step(last as i128)?;
        let mut order = self.every_step();
        order.extend(first..=last);
        self.take_steps(&order)
    }

    /// Put a copy of the steps from first through last before the first step.
    pub fn repeat_at_start(&mut self, first: usize, last: usize) -> Result<(), InvalidValue> {
        self.check_step(first as i128)?;
        self.check_step(last as i128)?;
        let mut order: Vec<usize> = (first..=last).collect();
        order.extend(self.every_step());
        self.take_steps(&order)
    }

    /// Turn the pattern so many steps to the left, or to the right when negative.
    pub fn roll(&mut self, steps: i64) -> Result<(), InvalidValue> {
        let count = self.steps as i64;
        let order: Vec<usize> = (0..count).map(|step| (step + steps).rem_euclid(count) as usize).collect();
        self.take_steps(&order)
    }

    /// Turn a step and every step before it one step to the left among themselves.
    pub fn roll_through(&mut self, step: usize) -> Result<(), InvalidValue> {
        self.check_step(step as i128)?;
        let order = self.every_step();
        let mut turned: Vec<usize> = order[1..=step].to_vec();
        turned.push(0);
        turned.extend(order[step + 1..].iter().copied());
        self.take_steps(&turned)
    }

    /// Turn a step and every step after it one step to the right among themselves.
    pub fn roll_from(&mut self, step: usize) -> Result<(), InvalidValue> {
        self.check_step(step as i128)?;
        let order = self.every_step();
        let last = order.len() - 1;
        let mut turned: Vec<usize> = order[..step].to_vec();
        turned.push(last);
        turned.extend(order[step..last].iter().copied());
        self.take_steps(&turned)
    }

    /// Reverse every step after a step.
    pub fn reverse_after(&mut self, step: usize) -> Result<(), InvalidValue> {
        self.check_step(step as i128)?;
        let order = self.every_step();
        let mut turned: Vec<usize> = order[..=step].to_vec();
        turned.extend(order[step + 1..].iter().rev().copied());
        self.rearrange(&turned)
    }

    /// Reverse every step before a step.
    pub fn reverse_before(&mut self, step: usize) -> Result<(), InvalidValue> {
        self.check_step(step as i128)?;
        let order = self.every_step();
        let mut turned: Vec<usize> = order[..step].iter().rev().copied().collect();
        turned.extend(order[step..].iter().copied());
        self.rearrange(&turned)
    }

    /// Reverse the whole pattern, so that its last step plays first.
    pub fn reverse(&mut self) -> Result<(), InvalidValue> {
        let order: Vec<usize> = self.every_step().into_iter().rev().collect();
        self.rearrange(&order)
    }

    /// Swap what's before a step with what's after it, and return where the step ends up.
    pub fn pivot_around(&mut self, step: usize) -> Result<usize, InvalidValue> {
        self.check_step(step as i128)?;
        let order = self.every_step();
        let after = &order[step + 1..];
        let mut turned: Vec<usize> = after.to_vec();
        turned.push(step);
        turned.extend(order[..step].iter().copied());
        let place = after.len();
        self.rearrange(&turned)?;
        Ok(place)
    }

    /// Put it in a group, by the group's name, or in none.
    pub fn set_group(&mut self, group: Option<&str>) {
        self.settings
            .put(PatternSetting::GROUP, group.filter(|group| !group.is_empty()).map(Data::text));
    }

    /// Set the order its steps play in, forward left out of the file as the default.
    pub fn set_direction(&mut self, direction: &str) {
        self.settings.put(
            PatternSetting::DIRECTION,
            (direction != file_format::Direction::FORWARD).then(|| Data::text(direction)),
        );
    }
}

/// A number, whole or not, as a float, 0 for anything else.
fn number(value: &Data) -> f64 {
    match value {
        Data::Whole(whole) => *whole as f64,
        Data::Float(float) => *float,
        _ => 0.0,
    }
}

impl Pattern {
    /// Give a step a statement of a kind about the draws, written across the kind's five rows, or None to take the step's
    /// away; the first step never starts the pattern over.
    pub fn set_statement(&mut self, kind: &str, step: usize, statement: Option<&Data>) -> Result<(), InvalidValue> {
        self.check_step(step as i128)?;
        if statement.is_some() && kind == file_format::LfoSetting::RESTART && step == 0 {
            return Err(InvalidValue::new(errors::ERR_RESTART_ON_FIRST_STEP.to_string()));
        }
        let rows = crate::schema::generated::file_format::STATEMENT_ROWS
            .iter()
            .find(|(each, _)| *each == kind)
            .map(|(_, rows)| *rows)
            .unwrap_or(&[]);
        let parts = crate::schema::generated::file_format::STATEMENT_PARTS;
        for (row, part) in rows.iter().zip(parts) {
            let value = statement.and_then(|statement| statement.get(part)).cloned();
            let place = Self::place_of(row);
            if value.is_none() && place.is_none_or(|place| self.rows[place].is_none()) {
                continue;
            }
            if let Some(values) = self.row_mut(row) {
                values[step] = value.unwrap_or(Data::Null);
            }
        }
        Ok(())
    }
}
