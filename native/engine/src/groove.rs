// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! Grooves (the Python model/objects/groove.py): a groove moves each note's start by its cell's share of the cell's length,
//! cell after cell around the groove, and a clip's groove is chosen by its track, then its scene, then its song, a false
//! anywhere switching grooving off. A groove that moves nothing is no groove at all.

use crate::error::{RenderError, Rendered};
use llamatron_math::Rational;
use llamatron_model::file::data::Data;
use llamatron_model::objects::named::Groove as WrittenGroove;
use llamatron_model::objects::setlist::{Item, Setlist};
use llamatron_model::schema::checking::written_length;
use llamatron_model::schema::generated::file_format::Section;
use llamatron_model::schema::generated::limits::MAX_GROOVE_CELL_LENGTH;

const PERCENT: i128 = 100;
const DEFAULT_CELL_LENGTH: &str = "1/16";

/// The factory grooves every set has, each its cells as percentages of its cell's length, and its cell's length.
const FACTORY_GROOVES: &[(&str, [i64; 16], (i128, i128))] = &[
    ("none", [0; 16], (1, 16)),
    ("swing 54", [0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8, 0, 8], (1, 16)),
    ("swing 58", [0, 16, 0, 16, 0, 16, 0, 16, 0, 16, 0, 16, 0, 16, 0, 16], (1, 16)),
    ("swing 62", [0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24, 0, 24], (1, 16)),
    ("swing 66", [0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32], (1, 16)),
    ("8th swing 58", [0, 16, 0, 16, 0, 16, 0, 16, 0, 16, 0, 16, 0, 16, 0, 16], (1, 8)),
    ("8th swing 66", [0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32, 0, 32], (1, 8)),
    ("push", [0, -16, 0, -16, 0, -16, 0, -16, 0, -16, 0, -16, 0, -16, 0, -16], (1, 16)),
];

#[derive(Clone, Debug, PartialEq)]
pub struct Groove {
    cell_length: Rational,
    offsets: Vec<Rational>,
}

impl Groove {
    fn of(cells: &[i64], cell_length: Rational) -> Groove {
        Groove {
            cell_length,
            offsets: cells.iter().map(|amount| cell_length * Rational::new(*amount as i128, PERCENT)).collect(),
        }
    }

    /// A groove by name: a factory groove, or one of the set's own.
    pub fn named(setlist: &Setlist, name: &str) -> Rendered<Groove> {
        if let Some((_, cells, (numerator, denominator))) = FACTORY_GROOVES.iter().find(|(found, _, _)| *found == name) {
            return Ok(Groove::of(cells, Rational::new(*numerator, *denominator)));
        }
        let Some(Item::Groove(written)) = setlist.get_item(Section::GROOVES, name) else {
            return Err(RenderError::Refused(format!("no groove called ({name})")));
        };
        Groove::written(written)
    }

    fn written(written: &WrittenGroove) -> Rendered<Groove> {
        let text = written.get_cell_length().cloned().unwrap_or(Data::text(DEFAULT_CELL_LENGTH));
        let cell_length = written_length(&text, Rational::whole(MAX_GROOVE_CELL_LENGTH as i128)).map_err(|problem| RenderError::Refused(problem.message))?;
        let cells: Vec<i64> = written
            .get_cells()
            .as_list()
            .unwrap_or(&[])
            .iter()
            .filter_map(Data::as_whole)
            .map(|amount| amount as i64)
            .collect();
        Ok(Groove::of(&cells, cell_length))
    }

    pub fn is_straight(&self) -> bool {
        self.offsets.iter().all(|offset| *offset == Rational::ZERO)
    }

    /// When something at a time plays once the groove has moved it, never before the clip's start.
    pub fn moved(&self, time: Rational) -> Rational {
        let cell = (time / self.cell_length).floor().rem_euclid(self.offsets.len() as i128) as usize;
        (time + self.offsets[cell]).max(Rational::ZERO)
    }
}

/// The groove choices, from the most specific to the least, settle on: a false anywhere switches grooving off; otherwise the
/// first name wins, and a straight groove is none.
pub fn groove_for(setlist: &Setlist, choices: &[Option<&Data>]) -> Rendered<Option<Groove>> {
    if choices.contains(&Some(&Data::Bool(false))) {
        return Ok(None);
    }
    let Some(name) = choices.iter().flatten().find(|choice| !choice.is_null()) else {
        return Ok(None);
    };
    let groove = Groove::named(setlist, &name.python_str())?;
    Ok((!groove.is_straight()).then_some(groove))
}
