// llamatron: a music program
// Copyright (C) 2026  Michael DeHaan
// SPDX-License-Identifier: GPL-3.0-or-later
//! The groove editor (the Python screens/set/groove_editor.py): one groove's cells in a row, each a percentage of its cell
//! late or early, which can be edited unless the groove is a factory one, which can only be looked at.

use crate::app::App;
use crate::drawing::Style;
use crate::keybindings::{Binding, GrooveEditor as Keys, KeyClass};
use crate::keys::KeyItem;
use crate::screens::one_row_editor::{Edge, GridLine, OneRow};
use crate::screens::set::grooves_page::is_factory;
use crate::settings::named_in;
use crate::text::Text;
use crate::themes::{self, Colour};
use llamatron_engine::groove::FACTORY_GROOVES;
use llamatron_model::file::data::Data;
use llamatron_model::objects::setlist::Item;
use llamatron_model::schema::generated::defaults::DEFAULT_GROOVE_CELL_LENGTH;
use llamatron_model::schema::generated::file_format::Section;
use llamatron_model::schema::generated::limits::{MAX_GROOVE_AMOUNT, MAX_GROOVE_CELLS, MIN_GROOVE_CELLS};
use llamatron_strings::{labels, marks, messages, named};

const CELL_WIDTH: usize = 5;

/// A groove's cells and its cell length as the file writes it, a factory one's or the set's own.
pub fn groove_of(app: &App, name: &str) -> (Vec<Option<i64>>, String) {
    if let Some((_, cells, (numerator, denominator))) = FACTORY_GROOVES.iter().find(|(found, _, _)| *found == name) {
        return (cells.iter().map(|cell| Some(*cell)).collect(), format!("{numerator}/{denominator}"));
    }
    let Some(Item::Groove(groove)) = app.document.get_setlist().get_item(Section::GROOVES, name) else {
        return (Vec::new(), DEFAULT_GROOVE_CELL_LENGTH.to_string());
    };
    let cells = groove
        .get_cells()
        .as_list()
        .unwrap_or(&[])
        .iter()
        .map(|cell| cell.as_whole().map(|whole| whole as i64))
        .collect();
    let length = match groove.get_cell_length() {
        Some(Data::Text(text)) => text.clone(),
        Some(Data::Whole(whole)) => whole.to_string(),
        _ => DEFAULT_GROOVE_CELL_LENGTH.to_string(),
    };
    (cells, length)
}

pub struct GrooveEditor {
    pub name: String,
}

impl OneRow for GrooveEditor {
    fn name(&self) -> &'static str {
        "GrooveEditor"
    }

    fn class(&self) -> &'static KeyClass {
        &Keys::CLASS
    }

    fn crumbs(&self, _app: &App) -> Vec<String> {
        vec![
            labels::Crumb::GROOVES.to_string(),
            named(labels::MSG_ITEM_CRUMB, &[("name", self.name.as_str().into())]),
        ]
    }

    fn caption(&self, _app: &App) -> String {
        let what = named_in(labels::MSG_CAPTION_WORDS, Section::GROOVES).to_uppercase();
        named(
            labels::MSG_EDITING_CAPTION,
            &[("what", what.as_str().into()), ("name", self.name.as_str().into())],
        )
    }

    fn theme(&self) -> Option<Colour> {
        Some(themes::GROOVES)
    }

    fn cell_width(&self) -> usize {
        CELL_WIDTH
    }

    fn most(&self) -> i64 {
        MAX_GROOVE_AMOUNT
    }

    fn most_steps(&self) -> usize {
        MAX_GROOVE_CELLS as usize
    }

    fn fewest_steps(&self) -> usize {
        MIN_GROOVE_CELLS as usize
    }

    fn insert(&self) -> &'static Binding {
        &Keys::INSERT_CELL
    }

    fn remove(&self) -> &'static Binding {
        &Keys::REMOVE_CELL
    }

    fn steps_shown(&self) -> &'static str {
        marks::MSG_CELLS_SHOWN
    }

    fn values(&self, app: &App) -> Vec<Option<i64>> {
        groove_of(app, &self.name).0
    }

    fn can_edit(&self, _app: &App) -> bool {
        !is_factory(&self.name)
    }

    fn more_keys(&self, _app: &App) -> Vec<KeyItem> {
        vec![KeyItem::of(&Keys::CLASS, &Keys::CELL_LENGTH), KeyItem::of(&Keys::CLASS, &Keys::RENAME)]
    }

    fn lines(&self, app: &App, heading: &dyn Fn(String, bool, bool) -> GridLine, first: usize, last: usize, step: usize) -> Vec<GridLine> {
        let (cells, length) = groove_of(app, &self.name);
        let title = named(
            marks::MSG_GROOVE_NAME_SHOWN,
            &[("label", labels::MSG_NAME_LABEL.into()), ("name", self.name.as_str().into())],
        );
        let mut lines = vec![
            heading(title, false, true),
            GridLine::Drawn(Text::styled(
                &named(messages::MSG_GROOVE_NOTE, &[("length", length.as_str().into())]),
                Style::DIM,
            )),
            GridLine::Drawn(Text::styled(messages::MSG_GROOVE_REPEATS_NOTE, Style::DIM)),
        ];
        if is_factory(&self.name) {
            lines.push(GridLine::Drawn(Text::styled(messages::MSG_FACTORY_GROOVE_NOTE, Style::DIM)));
        }
        let count = last - first;
        lines.push(GridLine::Drawn(Text::default()));
        lines.push(GridLine::Rule { edge: Edge::Top, count });
        lines.push(GridLine::Row {
            label: labels::MSG_CELL_ROW_LABEL.to_string(),
            cells: (first..last).map(|place| (place, (place + 1).to_string())).collect(),
            selected: None,
            bold: true,
        });
        let amounts = (first..last)
            .map(|place| (place, cells[place].map_or("None".to_string(), |cell| cell.to_string())))
            .collect();
        lines.push(GridLine::Row {
            label: labels::MSG_AMOUNT_ROW_LABEL.to_string(),
            cells: amounts,
            selected: Some(step),
            bold: false,
        });
        lines.push(GridLine::Rule { edge: Edge::Bottom, count });
        lines
    }
}
