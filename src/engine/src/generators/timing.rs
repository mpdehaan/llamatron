// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The Timing generator (the Python engine/generators/timing/ and engine/timing/nudge_plan.py): four rows of steps, each with
//! its own step and amount. Its Glide holds a single note starting on a lit step into a next note of another pitch, and its
//! Shorten plays such a note for a share of its length, both as a step of the chain; its Rush and Drag move the notes on their
//! lit steps early or late after every chain has run, on top of the groove.

use crate::clip::Clip;
use crate::error::{RenderError, Rendered};
use crate::sound::{NoteSound, Sound};
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::schema::checking::{number, time_length, TimeLength};
use llamatron_names::file_format;
use llamatron_names::words;

const RUSH: &str = words::RUSH;
const DRAG: &str = words::DRAG;
const SHORTEN: &str = words::SHORTEN;
const GLIDE: &str = file_format::Row::GLIDE;
const PERCENT: i128 = 100;

/// A part's row of steps, on or off, and how long each step is.
struct StepRow {
    steps: Vec<bool>,
    step: Rational,
}

impl StepRow {
    fn of(settings: &Data, part: &str, pattern_step: Rational, bar: Rational) -> Rendered<Option<StepRow>> {
        let steps: Vec<bool> = settings
            .get(&format!("{part}_steps"))
            .and_then(Data::as_list)
            .unwrap_or(&[])
            .iter()
            .map(|step| *step == Data::Bool(true))
            .collect();
        if !steps.iter().any(|step| *step) {
            return Ok(None);
        }
        let step = match settings.get(&format!("{part}_step")).filter(|step| !step.is_null()) {
            None => pattern_step,
            Some(written) => match time_length(written).map_err(|problem| RenderError::Refused(problem.message))? {
                TimeLength::Bars(count) => bar * Rational::whole(count as i128),
                TimeLength::Length(length) => length,
            },
        };
        Ok(Some(StepRow { steps, step }))
    }

    /// Whether the step a time from the clip's start falls in is on, the row carried on from offset into its run.
    fn is_on(&self, time: Rational, offset: Rational) -> bool {
        self.steps[((time + offset) / self.step).floor().rem_euclid(self.steps.len() as i128) as usize]
    }
}

fn amount<'a>(settings: &'a Data, part: &str) -> Option<&'a Data> {
    settings.get(&format!("{part}_amount")).filter(|amount| !amount.is_null())
}

enum Change {
    Glide(Rational),
    Shorten(Rational),
}

/// Glide and then Shorten, the parts that change notes, each a lit row.
pub struct TimingGenerator {
    rows: Vec<(StepRow, Change)>,
    offset: Rational,
}

impl TimingGenerator {
    pub fn of(settings: &Data, pattern_step: Rational, bar: Rational, offset: Rational) -> Rendered<TimingGenerator> {
        let mut rows = Vec::new();
        if let Some(row) = StepRow::of(settings, GLIDE, pattern_step, bar)? {
            let glide = match amount(settings, GLIDE) {
                Some(written) => number(written).map_err(|problem| RenderError::Refused(problem.message))?,
                None => Rational::new(1, 128),
            };
            rows.push((row, Change::Glide(glide)));
        }
        if let Some(row) = StepRow::of(settings, SHORTEN, pattern_step, bar)? {
            let shorten = amount(settings, SHORTEN).and_then(Data::as_whole).unwrap_or(70);
            rows.push((row, Change::Shorten(Rational::new(shorten, PERCENT))));
        }
        Ok(TimingGenerator { rows, offset })
    }

    pub fn generate(&self, clip: &Clip) -> Rendered<Clip> {
        let mut sounds = clip.resolved_sounds()?;
        for (row, change) in &self.rows {
            let mut result = Vec::new();
            let mut now = Rational::ZERO;
            for (place, sound) in sounds.iter().enumerate() {
                match sound {
                    Sound::Note(note) if row.is_on(now, self.offset) => result.extend(changed(note, change, &sounds[place + 1..])),
                    other => result.push(other.clone()),
                }
                now = now + sound.place();
            }
            sounds = result;
        }
        Ok(Clip {
            sounds,
            time_signature: None,
            looping: true,
            groove: None,
            ..clip.clone()
        })
    }
}

/// The positions a note starting on a lit step becomes.
fn changed(note: &NoteSound, change: &Change, following: &[Sound]) -> Vec<Sound> {
    let length = note.length.unwrap_or(Rational::ZERO);
    match change {
        Change::Glide(amount) => {
            let next = match following.first() {
                Some(Sound::Note(next)) => Some(next.midi),
                _ => None,
            };
            if next.is_none() || next == Some(note.midi) {
                return vec![Sound::Note(*note)];
            }
            vec![Sound::held(
                Sound::Note(NoteSound {
                    length: Some(length + *amount),
                    ..*note
                }),
                length,
            )]
        }
        Change::Shorten(share) => {
            let short = length * *share;
            vec![Sound::Note(NoteSound { length: Some(short), ..*note }), Sound::Rest(length - short)]
        }
    }
}

/// One Rush's or Drag's row: how far a note on one of its lit steps moves, later for a drag and earlier for a rush.
#[derive(Clone, Debug, PartialEq)]
pub struct MovingRow {
    steps: Vec<bool>,
    step: Rational,
    amount: Rational,
    offset: Rational,
}

impl MovingRow {
    /// A Timing generator's lit Rush and Drag rows, carried on from offset into their run.
    pub fn of(settings: &Data, pattern_step: Rational, bar: Rational, offset: Rational) -> Rendered<Vec<MovingRow>> {
        let mut rows = Vec::new();
        for (part, default, later) in [(RUSH, 15, false), (DRAG, 20, true)] {
            let Some(row) = StepRow::of(settings, part, pattern_step, bar)? else {
                continue;
            };
            let share = Rational::new(amount(settings, part).and_then(Data::as_whole).unwrap_or(default), PERCENT);
            let amount = if later { share } else { Rational::ZERO - share };
            rows.push(MovingRow {
                steps: row.steps,
                step: row.step,
                amount,
                offset,
            });
        }
        Ok(rows)
    }

    fn moved(&self, time: Rational) -> Rational {
        let place = ((time + self.offset) / self.step).floor().rem_euclid(self.steps.len() as i128) as usize;
        if !self.steps[place] {
            return Rational::ZERO;
        }
        self.step * self.amount
    }
}

/// A clip's rushes and drags together, the moves of every row its chains name added up.
#[derive(Clone, Debug, PartialEq)]
pub struct NudgePlan {
    pub rows: Vec<MovingRow>,
}

impl NudgePlan {
    /// How much later a note starting at a time from the clip's start plays, early being less than nothing.
    pub fn moved(&self, time: Rational) -> Rational {
        self.rows.iter().fold(Rational::ZERO, |total, row| total + row.moved(time))
    }
}
